"""R9.4 — a change to the tool surface carries a CHANGELOG line (428).

``tests/fixtures/tool_manifest.json`` is the pinned tool surface. A commit range that changes it
without touching ``CHANGELOG.md`` ships a surface change nobody was told about; CI and gate.sh run
this over the change range.

Stdlib only: the CI `guardrails` job runs it on the runner's own `python3`, with no install step.

    python3 scripts/surface_changelog.py <rev-range>

Exit 0 clean, 1 the manifest changed and the CHANGELOG did not, 2 an unreadable range.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = "tests/fixtures/tool_manifest.json"
CHANGELOG = "CHANGELOG.md"


def changed_paths(rev_range: str, repo: Path = REPO) -> set[str]:
    """Paths the range's commits change (from the merge base); raises CalledProcessError if bad."""
    triple = rev_range if "..." in rev_range else rev_range.replace("..", "...", 1)
    out = subprocess.run(
        ["git", "diff", "--name-only", "-z", triple, "--"],
        cwd=repo,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    return {path for path in out.split("\0") if path}


def main(argv: list[str], repo: Path = REPO) -> int:
    if len(argv) != 1:
        print("usage: surface_changelog.py <rev-range>", file=sys.stderr)
        return 2
    try:
        changed = changed_paths(argv[0], repo)
    except subprocess.CalledProcessError as error:
        print(f"R9.4 — cannot read range {argv[0]!r}: {error.stderr.strip()}", file=sys.stderr)
        return 2
    if MANIFEST in changed and CHANGELOG not in changed:
        print(f"R9.4 — {MANIFEST} changed in {argv[0]!r} but {CHANGELOG} did not: add the line")
        return 1
    print(f"R9.4 tool surface and {CHANGELOG} agree over {argv[0]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
