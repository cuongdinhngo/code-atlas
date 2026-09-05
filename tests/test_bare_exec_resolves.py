"""Task 214 — a bare EXEC links when the Function is unique; residual zeros stay honest.

Proves at the find_callers consumer (R6.9): adapter emit stays bare (R3.3); the core links a
unique same-language Function; ambiguity refuses; a non-dbo-only repo is not mis-linked to dbo.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
)
from tests.sql_adapter_cli import CLI, needs_node

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sql" / "bare_exec"

pytestmark = needs_node


def _index(root: Path, fixture_name: str) -> Config:
    src = root / "src"
    src.mkdir()
    shutil.copy(FIXTURES / fixture_name, src / fixture_name)
    argv = ", ".join(f"'{part}'" for part in (*CLI.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(
        f"[adapter_cmd]\nsql = [{argv}]\n", encoding="utf-8"
    )
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    db_path = root / ".code-atlas" / "graph.db"
    config = load_config(root, {"CA_WORKERS": "1", "CA_DB_PATH": str(db_path)})
    with GraphStore(db_path) as store:
        assert full_build(config, store).nodes > 0
    return config


def test_bare_exec_links_to_unique_dbo_proc(tmp_path: Path) -> None:
    """AC1 — EXEC/EXECUTE BareTarget against a single dbo.BareTarget links."""
    config = _index(tmp_path, "unique_dbo.sql")
    payload = find_callers.create(config)("dbo.BareTarget", detail_level="minimal")
    assert payload["reason"] != REASON_NO_MATCHES
    assert payload["total_count"] >= 2  # EXEC + EXECUTE callers
    files = {hit["file"] for hit in payload["results"]}
    assert any("unique_dbo.sql" in path for path in files)


def test_ambiguous_bare_exec_does_not_silently_link(tmp_path: Path) -> None:
    """AC2 — two Twins; bare EXEC Twin must not pick one; competition is visible."""
    config = _index(tmp_path, "ambiguous_twin.sql")
    for qname in ("dbo.Twin", "sales.Twin"):
        payload = find_callers.create(config)(qname, detail_level="minimal")
        assert payload["total_count"] == 0, f"{qname} silently linked a twin"
        siblings = payload.get("sibling_definitions")
        assert siblings, f"{qname} must surface the competing Function (AC2 visibility)"
        assert len(siblings) >= 1


def test_residual_unlinked_calls_say_relation_unmodelled_not_no_matches(
    tmp_path: Path,
) -> None:
    """AC3 — unlinked bare EXEC residual is relation_unmodelled_for_language, never no_matches."""
    config = _index(tmp_path, "ambiguous_twin.sql")
    payload = find_callers.create(config)("dbo.Twin", detail_level="minimal")
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    assert payload["reason"] != REASON_NO_MATCHES
    assert payload["total_count"] == 0


def test_non_dbo_only_repo_is_not_mislinked_to_dbo(tmp_path: Path) -> None:
    """AC4 — sales.OnlyOne is the sole declaration; bare EXEC links there, not to dbo."""
    config = _index(tmp_path, "non_dbo_only.sql")
    with GraphStore(config.db_path) as store:
        assert store.nodes_by_qualified_name("dbo.OnlyOne", limit=2) == []
        sales = store.nodes_by_qualified_name("sales.OnlyOne", limit=2)
        assert len(sales) == 1
    payload = find_callers.create(config)("sales.OnlyOne", detail_level="minimal")
    assert payload["total_count"] >= 1
    assert payload["reason"] != REASON_NO_MATCHES
