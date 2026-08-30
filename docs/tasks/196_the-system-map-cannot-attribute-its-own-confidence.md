---
id: 196
slug: the-system-map-cannot-attribute-its-own-confidence
title: "The committable system map reports one blended confidence figure and cannot say which language earned it"
phase: 1.5b
milestone: Measure
status: todo
depends_on: [195]
---

## Why this exists

[195](195_three-tools-still-read-the-whole-graph-blend.md) enumerated every consumer of the
whole-graph `edge_health()` aggregate and re-pointed the two it could: `find_orphans` and
`reachable_from` now carry the 183 per-language split beside the blend. The third consumer is
`code_atlas/tools/generate_onboarding.py:99`:

```
confidence = store.edge_health()["by_tier"]
```

It is a **genuinely whole-graph headline** — the artifact describes the whole repo — so the number is
right. It is also the one a human reads. PILLAR 2 exists so a person supervising an agent can see
what the code actually is, and on a two-language index the map's confidence figure is a blend that
names no language, which is round 12 §13's complaint pointed at the audience it matters most for.

## Why 195 did not do it

195's *Explicitly not in scope* is *"Any new aggregate. This re-points existing readers at an existing
stamp."* `confidence` is not a payload caveat: it is a field of the **versioned published dataset
schema** (`DATASET_VERSION`, currently 7 — `code_atlas/onboarding/dataset.py:45`), read by
`code_atlas/onboarding/headlines.py:186` and rendered by `code_atlas/onboarding/viewer.py:398`'s
JavaScript. Adding to it is a schema bump and a renderer change on a committed artifact, not a
re-point — a different ticket, deliberately.

## Scope

1. Carry the per-language split into the onboarding dataset from the **183 stamp**, not a second fold
   (195's Scope 3 and 183's own lesson: two folds stop summing to the whole).
2. Bump `DATASET_VERSION` and update the artifact/dataset conformance tests.
3. Render it where a human reads the confidence figure, so the map can say which language earned it.

### Explicitly not in scope

- `contract_version`. The adapter contract is untouched; `DATASET_VERSION` is not it
  (`dataset.py:11`).
- Any new *measurement*. The stamp already exists; this is a second reader of it.

## Constraints

- **183's arithmetic invariant** — the slices plus `unattributed` must equal the whole, pinned in the
  dataset as 195 pinned it in the payloads.
- **R5.6** — a pre-183 index has no stamp; the map must say so rather than claim one language.
- **R4.2** — identical graph ⇒ identical artifact bytes.

## Acceptance criteria

1. The dataset carries the per-language split, read from the stamp, and reconciles against the whole.
2. An index with no stamp renders the blend with the attribution **stated as unavailable**, not
   silently omitted and not invented.
3. `DATASET_VERSION` is bumped and the conformance tests move with it.
4. No `contract_version` bump.

## References

[195](195_three-tools-still-read-the-whole-graph-blend.md) (the enumeration and the deferral),
[183](183_edge-health-has-no-per-language-breakdown.md) and claim `183-C1`. Field retro round 12 §13.
