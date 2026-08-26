---
id: 166
slug: read-symbol-answers-from-pre-repair-state-and-calls-it-no-such-symbol
title: '`read_symbol` answers from the pre-repair state and reports `no_such_symbol` / `stale: false` — an identical second call returns the symbol'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [035, 014, 065]
---

## Why this exists (field retro round 10, 2026-08-26)

A confident false negative for a symbol merged that day, and a second identical call answered it
correctly — two tools disagreeing about the same symbol in the same index in the same minute:

```
call 1:  read_symbol(ImprovementUtility::buildPaginatorQuery)
         → found: false, reason: "no_such_symbol", stale: false      ← WRONG
call 2:  read_symbol(same args, seconds later)
         → found: true, line_start: 352, correct source              ← RIGHT
search:  search_symbol("buildPaginatorQuery")
         → found at line 352, reason: "ok"                           ← RIGHT, contradicts call 1
```

The retro's reading: **read-through repair fires but the answer is composed from the pre-repair
state**, and that answer is labelled with the one reason an agent is entitled to treat as proof of
absence. `no_such_symbol` at `stale: false` is the strongest negative the surface can emit; here it was
produced by a race, not by the graph.

Corroborating, and part of the same fault line: `get_index_status` reported **`dirty_indexed_files: 0`**
while the file's mtime was **1h45m after** `built_at`. The file-level dirty count was wrong at the same
moment the index-level `staleness: "behind"` was right.

**Note this is not the "missing reason" it looks like.** `read_symbol` already has `index_stale`
(`read_symbol.py:45-48`) and already re-queries after repair. The defect is **ordering and coverage of
the re-query**, which is a different and more serious fix than renaming a reason — the retro's own §15
runner-up understates it.

## Root cause — where to look

- `code_atlas/tools/read_symbol.py:64-88` — the miss path: `rows` empty → `guard.ensure_miss()` →
  on `"repaired"` the rows are re-fetched, and on a still-empty result `_resolve_miss` produces the
  terminal miss payload. The observed behaviour says one of these three is true, and **design must
  determine which before writing code**:
  1. `ensure_miss()` returned something other than `"repaired"` for a file whose hash had drifted (so no
     re-query ran at all);
  2. the re-query at `:84` ran against a store handle that does not see the repair's write;
  3. the repair is asynchronous or partial, so the re-query is correct-but-early.
- `code_atlas/tools/read_symbol.py:108-118` — the same re-query-after-repair shape on the **found**
  path, which must get whatever fix the miss path gets.
- The `dirty_indexed_files: 0` contradiction points at the freshness signal itself, not only at
  `read_symbol`: a file-level dirty count that reads `0` for a drifted file cannot gate a repair.

**A reproduction is the first deliverable.** The retro's evidence is two probes seconds apart; the
ticket must not assume the cause.

## Scope

1. Reproduce the two-calls-disagree sequence deterministically in a test (write a file, index, edit,
   read twice).
2. Fix the ordering so a repaired file's symbol is visible to the answer that triggered the repair.
3. If a case remains where the answer genuinely cannot be composed post-repair, it must report
   `index_stale`, **never** `no_such_symbol` — a negative that a race can produce must not wear the
   spelling reserved for proof of absence.
4. Check `dirty_indexed_files` against the same scenario and record whether it is the same fault or a
   separate one (a separate ticket if so — do not widen this one).

### Explicitly not in scope

- Making the index synchronous, or rebuilding on read.
- `search_symbol`'s behaviour, which was **correct** throughout this incident.
- The consuming repo's `CLAUDE.md` carve-out (*"a symbol you just wrote reads as absent"*) — it is
  their file; this ticket's job is to make the carve-out unnecessary, not to edit it.

## Constraints

- **R4.2** — the fix must be deterministic; a retry loop that sometimes wins is not a fix.
- **065** — an empty answer must say **why**, and the why must be the true one.
- **Cost** — `read_symbol` is the highest-frequency read on the surface. No extra query on the common
  path where nothing has drifted (061 shape).
- **R1.1 / R3** — no language branch, no contract bump.

## Acceptance criteria

1. A test reproduces the failure on the pre-fix code (write → index → edit → read) and passes after the
   fix: the **first** call returns the symbol.
2. No path can return `reason: "no_such_symbol"` with `stale: false` for a symbol whose file has drifted;
   such a case returns `index_stale`.
3. The clean path (no drift) is byte-identical and incurs no additional query.
4. The `dirty_indexed_files: 0` observation is checked and its verdict recorded — fixed here, or filed
   as its own ticket with evidence.
5. Determinism (R4.2); no bump (R3); no language branch (R1.1).

## References

Field retro round 10 §5 (**the round's second finding**), §4 (*"unmodelled silence dressed as a modelled
zero"*), §1 P2/P3/P4, §15 runner-up, §14 (**8-A: a new instance of the same class, uncovered**).
`code_atlas/tools/read_symbol.py:45-48,64-88,108-118`. Related: [035](035_read-through-freshness.md)
(read-through repair), [014](014_search-read-outline.md), [065](065_empty-answer-cannot-explain-itself.md).
