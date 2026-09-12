"""Task 186 — a zero answer can finally say "this relation is unmodelled for this file's language".

160 shipped the coverage note and wrote its own limit into a docstring: *"the note names what the
index does not cover, **never the subject's own language** (160 out of scope)."* On one language
that costs nothing. On two it is a **confident false negative**:
`include_graph(path=".../thing.ts", direction="imported_by")` said `no_matches` — *"nothing imports
this file"* — while three files did import it, under `IMPORTS`, a kind the tool does not read.

**The inversion worth fixing: the better the adapter, the more confident the wrong answer.** The
honest arm (`relationship_not_modelled`) needs *unlinked* `INCLUDES` as evidence, and an adapter
that emits no `INCLUDES` at all produces none — so the evidence is zero and the tool falls through
to a confident zero.

The verdict is a data question, never a language name (R1.1): *has this language ever emitted any of
the kinds this tool reads, in this index?* Spec-driven fixtures only (R2/R6.2).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from time import perf_counter

import pytest

from code_atlas.config import Config, load_config
from code_atlas.contract import UNMODELLED_REFERENCE_KINDS
from code_atlas.indexer import full_build
from code_atlas.store import EMITTED_KINDS_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import find_references, include_graph
from code_atlas.tools.coverage import relation_unmodelled_for_language
from code_atlas.tools.nav_result import (
    NAV_REASONS,
    REASON_NO_MATCHES,
    REASON_PROXIMITY_CANDIDATES,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    REASON_RELATIONSHIP_NOT_MODELLED,
    TRY_INSTEAD_FIND_REFERENCES,
    TRY_INSTEAD_HINT_RELATION_CARRIED_BY_ANOTHER_KIND,
)
from tests.php_adapter_cli import CLI as PHP_CLI
from tests.php_adapter_cli import needs_php
from tests.ts_adapter_cli import CLI as TS_CLI
from tests.ts_adapter_cli import needs_node

# A TS file three other fixture files import — the false-negative subject.
TS_IMPORTED = "src/models.ts"
# A PHP file nothing includes: the genuine zero that must NOT be collapsed into the new reason.
PHP_NOT_INCLUDED = "src/namespaced.php"


def _index(root: Path, cli, patterns: tuple[str, ...]) -> Config:
    src = root / "src"
    src.mkdir()
    for pattern in patterns:
        for directory in (cli.fixtures_dir, cli.fixtures_dir / "resolve"):
            for fixture in sorted(directory.glob(pattern)):
                shutil.copy(fixture, src / fixture.name)
    argv = ", ".join(f"'{part}'" for part in (*cli.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(
        f"[adapter_cmd]\n{cli.name} = [{argv}]\n", encoding="utf-8"
    )
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    db_path = root / ".code-atlas" / "graph.db"
    config = load_config(root, {"CA_WORKERS": "1", "CA_DB_PATH": str(db_path)})
    with GraphStore(db_path) as store:
        assert full_build(config, store).nodes > 0
    return config


@pytest.fixture(scope="module")
def ts_index(tmp_path_factory: pytest.TempPathFactory) -> Config:
    return _index(tmp_path_factory.mktemp("ts186"), TS_CLI, ("*.ts", "*.tsx", "*.js"))


@pytest.fixture(scope="module")
def php_index(tmp_path_factory: pytest.TempPathFactory) -> Config:
    return _index(tmp_path_factory.mktemp("php186"), PHP_CLI, ("*.php",))


@needs_node
def test_the_false_negative_is_reproduced_then_named(ts_index: Config) -> None:
    """AC1: the subject IS imported by three files, and the old answer was a confident zero."""
    with GraphStore(ts_index.db_path) as store:
        importers = [
            str(row[0])
            for row in store._conn.execute(
                "SELECT source_qname FROM edges WHERE kind = 'IMPORTS' AND target_raw = ?",
                (TS_IMPORTED,),
            )
        ]
        assert len(importers) >= 2, f"the fixture must exhibit the false negative, got {importers}"
        assert store.language_emits_none_of("typescript", ("INCLUDES",)) is True

    payload = include_graph.create(ts_index)(path=TS_IMPORTED, direction="imported_by")
    assert payload["results"] == []
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    assert payload["reason"] != REASON_NO_MATCHES


@needs_node
def test_the_no_route_became_a_route_once_a_tool_could_answer(ts_index: Config) -> None:
    """AC6 / R5.4 clause (c), **revised by 188** — and the revision is why the rule is worth having.

    186 emitted a hint and NO route on a measurement: `find_references` on this file returned zero
    rows, because TS `IMPORTS` carried a resolved path in `target_raw` that nothing linked. 188
    linked it, so the same measurement now returns rows and clause (c) says name the tool. The
    no-route branch is still live for a language that emits neither kind, pinned in
    `tests/test_imports_link_the_file_they_name.py`.
    """
    payload = include_graph.create(ts_index)(path=TS_IMPORTED, direction="imported_by")
    assert payload["try_instead"] == TRY_INSTEAD_FIND_REFERENCES
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_RELATION_CARRIED_BY_ANOTHER_KIND

    routed = find_references.create(ts_index)(qname=TS_IMPORTED)
    assert routed["results"], "the route must answer, or 186's no-route was the right call"


@needs_php
def test_a_genuine_php_zero_is_still_no_matches(php_index: Config) -> None:
    """AC2: the two are not collapsed — PHP emits INCLUDES, so an empty answer means empty."""
    with GraphStore(php_index.db_path) as store:
        assert store.language_emits_none_of("php", ("INCLUDES",)) is False
    payload = include_graph.create(php_index)(path=PHP_NOT_INCLUDED, direction="imported_by")
    assert payload["results"] == []
    assert payload["reason"] == REASON_NO_MATCHES


def test_unlinked_evidence_still_wins_over_the_language_verdict(tmp_path: Path) -> None:
    """AC3 (160/065): the existing arm keeps precedence, proven on the case where both could fire.

    Seeded directly, because it needs a shape no single-language fixture has: a file of a language
    that emits **no** `INCLUDES` which is nevertheless mentioned by another language's unlinked
    include text. The relationship genuinely exists (from the other language), so saying
    "unmodelled for this file's language" would be the wrong answer — and the `elif` ordering makes
    that structural rather than incidental. Generic names, no real language (R2).
    """
    db_path = tmp_path / ".code-atlas" / "graph.db"
    (tmp_path / "src").mkdir(parents=True)
    for path in ("src/subject.bb", "src/includer.aa"):
        (tmp_path / path).write_text("# planted\n", encoding="utf-8")
    with GraphStore(db_path) as store:
        store.upsert_file("src/subject.bb", "d1", "second")
        store.upsert_file("src/includer.aa", "d2", "fake")
        store.replace_file_rows(
            "src/subject.bb",
            [{"kind": "File", "name": "subject.bb", "qualified_name": "src/subject.bb",
              "file_path": "src/subject.bb", "line_start": 1}],
            [],
        )
        store.replace_file_rows(
            "src/includer.aa",
            [{"kind": "File", "name": "includer.aa", "qualified_name": "src/includer.aa",
              "file_path": "src/includer.aa", "line_start": 1}],
            [{"kind": "INCLUDES", "source_qname": "src/includer.aa", "target_raw": "subject.bb",
              "file_path": "src/includer.aa", "line": 1, "confidence_tier": "DYNAMIC"}],
        )
        languages = store.edge_language_census()
        store.set_meta(EMITTED_KINDS_BY_LANGUAGE_KEY, json.dumps(languages.kinds, sort_keys=True))
        # The premise: `second` emits no INCLUDES, so the language arm COULD fire here.
        assert store.language_emits_none_of("second", ("INCLUDES",)) is True
        assert store.language_emits_none_of("fake", ("INCLUDES",)) is False

    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    payload = include_graph.create(config)(path="src/subject.bb", direction="imported_by")
    assert payload["results"] == []
    assert payload["reason"] == REASON_RELATIONSHIP_NOT_MODELLED, (
        "unlinked evidence outranks the language verdict — the relationship really does exist"
    )
    assert "try_instead" not in payload


@needs_node
def test_find_references_fires_when_references_alone_is_unmodelled(ts_index: Config) -> None:
    """232 — IMPORTS in the set must not mask a never-emitted REFERENCES.

    Rewrite the stamp so typescript keeps IMPORTS but drops REFERENCES; a zero answer then
    carries relation_unmodelled_for_language (authoritative: false), not a genuine no_matches.
    The per-language census is a measured claim, so it outranks 255's widened evidence arm —
    which is why that arm reads the qname only and runs after this one.
    """
    with GraphStore(ts_index.db_path) as store:
        stamped = store.stamped_emitted_kinds_by_language()
        assert stamped is not None
        kinds = [k for k in stamped["typescript"] if k != "REFERENCES"]
        if "IMPORTS" not in kinds:
            kinds.append("IMPORTS")
        store.set_meta(EMITTED_KINDS_BY_LANGUAGE_KEY, json.dumps({"typescript": kinds}))
        assert store.language_emits_none_of("typescript", UNMODELLED_REFERENCE_KINDS) is False
        assert store.language_emits_none_of("typescript", ("REFERENCES",)) is True

    payload = find_references.create(ts_index)(qname="src/class_heritage.ts::Circle::draw")
    if payload.get("total_count", 0) == 0:
        assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
        assert payload.get("authoritative") is False


@needs_php
def test_a_pre_186_index_says_nothing_rather_than_guessing(php_index: Config) -> None:
    """AC5 / R5.6: with no stamp the index cannot support the claim, so it does not make it."""
    with GraphStore(php_index.db_path) as store:
        store.delete_meta(EMITTED_KINDS_BY_LANGUAGE_KEY)
        assert store.stamped_emitted_kinds_by_language() is None
        assert store.language_emits_none_of("php", ("INCLUDES",)) is None
        assert not relation_unmodelled_for_language(
            store, file_path=PHP_NOT_INCLUDED, kinds=("ZZZ",)
        )

    payload = include_graph.create(php_index)(path=PHP_NOT_INCLUDED, direction="imported_by")
    assert payload["reason"] == REASON_NO_MATCHES


@needs_php
def test_an_unindexed_file_and_an_unknown_language_say_nothing(php_index: Config) -> None:
    """R5.6's other two holes: no `files` row, and a language the stamp never named."""
    with GraphStore(php_index.db_path) as store:
        assert store.language_of_file("src/not_indexed.php") is None
        assert not relation_unmodelled_for_language(
            store, file_path="src/not_indexed.php", kinds=("INCLUDES",)
        )
        assert store.language_emits_none_of("never_built", ("INCLUDES",)) is None


@needs_php
def test_a_confident_answer_is_byte_identical(php_index: Config) -> None:
    """AC4 (061): the verdict rides an EMPTY answer only — a non-empty one is untouched."""
    payload = include_graph.create(php_index)(path="src/include_require.php", direction="imports")
    assert payload["results"], "the fixture must have resolved includes for this to mean anything"
    assert "reason" not in payload, "an omitted reason is the confident shape (061)"
    assert "try_instead_hint" not in payload


@needs_php
def test_the_verdict_is_a_stamp_read_not_a_group_by(php_index: Config) -> None:
    """The cost constraint inherited from 183: a meta read per answer, never a scan."""
    with GraphStore(php_index.db_path) as store:
        traced: list[str] = []
        store._conn.set_trace_callback(traced.append)
        store.language_emits_none_of("php", ("INCLUDES",))
        store._conn.set_trace_callback(None)
    assert len(traced) == 1, traced
    assert "GROUP BY" not in traced[0]

    tool = include_graph.create(php_index)
    started = perf_counter()
    for _ in range(100):
        tool(path=PHP_NOT_INCLUDED, direction="imported_by")
    per_call_ms = (perf_counter() - started) / 100 * 1000
    assert per_call_ms < 25.0, f"{per_call_ms:.3f} ms per empty inbound answer"


def test_the_new_reason_joins_the_vocabulary_once() -> None:
    """AC7/R3: nav vocabulary, one definition site, and it is a real member of NAV_REASONS."""
    assert REASON_RELATION_UNMODELLED_FOR_LANGUAGE in NAV_REASONS
    assert NAV_REASONS[-1] == REASON_PROXIMITY_CANDIDATES
    assert len(set(NAV_REASONS)) == len(NAV_REASONS)


@needs_php
@needs_node
def test_one_rule_two_consumers(ts_index: Config, php_index: Config) -> None:
    """R1.8: both vocabulary-gated tools route through the same helper, not two copies."""
    import subprocess as sp

    root = Path(__file__).resolve().parent.parent
    found = sp.run(
        ["grep", "-rl", "def relation_unmodelled_for_language", "code_atlas/"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert found == ["code_atlas/tools/coverage.py"]
    callers = sp.run(
        ["grep", "-rl", "relation_unmodelled_for_language(", "code_atlas/tools/"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert sorted(callers) == [
        "code_atlas/tools/coverage.py",
        "code_atlas/tools/find_references.py",
        "code_atlas/tools/include_graph.py",
    ]
