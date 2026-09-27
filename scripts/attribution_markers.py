"""R7.3 attribution markers — one definition site for the commit-message check CI and gate.sh run.

The pattern was a regex copied into `ci.yml` and `scripts/gate.sh`, and it knew only
`Co-authored-by:`, `Generated with` and the robot emoji. Four commits carrying a
`Claude-Session:` trailer and its session URL passed both, and reached the history the public
release was rewritten from. This module owns the markers; both callers run it over the change range.

Stdlib only: the CI `guardrails` job runs it on the runner's own `python3`, with no install step.

    python3 scripts/attribution_markers.py <rev-range>

Exit 0 clean, 1 an offence (named by commit and marker — never by the line, which would republish
a session link in a public CI log), 2 an empty or unreadable range, which must not pass vacuously
(R6.5).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# A trailer is a `Key:` at the start of a line, which is where git and GitHub read one; a message
# that only mentions the key mid-sentence is prose about the rule, not an attribution.
TRAILER_KEYS = ("co-authored-by", "claude-session", "generated-with", "generated-by")
TRAILER = re.compile(rf"^[ \t]*({'|'.join(TRAILER_KEYS)})[ \t]*:", re.IGNORECASE | re.MULTILINE)

MARKERS: dict[str, re.Pattern[str]] = {
    "attribution trailer": TRAILER,
    "a generated-with line": re.compile(r"generated with", re.IGNORECASE),
    "an assistant session link": re.compile(r"claude\.ai/code/session", re.IGNORECASE),
    "the robot emoji": re.compile("\U0001f916"),
}

# Commit boundary: NUL cannot appear in a commit message, so no message can forge one.
_LOG_FORMAT = "%H%x00%B%x00"


def message_offences(message: str) -> list[str]:
    """Which markers one commit message trips, by marker name only."""
    return [label for label, pattern in MARKERS.items() if pattern.search(message)]


def commit_attribution_offences(rev_range: str, repo: Path = REPO) -> tuple[int, list[str]]:
    """(commits read, offences) over ``rev_range``; raises CalledProcessError on a bad range."""
    out = subprocess.run(
        ["git", "log", f"--format={_LOG_FORMAT}", rev_range, "--"],
        cwd=repo, capture_output=True, check=True, text=True,
    ).stdout
    fields = out.split("\0")
    commits = [(sha.strip(), body) for sha, body in zip(fields[::2], fields[1::2], strict=False)]
    offences = [
        f"{sha[:12]}: {label}" for sha, body in commits for label in message_offences(body)
    ]
    return len(commits), offences


def main(argv: list[str], repo: Path = REPO) -> int:
    if len(argv) != 1:
        print("usage: attribution_markers.py <rev-range>", file=sys.stderr)
        return 2
    try:
        count, offences = commit_attribution_offences(argv[0], repo)
    except subprocess.CalledProcessError as error:
        print(f"R7.3 — cannot read range {argv[0]!r}: {error.stderr.strip()}", file=sys.stderr)
        return 2
    if count == 0:
        print(f"R7.3 — empty commit range {argv[0]!r}; this check would pass vacuously")
        return 2
    if offences:
        print("R7.3 — a co-author or AI-attribution marker in a commit message (reword it):")
        print("\n".join(f"  {line}" for line in offences))
        return 1
    print(f"R7.3 no AI-attribution trailer over {count} commit(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
