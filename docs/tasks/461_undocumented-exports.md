---
id: 461
slug: undocumented-exports
title: "The other direction: exports of chosen paths that no doc names"
phase: 2
milestone: "Field gaps — Python/TS consumer"
status: done
depends_on: [443]
---

## Why this exists

Same field report as 456. `verify_refs` answers "is what the docs say still true" (docs → code). Drift
also goes the other way: a shared helper is added and the catalogue that tells agents to reuse it is
never updated. The next session doesn't find it and writes a second copy. The Python/TS consumer found 14
copies of the same error ternary, 3 of the native-dialog logic and 6 of the LLM retry loop (its decision record
audit, 2026-11-27).

The index already holds both sides (exported symbols, and the refs `verify_refs` extracts). The
missing piece is the set difference.

## Scope

1. A query over a path glob and a doc glob: public top-level symbols under the paths that no ref
   in the docs resolves to. Rows: `symbol`, `file:line`, `kind`. "Public" comes from what the
   adapter emits (`modifiers`), never from a core rule about `export` or a leading `_` (R1.1). An
   adapter that emits no visibility counts as all public, and says so in coverage.
2. Surface it as a `compute` template, or as `verify_refs` mode `undocumented`, whichever 443's export
   code already fits. One surface only. CLI too: `code-atlas query --undocumented <paths> --docs
   <globs> --format jsonl|md`, with `--fail-on any`.
3. An allowlist file (one qname per line) for internal helpers.

## Acceptance

1. Fixture: two exports, one named in a doc → one row; an allowlisted export → no row.
2. The Python/TS consumer: run on `src/components/ui/**`, `src/lib/**` against
   `docs/CONVENTIONS_FE.md`. Report the rows and check them by hand against the catalogue.
3. Runtime on the anchor for one path glob, reported.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Last updated:** 2026-11-28
- **Current phase:** finalise
- **Next action:** the maintainer merges #194, then this PR; 462 runs next, stacked on this branch
- **Blocked on:** nothing
- **KEY:** 461 · **work_doc_mode:** embed · `TRACK: backend` · Run mode: `autorun 456 - … - 462`, sixth —
  `REVIEWER: ON` · `CHALLENGER: ON` · `cost_tier: standard`. A want-decision is `ASSUMED` under the handover.
- Branch `feat/461-undocumented-exports` from 460's tip `fa6ca529`, in a worktree. Contract
  `.mango/run-contract-461.txt`; RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 3 want-decision asked | 9 how-decision resolved+cited | 3 ASSUMED | skip: no`

`modifiers` (`NODE_FIELDS`), `verify_refs`, `compute` and `query --fail-on` resolve; `--undocumented` and the allowlist
are to be created. Ambiguous: the consumer's paths (`src/…` in the ticket is `web/src/…` there). Recalled: 456-C1
`diff-every-row-not-the-target-rows` (handle), 398-C1 (area). Exposure-checker: 7 returned (H6–H9, W1–W3).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the surface | how | `verify_refs`' `undocumented` parameter; a `compute` template runs one SQL body and cannot read docs (`compute.py:73`) — Scope 2 "whichever 443's export code already fits" |
| H2 | the candidates | how | nodes of `TYPE_KINDS` ∪ `CALLABLE_KINDS` ∪ `VALUE_KINDS` under the globs, whose container is no such node (top-level), not `is_test` |
| H3 | public | how | not `private` / `protected` in `modifiers`; a language whose candidates carry no visibility word is named in `coverage.visibility_not_emitted` (Scope 1) |
| H4 | the CLI | how | `query --undocumented GLOB… --docs GLOB… --format json\|md\|jsonl --fail-on any` (Scope 2) |
| H5 | the allowlist | how | `refs_undocumented_allow`, one repo file, a qname per line (Scope 3) |
| H6 | a re-export | how | no node, so no candidate |
| H7 | an unreadable allowlist | how | a config error, never an empty list (R5.3) |
| H8 | order and paging | how | file, line, qname; `total_count` full, the page capped (R5.8) |
| H9 | an empty answer | how | `no_symbol_under_paths` / `every_export_documented`, never an error |
| W1 | a file named in a doc | want | **ASSUMED:** documents its top-level symbols — the consumer's catalogue names files |
| W2 | an ambiguous mention | want | **ASSUMED:** documents each of its candidates |
| W3 | AC2 and AC3's bars | want | **ASSUMED:** reported and hand-checked, no threshold |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=0 R=3 G=1 AC=3`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "The missing piece is the set difference" | exports less what docs name | ✅ |
| R1 | Scope 1 | "public top-level symbols under the paths that no ref in the docs resolves to" | H2, H3, W1, W2 | ✅ |
| R2 | Scope 2 | "One surface only. CLI too … `--fail-on any`" | H1, H4 | ✅ |
| R3 | Scope 3 | "An allowlist file (one qname per line)" | H5, H7 | ✅ |
| AC1 | Acc 1 | "two exports, one named in a doc → one row; an allowlisted export → no row" | fixture | ✅ |
| AC2 | Acc 2 | "run on `src/components/ui/**`, `src/lib/**` against `docs/CONVENTIONS_FE.md`" | consumer, hand-checked | ✅ |
| AC3 | Acc 3 | "Runtime on the anchor for one path glob" | timed | ✅ |

**Gap.** Nothing reads the docs → code direction backwards; the index holds both sides.

`BASELINE: green — the 460 suites, its proving test and the tool-surface suites: 1085 passed`

Ran at fa6ca529 (pre-change)
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q $(cat .mango/baseline-461.list)
1085 passed in 47.49s
```

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 kinds, containers and modifier words, no language; R1.4 the node query lives in store.py · §2 (change-type) ✅ R2.2 the core names no test-file convention — an exclusion glob is the caller's · §5 (change-type) ✅ R5.3 an unreadable allowlist is a config error; R5.8 ordered before the cap · §6 (change-type) ✅ R6.5 seen failing on the base, R6.7 the knob joins the derived guards · §7 (change-type) ✅ R7.5, R7.6 TOOLS lines in place · §9 (change-type) ✅ R9.1 the allowlist is read through containment; the row fields are untrusted; R9.4 the tool surface change is in the manifest and CHANGELOG`

## Phase 2 — design

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `diff-every-row-not-the-target-rows` — traced: every row of the consumer's run read by hand (Phase 3), not a count.

**Approach.** (1) `store.nodes_of_kinds_under`. (2) `doc_refs.undocumented` + `_top_level` + `_allowlist` +
`undocumented_markdown`. (3) the tool's `undocumented` parameter. (4) `query --undocumented / --docs / --fail-on any`.
(5) the `refs_undocumented_allow` knob. **Rejected:** a `compute` template (no doc scan in its sandbox); judging a
test file by its name in the core (R2) — a `!` glob is the caller's.
**Assumptions:** none novel.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| node query | `code_atlas/store.py` | `test_sql_confinement.py` | R1 |
| the answer | `code_atlas/doc_refs.py` | `test_verify_refs*.py` | R1, R3 |
| tool parameter | `code_atlas/tools/verify_refs.py` | `tests/fixtures/tool_manifest.json`, `test_tool_surface_budget.py` (cap +145) | R2 |
| CLI | `code_atlas/query.py` | `test_verify_refs_actionable.py` (`--fail-on`) | R2 |
| knob | `code_atlas/config.py` | `test_config.py` | R3 |
| proving test | `tests/test_undocumented_exports.py` | — | AC1 · 4/4 |
| docs | `docs/TOOLS.md`, `CHANGELOG.md` | `test_doc_size_budget.py` | R7.6, R9.4 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration (built index, Python + TS, the tool and the CLI) | integration fixture | authored | ✅ |
| AC2 | e2e (the consumer) | manual-recorded: the run, every row read by hand | n/a | ✅ |
| AC3 | runtime (the anchor) | manual-recorded: timed run | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `tests/test_undocumented_exports.py`. Rollback: revert. Porting: one repo.

## Phase 3 — execute

Main loop, in the worktree, at `616670e3` and `0e2666e6`. **Sweep.** Axis 1: the diff is the approved list; `ruff`,
`mypy` clean. Axis 2: (1)–(5) implemented-as-approved, plus one **deviation**: the consumer's first run returned 17
helpers from `*.test.ts` files its adapter does not mark as tests; a path glob starting `!` now excludes (fixture row),
since the core may not name a test file by its name (R2.2).

Ran at fa6ca529 (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_undocumented_exports.py   # base + the new test only
3 errors in 0.63s
```

At `0e2666e6` (superseded by the review fixes) the suites read `1090 passed`, the consumer 2 rows of 130 in 0.7 s and
the anchor 28.5 s; Phase 4 holds the reviewed tree's runs.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. `reviewer` (Sonnet), and the ticket-blind `challenger` on the raw ticket
(`git show fa6ca529:<this file>`) + the branch diff.

- **Reviewer round 1** at `0e2666e6` (71,427 tokens): CHANGES REQUESTED, conditional on 1–3. **Taken** (`685d24e7`):
  (1) a caller's glob reached `glob_regex` unbounded — `**/` + 20 × `*a` + `*b` ran past 120 s — `check_globs` caps
  count, length and `*`, for `undocumented` and every caller glob of `collect`; each file matched once; (2) only
  `TOP_LEVEL_KINDS` load, `is_test` filtered in SQL — a member kind never reaches memory; (3) the visibility words
  moved to `contract.py`; (4) `no_docs_read`; (5) `patch` refused, the tool's default page 20; (6) tests.
- **Challenger round 1** at `0e2666e6` (66,459 tokens): 9 rebuilt · 8 met · AC3 can't tell (no threshold named).
  **Taken**: `documented_by_file` counts the exports a doc covers only by naming their file — the rule stays (W1), the
  masking is visible (consumer: 87 of 130).
- **Reviewer round 2** (resumed, 6,652 tokens): LGTM; two minor items. **Taken** (`d13b5abf`): the TOOLS line and the
  `?`/`[` comment. **Challenger round 2** (resumed, 6,278 tokens): AC3 met on the ticket's wording; 9 met.
- **Reviewer round 3** (verify-only, main loop, at `d13b5abf`): the comment and the TOOLS line as described.

The round-1 rows (`no_docs_read`, the glob cap, the documented-by-file count) were seen red on the superseded tree
`0e2666e6` (its code, this test file): three failures.

`CHALLENGER VERDICT: 9 requirement(s) rebuilt | 9 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

Ran at d13b5abf
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_undocumented_exports.py $(cat .mango/baseline-461.list)
1092 passed in 43.30s
```

**AC2 — the consumer** (`--undocumented 'web/src/components/ui/**' 'web/src/lib/**' '!**/*.test.*' --docs
docs/CONVENTIONS_FE.md`, backup index copy):

Ran at d13b5abf
```
reason ok · candidates 130 · documented_by_file 87 · total_count 2 · docs_read 1 · visibility_not_emitted [typescript]
lib/sceneSeconds.ts:5 Function words — a module-private const: false, the coverage line explains (no export visibility)
lib/sceneSeconds.ts:7 Interface SceneSeconds — exported; the catalogue names `sceneSeconds`, not this type: true
```

**AC3 — the anchor**, its largest top-level folder as the one glob, its default doc corpus:

Ran at d13b5abf
```
real 0m26.426s · candidates 7707 · documented_by_file 2885 · total_count 2207 · docs_read 2025
visibility_not_emitted [php, typescript]
```

Reviewed at d13b5abf — files: `code_atlas/contract.py`, `code_atlas/store.py`, `code_atlas/doc_refs.py`,
`code_atlas/tools/verify_refs.py`, `code_atlas/query.py`, `code_atlas/config.py`, `tests/test_undocumented_exports.py`,
`tests/test_config.py`, `tests/test_tool_surface_budget.py`, `tests/fixtures/tool_manifest.json`, `docs/TOOLS.md`,
`CHANGELOG.md`; working doc `docs/tasks/461_undocumented-exports.md`.

`Ph3/4 proven by`: R1–R3, AC1 → `tests/test_undocumented_exports.py` (6); AC2, AC3 → the corpus blocks.

## Phase 5 — finalise

Stale-review guard: only bookkeeping after `d13b5abf` — not stale.

**Durable lesson.** A second sighting of 430-C1 `redos-is-overlap-not-nesting`: a glob compiled to a regex is
ambiguous under repetition the same way an alternation is, so a caller's glob needs a bound before it compiles. Now
seen 430, 461 — recurring.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`

Falsify: still true — `glob_regex` is unchanged and the caps bound only its input; the reviewer's probe ran past 120 s
on `0e2666e6`. Proposed for `ENGINEERING_RULES.md` §9: caller text compiled to a regex is bounded before it compiles.
Unratified, so written nowhere; `/mango:promote` is the cross-ticket pass.

### Outward actions

Under the handover: push `feat/461-undocumented-exports`; open its PR against `feat/460-verify-refs-planned-marker`
(#194, stacked). Deferred to the maintainer: ratify W1–W3 and the rule proposal; merge after #194.
Revert: revert the branch's commits.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 48,850 |
| 3 execute | `implementer` — not dispatched (main loop implemented) | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | rule-book `reviewer` | 1 | 71,427 |
| 4 review | rule-book `reviewer` | 2 | 6,652 (resumed: 78,079 cumulative − 71,427) |
| 4 review | ticket-blind `challenger` | 1 | 66,459 |
| 4 review | ticket-blind `challenger` | 2 | 6,278 (resumed: 72,737 − 66,459) |

`LEDGER TOTAL: 199,666 · top cost driver: 4 review / reviewer` — main loop unmeasured.
