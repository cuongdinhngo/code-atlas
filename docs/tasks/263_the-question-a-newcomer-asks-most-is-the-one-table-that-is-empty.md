---
id: 263
slug: the-question-a-newcomer-asks-most-is-the-one-table-that-is-empty
title: '"I was told to change screen X — which file?" is the question the onboarding artifact exists to answer, and it is the one table that renders empty on an ordinary repo: modules are found by structural fan-out, which scores zero on all three pinned samples, so the artifact answers every question except the one that was asked'
phase: 3
milestone: Onboarding
status: todo
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
