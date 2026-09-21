---
id: 314
slug: a-zero-at-a-coverage-edge-dies-silent
title: "A tool that returns zero at a coverage edge attaches no try_instead and names no grep target, so the code-atlas chain ends on a bare no_matches and the session falls back to a grep it never returns from"
phase: 1.5b
milestone: Agent-trust
status: todo
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
