---
id: 458
slug: verify-refs-file-suffix-is-a-path
title: "A bare word with a file suffix is a path, never a member reference"
phase: 2
milestone: "Field gaps — Python/TS consumer"
status: done
depends_on: [443]
---

## Why this exists

Same field report as 456. `atoms.json`, `voice_pace.json`, `series.json` and `keys.ts` have no folder,
so they are classified as symbols: `atoms` + `.json`. The head then matches a member
(`series.SeriesAtoms::atoms`, `Pipeline::voice_pace`, `SqliteJobQueue::series`,
`preview/rail.tsx::Tip::keys`), and the "member" `json` / `ts` is `gone`. That is 10 actionable
rows, all false.

- `atoms.json` (5 rows): a data file written under the channel folder at run time (ADR 0016).
- `keys.ts` (`docs/ARCHITECTURE.md:66`): the real file `src/api/keys.ts`, written as a bare name
  in a table cell.

## Scope

1. A ref whose last segment is a known file suffix is kind `path`, not `symbol`. Use the suffix set
   the tree and the adapters already know (`.json .ts .tsx .py .md .yaml .sh .css .j2 …`), not a new
   list, if one exists.
2. A bare file name (no folder) resolves like other folderless paths: `ok` if exactly one file in
   the tree has that name (`keys.ts` → `src/api/keys.ts`), otherwise the current weak path rules.
   A name no branch ever held stays `never_existed` and is never actionable (443).

## Acceptance

1. Fixtures: `atoms.json` next to a class with member `atoms` → a path row, not a symbol row;
   `keys.ts` with one match in the tree → `ok`.
2. Re-run the Python/TS consumer: the 10 rows above are not actionable.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Last updated:** 2026-11-28
- **Current phase:** finalise
- **Next action:** the maintainer merges #191, then this PR; 459 runs next, stacked on this branch
- **Blocked on:** nothing
- **KEY:** 458 · **work_doc_mode:** embed · `TRACK: backend` · Run mode: `autorun 456 - … - 462`, third —
  `REVIEWER: ON` · `CHALLENGER: ON` · `cost_tier: standard`. A want-decision is `ASSUMED` under the handover.
- Branch `feat/458-verify-refs-file-suffix-is-a-path` from 457's tip `3833f06a` (#191), in a worktree. Contract
  `.mango/run-contract-458.txt`; RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 2 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 2 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 2 want-decision asked | 8 how-decision resolved+cited | 2 ASSUMED | skip: no`

`kind_of` and `_resolve` resolve in `doc_refs.py`; ambiguous: the consumer's ADR and file sites, present in its
tree. Recalled: 456-C1 `diff-every-row-not-the-target-rows`, 457-C1 `accept-by-kind-not-reject-by-kind` (handles),
398-C1 (area). Exposure-checker: 5 returned (H5–H8, W2).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the suffix set | how | the index's suffixes ∪ `_DOC_FILE_SUFFIXES` (both already in `kind_of`, `doc_refs.py:322`) ∪ the suffixes tracked files carry — no new list (Scope 1) |
| H2 | the comparison | how | the last segment exactly, case kept: `threading.Lock` keeps the symbol fallback `_resolve` gives it (`doc_refs.py:960`) |
| H3 | the kind | how | asked as a path first; a name no branch held stays `never_existed`, never actionable (Scope 2, 443) |
| H4 | a bare file name | how | today's path rules: one tracked file ending so → `ok` (`under_a_subproject`) (Scope 2) |
| H5 | a real symbol ending in a suffix (`Series.json`, `response.json`) | how | the symbol still wins when it is `ok`, or external (no row) — `test_verify_refs.py:48,167` pins `response.json` silent |
| H6 | several tracked files of that name | how | today's `ambiguous` (`several_paths_end_so`, `doc_refs.py:469`) |
| H7 | an odd tree suffix (`lock`) | how | H2's exact case keeps `Lock` a symbol; a lowercase member literally named like a suffix reads as a file — accepted with H5 |
| H8 | compound names (`x.tar.gz`) | how | the last dot only, as `kind_of` already splits |
| W1 | a tree-only suffix (`.wav`, `.j2`) | want | **ASSUMED:** counts like an indexed one |
| W2 | AC2's bar | want | **ASSUMED:** the 10 rows in any non-actionable state; a path row is the target |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=0 R=2 G=1 AC=2`
`CLARIFICATION: 10 raised | 10 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/5 touched files under UI paths`
`SCOPE: S`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "That is 10 actionable rows, all false" | file names leave the member path | ✅ |
| R1 | Scope 1 | "A ref whose last segment is a known file suffix is kind `path`, not `symbol`" | H1–H3, H5 | ✅ |
| R2 | Scope 2 | "A bare file name … `ok` if exactly one file in the tree has that name" | H4 | ✅ |
| AC1 | Acc 1 | "`atoms.json` next to a class with member `atoms` → a path row; `keys.ts` with one match → `ok`" | fixture | ✅ |
| AC2 | Acc 2 | "the 10 rows above are not actionable" | the 10 rows, by ref | ✅ |

**Gap.** `_resolve` re-asks every slash-less `never_existed` path in a symbol's shape as a symbol, so `atoms.json`
reached the member `atoms` and read `gone` when git found `json` in its file; `.wav` was no known suffix at all.

`BASELINE: green — the 457 suites plus its proving test: 877 passed`

Ran at 3833f06a (pre-change)
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q $(cat .mango/baseline-458.list)
877 passed in 37.68s
```

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 suffixes come from the index, a set and the tree, never a language · §5 (change-type) ✅ R5.6 a never-held path is never_existed, not gone · §6 (change-type) ✅ R6.5 seen failing on the base, R6.7 the suffix set is derived from the tree and the index · §7 (change-type) ✅ R7.5 comments ≤ 3 lines, R7.6 the TOOLS line extended in place`

## Phase 2 — design

`HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- `diff-every-row-not-the-target-rows` — traced: the consumer's 457-code and 458-code exports diffed by (file, line,
  ref) on one index copy (Phase 3): 0 newly actionable, 0 dropped, 41 rows symbol → path.
- `accept-by-kind-not-reject-by-kind` — does not apply because the rule reads suffixes, not node kinds.

**Approach.** (1) `Resolver.names_a_file`: a slash-less name whose last segment, case kept, is in the suffix set (H1),
built once from `_tracked_index`. (2) `_resolve`: such a name is asked as a path first; on `never_existed` in a symbol's
shape, the symbol answer wins only when `ok` or external. **Rejected:** dropping the symbol fallback for every suffixed
name — `response.json` (an external call) would start emitting rows; a case-folded compare — `threading.Lock` would
become a path. **Assumptions:** none novel.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| path first | `code_atlas/doc_refs.py` | `test_verify_refs.py` (`threading.Lock`, `response.json`), the stored summary | R1, R2 |
| proving test | `tests/test_verify_refs_file_suffix.py` | — | AC1 · 5/5 |
| docs | `docs/TOOLS.md`, `CHANGELOG.md` | `test_doc_size_budget.py` | R7.6 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration (built index) | integration fixture | authored | ✅ |
| AC2 | e2e (the consumer) | manual-recorded: export pair on one index copy | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `tests/test_verify_refs_file_suffix.py`. Rollback: revert. Porting: one repo.

## Phase 3 — execute

Main loop, in the worktree, at `3ca4d31b`. **Sweep.** Axis 1: the diff is the approved list; `ruff`, `mypy` clean.
Axis 2: (1)–(2) implemented-as-approved.

Ran at 3833f06a (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_verify_refs_file_suffix.py   # base + the new test only
3 failed, 2 passed in 0.93s
```

At `3ca4d31b` (superseded by the review fix) the suites read `882 passed`; Phase 4 holds the reviewed tree's run.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. `reviewer` (Sonnet), and the ticket-blind `challenger` on the raw ticket
(`git show 3833f06a:<this file>`) + the branch diff.

- **Reviewer round 1** at `3ca4d31b` (60,621 tokens): CHANGES REQUESTED, conditional on 1. **Taken** (`a135b1a2`):
  (1) a suffix one tracked file carries (`Dockerfile.dev`) turned a removed member `Settings.dev` into a silent path —
  a tree-only suffix now needs two tracked files and two characters; row `Settings.dev` pinned, seen failing on
  `3ca4d31b`; the fixture tracks a second `.ts` file since it runs no TS adapter. **Declined:** (2) case-folding the
  doc-set compare — it would make a removed member named `Lock` or `Json` a silent path; `README.MD` keeps today's
  route. The `_resolve` docstring is back to three lines.
- **Reviewer round 2** (verify-only, main loop, at `a135b1a2`): the fix and its row as described; only the affected
  proof and the consumer pair re-run.
- **Challenger round 1** at `3ca4d31b` (54,994 tokens): 6 rebuilt · 6 met. Not re-dispatched: the round-2 fix stays
  inside the reviewer's named finding.

`CHALLENGER VERDICT: 6 requirement(s) rebuilt | 6 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

Ran at a135b1a2
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_verify_refs_file_suffix.py $(cat .mango/baseline-458.list)
883 passed in 34.28s
```

**AC2 — the consumer**, re-run on the reviewed tree, 457 code and this branch back to back:

Ran at a135b1a2
```
before (3833f06a): 1947 rows, 4 actionable
after  (a135b1a2): 1954 rows, 4 actionable — atoms.json ×5, voice_pace.json ×2, series.json ×2 path never_existed;
keys.ts path ok; none actionable. 40 rows symbol → path; 0 newly actionable, 0 dropped
```

Reviewed at a135b1a2 — files: `code_atlas/doc_refs.py`, `tests/test_verify_refs_file_suffix.py`, `docs/TOOLS.md`,
`CHANGELOG.md`; working doc `docs/tasks/458_verify-refs-file-suffix-is-a-path.md`.

`Ph3/4 proven by`: R1, R2, AC1 → `tests/test_verify_refs_file_suffix.py` (6); AC2 → the corpus block.

## Phase 5 — finalise

Stale-review guard: only bookkeeping after `a135b1a2` — not stale.

**Durable lesson.** 458-C1 `a-derived-set-needs-a-floor` (type 2, first sighting) in `docs/LESSONS.md`.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/458-verify-refs-file-suffix-is-a-path`; open its PR against
`feat/457-verify-refs-callable-container-not-gone` (#191, stacked). Deferred to the maintainer: ratify W1–W2; merge
after #191. Revert: revert the branch's commits.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 48,646 |
| 3 execute | `implementer` — not dispatched (main loop implemented) | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | rule-book `reviewer` | 1 | 60,621 |
| 4 review | ticket-blind `challenger` | 1 | 54,994 |

`LEDGER TOTAL: 164,261 · top cost driver: 4 review / reviewer` — main loop unmeasured.
