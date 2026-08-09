---
id: 065
slug: empty-answer-cannot-explain-itself
title: 'An empty answer cannot say why it is empty — three tools returned 0 for 1, 3348 and 2 real sites'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [033, 054, 056]
---

## Goal
`reason: "no_matches"` on a query the resolver **cannot link** is byte-identical to `no_matches` on a
symbol that genuinely has no references. Field round 3 hit this three times in one session, on
questions whose true answers were **1**, **3,348**, and **2** sites. Give an empty answer a channel to
say *"this relationship is not modelled"*, distinct from *"this relationship is empty"*.

## Evidence (field retro round 3, 2026-08-09, contract v5)
| Query | Payload | Truth |
|---|---|---|
| `find_references` on class `…\ServiceControllerMemberAllergies` | `results: []`, `total_count: 0`, `reason: "no_matches"` | 1 site — `config/legacy_aliases.php:509`, **the root cause of the bug being fixed** |
| `find_references` on class `\Src\System\RegionManager` | same shape | **3,348 sites across 614 files** |
| `include_graph(path, direction="imported_by")` | `results: []`, **`unresolved_includes: 0`** | 2 requirers, both via computed paths (`dirname(__DIR__, 2) . …`, `__DIR__ . '/../../…'`) |

The control proves the tools are **narrow, not broken**: `find_references` on a *method* qname
(`ModelMember::getActiveStatus`) returned 18 correct results in the same session.

Where the behaviour is already known and where it is not:
- `find_references`' docstring states it — *"Bare `IMPORTS` / `CONTAINS` / `REFERENCES` stay
  unlinkable until the resolver grows — they never appear here even though the SQL has no kind
  filter"* (`tools/find_references.py`). **The docstring carries the caveat; the payload does not.**
- `relation_reason()` (`tools/nav_result.py`) can only return `ok` / `no_such_symbol` / `no_matches` —
  it branches on `hit_total` and `symbol_indexed` and has no third input to branch on.
- `NAV_REASONS` has six values, none of which means "not modelled".
- `unresolved_includes` counts *outbound* bare/dynamic includes only —
  `_count_unresolved_imports` is called `if direction in ("imports", "both")`
  (`tools/include_graph.py:84`), so an `imported_by` query always reports `0`. The field is not
  wrong; it is **unanswerable in that direction and still prints a confident zero**.

Why this is the top item and not a nicety: the anchor repo's own `CLAUDE.md` instructs agents that
`find_references` / `impact` are *"required, not grep"* for "who calls this / what breaks if I change
it". An agent obeying that reads `total_count: 0` for `RegionManager` and concludes the project's
central region switch is dead code. The round-3 session escaped only because it routed around the
tools by instinct — it calls the loss **latent, not realised**.

## Scope / Deliverables
- **A new `reason` value for unmodelled relationships.** Add to `NAV_REASONS` something in the shape
  of `relationship_not_modelled`, emitted whenever the query kind is one the resolver cannot link —
  not guessed from an empty result, but decided from the query's own shape.
- **Say what to do instead.** The payload must carry a short, machine-stable hint (which tool or which
  name form *would* answer), not prose an agent has to parse. Keep it one field; R-061 weight rules
  still apply.
- **Decide the trigger honestly.** A class-shaped qname whose reference edges are all unlinked is
  the case in hand, but the rule must be derived from what the resolver links, not from a
  regex on the qname. If that decision cannot be made cheaply at query time, say so and record the
  cheaper approximation chosen.
- **`include_graph` must stop asserting completeness it cannot claim.** Either report inbound
  unresolved edges (an `unresolved_inbound` counter alongside `unresolved_includes`), or omit the
  field entirely for `imported_by` — a printed `0` that is structurally always `0` is worse than
  absent.
- **Every nav tool, not just these two.** Whatever channel is added must be emitted consistently by
  `find_references`, `include_graph`, `impact`, `reachable_from`, `explain_path` and
  `find_implementations`, or the next session learns to trust the wrong subset.

## Constraints
- R1.1 — no language branch; "which kinds does the resolver link" is contract vocabulary, not PHP.
- R3 — if the reason vocabulary is part of the contract surface, the version bump and
  `tests/contract/` update travel in the same change.
- R4 — deterministic: same index + same query ⇒ same reason, every time.
- 061 — do not reintroduce payload weight; this is one field, present only when it means something.
- Do **not** fix the underlying resolver gap here. This ticket makes the gap *legible*; linking
  class-level references is a separate, larger piece of work.

## Acceptance criteria
- `find_references` on a class qname whose reference edges are unlinked returns a reason distinguishable
  from a genuine zero, with a hint naming a route that does work.
- `find_references` on a method qname with real callers is unchanged (the 18-result control still
  returns `reason: "ok"` and 18 rows).
- A symbol that genuinely has zero references still reports the plain empty reason — the new value
  must not swallow the honest case.
- `include_graph(direction="imported_by")` no longer emits a field that is always `0`; whichever way
  it is resolved, a file with unresolvable inbound includes is distinguishable from one with none.
- A conformance test pins each reason value to a query shape, so the vocabulary cannot drift.

## References
Field retro round 3 §3, §4, §9 (`today-i-learned/ai/code-atlas/Retros/2026-08-09_…round3.md` — the
retro is outside this repo; the counts above are the artifact). `code_atlas/tools/nav_result.py`
(`NAV_REASONS`, `relation_reason`); `code_atlas/tools/find_references.py` (docstring carries the
caveat); `code_atlas/tools/include_graph.py:84,111` (`_count_unresolved_imports`, outbound only).
Related: [054](054_bare-name-callers-silent-drop.md) (a silent drop with a count that lied),
[056](056_filter-values-fail-loud.md) (an empty result standing in for an error),
[033](033_nav-reason-codes.md) (the `reason` field this extends).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 065 — empty-answer-cannot-explain-itself (working doc)

- **Ticket:** 065 · local `docs/tasks/065_empty-answer-cannot-explain-itself.md`
- **Type:** bug / agent-trust
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N UI
- **TIER:** full (review skipped per user instruction this run)
- **BASELINE:** green — `995 passed` on untouched checkout before edits
- **work_doc_mode:** embed
- **working-doc path:** this file below separator

## Phase 0 — Refine

`REFINE: 7 unresolved surfaced | 4 want asked | 5 how resolved+cited | 3 ASSUMED (exposure) | skip: no`
`INPUT KIND: ticket`

**Settled wants** (user: “best option + pass all gates”; recommended options ratified):

| # | Want | Chosen | Becomes AC constraint |
|---|------|--------|------------------------|
| W1 | inbound includes honesty | Omit `unresolved_includes` for `imported_by` | AC4 |
| W2 | where vocabulary is pinned | Unit/nav tests + contract subset pin; **no** `contract_version` bump | AC5 |
| W3 | alternate route for class refs | `try_instead=find_references_on_method_qname` | AC1 |
| W4 | review | Skip Phase 4 this run | process |

**HOW (cited):**

| # | HOW | Resolution | Citation |
|---|-----|------------|----------|
| H1 | reason string | `relationship_not_modelled` | ticket Scope |
| H2 | trigger | unlinked evidence of kinds resolver does not link | ticket + `resolver.py` + `FQN_EDGE_KINDS` |
| H3 | no resolver fix | legibility only | ticket Constraints |
| H4 | one companion field | `try_instead` (061 omit-when-empty) | ticket + 054 pattern |
| H5 | tool consistency | emit when query is unmodelled; modelled tools keep genuine zeros | ticket Scope + exposure |

**ASSUMED (ratified by blanket approval):**

| # | Choice | Why |
|---|--------|-----|
| A1 | empty `imported_by` → new reason only when basename unlinked evidence > 0 | allows genuine zero |
| A2 | impact / reachable_from / explain_path / find_implementations: shared vocab; no false emit (their kinds are linked) | H5 applicability |
| A3 | empty-only (not partial non-empty) | ticket goal + 061 |

**Exposure-checker:** [challenger](902618aa-115c-43d2-8cfc-0ba43d735c63) — surfaced A1–A3; folded above.

## Requirements matrix

`SECTIONS: 5 found (Goal, Evidence, Scope, Constraints, Acceptance) | 5 decomposed | ROWS: C=5 R=5 G=1 AC=5`

| ID | Source | Verbatim (short) | Interpretation | Ph1 | Ph2 | Ph3/4 | Status |
|----|--------|------------------|----------------|-----|-----|-------|--------|
| G1 | Goal | empty must say unmodelled vs empty | new reason + hint | nav_result/tools | CL1–3 | tests | ✅ |
| R1 | Scope | new reason value | `relationship_not_modelled` in NAV_REASONS | | CL1 | vocab test | ✅ |
| R2 | Scope | machine-stable hint field | `try_instead` | | CL1–3 | proving tests | ✅ |
| R3 | Scope | trigger from resolver linkability | unlinked REFERENCES/IMPORTS count | | CL2 | store+refs | ✅ |
| R4 | Scope | include_graph inbound honesty | omit field; basename proxy | | CL3 | include tests | ✅ |
| R5 | Scope | every listed nav tool | shared vocab; emit only when applicable | | CL4 | docs+impl tests | ✅ |
| C1 | Constraints | R1.1 | no language branch | | | sole-source ok | ✅ |
| C2 | Constraints | R3 conditional | subset in contract; no version bump | | | schema pin | ✅ |
| C3 | Constraints | R4 deterministic | same SQL evidence | | | | ✅ |
| C4 | Constraints | 061 one field | try_instead only when set | | | | ✅ |
| C5 | Constraints | do not fix resolver | no resolver.py link change | | | | ✅ |
| AC1 | AC | class unlinked ≠ no_matches + hint | | | | proving test | ✅ |
| AC2 | AC | method control ok | | | | proving test | ✅ |
| AC3 | AC | genuine zero stays no_matches | | | | proving test | ✅ |
| AC4 | AC | imported_by no always-0; distinguishable | | | | proving test | ✅ |
| AC5 | AC | pin reason↔query shape | | | | unit+contract | ✅ |

## AC validation

| AC | Match | Falsifiable |
|----|-------|-------------|
| AC1–5 | Y | pytest asserts on reason / field presence |

`CLARIFICATION: 0 raised | 0 for human | j=0`

## Inventory (universal “every nav tool”)

`N=6` — find_references, include_graph, impact, reachable_from, explain_path, find_implementations

| # | Tool | Emission this ticket |
|---|------|----------------------|
| 1 | find_references | yes — primary |
| 2 | include_graph | yes — imported_by |
| 3 | find_implementations | vocab only — IMPL modelled |
| 4 | impact | vocab/doc — IMPACT modelled |
| 5 | reachable_from | vocab/doc — IMPACT modelled |
| 6 | explain_path | vocab/doc — IMPACT modelled |

## Cause / gap

`validation` / presentation: `relation_reason` had no unmodelled branch (`nav_result.py`); `include_graph` forced `unresolved_includes=0` for inbound (`include_graph.py`).

`RULE SECTIONS: §1 ✅ · §2 N/A (no adapter) · §3 ✅ (subset only, no vocab bump) · §4 ✅ · §5 N/A · §6 N/A · §7 ✅ docs`

`TRACK: backend` · `SCOPE: M` · `TIER: full`

**Gate 1:** cleared by user blanket ratification.

## Phase 2 — Design

**Approach:** Add `relationship_not_modelled` + `try_instead`. On `find_references`, when `relation_reason` would be `no_matches` and unlinked REFERENCES/IMPORTS match qname/name, upgrade reason + hint. On `include_graph(imported_by)`, omit `unresolved_includes`; if empty and `count_unlinked_includes_mentioning(basename)>0`, emit new reason + `path_basename_search`. Put `UNMODELLED_REFERENCE_KINDS` in `contract.py` (like CALLER_KINDS). No resolver link changes.

**Rejected:** Always mark empty class refs unmodelled without unlinked evidence (swallows genuine zeros). Add `unresolved_inbound` counter (cannot be exact per-path). Contract version bump for tools-only reason vocab (033/054 precedent).

**Assumptions:** basename `instr` proxy for inbound includes is approximate — `verified` as documented cheaper approximation; proving test pins behaviour.

### Change-list

| # | Change | Area | Ph2 | k/N |
|---|--------|------|-----|-----|
| 1 | NAV_REASONS + try_instead helpers | `nav_result.py` | R1 R2 | 2/2 |
| 2 | UNMODELLED_REFERENCE_KINDS | `contract.py` | R3 C2 | 1/1 |
| 3 | count_unlinked_* store helpers | `store.py` | R3 R4 | 2/2 |
| 4 | find_references emission | `find_references.py` | AC1–3 | 3/3 |
| 5 | include_graph omit + emission | `include_graph.py` | AC4 R4 | 2/2 |
| 6 | docstrings on modelled tools | impact/reachable/explain/impl | R5 | 4/4 |
| 7 | proving + vocab + contract pin tests | `tests/` | AC5 | 1/1 |
| 8 | PLAN + BACKLOG + task status | docs | C docs | 1/1 |

**Proving test:** `tests/test_empty_answer_cannot_explain_itself.py` — `.venv/bin/pytest tests/test_empty_answer_cannot_explain_itself.py`

**Verification plan:** all ACs logic/integration via unit tests — layer-match ✅

**Gate 2:** cleared by user blanket ratification.

## Phase 3 — Execute

- Branch: `feat/065-empty-answer-cannot-explain-itself`
- Implemented as approved; Axis-1 diff ⊆ list; Axis-2 all bullets `implemented-as-approved`
- Suite: **1001+ passed** (incl. new tests); baseline was 995 green
- Review: **skipped** per W4

## Phase 4 — Review

`SKIPPED` per user instruction (`/solve 065 with skipped review`). No `Reviewed at` marker.

## Phase 5 — Finalise

Pending outward-action approvals.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | explore (nav scan) | 0 | unmeasured (blocking retrieval) |
| refine | exposure-checker challenger | 0 | unmeasured (blocking retrieval) |

`DISPATCHES: 2 | ROWS: 2 | complete`

## Session status

- Phase: finalise (review skipped)
- Waiting: per-action approval for push / PR
- Next: user approves outward actions

## Durable lesson

Inbound unresolved includes cannot be counted by `target_qname` (it is empty). A confident zero on `imported_by` is always a lie; omit the field and use a documented basename approximation only when emitting `relationship_not_modelled`.
