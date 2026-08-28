---
id: 184
slug: tsql-source-adapter-tier-1a
title: 'T-SQL source adapter, tier 1a — 378,790 lines held the decisive fact and procs · functions · `EXEC` cost zero contract vocabulary'
phase: 2
milestone: M9+
status: deferred
depends_on: [019, 147, 183]
---

## Why this exists (field retro round 12 §2.b, §15)

Round 12's load-bearing question — *who writes `LedgerTrans.ChangeUser`* — was answered outside the
index, and the retro named this the most important thing in the report:

```
tracked .sql files ................... 2,977
total SQL lines ...................... 378,790
CREATE PROC/FUNC/TRIGGER/VIEW ........ 1,424
CREATE TABLE ......................... 1,466
.sql in indexed_suffixes ............. NO
```

`LedgerTranSummary` write sites: **10 in `src/` PHP, 62 DB-side. 86 % of the write logic for the column
the ticket was about lives outside the index.** `decisive facts in-graph: 1.5 of 6`. Root causes found
by a tool call: **0** — the chain `Insert_AC_Trans_v1` → `DEFAULT (user_name())` → `Score_Calc` →
`LedgerTranSummary` was assembled from `grep`, a hand-written sweep script and `sqlcmd`.

**Why this is a new finding and not a restatement of the scope observation.** Rounds 10–11 classified
out-of-graph facts as dispatch tables, alias registries and file pragmas — all PHP-adjacent, all
genuinely unmodellable by a symbol graph. This is **a second Turing-complete language holding more
lines than the CI scanners, the tests and the `src/` views combined**, and a symbol graph models it
perfectly well. Round 12 §11.e: *"the repo-fit cap is not a permanent property of a legacy PHP
monolith. It is a missing adapter."*

Round 12 §17 records the sharper version: `CLAUDE.md` forbids slicing a body out by line range
because *"that is `read_symbol`'s job"* — and the evaluator ran
`sed -n '163353,163770p' V0.1__baseline_schema.sql`, because there was no alternative. **The
project's own rule has a hole the size of its database layer.**

## The tier split — by contract cost, not by difficulty

Checked against `contract.py` **v8**. This is what makes tier 1a shippable independently:

| Tier | What it emits | Contract cost |
|---|---|---|
| **1a** | `CREATE PROCEDURE` / `CREATE FUNCTION` → node kind **`Function`**; `EXEC <name>` → edge kind **`CALLS`** | **none.** Both exist; `CALLS` is already in `FQN_EDGE_KINDS`, so the resolver links it with no core change |
| 1b | `CREATE VIEW`, `CREATE TRIGGER` | **undecided.** No existing kind fits: a trigger is not callable by name the way a proc is, and a view is not a `Class`. Do not fold them into `Function` to avoid a bump |
| 2 | `CREATE TABLE`; `INSERT INTO t (cols…)` / `UPDATE t SET col=` → a **`WRITES`** edge carrying the column list; `DEFAULT` as a column attribute | **bump (R3).** No node kind for a table, no edge kind for a column write. `REFERENCES` is closest and is in `UNMODELLED_REFERENCE_KINDS`, so reusing it would corrupt `find_references`' honesty evidence |
| 3 | The PHP↔SQL crossing: **331 `<<<SQL` heredocs** and **82 `EXEC <proc>` string literals** in `src/` | bump, and noisy |

**This ticket is tier 1a only.** It is the whole of what round 12 needed by hand:

- `search_symbol("Insert_AC_Trans_v1")` → the definition, instead of `grep -n` over a 240k-line file
- `find_callers("Score_Calc")` → **every proc that invokes it** — precisely how the `admin` value
  reached `LedgerTranSummary`, found by reading proc bodies by hand
- `read_symbol("dbo.Insert_AC_Trans_v1")` → the body, without the forbidden `sed`

**Tier 2 is the tier that detects the defect class**, and it belongs to
[022](022_sql-schema-adapter.md), which is where the vocabulary spend is gated. Round 12 §15: the
one-call query *"which writers of `LedgerTrans` omit `ChangeUser`, and what is that column's DEFAULT?"*
is tier 2, and **FIELD-1020 · FIELD-1027 · FIELD-962 · FIELD-1026 are one defect class** — *a column whose
value comes from a DEFAULT because every writer omits it* — mechanically detectable from it. That is a
`check_architecture_rules`-shaped query, not a search.

**Tier 3 stays unscheduled deliberately.** It is string parsing, it will be noisy, and *"do not ship a
tier nobody has asked for"* is adapter #2's own lesson: eight capability tickets landed in one day and
returned zero for four rounds. Tiers 1a and 2 have a measured ticket behind them; tier 3 does not.

## What this needs before it can start — and it is not code

**Phase 2 is `deferred` for adapters #3–#4 by human ratification (2026-08-04), and the language order
is §18.2's.** This ticket does **not** reorder either, and its `deferred` status and `M9+` milestone
match [022](022_sql-schema-adapter.md) rather than asserting a position.

**The only blocker is a PLAN §19 ratification of where T-SQL sits in the order.** Not capability
(019 proved a second adapter costs zero core abstraction — 156's recorded verdict: **NO core
registry**), not the conformance harness (147 admits a second adapter), and not evidence — which is
the argument:

- **019/020/021 were ordered by expected breadth.** T-SQL's claim is not breadth; it is that a
  *measured, in-anchor, critical-path defect* lived in it. **No other deferred adapter has that**, and
  no adapter in this project's history has had field-measured demand attached before implementation.
- **The honest counter-case, stated at its strongest:** this is `n = 1` repo. Adapter #2 shipped
  eight tickets of correct capability for a language the consumer never asked a question of, and the
  discipline that failure earned is *demand first*. One anchor's two tickets (FIELD-959 for schema
  state, FIELD-1026 for proc structure) is demand from **one consumer**, and a general server that
  reorders its roadmap for one consumer is how R2 gets violated in spirit while passing its grep gate.
- **What would settle it:** tier 1a costs **zero contract vocabulary**, so unlike 022 it spends
  nothing every future user inherits. That asymmetry — free at the contract, gated at the roadmap — is
  the decision §19 has to make, and it is the maintainer's, not this ticket's.

## Scope (only if the ordering is ratified)

1. `adapters/sql/`, self-contained, launched via `CA_SQL_CMD` like every other adapter (R1.1 — no
   language named in the core). Announces `.sql` and its capabilities over the §4.1 handshake.
2. Emit `Function` nodes for `CREATE PROCEDURE` / `CREATE FUNCTION`, with the schema-qualified name as
   the qname per CONVENTION §3 (`dbo.Insert_AC_Trans_v1`) — design records the separator choice and
   why it composes with the existing qname grammar.
3. Emit bare `CALLS` edges for `EXEC` / `EXECUTE` sites, `target_raw` filled, resolver links them
   (R3.3). `sp_executesql` and dynamic proc names are `DYNAMIC` tier or omitted, never `RESOLVED` —
   design records which and why.
4. Pass `tests/contract/` with SQL fixtures (147's per-adapter table), and R6.6's static-analyser and
   R6.3's cross-repo requirements — **the two guardrails adapter #2 shipped without and needed 150 to
   retrofit.** Do not repeat that order.
5. **No contract bump, no core change.** If either turns out to be required, that is a finding: stop
   and record it rather than spending the bump inside a tier-1a ticket.

### Explicitly not in scope

- Tiers 1b, 2 and 3 above. Tier 2 is [022](022_sql-schema-adapter.md).
- Any live database connection. R4/R4.1: the core is deterministic and offline; `INFORMATION_SCHEMA`
  is a runtime probe and 022 already records that it is what actually solved FIELD-959.
- Dialect breadth. T-SQL only, encoded from the T-SQL specification (R2) — never from the anchor's
  proc names, which the R2.2 grep gate will check.

## Constraints, all four evidence-backed

- **A single multi-MB file is the normal shape here, not the exception.** `V0.1__baseline_schema.sql`
  is ~240k lines in **one** file. This is the shape that **killed the PHP adapter** on the anchor —
  ~30 files at 1.2–1.6 MB produced `adapter 'php' exited (code None) with the stream open`, memory
  exhaustion building an AST for one huge literal. **The SQL adapter must stream, not build a
  whole-file AST**, and this constraint is free to write down now and expensive to discover later.
- **Parser choice is bounded by R2, and tier 1a bounds it further.** Tier 1a needs only `CREATE
  PROC/FUNC` headers and `EXEC` sites, so a targeted DDL/`EXEC` scanner encoding the **T-SQL DDL
  grammar** is defensible and keeps the dependency surface at zero. Design must record why the
  heavier options were rejected — in particular a .NET/ScriptDom dependency, which drags a runtime
  into an adapter that does not need one for this tier.
- **The scope-change and shell-build path already exists, and this is its first real use.** Adding
  `.sql` is a suffix-set change, so **172** escalates to `full_build` and reports
  `scope_change: {added: ['.sql'], escalated_to: 'full'}` instead of a silent `wrote.files: 0`; **176**
  (`code-atlas-build`) is how that rebuild runs from a shell; **177** is how it reports progress
  across a build that will be long. Round 12 §11.i(e) judged those three tickets *"motion, not
  progress"* for removing a non-binding constraint — **this is the ticket that makes them
  load-bearing**, and that should be measured, not assumed.
- **`.sql` reaches `indexed_suffixes` only once the graph holds files** (173); `claimed_suffixes`
  names the gap until the build runs. No work needed — recorded so it is not mistaken for a bug.

## Acceptance criteria (only if the ordering is ratified)

1. PLAN §19 carries the ratified ordering decision **before** any parser is written.
2. A fixture `.sql` file yields `Function` nodes for procs and functions with schema-qualified qnames,
   and `CALLS` edges for `EXEC` sites that the resolver links — pinned by `tests/contract/`.
3. **No `contract_version` bump and no `code_atlas/` diff** (R1.1/R3) — asserted by the existing
   grep gates, and the empty core diff recorded the way 019's was (156).
4. A repo with no `CA_SQL_CMD` is byte-identical: no new field, no build cost (061), proven.
5. A multi-MB single-file input parses within a stated memory ceiling — pinned by a large generated
   fixture, because this is the failure mode the PHP adapter already has.
6. R6.6 static analyser and R6.3 cross-repo run land **with** the adapter, not retrofitted (150).
7. Dynamic/`sp_executesql` call sites are tiered per the recorded rule, never `RESOLVED`.
8. `edge_health` reports the SQL slice's own tier mix — **which is why this depends on
   [183](183_edge-health-has-no-per-language-breakdown.md)**: without it, this adapter is
   unevaluatable on the only repo that asked for it, exactly as adapter #2 was in round 12 §13.

## References

Field retro round 12 §2.b (the counts and the 86 % figure), §10.a (0 root causes by tool call), §11.e
(*"a missing adapter, not a property of legacy PHP"*), §15 (the three tiers and the one-call query),
§17.1 (`CLAUDE.md`'s hole). `code_atlas/contract.py` v8 (`NODE_KINDS`, `EDGE_KINDS`,
`FQN_EDGE_KINDS`, `UNMODELLED_REFERENCE_KINDS`). The PHP adapter's multi-MB failure is a recorded
field observation on the anchor, not a repo-side quirk. Related:
[022](022_sql-schema-adapter.md) (tier 2 and the schema-state half — **the gate lives there**),
[019](019_typescript-adapter.md) (a second adapter cost zero core abstraction),
[147](147_contract-harness-is-php-shaped.md) (the harness admits adapter #2+),
[150](150_ts-adapter-has-no-gate-but-its-own-fixtures.md) (the guardrails to ship *with*, not after),
[183](183_edge-health-has-no-per-language-breakdown.md) (without it this is unevaluatable),
[172](172_incremental-is-blind-to-a-scope-change.md) · [176](176_no-full-build-from-a-shell.md) ·
[177](177_a-long-build-is-indistinguishable-from-a-hang.md) (the rebuild path this first exercises).
