---
id: 269
slug: twelve-graph-nouns-where-a-reader-has-seven-questions
title: 'Every heading in `overview.md` is a noun from the graph and none is a question a reader has — "Start here" is the tenth of twelve, after nine sections of census — so a complete, correct artifact reads as a meaningless list and loses to asking a model; make the headings the questions, answer before you tabulate, and never render an empty table'
phase: 3
milestone: Onboarding
status: done
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

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 269 — question-shaped overview (working doc)

- **SCOPE:** M · **TRACK:** onboarding · **TIER:** full · **BASELINE:** green · **INPUT KIND:** ticket
- **work_doc_mode:** embed
- **Current phase:** execute

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

HOW self-resolved: (1) demote census headings to `###` under Appendix — ticket "relocation only" + question-first AC; (2) Q2/Q5/Q6/Q7 always emit (not audience-gated) so the seven questions stay the overview shape; audience still gates orientation/modules/appendix census; (3) R4.2 byte-identity measured once a prior manifest exists (Q6 is intentionally run-stateful).

## Requirements matrix

`SECTIONS: 4 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria) | 4 decomposed | ROWS: C=4 R=7 G=1 AC=5`

| ID | Source | Verbatim | Ph2 | Status |
|----|--------|----------|-----|--------|
| G1 | Goal | headings are questions; answer before table; never empty | D1 | ✅ |
| C1 | 121 | no reading-order syllabus — doors only | D1 | ✅ |
| C2 | R4 | no LLM in core | D1 | ✅ |
| C3 | PLAN §1 | no second pipeline | D1 | ✅ |
| C4 | scope | relocation only — no section deletion | D1 | ✅ |
| R1 | Q1 | 60-second summary + layer mermaid | D1 | ✅ |
| R2 | Q2 | landmines + action column | D1 | ✅ |
| R3 | Q3 | doors / CA_ENTRY_POINTS | D1 | ✅ |
| R4 | Q4 | capability table (263) | D1 | ✅ |
| R5 | Q5 | spine hubs + test-bootstrap warn | D1 | ✅ |
| R6 | Q6 | architecture_diff wiring | D1 | ✅ |
| R7 | Q7 | HEURISTIC / Uncategorised / unmodelled | D1 | ✅ |
| AC1 | seven questions in order | proving | D1 | ✅ |
| AC2 | never empty / refusal names reason | proving | D1 | ✅ |
| AC3 | DiffRefusal first run; real diff later | proving | D1 | ✅ |
| AC4 | appendix keeps existing tests | proving | D1 | ✅ |
| AC5 | field check | maintainer on PR | — | ⏳ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision` → `j = 0`

## Phase 1 — Analysis

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R4 (change-type) ✅ · R4.2 (change-type) ✅ · R1.1 (change-type) ✅ · R7.2 (change-type) ✅`

`BASELINE: green` — onboarding suite subset green before edit.

## Phase 2 — Design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
Proving test: `tests/test_question_shaped_overview.py`
Change list: `code_atlas/onboarding/artifact.py` · `code_atlas/tools/generate_onboarding.py` · proving + audience/orientation/provenance/community/generate_onboarding test updates · docs (BACKLOG/TOKEN_LEDGER/task).

## Phase 3 — Execute

Implemented question headings, appendix demotion, arch_diff wiring via prior manifest, never-empty mirrors/orientation/landmines/spine/trust. Challenger round-1 NOT CLEAN → enrich overview from dataset (hubs/headlines/confidence/263 capability map) + landmine answer-before-table + Uncategorised segment worklist.

## Phase 4 — Review

`reviewer: off` · `challenger: on` — round-1/2 NOT CLEAN → fix → round-3 CLEAN.

## Phase 5 — Finalise

PR [#429](https://github.com/cuongdinhngo/code-atlas/pull/429); GATE GREEN.
