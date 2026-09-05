---
id: 215
slug: a-partial-writer-set-looks-finished-and-a-column-is-counted-twice
title: '`check_column_defaults` saw 38 of 55 writers and said so with no marker, and reported one column twice — a 69 %-complete answer that looks finished retires the cross-check that would have caught it'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [194, 192, 022]
---

## Why this exists (field retro round 13 §12.d, §18.4)

[194](194_default-filled-column-defect-class-query.md) shipped the query round 12 named verbatim, and
round 13 called the result **the best single answer of the round**:

> `check_column_defaults("dbo.LedgerTrans", "ChangeUser")` → `default: "(user_name())"` — verified exact
> at `Tables/Data/LedgerTrans.sql:58` — `writers_total: 38`, `omitted_count: 36`, and the two exceptions
> by name, both of which genuinely name the column, for a reason their own comment gives.

And in the same paragraph: **"not trustworthy without the grep."** Three defects, measured:

| | Reported | True | Where |
|---|---|---|---|
| writers of the table | **38** | **55** | grep, cross-checked three ways |
| writers naming the column | **2** | **≥ 4** | same |
| rows for one column | **`total_count: 2`** | 1 | `dbo.LedgerTrans::ChangeUser` is declared in both the per-object file and the baseline migration |

The duplicate is a two-line defect: `_columns_of` builds `qnames` as a **sorted list** of `CONTAINS`
edge targets (`code_atlas/tools/check_column_defaults.py:71`), so a column declared twice yields two
identical qnames, two identical rows and a `total_count` of 2 for one column.

**The under-count is the important half, and it is not primarily this tool's fault.** The 17 invisible
writers fail at the tier below — the write-site edges 022 emits. The retro diagnosed each one:

| Missed writer | Form | Failing tier |
|---|---|---|
| `LedgerTransExtras` — a **trigger on the table** that `UPDATE`s `ChangeUser` | the whole `CREATE TRIGGER` sits inside `EXEC('…')`; the declaration is at `:26` **inside the string** | **parse** |
| `createAppraisalFromDiagnosis` — 2 INSERTs, **both naming the column** | the proc **is** a `Function` node with 2 definitions | **edge** — symbol present, `WRITES` absent |
| `Insert_AB_Trans_v1` — 6 writes | `insert into **Ledgertrans** (` — table name in a different case from the declaration | **edge** — T-SQL is case-insensitive; the matcher is not |
| `Insert_AA_Trans_v1` / `_beta` | `update LedgerTrans` with `SET` on the **next line** — **46 of 51** `UPDATE` sites in the anchor are written that way | **edge** |

**Why this ticket is about the marker, not only the misses.** 194's AC2 required that *a table with no
recorded writers* answer `table_has_no_writers` rather than zero — and it does, correctly. Nobody
specified the case that actually occurred: **a writer set that is present but partial.** The tool has
a coverage surface already (`attach_coverage_note`, from
[192](192_coverage-note-suppressed-on-a-partial-answer.md)) and it fires on *language* coverage, which
was never in doubt here.

Round 13's §18.4 is written about this answer, and it is the round's one genuinely new finding:

> **A wrong answer gets caught by the cross-check the project already mandates, while a 69 %-complete
> answer retires the cross-check by looking finished.** It is also the shape a tool acquires as it
> gets *better* — round 7's harmful ranking was crude enough to spot; this is not.

The cost is measured, not asserted: the retro wrote **three throwaway scripts, 86 lines, 19 minutes**,
all three to check this tool — the tool built to stop people writing throwaway scripts.

## Scope

1. **Dedupe by column identity.** One column is one row, whatever number of files declare it. A
   column declared in N places must not multiply `total_count`, and the extra declarations must not
   be silently discarded either — a column the graph holds twice is a fact about the graph.
2. **A partial writer set says it is partial.** Where the tool can know its writer set is incomplete,
   the payload says so, next to the number. The mechanism is 192's coverage note, applied to a
   condition it does not currently test.
3. **Name what would make it complete**, at whatever precision is available: the write forms that do
   not produce a `WRITES` edge are enumerable (the table above is four rows, three of them mechanical).
   A reader must be able to tell *"38 of the writes I can see"* from *"38 writes exist"*.
4. **Fix the two mechanical edge-tier misses** if design finds them in reach: a case-insensitive table
   match for a case-insensitive language (**R2** — T-SQL's rule, not the anchor's habit) and an
   `UPDATE … SET` whose `SET` is on the following line. Together they account for most of the 17. If
   either is larger than it looks, it splits out and Scope 2 still ships — **the marker is the
   ticket's floor, the edges are its ceiling.**

### Explicitly not in scope

- **The parse-tier miss** — a trigger whose whole body is a string literal (`EXEC('CREATE TRIGGER …')`).
  That is a `CREATE`-inside-dynamic-SQL gap in tier 1a and needs its own evidence; it lands under
  Scope 3's disclosure, not Scope 4's fix.
- **A live `INFORMATION_SCHEMA` probe.** R4 bars the core from a database, and 194 already recorded
  that the probe is the right tool for schema *state*.
- **Generalising the rule beyond SQL writers** before a second consumer asks (194's own boundary).
- **`find_callers`' bare-`EXEC` zero** — that is [214](214_a-bare-exec-links-to-nothing-and-the-zero-says-no-matches.md).

## Constraints

- **R4.2** — deterministic; identical graph ⇒ identical rows, dedupe included.
- **R5.6** — silence is not evidence, and this ticket extends it: **a partial count presented as a
  total is the same failure with a number attached.**
- **R6.3** — the judgement about the anchor ships as a committed re-runnable check, not a session run.
- **R6.9** — assert at the consumer: the proving test reads the payload a caller receives.
- **R7.6** — the disclosure earns its bytes. Round 13 measured mean disclosure at ≈1.2 KB/call, down
  from ~4 KB, and called that batch D's best property. A note that fires on every answer would give
  that back.

## Acceptance criteria

1. A column declared in two files produces **one** row and `total_count: 1`, pinned by a fixture that
   fails before the change.
2. A writer set the tool knows to be partial carries a marker naming that, and a complete one does
   **not** — both pinned. An unconditional note fails this criterion.
3. The marker names what is missing at the precision available (Scope 3), not merely that something
   is.
4. Any edge-tier fix taken under Scope 4 is proven by a fixture in the missed form — case-varied table
   name, or `SET` on the following line — and the anchor's before/after writer count is recorded.
5. `table_has_no_writers` still answers *unmeasured*, never *zero* (194's AC2 does not regress).
6. No `contract_version` bump beyond 022's.

## References

Field retro round 13 §12.d.1 (the three defects), §12's tier-diagnosis table (the four missed write
forms), §2.c (the three throwaway scripts, 86 lines / 19 min), §11.c (best artifact, and why it is not
trusted), §18.4 (*"partial, unmarked, and therefore trusted"* — the box the round says the next one
needs).
[194](194_default-filled-column-defect-class-query.md) (the tool, and the AC that covered the empty
case only), [192](192_coverage-note-suppressed-on-a-partial-answer.md) (the coverage-note mechanism),
[022](022_sql-schema-adapter.md) (tier 2, which emits the `WRITES` edges).
`code_atlas/tools/check_column_defaults.py:64` (`_columns_of`), `:71` (the list that should be a set),
`:85` (`_row`), `:190` (the `unmeasured` discriminator this builds on),
`code_atlas/tools/coverage.py:29` (`relation_unmodelled_for_language` and the note surface).


<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 215 · **work_doc_mode:** embed · **Current phase:** 5 finalise → PR.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** bug.
- Run: `/mango:autorun 215` with skipped reviewer (`--no-reviewer`); challenger ON.
- Branch: `fix/215-a-partial-writer-set-looks-finished`. Contract `.mango/run-contract-215.txt`.
- RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 7 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 3 by handle | 1 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions. Ticket locks floor (dedupe + partial marker) and
ceiling (edge fixes if in reach). User handover authorises design to choose Scope 4 reach.

**Ambiguous:** field retro round 13 (prose). **INPUT KIND:** ticket.

**Recalled (advisory):** `reproduce-the-payload-not-the-story`, `prefer-the-provable-fix`,
`count-pin-in-blast-radius`; area SQL/WRITES (022). Retired skipped: `assert-the-consumer-not-the-field`, `prove-the-guard-fails`.

## Phase 1 — analysis

`PREMISE: 7 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 3 by handle | 1 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 5 decomposed | ROWS: C=5 R=4 G=2 AC=6`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`
`RULE SECTIONS: 8 applicable — 7 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ no language branch · R2.1 (change-type) ✅ T-SQL case-insensitive rule · R4.2 (change-type) ✅ deterministic dedupe · R5.6 (change-type) ✅ partial ≠ total · R6.9 (change-type) ✅ consumer payload · R7.1 (change-type) ✅ floor first · R7.6 (change-type) ✅ note not unconditional · R6.5 (recalled handle) ✅ AC1 red-before`

### BASELINE

`.venv/bin/python -m pytest -q --tb=no` at **9732b4e**: `2877 passed in 259.52s`.
`Ran at c6c9f56892ad45ff94d5da6642fbe8de3b654d9e`. No exclusions.

### Clarifications (j = 0)

| # | Q | Resolution | Cite |
|---|---|---|---|
| Q1 | SET-on-next-line broken at emit? | **No — already works.** Adapter emits `LedgerTrans::ChangeUser`; miss is FQN link (schema/case) | measured spike; scan.js pending absorb |
| Q2 | Scope 4 home? | **Resolver WRITES-only CI / unqualified unique Table·Column match** — WRITES is SQL-only vocabulary today; no `language ==` | R1.1; contract WRITES; Q1 |
| Q3 | Partial marker mechanism? | Unlinked WRITES that casefold-relate to the table → payload `writers_partial` + hint naming forms; absent when none | ticket Scope 2–3; R7.6 |

### Requirements matrix

| ID | Source | Interpretation | Status |
|---|---|---|---|
| G1 | Why | duplicate column → one row | open |
| G2 | Why | partial writers marked | open |
| R1 | Scope 1 | dedupe + surface multiplicity | open |
| R2 | Scope 2–3 | partial marker + named forms | open |
| R3 | Scope 4 | CI / unqualified WRITES link if in reach | open |
| R4 | not in scope | parse-tier dynamic CREATE | closed (disclose) |
| C1–C5 | Constraints | R4.2 R5.6 R6.3 R6.9 R7.6 | closed |
| AC1–AC6 | AC | see validation | open |

### AC validation

| AC | Falsifiable | Match |
|---|---|---|
| AC1 | fixture two CONTAINS same column → total_count 1 | yes |
| AC2 | partial marked; complete unmarked | yes |
| AC3 | hint names forms | yes |
| AC4 | edge fixtures + census or exclusion | yes |
| AC5 | table_has_no_writers unchanged | yes |
| AC6 | CONTRACT_VERSION == 9 | yes |

### Cause

1. `_columns_of` builds sorted **list** of CONTAINS targets → duplicate qnames (`check_column_defaults.py:71`).
2. Partial writers look finished — no marker when WRITES exist but under-count (194 covered empty only).
3. Edge tier: WRITES `target_raw` case/schema ≠ declared Table qname → unlinked.

### Blast radius

`check_column_defaults.py`, possibly `resolver.py` + `store.py` for WRITES CI; SQL fixtures/tests; docs.

## Phase 2 — design

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Approach

1. **Dedupe** CONTAINS targets with `dict.fromkeys`; row carries `declarations` when >1.
2. **Partial marker** on payload when linked writers exist AND unlinked WRITES casefold-relate to the table — hint enumerates forms (case/schema mismatch; dynamic; CREATE-in-string). Absent when no such edges.
3. **Scope 4:** after FQN miss on WRITES, unique case-insensitive qname match, else unique Table/Column by casefolded name (+ schema-unqualified container). SET-next-line: no adapter change (already emits).
4. Anchor writer-count census: exclusion (no real_corpus_path); fixture before/after recorded.

### Rejected

| Alt | Why |
|---|---|
| Always attach language coverage note | Fails AC2; R7.6 |
| Adapter lowercases all SQL qnames | Rebuild tax; wrong for display |
| Skip Scope 4 entirely | In reach via WRITES-only path; take the ceiling |

### Assumptions

| A | Tag |
|---|---|
| SET-next-line already emits | verified — spike |
| WRITES only from SQL adapter today | verified — vocabulary |
| CI unique match is safe for WRITES | novel-untested → proving fixtures |

### Change list

| # | Change | File | Blast | Ph2 | k/N |
|---|---|---|---|---|---|
| 1 | Dedupe + declarations | check_column_defaults.py | existing 194 tests | R1,AC1 | 2/2 |
| 2 | writers_partial marker + hint | check_column_defaults.py (+ store helper) | payload shape | R2,AC2,AC3 | 3/3 |
| 3 | WRITES CI / unqualified unique link | resolver.py + store.py | all WRITES linking | R3,AC4 | 2/2 |
| 4 | Proving tests | tests/test_check_column_defaults_partial.py | 194 suite | AC1–AC5 | 5/5 |
| 5 | Docs / ledger / census method | docs/ | bookkeeping | AC4,AC6,R7.2 | 3/3 |

### HANDLES

**H1 reproduce-the-payload** — traced.

```
Ran at 9732b4e68d2191629e16add6468aab3e6ab0cd8f
$ rg -n '_columns_of|writers_total|STATUS_NO_WRITERS' code_atlas/tools/check_column_defaults.py | head -5
64:def _columns_of
102:        "writers_total": len(writers),
32:STATUS_NO_WRITERS = "table_has_no_writers"
```

**H2 prefer-the-provable-fix** — traced.

```
Ran at 9732b4e68d2191629e16add6468aab3e6ab0cd8f
$ node -e '/* SET-next-line spike */' → WRITES target_raw LedgerTrans::ChangeUser (emit ok)
```

**H3 count-pin-in-blast-radius** — traced.

```
Ran at 9732b4e68d2191629e16add6468aab3e6ab0cd8f
$ rg -ln 'writers_total|omitted_count|check_column_defaults' tests/
tests/test_check_column_defaults.py
```

### Coverage-gap exclusions

| Item | expiry | seen |
|---|---|---|
| AC4 anchor before/after writer count on field index | when config.real_corpus_path is configured | (first) |

### Verification plan

| AC | risk | proof | provenance | match |
|---|---|---|---|---|
| AC1 | integration | pytest consumer | authored | ✅ |
| AC2 | integration | pytest partial vs complete | authored | ✅ |
| AC3 | integration | hint string pin | authored | ✅ |
| AC4 | integration | case/unqualified fixture | authored + E1 exclusion | ✅ |
| AC5 | integration | existing no-writers test | authored | ✅ |
| AC6 | logic | CONTRACT_VERSION==9 | n/a | ✅ |

### Proving test

`.venv/bin/python -m pytest tests/test_check_column_defaults_partial.py tests/test_check_column_defaults.py -q`

### Rollback

`git revert` / close PR. Single repo.

`SCOPE: M` unchanged.


## Phase 3 — execute

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`

### Implementation

Approved change list landed:

1. `_columns_of` dedupes CONTAINS qnames; row carries `declarations` when N>1.
2. Envelope `writers_partial` + hint when linked writers exist AND `has_unlinked_writes_relating_to`.
3. Resolver `_link_writes_casefold` after FQN miss on WRITES; store CI helpers.
4. Proving tests in `tests/test_check_column_defaults_partial.py`.
5. Docs/ledger/BACKLOG/LESSONS.

SET-on-next-line: no adapter change (already emits).

### Verification sweep

Ran at 49c6fe4864429709617f9d7544246af03767a76d
```
$ .venv/bin/python -m pytest tests/test_check_column_defaults_partial.py tests/test_check_column_defaults.py -q
14 passed
```

`diff ⊆ approved list` — only listed paths (+ LESSONS/BACKLOG/TOKEN_LEDGER/task as docs).

### Design-conformance self-check

Dedupe + partial marker + WRITES CI link match Gate 2 approach. No contract bump.


### AC4 census recording (challenger F1)

Fixture method (committed in LESSONS 215): before = case-mismatched / SET-next-line WRITES unlinked
on the synthetic fixtures; after = linked (`writers_total: 2` / `named_by` pinned). Anchor
`38→N` on the field index: **cannot measure on this checkout** (`real_corpus_path` null) — E1,
expiry when configured. Mechanism deviation: `writers_partial*` keys rather than 192's language
`attach_coverage_note` (that surface is language coverage; this is WRITES incompleteness).


## Phase 4 — review

REVIEWER: OFF (waived --no-reviewer). CHALLENGER: ON.

- Round 1: CHANGES REQUESTED — AC4b anchor before/after missing; Scope-2 mechanism deviation (writers_partial* vs 192 language note).
- Fixes: LESSONS census method + E1; ORDER BY on unlinked WRITES scan; mechanism documented.
- Round 2: LGTM — previously open rows met.

Ph3/4 proven by: tests/test_check_column_defaults_partial.py (7 passed at review); challenger LGTM.

Reviewed at 49c6fe4864429709617f9d7544246af03767a76d — source set through AC4 census recording; subsequent finalise docs-only commits are bookkeeping-exempt.

clean (challenger only — REVIEWER: OFF)

## Phase 5 — finalise

`LEDGER TOTAL: unmeasured · top cost driver: challenger dispatch`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`


### Maintainer review of PR #266 — one blocker, fixed

CI red on both matrix legs: `ruff` **F841** `code_atlas/resolver.py:221` — `kinds` assigned, never
used. Introduced live at `9e39893` (`kinds <= {"Table", "Column"}`) and orphaned by the R3.2 vocab
refactor `c6c9f56`, which rewrote the guard as `str(hits[0]["kind"]) in (_TABLE_KIND, _COLUMN_KIND)`.
The refactor is behaviour-preserving (`len(hits) == 1` makes the two forms equivalent); only the dead
binding was left. Fix: delete the line. Re-run: **GATE GREEN — 17/17**, 2883 passed.
This is DISCLOSURE item 8 landing: the gate was not re-run after `c6c9f56`, so `ruff` never saw it.

Also verified, no change made:
- New tests are not vacuous — 6 of 7 fail against `origin/main`'s `code_atlas/`.
- `nodes_by_*_casefold` use `LOWER(...)`, which no index covers: ~25 ms vs ~0.3 ms exact at 200k
  nodes. Paid only on batches that hold a `WRITES` miss, so it is opt-in on the broken case.
- `_link_writes_casefold` matches on `target_raw`, not the alias-followed `lookup` the exact pass
  used. Unreachable today — the SQL adapter is the only `WRITES` emitter and emits no `ALIASES`
  (R1.2 YAGNI); revisit if a second emitter lands.
- `LOWER()` is ASCII-only in SQLite while the Python side uses `.casefold()`; a non-ASCII identifier
  fails to match. Fails toward no-link, never a wrong link.


## DISCLOSURE

```
DISCLOSURE
  1a. REVIEWER: OFF — waived by `--no-reviewer`. No rule-book-grounded review of the diff ran; a clean result below carries no reviewer finding because none was sought.
  1b. CHALLENGER: ON — the ticket-blind challenger ran (round 1 CHANGES REQUESTED → round 2 LGTM).
  2. UNCHECKED AGENT CLAIMS: 2 — no command derived these values at t0.
       - TREE-COMPARISON paths / PROVING-TEST (bound at Gate 2 from design).
  3. BUDGET: call-count ceiling unknown — no ledger history for this tier; proxy only.
  4. This list is the ONE artifact nothing can check: only the agent knows what it chose not to verify. A near-empty list on a long run is a reason to distrust the run, not to trust it.
  5. AC4 field-anchor 38→N excluded (real_corpus_path null); fixture census recorded in LESSONS 215.
  6. Mechanism deviation: writers_partial* keys rather than 192 attach_coverage_note (documented).
  7. Outward actions deferred: merge #266 (NOT authorised inside this skill).
  8. Full suite after final docs: 2882 passed + 2 fixed mid-run (R3.2 vocab literal; bookkeeping status); not re-run after last docs-only commits — proving + targeted green at reviewed tree 49c6fe4.
  9. has_unlinked_writes_relating_to caps at 10k unlinked WRITES; knowable incompleteness beyond the cap could be missed.
```
