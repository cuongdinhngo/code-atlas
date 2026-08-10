# Running code-atlas under parallel agents (worktree fan-out)

Guidance for dispatching many background agents at once — e.g. one `claude --bg` per ticket, each in
its own git worktree — with code-atlas as an MCP server. Background for **why** this matters:
[`FEEDBACK.md`](../FEEDBACK.md) Round 4 (a resident-LSP MCP-server fan-out that OOM'd a large private
monorepo).

**Every number below is measured**, on the anchor monorepo (18.9k files, 925 MB index, 185.9k nodes,
1.78M edges) on a 16-core / 27.8 GB Linux host, commit `869dcc6`. An earlier version of this runbook
was written from code reading and got its most important claim backwards; see *Corrected* below.

## The short version

Memory is not the constraint, and it is not close. The **n-th concurrent agent costs ~70 MB PSS**, of
which the index is **0 MB**: `graph.db` is never mmapped and no descriptor outlives a call, so the file
is resident **once**, in the OS page cache (93.7 % of it), shared by every process and reclaimable.
Five agents running 4,500 tool calls cost **355 MB PSS total** — 1.3 % of RAM — and returned **4.3×**
the single-agent throughput at 15.7 % higher per-agent wall time.

**The constraint is correctness, not cost.** Read the worktree section before dispatching anything.

## Corrected (2026-08-09): worktree agents get the *main* repo's index

This runbook previously said `db_path` is `cwd`-relative, so each worktree reads its own index. The
config statement is true and the operational conclusion was **false**: the registration that
`/parallel-tasks`-style dispatchers generate bakes `cd <main repo>` into the server command, so the
server's cwd is the main checkout no matter where the client runs.

Proven with a two-marker probe — a uniquely named method injected into the *same file* in both trees:
the worktree agent asked `file_outline` about **its own path** and was handed the **main checkout's**
symbol, while its own symbol was reported absent. The payload said `reason: "ok"`. Since task 061
removed `db_path` from nav payloads, **no field in any read tool named the tree** until
([071](../tasks/071_answers-do-not-name-their-tree.md)) landed `index_root`.

This is the same defect the resident-LSP server had (it hardcoded `--project <main repo>`). code-atlas
does not avoid it — it reproduces it identically. For that tool the memory verdict was "switch it off",
which masked the routing bug; here the memory verdict is "keep it on", so the routing bug is the whole
finding.

**Pick one, deliberately:**

| Option | What the agent gets | Cost |
|---|---|---|
| **Isolate (recommended)** — `CA_DB_PATH` per worktree, built once before dispatch | correct answers about its own tree | one incremental build, ~83 s on the anchor repo |
| **Fail loud** — drop the `cd` so cwd decides | `indexed: false` / `reason: "not_indexed"`, every tool inert | zero; honest and useless |
| **Share main's index** — keep `cd <main>` and compare `index_root` | answers about `main`; mismatch is visible (071) | zero; only safe when the agent's diff is tiny |

**Recommended fan-out recipe:** set a distinct `CA_DB_PATH` (and matching `root` / working directory)
per worktree, run one `build_or_update_index` before dispatch, and leave the shared main index alone.
Task 071 makes option 3 legible — every read payload carries `index_root` — but it does **not** make
sharing correct. If you share anyway, compare `index_root` to the agent's cwd before trusting a hit.

## Do this

- **Refresh the index once, before dispatch — never from inside an agent.** Two concurrent
  `build_or_update_index` calls are mutually excluded correctly by `write.lock`; the loser returns
  `mode: "busy"`, `performed: false`. Since [072](../tasks/072_busy-build-hides-staleness.md) that
  refusal also carries the staleness of the index it would have read
  (`staleness`/`last_commit`/`head_commit`, the `get_index_status` vocabulary), so an agent whose plan
  is "refresh, then investigate" can now tell the refresh did **not** run instead of reading the
  0.0 s reply as done. The rule stands regardless: a busy refusal means *your* refresh did not happen,
  so refresh once before dispatch rather than relying on an in-agent call that may lose the race.
- **Cap `CA_WORKERS` when many agents build at once.** A build fans out up to `workers` PHP processes
  (default `max(1, min(cpu-2, 8))`, `config.py`); measured at 6 during one incremental build. `N`
  agents each building → `N × workers` short-lived PHP processes. Set `CA_WORKERS=1` or `2`, or
  stagger. This burst is transient, never a resident leak.
- **Keep the in-flight agent cap where your *other* shared resources put it.** RAM does not bind:
  extrapolating, ten agents cost ~700 MB PSS, under 3 % of this host. On the anchor repo the binding
  constraint is the shared database/PHP container, not code-atlas.
- **MCP-config hygiene.** `claude --bg` inherits the parent's MCP config. Mind the variadic-flag order:
  `--mcp-config <file> --strict-mcp-config "<prompt>"`, never `--mcp-config` last — it eats the prompt.
  Verify what the agents actually got by reading `/proc/<pid>/cwd` of the live servers, not the config
  file: configuration is an intention, `/proc` is what happened.

## Don't worry about

- **Steady-state query memory.** Tools open and close the store per call; nothing holds the graph in
  RAM. 20 repeated `find_callers` calls moved PSS by **+0.1 MB**, latency flat at ~3 ms. The three
  heaviest tools in the API (`find_orphans`, `reachable_from` depth 3, `impact` depth 3) together added
  **+6.2 MB**.
- **Write contention.** Three servers querying continuously while a writer rewrote two indexed files
  every 0.4 s: **452 drift events, zero `index_stale` soft-fails, zero `SQLITE_BUSY` reaching a
  caller.** The 5 s `busy_timeout` was never approached — the slowest contended call was 1.28 s. WAL
  peaked at 121 MB and checkpointed itself away completely, because no reader holds the DB open.
- **Lingering processes.** No resident server to leak. Finished background agents kept their server
  alive for ~1 hour before being reaped, then went cleanly — a delayed reap, not a leak. Killing an
  agent takes its server with it.

## Do worry about

- **A symbol you just wrote may be reported absent.** Read-through freshness repairs only the paths of
  rows a query already matched, so a *new* symbol matches nothing, triggers no reparse, and comes back
  `no_matches` ([073](../tasks/073_freshness-cannot-find-what-is-not-indexed.md)). During an edit-heavy
  fan-out this is every symbol the agent has added. Path-named tools (`file_outline`) do repair, so two
  tools can disagree about the same file.
