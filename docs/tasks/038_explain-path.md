---
id: 038
slug: explain-path
title: explain_path(from, to) — control-flow path tool
phase: 1.5
milestone: Task-level
status: done
depends_on: [017, 031]
---

## Goal
Answer a task-level question grep structurally cannot: **how does control reach B from A?** Agents
rarely ask "who calls X" — they ask "what happens when a user submits this form", "what breaks if I
change this". `explain_path` returns the path through the call/include graph between two symbols,
making the graph a reasoning tool, not just a lookup (§19 agent-first pivot).

## Scope / Deliverables
- `explain_path(from_qname, to_qname)`: a bounded, in-SQL traversal over the call/include graph that
  returns a path (sequence of edges) from A to B, reusing the impact/reachability traversal style.
- Distinguish "no path" from an empty/unknown result; mark a path that crosses non-RESOLVED hops as
  unproven (tier discipline consistent with 031/impact).
- Register in `main.build_server` + `TOOL_NAMES`.

## Constraints
- Bounded traversal **in SQL** — never `SELECT` the whole edge table, never load the graph into
  memory (R4.3), same guard as the impact/reachability suites.
- RESOLVED-first: a path that exists only via HEURISTIC/DYNAMIC edges is returned as **unproven**,
  never conflated with a proven path or with "no path".
- No language branches (R1.1); no new abstraction seam (R1.2).

## Acceptance criteria
- Planted graph with a known A→…→B chain: `explain_path` returns exactly that path (asserted, not
  counted).
- An unreachable pair returns a distinct "no path" result, not an empty-as-proof.
- A path crossing only HEURISTIC edges is marked unproven.
- Tool registered and listed via MCP; traversal never selects the whole edge table; suite passes.

## References
`code_atlas/store.py` (`impact_radius`, `reachable_from` — traversal patterns to reuse); tasks 017
(impact), 031 (reachability). PLAN §12 (impact/reachability), §8.2 (tiers). `R1.1`, `R1.2`, `R4.3`.
Feedback origin: [`FEEDBACK.md`](../FEEDBACK.md) round 3 ("add explain_path — the next new tool after
031, ahead of everything else").

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 038 — explain_path (working doc)

- **Ticket:** 038 · local `docs/tasks/038_explain-path.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `684 passed in 38.50s` (`.venv/bin/pytest -q`), main @ `a1fd7b5`
  <!-- baseline exclusions: none -->
- **work_doc_mode:** embed (plain local-file ticket)

---

## Phase 0 — Refine

`REFINE: 4 unresolved surfaced | 4 want-decision asked | 4 how-decision resolved+cited | 4 ASSUMED | skip: no`

**INPUT KIND:** ticket

**Settled wants (ASSUMED under standing approval 2026-08-05 "suggest and do the best option, and pass all gates") — ratified at Gate 1 by that standing approval:**

| # | Want | Chosen direction | Becomes |
|---|------|------------------|---------|
| W1 | When several routes exist, what does the agent get? | **One shortest path**, deterministic tie-break | AC path shape |
| W2 | If the search budget dies before B? | **Distinct `incomplete`** — not no_path / unknown | status=`incomplete` |
| W3 | What counts as a control-flow hop? | **Same `IMPACT_KINDS` as impact/reachability** | edge-kind set |
| W4 | When is the answer unknown vs no_path? | **Unknown only if A or B missing from index** | status=`unknown` |

**Resolved HOW + citation:**

| # | HOW | Resolution | Citation |
|---|-----|------------|----------|
| H1 | Bound knobs | Reuse `CA_IMPACT_MAX_NODES`; depth default unset (closure) | 031 H1; `reachable_from` |
| H2 | RESOLVED-first | Proven path preferred; HEURISTIC/DYNAMIC-only → unproven | ticket Constraints |
| H3 | Store owns SQL | New `GraphStore.explain_path`; tool presents | R1.4 |
| H4 | Register | `TOOL_NAMES` + `build_server` one-module tool | `main.py` pattern |

**Exposure-checker:** [challenger](9b8c4c2a-903d-4839-9c50-d8d6373932c6) — 4 un-exposed → W1–W4.

**Constraints from scan:** R1.1 / R1.2 / R1.4 / R4.3 / R5.2; no new seam.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 0 refine | mango:challenger (exposure-checker) | 1 | unmeasured (blocking retrieval) |
| 1 analysis | extractor (path-traversal facts) | 1 | unmeasured (blocking retrieval) |

---

## Requirements matrix

`SECTIONS: 5 found (Goal, Scope, Constraints, Acceptance criteria, References) | 5 decomposed`
`ROWS: G=1 R=3 C=3 AC=4 W=4`

| ID | Source | Verbatim (short) | Interpretation | Ph1 | Ph2 | Ph3/4 | Status |
|----|--------|------------------|---------------|-----|-----|-------|--------|
| G1 | Goal | how control reaches B from A | Path through IMPACT graph | ticket | Approach | proving test | ✅ |
| R1 | Scope | explain_path(from,to) bounded SQL | store method + tool | store/impact | CL1–2 | tests | ✅ |
| R2 | Scope | no_path ≠ empty/unknown; unproven hops | status enum | W2/W4 | Approach | status tests | ✅ |
| R3 | Scope | Register main + TOOL_NAMES | one new tool | main.py | CL3 | mcp tests | ✅ |
| C1 | Constraints | in-SQL, never whole edge table | frontier JOIN | R4.3 | Approach | SQL waves | ✅ |
| C2 | Constraints | RESOLVED-first unproven | two-phase BFS | H2 | Approach | heuristic test | ✅ |
| C3 | Constraints | R1.1 / R1.2 | no lang branch / no seam | rulebook | — | CI gates | ✅ |
| AC1 | AC | planted chain → exact path | asserted hops | plant | proving | test_planted… | ✅ |
| AC2 | AC | unreachable → no_path | distinct status | W4 | — | test_unreachable… | ✅ |
| AC3 | AC | HEURISTIC-only → unproven | status=unproven | C2 | — | test_heuristic… | ✅ |
| AC4 | AC | registered; suite passes | TOOL_NAMES + 696 | R3 | CL3–4 | mcp + full | ✅ |
| W1 | refine | one shortest path | BFS + ROW_NUMBER tie-break | Phase 0 | Approach | prefer-resolved test | ✅ |
| W2 | refine | incomplete on budget | status=incomplete | Phase 0 | Approach | depth test | ✅ |
| W3 | refine | IMPACT_KINDS | contract.IMPACT_KINDS | Phase 0 | Approach | kinds table | ✅ |
| W4 | refine | unknown iff missing endpoint | nodes lookup | Phase 0 | Approach | missing test | ✅ |

## AC validation

| AC | Ticket | Computed | Match | Falsifiable |
|----|--------|----------|-------|-------------|
| AC1 | exact planted path | assert hop sequence A→B→C | Y | measurable |
| AC2 | distinct no_path | status==no_path, path=[] | Y | measurable |
| AC3 | heuristic unproven | status==unproven | Y | measurable |
| AC4 | registered + suite | EXPLAIN in TOOL_NAMES; 696 pass | Y | measurable |

`CLARIFICATION: 4 raised | 4 ASSUMED standing | j=0`
`TRACK: backend` · `SCOPE: M` · `TIER: full`
`RULE SECTIONS: §1 ✅ R1.1/R1.2/R1.4 · §2 N/A · §3 ✅ R3.2 sole-source · §4 ✅ R4.2/R4.3 · §5 N/A soft · §6 ✅ tests · §7 ✅ docs`

### Gap

| Current | Target |
|---------|--------|
| no path tool | `explain_path` store+tool+tests |
| only set walks (impact/reach) | path with parent pointers |

### Gate 1

**ASSUMED W1–W4 ratified** by standing approval. **cleared.**

---

## Phase 2 — Design

### Approach

1. `GraphStore.explain_path(from, to, *, depth, max_nodes) -> ExplainPathResult` — SQL BFS over outgoing `IMPACT_KINDS` with `path_seen` parent columns; reconstruct hops.
2. RESOLVED-only pass first; on `no_path` (frontier empty), second pass all tiers → `unproven` if found; bound hit → `incomplete`.
3. Missing endpoint(s) → `unknown`; same qname → empty `path` status.
4. Tool `code_atlas/tools/explain_path.py`; register in `main`; caps via `config.impact_max_nodes`.
5. Proving tests in `tests/test_explain_path.py`; update MCP/sql-confinement/lang-agnostic counts + PLAN/BACKLOG.

### Rejected alternatives

| Rejected | Why |
|----------|-----|
| Load full edge table / NetworkX | Violates R4.3; ticket forbids |
| CALLS/NEW/INCLUDES only | W3 chose IMPACT_KINDS for 017/031 consistency |
| Treat budget miss as no_path | Conflates incomplete with proven absence (W2) |
| New depth/max knobs | YAGNI — reuse impact caps (H1/R1.2) |

### Assumptions

| Assumption | Tag |
|------------|-----|
| SQLite ROW_NUMBER available (≥3.25, already required) | verified (store module docstring) |
| INSERT OR IGNORE + first-visit = shortest BFS | verified (standard BFS; tie via ROW_NUMBER ORDER BY) |

### Change list

| # | Change | File | Ph2 rows | k/N |
|---|--------|------|----------|-----|
| 1 | explain_path SQL + result types | `code_atlas/store.py` | R1,C1,C2,W1–W4,AC1–3 | 1/1 |
| 2 | MCP tool module | `code_atlas/tools/explain_path.py` | R1,R2,G1 | 1/1 |
| 3 | Register tool | `code_atlas/main.py` | R3,AC4 | 1/1 |
| 4 | Proving + status tests | `tests/test_explain_path.py` | AC1–4,W1–W4 | 1/1 |
| 5 | MCP/suggestion/count guards | `tests/test_mcp_server.py`, `test_sql_confinement.py`, `test_core_is_language_agnostic.py` | AC4,C3 | 1/1 |
| 6 | Docs | `docs/PLAN.md`, `docs/BACKLOG.md`, this working doc | §7 | 1/1 |

### Verification plan

| AC | Risk layer | Proof | Match |
|----|------------|-------|-------|
| AC1 | logic | unit planted chain | ✅ |
| AC2 | logic | unit no_path | ✅ |
| AC3 | logic | unit heuristic | ✅ |
| AC4 | integration | TOOL_NAMES + full pytest | ✅ |
| W2 | logic | depth=1 → incomplete | ✅ |
| W4 | logic | missing → unknown | ✅ |

**Proving test:** `tests/test_explain_path.py::test_planted_chain_returns_exact_resolved_path`
**Invocation:** `.venv/bin/pytest tests/test_explain_path.py -q`

**Rollback:** revert the branch. **Porting:** single repo.

### Gate 2

Standing approval clears Gate 2. **cleared.**

---

## Phase 3 — Execute

**Branch:** `feat/038-explain-path` from `main`.

### Design-conformance

| Approach bullet | Classification |
|-----------------|----------------|
| 1 SQL BFS + parents | implemented-as-approved |
| 2 RESOLVED-first two-phase | implemented-as-approved |
| 3 unknown / same-qname | implemented-as-approved |
| 4 tool + register + caps | implemented-as-approved |
| 5 tests + docs | implemented-as-approved |

### Sweep

- Axis 1 file set ⊆ change list: ✅
- Axis 2 behaviour: ✅ no deviations
- Suite: **696 passed** (post-change)

### Cost ledger (continued)

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 3 execute | (none) | — | — |

---

## Phase 4 — Review

`Reviewed at 12b0c2f3ea1564b999574fc1b8f378e5608fb03a`
Reviewed files: `code_atlas/store.py`, `code_atlas/tools/explain_path.py`, `code_atlas/main.py`, `tests/test_explain_path.py`, `tests/test_mcp_server.py`, `tests/test_sql_confinement.py`, `tests/test_core_is_language_agnostic.py`, `docs/PLAN.md`, `docs/BACKLOG.md`, `docs/tasks/038_explain-path.md`

### Reviewer (`mango:reviewer` · [6ed2b502](6ed2b502-2cc4-4c33-bfa2-69c06b090c67))
- **Verdict:** **LGTM**
- **Scope:** `main..feat/038-explain-path` 10 files ⊆ Gate-2 list; no reformatting of untouched lines
- **Behaviour axis:** all 5 Approach bullets implemented-as-approved (SQL BFS + parents; RESOLVED-first / incomplete short-circuit; unknown / same-qname; tool + caps; tests + docs)
- **Rules:** R1.1 / R1.2 / R1.4 / R3.2 / R4.2 / R4.3 / R5.2 / R7.4 / R7.5 — no Critical/Important findings
- **Proof:** related slice **156 passed** (`test_explain_path` + mcp + sql_confinement + lang-agnostic + sole-source)
- **Findings:** none
- **Nit (non-blocking):** `test_store_explain_path_prefers_resolved_over_shorter_heuristic` overclaims “shorter” — planted RESOLVED and HEURISTIC routes are both 2 hops (name only; assertion correct)

### Challenger (ticket-blind · [3b467586](3b467586-b10f-441c-baef-f030a801078e))

| # | Rebuilt requirement | Verdict | Evidence / adjudication |
|---|---------------------|---------|-------------------------|
| 1 | `explain_path(from,to)` bounded path over call/include-style graph | **met** | `store.py` IMPACT_KINDS BFS; `explain_path.py` API |
| 2 | Distinguish no_path from empty/unknown | **met** | statuses + missing→unknown / no-route→no_path tests |
| 3 | Non-RESOLVED hops marked unproven | **met** | two-phase search; heuristic-only test |
| 4 | Register `main.build_server` + `TOOL_NAMES` | **met** | `main.py:47,79-80` |
| 5 | In-SQL; never whole edge table (R4.3) | **met** | frontier JOIN expand; max_nodes prune |
| 6 | RESOLVED-first; HEURISTIC-only → unproven not proven/no_path | **met** | prefer-RESOLVED + unproven tests |
| 7 | R1.1 / R1.2 | **met** | plain `create(config)`; module-count 30 |
| 8 | AC planted chain exact path | **met** | `test_planted_chain…` asserts A→B→C hops |
| 9 | AC unreachable → distinct no_path | **met** | `test_unreachable…` |
| 10 | AC HEURISTIC-only → unproven | **met** | `test_heuristic_only…` |
| 11 | AC registered via MCP; suite passes | **met** | mcp EXPLAIN + 133 related / 696 full |

**11 met · 0 not met · 0 can't tell.** Extra statuses (`incomplete`, same-qname empty path) noted as consistent with “bounded”, not unmet.

### Scope reconciliation
- File axis: ✅ approved list only
- Behaviour axis: ✅ Approach as approved; no deviations
- Challenger: all met — no adjudication needed

### Gate 4 status
**clean** — reviewer LGTM at `12b0c2f`; challenger 11/11 met.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| Phase 0 | exposure-checker (challenger) | 1 | unmeasured (blocking retrieval) |
| Phase 1 | extractor (path-traversal facts) | 1 | unmeasured (blocking retrieval) |
| Phase 4 | mango:reviewer | 1 | unmeasured (blocking retrieval) |
| Phase 4 | mango:challenger | 1 | unmeasured (blocking retrieval) |

`LEDGER: 4 dispatch rows | all cells valued or marked unmeasured | complete`

### Durable lesson
Edge-shaped hop dicts must assign `EDGE_FIELDS` keys one statement at a time or the R3.2 sole-source gate fails. See `docs/LESSONS.md` §038.

## Phase 5 — Finalise
- Status → done; BACKLOG + token row; lesson in LESSONS.md
- Outward: push branch + open PR (user-approved 2026-08-05) → [#44](https://github.com/cuongdinhngo/code-atlas/pull/44)

## Session status

- **Ticket:** 038
- **work_doc_mode:** embed
- **working-doc path:** `docs/tasks/038_explain-path.md`
- **Current phase:** finalise complete
- **Reviewed at:** `12b0c2f3ea1564b999574fc1b8f378e5608fb03a`
- **Blocked on:** —
- **Next action:** —
- **PR:** [#44](https://github.com/cuongdinhngo/code-atlas/pull/44)
