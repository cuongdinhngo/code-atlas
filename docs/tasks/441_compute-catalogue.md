---
id: 441
slug: compute-catalogue
title: "`compute`: the first eight templates, each with fixtures for its answer, caveat, empty and truncation"
phase: 2
milestone: "0.11 Verify & Compute"
status: in-progress
depends_on: [440, 437]
---

## Why this exists

Roadmap R3.4 (0.11). 440 ships the sandbox and the contract; this ships the questions the anchor's
survey found unanswerable or costly today (8 of 10), so the validation run (442) can measure whether
an agent reaches for `compute` unprompted.

## Scope

| Template | Question | Depends on |
|---|---|---|
| `unreferenced_objects` | Objects of kind K with no inbound edges from language L, split by evidence level | 440's absence split |
| `tier_mix` | Edge tier mix per edge kind × language pair | — |
| `calls_by_module` | Calls into a target set (qname or kind pattern), grouped by module | — |
| `untested_classes` | Classes with no edge from test files, per module | test-path config |
| `resolved_share` | RESOLVED share of CALLS per module | — |
| `includes_by_dir` | `include` / `require` counts per top directory | — |
| `multi_defined` | Objects defined more than once, with the live one | 437 |
| `variant_pairs` | Name-pattern pairs from config with one-sided use | config rule; the core only matches patterns |

Every pattern a template takes comes from params or a non-command toml key (430), never a repo's
names baked in (R2). No template branches on language (R1.1) — a language is a param value.

## Acceptance

1. Per template, fixture tests for: the answer, the caveat, an empty result with its reason, and
   truncation (`total_count` truthful when `truncated`).
2. `multi_defined` with no 437 order rule names that the live definition is unknown, never guesses.
3. Anchor (privacy rules in 442): p95 ≤ 3 s per template warm; the cold-cache timing recorded too.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 441 · **work_doc_mode:** embed · **Current phase:** 5 finalise.
- `TRACK: backend` · Run mode: `autorun 439 - 441`, second — `REVIEWER: OFF` (waived: "with skipped reviewer") ·
  `CHALLENGER: ON` · `cost_tier: standard`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/441-compute-catalogue` from `main` at `e7896fa1`, built in a worktree while 439's gate held the main
  checkout. Contract `.mango/run-contract-441.txt` (mango 1.21.0), written before any code; RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 0 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 5 want-decision asked | 2 how-decision resolved+cited | 5 ASSUMED | skip: no`

440's `ComputeSandbox` / `COMPUTE_QUERIES`, 437's `definition_states` and `definition_order` meta, 114's module table
(`impact_modules`), the `is_test` role (262) and `INCLUDES` resolve. Ambiguous: "test-path config" — no such knob
exists; the test role is the adapter's or the path convention's. Recalled by area: 440-C1 (measure a capped check on
the real corpus), 437-C1.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | "per module" | how | the one business-module table (PLAN §1) via `impact_modules.module_owners`, unassigned files in `unassigned` — SQL aggregates per file, the tool rolls up |
| H2 | a row's language | how | its own, else its file's (the store's `_NODE_LANGUAGE` rule) — the private views now say so |
| W1 | `untested_classes` "test-path config" | want | **ASSUMED:** the indexed `is_test` role (adapter or path convention); a test reaching a member reaches its container; no test symbol → `no_test_symbol_indexed` |
| W2 | `variant_pairs` "pairs from config" | want | **ASSUMED:** params `left`/`right` (one `*` each), else toml `variant_pairs`; pairs share a container; "used" = an inbound edge |
| W3 | `tier_mix` exists (440) and gains the language pair | want | **ASSUMED:** rows gain `source_language` / `target_language` (440 is unreleased); `target_language` null when unlinked |
| W4 | `calls_by_module` "qname or kind pattern" | want | **ASSUMED:** `target` a GLOB over qnames, or `target_kind`; one of them required; `edge_kind` defaults to CALLS |
| W5 | 434's surface cap had no room for seven more template ids | want | **ASSUMED:** `SURFACE_CAP` +130 chars for the enum, not a shorter description |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=2 R=8 G=1 AC=3`
`CLARIFICATION: 7 raised | 7 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/13 touched files under UI paths`
`SCOPE: L`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "ships the questions the anchor's survey found unanswerable or costly" | eight templates | ⚠ |
| C1 | Scope | "never a repo's names baked in (R2)" | patterns from params / toml only | ⚠ |
| C2 | Scope | "No template branches on language (R1.1)" | a language is a bound value | ⚠ |
| R1–R8 | Scope table | the eight templates | as written, W1–W5 | ⚠ |
| AC1–AC3 | Acc 1–3 | as written | `tests/test_compute_catalogue.py`; AC3 the anchor report | ⚠ |

`BASELINE: green — tests/test_compute.py, test_config.py, test_tool_surface_budget.py on main at e7896fa1: 107 passed`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 a language is a param value, R1.4 SQL only in store.py · §2 (change-type) ✅ R2 no repo pattern · §5 (change-type) ✅ R5.6 an undecided live definition is unknown · §7 (change-type) ✅ R7.2, R7.5, R7.6`

## Phase 2 — design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**Approach.** `store.py`: the bodies (per-file aggregates, the variant self-join on `idx_nodes_name`, `meta.value`),
`glob` added to the sandbox's functions, the views' language from the file. `tools/compute.py`: typed params
(`language`, `qname_glob`, `name_pattern`), the eight runners, `_whole` (an aggregate read whole, refused past
200,000 rows) and `_rollup`. `config.py`: `variant_pairs` and `variant_pattern`. Wiring: untrusted fields, manifest,
pins, TOOLS, CHANGELOG.
**Rejected:** a correlated per-edge target-language lookup (anchor: past 3 s); module names computed in SQL (the table
is Python's, one notion).
**Proving test:** `tests/test_compute_catalogue.py`.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

## Phase 3 — execute

Main loop, no `implementer` (`34de5257`). **R6.5:** on `main` the catalogue has two templates, so every new test is
red. **Anchor (counts only, a copy of the index; `~/code-atlas-review/441-anchor.md`):** first pass, `tier_mix` and
`calls_by_module` hit the 3 s deadline; after one grouped pass and an `IN` set, warm p95 ≤ 2.08 s for all eight
(`tier_mix` 2.08, `untested_classes` 1.92, `unreferenced_objects` 1.41, the rest ≤ 0.61); cold within 0.05 s of warm.

## Phase 4 — review

`REVIEWER: OFF` (waived by the run's args — no rule-book seat looked) · `CHALLENGER: ON`. Review step: the ticket-blind
`challenger` alone, at `34de5257`.

- **`challenger` round 1** (84,365 tokens): 13 met · 0 not met · 1 can't tell (AC3 — the anchor is private).
  **Taken:** F4 — `untested_classes` saw only edges whose source symbol is a test; every edge a test file makes now
  counts (a module-level `NEW`, seen red on `34de5257`). F1 — a language's file list past the cap is refused, never
  cut. F2, F3 — the caveats name test copies, the prefix and a null `target_language`. **Not taken:** F5 (the anchor
  run settles it: below), F6 (a GLOB is a bound value under the deadline), F7 (`no_referrer` stays; the views'
  language fallback is H2).
- **`challenger` round 2** (verify-only, at `f07f95a0`): its final line, transcribed:

`CHALLENGER VERDICT: 14 requirement(s) rebuilt | 13 met | 0 not met | 1 can't tell | 0 not-met covered by a recorded exclusion`

The can't-tell is AC3, an acceptance check off the diff: the anchor timings live in
`~/code-atlas-review/441-anchor.md` (warm p95 ≤ 2.07 s, all eight). `m + g = 13 ≠ 14 = n`: **the arithmetic gate does
not close** — the PR opens as a DRAFT and DISCLOSURE says why.

Gate-driven after round 2: the full suite found two core rules the targeted runs missed — one contract word per
statement (R3.2) and no language named in the core (R1.1, a param's example text). Round 3 (`c1178a9b`) verified
that range and caught one more: the rewritten param line ran past 100 columns (E501), wrapped in `196ce137`; round 4
verified the wrap. Both: 13 met · 1 can't tell (AC3), nothing new.

Reviewed at 196ce137

`Ph3/4 proven by`: AC1–AC2 → `tests/test_compute_catalogue.py` (45); AC3 → the anchor report (counts and timings only).

## Phase 5 — finalise

**Durable lesson.** 441-C1 `a-page-and-its-total-each-run-the-body` (new, type 2).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Ran at 196ce137

```
$ scripts/gate.sh
26 passed · 0 failed · 0 skipped
GATE GREEN — all 26 checks passed
```

A first gate run at `c1178a9b` was stopped once round 3 found the E501 it would fail on.

### Outward actions

Under the handover: push `feat/441-compute-catalogue`; open its PR against `main` (draft — the review gate's
arithmetic does not close on an off-diff AC). Deferred: ratify W1–W5; merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 4 review | ticket-blind `challenger` | 1 | 84,365 |
| 4 review | ticket-blind `challenger` | 2 | 4,196 (resumed: 88,561 cumulative − 84,365) |
| 4 review | ticket-blind `challenger` | 3 | 2,109 (resumed: 90,670 cumulative − 88,561) |
| 4 review | ticket-blind `challenger` | 4 | 837 (resumed: 91,507 cumulative − 90,670) |

`LEDGER TOTAL: 91,507 · top cost driver: 4 review / challenger` — main loop unmeasured.
