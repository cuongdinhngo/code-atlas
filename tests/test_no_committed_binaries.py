"""424 — SEC-SC-14: no unreviewable binary is committed.

A tracked file is binary when its first 8 KB holds a NUL byte (git's own test). A reviewer cannot
read one, and a binary can hide an executable, so each needs a named exception with its reason.
Today there is one, and it is a source file, not an artifact. A stale exception fails, and a planted
binary proves the sweep refuses one.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SNIFF = 8192

# path -> why a reviewer can still read it. Every entry must still be binary-by-NUL (no stale rows).
ALLOWED = {
    "adapters/typescript/src/imports.js": (
        "JavaScript source with one literal NUL byte inside a template-literal cache key (370); "
        "it diffs as text everywhere but git's NUL sniff"
    ),
}


def is_binary(head: bytes) -> bool:
    return b"\0" in head


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        check=True,
        text=True,
        timeout=60,
    ).stdout
    return sorted(f for f in out.split("\0") if f)


def binaries(root: Path, files: list[str]) -> list[str]:
    found = []
    for name in files:
        path = root / name
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as handle:
            if is_binary(handle.read(SNIFF)):
                found.append(name)
    return found


def test_no_committed_file_is_an_unlisted_binary() -> None:
    files = tracked_files()
    assert len(files) > 500, "git ls-files returned almost nothing; this would pass vacuously"
    found = binaries(REPO, files)
    assert [f for f in found if f not in ALLOWED] == []
    assert sorted(set(ALLOWED) - set(found)) == [], (
        "an allow-list entry is no longer binary; drop it"
    )


def test_a_planted_binary_is_refused(tmp_path: Path) -> None:
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\0\0\0\rIHDR")
    (tmp_path / "late.bin").write_bytes(b"text " * 100 + b"\0")
    (tmp_path / "notes.md").write_text("plain text\n", encoding="utf-8")
    (tmp_path / "past.bin").write_bytes(b"x" * SNIFF + b"\0")
    names = ["logo.png", "late.bin", "notes.md", "past.bin"]
    assert binaries(tmp_path, names) == ["logo.png", "late.bin"]
