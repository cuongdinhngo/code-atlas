"""R2.4 identity markers — one definition site for the tree sweep and the commit-identity check.

`tests/test_no_client_identifiers.py` (325) sweeps every tracked file with these patterns. Commit
headers were read by nothing, and GitHub serves author and committer identity raw, so an employer
logon came back as the author of six commits one day after 325 rewrote it out (340). This module
owns the patterns; the test imports them, and CI and `scripts/gate.sh` run the check below over the
change range, as R7.3 does for commit messages.

Stdlib only: the CI `guardrails` job runs it on the runner's own `python3`, with no install step.

    python3 scripts/identity_markers.py <rev-range> [--ref "<label>=<ref name>" ...]

A `--ref` value is a branch or pull-request head ref, which GitHub serves raw and nothing else reads
(424, SEC-SC-16). An empty value is skipped; an offence names the label and arm, never the value.

Exit 0 clean, 1 an offence (named by commit, field and arm — never by the value, which a public
CI log would republish), 2 an empty or unreadable range, which must not pass vacuously (R6.5).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HASHES = REPO / "tests" / "contract" / "anchor_vocabulary_hashes.txt"

# Tokens are matched whole and lowercased; a hyphenated run is also checked in one piece, because
# `rac`-style repo slugs are hyphen-joined and neither half is distinctive on its own.
TOKEN = re.compile(r"[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*")

# Emails that are placeholders, the maintainer's public identity, or a vendor's bot.
ALLOWED_EMAIL_DOMAINS = frozenset(
    {"example.com", "example.org", "gmail.com", "cursor.com", "github.com", "noreply.github.com"}
)
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")

# A corporate second-level TLD names an employer; a home directory names a person; an uppercase
# token, a backslash and a username is a Windows logon and names both. None of these has to know
# *which* company to be a leak — which is why they outlive any word list.
CORPORATE_TLD = re.compile(r"\b[a-z0-9-]+\.(?:com|net|org|co)\.[a-z]{2}\b", re.IGNORECASE)
HOME_DIR = re.compile(r"/home/(?!you/|user/|dev/|runner/|ubuntu/)[a-z0-9_.-]+/")
# Not preceded by a separator or drive letter: `D:\PROJECTS\code-atlas` is a path, not a logon.
WINDOWS_LOGON = re.compile(r"(?<![\\:/\w])[A-Z]{4,}\\[a-z][a-z0-9._-]+\b")

STRUCTURAL: dict[str, re.Pattern[str]] = {
    "corporate domain": CORPORATE_TLD,
    "a real account's home directory": HOME_DIR,
    "a Windows domain logon": WINDOWS_LOGON,
}

# git log fields, in format order. NUL-separated so no identity value can forge a boundary.
IDENTITY_FIELDS = ("author name", "author email", "committer name", "committer email")
_LOG_FORMAT = "%H%x00%an%x00%ae%x00%cn%x00%ce"


def digest(token: str) -> str:
    return hashlib.sha256(token.lower().encode()).hexdigest()[:16]


def banned_digests() -> frozenset[str]:
    lines = HASHES.read_text(encoding="utf-8").splitlines()
    return frozenset(ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#"))


def email_allowed(domain: str) -> bool:
    domain = domain.lower()
    return domain in ALLOWED_EMAIL_DOMAINS or domain.endswith(".noreply.github.com")


def banned_tokens(text: str, banned: frozenset[str]) -> list[str]:
    """The digests of every banned token in ``text`` — digests, so a caller never echoes a word."""
    found: list[str] = []
    for match in TOKEN.finditer(text):
        whole = match.group(0)
        found.extend(d for d in map(digest, {whole, *whole.split("-")}) if d in banned)
    return found


def identity_offences(value: str, banned: frozenset[str]) -> list[str]:
    """Which arms one identity value trips, by arm name only."""
    arms = [label for label, pattern in STRUCTURAL.items() if pattern.search(value)]
    arms += [f"banned digest {d}" for d in banned_tokens(value, banned)]
    arms += ["email outside the allowed domains" for m in EMAIL.finditer(value)
             if not email_allowed(m.group(1))]
    return arms


def commit_identity_offences(rev_range: str, repo: Path = REPO) -> tuple[int, list[str]]:
    """(commits read, offences) over ``rev_range``; raises CalledProcessError on a bad range."""
    out = subprocess.run(
        ["git", "log", f"--format={_LOG_FORMAT}", rev_range, "--"],
        cwd=repo, capture_output=True, check=True, text=True,
    ).stdout
    banned = banned_digests()
    commits = [line.split("\0") for line in out.splitlines() if line]
    offences = [
        f"{sha[:12]} {field}: {arm}"
        for sha, *values in commits
        for field, value in zip(IDENTITY_FIELDS, values, strict=True)
        for arm in identity_offences(value, banned)
    ]
    return len(commits), offences


def ref_offences(refs: dict[str, str], banned: frozenset[str]) -> list[str]:
    """Which arms each non-empty ref name trips, as ``<label>: <arm>``."""
    return [
        f"{label}: {arm}"
        for label, value in refs.items()
        if value
        for arm in identity_offences(value, banned)
    ]


def _split_refs(argv: list[str]) -> tuple[list[str], dict[str, str]] | None:
    rest: list[str] = []
    refs: dict[str, str] = {}
    it = iter(argv)
    for arg in it:
        if arg != "--ref":
            rest.append(arg)
            continue
        label, sep, value = next(it, "").partition("=")
        if not sep or not label:
            return None
        refs[label] = value
    return rest, refs


def main(argv: list[str], repo: Path = REPO) -> int:
    split = _split_refs(argv)
    if split is None or len(split[0]) != 1:
        usage = 'usage: identity_markers.py <rev-range> [--ref "<label>=<name>" ...]'
        print(usage, file=sys.stderr)
        return 2
    (rev_range,), refs = split[0], split[1]
    try:
        count, offences = commit_identity_offences(rev_range, repo)
    except subprocess.CalledProcessError as error:
        print(f"R2.4 — cannot read range {rev_range!r}: {error.stderr.strip()}", file=sys.stderr)
        return 2
    if count == 0:
        print(f"R2.4 — empty commit range {rev_range!r}; this check would pass vacuously")
        return 2
    ref_found = ref_offences(refs, banned_digests())
    if offences:
        print("R2.4 — an employer/client marker in a commit identity (fix user.name/user.email, "
              "then rewrite these commits):")
        print("\n".join(f"  {line}" for line in offences))
    if ref_found:
        print("R2.4 — an employer/client marker in a ref name (rename the branch):")
        print("\n".join(f"  {line}" for line in ref_found))
    if offences or ref_found:
        return 1
    print(f"R2.4 commit identity ok over {count} commit(s), {sum(map(bool, refs.values()))} ref(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
