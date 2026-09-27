"""R2.4 — no anchor-repo or client identifier survives anywhere in the tracked tree (task 325).

R2.2 bans a repo's names from *adapter and core source*, because a parser that knows a customer's
directory layout has stopped implementing the language. That is a correctness rule, and R2.3
deliberately leaves `tests/` and `scripts/` unswept so they can name the pinned public repos.

This is a different rule with a different blast radius: **disclosure**. The anchor repo is a client
codebase, and its schema objects, class names and tracker keys had spread into `docs/tasks/`,
fixtures and test assertions — every one of them outside R2.2's scope. Three manual sweeps were
needed to clear it, and the second existed only because the first read its own grep output three
lines at a time. A sweep cannot certify itself; this is the certificate.

Two detectors, because neither is sufficient alone:

* **Vocabulary** — exact tokens, matched by digest so the denylist is not itself the disclosure
  (`tests/contract/anchor_vocabulary_hashes.txt` says why). Catches a name pasted back verbatim.
* **Structure** — shapes that are client-specific whatever the client is: tracker keys, corporate
  domains, a real account's home directory, a Windows domain login. Catches the *next* leak, whose
  vocabulary no list can hold yet.

What neither catches, recorded rather than implied: a term that is also ordinary English. `resident`
appears 1,277 times in this repo meaning a resident language server, so it cannot be banned. Those
were handled by replacement, and a fresh paste of one would pass here.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from scripts.identity_markers import (
    CORPORATE_TLD,
    EMAIL,
    HASHES,
    HOME_DIR,
    STRUCTURAL,
    TOKEN,
    WINDOWS_LOGON,
    banned_digests,
    email_allowed,
)
from scripts.identity_markers import digest as _digest

REPO = Path(__file__).resolve().parent.parent

# Prefixes that look like a tracker key but are standards or this repo's own de-identified
# stand-in. Anything else with this shape is a real ticket in someone's tracker.
# `PRE-172` is this repo's own "state before ticket 172" notation, not a ticket in a tracker.
ALLOWED_KEY_PREFIXES = frozenset(
    {"FIELD", "PRE", "SHA", "ISO", "UTF", "RFC", "PSR", "PEP", "CVE", "CL"}
)
# All-letter prefix, two or more: a one-letter `S-12` is a scenario label and `L26-27` a line
# range, and both are this repo's own notation, not anyone's ticket.
TRACKER_KEY = re.compile(r"\b([A-Z]{2,10})-\d{2,6}\b")

# Binary and generated paths carry no prose; `.git` is not tracked. Nothing else is exempt —
# the point of this gate is that no directory is out of scope.
SKIP_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".db", ".woff", ".woff2")


BANNED = banned_digests()


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True
    ).stdout
    return [REPO / p.decode() for p in out.split(b"\0") if p]


def _readable_text(path: Path) -> str | None:
    if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def test_the_denylist_is_present_and_substantial() -> None:
    """R6.5 — an empty digest file would make the vocabulary sweep pass vacuously."""
    assert HASHES.is_file(), f"{HASHES} is missing; the vocabulary sweep would check nothing"
    assert len(BANNED) >= 80, (
        f"the denylist shrank to {len(BANNED)} — was a term dropped instead of fixed?"
    )
    assert all(re.fullmatch(r"[0-9a-f]{16}", d) for d in BANNED), "a denylist line is not a digest"


def test_the_sweep_actually_reaches_the_tree() -> None:
    """R6.5 — the same vacuity trap one level up: a green sweep over zero files is not a pass."""
    files = _tracked_files()
    assert len(files) > 500, f"only {len(files)} tracked files found; `git ls-files` is not working"
    assert any(f.name == "AGENTS.md" for f in files)


def test_no_banned_vocabulary_token_appears_in_any_tracked_file() -> None:
    """The exact-token arm. Failure names the digest, never the word — see the denylist header."""
    offences: list[str] = []
    for path in _tracked_files():
        text = _readable_text(path)
        if text is None:
            continue
        for match in TOKEN.finditer(text):
            whole = match.group(0)
            for candidate in {whole, *whole.split("-")}:
                digest = _digest(candidate)
                if digest in BANNED:
                    line = text.count("\n", 0, match.start()) + 1
                    rel = path.relative_to(REPO)
                    offences.append(f"{rel}:{line} matched banned digest {digest}")
    assert not offences, (
        "anchor/client vocabulary is back in the tree. Look each digest up in your local "
        "de-identification map, replace the term with its stand-in, and do not paste the word "
        "into a tracked file to silence this:\n  " + "\n  ".join(sorted(set(offences))[:20])
    )


def test_no_foreign_tracker_key_appears_in_any_tracked_file() -> None:
    """An uppercase prefix, a dash and digits is a ticket in a tracker; ours are stood in for."""
    offences: list[str] = []
    for path in _tracked_files():
        text = _readable_text(path)
        if text is None:
            continue
        for match in TRACKER_KEY.finditer(text):
            if match.group(1) in ALLOWED_KEY_PREFIXES:
                continue
            line = text.count("\n", 0, match.start()) + 1
            offences.append(f"{path.relative_to(REPO)}:{line} {match.group(0)}")
    assert not offences, (
        "a foreign tracker key is in the tree — renumber it under the FIELD- stand-in, or add the "
        "prefix to ALLOWED_KEY_PREFIXES if it is a standard:\n  " + "\n  ".join(offences[:20])
    )


@pytest.mark.parametrize("label", sorted(STRUCTURAL))
def test_no_structural_identity_marker_appears_in_any_tracked_file(label: str) -> None:
    """The shapes that leak an employer or an account without naming one in this file."""
    pattern = STRUCTURAL[label]
    offences: list[str] = []
    for path in _tracked_files():
        text = _readable_text(path)
        if text is None:
            continue
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            offences.append(f"{path.relative_to(REPO)}:{line} {match.group(0)}")
    assert not offences, f"{label} found in the tree:\n  " + "\n  ".join(offences[:20])


def test_no_email_outside_the_allowed_domains() -> None:
    offences: list[str] = []
    for path in _tracked_files():
        text = _readable_text(path)
        if text is None:
            continue
        for match in EMAIL.finditer(text):
            if email_allowed(match.group(1)):
                continue
            line = text.count("\n", 0, match.start()) + 1
            offences.append(f"{path.relative_to(REPO)}:{line} {match.group(0)}")
    assert not offences, "an address outside the allowed domains:\n  " + "\n  ".join(offences[:20])


# ---------------------------------------------------------------- planted negative controls
# Each control is assembled at runtime so this file never contains the string it detects — the
# idiom `tests/contract/test_guardrail_gates.py` uses for the same reason (AC2 there).


def test_the_vocabulary_arm_fires_on_a_planted_term() -> None:
    """A guard that has never been made to fail is a guard nobody has tested."""
    planted = "Model" + "Resident"
    assert _digest(planted) in BANNED, "the control term is not on the denylist"
    assert _digest("GraphStore") not in BANNED, "an innocent core symbol must not be banned"


def test_the_tracker_arm_fires_on_a_planted_key_and_spares_ours() -> None:
    planted = "XYZ" + "-" + "1234"
    match = TRACKER_KEY.search(planted)
    assert match is not None and match.group(1) not in ALLOWED_KEY_PREFIXES
    ours = TRACKER_KEY.search("FIELD" + "-" + "891")
    assert ours is not None and ours.group(1) in ALLOWED_KEY_PREFIXES
    assert TRACKER_KEY.search("SHA" + "-" + "256").group(1) in ALLOWED_KEY_PREFIXES  # type: ignore[union-attr]


def test_the_structural_arms_fire_on_planted_markers() -> None:
    assert CORPORATE_TLD.search("acme" + ".com" + ".au")
    assert HOME_DIR.search("/home/" + "someone" + "/w/")
    assert not HOME_DIR.search("/home/" + "you" + "/project/")
    assert WINDOWS_LOGON.search("BIGCORP" + "\\" + "j.doe")
    assert EMAIL.search("a@" + "acme" + ".io")
