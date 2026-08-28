"""Task 175 — which config answered, and whether the disk still matches it.

The field episode: the maintainer edited `.code-atlas.toml` to add the second adapter, ran a
build, and got a success describing the old world — `indexed_suffixes: [".php", ".phtml"]`,
`wrote.files: 0`, 2.6 s. *"No field says 'the config on disk differs from the config I loaded'."*

164 closed *which code answered* and 170 made that verdict live. Neither covers *which config
answered* — and config decides what the index even **contains**, which makes a silent stale read
more consequential here than a stale build id. Spec-driven fixtures (R2); no language is named.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import pytest

from code_atlas import adapter
from code_atlas.config import (
    CONFIG_ID_CHARS,
    PROJECT_FILE,
    config_identity,
    config_stale,
    load_config,
)
from code_atlas.store import CONFIG_IDENTITY_KEY, GraphStore
from code_atlas.tools import get_index_status
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.config_provenance import CONFIG_BUILD, CONFIG_STALE, INDEX_CONFIG_BUILD

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


def fake_cmd(mode: str = "ok") -> str:
    return shlex.join([sys.executable, str(FAKE), mode])


@pytest.fixture(autouse=True)
def only_the_fixture_adapters_ship(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "shipped"
    for name in ("fake", "second"):
        (root / name / "src").mkdir(parents=True)
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", root)


def write_project_file(root: Path, *modes: str) -> None:
    lines = ["[adapter_cmd]"]
    for mode in modes:
        name = "fake" if mode == "ok" else mode
        lines.append(f'{name} = {list(shlex.split(fake_cmd(mode)))!r}')
    (root / PROJECT_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")


def seed(root: Path, *paths: str) -> None:
    for path in paths:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)


def configured(root: Path):
    return load_config(root, {"CA_WORKERS": "1", "CA_DB_PATH": str(root / ".ca" / "graph.db")})


def test_a_config_edited_after_load_is_reported_by_the_next_build(tmp_path: Path) -> None:
    """AC1 — the episode. The config is loaded, the file changes, and the build says so.

    This fails on today's code: nothing hashes the config, so nothing can compare it to the disk.
    """
    write_project_file(tmp_path, "ok")
    seed(tmp_path, "src/a.aa")
    config = configured(tmp_path)

    clean = build_tool(config)(full=True)
    assert clean[CONFIG_STALE] is False
    assert clean[CONFIG_BUILD] == config.identity

    # The edit that started this: a second adapter added to the file, under a running server.
    write_project_file(tmp_path, "ok", "second")
    stale = build_tool(config)(full=True)

    assert stale[CONFIG_STALE] is True, "a build under a moved config must say so"
    assert stale[CONFIG_BUILD] == config.identity, "the id still names the config that answered"


def test_the_verdict_is_stated_not_omitted(tmp_path: Path) -> None:
    """AC2 / 170's lesson: absence and 'checked, still matching' are different claims."""
    write_project_file(tmp_path, "ok")
    seed(tmp_path, "src/a.aa")
    config = configured(tmp_path)
    build_tool(config)(full=True)

    status = get_index_status.create(config, (get_index_status.NAME,))(detail_level="standard")
    assert CONFIG_STALE in status, "the verdict rides; silence is not the clean answer"
    assert status[CONFIG_STALE] is False
    assert status[CONFIG_BUILD] == config.identity
    assert len(str(status[CONFIG_BUILD])) == CONFIG_ID_CHARS


def test_the_index_can_say_which_config_built_it(tmp_path: Path) -> None:
    """AC5 — decided and IMPLEMENTED: the index stamps its own config, a claim distinct from the
    process's. Surfaced only when the two differ; equal ids tell the reader nothing (061)."""
    write_project_file(tmp_path, "ok")
    seed(tmp_path, "src/a.aa")
    first = configured(tmp_path)
    build_tool(first)(full=True)

    with GraphStore(first.db_path) as store:
        assert store.get_meta(CONFIG_IDENTITY_KEY) == first.identity

    same = get_index_status.create(first, (get_index_status.NAME,))(detail_level="standard")
    assert INDEX_CONFIG_BUILD not in same, "equal ids add nothing (061)"

    # A second process, loaded from a changed file, reading an index the old config built.
    write_project_file(tmp_path, "ok", "second")
    second = configured(tmp_path)
    assert second.identity != first.identity
    moved = get_index_status.create(second, (get_index_status.NAME,))(detail_level="standard")
    assert moved[INDEX_CONFIG_BUILD] == first.identity
    assert moved[CONFIG_BUILD] == second.identity


def test_the_no_config_path_still_names_an_identity(tmp_path: Path) -> None:
    """AC3 (125's guarantee, one layer up): env-only or defaults must answer, and not raise."""
    assert not (tmp_path / PROJECT_FILE).exists()
    config = load_config(tmp_path, {})

    assert len(config.identity) == CONFIG_ID_CHARS
    assert config_stale(config) is False
    # And it is stable: the absence is hashed as a marker, not as nothing.
    assert config_identity(tmp_path, {}) == config.identity


def test_the_identity_is_content_only(tmp_path: Path) -> None:
    """AC4/R4.2: identical bytes and env ⇒ identical id; a touch must not move it."""
    write_project_file(tmp_path, "ok")
    env = {"CA_WORKERS": "1"}
    before = config_identity(tmp_path, env)

    body = (tmp_path / PROJECT_FILE).read_bytes()
    (tmp_path / PROJECT_FILE).write_bytes(body)  # same bytes, new mtime
    assert config_identity(tmp_path, env) == before, "no timestamp reaches the id"

    other = tmp_path / "elsewhere"
    other.mkdir()
    (other / PROJECT_FILE).write_bytes(body)
    assert config_identity(other, env) == before, "same bytes and env, another directory, same id"


def test_the_identity_is_stable_across_processes(tmp_path: Path) -> None:
    """AC4: R4.2 across processes, not just across calls — measured by running a second one."""
    write_project_file(tmp_path, "ok")
    mine = config_identity(tmp_path, {"CA_WORKERS": "1"})

    other = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, pathlib; sys.path.insert(0, sys.argv[2]); "
            "from code_atlas.config import config_identity; "
            "print(config_identity(pathlib.Path(sys.argv[1]), {'CA_WORKERS': '1'}))",
            str(tmp_path),
            str(REPO),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert other.stdout.strip() == mine


def test_only_the_env_the_config_reads_moves_the_identity(tmp_path: Path) -> None:
    """An unrelated variable must not move the identity, or every shell change reads as stale."""
    write_project_file(tmp_path, "ok")
    base = config_identity(tmp_path, {"CA_WORKERS": "1"})

    assert config_identity(tmp_path, {"CA_WORKERS": "1", "PATH": "/nowhere"}) == base
    assert config_identity(tmp_path, {"CA_WORKERS": "1", "EDITOR": "vi"}) == base
    assert config_identity(tmp_path, {"CA_WORKERS": "2"}) != base, "a knob it reads does move it"
    assert config_identity(tmp_path, {"CA_WORKERS": "1", "CA_SECOND_CMD": "x"}) != base


def test_a_deleted_config_file_reads_as_a_divergence(tmp_path: Path) -> None:
    """Removing the file is as much a change as editing it — R5.6's shape: say what is known."""
    write_project_file(tmp_path, "ok")
    seed(tmp_path, "src/a.aa")
    config = configured(tmp_path)
    assert config_stale(config) is False

    (tmp_path / PROJECT_FILE).unlink()
    assert config_stale(config) is True


def test_a_hand_built_config_says_nothing(tmp_path: Path) -> None:
    """A Config that never resolved from disk has nothing to compare, so it claims nothing."""
    write_project_file(tmp_path, "ok")
    seed(tmp_path, "src/a.aa")
    config = replace(configured(tmp_path), identity="")
    build_tool(config)(full=True)

    status = get_index_status.create(config, (get_index_status.NAME,))(detail_level="standard")
    assert CONFIG_STALE not in status
    assert CONFIG_BUILD not in status


def test_the_cheap_path_and_nav_payloads_carry_nothing(tmp_path: Path) -> None:
    """Recorded design decision: the verdict rides the two tools that need it, not every answer.

    The code axis already costs 91 B unconditionally on every nav payload (170); a second standing
    tax needs a better reason than symmetry, and the constraint says so explicitly.
    """
    write_project_file(tmp_path, "ok")
    seed(tmp_path, "src/a.aa")
    config = configured(tmp_path)
    build_tool(config)(full=True)

    minimal = get_index_status.create(config, (get_index_status.NAME,))(detail_level="minimal")
    assert CONFIG_STALE not in minimal, "the cheap path stays cheap"

    from code_atlas.tools import nav_result as nr

    nav = nr.nav_result("Foo", [], detail_level="standard", index_root="/r", truncated=False)
    assert CONFIG_STALE not in nav and CONFIG_BUILD not in nav


def test_the_added_cost_is_one_small_read(tmp_path: Path) -> None:
    """Cost constraint: a file read plus a hash, at build time and on status — never per payload."""
    write_project_file(tmp_path, "ok")
    seed(tmp_path, "src/a.aa")
    config = configured(tmp_path)
    build_tool(config)(full=True)

    started = perf_counter()
    for _ in range(500):
        config_stale(config)
    per_call_ms = (perf_counter() - started) / 500 * 1000
    assert per_call_ms < 1.0, f"{per_call_ms:.4f} ms per config staleness check"


def test_no_language_is_named_by_the_identity(tmp_path: Path) -> None:
    """AC6/R1.1: the env slice is derived from KNOB_KEYS and the CMD pattern, never a list."""
    hits = subprocess.run(
        ["grep", "-rn", "-e", "php", "-e", "typescript", "code_atlas/tools/config_provenance.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert hits.stdout == ""
    write_project_file(tmp_path, "ok", "second")
    assert len(config_identity(tmp_path, {})) == CONFIG_ID_CHARS
