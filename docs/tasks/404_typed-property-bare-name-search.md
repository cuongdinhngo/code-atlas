---
id: 404
slug: typed-property-bare-name-search
title: "`search_symbol` for a PHP property's bare name returns only near-misses"
phase: 2
milestone: Retrieval
status: done
depends_on: []
---

## Why this exists

From the anchor project's Round-3 feedback: `search_symbol "isInRespite"` for `public bool $isInRespite` returned
substring near-misses, and `git grep` found it. On `main` the PHP adapter stores the name as `$isInRespite`
(`Visitor.php:496`), so a bare query is neither an exact match nor a prefix, and `$` is not a separator in the
suffix check (`store.py:470-505`).

## Scope

1. An exact search for `name` matches a property stored as `$name`, ranked as an exact hit. The adapter's stored
   name is unchanged (R3).

## Acceptance criteria

- **AC1:** `search_symbol "isInRespite"` ranks `C::$isInRespite` first, as an exact match.
- **AC2:** `search_symbol "$isInRespite"` is unchanged.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 404 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews the PR (stacked on 403's); merging is theirs. **Revert path:** `git revert` the branch; nothing is stored differently.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun 404` — `REVIEWER: OFF` (waived, "with skipped reviewer") · `CHALLENGER: ON`.

## Phase 0 — refine

`PREMISE: 2 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** The PHP adapter stores a property as `$name` (`Visitor.php:496`; CONVENTION §3's qname
`\Ns\Class::$prop`), and `store.is_exact_or_prefix_match` / `is_direct_match` compare the query with the stored
name and qname as written, both at 8c0ddd00.

**Recall.** `widen-every-query-that-shares-the-page` (362-C1): the FTS path's band and the short-query `LIKE` path
answer the same search, so a widened match must reach both.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the match widens | how | the one predicate the band and `reason` read (`is_exact_or_prefix_match`, R6.7), so ranking and label move together |
| H2 | language-agnostic | how | the sigil is a contract constant, `NAME_SIGIL = "$"`, from CONVENTION §3's qname convention, applied by the shape of the stored name, never by language (R1.1). A `$`-led JS name reads the same way, which is the same right answer |
| H3 | AC2 | how | a query that carries the sigil takes the old path unchanged |
| H4 | the stored name | how | untouched (R3): only the comparison reads through the sigil |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=1 G=1 AC=2`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/5 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### Root cause

`config.cause_taxonomy` class: **logic**. Exactness compared the query against the stored spelling, and the
contract's property spelling carries a sigil a person does not type.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "returned substring near-misses, and `git grep` found it" | the property leads its search | ✅ |
| R1 | Scope 1 | "An exact search for `name` matches a property stored as `$name`, ranked as an exact hit" | H1, H2; both search paths | ✅ |
| C1 | R3 | "The adapter's stored name is unchanged" | H4 | ✅ |
| C2 | R1.1 | — | H2 | ✅ |
| AC1 | AC | "ranks `C::$isInRespite` first, as an exact match" | row 1, `reason: ok`, above BM25-favoured near-misses | ✅ |
| AC2 | AC | "`$isInRespite` is unchanged" | H3 | ✅ |

`RULE SECTIONS: 5 applicable — 4 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ a contract constant, no language branch · §R3.1 (change-type) ✅ no stored row or vocabulary changes · §R6.7 (change-type) ✅ one predicate for band and reason, one clause for page and count · §R6.5 (change-type) ✅ the proving test observed red on main · §R1.8 (recalled handle 362-C1) ✅ both search paths read the sigil`

## Phase 2 — design

**Approach.** `contract.NAME_SIGIL`. `is_exact_or_prefix_match` also compares the stored name without a leading
sigil when the query has none. `_search_short` and `_count_search_short` share one `_short_prefix_clause` that
adds the sigil-led pattern.

| # | Change | File | Covers |
|---|---|---|---|
| 1 | the sigil | `code_atlas/contract.py` | H2 |
| 2 | the predicate, the short clause | `code_atlas/store.py` | R1, H1, H3 |
| 3 | proving test | `tests/test_typed_property_bare_name_search.py` (new) | AC1, AC2 |
| 4 | docs | `docs/TOOLS.md`, `CHANGELOG.md` (0.6.0) | R7.2 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | R7.2 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- 362-C1 → traced: the short-query `LIKE` path reads the sigil too (`test_a_short_bare_name_finds_its_property`), after the challenger found it unwidened.

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1, AC2 | integration — the store and the tool | seeded rows in the field's shape: BM25-favoured near-misses in short files | authored (180's shape) | ✅ |
| AC1 | integration — the real PHP adapter | `test_the_php_adapter_property_is_found_by_its_bare_name` (`@needs_php`) | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test.** `pytest -q tests/test_typed_property_bare_name_search.py`.

## Phase 3 — execute

Branch `fix/404-typed-property-bare-name-search`, stacked on `fix/403-read-symbol-latest-routine-definition` (its
changelog line sits in 0.6.0). **Red first** on `main` (8c0ddd00): AC1 and the member-spelling unit test failed
(`wasIsInRespite` led). **Green** on the branch. `ruff`, `mypy` clean.

Axis 1 (the diff ⊆ the change list): rows 1–5. Axis 2: the approach as designed, narrowed by review.

## Phase 4 — review

`REVIEWER: OFF` — waived by the run's "with skipped reviewer". `CHALLENGER: ON`.

**Challenger** (ticket-blind `mango:challenger`, 64,273 tokens) on 9e41cfdf: `CHALLENGE: 2 met · 0 not met · 0
can't tell`. Fixed in d4d2ebbf:
- **1 (Important):** a query under three characters takes `_search_short`'s `LIKE`, which never matched `$id`. Both
  short sites now share `_short_prefix_clause`; the new test was observed red without it (`1 failed, 3 passed`).
- **2 (Important):** a `C::prop` arm added to the qname suffix check was unreachable: FTS must match first, and the
  trigram of `c::prop` never meets `c::$prop`. Beyond scope, it is removed with its test (R7.1).
- **3:** `NAME_SIGIL`'s comment now says any `$`-led name reads alike.
- **4, 5 (no change):** `read_symbol` / `find_references` resolve by qname, which the ticket does not scope. The
  PHP end-to-end test runs in Docker.

**Scope reconciliation.** Rows 1–5. `SCOPE: S` holds.

## Phase 5 — finalise

**Durable lessons.** None new. 362-C1 gains 404 (P1).

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 1 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

It cannot promote here: `/mango:promote` is the maintainer's pass between tickets.

### Outward actions

Under AGENTS.md's standing approval and the maintainer's handover of 2026-10-19: push
`fix/404-typed-property-bare-name-search`, then open the PR against `main`, marked stacked on 403's.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 4 review | `challenger` (ticket-blind) | 1 | 64,273 |

`LEDGER TOTAL: 64,273 · top cost driver: challenger`
