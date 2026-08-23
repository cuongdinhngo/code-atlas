#!/usr/bin/env python3
"""What an agent pays to read the chain before it knows what binds it (task 133).

Walks from `CLAUDE.md` through its `@import` to `AGENTS.md`, then follows the list `AGENTS.md`
itself calls *read before non-trivial work* — tier 1. The list it calls *consult when you need it*
is reported beside it as tier 2, so the boundary can be seen rather than asserted. Both sets are
**derived from the chain's own statement**, never listed here (R6.7): change a bullet list and this
reporter follows it.

Read-only, no network, no index. Two runs on one tree are byte-identical (R4.2) — the walk is
ordered by the chain, not by the filesystem.

Exists because `tests/test_doc_size_budget.py` carries per-file ceilings, and a threshold whose only
evidence is a session transcript is what R6.3 forbids. This prints the inputs those numbers were
chosen from, so they can be re-justified whenever a document moves.

    python scripts/agent_chain_cost.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from code_atlas.tokens import estimate_tokens  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ENTRY = "CLAUDE.md"
BINDING_LIST = "Read these before non-trivial work"
CONSULT_LIST = "Consult when you need it"

IMPORT = re.compile(r"^@(\S+)\s*$", re.MULTILINE)
BULLET_LINK = re.compile(r"^-\s*\[[^\]]*\]\(([^)]+\.md)\)")


def _imports(path: Path) -> list[Path]:
    """The `@path` imports a chain file declares, in the order it declares them."""
    return [REPO / target for target in IMPORT.findall(path.read_text(encoding="utf-8"))]


def _bulleted_links(path: Path, marker: str) -> list[Path]:
    """The markdown links bulleted under the file's own line naming this list."""
    found: list[Path] = []
    started = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if marker in line:
            started = True
            continue
        if not started:
            continue
        match = BULLET_LINK.match(line)
        if match:
            found.append((path.parent / match.group(1)).resolve())
        elif line.strip() and not line.startswith("-"):
            break  # the list ended; anything after it is a different claim
    return found


def chain() -> list[Path]:
    """Tier 1 — every file an agent must read before it knows what binds it, in chain order."""
    ordered: list[Path] = []
    queue = [REPO / ENTRY]
    while queue:
        current = queue.pop(0)
        if current in ordered or not current.is_file():
            continue
        ordered.append(current)
        queue.extend(_imports(current))
        queue.extend(_bulleted_links(current, BINDING_LIST))
    return ordered


def consult_only() -> list[Path]:
    """Tier 2 — what the chain names as reference, reached by a pointer and not read up front."""
    found: list[Path] = []
    for path in chain():
        for target in _bulleted_links(path, CONSULT_LIST):
            if target.is_file() and target not in found:
                found.append(target)
    return found


def _rows(paths: list[Path]) -> list[tuple[str, int, int]]:
    out = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        name = path.relative_to(REPO).as_posix()
        out.append((name, len(text.splitlines()), estimate_tokens(text)))
    return out


def main() -> int:
    tiers = [("tier 1 — binding", _rows(chain())), ("tier 2 — consult", _rows(consult_only()))]
    width = max(len(name) for _, rows in tiers for name, _, _ in rows)

    for title, rows in tiers:
        print(f"\n{title}")
        print(f"{'file'.ljust(width)}  {'lines':>6}  {'tokens':>7}")
        for name, lines, tokens in rows:
            print(f"{name.ljust(width)}  {lines:>6}  {tokens:>7,}")
        print(f"{'—' * width}  {'—' * 6}  {'—' * 7}")
        print(
            f"{f'{len(rows)} files'.ljust(width)}  "
            f"{sum(r[1] for r in rows):>6}  {sum(r[2] for r in rows):>7,}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
