---
id: 349
slug: cross-repo-floors-predate-258
title: 'The cross-repo edge floors were measured before 258, so the weekly run fails on two samples'
phase: 2
milestone: Coverage
status: done
depends_on: [018, 233, 258]
---

## Why this exists

Issue #4: the scheduled cross-repo run of 2026-09-28 (run 36419867195, `ff9c707`) failed with
`socketio: edges must be >= 48520, got 28050` and `flask: edges must be >= 8635, got 7317`. It
reproduces locally on `09d1e8e` (9 ok, 2 failed).

## Cause

Bisecting `main`'s first-parent history on flask's edge count
(`986e614` 10,794 → `09d1e8e` 7,300) lands on `6e6f577` — 258, *one unresolved CALL site*.
258 keeps a multi-match bare CALL as one unresolved edge instead of one edge per same-named
candidate. Files and nodes are unchanged on every sample; only edges fall:

| sample | before 258 (`f7f0f19`) | after (`6e6f577`, `09d1e8e`) | old floor | new floor (≈80%) |
|---|---|---|---|---|
| socketio | 53,299 | 28,050 | 48,520 ❌ | 22,440 |
| flask | 10,794 | 7,300 | 8,635 ❌ | 5,840 |
| pydantic | 90,199 | 78,584 | 72,159 | 62,867 |
| requests | 5,220 | 4,417 | 4,176 | 3,534 |

The drop is 258's intended behaviour, not a regression. The floors predate it, and the cross-repo
job is not in the gate, so 258 never re-measured them.

## Scope

1. Re-floor `min_edges` for the four samples 258 moved, at ≈80% of the post-258 build, and record
   the re-measure in the manifest's `contract_note`. File and node floors are unchanged.

## Proof

`python scripts/cross_repo_validate.py --public-only --skip-clone` on this branch:
`{"public_ok": 11, "public_failed": 0}` (was 9 / 2 on `main`).
