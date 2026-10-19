---
id: 402
slug: sql-view-nodes
title: "A T-SQL view is not in the graph, so its definition, its predicate and its redefinitions answer nothing"
phase: 2
milestone: Coverage
status: todo
depends_on: [390]
---

## Why this exists

From the anchor project's Round-3 feedback (2026-09-20 → 10-18). Four PRs asked a view question, and each was
answered from the live DB or `git grep`: what filters this view, which migrations redefine it, what a view reads.
On `main` the SQL adapter emits no node for `CREATE VIEW` (no `view` in `adapters/sql/src`), so `search_symbol`,
`read_symbol` and `find_references` have nothing to answer with. `search_symbol`'s `altered_by` covers only
`Table` and `Function` (`search_symbol.py:70`).

## Scope

1. The SQL adapter emits `CREATE` / `ALTER` / `CREATE OR ALTER VIEW` as a node, following T-SQL's grammar
   (R2.1). The kind is chosen in design: a new kind bumps `contract_version` (R3).
2. A view's `SELECT … FROM` sources are `READS` edges, as a routine's are (390).
3. `altered_by` covers views.

## Acceptance criteria

- **AC1:** a fixture view is found by `search_symbol` and read by `read_symbol`.
- **AC2:** `find_references(<table>, kinds=["READS"])` lists the view.
- **AC3:** two migrations that redefine one view both appear in its `altered_by`.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 402 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews the PR (stacked on 401's), merges in order, and tags `v0.6.0`. **Revert path:** `git revert` the branch, then `code-atlas-build --full` (the contract moves back to 16).
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 402` — `REVIEWER: OFF` (waived, "with skipped reviewer") · `CHALLENGER: ON`.

## Phase 0 — refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 5 unresolved surfaced | 0 want-decision asked | 5 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** No `view` in `adapters/sql/src` at 8c0ddd00 (the scanner's `CREATE_RE` takes `proc|function`), a view
body's reads are the file's (README, 390), and `_ALTERED_KINDS = (Table, Function)` (`search_symbol.py:70`).

**Recall.** `widen-every-query-that-shares-the-page` (362-C1): every reader of the kind the view joins must be
enumerated. `keep-first-hides-the-later-declaration` (384-C1).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the kind | how | a new `View` kind, contract 17. `Table` + `extra.object_type` (the trigger precedent) was rejected: `read_symbol` replaces a Table's source with its columns (`read_symbol.py:635`), the ER map draws every Table (`generate_onboarding.py:127`), and a Table subject's writer set walks its CONTAINS — each would need a view branch |
| H2 | which statements are ALTERS | how | `ALTER VIEW` and `CREATE OR ALTER` / `OR REPLACE VIEW` redefine, so each is an `ALTERS` edge from its file, as 321's literal `ALTER TABLE` is. A plain `CREATE VIEW` creates and is not one (AC3's two migrations both redefine) |
| H3 | the view's body | how | the view is `current` until `GO` or the next routine, so its SELECT's sources are READS from the view (`reads` uses `current`) — T-SQL makes a view the only statement of its batch |
| H4 | release | how | R3.1: contract 17 cuts release 0.6.0, *Full rebuild required* and *Adapter checkout must be updated*; the tag is the maintainer's (381 E3) |
| H5 | the consumers of `Table` | how | unchanged by construction (H1); `View` joins `_ALTERED_KINDS` only |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=3 G=1 AC=3`
`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### Root cause

`config.cause_taxonomy` class: **data** (vocabulary). The adapter had no construct for a view, so the graph held
nothing for a tool to answer with.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "what filters this view, which migrations redefine it, what a view reads" | each answerable from the index | ✅ |
| R1 | Scope 1 | "emits `CREATE` / `ALTER` / `CREATE OR ALTER VIEW` as a node" | `View` (H1), the three spellings | ✅ |
| R2 | Scope 2 | "sources are `READS` edges, as a routine's are" | READS from the view (H3) | ✅ |
| R3 | Scope 3 | "`altered_by` covers views" | `View` in `_ALTERED_KINDS`, ALTERS per H2 | ✅ |
| C1 | R3.1 | — | contract 17, conformance cases, release 0.6.0 | ✅ |
| C2 | R2.1 | — | T-SQL's own grammar; no repo's names | ✅ |
| AC1 | AC | "found by `search_symbol` and read by `read_symbol`" | top hit `dbo.ActiveOrders` / `View`; the source holds the predicate | ✅ |
| AC2 | AC | "`find_references(<table>, kinds=["READS"])` lists the view" | the view, never its file | ✅ |
| AC3 | AC | "two migrations that redefine one view both appear in its `altered_by`" | `V1__…` and `V7__…` | ✅ |

`RULE SECTIONS: 7 applicable — 6 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ no language branch: the core reads the kind · §R2.1 (change-type) ✅ T-SQL's CREATE / ALTER / CREATE OR ALTER VIEW · §R3.1 (change-type) ✅ contract 17 + conformance + release 0.6.0 · §R3.4 (change-type) ✅ two SQL conformance cases (create-view, alter-view) · §R6.2 (change-type) ✅ the second spelling is its own case · §R6.5 (change-type) ✅ the proving test observed red on main · §R1.8 (recalled handle 362-C1) ✅ every Table consumer enumerated, none branches on View`

## Phase 2 — design

**Approach.** `contract.py` adds `View` (v17) and `VIEW_KIND`. The SQL scanner's `VIEW_RE` matches the three
spellings and emits a `View` node, a CONTAINS from the file, an ALTERS for a redefinition (H2), and makes the view
`current`, so its SELECT, on that line or the next, reads as the view. `search_symbol._ALTERED_KINDS` adds `View`.
Every adapter's handshake says 17. Release 0.6.0.

**Rejected.** `Table` + `extra.object_type = "view"` (H1).

| # | Change | File | Covers |
|---|---|---|---|
| 1 | the kind | `code_atlas/contract.py` | R1, C1 |
| 2 | `altered_by` | `code_atlas/tools/search_symbol.py` | R3 |
| 3 | the construct | `adapters/sql/src/scan.js` | R1, R2, H2 |
| 4 | handshakes | `adapters/{php,python,sql,typescript}/index.*` | C1 |
| 5 | conformance | `tests/contract/adapter_registry.py`, `tests/fixtures/sql/{create,alter}_view.sql` | C1 |
| 6 | count pins (P5) | the tests pinning `CONTRACT_VERSION`, the node-kind tuples, the vocabulary count | C1 |
| 7 | proving test | `tests/test_sql_view_nodes.py` (new) | AC1–AC3 |
| 8 | release | `pyproject.toml`, plugin/marketplace JSON, the generated hook tables, `tests/test_release_discipline.py`'s untagged marker, `CHANGELOG.md` | H4 |
| 9 | docs | `docs/CONVENTION.md` §3, `adapters/sql/README.md` | C1 |
| 10 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | R7.2 |

`HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- 362-C1 → traced: the consumers of `Table` under `code_atlas/` (resolver, check_column_defaults, find_references, generate_onboarding, nav_result, read_symbol, search_symbol) keep their behaviour because a view is not a Table; only `_ALTERED_KINDS` widens.
- 384-C1 → does not apply: no per-row derived value is added; a view's body hash already spans every declaration of its qname (`bodyHash.js` `qnameSpans`).

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC3 | integration — the real SQL adapter, a full build, the tools | `tests/test_sql_view_nodes.py` | authored (stand-in names) | ✅ |
| C1 | adapter conformance | `tests/contract` SQL cases | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test.** `pytest -q tests/test_sql_view_nodes.py`.

## Phase 3 — execute

Branch `feat/402-sql-view-nodes`, stacked on `fix/401-refused-refresh-in-status` (5848b846) so the release carries
400 and 401's changelog lines. **Red first** on `main` (8c0ddd00): `3 failed` — no hit, the reader is the file
`db/schema.sql`, and `kind="View"` is unknown. **Green:** `3 passed`; the SQL conformance, contract-schema,
sole-source, alters, doc-budget and release suites pass (WSL, PHP-dependent cases excluded: this host's PHP is 7.4).
`ruff`, `mypy` (103 files) and the SQL adapter's `tsc --checkJs` are clean.

**Found during execute.** Eleven more `CONTRACT_VERSION == 16` pins than the first sweep found (P5): the first
grep went through a filtering shell wrapper. `CONVENTION.md` crossed its budget by 4 tokens; the `ALTERS` line was
cut back. A PLAN §19 line for H1 put PLAN 49 tokens over its ceiling, so the decision lives in `contract.py`'s v17
comment and here instead (R7.6).

Axis 1 (the diff ⊆ the change list): rows 1–10. Axis 2: the approach as designed.
