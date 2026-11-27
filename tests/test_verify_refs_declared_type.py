"""Task 456 — a dotted reference follows a field's, property's or method's declared type.

`Timeline.theme.vars` names `vars` on the class `theme` is declared as, not on the property, so the
walk reads the member's type and asks there. Built through the real Python and TypeScript adapters:
the type comes from the edges each one emits for an annotation, never from the core reading one.
"""

from __future__ import annotations

import shlex
import sys
from collections.abc import Iterator
from typing import Any

import pytest

from code_atlas import doc_refs
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from tests.python_adapter_cli import ENTRY as PY_ENTRY
from tests.test_verify_refs import git, write
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

pytestmark = needs_node

IR = (
    "class Palette:\n    name: str = 'x'\n\n\n"
    "class Theme:\n    vars: dict = {}\n    palette: Palette\n    old: int = 0\n\n\n"
    "class Diagram:\n    nodes: list = []\n\n\n"
    "class Other:\n    vars: int = 0\n\n\n"
    "class Timeline:\n    theme: Theme\n    diagram: Diagram | None = None\n    meta: dict = {}\n"
    "    either: Theme | Other\n\n"
    "    @property\n    def ctx(self) -> Theme:\n        return self.theme\n\n"
    "    def run(self):\n        return 1\n\n\n"
    "class Shelf:\n    box: Theme\n\n\n"
    "class Crate:\n    box: Diagram\n"
)
TS = (
    "export class Style {\n  color = 'red';\n}\n\n"
    "export class Shot {\n  style: Style | null = null;\n}\n"
)
DOC = (
    "- `Timeline.theme.vars` · `Timeline.diagram.nodes` · `Timeline.ctx.vars`\n"
    "- `Timeline.theme.palette.name` · `Timeline.meta.keys` · `Timeline.either.vars`\n"
    "- `Timeline.theme.old` · `Timeline.theme.invented` · `Timeline.run.later`\n"
    "- `Shot.style.color` · `box.vars`\n"
)


@pytest.fixture(scope="module")
def found(tmp_path_factory: pytest.TempPathFactory) -> Iterator[doc_refs.Scan]:
    root = tmp_path_factory.mktemp("declared")
    write(root, {"lib/ir.py": IR, "web/ir.ts": TS, "CLAUDE.md": DOC})
    (root / ".gitignore").write_text(".code-atlas/\n", encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    write(root, {"lib/ir.py": IR.replace("    old: int = 0\n", "")})
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "drop Theme.old")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path_factory.mktemp("home")))
        config: Config = load_config(root, {
            "CA_WORKERS": "1",
            "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
            "CA_TYPESCRIPT_CMD": shlex.join([str(NODE), str(TS_ENTRY), "--server"]),
        })
        with GraphStore(config.db_path) as store:
            assert full_build(config, store).failed == 0
            yield doc_refs.scan(config, store)


def row(found: doc_refs.Scan, ref: str) -> dict[str, Any]:
    hits = [r for r in found.rows if r["ref"] == ref]
    assert len(hits) == 1, (ref, hits)
    return hits[0]


@pytest.mark.parametrize(
    ("ref", "member_of"),
    [
        ("Timeline.theme.vars", "lib.ir.Theme"),  # field -> class -> member
        ("Timeline.diagram.nodes", "lib.ir.Diagram"),  # `X | None`
        ("Timeline.ctx.vars", "lib.ir.Theme"),  # a property's return type
        ("Timeline.theme.palette.name", "lib.ir.Palette"),  # every segment
        ("Shot.style.color", "web/ir.ts::Style"),  # TypeScript `Style | null`
    ],
)
def test_a_typed_container_resolves_the_member_on_its_type(
    found: doc_refs.Scan, ref: str, member_of: str
) -> None:
    got = row(found, ref)
    assert (got["state"], got["reason"]) == ("ok", "via_declared_type"), got
    assert got["type"] == member_of
    assert str(got["site"]["qname"]).startswith(member_of)
    assert not got["actionable"]


@pytest.mark.parametrize(
    ("ref", "state", "reason", "actionable"),
    [
        ("Timeline.meta.keys", "unknown", "untyped_container", False),  # `dict`: not indexed
        ("Timeline.run.later", "unknown", "untyped_container", False),  # no return annotation
        ("Timeline.either.vars", "unknown", "several_container_types", False),
        ("box.vars", "unknown", "several_container_types", False),  # two `box`, two types
        # A member the type does not declare keeps today's verdicts, read on the type's file.
        ("Timeline.theme.old", "gone", "missing_on_live_container", True),
        ("Timeline.theme.invented", "unknown", "not_declared_on_container", False),
    ],
)
def test_an_untyped_or_missing_member_is_never_a_false_ok(
    found: doc_refs.Scan, ref: str, state: str, reason: str, actionable: bool
) -> None:
    got = row(found, ref)
    assert (got["state"], got["reason"], got["actionable"]) == (state, reason, actionable), got
    if reason in ("missing_on_live_container", "not_declared_on_container"):
        assert got["container"] == "lib.ir.Theme"


def test_the_new_row_fields_are_untrusted() -> None:
    assert {"rows[].type", "rows[].types"} <= set(doc_refs.UNTRUSTED)
