# code-atlas

**Local-first MCP server that indexes your codebase into a symbol graph for fast, token-efficient
search, navigation, and impact analysis.** Language-agnostic core with per-language adapters — PHP
first, then TypeScript/JavaScript, Python, C#/.NET.

> Status: **the PHP path is feature-complete and daily-usable** — index → search / read / outline →
> callers / refs / impls → impact → incremental (`git diff`) → reachability / orphans, plus a
> read-through freshness reparse. Other languages are still planned. See [`docs/PLAN.md`](docs/PLAN.md)
> for the full design and milestones.

## Why

**`grep` is good at finding locations. It cannot produce a relationship.** Ask it who calls a method
and it gives you every line that contains the name — across every class that happens to declare one,
with no way to tell a resolved call from a coincidence, and no second number to check itself against.
code-atlas parses each language with its **best** parser into a **SQLite symbol graph**, then serves
symbol-level, *resolved* relationships over MCP: callers, implementations, blast radius, reachability,
the path between two symbols.

> **Honest scope.** This project began on the claim that native tools and `grep` are weak at
> name-resolved *search* on large repos. On 2026-08-08 that was measured against a ~19k-file private
> monorepo and it did not hold — native tools answered five real symptom-first questions correctly, and
> broad `grep` over that tree ran in under nine seconds at every scope. **If you want faster text
> search, you do not need this.** What survives the measurement is the edge data above. See
> [`docs/PLAN.md`](docs/PLAN.md) §19 for the full result, including what it got wrong.

- **Symbol-level, name-resolved** — "who calls this method?", "what implements this interface?", "read
  just this method", "blast radius of changing this file" — not grep-and-read-everything.
- **Language-agnostic core + per-language adapters** — each language uses the parser that actually
  understands it (PHP → nikic/php-parser, TS/JS → TypeScript Compiler API, Python → `ast`+jedi, C# →
  Roslyn), all speaking one versioned JSON contract.
- **Local-first & deterministic** — everything runs offline against a local SQLite index; no LLM or
  network in the core. Incremental updates via `git diff`. Requires **SQLite ≥ 3.25** (window
  functions for batched resolver lookups; Python's bundled `sqlite3` on supported platforms qualifies).
- **Complements your LSP tooling** — code-atlas is the indexed search/impact layer; a language server stays for precise nav/edit.

The token saving is measured, not asserted: a deterministic tokens-to-answer benchmark shows
code-atlas reaching the resolved answer **~98× cheaper** than grep-and-read on pinned public PHP repos
(laravel / symfony / brick) — see [`docs/runbooks/tokens-to-answer.md`](docs/runbooks/tokens-to-answer.md).

## How it works

```
MCP client ──stdio──▶ core (Python / FastMCP) ──JSONL contract──▶ language adapter (e.g. PHP sidecar)
                          │
                          ▼
                   SQLite  .code-atlas/graph.db   (nodes · edges · files · fts5 · meta)
```

The core is language-agnostic (no per-language branches). Adapters parse files and emit a common
`{nodes, edges}` vocabulary; the core stores them, resolves cross-file edges, and exposes MCP tools.

## Install

You need **Python ≥ 3.12**, and — to index PHP (the only adapter so far) — a **PHP CLI ≥ 8.1** and
**[Composer](https://getcomposer.org/)** on your PATH.

One command sets everything up and writes a ready-to-use `.mcp.json` into your project:

```bash
git clone https://github.com/cuongdinhngo/code-atlas.git
cd code-atlas
python scripts/setup.py /abs/path/to/your-project
```

That installs the core, builds the PHP adapter, and writes `<your-project>/.mcp.json` with the correct
interpreter, adapter path, and working directory filled in — the three things that are easy to get
wrong by hand. Run it with no path to print the snippet instead of writing it, or `--no-adapter` to
skip PHP. If PHP or Composer is missing it tells you and continues; rerun once they're installed.

Then **reload your MCP client** (in Claude Code: restart, or re-approve the project's `.mcp.json`) and
the `code-atlas` tools appear.

Onboarding a **large legacy repo** — where the first build takes minutes, `.gitignore` negations can
smuggle vendored trees into the index, and one knob decides whether the database is 1 GB or 2 GB — is
covered step by step in [`docs/runbooks/onboarding-a-repo.md`](docs/runbooks/onboarding-a-repo.md).

### Keep the index fresh while Claude edits (opt-in)

Task 035 already reparses drifted files at query time. For eager updates after Claude Code
`Edit`/`Write` on PHP files, install the PostToolUse hook under
[`contrib/claude-code/`](contrib/claude-code/) (`code-atlas-poke` console script + `"async": true`).
Safe no-op when `.code-atlas/graph.db` is missing; does not stall the tool round-trip.

<details>
<summary>Prefer to wire it up by hand?</summary>

`pip install -e .`, then `composer install --working-dir=adapters/php`, then point an `.mcp.json` at
your repo — `command` = `code-atlas` (or `python -m code_atlas.main`), `cwd` = the repo to index,
`env.CA_PHP_CMD` = `php /abs/path/to/code-atlas/adapters/php/index.php --server`. The adapter lives in
this checkout, so `CA_PHP_CMD` must be an **absolute** path. Docker instead of host PHP:
`docker compose exec -T php php /app/adapters/php/index.php --server`. Details in
[`adapters/php/README.md`](adapters/php/README.md).
</details>

## Usage

Drive everything through the MCP tools:

1. **`get_index_status`** — call first. The cheap (~100-token) entry point: is there an index, how
   stale is it, what to call next. A fresh project reports `indexed: false`.
2. **`build_or_update_index`** — builds the SQLite graph under `.code-atlas/graph.db`. Later,
   `full=false` does an incremental `git diff` update when it can, else a full rebuild.
   The index is a derived cache with no migration runner: after upgrading code-atlas across a
   `schema_version` change, an index **older** than the server is deleted and rebuilt in-band. An
   index **newer** than the server is refused untouched — that means the running server predates the
   upgrade, so restart the MCP client rather than rebuild (see `direction` in the payload).
3. **Query** — `search_symbol`, `file_outline`, `read_symbol`, `find_callers`, `find_references`,
   `find_implementations`, `include_graph`, `impact`, `reachable_from`, `find_orphans`, `explain_path`
   (see [Tools](#tools)).

Every tool takes `detail_level` — `minimal` for the payload alone, `standard` (default) adds provenance.

> **Language scope today:** only the **PHP** adapter exists. A TypeScript, Python, or C# project won't
> index yet — those are planned (see [Roadmap](#roadmap)).

## Tools

| Tool | Returns |
|---|---|
| `get_index_status` | index stats, last indexed commit, staleness, next-step suggestions (call first) |
| `build_or_update_index` | counts + timing; `full=false` incremental when possible, else full |
| `search_symbol` | ranked symbols (`qname`, kind, `file:line`) |
| `file_outline` | symbols + line ranges, no bodies |
| `read_symbol` | source of just one class/method + docblock |
| `find_callers` / `find_references` / `find_implementations` | resolved relationships + confidence tier; `find_callers` can also filter call sites by argument shape (`arg_position` + `arg_is`) |
| `include_graph` | `include`/`require` neighbors (`imports` / `imported_by` / `both`) |
| `impact` | bounded blast radius of a change (paths/qnames), depth-limited with decay |
| `reachable_from` | forward reachability from configured entry points |
| `find_orphans` | unreachable / zero-inbound symbols (dead-code candidates) |
| `explain_path` | shortest control-flow path between two symbols |

## Prompts

| Prompt | Recipe |
|---|---|
| `explore_area` | status → search/outline → read only what's needed |
| `find_usages` | status → find_references / find_callers / find_implementations → read to confirm |
| `impact_of_change` | status → impact on the changed paths/qnames → read only the blast-radius surface |

### Planned

| Tool | Returns |
|---|---|
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
| `CA_IMPACT_DEPTH` | `impact_depth` | `2` | hops the impact engine traverses (with default decay/floor, depths above ~8 are a no-op) |
| `CA_IMPACT_MAX_NODES` | `impact_max_nodes` | `500` | node budget for one impact query (seeds kept preferentially when over budget) |
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
| PHP (8.5 grammar, 8.1+ runtime) | nikic/php-parser | Available (first) — see [`adapters/php/`](adapters/php/) |
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
[build plan](docs/PLAN.md). Cross-repo validation (opt-in / scheduled, not per-PR) lives in
[`docs/runbooks/cross-repo-validation.md`](docs/runbooks/cross-repo-validation.md).

## License

MIT — see [`LICENSE`](LICENSE). © 2026 Cuong Ngo.
