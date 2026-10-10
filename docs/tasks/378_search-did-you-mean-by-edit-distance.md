---
id: 378
slug: search-did-you-mean-by-edit-distance
title: 'A one-letter typo in a symbol name answers empty, and the token route cannot suggest the right name'
phase: 2
milestone: Retrieval
status: todo
depends_on: [180, 253]
---

## Why this exists

`fts_term` (`store.py:458`) searches the whole query as one literal trigram phrase, so a
misspelled name has no substring hit. The miss path then tries `token_candidates` (253), which
ranks names sharing a `name_tokens` token (`contract.py:371-389`, `TOKEN_CANDIDATE_K=5`). A typo
inside the distinctive token defeats it. Observed on this repo's index, 2026-10-09, one sweep:

- `full_biuld` → `results: []`; the five candidates matched only `full`, and
  `indexer.full_build` is not among them.
- `resolves_insdie` → `containment.resolves_inside` ranked 4th of 5.
- `estimate_tokesn` → `tokens.estimate_tokens` ranked 1st (rescued by the `estimate` token).

Each miss costs a guessed retry or a fall-back to grep + `Read` — the exact cost the product
exists to remove (PLAN §1 Goals). context-mode corrects typos by Levenshtein with thresholds
1/2/3 by word length, but ties go to scan order (its `src/store.ts:144-148, 1195-1240`; idea only,
ELv2). 253's rejected alternatives never considered edit distance.

## Scope

1. A store method (`store.py` stays the sole SQLite owner) returns names within an edit distance
   of the query: prefilter by trigram OR over the query's 3-grams, then Levenshtein on casefolded
   `name`, ordered by `(distance, casefolded name, qname)` — a total order (R4.2).
2. `search_symbol` consults it when a subject's results are empty, alongside or after
   `token_candidates`. Suggestions live beside `results`, never in it (R5.6); each carries its
   distance.
3. An exact or prefix hit never takes this path; a `queries` sweep applies it per subject.
4. The tool description names the new field; the 24-tool surface does not grow.

## Assumptions to prove at design

- Whether the field merges into `candidates` (with `edit_distance`) or is its own reason — and
  whether either moves `CONTRACT_VERSION` (101's CL-1 reasoning says payload vocabulary does not;
  confirm against the sole-source gate).
- The prefilter keeps the cost bounded on the anchor index (~22.9k files); measure, do not assume.

## Acceptance criteria

- **AC1:** on a fixture, `getUserByld` suggests `getUserById` at distance 1.
- **AC2:** two equidistant names come back in name order; 50 repeated calls are byte-identical.
- **AC3:** a query with an exact hit returns exactly today's answer (byte-identical).
- **AC4:** on this repo's index, `full_biuld` suggests `full_build`.
- **AC5:** the miss-path cost on the anchor index is recorded in the task, against today's.
