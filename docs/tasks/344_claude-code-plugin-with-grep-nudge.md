---
id: 344
slug: claude-code-plugin-with-grep-nudge
title: 'Ship code-atlas as a Claude Code plugin — server, hooks and skill in one install, plus the grep-time nudge'
phase: 2
milestone: Adoption
status: todo
depends_on: [036, 099, 200, 322, 343]
---

## Why this exists

Every channel code-atlas controls reaches the model **before** or **after** the decision that
matters, never *at* it:

| Channel | When it speaks | Limit |
|---|---|---|
| Server `instructions` (300) | Session start | Capped and frozen (343) |
| Tool descriptions (069) | After a ToolSearch load | Claude Code delivers tools as deferred names, so the description is unseen until the model has already chosen the tool |
| Tool results | After a call | Silent when the agent never calls |
| Hooks `poke` / `signal` / `state` (036, 099, 322) | At the moment | **Offered, never installed**: `contrib/claude-code/settings.snippet.json` has to be merged by hand in each repo |

So in any repo where nobody read `contrib/`, the only channels in play are the first three, and the
grep decision happens unobserved.

## Evidence (anchor repo, 2026-09-29)

- **A concrete procedure step beats a general rule.** The anchor repo's CLAUDE.md routed symbol
  questions to code-atlas, and its SessionStart hooks restated it. Even so, sessions running a project
  skill answered caller questions with Grep, because the skill's own step said
  `grep -rn "methodName("`. The fix there was to rewrite six skills by hand. A new anchor project
  won't know it needs to.
- **The one channel that fired at the decision was project-local.** The anchor repo wrote its own
  PostToolUse(`Bash|Grep`) hook, `.claude/hooks/code-atlas-symbol-nudge.sh`. It spots a grep for a
  symbol (`function x`, `->x(`, `::x(`, `class X`, or a proc/table name over `*.sql`), or a sed/awk
  slice of a body by line range, and injects one "ask code-atlas first, keep Grep as the cross-check"
  line. It is rate-limited to once per kind per 15 minutes and silent without an index or a
  registration. None of that exists upstream. Its SessionStart companion,
  `code-atlas-session-refresh.sh`, starts a background incremental refresh on a `behind` index, which
  `code-atlas-state` does not.
- Registration is still a hand-typed `claude mcp add-json` with an absolute interpreter path. A
  backslashed path fails as `Invalid configuration: : Invalid input` (anchor
  `CODE_ATLAS_SETUP.md` §3).

## Scope

1. **Plugin manifest in this repo:** `.claude-plugin/plugin.json` plus a `marketplace.json`, so
   `/plugin marketplace add <repo>` → `/plugin install code-atlas` covers every project for that user.
   It bundles:
   - **`mcpServers`**, launching the `code-atlas` console script, which replaces `claude mcp add-json`;
   - **hooks**: `code-atlas-state` (SessionStart, PreCompact), `code-atlas-poke` (PostToolUse
     Edit/Write, async), `code-atlas-signal` (PostToolUse Read, PreToolUse Write), and the new nudge;
   - **skill**: the generated `contrib/skill/SKILL.md`, which holds the full recognition map that 343
     takes out of `instructions`.

   This keeps the 036/099 rule: code-atlas writes to no settings file. The user's one install is
   the opt-in.
2. **`code-atlas-nudge` console script**, the upstream of the anchor hook, made language-neutral.
   - The symbol patterns come from each adapter's declared suffixes and declaration keywords,
     generated the way the poke `if` filter is (200), never widened by hand.
   - Rate-limited per kind per session. It never blocks, always exits 0, and stays silent with no
     index.
   - It keeps the anchor's deliberate exemption: a proc name grepped inside host-language source is a
     string literal, so Grep is the right first tool there.
3. **`code-atlas-state --refresh`**: optionally starts the background incremental refresh on a
   `behind` index, as the anchor's session-refresh hook does. It skips with one line when an
   adapter command is unset (the `coverage_loss_pending` case).
4. **Every hook gates itself on the repo.** A user-scope plugin fires in *every* project, so each
   command is a silent no-op when the cwd has no `.code-atlas/`, and costs no process spawn beyond a
   pre-filter.

## Acceptance criteria

- **AC1:** On a clean machine with code-atlas installed via pip, `/plugin install` alone gives a
  connected server and all five hooks. There is no `claude mcp add-json` and no settings merge. This
  is verified on a running Claude Code (not from docs, per 200's A-4 discipline).
- **AC2:** In a repo with no index, no hook prints anything and each exits 0 in under 50 ms. A test
  covers each command.
- **AC3:** Replaying the anchor's grep shapes (PHP method, SQL proc) fires the nudge once, and a second
  replay within the window stays silent. A literal-text grep (a config key, a comment) never fires.
- **AC4:** A drift test, in the manner of `test_poke_snippet_covers_every_adapter.py`, fails when an
  adapter ships without nudge patterns.
- **AC5:** A project that already wires the anchor's local hooks gets one nudge per event, not two.
  Either the plugin's nudge detects that and stands down, or the anchor retires its hook, and the
  README says which.

## Open questions

- **Adapters.** The plugin cache holds a clone, but the PHP and TS/SQL adapters need a Composer or npm
  install, and `CA_<LANG>_CMD` is still per-machine. Decide whether the plugin defaults `CA_*_CMD` to
  `${CLAUDE_PLUGIN_ROOT}/adapters/...` with a first-run install step, or stays server-and-hooks only
  and leaves adapters to the README.

## Out of scope — follow-up

- **`code-atlas init`**, for what has to live *in* the repo for a team: a `.code-atlas.toml`
  skeleton, a marker-fenced routing block in CLAUDE.md/AGENTS.md, and git hooks. The plugin is per
  user; `init` is per repo. Ticket it once this lands, and only if a second anchor project asks.
