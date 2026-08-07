---
id: 048
slug: edge-health-resolved-ambiguity
title: `edge_health` returns two different fields both meaning "resolved" — rename them
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [028]
---

## Goal
`store.edge_health` (`store.py:334-356`) returns, in one payload, two numbers that differ by ~2× and are
both called *resolved*:

- `edge_health.by_tier.RESOLVED` — edges whose `confidence_tier` is RESOLVED (the §8.2 trust tier).
- `edge_health.resolved` — edges whose **`target_qname IS NOT NULL`** (`:348-350`), i.e. edges the
  resolver managed to *link* to something, at any tier.

On the anchor repo: 642,370 (36 %) versus 1,283,969 (72 %) out of 1,774,891 edges. Both are internally
consistent — `sum(by_tier) == edges` and `resolved + unresolved == edges` — so a reader can tell they
measure different things, but nothing in the payload says *what* the second one is. The distinction lives
only in the docstring, which no MCP client ever sees.

This is not cosmetic. In the first external session (retro round 1), the agent had to choose which of the
two to write into a permanent, mandatory instruction file telling every future agent how much of the graph
to trust. It picked the tier number, and only because the onboarding prose it had been handed happened to
quote 36 %. Had it picked the other field — equally plausible from the payload alone — the repo's standing
rules would now assert that ~72 % of edges are trustworthy, which is false: a HEURISTIC edge with a
non-NULL `target_qname` is a *name-match guess that found a name*, not a verified link. The payload
currently makes the wrong reading the easy one, and the consumer of this field is an autonomous agent
with no way to check.

## Scope / Deliverables
- **Rename to what they measure.** `resolved`/`unresolved` become `linked`/`unlinked` (or equivalent
  unambiguous wording) — the word "resolved" belongs to the tier and should appear in exactly one place
  in this payload. Whatever the wording, the constraint is that no two keys share a stem.
- **Update every reader.** `get_index_status` (`tools/get_index_status.py:92`), `find_orphans`
  (`tools/find_orphans.py:49-60`), `reachable_from` (`tools/reachable_from.py:49-62`), `reach_shared`
  (`tools/reach_shared.py:85-103`), plus tests and any doc quoting the old key.
- **Decide the compatibility story explicitly.** This is a *tool payload* change, not a contract change
  — `contract.py` and `schema_version` are untouched — but it is still a break for anything reading the
  field. Options: rename outright (pre-1.0, single known consumer), or emit both for one release with
  the old key documented as deprecated. Pick one and say why in the working doc; do not leave a
  permanent alias, which reintroduces exactly the ambiguity being removed.
- **Make the tier number the one a reader reaches first.** Whatever the final shape, "how much of this
  graph can I trust" should be answerable without knowing §8.2. A one-line legend in the `standard`
  payload is in scope if it is cheap.
- **Documentation sweep** for the 36 % / 72 % figures wherever they appear (runbooks, README, PLAN §8.2),
  so no doc quotes a number whose key no longer exists.

## Constraints
- **No contract change (R3).** The adapter contract, `contract_version` and `schema_version` do not move.
- **SQL only, in the store (R1.4).** `edge_health` stays a store method computed in SQL; the rename must
  not move logic into a tool.
- **Determinism (R4)** and **cost** unchanged — this is a naming fix, not a new query. `get_index_status`
  at `standard` must stay in the ~100-token class the field session relied on.
- **`sum(by_tier.values()) == edges` and `linked + unlinked == edges` must both keep holding**, including
  the NULL/unknown-tier fold into RESOLVED (`:346-347`). If that fold is itself questionable, say so —
  but changing it is a separate ticket, not this one.

## Acceptance criteria
- No two keys in the `edge_health` payload share a word stem with a different meaning (asserted against
  the literal key set, so the guard survives a future addition).
- Every reader listed above returns the new shape; a test asserts the exact key set of `edge_health`
  (`get_index_status` at `standard`, `find_orphans`, `reachable_from`).
- Both invariants asserted on a store with a mix of tiers and NULL `target_qname` rows: tiers sum to
  `edges`, linked + unlinked sums to `edges`.
- The chosen compatibility decision is implemented and tested (either the old key is absent, or it is
  present, equal, and marked deprecated with a removal ticket referenced).
- No doc in the repo quotes a removed key; the 36 % figure is attributed to the tier field explicitly.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/store.py:334-356` (`edge_health`; `:348-350` the `target_qname IS NOT NULL` count that is
named `resolved`; `:346-347` the NULL-tier fold), `code_atlas/tools/get_index_status.py:92`,
`code_atlas/tools/find_orphans.py:49-60`, `code_atlas/tools/reachable_from.py:49-62`,
`code_atlas/tools/reach_shared.py:85-103`. Tier semantics: PLAN §8.2, R5.2.
Origin: [028](028_index-health-metrics.md) introduced the payload; field retro round 1 (`v0.1.0`, commit
`e117b47`) §3e is where the ambiguity cost a real decision.
