---
id: 388
slug: behind-refuses
title: 'With no build running, a behind index still refuses find_callers and find_references, and it is the most common reason an agent falls back to Grep'
phase: 2
milestone: Freshness
status: todo
depends_on: [257, 267, 274, 365]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17, 45 scored PRs, all
answered by 0.3.0, so 365 and 366 had shipped). In 6 PRs the agent fell back to Grep because the
index was `behind`, and at those moments no build held `write.lock`, so 365's unasked serve did
not apply.

- F1 (4 PRs): `find_callers` / `find_references` refused while the index was `behind`. The agent
  did not know about `serve_behind`, or read the refusal as final, and used Grep for the callers.
- F2 (1 PR): the index was `behind` because the main checkout had uncommitted deletions under a
  directory the change never touched. Nothing named those paths, so the agent could not tell that
  its own subject was unaffected.
- F3 (1 PR): `search_symbol` answered `index_stale` for one name inside a multi-query sweep. A
  name search has no inbound edge to vouch for.
- F4 (1 PR): a field had just been deleted in the working tree, so proving that nobody still reads
  it needed the *built* graph. `find_references` refused instead.

257 made `serve_behind` opt-in, and 365 narrowed that to "a build is writing". These six PRs are
the evidence that the opt-in itself is the cost: an agent rarely passes the flag.

## Scope

1. Measure first. On the anchor index, count over a window how often a behind answer refuses
   with no lock held, and check whether the refused subject's file is in `changed_indexed_files`.
2. Unchanged subject: serve by default, labelled `index_behind` with the built revision, never
   `ok`. Re-decide 257's default in PLAN §19 using this evidence.
3. Changed subject: keep the refusal, but name the route: the `serve_behind` call, ready to copy.
4. `search_symbol` never refuses on staleness. A row from a changed file carries `source_stale`.
5. `get_index_status` lists the uncommitted and changed paths that made the index `behind`
   (`behind_because`, capped), so "my subject is unaffected" can be read without another call (F2).
6. A symbol removed since the build is answered from the built graph as
   `index_behind_subject_removed`, so "who still uses what I deleted" works (F4).

## Acceptance criteria

- **AC1:** Index built at A, HEAD at B, no lock held, and the subject's file unchanged between A
  and B: `find_callers` answers `index_behind` with rows and the built revision.
- **AC2:** The same with the subject's file changed: a refusal whose `try_instead_hint` names the
  exact `serve_behind` call.
- **AC3:** `search_symbol` on a behind index never answers `index_stale`.
- **AC4:** A method deleted between A and B: `find_references` lists its built-graph references,
  labelled `index_behind_subject_removed`.
- **AC5:** On a current index, every answer is byte-identical.

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.
