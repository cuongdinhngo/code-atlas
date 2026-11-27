---
id: 463
slug: near-duplicate-bodies
title: "Near-duplicate bodies under different names — evidence-gated"
phase: 2
milestone: "Field gaps — Python/TS consumer"
status: deferred
depends_on: [098]
---

> **Status: deferred.** A hypothesis and its gate, like 098 (copy/port between files), which this is
> the symbol-level case of.

## Why this exists

The Python/TS consumer's audit (2026-11-27) found the same logic copied under different names,
by hand and with grep:
- the "call the LLM, validate, retry with feedback" loop, 6 times in `studio/core/`;
- `e instanceof Error ? e.message : …`, 14 times in `web/src`;
- the native `<dialog>` `showModal` effect, 3 times;
- the pack-test Playwright setup, in 6 test files.

`_body_hash` already exists (`_moved_by_body` uses it for same-name moves, 384), so the index is close to answering "which
symbols share a normalised body". It cannot catch the inline expression copies, which are not
symbols.

## Gate (all three before this becomes `todo`)

1. A second consumer repo asks for it, or the anchor shows ≥ 10 symbol-level copy groups that a
   maintainer confirms.
2. A spike on the existing body hash (exact normalised match only) finds at least 4 of the 6 retry
   loops in the Python/TS consumer at the audited commit. If an exact hash finds none, the idea needs fuzzy
   matching, which is a new dependency and its own decision.
3. Precision ≥ 0.8 on the spike's top 20 groups (getters and `__init__`s excluded).

## Scope (if the gate passes)

A `compute` template: groups of ≥ 2 symbols with the same normalised body hash and ≥ N lines, rows
`(group, qname, file:line)`. No new storage beyond the existing hash.
