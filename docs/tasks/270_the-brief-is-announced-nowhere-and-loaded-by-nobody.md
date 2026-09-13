---
id: 270
slug: the-brief-is-announced-nowhere-and-loaded-by-nobody
title: 'The five-occasion brief 266 shipped is named in no document a user reads — not README, not the onboarding runbook, not setup''s closing line — and on Claude Code it is loaded by nothing: the hardcoded memory list is `CLAUDE.md` / `CLAUDE.local.md`, and `AGENTS.md` is not in it, so the artifact that fixes recognition repeats 266''s own failure one level down'
phase: 1.5b
milestone: Adoption
status: todo
depends_on: [266, 200, 240, 244]
---

## Why this exists

[266](266_the-artifact-that-would-make-an-agent-ask-is-in-our-repo-not-theirs.md) moved the brief out of
`contrib/skill/` — *"a place no agent working in a consumer repo ever reads"* — and into the indexed
tree. The move was right. **Two links in the chain were left unbuilt, and each reproduces the defect
266 was written to remove.**

**1. No channel announces it.** Grep for `write-agent-brief` / `agent brief` across `README.md`,
`docs/**` and `contrib/**`, excluding `docs/tasks/`: **four hits, none of them a place a user looks** —
`PLAN.md:976` (the §19 decision), `TOOLS.md:241` (`CA_PROJECT_FILES`, unrelated), `TOKEN_LEDGER.md:27`
(the spend row) and `contrib/agent-brief.md:5` (the generated artifact naming its own regeneration
command). **Zero hits in `README.md`**, **zero in `docs/runbooks/`**, **zero in
`contrib/claude-code/README.md`**. README's Quick start ends at *"call `get_index_status` →
`build_or_update_index`"* — the exact line where the brief should be offered. `scripts/setup.py`
carries the `--write-agent-brief` flag but its closing `Done.` never mentions it, so the one screen
every installer reads stays silent. The maintainer learned the feature existed by asking, 2026-09-13
— not from any document.

**2. On Claude Code, `AGENTS.md` is loaded by nothing.** The hardcoded project-memory list in the
shipped binary (`claude 2.1.270`) is `["CLAUDE.md","CLAUDE.local.md"]`; `"AGENTS.md"` occurs in that
binary only inside the Codex-import path. This repo never noticed because its own `CLAUDE.md` carries
an `@AGENTS.md` import — a consumer repo has no reason to. **Field instance, 2026-09-13, `anchor-repo`:**
the brief was written correctly, the repo's 15 KB `CLAUDE.md` had no import, and the brief was inert
until a `CLAUDE.local.md` holding `@AGENTS.md` was added by hand. This is [240](240_the-read-time-signal-is-offered-to-codex-and-not-to-claude-code.md)'s
class — an offer shipped for a host that is not the one the field rounds run on.

Both defects are docs-and-offer shaped. Neither needs a measurement first, and neither changes a tool.

## Scope / Deliverables

- **README, after Quick start:** a short subsection — what the brief is (five occasions, not 24
  descriptions), the command, and **the load requirement per host** (Claude Code reads `CLAUDE.md` /
  `CLAUDE.local.md`; Cursor reads `AGENTS.md` directly).
- **`scripts/setup.py` closing line names the flag** when a PROJECT was given and the flag was not —
  the one screen an installer reads.
- **`docs/runbooks/onboarding-a-repo.md`:** the brief becomes a step in the onboard sequence, next to
  the hook offer.
- **Make the brief reachable on Claude Code — offered, never installed.** `write_agent_brief` detects
  a `CLAUDE.md` in the target that lacks an `@AGENTS.md` import and **prints the one line to add**. It
  writes nothing to `CLAUDE.md`.
- **Record the boundary in PLAN §19 before any code.** 266's entry authorises writing `AGENTS.md`
  into the indexed tree. Appending an import line to a repo's **existing, team-committed** `CLAUDE.md`
  is a different act with a different blast radius — the same reason 266 needed its own entry against
  [036](036_edit-index-hook.md)/[099](099_write-time-signal-seam.md). Decide it first; this ticket's
  recommendation is **print, never write**.

## Constraints

- No 25th tool, no new env knob, no editor settings (036/099 unchanged).
- The brief's body stays generated from `which_tool` (R6.7) — the new README text must not become a
  second hand-kept copy of the occasions or the tool list.
- R7.6: the README subsection removes what it supersedes; `tests/test_doc_size_budget.py` stays green.

## Acceptance criteria

- A test asserts `--write-agent-brief` appears in `README.md` **and** in
  `docs/runbooks/onboarding-a-repo.md`, and that the README text names no tool the generator does not
  (R6.7 drift guard extended).
- `scripts/setup.py PROJECT` without the flag prints the offer line; a test pins it.
- `write_agent_brief` against a fixture repo whose `CLAUDE.md` lacks `@AGENTS.md` returns/prints the
  import line and leaves `CLAUDE.md` byte-identical; with the import present it says nothing. Both
  arms tested.
- PLAN §19 carries the `CLAUDE.md`-import boundary decision, committed **before** the code change.
- Docs budget and `tests/test_agent_brief_in_indexed_repo.py` stay green.

## References
`README.md` §Quick start, `scripts/setup.py:121,178`, `scripts/gen_skill.py:269`,
`docs/runbooks/onboarding-a-repo.md`, `contrib/claude-code/README.md`,
[266](266_the-artifact-that-would-make-an-agent-ask-is-in-our-repo-not-theirs.md),
[240](240_the-read-time-signal-is-offered-to-codex-and-not-to-claude-code.md),
[200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md),
[244](244_no-channel-announces-a-capability-change.md), PLAN §19 (266 entry, `PLAN.md:976`).
