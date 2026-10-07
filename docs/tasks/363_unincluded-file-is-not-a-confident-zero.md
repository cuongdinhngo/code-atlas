---
id: 363
slug: unincluded-file-is-not-a-confident-zero
title: 'A file nothing includes answers relationship_not_modelled, so "this copy is unused" still needs Grep'
phase: 2
milestone: Coverage
status: done
depends_on: [353]
---

## Why this exists

This comes from the anchor project's field retro, written after 353 landed (2026-10-06).

- F1 (1 PR): `include_graph` named one `tabs.php` line as the only includer of one copy of a
  `screen.php`. On the unused copy, it answered `relationship_not_modelled`, not zero.
- F2 (1 PR): the same answer on a second, regional copy of that `screen.php`.
- F3 (1 PR): `include_graph` on a vendored PDF library's `autoload.inc.php` answered
  `relationship_not_modelled`. Proving "this `vendor/` tree is unreachable" fell back to Grep over
  four roots.

`relationship_not_modelled` fires only when at least one *unlinked* `INCLUDES` row contains the
basename as a substring (`include_graph.py`, `store.count_unlinked_includes_mentioning`). With no
such row the answer is already `no_matches`. So in each case above, some unlinked row matched.

## Scope

1. Reproduce first: on F1–F3, list the unlinked rows that matched and classify them
   (substring false positive such as `old_screen.php`, a concatenation whose literal tail
   rules this path out, or a truly dynamic include). For F3, first confirm that the subject was
   indexed at all, since `vendor/` is excluded by default.
2. Count only the unlinked rows that *could* name the subject: the basename matches at a path
   boundary, and any literal path tail is compatible with the subject's path. If none remain,
   `imported_by` is a positive zero (`no_matches`, `authoritative: true`), and the answer names the
   resolved same-basename alternatives.
3. When a compatible unlinked or dynamic include remains, the answer stays non-`ok` and lists
   those sites as candidates.

## Acceptance criteria

- **AC1:** Two files share a basename, and one is included by a path that resolves to it. The other
  answers a confident zero that names the included file.
- **AC2:** Add one dynamic include of that basename: the answer reverts to non-`ok` and lists it.
  An unlinked include of `old_<basename>` does not revert it.
- **AC3:** Answers for files with at least one includer are unchanged.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 363 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews and merges the PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`, batch 365 → 366 → 361 → 362 → 364 → 363;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `fix/363-unincluded-file-is-not-a-confident-zero` from `main` (`fb256ec5`). Contract `.mango/run-contract-363.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run (run late — see Phase 3).

## Phase 0 — refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 4 want-decision asked | 6 how-decision resolved+cited | 4 ASSUMED | skip: no`

**Premise.** `include_graph` (`include_graph.py:91`), `store.count_unlinked_includes_mentioning`
(`store.py:2552`), `relationship_not_modelled` — all resolve.

**Recall (by handle).** `343-C2` `formatter-rewrites-untouched-lines`.

**Measured on `main` with the PHP adapter.** `include 'views/screen.php'` → `target_raw` `views/screen.php`;
`include $dir . '/screen.php'` → `/screen.php` (HEURISTIC); an interpolated or variable path →
`(dynamic)`. The not-modelled arm fires on any unlinked row *containing* the basename (`instr`),
so `old_screen.php` and `../missing/screen.php` blocked a copy nothing could include.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 50,393 tokens) surfaced X1–X10.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | what "could name the subject" means | want | **ASSUMED:** the last quoted literal (or the raw text) split on `/`, `.`/`..` dropped, must be a path suffix of the subject — `_tail_fits` |
| X2 | a variable-head tail `/screen.php` | want | **ASSUMED:** it fits every `screen.php`, so it keeps the answer non-`ok` (AC2's own case) |
| X3 | where `authoritative: true` appears | want | **ASSUMED:** only on the ticket's case — a positive zero with a same-named file included; a plain `no_matches` is unchanged |
| X4 | a cap on listed sites | want | **ASSUMED:** `page_limit`; a cut listing says `unlinked_includes_truncated` and is never a positive zero (R5.6) |
| X5 | where the predicate lives | how | the SQL in `store.py` (R1.4); the path-tail test in the tool — it is about one subject |
| X6 | naming the alternatives | how | `same_basename_included`: paths a linked `INCLUDES` reaches; not `sibling_definitions`, which names symbol definitions |
| X7 | reason order, AC3 | how | a file with an includer never enters the branch (`include_graph.py:87`); the language arm still runs when no row fits |
| X8 | F3 (a vendored subject) | how | no positive zero for an unindexed path (`store.file_hash`); `vendor/` is excluded by default |
| X9 | `target_raw` as written | how | CONVENTION §3: the literal as written, so quotes and expression heads are read past |
| X10 | SQL vs Python | how | a bounded `instr` fetch, then the tail test in Python |

## Phase 1 — analysis

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=2 G=1 AC=3`
`CLARIFICATION: 10 raised | 10 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/4 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### BASELINE

`main` at `fb256ec5` has the tree of `4e05c246`, on which `scripts/gate.sh` printed
`GATE GREEN — all 21 checks passed`. Ran at 4e05c246.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | title | "this copy is unused still needs Grep" | a confident zero where the include text allows it | ✅ |
| C1 | AC3 | files with an includer unchanged | | ✅ |
| R1 | Scope 1 | reproduce, then count only rows that could name the subject | `_tail_fits` | ✅ |
| R2 | Scope 2/3 | a fitting unlinked/dynamic include keeps non-`ok` and lists the sites | `unlinked_includes` | ✅ |
| AC1 | AC | the unused copy answers a confident zero naming the included one | | ✅ |
| AC2 | AC | a dynamic include of the basename reverts and lists it; `old_<basename>` does not | | ✅ |
| AC3 | AC | files with an includer unchanged | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `no_matches`, `authoritative True`, `same_basename_included == ["app/views/screen.php"]` | |
| AC2 | yes — `relationship_not_modelled`, `unlinked_includes == [{file: app/cron/job.php, line: 2, target_raw: /screen.php}]`; `old_screen.php` in the base fixture does not block AC1 | |
| AC3 | yes — the includer listed, no new field | |

### Gap analysis (bug — logic)

- **Root cause.** `include_graph.py:91` read `count_unlinked_includes_mentioning(basename) > 0`, a substring
  test over every unlinked include in the index: a row naming another directory, or a longer file name
  containing this one, read as possible evidence for this file.

### Blast radius

- `include_graph` only; `count_unlinked_includes_mentioning` lost its one reader and is removed (an orphan this change made).
- Every include / not-modelled test (13 files): `349 passed, 10 skipped`.

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ a path-text test, no language · §R1.4 (change-type) ✅ the SQL is in store.py · §R5.4 (change-type) ✅ the hint stays with no route · §R5.6 (change-type) ✅ no positive zero over a cut listing or an unindexed path · §R6.5 (change-type) ✅ AC1/AC2 red on main`

## Phase 2 — design

### Approach

1. `store.unlinked_includes_mentioning(needle, limit)` (the rows) and `store.included_files_named(basename)`.
2. `include_graph`: keep only rows whose tail fits (`_tail_fits`); list them; with none, a whole listing
   and an indexed subject, a `no_matches` naming included same-named files is `authoritative: true`.
3. TOOLS.md row and the tool docstring.

### Rejected alternatives

- **Resolve each unlinked relative literal against its includer's directory** — that is the resolver's
  job, and a row it could resolve would already be linked; an unlinked one is unlinked because it could not.
- **`authoritative: true` on every empty `imported_by`** — a file nothing mentions may be an entry point; the
  ticket's case is the one with a same-named included copy.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | the PHP adapter's `target_raw` shapes | verified — the measurement above |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | two lookups | `code_atlas/store.py` | new methods only | R1 | 1/1 |
| 2 | tail test, listing, positive zero | `code_atlas/tools/include_graph.py` | include_graph only | R1, R2, AC1–AC3 | 1/1 |
| 3 | proving tests | `tests/test_unincluded_file_zero.py` (new) | — | AC1–AC3 | 1/1 |
| 4 | docs | `docs/TOOLS.md` | doc budget | R2 | 1/1 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `tests/test_backlog_bookkeeping.py` | — | 4/4 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced: only the new test file was formatted; `ruff check` clean.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | real PHP build, `include_graph` | authored | ✅ |
| AC2 | integration | same | authored | ✅ |
| AC3 | integration | same | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_unincluded_file_zero.py`.

### Rollback

`git revert`; answers return to the substring test.

## Phase 3 — execute

Commits `2a1c1a57` (the change, built in a worktree while 364's gate held the checkout) and
`d8795875` (X4/X8 guards from the exposure-checker). **Order deviation:** the code, the exposure-check
and the run contract came after the first commit; t0 still observed every bound condition failing.

**Red first** — the proving file on `main`: `2 failed, 2 passed` (AC1 `relationship_not_modelled ==
no_matches`, AC2 `KeyError: 'unlinked_includes'`); the guards pass on both trees by design.

On `d8795875` the file gave `13 passed` (superseded by Phase 4's run).

**Sweep.** Axis 1: `git diff --name-only main..HEAD` = items 1–4; `ruff check`, `mypy` clean. Axis 2:
Approach 1–3 as approved (plus X4/X8 guards). Include suites: `349 passed, 10 skipped`.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `c1199eef`, 59,414 tokens): 4 met · 0 not met · 3 can't tell/partial.**
It saw four line numbers of this doc through a grep and says it did not open it. Dispositions:

1. **F1: no attested zero without a same-named copy.** **Fixed** in `3b82d9e7` — any indexed file's zero
   with nothing fitting is attested; `same_basename_included` only when non-empty.
2. **F2: a fitting row past the cut was dropped.** **Fixed** — a cut listing keeps
   `relationship_not_modelled` and says `unlinked_includes_truncated`.
3. **F3: interpolated quoted paths.** **Not a defect here:** the adapter stores them as `(dynamic)`
   (measured), so they never reach `_tail_fits`; F4 carries their consequence.
4. **F4 (the important one): `(dynamic)` names no file, so a zero could not rule it out.** **Fixed** —
   `authoritative` is `false` while the index holds any, counted in `dynamic_includes_unchecked` (R5.6);
   the test fails with the count forced to 0 (`assert True is False`).
5. **F5: case-sensitive tail.** **Left:** the resolver links includes case-sensitively too (same rule).
6. F6/F7 checked fine. **F8: docs.** **Fixed** with the docstring.

Verify-only (main loop — every fix is inside the approved files):

Ran at 3b82d9e7:
```
$ .venv/bin/python -m pytest -q tests/test_unincluded_file_zero.py
16 passed in 3.26s
```
Every include / not-modelled test on the same tree: `371 passed in 46.98s`.

`Ph3/4 proven by`: G1, C1, R1, R2, AC1–AC3 — 7/7.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 3b82d9e7 — the diff `main..3b82d9e7`. Working doc: `docs/tasks/363_unincluded-file-is-not-a-confident-zero.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `3b82d9e7` only bookkeeping changes — this doc, `docs/BACKLOG.md`,
`docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`, all exempt.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

`363-C1` is type 2 (code), handle `a-zero-must-count-what-the-search-cannot-see`: a confident zero built
from a text search over stored rows must also count the rows the search could never match (here
`(dynamic)`, which names nothing). First sighting. Per P1, `343-C2` gains 363.

### Outward actions

1. Push `fix/363-unincluded-file-is-not-a-confident-zero` — pre-authorised.
2. Open the PR against `main` — pre-authorised.

Deferred to the maintainer: the merge; ratifying X1–X4.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 50,393 |
| 2 | review | `challenger`, round 1 | 59,414 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 109,807 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits.
