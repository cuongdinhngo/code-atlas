---
id: 190
slug: a-same-second-guard-is-flaky-under-suite-load
title: '`test_ac4_a_same_second_same_size_edit_is_a_stale_import` needs two writes inside one wall-clock second and flakes under full-suite load'
phase: 1.5b
milestone: Coverage
status: todo
depends_on: [146]
---

## Why this exists

Observed **twice** in one autorun batch (2026-08-28), during 175 and again during 182: green alone,
green on a re-run, red once inside a full `pytest -q`.

```
tests/test_bytecode_invalidation.py:70: AssertionError
>   assert _import_value(tmp_path) == 1, "if this reads 2, CPython changed and 146 can be dropped"
```

146's hazard is real and the guard is the right guard: timestamp-based `.pyc` invalidation misses an
edit that lands **in the same second and at the same length**. But the test **creates** that condition
by writing twice in quick succession, and under a loaded suite the two writes can straddle a second
boundary — at which point CPython correctly picks up the new source and the assertion fails.

**So the guard fails for the wrong reason.** It is not reporting that 146's hazard has gone; it is
reporting that the machine was slow. R6.5's spirit is that a guard must fail only when the thing it
forbids is present.

## Scope

1. Make the premise deterministic instead of hoping for it: set both files' `st_mtime` explicitly
   (`os.utime`) so "same second, same size" is **constructed**, not raced.
2. Keep the escape hatch the assertion message names — if CPython's behaviour ever changes, the test
   must still say so rather than being skipped into silence.
3. Check the sibling tests in the file for the same race
   (`test_ac4_checked_hash_reads_the_source_that_is_on_disk` writes twice as well).

### Explicitly not in scope

- 146's fix itself (`--invalidation-mode checked-hash` in the gate). It works and is separately pinned.
- Any change to `scripts/gate.sh`.

## Constraints

- **R6.5** — the guard must still be observable failing against the shape it forbids; a deterministic
  premise must not become a mock of the hazard.
- **R4.2** — no wall-clock dependence left in the assertion path.

## Acceptance criteria

1. The test's premise (same second, same size) is set explicitly and asserted before the import.
2. The test passes 20 consecutive full-suite runs, or the flake is otherwise shown to be gone.
3. The "CPython changed" escape hatch still fires if timestamp invalidation starts catching the edit.
4. Sibling tests in the file are checked for the same race and fixed or cleared.

## References
Observed 2026-08-28 in the 180–182 autorun batch (recorded in 175's and 182's working docs and
disclosures). `tests/test_bytecode_invalidation.py:62-70`. Related:
[146](146_gate-can-pass-on-stale-bytecode.md).
