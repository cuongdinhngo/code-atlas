---
id: 362
slug: untyped-receiver-and-constructor-calls-unlinked
title: 'A call on a variable assigned from new X() in a view, or a constructor call, links to nothing, so find_callers answers relation_unmodelled'
phase: 2
milestone: Coverage
status: done
depends_on: [258, 336]
---

## Why this exists

This comes from the anchor project's field retro (2026-10-02 → 10-06). In each case below,
`find_callers` returned an empty answer with `relation_unmodelled_for_language`, and the callers
had to come from Grep.

- F1 (1 PR): `getStartDate` is called on `$editor`, which an included view assigns with
  `new X(...)`. 14 view and report call sites were invisible.
- F2 (1 PR): `find_callers` on `Widget::__construct`. Each `new Widget(` site is a `NEW` edge to
  the class, not a caller of the constructor, so `arg_is` could not narrow the call sites by their
  `$type` literal.
- F3 (2 PRs): one regional copy's `Widget::validate`, called via `$this->` in its own class, is
  unlinked, while its twin in the other regional tree resolves.
- F4 (1 PR): `ReportModel::heading` returned an empty answer with `authoritative: false` and no
  candidates.

## Scope

1. Infer local types for `$x = new X(...)` at file or top-level scope (an included view), so that
   `$x->m()` resolves at `HEURISTIC`.
2. `find_callers` on `X::__construct` reads the `NEW` edges onto `X` as its callers, with their
   argument shapes, so `arg_position` and `arg_is` apply.
3. Before changing the resolver, measure why a same-class `$this->m()` resolves for one twin and
   not the other (F3). Then fix the cause, or file it.
4. Where the answer is still empty, the 258 proximity expansion lists the unlinked same-name sites
   instead of a bare zero.

## Acceptance criteria

- **AC1:** In a fixture view, `$o = new Foo(); $o->bar();` gives `find_callers Foo::bar` one
  `HEURISTIC` row.
- **AC2:** `find_callers Foo::__construct` returns each `new Foo(...)` site, and `arg_is` can
  filter them.
- **AC3:** A fixture reproduces the F3 asymmetry, and the asymmetry is either resolved or
  documented with its cause.
- **AC4:** No existing `RESOLVED` edge changes tier.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 362 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews and merges the PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`, batch 365 → 366 → 361 → 362 → 364 → 363;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `feat/362-untyped-receiver-and-constructor-calls-unlinked` from `main` (`fb256ec5`). Contract `.mango/run-contract-362.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 6 want-decision asked | 6 how-decision resolved+cited | 6 ASSUMED | skip: no`

**Premise.** `find_callers` `arg_position`/`arg_is` (049), 258's proximity expansion
(`_proximity_unresolved_callers`), the `NEW` edge kind, 336's local types (`TypeTable.php`) — all resolve.

**Recall (by handle — a shared vocabulary is extended).** `343-C2` `formatter-rewrites-untouched-lines`.

**Measured on `main` before design** (real PHP adapter):
1. `$o = new Foo(); $o->bar();` at a file's top level already emits `CALLS \Foo::bar` — AC1 holds today.
2. The field case is cross-file: `setup.php` does `$editor = new Editor()`, `report.php` includes it
   and calls `$editor->getStartDate()` — a bare `CALLS getStartDate`. With two classes declaring
   the method it stays unlinked and `find_callers` answers `no_matches`: 258 qualifies a site only by
   shared directory.
3. `find_callers \FormBuilder::__construct` → `no_matches`; the core has no notion of a constructor.
4. Twin asymmetry reproduced (AC3): `$this->validate()` onto a declared `Validate()` emits a
   RESOLVED-tier edge the case-sensitive resolver leaves unlinked, while a twin spelling it alike
   links. Trait/parent/namespace variants all resolve.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 49,108 tokens) surfaced X1–X12. Want-decisions
handed back by the handover → **ASSUMED (awaiting ratification)**.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | how the core learns a constructor | want | **ASSUMED:** `Method.extra.constructor: true`, set by the adapter from its language spec (PHP `__construct`, any case). Read by `find_callers` only. No capability, so no handshake change |
| X2 | contract bump | how | none — the `STUB_FLAG`/`RULE_FLAG`/`UNMODELLED_RESOLUTION` precedent (`contract.py:266-276`): a new `extra` key is "Not a contract bump"; R3.1 binds vocabulary and qname |
| X3 | what counts as a constructor's caller | want | **ASSUMED:** `NEW` onto its class plus direct calls (`parent::__construct`), tiers as stored; a class with no declared constructor has no such node, so nothing changes for it |
| X4 | `arg_position`/`arg_is` on `NEW` sites | how | reused: `NEW` edges carry `args`; every census query takes the same extra target |
| X5 | include proximity: direction, depth, condition | want | **ASSUMED:** one include either way, and only toward a file whose own top level does `new` of the subject's class — a variable typed there is in scope across that include (PHP include semantics) |
| X6 | where the reachability query lives | how | `store.py` (R1.4): `files_constructing_at_top_level`, `include_neighbours` |
| X7 | adapter cross-file typing vs query-time candidates | want | **ASSUMED:** query-time candidates only. Typing `$editor` across files would make a file's rows depend on another file, breaking R4.2's incremental equivalence |
| X8 | fix or document F3 | want | **ASSUMED: documented** with its cause (AC3 allows it); the fix needs a per-language case rule the resolver can read — filed to Follow-ups |
| X9 | AC4 | how | the resolver is untouched (`git diff main -- code_atlas/resolver.py` is empty); new answers are query-time candidates (`proximity_candidates`, never `ok`) or already-stored `NEW` rows |
| X10 | F4 (`ReportModel::heading`) | how | no scope item or AC names it; out of scope |
| X11 | Scope 4 | how | the listing exists (258); the gap is the qualifier — X5 |
| X12 | docs / release | want | **ASSUMED:** no release: no contract or schema version moves. TOOLS.md, the ADAPTER_PLAYBOOK optional-field table and BACKLOG Follow-ups carry it |

## Phase 1 — analysis

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=4 G=1 AC=4`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/8 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

`main` at `fb256ec5` has the tree of `4e05c246`, on which `scripts/gate.sh` printed
`GATE GREEN — all 21 checks passed`. Ran at 4e05c246.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "the callers had to come from Grep" | the graph offers them | ✅ |
| C1 | AC4 | "No existing RESOLVED edge changes tier" | resolver untouched | ✅ |
| R1 | Scope 1 | `$x = new X()` at top level → `$x->m()` resolves | same file: holds today (pinned); cross-file: X5/X7 | ✅ |
| R2 | Scope 2 | `X::__construct` reads `NEW` onto `X` with args | X1/X3 | ✅ |
| R3 | Scope 3 | measure the twin asymmetry, then fix or file | X8 | ✅ |
| R4 | Scope 4 | proximity lists unlinked same-name sites instead of a zero | X5 | ✅ |
| AC1 | AC | fixture view → one row | linked at HEURISTIC in the same file; cross-file as candidates | ✅ |
| AC2 | AC | `find_callers Foo::__construct` → each `new`, `arg_is` filters | | ✅ |
| AC3 | AC | asymmetry reproduced, resolved or documented with cause | documented | ✅ |
| AC4 | AC | no RESOLVED edge changes tier | X9 | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `find_callers \Planner::getStartDate` → `ok`, `["views/inline.php"]`; cross-file → `proximity_candidates`, `["reports/daily.php", "views/part.php"]` | the ticket's literal AC1 passes on `main` too; the cross-file case is what was red |
| AC2 | yes — sources `["\Child::__construct", "forms/make.php"]`; `arg_is=string` 2, `null` 0 | |
| AC3 | yes — `\AusWidget::validate` has its caller; `\NzWidget::Validate` 0; the unlinked row is `("\NzWidget::validate", None)` | |
| AC4 | yes — `git diff main..HEAD -- code_atlas/resolver.py` empty; the gate's resolver/tier suites pass unedited | |

### Gap analysis (enhancement)

- **Now.** `_proximity_qualifies` reads directories only (`find_callers.py`); `_callers` reads one target.
- **Target.** Include-qualified candidates; a flagged constructor reads its class's `NEW` too.

### Blast radius

- Store inbound queries gain `also_targets` (default empty → unchanged SQL text but for an
  `edges.` qualifier on `tier_census_by_target`): `edges_by_target`, `count_edges_by_target`,
  `call_lines_by_source`, `inbound_test_rows`, `count_edges_without_args`, `tier_census_by_target`.
- PHP adapter: one `extra` key on constructor Method nodes; no edge changes; no golden files exist.
- Neighbouring suites (63 files incl. `tests/contract`): `1555 passed`.

### Rule sections

`RULE SECTIONS: 9 applicable — 9 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the core reads a flag and the include graph, never a language or "__construct" · §R1.4 (change-type) ✅ new SQL lives in store.py · §R1.6 (change-type) ✅ the flag is advertised and never required: no flag, no constructor union · §R2.1 (change-type) ✅ __construct, case-insensitive, is the PHP spec's constructor · §R3.1 (change-type) ✅ no vocabulary or qname change; an extra key, per the contract.py precedent · §R4.2 (change-type) ✅ no row depends on another file; candidates are query-time · §R5.2 (change-type) ✅ include candidates are proximity_candidates, never ok or linked · §R5.5 (change-type) ✅ the census, tier census and unrecorded-args count read the same targets as the page · §R6.6 (change-type) ✅ PHPStan level max clean on the adapter edit`

## Phase 2 — design

### Approach

1. **PHP adapter** — `extra.constructor = true` on `__construct` (any case).
2. **`contract.CONSTRUCTOR_FLAG`**, the one definition site.
3. **Store** — `also_targets` on the six inbound queries; `files_constructing_at_top_level`, `include_neighbours`.
4. **`find_callers`** — `_constructed_class` → `also_targets` through `_callers`, call lines, both
   censuses and the unrecorded-args count; `_include_qualified` widens `_proximity_unresolved_callers`.
5. **Docs** — TOOLS.md, ADAPTER_PLAYBOOK, BACKLOG Follow-ups.

### Rejected alternatives

- **Type `$editor` across files in the adapter** — a file's rows would depend on another file (R4.2).
- **Link a unique bare name at build time** — it already links when unique; the field case is two classes.
- **A handshake capability for constructors** — a handshake key is a contract bump (v13's precedent); the flag is per-node data.
- **Case-insensitive linking now** — needs a per-language case rule; filed (X8).

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | `NEW` edges carry `args` | verified — `arg_is=string` counts 2 of the fixture's `new` sites |
| S2 | an included file's top-level variable is in the includer's scope and vice versa | verified — the PHP language spec (include shares the calling scope) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | constructor flag | `adapters/php/src/Visitor.php` | Method extra only | R2 | 1/1 |
| 2 | flag constant | `code_atlas/contract.py` | — | R2 | 1/1 |
| 3 | inbound targets + include lookups | `code_atlas/store.py` | six inbound queries (default unchanged) | R2, R4 | 1/1 |
| 4 | union + include proximity | `code_atlas/tools/find_callers.py` | find_callers only | R1, R2, R4 | 1/1 |
| 5 | proving tests | `tests/test_untyped_receiver_and_constructor_calls.py` (new) | — | AC1–AC3 | 1/1 |
| 6 | docs | `docs/TOOLS.md`, `docs/ADAPTER_PLAYBOOK.md`, `docs/BACKLOG.md` | doc budgets | R3 | 3/3 |
| 7 | bookkeeping | this file, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced: only the new test file was formatted; the
  edited files had `ruff check` only (`All checks passed!`).

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | real PHP build, `find_callers` | authored | ✅ |
| AC2 | integration | same | authored | ✅ |
| AC3 | integration | same + edge rows | authored | ✅ |
| AC4 | integration | resolver diff empty + gate resolver suites | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_untyped_receiver_and_constructor_calls.py`.

### Rollback

`git revert`; indexes keep the extra key until the next build, which nothing else reads.

## Phase 3 — execute

Commit `f7b3ac71`. **Order deviation:** code before this doc's design text.

**Red first** — the file on `main` in a throwaway worktree (only `CONSTRUCTOR_FLAG` appended so it
imports): `2 failed, 4 passed` — the include candidates and the constructor callers. The flag test
passed there only because the symlinked `vendor/` autoloads this checkout's `Visitor.php`;
`git show main:adapters/php/src/Visitor.php | grep -c "'constructor'"` is `0`. AC1, the
narrowing test and AC3 pass on both trees by design (guards).

On `f7b3ac71` the file gave `7 passed` (superseded by Phase 4's run).

**Sweep.** Axis 1: `git diff --name-only main..HEAD` = items 1–6 exactly; `ruff check`, `mypy`,
PHPStan clean. Axis 2: Approach 1–5 as approved. Neighbouring suites: `1555 passed`.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `f7b3ac71`, 72,547 tokens): 5 met · 1 not met · 3 can't tell.**
The "not met" is Scope 1 read as a *linked* HEURISTIC edge for the included-view case. Dispositions:

1. **F1 (high): the included-view case lands as candidates, not a linked edge.** **Kept, recorded as
   a deviation (P3):** a linked edge would make one file's rows depend on another (R4.2 — an
   incremental would go stale when the included file changes); same-file top-level typing already
   ships (336). Candidates show only on an otherwise empty answer, depth 1, no `arg_is` — 258's
   existing gate, unchanged.
2. **F2 (medium): the subtree spread read only the method.** **Fixed** in `05e45244` (`also_targets`);
   test fails without it (`KeyError: 'result_subtrees'`).
3. **F3 (medium): an inherited constructor misses its subclass's `new` sites.** **Documented** in
   TOOLS.md and BACKLOG. A `__CONSTRUCT` spelling is still found only under that spelling (the F3
   resolver case).
4. **F4 (medium): the twin cause is a fixture finding, not matched to the anchor.** **Recorded** in
   BACKLOG ("a fixture cause, not matched to the field").
5. **F5: a widely included bootstrap that does `new` makes every includer a candidate.** **Left,
   disclosed:** candidates are labelled and ranked; no cap invented.
6. **F6: existing indexes lack the flag until a full rebuild.** **Documented** in TOOLS.md.
7. **F7: tests for depth > 1 and tier/census on the constructor path.** **Left:** the BFS seed and the
   census threading were read; the truncated-page test covers the census path.

Verify-only (main loop — every fix is inside the approved files):

Ran at 05e45244:
```
$ .venv/bin/python -m pytest -q tests/test_untyped_receiver_and_constructor_calls.py
7 passed in 0.35s
```
Neighbouring suites (callers, store, PHP, onboarding, proximity, nav): `971 passed in 66.17s`.

`Ph3/4 proven by`: G1, C1, R1–R4, AC1–AC4 — 10/10 (R1 by candidates, per the recorded deviation).

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 05e45244 — the diff `main..05e45244`. Working doc: `docs/tasks/362_untyped-receiver-and-constructor-calls-unlinked.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `05e45244` only bookkeeping changes — this doc, `docs/TOKEN_LEDGER.md`,
`docs/LESSONS.md` and `docs/BACKLOG.md`, all exempt.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

`362-C1` is type 2 (code), handle `widen-every-query-that-shares-the-page`: when a tool's answer
widens what it targets, every store query behind that answer — rows, count, census, spread — must
take the same widening, or the payload disagrees with itself. The challenger found the one missed
(the subtree spread). First sighting. Per P1, `343-C2` gains 362 (traced).

### Outward actions

1. Push `feat/362-untyped-receiver-and-constructor-calls-unlinked` — pre-authorised.
2. Open the PR against `main` — pre-authorised.

Deferred to the maintainer: the merge; ratifying X1, X3, X5, X7, X8, X12.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 49,108 |
| 2 | review | `challenger`, round 1 | 72,547 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 121,655 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits.
