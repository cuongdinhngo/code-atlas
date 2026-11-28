---
id: 457
slug: verify-refs-callable-container-not-gone
title: "A dotted name whose head only matches a method or function is not a member reference"
phase: 2
milestone: "Field gaps — Python/TS consumer"
status: done
depends_on: [443]
---

## Why this exists

Same field report as 456 (the Python/TS consumer, 2026-11-27). Docs name dotted words that are **not code**:
telemetry event names, SQL `table.column` pairs, Playwright calls on a local. `_resolve` takes the
part before the last dot, finds *some* indexed symbol with that last word, and asks `_member`.
That symbol is often a **method**, which has no members. Git never saw the member in the method's
file, so the row is `gone` / `missing_on_live_container` and actionable.

| Doc ref (rows) | What it really is | Container it was matched to |
|---|---|---|
| `llm.rejected` (7), `llm.call` (4) | telemetry events | `pipeline.Providers::llm` |
| `run.start` (3), `run.end` (5) | telemetry events | `pipeline.Pipeline::run` (method) |
| `step.end` (5) | telemetry event | `occlusion.OcclusionReport::step` |
| `tts.batch` (3), `tts.synth` (2) | telemetry events | `metrics.Metrics::tts` |
| `render.end` (3) | telemetry event | `HyperframesRenderer::render` (method) |
| `jobs.series_id` (3), `jobs.video_id` (2), `jobs.project_id`, `jobs.log_path` | SQL columns | `SqliteJobQueue::jobs` (method) |
| `accounts.slug` (3), `accounts.id`, `videos.channel_id`, `videos.published_at`, `channels.account_id` | SQL columns | `SqliteJobQueue::accounts` / `::videos` / `::channels` |
| `page.evaluate` | Playwright API on a local | `tests…test_cyber.page` (fixture function) |

Around 50 of the 70 false rows. The match on a lowercase head word is the weak point: `run` or
`jobs` in prose almost never means "the method `Pipeline.run`".

## Scope

1. If the matched container is a function or method (no class or record body), a following segment
   is not a member reference → `unknown` (reason `container_is_callable`), not actionable.
   456 handles a property or method **with** a return annotation first.
2. If the head is a lowercase word that matches a container only by its **last** segment (not its
   qualified name or class name), the row is `weak`. This only changes `strength`; the state stays.
3. Optional, if cheap: when an indexed SQL table has the head's name and a column with the tail's
   name, `ok` (reason `table_column`). Uses what the SQL adapter already emits; no new parser.

## Acceptance

1. Fixtures: `run.end` against a class with method `run` → `unknown`, not actionable;
   `Repo.gone` against a class `Repo` keeps today's verdict; a lowercase head that matches only a
   member name → `weak`.
2. Re-run the Python/TS consumer: none of the rows in the table above is actionable. Report the count.
3. Anchor: the instruction-class actionable count before and after. A drop is fine if each dropped
   row is shown to be a non-code word.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Last updated:** 2026-11-28
- **Current phase:** finalise
- **Next action:** the maintainer merges #190, then this PR; 458 runs next, stacked on this branch
- **Blocked on:** nothing
- **KEY:** 457 · **work_doc_mode:** embed · `TRACK: backend` · Run mode: `autorun 456 - … - 462`, second —
  `REVIEWER: ON` · `CHALLENGER: ON` · `cost_tier: standard`. A want-decision is `ASSUMED` under the handover.
- Branch `feat/457-verify-refs-callable-container-not-gone` from 456's tip `6134b3e4` (#190), in a worktree. Contract
  `.mango/run-contract-457.txt`; RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 3 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 2 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 3 want-decision asked | 7 how-decision resolved+cited | 3 ASSUMED | skip: no`

`_resolve`, `_member` and the `table.column` path resolve in `doc_refs.py`; ambiguous: the table's containers live in
the consumer repo, all present in its index. Recalled: 456-C1 `diff-every-row-not-the-target-rows`, 438-C1
`area:verify_refs` (handles), 398-C1 (area: worktrees). Exposure-checker: 5 returned (H5–H7, W2–W3).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | a callable container | how | a `CALLABLE_KINDS` node 456's type walk leaves untyped → `unknown` (`container_is_callable`) (Scope 1; `contract.py:85`) |
| H2 | the weak head | how | the doc's first word is lowercase, its matches are all members (not `TYPE_KINDS`) reached by their last segment (Scope 2) |
| H3 | state under `weak` | how | unchanged; only `strength` moves (Scope 2) |
| H4 | `table.column` | how | an indexed column already resolves as written (`_matches`, `doc_refs.py:556`): a fixture proves it, no code (Scope 3) |
| H5 | 456's callable rows | how | `untyped_container` → `container_is_callable` in `test_verify_refs_declared_type.py` — the reason Scope 1 names |
| H6 | an untyped value container (`Metrics::tts`) | how | already `unknown` since 456; the weak head covers the row's actionability |
| H7 | what `weak` changes | how | `is_actionable` needs `strong` (`doc_refs.py:884`), so a weak row leaves every actionable count |
| W1 | showing AC3's dropped rows are words | want | **ASSUMED:** counts and categories in tracked files; row lists stay untracked (R2.4) |
| W2 | a head matching a class and a member | want | **ASSUMED:** strong — a class match keeps today's walk |
| W3 | attributes set on a function | want | **ASSUMED:** the recall loss is accepted: `unknown`, never `gone` |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=0 R=3 G=1 AC=3`
`CLARIFICATION: 10 raised | 10 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/5 touched files under UI paths`
`SCOPE: S`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "The match on a lowercase head word is the weak point" | non-code words leave the actionable set | ✅ |
| R1 | Scope 1 | "a following segment is not a member reference → `unknown` (reason `container_is_callable`)" | H1 | ✅ |
| R2 | Scope 2 | "the row is `weak`. This only changes `strength`" | H2, H3 | ✅ |
| R3 | Scope 3 | "Optional, if cheap: … `ok` (reason `table_column`)" | H4: `ok indexed` already, no new reason | ✅ |
| AC1 | Acc 1 | "`run.end` … → `unknown`; `Repo.gone` keeps today's verdict; a lowercase head … → `weak`" | fixture rows | ✅ |
| AC2 | Acc 2 | "none of the rows in the table above is actionable" | 47 rows in today's corpus | ✅ |
| AC3 | Acc 3 | "the instruction-class actionable count before and after" | counts; a drop shown as words (W1) | ✅ |

**Gap.** 456 left a callable with no type `untyped_container`, and nothing marks a container matched only by a
member's name, so `tts.batch` still read strong `gone` through `Pipeline::tts`'s type.

`BASELINE: green — the 456 suites plus its proving test: 869 passed`

Ran at 6134b3e4 (pre-change)
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q $(cat .mango/baseline-457.list)
869 passed in 29.76s
```

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 the head rule reads case and node kinds, no language · §5 (change-type) ✅ R5.6 a callable container is unknown, never gone · §6 (change-type) ✅ R6.1 fixture over a built index, R6.5 seen failing on the base · §7 (change-type) ✅ R7.5 comments ≤ 3 lines, R7.6 the TOOLS line rewritten in place · §9 (change-type) ✅ R9.1 `matched_by` is a fixed vocabulary value, not repo text`

## Phase 2 — design

`HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- `diff-every-row-not-the-target-rows` — traced: the consumer's 456-code and 457-code exports diffed by (file, line,
  ref) on one index copy (Phase 3 block): no newly actionable row.
- `area:verify_refs` — does not apply because the head check is one `_matches` seek per reference, no git history.

**Approach.** (1) `_through_type`: no type on a `CALLABLE_KINDS` owner → `container_is_callable`. (2) `_by_head` marks
a container-path verdict `matched_by: member_name` when the first word is lowercase and every match is a member reached
by its last segment; `strength()` reads it as `weak`. (3) Scope 3 by fixture only — reversed at review (below). **Rejected:** marking every lowercase head weak — a class written lowercase
(`lib.ir`'s module path) would lose real rows. **Assumptions:** none novel.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| the two rules | `code_atlas/doc_refs.py` | `test_verify_refs*.py`, the stored summary | R1, R2 |
| proving test | `tests/test_verify_refs_callable_container.py` | — | AC1 · 7/7 |
| 456's callable rows | `tests/test_verify_refs_declared_type.py` | — | H5 |
| docs | `docs/TOOLS.md`, `CHANGELOG.md` | `test_doc_size_budget.py` | R7.6 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration (built index, Python + SQL adapters) | integration fixture | authored | ✅ |
| AC2 | e2e (the consumer) | manual-recorded: export pair on one index copy | n/a | ✅ |
| AC3 | e2e (the anchor) | manual-recorded: export pair | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `tests/test_verify_refs_callable_container.py`. Rollback: revert. Porting: one repo.

## Phase 3 — execute

Main loop, in the worktree, at `54d33f50` (review fixes at `c015a5e7`, `004d4420`). **Sweep.** Axis 1: the diff is the approved list; `ruff`, `mypy` clean.
Axis 2: (1)–(3) implemented-as-approved. Golden change (H5): four 456 rows' reason, approved at Gate 2.

Ran at 6134b3e4 (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_verify_refs_callable_container.py   # base + the new test only
3 failed, 4 passed in 0.85s
```

At `54d33f50` (superseded by the review fixes) the same suites read `876 passed`; Phase 4 holds the run on the
reviewed tree.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. `reviewer` (Sonnet), and the ticket-blind `challenger` on the raw ticket
(`git show 6134b3e4:<this file>`) + the branch diff.

- **Reviewer round 1** at `54d33f50` (65,481 tokens): CHANGES REQUESTED, conditional on 1. **Taken** (`c015a5e7`):
  (1) a lowercase package head (`core.ir.Theme.old`, a `Namespace` named `core`) was marked weak and lost a true
  `gone` — only value and callable matches mark a head now, fixture row added; (2) the head check is memoised.
- **Challenger round 1** at `54d33f50` (59,150 tokens): 7 rebuilt · 5 met · Scope 3 not met (the ticket names a
  `table_column` reason; the design had reused `indexed`) · AC3 pending. **Taken** (`c015a5e7`): a direct hit on
  `Column` nodes answers `table_column` — the design's rejection of that reason reversed; it changed scope, so both
  seats were re-dispatched.
- **Reviewer round 2** (resumed, 6,990 tokens): findings landed; new: reuse `contract.COLUMN_KIND`, name the reason
  in TOOLS. **Taken** (`004d4420`). **Challenger round 2** (resumed, 4,938 tokens): Scope 3 met, AC2 holds.
- **Reviewer round 3** (verify-only, main loop, at `004d4420`): the import swap and the TOOLS line as described.

The two round-1 rows were seen red on the superseded tree `54d33f50` (its code, this test file): `1 failed, 7 passed`
before the package fixture, then both `jobs.series_id` and `core.ir.Theme.old` failing once `src/core/__init__.py`
made `core` a package.

Ran at 004d4420
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q $(cat .mango/baseline-457.list) tests/test_verify_refs_callable_container.py
877 passed in 29.94s
```

**AC2 — the consumer**, 456 code and this branch back to back on one index copy:

Ran at 004d4420
```
before (6134b3e4): 14 actionable
after  (004d4420): 1947 rows, 4 actionable — the ticket table's 47 rows: 0 actionable; no row newly actionable
dropped: tts.batch ×3, tts.synth ×2, voice_pace.json ×2, and 456's three data-file rows (its delta)
```

**AC3 — the anchor**, 456 code and this branch on one backup index copy:

Ran at 004d4420
```
before (6134b3e4): 306 actionable — instruction gone 16, moved 0
after  (004d4420): 306 actionable — instruction gone 16, moved 0; 0 rows newly actionable, 0 dropped
2,167 rows ok indexed → ok table_column; 1,122 unknown untyped_container → unknown container_is_callable
```

- **Challenger round 3** (resumed, AC3 only, 1,896 tokens): re-derived from the raw exports; no drop, so nothing to show.

`CHALLENGER VERDICT: 7 requirement(s) rebuilt | 7 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

Reviewed at 004d4420 — files: `code_atlas/doc_refs.py`, `tests/test_verify_refs_callable_container.py`,
`tests/test_verify_refs_declared_type.py`, `docs/TOOLS.md`, `CHANGELOG.md`; working doc
`docs/tasks/457_verify-refs-callable-container-not-gone.md`.

`Ph3/4 proven by`: R1–R3, AC1 → `tests/test_verify_refs_callable_container.py` (8); AC2, AC3 → the corpus blocks.

## Phase 5 — finalise

Stale-review guard: only bookkeeping after `004d4420` — not stale.

**Durable lessons.** 457-C1 `accept-by-kind-not-reject-by-kind` and 457-C2 `a-named-value-in-the-ticket-is-the-bar`
(type 2, first sightings) in `docs/LESSONS.md`.

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/457-verify-refs-callable-container-not-gone`; open its PR against
`feat/456-verify-refs-follow-declared-type` (#190, stacked). Deferred to the maintainer: ratify W1–W3; merge after
#190. Revert: revert the branch's commits.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 49,986 |
| 3 execute | `implementer` — not dispatched (main loop implemented) | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | rule-book `reviewer` | 1 | 65,481 |
| 4 review | rule-book `reviewer` | 2 | 6,990 (resumed: 72,471 cumulative − 65,481) |
| 4 review | ticket-blind `challenger` | 1 | 59,150 |
| 4 review | ticket-blind `challenger` | 2 | 4,938 (resumed: 64,088 − 59,150) |
| 4 review | ticket-blind `challenger` | 3 | 1,896 (resumed: 65,984 − 64,088) |

`LEDGER TOTAL: 188,441 · top cost driver: 4 review / reviewer` — main loop unmeasured.
