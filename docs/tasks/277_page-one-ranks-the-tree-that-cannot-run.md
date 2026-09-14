---
id: 277
slug: page-one-ranks-the-tree-that-cannot-run
title: 'Search ranks an exact name by match band and relevance and knows nothing about which subtree can run, so in a repo with two read-only mirrored trees the live class is third and the next forty rows are the copies — while the graph already computes the mirror pairs deterministically for the onboarding artifact and no nav tool reads them'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [115, 180, 265]
---

## Why this exists (field retros — the anchor repo, rounds 21 §2.1 and 22 §5, 2026-09-14)

Round 21, one `search_symbol` subject: `total_count: 290`, first two hits
`legacy/beta/web/include/PdfReport.php` and `legacy/alpha/…`, the unified `src/` class **third**,
then forty rows of legacy properties and constants. The repo's loudest standing rule is *never edit
`legacy/`* — both trees are being deleted.

> *"I knew to skip them. An agent that did not would have read, reasoned about, and possibly edited
> a file that cannot run."*

Round 22 logged the same shape from the other end: `"Assessment"` → `total_count: 5224`, first page
dominated by `.js`, the PHP class tenth. Passing `kind` fixes that one; nothing fixes the mirror one,
because both hits are the same kind, the same name, the same language.

The asymmetry worth noting: `read_symbol` **refuses** on exactly this repo shape
(`subject_ambiguous`, three definitions, no body — round 20 §3.2 calls the refusal load-bearing), and
two rounds rate it correct. Search faces the same ambiguity and silently picks an order instead.

The ingredient exists. `onboarding/mirrors.py:163` (`find_mirror_subtrees`) already derives mirrored
subtree pairs from the graph, deterministically, with an honest negative (`outside_mirror`) and two
gates against overstating adjacency — built for 115's panel, read by no nav tool.

## Scope / Deliverables

- **A mirror-aware ordering signal for name search**, derived from the same 115 computation, not from
  a path-name list. Where a repo has no mirrors, nothing changes and nothing is paid.
- **Rows say which side they are on.** A hit inside a mirror pair carries its counterpart — the
  answer to *"is this the copy or the original?"* is one field, not a second call.
- **Ordering is a stated rule, never a silent preference.** 265's verdict applies: a page the reader
  cannot explain is a page they read as spelling. Whatever decides the order says so in the payload.
- **No repo's names.** Which side of a mirror is canonical is the *repo's* fact — R2 forbids encoding
  `src/` or `legacy/` anywhere. The graph can rank by measurable properties (which side carries
  inbound edges from the rest of the graph, which is stub-only), or the operator names the preference
  in config. Not by a directory name we ship.

## Constraints

- R2 / R2.2: no sample-repo directory names, no framework list, in the core or an adapter.
- R4.2: ordering stays byte-reproducible.
- R4.3: the mirror computation is bounded and must not be run per query if that costs a scan — it is
  a build-time or cached fact, the way 258 converted the expensive case to build-time ranking.
- 180's band order (exact/prefix first, relevance inside the band) is not replaced; this decides
  *within* a band.

## Acceptance criteria

- A fixture with two mirrored subtrees and one non-mirrored tree: the exact-name hit outside the
  mirrors ranks above both copies, and each mirrored row names its counterpart.
- A fixture with no mirrors produces byte-identical results and no new field.
- The deciding rule is named in the payload and pinned by a test.
- No directory name from any sample repo appears in `code_atlas/` or `adapters/` (the existing R2 CI
  grep still passes).

## References
`code_atlas/onboarding/mirrors.py:163,215`, `code_atlas/store.py:388–391` (`is_direct_match` band),
`code_atlas/tools/search_symbol.py`, field retro round 21 §2.1 / §8.3, round 22 §5 / §8.5,
round 20 §3.2 (the refusal that is right), [115](115_mirror-subtree-detection.md),
[180](180_search-ranks-a-near-miss-above-exact-matches.md), [265](265_the-default-page-order-is-the-alphabet.md).
