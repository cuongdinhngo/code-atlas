"""``find_references`` — every resolved edge targeting a qname (§12)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import edge_hit, empty_nav, nav_result

NAME = "find_references"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_references(qname: str, detail_level: DetailLevel = "standard") -> dict[str, object]:
        """All edges whose resolved target is ``qname`` (any kind), with confidence tiers."""
        if not config.db_path.is_file():
            return empty_nav(qname, detail_level=detail_level, db_path=str(config.db_path))
        with GraphStore(config.db_path) as store:
            edges = store.edges_by_target(qname, limit=config.max_results)
            results = [edge_hit(edge) for edge in edges]
        return nav_result(qname, results, detail_level=detail_level, db_path=str(config.db_path))

    return find_references
