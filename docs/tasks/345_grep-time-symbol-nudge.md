---
id: 345
slug: grep-time-symbol-nudge
title: 'A grep for a symbol gets one "ask code-atlas first" line — right after it, from adapter-declared shapes'
phase: 2
milestone: Adoption
status: done
depends_on: [344]
---

## Why this exists

344 installs the hooks, but none of them speaks when the agent reaches for Grep on a structural
question. Of the channels in 344's table, only a PostToolUse hook on `Bash|Grep` sees that moment.

## Evidence (anchor repo, 2026-09-29)

- **A concrete procedure step beats a general rule.** The anchor repo's CLAUDE.md routed symbol
  questions to code-atlas, and its SessionStart hooks restated it. Even so, sessions running a project
  skill answered caller questions with Grep, because the skill's own step said
  `grep -rn "methodName("`. The fix there was to rewrite six skills by hand. A new anchor project
  won't know it needs to.
- **The one channel that fired at the decision was project-local.** The anchor repo wrote its own
  PostToolUse(`Bash|Grep`) hook, `.claude/hooks/code-atlas-symbol-nudge.sh`. It spots a grep for a
  symbol (`function x`, `->x(`, `::x(`, `class X`, or a proc/table name over `*.sql`), or a sed/awk
  slice of a body by line range, and injects one "ask code-atlas first, keep Grep as the cross-check"
  line. It is rate-limited to once per kind per 15 minutes and silent without an index or a
  registration. None of that exists upstream.
- Adapter `meta` declares `name`, `extensions`, `capabilities` and `contract_version`
  (`contract.py`, `validate_meta`) — no symbol shape, so the core has nothing to build a
  language-neutral pattern from. `META_FIELDS` is closed, so a new key is a contract change.
- PostToolUse speaks after the first grep, not before it. That is the earliest non-blocking seam;
  a PreToolUse block is out of scope (it would make Grep fail, not steer).

## Scope

1. **Contract: adapters declare their symbol shapes.** A new optional `meta` field lists the
   regex shapes that mark a grep pattern as a symbol search in that language — declarations
   (`function x`, `class X`), qualified references (`->x(`, `::x(`) **and the bare call `x(`**,
   the exact shape of the anchor skill's `grep -rn "methodName("`. Name the field for what it
   matches, not "declaration keywords". Bump `contract_version` and extend the conformance suite
   (R3); each adapter encodes its language standard, never a repo's names (R2).
2. **`code-atlas-nudge` console script**, the upstream of the anchor hook, shipped in 344's plugin.
   - Patterns come only from adapter `meta`, never widened by hand (the 200 poke-filter rule).
   - **Parse surface, closed:** the Grep tool's `pattern` / `path` / `glob` / `type`, and in Bash
     the first `grep`, `rg` or `git grep` of the command with its `--include`, `-g/--glob`,
     `-t/--type` and path arguments. Anything else (pipes past the first grep, `find -exec`,
     `xargs`) is silent — a missed nudge costs nothing, a wrong one costs trust.
   - **Scope rule:** a shape fires when the grep is unscoped or its scope includes that adapter's
     suffixes, and stays silent when the scope is limited to other suffixes only. That one generic
     rule yields the anchor's exemption — a proc name grepped over `*.php` is a string literal,
     Grep is right there — with no language branch in the core (R1.1).
   - Rate-limited to once per kind per session (keyed on the hook's `session_id`). It never
     blocks, always exits 0, and stays silent with no index.
   - Each firing appends one line to the index's log, so a later scoring run can count it.

## Acceptance criteria

- **AC1:** Replaying the anchor's grep shapes — a PHP method (`->x(`, bare `x(`), a SQL proc over
  `*.sql`, and the same shapes unscoped — fires the nudge once per kind, and a second replay in the
  same session stays silent. A literal-text grep (a config key, a comment), a proc name grepped over
  `*.php`, and a Bash shape outside the parse surface never fire.
- **AC2:** A drift test, in the manner of `test_poke_snippet_covers_every_adapter.py`, fails when an
  in-tree adapter ships without symbol shapes (optional in the contract, required in this repo).
- **AC3:** The README tells a project that wires its own grep-nudge hook to remove it once the
  plugin is installed, so each event gets one nudge, not two. The anchor's retirement is its own
  change, outside this repo.
- **AC4:** A test asserts each firing writes its log line (kind, adapter, session). Scoring the
  recognition effect is 200's AC5 and waits on 200; this ticket does not claim it.

## Out of scope

- sed/awk slices of a body by line range — the anchor's hook catches them, but they are a
  read-a-symbol signal, not a grep; `code-atlas-signal` (099) is where they belong.
- A PreToolUse block on Grep.

Only the plugin packaging depends on 344; the contract field and the script can land first.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 345 · **work_doc_mode:** embed · **Current phase:** 3 execute · **Next action:** review.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`; *"with
  skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `feat/345-symbol-search-nudge` (renamed from `…-grep-symbol-nudge`: the contract validator reads `grep` in a branch name as a content grep — SG-1). Stacked on `feat/344-claude-code-plugin` (PR #7): the nudge ships in 344's plugin. Contract
  `.mango/run-contract-345.txt`, base `feat/344-claude-code-plugin`. RECONCILE t0: 5 declared |
  3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 2 want-decision asked | 8 how-decision resolved+cited | 2 ASSUMED | skip: no`

Premise: `contract.py` `validate_meta`/`META_FIELDS`, `test_poke_snippet_covers_every_adapter.py`,
344's plugin hook table (`gen_skill._claude_code_hooks`), 200's poke-filter rule, R1.1/R2/R3 — resolve.
Ambiguous: the anchor's `.claude/hooks/code-atlas-symbol-nudge.sh` lives in another repo.
Recall: `343-C2` (`formatter-rewrites-untouched-lines`) and `344-C3`
(`verify-the-shipped-artifact-not-the-working-tree`) by handle — this change adds a shared contract
field and a shipped hook. Advisory.

**Spike (Claude Code 2.1.284, `--plugin-dir`, PostToolUse on Read).** A hook's **plain stdout never
reached the model** (asked to quote a marker: `NONE`); the same marker as
`hookSpecificOutput.additionalContext` JSON did (the JSON marker quoted back verbatim). So the nudge emits JSON. It also
means `code-atlas-signal`'s plain `print` has never reached a model — filed as ticket 346, not fixed
here (outside this change list).

**Want-decisions — handed back by the maintainer, so `ASSUMED (awaiting ratification)`:**

| # | The want | ASSUMED answer |
|---|---|---|
| W1 | The contract shape of the new field | `symbol_shapes`: a list of `{kind, pattern, scoped?}`; `kind` ∈ `declaration · reference · call · name`; `pattern` a regex over the grep pattern text; `scoped: true` fires only when the grep is scoped to that adapter's suffixes (a bare SQL proc name is ambiguous alone). Optional in the contract, required in this repo (AC2). |
| W2 | The signal hook's plain-stdout defect | Filed as 346; this PR does not touch `signal.py`. |

**How-decisions — resolved and cited** (the exposure-checker, 1 dispatch, 44,332 fresh, raised 8):

| # | Decision | Resolution | Citation |
|---|---|---|---|
| H1 | "per kind" | the shape's `kind`; `->x(` (reference) and `x(` (call) are two kinds | ticket AC1 *"once per kind"* |
| H2 | the log | `.code-atlas/nudge.log`, one TSV line (time · session · adapter · kind) per firing | ticket Scope 2 *"the index's log"*; `.code-atlas/` is code-atlas's own dir (`tests/test_contrib_snippets.py` `OWN`) |
| H3 | wording | one line: `code-atlas: this grep looks like a symbol search (<kinds>) — ask the index first (search_symbol / find_callers / find_references); keep Grep as the cross-check.` | ticket Evidence (the anchor line) |
| H4 | symbol vs literal | the adapter's shapes are the whole rule; the core adds none | ticket Scope 2 *"Patterns come only from adapter meta"* |
| H5 | `type` → suffix | `-t X` / Grep `type: X` means suffix `.X`; an unknown type scopes to no adapter → silent | R1.1 (a generic rule, no table) |
| H6 | several adapters match | one line naming every new kind; each kind rate-limited once | ticket Scope 2 |
| H7 | no `session_id` | key `""` — once per kind per state file | ticket Scope 2 *"never blocks"* |
| H8 | a stale index | the gate is presence of an index, as every hook's is | ticket Scope 2 *"silent with no index"*; 344 `PLUGIN_GATE` |
| H9 | how the nudge gets the shapes | the build stamps them into `graph.db` meta (as `capabilities_by_language`); the nudge reads that. A tool install ships no `adapters/`, and a spawn per grep would cost more than the grep | `indexer._record_meta`, `store.stamped_capabilities_by_language` |
| H10 | wiring | the shared hook table gains `PostToolUse` entries: `Grep` (no `if`) and `Bash` with `Bash(grep *)`, `Bash(rg *)`, `Bash(git grep *)` — one rule each (344-C1) | `docs/LESSONS.md` 344-C1 |

## Phase 1 — analysis

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Evidence, Scope, Acceptance criteria, Out of scope) | 5 decomposed | ROWS: C=4 R=7 G=1 AC=4`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/18 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

Carried forward from Phase 0: the two lines above `SECTIONS:`.

### BASELINE

The branch point is `af879142`+ (344's head), whose full gate ran green — `scripts/gate.sh`:
`GATE GREEN — all 21 checks passed` (344 Phase 4). Not re-run.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "only a PostToolUse hook on `Bash\|Grep` sees that moment" | a hook that speaks right after a symbol-shaped grep | open |
| C1 | Evidence | "Adapter `meta` declares … no symbol shape" | the field is new; `META_FIELDS` is closed → R3 bump | open |
| C2 | Out of scope | sed/awk slices | not here | constraint |
| C3 | Out of scope | a PreToolUse block | never blocks | constraint |
| C4 | Scope trailer | "Only the plugin packaging depends on 344" | stacked on 344 | met |
| R1 | Scope 1 | "A new optional `meta` field … Bump `contract_version` … extend the conformance suite" | `symbol_shapes`, v13 | open |
| R2 | Scope 1 | "each adapter encodes its language standard" | 4 adapters declare shapes | open |
| R3 | Scope 2 | "`code-atlas-nudge` console script … shipped in 344's plugin" | script + hook table | open |
| R4 | Scope 2 | "Parse surface, closed" | Grep fields; first `grep`/`rg`/`git grep` in Bash | open |
| R5 | Scope 2 | "Scope rule" | unscoped or overlapping suffixes fire | open |
| R6 | Scope 2 | "Rate-limited to once per kind per session … never blocks, always exits 0, silent with no index" | state file + gate | open |
| R7 | Scope 2 | "Each firing appends one line to the index's log" | H2 | open |
| AC1 | AC | replay table | unit + live | open |
| AC2 | AC | "fails when an in-tree adapter ships without symbol shapes" | live handshake per registered adapter | open |
| AC3 | AC | "The README tells a project … to remove it" | README line | open |
| AC4 | AC | "each firing writes its log line (kind, adapter, session)" | unit | open |

### AC validation

AC1–AC4 are falsifiable as written (replay inputs → fired/silent; a handshake without the field →
red; a README sentence; a log line). No value to recompute.

### Clarifications — 4, all self-resolved

1. Which shapes per adapter → each adapter's language standard (R2): declarations and qualified/bare
   calls of its own grammar. 2. How AC2 reads an adapter's shapes → its live `--server` handshake,
   per `tests/contract/adapter_registry.REGISTRY` (derived, R6.7). 3. v13's cost → one full rebuild
   per index, the price every bump pays (`contract.py` header). 4. Windows → the nudge is Python; the
   hook one-liner is 344's, with 344's exclusion.

### Universal inventory — N = 4 adapters (AC2)

php · python · sql · typescript — `gen_skill.shipped_adapters()`. Review confirms each.

### Blast radius

`contract.py` (`META_FIELDS`, `validate_meta`, `CONTRACT_VERSION`), `adapter.py` (a property),
`indexer.py` (two build paths pass the stamp), `store.py` (a meta key + reader), 4 adapter
handshakes, 6 tests pinning `CONTRACT_VERSION == 12`, `gen_skill.py` hook table (snippet + plugin),
`pyproject.toml` scripts. Docs: TOOLS.md hooks, contrib README, CONVENTION §3 vocabulary.

### Rule sections

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the scope rule is generic and names no language, §R1.4 (change-type) ✅ the nudge reads graph.db through GraphStore only, §R2.1 (change-type) ✅ each adapter declares its own grammar's shapes and no repo name, §R3.1 (change-type) ✅ contract_version 12 to 13 with the conformance suite extended, §R3.5 (change-type) ✅ the new meta key bumps contract_version which is the handshake's document, §R6.5 (change-type) ✅ the AC2 guard is seen red on an adapter without shapes, §R6.7 (change-type) ✅ the adapter set is derived from REGISTRY and shipped_adapters, §R7.6 (change-type) ✅ docs replaced where the snippet's hooks are described`

N/A: §4 because the build output rows do not change (a meta stamp only) · §8 because no dependency.

## Phase 2 — design

### Approach

1. **Contract v13.** `META_FIELDS` += `symbol_shapes`; `_check_symbol_shapes` validates W1 (kind in
   `SHAPE_KINDS`, `pattern` compiles, `scoped` a bool). `CONTRACT_VERSION = 13`.
2. **Adapters** declare shapes from their grammar and speak v13.
3. **Stamp.** `LanguageAdapter.symbol_shapes`; both build paths stamp
   `symbol_shapes_by_language` = `{name: {extensions, shapes}}` (sorted); `GraphStore.stamped_symbol_shapes()`.
4. **`code_atlas/hooks/nudge.py`** + `code-atlas-nudge`: parse (R4), scope (R5), match, rate-limit and
   log (R6/R7), emit `additionalContext` JSON. Exit 0 always.
5. **Wiring**: H10 in the shared hook table → snippet and plugin (344's drift test still holds).
6. **Tests**: contract validation + v13 pins; AC2 live-handshake guard per `REGISTRY` with a red
   control; nudge replay (AC1), rate limit, log (AC4), no index, never blocks.
7. **Docs**: TOOLS.md hook section, `contrib/claude-code/README.md` (AC3), CONVENTION vocabulary line.

### Rejected alternatives

- **Read shapes from the adapter entry files at hook time.** A tool install has no `adapters/` dir, and a regex over source is a text sweep (R6.7).
- **Spawn the adapter for its handshake per grep.** That means a PHP or Node start on every grep.
- **Core-side default shapes.** These would be a language table in the core (R1.1).

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| A1 | PostToolUse `additionalContext` JSON reaches the model | verified — spike (the JSON marker quoted back verbatim) |
| A2 | `Bash(grep *)` as a single-rule `if` matches a Bash call starting `grep` | novel-untested → the live replay (AC1) is shaped to fail if false |
| A3 | Grep tool input carries `pattern` / `path` / `glob` / `type` | novel-untested → the live replay logs the payload |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | v13 field + validation | `code_atlas/contract.py` | every handshake; 6 version pins | R1, C1 | 1/1 |
| 2 | property + stamp + reader | `code_atlas/adapter.py`, `code_atlas/indexer.py`, `code_atlas/store.py` | both build paths | R3 (H9) | 3/3 |
| 3 | shapes + v13 | `adapters/{php/index.php,python/index.py,sql/index.js,typescript/index.js}` | conformance suite | R2 | 4/4 |
| 4 | the nudge | `code_atlas/hooks/nudge.py`, `pyproject.toml` | new | R3–R7 | 2/2 |
| 5 | hook entries | `scripts/gen_skill.py` → snippet, plugin `hooks.json` | 344's plugin tests | R3, H10 | 3/3 |
| 6 | tests | `tests/test_symbol_shapes_contract.py`, `tests/test_grep_nudge.py`, `tests/adapter_cli.py` (a handshake helper), the 6 v12 pins | proof collateral | AC1, AC2, AC4 | — |
| 7 | docs | `docs/TOOLS.md`, `contrib/claude-code/README.md`, `docs/CONVENTION.md`, `docs/BACKLOG.md` (346), `docs/tasks/346_*.md` | doc budgets | AC3, W2 | — |

`HANDLES: 2 recalled | 0 traced (command + result) | 2 does not apply (reason) | 0 unanswered`

`formatter-rewrites-untouched-lines` does not apply because it names no producer to trace; it is
honoured at execute. `verify-the-shipped-artifact-not-the-working-tree` does not apply because it is a
verification step, not a producer or consumer; it is honoured by the live replay from a clone.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | runtime/3p | unit replay over the parse/scope rules + a live `claude -p` session that greps and quotes the nudge | authored | ✅ |
| AC2 | integration | live `--server` handshake of every registered adapter | n/a | ✅ |
| AC3 | logic | README sentence | n/a | ✅ |
| AC4 | logic | unit — log line fields | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_grep_nudge.py -k anchor_shapes_fire_once_per_kind` — fails
before (no module), passes after.

### Rollback

`git revert`; v13 → v12 is one more full rebuild. One repo.

`SCOPE: M`.

## Phase 3 — execute

Commits on `feat/345-symbol-search-nudge`: `04b20074` (contract v13, adapters, stamp, conformance),
`4c79540b` (the nudge + wiring + tests), `5c7aed9c` (docs, ticket 346), `7ddf1111` (PHP README).

**Live, from a clone of `5c7aed9c`** — `uv tool install` from the clone, an isolated
`CLAUDE_CONFIG_DIR` (credentials copied, then deleted), `/plugin install` from the clone's
marketplace, a fresh repo indexed with the Python adapter. A `Grep` for `def helper`; the model, asked
to quote any hook line:

```
code-atlas: this grep looks like a symbol search (declaration) — ask the index first (search_symbol / find_callers / find_references); keep Grep as the cross-check.
```

`.code-atlas/nudge.log`: `2026-09-29T13:06:48Z	9bf9510e-…	python	declaration`. A second session ran
`grep -rn -e 'helper(' . --include=*.py` through Bash (A2): the model quoted the `(call)` line, and
the log gained `…	python	call`.

**Unit and integration.** `tests/test_grep_nudge.py` has 13 tests: the AC1 replay, 7 never-fire
cases, the parse surface, the AC4 log, the no-index case, the exit-0 JSON contract, and a real build
that stamps the shapes the nudge then reads. `tests/contract/test_symbol_shapes.py` has 13 tests,
including a live handshake per registered adapter (AC2) and its red control.

**Two corrections made while testing, not deviations.** The parser first read a `grep` anywhere in a
command, so `cat x | grep …` fired. It now requires the command to *start* with a search, the same
test the hook's `if` makes. `--` (end of options) is also honoured: `grep -rn "->x("` is itself a
grep error, so real sessions write `-e`/`--`.

**Deviations** — none against the Gate-2 change list. Additions inside the list's "docs" item:
the PHP README handshake example (v12 → v13), and `docs/SKILL_GAP_CANDIDATES.md` SG-1/SG-2
(bookkeeping).

**Sweep — axis 2.** Approach 1–7 implemented as approved.
