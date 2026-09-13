---
id: 252
slug: a-class-reference-question-costs-n-plus-one-calls
title: 'A class-level `find_references` returns zero hits and routes to a two-step costing one `search_symbol` plus one `find_callers` per member, so the commonest first question about a class — what touches it at all — is the most expensive answer on the surface'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [245, 168, 065]
---

## Why this exists (field retro — the anchor repo, 2026-09-11, round 18)

The consuming agent's first move on the photo bug was the obvious one — ask what references
`MemberPhotoResolver`. Its account:

> `find_references` on the `MemberPhotoResolver` **class** returned `results: []` with
> `reason: relationship_not_modelled` and `try_instead: search_symbol` + a hint to re-ask with a
> `Class::method` qname. […] It's the one place a naive expectation ("find everything that references
> this class") fails silently-ish — but the tool tells you why and what to do, so it cost one
> redirected call, not a wrong conclusion.

The retro grades this mildly and the grade is too kind, because it prices only the redirect. 065's
rule — a refusal with no route is a trap — is satisfied; 093's stronger rule, that **the route must
make progress**, is satisfied only in the sense that the reader ends up somewhere. What the route
actually costs is one `search_symbol` to enumerate the members, then one `find_callers` per member:
for `MemberPhotoResolver` (`browserSrc`, `embeddedSrc`, `resolve`, `storedValue`) that is five
calls, and the reader must then union four payloads by hand and decide what the union means.

The agent paid it and got the right answer. The finding is the price, not the outcome: the question
asked most often first about a class is the only navigation question on the surface whose cost scales
with the subject's member count.

## Root cause

`find_references` answers a single relation — resolved edges whose `target_qname` is the subject.
When that set is empty and unlinked `REFERENCES`/`IMPORTS` exist for the bare name, it correctly
declines to call the zero genuine and hands over a route
(`code_atlas/tools/find_references.py:223-233`):

```python
if unlinked > 0:
    reason = REASON_RELATIONSHIP_NOT_MODELLED
    try_instead = TRY_INSTEAD_SEARCH_SYMBOL
    try_instead_hint = TRY_INSTEAD_HINT_METHOD_QNAME
```

Every part of that is right under the rules it was built to. What is missing is that the tool already
sits on the data the reader is about to assemble: the class's members are `CONTAINS` children, and
each member's inbound `CALLS`/`NEW` edges are exactly what the `n` follow-up calls will fetch. The
union is one query's distance away and is instead sold as `n + 1` calls of the reader's own work.

## Scope

A class-level answer that is a **union over the subject's own members**, computed in the call the
reader already made.

Shape decisions left to phase 2 — the ticket does not bind one:

- **Whose members.** Declared members only, or inherited too. Declared-only is the working assumption:
  it is derivable without a resolution pass and it matches what the two-step would have produced.
- **What the hit says.** Each row must name the member it arrived through, or the union is a list of
  call sites that appear to reference a class that nothing references.
- **What the answer is called.** It is not a `REFERENCES` edge set and must not wear that name. The
  relation "a caller of a member of this class" is a derived aggregate, and the payload says so.

## Constraints

- **R5.6 — never dress a derivation as a modelled edge.** `reason` stays distinct from `ok`; the union
  cannot claim the class-reference relation the graph does not hold. This is the same discipline 249
  used for `separator_normalised`.
- **Tiering survives the union.** Each hit keeps its own tier; the answer's weakest tier governs any
  claim line, exactly as `find_callers` does today.
- **24 tools stay 24** (`tests/test_documented_tool_count.py`) — this lands on `find_references`, not
  as a new tool.
- **R4.2 / R1.1** — deterministic union order; keyed by contract kind, never by language.
- **Bounded.** A class with hundreds of members must not fan out unboundedly; the answer pages like
  every other navigation answer (057) and says when it capped.

## Acceptance criteria

- **AC1** A class subject with unlinked references and called members returns the union **in one
  call**, each hit naming the member it came through and carrying its own tier.
- **AC2** The payload's `reason` distinguishes the union from a modelled class-reference answer; no
  reader can mistake it for `ok`.
- **AC3** A class whose members genuinely have no callers still returns an honest zero, and that zero
  is distinguishable from today's `relationship_not_modelled`.
- **AC4** The 065/093 route survives wherever the union is not available, so no answer loses its
  route (the regression this must not cause).
- **AC5** Every other tool's payload is byte-identical (022 AC3).

## References

- `code_atlas/tools/find_references.py:223-233` — the decline and the two-step route.
- `code_atlas/tools/nav_result.py` — `REASON_RELATIONSHIP_NOT_MODELLED`, `TRY_INSTEAD_SEARCH_SYMBOL`,
  `TRY_INSTEAD_HINT_METHOD_QNAME`.
- [065](065_empty-answer-cannot-explain-itself.md) / [093](093_try-instead-is-not-a-callable-tool-name.md)
  — the route rules this keeps while removing the reason to use them.
- [245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md) /
  [249](249_a-miss-whose-only-defect-is-the-separator-spelling-gets-no-route.md) — the precedent for
  answering a near-miss in the call that missed, rather than routing the reader to re-ask.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 252 — A class-level reference question costs n+1 calls (working doc)

- **Ticket:** 252
- **Type:** enhancement
- **Repo(s):** app
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — related nav/065 suite on untouched `main` `8303edb` (no failing items)

## Session status

- **Last updated:** 2026-09-12
- **Current phase:** finalise
- **Next action:** push feature branch + open PR (handover-authorised); merge not authorised
- **Blocked on:** none
- **work_doc_mode:** embed
- Run: `/mango:autorun 252 --no-reviewer`; challenger ON.
- Branch: `feat/252-a-class-reference-question-costs-n-plus-one-calls`
- Contract: `.mango/run-contract-252.txt`

---

## Phase 0 — Refine

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 5 unresolved surfaced | 4 want-decision asked | 1 how-decision resolved+cited | 4 ASSUMED | skip: no`

**PREMISE detail.** Present: `code_atlas/tools/find_references.py`, `code_atlas/tools/nav_result.py` (`REASON_RELATIONSHIP_NOT_MODELLED`, `TRY_INSTEAD_SEARCH_SYMBOL`, `TRY_INSTEAD_HINT_METHOD_QNAME`), `tests/test_documented_tool_count.py`, tasks 065, 093, 245, 249. No missing resolvable identifiers.

**INPUT KIND:** ticket (not epic).

**How-decisions (self-resolved):**

1. **Lands on `find_references`, not a 25th tool.** Citation: ticket Constraints "24 tools stay 24"; `tests/test_documented_tool_count.py`; AGENTS.md 24-tool pin.

**ASSUMED (awaiting ratification) — handover authorised choose-the-best-approach:**

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses a prior decision? |
|---|----------------|-------------|--------------------------|----------------------------|
| 1 | Declared CONTAINS members only (not inherited) | Ticket Scope working assumption; matches the two-step | design / DISCLOSURE | no |
| 2 | Subject kind is `Class` only (not Interface/Trait/Enum) | Ticket says "class subject"; Interface methods often have no CALLS, so a union zero would swallow the 065 route (AC4) | design / DISCLOSURE | no |
| 3 | Union replaces only the unlinked-decline path, not a genuine `no_matches` | Ticket AC1 names "unlinked references"; 065 genuine zero stays `no_matches` | design / DISCLOSURE | no |
| 4 | Reason spelling is `via_members` (tool vocab, not a `contract_version` bump) | Acceptance-bar / naming; same class as 249 `separator_normalised` | design / DISCLOSURE | no |

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `do-not-attest-past-the-payloads-resolution` | 2 | handle | Yes — union must not wear `reason=ok` |
| 2 | `try-instead-tool-name` / `route-must-answer` | 2 | handle | Yes — AC4 keeps the 065/093 route when union is unavailable |
| 3 | `prove-the-guard-fails` | 2 | handle | Yes — proving test red on `main` |
| 4 | `one-rule-for-every-subject-slot` | 2 | handle | Weigh: Class-only is a kind key, not a second code path per language |

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch) [1b24dae8](1b24dae8-4a1e-4a06-9d78-e32b5a7b89fb): surfaced ASSUMED #2 (which TYPE_KINDS) and #3 (whether to replace `no_matches`). Classified WANT; recorded ASSUMED.

**Constraints from the scan:** R5.6, R5.4, R4.2, R1.1, 24-tool pin, 057 paging, 061 omit-when-empty on default modelled answers.

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria) | 5 decomposed | ROWS: C=5 R=3 G=2 AC=5`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 proven by | Status |
|----|--------|------------------|----------------|--------------|-----|-----------------|--------|
| G1 | Why | class-level first question costs n+1 | One `find_references` call returns the member-caller union | ticket Why | D1 | AC1 | ✅ |
| G2 | Root cause | union is one query away | Compute CONTAINS → CALLS/NEW in the same call | `find_references.py` decline | D1 | AC1 | ✅ |
| C1 | Constraints | R5.6 | `reason` ≠ `ok`; not a REFERENCES edge set | ticket + 249 | D1 | AC2 | ✅ |
| C2 | Constraints | tiering survives | each hit keeps its tier; all-DYNAMIC ⇒ authoritative false | find_callers caveats | D1 | AC1 | ✅ |
| C3 | Constraints | 24 tools | no new tool | `TOOL_NAMES` | D1 | AC5 | ✅ |
| C4 | Constraints | R4.2 / R1.1 | deterministic sort; keyed by kind `Class` | ticket | D1 | proving | ✅ |
| C5 | Constraints | bounded / 057 | page limit/offset; truncated when capped | ticket | D1 | paging test | ✅ |
| R1 | Scope | declared members | CONTAINS children only | ASSUMED #1 | D1 | AC1 | ✅ |
| R2 | Scope | each hit names the member | `via_member` = member qname | ticket Scope | D1 | AC1 | ✅ |
| R3 | Scope | derived aggregate name | `reason=via_members` | ASSUMED #4 | D1 | AC2 | ✅ |
| AC1 | AC | union in one call | Class + unlinked + called members | ticket AC1 | D3 | proving | ✅ |
| AC2 | AC | reason ≠ ok | `via_members` | ticket AC2 | D3 | proving | ✅ |
| AC3 | AC | honest member-zero ≠ unmodelled | `via_members` + empty + no try_instead | ticket AC3 | D3 | zero test | ✅ |
| AC4 | AC | 065/093 route survives | no CONTAINS or non-Class keeps the route | ticket AC4; ASSUMED #2–#3 | D3 | 065 + interface test | ✅ |
| AC5 | AC | other tools byte-identical | no other tool signature change | ticket AC5 | D3 | tool-count + method/callers | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-----------------|
| AC1 | union in one call; hit names member + tier | CONTAINS + CALLER_KINDS already stored; `edge_hit` already carries tier | Y | planted Class + 2 CALLS | ASSUMED #1–#2 |
| AC2 | reason ≠ ok | new `NavReason` member | Y | `reason == via_members` | ASSUMED #4 |
| AC3 | empty members-no-callers ≠ relationship_not_modelled | distinct reason + no try_instead | Y | planted CONTAINS, no CALLS | — |
| AC4 | route survives when union unavailable | no CONTAINS / non-Class → existing decline | Y | 065 fixture + Interface | ASSUMED #2–#3 |
| AC5 | every other tool byte-identical | find_references only; default modelled path unchanged | Y | `len(TOOL_NAMES)==24`; method subject still `ok` | — |

## Inventory

- **Denominator / total N:** 24 (`code_atlas.main.TOOL_NAMES`). AC5 is "every current tool".

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| 1 | Other tools' default payloads unchanged | tool-count pin + no signature change outside find_references | ✅ |

`TRACK: backend — 0/0 touched files under UI paths`

## Clarifications

`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`

1. Lands on find_references — ticket Constraints + 24-tool pin.
2. Declared CONTAINS only — ticket Scope working assumption (`ASSUMED` #1).
3. Class only — ticket wording + AC4 / Interface CALLS gap (`ASSUMED` #2; exposure-checker).
4. Unlinked-decline only — ticket AC1 + 065 genuine zero (`ASSUMED` #3; exposure-checker).
5. Reason `via_members` — 249 precedent (`ASSUMED` #4).

---

## Phase 1 — Analysis

`RULE SECTIONS: 8 applicable — 5 by change-type | 3 by recalled handle — §R1.1 (change-type) ✅ kind==Class not a language name, §R3 (change-type) N/A (nav reason is tool vocab; 065 pin: not CONTRACT_VERSION), §R4.2 (change-type) ✅ deterministic sort, §R5.4 (handle try-instead-tool-name) ✅ route kept when union unavailable, §R5.6 (handle do-not-attest-past-the-payloads-resolution) ✅ reason≠ok, §R6.5 (handle prove-the-guard-fails) ✅ proving test, §R7.5 (change-type) ✅ comments≤3, §R7.6 (change-type) ✅ PLAN cell pruned`

Related suite on untouched `main` `8303edb00205ecd15ae88686cc14b263dd2fe4da` (065 / find_references / nav reasons) was green before this branch's edits. No baseline exclusions.

`BASELINE: green — no failing items`

- **Gate 1 status:** ✋ surfaced (autorun proceeds on standing + handover; `j = 0`)

---

## Phase 2 — Design

- **Approach.** When `find_references` would emit `relationship_not_modelled` and the subject `kind` is `Class` and the class has at least one `CONTAINS` child with a `target_qname`, replace that decline with a paged union of inbound `CALLS`/`NEW` on those children (`contract.CALLER_KINDS`). Each hit is `edge_hit` plus `via_member`. `reason=via_members` (never `ok`). Empty union is still `via_members` and omits `try_instead`. No CONTAINS or non-Class keeps the 065/093 route. Sort by `(via_member, qname, file, line)`. Page with existing `limit`/`offset`. Walk cap `_MEMBER_WALK=10_000`.

- **Rejected.** (1) New tool — rejected: 24-tool pin. (2) Union on Interface/Trait/Enum — rejected this ticket: ticket says class; Interface CALLS are usually empty and would swallow AC4. (3) Replace genuine `no_matches` — rejected: 065 confident zero; ticket AC1 is the unlinked path. (4) `reason=ok` — rejected: R5.6.

**Assumptions**

| Assumption | Status |
|------------|--------|
| CONTAINS children carry `target_qname` when the adapter linked them | verified — same as Table CONTAINS (248) |
| Unlinked REFERENCES evidence is unchanged (`count_unlinked_by_target_raw`) | verified — 065 fixture |
| `edge_hit` already carries `confidence_tier` | verified — `nav_result.py` |

**Smallest change-list**

| Change | File | Blast radius | Ph2 | k/N |
|--------|------|--------------|-----|-----|
| `REASON_VIA_MEMBERS` | `code_atlas/tools/nav_result.py` | `NAV_REASONS` pin tests | AC2 | 1/1 |
| Union on unlinked Class | `code_atlas/tools/find_references.py` | 065 route when union unavailable | AC1–AC4 | 4/4 |
| Proving + AC tests | `tests/test_find_references_via_members.py` + last-reason pins | 065 / 186 last-element pins | AC1–AC5 | 5/5 |
| PLAN tool cell | `docs/PLAN.md` | standing budget | R7.6 | 1/1 |
| Working doc / backlog / ledger / lesson | docs | bookkeeping | R7.2 | 1/1 |

**Recalled handles**

| Handle | Answer |
|--------|--------|
| `do-not-attest-past-the-payloads-resolution` | traced — `via_members` ≠ `ok` |
| `try-instead-tool-name` | traced — 065 hint survives when union is None |
| `prove-the-guard-fails` | traced — proving asserts `via_members` (fails on main) |

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

Handle traces (pre-change tree `8303edb`, not `$` evidence):

```
rg -n "REASON_VIA_MEMBERS|via_members" code_atlas/tools/find_references.py || echo count=0
count=0
```

```
sed -n '223,233p' code_atlas/tools/find_references.py
    if unlinked > 0:
        reason = REASON_RELATIONSHIP_NOT_MODELLED
        try_instead = TRY_INSTEAD_SEARCH_SYMBOL
        try_instead_hint = TRY_INSTEAD_HINT_METHOD_QNAME
```

**Verification plan**

| AC | Layer | Proof | Match |
|----|-------|-------|-------|
| AC1 | tool pytest | planted Class + 2 member CALLS | ✅ |
| AC2 | tool pytest | `reason == via_members` | ✅ |
| AC3 | tool pytest | CONTAINS, no CALLS | ✅ |
| AC4 | tool pytest | no CONTAINS + Interface | ✅ |
| AC5 | tool pytest | tool count 24; method `ok` | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `tests/test_find_references_via_members.py::test_class_with_called_members_returns_via_members_union`

- **Gate 2 status:** ✋ surfaced (autorun proceeds; then BIND)

---

## Phase 3 — Execute

- **Branch:** `feat/252-a-class-reference-question-costs-n-plus-one-calls`
- **Proving test:** `tests/test_find_references_via_members.py::test_class_with_called_members_returns_via_members_union`

- **Verification sweep.**
  - Axis 1 (files): `code_atlas/tools/find_references.py`, `code_atlas/tools/nav_result.py`, `tests/test_find_references_via_members.py`, last-reason pins, `docs/PLAN.md`. ⊆ approved list.
  - Axis 2 (behaviour): Approach bullets `implemented-as-approved` — Class + unlinked + CONTAINS → `via_members` union; empty union distinguishable; 065 route when union unavailable; no 25th tool.

- **Design-conformance deviations:** none.

- **Empirical output**

Ran at 2bb70455164705f6c4f4511d6f93938e3382f535

```
$ .venv/bin/python -m pytest tests/test_find_references_via_members.py -q --tb=line
......                                                                   [100%]
6 passed in 1.45s
```

Ran at 2bb70455164705f6c4f4511d6f93938e3382f535

```
$ .venv/bin/python -m pytest tests/test_find_references_via_members.py tests/test_empty_answer_cannot_explain_itself.py tests/test_find_references_twins.py tests/test_try_instead_is_a_callable_tool_name.py tests/test_nav_reason_codes.py tests/test_documented_tool_count.py -q --tb=line
........................................                                 [100%]
40 passed in 2.14s
```

- **Golden/snapshot:** none
- **Design-invalidation:** none

---

## Phase 4 — Review

- **REVIEWER: OFF (`--no-reviewer`)** — no rule-book-grounded review of this diff exists.
- **CHALLENGER: ON** — ticket-blind challenger [df303930](df303930-4ea3-4ff9-ad4a-83bf47d1cdf0). Raw ticket (above separator) + `git diff main...HEAD` on product paths only.
- **challenger result:** **11/11 MET — CLEAN**.
- **Verdict:** `clean (challenger only — REVIEWER: OFF)`
- **Scope reconciliation:** file + behaviour axes clean.
- **Proving test would fail without the change?** Yes — `via_members` is not a reason on `main`.
- **Layer-match:** no ❌.

Reviewed at 2bb70455164705f6c4f4511d6f93938e3382f535

Reviewed files: `code_atlas/tools/find_references.py`, `code_atlas/tools/nav_result.py`, `tests/test_find_references_via_members.py`, `tests/test_nav_reason_codes.py`, `tests/test_empty_answer_cannot_explain_itself.py`, `tests/test_relation_unmodelled_for_language.py`, `docs/PLAN.md`

Working-doc path (stale-review exempt): `docs/tasks/252_a-class-reference-question-costs-n-plus-one-calls.md`

- **Gate 4 status:** ✋ surfaced (autorun proceeds; challenger CLEAN; reviewer waived)

---

## Phase 5 — Finalise

**Durable lesson.** A member-caller union must not wear `reason=ok`; empty union is still `via_members`, not `relationship_not_modelled`.

### 252-C1 — A member-caller union is not a modelled class-reference

- type: 2 (code) · handle: `do-not-attest-past-the-payloads-resolution`
- status: proposed (recurrence of R5.6 — bump `seen:` only)
- seen: 252
- destination: stays as bump; rule already carries the class

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: R5.6 (already) | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (autorun)`

**P1.** Class-index `seen:` bumped for `do-not-attest-past-the-payloads-resolution`, `try-instead-tool-name`, `prove-the-guard-fails`.

**Gate:** `scripts/gate.sh` GATE GREEN — 20 passed · 0 failed · 0 skipped (Linux host).

**Outward actions (handover-authorised):** (1) push feature branch (2) open PR. Merge later authorised; merged 2026-09-12 — `9fdcdc1` ([#329](https://github.com/cuongdinhngo/code-atlas/pull/329)).

**Token-usage (working doc).** 2 challenger dispatches unmeasured; reviewer off; main-loop unmeasured. See `docs/TOKEN_LEDGER.md` row 252.

---
