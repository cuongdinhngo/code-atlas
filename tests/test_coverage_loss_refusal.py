"""Task 203 scope 3: a full build that would discard a covered language refuses first.

Field run, 2026-09-01: enabling the T-SQL adapter forced a full rebuild, and the shell route
resolves adapters from `.code-atlas.toml` plus env. Had `CA_PHP_CMD` — which lived only in the MCP
server's env block — not been exported by hand, that run would have written an index with all
19,155 PHP files silently dropped, overwriting the `covered_languages` stamp that was the only
record they had ever been there.

Spec-driven (R6.2/R2): the two languages are the fixture adapter's arbitrary tokens `fake` and
`second`, never a real language name.
"""

from __future__ import annotations

import shlex
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import adapter
from code_atlas.config import Config, load_config
from code_atlas.indexer import COVERAGE_LOSS
from code_atlas.store import COVERED_LANGUAGES_KEY, GraphStore
from code_atlas.tools.build_or_update_index import create as build_tool

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


def fake_cmd(mode: str = "ok") -> str:
    return shlex.join([sys.executable, str(FAKE), mode])


@pytest.fixture(autouse=True)
def only_these_adapters_ship(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ship exactly the two fixture adapters, so 159's unwired note cannot muddy this."""
    root = tmp_path / "shipped"
    for name in ("fake", "second"):
        (root / name / "src").mkdir(parents=True)
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", root)


@pytest.fixture
def repo(tmp_path: Path) -> Iterator[Path]:
    for rel in ("lib/core.aa", "dep/a.aa", "dep/cross.cc", "dep/extends_b.cc"):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
    yield tmp_path


def config_for(root: Path, env: dict[str, str]) -> Config:
    return load_config(root, {**env, "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")})


BOTH = {"CA_WORKERS": "1", "CA_FAKE_CMD": fake_cmd(), "CA_SECOND_CMD": fake_cmd("second")}
ONE = {"CA_WORKERS": "1", "CA_FAKE_CMD": fake_cmd()}


def languages(config: Config) -> dict[str, int]:
    with GraphStore(config.db_path) as store:
        return dict(
            store._conn.execute("SELECT language, COUNT(*) FROM files GROUP BY language")
        )


def covered(config: Config) -> str:
    with GraphStore(config.db_path) as store:
        return store.get_meta(COVERED_LANGUAGES_KEY) or ""


def build_both(repo: Path) -> Config:
    config = config_for(repo, BOTH)
    build_tool(config)(full=True)
    assert covered(config) == "fake,second", "the fixture must first cover both languages"
    return config


def test_a_full_build_refuses_to_discard_a_covered_language(repo: Path) -> None:
    """AC4, red before the fix: today this returns `mode: full` and drops the `second` files."""
    build_both(repo)
    narrowed = config_for(repo, ONE)

    result = build_tool(narrowed)(full=True)

    assert result["mode"] == "refused"
    assert result["reason"] == COVERAGE_LOSS
    assert result["lost_languages"] == ["second"]
    assert result["performed"] is False


def test_the_refusal_leaves_the_index_untouched(repo: Path) -> None:
    """AC4's second half: asserted on the INDEX, not only on the payload."""
    config = build_both(repo)
    before = languages(config)
    narrowed = config_for(repo, ONE)

    build_tool(narrowed)(full=True)

    assert languages(narrowed) == before == {"fake": 2, "second": 2}
    assert covered(narrowed) == "fake,second", "the stamp is the only record — it must survive"


def test_the_refusal_names_no_route_because_no_tool_can_answer(repo: Path) -> None:
    """R5.4c: naming a tool that cannot configure an adapter is worse than naming none."""
    build_both(repo)

    result = build_tool(config_for(repo, ONE))(full=True)

    assert "route" not in result
    assert "adapter_cmd" in str(result["hint"])
    assert result["in_band_option"] == "allow_coverage_loss=true"


def test_the_caller_can_opt_in_to_the_narrowing(repo: Path) -> None:
    """A deliberate narrowing stays possible — the refusal is a guard, not a wall."""
    build_both(repo)
    narrowed = config_for(repo, ONE)

    result = build_tool(narrowed)(full=True, allow_coverage_loss=True)

    assert result["mode"] == "full"
    assert languages(narrowed) == {"fake": 2}
    assert covered(narrowed) == "fake"


def test_a_first_build_has_nothing_to_lose(repo: Path) -> None:
    """No stamp means no covered language, so the guard is silent rather than blocking (R5.6)."""
    result = build_tool(config_for(repo, ONE))(full=True)

    assert result["mode"] == "full"
    assert covered(config_for(repo, ONE)) == "fake"


def test_a_widening_run_is_never_refused(repo: Path) -> None:
    """Adding an adapter loses nothing, so the guard must not fire on the direction that helps."""
    config = config_for(repo, ONE)
    build_tool(config)(full=True)
    assert covered(config) == "fake"

    widened = config_for(repo, BOTH)
    result = build_tool(widened)(full=True)

    assert result["mode"] == "full"
    assert covered(widened) == "fake,second"


def test_an_escalating_incremental_is_refused_too(repo: Path, monkeypatch) -> None:
    """The path a ticket-blind review found: `full=False` reaches `full_build` anyway.

    `_require_unchanged_scope` raises `_ScopeChanged` when the announced suffix set differs —
    including when it has **narrowed**, which is exactly "an adapter went missing". The handler
    calls `full_build` directly, so a guard sitting only in front of an explicit `--full` never
    sees the most common call shape. Red before the guard moved into `full_build`.
    """
    config = build_both(repo)
    before = languages(config)
    # A commit stamp is what lets `_run` attempt the incremental path at all.
    monkeypatch.setattr(
        "code_atlas.tools.build_or_update_index.gitutil.head_commit", lambda _root: "deadbeef"
    )
    monkeypatch.setattr(
        "code_atlas.tools.build_or_update_index.gitutil.changed_paths",
        lambda _root, _last: ["dep/cross.cc"],
    )
    with GraphStore(config.db_path) as store:
        store.set_meta("last_commit", "cafebabe")

    narrowed = config_for(repo, ONE)
    result = build_tool(narrowed)(full=False)

    assert result["mode"] == "refused", result
    assert result["reason"] == COVERAGE_LOSS
    assert languages(narrowed) == before, "an escalating incremental must not discard it either"
    assert covered(narrowed) == "fake,second"


def test_the_comparison_folds_case_on_both_sides(repo: Path) -> None:
    """`extensions` is lowercased by the contract; the announced `name` is not, and config keys
    always are. Folding one side only reports a false loss for a configured language."""
    build_both(repo)
    with GraphStore(config_for(repo, BOTH).db_path) as store:
        store.set_meta(COVERED_LANGUAGES_KEY, "Fake,SECOND")

    result = build_tool(config_for(repo, BOTH))(full=True)

    assert result["mode"] == "full", "both languages ARE configured — this must not refuse"


def test_a_refused_escalation_does_not_even_mark_the_index_incomplete(repo: Path) -> None:
    """The refusal must be free on EVERY path, not only on the `--full` one.

    `incremental_update` stamps `build_complete = 0` before it reaches `full_build`, so a guard
    that only lived at the write boundary left a refused escalation having already marked the
    index incomplete — 202's `staleness: incomplete` for a build that never ran. Found by a
    ticket-blind review of the first version of this guard.
    """
    config = build_both(repo)
    with GraphStore(config.db_path) as store:
        before = store.get_meta("build_complete")
    assert before == "1"

    narrowed = config_for(repo, ONE)
    assert build_tool(narrowed)(full=True)["mode"] == "refused"

    with GraphStore(narrowed.db_path) as store:
        assert store.get_meta("build_complete") == "1", "a refusal must write nothing at all"
