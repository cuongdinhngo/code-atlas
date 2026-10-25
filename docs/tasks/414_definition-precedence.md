---
id: 414
slug: definition-precedence
title: "A table defined in a schema project and again in migrations answers `subject_ambiguous` to `read_symbol` and `impact`"
phase: 2
milestone: Retrieval
status: done
depends_on: [403, 407]
---

## Why this exists

A consumer's survey, 2026-10-25. One central table had 8 definitions: a schema project plus several
migration files. Every table question came back `subject_ambiguous`, so the agent could not read the
table or its blast radius in one call. This was already a BACKLOG follow-up: *"`impact` on a table
defined in several files walks nothing … 403's fix covers `read_symbol` on routines"*.

403 resolves the case where every definition is a *versioned migration* redefinition: the highest
version answers (`symbol_pointers.py:131-166`). A schema project beside migrations is not ordered by
any standard, so only the project can say which definition is authoritative (R2).

## Scope

1. A project-declared definition precedence: an ordered list of path globs. Design picks where it
   lives, either the indirection rules file or the project config.
2. With it, `read_symbol` and `impact` answer from the preferred definition, and list the others as
   `other_definitions` (path and line). This mirrors 394 and 403's lists.
3. References, readers and writers are aggregated across every definition of the object. First
   measure whether they already are: edges that target the qname may need no change.
4. Without the setting, behaviour does not change. 403's migration ordering still applies.
5. Update the user docs.

## Acceptance criteria

- **AC1:** A fixture table is defined in `schema/t.sql` and `migrations/V2__t.sql`, with precedence
  `["schema/**"]`. `read_symbol` returns the schema definition plus one `other_definitions` entry.
- **AC2:** `impact` on that table walks its readers and writers. `find_references` lists writers found
  against either definition.
- **AC3:** Without the precedence, the answer is `subject_ambiguous`, as today.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 414 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W5 and merges #112 after #111. **Revert path:** `git revert` the branch's commits; no contract or schema moved.
- `TRACK: backend` · Run mode: `autorun 411 - 412 - 413 - 414 - 415 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/414-definition-precedence`, **stacked on `feat/413-record-attributes`** (#111). Contract `.mango/run-contract-414.txt`.
  RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 5 want-decision asked | 3 how-decision resolved+cited | 5 ASSUMED | skip: no`

**Premise.** `symbol_pointers.py:131-166` (403's ordering), `one_definition_first`, `read_symbol`, `impact`,
`subject_ambiguous` resolve. Recall (type 2, by handle — one shared rule several readers apply): 362-C1
`widen-every-query-that-shares-the-page`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 56,210 tokens) raised seven items; the eighth (AC2's
premise) surfaced at execute.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where it lives | how | the rules file, `{"definitions": {"precedence": [globs]}}`, beside `routes`/`records`: digested, so an edit reads `rules_stale` (396); a `Config` knob would add an env var and a identity slot for a build-time fact |
| H2 | aggregation (Scope 3) | how | measured: `find_references` lists a writer of the qname under either definition with no change — edges target the qname; the blocker was `impact._split_ambiguous` |
| H3 | the AC3 anchor | how | 407's `dbo.Orders` in `db/schema.sql` and `db/V002.sql` stays `subject_ambiguous` with no rule (its suite is unchanged) |
| W1 | ties and misses | want | **ASSUMED (awaiting ratification):** the first glob any production definition matches decides; one match answers, two stay `subject_ambiguous` (never a guess, never a later glob); no glob matching falls through to 403 |
| W2 | order against 394/403 | want | **ASSUMED (awaiting ratification):** test copies (394) first, then the declared precedence, then migration versions (403) — the project's word over an inferred order |
| W3 | which readers follow | want | **ASSUMED (awaiting ratification):** every caller of `one_definition_first` — `read_symbol`, `search_symbol` — plus `impact`'s seed plan (shared with `impact_modules`); one rule (R1.8) |
| W4 | field names | want | **ASSUMED (awaiting ratification):** `read_symbol`/`search_symbol` reuse `ambiguity` (new value `definition_precedence`) and `ambiguous_definitions` — the 394/403 list the ticket says to mirror; `impact` adds `other_definitions` (the ticket's name), its seed row placed at the answering definition. No contract move: `ambiguity` values are answer vocabulary, as 403's was |
| W5 | AC2 "walks its readers and writers" | want | **ASSUMED (awaiting ratification):** `impact` walks `IMPACT_KINDS` (`contract.py:179`: CALLS, NEW, EXTENDS, IMPLEMENTS, INCLUDES, IMPORTS) — no `READS`/`WRITES`, for a table with one definition too. 414 lifts the refusal; walking data edges is a new follow-up, not this ticket |

## Phase 1 — analysis

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=5 G=1 AC=3`
`CLARIFICATION: 8 raised | 8 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

W1–W5 count as self-resolved because the handover handed them back; each stands `ASSUMED` for the maintainer.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "could not read the table or its blast radius in one call" | a declared precedence lifts the refusal | ✅ |
| C1 | Scope 4 | no setting → no change; 403 still applies | AC3, W2 | ✅ |
| R1 | Scope 1 | ordered path globs | H1 | ✅ |
| R2 | Scope 2 | `read_symbol`, `impact` answer from it; others listed | W3, W4 | ✅ |
| R3 | Scope 3 | aggregation, measured first | H2 | ✅ |
| R4 | Scope 4 | as C1 | — | ✅ |
| R5 | Scope 5 | docs | TOOLS.md, two docstrings | ✅ |
| AC1 | AC1 | schema definition + one other | fixture | ✅ |
| AC2 | AC2 | `impact` walks; writers either definition | W5, H2 | ✅ (W5) |
| AC3 | AC3 | no precedence → `subject_ambiguous` | fixture, 407 | ✅ |

### AC validation

| AC | Ticket states | Independently computed | Match? | Falsifiable? |
|---|---|---|---|---|
| AC1 | schema definition + one `other_definitions` | `read_symbol` file `schema/t.sql`, `ambiguous_definitions == [migrations/V2__t.sql]` (W4's field) | Y | yes |
| AC2 | `impact` "walks its readers and writers" | `impact` walks no `READS`/`WRITES` edge on any table (`contract.py:179`); on `main` a one-definition table answers its seed alone | **N** → W5 | yes: not `subject_ambiguous`, seed at `schema/t.sql`, `other_definitions` names the migration |
| AC3 | `subject_ambiguous` | the same | Y | yes |

### Gap analysis (enhancement)

- Current: `one_definition_first` knows 394 and 403 only; `impact._split_ambiguous` refuses every shared qname.
- Target: a declared precedence in both.

**Blast radius.** `enrichment` (rules payload, a publisher), `indexer` (calls it), `symbol_pointers`, `read_symbol`,
`search_symbol`, `impact` (`plan_seeds`, shared with `impact_modules`), TOOLS.md.

### BASELINE

`BASELINE: green — 413's final gate on this stack: 4962 passed, 4 skipped, 1 xfailed, 2 host exclusions`

Ran at ff7c85b0 (413's gate; the base tip adds only its record). Host exclusions as 411.

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ globs over paths, no language · §R1.7 (change-type) ✅ the precedence on its own meta key · §R1.8 (change-type) ✅ one_definition_first carries it for every reader · §R2.2 (change-type) ✅ no directory name is built in; the project declares it · §R5.6 (change-type) ✅ a tie stays subject_ambiguous, never a guess · §R6.5 (change-type) ✅ the proving tests seen red · §R7.6 (change-type) ✅ TOOLS.md's read_symbol row extended in place`

## Phase 2 — design

### Approach

1. `_load_rules` returns `definitions`; `_precedence` validates `precedence`; `RulesPayload.precedence`; a
   `publish_definitions` stores it as `definition_precedence`, called beside `publish_records`.
2. `symbol_pointers.precedence_first` (W1) and `declared_precedence(store)`; `one_definition_first` gains
   `precedence`, tried after 394 and before 403 (W2).
3. `read_symbol` (both call sites) and `search_symbol` pass the stored precedence.
4. `impact._split_ambiguous` walks a qname the precedence settles; `SeedPlan.preferred` keeps its sites; the seed row
   is placed at the answering definition; `other_definitions` lists the rest.
5. Docs: TOOLS.md (a rules bullet, the `read_symbol` row), the `read_symbol` and `impact` docstrings.

### Rejected alternatives

- **A `Config` knob** (H1).
- **Make `impact` walk every 394/403 case too** — Scope 4: no setting, no change.
- **Walk `READS`/`WRITES` in `impact`** — W5: every table's answer would move; a ticket of its own.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| `find_references` already aggregates by qname | verified | `test_ac2_writers_aggregate_*` passes before the change (red run: 3 of 7 pass, this among them) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | read + store the precedence | `code_atlas/enrichment.py`, `code_atlas/indexer.py` | rules digest | R1 | 2/2 |
| 2 | the shared rule | `code_atlas/tools/symbol_pointers.py` | every `one_definition_first` caller | R2, C1 | 1/1 |
| 3 | readers | `code_atlas/tools/read_symbol.py`, `code_atlas/tools/search_symbol.py` | 394/403 suites | R2, AC1 | 2/2 |
| 4 | `impact` seeds | `code_atlas/tools/impact.py` | `impact_modules` (shared plan) | R2, AC2 | 1/1 |
| 5 | tests | `tests/test_definition_precedence.py` (new) | — | AC1–AC3 | 1/1 |
| 6 | docs | `docs/TOOLS.md` | doc budgets | R5 | 1/1 |
| 7 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `widen-every-query-that-shares-the-page` — traced: `rtk proxy grep -rn "one_definition_first\|def _split_ambiguous" code_atlas`
  → `search_symbol.py:619`, `read_symbol.py:300`, `read_symbol.py:357`, `impact.py:404`; all four carry the precedence.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — SQL adapter, build, tool | a real build through the SQL adapter | n/a | ✅ |
| AC2 | integration | the same build, `impact` and `find_references` | n/a | ✅ |
| AC3 | integration | a build without the rule; 407's suite | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_definition_precedence.py`

### Rollback

`git revert` the branch's commits; no contract or schema moved.

## Phase 3 — execute

Implemented in the main loop. Commits `d4d7e9dc` (core + tests), `922d709e` (docs).

**Red first** (R6.5): with `code_atlas/` stashed back to the base, `tests/test_definition_precedence.py` gives
`4 failed, 3 passed` — the three that pass are AC3, the tie (both ambiguous before), and Scope 3's measurement.

**Green at execute:**

Ran at 922d709e

```
$ .venv/bin/python -m pytest -q tests/test_definition_precedence.py
7 passed in 1.27s
$ .venv/bin/python -m pytest -q -k "definition or migration or test_cop or ambiguous or read_symbol or search_symbol or impact or rules or record"
549 passed, 4427 deselected in 76.36s (0:01:16)
$ .venv/bin/ruff check code_atlas tests && .venv/bin/mypy code_atlas
All checks passed!
Success: no issues found in 105 source files
```

**Verification sweep.** File axis: every touched file is on the change list. Behaviour axis: Approach 1–5 implemented
as approved.

| # | Deviation | Trace | Effect |
|---|---|---|---|
| D1 | `impact`'s seed row carried the migration's file | Approach 4 | the walk resolves a qname to one stored row; `_place_preferred_seeds` rewrites a depth-0 preferred seed to its answering site |
| D2 | AC2's premise | W5 | surfaced by the first AC2 test: `impact` on a one-definition table lists the seed alone |

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.

- **`challenger` round 1** (ticket-blind, 71,034 tokens; raw ticket only): R1, R3, R4, R5 met; R2 partly (the field
  name); AC1, AC3 met; AC2 not met as worded.
  - C1 (Critical) — `impact` walks no reader or writer, and the docs and test hid it — **resolved honestly**: the
    review measured that `main` answers a one-definition table with its seed alone, so AC2's first half was never
    `impact`'s (W5). TOOLS.md now says so, the AC2 test asserts the seed is the whole answer, and BACKLOG carries the
    follow-up *`impact` walks no `READS`/`WRITES`*.
  - M1 (Major) — `impact(paths=[the migration])` relocated its rows to the schema and listed the asked file as "other"
    — **fixed** in `20d3edb3`: a seed a path expanded into keeps its file; the precedence moves named qnames only.
  - M2 (Major) — `impact_modules` named the migration as the exemplar, no `other_definitions` — **fixed**: both tools
    call `place_preferred_seeds` and `attach_other_definitions` (R1.8).
  - M3 (Major) — `impact` applies the precedence alone, not 394 first — **accepted**: Scope 4 keeps `impact`'s
    answers unchanged without a precedence, so only the declared rule moves it; a glob naming a test copy alone is
    still skipped (production rows only).
  - m1 — a leading `/` matched nothing — **fixed**: dropped at load. m2 — `find_references` still lists both
    definitions unlabelled — **accepted** (it answers by qname, Scope 3). m5 — a cut search page applies no
    precedence — **documented**. The `other_definitions` name on `read_symbol` stays W4.
- **Round 2: verify-only, main loop.** The fixes stay inside `impact.py`, `impact_modules.py`, `enrichment.py`, the
  test and TOOLS.md.

```
$ .venv/bin/python -m pytest -q -k "impact or definition or migration or read_symbol or search_symbol or record or modules"
488 passed, 4491 deselected in 34.80s
```

Ran at 20d3edb3

Verdict: clean (challenger only — REVIEWER: OFF), W1–W5 standing for ratification; AC2's first half deferred by W5.
`Ph3/4 proven by`: R1 → `test_a_malformed_*`, `test_a_leading_slash_*`; R2, AC1 → `test_ac1_*`, `test_search_*`,
`test_impact_modules_*`; AC2 → `test_ac2_*` (both); R3 → `test_ac2_writers_*`; C1/R4, AC3 → `test_ac3_*`,
`test_two_definitions_*`, 407's suite; R5 → TOOLS.md.

Reviewed at 20d3edb3. Files: `code_atlas/enrichment.py`, `code_atlas/indexer.py`, `code_atlas/tools/symbol_pointers.py`,
`code_atlas/tools/read_symbol.py`, `code_atlas/tools/search_symbol.py`, `code_atlas/tools/impact.py`,
`code_atlas/tools/impact_modules.py`, `tests/test_definition_precedence.py`, `docs/TOOLS.md`. Working doc: this file.

## Phase 5 — finalise

**Durable lesson.**

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`

- 414-C1 `run-the-ac-on-main-before-the-design` (process, new): AC2 assumed `impact` walks a table's writers; one
  call on `main` would have shown it never does, before the design was built around it.

### Outward actions

Under the handover: push `feat/414-definition-precedence`; open its PR against `feat/413-record-attributes`.
Deferred to the maintainer: ratify W1–W5 (W5 the AC2 reading), merge after #111.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 56,210 |
| 3 execute | `implementer` — not dispatched; main loop implemented | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | ticket-blind `challenger` | 1 | 71,034 |

`LEDGER TOTAL: 127,244 · top cost driver: 4 review / challenger` — main loop unmeasured.
