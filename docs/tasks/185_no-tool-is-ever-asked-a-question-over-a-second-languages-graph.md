---
id: 185
slug: no-tool-is-ever-asked-a-question-over-a-second-languages-graph
title: 'The multi-language claim stops at the adapter boundary — 147 made conformance a per-adapter matrix, but no test asks any of the 22 tools a question over a second language''s graph'
phase: 1.5b
milestone: Coverage
status: todo
depends_on: [147, 012, 019]
---

## Why this exists

code-atlas is a multi-language server whose anchor repo happens to be PHP. The PHP repo is the
**test subject**, not the product. Everything that proves the product is language-agnostic stops one
layer short of the surface an agent actually calls:

| Layer | Proven for two languages? | By what |
|---|---|---|
| Adapter output | **yes** | `tests/contract/test_adapter_conformance.py` — a per-adapter matrix (147), `REGISTRY` holds PHP + TS, cases are data in `adapter_registry.py`, empty registry FAILS (R6.5) |
| Indexer + store | **yes, for TS** | `test_ts_import_resolution.py` / `test_ts_semantic_types.py` run `full_build` + `GraphStore` |
| **The 22 tools** | **no** | no test in `tests/` imports `code_atlas.tools` and asks anything over a TS-indexed graph |

Swept all 140 files in `tests/`: the only ones that build a TS graph are the two above, and neither
imports a tool. `test_class_diagram.py:179` mentions `"typescript"` solely as an R2.2 denylist
string. So **"22 tools × every language" is tested for PHP and *asserted* for TypeScript** — the
strongest sentence the repo can honestly say today is *"the adapter conforms"*.

## What that gap already costs, concretely

Three tools are gated on vocabulary a given adapter may never emit, and nothing pins what they
should do about it:

| Tool | Gated on | PHP | TS/JS |
|---|---|---|---|
| `include_graph` | `INCLUDES` (`include_graph.py:28`) | emits it | **never emits it** — TS uses `IMPORTS` |
| `find_references` | `UNMODELLED_REFERENCE_KINDS` = `REFERENCES` + `IMPORTS` | both | `IMPORTS` only |
| `find_view_data` | `PROVIDES_VIEW_DATA` | config-driven for every language (`enrichment.py:186`), so empty by default for **all** of them |

`class_diagram` / `find_implementations` lose `USES_TRAIT` for TS, which is **correct** — TypeScript
has no traits. That is exactly why the matrix needs three states and not two: *answers*, *empty
because the relation is not modelled for this language*, and *not applicable by language design*.
Today all three collapse into the same empty payload, and no test can tell them apart.

**This is the ticket that makes adapter #3 and #4 safe to add.** 184's tier 1a emits only `Function`
and `CALLS`, so it is the most extreme column this matrix will ever hold — roughly half the surface
declaring an empty. Landing 184 without this matrix ships ~10 tools' worth of confident zeros over
378,790 lines and calls it coverage.

## Scope

1. A **cross-language tool-parity matrix**, one layer above 147's and built the same way: the
   expectations are **data**, adding a language is a row of declarations, and the test body is never
   edited (147 AC2 is the precedent to copy).
2. For each registered adapter × each of `main.py`'s `TOOL_NAMES`, a declared expected state from a
   closed set — at minimum `answers` · `empty_relation_not_modelled` · `not_applicable_by_language`.
   Design fixes the vocabulary and records why each state is distinguishable from the others **in the
   payload**, not only in the test.
3. **Guard-the-guard, the same way 147 did it.** An `(adapter, tool)` pair with no declaration
   FAILS; an empty matrix FAILS. A new adapter must not be able to land with an undeclared surface.
4. Design records the **fixture strategy**: whether one small per-language fixture repo can drive all
   22 tools, or whether some tools (`architecture_overview`, `guided_tour`, `generate_onboarding`)
   need a shaped fixture, and what the suite costs per run.

### Explicitly not in scope

- **Fixing** any of the three gaps above. This ticket makes the state declared and checked;
  [186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) owns turning a
  declared `empty_relation_not_modelled` into an honest payload.
- Adding an adapter, or `.sql`/Python/C# fixtures. The matrix must accept a new column; filling one
  is that adapter's ticket.
- Per-language output *quality* (ranking, resolution rate). 183 owns the measurement.
- Asserting identical payloads across languages. Parity is **the declared state matching**, never
  byte equality — two languages legitimately answer differently.

## Constraints

- **R1.1** — the matrix is data keyed by the adapter's own handshake language string. A test may name
  a language (tests are not the core); the **core** must gain no branch from this work.
- **R2 / R2.2** — fixtures encode each language's spec, never a repo's names. No anchor-repo shapes.
- **R6.5** — an unrunnable column is `skipped`, and `0 skipped` is the evidence it ran; a matrix that
  silently skips TS reads as green while proving nothing. Use the `availability` marks
  `adapter_registry.py` already carries.
- **R6.7** — one definition site for the state vocabulary, shared with 186 if 186 needs it at runtime.
- **Cost** — 22 tools × n adapters is the whole suite's shape; design states the per-run cost and
  whether any tool is declared-only rather than executed, and why.

## Acceptance criteria

1. The matrix exists as data, covers `TOOL_NAMES` × `REGISTRY`, and **fails today** for at least the
   three gated tools above (`include_graph`, `find_references`, `find_view_data` on TS).
2. An undeclared `(adapter, tool)` pair fails; an empty matrix fails — both made to fail, pinned.
3. Adding a hypothetical adapter is a data row plus fixtures, with no edit to the test body — pinned
   the way 147 AC2 is.
4. A tool that legitimately differs by language (`USES_TRAIT` on TS) is declared
   `not_applicable_by_language` and is **not** a failure.
5. TS columns run for real; `0 skipped` on a host with Node, `skipped` (never green) without it.
6. No new language branch under `code_atlas/` — R1.1 grep-gate stays green.
7. The suite's added wall-clock is measured and recorded in the working doc.

## References

`tests/contract/test_adapter_conformance.py` + `tests/contract/adapter_registry.py` (`REGISTRY`,
`AdapterConformance`, `availability`) — the pattern this ticket lifts one layer, from 147/012.
`code_atlas/main.py:47` (`TOOL_NAMES`, 22 tools). `code_atlas/tools/include_graph.py:28,76`;
`code_atlas/contract.py:78` (`UNMODELLED_REFERENCE_KINDS`); `code_atlas/enrichment.py:186`
(`PROVIDES_VIEW_DATA` is config-driven, not adapter-emitted). AGENTS.md's roll-out order
(PHP → TS/JS → Python → C#/.NET) and PLAN §18.2. Related:
[147](147_contract-harness-is-php-shaped.md) (the per-adapter matrix),
[019](019_typescript-adapter.md) (adapter #2),
[183](183_edge-health-has-no-per-language-breakdown.md) (the per-language measurement),
[184](184_tsql-source-adapter-tier-1a.md) (the column that most needs this to exist first).
