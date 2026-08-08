# Git post-merge / post-checkout index refresh (task 053)

After `git pull` / `git merge` / a **branch** checkout, run an incremental
`build_or_update_index(full=false)` against `.code-atlas/graph.db` when the index
already exists. Complements the Claude Code Edit/Write poke
([`contrib/claude-code/`](../claude-code/)) and query-time read-through freshness
(task 035): changes that never pass through the agent's editor still reach the
index without waiting for someone to call the MCP build tool.

These hooks are **not installed automatically**. `.git/hooks` is not
version-controlled, and this project never writes into a user's `.git` for them.

## Install

1. Install code-atlas so **`code-atlas-refresh`** is on `PATH` (same interpreter as
   the MCP server — see the [README](../../README.md)).
2. Copy the hook scripts into the repo's `.git/hooks/` (names must match exactly):

   ```bash
   cp contrib/git/post-merge contrib/git/post-checkout /path/to/repo/.git/hooks/
   chmod +x /path/to/repo/.git/hooks/post-merge /path/to/repo/.git/hooks/post-checkout
   ```

3. Confirm with a pull or branch switch; with `CA_REFRESH_VERBOSE=1` on PATH's
   environment you should see `code-atlas refresh: refreshed` (or `skipped: …`)
   on stderr from a foreground run of `code-atlas-refresh --verbose`.

## Behaviour

| Situation | Result |
|-----------|--------|
| No `.code-atlas/graph.db` under cwd / `$CLAUDE_PROJECT_DIR` | Exit 0; verbose: `skipped: no index` (never full-builds) |
| Index present | Background incremental; verbose: `refreshed` |
| Another refresh holds `.code-atlas/refresh.lock` | Exit 0; verbose: `skipped: another refresh is running` |
| `post-checkout` with git's 3rd arg ≠ `1` (file checkout) | Hook exits 0 immediately; no refresh |
| Install/config error | Exit 0; **always** one stderr line `code-atlas refresh skipped: …` |

**Why background?** A no-op / small incremental on a large index can cost on the
order of a minute (task 052). A hook that blocks `git pull` for that long gets
deleted. The scripts spawn `code-atlas-refresh` and return 0 immediately.

**Why a lock file?** R4.3 — one SQLite writer. Two overlapping hooks (or a hook
racing the MCP server's build) must not both write. The second process skips
cleanly instead of partially updating the graph.
