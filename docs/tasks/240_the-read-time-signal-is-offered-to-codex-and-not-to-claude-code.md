---
id: 240
slug: the-read-time-signal-is-offered-to-codex-and-not-to-claude-code
title: '`code-atlas-signal` is wired in `contrib/codex/hooks.json` and absent from `contrib/claude-code/settings.snippet.json`, so the one signal the field asked for has never fired on the host every field round runs — and the Codex README asserts the Claude Code snippet already uses it'
phase: 1.5b
milestone: Adoption
status: in-progress
depends_on: [099, 036, 200]
---

## Why this exists (field corpus — rounds 5-16, anchor-repo)

**099 built exactly what the field asked for, and the field has never seen it.**

The round-5 field interview is the sharpest document in the corpus. Its §1 inventories the three most
consequential decisions the agent made *without* calling code-atlas, and reaches an unexpected
convergence, stated in the file as the finding:

> All three moments want the **same delivery channel — a file read I was already performing** — and
> **none of them wants a tool call.**

§3 priced it: one line, `~150 tokens`, at the `Read` that opens the file; *"past ~500 attached to a
Read result I would learn to treat it as chrome"*. §8.4 ranked it second of six asks.

Task 099 shipped that, faithfully — `read_signal` + `write_signal`, `TOKEN_BUDGET = 150`,
`MIN_SYMBOLS = 5`, the silence rule, the Read/PostToolUse + Write/PreToolUse split documented in
[`docs/TOOLS.md`](../TOOLS.md). **Then it was wired for one host and not the other.**

| Host | `code-atlas-poke` | `code-atlas-signal` |
|---|---|---|
| `contrib/codex/hooks.json` | ✅ | ✅ |
| `contrib/claude-code/settings.snippet.json` | ✅ | **absent** |

**Every field round runs in Claude Code.** So the signal has fired zero times in the entire corpus,
and rounds 14, 15 and 16 do not mention it. `docs/runbooks/field-retro.md:48` already carries the
symptom as a permanent affordance — *"If the host wired `code-atlas-signal`, record for each round —
otherwise write `not wired`"*.

**And the repo states the opposite is true.** `contrib/codex/README.md:3`, verbatim:

> Two commands the Claude Code snippet already uses, offered to Codex

That sentence is false today. It is the reason the gap survived: the offer was believed to exist.

## Root cause

`scripts/gen_skill.py:133` `render_poke_snippet()` is named, scoped and documented as the *poke*
snippet — *"The Claude Code Edit/Write poke hook"*. 099 added a second hook command and a second
host file, and did not widen the generator that owns the first host's file. Nothing failed, because
no guard compares one host's offer against another's: `tests/test_contrib_snippets.py` checks that
every command a snippet **calls** is declared in `pyproject.toml` (the reverse direction), and
`tests/test_poke_snippet_covers_every_adapter.py` checks suffix coverage **within** the poke hook.

This is task 200's lesson recurring one level up. 200 found the poke filter *"stayed PHP-only across
two adapter launches"* and built a generated filter plus a guard. The same drift then happened to the
*command set* rather than the suffix set, in the same file, with no guard on that axis.

## Scope

- **Widen the generator to render the whole Claude Code hook offer**, not only the poke hook:
  `code-atlas-signal` at `PostToolUse`/`Read` and at `PreToolUse`/`Write`, per `docs/TOOLS.md`'s
  stated wiring (*"the create-vs-edit test is whether the path exists yet, so a `PostToolUse` `Write`
  is silent by construction"*). One command, two events — `signal()` dispatches on `tool_name`.
- **Filter both signal hooks by the same generated adapter-suffix set the poke hook uses**, so a
  `Read` of a file no adapter owns does not spawn a process. One source of truth, already tested.
- **Regenerate `contrib/claude-code/settings.snippet.json`** from the generator, never by hand.
- **Update `contrib/claude-code/README.md`** — it is titled and written for 036 alone.
- **Proving test: a hook command offered to one host is offered to every host that can run it.**
  This is the guard whose absence is the root cause, and it is the axis no existing test covers.

### Explicitly not in scope

- **Installing anything.** 036 and 099 both settled the stance and `docs/TOOLS.md` states it:
  *"code-atlas does not wire itself into anyone's editor … the command is offered and the host
  decides."* `tests/test_contrib_snippets.py::test_no_code_atlas_command_writes_to_any_install_target`
  enforces it. This ticket fixes **what is offered**, not **who installs it**.
- **`scripts/setup.py` mentioning the hooks**, and **`get_index_status` naming unwired hook surfaces
  the way it names `unconfigured_adapters`** (7-I, standing since round 7). Both are real and both
  are follow-ups — the second carries an envelope-cost decision (223) that deserves its own gate.
- **Changing `code-atlas-signal`'s behaviour, budget or silence rule.** 099 is not reopened.

## Constraints

- **R2, standard over sample** — the wiring encodes each host's documented hook contract and the
  adapters' own declared suffixes; no anchor-repo name appears in a snippet.
- **R4.2, deterministic** — `gen_skill.py --write` is idempotent; the committed file equals the
  rendered one, which `scripts/gate.sh` already checks.
- **200's stance, unchanged** — code-atlas emits a file; the host installs it. No new write path.
- **061 / R7.1** — no tool payload changes; this ticket touches `contrib/`, `scripts/gen_skill.py`
  and `tests/` only.

## Acceptance criteria

1. `contrib/claude-code/settings.snippet.json` wires `code-atlas-signal` at `PostToolUse`/`Read` and
   at `PreToolUse`/`Write`, alongside the unchanged `code-atlas-poke` hook.
2. The file is rendered by `scripts/gen_skill.py`; `--write` is idempotent and the committed file
   matches.
3. A proving test fails when a hook command offered to one host is missing from another host's
   offer, and is observed failing (R6.5) before it passes.
4. `tests/test_poke_snippet_covers_every_adapter.py` still passes, selecting the poke hook **by
   command name** rather than by list position — adding a second hook must not make suffix coverage
   depend on ordering.
5. `contrib/codex/README.md`'s claim that the Claude Code snippet already uses both commands becomes
   true; `contrib/claude-code/README.md` describes both hooks and their two events.
6. `GATE GREEN` (R6.5) — exit 2 is not a pass.

## References

Field corpus (local, maintainer-only — R-7): round-5 field interview §1, §3, §8.4(2); rounds 14-16
(no mention of the signal); `docs/runbooks/field-retro.md:48`. In-repo: `code_atlas/hooks/signal.py`
(099), `scripts/gen_skill.py:133`, `contrib/claude-code/`, `contrib/codex/`,
[`docs/TOOLS.md`](../TOOLS.md) "Hooks (opt-in)".
Lineage: [099](099_write-time-signal-seam.md) built the signal,
[200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md) generated the poke filter after the
same file drifted on a different axis — **this ticket is that drift's second axis, and the guard 200
did not write.**
