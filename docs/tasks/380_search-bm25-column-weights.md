---
id: 380
slug: search-bm25-column-weights
title: 'Inside a search band, a hit on a file path ranks level with a hit on the symbol name — evidence-gated'
phase: 2
milestone: Retrieval
status: deferred
depends_on: [180]
---

## Why this exists

`search_symbol` orders by the exact/prefix band (180), container-demote, mirror preference, then
`nodes_fts.rank` (`store.py:260-264`). That rank is BM25 with **equal weight** on every indexed
column — `name`, `qualified_name`, `file_path`, `params`. So within the substring band a symbol
whose only match is its directory can tie with or outrank one whose name matches.

context-mode weights its title column 5x in `bm25()` (its `src/store.ts:592`; idea only, ELv2).
Its other ranking machinery — RRF over porter + trigram, proximity reranking — is rejected for
identifiers, and 180 rejected opaque re-ranking.

**Evidence gate:** no field report yet shows a misranked page. This ticket opens only when one
does, or when 378's measurement turns one up.

## Scope

1. Measure first: on the pinned samples, count substring-band pages where a path- or params-only
   hit sits above a name hit.
2. Only if that count is non-trivial: `bm25(nodes_fts, w_name, w_qname, w_path, w_params)` in
   `_SEARCH_ORDER`, weights chosen from the measurement. No schema change; bands untouched.

## Acceptance criteria

- **AC1:** the measurement is recorded in the task with the samples and query set it used.
- **AC2:** if shipped, a fixture where A matches only by `file_path` and B by `name` ranks B
  first inside the substring band; exact/prefix bands are byte-identical to today.
- **AC3:** if not shipped, the task closes with the count that decided it.
