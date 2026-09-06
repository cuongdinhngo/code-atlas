#!/usr/bin/env python3
"""One-command setup for code-atlas: install the core, set up the adapters, write MCP config.

Run with the plain system Python from anywhere:

    python scripts/setup.py [PROJECT_DIR]

Given a PROJECT_DIR it installs the core, sets up every adapter whose runtime is present, and writes
a ready-to-use ``.mcp.json`` into that project (the repo you want indexed). With no PROJECT_DIR it
does the setup and prints the snippet to paste into your client. It computes the three things the
manual guide made you get right by hand: the interpreter to launch, the adapter paths, and ``cwd``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # the code-atlas checkout
ADAPTER_PHP = ROOT / "adapters" / "php" / "index.php"


def run(cmd: list[str]) -> bool:
    """Echo and run a command; return True on success, False (with a note) on failure."""
    print(f"  $ {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"  ! command failed (exit {exc.returncode})")
        return False


def core_is_importable() -> bool:
    """True when ``code_atlas`` already imports on this interpreter — the goal step 1 exists for."""
    probe = "import code_atlas, sys; sys.stdout.write(code_atlas.__file__)"
    try:
        # Probed from a neutral directory on purpose: run from inside the checkout, the cwd is on
        # `sys.path` and every interpreter "imports" code_atlas whether or not it is installed.
        with tempfile.TemporaryDirectory() as neutral:
            done = subprocess.run(
                [sys.executable, "-c", probe],
                capture_output=True,
                text=True,
                check=True,
                cwd=neutral,
            )
    except (subprocess.CalledProcessError, OSError):
        return False
    print(f"  core already importable: {done.stdout.strip()}")
    return True


def install_core() -> bool:
    """Install the core, but only when it is not already usable.

    An interpreter with no ``pip`` (a venv built with ``--without-pip``, or a distro split package)
    used to abort the whole run, including the ``.mcp.json`` write that is the point of the script.
    Being already installed is success, so check that first and report the remedy when it is not.
    """
    if core_is_importable():
        return True
    if run([sys.executable, "-m", "pip", "install", "-e", str(ROOT)]):
        return True
    has_pip = (
        subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True).returncode
        == 0
    )
    if not has_pip:
        print(f"  ! this interpreter has no pip: {sys.executable}")
        print(f"  ! add it with `{sys.executable} -m ensurepip --upgrade`, or rerun this script")
        print("    with an interpreter that has pip, then rerun.")
    return False


def adapter_commands() -> dict[str, str]:
    """``CA_<LANG>_CMD`` for every adapter whose runtime is on PATH — the rest are left out.

    The core resolves any ``CA_<LANG>_CMD`` from the variable name, so wiring one more adapter is
    one more entry here and no core change.
    """
    node = shutil.which("node")
    py_adapter = (ROOT / "adapters/python/index.py").as_posix()
    # stdlib-only: it runs on the interpreter that is already running the core.
    cmds: dict[str, str] = {"CA_PYTHON_CMD": f"{sys.executable} {py_adapter} --server"}
    if shutil.which("php"):
        cmds["CA_PHP_CMD"] = f"php {ADAPTER_PHP.as_posix()} --server"
    if node:
        ts = ROOT / "adapters/typescript"
        sql = ROOT / "adapters/sql"
        if (ts / "node_modules").is_dir():
            cmds["CA_TYPESCRIPT_CMD"] = f"node {(ts / 'index.js').as_posix()} --server"
        if (sql / "node_modules").is_dir():
            cmds["CA_SQL_CMD"] = f"node {(sql / 'index.js').as_posix()} --server"
    return cmds


def server_entry() -> dict[str, object]:
    """The MCP server block: this interpreter + ``-m code_atlas.main`` avoids any PATH guesswork."""
    return {
        "command": sys.executable,
        "args": ["-m", "code_atlas.main"],
        "env": adapter_commands(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Set up code-atlas in one command.")
    ap.add_argument("project", nargs="?", help="repo to index; its .mcp.json is written for you")
    ap.add_argument(
        "--no-adapter",
        action="store_true",
        help="skip adapter setup (nothing is indexable until an adapter is set up)",
    )
    args = ap.parse_args()

    print("code-atlas setup\n================")

    print("\n[1/3] Installing the Python core ...")
    core_ready = install_core()
    if not core_ready:
        # Not fatal: writing .mcp.json is what this script is for, and a config pointing at a
        # not-yet-installed core is still the right config once the install is repaired.
        print("  ! core not installed -- the config below is still correct; install, then reload.")

    print("\n[2/3] Setting up the language adapters ...")
    if args.no_adapter:
        print("  - skipped (--no-adapter)")
    else:
        composer = shutil.which("composer")
        if not shutil.which("php"):
            print("  - PHP not found; skipping (install PHP 8.1+ with tokenizer to index PHP).")
        elif not composer:
            print("  ! Composer not found. Install from https://getcomposer.org, then rerun.")
        elif not run([composer, "install", "--working-dir", str(ROOT / "adapters" / "php")]):
            print("  ! `composer install` failed -- the adapter can't run until this succeeds.")
        if shutil.which("npm"):
            for name in ("typescript", "sql"):
                if not (ROOT / "adapters" / name / "node_modules").is_dir():
                    run(["npm", "ci", "--prefix", str(ROOT / "adapters" / name)])
        else:
            print("  - Node/npm not found; skipping (needed for TypeScript/JavaScript and T-SQL).")
        print("  - Python adapter needs no setup: stdlib only.")

    print("\n[3/3] MCP server configuration ...")
    entry = server_entry()
    if args.project:
        proj = Path(args.project).resolve()
        if not proj.is_dir():
            print(f"  ! {proj} is not a directory.")
            return 1
        entry["cwd"] = str(proj)
        dest = proj / ".mcp.json"
        config: dict[str, object] = {"mcpServers": {}}
        if dest.is_file():
            try:
                config = json.loads(dest.read_text(encoding="utf-8"))
                config.setdefault("mcpServers", {})
            except json.JSONDecodeError:
                print(f"  ! {dest} exists but isn't valid JSON -- printing the snippet instead.")
                config = {}
        if config:
            config["mcpServers"]["code-atlas"] = entry  # type: ignore[index]
            dest.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            print(f"  wrote {dest}")
        else:
            print(json.dumps({"mcpServers": {"code-atlas": entry}}, indent=2))
    else:
        entry["cwd"] = "/abs/path/to/your-project"
        print("  Add this to your project's .mcp.json (set cwd to the repo you index):\n")
        print(json.dumps({"mcpServers": {"code-atlas": entry}}, indent=2))

    wired = ", ".join(sorted(k[3:-4].lower() for k in adapter_commands()))
    print(f"\nAdapters wired into the config: {wired}")
    if not core_ready:
        print("Install the core (see above), then reload your MCP client.")
        return 1
    print("Done. Reload your MCP client, then call get_index_status -> build_or_update_index.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
