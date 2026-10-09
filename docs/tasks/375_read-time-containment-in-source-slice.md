---
id: 375
slug: read-time-containment-in-source-slice
title: 'A file indexed inside the repo and later swapped for a symlink is read through to wherever it points'
phase: 2
milestone: Trust
status: done
depends_on: [342]
---

## Why this exists

Containment is checked when a file is indexed (`containment.resolves_inside`, `indexer.py`), not
when its source is read back. `source_slice.declaration_slice` and `comment_block`
(`code_atlas/source_slice.py:38-59`) guard only with `path.is_file()`, which follows symlinks.

So a path that was a regular file at index time and is now a link to `/etc/…` or to a sibling
repo is read through by `read_symbol` until the next build notices. Graph rows are the only path
source (`read_symbol.py`), so the window is narrow — but the answer leaves the project.

Found while comparing context-mode's `isPathInsideProject`, which re-checks the realpath at use
time as well as lexically (context-mode `src/security.ts:686-728`; idea only, ELv2). 342 contained
the index-time walks; its two listed residuals (stub roots, the index directory) are separate.

## Scope

1. Every read in `source_slice` that returns file text resolves the path and refuses one that
   does not resolve inside the project root (`containment.resolves_inside`).
2. A refused read is an honest answer, never empty text signed as the body: the caller reports a
   reason (reuse an existing `NavReason` if one fits; a new one is a design decision).
3. No change to index-time containment or to graph rows.

## Assumptions to prove at design

- The project root is reachable at every `source_slice` call site without a new parameter chain;
  if not, the check moves one level up to the tool.
- The realpath cost per read is negligible next to the file read itself.

## Acceptance criteria

- **AC1:** index a fixture, replace an indexed file with a symlink to a file outside the repo;
  `read_symbol` on a symbol in it returns no outside text and names why.
- **AC2:** a symlink that resolves *inside* the repo still reads as today (byte-identical answer).
- **AC3:** `comment_block` obeys the same check (no docblock read through a link out).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 375 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1 and merges the PR after #54. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun 375 - 376 - 377 - 378 - 379`, no flags —
  `REVIEWER: ON` · `CHALLENGER: ON`. The handover delegates decisions ("make the necessary decisions"), so a want-decision is `ASSUMED`, never silent.
- Branch `fix/375-read-time-containment-in-source-slice` off `docs/375-context-mode-learnings` (`9226aca7`, PR #54 — stacked).
  Contract `.mango/run-contract-375.txt`. RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 3 retired skipped — advisory (blocks nothing)`
`REFINE: 6 unresolved surfaced | 0 want-decision asked | 5 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Premise.** `containment.resolves_inside` (`containment.py:11`), `source_slice.declaration_slice` / `comment_block`
(`source_slice.py:38-59`), `read_symbol.py`, `indexer.py`'s containment (`indexer.py:1121`) and `NavReason` all resolve.

**Recall (handle).** 360-C1 `confirm-the-blocked-path-runs` — run the named path once before designing around it. Done:
the spike below.

**Spike** (the ticket's window, run before design): index `src/real.py`, swap it for a link to `outside/secret.py`,
call `read_symbol("src.real.real")` — `{"found": true, "reason": "ok", "source": "def real():\n    return 'SECRET outside'\n"}`.
The read-through repair also re-parsed the outside file and stored its rows first (H4).

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 43,164 tokens) added W1 and H5–H6; found H1–H4 correctly classified.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the reason | how | reuse `path_outside_root` (`nav_result.py:104`, 342) — Scope 2 allows reuse; its comment widens to a swapped file |
| H2 | where the check lives | how | `source_slice.readable(root, path)` guards both readers (Scope 1); `read_symbol._found_body_payload`, the one body site for the main and separator-normalised paths, refuses with the reason |
| H3 | the refusal's shape | how | `found: true`, empty `source`, `file`, `reason: path_outside_root` — the `index_stale` payload's shape (`read_symbol.py:240`) |
| H4 | repair re-parses the swapped file | how | out of scope by Scope 3 ("No change to index-time containment") — a BACKLOG follow-up |
| H5 | the signature-only read (`read_symbol.py:398`) | how | inside `_found_body_payload`, so behind the check; `source_slice` guards it too |
| H6 | an in-root chain of links | how | `resolves_inside` follows the chain; tested |
| W1 | onboarding's docblock refused (`module_facts.py:58`) | want | **ASSUMED (awaiting ratification):** the map omits it, as for a file with no docblock — no new field in the onboarding dataset. Reverses no prior decision. |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=1 R=2 G=1 AC=3`
`CLARIFICATION: 7 raised | 7 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

Clarifications: H1–H6 cite code (Phase 0); W1 is resolved by the handover's delegation as `ASSUMED`, so it does not reach `j`.
TIER full: more than one file, and the ticket is a Trust (security) fix.

### BASELINE

`scripts/gate.sh` on `docs/375-context-mode-learnings`, Linux, bare pytest: `21 passed · 0 failed · 0 skipped` —
`GATE GREEN — all 21 checks passed`. Ran at 9226aca7.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "the answer leaves the project" | no file text from outside the root reaches a payload | ✅ |
| C1 | Scope 3 | "No change to index-time containment or to graph rows" | `indexer.py` and the store untouched | ✅ |
| R1 | Scope 1 | every `source_slice` read refuses a path outside the root | `readable()` in both readers | ✅ |
| R2 | Scope 2 | a refused read names a reason | `path_outside_root` on `read_symbol` | ✅ |
| AC1 | AC | swapped-out file → no outside text, names why | standard and minimal | ✅ |
| AC2 | AC | in-repo link reads as today | | ✅ |
| AC3 | AC | `comment_block` obeys the check | through `module_facts`, the consumer | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `"SECRET" not in json.dumps(result)` and `reason == path_outside_root`, on a real build | |
| AC2 | yes — `source` equals the target's text, `reason == ok` | a link existed in no prior test of `read_symbol`; the guard is non-regression |
| AC3 | yes — `module_facts(...).doc == ""` for a link out; an in-root chain still reads | |

### Rule sections

`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ no language test in source_slice or read_symbol · §R1.8 (change-type) ✅ one containment helper, resolves_inside, behind both readers · §R5.6 (change-type) ✅ the refusal is a distinct reason, never an empty body under ok · §R6.5 (change-type) ✅ AC1 and AC3 seen red on the prior code · §R7.5 (change-type) ✅ comments ≤ 3 lines · §AGENT_BRIEF P-spike (recalled handle confirm-the-blocked-path-runs) ✅ the spike ran the read before design`

## Phase 2 — design

### Approach

1. `source_slice.readable(root, path)` = `is_file()` and `resolves_inside(root, path)`; `comment_block` and
   `declaration_slice` take a required keyword `root` and return `""` for an unreadable path.
2. `read_symbol._found_body_payload(..., root=)` refuses first: `path_outside_root`, `found: true`, empty `source`, `file`.
3. `module_facts` passes its `root` (W1).
4. The reason's comment, the tool docstring, TOOLS.md and CHANGELOG name the case; BACKLOG files H4 beside 342's residuals.

### Rejected alternatives

- **A check in the tool only** — `module_facts` would still read through (AC3).
- **A new reason** — `path_outside_root` already means "resolves outside the indexed tree, not read" (342).
- **Re-checking in FreshnessGuard's repair** — index-time, excluded by Scope 3.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| the root reaches every call site | verified | `read_symbol` has `config.root`; `module_facts` has `root` — two sites, `grep declaration_slice\|comment_block` |
| realpath cost is negligible | verified | one `resolve()` per read beside a whole-file `read_text`; 342 already pays it per collected file |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `readable`, `root` keyword | `code_atlas/source_slice.py` | both callers; tests calling `declaration_slice` | R1, AC3 | 1/1 |
| 2 | refusal in `_found_body_payload` | `code_atlas/tools/read_symbol.py` | main and separator-normalised paths; docstring | R2, AC1, AC2 | 1/1 |
| 3 | pass `root` | `code_atlas/onboarding/module_facts.py` | the map's docblock | AC3, W1 | 1/1 |
| 4 | reason comment | `code_atlas/tools/nav_result.py` | — | R2 | 1/1 |
| 5 | proving tests | `tests/test_symlink_containment.py` | — | AC1–AC3 | 1/1 |
| 6 | proof collateral: `root=` | `tests/test_read_symbol_minimal_drops_docblock.py` | 4 calls | R1 | 1/1 |
| 7 | docs | `docs/TOOLS.md`, `CHANGELOG.md` | — | R2 | 2/2 |
| 8 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py`, the doc budget | — | 3/3 |

### Recalled handles

| # | Handle | Answer |
|---|---|---|
| 1 | `confirm-the-blocked-path-runs` | traced — `.venv/bin/python spike375.py` → `diff_content {"found": true, "stale": false, "reason": "ok", "source": "def real():\n    return 'SECRET outside'\n"}` |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — build, swap, the tool | `read_symbol` over a real Python-adapter build | n/a | ✅ |
| AC2 | integration | the same build, an in-root link | n/a | ✅ |
| AC3 | logic — the consumer | `module_facts`, `comment_block`, `declaration_slice` on links | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_symlink_containment.py tests/test_read_symbol_minimal_drops_docblock.py`.

### Rollback

`git revert` the two commits; nothing is stored.

## Phase 3 — execute

Commits `4bc4ffda` (code, tests), `e42e5a2b` (docs). **Red first** (R6.5), the code stashed:

```
$ .venv/bin/python -m pytest -q tests/test_symlink_containment.py -k "swapped or docblock"
FAILED tests/test_symlink_containment.py::test_an_indexed_file_swapped_for_a_link_out_reads_no_outside_text[standard]
FAILED tests/test_symlink_containment.py::test_an_indexed_file_swapped_for_a_link_out_reads_no_outside_text[minimal]
FAILED tests/test_symlink_containment.py::test_a_docblock_is_not_read_through_a_link_out
3 failed, 1 passed, 10 deselected in 2.14s
Ran at 9226aca7 (+ the new tests)
```

AC2 passed before too: it guards against a false refusal, not a missing one.

```
$ .venv/bin/python -m pytest -q tests -k "read_symbol or module_facts or source_slice or onboarding or symlink"
478 passed, 3897 deselected in 14.06s
Ran at 4bc4ffda
```

**Verification sweep.** File axis: the diff is the change list; `ruff check .` and `mypy code_atlas` clean.
Behaviour axis: Approach 1–4 implemented as approved; no deviation.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. Reviewed at e42e5a2b — files: `code_atlas/source_slice.py`,
`code_atlas/tools/read_symbol.py`, `code_atlas/tools/nav_result.py`, `code_atlas/onboarding/module_facts.py`,
`tests/test_symlink_containment.py`, `tests/test_read_symbol_minimal_drops_docblock.py`, `CHANGELOG.md`,
`docs/TOOLS.md`; working doc: this file.

- **`reviewer` round 1 — LGTM** (50,509 tokens): R1.1, R1.4, R7.5 checked; every caller passes the
  required `root`, so a missed one raises rather than reads. Non-blocking: W1 still awaits ratification;
  the H4 residual stands as filed.
- **`challenger` round 1** (ticket-blind, 48,908 tokens): 7 met · 0 not met · 0 can't tell. Notes: AC2
  compares with the fixture's text, not a pre-change answer; Scope 2's reason reaches `read_symbol` only
  (W1); the realpath cost is argued, not measured.

Verdict: clean. Matrix `Ph3/4 proven by`: G1, R1, R2, AC1–AC3 → `tests/test_symlink_containment.py`; C1 → the diff (no indexer/store hunk).

## Phase 5 — finalise

**Durable lesson.** None new: the spike confirmed 360-C1's practice; no claim generalises past this ticket.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `fix/375-read-time-containment-in-source-slice`; open the PR against
`docs/375-context-mode-learnings` (stacked on #54). Deferred to the maintainer: ratify W1; merge.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 43,164 |
| 4 review | `reviewer` | 1 | 50,509 |
| 4 review | `challenger` (ticket-blind) | 1 | 48,908 |

`LEDGER TOTAL: 142,581 · top cost driver: 4 review/reviewer`
