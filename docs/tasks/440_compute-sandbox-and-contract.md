---
id: 440
slug: compute-sandbox-and-contract
title: "`compute`: exact answers over the whole graph — private views, sandbox, template contract, evidence levels"
phase: 2
milestone: "0.11 Verify & Compute"
status: todo
depends_on: [428, 434]
---

## Why this exists

Roadmap R3 (0.11). A model cannot count, group or prove an absence over a codebase from inside its
context window. On the anchor (survey 2026-11-07), **8 of 10 aggregate questions** were unanswerable
or costly through the current tools — "procedures with no PHP referrer" cost ~230k tokens by
navigation against ~25 computed. A prototype over the anchor's 1.49 GB index answered in 0.01–2.05 s
warm and refused 6 of 6 safety probes. Absences need care: PHP → SQL linkage there is **0%
RESOLVED**, so "nothing references X" is often "nothing *resolved* references X".

## Scope

1. **Private view layer** (`v_file`, `v_symbol`, `v_edge`) used only by templates — not a public API,
   free to change. It lives in `store.py`, the only file that touches SQLite (R1.4).
2. **Sandbox**, as prototyped: `mode=ro` + `PRAGMA query_only`, an authorizer allowing
   SELECT / READ / FUNCTION only, a progress-handler deadline (3 s default), a row cap (200 default).
   **Callers never supply SQL** — only a template id and typed params.
3. **Template contract:** `id`, a one-line question, typed parameters as a closed schema (428), an SQL
   body over the views, a **data-driven `caveat`** (e.g. the share of rows backed by HEURISTIC or
   unlinked evidence), `total_count`, `truncated`, and an explained-empty `reason`.
4. **Evidence levels for absence questions (mandatory):** `no_edge_no_mention` (no edge and the name
   appears nowhere in indexed text — a strong candidate) vs `no_edge_but_mentioned` (no edge, but the
   name appears in literals or other files — **unknown, never dead**, R5.6). The mention check reuses
   the FTS index or a time-capped bounded grep, counted in the payload.
5. **Surfaces:** MCP tool `compute` (`template`, `params`, `limit`; no template lists the catalogue:
   ids and questions) and `code-atlas query compute --args '{…}'`. Read-only annotations; description
   within 434's budget; the pinned tool count moves.
6. One proving template ships here (e.g. `tier_mix`) so the contract is exercised end to end; the
   catalogue is 441. Overlap with `find_orphans` is stated in the tool description, not duplicated.

## Acceptance

1. Safety: a write, `ATTACH`, `load_extension` and a runaway recursive CTE are each refused or
   interrupted, with a reason — never a partial answer presented as complete.
2. An unknown template or an extra param fails loud through the closed schema.
3. Every computed row carries a tier or caveat; an empty result names why it is empty.
4. The absence split is asserted on a fixture where one target has a string mention and one has none.
