---
id: 280
slug: a-parser-accepts-what-the-runtime-rejects
title: 'A parse-failure count answers "what could not be parsed", a reader uses it as "what cannot run", and the two differ by every compile-stage error a parser accepts by construction — a handoff built a PHP-8 upgrade argument on 2 when `php -l` found 10, including a live fatal the count was being used to rule out'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [058]
---

## Why this exists (field retro — a PHP 5.6 monolith, 2026-09-13, round 19 §4)

A prior session's handoff built its central structural argument on the index's parse-failure count:
*"66 parse failures… only 2 are the project's own code"*, concluding the PHP 8 syntax problem was a
document-generation problem. The next session ran `php -l` over the same scope and found **10**.

Four files fail to compile on *every* runtime, 5.6 included, and the index accepted all four —
a re-assigned auto-global used as a parameter name, an abstract method with a body, a redeclared
function, a method call in a property initialiser. All are **compile-stage** errors; a parser accepts
them by construction. So is the one that mattered: an unparenthesized nested ternary, valid on 5.6,
**fatal on 8.0**, in live view code. It is not among the 66, and the 66 were being used to rule out
exactly that.

This is not a defect in the parser. It is a defect in a count that invites one reading and supports
another, with nothing on it to say which — and the evidence that the trap is real is that a previous
session had already fallen into it and the next nearly inherited the conclusion:

> *"Gate on `php -l` against the target runtime, not on the index's parse-failure count. The index
> remains the right tool for reachability and reference counts; it is the fatal surface it
> structurally understates."*

`parse_failures` (files with `parsed_ok = 0`) ships on `standard`, with `parse_failure_paths` on
`verbose` (058). Both say how many files the adapter could not parse. Neither says that a file it
*could* parse may still be unable to run.

## Scope / Deliverables

- **One sentence where the count is** — the field, the tool description, and §12's row say the count
  is syntax the adapter could not parse, and that compile-stage errors are not detected, so it is a
  floor on brokenness and never a fatal surface.
- **A route, not only a caveat** (R5.4c): the reader is pointed at the runtime's own checker for the
  question they are actually asking. The core runs nothing — it names the class of tool.
- **Say it once.** The sentence lands where the number is served; `docs/` gets a pointer, not a copy
  (R7.6).

## Constraints

- R4/R4.1: the core does not execute a language runtime, now or as part of this.
- R1.1: the wording is language-agnostic — "the language's own compiler/linter", never `php -l` in
  core code or a per-language string.
- 061 / 223: no new field, no new payload weight on `minimal`; this is wording on what already ships.
- The count itself does not change — 058's semantics stay, including `parse_failures` mirroring
  `failed` exactly rather than a subset.

## Acceptance criteria

- The disclaimer is present wherever `parse_failures` is served, pinned by a test so it cannot be
  dropped silently.
- The tool description and CONVENTION §6's row agree with it in the same commit.
- No language name appears in the core wording.
- A fixture file that parses and cannot compile still counts as parsed, and the payload's wording is
  what makes that honest.

## References
`code_atlas/tools/get_index_status.py` (`parse_failures`, `parse_failure_paths`),
field retro round 19 §4 / §6.3 / §8 (fatal-surface dimension, 3/10),
[058](058_list-parse-failures.md).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 280 — parse_failures floor (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 2 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=3 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | count invites fatal reading | note + route | D1 | AC1 | ✅ |
| C1 | Constraints | R4 no runtime exec | wording only | D1 | — | ✅ |
| C2 | Constraints | R1.1 no language name | agnostic note | D1 | AC3 | ✅ |
| C3 | Constraints | 061 no minimal weight | standard+ only | D1 | AC1 | ✅ |
| R1 | Scope | one sentence where count is | parse_failures_note | D1 | AC1 | ✅ |
| R2 | Scope | route to runtime checker | note text | D1 | AC1 | ✅ |
| R3 | Scope | docs pointer once | CONVENTION/TOOLS | D2 | AC2 | ✅ |
| AC1 | AC | disclaimer pinned | proving | D1 | proving | ✅ |
| AC2 | AC | tool desc + CONVENTION | docs | D2 | docs | ✅ |
| AC3 | AC | no language name in core | proving | D1 | proving | ✅ |
| AC4 | AC | zero count still honest | proving | D1 | proving | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R1.1 ✅ · R4 ✅ · R7.6 ✅`
`BASELINE: green`

## Phase 2 — Design

- Approach: `parse_failures_note` constant beside count at standard/verbose; CONVENTION/TOOLS/§19 pointer.
- Rejected: running a language linter from the core.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_parse_failures_floor_not_fatal.py -q`

## Phase 3 — Execute

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — CLEAN (12 met); agent 94caaafb-fda4-4517-bcfa-d513291b4899
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward: push + PR.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
