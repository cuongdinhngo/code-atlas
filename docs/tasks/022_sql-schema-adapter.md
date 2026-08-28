---
id: 022
slug: sql-schema-adapter
title: SQL / DB-schema awareness — a fifth capability, distinct in kind from a source-language adapter
phase: 2
milestone: M9+
status: deferred
depends_on: [019, 020, 021]
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
