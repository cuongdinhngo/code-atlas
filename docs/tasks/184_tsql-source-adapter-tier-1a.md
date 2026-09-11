---
id: 184
slug: tsql-source-adapter-tier-1a
title: 'T-SQL source adapter, tier 1a — 378,790 lines held the decisive fact and procs · functions · `EXEC` cost zero contract vocabulary'
phase: 2
milestone: M9+
status: done
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
is tier 2, and **TKT-1020 · TKT-1027 · TKT-962 · TKT-1026 are one defect class** — *a column whose
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
- **The honest counter-case, stated at its strongest:** this is `n = 1` repo. One anchor's two
  tickets (TKT-959 for schema state, TKT-1026 for proc structure) is demand from **one consumer**,
  and a general server that reorders its roadmap for one consumer is how R2 gets violated in spirit
  while passing its grep gate.
- **Corrected 2026-08-30 — the sentence that used to sit here was false.** It read *"adapter #2
  shipped eight tickets of correct capability for a language the consumer never asked a question
  of."* The retros say the opposite: round 10 §0.g records **three** PHP↔JS questions, **two on the
  critical path**, and round 11 §0.g **two more, both critical-path**. Adapter #2's four consecutive
  zeros were a **roll-out** failure — round 11 §11.e: *"caused by one absent env var, not by any
  capability gap"* — not absent demand. This weakens the demand-first objection to T-SQL and, in the
  same breath, names the risk that actually applies to this ticket: an adapter nobody switches on
  returns zero however good it is.
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
  is a runtime probe and 022 already records that it is what actually solved TKT-959.
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

---

## Session status

- **KEY:** 184 · **work_doc_mode:** embed · **Run args:** `refine` → `analysis` → `design` only ("discuss, analysis, plan"); execute NOT authorised this run.
- **Lane:** interactive `/mango:refine` on **184 + 022 jointly** — one refine run, one exposure-checker dispatch, counts below cover both tickets.
- **Branch:** none — refine and analysis write no code.
- **Current phase:** 5 finalise — PR [#231](https://github.com/cuongdinhngo/code-atlas/pull/231) open. Review phase SKIPPED per run arg; the maintainer reviews on the PR.

## Phase 0 — refine

`PREMISE: 40 reference(s) checked | 0 missing | 6 ambiguous (surfaced, not blocking)`
`RECALL: 8 claim(s) surfaced | 0 by symbol | 6 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 15 unresolved surfaced | 8 want-decision asked | 7 how-decision resolved+cited | 5 ASSUMED | skip: no`

**Re-emitted 2026-08-30** after `check_lines.py` rejected the first `REFINE:` line for `U != a + b`.
The first run set `a` to the number of typed-UI questions (2) instead of the number of want-decisions
exposed (8): want and how are an exhaustive binary over the 15, and 8 + 7 = 15. Re-deriving also
found an **eighth** recalled claim the first pass missed — see row 8.

Not an epic — four deliverables, but each is an independently execute-able ticket with its own
lifecycle, not a feature-suite needing a split gate.

**Premise.** Every resolvable identifier both tickets frame as existing resolves: `contract.py` v8
(`CONTRACT_VERSION` :26, `EDGE_KINDS` :50, `FQN_EDGE_KINDS` :65, `UNMODELLED_REFERENCE_KINDS` :91),
`tests/contract/`, `adapters/{php,typescript}`, `indexed_suffixes` (`store.py:43`) /
`claimed_suffixes` (`tools/collection.py:54`), the five tool symbols, all 14 cross-referenced task
files, PLAN §3/§4.1/§18/§19, CONVENTION §3, R1.1/R2.2/R3.3/R4.1/R6.3/R6.6. **All three `depends_on`
(019, 147, 183) are `done`**, as are 150, 156, 172, 173, 176, 177. Ambiguous, surfaced not blocking:
the six anchor-repo names (`V0.1__baseline_schema.sql`, `Insert_AC_Trans_v1`, `Score_Calc`,
`LedgerTranSummary`, `LedgerTrans.ChangeUser`, the consumer ticket ids) live in an external repo the ticket
declares as field observation. `adapters/sql/`, `CA_SQL_CMD` and `.sql` in the suffix set are
to-be-created — never missing.

**Recalled claims (ADVISORY — surfaced only; injected nothing, blocked nothing).**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `emit-do-not-gate-on-resolution` (128-C1) | 2 | handle — new adapter, new core module | **Load-bearing.** Both adapters discard the string literal and write the sentinel `'(dynamic)'` (`Visitor.php:254,518,606,867`; `parse.js:419-420`), so the crossing datum is destroyed *at the adapter*. This claim names exactly that. Motivates A0′ |
| 2 | `evidence-shaped-honesty-inverts-on-a-second-instance` (186-C1) | 2 | handle — third producer | **Load-bearing.** See the finding below |
| 3 | `an-aggregate-outlives-the-world-that-named-it` (183-C1) | 2 | handle — a dimension gains a third value | **Load-bearing.** Its own `destination:` names "whichever ticket adds adapter #3" — this one |
| 4 | `link-on-the-graph-not-on-the-string` (188-C1) | 2 | handle — threads a value through callers | Relevant: A0′ links a literal, so 188's rule bounds how |
| 5 | `derived-not-listed-invariant` (R6.7, rec 20) | 2 | handle — shared vocabulary | Relevant: the SQL conformance row is `set(adapter.cases)`, never re-listed (147) |
| 6 | `same-file-symbol-map-scope-per-container` (128-C2) | 5 | area — adapters | Relevant: a proc-name map keyed on the bare name collides across schemas |
| 7 | `verify-cited-reference-at-pickup` (149-C1) | 5 | area — process | Applied: all 40 premise references re-verified above |
| 8 | `two-syntaxes-two-paths` (019-C2) | 2 | handle — a construct reached by two syntaxes | **Missed by the first pass** (recurrence 1, so absent from the class index the pass keyed on). T-SQL has three such pairs: `EXEC`/`EXECUTE`, `CREATE PROC`/`PROCEDURE`, `CREATE`/`CREATE OR ALTER`. R6's inventory must parametrise over both spellings, not pick one |

**Settled wants (from the maintainer — become AC constraints).**

| # | The want | Chosen direction (not a tool) | Becomes AC constraint |
|---|---|---|---|
| W1 | Where does T-SQL sit in the roadmap? | **Ratified ahead of Python (020) and C#/.NET (021).** Measured in-anchor demand outranks expected breadth; tier 1a spends no vocabulary a future user inherits | AC1's §19 entry must record the reversal **and its reason**, not just the new order |
| W2 | What gets built | **Four tickets**: A=184 tier 1a + census · A′=192 cross-language literal call sites · B=022 tier 2 + triggers · C=193 defect-class query | Scope of this ticket is A only |
| W3 | Is the crossing a PHP↔SQL feature? | **No — it is language-agnostic.** A′ is a core capability serving 019/020/021 and every later adapter; SQL is only its first consumer with measured demand | A′'s ticket text carries no language name; T-SQL appears in fixtures only (R2) |

**Resolved direction + citation (how-decisions — refine-resolved, NOT asked).**

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | Can 022 start now? | No — evidence-gate §1 ("a second independent repo") is unmet; round 12 is the same anchor as TKT-959 | `022` *Evidence gate* §1 + *"the gate below is unchanged and still unmet"* |
| H2 | Contract cost of this ticket | Zero: `CALLS` is already in `FQN_EDGE_KINDS`; no bump, no `code_atlas/` diff | `184` Scope §5, AC3; `contract.py:65` |
| H3 | Is 184 blocked on capability? | No — 019, 147, 183 all `done`; only the §19 ordering blocked it, and W1 settles that | `184` *What this needs… is not code*; frontmatter statuses |
| H4 | Parser direction (not tool) | Stream; never build a whole-file AST — one ~240k-line file is the normal shape | `184` Constraints §1 |
| H5 | Sequencing 184 vs 022 | 184 first (free at the contract), 022 second (spends the bump) | both tickets' split table |
| H6 | This run's stopping point | Phase 0 → 1 → 2; no execute | maintainer's request: "discuss, analysis, plan" |
| H7 | Fixture sourcing | T-SQL spec only, never the anchor's proc names; tiers 1b/2/3 out of *this* ticket | `184` *Explicitly not in scope*; R2.2 |

**ASSUMED (awaiting ratification) — each needs an EXPLICIT human confirm at Gate 1. Silence ≠ approval.**

| # | Assumed choice | Why ASSUMED | Confirm at | Reverses a prior decision? |
|---|---|---|---|---|
| A1 | 022's gate §1 widened to *"a second independent repo **or** a measured defect class of ≥3 tickets in one repo the vocabulary mechanically detects"* (round 12 supplies 4) | Handed back ("suggest the best approach"). **This widens a gate to admit the case in front of it — the failure mode the gate exists to prevent** | Gate 1 of **022**, not this ticket | Yes — amends a ratified gate |
| A2 | Contract shape for B: `Table` + `Column` nodes joined by existing `CONTAINS`; new `WRITES` edge, Column-targeted, opted into `FQN_EDGE_KINDS`. Not `REFERENCES` — it is in `UNMODELLED_REFERENCE_KINDS` (`contract.py:91`) and reuse corrupts `find_references`' honesty | Handed back; exposure-checker item 1 | Gate 1 of **022** | No |
| A3 | AC5's memory ceiling stated as **constant in input size** (~20 MB and ~200 MB fixtures, `peak_rss_children_kb` growth < 1.25×) plus a 512 MB absolute backstop — not an invented MB figure | Handed back; exposure-checker item 2. 015 deliberately set no numeric SLA (`scripts/scale_full_build.py:97`) | Gate 1 of **this** ticket | No |
| A4 | `CREATE TRIGGER` moves from tier 1b into B (tier 2), because a trigger **is** a writer and excluding it makes the WRITES answer wrong | My recommendation; not explicitly ratified | Gate 1 of **022** | Partially — 184's tier table puts triggers in 1b |
| A5 | ~~emit-don't-gate as primary~~ → **REVERSED at Gate 0 by my own investigation.** The crossing is **config-driven**: the proc name sits inside a T-SQL statement inside an *argument* string (`$db->exec("EXEC dbo.Proc")`), not at the callee position, so no language-neutral adapter rule can extract it without knowing which sink executes SQL. That is `enrichment.py`'s `calls`-rule shape | Handed back 2026-08-30 ("chọn the best approach") | Gate 1 of **193** | Reverses my own earlier recommendation, not a human decision |

**Constraints surfaced from the scan.**

- **Finding — tier 1a alone ships a known regression.** Today `find_callers("dbo.Score_Calc")`
  answers `no_such_symbol`: an honest miss. After tier 1a it answers `reason=ok` with the DB-side
  callers only, silently omitting every call site named by a string literal in another language.
  186's per-language census **cannot** catch this: it asks *"does the **subject's** language emit
  these kinds?"* (`coverage.py:29-43`) and SQL does emit `CALLS`. Worse, `find_callers` never
  consults the census at all — 186 wired it into `find_references` and `include_graph` only. And
  `impact` emits **no `reason` whatsoever** on an empty radius (`impact.py:207-216`), documented as a
  deliberate "modelled zero". `impact` is the tool a supervising agent calls to ask *"is this safe to
  change"*.
- **Therefore A0 carries a cross-language pair census**: count edges by ordered pair (source
  language → target language). Both languages indexed but the pair empty ⇒ every answer about a
  subject in the target language is *partial*. A pure data question with no language name (R1.1),
  extending the single `edges ⋈ files` scan 183 already runs. **Cost must be measured** — 183 cost
  ~1.0 s for the source side alone and the target side needs a further join through `nodes`.
- **Cross-language linking already works and needs no core change.** `resolver.py:111-127` filters
  `nodes_by_qualified_names` by node kind only, with no language or adapter predicate;
  `store.py:733` states outright that *"a cross-language edge is one row of the source language"*.
  Neither existing adapter produces one only because TS `resolveSpecifier` resolves to TS/JS files
  and PHP `IMPORTS` carries an FQN, not a path.
- **Correction to an earlier reading, recorded so it is not repeated:** `PROVIDES_VIEW_DATA` is
  **not** a cross-boundary precedent. Its `target_raw` is the synthetic `viewdata:<key>`, it has no
  target node, it is in neither `FQN_EDGE_KINDS` nor `PATH_EDGE_KINDS`, and the resolver never links
  it (`contract.py:180`). The real precedent is PHP's string-literal callables at `HEURISTIC`
  (`Visitor.php:590-620`) which the core **does** match against the node table (`resolver.py:176-184`).
- Suffix ownership is exclusive with a duplicate-claim check (`indexer.py:746-750`), so `.sql`
  claimed by one adapter is clean.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch — not a debate): 2 un-exposed
product-decisions found, both WANT, both re-classified above — the contract shape for
table/column/migration facts (→ **A2**) and AC5's numeric memory ceiling (→ **A3**). None beyond those.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** L · **TIER:** full

`PREMISE: 40 reference(s) checked | 0 missing | 6 ambiguous (surfaced, not blocking)` — carried forward from Phase 0, not re-run.
`RECALL: 7 claim(s) surfaced | 0 by symbol | 5 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)` — carried forward from Phase 0.
`SECTIONS: 8 found (Why this exists, The tier split, What this needs before it can start, Scope, Explicitly not in scope, Constraints, Acceptance criteria, References) | 8 decomposed | ROWS: C=6 R=6 G=2 AC=8`
`CLARIFICATION: 6 raised | 3 self-resolved (cited) | 3 for human decision`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green — 2489 passed, 1 skipped in 164.70s`

```
$ bash scripts/docker-test.sh        # Ran at 12150c1 (container built from this tree)
2489 passed, 1 skipped in 164.70s (0:02:44)

$ bash scripts/docker-test.sh        # Ran at 9c478f3 — the delta, after the adapter landed
2552 passed, 1 skipped in 133.88s (0:02:13)
[exited with code 0]
```

Re-run at `12150c1` after `check_lines.py` refused the first capture as evidence from another tree
(`6992aff`, before the scaffold merged). **2,489 rather than README's 2,483**: the six extra are the
bookkeeping, budget and doc-size tests re-parametrised over the three ticket files and the BACKLOG
rows PR #230 added. Still exactly one structural skip, that one skip being `test_runtime_image_reports_server_build`, which
shells out to `docker` and cannot from inside the test image. Structural and permanent, not a red
run. Host: this Linux box, not the maintainer's Windows dev host.

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title / Why | 378,790 lines held the decisive fact; procs · functions · `EXEC` cost zero vocabulary | make the DB half of the anchor queryable at zero contract cost | round 12 counts; `contract.py:65` | open |
| G2 | Why §17 | the project's own rule has a hole the size of its database layer | `search_symbol` / `find_callers` / `read_symbol` replace `grep`, a hand sweep, and a forbidden `sed` | round 12 §17.1 | open |
| R1 | Scope 1 | `adapters/sql/` self-contained, launched via `CA_SQL_CMD`, announces `.sql` over the §4.1 handshake | generic env convention, no language in the core | `config.py:25` `ADAPTER_CMD_ENV`; `adapter.py:344` | open |
| R2 | Scope 2 | `Function` nodes for `CREATE PROCEDURE` / `CREATE FUNCTION`, schema-qualified qname | design records the separator choice against CONVENTION §3 | `CONVENTION.md:75` | open |
| R3 | Scope 3 | bare `CALLS` edges for `EXEC` / `EXECUTE`; dynamic never `RESOLVED` | R3.3 — adapter emits bare, resolver links | `contract.py:65`; `resolver.py:105` | open |
| R4 | Scope 4 | pass `tests/contract/` with SQL fixtures, **plus** R6.6 static analyser and R6.3 cross-repo, landing *with* the adapter | 150's lesson: guardrails ship with, never retrofitted | `tests/contract/adapter_registry.py` | open |
| R5 | Scope 5 | no contract bump, no core change — **if either is required, that is a finding: stop and record** | this clause fires; see Q1 | ticket line, Scope §5 | **fired** |
| R6 | **derived** (R6.2 + lesson 149) | name the T-SQL construct inventory in the rule book **before the first fixture** | R6.2 names PHP (11) and TS/JS (15); **there is no T-SQL list** | `ENGINEERING_RULES.md` R6.2 | open |
| C1 | The tier split | tier 1a only — 1b/2/3 excluded, by contract cost not difficulty | `CREATE VIEW`/`TRIGGER` deferred because no existing kind fits | ticket table | binding |
| C2 | Constraints 1 | a single multi-MB file is the normal shape; **stream, never build a whole-file AST** | this is the failure mode the PHP adapter already has | ticket line | binding |
| C3 | Constraints 2 | parser choice bounded by R2; heavier options rejected in the design record | in particular a .NET/ScriptDom runtime dependency | ticket line | binding |
| C4 | Constraints 3 | 172 / 176 / 177 get their first real use — **measured, not assumed** | a scope-change escalation to `full_build` must be observed | `docs/tasks/172,176,177` (all `done`) | binding |
| C5 | Constraints 4 | `.sql` reaches `indexed_suffixes` only once the graph holds files (173) | no work — recorded so it is not mistaken for a bug | `store.py:43`; `tools/collection.py:54` | binding |
| C6 | Explicitly not in scope | tiers 1b/2/3 · any live DB connection · dialect breadth | T-SQL from the spec, never the anchor's proc names | R2.2 grep gate | binding |
| AC1 | AC 1 | PLAN §19 carries the ratified ordering **before** any parser is written | decision settled at refine (W1); **the §19 entry is not yet written** | Phase 0 W1 | open |
| AC2 | AC 2 | fixture `.sql` → `Function` nodes with schema-qualified qnames + resolver-linked `CALLS` | pinned by `tests/contract/` | registry row + fixtures | open |
| AC3 | AC 3 | **no `contract_version` bump and no `code_atlas/` diff** | **conflicts with the Phase-0 census scope — see Q1** | 74 files under `code_atlas/` | **conflict** |
| AC4 | AC 4 | a repo with no `CA_SQL_CMD` is byte-identical: no new field, no build cost | 061's precedent | `docs/tasks/061` | open |
| AC5 | AC 5 | a multi-MB single file parses **within a stated memory ceiling** | **no ceiling is stated anywhere — see Q2** | `scale_full_build.py:97` ("no numeric SLA") | **not falsifiable as written** |
| AC6 | AC 6 | R6.6 static analyser and R6.3 cross-repo land **with** the adapter | duplicate of R4's second half; kept as the proof row | `docs/tasks/150` | open |
| AC7 | AC 7 | dynamic / `sp_executesql` tiered per the recorded rule, never `RESOLVED` | falsifiable **once design records the rule**; `resolver.py:105` already skips DYNAMIC | `resolver.py:105` | open |
| AC8 | AC 8 | `edge_health` reports the SQL slice's own tier mix | **already built by 183** — `edge_health_by_language` exists; this is a proof, not a build | `store.py:730`; `indexer.py:975-977` | open (proof only) |

### AC validation

| AC | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 question |
|---|---|---|---|---|---|
| AC1 | §19 entry before any parser | settled at refine; entry unwritten | Y | greppable | — |
| AC2 | Function nodes + linked CALLS | consistent with `contract.py:65` | Y | conformance case | — |
| AC3 | zero `code_atlas/` diff | the Phase-0 census needs **≥6** core files (`store.py`, `indexer.py`, `coverage.py`, `nav_result.py`, `find_callers.py`, `impact.py`) | **N** | greppable | **Q1** |
| AC4 | byte-identical when unconfigured | 061's method applies unchanged | Y | greppable | — |
| AC5 | "a stated memory ceiling" | **no number exists** in rules, CONVENTION or PLAN | **N** | **neither** | **Q2** |
| AC6 | guardrails land with | R6.6/R6.3 both codified | Y | CI gate | — |
| AC7 | never `RESOLVED` | rule not yet recorded | Y | greppable once recorded | — |
| AC8 | SQL slice tier mix | already shipped by 183 | Y | assertion | — |

### Inventory (universal requirements)

- **AC3 "no `code_atlas/` diff"** — denominator **N = 74** files under `code_atlas/`. Proven by an
  empty core diff recorded the way 019's was (156), not by assertion.
- **R4 / R6.2 conformance cases** — denominator **N = undefined**: R6.2 names PHP (11 constructs) and
  TS/JS (15), and **no T-SQL inventory exists**. Lesson 149 (`name-the-spec-inventory-before-the-first-fixture`)
  is exactly this failure. R6 above is the row that closes it; N is set when the inventory is named,
  and every case gets its own checklist row — not an aggregate.

### Gap analysis (enhancement — current vs target)

| Goal | Current | Target | Gap |
|---|---|---|---|
| G1 | `.sql` is unowned: `adapters/` holds `php`, `typescript` only; `indexer.py:746-750` assigns suffixes exclusively | a third adapter owns `.sql` and emits `Function` + `CALLS` | a new self-contained adapter + one `adapter_registry.py` row |
| G2 | `read_symbol` cannot address a proc, so the body is reachable only by the `sed` `CLAUDE.md` forbids | `read_symbol("dbo.X")` returns the body | falls out of G1 once nodes carry `line_start`/`line_end` |
| Honesty | `find_callers` consults **no** census (`coverage.py` is wired into `find_references` and `include_graph` only); `impact` emits **no `reason`** on an empty radius (`impact.py:207-216`) | a partial cross-language answer is marked partial | **a core change — which AC3 forbids. Q1.** |

### Blast radius

- **Additive, outside the core:** `adapters/sql/**` (new), `tests/contract/adapter_registry.py` (one
  row), `tests/fixtures/sql/**` (new), `docs/ENGINEERING_RULES.md` R6.2 (the T-SQL inventory), CI
  static-analyser job, `docs/PLAN.md` §19 + §18.4, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`.
- **Core, only if Q1 folds the census in:** `store.py`, `indexer.py`, `tools/coverage.py`,
  `tools/nav_result.py`, `tools/find_callers.py`, `tools/impact.py`.
- **Repos touched:** `app` (the only entry in `config.repos`).
- No `db-map` exists in `docs/` (`db_kind` is `null`), so no schema-dependent widening applies.

### `RULE SECTIONS`

`RULE SECTIONS: 9 applicable — 7 by change-type | 2 by recalled handle — §R1.1 (change-type) ✅ new adapter names no language in the core; launched by the generic per-language CMD env convention (config.py:25) · §R1.4 (change-type) ✅ the adapter parses only and never imports store.py · §R2/R2.2 (change-type) ✅ fixtures come from the T-SQL spec; R6 names the inventory first · §R3 (change-type) ✅ zero vocabulary spend — CALLS is already in FQN_EDGE_KINDS (contract.py:65) · §R4/R4.1 (change-type) ✅ static files only, no live DB connection (C6) · §R6.2 (change-type) ⚠ NOT SATISFIABLE TODAY — no T-SQL construct inventory exists; R6 is the row that closes it · §R6.3+R6.6 (change-type) ✅ both land with the adapter per R4/AC6, not retrofitted (150) · §R6.5 (recalled handle: prove-the-guard-fails) ✅ every new fixture must be shown failing before it is trusted · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ the SQL conformance valid-set is set(adapter.cases), never re-listed (147)`

### Gate 0 — the three questions, and the answers (handed back 2026-08-30)

**All three were handed back ("dựa vào investigation, bạn hãy chọn"), so all three are `ASSUMED (awaiting ratification)` and need an explicit confirm at Gate 1 — silence is not approval.** The questions are kept below as they were asked; each answer follows it.

**Q1 — AC3 vs the census: where does the honesty fix live?** AC3 forbids any `code_atlas/` diff, and
Scope §5 says in terms: *"If either turns out to be required, that is a finding: stop and record it
rather than spending the bump inside a tier-1a ticket."* **That clause has now fired.** The census
needs ≥6 core files. My recommendation: **split it into its own ticket (192) and keep 184's AC3
intact** — which is the ticket's own instruction, not a workaround.

**Q2 — AC5's ceiling.** Confirm ASSUMED **A3** explicitly (constant-in-input-size: ~20 MB and
~200 MB fixtures, `peak_rss_children_kb` growth < 1.25×, 512 MB absolute backstop), or state a
different bar. Until one is chosen AC5 may not carry a `✅`.

**Q3 — a new finding that changes the census's shape.** An empty language pair is **not by itself**
evidence of a gap. PHP→TS is empty today and that is *correct* — a PHP backend does not call TS.
PHP→SQL empty while PHP demonstrably `EXEC`s procs **is** a gap. A pair census alone cannot tell them
apart, so on its own it would emit false alarms. The discriminator has to be **unlinked/dynamic
evidence** — the same 065 pattern `relationship_not_modelled` already uses — and the adapters
currently destroy it (`'(dynamic)'` at `Visitor.php:254,518,606,867`, `parse.js:419-420`). That makes
the census **depend on** A′'s emit-don't-gate direction (**A5**) rather than being independent of it.
Confirm that reading before design commits to either.

**Self-resolved (cited), for the record:** AC1 is unblocked — W1 settled the decision, only the §19
entry remains. AC8 is a **proof, not a build**: 183 already shipped `edge_health_by_language`
(`store.py:730`). R6 is a required deliverable the ticket never listed — R6.2 names PHP and TS/JS
inventories and no T-SQL one, which is lesson 149 verbatim.


### Gate-0 answers — `j` closed to 0 by delegation, NOT by agreement

`CLARIFICATION: 6 raised | 3 self-resolved (cited) | 3 handed back → ASSUMED (A3, A6, A7)`

**A6 (was Q1) — the census is split out; AC3 stays intact.** Scope §5's *"stop and record"* clause is
followed literally rather than worked around. 184 ships tier 1a with an empty `code_atlas/` diff
recorded the way 019's was (156). **No released regression**, because the adapter is opt-in (AC4): a
repo that never sets `CA_SQL_CMD` is byte-identical. **Recorded operational caveat, and it belongs in
this ticket's runbook note: do not enable `CA_SQL_CMD` on the anchor until 192 has landed**, or
`find_callers` on a proc answers `reason=ok` while omitting every call site named from another
language.

**A3 (was Q2) — the ceiling is constant-in-input-size, not an MB figure.** Two generated fixtures
(~20 MB and ~200 MB), `peak_rss_children_kb` growing < 1.25× between them, plus a 512 MB absolute
backstop. **The reason is C2, not convenience:** C2 makes *"stream, never build a whole-file AST"*
binding, and an absolute MB threshold **passes even for an AST-building parser** whenever the input
is small enough. Only the ratio falsifies the thing C2 actually forbids. The instrument already
exists (`scripts/scale_full_build.py:91`); 015 deliberately set no numeric SLA (`:97`), so inventing
one now would be the arbitrary half.

**A7 (was Q3) — the cross-language pair census is WITHDRAWN. It was the wrong design.**
`store.py:1235` `count_unlinked_by_target_raw` already exists and is documented as *"Evidence that a
relationship exists in the table but the resolver never links that kind"* (065). `find_references`
uses it; **`find_callers` does not**, though it already carries `frontier_skipped_non_resolved`
(`find_callers.py:278`). The right evidence is **per-subject, not per-population**: an unlinked edge
whose `target_raw` names *this* subject. That dissolves Q3's false-alarm problem outright — PHP→TS
being legitimately empty produces no such edge, so nothing fires, while an unlinked edge naming
`Insert_AC_Trans_v1` fires precisely. **No new reason code, no new meta stamp, no `edges ⋈ nodes ⋈
files` double join, and none of the ~1.0 s per-build cost 183 measured for the source side alone.**

### The change list this produces — five tickets, one of them already correct today

| # | Ticket | Scope | Core diff? |
|---|---|---|---|
| 1 | **192** (new) | `find_callers` has no unmodelled-reference arm — wire the existing `count_unlinked_by_target_raw` in; check `impact`'s bare modelled zero (`impact.py:207-216`) against the same gap | yes, small |
| 2 | **184** (this) | tier 1a only; AC3 intact | **no** |
| 3 | **193** (new) | extend `enrichment.py`'s `calls` rule so `target_raw` comes from the string literal and resolves by FQN — language-agnostic, config-driven, off by default | yes |
| 4 | **022** | tier 2 + `CREATE TRIGGER` (A4), both directions | bump 8→9 |
| 5 | **194** (new) | the defect-class query over B's graph | no |

**192 goes first, and it is justified without SQL at all:** PHP already emits callable-string `CALLS`
at `HEURISTIC` (`Visitor.php:590-620`) and the ones that fail to resolve stay unlinked — invisible to
`find_callers` today. That is a present-tense, measurable defect on the two adapters already shipped,
so 192 is provable on the current index and does not wait on this ticket.

Once 193 exists, the 065 arm gives honesty **for free** in both branches: the edge links and the
answer is complete, or it stays unlinked and the arm fires with subject-correct evidence.

## Phase 2 — design

### Approach

**A dependency-free streaming scanner in Node, launched as `CA_SQL_CMD`, emitting `Function` nodes
and bare `CALLS` edges — no core change, no vocabulary spend.**

T-SQL files are a sequence of **batches** separated by `GO` on its own line, and tier 1a needs only
two constructs out of them. So the adapter holds a small state machine over the byte stream — in
line-comment (`--`), in block-comment (`/* */`), in string (`'…'` with `''` escape), in delimited
identifier (`[…]`) — and never materialises the file:

- `CREATE [OR ALTER] {PROC|PROCEDURE|FUNCTION}` at statement position → a `Function` node.
  `line_start` at the header; `line_end` at the batch terminator.
- `EXEC|EXECUTE <name>` inside a body → a bare `CALLS` edge, `source_qname` = the enclosing proc.
- `EXEC (@sql)` / `EXEC sp_executesql` → `DYNAMIC`, `target_raw='(dynamic)'` (see H1 below).

Memory is **O(1) in file size** — one line plus the current header. That is exactly what C2 demands
and what AC5's ratio test falsifies.

**Qname:** the schema is the container and `.` is its native separator, so
`dbo.Insert_AC_Trans_v1` — the same shape as PHP's `\ns\func`. **Traced, not assumed:**
`MEMBER_SEPARATOR` is `::` (`contract.py:184`), so `split_qname("dbo.X")` finds no member and returns
container `None` (`resolver.py:152-156`). A `RESOLVED`-tier `EXEC` edge therefore either matches a
node qname outright (`resolver.py:135`, `nodes_by_qualified_names` — **no kind filter and no language
filter**, which is why this crosses languages for free) or stays unlinked. It never falls into the
bare-name or receiver-type branches, which are gated on `incoming == "HEURISTIC"` and on a
`::`-container respectively. The grammar composes with no core change.

**Runtime: Node, no npm dependency.** Not because JS is nicer — because of three concrete facts.
(1) `node` is already required by CI and the test image for the TS adapter, so it adds no runtime.
(2) R6.6 needs a static analyser at its strictest clean setting, and lesson 150 already worked out
the recipe for an untyped-JS adapter (`tsc --checkJs` strict) — a known recipe beats a new one.
(3) **R1.4 is structurally enforced rather than grepped**: a Node process *cannot* `import
code_atlas.store`, where a Python adapter in this repo could and only a grep gate would stop it.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| **.NET / `Microsoft.SqlServer.TransactSql.ScriptDom`** | The correct T-SQL parser, and wrong here: it drags a .NET runtime into CI, the test image and every contributor's machine for two constructs. C3 names this option specifically and asks for the rejection in writing. It also builds a full AST — the one thing C2 forbids |
| **A Python adapter** | Cheapest to write and mypy-strict is already configured — but it puts the adapter one `import` away from `store.py`, leaving R1.4 defended by a grep gate instead of by process boundary. Rejected on structure, not effort |
| **Reuse the PHP adapter's process** | Would put T-SQL knowledge in a PHP-named adapter; `indexer.py:746-750` assigns suffixes exclusively, so `.sql` needs its own owner anyway |
| **Fold the honesty fix in (the Phase-0 census)** | AC3 forbids a `code_atlas/` diff and Scope §5 says to stop and record instead. Split to 192 — see **A6** |

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| 1 | A `RESOLVED` `CALLS` edge whose `target_raw` is a schema-qualified qname links against a node from **another adapter** with no core change | **verified** — `resolver.py:131-147`; `nodes_by_qualified_names` filters by neither kind nor language, and `store.py:733` states a cross-language edge is one row of the source language |
| 2 | `dbo.X` does not collide with the member grammar | **verified** — `MEMBER_SEPARATOR` is `::` (`contract.py:184`); the `.` container is invisible to `split_qname` |
| 3 | A registered third adapter needs one `REGISTRY` row plus fixtures, no conformance-module edit | **verified** — `tests/contract/adapter_registry.py:3-5`, `:445-448` |
| 4 | A line-oriented state machine parses T-SQL DDL headers correctly enough for tier 1a | **novel-untested** → resolved by shaping the proving test at the integration layer: the `exec-dynamic`, `bracket-quoted-identifier`, `string-literal-with-keyword` and `comment-forms` fixtures each fail if the state machine is wrong. Not a spike — a conformance case |
| 5 | Peak RSS stays flat as input grows | **novel-untested** (runtime) → resolved by the named proving test below, which measures it |

### Smallest change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | The adapter: entry point, streaming scanner, qname, handshake | `adapters/sql/{index.js,src/*.js,package.json,README.md}` (new) | none identified — new directory, no importer; reaches the core only over stdio | R1, R2, R3, C2 | 0/4 |
| 2 | T-SQL construct inventory named in the rule book **before the first fixture** | `docs/ENGINEERING_RULES.md` R6.2 | R6.2's text is asserted by `tests/test_doc_size_budget.py`; adds ~13 entries | R6 | 0/1 |
| 3 | 13 spec-driven fixtures | `tests/fixtures/sql/**` (new) | `tests/contract/test_guardrail_gates.py` scans fixtures for repo/framework names (R2.2) | R4, AC2, AC7 | 0/3 |
| 4 | Registry row + spawn binding | `tests/contract/adapter_registry.py`, `tests/sql_adapter_cli.py` (new) | **proof collateral:** `test_adapter_conformance.py` and `test_tool_parity.py` are parametrised over `REGISTRY`, so both gain a third parametrisation automatically | R4, AC2 | 0/2 |
| 5 | Memory guard | `tests/test_sql_adapter_memory.py` (new) | generates two large fixtures at run time; must not be committed | AC5, C2 | 0/2 |
| 6 | Byte-identical-when-unconfigured proof | `tests/test_sql_adapter_absent.py` (new) | none identified | AC4 | 0/1 |
| 7 | `edge_health_by_language` carries the SQL slice | assertion inside change 4's suite | none — 183 already built it (`store.py:730`) | AC8 | 0/1 |
| 8 | Static analyser job + gate step | `.github/workflows/ci.yml`, `scripts/gate.sh` | **the two must stay in step** — AGENTS.md makes a check in one and not the other a lie about what was verified | R4, AC6 | 0/2 |
| 9 | §19 ordering entry + §18.4 answer; BACKLOG + TOKEN_LEDGER rows | `docs/PLAN.md`, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` (spend), `tests/test_doc_size_budget.py` (size) | AC1, R7.2 | 0/2 |

### `HANDLES` — every recalled type-2 handle answered

`HANDLES: 5 recalled | 5 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**H1 `emit-do-not-gate-on-resolution`** — `grep -rn "'(dynamic)'\|\"(dynamic)\"" adapters/php/src adapters/typescript/src`

```
adapters/php/src/Visitor.php:254:                    '(dynamic)',
adapters/php/src/Visitor.php:518:'NEW', $this->container(), '(dynamic)', ..., 'DYNAMIC', $node,
adapters/php/src/Visitor.php:606:$this->edge('CALLS', $this->container(), '(dynamic)', ..., 'DYNAMIC');
adapters/php/src/Visitor.php:867:$literal ?? '(dynamic)',
adapters/typescript/src/parse.js:420:addEdge("CALLS", scope, "(dynamic)", node.getStart(sf), "DYNAMIC", node);
```

**Decision, recorded because the handle and the convention disagree.** 128-C1 says keep the datum;
both shipped adapters discard it. **Tier 1a follows the existing convention** — `'(dynamic)'` at
`DYNAMIC` — because a third adapter deviating unilaterally recreates exactly the two-adapters-two-
conventions split 147 had to repair. Changing the convention is **193's** subject, where it can be
changed in all three at once. AC7 is satisfied either way: never `RESOLVED`.

**H2 `evidence-shaped-honesty-inverts-on-a-second-instance`** — `grep -rn "relation_unmodelled_for_language\|relation_carried_by" code_atlas/ --include=*.py`

```
code_atlas/tools/find_references.py:219  code_atlas/tools/include_graph.py:91,96
code_atlas/tools/coverage.py:29,46       code_atlas/tools/nav_result.py:37,67
```

Two consumers only. A third language that emits `CALLS` passes `language_emits_none_of` and the arm
stays silent — the finding Phase 1 recorded. **Folded into 192, not this change list** (A6).

**H3 `an-aggregate-outlives-the-world-that-named-it`** — `grep -rn "edge_health()" code_atlas/ --include=*.py`

```
code_atlas/tools/get_index_status.py:245:  "edge_health": store.edge_health(),
code_atlas/tools/find_orphans.py:114:      health = store.edge_health() if detail_level == "standard" else None
code_atlas/tools/generate_onboarding.py:99: confidence = store.edge_health()["by_tier"]
code_atlas/tools/reachable_from.py:55:     health = store.edge_health() if detail_level == "standard" else None
```

**Three consumers still read the whole-graph blend**; 183 wired the per-language split into
`get_index_status` alone. This is **pre-existing** — already a two-language blend — and a third
language widens it. Fixing it is a `code_atlas/` diff, so **AC3 bars it from this ticket**: recorded
as follow-up **195**, not absorbed.

**H4 `link-on-the-graph-not-on-the-string`** — `sed -n '108,147p' code_atlas/resolver.py`

```
if kind in contract.PATH_EDGE_KINDS:   paths.append(edge)
elif kind in contract.FQN_EDGE_KINDS:  symbols.append(edge)
...
qname_hits = store.nodes_by_qualified_names(lookup_raws, limit=max_candidates)
```

The resolver branches on the **declared kind set**, never on the shape of a string. `CALLS` is in
`FQN_EDGE_KINDS` (`contract.py:65`), so the SQL edge links on the graph. Change 1 complies by
emitting a bare edge and letting the resolver link (R3.3) — the adapter resolves nothing itself.

**H5 `derived-not-listed-invariant`** — `grep -rn "\"php\"\|'php'" code_atlas/ tests/contract/ --include=*.py`

```
tests/contract/test_guardrail_gates.py:21: VENDOR = ADAPTERS / "php" / "vendor"
tests/contract/test_guardrail_gates.py:89: planted.write_text('if language == "php":\n    pass\n', ...)
```

Two hits, both legitimate: a vendor path constant and the guardrail test's own planted negative
control. **No adapter list is re-declared anywhere in the core.** Change 4 complies — the valid set
stays `set(adapter.cases)` and `REGISTRY` keys, never re-listed (147, R6.7).

### Rule compliance

R1.1 ✅ launched by the generic `CA_<LANG>_CMD` convention (`config.py:25`), no language named in the
core · R1.4 ✅ enforced by process boundary, see Approach · R2/R2.2 ✅ change 2 names the inventory
from the T-SQL spec *before* change 3 writes a fixture, which is lesson 149's whole point · R3 ✅ zero
vocabulary spend · R3.3 ✅ bare edges only · R4/R4.1 ✅ static files, no DB connection · R6.2 ✅ closed
by change 2 · R6.3+R6.6 ✅ change 8, landing with the adapter not after (150) · R6.5 ✅ every fixture
shown red first · R6.7 ✅ H5 · R7.2/R7.6 ✅ change 9.

### Verification plan

| AC | Risk layer | Proof artifact | Fixture provenance | Layer-match |
|---|---|---|---|---|
| AC1 | logic | unit — `test_backlog_bookkeeping.py` | n/a | ✅ |
| AC2 | integration | integration — conformance suite spawns the adapter CLI | authored | ✅ |
| AC3 | logic | unit — grep gate + empty core diff recorded as 019's was (156) | n/a | ✅ |
| AC4 | integration | integration — 061's method, no `CA_SQL_CMD` set | n/a | ✅ |
| AC5 | runtime | runtime — subprocess peak RSS at two input sizes | authored (generated) | ✅ |
| AC6 | e2e | cross-repo reporter over varied real repos | **real-corpus — unavailable** | ❌ → excluded |
| AC7 | integration | integration — `exec-dynamic` conformance case | authored | ✅ |
| AC8 | integration | integration — assert the SQL slice in `edge_health_by_language` | authored | ✅ |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Coverage-gap exclusion — AC6's cross-repo half.** `config.real_corpus_path` is `null` and
`scripts/cross_repo_samples.json` pins PHP/TS repos only, so *"several varied repos index with sane
counts"* cannot be run for T-SQL. Stated plainly rather than passed off as authored: **AC6's static
analyser half ships and is proven; its cross-repo half does not.**
`risk tier: medium · follow-up: add a T-SQL entry to scripts/cross_repo_samples.json ·`
`expiry: when a T-SQL sample is added to scripts/cross_repo_samples.json or config.real_corpus_path is configured · seen: (first occurrence of this class)`

### Proving test

**`tests/test_sql_adapter_memory.py::test_peak_rss_is_constant_in_input_size`**

```
pytest tests/test_sql_adapter_memory.py::test_peak_rss_is_constant_in_input_size
```

It generates a ~20 MB and a ~200 MB `.sql` file, runs the adapter on each as a subprocess, and
asserts `peak_rss_children_kb` grows by < 1.25× with a 512 MB absolute backstop. **Red run (R6.5) is
constructed, not asserted:** swap the streaming scanner for a `readFileSync` variant and this exact
assertion fails on the ratio while every other test stays green. It sits at the runtime layer because
that is the only layer where C2 can fail — a unit test over the scanner would pass with the file
fully in memory.

Second, for AC2: **`tests/contract/test_adapter_conformance.py`** parametrised over the new `sql`
registry row; red run by making the adapter emit `HEURISTIC` for a static `EXEC` and watching
`exact_edge_shapes` fail on the tier.

### Rollback + porting

Rollback is `git revert` of one commit: changes 1–7 are new files, change 8 is two additive job
blocks, change 9 is documentation. Nothing existing changes behaviour, and a repo without
`CA_SQL_CMD` is unaffected by construction (AC4). `config.repos` holds one entry (`app`), so there is
no porting order.

### SCOPE

`SCOPE: L` — unchanged from analysis. Nine change-list items, but eight are additive and one is
documentation; the *outgrew-its-ticket* nudge does not fire because the census that would have grown
it was split out (A6) rather than absorbed.

### Gate-2 addendum — the field retros were read, and they moved three things

Source: `today-i-learned/ai/code-atlas/Retros/` rounds 8–12, read in full at Gate 2.

**1. Roll-out sits outside this repo — noted once, then set aside.** Round 12's own item 1 is a PR
in the anchor repo (`.mcp.json` + a CI job). **176 *Explicitly not in scope* already ruled that out as
code-atlas work** — *"those belong to the consuming repo, deliberately not filed here"* — so it is
not a ticket, not a dependency, and does not reorder anything here. Recorded and dropped.

**2. This ticket's own counter-case is factually wrong.** The ticket argues *"Adapter #2 shipped
eight tickets of correct capability for a language the consumer never asked a question of."* The
retros say otherwise — round 10 §0.g records **three** PHP↔JS questions, **two on the critical
path**; round 11 §0.g records **two more, both critical path**. Demand was there and was measured.
That weakens the demand-first objection to T-SQL, which is the argument AC1's §19 entry has to make
honestly. **Fix the sentence in the ticket body when AC1 is written.**

**3. `A7` is REJECTED — and the retros name a better fix that this ticket's own AC3 still bars.**
Round 12 §15 **defers tier 3** (the PHP↔SQL crossing) in terms: *"it is string parsing, it will be
noisy, and the honest lesson of adapter #2 is do not ship a tier nobody has asked for."* With tier 3
deferred there is **no unlinked edge naming a proc**, so A7's per-subject evidence is **structurally
inert** — the same shape as `186-C1`, one level up again. The measured failure is instead:

> **8-A (round 8 §4):** `search_symbol("DialogueService")` returned **1** hit. Ground truth: **281
> `.js` files** reference it. *"`total_count: 1` on a symbol with 281 real sites is a false negative
> wearing a modelled zero's clothes"* — and *"nothing in any `no_matches` or low-`total_count` answer
> names the index's language coverage, while `get_index_status` holds `indexed_suffixes` one call
> away."*

Round 12 §14 row 6-C: **"STILL INVERTED, now on JS… r9 showed completeness harming via `legacy/`;
r12 shows the same shape with a new language added to it."** **Adding a language has already made an
answer worse twice, measured.** A third is not a prediction.

**The verified mechanism** — `code_atlas/tools/coverage.py:119-120`:

```python
    if payload.get("results"):
        return payload
```

The coverage note **self-suppresses on any answer that carries results**. That is exactly the SQL
case: 62 DB-side callers found, the cross-language ones missing, note withheld. So the honest fix is
neither a pair census nor per-subject unlinked evidence — it is **letting the coverage disclosure
reach a partial answer, not only an empty one**. Language-agnostic, needs no new edges, no new
vocabulary, and closes a finding carried since round 8.

**4. `A1`'s premise is now corroborated outside the ticket.** Round 12 §15 verbatim: *"**TKT-1020,
TKT-1027, TKT-962 and TKT-1026 are one defect class** — a column whose value comes from a DEFAULT
because every writer omits it — and it is mechanically detectable from tier 2."* A1 was resting on
184's own text; it now has a retro behind it.

**5. Two things the retros do NOT corroborate — recorded so they are not mistaken for evidence.**
(a) The **multi-MB PHP-adapter crash** (`adapter 'php' exited (code None) with the stream open`,
~30 restart cycles) appears in **no** retro, rounds 8–12. C2's premise is the ticket's own field
note, uncorroborated. The streaming design is right regardless — but AC5 should not be described as
retro-backed. (b) The **shape** of the 82 `EXEC <proc>` string literals — plain literal versus
concatenated/interpolated — is documented **nowhere**. Any crossing ticket is unevidenced on the one
fact that decides whether it is feasible.

**6. Round 12 treats tiers 1 and 2 as ONE recommendation** (*"T-SQL adapter, tiers 1–2"*), and puts
`CREATE TRIGGER` / `CREATE VIEW` inside tier 1. This ticket's 1a/1b split is a contract-cost
refinement made here, not in the retro — legitimate, but it means **022 should follow 184 closely
rather than sitting behind a long gate**, and it independently supports **A4** (triggers are writers).

### What the retros change about 184 and 022 — nothing outside them

| Ticket | Change from the retro read |
|---|---|
| **184** | Scope confirmed by §15 tier 1 verbatim; G2 confirmed by §17's `sed` incident. **Ships first.** Carries a recorded follow-up (192) for the coverage-note gap it creates, which does **not** gate it — the adapter is opt-in (AC4), so nothing regresses for a repo that never sets `CA_SQL_CMD` |
| **022** | Tier 2 content confirmed by §15 verbatim; **A1 corroborated** by §15's defect-class sentence; A4 supported (§15 puts `TRIGGER` in tier 1, so triggers are in scope somewhere and tier 2 is where they bite). Round 12 recommends tiers 1–2 together, so 022 follows 184 closely |
| **192** (follow-up, not a prerequisite) | `coverage.py:119` self-suppresses the disclosure on any answer carrying results. Replaces the rejected A7 |
| **194** (follow-up) | §15's one-call query |
| ~~193~~ | **Dropped** — §15 defers tier 3, and the call-site shape is undocumented anywhere |

`ASSUMED verdicts: A3 ratified (unchanged) · A6 ratified and strengthened · A7 REJECTED, replaced by the coverage-note fix · A1 corroborated · A4 supported · A5 moot (193 deferred)`

## Phase 3 — execute (deviations recorded, not smoothed over)

Three defects this ticket introduced were caught by guards **written for earlier tickets**, and one
blast-radius miss was caught by the gate rather than by the design:

| # | What | Caught by | Deviation from the approved change list? |
|---|---|---|---|
| 1 | An `EXEC` inside a string literal became a `CALLS` edge — `stripToCode` kept literal bodies | the `string-literal-keyword` fixture, written for exactly this | no — the fixture is change-list item 3 |
| 2 | The memory test spawned its own `--file` subprocess | **147 AC4** — the "fourth copy" guard | no — routed through the shared `AdapterCli` |
| 3 | `find_references` declared `answers_without`, actually answers `relation_unmodelled_for_language` | the tool-parity matrix | no — the declaration was corrected to the measured state |
| 4 | `test_batched_subject_sweep.py` pins a payload carrying `unconfigured_adapters`, so a third adapter reddened a test unrelated to SQL | `scripts/gate.sh` | **YES — a change-list miss.** The Gate-2 trace followed `REGISTRY` and never looked for readers of `coverage_gap`. Exactly what the blast-radius step exists to catch |

**AC5's wording was wrong, and the proving test is what found it** — the finding is written up in the
ledger row and in `tests/test_sql_adapter_memory.py`'s module docstring. `code_atlas/` diff: **empty**,
as 019's was (156).

## Phase 5 — finalise

`CLAIMS: 6 claim(s) from 1 lesson entr(ies) | T1=0 T2=5 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 4 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 6 candidate(s) checked | 6 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 4 type-2 claim(s) with seen ≥ 2 | 3 routed to a destination | 0 cannot promote (reason) | 1 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: execute (main-loop)`

**The promotion candidate is `two-syntaxes-two-paths`**, now at recurrence 2 (019, 184). It is
**proposed, not written**: `/mango:promote` and a human ratify own that, and this phase never authors
a rule. Its shape if ratified: *where a construct has two syntaxes that reach the walk by different
branches, both are conformance cases — a fixture covering one proves nothing about the other.*

Three sightings routed to rules already binding — `prove-the-guard-fails` → R6.5 (rec 26),
`count-pin-in-blast-radius` → AGENT_BRIEF P5 (rec 6), `derived-not-listed-invariant` → R6.7 (rec 21).
`LEDGER TOTAL` is `unmeasured` rather than a figure: this host surfaces no usage block, and a
plausible number would be a false green.

**One type-3 skill-gap signal recorded** in `docs/SKILL_GAP_CANDIDATES.md`: `check_lines.py`'s
`PLACEHOLDER_RE` matched `<LANG>` inside `CA_<LANG>_CMD` — a real convention this project documents —
and rejected a correct `RULE SECTIONS:` line as a copied template. The only workaround was to reword
the doc to suit the checker. This repo never edits a mango skill; the signal is for its maintainer.

### DISCLOSURE — the one artifact nothing can check

1a. **REVIEWER: OFF** — waived by the run arg. No rule-book-grounded review of the diff ran; a clean
    result carries no reviewer finding because none was sought.
1b. **CHALLENGER: OFF** — waived. Nothing independent re-derived the requirements from the raw ticket.
    **Both seats off: nothing but the author looked at this diff.** The maintainer reviews on the PR.
2. **AC6's cross-repo half is not proven.** `real_corpus_path` is `null`; `cross_repo_samples.json`
   pins PHP/TS repos only. Coverage-gap exclusion recorded with a checkable expiry.
3. **C2's premise is uncorroborated.** The multi-MB PHP-adapter crash appears in no retro, rounds
   8–12. The streaming design is right regardless; AC5 is not retro-backed.
4. **The blast-radius miss above (row 4)** — a change-list item discovered by the gate, not the design.
5. **The `REFINE:` line was re-emitted** after `check_lines.py` rejected the first one for `U != a + b`:
   the first pass counted typed-UI questions (2) instead of want-decisions exposed (8). Re-deriving
   also surfaced an **eighth** recalled claim the first pass missed (`two-syntaxes-two-paths`).
6. **The working doc is 147% of `doc_size_budget`** (59 KB of 40 KB). Reported by the checker, not
   blocked — the ceiling is the project's. It is not pruned here because the phase records are the
   evidence a reviewer reads.
7. **`gotchas_path` and `drift_path` do not exist** (`docs/gotchas.md`, `docs/DRIFT.md`), so any
   gotcha or drift this run produced is surfaced here rather than written to a file. None was.
8. **Call ceiling `unknown`** — no ledger history in the `fresh/calls` shape; every row records
   `main-loop unmeasured`. Recorded unknown rather than invented, so no budget ladder step was taken.
9. **`EVIDENCE` reports the delta capture as "another tree", and it is right.** The run at `9c478f3`
   is the last commit before this block; recording it necessarily lands one commit later, so the
   provenance axis can never agree. Same family as the pre-fix red-run signal
   `docs/SKILL_GAP_CANDIDATES.md` already carries (8 of 8 tickets in the 2026-08-28 batch). Recorded
   as unverified-by-the-checker rather than papered over.
10. **`RECONCILE` at close reports `TREE-COMPARISON: BROKEN`, and that is MY error, not a finding.**
    I wrote the check as `git diff --quiet <base> <branch> -- <paths>`, which compares the base to the
    branch and therefore *must* differ the moment any work exists. The floor condition asks whether a
    commit landed on the branch **beyond what the PR carries** — that is branch-head vs PR-head, not
    base vs branch. So this condition was in its failing state at t0 for the right reason (no branch)
    and is in its failing state at close for the wrong one, and **it verified nothing at close**. The
    contract is left as written rather than rewritten after the fact to go green; the other five
    conditions do hold.
11. **Deferred to the morning:** the merge. `autorun` never merges.
