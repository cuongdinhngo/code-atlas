# Claude Code hooks — index poke, read/write signal, session state (tasks 036, 099, 240, 322)

Three commands, for the moments an agent was never going to make a tool call.

- **`code-atlas-poke`** (036) — after Claude Code `Edit`/`Write` on a file an adapter owns,
  reparse that one file into `.code-atlas/graph.db` using `code_atlas.indexer.reparse_file`
  (same write path as a full/incremental build). Complements query-time read-through
  freshness (035): the index is often already fresh before the next tool call.
- **`code-atlas-signal`** (099) — one line (~150 tokens, hard cap) riding along with a file
  the agent is already opening. The field found three consequential decisions that wanted
  exactly that and **none** that wanted a round-trip. Wired at **`Read`/PostToolUse** (the
  line rides the result) and **`Write`/PreToolUse** — the create-vs-edit test is whether the
  path exists yet, so a `PostToolUse` `Write` is silent by construction.

  It shipped in 2026-08 wired for Codex only; **240** is the drift that left the host every
  field round runs on without it, and the guard that now keeps the two offers in step.
- **`code-atlas-state`** (322) — restates `get_index_status`'s `summary` at **`SessionStart`**
  and **`PreCompact`**, because the `initialize` copy decays in a long or compacted session.
  Silent when the index is current and no build runs; ≤ 90 tokens; always exits 0
  ([TOOLS.md](../../docs/TOOLS.md#the-session-boundary-state-line--the-index-state-restated-when-the-first-copy-decayed-opt-in)).

## Install as a plugin (344) — the server, these hooks and the skill, for every project

1. Put the console scripts on `PATH`: `uv tool install git+https://github.com/cuongdinhngo/code-atlas.git`
   (or `pipx install …`). The plugin names them, and a venv's scripts are not on `PATH`.
2. `claude plugin marketplace add cuongdinhngo/code-atlas`, then
   `claude plugin install code-atlas@code-atlas` (or `/plugin` inside a session).

[`plugin/`](plugin/) is generated from the same table as the snippet below, and each command is gated
on `${CLAUDE_PROJECT_DIR}/.code-atlas`, so a repo with no index pays one shell test (~1.5 ms) and
spawns no Python. A fourth hook, `code-atlas-refresh`, runs in the background at `SessionStart`.
Coming from a hand install? Remove the merged snippet and any `claude mcp add` entry first.

## Install by hand

1. Install code-atlas into the environment Claude Code uses (`pip install -e /path/to/code-atlas`
   or your usual setup from the [README](../../README.md)). This provides the
   **`code-atlas-poke`**, **`code-atlas-signal`** and **`code-atlas-state`** console scripts on `PATH` (same
   interpreter as the install).
2. Merge [`settings.snippet.json`](settings.snippet.json) into the **project**
   `.claude/settings.json` (shareable) **or** `~/.claude/settings.json` (user-global). Keep
   `"async": true` on the poke so it does not stall the Edit/Write round-trip; the signal is
   synchronous by design, because its line has to reach the result it rides on. Every `"if"`
   filter is **generated** from each shipped adapter's own declared suffixes — never widened
   by hand.
3. Restart Claude Code (or reload hooks) so the settings take effect.

No `CODE_ATLAS_ROOT` export is required — the console script is the stable entrypoint.

## Behaviour

| Situation | Result |
|-----------|--------|
| No `.code-atlas/graph.db` under `$CLAUDE_PROJECT_DIR` / cwd | Exit 0; verbose: `skipped: no index` |
| Index present; path under the project; content drifted | Background `reparse_file`; verbose: `poked <rel>` |
| Content already matches the index | Exit 0; verbose: `skipped: current` (no adapter call) |
| Path outside the project / bad JSON | Exit 0; no-op |
| No adapter owns the suffix | Exit 0; verbose: `skipped: no adapter owns …` |
| Install/config error (import, `ConfigError`, …) | Exit 0; **always** one stderr line `code-atlas poke skipped: …` |

## Verify

```bash
export CLAUDE_PROJECT_DIR=/abs/path/to/your-project
echo '{"tool_name":"Edit","tool_input":{"file_path":"'"$CLAUDE_PROJECT_DIR"'/src/Example.php"}}' \
  | code-atlas-poke --verbose
```

Expect `code-atlas poke: poked src/Example.php` (or `skipped: …` with a clear reason) on stderr.
On a broken install you should see `code-atlas poke skipped: …` even without `--verbose`.

## Regenerate

```bash
python scripts/gen_skill.py --write
```

The `"if"` filter is derived from each shipped adapter's entry-file declaration, so an adapter that
ships without coverage is a red test (`tests/test_poke_snippet_covers_every_adapter.py`), not a
silent gap — which is how this filter stayed PHP-only across two adapter launches (task 200).
