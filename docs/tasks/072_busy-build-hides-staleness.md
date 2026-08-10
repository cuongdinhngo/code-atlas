---
id: 072
slug: busy-build-hides-staleness
title: '`mode: "busy"` returns in 0.0 s and reads like success — the caller then queries a stale index'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [053, 033]
---

## Goal
Two clients called `build_or_update_index` at once. The lock did its job: one built, one was refused,
nothing corrupted. But the refusal returns in **0.0 seconds** carrying no staleness information, so an
agent whose opening move is *"refresh the index, then investigate"* reads it as done and proceeds
against an index it never refreshed. Make the refusal say what the caller is about to query.

## Evidence (memory/concurrency field run, 2026-08-09, anchor repo)
Two clients released simultaneously through a barrier, both calling `build_or_update_index(full=false)`:

```
--- client 0: 0.0s
    {"mode": "busy", "requested_full": false, "reason": "another_build_running",
     "db_path": "…/.code-atlas/graph.db", "seconds": 0.0}
--- client 1: 83.2s
    {"mode": "incremental", "wrote": {"files": 107, …},
     "graph": {"files": 18878, "nodes": 185966, "edges": 1782725}, "seconds": 83.21}
# errors: none; afterwards staleness "current"
```

The mechanism is correct and stays: `try_index_write_lock` (`index_lock.py:19`) gives real mutual
exclusion via `write.lock`, and the busy branch returns **without opening the DB**
(`build_or_update_index.py:53-62`) — a deliberate property worth keeping.

What the loser cannot tell from that payload:
- whether the index it is about to read is **current or behind** — `get_index_status` in the same run
  reported `"staleness": "behind"` with `last_commit` ≠ `head_commit`, a field the refusal never
  carries;
- whether the winner's build will finish **soon or in 83 seconds**;
- that the correct next move is to wait and re-check rather than proceed.

The 0.0 s latency is what makes it read as success. A refusal that takes no time and returns no
warning is indistinguishable, to a caller skimming for "did the refresh happen", from a no-op
"already current" — and the tool has no such response today, so nothing teaches the caller otherwise.

This is one of exactly two API shapes in the whole run that can mislead a caller under concurrency;
the other is [071](071_answers-do-not-name-their-tree.md). Both produce a **confident answer rather
than an error**. The rest of the concurrency path was honest: 452 drift events under 3-way contention
produced zero soft-fails and zero `SQLITE_BUSY` reaching a caller.

## Scope / Deliverables
- **Attach the staleness of the index the caller is about to query** to the busy payload —
  `staleness`, `last_commit` and `head_commit` in the shapes `get_index_status` already uses, so a
  caller has one vocabulary, not two.
- **Preserve the no-DB-open property, or justify losing it.** The busy branch currently answers without
  touching the database, which is why it costs 0.0 s under contention. Reading staleness may require
  opening it. Measure the cost under N-way contention and record the decision; if the cost is real,
  a cheaper signal (e.g. reporting only that the answer is unverified) is acceptable and must be
  stated as such rather than silently substituted.
- **Say the request was not performed, in the reason vocabulary.** `reason: "another_build_running"`
  states the cause; nothing states the consequence. Whatever channel [033](033_nav-reason-codes.md)
  established for "this is not the answer you asked for" applies here too.
- **Decide whether busy should ever wait.** A bounded wait-and-retry inside the tool is one option;
  returning immediately with enough information for the caller to decide is the other. Pick one and
  record why. Do not do both.
- **State the operational rule in the docs.** The measured recipe is: refresh the index **once before
  dispatching a fan-out, never from inside an agent**. That is a docs deliverable of this ticket, not
  a code one.

## Constraints
- R4 — deterministic: the same lock state and the same index produce the same payload.
- R5.3 — busy is not a config error; it stays a normal, non-raising outcome. This ticket adds
  information to it, it does not turn it into a failure.
- 053 — lock semantics do not change. Exactly one writer, no corruption, no lock upgrade.
- 061 — the added fields land only on the busy payload, which is rare by construction.

## Acceptance criteria
- A busy refusal carries enough for the caller to distinguish "the index is current, proceeding is
  safe" from "the index is behind and a build is in flight".
- The successful build payload is unchanged.
- A test drives two concurrent builds and asserts the loser's payload contains the staleness signal
  and that exactly one build ran.
- The busy-branch latency under contention is measured and recorded before and after.
- `docs/` states the before-dispatch refresh rule for parallel agents.

## References
Memory/concurrency field run 2026-08-09 §5 ("concurrent rebuild — the deliberate separate trial"),
§9 fix #2 and the configuration table. `code_atlas/tools/build_or_update_index.py:53-62` (the busy
branch), `code_atlas/index_lock.py:19` (`try_index_write_lock`),
`code_atlas/tools/get_index_status.py` (the staleness vocabulary to reuse),
`code_atlas/hooks/refresh.py:49` (an existing consumer that already branches on `mode == "busy"`).
Related: [053](053_refresh-on-checkout-hook.md) (the lock), [033](033_nav-reason-codes.md),
[071](071_answers-do-not-name-their-tree.md) (the run's other silent-wrong-answer shape).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 072 — busy build hides staleness (working doc)

- **Ticket:** 072 · local `docs/tasks/072_busy-build-hides-staleness.md`
- **Type:** enhancement (agent-trust: add information to a payload)
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `1049 passed in 63.69s`, ruff clean, mypy clean (`scripts/docker-test.sh`, 2026-08-10). Bare `pytest` on this Windows host is red by the known `fcntl` platform exclusion (AGENTS.md); Docker is the authoritative suite.
  <!-- baseline exclusions (pre-existing failures outside this change): none -->

---

## Requirements matrix

`SECTIONS: 6 found (Goal, Evidence, Scope/Deliverables, Constraints, Acceptance criteria, References) | 6 decomposed (4 → rows; Evidence + References → context) | ROWS: C=4 R=5 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Make the refusal say what the caller is about to query." | The busy payload must carry the staleness of the index a losing caller is about to read, so a "refresh then investigate" agent is not misled into querying a stale index. | ticket L11–15; busy branch returns no staleness `build_or_update_index.py:53-62` | | | ❌ |
| R1 | Scope | "Attach the staleness of the index the caller is about to query … `staleness`, `last_commit` and `head_commit` in the shapes `get_index_status` already uses." | Busy payload gains `staleness`/`last_commit`/`head_commit` reusing `get_index_status`'s vocabulary (one vocabulary, not two). | `get_index_status.py:126-196` (`_status`, `_staleness`, keys) | | | ❌ |
| R2 | Scope | "Preserve the no-DB-open property, or justify losing it … Measure the cost under N-way contention and record the decision; if the cost is real, a cheaper signal … is acceptable and must be stated as such." | Keep the 0.0 s / no-DB-open busy branch if feasible; otherwise justify opening the DB, measure busy-branch latency under N-way contention, and record it. A cheaper "unverified" signal is allowed only if stated as such, not silently substituted. | ticket L54-58; no-DB-open at `build_or_update_index.py:53-62` | | | ❌ |
| R3 | Scope | "Say the request was not performed, in the reason vocabulary … Whatever channel [033] established for 'this is not the answer you asked for' applies here too." | Payload states the *consequence* (request not performed / not the refresh you asked for), not just the cause `another_build_running`, using the 033 reason-code channel. | ticket L59-61; `nav_result.py` reason vocab (033); refresh.py consumer `refresh.py:49` | | | ❌ |
| R4 | Scope | "Decide whether busy should ever wait … Pick one and record why. Do not do both." | Choose exactly one of {bounded wait-and-retry inside the tool} / {return immediately with enough info}; record the rationale. Not both. | ticket L62-64 | | | ❌ |
| R5 | Scope | "State the operational rule in the docs … refresh the index **once before dispatching a fan-out, never from inside an agent**. That is a docs deliverable." | Docs (README/PLAN/runbook) state the before-dispatch refresh rule for parallel agents. Docs-only deliverable. | ticket L65-67, L83 | | | ❌ |
| C1 | Constraint | "R4 — deterministic: the same lock state and the same index produce the same payload." | No wall-clock/random leaking into the payload's staleness fields; identical lock+index state → identical payload (latency aside). | ENGINEERING_RULES R4.2 | | | ❌ |
| C2 | Constraint | "R5.3 — busy is not a config error; it stays a normal, non-raising outcome. This ticket adds information to it, it does not turn it into a failure." | Busy still returns a dict, never raises; added fields are additive. | ENGINEERING_RULES R5.3; ticket L71-72 | | | ❌ |
| C3 | Constraint | "053 — lock semantics do not change. Exactly one writer, no corruption, no lock upgrade." | `try_index_write_lock` unchanged; still one writer; the loser must not upgrade the read to a write or touch `write.lock` semantics. | `index_lock.py:19-32`; ticket L73 | | | ❌ |
| C4 | Constraint | "061 — the added fields land only on the busy payload, which is rare by construction." | New fields appear only on `mode: busy`; the successful and refused payloads are untouched. | ticket L74; task 061 (rare-payload discipline) | | | ❌ |
| AC1 | AC | "A busy refusal carries enough for the caller to distinguish 'the index is current, proceeding is safe' from 'the index is behind and a build is in flight'." | Two-state proof: a busy refusal over a *current* index vs a *behind* index carries distinguishable staleness. | ticket L77-78 | | | ❌ |
| AC2 | AC | "The successful build payload is unchanged." | Full/incremental payload shape is byte-for-key identical to today; existing build-payload tests stay green. | ticket L79; `test_build_report_counts.py` | | | ❌ |
| AC3 | AC | "A test drives two concurrent builds and asserts the loser's payload contains the staleness signal and that exactly one build ran." | Concurrency test: two builders, one wins (built) one busy; assert staleness on the loser AND exactly one build executed. | ticket L80-81; pattern in `test_git_refresh_hook.py:109-126` | | | ❌ |
| AC4 | AC | "The busy-branch latency under contention is measured and recorded before and after." | Before = current (0.0 s, ticket evidence) and after = measured under N-way contention; both recorded in this working doc. | ticket L82; evidence L20-27 | | | ❌ |
| AC5 | AC | "`docs/` states the before-dispatch refresh rule for parallel agents." | Grep-able rule present in docs/. | ticket L83; = R5 | | | ❌ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 Q |
|-------|---------------|------------------------|--------|--------------|----------|
| AC1 | distinguish current vs behind | requires `staleness` field driven by `last_commit` vs `head_commit` (+dirty) — needs DB read for `last_commit` | Y | measurable (assert distinct field values across two planted lock+index states) | — |
| AC2 | success payload unchanged | additive change on busy branch only ⇒ success dict keys identical | Y | measurable (dict-shape assertion / existing tests green) | — |
| AC3 | staleness on loser + exactly one build | 2 builders → exactly one `mode∈{full,incremental}`, one `mode=busy` carrying staleness | Y | measurable (count builds == 1; assert field present) | — |
| AC4 | latency measured before/after | before = 0.0 s (evidence); after = measured N-way number recorded here | Y | recorded-artifact: falsifiable by presence of before/after numbers in this doc | — |
| AC5 | docs state the rule | grep docs/ for the refresh-before-fan-out rule | Y | measurable (grep) | — |

No acceptance-value mismatches; the only numeric value ("exactly one build ran" = 1) matches an independent read of the lock's single-writer guarantee (053). No uncodified standard is being applied — all judgments cite the ticket, 033/047/053, or ENGINEERING_RULES.

## Inventory (universal)

- No app-wide "all/every/no" requirement. R1/R3/R4 target **one** payload shape (`mode: busy`). Denominator **N = 1** (single branch, single payload).
- `TRACK: backend — 0/N touched files under UI paths`
- `SURFACES:` n/a (backend track, N=1).

`RULE SECTIONS: §1 ✅ (no lang branch; store owns SQL; tool presents) · §2 N/A (no adapter) · §3 N/A (MCP response shape ≠ contract JSONL version bump) · §4 ✅ (determinism C1) · §5 ✅ (R5.3 non-raising, C2) · §6 ✅ (fixture concurrency test) · §7 ✅ (smallest; docs) · §8 N/A (no deps)` — checked at design.

## Design decisions to settle at Gate 2 (either/or in the ticket; standing approval to pick the best)

1. **R2 — read staleness with or without opening the DB.** `last_commit` lives in DB meta, so distinguishing current/behind needs a read connection (WAL allows concurrent reads while the winner holds the write lock). Recommendation to prove at design: open a **read-only** connection for the meta + git head, measure the cost under N-way contention; if measurable and material, fall back to the cheaper "unverified" signal — stated as such. Reuse `get_index_status`'s `_staleness` helper (do not fork).
2. **R4 — wait or return-immediately.** Recommendation: **return immediately with enough info** (no bounded wait). A wait would fight 053's "no lock upgrade / one writer" and the operational rule (R5) already says refresh once before fan-out, never inside an agent — so the tool should inform, not block. Record why; do not do both.

`CLARIFICATION: 2 raised (the two either/or design decisions above) | 2 self-resolved via standing approval 2026-08-10 ("suggest and do the best option, pass all gates"), cited above | j=0 for human decision`

`STRUCTURE: native`
`SCOPE: M` — busy-branch staleness + a recorded decision + a concurrency test + docs; more than a one-line fix, well short of L.
`TIER: full` — SCOPE=M and two genuine design either/ors need the design gate; not lite-eligible.

### Root-cause / gap (enhancement)

| Goal | Current | Target | path:line |
|------|---------|--------|-----------|
| Loser learns what it will query | busy payload = `{mode, requested_full, reason, db_path, seconds}` — no staleness | + `staleness`/`last_commit`/`head_commit` (get_index_status vocab) | `build_or_update_index.py:53-62` |
| Loser learns the request was not performed | `reason: another_build_running` states cause only | + consequence in the 033 reason channel | `build_or_update_index.py:57-60` |
| Cost of the signal is known | no-DB-open 0.0 s; unmeasured if DB opened | measured N-way latency recorded | ticket evidence L20-27 |

### Blast radius

- Entry: `build_or_update_index` busy branch (`build_or_update_index.py:53-62`).
- Consumers: `refresh.py:49` already branches on `mode == "busy"` (a clean skip — additive fields are safe); MCP clients; `test_git_refresh_hook.py:109-126` asserts `mode`/`reason` (additive-safe).
- Reuse target: `get_index_status._staleness` / staleness keys (`get_index_status.py:188-196`) — extract or import, do not fork (R3-of-033 spirit: one vocabulary).
- Store: read-only `get_meta(LAST_COMMIT_KEY)`; no schema change, no new writer (C3).
- Out of scope: 071 (sibling), lock mechanics (053).

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| _(analysis dispatched no subagent — fan-out not needed for a single-branch backend change)_ | — | — | — |

## Decision log

| Phase | Decision | Note |
|-------|----------|------|
| Analysis | TIER=full, SCOPE=M, TRACK=backend | single busy-branch payload; N=1 |
| Analysis | Two design either/ors self-resolved via standing approval; recommendations recorded for Gate 2 | j=0 |

---

## Phase 2 — Design

### Approach

The busy refusal opens a **read-only** `GraphStore`, computes staleness with the **same helper**
`get_index_status` uses, and merges four fields into the busy payload: `staleness`, `last_commit`,
`head_commit` (R1) plus `performed: false` — the consequence in the 033 reason channel (R3), stated
beside the existing cause `reason: "another_build_running"`. To make it *one* vocabulary and not two,
the commit/dirty staleness computation is **extracted** from `get_index_status` into a small shared
module `code_atlas/tools/staleness.py`; `get_index_status` then imports (and re-exports) it, so both
callers share one source. The busy branch **returns immediately** with this info — no wait (R4).

**R2 decision (no-DB-open trade, to be measured at execute — AC4).** Distinguishing *current* from
*behind* requires `last_commit`, which lives in DB meta, so the busy branch **loses** the no-DB-open
property — a justified loss: WAL reads are independent of the `write.lock` fcntl flock (a separate
file), so a read-only connection neither blocks the winner nor raises `SQLITE_BUSY`, and returns the
last *committed* index state — exactly "what the caller is about to query". Cost is measured under
N-way contention and recorded (before 0.0 s / after) in the Decision log at execute; if the measured
cost is material the stated fallback is a commit-only signal, recorded as such — never silently
substituted.

**R4 decision — return immediately, no bounded wait.** A wait would fight 053 (one writer, no lock
upgrade) and the operational rule (R5: refresh once before fan-out, never inside an agent) already
says the tool should *inform*, not block. Exactly one option, recorded; not both.

### Rejected alternatives

- **Import `get_index_status`'s private `_staleness`/`_dirty_indexed` into the busy branch** —
  rejected: couples two tool modules through underscore internals and still leaves the vocabulary in
  `get_index_status`; the shared module is the honest single source (033-R3 spirit, R7.4).
- **Duplicate a commit-only staleness in the busy branch** — rejected: two implementations drift →
  the exact "two vocabularies" the ticket forbids; and it would disagree with `get_index_status` on
  dirty-tree cases.
- **Bounded wait-and-retry inside the tool** — rejected under R4: pushes the tool toward holding/
  upgrading the lock (053 violation) and duplicates the caller's own refresh-before-fan-out policy.
- **Keep no-DB-open, report only "unverified"** — rejected as the *primary* (it cannot satisfy AC1's
  current-vs-behind distinction); retained only as the measured fallback if the DB-read cost is material.

### Assumptions

| # | Assumption | Tag |
|---|------------|-----|
| A1 | A read-only `GraphStore` can read `last_commit` while the winner holds `write.lock` and is mid-build (WAL), without blocking or `SQLITE_BUSY`, returning the last committed value | **novel-untested → resolved** by the integration-shaped proving/AC3 tests (real concurrent build with the lock held; a block would hang the test, a raise would fail it) |
| A2 | `write.lock` (fcntl flock) is a separate file from `graph.db`, so reading the DB never touches that lock | verified (`index_lock.py:21-25`) |
| A3 | Additive busy-payload keys break no consumer: `refresh.py:49` branches only on `mode=="busy"`; `test_git_refresh_hook.py:109-126` asserts only `mode`/`reason` | verified |
| A4 | Extracting constants and re-exporting them from `get_index_status` keeps `from get_index_status import BEHIND, CURRENT, UNKNOWN` working | verified (`test_staleness_scope.py:18`) |
| A5 | `get_index_status` output is unchanged by the extraction (moves code, not behaviour) | verified by the untouched `test_staleness_scope.py`/`test_get_index_status_health.py` staying green |

No unresolved `novel-untested` runtime assumption remains: A1 is de-risked by an integration-layer proving test.

### Smallest change-list

| # | Change | File/area | Ph2 covered by | k/N |
|---|--------|-----------|----------------|-----|
| 1 | New shared module: constants `CURRENT/BEHIND/UNKNOWN`, moved `_staleness` + `_dirty_indexed`, public `compute_staleness(store, config) -> {staleness, last_commit, head_commit}` | `code_atlas/tools/staleness.py` (new) | R1, C1 | 2/2 |
| 2 | Import + re-export constants/helpers from the shared module; output identical | `code_atlas/tools/get_index_status.py` | R1 (single source), A4/A5 | 2/2 |
| 3 | Busy branch: open read-only `GraphStore` (guard no-DB / `SchemaVersionError` → `staleness=unknown`, best-effort commits, never raise), merge `staleness`/`last_commit`/`head_commit` + `performed: false` | `code_atlas/tools/build_or_update_index.py:53-62` | G1, R1, R3, R4, C2, C3, C4 | 7/7 |
| 4 | Proving + concurrency tests: lock-held current-vs-behind two-state; threaded two-builder "exactly one ran + loser carries staleness"; success-payload-unchanged assertion; `performed:false` | `tests/test_busy_build_staleness.py` (new) | AC1, AC2, AC3, G1, R1, R3 | 6/6 |
| 5 | Operational rule in docs (refresh once before fan-out, never inside an agent) + busy-payload fields documented | `README.md`, `docs/PLAN.md` (§12/§19) | R5, AC5, R7.2 | 3/3 |
| 6 | Decision-log rows: R2 measured N-way latency (before 0.0 s / after) + R4 no-wait rationale | this working doc | R2, AC4 | 2/2 |
| 7 | Bookkeeping: status→done in frontmatter + `docs/BACKLOG.md`; token row | task frontmatter, `docs/BACKLOG.md` | R7.2 | 1/1 |

**Test blast-radius (mechanical).** Grepped consumers of the moved symbols: `get_index_status`
constant imports (`test_staleness_scope.py:18`) stay valid via re-export (change 2); busy-payload
assertions (`test_git_refresh_hook.py:109-126`) assert only `mode`/`reason` — additive keys keep them
green; no snapshot/exact-dict test asserts the full busy payload. **No existing assertion is
invalidated** → no proof-collateral edit required.

### Rule compliance

`RULE SECTIONS: §1 ✅ (no lang branch; store owns SQL — busy branch only *reads* via GraphStore; shared module presents) · §2 N/A · §3 N/A (MCP response shape, not contract JSONL — no version bump) · §4 ✅ (C1: same index+tree → same payload; latency excepted) · §5 ✅ (R5.3/C2: busy never raises, guards degrade to unknown) · §6 ✅ (fixture concurrency test) · §7 ✅ (smallest; one shared module not a registry — R1.2/R7.4; docs updated) · §8 N/A`

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 distinguish current vs behind | integration | integration test: planted current index vs behind index, lock held, assert `staleness` differs & correct | ✅ |
| AC2 success payload unchanged | integration | integration test asserting success payload has no `performed`/staleness keys + existing build-payload tests green | ✅ |
| AC3 two concurrent builds, exactly one ran, loser carries staleness | integration/concurrency | threaded two-builder test (barrier + slowed build) counts exactly one `mode∈{full,incremental}`, one busy carrying staleness | ✅ |
| AC4 busy latency measured before/after | runtime | manual-recorded: before 0.0 s (evidence) / after = measured N-way number in Decision log at execute | ✅ (runtime measurement ↔ manual-recorded) |
| AC5 docs state the rule | logic/docs | grep `docs/` + README for the refresh-before-fan-out rule | ✅ |
| R2 decision (DB-open trade) | — | recorded in Decision log with the measured number | ✅ |
| R4 decision (no-wait) | — | recorded in Decision log | ✅ |

No layer-match `❌`; no coverage-gap exclusion needed.

### Named proving test

`tests/test_busy_build_staleness.py::test_busy_refusal_carries_staleness_of_the_index_it_will_query`

Fails today: the busy payload has no `staleness` key (`build_or_update_index.py:55-61`), so the
assertion `result["staleness"] in {CURRENT, BEHIND}` raises `KeyError`. Passes post-change.

Invocation (needs POSIX `fcntl` + PHP adapter → Docker; bare Windows `pytest` is the known exclusion):
`scripts/docker-test.sh pytest -q tests/test_busy_build_staleness.py`

### Rollback + porting

- **Rollback:** revert the four code/test files + doc edits; `staleness.py` is new (delete) and
  `get_index_status` reverts to inline helpers. No schema/data migration, so revert is clean.
- **Porting:** single repo (`app`); no shared cross-repo code. No adapter touched (backend core only).

### SCOPE re-affirm

`SCOPE: M` — unchanged from analysis. One shared-module extraction + one busy-branch edit + one test
file + docs. Not L: no new subsystem, no schema change, no lock-semantics change (C3). No
outgrew-its-ticket condition; branch type `feat` matches an additive enhancement.

### Gate 2 status
Ready — every change-list item traces to a matrix row, all assumptions tagged (A1 de-risked by an
integration proving test), proving test named + runnable, verification plan has no `❌`. **Awaiting
approval** (standing approval to pick best option + pass gates).

---

## Phase 3 — Execute

- **Branch:** `feat/072-busy-build-hides-staleness`
- **Proving test:** `tests/test_busy_build_staleness.py::test_busy_refusal_carries_staleness_of_the_index_it_will_query` — PASS (raises `KeyError` pre-change: no `staleness` key)
- **Suite (Docker):** `1056 passed in 67.46s` — baseline 1049 + 4 new tests + 2 parametrized guard rows + 1. ruff clean, mypy clean.

### AC4 — busy-branch latency, measured (before / after)

| | busy-branch cost | staleness |
|--|------------------|-----------|
| **Before (ticket evidence)** | 0.0 s — returned without opening the DB or touching git | none carried |
| **After (measured, 4-way contention, 3000-file git tree, Docker)** | **0.030–0.041 s/call** (4 concurrent losers; wall 0.0425 s) | correct `current` |
| DB-open component alone (non-git tree) | ~0.007 s | — |

The no-DB-open property is **deliberately traded** (R2) for a read-only staleness read whose cost is
one `git status` + `rev-parse` + one meta `SELECT` — ~30–40 ms on a 3k-file tree, dominated by git,
not the DB. On the anchor repo (~19k files) this extrapolates to sub-second, still negligible against
the 83 s build it warns about. WAL reads are independent of the winner's `write.lock` (fcntl) flock,
so the read never blocks the winner nor raises `SQLITE_BUSY` (assumption A1, proven by AC3 test). The
cheaper commit-only fallback was **not** needed — the measured cost is immaterial.

### R4 — decision recorded

Busy **returns immediately** with the staleness info; **no** bounded wait. Rationale: a wait would
push the loser toward holding/upgrading the lock (053 forbids), and the operational rule (R5) already
says refresh once before fan-out, never inside an agent. One option chosen, not both.

### Design-conformance (Approach bullets)

| # | Bullet | Status |
|---|--------|--------|
| 1 | Busy opens read-only `GraphStore`, staleness via shared helper, adds 3 fields + `performed:false` | implemented-as-approved |
| 2 | Extract `staleness.py`; `get_index_status` imports + re-exports (output unchanged) | implemented-as-approved |
| 3 | Return immediately, no wait (R4) | implemented-as-approved |
| 4 | R2 no-DB-open trade measured + recorded (AC4) | implemented-as-approved |
| 5 | Guarded degrade to `unknown` on no-DB / schema mismatch, never raise (C2) | implemented-as-approved |
| 6 | Docs state the before-dispatch rule (R5/AC5) | implemented — see deviation note |

### Verification sweep

- **Axis 1 (file set):** 9 files. 7 ⊆ approved list (staleness.py, get_index_status.py,
  build_or_update_index.py, test_busy_build_staleness.py, PLAN.md, working doc, + runbook under
  "docs"). **2 beyond the named list** — `test_core_is_language_agnostic.py` +
  `test_sql_confinement.py`, each a **+1-line guard-count bump** (`36 → 37`) forced by the new core
  module `staleness.py`. Mechanical proof collateral; the design's blast-radius grep matched moved
  *symbols*, not the pinned module-count guards. **Surfaced to review.**
- **Axis 2 (behaviour):** all 6 approach bullets implemented-as-approved; 1 doc-placement deviation.
- **Deviations (for review adjudication):**
  1. Two guard-count files edited beyond the named change list (mechanical, +1 line each).
  2. **Doc placement:** change #5 named `README.md`; the refresh-before-fan-out rule already lives in
     `docs/runbooks/parallel-agents.md` (README links to it), so I strengthened the runbook + PLAN
     §12/§19 rather than duplicating the rule into README. R5/AC5 satisfied; README unchanged.
- **SCOPE:** stays **M** — no tier crossing; diff does not materially exceed the approved list.

### Ph3/4 proven by (matrix delta)

G1, R1, R3, R4, C2, C3, C4, AC1, AC2, AC3 → `tests/test_busy_build_staleness.py` (4 tests) + suite;
R2, AC4 → measured latency recorded above; R5, AC5 → runbook + PLAN docs; C1 → determinism (same
index+tree → same payload, staleness is a pure function of committed meta + git state).

---

## Phase 4 — Review

**Waived** per run args (`with skipped review`). No `mango:reviewer` / `mango:challenger` dispatched.
The two execute deviations were self-adjudicated (both benign): the guard-count bumps are mandatory
for a new core module; the doc rule lives in the runbook README links to, not README itself.

## Phase 5 — Finalise

- **Bookkeeping:** status → done (frontmatter + BACKLOG); token row added; lesson recorded.
- **Outward (user-approved + standing maintainer authorization):** push `feat/072-busy-build-hides-staleness`, open PR.

### Cost ledger (dispatch)

`LEDGER: 0 dispatch rows | 0 subagents ran (review waived, no fan-out) | complete`. Main-loop spend is
unmeasured — mango measures subagent dispatch only.

### Durable lesson
A change that adds/removes a core module must grep **pinned counts** (`len(...) == N`, parametrize
sources), not just moved symbols — the two `== 36` guard tests broke on the new `staleness.py` and
surfaced only at the full-suite run. Recorded in `docs/LESSONS.md` (072).

---

## Session status

- **Ticket:** 072
- **work_doc_mode:** embed
- **working-doc path:** `docs/tasks/072_busy-build-hides-staleness.md`
- **Current phase:** finalise — complete (PR #89)
- **Blocked on:** none
- **PR:** https://github.com/cuongdinhngo/code-atlas/pull/89
- **Next action:** none (await review/merge)
- **Revert path:** branch `feat/072-busy-build-hides-staleness` (commits `07017c8`, `0d070df`, `3b5d89c`, `e5415c1`); undo = close PR + delete branch. No schema/data migration.
