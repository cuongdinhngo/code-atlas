---
id: 077
slug: index-cannot-name-the-revision-it-describes
title: 'The branch changed under a live session and `staleness: "current"` was true, correct, and useless'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [071, 047, 072]
---

## Goal
[071](071_answers-do-not-name-their-tree.md) made every answer name the *directory* it describes
(`index_root`). Round 4 found the same defect one level up: nothing names the *revision*. Mid-session
the main checkout was switched to an unrelated branch by another actor; the next incremental build
happily re-indexed onto it, and `get_index_status` then reported `staleness: "current"` with
`dirty_indexed_files: 0`. Both true. The index was perfectly current with a tree the agent had never
been reasoning about, and no payload anywhere carries a branch name — only commit SHAs. The only way
to notice is to have memorised the previous SHA and diff it yourself.

## Evidence (field retro round 4, 2026-08-10, §5 — a finding the questionnaire did not ask for)
- Session start, verbatim (`db_path` redacted):
  `"last_commit":"47668e3…","head_commit":"bf1e25b…","staleness":"behind"` — correct, and it did its
  job: it stopped a 3-agent fan-out until a rebuild had run.
- Mid-session, after an out-of-band branch switch, the build returned
  `"last_commit":"ba32412…","graph":{"files":18888,…}` and the following status:
  `{"last_commit":"ba32412…","staleness":"current","head_commit":"ba32412…","dirty_indexed_files":0}`.
- The evaluator's reading, quoted: *"an agent that recorded 'index current @ `bf1e25b`' earlier in a
  session, then reads 'current' later, is being told what it wants to hear."*
- This is one of the two round-4 findings that fell **outside** the fix-verification section, and the
  retro's §11 note stands: §A alone would have reported "10 of 12 verified, all good" and missed it.
- Related exposure the same session paid for by hand: three dispatched agents each ran in a
  `.worktrees/<slug>` while the server `cd`s to the main checkout, so every symbol answer they got
  described `main`. `index_root` would have let a careful agent notice; nothing made it notice. The
  evaluator wrote the warning into each agent's prompt manually.

## Why a SHA is not enough
A SHA answers "is the index current?" — a *sameness* question, and 047 already answers it correctly.
It cannot answer "current with **what**?", which is the question an agent actually holds, because the
agent reasons in branches and worktrees, not in hashes. Two failure shapes follow from the same gap:
a branch switch (same directory, different revision) and a rebase/reset (same branch name, different
history). Both currently render as `current`.

## Scope / Deliverables
- **Attach the revision's human name.** Add `head_ref` (the branch/ref name, or a detached-HEAD
  marker) beside `last_commit` / `head_commit` in `get_index_status`, and decide — explicitly — whether
  nav payloads carry it too or only `index_root`. Weigh against 061: this is one short string on a
  status call, and the field session shows it load-bearing.
- **Record the ref the index was built on**, not only the commit, so `staleness` can distinguish
  "behind on the same branch" from "current with a different branch than the last build".
- **Give the switch its own staleness word, or justify not doing so.** `current` after a ref change is
  the misleading case; a value that says "current, but this is not the tree your last answer came
  from" is the honest one. If the vocabulary stays as-is, the ticket must say why the name alone is
  enough.
- **Cover the worktree case in the same pass** — a server whose `index_root` differs from the caller's
  cwd is the routing half of this defect, and the runbook's mitigation (`CA_DB_PATH`) should be
  reachable from the payload's own fields.
- **Non-git repos and detached HEAD must degrade, never raise** (072's precedent: degrade to
  `unknown`).

## Constraints
- R4 — determinism: reading a ref name is a `git` read like the others in `gitutil`; identical repo
  state gives identical fields.
- R5.3 / 072 — never let a ref read make a status or build call fail.
- 061 — a field that means nothing must be omitted, not shipped empty; a detached HEAD is a value,
  not an omission.
- Do not re-model staleness: 047 owns which files count, and this ticket does not change that.

## Acceptance criteria
- `get_index_status` names the ref the index was built on and the ref HEAD is on now; a test switches
  branches between build and status and asserts the two differ.
- A branch switch with no file drift no longer reports a bare `staleness: "current"` — either the
  vocabulary distinguishes it or the payload names both refs so the difference is visible.
- Detached HEAD, a non-git directory, and a `git` failure each produce a defined value and no raise.
- The worktree mismatch case has a test and a runbook line pointing at the field that reveals it.

## References
Field retro round 4 §5 (the whole finding), §9 runner-up, §0.a, §A.7 (`index_root` verified on nav,
absent on build). Related: [071](071_answers-do-not-name-their-tree.md) (which *directory* — the
sibling this extends), [047](047_staleness-scoped-to-indexed-files.md) (what staleness counts),
[072](072_busy-build-hides-staleness.md) (degrade to `unknown`, never raise),
[053](053_refresh-on-checkout-hook.md) (the `post-checkout` refresh this makes auditable),
[`runbooks/parallel-agents.md`](../runbooks/parallel-agents.md).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 077 — index cannot name the revision it describes (working doc)

- **Ticket:** 077 · local `docs/tasks/077_index-cannot-name-the-revision-it-describes.md`
- **Type:** enhancement (agent-trust: name the revision)
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full (review **skipped** by invoke args)
- **BASELINE:** green — `1108 passed in 75.04s` (`.venv/bin/pytest -q`, 2026-08-12).
  <!-- baseline exclusions: none -->

---

## Phase 0 — Refine

`REFINE: 3 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 3 ASSUMED | skip: no`

**INPUT KIND:** ticket (single deliverable)

**Settled wants (want-decision).** _(none asked — handed-back via standing "best option / pass all gates"; see ASSUMED)_

**Resolved direction + citation (how-decision).**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Persist the build-time ref in meta beside `last_commit` | Add `last_ref` meta key; stamp in `_record_meta` when git can name a ref | ticket Scope L48–49; `indexer.py:704-711` |
| 2 | Detached HEAD is a value, not an omission | Emit abbrev-ref result `HEAD` (git's own detached marker via `rev-parse --abbrev-ref HEAD`) | ticket Constraints L64–65; 061 |
| 3 | Non-git / git failure degrade never raise | Return `None` for refs like other `gitutil` helpers; status/busy stay dicts | ticket Constraints L62–63; `gitutil.py:1-5`; 072 |
| 4 | Refs join the 072 busy / shared staleness trio | Extend `compute_staleness` (+ busy payload) so status↔busy stay one vocabulary; build *success* refs deferred to 079 fold-in | exposure-checker; 072 R1; ticket 079 L40–41 |

**ASSUMED (awaiting ratification).**

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses prior? |
|---|----------------|-------------|--------------------------|-----------------|
| 1 | Refs on **status + busy only**, not nav | 061 weight; nav already has `index_root` for directory mismatch; ticket asks decide | Gate 1 | no |
| 2 | **Keep** staleness vocab (`current`/`behind`/`unknown`); name **both** `last_ref` + `head_ref` so a switch is visible | Ticket Constraint "Do not re-model staleness"; AC allows either vocab OR dual-ref naming | Gate 1 | no |
| 3 | Both refs on **minimal** status (beside `last_commit`) so the cheap path still names the revision | AC requires naming both refs; switch visibility must not require `standard` | Gate 1 | no |

**Constraints surfaced from the scan:** R4.2 determinism; R5.3 soft-fail on data; 061 omit empty; 047 owns dirty file counts; 072 one vocabulary; 079 owns build-success `index_root`/ref fold-in.

**Exposure-checker** (challenger, 1 dispatch): found busy-trio join → classified as HOW #4 above. No further unexposed wants.

---

## Requirements matrix

`SECTIONS: 6 found (Goal, Evidence, Why SHA not enough, Scope/Deliverables, Constraints, Acceptance criteria) | 6 decomposed (Evidence + Why → context; Goal/Scope/Constraints/AC → rows) | ROWS: C=4 R=5 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "nothing names the *revision*… no payload anywhere carries a branch name" | Status (and shared busy vocab) must name the human ref for the indexed revision and for HEAD | ticket L11–18; status has only SHAs `get_index_status.py:146-157` | CL1–CL6 | | ✅ |
| R1 | Scope | "Add `head_ref` … beside `last_commit` / `head_commit` in `get_index_status`" | Emit `head_ref` (live HEAD ref) on status | no ref read in `gitutil.py` | CL1,CL3 | | ✅ |
| R2 | Scope | "Record the ref the index was built on, not only the commit" | Persist `last_ref` in meta at build; emit on status | `_record_meta` only stamps `last_commit` `indexer.py:704-711` | CL2,CL4 | | ✅ |
| R3 | Scope | "Give the switch its own staleness word, or justify not" | Keep vocab; dual-ref naming makes switch visible (ASSUMED #2) | `staleness.py:15-44` | CL3–CL5 | | ✅ |
| R4 | Scope | "Cover the worktree case… runbook's mitigation (`CA_DB_PATH`) reachable from payload fields" | Test root≠cwd visibility via `index_root`; runbook line points at `index_root` (+ refs for revision) | `parallel-agents.md:40-51` | CL7 | | ✅ |
| R5 | Scope | "Non-git repos and detached HEAD must degrade, never raise" | Defined values; no raise | `gitutil` None pattern | CL1,CL8 | | ✅ |
| C1 | Constraint | "R4 — determinism… identical repo state gives identical fields" | Ref read is deterministic git read | ENGINEERING_RULES R4.2 | CL1 | | ✅ |
| C2 | Constraint | "R5.3 / 072 — never let a ref read make a status or build call fail" | Soft degrade | R5.3; 072 | CL1,CL5 | | ✅ |
| C3 | Constraint | "061 — field that means nothing omitted; detached HEAD is a value" | Detached → `HEAD`; non-git → `null` (same as `last_commit`) | 061; ticket L64–65 | CL1,CL3 | | ✅ |
| C4 | Constraint | "Do not re-model staleness: 047 owns which files count" | `staleness_of` rules unchanged | `staleness.py:36-44` | CL5 | | ✅ |
| AC1 | AC | "names the ref the index was built on and the ref HEAD is on now; test switches branches…" | Assert `last_ref` ≠ `head_ref` after switch without rebuild | ticket L69–70 | CL8 | | ✅ |
| AC2 | AC | "branch switch with no file drift no longer reports a bare `staleness: current`" | Dual refs visible when both current after rebuild, or differ when switch-without-rebuild | ticket L71–72 | CL8 | | ✅ |
| AC3 | AC | "Detached HEAD, non-git, git failure → defined value, no raise" | Values + no exception | ticket L73 | CL8 | | ✅ |
| AC4 | AC | "worktree mismatch has a test and a runbook line pointing at the revealing field" | Test + runbook cite `index_root` | ticket L74 | CL7 | | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 Q |
|-------|---------------|------------------------|--------|--------------|----------|
| AC1 | both refs named; branch-switch test | `last_ref` from meta + `head_ref` from live git; checkout other branch without rebuild ⇒ assert inequality | Y | greppable pytest | — |
| AC2 | not bare `current` after switch | After switch+rebuild both refs equal new branch (named); after switch-no-rebuild refs differ while SHA staleness may be `behind` — visibility via dual refs (ASSUMED #2) | Y | assert keys present + values | — |
| AC3 | detached / non-git / fail | detached → `"HEAD"`; non-git/fail → `null`; no raise | Y | pytest cases | — |
| AC4 | worktree test + runbook | extend/reuse 071-style root≠cwd; runbook names `index_root` | Y | test + grep runbook | — |

## Inventory (universal)

- **Denominator N:** 0 (no all/every/no surface requirement beyond status+busy shared vocab — enumerated in change-list)

## Clarifications

`CLARIFICATION: 3 raised | 3 self-resolved as ASSUMED (standing best-option) | 0 for human decision`

- ASSUMED #1–#3 ratified at Gate 1 by invoke standing approval ("best option, pass all gates").

---

## Phase 1 — Analysis ✋ Gate 1

- **Root cause / gap:** Status answers sameness (`last_commit`/`head_commit`/`staleness`) but never the human revision name. After an out-of-band branch switch + rebuild, `staleness: "current"` is true and useless. `gitutil` has no ref reader; meta stores only SHA.
- **Entry + blast radius:** `gitutil` → `_record_meta` / `get_index_status` / `staleness.compute_staleness` / busy `_busy_staleness`; tests for status/staleness/busy; `parallel-agents.md`; PLAN/CONVENTION tool tables. Build *success* payload refs → 079 (out of scope). Nav payloads → not in scope (ASSUMED #1).
- **RULE SECTIONS:** R4.1–4.2 ✅ · R5.3 ✅ · R1.1–1.4 N/A (no language/adapter) · R3 N/A (MCP payload fields, not contract vocabulary) · R6.1 ✅ (fixture-repo tool tests)
- **Self-audit:** sections 6=6; j=0; ASSUMED confirm required.
- **Gate 1 status:** **cleared** (standing approval; ASSUMED #1–#3 ratified)

`TIER: full` · review waived by invoke · `SCOPE: M`

---

## Phase 2 — Design ✋ Gate 2

- **Approach:**
  1. Add `gitutil.head_ref(root)` → `rev-parse --abbrev-ref HEAD` (returns `"HEAD"` when detached; `None` when git cannot answer).
  2. Add `LAST_REF_KEY = "last_ref"` to store meta; `_record_meta` stamps it when `head_ref` is not `None` (parallel to `last_commit`).
  3. Status (`minimal`+): emit `last_ref` (meta) + `head_ref` (live). Unbuilt: both `None`.
  4. Extend `compute_staleness` (+ busy) with `last_ref`/`head_ref`; leave `staleness_of` unchanged (C4).
  5. Tests: branch switch without rebuild (`last_ref != head_ref`); detached/non-git/fail; worktree `index_root` assertion; runbook line for `index_root` as revealing field (revision: compare `head_ref` / `last_ref` on status).
  6. Docs: PLAN status row + CONVENTION if field list lives there; BACKLOG status on finalise.

- **Rejected alternatives:**
  - New staleness word e.g. `switched` — rejected: re-models 047 vocabulary; AC allows dual-ref naming; Constraint C4.
  - Put refs on every nav payload — rejected: 061 weight; directory mismatch already `index_root`; ticket allows status-only.
  - Only `head_ref` without persisting `last_ref` — rejected: cannot name "ref the index was built on" after HEAD moves.

**Assumptions**

| Assumption | verified / novel-untested | Proof |
|------------|---------------------------|-------|
| `git rev-parse --abbrev-ref HEAD` returns branch name or `HEAD` when detached | verified (git documented behaviour; proving test covers detached) | integration test |
| Missing `last_ref` on pre-077 DBs reads as `None` (061) | verified (get_meta already returns None for absent keys) | existing store behaviour |

**Smallest change-list**

| # | Change | File/area | Ph2 covered by | k/N |
|---|--------|-----------|----------------|-----|
| CL1 | `head_ref()` helper | `code_atlas/gitutil.py` | R1,R5,C1,C2,C3 | |
| CL2 | `LAST_REF_KEY` + META_KEYS | `code_atlas/store.py` | R2 | |
| CL3 | Stamp `last_ref` in `_record_meta` | `code_atlas/indexer.py` | R2,G1 | |
| CL4 | Emit `last_ref`/`head_ref` on status (all detail levels that carry commits) | `code_atlas/tools/get_index_status.py` | R1,R2,R3,AC1,AC2,C3 | |
| CL5 | Extend `compute_staleness` + busy with refs; leave `staleness_of` alone | `code_atlas/tools/staleness.py`, `build_or_update_index.py` | R3,C2,C4,G1 | |
| CL6 | Docs: PLAN tool row (+ CONVENTION if needed) | `docs/PLAN.md`, maybe `docs/CONVENTION.md` | G1 | |
| CL7 | Runbook: point at `index_root` (+ status refs for revision) | `docs/runbooks/parallel-agents.md` | R4,AC4 | |
| CL8 | Proving + degrade + worktree tests | `tests/test_index_ref.py` (new) + touch busy/status key freezes if any | AC1–AC4,R5 | |
| CL9 | Proof collateral: update frozen key sets / busy tests that assert exact keys | `tests/test_get_index_status_health.py`, `tests/test_busy_build_staleness.py`, related | blast-radius | |

**Blast-radius (producers/consumers):** `compute_staleness` consumers = status + busy; `_MINIMAL_KEYS` / busy key asserts; `LAST_COMMIT_KEY` stamp sites only `_record_meta`. No nav_result change.

**Rule compliance:** R4.2 ✅ · R5.3 ✅ · R6.1 ✅ · 061 ✅ · 047/C4 ✅ · R1.1 N/A

**Proving test:** `tests/test_index_ref.py::test_branch_switch_names_distinct_refs` — build on branch A, checkout B without rebuild, status asserts `last_ref != head_ref` and both non-null. Invocation: `pytest -q tests/test_index_ref.py`.

**Verification plan**

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 | integration | pytest branch switch | ✅ |
| AC2 | integration | pytest dual-ref present (switch±rebuild cases) | ✅ |
| AC3 | integration | pytest detached / non-git / fail | ✅ |
| AC4 | integration + docs | pytest index_root worktree + grep runbook | ✅ |

**Coverage-gap exclusions:** none

- **Rollback:** revert branch; meta `last_ref` ignored by old readers.
- **SCOPE confirmed:** M
- **Gate 2 status:** **cleared** (standing approval)

---

## Phase 3 — Execute

- Branch: `feat/077-index-cannot-name-the-revision-it-describes`
- Commits: (pending push)
- Proving test added: `tests/test_index_ref.py::test_branch_switch_names_distinct_refs` (+ degrade/worktree cases)
- **Verification sweep — BOTH axes.** *File axis:* diff ⊆ CL1–CL9 ✅. *Behaviour axis:* Approach bullets 1–6 `implemented-as-approved` ✅. No design-conformance deviations.
- Full suite: **1115 passed** (baseline 1108; +7 proving/collateral). ruff/mypy clean on touched modules.
- Design-invalidation: none

## Phase 4 — Review ✋

- **Skipped** by invoke (`/solve 077 with skipped review`). No `Reviewed at` marker — finalise proceeds under waived review per standing maintainer workflow + AGENTS.md finishing path.

## Phase 5 — Finalise ✋

- PR draft: `/tmp/pr-077.md`
- Planned outward actions (user-approved in invoke: commit + push + open PR):
  - [x] commit change-set
  - [ ] push branch
  - [ ] open PR via gh
- Durable lesson: written to `docs/LESSONS.md` (077 dual-ref vs new staleness word)
- Revert path: revert the PR branch; old readers ignore unknown `last_ref` meta

---

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 0 | explore (context scan) | 1 | unmeasured (blocking retrieval) | rtk expect · n/a |
| 0 | challenger (exposure-checker) | 1 | unmeasured (blocking retrieval) | rtk expect · n/a |

`LEDGER TOTAL: unmeasured (2 blocking dispatches) · top cost driver: Phase 0 explore + exposure-checker`

---

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Gate 0/1 | ASSUMED #1–#3 ratified | standing "best option / pass all gates" |
| Gate 1 | TIER=full, review waived | invoke args |
| Gate 2 | dual-ref, no new staleness word; status+busy only | ASSUMED + C4 + 072 |

## Session status

- **Last updated:** 2026-08-12
- **work_doc_mode:** embed → `docs/tasks/077_index-cannot-name-the-revision-it-describes.md`
- **Current phase:** Phase 5 — Finalise (outward actions)
- **Next action:** push branch + open PR (user-approved in invoke)
- **Blocked on:** nothing
