---
id: 337
slug: the-elision-hint-names-the-default-not-the-cap-that-fired
title: "read_symbol with max_lines says 'body elided above 600 lines' for a 62-line method — the hint names the default threshold, not the cap that elided the body"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [288]
---

## Why this exists (field retro, 2026-09-25)

`read_symbol` with `max_lines=40` on a 62-line method returned the signature and the hint
*"body elided above 600 lines"*. The reader is told a threshold that did not fire.

`_body_elided_hint` (`read_symbol.py:59-64`) always prints `BODY_LINE_THRESHOLD`. The cap that
decided is `_effective_body_cap` (`read_symbol.py:315-321`), which returns `max_lines` when given.
Probed on `main` (`927aeb9`): `max_lines=3` on a 7-line method → the same 600-line hint.

## Goal

The hint names the cap that elided the body.

## Scope / Deliverables

1. `_body_elided_hint` takes the effective cap and says which one it was (`max_lines=40` or the
   default).

## Constraints

- **061 / R6.7** — the default-cap payload is byte-identical; the threshold stays one site.

## Acceptance criteria

- **AC1** `max_lines=3` on a 7-line body → the hint names 3 and `max_lines`; red on today's code.
- **AC2** A 700-line body with no `max_lines` → today's hint, byte-identical.

## References
`code_atlas/tools/read_symbol.py:59-64,315-321,362-384`; ticket 288.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 337 — the elision hint names the cap that fired (working doc)

- **Ticket:** 337 · local · **SCOPE:** S · **TIER:** full · **TRACK:** backend
- **REVIEWER:** OFF (`--no-reviewer`) · **CHALLENGER:** ON
- **Current phase:** finalise
- **Session status:** done — autorun, PR open
- **Reviewed at:** `d5b1af9` (challenger round 1, CLEAN) · reviewed: code_atlas/tools/read_symbol.py · tests/test_elision_hint_names_the_cap.py · docs/TOOLS.md

## Phase 0 — Refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW1: the caller cap is named as `max_lines=<n>` in the same sentence slot the default fills —
`body elided above max_lines=3 lines (declaration …)` — so the default hint stays byte-identical and
the named cap is the one `_effective_body_cap` returned. A `max_lines` equal to 600 still says
`max_lines=600`: the caller's cap fired, not the default. Citation: Scope 1; C1 (061 / R6.7).

## Requirements matrix

`SECTIONS: 7 found (Why · Goal · Scope · Constraints · Acceptance · References · title) | 7 decomposed | ROWS: C=1 R=1 G=1 AC=2`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Goal | the hint names the cap that elided the body | D1 | ✅ |
| R1 | Scope 1 | `_body_elided_hint` takes the effective cap and says which (`max_lines=N` or the default) | D1 | ✅ |
| C1 | 061 / R6.7 | default-cap hint byte-identical; the threshold stays `BODY_LINE_THRESHOLD`, one site | D1 · D2 | ✅ |
| AC1–AC2 | AC | proving | D2 | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: `_body_elided_hint` interpolated `BODY_LINE_THRESHOLD` unconditionally while
  `_effective_body_cap` returns `max_lines` when the caller passes one.
- Blast radius: one call site (`_found_body_payload`); the separator-normalised path reaches it
  through the same builder. `tests/test_read_symbol_body_elision.py` asserts only that the default
  hint contains 600 — unchanged.

`TRACK: backend — 0/N UI`

`RULE SECTIONS: 2 applicable — 2 by change-type | 0 by recalled handle — R6.7 ✅ (threshold read from BODY_LINE_THRESHOLD only) · R7.5 ✅ (comment ≤ 3 lines)`

`BASELINE: green`

Baseline: bare `pytest` on `833564c` (Linux, php · composer · node on PATH) → `4589 passed, 4 skipped`.

## Phase 2 — Design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | k/N |
|---|--------|------|-----|
| D1 | `_body_elided_hint(..., max_lines=)` names `max_lines=<n>` when given, else the threshold | code_atlas/tools/read_symbol.py | 1/1 |
| D2 | proving | tests/test_elision_hint_names_the_cap.py | 1/1 |
| D3 | TOOLS line · bookkeeping | docs | 1/1 |

| AC | risk | proof | provenance | match |
|----|------|-------|------------|-------|
| AC1 | tool payload | pytest through `read_symbol.create` over a planted store | authored | ✅ |
| AC2 | tool payload, byte equality | pytest, full-string equality | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_elision_hint_names_the_cap.py -q`

Rejected alternatives: passing the resolved cap integer alone (loses *which* cap fired when
`max_lines` equals the default); a second hint constant (two sites for one sentence — R6.7).

`SCOPE: S`

## Phase 3 — Execute

**Branch:** fix/337-elision-hint-names-the-cap

Ran at cf4463ac986669379c1618d57e8c3b9d70a53107

```
$ .venv/bin/python -m pytest tests/test_elision_hint_names_the_cap.py -q
2 passed
```

Full verification at `cf4463a` (the reviewed source `9a4ced1` plus docs only): `scripts/gate.sh` →
`GATE GREEN — all 20 checks passed`; `scripts/docker-test.sh` → `4590 passed, 5 skipped` (Linux
host, Docker). Later commits touch this working doc only.

Red arm on `main` (`833564c`): AC1 fails (hint names 600), AC2 passes. `ruff` + `mypy` clean;
`tests/test_read_symbol_body_elision.py` 6 passed unchanged.

Design conformance: D1–D3 implemented-as-approved.

## Phase 4 — Review

REVIEWER: OFF (`--no-reviewer`) · CHALLENGER: ON — round 1: **CLEAN 6/0/0**. Verdict:
`clean (challenger only — REVIEWER: OFF)`. Probed beyond the ACs: `max_lines=600` names
`max_lines=600`; `full_body` with `max_lines` never reaches the hint; `max_lines` equal to the span
does not elide; the en dash in the declaration range is unchanged.

## Phase 5 — Finalise (learning loop)

Lesson: `docs/LESSONS.md` § 337 — a sighting of `source-the-caveat-from-the-computation` (R5.5);
class index bumped to 7.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: 56826 · top cost driver: review/challenger ×1 (1 dispatch; main-loop unmeasured)`
