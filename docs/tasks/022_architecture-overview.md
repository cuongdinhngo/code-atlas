---
id: 022
slug: architecture-overview
title: Onboarding — architecture overview + layers (M10)
phase: 3
milestone: M10
status: todo
depends_on: [014]
---

## Goal
Phase-2 onboarding as a graph consumer: architectural layers + overview (§14).

## Scope / Deliverables
- Heuristic layering by namespace/directory, refined with an LLM (LLM confined to this layer).
- Per-module/symbol plain-English summaries + tags.
- `architecture_overview` tool; write enriched artifact to `.code-atlas/onboarding/`.

## Acceptance criteria
- Overview generated for a real repo; layers are sensible; core stays deterministic (no LLM in core).
- Works for any language with an adapter (no PHP-specific logic).

## References
Plan §14, §15 (M10).
