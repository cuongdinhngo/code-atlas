---
id: 286
slug: the-mirror-pairs-are-stamped-and-the-tool-that-forms-the-belief-never-reads-them
title: '277 stamps the mirrored subtree pairs and only `search_symbol` reads them, so `read_symbol` returns a perfect body for a port that no request reaches and says nothing about the twin that serves it — the caveat naming that exact limit is printed on `find_callers`, which is not where an agent forms the belief "this is the code that runs"'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [277, 282, 276]
---

## Why this exists (field retro — the anchor repo, round 24 §4, 2026-09-15)

A ticket named a controller action by qname. `read_symbol` on exactly that qname returned a perfect,
current body whose emitted payload lacked a key the front end reads — so the session concluded the
feature was broken, wrote that into its notes, and nearly shipped a fix to working code. The live
request is served by the **mirror twin** under the read-only tree; the ported symbol is not reachable.
Live measurement overturned it; the graph did not.

The tool answered correctly. The retro's diagnosis is where the payload is misplaced:

> *"That caveat is exactly right and it is printed on the **wrong tool**. It appears on `find_callers`,
> where I was already thinking about reachability. It does **not** appear on `read_symbol`, which is
> where an agent forms the belief 'this is the code that runs'."*

`read_symbol` today has exactly one ambiguity signal, and it is keyed on the **same qname** resolving
to several definitions (`subject_ambiguous` + `ambiguous_definitions`, `read_symbol.py:79-85`). Two
rounds rate that refusal load-bearing and it stays. A mirror twin is a *different* qname in a
different subtree, so nothing fires — the honest refusal and the silent wrong answer are the same tool
one namespace apart.

The ingredient already exists and is already stamped. 277 derives the mirrored subtree pairs at build
time and 282 restricted a counterpart to files the index actually holds; `mirror_search.py` is imported
by `search_symbol`, `indexer` and `store` — and by nothing else. So the fact that would have stopped
this is computed, deterministic, honest about divergence, and addressable from one tool. That is 278's
shape exactly, and 278 is the ask the field ranked first the round before.

## Scope / Deliverables

- **A found symbol whose file sits on one side of a stamped mirror pair says so**, naming the indexed
  counterpart — reusing 282's rule that a counterpart is named only when it is in the index, so a
  genuinely diverged file gets the honest negative rather than a synthesized path.
- **The field must not claim dispatch.** It says a twin exists and that this tool cannot say which one
  a request reaches; it never asserts which is live. The existing `caveat_limits` wording is the
  precedent — a boundary, not a verdict.
- **Decide the scope of the signal once.** Whether it belongs on every mirrored hit or only where the
  kind makes dispatch plausible is a 061 judgement to argue in design, not to assume here.

## Constraints

- R1.1 / R2: mirrored-tree pairs come from the stamped derivation, never from a path convention, a
  framework name or a repo's directory names.
- 061: a repo with no stamped pairs stays byte-identical — this must cost nothing on a single-tree repo.
- R5.6: the counterpart is an indexed file (282), never a string the pair rule can spell.
- Do not weaken `subject_ambiguous`: two rounds call the refusal load-bearing and it is unchanged here.
- R4.2: same index, same decision.

## Acceptance criteria

- A `read_symbol` hit inside a stamped mirror pair whose counterpart is indexed names it.
- The same hit whose counterpart is **not** indexed gets the honest negative, not a synthesized path.
- A repo with no stamped pairs produces byte-identical payloads to today.
- No field asserts which side a request reaches.
- 277's ordering and 282's counterpart tests still pass.

## References
`code_atlas/mirror_search.py:110,119`, `code_atlas/tools/read_symbol.py:79-85`,
`code_atlas/tools/search_symbol.py:327-329`,
[277](277_page-one-ranks-the-tree-that-cannot-run.md),
[282](282_a-mirror-hit-names-a-counterpart-that-is-not-in-the-index.md),
[278](278_the-writer-set-is-computed-for-one-check-and-addressable-from-nothing.md).
Origin: field retro round 24 §4, 2026-09-15 — "the most useful thing in this retro".

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 286 — read_symbol names mirror twin (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** M · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: (1) signal on every kind on a stamped pair — Class and Method both form "code that runs"; filtering CALLABLE would miss the incident Class. Cite ticket Scope + Why. (2) `mirror_no_counterpart` + `caveat mirror_twin` boundary text — never a live-side verdict. Cite ticket Scope bullet 2 + AC4.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=5 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | twin invisible on read_symbol | attach mirror fields on found hit | D1 | AC1 | ✅ |
| C1 | Constraints | R1.1/R2 stamped pairs | load_mirror_search_stamp | D1 | — | ✅ |
| C2 | Constraints | 061 no pairs | early return | D1 | AC3 | ✅ |
| C3 | Constraints | R5.6 indexed only | resolve_counterpart 282 | D1 | AC2 | ✅ |
| C4 | Constraints | subject_ambiguous unchanged | no attach on ambiguous | D1 | — | ✅ |
| C5 | Constraints | R4.2 | deterministic stamp | D1 | — | ✅ |
| R1 | Scope | name indexed counterpart | mirror_counterpart | D1 | AC1 | ✅ |
| R2 | Scope | no dispatch claim | CAVEAT_MIRROR_TWIN | D1 | AC4 | ✅ |
| R3 | Scope | scope once | every kind on pair | D1 | — | ✅ |
| AC1 | AC | names indexed twin | proving | D2 | proving | ✅ |
| AC2 | AC | honest negative | proving | D2 | proving | ✅ |
| AC3 | AC | no stamp identical | proving | D2 | proving | ✅ |
| AC4 | AC | no live-side claim | caveat text | D1 | proving | ✅ |
| AC5 | AC | 277/282 still pass | proving | D2 | proving | ✅ |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: mirror stamp read only by search_symbol; read_symbol forms the "runs" belief without twin.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R1.1 ✅ · R5.6 ✅ · R7.6 ✅`

Ran at 02f4bab7e1ecbe39e6740cd7865ecbe1a2a0bf7f

```
$ .venv/bin/python -m pytest tests/test_mirror_aware_search_order.py -q --tb=no
......                                                                   [100%]
6 passed in 1.91s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: `attach_mirror_read_fields` + CAVEAT_MIRROR_TWIN on found read_symbol; reuse resolve_counterpart.
- Rejected: CALLABLE-only (misses Class incident); synthesizing paths (282).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_read_symbol_mirror_twin.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | mirror read attach + caveat | mirror_search.py, read_symbol.py, nav_result.py | mirrored reads | 1/1 |
| D2 | proving | tests/test_read_symbol_mirror_twin.py | — | 1/1 |

## Phase 3 — Execute

**Branch:** feat/286-read-symbol-names-mirror-counterpart
**Axis 1:** mirror_search · read_symbol · nav_result · tests.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at 02f4bab7e1ecbe39e6740cd7865ecbe1a2a0bf7f

```
$ .venv/bin/python -m pytest tests/test_read_symbol_mirror_twin.py -q --tb=no
....                                                                     [100%]
4 passed in 0.56s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — round-1 NOT CLEAN (1 can't tell: AC5 277/282 suites); verify-only — ran tests/test_mirror_aware_search_order.py + proving (10 passed). agent b7a9950a-6194-48fc-9e11-aa27b51f2c87

Verify-only:

Ran at 02f4bab7e1ecbe39e6740cd7865ecbe1a2a0bf7f

```
$ .venv/bin/python -m pytest tests/test_mirror_aware_search_order.py tests/test_read_symbol_mirror_twin.py -q --tb=no
..........                                                               [100%]
10 passed in 1.32s
```

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_read_symbol_mirror_twin.py — 4 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN (.mango/gate-286.log)
PR: https://github.com/cuongdinhngo/code-atlas/pull/380

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
