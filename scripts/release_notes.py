"""Release notes and the release's own agreement check (431).

The `Release` workflow runs this before it builds: the tag, the pyproject version and the top
CHANGELOG entry must name one version. `notes` prints that entry as the GitHub Release body.

    python3 scripts/release_notes.py check vX.Y.Z      # exit 0 agree, 1 each disagreement named
    python3 scripts/release_notes.py notes X.Y.Z       # the CHANGELOG entry's body
    python3 scripts/release_notes.py prerelease X.Y.Z  # exit 0 a PEP 440 pre-release, 1 final

Stdlib only: the workflow runs it on the runner's own `python3`.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HEADING = re.compile(r"^## (\S+) — \d{4}-\d{2}-\d{2} · contract \d+ · schema \d+$", re.M)
PRERELEASE = re.compile(r"\d(?:a|b|rc)\d*|\.?dev\d*")


def top_version(changelog: str) -> str | None:
    """The newest release heading's version; an *Unreleased* section above it is not one."""
    found = HEADING.search(changelog)
    return found.group(1) if found else None


def entry(changelog: str, version: str) -> str | None:
    """The body under ``version``'s heading, up to the next release heading; None if absent."""
    for found in HEADING.finditer(changelog):
        if found.group(1) == version:
            return changelog[found.end() :].split("\n## ", 1)[0].strip("\n")
    return None


def is_prerelease(version: str) -> bool:
    return PRERELEASE.search(version) is not None


def disagreements(tag: str, project_version: str, changelog: str) -> list[str]:
    """Every way the tag, pyproject and the top CHANGELOG entry fail to name one version."""
    found = []
    if tag != f"v{project_version}":
        found.append(f"tag is {tag}, pyproject.toml says v{project_version}")
    top = top_version(changelog)
    if top != project_version:
        found.append(f"CHANGELOG's top entry is {top}, pyproject.toml says {project_version}")
    elif not (entry(changelog, project_version) or "").strip():
        found.append(f"CHANGELOG entry {project_version} is empty")
    return found


def _project_version(root: Path) -> str:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def main(argv: list[str], root: Path = REPO) -> int:
    if len(argv) != 2 or argv[0] not in {"check", "notes", "prerelease"}:
        print(__doc__, file=sys.stderr)
        return 2
    command, arg = argv
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    if command == "prerelease":
        return 0 if is_prerelease(arg) else 1
    if command == "notes":
        body = entry(changelog, arg)
        if body is None:
            print(f"CHANGELOG.md has no entry for {arg}", file=sys.stderr)
            return 1
        print(body)
        return 0
    problems = disagreements(arg, _project_version(root), changelog)
    for problem in problems:
        print(f"RELEASE MISMATCH {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
