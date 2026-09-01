---
id: 200
slug: the-recognition-map-is-a-prompt-no-agent-can-read
title: 'The recognition map is an operator prompt no model can read, and the one channel a model does see is wired for one agent and one language'
phase: 1.5b
milestone: Adoption
status: todo
depends_on: [081, 097, 036, 099]
---

## Why this exists

[081](081_routing-prompts-are-not-in-the-agents-surface.md) settled the finding this ticket extends:
a client exposes only **tools** to the model, never prompts — `TOOLS.md` states it as decided,
*"an agent's client exposes only the tools above to the model, so a model never sees a prompt"*.

`which_tool` is an MCP prompt. It is also the only artifact in this repo that maps a
natural-language question onto a tool **across all 24 tools** — written for a model, living in the
one channel a model cannot read. 081's answer was to move routing into the tool descriptions
themselves (069), which is correct and is where routing belongs. What 081 did **not** do is give the
map a channel of its own, because at the time none existed that did not mean wiring code-atlas into
somebody's editor.

One exists now and it does not cross that line. An **Agent Skill** is a file a *user* installs into
their own agent; it loads on demand when the agent recognises a matching task, costs nothing in a
session that never triggers it, and is read by any agent supporting the format. code-atlas emits a
file; the host decides. That is the same posture the hooks already take — *"code-atlas does not wire
itself into anyone's editor"* (`TOOLS.md`, 036/099) — and this ticket does not change it.

**The second defect is rot in the one channel that does reach a model.**
`contrib/claude-code/settings.snippet.json` filters on `"if": "Edit(*.php)|Write(*.php)"`. That was
right at [036](036_edit-index-hook.md), when PHP was the only adapter. Adapter #2 (TS/JS, 019) and
adapter #3 (T-SQL, 184 + 022) have landed since, and `adapter.shipped_adapters()` now returns three
directories: **a TypeScript edit drifts the index and nothing pokes it.** The same file is also the
only snippet in `contrib/` — a Codex or OpenCode user is offered nothing, though both have a
documented session-hook surface.

Neither defect is a payload defect, so none of the Agent-trust work reaches either. Both are
**recognition** defects — and recognition is the one thing this repo already knows how to measure:
[097](097_recognition-probe-measures-names-not-recall.md) taught the blind probe to separate a
name-only answer from a description-backed one, so it can score whether any of this moved anything.

## Scope

1. A generated `SKILL.md` — the `which_tool` map plus the tool table — emitted from the **same
   source those already come from**, so the skill cannot describe a surface the server does not
   serve. Drift guarded by a test, in the shape `test_documented_tool_count.py` already uses.
2. The Claude Code poke snippet covers **every shipped adapter**, not a filter frozen at 036.
   `adapter.shipped_adapters()` is the static list and `adapter.py`'s handshake is the suffix
   source; the snippet is checked against one of them, never re-typed beside them.
3. Session-hook snippets for **Codex** (`hooks.json`, `[features].hooks = true`) and **OpenCode**
   (managed plugin) beside the Claude Code one, carrying the same `code-atlas-poke` /
   `code-atlas-signal` commands. Snippets and a README — offered, never installed.
4. A blind recognition-probe round before and after.

### Explicitly not in scope

- **An installer, a `setup` command, or anything that writes to a user's agent settings.** 036 and
  099 both settled this and `TOOLS.md` states it. The external principle this ticket borrows asks
  for a setup command; this repo's answer is stricter and stays stricter.
- **Rewriting tool descriptions.** That is 069's surface and routing lives there. The skill carries
  the map, not a second set of descriptions that can disagree with the first.
- **Output format.** TOON, exit codes and a shell surface are a separate question with a separate
  gate; nothing here changes a payload byte.
- **Publishing the skill anywhere.** Generating and committing it is this ticket; distribution is a
  maintainer decision taken after the probe reports.

## Constraints

- **No core change.** `code_atlas/` gains nothing: the generator is a script plus a test, the
  snippets are `contrib/`. R1.1, R1.4 and R4.1 are untouched by construction — and the diff must
  show it.
- **Single source, or it rots exactly as 036's filter did.** A hand-kept skill is the defect this
  ticket is fixing, one file over. Derive it or check it; never re-type it.
- **The skill is static.** No live state — index freshness, symbol counts, open work — may appear in
  it. That is the hooks' job, and a stale number in a committed file is a wrong answer, not a stale one.
- **R7.6, and the room is already gone.** `BACKLOG.md` is at 8,134 tokens against 8,200 and
  `CONVENTION.md` sits exactly on 6,600. This ticket's backlog row fits; any prose it wants in a
  standing doc does not, and must prune first or argue a raise in the PR.

## Acceptance criteria

1. `SKILL.md` is generated, and the drift test goes **red when either side is mutated** — proven by
   mutating each, not asserted.
2. A shipped adapter with no coverage in the poke snippet fails a test. Proven by adding a fourth
   adapter directory in a fixture and seeing it red, so the 036 rot cannot recur silently.
3. Codex and OpenCode snippets exist, each naming the file it belongs in, each installable by hand
   from the README, and no code-atlas command writes to any of them.
4. `code_atlas/` is byte-unchanged; R4.1's grep-gate is still green.
5. A blind probe round is recorded **before and after**, per
   [`runbooks/tool-recognition-probe.md`](../runbooks/tool-recognition-probe.md) and 097's
   name-only / description-backed split. **A round that does not move is a result, not a failed run
   to be repeated** — if the skill changes no score, this ticket says so in writing and the skill is
   reconsidered rather than kept for its own sake.
6. Nothing in `contrib/` claims a language this repo cannot index.

## References

[081](081_routing-prompts-are-not-in-the-agents-surface.md) (prompts are not in the agent's
surface), [097](097_recognition-probe-measures-names-not-recall.md) (the probe that can score this),
[036](036_edit-index-hook.md) (the snippet, and the never-installed stance),
[099](099_write-time-signal-seam.md) (the read-time signal, and the field evidence that the
decisions that most needed code-atlas wanted one line and no tool call),
[159](159_get-index-status-does-not-name-available-but-unconfigured-adapters.md) (the Adoption
theme, and `adapter.shipped_adapters()`).
External: principle 7 of the AXI skill, [kunchenguid/axi](https://github.com/kunchenguid/axi) — the
source of the skill-plus-hook shape, taken here without its installer.
