---
id: 259
slug: one-knob-sets-both-index-size-and-page-truthfulness
title: '`CA_MAX_RESULTS` is both the query-time page cap and the build-time resolver fan-out, so the value an operator picks to keep the index small silently caps how much of an answer a caller page is allowed to show — the anchor pinned it to 10 and thereby pinned every `find_callers` page to ten rows'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [251, 138]
---

## Why this exists

One config value spans two unrelated decisions:

- **Build-time fan-out.** `indexer.py:617` and `:673` pass it as `resolve_edges(..., max_candidates=config.max_results)` — it caps how many candidates a multi-match HEURISTIC link may consider, i.e. **index size**.
- **Query-time page cap.** `config.clamp_limit(limit, max_results)` (`config.py:488`) makes it the ceiling on every nav page.

`get_index_status` already admits the conflation in its own words — *"disk / nav / resolver knob"*.

The anchor repo pinned `max_results = 10` to hold 2.6M heuristic edges. The consequence was not a smaller index; it was that **every caller page on that repo is ten rows long**. [251](251_the-resolved-caller-can-be-off-the-page.md) found the `RESOLVED` caller sitting on page 12 under vendor `build()` noise. An operator tuning disk usage was, without being told, tuning **how much of the truth a page may contain**.

This is the root of the page-1 class. Fixing ordering ([265](265_the-default-page-order-is-the-alphabet.md)) while this knob still caps the page at ten leaves the fix cosmetic on exactly the repo that needs it.

## Scope / Deliverables

- **Two config keys.** A query-time page cap (new default **50**) and a build-time resolver fan-out (keeps today's default and today's meaning). `contract`/`config.py` is the single source; `clamp_limit` reads the page cap only.
- **Changing the fan-out is a build decision** — it must require a rebuild to take effect and say so, exactly as it does today. Changing the page cap must never require a rebuild.
- **Back-compat.** `CA_MAX_RESULTS` set alone keeps working and keeps its build-time meaning; the page cap falls back to its own default rather than inheriting the fan-out value. A repo that pinned 10 for disk reasons gets 50-row pages on upgrade **without** a rebuild — that is the point of the ticket, and it must be stated in the runbook.
- **`get_index_status`** stops describing one knob as three things and names each key with its scope.

## Constraints

- R4.2: identical input → identical rows. Raising the page cap changes page *length*, never row order or row content.
- Do not raise the fan-out default to "fix" 251 — [creator note §1, remaining-improvements §1] name widening the knob as the wrong fix. The page cap is the knob that moves.
- No new tool, no new payload field beyond the status rename.

## Acceptance criteria

- `CA_MAX_RESULTS` no longer reaches `resolve_edges`; a grep for the old symbol in `indexer.py` returns the new fan-out key.
- A test pins: page cap default 50; fan-out default unchanged; setting the fan-out does not change any page length; setting the page cap does not change any edge count in a rebuilt index.
- A test pins the back-compat arm: `CA_MAX_RESULTS=10` alone yields fan-out 10 **and** page cap 50.
- `runbooks/onboarding-a-repo.md` states which key needs a rebuild and which does not.

## References
[251](251_the-resolved-caller-can-be-off-the-page.md) (the `RESOLVED` caller on page 12), `code_atlas/indexer.py:617`, `code_atlas/config.py:488`, `code_atlas/tools/get_index_status.py`.
