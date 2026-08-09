---
id: 064
slug: build-without-adapter-silent
title: 'A build with no adapter configured reports success over an empty index'
phase: 1.5b
milestone: Agent-trust
status: done
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

## Outcome

- **Empty `adapter_cmds`:** `AdapterError` naming `CA_<LANG>_CMD` and `[adapter_cmd].<lang>` before
  announce / meta (full + incremental + `build_or_update_index`).
- **Empty suffix union:** handshake already rejects empty `extensions`; `_require_announced_suffixes`
  keeps the same refusal if owners is empty after announce.
- **Zero files + non-empty suffixes:** success (data). Distinguisher: non-empty `indexed_suffixes`.
- **Proving tests:** `tests/test_build_without_adapter_silent.py`.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 064 — build-without-adapter-silent (working doc)

- **Ticket:** 064 · local `docs/tasks/064_build-without-adapter-silent.md`
- **Type:** bug
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N UI
- **TIER:** full (review skipped per user instruction this run)
- **BASELINE:** green — `989 passed` at tip `a2b884b` (untouched main)
- **work_doc_mode:** embed
- **working-doc path:** this file below separator

## Phase 0 — Refine

`REFINE: 0 unresolved | skip: yes`

`refine skipped: 0 unresolved product-decisions`

**HOW (cited, for analysis):** zero files collected with non-empty suffix set stays a **successful**
build (data, not config) — ticket Scope already frames it as a data condition; R5.3 is for config
errors only. Distinguishability: refused runs never write `last_commit` / empty `indexed_suffixes`;
successful empty-collect still has non-empty `indexed_suffixes` from announced adapters.

`scripts/profile_incremental.py:58-63` already refuses empty `adapter_cmds` for the profiler; the
indexer path does not yet.

## Requirements matrix

`SECTIONS: 5 found (Goal, Evidence, Scope/Deliverables, Constraints, Acceptance criteria) | 5 decomposed | ROWS: C=4 R=6 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | Make a build that cannot parse anything refuse to run | Empty adapter / empty suffix union must fail loud | indexer `_announce` empty loop | | | ❌ |
| R1 | Scope | Refuse when `adapter_cmds` empty; message names both config forms | Early raise before meta | ticket + `indexer.py:484` | | | ❌ |
| R2 | Scope | Refuse when suffix union empty after handshake | Same class, after `_owners` | `_owners` / `extension_index` | | | ❌ |
| R3 | Scope | Zero files collected = data; decide+record boundary | Stay success; pin in test + Outcome | ticket Scope | | | ❌ |
| R4 | Scope | Leave nothing behind — no valid last_commit / empty indexed_suffixes | Raise before `_record_meta`; no reconcile wipe of prior good index if check is first | `_record_meta` | | | ❌ |
| R5 | Scope | Same refusal through `build_or_update_index` | Exception or error payload, not files:0 success | `build_or_update_index.py` | | | ❌ |
| R6 | Scope | nodes:1 rules bookmark → 068 | Out of scope | ticket | | | ⚠ → 068 |
| C1 | Constraints | R5.3 config loud; bad file soft | Use AdapterError/ConfigError family | ENGINEERING_RULES R5.3 | | | ❌ |
| C2 | Constraints | R1.1 language-agnostic check | No named-language branch | R1.1 | | | ❌ |
| C3 | Constraints | R4 no behaviour change when correctly configured | Existing suite floor | baseline green | | | ❌ |
| C4 | Constraints | R1.2 no new abstraction — at `_announce` | Guard beside `_announce` | ticket | | | ❌ |
| AC1 | AC | No adapter → non-zero exit; message names both forms; no schema/last_commit pair | pytest.raises + meta assert | | | | ❌ |
| AC2 | AC | `build_or_update_index` returns error not files:0 | tool call / exception | | | | ❌ |
| AC3 | AC | Empty suffix union fails same way | fake adapter announcing `extensions:[]` | | | | ❌ |
| AC4 | AC | Correct config over fixtures byte-identical | existing indexer tests | | | | ❌ |
| AC5 | AC | Tests: empty cmds, empty suffixes, zero-files boundary pin | new tests | | | | ❌ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1? |
|-------|---------------|------------------------|--------|--------------|---------|
| AC1 | non-zero + both forms + no last_commit pair | Message must include `CA_<LANG>_CMD` and `[adapter_cmd]` (profiler already has both) | Y | greppable | — |
| AC2 | MCP/tool error not files:0 | Raising AdapterError → FastMCP ToolError | Y | test | — |
| AC3 | empty suffix union fails | After announce, `owners == {}` | Y | test | — |
| AC4 | byte-identical when configured | Existing suite / hash of graph under fixtures | Y | suite | — |
| AC5 | three test cases | empty cmds, empty suffixes, zero files success | Y | tests exist | — |

## CLARIFICATION

`CLARIFICATION: j=0 | Gate-0 items: none`

## Inventory

- Denominator N: 2 call sites (`full_build`, `incremental_update`) + 1 tool surface
- 1. `full_build` early refuse
- 2. `incremental_update` early refuse
- 3. `build_or_update_index` surfaces raise

## Cause taxonomy

config (empty adapter_cmds / empty announced suffixes) — not soft file failure.

## TIER / SCOPE

`TIER: full` · `SCOPE: M` · review **skipped this run** (user: `/solve 064 but no review step`)

## Decision log

| When | Decision | Why |
|------|----------|-----|
| refine | Zero-files-with-suffixes = success | Ticket Scope data-condition + R5.3 |
| solve | Skip review phase | Explicit user instruction |

## Phase 2 — Design

**Approach:** Guard beside `_announce`: `_require_configured_adapters` before start;
`_require_announced_suffixes` after `_owners`. Raise `AdapterError` before `_record_meta`.
Zero-files with suffixes stays success.

**Rejected:** Soft-fail with `files:0` + warning flag — still reads as a healthy empty index
(the defect). Unlink DB on every refusal — too aggressive when a prior good index exists and
the check runs first (no mutation).

**Assumptions:** FastMCP surfaces raised `AdapterError` as tool failure — verified by existing
adapter-error patterns / AC2 integration test. Handshake rejects empty `extensions` —
verified (`contract._check_extensions`).

**Change list:** `indexer.py` · `fake_adapter.py` (empty-extensions mode) · proving tests ·
indexer test flip · BACKLOG/LESSONS/Outcome.

**Proving test:** `tests/test_build_without_adapter_silent.py`

| AC | risk | proof | match |
|----|------|-------|-------|
| AC1 | integration | pytest AdapterError + meta | ✅ |
| AC2 | integration | build_or_update_index raise | ✅ |
| AC3 | integration | empty-extensions handshake | ✅ |
| AC4 | integration | existing suite | ✅ |
| AC5 | integration | three cases + zero-files | ✅ |

Gate 2 cleared under standing approval.

## Phase 3 — Execute

**Branch:** `fix/064-build-without-adapter-silent`
**Sweep:** diff ⊆ change list; review skipped per user.

## Phase 4 — Review

**Skipped** (user: `/solve 064 but no review step`).

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| — | — | — | no subagent dispatch this run |

## Phase 5 — Finalise

Standing: push + PR + merge when CI green.

## Session status

- **Phase:** finalise
- **work_doc_mode:** embed
- **working-doc path:** `docs/tasks/064_build-without-adapter-silent.md` (below separator)
