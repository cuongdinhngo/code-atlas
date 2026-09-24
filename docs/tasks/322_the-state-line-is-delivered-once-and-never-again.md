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
