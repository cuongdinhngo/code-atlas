---
id: 246
slug: ensure-miss-refuses-on-the-count-of-drifted-files-not-on-the-subject
title: '`ensure_miss` returns `stale` whenever more than one indexed file has drifted, and 166 widened drift to `indexed_commit..HEAD`, so three commits on a feature branch make every zero-hit answer `index_stale` no matter which file it asked about — the tool teaches its users to finish all symbol work before their first commit, and the field has learned it as a habit'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [073, 166, 035, 057]
---

## Why this exists (field retro round 17)

035 made freshness result-driven and 073 added the miss-driven case: a query that matched nothing may
spend the per-call reparse budget on the sole dirty indexed file, because absence is the one answer a
drifted index can invent. Both are right, and both are bounded by `READ_THROUGH_CAP = 1`.

The bound is applied to the **count of drifted files**, not to the subject:

```python
candidates = dirty_indexed_paths(self.store, self.config)
if not candidates:      return "ok"
if len(candidates) > 1: return "stale"
return self.ensure(candidates[0])
```

`code_atlas/tools/freshness.py`. Then 166 — correctly — widened what counts as drift: `dirty_indexed_paths`
unions `indexed_commit..HEAD` with the working tree, so a file changed and *committed* after the build
also drifts. The two together compose into a refusal nobody chose: **commit three files on a feature
branch and `len(candidates)` is 3 forever**, so every zero-hit query answers `index_stale` — including
one about a file untouched by any of them, whose rows the index can still vouch for.

The retro records the consequence as a habit rather than a complaint: *"all my symbol work happened
before the first commit, by habit learned from an earlier round. That habit should not be necessary."*
It calls the global refusal on a three-file diff **the single most annoying property of the tool in
day-to-day use**, and the session's status payload confirms the trigger: `staleness` flipped to
`behind` at the first branch, with `head_ref` on a feature branch.

The retro's own framing — *"serve reads from a `behind` index"* — is not what the code does, and the
distinction matters for the fix. There is no global refusal: `staleness: "behind"` is a status field,
and `FreshnessGuard.ensure` is per path. What refuses is narrower and stranger: a **count** standing
in for a subject.

## Scope

- **Decide the refusal on the subject, not on the population.** A zero-hit query whose subject is
  nameable (a qname, a path) has a subject to check; the count of unrelated drifted files is not
  evidence about it. Where the subject genuinely cannot be named, the honest answer stays `stale`.
- **State what absence can and cannot be proven from.** This is the ticket's real question: a zero on
  a subject whose own file is current is still not proof that nothing *elsewhere* matches, and 073's
  refusal exists for that. Name the tier the answer may claim (R5.2: never the stronger one) and
  disclose the residue — *"checked this subject's file; N other indexed files have drifted"* — rather
  than refusing whole.
- **Revisit `READ_THROUGH_CAP` on the same evidence, or reject doing so in writing.** One reparse per
  call is a conservative bound chosen for "one adapter call"; an answer spanning two drifted files is
  `stale` today for the same structural reason. Measure before changing it.
- **Out of scope:** background or automatic rebuilds, raising the cap without a measurement, and any
  change to `staleness`'s vocabulary (047/077/202 settled it).

## Constraints

- **R5.2 / R5.6** — a partially verified answer is never signed as a verified one. If the answer
  claims less, it must say so in `reason`, not in prose only.
- **035 / 073** — per-call repair stays bounded; this ticket must not make one query reparse a branch.
- **R4.2** — deterministic: the same working tree yields the same rows and the same `reason`.
- **061** — a clean tree must produce byte-identical payloads.
- **Cost** — `dirty_indexed_paths` runs a git diff per call already; a subject-scoped check must not
  add a second traversal per answer. Measure on the anchor-scale index.

## Acceptance criteria

- A zero-hit query about a subject whose file is current, on a branch with three unrelated committed
  changes to indexed files, returns an answer whose `reason` states what was verified — pinned by a
  test that builds exactly that state.
- The unnameable-subject case still returns `stale`, asserted.
- A clean tree is byte-identical to today.
- A written verdict on `READ_THROUGH_CAP`, with the measurement behind it.
- The field habit is retired in evidence: the same sequence the retro describes (index, branch,
  commit three files, ask a symbol question) runs green in a test.

## References

Field retro round 17 (2026-09-11, maintainer-local) §3 and §5 ask 2 — note that ask 2's framing
("serve reads from a `behind` index") misstates the mechanism; the defect is the count-based refusal
above. Related: [035](035_read-through-freshness.md) (result-driven repair),
[073](073_freshness-cannot-find-what-is-not-indexed.md) (the miss-driven case and its cap),
[166](166_read-symbol-answers-from-pre-repair-state-and-calls-it-no-such-symbol.md) (widened drift to
the indexed commit), [047](047_staleness-scoped-to-indexed-files.md) / [077](077_index-cannot-name-the-revision-it-describes.md) / [202](202_a-killed-build-leaves-an-index-that-reports-current.md) (the `staleness` vocabulary, deliberately untouched).

## Token usage

| Phase | Tokens |
|---|---|
| — | not yet started |
