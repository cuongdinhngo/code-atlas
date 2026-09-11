"""Every shipped adapter has a suffix in the Claude Code poke snippet (task 200, AC2).

036 froze `"if": "Edit(*.php)|Write(*.php)"` when PHP was the only adapter. TS/JS (019) and T-SQL
(184/022) landed since, so a TypeScript edit drifted the index and nothing poked it. The snippet is
now generated from each adapter's own declared suffixes, and this is the guard that keeps it true.

The denominator is `shipped_adapters()`, so adapter #4 is covered the moment its directory exists —
R6.7, and the reason the fixture control below can exist at all.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import gen_skill  # noqa: E402


def _filter_string() -> str:
    """The poke hook's filter, selected by command name — 240 added a second hook to this file,
    so a positional lookup would silently start grading the wrong one."""
    snippet = json.loads(gen_skill.CLAUDE_CODE_SNIPPET_PATH.read_text(encoding="utf-8"))
    filters = [
        hook["if"]
        for entries in snippet["hooks"].values()
        for entry in entries
        for hook in entry["hooks"]
        if hook["command"] == "code-atlas-poke"
    ]
    assert len(filters) == 1, f"expected exactly one poke hook, found {len(filters)}"
    return filters[0]


def uncovered_adapters(filter_string: str, adapters_dir: Path | None = None) -> list[str]:
    """Shipped adapters with none of their declared suffixes in the snippet's filter."""
    declared = gen_skill.declared_extensions(adapters_dir)
    return sorted(
        name
        for name, suffixes in declared.items()
        if not any(f"(*{suffix})" in filter_string for suffix in suffixes)
    )


def test_every_shipped_adapter_has_a_suffix_in_the_poke_snippet() -> None:
    assert uncovered_adapters(_filter_string()) == []


def test_a_fourth_adapter_with_no_coverage_is_caught(tmp_path: Path) -> None:
    # R6.5: the guard is observed failing. A new adapter directory is red until the snippet moves.
    for name in gen_skill.shipped_adapters():
        (tmp_path / name).mkdir()
        (tmp_path / name / "index.js").write_text(
            f'export const x = {{ extensions: [".{name}x"] }};\n', encoding="utf-8"
        )
    (tmp_path / "ruby").mkdir()
    (tmp_path / "ruby" / "index.rb").write_text('extensions: [".rb"]\n', encoding="utf-8")
    assert "ruby" in uncovered_adapters(_filter_string(), tmp_path)


def test_the_declaration_reader_is_not_vacuous() -> None:
    # R6.5: an empty suffix set would make the coverage check pass by finding nothing to check.
    declared = gen_skill.declared_extensions()
    assert declared, "no shipped adapters were read at all"
    assert all(suffixes for suffixes in declared.values()), (
        f"an adapter declares no suffix, so its coverage is unfalsifiable: {declared}"
    )
