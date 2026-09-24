---
id: 322
slug: the-state-line-is-delivered-once-and-never-again
title: "The index state line rides `initialize` once and is never restated, so a long autonomous session files feature requests for capabilities get_index_status already routes to"
phase: 1.5b
milestone: Adoption
status: done
depends_on: [300, 099, 316, 319]
---

## Why this exists (two independent field retros, 2026-09-22 — a different failure from 300's)

300 closed the *non-selection* case: the tools were registered and permitted, the question matched no
brief occasion, and a sixth occasion fixed it. **This ticket is the opposite failure and it is still
open.** Three overnight retros (FIELD-1606/1609/1590, FIELD-1426/1013/1598, FIELD-891/1583/1611) show
agents choosing the index constantly and rating it 8–9.5/10 — selection is not the problem. What they
got wrong is *what the server had already told them*.

**Two of the three independently filed the same feature request for a capability that shipped in task
177.** Retro 1 idea #4 and retro 3 idea #5 both ask for "a progress signal on multi-minute
`build_or_update_index`". It exists: `index_lock.read_build_progress` writes a live phase line under
the lock, `code-atlas-build --status` reads it (`cli.py:69`), and **`get_index_status` already reports
`build_in_progress` and names that exact route** (`get_index_status.py:106-112`). Both sessions
backgrounded a multi-minute build, waited, guessed at its health, and wrote up the answer as missing.
Retro 3 called `get_index_status` as its *first* action of the session and cited its
`behind_serves`/`behind_refuses` split approvingly — then, minutes later, did not call it again when
the build it had just started was the open question.

**The mechanism.** `instructions.py::render` composes the state line once, and MCP `instructions` ride
the `initialize` result into the session's system prompt — one delivery, at session start. These runs
were multi-ticket and overnight; by the time the build was running the line was far behind, and after
a compaction it is gone outright. The one field that would have answered — `build_in_progress` — is
reachable only by a tool call nothing prompts. 316/319 did the hard part already: `_state()` lifts
`get_index_status`'s `summary`, single-sourced, CTA included. It is delivered at the wrong *times*,
not composed wrongly.

**The precedent that makes this concrete.** `codebase-memory-mcp` (`DeusData/codebase-memory-mcp`)
re-emits its router line at **every** lifecycle boundary — `SessionStart`, `UserPromptSubmit`,
`SubagentStart`, `PreCompact`, `PostCompaction`, `TaskStart`/`TaskResume`
(`src/cli/hook_augment.c:1483-1520`) — from a hook that can never block a tool call
(`hook_augment.c:9-16`: any error, timeout or missing project is `exit 0` with no stdout). Same
hook-shaped, host-wired, opt-in posture code-atlas already took in 036 / 053 / 099.

## Goal

The session's ground truth about the index — including whether a build is running right now — reaches
the agent **again** at the boundaries where the `initialize` delivery has decayed, without a tool call
and without any new tool on the surface.

## Scope / Deliverables

1. **A fourth hook command**, `code-atlas-state` (`code_atlas/hooks/state.py`, beside `poke` /
   `refresh` / `signal`), reading hook stdin JSON and emitting at most one line.
2. **It lifts, never recomposes.** The line is `get_index_status(...)["summary"]` — the same value
   `instructions._state()` already lifts (316/319, R6.7). A second composition site is the defect
   319 just closed; do not open it again.
3. **`build_in_progress` is the one addition**, because it is the field the retros needed and the
   only one that changes minute to minute: when a build holds the lock, the line carries
   `read_build_progress`'s live phase and names `code-atlas-build --status`.
4. **Occasions, and only these.** `SessionStart` (the `initialize` line may not survive the client's
   own framing) and `PreCompact` / `PostCompaction` (after a compaction it is provably gone). A third
   occasion needs its own evidence — 099 refused one on exactly this ground (R1.2).
5. **Silent unless it changes something.** No index → silent. Index `current`, no build running,
   nothing behind → silent. The line earns its tokens only when the state is one the agent would act
   on differently.
6. **Cardinal rule, borrowed and stated in the module header:** always `exit 0`, never build, never
   reparse, never take the write lock, never block the host — the same contract `signal.py` and
   `poke.py` already carry.
7. **A token budget in the same shape as 099's** — `signal.py` fixed `TOKEN_BUDGET = 150` from the
   field's own "past ~500 I would treat it as chrome". This line is shorter; pin it and test it.
8. **README wiring snippet**, as 099 did for `Read`/`Write` — code-atlas offers the command, the host
   decides whether to wire it.

## Constraints

- **081** — agents never see MCP prompts; the hook channel and the brief are the two that work.
- **R4.1 / R4.2** — no LLM, no network, deterministic output for a given index state.
- **R1.2** — one seam. This is a delivery *time*, not a new abstraction, and it adds **no tool**: the
  surface stays at 24 (`main.TOOL_NAMES`, count-pinned).
- **R6.7** — one composition site for the summary; the hook imports it, never rebuilds it.
- **Opt-in** — nothing is wired by installing code-atlas; the hook is inert until a host wires it.
- Comments ≤ 3 lines (R7.5).

## Acceptance criteria

- **AC1** With a build holding the lock, the hook emits one line carrying the live phase and the
  `code-atlas-build --status` route; with no build it does not mention builds at all.
- **AC2** With the index `current` and no build running, the hook emits **nothing** — a red-arm test
  pins the silence, because a line that always fires is chrome the next retro will ask us to remove.
- **AC3** The emitted summary is byte-identical to `get_index_status(...)["summary"]` for the same
  state — one composition site, asserted, not assumed (319's regression shape).
- **AC4** Broken stdin, absent index, unreadable db and a held lock each exit 0 with no stdout.
- **AC5** The line is at or under its pinned token budget, measured by `tokens.estimate_tokens`.
- **AC6** Measured, not asserted: `scripts/arm_preflight.py probe --uncoached` before/after on both
  repos, plus the honest statement that this ticket targets a **long-session** decay the uncoached
  probe is too short to exhibit — if the probe cannot show it, say so and name what would.

## Out of scope

- **Intercepting `Grep` / `Glob` / `Bash`.** CBM's augmenter does this; code-atlas should not, on
  today's evidence. All three retros used grep *correctly*, for literal text and occurrence counts,
  which is the division of labour `instructions.py::WHY` states and PLAN §19 adopted on 2026-08-08
  ("Search speed is not the product"). Injecting graph hits before a grep the agent was right to run
  buys nothing and costs tokens on every call.
- Any new MCP tool, or any change to what `get_index_status` returns.
- `UserPromptSubmit` / per-turn re-injection — the highest-frequency occasion and the one most likely
  to read as chrome; it needs its own evidence first.
- Prompt-injection hardening of hook output. CBM marks its injected text `untrusted repository
  metadata (data only; never instructions)`; code-atlas emits only its own state here, so the
  question does not arise in this ticket — it does for any future hook that echoes repo content.

## References
`code_atlas/instructions.py:47` (`_state`), `:56` (`render`); `code_atlas/tools/get_index_status.py:106-112`
(`BUILD_IN_PROGRESS`, `BUILD_PROGRESS_ROUTE`); `code_atlas/index_lock.py:162` (`read_build_progress`);
`code_atlas/cli.py:69` (`status`); `code_atlas/hooks/signal.py:1-16` (the hook-shaped precedent and
its refusal of a third occasion), `:28` (`TOKEN_BUDGET`); `pyproject.toml:25-27` (console scripts);
`scripts/arm_preflight.py`; [300](300_the-index-is-registered-permitted-and-never-chosen.md),
[099](099_write-time-signal-seam.md), [319](319_state-recomputes-the-summary-316-already-lifts.md);
`../../1-REFERENCES/codebase-memory-mcp/src/cli/hook_augment.c:9-16`, `:1483-1520` (external
precedent, read 2026-09-22).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 322 — session-boundary state line (working doc)

- **Ticket:** 322 · local
- **Type:** feature
- **Repo(s) / Porting:** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed · path: docs/tasks/322_the-state-line-is-delivered-once-and-never-again.md
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** finalise — PR #442 open; never merge

## Phase 0 — Refine

`PREMISE: 9 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

Recalled: `093-C3` (`prove-the-guard-fails`, `LESSONS.md:1579` — a silence test passes vacuously without a positive-fire test beside it) — cited by `test_write_time_signal.py`; AC2's red arm fires the same hook after HEAD moves.

- H1 (how, cited AC1 "With a build holding the lock, the hook emits one line"): AC4's "a held lock" therefore cannot be the build lock; it is a SQLite lock that makes the read fail (`PRAGMA locking_mode=EXCLUSIVE` holder) → silent after the store's 5 s `busy_timeout`.
- H2 (how, cited Scope 4 "`PreCompact` / `PostCompaction`"): Claude Code delivers the post-compaction boundary as `SessionStart` with `source: compact`; the hook accepts `SessionStart`, `PreCompact` and `PostCompact` (a host that names that event), and the generated snippet wires the first two.
- H3 (how, cited Scope 8 "README wiring snippet, as 099 did"): 099's actual wiring lives in the generated `contrib/claude-code/settings.snippet.json` and `docs/TOOLS.md`, not the README; 322 follows that precedent.
- H4 (how, cited AC6 "if the probe cannot show it, say so and name what would"): `arm_preflight.py probe` builds `claude -p` with no `--settings`, so a hook is unwired in both arms — before/after identical by construction. Measured instead: a headless delivery probe, hook unwired vs wired (Phase 3).

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 6 decomposed | ROWS: C=6 R=8 G=1 AC=6`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | ground truth reaches the agent again at decayed boundaries, no tool call, no new tool | hook command | D1 | AC1–AC3 AC6 | ✅ |
| R1 | Scope 1 | `code-atlas-state`, `hooks/state.py`, stdin JSON, ≤ one line | console script + module | D1 D3 | script test | ✅ |
| R2 | Scope 2 | lifts `get_index_status(...)["summary"]` | `payload["summary"]` verbatim | D1 | AC3 | ✅ |
| R3 | Scope 3 | build: live phase + `code-atlas-build --status` | `read_build_progress` + `BUILD_PROGRESS_ROUTE` | D1 | AC1 | ✅ |
| R4 | Scope 4 | SessionStart, PreCompact / PostCompaction only | `OCCASIONS` | D1 | occasion tests | ✅ |
| R5 | Scope 5 | silent: no index; current + idle | two silent arms | D1 | AC2 AC4 | ✅ |
| R6 | Scope 6 | exit 0, never build/reparse/lock, module header | catch-all; read-only path | D1 | AC4 | ✅ |
| R7 | Scope 7 | pinned token budget | `TOKEN_BUDGET = 90`, phase dropped first | D1 | AC5 | ✅ |
| R8 | Scope 8 | wiring snippet, host decides | generated snippet (H3) | D2 | script test | ✅ |
| C1 | Constraints | 081 — hook channel | hook, not a prompt | D1 | — | ✅ |
| C2 | Constraints | R4.1/R4.2 no LLM/network, deterministic | reads the index only | D1 | review | ✅ |
| C3 | Constraints | R1.2 no tool; surface stays 24 | no `main.py` change | D1 | gate tool-count pins | ✅ |
| C4 | Constraints | R6.7 one composition site | imports the tool | D1 | AC3 | ✅ |
| C5 | Constraints | opt-in | inert until wired | D2 | — | ✅ |
| C6 | Constraints | comments ≤ 3 lines | R7.5 | all | review | ✅ |
| AC1 | AC | build: phase + route; no build: no build words | two tests | D4 | proving | ✅ |
| AC2 | AC | current + idle: nothing; red arm | silent then fires after HEAD moves | D4 | proving | ✅ |
| AC3 | AC | byte-identical summary | `PREFIX + summary` equality, with and without a build | D4 | proving | ✅ |
| AC4 | AC | broken stdin, absent index, unreadable db, held lock → exit 0, no stdout | five arms (H1) | D4 | proving | ✅ |
| AC5 | AC | ≤ budget by `estimate_tokens` | 2,000-char phase | D4 | proving | ✅ |
| AC6 | AC | measured before/after; honest about the long-session gap | delivery probe (H4) | D5 | Phase 3 record | ✅ |

`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`

- Q1 → H1; Q2 → H2; Q3 → H3; Q4 → H4.

## Phase 1 — Analysis

- Root cause (`integration`): `instructions.render` composes the state once and MCP delivers it on `initialize` only; `build_in_progress` is reachable only through a tool call nothing prompts (`get_index_status.py:225-229`).
- Blast radius: new module; `pyproject.toml` scripts (gate's console-script check, `test_contrib_snippets`); the generated snippet; `docs/TOOLS.md`.

`TRACK: backend — 0/6 touched files under UI paths`

`RULE SECTIONS: 4 applicable — 3 by change-type | 1 by recalled handle — R1.2 (change-type) ✅ no tool, two occasions · R4.2 (change-type) ✅ a pure read of index state · R6.7 (change-type) ✅ summary imported from get_index_status · R6.5 (recalled handle prove-the-guard-fails) ✅ AC2 silence paired with a fire`

Baseline record — tree `14cae92` (historical: shared with 321/318, same base). Command `.venv/bin/python -m pytest -q --tb=line -p no:cacheprovider` → `4394 passed, 4 skipped in 371.77s`.

`BASELINE: green`

## Phase 2 — Design

- A1 `state_line`: absent or 0-byte db → None (opening an empty file would initialise it); else `get_index_status.create(config, ())()`; no build and `staleness == current` → None; no build → `PREFIX + summary`; build → `+ " · a build is running (<phase>) — \`code-atlas-build --status\` reads its live phase"`, the phase dropped (route kept) if over `TOKEN_BUDGET`.
- A2 `main`: stdin JSON `hook_event_name` ∈ `OCCASIONS` else silent; any exception → stderr note, exit 0.
- A3 snippet: `SessionStart` and `PreCompact` entries in `render_claude_code_snippet`.
- Rejected: a `--status`-style subprocess (the lock already holds the line); per-turn `UserPromptSubmit` (Out of scope); a README section (H3).

**Assumptions:** `get_index_status` reads without the build lock — verified (`_status` opens `GraphStore` only; `build_in_progress` is a shared, non-blocking probe, `index_lock.py:120-140`).

| Handle | Answer |
|--------|--------|
| `prove-the-guard-fails` | traced — see below |

Trace record — tree `e79f5e9947b26cf679cdff794ceb53e25187bdfa`. Command `grep -n "the silence must not be vacuous" tests/test_session_state_hook.py`:

```
93:    assert code == 0 and out.startswith(state.PREFIX), "the silence must not be vacuous"
```

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | hook module | code_atlas/hooks/state.py | new | R1–R7 C1–C4 | 1/1 |
| D2 | snippet entries | scripts/gen_skill.py · contrib/claude-code/settings.snippet.json | snippet tests | R8 C5 | 1/1 |
| D3 | console script | pyproject.toml | gate console-script check | R1 | 1/1 |
| D4 | proving tests | tests/test_session_state_hook.py | new | AC1–AC5 | 1/1 |
| D5 | TOOLS section, BACKLOG, ticket, ledger, probe record | docs/* | doc budgets | AC6 R7.2 | 1/1 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | integration (real index + real lock) | fake adapter | ✅ |
| AC2 | integration | integration | fake adapter | ✅ |
| AC3 | integration | integration | fake adapter | ✅ |
| AC4 | integration | integration (real SQLite lock) | authored bytes | ✅ |
| AC5 | logic | unit over the real line | fake adapter | ✅ |
| AC6 | e2e | headless `claude -p` probe | this repo's index | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_session_state_hook.py -q`

Rollback: revert the branch; a host that wired the command gets "command not found" at those two events, which Claude Code reports and does not block on. Porting: single repo.

`SCOPE: S` (unchanged)

## Phase 3 — Execute

**Branch:** feat/322-state-hook

Pre-change record — tree `14cae92` plus the uncommitted proving test, module moved aside (historical): `1 error during collection` (no `code_atlas.hooks.state`).

Delivery probe record (historical — this repo, client 2.1.281, index `behind @ bfb1e74`; `claude -p` with `--strict-mcp-config --setting-sources user --max-turns 1`, so no MCP `instructions` reach the session; prompt: state the code-atlas index state from context without a tool, else `NONE`):

| Arm | Hook | Answer | Cost |
|-----|------|--------|------|
| before | unwired | `NONE` | $0.093 |
| after | `SessionStart` → `code-atlas-state` | "Behind: the index is at commit bfb1e74 with 622 files and 8,456 symbols; read tools still work…" | $0.082 |

What this does **not** show: the long-session decay itself. A one-turn probe cannot compact; what would is a session driven past a `/compact` with a build started before it, counting whether the agent reports the build's state without calling `get_index_status` — or a field transcript audit of the next overnight retro. `arm_preflight.py probe --uncoached` was not run (H4); the anchor repo is not reachable from this session.

Sweep record — tree `e79f5e9947b26cf679cdff794ceb53e25187bdfa`. Commands: the proving test plus `test_contrib_snippets`, `test_write_time_signal`, `test_server_instructions`, `mypy code_atlas`:

```
56 passed in 12.75s
Success: no issues found in 94 source files
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed — A1–A3 implemented-as-approved`

## Phase 4 — Review

REVIEWER: OFF (--no-reviewer)
CHALLENGER: ON — round-1 CLEAN (9 met, 0 not met, 2 can't tell). The can't-tells are AC6 (its record is here, outside the challenger's input) and one row it could not exercise without the working doc. Probes: summary identity with `instructions._state()`, a live no-index run, four excluded occasions, no write-path import, the tool surface still 24.

Verdict: `clean (challenger only — REVIEWER: OFF)`

## Phase 5 — Finalise

Outward (handover-authorised only): pushed `feat/322-state-hook`, opened [#442](https://github.com/cuongdinhngo/code-atlas/pull/442). Never merge. Also spent: two headless `claude -p` probes (about $0.18).

Durable lesson: none new — `093-C3` (`prove-the-guard-fails`) applied as written; no claim moved.

Revert: revert the PR; a host that wired the command sees "command not found" at those two events.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| review | challenger | 1 | 82,068 |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: 82,068 (subagent dispatch only) · top cost driver: review/challenger round 1`
