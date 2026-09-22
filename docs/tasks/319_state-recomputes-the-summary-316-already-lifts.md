---
id: 319
slug: state-recomputes-the-summary-316-already-lifts
title: "316 put a lifted `summary` at the head of get_index_status, but the MCP server-instructions `_state()` still hand-composes its own one-line freshness sentence by reparsing the payload, so two independent ground-truth one-liners can disagree"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [316, 300]
---

## Why this exists (#422 follow-through — doc-surface sweep, not a field retro)

316 (#422) answered the field-retro batch's repeated ask — *"a one-line human summary at the top of
`get_index_status` so a routine is-it-fresh check does not reparse the payload"* — with a derived
`summary` string, single-sourced from the fields it precedes (`get_index_status.py` `_compose_summary`
/ `_with_summary`). But the **server-instructions channel builds its own one-liner the old way**:
`code_atlas/instructions.py:46-56` `_state()` reparses `status.get("indexed" / "files" / "nodes" /
"staleness")` and hand-assembles *"This repository is indexed and current: N files, M symbols."* That
is exactly the reparse pattern 316 set out to kill, now living one file over — and because the two
sentences are composed independently over the same status dict with no shared source, they can
disagree (e.g. `summary` folds edge-health `healthy` / `behind (read tools still serve)` nuance that
`_state()` does not). `_state()` is the very first sentence an anchor agent reads in its system prompt
(300), so a disagreement here is maximally visible.

## Goal

Make the server-instructions freshness sentence a single-sourced consumer of get_index_status's
`summary`, so there is one composed ground-truth one-liner, not two — or record an explicit decision
that the instruction channel needs its own terser wording and cite why.

## Scope / Deliverables

1. **`_state()` lifts `summary`** — read `status["summary"]` (316, present at every detail level incl.
   `minimal`, AC3) instead of recomposing from `indexed` / `files` / `nodes` / `staleness`. Keep the
   unbuilt-index branch's call-to-action wording that the summary already carries.
2. **One composition site** — if the instruction sentence and the payload sentence must differ in
   register, factor the shared compose into one helper both call (R6.7), rather than two hand-lists.
3. **Update `tests/test_server_instructions.py`** to assert the instruction sentence tracks the
   `summary` (mutate a staleness/count fixture → both move together), the red arm 316 gave the payload.

## Constraints

- R4.2: identical status → identical instruction text.
- 061 / 316 AC4: the structured payload and the `summary` field are unchanged — this only changes the
  consumer in `instructions.py`.
- `CA_TOOLS` may cut `get_index_status` from the surface; `_state()` still calls it directly for
  ground truth (it does today), so the summary is available regardless of the served roster.
- Comments ≤ 3 lines (R7.5).

## Acceptance criteria

- **AC1** The server-instructions freshness sentence is derived from get_index_status's `summary`, not
  a second reparse of the status dict — one composition site, greppable.
- **AC2** A test mutates a count/staleness fixture and both the payload `summary` and the instruction
  sentence change together, with no independent data path (mirrors 316 AC2).
- **AC3** The unbuilt / behind / current call-to-action wording an anchor agent acts on is preserved
  (no regression in what the first system-prompt sentence tells it to do).

## Out of scope

- The `summary` composition itself (owned by 316) and the structured payload shape.
- The `WHY` / `LOAD` / `KEEP_GOING` / `LIMITS` blocks of `instructions.py` — only `_state()` changes.

## References
`code_atlas/instructions.py:46-56` (`_state`), `:59-62` (`render`); `code_atlas/tools/get_index_status.py`
`_compose_summary` / `_with_summary`; `tests/test_server_instructions.py`;
[316](316_index-status-has-no-one-line-summary.md), [300](300_the-index-is-registered-permitted-and-never-chosen.md),
ENGINEERING_RULES R4.2 / R6.7.
