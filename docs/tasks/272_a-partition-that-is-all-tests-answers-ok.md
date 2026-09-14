---
id: 272
slug: a-partition-that-is-all-tests-answers-ok
title: 'Every honesty escalation in `find_callers` is gated on `total_count == 0`, so a subject whose only linked callers are tests answers `reason: ok` with `production_count: 0` — the exact signature of dead production code — while its sibling method, unreachable for the same reason, answers `relation_unmodelled_for_language`; make a zero *partition* as honest as a zero *answer*'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [262, 255, 264]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 20 §4)

Two methods on one class, both called exactly once from production, both through the same untyped
property (`$this->model = new CaseRegisterModel()`). The resolver types neither. The payloads:

| Subject | `reason` | rows | reality |
|---|---|---|---|
| `…::getCaseTranHistory` | `relation_unmodelled_for_language` + *"treat the empty answer as unmeasured, not as zero"* | 0 | one production caller |
| `…::getPathforRiskMatrix` | **`ok`**, `production_count: 0`, `test_count: 2` | 2 | one production caller |

The second resolves two callers only because the *test* helper declares a return type
(`private function createModel(…): CaseRegisterModel`). So the rule in practice is: **a declared
type links, an untyped property drops.** When every caller drops, the payload says unmeasured. When
only the production callers drop, it says `ok`.

The mechanism is in one place. `unlinked_calls` (`find_callers.py:428–441`), the shared 264 predicate
(`:442–452`) and the whole reason chain (`:469–482`) are each gated on `outcome.total_count == 0`.
A non-empty hit set skips all of them, and the partition 262 added (`:519–523`) is then emitted beside
`reason: ok` with no honesty pass of its own.

`authoritative: false` does not save it: it was on this payload too, as it is on almost every payload
in a multi-language repo ([276](276_the-caveat-that-fires-on-every-answer.md)).

## Scope / Deliverables

- **The honesty predicate runs on the partition, not only on the total.** When `production_count == 0`
  and the subject is indexed, the same evidence 255/264 already gather must run — unlinked inbound
  edges naming this subject, bare-name truncation, the cross-language census — and decide the
  reason. A partition that cannot be falsified stays `ok`.
- **A reason that names the shape.** `production_count: 0` beside surviving test rows is not
  `no_matches` and not a bare `ok`. Whatever word the vocabulary gains, it must carry the same
  *"unmeasured, not zero"* route the empty case already carries.
- **Count what falsifies it, and say the number.** The evidence exists: unlinked same-name call sites
  are countable today (`store.count_unlinked_by_target_raw`). A `production_count: 0` answer that also
  carries `unlinked_same_name_sites: 1` is one an agent cannot misread.
- **Same treatment in `find_references`** — same partition, same gate.

## Constraints

- **No new resolution.** Typing `$this->prop->method()` is [a separate ticket](#references) and a
  harder one; this ticket changes only what the payload says about what it already knows.
- R5.6: evidence, not inference. No route is named on a silence — a language that emits no inbound
  kind for this subject says so from the stamp, never from a guess.
- R4.2: the added counts are derived from stored rows, byte-reproducible.
- 061: nothing new on a payload that has nothing to add — a partition with production rows is unchanged.

## Acceptance criteria

- A fixture with one unlinked production call site and one *typed* test caller returns
  `production_count: 0` and a reason that is **not** `ok`, carrying the count of unlinked same-name
  sites.
- The same fixture with the production call site linked returns `reason: ok` unchanged.
- A subject with genuinely no production callers and no unlinked evidence still returns `ok` — the
  ticket must not make a true zero unsayable.
- `find_references` gets the same test.
- No existing `relation_unmodelled_for_language` case changes wording or route.

## References
`code_atlas/tools/find_callers.py:428–482,519–523`, `code_atlas/tools/find_references.py:292`,
`code_atlas/store.py` (`count_unlinked_by_target_raw`), field retro round 20 §4 / §9,
round 22 §4 (the honest arm, working as intended),
[262](262_the-contract-marks-test-code-and-no-tool-reads-it.md),
[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md),
[264](264_the-honesty-predicate-is-still-one-language-s-shape-wearing-a-constant-s-name.md),
[276](276_the-caveat-that-fires-on-every-answer.md).
