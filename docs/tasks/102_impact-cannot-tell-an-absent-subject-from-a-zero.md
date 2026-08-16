---
id: 102
slug: impact-cannot-tell-an-absent-subject-from-a-zero
title: '`impact` reports `seeds_dropped: 0` for a subject it never found — the one number that separates a modelled zero from a failed query'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [017, 100]
---

## Goal
`impact` answers a subject it cannot resolve at all with `results: []` **and**
`seeds_dropped: 0` — the same pair it returns for a genuine modelled zero. The two are
indistinguishable in the payload, and `seeds_dropped` is precisely the field a reader consults to
tell them apart.

Measured during task 100:

```
$ impact(qnames=["\App\Nope"], sign=True)
results=0 seeds_dropped=0
```

`\App\Nope` is not in the index. Nothing was walked. The payload says a clean zero.

## Root cause
`code_atlas/store.py:1009-1011`:

```python
ordered_seeds = list(dict.fromkeys(q for q in seeds if q))
if not ordered_seeds:
    return ImpactResult([], 0, 0)
```

The empty-seed early return is taken **before** any counting, so the drop is never attributed.
Upstream, `impact._resolve_seed` (`code_atlas/tools/impact.py`) returns `None` for a qname that
neither matches exactly nor resolves uniquely, and `_seeds` simply skips it — so the information
that a seed was requested and lost exists at the call site and is discarded one frame later.

## Why this is worth a ticket, not a note
`impact`'s value is the class of claim a text search cannot make: **a modelled zero**. That claim
rests entirely on `seeds_dropped == 0` meaning *"every subject you named was found"*. When the field
is 0 because nothing was ever counted, the strongest answer this server produces is
indistinguishable from its weakest, and the reader has no way to tell.

Task 100 shipped a **workaround, not a fix**: `impact` refuses to attach a signed `claim` line when
the seed set is empty, so the ambiguity cannot become a quotable falsehood. That guard protects the
one consumer 100 added. **Every other reader of the payload is still misled** — including any agent
reading `seeds_dropped` directly, which is the documented way to interpret an empty `impact` answer
(PLAN §12; task 065).

## Scope / Deliverables
- **Attribute the drop.** A requested seed that does not resolve must be counted in `seeds_dropped`,
  including when it is the *only* seed. Decide where the count belongs — `store.impact_radius`
  cannot see what `_seeds` discarded, so this is likely a tool-side count added to the store's,
  not a change to the early return alone.
- **Distinguish the two zeros in the payload.** After the fix, `results: []` with
  `seeds_dropped: 0` means a modelled zero and nothing else. Consider whether a subject that
  resolved to *no seeds at all* also needs a `reason` (the nav vocabulary already has
  `no_such_symbol` / `name_not_qualified` / `not_indexed`, and `classify_missing_subject` is
  already called on this path) — an empty `impact` answer currently carries no `reason` at all.
- **Re-examine task 100's guard.** Once the payload can tell the two apart, the
  `if not sign or not seeds` refusal in `impact` may be replaceable by an honest line that names the
  drop (`seeds_dropped=1`). Removing the guard is **not** required by this ticket; deciding whether
  it should go is.
- **Multi-seed partial loss.** `impact(paths=[a, b])` where `a` resolves and `b` does not must
  report `seeds_dropped: 1`, not 0 — check whether this already works or shares the bug.

## Constraints
- **R4** — same index, same subject, same counts. No new query on the hit path.
- **061** — the fix must not add a field to the common (non-empty, nothing-dropped) answer.
- **R3** — `seeds_dropped` is an existing tool-payload field; changing what it counts is a
  **behaviour change to a documented number**. PLAN §12 and any test asserting `seeds_dropped == 0`
  must be re-read, not merely re-recorded (a changed expectation here is a behaviour change, not a
  golden to bump).
- **R1.1** — no language branch; resolution already runs through `classify_missing_subject`.

## Acceptance criteria
- `impact` over a subject absent from the index reports `seeds_dropped >= 1`, pinned by a test.
- `impact` over an indexed subject with no dependents still reports `seeds_dropped: 0`, pinned by a
  test on the same fixture — the two must be shown to differ, not merely asserted separately.
- A partial loss (one seed resolves, one does not) reports the count of the lost seeds.
- Every existing assertion on `seeds_dropped` is re-read and either still correct or corrected with
  the reason recorded; no expectation is updated to match new output without that reasoning.
- A decision recorded on task 100's `if not seeds` signing guard: kept, or removed with the
  replacement line shown.

## References
Found during task 100 (`docs/tasks/100_claim-signing-output-mode.md`, Phase 3 finding **F1**),
measured but deliberately not fixed there — outside that ticket's approved change list.
`code_atlas/store.py:1009-1011` (the early return), `code_atlas/tools/impact.py` (`_seeds`,
`_resolve_seed`). Related: [017](017_impact-engine.md) (the attestation itself),
[100](100_claim-signing-output-mode.md) (the workaround and the consumer that exposed this),
[065](065_empty-answer-cannot-explain-itself.md) (an empty answer must explain itself),
[075](075_read-symbol-confident-zero-on-unnormalised-qname.md) / [076](076_bare-name-subject-reads-as-absence.md)
(`classify_missing_subject`, already on this path).
