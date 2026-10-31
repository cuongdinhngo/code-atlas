"""R9.4 — a change to the tool surface carries a CHANGELOG line (428).

``tests/fixtures/tool_manifest.json`` is the pinned tool surface. A commit range that changes it
without a CHANGELOG line ships a surface change nobody was told about. The range must ADD a line to
``CHANGELOG.md`` saying "tool surface" or naming a tool whose manifest entry changed; touching the
file is not enough. CI and gate.sh run this over the change range.

Stdlib only: the CI `guardrails` job runs it on the runner's own `python3`, with no install step.

    python3 scripts/surface_changelog.py <rev-range>

Exit 0 clean, 1 the manifest changed and no added line says so, 2 an unreadable range.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = "tests/fixtures/tool_manifest.json"
CHANGELOG = "CHANGELOG.md"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, check=True, text=True
    ).stdout


def _ends(rev_range: str, repo: Path) -> tuple[str, str]:
    """(merge base, head) of a ``A..B`` or ``A...B`` range; raises CalledProcessError if bad."""
    left, _, right = rev_range.replace("...", "..").partition("..")
    head = right or "HEAD"
    return _git(repo, "merge-base", left or "HEAD", head).strip(), head


def changed_paths(rev_range: str, repo: Path = REPO) -> set[str]:
    """Paths the range's commits change (from the merge base)."""
    base, head = _ends(rev_range, repo)
    out = _git(repo, "diff", "--name-only", "-z", base, head, "--")
    return {path for path in out.split("\0") if path}


def _manifest_tools(repo: Path, rev: str) -> dict[str, object]:
    """Tool name -> manifest entry at ``rev``; empty when the file is absent or unreadable."""
    try:
        data = json.loads(_git(repo, "show", f"{rev}:{MANIFEST}"))
        return {str(tool["name"]): tool for tool in data["tools"]}
    except (subprocess.CalledProcessError, ValueError, KeyError, TypeError):
        return {}


def changed_tools(rev_range: str, repo: Path = REPO) -> set[str]:
    """Names of the tools whose manifest entry the range adds, removes or edits."""
    base, head = _ends(rev_range, repo)
    before, after = _manifest_tools(repo, base), _manifest_tools(repo, head)
    return {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}


def changelog_added(rev_range: str, repo: Path = REPO) -> str:
    """The lines the range adds to the CHANGELOG."""
    base, head = _ends(rev_range, repo)
    diff = _git(repo, "diff", "-U0", base, head, "--", CHANGELOG)
    return "\n".join(
        line[1:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def names_the_change(added: str, tools: set[str]) -> bool:
    """An added line says "tool surface" or names a tool whose manifest entry changed."""
    if "tool surface" in added.lower():
        return True
    return any(re.search(rf"(?<![\w]){re.escape(tool)}(?![\w])", added) for tool in tools)


def main(argv: list[str], repo: Path = REPO) -> int:
    if len(argv) != 1:
        print("usage: surface_changelog.py <rev-range>", file=sys.stderr)
        return 2
    try:
        changed = changed_paths(argv[0], repo)
        tools = changed_tools(argv[0], repo) if MANIFEST in changed else set()
        added = changelog_added(argv[0], repo) if MANIFEST in changed else ""
    except subprocess.CalledProcessError as error:
        print(f"R9.4 — cannot read range {argv[0]!r}: {error.stderr.strip()}", file=sys.stderr)
        return 2
    if MANIFEST in changed and not names_the_change(added, tools):
        print(
            f"R9.4 — {MANIFEST} changed in {argv[0]!r}, but {CHANGELOG} adds no line saying "
            f'"tool surface" or naming one of: {", ".join(sorted(tools)) or "(none)"}'
        )
        return 1
    print(f"R9.4 tool surface and {CHANGELOG} agree over {argv[0]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
