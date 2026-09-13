"""Test vs production role — adapter ``is_test`` first, path convention fallback (130 / 262)."""

from __future__ import annotations

from collections.abc import Iterable, MutableMapping
from typing import Literal

from code_atlas.onboarding.layers import responsibility_of_segment
from code_atlas.onboarding.reachability import LAYER_TESTS

TestRoleSource = Literal["adapter", "path_convention"]


def path_indicates_test(file_path: str) -> bool:
    """Same rule as ``class_diagram._test_path`` — path segments only, never framework lists."""
    if not file_path:
        return False
    return any(
        responsibility_of_segment(segment) == LAYER_TESTS
        for segment in file_path.split("/")[:-1]
    )


def apply_test_role(nodes: Iterable[MutableMapping[str, object]]) -> None:
    """Fill ``is_test`` from the path when the adapter did not emit it (R2: convention, not names).

    Called where rows are *decided*, never inside ``store.py`` — classifying is not persisting
    (R1.4). An adapter that emits the field always wins; this only fills the gap.
    """
    for node in nodes:
        if "is_test" in node:
            continue
        if path_indicates_test(str(node.get("file_path") or "")):
            node["is_test"] = 1


def stored_test_source(is_test: int, file_path: str) -> TestRoleSource | None:
    """Name how one persisted row was decided — adapter field, or the path convention above."""
    if not is_test:
        return None
    return "path_convention" if path_indicates_test(file_path) else "adapter"


def aggregate_test_count_source(
    sources: Iterable[TestRoleSource | None],
) -> TestRoleSource | Literal["mixed"] | None:
    """One label for how a whole ``test_count`` was decided; ``mixed`` when the rows disagree."""
    decided = {source for source in sources if source is not None}
    if not decided:
        return None
    if len(decided) == 1:
        return decided.pop()
    return "mixed"
