---
id: 035
slug: read-through-freshness
title: Read-through freshness — inline reparse on hash drift
phase: 1.5
milestone: Freshness
status: done
depends_on: [009, 011]
---

## Goal
Make liveness a property of the answer, not a chore the user remembers. Today a tool answers from the
last build; only `read_symbol` detects staleness, and it returns `stale: true` with empty source and
punts to a rebuild rather than fixing it. For an AI consumer that will not rebuild on its own, this is
correctness: when a tool is about to return rows touching file X, compare X's current hash to the
stored `files.hash`, and if it drifted, reparse **just X** through the adapter inline before
answering. One adapter call, milliseconds, no daemon, no determinism violation (§19 agent-first pivot).

## Scope / Deliverables
- A query-time staleness check shared across the read/nav tools: hash the on-disk file, compare to
  `store.file_hash(rel)`, and on mismatch reparse that single file through the adapter and update its
  rows before shaping the response.
- Promote `read_symbol`'s existing check (`code_atlas/tools/read_symbol.py:50-61`) from
  "report stale" to "repair inline" using the same mechanism.
- A bound: cap the number of files reparsed per call; beyond it, fall back to the stale signal + a
  reason code (pairs with task 033).

## Constraints
- **Determinism preserved** — inline reparse uses the same adapter/store path as the full build, so
  the repaired rows are identical to what a rebuild would produce (R4). Add a test proving equality.
- No language branches (R1.1); adapter parses, store persists, never the reverse (R1.4).
- Single-file scope only — a read never triggers a full rebuild; never load the whole graph.

## Acceptance criteria
- Edit a file on disk after indexing; a nav/read query touching it returns rows reflecting the new
  content **without** an explicit rebuild.
- A query not touching the edited file performs no reparse (asserted — no adapter call).
- Determinism: the inline-reparsed rows for a file equal the rows a full build produces for it.
- The per-call reparse cap is enforced; overflow yields a stale reason code, not an unbounded stall.

## References
`code_atlas/tools/read_symbol.py:50-61` (existing staleness check to generalise);
`code_atlas/indexer.py:141-144` (incremental reparse-on-hash-mismatch — the path to reuse);
`code_atlas/store.py` (`file_hash`). PLAN §5 (incremental), §19. Feedback origin:
[`FEEDBACK.md`](../FEEDBACK.md) rounds 1 & 3 ("freshness has to be enforced, not surfaced").


<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 035 — Read-through freshness (working doc)

- **Ticket:** 035 · local `docs/tasks/035_read-through-freshness.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `657 passed in 24.90s` (`.venv/bin/pytest -q --tb=line`)
  <!-- baseline exclusions: none -->

---

## Phase 0 — Refine

`REFINE: 2 unresolved surfaced | 2 want-decision asked | 4 how-decision resolved+cited | 2 ASSUMED | skip: no`

**INPUT KIND:** ticket (single deliverable).

**Settled wants (ASSUMED — standing approval 2026-08-04 "best option / pass-all-gates").**

| # | Want | Chosen | AC constraint |
|---|------|--------|---------------|
| 1 | Reparse cap size | **Cap = 1** per tool call | W1 |
| 2 | Which tools | **read_symbol, search_symbol, file_outline, find_callers, find_references, find_implementations** | W2 (inventory N=6) |

**HOW (cited).**

| # | HOW | Resolution | Citation |
|---|-----|------------|----------|
| 1 | Overflow signal | Emit `reason=index_stale` (033 vocab); `read_symbol` also `stale: true` | `nav_result.REASON_INDEX_STALE`; ticket Scope L25–26; LESSONS 033 |
| 2 | Repair mechanism | Reuse indexer single-file write path + `resolve_edges` | `indexer.py:141–144`, `_write` `:394–404` |
| 3 | Shared helper | One freshness guard module; tools call `ensure(path)` | ticket Scope L20–22; R1.4 |
| 4 | Cap knob | Hardcode `1` this card (YAGNI — no `CA_*` until a second value is needed) | R7.1; WANT-1 |

**Exposure-checker:** none — exposure complete (dispatch `99175a23-2ae2-4a11-9612-d100feaaccfe`)

**Constraints from scan:** R1.1/R1.4/R4; fake_adapter proofs in `tests/test_incremental.py` / `fake_adapter.py`.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope, Constraints, AC) | 4 decomposed | ROWS: C=3 R=3 G=1 AC=4 W=2`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 | Status |
|----|--------|------------------|----------------|--------------|-----|-------|--------|
| G1 | Goal | liveness via inline reparse on hash drift | Tools repair drifted files before answering | ticket L11–17; read_symbol stale path today | | | ✅ |
| R1 | Scope | shared query-time check + single-file reparse + store update | Shared guard + indexer.reparse_file | ticket L20–22 | | | ✅ |
| R2 | Scope | promote read_symbol from report-stale to repair | read_symbol uses same ensure | `read_symbol.py:50–61` | | | ✅ |
| R3 | Scope | cap + overflow → stale + reason (033) | Cap=1; overflow → index_stale | ticket L25–26; 033 | | | ✅ |
| C1 | Constraints | determinism = full-build rows for that file | Prove equality vs full_build snapshot | ticket L29–30; R4 | | | ✅ |
| C2 | Constraints | R1.1 / R1.4 | No lang if; adapter parse / store persist | ENGINEERING_RULES | | | ✅ |
| C3 | Constraints | single-file only | reparse_file never full rebuild | ticket L32 | | | ✅ |
| AC1 | AC | edit then query → new content w/o rebuild | Fixture edit + tool call | ticket L35–36 | | | ✅ |
| AC2 | AC | untouched file → no adapter call | Spy/counter on adapter | ticket L37 | | | ✅ |
| AC3 | AC | reparsed rows == full build rows | Snapshot equality | ticket L38 | | | ✅ |
| AC4 | AC | cap overflow → stale reason | Second drifted file → index_stale | ticket L39 | | | ✅ |
| W1 | refine | cap = 1 | Hardcoded | Phase 0 | | | ✅ |
| W2 | refine | six tools | Inventory checklist | Phase 0 | | | ✅ |

## AC validation

| AC | Ticket | Computed | Match | Falsifiable |
|----|--------|----------|-------|-------------|
| AC1 | new content without rebuild | same | Y | measurable |
| AC2 | no adapter on untouched | same | Y | measurable (call counter) |
| AC3 | rows == full build | same | Y | measurable snapshot |
| AC4 | overflow → stale reason | `reason=index_stale` | Y | measurable |

## Inventory
`TOOLS N=6:` (1) read_symbol (2) search_symbol (3) file_outline (4) find_callers (5) find_references (6) find_implementations

`TRACK: backend`
`RULE SECTIONS: §1 ✅ · §2 N/A · §3 N/A · §4 ✅ · §5 soft-fail on parse N/A-ish · §6 ✅ · §7 ✅ · §8 N/A`
`CLARIFICATION: 2 raised | 2 ASSUMED via standing | j=0 at Gate 0`
`SCOPE: M` · `TIER: full` (N=6 tools)

### Gap
| Current | Target | path |
|---------|--------|------|
| read_symbol returns stale:true | repair then read | `read_symbol.py:50–61` |
| find_*/search/outline no hash check | ensure primary paths | nav/search/outline tools |
| index_stale unused | emit on cap overflow | `nav_result.py:25` |

### Blast radius
Entry: new freshness helper + `indexer.reparse_file`; six tool modules; tests; PLAN/BACKLOG.
Out of scope: impact, include_graph, reach, 036 hook.

### Gate 1
**ASSUMED W1/W2 ratified** by standing approval. **cleared**.

---

## Phase 2 — Design

### Approach
1. Add `indexer.reparse_file(config, store, rel) -> None` — announce matching adapter, parse one path, `_write`, then `resolve_edges` (same write path as build).
2. Add `code_atlas/tools/freshness.py`: `FreshnessGuard(config, store, cap=1)` with `ensure(rel) -> "ok"|"repaired"|"stale"` using `_hash_matches` / digest.
3. Wire six tools: create one guard per call; ensure primary path(s); on `"stale"` set `reason=index_stale` (find_*/search) or `stale=True`+reason (read_symbol); re-query store after repair before shaping.
4. Primary paths: subject file for read/find_*; outline path; for search — each distinct hit file in order until cap, then stale if more drifted.
5. Proving tests with fake_adapter + disk edit.

### Rejected
- Cap as CA_* knob now — YAGNI until a second value.
- Reparse all result files unbounded — violates AC4/cap.
- Surfacing-only stale without repair — contradicts Goal/FEEDBACK.

### Assumptions
| A | Tag |
|---|-----|
| Single-file reparse + resolve_edges matches full_build file rows | novel-untested → Gate-2 proving test AC3 |
| Cap=1 sufficient for agent UX | verified (WANT-1 / Goal "one adapter call") |
| Fake adapter supports hermetic proofs | verified (`tests/test_incremental.py`) |

### Change-list

| # | Change | File | Covers | k/N |
|---|--------|------|--------|-----|
| 1 | `reparse_file` | `code_atlas/indexer.py` | R1,C1,C2,C3,AC3 | 5/5 |
| 2 | `FreshnessGuard` | `code_atlas/tools/freshness.py` (new) | R1,R3,W1,AC2,AC4 | 5/5 |
| 3 | Wire read_symbol | `read_symbol.py` | G1,R2,AC1 | 3/3 |
| 4 | Wire find_callers | `find_callers.py` | W2,AC1,AC4 | 3/3 |
| 5 | Wire find_references | `find_references.py` | W2 | 1/1 |
| 6 | Wire find_implementations | `find_implementations.py` | W2 | 1/1 |
| 7 | Wire search_symbol | `search_symbol.py` | W2,AC4 | 2/2 |
| 8 | Wire file_outline | `file_outline.py` | W2 | 1/1 |
| 9 | Proving + tool tests | `tests/test_read_through_freshness.py` (new) | AC1–4,C1,W1–2 | 8/8 |
| 10 | Docs BACKLOG/PLAN/task | docs | R7.2 | 1/1 |
| 11 | Core-module count guards | `tests/test_core_is_language_agnostic.py`, `tests/test_sql_confinement.py` | R1.1 companion (26→27) | 1/1 |

### Verification plan
| AC | Layer | Proof | Match |
|----|-------|-------|-------|
| AC1 | integration | edit + tool | ✅ |
| AC2 | integration | adapter call counter | ✅ |
| AC3 | integration | snapshot vs full_build | ✅ |
| AC4 | integration | two drifted files, cap=1 | ✅ |

### Named proving test
`tests/test_read_through_freshness.py::test_read_symbol_repairs_drifted_file_inline`
Fails today: returns `stale: true` empty source.
Invoke: `.venv/bin/pytest tests/test_read_through_freshness.py -q`

### Gate 2
**cleared** — standing approval; approach = reparse_file + FreshnessGuard cap=1 + six tools.

---

## Phase 3 — Execute

**Branch:** `feat/035-read-through-freshness` (from main @ `6c8f4ff`)

**Implemented:** change-list #1–11 + review fix (deleted-file honesty). Suite tip: `666 passed`.

### Axis 1 — file set
`diff ⊆ approved list ✅` (plus #11 companion for new `freshness.py` module).

### Axis 2 — design-conformance
| Approach bullet | Status |
|-----------------|--------|
| 1 reparse_file + announce/parse/_write/resolve_edges | implemented-as-approved (returns `bool` instead of `None` — D1) |
| 2 FreshnessGuard cap=1 | implemented-as-approved (+ missing-path short-circuit — D2) |
| 3 Wire six tools + index_stale / stale | implemented-as-approved |
| 4 Primary path rules | implemented-as-approved |
| 5 Proving tests fake_adapter | implemented-as-approved |

### Deviations
| ID | What | Why | Trace |
|----|------|-----|-------|
| D1 | `reparse_file` → `bool` (False = no owner) | Callers need soft-fail → stale without exception | Approach §1 |
| D2 | `ensure`: missing on-disk file → `"ok"` | Planted-store fixtures / absent paths must not spawn adapters | Approach §2; hang fix |

### Ph3/4 proven by
| Row | Evidence |
|-----|----------|
| AC1–4, C1, W1–2 | `tests/test_read_through_freshness.py` (6 tests) green |
| R1–3, G1, C2–3 | wired tools + indexer path; suite green |
| Full suite | `666 passed in 32.35s` |

### Matrix (Ph3)
All rows → ✅ (evidence above).

---

## Phase 4 — Review

**Reviewed at** `d321d68` (files: indexer, freshness, six tools, proving tests, module-count guards, BACKLOG/PLAN/task). Bookkeeping commit after marker is exempt from stale-review.

### Reviewer (`mango:reviewer` · round 1 · [bcb7d9be](bcb7d9be-e438-422b-bb30-37af5c2050bf))
- **Verdict:** **CHANGES REQUESTED** (conditional LGTM once finding 1 lands)
- **Scope:** diff ⊆ Gate-2 list; R1.1 / R1.4 / R4 / R6 / R7.2 OK
- **Deviation adjudication:** D1 (`reparse_file` → bool) **accept**; D2 (missing on-disk → `"ok"`) **accept with compensating fix**
- **Findings:**
  | Sev | Finding | Path | Resolution |
  |-----|---------|------|------------|
  | Important | Indexed-but-deleted file reported `stale=False` with empty source | `freshness.py:32-33` + `read_symbol.py` | Fixed in `d321d68`: missing file → `stale=True` + `REASON_INDEX_STALE`; proving test `test_read_symbol_deleted_file_is_stale` |
- **Nits (non-blocking):** soft assert on `"edited" in source` — tightened; find_refs/impls share ensure wiring without dedicated cases — accepted

### Reviewer (`mango:reviewer` · verify-only · [efa8a034](efa8a034-19fc-4b5b-b3a6-de4e574fc892))
- **Verdict:** **LGTM** at tip `d321d68`
- **Proof:** freshness suite 6/6; related read_symbol/nav slice green; no new Critical/Important
- **Closed:** finding 1 fixed; D1/D2 and find_* subject-only left closed

### Challenger (ticket-blind · [155c9442](155c9442-6832-4857-97de-4cc1eadb13c7))

| # | Rebuilt requirement | Verdict | Adjudication |
|---|---------------------|---------|--------------|
| 1 | Shared query-time hash check + single-file reparse before shaping | **met** | — |
| 2 | Mechanism shared across read/nav tools | **met** (six tools) | impact/reach/include out of W2 inventory |
| 3 | Goal: refresh every file that returned rows touch | **not met** for find_* edge files | **Gate-2 Approach #4** — subject-only for find_*; edge refresh deferred under cap=1 |
| 4 | Promote `read_symbol` report-stale → repair inline | **met** | — |
| 5 | Per-call cap + stale reason (033) | **met** | — |
| 6 | Determinism: reparse rows == full_build; proving test | **met** | — |
| 7 | R1.1 / R1.4 | **met** | — |
| 8 | Single-file only (no full rebuild) | **met** | `resolve_edges` after one write = incremental pattern |
| 9 | AC edit→new content without rebuild | **met** (subject/hit tools); edge half tied to #3 | same adjudication as #3 |
| 10 | AC untouched → no adapter call | **met** | — |
| 11 | AC cap overflow → stale reason | **met** | — |

### Scope reconciliation
- File axis: ✅ approved list only (+ deleted-file fix inside `read_symbol` / proving tests)
- Behaviour axis: ✅ Approach bullets as approved; D1/D2 accepted; challenger #3/#9 adjudicated against Gate-2 #4
- Inventory N=6 tools: each calls `FreshnessGuard` ✅

### Gate 4 status
**clean** — reviewer LGTM at `d321d68`; challenger gaps adjudicated against ratified Approach #4.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| Phase 0 | exposure-checker | 1 | unmeasured (blocking retrieval) |
| Phase 4 | mango:reviewer | 1 | unmeasured (blocking retrieval) |
| Phase 4 | mango:challenger | 1 | unmeasured (blocking retrieval) |
| Phase 4 | mango:reviewer (verify) | 2 | unmeasured (blocking retrieval) |

`LEDGER: 4 dispatch rows | all cells valued or marked unmeasured | complete`

### Durable lesson
Planted-store paths without on-disk bytes must not trigger adapter spawn; tool-specific honesty (`read_symbol` stale on delete) compensates a shared guard short-circuit. See `docs/LESSONS.md` §035.

## Phase 5 — Finalise
- Status → done; BACKLOG + token row; lesson in LESSONS.md
- Outward: push branch + open PR (user-approved 2026-08-04) → [#41](https://github.com/cuongdinhngo/code-atlas/pull/41)

## Session status

- **Ticket:** 035
- **work_doc_mode:** embed
- **working-doc path:** `docs/tasks/035_read-through-freshness.md`
- **Current phase:** finalise complete
- **Blocked on:** —
- **Next action:** —
- **PR:** [#41](https://github.com/cuongdinhngo/code-atlas/pull/41)
