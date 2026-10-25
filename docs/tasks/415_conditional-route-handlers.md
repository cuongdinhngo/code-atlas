---
id: 415
slug: conditional-route-handlers
title: "A URL a front controller serves through different handlers by region, flag or parameter cannot be declared, so it cannot be traced"
phase: 2
milestone: Coverage
status: done
depends_on: [411]
---

## Why this exists

A consumer's survey, 2026-10-25. In a front controller, one URL is served by different handlers
depending on a region switch, a feature flag or a further request parameter:

```php
if ($action === 'x' && FEATURE_ON) { (Region::isA() ? new XA : new XB)->save(); }
```

A route row holds one target (`routes.py:51-56`), so these pages cannot be declared. 549 endpoints of
the form `?action=X` had no handler in the route table, including the main pages questions are asked
about. The consumer can generate the rows itself, but has nowhere to put the conditions.

## Scope

1. A route row may declare several handlers. Each has a free-form `when` label (for example
   `region=A`, `flag=FEATURE_ON`, `param:save=1`) and an optional `source` (`file:line` of the
   dispatching code). Inline, TSV and JSON sources all accept them.
2. Rows with the same key and distinct `when` labels are one conditional route, not a 411 collision.
   The same key with different targets and no `when` is still a collision.
3. `trace_capability` returns one flow per handler, each carrying its `when` and `source`.
   `impact(routes=…)` includes every handler.
4. Conditions are labels for the reader. Nothing evaluates them.
5. Update the user docs for the routes rule.

Out of scope: an extractor that proposes `(param value → handler)` pairs from `if` chains. It is
language-specific, so it belongs in an adapter (R1.1), and would be its own ticket.

## Acceptance criteria

- **AC1:** A fixture route has two handlers, labelled `region=A` and `region=B`. `trace_capability`
  returns two flows, each with its label and source, and `impact` covers both.
- **AC2:** A single-handler route answers exactly as before.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 415 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W3 and merges #113 after #112. **Revert path:** `git revert` the branch's commits; no contract or schema moved.
- `TRACK: backend` · Run mode: `autorun 411 - 412 - 413 - 414 - 415 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/415-conditional-route-handlers`, **stacked on `feat/414-definition-precedence`** (#112; 411 is #109 below it).
  Contract `.mango/run-contract-415.txt`. RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 13 unresolved surfaced | 3 want-decision asked | 10 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `routes.py` `Route` (one target), 411's collision (`colliding`, `collision_fields`), `trace_capability`,
`impact(routes=)` resolve. Recall (type 2, by handle — the route row's shape several tools read): 362-C1
`widen-every-query-that-shares-the-page`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 62,040 tokens) raised thirteen items, settled below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | duplicates | how | a duplicate repeats key, target **and** `when` — the same handler under two labels is two rows (411's rule widened) |
| H2 | source columns | how | inline `when`/`source` fields; TSV and JSON `columns` gain optional `when`/`source` (dotted for JSON); a blank cell is no label, never an incomplete row |
| H3 | `source` | how | a stored label like `when`; only `target` is located (routes are "declared, not resolved", `routes.py:10`) |
| H4 | old tables | how | `load` reads `when`/`source` with `get`, so a table stored before 415 loads |
| H5 | AC2 | how | `as_row` adds `when`/`source` only when set |
| H6 | status | how | `collisions` excludes conditional keys; `conditional` counts them |
| H7 | tools | how | `_traced_route` already traces every candidate; `impact` already seeds every match; `search_symbol`'s `containing` lists each row |
| H8 | order | how | table order (R4.2) |
| H9 | contract, docs | how | no contract move (meta only); TOOLS.md's collision sentence rewritten in place |
| H10 | the extractor | how | out of scope (R1.1), as the ticket says |
| W1 | mixed labels | want | **ASSUMED (awaiting ratification):** a key whose rows include an unlabelled one, or two rows sharing a label, is a 411 collision — only distinct labels on every row make it conditional |
| W2 | declaration shape | want | **ASSUMED (awaiting ratification):** repeated rows only, one handler each; no nested `handlers` list — one spelling across inline, TSV and JSON |
| W3 | telling alternatives from a collision | want | **ASSUMED (awaiting ratification):** no new top-level field; a conditional answer carries no `ambiguity`, and each flow's `route` (and `impact`'s `routes` rows) carries its `when`/`source` |

## Phase 1 — analysis

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Why this exists · Scope · Out of scope · Acceptance criteria) | 4 decomposed | ROWS: C=2 R=5 G=1 AC=2`
`CLARIFICATION: 13 raised | 13 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/5 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

W1–W3 count as self-resolved because the handover handed them back; each stands `ASSUMED` for the maintainer.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "has nowhere to put the conditions" | a declared condition per handler | ✅ |
| C1 | Scope 4 | nothing evaluates them | labels, stored and returned | ✅ |
| C2 | Out of scope | no extractor | — | ✅ |
| R1 | Scope 1 | several handlers, `when`, `source`, three sources | `Handler`; H2; W2 | ✅ |
| R2 | Scope 2 | distinct labels → conditional; no `when` → collision | `conditional`, W1 | ✅ |
| R3 | Scope 3 | one flow per handler; `impact` every handler | H7, W3 | ✅ |
| R4 | Scope 4 | as C1 | — | ✅ |
| R5 | Scope 5 | docs | TOOLS.md, two docstrings | ✅ |
| AC1 | AC1 | two flows, labels, sources; `impact` covers both | fixture | ✅ |
| AC2 | AC2 | single handler as before | H5 | ✅ |

### AC validation

| AC | Falsifiable? | Definition |
|---|---|---|
| AC1 | yes | flows `{(XA, region=A, x.php:12), (XB, region=B, x.php:12)}`; no `ambiguity`; `impact(routes=)` `routes` rows carry both targets and labels, `seeds_dropped == 0` |
| AC2 | yes | a single-handler flow's `route` keys are exactly `route, target, file, tier, rule`; the 385/397/411 suites unchanged |

**Inventory — R1 (N = 3):** 1 inline · 2 TSV · 3 JSON. Review confirms each.

### Gap analysis (enhancement)

- Current: `Route` holds one target; rows of one key with two targets are a collision (411).
- Target: a per-row `when`/`source`; distinct labels make a conditional route.

**Blast radius.** `routes.py` (readers, `resolve`, `load`, `as_row`, census, `collision_fields`), `trace_capability`,
`impact` (docstrings only), the route suites, TOOLS.md.

### BASELINE

`BASELINE: green — 414's final gate on this stack: 4972 passed, 4 skipped, 1 xfailed, 2 host exclusions`

Ran at 414's gate tree (recorded in 414's working doc). Host exclusions as 411.

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ labels are opaque strings, no language · §R1.8 (change-type) ✅ conditional() is the one test colliding and collision_fields share · §R4.2 (change-type) ✅ table order · §R5.6 (change-type) ✅ a conditional route and a collision answer differently; tests drive both · §R6.5 (change-type) ✅ the proving tests seen red · §R7.6 (change-type) ✅ TOOLS.md's collision sentence rewritten, not appended`

## Phase 2 — design

### Approach

1. `routes.Handler(key, target, when, source)`; `_entry`, `_tsv`, `_json` read the labels; a blank one is none.
2. `resolve` keys duplicates on `(target, when)` and stores `Route.when`/`source`; `load` reads them with `get`.
3. `conditional(rows)`; `colliding` and `collision_fields` skip a conditional key; the census adds `conditional`.
4. `as_row` carries `when`/`source` when set.
5. Docs: TOOLS.md, the `trace_capability` and `impact` docstrings.

### Rejected alternatives

- **A nested `handlers` list in a row** — W2.
- **A `conditional: true` top-level field** — W3: each flow carries its label already.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| `_traced_route` traces each candidate separately | verified | 411's loop (`trace_capability.py`, `_traced_route`) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | handlers, labels, conditional | `code_atlas/routes.py` | the route suites | R1–R3, AC1, AC2 | 3/3 |
| 2 | docstrings | `code_atlas/tools/trace_capability.py`, `code_atlas/tools/impact.py` | tool descriptions | R5 | 2/2 |
| 3 | tests | `tests/test_conditional_route_handlers.py` (new) | — | AC1, AC2 | 1/1 |
| 4 | docs | `docs/TOOLS.md` | doc budgets | R5 | 1/1 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `widen-every-query-that-shares-the-page` — traced: `rtk proxy grep -rn "as_row()\|routes.matches\|colliding(" code_atlas`
  → `trace_capability.py` (flows), `impact.py` (`reaching`, `collision_fields`), `search_symbol.py` (`containing`),
  `routes.py` (census); every reader takes the row from `as_row`, and both collision readers go through `conditional`.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — build, trace, impact | a real build through the Python adapter | n/a | ✅ |
| AC2 | integration | the same build's single-handler route; the route suites | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_conditional_route_handlers.py`

### Rollback

`git revert` the branch's commits; no contract or schema moved.

## Phase 3 — execute

Implemented in the main loop. Commits `8d36a070` (core + tests), `cb048d10` (docs).

**Red first** (R6.5): with `code_atlas/` stashed back to the base, `tests/test_conditional_route_handlers.py` gives
`5 failed, 1 passed` — the pass is AC2, unchanged by design.

**Green at execute:**

Ran at cb048d10

```
$ .venv/bin/python -m pytest -q tests/test_conditional_route_handlers.py
6 passed in 1.55s
$ .venv/bin/python -m pytest -q -k "route or trace or impact or status or doc_size or chain or description or brief or skill or tool"
830 passed, 4155 deselected in 65.26s (0:01:05)
$ .venv/bin/ruff check code_atlas tests && .venv/bin/mypy code_atlas
All checks passed!
Success: no issues found in 105 source files
```

**Verification sweep.** File axis: every touched file is on the change list. Behaviour axis: Approach 1–5 implemented
as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.

- **`challenger` round 1** (ticket-blind, 64,281 tokens; raw ticket only): 5 met · 2 ACs met · 0 not met · 0 can't
  tell; four Minor findings.
  - M1 — a misspelt TSV `when`/`source` column was ignored, turning every conditional route into a collision —
    **fixed**: a named label column the file lacks is a `ConfigError` (`test_a_missing_label_column_*`). A JSON
    dotted path cannot be checked against a header; a missing one reads as no label.
  - M2 — `collision_examples` hid the labels — **fixed**: an example names a row's `when` when it has one.
  - M3 — the docs did not say a blank label is none, or that one unlabelled row makes a collision — **fixed** in
    TOOLS.md. No CHANGELOG entry: the stack ships no release (no contract or schema move).
  - M4 — no test for a wildcard or `significant_by_path` conditional key — **accepted**: both act on the key before
    the label, and 411's suite covers them.
- **Round 2: verify-only, main loop.** The fixes stay inside `routes.py`, its test and TOOLS.md.

```
$ .venv/bin/python -m pytest -q tests/test_conditional_route_handlers.py tests/test_route_collisions.py tests/test_route_table.py tests/test_routes_from_json.py tests/test_doc_size_budget.py
46 passed in 6.25s
```

Ran at HEAD of the review fix (the commit before this bookkeeping).

Verdict: clean (challenger only — REVIEWER: OFF), W1–W3 standing for ratification.
`Ph3/4 proven by`: R1 (3/3: inline · TSV · JSON) → `test_inline_and_json_rows_*`, `test_ac1_*`; R2 →
`test_a_labelled_and_an_unlabelled_*`, `test_status_counts_*`; R3, AC1 → `test_ac1_*`; AC2 → `test_ac2_*`, the route
suites; C1/R4 → labels stored and echoed only; R5 → TOOLS.md, docstrings.

Reviewed at the review-fix commit. Files: `code_atlas/routes.py`, `code_atlas/tools/trace_capability.py`,
`code_atlas/tools/impact.py`, `tests/test_conditional_route_handlers.py`, `docs/TOOLS.md`. Working doc: this file.

## Phase 5 — finalise

**Durable lesson.** None new: 415 met its ACs on the first pass; the one finding of weight (M1, a silently ignored
optional column) is 363-C1's class — a zero that counts what it cannot see — and is recorded there.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`

### Outward actions

Under the handover: push `feat/415-conditional-route-handlers`; open its PR against `feat/414-definition-precedence`.
Deferred to the maintainer: ratify W1–W3, merge after #112.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 62,040 |
| 3 execute | `implementer` — not dispatched; main loop implemented | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | ticket-blind `challenger` | 1 | 64,281 |

`LEDGER TOTAL: 126,321 · top cost driver: 4 review / challenger` — main loop unmeasured.
