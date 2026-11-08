"""Task 440 — ``compute``: exact answers from a named template in a read-only sandbox.

Callers name a template and typed params, never SQL. The sandbox refuses a write, ``ATTACH`` and
``load_extension`` and interrupts a runaway query, always with a reason. An absence names its
evidence: a function nothing references and nothing mentions is a strong candidate; one named in a
string literal is unknown, never dead. Built through the real Python adapter.
"""

from __future__ import annotations

import asyncio
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from code_atlas import gitutil
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.main import build_server
from code_atlas.store import ComputeRefused, ComputeSandbox, GraphStore
from code_atlas.tools import compute

PY_ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "python" / "index.py"
SOURCES = {
    "lib/a.py": (
        "def used():\n    return 1\n\n\n"
        "def lonely_ghost():\n    return 2\n\n\n"
        "def by_name():\n    return 3\n\n\n"
        "def caller(mod):\n"
        "    used()\n"
        '    return getattr(mod, "by_name")\n'
    ),
}


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Config:
    root = tmp_path_factory.mktemp("compute")
    for rel, body in SOURCES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    config = load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
        },
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config


def ask(config: Config, **args: Any) -> dict[str, Any]:
    return compute.create(config)(**args)


@pytest.mark.parametrize(
    ("sql", "reason"),
    [
        ("INSERT INTO nodes (kind) VALUES ('x')", "refused_by_sandbox"),
        ("DELETE FROM edges", "refused_by_sandbox"),
        ("ATTACH DATABASE ':memory:' AS other", "refused_by_sandbox"),
        ("SELECT load_extension('x')", "refused_by_sandbox"),
        ("PRAGMA query_only = OFF", "refused_by_sandbox"),
        ("UPDATE sqlite_master SET sql = 'x'", "refused_by_sandbox"),
        (
            "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n) "
            "SELECT COUNT(*) FROM n",
            "deadline_exceeded",
        ),
    ],
)
def test_ac1_the_sandbox_refuses_or_interrupts_with_a_reason(
    repo: Config, sql: str, reason: str
) -> None:
    """AC1 (proving test): a write, ATTACH, load_extension and a runaway CTE never answer."""
    with ComputeSandbox(repo.db_path, deadline_s=0.3) as box, pytest.raises(ComputeRefused) as hit:
        box._execute(sql, cap=5)
    assert hit.value.reason == reason


def test_ac1_the_index_is_untouched_after_a_refused_write(repo: Config) -> None:
    with GraphStore(repo.db_path) as store:
        before = store.count_nodes_by_file("lib/a.py")
    with ComputeSandbox(repo.db_path) as box, pytest.raises(ComputeRefused):
        box._execute("DELETE FROM nodes", cap=1)
    with GraphStore(repo.db_path) as store:
        assert store.count_nodes_by_file("lib/a.py") == before


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ({"template": "drop_tables"}, "unknown template"),
        ({"template": "tier_mix", "params": {"sql": "SELECT 1"}}, "not sql"),
        ({"template": "tier_mix", "params": {"kind": "Function"}}, "not kind"),
        ({"template": "no_referrer"}, "needs kind"),
        ({"template": "no_referrer", "params": {"kind": "Banana"}}, "kind must be one of"),
        ({"template": "tier_mix", "params": {"edge_kind": "EATS"}}, "edge_kind must be one of"),
    ],
)
def test_ac2_an_unknown_template_or_param_fails_loud(
    repo: Config, args: dict[str, Any], message: str
) -> None:
    """AC2: the template's own closed parameter set, enforced."""
    with pytest.raises(ValueError, match=message):
        ask(repo, **args)


def test_ac2_the_mcp_schema_is_closed(repo: Config) -> None:
    async def call(arguments: dict[str, Any]) -> None:
        async with Client(build_server(repo)) as client:
            await client.call_tool(compute.NAME, arguments)

    with pytest.raises(ToolError):
        asyncio.run(call({"template": "tier_mix", "sql": "SELECT 1"}))
    with pytest.raises(ToolError):
        asyncio.run(call({"template": "nope"}))


def test_no_template_lists_the_catalogue(repo: Config) -> None:
    answer = ask(repo)
    assert answer["reason"] == "catalogue"
    assert {t["id"] for t in answer["templates"]} == set(compute._RUNNERS)  # 441's eight + 440's
    assert len(answer["templates"]) == 9
    assert all(t["question"].endswith("?") for t in answer["templates"])


def test_ac3_every_row_carries_a_tier_and_the_answer_a_caveat(repo: Config) -> None:
    answer = ask(repo, template="tier_mix")
    assert answer["reason"] == "ok" and answer["rows"]
    assert all(row["tier"] for row in answer["rows"])
    assert "HEURISTIC" in answer["caveat"] and "heuristic_share" in answer["caveat_data"]
    assert answer["total_count"] == len(answer["rows"])


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        ({"template": "tier_mix", "params": {"edge_kind": "DELETES"}}, "no_edge_matches"),
        ({"template": "no_referrer", "params": {"kind": "Trait"}}, "no_symbol_of_that_kind"),
        (
            {"template": "no_referrer", "params": {"kind": "Function", "path_prefix": "nowhere"}},
            "no_symbol_of_that_kind",
        ),
    ],
)
def test_ac3_an_empty_answer_names_why(repo: Config, args: dict[str, Any], reason: str) -> None:
    answer = ask(repo, **args)
    assert (answer["rows"], answer["reason"]) == ([], reason)


def test_ac4_an_absence_names_its_evidence(repo: Config) -> None:
    """AC4: no edge and no mention is a strong candidate; a name in a literal is unknown."""
    answer = ask(repo, template="no_referrer", params={"kind": "Function"})
    levels = {row["qname"]: row["evidence"] for row in answer["rows"]}
    assert levels["lib.a.lonely_ghost"] == "no_edge_no_mention"
    assert levels["lib.a.by_name"] == "no_edge_but_mentioned"
    assert "lib.a.used" not in levels
    assert answer["mention_checks"] == len(answer["rows"])
    assert sum(answer["evidence_levels"].values()) == len(answer["rows"])
    assert "never dead" in answer["caveat"]


def test_total_count_is_the_whole_answer_and_truncated_is_said(repo: Config) -> None:
    whole = ask(repo, template="no_referrer", params={"kind": "Function"})
    cut = ask(repo, template="no_referrer", params={"kind": "Function"}, limit=1)
    assert len(cut["rows"]) == 1 and cut["truncated"] is True
    assert cut["total_count"] == whole["total_count"] >= 2


def _git_repo(root: Path, files: dict[str, str]) -> Path:
    for rel, body in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    for git in (["git", "init", "-q"], ["git", "add", "a.txt"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    return root


def test_word_sites_counts_each_occurrence_tracked_or_not(tmp_path: Path) -> None:
    """The grep arm: every occurrence, untracked files too, a flag-like word stays a word."""
    root = _git_repo(tmp_path, {"a.txt": "foo(foo)\nbar -x\n", "b.txt": "foo\n"})
    sites = gitutil.word_sites(root, ["foo", "-x", "zzz", "two\nlines"], timeout=5)
    assert sites == {
        "foo": [("a.txt", 1), ("a.txt", 1), ("b.txt", 1)],
        "-x": [("a.txt", 2)],
        "zzz": [],
    }


def test_word_sites_cut_by_its_deadline_knows_nothing(tmp_path: Path) -> None:
    root = _git_repo(tmp_path, {"a.txt": "foo\n"})
    assert gitutil.word_sites(root, ["foo"], timeout=0.0) is None


def test_an_absence_the_grep_could_not_check_is_never_strong(
    repo: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R5.6: a grep cut by its deadline leaves `mention_unchecked`, never `no_edge_no_mention`."""
    monkeypatch.setattr(gitutil, "word_sites", lambda *a, **k: None)
    answer = ask(repo, template="no_referrer", params={"kind": "Function"})
    levels = {row["qname"]: row["evidence"] for row in answer["rows"]}
    assert levels["lib.a.lonely_ghost"] == "mention_unchecked"


def test_a_name_used_on_its_own_definition_line_is_mentioned(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "lib").mkdir(parents=True)
    (root / "lib/r.py").write_text("def again(n): return again(n - 1)\n", encoding="utf-8")
    (root / "lib/u.py").write_text("def gone_quiet():\n    return 1\n", encoding="utf-8")
    (root / "notes.txt").write_text("gone_quiet is handled elsewhere\n", encoding="utf-8")
    for git in (["git", "init", "-q"], ["git", "add", "lib"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    config = load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
        },
    )
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    levels = {
        row["qname"]: row["evidence"]
        for row in ask(config, template="no_referrer", params={"kind": "Function"})["rows"]
    }
    assert levels["lib.r.again"] == "no_edge_but_mentioned"  # its only caller is itself
    assert levels["lib.u.gone_quiet"] == "no_edge_but_mentioned"  # named in an untracked file


def test_a_root_prefix_is_no_filter(repo: Config) -> None:
    whole = ask(repo, template="tier_mix")
    for prefix in (".", "./", "/"):
        assert ask(repo, template="tier_mix", params={"path_prefix": prefix}) == whole


def test_the_catalogue_types_every_param(repo: Config) -> None:
    params = {t["id"]: t["params"] for t in ask(repo)["templates"]}
    assert params["no_referrer"]["kind"]["type"] == "node_kind"
    assert "Function" in params["no_referrer"]["kind"]["one_of"]


def test_the_tool_is_read_only_and_answers_from_a_shell(
    repo: Config, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from code_atlas import query
    from code_atlas.main import tool_annotations

    assert tool_annotations(compute.NAME).readOnlyHint is True
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo.root))
    monkeypatch.setenv("CA_PYTHON_CMD", shlex.join([sys.executable, str(PY_ENTRY), "--server"]))
    assert query.main(["compute", "--args", '{"template": "tier_mix"}']) == query.OK
    assert '"template": "tier_mix"' in capsys.readouterr().out


def test_a_dot_directory_prefix_keeps_its_dot(repo: Config) -> None:
    """`.lib` is not `lib`: a prefix loses `./`, never the leading dot of a name."""
    function = {"kind": "Function"}
    plain = ask(repo, template="no_referrer", params={**function, "path_prefix": "lib"})
    assert ask(repo, template="no_referrer", params={**function, "path_prefix": "./lib"}) == plain
    dotted = ask(repo, template="no_referrer", params={**function, "path_prefix": ".lib"})
    assert dotted["rows"] == []


def test_word_sites_ignores_the_users_grep_config_and_case(tmp_path: Path) -> None:
    """A colored or column-numbered grep would drop every site; a mention in another case counts."""
    root = _git_repo(tmp_path, {"a.txt": "FOO()\nfoo\n"})
    for key, value in (("color.ui", "always"), ("color.grep", "always"), ("grep.column", "true")):
        subprocess.run(["git", "config", key, value], cwd=root, check=True, capture_output=True)
    assert gitutil.word_sites(root, ["foo"], timeout=5) == {"foo": [("a.txt", 1), ("a.txt", 2)]}


def test_a_slow_mention_check_costs_its_row_not_the_page(
    repo: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = ComputeSandbox.scalar

    def slow(self: ComputeSandbox, body: str, *args: Any, **kwargs: Any) -> Any:
        if body.startswith("mention."):
            raise ComputeRefused("deadline_exceeded", "over 3 s")
        return real(self, body, *args, **kwargs)

    monkeypatch.setattr(ComputeSandbox, "scalar", slow)
    answer = ask(repo, template="no_referrer", params={"kind": "Function"})
    assert answer["reason"] == "ok"
    assert {row["evidence"] for row in answer["rows"]} == {"mention_unchecked"}
