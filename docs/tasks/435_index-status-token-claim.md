---
id: 435
slug: index-status-token-claim
title: "README's \"~100-token get_index_status\" — make the number true and hold it with a test"
phase: 2
milestone: Docs
status: todo
depends_on: []
---

## Why this exists

`README.md:190` calls `get_index_status` "the cheap (~100-token) entry point", in a README that says
its numbers are measured, not asserted. Measured 2026-11-04 on this repo's own index (784 files) with
`code-atlas query get_index_status`:

| `detail_level` | chars | ~tokens (chars/4) |
|---|---:|---:|
| `standard` (default) | 3,236 | ~809 |
| `minimal` | 830 | ~207 |
| `verbose` | 5,021 | ~1,255 |

The default is about 8× the claim, and even `minimal` is about 2×. (The brief measured 2,042 / 971 on
Flask and called the level `brief`; the level is `minimal` now.) A skeptical reader checks this number
first.

## Acceptance

1. The README number is true: either `minimal` gets down to about 100 tokens, or the README states the
   measured value and names the `detail_level` that gives it. The analysis picks one and records why.
2. A test measures `get_index_status` on a pinned in-repo fixture and fails when the README's number
   is off by more than ±20%, like the repo's other doc/number agreement tests.
3. If `minimal`'s shape changes, the byte-identical rule for `minimal` on a built index (061,
   `code_atlas/tools/get_index_status.py:278`) and the staleness verdict fields still hold.
   `stale_process` stays a verdict.

## Out of scope

- Per-response metadata on the other tools (brief A3).
