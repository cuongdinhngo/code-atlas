---
id: 161
slug: impact-resolves-a-shared-qname-to-one-twin-and-carries-no-freshness
title: '`impact` binds a shared qname to one arbitrary twin at tier RESOLVED, and carries no freshness field for an answer acted on destructively'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [017, 070, 078, 077]
---

## Why this exists (field retro rounds 8–9, 2026-08-25/26)

`impact` answers *"what breaks if I change this?"* — the answer a developer acts on **destructively**
(round 9's author deleted directories on it). Two rounds found it silently wrong or silently
undated on exactly that question.

**9-A — a shared global binds to the wrong twin, and the whole radius is downstream of it.**

> Seed `src/.../MemberTab/tabs.php`. `impact` bound `showNewMemberScreen` — defined **in the seed
> file itself at :87** — to the **legacy ALPHA** definition at `legacy/.../tabs.php:39`, tier `RESOLVED`.
> **5 of 6 rows (83%) were `legacy/` files the change cannot affect; 0 rows were the file's real `src/`
> consumers.** `seeds_dropped: 0`, no `reason`, every row `RESOLVED` — nothing in the payload suggests
> anything is wrong. And this repo's `CLAUDE.md` **routes developers to this exact call.**

The asymmetry that makes it dangerous: a *bare-name* ambiguity is dropped and counted; a *shared exact
qname* is silently resolved to one. `read_symbol` already refuses this case with `subject_ambiguous`
— *"same ambiguity, same index, opposite honesty"* (round 9 §15).

**8-E — no freshness field at all.**

> `impact` calls answered about files already deleted in the working tree, correctly, with nothing in
> the payload naming the revision. No `staleness`, no `built_at`, no `source_stale`. A blast-radius
> answer is exactly the kind acted on destructively; `sign=true` gives a revision, the default payload
> gives none.

## Root cause

- **Seed resolution short-circuits on the first exact hit.** `code_atlas/tools/impact.py:176-184`
  (`_resolve_seed`) returns `SubjectResolution("resolved_unique", …)` when
  `store.nodes_by_qualified_name(qname, limit=1)` is non-empty — `limit=1`, so N identical-qname
  definitions collapse to one. `store.py:2461-2467` (`_impact_node_loc`) then picks **one arbitrary**
  node's file/line (`limit=1`, whichever `_NODE_ORDER` yields first). No same-file / same-tree
  preference.
- **The honest path exists but is not taken here.** A bare name that is not an exact qname falls to
  `classify_missing_subject` and an `ambiguous` status is dropped and counted (`impact.py:135-198`).
  `REASON_SUBJECT_AMBIGUOUS` (`nav_result.py:49`) and `attach_ambiguous_definitions`
  (`nav_result.py:512-523`) exist and are used by `find_references` (`find_references.py:198`) — but
  `impact` never emits either.
- **Freshness never reaches the body.** `impact.py:91` calls `compute_staleness(...)` **only** when
  `sign=True`, feeding the optional `claim` line (`impact.py:111-119`). The `nav_result(...)` payload
  (`impact.py:94-104`) carries `depth` / `seeds_dropped` / `truncated` but no `staleness` /
  `built_at` / `source_stale` / `last_commit`. Contrast `get_index_status.py:166-167` and
  `find_references.py:110-112` (`FreshnessGuard`).

## Scope

- **Resolve a shared qname honestly.** When a seed qname has N > 1 definitions, prefer a definition in
  the **same file**, then the **same directory subtree** as the seed; if still ambiguous, emit
  `subject_ambiguous` with the candidates (as `read_symbol` / `find_references` already do) rather than
  silently walking one twin's subtree at tier `RESOLVED`. The preference is a general graph/path
  heuristic — **never** a repo- or framework-specific rule (R2).
- **Carry freshness in-band.** Add `staleness` (and the revision it is a zero *at*) to the default
  `impact` payload, via the same `FreshnessGuard` / `compute_staleness` the other tools use — not only
  behind `sign=true`. A `seeds_dropped: 0` that a reader relies on before deleting code must name the
  revision that zero is true at.

### Explicitly not in scope

Per-subject reasons for a multi-seed `impact` call (`impact` merges seeds into one radius by design —
PLAN §12, task 102). This ticket is about a *single* seed whose qname is shared, and about the payload's
freshness.

## Constraints

- **R1.1** — no language branch. Same-file / same-tree preference keys on node file path and the seed's
  path, which are language-neutral. **R2** — no repo/framework names (the `legacy/alpha` ↔ `legacy/beta`
  twin shape is the *symptom*, not the rule; the fix is general same-tree preference).
- **R3** — `subject_ambiguous` is existing tool vocabulary (no `contract_version` bump); changing what
  a seed resolves to is a **behaviour change** — re-read every test asserting an `impact` seed binding
  or `seeds_dropped`, don't merely re-record.
- **R4 / R4.2** — same index, same subject, same result; the tie-break among equal-distance candidates
  must be deterministic (e.g. path order), not arbitrary.
- **061** — freshness rides the existing payload shape; measure any size change on the cheap path.

## Acceptance criteria

1. On a planted graph with the same qname defined in the seed file and in a sibling subtree, `impact`
   on the seed resolves to the **same-file** definition and its real consumers — not the sibling twin —
   pinned by a test that fails on today's `limit=1` short-circuit.
2. When N > 1 definitions are equidistant (no same-file/same-tree winner), `impact` emits
   `subject_ambiguous` with the candidates rather than a confident `RESOLVED` walk of one — pinned by a
   test.
3. The default (`sign=false`) `impact` payload carries a freshness signal (`staleness` and the revision
   the answer describes), pinned by a test; `minimal`'s size change, if any, is measured and stated.
4. Every existing assertion on an `impact` seed binding / `seeds_dropped` is re-read, each verdict
   recorded (R3); no expectation is updated to match new output without that reasoning.
5. No language branch (R1.1 grep-gate green); no repo/framework name in the heuristic (R2 grep-gate
   green). Determinism holds (R4.2).

## References

Field retro rounds 8–9, findings **9-A** (shared-qname mis-binding) and **8-E** (`impact` carries no
freshness). `code_atlas/tools/impact.py:91,94-104,111-119,135-198,176-184`,
`code_atlas/store.py:2461-2467`, `code_atlas/tools/nav_result.py:49,512-523`,
`code_atlas/tools/find_references.py:110-112,198`, `code_atlas/tools/get_index_status.py:166-167`.
Related: [017](017_impact-engine.md) (the engine), [070](070_ambiguous-qname-no-scoping.md) (one qname,
five definitions merged), [078](078_ambiguous-payload-still-picks-one-definition.md)
(`ambiguous_definitions` warns while `source` ships one), [077](077_index-cannot-name-the-revision-it-describes.md),
[102](102_impact-cannot-tell-an-absent-subject-from-a-zero.md) (the seed-drop count this builds on).
