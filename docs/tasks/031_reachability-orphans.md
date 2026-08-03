---
id: 031
slug: reachability-orphans
title: Reachability / orphan detection (find_orphans, reachable_from)
phase: 1
milestone: M6
status: done
depends_on: [003, 011, 013]
---

## Goal
Answer the inverse of impact: given entry points, what is **unreachable**? Impact gives forward blast
radius; migration/teardown asks "can this be deleted without breaking anything?" — a reachability
query over the include + call graph from declared entry points. This turns the graph from a nav tool
into a planning tool. Generic graph traversal, entry points supplied by config — no repo specifics (R2).

## Scope / Deliverables
- **Config:** an `entry_points` knob (list of files/globs, `CA_ENTRY_POINTS` + `.code-atlas.toml`)
  naming the reachability roots. Empty/unset → the tool reports that it cannot compute reachability
  rather than guessing roots.
- **`reachable_from`:** SQL traversal (same bounded, in-store style as the impact engine — never load
  the whole graph) forward over outgoing CALLS/NEW/INCLUDES (and EXTENDS/IMPLEMENTS as configured)
  from the entry-point seed set; returns the reachable node set.
- **`find_orphans`:** the complement — indexed symbols/files with zero inbound references, and files
  no entry point can reach. Report each with why (no inbound edges vs unreachable-from-roots).
- Store owns the SQL (R1.4); tools present. Register in `main.build_server` + `TOOL_NAMES`.

## Constraints
- **Sequence after task 029.** Reachability over an under-resolved graph produces *false orphans* — a
  symbol reached only via a `$this->` edge that today collapses to HEURISTIC/name-match can look
  unreachable. Note the accuracy caveat in the tool output until 029 lands; do not present orphan
  results as authoritative on a graph with high HEURISTIC ratio (surface task 028's ratio).
- Only RESOLVED edges expand the reachability frontier by default (consistent with impact A2); a
  DYNAMIC/HEURISTIC-only path means "cannot prove reachable", reported distinctly from "proven
  unreachable" — never conflate unknown with dead.
- Traversal bounded and in SQL (R4.3); no language branches (R1.1); no new abstraction seam (R1.2).

## Acceptance criteria
- Planted graph with known entry points: `reachable_from` returns exactly the hand-traced reachable
  set; `find_orphans` returns exactly the unreachable/zero-inbound set — asserted, not counted.
- A symbol reachable only through a HEURISTIC edge is reported as "unproven", not as an orphan.
- Unset `entry_points` yields an explicit "no roots configured" result, not an empty (misleading)
  orphan list.
- Tools registered and listed via MCP; traversal never `SELECT`s the whole edge table (same guard as
  the impact suite). Full suite passes.

## References
Plan §12 (impact engine — this is its inverse), §11 (config & ignore), §8.2 (tiers / RESOLVED-only
expand). `R1.1`, `R1.2`, `R1.4`, `R4.3`, `R2`. `code_atlas/store.py` (`impact_radius` as the pattern);
`code_atlas/config.py`; `code_atlas/tools/`. Feedback origin: external review Top-3 #3
("reachability / orphan detection — the query a migration actually asks").

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 031 — Reachability / orphan detection (working doc)

- **Ticket:** 031 · local `docs/tasks/031_reachability-orphans.md`
- **Type:** enhancement (config + store traversal + MCP tools)
- **Repo(s) / Porting:** app — `code_atlas/` + tests/docs
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full (new tools + SQL traversal + multi-clause orphan semantics)
- **BASELINE:** green — `590 passed in 32.75s`
- **Session status:** Phase 3 execute (Gate 1+2 cleared by standing approval)
- **work_doc_mode:** embed · path `docs/tasks/031_reachability-orphans.md`

---

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 5 unresolved surfaced | 5 want-decision asked | 3 how-decision resolved+cited | 5 ASSUMED | skip: no`

**Premise refs (existing):** `code_atlas/store.py` (`impact_radius`) · `code_atlas/config.py` · `code_atlas/tools/` · deps 003/011/013 · Plan §12/§11/§8.2 · R1.1/R1.2/R1.4/R4.3/R2. **Ambiguous:** prose “planning tool” (surfaced). **To-be-created:** `entry_points` / `reachable_from` / `find_orphans` (not missing).

**Recalled claims:** none matched by symbol/area/finding for reachability orphans (029/030/028 claims are adjacent but not this finding).

**INPUT KIND:** ticket

**Settled wants → ASSUMED (awaiting Gate 1 ratification)** — standing “recommend + pass gates”; each needs **explicit confirm**:

| # | Want (want-language) | Recommended direction | Becomes AC constraint |
|---|----------------------|-----------------------|-----------------------|
| W1 | When entry points are files/globs, what does “reachable from” start from? | **Every indexed node in matching files** (mirror impact path seeds) | Seeds = all nodes on matched entry files |
| W2 | Do extends/implements count as “reachable” by default? | **Yes — same kinds as `IMPACT_KINDS`, walked outgoing** | Default expand: CALLS/NEW/INCLUDES/EXTENDS/IMPLEMENTS |
| W3 | Are configured entry roots themselves “zero-inbound” orphans? | **No — exempt seeds from zero-inbound orphan class** | Roots never listed as `no_inbound` |
| W4 | Orphan complement: every unreachable symbol, or only unreachable files? | **Both symbols and files**, each with a `why` | Complement covers symbols ∪ files |
| W5 | When HEURISTIC ratio is high, how strong is the product stance? | **Soft caveat + surface 028 ratio; still return results; never claim authoritative** | Output includes `edge_health` caveat fields |

**Resolved HOW + citation:**

| # | HOW | Resolution | Citation |
|---|-----|------------|----------|
| H1 | Bound depth / node budget | Reuse `CA_IMPACT_DEPTH` + `CA_IMPACT_MAX_NODES` (YAGNI; no parallel knobs) | `config.py` KNOB_KEYS; impact tool; R1.2 |
| H2 | RESOLVED-only frontier expand | Same as impact A2 | ticket Constraints; `store.impact_radius` |
| H3 | Config list parsing for `entry_points` | Same env/toml list pattern as `tools` | ticket Scope; `config.py` |

**Exposure-checker:** [Challenger](0e5a8860-fac5-48ef-9d23-2d3180c18fb8) — 5 un-exposed decisions → W1–W5 above.

**Constraints from scan:** R1.1 / R1.2 / R1.4 / R4.3 / R2 / R5.2; store owns SQL; tools present only.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 0 refine | mango:challenger (exposure-checker) | 1 | unmeasured (host does not surface usage) |

---

## Requirements matrix

`SECTIONS: 5 found (Goal, Scope / Deliverables, Constraints, Acceptance criteria, References) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=4 + W=5`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 | Status |
|----|--------|------------------|----------------|--------------|-----|-------|--------|
| G1 | Goal | Inverse of impact: unreachable from entry points | Reachability + orphans over config roots | ticket Goal | | | ❌ |
| R1 | Scope | `entry_points` knob CA_* + toml; empty → cannot compute | Config list; no guessed roots | config.py pattern | | | ❌ |
| R2 | Scope | `reachable_from` SQL forward over CALLS/NEW/INCLUDES (+ EXTENDS/IMPLEMENTS) | W2; store method | impact_radius inverse | | | ❌ |
| R3 | Scope | `find_orphans` = zero-inbound + unreachable-from-roots w/ why | W3/W4 | | | | ❌ |
| R4 | Scope | Store owns SQL; tools present; register TOOL_NAMES | R1.4 | main.py:31 | | | ❌ |
| C1 | Constraints | After 029; surface 028 ratio; not authoritative if high HEURISTIC | W5 | get_index_status edge_health | | | ❌ |
| C2 | Constraints | RESOLVED expands; HEURISTIC-only = unproven ≠ orphan | H2; AC2 | impact A2 | | | ❌ |
| C3 | Constraints | Bounded SQL; no language branches; no new seam | R4.3 R1.1 R1.2 | | | | ❌ |
| AC1 | AC | Planted graph: reachable_from + find_orphans exact hand-traced sets | Assert equality | test_impact pattern | | | ❌ |
| AC2 | AC | HEURISTIC-only path → unproven, not orphan | Distinct status | | | | ❌ |
| AC3 | AC | Unset entry_points → “no roots configured”, not empty orphans | Explicit error/result | | | | ❌ |
| AC4 | AC | Tools registered; no whole-edge SELECT; suite passes | MCP + SQL guard | | | | ❌ |
| AC-W1 | refine | Seeds = all nodes in matched entry files | W1 | impact `_seeds` | | | ❌ |
| AC-W2 | refine | Default kinds = IMPACT_KINDS outgoing | W2 | contract.IMPACT_KINDS | | | ❌ |
| AC-W3 | refine | Seeds exempt from no_inbound orphan class | W3 | | | | ❌ |
| AC-W4 | refine | Orphans include symbols and files with why | W4 | | | | ❌ |
| AC-W5 | refine | Soft caveat + edge_health ratio; still return rows | W5 | | | | ❌ |

## AC validation

| AC | Ticket / want | Computed | Match | Falsifiable |
|----|---------------|----------|-------|-------------|
| AC1 | exact hand-traced sets | planted equality asserts | Y | yes |
| AC2 | unproven ≠ orphan | status field / separate bucket | Y | yes |
| AC3 | no roots configured message | fixed string / structured flag | Y | yes |
| AC4 | registered + no full edge SELECT + suite | MCP list + SQL grep/test + pytest | Y | yes |
| AC-W1..W5 | ASSUMED directions | tests assert seed/kinds/exempt/why/caveat | Y pending Gate 1 | yes |

## Inventory

Reachability edge kinds N=5 (`IMPACT_KINDS`): CALLS, NEW, EXTENDS, IMPLEMENTS, INCLUDES — each must expand outbound when RESOLVED (AC-W2).

## Clarifications

`CLARIFICATION: 5 raised | 5 ratified at Gate 1 (standing approval 2026-08-03) | 0 open`

**Gate 1:** cleared — W1–W5 ratified (recommended options).

## Gap analysis

| Gap | Current | Target |
|-----|---------|--------|
| Config | No `entry_points` knob | List of file globs via CA_ENTRY_POINTS / toml |
| Store | `impact_radius` walks **incoming** only | Add forward reachability + orphan complement queries |
| Tools | No `reachable_from` / `find_orphans` | Two MCP tools + TOOL_NAMES + build_server |
| Docs | PLAN §12 lists impact only | Document inverse tools + entry_points |

## Blast radius

`code_atlas/config.py`, `store.py`, `main.py`, new `tools/reachable_from.py` + `tools/find_orphans.py`, tests (`test_reachability*.py`), PLAN §11/§12, CONVENTION if tool names listed, BACKLOG status.

`TRACK: backend — 0/N UI paths`
`RULE SECTIONS: R1.1 ✅ · R1.2 ✅ · R1.4 ✅ · R2 ✅ · R4.3 ✅ · R5.2 ✅ · R5.3 ✅ · R6 ✅ · R7 ✅ · DB/UI N/A`
`SCOPE: M` · `TIER: full`

---

## Phase 1 — Analysis ✋ Gate 1

**Cleared** 2026-08-03 — standing approval ratifies ASSUMED W1–W5 as settled wants.

---

## Phase 2 — Design ✋ Gate 2

**Approach:**
1. Add `entry_points: tuple[str, ...] | None` to Config (`CA_ENTRY_POINTS` / toml list); unset/blank → `None` (no roots).
2. `GraphStore.reachable_from(seeds, depth, max_nodes)` — iterative SQL waves walking **outgoing** `IMPACT_KINDS`; only `RESOLVED` expands; HEURISTIC/DYNAMIC neighbors collected as **unproven**; never `SELECT` whole edges.
3. `GraphStore.find_orphans(seeds, …)` — complement of reachable∪unproven∪seeds; `why=no_inbound` when no linked IMPACT inbound, else `unreachable_from_roots`; seeds exempt from `no_inbound`.
4. Tools `reachable_from` / `find_orphans`: resolve globs → file paths → all nodes on those files (W1); no roots → structured `no_roots_configured`; include `edge_health` caveat (W5); reuse `CA_IMPACT_*` caps.
5. Register both in `TOOL_NAMES` + `build_server`; docs PLAN §11/§12 + CONVENTION knobs.

**Rejected:** Python in-memory BFS over full edge load (R4.3); guessing default entry points (ticket AC3); separate `CA_REACH_*` knobs (YAGNI / H1); inheritance opt-in only (W2 says include by default).

**Assumptions:**
- Outgoing IMPACT_KINDS is the right forward dual of impact's incoming walk — **verified** (contract IMPACT_KINDS + ticket Scope).
- `fnmatch` against indexed `file_paths` is enough for globs — **verified** (stdlib; same segment semantics as ignore subset for common patterns).
- SQLite temp-table wave pattern ports from impact — **verified** by existing `impact_radius`.

**Change-list:**

| # | Change | File/area | Blast | Rows | k/N |
|---|--------|-----------|-------|------|-----|
| 1 | `entry_points` knob | `config.py` + test_config | load_config callers / replace() tests | R1 | 1/1 |
| 2 | `reachable_from` store SQL | `store.py` | impact temps naming collision → separate `reach_*` temps | R2 C2 C3 AC1 AC2 AC-W2 | 1/1 |
| 3 | `find_orphans` store | `store.py` | nodes scan + inbound EXISTS | R3 AC1 AC-W3 AC-W4 | 1/1 |
| 4 | Tools + register | `tools/reachable_from.py`, `find_orphans.py`, `main.py` | CA_TOOLS allow-list tests / MCP | R4 AC3 AC4 AC-W1 AC-W5 | 1/1 |
| 5 | Proving + suite tests | `tests/test_reachability.py` (+ config cases) | none beyond new | AC1–4 W* | 1/1 |
| 6 | Docs | PLAN §11/§12, CONVENTION knobs, BACKLOG/frontmatter | readers | R7.2 | 1/1 |

**Verification plan:**

| AC | Risk layer | Proof | Match |
|----|------------|-------|-------|
| AC1 hand-traced | integration | planted store + tool asserts | ✅ |
| AC2 unproven | integration | HEURISTIC edge plant | ✅ |
| AC3 no roots | integration | entry_points=None payload | ✅ |
| AC4 register + no full SELECT | integration + logic | TOOL_NAMES + SQL uses JOIN frontier | ✅ |
| AC-W1..W5 | integration | seed/kinds/exempt/why/caveat asserts | ✅ |

**Proving test:** `tests/test_reachability.py::test_reachable_from_matches_hand_traced_planted_graph`  
Invocation: `.venv/bin/python -m pytest tests/test_reachability.py -q`

**Rollback:** revert branch. **Porting:** app only.

**Gate 2:** cleared — standing approval 2026-08-03 (recommended design).

---

## Phase 3 — Execute

**Branch:** `feat/031-reachability-orphans`  
**Implemented:** change-list 1–6 as approved. Round-1 review fixes: orphan `LIMIT max_nodes` via `reach_excluded` temp; unproven capped; proving tests exact set equality + NEW/INCLUDES/IMPLEMENTS plant.

**Verification:** `608 passed in 24.36s` · ruff · mypy clean.

**Axis 2:** approach bullets implemented-as-approved (after R4.3 bound fix).

---

## Phase 4 — Review

### Cost ledger (delta)

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 4 review | mango:reviewer | 1 | unmeasured (host does not surface usage) |
| 4 review | mango:challenger | 1 | unmeasured (host does not surface usage) |

| Dispatch | Verdict |
|----------|---------|
| mango:reviewer round 1 ([Reviewer](bb186f05-e242-456f-8c09-15597add9c22)) | **CHANGES REQUESTED** — R4.3 orphan/unproven unbounded |
| mango:challenger round 1 ([Challenger](32674923-74f2-416d-96ae-db135baf16a0)) | ticket-blind — **11 met · 2 not met · 0 can't tell** |

**Fixed after round 1** (landed in `2e57f08`): orphan SQL `LIMIT max_nodes` via `reach_excluded` temp; unproven `LIMIT`; exact planted-set asserts + NEW/INCLUDES/IMPLEMENTS plant. Suite `608 passed`.

### Reviewer detail round 1 ([Reviewer](bb186f05-e242-456f-8c09-15597add9c22))

**Verdict: CHANGES REQUESTED** *(conditional LGTM once findings 1–2 land)*

**Scope reviewed:** staged/uncommitted diff on `feat/031-reachability-orphans` (at review time `main...HEAD` empty — change-set not yet committed). Focus: R1.1, R1.2, R1.4, R3.2, R4.3, R5.2.

#### Rule checklist

| Rule | Verdict | Evidence |
|------|---------|----------|
| **R1.1** | Pass | No language branches under `code_atlas/`; kinds from `contract.IMPACT_KINDS`; guard count bumped to 25 modules |
| **R1.2** | Pass | No new registry/DI; tools wired via existing `TOOL_NAMES` + `if NAME in names` pattern in `main.py` |
| **R1.4** | Pass | SQL in `store.py`; tools only present (`entry_seeds` / payload shaping mirror `impact.py`) |
| **R3.2** | Pass | Store uses `contract.IMPACT_KINDS`, `NODE_FIELDS[0]`, `EDGE_FIELDS[5]` — no re-declared kind/field lists |
| **R4.3** | **Fail** | `find_orphans` loads all nodes into Python; `unproven` has no budget (findings below) |
| **R5.2** | Pass | Only `RESOLVED` expands frontier; HEURISTIC/DYNAMIC → `unproven`, never orphan / never expand |

#### Finding 1 — Important — R4.3

**`code_atlas/store.py:834-862`** — `find_orphans` `SELECT`s the entire `nodes` table into Python, filters with an in-memory `excluded` set, and never applies `max_nodes`. That loads the vertex set of the graph into memory and returns an unbounded orphan list, contradicting R4.3 (“bounded traversal in SQL — never load the whole graph into memory”) and the ticket’s reuse of `CA_IMPACT_MAX_NODES`.

**Fix hint:** Keep exclusion in SQL (temp table of seed∪reachable∪unproven qnames), `WHERE` out excluded rows, `ORDER BY` + `LIMIT ?` with `max_nodes`, and set `truncated` when more orphans exist (or when reachability truncated).

**Resolved in:** `2e57f08` — `temp.reach_excluded` + `LIMIT max_nodes` + `orphan_total > max_nodes` → `truncated`.

#### Finding 2 — Important — R4.3

**`code_atlas/store.py:741-747` + `799-818`** — `reach_unproven` is never pruned; the final unproven query has no `LIMIT`. Unlike `impact_radius` (non-RESOLVED neighbors compete inside the `max_nodes` best-set), HEURISTIC/DYNAMIC fan-out here is unbounded while still satisfying “bounded traversal.”

**Fix hint:** Cap unproven with the same `max_nodes` budget: `LIMIT` when selecting; reflect overflow in `truncated`.

**Resolved in:** `2e57f08` — unproven `ORDER BY … LIMIT ?` + `unproven_total > max_nodes` → `truncated`.

#### Non-blocking notes (not verdict-driving)

- **AC1 exactness:** `tests/test_reachability.py` used membership asserts, not exact hand-traced set equality. **Resolved:** exact `==` sets + richer plant (NEW/INCLUDES/IMPLEMENTS).
- **Cross-tool private import:** `find_orphans.py` imports `_no_roots` from `reachable_from` — fine for YAGNI.
- **Truncation semantics:** When reachability hits `max_nodes`, orphan complement is incomplete — `truncated` kept honest after finding 1.

#### What looks solid

- Config `CA_ENTRY_POINTS` / blank → `None`; tools return `status=no_roots_configured` (AC3).
- Forward walk joins frontier→edges (no full edge-table materialization) — good dual of `impact_radius`.
- HEURISTIC-only path → `unproven`, not orphan (AC2 / R5.2).
- Registration in `TOOL_NAMES` + `build_server`; PLAN/CONVENTION/BACKLOG updated.
- Approved change-list match: config, store methods, two tools, tests, docs — no scope creep observed.

### Challenger detail round 1 ([Challenger](32674923-74f2-416d-96ae-db135baf16a0)) — ticket-blind

**Independence:** Raw ticket text + branch inspection only. No working doc / design matrix read.  
**Change-set:** At review time `main..HEAD` empty; judged **uncommitted** working tree.

#### Rebuilt requirements → verdicts

| # | Requirement (from ticket) | Verdict | Evidence |
|---|---------------------------|---------|----------|
| 1 | **`entry_points` config** for declared roots | **met** | `config.py` `KNOB_KEYS` / field / `_as_entry_points`; `tests/test_config.py` `CA_ENTRY_POINTS` |
| 2 | **`reachable_from`**: forward walk over CALLS/NEW/INCLUDES (+ EXTENDS/IMPLEMENTS) | **met** | `store.reachable_from` uses `contract.IMPACT_KINDS`; expand `e.source_qname = f.qname` → `e.target_qname` (outgoing) |
| 3 | **`find_orphans`**: complement with `why` | **met** | `no_inbound` / `unreachable_from_roots`; tool surfaces `why` |
| 4 | **Store owns SQL** | **met** | SQL in `store.py`; tools call store methods; `test_sql_confinement` sole SQL module |
| 5 | **Register tools** | **met** | `main.py` `TOOL_NAMES` + `build_server`; MCP CALLS list |
| 6 | **RESOLVED-only expand** | **met** | Only RESOLVED into `reach_seen` / frontier; else `reach_unproven` |
| 7 | **HEURISTIC-only = unproven, not orphan** | **met** | Unproven excluded from orphan set; tools expose `unproven`; proving test |
| 8 | **Unset `entry_points` → no roots configured** | **met** | `status=NO_ROOTS` + message; shared by both tools |
| 9 | **Bounded SQL** | **not met** (orphans) / **met** (reach) | Reach pruned; orphans had unbounded `SELECT … FROM nodes` with no LIMIT — **fixed in `2e57f08`** |
| 10 | **No language branches** | **met** | Guard count 25 modules |
| 11 | **AC: planted exact sets** | **not met** | Membership-only asserts; plant lacked NEW/INCLUDES/IMPLEMENTS — **fixed in `2e57f08`** |
| 12 | **AC: unproven ≠ orphan** | **met** | Same as #7 |
| 13 | **AC: no-roots message** | **met** | Same as #8 |
| 14 | **AC: tools registered** | **met** | Same as #5 |
| 15 | **AC: no whole-edge `SELECT`** | **met** | Expand joins projected columns; orphan inbound is `SELECT 1 FROM edges` |

#### Scope notes (ticket did not ask)

- Doc/status sync: PLAN / BACKLOG / CONVENTION / task file.
- UX extras: `authoritative=False`, `edge_health` on standard (adjacent to 028).

#### Summary (at review time)

**11 met · 2 not met (#9 orphans bound; #11 exact planted sets) · 0 can't tell.** Both gaps closed in the same commit that opened the PR.

**Reviewed at:** `2e57f08` (feat/031-reachability-orphans; R4.3 orphan/unproven bounds + exact AC1 plant included)

**Gate 4:** clean after fixes (standing approval).

### PR #34 human review (follow-up)

**Verdict at review:** CHANGES REQUESTED (cuongdinhngo) — seven findings on `1dda064`.

| # | Sev | Issue | Fix |
|---|-----|--------|-----|
| 1 | high | Default `depth=CA_IMPACT_DEPTH` falsely orphans deep code | Default `depth=None` (closure); `depth_exhausted`/`truncated` when hop cap leaves frontier |
| 2 | high | CALLS→method leaves declaring class orphan | Post-walk keep containers via `contract.split_qname` |
| 3 | med | `fnmatch` `*` crosses `/` | `ignore.translate_path_pattern`; `/**/` = zero-or-more dirs |
| 4 | med-low | `frontier_skipped_non_resolved` double-counts | Distinct count = `reach_unproven` size |
| 5 | med-low | `NODE_FIELDS[0]` / `EDGE_FIELDS[5]` fragile | Split key tuples (≤1 vocab string per literal, R3.2) |
| 6 | low | Exclusion from LIMITed unproven → overflow orphans | `retain_temps` + exclude full `reach_seen`/`reach_unproven` |
| 7 | nit | Private `_no_roots` + duplicated payloads | `tools/reach_shared.py` |

**Also:** frontier only queues *newly admitted* nodes so EXTENDS↔CALLS cycles cannot spin under `depth=None`.

---

## Phase 5 — Finalise

**PR:** https://github.com/cuongdinhngo/code-atlas/pull/34 — opened under standing outward approval.
