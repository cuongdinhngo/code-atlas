---
id: 015
slug: php-full-coverage-and-scale
title: Full PHP coverage + scale to 112k files (M4)
phase: 1
milestone: M4
status: in-progress
depends_on: [013, 014, 008]
---

## Goal
Prove global-namespace/PSR-0 resolution and large-repo performance (§6, §8).

## Scope / Deliverables
- Global-namespace & PSR-0 (`Foo_Bar_Baz` ↔ `Foo/Bar/Baz.php`) resolution end-to-end.
- `include_graph(path, direction)` tool over `include`/`require` edges.
- Run the ~112k-file validation sample (a large PHP monorepo) end-to-end; capture full-build timing as the perf target.
- **CI:** the 112k-file run cannot live in per-PR CI — wrong runtime, and the sample is not a public checkout. Put it in a separate opt-in / scheduled workflow (or a documented local procedure) and record the timing as an artifact, so "timing recorded" has a place to be recorded to.

## Acceptance criteria
- Underscore/global symbols resolve correctly (not dropped).
- Full build over the large sample completes and stays within memory caps; timing recorded.

## References
Plan §6, §6.1, §8, §12, §15 (M4), §17 (scale risk).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 015 — Full PHP coverage + scale (working doc)

- **Ticket:** 015 · [docs/tasks/015_php-full-coverage-and-scale.md](015_php-full-coverage-and-scale.md)
- **Type:** enhancement
- **Repo(s):** `app` (`.`) only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `503 passed in 18.10s` (`.venv/bin/pytest -q` on `main` @ `c3722dd`). baseline exclusions: none
- **work_doc_mode:** `embed`

---

## Phase 0 — Refine

`PREMISE: 8 reference(s) checked | 0 missing | 3 ambiguous` · `RECALL: 0` · `REFINE: 4 want + exposure 5 → ASSUMED`

**ASSUMED (ratified Gate 1 under standing approve):**

| # | Choice |
|---|--------|
| A1 | Fixture e2e for underscore/global resolution (+ optional sample smoke) |
| A2 | No new memory knob — pass = completes without OOM; host profile in timing JSON |
| A3 | Documented local/opt-in procedure + timing artifact; no scheduled GHA this ticket |
| A4 | Resolver batch/stream in scope |
| A5 | `include_graph` direction ∈ {imports, imported_by, both}; depth default 1; CA_MAX_RESULTS cap |
| A6 | Timing = baseline capture, no SLA fail bar |
| A7 | Sample via `CODE_ATLAS_SCALE_SAMPLE` (operator-provisioned out-of-tree) |
| A8 | Unresolved externals stay unlinked (Plan §8.2); “not dropped” = declarations + linkable targets |

`UNEXPOSED: 5` from exposure-checker → folded into A5–A8 / HOW.

---

## Phase 1 — Analysis

`SECTIONS: 4 found (Goal, Scope, AC, References) | 4 decomposed | ROWS: C=0 R=4 G=1 AC=2+ASSUMED`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|----|--------|------------------|----------------|--------------|--------|
| R1 | Scope | Global/PSR-0 resolution e2e | Fixture layout Foo/Bar/Baz.php + Legacy_Table links | fixtures + tests | ✅ |
| R2 | Scope | include_graph tool | MCP tool over INCLUDES | main TOOL_NAMES | ✅ |
| R3 | Scope | 112k sample run + timing | Opt-in script + runbook (sample out-of-tree) | scripts + runbook | ✅ |
| R4 | Scope | CI not per-PR | Documented local procedure | runbook | ✅ |
| G1 | Goal | Prove resolution + scale | R1–R4 | — | ✅ |
| AC1 | AC | Underscore/global resolve | A1/A8 | proving test | ✅ |
| AC2 | AC | Sample completes + memory + timing | A2/A3/A6/A7 | script + runbook | ✅ |

`CLARIFICATION: 0 open | ASSUMED A1–A8 ratified at Gate 1`

---

## Decision log

| When | Decision | Rationale |
|------|----------|-----------|
| Phase 0 | 1A–4A + exposure A5–A8 ASSUMED | standing “best option / pass all gates” |
| Gate 1 | Ratify ASSUMED; clear | standing approve |
| Gate 2 | Approve design | standing approve |

---

## Phase 2 — Design

### Approach

Ship M4 coverage+scale: (1) stream/batch resolver unresolved edges; (2) `include_graph` tool; (3) PSR-0 layout fixture proof; (4) opt-in `scripts/scale_full_build.py` + `docs/runbooks/scale-sample.md`.

### Change-list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| 1 | `iter_unresolved_edges` / `link_edges` / `insert_edges` | `store.py` | resolver + tests | A4, AC2 | 1 |
| 2 | Resolver uses batches | `resolver.py` | all builds | A4 | 1 |
| 3 | `include_graph` tool | `tools/include_graph.py` | MCP TOOL_NAMES | R2, A5 | 1 |
| 4 | Register tool | `main.py` | mcp tests, guard counts | R2 | 1 |
| 5 | PSR-0 + include fixtures + proving tests | `tests/fixtures…`, `test_scale…` | — | AC1, R2 | 1 |
| 6 | Scale script + runbook | `scripts/`, `docs/runbooks/` | gitignore artifacts | R3–R4, AC2 | 1 |
| 7 | Docs PLAN/BACKLOG/README | docs | readers | R7.2 | 1 |
| 8 | Guard count 21→22 | core guard tests | — | proof collateral | 1 |

### Proving test

```text
.venv/bin/pytest -q tests/test_scale_and_include_graph.py::test_underscore_global_symbols_resolve_on_psr0_layout
```

---

## Phase 3 — Execute

**Branch:** `feat/015-php-full-coverage-and-scale`

**Implemented:** change-list 1–8 as approved. **Deviations:** none. Large-sample wall-clock not run in-session (sample not in tree) — procedure + script proven on tiny fixture.

**Verification (paste):**
```
.venv/bin/pytest -q tests/test_scale_and_include_graph.py tests/test_resolver.py tests/test_mcp_server.py
→ 61 passed
.venv/bin/pytest -q --tb=line
→ 514 passed in 18.71s
```

**Axis 1:** diff ⊆ change-list ✅

---

## Cost ledger

| Phase | Dispatch | Round | Tokens | Notes |
|-------|----------|-------|--------|-------|
| refine | challenger (exposure-checker) | 1 | unmeasured (host does not surface usage) | [1e75450c](1e75450c-c709-4e93-864a-a90cb2bf6c52); UNEXPOSED: 5 |

---

## Session status

- **Phase:** 3 execute → review
- **PR:** —
- **Reviewed at:** —
- **Gate:** proceeding under standing approve
- **Blocked by:** none
- **Revert path:** delete branch `feat/015-php-full-coverage-and-scale`
