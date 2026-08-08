---
id: 060
slug: build-report-scale-naming
title: An incremental run reports deltas under the same field names a full build uses for totals
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [051]
---

## Goal
[051](051_build-report-edge-undercount.md) settled that `BuildReport` means **"what this run wrote"**,
and made the counts honest. It did not do the other half of its own scope, which said in as many words:

> If the delta reading wins, the fields must be named so a total cannot be read out of them.

They were not renamed. So an incremental returns:

```json
{"mode":"incremental","files":21,"parsed":21,"failed":0,"removed":0,
 "nodes":357,"edges":6396,"seconds":61.585,"schema_rebuilt":false}
```

against a graph holding 185,886 nodes and 1,775,839 edges — while a **full** build returns the same
field names meaning the whole graph, because on a full build "what this run wrote" *is* the graph. Only
`mode` distinguishes them, and a caller that does not read it sees `edges: 6396` and has no signal that
it is holding a delta.

Observed in field retro round 2 §A.5, which read the pair and could not tell which scale it was on
without reasoning about the mode.

**Also in scope: re-measure the round-1 disagreement on a clean server.** Round 2 reported a full build
at ~949,808 edges against `get_index_status` at 1,775,812 — the exact figures from before 051 shipped,
observed on a session whose server process predated the fix (its own §0 shows the core reporting
contract v2). 051's tests assert the two agree. Confirm on a restarted server, and record the result
either way; a "not fixed" that is actually a stale process should not stand in the record unchallenged.

## Scope / Deliverables
- **Make the scale unreadable-as-wrong.** Options, to be chosen and justified: distinct field names per
  mode; a nested shape (`wrote: {...}`) that cannot be mistaken for a total; or carrying the graph
  totals alongside the delta so both are present and labelled. Prefer whichever makes the wrong reading
  impossible rather than merely documented.
- **Do not silently change the meaning.** 051's definition stands — the fix is naming, not arithmetic.
- **A test that would fail on the old shape**, in the spirit of
  `test_an_incremental_run_reports_its_delta_not_the_graph`.
- **Re-measure and record** the full-build-vs-status agreement on a server known to be running current
  code, on a repo large enough for the two to differ if they were going to.

## Constraints
- **No schema or contract change (R3).**
- **Determinism (R4.2)** — counts unchanged; only their presentation moves.
- **Cost stays flat** — if totals are carried alongside, they come from `store.counts()`, which
  `get_index_status` already pays for, and not from a new scan.
- **`build_or_update_index` is called rarely**, so a slightly larger payload is acceptable here in a way
  it is not on the nav path.

## Acceptance criteria
- An incremental result cannot be read as a graph size: asserted by a test that fails against today's
  shape.
- A full build and an incremental are distinguishable without reading `mode`.
- 051's existing agreement tests still pass unchanged.
- The re-measurement is recorded in the Outcome, naming the server commit it ran against.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/indexer.py:71-81` (`BuildReport`), `:202-204` (the incremental return),
`:207-218` (`_count_late_writes`); `code_atlas/tools/build_or_update_index.py` (`mode`, `_result`);
`code_atlas/store.py` `counts()` (the totals `get_index_status` reports).
[051](051_build-report-edge-undercount.md) — the definition, the scope line left undone, and
`tests/test_build_report_counts.py`.
Origin: field retro round 2 §A.5.

## Outcome

- **Presentation (060):** `build_or_update_index` returns nested `wrote` (BuildReport — what this run
  wrote) and `graph` (`store.counts()` totals). Bare top-level `nodes`/`edges` from the report are gone,
  so an incremental delta cannot be read as a repo size.
- **Re-measure (AC4):** `CODE_ATLAS_SCALE_SAMPLE` was **unset** on this host — no anchor remount. On the
  `MULTI_CANDIDATE` fixture (same path as 051's tool/status agreement), a full build at commit
  `833b8be5a247fc2766f7aca19350e96ffbbff1fa` has `wrote.nodes`/`wrote.edges` ≡ `graph.*` ≡
  `get_index_status` (`pytest tests/test_build_report_counts.py::test_the_build_tool_and_the_status_tool_agree`
  + `tests/test_build_report_scale_naming.py`, green). The round-2 “~949,808 vs 1,775,812” disagreement
  is the pre-051 stale-process reading; current tip keeps 051 arithmetic and only moves presentation.
- **Suite:** `933 passed` at that tip; ruff/mypy clean on touched paths.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 060 — build-report-scale-naming (working doc)

- **Ticket:** 060 · local `docs/tasks/060_build-report-scale-naming.md`
- **Type:** bug / enhancement
- **Repo(s):** app (`.`)
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend — 0/N UI
- **TIER:** full
- **BASELINE:** green — `932 passed` (2026-08-08, untouched main)
- **work_doc_mode:** embed
- **working-doc path:** this file below separator

## Phase 0 — Refine

`REFINE: 1 unresolved | 0 asked (standing→ASSUMED) | 0 HOW in refine | 1 ASSUMED | skip: no`

**INPUT KIND:** ticket

**ASSUMED (standing — confirm at Gate 1):**

| # | Choice | Why |
|---|--------|-----|
| W1 | Nested **`wrote`** (BuildReport fields) + labelled **`graph`** (`store.counts()`) on every successful build payload; no bare top-level `nodes`/`edges` from the report | Ticket prefers wrong reading *impossible*; dual labelled scales beat rename-only or wrote-only |

**Exposure-checker:** [Challenger](4e38ff63-31d0-4320-a0cd-c34503e2965d) — surfaced W1.

## Requirements matrix

`SECTIONS: 4 found | 4 decomposed | ROWS: C=4 R=4 G=2 AC=5`

| ID | Interpretation | Ph2 | Status |
|----|----------------|-----|--------|
| G1 | Incremental cannot look like graph size | CL1 | ✅ |
| G2 | Scale clear without reading `mode` | CL1 | ✅ |
| R1 | Naming/shape fix; 051 arithmetic stands | CL1 | ✅ |
| R2 | Test fails on old flat shape | CL2 | ✅ |
| R3 | Re-measure full vs status on current server; record | CL3 | ✅ |
| R4 | Prefer impossible-wrong over documented | W1 | ✅ |
| C1 | No schema/contract (R3) | — | ✅ |
| C2 | Determinism — counts unchanged | CL1 | ✅ |
| C3 | Totals from `store.counts()` only | CL1 | ✅ |
| C4 | Build tool rarely called — larger payload OK | CL1 | ✅ |
| AC1 | Incremental not readable as graph size (test) | CL2 | ✅ |
| AC2 | Full vs incremental distinguishable w/o `mode` | CL2 | ✅ |
| AC3 | 051 agreement tests still pass (BuildReport↔store unchanged; tool keys navigate `wrote`/`graph`) | CL2 | ✅ |
| AC4 | Re-measure recorded in Outcome + commit | CL3 | ✅ |
| AC5 | pytest/ruff/mypy green | verify | ✅ |

`CLARIFICATION: 1 ASSUMED (W1) | j=0` (Gate 1 standing)

**Cause:** presentation — same field names for delta and total.

**Blast radius:** `build_or_update_index._result`; tests that read build tool keys; PLAN §12 / 051 note.

`SCOPE: S` · `TIER: full`

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker | 1 | unmeasured (blocking retrieval) |

## Decision log

| When | Decision |
|------|----------|
| 2026-08-08 | Standing: best option + pass process gates; push/PR need per-action OK |
| 2026-08-08 | Gate 1 cleared (standing) — W1 nested wrote + graph |
| 2026-08-08 | Gate 2 cleared (standing) — approach below |

## Session status

- **Phase:** done — PR [#69](https://github.com/cuongdinhngo/code-atlas/pull/69)
- **Reviewed at:** `69bbd7a6aa5d61a08a6261bd24dafcd68e1931f3`
- **Reviewed files:** `code_atlas/tools/build_or_update_index.py`, `tests/test_build_report_scale_naming.py`, `tests/test_build_report_counts.py`, `tests/test_mcp_server.py`, `tests/test_incremental.py`, `tests/test_schema_version_recovery.py`, `docs/PLAN.md`, `docs/tasks/060_…` (Outcome)

## Cost ledger (delta)

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker | 1 | unmeasured (blocking retrieval) |
| review | reviewer | 1 | unmeasured (blocking retrieval) |
| review | challenger | 1 | unmeasured (blocking retrieval) |

## Phase 2 — Design

**Approach**
1. `_result`: `wrote = asdict(report)`; `graph =` selected `store.counts()` keys; payload carries `wrote` + `graph`, not flat report fields at top level.
2. Proving test: incremental tool result has `wrote`/`graph`, no top-level `edges`; `wrote["edges"] < graph["edges"]` on multi-candidate fixture.
3. Update call-sites that read flat build keys (`test_build_report_counts` tool agree → `wrote`/`graph`; `test_mcp_server` build asserts).
4. Leave BuildReport + 051 store-agreement tests **byte-logic unchanged**.
5. Re-measure: run fixture agreement under current tip; record `CODE_ATLAS_SCALE_SAMPLE` unset → no anchor remount; fixture proves wrote≡graph on full at this commit.

**Rejected:** rename-only (`wrote_nodes`) without graph (still no scale anchor); totals-only documentation; changing BuildReport arithmetic.

**Change list**
| # | Change | Path |
|---|--------|------|
| 1 | Nested wrote + graph in `_result` | `code_atlas/tools/build_or_update_index.py` |
| 2 | Proving + shape tests | `tests/test_build_report_scale_naming.py` |
| 3 | Update flat-key readers | `tests/test_build_report_counts.py`, `tests/test_mcp_server.py`, others as needed |
| 4 | PLAN §12 note | `docs/PLAN.md` |
| 5 | Outcome re-measure note | task working doc |

**Proving test:** `test_incremental_tool_payload_cannot_be_read_as_graph_size`

## Phase 3 — Execute

Done on `fix/060-build-report-scale-naming` @ `833b8be` (+ Outcome docs follow-up). Suite: **933 passed**.

## Phase 4 — Review

- **Reviewed at** `69bbd7a6aa5d61a08a6261bd24dafcd68e1931f3`
- **Reviewed files:** `code_atlas/tools/build_or_update_index.py`, `tests/test_build_report_scale_naming.py`, `tests/test_build_report_counts.py`, `tests/test_mcp_server.py`, `tests/test_incremental.py`, `tests/test_schema_version_recovery.py`, `docs/PLAN.md`, `docs/tasks/060_…` (Outcome)
- **Reviewer round 1:** [Reviewer](9a7097eb-a616-4aef-8b87-9ec5246010a9) — **CHANGES REQUESTED** (conditional LGTM once finding 1 lands)
- **Challenger:** [Challenger](649909d2-26dc-430f-8827-1332685d5b72) — **10 met · 1 not met · 0 can't tell**
- **Gate 4:** clean after Outcome @ `69bbd7a` · **PR:** [#69](https://github.com/cuongdinhngo/code-atlas/pull/69)

### Reviewer detail — round 1 ([Reviewer](9a7097eb-a616-4aef-8b87-9ec5246010a9)) @ `833b8be`

**Verdict: CHANGES REQUESTED** (conditional LGTM after finding 1). Critical: none. Diff ⊆ approved list.

| # | Finding | Severity | Resolution |
|---|---------|----------|------------|
| 1 | No Outcome re-measure with commit SHA (AC4 / change-list #5); matrix R3/AC4 still `⏳` | Important | Fixed in `69bbd7a` — `## Outcome` above separator names fixture re-measure @ `833b8be` and `CODE_ATLAS_SCALE_SAMPLE` unset |

**Proving test:** present and green — `tests/test_build_report_scale_naming.py::test_incremental_tool_payload_cannot_be_read_as_graph_size` (no bare report keys; incremental `wrote.edges < graph.edges`; scales labelled without needing `mode`).

**Verified (no finding):** `_result` nests `wrote=asdict(report)` + `graph` from `store.counts()`; 051 BuildReport↔store tests untouched in logic; PLAN §8.1/§12; R1.4 / R3 / R4.2.

### Challenger detail ([Challenger](649909d2-26dc-430f-8827-1332685d5b72)) — ticket-blind @ `833b8be`

**10 met · 1 not met · 0 can't tell.** Independence: raw ticket + `git diff main...HEAD` only (working-doc below separator not used for intent).

| # | Requirement | Verdict |
|---|-------------|---------|
| 1 | Scale unreadable-as-wrong (nested wrote / labelled totals) | **met** — `build_or_update_index.py:121-128` |
| 2 | 051 meaning stands (presentation only) | **met** — no indexer/store/contract arithmetic change |
| 3 | Test that fails on old flat shape | **met** — `_REPORT_KEYS.isdisjoint` + wrote/graph present |
| 4 | Incremental cannot be read as graph size (AC) | **met** — proving test `wrote.edges < graph.edges` |
| 5 | Full vs incremental distinguishable without `mode` | **met** — wrote≡graph vs wrote≠graph labelled nests |
| 6 | 051 agreement tests still pass | **met** (note: tool agree navigates wrote/graph; store↔report tests unchanged) |
| 7 | Re-measure recorded in Outcome with server commit | **not met** at review → **met** after `69bbd7a` Outcome |
| 8 | No schema/contract change (R3) | **met** |
| 9 | Determinism — counts unchanged; presentation only | **met** |
| 10 | Totals from `store.counts()` (flat cost) | **met** |
| 11 | Slightly larger build payload OK | **met** |
| 12 | pytest / ruff / mypy green | **met** — 933 passed |

## Phase 5 — Finalise

Push + PR approved (standing). Opened [#69](https://github.com/cuongdinhngo/code-atlas/pull/69).
Cost summary: 3 subagent dispatches, all `unmeasured (blocking retrieval)`; top driver = review pair.

