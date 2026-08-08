---
id: 054
slug: bare-name-callers-silent-drop
title: '`find_callers` reports `total_count: 0` for a method that has callers, because bare-name resolution silently keeps only the first N declarations'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [011, 013, 046]
---

## Goal
A field session asked `find_callers` for a model's `save` method and got
`{"results": [], "total_count": 0, "reason": "no_matches", "truncated": false}`. Six call sites exist.
The session only discovered this because it grepped out of habit; had it believed the payload — which
is what the repo's own mandatory-use policy tells an agent to do — it would have concluded the method
was dead code, in a session whose entire subject was that method being called wrongly.

**The cause is not missing type inference.** That was the field session's diagnosis and it is wrong.
The adapter *does* emit the edge: for `$var->save()` where `$var` is not `$this`,
`Visitor.php:551-553` emits `CALLS` with `target_raw = "save"` — the bare method name — at tier
`HEURISTIC`. The row is in the table.

The loss happens in the resolver. Bare-name `CALLS` that no FQN lookup matched fall through to
`resolver.py:82-84`:

```python
method_hits = store.nodes_by_names(call_raws, kind="Method", limit=max_candidates)
```

`max_candidates` is `config.max_results` (`indexer.py:216`), and `nodes_by_names` returns the
**per-name top-`limit`** rows ordered by `_NODE_ORDER = "qualified_name, file_path, line_start, id"`
(`store.py:112`). So for a method name declared by more than `max_results` classes, only the
**alphabetically first `max_results` declarations** ever receive an inbound edge. Every other class is
invisible to `find_callers` for every bare-name call site, permanently.

On the anchor repo `max_results` is 10. `save`, `get`, `handle`, `run` are declared by far more than
ten classes. This is not an edge case on that repo — it is the default outcome, and which classes win
is decided by their qname's position in the alphabet.

**Two properties make it worse than a coverage gap.** It is *silent* — `relation_reason`
(`nav_result.py:153-159`) correctly reports `no_matches` because the subject is indexed and genuinely
has no inbound edges *recorded*, so the payload is internally honest and externally false. And it is
*systematic* — the same subject fails the same way on every run, so an agent cannot learn to distrust
it from variance.

It also explains why `find_implementations` was correct in the same session: `EXTENDS`/`IMPLEMENTS`
resolve through `nodes_by_qualified_names`, never through the bare-name path.

## Scope — split deliberately, and the second half is gated

This ticket has two halves with very different risk. **They ship separately.**

### Part B — say what was dropped (do this first, unconditionally)
- **Count the candidates the cap discarded** and carry that count to the caller. A subject whose
  inbound call-shaped edges were dropped, or whose bare-name lookup was truncated, must never return a
  bare `total_count: 0`.
- **Surface it on `find_callers`** alongside the existing `frontier_skipped_non_resolved`, so an empty
  result can say *"0 resolved callers, N call sites recorded but unlinked"* — which turns a false
  negative into a correct hand-off to grep.
- **Decide where the number lives.** The candidate drop happens at index time and the query happens
  later, so either the resolver records it (a column or a meta counter) or the query counts unlinked
  call-shaped edges whose `target_raw` matches the subject's bare name. Prefer whichever keeps SQL in
  the store (R1.4) and costs nothing on the hot path.
- **Correct regardless of anything else.** This half does not depend on the benchmark below and must
  not wait for it.

### Part A — stop dropping them (gated on the three-way benchmark)
- Separate the **resolution budget** from the **response budget**. `max_results` is a payload cap;
  reusing it to decide how much of the graph gets built is a category error, and it is why a
  presentation default silently governs recall.
- **Gated, and the gate is real.** [046](046_resolver-qname-candidate-dedupe.md) cut the anchor repo
  from 2,836,428 edges to 1,774,891 *by limiting candidates*. Raising the cap re-inflates that: a bare
  name declared by 200 classes would emit up to 200 sibling rows per call site, across hundreds of
  thousands of call sites. Any change here must be measured on the anchor repo before it is believed,
  at ~17 minutes per rebuild.
- **The benchmark may make this unnecessary.** If a language-server-backed tool is decisively better
  at semantic resolution, the right answer is to concede depth and let Part B hand the question off
  honestly, rather than to chase recall by inflating the graph. Do not start Part A before that result
  is in.

## Constraints
- **No adapter change.** The edge is already emitted correctly; this is core-side (R1.1 — and the fix
  must not teach the core anything about PHP).
- **SQL stays in the store (R1.4).**
- **Never promote a weaker tier (R5.2).** A bare-name match is `HEURISTIC` and stays so.
- **Determinism (R4.2)** — whatever is counted must be identical across two runs on one tree.
- **`get_index_status` stays cheap** — no new aggregate on the status path.
- **Part B adds no measurable cost to the query path.** A field that costs a second query per nav call
  is not worth the honesty.

## Acceptance criteria
- On a fixture where a method name is declared by more than `max_results` classes and a call site
  targets one of the ones outside the cap: `find_callers` returns a payload that **states the subject
  has unlinked call-shaped edges**, and a test asserts the payload is not a bare
  `total_count: 0` / `no_matches`.
- The fixture asserts the drop is real (a declaration outside the cap exists), so the guard cannot pass
  vacuously — same discipline as `test_the_fixture_really_produces_siblings` in
  [051](051_build-report-edge-undercount.md).
- Two runs over one tree report identical counts (R4.2).
- Part A is **not** implemented in this ticket unless the benchmark result is recorded here first,
  with the measured edge-count impact on the anchor repo.
- `pytest`, `ruff`, `mypy` green.

## References
`adapters/php/src/Visitor.php:533-554` (`enterInstanceCall` — `$this` resolves to an FQN, everything
else emits the bare method name at `HEURISTIC`).
`code_atlas/resolver.py:77-88` (the bare-name fallback), `:18-35` (`resolve_edges` signature and the
`max_candidates` parameter).
`code_atlas/store.py:112` (`_NODE_ORDER`, the alphabetical tie-break that decides who wins),
`nodes_by_names` (per-name top-`limit`).
`code_atlas/indexer.py:216` (`max_candidates=config.max_results` — where a display cap becomes a
resolution cap); `code_atlas/config.py:44` (`DEFAULT_MAX_RESULTS = 50`; the anchor repo sets 10).
`code_atlas/tools/nav_result.py:153-159` (`relation_reason` — why the empty answer is internally
honest); `code_atlas/tools/find_callers.py` (`frontier_skipped_non_resolved`, the existing precedent
for a counter that explains an incomplete answer).
Scale precedent and the gate on Part A: [046](046_resolver-qname-candidate-dedupe.md) outcome table.
Payload-honesty precedent: [048](048_edge-health-resolved-ambiguity.md),
[050](050_schema-version-mismatch-recovery.md) (no empty `results` beside an error).
Origin: field retro round 2 §4 — reported there as a missing-type-inference limitation; the resolver
cap is the actual mechanism, found by reading the path afterwards.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 054 — bare-name-callers-silent-drop (working doc)

- **Ticket:** 054 · local `docs/tasks/054_bare-name-callers-silent-drop.md`
- **SCOPE:** M · **TIER:** full · **STRUCTURE:** native · **TRACK:** backend
- **BASELINE:** green area — proving + resolver/nav tools; full suite at review
- **work_doc_mode:** embed
- **working-doc path:** this file below separator

## Phase 0 — Refine

`REFINE: 1 want asked | W1=A Part B only (standing) | 3 ASSUMED from exposure | skip: no`

**ASSUMED (standing approval after exposure-checker):**
1. Honesty metric = distinct CALLS sites with `target_raw`=bare name that never target this subject
2. Empty case → `reason=bare_name_truncated` + `unresolved_bare_calls` (not bare `no_matches`)
3. Emit field whenever count > 0; Part A out

**Exposure-checker:** [Challenger](2414f1de-7f0f-480b-b260-c0b1265480c4)

## Requirements matrix (Part B only)

`SECTIONS: 5 | ROWS: C=5 R=4 G=2 AC=5` · `j=0` · Gate 1 cleared (standing)

| ID | Interpretation | Status |
|----|----------------|--------|
| R1–R3 | Part B honesty counter on find_callers | ✅ |
| R4 | Part A gated out | ✅ (not implemented) |
| C1–C5 | No adapter; store SQL; HEURISTIC; R4; status cheap; cheap count | ✅ |
| AC1–AC3 | Fixture + truncated reason + deterministic | ✅ |
| AC4 | Part A not in this ticket | ✅ |
| AC5 | green suite | ✅ |

- **Gate 1/2:** cleared — standing approval 2026-08-08

## Phase 2 — Design (approved)

| # | Change | Path |
|---|--------|------|
| 1 | `count_bare_calls_not_targeting` | `code_atlas/store.py` |
| 2 | `bare_name_truncated` + field wiring | `nav_result.py`, `find_callers.py` |
| 3 | Proving tests (drop real + honesty + deterministic) | `tests/test_bare_name_callers_silent_drop.py` |
| 4 | NAV_REASONS vocabulary test | `tests/test_nav_reason_codes.py` |
| 5 | BACKLOG/frontmatter | docs |

**Proving test:** `test_find_callers_reports_truncated_bare_name_not_no_matches`

## Phase 3 — Execute

- Branch: `fix/054-bare-name-callers-silent-drop`
- Commits: `221f07e` (feat), `5092201` (review: indexed+empty-only count)
- Proving: 5 tests in `test_bare_name_callers_silent_drop.py` + vocabulary — green

## Phase 4 — Review ✋

- reviewer: **CHANGES REQUESTED** → verify-only **LGTM** ([Reviewer](b3f00b88-7934-4cbe-b075-ae1939de7a91) → [Reviewer](b286671d-7e53-4f0e-909d-64ef04349bd7)) @ `5092201`
- challenger (ticket-blind): **12 met · 1 not met** → mitigated by empty-only count ([Challenger](63eb9ef5-839c-42d4-89d7-5077dc17b03a))
- Scope reconciliation: diff ⊆ approved Part B list ✅ (no Part A / adapter / resolver budget change)
- Proving: 5 tests in `test_bare_name_callers_silent_drop.py` + vocabulary; full suite **901 passed**
- **Clean?** yes
- **Reviewed at:** `5092201` · files: `code_atlas/store.py`, `code_atlas/tools/find_callers.py`, `code_atlas/tools/nav_result.py`, `tests/test_bare_name_callers_silent_drop.py`, `tests/test_nav_reason_codes.py`, `docs/BACKLOG.md`, `docs/tasks/054_bare-name-callers-silent-drop.md`

### Reviewer detail — round 1 ([Reviewer](b3f00b88-7934-4cbe-b075-ae1939de7a91)) @ `221f07e`

**Verdict: CHANGES REQUESTED** (conditional LGTM). Critical: none.

| # | Finding | Path | Fix |
|---|---------|------|-----|
| 1 | `unresolved_bare_calls` emitted for unknown qnames (`\Typo::put` + bare `put` sites → `no_such_symbol` plus a positive count) | `find_callers.py` | Gate count on `indexed` (and empty-only SQL) |

**Scope check:** approved Part B files only; R1.1/R1.4/R5.2; Part A absent ✅.

### Challenger detail ([Challenger](63eb9ef5-839c-42d4-89d7-5077dc17b03a)) — ticket-blind @ `221f07e`

Rebuilt from raw ticket + `main...fix/054-bare-name-callers-silent-drop` only.

**Summary: 12 met · 1 not met · 0 can’t-tell**

| # | Requirement | Verdict |
|---|-------------|---------|
| 1–7, 9–13 | Part B count/surface/reason/store SQL/no adapter/R5.2/R4/status cheap/Part A out/ACs/suite | **met** |
| 8 | Part B adds no second query per nav call | **not met** (always ran `count_bare_calls_not_targeting` for method qnames) |

### Reviewer detail — verify-only ([Reviewer](b286671d-7e53-4f0e-909d-64ef04349bd7)) @ `5092201`

**Verdict: LGTM.** Finding 1 fixed (`indexed and total_count == 0`); unknown-qname regression test present; hot path skips honesty SQL on hits.

**Challenger #8 mitigation:** count SQL only when `indexed and total_count == 0` — empty truncated case still honest; winners and typos pay no extra query.

## Phase 5 — Finalise ✋

- Outward actions (approved 2026-08-08): push ✅ · open PR [#65](https://github.com/cuongdinhngo/code-atlas/pull/65) ✅ · status→done + token row ✅
- Follow-up deferred: Part A (resolution budget) still gated on anchor benchmark in-ticket
- Revert path: revert branch commits; close [#65](https://github.com/cuongdinhngo/code-atlas/pull/65)

## Session status

- **Last updated:** 2026-08-08
- **Current phase:** Phase 5 — Finalise complete (awaiting merge)
- **Next action:** none (PR open)

---

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 0 | exposure-checker Challenger ([Challenger](2414f1de-7f0f-480b-b260-c0b1265480c4)) | 1 | unmeasured (blocking retrieval) | — |
| 4 | mango:reviewer ([Reviewer](b3f00b88-7934-4cbe-b075-ae1939de7a91)) | 1 | unmeasured (blocking retrieval) | — |
| 4 | mango:challenger ([Challenger](63eb9ef5-839c-42d4-89d7-5077dc17b03a)) | 1 | unmeasured (blocking retrieval) | — |
| 4 | mango:reviewer verify ([Reviewer](b286671d-7e53-4f0e-909d-64ef04349bd7)) | 2 | unmeasured (blocking retrieval) | — |

`LEDGER TOTAL: 4 dispatch rows · all unmeasured (blocking retrieval) · top cost driver: review`

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-08-08 | W1=A Part B only | Standing + recommended |
| 2026-08-08 | ASSUMED metric/reason/emit | Standing after exposure |
| 2026-08-08 | Count only indexed+empty | Reviewer finding 1 + challenger #8 |
| 2026-08-08 | Gate 4 clean | LGTM @ `5092201` |
| 2026-08-08 | Finalise push+PR approved | user: add review detail, commit, push, open PR |
