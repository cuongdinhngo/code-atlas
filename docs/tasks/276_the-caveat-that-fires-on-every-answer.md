---
id: 276
slug: the-caveat-that-fires-on-every-answer
title: '`cross_language_relation_unmodelled` is language-scope, so in a multi-language repo it decorates every caller and reference payload — including a 78-site, fully-correct, single-language answer — and `authoritative: false` therefore fires identically on the answer an agent should act on and the one that would mislead it: a flag that is always on cannot warn'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [221, 238, 243]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 20 §5)

Every `find_callers` and `find_references` payload in that session carried:

```json
"authoritative": false,
"authoritative_caveats": ["cross_language_relation_unmodelled"],
"caveat_limits": {"cross_language_relation_unmodelled": "This answer is reachability within one
  language's call graph and does not establish which entry point the front end invokes."}
```

…including the 78-site PHP→PHP answer that was completely correct and that the session acted on, and
the answer that was a false zero ([272](272_a-partition-that-is-all-tests-answers-ok.md)). Same flag,
same caveat, opposite trustworthiness.

The predicate is deliberate and 221/238 argued it: an unmeasured crossing is unmeasured whether or
not this answer found in-language hits (`coverage.py:71–94`). What that argument did not weigh is
**dynamic range**. In a repo indexing three languages with no `*->php` pair, the condition holds for
every subject in the repo, forever — so the field partitions nothing, and the retro's conclusion is
the one any reader reaches: *"read the reason code, not the flag."* A flag nobody reads is tokens on
every payload plus a lost warning on the payload that needed one.

The retro's own suggestion — suppress when `cross_language.linked + .unlinked == 0` — is one
comparison, and it is **not obviously right**: a census of zero is the case where *nothing* was
measured. That tension is what this ticket has to resolve rather than assume.

## Scope / Deliverables

- **Decide, with the evidence, what `authoritative: false` is for** — and record the verdict in
  §19. Either it discriminates (and a condition true of every subject in the repo must not raise it),
  or it is a standing property of a language's coverage (and it belongs on `get_index_status` and in
  the tool description, charged once, not on every answer).
- **Whichever way it goes, one repo-wide truth is stated once.** 243 already bounds the census on the
  status payload; a per-answer copy of a per-repo fact is R7.6 applied to payloads.
- **Keep the discriminating cases discriminating.** Where a `*->L` pair exists in the census and this
  subject's answer could genuinely have crossed, the caveat stays.
- Measure the cost: the caveat plus `caveat_limits` prose on every nav answer, at the session call
  counts the retros record.

## Constraints

- 221/238 are decisions; this reopens them only with the field evidence above, and the outcome is a
  §19 entry either way — including *"no change, and here is why the retro's read is wrong"*.
- R5.6 is not negotiable: nothing here may turn an unmeasured crossing into an implied zero. If the
  caveat moves off the answer, the answer must still not claim authority it lacks.
- No language branch (R1.1): the predicate stays keyed to the stamped census.

## Acceptance criteria

- A §19 entry naming the verdict and the evidence it was decided on.
- A test that pins the chosen behaviour on a three-language index with an empty `cross_language`
  census, and on one with a real `*->L` pair.
- If the caveat narrows: a regression test that an answer which *could* cross still carries it.
- The tool descriptions and `docs/design/payload.md` agree with the new rule in the same commit.

## References
`code_atlas/tools/coverage.py:71–94`, `code_atlas/tools/nav_result.py:652`,
`code_atlas/tools/find_callers.py:458`, `code_atlas/tools/find_references.py:292`,
field retro round 20 §5 / §9, [243](243_the-capability-predicate-221-relies-on-is-attached-at-verbose-only.md),
[272](272_a-partition-that-is-all-tests-answers-ok.md), PLAN §19 (221, 238).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 276 — cross_language hit-caveat dynamic range (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** M · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: `authoritative: false` is discriminating (payload.md) — cite field retro + R7.6; empty census → status (243), not every hit. Zeros keep 221 (R5.6).

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=4 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | always-on flag | hit caveat needs edges | D1 | AC1 | ✅ |
| C1 | Constraints | 221/238 reopen with evidence | §19 | D2 | AC1 | ✅ |
| C2 | Constraints | R5.6 | zeros keep upgrade | D1 | AC3 | ✅ |
| C3 | Constraints | R1.1 | stamp census | D1 | — | ✅ |
| R1 | Scope | decide + §19 | discriminating | D2 | AC1 | ✅ |
| R2 | Scope | state once | status empty census | D1 | AC1 | ✅ |
| R3 | Scope | keep discriminating | edges>0 keeps caveat | D1 | AC2 | ✅ |
| R4 | Scope | measure cost | docs | D3 | — | ✅ |
| AC1 | AC | §19 + empty census pin | proving | D3 | proving | ✅ |
| AC2 | AC | *->L / could-cross | proving | D3 | proving | ✅ |
| AC3 | AC | could-cross still carries | proving | D3 | proving | ✅ |
| AC4 | AC | TOOLS/payload agree | docs | D3 | — | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: 238 hit-path used language-scope with empty census → always-on.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R5.6 ✅ · R7.6 ✅ · R1.1 ✅ · R6.1 ✅`

```
Ran at f33fc3efc61f3be85d4fe4436ffc80f90a2aa957
$ .venv/bin/python -m pytest tests/test_find_callers_cross_language_unmodelled.py::test_a_cross_language_zero_is_not_no_matches -q --tb=no
1 passed
```

`BASELINE: green`

## Phase 2 — Design

- Approach: hit-path attach only if `cross_language_census_has_edges`; zeros unchanged; §19 fold into 238.
- Rejected: move caveat only to status (loses discriminating hit cases). Rejected: suppress all empty-census including zeros (breaks 221 AC1).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_cross_language_hit_caveat_dynamic_range.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | has_edges gate | coverage + callers/refs | hit path | 3/3 |
| D2 | §19 + payload | PLAN · payload | docs | 1/1 |
| D3 | proving + 238 pin retarget | tests | — | 4/4 |

## Phase 3 — Execute

**Branch:** feat/276-the-caveat-that-fires-on-every-answer
**Axis 1:** coverage, find_callers, find_references, tests, PLAN, payload.
**Axis 2:** implemented-as-approved.

**Verification sweep**

```
Ran at f33fc3efc61f3be85d4fe4436ffc80f90a2aa957
$ .venv/bin/python -m pytest tests/test_cross_language_hit_caveat_dynamic_range.py tests/test_find_callers_cross_language_unmodelled.py -q --tb=line
20 passed
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — round-1 NOT CLEAN (find_references docstring + cost); verify-fix landed; no re-dispatch
`REVIEW: CLEAN` (verify-only)

## Phase 5 — Finalise

Outward: push + open PR. Gate GREEN (.mango/gate-276b.log)

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGERTOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
