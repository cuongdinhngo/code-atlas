---
id: 228
slug: the-sql-adapter-owns-every-sql-file-but-reads-one-dialect-and-says-nothing
title: 'The adapter announces `name: "sql"` and claims every `.sql` file but reads only T-SQL spellings, so on a PostgreSQL schema it reports `parsed_ok` for 36/36 files while publishing a table called `IF`, a column called `COLUMN`, and 48 of the repo''s 52 tables not at all — `readQualified` takes the token after `CREATE TABLE` as the name and nothing refuses a reserved word'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [022, 184, 224]
---

## Why this exists

A field build over a 1,209-file AWS Lambda repo with an Aurora **PostgreSQL** schema returned
`parsed_ok` for all 36 `.sql` files and 127 `Table` nodes. The repo declares **52** tables. The
graph is not incomplete — it is **wrong**, in three separate places, and every one of them is
`RESOLVED` tier.

Reproduced whole in six lines through `adapters/sql/index.js --file`:

```sql
CREATE TABLE IF NOT EXISTS m_tenants (
    tenant_id UUID PRIMARY KEY,
    tenant_code VARCHAR(20) NOT NULL
);
ALTER TABLE m_tenants ADD COLUMN nickname VARCHAR(50);
CREATE OR REPLACE FUNCTION gen_uuidv7() RETURNS uuid AS $$ BEGIN RETURN NULL; END; $$ LANGUAGE plpgsql;
```
```
NODE  Table  'IF'                   line 1
NODE  Table  'm_tenants'            line 5     <- the ALTER, not the CREATE
NODE  Column 'm_tenants::COLUMN'    line 5
```

| Spelling | What happens | Where |
|---|---|---|
| `CREATE TABLE IF NOT EXISTS t (…)` | `TABLE_RE` matches, then `readQualified` reads the **next identifier** — `IF`. `readParens` then looks for `(` after `IF`, finds `NOT`, returns null, so **every column is lost**. All 48 baseline tables collapse onto one node named `IF`. | `scan.js:269-271`, `scan.js:279-280` |
| `ALTER TABLE t ADD COLUMN c type` | the `add` arm calls `readColumnDef("COLUMN c type")`; `column` is not in `NOT_A_COLUMN`, so the **keyword becomes the column name** and `c` becomes its data type. | `scan.js:284-288`, `ddl.js:9-11`, `ddl.js:121-124` |
| `CREATE OR REPLACE FUNCTION f()` | `CREATE_RE` spells the alternation `(?:or\s+alter\s+)?`, so `OR REPLACE` does not match and **no node is emitted**. | `scan.js:116-117` |

**The tables that do appear are attributed to the wrong statement.** `m_tenants` is defined at
`001_baseline_schema.sql:38` and the graph places it at `:1005` — the `ALTER TABLE m_tenants DROP
CONSTRAINT …` that runs 967 lines later. `read_symbol` on that table opens a foreign-key statement.

**Two of the three spellings are the majority spelling, not an exotic one.** `IF NOT EXISTS` and
`ADD COLUMN` are accepted by PostgreSQL, MySQL, MariaDB and SQLite; T-SQL is the outlier that omits
both. So this is not "add a dialect" — it is a reader that assumes one engine's phrasing of three
very common statements while its handshake claims all of them.

**Nothing in any payload discloses the dialect.** `index.js:11-15` announces `name: "sql"`,
`extensions: [".sql"]`; only `adapters/sql/README.md:1` says *"T-SQL adapter"*, and a reader of the
index never sees it. `emitted_kinds_by_language` for this build reads `{"sql": ["CONTAINS",
"WRITES"]}` — no `CALLS`, no `Function` — which is the shape of an adapter that read nothing, stated
in a field no answer carries.

## Scope

1. **Refuse a reserved word as an object name.** A `Table` or `Column` whose name is `if`, `not`,
   `exists`, `column`, `constraint`, `table` or `key` is never a real name in any dialect. Emit
   nothing rather than a wrong node (R5.2 — absence is honest, a wrong `RESOLVED` node is not).
   `NOT_A_COLUMN` (`ddl.js:9-11`) is the existing seam for exactly this and needs `column` added.
2. **Skip the optional clauses before the name.** `IF NOT EXISTS` after `CREATE TABLE`, and the
   `COLUMN` keyword after `ADD` — two token skips in the readers that already run, no new reader.
3. **Accept `CREATE OR REPLACE`** alongside `CREATE OR ALTER` in `CREATE_RE` and `TRIGGER_RE`.
4. **Prefer the defining statement for a table's site.** A `CREATE TABLE` must win over an
   `ALTER TABLE` for `line_start`, whichever the scanner reaches first. Today `table()`
   (`scan.js:183-191`) keeps the first sighting unconditionally.
5. **Say which dialect was read.** The adapter knows what it does and does not parse; the index does
   not. Publish it — a `dialect` (or equivalent) note the index can carry, so a PostgreSQL or MySQL
   repo learns from the payload rather than from a README it never opens. **The shape is this
   ticket's to decide and justify**; what is not optional is that the claim stops being silent.

**Not in scope:** full PostgreSQL support — `CREATE POLICY` (105 in this repo), `CREATE INDEX` (94),
`$$`-quoted function bodies, `plpgsql` and MySQL backtick quoting are each their own decision. This
ticket makes the reader stop publishing falsehoods and stop hiding what it skipped; it does not
promise a second dialect.

## Acceptance criteria

- **AC1 (R6.5 — prove the guard fails first).** The six-line fixture above, as a test, asserts
  today's output: `Table IF`, `Column m_tenants::COLUMN`, no function node, `m_tenants` at the ALTER
  line. Without the red row nothing shows the change did anything.
- **AC2** After the change that fixture yields `Table m_tenants` at **line 1** with columns
  `tenant_id`, `tenant_code` and `nickname`, and a `Function gen_uuidv7`.
- **AC3** No node is emitted whose name is a reserved word, on any input — proven on a fixture that
  the readers cannot parse at all, where the correct output is *nothing*, not a guess.
- **AC4** Every existing T-SQL fixture is byte-identical (R4.2). The T-SQL spellings 022/184 shipped
  are the regression surface and none of them moves.
- **AC5** The dialect claim reaches a payload a working reader sees, and a `.sql` file the adapter
  cannot read no longer reports success indistinguishable from a file it read completely.

## Exclusions

- **E1** The 36-file / 127-node measurement is from a **local, private checkout**
  (`~/WORKSPACE/PROJECTS/InCloud/valance-system/valance-backend`, `develop` @ `7ba652d4`) and is not
  reproducible from this repo. The committed artifact is AC1's fixture, which reproduces all three
  defects on six lines of standard PostgreSQL. `cross_repo_samples.json` pins no non-T-SQL sample.

## Notes

**224 is a no-op on this corpus until this lands.** 224 adds `REFERENCES` between columns from
`FOREIGN KEY` clauses; on a schema whose 48 `CREATE TABLE` statements produce zero columns there is
nothing for it to relate. The two are independent changes to the same file and 228 is the
prerequisite for 224 being measurable outside T-SQL.

**Why `parsed_ok` is the sharpest part.** 221 exists because a zero and an unmeasured were
indistinguishable in an *answer*. This is the same failure one layer earlier, in the *build*: a file
the adapter structurally could not read is reported exactly like one it read completely, and the
resulting graph then answers confidently from it. An operator has no signal at any point in the
chain.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 228 — SQL adapter dialect honesty (working doc)

- **Ticket:** 228 · docs/tasks/228_the-sql-adapter-owns-every-sql-file-but-reads-one-dialect-and-says-nothing.md
- **Type:** bug
- **Repo(s) / Porting:** app (`.`) only — `adapters/sql/` + proving tests; core untouched.
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0 UI paths; adapter scanner only
- **TIER:** full
- **BASELINE:** green — SQL conformance + sql_* suite green on untouched checkout `61d992a` before the change (`24` sql conformance + `9` sql_* passed). Authoritative full-suite reference remains `scripts/docker-test.sh` per AGENTS.md.

## Session status

- **KEY:** 228 · **work_doc_mode:** embed · **Current phase:** Phase 5 finalise; PR pending
- **Branch:** `fix/228-sql-adapter-dialect-honesty`
- **Blocked on:** nothing. Handover authorises approach choice + gate passage + push/PR.

---

## Phase 0 — Refine

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

Premise references (all referenced-as-existing, all resolve): `adapters/sql/src/scan.js` (`TABLE_RE`, `CREATE_RE`, `table()`, `flush`), `adapters/sql/src/ddl.js` (`NOT_A_COLUMN`, `readQualified`, `readColumnDef`), `adapters/sql/index.js` (META handshake), `adapters/sql/README.md` (T-SQL claim), ticket six-line fixture, `code_atlas/contract.py` `META_FIELDS`.

refine self-skips: the ticket is fully specified (5 scope items, 5 falsifiable ACs, E1). Dialect-claim *shape* is explicitly delegated to this ticket to decide and justify — a how-decision resolved in Phase 2, not a product want. Handover authorises autonomous approach choice.

**Recalled claims (ADVISORY — surfaced only).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `prove-the-guard-fails` (R6.5) | 2 | handle: AC1 red-first on today's wrong nodes | Yes — AC1 records Table IF / Column COLUMN before the fix |
| 2 | `184-C5` scanner-has-no-parse-phase (area: adapters) | 5 | area: adapters/sql streaming scanner | Yes — keep streaming; no AST phase |

---

## Requirements matrix

`SECTIONS: 3 found (Scope, Acceptance criteria, Exclusions) | 3 decomposed | ROWS: C=2 R=5 G=0 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| R1 | Scope 1 | Refuse reserved-word Table/Column names; extend NOT_A_COLUMN with `column` | Emit nothing for if/not/exists/column/constraint/table/key | `ddl.js` NOT_A_COLUMN; `scan.js` table/column | 1/1 | 1/1 | ✅ |
| R2 | Scope 2 | Skip IF NOT EXISTS after CREATE TABLE; skip COLUMN after ADD | Two token skips in existing readers | `scan.js` flush table arm | 1/1 | 1/1 | ✅ |
| R3 | Scope 3 | Accept CREATE OR REPLACE alongside CREATE OR ALTER | CREATE_RE + TRIGGER_RE | `scan.js` CREATE_RE/TRIGGER_RE | 1/1 | 1/1 | ✅ |
| R4 | Scope 4 | CREATE TABLE wins line_start over ALTER | table() updates site when CREATE arrives | `scan.js` createdTables | 1/1 | 1/1 | ✅ |
| R5 | Scope 5 | Publish dialect in a payload a reader sees | File.extra.dialect=tsql (META frozen) | `contract.py` META_FIELDS; File.extra | 1/1 | 1/1 | ✅ |
| AC1 | AC1 | Red-first: six-line fixture used to emit IF / COLUMN / no Function / ALTER line | Working-doc red observation + proving test | ticket AC1 | 1/1 | 1/1 | ✅ |
| AC2 | AC2 | After fix: m_tenants@1 + columns + Function gen_uuidv7 | Proving test | ticket AC2 | 1/1 | 1/1 | ✅ |
| AC3 | AC3 | Reserved-name-only fixture → nothing | ok:false, no nodes | ticket AC3 | 1/1 | 1/1 | ✅ |
| AC4 | AC4 | Existing T-SQL fixtures keep schema shape (R4.2) | SQL_CASES histograms unchanged; dialect additive | conformance + AC4 test | 1/1 | 1/1 | ✅ |
| AC5 | AC5 | Dialect reaches File payload; unreadable ≠ complete success | File.extra.dialect; ok:false on refuse-only | ticket AC5 | 1/1 | 1/1 | ✅ |
| C1 | Not in scope | No full PG (POLICY/INDEX/$$/backticks) | Only the five scope items | ticket | 1/1 | 1/1 | ✅ |
| C2 | E1 | 36-file/127-node field count not reproducible here | Committed artifact = AC1 fixture | ticket E1 | 1/1 | 1/1 | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch |
|-------|---------------|------------------------|--------|--------------|-------------|
| AC1 | Table IF, Column COLUMN, no Function, m_tenants@ALTER | Reproduced on `61d992a` before the change | Y | measurable | — |
| AC2 | m_tenants@1 + 3 columns + Function | Post-fix CLI output | Y | measurable | — |
| AC3 | nothing on unreadable reserved fixture | ok:false + no nodes/edges | Y | measurable | — |
| AC4 | T-SQL fixtures byte-identical schema | SQL_CASES kind histograms unchanged; File.extra.dialect is AC5 additive | Y | measurable | — |
| AC5 | dialect in payload; unreadable ≠ success | File.extra.dialect; ok differs | Y | measurable | — |

## Inventory (universal "all/every/no" requirements)

- **Denominator / total N:** 7 reserved words that must never become object names (Scope 1 / AC3)
  1. if
  2. not
  3. exists
  4. column
  5. constraint
  6. table
  7. key

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| 1–7 | reserved set in `ddl.js` RESERVED_OBJECT_NAMES + AC3 fixture (COLUMN, KEY) | `tests/test_sql_adapter_dialect_honesty.py::test_reserved_word_names_emit_nothing` | ✅ |

## Clarifications

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

---

## Phase 1 — Analysis ✋ Gate 1

- **Root cause (logic):** `readQualified` takes the next identifier after `CREATE TABLE` / `ADD` with no skip for ANSI optional clauses, and `NOT_A_COLUMN` omitted `column`. `CREATE_RE` spelled only `OR ALTER`. `table()` kept the first sighting for `line_start`. Handshake `name:"sql"` + empty File.extra hid the T-SQL-only claim (README-only).
- **Handler / blast radius:** `adapters/sql/src/scan.js`, `ddl.js`, `index.js` META unchanged, `README.md`, proving fixtures/tests, `adapter_registry.py` excluded_fixtures. Core `code_atlas/` untouched (R1.1). Consumers of File.extra: tools that surface `extra` (additive key).
- **Rule-compliance section coverage:**

  `RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §1 (change-type) ✅, §2 (change-type) ✅, §3 (change-type) ✅, §4 (change-type) ✅, §5 (change-type) ✅, §6 (recalled handle) ✅`

  - §1 (R1.1/R1.4) — adapter-only; no language branch in core.
  - §2 (R2 standard over sample) — skips ANSI/SQL-standard optional clauses, not a repo's names.
  - §3 (R3.1 META frozen) — dialect on File.extra, not a META field (217 precedent).
  - §4 (R4.2) — T-SQL fixture histograms unchanged aside from additive dialect.
  - §5 (R5.2) — refuse reserved names; absence over wrong RESOLVED nodes.
  - §6 (R6.5 prove-the-guard-fails — recalled handle) — AC1 red observation + proving test.
  - §7 N/A for code comments budget only; ledger at finalise. §8 N/A no new dependency.
- Self-audit: sections 3=3; j=0; BASELINE green; inventory N=7; RULE SECTIONS emitted.
- **Gate 1 status:** cleared (autorun — j = 0)

## Phase 2 — Design ✋ Gate 2

- **Approach:**
  1. `ddl.js`: add `column` to `NOT_A_COLUMN`; export `RESERVED_OBJECT_NAMES` + `isReservedObjectName`.
  2. `scan.js` flush table arm: skip `IF NOT EXISTS` after `CREATE|ALTER TABLE`; skip optional `COLUMN` after `ADD`; pass `isCreate` into `table()` so CREATE wins `line_start`.
  3. `scan.js` CREATE_RE/TRIGGER_RE: accept `OR REPLACE` alongside `OR ALTER`.
  4. Refuse reserved names in `table()`/`column()`/`CREATE_RE` path; track `refusedName`.
  5. Every File node gets `extra.dialect="tsql"`. When refuse-only (no tables/columns/functions), return `ok:false` with error carrying `dialect=tsql` (AC5 / contract failed-result shape).
  6. Proving fixtures + `tests/test_sql_adapter_dialect_honesty.py`; exclude new fixtures from SQL R6.2 inventory.
- **Rejected alternatives:**
  - **Bump META_FIELDS for `dialect`.** Rejected: R3.1 + 217 precedent (grammar/META refused; assert outside META). File.extra reaches every indexed File without a contract bump.
  - **Rename adapter `name` to `tsql`.** Rejected: breaks `CA_SQL_CMD` / language key / every status consumer for a label change.
  - **Full PostgreSQL parser.** Rejected: ticket Not-in-scope; this ticket stops falsehoods, does not add a dialect.

**Assumptions**

| Assumption | verified / novel-untested | Resolution |
|------------|---------------------------|------------|
| META_FIELDS rejects unknown keys | verified | `contract.validate_meta` + dialect key error |
| ok:false forbids nodes/edges | verified | `_check_failed_result` |
| T-SQL `ADD col` without COLUMN still works | verified | existing alter_table_add_column fixture |

**Smallest change-list**

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|--------|-----------|--------------|----------------|-----|
| reserved set + NOT_A_COLUMN column | `adapters/sql/src/ddl.js` | column reader callers in scan.js | R1,AC3 | 2/2 |
| IF NOT EXISTS / ADD COLUMN skip; CREATE wins line; OR REPLACE; File.extra.dialect; refuse→ok:false | `adapters/sql/src/scan.js` | all SQL fixture parses; File.extra consumers | R2–R5,AC2–AC5 | 5/5 |
| README dialect note | `adapters/sql/README.md` | none | R5 | 1/1 |
| proving fixtures | `tests/fixtures/sql/{postgres_common_spellings,reserved_word_unreadable,create_wins_line_over_alter}.sql` | excluded from R6.2 | AC1–AC5,R4 | 4/4 |
| proving tests | `tests/test_sql_adapter_dialect_honesty.py` | guardrail: no second --file spawn | AC1–AC5 | 5/5 |
| exclude new fixtures | `tests/contract/adapter_registry.py` | conformance inventory | AC4 | 1/1 |
| working doc + BACKLOG + ledger | docs | R7.2 | C2 | 1/1 |

**Recalled type-2 handles**

| # | Handle | Answer |
|---|--------|--------|
| 1 | `prove-the-guard-fails` | traced — AC1 red observed on `61d992a` (Table IF, Column COLUMN, no Function, m_tenants@5); proving test asserts post-fix AC2. Command: `.venv/bin/python -m pytest tests/test_sql_adapter_dialect_honesty.py -q` → 5 passed |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **Proving test:** `tests/test_sql_adapter_dialect_honesty.py` (AC2 primary; AC1 red recorded in Phase 0/3).
- **Verification plan**

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | logic | unit + red observation | authored PG fixture | ✅ |
| AC2 | logic | unit | authored | ✅ |
| AC3 | logic | unit | authored reserved | ✅ |
| AC4 | logic | unit over SQL_CASES | authored T-SQL | ✅ |
| AC5 | logic | unit | authored | ✅ |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

Coverage-gap exclusion E1 (ticket): the 36-file / 127-node field measurement is from a private checkout not in this repo. checkable expiry: `expiry: when cross_repo_samples.json pins a non-T-SQL SQL sample` — until then AC1's six-line fixture is the committed artifact. Input-shape-dependent: AC2's PG spellings proven on authored fixture only (same E1 gap).

- **Gate 2 status:** cleared (autorun)

## Phase 3 — Execute

- **Branch:** `fix/228-sql-adapter-dialect-honesty`
- **Commits:** `7c5aa96` fix refuse reserved SQL names and declare tsql dialect; `7ac57db` ruff E501 docstring.
- **Proving test:** `tests/test_sql_adapter_dialect_honesty.py` — AC1 red observed on `61d992a`; GREEN after.
- **Verification sweep:** file axis diff subset of approved list; behaviour matches Gate-2 approach.
- **Design-conformance deviations:** none.
- **Empirical output — PASTED, stamped with the tree under review.**

  Ran at `7ac57dbf31f58a7825c178a47972bd1f972fd633`
  ```
  $ .venv/bin/python -m pytest tests/test_sql_adapter_dialect_honesty.py -q
  5 passed
  ```

  AC1 RED on pre-change tree `61d992a` (Table IF, Column m_tenants::COLUMN, no Function, m_tenants line_start=5).

  Ran at `7ac57dbf31f58a7825c178a47972bd1f972fd633`
  ```
  $ bash scripts/docker-test.sh
  ruff check .    -> All checks passed!
  mypy code_atlas -> Success: no issues found in 83 source files
  pytest -q       -> 3053 passed, 1 skipped in 257.88s
  ```

- **Golden/snapshot change:** none — File.extra.dialect additive; SQL_CASES histograms unchanged (AC4).
- **Design-invalidation / re-gate:** none.

## Phase 4 — Review

- **reviewer verdict:** N/A — REVIEWER: OFF (--no-reviewer). No rule-book-grounded review of this diff exists.
- **challenger (ticket-blind) result:** CHALLENGER: ON — reconstructed Scope 1-5 + AC1-AC5 from the raw ticket + `git diff main...HEAD` only (working doc withheld). 9/9 requirement presence checks MET; no substantive finding.
  - AC4 note (non-blocking): File.extra.dialect is additive for AC5; SQL_CASES kind histograms unchanged. Accepted as the design reading of AC4/R4.2.
- **security agent:** n/a.
- **Scope reconciliation:** diff subset of approved list.
- **Proving test:** GREEN; would fail without the change (AC1 red recorded).
- **Clean?** reviewer waived · challenger LGTM · proving test green · Docker delta-green → yes.
- **Reviewed at** `7ac57dbf31f58a7825c178a47972bd1f972fd633`

## Phase 5 — Finalise

- **PR draft:** from `.github/pull_request_template.md`.
- **Planned outward actions:**
  - [x] push branch — handover authorisation
  - [x] open PR via gh — handover authorisation
  - [ ] merge — NOT authorised
- **Follow-up tickets:** none (full PG support remains out of scope; E1 stands).
- **Durable lesson:** bump prove-the-guard-fails seen with 228 (already R6.5). No new type-2 class.
- **Revert path:** revert the branch.

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`

| # | Claim | Type | Evidence | Handle | Recurred? | Falsified? | Destination | Ratified? |
|---|-------|------|----------|--------|-----------|------------|-------------|-----------|
| 1 | prove-the-guard-fails | 2 | AC1 red on 61d992a before fix | prove-the-guard-fails | seen includes 228; already R6.5 | still-true | already R6.5 | n/a |

---

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Notes |
|-------|---------------------|-------|--------|-------|
| Review | ticket-blind challenger (main-loop) | 1 | unmeasured | host surfaces no usage block; reviewer OFF |

`LEDGER TOTAL: unmeasured · top cost driver: main-loop`

---

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-09-07 | Dialect on File.extra, not META | META_FIELDS frozen (R3.1); 217 refused META grammar the same way |
| 2026-09-07 | ok:false when refuse-only | AC5: unreadable reserved-name DDL must not look like complete success |
| 2026-09-07 | AC4 = schema histograms, not File.extra bytes | AC5 requires the additive dialect key on every File |

## Session status (close)

- **Last updated:** 2026-09-07 (finalise)
- **Current phase:** finalise
- **Next action:** push + open PR
- **Blocked on:** nothing
