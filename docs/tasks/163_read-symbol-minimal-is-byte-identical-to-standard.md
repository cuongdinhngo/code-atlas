---
id: 163
slug: read-symbol-minimal-is-byte-identical-to-standard
title: '`read_symbol` `detail_level: "minimal"` is byte-identical to `standard` — a documented knob that does nothing'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [014, 066]
---

## Why this exists (field retro rounds 7 & 9)

`read_symbol` advertises a `detail_level` of `minimal` / `standard`, but the two return exactly the
same bytes — verified across two rounds:

> Round 9 (**7-F**): `read_symbol` at `minimal` and at `standard` on the same method — *"same keys,
> same full doc comment, same full body, same `line_start`/`line_end`. Not one byte differs."*
> Unchanged from round 7, which found the same.

Elsewhere `minimal` earns its name — `get_index_status`'s `minimal` deliberately drops provenance and
`edge_health` to stay ~100 tokens (task 066). On `read_symbol` it is a promise the payload does not
keep: a caller who asks for the cheap shape pays the full shape and cannot tell.

## Root cause

- `code_atlas/tools/read_symbol.py:33` declares `DetailLevel = Literal["minimal", "standard"]` and
  threads `detail_level` through every code path.
- `code_atlas/tools/read_symbol.py:260` — `_result()`, the found-symbol payload builder, opens with
  `del detail_level, db_path`: the parameter is **explicitly discarded**. The payload keys are the
  same for both levels; the `source` slice (`_slice` → `declaration_slice`, `read_symbol.py:226-228`)
  is the full declaration **plus the contiguous comments above it** regardless of level.
- `_empty()` (`read_symbol.py:234`) does the same `del detail_level`.

So the knob has no effect anywhere in `read_symbol`.

## Scope — pick one, record why

- **Option A — remove the knob.** Drop `detail_level` from `read_symbol`'s signature and payload
  plumbing. Honest: `read_symbol` returns a symbol's declaration; there is no cheaper useful shape, so
  the parameter should not exist. Simplest, and it removes a misleading affordance.
- **Option B — make `minimal` actually trim.** Have `minimal` return the declaration **without** the
  contiguous comment block that `standard`'s `source` carries above the signature. This also narrows
  the 8-H trap (the returned `line_start`/`line_end` name the symbol, while `source` silently includes
  the docblock above — a caller splicing by the range gets different text than `source`); a comment-free
  `minimal` `source` would then match its own range.

Design chooses A or B with the reason recorded; do **not** ship both. Default recommendation: **A**
(YAGNI / R7.1) unless a measured caller wants the trimmed body.

### Explicitly not in scope

Changing `get_index_status`'s `detail_level`, which is correct and load-bearing (066).

## Constraints

- **R7.1** — smallest thing that makes the surface honest; removing a no-op parameter is smaller than
  inventing behaviour for it.
- **R3** — `detail_level` is a tool argument, not contract vocabulary; no `contract_version` bump.
- **061** — if Option B, the `minimal` payload must be measurably smaller than `standard`, not merely
  differently shaped.
- **R4.2** — deterministic either way.

## Acceptance criteria

1. Either `read_symbol` no longer accepts `detail_level` (Option A), **or** its `minimal` payload is
   measurably smaller than `standard` on a symbol that has a docblock (Option B) — pinned by a test.
2. The chosen option and the reason for rejecting the other are recorded in the working doc.
3. No existing caller/test silently breaks: every reference to `read_symbol(..., detail_level=...)` is
   re-read and updated with the verdict recorded.
4. Determinism holds (R4.2); no `contract_version` bump (R3).

## References

Field retro rounds 7 & 9, finding **7-F** (and touches **8-H** — range vs. docblock in `source`).
`code_atlas/tools/read_symbol.py:33,226-228,234,260`. Related:
[014](014_search-read-outline.md) (read_symbol's origin), [066](066_limit-clamped-silently.md)
(where `minimal` genuinely trims and why it matters).
