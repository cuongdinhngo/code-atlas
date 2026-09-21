---
id: 315
slug: search-symbol-filters-by-kind-but-not-by-path
title: "search_symbol can filter by kind and namespace but not by file path, so a common token buries the one src/ hit under hundreds of test and mirror rows and the agent filters by eye"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [056]
---

## Why this exists (field-retro batch 2026-09-20/21)

Every retro in the batch hit the same friction on a common token: `Database` → `total_count: 506`,
`Member_Site` → 645 (`truncated: true`), the canonical hit buried under test doubles, compat mirrors
and FK-constraint rows. The agent's own words: *"I mentally filter out tests/ on every common-name
query."* The `kind:` filter shipped (056, `search_symbol.py:97-100`) and the default ranking is
already tier-first (265/297), but neither lets the agent say **"only under `src/`"** — and a
mental filter over a 50-row page is exactly the manual, error-prone step the index is meant to remove.

`search_symbol` accepts `kind` and `namespace` (a qname-prefix filter), but **nothing keyed on file
path**: `store.search_nodes` narrows only by kind and namespace (`store.py:2530-2571`, `_narrow`
`:3949-3976`); there is no `path`/`path_prefix` param on the tool (`search_symbol.py:97-105`) and a
grep of the repo for `path_prefix` finds none. `find_references` compounds it: it pages at 50 and
gives an exact `total_count` but no way to enumerate within a subtree (`find_references.py:452-458`),
so "list every consumer under `src/`" is unanswerable.

## Goal

Let an agent scope a symbol search (and a reference enumeration) to a file-path prefix, so a common
token returns the handful under the tree it cares about instead of a truncated page it must eyeball.

## Scope / Deliverables

1. **A `path_prefix` param on `search_symbol`** (file-path, distinct from the qname `namespace`
   filter), threaded into `store.search_nodes` as a path clause beside `_narrow`, fail-loud on a
   malformed value in the 056 style.
2. **The same filter on `find_references`** so a consumer enumeration can be scoped to a subtree —
   turning the 50-row sample into an enumerable answer within that scope.
3. **Disclosure when the filter hides an otherwise-exact hit** — mirror the existing `kind_excluded`
   pattern (`search_symbol.py:353-363`) so a path filter that excludes the match says so, rather than
   reading as absence.

## Constraints

- 056: an invalid `path_prefix` fails loud naming the expectation; it is published in the schema.
- The filter narrows, it does not re-rank — the tier-first order (265) is unchanged within the
  filtered set.
- R4.2: identical query + filter → identical rows.
- Path matching is on the stored, normalized path form (POSIX, index-root-relative) — one spelling,
  documented, not OS-dependent.

## Acceptance criteria

- **AC1** `search_symbol("Database", path_prefix="src/")` returns only rows whose file is under
  `src/`, in the same tier order, with `total_count` reflecting the filtered population.
- **AC2** A `path_prefix` that excludes an exact-name hit returns a `path_excluded`-style disclosure,
  not a bare `no_matches`.
- **AC3** `find_references(..., path_prefix=...)` enumerates consumers within the subtree; the page /
  `truncated` semantics stay honest for the filtered count.
- **AC4** An invalid `path_prefix` fails loud (056); the param appears in the published schema.

## Out of scope

- A path filter on `find_orphans` — its own scope question is [316]-adjacent and separately ticketed
  if wanted; not folded here.
- Re-ranking or changing the default order.
- Glob/regex path matching — a plain prefix only; anything richer is a later, evidence-backed ticket.

## References
`code_atlas/tools/search_symbol.py:97-105`, `:353-363`, `code_atlas/store.py:2530-2571`, `:3949-3976`,
`code_atlas/tools/find_references.py:452-458`, [056](056_filter-values-fail-loud.md),
ENGINEERING_RULES R4.2.
<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 315 — search_symbol path_prefix (working doc)
- **TIER:** full · **TRACK:** backend · **SCOPE:** M · **BASELINE:** green
- **Depends on:** 056 (done)
- **reviewer:** off · **challenger:** on
- **Branch:** `feat/315-search-symbol-path-prefix`
- **work_doc_mode:** embed · **working-doc:** this file below separator

## Session status
- **Current phase:** finalise

## Phase 0
`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
- search_symbol.py:97-105, :353-363 · store.py:2530-2571, :3949-3976 · find_references.py:452-458 · kind_excluded pattern · _path_under (120) · 056 fail-loud
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
| # | Claim | Type | Matched by | Relevant? |
|---|-------|------|------------|-----------|
| 1 | filter-contains-by-member-kind-before-page | 2 | handle | adjacent — path filter is orthogonal |
`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`
**INPUT KIND:** ticket.

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | How to express path SQL | Reuse `_path_under` on `nodes.file_path` / `edges.file_path` | store.py:3942-3946 (task 120) |
| 2 | Invalid path_prefix shape | Fail loud: empty, absolute, `\\`, `.`/`..` segments | ticket Constraints + 056 / R5.3 |
| 3 | Disclosure payload | `reason=path_excluded` + `path_excluded: [file paths]` mirroring kind_excluded | search_symbol.py:353-363; ticket AC2 |

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis
`SECTIONS: 5 found (Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=4 R=3 G=1 AC=4`
`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R4.2 (change-type) ✅ · R5.3 (change-type) ✅ · R5.6 (change-type) ✅ · R7.2 (change-type) ✅`
`BASELINE: green`

| ID | Source | Verbatim (abbrev) | Interpretation | Ph1 | Ph2 | Ph3/4 | Status |
|----|--------|-------------------|----------------|-----|-----|-------|--------|
| C1 | Constraint | invalid fails loud; schema | require_path_prefix + published param | ✅ | 1/5 | | ✅ |
| C2 | Constraint | narrows, no re-rank | SQL WHERE only | ✅ | 1/5 | | ✅ |
| C3 | Constraint | R4.2 identical→identical | deterministic SQL | ✅ | 1/5 | | ✅ |
| C4 | Constraint | POSIX index-root-relative | stored file_path form | ✅ | 1/5 | | ✅ |
| R1 | Scope | path_prefix on search_symbol→store | search_nodes + count | ✅ | 1/5 | | ✅ |
| R2 | Scope | same on find_references | edges_by_target(s) | ✅ | 1/5 | | ✅ |
| R3 | Scope | path_excluded disclosure | reason + field | ✅ | 1/5 | | ✅ |
| G1 | Goal | scope search/refs to path prefix | AC1-AC3 | ✅ | 1/5 | | ✅ |
| AC1 | AC | only under src/; total filtered | proving test | ✅ | 1/5 | | ✅ |
| AC2 | AC | path_excluded not no_matches | proving test | ✅ | 1/5 | | ✅ |
| AC3 | AC | find_references scoped; honest page | proving test | ✅ | 1/5 | | ✅ |
| AC4 | AC | invalid fails loud; schema | proving test | ✅ | 1/5 | | ✅ |

## AC validation
| AC ID | Ticket states | Independently computed | Match? | Falsifiable? |
|-------|---------------|------------------------|--------|--------------|
| AC1 | only under src/; total filtered | _path_under LIKE | Y | measurable |
| AC2 | path_excluded disclosure | reason + path_excluded list | Y | greppable |
| AC3 | refs under subtree; truncated honest | count with same filter | Y | measurable |
| AC4 | invalid loud; schema | ValueError + list_tools | Y | greppable |

## Phase 2 — Design
**Approach:** Add optional `path_prefix` to `search_symbol` and `find_references`; validate via shared `require_path_prefix` (nav_result); thread into `search_nodes`/`count_search_nodes` and edge list/count APIs using existing `_path_under`. On zero-hit with path filter that hid exact names, emit `REASON_PATH_EXCLUDED` + `path_excluded` file list (after kind_excluded). No re-rank.

**Rejected alternatives:** (a) post-filter in Python after unbounded fetch — breaks total_count honesty; (b) glob/regex — out of scope; (c) new SQL helper instead of `_path_under` — duplicates 120.

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
- filter-contains-by-member-kind-before-page → path filter is orthogonal; contains demote also receives path_prefix so demotion stays inside filtered set

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**APPROVED CHANGE LIST:**
1. `code_atlas/store.py` — path_prefix on search + edge APIs; `_with_path_prefix` / `_path_prefix_predicate`
2. `code_atlas/tools/nav_result.py` — `path_excluded` reason + `require_path_prefix`
3. `code_atlas/tools/search_symbol.py` — param, thread, path_excluded disclosure
4. `code_atlas/tools/find_references.py` — param, thread to edge queries
5. `tests/test_search_symbol_path_prefix.py` — AC1–AC4 proving tests
6. reason-vocabulary pin tests + `docs/TOOLS.md` note
7. working doc / BACKLOG / TOKEN_LEDGER

**PROVING TEST:** `.venv/bin/python -m pytest tests/test_search_symbol_path_prefix.py -q`
**TREE_PATHS:** `code_atlas/store.py code_atlas/tools/nav_result.py code_atlas/tools/search_symbol.py code_atlas/tools/find_references.py tests/test_search_symbol_path_prefix.py tests/test_empty_answer_cannot_explain_itself.py tests/test_relation_unmodelled_for_language.py tests/test_nav_reason_codes.py docs/TOOLS.md docs/tasks/315_search-symbol-filters-by-kind-but-not-by-path.md docs/BACKLOG.md docs/TOKEN_LEDGER.md`

**Gate 2 status:** cleared (autorun)

## Phase 3 — Execute
Implemented approved list. Proving test green.
`PROVING TEST:` `.venv/bin/python -m pytest tests/test_search_symbol_path_prefix.py -q` → 6 passed.

## Phase 4 — Review
`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — round1 NOT CLEAN (AC3 result_subtrees unfiltered); round2 CLEAN (agent 00348627). Gate 4: challenger CLEAN; reviewer waived.

## Phase 5 — Finalise
`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop`
