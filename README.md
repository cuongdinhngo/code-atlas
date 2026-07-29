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

## Tools (planned)

| Tool | Returns |
|---|---|
| `get_index_status` | index stats, staleness, next-step suggestions (call first) |
| `build_or_update_index` | full or incremental build |
| `search_symbol` | ranked symbols (`qname`, kind, `file:line`) |
| `file_outline` | symbols + line ranges, no bodies |
| `read_symbol` | source of just one class/method + docblock |
| `find_callers` / `find_references` / `find_implementations` | resolved relationships + confidence tier |
| `include_graph` | `include`/`require` graph |
| `impact` | bounded blast radius of a change |
| `namespace_tree` | namespaces + members |

## Language support

| Language | Parser | Status |
|---|---|---|
| PHP (8.5) | nikic/php-parser | In progress (first) |
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
