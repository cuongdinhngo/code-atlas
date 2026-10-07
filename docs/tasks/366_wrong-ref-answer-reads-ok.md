---
id: 366
slug: wrong-ref-answer-reads-ok
title: 'An answer about a ref other than HEAD reads reason ok, so an agent in a worktree trusts main'
phase: 2
milestone: Adoption
status: done
depends_on: [354, 360]
---

## Why this exists

This comes from the anchor project's field retro.

- F1 (1 PR): after a branch switch, `find_callers` answered for an `answered_about_ref` on another
  branch, and one hit came back `source_stale`. Only a metadata field showed the mismatch.
- F2 (3 PRs): a second developer did not use code-atlas at all, because "the index in a
  worktree answers about `main`" while still reporting `reason: ok`. The anchor project's agent
  guide lists this as a standing trap.

**Prior art.** 268 (`worktree_guard.py`) already refuses with `index_root_mismatch`, but only when
the *server's* root is a linked worktree whose `CA_DB_PATH` points outside it. The field case is a
server rooted at main while the agent works in a worktree. A stdio server's root is fixed at launch,
so it cannot see the caller's checkout unless the client reports it: the MCP `roots` capability is
the only route.

F1 is a different case: a branch switch in the same tree. Per-subject staleness answers `ok`
for a subject unchanged between the two revisions, by 257's design. Reproduce it before deciding
whether it is a defect.

## Scope

1. When the client reports MCP `roots` and the HEAD of the index root differs from the HEAD of
   the caller's root, the answer's `reason` says so (`ref_mismatch`). The answer carries both
   revisions and is not `ok`. A client that reports no roots gets today's answer, and
   `get_index_status` says that the check could not run.
2. The `get_index_status` summary names the mismatch and the route to fix it: a per-worktree index,
   or a refresh.

## Acceptance criteria

- **AC1:** An index is built at commit A and queried from a worktree at commit B. Every navigation
  tool answers `reason: ref_mismatch` with both revisions.
- **AC2:** When HEAD matches, or the client reports no roots, answers are byte-identical.
- **AC3:** The server `instructions` still fit `CLIENT_CAP` (343).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 366 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews and merges the PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`, batch 365 → 366 → 361 → 362 → 364 → 363;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `feat/366-wrong-ref-answer-reads-ok` from `main` (`fb256ec5`). Contract `.mango/run-contract-366.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 6 want-decision asked | 6 how-decision resolved+cited | 6 ASSUMED | skip: no`

**Premise.** All six resolve: `worktree_guard.py`, `index_root_mismatch` (`nav_result.py:70`),
`answered_about_ref` (`nav_result.py:339`), `get_index_status`, `CLIENT_CAP` (`instructions.py:19`),
`source_stale`. Ambiguous: "the anchor project's agent guide" (outside this repo).

**Recall (by handle — a new core module other modules import).** `343-C2`
`formatter-rewrites-untouched-lines`. Retired skipped: `349-C1`.

**Spikes before design.** (1) A probe MCP server under `claude -p --strict-mcp-config` (Claude Code
2.1.292) logged `["file:///…/roots/work", "file:///tmp"]` — the working directory first, then the
additional directories. (2) FastMCP 3.4.5: `Context.list_roots` from a client without the
capability raises `ToolError: List roots not supported`. (3) A ContextVar set in `on_call_tool`
middleware reached a sync tool running on `AnyIO worker thread`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 48,402 tokens) surfaced X1–X12. The six
want-decisions were handed back by the run's handover and are **ASSUMED (awaiting ratification)**.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | compare with the index root's live HEAD or the built commit | want | **ASSUMED:** the built commit (`meta.last_commit`) — the answer is about it, and AC1 reads "an index is built at commit A". A moved main HEAD is `behind`, which staleness already reports. Deviation from Scope 1's wording (P3) |
| X2 | which root counts | want | **ASSUMED:** any root that *is* the index root → no check (the caller can see that checkout); else the first root, in client order, that is another checkout of the same repository (same `--git-common-dir`, different top level). Unrelated roots are ignored |
| X3 | replace the reason or sit beside it | want | **ASSUMED:** `reason` becomes `ref_mismatch`, the rows stay, and the previous reason moves to `reason_at_index`. A refusal that returns before the tool runs (`index_root_mismatch`, schema mismatch) is untouched: the guard returns it first (`schema_guard.py:56-58`) |
| X4 | "every navigation tool" and the field names | want | **ASSUMED:** every query tool the guard wraps — all but `build_or_update_index` (`main.py`); `index_commit` / `caller_commit` / `caller_root`. `get_index_status` keeps no reason and names the route in `summary` |
| X5 | cost per call | how | the git check runs only when no root is the index root, i.e. only in the worktree case; checkout identity is cached per root path, HEAD read per call so a commit in the worktree is seen. The common case adds no subprocess (260's bar, `schema_guard.py:44-47`) |
| X6 | when to read roots | how | once per session in middleware, cleared on `notifications/roots/list_changed`; a 5 s bound so a silent client never holds a call |
| X7 | "or a refresh" | how | dropped: a refresh rebuilds main's index at main's HEAD and cannot fix a worktree's mismatch (`worktree_guard.py:28-49`, 268). Route: a per-worktree index. Deviation (P3) |
| X8 | F1 (branch switch in one tree) | want | **ASSUMED:** not a defect here — an unchanged subject on a behind index answering `ok` is 257's default (PLAN §19 `serve_behind`), which 365 kept; out of scope |
| X9 | how "the check could not run" shows | want | **ASSUMED:** `ref_check: client_reported_no_roots` on `get_index_status` only; navigation answers stay byte-identical (AC2) |
| X10 | where the check lives | how | `schema_guard.guard`, beside `attach_build_state` (`schema_guard.py:66-73`), which already wraps every query answer |
| X11 | contract bump | how | none: `NavReason` is payload vocabulary in `nav_result.py`; R3.1's bump covers node/edge vocabulary and the qname convention (`contract.py`) |
| X12 | AC3 | how | `instructions.render` is unchanged; `tests/test_server_instructions.py` keeps the cap |

## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=3`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/11 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

`main` at `fb256ec5` has the tree of `4e05c246`, on which `scripts/gate.sh` printed
`GATE GREEN — all 21 checks passed`. Ran at 4e05c246.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | title | "an agent in a worktree trusts main" | an answer about another commit is never `ok` | ✅ |
| C1 | Why | "the MCP `roots` capability is the only route" | the server learns the caller's checkout only from `roots` | ✅ |
| R1 | Scope 1 | mismatch → `ref_mismatch`, both revisions, not `ok` | guard label (X1–X4) | ✅ |
| R2 | Scope 1 | no roots → today's answer; status says the check could not run | X9 | ✅ |
| R3 | Scope 2 | status summary names the mismatch and the route | X7 | ✅ |
| AC1 | AC | built at A, worktree at B → every navigation tool `ref_mismatch` with both | in-process client over six tools + an AST check that every query tool is guarded | ✅ |
| AC2 | AC | HEAD matches → byte-identical | index root, a worktree at A, an unrelated root, no roots: all equal | ✅ |
| AC3 | AC | instructions fit `CLIENT_CAP` | unchanged instructions; existing test | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `reason == "ref_mismatch"`, `index_commit == A`, `caller_commit == B` on six tools; AST: every `serve(...)` but the build passes `guard(...)` | "every" derived from `main.py`'s syntax (R6.7), not listed |
| AC2 | yes — structured answers equal across four root shapes | |
| AC3 | yes — `tests/test_server_instructions.py::test_instructions_fit_under_the_client_cap_on_every_state` | |

### Gap analysis (enhancement)

- **Now.** `worktree_guard.worktree_db_refusal` fires only when the server's own root is a linked
  worktree (`worktree_guard.py:28-49`); a server rooted at main answers a worktree agent `ok`.
- **Target.** The client's roots reach the guard; another checkout at another commit is labelled.

### Blast radius

- `schema_guard.guard`: 23 wrapped tools (`main.py`); `get_index_status` passes `status=True`.
- `NAV_REASONS` count-pin: `tests/test_nav_reason_codes.py` (P5) — on the change list.
- Hooks and CLI call tools outside MCP: `CALLER_ROOTS` stays `None` there, so they are unchanged.
- Docs: TOOLS.md status row, CONVENTION §6 ref row, PLAN §19 worktree line, `runbooks/parallel-agents.md`.

### Rule sections

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the check names no language · §R1.4 (change-type) ✅ the built commit is read through GraphStore.get_meta; git through gitutil · §R4.1 (change-type) ✅ no network: roots arrive on the existing MCP session · §R4.2 (change-type) ✅ with no mismatch every answer is byte-identical (AC2) · §R5.6 (change-type) ✅ the payload now separates "answered about the caller's commit" from "about another" · §R6.7 (change-type) ✅ "every tool" is derived from main.py's syntax · §R7.5 (change-type) ✅ comments ≤ 3 lines · §R7.6 (change-type) ✅ the CONVENTION row is folded into the existing ref row and R5.4's restatement is cut to a pointer`

## Phase 2 — design

### Approach

1. **`gitutil.checkout_identity`** — `(top level, shared git dir)` from one `rev-parse`.
2. **`ref_check.CallerRoots`** — FastMCP middleware: roots once per session (5 s bound, a client
   without the capability reads as no roots), into the `CALLER_ROOTS` ContextVar per call.
3. **`ref_check.find_mismatch` / `attach_ref_check`** — X2's root rule; built commit vs the
   caller checkout's HEAD; label per X3/X4; status gets the summary route or `ref_check`.
4. **`schema_guard.guard(..., status=)`** calls it after `attach_build_state`; `main.build_server`
   adds the middleware and passes `status=True` for `get_index_status`.
5. **`REASON_REF_MISMATCH`** in `NavReason`; docs as above.

### Rejected alternatives

- **Compare paths only, no git.** A root under the repo directory can be a separate worktree
  (`.claude/worktrees/…`), and a sibling directory can be an unrelated repo.
- **A tool parameter for the caller's root.** Every agent would have to pass it; the field case is an
  agent that does not know it is mismatched.
- **Read HEAD from `.git` files.** Packed refs and reftable make a hand-rolled reader wrong; one
  `rev-parse` in the worktree case only is the price.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | Claude Code answers `roots/list` with its working directory | verified — spike (1) |
| S2 | a client without roots raises, and the server must survive it | verified — spike (2); AC2's no-roots client |
| S3 | the ContextVar reaches sync tools | verified — spike (3); AC1 runs through it |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `checkout_identity` | `code_atlas/gitutil.py` | new helper only | R1 | 1/1 |
| 2 | middleware + check | `code_atlas/ref_check.py` (new) | every MCP tool call | R1–R3, C1 | 1/1 |
| 3 | guard hook | `code_atlas/tools/schema_guard.py` | 23 guarded tools | R1, AC1 | 1/1 |
| 4 | wiring | `code_atlas/main.py` | server construction | R1, R3 | 1/1 |
| 5 | reason value | `code_atlas/tools/nav_result.py` | `NAV_REASONS` | R1 | 1/1 |
| 6 | count-pin | `tests/test_nav_reason_codes.py` | — | R1 (P5) | 1/1 |
| 7 | proving tests | `tests/test_ref_mismatch.py` (new) | — | AC1–AC2, R2–R3 | 1/1 |
| 8b | read-only meta read (F2) | `code_atlas/store.py` | one new function | R1 | 1/1 |
| 8 | docs | `docs/TOOLS.md`, `docs/CONVENTION.md`, `docs/PLAN.md`, `docs/runbooks/parallel-agents.md` | doc budgets | R3 | 4/4 |
| 9 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `tests/test_backlog_bookkeeping.py` | — | 4/4 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced: only the two new files (`ref_check.py`,
  `test_ref_mismatch.py`) were run through `ruff format`; the edited files had `ruff check` only.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | in-process FastMCP client with `roots`, a real PHP index, a real `git worktree` | n/a | ✅ |
| AC2 | integration | the same client across four root shapes | n/a | ✅ |
| AC3 | logic | existing instructions cap test | n/a | ✅ |
| R2/R3 | integration | the same client, status tool | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_ref_mismatch.py`.

### Rollback

`git revert` the branch commits. Nothing persistent: no schema, no contract.

## Phase 3 — execute

Commit `17c59f87`. **Order deviation:** the code was written before this doc's design text; the
design was settled first (spikes and `366-design-notes`, not committed) and the doc records it as built.

**Red first** — `main` in a throwaway worktree with only the unwired vocabulary copied in
(`ref_check.py`, `nav_result.py`, `gitutil.py`; `main.py` and `schema_guard.py` untouched): `3 failed,
2 passed in 2.02s` — search_symbol answered `ok`, the summary read `current @ cec2027 · 2 files ·
8 symbols`, and `ref_check` was absent. The two that pass there are AC2 and the guard sweep.

On `17c59f87` the file gave `5 passed in 2.02s` (superseded by Phase 4's run).

**Sweep.** Axis 1: `git diff --name-only main..HEAD` = change-list items 1–8 exactly; `ruff check`
and `mypy code_atlas` clean. Axis 2: Approach 1–5 implemented as approved. Related suites (nav
reasons, MCP server, instructions, six-tool preset, status health, server identity): `129 passed`.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `17c59f87`, 68,160 tokens): 6 met · 1 not met · 0 can't tell.**
The "not met" is Scope 2's "or a refresh" (F10 below). Dispositions:

1. **F1 (high): the per-session roots cache never refreshed** — FastMCP does not hand
   `roots/list_changed` to middleware, so `on_notification` was dead. **Fixed** in `f8b28e71`: roots
   are asked on every call; only a session that timed out is not asked again. Test
   `test_a_caller_that_moves_into_a_worktree_mid_session_is_seen` fails with a session cache
   restored (`1 failed, 8 passed`).
2. **F2 (high): `GraphStore` open raised on a foreign schema.** **Fixed:** `store.read_meta_readonly`
   (`mode=ro`, any `sqlite3.Error` → None). Test with a schema-0 index: red on `17c59f87`
   (`SchemaVersionError` escaped as a tool error), green now.
3. **F3 Windows/UNC URIs.** **Fixed:** `url2pathname` plus the netloc. The drive-letter case is
   untestable on this POSIX host; the UNC and percent-escape cases are tested.
4. **F4 a `rev-parse` per call for worktree callers.** **Kept, documented** in `find_mismatch`'s
   docstring: a commit made in the worktree must be seen at once; the meta read is now read-only.
5. **F5 a hanging client.** **Fixed:** 2 s bound, and a session that timed out is not asked again.
6. **F6 built commit vs live HEAD** — X1, recorded. F1 of the ticket — X8, recorded.
7. **F7 `return` ended the root scan.** **Fixed** (`continue`); test with `[same, side]`.
8. **F8 caches.** **Fixed:** a non-checkout is no longer cached; the session cache is gone.
9. **F9 CONVENTION R5.4 text.** **Intended:** R7.6 pruning to hold the doc budget — the bullet now
   points at R5.4 (b) and (c) instead of restating them; the rule itself is unchanged.
10. **F10 "or a refresh".** **Left, recorded:** X7 — a refresh rebuilds main's index at main's HEAD
    and cannot fix a worktree's mismatch.

Verify-only (main loop, no re-dispatch — every fix is inside the approved files, plus one
`store.py` helper the F2 fix needs, recorded here as a change-list addition):

On `f8b28e71` the file gave `9 passed in 3.03s`; related suites plus doc tests `243 passed`.

**Gate red once — a P5 miss.** `scripts/gate.sh` on the first bookkeeping tip failed four count-pins
the blast radius did not list: `len(core_modules()) == 96` (`tests/test_core_is_language_agnostic.py`,
`tests/test_sql_confinement.py` — `ref_check.py` is a new core module) and `NAV_REASONS[-1] ==
REASON_PATH_OUTSIDE_ROOT` (`tests/test_empty_answer_cannot_explain_itself.py`,
`tests/test_relation_unmodelled_for_language.py`). Each moved to the new value; recorded as a
change-list deviation. AGENT_BRIEF P5 already names this class, so no new claim.

**Round 2** (re-dispatched: the pin fix touched tests outside the reviewed set; on `1121f5d7`,
66,088 tokens): **5 met · 0 not met · 1 can't tell** (AC3 — the cap test was not in
its run list; the gate runs it). Every round-1 fix confirmed. Its findings: the "or a refresh" route
(F10 again — left, X7); the R5.4 text (left, R7.6); an `error` payload stamped `ref_mismatch` —
**fixed** in `1a963e84`, an error answer is left as it is; an untested hang guard and an unbounded
checkout cache — left (low; a timed-out session reads as no roots).

Ran at 1a963e84:
```
$ .venv/bin/python -m pytest -q tests/test_ref_mismatch.py
9 passed in 2.92s
```

`Ph3/4 proven by`: G1, C1, R1–R3, AC1–AC3 — 8/8.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 1a963e84 — the diff `main..1a963e84`. Working doc: `docs/tasks/366_wrong-ref-answer-reads-ok.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `1a963e84` only bookkeeping changes — this doc, `docs/BACKLOG.md`,
`docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`, all exempt.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

`366-C1` is type 5 (environment), area `fastmcp / middleware notifications`: FastMCP 3.4.5 does not
dispatch a client's `roots/list_changed` to `Middleware.on_notification`, and its in-process
`Client.set_roots` does not change what a live session answers. First sighting. Per P1, `343-C2`
gains 366 (traced).

### Outward actions

1. Push `feat/366-wrong-ref-answer-reads-ok` — pre-authorised.
2. Open the PR against `main` — pre-authorised.

Deferred to the maintainer: the merge; ratifying X1–X4, X8, X9.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 48,402 |
| 2 | review | `challenger`, round 1 | 68,160 |
| 3 | review | `challenger`, round 2 | 66,088 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 182,650 · top cost driver: review/challenger`

**Gate.** `scripts/gate.sh` on `ae121a7e`: `GATE GREEN — all 21 checks passed` (Linux, bare pytest).
Only this doc and the ledger row's gate note changed after it.

**Revert path.** `git revert` the branch commits; nothing persistent changes.
