---
id: 372
slug: python-keyword-arguments-record-no-args
title: 'A Python keyword argument records no args entry, so arg_is and keyed_calls rules cannot read it'
phase: 2
milestone: Coverage
status: done
depends_on: [049, 352, 364]
---

## Why this exists

Split from 367. Measured with `adapters/python/index.py --file` on 2026-10-08: `Foo(a=1, b='b')`
emits `args: []`. `contract.py`'s `args` is positional, so a keyword argument is invisible to
`arg_is` (049), to a `keyed_calls` rule's `key_arg` (352/364), and to 367's construction sites.
Keyword arguments are the common Python call shape, so this caps every argument-reading tool there.

## Scope

1. Design settles the shape against `contract.py` before code: a parallel keyword map, or named
   entries in `args`. Either may move the contract — then R3 applies (version bump, conformance
   tests, release), decided in design, not assumed.
2. A `keyed_calls` rule can name a keyword (`key_arg` by name) only if design adds it; `arg_is`
   gains the same reach.
3. Python only: TS has no keyword arguments; PHP 8 named arguments are a follow-up if design keeps
   the shape language-neutral.

## Acceptance criteria

- **AC1:** `Foo(a=1, b='b')` records both arguments with their shapes.
- **AC2:** `arg_is` narrows `find_callers` by a keyword argument's shape.
- **AC3:** A positional-only call's `args` are byte-identical to today's.
- **AC4:** If the contract moves, `contract_version` is bumped and the conformance suite covers it.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 372 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges #44–#49, then this PR, then tags 0.3.0. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`, batch 367 → 368 → 369 → 370 → 373 → 371 → 372;
  *"with skipped reviewers"* = `--no-reviewer` only (AGENTS.md), the challenger keeps its seat.
- Branch `feat/372-python-keyword-arguments-record-no-args`, stacked on `feat/371-sql-statement-in-a-host-string-beyond-php`
  (a contract bump cuts the release, so it goes last); its PR targets that branch. Contract `.mango/run-contract-372.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 9 unresolved surfaced | 1 want-decision asked | 8 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Premise.** `contract.py`'s positional `args` and `arg_keys`, `store._args_predicate`,
`find_callers._args_at`, `count_edges_without_args` and `enrichment.py`'s `key_arg` all resolve;
`--file` confirmed `Foo(a=1, b='b')` emits `args: []`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 45,403 tokens) surfaced X1–X8; the
main loop added X9.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | a `keyed_calls` rule naming a keyword | want | **ASSUMED (delegated by the handover):** not in this change — `arg_is` gains the reach (AC2); `key_arg` by name is filed in BACKLOG Follow-ups |
| X2 | shape | how | a parallel `kwargs` map, never named entries in `args`: a positional reader would misread them (R1.7, sibling key) |
| X3 | the contract moves | how | yes: a new edge field — contract 14, schema 7 (a column), release 0.3.0 flagging the rebuild (R3.1, R3.5) |
| X4 | validation, an old index | how | `_check_kwargs`; a schema-6 index refuses and rebuilds (`SchemaVersionError`, PLAN §10) |
| X5 | the filter's blind spot | how | an edge with no `kwargs` is `args_unrecorded`, never a non-match (`count_edges_without_args(keyword=True)`) |
| X6 | the tool surface | how | a separate `arg_name`, exclusive with `arg_position` (R5.3: fail loud on both) |
| X7 | `**` spreads, non-literals | how | a spread records no `kwargs` (unknown); a non-literal value is `null`, as in `args` |
| X8 | mixed calls | how | positionals stay in `args`, keywords in `kwargs`; a positional-only call records `kwargs: {}` |
| X9 | `absent` on a keyword | how | "not passed by that keyword" — a positional value counts as absent (docstring, TOOLS.md) |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=4`
`CLARIFICATION: 9 raised | 9 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/40 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

The base is 371's tip. `scripts/gate.sh` on `main` (`e0d84cf1`): `GATE GREEN — all 21 checks passed`.
Ran at e0d84cf1.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "caps every argument-reading tool there" | a keyword argument is readable | ✅ |
| C1 | Scope 3 | "Python only" | the shape language-neutral, filled by Python | ✅ |
| R1 | Scope 1 | design settles the shape; R3 if it moves | X2/X3 | ✅ |
| R2 | Scope 2 | `keyed_calls` by keyword only if design adds it; `arg_is` gains the reach | X1 | ✅ |
| R3 | Scope 3 | PHP 8 named arguments a follow-up | BACKLOG | ✅ |
| AC1 | AC | `Foo(a=1, b='b')` records both with shapes | | ✅ |
| AC2 | AC | `arg_is` narrows `find_callers` by a keyword | | ✅ |
| AC3 | AC | a positional-only call's `args` byte-identical | | ✅ |
| AC4 | AC | `contract_version` bumped, conformance covers it | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `{"a": "number", "b": "string"}`; a spread records none | |
| AC2 | yes — `number` → `by_keyword`, `dynamic` → `by_variable`, `absent` → `by_position`; the spread is unrecorded | |
| AC3 | yes — `args`/`arg_keys` equal 371's output for the same call | |
| AC4 | yes — `CONTRACT_VERSION == 14`, `EDGE_FIELDS` pinned, `_check_kwargs` rejects a bad category | |

### Blast radius

- The contract, the edge table, `find_callers`' filter, every adapter's handshake version, release
  0.3.0 (pyproject, plugin manifest, hooks, snippet, marketplace via `scripts/gen_skill.py`).
- P5 count-pins: 15 test files pin `CONTRACT_VERSION == 13` (two also `SCHEMA_VERSION == "6"`), and
  `test_contract_schema.py` lists `EDGE_FIELDS` — all moved in the change list.

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.7 (change-type) ✅ a sibling field, positional args untouched · §R3.1 (change-type) ✅ contract 14 + conformance + release 0.3.0 · §R3.2 (change-type) ✅ EDGE_FIELDS drives the column list · §R3.5 (change-type) ✅ contract and schema each bumped for their own document · §R5.3 (change-type) ✅ arg_position with arg_name, or a bad name, fails loud · §R5.6 (change-type) ✅ unrecorded kwargs counted apart, never a miss`

## Phase 2 — design

### Approach

1. `contract.py`: `kwargs` in `EDGE_FIELDS`, `KWARGS_FIELD`, `_check_kwargs`, contract 14.
2. `store.py`: an `edges.kwargs` column, schema 7; `_kwargs_predicate` (a keyword in place of the
   position); `count_edges_without_args(keyword=…)`.
3. `find_callers`: `arg_name`; `_by_name` routes the unrecorded count.
4. Python adapter: `kwargs` at every call site it records arguments for; all adapters announce 14.
5. Version pins, release 0.3.0 (`scripts/gen_skill.py --write`), docs, a parity row.

### Rejected alternatives

- **Named entries appended to `args`** — every positional reader (`arg_position`, `key_arg`) would read
  a keyword as a position (R1.7).
- **No schema bump (a JSON blob in an existing column)** — no column fits; a field is a field (R3.1).

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | field + validator | `code_atlas/contract.py` | every adapter | R1, AC4 | 1/1 |
| 2 | column, predicate | `code_atlas/store.py` | every index (rebuild) | AC2 | 1/1 |
| 3 | `arg_name` | `code_atlas/tools/find_callers.py` | tool schema | AC2 | 1/1 |
| 4 | `kwargs` + handshake | `adapters/python/{index.py,src/parse.py}`, `adapters/{php/index.php,typescript/index.js,sql/index.js}` | all adapters | AC1, AC3, C1 | 5/5 |
| 5 | proving test | `tests/test_python_keyword_arguments.py` (new) | — | AC1–AC4 | 1/1 |
| 6 | pins (P5) | 15 test files, `tests/contract/test_contract_schema.py` | — | AC4 | 16/16 |
| 7 | release | `pyproject.toml`, `CHANGELOG.md`, `contrib/claude-code/**`, `.claude-plugin/marketplace.json` | `test_release_discipline` | AC4 | 6/6 |
| 8 | docs + parity | `docs/{CONVENTION,PLAN,TOOLS,ADAPTER_PLAYBOOK}.md`, `docs/design/storage.md`, Python/PHP READMEs, `scripts/adapter_parity_report.py` | doc budget | R2, R3 | 8/8 |
| 9 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1, AC3 | adapter | `--file` edges | authored | ✅ |
| AC2 | integration | real Python build, `find_callers` | authored | ✅ |
| AC4 | contract | `contract.validate`, the schema pins, release discipline | — | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_python_keyword_arguments.py`.

### Rollback

`git revert`; an index built at schema 7 then refuses and rebuilds at 6.

## Phase 3 — execute

Commit `92f1289c`. **Red first** — the proving test on 371's tip: `4 failed` (no
`kwargs`, no `arg_name`). **P8:** `cross_repo_validate.py --public-only --skip-clone` with `CA_*_CMD`
unset, 11 ok / 0 failed; every count equals 371's (`kwargs` rides an existing edge).

**Sweep.** Axis 1: `git diff --name-only feat/371-sql-statement-in-a-host-string-beyond-php..HEAD` = items
1–8; `ruff check`, `mypy` (core, Python adapter), `tsc` clean. The full suite in this worktree's own
venv with `CA_*_CMD` unset: `3 failed, 4328 passed` on the first run — a vocabulary count-pin and
the brief's parameter gate (P5 misses), fixed in `5b3acd11`. Axis 2: as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `44d935fb` — `92f1289c` after the rebase —, 84,971 tokens): 5 met · 0 not met · 3 can't tell.**

1. **F1: `test_schema_version_recovery` failed in its run.** **Not a defect:** it passes in a venv
   bound to this tree; the run imported the main checkout's `code_atlas` (v13) in a child process.
2. **F2: PLAN and the PHP README showed `contract_version` 13.** **Fixed.**
3. **F3: no parity row says which adapters record `kwargs`.** **Fixed** — a ratio row, PHP 0/1 (PHP 8
   named arguments, a follow-up), TS/SQL 0/1 (no keywords), Python 1/1.
4. **F4 (can't tell, Scope 2): `keyed_calls` by keyword.** Decided out (X1) and filed in BACKLOG.
5. **F5: `absent` on a keyword reads a positional value as absent.** **Documented** (docstring, TOOLS.md).
6. **F6: no `total_count` under a keyword filter.** **Fixed.**
7. **F7: a mis-indented block.** **Fixed.**

Fixes in `9b06622c` and `5b3acd11`. Verify-only (main loop):

Ran at 5b3acd11:
```
$ .venv/bin/python -m pytest -q tests/test_python_keyword_arguments.py
4 passed
```

`Ph3/4 proven by`: G1, C1, R1–R3, AC1–AC4 — 8/8.

Verdict: **clean (challenger only — REVIEWER: OFF)** — every can't-tell resolved or decided.

Reviewed at 5b3acd11 — the diff `feat/371-sql-statement-in-a-host-string-beyond-php..5b3acd11`. Working doc:
`docs/tasks/372_python-keyword-arguments-record-no-args.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `5b3acd11` only bookkeeping changes — this doc, `docs/BACKLOG.md` and
`docs/TOKEN_LEDGER.md`, all exempt.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

No new lesson. The P5 misses (a vocabulary pin, the brief's parameter gate) are the rule's own class.

### Outward actions

1. Push `feat/372-python-keyword-arguments-record-no-args` — pre-authorised.
2. Open the PR against `feat/371-sql-statement-in-a-host-string-beyond-php` — pre-authorised.

Deferred to the maintainer: tagging and publishing 0.3.0 after the stack merges.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 45,403 |
| 2 | review | `challenger`, round 1 | 84,971 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 130,374 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits; the release entry goes with them.

**Gate.** `scripts/gate.sh` on `3158e44a`: `GATE GREEN — all 21 checks passed` (Linux, bare pytest).
