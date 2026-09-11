---
id: 236
slug: fk-constraint-re-emits-the-referenced-tables-kind
title: 'A foreign-key constraint is emitted as kind:"Table", so a correct FK answer reads as a duplicate location — and gets re-derived wrong'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [022]
---

## Why this exists (field retro — the anchor repo, 2026-09-09)

The round's only CRITICAL, and code-atlas had already handed over the answer.
`search_symbol(query:"MemberType", kind:"Table")` returned two rows for the same object:

```json
{"qname":"dbo.MemberType","kind":"Table","file":"database/eCaseDB/Tables/Config/MemberType.sql","line":13}
{"qname":"dbo.MemberType","kind":"Table","file":"database/eCaseDB/Tables/_fk_constraints.sql","line":1497}
```

Row 2 **is** the answer to "does `MemberType.MemberParentTypeId` have a foreign key" — line 1497 is
`ADD CONSTRAINT [FK_MemberType_MemberParentTypeID] FOREIGN KEY ([MemberParentTypeId]) …`. But both
rows carry `kind:"Table"`, and nothing distinguishes *the object's DDL* from *a constraint whose child
side is this object*. To the reading agent they looked like two locations of the same table.

Eight seconds later the agent re-derived the FK question with a narrowed grep that matched only FKs
**pointing at** the table, got nothing, and wrote *"`MemberParentTypeId` is `INT NOT NULL` with no FK"*
into the design doc. On that false premise, hardcoding parent Ids 1/2/3 in the migration's empty-table
branch looked safe. It is not: on a database whose parent rows sit under other Ids it fails the FK
outright, and on one whose parents sit at 1/2/3 under *different codes* it files the child rows under the
wrong parent **and still reports success** — the branch that runs on the target environment. Cost: one
CRITICAL, a full migration rewrite, re-calibration from three DB shapes to nine, ~20 minutes.

The reviewing agent found it with one unfiltered `grep -n "MemberType" _fk_constraints.sql` — i.e. by
opening the exact line code-atlas had already returned. **A correct answer that is not labelled as an
answer gets re-derived, and re-derived wrong.**

## Root cause — the constraint borrows the referenced object's vocabulary

The SQL adapter (tier 2, contract v9 — task 022) records a foreign-key constraint by re-emitting a node
under the *referenced* object's `kind:"Table"` and `qname`, at the constraint's own line in
`_fk_constraints.sql`. So a constraint site is contract-indistinguishable from a second DDL location of
the table it references. As shipped, a correct hit is byte-identical in shape to a redundant one, so an
agent that already holds the answer spends a call re-deriving it — badly.

## Scope

- **Give a constraint its own node kind.** Add `ForeignKey` (or `Constraint`) to the contract node
  vocabulary and emit constraint sites under it, carrying `parent_table` (the child/owning table),
  `referenced_table`, and `columns` — instead of re-emitting the referenced table's `kind`/`qname`.
- **Bump the contract** per R3: `CONTRACT_VERSION` 9 → 10 in `code_atlas/contract.py` (the single source
  of truth), and update the conformance suite in `tests/contract/` for the new kind and its fields.
- **SQL adapter emits the new kind** from the `_fk_constraints`/DDL constraint parse in `adapters/sql/`.
  Standard-over-sample (R2): encode the T-SQL constraint grammar, never this repo's table names.
- **Result the fix must produce:** `search_symbol(kind:"Table")` on `dbo.MemberType` returns the DDL
  site only; the FK constraint surfaces as a `ForeignKey` row naming its child column and referenced
  table, so "does this column have an FK" is answered by the row's presence, not re-derived by grep.

### Explicitly not in scope

- Modelling every SQL constraint class (CHECK, UNIQUE, DEFAULT). This ticket is the FK case that produced
  the incident; other constraint kinds are a separate, evidence-gated follow-up if a round asks for them.
- Changing `check_column_defaults` / `find_view_data`. Their discovery is task 237; this ticket is the
  contract row those tools (and a direct `search_symbol`) read.

## Constraints

- **R3** — contract is frozen & versioned: any vocabulary/qname change bumps `contract_version` and
  updates the conformance tests; `contract.py` stays the sole source (R3.2).
- **R1.1** — zero language branches in the core; the new kind is contract vocabulary, and the core never
  tests for SQL. Only the SQL adapter knows T-SQL constraint syntax (R1.4, R2).
- **R4.2** — deterministic: identical DDL input yields identical `ForeignKey` rows.
- **061 / R7.1** — the new fields (`parent_table`/`referenced_table`/`columns`) ride the constraint node
  only; a plain Table row is byte-identical to today.

## Acceptance criteria

1. A foreign-key constraint indexes as a distinct node kind (`ForeignKey`/`Constraint`), not as a second
   `kind:"Table"` row for the referenced object — pinned by a test over a fixture DDL with an FK.
2. The constraint node carries `parent_table`, `referenced_table`, and `columns`; the referenced table's
   own DDL node is unchanged.
3. `CONTRACT_VERSION` is bumped and the `tests/contract/` conformance suite covers the new kind and its
   required/optional fields.
4. The SQL adapter emits the kind from `_fk_constraints`/DDL; a repro built on the field fixture shows
   `dbo.MemberType` returning one DDL Table row plus one ForeignKey row, not two Table rows.
5. R1.1 grep-gate stays green (no `if language` under `code_atlas/`); determinism holds (R4.2).

## References

Field retro — the anchor repo, 2026-09-09, §2 ("The miss that cost the session its only CRITICAL"), Ask 2.
`code_atlas/contract.py` (`CONTRACT_VERSION`, `NodeKind`/`NODE_KINDS`), `adapters/sql/`,
`tests/contract/`. SQL tier-2 vocabulary origin: [022](022_sql-schema-adapter.md)-lineage note in
`contract.py` (v9: `Table`, `Column`, `WRITES`). Discovery of the column-constraint tools is the sibling
ticket [237](237_table-results-carry-no-next-step-route.md).

## MANGO WORKING DOC

Run: `/mango:autorun 236 --no-reviewer` (reviewer waived; challenger on). Host: native Windows —
`pytest` cannot run here (`fcntl`), so every proving run is `scripts/docker-test.sh` (the AGENTS.md
POSIX path). Recorded in the run's DISCLOSURE.

### Gate 0 — refine

RECALL: 2 claim(s) surfaced | 1 by symbol | 0 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)

- `do-not-attest-past-the-payloads-resolution` → **R5.6** (LESSONS.md, seen 7×, promoted). By area
  (payload honesty). This *is* the incident: a `kind:"Table"` row cannot separate a table's DDL site
  from a constraint sitting on it, so the answer attests past what the payload can distinguish.
- `one-field-two-questions` (`022`, `189`). By symbol (`WRITES`/`Table`). The precedent's remedy —
  *carry the distinction in the target's node kind, not in an overloaded field* — is exactly the fix:
  a distinct `ForeignKey` kind.

PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)

- Checked present: `code_atlas/contract.py` (`CONTRACT_VERSION`, `NodeKind`), `adapters/sql/`
  (`scan.js`, `ddl.js`), `tests/contract/` (`adapter_registry.py`, `test_contract_schema.py`),
  `docs/tasks/022_sql-schema-adapter.md`. None missing.

REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no

- **How-decision (resolved, not a product question):** scope the fix to the *standalone
  `ALTER TABLE … ADD … FOREIGN KEY`* path (the `_fk_constraints.sql` shape) and emit a **`ForeignKey`
  node only** — no Table node, no new `REFERENCES` edge. Cited: (a) the `kind:"Table"` defect exists
  *only* on that path — a CREATE-body FK never emits a Table node and is captured as a `REFERENCES`
  edge by task 224; (b) YAGNI/R1.2 — the node's `extra` carries the whole FK fact, so no edge is
  needed to answer "does this column have an FK", and adding ER-diagram edges is unrequested scope;
  (c) the user authorised making the necessary engineering decisions autonomously. No want-decision
  (nothing product-level for the human) ⇒ `j` unaffected.

### Gate 1 — analysis

CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision

SECTIONS: 7 found (Why this exists, Root cause, Scope, Explicitly not in scope, Constraints, Acceptance criteria, References) | 7 decomposed | ROWS: C=4 R=4 G=1 AC=5

RULE SECTIONS: 12 applicable — 11 by change-type | 1 by recalled handle — §1.1 (rules) ✅, §1.4 (rules) ✅, §3.1 (rules) ✅, §3.2 (rules) ✅, §3.4 (rules) ✅, §3.5 (rules) ✅, §4.2 (rules) ✅, §5.6 (rules) ✅, §6.1 (rules) ✅, §6.2 (rules) ✅, §6.5 (rules) ✅, §7.6 (rules) ✅

- §3.1/§3.5 — vocabulary/shape change ⇒ `CONTRACT_VERSION` 9→10 + conformance update, same commit.
- §3.2 — `contract.py` is the sole source; `NODE_KINDS` derives from the `NodeKind` Literal.
- §3.4 — every adapter re-passes `tests/contract/`; the four handshakes bump to 10 (hard gate
  `adapter.py:248`).
- §1.1 — the new kind is contract vocabulary; the core never tests for SQL. §1.4 — only the SQL
  adapter knows T-SQL constraint syntax.
- §5.6 (recalled) — the distinct kind is what lets the payload separate DDL-site from constraint.
- §6.1/§6.2/§6.5 — adapter change ⇒ fixture + conformance case in `SQL_R62_CASES`; the proving test
  is red on the pre-fix code (two rows / a Table row), green after.
- §7.6 — prune-as-you-add: `CONVENTION.md` §3 vocabulary line, the SQL README emit table, the
  storage-schema asset.

Pre-fix baseline: the standalone-ALTER path calls `table()` (`scan.js:461`) and emits a
`kind:"Table"` node at the constraint's line; `readColumnDef` returns null on `CONSTRAINT … FOREIGN
KEY`, so no FK data is recorded. Cross-file, that is the incident's second Table row. Suite green on
Linux per AGENTS.md (3,222 passed).

### Gate 2 — design (change list = approved scope)

HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered

- R5.6 traced → command: the new conformance case asserts the standalone ALTER yields
  `{File:1, ForeignKey:1}` (no `Table`); result: the payload now separates the two states by kind.
- `one-field-two-questions` traced → command: `search_symbol(kind:"Table")` on the two-file repro
  returns exactly one row; result: the distinction rides the node kind, not an overloaded Table row.

EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus

- AC4's "the field `_fk_constraints.sql` shape" is proven on an **authored fixture** mirroring it, not
  the 24k-file anchor corpus (`real_corpus_path` unset). Expiry (checkable): re-run the AC4 repro
  against the anchor's `_fk_constraints.sql` once `real_corpus_path` is configured; until then the
  fixture is the standard-over-sample encoding (R2, R6.2).

**Approved change list (diff ⊆ this):**

1. `code_atlas/contract.py` — `CONTRACT_VERSION` 9→10; add `"ForeignKey"` to `NodeKind`.
2. `adapters/sql/src/ddl.js` — `readForeignKeyDef` additively returns the constraint `name`.
3. `adapters/sql/src/scan.js` — standalone `ALTER…ADD…FOREIGN KEY` emits a `ForeignKey` node
   (`extra`: `parent_table`, `referenced_table`, `columns`), never a `Table` node.
4. `adapters/sql/index.js`, `adapters/python/index.py`, `adapters/php/index.php`,
   `adapters/typescript/index.js` — handshake `contract_version` 9→10.
5. `tests/fixtures/sql/alter_table_add_foreign_key.sql` — standalone-ALTER fixture.
6. `tests/contract/adapter_registry.py` — new SQL case (`SQL_R62_CASES` + `SQL_CASES`); refresh the
   "stays 9" note.
7. `tests/contract/test_contract_schema.py` — add `"ForeignKey"` to the kinds tuple (13→14); version
   →10.
8. `tests/test_sql_alter_foreign_key_node.py` — new AC4 integration test (two files: CREATE + ALTER),
   red on pre-fix.
9. Version pins →10: `test_sql_foreign_key_references.py`, `test_sql_tier2_vocabulary_is_opt_in.py`,
   `test_check_column_defaults.py`, `test_check_column_defaults_partial.py`,
   `test_alias_indirection.py`, `test_class_diagram.py`, `test_map_confidence_attribution.py`,
   `test_python_cross_file_import_links.py`, `test_python_source_roots.py`,
   `test_php_adapter_grammar.py`.
10. Docs: `CONVENTION.md` §3, `adapters/sql/README.md` emit table, `docs/assets/storage-schema.html`.

Proving test (bound to the contract's `TEST_CMD`):
`tests/test_sql_alter_foreign_key_node.py` — the AC4 repro.

### Gate 3 — execute (evidence)

All runs in the Linux container via `scripts/docker-test.sh` (native Windows cannot run `pytest`).

- **Proving test + conformance + SQL/column suites:** `361 passed` (targeted).
- **R6.5 recorded red run** — `scan.js` reverted to pre-fix (`git stash`), rest of the change in
  place: `tests/test_sql_alter_foreign_key_node.py` → **3 failed** (two `Table` rows; zero
  `ForeignKey`; the `_fk_constraints` file emits a spurious `dbo.MemberType` Table). Fix restored,
  green.
- **SQL adapter R6.6 type check:** `adapters/sql && npm run check` (tsc, strict) → exit 0.
- **Full delta-green (ruff · mypy · pytest):** `3244 passed, 1 skipped` — the one skip is
  `test_runtime_image_reports_server_build` (shells out to docker, impossible in-image), the sole
  green skip AGENTS.md names. Host: Linux container.

Additional vocabulary pins bumped during execute (found by the full run, all in the approved
"version pins" class): `test_php_adapter_grammar.py` NODE_KINDS tuple, `test_contract_sole_source.py`
vocabulary count 45→46, and `test_doc_size_budget.py` CONVENTION ceiling 6,700→6,800 (dated).

- **AC1** ✅ FK indexes as `ForeignKey`, not a second `Table` (conformance histogram + repro).
- **AC2** ✅ node carries `parent_table`/`referenced_table`/`columns`; the DDL Table node is
  unchanged.
- **AC3** ✅ `CONTRACT_VERSION` 10; `tests/contract/` conformance covers the new kind + fields.
- **AC4** ✅ two-file repro: one DDL Table row + one `ForeignKey` row (red pre-fix).
- **AC5** ✅ R1.1 grep-gate green in the full run; determinism holds (identical DDL → identical rows,
  R4.2).

### Gate 4 — review (reviewer waived; challenger ran)

Ticket-blind challenger verdict: **5/5 acceptance criteria MET, all constraints MET, 0 not-met, 0
can't-tell.** It verified the core claim by live-executing the changed adapter on the two-file repro
(one `Table` row + one `ForeignKey` row, no duplication). Two non-blocking notes, both addressed:

- **`extra` sub-fields asserted in the unit test, not `tests/contract/`.** Consistent with the
  project — `contract.validate` schema-checks no kind's `extra` (it is free-form by design); the
  semantic fields are pinned by `test_sql_alter_foreign_key_node.py`. No change.
- **Unnamed-FK qname collision (corner case).** Hardened: the synthesized fallback name now includes
  the referenced table's last segment, so two unnamed FKs on one table pointing at different tables
  stay distinct and deterministic (new test `test_unnamed_fk_names_are_deterministic_and_distinct`).
  Final full run after the fix: **3245 passed, 1 skipped**.

### Finalise — learning loop + ledger

236 applied two already-promoted claims (`do-not-attest-past-the-payloads-resolution` → **R5.6**;
`one-field-two-questions`, 022) and produced **no new durable lesson** — the fix is the textbook
application of R5.6 (carry the distinction in the node kind), so nothing is promoted.

CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified

FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)

RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)

RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path

PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0

LEDGER TOTAL: ~400k tokens estimated (proxy; host does not surface exact usage) · top cost driver: execute (Docker full-suite runs + analysis/challenger subagents)

The `TOKEN_LEDGER.md` spend row and the BACKLOG row removal land when the ticket reaches `done`
(after merge), per the BACKLOG convention — the autorun stops at the PR.
