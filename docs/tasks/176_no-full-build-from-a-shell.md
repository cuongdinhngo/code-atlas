---
id: 176
slug: no-full-build-from-a-shell
title: 'No full build from a shell — `code-atlas-refresh` runs the incremental path but never a full one, so a first build and a post-config rebuild both require an MCP client'
phase: 1.5b
milestone: Freshness
status: todo
depends_on: [010, 053]
---

## Why this exists (field episode, 2026-08-27)

The maintainer, trying to rebuild after wiring the second adapter:

> *"`[project.scripts]` đã có 4 entry (`code-atlas-poke`, `-refresh`, `-signal`, `-llm`) nhưng không có
> `code-atlas build [--full]`. Muốn rebuild phải qua một MCP client — nên không rebuild được từ shell,
> từ CI, hay sau khi đổi config. Đây cũng chính là thứ mà mục roll-out trong retro cần."*

**Narrowed after checking the source, because the gap is smaller and more specific than "no build
CLI".** `code-atlas-refresh` already runs *"the same path as `build_or_update_index(full=false)`"*
(`hooks/refresh.py:1-8`). What no entry point can do is:

- a **full** build — there is no `--full`, on any script;
- a **first** build — refresh is deliberately a *"safe no-op with no index (never builds)"*.

So the fix is a flag on machinery that already exists, not a new subsystem. And it is on the roll-out
critical path: round 11 §11.g's break-even condition is *`.mcp.json` + one CI job + delete the scanner
lines the graph answers*, and **a CI job cannot call an MCP tool.**

## Root cause

- `pyproject.toml` `[project.scripts]` — `code-atlas` is the **MCP server** (`code_atlas.main:main`);
  the three hook helpers are `poke` (one file, task 036), `refresh` (incremental, task 053) and
  `signal`. None takes a full-build path.
- `code_atlas/hooks/refresh.py:1-8` — by design: incremental only, and never builds without an index,
  so a git hook can never trigger a multi-minute first build.
- `code_atlas/tools/build_or_update_index.py` owns the whole build entry (lock, schema mismatch,
  report shaping — `:101,177,196,213`); a CLI must reuse it rather than call `indexer` directly, or the
  two paths will drift on locking and reporting.

## Scope

One shell entry point for a build, reusing the existing tool path.

1. A `--full` capability reachable from a shell, and a first build when no index exists — as a flag on
   `code-atlas-refresh`, or a new `code-atlas-build` script. Design picks one and records why (the
   safety property of refresh's *"never builds"* default must not be lost for git hooks).
2. Exit codes and one-line stderr output usable from CI: success, nothing-to-do, busy peer (R4.3),
   and failure distinguishable.
3. It goes through `build_or_update_index`'s path, so the lock, the schema-mismatch answer and the
   report shape are identical to the MCP route.

### Explicitly not in scope

- A general CLI surface for the query tools. This is the build only.
- The CI job itself and `.mcp.json` — those belong to the consuming repo, deliberately not filed here
  (round 11 §11.i).
- What the build should *do* when scope changed — [172](172_incremental-is-blind-to-a-scope-change.md).

## Constraints

- **R4.3** — one mutex shared with the server; a busy peer is a clean skip, not an error.
- **053's safety property** — the git-hook path must keep *never builds without an index*; a `--full`
  flag must be opt-in per invocation.
- **R6.5** — the entry point is covered by the gate's `entry points (derived from [project.scripts])`
  check, so a new script must appear there.
- **Determinism** — same tree ⇒ same rows as the MCP route (R4.2); the CLI adds no second code path
  for the build itself.

## Acceptance criteria

1. A full build runs from a shell with no MCP client, on a repo with **no** existing index, and
   produces the same rows as the MCP route — pinned by a test.
2. The incremental hook path still never builds without an index (053), pinned.
3. Exit codes distinguish success · nothing-to-do · busy peer · failure, each pinned.
4. The build goes through `build_or_update_index`; no second lock and no second report shape.
5. `scripts/gate.sh`'s entry-point check covers the new script.
6. Determinism (R4.2); no language branch (R1.1); no contract bump (R3).

## References

Field episode 2026-08-27, finding (4), narrowed against source (refresh already covers incremental).
Round 11 §11.g (break-even needs a CI job), §11.i (roll-out is not filed as a ticket, but the
capability it needs is). `pyproject.toml` `[project.scripts]`; `code_atlas/hooks/refresh.py:1-8`;
`code_atlas/tools/build_or_update_index.py:101,177,196,213`. Related:
[010](010_index-status-and-build-tools.md) (the tool this must reuse),
[053](053_refresh-on-checkout-hook.md) (the existing shell path),
[172](172_incremental-is-blind-to-a-scope-change.md).
