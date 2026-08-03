#!/usr/bin/env python3
"""One-command setup for code-atlas: install the core, build the PHP adapter, write MCP config.

Run with the plain system Python from anywhere:

    python scripts/setup.py [PROJECT_DIR]

Given a PROJECT_DIR it installs the core, sets up the PHP adapter, and writes a ready-to-use
``.mcp.json`` into that project (the repo you want indexed). With no PROJECT_DIR it does the setup
and prints the snippet to paste into your client. It computes the three things the manual guide
made you get right by hand: the interpreter to launch, the adapter path, and the project ``cwd``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
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


def server_entry() -> dict[str, object]:
    """The MCP server block: this interpreter + ``-m code_atlas.main`` avoids any PATH guesswork."""
    return {
        "command": sys.executable,
        "args": ["-m", "code_atlas.main"],
        "env": {"CA_PHP_CMD": f"php {ADAPTER_PHP.as_posix()} --server"},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Set up code-atlas in one command.")
    ap.add_argument(
        "project", nargs="?", help="repo to index; its .mcp.json is written for you"
    )
    ap.add_argument(
        "--no-adapter",
        action="store_true",
        help="skip the PHP adapter (nothing to index until set up)",
    )
    args = ap.parse_args()

    print("code-atlas setup\n================")

    print("\n[1/3] Installing the Python core ...")
    if not run([sys.executable, "-m", "pip", "install", "-e", str(ROOT)]):
        print("Core install failed -- fix the error above and rerun.")
        return 1

    print("\n[2/3] Setting up the PHP adapter ...")
    if args.no_adapter:
        print("  - skipped (--no-adapter)")
    else:
        php = shutil.which("php")
        composer = shutil.which("composer")
        if not php:
            print("  ! PHP CLI not found. Install PHP 8.1+ (tokenizer ext) to index PHP repos.")
        if not composer:
            print("  ! Composer not found. Install from https://getcomposer.org, then rerun.")
        elif not run([composer, "install", "--working-dir", str(ROOT / "adapters" / "php")]):
            print("  ! `composer install` failed -- the adapter can't run until this succeeds.")

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

    print("\nDone. Reload your MCP client, then call get_index_status -> build_or_update_index.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
