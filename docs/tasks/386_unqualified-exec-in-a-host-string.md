---
id: 386
slug: unqualified-exec-in-a-host-string
title: 'A PHP string that runs `EXEC Proc @p` without a schema calls nothing, so a procedure lists no PHP callers'
phase: 2
milestone: Coverage
status: done
depends_on: [335, 371]
---

## Why this exists

278/281/335 taught the PHP adapter to read a string literal that *begins* a SQL statement
(`adapters/php/src/SqlLiteral.php`). For `EXEC` it requires a **schema-qualified** name
(`SqlLiteral.php:74-76`): "a bare EXEC name would bind to a same-language method by name (204), so
EXEC is schema-qualified or nothing".

That guard is right about the risk and wrong about the population. In T-SQL an unqualified
procedure name is the ordinary form: the server resolves it against the caller's default schema,
then `dbo`. Measured on the anchor index (2026-10-10): of 94 `EXEC` literals in its PHP layer,
**88 name the procedure without a schema** (bare `Proc` or bracketed `[Proc]`) and emit nothing. Only 6 are
qualified. The procedures themselves are indexed by the T-SQL adapter, so `find_callers` on one
answers with its SQL callers only, and a capability trace stops at the PHP method that calls it.
Every PHP → procedure → table path in such a repo is cut at the first hop.

## Scope

1. An `EXEC` / `EXECUTE` literal whose name is unqualified (bare or `[bracketed]`) and that still
   meets the existing clause rule (a parameter follows: `@`, `?`, `:name`, a literal) emits a
   `CALLS` edge, tier `HEURISTIC`.
2. The edge must never bind to a same-language symbol (204). Decide at design how. Two known
   constraints: the contract has no procedure kind (a T-SQL procedure is a `Function`, the same kind
   as a PHP function, `code_atlas/contract.py` `NodeKind`), so a target-kind restriction needs a new
   kind and a `contract_version` bump (R3) — filtering by language in the core breaks R1.1. And the
   T-SQL adapter keeps a routine's qname as written (`adapters/sql/src/scan.js` `CREATE_RE`), so
   `CREATE PROCEDURE Insert_Order` is `Insert_Order`, not `dbo.Insert_Order`: an adapter that emits
   `dbo.<name>` alone misses every procedure created without a schema.
3. Unqualified `EXEC` with no clause after the name (prose like `"exec summary"`) still emits
   nothing, as today. That also leaves a parameterless `"EXEC Proc"` unlinked; whether a whole,
   closed literal `"EXEC Proc"` may link (as the qualified form does) is decided at design from the
   split measured in the first assumption.
4. `EXEC @rc = Proc @p` (return-code form) and `EXECUTE AS …` (not a call) keep their current
   handling.
5. The same guard lives in all three host adapters: `adapters/php/src/SqlLiteral.php:74-76`,
   `adapters/typescript/src/sqlLiteral.js:50` and `adapters/python/src/sql_literal.py` (371). All
   three change together, so one host never links what another drops.

## Assumptions to prove at design

- Before design, split the anchor index's 88 unqualified literals into those followed by a clause
  and those not (parameterless calls): the first number is what this ticket can link.
- `dbo` as the default schema is the T-SQL standard fallback, not a sample convention (R2.3). A repo
  whose procedures live in another schema gets `rule_keys_unresolved`-style counting of misses, not
  a wrong edge.
- No language branch enters the core (R1.1).

## Acceptance criteria

- **AC1:** `"EXEC Insert_Order @id"` and `"EXEC [Insert_Order] ?"` in a PHP fixture emit `CALLS` to
  the fixture's procedure, tier `HEURISTIC` — once created as `dbo.Insert_Order` and once as bare
  `Insert_Order`; both link.
- **AC2:** with a PHP method also named `Insert_Order` in the fixture, no edge lands on the method.
- **AC3:** `"exec summary"` (no clause) and `"EXECUTE AS USER = 'x'"` emit nothing.
- **AC4:** `find_callers` on the procedure lists the PHP caller; the count of linked call sites on
  the anchor index before and after is recorded in the task.
- **AC5:** AC1-AC3 pass on a TypeScript and a Python fixture too.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 386 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W2, takes the anchor counts (E1), and merges after #63. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 381 - 382 - 386 with skipped reviewer` —
  `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/386-unqualified-exec-in-a-host-string` off `feat/382-batch-query-from-a-shell` (PR #63 — stacked).
  Contract `.mango/run-contract-386.txt`. RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 2 want-decision asked | 10 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** `adapters/php/src/SqlLiteral.php` (the `follows()` guard), `adapters/typescript/src/sqlLiteral.js`,
`adapters/python/src/sql_literal.py`, `adapters/sql/src/scan.js` `CREATE_RE`, `contract.NodeKind` and
`resolver._link_by_bare_name` resolve.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 44,014 tokens) added H9–H12.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | how the edge avoids a same-language symbol | how | the hosts emit `dbo.<name>`: `split_qname` finds no `::`, so the bare-name fallback (`resolver._link_by_bare_name`, 204) looks for a method literally named `dbo.<name>`; no core line, no kind, no contract bump (R1.1, R3) |
| H2 | a procedure created with no schema | how | the SQL adapter adds an `ALIASES` edge `dbo.P` → `P` at HEURISTIC; `resolver._lookup_raw` already follows ALIASES for every FQN edge; the qname stays `P` |
| H3 | the clause rule | how | unchanged; a closed parameterless bare `"EXEC Proc"` stays unlinked — forced by AC3, since `"exec summary"` is the same shape |
| H4 | `EXEC @rc = Proc @p` | how | the capture is skipped as today (Scope 4) and the bare name then follows the new rule |
| H5 | `EXECUTE AS …` | how | unchanged: no parameter marker follows `AS` |
| H6 | the three hosts | how | one table, `tests/contract/sql_literal_cases.json`, drives all three (371) |
| H7 | the default schema's spelling | how | one `DEFAULT_SCHEMA` constant per adapter, the README naming it T-SQL's default (R2.3) |
| H8 | the tier | how | HEURISTIC on the host edge (as 335) and on the alias: the default schema is a server setting |
| H9 | case | how | out of scope: T-SQL folds case, the resolver's casefold pass covers writes only (215); a BACKLOG follow-up |
| H10 | `sp_executesql` and system procedures | how | an unqualified `EXEC sp_executesql @s` now emits `dbo.sp_executesql`, which never resolves; harmless, recorded with H9 |
| H11 | counting misses | how | a procedure in another schema leaves an unresolved edge; nothing counts it by name — the follow-up line |
| H12 | `CREATE PROCEDURE [P]` | how | `splitName` drops delimiters, so it aliases as the bare form; a test case |
| W1 | adopt `dbo` as the default schema | want | **ASSUMED (awaiting ratification):** yes. **Tripwire:** this reverses `adapters/sql/README.md`'s "inventing `dbo.` would be a guess" — the qname still is not invented; the alias and the host edge are HEURISTIC and say why |
| W2 | link a closed parameterless `"EXEC Proc"`? | want | **ASSUMED (awaiting ratification):** no — AC3's prose case has the same shape, and the anchor split (E1) is not measurable here |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=2 R=5 G=1 AC=5`
`CLARIFICATION: 14 raised | 14 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/12 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

The base is 382's branch; its gate ran at `7e89fa81` (recorded in 382's Phase 3). The 386 adapter tests on the
base: `tests/test_unqualified_exec.py` and the agreement table fail on the prior adapters (red first, below), every
other adapter test green — `1137 passed` over the SQL/host/alias/contract tests in the worktree, one
failure being 382's module pin, since fixed in `2efad93c`. Ran at 7e89fa81.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "Every PHP → procedure → table path … is cut at the first hop" | unqualified EXEC links | ✅ |
| C1 | Scope 2 | "must never bind to a same-language symbol (204)" | H1 | ✅ (residual: a module whose qname is `dbo.<name>`, as the qualified form) |
| C2 | Assumptions | "No language branch enters the core (R1.1)" | no `code_atlas/` change | ✅ |
| R1 | Scope 1 | bare or bracketed, with a clause → CALLS HEURISTIC | H1 | ✅ |
| R2 | Scope 2 | both declaration forms | H2 | ✅ |
| R3 | Scope 3 | no clause → nothing | H3, W2 | ✅ |
| R4 | Scope 4 | rc form, EXECUTE AS | H4, H5 | ✅ |
| R5 | Scope 5 | all three hosts together | H6 | ✅ |
| AC1 | AC | both literals link, both declarations | | ✅ |
| AC2 | AC | no edge on a same-named method | | ✅ |
| AC3 | AC | `exec summary`, `EXECUTE AS` → nothing | | ✅ |
| AC4 | AC | `find_callers` lists the PHP caller; anchor counts recorded | caller ✅; counts → E1 | ✅ / E1 |
| AC5 | AC | AC1–AC3 on TS and Python | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `find_callers` site set per declaration (`dbo.P`, `P`, `[P]`) | |
| AC2 | yes — `find_callers` on the PHP method, TS and Python functions answers no rows | |
| AC3 | yes — no other site in the set; table cases expect null | |
| AC4 | the caller: yes; the anchor counts: **manual-check exclusion E1** | |
| AC5 | yes — the same fixture carries TS and Python | |

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ no code_atlas/ line changes · §R2.3 (change-type) ✅ dbo is T-SQL's default schema, a named constant, not a sample's name · §R3 (change-type) ✅ ALIASES is existing vocabulary; no qname changes, no contract bump · §R6.5 (change-type) ✅ red on the prior adapters · §R7.5 (change-type) ✅ comments ≤ 3 lines`

## Phase 2 — design

### Approach

1. Hosts: `follows()` accepts a clause after a bare EXEC name; `read()` prepends `DEFAULT_SCHEMA`.
2. SQL adapter: a schema-less `CREATE PROCEDURE P` emits `ALIASES dbo.P → P` at HEURISTIC.
3. The shared table gains the bare, bracketed, open, rc, parameterless, prose and EXECUTE AS cases.
4. Adapter READMEs and CHANGELOG.

### Rejected alternatives

- **A `Procedure` node kind** — a contract bump, a release and a full rebuild, and every tool keyed on
  `Function` moves (the ticket's own constraint).
- **Emit the bare name** — the bare-name fallback binds it to a same-named PHP method (204).
- **Rewrite a schema-less procedure's qname to `dbo.P`** — a qname change, so R3's bump.
- **A resolver rule that retries without the schema** — a core change reading a string's shape.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| a dotted target reaches no method by name | verified | AC2 on PHP, TS and Python |
| ALIASES remaps a CALLS lookup | verified | AC1 with the bare declaration |
| `dbo` is the T-SQL default | verified (spec) | SQL Server resolves an unqualified name in the caller's default schema, `dbo` unless changed |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | bare EXEC → `dbo.<name>` | `adapters/php/src/SqlLiteral.php`, `adapters/typescript/src/sqlLiteral.js`, `adapters/python/src/sql_literal.py` | every host string beginning EXEC | R1, R3–R5 | 3/3 |
| 2 | the alias | `adapters/sql/src/scan.js` | every schema-less procedure | R2 | 1/1 |
| 3 | proving tests | `tests/test_unqualified_exec.py`, `tests/contract/sql_literal_cases.json` | — | AC1–AC5 | 2/2 |
| 4 | docs | four adapter READMEs, `CHANGELOG.md` | — | G1 | 5/5 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — four real adapters, a real build | `find_callers` per declaration | authored | ✅ |
| AC2 | integration | `find_callers` on each same-named symbol | authored | ✅ |
| AC3 | integration + adapter | the site set; the shared table | authored | ✅ |
| AC4 | integration (caller); real corpus (counts) | the PHP caller; E1 | authored / anchor | ❌ E1 (recorded exclusion) |
| AC5 | integration | the same build | authored | ✅ |

**E1 — coverage-gap exclusion (manual check).** The anchor index (PHP + SQL + TS, ~22.9k files) is not on this
machine, so neither the clause / no-clause split of its 88 unqualified literals nor AC4's before/after linked count
can be taken. The cross-repo samples hold no host-string EXEC. `expiry:` the maintainer records both counts in this
file from the anchor after merge (`find_callers` totals over the anchor's procedures before and after) — checkable
by any non-author as "the two numbers are in this section".

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_unqualified_exec.py tests/contract/test_sql_literal_agreement.py`.

### Rollback

`git revert`; the alias rows go with the next full build.

## Phase 3 — execute

Commits `9837f6e0` (code, tests), `f6b70828` (docs), `b6588ddc` (challenger fixes). **Red first** (R6.5): with
the four adapter files reverted, `test_every_host_lists_as_a_caller_of_the_procedure` (both declarations) and all
three agreement tests fail — 5 failed; AC2 passes before and after, since nothing linked before.

**Cross-repo (P8).** `scripts/cross_repo_validate.py --skip-clone --public-only` on the base (`7e89fa81`) and on
this branch: 11/11 ok both, every sample's node and edge count identical (adventureworks 327,920 edges both) —
the samples hold no host-string EXEC, and their only schema-less `CREATE PROCEDURE` lines are template
placeholders the adapter does not name. Floors unmoved, nothing to re-floor.

**Verification sweep.** File axis: the diff is the change list; `ruff`, `npm run check` (SQL adapter) clean;
`git diff --stat -- code_atlas` empty. Behaviour axis: Approach 1–4 implemented as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. Reviewed at b6588ddc — files: the three host recognisers,
`adapters/sql/src/scan.js`, `tests/test_unqualified_exec.py`, `tests/contract/sql_literal_cases.json`, four
adapter READMEs, `CHANGELOG.md`; working doc: this file.

- **`challenger` round 1** (ticket-blind, 56,423 tokens): 11 met · 0 not met · 3 can't tell (the anchor split and
  AC4's counts — E1). Finding: a root-level Python `dbo.py` defining `Insert_Order` has the qname `dbo.Insert_Order`
  and receives the edge — the qualified form's exposure since 335/371, now reached by the unqualified calls too;
  the comments overstated the guarantee. Fixed in `b6588ddc`: the comments say what the dotted target rules out
  and what it does not; the residual is a BACKLOG follow-up. Also covered: `CREATE PROCEDURE [Insert_Order]`.

Verdict: clean (challenger only — REVIEWER: OFF). Matrix `Ph3/4 proven by`: R1–R5, AC1–AC3, AC5 →
`tests/test_unqualified_exec.py` + the agreement table; AC4 → the PHP caller, counts E1; C1–C2 → the diff.

## Phase 5 — finalise

**Durable lesson.** A tool hook that compacts `git diff` output (RTK) makes a saved patch unusable: one
`git diff > patch; git checkout -- …` lost this ticket's adapter edits, re-applied from the edit script.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=1 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/386-unqualified-exec-in-a-host-string`; open the PR against 382's branch (stacked on #63).
Deferred to the maintainer: ratify W1–W2; E1's anchor counts; merge after #63.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 44,014 |
| 4 review | `challenger` (ticket-blind) | 1 | 56,423 |

`LEDGER TOTAL: 100,437 · top cost driver: challenger`
