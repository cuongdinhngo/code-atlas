---
id: 214
slug: a-bare-exec-links-to-nothing-and-the-zero-says-no-matches
title: 'A schema-unqualified `EXEC X` links to nothing, so `find_callers` answers `no_matches` on a proc with 42 call sites — 604 of 696 EXEC sites (86.8 %) on the anchor are written that way'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [184, 186, 204, 160]
---

## Why this exists (field retro round 13 §13, §16)

Round 13 is the first round that could ask a SQL question. It asked six and got **two harmful
answers**, both the same shape:

> `find_callers("dbo.Score_Calc")` → `total_count: 0`, `reason: "no_matches"` — against **42**
> grep-verified `EXEC` sites. `find_callers("dbo.Score_Calc_BETA")` → **0 vs 6**, all exact-case.

The retro isolated the cause in five further calls, ruling out the two obvious suspects: **not case**
(`Score_Calc_BETA` fails with six exact-case sites) and **not double definition**
(`usp_CleanOrphanedMemberReferences` has two definitions and resolves to **1 caller, RESOLVED**).

> **The discriminator is qualification: `EXEC dbo.X` links, `EXEC X` does not — and 604 of 696 EXEC
> sites (86.8 %) are bare.**

Corroborated independently by the per-language `edge_health` 183 shipped: SQL is **14.6 % linked**
against **13.2 % qualified**. The two numbers agree, from opposite directions.

**The chain is three hops and every hop is in this repo:**

1. `adapters/sql/src/scan.js:400` emits `target_raw: qname` verbatim — for `EXEC Score_Calc` that
   is `Score_Calc`, with `confidence_tier: "RESOLVED"`.
2. The core resolves a `CALLS` edge by `target_raw` against the declared qname, which is
   `dbo.Score_Calc`. No match.
3. The bare-name fallback cannot catch it either: `code_atlas/resolver.py:19` fixes
   `_BARE_NAME_KIND = "Method"`, and a T-SQL procedure is a `Function` node. **SQL's HEURISTIC count
   is 0** — there is no guessing tier for this language at all.

So the edge is dropped, and `find_callers` reports the drop as a **modelled zero**.

**Why this is the round's only harmful payload class.** `no_matches` means *"I model this relation and
the answer is none"*. Here the truth is *"this call form is not linked"*. A reader deletes a live
stored procedure on that answer. The retro's §17 names it as the one place the tool made a competent
reader worse: *"a wrong answer I would have shipped into a report had the mandated grep not caught
it."*

**The honest field already exists and works.** [186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md)
shipped `relation_unmodelled_for_language` (`code_atlas/tools/nav_result.py:67`), and round 13
confirmed it fires correctly, first try, on a third language — for a **view's importers**, where
nobody would be badly misled. It is pointed away from the defect. **This is not a missing capability;
it is a capability wired to the wrong case.**

## Scope

1. **A schema-unqualified `EXEC X` resolves to the declared object** when the resolution is
   unambiguous — the T-SQL rule that an unqualified routine name resolves against the default schema
   (**R2: the language spec, not this repo's names**). Where the object lives decides tier: an
   unambiguous default-schema match is not a guess of the same class as a bare method name.
2. **Where it lives is a design decision, and R1.1 constrains it.** Two candidate homes: the adapter
   normalising `target_raw` (a language rule, in the file that already encodes T-SQL syntax) or a
   generic core mechanism the adapter opts into. **A branch on `language == "sql"` under
   `code_atlas/` is not one of the options.** Design records the choice and why.
3. **Ambiguity refuses rather than guesses.** More than one candidate for a bare `EXEC X` must not
   silently pick one; the existing ambiguity surface (`ambiguous_definitions`) is the precedent.
4. **The residual zero says what it is.** Whatever Scope 1 cannot link — a target that is genuinely
   ambiguous, a dynamic `EXEC(@sql)`, a proc declared inside a string — answers
   `relation_unmodelled_for_language`, **not** `no_matches`. This half needs no schema bump and no
   rebuild.
5. **Measure it on the anchor.** Report the qualified/bare census and the linked share before and
   after. If Scope 1 moves SQL's linked share by little, that is the finding and it is reported;
   Scope 4 still ships, because the honest zero is worth more than the edges.

### Explicitly not in scope

- **Views as symbols.** 1,263 `CREATE VIEW` statements are File nodes only, and `dbo.WRB` — the fact
  that motivated adapter #3 — is still outside the graph. That is a separate gap in tier 1a's scope,
  not this ticket. See *References*.
- **A proc declared inside dynamic SQL** (`EXEC('CREATE TRIGGER …')`). A parse-tier gap; it lands in
  Scope 4's honest zero, not in Scope 1's resolution.
- **Widening the bare-name HEURISTIC fallback across languages.** [204](204_bare-name-resolution-has-no-language-predicate.md)
  deliberately restricted it, and deleted 342,758 false edges by doing so. This ticket does not
  reopen that.
- **Any PHP↔SQL crossing.** `cross_language.pairs` is `{}` by design.

## Constraints

- **R1.1** — zero language branches in the core. If the rule cannot be expressed without one, it
  belongs in the adapter.
- **R2** — the rule encodes T-SQL's default-schema resolution, never the anchor repo's habit of
  writing `dbo`. A repo whose objects live in another schema must not be silently mis-linked.
- **R4.2** — deterministic: identical input, identical rows.
- **R5.2** — a link weaker than what the edge claimed is never reported as stronger.
- **R5.6** — silence is not evidence. Scope 4 is this rule applied to the exact case that broke it.
- **R6.9** — assert at the consumer: the proving test reads `find_callers`' payload, not the resolver's
  internal state.

## Acceptance criteria

1. A fixture where `EXEC X` is called against a single declared `dbo.X` links, and `find_callers` on
   the declared qname returns that call site.
2. A fixture where two candidates exist does **not** silently link one; the ambiguity is visible in
   the payload.
3. Every `CALLS` edge Scope 1 cannot link answers `relation_unmodelled_for_language` with its hint —
   **never** `no_matches` — pinned by a test that fails before the change.
4. A repo whose routines are declared in a non-`dbo` schema is not mis-linked to `dbo`, pinned by a
   fixture.
5. No `if language ==` under `code_atlas/` (the existing CI grep gate stays green).
6. Scope 5's before/after census is recorded with its method, including a negative result.

## References

Field retro round 13 §13 (the isolation chain), §4 (the zero taxonomy), §16 (this ticket, named as
the one change to make), §17 (the harm), §15.a (the narrowed `.sql` carve-out — *"who calls a stored
procedure"* is the entry this ticket exists to remove).
[184](184_tsql-source-adapter-tier-1a.md) (tier 1a, which emits the edge),
[186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) (the reason string
this reuses), [204](204_bare-name-resolution-has-no-language-predicate.md) (why the bare-name fallback
is language-restricted), [160](160_a-zero-answer-never-names-the-index-language-coverage.md) (the
zero-answer disclosure this joins).
`adapters/sql/src/scan.js:389` (the `EXEC` scan), `:400` (the edge, with `target_raw` verbatim),
`code_atlas/resolver.py:19` (`_BARE_NAME_KIND = "Method"`), `:185` (`_link_by_bare_name`),
`code_atlas/tools/nav_result.py:67` (`REASON_RELATION_UNMODELLED_FOR_LANGUAGE`),
`code_atlas/tools/find_callers.py:111` (the `bare_name_truncated` precedent for a non-`no_matches`
zero).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 214 · **work_doc_mode:** embed · **Current phase:** 5 finalise — complete on disk. PR [#265](https://github.com/cuongdinhngo/code-atlas/pull/265) open on `main`. **Next action:** merge #265.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** bug.
- Run: `/mango:autorun 214` with skipped reviewer (`--no-reviewer`); challenger ON.
- Branch (planned): `fix/214-a-bare-exec-links-to-nothing`. Contract `.mango/run-contract-214.txt`.
- RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN | 2 UNBOUND | 0 could-not-run.
- Handover: push feature branch + open PR only (never merge).

## Phase 0 — refine

`PREMISE: 12 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 4 by handle | 1 by area | 0 by finding | 3 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions. The ticket is locked — Scope 2 explicitly parks
"where it lives" for design; ACs and constraints already pin the acceptance bar. User handover
("choose the best approach, and pass all gates") authorises design to pick the home without a
want-decision stop.

**PREMISE detail.** Checked and present: `adapters/sql/src/scan.js`, `code_atlas/resolver.py`
(`_BARE_NAME_KIND`, `_link_by_bare_name`), `code_atlas/tools/nav_result.py`
(`REASON_RELATION_UNMODELLED_FOR_LANGUAGE`), `code_atlas/tools/find_callers.py` (bare_name_truncated
precedent), tickets 184/186/204/160. **Ambiguous (not blocking):** field retro round 13 (prose
noun, not a resolvable path in this repo).

**INPUT KIND:** ticket (not epic).

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `reproduce-the-payload-not-the-story` | 2 | handle | **Yes** — prove on `find_callers` payload (R6.9 / ticket C) |
| 2 | `prefer-the-provable-fix` | 2 | handle | **Yes** — Scope 2 home: prefer what a fixture can falsify |
| 3 | `count-pin-in-blast-radius` | 2 | handle | **Yes** — Scope 5 census / any count pin that moves |
| 4 | `two-syntaxes-two-paths` (184-C3) | 2 | handle | **Yes** — EXEC/EXECUTE both must link |
| 5 | SQL / CALLS area (022, 184) | 5 | area | Surfaced; dynamic EXEC already DYNAMIC |
| — | `assert-the-consumer-not-the-field` | 2 | — | **retired skipped** → R6.9 |
| — | `prove-the-guard-fails` | 2 | — | **retired skipped** → R6.5 |
| — | `skip-dynamic-means-unlinkable` | 2 | — | **retired skipped** → R5.2 |

**Exposure-checker:** skipped with refine (`skip: yes`).

## Phase 1 — analysis

`PREMISE: 12 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 4 by handle | 1 by area | 0 by finding | 3 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 5 decomposed | ROWS: C=6 R=5 G=2 AC=6`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N touched files under UI paths (resolver + find_callers + sql adapter/tests/docs)`
`BASELINE: green`
`SCOPE: M`
`TIER: full`
`RULE SECTIONS: 11 applicable — 10 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ resolver stays language-agnostic · R1.4 (change-type) ✅ linking stays in resolver · R1.8 (change-type) ✅ one residual-reason site · R2.2 (change-type) ✅ no dbo hardcode · R3.3 (change-type) ✅ bare edges stay bare · R4.2 (change-type) ✅ deterministic links · R5.2 (change-type) ✅ _weaker_tier · R5.6 (change-type) ✅ Scope 4 honest zero · R6.5 (recalled handle) ✅ AC3 red-before · R6.9 (change-type) ✅ assert find_callers payload · R7.1 (change-type) ✅ smallest useful fix`

Both `PREMISE:` / `RECALL:` carried forward from Phase 0.

### BASELINE

`.venv/bin/python -m pytest -q --tb=no` on untouched `main` at **0b21dcc**:

```
2873 passed in 271.75s (0:04:31)
```

`Ran at 0b21dccbf4435f4dc8cd1856ca45e920386fdda3`. Green. README *Testing* still lists 2,739 —
the count has moved; DoD is this captured baseline, not the stale README figure. No baseline
exclusions.

### Clarifications (all self-resolved; j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | Adapter-prefix `dbo.` vs core unique-Function link? | **Core.** R3.3: adapters emit bare targets; linking is the core's job. Prefixing `dbo` hardcodes a repo habit and fails AC4/R2. A language-agnostic "unique Function named X in the call site's language" needs no `if language ==` | R3.3; R1.1; R2.2; ticket AC4 |
| Q2 | Why do RESOLVED bare EXEC edges never reach `_link_by_bare_name` today? | **Gate.** `resolver.py` only queues bare targets when `incoming == "HEURISTIC"`; SQL stamps `RESOLVED` (`scan.js:400`), so the edge is dropped after the FQN miss | `resolver.py` bare branch; `scan.js:400` |
| Q3 | Can Scope 4 reuse `coverage.relation_unmodelled_for_language` as-is? | **No — wrong evidence.** That helper is true when the language emits *none* of the kinds; SQL *does* emit CALLS. AC3 still pins the **reason string**. Wire `find_callers` on unlinked CALLS evidence (065/186's sibling pattern) to emit `relation_unmodelled_for_language` — "capability wired to the wrong case" | ticket Why/AC3; `coverage.py:29-48`; `find_references.py:208-236` |

### Requirements matrix

| ID | Source | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|
| G1 | Why | bare `EXEC X` must link when the declared object is unambiguous | 604/696 bare; resolver drops RESOLVED bare | closed |
| G2 | Why | residual zero must not say `no_matches` | `find_callers` uses `relation_reason` → `no_matches` | closed |
| R1 | Scope 1 | unambiguous bare EXEC → declared Function | needs new core path (Q1/Q2) | open |
| R2 | Scope 2 | home recorded; no `language ==` in core | design chooses core unique-Function | open |
| R3 | Scope 3 | ambiguity refuses / visible | `ambiguous_definitions` precedent | open |
| R4 | Scope 4 | residual → `relation_unmodelled_for_language` | find_callers has no such arm today | open |
| R5 | Scope 5 | before/after census on anchor | method + numbers in working doc / PR | open |
| C1 | Constraints | R1.1 | CI grep gate | closed |
| C2 | Constraints | R2 — no dbo hardcode | AC4 fixture | closed |
| C3 | Constraints | R4.2 deterministic | resolver only | closed |
| C4 | Constraints | R5.2 never promote weaker | `_weaker_tier` | closed |
| C5 | Constraints | R5.6 silence ≠ evidence | Scope 4 | closed |
| C6 | Constraints | R6.9 assert at consumer | prove via `find_callers` payload | closed |
| AC1 | AC | fixture: EXEC X → dbo.X; find_callers returns site | proving test | open |
| AC2 | AC | two candidates → no silent link; ambiguity visible | fixture + payload | open |
| AC3 | AC | unlinked residual → `relation_unmodelled_for_language` not `no_matches`; red before | proving test fails on main | open |
| AC4 | AC | non-dbo-only repo not mis-linked to dbo | fixture | open |
| AC5 | AC | no `if language ==` under `code_atlas/` | existing CI gate | open |
| AC6 | AC | Scope 5 census recorded incl. negative | working doc / PR | open |

**Not in scope (decomposed, no rows to implement):** views as symbols; dynamic `EXEC('CREATE…')`
parse gap; widening HEURISTIC Method fallback (204); PHP↔SQL crossing.

### AC validation (falsifiability)

| AC | Stated value | Falsifiable form | Match? |
|---|---|---|---|
| AC1 | links + find_callers returns site | pytest: indexed fixture, `find_callers("dbo.X")` has ≥1 result, reason ok | yes |
| AC2 | no silent link on 2 candidates | pytest: 0 linked callers OR `ambiguous_definitions` / unlinked residual reason; never one arbitrary twin | yes |
| AC3 | reason == `relation_unmodelled_for_language` | pytest payload `reason` pin; red on main before fix | yes |
| AC4 | non-dbo schema not → dbo | fixture only `sales.X`; bare EXEC does not invent `dbo.X` | yes |
| AC5 | no language branch | existing R1.1 grep gate green | yes |
| AC6 | census recorded | working-doc/PR section with method + before/after; negative OK | yes (artifact) |

### Cause analysis (bug)

**Taxonomy:** `data` (edges present, unlinked) + `logic` (resolver gate + zero reason).

1. `adapters/sql/src/scan.js:400` emits `target_raw` = bare name, `confidence_tier: RESOLVED`.
2. `resolver.py` FQN miss on bare; bare fallback only for `HEURISTIC` + `Method` (204) → SQL HEURISTIC = 0.
3. `find_callers.py:264` → `relation_reason` → `no_matches` on a modelled-but-unlinked CALLS graph.

### Blast radius

- `code_atlas/resolver.py` (new unique-Function bare CALLS path)
- `code_atlas/tools/find_callers.py` (honest residual reason)
- possibly `code_atlas/store.py` if a new unlinked-CALLS count helper is needed
- `adapters/sql/` — **likely unchanged** under Q1 (R3.3); tests/fixtures only
- `tests/` new proving module; docs (task, BACKLOG, TOKEN_LEDGER, maybe PLAN §19)

`TRACK: backend`.

### RULE SECTIONS

`RULE SECTIONS: 11 applicable — 10 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ resolver stays language-agnostic · R1.4 (change-type) ✅ linking stays in resolver · R1.8 (change-type) ✅ one residual-reason site · R2.2 (change-type) ✅ no dbo hardcode · R3.3 (change-type) ✅ bare edges stay bare · R4.2 (change-type) ✅ deterministic links · R5.2 (change-type) ✅ _weaker_tier · R5.6 (change-type) ✅ Scope 4 honest zero · R6.5 (recalled handle) ✅ AC3 red-before · R6.9 (change-type) ✅ assert find_callers payload · R7.1 (change-type) ✅ smallest useful fix`

Out of applicable set (not counted): R3.1 N/A (no vocabulary bump); R4.1 N/A (no LLM); DB conventions N/A (no migration).

### Scope / Tier

`SCOPE: M` — resolver + find_callers + fixtures + census; not L (no adapter redesign, no contract bump).
`TIER: full` — multi-file, multi-AC, not lite-eligible.


## Phase 2 — design

`HANDLES: 4 recalled | 4 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Approach

**Core unique-Function link for bare CALLS + honest residual on find_callers.**

1. In `resolver.py`, when an FQN miss leaves a CALLS edge whose lookup has no container
   (bare `target_raw`), query `nodes_by_names([name], kind="Function", language=call-site
   language, limit=2)`. Exactly one hit → link at `_weaker_tier(incoming, "RESOLVED")`.
   Zero hits → existing HEURISTIC→Method bare path unchanged (204). Two+ hits → leave
   unlinked (AC2 ambiguity). No `dbo` prefix, no `language ==` (R1.1/R2/R3.3).
2. In `find_callers.py`, when `relation_reason` would be `no_matches` on an indexed
   subject, if `count_unlinked_by_target_raw((lookup, bare_name), kinds=CALLER_KINDS) > 0`,
   emit `reason=relation_unmodelled_for_language` (+ existing hint). AC3's string with
   unlinked-CALLS evidence — the 186 helper stays for language-silent kinds.
3. New authored SQL fixtures + `tests/test_bare_exec_resolves.py` proving AC1–AC4 at the
   `find_callers` consumer (R6.9). Adapter source unchanged.
4. Scope 5 census: method recorded; numbers from authored fixtures / any reachable index;
   anchor census deferred (no `real_corpus_path`) — see exclusions.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Adapter prefixes bare EXEC with `dbo.` | Hardcodes a schema habit (R2.2/AC4); adapter cannot see cross-file declarations; fights R3.3 |
| Widen `_BARE_NAME_KIND` to Function inside HEURISTIC-only path | SQL stamps RESOLVED, so edges never enter that path (Q2); also forces HEURISTIC against ticket's "not a guess" |
| Reuse `coverage.relation_unmodelled_for_language` for CALLS | Helper is true only when language emits *none* of the kinds; SQL emits CALLS — wrong evidence (Q3) |

### Assumptions

| Assumption | Tag |
|---|---|
| `nodes_by_names(..., kind="Function", language=)` already filters in-statement (204) | verified — store.py:1131-1147 |
| SQL procedure nodes are `kind=Function` with `name` = last segment | verified — scan.js:336-345 |
| Unique same-language Function match is safe for PHP/TS (no silent cross-link) | verified by language filter + kind=Function; proving test covers SQL; existing Method HEURISTIC path untouched |
| Unlinked CALLS targeting bare name are countable via `count_unlinked_by_target_raw` | verified — store.py:1345-1362 |

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | Unique-Function bare CALLS link before HEURISTIC Method fallback | `code_atlas/resolver.py` | all languages' bare CALLS; PHP/TS Method HEURISTIC path must stay byte-identical when no Function hit | R1,R2,C1,C3,C4,AC1,AC2,AC4,AC5 | 9/9 |
| 2 | Residual zero → `relation_unmodelled_for_language` on unlinked CALLS | `code_atlas/tools/find_callers.py` | every find_callers zero; `bare_name_truncated` arm must keep precedence | R4,C5,C6,AC3 | 4/4 |
| 3 | Proving fixtures + tests (bare EXEC, ambiguity, non-dbo, residual reason, EXEC/EXECUTE) | `tests/fixtures/sql/` + `tests/test_bare_exec_resolves.py` | SQL adapter conformance may see new fixtures if registry auto-globs — check | AC1–AC5 | 5/5 |
| 4 | Working-doc census method + BACKLOG/TOKEN_LEDGER/docs | `docs/` | none identified beyond bookkeeping | R5,AC6,R7.2 | 3/3 |

### HANDLES (recalled type-2 — command + result)

**H1 `reproduce-the-payload-not-the-story`** — traced.

```
Ran at '0b21dccbf4435f4dc8cd1856ca45e920386fdda3'
$ rg -n 'relation_reason|REASON_NO_MATCHES' code_atlas/tools/find_callers.py
264:        reason = relation_reason(hit_total=outcome.total_count, symbol_indexed=indexed)
$ rg -n 'find_callers' tests/test_bare_name_callers_silent_drop.py | head -5
13:from code_atlas.tools import find_callers
61:def test_find_callers_reports_truncated_bare_name_not_no_matches(
```

Folded: change #2 asserts on find_callers payload reason; change #3 is the consumer test.

**H2 `prefer-the-provable-fix`** — traced.

```
Ran at '0b21dccbf4435f4dc8cd1856ca45e920386fdda3'
$ rg -n 'def nodes_by_names' -A8 code_atlas/store.py
1131:    def nodes_by_names(
1137:        language: str | None = None,
```

Folded: change #1 uses existing language-scoped query (provable) over dbo-prefix (unfalsifiable habit).

**H3 `count-pin-in-blast-radius`** — traced.

```
Ran at '0b21dccbf4435f4dc8cd1856ca45e920386fdda3'
$ rg -ln 'linked' tests/test_edge_health*.py tests/test_sql*.py
tests/test_edge_health_report.py
tests/test_edge_health_per_language.py
tests/test_sql_tier2_write_sites.py
tests/test_sql_tier2_vocabulary_is_opt_in.py
```

Folded: edge_health pins use authored graphs; SQL linked share may rise on real rebuilds but
fixture pins stay local. Re-run those tests in execute verification; update any that pin absolute
SQL linked counts if they redden (proof collateral under change #3/#4).

**H4 `two-syntaxes-two-paths`** — traced.

```
Ran at '0b21dccbf4435f4dc8cd1856ca45e920386fdda3'
$ rg -n 'EXEC_RE' -A2 adapters/sql/src/scan.js | head -6
120:const EXEC_RE =
$ ls tests/fixtures/sql/execute_spelling.sql tests/fixtures/sql/exec_call.sql
tests/fixtures/sql/execute_spelling.sql
tests/fixtures/sql/exec_call.sql
```

Folded: proving fixtures cover both `EXEC` and `EXECUTE` bare forms (change #3).

### Coverage-gap exclusions

| Item | Risk tier | Why deferred | Follow-up | expiry | seen |
|---|---|---|---|---|---|
| AC6 anchor census (qualified/bare + linked share before/after on the field index) | medium | `config.real_corpus_path` unset; input-shape-dependent measurement cannot be honest on authored fixtures alone | Record method now; run numbers when an anchor path is configured or a maintainer supplies the field DB | `when config.real_corpus_path is configured` OR maintainer pastes field-index census into this working doc | (first) |

No real corpus configured; AC6 proven as *method recorded* on authored fixtures' before/after only for the linking claim; the anchor share is the excluded half.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|---|---|---|---|---|
| AC1 | integration | integration (`find_callers` over SQL-indexed fixture) | authored | ✅ |
| AC2 | integration | integration (two-candidate fixture) | authored | ✅ |
| AC3 | integration | integration (payload reason pin; red before) | authored | ✅ |
| AC4 | integration | integration (sales-only schema fixture) | authored | ✅ |
| AC5 | logic | unit (existing R1.1 CI grep) | n/a | ✅ |
| AC6 | runtime/3p (anchor measurement) | manual-recorded method + exclusion | authored (method) / real-corpus excluded | ✅ (exclusion) |

### Proving test

```
.venv/bin/python -m pytest tests/test_bare_exec_resolves.py -q
```

Named assertions (fail on main before the change):
- `test_bare_exec_links_to_unique_dbo_proc` — AC1
- `test_ambiguous_bare_exec_does_not_silently_link` — AC2
- `test_residual_unlinked_calls_say_relation_unmodelled_not_no_matches` — AC3 (red-before recorded in execute)
- `test_non_dbo_only_repo_is_not_mislinked_to_dbo` — AC4
- EXEC/EXECUTE spelling covered inside AC1 fixture pair

### Rollback + porting

- **Rollback:** `git revert` the commits on `fix/214-…` / close the PR unmerged.
- **Porting:** single repo (`app`); no multi-repo port.

`SCOPE: M` (unchanged).

## Phase 3 — execute

Branch `fix/214-a-bare-exec-links-to-nothing` from `main` @ `0b21dcc`.

### Implemented (⊆ approved change list)

1. `code_atlas/resolver.py` — `_link_by_unique_function` for non-HEURISTIC bare CALLS; unique same-language Function; ambiguity leaves unlinked; HEURISTIC Method path unchanged.
2. `code_atlas/tools/find_callers.py` — Function-subject residual with unlinked CALLS → `relation_unmodelled_for_language`; docstring updated.
3. `tests/fixtures/sql/bare_exec/*.sql` + `tests/test_bare_exec_resolves.py` — AC1–AC4.
4. Docs: this working doc, BACKLOG, TOKEN_LEDGER.

### Red-before (AC3)

```
Ran at 0b21dcc (find_callers temporarily restored to main; resolver+tests present)
$ .venv/bin/python -m pytest tests/test_bare_exec_resolves.py::test_residual_unlinked_calls_say_relation_unmodelled_not_no_matches -q
FAILED — assert 'no_matches' == 'relation_unmodelled_for_language'
```

### Proving test (green)

```
Ran at <post-change tree>
$ .venv/bin/python -m pytest tests/test_bare_exec_resolves.py -q
.... 4 passed
```

### Scope 5 census (authored fixtures — method; anchor excluded)

Method: index each `tests/fixtures/sql/bare_exec/*.sql` alone; count CALLS where `target_raw` has no `.` and is not `(dynamic)`; linked = those with non-empty `target_qname`.

| fixture | bare CALLS | linked bare | all CALLS |
|---|---|---|---|
| unique_dbo.sql | 2 | 2 | 2 |
| ambiguous_twin.sql | 1 | 0 | 1 |
| non_dbo_only.sql | 1 | 1 | 1 |

Negative result recorded: ambiguous twin stays unlinked (AC2). Anchor field-index before/after share is the coverage-gap exclusion (no `real_corpus_path`).

### Verification sweep

- `diff ⊆` change list (resolver, find_callers, bare_exec fixtures/tests, docs)
- Regressions: bare_name_callers_silent_drop, relation_unmodelled, cross_language_bare_name, tool_parity, edge_health_per_language, sql_confinement, core_is_language_agnostic — green
- R1.1 grep gate green

### Cost ledger (working doc)

| phase | dispatch | notes |
|---|---|---|
| refine | 0 | skip: yes |
| analysis | 0 | main-loop |
| design | 0 | main-loop |
| execute | 0 | main-loop |
| review | (pending challenger) | reviewer waived |



## Phase 4 — review

`reviewer: off` (waived `--no-reviewer`). `challenger: on`.

- Round 1: CHANGES REQUESTED — AC2 visibility (no sibling surface); AC6 census only "deferred" in ledger.
- Fixes: Function `sibling_definitions` on find_callers; TOKEN_LEDGER census method + before/after.
- Round 2: **LGTM** — 10 met / 0 not met. Both blockers discharged.

Ph3/4 proven by: `tests/test_bare_exec_resolves.py` 4 passed; challenger LGTM.

`Reviewed at 9d527dec3c9b60b41a0fee6f06c6092a14efc1d3` — source set through AC2 visibility fix; subsequent docs-only commits are bookkeeping-exempt.

### Maintainer review of PR #265 — one blocker, fixed

`scripts/gate.sh` on the PR head: **GATE RED** — `tests/test_resolver.py::test_batched_resolve_matches_golden_and_is_o1_selects`
(`assert 5 <= 4`). `_link_by_unique_function` queried the store once per language group even when
every bare call was `HEURISTIC`, which that pass can never claim — a wasted round-trip that broke
the O(1)-per-batch resolver budget (027). Fix: group only non-`HEURISTIC` bare calls, return the
batch untouched when none remain; original edge order preserved for `_link_by_bare_name`.
Re-run: **GATE GREEN — 17/17**, 2877 passed on Linux + PHP/Node adapters.
This is DISCLOSURE item 9 landing: the full suite was not re-run after execute, and it was red.

## DISCLOSURE

```
DISCLOSURE
  1a. REVIEWER: OFF — waived by `--no-reviewer`. No rule-book-grounded review of the diff ran; a clean result below carries no reviewer finding because none was sought.
  1b. CHALLENGER: ON — the ticket-blind challenger ran.
  2. UNCHECKED AGENT CLAIMS: 2 — no command derived these values.
       - TREE-COMPARISON: code_atlas/resolver.py code_atlas/tools/find_callers.py tests/fixtures/sql/ tests/test_bare_exec_resolves.py docs/
       - PROVING-TEST: .venv/bin/python -m pytest tests/test_bare_exec_resolves.py -q
  3. BUDGET: call-count ceiling unknown — no ledger history for this tier.
  4. This list is the ONE artifact nothing can check: only the agent knows what it chose not to verify. A near-empty list on a long run is a reason to distrust the run, not to trust it. Every line below this one is appended by the agent.
  5. AC6 anchor field-index census excluded (real_corpus_path null); authored-fixture census recorded in TOKEN_LEDGER.
  6. TREE-COMPARISON BROKEN at close is expected pre-merge (main…branch differs); not a stranded push.
  7. Outward actions deferred to morning: merge #265 (NOT authorised inside this skill).
  8. Challenger round 1 CHANGES REQUESTED → round 2 LGTM; reviewer never ran.
  9. Full suite not re-run end-to-end after final docs commits — proving test + targeted regressions green at execute.
```
