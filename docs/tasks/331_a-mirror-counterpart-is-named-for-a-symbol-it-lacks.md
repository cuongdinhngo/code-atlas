---
id: 331
slug: a-mirror-counterpart-is-named-for-a-symbol-it-lacks
title: "mirror_counterpart names the twin FILE on a function hit, so it reads as 'the other region has this function' when it does not — on the exact cross-region question the field asks daily"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [277, 282, 286]
---

## Why this exists (field retro, 2026-09-23 — FIELD-1621/1615 batch)

`search_symbol` on a page-file function returned it with `mirror_counterpart: <other-region page>`.
The session read that as *the other region has this function too*. It does not: a text search of
the counterpart file found **zero** occurrences. The retro: *"misleading on the exact region
question I was asking."*

**The field is file-level by construction.** 277 stamps mirrored **subtree** pairs; `decorate_mirror_hits`
and `label_mirror_rows` (`mirror_search.py:150-192`) call `resolve_counterpart(path, …)` on the hit's
file and attach the twin path when that file is indexed. The symbol is never consulted. On a File
hit that is the whole truth; on a Function / Method / Class hit it silently widens to a claim about
the symbol. 282 already refused to name a counterpart that is not indexed — this is the same
honesty one level down.

## Goal

On a symbol hit, a named counterpart means the symbol's twin exists there, or the payload says the
file exists and the symbol does not.

## Scope / Deliverables

1. **For non-File hits, check the counterpart file for a definition with the same name segment**
   (a `GraphStore` lookup scoped to that file; one batched query per page).
2. **Present ⇒ today's `mirror_counterpart`. Absent ⇒ a distinct field** (e.g. the file named plus
   a flag that the symbol is not in it) — the naming is the design call.
3. **Applies wherever 286/313 label mirrors**: `search_symbol`, `read_symbol`, nav rows.

## Constraints

- **061** — File hits, and symbol hits whose twin exists, are byte-identical.
- **R1.1** — match on the contract's name segment; no language or directory-name branch.
- **R1.4** — the lookup lives in `store.py`.
- Never assert which twin a request reaches (286's rule stands).

## Acceptance criteria

- **AC1** Fixture mirror pair; a function present only on one side → its hit does not carry a bare
  `mirror_counterpart`; red-arm on today's code.
- **AC2** A function present on both sides carries `mirror_counterpart` as today.
- **AC3** One query per page, not per hit (asserted by a query count or a store-call spy).

## References
`code_atlas/mirror_search.py:110-192`; `code_atlas/tools/search_symbol.py`; tickets 277, 282, 286, 313.
