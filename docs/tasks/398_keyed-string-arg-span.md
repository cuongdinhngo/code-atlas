---
id: 398
slug: keyed-string-arg-span
title: 'A keyed_calls string key is read from the call''s first line, so a wrapped call names no key and nothing counts the miss'
phase: 2
milestone: Coverage
status: done
depends_on: [222, 352, 364]
---

## Why this exists

This comes from the anchor project (2026-10-17). Its draft `keyed_calls` rules map a data-access
helper's first argument to a table write: `insertRow('Items', $row)` → WRITES `dbo.Items`.
`key_from: "string"` re-reads the source line at the edge's `line` and splits the arguments of the
one `<callee>(` on it (`enrichment.py:519-555`).

- F1: a call wrapped after `(`, or with the key on a later line, returns `None` from
  `_call_argument`, so the site emits nothing. The anchor's setup doc has to warn "only when the call
  is one line"; `find_references` on the table lists fewer writers and still says only
  `authoritative: false`.
- F2: two calls of one callee on a line also return `None` (352). Neither miss is counted, so a
  rule's coverage cannot be measured.
- `key_from: "array_keys"` has no such limit: the adapter captures `arg_keys` (063).

## Scope

1. Adapters that already advertise the `args` capability also capture a string literal's value
   for a `string` arg (e.g. `arg_strings`, parallel to `args`), so the key is read from the edge.
   A contract change: bump the version and say so.
2. `key_from: "string"` reads the captured value first and falls back to today's line read for an
   index built before the bump.
3. A `keyed_calls` rule may name its key by keyword (`key_kw`), and the PHP adapter reads PHP 8
   named arguments into `kwargs` — the line read could not see either (372's follow-up).
4. Each `keyed_calls` rule reports how many of its call sites had a string arg at `key_arg` but
   named no key (`keys_unread`), in the build report and `get_index_status`.

## Acceptance criteria

- **AC1:** PHP fixture `insertRow(\n  'Items',\n  $row\n)` under a WRITES rule: `find_references`
  on `dbo.Items` lists the site.
- **AC2:** Two calls of the callee on one line: both sites are linked.
- **AC3:** `insertRow($table, $row)`: no edge, and `keys_unread` counts it only if arg 1 was a string
  literal (here it is not, so 0).
- **AC4:** `insertRow(row: $row, table: 'Items')` under `key_kw: "table"`: the site is linked.
- **AC5:** An index built before the bump still answers single-line sites exactly as today.

- **AC-field:** on the anchor index, the writers listed for three tables known to be written by
  wrapped helper calls; record the before/after counts in the working doc.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 398 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W6, runs E1, rebuilds `--full`, then merges after 396 and 397. **Revert path:** `git revert` the branch's commits; a contract-15 server needs a full rebuild again.
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · `STRUCTURE: native` · Run mode: `autorun 396 - 398 - 397 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/398-keyed-string-arg-span`, **stacked on `feat/397-routes-from-source`** (so release 0.5.0 carries 396 and 397 too). Contract `.mango/run-contract-398.txt`.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 14 unresolved surfaced | 6 want-decision asked | 8 how-decision resolved+cited | 6 ASSUMED | skip: no`

**Premise.** `_call_argument` (`enrichment.py:519-555`), the `args` capability on all four adapters, `arg_keys`
(063) and `kwargs` (372) resolve. Ambiguous: "the anchor index".

**Recall (by handle).** `read-a-literal-by-its-structure-not-a-regex` (361-C1): the value comes from the parser's
literal node, never a regex over the line. `widen-every-query-that-shares-the-page` (362-C1): every reader of a
string key — `keyed_calls` and `view_data` share `_keys_for_rule`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 59,217 tokens) raised twelve; they are H1–H8 and W1–W5.
It ran after the code was drafted, not before; its item 2 changed the code (a `key_pattern` refusal is not unread).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | which value | how | the parser's decoded value of a plain literal; an interpolated string, an f-string, a template with a substitution or bytes has none (361-C1) |
| H2 | which adapters | how | all four, as Scope 1 says ("adapters that already advertise `args`") |
| H3 | the shape | how | `arg_strings` parallel to `args`, `kwarg_strings` keyword → value, each omitted when nothing was captured — sibling keys, R1.7 |
| H4 | a captured null | how | an adapter emits `arg_strings` whenever a `string` is passed, so a null means "no value" and is never re-read from the line; only an absent field (an older index) falls back to it (AC5) — changed after the challenger's M1 |
| H5 | a pre-bump index | how | the same fallback; its misses count as unread like any other |
| H6 | which sites are unread | how | a `string` category at the key and no key read; a `key_pattern` refusal is no route and is not counted (`TOOLS.md`, 361) |
| H7 | `keys_unread` beside the other counters | how | its own per-rule list; `rule_keys_unresolved` / `rules_unresolved` unchanged |
| H8 | where it surfaces | how | `BuildReport.keys_unread` and meta `keyed_calls_keys_unread`, which `get_index_status` (standard) lists; rewritten whenever the rules are applied |
| W1 | a cap on stored values | want | **ASSUMED (awaiting ratification):** 256 characters; a longer literal has no value and counts in `keys_unread` |
| W2 | `view_data` rules | want | **ASSUMED (awaiting ratification):** they read the captured value too — one reader (R1.8), so a wrapped `assign(…)` starts publishing its key |
| W3 | `key_kw` with `key_arg` | want | **ASSUMED (awaiting ratification):** the keyword first when the call passes it, else `key_arg`; `key_arg` becomes optional |
| W4 | PHP named arguments and `args` | want | **ASSUMED (awaiting ratification):** `args` keeps the positional prefix (it was voided), named ones go to `kwargs`, and every PHP call site records `kwargs` (`{}` when none) |
| W5 | AC-field (anchor) | want | **ASSUMED (awaiting ratification):** E1, the maintainer's standing answer of 2026-10-17 |
| W6 | SQL's share of Scope 1 | want | **ASSUMED (awaiting ratification):** the SQL scanner masks a literal's body before it reads EXEC args (`scan.js`, 022), so SQL captures no value and keeps the line read — a deviation from Scope 1 (P3), found at review |

## Phase 1 — analysis

`PREMISE: 5 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=4 G=1 AC=6`
`CLARIFICATION: 14 raised | 14 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/26 touched files under UI paths`
`BASELINE: green`
`SCOPE: L`
`TIER: full`

### BASELINE

`main`'s full suite: `4697 passed, 4 skipped, 1 xfailed in 573.67s (0:09:33)`. Ran at 60d802c5 (the 396 run's baseline;
this branch starts from it).

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a rule's coverage cannot be measured" | read every site, count the rest | ⏳ |
| C1 | AC5 | "still answers single-line sites exactly as today" | the line read survives as the fallback | ⏳ |
| R1 | Scope 1 | "also capture a string literal's value … bump the version" | H1–H3, contract 16, schema 8, release 0.5.0 | ⏳ |
| R2 | Scope 2 | "reads the captured value first and falls back" | H4, H5, W2 | ⏳ |
| R3 | Scope 3 | "`key_kw` … PHP 8 named arguments into `kwargs`" | W3, W4 | ⏳ |
| R4 | Scope 4 | "`keys_unread`, in the build report and `get_index_status`" | H6–H8 | ⏳ |
| AC1–AC5 | AC | wrapped · two on a line · variable · named · pre-bump | | ⏳ |
| AC6 | AC-field | anchor | W5 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1–AC4 | yes — a writer row, or a count | |
| AC5 | yes — the existing keyed_calls / view_data suites unchanged | the fallback path |
| AC6 | no — the anchor | E1 |

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ no language branch: the core reads two contract fields · §R1.7 (change-type) ✅ values ride sibling keys, args categories untouched · §R1.8 (change-type) ✅ view_data and keyed_calls share one reader · §R2.1 (change-type) ✅ PHP 8 named arguments per the language spec · §R3.1 (change-type) ✅ contract 16, schema 8, release 0.5.0 with a rebuild entry · §R6.6 (change-type) ✅ PHPStan max and tsc clean · §R7.6 (change-type) ✅ TOOLS.md and the playbook edited in place, the one-line limits removed`

## Phase 2 — design

### Approach

1. Contract 16: `arg_strings` / `kwarg_strings` in `EDGE_FIELDS` with validators; schema 8 stores them.
2. Adapters: PHP, Python and TypeScript emit the values (SQL emits none, W6); PHP reads named arguments into `kwargs`.
3. `enrichment.py`: `_keys_for_rule` reads `key_kw`, then the captured value, then the line; `keyed_calls` counts
   `keys_unread` per rule; the loader accepts `key_kw`.
4. `indexer.py` / `get_index_status.py`: the census in the report, meta and status.
5. Release 0.5.0: version files, hook pins, CHANGELOG, the release-discipline xfail.

### Rejected alternatives

- **Re-reading several lines from disk** — still blind to two calls on a line, and the line read is what drifts.
- **Capturing only in PHP** — Scope 1 names every `args` adapter.

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | contract 16 | `code_atlas/contract.py` | every adapter's handshake; conformance | R1 | 1/1 |
| 2 | schema 8 | `code_atlas/store.py` | every index rebuilds | R1 | 1/1 |
| 3 | adapters | `adapters/{php,python,typescript}/…` (index + parser), `adapters/sql/index.js` (version only, W6) | their edges | R1, R3 | 3/4 (W6) |
| 4 | the reader and census | `code_atlas/enrichment.py`, `code_atlas/indexer.py`, `code_atlas/tools/get_index_status.py` | rule edges | R2, R4 | 3/3 |
| 5 | release | `pyproject.toml`, the plugin and marketplace manifests, hook pins, `CHANGELOG.md` | release-discipline tests | R1 | 6/6 |
| 6 | tests | `tests/test_keyed_string_arg_span.py` (new); 19 version, shape and parity pins (P5), found by the full suite | — | AC1–AC5 | 20/20 |
| 7 | docs | `docs/TOOLS.md`, `docs/ADAPTER_PLAYBOOK.md` (row, parity table) | doc budgets | G1 | 2/2 |
| 8 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC4 | integration — PHP + SQL adapters + build + tool | real build, `find_references` | authored | ✅ |
| AC5 | integration | existing keyed_calls / view_data / route suites | existing | ✅ |
| AC6 | runtime — anchor | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** AC-field · risk: low · why: the anchor index is not on this machine ·
escalated, answered by the maintainer 2026-10-17 · follow-up: on the anchor, after the full rebuild, list the
writers of three tables written by wrapped helper calls, before and after · `expiry: when the anchor index is
available to a maintainer run` · `seen: 378, 384, 388, 389, 394, 390, 391, 393, 395, 396, 398`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_keyed_string_arg_span.py` — red on `main` (60d802c5: `8 failed`), green after.

### Rollback

`git revert`; the next build needs `--full` either way.

## Phase 3 — execute

Commits `d2518160` (contract, adapters, core, tests), `77d4fd6b` (release 0.5.0, docs), rebased onto 397's tip.

**Red first.** The proving test on `main` (60d802c5): `8 failed`. **Green after.** `8 passed`; PHPStan max, both `tsc`
runs, `ruff` and `mypy` clean.

**Axis 1.** Change-list rows 1–7. The full suite named 19 pinned tests (contract 15, schema 7, `EDGE_FIELDS`, the
vocabulary count, the PHP named-argument case, the playbook parity table) — row 6, traced by the suite rather than at
Gate 2 (P5). **Axis 2.** Approach bullets 1–5 implemented as approved, except bullet 2's SQL half (W6, at review).

A worktree run inherits the host's `CA_*_CMD` (the main checkout's adapters) and the venv's editable install; tests
here ran with both stripped, and the gate ran in the main checkout.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` — verdict **clean (challenger only — REVIEWER: OFF)**, with W6 open.

**Challenger** (ticket-blind: raw ticket plus `git diff feat/397-routes-from-source..HEAD` without this file; 1 dispatch,
79,584 tokens): 8 met · 2 partial (Scope 4, AC3) · 1 can't tell (E1). Three Major, six Minor:

| # | Finding | Resolution |
|---|---|---|
| M1 | a key the adapter could not value was still read from one line, so `keys_unread` hung on layout | H4 as now written: the field is present whenever a string is passed (1327ddb3) |
| M2 | Python, TS and SQL capture untested | tests for each; SQL turned out to capture only `…` — its scanner masks literals — so it keeps the line read (W6) |
| M3 | PHP now records `kwargs` (`{}`) on every call, so `arg_is="absent"` matches PHP calls | kept: W4 — PHP 8 keywords are now recorded, which is what the filter's `absent` means |
| m1 | storage growth | kept: values only where a string is passed, 256 characters at most (W1) |
| m2 | a `key_kw`-only rule reads no positional key | kept: the rule names a keyword (W3) |
| m3 | a keyword value over 256 characters has no fallback | consistent now: no value, counted, positional or not |
| m4 | census rows name setter, kind and key only | kept: a rule file lists rules in order |
| m5 | a no-op incremental reports `()` while status shows the stored census | kept: `wrote.*` is what this run did (051) |
| m6 | a spread names no key and counts nothing | kept: no position is known |

**Red first.** The review tests against 77d4fd6b: `4 failed, 9 passed`. **Green after:** `13 passed`. Ran at 1327ddb3.

| Row | Ph3/4 proven by | k/N |
|---|---|---|
| R1 / G1 | `test_the_php_adapter_captures_…`, `test_challenger_the_python_…`, `…typescript…`, `…sql_adapter_keeps…`, conformance | 5/5 |
| R2 / AC1 / AC2 | `test_ac1_…`, `test_ac2_…` | 2/2 |
| R3 / AC4 | `test_ac4_…`, `test_key_kw_…` (both), `test_call_site_arguments.py` | 4/4 |
| R4 / AC3 | `test_ac3_…`, `test_an_interpolated_key_…`, `test_a_key_the_pattern_refuses_…` | 3/3 |
| C1 / AC5 | `test_challenger_ac5_…`, the keyed-calls / view-data / route suites | 2/2 |
| AC6 | E1 | 0/1 (excluded) |

**P8.** `cross_repo_validate.py --public-only --skip-clone` at 8593611f: `public_ok: 10, public_failed: 1` —
brick_math's `Calculator.php` passes a non-UTF-8 literal, which the PHP adapter captured and could not encode, so the
file failed. A value that is not UTF-8 is no longer captured (00e4ab3f; `test_cross_repo_a_binary_literal_…`: 1 failed
before, 14 passed after).

Reviewed at 00e4ab3f — files: change-list rows 1–7. Working doc: `docs/tasks/398_keyed-string-arg-span.md`.

## Phase 5 — finalise

**Durable lesson.** `398-C1` in `LESSONS.md`: a git worktree run of this suite reads the host's `CA_*_CMD` and the
venv's editable install, so it tests the main checkout's adapters and core, not the worktree's.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 1 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

`read-a-literal-by-its-structure-not-a-regex` (361-C1) gains 398 (P1); it cannot promote in an unattended run.

Stale-review guard: after 00e4ab3f only this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`
change. Not stale.

### Outward actions

Under the handover: push `feat/398-keyed-string-arg-span`; open the PR against `main` (stacked on the 397 PR).
Deferred: ratify W1–W6; E1; tag v0.5.0 after the merge; merge after 396 and 397.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 59,217 |
| 4 review | `challenger` (ticket-blind) | 1 | 79,584 |

`LEDGER TOTAL: 138,801 · top cost driver: challenger`

