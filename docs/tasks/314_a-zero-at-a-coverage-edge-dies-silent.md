---
id: 314
slug: a-zero-at-a-coverage-edge-dies-silent
title: "A tool that returns zero at a coverage edge attaches no try_instead and names no grep target, so the code-atlas chain ends on a bare no_matches and the session falls back to a grep it never returns from"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [065, 093, 296]
---

## Why this exists (field-retro batch 2026-09-20/21 + the 300 H4 lead)

The BETA retro's root cause was a trigger created by `EXEC('CREATE TRIGGER ResFacToEpicor …')`.
`search_symbol "ResFacToEpicor"` returns a bare `no_such_symbol` — **byte-identical to "does not
exist"** — even though the file that holds it is already stamped
`File.extra.unmodelled_resolution: ["dynamic_sql"]` (task 296, `tools/find_orphans.py:82-95`). The
agent read the zero as absence and went to grep, and never came back to the index.

This is one instance of a general dead-end. When a core tool returns zero on something genuinely
outside coverage **with no stored trace to escalate on** (dynamic dispatch, dynamic SQL, superglobal
reads), the payload is a bare `no_matches`/`no_such_symbol` with **no `try_instead` and no fallback
target**: `find_callers` attaches a redirect only when `reason == relation_unmodelled_for_language`
(`find_callers.py:564`); `find_references` only when an unlinked-edge or relation-unmodelled arm fired
(`find_references.py:469-524`); `search_symbol`'s token-candidate arm needs non-empty name tokens
(`search_symbol.py:364`). Worse, even the hints that *do* fire and say "treat the empty answer as
unmeasured, not as zero" (`nav_result.py:172-175`) **name no place to look next**. The one hint that
names an out-of-index text search, `TRY_INSTEAD_HINT_PATH_BASENAME` (`nav_result.py:165`), is wired
into exactly one tool (`include_graph.py:91`) and none of the seven core ones.

The general "grep for absence / literal text" guidance exists, but only **once, at session scope**
(`instructions.py:37-43`) — never repeated at the per-call dead-end where the agent actually decides
to fall back. Task 300 flagged the un-mined lead this maps onto (H4, `docs/tasks/300_*.md:129-134`):
*"the first payload terminates or continues the chain"* — found the index, took one answer, then 29
Grep/Read calls. This is the chain-continuation problem, distinct from first-call adoption: the payload
is already in the agent's context, so it **can** steer the next step (081/099's "structurally
incapable" verdict is about riding a payload to win the *first* call — not this).

## Goal

Make a code-atlas call that lands at a coverage edge hand off deliberately — name the gap and the
concrete fallback — instead of returning a bare zero that ends the chain, without ever claiming a
coverage it does not have.

## Scope / Deliverables

1. **The dynamic-SQL case (the A1 instance):** when a `search_symbol`/nav zero-result subject resolves
   to file(s) carrying `unmodelled_resolution: ["dynamic_sql"]` (or the language's stamp is present),
   the payload names the gap and points to grep — reusing the existing stamp (296), never synthesizing
   a symbol from a runtime string (R5.2).
2. **The bare dead-ends:** the `no_matches`/`no_such_symbol` paths in `find_callers`,
   `find_references`, and `search_symbol` that today attach nothing gain the coverage note
   (`coverage.py:135-197`) plus a redirect, using the `TRY_INSTEAD_HINT_PATH_BASENAME`-style
   machinery generalized past `include_graph`.
3. **Every "unmeasured, not zero" hint names a fallback** — the relation-unmodelled / resolution-
   unmodelled hints (`nav_result.py:172-175`, `find_orphans.py`) gain a concrete "grep the X" or
   "use the runtime's own loader" target, so the honesty is actionable, not just a caveat.
4. **No false gap:** a genuinely-absent subject on a fully-covered single-language index stays
   byte-identical (061) — the redirect fires only when a real coverage reason exists.

## Constraints

- R5.2 / R5.6: surface the existing stamp and coverage fields; never claim a target, never synthesize
  a symbol from a string.
- R1.1: no language branch in the core — the dynamic-SQL case keys off the language-agnostic
  `unmodelled_resolution` stamp, not a `language == "sql"` test.
- R4.2 / 061: identical input → identical payload; nothing added where there is no coverage reason.
- 093: a `try_instead` must be a callable tool name or a standalone prose hint, per the two-register
  rule — a grep instruction rides as the hint, not as a fake tool.

## Acceptance criteria

- **AC1** A `search_symbol` for a name that exists only as `EXEC`-created DDL (a fixture file stamped
  `dynamic_sql`) returns a payload that names the dynamic-SQL coverage gap and a grep fallback — not a
  bare `no_such_symbol`.
- **AC2** `find_callers`/`find_references` returning `no_matches` on an outside-coverage subject
  carry the coverage note and a redirect; the same tools on a genuinely-absent, fully-covered subject
  return byte-identical payloads to today (no false gap) — both exhibited (R6.8).
- **AC3** Each "treat as unmeasured, not zero" hint names a concrete fallback location/action;
  greppable in the rendered payloads.
- **AC4** Deterministic and language-branch-free — a grep over the core for `language ==` finds none
  introduced by this change.
- **AC5 (value gate, referenced not blocking)** The 300 H4 continuation question — does an enriched
  dead-end earn the *next* index call rather than a grep fallback — is recorded as the measure of
  worth, run as a probe, not asserted by the unit fixtures (mirrors 312's split of fixtures from the
  real-corpus recall).

## Out of scope

- Indexing dynamic-SQL DDL as real symbols — decided against (R5.2; 296 chose the honest stamp).
- Any change aimed at the *first* call / adoption — proven ceiling (081/099/300); this ticket only
  continues a chain already begun.
- New nav tools or a payload rider outside the existing coverage-note / try_instead machinery.

## References
`code_atlas/tools/nav_result.py:165` (PATH_BASENAME hint), `:172-175` (unmeasured hint),
`code_atlas/tools/include_graph.py:91` (its only user), `code_atlas/tools/find_callers.py:564`,
`code_atlas/tools/find_references.py:469-524`, `code_atlas/tools/search_symbol.py:364`,
`code_atlas/tools/coverage.py:135-197`, `code_atlas/instructions.py:37-43`,
`code_atlas/tools/find_orphans.py:82-95`, [`docs/tasks/300_the-index-is-registered-permitted-and-never-chosen.md`](300_the-index-is-registered-permitted-and-never-chosen.md) (H4),
[065](065_empty-answer-cannot-explain-itself.md),
[093](093_try-instead-is-not-a-callable-tool-name.md),
[296](296_the-sql-adapter-names-the-dynamic-procs-and-stamps-nothing.md),
ENGINEERING_RULES R1.1, R4.2, R5.2, R5.6, R6.8.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 314 — coverage-edge zero handoff (working doc)
- **TIER:** full · **TRACK:** backend · **SCOPE:** S · **BASELINE:** green
- **Depends on:** 065, 093, 296 (done)
- **reviewer:** off · **challenger:** on
- **Branch:** `feat/314-coverage-edge-zero-handoff`
- **work_doc_mode:** embed

## Session status
- **Current phase:** finalise

## Phase 0
`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`
| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Signal for dynamic-SQL gap | Index meta `stamped_unmodelled_resolution_by_language` (296), never synthesize symbols | ticket Scope §1; R5.2; explore e21faf8f |
| 2 | Redirect shape | Hint-only Grep (PATH_BASENAME pattern); `try_instead` omitted (093) | nav_result PATH_BASENAME; Constraints 093 |
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis
`SECTIONS: 5 found (Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=5`
`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R4.2 (change-type) ✅ · R5.2 (change-type) ✅ · R5.6 (change-type) ✅ · R7.2 (change-type) ✅`
`BASELINE: green`

| ID | Source | Interpretation | Status |
|----|--------|----------------|--------|
| C1 | R5.2/R5.6 | stamp + coverage fields only | ✅ |
| C2 | R1.1 | strategy tokens, no language == | ✅ |
| C3 | 061 | no fire without stamp/gap | ✅ |
| C4 | 093 | Grep is hint, not tool | ✅ |
| R1–R4 | Scope 1–4 | helpers + wire three tools + hint rewrite | ✅ |
| G1 | deliberate handoff | AC1–AC3 | ✅ |
| AC1–AC5 | proving + AC5 probe note | ✅ | ✅ |

## AC validation
| AC | Match? | Falsifiable? |
|----|--------|--------------|
| AC1 | Y | stamped search miss greps dynamic_sql |
| AC2 | Y | gap vs covered byte-id pair |
| AC3 | Y | Grep in unmeasured hints |
| AC4 | Y | no new language == |
| AC5 | Y | recorded as probe, not fixture |

## Phase 2 — Design
**Approach:** `coverage_edge_hint` / `attach_coverage_edge_route` in nav_result; wire search_symbol / find_callers / find_references; rewrite RELATION_UNMODELLED + orphans hints.
**Rejected:** (a) per-file subject↔EXEC correlation — no store API, R5.2; (b) fake try_instead=grep tool — 093.
`HANDLES: 0 recalled | 0 traced | 0 does not apply | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
**APPROVED CHANGE LIST:**
1. `code_atlas/tools/nav_result.py` — hints + attach_coverage_edge_route
2. `code_atlas/tools/search_symbol.py` / `find_callers.py` / `find_references.py` / `find_orphans.py` — wire / hint
3. `tests/test_coverage_edge_zero_handoff.py` — proving
4. working doc / BACKLOG / TOKEN_LEDGER
**PROVING TEST:** `.venv/bin/python -m pytest tests/test_coverage_edge_zero_handoff.py -q`
**TREE_PATHS:** `code_atlas/tools/nav_result.py code_atlas/tools/search_symbol.py code_atlas/tools/find_callers.py code_atlas/tools/find_references.py code_atlas/tools/find_orphans.py tests/test_coverage_edge_zero_handoff.py docs/tasks/314_a-zero-at-a-coverage-edge-dies-silent.md docs/BACKLOG.md docs/TOKEN_LEDGER.md`
**Gate 2 status:** cleared (autorun)

## Phase 3 — Execute
Implemented. Proving green.
`PROVING TEST:` `.venv/bin/python -m pytest tests/test_coverage_edge_zero_handoff.py -q` → 6 passed.

## Phase 4 — Review
`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — round1 NOT CLEAN (ok-path Grep rider) → round2 CLEAN (agent 0d31889a). Gate 4: challenger CLEAN; reviewer waived.

## Phase 5 — Finalise
`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop`
