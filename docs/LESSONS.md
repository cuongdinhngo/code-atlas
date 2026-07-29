# Lessons — code-atlas

Durable lessons discovered while shipping tasks: constraints found, wrong assumptions, process gaps.
One entry per lesson; newest first.

## 002 — A guard written before its consumers exist must be negative-controlled
Task 002's AC2(b) ("no field lists duplicated in store/indexer") was **vacuously true**: all five
schema-consuming modules were one-line stubs, so any grep or guard passed while proving nothing about
the tasks that would actually write them. A guard that cannot fail is not evidence. **Fix:** inject a
real violation (`COLUMNS = ["kind", "name", …]` appended to `store.py`), confirm the guard fails, then
remove it and confirm the file is byte-identical again — and assert the guard's own inputs are non-empty
(`len(VOCABULARY) == 38`, `len(consumers()) >= 5`) so it can't silently degrade to a no-op later.
Generalises: when an acceptance criterion is satisfied only because the thing it constrains doesn't
exist yet, say so out loud and either negative-control the guard or record the vacuity.

## 001 — Fold a mid-task governance request into the ticket's scope, don't ride it on the branch
When a user asks for a repo-wide rule change mid-task (here: the "Token usage on PR" rule in
`CLAUDE.md` + `docs/BACKLOG.md`), the ticket-blind challenger and the reviewer both read it as
untraceable scope creep — it maps to no ticket requirement. **Fix:** add it to the task's
Scope/Deliverables + a matrix row (task 001 → R6 + change-list item 8) with a one-line rationale, so
every hunk still traces to a requirement. Splitting it into its own docs ticket is the alternative;
either way, never let a change ride the branch untraceable to a row.
