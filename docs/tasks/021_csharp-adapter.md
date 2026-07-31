---
id: 021
slug: csharp-adapter
title: C#/.NET adapter (M9)
phase: 2
milestone: M9
status: todo
depends_on: [019]
---

## Goal
Fourth adapter — confirms the contract for a second namespaced + semantic-model language (§3, §15).

## Scope / Deliverables
- `adapters/csharp/`: .NET sidecar over Roslyn; full semantic model → precise type/call/ref edges.
- Map `Namespace.Type.Member` onto the shared qname shape; advertise `semantic_types` → pre-resolved edges.
- Document .NET SDK runtime requirement.
- **CI:** add `actions/setup-dotnet` and a restore/build step for `adapters/csharp/`, with the lockfile committed (R8.3). This is the heaviest runtime of the four — likely the point where the adapter jobs must split from the core job so a Python-only change does not pay for a .NET SDK install.

## Acceptance criteria
- Passes `tests/contract/` with C# fixtures; core unchanged.
- Semantic-model edges arrive `RESOLVED`; resolver honors them without special-casing.

## References
Plan §3, §8.2, §15 (M9).
