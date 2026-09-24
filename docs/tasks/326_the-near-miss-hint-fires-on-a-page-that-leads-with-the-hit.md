---
id: 326
slug: the-near-miss-hint-fires-on-a-page-that-leads-with-the-hit
title: "search_symbol tells a truncated page it is 'substring near-misses, not hits' even when row 1 is the exact match — so the agent learns to ignore the one hint that exists to stop it"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [167, 245, 249]
---

## Why this exists (field retro, 2026-09-24 — FIELD-1624/1626/1636 batch)

One session saw `try_instead_hint: "the page is substring near-misses, not hits — …"` **three
times on pages that led with an exact hit**: a bare method name (410 rows, exact `X::name` methods
on the page), a class-constant enum (the class itself at row 2) and a `kind=Table` query (row 1
exact). Its conclusion: *"I learned to ignore it, which is the opposite of what a hint is for."*

**The cause is one predicate carrying two findings.** `_needs_narrowing_route`
(`search_symbol.py:649-653`) is true for `reason=substring_match` **or** for any truncated page
(`hits.truncated and total_count > len(results)`). Both arms then attach the same prose,
`TRY_INSTEAD_HINT_NARROW_BY_QNAME` (`nav_result.py:166`), which asserts the page holds no hits. The
`reason` is right — `is_direct_match` (`store.py:393`) already decides `ok` vs `substring_match`
(`search_symbol.py:349-353`) — but the hint contradicts it on the truncated arm.

245 scoped the route to *`reason: substring_match` with `total_count` far above `max_results`*;
the shipped predicate dropped the `substring_match` half on its second arm. 245's own rule is that a
different finding gets a different hint (`nav_result.py:163-164`) — "near-misses" and "a flood that
still holds the hit" are two findings sharing one sentence.

## Goal

The near-miss hint rides only a page the reason calls a near-miss. A truncated page that holds a
direct hit says it is truncated, not that it is wrong.

## Scope / Deliverables

1. **Split the truncated arm from the near-miss arm** in `_needs_narrowing_route`'s two callers
   (`_single_payload`, `_batch_answer`), so the sweep and single-subject shapes cannot drift.
2. **A truncated `reason=ok` page gets its own hint** (narrow by `kind` / `path_prefix`, the two
   filters that exist) or none — the design call — but never the "not hits" prose.
3. **`substring_match` and `separator_normalised` keep today's hints** byte-for-byte.

## Constraints

- **061** — only the truncated-and-direct arm changes; every other payload is byte-identical.
- **R6.7** — the hint follows `reason`; do not add a second direct-match test beside `_direct`.
- **093** — any new hint is a `TRY_INSTEAD_HINT_*` registry entry, pinned by the invariant test.
- Comments ≤ 3 lines (R7.5).

## Acceptance criteria

- **AC1** A fixture query whose first page is truncated and leads with an exact hit carries no
  `TRY_INSTEAD_HINT_NARROW_BY_QNAME`; red-arm test fails on today's code.
- **AC2** A first page of only substring hits still carries it (regression).
- **AC3** The same two cases hold inside a `queries=[…]` sweep.

## Out of scope

- Ranking exact final-segment matches above longer prefixes (`getX` over `getXList`) — a separate
  ranking question; the retro asked for it, but the hint lie is the defect.

## References
`code_atlas/tools/search_symbol.py:349-353,506-512,549-556,649-653`;
`code_atlas/tools/nav_result.py:163-168`; `code_atlas/store.py:393`; tickets 167, 245, 249.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 326 — near-miss hint on truncated-ok page (working doc)

- **Ticket:** 326 · local
- **Type:** bug
- **Repo(s) / Porting:** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed · path: docs/tasks/326_the-near-miss-hint-fires-on-a-page-that-leads-with-the-hit.md
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** finalise — next: push branch, open PR

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Truncated reason=ok page: own hint vs none (Scope 2) | Own hint `TRY_INSTEAD_HINT_NARROW_BY_FILTER` naming `kind=` / `path_prefix=`; route `search_symbol` | Ticket Scope 2; `nav_result.py` 245 rule "different finding → different hint" (lines 163-164); R5.4 progress route |

## Requirements matrix

`SECTIONS: 7 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope · References) | 7 decomposed | ROWS: C=4 R=3 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | near-miss hint rides only a near-miss page; truncated+hit says truncated | split predicates + new hint | D1 D2 | AC1 | ✅ |
| R1 | Scope 1 | Split truncated arm from near-miss arm in both callers | `_is_near_miss_page` / `_is_truncated_direct_page` in `_single_payload` + `_batch_answer` | D1 | AC1 AC3 | ✅ |
| R2 | Scope 2 | Truncated ok gets own hint or none — never "not hits" | `TRY_INSTEAD_HINT_NARROW_BY_FILTER` | D2 | AC1 | ✅ |
| R3 | Scope 3 | substring_match + separator_normalised keep today's hints byte-for-byte | near-miss arm unchanged | D1 | AC2 + separator tests | ✅ |
| C1 | Constraints | 061 — only truncated-and-direct arm changes | non-truncated ok / substring hints unchanged | D1 | AC2 + 245 tests | ✅ |
| C2 | Constraints | R6.7 — hint follows reason; no second direct-match test | predicates use `hits.reason` + truncated flags only | D1 | review | ✅ |
| C3 | Constraints | 093 — new hint is TRY_INSTEAD_HINT_* registry entry | `nav_result.py` constant; invariant derives it | D2 | try_instead invariant | ✅ |
| C4 | Constraints | comments ≤ 3 lines | R7.5 | D1 D2 | review | ✅ |
| AC1 | AC | truncated ok page carries no NARROW_BY_QNAME | proving test asserts FILTER hint | D1 D2 | proving | ✅ |
| AC2 | AC | substring-only first page still carries NARROW_BY_QNAME | proving AC2 | D1 | proving | ✅ |
| AC3 | AC | same two cases in queries=[…] sweep | proving AC3 | D1 | proving | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? |
|-------|---------------|------------------------|--------|--------------|
| AC1 | no NARROW_BY_QNAME on truncated ok | assert hint == FILTER and != NARROW_BY_QNAME | Y | measurable |
| AC2 | substring page still has NARROW_BY_QNAME | assert reason=substring_match + hint | Y | measurable |
| AC3 | both in sweep | assert per-subject hints; none on envelope | Y | measurable |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

- Q1 (self-resolved): Scope 2 own-hint vs none → own filter hint (Phase 0 HOW #1).

## Phase 1 — Analysis

- Root cause (bug, `logic`): `_needs_narrowing_route` (`search_symbol.py` pre-change ~649-653) is true for near-miss **or** any truncated page; both arms attached `TRY_INSTEAD_HINT_NARROW_BY_QNAME` which asserts "not hits". Truncated `reason=ok` pages (exact hits on page 1) got the lie.
- Blast radius: `_single_payload` + `_batch_answer`; `nav_result` hint registry; 245/249 tests; 093 invariant.

`TRACK: backend — 0/3 touched files under UI paths`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R6.7 (change-type) ✅ hint keyed to reason only · R1.1 (change-type) ✅ no language branch · R7.5 (change-type) ✅ comments ≤ 3 · R7.2 (change-type) ✅ ledger + BACKLOG`

Baseline record — tree `7eb734192ebffe539c2c2d9e80000884a3882a85`. Command `.venv/bin/python -m pytest tests/test_search_symbol_truncated_substring_route.py tests/test_try_instead_is_a_callable_tool_name.py -q`:

```
11 passed in 2.23s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: replace `_needs_narrowing_route` with `_is_near_miss_page` (substring/separator reasons only) and `_is_truncated_direct_page` (reason=ok ∧ truncated ∧ total>len). Near-miss arm keeps FILE_OUTLINE + existing hints byte-identical. Truncated-ok arm attaches SEARCH_SYMBOL + new `TRY_INSTEAD_HINT_NARROW_BY_FILTER`. Both callers updated.
- Rejected: **none** (no try_instead on truncated-ok) — leaves a truncated flood without a progress route (R5.4); 245 already established different finding → different hint, not silence. **Keep one predicate with a ternary hint** — still couples findings; ticket Scope 1 asks for the split.

**Assumptions:** none novel — same store predicates as today.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | Split predicates; rewire both callers | code_atlas/tools/search_symbol.py | 245/249 tests; batch envelope | R1 R3 C1 C2 G1 AC* | 1/1 |
| D2 | New HINT_NARROW_BY_FILTER | code_atlas/tools/nav_result.py | 093 invariant derives hints | R2 C3 | 1/1 |
| D3 | Proving tests AC1–AC3 | tests/test_truncated_ok_page_not_near_miss_hint.py | new file | AC1 AC2 AC3 | 1/1 |
| D4 | Ticket embed; BACKLOG; TOKEN_LEDGER | docs/tasks/326_… · docs/BACKLOG.md · docs/TOKEN_LEDGER.md | bookkeeping tests | R7.2 | 1/1 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | pytest proving | authored fixture | ✅ |
| AC2 | integration | pytest proving | authored fixture | ✅ |
| AC3 | integration | pytest proving | authored fixture | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_truncated_ok_page_not_near_miss_hint.py -q`

`SCOPE: S`

## Phase 3 — Execute

**Branch:** feat/326-near-miss-hint-truncated-ok

Pre-change red-arm (historical on main predicate): truncated ok attached NARROW_BY_QNAME — now asserted absent in proving AC1.

Ran at 87741d28fc8b2b0e824fd48e984bed46051f3ee6

```
$ .venv/bin/python -m pytest tests/test_truncated_ok_page_not_near_miss_hint.py tests/test_search_symbol_truncated_substring_route.py tests/test_separator_spelling_near_miss.py tests/test_try_instead_is_a_callable_tool_name.py -q
22 passed in 1.84s
```

Files: `code_atlas/tools/search_symbol.py`, `code_atlas/tools/nav_result.py`, `tests/test_truncated_ok_page_not_near_miss_hint.py` — all on D1–D3.

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed — split predicates + FILTER hint implemented-as-approved`

## Phase 4 — Review

REVIEWER: OFF (--no-reviewer)
CHALLENGER: ON — round-1 9 met / 1 not met (061: truncated index_stale lost NARROW_BY_QNAME) → legacy truncated arm in both callers → round-2 10 met / 0 not met / 0 can't tell CLEAN.

Verdict: `clean (challenger only — REVIEWER: OFF)`

Ran at 87741d28fc8b2b0e824fd48e984bed46051f3ee6

```
$ .venv/bin/python -m pytest tests/test_truncated_ok_page_not_near_miss_hint.py tests/test_search_symbol_truncated_substring_route.py tests/test_separator_spelling_near_miss.py tests/test_try_instead_is_a_callable_tool_name.py -q
22 passed in 1.84s
```

`REVIEW: CLEAN`
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`

`Reviewed at 87741d28fc8b2b0e824fd48e984bed46051f3ee6` · reviewed files: code_atlas/tools/search_symbol.py, code_atlas/tools/nav_result.py, tests/test_truncated_ok_page_not_near_miss_hint.py · working doc (embedded, staleness-exempt): docs/tasks/326_the-near-miss-hint-fires-on-a-page-that-leads-with-the-hit.md

## Phase 5 — Finalise

Outward (handover-authorised only): push `feat/326-near-miss-hint-truncated-ok`, open the PR. Never merge.

Revert: revert the PR.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| review | challenger | 1–2 | unmeasured (host surfaces no usage block) |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: unmeasured (subagent dispatch only; host surfaces no usage) · top cost driver: review/challenger rounds 1–2`

