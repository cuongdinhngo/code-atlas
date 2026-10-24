"""Task 390 — a table names its readers (opt-in READS), and a trigger is among its writers."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_references
from tests.adapter_cli import run_adapter_file

REPO = Path(__file__).resolve().parent.parent
SQL_ENTRY = REPO / "adapters" / "sql" / "index.js"
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
NODE = shutil.which("node")
PHP = shutil.which("php")
needs_both = pytest.mark.skipif(
    NODE is None or PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs node (SQL adapter) and the PHP CLI with `composer install`",
)

SCHEMA = """CREATE TABLE dbo.T (Id INT NOT NULL, C INT NULL, Flag BIT NULL);
GO
CREATE TRIGGER dbo.trg_T_upd ON dbo.T AFTER UPDATE AS
BEGIN
    UPDATE t SET t.C = 2 FROM dbo.T t INNER JOIN inserted i ON i.Id = t.Id;
END
GO
CREATE PROCEDURE dbo.ReadT AS
BEGIN
    SELECT C FROM dbo.T WHERE Flag = 1;
END
GO
"""
PHP_READER = (
    "<?php\nnamespace App;\nclass Repo { public function all() { "
    "return $this->db->query('SELECT Id FROM dbo.T WHERE Flag = 1'); } }\n"
)


def _built(root: Path) -> Config:
    (root / "db").mkdir()
    (root / "src").mkdir()
    (root / "db" / "schema.sql").write_text(SCHEMA, encoding="utf-8")
    (root / "src" / "Repo.php").write_text(PHP_READER, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=root,
            check=True,
            capture_output=True,
        )
    config = load_config(
        root,
        {
            "CA_WORKERS": "2",
            "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"]),
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        },
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config


@needs_both
def test_ac1_an_after_update_trigger_is_listed_as_the_columns_writer(tmp_path: Path) -> None:
    config = _built(tmp_path)
    payload = find_references.create(config)("dbo.T::C")
    assert [(row["qname"], row["kind"]) for row in payload["results"]] == [
        ("dbo.trg_T_upd", "WRITES")
    ]


@needs_both
def test_ac2_reads_lists_the_proc_and_the_host_string_with_their_tiers(tmp_path: Path) -> None:
    config = _built(tmp_path)
    payload = find_references.create(config)("dbo.T", kinds=["READS"])
    rows = sorted((str(r["qname"]), r["kind"], r["confidence_tier"]) for r in payload["results"])
    assert rows == [
        ("\\App\\Repo::all", "READS", "HEURISTIC"),
        ("dbo.ReadT", "READS", "RESOLVED"),
    ], payload


@needs_both
def test_ac3_without_kinds_a_table_answers_its_writers_only(tmp_path: Path) -> None:
    config = _built(tmp_path)
    plain = find_references.create(config)("dbo.T")
    explicit = find_references.create(config)("dbo.T", kinds=["WRITES", "DELETES"])
    assert plain == explicit
    assert {row["kind"] for row in plain["results"]} == {"WRITES"}
    assert "kinds_ignored" not in plain


@needs_both
def test_kinds_must_name_an_inbound_edge_kind(tmp_path: Path) -> None:
    config = _built(tmp_path)
    with pytest.raises(ValueError, match="kinds"):
        find_references.create(config)("dbo.T", kinds=["READ"])
    other = find_references.create(config)("\\App\\Repo::all", kinds=["READS"])
    assert other["kinds_ignored"] == ["READS"]


@needs_both
def test_a_language_that_emits_no_reads_marks_the_answer_partial(tmp_path: Path) -> None:
    """Exposure #2 — a covered language with no READS leaves readers unmeasured (R5.6)."""
    config = _built(tmp_path)
    (tmp_path / "src" / "Repo.php").write_text(
        "<?php\nnamespace App;\nclass Repo { public function all() { return 1; } }\n",
        encoding="utf-8",
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    payload = find_references.create(config)("dbo.T", kinds=["READS"])
    assert "reads_emitters_only" in payload["authoritative_caveats"], payload
    writers = find_references.create(config)("dbo.T")
    assert "reads_emitters_only" not in (writers.get("authoritative_caveats") or [])


@needs_both
def test_challenger_a_comma_join_a_self_read_and_a_one_line_function_are_reads(
    tmp_path: Path,
) -> None:
    """D1–D3: each of these reads a table the routine names; none may be dropped."""
    (tmp_path / "db").mkdir()
    (tmp_path / "db" / "more.sql").write_text(
        "CREATE FUNCTION dbo.F() RETURNS TABLE AS RETURN (SELECT Id FROM dbo.T)\nGO\n"
        "CREATE PROCEDURE dbo.P AS\n"
        "    INSERT INTO dbo.T (Id) SELECT Id FROM dbo.T WHERE 1 = 0;\nGO\n"
        "CREATE PROCEDURE dbo.Q AS\n    SELECT 1 FROM dbo.A a, dbo.B b;\nGO\n",
        encoding="utf-8",
    )
    done = run_adapter_file([str(NODE), str(SQL_ENTRY)], "db/more.sql", cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    reads = {
        (edge["source_qname"], edge["target_raw"])
        for edge in json.loads(done.stdout)["edges"]
        if edge["kind"] == "READS"
    }
    # 410: F's one source binds its bare `Id`; P's INSERT column list is the target's, not read.
    assert reads == {
        ("dbo.F", "dbo.T"),
        ("dbo.F", "dbo.T::Id"),
        ("dbo.P", "dbo.T"),
        ("dbo.Q", "dbo.A"),
        ("dbo.Q", "dbo.B"),
    }


@pytest.mark.skipif(NODE is None, reason="needs node (SQL adapter)")
def test_review_a_call_s_from_is_no_source_and_one_table_is_read_once(tmp_path: Path) -> None:
    """390 review: `TRIM(' ' FROM name)` reads no table; `dbo.T` and `[dbo].[t]` are one read."""
    (tmp_path / "db").mkdir()
    (tmp_path / "db" / "r.sql").write_text(
        "CREATE PROCEDURE dbo.R AS\n"
        "    SELECT TRIM(' ' FROM a.Name), EXTRACT(YEAR FROM a.D) FROM dbo.T a\n"
        "    JOIN [dbo].[t] b ON b.Id = a.Id\n"
        "    WHERE a.Id IN (SELECT Id FROM dbo.U);\nGO\n",
        encoding="utf-8",
    )
    done = run_adapter_file([str(NODE), str(SQL_ENTRY)], "db/r.sql", cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    reads = [
        (edge["source_qname"], edge["target_raw"])
        for edge in json.loads(done.stdout)["edges"]
        if edge["kind"] == "READS" and "::" not in edge["target_raw"]
    ]
    assert reads == [("dbo.R", "dbo.T"), ("dbo.R", "dbo.U")]
