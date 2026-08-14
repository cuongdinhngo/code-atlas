---
id: 092
slug: untracked-files-are-invisible-and-answer-no-such-symbol
title: 'An untracked file is silently skipped, then answers `no_such_symbol` for a class that is on disk'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [073, 082, 065]
---

## Goal
An agent wrote four new classes, rebuilt the index, and asked who consumes them. It got
`reason: "no_such_symbol"` — the vocabulary's word for *there is no such thing* — for a class that
existed on disk at `…/Controller/SiteMaintenanceController.php:17`. The cause was that the files
were **untracked**: `collect()` takes `git ls-files` as the walked set
(`code_atlas/indexer.py:366-367`), so an untracked file is not skipped-by-rule, it is never seen at
all. Every surface read green while this was true — the build reported `wrote:{files:14,…}` with no
mention of a skip, and `get_index_status` reported `dirty_indexed_files: 0`, which is literally true
(an unindexed file cannot be a dirty *indexed* file) and actively misleading.

The vocabulary already owns the right word — `not_indexed` (`code_atlas/tools/nav_result.py:21`) —
and the miss path did not reach for it. This is the round's §9 primary finding and the only one that
demonstrably cost the evaluator working time.

## Evidence (field retro round 5, 2026-08-14, **real work** — not a probe)
- Verbatim, after creating the file and rebuilding:
  ```json
  {"indexed":true,"qname":"\\…\\SiteMaintenanceController","results":[],
   "reason":"no_such_symbol","total_count":0}
  ```
- Build payload for the same rebuild: `{"mode":"incremental","wrote":{"files":14,…},"graph":{…}}` —
  no skip count, no untracked count.
- `get_index_status` at the same moment: `dirty_indexed_files: 0`.
- The reason changed only after `git add` + commit + rebuild — to
  `relationship_not_modelled`, which was the *correct* nothing (§4 row 2). Until that commit,
  **two independent nothings were stacked and indistinguishable** (retro §11.4): untracked
  invisibility and an unmodelled edge kind, both presenting as `results: []`.
- Consequence recorded in the retro's verdict (§10): a written carve-out — *"not for files you have
  just written and not yet committed"* — against a repo whose agent guide makes code-atlas mandatory
  for symbol questions.
- The evaluator attributed the empty answer to staleness, routed to `grep`, and had to correct the
  report to the operator when asked directly. **Right answer, wrong reason** — the failure mode 065
  exists to prevent.

## What "honest" looks like here
The agent most likely to ask about a file is the agent that just wrote it. Three states must be
distinguishable from the payload alone:
1. **On disk, indexable suffix, not ignored, but untracked** → `not_indexed`, with a `try_instead`
   naming the remedy. Never `no_such_symbol`.
2. **On disk and deliberately excluded** (suffix or ignore rule) → already covered by 082's census;
   the miss path should say which.
3. **Nowhere on disk** → `no_such_symbol` stays correct and this ticket changes nothing.

## Scope / Deliverables
- **Report the skip.** Add an untracked bucket to the collection census
  (`CollectionCensus`, `code_atlas/indexer.py:333-344`) and surface it on
  `get_index_status(verbose)` under `collection.skipped` **and** on the build payload. The 082
  identities must still close by construction — decide in design whether untracked files enter
  `collected` (changing the `git ls-files` denominator claim at `indexer.py:338`) or sit beside it as
  a separate walk; state the choice and why.
- **Classify the miss.** When a single-subject lookup misses and the subject maps to a path that
  exists on disk with an indexed suffix and is not ignored, return `not_indexed`, not
  `no_such_symbol`. Reuse `classify_missing_subject` (075/076) rather than adding a second classifier.
- **Give it a route.** `try_instead` must name the remedy, and must obey [093](093_try-instead-is-not-a-callable-tool-name.md) —
  a real tool name plus a prose hint, not an identifier-shaped instruction.
- **Bound the disk check.** The classification runs on the miss path only; a hit must not pay for it,
  and the check must not walk the tree (066's disclose-the-bound precedent).
- **Decide the qname→path direction explicitly.** A qname does not carry a path. Record in design how
  the miss path finds candidate files for an unindexed subject (adapter-free heuristic? a bounded
  suffix scan of the untracked set collected above?) — and if the answer is "only reachable via the
  untracked census", say so and scope the fix to that.

## Constraints
- R1.1 — no language branch in the core; "indexable suffix" is already config, not PHP knowledge.
- R4 — the untracked count must be deterministic for a given tree; no timestamp or ordering effects.
- R3 — `not_indexed` is existing vocabulary; adding no new reason value means no `contract_version`
  bump, but the conformance suite must gain the case.
- Cost: the census runs inside the existing single walk (082's rule — no rival second traversal).
- The fix must not make an untracked file *indexed*. Indexing untracked files is a separate decision
  with its own blast radius; this ticket makes the skip **visible**, not the skip go away.

## Acceptance criteria
- A test creates an untracked file with an indexed suffix, builds, and asserts: the build payload and
  `get_index_status(verbose)` both carry a non-zero untracked count, and the 082 identities still
  reconcile.
- A single-subject lookup for a symbol in that file returns `reason: "not_indexed"` with a
  `try_instead`, and the whole payload is pinned.
- After `git add` + rebuild, the same lookup returns the real answer; a symbol that is nowhere on disk
  still returns `no_such_symbol`.
- `dirty_indexed_files: 0` alongside a non-zero untracked count is covered by a test that documents
  the two are different questions.

## References
Field retro round 5 §4 row 1, §5 ("the gap 077 does not close"), §9 primary, §11.4; candidate 1.
Related: [073](073_freshness-cannot-find-what-is-not-indexed.md) (read-through freshness repairs only
rows it already found — this is the same blind spot on the collection side),
[082](082_claims-nobody-outside-can-check.md) (the census this extends),
[065](065_empty-answer-cannot-explain-itself.md), [075](075_read-symbol-confident-zero-on-unnormalised-qname.md)
and [076](076_bare-name-subject-reads-as-absence.md) (the classifier to reuse),
[093](093_try-instead-is-not-a-callable-tool-name.md).
