---
id: 264
slug: the-honesty-predicate-is-still-one-language-s-shape-wearing-a-constant-s-name
title: 'After 255, one subject kind counts its inbound relations correctly and the rule that made it wrong is unchanged: each tool still decides for itself what a genuine zero is, so the next Table-shaped kind, the next `WRITES` cousin, the next C# construct re-pays the same bug — make the predicate derive from the contract and let a tool that bypasses it fail a test'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [255, 232, 065]
---

## Why this exists

[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md) shipped: a T-SQL `Table` with 34 inbound `WRITES` no longer answers `no_matches`. What it fixed was one predicate, in one tool, against one subject kind. **The class survives.** `UNMODELLED_REFERENCE_KINDS` was a tuple of the two kinds a PHP class happens to have, consulted as though it were the set of all inbound relations — 255's own words: *a language branch wearing a constant's name*, in a core where R1.1 forbids language branches.

The next adapter that introduces a kind this predicate cannot see re-creates the defect silently. C#/.NET ([021](021_csharp-adapter.md)) is the obvious candidate and it has not been written yet — which makes this the cheapest moment to make the repeat impossible.

An empty inbound answer is genuine **only** after the tool has counted every inbound kind the contract holds for that subject's kind. If any exist and are unlinked, the reason is *unmeasured*, never `no_matches`.

## Scope / Deliverables

- **A `subject kind → inbound kinds` mapping in `contract.py`**, derived from the vocabulary the contract already owns — not a second hand-kept table (R6.7).
- **One shared empty-answer predicate** that every nav tool calls. No tool decides `no_matches` on its own.
- **A conformance test that fails a bypass**: a nav tool reaching the `no_matches` reason without consulting the shared predicate is a red test, not a quiet disagreement. Property-shaped over `(subject kind × inbound kind)` so a new kind is covered the day it enters the contract.
- **Design constraint, binding: derive, do not extend.** The mapping must be a derived view of existing vocabulary so **`contract_version` does not bump**. A bump forces consumers into a 9–20-minute full rebuild and the observed consequence is that they stay on the old server — which costs more honesty than this ticket buys.

## Constraints

- If the design cannot avoid a vocabulary change, **stop**: the atomic-swap upgrade path ships first, in its own ticket, and this one waits. A single PR that changes both the honesty layer and the upgrade path is not reviewable.
- R1.1: no language branch, and no constant that is one language's shape in disguise — the test must be able to catch the disguised form, which is what 255 could not.
- Whether a tool *returns* the newly-counted kinds stays out of scope; this ticket binds only that a bare `no_matches` over existing unlinked inbound edges becomes impossible.

## Acceptance criteria

- A matrix test over every `(subject kind × inbound kind)` the contract holds; adding a kind without extending the mapping fails it.
- Every nav tool's `no_matches` path routes through the one predicate; a test asserts there is no second implementation.
- `contract_version` unchanged, pinned by a test.
- The 255 fixture and the PHP-class fixture both still pass unchanged.

## References
[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md), [232](232_the-same-construct-is-a-references-edge-in-python-and-node-extra-in-php-and-ts.md), [065](065_empty-answer-cannot-explain-itself.md), `code_atlas/contract.py:106`, `docs/ENGINEERING_RULES.md` R1.1 / R3 / R6.7.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 264 — honesty predicate derived mapping (working doc)

- **Ticket:** 264
- **Type:** bug
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 touched files under UI paths
- **TIER:** full
- **BASELINE:** green

---

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**refine skipped:** 0 unresolved product-decisions — ticket already locks derive-not-extend, shared predicate, bypass test, no version bump.
**INPUT KIND:** ticket (not epic).

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `empty-answer-must-explain-itself` | 2 | handle | Yes |
| 2 | `evidence-shaped-honesty-inverts-on-a-second-instance` | 2 | handle | Yes |

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=3 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why | class survives after 255 | tools still decide zeros alone | find_references / callers / impl / include | D1–D3 | proving | ✅ |
| C1 | Constraints | stop if vocabulary change | derive; no bump | contract.py | D1 | version pin | ✅ |
| C2 | Constraints | R1.1 no language-shaped constant | mapping from NODE×EDGE | contract | D1 | matrix | ✅ |
| C3 | Constraints | return kinds out of scope | honesty only | ticket | D2 | 255 fixtures | ✅ |
| R1 | Scope | subject→inbound mapping derived | INBOUND_KINDS_BY_SUBJECT | contract | D1 | matrix | ✅ |
| R2 | Scope | one shared empty-answer predicate | nav_result helpers | nav_result | D2 | bypass AST | ✅ |
| R3 | Scope | conformance fails a bypass | AST over nav tools | tests | D3 | bypass test | ✅ |
| AC1 | AC | matrix every subject×inbound | parametrize | | D3 | proving | ✅ |
| AC2 | AC | every nav no_matches via predicate | four tools wired | | D2 | bypass | ✅ |
| AC3 | AC | contract_version unchanged | pin == 10 | | D1 | pin test | ✅ |
| AC4 | AC | 255 + PHP fixtures still pass | regression | | D3 | proving | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

---

## Phase 1 — Analysis

- Root cause (bug, `logic`): after 255, `UNLINKED_EVIDENCE_KINDS` is still consulted only inside `find_references`; other nav tools (and any new subject kind) re-decide zeros independently — the class of language-shaped constants survives as per-tool predicates.
- Handler / blast radius: `contract.py`, `nav_result.py`, inbound nav tools, 065 find_implementations assertion.
- `TRACK: backend — 0/0 touched files under UI paths`
- `SCOPE: S`
- `TIER: full`

`RULE SECTIONS: 5 applicable — 4 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ derived mapping not PHP pair · R3 (change-type) ✅ no vocabulary bump · R5.6 (recalled handle) ✅ honesty ≠ hits · R6.7 (change-type) ✅ derive NODE×EDGE · R7.5 (change-type) ✅ comments ≤3`

### BASELINE

```
Ran at de3b65bc56af90b1700f0d93e42b4665ed05c904
$ .venv/bin/python -m pytest tests/test_find_references_honesty_not_php_shaped.py tests/test_empty_answer_cannot_explain_itself.py -q --tb=no
318 passed in 28.29s
```

`BASELINE: green` for the change-adjacent suite.

---

## Phase 2 — Design

- **Approach.** Add `INBOUND_KINDS_BY_SUBJECT` / `inbound_kinds_for` as a derived view of `NODE_KINDS` × `UNLINKED_EVIDENCE_KINDS` (no bump). Put `unmeasured_inbound_for_subject` + `apply_empty_inbound_honesty` in `nav_result.py`. Wire find_references / find_callers / find_implementations / include_graph. AST bypass test + matrix + version pin. Update 065 IMPL-empty assertion to 264.

- **Rejected alternatives.**
  1. Hand-kept per-subject inbound table — rejected: R6.7 / vocabulary bump risk.
  2. Keep honesty only in find_references — rejected: ticket AC2 every nav tool.
  3. Bump contract_version to encode targets — rejected: Constraint stop; atomic-swap first.

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| Handle | Answer | Command + result (trimmed) |
|--------|--------|----------------------------|
| empty-answer-must-explain-itself | traced | shared predicate upgrades no_matches |
| evidence-shaped-honesty-inverts-on-a-second-instance | traced | mapping keys == NODE_KINDS |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_honesty_predicate_derived_mapping.py::test_matrix_subject_times_inbound_kind_not_bare_no_matches -q`

**Smallest change-list**

| # | Change | File/area |
|---|--------|-----------|
| D1 | INBOUND_KINDS_BY_SUBJECT + inbound_kinds_for | contract.py |
| D2 | shared predicate + wire four nav tools | nav_result + find_* + include_graph |
| D3 | proving matrix/bypass/version + 065 update + tier2 JOINED | tests |

---

## Phase 3 — Execute

**Branch:** `feat/264-the-honesty-predicate-is-still-one-language-s-shape-wearing-a-constant-s-name`

**Implemented:** D1–D3 as approved.

**Verification sweep**

```
Ran at 38bab8176c23079a85dcbde8bc146ee1087ef746
$ .venv/bin/python -m pytest tests/test_honesty_predicate_derived_mapping.py tests/test_find_references_honesty_not_php_shaped.py tests/test_sql_tier2_vocabulary_is_opt_in.py tests/test_empty_answer_cannot_explain_itself.py tests/test_relation_unmodelled_for_language.py tests/contract/test_tool_parity.py -q --tb=line
696 passed in 44.39s
```

diff ⊆ approved list: contract, nav_result, find_references, find_callers, find_implementations, include_graph, proving + 065 + tier2 tests, task/BACKLOG/TOKEN_LEDGER.

---

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived; no rule-book-grounded review ran.
**CHALLENGER: ON** — ticket-blind, 2 dispatches (round-1 NOT CLEAN on shared-predicate call sites + weak bypass AST; round-2 CLEAN after all four inbound tools call `apply_empty_inbound_honesty` and bypass requires that name).

```
Ran at 542cade8534800831041fedf1b52a220c5018f4d
$ .venv/bin/python -m pytest tests/test_honesty_predicate_derived_mapping.py tests/test_empty_answer_cannot_explain_itself.py -q --tb=no
168 passed
```

---

## Phase 5 — Finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x2)`

Outward actions authorised at handover: push feature branch; open PR. Deferred: merge, tracker writes, force-push.
