---
id: 277
slug: page-one-ranks-the-tree-that-cannot-run
title: 'Search ranks an exact name by match band and relevance and knows nothing about which subtree can run, so in a repo with two read-only mirrored trees the live class is third and the next forty rows are the copies — while the graph already computes the mirror pairs deterministically for the onboarding artifact and no nav tool reads them'
phase: 1.5b
milestone: Agent-trust
status: done
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


---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 277 — mirror-aware search order (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** M · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: canonical side = higher external inbound (measurable), not directory names (R2). Cite ticket Scope.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | mirrors silent in search | stamp + order | D1 | AC1 | ✅ |
| C1 | Constraints | R2 no names | inbound metric | D1 | AC4 | ✅ |
| C2 | Constraints | R4.2 | deterministic | D1 | — | ✅ |
| C3 | Constraints | R4.3 build stamp | indexer | D1 | — | ✅ |
| C4 | Constraints | 180 band stays | within band | D1 | AC1 | ✅ |
| R1 | Scope | mirror-aware order | prefer key | D1 | AC1 | ✅ |
| R2 | Scope | counterpart field | hit field | D1 | AC1 | ✅ |
| R3 | Scope | stated rule | search_order | D1 | AC3 | ✅ |
| R4 | Scope | no sample names | R2 | D1 | AC4 | ✅ |
| AC1 | AC | fixture outside>copies | proving | D2 | proving | ✅ |
| AC2 | AC | no mirrors identical | proving | D2 | proving | ✅ |
| AC3 | AC | rule named | proving | D2 | proving | ✅ |
| AC4 | AC | R2 grep | gate | D2 | — | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: search ranks by band+BM25 only; 115 mirrors unused by nav.
`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R2 ✅ · R4.2 ✅ · R4.3 ✅ · R7.6 ✅`

```
Ran at 874b52904421b0fcd23356f5b2f8cd6b5e37c00d
$ .venv/bin/python -m pytest tests/test_batched_subject_sweep.py::test_the_whole_batched_payload_is_pinned -q --tb=no
```

`BASELINE: green`

## Phase 2 — Design

- Approach: stamp mirror pairs + external_inbound at build; SQL `ca_mirror_prefer`; hit `mirror_counterpart` + `search_order`.
- Rejected: path-name preference (R2). Rejected: per-query scan (R4.3).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_mirror_aware_search_order.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | stamp + UDF + decorate | mirror_search · store · indexer · search | search | 4/4 |
| D2 | proving + TOOLS | tests · TOOLS | — | 3/3 |

## Phase 3 — Execute

**Branch:** feat/277-page-one-ranks-the-tree-that-cannot-run
`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

```
Ran at 874b52904421b0fcd23356f5b2f8cd6b5e37c00d
$ .venv/bin/python -m pytest tests/test_mirror_aware_search_order.py -q
3 passed
```

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — round-1 NOT CLEAN (batch search_order); verify-fix landed; no re-dispatch
`REVIEW: CLEAN` (verify-only)

## Phase 5 — Finalise

Outward: push + open PR. Gate GREEN (.mango/gate-277b.log)

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
