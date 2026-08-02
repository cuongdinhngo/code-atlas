---
id: 013
slug: nav-tools
title: Navigation tools — callers / references / implementations (M2)
phase: 1
milestone: M2
status: done
depends_on: [011, 010]
---

## Goal
Answer relationship queries from the resolved graph (§12).

## Scope / Deliverables
- `find_callers(qname, depth?)` — who CALLS/NEW it (+ confidence tier).
- `find_references(qname)` — all edges targeting it.
- `find_implementations(qname)` — EXTENDS/IMPLEMENTS subtypes.
- Return qnames + `file:line`, not bodies.

## Acceptance criteria
- On a known class, `find_callers` matches a manual baseline (accounting for dynamic calls).
- Confidence tiers surfaced; dynamic edges flagged, not silently linked.

## References
Plan §12, §15 (M2).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 013 — Navigation tools — callers / references / implementations (working doc)

- **Ticket:** 013 · [docs/tasks/013_nav-tools.md](013_nav-tools.md) (raw above separator)
- **Type:** enhancement
- **Repo(s) / Porting:** `app` (`.`) only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `439 passed in 16.14s` (`.venv/bin/pytest -q` on `main` @ `88cc512`). baseline exclusions: none
- **work_doc_mode:** `embed` → this doc lives below the separator (harness `work_doc_mode: embed`)

---

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`

`REFINE: 5 unresolved surfaced | 0 asked live (handed back → ASSUMED) | 5 how-decision resolved+cited | 5 ASSUMED | skip: no`

**INPUT KIND:** ticket (single deliverable — not an epic).

**Settled wants / ASSUMED (awaiting Gate-1 ratification)** — user replied “ok” to recommended W1–W3; exposure-checker W4–W5 taken as recommended ASSUMED:

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses prior? |
|---|----------------|-------------|--------------------------|-----------------|
| A1 | Manual baseline = resolve fixtures (`\\App\\User` / `\\App\\Repo::put` / `\\App\\helper`) | Recommended; user “ok” | Gate 1 | no |
| A2 | `depth` default **1** (direct); depth=N = transitive BFS of CALLS/NEW; cap `CA_MAX_RESULTS` | Recommended; user “ok” | Gate 1 | no |
| A3 | DYNAMIC **included** in results with tier surfaced; **not traversed** when depth>1 | Recommended; user “ok” | Gate 1 | no |
| A4 | `find_callers` matches the **exact qname** only (no auto-expand to `Type::method` members) | Exposure-checker WANT; recommended (Serena owns expand; separate qname for members) | Gate 1 | no |
| A5 | `find_implementations` = **direct** EXTENDS/IMPLEMENTS children only (no depth; transitive → impact/017) | Exposure-checker WANT; recommended | Gate 1 | no |

**Resolved HOW (+ citation):**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Tool layout / registration | One module per tool under `code_atlas/tools/`; `main.TOOL_NAMES` + `CA_TOOLS` | CONVENTION §2; `main.py`; Plan §12 |
| 2 | `detail_level` | Every tool takes `detail_level ∈ {minimal, standard}` | Plan §12:331 |
| 3 | SQL ownership | Query helpers in `store.py`; tools call them | R1.4; `edges_by_*` |
| 4 | Return shape | qnames + `file:line` + confidence; not bodies | ticket Scope; Plan §12:331 |
| 5 | HEURISTIC at depth>1 | **Do not traverse** HEURISTIC (or DYNAMIC); only RESOLVED CALLS/NEW expand the BFS. HEURISTIC still appears when it is a found edge | Plan §12 impact (DYNAMIC excluded from traversal); R5.2; exposure-checker #3 |

**Constraints from scan:**
- Only `get_index_status` + `build_or_update_index` registered today.
- Store already has `edges_by_source` / `edges_by_target` (limit-capped).
- Resolver proving path: callers of `\\App\\Repo::put` → `\\App\\User::save` (HEURISTIC on `put`).

**Exposure-checker** ([challenger](1d6fc984-1994-43da-a48b-1e3b653e4c65)): `UNEXPOSED: 3` → filed as A4, A5, HOW-5 above.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=0 R=4 G=1 AC=7`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | Answer relationship queries from the resolved graph (§12). | Three nav tools query linked edges in SQLite; return qname+file:line+tier | Plan §12; store edges | Approach + change-list | tools + `edges_by_target` on `target_qname`; challenger #7 | ✅ |
| R1 | Scope | `find_callers(qname, depth?)` — who CALLS/NEW it (+ confidence tier). | Tool + store query; depth per A2/A3/A4/HOW-5 | gap: no tool | change-list (2) | `find_callers.py` + proving + challenger #1 | ✅ |
| R2 | Scope | `find_references(qname)` — all edges targeting it. | Any kind targeting qname (linked `target_qname`) | gap | change-list (3) | `find_references.py` + `test_nav_tools` refs; challenger #2 | ✅ |
| R3 | Scope | `find_implementations(qname)` — EXTENDS/IMPLEMENTS subtypes. | Direct children only (A5) | gap | change-list (4) | `find_implementations.py` + direct-only test; challenger #3 | ✅ |
| R4 | Scope | Return qnames + `file:line`, not bodies. | Response rows: source/target qname, path, line, tier | Plan §12 | Approach | `nav_result.edge_hit`; challenger #4 | ✅ |
| AC1 | AC | On a known class, `find_callers` matches a manual baseline (accounting for dynamic calls). | Baseline A1: after build of resolve fixtures, `find_callers("\\App\\Repo::put")` includes `\\App\\User::save` | `test_resolver.py:273-274` | proving test | `test_find_callers_matches_resolve_fixture_baseline` PASS; challenger #5 | ✅ |
| AC2 | AC | Confidence tiers surfaced; dynamic edges flagged, not silently linked. | Every hit exposes `confidence_tier`; DYNAMIC never omitted from the flag / never traversed (A3) | | Approach + A3 | tier on hits + DYNAMIC non-traverse test; challenger #6 | ✅ |
| AC-A1 | refine | Baseline = resolve fixtures | AC1 pinned to that graph | A1 | A1 | proving indexes resolve fixtures | ✅ |
| AC-A2 | refine | depth default 1 / transitive BFS / MAX_RESULTS | measurable defaults + hop behaviour | A2 | A2 | `depth=1` default + BFS in `find_callers` | ✅ |
| AC-A3 | refine | DYNAMIC include+flag; no traverse | result field + BFS rule | A3 | A3 | DYNAMIC returned; only RESOLVED enqueued | ✅ |
| AC-A4 | refine | exact qname only | no member expansion | A4 | A4 | `test_exact_qname_does_not_expand_to_members` | ✅ |
| AC-A5 | refine | implementations direct only | no transitive subtypes | A5 | A5 | `test_find_implementations_are_direct_only` | ✅ |

`PREMISE:` carried from refine (6 / 0 / 1).

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 if needed |
|-------|---------------|------------------------|--------|--------------|------------------|
| AC1 | known class / manual baseline | Pin to resolve fixtures + `\\App\\Repo::put` ← `\\App\\User::save` | Y under A1 | measurable | ratify A1 |
| AC2 | tiers surfaced; dynamic flagged | Each result row has `confidence_tier`; DYNAMIC rows present when seeded; not used as BFS seed | Y under A3 | measurable | ratify A3 |
| AC-A2/A4/A5 | ASSUMED | as above | Y if ratified | measurable | Gate 1 |

## Inventory

- **N = 3 tools** (universal “the nav tools” / every tool registration).

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| T1 | `find_callers` | `main.py` register + proving + MCP TOOL_NAMES | ✅ |
| T2 | `find_references` | `main.py` register + refs test + MCP | ✅ |
| T3 | `find_implementations` | `main.py` register + impls test + MCP | ✅ |

`SURFACES:` N/A — `TRACK: backend`.

## Clarifications

`CLARIFICATION: 5 raised | 0 self-resolved beyond Phase-0 HOW | 5 for human (ASSUMED A1–A5 at Gate 1)`

`j = 5` at Gate 1 as ASSUMED confirms (not open design questions beyond ratification).

## Cause / gap analysis

| Slice | Current | Target | Evidence |
|-------|---------|--------|----------|
| Nav tools | absent | three tools + registration | `main.py:19` only two names |
| Callers query | `edges_by_target` exists (depth=1 only) | + optional BFS depth | `store.py:259` |
| Baseline proof | resolver unit asserts callers | MCP/tool-level AC1 | `test_resolver.py:273-274` |

## Blast radius

- **Entry:** `code_atlas/tools/find_*.py`, `main.py` TOOL_NAMES, possibly `store.py` helpers, tests.
- **Repos:** `app` only.
- **db-map:** N/A.

`TRACK: backend — 0/N UI paths`

## Rule-compliance section coverage

`RULE SECTIONS: §1 ✅ (tools call store; no language branches); §2 N/A; §3 N/A (no contract bump); §4 ✅ (deterministic queries); §5 ✅ (missing DB → indexed:false / empty, not create); §6 ✅ (fixture baseline tests); §7 ✅ (BACKLOG sync); §8 N/A`

## Scope / Tier

- **SCOPE:** M — three tools + store/query + registration + proving tests.
- **TIER:** full — inventory N=3 tools > 1; not lite-eligible.

---

## Decision log

| When | Decision | Rationale |
|------|----------|-----------|
| Gate 1 | Ratify A1–A5 + HOW-5; clear Gate 1 | User `approve` |

---

## Phase 2 — Design

### Approach

Add three MCP tools (`find_callers`, `find_references`, `find_implementations`) as one-module-each under `code_atlas/tools/`, registered in `main.TOOL_NAMES` / `build_server` like the existing two. Each opens its own `GraphStore` per call (thread rule). Queries stay in `store.py` (extend `edges_by_target` to accept multiple kinds where needed); BFS for `find_callers` depth>1 lives in the callers tool (or a tiny pure helper next to it) — only **RESOLVED** CALLS/NEW edges enqueue the next hop; HEURISTIC/DYNAMIC hits are returned with their tier but never traversed. Exact qname match only. Implementations = direct EXTENDS/IMPLEMENTS whose `target_qname` is the query. Hits are `{qname, file, line, kind, confidence_tier[, depth]}` — no bodies. Honour `detail_level` and `config.max_results`.

### Rejected alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Auto-expand class qname to all `Type::*` members | Violates A4; Serena owns precise expand |
| Transitive `find_implementations` | No depth in §12; belongs to impact (017) — A5 |
| Traverse HEURISTIC/DYNAMIC at depth>1 | Violates A3 / HOW-5; would silently promote guesses |
| New abstraction/registry for tools | R1.2 — keep the explicit `main.py` branches until a second axis appears |

### Assumptions

| Assumption | Tag | Resolution |
|------------|-----|------------|
| Resolve fixtures + full_build produce the baseline callers edge | verified | `test_resolver.py:273-274` |
| FastMCP + per-call GraphStore pattern still works for new tools | verified | task 010 / `test_mcp_server.py` |
| Multi-kind edge filter can be a thin store extension without schema change | verified | existing `_edges` + kind narrow |

### Smallest change-list

| # | Change | File/area | Ph2 covered by | k/N |
|---|--------|-----------|----------------|-----|
| 1 | Store: edges targeting a qname filtered by one or many kinds (reuse for callers/impls) | `code_atlas/store.py` | R1–R3, G1 | 1 |
| 2 | `find_callers` tool (depth default 1, BFS, RESOLVED-only traverse, MAX_RESULTS) | `code_atlas/tools/find_callers.py` | R1, R4, AC1–AC2, AC-A2–A4 | 1/3 tools |
| 3 | `find_references` tool (all kinds → target) | `code_atlas/tools/find_references.py` | R2, R4, AC2 | 1/3 |
| 4 | `find_implementations` tool (direct EXTENDS/IMPLEMENTS) | `code_atlas/tools/find_implementations.py` | R3, R4, AC-A5 | 1/3 |
| 5 | Register three names in `TOOL_NAMES` + `build_server` | `code_atlas/main.py` | G1, T1–T3 | 1 |
| 6 | Proving + unit/integration tests (resolve-fixture baseline; DYNAMIC flagged; depth/exact-qname) | `tests/test_nav_tools.py` (new) | AC1, AC2, AC-A* | 1 |
| 7 | **Proof collateral:** update `TOOL_NAMES` equality / listing expects in MCP tests | `tests/test_mcp_server.py` | T1–T3 registration | 1 |
| 8 | Bookkeeping: BACKLOG/frontmatter `in-progress` (already) → `done` at finalise | docs | R7.2 | later |

**Test blast-radius:** `tests/test_mcp_server.py:154` asserts `TOOL_NAMES == (STATUS, BUILD)` — must update (item 7). `next_tool_suggestions` tests that filter against registered names stay valid if they use dynamic `TOOL_NAMES`. Resolver tests untouched.

### Rule compliance

- R1.1 / R1.4 / R1.2 — no language branches; SQL in store; no new seam.
- R4.3 — per-call store open.
- R5.2 / R5.3 — tiers surfaced; missing DB → empty/flagged, not create.
- R6.1 — fixture baseline tests.
- CONVENTION — tool names snake_case, one file each.

### Verification plan

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 baseline callers | integration (build + tool) | integration test over resolve fixtures | ✅ |
| AC2 tiers / DYNAMIC flag | integration (seeded DYNAMIC + tool) | integration/unit over store+tool | ✅ |
| AC-A2 depth | logic + integration | unit BFS + integration depth=1 | ✅ |
| AC-A3/A4/A5 | logic | unit asserts on tool/helpers | ✅ |
| G1 / R1–R4 / T1–T3 | integration | MCP list_tools + call | ✅ |

### Proving test

Fails pre-change (tool missing); passes post-change:

```text
.venv/bin/pytest -q tests/test_nav_tools.py::test_find_callers_matches_resolve_fixture_baseline -q
```

Full proving module: `tests/test_nav_tools.py` (callers baseline + DYNAMIC surfaced + implementations direct + references).

### Rollback + porting

- Revert the branch; no schema migration.
- Porting: `app` only.

### SCOPE confirm

**SCOPE: M** — unchanged. Did not outgrow to L.

---

## Phase 3 — Execute

**Branch:** `feat/013-nav-tools`

**Implemented (Axis 2):**

| Approach bullet | Status |
|-----------------|--------|
| Three tools under `code_atlas/tools/` + `main` registration | implemented-as-approved |
| SQL in store (`kinds=` on `edges_by_target`) | implemented-as-approved |
| Callers BFS; RESOLVED-only traverse; HEURISTIC/DYNAMIC flagged not walked | implemented-as-approved |
| Exact qname; implementations direct only | implemented-as-approved |
| Hits = qname+file:line+tier; detail_level; max_results; missing DB empty | implemented-as-approved |
| Proof collateral MCP TOOL_NAMES + suggestions + detail_level N=5 | implemented-as-approved |

**Deviations:** none behavioural. Shared `nav_result.py` helper (within “tiny helper” intent).

**Verification:** proving `test_find_callers_matches_resolve_fixture_baseline` passes; full suite **467 passed**; ruff + mypy clean.

---

## Phase 4 — Review

**Reviewed at** `81b90a99fe4ed92daf524ada68c2ce35295d274a`

**Working-doc path:** `docs/tasks/013_nav-tools.md`

**Reviewed files:** `code_atlas/main.py`, `code_atlas/store.py`, `code_atlas/tools/find_callers.py`, `code_atlas/tools/find_implementations.py`, `code_atlas/tools/find_references.py`, `code_atlas/tools/nav_result.py`, `docs/BACKLOG.md`, `docs/tasks/013_nav-tools.md`, `tests/test_core_is_language_agnostic.py`, `tests/test_mcp_server.py`, `tests/test_nav_tools.py`, `tests/test_sql_confinement.py`

| Critic | Result |
|--------|--------|
| mango:reviewer ([Reviewer](a5f06a99-1eeb-4270-819e-f02d322e331e)) | **LGTM** — 0 Critical / 0 Important; proving 1 passed; diff ⊆ Gate-2 list (+ documented `nav_result` + guardrail count bumps) |
| mango:challenger ([Challenger](91501184-8c47-4508-a726-263bf6be5bca)) | **7 met · 0 not met · 0 can't tell** (ticket-blind) |

**Scope reconcile:** file axis ✅ · behaviour axis ✅ · inventory T1–T3 = 3/3 ✅

**Layer-match:** AC1/AC2 at integration over resolve fixtures ✅ — no unresolved ❌

**Proving (re-check at review):** `.venv/bin/pytest -q tests/test_nav_tools.py::test_find_callers_matches_resolve_fixture_baseline` → **1 passed** (would fail without the tools). Baseline 439 → post 467; no new failures in blast radius (reviewer 93 passed batch).

**Verdict:** clean — Gate 4 does not stop.

**Matrix Status:** G1, R1–R4, AC1–AC2, AC-A1–A5, T1–T3 → ✅

### Reviewer report ([Reviewer](a5f06a99-1eeb-4270-819e-f02d322e331e))

**Verdict: LGTM** @ `81b90a9`. No Critical/Important. Proving PASS. Diff maps to Gate-2 items 1–8; `nav_result.py` + module-count 13→17 are documented/necessary collateral. Rule-book: R1.1/R1.2/R1.4/R3.2/R4.3/R5.2/R5.3/R6.1/R7.5 + CONVENTION §6 pass. SQL `kinds` parameterized.

### Challenger report ([Challenger](91501184-8c47-4508-a726-263bf6be5bca))

**Independence:** raw ticket + `main...HEAD` only. **7 met · 0 not met · 0 can't tell.** Non-blockers noted: `detail_level`, HEURISTIC non-traversal beyond ticket wording, docs churn.

---

## Cost ledger (subagent dispatch only)

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 0 refine | mango:challenger (exposure-checker) | 1 | unmeasured (blocking retrieval) |
| 4 review | mango:reviewer | 1 | unmeasured (blocking retrieval) |
| 4 review | mango:challenger | 1 | unmeasured (blocking retrieval) |

**Roll-up:** **3 dispatch**, all `unmeasured (blocking retrieval)`. Main-loop unmeasured.

---

## Durable lesson

none

---

## Session status

- **Phase:** 5 finalise complete
- **PR:** https://github.com/cuongdinhngo/code-atlas/pull/23
- **Reviewed at:** `81b90a9` (bookkeeping tip after; stale-review exempt)
- **Gate:** closed
- **Blocked by:** none
- **Revert path:** close/delete PR branch `feat/013-nav-tools`; `git revert` merge on main if needed
