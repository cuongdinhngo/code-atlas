"""``build_or_update_index`` — run a build and report what it did (§12).

``full`` is accepted and echoed, but only a full build exists today (``indexer.incremental_update``
lands in task 016), so the response names the mode that actually ran rather than the one asked for.
The store is opened here, inside the call, because the caller's thread owns the connection (R4.3).
"""

import time
from collections.abc import Callable
from dataclasses import asdict
from typing import Literal

from code_atlas.config import Config
from code_atlas.indexer import BuildReport, full_build
from code_atlas.store import BUILT_AT_KEY, LAST_COMMIT_KEY, GraphStore

NAME = "build_or_update_index"

DetailLevel = Literal["minimal", "standard"]

FULL = "full"


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def build_or_update_index(
        full: bool = False, detail_level: DetailLevel = "standard"
    ) -> dict[str, object]:
        """Index this repo and return the counts and elapsed time. Only full builds exist so far."""
        started = time.monotonic()
        with GraphStore(config.db_path) as store:
            report = full_build(config, store)
            elapsed = round(time.monotonic() - started, 3)
            return _result(store, config, report, full, elapsed, detail_level)

    return build_or_update_index


def _result(
    store: GraphStore,
    config: Config,
    report: BuildReport,
    full: bool,
    elapsed: float,
    detail_level: DetailLevel,
) -> dict[str, object]:
    # The counts come off the report itself, so a field added there reaches clients without an edit.
    result: dict[str, object] = {
        "mode": FULL,
        "requested_full": full,
        **asdict(report),
        "seconds": elapsed,
    }
    if detail_level == "minimal":
        return result
    return result | {
        "last_commit": store.get_meta(LAST_COMMIT_KEY),
        "built_at": store.get_meta(BUILT_AT_KEY),
        "db_path": str(config.db_path),
    }
