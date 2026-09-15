---
id: 282
slug: a-mirror-hit-names-a-counterpart-that-is-not-in-the-index
title: 'A mirror-ordered search hit names its `mirror_counterpart` by prefix-substituting the pair, so a file whose sibling was deleted or never indexed still gets a confident counterpart path that does not exist — the exact divergence `no_counterpart` was built to mark — while `attach_mirror_search_fields`, the function that was meant to carry these fields, ships unused'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [277, 115]
---

## Why this exists

277 (#361) ranks search hits inside their exactness band by stamped mirror pairs and puts a
`mirror_counterpart` on each mirrored hit. The decoration is `decorate_mirror_hits`
(`code_atlas/mirror_search.py:120`):

```python
known = {str(hit.get("file", "")) for hit in results if hit.get("file")}
...
answer = resolve_counterpart(path, pairs, known | _counterpart_candidates(path, pairs))
```

`_counterpart_candidates` (`:141`) **synthesizes** the counterpart path by prefix substitution
(`src/x.php` → `legacy/x.php`) and unions it into the known set — so `resolve_counterpart` answers
`COUNTERPART` for a path that may not be in the index at all. A file whose mirror sibling was deleted,
renamed, or never indexed (a genuinely *diverged* file) therefore gets a confident `mirror_counterpart`
pointing at a file that does not exist. That is precisely the case `NO_COUNTERPART`
(`code_atlas/onboarding/mirrors.py:46`) exists to mark — the honest "the pair diverged here" answer — and
this path routes around it. It is the empty-vs-unmeasured shape again (272/238): naming a sibling that
is not there reads to an agent as "the counterpart is `legacy/x.php`", not "there is no counterpart".

Separately, `attach_mirror_search_fields` (`code_atlas/mirror_search.py:109`, exported at `:37`) has no
caller in `code_atlas/` or `tests/` — `search_symbol` calls `decorate_mirror_hits` directly. It is dead
surface that either should carry the counterpart/order fields (one attach point, tested) or be removed.

## Scope / Deliverables

- **A counterpart is named only when it is in the index.** Restrict `decorate_mirror_hits` to
  counterparts that actually exist among indexed files; a synthesized-but-absent sibling yields no
  `mirror_counterpart` (and, where the payload should say so, a `no_counterpart`-style marker rather
  than silence — decide per 061).
- **Resolve `attach_mirror_search_fields`.** Either route the fields through it (single tested attach
  point) or delete it and its export.

## Constraints

- R5.6: the counterpart is a stored fact (an indexed file), never a string the pair rule can spell.
- 061: no new field on a hit that has no counterpart, unless the payload's honesty needs the marker;
  a single-tree repo (no pairs) stays byte-identical (277's AC2).
- R4.2: deterministic — same index, same counterpart decision.
- Do not change 277's ordering; this ticket is about the counterpart *value*, not the band order.

## Acceptance criteria

- A hit on a file whose synthesized sibling is **not** in the index gets **no** `mirror_counterpart`
  (was: a fabricated path).
- A hit whose sibling **is** indexed still gets the correct `mirror_counterpart` (unchanged from 277).
- `attach_mirror_search_fields` is either covered by a test through a real caller or removed with its
  export.
- 277's mirror-order and single-tree byte-identical tests still pass.

## References
`code_atlas/mirror_search.py:109,120,133,141`, `code_atlas/onboarding/mirrors.py:46` (`NO_COUNTERPART`),
`code_atlas/tools/search_symbol.py:327-329`, [277](277_page-one-ranks-the-tree-that-cannot-run.md),
115 (mirror subtrees / `find_mirror_subtrees`). Origin: review of #361, 2026-09-15 (non-blocking follow-up).

---

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 282 — mirror counterpart must be indexed (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: (1) omit mirror_counterpart when sibling absent (061 — no new marker field); (2) route search_symbol through attach_mirror_search_fields rather than delete. Citation: ticket Scope bullets + Constraints 061.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=2 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | synthesized counterpart not in index | indexed-only known set | D1 | AC1 | ✅ |
| C1 | Constraints | R5.6 stored fact | file_paths as known | D1 | AC1 | ✅ |
| C2 | Constraints | 061 omit field / single-tree identical | no marker; AC4 | D1 | AC1·4 | ✅ |
| C3 | Constraints | do not change 277 ordering | decorate only counterpart value | D1 | AC4 | ✅ |
| R1 | Scope | counterpart only when indexed | drop _counterpart_candidates | D1 | AC1–2 | ✅ |
| R2 | Scope | resolve attach_mirror_search_fields | route search_symbol through it | D1 | AC3 | ✅ |
| AC1 | AC | absent sibling ⇒ no field | proving | D2 | proving | ✅ |
| AC2 | AC | indexed sibling still named | proving | D2 | proving | ✅ |
| AC3 | AC | attach covered or removed | proving via caller | D1 | proving | ✅ |
| AC4 | AC | 277 order + single-tree tests pass | proving | D2 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: _counterpart_candidates unions synthesized paths into known, so resolve_counterpart returns COUNTERPART for absent files.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R5.6 ✅ · R4.2 ✅ · R7.6 ✅`

Ran at f3deb8cdeb5659de678e48006802ca51b4296baa

```
$ .venv/bin/python -m pytest tests/test_mirror_aware_search_order.py -q --tb=no
....                                                                     [100%]
4 passed in 0.54s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: pass store.file_paths() as indexed; remove synthesizer; search_symbol calls attach_mirror_search_fields.
- Rejected: emit no_counterpart on every diverged hit (061 weight); delete attach and keep decorate-only (ticket prefers one attach point).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_mirror_aware_search_order.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | indexed-only counterpart + attach route | mirror_search · search_symbol | search mirror fields | 2/2 |
| D2 | proving absent sibling | tests/test_mirror_aware_search_order.py | — | 1/1 |

## Phase 3 — Execute

**Branch:** feat/282-mirror-counterpart-must-be-indexed
**Axis 1:** mirror_search · search_symbol · proving test.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at f3deb8cdeb5659de678e48006802ca51b4296baa

```
$ .venv/bin/python -m pytest tests/test_mirror_aware_search_order.py -q --tb=no
....                                                                     [100%]
4 passed in 0.54s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — CLEAN (8 met · 0 not met · 0 can't tell); agent 5919242b-3725-452d-9262-ecaad79aad48
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_mirror_aware_search_order.py — 4 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

PR review (#373): the indexed path set was re-read per subject and probed as a tuple — `SELECT path FROM files` once per sweep subject, then a linear scan per hit. It is now read once per call as a `frozenset`, and not at all when the stamp has no pairs. Proving: `test_path_scan_is_once_per_call_not_per_subject`, `test_no_pairs_never_scans_the_path_set` — 6 passed.

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN (.mango/gate-282.log)
PR: https://github.com/cuongdinhngo/code-atlas/pull/373

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
