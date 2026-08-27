---
id: 166
slug: read-symbol-answers-from-pre-repair-state-and-calls-it-no-such-symbol
title: '`read_symbol` answers from the pre-repair state and reports `no_such_symbol` / `stale: false` — an identical second call returns the symbol'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [035, 014, 065]
---

## Why this exists (field retro round 10, 2026-08-26)

A confident false negative for a symbol merged that day, and a second identical call answered it
correctly — two tools disagreeing about the same symbol in the same index in the same minute:

```
call 1:  read_symbol(ImprovementUtility::buildPaginatorQuery)
         → found: false, reason: "no_such_symbol", stale: false      ← WRONG
call 2:  read_symbol(same args, seconds later)
         → found: true, line_start: 352, correct source              ← RIGHT
search:  search_symbol("buildPaginatorQuery")
         → found at line 352, reason: "ok"                           ← RIGHT, contradicts call 1
```

The retro's reading: **read-through repair fires but the answer is composed from the pre-repair
state**, and that answer is labelled with the one reason an agent is entitled to treat as proof of
absence. `no_such_symbol` at `stale: false` is the strongest negative the surface can emit; here it was
produced by a race, not by the graph.

Corroborating, and part of the same fault line: `get_index_status` reported **`dirty_indexed_files: 0`**
while the file's mtime was **1h45m after** `built_at`. The file-level dirty count was wrong at the same
moment the index-level `staleness: "behind"` was right.

**Note this is not the "missing reason" it looks like.** `read_symbol` already has `index_stale`
(`read_symbol.py:45-48`) and already re-queries after repair. The defect is **ordering and coverage of
the re-query**, which is a different and more serious fix than renaming a reason — the retro's own §15
runner-up understates it.

## Root cause — where to look

- `code_atlas/tools/read_symbol.py:64-88` — the miss path: `rows` empty → `guard.ensure_miss()` →
  on `"repaired"` the rows are re-fetched, and on a still-empty result `_resolve_miss` produces the
  terminal miss payload. The observed behaviour says one of these three is true, and **design must
  determine which before writing code**:
  1. `ensure_miss()` returned something other than `"repaired"` for a file whose hash had drifted (so no
     re-query ran at all);
  2. the re-query at `:84` ran against a store handle that does not see the repair's write;
  3. the repair is asynchronous or partial, so the re-query is correct-but-early.
- `code_atlas/tools/read_symbol.py:108-118` — the same re-query-after-repair shape on the **found**
  path, which must get whatever fix the miss path gets.
- The `dirty_indexed_files: 0` contradiction points at the freshness signal itself, not only at
  `read_symbol`: a file-level dirty count that reads `0` for a drifted file cannot gate a repair.

**A reproduction is the first deliverable.** The retro's evidence is two probes seconds apart; the
ticket must not assume the cause.

## Scope

1. Reproduce the two-calls-disagree sequence deterministically in a test (write a file, index, edit,
   read twice).
2. Fix the ordering so a repaired file's symbol is visible to the answer that triggered the repair.
3. If a case remains where the answer genuinely cannot be composed post-repair, it must report
   `index_stale`, **never** `no_such_symbol` — a negative that a race can produce must not wear the
   spelling reserved for proof of absence.
4. Check `dirty_indexed_files` against the same scenario and record whether it is the same fault or a
   separate one (a separate ticket if so — do not widen this one).

### Explicitly not in scope

- Making the index synchronous, or rebuilding on read.
- `search_symbol`'s behaviour, which was **correct** throughout this incident.
- The consuming repo's `CLAUDE.md` carve-out (*"a symbol you just wrote reads as absent"*) — it is
  their file; this ticket's job is to make the carve-out unnecessary, not to edit it.

## Constraints

- **R4.2** — the fix must be deterministic; a retry loop that sometimes wins is not a fix.
- **065** — an empty answer must say **why**, and the why must be the true one.
- **Cost** — `read_symbol` is the highest-frequency read on the surface. No extra query on the common
  path where nothing has drifted (061 shape).
- **R1.1 / R3** — no language branch, no contract bump.

## Acceptance criteria

1. A test reproduces the failure on the pre-fix code (write → index → edit → read) and passes after the
   fix: the **first** call returns the symbol.
2. No path can return `reason: "no_such_symbol"` with `stale: false` for a symbol whose file has drifted;
   such a case returns `index_stale`.
3. The clean path (no drift) is byte-identical and incurs no additional query.
4. The `dirty_indexed_files: 0` observation is checked and its verdict recorded — fixed here, or filed
   as its own ticket with evidence.
5. Determinism (R4.2); no bump (R3); no language branch (R1.1).

## References

Field retro round 10 §5 (**the round's second finding**), §4 (*"unmodelled silence dressed as a modelled
zero"*), §1 P2/P3/P4, §15 runner-up, §14 (**8-A: a new instance of the same class, uncovered**).
`code_atlas/tools/read_symbol.py:45-48,64-88,108-118`. Related: [035](035_read-through-freshness.md)
(read-through repair), [014](014_search-read-outline.md), [065](065_empty-answer-cannot-explain-itself.md).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 166 · **work_doc_mode:** embed · **Run args:** `--no-challenger` (skipped review); Gate 4 waived per AGENTS.md.
- **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Branch:** `fix/166-read-symbol-miss-repair-sees-committed-drift`
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** red (Windows `import fcntl`); delta-green via Docker.

## Phase 0 — refine

`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

Fully specified; the "which of three causes" is an investigation the ticket assigns to design/execute (reproduction-first), not a want-decision. Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 1 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=4 R=4 G=1 AC=5`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.5 (recalled handle: source-the-caveat-from-the-computation) N/A because the fix changes drift detection, not a reported caveat's source ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type — reproduction is the red run) ✅`
`BASELINE: red — bare pytest fails at collection (import fcntl, Windows platform exclusion); delta-green via Docker`

**Premise:** `read_symbol.py:45-48,64-88,108-118`, `freshness.py`, `staleness.py`, `gitutil.changed_paths` all resolve.
**Recall:** `073` (miss-driven freshness, by symbol/area), `source-the-caveat-from-the-computation` (R5.5, by handle — N/A, see rule sections).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | first call must not report a confident false `no_such_symbol` for a drifted-in symbol | make the answer that triggered the repair see it | `read_symbol.py:64-88` | open |
| R1 | Scope 1 | reproduce the two-calls-disagree sequence deterministically | write→index→edit(commit)→read; red pre-fix | repro test | open |
| R2 | Scope 2 | fix the ordering so a repaired file's symbol is visible to the triggering answer | miss-repair must see committed drift, then re-query | `freshness.py:91`, `read_symbol.py:83-84` | open |
| R3 | Scope 3 | a case that can't compose post-repair → `index_stale`, never `no_such_symbol` | >1 drifted file → stale | `read_symbol.py:69-82` | open |
| R4 | Scope 4 | check `dirty_indexed_files` — same fault or separate; separate ticket if so | record verdict | `staleness.py:21-34` | open |
| AC1 | AC 1 | test reproduces on pre-fix (write→index→edit→read), passes after: first call returns the symbol | Falsifiable: red→green repro | repro test | open |
| AC2 | AC 2 | no path returns `no_such_symbol`/`stale:false` for a drifted file; returns `index_stale` | Falsifiable: multi-drift → index_stale | repro test 2 | open |
| AC3 | AC 3 | clean path byte-identical, no extra query | Falsifiable: found path untouched; `test_untouched_file_does_not_call_adapter` | existing test | open |
| AC4 | AC 4 | `dirty_indexed_files:0` checked, verdict recorded | Falsifiable: verdict + evidence | working doc | open |
| AC5 | AC 5 | determinism (R4.2), no bump (R3), no language branch (R1.1) | Falsifiable: deterministic git query; grep-gate | — | open |
| C1 | Constraint | R4.2 deterministic — not a retry-loop | drift detection is deterministic (git diff) | binding |
| C2 | Constraint | 065 — empty answer says the *true* why | index_stale over no_such_symbol on drift | binding |
| C3 | Constraint | Cost — no extra query on the clean (no-drift) common path | miss path only; found path untouched | binding |
| C4 | Constraint | R1.1 / R3 — no language branch, no bump | — | binding |

### Root cause (taxonomy: data / freshness)

**Reproduced deterministically** (first deliverable): the miss-repair (`freshness.dirty_indexed_paths` → `gitutil.dirty_paths`) keys on the **working tree vs HEAD** only. A file changed and **committed** after the index was built is not working-tree-dirty, so `ensure_miss()` finds no candidate, returns `"ok"`, and no repair fires — `read_symbol` composes `no_such_symbol`/`stale:false` from the stale index. This is exactly the field clue: `staleness: "behind"` (index commit ≠ HEAD, correct) with `dirty_indexed_files: 0` (working tree clean, also correct). Of the ticket's three candidate causes it is **cause 1** — `ensure_miss()` returned `"ok"` (not `"repaired"`) because its dirty signal was blind to committed drift; not a store-handle or async-repair issue.

### Blast radius

- `code_atlas/tools/freshness.py::dirty_indexed_paths` — the single fix point.
- Consumers of `ensure_miss` (which calls it): `read_symbol.py:68`, `search_symbol.py:178`. The change makes both miss paths see committed drift; search was already correct and is only improved (ticket-consistent).
- Existing direct test `test_dirty_indexed_paths_ignores_non_indexed_suffixes` (working-tree edit) stays green — working-tree drift is a subset of `changed_paths`.
- No change to `read_symbol.py` itself (its `ensure_miss`→re-query ordering is already correct once the candidate is found), to the contract, or to the resolver.

## Phase 2 — design

### Approach

`dirty_indexed_paths` measures drift against the **indexed commit**, not just the working tree: read `LAST_COMMIT_KEY` from the store; when present, use `gitutil.changed_paths(root, last_commit)` (which unions `indexed_commit..HEAD` with the working-tree diff), else fall back to `dirty_paths` (non-git / legacy index). Intersect with indexed suffixes as before. Then `ensure_miss()`'s existing single-candidate logic does the rest: exactly one drifted indexed file → repair it → `read_symbol` re-queries and returns the symbol (AC1); more than one → `"stale"` → `read_symbol` returns `index_stale` (AC2); none → `"ok"` → genuine `no_such_symbol` (correct).

### Rejected alternatives

- **Relabel `no_such_symbol`→`index_stale` whenever the index is behind HEAD, without repairing.** Satisfies AC2 but not AC1 (the first call would not *return the symbol*). The real fix repairs when it can; relabelling is the fallback the existing `>1 candidate` path already gives.
- **Scan every indexed file's stored hash vs disk on each miss.** Detects drift without git, but O(files) per miss — violates the cost constraint. `changed_paths(since=indexed_commit)` is one bounded git call already paid for on the miss path.

### Assumptions

| Assumption | Tag |
|---|---|
| `changed_paths(root, indexed_commit)` = committed-since ∪ working-tree drift | verified (gitutil.py:67-82; `test_incremental` pins it) |
| The index stores its build commit under `LAST_COMMIT_KEY` | verified (staleness.py uses it) |
| Repro: a committed edit makes the working tree clean, defeating the old signal | verified (reproduction test is red pre-fix) |

No unresolved novel-untested assumption — the reproduction test is the integration proof.

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `dirty_indexed_paths` uses `changed_paths(since=indexed_commit)` w/ working-tree fallback | `code_atlas/tools/freshness.py` | `ensure_miss` (read_symbol + search_symbol miss paths); existing direct test stays green | R2, R3, AC1, AC2, AC5 | 1/1 |
| Reproduction tests (committed drift; multi-drift→index_stale) | `tests/test_freshness_cannot_find_what_is_not_indexed.py` | new tests | R1, AC1, AC2 | 1/1 |
| AC4 verdict on `dirty_indexed_files` | working doc | none | R4, AC4 | 1/1 |
| Docs: BACKLOG, TOKEN_LEDGER, LESSONS | `docs/*` | R7.2 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `source-the-caveat-from-the-computation` (R5.5) — **traced.** This fix changes *drift detection*, not the source of a reported caveat, so R5.5's falsifier (a value honest about its source but false about its subject) does not apply. Confirmed the fix reads drift from the git computation that owns the whole "is this file behind the index" fact:
  ```
  $ grep -n "def changed_paths" code_atlas/gitutil.py
  67:def changed_paths(root: Path, since: str) -> tuple[str, ...] | None:
  ```

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (git repo + index + committed edit) | integration (reproduction test) | ✅ |
| AC2 | integration (two committed-drifted files) | integration | ✅ |
| AC3 | logic (found path untouched; no extra query) | existing `test_untouched_file_does_not_call_adapter` | ✅ |
| AC4 | analysis (verdict) | manual-recorded (verdict + evidence) | ✅ |
| AC5 | logic (deterministic git diff) + guard (R1.1) | integration + grep-gate | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

### Proving test

`test_read_symbol_miss_repairs_committed_drift` — fails pre-fix (`no_such_symbol`), passes after (`found: true`, `reason: ok`); plus `test_read_symbol_committed_multi_drift_is_index_stale_not_absent` for AC2. `pytest tests/test_freshness_cannot_find_what_is_not_indexed.py -k committed`.

### AC4 verdict — `dirty_indexed_files: 0` is a SEPARATE signal, not the same fault

`get_index_status`'s `dirty_indexed_files` comes from `staleness.dirty_indexed`, which by design (047) counts **working-tree-dirty** indexed files — for committed drift that is genuinely 0, and the same payload's `staleness: "behind"` already carries the commit-drift signal. So the field is **correct as defined**; the fault was that `read_symbol`'s *miss-repair* consumed only the working-tree signal, which this ticket fixes. **Not the same fault, not a defect → no separate ticket.** Optional (non-bug) follow-up noted in BACKLOG: whether the field's *name* invites the misread. Evidence: `staleness.py:21-34` (working-tree source) vs `staleness_of` returning `behind` on `last_commit != head` (staleness.py:41).

### Rollback + porting

Rollback: revert `freshness.py` + the two tests. Porting: `app` only.

### SCOPE

`SCOPE: M` — one function + tests + bookkeeping; branch `fix` matches (a correctness bug).

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `dirty_indexed_paths` drift vs indexed commit via `changed_paths`, working-tree fallback | implemented-as-approved |
| `ensure_miss` single-candidate logic unchanged (repair → re-query, else stale) | implemented-as-approved (no edit needed) |

No deviations. Diff ⊆ approved list.

### Empirical outputs

Reproduction on **pre-fix** code (Docker):
```
>       assert result["reason"] == REASON_INDEX_STALE
E       AssertionError: assert 'no_such_symbol' == 'index_stale'
2 failed, 7 deselected
```
After fix (Docker): `ruff → All checks passed! · mypy → MYPY-OK (72 files) · freshness tests → 16 passed`.
Full suite: `2122 passed, 1 skipped, 0 failed (263.78s)`.

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_read_symbol_miss_repairs_committed_drift` (red→green) |
| AC2 | `test_read_symbol_committed_multi_drift_is_index_stale_not_absent` |
| AC3 | existing `test_untouched_file_does_not_call_adapter`; found path untouched |
| AC4 | verdict recorded above (separate signal, not a defect) |
| AC5 | R1.1 grep clean; deterministic `git diff`; no contract change |

## Phase 5 — finalise

**Delta-green (Docker/Linux):** full suite `2122 passed, 1 skipped, 0 failed`; ruff+mypy green (72 files). Bare pytest red on Windows (`fcntl`) — recorded exclusion.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`166-C1` (type-2, `drift-is-vs-the-index-commit-not-the-working-tree`, seen: 166) recorded as `proposed`. seen=1 → stays in lessons_path. Relates to 073/047.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; review phase skipped by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer + challenger waived; no `Reviewed at` marker → stale-review guard waived. Self-checks: reproduction red→green, full suite delta-green, ruff/mypy green.
