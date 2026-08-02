# code-atlas

**Local-first MCP server that indexes your codebase into a symbol graph for fast, token-efficient
search, navigation, and impact analysis.** Language-agnostic core with per-language adapters — PHP
first, then TypeScript/JavaScript, Python, C#/.NET.

> Status: **early development.** See [`docs/PLAN.md`](docs/PLAN.md)
> for the full design and milestones.

## Why

Native AI-coding tools + `grep` are weak at language-specific, name-resolved queries on large repos:
they read whole files, miss cross-file relationships, and burn tokens. code-atlas parses each language
with its **best** parser into a **SQLite symbol graph**, then serves symbol-level, resolved,
token-efficient tools over MCP.

- **Symbol-level, name-resolved** — "who calls this method?", "what implements this interface?", "read
  just this method", "blast radius of changing this file" — not grep-and-read-everything.
- **Language-agnostic core + per-language adapters** — each language uses the parser that actually
  understands it (PHP → nikic/php-parser, TS/JS → TypeScript Compiler API, Python → `ast`+jedi, C# →
  Roslyn), all speaking one versioned JSON contract.
- **Local-first & deterministic** — everything runs offline against a local SQLite index; no LLM or
  network in the core. Incremental updates via `git diff`.
- **Complements Serena** — code-atlas is the indexed search/impact layer; Serena stays for LSP nav/edit.

## How it works

```
MCP client ──stdio──▶ core (Python / FastMCP) ──JSONL contract──▶ language adapter (e.g. PHP sidecar)
                          │
                          ▼
                   SQLite  .code-atlas/graph.db   (nodes · edges · files · fts5 · meta)
```

The core is language-agnostic (no per-language branches). Adapters parse files and emit a common
`{nodes, edges}` vocabulary; the core stores them, resolves cross-file edges, and exposes MCP tools.

## Run it

The server speaks MCP over stdio. Point a client at the repo you want indexed — the working
directory *is* the repo, and every `CA_*` knob below is read from that client's environment.

```jsonc
// .mcp.json
{
  "mcpServers": {
    "code-atlas": {
      "command": "code-atlas",           // or: "python", "args": ["-m", "code_atlas.main"]
      "cwd": "/path/to/your/repo",
      "env": { "CA_PHP_CMD": "php adapters/php/index.php --server" }
    }
  }
}
```

**Adapters are not in the PyPI/wheel install.** `pip install code-atlas` gives you the MCP server
only; indexing still needs a repo checkout that contains `adapters/<lang>/` and a `CA_<LANG>_CMD`
pointing at it (as in the example above). The wheel alone cannot index source.

Call `get_index_status` first: it is the cheap (~100-token) entry point and tells you whether the
index exists, how stale it is, and what to call next. `build_or_update_index` builds it. Every tool
takes `detail_level` — `minimal` for the payload alone, `standard` (the default) to add provenance.

## Tools

| Tool | Returns |
|---|---|
| `get_index_status` | index stats, last indexed commit, staleness, next-step suggestions (call first) |
| `build_or_update_index` | counts + timing for the build it ran (full builds only until incremental lands) |
| `search_symbol` | ranked symbols (`qname`, kind, `file:line`) |
| `file_outline` | symbols + line ranges, no bodies |
| `read_symbol` | source of just one class/method + docblock |
| `find_callers` / `find_references` / `find_implementations` | resolved relationships + confidence tier |
| `include_graph` | `include`/`require` neighbors (`imports` / `imported_by` / `both`) |

## Prompts

| Prompt | Recipe |
|---|---|
| `explore_area` | status → search/outline → read only what's needed |
| `find_usages` | status → find_references / find_callers / find_implementations → read to confirm |

### Planned

| Tool | Returns |
|---|---|
| `impact` | bounded blast radius of a change |
| `namespace_tree` | namespaces + members |

## Configuration

Every knob resolves **environment → project file → default**. The project file is
`.code-atlas.toml` at the repo root (optional, meant to be committed); its keys are the environment
names lower-cased without the `CA_` prefix. A malformed value or an unknown key is a loud error, never
a silent fallback.

| Environment | `.code-atlas.toml` | Default | Meaning |
|---|---|---|---|
| `CA_DB_PATH` | `db_path` | `.code-atlas/graph.db` | index location (relative to the repo root) |
| `CA_WORKERS` | `workers` | `max(1, min(cpu-2, 8))` | adapter processes during a build |
| `CA_ADAPTER_TIMEOUT` | `adapter_timeout` | `30` | seconds an adapter may stay silent before a build kills it |
| `CA_MAX_RESULTS` | `max_results` | `50` | result cap for search/nav tools |
| `CA_IMPACT_DEPTH` | `impact_depth` | `2` | hops the impact engine traverses |
| `CA_IMPACT_MAX_NODES` | `impact_max_nodes` | `500` | node budget for one impact query |
| `CA_TOOLS` | `tools` | all tools | comma-separated tool allow-list |
| `CA_HOST_ROOT` | `host_root` | unset | absolute-path rewrite only (pair with `CA_CONTAINER_ROOT`; unused by the relative-path build) |
| `CA_CONTAINER_ROOT` | `container_root` | unset | absolute-path rewrite only (pair with `CA_HOST_ROOT`) |
| `CA_<LANG>_CMD` | `[adapter_cmd].<lang>` | — | the **complete argv** that launches one adapter in server mode |

```toml
# .code-atlas.toml
workers = 4
max_results = 50
tools = ["get_index_status", "build_or_update_index"]   # only names the server serves; a typo is a loud error
# Optional: only needed if something passes absolute host paths to the adapter.
# host_root = "/home/you/project"
# container_root = "/app"

[adapter_cmd]
php = "docker compose exec -T php php /app/adapters/php/index.php --server"
# or, where quoting bites (Windows paths), one word per entry:
# php = ["C:\\php\\php.exe", "adapters/php/index.php", "--server"]
```

The adapter command is the **whole** command: the core appends nothing to it, not even `--server`, so
it never has to know where a language's adapter lives. An adapter announces its own name, the file
suffixes it owns, and its capabilities on the first line it writes — that handshake is what routes
files to it.

Files are skipped using built-in patterns (`vendor/ var/ uploads/ log/ node_modules/ .git/`), then
`.gitignore`, then an optional `.codeatlasignore` — later rules win, so `.codeatlasignore` can
re-include what an earlier source excluded.

## Language support

| Language | Parser | Status |
|---|---|---|
| PHP (8.5 grammar, 8.1+ runtime) | nikic/php-parser | In progress (first) — see [`adapters/php/`](adapters/php/) |
| TypeScript / JavaScript | TypeScript Compiler API | Planned |
| Python | `ast` + jedi | Planned |
| C# / .NET | Roslyn | Planned |

## Roadmap

- **Phase 1 — Core + PHP:** full build → resolver → **search/read/outline (first daily release)** →
  scale → incremental → impact.
- **Phase 2 — More languages:** TS/JS (hardens the contract), then Python, then C#/.NET.
- **Phase 3 — Onboarding:** an Understand-Anything-style layer on top of the graph (architecture
  overview, guided tour, generated onboarding docs).

## Design principles

SOLID **at the boundaries** (the axis of change is *languages*, expressed through one versioned
contract) + **YAGNI** (one seam only until a second adapter exists) + **standard over sample** (adapters
encode the language spec/standards, never a specific repo's conventions). Details in the
[build plan](docs/PLAN.md).

## License

TBD.
