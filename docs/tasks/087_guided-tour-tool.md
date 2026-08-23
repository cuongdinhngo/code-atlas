---
id: 087
slug: guided-tour-tool
title: Onboarding — guided_tour tool (M11)
phase: 3
milestone: M11
status: done
depends_on: [083, 086]
---

## Goal
A dependency-ordered walk through the codebase — the reading order a newcomer (human or agent) should
follow.

## Scope / Deliverables
- New `code_atlas/tools/guided_tour.py`: topological order over the include/call graph, seeded from
  entry points, **cycle-safe via SCC condensation**. Returns ordered stops each with a one-line
  rationale.
- **SCC lands here** (deferred from 083) and is **node-budgeted**, the pattern `impact`/`reach` already
  use (R4.3 — never load the whole graph).

## Acceptance criteria
- Tour order respects the dependency structure; a graph with a cycle is handled without a loop.
- Bounded memory (R4.3); deterministic (R4.2).
- Fixture test with a cycle asserts the order and that the node budget is honoured.

## References
[`../phase3-onboarding/ROADMAP.md`](../phase3-onboarding/ROADMAP.md) §4 (M11);
PLAN §14, §15 (M11).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 087 — Onboarding — guided_tour tool (M11) (working doc)

- **Ticket:** 087 · local file `docs/tasks/087_guided-tour-tool.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N touched files under UI paths
- **TIER:** full
- **BASELINE:** green — `.venv/bin/pytest -q` → **1336 passed, 0 failed** (untouched `main`, 2026-08-18). baseline exclusions: none.
- **CHALLENGER:** OFF (`--no-challenger` / operator: skipped Review + Challenger)
- **REVIEW:** SKIPPED (operator argument). Do not reintroduce.

---

## Session status

- **Runner:** `/mango:solve 087 with skipped Review + Challenger`. Standing approval: suggest and take the best option, pass all gates; after the task, commit + push + open PR (`AGENTS.md` *Maintainer workflow* + this run's args).
- **work_doc_mode:** embed (`.harness.json`; plain local-file ticket, not a breakdown stub). **Path:** `docs/tasks/087_guided-tour-tool.md` (below this separator).
- **Phase:** 5 finalise — review waived; proceeding to PR under standing approval.
- **Branch:** `feat/087-guided-tour-tool`.
- **Gate 0:** j = 0 — no human questions.
- **Gate 1:** cleared on standing approval (best-option + pass-all-gates).
- **Gate 2:** cleared on standing approval.
- **Gate 4:** **waived** (REVIEW: SKIPPED, CHALLENGER: OFF). Not a clean-review claim.
- **Final gate:** cleared on standing approval (commit + push + open PR).

---

## Phase 0 — Refine (the FIRST phase)

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 3 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**refine skipped: 0 unresolved product-decisions**

**Premise (all resolve):**
| Ref | Class | Found |
|-----|-------|-------|
| `code_atlas/tools/guided_tour.py` | to-be-created | absent, as framed |
| `impact` / `reach` (`impact.py`, `reachable_from.py`, `reach_shared.py`) | referenced-as-existing | present |
| R4.3 / R4.2 | referenced-as-existing | `docs/ENGINEERING_RULES.md:75-79` |
| `docs/phase3-onboarding/ROADMAP.md` | referenced-as-existing | present, §4 M11 |
| `docs/PLAN.md` §14/§15 | referenced-as-existing | present |
| tickets 083, 086 | referenced-as-existing | both `status: done` |

**Skip rationale.** The ticket names the module, the algorithm (topo + SCC condensation), the seed (entry points), the bound (impact/reach node budget / R4.3), and the proving fixture (cycle + budget). 083 already locked module unit = file path and entry-point = zero-inbound roots; PHASE3 §4 M11 open points that are *this* ticket's (granularity, stop budget) are answered by those locks + the ticket's "pattern impact/reach already use". Artifact location and markdown coherence belong to 088. No acceptance-bar want survives. Exposure-checker does not run on skip.

**Recalled claims (ADVISORY — surfaced only):**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | 085-C1 count-pin-in-blast-radius | 2 | handle — new core module under `code_atlas/` | yes — `len(core_modules()) == 46` pins |
| 2 | derived-not-listed-invariant (093-C2 / 095-C1 / 097-C1) | 2 | handle — new member of `TOOL_NAMES` | yes — probe / which_tool / listed tuples |
| 3 | prove-the-guard-fails (093-C3) | 2 | handle — new guard (cycle + budget) | yes — proving test must fail pre-change |
| 4 | 102-C3 | 5 | area: impact / store / tool payloads | weigh — tour is repo-wide, not a subject tool |
| 5 | 038 type-5 | 5 | area: store / tools / R3.2 | weigh — new store method must import kinds from `contract` |

**Constraints from scan:** R1.1 / R1.2 / R1.4 / R4.1 / R4.2 / R4.3 / R6.1 / R6.5 / R6.7 / R7.2 / R8.2; CONVENTION §6 (one module per tool, `NAME` + `create`); 086 payload conventions (`index_root`, reason, `total_count`, `truncated`, `detail_level`); SQL only in `store.py`; no LLM.

**INPUT KIND:** ticket (single deliverable — not an epic).

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=2 R=2 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | A dependency-ordered walk through the codebase — the reading order a newcomer (human or agent) should follow. | 16th MCP tool `guided_tour`: ordered module stops, entry-seeded, top-down along outgoing resolved deps. | `main.py` has 15 tools, no `guided_tour`. PHASE3 §4 M11; 083 entry-points. | change-list 1–4 | `tests/test_guided_tour.py` + `TOOL_NAMES` | ✅ |
| R1 | Scope | New `code_atlas/tools/guided_tour.py`: topological order over the include/call graph, seeded from entry points, cycle-safe via SCC condensation. Returns ordered stops each with a one-line rationale. | Presentation-only tool; SCC/topo in a pure onboarding module; store supplies a **budgeted** module subgraph. Stops = file paths (083 module unit). | `architecture_overview.py` pattern; `onboarding/metrics.py:125` defers SCC to 087. | change-list 1–3 | `code_atlas/tools/guided_tour.py` · `onboarding/tour.py` | ✅ |
| R2 | Scope | SCC lands here (deferred from 083) and is node-budgeted, the pattern impact/reach already use (R4.3 — never load the whole graph). | Do **not** call unbounded `node_universe`/`dependency_edges` for the walk. SQL waves + `max_nodes` (reuse `CA_IMPACT_MAX_NODES`). SCC in Python over that subgraph only. | `store.py:522-548` unbounded pulls; `impact_radius` / `reachable_from` wave+prune. | change-list 1–2 | `store.py` `tour_subgraph` | ✅ |
| C1 | Scope / AC | Bounded memory (R4.3) | `max_nodes` prunes the walk; `truncated` when the budget binds; no `fetchall` of all edges. | R4.3 `ENGINEERING_RULES.md:78-79`. | change-list 1, 5 | proving test `impact_max_nodes=2` | ✅ |
| C2 | Scope / AC | Deterministic (R4.2) | Stable `ORDER BY` / sorted ready-set Kahn / sorted keys inside an SCC; two runs byte-identical. | R4.2 `:75-77`. | change-list 2, 5 | `test_guided_tour_is_byte_stable_across_two_runs` | ✅ |
| AC1 | AC | Tour order respects the dependency structure; a graph with a cycle is handled without a loop. | Fixture E→A⇄B: E before {A,B}; each file at most once; condensation is a DAG (no cross-SCC back-edge in the stop order). | unbuilt | change-list 5 | proving test | ✅ |
| AC2 | AC | Bounded memory (R4.3); deterministic (R4.2). | Same as C1+C2, asserted: `max_nodes=2` on a larger graph → `truncated` and `len(results) ≤ 2`; two calls equal. | unbuilt | change-list 5 | proving test | ✅ |
| AC3 | AC | Fixture test with a cycle asserts the order and that the node budget is honoured. | Named proving test over a planted cycle + a budget-prune case. | no `tests/test_guided_tour.py` | change-list 5 | proving test | ✅ |

References decomposed as the M11 source for R1/R2 (not a separate requirement row — citing PHASE3/PLAN, no extra deliverable).

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | order respects deps; cycle without a loop | Pin: each stop appears ≤1; for every cross-SCC edge src→tgt, src is not after tgt; cycle nodes share one SCC and still terminate | Y | measurable (fixture asserts) | — |
| AC2 | Bounded memory (R4.3); deterministic (R4.2) | Pin: `max_nodes=M` ⇒ visited ≤ M and `truncated`; `payload1 == payload2` | Y | measurable | — |
| AC3 | Fixture test with a cycle asserts order + budget | The AC1+AC2 fixture **is** this test | Y | measurable (`tests/test_guided_tour.py`) | — |

No uncodified standard applied as a gate (payload conventions are already in CONVENTION §6 / 086).

## Inventory (universal "all/every/no")

- **Denominator / total N:** 1 (the cycle fixture graph) — "a graph with a cycle" is one planted graph, not every repo.
- Numbered list:
  1. The cycle fixture (E→A⇄B plus budget prune)

TRACK is backend — no `SURFACES:` line.

## Clarifications

`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`

- Self-resolved:
  1. **Stop grain = file path** — 083 locked "Module unit = file path"; PHASE3 §4 M10 #1. Ticket "include/call graph" at the same grain `architecture_overview` already uses.
  2. **Seeds = zero-inbound module files**; if that set is empty (pure cycle), seed the lexicographically first file so SCC still runs — 083 entry-point lock + ticket "cycle-safe"; `SELECT … ORDER BY file_path LIMIT 1` stays R4.3-bounded.
  3. **Node budget = `CA_IMPACT_MAX_NODES`** (no new knob) — ticket "pattern impact/reach already use"; 031 H1 YAGNI. Payload list still capped at `CA_MAX_RESULTS` (086 / CONVENTION §6).
  4. **Walk top-down from entries along outgoing resolved deps** (same edge set as `dependency_edges`, all resolved kinds) — ticket "seeded from entry points" + PHASE3 "entry point + first 5 things to read?".
- For human decision: none (`j = 0`).

## Phase 1 — Analysis ✋ Gate 1

- **Gap (enhancement):** `code_atlas/tools/` has `architecture_overview` (layers) but no reading-order walk. `onboarding/metrics.py:125` explicitly defers SCC to 087. `store.dependency_edges` / `node_universe` load the whole graph — unusable for 087's R4.3 SCC. Target: a 16th tool that returns ordered file stops with rationales, SCC-safe, node-budgeted.
- **Handler / blast radius:** new `tools/guided_tour.py` + `onboarding/tour.py` + `store` subgraph method; register in `main.py` `TOOL_NAMES` + `build_server`; `prompts.which_tool`; count-pins `== 46` → 48; `tests/test_mcp_server.py` listed `TOOL_NAMES`; recognition probe Q16; README tool table + unsigned-claim row + batching-exclusion row + `which_tool` "15"; PLAN §12 row + §15 M11; BACKLOG 087; field-retro heading is historical (086's 15th) — update the live "15 tools" strings that describe the current surface.
- **Rule-compliance section coverage:**

`RULE SECTIONS: 28 applicable — 28 by change-type | 0 by recalled handle — §1 R1.1 (change-type) ✅ no language token in new modules · R1.2 ✅ no new seam (085 Summarizer unused here) · R1.3 ✅ core still depends on contract only · R1.4 ✅ SQL in store, SCC pure, tool presents · R1.5 N/A because no adapter · R1.6 N/A because no new capability · R1.7 N/A because no coerced census blob · §2 R2.1–R2.3 N/A because no adapter source · §3 R3.1 N/A because no vocabulary change · R3.2 ✅ edge/node kinds from contract · R3.3 N/A because no adapter emit · R3.4 N/A because no adapter · §4 R4.1 ✅ no LLM/network · R4.2 ✅ sorted Kahn + stable SQL · R4.3 ✅ SQL waves + max_nodes, never whole edge table · §5 R5.1 N/A because read-only · R5.2 ✅ resolved edges only expand (same as dependency_edges) · R5.3 N/A because no new CA_* knob · R5.4 N/A because no try_instead route on this tool · R5.5 N/A because no signed claim line · §6 R6.1 ✅ fixture tool test · R6.2 N/A because fixture is language-neutral `.aa` · R6.3 N/A because AC does not demand a real-repo run (086 did; 087's ACs are fixture) · R6.4 ✅ existing grep-gates cover new files · R6.5 ✅ proving test fails pre-change · R6.6 N/A because no new analyser · R6.7 ✅ probe/TOOL_NAMES derived where a derivation exists; listed mcp-server tuple updated as the existing pin · §7 R7.1 ✅ one tool · R7.2 ✅ PLAN/BACKLOG/README · R7.3 ✅ commits · R7.4 ✅ tour.py is the second consumer 088 will need, not a one-shot interface · R7.5 ✅ comments ≤3 · §8 R8.1 N/A · R8.2 ✅ stdlib SCC, no NetworkX · R8.3 N/A`

Recalled handles add **0** rulebook sections (`handle:` tags are in rule *prose* for R6.5/R6.7, already applicable by change-type). PROVISIONAL R5.4/R5.5/R6.7/R1.7 listed; none gate-block.

- **Self-audit:** RECALL emitted, sections 4=4, AC falsifiable, BASELINE green, j=0, inventory N=1, RULE SECTIONS answered, STRUCTURE native, TRACK backend, TIER full (SCOPE=M, several files, not lite).
- **Gate 1 status:** cleared (standing approval).

`TRACK: backend — 0/N touched files under UI paths`

---

## Phase 2 — Design ✋ Gate 2

- **Approach:**
  1. `GraphStore.tour_subgraph(max_nodes) -> TourSubgraph` — SQL: collect zero-inbound **file_path** seeds (`ORDER BY`, prune to `max_nodes`); if none, one deterministic seed (`ORDER BY file_path LIMIT 1`). Expand **outgoing** resolved cross-file edges in waves (temp tables, `INSERT OR IGNORE`, prune to `max_nodes`) — the `reachable_from` pattern at module grain, kinds = all resolved (same as `dependency_edges`, no language branch). Return visited files, edges among them, `truncated`.
  2. `code_atlas/onboarding/tour.py` — Tarjan SCC + Kahn topo of the condensation (ready-set sorted) + sorted order inside an SCC. Each stop: `file`, one-line `rationale` (`entry point (zero inbound)` / `cycle with a.aa, b.aa` / `reached from <pred>`). Pure, no SQL.
  3. `code_atlas/tools/guided_tour.py` — presentation: unbuilt → `not_indexed`; empty index → `no_matches`; else `results` capped at `max_results`, `truncated` if walk **or** page bound binds, `total_count` = stop count before the page cap. `detail_level` `minimal` (file only) / `standard` (+ rationale, + `scc` when size>1). No verbose (YAGNI). No SQL, no LLM.
  4. Register as the 16th tool; bump count-pins 46→48; probe Q16; docs.

- **Rejected alternatives:**
  - Load `node_universe`+`dependency_edges` then SCC in Python (086's metrics path) — violates the ticket's R4.3 node budget; 083 deferred SCC specifically to avoid that.
  - NetworkX / a new SCC dependency — R8.2; Tarjan is ~40 lines of stdlib.
  - Symbol-level stops — 083 locked file grain; a 40k-symbol tour is the PHASE3 length risk.
  - New `CA_TOUR_MAX_NODES` — 031 H1 / R1.2 YAGNI; reuse `impact_max_nodes`.
  - SQL-only SCC — possible but not the impact/reach *pattern* (waves in SQL, reasoning in Python).

**Assumptions**

| Assumption | verified / novel-untested | If novel-untested 3p/runtime → spike result OR integration-shaped proving test |
|------------|---------------------------|--------------------------------------------------------------------------------|
| SQLite temp-table wave prune terminates on a cycle (same as `reachable_from`) | verified | `store.py:1270` comment + 031 tests; proving fixture is a cycle |
| Tarjan + Kahn on a ≤`max_nodes` graph is deterministic given sorted ties | verified | stdlib; proving test equality of two runs |
| FastMCP registers a new `create()` tool the same as 086 | verified | `architecture_overview` + `test_mcp_server.py` |

**Smallest change-list**

| Change | File/area | Blast radius (side-effect surface) | Ph2 covered by | k/N |
|--------|-----------|------------------------------------|----------------|-----|
| 1. Budgeted module-grain subgraph (SQL waves, `max_nodes`) | `code_atlas/store.py` | SQL-confinement guard still passes (SQL stays here); `test_sql_confinement` count pin | R2, C1, C2 | 3/3 |
| 2. Pure SCC + topo + rationale | `code_atlas/onboarding/tour.py` (new) | `len(core_modules())` pins; R1.1 grep-gate glob | R1, R2, C2, AC1 | 4/4 |
| 3. MCP tool presentation | `code_atlas/tools/guided_tour.py` (new) | count pin; tool-module import graph | G1, R1 | 2/2 |
| 4. Register 16th tool | `code_atlas/main.py` | `TOOL_NAMES` consumers: mcp-server listed tuple, routing/claim/batching derived sweeps, probe protocol | G1 | 1/1 |
| 5. Proving + payload tests | `tests/test_guided_tour.py` (new) | none beyond the new file | AC1, AC2, AC3, C1, C2 | 5/5 |
| 6. Count-pin bump 46→48 | `tests/test_sql_confinement.py`, `tests/test_core_is_language_agnostic.py` | the two pins **are** the blast (085-C1) | R2 (collateral) | 1/1 |
| 7. Listed `TOOL_NAMES` pin + OVERVIEW-style import | `tests/test_mcp_server.py` | stdio list-tools assertion | G1 | 1/1 |
| 8. Probe Q16 (occasion-worded) | `docs/runbooks/tool-recognition-probe.md` | `test_recognition_probe_protocol.py` derives intended tools from `TOOL_NAMES` | G1, R6.7 | 1/1 |
| 9. `which_tool` map row + "15" → "16" | `code_atlas/tools/prompts.py` | README which_tool row | G1 | 1/1 |
| 10. Unsigned-claim + batching-exclusion + tools table | `README.md` | PLAN §12 mirrors the table | G1, R7.2 | 1/1 |
| 11. PLAN §12 row + §15 M11 note | `docs/PLAN.md` | namespace_tree leftover untouched | G1, R7.2 | 1/1 |
| 12. BACKLOG 087 status + "15th tool" next-line | `docs/BACKLOG.md` + this ticket frontmatter | 088 still depends on 087 | R7.2 | 1/1 |

**HANDLES** (type-2 from RECALL, answered at this blast-radius step):

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply | 0 unanswered`

| Handle | Answer | Command + result (trimmed) |
|--------|--------|----------------------------|
| count-pin-in-blast-radius | **traced** — two pins at 46; new `tour.py` + `guided_tour.py` → 48. Folded as change-list 6. | `rg -n 'len\(core_modules\(\)\) ==' tests` → `test_core_is_language_agnostic.py:42` and `test_sql_confinement.py:32` both `== 46` |
| derived-not-listed-invariant | **traced** — probe/claim/batching **derive** from `TOOL_NAMES` (auto-cover once registered). The mcp-server **lists** the tuple (existing pin, same as 086). Probe markdown must gain a row or the derived guard fails. Folded as 4, 7, 8, 9. | `rg -n 'TOOL_NAMES ==' tests` → `tests/test_mcp_server.py:168`; `rg -n 'all 15 tools'` → `prompts.py:4,61` `README.md:322` `field-retro.md:39` (historical heading — live surface strings in prompts/README updated; retro heading is a past-round label, left unless it claims current count) |
| prove-the-guard-fails | **traced** — proving test is the cycle+budget fixture; execute records it failing on `main` before the tool exists (`import` / `pytest` red), then passing. Folded as change-list 5. | `rg -l guided_tour tests code_atlas` → no test/tool file yet (pre-change red is import/collection failure of the named test once added, and absence of the tool on `main`) |

field-retro "Coverage of the 15 tools" is a **historical** section title about a past round — not a live denominator. Not folded (does not apply to the current surface pin).

- **Rule compliance:** as RULE SECTIONS above; CONVENTION §6: `NAME` + `create`, question-first docstring, `index_root` on every payload, reason codes from `nav_result`.
- **Proving test:** `tests/test_guided_tour.py::test_guided_tour_orders_a_cycle_without_looping_and_honours_the_node_budget` — invocation: `.venv/bin/pytest -q tests/test_guided_tour.py`. Fails before the tool exists; passes after. Layer: integration (real `GraphStore` + fixture files, same as 086).

**Verification plan**

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 | integration (order over a stored graph) | integration — fixture `GraphStore` + tool payload | ✅ |
| AC2 | integration (budget + byte-stability over store) | integration — `max_nodes=2` prune + two-run equality | ✅ |
| AC3 | integration (the fixture test *is* AC1+AC2) | same proving test | ✅ |
| C1 / C2 | same as AC2 | same | ✅ |

**Coverage-gap exclusions:** none.

**Proof manifest:** n/a (`TRACK: backend`).

- **Rollback + porting:** revert the feature branch. Single repo (`config.repos` = app).
- **DESIGN.md:** n/a (backend).
- **SCOPE confirmed:** M (new tool + store method + pure SCC module + registration + docs). Has not crossed to L.
- **Gate 2 status:** cleared (standing approval).

## Phase 3 — Execute

- **Branch:** `feat/087-guided-tour-tool`
- **Commits:** `6c2475e` feat; bookkeeping SHA/PR after open.
- **Proving test added:** `tests/test_guided_tour.py::test_guided_tour_orders_a_cycle_without_looping_and_honours_the_node_budget`
- **Verification sweep — BOTH axes.** *File axis:* zero stray references ✅ · diff ⊆ approved list ✅ with one recorded proof-collateral file (`tests/test_tool_descriptions.py` — listed `== 15` pin, derived to `TOOL_NAMES`) · each hunk maps to a row ✅. *Behaviour axis:* Approach bullets 1–4 `implemented-as-approved`.
- **Design-conformance deviations:** none.
- **Empirical output:**

```
$ git show main:code_atlas/tools/guided_tour.py
fatal: path 'code_atlas/tools/guided_tour.py' exists on disk, but not in 'main'

$ .venv/bin/pytest -q
1347 passed in 61.73s
# baseline on untouched main: 1336 passed. Delta +11 (5 authored tests in
# test_guided_tour.py + parametrized TOOL_NAMES cases); none removed.

$ .venv/bin/ruff check code_atlas tests
All checks passed!
$ .venv/bin/mypy code_atlas
Success: no issues found in 48 source files
```

- **Golden/snapshot change:** none.
- **Design-invalidation / re-gate:** none.

## Phase 4 — Review ✋ (waived at solve time; a direct review was run on the PR)

- reviewer verdict: **not run** (operator: skipped Review + Challenger)
- challenger: **OFF**
- Clean? **not claimed.** Finalise proceeds under the waiver + handover authorisation.
- **Reviewed at:** n/a (review waived — stale-review guard does not apply)

### Review round on PR #126 (maintainer asked for a direct review; 0 dispatch, in-session)

CI on the PR is red for **four billing-blocked jobs** ("recent account payments have failed"), not for
code — no job started. The gate was proven in Docker instead (`scripts/docker-test.sh`).

Four findings, every one reproduced against `6c2475e` before the fix and green after
(one probe, both trees: `4 FAIL → 4 PASS`):

| # | Finding | Repro on `6c2475e` | Fix |
|---|---------|--------------------|-----|
| 1 | A component **no entry point reaches** was silently absent, with `truncated: false` and a `total_count` of only the reachable part — the 102 class (an absence indistinguishable from a complete answer) | index of 3 files (entry + `X ⇄ Y`) → **1 stop**, `truncated: false`, `total_count: 1` | `store.tour_subgraph` re-seeds the lowest unseen file until the budget binds (`round` column; earlier rounds outrank later ones under the prune), and `truncated` now derives from *an indexed file is not in the tour* |
| 2 | Recursive Tarjan → `RecursionError` once `CA_IMPACT_MAX_NODES` (user-settable, no ceiling) admits a deep chain | `ordered_stops` on a 1200-file chain → `RecursionError` | iterative work-stack in `_components`; probe at 1500 |
| 3 | A stop claimed `entry point (zero inbound)` where the store had proved no such thing — a budget-cut cycle member | one-cycle graph, `max_nodes=1` → `rationale: "entry point (zero inbound)"` | `TourSubgraph.entry_points` carries the proven zero-inbound set; an unproven stop reads `reached from outside the walk` |
| 4 | `results` capped at `CA_MAX_RESULTS` with **no `offset`** — the tail of a reading order was unreachable, against the convention 086 set one ticket earlier | `guided_tour(offset=2)` → `TypeError` | `offset` + `results_offset`, mirroring `architecture_overview` |

Also folded in, no behaviour change: `_topo` uses a heap instead of re-sorting the ready set each pop,
and `_rationale` keeps an incremental `emitted` set instead of rebuilding one per stop (both were
quadratic in the budget, harmless at 500 and not at a raised one).

**Delta-green after the fixes:** `1347 → 1353 passed, 0 failed` (+6 authored tests; none removed),
ruff clean, mypy **48 files**; confirmed in Docker (`scripts/docker-test.sh`).

## Phase 5 — Finalise ✋ final gate

- PR draft: from `.github/pull_request_template.md`
- Planned outward actions (each approved by this run's args + `AGENTS.md` maintainer workflow):
  - [x] push branch
  - [x] bookkeeping (lesson + BACKLOG) folds into the branch-push
  - [x] open PR via `gh`
  - [ ] tracker comment — N/A (local-file ticket, no tracker issue)
  - [ ] tracker transition — N/A
- Follow-up tickets: none deferred. 088 remains the next M11 card.
- **Durable lesson:** 087 in `docs/LESSONS.md` (listed `len(descriptions) == N` count-pin) + the review round's `087-C2` / `087-C3`. `seen:` appended on 085-C1, 097-C1, 093-C3 and on 100-C4 (`do-not-attest-past-the-payloads-resolution`, now 100, 101, 102, 087) per P1.
- Revert path: revert the feature branch / PR.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified | 0 not cheaply checkable`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/AGENT_BRIEF.md | mango files written: 0`

| # | Claim (id) | Type (proposed) | Evidence | Handle / area | Recurred? (`seen:`) | Falsified? | Proposed destination | Human ratified? |
|---|------------|-----------------|----------|---------------|---------------------|------------|----------------------|-----------------|
| 1 | 087-C1 / 085-C1 | 2 | `test_tool_descriptions.py` listed `== 15` | count-pin-in-blast-radius | 085, 087 (**2**) | still true: the pin existed and broke adding a tool; cheap `rg 'len(descriptions) =='` | `agent_brief_path` (process; widen P-rule or 085-C1) | **proposed** — `/mango:promote` is the cross-ticket pass |

Cross-ticket: `count-pin-in-blast-radius` now `seen:` 085, 087. Human runs `/mango:promote` between tickets.

---

## Cost ledger (descriptive — facts only, never auto-cuts)

`COST-LEDGER: 0 dispatch row(s) | complete`

Dispatch **0 rows** — no subagent was dispatched: refine self-skipped, review waived, challenger off, analysis fan-out done in the main loop. Main-loop **unmeasured (host does not surface usage)**.

| phase | dispatch | round | tokens |
|-------|----------|-------|--------|
| (none) | — | — | unmeasured (host does not surface usage) |
