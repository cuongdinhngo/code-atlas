---
id: 159
slug: get-index-status-does-not-name-available-but-unconfigured-adapters
title: 'An adapter ships in-repo but is invisible until an env var is set — nothing in any payload says it exists'
phase: 1.5b
milestone: Adoption
status: todo
depends_on: [064, 028, 095]
---

## Why this exists (field retro round 8, 2026-08-26)

Round 8's whole investment was adapter #2 (TS/JS). It contributed **zero** to the host project, and
the reason was not capability — it was that the running server gave no sign the adapter existed:

> "A shipped capability that is invisible from inside the running server is indistinguishable from one
> that does not exist." (finding **8-G**)
>
> 3,293 tracked JS/TS files fell into `skipped.suffix`; three real-work questions crossed PHP↔JS and
> none could be answered. Nothing in any payload said *"an adapter exists that you have not enabled"*;
> `indexed_suffixes` was the only clue, and it describes the past, not a switch.

This is R-16's third kind — **roll-out**, at the product level — and it is the precondition for the
whole round's coverage gap being invisible during the work.

## Root cause — adapters are known only by their configured command

- `code_atlas/config.py:235-253` (`_adapter_cmds`) — the server learns adapters **only** from the
  `[adapter_cmd]` table and `CA_<LANG>_CMD` env vars. `config.py:89-91` is the per-language lookup.
- `code_atlas/adapter.py:290-303` (`extension_index`) — the suffix→adapter map is *"a dict built from
  adapters the caller already made"* (comment `:292`), i.e. from configured commands. **Nothing
  enumerates the `adapters/` directory.**
- Filesystem: `adapters/php/` **and** `adapters/typescript/` both ship in-repo, each with `src/` and an
  entry point. The TS/JS adapter is present and unreachable unless `CA_TYPESCRIPT_CMD` (or the
  `[adapter_cmd]` table) is set.
- `code_atlas/tools/get_index_status.py` — never reports `indexed_suffixes` in-band; it appears only
  under `verbose` → `collection` (`collection.py:23,37`, from the `INDEXED_SUFFIXES_KEY` build meta,
  `store.py:37` / written `indexer.py:820`). That is *what was indexed*, never *what could be*.

## Scope

- **`get_index_status` names available-but-unconfigured adapters.** Enumerate the adapters that ship
  in the repo (the `adapters/` directory, or a small manifest), diff against `config.adapter_cmds`, and
  report the set that exists but is not wired — with the concrete way to enable each (its
  `CA_<LANG>_CMD` env var / `[adapter_cmd]` entry).
- **Additive, omit-when-empty** (061): a server with every shipped adapter configured shows no new
  field.
- **Feeds 160.** The same fact — *"this index holds PHP only; a TS/JS adapter exists, unconfigured"* —
  is what 160 threads into the zero-answer path. This ticket makes it discoverable proactively; 160
  makes it explain a specific empty answer. Land the shared source of truth once.

### Explicitly not in scope

Auto-configuring or launching the adapter. This ticket makes the choice **visible**; wiring
`CA_TYPESCRIPT_CMD` into a host repo's MCP entry stays an operator action.

## Constraints

- **R1.1** — zero language branches in the core. Enumerating a directory of adapters is **data**, not a
  branch; no `if language == …` and no hardcoded language list may enter `code_atlas/`. The adapter
  name comes from the directory / handshake, exactly as the extension map already does.
- **R4.2** — deterministic: the same repo + config yields the same list, order-stable.
- **061 / R7.1** — no field when nothing is unconfigured.

## Acceptance criteria

1. On a repo where a shipped adapter (e.g. `adapters/typescript/`) is present but no `CA_*_CMD` /
   `[adapter_cmd]` entry configures it, `get_index_status` reports that adapter as available-unconfigured,
   with its enable key — pinned by a test.
2. On a repo where every shipped adapter is configured, the field is absent (061), pinned by a test.
3. No language name is hardcoded in `code_atlas/` to produce the list — the R1.1 grep-gate stays green,
   asserted.
4. Determinism holds (R4.2): stable membership and order.

## References

Field retro round 8, finding **8-G**. `code_atlas/config.py:235-253`, `code_atlas/adapter.py:290-303`
(`extension_index`), `code_atlas/tools/get_index_status.py`, `code_atlas/tools/collection.py:23,37`,
`code_atlas/store.py:37`, `code_atlas/indexer.py:820`. Related:
[064](064_build-without-adapter-silent.md) (a build with no adapter reports success over an empty
index), [028](028_index-health-metrics.md), [095](095_ignore-bucket-does-not-name-its-rule.md)
(a bucket must name its rule). Feeds [160](160_a-zero-answer-never-names-the-index-language-coverage.md).
