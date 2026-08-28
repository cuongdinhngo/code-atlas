---
id: 190
slug: a-same-second-guard-is-flaky-under-suite-load
title: '`test_ac4_a_same_second_same_size_edit_is_a_stale_import` needs two writes inside one wall-clock second and flakes under full-suite load'
phase: 1.5b
milestone: Coverage
status: done
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

## Session status

- **KEY:** 190 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, ticket 3 of 3: 188 → 189 → 190) · envelope in `.mango/run-contract-190.txt`.
- **Branch:** `fix/190-a-same-second-guard-is-flaky` (off `main` at `f36f6a7`, which carries 188 and 189)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2475 passed, 0 failed` at `f36f6a7` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

1. How to construct the premise without mocking the hazard (R6.5) → read the `.pyc`'s **own**
   recorded mtime and set the source back to it.
2. AC2's *"20 consecutive full-suite runs, or the flake is otherwise shown to be gone"* → **the
   second branch**, and the reason is in *AC2's evidence* below.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** S · **TIER:** full

`PREMISE: 2 reference(s) checked | 0 missing | 0 ambiguous`
`RECALL: 2 claim(s) surfaced | 1 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=4`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §R4.2 (change-type) ✅ · §R6.3 (change-type) ✅ — it found the third double-writer · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.8 (change-type) ✅ · §R7.2 (change-type) ✅ · §R7.6 (change-type) ✅`
`BASELINE: green — 2475 passed, 0 failed, 0 skipped at f36f6a7 (bare pytest, Linux host)`

**Premise:** the citations resolve and the diagnosis is exactly right. Seen twice in one batch (175,
then 182): green alone, green on a re-run, red once inside a full `pytest -q`, always with the same
message — *"if this reads 2, CPython changed and 146 can be dropped"*.

**Recall:** `prove-the-guard-fails` (R6.5, by handle) — the handle this ticket is a case of, from the
other side. `_pyc_flags` (by symbol): the file already reads the `.pyc` header, so the mtime word is
two slices away.

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | the guard fails because the machine was slow, not because the hazard went | construct the premise | 175/182 sightings | open |
| R1 | Scope 1 | set both files' mtime explicitly so the premise is constructed | against the **pyc's own** recorded value | `_pyc_source_stamp` | open |
| R2 | Scope 2 | keep the escape hatch the assertion message names | it is the last assertion, and reachable | see AC3 | open |
| R3 | Scope 3 | check the sibling tests for the same race | **three** double-writers, not two | see below | open |
| AC1 | AC 1 | the premise is set explicitly and asserted before the import | Falsifiable: two premise asserts | red run 1 + 2 | open |
| AC2 | AC 2 | 20 consecutive full-suite runs, or the flake shown gone | **branch 2**, with the trigger pinned | see evidence | open |
| AC3 | AC 3 | the "CPython changed" hatch still fires | Falsifiable: positive control in the suite | see AC3 | open |
| AC4 | AC 4 | siblings checked for the same race, fixed or cleared | all three pinned | proving test ×3 | open |
| C1 | Constraint | R6.5 — a deterministic premise must not become a mock of the hazard | real file, real importer decision | — | binding |
| C2 | Constraint | R4.2 — no wall-clock dependence left in the assertion path | no `sleep`, no clock read | — | binding |

### Root cause (taxonomy: concurrency)

**The test created the condition it was testing for, by racing.** 146's hazard is *"the source moved
inside the second the `.pyc` recorded, at the same length"* — a state, not an event. The test tried to
reach that state by writing twice quickly, which makes it a function of scheduler luck. Under load
the second write landed in the next second, CPython **correctly** recompiled, and the assertion that
fired was the one whose message says the interpreter changed. **So the failure was true, the message
was false, and the two were indistinguishable from the outside.**

### Blast radius

`tests/test_bytecode_invalidation.py` only. No production code, no gate change (`--invalidation-mode
checked-hash` is out of scope and untouched).

## Phase 2 — design

### Construct the premise from the `.pyc`'s own header, not from a clock

The file already unpacks the PEP 552 header for its flags word. A **timestamp** `.pyc` stores the two
invalidation inputs in the next two words: the source mtime in whole seconds, and the source size.
So the premise is readable, not guessable:

```python
_MTIME_WORD = slice(8, 12)   # source mtime, whole seconds
_SIZE_WORD  = slice(12, 16)  # source size
```

`_pyc_source_stamp()` returns both; `_stamp_source()` sets the source's mtime back to the recorded
second with `os.utime`. Then the premise is **asserted**, in its two halves, before the import:

```python
assert int(module.stat().st_mtime) == stamped_mtime, "the same-second half of the premise"
assert module.stat().st_size == stamped_size, "the same-size half of the premise"
```

**This is not a mock (C1).** The file on disk really has that mtime, the importer really reads it,
and the importer really makes its own decision. What is removed is the coin toss over *which second
the second write landed in* — and note the pin is against the value the `.pyc` itself recorded, not
against a value the test invented, so it cannot drift from what the importer will compare.

### The flake's own trigger becomes a named test, which is what "shown to be gone" means

`test_a_write_that_straddles_a_second_is_why_the_old_guard_flaked` sets the mtime one second **past**
the recorded value and asserts the import reads `2`. That is precisely what a loaded run used to
produce at random. Both outcomes are now selected by an explicit integer, so the two cases are a
parameter rather than a probability — and the reason the old failure message was wrong is now stated
in the suite instead of in a task file.

### Scope 3 found a third double-writer, and a second reason to pin

The ticket names two tests. There are **three** that write twice, and the two siblings had a
different problem from the hazard test — not a flake, a **begged question** (R6.3):

- `test_ac4_checked_hash_reads_the_source_that_is_on_disk` asserts the source wins *because the pyc
  is hashed*. On a straddled second, a **timestamp** pyc would also have recompiled, so the test
  could pass without the hash doing anything. Pinning the mtime back removes the alternative
  explanation, and `_pyc_flags(...) & _HASH_BASED` is now asserted alongside it.
- `test_ac3_a_checked_hash_pyc_stays_checked_hash_when_the_import_rewrites_it` has the same exposure
  for its rewrite step; same pin, same reason.

So AC4's answer is *fixed*, not *cleared* — and the fix strengthens two assertions rather than only
stabilising them.

### AC3: the hatch still fires, and its positive control is already in the suite

The *"CPython changed and 146 can be dropped"* assertion is the last claim in the test, reached only
once both premise halves hold. Its positive control is the sibling immediately below it: **the same
constructed premise, a hash-based `.pyc`, and the import reads `2`.** If timestamp invalidation ever
began catching a same-second same-size edit, the hazard test would reach its final line with the
premise intact and fail with exactly that message. Demonstrating it any other way would need a
patched importer, which C1 forbids.

### Rejected

- **`time.sleep` to force a same-second window** — trades a race for a slower race, and leaves a
  clock in the assertion path (R4.2).
- **`pytest.mark.flaky` / a retry** — makes the message rarer, not truer; the failure was real.
- **Skipping the test when the writes straddle** — a guard that skips itself under load is a guard
  that is absent exactly when the suite is busiest.
- **Asserting on an invented mtime constant** — it could drift from what the `.pyc` recorded; reading
  the header keeps one source of truth.
- **Changing `tests/test_impact.seed_file`-style helpers or `scripts/gate.sh`** — out of scope.

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **Exclusion 1 (AC2 taken on its second branch):** 20 consecutive full-suite runs were **not** run;
  the evidence below is a pinned trigger plus 60 loaded repeats and 3 full suites. Expiry: the next
  time this test is seen red on any host — the sighting count is in this ticket, and a third sighting
  would mean the structural argument is wrong.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Premise read from the `.pyc`'s own header, set with `os.utime` | implemented-as-approved |
| Both premise halves asserted before the import | implemented-as-approved |
| The straddle pinned as a deliberate case | implemented-as-approved |
| All **three** double-writers pinned, two of them strengthened (R6.3) | implemented-as-approved |
| No `sleep`, no mock, no retry marker | implemented-as-approved |
| `scripts/gate.sh` and 146's fix untouched | implemented-as-approved |

### Red runs (R6.5) — and the point is *which line* fails

1. **Premise deliberately broken** (`stamped_mtime + 1` in the hazard test):
   `AssertionError: the same-second half of the premise / assert 1787930091 == 1787930090`.
2. **Same-size half broken** (`"V = 22\n"`, mtime pinned):
   `AssertionError: the same-size half of the premise`.

**Both fail on the premise, naming which half went**, instead of on the *"CPython changed"* line.
That difference is the whole ticket: the old test could only report a broken premise as an
interpreter change.

### AC2's evidence, and why it is the second branch

AC2 offers *"20 consecutive full-suite runs, **or** the flake is otherwise shown to be gone."* Taken
on the second branch, deliberately: **20 samples of a probabilistic event is weaker evidence than one
test that constructs both outcomes**, and it would not distinguish "fixed" from "unlucky twenty
times in a row". What was run instead:

| Evidence | Result |
|---|---|
| the straddle pinned as its own test (the flake's exact trigger) | passes, and fails if the mtime pin is removed |
| 60 repeats of the file under 8 spinning CPU loads | **0 failures** |
| 3 consecutive full suites, **default random order** (not `-p no:randomly`) | `2476 passed` ×3 |
| `scripts/gate.sh` | `GATE GREEN — all 15 checks passed` |

The loaded repeats matter more than the count: the flake's cause was scheduler pressure between two
writes, so saturating the host is the condition that used to produce it.

### Empirical outputs

| Measure | Before | After |
|---|---|---|
| what selects "same second" | scheduler luck between two writes | an explicit `os.utime` from the `.pyc` header |
| assertions before the import | 2 (content, flags) | **4** (content, flags, same-second, same-size) |
| line that fails when the premise breaks | *"CPython changed"* | *"the same-second/same-size half of the premise"* |
| tests in the file | 5 | **6** |
| double-writers left racing | 3 | **0** |
| sightings of the flake | 2 (175, 182) | 0 in 60 loaded repeats + 3 full suites |

**Verification coverage:** 4 AC, all 4 covered — 1 new test, 3 existing tests pinned (2 of them
strengthened against a begged question). AC2 covered on its second branch, with the substitution
recorded as an exclusion.

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2475 passed / 0 failed` at `f36f6a7` →
`2476 passed / 0 failed`, three times in a row under the default random order. ruff + mypy green.
`scripts/gate.sh` → `GATE GREEN — all 15 checks passed`.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen >= 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `prove-the-guard-fails` (R6.5) gains 190 → 25, from the **other** side: not *"was the guard seen
  failing?"* but *"did it fail for the thing it forbids?"*.
- `fixture-shape-begs-the-question` (R6.3) gains 190 → 10: two siblings could have passed without the
  hash doing any work.
- **New:** `190-C1` (type-2, `construct-the-premise-do-not-race-for-it`). seen=1.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. Self-checks: the
premise pinned against the `.pyc`'s **own** recorded value rather than an invented constant, so it
cannot drift from what the importer compares; the flake's trigger promoted from a hazard to a named
test, which is what makes "shown to be gone" checkable; Scope 3's sweep found a **third** double
writer and a second defect class in the two siblings (a begged question, not a race), so AC4 is
*fixed* rather than *cleared*; AC2's literal 20 runs declined with the reason stated and recorded as
an exclusion with a checkable expiry; two red runs whose value is *which line* fails; and no mock, no
sleep, no retry marker anywhere near the assertion path.
