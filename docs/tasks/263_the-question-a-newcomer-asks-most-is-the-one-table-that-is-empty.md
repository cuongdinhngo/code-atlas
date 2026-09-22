---
id: 263
slug: the-question-a-newcomer-asks-most-is-the-one-table-that-is-empty
title: '"I was told to change screen X — which file?" is the question the onboarding artifact exists to answer, and it is the one table that renders empty on an ordinary repo: modules are found by structural fan-out, which scores zero on all three pinned samples, so the artifact answers every question except the one that was asked'
phase: 3
milestone: Onboarding
status: done
depends_on: [114, 210]
---

## Why this exists

[114](114_business-module-table.md) finds business modules by structural fan-out and refuses to guess from directory names (correctly — R2.2). On the three pinned samples the structural module count is **zero**, and a role-organised `src` was refused outright. So the capability table — the artifact's answer to *"which file do I open"* — is empty on exactly the repos a human has.

The maintainer's own verdict on the shipped artifact, 2026-09-12: *"hiện tại như 1 list các class không có ý nghĩa, nếu là tôi thì tôi đi hỏi AI cho nhanh chứ xem Onboarding càng loạn thêm."* An artifact that cannot answer the most-asked question loses to asking a model, and deserves to.

Widening the heuristic to manufacture groups is forbidden (R2.2, and 114 settled it). The answer is to stop requiring that the *graph* invent the vocabulary.

## Scope / Deliverables

Three sources, tried in order, each stated in the output so a reader knows which answered:

1. **Names a human wrote** — `docs/onboarding/capabilities.toml` in the indexed repo: the human writes `billing`, `login`, `checkout`; the graph fills files and entries via `trace_capability` / entry seeds. **The name is the repo's, the paths are the index's** — no sample enters an adapter, so R2.2 holds.
2. **Entry list from the graph** — where no toml exists: every HTTP-layer entry (or `CA_ENTRY_POINTS` match) is one row, with its 1-hop outbound. A "screen" is an entry; a 200-file repo is served without any module concept.
3. **Structural modules** — unchanged, for trees that genuinely fan out. Empty ⇒ **do not draw the table**; fall through to (2).

- **Never-empty rule applies to this ticket immediately**, not to a later one: when all three are empty the section states *why* and *what to set*, with candidate globs and their `files_matched` — never silence and never an empty table.

## Constraints

- **No guessing business meaning from directory names** (R2.2, 114). Source (1) is a human-authored file in the consumer repo, read as data.
- No LLM (R4): naming comes from the human or from the graph, never from prose generation.
- No second pipeline (PLAN §1): all three sources read the same graph/dataset the artifact already derives.
- Does not depend on and must not wait for the overview restructure ([269](269_twelve-graph-nouns-where-a-reader-has-seven-questions.md)).

## Acceptance criteria

- On a pinned sample with no toml and no structural modules, the capability section renders **entry rows**, not an empty table.
- On a fixture with `capabilities.toml`, rows carry the human's names with graph-derived paths, and the payload names source (1) as the decider.
- With all three empty, the section states the reason and lists candidate globs with `files_matched`; a test pins that no empty table and no silent omission can be emitted.
- A test pins that no directory-name-to-business-meaning inference was introduced.

## References
[114](114_business-module-table.md), [210](210_the-artifact-has-one-shape-for-every-reader.md), `code_atlas/onboarding/modules.py`, `docs/PLAN.md` §1, maintainer verdict 2026-09-12.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 263 — capability table never empty (working doc)

- **SCOPE:** M · **TRACK:** backend · **TIER:** full · **BASELINE:** green · **INPUT KIND:** ticket
- **work_doc_mode:** embed
- **Current phase:** finalise

## Phase 0 — Refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

## Requirements matrix

`SECTIONS: 4 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria) | 4 decomposed | ROWS: C=4 R=3 G=1 AC=4`

| ID | Source | Verbatim | Ph2 | Status |
|----|--------|----------|-----|--------|
| G1 | Goal | never-empty capability answer | D1 | ✅ |
| C1 | R2.2 | no dir-name business meaning | D1 | ✅ |
| C2 | R4 | no LLM | D1 | ✅ |
| C3 | PLAN §1 | same graph | D1 | ✅ |
| C4 | independent of 269 | no wait | — | ✅ |
| R1 | toml source | capabilities.toml | D1 | ✅ |
| R2 | entry rows | CA_ENTRY_POINTS | D1 | ✅ |
| R3 | structural + empty explain | 114 + nominations | D1 | ✅ |
| AC1 | entry rows on sample | proving | D1 | ✅ |
| AC2 | toml names + source | proving | D1 | ✅ |
| AC3 | empty explained | proving | D1 | ✅ |
| AC4 | no dir inference | proving | D1 | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R2.2 (change-type) ✅ · R4 (change-type) ✅ · R7.2 (change-type) ✅`

Ran at 3439e175bfa3580a9c07d3b316df6407c86db7e8

```
$ .venv/bin/python -m pytest tests/test_business_modules.py -q --tb=no
...................                                                      [100%]
19 passed in 0.05s
```

`BASELINE: green`

## Phase 2 — Design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_capability_table_never_empty.py -q`

| # | Change | File |
|---|--------|------|
| D1 | resolve_capability_map | capabilities.py · modules.py · dataset.py · artifact.py · generate_onboarding.py |
| D2 | proving + DATASET_VERSION 16 | tests/… |

## Phase 3 — Execute

**Branch:** feat/263-capability-table-never-empty

Ran at 3439e175bfa3580a9c07d3b316df6407c86db7e8

```
$ .venv/bin/python -m pytest tests/test_capability_table_never_empty.py -q --tb=no
.....                                                                    [100%]
5 passed in 1.24s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — round-1 NOT CLEAN → fix → round-2 CLEAN (13 met)
agent dd41325b-98b5-41c9-a252-a9e4c128be57

`REVIEW: CLEAN`
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`

Ran at 3439e175bfa3580a9c07d3b316df6407c86db7e8

```
$ .venv/bin/python -m pytest tests/test_capability_table_never_empty.py -q --tb=no
.......                                                                  [100%]
7 passed in 0.04s
```

## Phase 5 — Finalise

Outward: push + PR. Never merge.

## Cost ledger

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
