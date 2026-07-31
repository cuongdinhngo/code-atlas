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
- **CI:** the LLM step must never run in the per-PR gate — no API key, no network, and a non-deterministic call would make the build flaky. The enrichment layer needs a seam CI can stub, and the test asserts the deterministic graph → enrichment → presentation split holds with the middle stage faked (R4.1 keeps the LLM out of the core; this keeps it out of CI too).

## Acceptance criteria
- Overview generated for a real repo; layers are sensible; core stays deterministic (no LLM in core).
- Works for any language with an adapter (no PHP-specific logic).

## References
Plan §14, §15 (M10).
