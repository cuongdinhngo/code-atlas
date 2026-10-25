---
id: 413
slug: record-attributes
title: "A record's trust tier, region or status is dropped at build, so the agent treats an unverified record as verified"
phase: 2
milestone: Trust
status: done
depends_on: [407]
---

## Why this exists

A consumer's survey, 2026-10-25. Its records carry attributes the answering agent needs right away:
a trust tier, a region, a status. The `records` field map reads only `id`, `title`, `url`, `kind` and
`targets` (`records.py:30`, `_fields`). To get the rest the agent must look each record up in a second
store. It often skips that lookup and treats unverified records as verified.

## Scope

1. The `records` block declares extra attributes as a list of dotted field paths, for example
   `"attributes": ["tier", "region", "status"]`. They are stored, and returned verbatim on every
   record row in every answer. Design states which JSON value shapes are kept.
2. A `records_filter` parameter on the tools that return records: equality or `in` on declared
   attributes, for example `{"tier": ["A", "B"]}`. A filter on an undeclared attribute is refused,
   not ignored.
3. Undeclared source fields are still ignored, and `exclude` still drops a record before anything
   reads it.
4. Update the user docs for the records rule.

## Acceptance criteria

- **AC1:** A fixture record with `tier: "A", region: "X"` carries both fields in `read_symbol`,
  `find_references` and `impact`.
- **AC2:** `records_filter: {"tier": ["A"]}` keeps it, and `{"tier": ["C"]}` drops it. The answer's
  record total counts what the filter kept.
- **AC3:** A records block without `attributes` answers byte-identically to before.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 413 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges #111 after #110. **Revert path:** `git revert` the branch's commits; no contract or schema moved.
- `TRACK: backend` · Run mode: `autorun 411 - 412 - 413 - 414 - 415 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/413-record-attributes`, **stacked on `feat/412-records-direct-first`** (#110). Contract `.mango/run-contract-413.txt`.
  RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 0 want-decision asked | 7 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** `records.py:30` (`_DEFAULT_FIELDS`), `_fields`, the `exclude` file, and the three tools that list records
resolve. Recall (type 2, by handle — a shared row shape three tools read; a new parameter on three tools): 362-C1
`widen-every-query-that-shares-the-page`; 412-C1 `a-new-parameter-meets-the-surface-guards`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 56,746 tokens): no want-decision; seven how-decisions.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where declared names live | how | their own meta key `records_attributes` (R1.7); the records blob gains a field only on a record that has values |
| H2 | kept value shapes | how | a string, number, boolean, or a non-empty list of them; null, objects and nested lists dropped, never failing the build — as `_record` treats `title`/`url`/`kind` (R5.3) |
| H3 | the row's layout | how | a nested `attributes` object: a flat `tier` would collide with the row's own `tier: HEURISTIC` (R5.4) |
| H4 | the key | how | the declared path as written (`a.b`), the same string the filter names |
| H5 | where the filter applies | how | on the stored records, before ranking, the page, `records_total` and `records_stopped` (AC2) |
| H6 | refusal and equality | how | `ValueError`, as `impact`'s `depth` and 412's parameters; the declared set is the union of every block; no block or no attributes declared refuses too; a list in the filter is `in`; a list attribute matches when any element does; JSON `true` never equals `1` |
| H7 | the brief guard | how | `records_filter` waived as a records side-field the three tool descriptions teach (`test_agent_brief_usage_completeness.py`) |

## Phase 1 — analysis

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=4 G=1 AC=3`
`CLARIFICATION: 7 raised | 7 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "treats unverified records as verified" | the attribute rides with the record | ✅ |
| C1 | Scope 3 | undeclared fields ignored; `exclude` first | opt-in paths; `exclude` unchanged | ✅ |
| R1 | Scope 1 | attributes stored, verbatim on every row | H1–H4 | ✅ |
| R2 | Scope 2 | `records_filter`, refused when undeclared | H5, H6 | ✅ |
| R3 | Scope 3 | as C1 | — | ✅ |
| R4 | Scope 4 | docs | TOOLS.md records paragraph, three docstrings | ✅ |
| AC1 | AC1 | `tier`, `region` in the three tools | fixture | ✅ |
| AC2 | AC2 | `["A"]` keeps, `["C"]` drops; total counts kept | fixture | ✅ |
| AC3 | AC3 | no `attributes` → byte-identical | no `attributes` key on any row | ✅ |

### AC validation

| AC | Falsifiable? | Definition |
|---|---|---|
| AC1 | yes | `R-A`'s row `attributes == {"tier": "A", "region": "X", "status": [...]}` in `read_symbol`, `find_references`, `impact` |
| AC2 | yes | `{"tier": ["A"]}` → `{R-A}`; `{"tier": ["C"]}` → no `records`; `impact` `records_total == 2` for `["A", "B"]` |
| AC3 | yes | a block without `attributes`: no row carries `attributes`; 407's exact-row test unchanged |

**Inventory — R1/R2 (N = 3):** 1 `read_symbol` · 2 `find_references` · 3 `impact`. Review confirms each.

### Gap analysis (enhancement)

- Current: `_record` reads five fields (`records.py:30`); no tool filters records.
- Target: declared paths stored per record, returned on every row, filterable in all three tools.

**Blast radius.** `records.py` (Record, read, load, dump), `enrichment.publish_records`, `read_symbol._attach_records`
(four call sites), `find_references`, `impact`, the brief guard, 407/412 suites, TOOLS.md.

### BASELINE

`BASELINE: green — 412's final gate on this stack: 4954 passed, 4 skipped, 1 xfailed, 2 host exclusions`

Ran at b4ae92c3 (412's gate; the base tip `a5088f85` adds only its record). Host exclusions as 411.

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.7 (change-type) ✅ declared names on records_attributes · §R1.8 (change-type) ✅ one load_selected for three tools · §R5.3 (change-type) ✅ a bad value is dropped, not a build failure · §R5.4 (change-type) ✅ attributes nested, never beside the row's tier · §R5.6 (change-type) ✅ an undeclared name is refused rather than read as "no match" · §R6.5 (change-type) ✅ the proving tests seen red · §R7.6 (change-type) ✅ TOOLS.md records paragraph extended in place`

## Phase 2 — design

### Approach

1. `Record.attributes` (`(path, value)` pairs); `_attribute` keeps H2's shapes; `RecordSet.attributes` holds the
   declared paths; `publish_records` stores their union as `records_attributes`.
2. `as_row` adds `attributes` only when the record has one; `load` reads it back (absent → none).
3. `records.select` (H5, H6) and `load_selected`, the one entry the three tools call with `records_filter`.
4. Docs: TOOLS.md, the three docstrings; the brief guard waiver.

### Rejected alternatives

- **Flatten attributes into the row** — collides with `tier`/`kind`/`via`.
- **Ignore an undeclared filter name** — Scope 2 says refuse.
- **Keep any JSON value** — an object is a second store inside the row; the ticket asks for the shapes to be named.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| a record row reaches all three tools through `load` | verified | `rtk proxy grep -rn "records.load\|record_table.load" code_atlas/tools` → the three tools |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | attributes, select | `code_atlas/records.py` | 407/412 suites | R1, R2 | 2/2 |
| 2 | store declared names | `code_atlas/enrichment.py` | — | R2 | 1/1 |
| 3 | `records_filter` | `code_atlas/tools/read_symbol.py`, `find_references.py`, `impact.py` | tool descriptions | R2, AC2 | 3/3 |
| 4 | tests | `tests/test_record_attributes.py` (new), `tests/test_agent_brief_usage_completeness.py` | — | AC1–AC3 | 2/2 |
| 5 | docs | `docs/TOOLS.md` | doc budgets | R4 | 1/1 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `widen-every-query-that-shares-the-page` — traced: `rtk proxy grep -rn "records.load\|record_table.load" code_atlas/tools`
  → `find_references.py:421`, `impact.py:267`, `read_symbol.py:440`; all three move to `load_selected`.
- `a-new-parameter-meets-the-surface-guards` — traced: `rtk proxy grep -ln "_tool_params\|limit: int | None" tests`
  → `test_agent_brief_usage_completeness.py` (waiver added) and `test_limit_clamp_visible.py` (not a limit: unaffected).

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — build, three tools | a real build through the Python adapter | n/a | ✅ |
| AC2 | integration | the same build, filtered | n/a | ✅ |
| AC3 | integration | a build without `attributes`; 407's exact-row test | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_record_attributes.py`

### Rollback

`git revert` the branch's commits; no contract or schema moved.

## Phase 3 — execute

Implemented in the main loop. Commits `dca5a7df` (core + tests), `4085c985` (docs).

**Red first** (R6.5): with `code_atlas/` stashed back to the base, `tests/test_record_attributes.py` gives
`7 failed in 1.35s`. The value-shape test also caught the first draft keeping a nested list (`[[1]]`); fixed before
the commit.

**Green at execute:**

Ran at 4085c985

```
$ .venv/bin/python -m pytest -q tests/test_record_attributes.py
7 passed in 1.26s
$ .venv/bin/python -m pytest -q -k "record or impact or read_symbol or find_references or brief or limit or description or tool or skill"
1294 passed, 3674 deselected in 82.73s (0:01:22)
$ .venv/bin/ruff check code_atlas tests && .venv/bin/mypy code_atlas
All checks passed!
Success: no issues found in 105 source files
```

**Verification sweep.** File axis: every touched file is on the change list. Behaviour axis: Approach 1–4 implemented
as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.

- **`challenger` round 1** (ticket-blind, 61,952 tokens; raw ticket only): 7 met · 0 not met · 0 can't tell.
  - F1 (Major) — `read_symbol` checked the filter only where records attach; an unknown subject, a stale or outside-root
    read, or no index ignored an undeclared name — **fixed** in `1a040455`: `nav_result.require_records_filter` runs at
    the entry of all three tools, before any early return; no index declares nothing, so a named path is refused.
  - F2 (Major) — only `impact` has a record total — **accepted**: `read_symbol` and `find_references` list the
    subject's records whole, so their list is the total; AC2's total is `impact`'s `records_total`.
  - F3–F5, F7 (Minor) — a filter value that is an object, a null, an empty or nested list now refused; NaN and the
    infinities dropped as attribute values; TOOLS.md says a record without the attribute never matches and a row holding
    none of them carries no `attributes`. F6 (flat dotted keys) was already documented.
- **Round 2: verify-only, main loop.** The fixes stay inside `records.py`, the three tools' entry, `nav_result.py`
  (one helper the three call, R1.8), the test and TOOLS.md.

```
$ .venv/bin/python -m pytest -q -k "record or impact or read_symbol or find_references or brief or nav_result or import"
1077 passed, 3892 deselected in 100.14s (0:01:40)
```

Ran at 1a040455

Verdict: clean (challenger only — REVIEWER: OFF).
`Ph3/4 proven by`: R1, AC1 (3/3 tools) → `test_ac1_*`; R2, AC2 → `test_ac2_*`, `test_a_boolean_*`,
`test_a_filter_on_an_undeclared_name_*`, `test_a_bad_filter_is_refused_on_every_path`; AC3 → `test_ac3_*`, 407's
exact-row test; C1/R3 → 407's `exclude` tests; R4 → TOOLS.md.

Reviewed at 1a040455. Files: `code_atlas/records.py`, `code_atlas/enrichment.py`, `code_atlas/tools/nav_result.py`,
`code_atlas/tools/read_symbol.py`, `code_atlas/tools/find_references.py`, `code_atlas/tools/impact.py`,
`tests/test_record_attributes.py`, `tests/test_agent_brief_usage_completeness.py`, `docs/TOOLS.md`. Working doc: this
file.

## Phase 5 — finalise

**Durable lesson.**

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`

- 413-C1 `validate-a-parameter-before-the-first-return` (code, new): a parameter refused deep in one answer path
  is ignored on every path that returns before it; `read_symbol` has eight.

### Outward actions

Under the handover: push `feat/413-record-attributes`; open its PR against `feat/412-records-direct-first`.
Deferred to the maintainer: merge after #110.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 56,746 |
| 3 execute | `implementer` — not dispatched; main loop implemented | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | ticket-blind `challenger` | 1 | 61,952 |

`LEDGER TOTAL: 118,698 · top cost driver: 4 review / challenger` — main loop unmeasured.
