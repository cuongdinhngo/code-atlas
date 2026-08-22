---
id: 124
slug: find-orphans-cannot-answer-at-scale
title: '`find_orphans` blew the transport limit at 19k files, and on the one ticket whose root cause *was* an orphan it contributed nothing'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [031, 057, 066, 119]
---

## Why this exists (field retro round 6, 2026-08-21, 19,022 files / 187,895 nodes / 1,820,955 edges)

```
Error: result (154,004 characters) exceeds maximum allowed tokens
```

The call never returned an answer. Its signature is `{depth, detail_level}` — **no `limit`, no
`offset`** — so there is no smaller request to make. From the spilled payload: `truncated: true`,
**500** results, `unproven: 500`, `authoritative: false`.

That 500 is not `find_orphans`' own cap. `find_orphans.py` passes
`max_nodes=config.impact_max_nodes` — it borrows **`impact`'s** budget
(`DEFAULT_IMPACT_MAX_NODES = 500`), a knob named after a different tool and tuned for a different walk.

**This mattered on a real ticket.** One of the five root-caused that session was **dead code** — an
include-path shim orphaned when a prior task removed the legacy router. That is precisely the question
this tool exists to answer. The shim is **not** among the 500 returned rows, and with no `offset` there
is no way to look further. The retro's verdict: *"It is honest about it (`authoritative: false`) —
which makes it harmless, not useful."*

Round 6 adds a standing carve-out to the mandatory-tool policy on the strength of this: **treat
`find_orphans` as unavailable at >10k files.** A shipped tool carrying an operational
"do not call this" is the cost being recorded here. **Retired by 124** — paging + transport-safe
`minimal` make the tool callable at anchor scale; no file-size carve-out remains in the runbooks.

## The exclusion was deliberate — same as [123](123_file-outline-total-count-is-the-page-length.md)

[057](057_answer-pagination.md) named the boundary explicitly: *"Reachability, `file_outline`, and
`include_graph` stay out."* Reasonable when written, before any measurement at this scale. Round 6 is
the measurement. **Nine tools already take `offset: int = 0`**; `find_orphans` and `file_outline` are
the only two list-returning tools that do not.

## Scope

- **Page the answer** — `limit` / `offset` on `find_orphans`, in the store's own stable order, per
  057's mechanism, and inside 066's clamp contract.
- **Give the walk its own budget** instead of borrowing `impact_max_nodes`. A cap that governs which
  orphans you can ever see must be named for what it governs and reported where the caller can find it.
- **Make the cap legible in the payload.** `truncated: true` next to 500 rows does not say whether the
  answer is 501 or 20,000. Report the population size the cap was applied to, so a reader knows the
  size of what they are not seeing — the same honesty 123 is asking of `total_count`.
- **Keep `minimal` genuinely small.** The transport blowout came from a `standard` payload; there must
  be a detail level that returns an answer at this scale by construction, not by luck.

### Relationship to [119](119_reachability-signal-provenance.md) — adjacent, not the same

119 is about *which signal* produced each reachability bucket, and it shares this tool's ancestry in
031. This ticket is about the answer not fitting through the transport and not being pageable. Both
were found in the same field round on the same repo; neither fixes the other, and 119's per-bucket
`signals` disclosure lands in the same payload area, so whichever ships second should reuse the first's
shape rather than adding a parallel one.

Round 6 also confirms 119's premise from the other side: the payload it saw carried
`entry_points: ["public/*.php"]` — the corrected declaration — which is how a stale root would have
been visible had 119 existed.

## Acceptance criteria

1. **AC1.** On a repo of the anchor's order (~19k files, ~1.8M edges), `find_orphans` returns a valid
   payload at every detail level instead of exceeding the transport limit. Measured, with the character
   count recorded before and after.
2. **AC2.** Paging visits every orphan exactly once in a stable order; the last page reports
   `truncated: false` (057's walk test shape).
3. **AC3.** The walk's node budget is a named `find_orphans` setting, no longer `impact_max_nodes`, and
   changing `impact`'s budget provably does not change which orphans are returned.
4. **AC4.** A truncated answer discloses the size of the population the cap was applied to, so
   "500 of N" is readable from the payload alone.
5. **AC5.** The new `limit` is inside 066's clamp contract (`limit_capped_to` on an over-ceiling
   request), proven by 066's enumerating test.
6. **AC6.** The round-6 case is reproduced as a test at reduced scale: a known-orphaned file beyond the
   first page is reachable via `offset`, and unreachable without it.
7. **AC7.** Round 6's ">10k files: treat as unavailable" carve-out is retired in writing once AC1 holds
   — an operational workaround that outlives its defect becomes folklore. **Closed:** runbooks §4 and
   this ticket's field note; no mandatory-tool file-size exclusion remains.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 124 — find_orphans cannot answer at scale (working doc)

- **Ticket:** 124 · `docs/tasks/124_find-orphans-cannot-answer-at-scale.md`
- **Type:** bug
- **SCOPE:** M · **TIER:** full
- **CHALLENGER:** OFF · **Review:** SKIPPED (solve args)
- **BASELINE:** 1710 passed (main after 123, 2026-08-22)

## Execute summary

- `CA_ORPHANS_MAX_NODES` / `orphans_max_nodes` — walk budget for `find_orphans` only
- `store.find_orphans`: SQL paging, `orphan_total`, walk via `orphans_max_nodes`
- Tool: `limit`/`offset`, honest `total_count`, page-only `truncated` + `walk_truncated`,
  `minimal` → `unproven_total` only
- Tests: `test_find_orphans_pagination.py`; 066/123 guard denominators updated
- Delta-green: **1710 → 1725 passed** (+15)

## Session status

- **Current phase:** complete (shipped)
- **work_doc_mode:** embed
- **Next action:** commit, push, open PR

## Cost ledger

| Phase | Dispatch | Notes |
|---|---|---|
| solve (main loop) | 0 | review/challenger waived; host unmeasured |
| **Total** | **0** | |
