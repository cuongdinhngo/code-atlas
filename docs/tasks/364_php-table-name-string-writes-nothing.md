---
id: 364
slug: php-table-name-string-writes-nothing
title: 'A PHP write that names its table as a string argument emits no WRITES, so find_references on a table lists SQL writers only'
phase: 2
milestone: Coverage
status: done
depends_on: [352, 278, 328]
---

## Why this exists

This comes from the anchor project's field retro.

- F1 (1 PR): `find_references dbo.Items` listed only the SQL writers (`authoritative: false`). A
  page's `Db::insertRow` on `'Items'` and an API model's `insert('Items')` were found with Grep.
- F2 (1 PR): another table's insert writers came back at `HEURISTIC` only and needed `git grep`.

278/281 read a PHP string that *begins* a T-SQL write. A wrapper call whose only argument naming
the table is the bare table name does not have that shape: `queryInsert('Items', $row)`,
`queryUpdate`, `queryDelete`. And 352 shipped as `keyed_calls` (222), which emits only `CALLS`,
never `WRITES` or `DELETES`.

## Scope

1. A `keyed_calls` rule gains an optional `kind` (`CALLS` by default; `WRITES` or `DELETES`). The
   target is the `Table` that `target_template` spells (e.g. `dbo.{key}`), so the schema stays in
   the rule file and no schema logic enters the core.
2. Rule edges carry `rule: true` at `HEURISTIC`. A name that matches no table stays unlinked and is
   counted in `unlinked_writes_count`.

## Acceptance criteria

- **AC1:** With a rule `queryInsert arg 0 → WRITES`, `find_references dbo.Items` lists the PHP call
  site beside the SQL writers.
- **AC2:** `check_column_defaults` keeps reading only writers that carry a column list. A rule edge
  without a column list is not reported as omitting every column.
- **AC3:** With no rule, the graph is unchanged.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 364 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges #36, then this PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`, batch 365 → 366 → 361 → 362 → 364 → 363;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `feat/364-php-table-name-string-writes-nothing`, stacked on `feat/361-js-route-strings-link-to-nothing`
  (`c17059cc`, PR #36): both extend `keyed_calls`. Its PR targets that branch. Contract `.mango/run-contract-364.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 3 want-decision asked | 5 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `keyed_calls` (`enrichment.py`), `unlinked_writes_count` (`find_references.py:88`),
`check_column_defaults`, 278/281's PHP T-SQL writes, the SQL adapter's default schema — all resolve.

**Recall (by handle).** `343-C2` `formatter-rewrites-untouched-lines`; `362-C1`
`widen-every-query-that-shares-the-page` (a rule edge of a new kind must reach every rule census).

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 59,447 tokens) surfaced X1–X8.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | AC2 | how | holds by construction: a Table-targeted writer is `unmeasured` for every column (`check_column_defaults.py:241-245`, CONVENTION §3); pinned by a test |
| X2 | Table vs Column target | how | Table only: a `::` in a `WRITES`/`DELETES` template is refused at load (R5.3) |
| X3 | `queryDelete` | how | `kind: DELETES`, Table-only per CONVENTION §3; its own test |
| X4 | linking | how | `WRITES` is in the resolver's case-insensitive arm (`resolver.py:26`); `DELETES` links on the exact qname only — documented in TOOLS.md |
| X5 | rule census reads CALLS only | how | `store.edges_by_target_raw(target_raw, kinds)`; the census reads every rule kind — a linked write was counted unresolved (`3 == 1` with the old lookup) |
| X6 | where an unlinked name is counted | want | **ASSUMED:** `rule_keys_unresolved` in the build report; `unlinked_writes_count` counts it under its own spelling, as for any writer (`store.py:2448`). Deviation from the ticket's single-field wording (P3) |
| X7 | a literal T-SQL write and a rule write at one site | want | **ASSUMED:** both stay — different evidence, `rule: true` tells them apart; sources are deduplicated in `writers_total` |
| X8 | AC2's bar | want | **ASSUMED:** the rule writer is in `unmeasured` and `writers_total`, never in `omitted_by` |

## Phase 1 — analysis

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=2 G=1 AC=3`
`CLARIFICATION: 8 raised | 8 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/4 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### BASELINE

The base is 361's tip `c17059cc`. `scripts/gate.sh` printed `GATE GREEN — all 21 checks passed`
on `73ccdc5c`; `c17059cc` adds only the ledger's gate note. Ran at 73ccdc5c.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "were found with Grep" | the PHP writer is a listed writer | ✅ |
| C1 | Scope 2 | rule edges carry `rule: true` at HEURISTIC | | ✅ |
| R1 | Scope 1 | `WRITES`/`DELETES` kind, Table by name, default schema | the template spells `dbo.{key}` | ✅ |
| R2 | Scope 2 | a name matching no table: unlinked, counted | X6 | ✅ |
| AC1 | AC | `find_references dbo.Items` lists the PHP call site | | ✅ |
| AC2 | AC | no column list → not an omitter | X1/X8 | ✅ |
| AC3 | AC | no rule → unchanged | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `\addItem` in the results, `kind WRITES`, HEURISTIC, `rule: True`; `\dropItem` `DELETES`; `\addFromVar` absent | |
| AC2 | yes — `omitted_by == ["dbo.Insert_Item"]`, `unmeasured == ["\addItem"]` | |
| AC3 | yes — only `dbo.Insert_Item`; `rule_keys_unresolved == 0` | |

### Gap analysis (enhancement)

- **Now.** `keyed_calls` emits `CALLS` only; the census looks rule rows up with `calls_by_target_raw`.
- **Target.** A rule declares its edge kind; the census reads every rule kind.

### Blast radius

- `KeyedCall` (361) gains `kind`; `_keyed_calls_edges`, both census helpers; a new store lookup.
- Every rule, writer and reference suite (24 files): `512 passed`.

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the kind is a validated rule-file string, no language branch · §R1.4 (change-type) ✅ the new lookup is in store.py · §R3.1 (change-type) ✅ no new edge kind: WRITES/DELETES exist (v9, v12) · §R5.2 (change-type) ✅ rule edges stay HEURISTIC · §R5.3 (change-type) ✅ an unknown kind or a member template fails loud · §R5.6 (change-type) ✅ a column-less writer stays unmeasured, never an omitter (AC2)`

## Phase 2 — design

### Approach

1. `KeyedCall.kind` (default `CALLS`), validated to `CALLS`/`WRITES`/`DELETES`; a write rule's template names a Table.
2. The emitted edge takes the rule's kind; dedup keys on `(kind, stamp)`.
3. `store.edges_by_target_raw(target_raw, kinds)` for both rule census helpers.
4. TOOLS.md *Configuration reference* and the `find_references` row.

### Rejected alternatives

- **A separate `table_writes` rule kind** — R1.2; `keyed_calls` already reads the key.
- **Extending the resolver's case-insensitive arm to `DELETES`** — a resolver change beyond the ticket; documented instead.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | a global function's call `target_raw` is its qname (`\queryInsert`), so its setter is spelled so | verified — the first run emitted no rule edge with a bare setter |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | rule kind, emission, census | `code_atlas/enrichment.py` | rule builds | R1, R2, C1 | 1/1 |
| 2 | kind-aware raw lookup | `code_atlas/store.py` | new method only | R2 | 1/1 |
| 3 | proving tests | `tests/test_table_name_string_writes.py` (new) | — | AC1–AC3 | 1/1 |
| 4 | docs | `docs/TOOLS.md` | doc budget | R1 | 1/1 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `tests/test_backlog_bookkeeping.py` | — | 4/4 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced: only the new test file was formatted; `ruff check` clean.
- **`widen-every-query-that-shares-the-page`** — traced: `grep -n calls_by_target_raw code_atlas/enrichment.py`
  listed the two census helpers and `_calls_for_setter`; the two census reads moved to the kind-aware
  lookup, the setter read stays on `CALLS` (a setter is a call).

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | real PHP + SQL build, `find_references` | authored | ✅ |
| AC2 | integration | same, `check_column_defaults` | authored | ✅ |
| AC3 | integration | build without rules | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_table_name_string_writes.py`.

### Rollback

`git revert`; a rule file using `kind` then fails loud at load.

## Phase 3 — execute

Commit `e5ac9f39`. **Order deviation:** code before this doc's design text.

**Red first** — the file on 361's tip: 3 failed (no PHP writer listed, no `unmeasured`,
`rule_keys_unresolved == 0`) and the kind check did not raise. With the census restored to the
CALLS-only lookup: `assert 3 == 1`.

On `e5ac9f39` the file gave `7 passed` (superseded by Phase 4's run).

**Sweep.** Axis 1: `git diff --name-only <361 tip>..HEAD` = items 1–4; `ruff check`, `mypy` clean.
Axis 2: Approach 1–4 as approved. Suites: `512 passed`.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `e5ac9f39`, 72,539 tokens): 6 met · 1 not met (partial) · 0 can't tell.**
The partial is Scope 2's `unlinked_writes_count` (X6). Dispositions:

1. **F1: a `DELETES` miss never reaches `unlinked_writes_count`; a case mismatch never links.**
   **Documented:** that count is the writer census (`kind = 'WRITES'`, 278) and `DELETES` is not a
   writer (CONVENTION §3); every miss of either kind is in `rule_keys_unresolved` (TOOLS.md).
2. **F2: kind-blind stamps let one rule's link hide another's miss.** **Fixed** in `a305e2de` — a stamp
   carries its kind, and `_linked_stamps` decides "linked" for both counters (R1.8). Test fails with
   the kind filter removed (`assert 0 == 1`).
3. **F3: a rule hit carries no line.** **Left:** pre-existing for every rule edge (`nav_result.py:308`).
4. **F4: test gaps.** **Fixed:** mixed kinds on one name, a member key, a case-differing `WRITES` key.
5. **F5: a `WRITES` and a `DELETES` rule edge on one line group into one statement row.** **Left:** rare.
6. **F6: a pattern key containing `::` became a column write.** **Fixed:** refused at emit time; tested.
7. **F7: stale docstring.** **Fixed.**

Verify-only (main loop — every fix is inside the approved files):

Ran at a305e2de:
```
$ .venv/bin/python -m pytest -q tests/test_table_name_string_writes.py
10 passed in 2.91s
```
Rule, writer and reference suites on the same tree: `506 passed in 71.06s`.

`Ph3/4 proven by`: G1, C1, R1, R2, AC1–AC3 — 7/7 (R2's single field per X6).

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at a305e2de — the diff `feat/361-js-route-strings-link-to-nothing..a305e2de`. Working doc:
`docs/tasks/364_php-table-name-string-writes-nothing.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `a305e2de` only bookkeeping changes — this doc, `docs/BACKLOG.md`,
`docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`, all exempt.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 1 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

The lesson is a second sighting of `362-C1` (`widen-every-query-that-shares-the-page`): the rule census
was a second read behind the same answer that a new edge kind had to widen, and the challenger found
it. `seen: 362, 364`. Falsify: still true — `grep -n edges_by_target_raw code_atlas/enrichment.py` shows
both counters on the kind-aware read now. **cannot promote: unattended run** — a promotion is a
human-ratified cross-ticket pass (`/mango:promote`), named for the maintainer. Per P1, `343-C2` gains 364.

### Outward actions

1. Push `feat/364-php-table-name-string-writes-nothing` — pre-authorised.
2. Open the PR against `feat/361-js-route-strings-link-to-nothing` — pre-authorised.

Deferred to the maintainer: the merge (after #36); `/mango:promote` on `362-C1`; ratifying X6–X8.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 59,447 |
| 2 | review | `challenger`, round 1 | 72,539 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 131,986 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits; a rule file using `kind` then fails loud at load.
