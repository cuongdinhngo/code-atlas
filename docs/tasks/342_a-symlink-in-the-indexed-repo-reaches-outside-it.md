---
id: 342
slug: a-symlink-in-the-indexed-repo-reaches-outside-it
title: "A symlink committed in the indexed repo is followed on read and write — code-atlas serves and overwrites files outside the repo"
phase: 1
milestone: Agent-trust
status: done
depends_on: []
---

## Why this exists (public-launch security audit, 2026-09-27)

Nothing under `code_atlas/` checks that a path it reads or writes stays inside the indexed root:
there is no `is_symlink` test and no `resolve()`-under-root check anywhere. The indexed repo is
untrusted content, and git stores symlinks.

- **Write.** `_write_outputs` (`code_atlas/tools/generate_onboarding.py:430-457`) writes into
  `docs/onboarding/` and `.code-atlas/onboarding/`. A repo that commits `docs/onboarding` as a
  symlink — or `overview.md` → a dotfile in the user's home, next to its own `manifest.json` so
  `_refuse_foreign_tree` passes — gets that file overwritten with partly attacker-shaped text.
  `_remove_recorded_pages` (`:362-363`) unlinks through a symlinked `modules/`.
- **Read.** A tracked `x.py` that is a symlink to a file outside the repo is indexed
  (`indexer.py:736`) and its body then served by `read_symbol` (`source_slice.py:42,61`);
  `orientation._read_text` (`onboarding/orientation.py:150-158`) quotes a symlinked README.
- **`diff_architecture`** (`tools/diff_architecture.py:109-113`) accepts an absolute or `..` path:
  an existence oracle for any file, and it parses any JSON it is pointed at.
- **Fallback walk.** `_walk` (`indexer.py:1018-1030`, used only without a git index) calls
  `entry.is_dir()`, which follows symlinks: a loop is an unbounded walk, a link to `/` indexes the
  host.

## Goal

Every file code-atlas reads from, or writes into, the indexed repo resolves inside that repo.

## Scope / Deliverables

1. One containment helper (resolve, then require the result under `root.resolve()`), used by every
   site below — one definition site (R6.7), not a check per caller.
2. File collection drops a path whose resolved target leaves the root (git and fallback walk
   alike), recorded in the build's skip accounting rather than silently (R5.3); `_walk` does not
   descend into a symlinked directory.
3. `generate_onboarding` refuses to write or unlink when the output directory or a target file
   resolves outside the root — a loud refusal naming the path.
4. `orientation._read_text` and `diff_architecture`'s path argument are contained the same way.
5. A symlink that stays inside the root keeps working (a repo may symlink one of its own files).

## Constraints

- **R1.1** — generic over paths; no language branch.
- **R4.2** — deterministic: identical tree → identical rows.
- **Windows (237)** — `resolve()` semantics differ; the helper must not break a native-Windows
  build (junctions, drive letters). No new POSIX-only import in the runtime.
- Cost: containment is a `resolve()` per collected path — measure the no-op incremental on the
  fixture corpus and record it; do not regress 052's figure without saying so.

## Acceptance criteria

- **AC1** A repo with `leak.py → <tmp outside root>/secret.py` → the file is not indexed,
  `read_symbol` cannot return its body, and the build reports the skip. Red on today's code.
- **AC2** A repo whose `docs/onboarding` is a symlink to a directory outside the root →
  `generate_onboarding` refuses and writes nothing there. Red on today's code.
- **AC3** `overview.md` → outside file, alongside a valid `manifest.json` → refused, target
  unchanged.
- **AC4** `diff_architecture` with an absolute path or a `..` escape → refusal; a path under the
  root still works.
- **AC5** Fallback walk over a tree containing a symlink loop terminates.
- **AC6** An in-root symlink (`alias.py → src/real.py`) is still indexed (regression).

## References
`code_atlas/tools/generate_onboarding.py:355-363,430-457`; `code_atlas/indexer.py:736,1018-1030`;
`code_atlas/source_slice.py:42,61`; `code_atlas/onboarding/orientation.py:150-158`;
`code_atlas/tools/diff_architecture.py:109-113`; tickets 052 (no-op cost), 237 (Windows).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 342 — every read and write stays inside the indexed repo (working doc)

- **Ticket:** 342 · local · **SCOPE:** M · **TIER:** full · **TRACK:** backend
- **REVIEWER:** OFF (`--no-reviewer`) · **CHALLENGER:** ON
- **Current phase:** finalise
- **Session status:** done — autorun, PR open

## Phase 0 — Refine

`PREMISE: 7 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW1: a write through an **in-root** link is refused too — it would overwrite whichever file the link
names, source included. Citation: Goal ("writes into … resolves inside"), Scope 3.
HOW2: `diff_architecture`'s refusal is a new reason, `path_outside_root`, not `snapshot_not_found` —
"refused" is not "missing". Citation: R5.6; `nav_result.py` registry (one site, R6.7).
HOW3: stub roots (`collect_stubs`) and the index directory are left out and ticketed — neither is
named in Scope, and composer path repositories legitimately symlink packages into `vendor/`.
Citation: Scope 1–4; R7.1.

Recalled (advisory): `prove-the-guard-fails` — AC1/AC2/AC4 shown red on `main`'s code (Phase 3).

Exposure-checker: not dispatched — the ticket was written this session under the maintainer's
direction; the three items above are HOW with citations. Recorded in DISCLOSURE.

## Requirements matrix

`SECTIONS: 7 found (Why · Goal · Scope · Constraints · Acceptance · References · title) | 7 decomposed | ROWS: C=4 R=5 G=1 AC=6`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Goal | every read/write into the repo resolves inside it | D1–D4 | ✅ |
| R1 | Scope 1 | one containment helper | D1 | ✅ |
| R2 | Scope 2 | collection drops escaping paths, counted; `_walk` skips dir links | D2 | ✅ |
| R3 | Scope 3 | onboarding refuses to write/unlink outside | D3 | ✅ |
| R4 | Scope 4 | orientation + diff_architecture contained | D3 | ✅ |
| R5 | Scope 5 | in-root symlinks keep working | D2 | ✅ |
| C1 | R1.1 | generic, no language | D1 | ✅ |
| C2 | R4.2 | deterministic, incl. 3.12 vs 3.13 loops | D1 | ✅ |
| C3 | 237 | Windows-safe: pathlib only, no POSIX import | D1 | ✅ |
| C4 | 052 | collection cost measured and recorded | D4 | ✅ |
| AC1–AC6 | AC | proving | D4 | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: no site under `code_atlas/` resolves a path before reading or writing it; git hands
  back a tracked symlink like any file, and `Path.is_dir()` follows directory links.
- Blast radius: `_collect_with_census` + `indexable` (full and incremental share the rule — 047),
  `CollectionCensus` (persisted via `asdict`, published by `tools/collection.py`), onboarding
  `_write` / `_remove_recorded_pages`, `orientation._read_text`, `diff_architecture`, the reason
  registry and its test.

`TRACK: backend — 0/N UI`

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — R1.1 ✅ (no language) · R4.2 ✅ (loop → outside on both 3.12 and 3.13) · R5.3 ✅ (skip counted as skipped.escape; write refusals raise) · R5.6 ✅ (a new reason for refused, not missing) · R7.5 ✅ (comments ≤ 3 lines)`

`BASELINE: green`

Baseline: bare `pytest` on `2c184a4` (Linux, php · composer · node on PATH) → `4598 passed, 4 skipped`
(taken for 340 on the same base commit).

## Phase 2 — Design

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `prove-the-guard-fails` → traced: a script over `main`'s code shows AC1/AC2/AC4 happen (Phase 3).

| # | Change | File | k/N |
|---|--------|------|-----|
| D1 | `resolves_inside`, `require_writable` | code_atlas/containment.py | 1/1 |
| D2 | `_containment` (one resolve per dir, one lstat per file) in collection + `indexable`; `skipped_escape`; `_walk` skips dir links; census publishes `escape` when non-zero | code_atlas/indexer.py · code_atlas/tools/collection.py | 1/1 |
| D3 | onboarding writes/unlinks, orientation read, diff_architecture paths; `path_outside_root` | code_atlas/tools/generate_onboarding.py · code_atlas/onboarding/orientation.py · code_atlas/tools/diff_architecture.py · code_atlas/tools/nav_result.py | 1/1 |
| D4 | proving tests; reason registry test; docs + bookkeeping | tests/test_symlink_containment.py · tests/test_nav_reason_codes.py · docs/TOOLS.md · docs/BACKLOG.md · docs/TOKEN_LEDGER.md · docs/tasks/342_… | 1/1 |

| AC | risk | proof | provenance | match |
|----|------|-------|------------|-------|
| AC1 | escaping file indexed | pytest: collect/census/indexable + full build with the Python adapter | authored | ✅ |
| AC2 | symlinked onboarding dir | pytest, refusal + outside dir empty | authored | ✅ |
| AC3 | symlinked page beside manifest | pytest, refusal + target unchanged | authored | ✅ |
| AC4 | diff_architecture escape | pytest, absolute + `..` refused, in-tree reaches next check | authored | ✅ |
| AC5 | walk loop | pytest, `_walk` over `loop -> root` | authored | ✅ |
| AC6 | in-root link | pytest, `alias.py` kept | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_symlink_containment.py tests/test_generate_onboarding.py tests/test_nav_reason_codes.py -q`

Rejected alternatives: git's index mode (`120000`) as the sole symlink test (free, but blind to the
fallback walk and to a working tree that differs from the index); a check per caller (R6.7);
reusing `snapshot_not_found` (R5.6).

`SCOPE: M`

## Phase 3 — Execute

**Branch:** fix/342-symlink-containment

Ran at 5495fa0

```
$ .venv/bin/python -m pytest tests/test_symlink_containment.py tests/test_generate_onboarding.py tests/test_nav_reason_codes.py -q
40 passed
```

Red arm on `main`'s code (byte-identical `code_atlas/`): `collect()` returned `('src/leak.py',)` for a
link to a file outside the repo; `generate_onboarding` wrote `flows.md`, `index.html`,
`manifest.json`, `overview.md`, `tour.md` into the directory a symlinked `docs/onboarding` named;
`diff_architecture` parsed an absolute outside path (`incomplete_snapshot`, i.e. read). The two
guards added after review were mutation-checked: removing either turns its test red.

C4 — collection cost, `_collect_with_census` over this repo (1,047 kept files, median of 15):
`main` 20.5 ms → branch 33.1 ms, about 12 µs per kept file (one lstat, one resolve per directory),
so roughly +0.23 s per collect on a 19k-file repo. Recorded, not optimised: git's `120000` mode
would be free but is blind to the fallback walk.

Design conformance: D1–D4 as approved, plus the review round's five sites (below). The first gate
run went red on five pins this change moves — the core-module count (94 → 95, two files), the
newest-last reason (`path_outside_root`, two files) and one `diff_architecture` test that passed an
absolute fixture path from outside its tree (now copied in); updated, none weakened. The PLAN §19 row
first drafted was reverted — PLAN had one token of headroom, and the ticket holds the decision.

## Phase 4 — Review

REVIEWER: OFF (`--no-reviewer`) · CHALLENGER: ON — round 1 on `5e1d826`: **FINDINGS 5/2/1**.

| # | Finding | Disposition |
|---|---|---|
| A | indirection-rules, architecture-rules, capabilities TOML and ignore files were read through a committed link | fixed in `5495fa0`: rules files → `ConfigError`, capabilities → named refusal, ignore file skipped; tests added |
| C | `_indexable_untracked` listed an escaping untracked path | fixed in `5495fa0` (same `_containment`) |
| 7 | the cost figure was not recorded | recorded above (C4) |
| B | check-then-write is not atomic (TOCTOU) | accepted: the attacker is committed content, not a concurrent local process |
| 6 | native-Windows junction semantics not exercised on this host | can't tell — pathlib only, no new POSIX import; DISCLOSURE |

Verdict: `clean after fix (challenger only — REVIEWER: OFF)`; no round 2 dispatched.

## Phase 5 — Finalise (learning loop)

Lesson: `docs/LESSONS.md` § 342 — first sighting of `a-class-fix-enumerates-its-sites-by-grep`.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: 105707 · top cost driver: review/challenger ×1 (1 dispatch; main-loop unmeasured)`
