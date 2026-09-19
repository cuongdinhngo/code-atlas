---
id: 299
slug: a-confident-hit-list-does-not-say-the-index-never-saw-this-extension
title: '160 attaches language coverage only on zeros (061 / AC3), so a non-empty `search_symbol` page of indexed-language hits — every row a `legacy/*.ts` twin — never says matching `.js` files were never candidates; field round 30 walked an agent into the forbidden tree with `reason: ok`'
phase: 1.5b
milestone: Honesty
status: done
depends_on: [160, 173, 255]
---

## Sequence — do this before 294, 295, 296

**This ticket is first in the open honesty cluster.** Do not start
[294](294_a-typescript-repo-that-imports-at-runtime-answers-unreachable-and-means-unmeasured.md),
[295](295_a-python-repo-that-imports-at-runtime-answers-unreachable-and-means-unmeasured.md), or
[296](296_the-sql-adapter-names-the-dynamic-procs-and-stamps-nothing.md) until this ships. Those three
stamp `unmodelled_resolution` on files an adapter **already parses**. They cannot mark an extension
the adapter never saw. Shipping them first leaves R30 green for PHP autoload and red for the JS twin.

Does **not** block [293](293_the-dot-spelling-is-a-near-miss-in-every-language-that-is-not-php.md) /
[297](297_the-member-demote-is-keyed-to-one-kind-so-a-class-still-buries-itself.md) /
[298](298_the-sql-adapter-answers-false-to-a-question-it-never-asked.md) (different predicates).
Does **not** gate [074](074_does-the-index-harm-mechanism-questions.md) / [200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md)
(measurements); a 200 round that scores `search_symbol` will just still be able to lie until this lands.

294–296 list this ticket in `depends_on` so the order is mechanical, not a comment.

## Why this exists (field round 30, 2026-09-18)

[160](160_a-zero-answer-never-names-the-index-language-coverage.md) closed zeros: a miss on a
partial-language index must name coverage. Its **AC3 / 061 carve-out** kept a confident non-empty
page byte-identical. Round 8 already had the other door (`DialogueService` → 1 PHP test hit vs 281
`.js` files); 160 recorded 9-C as a design call and locked the carve-out.

Round 30 reopened that door on a *hit list*, not a zero:

> `search_symbol("initialReportNew")` → 2 hits, both `legacy/**/*.ts`, `reason` not
> `language_not_indexed`. The file that had to change was
> `public/.../ControllerReportGenerator.beta.js`. `.js` is not an indexed suffix here. Every result
> pointed at `legacy/`, which the consumer forbids editing.

Not a bug in the TypeScript adapter. A well-formed, non-empty answer with **no signal that the live
copy was never a candidate.** Compare `index_stale` / `relation_unmodelled_for_language`: those
refuse to look like absence. This class looks like a location.

[173](173_coverage-claims-key-on-configured-not-indexed.md) already distinguishes configured vs
held. The stamp is on `get_index_status`. Round 30's agent **read** `capabilities_by_language:
{php, sql, typescript}` and still asked `search_symbol` about a `.js` symbol. Status is not the
payload that forms the belief.

## Scope / Deliverables

- **On `search_symbol` (including sweeps), a non-empty page carries coverage when the tree holds
  files this index never considered** that share a basename (or the query stem) with a hit or with
  the query, and whose suffix is outside the **indexed** suffix set (173's stamp, not
  `adapter_cmds`). Envelope field, omit-when-empty (061): names the unindexed suffixes / a count,
  never a guessed language, never an inferred symbol in those files.
- **`reason` stays `ok` (or today's band reason) when hits are real.** This is not a miss. The
  field is the 160 note moved onto the hit path; do not collapse it into `language_not_indexed` on
  a page that has indexed hits (that reason means the *subject* was unindexed — 160).
- **One definition site** (R6.7): reuse 173's indexed-suffix / covered-language stamp. No walk of
  file bodies. No new adapter. **Do not index `.js`.**
- **Supersedes 160 AC3 for this case only:** a confident non-empty answer is no longer universally
  byte-identical; the carve-out shrinks to "no unindexed same-basename files exist."

### Explicitly not in scope

Indexing JavaScript, ranking `legacy/` below `src/` (277), PHP `WRITES`, or stamping
`unmodelled_resolution` (294–296). A `get_index_status` line such as `unindexed_extensions` is
allowed as a sibling but does not close AC1 — the lie is on `search_symbol`.

## Constraints

- **R1.1** — suffix sets and basename match are data; no `if language == "javascript"`.
- **R5.6** — the field says *unmeasured / not a candidate*, never *the symbol lives at this .js path*.
- **061** — omit when the tree has no unindexed same-basename files; a PHP-only repo stays
  byte-identical.
- **R3** — tool-payload vocabulary, no `contract_version` bump.
- **R4.2** — deterministic given the same tree + stamp.

## Acceptance criteria

- A fixture with indexed `.ts` hits for query `Q` and a same-basename `.js` file that is not in
  `indexed_suffixes` returns the `.ts` rows **and** the coverage field naming `.js` (or a count ≥ 1).
  `reason` is not a miss code.
- The same query on a tree with no unindexed same-basename file is byte-identical to today (no field).
- A true empty miss still follows 160/173 (zero path unchanged).
- No adapter emits new node kinds; grep-gate R1.1 stays green.

## References

`code_atlas/tools/coverage.py` (160/173: note rides low-confidence only; AC3),
[160](160_a-zero-answer-never-names-the-index-language-coverage.md) AC3,
[173](173_coverage-claims-key-on-configured-not-indexed.md),
[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md),
[294](294_a-typescript-repo-that-imports-at-runtime-answers-unreachable-and-means-unmeasured.md) (after this).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 299 — hit list names unindexed same-stem suffix (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket
- **work_doc_mode:** embed · **working-doc path:** this file below separator

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Field name / shape | `unindexed_same_basename: {suffixes, count}` — suffixes + count, never a language | ticket Scope bullet 1; payload.md 160/173 table pattern |
| 2 | How to find twins | path-only census via git ls-files / ignore walk; 173 COVERED_SUFFIXES_KEY held set; stem = PurePosixPath.stem | ticket "No walk of file bodies"; store.py COVERED_SUFFIXES_KEY; R1.1 |

## Requirements matrix

`SECTIONS: 6 found (Sequence · Why this exists · Scope / Deliverables · Explicitly not in scope · Constraints · Acceptance criteria) | 6 decomposed | ROWS: C=5 R=4 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | hit list hides unindexed twin | envelope field on search_symbol hits | D1 | AC1 | ✅ |
| C1 | Constraints | R1.1 | suffix/stem data only | D1 | AC4 | ✅ |
| C2 | Constraints | R5.6 | unmeasured / not candidate; no guessed lang | D1 | AC1 | ✅ |
| C3 | Constraints | 061 omit-empty | no twin → no field | D1 | AC2 | ✅ |
| C4 | Constraints | R3 no contract bump | tool payload only | D1 | — | ✅ |
| C5 | Constraints | R4.2 | deterministic census | D1 | — | ✅ |
| R1 | Scope | non-empty page + same-stem unindexed | attach field | D1 | AC1 | ✅ |
| R2 | Scope | reason stays ok | do not flip to language_not_indexed | D1 | AC1 | ✅ |
| R3 | Scope | one site / 173 stamp | coverage.py + held_suffixes | D1 | — | ✅ |
| R4 | Scope | do not index .js | no adapter change | — | AC4 | ✅ |
| AC1 | AC | .ts hits + .js twin → field | proving | D2 | proving | ✅ |
| AC2 | AC | no twin → byte-identical | proving | D2 | proving | ✅ |
| AC3 | AC | empty miss unchanged | proving | D2 | proving | ✅ |
| AC4 | AC | no new node kinds / R1.1 green | grep / no adapter | D1 | AC4 | ✅ |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: 160/192 name adapter/language gaps; Round 30's lie is a held-language hit list whose same-stem unindexed twin was never a candidate.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R5.6 (change-type) ✅ · R6.7 (change-type) ✅ · R4.2 (change-type) ✅`

Ran at 71585db19fe14c95db46b944abb12e46c95553ac

```
$ .venv/bin/python -m pytest tests/test_zero_answer_coverage.py tests/test_coverage_keys_on_indexed.py -q --tb=no
.....................                                                    [100%]
21 passed in 3.64s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: held_suffixes + path-only same-stem census in coverage.py; wire from search_symbol (single + sweep envelope). Field unindexed_same_basename.
- Rejected: index .js (out of scope); flip reason to language_not_indexed (ticket forbids); stamp all skipped basenames at build (YAGNI).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_hit_list_unindexed_extension.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | held_suffixes + attach_unindexed_same_basename; search_symbol wire | coverage.py, search_symbol.py | search payload | 1/1 |
| D2 | proving tests | tests/test_hit_list_unindexed_extension.py | — | 1/1 |
| D3 | payload vocabulary row | docs/design/payload.md | docs | 1/1 |

## Phase 3 — Execute

**Branch:** feat/299-search-hit-unindexed-extension-coverage
**Axis 1:** coverage · search_symbol · proving · payload.md.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at 71585db19fe14c95db46b944abb12e46c95553ac

```
$ .venv/bin/python -m pytest tests/test_hit_list_unindexed_extension.py -q --tb=no
...                                                                      [100%]
3 passed in 0.65s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — CLEAN (14 met / 0 not met / 0 can't tell). agent 5b16f5d8-504e-47d1-b3cf-5dcfd9d29182

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_hit_list_unindexed_extension.py — 3 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN — all 20 checks passed (`scripts/gate.sh`)
PR: https://github.com/cuongdinhngo/code-atlas/pull/389

## Review finding — the census was O(files x ignore-rules), 2026-09-19

Pre-merge review measured `_unindexed_same_stem_census` on a 51,858-file tree: **4,842 ms added to
every non-empty `search_symbol` call**, of which 4,689 ms was `is_ignored` running the full rule walk
on every tracked path. The field rides the hottest tool, so that is not a cost the payload's value
covers.

The three filters are an AND, so ordering them is free: basename suffix, then stem, then
`is_ignored`. Same answer (40 files, same five suffixes), **24.5 ms** — the rule walk runs 120 times
instead of 51,858. `test_census_tests_the_basename_before_it_walks_the_ignore_rules` pins the order
with a spy, because the slow ordering passes every other test.

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
