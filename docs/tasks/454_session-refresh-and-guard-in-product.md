---
id: 454
slug: session-refresh-and-guard-in-product
title: "The anchors' session refresh and symbol guard become product scripts, so no anchor keeps a copy"
phase: 2
milestone: Freshness
status: done
depends_on: [453, 377]
---

## Why this exists

Epic 451. the PHP anchor keeps `code-atlas-session-refresh.sh` (6.3 KB) and `code-atlas-symbol-guard.sh`
(19 KB); the Python/TS anchor ported both (4 KB, 11 KB) and they already differ. Both add what the product
lacks: a session-start reminder that survives compaction, an incremental refresh when `behind`,
and a `PreToolUse` refusal of a grep for a symbol until code-atlas was asked about that name. The
product's own nudge (345) runs `PostToolUse`, after the grep already answered.

## Scope

1. `code-atlas-state` on SessionStart (all sources, compaction included) prints the routing
   reminder when the index can answer, and starts the background refresh when `behind`.
2. A `code-atlas-guard` script for `PreToolUse(Grep|Bash)`: refuses a symbol-shaped grep until
   the transcript holds a code-atlas query naming it; any non-argument code-atlas error lifts it
   for the session. The symbol shapes come from the configured adapters, not a hard-coded language
   list (R1.1); unsure always means allow.
3. Mode is configurable (`off` / `nudge` / `refuse`), recorded by `code-atlas-setup`; default `nudge`.
4. Plugin `hooks.json` and the setup-written settings both call it; the anchors' scripts are removed
   in their own repos (listed here, not done by this ticket).

## Acceptance criteria

- **AC1:** a fixture transcript with `grep -rn "def foo"` and no prior query → refused in `refuse`
  mode, nudged in `nudge` mode; after a `search_symbol foo` → allowed.
- **AC2:** a literal-text grep (string, config key) is never touched.
- **AC3:** the guard adds under 50 ms per call on the fixture (measured).
- **AC4:** both anchors run with their own scripts removed and keep the behaviour (field check).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 454 · **work_doc_mode:** embed · **Current phase:** finalise
- `TRACK: backend` · Run mode: `autorun 452 - 453 - 454 - 455 - 451`, third — `REVIEWER: OFF` (waived: "with
  skipped reviewer") · `CHALLENGER: ON` · `cost_tier: standard`. The handover delegates decisions, so a
  want-decision is `ASSUMED`, never silent.
- Branch `feat/454-session-refresh-and-guard-in-product` from `feat/453-code-atlas-setup` at `66b38e48`, in a
  worktree. Contract `.mango/run-contract-454.txt`; RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 8 want-decision asked | 4 how-decision resolved+cited | 8 ASSUMED | skip: no`

`code-atlas-state`, the plugin `hooks.json`, 345's nudge, 377's `index_answers` and 453's `code-atlas-setup` resolve.
Recalled by handle: 453-C1 `an-appended-hook-block-must-be-reached` (this ticket edits the hook table setup writes).
The exposure-checker ran after the code was drafted (disclosed in Phase 3); its 5 decisions are W4–W8.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the shapes | how | the adapters' stamped `symbol_shapes` (345), so the core names no language (R1.1) |
| H2 | one hook, not two | how | the guard replaces the nudge's table entries; `nudge` mode is 345's line, earlier — two hooks would judge each grep twice |
| H3 | the refresh | how | the state hook starts it only when `behind`; the plugin's unconditional start is removed (a no-op incremental costs ~60 s at scale, 052) |
| H4 | refuse-mode freshness | how | stored last commit == HEAD and no build running; the full status payload took 3,028 ms on the PHP anchor |
| W1 | names a grep asks about | want | **ASSUMED:** the pattern's identifiers less the shapes' keywords; none → allow |
| W2 | what lifts a refusal | want | **ASSUMED:** a code-atlas call naming one identifier, or a code-atlas error other than a bad argument |
| W3 | the reminder | want | **ASSUMED:** one fixed line at SessionStart / PreCompact / PostCompact on a settled index |
| W4 | an escape hatch | want | **ASSUMED:** `code-atlas-setup --guard nudge`, named in the refusal text |
| W5 | a stale or missing index in refuse mode | want | **ASSUMED:** allow — unsure allows |
| W6 | which commands | want | **ASSUMED:** `Grep`, `grep`, `rg`, `git grep` (the hook filters); `ag`, `find -exec grep` are not judged |
| W7 | anchor parity | want | **ASSUMED:** the guard, the reminder and the refresh-when-behind; the anchors' MCP-registration probes and `~/.claude.json` env import are dropped (452 replaced the latter) |
| W8 | existing installs | want | **ASSUMED:** a re-run of `code-atlas-setup` swaps the nudge entries for the guard's; the recorded mode is kept |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=4 G=1 AC=4`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/15 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "Both add what the product lacks" | product scripts; anchors keep none | ✅ |
| R1 | Scope 1 | "prints the routing reminder when the index can answer, and starts the background refresh when `behind`" | W3, H3 | ✅ |
| R2 | Scope 2 | "refuses a symbol-shaped grep until the transcript holds a code-atlas query naming it …" | W1, W2, H1, H4 | ✅ |
| R3 | Scope 3 | "Mode is configurable (`off` / `nudge` / `refuse`), recorded by `code-atlas-setup`; default `nudge`" | `--guard` | ✅ |
| R4 | Scope 4 | "Plugin `hooks.json` and the setup-written settings both call it" | one generated table | ✅ |
| C1 | Scope 2 | "not a hard-coded language list (R1.1); unsure always means allow" | H1, W5 | ✅ |
| AC1 | Acc 1 | "refused in `refuse` mode, nudged in `nudge` mode; after a `search_symbol foo` → allowed" | fixture transcript | ✅ |
| AC2 | Acc 2 | "a literal-text grep … is never touched" | fixture | ✅ |
| AC3 | Acc 3 | "the guard adds under 50 ms per call on the fixture (measured)" | median of 5 in-process calls | ✅ |
| AC4 | Acc 4 | "both anchors run with their own scripts removed and keep the behaviour (field check)" | exclusion + read-only probe | ✅ (exclusion) |

**Gap.** The nudge speaks at `PostToolUse`, after the grep answered (`hooks/nudge.py`); the state hook is silent on a
current index; nothing refuses.

`BASELINE: green — state, nudge, plugin, setup, skill, contrib, doc-budget and instructions suites: 532 passed, 19 skipped`

Ran at 66b38e48 (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q <the same suites, less test_grep_guard.py>
532 passed, 19 skipped in 25.90s
```

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 shapes come from the stamped adapter handshake, guard.py names no language · §4 (change-type) ✅ R4.2 state_line keeps its old output unless the hook asks for the reminder · §5 (change-type) ✅ R5.5 an unsure guard allows and says why on stderr · §6 (change-type) ✅ the proving test is seen failing on the base · §7 (change-type) ✅ R7.6 TOOLS, contrib README and PLAN replace the nudge text rather than add beside it · §9 (change-type) ✅ R9.1 the recorded mode is read as one of three values, R9.3 the refresh log opens through containment · §3 N/A because no contract vocabulary changes`

## Phase 2 — design

`HANDLES: 1 recalled | 0 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- `an-appended-hook-block-must-be-reached` — does not apply because this change edits the Claude Code hook table, a
  JSON list Claude Code runs whole; no shell hook body is appended to.

**Approach.** (1) `code_atlas/hooks/guard.py` + console script `code-atlas-guard`. (2) `scripts/gen_skill.py`: the
`Grep`/`Bash(grep|rg|git grep)` entries call the guard at `PreToolUse`; the plugin's unconditional refresh is removed;
regenerated `hooks.json`, `settings.snippet.json`, `code_atlas_hooks/table.py`. (3) `state_line(remind=, refresh=)`:
the reminder on a settled index, a detached refresh when `behind` at SessionStart; `index_answers` ignores
`unguarded` (a 453 regression found here: the nudge went silent in every repo without setup). (4)
`code-atlas-setup --guard`. **Rejected:** keeping the PostToolUse nudge beside a PreToolUse guard (double judgement);
`index_answers` in refuse mode (3 s per grep at scale); reading the transcript with a size-unbounded parse (capped
at 32 MB, larger allows). **Assumptions:** a PreToolUse hook's `permissionDecision: deny` blocks the call — `verified`
(the anchors' guard relies on it in the field). **Proving test:** `tests/test_grep_guard.py`.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| guard | `code_atlas/hooks/guard.py`, `pyproject.toml` | `test_core_is_language_agnostic.py` (module count) | R2, C1 |
| table | `scripts/gen_skill.py`, `contrib/claude-code/plugin/hooks/hooks.json`, `contrib/claude-code/settings.snippet.json`, `code_atlas_hooks/table.py` | `test_claude_code_plugin.py`, `test_skill_drift.py` | R4 |
| reminder, refresh | `code_atlas/hooks/state.py` | `test_session_state_hook.py`, `test_state_line_on_screen.py`, `test_grep_nudge.py` | R1 |
| mode | `code_atlas/setup_hooks.py` | `test_code_atlas_setup.py` | R3 |
| proving test | `tests/test_grep_guard.py` | — | AC1–AC3 · 3/3 |
| docs | `docs/TOOLS.md`, `contrib/claude-code/README.md`, `docs/PLAN.md`, `CHANGELOG.md` | — | R7.6 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | — | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC2 | integration (index + transcript on disk) | integration: `guard.guard` over a stamped index and a JSONL transcript | n/a | ✅ |
| AC3 | runtime (per-call cost) | integration: timed in-process calls; the anchor probe below | n/a | ✅ |
| AC4 | runtime on the anchors | manual-recorded (exclusion) | n/a | ✅ |

**Coverage-gap exclusions.**
- AC4 · risk: medium · why deferred: removing the anchors' scripts is a write to two other repos; a read-only probe on
  the PHP anchor's index stands in (Phase 3) · follow-up: remove them once a release with 452–454 is installed there ·
  expiry: the first release that ships 454 · seen: 454

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

Rollback: revert the commit; `code-atlas-setup` re-run puts the previous table back. Porting: one repo.

## Phase 3 — execute

Main loop, no `implementer`, in a worktree, at `a4140c8d`. **Sweep.** Axis 1: the diff is the approved list; `ruff`
and `mypy` clean. Axis 2: approach (1)–(4) implemented-as-approved.

**Recorded deviations.** (a) Process: the code was drafted before this record, and the exposure-checker ran after
the draft; its five decisions (W4–W8) changed one line (the refusal names its escape hatch). (b) `index_answers`
ignoring `unguarded` is a fix to 453 found here, carried in this change and in 453's own branch.

The proving test on the base (copied alone into a clean worktree of `66b38e48`):

Ran at 66b38e48 (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_grep_guard.py
E   ImportError: cannot import name 'guard' from 'code_atlas.hooks'
```

**AC3 at scale, AC4 probe (read-only, the PHP anchor's index, this branch's `guard._refusal`).**

Ran at a4140c8d
```
'grep -rn "function findUser" src/' transcript=empty: deny (23 ms)
'grep -rn "function findUser" src/' transcript=asked: allow (3 ms)
'grep -rn "TODO" src/' transcript=empty: allow (1 ms)
```
Before H4 the same denial took 3,028 ms (the full status payload).

## Phase 4 — review

`REVIEWER: OFF` (waived by the run's args — no rule-book seat looked) · `CHALLENGER: ON`. Review step: the ticket-blind
`challenger` alone; payload = the raw ticket (`git show 66b38e48:<this file>`) + the branch diff, working doc excluded.

- **Round 1** at `9ef12457` (73,222 tokens): 8 rebuilt · 7 met · 1 not met (AC4, the exclusion). **Taken** (`89e775fb`):
  F2 — `required` in the argument-error pattern read a server's "rebuild required" as a bad argument, so the refusal
  never lifted; F5 — `start_refresh` had no test that could fail, now a stand-in script proves argv, detach and log.
  **Accepted:** F1 (an absent server: the agent's own failed call lifts it, and the refusal names the human's switch),
  F3 (a transcript over 32 MB allows — unsure allows), F4 (substring match errs toward allowing), F6 (the reminder at
  PreCompact is discarded by the host, harmless).
- **Verify-only** (main loop, no re-dispatch: both fixes sit inside the named findings and approved files).

`CHALLENGER VERDICT: 8 requirement(s) rebuilt | 7 met | 1 not met | 0 can't tell | 1 not-met covered by a recorded exclusion`

Ran at 89e775fb
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_grep_guard.py <state, nudge, plugin, setup, skill, contrib, doc-budget, instructions suites>
539 passed, 19 skipped in 27.65s
```

Reviewed at 89e775fb — files: `code_atlas/hooks/guard.py`, `code_atlas/hooks/state.py`, `code_atlas/setup_hooks.py`,
`code_atlas_hooks/table.py`, `scripts/gen_skill.py`, `contrib/claude-code/plugin/hooks/hooks.json`,
`contrib/claude-code/settings.snippet.json`, `pyproject.toml`, `tests/test_grep_guard.py`,
`tests/test_session_state_hook.py`, `tests/test_state_line_on_screen.py`, `tests/test_claude_code_plugin.py`,
`tests/test_core_is_language_agnostic.py`, `docs/TOOLS.md`, `contrib/claude-code/README.md`, `docs/PLAN.md`,
`CHANGELOG.md`; working doc `docs/tasks/454_session-refresh-and-guard-in-product.md`.

`Ph3/4 proven by`: R1–R4, AC1–AC3 → `tests/test_grep_guard.py` (8) and the state suites; AC4 → exclusion (expiry: the
first release shipping 454), with the anchor probe in Phase 3.

- **Round 2** (resumed, 4,857 tokens; 78,079 cumulative − 73,222): after publishing on 453's tip, the full gate made
  two guards name this change — SEC-IN-14's spawn allow-list gains `hooks/state.py` (its own scripts, asserted
  never git) and SEC-PL-02 names the renamed plugin test. Re-reviewed: no guard weakened; verdict unchanged.
  Gate: GATE GREEN at `80d44f7a` (26 passed).

## Phase 5 — finalise

Stale-review guard: only bookkeeping after the review — not stale.

**Durable lesson.** 454-C1 `per-call-hook-reads-the-cheapest-signal` (type 2, first sighting) in `docs/LESSONS.md`.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/454-session-refresh-and-guard-in-product`; open its PR against
`feat/453-code-atlas-setup` (stacked), published as one commit carrying this tree. Deferred to the maintainer:
ratify W1–W8; remove the anchors' own scripts once a release ships (AC4's exclusion); merge after #184.

Next: 455. Revert: revert the commit and re-run `code-atlas-setup` to restore the previous hook table.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 49,638 |
| 4 review | ticket-blind `challenger` | 1 | 73,222 |
| 4 review | ticket-blind `challenger` | 2 | 4,857 (resumed: 78,079 − 73,222; the post-gate delta) |

`LEDGER TOTAL: 127,717 · top cost driver: 4 review / challenger` — main loop unmeasured.
