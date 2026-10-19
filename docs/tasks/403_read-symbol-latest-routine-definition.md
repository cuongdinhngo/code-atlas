---
id: 403
slug: read-symbol-latest-routine-definition
title: "`read_symbol` on a routine several migrations redefine refuses as ambiguous instead of answering the latest"
phase: 2
milestone: Retrieval
status: todo
depends_on: [394]
---

## Why this exists

From the anchor project's Round-3 feedback: three PRs read a procedure that Flyway-style migrations redefine
(`CREATE OR ALTER`), and got `subject_ambiguous` (or `path_excluded` under a `path_prefix`). They fell back to
`Read` on the newest migration. On `main`, more than one definition always refuses (`read_symbol.py:289-292`);
394's `test_copies` precedence is the only tie-break.

## Scope

1. When every competing definition of a routine is a migration-ordered redefinition, `read_symbol` answers the
   latest one and lists the rest (as `aliases` / `implemented_by` do). The ordering comes from the migration
   tool's standard naming (R2.1), never a repo's paths.
2. A genuine ambiguity, such as two schemas or two unordered files, still refuses.

## Acceptance criteria

- **AC1:** `V1__x.sql` and `V7__x.sql` both define `dbo.P`: `read_symbol dbo.P` returns V7's body, naming V1.
- **AC2:** two unordered definitions still answer `subject_ambiguous`.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 403 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews the PR (stacked on 402's); merging is theirs. **Revert path:** `git revert` the branch; `extra.migration_version` is then ignored, and a `--full` build drops it.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun 403` — `REVIEWER: OFF` (waived, "with skipped reviewer") · `CHALLENGER: ON`.

## Phase 0 — refine

`PREMISE: 2 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 5 unresolved surfaced | 0 want-decision asked | 5 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** `read_symbol.py:289-292` (two definitions refuse) and 394's `test_copies_first`
(`symbol_pointers.py:114`), the only tie-break, both resolve at 8c0ddd00.

**Recall.** `widen-every-query-that-shares-the-page` (362-C1): `search_symbol` reorders the same rows by 394's
rule, so a new precedence must reach it too.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | which naming standard | how | Flyway's versioned migration, `V<version>__<description>.sql`, version parts split on `.` or `_` and compared as numbers — the convention the field PRs used. Repeatable (`R__`) and undo (`U`) scripts carry no order and stay unversioned |
| H2 | who knows the standard | how | the SQL adapter, as R2.1 puts ecosystem standards in adapters: it stamps `extra.migration_version`. The core compares dotted integers and names no tool or language (R1.1) |
| H3 | contract | how | an adapter-emitted `extra` key, as `extra['type']` was in v7, so it rides 402's unreleased v17 (`contract.MIGRATION_VERSION_KEY`); no second bump |
| H4 | which kinds | how | routines, triggers and views: a `CREATE OR ALTER` replaces the whole object. A `Table` is not stamped: an `ALTER TABLE` amends, so its latest migration is not its definition |
| H5 | genuine ambiguity | how | any unversioned row, a tied version, or a cut fetch leaves the rows as they are, so the refusal stands (AC2) |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=2 G=1 AC=2`
`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### Root cause

`config.cause_taxonomy` class: **logic**. A multiplicity test with one tie-break (394's test copies) read every
other multiplicity as ambiguity, and the graph held nothing that ordered a redefinition.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "fell back to `Read` on the newest migration" | the newest answers in the tool | ✅ |
| R1 | Scope 1 | "answers the latest one and lists the rest" | the highest version, `ambiguity: "migration_redefinitions"`, the rest under `ambiguous_definitions` | ✅ |
| R2 | Scope 2 | "A genuine ambiguity … still refuses" | H5 | ✅ |
| C1 | R2.1 | "the migration tool's standard naming, never a repo's paths" | H1, H2 | ✅ |
| C2 | R1.8 | — | one rule (`one_definition_first`) for read_symbol's two sites and search_symbol | ✅ |
| AC1 | AC | "returns V7's body, naming V1" | V7's source, V1 listed | ✅ |
| AC2 | AC | "two unordered definitions still answer `subject_ambiguous`" | refused | ✅ |

`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ only the adapter knows Flyway · §R2.1 (change-type) ✅ Flyway's documented naming · §R3.1 (change-type) ✅ rides v17 (H3) · §R5.6 (change-type) ✅ a tie or an unversioned row still refuses · §R6.5 (change-type) ✅ the proving test observed red on main · §R1.8 (recalled handle 362-C1) ✅ one shared callable`

## Phase 2 — design

**Approach.** The SQL scanner reads the file name once (`MIGRATION_FILE_RE`) and stamps `migration_version` on
routine, trigger and view nodes. `symbol_pointers` gains `latest_migration_first` and `one_definition_first`:
test copies first (394), then the versioned order. `read_symbol`'s two multiplicity sites and `search_symbol`'s
page grouping call it, and the label it returns is the `ambiguity` value.

**Rejected.** Matching `V…__` on paths in the core: R1.1 and R2.1 put a tool's naming in its language's adapter.

| # | Change | File | Covers |
|---|---|---|---|
| 1 | the stamp | `adapters/sql/src/scan.js` | H1, H2, H4 |
| 2 | the key | `code_atlas/contract.py` | H3 |
| 3 | the rule | `code_atlas/tools/symbol_pointers.py` | R1, R2, C2 |
| 4 | readers | `code_atlas/tools/read_symbol.py`, `code_atlas/tools/search_symbol.py` | R1, C2 |
| 5 | proving test | `tests/test_read_symbol_latest_migration.py` (new) | AC1, AC2 |
| 6 | docs | `docs/TOOLS.md`, `adapters/sql/README.md`, `CHANGELOG.md` (0.6.0) | R7.2 |
| 7 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | R7.2 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- 362-C1 → traced: `search_symbol`'s 394 grouping now calls the shared rule (`test_search_lists_the_latest_first_with_the_same_label`).

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1, AC2 | integration — the real SQL adapter, a full build, the tools | `tests/test_read_symbol_latest_migration.py` | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test.** `pytest -q tests/test_read_symbol_latest_migration.py`.

## Phase 3 — execute

Branch `fix/403-read-symbol-latest-routine-definition`, stacked on `feat/402-sql-view-nodes` (it rides 402's
contract 17). **Red first** on `main` (8c0ddd00): `4 failed, 2 passed` — the two passing are the refusals AC2 keeps.
**Green:** `6 passed`. `ruff`, `mypy` (103 files) and the SQL adapter's `tsc --checkJs` clean.

**Found during execute.** 394's `_attach_pointers` listed the other definitions through
`attach_ambiguous_definitions`, which attaches only past one site, so a labelled answer with one other definition
named none: AC1's "naming V1" failed. A labelled answer now always lists them; this fixes 394's one-copy case too.

Axis 1 (the diff ⊆ the change list): rows 1–7. Axis 2: the approach as designed.
