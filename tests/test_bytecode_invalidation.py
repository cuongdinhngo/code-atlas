"""Task 146: the gate must not report GREEN against bytecode that is not the source on disk.

A ``.pyc`` stores the source mtime in whole seconds plus its size. An edit inside the same second
that leaves the length unchanged keeps both fields matching, so the stale bytecode is imported and
the changed bytes are never read. ``scripts/gate.sh`` IS this repo's verification story, so that is
a false pass, not an inconvenience.

The fix is checked-hash invalidation (PEP 552). The tests below pin the hazard, the fix, and the
one property the fix's durability rests on.

**Task 190 — the premise is CONSTRUCTED, not raced.** These tests used to create "same second,
same size" by writing twice in quick succession and hoping both writes landed inside one clock
second. Under full-suite load they sometimes straddled the boundary, CPython then *correctly*
recompiled, and the hazard test failed claiming *"CPython changed"* — a guard failing for a reason
it does not forbid (R6.5's spirit). Every test here that writes twice now sets the source mtime
explicitly against the value the ``.pyc`` itself recorded, and asserts the premise before importing.
No sleep and no clock read decides anything (R4.2); the hazard is still the real filesystem
condition, so the guard is still observable failing (R6.5).
"""

from __future__ import annotations

import os
import re
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
# Task 020: adapter #4's fixtures are parser input, not modules — nothing imports them, and one
# is unparseable on purpose. Both spellings of the same corpus: a compileall `-x` regex (which
# sees an os-native separator) and ruff's directory exclude.
FIXTURE_DIR = "tests/fixtures/python"
FIXTURE_EXCLUDE = r"tests[/\\]fixtures[/\\]python[/\\]"

# PEP 552 pyc header word 1: bit 0 = hash-based, bit 1 = check_source.
_HASH_BASED = 0b01
_CHECK_SOURCE = 0b10
# Words 2 and 3 of a TIMESTAMP pyc: the source mtime in whole seconds, and the source size.
_MTIME_WORD = slice(8, 12)
_SIZE_WORD = slice(12, 16)


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


def _pyc_source_stamp(workdir: Path) -> tuple[int, int]:
    """The (mtime, size) a timestamp ``.pyc`` recorded for its source — the invalidation inputs."""
    cached = next((workdir / "__pycache__").glob("m.*.pyc"))
    header = cached.read_bytes()
    mtime: int = struct.unpack("<I", header[_MTIME_WORD])[0]
    size: int = struct.unpack("<I", header[_SIZE_WORD])[0]
    return mtime, size


def _stamp_source(module: Path, mtime: int) -> None:
    """Set the source's mtime to a whole second — the filesystem half of the hazard, constructed.

    This is not a mock: the importer still reads a real mtime from a real file and makes its own
    decision. What is removed is the race that decided which second the second write landed in.
    """
    os.utime(module, (mtime, mtime))


def _compile_checked_hash(workdir: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", COMPILEALL, "-q", "-f", "--invalidation-mode", "checked-hash", "."],
        cwd=workdir,
        capture_output=True,
        check=True,
    )


def test_ac4_a_same_second_same_size_edit_is_a_stale_import(tmp_path: Path) -> None:
    """The hazard, reproduced — with its premise CONSTRUCTED and asserted first (190 AC1).

    Both bodies are the same length by construction; the mtime is then set back to the second the
    ``.pyc`` recorded, so "same second, same size" is a stated fact rather than a hoped-for one.
    """
    module = tmp_path / "m.py"
    _write(module, "V = 1\n")
    assert _import_value(tmp_path) == 1
    stamped_mtime, stamped_size = _pyc_source_stamp(tmp_path)
    _write(module, "V = 2\n")
    _stamp_source(module, stamped_mtime)

    assert module.read_text(encoding="utf-8") == "V = 2\n"
    assert _pyc_flags(tmp_path) & _HASH_BASED == 0, "timestamp invalidation is the hazard's premise"
    # The premise, asserted rather than raced for: both pyc invalidation inputs still match.
    assert int(module.stat().st_mtime) == stamped_mtime, "the same-second half of the premise"
    assert module.stat().st_size == stamped_size, "the same-size half of the premise"

    assert _import_value(tmp_path) == 1, "if this reads 2, CPython changed and 146 can be dropped"


def test_a_write_that_straddles_a_second_is_why_the_old_guard_flaked(tmp_path: Path) -> None:
    """190 AC2: the flake's own trigger, made deliberate — so it is a case, not a coin toss.

    Bump the source one second past what the ``.pyc`` recorded and CPython recompiles, correctly.
    That is exactly what a slow full-suite run used to produce at random, and the hazard test then
    failed under the message *"CPython changed"* — reporting a property of the machine as a
    property of the interpreter. Pinning it here is what shows the race is gone rather than quiet:
    the two outcomes are now selected by an explicit mtime, and nothing is left to timing.
    """
    module = tmp_path / "m.py"
    _write(module, "V = 1\n")
    assert _import_value(tmp_path) == 1
    stamped_mtime, _ = _pyc_source_stamp(tmp_path)
    _write(module, "V = 2\n")
    _stamp_source(module, stamped_mtime + 1)

    assert int(module.stat().st_mtime) != stamped_mtime, "the straddle, constructed"
    assert _import_value(tmp_path) == 2, (
        "a differing mtime is a correct recompile — and the reason the old guard's failure said "
        "nothing about 146's hazard"
    )


def test_ac4_checked_hash_reads_the_source_that_is_on_disk(tmp_path: Path) -> None:
    """The same edit, with the fix in place: the source wins because the pyc is hashed.

    190 AC4: this sibling wrote twice as well, and a straddled second would have let it pass for the
    WRONG reason — a timestamp pyc would also have recompiled. The mtime is pinned back to the
    second the timestamp pyc recorded, so the hash is the only thing that can explain the 2.
    """
    module = tmp_path / "m.py"
    _write(module, "V = 1\n")
    assert _import_value(tmp_path) == 1
    stamped_mtime, _ = _pyc_source_stamp(tmp_path)
    _compile_checked_hash(tmp_path)
    _write(module, "V = 2\n")
    _stamp_source(module, stamped_mtime)

    assert int(module.stat().st_mtime) == stamped_mtime, "no mtime difference is available to help"
    assert _pyc_flags(tmp_path) & _HASH_BASED, "so only the hash can account for the 2"
    assert _import_value(tmp_path) == 2


def test_ac3_a_checked_hash_pyc_stays_checked_hash_when_the_import_rewrites_it(
    tmp_path: Path,
) -> None:
    """Converting once must keep the tree converted, or the gate step protects only its own run."""
    module = tmp_path / "m.py"
    _write(module, "V = 1\n")
    assert _import_value(tmp_path) == 1
    stamped_mtime, _ = _pyc_source_stamp(tmp_path)
    _compile_checked_hash(tmp_path)
    assert _pyc_flags(tmp_path) & _HASH_BASED
    _write(module, "V = 7\n")
    # 190 AC4: the third double-writer. Same pin, same reason — the rewrite must be the hash's work.
    _stamp_source(module, stamped_mtime)
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


def test_020_the_python_fixture_corpus_is_skipped_by_both_python_gates_and_nothing_else() -> None:
    """The exclusion must cover the fixture corpus exactly — never a line of the authored suite.

    Widened to ``tests``, compileall would stop converting the modules 146 exists to convert and
    ruff would stop reading them, both silently: the false GREEN this file was written against.
    """
    for text in (GATE.read_text(encoding="utf-8"), CI.read_text(encoding="utf-8")):
        assert f"-x '{FIXTURE_EXCLUDE}'" in text
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert f'extend-exclude = ["{FIXTURE_DIR}"]' in pyproject

    swept = sorted((REPO / "tests").rglob("*.py"))
    rx = re.compile(FIXTURE_EXCLUDE)
    skipped = [p for p in swept if rx.search(p.relative_to(REPO).as_posix())]
    # The file that actually breaks the step: if it is not skipped, the exclusion is spelt wrong.
    assert REPO / FIXTURE_DIR / "syntax_error.py" in skipped
    assert all(p.relative_to(REPO).as_posix().startswith(f"{FIXTURE_DIR}/") for p in skipped)
    assert len(swept) - len(skipped) > 150, "the exclusion swallowed the authored suite"
