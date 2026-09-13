---
id: 267
slug: the-warning-an-autonomous-agent-cannot-act-on
title: 'The question an agent most wants to ask — "what did I just break" — is the one the index refuses, and the remedy it prints for a stale server process is a human typing `/mcp`: an autonomous run sees both, can act on neither, and learns to ignore the honesty layer'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [257, 096, 035]
---

## Why this exists

Two operational cliffs, both recorded in field round 18:

1. **The whole session ran with `server_stale_process: true`.** The documented remedy is a `/mcp` reconnect — an interactive human action. An autonomous run can read the warning and cannot act on it; after the first call it is noise. A warning with no available action is a defect in the honesty layer, the same class as a zero with no `reason`.
2. **A commit touching indexed files flips `index_stale` and symbol queries refuse.** That refusal is correct, and it lands exactly when the agent wants to ask *"did I just break a caller?"* — the moment [096](096_edit-then-ask-tax-two-files-cost-a-minute.md) named as the cliff.

[257](257_the-index-goes-blind-at-the-moment-it-is-most-wanted.md) shipped the honest half: `label_serve_behind` (`tools/freshness.py:173`) serves an answer from the last built revision and stamps rows with `index_revision`. But it is opt-in **and restricted to subjects that did not change** — and the subject an agent asks about after an edit is precisely the one that did.

A silent stale answer is forbidden. A **loud** stale answer is a product.

## Scope / Deliverables

- **Extend labelled serve-behind to the changed subject.** Opt-in stays; the default stays refuse-when-stale. When served, the row carries `index_commit` / `index_revision` and the reason names the subject as changed since that revision — the agent is told exactly what it is holding.
- **Make `server_stale_process` actionable.** Either the server re-execs itself once, or the payload states which capabilities actually differ between the running process and its disk. A warning must name an action its reader can take.
- **The distinction stays visible**: unchanged-subject-behind (257's arm) and changed-subject-behind (this ticket) are different reasons, not one blurred label.

## Constraints

- **Never a silent stale answer.** If the labelling cannot be attached, the tool refuses — that is the existing default and it does not move.
- Read-through repair (035) stays first; this ticket only governs what happens after a non-stale freshness result declines.
- R4.2 unaffected: served rows are rows of the last built revision, byte-identical to what that revision produced.

## Acceptance criteria

- With the opt-in on, a query about a symbol in a file dirty since the last build returns rows stamped with the built revision and a reason naming the subject as changed; with it off, the refusal is unchanged.
- A test pins that no code path can emit a behind-index row without a revision stamp.
- `server_stale_process: true` payloads name either a performed re-exec or the differing capabilities; a test pins that the field never appears with an action the reader cannot take.
- 257's unchanged-subject arm keeps its own reason and its existing tests.

## References
[257](257_the-index-goes-blind-at-the-moment-it-is-most-wanted.md), `code_atlas/tools/freshness.py:173`, [096](096_edit-then-ask-tax-two-files-cost-a-minute.md), `code_atlas/build_info.py:160`, field retro round 18 (ask #4).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 267 — actionable stale warnings (working doc)

- **Ticket:** 267
- **Type:** enhancement
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 touched files under UI paths
- **TIER:** full
- **BASELINE:** green

---

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**HOW resolved:** name capabilities vs re-exec → payload names `restart_mcp_server_process` + `server_stale_differs` (safer than self re-exec; PLAN §19 / ticket alt).
**refine skipped:** ticket locks opt-in serve-behind extension, distinct reason, actionable stale-process.
**INPUT KIND:** ticket.

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=3 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | warning with no action is defect | name restart action | D3 | AC3 | ✅ |
| C1 | Constraints | never silent stale | refuse if cannot label | D2 | AC1 off | ✅ |
| C2 | Constraints | 035 repair first | only after unrepaired stale | D2 | AC1 | ✅ |
| C3 | Constraints | R4.2 | last-built rows | D2 | — | ✅ |
| R1 | Scope | label changed subject | index_behind_subject_changed | D2 | AC1 | ✅ |
| R2 | Scope | actionable stale_process | action + differs | D3 | AC3 | ✅ |
| R3 | Scope | distinct from 257 | two reasons | D2 | AC4 | ✅ |
| AC1 | AC | opt-in rows + reason; off refuses | proving | D2 | proving | ✅ |
| AC2 | AC | no behind row without revision | unit | D2 | AC2 | ✅ |
| AC3 | AC | stale_process names action | proving | D3 | AC3 | ✅ |
| AC4 | AC | 257 arm keeps tests | 257 suite | D2 | 257 | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

---

## Phase 1 — Analysis

- Root cause: 257 refused dirty subjects; stale_process warned without an agent-actable remedy.
- TRACK: backend — 0/0 UI · SCOPE: M · TIER: full

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R4.2 ✅ · R5.6 ✅ · R7.6 ✅`

### BASELINE

```
Ran at 139938c171a0f18271cd9ae486f7498316459101
$ .venv/bin/python -m pytest tests/test_serve_behind_labelled_reads.py -q --tb=no
5 passed
```

`BASELINE: green`

---

## Phase 2 — Design

- Approach: §19 first; continue past unrepaired dirty-subject stale under serve_behind; label with new reason; stamp revision; provenance adds restart action + differs.
- Rejected: process re-exec (host-owned MCP lifecycle); blur into single index_behind reason.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_actionable_stale_warnings.py::test_serve_behind_labels_changed_subject -q`

| # | Change | File |
|---|--------|------|
| D1 | section-19 | PLAN.md |
| D2 | label + continue stale | freshness.py, find_callers.py, find_references.py, nav_result.py |
| D3 | actionable provenance | build_info.py |
| D4 | proving + 257 keep | tests |

---

## Phase 3 — Execute

**Branch:** feat/267-actionable-stale-warnings
**Implemented:** D1–D4.

**Verification sweep**

```
Ran at 53a4c9aa6feee4b385d6c6b49aa8599f8775a6a8
$ .venv/bin/python -m pytest tests/test_actionable_stale_warnings.py tests/test_serve_behind_labelled_reads.py -q --tb=no
8 passed
```

---

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived.
**CHALLENGER: ON** — round-1 NOT CLEAN (silent ok when stamp fails); round-2 CLEAN after refuse-when-cannot-label.

---

## Phase 5 — Finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`

Outward: push + PR authorised. Deferred: merge. DISCLOSURE: gate.sh / local CI / remote CI skipped per operator waiver.
