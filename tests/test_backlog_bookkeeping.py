"""The bookkeeping rules in AGENTS.md, enforced instead of asked for.

Two rules govern every task and neither had a guard: status is kept in sync in **both** the backlog
table and the task's frontmatter, and a task's token spend is recorded before its PR. They were held
by a lifecycle gate, so work arriving by another path skipped them silently — which is exactly how
task 024 shipped without a token row.
"""

import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parent.parent / "docs"
BACKLOG = DOCS / "BACKLOG.md"
TASKS = DOCS / "tasks"

STATUSES = ("todo", "in-progress", "blocked", "done")
FRONTMATTER_STATUS = re.compile(r"^status:\s*(\S+)\s*$", re.MULTILINE)
# `| 006 | [PHP adapter spike](…) | M0 | done | 002 |` — id, title, milestone, status, deps.
TASK_ROW = re.compile(r"^\|\s*(\d{3})\s*\|[^|]*\|[^|]*\|\s*([a-z-]+)\s*\|", re.MULTILINE)
# `| 006 | PHP adapter spike | …tokens… | [#13](…) |` — id, title, spend, PR link.
TOKEN_ROW = re.compile(
    r"^\|\s*(\d{3})\s*\|[^|]*\|\s*(\S[^|]*?)\s*\|\s*(\S[^|]*?)\s*\|", re.MULTILINE
)


def task_files() -> dict[str, Path]:
    return {path.name[:3]: path for path in sorted(TASKS.glob("[0-9][0-9][0-9]_*.md"))}


def frontmatter_status(path: Path) -> str:
    found = FRONTMATTER_STATUS.search(path.read_text(encoding="utf-8"))
    assert found, f"{path.name} has no status in its frontmatter"
    return found.group(1)


def backlog_sections() -> tuple[str, str]:
    """Split the backlog at the token table, so a task row is never read as a token row."""
    text = BACKLOG.read_text(encoding="utf-8")
    head, _, tail = text.partition("## Token usage")
    assert tail, "BACKLOG.md has no Token usage section"
    tokens, _, _ = tail.partition("## Suggested order")
    return head, tokens


def backlog_statuses() -> dict[str, str]:
    return dict(TASK_ROW.findall(backlog_sections()[0]))


def token_rows() -> dict[str, tuple[str, str]]:
    return {row[0]: (row[1], row[2]) for row in TOKEN_ROW.findall(backlog_sections()[1])}


def test_the_guard_has_something_to_check() -> None:
    # Guards the guard: a regex that silently stopped matching would pass every check below.
    assert len(task_files()) >= 24
    assert len(backlog_statuses()) == len(task_files())
    assert len([task for task in backlog_statuses().values() if task == "done"]) >= 7
    assert len(token_rows()) >= 7


@pytest.mark.parametrize("task_id", sorted(task_files()))
def test_status_matches_in_both_places(task_id: str) -> None:
    # AGENTS.md: status is kept in sync in the backlog table *and* the task's frontmatter.
    in_file = frontmatter_status(task_files()[task_id])
    assert in_file in STATUSES, f"task {task_id}: {in_file!r} is not a known status"
    assert backlog_statuses().get(task_id) == in_file, (
        f"task {task_id}: BACKLOG says {backlog_statuses().get(task_id)!r}, "
        f"its frontmatter says {in_file!r}"
    )


@pytest.mark.parametrize("task_id", sorted(task_files()))
def test_a_finished_task_records_what_it_cost(task_id: str) -> None:
    """AGENTS.md: no PR without the token spend recorded — so no `done` task without a row."""
    if frontmatter_status(task_files()[task_id]) != "done":
        return

    row = token_rows().get(task_id)
    assert row is not None, (
        f"task {task_id} is done but has no row in BACKLOG's Token usage table "
        "(AGENTS.md, 'Token usage on PR')"
    )
    spend, pull_request = row
    assert "dispatch" in spend or "fresh" in spend, (
        f"task {task_id}: {spend[:40]!r} names no measured spend"
    )
    assert pull_request.startswith("[#"), f"task {task_id}: no PR link, got {pull_request[:40]!r}"
