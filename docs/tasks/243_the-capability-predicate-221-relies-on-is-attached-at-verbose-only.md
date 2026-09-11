---
id: 243
slug: the-capability-predicate-221-relies-on-is-attached-at-verbose-only
title: '`cross_language` — the census 221 and 238 use to decide whether a zero is honest — rides inside `edge_health_by_language`, which is attached at `verbose` only, so the agent that calls `get_index_status` at its default `standard` cannot read the one number that says whether the crossing in its repo is modelled at all'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [221, 238, 204, 183]
---

## Why this exists (field retro round 17)

204 built the `cross_language` row precisely so a cross-language gap would be *visible*: a link to a
callee that cannot be called counts as healthy in 183's per-language rows, and this is the row that
can see it. 221 then made it a predicate — an empty `find_callers` on a subject whose real callers
are in another language answers `relation_unmodelled` instead of `no_matches` — and 238 extended the
predicate to the confident non-zero.

All three deliver **in the response**. A field in a response cannot reach an agent that has decided
not to call, and that decision happens before any call.

The one channel that reaches the agent first is `get_index_status`, which the round-17 session called
as **tool call #1** and pasted verbatim into its retro. It called it at `standard` — the default.
`edge_health_by_language`, which carries `cross_language`, is attached only inside the `verbose`
payload (`code_atlas/tools/get_index_status.py:314`). `standard` carries `edge_health` (whole-graph),
`parse_failures`, `dirty_indexed_files` and `unconfigured_adapters` — no per-pair crossing census.

So the session read the status payload carefully enough to act on `unconfigured_adapters` and on
`server_stale_process`, and then wrote in the same retro that *"a third of the interesting behaviour
in this system is in stored procedures, and for that third the index is not in the conversation at
all"* — a conclusion the missing field is the direct answer to.

## Evidence — measured on the anchor monorepo, 2026-09-11

The census on an index holding 19,352 PHP, 3,012 SQL and 2,519 TypeScript files:

```
cross_language: {"by_tier":{"DYNAMIC":0,"HEURISTIC":0,"RESOLVED":0},"linked":0,"pairs":{},"unlinked":0}
```

Zero linked crossings, no pairs. PHP in this repo calls stored procedures constantly — one proc
measured for [242](242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md)
has 0 linked inbound edges and **7 unlinked edges whose raw text names it**. That is exactly the
regression signal 204 wrote the row to carry, and it sat one `detail_level` above where the reader
was looking.

`_attach_edge_health_by_language` is also silent below two language buckets (:328-334) — correct for
a single-language graph, and not the cause here: this index has four.

## Scope

- **Attach the crossing census where the reader is.** Either move `cross_language` (not all of
  `edge_health_by_language`) to `standard`, or carry a bounded summary of it there. Decide between
  the two in the design and state the payload cost of each.
- **Consider `next_tool_suggestions` instead of, or as well as, a field.** `linked: 0` on a
  multi-language index is not a statistic, it is *an instruction about which questions this index
  cannot answer*. 061 built that list state-reactive for this shape of fact.
- **Keep 183's rows where they are.** The per-language tier mix is diagnostic and belongs at
  `verbose`; this ticket moves the one row that changes what a reader may conclude.
- **Out of scope:** improving cross-language linking itself (that is 222's line of work) and any
  change to 221/238's response-side predicates, which are correct.

## Constraints

- **061 / 223** — `standard` is the cheap path on the first call of every session; the added bytes
  must be measured and bounded. `pairs` grows with the square of the language count, so a summary
  may be the only admissible shape.
- **R5.6** — a pre-204 index has no stamp and must say it cannot tell, never `linked: 0`.
- **061** — omit when it adds nothing: a single-language index must stay byte-identical.
- **R4.2** — the value comes from the build stamp, not from a query-time scan; one scan per build is
  already 204's design and this ticket does not move it onto the answer path.

## Acceptance criteria

- `get_index_status` at `standard` on a multi-language index carries the crossing census (or its
  agreed summary), pinned by a test.
- A single-language index, and a pre-204 index, each stay unchanged — asserted.
- Added payload bytes at `standard` measured on the anchor-scale index and recorded here.
- A test asserts the `linked: 0` multi-language case produces the reader-facing signal chosen in
  design (field, suggestion, or both).


## Payload cost (AC3) — measured 2026-09-11

Bounded summary at `standard` (`by_tier` / `linked` / `unlinked`; **no `pairs`**):

| Corpus | What was measured | Bytes |
|--------|-------------------|------:|
| Anchor-scale (Evidence census above, pairs dropped) | field JSON only | **86** |
| Same census with empty `pairs` retained | field JSON (rejected shape) | 99 |
| Two-language fixture (`fake`/`second`) | full `standard` payload delta with vs without the field | **106** |

Proving test gates the fixture delta under 200 B. Dropping `pairs` keeps the cost O(1) in the language count (061 / 223); the anchor monorepo was not re-indexed in this run — the byte figure uses the census JSON already published in Evidence.

## References

Field retro round 17 (2026-09-11, maintainer-local) §0.1, §2.6, §3. Related:
[204](204_bare-name-resolution-has-no-language-predicate.md) (built the row),
[183](183_edge-health-has-no-per-language-breakdown.md) (per-language tier rows — the sibling that correctly stays at `verbose`),
[221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) and
[238](238_the-honest-zero-predicate-is-gated-on-the-zero.md) (the two predicates that read it),
[061](061_payload-weight.md) (`next_tool_suggestions` and omit-when-empty),
[244](244_no-channel-announces-a-capability-change.md) (this ticket is the narrowest instance of
that one).

## Token usage

| Phase | Tokens |
|---|---|
| autorun (main-loop) | unmeasured (host surfaces no usage block) |

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 243 — Crossing census at standard (working doc)

- **Ticket:** 243 · local file `docs/tasks/243_the-capability-predicate-221-relies-on-is-attached-at-verbose-only.md`
- **Type:** bug
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 touched files under UI paths
- **TIER:** full
- **BASELINE:** green — related suite 32 passed on untouched HEAD; no baseline exclusions
- **INPUT KIND:** ticket (not epic)

## Session status

- **Last updated:** 2026-09-11
- **Current phase:** review
- **Next action:** commit → review (challenger) → finalise
- **Blocked on:** none
- **work_doc_mode:** embed
- Run: `/mango:autorun 243 --no-reviewer`; challenger ON.
- Branch: `fix/243-the-capability-predicate-221-relies-on-is-attached-at-verbose-only`
- Worktree: `/tmp/code-atlas-wt-243`
- Contract: `.mango/run-contract-243.txt`

---

## Phase 0 — Refine

`PREMISE: 14 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: ticket locks AC, constraints (061/R5.6/R4.2), and the design fork (field vs summary vs suggestion) as an in-design HOW choice under handover authorisation — no WANT left open.

**PREMISE detail.** Present: `code_atlas/tools/get_index_status.py` (`_attach_edge_health_by_language` @318+, `detail_level == "standard"` early return), `EDGE_HEALTH_BY_LANGUAGE_FIELD`, `stamped_cross_language_edges` / `_cross_language_edges` in `store.py`, `next_tool_suggestions` / `_attach_suggestions`, `edge_health` / `parse_failures` / `dirty_indexed_files` / `unconfigured_adapters`, tasks 221/238/204/183/061/244. **Ambiguous (surfaced, not blocking):** private anchor monorepo census; field retro round 17 (maintainer-local).

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `do-not-attest-past-the-payloads-resolution` → R5.6 | 2 | handle | Yes — pre-204 stamp must stay silent |
| 2 | 221-C1 `cross-language-zero-needs-the-crossing-census` | 2 | handle | Yes — surface that census where the reader looks |
| 3 | 162-C1 `stamp-at-the-builder-not-the-wrapper` | 2 | handle | Yes — attach inside `get_index_status._status` |

**Exposure-checker:** skipped (refine skip: yes).

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Evidence · Scope · Constraints · Acceptance criteria) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why this exists | census rides at verbose only; agent calls standard | Attach crossing census (or summary) at standard | `get_index_status.py` attaches 183 field only after standard return | D1 | proving tests | ✅ |
| C1 | Constraints | 061/223 — added bytes measured and bounded; pairs may force a summary | Drop `pairs` from the standard copy | ticket Constraints; pairs O(n²) | D1 | delta 106 B fixture | ✅ |
| C2 | Constraints | R5.6 — pre-204 must not say `linked: 0` | Omit when stamp None | `stamped_cross_language_edges` | D1 | `test_pre_204_…` | ✅ |
| C3 | Constraints | 061 — single-language byte-identical | Omit under two buckets | `_language_bucket_count` | D1 | `test_single_language_…` | ✅ |
| C4 | Constraints | R4.2 — value from build stamp, not answer-path scan | Read stamped census only | store readers | D1 | stamp-read path | ✅ |
| R1 | Scope | Attach crossing census where the reader is (field or summary) | Bounded summary at standard | ticket Scope | D1 | AC1 tests | ✅ |
| R2 | Scope | Consider next_tool_suggestions | Rejected: no remedial tool exists (222 OOS); field is the signal | ticket Scope | D2 | AC4 asserts no fake suggestion | ✅ |
| R3 | Scope | Keep 183's per-language rows at verbose | Do not move `edge_health_by_language` | ticket Scope | D1 | `test_the_breakdown_is_verbose_only` still green | ✅ |
| R4 | Scope | OOS: linking / 221-238 predicates | No changes there | ticket | — | untouched | ✅ |
| AC1 | AC | standard on multi-lang carries census/summary, pinned | `{linked,unlinked,by_tier}` no pairs | | D3 | `test_standard_carries_…` | ✅ |
| AC2 | AC | single-lang and pre-204 unchanged | omit field | | D3 | two tests | ✅ |
| AC3 | AC | added bytes measured on anchor-scale and recorded | fixture 106 B; pairs omitted ⇒ anchor O(1) same shape | | D3 | `test_standard_payload_delta_…` + recorded here | ✅ |
| AC4 | AC | `linked: 0` multi-lang produces chosen signal | field present with linked==0 | | D3 | `test_linked_zero_…` | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | census or summary at standard | today absent at standard (`test_the_breakdown_is_verbose_only` sibling) | Y | key presence | — |
| AC2 | single-lang + pre-204 unchanged | 183 already omits under 2 buckets / missing stamp | Y | key absence | — |
| AC3 | bytes measured + recorded | measureable via json.dumps delta | Y | numeric delta in test + doc | — |
| AC4 | linked:0 signal | field or suggestion or both | Y | linked==0 on standard | — |

## Inventory (universal)

- **Denominator / total N:** 1 (`get_index_status` attach path)

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| 1 | standard attach of bounded cross_language | proving module | ✅ |

## Clarifications

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

- Self-resolved (with citation):
  1. Field vs summary: choose **bounded summary without `pairs`** — ticket Constraints cite pairs' quadratic growth and 061/223 cheap path. Cite ticket Constraints / Scope.
  2. Suggestion vs field: choose **field only** — `next_tool_suggestions` names servable tools; no tool remediates an unmodelled crossing (222 OOS). Cite `_suggestions` + ticket OOS.
- For human decision: none

---

## Phase 1 — Analysis

- Root cause (bug, `config`/`logic`): `_attach_edge_health_by_language` (and nested `cross_language`) runs only after the `detail_level == "standard"` early return, so the default first call never sees the census 221/238 already depend on.
- Handler / blast radius: `get_index_status._status`; tests for 183 verbose-only; PLAN §12 table cell; new proving module.
- `TRACK: backend — 0/0 touched files under UI paths`
- `SCOPE: S`
- `TIER: full`

`RULE SECTIONS: 7 applicable — 6 by change-type | 1 by recalled handle — R1.4 (change-type) ✅ tools present; store owns stamp · R1.8 (change-type) ✅ one bucket-count helper · R4.2 (change-type) ✅ stamp read not scan · R5.6 (change-type) ✅ pre-stamp silence · R6.1 (change-type) ✅ fixture proves multi/single/pre-stamp · R7.6 (change-type) ✅ PLAN cell updated in same change · R5.6 (recalled handle) ✅ do-not-attest`

### BASELINE

Related suite on untouched code:

```
Ran at 4be3f04510d0745cdb14fd5d3f5aa8f0fef165a4
$ .venv/bin/python -m pytest tests/test_edge_health_per_language.py tests/test_get_index_status_health.py tests/test_find_callers_cross_language_unmodelled.py -q --tb=no
................................                                         [100%]
32 passed in 9.36s
```

`BASELINE: green` for the change-adjacent suite. No baseline exclusions.

- **Gate 1 status:** cleared (autorun closes on artifacts; `j = 0`)

---

## Phase 2 — Design

- **Approach.** Before the `standard` early return, call `_attach_cross_language_summary`: read `stamped_edge_health_by_language` / `stamped_cross_language_edges`, omit when stamp missing or language buckets < 2, else attach `{by_tier, linked, unlinked}` under top-level `cross_language` (drop `pairs`). Extract `_language_bucket_count` shared with `_attach_edge_health_by_language` (R1.8). Keep full 183 field (with nested pairs) at verbose only. Reader signal for `linked: 0` = the field. Update PLAN §12 `get_index_status` cell. Prove with `tests/test_cross_language_at_standard.py`.

- **Rejected alternatives.**
  1. Move full `cross_language` including `pairs` to standard — rejected: ticket Constraints (pairs ∝ languages²) / 061.
  2. `next_tool_suggestions` instead of / as well as the field — rejected: suggestions name tools; no tool fixes an unmodelled crossing here (222 OOS); a fake hint would be dishonest.
  3. Move all of `edge_health_by_language` to standard — rejected: ticket Scope (183 rows stay verbose).

**Assumptions**

| Assumption | verified / novel-untested | Notes |
|------------|---------------------------|-------|
| `stamped_cross_language_edges` is a meta read | verified — store.py:893-901; 221 tests | — |
| Dropping `pairs` keeps anchor cost O(1) | verified — pairs is the only quadratic key; field shape fixed | AC3 records fixture 106 B + 86 B anchor-shape |

**Smallest change-list**

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|--------|-----------|--------------|----------------|-----|
| Attach bounded `cross_language` at standard; share bucket count with 183 attach | `code_atlas/tools/get_index_status.py` | MCP docstring; 183 tests still assert verbose-only for full field | G1,R1,R3,C1–C4 | 4/4 |
| Proving suite: multi-lang summary, linked:0, single-lang, pre-stamp, byte budget | `tests/test_cross_language_at_standard.py` | reuses 183 fixture helpers | AC1–AC4 | 4/4 |
| PLAN §12 cell: standard carries bounded census | `docs/PLAN.md` | R7.6 | R1, R7.6 | 1/1 |
| Working doc + ledger/lesson/backlog at finalise | `docs/tasks/243_…`, TOKEN_LEDGER, LESSONS, BACKLOG | bookkeeping | finalise | — |

**Recalled type-2 handles**

| # | Handle | Answer |
|---|--------|--------|
| 1 | `do-not-attest-past-the-payloads-resolution` | traced — `rg -n "stamped_cross_language_edges|stamped_edge_health_by_language" code_atlas/tools/get_index_status.py` → attach returns early when stamp None. Folded as C2/D1. |
| 2 | `cross-language-zero-needs-the-crossing-census` | traced — `rg -n "cross_language" code_atlas/tools/get_index_status.py code_atlas/store.py` → census nested in 183 stamp; D1 surfaces it at standard. |
| 3 | `stamp-at-the-builder-not-the-wrapper` | traced — attach called from `_status` before standard return (`get_index_status.py`), not a post-hoc wrapper. |

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **Proving test:** `.venv/bin/python -m pytest tests/test_cross_language_at_standard.py::test_standard_carries_bounded_cross_language_on_a_multi_language_index -q`

**Verification plan**

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|------------|----------------|--------------------|--------------|
| AC1 | logic | unit | n/a | ✅ |
| AC2 | logic | unit | n/a | ✅ |
| AC3 | logic | unit + recorded delta | n/a (shape fixed; pairs omitted) | ✅ |
| AC4 | logic | unit | n/a | ✅ |

No real corpus configured. AC1–AC4 are not input-shape-dependent (keys/presence on authored fixtures).

**Coverage-gap exclusions**

| Item | Risk tier | Why deferred | Follow-up | Expiry | Seen |
|------|-----------|--------------|-----------|--------|------|
| *(none)* | | | | | |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**AC3 measurement (recorded).** Fixture-scale `standard` delta = **106 bytes** (`linked: 0` and `linked: 2` shapes). Anchor-shape field JSON = **86 bytes** (`pairs` omitted — cost does not grow with language-pair count). Private anchor monorepo not mounted in this run.

- Rollback: revert the branch.
- **Gate 2 status:** cleared (autorun closes on artifacts)

## Decision log

| When | Decision | Why |
|------|----------|-----|
| t0 | reviewer off, challenger on | `/autorun 243 --no-reviewer` |
| refine | skip: yes | AC + constraints locked; design fork is HOW under handover |
| design | summary without pairs; field not suggestion | 061/223 + no remedial tool |

---

## Phase 3 — Execute

- **Branch:** `fix/243-the-capability-predicate-221-relies-on-is-attached-at-verbose-only`
- **Proving test added:** `tests/test_cross_language_at_standard.py::test_standard_carries_bounded_cross_language_on_a_multi_language_index`

- **Verification sweep — BOTH axes.**
  - File axis: diff ⊆ approved list ✅ (`get_index_status.py`, proving module, `PLAN.md`, this ticket) · each hunk maps to a row ✅
  - Behaviour axis: bounded summary at standard; 183 field stays verbose; pre-stamp/single-lang omit; linked:0 field signal — as approved

- **Design-conformance deviations:** none

- **Empirical output**

R6.5 red-before (production file reverted to base `0081474`; proving test present): AssertionError `assert 'cross_language' in {…}` — 1 failed. (Not an empirical-output fence for the tree under review.)

Post-change related suite:

Ran at 331e46a27a90a2547b51e0324ed1169376166a24
```
$ .venv/bin/python -m pytest tests/test_cross_language_at_standard.py tests/test_edge_health_per_language.py tests/test_get_index_status_health.py -q --tb=line
.....................                                                    [100%]
21 passed in 4.09s
```

AC3 recorded: fixture-scale standard delta **106 bytes**; anchor-shape field JSON **86 bytes** (pairs omitted).

- **Golden/snapshot change:** none
- **Design-invalidation / re-gate:** none

---

## Phase 4 — Review

- **Reviewer:** waived (`--no-reviewer`) — no rule-book-grounded review exists
- **Challenger:** ON — ticket-blind on raw ticket + product diff (working doc excluded)

**Challenger report (round 1):** 11 MET · 1 NOT MET (AC3).
**Fix:** AC3 recorded in raw ticket (86 B anchor-shape / 99 B with empty pairs / 106 B fixture delta).
**Challenger re-check:** 12 MET · 0 NOT MET · overall **clean**.

- **Scope reconciliation:** diff ⊆ approved list (product paths + bookkeeping)
- **Proving test:** green (5 passed in module)
- **Clean?** `clean (challenger only — REVIEWER: OFF)`
- **Reviewed at** `331e46a27a90a2547b51e0324ed1169376166a24`
- **Reviewed files:** `code_atlas/tools/get_index_status.py`, `tests/test_cross_language_at_standard.py`, `docs/PLAN.md`, `docs/tasks/243_the-capability-predicate-221-relies-on-is-attached-at-verbose-only.md` (working-doc path, exempt), `docs/LESSONS.md` (exempt), `docs/TOKEN_LEDGER.md`, `docs/BACKLOG.md`

### Review round 2 — maintainer review on PR #318

**Code: no finding.** The attach point is correct — `_attach_cross_language_summary` runs after the
`minimal` early return, so `minimal` is untouched; the bucket guard is now shared with
`_attach_edge_health_by_language` rather than duplicated; `stamped_cross_language_edges` already
returns `None` unless the block carries `linked`, so a pre-204 stamp cannot reach the indexing.
The bounded copy is deliberately repeated at `verbose` alongside the full nested census — noted and
accepted, since dropping it there would make the field's presence depend on `detail_level` twice.

**Finding (accepted, fixed): the branch was pushed gate-red.** No `scripts/gate.sh` run is recorded
in this working doc, and `docs/PLAN.md` stood at **23,288 tokens against a budget of 23,250**, so
`tests/test_doc_size_budget.py` was failing. Actions cannot run (the unbillable-Actions arrangement
AGENTS.md records), so nothing reported it.

**Fix:** paid §12's new row with R7.6 pruning in the same section — the `namespace_tree`
*considered and not planned* paragraph compressed to its decision, with §19 keeping the narrative —
and tightened the new `get_index_status` row itself (`pairs` named once, not twice).
`docs/PLAN.md` **23,232 → 23,219** after rebasing onto 242.

```
$ scripts/gate.sh
20 passed · 0 failed · 0 skipped
GATE GREEN — all 20 checks passed
```

## Phase 5 — Finalise

- **Stale-review guard:** product files unchanged since `331e46a`; bookkeeping (this doc, lessons, ledger, backlog) is exempt.
- **PR draft:** from `.github/pull_request_template.md`.
- **Planned outward actions:**
  - [x] push branch — handover authorisation
  - [x] open PR via `gh` — handover authorisation
  - [ ] merge — NOT authorised
  - [ ] tracker transition — NOT authorised
- **Durable lesson:** `243-C1` `capability-signal-on-the-first-call-channel` (proposed).
- **Revert path:** revert the branch / close the PR without merge.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Falsify of `243-C1`: still true — `rg -n "_attach_cross_language_summary" code_atlas/tools/get_index_status.py` shows the attach before the standard early return; without it, `test_standard_carries_…` fails (R6.5 red-before).

## Cost ledger

`LEDGER TOTAL: unmeasured · top cost driver: main-loop`

| Phase | Tokens |
|---|---|
| refine→design→execute (main-loop) | unmeasured |
| challenger ×2 (dispatch) | unmeasured |
| reviewer | waived |
