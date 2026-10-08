---
id: 371
slug: sql-statement-in-a-host-string-beyond-php
title: 'A TS or Python string that begins an INSERT, DELETE or EXEC writes nothing, so a table lists only its PHP and SQL writers'
phase: 2
milestone: Coverage
status: done
depends_on: [278, 281, 335, 364]
---

## Why this exists

278/281/335 taught the PHP adapter to read a string literal that *begins* a SQL statement:
`adapters/php/src/SqlLiteral.php` takes a leading keyword and one object name and requires the
clause that keyword needs (`insert` → `(`/`values`/`select`, `update` → `set`, `delete` → `where`,
`exec` → a parameter). `insert`/`update`/`merge` give `WRITES`, `delete` gives `DELETES`, `exec`
gives `CALLS`. Prose such as "Update settings" has no clause and emits nothing. It never keys on a
wrapper's name (R2.2). Measured with each adapter's `--file` mode on 2026-10-08:

- **TypeScript:** `db.query("INSERT INTO dbo.Items (a) VALUES (1)")`, a template `DELETE FROM …
  WHERE`, `"UPDATE … SET"` and `"EXEC dbo.Proc @p"` emit only `CALLS "query"`.
- **Python:** `cursor.execute("INSERT INTO …")`, an f-string `DELETE`, `"EXEC dbo.Insert_Order ?"`
  emit only `CALLS "execute"`.

So `find_references` on a table, and `find_callers` on a proc, cover PHP and SQL callers only in a
repo whose Node or Python layer talks to the same database.

## Scope

1. Each adapter ports the **recogniser's shape**, not its code (R1.1/R2): its own string-literal
   visitor, the same keyword → kind map, the same required-clause guard against prose. Template /
   f-string heads count only when the object name closes inside the literal part, as PHP's `$closed`.
2. Python's parameter markers (`?`, `%s`, `:name`) and TS's (`?`, `$1`, `@p`) satisfy the `exec`
   guard. Which dialects the guard reads is declared, never assumed (playbook §6, 228).
3. Measure first, as 281 did: a pinned TS and Python sample, the count of literals that match,
   and how many of them are prose. A sample with no hits is a finding, not a pass — and an edge
   links only where the repo indexes the DDL the SQL adapter reads (T-SQL). If the measurement finds
   no linkable hits, the ticket closes `wontdo` with the numbers, and no code lands.
4. One recogniser, three copies: a shared fixture table in `tests/contract/` (literal → expected
   kind and target) that the PHP, TS and Python adapters all pass, so the copies cannot drift.

## Acceptance criteria

- **AC1:** On a TS fixture, `find_references dbo.Items` lists the `INSERT` literal's site.
- **AC2:** On a Python fixture, `find_callers dbo.Insert_Order` lists the `EXEC` literal's site.
- **AC3:** `"Update settings"` / `"delete this?"` emit nothing in either adapter.
- **AC4:** The Scope 3 measurement is recorded in this file before any adapter code is written.
- **AC5:** All three adapters pass the shared literal table (Scope 4).
- **AC6:** ADAPTER_PLAYBOOK §1.1's host-string row reads `371` for both adapters.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 371 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges #44–#48, then this PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`, batch 367 → 368 → 369 → 370 → 373 → 371 → 372;
  *"with skipped reviewers"* = `--no-reviewer` only (AGENTS.md), the challenger keeps its seat.
- Branch `feat/371-sql-statement-in-a-host-string-beyond-php`, stacked on `feat/373-python-path-loaded-module-imports-nothing`
  (both edit the Python and TS walks); its PR targets that branch. Contract `.mango/run-contract-371.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 9 unresolved surfaced | 1 want-decision asked | 8 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Premise.** `SqlLiteral.php`, its call site (`Visitor.php`, `enterSqlLiteral`, `continuedLiterals`),
the pinned samples and their cache resolve; `--file` confirmed TS/Python emit only `CALLS "query"`.

**Recall (by handle).** `361-C1` `read-a-literal-by-its-structure-not-a-regex` — a literal is read by
the parser's string node, never a regex over source text; the ports read cooked literal nodes.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 47,885 tokens) surfaced X1–X8; the
main loop added X9.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | what "no linkable hits" means | want | **ASSUMED (delegated by the handover):** one linkable site keeps the ticket; the measurement found 38 |
| X2 | offline measurement | how | the cached pins, `--skip-clone` |
| X3 | the libraries hold no DB code | how | both counts are recorded: the libraries' prose and the samples repo's linkable sites |
| X4 | order | how | measure → record (`50dcac1c`) → table → ports |
| X5 | the shared table's form | how | JSON in `tests/contract/`, written into each language's own spelling and run through `--file` |
| X6 | the dialect the `EXEC` guard reads | how | PHP's markers plus each host's drivers': DB-API `%s`/`%(name)s` (PEP 249) for Python, `$1` for TS; declared in the table's `markers` and both READMEs |
| X7 | concatenation and tagged templates | how | PHP's rule: the literal before `+` is cut short; a template head is never closed; a tagged template is read |
| X8 | contract | how | no move: `WRITES`, `DELETES`, `CALLS` exist |
| X9 | strings no driver runs | how | a docstring or bare string statement (Python, TS), a type, a module specifier, a member's name (TS) |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=4 G=1 AC=6`
`CLARIFICATION: 9 raised | 9 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/16 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

The base is 373's tip. `scripts/gate.sh` on `main` (`e0d84cf1`): `GATE GREEN — all 21 checks passed`.
Ran at e0d84cf1.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "cover PHP and SQL callers only" | a table lists its TS/Python writers too | ✅ |
| C1 | Scope 1 | "the recogniser's shape, not its code (R1.1/R2)" | own parser, same map and guard | ✅ |
| C2 | Why | "never keys on a wrapper's name (R2.2)" | statement grammar only | ✅ |
| R1 | Scope 1 | template / f-string heads close only inside the literal | X7 | ✅ |
| R2 | Scope 2 | each host's parameter markers satisfy `EXEC`; declared | X6 | ✅ |
| R3 | Scope 3 | measure first, `wontdo` on no linkable hits | the measurement section | ✅ |
| R4 | Scope 4 | one shared table all three adapters pass | | ✅ |
| AC1 | AC | `find_references dbo.Items` lists the TS `INSERT` | | ✅ |
| AC2 | AC | `find_callers dbo.Insert_Order` lists the Python `EXEC` | | ✅ |
| AC3 | AC | "Update settings" / "delete this?" emit nothing | | ✅ |
| AC4 | AC | the measurement recorded before adapter code | `50dcac1c` precedes the code | ✅ |
| AC5 | AC | all three adapters pass the shared table | | ✅ |
| AC6 | AC | playbook row reads 371 for both | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — the TS `INSERT` and template `DELETE` and the Python f-string `UPDATE` sites | |
| AC2 | yes — exactly `jobs.orders.place` line 2 | |
| AC3 | yes — no site on either prose line | |
| AC4 | yes — `git log` order | |
| AC5 | yes — `tests/contract/test_sql_literal_agreement.py`, one case per adapter | |
| AC6 | yes — the row reads `371 \| 371` | |

### Blast radius

- Both adapters' literal handling; a new module per adapter; a new contract-suite table.
- Contract, parity, PHP/TS/Python suites: `402 passed`.

### Rule sections

`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ no core change · §R2.2 (change-type) ✅ no driver or method name · §R3.4 (change-type) ✅ the contract suite gains the table every adapter passes · §R5.2 (change-type) ✅ HEURISTIC, as PHP · §R6.3 (change-type) ✅ the measurement is a committed reporter · §R6.7 (recalled handle) ✅ literals read from the parser's string nodes`

## Phase 2 — design

### Approach

1. `adapters/python/src/sql_literal.py` and `adapters/typescript/src/sqlLiteral.js`: the shape, with
   each host's markers in the `EXEC` guard.
2. Each walk reads a value-position string or a template/f-string head, marks the literal before
   `+` as cut short, and emits the edge at `HEURISTIC` on the keyword's source line.
3. `tests/contract/sql_literal_cases.json` + `test_sql_literal_agreement.py`: one table, three adapters.
4. READMEs, playbook §1.1, TOOLS.md, CHANGELOG.

### Rejected alternatives

- **One shared implementation** — the adapters share no runtime (R1.1/R1.3); the table is the seam.
- **Keying on `execute`/`query`** — a driver's name (R2.2).

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | reporter | `scripts/sql_literal_report.py` (new) | — | R3, AC4 | 1/1 |
| 2 | Python port | `adapters/python/src/sql_literal.py` (new), `adapters/python/src/parse.py` | Python emission | C1, C2, R1, R2 | 2/2 |
| 3 | TS port | `adapters/typescript/src/sqlLiteral.js` (new), `adapters/typescript/src/parse.js` | TS emission | C1, C2, R1, R2 | 2/2 |
| 4 | shared table | `tests/contract/sql_literal_cases.json`, `tests/contract/test_sql_literal_agreement.py` (new) | contract suite | R4, AC5 | 2/2 |
| 5 | proving test | `tests/test_sql_in_a_host_string.py` (new) | — | AC1–AC3 | 1/1 |
| 6 | docs | both READMEs, `docs/ADAPTER_PLAYBOOK.md`, `docs/TOOLS.md`, `CHANGELOG.md` | doc budget | AC6 | 5/5 |
| 7 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `tests/test_backlog_bookkeeping.py` | — | 4/4 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`read-a-literal-by-its-structure-not-a-regex`** — traced: `grep -n "isStringLiteral\|isTemplateExpression\|ast.Constant\|ast.JoinedStr" adapters/*/src/parse.*`
  — each port reads the parser's literal node and its cooked text; the regex only reads that text.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC3 | integration | real TS + Python + SQL build, `find_references`, `find_callers` | authored | ✅ |
| AC4 | real corpus | `scripts/sql_literal_report.py` on the pins | pinned | ✅ |
| AC5 | adapter | the shared table through each `--file` | authored | ✅ |
| AC6 | doc | the playbook row | — | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 1 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_sql_in_a_host_string.py tests/contract/test_sql_literal_agreement.py`.

### Rollback

`git revert`; the next build drops the edges.

## Phase 3 — execute

Commits `50dcac1c` (measurement, before any code) and `271772d7` (ports, table, tests, docs).
**Red first:** the shared table failed for TS and Python and passed for PHP; the integration test on
the prior parsers `2 failed, 1 passed`. **P8:** `cross_repo_validate.py --public-only --skip-clone`
11 ok / 0 failed; flask's edges 7368→7373 (its tutorial's statements against its own `schema.sql`),
every other count unchanged; floors hold.

**Sweep.** Axis 1: `git diff --name-only feat/373-python-path-loaded-module-imports-nothing..HEAD` =
items 1–6; `ruff check`, `mypy` (core, Python adapter), `tsc --checkJs --strict` clean. Axis 2: as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `271772d7`, 79,980 tokens): 7 met · 1 not met · 1 can't tell.**

1. **F1 (medium): TS read a type literal, a module specifier, a member name.** **Fixed** — only a
   string a program runs is read.
2. **F2: Python counted the cooked text's `\n`.** **Fixed** — the source's own line breaks.
3. **F3: the table lacks line and continuation cases.** **Fixed** in the adapter tests (the line rule
   differs by language — PHP's `'\n'` is no newline — so it cannot be one shared row).
4. **F4 (can't tell, AC4): the reporter is not the ports.** **Fixed** — `--ports` counts what the
   adapters emit; the numbers agree (measurement section).
5. **F5: a `%`- or `.format()`-ed literal reads as whole.** **Left:** PHP's same shape; documented.
6. **F6 (not met, AC6): "Every port closed in 367–373" was not true.** **Fixed** — "367–371 and 373".
7. **F7: the status was still `todo` at review.** Bookkeeping, this commit.

All in `7125ef16` (red on the prior parsers: `2 failed, 3 passed`). Verify-only (main loop):

Ran at 7125ef16:
```
$ .venv/bin/python -m pytest -q tests/test_sql_in_a_host_string.py tests/contract/test_sql_literal_agreement.py
8 passed
```

`Ph3/4 proven by`: G1, C1, C2, R1–R4, AC1–AC6 — 13/13.

Verdict: **clean (challenger only — REVIEWER: OFF)** — the not-met and can't-tell items landed.

Reviewed at 7125ef16 — the diff `feat/373-python-path-loaded-module-imports-nothing..7125ef16`. Working doc:
`docs/tasks/371_sql-statement-in-a-host-string-beyond-php.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `7125ef16` only bookkeeping changes — this doc, `docs/BACKLOG.md`,
`docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`, all exempt.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

No new lesson. Per P1, `361-C1` gains 371 (traced in Phase 2).

### Outward actions

1. Push `feat/371-sql-statement-in-a-host-string-beyond-php` — pre-authorised.
2. Open the PR against `feat/373-python-path-loaded-module-imports-nothing` — pre-authorised.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 47,885 |
| 2 | review | `challenger`, round 1 | 79,980 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 127,865 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits.

**Gate.** `scripts/gate.sh` on `44ede84b`: `GATE GREEN — all 21 checks passed` (Linux, bare pytest).

## Measurement (Scope 3 · AC4) — recorded before any adapter code

`scripts/sql_literal_report.py` (committed, re-runnable, R6.3) ports `SqlLiteral.php`'s shape and
counts, per pinned checkout, every TS/JS and Python string literal led by `INSERT INTO` · `UPDATE` ·
`MERGE INTO` · `DELETE FROM` · `EXEC`, how many the clause guard accepts (*statements*), how many it
rejects (*prose*), and how many accepted targets name a table or procedure the checkout's own
`.sql` declares (*linkable*). Host dev-host, 2026-10-08, the cache of
`scripts/cross_repo_samples.json`'s pins (`--skip-clone`):

| sample (pin) | language | literals | keyword-led | statements | prose | linkable |
|---|---|---|---|---|---|---|
| ky | TS | 3,560 | 4 | 0 | 4 | 0 |
| mqttjs | TS | 3,178 | 0 | 0 | 0 | 0 |
| socketio | TS | 13,458 | 2 | 0 | 2 | 0 |
| flask | Python | 4,405 | 8 | 5 | 3 | 5 (its tutorial's own `schema.sql`) |
| pydantic | Python | 79,501 | 14 | 0 | 14 | 0 |
| requests | Python | 3,214 | 0 | 0 | 0 | 0 |
| sql-server-samples `fd84be9` (the `adventureworks_oltp` / `wwi_dw` pin, whole checkout) | Python | 2,259 | 12 | 12 | 0 | 12 |
| same | TS/JS | 111,850 | 35 | 26 | 9 | 26 |

**Reading.** The libraries hold no statement and every keyword-led literal there is prose the guard
rejects (20 of 20 across ky, socketio and pydantic) — a finding, not a pass. The one pinned repo whose
Node and Python layers talk to the database it declares — Microsoft's samples, 757 T-SQL objects —
has 38 linkable sites the PHP-only recogniser leaves unread. **The ticket goes ahead**; it does not
close `wontdo`.

**After the ports (review F4).** `scripts/sql_literal_report.py --ports` counts what the two adapters
themselves emit over the same checkouts: sql-server-samples Python 12 statements / 12 linkable, TS
26 / 26; flask 5 / 5; every other sample 0. The ports read exactly what the shape measured.
