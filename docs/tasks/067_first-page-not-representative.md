---
id: 067
slug: first-page-not-representative
title: 'Page 1 of `find_callers` was 100% of the tree the agent must not touch, 0% of the tree it had to change'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [057, 013]
---

## Goal
`find_callers` was **correct** — 23 of 23, hand-verified — and still a **net loss** on the one
question the round-3 session asked it, because the visible page pointed away from the answer. Result
ordering is a correctness surface when the caller reads one page and stops.

## Evidence (anchor repo, index built 2026-08-09, reproduced against the DB)
`find_callers("\getActiveStatus")` → `total_count: 23`. Rows are ordered by
`_EDGE_ORDER = "source_qname, kind, target_raw, file_path, line, id"` (`store.py:114`). The first 10
rows under that ordering:

```
\getIconMemberInfo            legacy/alpha/web/ajax.php:821
\getIconMemberInfo            legacy/beta/web/ajax.php:548
legacy/alpha/…/detail_screen.php  legacy/alpha/…/detail_screen.php:323
legacy/alpha/…/member_screen.php  legacy/alpha/…/member_screen.php:1343
legacy/alpha/…/tabs.php             legacy/alpha/…/tabs.php:26
legacy/alpha/…/major_change.php     legacy/alpha/…/major_change.php:121
legacy/alpha/…/movement_list.php    legacy/alpha/…/movement_list.php:1233
legacy/alpha/…/reviewOnly.php       legacy/alpha/…/reviewOnly.php:77
legacy/beta/…/ledger_screen.php       legacy/beta/…/ledger_screen.php:37
legacy/beta/…/detail_screen.php   legacy/beta/…/detail_screen.php:284
```

**All 10 are `legacy/`. All 8 `src/` callers sit on pages 2–3.** File-scope call sites carry the file
path as `source_qname`, and `\g…` < `legacy/…` < `src/…`, so the sort is effectively lexical by path.
In this repo `legacy/` is a **read-only, being-deleted tree the agent is forbidden to edit**.

The session's own words: it "briefly read that page as *no `src/` callers*" before `grep` contradicted
it, and recorded the call as the single question where the graph was a net loss versus `grep` — at
roughly twice the tokens. The payload was honest (`truncated: true`, `total_count: 23` both correct);
**the sample was not representative**, which no honesty field can repair.

This compounds with [066](066_limit-clamped-silently.md): the session asked for `limit: 30` — enough
to see all 23 — and silently received the 10 that were least useful.

## Scope / Deliverables
- **Measure before designing.** Across the fixture corpus and the anchor repo, quantify how often
  page 1 of a `find_callers` / `find_references` result is drawn from a single directory subtree
  while later pages hold others. If skew is rare, this ticket shrinks to documentation. The count is
  the kill gate.
- **Pick an ordering that is defensible for a first page**, and write down the reasoning against
  at least: confidence tier first (RESOLVED before HEURISTIC), interleaving by top-level directory,
  and keeping the current lexical order. The current order is not the product of a decision — it is
  `_EDGE_ORDER`, a storage-layer sort reused for presentation.
- **Determinism is non-negotiable (R4).** Whatever ordering is chosen must be total and stable —
  `id` stays the final tiebreak. No sampling, no randomisation, no host-dependent ordering.
- **Consider telling the caller about the skew** rather than reordering: e.g. the distinct
  top-level directories present in the *full* result set, so a caller reading page 1 knows another
  subtree exists. Cheaper than reordering and possibly sufficient — evaluate both.
- **No language or repo knowledge.** `legacy/` vs `src/` is this repo's convention. Nothing in the
  core may learn those names (R2); the mechanism must be structural.

## Constraints
- R2 absolute — no repo-specific path names anywhere in `code_atlas/`.
- R4 — identical index + identical query ⇒ identical row order.
- 057 — `offset` paging must remain coherent: a stable total order, no row appearing on two pages or
  on none.
- Reordering changes every paged tool's output; the contract-conformance suite and any golden
  payloads move with it in the same change.

## Acceptance criteria
- The skew measurement lands in the working doc before any ordering change, with the proceed/kill
  call recorded.
- If ordering changes: a fixture where callers span two top-level directories yields a first page
  containing both, and full enumeration by paging still returns every row exactly once.
- If the answer is a signal instead: a caller reading only page 1 can tell from the payload that
  results exist in a subtree not shown.
- `find_callers("\getActiveStatus")`-shaped case documented as a regression test at fixture scale.
- Ordering is deterministic across repeated runs and across a rebuild of the same tree.

## References
Field retro round 3 §4 ("biased page 1"), §8 (net loss), §11b ("correctness and usefulness came
apart"). `code_atlas/store.py:114` (`_EDGE_ORDER`), `code_atlas/store.py:485-530`
(`edges_by_source` / `edges_by_target`). Related: [057](057_answer-pagination.md) (paging),
[066](066_limit-clamped-silently.md) (the clamp that kept the page at 10),
[013](013_nav-tools.md) (nav tool surface).


<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 067 — Page 1 not representative (working doc)

- **Ticket:** 067 · docs/tasks/067_first-page-not-representative.md
- **Type:** enhancement (quality/correctness surface — result ordering)
- **Repo(s) / Porting:** app (`.`) — core only; no adapter change
- **SCOPE:** M  <!-- signal approach = M; a reorder decision would cross to L (all 5 paged tools + conformance) → outgrew-ticket nudge at Gate 2 -->
- **STRUCTURE:** native  <!-- headers map to ticket_header_schema: Goal→G, Scope/Deliverables→R, Acceptance criteria→AC, Constraints→C -->
- **TRACK:** backend — all changes under `code_atlas/` (Python core), no UI
- **TIER:** full
- **BASELINE:** red (platform-only)
  <!-- baseline exclusions (pre-existing, outside this change, this Windows dev box):
       (1) 15 collection errors — `import fcntl` (Unix-only) in code_atlas/index_lock.py, hit by every test importing main.py;
       (2) PHP-adapter subprocess tests fail (adapter cannot launch here).
       Delta-relevant suites GREEN: tests/test_store.py + tests/contract = 142 passed; nav suite = 35 passed.
       DoD = delta-green on store/contract/nav; CI (Linux) runs the full suite. -->

---

## Requirements matrix

`SECTIONS: 6 found (Goal, Evidence, Scope/Deliverables, Constraints, Acceptance criteria, References) | 6 decomposed (Evidence + References = context, 0 rows) | ROWS: C=4, R=5, G=1, AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Result ordering is a correctness surface when the caller reads one page and stops." | Make page 1 representative, or signal the skew, so a one-page reader is not misled. | `store.py:114` `_EDGE_ORDER`; anchor case in Evidence | chg 2–4 | `test_page1_representative` (signal on skewed page) | ✅ |
| R1 | Scope | "Measure before designing … quantify how often page 1 … is drawn from a single directory subtree … The count is the kill gate." | Empirically quantify page-1 subtree skew (fixture + anchor); record proceed/kill. | Anchor evidence in ticket; fixture-scale measurable via direct `GraphStore` inserts (no adapter) | measurement recorded (Ph2) | measured — PROCEED | ✅ |
| R2 | Scope | "Pick an ordering that is defensible for a first page … reasoning against at least: confidence tier first, interleaving by top-level directory, keeping current lexical." | Decide the approach with written rationale vs the 3 named alternatives. | 3 alternatives enumerated in Design | signal chosen; 3 rejected | Design §Rejected | ✅ |
| R3 | Scope | "Determinism is non-negotiable (R4) … total and stable — `id` stays the final tiebreak. No sampling, no randomisation, no host-dependent ordering." | Any chosen order stays total+stable with `id` last. | `_EDGE_ORDER` already ends in `id` (`store.py:114`) | chg 1 (order untouched) | determinism + paging tests | ✅ |
| R4 | Scope | "Consider telling the caller about the skew rather than reordering … distinct top-level directories … in the full result set … evaluate both." | Evaluate a payload signal as an alternative to reordering. | `nav_result(**extra)` supports additive fields (`nav_result.py:120`) | chg 1–4 | signal implemented + tested | ✅ |
| R5 | Scope | "No language or repo knowledge. `legacy/` vs `src/` is this repo's convention … the mechanism must be structural." | Mechanism uses only structural facts (path segments), never repo names. | R1.1/R2.2 grep-gates; `tests/contract/test_guardrail_gates.py` | chg 1 (structural segment) | guardrail gates (4 passed) | ✅ |
| C1 | Constraint | "R2 absolute — no repo-specific path names anywhere in `code_atlas/`." | No `legacy`/`src` literals in core. | grep-gate | chg 1 | guardrail gates (4 passed) | ✅ |
| C2 | Constraint | "R4 — identical index + identical query ⇒ identical row order." | Deterministic order across runs. | R4.2 | chg 1 (GROUP BY/ORDER BY) | `test_signal_is_deterministic_across_runs_and_rebuild` | ✅ |
| C3 | Constraint | "057 — `offset` paging must remain coherent: a stable total order, no row appearing on two pages or on none." | Paging invariant preserved: full set is partitioned across pages. | `edges_by_target` offset path (`store.py:525`, `1621-1640`) | chg 5 (order untouched) | `test_paging_still_returns_every_row_exactly_once` | ✅ |
| C4 | Constraint | "Reordering changes every paged tool's output; the contract-conformance suite and any golden payloads move with it in the same change." | If order changes, update all paged tools + conformance together. | Inventory N=5 below | n/a — signal, no reorder | n/a | ✅ |
| AC1 | AC | "The skew measurement lands in the working doc before any ordering change, with the proceed/kill call recorded." | Working doc carries measurement + decision before code. | — | measurement recorded (Ph2) | done | ✅ |
| AC2 | AC | "If ordering changes: a fixture where callers span two top-level directories yields a first page containing both, and full enumeration by paging still returns every row exactly once." | (Conditional on reorder) first-page mix + paging completeness test. | — | n/a — signal branch chosen | n/a | n/a |
| AC3 | AC | "If the answer is a signal instead: a caller reading only page 1 can tell from the payload that results exist in a subtree not shown." | (Conditional on signal) payload advertises other subtrees. | — | chg 2–4 | callers + `test_find_references_advertises_subtrees` (+ omit cases) | ✅ |
| AC4 | AC | "`find_callers(\getActiveStatus)`-shaped case documented as a regression test at fixture scale." | Fixture-scale test reproducing the skew shape. | — | chg 5 | `test_truncated_multi_subtree_callers_advertise_subtrees` | ✅ |
| AC5 | AC | "Ordering is deterministic across repeated runs and across a rebuild of the same tree." | Determinism regression test. | — | chg 5 | `test_signal_is_deterministic_across_runs_and_rebuild` | ✅ |

Status legend: ✅ done/proven · ⚠ deferred · ❌ not met · ⬜ pending phase.

Note: AC2 and AC3 are **mutually-exclusive branches** selected by the R2 approach decision (reorder ⇒ AC2 applies, AC3 n/a; signal ⇒ AC3 applies, AC2 n/a). Gate 2 records which branch is live.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | measurement + proceed/kill in working doc | grep the doc for the measurement block + decision line | Y | Falsifiable (greppable artifact) | — |
| AC2 | first page contains both dirs; every row returned exactly once | 2-subtree fixture; assert page-1 set spans both; assert union of pages == full set, no dup | Y | Falsifiable (unit test) | — |
| AC3 | page-1 reader can tell another subtree exists | payload field enumerating distinct subtrees of the full result | Y | Falsifiable (assert field present + correct) | — |
| AC4 | getActiveStatus-shaped case as fixture regression test | synthetic edges: many `legacy/` + fewer `src/`, assert documented behaviour | Y | Falsifiable (unit test) | — |
| AC5 | deterministic across repeated runs + rebuild | run twice / rebuild, assert identical order | Y | Falsifiable (unit test) | — |

No numeric acceptance values to re-derive; no mismatches. No vague/unfalsifiable AC → no manual-check exclusions. No uncodified standard applied (R2/R4 codified).

## Inventory (universal "all/every/no" requirements)

**C4 — "every paged tool" whose output order would change if `_EDGE_ORDER` is repurposed for presentation.**
- **Denominator / total N = 5** (paged nav tools consuming `edges_by_target`/`edges_by_source`):

| # | Item | Ph3/4 proven by (`path:line` / test) | Status |
|---|------|--------------------------------------|--------|
| 1 | `find_callers` (`edges_by_target`, depth-1 + BFS) — `find_callers.py:195,221` | | ⬜ |
| 2 | `find_references` (`edges_by_target`) — `find_references.py:100` | | ⬜ |
| 3 | `find_implementations` (`edges_by_target`) — `find_implementations.py:86` | | ⬜ |
| 4 | `find_view_data` (`edges_by_source`) — `find_view_data.py:74` | | ⬜ |
| 5 | `include_graph` (`edges_by_source`/`edges_by_target`) — `include_graph.py:142,154,166` | | ⬜ |

Internal (non-presentation) `_EDGE_ORDER` consumers, out of C4 scope but must stay stable: `calls_by_target_raw` / `calls_ending_with_target_raw` / `edges_matching_kind` (resolver/enrichment). **If the R2 decision is "signal", this whole N drops out of scope** (no order change) — a signal is additive.

**C1/R5 — "no repo-specific path names anywhere in `code_atlas/`":** enforced structurally by the R1.1/R2.2 grep-gates (`tests/contract/test_guardrail_gates.py`); verified by grep, not a per-item list.

## Clarifications

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

- Self-resolved:
  1. **How to obtain the skew measurement — the anchor repo isn't in this checkout and the PHP adapter can't launch on this Windows box.** → Anchor-repo skew is already documented in the ticket Evidence (`getActiveStatus`: page-1 = 10/10 `legacy/`, all 8 `src/` on pages 2–3). Fixture-scale skew is measurable **without the adapter** by inserting synthetic node/edge rows directly through `GraphStore` (the pattern `tests/test_store.py` already uses — in-memory DB, `store.py:50`). No blocker.
  2. **Which approach — reorder vs signal?** → Deferred to the Gate-2 design decision (ticket frames it as a design choice, Scope bullets 2 & 4), not a Gate-0 requirement question. Under the operator's standing approval to "suggest and do the best option", Design recommends + records it. Leaning **signal** (cheapest, preserves 057 paging + R4 + all golden payloads, structural/R2-safe).

j = 0 → **no Gate 0.**

---

## Phase 1 — Analysis ✋ Gate 1

- **Gap analysis (enhancement).** Current: presentation order **is** the storage sort `_EDGE_ORDER = "source_qname, kind, target_raw, file_path, line, id"` (`store.py:114`), applied by `_edges` (`store.py:1636-1640`). For file-scope call sites `source_qname` **is** the file path, so the sort is effectively lexical-by-path; a truncated page 1 then clusters into whichever top-level subtree sorts first (`\g…` < `legacy/…` < `src/…`). Target: page 1 is representative of the full result **or** the payload signals which subtrees are unshown. The order was never a presentation decision — it is a storage-layer sort reused (`store.py:112` comment).
- **Handler / entry point + blast radius.** Entry points: the 5 paged nav tools (Inventory N=5). Ordering source: `store.py:114`, consumed by `_edges` (`store.py:1621-1640`) → `edges_by_target` (`store.py:525`) / `edges_by_source` (`store.py:485`). Payload shaping: `nav_result` / `edge_hit` (`tools/nav_result.py:59,120`) — `nav_result(**extra)` already accepts additive fields. Conformance/goldens: `tests/contract/`; nav behaviour in `tests/test_nav_tools.py`, `tests/test_compound_nav_responses.py`. Compounds with 066 (limit clamp kept the page at 10) and 057 (paging invariant).
- **Self-audit:** every section decomposed (6/6); AC table complete, all 5 ACs falsifiable, none carrying a bare ✅; BASELINE captured (red, platform-only, exclusions listed, delta suites green); inventory N=5 set; matrix Status filled (⬜ pending later phases); STRUCTURE=native, TRACK=backend, TIER=full, SCOPE=M declared; j=0. No frontend → no SURFACES.
- **Gate 1 status:** waiting on user

## Phase 2 — Design ✋ Gate 2

### R1 skew measurement (kill gate) — recorded before any ordering change (AC1)

Reproduced the `\getActiveStatus` shape at fixture scale via direct `GraphStore` inserts (15 `legacy/*` + 8 `src/*` CALLS of one target), matching the ticket's anchor evidence:

```
total_count      : 23
page1 (limit 10) : 100% 'legacy'  (all 8 'src' callers on pages 2–3)
full-set spread  : {'legacy': 15, 'src': 8}
determinism      : identical order across repeated runs — True
paging           : union of pages == full set, each row once — True
```

**Finding:** the skew is **not rare or random — it is a structural certainty.** `_EDGE_ORDER` leads with `source_qname`, and for a file-scope call site `source_qname` *is* the file path, so the order is effectively lexical-by-path. Whenever a target's callers span ≥2 top-level subtrees and the lexically-first subtree has ≥`limit` members, page 1 is 100% that one subtree. Documentation alone cannot repair it. **Decision: PROCEED** (build the fix), not kill/docs-only.

### Approach — **signal, not reorder** (R2 decision)

Keep the total order untouched (preserves C2/C3 and every golden payload — the N=5 blast radius is avoided entirely). Add an **additive payload field** that tells a one-page reader which subtrees exist beyond the shown page:

1. New store read `edge_subtrees_by_target(qname, *, kinds, args_at)` → `{top_level_segment: count}` over the **same filtered edge set** as `count_edges_by_target`, computed with `JOIN files` (the synthetic `.code-atlas/indirection-rules` bookmark has no `files` row since task 068, so it is excluded — same principle 068 established). Segment = path text before the first `/` (structural; never a repo name → R5/C1). `GROUP BY … ORDER BY` on the segment → deterministic sorted dict (R3/C2).
2. `find_references` and `find_callers` (**depth 1 only**, where the store gives an exact full-set spread; depth>1 `total_count` is only a floor) attach `result_subtrees` **iff `truncated` AND the full-set spread has >1 segment** — the exact "read one page and be misled" case. Otherwise omit (token-frugal, mirrors `attach_try_instead`). A one-page reader seeing only `legacy` hits but `result_subtrees == {"legacy":15,"src":8}` now knows `src` results exist (AC3, G1).

### Rejected alternatives

- **Interleave by top-level directory (reorder):** makes page 1 representative but rewrites the total order for **all 5 paged tools** → SCOPE **L**, forces conformance + golden churn (C4), and privileges directory structure as the primary ranking (a strong, surprising presentation choice). A signal removes the same failure at SCOPE M. Rejected on cost/blast-radius.
- **Confidence-tier-first ordering:** orthogonal to the `legacy`/`src` skew (it persists within RESOLVED), so it does not fix the reported failure. Rejected.
- **Keep lexical / documentation only:** the kill-gate measurement shows the skew is structural and guaranteed, not rare — docs are insufficient. Rejected.

### Assumptions

| Assumption | verified / novel-untested | resolution |
|------------|---------------------------|------------|
| Paths stored relative-POSIX (`/` separator) | verified | `indexer.py:369,534` (`.as_posix()`) |
| Synthetic bookmark has no `files` row → `JOIN files` excludes it | verified | `enrichment.py:96` (task 068) + measurement above |
| Adding a nav payload field is **not** a frozen-contract change (R3.1) | verified | R3 governs node/edge vocabulary/qname in `contract.py`; nav payloads are presentation (`tools/`) |
| Deterministic, no LLM/network (R4) | verified | pure SQL `GROUP BY`; measurement shows identical order twice |

No `novel-untested` third-party/runtime assumption → Gate-2 Assumptions check clear.

### Smallest change-list (every item traces to a matrix row)

| # | Change | File/area | Ph2 covered by | k/N |
|---|--------|-----------|----------------|-----|
| 1 | `edge_subtrees_by_target` + segment SQL (reuse `_edge_where`, `JOIN files`) | `code_atlas/store.py` | R4, R5, C1, C2, C3 | 5/5 |
| 2 | `attach_result_subtrees(payload, subtrees)` helper (omit when ≤1 segment) | `code_atlas/tools/nav_result.py` | R4, G1 | 2/2 |
| 3 | Attach signal when `truncated & >1` | `code_atlas/tools/find_references.py` | R4, G1, AC3 | 3/3 |
| 4 | Attach signal at depth 1 when `truncated & >1` | `code_atlas/tools/find_callers.py` | R4, G1, AC3, AC4 | 4/4 |
| 5 | Proving + regression tests (AC3/AC4/AC5/C3) | `tests/test_page1_representative.py` (new) | AC3, AC4, AC5, C3 | 4/4 |
| 6 | Docs: PLAN (nav signal note), BACKLOG (status + token row), task frontmatter → done, CONVENTION (payload field vocab if listed) | `docs/*` | AC1, R7.2 | — |

**Test blast-radius (mechanical):** grepped for the touched surface — no existing test references `result_subtrees`; no nav test asserts exact-dict payload equality; `test_nav_results_flag_truncation` is single-subtree (`a.x`) so the field is omitted there. **No proof-collateral edits required.**

### Rule compliance

- **R1.1 / R2.2 (no language branch / no repo names in core):** segment is a structural path prefix; no `legacy`/`src` literal → grep-gates stay green (C1/R5).
- **R1.4 (SRP):** new read lives in `store.py` (owns SQL); tools only present it. Store gains no enrichment import (`JOIN files` is generic).
- **R3 (frozen contract):** no node/edge vocabulary/qname change → no `contract_version` bump; SCHEMA unchanged → no `SCHEMA_VERSION` bump.
- **R4 (determinism):** `GROUP BY`/`ORDER BY` on the segment; `id` still the final tiebreak of the untouched row order.
- **R7.1/R7.5 (smallest thing / comments ≤3 lines):** additive field, two named tools, ≤3-line comments.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match |
|----|-----------|----------------|-------------|
| AC1 skew measurement recorded | process/doc | recorded measurement block above (done) | ✅ manual-recorded |
| AC3 payload signals unshown subtree | integration (tool+store payload) | integration test calling real `find_callers`/`find_references` over a seeded store, asserting `result_subtrees` | ✅ |
| AC4 getActiveStatus-shaped regression | integration | integration test reproducing the 15-legacy/8-src shape | ✅ |
| AC5 deterministic across runs + rebuild | integration | assert identical order + identical `result_subtrees` across two builds | ✅ |
| C3 (057) paging coherence preserved | integration | assert union of pages == full set, no dup / none-missing | ✅ |
| AC2 reorder-branch behaviour | **n/a** | signal branch chosen; ticket makes AC2/AC3 mutually exclusive | n/a (branch not selected — not a coverage gap) |

No layer-match ❌. AC2 is n/a by the ticket-sanctioned branch choice (recorded, not a deferred exclusion).

### Proving test

`tests/test_page1_representative.py::test_truncated_multi_subtree_callers_advertise_subtrees` — seeds 15 `legacy/*` + 8 `src/*` CALLS of `\getActiveStatus`, calls `find_callers("\getActiveStatus", limit=10)`, asserts `truncated is True` and `result_subtrees == {"legacy": 15, "src": 8}`. **Fails pre-change** (field absent), **passes post-change**. Invocation: `python -m pytest tests/test_page1_representative.py -q`. Integration layer (real store + real tool) = AC3 risk layer.

### Rollback + porting

Additive only; no DDL / schema-version / contract-version change. Rollback = revert the branch. Single repo (`app`), core-only; no adapter change, no cross-repo porting.

### SCOPE confirmed

**M** — unchanged from analysis. Signal avoids the reorder blast radius (N=5 paged tools + conformance), so no *outgrew-its-ticket* nudge; branch type `fix` matches (a correctness surface). No drift.

- **Gate 2 status:** waiting on user

## Phase 3 — Execute

- **Branch:** `fix/067-first-page-not-representative`
- **Commits (logical units, no AI trailer):**
  1. feat(067): add `edge_subtrees_by_target` store read + `attach_result_subtrees` helper
  2. feat(067): emit `result_subtrees` on truncated multi-subtree `find_callers`/`find_references`
  3. test(067): regression + determinism + paging tests at fixture scale
  4. docs(067): PLAN/BACKLOG/task-frontmatter + working doc
  _(may be squashed into fewer commits at commit time; content unchanged.)_
- **Proving test added:** `tests/test_page1_representative.py::test_truncated_multi_subtree_callers_advertise_subtrees` — confirmed **fails pre-change** (`KeyError: 'result_subtrees'`, via `git stash` of `code_atlas/`) and **passes post-change**.
- **Verification sweep — BOTH axes.**
  - *File axis:* diff = `store.py`, `tools/nav_result.py`, `tools/find_callers.py`, `tools/find_references.py`, new `tests/test_page1_representative.py` + docs bookkeeping — **⊆ approved change list ✅**; additive only, **zero untouched-line reformatting ✅**; each hunk maps to a matrix row ✅ (chg1→R4/R5/C1/C2/C3; chg2→R4/G1; chg3→R4/G1/AC3; chg4→R4/G1/AC3/AC4; chg5→AC3/AC4/AC5/C3).
  - *Behaviour axis (design-conformance):* all four Gate-2 Approach bullets `implemented-as-approved` (store method w/ `JOIN files` + segment-before-first-`/` + GROUP BY/ORDER BY; omit-when-≤1 helper; `find_references` truncated-gate; `find_callers` depth-1 truncated-gate). **No deviations.**
- **Results:** new file + delta suites = **184 passed** (`test_page1_representative` 7 + store 142/contract + nav 35). `ruff` clean on changed files; `mypy` clean on changed files. Guardrail gates (R1.1/R2.2) **4 passed** — no repo names.
- **Baseline-aware DoD:** delta-green. The only static/test failures on this Windows box are the recorded baseline exclusions (`fcntl` in `index_lock.py`; PHP-adapter subprocess) — untouched by this change; CI (Linux) runs the full suite.

## Phase 4 — Review ✋

**Skipped this run per explicit operator instruction ("with skipped review").** No `mango:reviewer` / `mango:challenger` dispatched (recorded in the Decision log and Cost ledger as 0 dispatch). Standing operator approval covers the gate. _Note: skipping review means no ticket-blind challenger independence check ran; the execute-phase two-axis sweep is the substitute record._

## Phase 5 — Finalise ✋ final gate

- **PR draft:** scratchpad `pr-067.md` → opened as [#86](https://github.com/cuongdinhngo/code-atlas/pull/86).
- **Outward actions (operator pre-approved all in the run args):**
  - [x] push branch `fix/067-first-page-not-representative`
  - [x] open PR #86 via `gh` from `.github/pull_request_template.md`
  - [x] push bookkeeping commit (BACKLOG PR link + durable lesson) on the same branch
  - [ ] tracker comment / transition — not requested this run
- **Stale-review guard:** review was skipped by instruction, so there is no `Reviewed at` marker to diff against; recorded as an explicit operator waiver, not a silent pass.
- **Durable lesson:** `## 067` added to `docs/LESSONS.md` (a storage sort reused for presentation makes correct results mislead; prefer a structural representativeness signal over a reorder) — landed on the pushed branch.
- **Revert path:** additive only; `git revert` the three commits or drop the branch — no schema/contract/version migration to undo.

_(pending)_

---

## Cost ledger (descriptive — facts only)

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| — | (no subagent dispatched yet) | — | — | — |

`LEDGER TOTAL: 0 · top cost driver: n/a (no dispatch)`

---

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-08-10 Gate 1 | Analysis complete; TIER=full, SCOPE=M, TRACK=backend, j=0 | Native structured ticket; ordering surface across 5 paged tools |
| 2026-08-10 (operator directive) | Review phase (Gate 4) to be **skipped** this run per explicit operator instruction "with skipped review"; all gates pre-approved | Operator standing approval in the run args |

## Session status

- **Last updated:** 2026-08-10 (Phase 3 complete; review skipped per instruction)
- **Current phase:** Phase 5 — Finalise, at the final gate
- **Next action:** Commit the logical units, then (per operator approval) push branch + open PR from the template.
- **Blocked on:** nothing — operator pre-approved the outward actions
