---
id: 321
slug: dynamic-ddl-in-migrations-leaves-no-trace
title: "A migration that alters a table through sp_executesql leaves no trace on that table, so \"has this object already been migrated?\" is unanswerable and duplicate migrations ship"
phase: 2
milestone: Coverage
status: done
depends_on: [022, 184, 296]
---

## Why this exists (field retro, 2026-09-22 — FIELD-1426/1013/1598 batch; second sighting)

An agent fixing FIELD-1013 searched `dbo.UserNotes`, got the `Table` and its `Column`s — including
`ChangeUser` / `ModifiedUser` — read the proc, confirmed the live DEFAULTs, and wrote migration
**V187** re-pointing them at `SESSION_CONTEXT('app_user')`. A human reviewer then found
`V128__field962_usernotes_author_session_context.sql`: **the byte-identical fix, merged 2026-09-14.**
V187 was deleted. The retro names `FIELD-1371/1438` as a prior instance of the same class, and calls
duplicate migrations "the most expensive DB mistake here".

**The graph could not have prevented it.** V128 re-points the DEFAULT with `ALTER TABLE … ` handed
to `sp_executesql` inside a cursor. The adapter reads that as a dynamic call — `CALLS` at `DYNAMIC`
onto `(dynamic)`, with `unmodelled_resolution: ["dynamic_sql"]` stamped on the File
(`adapters/sql/src/scan.js:255`, `:781`) — and the table name exists **only inside a string
literal**, so no edge reaches `dbo.UserNotes`. `search_symbol("UserNotes")` therefore shows the
table and its columns but not the migration that changes them. The static spelling is already
modelled (`ddl.js:523` reads `ALTER TABLE t ADD CONSTRAINT n DEFAULT (expr) FOR col`); it is the
dynamic one — *"the one a migration usually takes"*, as that function's own docstring says — that
vanishes.

**This is a relation, not a location**, which is the surviving product claim after the 2026-08-08
measurement ([PLAN §19](../PLAN.md#19-project-context--decision-log): *"What survives is
relationships, not locations"*). "Which migrations have altered this object" is not a grep for a
count — the honest answer needs the object resolved to its node and the alteration attributed to a
file, which is what the graph is for. The retro's own mitigation ("grep `database/migrations/`
before writing any migration") is a process workaround for a missing edge.

## Goal

From a `Table` / `Function` node, name the migration files that alter it through dynamic DDL —
low-confidence and marked as such — so "has this object already been migrated?" is a graph question
instead of a discipline question.

## Scope / Deliverables

1. **A new edge kind, not an overload of `WRITES`.** `WRITES` means *a routine assigns a column*
   (`contract.py:74`), and `check_column_defaults` counts exactly those edges as the table's
   **writers** (`check_column_defaults.py:58`). Emitting DDL as `WRITES` would enrol every migration
   as a writer that omits every column it does not name, corrupting 022's whole ratio. Add
   `ALTERS` to `EDGE_KINDS`, joined to `FQN_EDGE_KINDS` so the resolver looks the target up by FQN.
2. **Bump `CONTRACT_VERSION` 10 → 11 and extend `tests/contract/`** — a new word in the vocabulary
   is exactly what R3 gates. Adapters that never emit `ALTERS` stay conformant.
3. **Emit it from the SQL adapter, at `DYNAMIC` only.** Inside an `EXEC` / `sp_executesql` string
   argument, match `ALTER TABLE` / `DROP CONSTRAINT` / `ADD CONSTRAINT` / `CREATE OR ALTER` followed
   by an identifier, and emit `ALTERS` from the File to that name at `confidence_tier: DYNAMIC`. No
   control flow, no string concatenation resolution, no attempt at the column: a name-in-string
   match is the whole claim, and the tier says so.
4. **Read it back on the object.** A `Table` / `Function` answer that has inbound `ALTERS` discloses
   them — the file and line — under a field that names the tier, never mixed into a resolved list.
   The `search_symbol` hit is the natural site; the tool decision is the ticket's, not this file's.
5. **Static DDL joins the same relation.** `ALTER TABLE` read literally (`ddl.js:523` and the
   `ALTER … ADD` path at `scan.js:523`) emits `ALTERS` at `RESOLVED`, so the reader gets one
   question with two tiers rather than two half-answers.

## Constraints

- **R2 standard over sample** — the scan keys on T-SQL DDL keywords and `sp_executesql`, never on
  Flyway's `V<n>__` naming, a `database/migrations/` path, or any repo's layout. A migration corpus
  is where this pays off; it must not be what the adapter recognises.
- **R5.6** — a name found inside a string literal is never signed like a resolved edge; `DYNAMIC` is
  load-bearing and the reader must be able to separate the two.
- **R3** — vocabulary change ⇒ version bump ⇒ conformance tests, in the same commit.
- **R1.1 / R1.4** — the core reads `ALTERS` as one more contract kind; no language branch, no SQL
  outside `store.py`.
- Flat memory: the scanner is streaming with a fixed 64 KB buffer and a `PENDING_CAP`; the string
  match must not require buffering a whole statement (`scan.js:497`).
- Comments ≤ 3 lines (R7.5).

## Acceptance criteria

- **AC1** A fixture reproducing V128's shape — `ALTER TABLE … DEFAULT … FOR …` built into a variable
  and run through `sp_executesql` inside a cursor — yields an `ALTERS` edge from that file to
  `dbo.UserNotes` at `DYNAMIC`.
- **AC2** Asking about `dbo.UserNotes` names that file, marked as a dynamic-DDL claim, distinct
  from any resolved relation in the same payload.
- **AC3** A literal `ALTER TABLE dbo.X ADD …` yields `ALTERS` at `RESOLVED` onto the same node.
- **AC4** `check_column_defaults`' `writers_total` / `omitted_count` are unchanged by the presence of
  `ALTERS` edges — a red-arm test pins that DDL never counts as a writer.
- **AC5** `CONTRACT_VERSION` is 11, `tests/contract/` covers the new kind, and every existing adapter
  still passes conformance unchanged.
- **AC6** A string mentioning a table without a DDL verb (`'SELECT * FROM UserNotes'` in an `EXEC`)
  emits **no** `ALTERS` — the claim is "altered by", not "mentioned near".

## Out of scope

- Resolving what the dynamic DDL actually *does* (which column, which expression) — the value is
  "this file alters that object", and inventing the rest would be worse than an honest name (R5.6).
- Any Flyway-, migration-path- or version-ordering awareness; "has it already shipped" is the
  reader's inference from the files named, not the graph's claim.
- A `find_object_migrations` tool. The surface is 24 tools and count-pinned; this is an edge on
  existing tools, and a new verb needs its own evidence (R1.2).
- Dynamic DML (`INSERT`/`UPDATE` built in a string) — `WRITES` at `DYNAMIC` already covers the
  truncated case (`scan.js:503`); widening it is a separate question.

## References
`adapters/sql/src/scan.js:255` (`DYNAMIC_PROCS`), `:497-509` (`flush`, `PENDING_CAP`), `:523`
(`ALTER … ADD`), `:781` (`unmodelled_resolution`); `adapters/sql/src/ddl.js:523`
(`readNamedDefault`); `code_atlas/contract.py:29` (`CONTRACT_VERSION`), `:62-77` (`EDGE_KINDS`),
`:81` (`FQN_EDGE_KINDS`); `code_atlas/tools/check_column_defaults.py:58` (`_sources`);
[PLAN §19](../PLAN.md#19-project-context--decision-log) (2026-08-08 measurement);
[320](320_column-defaults-dead-ends-on-an-unqualified-table.md); ADAPTER_PLAYBOOK §1.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 321 — ALTERS: dynamic DDL in migrations (working doc)

- **Ticket:** 321 · local
- **Type:** feature
- **Repo(s) / Porting:** app
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed · path: docs/tasks/321_dynamic-ddl-in-migrations-leaves-no-trace.md
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** finalise — PR #440 open; never merge

## Phase 0 — Refine

`PREMISE: 11 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

Recalled: `197-C3` (`the-consumer-owns-its-kind-set`, `LESSONS.md`) — a contract subset holding a tier-2 word trips 022 AC3's sweep; the resolver's retry set is the consumer's.

- H1 (how, cited Goal "From a `Table` / `Function` node"): the target is the object after `ALTER TABLE` or `[CREATE OR] ALTER <proc|function|trigger>`; `ADD`/`DROP CONSTRAINT` are clauses of that `ALTER TABLE`, and a constraint name alone names no `Table`/`Function`.
- H2 (how, cited Scope 3 "Inside an `EXEC` / `sp_executesql` string argument" + AC1 "built into a variable"): the field shape puts the string in `SET @sql = N'…'`, not in the `EXEC`, so each literal records what runs it — `EXEC (…)` / `sp_executesql` directly, or the `@variable` it is assigned to (across `+` continuations) — and counts only if an `EXEC` runs that variable. Round 1 shipped a file-wide gate (the 296 stamp); the challenger broke it (Phase 4).

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 6 decomposed | ROWS: C=6 R=5 G=1 AC=6`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | from a Table/Function node, name the migration files that alter it through dynamic DDL | `ALTERS` read back on the hit | D1–D4 | AC1 AC2 | ✅ |
| R1 | Scope 1 | new edge kind, not `WRITES`; joined to `FQN_EDGE_KINDS` | `ALTERS` in both | D1 | AC4 AC5 | ✅ |
| R2 | Scope 2 | bump 10 → 11, extend `tests/contract/` | four handshakes + pins + a DYNAMIC conformance case | D1 D5 | AC5 | ✅ |
| R3 | Scope 3 | SQL adapter, string DDL, `DYNAMIC` only, name-in-string is the whole claim | `DDL_IN_STRING_RE` over literal bodies | D2 | AC1 AC6 | ✅ |
| R4 | Scope 4 | a field naming the tier, never mixed into a resolved list | `altered_by` / `altered_by_dynamic` on `search_symbol` | D4 | AC2 | ✅ |
| R5 | Scope 5 | literal `ALTER TABLE` emits `ALTERS` at `RESOLVED` | at the `ALTER` flush | D2 | AC3 | ✅ |
| C1 | Constraints | R2 — keys on DDL keywords, never Flyway naming or paths | regex on T-SQL verbs only | D2 | test uses `V128__` names the adapter never reads | ✅ |
| C2 | Constraints | R5.6 — a string name never signed like a resolved edge | `DYNAMIC` tier; own field | D2 D4 | AC2 | ✅ |
| C3 | Constraints | R3 — bump + conformance in the same commit | `d640cba` | D1 D5 | AC5 | ✅ |
| C4 | Constraints | R1.1 / R1.4 | kind-keyed read; `edges_by_target` | D3 D4 | gate R1.1 | ✅ |
| C5 | Constraints | flat memory; no whole-statement buffering | `LITERAL_CAP` 64 KB, tail `LITERAL_KEEP` | D2 | review | ✅ |
| C6 | Constraints | comments ≤ 3 lines | R7.5 | all | review | ✅ |
| AC1 | AC | V128 shape → `ALTERS` to `dbo.UserNotes` at `DYNAMIC` | cursor + `sp_executesql` fixture | D6 | proving | ✅ |
| AC2 | AC | asking about the table names the file, marked dynamic, apart from resolved | `search_symbol` fields | D6 | proving | ✅ |
| AC3 | AC | literal `ALTER TABLE … ADD` → `RESOLVED` onto the same node | V130 fixture | D6 | proving | ✅ |
| AC4 | AC | `writers_total` / `omitted_count` unchanged; red arm | literal pinned on main; mutation red | D6 | proving | ✅ |
| AC5 | AC | version 11, conformance covers the kind, adapters conform | registry + schema pins | D5 | proving | ✅ |
| AC6 | AC | a string without a DDL verb emits no `ALTERS` | `report.sql`, `print_ddl.sql` | D6 | proving | ✅ |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

- Q1 → H1; Q2 → H2 (both above).

## Phase 1 — Analysis

- Root cause (`integration`): `stripToCode` drops every literal body (`scan.js:118`, by design so a keyword in a string is not code), so a table named only inside `N'ALTER TABLE …'` reaches no edge; the literal `ALTER` path emitted `Table`/`Column` rows but no relation from the migration file.
- Blast radius: the vocabulary tuple (every pin of `EDGE_KINDS` / `CONTRACT_VERSION`), the resolver (`skip_dynamic` drops DYNAMIC rows except `REFERENCES`, `store.py:2406`), the conformance histograms of the three `ALTER` fixtures, and `search_symbol`'s hit. `check_column_defaults` and `find_references` on a Table read `WRITES` only; `impact` / `find_orphans` walk `IMPACT_KINDS`, which `ALTERS` does not join.

`TRACK: backend — 0/9 touched files under UI paths`

`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ search_symbol keys on kind only · R1.4 (change-type) ✅ edges_by_target, no SQL outside store.py · R2 (change-type) ✅ T-SQL verbs only, no path or Flyway naming · R3 (change-type) ✅ version 11 with conformance in d640cba · R5.6 (change-type) ✅ DYNAMIC rides its own field · R3.2 (recalled handle the-consumer-owns-its-kind-set) ✅ retry set lives in resolver.py`

Baseline record — tree `14cae92` (historical: the base the branch forked from). Command `.venv/bin/python -m pytest -q --tb=line -p no:cacheprovider` → `4394 passed, 4 skipped in 371.77s`.

`BASELINE: green`

## Phase 2 — Design

- A1 contract: `ALTERS` joins `EDGE_KINDS` and `FQN_EDGE_KINDS`, not `IMPACT_KIND_WEIGHTS`; `DYNAMIC_LINKED_KINDS = (REFERENCES, ALTERS)` replaces the store's hard-coded `'REFERENCES'`.
- A2 adapter: literal bodies accumulate in `ScanState.body` (cap `LITERAL_CAP`, tail kept on overflow); on close, `DDL_IN_STRING_RE` + `readQualified` record `{target, literal line, runner}`; emitted at `DYNAMIC` only when the runner is a direct `EXEC` or a variable a dynamic `EXEC` runs. The literal `ALTER TABLE` flush emits one `RESOLVED` edge from the file.
- A3 resolver: `ALTERS` shares `WRITES`' case-insensitive default-schema retry (215) through a resolver-owned `_SCHEMA_OBJECT_KINDS` (197-C3).
- A4 read-back: `search_symbol` `Table`/`Function` hits at `standard` get `altered_by` (RESOLVED) and `altered_by_<tier>` per other tier, `{file, line}` deduped, capped at 32 with `altered_by_truncated`; omitted when empty (061).
- Rejected: emitting from the enclosing routine (the ticket asks which *files*); a new tool (Out of scope, R1.2); `ALTERS` in `IMPACT_KINDS` (changes every `impact` answer over SQL — not asked); fixing the duplicate-`Table`-row ambiguity in the 215 retry (pre-existing, recorded as a BACKLOG follow-up).

**Assumptions:** the scanner sees a literal's body one character at a time with no lookahead past the line — verified (`stripToCode` string branch).

| Handle | Answer |
|--------|--------|
| `the-consumer-owns-its-kind-set` | traced — see below |

Trace record — tree `9ddee2c08d736ae3c615a1c130d5750689373321`. Command `grep -n "_SCHEMA_OBJECT_KINDS\|SCHEMA_OBJECT_EDGE_KINDS" code_atlas/contract.py code_atlas/resolver.py`:

```
code_atlas/resolver.py:26:_SCHEMA_OBJECT_KINDS: tuple[str, ...] = (contract.WRITES, contract.ALTERS)
code_atlas/resolver.py:165:            if edge["kind"] in _SCHEMA_OBJECT_KINDS:
```

The set is the consumer's; the contract exports no subset holding `WRITES`.

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | `ALTERS`, v11, `DYNAMIC_LINKED_KINDS` | code_atlas/contract.py · code_atlas/store.py · four adapter handshakes · adapters/php/README.md · docs/PLAN.md | every version pin (15 tests) | R1 R2 | 1/1 |
| D2 | string-body capture, `DDL_IN_STRING_RE`, literal `ALTER` edge | adapters/sql/src/scan.js | SQL conformance histograms | R3 R5 C1 C5 | 1/1 |
| D3 | `ALTERS` shares the 215 retry | code_atlas/resolver.py | WRITES linking unchanged | A3 | 1/1 |
| D4 | `altered_by*` fields + docstring | code_atlas/tools/search_symbol.py | `Table`/`Function` hits only | R4 C2 | 1/1 |
| D5 | conformance: three `ALTER` cases gain `ALTERS`, new DYNAMIC case + fixture; schema pins | tests/contract/* · tests/fixtures/sql/unmodelled_resolution/alter_table_dynamic.sql · version pins | conformance suite | R2 AC5 | 1/1 |
| D6 | proving tests | tests/test_alters_dynamic_ddl.py | new file | AC1–AC6 | 1/1 |
| D7 | CONVENTION vocabulary (+ R7.6 prunes), TOOLS row, 197-C3, BACKLOG, ledger | docs/* | doc budgets | R7.2 R7.6 | 1/1 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | integration (adapter → store → resolver) | authored, field-shaped | ✅ |
| AC2 | integration | integration (tool payload) | authored | ✅ |
| AC3 | integration | integration | authored | ✅ |
| AC4 | integration | integration + mutation | literal captured on main | ✅ |
| AC5 | contract | conformance | registry fixtures | ✅ |
| AC6 | integration | integration | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_alters_dynamic_ddl.py -q`

Rollback: revert the branch; a v11 index rebuilds once on the way back (R3). Porting: single repo.

`SCOPE: M` (unchanged)

## Phase 3 — Execute

**Branch:** feat/321-dynamic-ddl-alters

Pre-change record — tree `14cae92` plus the uncommitted proving test (historical): `5 failed, 2 passed` — the passes are AC4 (must hold both sides) and AC6 (vacuous before any `ALTERS` exists).

Mutation record (historical, reverted): `_WRITES = ("WRITES", "ALTERS")` in `check_column_defaults.py` → `test_ddl_never_counts_as_a_writer` FAILED; restored, `git diff` empty.

Sweep record — tree `9ddee2c08d736ae3c615a1c130d5750689373321`. Commands: the proving test plus `tests/contract`, `mypy code_atlas`, `tsc -p adapters/sql/tsconfig.json`:

```
344 passed in 7.58s
Success: no issues found in 93 source files
tsc: exit 0
```

Deviation: the two AC tests over the `UserNotes` fixture expect **two** `Table` hits — the literal `ALTER … ADD` in V130 has always emitted a `Table` row of its own. Same cause behind the BACKLOG follow-up (the 215 retry reads them as two candidates); the unqualified-name case gets its own one-table fixture.

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed — A1–A4 implemented-as-approved`

## Phase 4 — Review

REVIEWER: OFF (--no-reviewer)
CHALLENGER: ON — round 1 FINDINGS (20 met, 2 not met, 0 can't tell). Not met: Scope 3 / AC6 — emission was gated file-wide, so `PRINT 'ALTER TABLE dbo.NeverTouched …'` in a file that also ran an unrelated `sp_executesql` emitted a DYNAMIC `ALTERS` (reproduced on the adapter). Fixed in `33a140d`: per-literal runner tracking; the challenger's input and a DDL variable no `EXEC` runs are now tests (`mixed.sql`), plus a `+`-continued statement run by `EXEC (@v)` (`continued.sql`).

Round 2 (same agent, resumed): Scope 3 and AC6 re-judged **met**, after nine adversarial runner shapes reproduced on the adapter (cursor, `EXEC (N'…')`, `sp_executesql N'…'`, `DECLARE … = N'…'` + `EXEC (@v)`, `EXEC @v`, `@stmt = @v`, two variables with one executed, an unexecuted variable). A full-suite run surfaced `tests/test_php_adapter_grammar.py::test_ac4_contract_vocabulary_pins_current_kinds`, a pin `d640cba` missed (R3 "same commit"), fixed in `d6bf6a6`; the other red was this row's missing ledger entry. Residual, within Scope 3's "no control flow": a variable reassigned before its `EXEC` keeps its first value's claim.

Verdict: `findings landed (challenger only — REVIEWER: OFF)`

Ran at b5b88361635b5e3da410f3428162c5f624a0efab

```
$ scripts/gate.sh
== summary ==
  20 passed · 0 failed · 0 skipped
GATE GREEN — all 20 checks passed
```

`REVIEW: CLEAN`
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`

`Reviewed at b5b88361635b5e3da410f3428162c5f624a0efab` · reviewed files: adapters/sql/src/scan.js, code_atlas/contract.py, code_atlas/resolver.py, code_atlas/store.py, code_atlas/tools/search_symbol.py, tests/test_alters_dynamic_ddl.py, tests/contract/adapter_registry.py, docs/CONVENTION.md, docs/TOOLS.md · working doc (embedded, staleness-exempt): docs/tasks/321_dynamic-ddl-in-migrations-leaves-no-trace.md

## Phase 5 — Finalise

Outward (handover-authorised only): pushed `feat/321-dynamic-ddl-alters`, opened [#440](https://github.com/cuongdinhngo/code-atlas/pull/440). Never merge.

Durable lesson: `197-C3` (`the-consumer-owns-its-kind-set`) seen 197, 321 → recurring type-2 claim; proposed destination `docs/ENGINEERING_RULES.md` R3.2 via `/mango:promote` — **not written**. Falsification: still true — `test_the_new_kinds_join_no_existing_named_subset` fails on a contract subset holding `WRITES` (observed this run before the move).

Follow-up (BACKLOG): the duplicate-`Table`-row ambiguity in the 215 retry.

Revert: revert the PR (the index rebuilds once, back to v10).

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| review | challenger | 1 | 103,950 |
| review | challenger | 2 | 48,657 (152,607 cumulative on the resumed agent) |

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`
`LEDGER TOTAL: 152,607 (subagent dispatch only) · top cost driver: review/challenger round 1`
