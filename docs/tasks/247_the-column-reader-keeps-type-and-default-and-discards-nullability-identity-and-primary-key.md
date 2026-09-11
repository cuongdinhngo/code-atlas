---
id: 247
slug: the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key
title: 'The SQL column reader keeps a column''s type and DEFAULT and discards its nullability, IDENTITY and PRIMARY KEY — so the first question anyone asks of a schema has no answer at any price'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [022, 228, 239]
---

## Why this exists (field retro — the anchor repo, 2026-09-11, round 17)

A consuming agent graded the round **6.5/10** and named one dimension as the whole of the gap:
symbol questions were answered well and honestly, schema questions were not answered at all. The
single most-repeated question of the review — *"what type is this column, and does this table have a
single-column integer primary key?"* — was asked about ten tables, roughly six times, and code-atlas
answered it **zero times**. All of it went by `grep` over DDL.

The retro's reading of why was that the data is in the index and no tool opens a door to it. That is
half right, and the half that is wrong is this ticket. **Type is captured. Nullability, IDENTITY and
PRIMARY KEY are never parsed**, so no read path could surface them however it were written.

Measured on the anchor index (read-only) — 20,808 `Column` nodes, 20,000 sampled:

```
extra keys across 20,000 Column nodes:
  data_type  19,979
  type       19,979
  default     6,975
  (nothing else)
```

Three keys. No `nullable`, no `identity`, no `primary_key`, no ordinal.

**A verification pass on 2026-09-11 found two more losses in the same reader**, both of which remove
the fallbacks a consumer would otherwise use to recover declaration order:

```
tables whose columns ALL share one line_start:  1348 / 1548
  dbo.ContractAssets   585 cols, 1 distinct line (13)
  dbo.AwardStructure     173 cols, 1 distinct line (13)
  dbo.Member_Site       316 cols, 8 distinct lines    <- multi-statement ALTER, not per-column
```

Every column of a `CREATE TABLE` is emitted at the line of the `CREATE` statement itself, so a
`Column` node's position is its table's position. And `_NODE_ORDER` is
`qualified_name, file_path, line_start, id` (`store.py:169`), so `file_outline` returns a table's
columns **alphabetically** — correct and R4.2-deterministic, but it means neither the line nor the
row order carries the DDL's column order. A consuming agent confirmed both in the field: *"the order
returned is alphabetical, not declaration order — I have no way to know the real column order. And
all 7 columns report line_start: 13, the same line as the Table node, so the position is meaningless
too."* Declaration order is currently **unrecoverable from the index at any price**, which also makes
a primary-key ordinal unverifiable against it.

## Root cause

`readColumnDef` (`adapters/sql/src/ddl.js:140`) reads exactly four things out of a column
definition: the name, the data type (with its size parens), the `DEFAULT` expression, and an inline
`REFERENCES` clause. Everything else in the T-SQL `column_definition` grammar — `NULL` / `NOT NULL`,
`IDENTITY(seed, increment)`, an inline `PRIMARY KEY`, `UNIQUE`, `ROWGUIDCOL` — is read only as a
boundary marker for the `DEFAULT` expression (`AFTER_DEFAULT`, `ddl.js:22-26`) and then dropped.

The table-level declaration is worse than unmodelled: it is **deliberately discarded**. `NOT_A_COLUMN`
(`ddl.js:10-12`) makes `readColumnDef` return `null` for any entry whose first word is `primary`,
`unique`, `foreign`, `constraint`, `key` or `index`. That guard is correct — those entries are not
columns — but nothing else reads them, so `PRIMARY KEY ([ID] ASC)` is parsed, recognised, and thrown
away. The composite/single distinction the retro asked for lives entirely in the list that guard
drops.

`scan.js:517` is the second loss: `for (const col of ddl.readColumns(body.body)) column(qname, col, line)`
passes **one** `line` — the `CREATE` statement's — for every column in the body. `readColumns`
(`ddl.js:295`) splits the body on top-level commas and never tracks an offset, so the per-column line
is not available to pass.

This is not a `get_index_status` honesty defect. The `sql` stamp declares `declared_types: true`,
which is true — `data_type` is captured. There is no flag claiming the other three, so nothing
lied; the capability simply does not exist.

## Scope

Extend the T-SQL DDL reader to capture, on each `Column` node's `extra`:

1. **`nullable`** — from an explicit `NULL` / `NOT NULL` in the column definition. Absent when the
   definition states neither: SQL Server's default nullability depends on session settings
   (`ANSI_NULL_DFLT_ON`) that no static reader can know, so an omitted clause must stay **omitted**,
   never defaulted to `true` (R5.6 — an unmeasured thing is not a value).
2. **`identity`** — presence, plus seed and increment when the DDL gives them.
3. **Primary-key membership and ordinal** — from *both* spellings: the inline `PRIMARY KEY` on a
   column definition, and the table-level `PRIMARY KEY (c1, c2, …)` / `CONSTRAINT x PRIMARY KEY (…)`
   entry that `NOT_A_COLUMN` currently drops. The ordinal is what makes a single-column key
   distinguishable from the first column of a composite one.
4. The same for `ALTER TABLE … ADD CONSTRAINT … PRIMARY KEY (…)`, which is how a large share of real
   schemas declare the key — `scan.js:529` already routes `ALTER` through `readColumnDef`.

## Constraints

- **R2 — standard over sample.** Encode the T-SQL `column_definition` and `table_constraint` grammar,
  not the shape of any one repo's tables. The anchor index is the measurement, never the spec.
- **No `CONTRACT_VERSION` bump.** These are `extra` keys, and `extra` is the free-form seam 236 used
  for the same reason (`contract.py`: the FK's child/referenced tables ride `extra` "since
  NODE_FIELDS is frozen"). No kind moves and no qname changes, so R3.1's trigger does not fire.
  A full rebuild is still needed to populate the new keys on an existing index — state that in the
  ticket's close-out rather than letting a reader assume incremental pickup.
- **Dialect honesty (228).** The SQL adapter owns every `.sql` file and reads one dialect. A MySQL
  or Postgres `AUTO_INCREMENT` / `GENERATED … AS IDENTITY` is not T-SQL `IDENTITY`; capture what the
  reader actually understands and leave the rest absent rather than guessing a cross-dialect mapping.
- **Omit-when-absent (061).** A column whose DDL declares none of these carries none of these keys.
  No `nullable: null`, no `identity: false` on every column in the graph.

## Acceptance criteria

- **AC1** A `CREATE TABLE` with `[ID] int IDENTITY(1,1) NOT NULL PRIMARY KEY` yields one `Column`
  node carrying nullability, identity (seed 1, increment 1) and a primary-key ordinal of 1.
- **AC2** A table-level `CONSTRAINT PK_x PRIMARY KEY ([A] ASC, [B] ASC)` marks exactly `A` and `B`
  with ordinals 1 and 2, and marks no other column. The `NOT_A_COLUMN` guard still emits no `Column`
  node for the constraint entry itself.
- **AC3** `ALTER TABLE … ADD CONSTRAINT … PRIMARY KEY` reaches the same nodes as AC2, including when
  the `ALTER` is in a different file from the `CREATE`.
- **AC4** A column definition stating neither `NULL` nor `NOT NULL` carries **no** `nullable` key.
- **AC5** Every existing `Column` assertion in `tests/contract/` and the SQL adapter suite still
  passes unchanged — this adds keys, it moves none.
- **AC6** A repo with no SQL adapter sees byte-identical rows from every tool (the 022 AC3 shape).

**Re-scoped after 248 shipped.** This ticket carried a fourth scope item — a declaration ordinal and
a real per-column `line_start` — added because declaration order looked unrecoverable. It is not:
248 reads the DDL order off the `CONTAINS` edge ids, proven end to end against a real indexed
`CREATE TABLE`, so the ordinal has no remaining caller. The per-column line is still missing and is
now [254](254_a-column-points-at-its-table-s-create-line-not-at-itself.md).

## References

- `adapters/sql/src/ddl.js:10-12` (`NOT_A_COLUMN`), `:22-26` (`AFTER_DEFAULT`), `:140-165`
  (`readColumnDef`).
- `adapters/sql/src/scan.js:415-431` (`Column` node emission), `:517` (one `line` for every column
  in a body), `:529` (`ALTER` path); `ddl.js:295` (`readColumns`, no offset tracking).
- `code_atlas/store.py:169` (`_NODE_ORDER`) — why row order cannot stand in for declaration order.
- [239](239_a-column-row-cannot-name-what-it-points-at.md) — the same shape one step earlier: the
  fact was in the graph and the row could not carry it. Here the fact is not in the graph at all.
- [228](228_the-sql-adapter-owns-every-sql-file-but-reads-one-dialect-and-says-nothing.md) — the
  dialect boundary this must not quietly cross.
- [248](248_a-table-is-addressable-and-its-columns-are-not-readable-from-it.md) — the read path that
  consumes these facts. Useless without this ticket for three of the four.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 247 — Column reader discards nullability / IDENTITY / PRIMARY KEY (working doc)

- **Ticket:** 247 · local file `docs/tasks/247_the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key.md`
- **Type:** bug / adapter capture
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 UI paths
- **TIER:** full
- **BASELINE:** green — related suite 28 passed / 3 skipped on `3548648b03e1b01ec13d7950c5ac57cf2e35bb0b`

## Session status

- **Last updated:** 2026-09-11
- **Current phase:** finalise
- **Next action:** push feature branch + open PR (handover-authorised); merge not authorised
- **Blocked on:** none
- **work_doc_mode:** embed
- Run: `/mango:autorun 247 --no-reviewer`; challenger ON.
- Branch: `feat/247-the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key`
- Contract: `.mango/run-contract-247.txt`
- Worktree: `/tmp/code-atlas-wt-247`

---

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

**PREMISE detail.** Present: `adapters/sql/src/ddl.js` (`readColumnDef`, `NOT_A_COLUMN`, `AFTER_DEFAULT`), `adapters/sql/src/scan.js` (Column emit, ALTER path), tasks 022/228/239. No missing resolvable identifiers.

**INPUT KIND:** ticket (not epic).

**How-decisions (self-resolved):**

1. **Extra key shapes** — `nullable: boolean` when explicit; `identity: {seed, increment}` when `IDENTITY[(s,i)]` (bare `IDENTITY` → T-SQL grammar default `{seed:1,increment:1}` per R2); `primary_key: <1-based ordinal>` number. Cite Scope bullets 1–3 + AC1 wording.
2. **Cross-file ALTER PK** — emit sparse Column extras from the ALTER file (same as same-file `Object.assign` path); fold those keys onto the typed Column row by qname in a kind-scoped indexer pass so AC3 lands on the same nodes. Cite AC3 + 022 same-file DEFAULT merge precedent + R1.1 (kind branch, not language).

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `do-not-attest-past-the-payloads-resolution` | 2 | handle | Yes — omit `nullable`/`identity`/`primary_key` when DDL is silent (R5.6/061) |
| 2 | `prove-the-guard-fails` | 2 | handle | Yes — proving test red before capture |

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=6`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 proven by | Status |
|----|--------|------------------|----------------|--------------|-----|-----------------|--------|
| G1 | Why | schema Q unanswered; type kept, rest dropped | Capture nullable/identity/PK on Column.extra | ddl.js:140 drops them | D1 | proving AC1 | ✅ |
| C1 | Constraints | R2 standard over sample | Encode T-SQL grammar, not anchor names | | D1 | fixture shapes | ✅ |
| C2 | Constraints | No CONTRACT_VERSION bump | extra keys only | | D1 | AC5 | ✅ |
| C3 | Constraints | Dialect honesty (228) | T-SQL IDENTITY only; no AUTO_INCREMENT map | | D1 | AC4/non-T-SQL absent | ✅ |
| C4 | Constraints | Omit-when-absent (061) | No keys when DDL silent | | D1 | AC4 | ✅ |
| R1 | Scope | nullable from explicit NULL/NOT NULL | | | D1 | AC1/AC4 | ✅ |
| R2 | Scope | identity + seed/increment | | | D1 | AC1 | ✅ |
| R3 | Scope | PK ordinal from inline + table-level | NOT_A_COLUMN stays; apply ordinals after | | D1 | AC2 | ✅ |
| R4 | Scope | ALTER ADD CONSTRAINT PRIMARY KEY | incl. other file | | D1 | AC3 | ✅ |
| AC1 | AC | IDENTITY(1,1) NOT NULL PRIMARY KEY | | | D3 | proving | ✅ |
| AC2 | AC | table-level composite PK ordinals | | | D3 | test | ✅ |
| AC3 | AC | ALTER PK same nodes cross-file | | | D3 | test | ✅ |
| AC4 | AC | no NULL/NOT NULL ⇒ no nullable | | | D3 | test | ✅ |
| AC5 | AC | existing Column asserts unchanged | | | D3 | related suite | ✅ |
| AC6 | AC | no-SQL-adapter byte-identical (022 AC3) | | | D3 | non-SQL fixture | ✅ |

## AC validation

| AC | Match? | Falsifiable? |
|----|--------|--------------|
| AC1–AC5 | Y | greppable extra keys / pytest |
| AC6 | Y | byte-identical tool rows without SQL adapter |

## Inventory

- **N:** 1 adapter (`sql`) · 2 files (`ddl.js`, `scan.js`) · 1 indexer fold · proving tests

| # | Item | Ph3/4 | Status |
|---|------|-------|--------|
| 1 | ddl column/PK readers | proving module | ✅ |
| 2 | scan emit + ALTER PK | proving module | ✅ |
| 3 | cross-file Column.extra fold | AC3 | ✅ |

## Clarifications

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

1. Extra shapes (`nullable` bool / `identity` `{seed,increment}` / `primary_key` ordinal) — cite Scope + AC1.
2. Cross-file fold of sparse Column extras by qname — cite AC3 + R1.1 kind branch.

---

## Phase 1 — Analysis

- Root cause (`data`/`logic`): `readColumnDef` treats NULL/IDENTITY/PRIMARY KEY only as DEFAULT boundaries; table-level PK entries return null via `NOT_A_COLUMN` with no second reader.
- Blast radius: SQL adapter + small kind-scoped indexer fold for AC3; no contract bump; no core language branch.
- `TRACK: backend` · `SCOPE: M` · `TIER: full`

`RULE SECTIONS: 9 applicable — 9 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R1.4 (change-type) ✅ · R2 (change-type) ✅ · R3 (change-type) ✅ · R4.2 (change-type) ✅ · R5.2 (change-type) ✅ · R5.6 (change-type) ✅ · R6.1 (change-type) ✅ · R6.5 (change-type) ✅`

### BASELINE

Related suite on ticket-landed HEAD `3548648b03e1b01ec13d7950c5ac57cf2e35bb0b` (pre-product change): `pytest tests/test_sql_tier2_write_sites.py tests/test_sql_foreign_key_references.py tests/test_sql_adapter_dialect_honesty.py tests/test_optional_field_capture.py -q` → **28 passed, 3 skipped**.

`BASELINE: green`. No exclusions.

- **Gate 1 status:** cleared (autorun)

---

## Phase 2 — Design

- **Approach.** Extend `readColumnDef` to return `nullable`, `identity`, `inlinePrimaryKey`. Add `readPrimaryKeyDef` / `readPrimaryKeys` mirroring FK readers for table-level and ALTER `ADD CONSTRAINT … PRIMARY KEY (…)`. `scan.js` writes those onto Column.extra (omit-when-absent); after CREATE body columns, apply table-level ordinals; ALTER PK uses the same `column()` merge path. Cross-file: sparse Column rows fold into the typed qname row via kind-scoped `fold_column_extras` in the indexer after each file replace (and once at end of full_build). Proving tests cover AC1–AC4; related suite covers AC5; PHP-only / no-SQL path covers AC6.

- **Rejected.** (1) CONTRACT_VERSION / NODE_FIELDS bump — rejected: C2 / R3. (2) Cross-dialect AUTO_INCREMENT mapping — rejected: C3 / 228. (3) Default `nullable: true` when clause absent — rejected: C4 / R5.6. (4) New PrimaryKey node kind instead of Column.extra — rejected: Scope names Column.extra; 248 consumes those keys.

**Assumptions**

| Assumption | Status |
|------------|--------|
| Column.extra may hold JSON bool/number/object (indexer json.dumps) | verified — stub flag is bool; FK extras are strings; numbers/objects round-trip |
| Same-file ALTER merges via scan `columns` Map | verified — DEFAULT path Object.assign |
| Kind-scoped fold is R1.1-clean | verified — R1.1 bans language branches; kind is contract vocabulary |

**Smallest change-list**

| Change | File | Rows |
|--------|------|------|
| Parse nullable/identity/inline PK + table-level PK | `adapters/sql/src/ddl.js` | R1–R3,C* |
| Emit extras; ALTER PK; apply ordinals | `adapters/sql/src/scan.js` | R1–R4,G1 |
| Fold sparse Column.extra by qname | `code_atlas/indexer.py` (or store helper) | AC3,R4 |
| Proving + AC tests | `tests/test_sql_column_nullability_identity_pk.py` | AC1–AC6 |
| Working doc / backlog / ledger | docs | finalise |

**Recalled handles**

| Handle | Answer |
|--------|--------|
| `do-not-attest-past-the-payloads-resolution` | traced — omit keys when DDL silent (AC4) |
| `prove-the-guard-fails` | traced — proving red before change |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**Proving test:** `pytest tests/test_sql_column_nullability_identity_pk.py::test_inline_identity_not_null_primary_key -q`

**Verification plan** — AC1–AC5 logic/unit ✅; AC6 integration ✅ (no-SQL adapter path). `EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **Gate 2 status:** cleared (autorun)

## Decision log

| When | Decision | Why |
|------|----------|-----|
| t0 | reviewer off, challenger on | `/autorun 247 --no-reviewer` |
| refine | extra shapes as above | Scope + AC1 |
| refine | cross-file fold by qname | AC3 |
| design | no contract bump | C2 |

## Phase 3 — Execute

- **Branch:** `feat/247-the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key`
- **Proving test:** `tests/test_sql_column_nullability_identity_pk.py::test_inline_identity_not_null_primary_key`

- **Verification sweep.** File axis ✅ (`ddl.js`, `scan.js`, `store.py` fold, `indexer.py` call sites, proving test). Behaviour axis: implemented-as-approved.

- **Design-conformance deviations:** none. Reserved-name gate on early ALTER PK/FK path kept 228 AC3 green (would otherwise emit `KEY::id`).

- **Empirical output**

Ran at 58895548ba16f766e445c5c2a2e1f19605fb44ca

```
$ .venv/bin/python -m pytest tests/test_sql_column_nullability_identity_pk.py tests/test_sql_adapter_dialect_honesty.py tests/test_sql_tier2_write_sites.py tests/test_optional_field_capture.py -q --tb=line
.....................s...s.....s..                                       [100%]
31 passed, 3 skipped in 3.62s
```

- **Golden/snapshot:** none
- **Design-invalidation:** none

## Phase 4 — Review

- **REVIEWER: OFF (`--no-reviewer`)** — no rule-book-grounded review of this diff exists.
- **CHALLENGER: ON** — ticket-blind challenger [815c25a3-1a39-4db5-8eaa-a8b25ff8eedf](815c25a3-1a39-4db5-8eaa-a8b25ff8eedf). Raw ticket + `git diff main...HEAD` excluding this file.
- **challenger result:** round-1 NOT CLEAN (4 must-fix); round-2 residual bare `DEFAULT NULL`; round-3 **15/15 MET — CLEAN**.
- **Scope reconciliation:** file + behaviour axes clean after challenger fixes.
- **Proving test would fail without the change?** Yes — Column.extra lacks the three keys.

Reviewed at 58895548ba16f766e445c5c2a2e1f19605fb44ca

## Phase 5 — Finalise

- Close-out: existing indexes need a **full rebuild** to populate the new Column.extra keys (incremental will not backfill).
- Durable lesson: bare `DEFAULT NULL` is a default *value*; treating `null` only as AFTER_DEFAULT invents `nullable` (R5.6 / 061). Routed as recurrence of `do-not-attest-past-the-payloads-resolution`.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md (already R5.6) | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop`

=======
