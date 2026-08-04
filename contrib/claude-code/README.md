# Claude Code Edit/Write index poke (task 036)

After Claude Code `Edit`/`Write`, reparse that one file into `.code-atlas/graph.db` using
`code_atlas.indexer.reparse_file` (same write path as a full/incremental build). Complements
query-time read-through freshness (task 035): the index is often already fresh before the next
tool call.

## Install

1. Have code-atlas installed in the environment Claude Code uses (`pip install -e /path/to/code-atlas`
   or your usual setup from the [README](../../README.md)).
2. Export the checkout root once per shell (or put it in the project env Claude Code inherits):

   ```bash
   export CODE_ATLAS_ROOT=/abs/path/to/code-atlas
   ```

3. Merge [`settings.snippet.json`](settings.snippet.json) into the **project**
   `.claude/settings.json` (shareable) **or** `~/.claude/settings.json` (user-global). Keep
   `"async": true` so the poke does not stall the Edit/Write round-trip.
4. Restart Claude Code (or reload hooks) so the settings take effect.

The hook command must be able to import `code_atlas`. Prefer the same interpreter you use for the
MCP server (replace `python3` with that interpreter’s absolute path if needed).

## Behaviour

| Situation | Result |
|-----------|--------|
| No `.code-atlas/graph.db` under `$CLAUDE_PROJECT_DIR` / cwd | Exit 0; does nothing (never builds) |
| Index present; path under the project | Background `reparse_file` for that relative path |
| Path outside the project / bad JSON | Exit 0; no-op |

Manual check (same script Claude Code runs):

```bash
export CLAUDE_PROJECT_DIR=/abs/path/to/your-project
echo '{"tool_name":"Edit","tool_input":{"file_path":"'"$CLAUDE_PROJECT_DIR"'/src/Example.php"}}' \
  | python3 "$CODE_ATLAS_ROOT/scripts/claude_code_poke_index.py"
```
