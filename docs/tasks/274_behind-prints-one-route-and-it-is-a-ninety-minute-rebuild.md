---
id: 274
slug: behind-prints-one-route-and-it-is-a-ninety-minute-rebuild
title: 'A `behind` index still serves `search_symbol` and `read_symbol` and still has `serve_behind` for the caller families it refuses, but `get_index_status` names exactly one route — `build_or_update_index`, ~91 minutes on the anchor repo — so two agents on the same day read "behind" as "rebuild before asking anything" and learned the real rule only by trying'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [257, 267, 246, 073]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 23 §4 / §4e / §4g)

`staleness: "behind"`, `dirty_indexed_files: 0`. What followed, in one session:

- `find_references` ×3 → `reason: index_stale`, zero rows, each time.
- `search_symbol` ×4 (15 subjects) and `read_symbol` ×6 → served from the **same** index,
  `reason: ok`. Two of those answers were the session's decisive findings.

So "behind" does not disable the index; it disables one family of questions. Nothing says so.
`_suggestions` (`get_index_status.py:500–508`) returns `[build_or_update_index]` for any staleness
that is not `CURRENT`, and that array is the payload's only route. The honest reading is *rebuild
before asking anything*, which for a ~91-minute build deters everything.

`serve_behind` already exists on both caller tools (257/267) and is exactly what that session needed
— an unchanged subject on a behind index answers `index_behind` rather than refusing. **No payload
ever names it.** A second agent working the same repo the same day declined the caller family
outright for the same reason, independently, which makes this a reliable trap rather than one
agent's misreading.

The workaround the retro had to derive by hand — `git diff --name-only <last_commit> <head_commit>
-- <area>`, empty ⇒ every symbol answer about that area is still accurate — is a route the status
payload has both commits to name.

## Scope / Deliverables

- **`behind` carries what it still serves.** A `behind` status names the tool families that answer
  from it (search / read, via read-through repair) and the families that refuse without opt-in,
  instead of implying a rebuild is the only move.
- **Name `serve_behind` where it is the route** (R5.4c: a warning an agent cannot act on is a
  warning it learns to ignore — 267's own finding, one round later, on the other side of the same
  payload).
- **A subject-scoped verdict, not only a global flag.** The status holds `last_commit` and
  `head_commit`; the files changed between them are the set that decides whether *this* question is
  affected. Name the count, and the route that narrows it, rather than colouring every subject.
- Applies to the refusal side too: an `index_stale` refusal names `serve_behind` when the subject's
  own file is the drifted one.

## Constraints

- 061 / 223: `minimal` stays cheap — this lands where `staleness` already lands, and adds no field
  to a `current` index.
- **No claim the index cannot back** (R5.6): "search still serves" is true of read-through repair
  within its cap ([246](246_ensure-miss-refuses-on-the-count-of-drifted-files-not-on-the-subject.md)),
  and the wording must not promise a repair the budget may not have.
- No git spawn added to the unbuilt path (077) or to `minimal`.
- The rebuild route stays; this widens the answer, it does not replace it.

## Acceptance criteria

- A behind-index status names the served families and `serve_behind`; a current-index status is
  byte-identical to today's.
- A test pins that `next_tool_suggestions` on `behind` is not *only* the build tool.
- An `index_stale` refusal on a drifted subject names `serve_behind` in its route.
- The runbook sentence a reader can act on — behind ⇒ check the changed set, then search/read freely,
  expect the caller family to refuse — lands in `docs/runbooks/onboarding-a-repo.md`, not in AGENTS.md.

## References
`code_atlas/tools/get_index_status.py:500–508`, `code_atlas/tools/freshness.py:173–188`,
`code_atlas/tools/nav_result.py` (`REASON_INDEX_BEHIND`, `REASON_INDEX_BEHIND_SUBJECT_CHANGED`),
field retro round 23 §4 / §4b / §4e / §4g #1,
[257](257_the-index-goes-blind-at-the-moment-it-is-most-wanted.md),
[267](267_the-warning-an-autonomous-agent-cannot-act-on.md),
[246](246_ensure-miss-refuses-on-the-count-of-drifted-files-not-on-the-subject.md).
