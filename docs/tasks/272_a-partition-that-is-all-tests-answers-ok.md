---
id: 272
slug: a-partition-that-is-all-tests-answers-ok
title: 'Every honesty escalation in `find_callers` is gated on `total_count == 0`, so a subject whose only linked callers are tests answers `reason: ok` with `production_count: 0` — the exact signature of dead production code — while its sibling method, unreachable for the same reason, answers `relation_unmodelled_for_language`; make a zero *partition* as honest as a zero *answer*'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [262, 255, 264]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 20 §4)

Two methods on one class, both called exactly once from production, both through the same untyped
property (`$this->model = new CaseRegisterModel()`). The resolver types neither. The payloads:

| Subject | `reason` | rows | reality |
|---|---|---|---|
| `…::getCaseTranHistory` | `relation_unmodelled_for_language` + *"treat the empty answer as unmeasured, not as zero"* | 0 | one production caller |
| `…::getPathforRiskMatrix` | **`ok`**, `production_count: 0`, `test_count: 2` | 2 | one production caller |

The second resolves two callers only because the *test* helper declares a return type
(`private function createModel(…): CaseRegisterModel`). So the rule in practice is: **a declared
type links, an untyped property drops.** When every caller drops, the payload says unmeasured. When
only the production callers drop, it says `ok`.

The mechanism is in one place. `unlinked_calls` (`find_callers.py:428–441`), the shared 264 predicate
(`:442–452`) and the whole reason chain (`:469–482`) are each gated on `outcome.total_count == 0`.
A non-empty hit set skips all of them, and the partition 262 added (`:519–523`) is then emitted beside
`reason: ok` with no honesty pass of its own.

`authoritative: false` does not save it: it was on this payload too, as it is on almost every payload
in a multi-language repo ([276](276_the-caveat-that-fires-on-every-answer.md)).

## Scope / Deliverables

- **The honesty predicate runs on the partition, not only on the total.** When `production_count == 0`
  and the subject is indexed, the same evidence 255/264 already gather must run — unlinked inbound
  edges naming this subject, bare-name truncation, the cross-language census — and decide the
  reason. A partition that cannot be falsified stays `ok`.
- **A reason that names the shape.** `production_count: 0` beside surviving test rows is not
  `no_matches` and not a bare `ok`. Whatever word the vocabulary gains, it must carry the same
  *"unmeasured, not zero"* route the empty case already carries.
- **Count what falsifies it, and say the number.** The evidence exists: unlinked same-name call sites
  are countable today (`store.count_unlinked_by_target_raw`). A `production_count: 0` answer that also
  carries `unlinked_same_name_sites: 1` is one an agent cannot misread.
- **Same treatment in `find_references`** — same partition, same gate.

## Constraints

- **No new resolution.** Typing `$this->prop->method()` is [a separate ticket](#references) and a
  harder one; this ticket changes only what the payload says about what it already knows.
- R5.6: evidence, not inference. No route is named on a silence — a language that emits no inbound
  kind for this subject says so from the stamp, never from a guess.
- R4.2: the added counts are derived from stored rows, byte-reproducible.
- 061: nothing new on a payload that has nothing to add — a partition with production rows is unchanged.

## Acceptance criteria

- A fixture with one unlinked production call site and one *typed* test caller returns
  `production_count: 0` and a reason that is **not** `ok`, carrying the count of unlinked same-name
  sites.
- The same fixture with the production call site linked returns `reason: ok` unchanged.
- A subject with genuinely no production callers and no unlinked evidence still returns `ok` — the
  ticket must not make a true zero unsayable.
- `find_references` gets the same test.
- No existing `relation_unmodelled_for_language` case changes wording or route.

## References
`code_atlas/tools/find_callers.py:428–482,519–523`, `code_atlas/tools/find_references.py:292`,
`code_atlas/store.py` (`count_unlinked_by_target_raw`), field retro round 20 §4 / §9,
round 22 §4 (the honest arm, working as intended),
[262](262_the-contract-marks-test-code-and-no-tool-reads-it.md),
[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md),
[264](264_the-honesty-predicate-is-still-one-language-s-shape-wearing-a-constant-s-name.md),
[276](276_the-caveat-that-fires-on-every-answer.md).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 272 — a partition that is all tests answers ok (working doc)

- **Ticket:** 272
- **Type:** bug
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 touched files under UI paths
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed · path: docs/tasks/272_a-partition-that-is-all-tests-answers-ok.md

---

## Phase 0 — Refine

`PREMISE: 11 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**Recalled claims (advisory):**
| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | 258-C2 / R5.6 | 2 | handle `do-not-attest-past-the-payloads-resolution` | yes — `reason: ok` attests a modelled zero while production callers dropped |
| 2 | 196-C1 | 2 | handle `gate-on-the-invariant-not-on-presence` | yes — honesty gated on `total_count == 0` (presence of an empty answer) not on the partition |
| 3 | 186-C1 | 2 | handle `evidence-shaped-honesty-inverts-on-a-second-instance` | weigh — reuse 255/264 evidence; do not invent a second predicate |

**refine skipped:** 0 unresolved product-decisions. Ticket locks: honesty on `production_count == 0` when indexed; reason not `ok` and not `no_matches`; carry unlinked same-name count; same gate in `find_references`; true zero stays `ok`; existing `relation_unmodelled_for_language` cases unchanged; no new resolution.
**INPUT KIND:** ticket.

**Premise detail (m=0):** `find_callers.py` 428–441 / 442–452 / 469–482 / 519–523; `find_references.py`; `store.count_unlinked_by_target_raw`; tickets 262, 255, 264, 276.

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | honesty gated on `total_count == 0`; partition-zero answers `ok` | run the 255/264 evidence on a zero *partition* | D1–D3 | `find_callers.py:451,457` | ✅ |
| C1 | Constraints | no new resolution | payload wording only; untyped `$this->prop->method()` stays unlinked | — | no resolver change | ✅ |
| C2 | Constraints | R5.6: evidence, not inference | escalate only when stored unlinked/bare/census evidence exists | D1 | `nav_result.py:442` | ✅ |
| C3 | Constraints | R4.2: counts from stored rows | `unlinked_same_name_sites` from `count_unlinked_by_target_raw` | D2 | `find_callers.py:454` | ✅ |
| C4 | Constraints | 061: nothing new with nothing to add | production rows present → payload unchanged; field omitted on a true zero | D2 | AC2, AC3 | ✅ |
| R1 | Scope | honesty predicate on the partition | when `production_count == 0` and indexed, run unlinked / bare-name / census | D1 | AC1, AC3 · E1 census | ✅ |
| R2 | Scope | a reason that names the shape | not `ok`, not `no_matches`; same unmeasured route as the empty case | D1 | AC1 | ✅ |
| R3 | Scope | count what falsifies it | `unlinked_same_name_sites` on the partition-zero answer | D2 | AC1 | ✅ |
| R4 | Scope | same treatment in `find_references` | same partition gate | D3 | `find_references.py:379` | ✅ |
| AC1 | AC | one unlinked prod call + typed test caller → `production_count: 0`, reason ≠ `ok`, carries unlinked count | fixture | D1–D3 | `test_partition_zero_honesty.py` | ✅ |
| AC2 | AC | same fixture with production linked → `reason: ok` unchanged | fixture | D1 | proving | ✅ |
| AC3 | AC | genuine no-prod callers and no unlinked evidence still `ok` | fixture | D1 | proving | ✅ |
| AC4 | AC | `find_references` gets the same test | fixture | D3 | proving | ✅ |
| AC5 | AC | no existing `relation_unmodelled_for_language` case changes wording or route | existing honesty tests stay green | D1 | proving | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

**AC validation (all falsifiable, no manual-check exclusion):**
| AC | Stated | Re-derived | Match |
|----|--------|------------|-------|
| AC1 | production_count 0, reason not ok, unlinked count present | seed unlinked CALLS + typed test CALLS; assert those three | yes |
| AC2 | reason ok when production linked | same fixture with target_qname set | yes |
| AC3 | true zero stays ok | test-only callers, no unlinked rows | yes |
| AC4 | find_references same | same fixtures on that tool | yes |
| AC5 | existing unmodelled cases unchanged | `tests/test_relation_unmodelled_for_language.py` + empty-answer suite | yes |

**Universal inventory N=2** (R4 "same treatment"): find_callers · find_references — one proof row each, not an aggregate.

---

## Phase 1 — Analysis

- Root cause (bug, `logic`): `code_atlas/tools/find_callers.py:428–482` and `find_references.py:324` gate honesty on `total_count == 0` / `reason == no_matches`. A non-empty test-only hit set skips every arm; `_test_census` then emits `production_count: 0` beside `reason: ok`.
- TRACK: backend — 0/0 UI · SCOPE: M · TIER: full (N=2 tools, not a single-file lite)

`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — R5.5 (change-type) ✅ count sourced from store.count_unlinked_by_target_raw · R4.2 (change-type) ✅ stored-row counts · R6.1 (change-type) ✅ fixture tests on both tools · R1.1 (change-type) ✅ reuse inbound_kinds_for with no language branch · R3.5 (change-type) N/A because nav payloads have no version constant (262 optional-field precedent) · R5.6 (recalled-handle) ✅ do not attest ok when production callers dropped`

`TRACK: backend — 0/0 touched files under UI paths`

### BASELINE

```
Ran at 4585e269c73870724079d3e3837069f88232e229
$ .venv/bin/python -m pytest tests/test_callers_test_role_census.py tests/test_honesty_predicate_derived_mapping.py tests/test_relation_unmodelled_for_language.py tests/test_empty_answer_cannot_explain_itself.py tests/test_find_callers_cross_language_unmodelled.py -q --tb=no
203 passed in 11.35s
```

`BASELINE: green`

---

## Phase 2 — Design

- Approach: when `production_count == 0` and the subject is indexed, count unlinked same-name inbound via `store.count_unlinked_by_target_raw` and run the existing 255/264 evidence (shared honesty, bare-name, cross-lang census) even if `total_count > 0`. Escalate `reason: ok` onto the same unmeasured reason the empty case already uses (`relation_unmodelled_for_language` / `relationship_not_modelled` / `bare_name_truncated`). Attach `unlinked_same_name_sites` only when the count is > 0 (061). New helper `escalate_zero_production` in `nav_result.py` so `apply_empty_inbound_honesty` stays `no_matches`-only (find_implementations / include_graph unchanged). Same gate in `find_references`.
- Rejected: a new NavReason token (R3 bump + R6.7 registry for a synonym of the empty-case route). Rejected: widening `apply_empty_inbound_honesty` to accept `ok` (would change find_implementations / include_graph, which have no partition).

Assumptions: unlinked CALLS/REFERENCES rows with empty `target_qname` are already stored — verified (`count_unlinked_by_target_raw` / `unlinked_kinds_by_target_raw`). No novel-untested 3p/runtime assumption.

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `do-not-attest-past-the-payloads-resolution`: traced — honesty elifs keyed on `REASON_NO_MATCHES` while the partition is emitted beside `ok`. Folded into D1–D3.

```
Ran at 4585e269c73870724079d3e3837069f88232e229
$ rg -n "reason == REASON_NO_MATCHES" code_atlas/tools/find_callers.py code_atlas/tools/find_references.py
code_atlas/tools/find_references.py:324:            if reason == REASON_NO_MATCHES and nodes:
code_atlas/tools/find_references.py:335:                    reason == REASON_NO_MATCHES
code_atlas/tools/find_callers.py:477:        elif reason == REASON_NO_MATCHES and unlinked_calls > 0:
code_atlas/tools/find_callers.py:479:        elif reason == REASON_NO_MATCHES and cross_lang_census is not None:
code_atlas/tools/find_callers.py:483:        elif reason == REASON_NO_MATCHES and shared_unlinked:
```

- `gate-on-the-invariant-not-on-presence`: traced — evidence gated on `total_count == 0`. Folded into D2–D3.

```
Ran at 4585e269c73870724079d3e3837069f88232e229
$ rg -n "total_count == 0" code_atlas/tools/find_callers.py code_atlas/tools/find_references.py
code_atlas/tools/find_callers.py:430:                outcome.total_count == 0
code_atlas/tools/find_callers.py:442:                outcome.total_count == 0
code_atlas/tools/find_callers.py:474:        elif outcome.total_count == 0 and indexed and unresolved_bare > 0:
code_atlas/tools/find_references.py:253:            if total_count == 0 and not indexed:
```

- `evidence-shaped-honesty-inverts-on-a-second-instance`: traced — reuse `apply_empty_inbound_honesty`; do not add a second evidence-keyed predicate. Other callers (`find_implementations`, `include_graph`) stay out of the change list.

```
Ran at 4585e269c73870724079d3e3837069f88232e229
$ rg -n "apply_empty_inbound_honesty" code_atlas/tools/
code_atlas/tools/find_references.py:327
code_atlas/tools/find_implementations.py:130
code_atlas/tools/nav_result.py:423
code_atlas/tools/find_callers.py:448
code_atlas/tools/include_graph.py:107
```

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- E1: census does not rewrite `reason` on a non-empty hit set (238 already attaches it as a caveat). Ticket asked to "run census and decide reason"; flipping `ok` here would reverse 238. Unlinked + 264 + bare-name still decide. expiry: 2026-12-14.

**Verification plan**

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|------------|----------------|--------------------|--------------|
| AC1 | integration | integration | authored | ✅ |
| AC2 | integration | integration | authored | ✅ |
| AC3 | integration | integration | authored | ✅ |
| AC4 | integration | integration | authored | ✅ |
| AC5 | integration | integration | authored | ✅ |

No input-shape-dependent AC (each names `reason` / counts). no real corpus is configured; none needed.

**Proving test:** `.venv/bin/python -m pytest tests/test_partition_zero_honesty.py -q`

| # | Change | File | Blast | Ph2 | k/N |
|---|--------|------|-------|-----|-----|
| D1 | `escalate_zero_production` helper | `code_atlas/tools/nav_result.py` | find_callers + find_references only; honesty helper unchanged | G1 R1 R2 C2 | 4/4 |
| D2 | gather unlinked count when production_count==0; escalate from ok; attach field | `code_atlas/tools/find_callers.py` | `test_callers_test_role_census.py` AC3 cases stay ok | AC1 AC2 AC3 AC5 C3 C4 | 6/6 |
| D3 | same gate | `code_atlas/tools/find_references.py` | `test_find_references_carries_census` stays ok | R4 AC4 | 2/2 |
| D4 | proving fixtures (unlinked+test / linked / true-zero) for both tools | `tests/test_partition_zero_honesty.py` | none identified | AC1–AC5 | 5/5 |
| D5 | backlog/ledger/task status + P1 seen: | docs/BACKLOG.md, docs/TOKEN_LEDGER.md, docs/LESSONS.md, task frontmatter | tests/test_backlog_bookkeeping.py | C3 | 1/1 |

Rollback: revert the branch. Porting: one repo.

**SCOPE:** M (unchanged).

---

## Phase 3 — Execute

**Branch:** feat/272-a-partition-that-is-all-tests-answers-ok (from main)
**Implemented:** D1–D5. CONVENTION.md §6 row extended for `unlinked_same_name_sites` (262 payload-field blast; recorded, not a new approach).

**Axis 1 — file set:** nav_result.py, find_callers.py, find_references.py, tests/test_partition_zero_honesty.py, docs/CONVENTION.md, docs/BACKLOG.md, docs/LESSONS.md, docs/tasks/272_*.md. No stray references.

**Axis 2 — design-conformance:** Approach bullets `implemented-as-approved` after challenger round-1. Depth-1 gate on the count (061). Bare-name + shared 264 probe run when `depth==1 and production_count==0`. Census stays 238-shaped (E1).

**Verification sweep**

```
Ran at 5e6d1fb04982abe3fc41fa40f0fd5da2dbfb01f8
$ .venv/bin/python -m pytest tests/test_partition_zero_honesty.py tests/test_callers_test_role_census.py tests/test_empty_answer_cannot_explain_itself.py tests/test_honesty_predicate_derived_mapping.py tests/test_relation_unmodelled_for_language.py tests/test_find_callers_cross_language_unmodelled.py -q --tb=line
211 passed in 22.46s
```

---

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)**
**CHALLENGER: ON** — round-1 NOT CLEAN (R1 evidence arms + R8 depth sentinel). Verify-only round-2 in main loop (named findings only; no re-dispatch).

| Finding | Round 1 | Round 2 |
|---|---|---|
| R8 depth>1 sentinel `production_count==0` must not escalate | not met | met — `find_callers.py:451`; `test_depth_above_one_does_not_escalate` |
| R1 unlinked inbound | met | met |
| R1 264 shared probe | not met | met — probe when `depth==1 and production_count==0` (`find_callers.py:457`) |
| R1 bare-name truncation | not met | met — same gate (`find_callers.py:361`) + helper `unresolved_bare` |
| R1 census rewrites reason | not met | E1 — caveat only (238); expiry 2026-12-14 |

**Scope:** file axis ⊆ Gate-2 list. Behaviour: D1 helper now takes bare-name + shared reason (named finding, same files).
**Proving test:** `tests/test_partition_zero_honesty.py` 8 tests; would fail without the change (AC1 asserts `reason != ok`). vs BASELINE green → delta-green, no new honesty failure (211 passed).
**Layer-match:** no ❌. **k/N:** D1–D4 17/17; D5 bookkeeping at finalise.
**Clean?** clean (challenger only — REVIEWER: OFF)

`Reviewed at 4f366c576d223c14e79a8f5052b8d00ad62d66c4` · reviewed files: `code_atlas/tools/nav_result.py`, `code_atlas/tools/find_callers.py`, `code_atlas/tools/find_references.py`, `tests/test_partition_zero_honesty.py`, `docs/CONVENTION.md`, `docs/BACKLOG.md`, `docs/LESSONS.md`, `docs/TOKEN_LEDGER.md`. Working-doc path `docs/tasks/272_a-partition-that-is-all-tests-answers-ok.md` (embedded) is staleness-exempt.

---

## Phase 5 — Finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: challenger (1 dispatch)`

Durable lesson: none new — P1 `seen:` bumps on the three recalled handles already landed in execute. Census-vs-238 is E1, not a new claim.

Outward (handover-authorised): push feature branch; open PR. Deferred: merge.

Revert: drop the branch / revert the PR.

---

## Session status

- **Last updated:** 2026-09-14
- **Current phase:** finalise
- **Next action:** push branch and open PR
- **Blocked on:** none
