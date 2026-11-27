---
id: 459
slug: verify-refs-memory-links-resolve-in-memory
title: "Links inside host memory resolve against the memory folder first"
phase: 2
milestone: "Field gaps — Python/TS consumer"
status: done
depends_on: [443]
---

## Why this exists

Same field report as 456. Claude Code's memory index `<agent-memory>/MEMORY.md` links to its sibling
files: `[Title](user-language-preference.md)`. All 6 links in the Python/TS consumer's index come back
`never_existed` / `no_branch_ever_held_it`, but each file exists in the memory folder next to the
index. The link is checked against the repo tree only.

They are not actionable today, so nothing breaks. But the memory class is the one 443 made the
default, and a broken memory link is exactly what an agent needs to know. Today a deleted memory file
and a present one get the same answer, so the class cannot report the one stale case that matters.

## Scope

1. For a corpus file under `<agent-memory>/`, resolve a relative link against that file's folder in
   the memory dir first, then against the repo as today.
2. Found in memory → `ok` (reason `exists_in_memory`). Missing in both → `gone`, actionable, in the
   memory class (an edit, no diff, as 443 says). A memory file has no git history, so there is no
   rename lookup.
3. A repo file still cannot claim the `<agent-memory>/` namespace (SEC-IN-03, unchanged).

## Acceptance

1. Fixture memory dir: an index linking one present and one missing sibling → `ok` and actionable
   `gone`.
2. The Python/TS consumer: the 6 index links are `ok`.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Last updated:** 2026-11-28
- **Current phase:** finalise
- **Next action:** the maintainer merges #192, then this PR; 460 runs next, stacked on this branch
- **Blocked on:** nothing
- **KEY:** 459 · **work_doc_mode:** embed · `TRACK: backend` · Run mode: `autorun 456 - … - 462`, fourth —
  `REVIEWER: ON` · `CHALLENGER: ON` · `cost_tier: standard`. A want-decision is `ASSUMED` under the handover.
- Branch `feat/459-verify-refs-memory-links-resolve-in-memory` from 458's tip `dfa12039` (#192), in a worktree.
  Contract `.mango/run-contract-459.txt`; RECONCILE t0: `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 3 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 14 unresolved surfaced | 1 want-decision asked | 13 how-decision resolved+cited | 1 ASSUMED | skip: no`

`<agent-memory>/` (`MEMORY_PREFIX`, `doc_refs.py:79`), `memory_dir` and SEC-IN-03 (`collect`) resolve; ambiguous: the
consumer's memory folder, read on this host (6 links, 6 notes). Recalled: 456-C1 `diff-every-row-not-the-target-rows`
(handle), 398-C1 (area). Exposure-checker: 9 returned (H6–H13, W1).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | which refs | how | a LINK in a memory file (Scope 1 "a relative link"); code spans and prose keep the repo's rules |
| H2 | the folder | how | that file's folder in the memory dir, contained by `resolves_inside` (Scope 1, SEC-IN-03) |
| H3 | verdicts | how | there → `ok` `exists_in_memory`; in neither → `gone` `missing_from_memory`; any other repo answer stands (Scope 2) |
| H4 | strength | how | both reasons join `_PATH_FOUND` — the memory folder answered — so a `gone` is strong and actionable (Scope 2) |
| H5 | history | how | none: a memory file has no git history (Scope 2) |
| H6 | fragments, URLs, rooted paths | how | `kind_of` already strips `#…` and drops `://` and `/…` (`doc_refs.py:313-319`) |
| H7 | a directory target | how | `exists()`, as the repo's `_exists` reads one |
| H8 | subfolders | how | the linking file's own folder is the base (Scope 1 "that file's folder") |
| H9 | a symlink out | how | `resolves_inside` false → not looked for there → repo rules |
| H10 | case | how | the filesystem's own match, as the repo's |
| H11 | the edit shape | how | 443's: memory rows are edits, no diff (`patches`) |
| H12 | no memory folder | how | nothing found there → repo rules, as today |
| H13 | the cache | how | the verdict key carries whether it was a memory link, so a code span never reuses it |
| W1 | AC2's bar | want | **ASSUMED:** all 6 `ok`, measured on the host's memory folder |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=1 R=2 G=1 AC=2`
`CLARIFICATION: 14 raised | 14 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/5 touched files under UI paths`
`SCOPE: S`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a deleted memory file and a present one get the same answer" | they now differ | ✅ |
| R1 | Scope 1 | "resolve a relative link against that file's folder in the memory dir first" | H1, H2 | ✅ |
| R2 | Scope 2 | "Found in memory → `ok` … Missing in both → `gone`, actionable" | H3–H5 | ✅ |
| C1 | Scope 3 | "A repo file still cannot claim the `<agent-memory>/` namespace" | `collect` unchanged; links from repo docs never reach `memory_link` | ✅ |
| AC1 | Acc 1 | "one present and one missing sibling → `ok` and actionable `gone`" | fixture | ✅ |
| AC2 | Acc 2 | "the 6 index links are `ok`" | consumer, W1 | ✅ |

**Gap.** `Resolver.path` reads a memory file's link against the repo only (`here` is empty for memory), so every
sibling note came back `never_existed`, present or deleted.

`BASELINE: green — the 458 suites plus its proving test: 883 passed`

Ran at dfa12039 (pre-change)
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q $(cat .mango/baseline-459.list)
883 passed in 31.04s
```

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §5 (change-type) ✅ R5.6 present and deleted notes now answer differently · §6 (change-type) ✅ R6.5 seen failing on the base · §7 (change-type) ✅ R7.5 comments ≤ 3 lines, R7.6 the TOOLS sentence extended in place · §9 (change-type) ✅ R9.1/SEC-IN-03 the lookup stays inside the memory folder; `rows[].path` already untrusted`

## Phase 2 — design

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `diff-every-row-not-the-target-rows` — traced: the consumer's 458-code and 459-code exports diffed by (file, line,
  ref) on one index copy (Phase 3): 6 rows changed, all the memory links.

**Approach.** (1) `Resolver.memory_link`: the link normalised against the memory file's folder; present inside the
memory dir → `ok`; else the repo's `path` verdict, `never_existed` turned `gone`. (2) `_rows` routes a memory LINK there,
its own cache key. (3) `_PATH_FOUND` gains both reasons. **Rejected:** trying every path ref of a memory file in the
memory folder — a code span naming a repo file (`docs/SPEC.md`) would turn `gone` when the repo never had it.
**Assumptions:** none novel.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| memory first | `code_atlas/doc_refs.py` | `test_verify_refs_actionable.py` (memory rows), the stored summary | R1, R2, C1 |
| proving test | `tests/test_verify_refs_memory_links.py` | — | AC1 · 6/6 |
| docs | `docs/TOOLS.md`, `CHANGELOG.md` | `test_doc_size_budget.py` | R7.6 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration (a built index and a memory folder) | integration fixture | authored | ✅ |
| AC2 | e2e (the consumer's memory) | manual-recorded: export pair | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `tests/test_verify_refs_memory_links.py`. Rollback: revert. Porting: one repo.

## Phase 3 — execute

Main loop, in the worktree, at `b258f78a`. **Sweep.** Axis 1: the diff is the approved list; `ruff`, `mypy` clean.
Axis 2: (1)–(3) implemented-as-approved. The code-span row asserts no memory verdict rather than `never_existed`: since
458 an unanswered suffixed name in a symbol's shape that is external stays silent.

Ran at dfa12039 (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_verify_refs_memory_links.py   # base + the new test only
3 failed, 3 passed in 1.20s
```

At `b258f78a` (superseded by the review fixes) the suites read `889 passed`; Phase 4 holds the reviewed tree's runs.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. `reviewer` (Sonnet), and the ticket-blind `challenger` on the raw ticket
(`git show dfa12039:<this file>`) + the branch diff.

- **Reviewer round 1** at `b258f78a` (61,073 tokens): CHANGES REQUESTED, conditional on 1–2. **Taken** (`04b609a9`):
  (1) containment (`isabs`, `..`, `resolves_inside`) before any filesystem call — `kind_of` already drops `/…`, so
  defence in depth, pinned by `/etc/hosts`; (2) the memory folder is asked before the repo.
- **Challenger round 1** at `b258f78a` (55,139 tokens): 7 rebuilt · 6 met · 1 can't tell — Scope 2's "no rename
  lookup": the repo fallback was `path()`, git history included. **Taken** (`04b609a9`): `path()` split into
  `_in_tree` (the checkout) and the history part; a memory link falls back to `_in_tree` only. Row `old.md` (a repo
  file once, deleted) → `missing_from_memory`, seen failing on `b258f78a` where history answered `deleted`.
- **Reviewer round 2** (verify-only, main loop, at `04b609a9`): both fixes as described; only the affected proof re-run.
- **Challenger round 2** (resumed, 4,794 tokens): row 4 met; the `path()` split leaves repo docs unchanged.

`CHALLENGER VERDICT: 7 requirement(s) rebuilt | 7 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

Ran at 04b609a9
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_verify_refs_memory_links.py $(cat .mango/baseline-459.list)
891 passed in 39.07s
```

**AC2 — the consumer**, re-run on the reviewed tree, 458 code and this branch back to back:

Ran at 04b609a9
```
before (dfa12039): 6 memory links path never_existed (weak); 4 actionable
after  (04b609a9): 6 memory links ok exists_in_memory; 4 actionable; 6 rows changed, 0 newly actionable
```

Reviewed at 04b609a9 — files: `code_atlas/doc_refs.py`, `tests/test_verify_refs_memory_links.py`, `docs/TOOLS.md`,
`CHANGELOG.md`; working doc `docs/tasks/459_verify-refs-memory-links-resolve-in-memory.md`.

`Ph3/4 proven by`: R1, R2, C1, AC1 → `tests/test_verify_refs_memory_links.py` (9); AC2 → the corpus block.

## Phase 5 — finalise

Stale-review guard: only bookkeeping after `04b609a9` — not stale.

**Durable lessons.** 459-C1 `ask-the-cheap-answer-before-the-costly-one` and 459-C2 `paste-the-run-you-made` (type 2,
first sightings) in `docs/LESSONS.md`. 459-C2 records a slip in this run: the first baseline block carried the previous
ticket's figure; it was re-run and replaced before any gate.

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/459-verify-refs-memory-links-resolve-in-memory`; open its PR against
`feat/458-verify-refs-file-suffix-is-a-path` (#192, stacked). Deferred to the maintainer: ratify W1; merge after #192.
Revert: revert the branch's commits.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 48,542 |
| 3 execute | `implementer` — not dispatched (main loop implemented) | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | rule-book `reviewer` | 1 | 61,073 |
| 4 review | ticket-blind `challenger` | 1 | 55,139 |
| 4 review | ticket-blind `challenger` | 2 | 4,794 (resumed: 59,933 cumulative − 55,139) |

`LEDGER TOTAL: 169,548 · top cost driver: 4 review / reviewer` — main loop unmeasured.
