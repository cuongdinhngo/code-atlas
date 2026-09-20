---
id: 311
slug: semantic-types-means-two-different-things-across-adapters
title: "`semantic_types` is declared by TS and Python for a local type table PHP also has and does not declare, so the honesty flag answers two different questions"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [137, 153, 227, 231]
---

## Why this exists

`capabilities` is the R1.6 honesty channel: an adapter declares what it fills so a payload consumer
can tell *absent* from *never looked*. 231 closed the case where an adapter declared a flag it could
not fill. The inverse is open, and it is on the oldest adapter.

`KNOWN_CAPABILITIES` holds `semantic_types` (`contract.py:221`). TS declares it for the local type
table 153 shipped (`tests/test_ts_semantic_types.py:1` — *"a local type table gives the TS adapter
the `semantic_types` capability"*), and Python for the same mechanism from 227
(`tests/test_python_semantic_types.py:1`). PHP ships that mechanism too and declares five flags
without it (`adapters/php/index.php:28-34`), because in 137 the name meant the *other* thing: 137's
out-of-scope list reads **"PHPStan `semantic_types` — the opt-in half"**, i.e. an external checker's
types, which PHP never shipped.

So `get_index_status.capabilities_by_language` today says PHP — the depth standard, 1-4% HEURISTIC
`CALLS` against TS's 54.1% — has no semantic types, while the two shallower adapters say they do.
Both readings are defensible and that is the defect: one flag, two questions, and the payload does
not say which one it answered.

## Scope / Deliverables

1. Decide what `semantic_types` asserts, and write the decision where the flag is defined
   (`contract.py`) rather than in a task file: either **(a)** *a file-at-a-time local type table
   backs member-call receivers* — then PHP declares it and nothing else moves — or **(b)** *types
   come from a checker outside the file* — then TS and Python stop declaring it and the table-backed
   capability gets its own flag.
2. Apply the decision to all four handshakes and to `tests/contract/` conformance.
3. State the chosen meaning in `ADAPTER_PLAYBOOK.md` §3's `capabilities` row, so adapter #5 reads it
   with the other optional-field decisions instead of re-deriving it from three adapters.

## Constraints

- No core language branch; the flag is data the core routes, never a branch (R1.1).
- A flag change is a handshake change: conformance tests move with it (R3).
- No new capability invented for a mechanism no adapter has.


## Decision (AC1)

**Chosen: (a)** — `semantic_types` asserts *a file-at-a-time local type table backs member-call
receivers*. Written next to `KNOWN_CAPABILITIES` in `contract.py`. PHP declares the flag (it ships
137's table); TS and Python already declare it for the same mechanism; SQL does not (no table).

Rejected **(b)** (external-checker meaning): would force TS/Python to drop a flag their tests and
playbook already treat as the local type table, and invent a second flag for a mechanism every
depth adapter already has — larger blast, same honesty outcome.

PR #404 only filed the question in the playbook depth-parity table; this ticket answers it.

## Acceptance criteria

- AC1: `contract.py` states what `semantic_types` asserts, in one place.
- AC2: every adapter that has the asserted mechanism declares the flag, and no adapter that lacks it
  declares it — asserted per adapter, not by reading one handshake.
- AC3: `ADAPTER_PLAYBOOK.md` §3 carries the meaning.
- AC4: `get_index_status.capabilities_by_language` on a PHP+TS+Python index answers the same question
  for all three.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 311 — semantic_types means two different things (working doc)

- **Ticket:** 311 · **SCOPE:** S · **STRUCTURE:** native · **TRACK:** backend · **TIER:** full
- **BASELINE:** green
- **reviewer:** off · **challenger:** on
- **branch:** feat/311-semantic-types-means-two-different-things

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| H1 | Meaning (a) vs (b)? | Choose (a): local type table. Smaller change; matches TS/Python test titles and 153/227. | ticket Scope §1 options; `tests/test_ts_semantic_types.py:1`; `tests/test_python_semantic_types.py:1` |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

---

## Requirements matrix

`SECTIONS: 4 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria) | 4 decomposed | ROWS: C=3 R=3 G=1 AC=4`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Why | One flag, one question | D1–D3 | ✅ |
| C1 | Constraints | No core language branch | D1 | ✅ |
| C2 | Constraints | Handshake + conformance move together | D2 | ✅ |
| C3 | Constraints | No new capability for unused mechanism | D1 (a) | ✅ |
| R1 | Scope | Decide + write in contract.py | D1 | ✅ |
| R2 | Scope | Apply to all handshakes + conformance | D2 | ✅ |
| R3 | Scope | Playbook §3 capabilities row | D3 | ✅ |
| AC1–AC4 | AC | meaning · per-adapter honesty · playbook · same question | D1–D3 | ✅ |

## AC validation

| AC | Computed | Match? | Falsifiable? |
|----|----------|--------|--------------|
| AC1 | comment above KNOWN_CAPABILITIES names local type table | Y | grep |
| AC2 | PHP+TS+Python declare; SQL does not | Y | handshake tests |
| AC3 | playbook §3 row states meaning | Y | grep ADAPTER_PLAYBOOK |
| AC4 | same question for all three | Y | AC2 |

---

## Phase 1 — Analysis

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ no language branch · R1.6 (change-type) ✅ honesty flag · R3 (change-type) ✅ handshake moves with conformance · R7.2 (change-type) ✅ TOKEN_LEDGER`

### BASELINE

Proving: `pytest tests/test_semantic_types_capability_meaning.py tests/test_php_adapter_server.py::test_the_handshake_announces_capabilities_as_an_object_not_an_empty_array -q` → 6 passed.

`BASELINE: green`

---

## Phase 2 — Design

**Approach.** Option (a): document meaning in `contract.py`; PHP adds `semantic_types: true`; playbook §3 row; proving tests.

**Rejected:** (b) drop TS/Python flags + new flag name — larger, contradicts existing capability docs.

### Smallest change-list

| # | Change | Files | Ph2 |
|---|--------|-------|-----|
| D1 | Document meaning + PHP declare | `contract.py`, `adapters/php/index.php` | AC1,AC2 |
| D2 | Handshake/conformance pins | `tests/test_php_adapter_server.py`, `tests/test_semantic_types_capability_meaning.py` | AC2,AC4 |
| D3 | Playbook §3 row | `docs/ADAPTER_PLAYBOOK.md` | AC3 |
| D4 | Bookkeeping | ticket, BACKLOG, TOKEN_LEDGER | R7.2 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**PROVING TEST:** `.venv/bin/python -m pytest tests/test_semantic_types_capability_meaning.py tests/test_php_adapter_server.py::test_the_handshake_announces_capabilities_as_an_object_not_an_empty_array -q`

**SCOPE:** S

---

## Phase 3 — Execute

Diff ⊆ D1–D4. Verification: proving suite 6 passed.

---

## Phase 4 — Review

`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — VERDICT CLEAN (agent e467154c). Gate 4: challenger CLEAN; reviewer waived.

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (decision + challenger)`

## Phase 5 — Finalise

Outward: push + open PR only.
