---
id: 316
slug: index-status-has-no-one-line-summary
title: "get_index_status answers freshness in a wall of dense JSON with no one-line summary a reader can lift, so every routine is-it-fresh check reparses the payload"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [077]
---

## Why this exists (field-retro batch 2026-09-20/21 — asked in all four)

Every retro in the batch, and the two before, made the same small ask: *"still a wall of JSON for
'is it fresh?'; a one-line human summary at the top would help."* The payload is rich and honest and
that is correct for diagnosis — but the routine call is a yes/no freshness check, and today it means
parsing the dict to find `staleness` + `last_commit`. The one existing quotable line, `claim`, is
opt-in behind `sign=true` (`get_index_status.py:156-158`, `:371-388`) and is agent/provenance-facing,
not a guaranteed top-of-payload summary.

## Goal

Put one lifted, human-readable sentence of ground truth at the head of every `get_index_status`
payload, without removing or duplicating the structured fields below it.

## Scope / Deliverables

1. **A leading `summary` string** assembled at the three payload sites (`_status`
   `get_index_status.py:356-441`, `_unbuilt` `:304-336`, `_mismatched` `:339-353`), e.g.
   `"current @ 7efaa91 · 13,377 files · 146,048 symbols · healthy"` /
   `"behind by 6 commits @ 7efaa91 (read tools still serve) — run build_or_update_index"` /
   `"not indexed — run build_or_update_index"`.
2. **Derived, never a second source of truth** — the summary is composed from the same fields it
   precedes (staleness, counts, `last_commit`, edge health), so it cannot disagree with them.
3. **Present at every detail level**, since the freshness check is exactly the `minimal` call.

## Constraints

- 061: it adds a field, it removes none; the structured payload is unchanged below it.
- The summary reuses the ref/revision naming from 077 (`head_ref`/`last_ref`), not a new vocabulary.
- R4.2: identical status → identical summary string.
- It states only what the payload already proves — no new judgment, no health claim the fields don't
  support.

## Acceptance criteria

- **AC1** Every `get_index_status` payload (built / behind / unbuilt / schema-mismatch) leads with a
  `summary` string naming freshness, revision and scale in one line.
- **AC2** The summary is a pure function of the structured fields — a test mutates a count/staleness
  fixture and the summary tracks it, with no independent data path.
- **AC3** The summary is present at `minimal` detail level.
- **AC4** The existing fields and the opt-in `claim` line are unchanged.

## Out of scope

- Changing the structured payload shape or the `sign=true` claim line.
- A terse mode that *omits* fields — this adds a header, it does not slim the body.

## References
`code_atlas/tools/get_index_status.py:304-336`, `:339-353`, `:356-441`, `:156-158`, `:371-388`,
[077](077_index-cannot-name-the-revision-it-describes.md), ENGINEERING_RULES R4.2.
