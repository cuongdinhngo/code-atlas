"""The bookkeeping rules in ENGINEERING_RULES.md R7.2, enforced instead of asked for.

Two rules govern every task and neither had a guard: status is kept in sync in **both** the backlog
table and the task's frontmatter, and a task's token spend is recorded before its PR. They were held
by a lifecycle gate, so work arriving by another path skipped them silently — which is exactly how
task 024 shipped without a token row.

The reader below is derived, not positional (task 132). It finds the `Status` column by reading the
table's own header row and bounds the Token-usage section at the next heading, because the previous
version hard-coded the column index and bounded the section on a heading the file had stopped
having — a guard that keeps passing while its inputs move under it.

The ledger moved to `TOKEN_LEDGER.md` in task 133 (it was 4,773 tokens of tier 1). Only the two
paths below changed; every assertion is the one 132 left.

Task 218 narrowed the sync invariant rather than dropping it. A closed ticket no longer keeps a
BACKLOG row (it was 8,797 of an 8,800-token budget, 208 of 214 rows naming what the task file
already named), so `set(BACKLOG) == set(tasks)` had to go. What replaces it is not weaker: an
**open** task must have a row that agrees with its frontmatter, a **done** task must have a ledger
row and must **not** have a row here, and no task may fall through both — the same "a task cannot
go untracked" the old equality bought, minus the copy R7.6 forbids.
"""

import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parent.parent / "docs"
BACKLOG = DOCS / "BACKLOG.md"
LEDGER = DOCS / "TOKEN_LEDGER.md"
TASKS = DOCS / "tasks"

STATUSES = ("todo", "in-progress", "blocked", "deferred", "done")
FRONTMATTER_STATUS = re.compile(r"^status:\s*(\S+)\s*$", re.MULTILINE)
TASK_ID = re.compile(r"^\|\s*(\d{3})\s*\|")
HEADING = re.compile(r"^##\s+(.*)$", re.MULTILINE)
TOKEN_SECTION = "Token usage"


def task_files() -> dict[str, Path]:
    return {path.name[:3]: path for path in sorted(TASKS.glob("[0-9][0-9][0-9]_*.md"))}


def frontmatter_status(path: Path) -> str:
    found = FRONTMATTER_STATUS.search(path.read_text(encoding="utf-8"))
    assert found, f"{path.name} has no status in its frontmatter"
    return found.group(1)


def cells(row: str) -> list[str]:
    """The row's cells, without the empty strings the leading and trailing pipes produce."""
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def section(path: Path, title: str) -> str:
    """One `## ` section's body, bounded by the next `## ` heading — never by a named one.

    Bounding on a specific following heading is how the previous reader ran to EOF for months:
    the heading it partitioned on had been renamed away, so the Token-usage table silently
    extended over everything after it.
    """
    text = path.read_text(encoding="utf-8")
    starts = [match for match in HEADING.finditer(text) if match.group(1).strip() == title]
    assert len(starts) == 1, f"{path.name} has {len(starts)} '## {title}' sections, expected 1"
    body_from = starts[0].end()
    following = HEADING.search(text, body_from)
    return text[body_from : following.start() if following else len(text)]


def column_index(body: str, name: str) -> int:
    """Position of a named column, read from the first table header in this section."""
    for line in body.splitlines():
        if line.startswith("|") and name in cells(line):
            return cells(line).index(name)
    raise AssertionError(f"no table in this section has a {name!r} column")


def rows_by_id(body: str) -> dict[str, list[str]]:
    """Every `| NNN | …` row in a section, keyed by task id, as cell lists."""
    found: dict[str, list[str]] = {}
    for line in body.splitlines():
        match = TASK_ID.match(line)
        if match:
            found[match.group(1)] = cells(line)
    return found


def backlog_statuses() -> dict[str, str]:
    """Task id -> status, across every Open-work and phase table in BACKLOG.

    No longer bounded above the ledger: since 133 the ledger is a different file, so every
    `| NNN | … |` row still in BACKLOG belongs to a status table. A section with no such row, or
    with no `Status` column, is skipped rather than partitioned around.
    """
    head = BACKLOG.read_text(encoding="utf-8")
    statuses: dict[str, str] = {}
    for match in HEADING.finditer(head):
        body = head[match.end() : ]
        next_heading = HEADING.search(body)
        body = body[: next_heading.start()] if next_heading else body
        rows = rows_by_id(body)
        if not rows:
            continue
        index = column_index(body, "Status")
        for task_id, row in rows.items():
            statuses[task_id] = row[index]
    return statuses


def token_rows() -> dict[str, tuple[str, str]]:
    body = section(LEDGER, TOKEN_SECTION)
    return {task_id: (row[1], row[2]) for task_id, row in rows_by_id(body).items() if len(row) > 2}


def test_the_guard_has_something_to_check() -> None:
    """Guards the guard: a reader that silently stopped matching would pass every check below.

    Every count here is derived from the tree, so none of them can be satisfied by a stale floor.
    """
    tasks = task_files()
    statuses = backlog_statuses()
    assert tasks, "no task files found — the glob is broken"
    assert statuses, "no BACKLOG row parsed — the row reader is broken"
    assert set(statuses) <= set(tasks), (
        f"BACKLOG rows for tasks that do not exist: {sorted(set(statuses) - set(tasks))}"
    )
    on_disk = {task_id: frontmatter_status(path) for task_id, path in tasks.items()}
    done = {task_id for task_id, status in on_disk.items() if status == "done"}
    assert done, "no task reads as done — the frontmatter status is not being read"
    assert done <= set(token_rows()), (
        f"done tasks with no token row: {sorted(done - set(token_rows()))}"
    )
    # Every task is tracked by exactly one of the two: a BACKLOG row, or a closing ledger row.
    untracked = {task_id for task_id in tasks if task_id not in statuses and task_id not in done}
    assert not untracked, (
        f"tasks with neither a BACKLOG row nor a done status: {sorted(untracked)}"
    )


def test_a_closed_ticket_leaves_the_backlog() -> None:
    """R7.6, task 218: a `done` row here is a third naming of the task file and its ledger row.

    Made to fail: restore any one of the 208 rows 218 removed and this reports it by id.
    """
    lingering = sorted(task_id for task_id, row in backlog_statuses().items() if row == "done")
    assert not lingering, (
        f"BACKLOG still carries {len(lingering)} `done` row(s): {lingering}. A closing ticket's "
        "row goes in the same commit that adds its TOKEN_LEDGER.md spend row (R7.2, R7.6)."
    )


def test_the_token_ledger_reads_only_its_own_rows() -> None:
    """No spend row may come from outside the ledger's own section.

    The previous reader partitioned the tail on `## Suggested order` — a heading BACKLOG.md does
    not have — so the ledger ran to end of file and any `| NNN | … | … |` row in a later section
    counted as a recorded spend. Made to fail: a three-cell row planted after the ledger's own
    section is read as task 999's spend by that reader and by this one is not read at all.
    """
    stray = set(token_rows()) - set(task_files())
    assert not stray, f"the token ledger read rows for non-existent tasks: {sorted(stray)}"


@pytest.mark.parametrize("task_id", sorted(task_files()))
def test_status_matches_in_both_places(task_id: str) -> None:
    # R7.2: an *open* task's status is kept in sync in the backlog table *and* its frontmatter.
    in_file = frontmatter_status(task_files()[task_id])
    assert in_file in STATUSES, f"task {task_id}: {in_file!r} is not a known status"
    if in_file == "done":
        # Carried by its ledger row from here on — see test_a_closed_ticket_leaves_the_backlog.
        return
    assert backlog_statuses().get(task_id) == in_file, (
        f"task {task_id}: BACKLOG says {backlog_statuses().get(task_id)!r}, "
        f"its frontmatter says {in_file!r}"
    )


@pytest.mark.parametrize("task_id", sorted(task_files()))
def test_a_finished_task_records_what_it_cost(task_id: str) -> None:
    """R7.2: no PR without the token spend recorded — so no `done` task without a row."""
    if frontmatter_status(task_files()[task_id]) != "done":
        return

    row = token_rows().get(task_id)
    assert row is not None, (
        f"task {task_id} is done but has no row in TOKEN_LEDGER.md's Token usage table "
        "(ENGINEERING_RULES.md R7.2)"
    )
    spend, pull_request = row
    assert "dispatch" in spend or "fresh" in spend, (
        f"task {task_id}: {spend[:40]!r} names no measured spend"
    )
    assert pull_request.startswith("[#"), f"task {task_id}: no PR link, got {pull_request[:40]!r}"
