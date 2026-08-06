# Running code-atlas under parallel agents (worktree fan-out)

Guidance for dispatching many background agents at once — e.g. one `claude --bg` per ticket, each in
its own git worktree — with code-atlas as an MCP server. Background for **why** this matters:
[`FEEDBACK.md`](../FEEDBACK.md) Round 4 (a resident-LSP MCP-server fan-out that OOM'd a large private monorepo).

## The short version

code-atlas does **not** reproduce that OOM: it keeps no resident language server, queries an on-disk
SQLite index per call, and its adapters are transient (one file per request, reaped when a build
ends). So `N` agents cost `N ×` a lightweight Python process, not `N ×` a multi-GB LSP. The only real
cost knob is **concurrent builds**, not steady-state querying.

## Do this

- **Prefer a pre-built, per-worktree index.** `db_path` is resolved relative to the agent's `cwd`
  (`code_atlas/config.py:117`), so each worktree reads its **own** `.code-atlas/graph.db` — correct
  for a worktree agent's edits. Build it before the fan-out (or let read-through freshness repair
  drift inline; it is capped at one reparse per call).
- **Cap `CA_WORKERS` when many agents build at once.** Each build fans out up to `workers` PHP
  processes (default `max(1, min(cpu-2, 8))`, `config.py:176-178`). `N` agents each building →
  `N × workers` short-lived PHP processes and CPU oversubscription. Set `CA_WORKERS=1` or `2` for a
  fan-out, or stagger the builds. This burst is transient (adapters are killed at build end,
  `adapter.py:349-367`), never a resident leak.
- **Don't have every agent build the *same* DB path concurrently.** Writes serialise on one DB (WAL
  single-writer, `busy_timeout=5000`, `store.py:49`); heavy concurrent builds on a shared path hit
  5 s lock waits. Per-worktree indexes avoid this entirely; a single shared index built **once** and
  then queried read-only is also fine (reads don't block under WAL).
- **Apply MCP-config hygiene for tidiness.** `claude --bg` inherits the parent's MCP config, so each
  agent starts its own code-atlas core. Here that is megabytes, not an OOM — but if a background
  agent needs no MCP at all, dispatch it with an empty config and `--strict-mcp-config` (mind the
  variadic-flag order: `--mcp-config <file> --strict-mcp-config "<prompt>"`, never `--mcp-config`
  last — it eats the prompt). See [`FEEDBACK.md`](../FEEDBACK.md) Round 4 for the full recipe.

## Don't worry about

- **Steady-state query memory.** Query tools open and close the store per call
  (`code_atlas/tools/find_callers.py:67`); nothing holds the graph in RAM.
- **Lingering processes.** There is no resident server to leak; the poke hook (task 036) is a
  short-lived process that exits.
