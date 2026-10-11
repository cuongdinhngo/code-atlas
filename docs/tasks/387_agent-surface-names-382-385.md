---
id: 387
slug: agent-surface-names-382-385
title: 'An agent in a consuming repo cannot recognise 382–385: no map row, brief line or skill entry names a route, a claim re-run or a symbol-change check'
phase: 2
milestone: Adoption
status: done
depends_on: [382, 383, 384, 385]
---

## Why this exists

382–385 shipped for the anchor project and their human docs landed with them (README, `docs/TOOLS.md`,
`docs/design/impact-and-claims.md`, CHANGELOG). The surfaces an **agent** reads were not touched:

- `RECOGNITION_MAP` (`code_atlas/tools/prompts.py`) — feeds `which_tool`, the server instructions'
  `core` rows and the generated plugin skill — has no row for "a URL / route a user reports" although
  `trace_capability(route=)` and `impact(routes=)` exist (385).
- The agent brief (`scripts/gen_skill.py` → `contrib/agent-brief.md`, written into a consumer's
  `AGENTS.md`) never names the shell route: `code-atlas query` / `--batch` (382), `--verify-claims`
  (383), `--snapshot-symbols` / `--changed-since` (384). These are not MCP tools, so no tool
  description can carry them.

So an agent in the anchor repo keeps re-implementing them by hand (its own URL→handler script,
eyeballing pasted claims, file-level diffs) — the very work 382–385 removed. The finding's subject is
the agent, so it generalises (PLAN §19, 2026-08-14).

## Scope

1. A recognition-map row routing a reported URL / route to `trace_capability` (`route=`).
2. Agent-brief: an occasion for "a bug report or test doc names a URL", and usage lines naming the
   shell route for batch answers, re-running pasted claims and per-symbol change since a revision.
3. Regenerate every `gen_skill.py` output; tool count stays 24; server-instructions cap (343) holds.

## Acceptance criteria

- **AC1:** `which_tool` and the generated skill contain a route row naming `trace_capability`.
- **AC2:** `contrib/agent-brief.md` names `code-atlas query`, `--verify-claims` and `--changed-since`,
  and has a URL occasion selecting `trace_capability`.
- **AC3:** the drift guards, doc budgets and the 2,048-char instructions cap stay green.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 387 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W2–W3 and 387-C1, then merges the PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun 387 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/387-agent-surface-names-382-385` off `main`. Contract `.mango/run-contract-387.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 15 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 3 retired skipped — advisory (blocks nothing)`
`REFINE: 13 unresolved surfaced | 3 want-decision asked | 10 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** `RECOGNITION_MAP` (`code_atlas/tools/prompts.py:24`), `trace_capability(route=)`, `impact(routes=)`,
`scripts/gen_skill.py`, `contrib/agent-brief.md`, `code-atlas query` with `--args` / `--batch` / `--verify-claim(s)` /
`--snapshot-symbols` / `--changed-since` (`code_atlas/query.py`), README, `docs/TOOLS.md`,
`docs/design/impact-and-claims.md` and CHANGELOG resolve.

**Recall.** 343-C1 (area: server instructions keep a 2,048-char prefix) → H1. 344-C3
(`verify-the-shipped-artifact-not-the-working-tree`) → every regenerated file is committed and checked by its drift guard.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 48,146 tokens) added H2, H8, H10.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the route row goes | how | `RECOGNITION_MAP`, `core=False`: the instructions render only `core` rows under `CLIENT_CAP` (`instructions.py:8`, 343-C1) |
| H2 | which tool the row names | how | `trace_capability` only — a row is one tool (`prompts.py:24`); its question (a URL someone reports) differs from the generic request-routing rows (`prompts.py:53-64`); `impact(routes=)` goes in the brief prose |
| H3 | how the URL occasion selects the route line | how | settled at design: `recognition_lines_by_tool` keeps the first line per tool (`gen_skill.py:316`) |
| H4 | where the shell route is named | how | not a tool (`main.TOOL_NAMES` stays 24), so no tool description can carry it: one constant in `gen_skill.py` rendered into both the brief and the skill (R6.7) |
| H5 | phrasing | how | generic, no anchor-repo name — an agent finding generalises (PLAN §19, 2026-08-14); R2 |
| H6 | tool count | how | stays 24 (ticket Scope 3) |
| H7 | regeneration | how | `python scripts/gen_skill.py --write`; every output is drift-guarded (`tests/test_skill_drift.py:24`) |
| H8 | release / version | how | a CHANGELOG `Unreleased` line, no bump: a release is cut separately (`CHANGELOG.md:16-18`, 381) and publishing one is a stop-and-confirm action (AGENTS.md) |
| H9 | the brief's size | how | `contrib/agent-brief.md` is outside the tier-1 chain (`tests/test_agent_chain_budget.py` never reads `contrib/`); R7.6 still caps the addition at a few lines |
| H10 | which brief sections carry the new lines | how | the URL occasion in `OCCASIONS`; the shell route under "How to spend the calls" (`gen_skill.py:331`) |
| W1 | write the brief into the anchor repo too? | want | **asked, settled by the maintainer:** no — code-atlas only |
| W2 | the acceptance bar | want | **ASSUMED (awaiting ratification):** presence in the generated surfaces, not a field measurement of agent behaviour (that is 200's) |
| W3 | drop the `route` / `routes` waivers once the brief teaches them | want | **ASSUMED (awaiting ratification):** yes. **Tripwire:** reverses 385's waiver (`tests/test_agent_brief_usage_completeness.py:22-23`); a waiver for a taught param is untrue |

## Phase 1 — analysis

`PREMISE: 15 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 3 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=3 G=1 AC=3`
`CLARIFICATION: 13 raised | 13 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/6 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

The 13 are Phase 0's H1–H10 and W1–W3: W1 answered by the maintainer, W2–W3 handed back by the handover and
carried as `ASSUMED`. `TIER: full` because the change spans two source files plus generated outputs (quick refused it).

### BASELINE

`.venv/bin/pytest -q` over the ten guards this change can move (`test_skill_drift`, the three `test_agent_brief_*`,
`test_server_instructions`, `test_contrib_snippets`, `test_claude_code_plugin`, `test_doc_size_budget`,
`test_backlog_bookkeeping`, `test_release_discipline`): `222 passed, 1 xfailed in 2.76s`. Ran at 56ec66b2.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| route recognisable | `RECOGNITION_MAP` has no URL row (`code_atlas/tools/prompts.py:24-87`); the brief waives `route`/`routes` (`tests/test_agent_brief_usage_completeness.py:22-23`) | a row, an occasion, brief prose |
| shell route recognisable | `USAGE_RULES` (`scripts/gen_skill.py:331`) and `render_skill` (`:105`) never name `code-atlas query` | one constant, rendered into both |

Blast radius: `recognition_lines` feeds `which_tool`, `instructions.render` (core rows only) and `gen_skill`; one repo.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "an agent in the anchor repo keeps re-implementing them by hand" | the agent surfaces name 382–385 | ⏳ |
| C1 | Scope 3 | "tool count stays 24" | `main.TOOL_NAMES` unchanged | ⏳ |
| C2 | Scope 3 | "server-instructions cap (343) holds" | the row is non-core | ⏳ |
| R1 | Scope 1 | "A recognition-map row routing a reported URL / route to `trace_capability`" | H1, H2 | ⏳ |
| R2 | Scope 2 | "an occasion … and usage lines naming the shell route" | H3, H4, H10 | ⏳ |
| R3 | Scope 3 | "Regenerate every `gen_skill.py` output" | H7 | ⏳ |
| AC1 | AC | route row in `which_tool` and the skill | | ⏳ |
| AC2 | AC | brief names the three commands and a URL occasion | | ⏳ |
| AC3 | AC | drift guards, budgets, cap green | | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — a `which_tool` line contains `route` and `-> trace_capability`; the same line is in both SKILL.md files | |
| AC2 | yes — grep of `contrib/agent-brief.md` for `code-atlas query`, `--verify-claims`, `--changed-since`, and an occasion whose lines include the route row | |
| AC3 | yes — the named tests pass; `len(instructions)` ≤ `CLIENT_CAP` is already a test | |

### Rule sections

`RULE SECTIONS: 9 applicable — 9 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ prompts.py gains a data row, no language branch · §R1.8 (change-type) ✅ the shell-route lines are one constant rendered into brief and skill · §R2.4 (change-type) ✅ no anchor-repo identifier in any added line · §R3 (change-type) N/A because no node/edge vocabulary, qname or contract version moves · §R6.5 (change-type) ✅ the proving test is seen red before the row exists · §R6.7 (change-type) ✅ the occasion selects map lines; nothing re-typed · §R6.9 (change-type) ✅ the test reads the rendered brief and skill, the consumer side · §R7.2 (change-type) ✅ ledger row in the task and TOKEN_LEDGER · §R7.6 (change-type) ✅ the stale route waivers go in the same commit (W3)`

## Phase 2 — design

### Approach

1. `prompts.RECOGNITION_MAP`: one non-core row, after the two `trace_capability` rows — "A URL, route or command a
   user or test reports — which handler serves it -> trace_capability (route=…)". Placed last so
   `recognition_lines_by_tool` (first line per tool) still selects today's line for today's occasion (H3).
2. `gen_skill.SHELL_ROUTE`: one tuple of lines naming `code-atlas query` (`--args`, `--batch`), `--verify-claim(s)`
   and `--snapshot-symbols` / `--changed-since`; `USAGE_RULES` and `render_skill` both splice it (R1.8).
3. `gen_skill.OCCASIONS`: "A bug report or test doc names a URL" → `search_symbol`, `trace_capability`, `impact`,
   and one `USAGE_RULES` line teaching `route=` / `routes=` / the `routes` rule block; the `route` / `routes` waivers go (W3).
4. Regenerate (`gen_skill.py --write`); CHANGELOG `Unreleased` line.

### Rejected alternatives

- **A per-line selector in `OCCASIONS`** (pick the route row, not the first `trace_capability` row) — a second
  selection grammar for one call site (R7.4); the occasion's prose line carries the route.
- **The route row as `core`** — it would cost instructions characters under the 2,048 cap (343-C1) for a question
  that only arises once a `routes` block is declared.
- **Writing the brief into the anchor repo** — W1, the maintainer's answer.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| a non-core row leaves the server instructions byte-identical | verified | `instructions.render` passes `core_only=True` (`code_atlas/instructions.py:76`) |
| the plugin picks up a new skill body without a version bump | verified | the plugin skill is a committed file read at load; `test_skill_drift` compares bytes only |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | route row | `code_atlas/tools/prompts.py` | `which_tool` text, `test_server_instructions` (non-core: unchanged), `test_routing_surface` | R1, C1, C2 | 1/1 |
| 2 | shell route, occasion, route usage line | `scripts/gen_skill.py` | every `GENERATED` output; the three brief/skill tests | R2 | 1/1 |
| 3 | regenerated outputs | `contrib/agent-brief.md`, `contrib/skill/SKILL.md`, `contrib/claude-code/plugin/skills/code-atlas/SKILL.md` | drift guards | R3 | 3/3 |
| 4 | drop the two route waivers (proof collateral) | `tests/test_agent_brief_usage_completeness.py` | that gate now requires the brief to name both | R2, W3 | 1/1 |
| 5 | proving test | `tests/test_agent_surface_names_shell_route.py` (new) | — | AC1, AC2 | 1/1 |
| 6 | docs | `CHANGELOG.md` | `test_release_discipline` reads the top heading (unchanged) | G1 | 1/1 |
| 7 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

Trace: `grep -rn "RECOGNITION_MAP|recognition_lines|which_tool|OCCASIONS|USAGE_RULES|render_skill" tests scripts code_atlas`
→ `test_agent_brief_announce_and_claude_load.py:37`, `test_agent_brief_in_indexed_repo.py:61`,
`test_agent_brief_usage_completeness.py:55`, `test_routing_surface.py:63`, `test_server_instructions.py:24,81,197,206`,
`test_skill_drift.py:34-43` — all read the map or the render, none pins a row count; each is in the AC3 run.

| Handle | Answer |
|---|---|
| `verify-the-shipped-artifact-not-the-working-tree` | traced: `git check-ignore -v contrib/agent-brief.md contrib/skill/SKILL.md contrib/claude-code/plugin/skills/code-atlas/SKILL.md` → `exit=1 (1 = none ignored)`; `git ls-files` lists all three — the regenerated files ship as committed |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | logic (rendered text) | unit over `recognition_map()` and both committed SKILL.md files | n/a | ✅ |
| AC2 | logic (rendered text) | unit over the committed `contrib/agent-brief.md`, flags derived from `query.main`'s parser (R6.7) | n/a | ✅ |
| AC3 | logic | the ten-guard run plus `scripts/gate.sh` | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_agent_surface_names_shell_route.py` — red before the change (no route row,
no `code-atlas query` in any surface), green after.

### Rollback

`git revert` the branch's commits; one repo, nothing to port. `SCOPE: S` holds (two source files, generated outputs).

## Phase 3 — execute

Commits `e7a167fa` (the change) and `ebc0c3af` (CHANGELOG).

**Red first.** `.venv/bin/python -m pytest -q tests/test_agent_surface_names_shell_route.py` before the change:

```
FAILED tests/test_agent_surface_names_shell_route.py::test_which_tool_routes_a_reported_url_to_trace_capability
FAILED tests/test_agent_surface_names_shell_route.py::test_the_brief_and_both_skills_teach_every_query_flag
FAILED tests/test_agent_surface_names_shell_route.py::test_the_brief_has_a_url_occasion_that_selects_trace_capability
3 failed in 0.50s
```
Ran at 56ec66b2.

**Green after.** The same command: `3 passed in 0.42s`. The twelve guards (the ten baseline files plus the proving
test and `test_routing_surface`): `228 passed, 1 xfailed in 2.86s`. `ruff check` and `mypy` on the touched sources:
`All checks passed!` · `Success: no issues found in 1 source file`. Map rows: 26 total, 8 core (core unchanged, so the
server instructions are byte-identical). Ran at ebc0c3af.

**Axis 1 — file set.** `git diff --name-only main..HEAD` lists exactly change-list rows 1–7 (10 files); nothing else.
`gen_skill.py --write` rewrote the four other `GENERATED` files byte-identically. `ruff format --check
code_atlas/tools/prompts.py` reports a pre-existing hunk at line 143 (red on `main` too, checked by stashing) —
left untouched (R7.7).

**Axis 2 — design conformance.**

| Approach bullet | Result |
|---|---|
| 1 route row, non-core, last of the three | implemented-as-approved |
| 2 `SHELL_ROUTE`, spliced into brief and skill | implemented-as-approved |
| 3 URL occasion, route usage line, waivers dropped | implemented-as-approved |
| 4 regenerate, CHANGELOG `Unreleased` | implemented-as-approved |

No deviation, no design invalidation.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` — verdict **clean (challenger only — REVIEWER: OFF)**.

**Challenger** (ticket-blind: the raw ticket above the separator plus `git diff main..branch` without this file;
1 dispatch, 56,371 tokens): 3/3 requirements met, every new claim checked against `query.py`, `symbol_changes.py`,
`trace_capability.py`, `impact.py`, `search_symbol.py`, `claim.py`. Two Minor findings, both landed in `89f83865`:

| # | Finding | Resolution |
|---|---|---|
| F1 | "URL, route or command" over-promises: a route key goes through `urlsplit` (`code_atlas/routes.py:66`) | "or command" dropped from the row and the usage line |
| F2 | the exit codes of `code-atlas query` are unstated, which a CI caller needs | the batch line points at `code-atlas query --help` |

Verify-only round, main loop: the fixes stay inside F1–F2 and the approved files. Affected proof re-run:
`97 passed in 1.25s` (proving test, drift, completeness, brief, instructions, routing, plugin, snippets). Ran at 89f83865.

**Gate.** `scripts/gate.sh` on this host (`php`, `composer`, `node`, Python 3.13 present):
`21 passed · 0 failed · 0 skipped` · `GATE GREEN — all 21 checks passed` (`pytest -q` among them). Ran at 89f83865.

**Scope.** File axis: the ten change-list files, nothing else. Behaviour axis: the four Approach bullets as approved;
F1 narrows wording only. Regression scan: the Phase-2 consumers all sit in the gate's `pytest -q`.

| Row | Ph3/4 proven by | k/N |
|---|---|---|
| G1 | brief + both skills + `which_tool` render the route and the shell route | 1/1 |
| C1 | `test_skill_drift::test_the_recognition_map_covers_every_served_tool`; roster still 24 | 1/1 |
| C2 | `test_server_instructions` (core rows 8, unchanged) | 1/1 |
| R1 / AC1 | `test_which_tool_routes_a_reported_url_to_trace_capability` | 1/1 |
| R2 / AC2 | `test_the_brief_and_both_skills_teach_every_query_flag`, `test_the_brief_has_a_url_occasion_that_selects_trace_capability` | 2/2 |
| R3 / AC3 | `test_skill_drift` parametrised over every `GENERATED` path; gate green | 1/1 |

Reviewed at 89f83865 — files: `CHANGELOG.md`, `code_atlas/tools/prompts.py`, `scripts/gen_skill.py`,
`contrib/agent-brief.md`, `contrib/skill/SKILL.md`, `contrib/claude-code/plugin/skills/code-atlas/SKILL.md`,
`tests/test_agent_brief_usage_completeness.py`, `tests/test_agent_surface_names_shell_route.py`, `docs/BACKLOG.md`.
Working doc: `docs/tasks/387_agent-surface-names-382-385.md`.

## Phase 5 — finalise

**Durable lesson.** 382–385 each shipped an entry point an agent could not find: a CLI and a rule-file kind have no
tool description, so only the brief and the skill can carry them, and no guard asked. Recorded as 387-C1.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Stale-review guard: `git diff --name-only 89f83865..HEAD` plus the working tree touch only this file,
`docs/LESSONS.md`, `docs/BACKLOG.md` and `docs/TOKEN_LEDGER.md` — bookkeeping, or in the reviewed set. Not stale.

### Outward actions

Under the handover: push `feat/387-agent-surface-names-382-385`; open the PR against `main`.
Deferred to the maintainer: ratify W2–W3 and 387-C1's classification; merge; refresh a consuming repo's `AGENTS.md`
with `gen_skill.py --write-agent-brief <repo>` (W1: not done here).

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 48,146 |
| 4 review | `challenger` (ticket-blind) | 1 | 56,371 |

`LEDGER TOTAL: 104,517 · top cost driver: challenger`
