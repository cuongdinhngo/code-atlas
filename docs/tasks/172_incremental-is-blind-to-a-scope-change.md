---
id: 172
slug: incremental-is-blind-to-a-scope-change
title: 'An incremental build is blind to a scope change — 3,244 newly-in-scope files reported as `wrote.files: 0`, beside a census that counts them'
phase: 1.5b
milestone: Freshness
status: done
depends_on: [016, 060, 053]
---

## Why this exists (field episode, 2026-08-27 — the roll-out attempt)

The maintainer wired the second adapter into the anchor repo — the one change every round since 9 has
named as binding — restarted the server, and ran a build. It reported success and did nothing:

```
collection: kept: 22381,  indexed_suffixes: 8 suffixes   ← the walk sees the new scope
build:      wrote.files: 0                               ← nothing was parsed
status:     graph.files: 19137                           ← the graph is unchanged
elapsed:    2.6 s
```

> *"Payload trung thực nhưng tự mâu thuẫn về hiệu quả: `kept: 22381` nằm cạnh `graph.files: 19137`
> với `wrote: 0`. Em mất một vòng build vô ích vì thiếu cái này."*

The collector knew there were 3,244 files newly inside the scope. The incremental planner never
considers them, and no field says so. **A build that cannot act on the request must not answer like a
build that had nothing to do** — that is 060's rule, one layer up: 060 fixed *delta counts wearing
total field names*; this is *a refusal wearing a no-op's clothes*.

## Root cause

- `code_atlas/indexer.py:212` — `candidates = sorted((changed_set | dependents) & wanted)`.
  `changed_set` is the git delta and `dependents` are files targeting affected qnames. A file that
  entered scope because an **adapter** was added is neither, so it is never a candidate and
  `to_parse` is empty.
- `code_atlas/indexer.py:163-166` — the escalation this needs **already exists**, for a different
  axis: a stored `contract_version` that differs forces `full_build` ("*vocabulary changed —
  incremental would mix eras*", task 030 AC1). The suffix set is the same class of change and is not
  checked, though `store.get_meta(INDEXED_SUFFIXES_KEY)` holds the previous value
  (`store.py:37`, written at `indexer.py:820`).
- `code_atlas/indexer.py:193-195` — `wanted` is already the newly-collected set, so
  `wanted - set(store.file_paths())` names exactly the newly-in-scope files with **no new query**.

## Scope

Make a scope change a first-class build input, not an invisible one.

1. Compare the announced suffix set against `indexed_suffixes` in meta. When they differ, the build
   must not silently no-op. Design picks one of three and records the rejected two:
   - escalate to `full_build` (matches the `contract_version` precedent);
   - a **suffix-scoped** pass — parse `wanted - indexed` only, which is the right unit of work for
     "a language was added" and avoids re-parsing 19,137 unaffected files;
   - refuse: `mode: "scope_changed"` + `try_instead: full=true`.
2. Whatever is chosen, the report names it, so `wrote.files: 0` can never again mean two different
   things (060).
3. The escalation lives in `indexer.update`, **not** in a caller — `code-atlas-refresh` (053) and the
   MCP tool must both inherit it. A fix in one caller leaves the git hook in the same trap.

### Explicitly not in scope

- The `unconfigured_adapters` cost figure — [174](174_unconfigured-adapters-names-the-switch-not-the-cost.md).
- What the payload *claims* about coverage after such a build — [173](173_coverage-claims-key-on-configured-not-indexed.md),
  which is the dangerous half and should land with this one.
- Config reload — [175](175_config-is-loaded-at-spawn-and-nothing-says-so.md).

## Constraints

- **Cost** — the suffix-scoped option must be measured against the full rebuild it replaces; the
  no-op path (matching suffix sets) stays at today's ~2.6 s and adds no query (080, 096).
- **R4.3** — the write lock is unchanged; a busy peer is still a clean skip.
- **061** — a build whose scope did not change is byte-identical in its report.
- **R1.1** — the comparison is over suffix strings from the handshake; no language named in the core.
- **R4.2** — deterministic: same tree + same adapters ⇒ same decision.

## Acceptance criteria

1. A test adds an adapter (a second suffix) between two builds and asserts the second build does not
   report a successful no-op — it escalates, scopes to the new suffix, or refuses with a named
   `mode`. Fails on today's code.
2. The chosen behaviour is reported in the build payload; `wrote.files: 0` is unambiguous.
3. `code-atlas-refresh` inherits the behaviour, pinned by a test that goes through the hook path.
4. A build with an unchanged suffix set is byte-identical and pays no extra query (measured).
5. If the suffix-scoped pass is chosen, its cost against a full rebuild is measured and recorded.
6. Determinism (R4.2), no language branch (R1.1), no contract bump (R3).

## References

Field episode 2026-08-27 (the roll-out attempt), findings (1) and (5). Round 11 §13 measured the
adapter working on the anchor's real front end at 53.2 % RESOLVED while unwired; this is the first
thing a maintainer hits when acting on that. `code_atlas/indexer.py:163-166,193-195,212,820`;
`code_atlas/store.py:37`. Related: [016](016_incremental-git.md) (the path),
[060](060_build-report-scale-naming.md) (a report that cannot mean two things),
[053](053_refresh-on-checkout-hook.md) (the second caller),
[173](173_coverage-claims-key-on-configured-not-indexed.md) (ship together).

## Session status

- **KEY:** 172 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, 8-ticket batch) · envelope in `.mango/run-contract-172.txt`.
- **Branch:** `feat/172-incremental-sees-a-scope-change`
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2196 passed, 0 failed` at `f0134e6` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

Scope 1 names three candidate behaviours and asks design to pick one and record the rejected two. A
**how-decision**: the ticket's own root cause cites the `contract_version` precedent, and the
correctness argument for each candidate is readable from the source. Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=5 R=3 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 10 applicable — 9 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R1.8 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R4.3 (change-type) ✅ · §R5.4 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type) ✅ · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ · §R7.2 (change-type) ✅`
`BASELINE: green — 2196 passed, 0 failed, 0 skipped at f0134e6 (bare pytest, Linux host)`

**Premise:** `indexer.py:212` (`candidates = (changed_set | dependents) & wanted`), the
`contract_version` escalation, `wanted` already being the newly-collected set, and
`INDEXED_SUFFIXES_KEY` holding the previous value all resolve as described.

**One premise surfaced as ambiguous, not blocking.** The ticket cites `indexer.py:820` for the
suffix stamp; 173 (merged earlier in this batch) added two stamps beside it and moved the line. The
fact is unchanged; the line number is not.

**Recall:** `derived-not-listed-invariant` (R6.7, by handle — the comparison must derive the announced
set from the handshake, never list suffixes; traced below). `060` (by area: a report that cannot mean
two things) — the rule this applies one layer up.

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | 3,244 newly-in-scope files must not report as `wrote.files: 0` | make a scope change a build input | field payload | open |
| R1 | Scope 1 | compare announced suffixes against `indexed_suffixes`; on difference do not silently no-op | pick escalate / suffix-scoped / refuse | `indexer.py:163-166` | open |
| R2 | Scope 2 | the report names what it did, so `wrote.files: 0` is unambiguous | a payload field naming the escalation | `060` | open |
| R3 | Scope 3 | the escalation lives in `indexer.update`, not a caller | both callers inherit | `refresh.py` | open |
| AC1 | AC 1 | adding a suffix between two builds does not report a successful no-op — fails today | Falsifiable: red→green | proving test | open |
| AC2 | AC 2 | the chosen behaviour is in the payload | Falsifiable: `scope_change` asserted | proving test | open |
| AC3 | AC 3 | `code-atlas-refresh` inherits, pinned through the hook path | Falsifiable: hook subprocess | proving test | open |
| AC4 | AC 4 | unchanged suffix set is byte-identical and pays no extra query (measured) | Falsifiable: no field, mode unchanged, timed | proving test | open |
| AC5 | AC 5 | **if** the suffix-scoped pass is chosen, measure it against a full rebuild | N/A — not chosen; reason recorded | design | open |
| AC6 | AC 6 | R4.2, R1.1, no bump (R3) | Falsifiable: grep-gates, no `contract.py` edit | `gate.sh` | open |
| C1 | Constraint | the no-op path stays at today's ~2.6 s and adds no query | one meta read the build already makes | — | binding |
| C2 | Constraint | R4.3 — the write lock is unchanged; a busy peer is still a clean skip | do not touch the lock | — | binding |
| C3 | Constraint | 061 — a build whose scope did not change is byte-identical in its report | omit the field | — | binding |
| C4 | Constraint | R1.1 — the comparison is over suffix strings from the handshake | no language named | — | binding |
| C5 | Constraint | R4.2 — same tree + same adapters ⇒ same decision | set comparison | — | binding |

### Root cause (taxonomy: config / planning)

The incremental planner's candidate set is `(git delta ∪ dependents) ∩ wanted`. A scope change moves
`wanted` and touches neither of the other two, so the newly-in-scope files are structurally
unreachable — and the report has no vocabulary for *"I could not act on this request"*, so it reuses
the vocabulary for *"there was nothing to do"*.

### Blast radius

- `indexer.py`: one sentinel exception, one check after `_owners`, one `except` clause, one optional
  `scope` parameter. `full_build` untouched.
- `build_or_update_index.py`: `_run` gains the `scope` dict and returns `FULL` when it escalated;
  `_build` merges it into the payload.
- Both callers of the build tool inherit — including `code-atlas-refresh`, which is the point of R3.
- **An existing test became env-sensitive because of this change** (see *Empirical outputs*).

## Phase 2 — design

### Approach

`incremental_update` compares `{suffix.lower() for suffix in owners}` against
`INDEXED_SUFFIXES_KEY`, immediately after `_owners(announced)` — the first point where the announced
set is known. On a difference it raises a module-private `_ScopeChanged`, caught one frame out, which
records the change in the caller-supplied `scope` dict and returns `full_build(...)`.

The sentinel is raised *inside* the `try` whose `finally` stops every adapter, so the escalation
cannot leak a process. `scope` is filled in place — the same idiom `phase_times` already uses (052) —
so no existing caller's signature changes and the escalation is reportable without putting a
non-count inside `wrote` (060).

### Rejected alternatives

- **A suffix-scoped pass** — parse `wanted - indexed` only. This is the ticket's own preferred shape
  and it is the one I did not take, so the reason matters. It is not obviously equivalent to a full
  build: a new adapter can take ownership of a suffix an *existing* adapter already owned, and it can
  make edges from **existing, unmodified** files resolvable for the first time. Parsing only the new
  files would then rely on `delta_scope`'s inbound-edge reasoning being complete for a case it was not
  designed for (096 scoped it to a parse delta, not a vocabulary delta). That is a novel correctness
  argument, on the write path, for a saving on a one-off post-config build. AC5 asks for a measurement
  *if* this is chosen; it was not, so no measurement is recorded — and that absence is deliberate,
  not an omission.
- **Refuse with `mode: "scope_changed"` + `try_instead: full=true`.** Honest, but it makes the caller
  responsible for knowing the retry. `code-atlas-refresh` is a git hook that always exits 0 and
  reports nothing; under a refusal it would silently do nothing forever, which is the same trap in a
  new costume. A build that *can* act should act.
- **Check in `build_or_update_index` instead.** Rejected by Scope 3 (R1.8): the hook calls the tool,
  but a fix in the tool leaves any future direct `indexer.update` caller in the trap.

### Assumptions

| Assumption | Tag |
|---|---|
| `owners` keys are the announced suffixes, lowercased in the stamp | verified (`_record_meta` lowercases; the check lowercases the same way) |
| An escalation cannot leak an adapter process | verified — the sentinel is raised inside the `try` whose `finally` stops them; the proving tests would hang otherwise |
| A pre-172 index (no stamp) must not escalate | verified — `stored is None` returns early |
| `full_build` re-announces, so the escalation costs one extra announce round-trip | verified, and accepted: it is paid only on a scope change |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `_ScopeChanged` + `_require_unchanged_scope` + the `except` clause + `scope` param | `code_atlas/indexer.py` | both callers inherit | R1, R3, AC1, AC3 | 1/1 |
| `_run`/`_build` thread `scope`; payload carries `scope_change`; mode reads `full` | `code_atlas/tools/build_or_update_index.py` | payload gains a field only on escalation | R2, AC2, AC4 | 1/1 |
| Proving tests (6) | `tests/test_scope_change_escalates.py` (new) | new file | AC1–AC4 | 1/1 |
| Pin the profiler test's adapter set | `tests/test_profile_incremental.py` | fixes an env-sensitivity this change exposes | AC1 | 1/1 |
| README; BACKLOG; ledger; working doc | `README.md`, `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `derived-not-listed-invariant` (R6.7) — **traced.** The announced set is derived from the handshake
  via `owners`; no suffix is written down in the core:

  ```
  $ grep -n "now = {suffix.lower() for suffix in owners}" code_atlas/indexer.py   # Ran at f10e519976d937ddcfe35787e6812fe435755bb6
  now = {suffix.lower() for suffix in owners}
  ```

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (two real builds, two real adapters, a real git repo) | integration test ×2 | ✅ |
| AC2 | logic (payload field) | integration test | ✅ |
| AC3 | integration (the hook binary in a subprocess) | integration test | ✅ |
| AC4 | logic (no field, mode unchanged) + measurement (timed no-op builds) | integration test ×2 | ✅ |
| AC5 | N/A — the suffix-scoped pass was not chosen | design record | ✅ |
| AC6 | guard (grep-gates) + logic (no `contract.py` edit) | `gate.sh` | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

AC5 is **not** an exclusion: it is conditional on a choice the design did not make, and its condition
is recorded with its reason above.

### Proving test

`tests/test_scope_change_escalates.py::test_a_new_adapter_is_not_a_silent_no_op` — plus
`::test_the_newly_scoped_file_actually_lands_in_the_graph`, because an escalation that reported
itself but indexed nothing would satisfy the payload assertion and none of the point.

### Rollback + porting

Rollback: revert both source files and the test file; the profiler-test hardening is safe to keep.
No persisted state, no schema change. Porting: `app` only.

### SCOPE

`SCOPE: M` — one guard in the incremental planner plus its report; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Compare announced suffixes to the stamp, right after `_owners` | implemented-as-approved |
| Sentinel raised inside the adapter-stopping `try` | implemented-as-approved |
| Escalate to `full_build`, matching the `contract_version` precedent | implemented-as-approved |
| `scope` filled in place (the `phase_times` idiom); no non-count inside `wrote` | implemented-as-approved |
| Lives in `indexer.update`, so both callers inherit | implemented-as-approved |
| A pre-172 index (no stamp) does not escalate | implemented-as-approved |

No deviations. Diff ⊆ approved list.

### Empirical outputs

**The field contradiction, reproduced at fixture scale** (the scope check removed):

```
$ .venv/bin/python  (reproduction, pre-172)          # Ran at f0134e62064a3ec490d103627ed60a352af78bbf
PRE-172, after wiring a second adapter and running a build:
  build   mode: incremental  wrote.files: 0  scope_change: False
  collection kept: 2  claimed_suffixes: ['.aa', '.bb', '.cc']
  status  graph.files: 1
```

`kept: 2` beside `graph.files: 1` with `wrote.files: 0` — the field episode's three rows.
(`claimed_suffixes` is 173's field, landed earlier tonight, already making the *state* honest while
the *build* was still silent. The two tickets are the pair the retro said to ship together.)

**Red run — the scope check removed:**

```
$ .venv/bin/pytest -q tests/test_scope_change_escalates.py   # Ran at f0134e62064a3ec490d103627ed60a352af78bbf
E       KeyError: 'scope_change'
E           AssertionError: assert None is not None
E            +  where None = file_hash('src/c.cc')
E           AssertionError: the hook path escalated too
3 failed, 3 passed
```

The second failure is the one that matters: the newly-in-scope file is simply not in the graph, and
the third proves the hook path fails the same way.

**A regression this change caused, found and fixed rather than waived.** With the fix in, the full
suite went red on `test_profile_incremental::test_phase_times_cover_named_phases_and_sum_near_wall`.
The cause is real: the profiler reads `os.environ` while the build under test reads an explicit env
dict, so an ambient `CA_<LANG>_CMD` makes the two announce different suffix sets — which this change
now (correctly) escalates on, turning a phase-timing measurement into a full build with no phase
times:

```
$ (probe)                                             # Ran at f0134e62064a3ec490d103627ed60a352af78bbf
noop wall 0.3854 sum 0.0424 unattr 0.343 ok False
    {'announce': 0.0424, 'tree_walk': 0.0, 'reconcile': 0.0, 'hashing': 0.0, 'parse': 0.0, ...}
```

Every phase after `announce` is zero — the signature of an escalation. Confirmed environmental:

```
$ env -u CA_PHP_CMD .venv/bin/pytest -q tests/test_profile_incremental.py   →  3 passed
$ CA_PHP_CMD=... .venv/bin/pytest -q tests/test_profile_incremental.py      →  1 failed, 2 passed
```

`gate.sh` runs pytest **without** `CA_PHP_CMD`, so the gate would have stayed green and hidden it.
The test is now pinned to its own adapter set instead. It was passing before only because the extra
adapter was being silently ignored — which is the defect this ticket removes.

**Green run** (with the ambient adapter set deliberately present, the harder case):

```
$ CA_PHP_CMD=… .venv/bin/pytest -q                     # Ran at f10e519976d937ddcfe35787e6812fe435755bb6
2200 passed  (2 bookkeeping failures at the time of the run: this task's own BACKLOG/ledger rows,
              written after it — green in the gate below)
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_a_new_adapter_is_not_a_silent_no_op` + `test_the_newly_scoped_file_actually_lands_in_the_graph` + the red run |
| AC2 | `scope_change` asserted exactly, including `mode: "full"` |
| AC3 | `test_the_git_hook_inherits_the_escalation` — the hook binary in a subprocess |
| AC4 | `test_an_unchanged_scope_is_byte_identical` (no field, `mode: incremental`, `wrote.files: 0`) and `test_the_no_op_path_pays_no_extra_query` (timed) |
| AC5 | N/A, with the reason recorded: the suffix-scoped pass was rejected, so its measurement is not owed |
| AC6 | `gate.sh` R1.1/R2.2 green; `test_a_removed_adapter_is_named_too` shows the decision is a deterministic set difference; no `contract.py` edit ⇒ no bump |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2196 passed / 0 failed` at `f0134e6` →
`2206 passed / 0 failed` (gate). ruff + mypy green.

### Learning loop

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 1 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`172-C1` (type-2, `a-planner-must-be-told-when-its-input-set-moved`, seen: 172) recorded as
`proposed`. A delta planner is correct only while the *universe* it filters is fixed; when the
universe moves, the delta is silently wrong and the report has no word for it. Not falsified — the
red run shows the file simply missing from the graph.

`176-C1` (type-2, `a-test-must-strip-the-ambient-adapter-env`, seen: 176, **172**) — **recurring.**
176 hit it in a negative-control test that inherited the gate's `CA_PHP_CMD`; 172 hit it in a
phase-timing test where the ambient adapter changed what the build did. **Cannot promote yet:**
recurrence is 2 within one batch by one author, and `/mango:promote` is the cross-ticket path. Routed
nowhere; noted for it.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived — nothing but the author
looked at this diff; recorded as line one of `DISCLOSURE`. No `Reviewed at` marker ⇒ the stale-review
guard is waived. Self-checks: the field contradiction reproduced, a red run, a self-caused regression
found and fixed rather than waived, full suite delta-green, ruff/mypy green.
