---
id: 046
slug: resolver-qname-candidate-dedupe
title: Resolver — dedupe candidates by qualified_name (kill duplicate edges, stop the false downgrade)
phase: 1.5b
milestone: Robustness
status: in-progress
depends_on: [011, 027, 043]
---

## Goal
An FQN candidate lookup returns one node **per file** that declares the name, and the resolver turns
each extra node into a sibling edge. But `nodes_by_qualified_names` groups by `qualified_name`
(`store.py:374-380`), so every candidate in a group carries the *same* qname, and `_queue_candidates`
sets `sibling["target_qname"] = candidate["qualified_name"]` (`resolver.py:131`) — a value identical to
the first candidate's. The edge table stores a qname, not a node id, so "which file's copy" is not
representable in the first place. Those siblings are therefore **exact duplicates by construction**:
every column but `id` is equal.

Two consequences, both measured on a large private monorepo that carries two regional copies of the
same legacy tree (35,220 qnames declared in more than one file):

- **38.8 % of the graph is redundant rows** — 1,099,385 of 2,836,428 edges, distributed as CALLS
  1,059,283 · NEW 31,629 · EXTENDS 8,115 · IMPLEMENTS 354 · ALIASES 4. Verified pair: edge ids 118930
  and 1270419, identical in every column but `id`.
- **Edges are downgraded for a multiplicity that is not ambiguity.** `computed = "RESOLVED" if
  len(hits) == 1 else "HEURISTIC"` (`resolver.py:67`) counts *nodes*, so a name that resolves to
  exactly one qname in several files is marked HEURISTIC. 1,655,664 HEURISTIC FQN edges on that repo
  have a target qname declared in more than one file, against 484,983 RESOLVED edges in total (17 %).

Downstream, a nav tool joining on `target_qname` returns every hit twice, so half of `max_results` and
half of the response tokens are spent on nothing — and a duplicated row reads to an agent as a wrong
answer, not as a duplicate.

## Scope / Deliverables
- **Tier from distinct qnames, not node count.** In `resolve_edges`, compute the candidate set's
  distinct `qualified_name` values and derive `computed` from that count. `_weaker_tier` still applies,
  so an adapter's HEURISTIC claim is never promoted (R5.2).
- **Siblings per distinct qname.** In `_queue_candidates`, iterate distinct `qualified_name` values
  rather than candidate rows. Order-preserving, so the first candidate still wins the original edge
  (R4). This is a no-op for the `nodes_by_names` fallback, where candidate qnames genuinely differ.
- **Correct the test that pins the old behaviour.** `tests/test_resolver.py:112-133` seeds one qname in
  two files and asserts two linked edges both HEURISTIC — it encodes exactly this defect. It must
  assert one edge, RESOLVED.
- **New tests** for the shape that matters: one qname in N files yields one edge at RESOLVED; distinct
  qnames still yield one edge each and stay HEURISTIC; `max_candidates` still caps the distinct-qname
  fan-out; re-running the resolve is idempotent.

## Constraints
- **No contract change.** The vocabulary and the tier values are untouched, so `contract_version` does
  not move (R3). No schema change either, so `schema_version` does not move.
- **Language-agnostic (R1.1) and in the right layer (R1.4)** — this is the resolver's arithmetic; the
  store keeps owning SQLite and no adapter is involved.
- **Deterministic (R4).** Dedupe must preserve source order (`dict.fromkeys`, not `set`), so identical
  input still gives identical rows.
- **Never promote an incoming claim (R5.2).** Only `computed` changes; `_weaker_tier(incoming,
  computed)` still governs the result.
- **Nothing is lost.** The `nodes` table still holds every per-file declaration and `search_symbol`
  still lists them; only the edge duplication goes away.
- Existing indexes must be rebuilt for the change to take effect — edges are written at resolve time.
  Say so where operators will read it.

## Acceptance criteria
- One qname declared in N files, one incoming FQN edge → exactly **one** linked edge, at RESOLVED
  (asserted, N ≥ 2).
- An adapter-emitted HEURISTIC edge with a single-qname multi-file target stays HEURISTIC (asserted) —
  R5.2 holds.
- Candidates with genuinely distinct qnames still produce one edge each, all HEURISTIC, still capped by
  `max_candidates` (the existing method-name tests keep passing unchanged).
- Re-running `resolve_edges` over an already-resolved store adds no rows (idempotence, asserted).
- No exact-duplicate edge rows survive a full build of a tree that declares one qname in two files
  (asserted at the store level: group by every column but `id`, expect no group > 1).
- `pytest`, `ruff`, `mypy` green; the tokens-to-answer fixture gate still passes, with its floor
  recalibrated if the ratio moves.

## References
`code_atlas/resolver.py:57-83` (the FQN lookup and the fallback), `:67` (the tier computation),
`:119-133` (`_queue_candidates`); `code_atlas/store.py:374-380` (`nodes_by_qualified_names`, keyed by
qname), `:368-372` (`nodes_by_names`, keyed by name — the case where siblings are real), `:59`
(`UNIQUE(qualified_name, file_path)`, why one qname legitimately has N nodes).
`tests/test_resolver.py:112-133` (the test that pins the defect), `:136-154` (the distinct-qname case
that must not change). R5.2 (never promote), R4 (determinism), R1.1/R1.4 (layering).
Origin: the local-tier measurement in [045](045_tokens-to-answer-local-repo.md), which returned every
nav row twice.
