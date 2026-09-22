---
id: 319
slug: state-recomputes-the-summary-316-already-lifts
title: "316 put a lifted `summary` at the head of get_index_status, but the MCP server-instructions `_state()` still hand-composes its own one-line freshness sentence by reparsing the payload, so two independent ground-truth one-liners can disagree"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [316, 300]
---

## Why this exists (#422 follow-through — doc-surface sweep, not a field retro)

316 (#422) answered the field-retro batch's repeated ask — *"a one-line human summary at the top of
`get_index_status` so a routine is-it-fresh check does not reparse the payload"* — with a derived
`summary` string, single-sourced from the fields it precedes (`get_index_status.py` `_compose_summary`
/ `_with_summary`). But the **server-instructions channel builds its own one-liner the old way**:
`code_atlas/instructions.py:46-56` `_state()` reparses `status.get("indexed" / "files" / "nodes" /
"staleness")` and hand-assembles *"This repository is indexed and current: N files, M symbols."* That
is exactly the reparse pattern 316 set out to kill, now living one file over — and because the two
sentences are composed independently over the same status dict with no shared source, they can
disagree (e.g. `summary` folds edge-health `healthy` / `behind (read tools still serve)` nuance that
`_state()` does not). `_state()` is the very first sentence an anchor agent reads in its system prompt
(300), so a disagreement here is maximally visible.

## Goal

Make the server-instructions freshness sentence a single-sourced consumer of get_index_status's
`summary`, so there is one composed ground-truth one-liner, not two — or record an explicit decision
that the instruction channel needs its own terser wording and cite why.

## Scope / Deliverables

1. **`_state()` lifts `summary`** — read `status["summary"]` (316, present at every detail level incl.
   `minimal`, AC3) instead of recomposing from `indexed` / `files` / `nodes` / `staleness`. Keep the
   unbuilt-index branch's call-to-action wording that the summary already carries.
2. **One composition site** — if the instruction sentence and the payload sentence must differ in
   register, factor the shared compose into one helper both call (R6.7), rather than two hand-lists.
3. **Update `tests/test_server_instructions.py`** to assert the instruction sentence tracks the
   `summary` (mutate a staleness/count fixture → both move together), the red arm 316 gave the payload.

## Constraints

- R4.2: identical status → identical instruction text.
- 061 / 316 AC4: the structured payload and the `summary` field are unchanged — this only changes the
  consumer in `instructions.py`.
- `CA_TOOLS` may cut `get_index_status` from the surface; `_state()` still calls it directly for
  ground truth (it does today), so the summary is available regardless of the served roster.
- Comments ≤ 3 lines (R7.5).

## Acceptance criteria

- **AC1** The server-instructions freshness sentence is derived from get_index_status's `summary`, not
  a second reparse of the status dict — one composition site, greppable.
- **AC2** A test mutates a count/staleness fixture and both the payload `summary` and the instruction
  sentence change together, with no independent data path (mirrors 316 AC2).
- **AC3** The unbuilt / behind / current call-to-action wording an anchor agent acts on is preserved
  (no regression in what the first system-prompt sentence tells it to do).

## Out of scope

- The `summary` composition itself (owned by 316) and the structured payload shape.
- The `WHY` / `LOAD` / `KEEP_GOING` / `LIMITS` blocks of `instructions.py` — only `_state()` changes.

## References
`code_atlas/instructions.py:46-56` (`_state`), `:59-62` (`render`); `code_atlas/tools/get_index_status.py`
`_compose_summary` / `_with_summary`; `tests/test_server_instructions.py`;
[316](316_index-status-has-no-one-line-summary.md), [300](300_the-index-is-registered-permitted-and-never-chosen.md),
ENGINEERING_RULES R4.2 / R6.7.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 319 — instructions `_state()` single-sources on the 316 summary (working doc)
- **TIER:** full · **TRACK:** backend · **SCOPE:** S · **BASELINE:** green
- **Depends on:** 316 (done), 300 (done)
- **reviewer:** off (`--no-reviewer`) · **challenger:** on
- **Branch:** `fix/319-state-lifts-summary`
- **work_doc_mode:** embed
- **Run:** `/mango:autorun 319 --no-reviewer` (unattended; RUN CONTRACT `.mango/run-contract-319.txt`)

## Session status
- **Current phase:** finalise

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

refine skipped: 0 unresolved product-decisions. The ticket is fully specified against a strong existing
pattern (316's `summary`); the only open direction — lift the summary verbatim vs. keep a terser
instruction register — is a design-phase HOW bounded by AC1 (one composition site, derived), not a
product-decision the user owns. INPUT KIND: ticket.

**Premise (referenced-as-existing, all resolve):** `_state` (`instructions.py:46`),
`_compose_summary`/`_with_summary` (`get_index_status.py:311`/`:341`), `tests/test_server_instructions.py`,
tasks 316 / 300.

**Recalled claims (ADVISORY — surfaced only):**

| # | Claim | Type | Matched by (handle) | Relevant here? |
|---|-------|------|---------------------|----------------|
| 1 | 243/244 — get_index_status attached `cross_language` / `capabilities_by_language` only after the `standard` early return, so the first-call channel never saw them | 2 | get_index_status payload assembly / early-return placement | Mildly — 319 changes a *consumer* of that payload; the design must read `summary` from the same payload the first-call channel receives. Design's call, not recall's. |

---

## Phase 1 — Analysis

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Goal, Scope/Deliverables, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=4 R=3 G=1 AC=3`
`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R4.2 (change-type) ✅ | R6.7 (change-type) ✅ | R7.5 (change-type) ✅`
`BASELINE: green — via scripts/docker-test.sh`
`TRACK: backend — 0/2 touched files under UI paths`
`SCOPE: S`
`TIER: full`

**STRUCTURE:** native. **INPUT KIND:** ticket. **work_doc_mode:** embed (below the raw-ticket separator).

**Clarification (self-resolved, cited).** The one open direction — lift the `summary` string verbatim
vs. keep a terser instruction register — is settled by AC1 ("one composition site, derived") + R6.7
(one definition site): `_state()` returns the `summary` the payload already carries, adding no second
sentence. Cited: AC1 (ticket), R6.7 (`docs/ENGINEERING_RULES.md`), `get_index_status.py:341`
(`_with_summary` puts `summary` first at every level). j = 0.

**Baseline evidence.** `scripts/docker-test.sh pytest -q tests/test_server_instructions.py` → **7
passed in 3.11s (exit 0)**. Ran at `a6aca0f` (the tree under review; docs-only uncommitted edits do
not touch this test). Full suite `scripts/docker-test.sh` = **4351 passed / 5 skipped** measured
2026-09-22 on the same code tree. Bare-Windows: 6/7 pass; the 7th,
`test_an_indexed_repo_carries_its_own_counts`, fails because the index does not build bare on Windows
(the documented platform limitation in AGENTS.md — POSIX + adapters required), **not a regression**.
It is a **baseline exclusion** on bare-Windows only, green under Docker. DoD for later phases: prove
the delta green under Docker.

### Requirements matrix

| ID | Source | Verbatim (abridged) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | "single-sourced consumer of `summary`… or record an explicit decision" | `_state()` reads the `summary` field; no second composed one-liner | `instructions.py:46-56` recomputes today | open |
| R1 | Scope 1 | "`_state()` lifts `summary`… instead of recomposing from indexed/files/nodes/staleness" | Read `status["summary"]`; keep the unbuilt call-to-action the summary carries | `get_index_status.py:341` emits `summary` at every level | open |
| R2 | Scope 2 | "One composition site… factor the shared compose into one helper both call (R6.7)" | No hand-list duplicate of the summary; single derivation | R6.7; `_compose_summary` at `get_index_status.py:311` | open |
| R3 | Scope 3 | "Update `test_server_instructions.py`… mutate a staleness/count fixture → both move together" | Add the AC2 red arm; repoint the two assertions that hard-code the old wording | `test_server_instructions.py:60` asserts the old sentence | open |
| C1 | Constraint | "R4.2: identical status → identical instruction text" | Deterministic; pure function of the status dict | R4.2 | open |
| C2 | Constraint | "061 / 316 AC4: structured payload and `summary` unchanged" | Only the consumer in `instructions.py` changes | 316 AC4 | open |
| C3 | Constraint | "`CA_TOOLS` may cut `get_index_status`; `_state()` still calls it directly" | `_state()` calls `get_index_status.create(...)` for ground truth regardless of the served roster | `instructions.py:48` | open |
| C4 | Constraint | "Comments ≤ 3 lines (R7.5)" | Any new comment ≤ 3 lines | R7.5 | open |
| AC1 | AC | "instruction sentence derived from `summary`, not a second reparse — one composition site, greppable" | A test asserts `_state` uses `summary`; no reparse of indexed/files/nodes/staleness | falsifiable | open |
| AC2 | AC | "mutate a count/staleness fixture → payload `summary` and instruction sentence change together, no independent data path" | One red-arm test proving the shared source | falsifiable | open |
| AC3 | AC | "unbuilt / behind / current call-to-action wording an anchor agent acts on is preserved" | The CTA (run `build_or_update_index`) survives in each state's sentence | falsifiable | open |

### AC validation (falsifiability)

| AC | Stated value | Re-derived | Falsifiable? | Note |
|---|---|---|---|---|
| AC1 | derived-from-summary, one site | grep `_state` uses `summary`; no `staleness`/`files`/`nodes` reparse | yes | red-arm greppable |
| AC2 | both move together, no independent path | mutate fixture; assert `summary` ⊆ instruction text | yes | the proving test |
| AC3 | CTA preserved in 3 states | assert `build_or_update_index` present in unbuilt/behind text | yes | wording may change, CTA verb+tool preserved |

No unfalsifiable AC; no manual-check exclusion needed; no AC-value mismatch.

### Cause / gap · blast radius

- **Cause (`config.cause_taxonomy` = logic).** `instructions.py:46-56` `_state()` hand-composes a
  freshness sentence by reparsing the status dict — a second derivation of what 316's `summary`
  already single-sources. Duplication, not a wrong value; the two can diverge (edge-health nuance).
- **Gap.** Current: `_state()` recomposes. Target: `_state()` returns `status["summary"]` (indexed /
  behind / unbuilt all carry their CTA in the summary), one composition site.
- **Blast radius.** `_state()` ← `render()` (`instructions.py:59-62`) ← MCP server init; consumes
  `get_index_status`'s payload. Only `code_atlas/instructions.py` (code) + `tests/test_server_instructions.py`
  (test) change. No contract, no adapter, no store. Repo touched: `app` (`.`). No db-map.

**Gate 1 self-audit:** sections decomposed (4/4), AC table complete and all falsifiable, BASELINE
captured (green via Docker; bare-Windows exclusion recorded), j = 0, RULE SECTIONS covered, no
multi-clause want-decision to split (refine self-skipped), STRUCTURE/TRACK/TIER/SCOPE declared.
STOP at Gate 1 → (autorun closes it from these artifacts).

---

## Phase 2 — Design

`HANDLES: 1 recalled | 0 traced (command + result) | 1 does not apply (reason) | 0 unanswered`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
`SCOPE: S`

### Approach

`_state()` returns `get_index_status.create(config, ())()["summary"]` — the one-line ground truth
316 already single-sources in `_compose_summary` — instead of recomposing from `indexed` / `files` /
`nodes` / `staleness`. The summary is attached first at **every** detail level by `_with_summary`
(`get_index_status.py:341-343`) and already carries the call-to-action for each state (unbuilt:
`… — not indexed — run build_or_update_index`; behind: `behind … — run build_or_update_index`;
current: `current @ rev · N files · M symbols · healthy`). Verbatim lift → one composition site
(R6.7), deterministic (R4.2), CTA preserved (AC3).

### Rejected alternatives

- **Factor a shared helper both `_compose_summary` and `_state` call.** Rejected: there is nothing
  left for `_state` to compose once it lifts the summary — a helper would be one caller wrapping a
  single field read. The single composition site already lives in `get_index_status`; adding an
  indirection for one call site violates the smallest-edit rule (principle 2).
- **Keep `_state`'s fuller prose ("This repository is indexed and current: …") and merely re-derive
  it from summary.** Rejected: that is a second composed sentence, exactly the duplication AC1/R6.7
  forbid — the register difference is not worth a parallel derivation.

### Assumptions

| # | Assumption | Tag | Resolved by |
|---|---|---|---|
| A1 | `summary` is present on every `get_index_status` payload at every detail level | verified | `get_index_status.py:341-343` (`_with_summary` wraps `_status`/`_unbuilt`/`_mismatched`); 316 AC3 |
| A2 | The summary carries the CTA (`run build_or_update_index`) for unbuilt and behind states | verified | `get_index_status.py:327` (unbuilt), `:331` (behind) |

No `novel-untested` third-party/runtime assumption — the field and its content are read from this
repo's own code, confirmed by citation.

### Smallest change-list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `_state()` returns `status["summary"]`; drop the recompose branch | `code_atlas/instructions.py:46-56` | `render()` (`:59-62`) → `main.py:107` server init (pass-through, no assertion); changes the first system-prompt sentence — the ticket's intent | R1, R2, G1, C1, C3 | 1/1 |
| 2 | Repoint the two assertions that hard-code the old wording | `tests/test_server_instructions.py:40, :60` | none beyond the file — mechanical trace below found no other consumer of the old strings | R3, AC3 | 2/2 |
| 3 | Add the AC2 red-arm: monkeypatch `get_index_status.create` to a crafted status, assert `_state` returns its `summary`, mutate the summary, assert `_state` tracks it | `tests/test_server_instructions.py` (new test) | none | R3, AC1, AC2 | 1/1 |

**Test blast-radius (mechanical trace).** `grep "This repository is|indexed and current|not indexed
yet"` across `*.py` → only `instructions.py:50/55/56` (the code being changed) and
`test_server_instructions.py:40, :60` (folded in as change-list item 2). `grep instructions.render`
→ `main.py:107` (pass-through) + 7 test call sites, none asserting `_state`'s exact wording except
:40/:60. No golden, no other test root, no downstream consumer. Change-list is the complete set.

**HANDLES.** `get_index_status payload assembly / early-return placement` (243/244) — **does not
apply because** the `summary` field is attached at **every** detail level by `_with_summary`
(`get_index_status.py:341-343`, 316 AC3), so 319's consumer never reads a field gated behind the
`standard`-only early return the 243/244 claim concerns.

**FALSIFY.** A1 (summary present at every level) — checked against `_with_summary`'s three call sites;
still true. A2 (summary carries the CTA) — checked against the unbuilt/behind branches of
`_compose_summary`; still true. Neither is a runtime/3p assumption; both are cheaply checkable in
source.

### Rule compliance

- **R6.7** (one definition site): satisfied — the summary is composed once, in `get_index_status`;
  `_state` reads it, composing nothing.
- **R4.2** (deterministic, identical input → identical output): satisfied — `_state` becomes a pure
  read of a pure-function field.
- **R7.5** (comments ≤ 3 lines): the one docstring stays ≤ 3 lines.
- **316 AC4 / 061**: the structured payload and the `summary` field are untouched — only the consumer
  changes.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | logic | unit — assert `_state` returns the payload's `summary`, greps no `staleness`/`files`/`nodes` recompose | n/a | ✅ |
| AC2 | logic | unit — monkeypatch a crafted status; mutate its `summary`; assert `_state` output tracks it (shared source, no independent path) | n/a | ✅ |
| AC3 | logic | unit — unbuilt and behind summaries carry `build_or_update_index`; the repointed integration test 44 confirms the current-state sentence | n/a | ✅ |

No input-shape-dependent AC (each asserts an equality/containment whose expected value is writable up
front) → no corpus wanted, no coverage-gap exclusion.

### Proving test

`tests/test_server_instructions.py::test_state_single_sources_on_the_index_status_summary` (new,
AC2 red arm): crafts a status whose `summary` is a sentinel, monkeypatches `get_index_status.create`
to return it, asserts `_state`/`render` surface the sentinel; mutates the sentinel and asserts it
tracks. **Fails pre-change** (`_state` recomposes and never echoes the sentinel summary), **passes
post-change**. Invocation: `pytest tests/test_server_instructions.py` (runs bare and in Docker; the
new tests need no index build).

### Rollback + porting

Rollback: `git revert` the single commit — the change is one function body + test edits. Porting:
single repo (`app`); no shared-code porting.

**Gate 2 self-audit:** HANDLES u=0 and h==t+x (1==0+1), every change-list item traces to a matrix
row with k/N, assumptions all `verified` (no unresolved novel-untested 3p/runtime), proving test
named and runnable at the risk layer, verification plan has no ❌, EXCLUSIONS line e==n and s-c≤n
(all zero), rollback + porting recorded, SCOPE S unchanged. STOP at Gate 2 → (autorun closes it).

---

## Phase 3 — Execute

**Axis 1 — file set.** `git diff --stat` (code) = `code_atlas/instructions.py` (16),
`tests/test_server_instructions.py` (40) — both inside the approved change list, no third file, no
untouched-line reformatting. Diff ⊆ approved list ✅. Each hunk maps to a matrix row: `_state` body →
R1/R2/G1; the two repointed assertions → R3/AC3; the new red-arm test → R3/AC1/AC2. No stray
symbol/import (mypy clean below).

**Axis 2 — design conformance.** The one Approach bullet — `_state()` returns
`get_index_status.create(config, ())()["summary"]` — is `implemented-as-approved`. No deviation.

### Empirical output (`Ran at a6aca0f` working tree; Docker image built from the same)

Pre-change red arm (stash `instructions.py` only, run the new test):
```
FAILED tests/test_server_instructions.py::test_state_single_sources_on_the_index_status_summary
 = 'This repository is indexed and current: 7 files, 9 symbols.\n\n…'.startswith('SENTINEL …')
1 failed in 1.17s
```
Post-change, full proving file **in Docker** (`scripts/docker-test.sh pytest -q tests/test_server_instructions.py`):
```
8 passed in 1.72s   [exited with code 0]
```
Bare-Windows (same file): `1 failed, 7 passed` — the 1 is `test_an_indexed_repo_carries_its_own_counts`,
the recorded baseline exclusion (index does not build bare on Windows), green in Docker above. Lint/type:
```
ruff check code_atlas/instructions.py tests/test_server_instructions.py → All checks passed!
mypy code_atlas/instructions.py tests/test_server_instructions.py → Success: no issues found
```

**Ph3/4 proven by:** `tests/test_server_instructions.py::test_state_single_sources_on_the_index_status_summary`
(red pre-change, green post-change) + the repointed `test_an_unindexed_repo_…` / `test_an_indexed_repo_…`.
Full-suite delta-green on the committed tree is stamped in Phase 4. No scope growth (SCOPE S holds);
no golden re-recorded (the two assertion edits are the ticket's intended behaviour change, traced to R3).

---

## Phase 4 — Review

`REVIEWER: OFF (--no-reviewer)`
`CHALLENGER: ON`

**Verdict: clean (challenger only — REVIEWER: OFF).**

**Challenger (ticket-blind, raw ticket + code diff only).** Overall **CLEAN**: 3/3 deliverables MET,
3/3 ACs MET, 4/4 constraints MET, 0 not-met, 0 can't-tell. It independently re-ran the proving file
and, to rule out a regression, checked out `main` in an **isolated `git worktree`** and confirmed
`test_an_indexed_repo_carries_its_own_counts` **fails identically on `main`** for the same reason
(bare-host build lands `incomplete`, not `current`) — i.e. the recorded baseline exclusion, **not a
regression**. Non-blocking caveats it raised: (AC2) the new test mutates a mocked payload's `summary`
key rather than a staleness/count fixture that `_compose_summary` recomputes — judged "valid,
arguably stronger wiring proof," and the two repointed tests exercise the real `_compose_summary`
path end-to-end; (AC3) the behind-state CTA is proven via the mocked test, same coverage as pre-319.
One independence disclosure (carried to DISCLOSURE): a `git diff -- docs` it ran for the scope check
surfaced ~35 lines of the embedded working doc, but its requirement rebuild predated the leak and was
not shaped by it.

**Scope reconciliation (both axes).** File axis: diff = `code_atlas/instructions.py` +
`tests/test_server_instructions.py` (+ the embedded working doc, `work_doc_mode: embed`) — ⊆ approved
list, no untouched-line reformat. Behaviour axis: the one Approach bullet implemented as approved; no
deviation. Challenger independently found no scope creep.

**Proving test / gate — evidence on the tree under review (`Ran at 4c924b9`).**
```
scripts/docker-test.sh (ruff + mypy + pytest, full suite) → 4354 passed, 5 skipped in 306s [exit 0]
```
GATE GREEN — delta-green: no new failure, the env-fault test passes in Docker, lint + types clean.
Proving test green; `k = N` on every matrix row (all MET); no layer-match ❌ (all ACs logic-layer,
proven at the logic layer).

**Reviewed at `4c924b9`** — reviewed files: `code_atlas/instructions.py`,
`tests/test_server_instructions.py`. Working-doc path (exempt from the staleness comparison):
`docs/tasks/319_state-recomputes-the-summary-316-already-lifts.md` (embedded). Clean → proceed to finalise.

---

## Phase 5 — Finalise

**Stale-review guard.** `git diff --name-only 4c924b9..HEAD` ∪ uncommitted = only the embedded working
doc + the bookkeeping files (`BACKLOG.md`, `TOKEN_LEDGER.md`) mango writes at finalise — all exempt.
Non-exempt reviewed files (`instructions.py`, the test) unchanged → **not stale**.

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

**Durable lesson: none.** The run applied an existing rule rather than discovering a new one — a
lifted/aggregate field (316's `summary`) leaving a hand-composed consumer of the same fact (`_state`)
is the R6.7 "one definition site" case, already codified. No new constraint, no wrong assumption
(design held end-to-end), no process gap (every gate closed on its artifacts). Nothing to promote.

### Cost ledger

`LEDGER TOTAL: 82,664 tokens (1 dispatch) · top cost driver: review/challenger`

One subagent dispatch this run — the ticket-blind `challenger` (82,664 fresh, from its handback usage
block). `reviewer` waived by `--no-reviewer`. Main-loop spend is **unmeasured** (the host surfaces
subagent dispatch only; `rtk gain` is global, not per-ticket). Ledger complete: one row per dispatch,
each with a value. Recorded in `docs/TOKEN_LEDGER.md` row 319.

### Outward actions (each pre-authorised by the handover — push branch + open PR only)

1. `git push -u origin fix/319-state-lifts-summary` (carries the fix, working doc, and the
   bookkeeping so the ledger/BACKLOG reach a shared ref — not orphaned).
2. `gh pr create` from `.github/pull_request_template.md` (CONVENTION §7).

No other outward action (no merge, no tracker transition, no force-push) — those stay for the human.

### Revert path

Revert the single fix commit (`git revert 4c924b9`), or close the PR and delete
`fix/319-state-lifts-summary`. The change is one function body + test edits; no migration, no data.
