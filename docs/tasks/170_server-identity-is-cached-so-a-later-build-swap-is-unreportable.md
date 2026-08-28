---
id: 170
slug: server-identity-is-cached-so-a-later-build-swap-is-unreportable
title: '`server_identity` is `@lru_cache`d, so the divergence check runs once — a build swap after the first payload can never be reported, and silence does not say which'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [164, 162, 125]
---

## Why this exists (field retro round 11)

164 fixed 10-A and round 11 verified it **non-circularly** (`/proc` + `stat` + `git reflog`, never the
stamp itself): the process imported at a tree carrying `e591f02`, the repo later moved to `331ac06`, and
every payload correctly read `e591f02`. That half works and it is what made round 11's §12 possible at
all. **The remaining half does not fire:**

```
21:18:48  appended a comment to code_atlas/build_info.py — a real content change to a loaded module,
          48 minutes after import
then      read_symbol(...)                    → server_build: "e591f02", no stale_process
          get_index_status --verbose --sign   → server_build: "e591f02", no stale_process, no repo_head
```

> Round 11 §12.c: *"**Closed — with a narrow third layer.** … Whether that is by design or a defect
> **I cannot tell from the payload** — and R-2 says that inability is the finding. The practical
> consequence is small; the reporting consequence is not: **a reader cannot distinguish "no divergence
> detected" from "divergence not checked."**"*
> §0.a: for the last 12 minutes of the session the checkout genuinely differed from the process and no
> payload said so — *"harmless here **only because** the delta was a docs-only commit… The harmlessness
> was luck of the delta, not a property of the design."*
> §14.a adds the carve-out this ticket exists to retire: ***`server_build` names the loaded code, not
> the current checkout.***

## Root cause

- `code_atlas/build_info.py:77` — `@lru_cache(maxsize=1)` on `server_identity()`. The divergence
  comparison at `:89` (`_content_build_id() == _LOADED_BUILD_ID`) therefore runs **once**, on the first
  call, and every later payload reuses that dict. A swap after the first answer is structurally
  unreportable — which is the same *class* of staleness 164's own docstring (`:3-9`) says the field
  exists to make legible in-band.
- `code_atlas/build_info.py:89-97` — the matching branch returns `{version, build}` and the diverged
  branch adds `stale_process` / `repo_head`. **Absence of the field is the only signal of the matching
  case**, so a payload cannot say *"checked, and the disk still matches"*; 061's omit-when-empty rule is
  correct for a value and wrong for a **verdict**.
- The cost that motivated the cache is real and measured: 164 recorded the hash walk at **6.35 ms /
  72 files / 780 KB** (`docs/TOKEN_LEDGER.md`, row 164). Re-hashing on every payload is not the answer;
  a cheaper freshness probe is.

## Scope

Make the divergence verdict live, and make it legible.

1. The divergence check re-evaluates after the first call, at a cost that does not scale with payload
   count — design picks and records the probe (an `st_mtime`/`st_size` sweep of the loaded modules; a
   bounded interval; an explicit invalidation) and states its rejected alternatives.
2. A reader can distinguish **checked-and-matching** from **not-checked**. One field, one verdict; the
   design records whether it rides every payload or only `get_index_status` + `sign`.

### Explicitly not in scope

- Reloading modules, restarting, or acting on the divergence. The tool reports; the operator restarts.
- The `+dirty` worktree axis (`:51`) — orthogonal and already correct.
- Changing `_LOADED_BUILD_ID`'s freeze-at-import semantics: that is 164's fix and it verified.

## Constraints

- **Cost** — no full re-hash per payload. The added per-call cost is measured and recorded against
  164's 6.35 ms baseline and the tokens-to-answer gate.
- **R4.2** — identical loaded artifact ⇒ identical id, across processes and hosts; no timestamps in the
  id itself.
- **061** — if the verdict field is added to every payload, its bytes are measured and pinned (164's
  stamp is already 49 B unconditional, measured in round 11 §6); if it is not, the omission is a
  recorded design decision, not an accident.
- **R1.1** no language branch · **R3** no bump · the wheel / no-checkout path (125) unchanged.

## Acceptance criteria

1. A test simulates a post-first-call divergence (loaded module content changes after `server_identity`
   has already answered once) and the next payload reports it — fails on today's code.
2. A payload can be read as *checked and matching* rather than as *silent*; pinned for both the matching
   and the diverged case.
3. The added per-call cost is measured, recorded, and does not re-hash the package tree per payload.
4. A server whose disk never moves is byte-identical to today, or the byte delta is measured and pinned.
5. The wheel / no-checkout path still names a build (125) and is unchanged; the `+dirty` axis unchanged.
6. Determinism (R4.2), no language branch (R1.1), no contract bump (R3).

## References

Field retro round 11 §12.c (**the third layer**), §0.a (12 minutes of undisclosed divergence in the
session itself), §14 row 10-A (verified, layer noted), §14.a (the new carve-out this retires), §6
(the 49 B unconditional stamp). `code_atlas/build_info.py:3-9,51,77,89-97`; 164's measured hash-walk
row in [`TOKEN_LEDGER.md`](../TOKEN_LEDGER.md). Related:
[164](164_server-build-names-the-repo-not-the-running-process.md) (the fix this completes),
[162](162_a-build-swap-is-invisible-on-every-payload-but-get-index-status.md),
[125](125_no-payload-names-the-server-build.md).

## Session status

- **KEY:** 170 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended batch) · envelope in `.mango/run-contract-170.txt`.
- **Branch:** `feat/170-server-identity-is-cached` (stacked on `feat/174-…`)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2390 passed, 0 failed` at `739435e` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

Both are how-decisions the ticket delegates by name:

1. Scope 1 — *"design picks and records the probe (an `st_mtime`/`st_size` sweep of the loaded
   modules; a bounded interval; an explicit invalidation) and states its rejected alternatives."*
   → *Approach* / *Rejected alternatives*, **decided on a measurement that changed the answer**.
2. Scope 2 — *"the design records whether it rides every payload or only `get_index_status` +
   `sign`."* → *Approach*, with the byte cost measured and re-pinned.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous`
`RECALL: 2 claim(s) surfaced | 1 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=4 R=2 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 10 applicable — 9 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.6 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.7 (change-type) ✅ · §R7.2 (change-type) ✅ · §R7.4 (change-type) ✅ · §R7.6 (change-type) ✅ — CONVENTION went over budget and was pruned`
`BASELINE: green — 2390 passed, 0 failed, 0 skipped at 739435e (bare pytest, Linux host)`

**Premise:** every citation resolves. `build_info.py:77` is `@lru_cache(maxsize=1)` on
`server_identity()`; the comparison at `:89` therefore runs once per process. The matching branch at
`:89-90` returns two fields and the diverged one at `:91-97` adds two more, so **absence is the only
signal of the matching case**. 164's measured hash walk (6.35 ms / 72 files / 780 KB) is in the ledger.

**Recall:** `prove-the-guard-fails` (R6.5, by handle). `server_provenance` (by symbol — the stamp whose
byte cost 061 requires pinning).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | the check runs once, so a later swap is unreportable, and silence does not say which | make the verdict live and legible | `:77`, `:89-97` | open |
| R1 | Scope 1 | re-evaluate after the first call at a cost that does not scale with payload count; record the probe and its rejected alternatives | a stat probe over loaded modules | 164's 6.35 ms | open |
| R2 | Scope 2 | a reader can distinguish checked-and-matching from not-checked; one field, one verdict; record where it rides | `stale_process` unconditional, every payload | round 11 §12.c | open |
| AC1 | AC 1 | a post-first-call divergence is reported — fails on today's code | Falsifiable: two-state test + red run | proving test | open |
| AC2 | AC 2 | a payload reads as *checked and matching*, pinned for both cases | Falsifiable: both asserted on a real payload | proving test ×2 | open |
| AC3 | AC 3 | the added per-call cost is measured and does not re-hash per payload | Falsifiable: hash-call count + timing + ratio | proving test ×2 | open |
| AC4 | AC 4 | a never-moving server is byte-identical, or the byte delta is measured and pinned | Falsifiable: the delta re-pinned at a measured number | proving test | open |
| AC5 | AC 5 | the wheel / no-checkout path still names a build (125); `+dirty` unchanged | Falsifiable: both asserted | proving test ×2 | open |
| AC6 | AC 6 | determinism (R4.2), no language branch (R1.1), no contract bump (R3) | Falsifiable: no timestamp in the id; grep-gates | proving test | open |
| C1 | Constraint | no full re-hash per payload; cost measured against 164's 6.35 ms and the tokens-to-answer gate | probe ≪ hash | — | binding |
| C2 | Constraint | R4.2 — identical loaded artifact ⇒ identical id; no timestamps in the id | mtimes are probe state only | — | binding |
| C3 | Constraint | 061 — if the verdict rides every payload, its bytes are measured and pinned | 91 B, re-pinned | — | binding |
| C4 | Constraint | R1.1 · R3 · the wheel path (125) unchanged | no branch, no bump | — | binding |

### Root cause (taxonomy: logic / caching a verdict)

**A cache was applied to a computation whose value is a verdict about the present.** `version` and the
loaded id are properties of the process and are correctly cached forever; *"does the disk still match"*
is a property of the world and expires the moment the world moves. One `lru_cache` covered both,
because they were returned from one function — so the cheap-and-permanent fact carried the
expensive-and-perishable one into the same memo.

The second half is the mirror image: **061's omit-when-empty rule was applied to a verdict.** For a
*value*, absence correctly means "nothing to say". For a *verdict*, absence and "checked, all clear"
are different claims, and 164's payload could not express the second.

### Blast radius

- `build_info.py`: the cache replaced by a probe plus a one-entry memo; the matching branch gains
  `stale_process: False`; `server_provenance` emits the verdict unconditionally.
- Every payload carrying `server_provenance` grows by a measured 38 bytes.
- Three existing pins move: 164's key-set and byte-cost pins, and 057's default-shape pin.
- `cache_clear()` is replaced by `reset_identity_cache()` — 8 test call sites.
- No store change, no query, no contract change.

## Phase 2 — design

### Approach

**The probe is a stat sweep of `sys.modules`, not of the tree — and that choice was decided by a
measurement, not by taste.** For each already-loaded `code_atlas.*` module, compare
`(st_mtime_ns, st_size)` against the last look; a module seen before whose stamp moved is a
divergence. A newly-imported module is **not** — otherwise every lazy import would trigger a hash
walk. When the probe fires, the full content hash runs and decides; otherwise a one-entry memo answers.

**Measured, with all 73 modules imported:**

| probe | per call | vs the hash |
|---|---|---|
| `rglob("*.py")` sweep of the package tree | 0.896 ms | **1.9×** — same order, rejected |
| `sys.modules` sweep (shipped) | **0.174 ms** | **10×** here; ~36× against 164's recorded 6.35 ms |

The tree sweep is dominated by directory traversal, not by the stats, so it is *not* a different order
of magnitude from the thing it replaces — which was the whole point. `sys.modules` is also the
**semantically right set**: `server_build` documents itself as naming *the code the process loaded*.

**The verdict rides every payload.** Scope 2 asks where. Round 11's own evidence decides it: the case
that could not be read was `read_symbol(...) → server_build: "e591f02", no stale_process` — a **nav**
payload. Putting the verdict only on `get_index_status` would leave every nav answer in exactly the
ambiguity §12.c describes. Cost: the stamp goes from ~53 B to **91 B**, i.e. **+38 B unconditional**,
measured and re-pinned with the number in the test's docstring.

**`stale_process` is present in both cases; `repo_head` stays conditional.** The verdict is always
knowable, so it is always stated. `repo_head` is *context for a divergence* and is meaningless without
one, so 061 still applies to it — which is the distinction the root cause turns on.

### Rejected alternatives

- **`rglob("*.py")` stat sweep.** Rejected **on the measurement above**: 1.9× is not an order, and
  0.896 ms per payload on the hot path is a real cost. It was written first; the number changed the
  design.
- **A bounded re-check interval** (the ticket's second option). Rejected: it trades a structural
  guarantee for a window, and the window would have to be *disclosed* to keep §12.c closed — a reader
  who cannot tell "checked" from "not checked" is no better off being told "checked within 30 s"
  without a timestamp. The probe has no window and costs less than the bookkeeping would.
- **Explicit invalidation** (the third option). Rejected: nothing in the process knows when the disk
  moved. That is the fact being detected, so it cannot also be the trigger.
- **Re-hashing per payload.** The cost 164 measured, and the reason the cache existed.
- **Deriving the fingerprint from `_LOADED_BUILD_ID`'s own tree walk.** That would put the id's
  computation on the hot path, which is the same 6.35 ms.
- **Making `_LOADED_BUILD_ID` cover only loaded modules**, so the id and the probe share a set.
  Explicitly out of scope (164's freeze-at-import semantics verified), *and* wrong: modules import
  lazily, so an id over the loaded set would change during a process's life.

### Recorded limit — the probe's set and the id's set differ, deliberately

`_LOADED_BUILD_ID` hashes **every** `.py` in the package; the probe watches only the modules the
process **loaded**. So an edit to a shipped-but-never-imported module moves the tree hash and does
**not** trip the probe, and the divergence goes unreported until something else does. This is a
deliberate scope choice matching what `server_build` claims to name — a file never imported is not
loaded code — and round 11's actual case (an edit to `build_info.py`, a loaded module) is covered.
Stated rather than blurred.

### Assumptions

| Assumption | Tag |
|---|---|
| A stat sweep is an order cheaper than the hash walk | **falsified for the tree sweep, verified for `sys.modules`** — 1.9× vs 10×; the measurement changed the design |
| mtime+size together move on a content change | verified for the case at hand; a same-size same-mtime edit is the known limit of every mtime probe, and the content hash is still the authority when the probe fires |
| A newly-imported module must not read as a divergence | verified — otherwise every lazy import pays a hash walk; pinned by its own test |
| The verdict's byte cost is small enough to ride every payload | verified — +38 B, measured, re-pinned |
| `cache_clear()` has no non-test callers | verified — grep found only `tests/` |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `_loaded_modules_changed` + `_probe_state`; `_compute_identity`; a live `server_identity`; `reset_identity_cache`; `stale_process` on the matching branch; unconditional verdict in `server_provenance` | `code_atlas/build_info.py` | every stamped payload | R1, R2, AC1–AC6 | 1/1 |
| Three pins moved to the new shape (164's key set + byte cost, 057's default shape) | `tests/test_server_build*.py`, `tests/test_answer_pagination.py` | 3 tests | AC2, AC4 | 1/1 |
| `cache_clear()` → `reset_identity_cache()` | `tests/test_server_build.py` | 8 call sites | — | 1/1 |
| Proving tests (13) | `tests/test_server_identity_is_live.py` (new) | new file | AC1–AC6 | 1/1 |
| Payload-field row; CONVENTION pruned to fit | `docs/CONVENTION.md` | R7.6 | R7.2 | 1/1 |
| BACKLOG; ledger; LESSONS; working doc | `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `prove-the-guard-fails` (R6.5) — **traced.** Three red runs below, one per property.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | logic (two on-disk states in one process) | integration test + red run 1 | ✅ |
| AC2 | integration (both cases on a payload a tool returns) | integration test ×2 + red run 2 | ✅ |
| AC3 | measurement (hash-call count, timing, ratio) | integration test ×2 + recorded measurement | ✅ |
| AC4 | measurement (byte delta re-pinned at a measured number) | integration test | ✅ |
| AC5 | integration (no-git path; `+dirty` with a matching process) | integration test ×2 | ✅ |
| AC6 | logic (no timestamp survives into the id) + guard (grep-gates) | integration test + red run 3 + `gate.sh` | ✅ |

`EXCLUSIONS: 1 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **The probe's set is narrower than the id's set** — recorded above under *Recorded limit*. **No
  expiry:** it is a deliberate scope decision, not a deferral, and closing it would mean either putting
  a tree walk on the hot path or changing 164's id semantics, both explicitly rejected. A same-size
  same-mtime edit is likewise undetectable by any mtime probe; the content hash remains the authority
  whenever the probe does fire.

### Proving test

`tests/test_server_identity_is_live.py::test_a_swap_after_the_first_answer_is_reported`

### Rollback + porting

Rollback: revert `build_info.py`, delete the new test file, restore three pins and the
`cache_clear()` calls. No persisted state, no schema or contract change. Porting: `app` only.

### SCOPE

`SCOPE: M` — one module's caching strategy plus one payload field; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| A live probe replaces the unconditional cache | implemented-as-approved |
| The probe reads `sys.modules`, not the tree (decided by measurement) | implemented-as-approved |
| A newly-imported module is not a divergence | implemented-as-approved |
| The full hash runs only when the probe fires | implemented-as-approved |
| `stale_process` unconditional; `repo_head` conditional | implemented-as-approved |
| The verdict rides every payload, byte cost measured and re-pinned | implemented-as-approved |
| mtimes never reach the id (R4.2) | implemented-as-approved |

No deviations. Diff ⊆ approved list. **The `rglob` probe was written, measured, and replaced** — see
*Rejected alternatives*; the discarded version is the reason the shipped one is defensible.

### Empirical outputs

**AC3 — the measurement that decided the design.** All 73 modules imported:

```
loaded code_atlas modules: 73
probe            : 0.1737 ms/call
content hash     : 1.7298 ms/call
server_provenance: 0.1770 ms/call
ratio            : 10.0x
```

and the version that was rejected:

```
rglob sweep      : 0.8960 ms/call over 73 entries   <- 1.9x the hash. Not an order. Rejected.
sys.modules sweep: 0.0236 ms/call over 11 entries   <- the same probe on a light import set
```

**The in-suite ratio guard is asserted at 4×, not 10×, and the reason is recorded**: 10× is exactly
where this host sits, and a guard standing on its own boundary fails for the wrong reason — it did,
once, under full-suite load. The number lives in the docstring; the assertion is a margin.

**AC4 — the byte cost, measured and re-pinned:** the stamp goes 53 B → **91 B** on a clean 7-char
build (~98 with `+dirty`). +38 B unconditional, on every payload that carries `server_provenance`.
The pin moved from `<= 80` to `<= 100` with the measured number written into the test.

**Three red runs (R6.5):**

```
1. the unconditional lru_cache restored (164's code)
   E  the swap must be reportable AFTER the first answer
   E  twenty answers, one hash walk                                    4 failed, 7 passed
2. the verdict omitted on the matching branch (061 applied to a verdict)
   E  silence cannot be the clean answer (170)
   E  the wheel path is checked too, and says so                       5 failed, 6 passed
3. the probe state leaked into the id
   E  identical content, recomputed twice, identical answer            1 failed, 10 passed
```

**A self-caused cross-file leak, found and fixed:** the new file's autouse fixture reset the memo
*before* each test only, so the last test's monkeypatched state outlived the file and broke
`test_standard_status_reports_server_version_and_build` — which passed in isolation and failed in the
suite. The fixture now resets before **and** after. Worth recording because a process-global memo is
exactly what this ticket introduced.

**Green run:**

```
$ .venv/bin/pytest -q
2403 passed in 130.01s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_a_swap_after_the_first_answer_is_reported` — one process, two on-disk states, the second reported; red run 1 |
| AC2 | `test_a_matching_payload_says_checked_not_nothing` + `test_both_cases_are_pinned_on_a_real_payload` (both cases, on `nav_result`'s own output); red run 2 |
| AC3 | `test_the_probe_is_what_notices_not_a_re_hash` (twenty answers, one hash walk) + `test_the_added_per_call_cost_is_an_order_below_the_hash_walk` + the measurement above |
| AC4 | `test_server_provenance_byte_cost_is_small_and_measured`, re-pinned at the measured 91 B |
| AC5 | `test_the_wheel_path_still_names_a_build` + `test_the_dirty_axis_is_untouched` (a *dirty* worktree that matches is **not** stale — two axes, kept apart) |
| AC6 | `test_the_probe_state_is_never_part_of_the_id` (no mtime survives into the payload); `gate.sh` R1.1/R2.2 green; no `contract.py` edit ⇒ **no bump (R3), confirmed** |
| — | `test_a_newly_imported_module_is_not_a_divergence`, `test_a_real_content_change_to_a_loaded_module_is_seen` (the probe's own falsifiability), `test_a_vanished_module_does_not_raise`, `test_the_memo_is_one_entry_however_many_swaps` |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2390 passed / 0 failed` at `739435e` →
`2403 passed / 0 failed`. ruff + mypy green. `scripts/gate.sh` → `GATE GREEN`.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen >= 2 | 0 routed to a destination | 0 cannot promote (reason) | 1 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `prove-the-guard-fails` (R6.5) gains 170: three red runs, one per property.
- **New:** `170-C1` (type-2, `never-cache-a-verdict-with-a-fact`) — a function returning both a
  **property of the process** (permanent) and a **verdict about the world** (perishable) must not be
  memoised as one value: the cheap permanent fact carries the perishable one into the same cache, and
  the verdict silently freezes. Its mirror: 061's omit-when-empty rule is right for a value and wrong
  for a verdict — absence and "checked, all clear" are different claims. seen=1.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. Self-checks: the probe
chosen by measurement after the first draft was measured and rejected, a flaky boundary guard
diagnosed and re-set with the reason recorded, a self-caused cross-file memo leak found and fixed, the
byte cost measured and re-pinned rather than hidden, three red runs, and the probe/id set asymmetry
recorded as a deliberate limit rather than blurred.
