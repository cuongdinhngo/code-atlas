---
id: 330
slug: impact-signs-a-zero-its-own-unlinked-sites-contradict
title: "impact signs 'nothing depends on this' for a method called only through a factory-built receiver — the unlinked same-name sites that find_callers and find_references already count never reach it"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [065, 272, 314]
---

## Why this exists (field retro, 2026-09-23 — FIELD-1621/1615 batch)

For a PR risk section the session asked `impact` on a base class's `display()` method, with
`sign=true`. It answered `answer == seeds` — a **modelled zero, signed**, with
`frontier_skipped_non_resolved: 0`. In fact the controller behind every chart page calls
`$instance->display()` on a receiver a class-map factory builds; the call is dynamic, so it is never
linked. The retro rated it 4/10: *"the signed zero is the most dangerous kind of answer for a PR
risk claim."*

**The honesty already exists, two tools over.** 272 made `find_references` report
`unlinked_same_name_sites` from `store.count_unlinked_by_target_raw` (`find_references.py:258,
552-558`), and `find_callers` counts `unlinked_calls` on its empty arm (`find_callers.py:231`, 272's
`:477`). `impact` consults neither: `CLAIM_CARRY` is `seeds_dropped` and
`frontier_skipped_non_resolved` (`impact.py:43`), and an unlinked edge is not in the frontier to be
skipped. Its docstring is accurate — *"resolver-linked IMPACT kinds only"* (`impact.py:170`) — but
a signed claim is read, not the docstring.

## Goal

An `impact` answer whose method seeds have unlinked same-name inbound sites says so, and does not
sign the empty frontier as authoritative.

## Scope / Deliverables

1. **Per method seed, count unlinked same-name sites** with the existing store query (272).
2. **Non-zero ⇒ disclose** the count and mark the answer `authoritative: false` with a named
   caveat; the signed `claim` carries the count rather than implying a closed zero.
3. **Route**, per 314: name `find_callers` on the seed / text search as the next step.

## Constraints

- **No new resolution** (272 C1) — typing factory receivers stays out of scope.
- **R6.7** — one count, from `count_unlinked_by_target_raw`; no second predicate.
- **061** — seeds with zero unlinked sites answer byte-identically, signed or not.
- **R4.2** — counts from stored rows only.

## Acceptance criteria

- **AC1** Fixture: a method whose only caller is `$f->make()->m()` (unlinked) → `impact` discloses
  one unlinked site and is not authoritative; red-arm on today's code.
- **AC2** The same call with `sign=true` does not emit a claim that reads as a closed zero.
- **AC3** A method with only resolved dependents is byte-identical (regression).

## References
`code_atlas/tools/impact.py:43,159-170`; `code_atlas/tools/find_references.py:258,552-558,589`;
`code_atlas/tools/find_callers.py:231`; `code_atlas/store.py:2099`; tickets 065, 272, 314.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 330 — impact unlinked same-name sites (working doc)

- **Ticket:** 330 · local
- **Type:** bug
- **Repo(s) / Porting:** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** finalise — next: push branch, open PR
- **Session status:** review clean → finalise

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions.

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · References) | 6 decomposed | ROWS: C=4 R=3 G=1 AC=3`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | method seeds with unlinked sites say so; do not sign closed zero | count + authoritative false + claim carry | D1 | AC1 AC2 | ✅ |
| R1 | Scope 1 | Per method seed count via 272 store query | `_method_seed_unlinked_sites` | D1 | AC1 | ✅ |
| R2 | Scope 2 | Non-zero ⇒ disclose + authoritative false + claim carries count | caveat + CLAIM_CARRY | D1 D2 | AC1 AC2 | ✅ |
| R3 | Scope 3 | Route to find_callers (314) | TRY_INSTEAD_FIND_CALLERS | D2 | AC1 | ✅ |
| C1 | Constraints | No new resolution | count only | D1 | review | ✅ |
| C2 | Constraints | R6.7 one count from count_unlinked_by_target_raw | same call | D1 | review | ✅ |
| C3 | Constraints | 061 zero-unlinked byte-identical | omit-when-empty | D1 | AC3 | ✅ |
| C4 | Constraints | R4.2 stored rows only | store query | D1 | review | ✅ |
| AC1 | AC | unlinked only caller → disclose 1, not authoritative | proving | D1 | proving | ✅ |
| AC2 | AC | sign=true claim not closed zero | unlinked in claim | D1 | proving | ✅ |
| AC3 | AC | resolved-only byte-identical | proving | D1 | proving | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause (bug, `logic`): impact CLAIM_CARRY omits unlinked sites; signed answer==seeds reads as closed zero while find_callers already counts those CALLS.
- Blast radius: impact.py; nav_result caveat/route; claim carry; 065/272/314.

`TRACK: backend — 0/3 touched files under UI paths`

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R6.7 (change-type) ✅ one store predicate · R5.4 (change-type) ✅ find_callers route · R7.2 (change-type) ✅ ledger`

`BASELINE: green`

## Phase 2 — Design

- Approach: after walk, sum `count_unlinked_by_target_raw` for Method seeds; if >0 attach field, caveat, find_callers route; extend CLAIM_CARRY.
- Rejected: typing factory receivers (out of scope / 272 C1).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | count + disclose + carry | code_atlas/tools/impact.py | claim line | R1 R2 C* AC* | 1/1 |
| D2 | caveat + find_callers route | code_atlas/tools/nav_result.py | 093 | R3 | 1/1 |
| D3 | proving AC1–3 | tests/test_impact_unlinked_same_name_sites.py | — | AC* | 1/1 |
| D4 | bookkeeping | docs/tasks/330_… · BACKLOG · TOKEN_LEDGER | — | R7.2 | 1/1 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | pytest | authored | ✅ |
| AC2 | integration | pytest | authored | ✅ |
| AC3 | integration | pytest | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_impact_unlinked_same_name_sites.py -q`

`SCOPE: S`

## Phase 3 — Execute

**Branch:** feat/330-impact-unlinked-sites

Ran at f906d7a2960a5a35ea9959b86c2020a0f74be7fb

```
$ .venv/bin/python -m pytest tests/test_impact_unlinked_same_name_sites.py -q
3 passed in 0.88s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: OFF (--no-reviewer)
CHALLENGER: ON — round-1 CLEAN, 12 met / 0 not met / 0 can't tell.

Verdict: `clean (challenger only — REVIEWER: OFF)`

Ran at f906d7a2960a5a35ea9959b86c2020a0f74be7fb

```
$ .venv/bin/python -m pytest tests/test_impact_unlinked_same_name_sites.py -q
3 passed in 0.88s
```

`REVIEW: CLEAN`
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`

`Reviewed at f906d7a2960a5a35ea9959b86c2020a0f74be7fb`

## Phase 5 — Finalise

Outward: push feat/330-impact-unlinked-sites, open PR. Never merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| review | challenger | 1 | unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: unmeasured (subagent dispatch only; host surfaces no usage) · top cost driver: review/challenger round 1`
