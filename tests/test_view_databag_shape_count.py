"""AC1 for 063: publish-shape count + proceed call are recorded in the ticket Outcome."""

from __future__ import annotations

from pathlib import Path

TICKET = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "tasks"
    / "063_view-databag-array-keys.md"
)


def test_ac1_count_and_proceed_are_in_the_ticket_outcome() -> None:
    """The kill/proceed deliverable lives above the mango separator (ticket Outcome)."""
    text = TICKET.read_text(encoding="utf-8")
    raw, _, _ = text.partition("<!-- ===== MANGO WORKING DOC")
    assert "## Outcome" in raw
    assert "PROCEED" in raw
    assert "7,663" in raw or "7663" in raw
    assert "11,204" in raw or "11204" in raw
    assert "array-literal" in raw.lower() or "array literal" in raw.lower()
