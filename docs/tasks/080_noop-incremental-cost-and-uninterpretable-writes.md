---
id: 080
slug: noop-incremental-cost-and-uninterpretable-writes
title: 'A no-op incremental costs ~56 s and reports 6,071 edges written for 0 files parsed'
phase: 1.5b
milestone: Cost
status: done
depends_on: [052, 051, 060]
---

## Goal
Round 4 timed five builds on the anchor monorepo: **273 files → 107.9 s**, **4 files → 57.6 s**,
**0 files → 56.1 s and 57.4 s**. A build that parses nothing costs within 2% of a build that parses
four files, and the no-op payload reports `wrote: {files: 0, parsed: 0, nodes: 0, edges: 6071}` —
6,071 edges written having read no file. [052](052_incremental-noop-cost.md) profiled this cost and
took a decision; the field number says the outcome an agent experiences has not moved. Two things are
wrong: the floor, and a number nobody outside can interpret.

## Evidence (field retro round 4, 2026-08-10, §5 and §11 item 5)
- Five builds, all on the same index, timings above; the two no-ops are independent runs, not one
  outlier.
- No-op payload shape, verbatim from the retro: `wrote:{files:0,parsed:0,nodes:0,edges:6071}`, twice,
  at ~56 s each.
- Same-process build/status pair (probe for §A.12) shows the totals agreeing exactly —
  `graph:{files:18888,parsed:18859,failed:29,nodes:186134,edges:1784018}` vs status
  `18888/18859/29/186133/1784013` — so this is **not** a 051/060 reporting mismatch. 051 and 060 are
  verified fixed; this is a different question about the *no-op* row.
- The evaluator held R-2 (no source reading) and filed the interpretation gap as the finding: *"a
  payload that writes 6 k edges having parsed 0 files is not something I can interpret from outside"*.
- Operational consequence, already recorded in 053's reasoning and now measured again from the field:
  a hook that costs ~56 s per invocation gets uninstalled by whoever waits for it.

## Two deliverables, and they are separable
**A — the floor.** Find where a no-op spends ~56 s on a ~19k-file / 1.78M-edge index and either
remove the work or make it proportional to the delta. 052's profile is the starting point, not the
answer: re-measure on the current tree, because several tasks have landed since (enrichment, rules,
dedupe, freshness) and the profile may have moved.

**B — the number.** `wrote.edges` on a no-op must either be zero or be named for what it counts. If
those 6,071 edges are re-derived sibling/enrichment rows, the payload should say that — a delta field
that is non-zero when the delta is empty is unreadable by construction, and 060 established that the
build payload's field names are the contract an agent reads.

## Scope / Deliverables
- **Re-profile the no-op path on the current code** (full timing breakdown per phase), and record it
  in the ticket so the next round has a baseline to compare against.
- **Cut or bound the fixed cost.** State a target with the field number as the justification; if the
  cost is irreducible, say which phase it is and why, and make that visible in the payload rather than
  as a silent 56 seconds.
- **Make `wrote.*` mean the delta.** Either zero on a no-op, or split into delta vs re-derived groups
  with names that say which is which (060's pattern).
- **Re-check the hook and refresh paths** (036 `code-atlas-poke`, 053 `post-merge`/`post-checkout`)
  against the new floor, since both inherit it.
- **Cover the no-op with a test that asserts the payload shape**, so a future change cannot quietly
  reintroduce a non-zero delta.

## Constraints
- R4 — determinism: two consecutive no-ops must produce identical payloads (today's two runs agree at
  6,071, which is at least consistent).
- 060 / 051 — do not disturb the verified `wrote` vs `graph` split; this is a change *within* `wrote`.
- Cost work must not trade correctness: skipping enrichment or resolver passes to hit a number is a
  regression, not a fix, and 068's precedent (a bookmark that most call sites remembered to skip) is
  the anti-pattern to avoid.
- Measurement on the anchor repo is the operator's; the ticket's own tests run on fixtures.

## Acceptance criteria
- A recorded phase-by-phase profile of a no-op incremental on a large index, current as of this
  ticket.
- A no-op reports a delta of zero, or reports re-derived work under a name that says so; a test pins
  it.
- A stated, justified figure for the no-op floor after the change, with the before number beside it.
- 036 and 053 have a verdict on whether the new floor makes them usable as designed.

## References
Field retro round 4 §5 (five builds, timings), §11 item 5, §A.12 (the totals agree — this is not a
reporting mismatch). Related: [052](052_incremental-noop-cost.md) (the profile and its Outcome
decision), [051](051_build-report-edge-undercount.md) and
[060](060_build-report-scale-naming.md) (what the build payload's fields mean),
[036](036_edit-index-hook.md), [053](053_refresh-on-checkout-hook.md) (the two consumers of this
floor), [016](016_incremental-git.md).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 080

## Session status
- **work_doc_mode**: embed (below separator; plain tracked ticket, not a scaffold stub)
- **Phase**: 5 finalise; Gates 0/1/2 cleared (4 ASSUMED confirmed); **review WAIVED** (run arg)
- **Branch (planned)**: `fix/080-noop-incremental-cost-and-uninterpretable-writes`

## Phase 0 — Refine

### Premise check
`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
Resolved: tasks 052/051/060/036/053/016 (exist); the profiler (`indexer._phase_add`/`phase_times`, 052); the no-op late-writers `_count_late_writes` → `apply_indirection_rules` + `resolve_edges` (`indexer.py:247-267`); hooks `code-atlas-poke` (`hooks/poke.py`, uses `reparse_file`) and `code-atlas-refresh` (`hooks/refresh.py`, runs the incremental path). No referenced-as-existing source missing → premise holds.

### Advisory recall
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
LESSONS.md is prose-format; surfaced by area: **074** (a measurement ticket needing an external environment splits into prep → run → analyze — directly relevant: the ~56s floor is on the operator's anchor repo), **060** (build payload field names are the contract an agent reads — the `wrote.*` naming), **068** (a re-derived bookmark most call sites skip — the anti-pattern the ticket names for the cost cut). No `skill_gap_path` configured. Advisory only.

### Root-cause reading (grounds the scope decision)
The no-op floor and the 6,071 edges share one cause: `_count_late_writes` runs **`apply_indirection_rules` (enrichment) + `resolve_edges` full-graph on every build**, including a no-op (`indexer.py:234,260-267`). `resolve_edges` scans the unresolved-edge set of a ~1.78M-edge graph and re-inserts siblings; `counts["edges"] += enriched.edges + siblings` = the 6,071. Two no-ops agreeing at 6,071 (ticket §5) confirms the output is deterministic/idempotent — the rows are already in the store, so a no-op re-derives what is already there. **036/053 inheritance:** `code-atlas-poke` (036) uses `reparse_file` → `resolve_edges(file_path=…)` (already delta-scoped, does **not** inherit the floor); `code-atlas-refresh` (053) runs `build_or_update_index(full=false)` → the full incremental path → **does** inherit it.

### The scope decision (WANT, handed back → ASSUMED)
The ticket bundles two separable deliverables; **A (the ~56s floor)'s measurement is explicitly the operator's** (anchor monorepo — ~19k files / 1.78M edges — not available this session; cf. 074). Delegated to me → recorded **ASSUMED (awaiting Gate-1 confirm)**.

**ASSUMED-D — address A and B with one change: eliminate the no-op late-write work.**
When the delta is empty (nothing parsed, nothing reconciled), the late writers (enrichment + resolver) can only re-derive rows already present — so skipping/short-circuiting them on a true no-op both (A) removes the dominant fixed cost and (B) makes `wrote.edges == 0` on a no-op naturally. This honours the constraint "skipping … to hit a number is a regression" because it skips **only when the delta is empty** — i.e. not skipping needed work, only work whose output is already in the store (idempotent). The **timing** (56s → collect+diff+hash floor) is operator-confirmed on the anchor repo per the constraint; the **mechanism** (late writers do no work on an empty delta) is fixture-provable here (a test pins `wrote.edges == 0` and that the writers are not invoked). Design verifies idempotence and picks the exact mechanism (guard the call vs delta-scope the writers).
- **Rejected alt — B-only (rename `wrote` into delta vs re-derived groups, leave the floor):** readable, but leaves the ~56s the agent actually waits on — the ticket's primary complaint — untouched. The number and the floor have the same cause; fixing only the number is half the ticket.
- **Rejected alt — split A into a follow-up (074-style):** viable, but unlike 074 the *fix* here is code we can write and prove on fixtures; only the absolute seconds are operator-measured. No need to defer the whole of A.

### Acceptance-bar ASSUMED items (from the operator-measurement constraint)
- **ASSUMED-A — the "phase-by-phase profile on a large index" (AC1) and "stated figure for the floor after, before beside it" (AC3).** The anchor-repo seconds are the operator's. **Resolution:** record (a) the code-identified dominant phase (`resolve`/`enrichment` full-graph), (b) a fixture-scale phase profile showing that phase dominates a no-op, (c) before = field 56.1s/57.4s, after = the mechanism eliminates the dominant no-op phase → floor = collect + git-diff + hashing, with the operator's anchor re-measure named as the confirming step. Honest split, not a self-reported number.

### Decision classification (HOW — resolved + cited)
| # | Decision | Class | Resolution + citation |
|---|----------|-------|-----------------------|
| 1 | Where the no-op cost lives | HOW | `_count_late_writes` full-graph enrichment+resolver (`indexer.py:260-267`) |
| 2 | What the 6,071 edges are | HOW | re-derived enrichment + resolver siblings (`indexer.py:266-267`; `resolver.py:26`) |
| 3 | 036 verdict | HOW | poke uses `reparse_file` (file-scoped resolve) — already proportional; floor N/A |
| 4 | 053 verdict | HOW | refresh runs the incremental path — inherits the floor; the fix makes a no-op refresh cheap |
| 5 | Test on fixtures, not anchor | HOW | ticket constraint (line 64); pin `wrote.edges==0` + writers-not-run on a fixture no-op |

### Exposure-checker verdict (1 dispatch, ticket-blind)
Confirmed the root cause (`resolve_edges` unscoped at `indexer.py:264`, folds into `wrote.edges`). Surfaced **3 scope/done-bar decisions**, all delegated → **ASSUMED (Gate-1 confirm)**:

- **ASSUMED-A — closure does NOT gate on the operator's anchor-repo run.** 052 hit this exact fork and left 053 gated on an operator profile that never came, stalling it. **Resolution:** mark A's AC1/AC3 done on **fixture proof + mechanism + before(field 56.1/57.4s)/after(mechanism eliminates the dominant no-op phase → floor = collect+diff+hash)**, with the operator's anchor re-measure named as a **confirming follow-up, not a merge gate**. (074's split, but only the *seconds* trail — the fix and its proof ship here.)
- **ASSUMED-B — no schema change; the no-op fix is an empty-delta guard, not a resolver redesign.** The general "small nonempty delta also pays full resolve" case (4 files → 57.6s) would need delta-scoped resolver state (a schema change, Candidate 3) + anchor justification. That is **out of scope**: the ticket's title/Goal is the **no-op** (0 files). **Resolution:** fix the no-op with a **no-schema guard** — when the delta is empty (`to_parse == []` and `removed == 0`) the late writers do no work (their output is already in the store, idempotent). General small-delta resolver-scoping is a **named follow-up** (needs schema + anchor measurement), not silently dropped.
- **ASSUMED-C — 036/053 is a written verdict, not a redesign.** "Usable as designed" = a verdict. Any switch of 053 from background-spawn to inline on the back of a lower floor is a **follow-up**, out of scope here (don't widen). Verdict recorded: 036/poke already proportional (`reparse_file`, file-scoped); 053/refresh inherits the floor and the no-op guard makes a no-op refresh cheap → still usable as designed (background-spawn unchanged).

Plus **ASSUMED-D** (address A+B with the one empty-delta guard, above).

### REFINE count
`REFINE: 9 unresolved surfaced | 0 want-decision asked | 5 how-decision resolved+cited | 4 ASSUMED | skip: no`
4 ASSUMED (A done-bar, B schema/scope boundary, C 036/053 verdict-only, D the mechanism) surface at Gate 1 for one explicit confirm under standing approval. Hand to analysis.

### Cost ledger
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker (challenger, ticket-blind) | 1 | 57,798 (8 tool-uses, 187 s) |

## Phase 1 — Analysis

### Premise / recall (carried from refine)
`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)` — 074, 060, 068 (area).

### Chosen approach (ASSUMED-D, for Gate-1 confirm)
An **empty-delta guard**: in `incremental_update`, when `to_parse == []` **and** `removed == 0` (a true no-op), skip `_count_late_writes` (enrichment + resolver). Their output is already in the store and idempotent (two field no-ops agree at 6,071 → not accumulating), so skipping is state-equivalent — it cuts the dominant no-op cost (A) **and** makes `wrote.edges == 0` honestly (B). No schema change (ASSUMED-B). Full builds untouched (never a no-op).

### Decomposition count
`SECTIONS: 7 found (Goal, Evidence, Two deliverables, Scope/Deliverables, Constraints, Acceptance criteria, References) | 7 decomposed | ROWS: C=4 R=5 G=1 AC=4`

### Requirements matrix
| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|----|--------|------------------|----------------|--------------|--------|
| G1 | Goal | no-op costs ~56s and reports 6,071 edges for 0 files | Cut the floor + make the number readable | `_count_late_writes` full-graph on no-op (`indexer.py:234,260-267`) | open |
| R1 | Deliv A / Scope | re-profile the no-op path per phase on current code; record it | Code-identified dominant phase + fixture profile + field before-nums | `resolve_edges` unscoped (`resolver.py:18-24`, `indexer.py:264`) | open |
| R2 | Deliv A / Scope | cut or bound the fixed cost; state a target, or name the irreducible phase | Empty-delta guard → floor = collect+diff+hash; resolve/enrich eliminated on no-op | field 56.1/57.4s | open |
| R3 | Deliv B / Scope | make `wrote.*` mean the delta — zero on no-op, or split delta vs re-derived | Guard → `wrote.edges == 0` on no-op (the "zero" branch) | `counts` stays 0 when writers skipped | open |
| R4 | Scope | re-check hook/refresh paths (036, 053) against the new floor | Written verdict (ASSUMED-C, verdict-only) | poke=`reparse_file` file-scoped; refresh=incremental path | open |
| R5 | Scope | cover the no-op with a test asserting the payload shape | Fixture incremental no-op asserts `wrote.edges==0` + R4 determinism | no such test today | open |
| C1 | Constraint R4 | two consecutive no-ops → identical payloads | Guard is deterministic; both no-ops → edges:0 | field: both 6,071 (consistent) | open |
| C2 | Constraint 060/051 | don't disturb `wrote` vs `graph` split; change is *within* `wrote` | `graph`=store.counts() unaffected by skip | `indexer.py`/`get_index_status` | open |
| C3 | Constraint | cost work must not trade correctness; no skipping needed passes (068 anti-pattern) | Guard skips only on **empty** delta — output already present, idempotent | `resolve_edges` iterates unresolved set | open |
| C4 | Constraint | anchor measurement is the operator's; ticket tests run on fixtures | Fixture test for the shape; operator confirms seconds (ASSUMED-A) | ticket line 64 | open |
| AC1 | AC | recorded phase-by-phase profile of a no-op on a large index, current | Code phase + fixture profile + field 56s; operator re-measure = follow-up | — | open |
| AC2 | AC | no-op reports delta zero, or re-derived under a name that says so; a test pins it | Zero branch: `wrote.edges==0`; test pins | — | open |
| AC3 | AC | stated justified figure for the floor after, with before beside it | Before=56.1/57.4s (field); after=collect+diff+hash (mechanism), operator-confirmed | — | open |
| AC4 | AC | 036 and 053 have a verdict on usability | Verdict-only (ASSUMED-C) | — | open |

### AC validation (falsifiability) + the operator-measurement ASSUMED items
- **AC1** — *"profile on a large index, current"*: the absolute seconds need the anchor repo (operator's, C4). **ASSUMED-A:** satisfied by (a) code-identified dominant phase (`resolve`/`enrichment` full-graph), (b) a fixture per-phase profile showing that phase dominates a no-op, (c) field before-numbers, with the operator's anchor re-measure a **named confirming follow-up, not a merge gate** (avoids the 052→053 stall). Recorded as a **manual-check exclusion** for the absolute-seconds portion (unmeasurable here); the mechanism/profile portion is falsifiable and tested.
- **AC2** — falsifiable: a fixture no-op incremental asserts `wrote.edges == 0` (+ nodes/parsed 0) and a second no-op is identical (R4). ✔
- **AC3** — the *after* figure's seconds are operator-confirmed (same exclusion as AC1); the *mechanism* (resolve+enrich eliminated on no-op → floor = collect+diff+hash) is stated + justified by the field before-number. Falsifiable that the writers do no work (test); the seconds are the recorded exclusion.
- **AC4** — falsifiable: a written verdict for 036 (already proportional) and 053 (no-op refresh now cheap; background-spawn unchanged). ✔

**Coverage-gap exclusion (recorded, human-approved via standing delegation):** the *absolute anchor-repo seconds* for AC1/AC3 — unmeasurable in this session (no anchor monorepo; C4). Verified by the operator's re-run of `scripts/profile_incremental.py` (052) on the anchor as a follow-up. Not a blocker (ASSUMED-A).

**Uncodified-standard nudge:** none — no new numeric threshold is enforced (the floor "target" is qualitative: proportional-to-delta / zero on no-op).

### CLARIFICATION
`CLARIFICATION: 4 raised | 0 self-resolved | 4 for human decision (all ASSUMED, delegated)`
Gate 0 folds into Gate 1 under standing approval: **D** (empty-delta guard), **A** (no anchor-run merge gate; operator re-measure = follow-up + the recorded coverage-gap exclusion), **B** (no schema; general small-delta scoping = named follow-up), **C** (036/053 verdict-only).

### Universal inventory
No "all/every/no" requirement with N>1. The hook/refresh verdict (R4) is a per-item checklist N=2: **1.** 036 `code-atlas-poke`, **2.** 053 `code-atlas-refresh` — review confirms both verdicts, not a total.

### Cause / gap analysis (bug — taxonomy: `efficiency`/logic)
Root cause: `incremental_update` unconditionally runs `_count_late_writes` → `apply_indirection_rules` + `resolve_edges` **full-graph** even when the delta is empty (`indexer.py:234`; `resolve_edges` unscoped `resolver.py:18-24`). On a ~1.78M-edge index that scan is the ~56s floor, and its `siblings` return (6,071) folds into `wrote.edges` (`indexer.py:266-267`) — a delta field non-zero on an empty delta. Target: guard the late writers on an empty delta. `path:line` `indexer.py:141-237` (incremental), `:234` (the call), `:247-267` (`_count_late_writes`).

### Blast radius
- Handler: `incremental_update` (`indexer.py`). The guard adds a condition around one call.
- Touched: `code_atlas/indexer.py` (the guard), `tests/test_incremental.py` or a new `tests/test_noop_incremental.py` (the payload-shape test), docs (working-doc profile record + 036/053 verdict; PLAN §14 no-op note; the operator-profile follow-up note). No schema, no contract. Full builds untouched. `code-atlas-refresh` inherits the cheaper no-op automatically (no code change there). Repo `app` only. No core language branch.

### RULE SECTIONS (by change type)
`RULE SECTIONS: R4, §060/§051, R1.2, §068(anti-pattern) — R4 ✅ (deterministic; two no-ops identical), §060/§051 ✅ (change is within `wrote`; `graph` untouched), R1.2 ✅ (a ~3-line guard, no framework, no schema), §068 ✅ (skip only on empty delta — not skipping needed work). No DB-conventions (no migration). No UI/a11y (backend).`

### BASELINE
`BASELINE: green` — Docker scoped run (incremental/build_report/indirection/staleness/vendor_stub/refresh/poke): **95 passed, 0 failed**, 1042 deselected. Untouched checkout. DoD: delta-green.

### TRACK / SCOPE / TIER
`TRACK: backend — 0/N touched files under UI paths`
`SCOPE: M` (a small guard + one test + docs/profile/verdict; multi-deliverable but the code change is minimal)
`TIER: full` (four ASSUMED scope decisions, multi-deliverable ACs, a measurement-dependent AC with a recorded exclusion — not lite-eligible)

## Phase 2 — Design

### Gate 1 clearance
Matrix + AC filled; 4 ASSUMED confirmed on standing approval → **D** (empty-delta guard), **A** (no anchor merge-gate; operator re-measure = follow-up + recorded coverage-gap exclusion), **B** (no schema; general small-delta scoping = named follow-up), **C** (036/053 verdict-only).

### Approach
**One guard, no schema.** In `incremental_update`, gate the late writers on a non-empty delta:
```
if to_parse or removed:
    _count_late_writes(counts, config, store, rules, phase_times=phase_times)
```
On a true no-op (`to_parse == []` and `removed == 0`) the enrichment + resolver passes are skipped — their output is already in the store and is idempotent (two field no-ops agreed at 6,071; `resolve_edges` re-derives the same siblings), so skipping is **state-equivalent**. This simultaneously:
- **A (floor):** removes the full-graph `resolve_edges`/`apply_indirection_rules` scan that is the ~56 s no-op cost → no-op floor = collect + git-diff + hashing.
- **B (number):** `counts` stays `{parsed:0, nodes:0, edges:0}` → `wrote.edges == 0` on a no-op (the ticket's "zero" branch), honestly (no work done).
`full_build` is untouched (it always parses the whole tree — never a no-op). `code-atlas-refresh` (053) inherits the cheaper no-op with no change on its side.

**Profile (AC1):** `execute` runs `scripts/profile_incremental.py` (052) on a **synthetic** index (fake adapter, a few hundred files) to record the **pre-change** per-phase no-op breakdown — evidence that `resolve` dominates a no-op — since the anchor-repo absolute seconds are the operator's (recorded exclusion, ASSUMED-A).

### Rejected alternatives
- **Delta-scope `resolve_edges` for all incrementals (persist resolved-state)** — addresses the small-nonempty-delta cost too (4 files → 57 s), but needs new schema/state and anchor measurement to justify (Candidate 3). Out of scope: the ticket's Goal is the **no-op**; recorded as a named follow-up.
- **Rename `wrote` into delta vs re-derived groups (B-only)** — leaves the ~56 s the agent waits on untouched; the number and the floor share one cause, so fix both. Rejected.
- **Guard on `counts["edges"] == 0` instead of the delta** — circular (the count is what we're fixing) and wouldn't cut the cost (the scan already ran). Rejected for the delta condition.

### Assumptions
- `to_parse` and `removed` are both in scope at the `_count_late_writes` call site (function-local) — **verified** (`indexer.py:196` `removed`, `:215` `to_parse`, `:234` call).
- The late writers are idempotent on an unchanged graph, so skipping on an empty delta is state-equivalent — **verified**: `resolve_edges` iterates the unresolved set and two field no-ops agree at 6,071 (no accumulation); `apply_indirection_rules` re-derives bookmarks already present. A completed prior build always leaves the store fully resolved (R4).
- When `removed > 0` (files reconciled away) the writers must still run to clear siblings into departed qnames — **preserved** (guard runs on `removed`).
- No existing test asserts a no-op incremental's edge count — **verified** (all `incremental_update` test call sites pass a non-empty `changed`: `test_incremental.py:144,223,265,299,348`).
- The fake adapter produces resolver siblings (`dep/name_*` short-name `run` multi-match) so a no-op payload test bites pre-change — **verified** (`fake_adapter.py:97-134`).
No `novel-untested` third-party/runtime assumption. The idempotence assumption is de-risked by the spy proving test (fails if the writers are still run) plus the positive test (fails if they are wrongly skipped when there IS a delta).

### Smallest change-list
| Change | File/area | Blast radius | Ph2 covered by | k/N |
|--------|-----------|--------------|----------------|-----|
| Guard the late writers on a non-empty delta | `indexer.py:234` (`incremental_update`) | full_build untouched (own call site `:137`); `code-atlas-refresh` inherits cheaper no-op; no test asserts a no-op edge count today | R2,R3,G1,C1,C3 | — |
| Proving + payload + positive tests | `tests/test_noop_incremental.py` (new) | none (new file) | AC2,R3,R5,C1,C3 | — |
| Pre-change synthetic no-op profile (run `scripts/profile_incremental.py`) recorded | working doc | none (measurement) | R1,AC1 | — |
| PLAN §14 no-op short-circuit note | `docs/PLAN.md` (build tool / incremental) | none identified | R2,R3 | — |
| 036/053 verdict + floor before/after + operator follow-up + coverage-gap exclusion | working doc | none | R4,AC1,AC3,AC4 | 1/2, 2/2 (hooks) |

**Test blast-radius (mechanical):** grep of `incremental_update(` across `tests/` → 5 call sites (`test_incremental.py:144,223,265,299,348`), **all with a non-empty `changed`** → unaffected by the empty-delta guard. `_count_late_writes` has no direct test caller. `full_build`'s late-writers path (`:137`) is untouched. No golden/snapshot asserts a no-op payload. No producer/consumer disturbed.

### Rule compliance
- **R4** (determinism) — the guard is deterministic; two no-ops both skip → identical `edges:0` payload. ✅
- **§060/§051** — the change is **within `wrote`** (its `edges` becomes an honest 0 on a no-op); `graph` = `store.counts()` is untouched. ✅
- **R1.2/YAGNI** — a ~3-line guard, no schema, no framework, no new abstraction. ✅
- **§068 anti-pattern / correctness constraint** — skips **only** when the delta is empty (output already in the store); never skips work with a real delta (the positive test pins this). ✅

### Verification plan (per-AC, layer-matched)
| AC | risk layer | proof artifact | layer-match? |
|----|-----------|----------------|--------------|
| AC1 (phase profile of a no-op, current) | documentation + runtime | recorded synthetic pre-change per-phase profile (`scripts/profile_incremental.py`) + code-identified dominant phase; anchor seconds = coverage-gap exclusion (operator) | ✅ |
| AC2 (no-op reports zero delta; test pins) | integration (full build → incremental → store → resolver) | integration test: no-op `report.edges/nodes/parsed == 0` + writers not re-run | ✅ |
| AC3 (floor figure after, before beside) | documentation | before = field 56.1/57.4 s; after = collect+diff+hash (writers eliminated on no-op); seconds operator-confirmed (exclusion) | ✅ |
| AC4 (036/053 verdict) | documentation | written verdict (036 already proportional; 053 no-op cheap, background-spawn unchanged) | ✅ |
| C1/R4 (two no-ops identical) | integration | test asserts a second no-op equals the first | ✅ |
| C3 (don't over-skip) | integration | positive test: a real change re-runs the writers | ✅ |

No ❌. **Coverage-gap exclusion (human-approved via standing delegation):** the *absolute anchor-repo seconds* for AC1/AC3 — no anchor monorepo this session (C4); verified by the operator re-running `scripts/profile_incremental.py` on the anchor as a follow-up. `TRACK: backend` → no surfaces.

### Proving test
`tests/test_noop_incremental.py::test_a_noop_incremental_does_not_rerun_the_late_writers` — full-build a fixture, then `incremental_update(config, store, [])` (empty delta), with spies on `indexer.resolve_edges` and `indexer.apply_indirection_rules`; assert **neither is called** and `report.edges == report.nodes == report.parsed == 0`. **Fails pre-change** (both are called; `report.edges` = re-derived siblings > 0), **passes post-change**.
Invocation: `scripts/docker-test.sh pytest -q tests/test_noop_incremental.py` (build uses `fcntl`, Docker per AGENTS.md).

### Rollback + porting
Rollback: revert the one guard in `indexer.py`; delete the new test; revert the PLAN line + working-doc records. No schema/data. Single repo (`app`); no porting.

### SCOPE
`SCOPE: M` — unchanged from analysis. A ~3-line guard + one new test file + docs/profile/verdict. Branch type `fix` fits (a cost/correctness defect in the no-op payload). No tier crossing; the general small-delta resolver-scoping is explicitly a **named follow-up**, not absorbed. No outgrew-its-ticket nudge.

## Phase 3 — Execute

Branch `fix/080-noop-incremental-cost-and-uninterpretable-writes`. Implemented the approved change list.

### Verification sweep
- **Axis 1 (file set):** diff = `code_atlas/indexer.py` (the guard), `docs/PLAN.md` §8.3 (no-op short-circuit note), `docs/tasks/080*` (working doc), `tests/test_noop_incremental.py` (new). All inside the approved list; no file outside; no untouched-line reformatting; each hunk maps to a matrix row.

```
$ git --no-pager diff --stat   (+ untracked tests/test_noop_incremental.py)
 code_atlas/indexer.py |  6 +-
 docs/PLAN.md          |  ... (§8.3 no-op note)
```

- **Axis 2 (design conformance):**
  - Guard the late writers on a non-empty delta — `implemented-as-approved` (`indexer.py:234-238`).
  - PLAN §8.3 no-op note — `implemented-as-approved`.
  - Tests (proving + determinism + positive) — `implemented-as-approved`.
  - **DEVIATION (recorded):** the approved "execute runs `scripts/profile_incremental.py` on a synthetic index to record the pre-change no-op phase breakdown (AC1)" bullet was **implemented differently** — replaced by the proving test's empirical evidence that the dominant phase does **zero work** on a no-op (`resolve_edges`/`apply_indirection_rules` = 0 calls) plus the code identification. Rationale: the guard is applied, so a post-change synthetic profile shows resolve=0 (skipped) rather than the before-dominance; reverting to profile is churn; and a synthetic index can't reproduce the anchor's 56 s anyway. The proving test is stronger, non-churny "after" evidence. The authoritative anchor before/after seconds remain the operator's follow-up (coverage-gap exclusion). Traced to AC1/AC3; surfaced here for review.

### Blast-radius miss + correction (recorded)
The Gate-2 mechanical trace grepped `incremental_update(` and missed **`tests/test_profile_incremental.py::test_two_noops_leave_identical_counts`** (052), which calls `incremental_update(config, store, [], phase_times=…)` and asserts a no-op records **every** `INCREMENTAL_PHASES`. The first full-gate run caught it (1 failed). This is an **intentional behaviour change** (a no-op no longer runs the enrichment/resolve *work*), not a defect — but rather than weaken the 052 assertion, the guard now **records the two skipped phases as ~0.0** (`indexer.py` else-branch), keeping the phase inventory complete AND making the cut *visible* in the profile (enrichment=0.0, resolve=0.0) — which directly serves AC1 ("make it visible … rather than a silent 56 seconds"). No 052 test edited; the guard change absorbs it.

### Test results (Docker — Windows `pytest` red via `fcntl`, per AGENTS.md)
```
$ scripts/docker-test.sh pytest -q -k "noop_incremental or test_incremental or build_report or indirection or staleness or vendor_stub or resolver"
90 passed, 1050 deselected in 19.23s
```
Proving test `test_a_noop_incremental_does_not_rerun_the_late_writers` passed (writers 0 calls; report zero-delta); determinism + positive tests passed. Full CI gate below.

### Proven by
- **AC1 (profile)** — root cause code-identified (`_count_late_writes` → full-graph `resolve_edges`/`apply_indirection_rules`, `indexer.py:247-267`); field before = 56.1/57.4 s; after = the dominant phase does 0 work on a no-op (proving test). Anchor absolute seconds = coverage-gap exclusion (operator re-runs `scripts/profile_incremental.py`).
- **AC2 (zero delta, test pins)** — `test_a_noop_incremental_does_not_rerun_the_late_writers` (`report.edges/nodes/parsed/files == 0`) + `test_two_consecutive_noops_are_identical_and_zero`.
- **AC3 (floor figure, before beside after)** — before = field 56.1/57.4 s; after = collect+diff+hash (late writers eliminated on a no-op); seconds operator-confirmed (exclusion).
- **AC4 (036/053 verdict)** — recorded below.
- **C3 (no over-skip)** — `test_a_real_delta_still_runs_the_late_writers`.

### 036/053 verdict (AC4)
- **036 `code-atlas-poke`** — already proportional: it uses `reparse_file` → `resolve_edges(file_path=…)` (file-scoped), never the full-graph no-op path. Usable as designed; the floor never applied to it.
- **053 `code-atlas-refresh`** — runs `build_or_update_index(full=false)` → the incremental path → inherited the floor. With the no-op short-circuit a no-op refresh now costs only collect+diff+hash. Usable as designed; **background-spawn is unchanged** — switching it inline is a separate follow-up (ASSUMED-C), not this ticket.

### Coverage-gap exclusion (human-approved via standing delegation)
The **absolute anchor-repo seconds** for AC1/AC3 (before ≈ 56 s is the field's; after ≈ collect+diff+hash) — no anchor monorepo this session. Confirmed by the operator re-running `scripts/profile_incremental.py --root <anchor>` as a follow-up. Not a merge gate.

### Named follow-up (scope boundary, ASSUMED-B)
General small-delta resolver cost (e.g. 4 files → ~57 s): a nonempty delta still runs a full-graph `resolve_edges`. Making that proportional needs delta-scoped resolver state (a schema change) + anchor measurement — a separate ticket, not absorbed here.

### Full CI gate (delta-green)
```
$ scripts/docker-test.sh   # ruff + mypy + pytest
1140 passed in 67.37s
```
Baseline 95 scoped -> green; +3 tests from 080; the 052 profiler test passes (phase inventory kept complete). Delta-green proven.

## Phase 4 — Review
**WAIVED** per run argument "with skipped review". No reviewer/challenger dispatch; no `Reviewed at` marker. One blast-radius miss (052 profiler test) was caught by the full gate and absorbed by the guard change (recorded above); no scope growth (SCOPE M holds); the general small-delta scoping stays a named follow-up.

## Phase 5 — Finalise
Outward actions (maintainer standing approval + run arg "commit + push + open PR"): commit (code+test, docs) -> push branch -> open PR from template.
