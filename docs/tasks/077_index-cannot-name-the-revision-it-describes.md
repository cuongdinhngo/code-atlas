---
id: 077
slug: index-cannot-name-the-revision-it-describes
title: 'The branch changed under a live session and `staleness: "current"` was true, correct, and useless'
phase: 1.5b
milestone: Agent-trust
status: todo
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
