---
id: 261
slug: the-readme-lists-four-adapters-as-peers-and-the-number-that-contradicts-it-is-in-verbose
title: 'The README lists PHP · TypeScript · T-SQL · Python as peers while HEURISTIC `CALLS` runs 1–4 % on PHP and 82 % on Python, and the per-language edge health that would say so is computed, stamped, and then shown only at `verbose` — a confident surface concealing a known gap, which is the one thing the honesty contract forbids'
phase: 1.5b
milestone: Agent-trust
status: todo
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
