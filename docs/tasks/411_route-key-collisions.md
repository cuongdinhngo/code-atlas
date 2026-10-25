---
id: 411
slug: route-key-collisions
title: "Two declared routes that canonicalise to one key keep the first silently, so a URL traces to an unrelated handler"
phase: 2
milestone: Trust
status: todo
depends_on: [385, 397]
---

## Why this exists

A consumer's survey of real questions, 2026-10-25, on a legacy PHP monolith (about 12.9k files and
177k symbols). 154 declared routes of the form `/endpoint.php?cmd=X` canonicalised to a single key,
because `cmd` was not in the block's `significant` set. Every such URL traced to the same, wrong,
handler, and nothing said so. Of 1,029 declared rows, 834 were stored. The consumer could account for
153 of the 195 missing rows (the collapsed ones) but not for the other 42.

On `main`, `routes.resolve` skips a key it has already seen with no count (`routes.py:236-238`).
Rows whose target names nothing are counted as `routes_unresolved`, but only in the build report
(`enrichment.py:261`), never in `get_index_status`. A consumer that reads status cannot balance the
table.

`significant` is already per block (`routes.py:92`), so a path can get its own keys through a
separate `routes` block. The gap is that a collision is never reported, and a JSON or TSV census is
one block with one key set.

## Scope

1. At build, two declared rows that canonicalise to one key with **different** targets are a
   collision. Store them, and report them in `get_index_status` as a count plus the first N examples.
   Two rows with the same key and the same target are a duplicate, not a collision.
2. Every declared row that is not stored is counted by reason: unresolved, short-name tie (397),
   collision, duplicate. Report the counts in `get_index_status`, with examples.
3. `trace_capability(route=…)` on a colliding key answers with every candidate and an ambiguity flag.
   It never answers one handler. `impact(routes=…)` behaves the same way.
4. Let a census set its significant keys per path, as well as per block. Design picks the smallest
   form: a per-path map in the block, or a per-row column.
5. Update the user docs for the routes rule.

Out of scope: several handlers on one key *by design* (415 builds that on top of this).

## Acceptance criteria

- **AC1:** A fixture declares `/x.php?cmd=a` → `A::a` and `/x.php?cmd=b` → `B::b`, with `significant`
  excluding `cmd`. Status reports one collision, and tracing `/x.php?cmd=b` does not answer `A::a`
  alone. It answers both candidates, flagged ambiguous.
- **AC2:** With `cmd` significant for `/x.php`, both URLs resolve to their own handler and no collision
  is reported.
- **AC3:** For every fixture, declared = stored + Σ dropped-by-reason.
- **AC4:** A routes rule with no collisions answers exactly as before. Status only gains the new
  counts.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 411 · **work_doc_mode:** embed · **Current phase:** 4 review · **Next action:** settle the challenger's findings, then finalise.
- `TRACK: backend` · Run mode: `autorun 411 - 412 - 413 - 414 - 415 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/411-route-key-collisions` from `main` (`d3d45b21`; `origin/main` `9a682358` is #108's merge commit, same tree). Contract `.mango/run-contract-411.txt`.
  RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 11 unresolved surfaced | 5 want-decision asked | 6 how-decision resolved+cited | 5 ASSUMED | skip: no`

**Premise.** `routes.resolve` (`routes.py:218`, its `seen` skip), `routes_unresolved` (`enrichment.py:261`),
`significant` per block (`routes.py:92`), `get_index_status`, `trace_capability(route=)`, `impact(routes=)` resolve.
Recall (type 2, by handle — the change widens what one route key holds, read by several tools): 384-C1
`keep-first-hides-the-later-declaration`; 363-C1 `a-zero-must-count-what-the-search-cannot-see`; 362-C1
`widen-every-query-that-shares-the-page`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 50,940 tokens) raised eleven items, settled below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the counts live | how | their own meta key `routes_census` beside `routes_ambiguous` (R1.7; `enrichment.py:296`) |
| H2 | examples cap | how | 20, as `routes_ambiguous` (`get_index_status.py:131`) |
| H3 | several rows per key | how | `dump`/`load` already store a list; `match` becomes `matches` → a list, both callers change |
| H4 | wildcard keys | how | collision by canonical-string equality, as today's `seen` (`routes.py:70`) |
| H5 | status when nothing collides | how | the `routes` block appears whenever a routes rule was built, as `records` does (`get_index_status.py:650`); zero reasons are omitted from `dropped` |
| H6 | contract | how | none: the table lives in meta (385's docstring, `routes.py:9`) |
| W1 | per-path form | want | **ASSUMED (awaiting ratification):** a `significant_by_path` map in the block, `{path: [keys]}`; the path is matched exactly (leading `/` dropped), never a glob, and replaces the block's `significant` for that path. One form for inline, TSV and JSON rows; a per-row column would need a TSV and a JSON spelling |
| W2 | the collision answer | want | **ASSUMED (awaiting ratification):** `trace_capability` traces every candidate, each flow carrying its own `route`; the payload adds `ambiguity: "route_collision"` (the existing `ambiguity` field, 394/403) and `route_candidates` (each route row); `reason` stays `ok` / `no_matches` |
| W3 | `impact` on a collision | want | **ASSUMED (awaiting ratification):** every candidate seeds the walk; the same two fields |
| W4 | duplicate vs collision | want | **ASSUMED (awaiting ratification):** across every block, a row repeating a key's stored target is a `duplicate` (dropped); each distinct target is stored in declaration order — A, B, A stores A and B |
| W5 | the dropped taxonomy | want | **ASSUMED (awaiting ratification):** `stored` counts rows, colliding rows included; `collisions` counts keys; `dropped` = `unresolved`, `short_name_tie`, `duplicate`, and `incomplete` (a census row missing its key or target — the likeliest home of the survey's 42). A tie row is a tie even when another row links its key. Scope 2's "collision" reason is empty by W5: colliding rows are stored (Scope 1, AC1) |

## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=5 G=1 AC=4`
`CLARIFICATION: 11 raised | 11 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

W1–W5 count as self-resolved because the handover handed them back; each stands `ASSUMED` for the maintainer.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "nothing said so … cannot balance the table" | a collision is visible and every row accounted for | ✅ |
| C1 | Out of scope | several handlers by design (415) | no `when`; a collision is reported, not modelled | ✅ |
| R1 | Scope 1 | collisions stored, counted, N examples; same target = duplicate | W4, W5 | ✅ |
| R2 | Scope 2 | every unstored row counted by reason, with examples | W5, H1, H2 | ✅ |
| R3 | Scope 3 | trace and impact answer every candidate, flagged | W2, W3 | ✅ |
| R4 | Scope 4 | per-path significant keys | W1 | ✅ |
| R5 | Scope 5 | user docs | TOOLS.md routes paragraph, both tool docstrings | ✅ |
| AC1 | AC1 | one collision in status; `cmd=b` answers both, flagged | fixture build | ✅ |
| AC2 | AC2 | `cmd` significant for `/x.php` → own handlers, no collision | `significant_by_path` | ✅ |
| AC3 | AC3 | declared = stored + Σ dropped | every fixture | ✅ |
| AC4 | AC4 | no collision → answers as before; status only gains | the 385/397 suites unchanged | ✅ |

### AC validation

| AC | Falsifiable? | Definition |
|---|---|---|
| AC1 | yes | `status.routes.collisions == 1`; `trace_capability(route=URL_B)` flows seeded at both `A::a` and `B::b`, `ambiguity == "route_collision"` |
| AC2 | yes | with `significant_by_path`, `collisions == 0`, the trace of `URL_B` seeds `B::b` only, no `ambiguity` |
| AC3 | yes | `declared == stored + sum(dropped.values())` on both fixtures and on the tie and A-B-A units |
| AC4 | yes | `tests/test_route_table.py`, `tests/test_routes_from_json.py` pass with only `match` → `matches` |

**Inventory — R3 (N = 2):** 1 `trace_capability(route=)` · 2 `impact(routes=)`. Review confirms each.

### Gap analysis (enhancement)

- Current: `resolve` keeps the first linked row of a key and skips the rest uncounted (`routes.py:236`); a census row
  missing a column is skipped uncounted (`_tsv`, `_json`); status shows `routes_ambiguous` only.
- Target: every row stored or dropped by reason, collisions stored and answered together.

**Blast radius.** `routes.py` (resolve, matches, readers), `enrichment.publish_routes`, `get_index_status`,
`trace_capability._traced_route`, `impact` (route seeds), `search_symbol` (reads `containing`, unchanged), the 385/397
suites, TOOLS.md.

### BASELINE

`BASELINE: green — CI on main: 4943 passed, 4 skipped, 1 xfailed (py3.12 and py3.13)`

Ran at 9a682358a (GitHub Actions run 40185299153; its tree equals `d3d45b21`, this branch's base). A local
`scripts/gate.sh` started on the base was stopped: edits landed in the tree while it ran, so it proved nothing.

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the core compares keys and targets, never a language · §R1.7 (change-type) ✅ the census is its own meta key, beside the table · §R1.8 (change-type) ✅ trace and impact share routes.collision_fields · §R5.6 (change-type) ✅ a collision is told apart from one handler by ambiguity; a test drives both · §R7.6 (change-type) ✅ TOOLS.md's first-row-wins sentence replaced, not appended to · §R6.5 (change-type) ✅ the proving tests seen red before the change · §R6.9 (change-type) ✅ assertions read the tools' answers and status, not the census object alone`

## Phase 2 — design

### Approach

1. `routes.resolve` keeps every distinct `(key, target)`; a repeat is `duplicate`. A `Census` (declared, stored,
   dropped by reason, 20 examples each) is filled in the same pass; `as_status` adds `collisions` and 20
   `collision_examples`.
2. `RouteBlock.by_path` from `significant_by_path`; `significant_for(declared)` picks the path's keys; the route
   stores the keys it was keyed with, so `matches` canonicalises a URL the same way.
3. The TSV and JSON readers return the count of rows missing a key or target (`incomplete`).
4. `matches` returns every route of the first matching key; `collision_fields` is the one helper both tools call.
5. `publish_routes` stores `routes_census`; `get_index_status` reports it as `routes`.
6. Docs: TOOLS.md's routes paragraph; the two tool docstrings.

### Rejected alternatives

- **A per-row `significant` column** — two spellings (TSV column, JSON field), and inline rows would need a third.
- **Answer the first candidate with a warning** — Scope 3 says never one handler.
- **Count collisions as dropped** — AC1 needs both targets traced, so they must be stored.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| `dump`/`load` round-trip several rows of one key | verified | a list of `Route` dicts (`routes.py`, `dump`) |
| a trace seeded per candidate gives each its own flow | verified | AC1 test: seeds `{A::a, B::b}` |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | resolve, census, matches, per-path keys, incomplete rows | `code_atlas/routes.py` | the 385/397 suites | R1, R2, R4 | 3/3 |
| 2 | store the census | `code_atlas/enrichment.py` | rules_stale digest (unchanged) | R2 | 1/1 |
| 3 | status `routes` | `code_atlas/tools/get_index_status.py` | status tests | R2, AC1 | 1/1 |
| 4 | trace and impact on a collision | `code_atlas/tools/trace_capability.py`, `code_atlas/tools/impact.py` | tool descriptions | R3 | 2/2 |
| 5 | tests | `tests/test_route_collisions.py` (new), `tests/test_route_table.py` (`matches`) | — | AC1–AC4 | 2/2 |
| 6 | docs | `docs/TOOLS.md` | doc budgets | R5 | 1/1 |
| 7 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `keep-first-hides-the-later-declaration` — traced: `rtk proxy grep -n "if key in seen" code_atlas/routes.py` →
  `237: if key in seen:` on the base; the keep-first skip is the defect, removed by Approach 1.
- `a-zero-must-count-what-the-search-cannot-see` — traced: `rtk proxy grep -n "if row.get(str(key_column))\|found.append" code_atlas/routes.py`
  on the base → the TSV comprehension filter and the JSON `found.append` drop a short row uncounted; Approach 3 counts them.
- `widen-every-query-that-shares-the-page` — traced: `rtk proxy grep -rn "routes.match\|route_table.match" code_atlas`
  on the base → `trace_capability.py:228`, `impact.py:241`; both move to `matches` (Approach 4). `search_symbol` reads
  `containing`, which already lists every row.

### Rule compliance

Phase 1's seven sections bind. R7.5 binds every comment.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — build, status, two tools | a real build through the Python adapter | n/a | ✅ |
| AC2 | integration | the same build with `significant_by_path` | n/a | ✅ |
| AC3 | logic + integration | both builds' status, and `resolve` units for ties and A-B-A | n/a | ✅ |
| AC4 | integration | the 385/397 suites | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_route_collisions.py`

### Rollback

`git revert` the branch's commits; no contract or schema moved, so an index needs only a rebuild to drop
`routes_census`. One repo.

## Phase 3 — execute

Implemented in the main loop. Commits `afaa56b9` (core + tests), `c644d8d3` (docs).

**Red first** (R6.5): with `code_atlas/` stashed back to `d3d45b21`, `tests/test_route_collisions.py` gives
`6 failed in 3.03s`. Ran at c644d8d3 (tests) over d3d45b21's core.

**Green at execute:**

```
$ .venv/bin/python -m pytest -q tests/test_route_collisions.py tests/test_route_table.py tests/test_routes_from_json.py
29 passed in 11.08s
$ .venv/bin/python -m pytest -q -x -k "route or status or impact or trace or description or skill or brief or record or rules or capability or tool"
1020 passed, 3934 deselected in 129.94s (0:02:09)
$ .venv/bin/ruff check code_atlas && .venv/bin/mypy code_atlas
All checks passed!
Success: no issues found in 105 source files
```

Ran at c644d8d3.

**Verification sweep.** File axis: every touched file is on the change list. Behaviour axis: Approach 1–6 implemented
as approved. `get_index_status._attach_routes_ambiguous` is renamed `_attach_routes` (it now attaches both).
