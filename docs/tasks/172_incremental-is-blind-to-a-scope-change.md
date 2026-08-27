---
id: 172
slug: incremental-is-blind-to-a-scope-change
title: 'An incremental build is blind to a scope change — 3,244 newly-in-scope files reported as `wrote.files: 0`, beside a census that counts them'
phase: 1.5b
milestone: Freshness
status: todo
depends_on: [016, 060, 053]
---

## Why this exists (field episode, 2026-08-27 — the roll-out attempt)

The maintainer wired the second adapter into the anchor repo — the one change every round since 9 has
named as binding — restarted the server, and ran a build. It reported success and did nothing:

```
collection: kept: 22381,  indexed_suffixes: 8 suffixes   ← the walk sees the new scope
build:      wrote.files: 0                               ← nothing was parsed
status:     graph.files: 19137                           ← the graph is unchanged
elapsed:    2.6 s
```

> *"Payload trung thực nhưng tự mâu thuẫn về hiệu quả: `kept: 22381` nằm cạnh `graph.files: 19137`
> với `wrote: 0`. Em mất một vòng build vô ích vì thiếu cái này."*

The collector knew there were 3,244 files newly inside the scope. The incremental planner never
considers them, and no field says so. **A build that cannot act on the request must not answer like a
build that had nothing to do** — that is 060's rule, one layer up: 060 fixed *delta counts wearing
total field names*; this is *a refusal wearing a no-op's clothes*.

## Root cause

- `code_atlas/indexer.py:212` — `candidates = sorted((changed_set | dependents) & wanted)`.
  `changed_set` is the git delta and `dependents` are files targeting affected qnames. A file that
  entered scope because an **adapter** was added is neither, so it is never a candidate and
  `to_parse` is empty.
- `code_atlas/indexer.py:163-166` — the escalation this needs **already exists**, for a different
  axis: a stored `contract_version` that differs forces `full_build` ("*vocabulary changed —
  incremental would mix eras*", task 030 AC1). The suffix set is the same class of change and is not
  checked, though `store.get_meta(INDEXED_SUFFIXES_KEY)` holds the previous value
  (`store.py:37`, written at `indexer.py:820`).
- `code_atlas/indexer.py:193-195` — `wanted` is already the newly-collected set, so
  `wanted - set(store.file_paths())` names exactly the newly-in-scope files with **no new query**.

## Scope

Make a scope change a first-class build input, not an invisible one.

1. Compare the announced suffix set against `indexed_suffixes` in meta. When they differ, the build
   must not silently no-op. Design picks one of three and records the rejected two:
   - escalate to `full_build` (matches the `contract_version` precedent);
   - a **suffix-scoped** pass — parse `wanted - indexed` only, which is the right unit of work for
     "a language was added" and avoids re-parsing 19,137 unaffected files;
   - refuse: `mode: "scope_changed"` + `try_instead: full=true`.
2. Whatever is chosen, the report names it, so `wrote.files: 0` can never again mean two different
   things (060).
3. The escalation lives in `indexer.update`, **not** in a caller — `code-atlas-refresh` (053) and the
   MCP tool must both inherit it. A fix in one caller leaves the git hook in the same trap.

### Explicitly not in scope

- The `unconfigured_adapters` cost figure — [174](174_unconfigured-adapters-names-the-switch-not-the-cost.md).
- What the payload *claims* about coverage after such a build — [173](173_coverage-claims-key-on-configured-not-indexed.md),
  which is the dangerous half and should land with this one.
- Config reload — [175](175_config-is-loaded-at-spawn-and-nothing-says-so.md).

## Constraints

- **Cost** — the suffix-scoped option must be measured against the full rebuild it replaces; the
  no-op path (matching suffix sets) stays at today's ~2.6 s and adds no query (080, 096).
- **R4.3** — the write lock is unchanged; a busy peer is still a clean skip.
- **061** — a build whose scope did not change is byte-identical in its report.
- **R1.1** — the comparison is over suffix strings from the handshake; no language named in the core.
- **R4.2** — deterministic: same tree + same adapters ⇒ same decision.

## Acceptance criteria

1. A test adds an adapter (a second suffix) between two builds and asserts the second build does not
   report a successful no-op — it escalates, scopes to the new suffix, or refuses with a named
   `mode`. Fails on today's code.
2. The chosen behaviour is reported in the build payload; `wrote.files: 0` is unambiguous.
3. `code-atlas-refresh` inherits the behaviour, pinned by a test that goes through the hook path.
4. A build with an unchanged suffix set is byte-identical and pays no extra query (measured).
5. If the suffix-scoped pass is chosen, its cost against a full rebuild is measured and recorded.
6. Determinism (R4.2), no language branch (R1.1), no contract bump (R3).

## References

Field episode 2026-08-27 (the roll-out attempt), findings (1) and (5). Round 11 §13 measured the
adapter working on the anchor's real front end at 53.2 % RESOLVED while unwired; this is the first
thing a maintainer hits when acting on that. `code_atlas/indexer.py:163-166,193-195,212,820`;
`code_atlas/store.py:37`. Related: [016](016_incremental-git.md) (the path),
[060](060_build-report-scale-naming.md) (a report that cannot mean two things),
[053](053_refresh-on-checkout-hook.md) (the second caller),
[173](173_coverage-claims-key-on-configured-not-indexed.md) (ship together).
