"""The tool-surface manifest: every tool's name, description, input schema and annotations (428).

The manifest is read off a live ``build_server`` over a throwaway config, so it is what a client is
offered and never a hand-kept copy (R6.7). A changed description is the vector a "rug pull"
uses; this makes it a reviewed diff.

    python scripts/gen_tool_manifest.py            # print a unified diff; exit 1 on drift
    python scripts/gen_tool_manifest.py --write    # regenerate tests/fixtures/tool_manifest.json
"""

from __future__ import annotations

import argparse
import asyncio
import difflib
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "tests" / "fixtures" / "tool_manifest.json"


def build_manifest() -> str:
    """The manifest text, deterministic: tools sorted by name, keys sorted, a trailing newline."""
    sys.path.insert(0, str(REPO))
    from code_atlas.config import load_config
    from code_atlas.main import build_server

    with tempfile.TemporaryDirectory() as root:
        server = build_server(load_config(Path(root), {}), count=False)
        tools = asyncio.run(server.list_tools())
    entries = [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
            "annotations": tool.annotations.model_dump(exclude_none=True)
            if tool.annotations
            else None,
        }
        for tool in tools
    ]
    entries.sort(key=lambda entry: str(entry["name"]))
    return json.dumps({"tools": entries}, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def drift(expected: str, live: str, label: str = "tests/fixtures/tool_manifest.json") -> list[str]:
    """The unified diff of the committed manifest against the live one; empty when they agree."""
    return list(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            live.splitlines(keepends=True),
            fromfile=f"{label} (committed)",
            tofile=f"{label} (live server)",
        )
    )


def main(argv: list[str], manifest: Path = MANIFEST) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="regenerate the committed manifest")
    args = parser.parse_args(argv)
    live = build_manifest()
    if args.write:
        manifest.write_text(live, encoding="utf-8")
        print(f"wrote {manifest.relative_to(REPO) if manifest.is_relative_to(REPO) else manifest}")
        return 0
    committed = manifest.read_text(encoding="utf-8") if manifest.exists() else ""
    diff = drift(committed, live)
    if diff:
        sys.stdout.writelines(diff)
        print(
            "\nthe tool surface changed: rerun with --write, review the diff, add a CHANGELOG line"
        )
        return 1
    print("tool manifest matches the live server")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
