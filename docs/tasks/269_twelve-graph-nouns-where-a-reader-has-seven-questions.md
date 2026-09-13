---
id: 269
slug: twelve-graph-nouns-where-a-reader-has-seven-questions
title: 'Every heading in `overview.md` is a noun from the graph and none is a question a reader has — "Start here" is the tenth of twelve, after nine sections of census — so a complete, correct artifact reads as a meaningless list and loses to asking a model; make the headings the questions, answer before you tabulate, and never render an empty table'
phase: 3
milestone: Onboarding
status: todo
depends_on: [263, 121, 210, 139]
---

## Why this exists

The shipped artifact's headings, in order (`onboarding/artifact.py:74–88`):

```
Summary · Mirror subtrees · Business modules · Zero-inbound modules, by population ·
Layers · Layer graph · Entity relationships · Cross-layer edges ·
Community / layer disagreement · Start here · How this was written · Who this was written for
```

Twelve headings, **not one of them a question**. The only one resembling a reader's question is **tenth of twelve**. On `symfony/demo` the largest layer is `Uncategorised` (18/51): complete, correct, low-information.

This is a content-structure defect, not a renderer defect. The maintainer's verdict, 2026-09-12: *"như 1 list các class không có ý nghĩa, nếu là tôi thì tôi đi hỏi AI cho nhanh."* A static artifact cannot win a race against an interactive model **in that shape** — and it does not have to: it holds facts a model cannot produce by reading code, namely whole-graph counts and a diff between two snapshots.

## Scope / Deliverables

**Headings are questions. The answer precedes the table. No section renders empty.**

| # | Heading | Source |
|---|---|---|
| 1 | What is this repo — 60 seconds | 5 figures + one layer mermaid |
| 2 | **Where will I step on a landmine?** | `headlines.py`'s six families, **plus an action column** |
| 3 | Where do I start reading? | entry points / `CA_ENTRY_POINTS` — **doors, not a reading order** |
| 4 | **I was told to change X — which file?** | [263](263_the-question-a-newcomer-asks-most-is-the-one-table-that-is-empty.md) |
| 5 | What is the spine of this repo? | hubs + fan-in, each with *why*, and a warning when a hub is test bootstrap |
| 6 | **What changed architecturally since the last generate?** | two manifests via `architecture_diff` |
| 7 | What should I not trust here? | HEURISTIC share, `Uncategorised`, what is unmodelled |

- **Never-empty rule, everywhere.** No mirrors ⇒ *"single-tree repo, normal"*. `entry_points` unset ⇒ candidate globs with `files_matched`. `Uncategorised` the mode ⇒ a **vocabulary worklist** of unmatched path segments, not a fake layer.
- **Section 6 is wiring, not a new engine.** `onboarding/architecture_diff.py` already loads an onboarding manifest into a comparable snapshot (`:112`), is already a pure two-dataset function, and already renders markdown (`:159`); `DiffRefusal` already satisfies never-empty ("no previous generate"). This is the supervision half of Pillar 2 (PLAN §1), which the artifact has never carried.
- **Everything else is kept and moved to an appendix** — mirrors, matrix, crossings, ER, community, provenance, audience. They are correct; they are not the first screen. Their tests stay green.
- **The same file is the model's grounding.** Question-shaped headings, a size ceiling, provenance on every figure — so "ask the AI" returns something true rather than invented.

## Constraints

- **No reading order / syllabus** — [121](121_onboarding-question-class-never-measured.md) measured it wrong and binds. Section 3 lists doors; it does not sequence them.
- **No LLM in the core** (R4/R4.1): prose is a template over already-derived figures; the LLM seam stays opt-in and outside `code_atlas/`.
- **No second pipeline** (PLAN §1) and no page-per-module revival (205).
- No deletion of existing sections — relocation only.

## Acceptance criteria

- `overview.md` renders the seven questions in order, each answered before any table.
- A property test: no section can emit an empty table or silent omission; the refusal text names the reason and what to set.
- Section 6 renders a real diff against a previously committed manifest, and `DiffRefusal` prose on the first run.
- Appendix sections keep their existing tests.
- **Field check on a repo the maintainer works in, not a fixture:** a stranger names one landmine within 60 seconds and answers "which file for X" within 5 minutes — or states why the graph cannot answer and what to configure.

## References
`code_atlas/onboarding/artifact.py:74–88`, `code_atlas/onboarding/headlines.py`, `code_atlas/onboarding/architecture_diff.py:112,159`, [263](263_the-question-a-newcomer-asks-most-is-the-one-table-that-is-empty.md), [121](121_onboarding-question-class-never-measured.md), [210](210_the-artifact-has-one-shape-for-every-reader.md), PLAN §1.
