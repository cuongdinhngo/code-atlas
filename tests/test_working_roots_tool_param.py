"""216 — ``working_roots`` is a ``generate_onboarding`` parameter, not env-only.

206 shipped the scoping; this ticket makes it reachable from an MCP client. Precedence matches
``audience``: explicit argument wins over ``CA_WORKING_ROOTS`` / config; unset preserves today.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import replace
from pathlib import Path

from code_atlas.tools import generate_onboarding
from tests.test_generate_onboarding import _out
from tests.test_nav_tools import db_config
from tests.test_working_scope import _artifact, _read, _scoped_repo


def test_argument_scopes_the_tour_when_config_is_unset(tmp_path: Path) -> None:
    """AC1 — call-site working_roots restricts destinations; unscoped visits a different set."""
    config = _scoped_repo(tmp_path)
    generate_onboarding.create(config)()
    unscoped_stops = {str(s["file"]) for s in _artifact(tmp_path)["stops"]}  # type: ignore[index]

    scoped_root = tmp_path / "arg"
    scoped_cfg = _scoped_repo(scoped_root)
    assert scoped_cfg.working_roots is None
    payload = generate_onboarding.create(scoped_cfg)(working_roots=["app"])
    stops = _artifact(scoped_root)["stops"]

    assert payload["working_roots"] == ["app"]
    assert all(str(stop["file"]).startswith("app/") for stop in stops)  # type: ignore[index]
    scoped_stops = {str(s["file"]) for s in stops}  # type: ignore[index]
    assert scoped_stops != unscoped_stops
    assert "legacy/Gate.aa" in unscoped_stops
    assert "legacy/Gate.aa" not in scoped_stops


def test_unset_argument_preserves_env_default(tmp_path: Path) -> None:
    """AC2 — omitting the argument keeps CA_WORKING_ROOTS / config behaviour byte-identical."""
    config = replace(_scoped_repo(tmp_path), working_roots=("app",))
    generate_onboarding.create(config)()  # seed prior for 269 Q6
    via_config = generate_onboarding.create(config)()
    docs = {
        name: (_out(tmp_path) / name).read_bytes()
        for name in ("overview.md", "tour.md", "flows.md", "manifest.json", "index.html")
    }

    again = generate_onboarding.create(config)()
    assert again == via_config
    for name, body in docs.items():
        assert (_out(tmp_path) / name).read_bytes() == body


def test_explicit_argument_overrides_config_working_roots(tmp_path: Path) -> None:
    """AC3 — call-site list wins over an env/config default that would scope elsewhere."""
    config = replace(_scoped_repo(tmp_path), working_roots=("legacy",))
    payload = generate_onboarding.create(config)(working_roots=["app"])
    stops = _artifact(tmp_path)["stops"]

    assert payload["working_roots"] == ["app"]
    assert all(str(stop["file"]).startswith("app/") for stop in stops)  # type: ignore[index]
    assert "- scope: working_roots=app (" in _read(tmp_path, "overview.md")


def test_written_tree_names_per_call_scope(tmp_path: Path) -> None:
    """AC4 — scoped vs unscoped are distinguishable from the committed file alone."""
    config = _scoped_repo(tmp_path)
    generate_onboarding.create(config)()
    assert "scope: working_roots=" not in _read(tmp_path, "overview.md")

    generate_onboarding.create(config)(working_roots=["app"])
    overview = _read(tmp_path, "overview.md")
    assert "- scope: working_roots=app (2 of 3 indexed files)" in overview


def test_empty_list_forces_the_whole_index_over_a_scoped_config(tmp_path: Path) -> None:
    """``[]`` is not "unset": it overrides a scoping config back to the whole index (216)."""
    config = replace(_scoped_repo(tmp_path), working_roots=("app",))
    payload = generate_onboarding.create(config)(working_roots=[])
    assert payload["working_roots"] is None
    assert "scope: working_roots=" not in _read(tmp_path, "overview.md")


def test_docstring_states_the_three_axes_and_schema_exposes_the_param() -> None:
    """AC5 — detail_level / audience / working_roots each named for what they shape."""
    tool = generate_onboarding.create(db_config(Path(__file__).parent))
    doc = tool.__doc__ or ""
    assert "detail_level" in doc and "response" in doc.lower()
    assert "audience" in doc and "sections" in doc
    assert "working_roots" in doc and "population" in doc
    assert "working_roots" in inspect.signature(tool).parameters


def test_scope4_docstring_vs_schema_sweep() -> None:
    """AC6 — method + result: backticked ``working_roots`` in a tool docstring ⇒ signature has it.

    Walk every nested tool function under ``code_atlas/tools/``. A docstring that writes
    `` `working_roots` `` (claiming a callable knob) while the signature omits it is the 177/216
    defect class. Result after this change: **zero** gaps.
    """
    gaps: list[str] = []
    tools_dir = Path(generate_onboarding.__file__).resolve().parent
    for path in sorted(tools_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            doc = ast.get_docstring(node) or ""
            if "`working_roots`" not in doc and "``working_roots``" not in doc:
                continue
            params = {arg.arg for arg in node.args.args} | {
                arg.arg for arg in node.args.kwonlyargs
            }
            if "working_roots" not in params:
                gaps.append(f"{path.as_posix()}:{node.name}")
    assert gaps == [], f"docstring claims working_roots but schema omits it: {gaps}"
