---
id: 027
slug: resolver-batched-lookups
title: Batch resolver candidate lookups (N+1 read path)
phase: 1
milestone: M4
status: done
depends_on: [011, 015]
---

## Goal
Make the resolver's read path batched like its write path, so the M4 scale baseline measures the
shape we intend to ship (§8.2, Plan §6.1).

## Scope / Deliverables
- `resolver.resolve_edges` pulls unresolved edges 1000 at a time (`_RESOLVE_BATCH`), then issues one
  `nodes_by_qualified_name` per edge — plus a `nodes_by_name(kind="Method")` fallback for
  HEURISTIC `CALLS` — so a full batch costs up to ~2000 SELECTs. `apply_resolution` is already
  batched; only the reads are not.
- Add a batched store lookup (`nodes_by_qualified_names` / `nodes_by_names`) taking a set of keys and
  returning `key → rows`, capped at `max_candidates` **per key**.
- Rewrite `_resolve_include` / `_resolve_symbol` to two passes per edge batch: (1) one batched lookup
  for FQN targets plus one kind-scoped lookup for `INCLUDES` paths, (2) one batched `Method` lookup
  for the `CALLS` edges that pass 1 left unmatched.
- No behavior change: same links, same siblings, same tiers, same candidate order.

## Constraints
- **Per-key top-N, not a global LIMIT.** `WHERE qualified_name IN (...) LIMIT n` breaks the
  `max_candidates` cap — it truncates across keys, changing which candidate becomes the edge's target
  and which become siblings. Use `ROW_NUMBER() OVER (PARTITION BY qualified_name ORDER BY …)`
  (SQLite ≥ 3.25) or an equivalent per-key partition.
- **Candidate order must be byte-identical to today's.** `_NODE_ORDER` is
  `qualified_name, file_path, line_start, id` (`store.py:101`), so partitioning by `qualified_name`
  and ordering by `file_path, line_start, id` reproduces the current per-key sequence exactly (R4).
- Store owns the SQL; the resolver never opens a cursor (R1.4). No language branches (R1.1).

## Acceptance criteria
- Resolving a fixture with multi-candidate targets produces byte-identical `edges` rows (target,
  tier, sibling set and order) before and after — a golden assertion, not just a count.
- A batch of N unresolved edges issues O(1) node SELECTs per batch, not O(N) — asserted by counting
  queries against a real store, not by inspecting the SQL string.
- `max_candidates` still caps candidates per target qname when several qnames in one batch each
  exceed the cap.
- Existing resolver and nav-tool tests pass unchanged.

## References
Plan §8.2, §6.1; [PR #25](https://github.com/cuongdinhngo/code-atlas/pull/25) review (write path
batched, read path not); `code_atlas/resolver.py`; `code_atlas/store.py` `_nodes` / `_NODE_ORDER`.
Ordering note: land this **before** the 015 AC2 timing artifact (BACKLOG follow-up / task 018), or
that baseline measures the read path this task removes.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 027 — Batch resolver candidate lookups (working doc)

- **Ticket:** 027 · [docs/tasks/027_resolver-batched-lookups.md](027_resolver-batched-lookups.md) (raw above separator)
- **Type:** enhancement
- **Repo(s) / Porting:** `app` (`.`) only
- **SCOPE:** _(analysis)_
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** _(analysis)_
- **BASELINE:** _(analysis)_
- **work_doc_mode:** `embed` → below separator (harness `embed`; sibling `027_*.work.md` would break `test_backlog_bookkeeping`)

## Session status

```
phase: 5 finalise — complete
Gate: closed (push + PR #30 approved)
work_doc_mode: embed
working_doc: docs/tasks/027_resolver-batched-lookups.md (below separator)
branch: feat/027-resolver-batched-lookups
PR: https://github.com/cuongdinhngo/code-atlas/pull/30
Reviewed at: 2c10bac7d88997355903d76df6015dab0414fff2
Reviewed files: code_atlas/store.py, code_atlas/resolver.py, tests/test_resolver.py, docs/BACKLOG.md, docs/tasks/027_resolver-batched-lookups.md
```

- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — 558 passed (`.venv/bin/pytest -q`)

---

## Phase 0 — Refine

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`

`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

`REFINE: 3 unresolved surfaced | 3 want-decision asked | 6 how-decision resolved+cited | 3 ASSUMED | skip: no`

**INPUT KIND:** ticket (single deliverable — not an epic).

### ASSUMED (ratified Gate 1 under standing approve)

| # | Assumed choice | Why ASSUMED | Explicit confirm | Reverses prior? |
|---|----------------|-------------|------------------|-----------------|
| A1 | Prove O(1) by counting `GraphStore._rows` calls during `resolve_edges` (monkeypatch/counter) — assert ≤ small constant for N≫1 | W1 best | Gate 1 standing | no |
| A2 | Plant multi-candidate graph in SQLite; golden assert target/tier/sibling order | W2 best | Gate 1 standing | no |
| A3 | Singular `nodes_by_*` become thin wrappers over batch helpers | W3 best | Gate 1 standing | no |

### HOW (cited)

| # | Resolution | Citation |
|---|------------|----------|
| 1 | `ROW_NUMBER() OVER (PARTITION BY …)` per-key top-N | ticket Constraints |
| 2 | Order `file_path, line_start, id` after partition key | `_NODE_ORDER` |
| 3 | Batch SQL in `store.py` only | R1.4 |
| 4 | Two-pass: FQN(+File INCLUDES) then Method for unmatched CALLS | ticket Scope |
| 5 | Behavior freeze | ticket; R4.2 |
| 6 | No language branches | R1.1 |

### Exposure-checker

[challenger](d0b1d784-c72d-4f33-bbdc-f674674c3fb1): `EXPOSURE: 0` — none.

---

## Phase 1 — Analysis

`PREMISE:` / `RECALL:` carried.

`SECTIONS: 5 found (Goal, Scope / Deliverables, Constraints, Acceptance criteria, References) | 5 decomposed | ROWS: C=3 R=4 G=1 AC=7`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | Batched read path like write path | Batch store lookups + two-pass resolve | gap | Approach | proving | ❌ |
| R1 | Scope | Current N+1 described | context only | resolver.py | — | — | ✅ |
| R2 | Scope | Add batch APIs per-key cap | `nodes_by_qualified_names` / `nodes_by_names` | gap | change-list 1 | store tests | ❌ |
| R3 | Scope | Two-pass rewrite | resolve_edges refactor | gap | change-list 2 | resolver tests | ❌ |
| R4 | Scope | No behavior change | golden + existing tests | A2 | proving | PASS | ❌ |
| C1 | Constraints | Per-key top-N not global LIMIT | ROW_NUMBER | ticket | change-list 1 | multi-key cap test | ❌ |
| C2 | Constraints | Order byte-identical | partition order | `_NODE_ORDER` | change-list 1 | golden | ❌ |
| C3 | Constraints | Store owns SQL; no lang branches | R1.4/R1.1 | rules | change-list | grep | ❌ |
| AC1 | AC | Byte-identical edges golden | A2 | A2 | proving | PASS | ❌ |
| AC2 | AC | O(1) SELECTs per batch | A1 | A1 | proving | PASS | ❌ |
| AC3 | AC | max_candidates per key when many exceed | C1 | change-list 1 | cap test | ❌ |
| AC4 | AC | Existing resolver/nav tests pass | suite | — | suite | ❌ |
| AC-A1 | refine | `_rows` counter proof | A1 | A1 | proving | ❌ |
| AC-A2 | refine | planted golden | A2 | A2 | proving | ❌ |
| AC-A3 | refine | singular wrappers | A3 | A3 | store unit | ❌ |

### AC validation

| AC | Falsifiable? | Gate-1 |
|----|--------------|--------|
| AC1–AC4, A1–A3 | yes under ASSUMED | ratify A1–A3 |

### Inventory

N=2 APIs + resolver rewrite + tests. `TRACK: backend`. `SURFACES:` N/A.

`CLARIFICATION: 3 raised | 6 how | 3 ASSUMED` → **j=0** after standing approve.

### Gap / blast

| Slice | Current | Target |
|-------|---------|--------|
| Store | single-key `_nodes` | batch + wrappers |
| Resolver | per-edge lookup | two-pass batch |

Blast: `store.py`, `resolver.py`, `tests/test_resolver.py` (+ maybe `test_store.py`). Repos: app.

`RULE SECTIONS: §1 ✅ R1.1/R1.4 · §2 N/A · §3 N/A · §4 ✅ R4.2 · §5 N/A · §6 ✅ R6.1 · §7 ✅ R7.2 · §8 N/A`

**SCOPE:** M · **TIER:** full

**Gate 1:** A1–A3 ratified under standing approve. Cleared.

---

## Decision log

| When | Decision | Rationale |
|------|----------|-----------|
| Phase 0 | W1–W3 → ASSUMED A1–A3 | standing best option |
| Gate 1 | Ratify A1–A3 | standing pass all gates |
| Gate 2 | Approve approach + change-list | standing pass all gates |

---

## Phase 2 — Design

### Approach

Add `GraphStore.nodes_by_qualified_names` / `nodes_by_names` using `ROW_NUMBER() OVER (PARTITION BY key ORDER BY file_path, line_start, id)` with `rn <= limit`, returning `dict[key, list[Row]]` in `_NODE_ORDER` within each key. Make singular lookups thin wrappers (A3). Rewrite `resolve_edges` to collect keys per batch, one FQN(+File for INCLUDES) batch lookup, then one Method batch for unmatched HEURISTIC CALLS — same `_queue_candidates` / tier logic. Prove with planted multi-candidate golden (A2) and `_rows` call-count ≤ constant for N edges (A1).

### Rejected

| Alt | Why |
|-----|-----|
| Global `IN (...) LIMIT n` | Violates C1 / changes siblings |
| Keep N+1, only memoize in Python | Still O(N) round-trips to SQLite |
| Dual-path feature flag | Unnecessary forever-dual; golden + existing tests suffice |

### Assumptions

| Assumption | Tag | Resolution |
|------------|-----|------------|
| ROW_NUMBER available | verified | SQLite 3.45.1 |
| Empty key list → `{}` without SQL | novel → unit test | proving |
| Wrapper preserves singular semantics | verified → tests | existing + new |

### Change-list

| # | Change | File | Blast | Ph2 | k/N |
|---|--------|------|-------|-----|-----|
| 1 | Batch lookups + singular wrappers | `code_atlas/store.py` | all `_nodes` callers | R2,C1–C2,AC3,A3 | 1 |
| 2 | Two-pass `resolve_edges` | `code_atlas/resolver.py` | resolve callers | R3,R4,G1 | 1 |
| 3 | Proving: golden + SELECT count + per-key cap | `tests/test_resolver.py` (and/or `test_store.py`) | — | AC1–3,A1–A2 | 1 |
| 4 | Docs: BACKLOG status + task frontmatter | docs | readers | R7.2 | 1 |

### Verification plan

| AC | layer | proof | match |
|----|-------|-------|-------|
| AC1 golden | integration | planted edges dump | ✅ |
| AC2 O(1) | integration | `_rows` counter | ✅ |
| AC3 per-key cap | integration | two qnames each >cap | ✅ |
| AC4 suite | integration | pytest | ✅ |

### Proving test

`tests/test_resolver.py::test_batched_resolve_matches_golden_and_is_o1_selects` — plant multi-candidate CALLS/EXTENDS; resolve; assert edge golden; assert `_rows` count ≤ 4 for batch of ≥10 edges.

**Gate 2:** cleared under standing approve.

---

## Phase 3 — Execute

**Branch:** `feat/027-resolver-batched-lookups`

**Verification sweep**

| Check | Result |
|-------|--------|
| Proving | `test_batched_resolve_matches_golden_and_is_o1_selects` PASS |
| Cap test | `test_batch_lookup_caps_per_key_not_globally` PASS |
| Full suite | **560 passed** |
| Diff ⊆ change-list | store + resolver + tests + docs |
| Approach | ROW_NUMBER batch + two-pass resolve + wrappers — **implemented-as-approved** |

**Deviations:** none.

---

## Phase 4 — Review

**Reviewed at** `2c10bac7d88997355903d76df6015dab0414fff2` (after partition-order fix). Bookkeeping tip after (`5b07128`) is stale-review exempt (working doc only).

| Dispatch | Verdict |
|----------|---------|
| mango:reviewer round 1 ([Reviewer](3e4ad06e-0b78-427f-9432-fabe4883fb59)) | **BLOCK** — `nodes_by_names` top-N ordered by `file_path` not full `_NODE_ORDER` |
| mango:challenger ([Challenger](70f0e660-c06d-4042-9699-477df9b8edd6)) | ticket-blind — **7 met · not met on #2/#4/#6** (name-keyed byte-identity) |
| mango:reviewer round 2 verify ([Reviewer](c04e91c4-c4a4-4b0d-9478-c96570a57b35)) | **LGTM** — prior Critical verified fixed; regression test present |

### Reviewer detail round 1 ([Reviewer](3e4ad06e-0b78-427f-9432-fabe4883fb59))

- **Verdict:** BLOCK
- **Tip then:** `1f0681c` (pre-fix)
- **Critical — `code_atlas/store.py` `_nodes_batched`:** partition used `ORDER BY file_path, line_start, id`. Correct when `PARTITION BY qualified_name` (key constant in partition). **Wrong** when `PARTITION BY name` (`nodes_by_names` / Method fallback): same-name rows can differ on `qualified_name`, so top-N by `file_path` can pick a **different candidate set** than singular `_nodes` (`ORDER BY _NODE_ORDER = qualified_name, file_path, line_start, id`). Violates R4.2 / AC1 / C2.
- **Repro:** `\A\put`@`b.x` vs `\Z\put`@`a.x`, `limit=1` → old semantics `\A\put`; new path `\Z\put`.
- **Why proving missed it:** golden fixture `a.x`/`b.x`/`c.x` sorted the same as `\A::put`/`\B::put`/`\C::put`.
- **Non-blocking:** sibling append order across pass-1 vs pass-2 not observable under `_EDGE_ORDER`.

**Fixed in:** `2c10bac` — `ORDER BY {_NODE_ORDER}` inside partition + `test_nodes_by_names_top_n_follows_qualified_name_not_file_path`.

### Challenger detail ([Challenger](70f0e660-c06d-4042-9699-477df9b8edd6)) — ticket-blind

`REQUIREMENTS: 9` · independence: raw ticket only (working doc excluded from judgment).

| # | Reconstructed requirement | Verdict | Evidence |
|---|---------------------------|---------|----------|
| 1 | Add `nodes_by_qualified_names` / `nodes_by_names` with per-key cap | met | `store.py:283-297`; resolver calls with `limit=max_candidates` |
| 2 | Two-pass rewrite; **no behavior change** | **not met** (pre-fix) | name-keyed top-N diverged — see #4 |
| 3 | Per-key top-N via `ROW_NUMBER` PARTITION, not global LIMIT | met | `store.py` `ROW_NUMBER() … WHERE rn <= ?` |
| 4 | Candidate order byte-identical to `_NODE_ORDER` | **not met** (name) / met (qname) | partition ordered by `file_path…` for `name` keys |
| 5 | Store owns SQL; no language branches | met | SQL only in `store.py`; no `if language ==` in core |
| 6 | AC: byte-identical edges golden | **not met** (as proof) | golden fixture couldn't catch #4; live counter-example existed |
| 7 | AC: O(1) node SELECTs per batch | met | ≤3 `_rows` SELECTs per batch; proving asserts `calls["n"] <= 4` |
| 8 | AC: `max_candidates` per key when several exceed | met | `test_batch_lookup_caps_per_key_not_globally` |
| 9 | AC: existing tests pass | met | **560 passed** at challenger time |

**Summary from challenger:** batching + O(1) + store SQL sound; **behavior change** on Method-name fallback truncation until partition order fixed.

### Reviewer detail round 2 verify ([Reviewer](c04e91c4-c4a4-4b0d-9478-c96570a57b35))

- **Verdict:** LGTM
- **Prior Critical verified fixed:**
  1. Partition `ORDER BY {_NODE_ORDER}` (`store.py:695-701`)
  2. Regression `test_nodes_by_names_top_n_follows_qualified_name_not_file_path` — `\Z::put`@`a.x` vs `\A::put`@`z.x`, `limit=1` → both singular and batched pick `\A::put`
- **Verification:** `tests/test_resolver.py` + `test_store.py` → **95 passed**; ruff/mypy clean; full-suite sandbox adapter hangs treated as env fault (untouched files)
- **Rules:** R1.1 / R1.4 / R3.2 / R4.2 / R7.2 — ok; no Critical/Important remain

### Scope reconcile

File set ⊆ change-list; approach bullets **implemented-as-approved** (after round-1 fix). **Gate 4: clean.**

### Matrix Ph3/4

G1 / R2–R4 / C* / AC* → ✅ proven by proving + cap + name-order regression + full suite (**561 passed** post-fix).

---

## Phase 5 — Finalise

### Outward actions

1. **Push** — approved → `feat/027-resolver-batched-lookups`
2. **Open PR** — approved → [#30](https://github.com/cuongdinhngo/code-atlas/pull/30)

---

## Cost ledger

| Phase | Dispatch | Round | Tokens | Notes |
|-------|----------|-------|--------|-------|
| 0 refine | challenger (exposure-checker) | 1 | unmeasured (host does not surface usage) | [d0b1d784](d0b1d784-c72d-4f33-bbdc-f674674c3fb1); EXPOSURE: 0 |
| 4 review | reviewer | 1 | unmeasured (host does not surface usage) | [3e4ad06e](3e4ad06e-0b78-427f-9432-fabe4883fb59); BLOCK |
| 4 review | challenger | 1 | unmeasured (host does not surface usage) | [70f0e660](70f0e660-c06d-4042-9699-477df9b8edd6); 7 met / not met on byte-identity |
| 4 review | reviewer | 2 verify | unmeasured (host does not surface usage) | [c04e91c4](c04e91c4-c4a4-4b0d-9478-c96570a57b35); LGTM |