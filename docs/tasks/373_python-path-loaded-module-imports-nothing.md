---
id: 373
slug: python-path-loaded-module-imports-nothing
title: 'A Python module loaded by file path is unstamped, and a literal import_module reads as dynamic'
phase: 2
milestone: Coverage
status: done
depends_on: [353, 363, 295, 370]
---

## Why this exists

The Python half of 370. Measured with `adapters/python/index.py --file` on 2026-10-08:
`runpy.run_path(os.path.join(os.path.dirname(__file__), 'x.py'))` and `exec(open(...).read())` emit
plain `CALLS` with the path dropped and no stamp — `maybe_stamp_dynamic_import` covers
`import_module`, `__import__` and `spec_from_file_location` only. A literal
`import_module('pkg.mod')` is stamped dynamic though its target is a literal.

## Scope

1. `run_path` / `exec`-of-a-file stamp `unmodelled_resolution` (the honesty fix, 295).
2. A `__file__`-relative path (`os.path.join(os.path.dirname(__file__), …)`, `Path(__file__).parent
   / …`) gets 353's treatment: an exact relative `IMPORTS`.
3. A literal `import_module('pkg.mod')` / `__import__('pkg.mod')` becomes an `IMPORTS` of that
   module instead of a stamp. Standard library only (R2.1).

## Acceptance criteria

- **AC1:** A file loaded only by `run_path(dirname(__file__)/…)` is `imported_by` its loader.
- **AC2:** `exec(open(p).read())` with a computed `p` stamps the file; `find_orphans` stays unmeasured.
- **AC3:** `import_module('pkg.mod')` is an `IMPORTS` of `pkg.mod`; a computed argument still stamps.
- **AC4:** ADAPTER_PLAYBOOK §1.1's path-built row reads `373` for Python.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 373 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges #44–#47, then this PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`, batch 367 → 368 → 369 → 370 → 373 → 371 → 372;
  *"with skipped reviewers"* = `--no-reviewer` only (AGENTS.md), the challenger keeps its seat.
- Branch `feat/373-python-path-loaded-module-imports-nothing`, stacked on `feat/370-path-built-imports-beyond-php`
  (the ticket depends on 370); its PR targets that branch. Contract `.mango/run-contract-373.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 9 unresolved surfaced | 1 want-decision asked | 8 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Premise.** `maybe_stamp_dynamic_import` (295), `import_target_raw`, 353's exact-path reading and
the `dynamic_import` token resolve; `--file` confirmed `run_path`/`exec` emit plain `CALLS`, unstamped.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 52,821 tokens) surfaced X1–X8; the
main loop added X9.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | edge kind and basis | how | `IMPORTS` with a normalised repo-relative path, as a module import; no new kind (R3) |
| X2 | stamp token | how | the existing `dynamic_import` (`contract.py`) |
| X3 | stamp beside an exact edge | how | none: the load is modelled; a computed one stamps |
| X4 | which `__file__` spellings | how | `os.path.dirname(__file__)` (nested for parents), `Path(__file__).parent` (chained), through `abspath`/`realpath`/`normpath`/`resolve()`/`absolute()`/`str()`/`os.fspath`; joined by `os.path.join`, `/`, `+ '/…'`, an f-string |
| X5 | aliased callees | how | read through the file's own imports (`from runpy import run_path`, `import importlib as il`) |
| X6 | literal `import_module` | how | an absolute literal → `import_target_raw`; a relative one or `package=` keeps the stamp; `__import__('a.b')` names `a.b` |
| X7 | the existing `CALLS` | how | kept |
| X8 | `exec(open('x.py').read())` with a cwd-relative literal | want | **ASSUMED (delegated by the handover):** stamps — the working directory is not in the file |
| X9 | AC1 names `imported_by` | how | `include_graph` routes an `IMPORTS` language to `find_references` (186/188); proven through that route (P3), as 370 |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=4`
`CLARIFICATION: 9 raised | 9 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### BASELINE

The base is 370's tip. `scripts/gate.sh` on `main` (`e0d84cf1`): `GATE GREEN — all 21 checks passed`.
Ran at e0d84cf1.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "emit plain `CALLS` with the path dropped and no stamp" | a path-loaded module is imported or stamped | ✅ |
| C1 | Scope 3 | "Standard library only (R2.1)" | `runpy`, `importlib`, `exec`, `os.path`, `pathlib` | ✅ |
| R1 | Scope 1 | `run_path` / `exec`-of-a-file stamp | | ✅ |
| R2 | Scope 2 | a `__file__`-relative path → exact relative `IMPORTS` | X4 | ✅ |
| R3 | Scope 3 | a literal `import_module`/`__import__` → `IMPORTS` | X6 | ✅ |
| AC1 | AC | a file loaded only by `run_path(dirname(__file__)/…)` is `imported_by` its loader | X9 | ✅ |
| AC2 | AC | `exec(open(p).read())` with a computed `p` stamps; orphans unmeasured | | ✅ |
| AC3 | AC | `import_module('pkg.mod')` is an `IMPORTS`; computed stamps | | ✅ |
| AC4 | AC | playbook row reads 373 | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — three loaded files each list only the loader | |
| AC2 | yes — the loader unstamped, the computed file stamped, `resolution_unmodelled` | |
| AC3 | yes — line 8's `IMPORTS` links `pkg/mod.py`; the computed one adds none | |
| AC4 | yes — the row reads `373` | |

### Blast radius

- The Python adapter's call handling: the old dotted-text stamp check becomes alias-aware.
- Contract, parity and Python suites: `391 passed`.

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ no core change · §R2.1 (change-type) ✅ standard-library callees only · §R3.3 (change-type) ✅ a bare path or module, the core links it · §R5.2 (change-type) ✅ exact only when every part is literal · §R5.6 (change-type) ✅ anything unmodelled stamps`

## Phase 2 — design

### Approach

1. `adapters/python/src/loads.py`: the file's import aliases, the canonical callee, the
   `__file__`-relative path reader, the `exec`-of-a-file shapes.
2. `parse.py`: `emit_runtime_load` replaces the dotted-text stamp check.
3. README, playbook §1.1, CHANGELOG.

### Rejected alternatives

- **`INCLUDES` for a path load** — Python modules are `IMPORTS` everywhere else; one kind per relation.
- **Stamping every `exec`** — `exec` of a code string loads no module.

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | load recognition | `adapters/python/src/loads.py` (new) | — | R1–R3, C1 | 1/1 |
| 2 | emission | `adapters/python/src/parse.py` | Python emission | R1–R3 | 1/1 |
| 3 | proving test | `tests/test_python_runtime_loads.py` (new) | — | AC1–AC3 | 1/1 |
| 4 | docs | `adapters/python/README.md`, `docs/ADAPTER_PLAYBOOK.md`, `CHANGELOG.md` | doc budget | AC4 | 3/3 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC3 | integration | real Python build, `find_references`, `find_orphans` | authored | ✅ |
| AC4 | doc | the playbook row | — | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_python_runtime_loads.py`.

### Rollback

`git revert`; the next build drops the edges and the stamps.

## Phase 3 — execute

Commit `716d9e8a`. **Red first** — the test on the prior parser: `5 failed`. **P8:**
`cross_repo_validate.py --public-only --skip-clone` 11 ok / 0 failed; every count equals 370's
(no pinned Python sample loads a module this way), so no floor moves.

**Sweep.** Axis 1: `git diff --name-only feat/370-path-built-imports-beyond-php..HEAD` = items 1–4;
`ruff check`, `mypy --strict` (Python adapter) clean. Axis 2: as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `9872a5e2` — `716d9e8a` after the rebase —, 57,143 tokens): 7 met · 0 not met · 0 can't tell.**

1. **F1: a directory (`run_path(dirname(__file__))`) read as an exact target.** **Fixed** — stamps.
2. **F2: `str(Path(…) / 'x.py')` stamped.** **Fixed** — `str` and `os.fspath` keep the path.
3. **F3: a local rebinding `os` or `exec`.** **Left:** callees are read through the file's imports;
   documented in the README.
4. **F4: `exec(source)` of file text held in a variable went unstamped.** **Fixed** — stamps.
5. **F5: no edge-case tests.** **Fixed** with F1/F2/F4 (red `1 failed, 5 passed` on the prior reader).

All in `756c6031`. Verify-only (main loop):

Ran at 756c6031:
```
$ .venv/bin/python -m pytest -q tests/test_python_runtime_loads.py
6 passed
```

`Ph3/4 proven by`: G1, C1, R1–R3, AC1–AC4 — 9/9.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 756c6031 — the diff `feat/370-path-built-imports-beyond-php..756c6031`. Working doc:
`docs/tasks/373_python-path-loaded-module-imports-nothing.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `756c6031` only bookkeeping changes — this doc, `docs/BACKLOG.md` and
`docs/TOKEN_LEDGER.md`, all exempt.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

No new lesson.

### Outward actions

1. Push `feat/373-python-path-loaded-module-imports-nothing` — pre-authorised.
2. Open the PR against `feat/370-path-built-imports-beyond-php` — pre-authorised.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 52,821 |
| 2 | review | `challenger`, round 1 | 57,143 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 109,964 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits.
