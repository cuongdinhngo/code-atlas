---
id: 082
slug: claims-nobody-outside-can-check
title: 'Two claims a field evaluator could not check: what `files` counts, and whether a busy build ever says so'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [068, 072, 028]
---

## Goal
Round 4 tried to verify two shipped fixes from the outside and could verify neither — not because they
are broken, but because nothing in the surface makes them checkable. **Part A:** `get_index_status`
publishes `files` / `parsed` / `failed` with no denominator, so 068's one-row correction is
unauditable. **Part B:** the evaluator could not make a build lose a race, so 072's `mode: "busy"` has
never been observed in the field. A fix that cannot be checked by its user is indistinguishable from a
fix that was not made — and this project's own history (round 2's stale server process, 060's
reproduced-then-refuted mismatch) is a record of what that costs.

## Part A — `files: 18,888` against a tree of 28,425 PHP files
- Round 4, §A.4: `files: 18,888` while `git ls-files '*.php'` = **28,425** (on-disk, excluding
  `vendor`/`node_modules`/worktrees: 28,427; adding `.inc`/`.phtml`: 28,442). The 9,537-file gap is
  presumably ignore rules and inclusion policy doing their job — but nothing in the payload discloses
  which policy produced 18,888, so a **±1** synthetic-bookmark drift is invisible from outside.
- The evaluator's verdict was **NOT EXERCISED**, with the honest reason: *"I cannot distinguish 18,888
  from 18,889 without knowing the denominator."* 068 was caught in round 3 precisely by two of our own
  numbers disagreeing by one; after the fix there is no way for an outsider to confirm it.
- Note the shape: this is the same class as 051 (a number that did not describe the thing it named) and
  058 (a count with no way to enumerate what it counted). 058's answer — publish the paths — is the
  precedent.
- **Deliverable:** publish the denominator. Collected vs kept vs indexed, the suffixes in force, and
  the skip counts by cause (ignore rule, suffix, size, unreadable), on the verbose status path where
  058 already put `parse_failures`. An outsider must be able to reconcile `files` against their own
  `git ls-files` without reading code-atlas source.

## Part B — five builds, zero `mode: "busy"`
- Round 4, §A.8: the evaluator ran a background loop hammering `code-atlas-poke` across four files and
  called `build_or_update_index` into it; the build won cleanly
  (`"mode":"incremental","wrote":{"files":4,…},"seconds":57.997`). Across five builds it never saw the
  refusal, and reported — correctly — that *"I cannot report the fix as working on the strength of
  never having lost a race."*
- **Correction to the retro's reasoning, verified in this repo:** it concluded no second builder is
  reachable because the console script starts the stdio server and `code-atlas-poke` reparses a single
  file. There is a third entry point — **`code-atlas-refresh`** (053) — which runs *the same path as*
  `build_or_update_index(full=false)` and already prints `skipped: another build is running`. So the
  race **is** reachable from the CLI; the surface simply does not tell an evaluator that, and the tool
  descriptions do not mention it. The finding stands, its cause moves: this is a documentation and
  affordance gap, not a missing capability.
- **Deliverable:** make the busy path observably testable. Document the `code-atlas-refresh` race
  recipe in the parallel-agents runbook, and add a supported way to exercise the refusal (a long-held
  build in the test suite already does this; what is missing is an operator-facing recipe with an
  expected payload beside it). Then have the next field round confirm the payload, not just the
  timings.

## Scope / Deliverables
- Part A: denominator fields on verbose `get_index_status`, with the skip causes counted; the
  bookmark's exclusion becomes checkable arithmetic rather than a claim.
- Part B: a documented, reproducible way for a user to see `mode: "busy"` with its staleness fields,
  plus the runbook line naming `code-atlas-refresh` as the second writer.
- **One line in each affected tool description** pointing at where the auditing data lives — the
  round-4 evidence is that agents read descriptions and do not read plans.
- Update 068 and 072 with pointers, so each records that its field verification is now possible.

## Constraints
- 061 — the denominator belongs on the **verbose** path; the default status payload must not grow.
- R4 — the skip counts are derived from the same walk that produces `files`, not a second traversal
  with its own answer; two ways to count is the defect, not the fix.
- R2 — no repo names in fixtures; the reconciliation test builds its own tree with known skips.
- Part B must not weaken the lock: exposing a way to *observe* contention is not a way to *create*
  corruption.

## Acceptance criteria
- Verbose `get_index_status` lets a reader reconcile `files` end to end: collected − skipped(by cause)
  = kept = `files`, proven by a fixture test where every term is asserted.
- With the rules channel on and off, the arithmetic still closes and the bookmark is visibly excluded
  (068's claim, now auditable).
- A documented recipe produces `mode: "busy"` with `performed: false` plus staleness fields, and a test
  pins that payload.
- 068 and 072 carry pointers here.

## References
Field retro round 4 §A.4 (`NOT EXERCISED`, the missing denominator), §A.8 (`NOT EXERCISED`, the race),
§11 item 3 (the pre-flight checks the wrong tense). Repo facts checked for this ticket:
`pyproject.toml:19-21` (three console scripts), `code_atlas/hooks/refresh.py:1-6,42-50` (`refresh`
runs the incremental path and reports a lost race). Related:
[068](068_rules-bookmark-counted-as-source-file.md) (the ±1 this makes auditable),
[072](072_busy-build-hides-staleness.md) (the refusal payload),
[058](058_list-parse-failures.md) (precedent: publish what a count counted),
[028](028_index-health-metrics.md) (the counters), [053](053_refresh-on-checkout-hook.md)
(`code-atlas-refresh`), [`runbooks/parallel-agents.md`](../runbooks/parallel-agents.md).
