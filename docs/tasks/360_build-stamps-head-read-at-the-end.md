---
id: 360
slug: build-stamps-head-read-at-the-end
title: 'A build stamps the HEAD it reads at the end, so a HEAD move mid-build leaves an index that says current but is not'
phase: 2
milestone: Freshness
status: done
depends_on: [053, 166]
---

## Why this exists

`_record_meta` (`code_atlas/indexer.py:1396`) reads `gitutil.head_commit_and_ref` once parsing is
done and stores that SHA as `last_commit`. The diff an incremental parses is taken earlier
(`code_atlas/tools/build_or_update_index.py:329`, `changed_paths(root, last)`), and a full build collects the tree
earlier still. If HEAD moves in between, the index stamps a commit whose changes it never parsed.

Seen 2026-10-01 on the anchor repo (~23k files):

| Time (+07) | Event |
|---|---|
| 14:19:41 | session-start build takes `write.lock` at HEAD `48b2089` |
| 14:19:57 | `git pull --ff-only` moves HEAD to `03420e7` (17 commits, 25 files added); `post-merge` refresh finds the lock held and skips (357) |
| after | the build finishes and stamps `last_commit = 03420e7` |

The result is worse than 357's "behind":

- `get_index_status` reports `current @ 03420e7`, while file and symbol counts match `48b2089`
  exactly.
- `file_outline` on a file added in that range answers `found: false`, `reason` ok.
- 035's read-through cannot repair it: `code_atlas/tools/freshness.py:184` diffs `last_commit..HEAD`, which is now
  empty.
- `code-atlas-build` (incremental) exits 3 with `0 file(s)`. Only `--full` recovers.

357 assumes a dropped refresh leaves the index honestly `behind`. Because of this stamp, it can
leave it falsely `current` instead, so fixing 357 alone does not close the gap.

## Scope

1. Capture HEAD (SHA and ref) once, before the build reads the tree or the diff, and stamp that
   value. No second HEAD read feeds `last_commit`.
2. An incremental diffs against the captured SHA, never HEAD. `gitutil.changed_paths` reads HEAD
   twice (`since..HEAD` and the working tree vs `HEAD`, `gitutil.py:82-86`), so both reads must go.
   A single `git diff --name-only <since>` (working tree vs `since`) covers both without either.
3. When HEAD at publish time differs from the captured SHA, the index is `behind` against it, and
   nothing extra is needed for the state line to say so. 357's pending marker (or the next refresh)
   catches it up.
4. **Stamp old, never new.** The parse reads the working tree, not git objects, so a pull mid-parse
   leaves some files newer than the captured SHA. That is safe: the next incremental re-parses them,
   and re-parsing is idempotent. A stamp newer than the parsed content loses changes; this one only
   costs work.
5. The captured value reaches `_record_meta` as a parameter from both of its callers
   (`indexer.py:296` and `:600`, via `full_build` and `incremental_update`); `_record_meta` no
   longer calls `gitutil`. Design lists every caller of both, so no path keeps a HEAD re-read.

**Out of scope:** detecting an index already stamped falsely `current`. It cannot be told apart
cheaply, so the CHANGELOG entry tells an affected index to run `--full` once.

## Acceptance criteria

- **AC1 (proving test):** a build that HEAD moves past mid-parse (the test commits a new indexable
  file from the existing `progress=` callback; no production hook is added) ends with `last_commit` equal to the pre-move SHA,
  `staleness: behind`, and an incremental that then parses the new file.
- **AC2:** the incremental path is covered the same way: the diff and the stamp name the same SHA.
- **AC3:** with HEAD unchanged during the build, `last_commit` and every existing freshness test are
  unchanged.
- **AC4:** after AC1's build, 035's read-through answers `file_outline` on the new file with
  `found: true`, with no rebuild in between.
- **AC5:** an uncommitted edit made during the build is still seen by the next incremental (Scope 2's
  single diff keeps the working-tree half).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 360 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews and merges the PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`, batch 360 → 357 → 358 → 359;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `fix/360-build-stamps-head-read-at-the-end` off `main` (`41ba7996`). Contract `.mango/run-contract-360.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 9 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 0 want-decision asked | 7 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** All nine resolve on `41ba7996`: `_record_meta` (`indexer.py:1321`, the HEAD read at
`:1396`), `gitutil.head_commit_and_ref` (`gitutil.py:58`), `changed_paths` (`gitutil.py:74`, the two
HEAD reads at `:82`/`:85`), `build_or_update_index.py:329`, `freshness.py:184`, the two
`_record_meta` callers (`indexer.py:296`, `:600`), `full_build` (`:198`), `incremental_update` (`:395`).

**Recall (by handle — the change threads a value through callers).** `343-C2`
`formatter-rewrites-untouched-lines`; `356-C1` `child-build-inherits-adapter-env`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 47,932 tokens) surfaced X1–X3; H1–H4 are
the run's own. None is a want-decision: every one is answered by the ticket's Scope or the code.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where HEAD is captured | how | once, at the top of `build_or_update_index._run`, before the diff; passed to `full_build` / `incremental_update` → `_record_meta` (Scope 1, 5) |
| H2 | `freshness.dirty_indexed_paths` shares `changed_paths` | how | it moves with it: `git diff <since>` (since vs working tree) answers the same question the union did, without reading HEAD (`freshness.py:178` docstring: "both a `git pull` and an uncommitted edit are seen") |
| H3 | the three escalations inside `incremental_update` | how | pass the incremental's captured head to `full_build` (Scope 5: "no path keeps a HEAD re-read") |
| H4 | direct callers that pass no head (`scripts/scale_full_build.py:70`, `tokens_to_answer.py:891`, `cross_repo_validate.py:249`, `profile_incremental.py:112,157`, tests) | how | `head` defaults to `None` = capture at entry, before the tree walk — one read, not a re-read; an explicit `(None, None)` keeps today's delete branch (`indexer.py:1397-1405`) |
| X1 | the dispatcher's `gitutil.head_commit(...) is None` gate (`build_or_update_index.py:325`) is a second HEAD read | how | reuse the captured SHA for that gate (Scope 1) |
| X2 | "not supplied" vs "git cannot answer" | how | sentinel `None` vs `(None, None)`; the delete branch is AC3 behaviour (`indexer.py:1397-1405`) |
| X3 | `changed_paths` failure semantics | how | one command, so one failure: unreachable `since` → `None` → full build, as `since..HEAD` failing did; the old dirty-only tolerance (`gitutil.py:86`) goes with the second command |

## Phase 1 — analysis

`PREMISE: 9 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (title, Why this exists, Scope, Acceptance criteria) | 4 decomposed | ROWS: C=2 R=5 G=1 AC=5`
`CLARIFICATION: 7 raised | 7 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### BASELINE

`main` at `41ba7996` (the merge of #26): CI run 36876561135 concluded `success` on that SHA. Per SG-2
that run is not pasted as a `$` evidence block. Ran at 41ba7996.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | title / Why | "an index that says current but is not" | a HEAD move mid-build never leaves `last_commit` naming changes the build did not parse | ✅ |
| C1 | Scope 4 | "Stamp old, never new" | the stamp is read before the tree and the diff | ✅ |
| C2 | Out of scope | CHANGELOG tells an affected index to run `--full` once | no detection of an already-false stamp | ✅ |
| R1 | Scope 1 | capture HEAD once, before the tree or diff | `_run` captures; no second read feeds `last_commit` | ✅ |
| R2 | Scope 2 | incremental diffs against the captured SHA, never HEAD | `changed_paths` = `git diff --name-only <since>` | ✅ |
| R3 | Scope 3 | HEAD at publish ≠ captured → `behind` | existing state line; nothing added | ✅ |
| R4 | Scope 4 | files newer than the stamp are re-parsed next time | idempotent re-parse | ✅ |
| R5 | Scope 5 | `_record_meta` takes the value; no `gitutil` call | both callers pass it | ✅ |
| AC1 | AC | mid-parse HEAD move → pre-move stamp, `behind`, next incremental parses the new file | tool-level test | ✅ |
| AC2 | AC | incremental: diff and stamp name the same SHA | tool-level test | ✅ |
| AC3 | AC | HEAD unchanged → stamp + freshness tests unchanged | existing suites | ✅ |
| AC4 | AC | read-through answers `file_outline` on the new file, no rebuild | tool-level test | ✅ |
| AC5 | AC | an uncommitted edit during the build is seen by the next incremental | tool-level test | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `last_commit == pre-move SHA`, `staleness == behind`, the next incremental's report `files ≥ 1` and the new file's node present | the commit happens inside the `parse` progress tick (no production hook) |
| AC2 | yes — after an incremental HEAD moved past, `last_commit == pre-move SHA` and the next incremental parses the moved file | |
| AC3 | yes — the existing freshness / staleness / incremental suites stay green | |
| AC4 | yes — `file_outline(new)` → `found: true` with no build between | |
| AC5 | yes — a working-tree edit made in the parse tick appears in the next incremental's parsed set | |

### Gap analysis (enhancement)

- **Now.** `_record_meta` reads HEAD after the late writes (`indexer.py:1396`); `changed_paths` diffs
  `since..HEAD` and `HEAD` vs the tree (`gitutil.py:82,85`) at a different moment; `_run` gates on a
  third read (`build_or_update_index.py:325`).
- **Target.** One read, before the tree walk and the diff, threaded to the stamp.

### Blast radius

- `_record_meta` callers: `indexer.py:296` (`_fill`), `:600` (`incremental_update`) — 2/2.
- `full_build` callers: `build_or_update_index._run` ×3, `incremental_update` escalations ×3,
  scripts ×3 (default capture), tests (default capture).
- `incremental_update` callers: `_run`, `scripts/profile_incremental.py` ×2, tests (default capture).
- `changed_paths` callers: `_run`, `freshness.dirty_indexed_paths` — 2/2.
- Docs: `CHANGELOG.md` (C2). No PLAN/AGENTS line states the old read order (`grep -n "head_commit_and_ref\|last_commit" docs/PLAN.md AGENTS.md` names none that this changes).

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ no language branch: the captured head is a language-free tuple, §R1.4 (change-type) ✅ git reads stay in gitutil.py and the stamp stays in indexer.py, §R4.2 (change-type) ✅ with HEAD unchanged the stamp is the same SHA (AC3), §R6.5 (change-type) ✅ AC1/AC2/AC4 are seen red on 41ba7996 before the fix, §R6.8 (change-type) ✅ the HEAD move is exhibited by a real commit inside the build, §R7.5 (change-type) ✅ every new comment ≤ 3 lines`

## Phase 2 — design

### Approach

1. **`gitutil.changed_paths`** runs one `git diff --name-only -z <since>` (since vs the working tree,
   staged and unstaged). No HEAD read. `None` when git cannot answer (X3).
2. **`indexer`**: `full_build` and `incremental_update` take `head: GitHead | None = None` (`GitHead =
   tuple[str | None, str | None]`); `None` captures at entry, before any tree read (H4). The
   incremental's three escalations pass their head on (H3). `_record_meta` takes `head` and no
   longer imports `gitutil` for it (R5).
3. **`build_or_update_index._run`** captures `head` once, first; the "no commit" gate reads
   `head[0]` (X1); every `full_build` / `incremental_update` call receives it.
4. **`CHANGELOG.md`**: an `Unreleased` entry — an index whose `last_commit` was stamped across a HEAD
   move reads `current` falsely; run `code-atlas-build --full` once.

### Rejected alternatives

- **Re-read HEAD at publish and refuse to stamp when it moved.** Leaves `last_commit` unset or old
  anyway, and adds the second read the ticket forbids.
- **Make `head` required on `incremental_update`.** Forces 17 test modules and a script to change for
  a race only a production caller can meet; the default capture is still taken before the tree walk.
- **Diff `since..<captured>` plus the working tree.** Two commands again; `git diff <since>` already
  covers both halves (Scope 2).

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | `git diff --name-only <since>` lists committed-since and uncommitted changes together | verified — git docs ("changes between the working tree and the named commit"), and AC5's test |
| S2 | 035's read-through repairs a file absent from the index | to verify — AC4's test |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | single-diff `changed_paths` | `code_atlas/gitutil.py` | `_run`, `freshness.dirty_indexed_paths` | R2, AC5 | 1/1 |
| 2 | `head` threaded; `_record_meta` stops reading git | `code_atlas/indexer.py` | every `full_build` / `incremental_update` caller (default keeps them) | R1, R5, C1 | 1/1 |
| 3 | capture once in `_run` | `code_atlas/tools/build_or_update_index.py` | the build tool and `code-atlas-build` / refresh (both go through `_run`) | R1, X1 | 1/1 |
| 4 | proving tests | `tests/test_build_stamps_the_head_it_read_first.py` (new) | — | AC1, AC2, AC4, AC5 | 1/1 |
| 5 | CHANGELOG entry | `CHANGELOG.md` | `tests/test_release_discipline.py` reads only `## <ver> — <date> · …` headings | C2 | 1/1 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `tests/test_backlog_bookkeeping.py` | — | 4/4 |

`HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced in Phase 3 with `ruff format --diff` over the
  edited files; only hunks on changed lines are applied.
- **`child-build-inherits-adapter-env`** — does not apply because the new tests build in-process
  through the tool; no child build is spawned.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | the build tool (`_run`) over a real git repo; a real `git commit` inside the `parse` progress tick; `get_index_status` state; a second tool call | n/a | ✅ |
| AC2 | integration | same, on an incremental | n/a | ✅ |
| AC3 | integration | existing freshness / staleness / incremental suites | n/a | ✅ |
| AC4 | integration | `file_outline` tool on the new file after AC1's build | n/a | ✅ |
| AC5 | integration | a working-tree edit in the tick; the next incremental parses it | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_build_stamps_the_head_it_read_first.py`. It fails on
`41ba7996` (the stamp names the post-move SHA and the next incremental parses nothing) and passes
after the change.

### Rollback

`git revert` the branch commits. No index changes shape.

## Phase 3 — execute

Commits on `fix/360-build-stamps-head-read-at-the-end`: `7b82715a` (the change), `2aec8051` (the
challenger's findings 3 and 5).

**Proving test, red first.** On `41ba7996` plus the new test file only: 3 failed, 1 passed — AC1
(`last_commit` was the post-move SHA), AC2 (same, on the incremental), AC4 (`found: false`). AC5
passed before the change: it guards the working-tree half the single diff must keep, and is a
regression guard rather than a red-first proof.

**Sweep.**
- Axis 1 — file set. The diff is the change list plus two files the trace missed (D1, D2).
- Axis 2 — design conformance. Approach bullets 1–4 implemented as approved; D1 adds a fifth.
  `ruff check` and `mypy code_atlas` (96 files) clean.
- Handle `formatter-rewrites-untouched-lines`, traced. `ruff format --diff` over the edited files
  proposes eight hunks in `indexer.py` and two in `build_or_update_index.py` on lines this change
  does not own; none applied. One hunk sat on a changed line (the `incremental_update(...)` call in
  `_run`) and was applied.
- Targeted suites (`-k "fresh or stale or incremental or outline or build or refresh or git or killed
  or noop or delta or status"`): 470 passed, 1 skipped, on `7b82715a`.

**Deviations.**

| # | Approved | Shipped | Why |
|---|---|---|---|
| D1 | no `file_outline` change (S2 "to verify") | a path missing from `files` goes through `FreshnessGuard.ensure_miss(path)` before answering `found: false` (`file_outline.py:64`) | S2 was false: `file_outline` returned `found: false` for an unindexed path before any read-through ran, so the honest stamp alone could not pass AC4. A clean, never-indexed path still answers as before (test added in `2aec8051`) |
| D2 | blast radius: "no PLAN line states the old read order" | PLAN §8.3's diff sentence rewritten | the grep missed `last_commit..HEAD` in §8.3; the sentence described the two-read union this change removes |

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `7b82715a`, 52,669 tokens): 11 met · 0 not met · 0 can't
tell.** It ran 35 targeted tests read-only in place. Its findings, and what happened to each:

1. No HEAD read still feeds `last_commit` — no action.
2. A `head=None` default on `incremental_update` after a caller-side diff would re-open the race;
   only scripts and tests take the default. **Left:** the docstring states the rule, and the
   Rejected alternatives record why `head` is not required.
3. `file_outline` behaviour change (D1). **Fixed:** a test pins that a never-indexed path in a clean
   repo still answers `found: false`.
4. The `incremental_update` call reflow in `_run` — the formatter's form for a changed line. **Kept.**
5. PLAN §8.3 ran one sentence onto a long line. **Fixed:** rewrapped.
6. `behind` depends on the state line comparing the stamp to live HEAD — confirmed by AC1. No action.

The fixes stay inside the reviewed files plus one test, so the verify ran in the main loop with no
re-dispatch: 5 passed (`tests/test_build_stamps_the_head_it_read_first.py`) on `2aec8051`.

`Ph3/4 proven by`: G1, C1, C2, R1–R5, AC1–AC5 — 13/13.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 2aec8051 — the diff `main..2aec8051`. Working doc:
`docs/tasks/360_build-stamps-head-read-at-the-end.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `2aec8051` only bookkeeping changed — this doc, `docs/BACKLOG.md` (the row
closed), `docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`, all exempt.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

`360-C1` is type 2 (process), handle `confirm-the-blocked-path-runs`: the ticket said read-through
"cannot repair" because its diff was empty, and the design took the diff as the only blocker; the
tool never reached read-through for that path at all (D1). Recorded in `docs/LESSONS.md` as a first
sighting. Per P1, `343-C2`'s `seen:` gains 360 (the formatter handle was traced).

### Outward actions

1. Push `fix/360-build-stamps-head-read-at-the-end` — pre-authorised.
2. Open the PR — pre-authorised.

Deferred to the maintainer: the merge; cutting a release for the `Unreleased` CHANGELOG entry.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 47,932 |
| 2 | review | `challenger`, round 1 | 52,669 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 100,601 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits. No index changes shape.
