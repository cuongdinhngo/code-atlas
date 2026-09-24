---
id: 022
slug: sql-schema-adapter
title: SQL / DB-schema awareness — a fifth capability, distinct in kind from a source-language adapter
phase: 2
milestone: M9+
status: done
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

- **KEY:** 022 · **work_doc_mode:** embed · **Phase:** 2 design — complete; Gates 0/1/2 closed.
- **The hold is released.** The maintainer handed A1/A2/A4 back ("choose the best approach"),
  so each is resolved and recorded here: **A1 rejected as put** (Phase 1, *Evidence gate —
  disposition*), **A2 and A4 adopted** and tagged `ASSUMED (awaiting ratification)`, ratified
  at the PR. `TRACK: backend` · `TIER: full`.
- Refined jointly with [184](184_tsql-source-adapter-tier-1a.md) in one run; the counted artifacts,
  the recall table and the full ASSUMED list live there and are **not** duplicated here (R7.6).
- **Held because three of the five ASSUMED items are this ticket's** (A1, A2, A4) and each needs an
  explicit human confirm at **this ticket's** Gate 1. 184 runs first.

## Phase 0 — refine (this ticket's slice)

`REFINE: 15 unresolved surfaced | 8 want-decision asked | 7 how-decision resolved+cited | 5 ASSUMED | skip: no`

One joint refine run covered 022 and 184 together, so this is 184's line carried forward verbatim, not a second count. Five of the fifteen landed as `ASSUMED`; three of those five (A1, A2, A4) are this ticket's and are dispositioned in Phase 1.

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

## Phase 1 — analysis

`PREMISE: 31 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`

Resolved: 5 task files (184 · 020 · 021 · 098 · 194), 12 rule ids (R1.1 R1.2 R1.4 R3 R4 R4.1 R4.2
R5.6 R6.2 R6.3 R6.7 R7.6), PLAN §3/§18/§19, 7 symbols (`NODE_KINDS` `EDGE_KINDS` `FQN_EDGE_KINDS`
`CONTAINS` `REFERENCES` `contract_version` `check_architecture_rules`), 4 paths (`adapters/sql/`
`tests/contract/` `code_atlas/contract.py` `code_atlas/architecture_rules.py`). Ambiguous, surfaced:
`INFORMATION_SCHEMA` (a live-database facility, deliberately outside this checkout) and
`V0.1__baseline:41357` (an anchor-repo migration named as external evidence).

`RECALL: 9 claim(s) surfaced | 0 by symbol | 7 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

By handle — the change edits a **shared vocabulary** (`contract.py`'s kind tuples), which is
recall trigger 1: `count-pin-in-blast-radius` (184) · `derived-not-listed-invariant` (128/147/148) ·
`prove-the-guard-fails` (019/147/184) · `two-syntaxes-two-paths` (019/184) ·
`read-the-syntax-not-the-text` (187/190/192) · `emit-do-not-gate-on-resolution` (128) ·
`link-on-the-graph-not-on-the-string` (188). By area (`adapters/sql`, type 5):
`ignored-artefact-outlives-the-branch` (192) · `verify-cited-reference-at-pickup` (149).

`SECTIONS: 7 found | 7 decomposed | ROWS: C=6 R=4 G=2 AC=7`

Sections: *Why this exists* · *What this is, and what it is not* · *What round 12 split off* ·
*Evidence gate* · *Scope / Deliverables* · *Acceptance criteria* · *References*. `STRUCTURE:
synthesized` for C and G — the raw ticket carries no `Constraint` or `Goal` header, so both are
derived from the prose and the rulebook, and Phase 0's re-scope is applied where it supersedes.

| ID | Source | Verbatim (abridged) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | round 12 §15 | *"which writers of `LedgerTrans` omit `ChangeUser`"* | the graph must make writers-per-column derivable | 194 consumes it; no vocabulary today carries it | open |
| G2 | Evidence gate preamble | *"does not spend contract vocabulary every user inherits"* | a repo with no `.sql` must be behaviourally unchanged | `contract.py:47-95` — every consumer reads a **named subset** | open |
| C1 | *What this is not* | *"Static files only — no live DB"* | R4/R4.1 | `test_no_llm_in_core` / gate.sh grep-gates | held |
| C2 | R1.1 | zero language branches in the core | the bump adds kinds, never a branch | `test_core_is_language_agnostic.py` | held |
| C3 | R3 | vocabulary change ⇒ bump + conformance | `CONTRACT_VERSION` 8→9, all 3 adapters re-announce | `adapter.py:230` rejects a mismatch | open |
| C4 | 184 C2 (carried) | peak RSS flat in input size | tier 2 must stay streaming | `tests/test_sql_adapter_memory.py` | open |
| C5 | R5.6 | silence is not evidence | a writer that names no column may not read as writing none | — | open |
| C6 | R6.2 | named construct inventory | every new construct is a registry key + fixture | `tests/contract/adapter_registry.py:448` | open |
| R1 | Scope | *"parse migration DDL into table + column facts"* | `CREATE TABLE` / `ALTER TABLE … ADD` → `Table` + `Column` | — | open |
| R2 | Phase 0 re-scope | *"column write-sites, both directions"* | `INSERT` / `UPDATE` / trigger bodies → `WRITES` | — | open |
| R3 | Scope | *"bump `contract_version` and extend the conformance suite"* | A2's shape, registered as registry rows | — | open |
| R4 | Scope | *"off by default … byte-identical to today"* | no new config key, no new required field | `config.py` unchanged | open |
| AC1 | AC | *"the evidence gate is satisfied in writing"* | see the gate disposition below | — | open |
| AC2 | AC | *"passes `tests/contract/` with SQL fixtures"* | new registry keys green | — | open |
| AC3 | AC | *"no new fields and no new build cost (proven, not asserted)"* | re-derived below — see CL-2 | — | amended |
| AC4 | Phase 0 A4 | `CREATE TRIGGER` is a writer | a trigger body emits `WRITES` like a proc | — | open |
| AC5 | H4 trace | both DEFAULT spellings | inline `DEFAULT` **and** `ADD CONSTRAINT … FOR` | — | open |
| AC6 | C5 | a column-less writer is `DYNAMIC`, never absent | `WRITES → Table` at `DYNAMIC` | — | open |
| AC7 | R6.3 | the extraction holds on real T-SQL | input-shape-dependent — see EXCLUSIONS | — | excluded |

### AC validation — one value re-derived, one mismatch raised

**AC3, "no new build cost".** Re-derived: a `contract_version` bump makes the next incremental run
a **full rebuild** for *every* repo, SQL or not — `indexer.py:239-242`, *"Vocabulary changed —
incremental would mix eras; force a full rebuild"*. So AC3 as literally worded is unsatisfiable by
any bump. Computed value carried forward rather than silently corrected: **AC3 is amended to "no new
field, no new config key, no new per-build cost, and no change to any existing tool's output"** — the
one-time rebuild is the standing, precedented cost of every bump (seven of them, v1→v8) and is
recorded in DISCLOSURE rather than claimed away.

### Clarifications

`CLARIFICATION: 7 raised | 7 self-resolved (cited) | 0 for human decision`

1. **Does evidence gate §1 still bind?** — *self-resolved.* §1 names *"a schema-state question a
   symbol index cannot answer"*. Phase 0 declined the schema-state half **permanently** and closed
   PLAN §18.4. What survives — write-sites parsed from static `.sql` text — is a **source** question,
   the same class as 184. §1's literal condition no longer describes this ticket. Full disposition
   below; **§1's text is left exactly as written.**
2. **AC3 vs the forced rebuild** — *self-resolved*, `indexer.py:239-242`; amended above.
3. **A2, the contract shape** — *resolved on the maintainer's hand-back* ("choose the best
   approach"), tagged `ASSUMED (awaiting ratification)`; ratified at the PR.
4. **A4, triggers** — *resolved on the same hand-back*, tagged `ASSUMED`; ratified at the PR.
5. **Does `WRITES` join `IMPACT_KIND_WEIGHTS`?** — *self-resolved:* **no.** `contract.py:64` —
   *"new EDGE_KINDS must opt in here (not silently join)"* — and R1.2 (YAGNI): 194 queries the edge
   directly and asks for no impact ranking. Joining it would change every impact answer on a SQL
   repo for a use nobody filed.
6. **`MERGE` (T-SQL's upsert)** — *self-resolved:* out of scope for tier 2 v1. It is a **feature
   bound**, not a deferred proof, so it is a scope line and not a coverage-gap exclusion; recorded in
   the adapter README and in *Explicitly not in scope* below.
7. **Migration lineage** (raw Scope, *"and migration lineage"*) — *self-resolved:* declined with the
   schema-state half in Phase 0. *"Which migration created it"* is the question PLAN §18.4 closed.

### The evidence gate — disposition (this is A1, and A1 is REJECTED as put)

- **Gate §1 is NOT widened.** The refine-phase A1 proposed replacing *"a second independent repo"*
  with *"…or a measured defect class of ≥3 tickets in one repo"*. **Rejected.** Round 12's four
  tickets (FIELD-1020 · 1027 · 962 · 1026) are one repo, and one repo's four tickets can share one
  team's single idiom — which is precisely what the word *independent* was guarding. Amending a gate
  to admit the case standing in front of it is the failure mode the gate exists to prevent, and it
  would leave the bar permanently lowered for every ticket after this one. **§1's text is unchanged.**
- **§1 does not apply, because the ticket shed the capability §1 gated.** §1 is scoped to *"a
  **schema-state** question a symbol index cannot answer"*. Phase 0 declined that half permanently.
  Tier 2 reads `CREATE`/`INSERT`/`UPDATE` text out of `.sql` files exactly as tier 1a reads
  `CREATE PROCEDURE` — no database, no runtime, no lineage.
- **The preamble's concern survives §1 and is answered on its own terms.** *"A general server does
  not spend contract vocabulary every user inherits"* still bites, because tier 2 does spend three
  words. It is answered by **proof, not by argument**: `Table`, `Column` and `WRITES` join **no**
  existing named subset — not `TYPE_KINDS`, `CALLABLE_KINDS`, `CLASS_MEMBER_KINDS`, `INHERIT_KINDS`,
  `IMPL_KINDS`, `CALLER_KINDS`, `IMPACT_KIND_WEIGHTS`, `PATH_EDGE_KINDS` or
  `UNMODELLED_REFERENCE_KINDS` — so no existing tool's behaviour moves. That is AC3's proving test,
  and it is what makes the spend genuinely opt-in rather than merely claimed to be.
- **Round 12's four tickets are recorded as demand, which is what they are** — not as a substitute
  for the second repo. Gate condition **2** is satisfied by the proof above; condition **3** was
  satisfied in Phase 0 by *accepting* the cheaper alternative for the declined half.

### Cause / gap analysis

Enhancement. Current: the graph holds T-SQL procs, functions and `EXEC` edges (184) and nothing
about what they write — `scan.js:180-206` emits `CALLS` only. Target: the same scanner also emits
`Table`/`Column` nodes and `WRITES` edges, so *"which writers of T omit C"* is one graph query
(194) instead of four greps and a purpose-built `dbsweep.php` (round 12 §15).

### Blast radius

Handler: `adapters/sql/src/scan.js`. Traced mechanically (the `HANDLES:` table in Phase 2 carries
each command and its output). The bump reaches **3 adapter handshakes** and **6 test pins**; the new
kinds reach **`search_symbol`'s kind filter** and **`store.counts()`'s GROUP BY** (both correct by
construction — a new legal value, a new count row) and **nothing else**, because every other core
consumer reads a named subset. Repos touched: `app` only.

`TRACK: backend — 0/24 touched files under UI paths`
`SCOPE: L` — a contract bump plus a scanner tier; larger than 184 (which spent no vocabulary), and
it does not split further: the vocabulary and the emitter that justifies it must land together or
the bump ships unused.

`BASELINE: green — 2554 passed, 1 skipped in 164.75s`

Ran at `859a2104a6a02a0b726eefce9c55a9f859ec26d1` — the branch point, tree untouched.

```
scripts/docker-test.sh — at the branch point, NOT the tree under review
All checks passed!
2554 passed, 1 skipped in 164.75s (0:02:44)
```

Deliberately not written as a `$ `-prefixed empirical-output record: that shape asserts *this is the
tree under review*, and a baseline is required to be the tree before the change. Its provenance is
the `Ran at` stamp above. The route AGENTS.md names: bare `pytest` on the maintainer's Windows host
is red for two known platform reasons; the one skip is structural (the test that shells out to
`docker`).

## Phase 2 — design

### Approach

Extend **the tier-1a scanner**, not a second one. `scan.js` already streams a `.sql` file line at a
time with a comment/string/delimited-identifier state machine, and every tier-2 construct is read
from the same stripped-to-code line. Tier 2 adds three words to the contract and one accumulator to
the scanner:

- `Table` node — qname is the object's schema-qualified name (`dbo.LedgerTrans`), the same
  file-independent convention tier 1a gave procs, so a write in one file links to a table declared
  in another.
- `Column` node — qname is `dbo.LedgerTrans::ChangeUser`, the container joined with
  `MEMBER_SEPARATOR`, exactly as `\Ns\Class::$prop` is. `extra` carries `data_type` and `default`
  (the DEFAULT expression as written — what 194 AC1 asks for). An `extra` key is not vocabulary
  and costs no bump (`contract.py:163` STUB_FLAG precedent).
- `WRITES` edge — enclosing proc / function / trigger → the Column it writes, `RESOLVED`. It joins
  `FQN_EDGE_KINDS` so the resolver links it by qname lookup, and **joins nothing else**.
- `CONTAINS` carries File→Table and Table→Column. No new containment vocabulary.

**Honest emptiness (C5 / R5.6).** A writer that does not name its columns — `INSERT INTO t VALUES
(…)`, `INSERT INTO t SELECT …` — emits **one `WRITES` targeting the Table at `DYNAMIC`**, never
silence and never a guessed column list. 194 can then say *unmeasured* for that writer instead of
reporting it as omitting the column.

**Streaming is preserved (C4).** The only new cross-line state is a bounded statement accumulator
for the three constructs that span lines (a `CREATE TABLE` body, an `INSERT` column list, an
`UPDATE … SET` list). It is capped; a statement that exceeds the cap is abandoned and degraded to
the `DYNAMIC` table-level `WRITES` above, so peak memory stays flat in file size.

### Rejected alternatives

1. **Reuse `REFERENCES` instead of a new `WRITES`** — zero vocabulary, and it was the cheapest
   option. Rejected: `REFERENCES` is in `UNMODELLED_REFERENCE_KINDS` and carries no direction, so
   *"which writers omit C"* — the entire point (194) — becomes underivable. A read and a write would
   be one row.
2. **`Table` as `Class`, `Column` as `Property`** — also zero vocabulary. Rejected: it is false, and
   PILLAR 2 would render tables as classes in the class diagram and the system map. A contract that
   lies to save a version number is worse than a bump.
3. **Amend evidence gate §1 (the refine phase's A1)** — rejected in Phase 1 above; the gate's text
   stands and the ticket is justified without it.
4. **A separate tier-2 scanner beside `scan.js`** — rejected: two scanners over one grammar is two
   comment/string state machines to keep in step, and R1.2 has no second consumer asking for the
   split.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| 1 | Adding a `NodeKind`/`EDGE_KINDS` member changes no existing tool's behaviour, because every consumer reads a named subset | **verified** — H1/H2 traces below, and CL-9 is the proving test |
| 2 | The resolver links a new FQN edge kind with no resolver change | **verified** — H7 trace: `resolver.py:115-118` dispatches on set membership |
| 3 | `INSERT` is legal T-SQL with `INTO` omitted, and `UPDATE` may target an alias | **verified** — H4 trace; both become registry cases |
| 4 | A capped accumulator keeps peak RSS flat in file size | **novel-untested (runtime)** → resolved by shaping the proving test: `tests/test_sql_adapter_memory.py` re-runs on the tier-2 scanner over the same byte axis and would fail if the accumulator grew with the file |

### Change list (smallest complete set)

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| CL-1 | `CONTRACT_VERSION` 8→9; `NodeKind` += `Table`, `Column`; `EDGE_KINDS` += `WRITES`; `FQN_EDGE_KINDS` += `WRITES` | `code_atlas/contract.py` | 3 adapter handshakes (`adapter.py:230` rejects a mismatch) · 6 test pins · `search_symbol`'s kind filter · `store.counts()` GROUP BY · **nothing else** (H1) | C3, R3, G2 | 1/1 |
| CL-2 | announce v9 | `adapters/{php/index.php,typescript/index.js,sql/index.js}` | all three must move with CL-1 or every build fails the handshake — **proof collateral for CL-1** | C3 | 3/3 |
| CL-3 | tier-2 scanner: `CREATE TABLE` / `ALTER TABLE … ADD` / `INSERT` / `UPDATE` / `CREATE TRIGGER` | `adapters/sql/src/scan.js` | tier-1a output must not move — the 13 existing registry cases pin it | R1, R2, AC4, AC5, AC6 | 1/1 |
| CL-4 | new fixtures, one per construct | `tests/fixtures/sql/*.sql` | R6.2 named inventory | C6 | 9/9 |
| CL-5 | new registry keys, cases and edge shapes | `tests/contract/adapter_registry.py` | `edge_shapes()` sort order; `test_batched_subject_sweep.py` reads `REGISTRY` (the 184-C4 miss) | C6, AC2 | 1/1 |
| CL-6 | version + vocabulary pins | `tests/contract/test_contract_schema.py:68,84,101,173` · `tests/test_php_adapter_grammar.py:250-258` · `tests/test_alias_indirection.py:33` · `tests/test_class_diagram.py:154` | **proof collateral** — H1 traced all six; a shallow grep would have found four | C3 | 6/6 |
| CL-7 | `WRITES` entry + the two node kinds | `docs/CONVENTION.md` §3 | **tier-1 token budget has 18 tokens of headroom** (`agent_chain_cost.py`) — this change must prune tier 1 to pay for itself (R7.6) | R3 | 1/1 |
| CL-8 | prune tier 1 to fund CL-7 | `docs/BACKLOG.md` | `test_agent_chain_budget.py` (25,200) · `test_backlog_bookkeeping.py` | R7.6 | 1/1 |
| CL-9 | **AC3/G2 proving test** — the three new words join no named subset; CONVENTION §3 is derived from `contract.py`, not re-listed | `tests/test_sql_tier2_vocabulary_is_opt_in.py` (new) | closes the `derived-not-listed-invariant` drift H2 found | G2, AC3 | 1/1 |
| CL-10 | **G1 proving test** — round 12 §15's shape | `tests/test_sql_tier2_write_sites.py` (new) | — | G1, AC5, AC6 | 1/1 |
| CL-11 | tier 2 + the `MERGE` bound | `adapters/sql/README.md` | — | R2 | 1/1 |
| CL-12 | §19 decision (gate disposition, A2's shape); contract v9 | `docs/PLAN.md` | `test_doc_size_budget.py` | AC1 | 1/1 |
| CL-13 | status, spend row, claims | `docs/BACKLOG.md` frontmatter · `docs/TOKEN_LEDGER.md` · `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 | 1/1 |

### Recalled handles — every one answered

`HANDLES: 7 recalled | 7 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| Handle | Command | Result → what it changed |
|---|---|---|
| `count-pin-in-blast-radius` | `grep -rn "== 8\b\|NODE_KINDS ==\|EDGE_KINDS ==\|FQN_EDGE_KINDS ==" tests/` | **6 real pins**, in 4 files: `test_contract_schema.py:68,84,101,173` · `test_php_adapter_grammar.py:250-258` · `test_alias_indirection.py:33` · `test_class_diagram.py:154`. Three further `== 8` hits (`total_count`, `suffix`, `core_modules`) are unrelated counts. Folded in as **CL-6**. |
| `derived-not-listed-invariant` | `grep -rln "CONTAINS EXTENDS IMPLEMENTS" docs/ tests/` | `docs/CONVENTION.md` **re-lists both kind tuples by hand and no test derives them from `contract.py`** — live R6.7 drift the bump would widen. Folded in as **CL-9**'s second assertion. |
| `prove-the-guard-fails` | `grep -rn 'WRITES\|"Table"\|"Column"' code_atlas/ adapters/sql/src/ tests/contract/adapter_registry.py \| wc -l` → `0`; `ls tests/test_sql_tier2_write_sites.py` → *No such file* | The pre-change state is provably red on every tier-2 assertion. The red run is recorded at execute, per R6.5. |
| `two-syntaxes-two-paths` | `grep -n "create-procedure\|create-proc-abbrev\|exec-call\|execute-spelling" tests/contract/adapter_registry.py` | Tier 1a already ships each paired spelling as **two** cases. The tier-2 pairs found by the same reading: `DEFAULT` inline **vs** `ALTER TABLE … ADD CONSTRAINT … FOR` · `INSERT INTO t` **vs** `INSERT t` (T-SQL makes `INTO` optional) · `INSERT … VALUES` **vs** `INSERT … SELECT` · `CREATE TRIGGER` **vs** `CREATE OR ALTER TRIGGER`. Each is its own fixture in **CL-4** — this handle is why AC5 exists. |
| `read-the-syntax-not-the-text` | `sed -n '17,20p' tests/test_sql_confinement.py` | The R1.4 guard greps every core `.py` for `\bCREATE (?:TABLE\|INDEX\|TRIGGER\|VIRTUAL TABLE)\b` and `\bINSERT INTO\b`, **case-sensitively, over comments too**. CL-1's comments describe exactly those constructs, so prose would trip it — **4th sighting**. Mitigation is CL-1's wording, not a weakened guard. |
| `emit-do-not-gate-on-resolution` | `grep -c "target_qname" adapters/sql/src/scan.js` → `0` | The adapter emits bare edges and never resolves (R3.3). `WRITES` follows: `target_raw` only, and an unlinkable target stays bare rather than being dropped. |
| `link-on-the-graph-not-on-the-string` | `sed -n '110,125p' code_atlas/resolver.py` | The resolver dispatches on `kind in contract.FQN_EDGE_KINDS` / `PATH_EDGE_KINDS` — **set membership, never the string's shape**. Adding `WRITES` to `FQN_EDGE_KINDS` is therefore sufficient and **no resolver change is in the list**. |

Type-5, by area: `ignored-artefact-outlives-the-branch` — `adapters/sql/node_modules` is gitignored
and survives a `git checkout`, so `shipped_adapters`-style counts must be read on a clean tree.
`verify-cited-reference-at-pickup` — every `path:line` above was re-resolved this session.

### Rule compliance

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) ✅ CL-1 adds kinds, never a branch, and the scanner never imports the core · §2 (change-type) ✅ every construct is the T-SQL spec's, not the anchor repo's names · §3 (change-type) ✅ CL-1 + CL-2 + CL-5 — bump, re-announce, conformance · §4 (change-type) ✅ static files only; identical input yields identical rows · §5 (change-type) ✅ R5.6 is AC6 · §6 (change-type) ✅ CL-4/5/6/9/10, red run recorded at execute · §7 (change-type) ✅ CL-7/8/11/12/13, and the tier-1 add is funded by a prune · §8 (change-type) N/A (no dependency added — the scanner stays Node-stdlib only, as tier 1a is)`

The rule book carries no `handle:` annotations (`grep -n "handle:" docs/ENGINEERING_RULES.md` → 0),
so the recalled-handle source contributes 0 sections; the union is the change-type list.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|---|---|---|---|---|
| G1 | integration | `tests/test_sql_tier2_write_sites.py` — adapter → store → query | authored | ✅ |
| G2 / AC3 | logic | `tests/test_sql_tier2_vocabulary_is_opt_in.py` | n/a | ✅ |
| AC1 | manual-recorded | this document's gate disposition | n/a | ✅ |
| AC2 | integration | `tests/contract/` over the new registry keys | authored | ✅ |
| AC4 | integration | trigger fixture → `WRITES` edges | authored | ✅ |
| AC5 | integration | both DEFAULT-spelling fixtures | authored | ✅ |
| AC6 | integration | column-less `INSERT` fixture → `DYNAMIC` table edge | authored | ✅ |
| C4 | runtime | `tests/test_sql_adapter_memory.py` re-run on the tier-2 scanner | authored | ✅ |
| AC7 | integration | — | **authored only** | ❌ → excluded |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **AC7 — the extraction holds on real T-SQL.** Whether the scanner finds *the write-sites that are
  actually there* in 378,790 lines cannot be written down before running it, so it is
  input-shape-dependent and authored fixtures cannot prove it. `config.real_corpus_path` is `null`,
  stated plainly rather than passed off as proven. Risk tier: medium — a miss understates writers,
  and AC6's `DYNAMIC` arm is what keeps that honest rather than silent. Follow-up: run the scanner
  over the anchor corpus and file the delta. `expiry: when config.real_corpus_path is configured` ·
  `seen: 184` (occurrence 2 of this class; the threshold is 3).

**Explicitly not in scope**, as a feature bound and not a deferred proof: `MERGE` (T-SQL's upsert),
cross-file `ALTER TABLE … ADD CONSTRAINT … FOR` (the file-at-a-time contract cannot reach a table
declared elsewhere), and column-level lineage across migrations — that last one is the half Phase 0
declined permanently.

### Proving test

`tests/test_sql_tier2_write_sites.py::test_writers_omitting_a_defaulted_column_are_derivable` —
builds round 12 §15's shape (a table whose `ChangeUser` column declares `DEFAULT (user_name())`,
plus several `Insert_*_Trans*` procs of which some name the column and some do not), indexes it, and
asserts the graph yields *which writers omit it* and *what the DEFAULT is*. It fails pre-change on
`Table`/`Column`/`WRITES` not existing (H3 trace: 0 occurrences) and passes post-change.

`python3 -m pytest tests/test_sql_tier2_write_sites.py tests/test_sql_tier2_vocabulary_is_opt_in.py -q`

### Rollback + porting

Revert the branch: the three new words leave `contract.py`, the version returns to 8, and an index
built at v9 rebuilds itself on the next run by the same `indexer.py:239` path the bump used. One
repo (`app`); no cross-repo porting.

`SCOPE: L` — confirmed from Phase 1, unchanged.

## Phase 3 — execute

**Deviation from the approved change list: one, recorded.** CL-6 named **6** count pins across four
files. The run found **8**: `tests/test_contract_sole_source.py:53` (`assert len(VOCABULARY) == 42`)
and `CONVENTION.md`'s own entry in `tests/test_doc_size_budget.py`. Neither matches the H1 trace's
pattern, because neither names the thing it counts. Both were folded in; the miss is claim `022-C3`.

**The proving test failed on the implementation, and the design was wrong, not the code.** AC6 needed
a writer that names no columns to be distinguishable from one that omits a column. I put that in
`confidence_tier` — `RESOLVED` onto a column, `DYNAMIC` onto the table — and the integration test
came back with an empty writer set. `resolver.py:104` iterates `iter_unresolved_edges(...,
skip_dynamic=True)`: a `DYNAMIC` edge is **never linked, by design**, so the table-level write
arrived bare and answered nothing. Nothing about the *target* was ever uncertain — the table name is
literal in the source — so the tier was the wrong field. The fix drops the second question rather
than finding a field for it: the **target kind** discriminates (`WRITES`→`Column` named it,
`WRITES`→`Table` did not), both `RESOLVED`, both linked.

The conformance case could not have caught this. It asserts the adapter's returned edge, which was
correct in every field; the defect is one layer down, in what the resolver links. Gate 2 classified
G1's risk layer as *integration* for exactly that reason, and that row is the one that fired.

**Two guards, both red before their fix (R6.5).** `test_convention_publishes_the_contract_vocabulary_
not_a_stale_copy` failed on the stale doc — the drift `derived-not-listed-invariant` predicted, live
in `CONVENTION.md` §3 with no test deriving it. `test_writers_omitting_a_defaulted_column_are_
derivable` failed on the unlinked `DYNAMIC` edge above.

**One guard was avoided rather than tripped.** `read-the-syntax-not-the-text` (rec 3, overdue)
predicted it: `tests/test_sql_confinement.py:18` greps every core `.py` for `\bINSERT INTO\b` and
`\bCREATE (?:TABLE|TRIGGER)\b`, **case-sensitively, comments included**. `contract.py`'s new comments
describe exactly those constructs, so the wording avoids the literal tokens. The guard was not
weakened to make room for prose.

**Budgets: both paid by pruning, neither raised.** Tier 1 had **18 tokens** of headroom before this
change. `CONVENTION.md` grew by the three words and one bullet; `docs/BACKLOG.md` gave the room back
by dropping what round 12 already corrected (adapter #2's zero, stated in three places and no longer
agreeing with itself) and what 022 supersedes (its own `deferred` listing). `PLAN.md` paid for its
§19 entry out of §18.4's closure paragraph, which the task file now holds.

### Delta-green

Ran at `7d4ab631562ff7eccbb72334c06e76cb42a1c6dc` — the tree under review.

```
$ scripts/docker-test.sh
All checks passed!
2572 passed, 1 skipped in 167.05s (0:02:47)
```

**+18 against the 2554 baseline, no new failure, the same one structural skip.** The 18 are 10
conformance cases and 8 assertions across the two new files.

## Phase 5 — finalise

`CLAIMS: 7 claim(s) from 1 lesson entr(ies) | T1=0 T2=7 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 6 recurring | 0 superseded (0 retired) | 3 promotion candidate(s)`
`FALSIFY: 9 candidate(s) checked | 9 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 6 type-2 claim(s) with seen ≥ 2 | 3 routed to a destination | 3 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 3 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md, docs/AGENT_BRIEF.md | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: execute (main-loop)`

The three routed handles are already binding (`derived-not-listed-invariant` → R6.7,
`prove-the-guard-fails` → R6.5, `count-pin-in-blast-radius` → AGENT_BRIEF P5), so their sighting is a
`seen:` bump and nothing more. The three that **cannot promote** all need a human, which an
unattended run does not have: `one-field-two-questions` (rec 2), `two-syntaxes-two-paths` (rec 3,
overdue) and `skip-dynamic-means-unlinkable` — the last is not a promotion but a **re-adjudication**,
because its 2026-08-15 rejection reasoned from a second sighting that *bound a design*, and the third
bound one wrongly first. `LEDGER TOTAL` is `unmeasured` rather than a figure: this host surfaces no
usage block, and an invented number would be worse than the gap.

One type-3 signal went to `docs/SKILL_GAP_CANDIDATES.md` (a counted line truncated at a nested
backtick is reported as a contradicted count); this repo never edits a skill.

### DISCLOSURE

**Nobody reviewed this.** Both seats — the rule-book reviewer and the ticket-blind challenger — were
**waived** by the run arg *"with skipped review"*, and recorded `off` in the RUN CONTRACT. A clean
result here means *clean, nobody looked*.

- **The three ASSUMED decisions were resolved by the agent, on the maintainer's hand-back**
  (*"choose the best approach"*), not ratified by a human. **A1 was rejected as put**; **A2** (the
  contract shape) and **A4** (triggers ride with tier 2) were adopted and remain `ASSUMED (awaiting
  ratification)` until the PR review. A1's rejection is the one to read first: it means the ticket
  argues the gate does not apply, which is a judgement a reviewer may disagree with — and if they do,
  the vocabulary spend is what is at stake, not the code.
- **A `contract_version` bump forces a full rebuild for every repo**, SQL or not
  (`indexer.py:239-242`). AC3's literal *"no new build cost"* is unsatisfiable by any bump; it was
  amended in Phase 1 with the computed value, not passed silently.
- **AC7 is unproven.** The extraction's behaviour on real T-SQL is input-shape-dependent and
  `config.real_corpus_path` is `null`. Recorded as a coverage-gap exclusion with a checkable expiry;
  occurrence 2 of 3 for that class.
- **`UPDATE` through an alias is not resolved.** `UPDATE t SET … FROM dbo.Real AS t` emits a bare
  `WRITES` under the alias name, which the resolver will not link. It is emitted rather than dropped
  (R3.3) but it is not an answer. No fixture claims otherwise.
- **`MERGE`, cross-file `ADD CONSTRAINT … FOR`, and migration lineage are absent by decision.** A
  repo whose writes go through `MERGE` gets an *incomplete* writer set from this adapter, and nothing
  in the graph says so — the honest arm (AC6) covers a statement it *parsed*, not one it never saw.
- **The `PENDING_CAP` degradation path has no fixture.** A statement over 256 KB degrades to a
  `DYNAMIC` table-level write; that branch is reasoned, not exercised.
- **`call-ceiling` and `token-budget` are `unknown`**, and `LEDGER TOTAL` is `unmeasured`: this host
  surfaces no usage block and this project's ledger has no `fresh/calls` history to derive a ceiling
  from. Recorded unknown rather than invented.
- **The 192 ledger row this branch adds was reconstructed from the session that shipped it**, not
  measured at the time — its spend column is the same `unmeasured` as every other row, but its
  narrative is written after the fact.
