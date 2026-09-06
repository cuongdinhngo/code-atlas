"""`scripts/setup.py` is the install path the README hands a first-time user, so its failure modes
are adoption failures, not developer inconvenience.

The defect this pins: step 1 ran `pip install -e .` unconditionally and returned 1 the moment it
failed, so an interpreter with no `pip` — a venv built `--without-pip`, or a distro that splits it
out — aborted before writing `.mcp.json`, which is the one thing the script exists to compute. It
did that even when the core was already installed and the run had nothing left to do.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import setup as setup_script  # noqa: E402


def test_an_already_installed_core_needs_no_pip() -> None:
    """Being installed is success. The old code called `pip` regardless and failed without it."""
    assert setup_script.core_is_importable() is True
    assert setup_script.install_core() is True


def test_every_ready_adapter_is_wired_not_just_php() -> None:
    """`server_entry` used to hardcode `CA_PHP_CMD` alone, so the other three were manual work."""
    env = setup_script.server_entry()["env"]
    assert isinstance(env, dict)
    # Python is stdlib-only, so it is always available on the interpreter running the core.
    assert "CA_PYTHON_CMD" in env
    assert env["CA_PYTHON_CMD"].startswith(sys.executable)
    for key, cmd in env.items():
        assert key.startswith("CA_") and key.endswith("_CMD"), key
        assert cmd.endswith("--server"), cmd
        # The adapter path must be absolute: the core appends nothing and never guesses a cwd.
        assert Path(cmd.split()[-2]).is_absolute(), cmd


@pytest.mark.parametrize("adapter", ["typescript", "sql"])
def test_an_uninstalled_node_adapter_is_left_out(adapter: str, monkeypatch) -> None:
    """A command naming a missing `node_modules` would be a config that fails at first call."""
    monkeypatch.setattr(setup_script.shutil, "which", lambda name: None)
    assert f"CA_{adapter.upper()}_CMD" not in setup_script.adapter_commands()


def test_a_pipless_interpreter_still_writes_the_config(tmp_path: Path) -> None:
    """The regression, end to end: no pip and no core, yet `.mcp.json` is still produced.

    Exit stays 1 — the core really is missing — but the config is correct for the moment it is
    installed, and the message names the interpreter and the `ensurepip` remedy.
    """
    venv = tmp_path / "nopip"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True
    )
    python = venv / "bin" / "python"
    if not python.is_file():  # pragma: no cover - Windows layout; the suite is POSIX-only anyway
        pytest.skip("no POSIX venv layout")
    project = tmp_path / "project"
    project.mkdir()

    done = subprocess.run(
        [str(python), str(REPO / "scripts" / "setup.py"), str(project), "--no-adapter"],
        capture_output=True,
        text=True,
    )

    assert (project / ".mcp.json").is_file(), done.stdout + done.stderr
    assert done.returncode == 1, "the core is genuinely absent, so the exit code must say so"
    assert "has no pip" in done.stdout
    assert "ensurepip" in done.stdout
