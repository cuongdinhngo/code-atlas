---
id: 460
slug: verify-refs-planned-marker
title: "A planned reference reports `planned`, and a marker whose target now exists says so"
phase: 2
milestone: "Field gaps — Python/TS consumer"
status: done
depends_on: [443]
---

## Why this exists

Same field report as 456. The Python/TS consumer's conventions now hold a "shared building blocks" catalogue.
Each row is ✅ (it exists) or ⏳ with the task that will build it, e.g. `src/lib/errors.ts` (T30.2).
Specs and ADRs name files that a later task creates, too. Those rows come back
`never_existed`. That is correct, and not actionable, so they are silent.

The useful signal is the other way round, and nothing reports it:
- a planned file that now **exists**, so the marker should be dropped;
- a planned ref whose task is closed but whose file never came.

The consumer is writing its own CI test for this. A general marker would let any repo get
it from `verify_refs`.

## Scope

1. Read a configurable planned marker on the ref's line or table row (default: none; config such as
   `refs_planned_markers = ["⏳", "(planned)"]`). Such a row reports state `planned` and is never
   actionable while its target is absent.
2. A `planned` row whose target now resolves → `ok` with reason `planned_but_exists`, counted in the
   summary as "markers to drop". Language-free, no tracker integration.
3. No marker configured → today's behaviour, byte for byte.

## Acceptance

1. Fixtures: a marked absent path → `planned`; a marked existing path → `planned_but_exists`; no
   config → unchanged output (golden).
2. The summary and `--format md` list `planned_but_exists` rows; `--fail-on` can name it.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Last updated:** 2026-11-28
- **Current phase:** finalise
- **Next action:** the maintainer merges #193, then this PR; 461 runs next, stacked on this branch
- **Blocked on:** nothing
- **KEY:** 460 · **work_doc_mode:** embed · `TRACK: backend` · Run mode: `autorun 456 - … - 462`, fifth —
  `REVIEWER: ON` · `CHALLENGER: ON` · `cost_tier: standard`. A want-decision is `ASSUMED` under the handover.
- Branch `feat/460-verify-refs-planned-marker` from 459's tip `f598cb1d`, in a worktree. Contract
  `.mango/run-contract-460.txt`; RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 3 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 3 want-decision asked | 9 how-decision resolved+cited | 3 ASSUMED | skip: no`

`--fail-on`, `--format md` and the summary resolve (`query.py`, `doc_refs.py`); `refs_planned_markers` is to be
created. Ambiguous: the consumer's catalogue — read on this host: its `⏳` sits on 4 legend lines with no reference.
Recalled: 456-C1 `diff-every-row-not-the-target-rows` (handle), 398-C1 (area). Exposure-checker: 6 returned (H7–H9, W1–W3).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the config | how | `refs_planned_markers` in `.code-atlas.toml` / `CA_REFS_PLANNED_MARKERS`, default none (Scope 1) |
| H2 | "the ref's line or table row" | how | the source line; a markdown table row is one line (Scope 1) |
| H3 | verdicts | how | marked and not `ok` → state `planned`, reason kept, never actionable; marked and `ok` → `planned_but_exists` (Scope 1–2) |
| H4 | unconfigured | how | byte for byte: `planned` and `markers_to_drop` appear only when markers are configured — a golden captured from the base (Scope 3, AC1) |
| H5 | the surfaces | how | a "markers to drop" section in `--format md`; `--fail-on planned_but_exists` (AC2) |
| H6 | the marker's text | how | never parsed — no tracker integration (Scope 2) |
| H7 | where the counts sit | how | a `planned_but_exists` row is `ok` in `by_class` and in `markers_to_drop`; not actionable |
| H8 | the env syntax | how | comma-separated, as every list knob (`as_doc_globs`, `config.py:662`); a marker may hold no comma |
| H9 | the MCP tool | how | it calls the same `summarize`, so the same keys (R1.8) |
| W1 | matching | want | **ASSUMED:** a case-sensitive substring of the line; a blank marker is dropped, one over 32 characters refused |
| W2 | a marker on another line | want | **ASSUMED:** not counted — the ref's own line only |
| W3 | `--fail-on planned_but_exists` unconfigured | want | **ASSUMED:** a valid value that never fires, so a CI gate written first does not break |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=1 R=2 G=1 AC=2`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a planned file that now **exists**, so the marker should be dropped" | the stale-marker signal | ✅ |
| R1 | Scope 1 | "Such a row reports state `planned` and is never actionable while its target is absent" | H1–H3 | ✅ |
| R2 | Scope 2 | "`ok` with reason `planned_but_exists`, counted in the summary as 'markers to drop'" | H3, H7 | ✅ |
| C1 | Scope 3 | "No marker configured → today's behaviour, byte for byte" | H4, the golden | ✅ |
| AC1 | Acc 1 | "a marked absent path → `planned`; a marked existing path → `planned_but_exists`; no config → unchanged output (golden)" | fixture + golden | ✅ |
| AC2 | Acc 2 | "The summary and `--format md` list `planned_but_exists` rows; `--fail-on` can name it" | H5 | ✅ |

**Gap.** Nothing reads a marker: a planned path is `never_existed` and silent, a planned file that appeared is a
plain `ok`.

`BASELINE: green — the 459 suites, its proving test and the two config suites: 975 passed`

Ran at f598cb1d (pre-change)
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q $(cat .mango/baseline-460.list)
975 passed in 40.23s
```

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §5 (change-type) ✅ R5.6 planned and never_existed are separate states once configured · §6 (change-type) ✅ R6.5 seen failing on the base, R6.7 the knob joins the derived precedence guard · §7 (change-type) ✅ R7.5 comments ≤ 3 lines, R7.6 the TOOLS row and sentence · §9 (change-type) ✅ R9.1 a marker is matched as text, never run; ≤ 32 characters · §3 (change-type) ✅ R3.5 no published version constant guards the verify_refs payload; unconfigured it is unchanged`

## Phase 2 — design

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `diff-every-row-not-the-target-rows` — traced: the consumer's export with `CA_REFS_PLANNED_MARKERS="⏳"` (Phase 3):
  1954 rows, 0 `planned`, 0 `planned_but_exists` — its markers sit on legend lines with no reference.

**Approach.** (1) `config.as_markers` + the `refs_planned_markers` knob. (2) `Mention.marked` set by `extract` from the
line. (3) `_rows` applies `_planned` to a marked mention's verdict. (4) `PLANNED`, `ALL_STATES`; `summarize` counts
`planned` and `markers_to_drop` only when configured; `markdown` adds the column and a "markers to drop" section only
then. (5) `query --fail-on planned_but_exists`. **Rejected:** always counting `planned` — the unconfigured payload
would gain a zero key and break Scope 3; parsing the marker's task id — Scope 2 rules it out.
**Assumptions:** none novel.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| the knob | `code_atlas/config.py` | `test_config.py` (precedence and env-name guards) | R1 |
| marks, state, summary | `code_atlas/doc_refs.py` | `test_verify_refs*.py`, the MCP tool's payload | R1, R2, C1 |
| `--fail-on` | `code_atlas/query.py` | `test_verify_refs_actionable.py` | AC2 |
| proving test + golden | `tests/test_verify_refs_planned.py`, `tests/fixtures/verify_refs/planned_unconfigured.json` | — | AC1, AC2 · 6/6 |
| knob guards | `tests/test_config.py` | — | R6.7 |
| docs | `docs/TOOLS.md`, `CHANGELOG.md` | `test_doc_size_budget.py` | R7.6 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration (built index, scan, summary) | integration fixture + a golden from the base | authored | ✅ |
| AC2 | integration (CLI exit code, md) | `query.main` over the fixture | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `tests/test_verify_refs_planned.py`. Rollback: revert. Porting: one repo.

## Phase 3 — execute

Main loop, in the worktree, at `02e31126`. **Sweep.** Axis 1: the diff is the approved list; `ruff`, `mypy` clean.
Axis 2: (1)–(5) implemented-as-approved.

Ran at f598cb1d (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_verify_refs_planned.py   # base + the test and its golden
1 passed, 5 errors in 1.22s
```

At `02e31126` (superseded by the review fixes) the suites read `1072 passed`; Phase 4 holds the reviewed tree's run.

The golden passing on the base is the point of it: it was captured there. The five errors are the base refusing the
unknown `refs_planned_markers` key.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. `reviewer` (Sonnet), and the ticket-blind `challenger` on the raw ticket
(`git show f598cb1d:<this file>`) + the branch diff.

- **Challenger round 1** at `02e31126` (59,540 tokens): 7 rebuilt · 7 met. Note **taken** (`ff47b6a2`): every non-`ok`
  state became `planned`; now only an absent target (`never_existed`, `gone`) does — `moved`, `ambiguous`, `unknown`
  keep their state, so a marker never hides an unchecked or actionable row.
- **Reviewer round 1** at `02e31126` (69,325 tokens): CHANGES REQUESTED, conditional on 1–2. **Taken** (`ff47b6a2`):
  (1) the MCP tool's `State` and `--state` lacked `planned` while `check_filters` took it — both derive from
  `ALL_STATES` now, guarded; the tool manifest regenerated and `SURFACE_CAP` +15 (collateral); (2) the default call
  counted markers to drop but its page holds only actionable rows — `markers_to_drop_rows` is its own field;
  (3) the count uses `counted()`, as `by_class`; (4) `extract` sets `marked` at construction. Both new tests seen failing
  on `02e31126`. The reasons are R5.5's and R6.7's classes, already carried by the rule book.
- **Reviewer round 2** (resumed, 6,905 tokens): LGTM; nit — cap the drop rows. **Taken** (`6cfd0538`).
- **Reviewer round 3** (verify-only, main loop, at `6cfd0538`): the cap and its test as described.

`CHALLENGER VERDICT: 7 requirement(s) rebuilt | 7 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

Ran at 6cfd0538
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_verify_refs_planned.py $(cat .mango/baseline-460.list) tests/test_tool_surface_budget.py tests/test_mcp_server.py tests/test_tool_manifest.py
1085 passed in 57.47s
```

Reviewed at 6cfd0538 — files: `code_atlas/config.py`, `code_atlas/doc_refs.py`, `code_atlas/query.py`,
`code_atlas/tools/verify_refs.py`, `tests/test_verify_refs_planned.py`, `tests/fixtures/verify_refs/planned_unconfigured.json`,
`tests/test_config.py`, `tests/test_tool_surface_budget.py`, `tests/fixtures/tool_manifest.json`, `docs/TOOLS.md`,
`CHANGELOG.md`; working doc `docs/tasks/460_verify-refs-planned-marker.md`.

`Ph3/4 proven by`: R1, R2, C1, AC1, AC2 → `tests/test_verify_refs_planned.py` (9) and its golden.

## Phase 5 — finalise

Stale-review guard: only bookkeeping after `6cfd0538` — not stale.

**Durable lesson.** None new: both review findings are sightings of classes the rule book carries — R5.5 (a count
and the list it names come from one computation) and R6.7 (a closed set every surface names is derived) — so, by
`LESSONS.md`'s own rule, they cite the rules and open no claim.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/460-verify-refs-planned-marker`; open its PR against
`feat/459-verify-refs-memory-links-resolve-in-memory` (#193, stacked). Deferred to the maintainer: ratify W1–W3;
merge after #193. Revert: revert the branch's commits.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 49,698 |
| 3 execute | `implementer` — not dispatched (main loop implemented) | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | rule-book `reviewer` | 1 | 69,325 |
| 4 review | rule-book `reviewer` | 2 | 6,905 (resumed: 76,230 cumulative − 69,325) |
| 4 review | ticket-blind `challenger` | 1 | 59,540 |

`LEDGER TOTAL: 185,468 · top cost driver: 4 review / reviewer` — main loop unmeasured.
