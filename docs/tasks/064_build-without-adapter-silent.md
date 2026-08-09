---
id: 064
slug: build-without-adapter-silent
title: 'A build with no adapter configured reports success over an empty index'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [009, 028, 056]
---

## Goal
A full build launched with **no adapter command configured** completes, exits 0, and writes a
well-formed database containing nothing. Every later question answers "not found" — correctly, from
an index that never saw a file. [R5.3](../ENGINEERING_RULES.md) names "missing adapter command" as a
fail-loud case; this path evades it. Make a build that cannot parse anything refuse to run.

## Evidence (anchor-repo rebuild, 2026-08-09)
- `scripts/scale_full_build.py` run without `CA_PHP_CMD` and against a `.code-atlas.toml` with no
  `[adapter_cmd]` table: **exit 0** in **0.277 s**, artifact written as for any real build —
  `files: 0`, `parsed: 0`, `failed: 0`, `edges: 0`, `nodes: 1`.
- The DB it left is **76 KB** and presents as current and valid: `schema_version = 4`,
  `contract_version = 5`, `last_commit` recorded, `indexed_suffixes = ""` (empty string).
  Nothing in `meta` distinguishes it from an index of a repo that genuinely has no code.
- Root cause is arity, not error handling. `_announce` loops `for key in sorted(config.adapter_cmds)`
  (`indexer.py:484`); an **empty** mapping means zero iterations, so the loud `AdapterError` in
  `_adapter` (`indexer.py:499`, *"has no configured command — set CA_<LANG>_CMD"*) is only reachable
  when a key exists with no command. Zero keys reads as "nothing to do", not "misconfigured".
- `_adapter_cmds` (`config.py:200`) has no default entry, so a repo with neither the `[adapter_cmd]`
  table nor a `CA_<LANG>_CMD` variable yields `{}` — the exact shape that slips through.
- Downstream is then consistent and silent: `_owners` is `{}`, `collect(root, ())` returns nothing,
  and `_record_meta` writes the empty suffix list as fact.
- `nodes: 1` alongside `parsed: 0` is the **rules bookmark**, not a parsed symbol: `indirection_rules`
  was configured for this build, and `enrichment.py:142` writes `.code-atlas/indirection-rules` as a
  `File` node and a `files` row with `parsed_ok=True`. That the bookmark is counted as source is its
  own defect — [068](068_rules-bookmark-counted-as-source-file.md) owns it.

The failure is worse than a crash because it is *stable*: re-running reproduces it, and the index
looks healthy to every tool that inspects it.

## Scope / Deliverables
- **Refuse the build when no adapter can run.** `full_build` and `incremental_update` fail loud when
  `config.adapter_cmds` is empty, with a message naming **both** configuration forms (`CA_<LANG>_CMD`
  and `[adapter_cmd].<lang>`), in the wording family already used at `indexer.py:499`.
- **Refuse when the claimed suffix set is empty** — adapters configured, handshakes read, but the
  union of announced extensions is empty. Same class of defect, one step later.
- **Draw the config/data line explicitly.** Adapters configured, suffixes claimed, but zero files
  collected (empty repo, everything ignored) is a **data** condition, not a config one. Decide and
  record whether that stays a successful build, and if so, what the report says so a caller can tell
  it apart from the case above. The written boundary is a deliverable.
- **Leave nothing behind.** A refused build must not leave a DB whose `meta` reads as a valid,
  current index of the repo — no `last_commit`, no empty `indexed_suffixes` row.
- **Same refusal through MCP.** `build_or_update_index` surfaces the error; it must not return a
  report with `files: 0` and no signal.
- **`nodes: 1` is accounted for** — the rules bookmark, tracked in
  [068](068_rules-bookmark-counted-as-source-file.md). Nothing to do here beyond not re-deriving it.

## Constraints
- R5.3 — config error, so loud; a single unparseable source file stays soft. Do not blur the two.
- R1.1 — the check is language-agnostic ("no adapter configured"), never a test for a named language.
- R4 — no behaviour change for a correctly configured build; the existing suite is the floor.
- No new abstraction for the check (R1.2) — it belongs where `_announce` already stands.

## Acceptance criteria
- A build with no adapter configured exits non-zero with a message naming both configuration forms,
  and no database is left that reports a `schema_version`/`last_commit` pair for the repo.
- The same run through `build_or_update_index` returns an error, not a `files: 0` success report.
- A build whose adapters announce no suffixes fails the same way.
- A correctly configured build over the fixture corpus is byte-identical to today's.
- Tests cover the empty-`adapter_cmds` case and the empty-suffix-union case; the "zero files
  collected" boundary case has a test pinning whichever side the ticket lands on.

## References
[R5.3](../ENGINEERING_RULES.md) (fail loud on config errors — names this exact case);
[056](056_filter-values-fail-loud.md) (precedent: an empty answer standing in for an error);
[058](058_list-parse-failures.md) (making index holes visible); `code_atlas/indexer.py:476-515`
(`_announce`, `_adapter`, `_owners`), `code_atlas/indexer.py:693` (`_record_meta`);
`code_atlas/config.py:200` (`_adapter_cmds`); `README.md:170,181` and
[`docs/runbooks/onboarding-a-repo.md`](../runbooks/onboarding-a-repo.md) §2 (both document
`CA_<LANG>_CMD` as required — the code does not enforce it).
Origin: rebuilding the anchor repo onto contract v5, 2026-08-09 — the operator forgot `CA_PHP_CMD`
and the build reported success.
