---
id: 022
slug: sql-schema-adapter
title: SQL / DB-schema awareness — a fifth capability, distinct in kind from a source-language adapter
phase: 2
milestone: M9+
status: todo
depends_on: [184]
---

## Why this exists (field retro rounds 8–9, 2026-08-25/26)

Two consecutive retro rounds on the anchor PHP monorepo decided a ticket the index could not touch,
because its root cause lived in **database schema state**, not in any source symbol:

> FIELD-959 — a missing BETA column — was settled by `INFORMATION_SCHEMA` queries across three databases
> plus reading a migration's `CREATE TABLE` interior at `V0.1__baseline:41357`. *"A migration's
> `CREATE TABLE` interior is not a queryable fact"* (retro §2). Both rounds list **"DB schema state"**
> among the question types to keep a symbol index out of.

The demand is real and recurring; the supply does not exist. This ticket names the capability so it
has a home in the roadmap — **not** a commitment that a symbol index is the right home for it.

## What this is, and what it is not

- **In kind:** schema/migration awareness — "does column X exist on table Y?", "which migration
  created it?", "which code reads a column this migration drops?". The facts are in `.sql` migration
  files and (at runtime) in `INFORMATION_SCHEMA`.
- **Not a source-language adapter.** Python (020) and C# (021) emit the standard node/edge symbol
  vocabulary; a SQL layer emits **tables, columns, and migration lineage**, which the frozen contract
  (R3) does not model today. Treating this as "adapter #5 like Python/C#" understates that it likely
  needs contract vocabulary of its own — a `contract_version` bump, gated by R3.
- **The honest caveat, recorded up front:** the retros classify DB schema state as *out of scope* for
  a symbol index. This ticket may resolve to *"build it as a separate capability behind its own seam"*
  or to *"decline — runtime `INFORMATION_SCHEMA` is the right tool and no static index should pretend
  to answer it."* Either is a valid close.

## What round 12 split off (2026-08-28)

Field retro round 12 found the anchor's decisive fact in **378,790 lines of T-SQL** and, in doing so,
separated two capabilities this ticket had held as one:

| | Stays here (022) | Moved to [184](184_tsql-source-adapter-tier-1a.md) |
|---|---|---|
| The question | *"does column X exist on table Y? which migration created it?"* | *"which proc writes this table? who `EXEC`s it?"* |
| Vocabulary cost | tables · columns · migration lineage ⇒ **bump (R3)** | procs → `Function`, `EXEC` → `CALLS` ⇒ **none** |
| Gated by | **the evidence gate below** | a PLAN §19 ordering decision, argued in that ticket |

**The gate below is unchanged and still unmet** — round 12 is the same anchor as FIELD-959, so the
demand is two tickets in **one** repo, not two repos. What round 12 changes is only that the *free*
half no longer waits behind the *paid* half: 184 spends no vocabulary any future user inherits, so it
is not this gate's business. Tier 2 there — table/column write-sites, the tier that mechanically
detects *a column defaulted because every writer omits it* — **is** this ticket's, and is the strongest
evidence yet for opening the gate.

## Evidence gate (before any build)

Mirrors the 098 gate — a general server does not spend contract vocabulary every user inherits on
`n = 1`:

1. **A second independent repo** whose real work turns on a schema-state question a symbol index
   cannot answer (FIELD-959 is `n = 1`).
2. **Zero cost when undeclared** — a repo with no SQL layer configured pays nothing (no new required
   field, no build-time work).
3. **A cheaper alternative rejected in writing** — specifically: why a runtime `INFORMATION_SCHEMA`
   probe (which is what actually solved FIELD-959) is not sufficient, given R4's determinism rule bars
   the core from querying a live database at all.

## Scope / Deliverables (only if the gate opens)

- `adapters/sql/`: parse migration DDL (`CREATE TABLE` / `ALTER TABLE`) into table + column facts and
  migration lineage. Static files only — no live DB connection in the core (R4/R4.1).
- Decide the contract shape for table/column/migration nodes; bump `contract_version` and extend the
  conformance suite (`tests/contract/`) per R3.
- Keep it behind its own seam and off by default, like the onboarding LLM (R4.1) — a repo that does
  not configure it is byte-identical to today.

## Acceptance criteria (only if the gate opens)

- The evidence gate above is satisfied in writing before any parser is written.
- Passes `tests/contract/` with SQL fixtures; the source-language core and adapters are unchanged.
- A repo with no SQL layer configured shows no new fields and no new build cost (proven, not asserted).

## References

Field retro rounds 8–9 (FIELD-959; "DB schema state" keep-out list). Plan §3 (roll-out order), §18
(open questions), §19 (decision log). Gate pattern from [098](098_correspondence-relation-seam.md).
Sibling deferred adapters: [020](020_python-adapter.md), [021](021_csharp-adapter.md).

---

## Session status

- **KEY:** 022 · **work_doc_mode:** embed · **Phase:** 0 refine — complete, then **held**.
- Refined jointly with [184](184_tsql-source-adapter-tier-1a.md) in one run; the counted artifacts,
  the recall table and the full ASSUMED list live there and are **not** duplicated here (R7.6).
- **Held because three of the five ASSUMED items are this ticket's** (A1, A2, A4) and each needs an
  explicit human confirm at **this ticket's** Gate 1. 184 runs first.

## Phase 0 — refine (this ticket's slice)

`REFINE: see 184 — one joint run (15 surfaced | 2 asked | 7 cited | 5 ASSUMED | skip: no)`

**Settled (from the maintainer).** This ticket is re-scoped to **tier 2 only** — table/column facts
and column write-sites, both directions (table → its writers, and proc → the tables it writes). The
defect-class *query* that consumes it moves to its own ticket (C), because this one is
adapter + contract and that one is a tool over the resulting graph.

**Declined, and it closes PLAN §18.4.** The schema-state half — *"does column X exist? which
migration created it?"* — is answered **no**, permanently. R4 bars the core from a live database,
`INFORMATION_SCHEMA` is what actually solved FIELD-959, and a static index that guesses at current
schema state is worse than the probe that knows. The index answers *where the code writes a column*;
the database answers *what it currently holds*. This satisfies gate condition 3 ("a cheaper
alternative rejected in writing") for the surviving half by **accepting** it for this one.

**The three ASSUMED items this ticket must ratify at its own Gate 1** (detail in 184's Phase 0):

- **A1** — widening gate §1 to admit a measured defect class of ≥3 tickets in one repo in place of a
  second repo. Round 12 supplies four (FIELD-1020 · 1027 · 962 · 1026). **This widens a gate to admit
  the case standing in front of it, which is the failure mode the gate exists to prevent.** It is the
  maintainer's call and nothing here should read as it having been made.
- **A2** — the contract shape: `Table` + `Column` nodes on the existing `CONTAINS`, plus a new
  Column-targeted `WRITES` edge in `FQN_EDGE_KINDS`. Explicitly not `REFERENCES`.
- **A4** — `CREATE TRIGGER` moves here from 184's tier 1b: a trigger **is** a writer, so excluding it
  makes this ticket's headline answer wrong rather than merely incomplete.

**Gate conditions 2 and 3 are unchanged and both satisfiable**; only §1 is at issue.
