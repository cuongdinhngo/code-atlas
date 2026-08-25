"""Task 019: cross-file import resolution — the RESOLVED win adapter #2 exists to prove.

full_build over a tiny TS project; a direct ESM import and a re-export barrel both link a cross-file
NEW to the *defining* module at RESOLVED. Drives the real indexer + resolver (not just the adapter),
so it needs Node; the full suite runs it in Docker.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from tests.ts_adapter_cli import ENTRY, FIXTURES, NODE, needs_node

RESOLVE = FIXTURES / "resolve"


@needs_node
def test_cross_file_new_resolves_to_the_defining_module(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    fixtures = ("models.ts", "app.ts", "barrel.ts", "consumer.ts", "service.ts", "boot.ts")
    for name in fixtures + ("dual.ts", "dual.js", "uses_dual.ts"):
        shutil.copy(RESOLVE / name, src / name)
    # The launch argv goes in the project file as a list (taken verbatim): a Windows node path holds
    # spaces, which a CA_*_CMD env string cannot survive the platform split intact (config.py:257).
    (tmp_path / ".code-atlas.toml").write_text(
        f"[adapter_cmd]\ntypescript = ['{NODE}', '{ENTRY}', '--server']\n", encoding="utf-8"
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)

    db_path = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {"CA_WORKERS": "1", "CA_DB_PATH": str(db_path)})
    with GraphStore(db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
        assert report.parsed == 9

        # Direct ESM import: app.ts `new User()` links to models.ts::User at RESOLVED.
        app_new = store.edges_by_source("src/app.ts::make", kinds=("NEW",), limit=10)
        assert len(app_new) == 1
        assert app_new[0]["target_raw"] == "src/models.ts::User"
        assert app_new[0]["target_qname"] == "src/models.ts::User"
        assert app_new[0]["confidence_tier"] == "RESOLVED"

        # Through the barrel: consumer's `new User()` targets barrel.ts::User, which the ALIASES
        # edge redirects to the defining models.ts::User — RESOLVED, not stopped at the barrel.
        con_new = store.edges_by_source("src/consumer.ts::build", kinds=("NEW",), limit=10)
        assert len(con_new) == 1
        assert con_new[0]["target_raw"] == "src/barrel.ts::User"
        assert con_new[0]["target_qname"] == "src/models.ts::User"
        assert con_new[0]["confidence_tier"] == "RESOLVED"

        # A *named* default export: the importing file only knows `default`, so the declaration's
        # `::default` alias is the only path from `new Service()` to the class that declares it.
        boot_new = store.edges_by_source("src/boot.ts::boot", kinds=("NEW",), limit=10)
        assert len(boot_new) == 1
        assert boot_new[0]["target_raw"] == "src/service.ts::default"
        assert boot_new[0]["target_qname"] == "src/service.ts::Service"
        assert boot_new[0]["confidence_tier"] == "RESOLVED"

        # A member call carries only the method name, so the adapter claims HEURISTIC — the tier
        # that switches on the core's name-only fallback. Without it the edge links to nothing.
        app_calls = store.edges_by_source("src/app.ts::make", kinds=("CALLS",), limit=10)
        assert len(app_calls) == 1
        assert app_calls[0]["target_raw"] == "greet"
        assert app_calls[0]["target_qname"] == "src/models.ts::User::greet"
        assert app_calls[0]["confidence_tier"] == "HEURISTIC"

        # A NodeNext `./dual.js` specifier names the TypeScript source, which wins over the compiled
        # `dual.js` sitting beside it — otherwise every import in such a repo lands on build output.
        dual_new = store.edges_by_source("src/uses_dual.ts::pick", kinds=("NEW",), limit=10)
        assert len(dual_new) == 1
        assert dual_new[0]["target_raw"] == "src/dual.ts::Widget"
        assert dual_new[0]["confidence_tier"] == "RESOLVED"
