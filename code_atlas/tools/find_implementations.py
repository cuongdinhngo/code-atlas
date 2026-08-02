"""``find_implementations`` — direct EXTENDS/IMPLEMENTS subtypes (§12)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import edge_hit, empty_nav, nav_result

NAME = "find_implementations"

DetailLevel = Literal["minimal", "standard"]

_EXTENDS = "EXTENDS"
_IMPLEMENTS = "IMPLEMENTS"
IMPL_KINDS: tuple[str, ...] = (_EXTENDS, _IMPLEMENTS)


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_implementations(
        qname: str, detail_level: DetailLevel = "standard"
    ) -> dict[str, object]:
        """Direct subtypes that EXTEND or IMPLEMENT ``qname`` (not transitive — see impact/017)."""
        if not config.db_path.is_file():
            return empty_nav(qname, detail_level=detail_level, db_path=str(config.db_path))
        with GraphStore(config.db_path) as store:
            edges = store.edges_by_target(qname, kinds=IMPL_KINDS, limit=config.max_results)
            results = [edge_hit(edge) for edge in edges]
        return nav_result(qname, results, detail_level=detail_level, db_path=str(config.db_path))

    return find_implementations
