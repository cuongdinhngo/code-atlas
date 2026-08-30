"""The SQL adapter must STREAM the file, not build a whole-file AST (task 184, C2 / AC5).

The anchor's normal shape is one ~240k-line `.sql` file, and a whole-file parse is the failure mode
the PHP adapter already has on multi-MB input.

**AC5 is measured on the BYTE axis at a fixed symbol count, and the reason is a finding.** AC5's
first wording — "peak RSS constant in input size" — is not satisfiable by ANY adapter: §4.1
answers one JSON object per file, so every adapter holds that file's whole node list before it
can emit. Growth in the SYMBOL count is the contract's, not this scanner's. Growth in BYTES at a
fixed symbol count is exactly what a whole-file AST causes and a stream does not, so that is the
axis with a defect behind it. The second test pins the symbol axis as bounded, not unmeasured.

Stated as a ratio, not an absolute: an MB ceiling passes an AST-building parser whenever the input
happens to be small. The absolute backstop only stops a runaway swapping for minutes.
"""

from __future__ import annotations

import resource
from pathlib import Path

from tests.sql_adapter_cli import CLI, needs_node

THIN_FILLER = 8_000
FAT_FILLER = 400_000
GROWTH_CEILING = 1.25
ABSOLUTE_KB = 512 * 1024

pytestmark = needs_node


def _write_bytes_axis(path: Path, filler_lines: int) -> None:
    """Two symbols, and as many non-symbol bytes as asked for — the multi-MB single-file shape."""
    with path.open("w", encoding="utf-8") as handle:
        handle.write("CREATE PROCEDURE dbo.Only\nAS\nBEGIN\n")
        for index in range(filler_lines):
            handle.write(f"    -- filler line carrying bytes but not one symbol {index:08d}\n")
        handle.write("    EXEC dbo.Other;\nEND\nGO\n")


def _write_symbol_axis(path: Path, procs: int) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for index in range(procs):
            handle.write(
                f"CREATE PROCEDURE dbo.Generated_{index}\nAS\nBEGIN\n"
                f"    EXEC dbo.Generated_{max(index - 1, 0)};\nEND\nGO\n"
            )


def _run(path: Path) -> tuple[int, dict]:
    """Peak child RSS across the ONE shared `--file` spawn (147 AC4 — never a second copy here)."""
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    result = CLI.parse_file(path)
    after = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return max(after, before), result


def test_peak_rss_is_constant_in_input_size(tmp_path: Path) -> None:
    """AC5: bytes grow ~50x at a FIXED symbol count; peak RSS must not follow them."""
    thin, fat = tmp_path / "thin.sql", tmp_path / "fat.sql"
    _write_bytes_axis(thin, THIN_FILLER)
    _write_bytes_axis(fat, FAT_FILLER)
    ratio = fat.stat().st_size / thin.stat().st_size
    assert ratio > 20, f"the two inputs must differ in scale (got {ratio:.1f}x)"

    thin_kb, thin_result = _run(thin)
    fat_kb, fat_result = _run(fat)

    # Correctness first: a scanner that read nothing would also use no memory.
    assert len(thin_result["nodes"]) == len(fat_result["nodes"]) == 2
    assert [e["target_raw"] for e in fat_result["edges"] if e["kind"] == "CALLS"] == ["dbo.Other"]

    growth = fat_kb / thin_kb
    assert growth < GROWTH_CEILING, (
        f"peak child RSS grew {growth:.2f}x ({thin_kb} KB -> {fat_kb} KB) while the input grew "
        f"{ratio:.1f}x at an unchanged symbol count. C2 requires streaming: a whole-file AST is "
        "what killed the PHP adapter on this shape."
    )
    assert fat_kb < ABSOLUTE_KB, f"peak child RSS {fat_kb} KB exceeds the {ABSOLUTE_KB} KB backstop"


def test_the_symbol_axis_is_bounded_not_constant(tmp_path: Path) -> None:
    """The other axis, pinned rather than left unmeasured — and it belongs to §4.1, not to us.

    One JSON object per file means every adapter holds the file's whole node list before it
    emits, so
    memory here is O(symbols) by the contract. What must hold is that it stays bounded per symbol.
    """
    small, large = tmp_path / "small.sql", tmp_path / "large.sql"
    _write_symbol_axis(small, 2_000)
    _write_symbol_axis(large, 20_000)

    small_kb, small_result = _run(small)
    large_kb, large_result = _run(large)
    assert len(small_result["nodes"]) == 2_001
    assert len(large_result["nodes"]) == 20_001

    per_symbol_kb = (large_kb - small_kb) / (20_000 - 2_000)
    assert per_symbol_kb < 8, (
        f"{per_symbol_kb:.2f} KB of peak RSS per emitted symbol ({small_kb} -> {large_kb} KB). "
        "The node list is the contract's cost; anything much above it is the scanner retaining "
        "source it should have released."
    )
    assert large_kb < ABSOLUTE_KB
