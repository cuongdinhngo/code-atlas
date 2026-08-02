---
id: 017
slug: impact-engine
title: Impact engine + tool + prompts (M6)
phase: 1
milestone: M6
status: done
depends_on: [013, 016]
---

## Goal
Bounded blast-radius analysis in SQL (§12 impact engine).

## Scope / Deliverables
- Bounded best-score relaxation in SQLite: seed = changed qnames; per-edge-kind weight/direction policy (`CALLS/NEW`→callers, `EXTENDS/IMPLEMENTS`→subtypes, `INCLUDES` follows requires, `CONTAINS` not traversed); one best score/node, decay per hop, floor, bounded by `CA_IMPACT_DEPTH`/`CA_IMPACT_MAX_NODES`; exclude `DYNAMIC` by default.
- `impact(paths|qnames, depth?)` tool; `impact_of_change` prompt.

## Acceptance criteria
- Traversal happens in SQL (never loads the whole graph); respects depth/max-node caps.
- Blast radius for a known change matches a hand-traced expectation.

## References
Plan §12 (impact engine), §15 (M6).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 017 — Impact engine + tool + prompts (working doc)

- **Ticket:** 017 · [docs/tasks/017_impact-engine.md](017_impact-engine.md) (raw above separator)
- **Type:** enhancement
- **Repo(s) / Porting:** `app` (`.`) only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `528 passed in 21.21s` (`.venv/bin/pytest -q` on `main` @ `22b84cb`). baseline exclusions: none
- **work_doc_mode:** `embed` → below separator (harness `embed`; sibling `017_*.work.md` would be scooped by `test_backlog_bookkeeping.task_files`)

## Session status

```
phase: 5 finalise
Gate: 4 clean; Reviewed at: 2b40f18
work_doc_mode: embed
working_doc: docs/tasks/017_impact-engine.md (below separator)
```

---

## Phase 0 — Refine

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`

`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

`REFINE: 8 unresolved surfaced | 0 asked live (handed back → ASSUMED) | 9 how-decision resolved+cited | 6 ASSUMED | skip: no`

**INPUT KIND:** ticket (single deliverable — not an epic).

**Premise:** Plan §12/§15, `CA_IMPACT_*`, edge kinds, DYNAMIC, deps 013+016 resolve; `impact` + `impact_of_change` to-be-created. Ambiguous: “code-review-graph…” prose.

### ASSUMED (ratified Gate 1 under standing approve)

| # | Assumed choice | Why ASSUMED | Explicit confirm | Reverses prior? |
|---|----------------|-------------|------------------|-----------------|
| A1 | Seed `1.0`; weights CALLS/NEW `1.0`, EXTENDS/IMPLEMENTS `0.9`, INCLUDES `0.8`; decay `×0.7`/hop; floor `0.05`; best score/node | W1 best (per-kind weights) | Gate 1 standing | no |
| A2 | Only `RESOLVED` expands; HEURISTIC/DYNAMIC never expand | W2; 013 HOW-5 | Gate 1 standing | no |
| A3 | Proving test = planted SQLite graph; hand-traced set+scores | W3 | Gate 1 standing | no |
| A4 | `paths` → every node with that `file_path` | W4 | Gate 1 standing | no |
| A5 | Rows `{qname,score,file,line,depth}`; order score DESC, qname ASC; seeds at 1.0 | Exposure #2 | Gate 1 standing | no |
| A6 | Floor inclusive: keep/expand iff `score >= floor` | Exposure #4 | Gate 1 standing | no |

### HOW (cited)

| # | Resolution | Citation |
|---|------------|----------|
| 1 | `tools/impact.py` + `TOOL_NAMES`; add only `impact_of_change` | CONVENTION §2; Plan §12 |
| 2 | CALLS/NEW→callers; EXTENDS/IMPLEMENTS→subtypes; INCLUDES→requires direction; CONTAINS never; unlisted kinds not traversed | ticket Scope; Plan §12:371 |
| 3 | depth=`CA_IMPACT_DEPTH` (arg override); cap=`CA_IMPACT_MAX_NODES` | ticket; config |
| 4 | DYNAMIC excluded from traversal | ticket; R5.2 |
| 5 | Traversal SQL in `store.py`; tool presents | R1.4; AC1 |
| 6 | Symbol-level results (not bodies) | Plan §12; nav |
| 7 | `paths`∪`qnames` when both given | exposure #1; Plan seed |
| 8 | Seeds count toward max_nodes; ties by qname ASC | R4.2; exposure #3 |
| 9 | Unknown path/qname → empty success | R5.3; nav empty; exposure #5 |

### Exposure-checker

[challenger](c603802d-67ba-4d42-9d99-ab80f2061b7d): `UNEXPOSED: 5` → HOW-7/8/9 + A5/A6.

---

## Phase 1 — Analysis

`PREMISE:` / `RECALL:` carried from refine.

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=0 R=2 G=1 AC=8`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | Bounded blast-radius analysis in SQL (§12 impact engine). | Store SQL walk + scored nodes; tool+prompt surface it | Plan §12:370-371; no impact yet | Approach | store.impact + tool | ❌ |
| R1 | Scope | Bounded best-score… DYNAMIC by default | A1–A2,A6 + HOW-2–5,7–8 in store | gap | change-list 1 | proving + SQL caps tests | ❌ |
| R2 | Scope | `impact(paths\|qnames, depth?)` tool; `impact_of_change` prompt | tool module + prompt + register | gap | change-list 2–4 | MCP + prompt tests | ❌ |
| AC1 | AC | Traversal in SQL; respects depth/max-node caps | No whole-graph load; depth & max_nodes enforced in SQL path | R4.3 | change-list 1 | SQL/caps tests | ❌ |
| AC2 | AC | Blast radius matches hand-traced expectation | A3 planted graph exact set+scores | A3 | proving test | proving PASS | ❌ |
| AC-A1 | refine | scoring constants | as A1 | A1 | A1 | planted scores | ❌ |
| AC-A2 | refine | RESOLVED-only expand | as A2 | A2 | A2 | HEURISTIC non-expand test | ❌ |
| AC-A3 | refine | planted proof | as A3 | A3 | A3 | proving | ❌ |
| AC-A4 | refine | path→all file nodes | as A4 | A4 | A4 | path-seed test | ❌ |
| AC-A5 | refine | result shape/order | as A5 | A5 | A5 | shape asserts | ❌ |
| AC-A6 | refine | floor inclusive | as A6 | A6 | A6 | floor test | ❌ |

### AC validation

| AC ID | Ticket / ASSUMED | Computed | Match? | Falsifiable? | Gate-1 |
|-------|------------------|----------|--------|--------------|--------|
| AC1 | SQL + caps | SQL waves/CTE; depth & max_nodes | Y | greppable/tests | — |
| AC2 | hand-traced | A3 planted exact | Y under A3 | measurable | ratify A3 |
| A1 nums | not in Plan | A1 constants | ASSUMED | measurable | ratify A1 |
| A2–A6 | ASSUMED | as Phase 0 | Y if ratified | measurable | Gate 1 |

### Inventory

- **N = 2 surfaces** (tool + prompt) plus store engine.

| # | Item | Status |
|---|------|--------|
| T1 | `impact` tool | ❌ |
| T2 | `impact_of_change` prompt | ❌ |

`SURFACES:` N/A — `TRACK: backend`.

### Clarifications

`CLARIFICATION: 6 raised | 9 how self-resolved (Phase 0) | 6 for human (ASSUMED A1–A6)` → Gate 1 ratification only; **j=0 open design Qs** after standing approve.

### Gap analysis

| Slice | Current | Target | Evidence |
|-------|---------|--------|----------|
| Impact engine | absent | SQL best-score in store | no `impact` in store |
| Tool | absent | `impact` + register | `TOOL_NAMES` lacks it |
| Prompt | explore/find_usages only | + `impact_of_change` | `prompts.py:7-10` |
| Caps | config knobs unused | consumed by impact | `config.py` |

### Blast radius

- **Entry:** `store.py` impact query; `tools/impact.py`; `prompts.py`; `main.py` TOOL_NAMES; tests (`test_mcp_server` TOOL_NAMES; prompt list).
- **Repos:** `app` only. **db-map:** N/A.

`TRACK: backend — 0/N UI paths`

### Rule sections

`RULE SECTIONS: §1 ✅ R1.1/R1.2/R1.4 (SQL in store, tools present, no new seam) · §2 N/A · §3 N/A (no contract bump) · §4 ✅ R4.1–R4.3 · §5 ✅ R5.2/R5.3 · §6 ✅ R6.1/R6.2 · §7 ✅ R7.2 docs · §8 N/A`

### Scope / Tier

- **SCOPE:** M — engine + one tool + one prompt + tests + docs.
- **TIER:** full — N>1; not lite.

**Gate 1:** ASSUMED A1–A6 ratified under standing “best option / pass all gates”. Cleared.

---

## Decision log

| When | Decision | Rationale |
|------|----------|-----------|
| Phase 0 | W1–W4 + exposure → ASSUMED A1–A6 | standing best option |
| Gate 1 | Ratify A1–A6; clear | standing pass all gates |
| Gate 2 | Approve approach + change-list | standing pass all gates |

---

## Phase 2 — Design

### Approach

Add `GraphStore.impact_radius(...)` that walks **incoming** RESOLVED edges of kinds CALLS/NEW / EXTENDS/IMPLEMENTS / INCLUDES (all three policies are “who points at the changed node”) with per-kind weights (A1), decay ×0.7/hop, floor 0.05 inclusive (A6), best score per qname, depth + max_nodes caps — implemented as **iterative SQL waves** (temp frontier → JOIN edges → merge best) so traversal never `SELECT`s the whole edge table. Tool `impact(paths?, qnames?, depth?)` unions path nodes (A4) with explicit qnames (HOW-7), returns A5-shaped rows. Prompt `impact_of_change` steers status→impact→read_symbol. Register tool in `main`; update MCP/prompt tests.

### Rejected alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Python BFS like `find_callers` | Violates AC1 “in SQL” / R4.3 spirit |
| Traverse HEURISTIC with lower weight | Violates A2 |
| File-level-only blast radius | Violates symbol seed + Plan qname grain |
| New tool registry | R1.2 |

### Assumptions

| Assumption | Tag | Resolution |
|------------|-----|------------|
| Incoming-edge walk implements CALLS→callers, EXTENDS→subtypes, INCLUDES→requires | verified | edge direction in contract/adapters |
| Iterative SQL waves = “traversal in SQL” for AC1 | novel-untested → proving | proving + caps tests fail if Python loads all edges |
| Per-call GraphStore + FastMCP prompt pattern | verified | 010–014 |

### Smallest change-list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| 1 | `impact_radius` SQL waves + constants | `code_atlas/store.py` | none beyond impact callers | R1, AC1, AC-A* | 1 |
| 2 | `impact` tool | `code_atlas/tools/impact.py` | MCP | R2, AC-A4/A5, T1 | 1 |
| 3 | `impact_of_change` prompt | `code_atlas/tools/prompts.py` | MCP prompts | R2, T2 | 1 |
| 4 | Register `impact` in TOOL_NAMES / build_server | `code_atlas/main.py` | `test_mcp_server` TOOL_NAMES | G1, T1 | 1 |
| 5 | Proving + caps + HEURISTIC + path-seed tests | `tests/test_impact.py` (new) | — | AC1–2, AC-A* | 1 |
| 6 | Proof collateral: TOOL_NAMES + PROMPT_NAMES expects | `tests/test_mcp_server.py`, `tests/test_search_read_outline.py` | — | T1–T2 | 1 |
| 7 | Docs: BACKLOG/frontmatter status; PLAN if needed | docs | readers | R7.2 | 1 |

**Test blast-radius:** `test_mcp_server.py` TOOL_NAMES tuple; prompt set in `test_search_read_outline.py`.

### Rule compliance

R1.1/R1.2/R1.4 · R4.2/R4.3 · R5.2/R5.3 · R6.1 · R7.2 — as analysis RULE SECTIONS.

### Verification plan

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 SQL + caps | integration (store SQL) | planted graph + depth/max_nodes asserts; no full-graph load | ✅ |
| AC2 hand-trace | integration | exact set+scores vs hand trace | ✅ |
| AC-A1–A6 | logic+integration | unit asserts on planted cases | ✅ |
| T1–T2 | integration | MCP list_tools / list_prompts | ✅ |

### Proving test

`tests/test_impact.py::test_impact_matches_hand_traced_planted_graph` — plant seeds+edges; assert results equal hand-traced `{qname,score,depth}` (A1 math). Invocation: `.venv/bin/pytest tests/test_impact.py -q`.

### Rollback / porting

Revert the change-list commit(s). Repos: `app` only.

**Gate 2:** cleared under standing approve.

---

## Phase 3 — Execute

**Branch:** `feat/017-impact-engine` @ `ca0e50f` (3693287 → 65b8142 SQL waves → ca0e50f score/depth pair)

**Verification sweep**

| Check | Result |
|-------|--------|
| Proving test | `test_impact_matches_hand_traced_planted_graph` PASS |
| Impact suite | `tests/test_impact.py` — **8 passed**; with MCP/store collateral **110 passed** focused |
| Diff ⊆ change-list | store/impact/prompts/main/tests/docs/contract weights — items 1–7 |
| Approach bullets | SQL temp-table waves + RESOLVED-only + A1 weights + tool/prompt — **implemented-as-approved** |
| Deviations | none (post-execute hardening stayed inside item 1 + 5) |

Flows to review.

---

## Phase 4 — Review

**Reviewed at** `2b40f18` (impact suite 9 passed; tip after round-2 fixes). Bookkeeping tips after (`740cfb9`, `f4a4db7`) are stale-review exempt.

| Dispatch | Verdict |
|----------|---------|
| mango:reviewer round 1 ([Reviewer](b3717f52-4275-4a12-afd1-cf42eb7986a8)) | **CHANGES REQUESTED** — Python best-score / path 10k cap / proving kinds / mypy |
| mango:challenger round 1 ([Challenger](b4802a05-62b6-4d46-8d7e-59f1c1dafdc7)) | **NOT CLEAN** — 3 met · 1 not met · 1 can't tell (relaxation held in Python) |
| mango:reviewer round 2 ([Reviewer](86de1d76-5c4d-4763-90ff-68a45e18b551)) | **CHANGES REQUESTED** — unknown-qname synthetic hit; exact-fill `truncated` |
| mango:challenger round 2 ([Challenger](31ddc96d-3a17-4c81-ac8c-8fc767c4aff8)) | **NOT CLEAN** — 4 met · 1 not met · 0 can't tell (`max_nodes` result-only) |
| mango:reviewer round 3 verify ([Reviewer](d6f51888-ed89-4a94-a7ab-bb23c975a8a8)) | **LGTM** — prior findings verified fixed; `tests/test_impact.py` → **9 passed** |

### Reviewer detail round 1 ([Reviewer](b3717f52-4275-4a12-afd1-cf42eb7986a8))

- **Verdict:** CHANGES REQUESTED
- **Tip then:** `3693287`
- **Verification then:** targeted impact/MCP/SQL-guard **110 passed**; ruff clean; mypy failed (finding 4)
- **Finding 1 (Important — AC1 / R4.3):** `code_atlas/store.py` applied `max_nodes` only after materializing all reachable nodes into a Python `best` dict — unbounded fan-out risk
- **Finding 2 (Important — A4):** `code_atlas/tools/impact.py` path seeds silently stopped at `limit=10_000`
- **Finding 3 (Important — R6.1 / AC2):** proving graph omitted `NEW`, `IMPLEMENTS`, `INCLUDES`
- **Finding 4 (R6.6):** sort key `int(row["line_start"] or 0)` failed strict mypy

**Fixed in:** `65b8142` (SQL temp-table waves + `nodes_by_file_all` + full-kind proving + mypy) · `ca0e50f` (pair depth with MAX(score) path)

### Challenger detail round 1 ([Challenger](b4802a05-62b6-4d46-8d7e-59f1c1dafdc7)) — ticket-blind

`REQUIREMENTS: 5`

| # | Reconstructed requirement | Verdict | Evidence |
|---|---------------------------|---------|----------|
| 1 | Edge direction / weights / decay / floor; exclude DYNAMIC | met | `contract.py` IMPACT weights; store RESOLVED join |
| 2 | Bounded best-score relaxation entirely in SQLite; depth + max-node caps; no whole-graph load | **not met** | best/frontier/relaxation in Python; `max_nodes` post-sort only |
| 3 | `impact(paths\|qnames, depth?)` with config caps | met | `tools/impact.py`; `main.py` register |
| 4 | `impact_of_change` prompt | met | `prompts.py` |
| 5 | Hand-traced known blast radius | can't tell | planted test present; challenger env could not run pytest |

**Blocker:** core traversal/relaxation not SQL-side → addressed by round-1 fixes.

### Reviewer detail round 2 ([Reviewer](86de1d76-5c4d-4763-90ff-68a45e18b551))

- **Verdict:** CHANGES REQUESTED (prior 1–4 verified fixed; impact suite **8 passed**; mypy clean)
- **Finding 1 (HOW-9 / R5.3):** unknown qnames became synthetic score-1.0 hits when a DB existed — `tools/impact.py` + `tests/test_impact.py` codified the wrong behaviour
- **Finding 2 (R4.2 / CONVENTION §6):** `truncated = len(results) >= max_nodes` flagged exact fills as truncated (nav tools use fetch `max+1`)

**Fixed in:** `2b40f18` (drop unknown qname seeds; fetch `max_nodes+1` for honest `truncated`; SQL prune of best/frontier each wave)

### Challenger detail round 2 ([Challenger](31ddc96d-3a17-4c81-ac8c-8fc767c4aff8)) — ticket-blind

`REQUIREMENTS: 5` · proving test **1 passed**

| # | Reconstructed requirement | Verdict | Evidence |
|---|---------------------------|---------|----------|
| 1 | Traverse callers/subtypes/includers in SQLite; no CONTAINS; exclude DYNAMIC | met | store expand JOIN + IMPACT weights |
| 2 | Best-score + decay + floor | met | SQL score calc + upsert |
| 3 | Bound by depth and `CA_IMPACT_MAX_NODES` | **not met** | depth loop OK; `max_nodes` only on final SELECT — frontier/best still unbounded |
| 4 | `impact` tool + `impact_of_change` prompt | met | tool + prompts + main |
| 5 | Hand-traced blast radius | met | `test_impact_matches_hand_traced_planted_graph` |

**Blocker:** `max_nodes` must bound traversal working set → `2b40f18` prunes `impact_best` / frontier each wave (and after oversized seed insert).

**Note:** challenger saw the embedded working doc in the branch diff (independence compromised warning); verdict still keyed to raw ticket + implementation evidence.

### Reviewer detail round 3 verify ([Reviewer](d6f51888-ed89-4a94-a7ab-bb23c975a8a8))

- **Verdict:** LGTM
- **Prior findings verified fixed:**
  1. Unknown qname → empty results (not synthetic seed)
  2. `truncated` only when `len > max_nodes` (fetch max+1)
  3. `max_nodes` prunes SQL best/frontier each wave
- **Verification:** `.venv/bin/pytest tests/test_impact.py -q` → **9 passed**

### Matrix Ph3/4

All G/R/AC rows → ✅ proven by impact tests + MCP registration + review rounds.

**Gate 4:** clean.

---

## Cost ledger

| Phase | Dispatch | Round | Tokens | Notes |
|-------|----------|-------|--------|-------|
| refine | challenger (exposure-checker) | 1 | unmeasured (host does not surface usage) | [c603802d](c603802d-67ba-4d42-9d99-ab80f2061b7d); UNEXPOSED: 5 |
| review | reviewer | 1 | unmeasured (host does not surface usage) | [b3717f52](b3717f52-4275-4a12-afd1-cf42eb7986a8); CHANGES REQUESTED |
| review | challenger | 1 | unmeasured (host does not surface usage) | [b4802a05](b4802a05-62b6-4d46-8d7e-59f1c1dafdc7); 3 met / 1 not met / 1 can't tell |
| review | reviewer | 2 | unmeasured (host does not surface usage) | [86de1d76](86de1d76-5c4d-4763-90ff-68a45e18b551); CHANGES REQUESTED |
| review | challenger | 2 | unmeasured (host does not surface usage) | [31ddc96d](31ddc96d-3a17-4c81-ac8c-8fc767c4aff8); 4 met / 1 not met |
| review | reviewer | 3 verify | unmeasured (host does not surface usage) | [d6f51888](d6f51888-ed89-4a94-a7ab-bb23c975a8a8); LGTM |

**PR:** https://github.com/cuongdinhngo/code-atlas/pull/27

