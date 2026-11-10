---
id: 448
slug: exec-target-casefold
title: "An `EXEC` target links case-insensitively, and its misses are counted"
phase: 2
milestone: "Round-3 field gaps"
status: done
depends_on: [386]
---

## Why this exists

The follow-up 386 left: a host-string or T-SQL `EXEC` matches its procedure case-sensitively, so
`exec insert_order` misses `Insert_Order`, and the miss is never counted. Round-3 field feedback hit
it in the last week: `find_callers` on a procedure answered `no_matches` while one T-SQL caller
spelled it lowercase with no schema. T-SQL resolves routine names case-insensitively under the
default collation, so this is the language standard, not one repo's habit (R2).

`resolver.py` already has a casefold pass for writes and column reads (`_link_writes_casefold`);
`_link_by_unique_function` (bare `EXEC`) does an exact match only.

## Scope

1. A bare or schema-qualified `EXEC` target from SQL, or from a host string the SQL literal scanner
   reads, that misses exactly falls back to a casefold match against `Function` nodes of the SQL
   language. One distinct qname links at the incoming tier; two or more stays unlinked.
2. An `EXEC` naming a procedure in a schema other than `dbo` resolves in that schema first, then
   casefold, as today's `dbo` default does.
3. Unlinked `EXEC` targets are counted per build (`exec_unresolved`) in the build report and
   `get_index_status`, beside the existing `routes_unresolved`.

## Out of scope

A Python `dbo.py` module's function named like a procedure stays an exact match (386); casefold is
for SQL targets only.

## Acceptance

- Fixture: `exec insert_order` from T-SQL and from a PHP string both link to `dbo.Insert_Order`.
- Fixture: `Insert_Order` in two schemas, called bare → unlinked, counted, no guess.
- `find_callers dbo.Insert_Order` lists both callers; contract unchanged (resolver only), so no
  rebuild is forced — say so in the CHANGELOG.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 448 · **work_doc_mode:** embed · **Current phase:** finalise
- `TRACK: backend` · Run mode: `autorun 447 - 448 - 449 - 450`, second — `REVIEWER: OFF` (waived: "with skipped
  reviewer") · `CHALLENGER: ON` · `cost_tier: standard`. The handover delegates decisions, so a want-decision is
  `ASSUMED`, never silent.
- Branch `feat/448-exec-target-casefold` from `main` at `89ecb16d`, built in a worktree while 447 held the main
  checkout. Contract `.mango/run-contract-448.txt` (mango 1.21.0), written before any code; RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 5 want-decision asked | 3 how-decision resolved+cited | 5 ASSUMED | skip: no`

`resolver.py`'s `_link_writes_casefold` and `_link_by_unique_function`, `routes_unresolved` (`indexer.py:212`),
`get_index_status` and 386's `dbo.` default (`SqlLiteral.php:77`) resolve. Recalled by handle (the change adds a shared
capability word and threads it to the resolver): 399-C1 `a-guest-row-needs-its-own-language`, 396-C1
`an-absent-reason-is-ok`. The exposure-checker (1 dispatch) returned 6; they fold in below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the order for a qualified target | how | exact, then casefold within that schema only — T-SQL never searches another schema for a qualified name (README: "the default schema is a server setting") |
| H2 | the schema part folds too | how | yes: `SALES.close_order` reaches `sales.Close_Order` — identifiers fold under the default collation (ticket, R2) |
| H3 | the casefold link's tier | how | the incoming tier, as the exact path (`_weaker_tier(incoming, "RESOLVED")`, ticket scope 1) |
| W1 | how the core knows a language's routines fold | want | **ASSUMED:** an optional adapter capability `case_insensitive_routines` (R1.6), announced by the SQL adapter — the core names no language (R1.1); no contract bump, an absent flag is legal |
| W2 | what `exec_unresolved` counts | want | **ASSUMED:** index-wide, after the link phase: every unlinked non-`DYNAMIC` CALLS from a folding language's site, plus another site's unlinked CALLS whose container folds to one a folding routine lives in (a host string's EXEC); `EXEC (@sql)` / `sp_executesql` are `DYNAMIC` and out |
| W3 | absent vs 0 | want | **ASSUMED:** `0` when counted; the field is absent on an index built before 448 or with no folding adapter (R5.6) |
| W4 | the PHP function rule | want | **ASSUMED:** PHP functions are case-insensitive too, but the PHP adapter does not announce the flag here — out of scope (362's follow-up) |
| W5 | a Python dotted call whose module shares a schema's name | want | **ASSUMED:** it may be counted in `exec_unresolved` (never linked: candidates are the folding languages' routines) — noise accepted over a language branch |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Out of scope · Acceptance) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=3`
`CLARIFICATION: 8 raised | 8 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "`find_callers` on a procedure answered `no_matches` while one T-SQL caller spelled it lowercase" | that caller links | ✅ |
| R1 | Scope 1 | "misses exactly falls back to a casefold match against `Function` nodes of the SQL language … two or more stays unlinked" | `_link_routines_casefold`, W1 | ✅ |
| R2 | Scope 2 | "resolves in that schema first, then casefold" | H1, H2 | ✅ |
| R3 | Scope 3 | "counted per build (`exec_unresolved`) in the build report and `get_index_status`" | W2, W3 | ✅ |
| C1 | Out of scope | "A Python `dbo.py` module's function … stays an exact match (386); casefold is for SQL targets only" | candidates are the folding languages' routines only | ✅ |
| C2 | Why | "the language standard, not one repo's habit (R2)" | T-SQL's collation rule, announced by its adapter | ✅ |
| AC1 | Acc 1 | "`exec insert_order` from T-SQL and from a PHP string both link to `dbo.Insert_Order`" | fixture | ✅ |
| AC2 | Acc 2 | "`Insert_Order` in two schemas, called bare → unlinked, counted, no guess" | fixture | ✅ |
| AC3 | Acc 3 | "`find_callers dbo.Insert_Order` lists both callers; contract unchanged … say so in the CHANGELOG" | fixture + CHANGELOG | ✅ |

**Gap.** `_link_by_unique_function` (`resolver.py:340`) matches `nodes.name` exactly; a qualified miss
(`dbo.insert_order`) has no fallback at all. **P6, run on `main`:** the proving test's AC rows are red there (Phase 3).

`BASELINE: green — resolver, SQL, status, capability and contract suites (47 files + tests/contract) on main at 89ecb16d: 674 passed, 67 skipped (TS adapter not installed in that worktree)`

Ran at 89ecb16d (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q <47 files matching sql|exec|resolver|index_status|capabilit|contract|status|…> tests/contract
674 passed, 67 skipped in 57.70s
```

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 the core names no language, R1.6 the fold is an announced capability, R1.4 SQL stays in store.py · §2 (change-type) ✅ R2.1 T-SQL collation rule, no repo name · §3 (change-type) ✅ R3.2 the capability word lives in contract.py, no vocabulary moved · §5 (change-type) ✅ R5.2 two folds stay unlinked, R5.6 absent vs 0 · §6 (change-type) ✅ R6.1 an integration fixture, R6.5 seen red · §7 (change-type) ✅ R7.2 ledger`

## Phase 2 — design

`HANDLES: 2 recalled | 0 traced (command + result) | 2 does not apply (reason) | 0 unanswered`

- `a-guest-row-needs-its-own-language` — does not apply because the change reads a site's language through the existing
  `_site_language` (row first, then file) and adds no new `files.language` reader.
- `an-absent-reason-is-ok` — does not apply because the change adds a count field and no relabel keyed on `reason`.

**Approach.** (1) `contract.CASE_INSENSITIVE_ROUTINES` joins `KNOWN_CAPABILITIES`; the SQL adapter announces it. (2)
`resolve_edges` takes the folding languages (from the build's handshake, else the stamp) and runs
`_link_routines_casefold` on what `_link_by_unique_function` left: a bare name from a folding site against that
language's Functions, a qualified name against every folding language's Functions, one distinct qname or nothing. (3)
The store's casefold lookups gain the `language` filter `nodes_by_names` has. (4) `publish_exec_unresolved` stamps the
count; `BuildReport.exec_unresolved` and `get_index_status` read it.
**Rejected:** `if language == "sql"` in the resolver (R1.1); a contract bump with a node field (the ticket keeps the
contract); counting misses per resolve batch (an incremental would count its delta only, R5.5).
**Proving test:** `tests/test_exec_target_casefold.py`.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| capability word | `code_atlas/contract.py`, `adapters/sql/index.js` | `KNOWN_CAPABILITIES` pins (`test_optional_field_capture.py`, `test_contract_schema.py`) | R1 · 1/1 |
| casefold pass | `code_atlas/resolver.py` | every bare / qualified CALLS miss | R1, R2 · 2/2 |
| language-filtered casefold + count | `code_atlas/store.py` | `_link_writes_casefold` (same methods, default unchanged) | R1, R3 |
| thread + stamp + report | `code_atlas/indexer.py` | `BuildReport` (`build_or_update_index` serialises it) | R3 |
| status field | `code_atlas/tools/get_index_status.py` | status payload | R3 |
| proving test | `tests/test_exec_target_casefold.py` | — | AC1–AC3 · 3/3 |
| docs | `docs/TOOLS.md`, `adapters/sql/README.md`, `CHANGELOG.md` | — | AC3, R9.4 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC3 | integration (adapters → resolver → tools) | integration: full build + `find_callers` / `get_index_status` | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

Rollback: revert the branch; an index re-links on its next build. Porting: one repo.

## Phase 3 — execute

Main loop, no `implementer` (`477dfffb`, `652bba97`, `f6816cdc`, `95f352de`), in a worktree. **Sweep.** Axis 1: the diff
is the approved files plus nothing else; `ruff` and `mypy` clean; `test_contract_sole_source` caught a
`("CALLS", "DYNAMIC")` tuple in `store.py` — now spelled in the SQL text (`f6816cdc`). Axis 2: approach bullets 1–4
implemented-as-approved. A first cut of the change was lost to a patch saved through `rtk git diff` (a compact summary,
not a patch) and re-applied from the same edits before any commit — no behaviour differs (lesson 386-C1's tool).

The new tests on the base (only the test file added):

Ran at 89ecb16d (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_exec_target_casefold.py
FAILED tests/test_exec_target_casefold.py::test_ac1_a_lowercase_bare_exec_links_from_tsql
FAILED tests/test_exec_target_casefold.py::test_ac1_a_lowercase_exec_in_a_php_string_links
FAILED tests/test_exec_target_casefold.py::test_scope2_a_schema_qualified_exec_folds_in_its_own_schema
FAILED tests/test_exec_target_casefold.py::test_ac2_one_name_in_two_schemas_stays_unlinked_and_counted
FAILED tests/test_exec_target_casefold.py::test_scope3_a_linked_index_counts_zero_and_status_says_so
FAILED tests/test_exec_target_casefold.py::test_scope3_a_host_string_miss_is_counted
FAILED tests/test_exec_target_casefold.py::test_no_folding_adapter_leaves_status_unchanged
7 failed, 1 passed in 2.72s
```

Ran at 95f352de
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q <the same 47 files> tests/contract
749 passed in 88.06s (0:01:28)
```

## Phase 4 — review

`REVIEWER: OFF` (waived by the run's args — no rule-book seat looked) · `CHALLENGER: ON`. Review step: the ticket-blind
`challenger` alone, at `95f352de`; payload = the raw ticket (`git show 89ecb16d:<this file>`) + the branch diff.

- **`challenger` round 1** (87,158 tokens): its final line, transcribed:

`CHALLENGER VERDICT: 13 requirement(s) rebuilt | 13 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

  **Taken:** F5 — the CHANGELOG said "the next build links them"; an incremental's delta is keyed on exact qnames, so
  it is the next **full** build. **Recorded, not changed:** F1 (the capability word in `contract.py` and the SQL
  adapter — W1, said in the CHANGELOG); F2 (the count's breadth — W2, W5); F6 (a bare name reaches the one routine of
  that name in any schema — today's exact rule, H1). **F3/F4 (cost), measured on the anchor** below: no slowdown.

**Anchor (counts and timings only, `~/code-atlas-review/448-anchor.md`).** The anchor's tracked PHP + SQL, one fresh
build per tree: SQL-site EXEC linked 1,198 → 1,253 of 1,428; host-string EXEC 93 → 93 of 106; `exec_unresolved` 188;
full build 339 s → 335 s.

Reviewed at 95f352de — files: `code_atlas/{contract,resolver,store,indexer}.py`, `code_atlas/tools/get_index_status.py`,
`adapters/sql/index.js`, `adapters/sql/README.md`, `tests/test_exec_target_casefold.py`, `docs/TOOLS.md`,
`CHANGELOG.md`; working doc `docs/tasks/448_exec-target-casefold.md`.

`Ph3/4 proven by`: AC1–AC3, R1–R3 → `tests/test_exec_target_casefold.py` (8); the anchor run.

## Phase 5 — finalise

**Durable lesson.** 386-C1 `symbol:rtk git diff` seen again (type 1): a patch saved through the hook was a summary,
and a checkout discarded the change — the record did not prevent it.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=1 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/AGENT_BRIEF.md | mango files written: 0`

FALSIFY's check: the patch file this run saved (`448.patch`) opens with `rtk`'s stat table, not a `diff --git` header.

Gate at `51fa5efc` (the tip but this record; after review only bookkeeping and the CHANGELOG wording moved):

```text
scripts/gate.sh
26 passed · 0 failed · 0 skipped
GATE GREEN — all 26 checks passed
```

**P8.** `scripts/cross_repo_validate.py --public-only --skip-clone` on this branch's code: `public_ok: 11,
public_failed: 0` — no floor moved, so none re-floored.

### Outward actions

Under the handover: push `feat/448-exec-target-casefold`; open its PR against `main`. Deferred: ratify W1–W5 and the
AGENT_BRIEF promotion; merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 48,121 |
| 4 review | ticket-blind `challenger` | 1 | 87,158 |

`LEDGER TOTAL: 135,279 · top cost driver: 4 review / challenger` — main loop unmeasured.
