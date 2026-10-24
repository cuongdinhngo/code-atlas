---
id: 408
slug: per-call-caller-root
title: "A subagent in a session-spawned worktree gets answers about `main` with `reason: ok` — a per-call `caller_root`"
phase: 2
milestone: Freshness
status: done
depends_on: [389, 366]
---

## Why this exists

Issue [#100](https://github.com/cuongdinhngo/code-atlas/issues/100), 2026-10-24. On the anchor, about
26 of 68 PRs in 19–23 Oct report answers about the main checkout from an agent working in a worktree
spawned inside the session (`isolation: worktree`, `parallel-tasks`): `no_such_symbol` on a method
only the worktree holds, line numbers off by ~75, new classes invisible. The largest single complaint.

**Confirmed in code (2026-10-24):** `ref_check.caller_checkout` reads `CALLER_ROOTS` (per MCP session)
or `CA_CALLER_ROOT` (per server). A subagent shares the parent's server and roots, which name the
main checkout, so 389's overlay never fires and 366's `ref_mismatch` cannot either — the roots'
checkout *is* the index root. Wrong and confident. Unconfirmed: the version behind the field reports.

## Scope

1. An optional `caller_root` argument on the tools 389 overlays (`read_symbol`, `file_outline`,
   `search_symbol`, `find_callers`, `find_references`). It names a checkout of the indexed repo and
   takes precedence over roots and `CA_CALLER_ROOT` for that call only.
2. Validated exactly as a root is (`ref_check.other_checkout`): another checkout of the same repo,
   otherwise refused with a reason — never a silent fall-back to the session's root.
3. The skill (`contrib/claude-code/plugin/`) and the agent brief tell an agent working in a worktree
   to pass its own top-level path.

Out of scope: per-worktree indexes (`CA_DB_PATH`, already in `docs/runbooks/parallel-agents.md`);
the optional "subject file differs in a known worktree" caveat.

## Acceptance criteria

- AC1: With session roots on the main checkout, `caller_root=<worktree>` answers a symbol that exists
  only in the worktree, labelled with 389's overlay field.
- AC2: A `caller_root` outside the repo, or a non-checkout path, is refused with a named reason.
- AC3: Omitting `caller_root` leaves every answer byte-identical to today (roots, then env).
- AC4: The tool-docstring token budget still holds; the five tools' schemas name the argument.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 408 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W4 and merges. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · Run mode: `autorun 408 - 409 - 410 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/408-per-call-caller-root` from `main` (`191b7a8f`, #103 merged). Contract `.mango/run-contract-408.txt`.
  RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 0 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 14 unresolved surfaced | 3 want-decision asked | 11 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `ref_check.CallerRoots`, `ref_check.other_checkout`, `CA_CALLER_ROOT`, `docs/runbooks/parallel-agents.md`,
the five overlaid tools, `contrib/claude-code/plugin/`, tasks 389 and 366 resolve. Ambiguous: "the agent brief" — the
generated `contrib/agent-brief.md` (what a consumer agent reads), not this repo's `docs/AGENT_BRIEF.md` (process rules).
Recall (type 5, area `freshness / shared index across checkouts`): 389-C1 — a worktree compares stored hashes with its
own bytes per file, so the overlay stays correct while main repairs the shared store. No type-2 handle matches: the
change adds a parameter, no shared vocabulary, no new core module, no value threaded through callers.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 57,725 tokens) raised thirteen items; H1–H11 and W1–W3
settle them, H12 is this run's own.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | does `caller_root` drive 366's `ref_mismatch` as well as the overlay | how | yes — Scope 2 "validated exactly as a root is" and "takes precedence over roots": the argument stands in for the roots for that call, overlay and label alike |
| H2 | `caller_root` naming the index checkout (or a directory inside it) | how | accepted: that caller is in the index checkout, so no overlay and no label — `other_checkout` (`ref_check.py:136`) |
| H3 | a subdirectory of a worktree | how | accepted and answered as that worktree's top level — `_checkout` resolves the top level (`ref_check.py:119`) |
| H4 | empty, relative, missing or non-directory value | how | refused (W1's shape) before any read — R5.3; `require_path_prefix` (`nav_result.py:155`) |
| H5 | a client that reported no roots, timed out, or is not MCP | how | the argument still applies — Scope 1 "takes precedence over roots and `CA_CALLER_ROOT`" |
| H6 | an answer echoing the validated root | how | only through 389's `overlay_root` / 366's `caller_root` fields — the existing output names; no new field |
| H7 | nothing differs between the worktree and the built commit | how | silence, as 389: `Overlay.label` labels nothing when nothing differs (`overlay.py:136`) |
| H8 | per-call cost | how | the roots route's cost (389): one `git diff` and one untracked listing per call — the runbook row |
| H9 | skill and brief wording | how | one shared line, "in a worktree of the indexed repo, pass `caller_root` = `git rev-parse --show-toplevel`", in both generated files — Scope 3; the size gates bound it |
| H10 | contract or release | how | neither: a tool argument is no node/edge vocabulary, field or qname (R3.1); a CHANGELOG *Unreleased* line |
| H11 | AC3 "byte-identical" | how | the answers; the published schemas change by one property (AC4) |
| H12 | a signed claim from a `caller_root` call | how | replayed, like every non-default argument (`claim.call_args`, 383): the answer depended on it, so a re-run without it would ask another question |
| W1 | the shape of a refusal | want | **ASSUMED (awaiting ratification):** an input error (`ValueError`, the tool-call error a client sees), naming why — not a new `reason`, which would widen `NavReason` and the reason docs for a malformed argument; `path_prefix` is the precedent |
| W2 | the other nineteen tools | want | **ASSUMED (awaiting ratification):** unchanged; only the five tools 389 overlays take `caller_root`, and the brief line says so. `impact` from a worktree stays the per-worktree-index route |
| W3 | which paths the server may read | want | **ASSUMED (awaiting ratification):** any checkout sharing the index's git directory (the roots' own gate); not narrowed to the session's roots or `git worktree list` |

## Phase 1 — analysis

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 0 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=4 G=1 AC=4`
`CLARIFICATION: 15 raised | 15 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/12 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

The four want-decisions (W1–W3 from refine, W4 below) count as self-resolved because the handover handed them back
("make the necessary decisions"): each stands `ASSUMED (awaiting ratification)` for the maintainer at the PR.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "answers about the main checkout … Wrong and confident" | a subagent in a worktree can make the five reads answer about its worktree | ✅ |
| C1 | Scope 2 | "never a silent fall-back to the session's root" | a refused `caller_root` answers nothing about main | ✅ |
| C2 | Out of scope | "per-worktree indexes … the optional caveat" | no `CA_DB_PATH` change, no differs-in-worktree caveat | ✅ |
| R1 | Scope 1 | "an optional `caller_root` argument on the tools 389 overlays" | `read_symbol`, `file_outline`, `search_symbol`, `find_callers`, `find_references` (N = 5) | ✅ |
| R2 | Scope 1 | "takes precedence over roots and `CA_CALLER_ROOT` for that call only" | it replaces the roots for the overlay and the 366 label (H1, H5); the next call is unaffected | ✅ |
| R3 | Scope 2 | "validated exactly as a root is … refused with a reason" | a checkout sharing the index's git dir, else refused (H2–H4, W1, W3) | ✅ |
| R4 | Scope 3 | "the skill … and the agent brief tell an agent working in a worktree to pass its own top-level path" | one shared line in `contrib/skill/SKILL.md`, the plugin skill and `contrib/agent-brief.md` (H9) | ✅ |
| AC1 | AC1 | worktree-only symbol answered with roots on main | `read_symbol` and the inbound tools over the guarded tool, roots = main | ✅ |
| AC2 | AC2 | outside path / non-checkout refused with a named reason | `ValueError` naming the cause (W1) | ✅ |
| AC3 | AC3 | omitting it leaves answers byte-identical | answer dicts equal with and without the parameter's existence | ✅ |
| AC4 | AC4 | "the tool-docstring token budget still holds; the five tools' schemas name the argument" | W4 | ✅ |

### AC validation

| AC | Falsifiable? | Definition |
|---|---|---|
| AC1 | yes | with `CALLER_ROOTS = (main,)`, the guarded `read_symbol(…, caller_root=wt)` returns the worktree's span with `overlay == "worktree"`; without the argument it answers main's span |
| AC2 | yes | `caller_root` = another repository, a plain directory, a relative path, a missing path → `ValueError` whose message names the cause; no answer |
| AC3 | yes | `read_symbol` / `find_callers` answers with `caller_root` omitted equal the same calls on `main` |
| AC4 | yes (W4) | each of the five published `inputSchema`s has `caller_root`; no other tool's does; the gate's tokens-to-answer check stays green |

**W4 — ASSUMED (awaiting ratification).** No tool-docstring token budget exists to recompute: the gates that bound
the surface are the description-opener test (`tests/test_tool_descriptions.py`), the server-instructions cap
(`instructions.CLIENT_CAP`) and tokens-to-answer. AC4 is read as those three staying green plus the schema check.

**Universal inventory — R1 (N = 5):** 1 `read_symbol` · 2 `file_outline` · 3 `search_symbol` · 4 `find_callers` ·
5 `find_references`. Review confirms each.

### Root cause (bug — `logic`)

`ref_check.caller_checkout` (`code_atlas/ref_check.py:166`) reads `CALLER_ROOTS`, set per MCP session by
`CallerRoots.on_call_tool` (`:69`), or `config.caller_root` (`CA_CALLER_ROOT`, per server). A subagent spawned into a
worktree shares its parent's server and roots, which name the main checkout, so `other_checkout` (`:129`) sees the
index root and returns `None`: no overlay (`overlay.active_overlay`, `overlay.py:147`) and no 366 label
(`attach_ref_check`, `:182`). Nothing in a call can name another checkout.

**Blast radius.** One repo (`app`). `ref_check.py` (validation, the override), `overlay.active_overlay`, the five
tools, `schema_guard.guard` (the 366 label runs there), `scripts/gen_skill.py` and its three generated files; docs:
`docs/TOOLS.md`, `docs/runbooks/parallel-agents.md`, `CHANGELOG.md`. Surfaces counting tool params:
`tests/test_agent_brief_usage_completeness.py` (every unwaived param of an occasion tool must be taught — it is, R4),
the skill drift test, claim replay (`claim.call_args`, H12).

### BASELINE

`BASELINE: red — tests/test_agent_chain_budget.py::test_tier_one_stays_under_its_total_budget (tier 1 is 19,906 tokens against 19,900: #103's three BACKLOG rows; this ticket claims the fix — its row leaves BACKLOG at done)`

`scripts/gate.sh` on the untouched checkout: `FAIL pytest -q` — `1 failed, 4908 passed, 4 skipped in 674.86s`;
`20 passed · 1 failed · 0 skipped`, `GATE RED`. Ran at 191b7a8f (log `.mango/baseline-408.log`, untracked).

DoD: delta green, and the claimed fix lands — no failure after the change.

### Rule sections

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the validation asks git about paths, never a language · §R1.8 (change-type) ✅ one validator, read by the tools and by the guard · §R5.3 (change-type) ✅ a bad caller_root is an input error and fails loud · §R5.6 (change-type) ✅ a refusal carries no rows, so main is never answered as the worktree · §R6.1 (change-type) ✅ a tool change → a test over a fixture repo · §R6.5 (change-type) ✅ the new test fails on main (unknown argument) · §R6.10 (change-type) ✅ the fixture builds in-process with an explicit env · §R7.6 (change-type) ✅ the runbook row and TOOLS.md lines are edited in place, BACKLOG loses this row`

## Phase 2 — design

### Approach

1. `ref_check.require_caller_root(config, caller_root)` — the one validator (R1.8). `None` → `None`. Otherwise
   `ValueError` naming the cause unless the value is a non-empty absolute path to a directory inside a git checkout
   whose shared git directory is the index root's; returns the path. An index root that is no git checkout refuses
   every value but itself.
2. `caller_checkout(config, caller_root=None)`, `active_overlay(config, store, caller_root=None)` and
   `attach_ref_check(…, caller_root=None)`: a given `caller_root` stands in for the roots — `(caller_root,)` — ahead of
   `CALLER_ROOTS` and `CA_CALLER_ROOT`, for that call only.
3. The five tools take `caller_root: str | None = None`, validate it first (before any read) and pass it to
   `active_overlay`; each docstring says so. `schema_guard.guard` validates the same keyword and hands it to
   `attach_ref_check`, so the 366 label follows the argument too.
4. `scripts/gen_skill.py`: one `WORKTREE_ROUTE` line, used by the skill and the agent brief; the three generated
   files regenerated.
5. Docs: `docs/TOOLS.md` (the `CA_CALLER_ROOT` row and the overlay sentence), the runbook's *Share main's index* row,
   CHANGELOG *Unreleased*.

### Rejected alternatives

- **Set `CALLER_ROOTS` inside `guard` only** — one place, but a tool called without the guard (the 389 tests, any
  in-process caller) would take the argument and ignore it: a parameter that does nothing on one path.
- **A new `reason` such as `caller_root_refused`** — W1: it widens `NavReason`, its docs and count tests for a
  malformed argument, which every other tool reports as an input error.
- **Narrow to `git worktree list` or the session's roots** — W3: a clone sharing nothing is already refused by the
  git-dir gate, and a subagent's worktree is often not one of the session's roots, which is the bug.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| `gitutil.checkout_identity` gives the same git dir for a linked worktree and its main checkout | verified | 366/389 rely on it; `tests/test_worktree_overlay.py` builds a linked worktree and overlays it |
| FastMCP publishes a keyword's schema from the inner tool through `functools.wraps` | verified | `path_prefix` / `serve_behind` reach `inputSchema` through the same guard (`tests/test_search_symbol_path_prefix.py:202`) |
| a `ValueError` raised in a tool reaches the client as a tool error, not a crash | verified | `tests/test_filter_values_fail_loud.py` (a bad `kind` value) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | the validator; the override in `caller_checkout` and `attach_ref_check` | `code_atlas/ref_check.py` | `caller_checkout`'s one caller (`overlay.py:149`); `attach_ref_check`'s one caller (`schema_guard.py:67`) | R2, R3, C1 | 1/1 |
| 2 | `active_overlay(…, caller_root)` | `code_atlas/overlay.py` | its five callers, all in this list | R2 | 1/1 |
| 3 | the guard passes the keyword to the label | `code_atlas/tools/schema_guard.py` | every guarded tool — only the five declare the keyword, so the rest never see it | R2 | 1/1 |
| 4 | the five tools | `tools/read_symbol.py`, `tools/file_outline.py`, `tools/search_symbol.py`, `tools/find_callers.py`, `tools/find_references.py` | published schemas (+1 property each); the brief-completeness gate (taught by #5); claim replay (H12) | R1, AC1–AC4 | 5/5 |
| 5 | the route line | `scripts/gen_skill.py`, `contrib/skill/SKILL.md`, `contrib/claude-code/plugin/skills/code-atlas/SKILL.md`, `contrib/agent-brief.md` | the skill drift test (regenerated files) | R4 | 4/4 |
| 6 | tests | `tests/test_per_call_caller_root.py` (new) | — | AC1–AC4, R3, C1 | 1/1 |
| 7 | docs | `docs/TOOLS.md`, `docs/runbooks/parallel-agents.md`, `CHANGELOG.md` | doc size budgets | G1 | 3/3 |
| 8 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests; tier-1 budget (B1's fix) | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

Count-pins (P5): `rtk proxy grep -rn 'properties"\]) ==\|parameters) ==' tests/*.py` → one hit,
`tests/test_onboarding_summary.py:105` (`summaries_as_dict`, not a tool). No tool's parameter set is pinned.

### Rule compliance

The eight sections of Phase 1 bind the design unchanged. R7.5 (≤ 3-line comments) binds every change.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — git worktree, adapter parse, guard | a real PHP build, a linked worktree, the guarded tools with `CALLER_ROOTS = (main,)` | n/a | ✅ |
| AC2 | integration | each refused shape raises before an answer | n/a | ✅ |
| AC3 | integration | the same calls without the argument equal the 389 answers | n/a | ✅ |
| AC4 | integration — the MCP client | `Client.list_tools()` on a built server: five schemas carry `caller_root`, no other | n/a | ✅ |
| R4 | logic | the generated skill and brief carry the route line; drift test | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_per_call_caller_root.py`

### Rollback

`git revert`; no stored state changes. One repo, no porting.

`SCOPE: M` — unchanged.

## Phase 3 — execute

Implemented in the main loop: the change sets which paths the server may read (W3), an access boundary. Commits
`9c5c46b5` (core, tools, test), `d1feb2d1` (skill and brief), `1c25cc0a` (docs).

**Red first** (R6.5): with `code_atlas/` stashed back to `55b1f415`, `tests/test_per_call_caller_root.py` gives
`8 failed in 4.20s` (the tools reject the unknown keyword). With only `schema_guard.py` stashed: `2 failed, 6 passed`
— the label test and the index-checkout test, so the guard half is guarded on its own. Ran at 9c5c46b5.

**Green at execute:** the proving test `8 passed in 2.90s`; the neighbours (worktree overlay, ref mismatch, brief
completeness, skill drift, shell route, tool descriptions, MCP server, claim signing, batched sweep, schema recovery,
path prefix, filter values, doc size, config, nav tools) `309 passed in 27.21s`; `ruff check .` clean; `mypy`
`Success: no issues found in 113 source files`. Ran at 9c5c46b5 (the two later commits touch no Python under test).

**Verification sweep.** File axis: `git diff --name-only 55b1f415..HEAD` lists 16 files, all on the change list.
No language branch: `grep -n 'if .*language ==' code_atlas/ref_check.py` exits 1. Behaviour axis: Approach 1–5
implemented as approved. One finding while writing the test: a worktree that differs from the built commit labels
every overlaid answer `overlay: worktree` (389), so the 366 label never reaches those five tools from a worktree; the
guard half matters when the call names the **index** checkout while the session's roots name a worktree. The test
asserts that case, and `find_implementations` shows what the roots alone would say.

| # | Deviation | Trace | Effect |
|---|---|---|---|
| — | none | — | — |

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.

- **`challenger` round 1** (ticket-blind, 74,806 tokens; raw ticket only, read from a file holding the text above the
  separator; the task file excluded from its diff): 8 met · 0 not met · 0 can't tell. Findings:
  - D1 (Major) — `test_tier_one_stays_under_its_total_budget` red at the tip: B1, #103's rows, cleared at finalise
    when this row leaves BACKLOG.
  - D2 (Minor) — a refusal is a raised error, not a `reason`: W1, as designed; the docstrings say "refused as an error".
  - D3 (Minor) — a worktree whose HEAD no longer reads passed validation, then `other_checkout` dropped it and the call
    answered about main unlabelled — **fixed** in `824e75a3`: refused, with
    `test_a_worktree_whose_head_does_not_resolve_is_refused`, seen red with only that check removed (`DID NOT RAISE`).
  - D4 (Minor) — a signed claim replays `caller_root`: H12, as designed.
  - D5 (Minor) — the guard and the tool both validate (cached git identity); a bad root on a schema-mismatched index
    raises rather than answering the mismatch. Left: an input error before the index is read is R5.3's order.
- **Round 2: verify-only, main loop.** The fix stays inside D3 and the approved files. The affected proof re-ran:
  `tests/test_per_call_caller_root.py`, `test_worktree_overlay.py`, `test_ref_mismatch.py` `33 passed in 11.05s`;
  `ruff`, `mypy` clean. Ran at 824e75a3, superseded by the final gate below.

Verdict: clean (challenger only — REVIEWER: OFF), with W1–W4 standing for ratification.
`Ph3/4 proven by`: R1 and the inventory (5/5: read_symbol · file_outline · search_symbol · find_callers ·
find_references) → `test_each_of_the_five_tools_honours_caller_root`; R2 → the label and AC3 tests; R3, C1 → the
refusal, HEAD and never-reaches-the-index tests; R4 → the skill drift test and `test_agent_brief_usage_completeness`;
AC1–AC4 → their named tests; G1 → all of them.

Reviewed at 824e75a3520e36bc8d6e85384de96184f5330d4b. Files: `code_atlas/ref_check.py`, `code_atlas/overlay.py`,
`code_atlas/tools/schema_guard.py`, the five tools, `tests/test_per_call_caller_root.py`, `scripts/gen_skill.py`, the
three generated files, `docs/TOOLS.md`, `docs/runbooks/parallel-agents.md`, `CHANGELOG.md`. Working doc: this file.

## Phase 5 — finalise

**Durable lesson.** 408-C1 (`a-docs-change-runs-every-doc-budget`, first sighting): #103 ran two doc tests, not the
tier-1 budget, and turned `main` red.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`

### Outward actions

Under the handover: push `feat/408-per-call-caller-root`; open its PR against `main`.
Deferred to the maintainer: ratify W1–W4, merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 57,725 |
| 3 execute | `implementer` — not dispatched (high-stakes: a path-access boundary); main loop implemented | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | ticket-blind `challenger` | 1 | 74,806 |

`LEDGER TOTAL: 132,531 · top cost driver: 4 review / challenger` — main loop unmeasured.
