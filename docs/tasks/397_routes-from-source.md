---
id: 397
slug: routes-from-source
title: 'A routes table must be a generated TSV, so the consumer keeps a script and a copy that drift from the census it came from'
phase: 2
milestone: Coverage
status: done
depends_on: [385, 396]
---

## Why this exists

This comes from the anchor project (2026-10-17). The anchor already keeps a JSON census of its
endpoints: URL plus handler, the handler by short class name (`OrderController::listAction()`).
385's `routes` block reads only an inline `table` or a two-column TSV whose target is a stored
qname, so the anchor wrote a ~100-line script to turn the census into a 1,162-row TSV.

- F1: the script re-implements name resolution. It scans `namespace` + `class` declarations to
  turn a short class into a qname and picks a regional twin by a hand-written order. The index
  already holds every class's qname.
- F2: the TSV is a copy. When the census changes and nobody re-runs the script, routes answer from
  the old table; 396's digest sees the TSV, not the census behind it.

## Scope

1. A `routes` block may name a JSON source: a path, the row selector, and the fields for `key` and
   `target`. The file is digested like a TSV (396).
2. A target written `Class::method()` or `Class::method` with a short class resolves against the
   index's stored qnames. Exactly one class: linked. Several: an optional `prefer` list of qname
   segments picks one in order, else the row counts as unresolved and the status lists its
   candidates. None: unresolved, as today.
3. TSV and inline tables are unchanged.

## Acceptance criteria

- **AC1:** A fixture census with three endpoints whose handlers name short classes: the build
  links all three, and `trace_capability(route=…)` answers as it does for the equivalent TSV.
- **AC2:** Two classes with one short name, `prefer` absent: the row is unresolved and the status
  names both candidates. With `prefer`, the preferred one is linked.
- **AC3:** Edit the census only: 396's `rules_stale` turns on, and the next incremental build
  applies it.
- **AC4:** An existing TSV block answers byte-identically.

- **AC-field:** the anchor deletes its generator script and TSV, points the block at its census,
  and gets at least the TSV's resolved count; record both counts in the working doc.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 397 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W3, runs E1, then merges after the 396 PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 396 - 398 - 397 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/397-routes-from-source`, **stacked on `feat/396-rules-stale`** (it needs 396's digest). Contract `.mango/run-contract-397.txt`.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 3 want-decision asked | 9 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** 385's `routes` block (`routes.py`), the TSV reader, `publish_routes` and 396's digest resolve. Ambiguous:
"the anchor's census".

**Recall (by handle).** `a-zero-must-count-what-the-search-cannot-see` (363-C1): an ambiguous row is counted and named,
never a silent miss. `widen-every-query-that-shares-the-page` (362-C1): every route reader — `trace_capability`,
`impact`, `search_symbol` — reads the one stored table, so nothing past `publish_routes` changes.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 57,315 tokens) raised twelve; they are H1–H9 and W1–W3.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where candidates show | how | `get_index_status` (standard) `routes_ambiguous`, first 20 with `routes_ambiguous_count` — 388's `behind_because` cap |
| H2 | exact or short first | how | a File, then an exact stored qname, as today; the short form only on a miss, in census rows only (Scope 3) |
| H3 | what a short class matches | how | the qname's last component before `::method`, whole and case-sensitive, and the member must exist — no class fallback (R5.2) |
| H4 | `()` | how | stripped; the ticket names both spellings |
| H5 | the selector | how | `rows` is a dotted object path to a list (absent: the file is the list); `columns` fields may be dotted; a row missing either is skipped like a TSV row; a bad file, selector or `columns` is a `ConfigError` (R5.3) |
| H6 | order across sources | how | inline, TSV, then the census in document order; the first row of a key wins (385) |
| H7 | where an ambiguous row lands | how | `routes_unresolved` as today, its URL `no_such_symbol` with `nearest_routes`; the status names it |
| H8 | `significant` and `*` | how | the block's own, as for every row |
| H9 | the digest | how | the file's bytes, as a TSV's (396 H12) |
| W1 | `prefer` semantics | want | **ASSUMED (awaiting ratification):** whole qname segments, tried in order; each that matches a candidate narrows the set; a tie left over stays ambiguous; per block, census rows only |
| W2 | a resolved short name in answers | want | **ASSUMED (awaiting ratification):** stored as the full qname and answered exactly as a TSV row (AC1) — no extra flag |
| W3 | AC-field (anchor) | want | **ASSUMED (awaiting ratification):** E1, the maintainer's standing answer of 2026-10-17 |

## Phase 1 — analysis

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=5`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/6 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

Stacked on 396. `main`'s full suite: `4697 passed, 4 skipped, 1 xfailed in 573.67s (0:09:33)`, ran at 60d802c5; 396's own
gate is quoted in its working doc.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a script and a copy that drift from the census" | read the census itself | ⏳ |
| C1 | AC4 | "An existing TSV block answers byte-identically" | TSV and inline rows untouched | ⏳ |
| R1 | Scope 1 | "may name a JSON source … digested like a TSV" | H5, H9 | ⏳ |
| R2 | Scope 2 | "a short class resolves … `prefer` … the status lists its candidates" | H1–H4, H7, W1, W2 | ⏳ |
| R3 | Scope 3 | "TSV and inline tables are unchanged" | H2 | ⏳ |
| AC1–AC4 | AC | three link · two classes · census edit · TSV unchanged | | ⏳ |
| AC5 | AC-field | anchor | W3 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — three routes, answers equal to a TSV twin's | |
| AC2 | yes — the count and the candidate list | |
| AC3 | yes — `rules_stale`, then the new target | |
| AC4 | yes — 385's suite unchanged | |
| AC5 | no — the anchor | E1 |

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the member separator is the contract's, no language branch · §R1.4 (change-type) ✅ routes.py reads data, enrichment resolves through the store · §R4.2 (change-type) ✅ candidates sorted, census rows in document order · §R5.2 (change-type) ✅ a tie is never guessed: it is counted and named · §R5.3 (change-type) ✅ a bad census file, selector or columns fails loud`

## Phase 2 — design

### Approach

1. `routes.py`: `_json` reads the census into its own `RouteBlock(short_names=True, prefer=…)` after the inline and TSV
   rows; `resolve` asks a `candidates` callback on a census miss and collects ties.
2. `enrichment.publish_routes`: `candidates` finds `Class::method` by name and whole component; ties go to meta.
3. `get_index_status`: `routes_ambiguous` at standard. Docs: TOOLS.md, CHANGELOG `Unreleased`.

### Rejected alternatives

- **Short names for TSV rows too** — Scope 3 keeps them unchanged.
- **A new tool argument for the census** — the rule file is where routes are declared (385).

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | the census and ties | `code_atlas/routes.py` | route blocks | R1, R2, R3 | 1/1 |
| 2 | candidates | `code_atlas/enrichment.py` | `publish_routes` | R2 | 1/1 |
| 3 | status | `code_atlas/tools/get_index_status.py` | standard payload, only with ties | R2 | 1/1 |
| 4 | tests | `tests/test_routes_from_json.py` (new) | — | AC1–AC3 | 1/1 |
| 5 | docs | `docs/TOOLS.md`, `CHANGELOG.md` | doc budgets | G1 | 2/2 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC3 | integration — Python adapter + build + tools | real builds, `trace_capability`, status | authored | ✅ |
| AC4 | integration | `tests/test_route_table.py` unchanged | existing | ✅ |
| AC5 | runtime — anchor | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** AC-field · risk: low · why: the anchor index is not on this machine ·
escalated, answered by the maintainer 2026-10-17 · follow-up: on the anchor, point the block at the census, delete
the generator and TSV, compare resolved counts · `expiry: when the anchor index is available to a maintainer run` ·
`seen: 378, 384, 388, 389, 394, 390, 391, 393, 395, 396, 398, 397`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_routes_from_json.py` — red on 396's tip (2232eb74: `6 failed`), green after.

### Rollback

`git revert`; a census block then fails the build as an unknown source, so remove it first.

## Phase 3 — execute

Commits `dd4a5b9d` (code, tests), `b6490f1d` (docs).

**Red first.** 2232eb74: `6 failed`. **Green after.** `6 passed`; with `test_route_table.py` and `test_rules_stale.py`:
`29 passed`. `ruff`, `mypy` clean. Ran at b6490f1d.

**Axis 1.** Change-list rows 1–5. **Axis 2.** Approach bullets 1–3 implemented as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` — verdict **clean (challenger only — REVIEWER: OFF)**.

**Challenger** (ticket-blind: raw ticket plus `git diff feat/396-rules-stale..HEAD` without this file; 1 dispatch,
61,154 tokens): 8 met · 0 not met · 2 can't tell (AC4 by test, AC-field). No Major, eight Minor:

| # | Finding | Resolution |
|---|---|---|
| m1 | `prefer` stopped at the first segment matching several | each matching segment narrows the set (ee533907) |
| m2 | a `prefer` entry like `Acme\Main` never matches | kept: an entry is one segment (TOOLS.md says so) |
| m3 | a block with TSV/inline rows and a census resolved short names in all of them | the census is its own block (ee533907) |
| m4 | an exact top-level `Orders::edit` wins over a namespaced twin | kept: exact first is 385's rule (H2) |
| m5 | `columns` naming one field dropped every row | a `ConfigError` (ee533907) |
| m6 | a key tied in one row and linked by a later row stayed listed | only an unrouted key is named (ee533907) |
| m7 | 50 candidates at most, unannounced | kept: deterministic, and 50 same-named classes is not a census |
| m8 | ties read from the last build | kept: `rules_stale` names that window (AC3) |

**Red first.** The three challenger tests against b6490f1d: `3 failed`. **Green after:** `9 passed`; with
`test_route_table.py`: `21 passed`. Ran at ee533907.

| Row | Ph3/4 proven by | k/N |
|---|---|---|
| R1 / AC3 | `test_ac3_…`, `test_a_census_with_no_list_…`, `test_challenger_columns_…` | 3/3 |
| R2 / AC1 / AC2 | `test_ac1_…`, `test_ac2_…` (both), `test_a_short_class_matches_…`, `test_challenger_prefer_…` | 5/5 |
| R3 / C1 / AC4 | `test_challenger_inline_rows_…`, `test_route_table.py` unchanged | 2/2 |
| AC5 | E1 | 0/1 (excluded) |

Reviewed at ee533907 — files: change-list rows 1–5. Working doc: `docs/tasks/397_routes-from-source.md`.

## Phase 5 — finalise

**Durable lesson.** None new as a claim. `seen:` gains 397 for the two traced handles (P1).

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Stale-review guard: after ee533907 only this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` and `docs/LESSONS.md` change.
Not stale.

### Outward actions

Under the handover: push `feat/397-routes-from-source`; open the PR against `main` (stacked on the 396 PR).
Deferred: ratify W1–W3; E1; merge after 396.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 57,315 |
| 4 review | `challenger` (ticket-blind) | 1 | 61,154 |

`LEDGER TOTAL: 118,469 · top cost driver: challenger`
