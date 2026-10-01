---
id: 353
slug: include-path-concatenation
title: 'An include built as a constant plus a literal path reads as dynamic, so imported_by is empty'
phase: 2
milestone: Coverage
status: done
depends_on: [065, 279]
---

## Why this exists

The PHP adapter keeps an include's target only when the whole expression is one string literal
(`adapters/php/src/Visitor.php:958`). Anything else becomes `(dynamic)` and the literal is lost.
That covers the two commonest include shapes in PHP:

- `require_once __DIR__ . '/partials/select.php';` (magic constant — language spec)
- `require_once ROOT_DIR . '/src/partials/select.php';` (a `define()`d root)

In the field retro (2026-09-30) `include_graph imported_by` on a partial answered
`relationship_not_modelled` for exactly the second shape, the dominant pattern in that tree.
Grep on the basename found the includers.

## Scope

1. The adapter emits the literal tail of a `Concat` include as the target, still tier `DYNAMIC`
   when the head is not a literal. `__DIR__` / `dirname(__DIR__)` heads are spec, so they resolve
   exactly (includer-relative, `contract.py` `INCLUDES`).
2. The core links a tail to a file when exactly one indexed path ends with it, at HEURISTIC.
   Several matches stay unlinked and counted (R5.6), never a pick.
3. Whether the target_raw shape change needs a `contract_version` bump is settled in design (R3).

## Acceptance criteria

- **AC1:** `__DIR__ . '/x.php'` links RESOLVED to the file beside the includer.
- **AC2:** `CONST . '/src/a/x.php'` with one indexed `…/src/a/x.php` links at HEURISTIC, and
  `include_graph imported_by` on that file lists the includer.
- **AC3:** Two indexed files ending in the tail ⇒ no edge, counted in `unresolved_includes`.
- **AC4:** A fully dynamic include (`$path`) is unchanged.
- **AC5:** Measured on the pinned PHP samples: unresolved INCLUDES before/after, recorded in the
  working doc; cross-repo floors re-set if counts move (P8).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 353 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews and merges the PR, and ratifies ASSUMED A1–A2. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`, batch 352 → 353;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `feat/353-include-path-concatenation` off `main` (`2ad87272`). Contract `.mango/run-contract-353.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 2 want-decision asked | 1 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** All five resolve on `2ad87272`: the whole-literal-only include (`Visitor.php`
`enterInclude`), `contract.PATH_TARGET_BASIS["INCLUDES"] = "includer-relative"`, the resolver's path
pass (`resolver.py` `_path_key`), `include_graph`'s `unresolved_includes`, and R5.2's rule that the
resolver skips `DYNAMIC` (`store._iter_unresolved_edges`, `skip_dynamic`).

**Recall (by handle).** `343-C2` `formatter-rewrites-untouched-lines`.

The exposure check ran in the main loop; no dispatch.

| # | Decision | Class | Resolution |
|---|---|---|---|
| A1 | the tail's tier (Scope 1 says "still `DYNAMIC`") | want (bar) | **ASSUMED:** `HEURISTIC`. R5.2 (ratified 2026-08-30): the resolver skips `DYNAMIC` outright, so a `DYNAMIC` tail could never link and AC2 would be unreachable; its falsifier is "a `DYNAMIC` edge whose `target_raw` is resolvable". A constant root plus a literal is the "unresolvable-but-static" case R5.2 grades `HEURISTIC` |
| A2 | Scope 3: does the `target_raw` shape need a `contract_version` bump | want (scope) | **ASSUMED: no bump.** No vocabulary or qname changes (R3). The new raw is a `/…` path under the existing `INCLUDES` kind; a core that predates it reads it as an unlinkable includer-relative path, never a wrong link. The cost: an existing index keeps `(dynamic)` rows for files it does not re-parse until a full build |
| H1 | the suffix lookup | how | File nodes are named by their basename in all four adapters (checked on this repo's index: 618/618), so one batched `nodes_by_names(kind="File")` finds every candidate (283's batching rule) |

A1–A2 rest on the maintainer's up-front hand-back; both are surfaced in the PR.

## Phase 1 — analysis

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (title, Why this exists, Scope, Acceptance criteria) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=5`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/11 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

H1 cites the index; A1–A2 cite the hand-back and R5.2/R3, so `j = 0`.

### BASELINE

`main` at `2ad87272` is CI run 36795547832's tree (4117 passed / 4 skipped on py3.13). Per SG-2 it is
not pasted as a `$` block.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "`include_graph imported_by` on a partial answered `relationship_not_modelled`" | the includer is listed | |
| C1 | R5.6 | "Several matches stay unlinked and counted, never a pick" | | |
| C2 | R1.1 | — | the suffix pass reads no language | |
| R1 | Scope 1 | literal tail of a `Concat`; `__DIR__` heads exact | A1 | |
| R2 | Scope 2 | unique suffix → HEURISTIC | H1 | |
| R3 | Scope 3 | contract bump settled | A2 | |
| AC1 | AC | `__DIR__ . '/x.php'` → RESOLVED | | |
| AC2 | AC | `CONST . '/src/a/x.php'` → HEURISTIC; `imported_by` lists it | | |
| AC3 | AC | two files end with the tail → no edge, counted | | |
| AC4 | AC | `$path` unchanged | | |
| AC5 | AC | pinned PHP samples before/after; floors re-set if counts move | | |

### AC validation

AC1–AC4 read the stored `INCLUDES` rows and `include_graph` on a real PHP build; AC5 counts rows on
three pinned public samples with the `main` and branch adapters.

### Gap analysis

- **Now:** any non-literal include is `(dynamic)` `DYNAMIC`, so it can never link.
- **Target:** spec heads exact; other heads leave a linkable tail.

### Blast radius

- Every PHP include row changes shape on its next parse.
- The resolver's path pass gains a fallback limited to `HEURISTIC` path edges. No adapter emitted a
  `HEURISTIC` `INCLUDES` or `IMPORTS` before (`grep` over `adapters/`), so no existing row moves.
- `include_graph`, `impact` over includes, the onboarding include figures.

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the suffix pass keys on the tier and a path string not a language, §R2.2 (change-type) ✅ the adapter encodes PHP's magic constants and dirname only, no repo name, §R3 (change-type) ✅ no vocabulary or qname change so no contract_version bump (A2), §R5.2 (change-type) ✅ a constant-rooted tail is HEURISTIC and a variable-broken one stays DYNAMIC, §R5.6 (change-type) ✅ two or more suffix matches or a truncated lookup link nothing`

## Phase 2 — design

### Approach

1. **Adapter.** `includeTarget` flattens the `.` chain and takes its trailing literals as the tail. A
   whole literal is unchanged. `__DIR__`, `dirname(__FILE__)` and `dirname(<head>, n)` give
   `../`×n plus the tail, exact. Any other head with a `/…` tail gives the tail at `HEURISTIC`.
   Anything else stays `(dynamic)`.
2. **Resolver.** A `HEURISTIC` path edge whose includer-relative key misses goes to
   `_link_by_path_suffix`: one batched basename lookup, kept only when exactly one File's
   `/<qname>` ends with the tail. A lookup that hit `_MAX_SUFFIX_CANDIDATES` links nothing.
3. **Docs.** TOOLS.md's `include_graph` row; the contract comment on `INCLUDES`.

### Rejected alternatives

- **Keep the tail `DYNAMIC`** (A1): unlinkable by R5.2.
- **Read `define()` values to resolve the root.** Cross-file constant evaluation; a guess wearing
  `RESOLVED`.
- **A suffix scan per edge** over every File node: O(edges × files) on the anchor's 112k files.

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | include target | `adapters/php/src/Visitor.php` | every PHP include row | R1, AC1, AC4 | 1/1 |
| 2 | suffix link | `code_atlas/resolver.py`, `code_atlas/contract.py` (comment) | path-edge resolve | R2, AC2, AC3 | 2/2 |
| 3 | docs | `docs/TOOLS.md` | doc budgets | G1 | 1/1 |
| 4 | tests | `tests/test_include_path_concatenation.py`, `tests/fixtures/include_concat/` (new) | proof | AC1–AC4 | 2/2 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced in Phase 3.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | real PHP build, `INCLUDES` rows | n/a | ✅ |
| AC2 | integration | real PHP build + `include_graph imported_by` | n/a | ✅ |
| AC3 | integration | rows + `include_graph imports` `unresolved_includes` | n/a | ✅ |
| AC4 | integration | rows | n/a | ✅ |
| AC5 | runtime | `main` vs branch builds of `laravel_app`, `symfony_demo`, `brick_math` | pinned public samples | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 1 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_include_path_concatenation.py`. On `2ad87272` three of four
fail (every include is `(dynamic)`); AC4 passes as a guard. All four pass after.

### Rollback

`git revert`. Rows re-take their old shape on the next parse of each file.

## Phase 3 — execute

Commits on `feat/353-include-path-concatenation`: `0d52ed79` (the change), `836e7dd3` (the challenger's
F2: a path with a variable in it stays dynamic).

**Proving test, red on the pre-change tree** (`2ad87272`, before any source edit):

    FAILED tests/test_include_path_concatenation.py::test_a_dir_head_links_resolved_to_the_file_beside_the_includer
    FAILED tests/test_include_path_concatenation.py::test_a_constant_head_links_its_unique_tail_at_heuristic
    FAILED tests/test_include_path_concatenation.py::test_a_tail_two_files_end_with_stays_unlinked_and_counted
    3 failed, 1 passed in 0.86s

**AC5 — the pinned PHP samples, `main` (`2ad87272`) adapter and core against the branch.**

| Sample | nodes / edges | INCLUDES | `DYNAMIC` before → after | linked before → after |
|---|---|---|---|---|
| `laravel_app` | 74 / 467 both | 3 | 3 → 1 (`require $maintenance`) | 0 → 1 (`bootstrap/app.php`) |
| `symfony_demo` | 437 / 1825 both | 4 | 4 → 0 | 0 → 0 |
| `brick_math` | 887 / 4312 both | 2 | 2 → 0 | 0 → 0 |

The seven newly non-dynamic rows that stay unlinked name `vendor/` or `var/cache/` files, which are
not indexed; they now count as unresolved claims with a real path instead of `(dynamic)`. Node and
edge counts are identical, so no cross-repo floor moves (P8 needs no re-floor). The `main` run used a
copy of `vendor/`: a symlinked one loads the branch's `src/` through Composer's real path, which a
first measurement did by mistake.

**Sweep.**
- **Axis 1 — file set.** The diff is the change list.
- **Axis 2 — design conformance.** Approach 1–3 as approved, plus D1.
- **Handle `formatter-rewrites-untouched-lines`, traced.** `ruff format --diff code_atlas/resolver.py`
  proposes hunks only on untouched lines (the `file_hits` call and older call sites); none applied.

| # | Approved | Implemented instead | `path:line` | Surfaced |
|---|---|---|---|---|
| D1 | any non-literal head plus a `/…` tail → HEURISTIC | exactly one head; a variable between the root and the tail stays `(dynamic)` | `adapters/php/src/Visitor.php` `includeTarget` | yes |
| D2 | `tests/fixtures/php/reach`'s reachability answer unchanged | its `expected_set` gains `lib.php`: `entry.php`'s `require_once __DIR__ . '/lib.php'` now links, so the include reaches the file | `scripts/tokens_to_answer_questions.json` | yes |

Ran at 1653046a

```
$ scripts/gate.sh
  PASS bytecode invalidation (checked-hash, 146)
  PASS entry points (derived from [project.scripts])  — code_atlas.egg-info
  PASS ruff check .
  PASS mypy (code_atlas + onboarding_llm)
  PASS npm ci (adapters/typescript)
  PASS npm ci (adapters/sql)
  PASS php adapter runtime deps present (pytest coverage)
  PASS pytest -q
  PASS tokens-to-answer (ratio >= 0.63, recall 1.0, precision 1.0)
  PASS composer validate --strict (R8.3)
  PASS php -l (authored source)  — 8 file(s)
  PASS phpstan level max (R6.6)
  PASS tsc --checkJs --strict (R6.6, TS adapter)
  PASS tsc --checkJs --strict (R6.6, SQL adapter)
  PASS ruff check (R6.6, Python adapter)
  PASS mypy --strict (R6.6, Python adapter)
  PASS R1.1 no language branch in core
  PASS R2.2 no repo/framework name
  PASS R4.1 no LLM in core
  PASS R7.3 no AI-attribution trailer  — 3 commit(s)
  PASS R2.4 commit identity  — 3 commit(s)
  21 passed · 0 failed · 0 skipped
GATE GREEN — all 21 checks passed
```

The first gate run, on `836e7dd3`, was RED on tokens-to-answer precision (`reachable_from_entry` 0.923, unexpected `lib.php`): D2.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `0d52ed79`, 67,708 tokens): 7 met · 0 not met · 1 can't tell
(AC5 — recorded here, which it may not read).** It judged A1 (`HEURISTIC`, by R5.2) and A2 (no bump,
by R3.1, with 335/336 as precedent) correct. Its findings:

1. **An incremental keeps a unique link after a twin file is added.** Accepted as the resolver's
   existing contract: only unlinked edges are re-resolved, which already holds for 214's unique
   `Function` and 258's unique `Method` links. A full build re-decides it.
2. **A variable mid-path leaves a basename-only tail** (`ROOT . '/p/' . $n . '/x.php'` → `/x.php`).
   **Fixed (D1)** in `836e7dd3`, pinned by a fixture line.
3. **`dirname(__DIR__, n)` past the repo root collapses at the root** — `_relative_to`'s existing
   behaviour for any `../` literal. Accepted.
4. **A namespaced user `dirname`** is read as the builtin. Accepted: PHP's own fallback resolves an
   unqualified `dirname` to the global one unless a namespace declares its own.

The fixes are small and test-pinned, so the round-1 verify ran in the main loop with no re-dispatch.

`Ph3/4 proven by`: G1, C1–C2, R1–R3, AC1–AC5 — 11/11.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 1653046a — the diff `main..1653046a`. Working doc: `docs/tasks/353_include-path-concatenation.md`
(embedded).

## Phase 5 — finalise

Stale-review guard: after `1653046a` only this doc, `docs/BACKLOG.md` (the row closed) and
`docs/TOKEN_LEDGER.md` change; all are exempt.

**Durable lesson: none.** The AC5 symlink trap (a symlinked `vendor/` loads another tree's sources
through Composer's real path) is recorded above; it is a first sighting with no rule to amend.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

1. Push `feat/353-include-path-concatenation` — pre-authorised.
2. Open the PR — pre-authorised.

Deferred to the maintainer: the merge (`docs/TOKEN_LEDGER.md` and `docs/BACKLOG.md` conflict
trivially with #21); ratifying ASSUMED A1–A2.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | review | `challenger`, round 1 | 67,708 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 67,708 · top cost driver: review/challenger`

**Revert path:** `git revert` the branch commits; rows re-take their old shape on the next parse.
