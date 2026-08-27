---
id: 173
slug: coverage-claims-key-on-configured-not-indexed
title: 'Coverage claims key on what is *configured*, not on what is *indexed* — wiring an adapter deletes the coverage note and makes `indexed_suffixes` claim a language the graph does not hold'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [160, 159, 082]
---

## Why this exists (field episode, 2026-08-27 — and it is 8-A reopening through a new door)

159 and 160 exist so a zero on an index that holds only some of a repo's languages cannot read as
absence. **Both are keyed on `config.adapter_cmds` — whether the adapter is *launchable* — and neither
asks whether its files are actually *in the graph*.** So the act of flipping the switch, which every
round since 9 has asked for, produces this window:

| | before wiring | after wiring, before a full rebuild |
|---|---|---|
| `search_symbol("<a JS symbol>")` | `no_matches` **+ `unconfigured_adapters`** | `no_matches`, **note gone** |
| `indexed_suffixes` | `[".php", ".phtml"]` — true | **8 suffixes incl. `.js`** — false |
| JS files in the graph | 0 | **0** |

That is a **confident zero for an unindexed language** — 8-A's *"a false negative wearing a modelled
zero's clothes"*, and 9-C's *"the only payload this round I would call harmful"*, arriving as a
**consequence of the roll-out the retro recommends.** Round 11 §13 credited 167/159 for the harmful
shape being *"genuinely gone"*; it is gone only while the adapter stays off.

## Root cause

- `code_atlas/tools/coverage.py:22-24` — `coverage_gap(config)` returns
  `unconfigured_adapters(config.adapter_cmds)`. The gap is *"shipped but not launchable"*. Once
  `CA_<LANG>_CMD` is set the list is empty (`adapter.py:334-348`, omit-when-empty by 061), so
  `attach_coverage_note` attaches nothing — on every zero, for every tool, immediately.
- `code_atlas/indexer.py:239` — `_record_meta` runs **unconditionally**, before the
  `if to_parse or removed:` guard at `:242`. A no-op incremental therefore rewrites
  `INDEXED_SUFFIXES_KEY` (`:820`) to the newly-announced set while zero files of those suffixes were
  parsed. `indexed_suffixes` becomes a claim about the **adapters**, under a name that reads as a
  claim about the **index**.
- Nothing joins the two facts the store already holds: the suffix set in meta, and the suffixes that
  actually have rows in `files`.

## Scope

Make both claims answer *"what does the graph hold"*, not *"what could it hold"*.

1. `indexed_suffixes` reports suffixes the index **has files for** — or the payload distinguishes
   *claimed scope* from *achieved coverage* under two names. Design picks and records the rejected
   alternative; 082's collection identity must still reconcile.
2. The coverage note fires for a language that is configured but **has no indexed files**, not only
   for one that is unconfigured. The `enable` hint changes accordingly (the switch is already on; what
   is missing is a build).
3. The note stays self-gating and idempotent, and still never names the subject's own language (160's
   recorded boundary).

### Explicitly not in scope

- Why the build did nothing — [172](172_incremental-is-blind-to-a-scope-change.md). This ticket makes
  the *state* honest whatever the build did; 172 stops the state arising.
- Counting the invisible files — [174](174_unconfigured-adapters-names-the-switch-not-the-cost.md).
- Per-language node/edge statistics.

## Constraints

- **061** — a fully-wired, fully-indexed server adds nothing to any payload; a PHP-only server with no
  shipped second adapter is byte-identical to today.
- **Cost** — one bounded query at most, cached per build like the census; no per-answer scan of `files`.
- **R1.1** — keyed on suffix strings and row counts, never on a language name in the core.
- **160's boundary** — the note names the *index's* gap, not the subject's language.
- **R3** — new vocabulary, if any, is nav-level; confirm and record.

## Acceptance criteria

1. A test configures a second adapter, builds nothing, and asserts a zero answer **still** carries a
   coverage note — fails on today's code.
2. In that state `indexed_suffixes` (or its replacement pair) does not claim the unindexed suffix;
   082's `collected − skipped == kept` identity still reconciles.
3. A fully-indexed, fully-wired server is byte-identical to today (061), pinned.
4. The note remains self-gating/idempotent across the single and sweep envelopes (160 AC1e).
5. The added cost is measured; no per-answer table scan.
6. Determinism (R4.2), no language branch (R1.1), contract impact confirmed (R3).

## References

Field episode 2026-08-27, finding (3)'s consequence — surfaced while verifying findings (1)–(5) against
source, not observed directly. Round 11 §13 (*"the harmful shape is genuinely gone"* — true only while
the adapter is off), §4, §14 rows 8-A / 9-C. `code_atlas/tools/coverage.py:22-24,38-58`;
`code_atlas/adapter.py:334-348`; `code_atlas/indexer.py:239,242,820`. Related:
[160](160_a-zero-answer-never-names-the-index-language-coverage.md),
[159](159_get-index-status-does-not-name-available-but-unconfigured-adapters.md),
[082](082_claims-nobody-outside-can-check.md),
[172](172_incremental-is-blind-to-a-scope-change.md) (ship together).
