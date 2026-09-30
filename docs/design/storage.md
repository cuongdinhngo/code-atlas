# Storage — the shape of the graph, and what it cannot express

**`code_atlas/store.py` is the source of truth**; the `DDL` constant is the schema.
**[PLAN §10](../PLAN.md#10-sqlite-schema) is the reasoning** — the qname-uniqueness decision, the FTS
triggers, the schema versions and the two directions of a version mismatch all live there verbatim
and are not retold here (R7.6).

This file holds the three things neither of those does: the **scope** answer (how many repositories
one database serves), a **dated column-and-index snapshot** so a reader can see the shape without
opening `store.py`, and the **gaps** — what the schema cannot currently express.

Rendered companion: [`../assets/storage-schema.html`](../assets/storage-schema.html) — the same
snapshot as a standalone page, restating enough of PLAN §10 to be readable on its own.

> **Snapshot 2026-09-06 · schema 5 · contract 9.** Task 132 removed PLAN §10's `CREATE TABLE` block
> because it was byte-equivalent to `store.py`'s DDL and its `meta` comment had drifted to five keys
> of nine. The listing below is the same class of object and carries the same risk: where it
> disagrees with `store.py`, `store.py` is right and this file is stale.

## One database per repository

`main.py` opens with the whole scope in one line: *"build an app for one repo, then serve it over
stdio"*. `db_path` defaults to `<root>/.code-atlas/graph.db` (`config.DEFAULT_DB_PATH`), resolved from the
`root` handed to `load_config(root)`.

**No table carries a project column, and that is the answer, not an omission.** `nodes.file_path` is
repo-relative and `qualified_name` carries no repo prefix, so two repositories mean two server
processes over two databases: nothing in one index is reachable from the other, and no answer can
mix them. Merging two trees into one graph would collide on `UNIQUE(qualified_name, file_path)` the
moment they share a namespace — the same multiplicity PLAN §10 settled, one level up.

`working_roots` is not a project mechanism. It narrows what the onboarding surfaces *present* (tour,
flows) and leaves the graph whole (tasks 206/216).

Connection state, set **outside any transaction** because `foreign_keys` is silently ignored inside
one: `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`.

## Snapshot — five relations

| Relation | One row is | Columns |
|---|---|---|
| `files` | one indexed path | `path` PK · `hash` · `language` · `parsed_ok` · `updated_at` · `fingerprint` |
| `nodes` | one symbol | `id` PK · `kind` · `name` · `qualified_name` · `file_path` → `files(path)` · `line_start` · `line_end` · `modifiers` · `params` · `is_test` · `extra` · UNIQUE(`qualified_name`, `file_path`) |
| `edges` | one relationship | `id` PK · `kind` · `source_qname` · `target_qname` · `target_raw` · `file_path` · `line` · `confidence_tier` · `args` · `arg_keys` |
| `nodes_fts` | the search index | fts5 over `name`, `qualified_name`, `file_path`, `params`; `content='nodes'`, `content_rowid='id'`, `tokenize='trigram'`, three sync triggers |
| `meta` | one build-time stamp | `key` PK · `value`; the keys are the `*_KEY` constants in `store.py` and are deliberately not listed (task 132) |

Two properties of that table are worth stating because they are easy to miss and both are load-bearing:

- **`nodes.file_path → files(path)` is the only enforced foreign key in the schema.** Every other
  join is by string, and only the resolver upholds it. An edge stores `target_qname`, never a node id
  — so *which declaring file* is not representable (PLAN §8.2 / task 046).
- **`meta` exists so an answer never scans the graph.** Stamps are written once per build and read
  per answer. That direction is the constraint on every new predicate: a full-graph scan costs
  ~3.2 s on the 2.19 M-edge anchor (task 204) — fine once per build, disqualifying once per answer.
  `covered_suffixes` / `covered_languages` (159/160/173) are the shape to copy.

## Snapshot — eight indexes, one per query direction

| Index | On | Serves |
|---|---|---|
| `idx_nodes_name` | `nodes(name)` | bare-name lookup |
| `idx_nodes_kind` | `nodes(kind)` | filter by kind |
| `idx_nodes_file` | `nodes(file_path)` | outline one file |
| `idx_edges_src` | `edges(source_qname, kind)` | outgoing — impact, reachability |
| `idx_edges_tgt` | `edges(target_qname, kind)` | incoming — `find_callers` |
| `idx_edges_tier` | `edges(confidence_tier)` | confidence census |
| `idx_edges_raw` | `edges(target_raw, kind)` | pre-resolver and never-resolvable cases |
| `idx_edges_file` | `edges(file_path)` | `replace_file_rows` deletes by file, once per parsed file |

The last one is the dearest line in the schema. Unindexed, that delete is a full scan of the edge
table per file: **189 ms × 24,569 files = 77 minutes** — of a 76-minute rebuild (task 203).

## What the schema cannot express

- **No project column.** By design, above.
- **No `READS`.** `WRITES` has no counterpart — `SELECT … FROM` and `JOIN` emit no edge. *Which
  routine writes this table* is answerable; *which routine reads it* is not.

Declared foreign keys are modelled: the T-SQL adapter emits `REFERENCES` edges (Column → Column at
`RESOLVED`, or Column → Table at `HEURISTIC` when the target column list is omitted). The overview's
entity-relationship section renders them (task 224).
