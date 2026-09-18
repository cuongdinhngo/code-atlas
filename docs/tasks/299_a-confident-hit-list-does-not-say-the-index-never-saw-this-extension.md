---
id: 299
slug: a-confident-hit-list-does-not-say-the-index-never-saw-this-extension
title: '160 attaches language coverage only on zeros (061 / AC3), so a non-empty `search_symbol` page of indexed-language hits — every row a `legacy/*.ts` twin — never says matching `.js` files were never candidates; field round 30 walked an agent into the forbidden tree with `reason: ok`'
phase: 1.5b
milestone: Honesty
status: todo
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
