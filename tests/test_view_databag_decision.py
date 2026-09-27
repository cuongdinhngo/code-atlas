"""Design decision for the handler → template data-bag edge is recorded (task 059)."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLAN = REPO / "docs" / "PLAN.md"


def test_plan_records_option_1_producer_side_decision() -> None:
    text = PLAN.read_text(encoding="utf-8")
    assert "Option 1 — producer side only" in text
    # Discriminating count phrases — bare "100"/"35"/"84" already appear on main.
    assert "**100** sites in **35** handler files" in text
    assert "**296** / **84**" in text
    assert "excluding** ORM-contaminated `->with(`" in text or (
        "excluding" in text and "ORM-contaminated" in text and "->with(" in text
    )
    assert "language server does *not* solve" in text or "language server does not solve" in text
    assert "string key" in text.lower()

