"""Task 146: the gate must not report GREEN against bytecode that is not the source on disk.

A ``.pyc`` stores the source mtime in whole seconds plus its size. An edit inside the same second
that leaves the length unchanged keeps both fields matching, so the stale bytecode is imported and
the changed bytes are never read. ``scripts/gate.sh`` IS this repo's verification story, so that is
a false pass, not an inconvenience.

The fix is checked-hash invalidation (PEP 552). The tests below pin the hazard, the fix, and the
one property the fix's durability rests on.
"""

from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "scripts" / "gate.sh"
CI = REPO / ".github" / "workflows" / "ci.yml"
COMPILEALL = "compileall"
CHECKED_HASH = "--invalidation-mode checked-hash"
TARGETS = ("code_atlas", "onboarding_llm", "tests")

# PEP 552 pyc header word 1: bit 0 = hash-based, bit 1 = check_source.
_HASH_BASED = 0b01
_CHECK_SOURCE = 0b10


def _write(module: Path, body: str) -> None:
    """Rewrite the module. Every body here is the same length, which is the whole point."""
    module.write_text(body, encoding="utf-8")


def _import_value(workdir: Path) -> int:
    """Import ``m`` in a fresh interpreter and report ``m.V`` as that interpreter saw it."""
    done = subprocess.run(
        [sys.executable, "-c", "import m; print(m.V)"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=True,
    )
    return int(done.stdout.strip())


def _pyc_flags(workdir: Path) -> int:
    cached = next((workdir / "__pycache__").glob("m.*.pyc"))
    return int(struct.unpack("<I", cached.read_bytes()[4:8])[0])


def _compile_checked_hash(workdir: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", COMPILEALL, "-q", "-f", "--invalidation-mode", "checked-hash", "."],
        cwd=workdir,
        capture_output=True,
        check=True,
    )


def test_ac4_a_same_second_same_size_edit_is_a_stale_import(tmp_path: Path) -> None:
    """The hazard, reproduced. Both writes land in one second and are the same length."""
    module = tmp_path / "m.py"
    _write(module, "V = 1\n")
    assert _import_value(tmp_path) == 1
    _write(module, "V = 2\n")
    assert module.read_text(encoding="utf-8") == "V = 2\n"
    assert _pyc_flags(tmp_path) & _HASH_BASED == 0, "timestamp invalidation is the hazard's premise"
    assert _import_value(tmp_path) == 1, "if this reads 2, CPython changed and 146 can be dropped"


def test_ac4_checked_hash_reads_the_source_that_is_on_disk(tmp_path: Path) -> None:
    """The same edit, with the fix in place: the source wins because the pyc is hashed."""
    module = tmp_path / "m.py"
    _write(module, "V = 1\n")
    assert _import_value(tmp_path) == 1
    _compile_checked_hash(tmp_path)
    _write(module, "V = 2\n")
    assert _import_value(tmp_path) == 2


def test_ac3_a_checked_hash_pyc_stays_checked_hash_when_the_import_rewrites_it(
    tmp_path: Path,
) -> None:
    """Converting once must keep the tree converted, or the gate step protects only its own run."""
    module = tmp_path / "m.py"
    _write(module, "V = 1\n")
    _compile_checked_hash(tmp_path)
    assert _pyc_flags(tmp_path) & _HASH_BASED
    _write(module, "V = 7\n")
    assert _import_value(tmp_path) == 7  # a real change: the interpreter rewrites the pyc
    flags = _pyc_flags(tmp_path)
    assert flags & _HASH_BASED and flags & _CHECK_SOURCE, "invalidation mode decayed on rewrite"


def test_ac1_the_gate_converts_bytecode_before_it_imports_the_tree() -> None:
    text = GATE.read_text(encoding="utf-8")
    assert COMPILEALL in text and CHECKED_HASH in text
    for target in TARGETS:
        assert target in text.split(COMPILEALL, 1)[1].split("\n\n", 1)[0]
    # Before the first step that imports the tree, or it converts bytecode already read this run.
    assert text.index(COMPILEALL) < text.index("from code_atlas.main import")
    assert text.index(COMPILEALL) < text.index("\"$bin/pytest\"")


def test_ac2_ci_carries_the_same_step_as_the_gate() -> None:
    """A check in one and not the other means one of them is lying about what was verified."""
    text = CI.read_text(encoding="utf-8")
    assert COMPILEALL in text and CHECKED_HASH in text
    assert text.index(COMPILEALL) < text.index("pytest -q")
