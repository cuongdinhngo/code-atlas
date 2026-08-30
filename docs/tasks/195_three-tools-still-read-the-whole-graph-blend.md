---
id: 195
slug: three-tools-still-read-the-whole-graph-blend
title: '183 split the tier mix per language for one caller; three other tools still read the whole-graph blend'
phase: 1.5b
milestone: Measure
status: todo
depends_on: [183]
---

## Why this exists

183 built `edge_health_by_language` because *"a whole-graph blend cannot be attributed"*, and wired it
into `get_index_status`. Three other callers still read the un-split number:

```
code_atlas/tools/find_orphans.py:114        health = store.edge_health() ...
code_atlas/tools/generate_onboarding.py:99  confidence = store.edge_health()["by_tier"]
code_atlas/tools/reachable_from.py:55       health = store.edge_health() ...
```

Round 12 §13 recorded what that costs, on the two-language index: *"**Cannot answer.** No per-language
breakdown exists in any payload. Whole-graph HEURISTIC fell 68.9 % → **53.51 %**, still **+9.6 pp**
over PHP-only. **This is a measurement the tool cannot make about itself**."*

**Claim `183-C1` predicted exactly this and named its own destination**: *"the actionable form is a
roll-out checklist item (enumerate the aggregates this new dimension makes ambiguous), which belongs
to whichever ticket adds adapter #3."* [184](184_tsql-source-adapter-tier-1a.md) is that ticket, and
its AC3 forbids a `code_atlas/` diff — so the enumeration lands here instead of being absorbed there.

**The number is already wrong, today, with two languages.** This does not wait on a third.

## Scope

1. Enumerate every consumer of the whole-graph aggregate, from the code and not from memory — the
   three above are the trace, not an assumption.
2. For each, decide and record: does it want the whole-graph number, the subject's slice, or both? A
   confidence figure attached to a per-language answer that reports a cross-language blend is the
   defect; a genuinely whole-graph headline is not.
3. Where a slice is wanted, read the stamp 183 already writes — no second scan, no second fold. 183's
   own lesson is that two folds make the split stop summing to the whole.

### Explicitly not in scope

- Any new aggregate. This re-points existing readers at an existing stamp.
- `get_index_status`, already correct (183).
- The `unattributed` residue's definition — 183 settled it and it stays as is.

## Constraints

- **183's arithmetic invariant** — the slices plus `unattributed` must equal the whole; that
  reconciliation is the only check an outside reader has.
- **R1.1** — read the stamp by language key, never branch on a language name.
- **R6.5** — each re-pointed caller ships with a red run showing the blended number where the slice
  was wanted.

## Acceptance criteria

1. Every consumer of `edge_health()` is enumerated with a recorded decision (slice / whole / both).
2. Each caller that wanted a slice reads the 183 stamp, and its payload is pinned by a test that fails
   on the blended value.
3. The slices-plus-residue reconciliation still holds, pinned as 183 pinned it.
4. No `contract_version` bump.

## References

Field retro round 12 §13 (*"a measurement the tool cannot make about itself"*, the +9.6 pp).
[183](183_edge-health-has-no-per-language-breakdown.md) and its claim `183-C1`
(`an-aggregate-outlives-the-world-that-named-it`, `docs/LESSONS.md`).
