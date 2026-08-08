"""Task 059: design decision for the handler → template data-bag edge is recorded."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLAN = REPO / "docs" / "PLAN.md"
FOLLOW_UP = REPO / "docs" / "tasks" / "062_view-databag-producer.md"


def test_plan_records_option_1_producer_side_decision() -> None:
    text = PLAN.read_text(encoding="utf-8")
    assert "Option 1 — producer side only" in text
    assert "100" in text and "35" in text and "84" in text
    assert "language server does *not* solve" in text or "language server does not solve" in text
    assert "string key" in text.lower()


def test_follow_up_062_spells_contract_impact() -> None:
    assert FOLLOW_UP.is_file()
    text = FOLLOW_UP.read_text(encoding="utf-8")
    assert "contract_version" in text
    assert "EDGE_KINDS" in text or "edge kind" in text.lower()
    assert "enrichment" in text.lower()
    assert "PROVIDES_VIEW_DATA" in text or "view-scope" in text.lower()
