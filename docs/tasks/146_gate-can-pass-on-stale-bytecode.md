---
id: 146
slug: gate-can-pass-on-stale-bytecode
title: '`scripts/gate.sh` can report GREEN against bytecode that is not the source on disk'
phase: 3
milestone: Measure
status: done
depends_on: []
---

## Why this exists

A `.pyc` records the source's **mtime in whole seconds** and its size, both 4 bytes. CPython treats
the cached bytecode as valid when both still match. So a source edit that lands **in the same second
as the previous import and leaves the file the same length** is invisible: the next interpreter
imports the stale bytecode and never looks at the changed bytes.

`scripts/gate.sh` is not a convenience script — AGENTS.md says *"Only `GATE GREEN` counts"*, and
GitHub Actions cannot run for this repo, so that line is the whole verification story. A GREEN taken
against bytecode that is not the source on disk is a false pass of exactly the kind R6.5 exists to
prevent: a check that reports on something other than what it claims to have checked.

The trigger is narrow for a human typing in an editor. It is **not** narrow for the workflow this
repo is built around: an agent that scripts a sequence of edits, re-running the suite between them,
routinely rewrites a file to the same length within the same second — flipping a version constant,
reverting a one-character fix to confirm a test is red-first, toggling a flag.

Provenance: hit during the review of [#170](https://github.com/cuongdinhngo/code-atlas/pull/170), on
2026-08-24, while verifying that a version bump reddens the conformance suite. `ARTIFACT_VERSION`
read `1` on disk and `2` at runtime in the same process, for two minutes, before the cause was
found.

## What does not fix it

Recorded because both are the obvious first guesses and both are wrong — verified, not assumed:

- **`-B` / `PYTHONDONTWRITEBYTECODE=1` suppress only the *write*.** An existing stale `.pyc` is still
  read. Under both, an import of a source reading `V = 2` still yielded `1`.
- **`SOURCE_DATE_EPOCH` does not reach the import path.** It changes `py_compile` / `compileall`
  defaults; bytecode the interpreter writes on import stays timestamp-based (header flags `0`).
- **`compileall --invalidation-mode checked-hash` without `-f` converts nothing.** It skips every
  file whose cached bytecode it already considers current — which is all of them — so the tree stays
  timestamp-based and the stale read still happens. `--force` is not an optimisation knob here; it
  is what makes the step do its job.

## Scope

Convert the tree's bytecode to **checked-hash** invalidation (PEP 552), which validates by hashing
the source and so cannot be fooled by an mtime or size collision:

```sh
python -m compileall -q -f --invalidation-mode checked-hash code_atlas onboarding_llm tests
```

Two properties make this the right shape rather than a bigger hammer:

- **It is durable.** When a source really changes, CPython rewrites the `.pyc` and **preserves** the
  invalidation mode (header flags `3` after the rewrite). Converting once keeps the tree converted.
- **It protects the whole loop, not just the gate.** Bare `pytest`, an ad-hoc probe script and the
  gate all read the same cache, so the fix reaches every one of them. Only a brand-new file starts
  timestamp-based, which is why the step belongs in a script that runs regularly rather than in a
  one-off command.

Measured cost: **0.23 s** to force-recompile all 195 files, against a ~100 s gate.

## Acceptance criteria

- **AC1** The step runs in `scripts/gate.sh` before anything imports the tree, and is a **counted**
  check in the summary — not a silent side effect (R6.5: a gate names what it did).
- **AC2** `.github/workflows/ci.yml` carries the same step. A check in one and not the other means
  one of them is lying about what was verified (AGENTS.md). Its value there is insurance only — a
  fresh checkout has no bytecode to be stale.
- **AC3** The assumption the fix rests on is asserted, not believed: a checked-hash `.pyc` survives
  an import-time rewrite as checked-hash. If a future CPython stops preserving the mode, this goes
  red rather than the protection silently lapsing.
- **AC4** The hazard itself is pinned: a same-second, same-size edit under timestamp invalidation
  yields a stale import, and the same edit under checked-hash does not.

## Out of scope

- **Deleting `__pycache__` on every gate run.** It works, costs a full recompile each time, and
  protects only the gate — the next bare `pytest` is unguarded again.
- **Making the repo's determinism gates (R4.2) care about bytecode.** They compare emitted rows, not
  how the interpreter cached itself; nothing there is affected.
- **Any change to how tests are collected or run.**

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->
<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review/challenger waived)
- **Branch:** `chore/146-gate-can-pass-on-stale-bytecode`
- **CHALLENGER:** OFF
- **work_doc_mode:** embed
- **TIER:** full · **SCOPE:** S

## Design

- One counted `_run` step at the head of gate.sh's test job, before the entry-point check imports
  `code_atlas.main`; the same step in ci.yml to keep the two in step.
- `tests/test_bytecode_invalidation.py` proves the mechanism in `tmp_path` subprocesses rather than
  asserting the repo's own `__pycache__`, which is gitignored and absent on a fresh checkout.

## Requirements matrix

| ID | Ph3 | Ph4 | Notes |
|---|---|---|---|
| AC1 | ✅ | waived | `test_ac1_the_gate_converts_bytecode_before_it_imports_the_tree` |
| AC2 | ✅ | waived | `test_ac2_ci_carries_the_same_step_as_the_gate` |
| AC3 | ✅ | waived | `test_ac3_a_checked_hash_pyc_stays_checked_hash_when_the_import_rewrites_it` |
| AC4 | ✅ | waived | the hazard and its absence, both pinned |

## Cost ledger

| phase | dispatch | tokens |
|---|---|---|
| execute | main loop | unmeasured (host does not surface usage; review/challenger waived) |

## What the measurement got wrong first

The first timing said 0.14 s warm and looked free. It was measuring a no-op: without `-f`,
`compileall` skips every file whose cache it considers current, so nothing was converted. The
number only became real once `-f` was added — and the test that caught it is the one that matters,
`test_ac4_checked_hash_reads_the_source_that_is_on_disk`, which stayed red under the `-f`-less
command. Recorded because the failure mode is the ticket's own: a step that runs, reports success,
and did not do the thing.
