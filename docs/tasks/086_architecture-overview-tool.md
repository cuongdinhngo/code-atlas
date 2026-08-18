---
id: 086
slug: architecture-overview-tool
title: Onboarding — architecture_overview tool (M10)
phase: 3
milestone: M10
status: todo
depends_on: [084, 085, 104]
---

> **Gated on [104].** This is the first consumer of `assign_layers`. 103 (PR #122) shipped a layer
> heuristic that collapses real multi-root repos into one layer (retro F1); 104 fixes it with the
> dominant-subtree signal. Do **not** surface layers through this tool until 104 has landed — that is
> why 104 is a hard dependency, not just 084/085.

## Goal
Expose the deterministic layers + metrics as an agent-facing MCP tool — the first onboarding tool.

## Scope / Deliverables
- New `code_atlas/tools/architecture_overview.py`: JSON layers + module list + per-module metrics +
  summary + cross-layer edges. Reads 083/084/085; writes nothing (read-only).
- Follows the established payload conventions: `index_root` (071), reason codes + `total_count`
  (033/065), `detail_level` (061).

## Acceptance criteria
- Overview generated for a real repo; layers are sensible; core stays deterministic (no LLM in core).
- Works for any language with an adapter (no PHP-specific logic).
- Tool test over a fixture repo asserts the payload shape and a known layer split.

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §4 (M10);
PLAN §14, §15 (M10).
