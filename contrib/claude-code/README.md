# Claude Code Edit/Write index poke (task 036)

After Claude Code `Edit`/`Write` on a PHP file, reparse that one file into
`.code-atlas/graph.db` using `code_atlas.indexer.reparse_file` (same write path as a
full/incremental build). Complements query-time read-through freshness (task 035): the
index is often already fresh before the next tool call.

## Install

1. Install code-atlas into the environment Claude Code uses (`pip install -e /path/to/code-atlas`
   or your usual setup from the [README](../../README.md)). This provides the
   **`code-atlas-poke`** console script on `PATH` (same interpreter as the install).
2. Merge [`settings.snippet.json`](settings.snippet.json) into the **project**
   `.claude/settings.json` (shareable) **or** `~/.claude/settings.json` (user-global). Keep
   `"async": true` so the poke does not stall the Edit/Write round-trip. The `"if"` filter
   limits the hook to `*.php` while PHP is the only adapter — widen it when more adapters ship.
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
