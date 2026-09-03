"""206 — onboarding can be scoped to the tree the reader works in.

The proving test runs ``generate_onboarding`` over a two-tree fixture where an in-scope app file
depends on a legacy file. Declaring ``working_roots = ["app"]`` must keep the tour inside ``app``
while still letting the generated map cite the out-of-scope neighbour as context.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from code_atlas.tools import generate_onboarding
from tests.test_generate_onboarding import _out
from tests.test_nav_tools import db_config, edge, node, seed_file


def _scoped_repo(root: Path):
    from code_atlas.store import GraphStore

    config = db_config(root)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            "app/controllers/Entry.aa",
            [node("Method", "show", "\\App\\Entry::show", "app/controllers/Entry.aa")],
            [
                edge(
                    "CALLS",
                    "\\App\\Entry::show",
                    "\\App\\Feature",
                    "app/controllers/Entry.aa",
                    target_qname="\\App\\Feature",
                )
            ],
            root=root,
        )
        seed_file(
            store,
            "app/services/Feature.aa",
            [node("Class", "Feature", "\\App\\Feature", "app/services/Feature.aa")],
            [
                edge(
                    "CALLS",
                    "\\App\\Feature",
                    "\\Legacy\\Gate",
                    "app/services/Feature.aa",
                    target_qname="\\Legacy\\Gate",
                )
            ],
            root=root,
        )
        seed_file(
            store,
            "legacy/Gate.aa",
            [node("Class", "Gate", "\\Legacy\\Gate", "legacy/Gate.aa")],
            [],
            root=root,
        )
    return config


def _artifact(root: Path) -> dict[str, object]:
    text = (root / ".code-atlas" / "onboarding" / "artifact.json").read_text(encoding="utf-8")
    payload = json.loads(text)
    assert isinstance(payload, dict)
    return payload


def _read(root: Path, name: str) -> str:
    return (_out(root) / name).read_text(encoding="utf-8")


def test_declared_working_roots_keep_the_tour_inside_the_roots(tmp_path: Path) -> None:
    """Proving test: app-only scope narrows destinations, not the cited context."""
    config = replace(_scoped_repo(tmp_path), working_roots=("app",))
    payload = generate_onboarding.create(config)()
    artifact = _artifact(tmp_path)
    stops = artifact["stops"]

    assert payload["working_roots"] == ["app"]
    assert all(str(stop["file"]).startswith("app/") for stop in stops)  # type: ignore[index]
    flows = _read(tmp_path, "flows.md")
    assert "\\Legacy\\Gate" in flows


def test_scope_lines_appear_only_when_roots_are_declared(tmp_path: Path) -> None:
    config = _scoped_repo(tmp_path)
    generate_onboarding.create(config)()
    unscoped = {name: _read(tmp_path, name) for name in ("overview.md", "tour.md", "flows.md")}

    scoped_root = tmp_path / "scoped"
    scoped = replace(_scoped_repo(scoped_root), working_roots=("app",))
    generate_onboarding.create(scoped)()
    scoped_docs = {
        name: _read(scoped_root, name) for name in ("overview.md", "tour.md", "flows.md")
    }

    for text in unscoped.values():
        assert "scope: working_roots=" not in text
    for text in scoped_docs.values():
        assert "- scope: working_roots=app (2 of 3 indexed files)" in text


def test_unset_working_roots_leave_the_emitted_tree_byte_identical(tmp_path: Path) -> None:
    config = _scoped_repo(tmp_path)
    first = generate_onboarding.create(config)()
    first_docs = {
        name: (_out(tmp_path) / name).read_bytes()
        for name in ("overview.md", "tour.md", "flows.md", "manifest.json", "index.html")
    }

    second = generate_onboarding.create(replace(config, working_roots=None))()

    assert second == first
    for name, body in first_docs.items():
        assert (_out(tmp_path) / name).read_bytes() == body


def test_the_working_scope_predicate_has_one_prefix_body() -> None:
    files = sorted(Path("code_atlas/onboarding").glob("*.py"))
    matches = [
        path.as_posix()
        for path in files
        if 'path.startswith(f"{root}/")' in path.read_text(encoding="utf-8")
    ]
    assert matches == ["code_atlas/onboarding/scope.py"]
