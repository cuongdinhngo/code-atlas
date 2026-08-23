---
id: 119
slug: reachability-signal-provenance
title: Onboarding — the reachability split never says which signal produced each count, so a false declaration is invisible (M11)
phase: 3
milestone: M11
status: done
depends_on: [113, 116]
---

## Why this exists (measured, anchor monorepo, 2026-08-21)

The anchor's `.code-atlas.toml` declared:

```toml
entry_points = ["public/*.php", "legacy/*/web/*.php"]
```

The second glob matched **1,087** files and put **560** of them into 113's **Web entry points** bucket.
The declaration was **false**: all three nginx configs set `root /var/www/html/public`, the only location
blocks that reset root serve `/src/` static assets and `/uploads/`, and the `@legacy_static` fallback into
`legacy/alpha/web` was removed by that repo's own task-212. No request can address a legacy page.

The artifact reported the bucket as:

```
- **Web entry points**: 901 (sample capped)
  - signal: declared entry-point globs, or a path naming a request-handling responsibility
```

**One number over two signals.** The split — 653 from the operator's globs (560 legacy + 93 `public/`) and
248 from 110's responsibility vocabulary — appears nowhere in the payload, the markdown or the map. It had to
be recomputed by hand, against `_bucket_of`, to find the wrong declaration. After the operator corrected the
knob: **341** = 93 declared + 248 vocabulary, with 494 files moving to *not statically reachable* and 66 to
*no edge either way*.

The cost of the invisibility is not cosmetic. 113 calls a declaration "the highest-trust signal, because it is
that operator's statement about their own repo rather than the core guessing" — and it is, right up until the
statement is stale. While it stood, every unreferenced legacy page was **self-justifying to `find_orphans`**:
declared a root, therefore never an orphan. The one number that would have exposed it — *560 of these files
are in this bucket because you said so* — was never printed.

## Scope

Disclosure only. The core still may not judge whether a declaration is true; it can only show what the
declaration did (R4, no new heuristic):

- Per bucket, report the **provenance counts**: how many members came from a declared pattern and how many
  from the path vocabulary. `signals: {declared: N, vocabulary: N}`.
- Report **per declared pattern**: the pattern, how many indexed files it matches, and how many zero-inbound
  modules it placed in a bucket. A pattern that matches 1,087 files and claims 560 roots is then legible at a
  glance without reproducing `_bucket_of` by hand.
- Both renderers carry it: the `architecture_overview` payload and the emitted artifact (markdown + map).
- No change to classification, bucket order, or the raw total. This ticket adds numbers; it moves nothing.

## Acceptance criteria

1. **AC1.** Classification is unchanged: on the anchor, the five bucket counts before and after this ticket
   are identical, asserted in a test, not eyeballed.
2. **AC2.** The provenance numbers reproduce this session's measurement exactly — 341 = 93 declared + 248
   vocabulary with the corrected knob, and 901 = 653 + 248 with the old one, both from the same index.
3. **AC3.** Each declared pattern reports `files_matched` and `zero_inbound_claimed`; a pattern matching
   nothing reports zero rather than being omitted, so a typo'd glob is visible as a zero, not as silence.
4. **AC4.** A bucket whose signal is unavailable stays *dropped with its reason* (113's AC5) — provenance
   never resurrects a bucket as a misleading zero.
5. **AC5.** Deterministic and SQL-free: the split is computed from the same in-memory metrics 113 already
   walks, adds no query, and is byte-stable (R4.2 / R4.3).
6. **AC6.** No judgment shipped: nothing in the output calls a declaration wrong, stale or suspicious. The
   operator reads the counts and decides.

---

## Closed by [127](127_caveats-drop-at-the-artifact-layer.md), 2026-08-23

127's derived caveat guard needed a first customer and this was it: the split carried the counts and
dropped the declarations that produced them. Shipped there, in one change — per-bucket
`signals: {declared, vocabulary, structure}`, one `PatternClaim` per declared glob with
`files_matched` beside `zero_inbound_claimed`, and `DECLARATION_CAVEAT` riding on the split so no
renderer can show a declared count without it. Classification, bucket order and the raw total moved
by nothing (AC1), a dropped bucket stays dropped (AC4), and nothing in the output judges a
declaration (AC6).

**AC2 is met in restated form and the deviation is recorded, not hidden.** Its figures — 341 = 93 + 248
with the corrected knob, 901 = 653 + 248 with the old one — are anchor measurements, and the anchor
monorepo is not present on the host this ran on. The assertion became the arithmetic those numbers are
an instance of: every bucket's signal tally sums to its count, and a pattern's `files_matched` is
reported separately from what it claimed. **The anchor figures remain unverified here.** Re-running
`scripts/reachability_report.py` against the anchor is the operator step that would close them —
the same "anchor deferred to operator" pattern as 108 and 112–117.
