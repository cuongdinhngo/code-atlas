---
id: 261
slug: the-readme-lists-four-adapters-as-peers-and-the-number-that-contradicts-it-is-in-verbose
title: 'The README lists PHP · TypeScript · T-SQL · Python as peers while HEURISTIC `CALLS` runs 1–4 % on PHP and 82 % on Python, and the per-language edge health that would say so is computed, stamped, and then shown only at `verbose` — a confident surface concealing a known gap, which is the one thing the honesty contract forbids'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [227, 153, 233]
---

## Why this exists

Measured, on pinned samples:

| Adapter | HEURISTIC `CALLS` |
|---|---|
| PHP (after its type table) | **1–4 %** |
| TypeScript (`ky`, after 153/154/155) | **54.1 %** |
| Python (Flask, after 227's type table) | **82.2 %** |

Those are not three adapters at different depths. They are one product and two sketches. A reader of the README cannot tell which one they are getting, and an agent that closes a blast-radius claim on a Python `find_callers` page is closing it over an 82 %-heuristic edge set.

The fact that would correct this **already exists and is already cheap**: `store.stamped_edge_health_by_language()` is a single meta read, never a query-time scan. `get_index_status.py:330` attaches it to the `verbose` payload only. The whole-graph `edge_health` is at `standard`; the per-language split — the one that distinguishes PHP from Python — is one level down.

## Scope / Deliverables

- **Per-language edge health at `standard`.** `unlinked` / `by_tier` per language beside the existing whole-graph `edge_health`. The full census with `pairs` stays in `verbose` — this ticket moves the verdict, not the detail.
- **README says what each adapter is.** Not a removal and not an apology: each shipped language carries its measured HEURISTIC `CALLS` figure on its pinned sample, with the sample named and dated. PHP is the depth standard; TS and Python are stated as shallower, with the number.
- **The same figure in one place only** (R6.7) — the README quotes the report `scripts/edge_health_report.py` produces; no hand-kept second copy.

## Constraints

- **This is a surface-honesty fix, not a depth ticket.** It must not queue, imply, or pre-commit any work on Python or TypeScript depth — that stays behind the playbook's field-round gate and is explicitly out of scope here.
- No payload restructuring: `standard` gains a field, nothing moves out of it.
- R4.2: one meta read, no scan.

## Acceptance criteria

- `get_index_status` at `standard` carries per-language `unlinked` / `by_tier`; a test pins that `pairs` is still `verbose`-only and that no query-time scan was added.
- README states, per shipped adapter, the measured HEURISTIC `CALLS` share, the sample it was measured on, and the date — sourced from the report script, not retyped.
- A test (or the existing doc guard) fails if the README figure and the report disagree.
- No ticket, backlog row, or doc line created by this change proposes deepening Python or TS.

## References
`code_atlas/tools/get_index_status.py:330`, `scripts/edge_health_report.py`, [227](227_python-has-no-local-type-table-so-every-member-call-is-heuristic.md), [153](153_ts-declared-and-inferred-types.md), `docs/benchmarks/233_python-edge-health.md`, `docs/ADAPTER_PLAYBOOK.md` §5.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 261 — README peer adapters vs per-language edge health at standard (working doc)

- **Ticket:** 261
- **Type:** bug
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 touched files under UI paths
- **TIER:** full
- **BASELINE:** green

---

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**refine skipped:** 0 unresolved product-decisions — ticket already locks standard verdict, README report-sourced figures, no depth work.
**INPUT KIND:** ticket (not epic).

HOW self-resolved at design (not refine want): field reuses `edge_health_by_language` stripped at standard (243 pattern); SQL stated as not CALLS-HEURISTIC metric (233_sql).

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=3 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why | confident surface conceals known gap | peers without HEURISTIC shares | README L7 | D2 | readme test | ✅ |
| C1 | Constraints | surface honesty not depth | no deepen PHP/TS/Python work | ticket | D2 | readme assert | ✅ |
| C2 | Constraints | no payload restructure | standard gains field | get_index_status | D1 | proving | ✅ |
| C3 | Constraints | R4.2 one meta read | no live scan | stamped_* | D1 | monkeypatch | ✅ |
| R1 | Scope | per-lang unlinked/by_tier at standard | verdict attach | get_index_status | D1 | proving | ✅ |
| R2 | Scope | README measured figures + sample + date | report-sourced | README | D2 | readme test | ✅ |
| R3 | Scope | one place only R6.7 | quote report outputs | README+bench | D2 | doc guard | ✅ |
| AC1 | AC | standard unlinked/by_tier; pairs verbose; no scan | | | D1 | proving | ✅ |
| AC2 | AC | README per adapter figure/sample/date | | | D2 | readme test | ✅ |
| AC3 | AC | test fails if README ≠ report | | | D2 | doc guard | ✅ |
| AC4 | AC | no deepen ticket/doc from this change | | | D2 | readme assert | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

---

## Phase 1 — Analysis

- Root cause (bug, `logic`): `stamped_edge_health_by_language` already exists; only `_attach_edge_health_by_language` at verbose used it; README listed four languages as peers without the HEURISTIC CALLS shares the report already measured.
- Handler / blast radius: `get_index_status.py`, README, TOOLS/PLAN one-liners, 183's "verbose only" test.
- `TRACK: backend — 0/0 touched files under UI paths`
- `SCOPE: S`
- `TIER: full`

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — R4.2 (change-type) ✅ meta read · R5.6 (change-type) ✅ silence when absent · R6.7 (change-type) ✅ report quote · R7.5 (change-type) ✅ comments ≤3 · R7.6 (change-type) ✅ prune TOOLS/PLAN`

### BASELINE

```
Ran at a5fb9a568e5e1e22dede328df47bdc39e34f7713
$ .venv/bin/python -m pytest tests/test_edge_health_per_language.py tests/test_cross_language_at_standard.py -q --tb=no
17 passed in 5.25s
```

`BASELINE: green` for the change-adjacent suite.

---

## Phase 2 — Design

- **Approach.** Add `_attach_edge_health_by_language_verdict` before the standard return: same silence rules as 183, payload keys `unlinked`/`by_tier` per language only. Verbose still replaces with the full stamp (`pairs` nested). README table quotes report outputs (137 / 153 / 227 / 233_sql). Proving test + update 183's "verbose only" AC. No depth work.

- **Rejected alternatives.**
  1. New field name beside `edge_health_by_language` — rejected: 243 already reuses one field at two detail levels.
  2. Hand-typed README numbers without report cite — rejected: R6.7 / AC3.
  3. Re-run samples in CI for the guard — rejected: committed report outputs are the quote source; live samples need network/docker.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_edge_health_verdict_at_standard.py::test_standard_carries_per_language_verdict_without_pairs -q`

**Smallest change-list**

| # | Change | File/area |
|---|--------|-----------|
| D1 | verdict attach at standard; verbose still full | get_index_status.py |
| D2 | README peers table + TOOLS/PLAN prune | README · TOOLS · PLAN |
| D3 | proving + 183 AC update + doc guard | tests |

---

## Phase 3 — Execute

**Branch:** `fix/261-readme-lists-four-adapters-as-peers`

**Implemented:** D1–D3 as approved.

**Verification sweep**

```
Ran at 1cfad5510381a9f09e7c549bfd8b34ce7d254053
$ .venv/bin/python -m pytest tests/test_edge_health_verdict_at_standard.py tests/test_edge_health_per_language.py tests/test_cross_language_at_standard.py -q --tb=no
21 passed
```

diff ⊆ approved list: get_index_status, README, TOOLS, PLAN, proving + 183 test update, task/BACKLOG/TOKEN_LEDGER.

---

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived; no rule-book-grounded review ran.
**CHALLENGER: ON** — ticket-blind, 2 dispatches (round-1 NOT CLEAN: TS/Python Measured column lacked calendar dates; round-2 after dating 2026-08-27 / 2026-09-08).

```
Ran at 1cfad5510381a9f09e7c549bfd8b34ce7d254053
$ .venv/bin/python -m pytest tests/test_edge_health_verdict_at_standard.py -q --tb=no
4 passed
```

---

## Phase 5 — Finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`

Outward actions authorised at handover: push feature branch; open PR. Deferred: merge, tracker writes, force-push.
