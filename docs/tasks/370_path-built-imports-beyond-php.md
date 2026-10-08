---
id: 370
slug: path-built-imports-beyond-php
title: 'A TS require built from __dirname plus a path imports nothing'
phase: 2
milestone: Coverage
status: done
depends_on: [353, 363, 294, 295]
---

## Why this exists

353 made a PHP include built as `__DIR__ . '/x.php'` an exact includer-relative edge, and
`ROOT . '/x.php'` a `HEURISTIC` tail the core links by a unique path suffix. 363 then let
`include_graph` call a file nothing can reach a confident zero. Both are core-side once the adapter
emits the tail. Measured with the TS adapter's `--file` mode on 2026-10-08: `require(__dirname +
'/lib/x')`, `require(path.join(__dirname, 'lib', 'y'))`, `` require(`${__dirname}/lib/z`) `` and
`require(ROOT + '/lib/w')` each emit only `CALLS "require"` — no `IMPORTS`, no literal tail, and no
`unmodelled_resolution` stamp. The Python half (`run_path`, `exec`-of-a-file) is 373.

## Scope

1. A `require` whose argument is `__dirname` joined to literals (by `+`, a template, or
   `path.join`/`path.resolve`) is an exact relative `IMPORTS`; another head with a `/…` literal tail
   is a `HEURISTIC` tail, as 353. Anything else stays `(dynamic)` and stamps the file (295).
2. Only node builtins are spec (R2.1); no bundler alias or framework loader.

## Acceptance criteria

- **AC1:** `include_graph imported_by lib/x.js` lists the `__dirname`-built `require`, in each of
  the `+`, template and `path.join` forms.
- **AC2:** `require(ROOT + '/lib/w')` links by unique path suffix at `HEURISTIC`.
- **AC3:** A `require(name)` with no literal still stamps the file and `find_orphans` stays unmeasured.
- **AC4:** ADAPTER_PLAYBOOK §1.1's path-built row reads `370` for TS.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 370 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges #44–#46, then this PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`, batch 367 → 368 → 369 → 370 → 373 → 371 → 372;
  *"with skipped reviewers"* = `--no-reviewer` only (AGENTS.md), the challenger keeps its seat.
- Branch `feat/370-path-built-imports-beyond-php`, stacked on `feat/369-class-property-references-beyond-php`
  (both edit `adapters/typescript/src/parse.js`); its PR targets that branch. Contract `.mango/run-contract-370.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 1 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 0 want-decision asked | 8 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** 353's `_link_by_path_suffix` (`resolver.py`), 294's stamp, `requireSpecifier` and
`resolveWithExt` resolve. **Missing:** the ticket says `require(ROOT + '/lib/w')` emits no
`unmodelled_resolution` stamp; `--file` shows it already stamps (294) — AC3 already held (P3, below).

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 53,273 tokens) surfaced X1–X7; the
main loop added X8.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | an extensionless tail never ends a `File` qname | how | the adapter completes it with the requirer's own extension (a `.js` file's sibling is `.js`, a `.ts` file's `.ts`), since the core matches a basename exactly (`resolver.py`, `_link_by_path_suffix`) |
| X2 | edge kind and basis | how | `IMPORTS`, repo-relative, as a `./x` literal; the tail at `HEURISTIC` — both in `PATH_EDGE_KINDS`, no contract move |
| X3 | the `CALLS "require"` | how | replaced by the `IMPORTS`, as for a literal require (`parse.js`) |
| X4 | `path.join`'s own `CALLS` | how | left: a real call |
| X5 | which `join` counts | how | node's `path`/`node:path` by its file-level binding (`require`, default, namespace or named import); `__filename` and `import.meta` are out |
| X6 | normalisation | how | a tail must open with `/` and hold no `.`/`..` step; an exact path may step up but not out of the repo |
| X7 | the stamp | how | dropped only for an exact path; a tail keeps it (it may not link) |
| X8 | AC1 names `include_graph` | how | `include_graph` reads `INCLUDES` and routes an `IMPORTS` language to `find_references` (186/188): AC1 is proven through that route (P3) |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=4`
`CLARIFICATION: 8 raised | 8 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/8 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### BASELINE

The base is 369's tip. `scripts/gate.sh` on `main` (`e0d84cf1`): `GATE GREEN — all 21 checks passed`.
Ran at e0d84cf1.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "each emit only `CALLS \"require\"`" | a path-built require imports | ✅ |
| C1 | Scope 2 | "Only node builtins are spec (R2.1)" | `path` / `node:path` only | ✅ |
| R1 | Scope 1 | `__dirname` + literals → exact relative `IMPORTS` | `+`, template, `path.join`/`resolve` | ✅ |
| R2 | Scope 1 | another head + `/…` literal → `HEURISTIC` tail | X1, X6 | ✅ |
| R3 | Scope 1 | anything else `(dynamic)`, stamped | | ✅ |
| AC1 | AC | the requirer is listed for `lib/x.js`, three forms | X8 | ✅ |
| AC2 | AC | `ROOT + '/lib/w'` links by unique suffix at `HEURISTIC` | | ✅ |
| AC3 | AC | `require(name)` still stamps; orphans unmeasured | already held (premise) | ✅ |
| AC4 | AC | playbook row reads 370 for TS | | ✅ |

**P3 deviations.** AC1 names `include_graph imported_by`; it answers `relation_unmodelled_for_language`
with `try_instead: find_references` for a TS file, so the test asserts that route and then the
importer through `find_references`. The ticket's "no stamp" premise was wrong for the `ROOT` form.

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — each of four targets lists `src/loader.js`, at `RESOLVED` | |
| AC2 | yes — `/vendorless/tail.js` links `HEURISTIC`; a twin tail stays unlinked | |
| AC3 | yes — no `IMPORTS` at line 10, the stamp, `find_orphans` `resolution_unmodelled` | |
| AC4 | yes — the row reads `370` | |

### Blast radius

- The TS adapter's require handling and `classifyVariable` (a recognised require is no `Const`).
- Contract, parity and TS suites: `366 passed`.

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ no core change · §R2.1 (change-type) ✅ node's path module and __dirname only · §R3.3 (change-type) ✅ the tail is bare, the core links it · §R5.2 (change-type) ✅ a tail is HEURISTIC, a computed part stays DYNAMIC · §R5.6 (change-type) ✅ a tail keeps the stamp; only an exact path drops it`

## Phase 2 — design

### Approach

1. `imports.js`: `pathModuleNames` (the file's `path` bindings) and `pathBuiltRequire`, which flattens
   `+`, templates and `path.join`/`resolve` into a head and literals and returns the exact target or
   the completed tail, or null.
2. `parse.js`: `emitBuiltRequire` in the body walk and in `walkVariables` (so `declarations_only` keeps
   it); `classifyVariable` takes the same predicate.
3. README, playbook §1.1, CHANGELOG.

### Rejected alternatives

- **Completing the tail in the core** — an extension list is a language fact (R1.1).
- **Emitting one edge per candidate extension** — several unlinked edges per site.

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | recognition | `adapters/typescript/src/imports.js` | TS emission | R1–R3, C1 | 1/1 |
| 2 | emission | `adapters/typescript/src/parse.js` | TS emission | R1–R3 | 1/1 |
| 3 | proving test | `tests/test_path_built_require.py` (new) | — | AC1–AC3 | 1/1 |
| 4 | docs | `adapters/typescript/README.md`, `docs/ADAPTER_PLAYBOOK.md`, `CHANGELOG.md` | doc budget | AC4 | 3/3 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC3 | integration | real TS build, `find_references`, `include_graph`, `find_orphans` | authored | ✅ |
| AC4 | doc | the playbook row | — | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_path_built_require.py`.

### Rollback

`git revert`; the next build emits the old `CALLS`.

## Phase 3 — execute

Commit `3de03837`. **Red first** — the test on the prior parser: `5 failed, 1 passed` (AC3 held).
**P8:** `cross_repo_validate.py --public-only --skip-clone` 11 ok / 0 failed. Edges rose on two TS
samples — mqttjs 6150→6151, socketio 28229→28241 — with nodes unchanged; the floors still hold, so
none moves. A first run on this tree reported 369's counts unchanged; a re-run on the same tree, and
373's run on top of it, both reported the rise — the first run is not trusted.

**Sweep.** Axis 1: `git diff --name-only feat/369-class-property-references-beyond-php..HEAD` = items
1–4; `ruff check`, `tsc --checkJs --strict` clean. Axis 2: as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `6479a1e9` — `3de03837` after the rebase —, 63,772 tokens): 8 met · 0 not met · 0 can't tell.**

1. **F1: a rejected shape lost its `const` node.** **Fixed** in `890f4c6c`: one accept test feeds both.
2. **F2: `__dirname + 'lib/x'` (no separator) read as `lib/x`.** **Fixed:** a tail must open with `/`.
3. **F3: a `path` parameter shadowing the module.** **Left:** `path` is matched by its file-level
   binding; a function rebinding that name is a documented limit.
4. **F4: an exact path leaving the repo.** **Fixed:** it stays dynamic.
5. **F5: any expression is a tail's head.** **Left:** the ticket's "another head", as 353.
6. **F6: no negative shapes.** **Fixed** with F1/F2/F4 (red `2 failed, 5 passed` on the prior parser).
7. **F7: `imports.js` lost its CRLF endings.** **Fixed** — the edit tool rewrote them.

Verify-only (main loop):

Ran at 890f4c6c:
```
$ .venv/bin/python -m pytest -q tests/test_path_built_require.py
7 passed
```

`Ph3/4 proven by`: G1, C1, R1–R3, AC1–AC4 — 9/9.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 890f4c6c — the diff `feat/369-class-property-references-beyond-php..890f4c6c`. Working doc:
`docs/tasks/370_path-built-imports-beyond-php.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `890f4c6c` only bookkeeping changes — this doc, `docs/BACKLOG.md` and
`docs/TOKEN_LEDGER.md`, all exempt.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

No new lesson in this repo. The CRLF rewrite is a harness signal: a scripted edit that read a file
in text mode rewrote its line endings, which the diff showed only as a binary change.

### Outward actions

1. Push `feat/370-path-built-imports-beyond-php` — pre-authorised.
2. Open the PR against `feat/369-class-property-references-beyond-php` — pre-authorised.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 53,273 |
| 2 | review | `challenger`, round 1 | 63,772 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 117,045 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits.

**Gate.** `scripts/gate.sh` on `18cdeef6`: `GATE GREEN — all 21 checks passed` (Linux, bare pytest).
