"""235 — gate-4 TS field round is recorded (benchmark + playbook §4)."""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_BENCH = _REPO / "docs" / "benchmarks" / "235_typescript_field_round.md"
_PLAYBOOK = _REPO / "docs" / "ADAPTER_PLAYBOOK.md"

_REQUIRED_SHA = re.compile(r"`[0-9a-f]{40}`")
_REQUIRED_HEADINGS = (
    "## Corpus (pinned SHAs)",
    "## Builds",
    "## Nav-tool questions",
    "## Findings filed",
)


def test_benchmark_file_carries_pinned_shas_host_and_nav_table() -> None:
    text = _BENCH.read_text(encoding="utf-8")
    assert "Date:" in text and "Host:" in text
    shas = _REQUIRED_SHA.findall(text)
    assert len(shas) >= 2, f"need ≥2 pinned 40-char SHAs, found {len(shas)}"
    for heading in _REQUIRED_HEADINGS:
        assert heading in text, f"missing {heading}"
    assert "typescript-eslint" in text and "jsdoc" in text
    assert "determinism" in text.lower()
    assert "find_callers" in text and "find_references" in text and "find_implementations" in text


def test_playbook_gate4_no_longer_says_never_for_typescript() -> None:
    text = _PLAYBOOK.read_text(encoding="utf-8")
    # The indictment sentence that 235 retires.
    assert "never for TS" not in text
    assert "235_typescript_field_round.md" in text
    assert "Gate 4 has run for PHP, SQL, Python, and TypeScript" in text
