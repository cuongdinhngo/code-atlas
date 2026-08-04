---
id: 033
slug: nav-reason-codes
title: Reason codes + total_count on find_* / search (empty ≠ unknown)
phase: 1.5
milestone: Agent-trust
status: done
depends_on: [013, 014]
---

## Goal
Stop an empty result from reading as proof. To an LLM consumer, a bare `[]` from `find_callers`
means "nothing exists" — so it will confidently report a function is dead when the real cause was a
missing symbol, an unbuilt index, or a truncated list. Every `find_*`/`search` response must carry a
machine-readable reason so the agent can tell **"no"** from **"I don't know"** (§19 agent-first pivot).

## Scope / Deliverables
- Add a `reason` enum to `find_callers` / `find_references` / `find_implementations` / `search_symbol`
  responses covering at least: `ok` (matches returned), `no_matches` (symbol exists, zero relations),
  `no_such_symbol` (qname not in `nodes`), `not_indexed` (no DB), `index_stale` (queried file drifted).
- Add `total_count` alongside the existing `truncated` bool so a clipped list says how many existed.
- Generalise the instinct already in `get_index_status.next_tool_suggestions`
  (`code_atlas/tools/get_index_status.py:114`) and the status enum in
  `code_atlas/tools/reach_shared.py` — reuse that vocabulary, don't invent a parallel one.

## Constraints
- The reason must distinguish **not-found** (qname absent from `nodes`) from **empty** (qname present,
  zero inbound/outbound of the asked relation) — these are different answers for an agent.
- No language branches (R1.1); store owns SQL (R1.4); read-only, deterministic (R4).
- `nav_result` / `empty_nav` shaping stays in one place (`code_atlas/tools/nav_result.py:54-79`);
  extend it, don't fork per tool.

## Acceptance criteria
- Querying a non-existent qname returns `reason=no_such_symbol` (not `no_matches`, not a bare empty).
- A symbol with zero callers returns `reason=no_matches` with an empty `results` list.
- Truncation sets `truncated=true` **and** `total_count > limit`; a full result sets `total_count`
  equal to the returned length.
- An unbuilt index returns `reason=not_indexed`. All asserted on planted fixtures; full suite passes.

## References
`code_atlas/tools/nav_result.py:60-79` (current `{indexed, results, truncated}` shape);
`code_atlas/tools/read_symbol.py:38-61` (already distinguishes found / stale — mirror it);
`code_atlas/tools/reach_shared.py` (status enum); `get_index_status.py:114`. PLAN §8.2 (tiers), §12.
Feedback origin: [`FEEDBACK.md`](../FEEDBACK.md) round 3 ("empty ≠ unknown — the highest-leverage
safety property you don't have").

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 033 — Reason codes + total_count on find_* / search (working doc)

- **Ticket:** 033 · local `docs/tasks/033_nav-reason-codes.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `646 passed in 24.81s` (`.venv/bin/pytest -q --tb=line`)
  <!-- baseline exclusions (pre-existing failures outside this change): none -->

---

## Phase 0 — Refine

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by area | 0 by finding | 0 retired skipped — advisory`
`REFINE: 1 unresolved surfaced | 1 want-decision asked | 5 how-decision resolved+cited | 1 ASSUMED | skip: no`

**INPUT KIND:** ticket (single deliverable — reason + total_count on four named tools).

**Settled wants (want-decision — from the user; become AC constraints).**

| # | The want (in want-language) | Chosen direction (NOT a tool) | Becomes AC constraint |
|---|-----------------------------|-------------------------------|-----------------------|
| 1 | When a file drifted since last index, should *this* card already say "index out of date," or only fix empty≠unknown and leave stale to the freshness card? | **Vocabulary only** — enum includes `index_stale`; emission/proof deferred to 035 | W1+W2 below |

**Resolved direction + citation (how-decision).**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Response field name | Use `reason` (not rename reach `status`) | ticket Scope L18; AC L34–38 |
| 2 | Tool set in scope | Exactly four: `find_callers`, `find_references`, `find_implementations`, `search_symbol` | ticket Scope L18 |
| 3 | `search_symbol` vs `no_such_symbol` | Search has no qname lookup; emits `ok`/`no_matches`/`not_indexed` only | `search_symbol.py:19–24` (query, not qname); ticket `no_such_symbol` = "qname not in nodes" |
| 4 | Keep `indexed` bool | Additive `reason` + `total_count`; do not remove `indexed` | current `nav_result.py:70–75`; FEEDBACK "PARTIAL" gap is missing reason, not indexed |
| 5 | FEEDBACK `filtered_by_tier` | Out of scope — not in ticket enum | ticket Scope L19–20 vs FEEDBACK.md:30 |

**ASSUMED (awaiting ratification) — standing approval 2026-08-04 ("suggest and do the best option, and pass all gates").**

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses prior? |
|---|----------------|-------------|--------------------------|-----------------|
| 1 | Option 1: `index_stale` vocabulary-only in 033; emit/prove in 035 | Handed back as recommended / pass all gates | Gate 1 — standing approval ratifies when concrete | no |

**Want clauses (split at Gate 1 — one row each):**
- **W1:** `reason` vocabulary includes named member `index_stale` (even if unused this card).
- **W2:** No fixture proof that any in-scope tool *emits* `index_stale` this card (035 owns emission).

**Constraints surfaced from the scan:**
- R1.1 / R1.4 / R4 (ticket + ENGINEERING_RULES §1, §4)
- Shaping only via `nav_result` / `empty_nav` (ticket Constraint; `nav_result.py:45–79`)
- `find_callers` truncation today is `len >= limit` (`find_callers.py:90`) — exact-fill honesty must align with `total_count` (cf. `test_include_graph_exact_fill…`)
- 035 depends on 033 vocabulary for stale reason on reparse-cap overflow

**Exposure-checker:** none — exposure complete (dispatch `c5cb9610-48c3-409b-b042-3fe08f1d7b15`).

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope/Deliverables, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=3 R=3 G=1 AC=4 + W=2`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Every find_*/search response must carry a machine-readable reason so the agent can tell no from I don't know" | Four in-scope tools always return a `reason` string from the shared vocabulary | ticket L11–15; bare `[]` today in `nav_result.py:70–75` | | | ❌ |
| R1 | Scope | "Add a reason enum to find_callers / find_references / find_implementations / search_symbol covering at least: ok, no_matches, no_such_symbol, not_indexed, index_stale" | Shared constants + every response carries `reason`; `index_stale` member exists (W1); emission of stale deferred (W2) | ticket L18–20; `reach_shared.NO_ROOTS` precedent | | | ❌ |
| R2 | Scope | "Add total_count alongside the existing truncated bool so a clipped list says how many existed" | Every shaped nav/search payload includes `total_count`; when truncated, `total_count > limit` | ticket L21; FEEDBACK.md:62–63 | | | ❌ |
| R3 | Scope | "Generalise the instinct already in get_index_status.next_tool_suggestions and the status enum in reach_shared — reuse that vocabulary, don't invent a parallel one" | Machine-readable code field on every response; values aligned with existing status instinct; field name `reason` per ticket | `get_index_status.py:107–114`; `reach_shared.py:14,41–48` | | | ❌ |
| C1 | Constraints | "distinguish not-found (qname absent from nodes) from empty (qname present, zero relations)" | find_* looks up node existence before classifying empty | ticket L27–28; `read_symbol.py:37–45` pattern | | | ❌ |
| C2 | Constraints | "No language branches (R1.1); store owns SQL (R1.4); read-only, deterministic (R4)" | No lang ifs; any new COUNT in store; tools present only | ENGINEERING_RULES R1.1/R1.4/R4 | | | ❌ |
| C3 | Constraints | "nav_result / empty_nav shaping stays in one place; extend it, don't fork per tool" | `reason` + `total_count` added in `nav_result.py` helpers; tools call them | `nav_result.py:45–79` | | | ❌ |
| AC1 | AC | "non-existent qname → reason=no_such_symbol" | Planted graph; unknown qname; assert reason | ticket L34 | | | ❌ |
| AC2 | AC | "symbol with zero callers → reason=no_matches + empty results" | Node present, no CALLS/NEW inbound; assert | ticket L35 | | | ❌ |
| AC3 | AC | "truncated=true and total_count > limit; full → total_count == returned length" | Cap results; assert both truncated and full cases | ticket L36–37 | | | ❌ |
| AC4 | AC | "unbuilt index → reason=not_indexed; planted fixtures; full suite passes" | No DB file; reason + no DB created; suite green vs baseline | ticket L38; `test_missing_database…` | | | ❌ |
| W1 | refine WANT | enum includes `index_stale` member | Named constant / Literal includes `index_stale` | Phase 0 ASSUMED #1 | | | ❌ |
| W2 | refine WANT | no emit-proof of `index_stale` this card | No test requiring emission; 035 owns | Phase 0 ASSUMED #1 | | | ❌ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 Q |
|-------|---------------|------------------------|--------|--------------|----------|
| AC1 | reason=no_such_symbol | same string; requires node miss path | Y | measurable (assert equality) | — |
| AC2 | reason=no_matches + empty results | same | Y | measurable | — |
| AC3 | truncated⇒total_count>limit; else total_count==len(results) | same inequalities | Y | measurable | — |
| AC4 | reason=not_indexed + suite | same; suite = pytest green vs BASELINE | Y | measurable | — |

## Inventory (universal)

- **Tools denominator N=4:** (1) `find_callers` (2) `find_references` (3) `find_implementations` (4) `search_symbol`
- **Reason vocabulary N=5 members:** ok, no_matches, no_such_symbol, not_indexed, index_stale (W1: all named; W2: stale unused)
- Per-tool checklist for R1/R2/G1 — review must confirm **each** of the 4, not an aggregate k/N only.

`TRACK: backend — 0/N touched files under UI paths`

`RULE SECTIONS: §1 (arch), §4 (determinism), §6 (testing), §7 (change discipline) — check at design; §2 N/A (no adapter); §3 N/A (no contract vocab bump — tool response shape not contract JSONL); §5 N/A (no new error class); §8 N/A (no deps)`

`CLARIFICATION: 1 raised | 1 self-resolved via standing approval (ASSUMED #1 → Option 1) | j=0 for human decision at Gate 0`

`SCOPE: M` — four tools + shared shaper + tests; not a single-line fix.
`TIER: full` — SCOPE=M and universal tool inventory N=4 > 1.

### Gap analysis (enhancement)

| Goal | Current | Target | path:line |
|------|---------|--------|-----------|
| Empty ≠ unknown | `{indexed, results, truncated}` only; missing qname ≡ zero callers | + `reason` + `total_count` | `nav_result.py:45–79`; `find_callers.py:41–54` |
| Node miss vs empty | No node existence check on find_* | Check `nodes_by_qualified_name` before edge walk | `read_symbol.py:37–45` mirror |
| Truncation honesty | `find_callers` uses `len>=limit` (exact-fill false positive); refs/impls use limit+1 | `truncated ≡ total_count > len(results)` | `find_callers.py:90`; `find_references.py:31–33` |
| search_symbol | Own `_empty`/`_result` fork | Route through extended nav helpers or shared reason/total fields | `search_symbol.py:59–80` |

### Blast radius

- Entry: `nav_result.empty_nav` / `nav_result.nav_result`; four tool `create` closures; `search_symbol` local shapers
- Consumers: MCP clients; tests asserting exact dict equality (`test_nav_tools.py:236`); `test_mcp_server`, `test_search_read_outline`, `test_alias_indirection`, reach tools via `nav_result` (must stay compatible — additive keys)
- Store: possible `count_edges_by_target` for exact totals (R1.4)
- Out of scope: `reachable_from` / `find_orphans` / `impact` / `read_symbol` (already has found/stale)

### Gate 1 — standing approval

**ASSUMED #1 ratification (explicit):** Option 1 — `index_stale` in vocabulary only; no emission proof in 033 (035 pairs).

**Gate 1 status:** cleared — human standing approval 2026-08-04 ("suggest and do the best option, and pass all gates"); j=0.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| Phase 0 | exposure-checker (challenger) | 1 | unmeasured (blocking retrieval) |

---

## Phase 2 — Design

### Approach
1. Extend `nav_result.empty_nav` / `nav_result` to always emit `reason` + `total_count` (defaults so out-of-scope callers stay source-compatible: `not_indexed`/0 and `ok`/len(results)).
2. Define shared vocabulary constants in `nav_result.py`: `ok`, `no_matches`, `no_such_symbol`, `not_indexed`, `index_stale` (W1; unused this card — W2).
3. In-scope find_*: no DB → `not_indexed`; else node miss → `no_such_symbol`; else empty relations → `no_matches`; else `ok`. Compute `total_count` honestly; `truncated ≡ total_count > len(results)`.
4. `search_symbol`: no DB → `not_indexed`; empty hits → `no_matches`; else `ok` (never `no_such_symbol`). Route shaping through shared helpers (no private fork for reason/count).
5. Store owns exact counts: `count_edges_by_target` for refs/impls; find_callers BFS counts past the result cap; `count_search_nodes` when search truncates.
6. Proving tests on planted fixtures for AC1–4; update exact-dict collateral in `test_nav_tools`.

### Rejected alternatives
- **Per-tool ad-hoc reason fields** — rejected: ticket C3 + R1.4 demand one shaper.
- **Emit `index_stale` via read_symbol-style hash check now** — rejected: ASSUMED Option 1 / PLAN §19 / 035 owns freshness emission.
- **`total_count = limit+1` lower-bound only** — rejected: ticket wants how many existed; exact COUNT/BFS count is small and honest.
- **Rename reach `status` → `reason`** — rejected: out of scope; field name `reason` is ticket-specified for find_*/search.

### Assumptions
| Assumption | Tag |
|------------|-----|
| Additive `reason`/`total_count` keys do not break MCP clients (extra JSON keys) | verified (existing tools already grow payloads; CONVENTION subset rule for minimal) |
| `nodes_by_qualified_name` is the right existence check for find_* | verified (`read_symbol.py:37–45`) |
| Exact edge/search COUNTs are cheap vs result shaping | verified (single indexed SQL COUNT; same predicates as list queries) |
| Out-of-scope tools accepting default reason/total_count is acceptable | verified (ticket scope names four tools only) |

### Smallest change-list

| # | Change | File/area | Ph2 covered by | k/N |
|---|--------|-----------|----------------|-----|
| 1 | Reason constants + `reason`/`total_count` on `empty_nav`/`nav_result` (+ optional subject-less list helper for search) | `code_atlas/tools/nav_result.py` | G1,R1,R2,R3,C3,W1 | 6/6 |
| 2 | `count_edges_by_target` (+ kinds) | `code_atlas/store.py` | R2,C2,AC3 | 3/3 |
| 3 | `count_search_nodes` mirroring search filters | `code_atlas/store.py` | R2,AC3,C2 | 3/3 |
| 4 | Wire find_callers: existence check, BFS total_count, reasons | `code_atlas/tools/find_callers.py` | G1,R1,R2,C1,AC1–4 | 7/7 |
| 5 | Wire find_references | `code_atlas/tools/find_references.py` | G1,R1,R2,C1,AC1,AC3,AC4 | 6/6 |
| 6 | Wire find_implementations | `code_atlas/tools/find_implementations.py` | G1,R1,R2,C1,AC1,AC3,AC4 | 6/6 |
| 7 | Wire search_symbol via shared shaper | `code_atlas/tools/search_symbol.py` | G1,R1,R2,AC3,AC4 | 5/5 |
| 8 | Proving tests AC1–4 + per-tool inventory smoke | `tests/test_nav_reason_codes.py` (new) | AC1–4,W1,W2, inventory N=4 | 8/8 |
| 9 | Update exact missing-DB dict + truncation assertions | `tests/test_nav_tools.py` | AC4,R2 proof collateral | 2/2 |
| 10 | Store unit tests for new COUNT helpers | `tests/test_store.py` | C2,R2 | 2/2 |
| 11 | Docs: BACKLOG + task frontmatter status; PLAN §12/§19 touch if shape documented | `docs/BACKLOG.md`, task frontmatter, `docs/PLAN.md` as needed | R7.2 | 1/1 |

**Proof collateral (blast):** exact equality `test_nav_tools.py:236`; truncation test `:258–268`; any MCP assertions on nav keys (additive — expect pass). Reach/impact/include_graph call sites unchanged (defaults).

### Rule compliance
`RULE SECTIONS: §1 ✅ (no lang branch; store SQL; tools present) · §2 N/A · §3 N/A (MCP response shape ≠ contract JSONL version) · §4 ✅ (deterministic counts) · §5 N/A · §6 ✅ (fixture tests) · §7 ✅ (smallest; docs) · §8 N/A`

### Verification plan

| AC | Risk layer | Proof artifact | Layer-match? |
|----|------------|----------------|--------------|
| AC1 | integration | planted store + find_* tool | ✅ |
| AC2 | integration | planted node, zero callers | ✅ |
| AC3 | integration | max_results cap + total_count | ✅ |
| AC4 | integration | missing DB + suite | ✅ |
| W1 | logic | constants/Literal includes index_stale | ✅ |
| W2 | logic | no test asserts emission of index_stale | ✅ |

### Named proving test
`tests/test_nav_reason_codes.py::test_find_callers_distinguishes_no_such_symbol_from_no_matches`

Fails today: both paths return empty results with no `reason` key.

Invocation: `.venv/bin/pytest tests/test_nav_reason_codes.py -q`

### Gate 2 status
cleared — standing approval 2026-08-04 (best option / pass all gates); approach = shared nav_result vocabulary + store COUNTs + four tool wires; index_stale vocabulary-only.

---

## Phase 3 — Execute

- **Branch:** `feat/033-nav-reason-codes`
- **Proving test:** `tests/test_nav_reason_codes.py::test_find_callers_distinguishes_no_such_symbol_from_no_matches` — PASS
- **Suite:** `655 passed in 34.37s` (baseline 646; +9 net from new tests)
- **ruff/mypy:** clean on change-set

### Design-conformance (Approach bullets)

| # | Bullet | Status |
|---|--------|--------|
| 1 | Extend empty_nav/nav_result with reason+total_count (defaults) | implemented-as-approved |
| 2 | Shared vocabulary constants incl. index_stale | implemented-as-approved |
| 3 | find_* classify miss/empty/ok; truncated≡total>len | implemented-as-approved |
| 4 | search_symbol via list_result; no no_such_symbol | implemented-as-approved |
| 5 | Store COUNTs + BFS total_count | implemented-as-approved |
| 6 | Proving tests + collateral dict update | implemented-as-approved |

### Verification sweep
- **Axis 1 (file set):** diff ⊆ approved list (nav_result, store, 4 tools, 3 test files, PLAN, BACKLOG, task) ✅
- **Axis 2 (behaviour):** all approach bullets implemented-as-approved; 0 deviations ✅
- **Deviations:** none

### Ph3/4 proven by (matrix delta)
AC1–AC4, W1–W2, G1, R1–R3, C1–C3 → proving + inventory tests / suite ✅

---

## Phase 4 — Review

### Reviewer (`mango:reviewer` · 8668a1b1)
- **Verdict:** **LGTM**
- **Scope:** diff ⊆ Gate-2 list (12 files); R1.1 / R1.4 / R4 / R6 / R7.2 OK; `index_stale` vocabulary-only
- **Proof:** blast-radius pytest 106 passed; suite claim 655 vs baseline 646
- **Findings:** none Critical/Important
- **Nit (R7.4):** unused `NavReason` + `relation_reason` in `nav_result.py` — **fixed post-LGTM** (deleted; constants/`NAV_REASONS` retained)

### Challenger (ticket-blind · 7cf518c3)

| # | Rebuilt requirement | Verdict | Adjudication |
|---|---------------------|---------|--------------|
| 1a | reason vocab includes ok/no_matches/no_such_symbol/not_indexed/index_stale | **met** | — |
| 1b | emit `index_stale` on drift | **not met** (as written) | **ratified W2 / ASSUMED Option 1** — emission deferred to 035; not a Gate-4 miss |
| 2 | total_count alongside truncated | **met** | — |
| 3 | reuse get_index_status/reach_shared status strings | **not met** (challenger) | **adjudicated met** — ticket specifies `reason` values; "generalise the *instinct*" ≠ share `behind`/`current` commit-staleness strings; reach keeps `status` for no_roots |
| 4 | distinguish absent vs empty | **met** | — |
| 5 | R1.1/R1.4/R4; one shaper | **met** | — |
| 6a–6d | ACs no_such_symbol / no_matches / total_count / not_indexed | **met** | — |
| 6e | full suite | **can't tell** (challenger) | **resolved** — execute recorded `655 passed` |

### Scope reconciliation
- File axis: ✅ approved list only (+ post-LGTM deletion inside `nav_result.py` item 1)
- Behaviour axis: ✅ Approach bullets as approved; W2 holds
- Inventory N=4 tools: each has reason+total_count ✅

### Gate 4 status
**clean** — reviewer LGTM; challenger gaps adjudicated against ratified Option 1 / ticket field name.

### Cost ledger (dispatch)

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| Phase 0 | exposure-checker (challenger) | 1 | unmeasured (blocking retrieval) |
| Phase 4 | reviewer | 1 | unmeasured (blocking retrieval) |
| Phase 4 | challenger | 1 | unmeasured (blocking retrieval) |

`LEDGER: 3 dispatch rows | all cells valued or marked unmeasured | complete`

### Durable lesson
Ticket Scope enum members that 035 will emit must be listed in 033 without AC proof — record as W1/W2 (vocab vs emit) at refine so ticket-blind challenger "not met" on emission is expected, not a surprise rework.

## Phase 5 — Finalise
- Status → done; BACKLOG + token row; lesson in LESSONS.md
- Outward: push branch + open PR (user-approved 2026-08-04)

## Decision log

| Phase | Decision | Note |
|-------|----------|------|
| Phase 0 | Option 1 index_stale vocabulary-only | standing approval / recommended |
| Gate 1/2 | cleared | standing approval pass-all-gates |
| Gate 4 | challenger emit-stale + parallel-vocab | adjudicated via W2 + ticket `reason` field |
| Gate 5 | push + PR | explicit user request |

## Session status

- **Ticket:** 033
- **work_doc_mode:** embed
- **working-doc path:** `docs/tasks/033_nav-reason-codes.md`
- **Current phase:** finalise — complete (PR #40)
- **Blocked on:** none
- **Reviewed at:** `ff55feff067b8b09b58841b73b6733ff2879b20c` · reviewed files: nav_result, store, find_callers, find_references, find_implementations, search_symbol, test_nav_reason_codes, test_nav_tools, test_store, PLAN, BACKLOG, LESSONS, task doc
- **PR:** https://github.com/cuongdinhngo/code-atlas/pull/40
- **Next action:** none (await merge)
