---
id: 437
slug: sql-live-definition
title: "SQL: which definition of a multiply-defined routine is live, and a hash that ignores formatting"
phase: 2
milestone: "0.11 Verify & Compute"
status: in-progress
depends_on: [384]
---

## Why this exists

Roadmap R2 (0.11), and the prerequisite for 438's SQL rows and 440/441's `multi_defined` and
absence templates. On the maintainer's anchor (survey 2026-11-07, counts only), **161 of 389 SQL
routines are defined more than once** — migrations re-issue `CREATE OR ALTER`, a snapshot holds a
copy — and nothing says which definition is the one the database runs. Today a reference to one of
them can only resolve `ambiguous`, and a "what does X do" answer may read a superseded body.

`adapters/sql/src/bodyHash.js` (384) drops comments and collapses whitespace per line, so a
keyword-case change, `[bracket]` quoting, `CREATE OR ALTER` vs `CREATE` or a reflowed statement
still moves the hash. Identical routines then look changed, and 438's `body_hash` successor match
misses them.

## Scope

1. **Definition order.** The SQL adapter emits a generic `definition_ordinal` per definition. The
   ordering comes from a per-repo rule, e.g. `sql.definition_order = ["migration:V<n>", "snapshot",
   "other"]` — the adapter parses the version from the path by the rule's pattern; the core only sorts
   (R1.1). The highest ordinal is `live`; the others carry `superseded_by`.
2. **The rule is a non-command `.code-atlas.toml` key** (430): a list of path patterns, never a
   command, validated by `config.py` like every other knob.
3. **Hash normalization** in `bodyHash.js` before digesting: keyword case, `[bracket]` / `"quoted"`
   identifiers that need no quoting, `CREATE OR ALTER` → `CREATE`, and whitespace across line breaks
   (reflow). A literal's text stays as written.
4. **Contract**: a new field or vocabulary is R3 — bump `contract_version`, conformance tests, and
   say in the release note that every stored SQL `body_hash` moves once (a 384 snapshot taken before
   reports SQL symbols changed after the upgrade).

**Decision already taken** (roadmap §4.6, maintainer may override at the gate): ordering by migration
version is a per-repo config rule, not a built-in convention (R2).

## Acceptance

1. Fixtures: a routine defined in three migrations and a snapshot has exactly one `live` definition,
   the highest-versioned migration; the others name it in `superseded_by`.
2. With no rule configured, nothing is `live` and multi-definition stays reported as ambiguous —
   an unknown is never `ok` (R5.6).
3. Formatting-only variants (case, brackets, `OR ALTER`, reflow) keep their hash; a changed predicate
   or column list moves it.
4. A toml value that is not a list of strings fails loud, naming the key.
5. Anchor (privacy rules in 442): each of the 161 multiply-defined routines has exactly one `live`
   definition — counts only, reported to `~/code-atlas-review/`.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 437 · **work_doc_mode:** embed · **Current phase:** 5 finalise — the PR is open; merging is the maintainer's.
- `TRACK: backend` · Run mode: `autorun 437 - 438 - 440`, first — `REVIEWER: ON` · `CHALLENGER: ON` · `cost_tier: standard`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/437-sql-live-definition` from `main` at `63991c1b`. Contract `.mango/run-contract-437.txt`. RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run`. Budget: unknown.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 0 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 4 unresolved surfaced | 2 want-decision asked | 2 how-decision resolved+cited | 2 ASSUMED | skip: no`

`adapters/sql/src/bodyHash.js`, `code_atlas/config.py`, `code_atlas/contract.py`, 384's `symbol_changes.py`, 403's
`latest_migration_first` and 414's `precedence_first` (`code_atlas/tools/symbol_pointers.py`) resolve. Recalled by area: 403
(a built-in Flyway reading answers `read_symbol`) and 414 (a rules-file `definitions.precedence`, path globs, already the
one seam every reader of several definitions applies, R1.8). The ticket names neither.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the order is computed | how | in the core, on the stored path: the rule is a repo's own layout, which R2 keeps out of adapters ("never a repo's names"), and matching a path glob is language-free (R1.1). Handing config to an adapter would be a second protocol channel (R1.2). The ordinal is derived, never stored. |
| H2 | one rule or two | how | 414's precedence is the same question ("which definition answers"). The rule is 414's glob list gaining a `<n>` version token; the toml knob and the rules file feed one reader, toml first, so `read_symbol`, `impact`, `search_symbol` and the new states agree (R1.8). |
| W1 | scope 1 says the *adapter* emits `definition_ordinal` | want | **ASSUMED (awaiting ratification):** H1 — the core derives it. Nothing in the adapter output changes but the hash. |
| W2 | scope 4's `contract_version` bump | want | **ASSUMED (awaiting ratification):** no bump in this PR. A bump needs a tagged release (`test_release_discipline.py`), and 438 adds a handshake field that owes one too: one bump for 0.11, at its release, as 417 and 432 did. CHANGELOG *Unreleased* flags the one-time SQL `body_hash` move and the `--full` it needs. |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=2 R=4 G=1 AC=5`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

W1 and W2 count as self-resolved because the handover handed them back; they stay `ASSUMED` until ratified.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "nothing says which definition is the one the database runs" | a declared rule names one live definition | ⚠ |
| C1 | Scope 1 | "the core only sorts (R1.1)" | no language branch; path globs only | ⚠ |
| C2 | Scope 2 | "a list of path patterns, never a command" (430) | globs, validated by `config.py` | ⚠ |
| R1 | Scope 1 | "highest ordinal is `live`; the others carry `superseded_by`" | `definition_states()` | ⚠ |
| R2 | Scope 2 | "non-command `.code-atlas.toml` key" | knob `definition_order` | ⚠ |
| R3 | Scope 3 | "keyword case, `[bracket]` / `"quoted"` … `CREATE OR ALTER` → `CREATE`, … reflow" | `bodyHash.js` normalisation | ⚠ |
| R4 | Scope 4 | "say in the release note that every stored SQL `body_hash` moves once" | W2 | ⚠ |
| AC1 | Acc 1 | "three migrations and a snapshot has exactly one `live` definition" | fixture through the real adapter | ⚠ |
| AC2 | Acc 2 | "With no rule configured, nothing is `live`" | states `unranked`; `read_symbol` unchanged | ⚠ |
| AC3 | Acc 3 | "Formatting-only variants … keep their hash; a changed predicate or column list moves it" | adapter fixture | ⚠ |
| AC4 | Acc 4 | "A toml value that is not a list of strings fails loud, naming the key" | `ConfigError` | ⚠ |
| AC5 | Acc 5 | "each of the 161 multiply-defined routines has exactly one `live` definition" | anchor run, counts only | ⚠ |

`BASELINE: green — tests/test_definition_precedence.py, test_definition_precedence_rules.py, test_read_symbol_latest_migration.py, test_symbol_changed_since.py, test_config.py on main at 63991c1b: 108 passed`

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 no language branch, R1.2 one seam, R1.8 one rule · §2 (change-type) ✅ R2 the repo's layout stays out of the adapter · §3 (change-type) ✅ R3.1 owed at the release (W2) · §6 (change-type) ✅ R6.5 each new test seen red · §7 (change-type) ✅ R7.2, R7.5, R7.6`

## Phase 2 — design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**Approach.**
1. `symbol_pointers.py`: a precedence glob may carry one `<n>` — a dotted or underscored version read from the path.
   One rank function: `(glob position, version)`. `precedence_first` takes the unique best rank (a tie answers
   nothing, as today), and new `definition_states(rows, precedence)` returns per row `definition_ordinal`, `state`
   (`live` · `superseded` · `unranked` · `test_copy`) and `superseded_by`. No rule, a tie, or a cut fetch: nothing is
   `live` (R5.6).
2. `config.py`: knob `definition_order`, a list of path globs; in the toml anything but a list of non-empty strings is
   a `ConfigError` naming the key; more than one `<n>` in a glob fails loud. The rules file's `definitions.precedence`
   takes the same check.
3. `enrichment.py` / `indexer.py`: the knob is stored in its own meta key on every build; `declared_precedence` reads
   toml first, then the rules file.
4. `bodyHash.js`: outside literals — lower-case, unquote a `[x]` / `"x"` that is a regular identifier, drop `OR ALTER` /
   `OR REPLACE` after `CREATE`, and emit a space only between two word characters, line breaks included. Lines become
   composable polynomial hashes (three moduli below 2^26, so the arithmetic is exact), so a span hashes as one stream and
   the file is still never held as text. A literal keeps its text.
5. Docs: CHANGELOG *Unreleased* (rebuild flag, W2), `docs/TOOLS.md` precedence section, `adapters/sql/README.md`.

**Rejected:** the adapter computing the order — it would need the repo's rule (R2) over a new channel; a second,
separate "live" rule beside 414 — two answers to one question (R1.8); keeping the file's normalised text to re-hash a
span — the scanner exists not to hold the file.
**Change list:** `code_atlas/tools/symbol_pointers.py`, `code_atlas/config.py`, `code_atlas/enrichment.py`,
`code_atlas/indexer.py`, `adapters/sql/src/bodyHash.js`, new `tests/test_definition_order.py`, new
`tests/test_sql_body_hash_normalised.py`, `CHANGELOG.md`, `docs/TOOLS.md`, `adapters/sql/README.md`; bookkeeping
(`docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md`, this file).
**Proving test:** `tests/test_definition_order.py` (AC1, AC2, AC4); `tests/test_sql_body_hash_normalised.py` (AC3).

`EXCLUSIONS: 4 recorded | 4 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 1 proven on a real corpus`

- E1 — AC5 runs on the maintainer's anchor; **expiry:** the anchor count is recorded in
  `~/code-atlas-review/437-anchor.md` before the PR opens, or this row says why not.
- E2 — W1: the core derives `definition_ordinal`, the adapter emits none (scope 1 says the adapter). Approved under the
  handover's delegated decisions, not at a gate; **expiry:** the maintainer ratifies or rejects W1 on the PR before merge.
- E3 — W2: no `contract_version` bump in this PR (scope 4); BACKLOG *Follow-ups* names the 0.11 release as its owner.
  Approved under the handover; **expiry:** ratified on the PR before merge, and the bump lands at the 0.11 release.
- E4 — W3: the knob is `definition_order` with path globs and one `<n>`, not `sql.definition_order` with
  `migration:V<n>` labels: core config carries no language name (R1.1), and 414's globs already were the form. Approved
  under the handover; **expiry:** ratified on the PR before merge.

## Phase 3 — execute

Main loop, no `implementer` dispatch: `764f118e`. **Verification sweep.** File axis: `git diff --stat main` names
`adapters/sql/src/bodyHash.js`, `adapters/sql/README.md`, `code_atlas/config.py`, `code_atlas/enrichment.py`,
`code_atlas/indexer.py`, `code_atlas/tools/symbol_pointers.py`, `docs/TOOLS.md`, `CHANGELOG.md`, the two new tests and
`tests/test_config.py` — the last off the list: it pins the knob list and count (24 → 25), which a new knob must move.
Behaviour axis: as approved. **Design conformance:** H1 (core-side, no language branch), H2 (one reader, toml first).

**R6.5 seen red** on `main`'s code (a worktree at `63991c1b` with only the two new tests copied in): the hash test fails
5 of 6 formatting variants (comments alone already held); the order test cannot import `definition_states`.

**AC5 (E1 discharged)** — `~/code-atlas-review/437-anchor.md`, counts only: 621 SQL routines, 161 defined more than
once (the survey's figure); a 7-glob rule shaped on the anchor's layout gives **160 / 161** exactly one `live`; the one
left is two definitions in one plain directory — a tie, `unranked`, never a guess.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. Review step: mango `reviewer` (Sonnet), round 1, at `791eb36b`.

- **`reviewer` round 1** (67,075 tokens): CHANGES REQUESTED → conditional LGTM on findings 1–2. It verified the
  exact-arithmetic claim (every product < 2^52), 414's semantics unchanged for globs without `<n>`, and that a toml
  edit reaches meta on an incremental build (`_record_meta`).
  - **1, taken:** `CREATE OR` / `ALTER` split across lines kept two hashes. Two causes: the clause was matched per
    line, and the scanner starts the span at the `ALTER` line. The word sequence now carries across lines, and a span's
    opening verb (`create` / `alter`) is not hashed — so `ALTER PROCEDURE` ≡ `CREATE PROCEDURE` too. Lesson 437-C1.
  - **2, taken as an owner, not a bump:** W2 stays `ASSUMED`; BACKLOG *Follow-ups* now names the one bump the 0.11
    release owes for 437 + 438. CHANGELOG keeps the rebuild flag.
  - **Minors taken:** `FROM[dbo]` is `FROM dbo`; the glob reader fails loud if `fnmatch.translate` changes shape, and a
    `<n>` inside `[...]` is refused. **Not taken:** wiring `definition_states` into a tool here — 438 (`verify_refs`'
    SQL rows) and 441 (`multi_defined`) are its consumers; `read_symbol` already answers the live definition.
- **`challenger` round 1** (64,148 tokens, ticket-blind): 5 met · 2 partly · 2 not met · 1 can't tell (AC5, off-diff).
  The two "not met" are W1 (the core derives the ordinal) and W2 (bump deferred) — recorded decisions, not defects.
  **Taken:** `N 'x'` (a column and its alias) no longer hashes as `N'x'`. **Not taken:** keeping `[select]` apart from
  `select` — a bare reserved word where a delimited one stood is not valid T-SQL, so no real pair of bodies collides.

- **`challenger` round 2** (54,100 + 57,063 tokens, ticket-blind, at `190faffc`, after `read_symbol` gained
  `definition_state` / `superseded_by`): first pass 3 met · 5 not met · 1 can't tell; asked to re-read rows 7–8 (it had
  grepped only `tests/test_config.py`), it corrected both to met. Its final table, transcribed:

`CHALLENGER VERDICT: 9 requirement(s) rebuilt | 5 met | 3 not met | 1 can't tell | 3 not-met covered by a recorded exclusion`

The three not met are W1 (row 1, the core derives the ordinal), W3 (row 3, the key is `definition_order`, globs, not
`sql.definition_order` / `migration:V<n>` — a language name in core config is R1.1's leak) and W2 (row 5, bump deferred):
E2–E4, approved under the handover, not at a gate. The can't-tell is AC5, off-diff, held by E1's anchor report.

**Gate 4 does not close by the harness's arithmetic** (`m + g = 8 ≠ 9`: AC5's can't-tell), and E2–E4 await the
maintainer. No code change can close either without reversing a delegated decision, so the PR opens as a **draft**
naming this first; the reviewer's conditional LGTM stands, its findings 1 and 2 landed. `Ph3/4 proven by`: AC1, AC2, AC4 → `tests/test_definition_order.py`;
AC3 → `tests/test_sql_body_hash_normalised.py` (19 variants, the reviewer's and challenger's cases included); AC5 →
`~/code-atlas-review/437-anchor.md`; G1 → AC1 + AC5.

## Phase 5 — finalise

**Durable lesson.** 437-C1 `a-fingerprint-is-taken-over-the-span-the-scanner-names` (new, type 2).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

**The final gate.** Run 1 at `b3243948` was RED on one check: `test_guardrail_gates.py` allows one `--file` adapter
spawn (`tests/adapter_cli.py`), and the hash test spawned its own — moved onto the helper (`3e138aec`). Run 2 at
`3e138aec` was green; round 2 then added `read_symbol`'s fields, so run 3 covers the final tree:

Ran at 379528d0

```
$ scripts/gate.sh
26 passed · 0 failed · 0 skipped
GATE GREEN — all 26 checks passed
```

### Outward actions

Under the handover: push `feat/437-sql-live-definition`; open its PR against `main`. Deferred to the maintainer:
ratify W1 and W2; merge; the 0.11 release's contract bump.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 4 review | rule-book `reviewer` | 1 | 67,075 |
| 4 review | ticket-blind `challenger` | 1 | 64,148 |
| 4 review | ticket-blind `challenger` | 2 | 111,163 |

`LEDGER TOTAL: 242,386 · top cost driver: 4 review / challenger` — main loop unmeasured.
