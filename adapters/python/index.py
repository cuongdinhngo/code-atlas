#!/usr/bin/env python3
"""Python adapter entry — handshake then JSONL serve, same shape as the TS/PHP adapters."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Launch cwd is the repo root; make `src.parse` importable from this directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.parse import parse_file  # noqa: E402

# One-line literal — claim 200-C4; gen_skill.py reads this without a subprocess.
META = {
    "name": "python",
    "extensions": [".py"],
    "capabilities": {
        "semantic_types": True,
        "params": True,
        "args": True,
        "modifiers": True,
        "declared_types": True,
        "inheritance": True,
    },
    "contract_version": 13,
    # What a grep for a Python symbol looks like (345): a def/class, a method or import, a call.
    "symbol_shapes": [
        {"kind": "declaration", "pattern": r"\b(async\s+)?def\s+\w+|\bclass\s+\w+"},
        {
            "kind": "reference",
            "pattern": r"\.\s*\w+\s*\\?\(|\bimport\s+\w+|\bfrom\s+[\w.]+\s+import\b",
        },
        {"kind": "call", "pattern": r"^\w+\\?\($"},
    ],
}


def emit(result: object) -> None:
    sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def serve() -> None:
    emit(META)
    for raw in sys.stdin:
        trimmed = raw.strip()
        if not trimmed:
            continue
        try:
            request = json.loads(trimmed)
        except json.JSONDecodeError:
            sys.stderr.write("code-atlas python adapter: skipped an unusable request line\n")
            continue
        path = request.get("path") if isinstance(request, dict) else None
        if not isinstance(path, str):
            sys.stderr.write("code-atlas python adapter: skipped an unusable request line\n")
            continue
        roots_raw = request.get("source_roots") if isinstance(request, dict) else None
        roots: list[str] = []
        if isinstance(roots_raw, list):
            roots = [r for r in roots_raw if isinstance(r, str) and r.strip()]
        emit(
            parse_file(
                path,
                declarations_only=bool(request.get("declarations_only")),
                source_roots=roots or None,
            )
        )


def main(argv: list[str]) -> int:
    # Grammar floor is R4.2: ``ast.parse`` tracks the running interpreter (task 217 / AC3).
    # Kept even under requires-python>=3.12 so a wrong CA_PYTHON_CMD host fails loudly.
    if sys.version_info < (3, 12):  # noqa: UP036
        ver = sys.version_info
        sys.stderr.write(
            "code-atlas python adapter requires Python >= 3.12 "
            f"(running {ver[0]}.{ver[1]})\n"
        )
        return 2
    if len(argv) == 1 and argv[0] == "--server":
        serve()
        return 0
    if len(argv) == 2 and argv[0] == "--file":
        emit(parse_file(argv[1], declarations_only=False))
        return 0
    sys.stderr.write("usage: python index.py --file <path> | --server\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
