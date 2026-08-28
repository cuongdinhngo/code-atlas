---
id: 183
slug: edge-health-has-no-per-language-breakdown
title: '`edge_health` is whole-graph only, so no adapter can be evaluated on the repo it was added for — the tool cannot make this measurement about itself'
phase: 1.5b
milestone: Measure
status: todo
depends_on: [136, 082, 173]
---

## Why this exists (field retro round 12 §13)

Round 12 was the first round with a two-language index in the field, and **the question the whole
round was built to answer could not be asked of the tool:**

> *"HEURISTIC share for the JS/TS slice — did the prune fix round 11's 46.8 %?"*
> **"Cannot answer. No per-language breakdown exists in any payload. This is a measurement the tool
> cannot make about itself."**

What could be reported was the whole-graph delta only: RESOLVED 55.2 % → **45.70 %**, HEURISTIC
43.9 % → **53.51 %**, across +2,435 files and +573,762 edges. Every one of those numbers is a blend
of two languages, so **neither language's own health is recoverable**, and the +9.6 pp HEURISTIC move
cannot be attributed. Round 11 had to measure the JS slice **out of band**, by building three files
in isolation, to get its 46.8 %.

## Why this is a measurement ticket and not a nice-to-have

- **It blocks every future adapter's evaluation, including the one it is most needed for.** A T-SQL
  or Python adapter lands, the whole-graph share moves, and nobody can say whether the new adapter is
  healthy or whether it dragged the average — the exact position round 12 was in for JS.
- **136 gave the HEURISTIC share an owner and a target.** A target on a blended number cannot be
  attributed to the adapter that missed it.
- **The data is already there.** `files.language` exists and 173 already reads
  `SELECT DISTINCT language FROM files` once per build for its coverage stamp; `edges.file_path`
  joins to it, and `idx_edges_tier` is already indexed. `store.edge_health()` (`store.py:580-610`)
  does one `GROUP BY confidence_tier` over the whole table.
- **It is the cheapest honest answer to "is the JS half worth 1.0 GB?"** — round 12 could only say
  *"reserve judgement"*, and one field would have replaced that with a number.

## Scope

1. `edge_health` gains a **per-language tier mix** — the same `by_tier` / `linked` / `unlinked`
   shape, keyed by the language of the edge's own file. Design records the grouping key: `files.language`
   (the adapter that produced the row) or file suffix, and why the other was rejected.
2. **Stamped per build, not computed per call.** 173's precedent: one bounded query in
   `_record_meta`, read from meta afterwards. `get_index_status` is called first by convention
   (`CLAUDE.md`), so it must not gain a `GROUP BY` over a 2.1 M-row table on the hot path.
3. **Detail-gated and omit-when-single.** A one-language index adds nothing (061); the breakdown
   belongs at `verbose`, beside `collection`, where the other reconciliation data already lives.
4. **The identity reconciles.** Per-language tier counts sum to the whole-graph `by_tier`, the way
   082's `collected − skipped == kept` reconciles — an outsider must be able to check the split
   without reading source.

### Explicitly not in scope

- Per-language node counts, or a per-language `files`/`parsed`/`failed` split. Adjacent, cheaper, and
  a separate ticket if wanted.
- Changing what a tier means, or the resolver.
- Attributing an edge to the language of its **target**. An edge belongs to the file that declared it;
  a cross-language edge is one row of the source language, and the design must say so explicitly
  because the alternative is arguable.
- Fixing any language's share. This ticket makes it visible; 136/137 own moving it.

## Constraints

- **061** — a single-language index is byte-identical; so is `minimal`/`standard`.
- **Cost** — one bounded query per build, never per answer. Measured on a two-language index of the
  anchor's size (~2.1 M edges), and the per-call read must be a meta lookup.
- **R1.1** — grouped by a language string the handshake supplied, never by a language named in the
  core. A core that reads `if language == "php"` here has lost the contract.
- **R4.2** — deterministic, stable key order.
- **R5.6** — an index built before the stamp existed says nothing rather than guessing.
- **R3** — confirm whether the field is nav or contract vocabulary.

## Acceptance criteria

1. A two-language fixture index reports a per-language tier mix, and the per-language counts **sum to
   the whole-graph `by_tier`** — pinned, and failing on today's code.
2. A single-language index is byte-identical to today (061), pinned.
3. The breakdown is absent from `minimal`/`standard` and present at `verbose`, pinned.
4. A cross-language edge is attributed to exactly one language, per the recorded rule, pinned.
5. Stamped once per build; the per-answer path adds no `GROUP BY` — measured on ~2.1 M edges.
6. A pre-stamp index says nothing (R5.6), pinned.
7. Determinism (R4.2), no language branch (R1.1), contract impact confirmed (R3).

## References

Field retro round 12 §13 (*"a measurement the tool cannot make about itself"*), §0.d (the blended
before/after table), §11.a (*"the graph got more complete and that completeness bought zero
answers"*), §13's unanswerable HEURISTIC row; round 11 A.3 measured the JS slice out of band at
46.8 % because no payload could. `code_atlas/store.py:580-610` (`edge_health`), `files.language`;
173's per-build stamp in `indexer._record_meta` is the cost precedent. Related:
[136](136_heuristic-share-has-no-owner.md) (the share's owner),
[082](082_claims-nobody-outside-can-check.md) (the reconciliation pattern),
[173](173_coverage-claims-key-on-configured-not-indexed.md) (per-build stamp, one query).
