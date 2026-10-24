---
id: 410
slug: column-readers
title: "`READS` onto a `Table::Column` — who reads this column (reopens 390 W3)"
phase: 2
milestone: Coverage
status: in-progress
depends_on: [390, 329]
---

## Why this exists

Issue [#102](https://github.com/cuongdinhngo/code-atlas/issues/102), 2026-10-24. 390 W3 shipped as
*ASSUMED (awaiting ratification): a `SELECT`'s source is a table; a column subject's readers are not
modelled.* Four anchor PRs in 20–23 Oct asked the column question (`InjuryInformation.HasLocation`,
a search's `gender`, `GBE_RULES`), each a data-fix migration whose risk was *which screens and
reports change*. Today `find_references(<Table::Column>, kinds=["READS"])` lands in `kinds_ignored`
(`find_references._kinds_ignored`). **W3 is reopened by this field evidence.**

## Scope

1. T-SQL routines and views: `READS` onto a `Column` when it appears in the select list, `WHERE`,
   `JOIN … ON` or `CASE` of a `SELECT` whose `FROM`/`JOIN` source is its table, alias-resolved —
   `RESOLVED`.
2. Host strings 390 already reads as `SELECT … FROM t` (PHP/TS/Python): an identifier matching a
   column of `t`, or `alias.col` — `HEURISTIC`. Language spec only (R2).
3. `find_references(<Table::Column>, kinds=["READS"])` lists them; `READS` on the table unions the
   column reads, as `WRITES` does (329).
4. `select *` counts as a table read only and says so (`column_reads_unknown`) — the column answer
   never claims completeness it lacks.

Contract: new edges onto an existing kind; decide in design whether that is a `contract_version`
bump (R3). Out of scope: runtime-built SQL; PHP views reading `$row['col']` (a model→view trace).

## Acceptance criteria

- AC1: A view selecting `t.flag` and a proc filtering `WHERE flag = 1` both appear as `RESOLVED`
  readers of `t::flag`; a proc reading only `t.other` does not.
- AC2: A PHP string `SELECT flag FROM t` is a `HEURISTIC` reader of `t::flag`.
- AC3: A `select *` reader is counted in `column_reads_unknown`, not listed as a column reader.
- AC4: Table-level `READS` answers are unchanged except for the union; P8 counts re-floored.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 410 · **work_doc_mode:** embed · **Current phase:** 2 design · **Next action:** execute. **Revert path:** `git revert` the branch's commits (a contract bump: an index built at 19 needs a full rebuild after a revert).
- `TRACK: backend` · Run mode: `autorun 408 - 409 - 410 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/410-column-readers`, **stacked on `feat/409-measured-zero-callers`** (#105). Contract `.mango/run-contract-410.txt`.
  RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 16 unresolved surfaced | 8 want-decision asked | 8 how-decision resolved+cited | 8 ASSUMED | skip: no`

**Premise.** `find_references`, `kinds_ignored`, `READS`, 390 W3, 329's union, the `Table::Column` qname, the three host
string readers (`SqlLiteral.php`, `sqlLiteral.js`, `sql_literal.py`) and the T-SQL scanner resolve. Ambiguous: "a
column of `t`" in a host string — an adapter sees one file and no column list (R3.3), so "matching" can only mean "an
identifier the statement uses as one".
Recall (type 2, by handle — the change widens a target that several reads share): 362-C1
`widen-every-query-that-shares-the-page`; 363-C1 `a-zero-must-count-what-the-search-cannot-see`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 72,335 tokens) raised sixteen items, settled below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where alias and column binding live | how | the adapter: it already reads aliases (`ddl.aliasSourceTable`, `ddl.js:601`) and emits `T::col` for a column write (`scan.js:621`); the resolver links the raw as it links a write (R3.3) |
| H2 | case and quoting | how | as a column write: the text as written, brackets dropped; the resolver's unique-casefold pass links it (`resolver.py:263`) |
| H3 | the edge's line | how | its table's `READS` line, so 329's by-statement grouping folds a table read and its columns into one row |
| H4 | a view body | how | as 402: the view is the reader (`scan.js:950`) |
| H5 | the Table answer | how | unchanged path: `_writes_targets` already unions the table's columns and groups by statement (`find_references.py:165`); a statement's row gains `columns` |
| H6 | `kinds_ignored` / `_unlinked_counts` | how | `READS` on a Column is no longer ignored; unlinked column reads are not counted (a Column answer counts what it could not attribute instead, W6) |
| H7 | other consumers (`impact`, orphans, the map) | how | they see the new edges, as 390 H10 accepted for table reads; P8 re-measures the counts |
| H8 | case of `select *` / `t.*` | how | no column edge; the statement counts in W6 |
| W1 | contract bump | want | **ASSUMED (awaiting ratification):** yes — contract 19, release 0.8.0 (R3.1/R3.5: a new target shape on an existing kind is a vocabulary change a pre-410 index cannot answer; the bump makes it rebuild rather than answer "no readers"). The `v0.8.0` tag is the maintainer's |
| W2 | an unqualified column beside several sources | want | **ASSUMED (awaiting ratification):** not attributed — only a statement with one source binds a bare name; in a `JOIN` only `alias.col` / `table.col` bind. Precision over recall: a wrong reader on a data-fix question is worse than an unlisted one, and W6 counts what was skipped |
| W3 | host strings | want | **ASSUMED (awaiting ratification):** 390 W4 kept — the first `FROM` only; `alias.col` / `t.col`, and bare names when the string holds no `JOIN` and one `FROM`; `HEURISTIC` |
| W4 | what is not a column | want | **ASSUMED (awaiting ratification):** a keyword, a name followed by `(` (a call), a name after `AS` (an alias or a type), a parameter (`@x`, `:x`, `?`), a temp (`#t`), the source's own name and alias, anything inside a quoted string |
| W5 | CTE, derived table, view-through | want | **ASSUMED (awaiting ratification):** not followed — a column read through them is not its base table's |
| W6 | `column_reads_unknown` | want | **ASSUMED (awaiting ratification):** on a Column subject asked `READS`: the statements that read its table and attributed no column of it (a `select *`, W2's bare names, a host string no column was read from); omitted at 0, as the unlinked counts are |
| W7 | other completeness caveats | want | **ASSUMED (awaiting ratification):** W6 plus 390's `reads_emitters_only`; runtime SQL and `$row['col']` stay out of scope (the ticket) |
| W8 | P8 | want | **ASSUMED (awaiting ratification):** floors move by design (more `READS` rows); re-measured per AGENT_BRIEF P8 in this PR |

## Phase 1 — analysis

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=4 G=1 AC=4`
`CLARIFICATION: 16 raised | 16 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/30 touched files under UI paths`
`SCOPE: L`
`TIER: full`
`STRUCTURE: native`

W1–W8 count as self-resolved because the handover handed them back; each stands `ASSUMED` for the maintainer.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "W3 is reopened by this field evidence" | `find_references(<Table::Column>, kinds=["READS"])` lists the column's readers | ✅ |
| C1 | Scope, contract | "decide in design whether that is a `contract_version` bump (R3)" | W1 | ✅ |
| C2 | Out of scope | runtime SQL, `$row['col']` | untouched | ✅ |
| R1 | Scope 1 | T-SQL routines and views, select list / `WHERE` / `JOIN … ON` / `CASE`, alias-resolved, `RESOLVED` | the scanner binds columns (W2, W4, W5) | ✅ |
| R2 | Scope 2 | host strings, `HEURISTIC` | the three readers (W3) | ✅ |
| R3 | Scope 3 | Column answer lists them; Table answer unions | H5, H6 | ✅ |
| R4 | Scope 4 | `select *` → `column_reads_unknown` | H8, W6 | ✅ |
| AC1 | AC1 | a view selecting `t.flag` and a proc with `WHERE flag = 1` are `RESOLVED` readers; a proc reading only `t.other` is not | SQL adapter fixture | ✅ |
| AC2 | AC2 | a PHP `SELECT flag FROM t` is a `HEURISTIC` reader | the shared literal table, all three host adapters | ✅ |
| AC3 | AC3 | `select *` counted, not listed | W6 | ✅ |
| AC4 | AC4 | table answers unchanged but the union; P8 re-floored | H5, W8 | ✅ |

### AC validation

| AC | Falsifiable? | Definition |
|---|---|---|
| AC1 | yes | `find_references(t::flag, kinds=["READS"])` lists the view and the proc at `RESOLVED`, not the `t.other` proc |
| AC2 | yes | each of the three adapters emits `READS t::flag` at `HEURISTIC` on the literal's line (`sql_literal_cases.json`) |
| AC3 | yes | a `select * from t` routine is not listed on `t::flag` and `column_reads_unknown == 1` |
| AC4 | yes | `find_references(t, kinds=["READS"])` lists the same statements as before, one row each, with `columns`; P8 manifest re-floored |

**Inventory — R2 (N = 3):** 1 PHP · 2 TypeScript · 3 Python. Review confirms each.

### Gap analysis (enhancement)

- Current: `READS` targets a Table only (`scan.js:657`, the host readers' `read()`); `find_references` ignores `READS`
  on a Column (`find_references.py:155`).
- Target: column `READS` from both sources, answered on the Column and folded into the Table's statements.

**Blast radius.** `adapters/sql/src/{ddl,scan}.js`; the three host readers and their callers
(`Visitor.php:352`, `parse.js:632`, `parse.py:1129`); `contract.py` and the four adapter handshakes (19); the tests
that pin the contract version; `find_references.py`, `store.py`; `gen_skill.py` (the brief's `READS` line) and its
generated files; TOOLS.md, PLAN, CHANGELOG (release 0.8.0), `pyproject.toml`, the plugin manifests.

### BASELINE

`BASELINE: green — scripts/gate.sh at the stacked base: 21 passed · 0 failed · 0 skipped, GATE GREEN`

Ran at 9b9c25e754d4fdec4f3c8b3c60c2d644d6ee1736 (409's final gate; the base tip adds only that gate's record).

### Rule sections

`RULE SECTIONS: 11 applicable — 11 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the core reads a Column kind, never a language · §R2.1 (change-type) ✅ the readers encode T-SQL's grammar (FROM, JOIN, AS, a call's paren) · §R2.2 (change-type) ✅ no repo or framework name · §R3.1 (change-type) ✅ contract 19 + conformance + release 0.8.0 (W1) · §R3.3 (change-type) ✅ adapters emit bare T::col; the resolver links · §R3.4 (change-type) ✅ tests/contract runs on every adapter · §R4.2 (change-type) ✅ columns emitted in first-seen order, deduplicated · §R5.2 (change-type) ✅ RESOLVED in T-SQL bodies, HEURISTIC in host strings · §R5.6 (change-type) ✅ column_reads_unknown separates "no reader" from "not attributed"; a test drives both · §R6.2 (change-type) ✅ the construct inventory is the shared literal table plus the scanner's cases · §R7.6 (change-type) ✅ the brief's READS line and TOOLS.md are edited in place`

## Phase 2 — design

### Approach

1. **T-SQL** (`ddl.js`): `readColumnReads(code, sources, bare)` → `{table, column}[]`. An alias map from every
   `FROM` / `JOIN` source (`[AS] alias`); a dotted chain `q.c` binds `c` when `q` is an alias or a source's name
   (last part or whole); a bare name binds to the one source when `bare` and the statement has exactly one, scanned
   from the first `SELECT` on, never W4's non-columns. `scan.js` `reads()` emits `READS T::col` `RESOLVED` on the
   table's line; `bare` is true only for a pure `SELECT` / view body (never an `INSERT … SELECT`, whose column list
   is the target's).
2. **Host strings**: the same rule in each reader — `SqlLiteral::columns`, `readSqlColumns`, `sql_literal.columns`
   (text, closed) → names for the first `FROM`'s table; each caller emits `READS target::col` `HEURISTIC` on the
   statement's line. Bare names only when the string has no `JOIN` and one `FROM`. `sql_literal_cases.json` gains an
   `expect.columns` list and the agreement test reads it.
3. **Contract 19** (`contract.py` comment + constant, four handshakes, the conformance pins).
4. **Core**: `_kinds_ignored` no longer ignores `READS` on a Column; `store.count_table_reads_without_columns(table,
   columns)`; a Column answer asked `READS` carries `column_reads_unknown` when > 0; docstring.
5. **Release 0.8.0**: CHANGELOG heading (rebuild + adapter flags), `pyproject.toml`, the plugin manifests, the strict
   tag xfail 399 used.
6. **Docs**: TOOLS.md, the brief's `READS` line (`gen_skill.py`, regenerated), PLAN's handshake version, the
   playbook if it pins 18.
7. **P8**: `scripts/cross_repo_validate.py --public-only`; re-floor what moved by design.

### Rejected alternatives

- **Fan a bare name out to every source at `HEURISTIC`** — W2: a non-column of each source stays an unlinked edge,
  and a column of the wrong source is a false reader.
- **Bind columns in the core against `CONTAINS`** — the core would re-parse statements it never sees (R1.4); the
  adapter has the text.
- **A new `READS_COLUMN` kind** — two words for one relation; the Table union would need both.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| the resolver links `T::col` for any FQN kind as it does for `WRITES` | verified | `READS` ∈ `FQN_EDGE_KINDS` (`contract.py:111`); column writes link the same way (`scan.js:621`) |
| one row per statement on a Table answer | verified | 329's `write_statements_by_targets` groups by source, file, line |
| the scanner's buffer has its string literals masked | novel-untested (own code) | asserted by a proc whose `WHERE` compares to a string literal |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | column binding | `adapters/sql/src/ddl.js`, `adapters/sql/src/scan.js` | the SQL contract fixture, cross-repo SQL samples | R1, AC1 | 2/2 |
| 2 | host readers | `adapters/php/src/{SqlLiteral,Visitor}.php`, `adapters/typescript/src/{sqlLiteral,parse}.js`, `adapters/python/src/{sql_literal,parse}.py` | PHPStan max, tsc strict, mypy strict on each | R2, AC2 | 6/6 |
| 3 | contract 19 | `code_atlas/contract.py`, four `index.*` handshakes, version-pinning tests | every fake adapter speaking 18 | C1 | — |
| 4 | the Column answer | `code_atlas/tools/find_references.py`, `code_atlas/store.py` | Table/Column `kinds` tests (390) | R3, R4, AC3, AC4 | 2/2 |
| 5 | tests | `tests/test_column_readers.py` (new), `tests/contract/sql_literal_cases.json`, `tests/contract/test_sql_literal_agreement.py` | — | AC1–AC4 | 3/3 |
| 6 | release 0.8.0 | `CHANGELOG.md`, `pyproject.toml`, the plugin manifests (via `gen_skill.py --write`), `tests/test_release_discipline.py` | release-discipline tests | C1 | — |
| 7 | docs | `docs/TOOLS.md`, `scripts/gen_skill.py` + generated files, `docs/PLAN.md`, `docs/ADAPTER_PLAYBOOK.md` | doc size budgets, skill drift | G1 | — |
| 8 | P8 | `scripts/cross_repo_samples.json` | the weekly cross-repo job | AC4 | 1/1 |
| 9 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `widen-every-query-that-shares-the-page` — traced: `rtk proxy grep -n "READS in kinds\|_writes_targets(" code_atlas/tools/find_references.py`
  → `150: if READS in kinds and subject_kind == TABLE_KIND:` (the unlinked count, Table-only — kept, H6) and the
  `_writes_targets` call that already feeds the page, the total and the subtrees from one target list; the Column
  answer gains its own reads through the same list, so no read behind the page is left on the table alone.
- `a-zero-must-count-what-the-search-cannot-see` — traced: the same grep shows no count of unattributed statements
  today; W6's `column_reads_unknown` is that count.

### Rule compliance

The eleven sections of Phase 1 bind the design. R7.5 binds every comment; R6.6 (PHPStan max, tsc strict, mypy
strict) binds the three host readers.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — SQL adapter, resolver, tool | a real build of a `.sql` fixture through the SQL adapter, `find_references` | authored | ✅ |
| AC2 | integration — each host adapter's `--file` mode | the shared literal table, three adapters | authored | ✅ |
| AC3 | integration | a `select *` routine in the AC1 build | authored | ✅ |
| AC4 | integration + runtime (samples) | the AC1 build's table answer; `cross_repo_validate.py --public-only` | real-corpus (public samples) | ✅ |
| W4 bias | heuristic — input-shape-dependent | the cross-repo SQL samples' column-read counts, linked vs unlinked | real-corpus | ✅ (E1 below) |

**Coverage-gap exclusion E1 — the anchor's column questions.** item: the four field questions (`HasLocation`, the
search's `gender`, `GBE_RULES`) answered on the anchor index · risk tier: medium (usefulness on the field's query
shapes) · why deferred: the anchor is a private client repo this run does not read · follow-up: the maintainer
replays them after a full rebuild at contract 19 · expiry: when the maintainer has run `find_references` on those
three columns on a contract-19 anchor index · seen: 410.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 1 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_column_readers.py tests/contract/test_sql_literal_agreement.py`

### Rollback

`git revert`; a contract-19 index needs a full rebuild after a revert. One repo; the adapters ship in it.

`SCOPE: L` — the analysis baseline; the realized scope is the ticket's own (three host readers named in Scope 2).
