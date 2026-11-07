---
id: 440
slug: compute-sandbox-and-contract
title: "`compute`: exact answers over the whole graph — private views, sandbox, template contract, evidence levels"
phase: 2
milestone: "0.11 Verify & Compute"
status: in-progress
depends_on: [428, 434]
---

## Why this exists

Roadmap R3 (0.11). A model cannot count, group or prove an absence over a codebase from inside its
context window. On the anchor (survey 2026-11-07), **8 of 10 aggregate questions** were unanswerable
or costly through the current tools — "procedures with no PHP referrer" cost ~230k tokens by
navigation against ~25 computed. A prototype over the anchor's 1.49 GB index answered in 0.01–2.05 s
warm and refused 6 of 6 safety probes. Absences need care: PHP → SQL linkage there is **0%
RESOLVED**, so "nothing references X" is often "nothing *resolved* references X".

## Scope

1. **Private view layer** (`v_file`, `v_symbol`, `v_edge`) used only by templates — not a public API,
   free to change. It lives in `store.py`, the only file that touches SQLite (R1.4).
2. **Sandbox**, as prototyped: `mode=ro` + `PRAGMA query_only`, an authorizer allowing
   SELECT / READ / FUNCTION only, a progress-handler deadline (3 s default), a row cap (200 default).
   **Callers never supply SQL** — only a template id and typed params.
3. **Template contract:** `id`, a one-line question, typed parameters as a closed schema (428), an SQL
   body over the views, a **data-driven `caveat`** (e.g. the share of rows backed by HEURISTIC or
   unlinked evidence), `total_count`, `truncated`, and an explained-empty `reason`.
4. **Evidence levels for absence questions (mandatory):** `no_edge_no_mention` (no edge and the name
   appears nowhere in indexed text — a strong candidate) vs `no_edge_but_mentioned` (no edge, but the
   name appears in literals or other files — **unknown, never dead**, R5.6). The mention check reuses
   the FTS index or a time-capped bounded grep, counted in the payload.
5. **Surfaces:** MCP tool `compute` (`template`, `params`, `limit`; no template lists the catalogue:
   ids and questions) and `code-atlas query compute --args '{…}'`. Read-only annotations; description
   within 434's budget; the pinned tool count moves.
6. One proving template ships here (e.g. `tier_mix`) so the contract is exercised end to end; the
   catalogue is 441. Overlap with `find_orphans` is stated in the tool description, not duplicated.

## Acceptance

1. Safety: a write, `ATTACH`, `load_extension` and a runaway recursive CTE are each refused or
   interrupted, with a reason — never a partial answer presented as complete.
2. An unknown template or an extra param fails loud through the closed schema.
3. Every computed row carries a tier or caveat; an empty result names why it is empty.
4. The absence split is asserted on a fixture where one target has a string mention and one has none.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 440 · **work_doc_mode:** embed · **Current phase:** 5 finalise — the PR is open; merging is the maintainer's.
- `TRACK: backend` · Run mode: `autorun 437 - 438 - 440`, third — `REVIEWER: ON` · `CHALLENGER: ON` · `cost_tier: standard`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/440-compute-sandbox` from `main` at `63991c1b` (independent of 437/438). Contract
  `.mango/run-contract-440.txt` (mango 1.21.0), written **after** the code had started in the worktree but before any
  commit or push; RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 0 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 5 unresolved surfaced | 3 want-decision asked | 2 how-decision resolved+cited | 3 ASSUMED | skip: no`

`store.py` (R1.4), 428's `close_schema`, 434's budgets (`tests/test_tool_surface_budget.py`), `find_orphans` and
`nodes_fts` (trigram) resolve. Recalled by area: 428 (closed schemas), 434 (description caps — ~34 chars of headroom).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where template SQL lives | how | the bodies sit in `store.py` (`COMPUTE_QUERIES`), the only file that touches SQLite (R1.4); `tools/compute.py` holds the contract |
| H2 | temp views on a read-only file | how | created on the `mode=ro` connection *before* `PRAGMA query_only` (probed: after it, a temp view is a refused write) |
| W1 | 434's caps had ~34 chars left | want | **ASSUMED:** each added tool brings its own share — description total `+600`, surface `+1,100` |
| W2 | scope 6 ships "one proving template" | want | **ASSUMED:** two — `tier_mix`, and `no_referrer`, because AC4 asserts an absence and `tier_mix` has none |
| W3 | scope 4 names two evidence levels | want | **ASSUMED:** a third, `mention_unchecked`, when the grep is cut by its deadline or cannot run — R5.6 forbids calling that "no mention" |
| W4 | scope 2: the authorizer allows "SELECT / READ / FUNCTION only" | want | **ASSUMED:** also `RECURSIVE` (so a runaway recursive CTE is *interrupted* by the deadline, as AC1 asks, not refused at parse) and the FTS index's own bare `PRAGMA data_version` read (FTS5 issues it; refusing it refuses every text lookup) |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=2 R=6 G=1 AC=4`
`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/19 touched files under UI paths`
`SCOPE: L`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "A model cannot count, group or prove an absence" | exact answers from templates | ⚠ |
| C1 | Scope 1 | "the only file that touches SQLite (R1.4)" | H1 | ⚠ |
| C2 | Scope 2 | "Callers never supply SQL" | template id + typed params only | ⚠ |
| R1–R6 | Scope 1–6 | views · sandbox · contract · evidence · surfaces · proving template | as written, W1–W3 | ⚠ |
| AC1–AC4 | Acc 1–4 | as written | `tests/test_compute.py` | ⚠ |

`BASELINE: green — tests/test_tool_manifest.py, test_tool_surface.py, test_tool_surface_budget.py, test_untrusted_output.py, test_routing_surface.py on main at 63991c1b: green before the change`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.4 SQL only in store.py · §5 (change-type) ✅ R5.6 an absence never "dead", a cut check never "no mention" · §6 (change-type) ✅ R6.5 seen red, R6.7 the new tool joins every walk · §7 (change-type) ✅ R7.2, R7.5, R7.6`

## Phase 2 — design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**Approach.** `store.py`: three temp views, `ComputeSandbox` (`mode=ro`, `query_only`, authorizer: SELECT / READ /
FUNCTION from a short list / RECURSIVE, plus the FTS index's own `PRAGMA data_version` read; progress-handler deadline
3 s; row cap 200), `COMPUTE_QUERIES`. `gitutil.word_sites`: one time-capped `git grep -F -w -o` for a page's names.
`tools/compute.py`: the contract, `tier_mix`, `no_referrer`, the catalogue. Wiring: `main.TOOL_NAMES`, the routing map,
`untrusted.FIELDS`, the manifest, the pinned counts, TOOLS / README / PLAN / CHANGELOG.
**Rejected:** a free-SQL escape hatch (scope 2); a literal scan of every edge's string arguments in SQL — on the anchor
it hit the 3 s deadline every time, leaving every absence unchecked.
**Proving test:** `tests/test_compute.py`.

- E1 — W4, two authorizer allowances beyond scope 2's words; approved under the handover, not at a gate; **expiry:**
  the maintainer ratifies or rejects W4 on the PR before merge.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

## Phase 3 — execute

Main loop, no `implementer` (`736b6f7a`). **R6.5:** on `main` the test cannot import `compute`; the AC4 fixture was seen
red twice while building — the file's own `CONTAINS` edge counted as a mention, and the FTS read was refused until its
`data_version` pragma was allowed.
**Anchor (counts only, a copy of the index):** `tier_mix` 1.5 s warm (28 rows); `no_referrer` Function 3.1 s (total
7,011; the 50 returned all mentioned), Method 3.2 s (total 7,372; 41 mentioned, 9 unchecked — the grep's deadline), Class
0.4 s (total 713; 18 strong candidates, 32 mentioned).

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. Review step: mango `reviewer` (Sonnet), round 1, at `f64d2172`.

- **`reviewer` round 1** (67,483 tokens): CHANGES REQUESTED → conditional LGTM on 1–2. Sandbox sound: `mode=ro` +
  `query_only` + hardened `_connect`, default-deny authorizer, bound parameters only, the FTS phrase escaped.
  - **1, taken:** the grep arm and `mention_unchecked` gained tests (parse, a flag-like word, the deadline, the
    monkeypatched cut).
  - **2, taken:** occurrences are counted, so `foo(foo)` on the definition line is a mention; a name holding a line
    break is never grepped and stays unchecked. **Minors taken:** a root prefix is no filter.
- **`challenger` round 1** (70,647 tokens, ticket-blind): 11 met · 3 not met · 1 can't tell. **Taken:** Important 1 —
  the grep missed untracked indexed files (`--untracked` now); params are typed and the catalogue lists each type's
  values; a template names its body by key; non-object params fail loud; a self-call is no referrer; the CLI route and
  the read-only annotation are tested.
- **`challenger` round 2** (verify-only, at `813d93f3`): its final table, transcribed:

`CHALLENGER VERDICT: 16 requirement(s) rebuilt | 15 met | 1 not met | 0 can't tell | 1 not-met covered by a recorded exclusion`

The one not met is row 2, the authorizer's wording — W4, E1. `m + g = 16 = n`: the gate closes, E1 awaiting the
maintainer. **Not taken:** `sqlite_master` stays readable (schema only — callers supply no SQL); `CONTAINS` edges stay in
`tier_mix`'s caveat (true, if noisy).

Verdict: clean (conditional LGTM landed; challenger 15 met + 1 recorded exclusion). `Ph3/4 proven by`: AC1–AC4 →
`tests/test_compute.py` (28).

Reviewed at 813d93f3

## Phase 5 — finalise

**Durable lesson.** 440-C1 `a-deadline-on-a-scan-is-an-answer-only-if-the-scan-ever-fits` (new, type 2).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/440-compute-sandbox`; open its PR against `main`. Deferred: ratify W1–W4; merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 4 review | rule-book `reviewer` | 1 | 67,483 |
| 4 review | ticket-blind `challenger` | 1 | 70,647 |
| 4 review | ticket-blind `challenger` | 2 | 7,416 (resumed: 78,063 cumulative − 70,647) |

`LEDGER TOTAL: 145,546 · top cost driver: 4 review / challenger` — main loop unmeasured.
