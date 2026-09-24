---
id: 320
slug: column-defaults-dead-ends-on-an-unqualified-table
title: "check_column_defaults answers a bare table name with a dead-end no_such_symbol — the exact-qname partition 165-C1 already ruled on, and the one tool where the bare name is what a caller types"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [194, 022]
---

## Why this exists (field retro, 2026-09-22 — FIELD-891/1583/1611 batch)

A field session asked `check_column_defaults` whether `FormInstance.Status` / `ModifiedDate`
declared a DEFAULT. It answered **`no_such_symbol`, empty** — and the agent concluded the tool
"can't reach the schema because the DDL lives in migration `.sql`", rated it **3/10**, and answered
the question with raw `sys.columns` / `sys.default_constraints` queries instead. The defaults
existed (`DEFAULT((1))` / `DEFAULT(getdate())`).

**That diagnosis was wrong, and the payload is why it was reachable.** The SQL adapter does index
this DDL: `CREATE TABLE` and `ALTER TABLE … ADD` emit `Table` + `Column` on `CONTAINS`, and both
DEFAULT spellings are parsed — the inline clause and `ALTER TABLE t ADD CONSTRAINT n DEFAULT (expr)
FOR col` (`adapters/sql/src/ddl.js:424`, `:523`). What failed is the **lookup**: the tool does one
exact `nodes_by_qualified_name(table, kind="Table")` (`check_column_defaults.py:198`), and a SQL
qname is schema-qualified and file-independent by CONVENTION §3 — so the bare `FormInstance`
can never match the stored `dbo.FormInstance`.

**The repo has already ruled on this shape.** Claim `165-C1` (`LESSONS.md:807`,
`disclose-a-partition-as-a-partition`): *"a tool answer scoped to one qname is a partition when the
subject shares its identity slot with definitions under other qnames; disclose the siblings and mark
the answer `authoritative: false` rather than presenting the partition as the whole."* It was closed
in `find_callers` by adding a `nodes_by_name` sibling query beside the exact one
(`nav_result.attach_sibling_definitions:929`). `check_column_defaults` never received the same
treatment, and its envelope (`:139-157`) carries **no** `try_instead`, no candidate list, no hint
that the name wants a schema — unlike `search_symbol`, which routes a near-miss to `file_outline`,
and `read_symbol`, which refuses ambiguity with `ambiguous_definitions` (070/078). This is the
second sighting of `165-C1`, which is the promotion gate (P1).

It matters disproportionately here because this is the one tool whose subject a caller types from a
**database** mental model, where the bare table name is the name — not from a symbol the index
already handed them.

## Goal

A bare, unqualified table name reaches the table it plainly names, or is refused with the qualified
candidates that would reach it — never a bare `no_such_symbol` that reads as "this table does not
exist".

## Scope / Deliverables

1. **A name fallback beside the exact lookup** in `check_column_defaults.create` — when
   `nodes_by_qualified_name(table, kind="Table")` misses, query `nodes_by_names(table,
   kind="Table")`. Contract-kind branch only; no language branch (R1.1).
2. **One candidate → answer about it, and say so.** Report the resolved `qualified_name` in the
   envelope (the subject the answer is about is not the string that was passed), so a reader never
   has to assume which table was measured. The `column` argument composes against the **resolved**
   qname, not the raw one (`f"{table}::{column}"` at `:208`).
3. **Two or more candidates → refuse and list them**, following `read_symbol`'s 078 precedent: no
   rows, and `ambiguous_definitions` naming each qualified candidate — one schema's table must not
   be measured while the others go unmentioned.
4. **Zero candidates → keep `no_such_symbol`, but stop the dead end.** Attach `try_instead`
   pointing at `search_symbol(kind="Table")`, the way a `substring_match` page already routes to
   `file_outline` (245/093).

## Constraints

- **061** — a call that already resolves exactly stays byte-identical; the new fields ride only the
  fallback, ambiguous and empty arms.
- **R5.6** — a resolved-by-fallback answer must be distinguishable from an exact hit; do not sign
  them alike.
- **R1.1** — the fallback keys on `kind="Table"`, never on a language or a schema-name convention.
- **R1.4** — the name query goes through `GraphStore`; no SQL in the tool.
- **R4.2** — candidate order is deterministic.
- Comments ≤ 3 lines (R7.5).

## Acceptance criteria

- **AC1** `check_column_defaults(table="FormInstance")` against a fixture holding
  `dbo.FormInstance` returns that table's defaulted columns, and the envelope names the
  resolved qualified subject.
- **AC2** With the same bare name held by two schemas, the call returns **no rows** and lists both
  qualified candidates — a red-arm test proves one schema's answer is never returned alone.
- **AC3** A genuinely absent table still answers `no_such_symbol`, now carrying `try_instead`.
- **AC4** Regression: an exactly-qualified call's payload is byte-identical to today's (061).
- **AC5** `LESSONS.md` claim `165-C1` gains this incident on its `seen:` line — the gate P1 reads.

## Out of scope

- Indexing anything new; the DDL is already indexed and this ticket touches no adapter.
- Dynamic DDL inside `EXEC` / `sp_executesql` — that is genuinely unreadable here and is
  [321](321_dynamic-ddl-in-migrations-leaves-no-trace.md).
- Extending the fallback to other tools; do it when a second tool is sighted, not before (R1.2).

## References
`code_atlas/tools/check_column_defaults.py:198` (exact lookup), `:139-157` (envelope), `:208`
(column composition); `code_atlas/store.py:1671` (`nodes_by_qualified_name`), `:1677`
(`nodes_by_names`); `code_atlas/tools/nav_result.py:929` (`attach_sibling_definitions`);
`adapters/sql/src/ddl.js:424`, `:523`; `docs/LESSONS.md:807` (claim `165-C1`);
`tests/test_check_column_defaults.py`; CONVENTION §3; AGENT_BRIEF P1.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 320 — check_column_defaults bare table name (working doc)

- **Ticket:** 320 · local
- **Type:** bug
- **Repo(s) / Porting:** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed · path: docs/tasks/320_column-defaults-dead-ends-on-an-unqualified-table.md
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** finalise — next: push branch, open PR

## Phase 0 — Refine

`PREMISE: 10 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

Recalled: `165-C1` (`disclose-a-partition-as-a-partition`, `LESSONS.md:807`) — the ticket names it; the change threads a resolved qname through the tool's callers of `_columns_of` / `_sources`.

refine skipped: 0 unresolved product-decisions — each arm (1 / ≥2 / 0 candidates) is prescribed by the ticket.

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 6 decomposed | ROWS: C=6 R=4 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | bare name reaches its table or is refused with qualified candidates | three arms after the exact miss | D1 | AC1–AC3 | ✅ |
| R1 | Scope 1 | name fallback beside the exact lookup, `kind="Table"` | `store.nodes_by_name(table, kind="Table")` on miss | D1 | AC1 | ✅ |
| R2 | Scope 2 | one candidate → answer, envelope names the resolved qname; column composes on it | `resolved_qname`; `wanted` uses resolved | D1 | AC1 + column test | ✅ |
| R3 | Scope 3 | ≥2 → no rows + `ambiguous_definitions` naming each qualified candidate | `subject_ambiguous`, sites carry `qname` | D1 | AC2 | ✅ |
| R4 | Scope 4 | 0 → `no_such_symbol` + `try_instead` search_symbol(kind=Table) | `attach_try_instead` + hint | D1 | AC3 | ✅ |
| C1 | Constraints | 061 exact call byte-identical | new fields only on fallback/ambiguous/empty arms | D1 | AC4 | ✅ |
| C2 | Constraints | R5.6 fallback distinguishable from exact | `resolved_qname` present only on fallback | D1 | AC1 AC4 | ✅ |
| C3 | Constraints | R1.1 keys on kind, not language/schema | `kind="Table"` only | D1 | gate R1.1 | ✅ |
| C4 | Constraints | R1.4 name query through GraphStore | existing `nodes_by_name` | D1 | review | ✅ |
| C5 | Constraints | R4.2 deterministic candidate order | `_NODE_ORDER` (qname) | D1 | AC2 order assert | ✅ |
| C6 | Constraints | comments ≤ 3 lines | R7.5 | D1 | review | ✅ |
| AC1 | AC | bare `FormInstance` → dbo table's defaulted columns + resolved subject named | integration via SQL adapter | D2 | proving | ✅ |
| AC2 | AC | two schemas → no rows, both candidates listed | red-arm test | D2 | proving | ✅ |
| AC3 | AC | absent → `no_such_symbol` + `try_instead` | integration | D2 | proving | ✅ |
| AC4 | AC | exact call byte-identical | literal captured pre-change | D2 | proving | ✅ |
| AC5 | AC | `165-C1` `seen:` gains 320 | LESSONS edit + assertion | D3 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

- Q1 (self-resolved): `definition_sites` (`nav_result.py:1012`) emits `{file, line, kind}` only, and two schemas' tables can share a file — so AC2's "lists both qualified candidates" needs `qname` on each site; added for this tool only (ticket Scope 3 "naming each qualified candidate").

## Phase 1 — Analysis

- Root cause (`logic`): `check_column_defaults.py:198` does one exact `nodes_by_qualified_name(table, kind="Table")`; a SQL qname is schema-qualified (CONVENTION §3), so a bare name can never match and falls to a bare `no_such_symbol` with no route (`:199-206`).
- Blast radius: one tool; `_columns_of`, `_sources`, `has_unlinked_writes_relating_to` take the table qname — all must get the resolved one. No other tool changes (Out of scope, R1.2).

`TRACK: backend — 0/3 touched files under UI paths`

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ the fallback keys on kind Table only · R1.4 (change-type) ✅ nodes_by_name is a GraphStore method · R4.2 (change-type) ✅ candidates in _NODE_ORDER · R5.6 (change-type) ✅ resolved_qname marks the fallback answer · R7.2 (change-type) ✅ ledger row and BACKLOG removal`

Baseline record — tree `660281a140e52a4ccd0a71f1e43bfd9b639c79bc` (historical, shared with 313/323). Command `.venv/bin/python -m pytest -q --tb=line -p no:cacheprovider` → `4376 passed, 4 skipped`.

`BASELINE: green`

## Phase 2 — Design

- Approach:
  - A1 after the exact miss, `store.nodes_by_name(table, kind="Table", limit=page_limit)`; distinct qnames decide the arm.
  - A2 one candidate: measure it (`_columns_of`, `_sources`, the column composition and `writers_partial` all on the resolved qname); envelope keeps `table` as asked and adds `resolved_qname` via `attach_resolved_qname`.
  - A3 two or more: `reason=subject_ambiguous`, empty results, `ambiguous_definitions` = `definition_sites` plus each site's `qname`.
  - A4 none: `no_such_symbol` plus `try_instead: search_symbol` and a hint naming `kind="Table"`.
  - A5 the exact arm is untouched.
- Rejected: `classify_missing_subject` (suffix match over every kind; its `name_not_qualified` arm carries a count, not the candidates AC2 needs, and it would change which arm a qualified miss takes); a case-insensitive match (T-SQL folds case, but the ticket asks for the name index; recorded as a follow-up).

**Assumptions:** a SQL `Table` node's `name` is the bare table name — verified (probe: `nodes_by_name('FormInstance', kind='Table')` → `audit.FormInstance`, `dbo.FormInstance`, qname order).

| Handle | Answer |
|--------|--------|
| `disclose-a-partition-as-a-partition` | traced — see below |

Trace record — pre-change tree `660281a140e52a4ccd0a71f1e43bfd9b639c79bc` (historical: a design trace must read the code before the change). Command `grep -n "nodes_by_qualified_name(table\|_columns_of(store, table)\|has_unlinked_writes_relating_to(table)\|{table}::{column}\|_sources(store, table)" code_atlas/tools/check_column_defaults.py`:

```
197:            if not store.nodes_by_qualified_name(table, kind="Table", limit=1):
206:            all_columns, columns, declarations = _columns_of(store, table)
208:                wanted = column if "::" in column else f"{table}::{column}"
221:            unmeasured = _sources(store, table)
248:            if writers and store.has_unlinked_writes_relating_to(table):
```

All five consumers of the table qname are in the change list (D1): the partition is disclosed (≥2 → refuse) rather than one schema measured.

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | name fallback, three arms, resolved qname threaded, docstring | code_atlas/tools/check_column_defaults.py | its callers only (MCP surface); existing `tests/test_check_column_defaults.py` exact-arm tests | R1–R4 C1–C6 | 1/1 |
| D2 | proving tests AC1–AC5 | tests/test_column_defaults_bare_table.py | new file | AC1–AC5 | 1/1 |
| D3 | `165-C1` seen; ticket; BACKLOG; TOKEN_LEDGER; TOOLS row if it names the lookup | docs/LESSONS.md · docs/tasks/320_… · docs/BACKLOG.md · docs/TOKEN_LEDGER.md | bookkeeping tests | AC5 R7.2 | 1/1 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | integration (SQL adapter indexes real DDL, tool reads the graph) | n/a | ✅ |
| AC2 | integration | integration | n/a | ✅ |
| AC3 | integration | integration | n/a | ✅ |
| AC4 | integration | integration (literal captured on main) | n/a | ✅ |
| AC5 | logic | unit (reads LESSONS.md) | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_column_defaults_bare_table.py -q`

Rollback: revert the branch. Porting: single repo.

`SCOPE: S` (unchanged)

## Phase 3 — Execute

**Branch:** fix/320-column-defaults-bare-table

Pre-change record — tree `660281a` plus the uncommitted proving test (historical): `.venv/bin/python -m pytest tests/test_column_defaults_bare_table.py -q` → `5 failed, 1 passed` (the pass is AC4, the regression that must hold both sides).

Sweep record — tree `56372584b7233db16d36fe5dd0572d813d01295b` (historical: superseded by the Phase 4 gate run). Commands `git diff --name-only main..HEAD`, the two test files, mypy:

```
code_atlas/tools/check_column_defaults.py
docs/BACKLOG.md
docs/LESSONS.md
docs/TOOLS.md
docs/tasks/320_column-defaults-dead-ends-on-an-unqualified-table.md
tests/test_column_defaults_bare_table.py
13 passed in 2.55s
Success: no issues found in 93 source files
```

`ruff format` was not run over `check_column_defaults.py` wholesale: it would also rewrap pre-existing line 208, which this change does not touch.

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed — A1–A5 implemented-as-approved`

## Phase 4 — Review

REVIEWER: OFF (--no-reviewer)
CHALLENGER: ON — round-1 CLEAN (22 of 22 met, 0 not met, 0 can't tell). Observation, no verdict: a qname defined in two files would list both sites — accurate (two definition sites), not changed.

Verdict: `clean (challenger only — REVIEWER: OFF)`

Ran at 5177220efd19954d16643e6a056a177a39ec2b56

```
$ scripts/gate.sh
== summary ==
  20 passed · 0 failed · 0 skipped
GATE GREEN — all 20 checks passed
```

The first gate run (at `475f754`) was `19 passed · 1 failed`: `test_backlog_bookkeeping` wanted this ticket's ledger row, which needs the PR link. Code is unchanged between the two runs.

`REVIEW: CLEAN`
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`

`Reviewed at 475f754de4fcb5b74f771fbda2b0303749dbc1a2` · reviewed files: code_atlas/tools/check_column_defaults.py, tests/test_column_defaults_bare_table.py, docs/LESSONS.md, docs/TOOLS.md, docs/BACKLOG.md · working doc (embedded, staleness-exempt): docs/tasks/320_column-defaults-dead-ends-on-an-unqualified-table.md

## Phase 5 — Finalise

Outward (handover-authorised only): push `fix/320-column-defaults-bare-table`, open the PR. Never merge.

Durable lesson: `165-C1` (`disclose-a-partition-as-a-partition`) seen 165, 320 → a recurring type-2 code claim. Proposed destination: `docs/ENGINEERING_RULES.md` via codify's provisional→ratify — **not written**; ratification is the maintainer's, and `/mango:promote` is the cross-ticket pass. Falsification: still true — `nav_result.attach_sibling_definitions` and `test_find_callers_discloses_sibling_definitions_on_a_twin` exist; both sightings carry a test.

Follow-up (not ticketed): T-SQL resolves names case-insensitively; the fallback matches the stored name exactly.

Revert: revert the PR.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| review | challenger | 1 | 79,985 |

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`
`LEDGER TOTAL: 79,985 (subagent dispatch only) · top cost driver: review/challenger round 1`
