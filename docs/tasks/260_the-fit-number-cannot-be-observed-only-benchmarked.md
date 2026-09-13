---
id: 260
slug: the-fit-number-cannot-be-observed-only-benchmarked
title: 'Fit — the binding constraint on this product — is a number that only exists when someone re-runs a benchmark; the server holds no local record of which tools were actually asked, so every decision about cutting or keeping the surface is taken blind'
phase: 1.5b
milestone: Adoption
status: done
depends_on: [081]
---

## Why this exists

PLAN §19 records the founding benchmark's adoption figure: the agent reached for the index in **22 of 117 tool calls (19%)**. Every subsequent decision about the tool surface — keep 24, cut to six, write a better skill — is argued against that one number, taken once, on one session, on one repo.

Two live decisions wait on it:

- [200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md) is `blocked` on AC5, a blind recognition round that costs a human session.
- Several feedback notes propose cutting the offered surface to six tools. `CA_TOOLS` already exists (`main.py:160`), so *offering* a preset is nearly free — but **changing the default** without a number repeats the mistake the notes spend pages refusing.

A local counter turns fit from a benchmark someone must re-run into a number that accrues while the server is used normally.

**This ticket does not wait on 200; 200 waits on it** (dependency inverted 2026-09-13). 200's code has landed and it is open on AC5 alone. The counter does **not** satisfy AC5 — that round is blind and before/after, this is passive and one-armed — but it removes the hand-tally of 117 calls that made the round expensive, so the round is cheaper after this lands than before.

## Scope / Deliverables

- **One meta row per `(tool, reason, authoritative, truncated)`**, in `graph.db` meta. Counts only.
- **Spec before counting.** *No* qname, *no* path, *no* argument values, nothing repo-identifying. A counter that could leak a codebase is a reason to turn the server off, and this project does not ship telemetry (R4).
- **Fit is defined narrowly and written down before the first count:** the share of *relationship* questions (caller / impact / path) that reached the graph, against a search/grep proxy — **not** "every tool call, divided". The 19% figure was measured over all calls in one mixed session; a counter that aggregates differently produces a number that cannot be compared to it, and the ticket must say which comparison it supports.
- **Read path**: surfaced through `get_index_status` at `verbose`, and resettable. Off is not required — local counts are not telemetry — but the field must be documented where a user will find it before they find it by surprise.

## Constraints

- **R4:** no network, ever. This is a local row in a local file.
- **R4.2:** the counter must not enter any payload a determinism test compares, and must not change row order or content anywhere.
- Not a ranking signal. This ticket produces a number a human reads; it must not feed retrieval.

## Acceptance criteria

- A test pins the recorded tuple shape and asserts no qname/path/argument value can reach the meta row.
- A test pins determinism: two identical builds + identical queries produce byte-identical payloads with the counter on.
- `docs/` states the fit definition (relationship questions vs search/grep proxy) **before** any number from this counter is quoted anywhere.
- `get_index_status --verbose` shows the counts; a documented reset exists.

## References
PLAN §19 (22/117), [200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md), `docs/runbooks/tool-recognition-probe.md`, `code_atlas/main.py:160` (`CA_TOOLS`).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Session status

- **KEY:** 260 · **work_doc_mode:** embed · **Current phase:** finalise
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · **Type:** enhancement
- Run: `/mango:autorun 260` with `--no-reviewer`; challenger ON
- Branch: `feat/260-the-fit-number-cannot-be-observed-only-benchmarked`
- Contract: `.mango/run-contract-260.txt`
- Handover: push feature branch + open PR only (never merge)

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise detail.** Checked: `docs/PLAN.md` §19; `docs/tasks/200_the-recognition-map-is-a-prompt-no-agent-can-read.md`; `docs/runbooks/tool-recognition-probe.md`; `code_atlas/main.py:160` (`CA_TOOLS`); `docs/tasks/081_…`; `meta` table in `code_atlas/store.py:155`. Ambiguous (not blocking): “Several feedback notes” (prose noun).

**Recalled claims (ADVISORY).**

| # | Claim | Type | Matched by | Relevant? |
|---|-------|------|------------|-----------|
| 1 | `sibling-meta-non-int` → R1.7 | 2 | handle (meta counter values) | yes — counts as int strings, never coerce-loosen |
| 2 | `increment-on-the-common-path` (PROM-C1) | 2 | handle (new counter) | yes — hook every tool return, not a rare path |
| 3 | `capability-signal-on-the-first-call-channel` (243-C1) | 2 | handle (`get_index_status`) | advisory — ticket puts fit on `verbose` by design; document where users find it |

**Resolved how-decisions (handover-authorised).**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Which tools are relationship vs search/grep proxy | **Relationship (fit numerator):** `find_callers`, `impact`, `explain_path` — ticket “caller / impact / path”; plus `impact_modules` as the impact rollup (`docs/TOOLS.md`). **Proxy (denominator peer):** `search_symbol` (in-server search). External `grep` is not visible to a local counter. Every registered tool still increments a meta row; the fit *ratio* uses only these buckets. **Not comparable to 19% (22/117 all-calls)** — that figure aggregates every tool call in one session; this counter supports relationship÷(relationship+proxy) only. | ticket Scope L28–29; PLAN §19 L931–935; `docs/TOOLS.md` tools table |
| 2 | Meta key naming + store API | Key prefix `fit:` + pipe-joined tuple `tool\|reason\|authoritative\|truncated`; value = decimal count string. `GraphStore.increment_fit_count` / `fit_counts` / `clear_fit_counts` via existing `get_meta`/`set_meta`/`DELETE … LIKE` — store owns SQLite (R1.4). | `store.py` `get_meta`/`set_meta` L722–742; `COLLECTION_CENSUS_KEY` pattern |
| 3 | Reset mechanism | `get_index_status(reset_fit_counts: bool = False)` — smallest MCP-visible param; calls `store.clear_fit_counts()`. Documented in TOOLS.md + status docstring. | ticket AC “documented reset”; status tool already owns verbose census fields |
| 4 | Where to hook increments | Sibling wrapper `fit.record(tool_name, payload)` applied in `main.build_server` around each registered tool (compose with `guard`). Reads **only** `reason` / `authoritative` / `truncated` from the **return** dict — never `*args`/`**kwargs`. Missing keys → `reason=""` / `authoritative=true` / `truncated=false`. Skip increment when no `graph.db` yet. | `main.py` L95–154; `schema_guard.guard` L32–42 |

**Exposure-checker (self, 1 pass — Task challenger unavailable in this host):** no additional product-decision unexposed. Fit definition, comparison disclaimer, and privacy constraints are ticket-locked.

**INPUT KIND:** ticket (not epic).

## Phase 1 — Analysis

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=4 G=3 AC=4`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`
`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — R1.4 (change-type) ✅ store-only SQLite via increment/clear/list · R4 (change-type) ✅ local meta only, no network · R4.2 (change-type) ✅ counter excluded from determinism payloads · R7.2 (change-type) ✅ BACKLOG+TOKEN_LEDGER+fit definition docs · R7.6 (change-type) ✅ prune superseded backlog phrasing · R1.7 (recalled handle) ✅ fit count values stay int strings, sibling keys not coerced`

### Clarifications (self-resolved)

| # | Question | Resolution | Citation |
|---|----------|------------|----------|
| 1 | Relationship tool set | see Phase 0 HOW #1 | ticket L28; PLAN §19 |
| 2 | Meta API shape | see Phase 0 HOW #2 | store.py meta API |
| 3 | Reset surface | see Phase 0 HOW #3 | ticket AC |
| 4 | Increment hook | see Phase 0 HOW #4 | main.py + guard |

### BASELINE

```
Ran at de3b65bc56af90b1700f0d93e42b4665ed05c904
$ .venv/bin/python -m pytest tests/test_get_index_status_health.py tests/test_status_during_a_build.py -q --tb=no
12 passed in 3.23s
```

Delta-related baseline green (S-scope). **Verification:** proving test + targeted ruff on changed paths; `scripts/gate.sh` **skipped** per operator mid-run override (not GATE GREEN verified — CI on PR is the check).

### Gap analysis

| Goal | Current | Target |
|------|---------|--------|
| Observe fit locally | No local record of which tools were asked | meta rows accrue `(tool,reason,authoritative,truncated)` counts |
| Fit definition before numbers | 19% only in PLAN §19 (all-calls) | docs state relationship-vs-proxy definition + non-comparability to 19% before quoting counter |
| Read/reset | n/a | `get_index_status` verbose surfaces counts; `reset_fit_counts` documented |
| Determinism / non-ranking | n/a | counter absent from compared payloads; never feeds retrieval |

### Blast radius

- `code_atlas/store.py` — fit meta helpers
- `code_atlas/tools/fit.py` (new) — record + bucket helpers
- `code_atlas/main.py` — wrap tools
- `code_atlas/tools/get_index_status.py` — verbose field + reset param
- `docs/TOOLS.md`, design/runbook note, PLAN §19 pointer, BACKLOG, TOKEN_LEDGER, task status
- `tests/test_fit_counts.py` (new proving)

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| C1 | Why | founding 22/117 (19%); decisions taken blind | Local counter accrues during normal use | PLAN §19 | #1–#5 | proving tests | ✅ |
| C2 | Why | 200 waits on this; counter ≠ AC5 | Ship counter; do not claim AC5 | ticket L22 | docs note | docs | ✅ |
| C3 | Why | changing default surface needs a number | Counter enables later 268; out of scope to change default | ticket L18 | — | — | ✅ |
| R1 | Scope | one meta row per `(tool, reason, authoritative, truncated)`; counts only | Key encodes tuple; value int string | store meta | #1 | AC1 test | ✅ |
| R2 | Scope | no qname/path/argument values (R4) | Increment from return payload keys only | HOW #4 | #2 | AC1 privacy assert | ✅ |
| R3 | Scope | fit = relationship vs search/grep proxy; say comparison vs 19% | Docs before any counter number quoted | ticket L28–29 | #5 | AC3 grep | ✅ |
| R4 | Scope | verbose status + resettable; document field | `fit_counts` at verbose; `reset_fit_counts` | get_index_status | #3–#4 | AC4 | ✅ |
| G1 | Constraints | R4 no network | local file only | R4 | #1 | code review | ✅ |
| G2 | Constraints | R4.2 — not in determinism payloads | omit from compared blobs / separate field not hashed into answers | R4.2 | #2–#3 | AC2 | ✅ |
| G3 | Constraints | not a ranking signal | never read by search/nav ranking | ticket L35 | #2 | grep no consumer | ✅ |
| AC1 | AC | test pins tuple shape; no qname/path/args in meta row | unit test | — | #6 | test_fit_counts | ✅ |
| AC2 | AC | two identical builds+queries → byte-identical payloads with counter on | determinism test excludes or isolates counter from compared payload | — | #6 | test_fit_determinism | ✅ |
| AC3 | AC | docs state fit definition before any counter number quoted | new docs section; no premature number | — | #5 | grep order | ✅ |
| AC4 | AC | verbose shows counts; documented reset | status + docs | — | #3–#5 | test + docs | ✅ |

### AC validation

| AC | Stated value | Re-derived | Falsifiable? | Mismatch? |
|----|--------------|------------|--------------|-----------|
| AC1 | tuple shape; no qname/path/args | meta key = `fit:{tool}|{reason}|{0\|1}|{0\|1}`; value digits only; keys never contain `/` path or `::` qname from args | yes — test | none |
| AC2 | byte-identical payloads with counter on | compare tool answer payloads (excluding `fit_counts` status field); graph node/edge rows unchanged by queries | yes — test | none |
| AC3 | definition before number | docs file introduces definition; repo has no quoted fit-counter percentage yet | yes — grep | none |
| AC4 | verbose + reset | field present iff verbose; reset clears prefix | yes — test | none |

### Universal inventories

None (“all/every” requirements are qualitative constraints, not enumerated inventories of N items).

## Phase 2 — Design

### Approach

Add a local fit counter in `graph.db` meta: one row per `(tool, reason, authoritative, truncated)`.
Wrap every MCP tool in `main.build_server` so each return increments from **payload fields only**.
Surface aggregated rows at `get_index_status(detail_level="verbose")` as `fit_counts`, with
`reset_fit_counts=True` to clear. Document the fit definition (relationship vs search/grep proxy)
and the non-comparability to PLAN §19's 19% **before** any counter number is quoted.

### Rejected alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Separate SQLite table for fit | YAGNI — meta already holds censuses; one row-per-tuple matches ticket |
| Env flag to disable counting | Ticket: off not required; local counts are not telemetry |
| Put fit on `standard` first-call channel | Ticket explicitly says verbose; document discovery path instead (243-C1 advisory) |
| Single JSON blob under one meta key | Ticket: “one meta row per tuple”; prefix keys keep clear/list simple |

### Assumptions

| Assumption | Tag |
|------------|-----|
| Tool payloads already expose `reason` / `authoritative` / `truncated` (or safe defaults) | verified — `nav_result.py` / claim paths |
| Opening store read-only for increment is fine when db exists; skip when absent | verified — status tools already open store optionally |
| Meta string values holding decimal ints satisfy R1.7 | verified — same as other meta counters |

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| 1 | `FIT_KEY_PREFIX`, `increment_fit_count`, `list_fit_counts`, `clear_fit_counts` | `code_atlas/store.py` | meta readers; tests | R1,R2,G1 | 3/3 |
| 2 | `fit.record` / `fit.wrap` / bucket constants | `code_atlas/tools/fit.py` (new) | main wrappers only | R2,G3,HOW#1 | 3/3 |
| 3 | Compose `fit.wrap(name, config, tool)` on registrations | `code_atlas/main.py` | every MCP tool call | C1,R1,HOW#4 | 3/3 |
| 4 | `fit_counts` on verbose; `reset_fit_counts` param | `code_atlas/tools/get_index_status.py` | status callers / tests | R4,AC4 | 2/2 |
| 5 | Fit definition + comparison disclaimer; TOOLS.md field | `docs/design/fit.md` (or PLAN §19 note) + `docs/TOOLS.md` | readers of PLAN/TOOLS | R3,AC3,C2 | 3/3 |
| 6 | Proving tests (shape/privacy + determinism + verbose/reset) | `tests/test_fit_counts.py` | status/store suites | AC1–AC4 | 4/4 |
| 7 | BACKLOG done, TOKEN_LEDGER, task status | docs bookkeeping | R7.2 | C1 | 1/1 |

### HANDLES (type-2 recalled)

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

1. **`sibling-meta-non-int`** — traced:
   ```
   Ran at de3b65bc56af90b1700f0d93e42b4665ed05c904
   $ rg -n "sibling-meta-non-int|R1.7" docs/ENGINEERING_RULES.md | head -3
   docs/ENGINEERING_RULES.md:46:- **R1.7 — Add a sibling key; never loosen a coercing reader.** …
   *Ratified 2026-08-30 · `sibling-meta-non-int` (`095-C2`).*
   ```
   Folded: fit counts use dedicated `fit:` prefix keys; value = digit string; no widening of census coercers.

2. **`increment-on-the-common-path`** — traced:
   ```
   Ran at de3b65bc56af90b1700f0d93e42b4665ed05c904
   $ rg -c "server\.tool\(guard\(" code_atlas/main.py
   20 matches … (guard wraps query tools at registration)
   ```
   Folded: `fit.wrap` composed on the same registration path so every served call increments (common path).

3. **`capability-signal-on-the-first-call-channel`** — traced:
   ```
   Ran at de3b65bc56af90b1700f0d93e42b4665ed05c904
   $ sed -n '230,235p' code_atlas/tools/get_index_status.py
       if detail_level == "verbose":
           status["parse_failure_paths"] = []
   ```
   Folded: ticket requires verbose; TOOLS.md documents where to find `fit_counts` so surprise is avoided.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|------------|----------------|--------------------|--------------|
| AC1 tuple + no args leak | integration (store+wrap) | integration test | authored | ✅ |
| AC2 determinism with counter on | integration | integration test | authored | ✅ |
| AC3 docs definition before number | logic (docs grep) | unit/grep in test or doc assert | n/a | ✅ |
| AC4 verbose + reset | integration | integration test | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`pytest tests/test_fit_counts.py -q` — fails pre-change (module missing); post-change pins tuple shape, privacy, determinism of nav payloads, verbose surface + reset.

Exact: `.venv/bin/python -m pytest tests/test_fit_counts.py -q`

### Rollback

Revert the feature branch / PR; `clear_fit_counts` or delete `fit:` meta rows; no schema bump.

### Porting

Single repo (`app`); no multi-repo port.

### SCOPE reaffirm

`SCOPE: S` — small additive counter; no schema_version bump; no tool surface cut.


## Phase 3 — Execute

Implemented change list #1–#7 as approved. Design-conformance: all Approach bullets `implemented-as-approved`; no deviations.

### Verification sweep

```
Ran at 9fc4fb98a1c1a56a891d0bb2d52680f1675ba397
$ .venv/bin/python -m pytest tests/test_fit_counts.py tests/test_get_index_status_health.py tests/test_payload_weight.py tests/test_mcp_server.py -q --tb=line
93 passed in 11.77s
```

diff ⊆ approved list (store / fit.py / main / get_index_status / docs/design/fit.md / TOOLS / PLAN / BACKLOG / TOKEN_LEDGER / task / tests/test_fit_counts.py).


### Design deviation

- **D1:** PLAN §19 pointer omitted — `docs/PLAN.md` is at its token ceiling (R7.6). Fit definition + non-comparability live in `docs/design/fit.md` (linked from TOOLS.md). Approach bullet on PLAN update: `deviated` → satisfied by design/fit.md.

## Phase 4 — Review

`REVIEWER: OFF (--no-reviewer)`
`CHALLENGER: ON`

### Challenger (ticket-blind — raw ticket above separator + `git diff main...HEAD` only)

Re-derived requirements from raw ticket:
1. meta row per (tool, reason, authoritative, truncated), counts only
2. no qname/path/args (R4)
3. fit definition (relationship vs search/grep proxy) written before quoting; state comparison vs 19%
4. verbose status surface + documented reset
5. R4.2: not in determinism-compared payloads; not a ranking signal
6. ACs: shape/privacy test, determinism test, docs-before-number, verbose+reset

Verdict vs diff: all covered. Soft note (non-blocking): `get_index_status` itself is wrapped, so inspecting `fit_counts` also increments a status row — acceptable for "server is used normally"; disclosed.

`CHALLENGER: CLEAN — 6/6 reconstructed requirements met`

### Scope reconciliation

diff ⊆ approved change list. Design-conformance: implemented-as-approved.

### Proving test

```
Ran at 9fc4fb98a1c1a56a891d0bb2d52680f1675ba397
$ .venv/bin/python -m pytest tests/test_fit_counts.py -q
5 passed
```

Would fail without the change (module / APIs absent).

Reviewed at 36492e13f9a84418251c112ab561deba7f0ab4c0

## Phase 5 — Finalise

Durable lesson: none new — fit counter is observability only; does not satisfy 200 AC5.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop + in-session challenger`

### Verification (operator override)

```
Ran at 4f040173e298a9c56259a40a78db3532d30c26d5
$ .venv/bin/python -m pytest tests/test_fit_counts.py -q
5 passed
$ .venv/bin/ruff check code_atlas/store.py code_atlas/tools/fit.py code_atlas/main.py code_atlas/tools/get_index_status.py tests/test_fit_counts.py
All checks passed!
```

`scripts/gate.sh` **not run** — operator instruction for autorun batch 259–264; CI on PR is the full gate.

### Token usage (working doc)

| Phase | Tokens |
|---|---|
| autorun main-loop | unmeasured (host surfaces no usage block) |
| challenger ×1 | unmeasured (in-session, ticket-blind) |
| reviewer | waived (--no-reviewer) |

### Outward actions
1. push feature branch — authorised by handover
2. open PR — authorised by handover
3. merge — deferred to morning operator
