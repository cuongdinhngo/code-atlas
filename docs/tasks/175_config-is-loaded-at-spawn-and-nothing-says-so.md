---
id: 175
slug: config-is-loaded-at-spawn-and-nothing-says-so
title: 'Config is read once at spawn and no payload says so — editing `.code-atlas.toml` then building returns a silent, unchanged success'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [164, 170]
---

## Why this exists (field episode, 2026-08-27)

The maintainer edited `.code-atlas.toml` to add the second adapter, ran a build, and got a success that
described the old world:

```
edit .code-atlas.toml   → adds the adapter
build                   → indexed_suffixes: [".php", ".phtml"],  wrote.files: 0,  2.6 s
```

> *"Không field nào báo 'config trên đĩa khác config tôi đã load'. Đây cùng lớp với 164/10-A nhưng lệch
> một tầng: 164 giờ đóng dấu code đã load, còn config đã load thì không có gì tương đương. Đề xuất:
> hash config lúc startup, so với file trên đĩa khi build, khác thì báo `config_stale_process` — đối
> xứng với `server_stale_process`."*

The diagnosis is exact. 164 closed *"which code answered"* (10-A) and 170 is open on *"which code
answered **now**"*. **Neither covers *which config answered*** — and config is the axis that decides
what the index even contains, which makes a silent stale read here more consequential than a stale
build id.

## Root cause

- `code_atlas/main.py:170` — `build_server(load_config(Path.cwd(), os.environ)).run()`. The `Config` is
  built **once**, at process start, from `.code-atlas.toml` (`config.py:22`, `PROJECT_FILE`) plus the
  environment, and bound into every tool's closure (e.g. `tools/build_or_update_index.py:51`).
- Nothing re-reads the file, and nothing hashes it. There is no `config` equivalent of
  `build_info._LOADED_BUILD_ID` (`build_info.py:74`), so no payload can compare loaded config against
  disk.
- `indexer._record_meta` records the *effects* of the config (`indexed_suffixes`, census) but never the
  *identity* of the config that produced them, so the index cannot be asked which config built it
  either.

## Scope

Give config the provenance 164 gave code, on the same shape.

1. Hash the loaded project config at startup — the file's bytes plus the `CA_*` environment the config
   reads — and expose the identity where `server_build` already rides.
2. When the file on disk differs from the loaded hash, say so: `config_stale_process` (or the design's
   recorded field name), with the same omit-when-empty discipline (061).
3. The build tool checks it at build time, because that is the moment the divergence costs a whole
   build (this episode).
4. Record whether the index should also store the config identity that built it — a separate claim from
   the process's, and possibly its own follow-up.

### Explicitly not in scope

- **Reloading** the config, or restarting the server. Report; the operator restarts. (A reload would
  change tool bindings mid-session, which is a different and much larger decision.)
- The environment axis of adapter launch commands beyond what the config reads.
- `server_identity`'s own caching bug — [170](170_server-identity-is-cached-so-a-later-build-swap-is-unreportable.md).

## Constraints

- **Cost** — one small file read plus a hash, at startup and at build time only. Never per payload:
  `server_build` already costs 49 B unconditionally (round 11 §6), and this must not add a second
  standing tax without measuring it.
- **R4.2** — same config bytes + same env ⇒ same identity, across processes and hosts; no timestamps.
- **061** — omit when the config matches, or measure and pin the byte delta if it always rides.
- **No-config path** — a repo with no `.code-atlas.toml` (env-only, or defaults) must still answer, and
  its identity must be stable (cf. 125's wheel path).
- **R1.1** no language branch · **R3** no bump.

## Acceptance criteria

1. A test loads a config, mutates the file on disk, and asserts the next build reports the divergence —
   fails on today's code.
2. A build whose config file is unchanged is byte-identical to today, or the added bytes are measured
   and pinned.
3. The no-config / env-only path names an identity and does not raise (125's guarantee).
4. Determinism (R4.2): identical bytes and env produce an identical identity across two processes.
5. Whether the index stores the config identity that built it is decided and recorded — implemented or
   filed with evidence.
6. No language branch (R1.1), no contract bump (R3).

## References

Field episode 2026-08-27, finding (3) — the maintainer's own diagnosis, verified in source.
`code_atlas/main.py:170`; `code_atlas/config.py:22,131`; `code_atlas/build_info.py:74`;
`code_atlas/tools/build_or_update_index.py:51`. Round 11 §12.c (the same class, one layer up), §6 (the
49 B standing cost of the code axis). Related:
[164](164_server-build-names-the-repo-not-the-running-process.md) (the shape to mirror),
[170](170_server-identity-is-cached-so-a-later-build-swap-is-unreportable.md) (the sibling defect),
[172](172_incremental-is-blind-to-a-scope-change.md) (what the silence cost this episode).

## Session status

- **KEY:** 175 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended batch) · envelope in `.mango/run-contract-175.txt`.
- **Branch:** `feat/175-config-is-loaded-at-spawn` (stacked on `feat/170-…`)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2403 passed, 0 failed` at `33c36dd` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

1. Scope 2 — *"`config_stale_process` (or the design's recorded field name)"* → *Approach*, and the
   name is kept, because the symmetry with `server_stale_process` is the point.
2. Scope 4 — *"Record whether the index should also store the config identity that built it … and
   possibly its own follow-up."* → **implemented, not filed**; see *Scope 4 verdict*.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous`
`RECALL: 2 claim(s) surfaced | 1 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=5 R=4 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 10 applicable — 9 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.3 (change-type) ✅ · §R5.6 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.7 (change-type) ✅ · §R7.2 (change-type) ✅ · §R7.6 (change-type) ⚠ **budget raised with an argument, not silently** — see below`
`BASELINE: green — 2403 passed, 0 failed, 0 skipped at 33c36dd (bare pytest, Linux host)`

**Premise:** every citation resolves and the maintainer's diagnosis is exact. `main.py:170` builds the
`Config` once from `PROJECT_FILE` plus the environment and binds it into every tool's closure;
`_record_meta` records the config's *effects* (`indexed_suffixes`, the census) and never its
*identity*. There is no `config` analogue of `_LOADED_BUILD_ID`.

**Recall:** `prove-the-guard-fails` (R6.5, by handle). `count-pin-in-blast-radius` (AGENT_BRIEF P5, by
symbol via `core_modules()` — a new core module moves two pinned counts; both found and bumped).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | editing the config then building returns a silent, unchanged success | give config the provenance code has | the episode | open |
| R1 | Scope 1 | hash the loaded config — file bytes plus the `CA_*` env it reads — and expose the identity where `server_build` rides | `config_identity`; on status, not on nav | `config.py:22,131` | open |
| R2 | Scope 2 | when disk differs from the loaded hash, say so, with 061's discipline | `config_stale_process`, stated where it rides | 170's verdict rule | open |
| R3 | Scope 3 | the build tool checks it at build time | on `build_or_update_index` | the episode | open |
| R4 | Scope 4 | record whether the index should store the config identity that built it | **implemented** | see verdict | open |
| AC1 | AC 1 | load, mutate the file, next build reports the divergence — fails today | Falsifiable: the episode replayed | proving test | open |
| AC2 | AC 2 | an unchanged config is byte-identical, or the added bytes are measured and pinned | Falsifiable: nav asserted unchanged; the two tools' fields pinned | proving test ×2 | open |
| AC3 | AC 3 | the no-config / env-only path names an identity and does not raise | Falsifiable: asserted | proving test | open |
| AC4 | AC 4 | determinism across two **processes** | Falsifiable: a subprocess compared | proving test ×2 | open |
| AC5 | AC 5 | the index-stores-config question decided and recorded | Falsifiable: implemented + pinned | proving test | open |
| AC6 | AC 6 | no language branch (R1.1), no contract bump (R3) | Falsifiable: grep + no `contract.py` edit | proving test + `gate.sh` | open |
| C1 | Constraint | one small read plus a hash, at startup and build time only; never per payload | two tools only | — | binding |
| C2 | Constraint | R4.2 — same bytes + env ⇒ same identity across hosts; no timestamps | content only | — | binding |
| C3 | Constraint | 061 — omit when matching, or measure and pin | verdict stated where it rides, nowhere else | — | binding |
| C4 | Constraint | no-config path must answer and be stable (125's shape) | a marker for the absence | — | binding |
| C5 | Constraint | R1.1 no language branch · R3 no bump | env slice derived, not listed | — | binding |

### Root cause (taxonomy: config / provenance)

**Two axes of "what answered", and only one of them had a stamp.** 164 gave the *code* axis an
identity frozen at import; 170 made its verdict live. The *config* axis — which decides what the index
even contains — had neither. And the asymmetry was invisible precisely because the code axis existed:
a payload naming `server_build` looks like it names its provenance.

### Blast radius

- `config.py`: `config_identity`, `config_stale`, `_config_env_slice`, and two defaulted `Config`
  fields. `load_config` fills both.
- `store.py`: one meta key. `indexer.py`: one `set_meta`.
- New `tools/config_provenance.py` — one definition site for the three fields, two consumers.
- `build_or_update_index` and `get_index_status` at `standard`+ only. **No nav payload changes.**
- Two `core_modules()` count pins move 73 → 74 (P5's handle; both found).
- No contract change, no schema change, no query.

## Phase 2 — design

### Approach

**`config_identity(root, env)` = a 7-char SHA-256 of the project file's bytes plus the `CA_*` slice the
config actually reads**, sorted. Content only, so identical bytes and env give an identical id on any
host (R4.2) — asserted by running a **second process** and comparing.

**The env slice is derived, not listed** (R6.7/R1.1): `{env_name(k) for k in KNOB_KEYS}` plus anything
matching `ADAPTER_CMD_ENV`. So knob N+1 is covered the moment it exists, and no language appears. An
unrelated variable (`PATH`, `EDITOR`) cannot move the id — otherwise every shell change would read as
stale, which is the failure mode a too-wide identity has.

**A missing project file hashes a stable marker**, not nothing, so an env-only repo names an identity
instead of looking like a missing answer (125's wheel path, one layer up). Reading it can never raise:
an `OSError` degrades to the marker, exactly as `_capture_loaded_build_id` does.

**`config_stale(config)` compares against the env the `Config` was resolved from, and that correction
matters.** My first version defaulted to `os.environ`, which made every explicitly-env'd caller read
as stale — including every test. The honest framing: **a running process's own environment cannot
change under it, so the file is the one axis that can move.** So the slice is stored on `Config`
(`config_env`) and the comparison re-derives against it, isolating the file. The staleness check needs
no arguments at all, which is also the API that cannot be got wrong.

**Where it rides — a recorded decision, not symmetry.** `config_build` + `config_stale_process` on
`get_index_status` (`standard`/`verbose`, where `server_build` rides) and on
`build_or_update_index` (`standard` — Scope 3's moment, where the divergence costs a build).
**Deliberately not on nav payloads.** Scope 1 says *"where `server_build` already rides"*, which could
be read as everywhere; the constraint is explicit that a second standing tax must be measured and
argued. 170 had just added 38 B unconditionally to every nav payload, and *"which config answered"* is
not a question a `find_callers` reader is asking. Pinned by a test that asserts a nav payload carries
neither field.

**The verdict is stated, never omitted** — 170's lesson applied without re-learning it: absence and
"checked, still matching" are different claims. `index_config_build` *is* conditional, because equal
ids tell the reader nothing (061).

### Scope 4 verdict — the index stamps its own config, IMPLEMENTED

`_record_meta` writes `config_identity`, so the index can be asked which config produced its contents —
a claim genuinely distinct from the process's. Implemented rather than filed because it is **one
`set_meta` reusing the identity already computed**, and filing a one-line follow-up would have been
worse than doing it. Surfaced as `index_config_build` only when it differs from the running config,
which is the comparison a reader actually wants: *"the index was built by a config I am no longer
running."* That is the episode's shape one step later, and it survives a restart, which the process's
own verdict does not.

### Rejected alternatives

- **Hash only the file, not the env.** Cheaper and wrong: `CA_SECOND_CMD` is exactly how the field
  episode's adapter would have been added, and an env-only change would have been invisible.
- **Hash the whole environment.** Every unrelated shell variable would move the id and every process
  would read as stale. Pinned against.
- **Store the resolved `Config`'s field values as the identity.** Tempting (it is the thing that
  matters) and wrong for this axis: `replace(config, db_path=…)` is used throughout the tests and
  would then change the identity, while the question asked is *"did the config **source** move"*.
- **Re-read the config per payload.** The constraint forbids it, and reloading is explicitly out of
  scope: it would rebind tools mid-session.
- **Reload the config when it changes.** Out of scope, and correctly — every tool's closure holds the
  old one, so a partial reload is worse than a report.
- **A field on `Config` computed lazily.** A frozen dataclass with a cached property is a mutable
  cache in an immutable object; and 170 had just shown what caching a verdict costs.

### Assumptions

| Assumption | Tag |
|---|---|
| `config_stale` can default to `os.environ` | **falsified during execute** — it made every explicitly-env'd caller read as stale; the env slice is now stored and the comparison needs no argument |
| A missing project file needs a stable identity | verified — pinned, and it is 125's guarantee one layer up |
| Only the file can move under a running process | verified by reasoning and encoded in the API: the env slice is frozen at load |
| A new core module moves pinned counts | verified — two `core_modules()` pins at 73, both found and bumped (P5) |
| `Config`'s new fields can be defaulted | verified — every `replace(...)` and hand-built `Config` in the suite still works, and a hand-built one claims nothing |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `config_identity`, `config_stale`, `_config_env_slice`, `CONFIG_ID_CHARS`; two `Config` fields; `load_config` fills them | `code_atlas/config.py` | one identity site | R1, R2, AC3, AC4, AC6 | 1/1 |
| `CONFIG_IDENTITY_KEY` | `code_atlas/store.py` | one key | R4 | 1/1 |
| Stamp it in `_record_meta` | `code_atlas/indexer.py` | both build paths | R4, AC5 | 1/1 |
| `attach_config_provenance` — one definition site, two consumers | `code_atlas/tools/config_provenance.py` (new) | 3 fields | R1, R2, R3 | 1/1 |
| Wire both tools at `standard`+ | `build_or_update_index.py`, `get_index_status.py` | 2 call sites | R3, AC2 | 1/1 |
| Two `core_modules()` count pins 73 → 74 | `tests/test_core_is_language_agnostic.py`, `tests/test_sql_confinement.py` | P5 | — | 1/1 |
| CONVENTION row; **budget raised 6,300 → 6,450 with the argument in the test** | `docs/CONVENTION.md`, `tests/test_doc_size_budget.py`, `tests/test_agent_chain_budget.py` | R7.6 | R7.2 | 1/1 |
| Proving tests (12) | `tests/test_config_provenance.py` (new) | new file | AC1–AC6 | 1/1 |
| BACKLOG; ledger; LESSONS; working doc | `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `prove-the-guard-fails` (R6.5) — **traced.** Three red runs below.
- `count-pin-in-blast-radius` (P5) — **traced.** A new core module moves two pins, and the suite found
  both rather than my remembering them:

  ```
  E  assert 74 == 73   tests/test_core_is_language_agnostic.py::test_the_guard_has_something_to_check
  E  assert 74 == 73   tests/test_sql_confinement.py::test_the_guard_has_something_to_check
  ```

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (the episode replayed through the real build tool) | integration test + red run 1 | ✅ |
| AC2 | integration (nav payload asserted unchanged; the cheap path asserted unchanged) | integration test ×2 | ✅ |
| AC3 | integration (no file at all) | integration test | ✅ |
| AC4 | logic (same bytes, new mtime; another directory) + **process** (a subprocess compared) | integration test ×2 + red run 3 | ✅ |
| AC5 | integration (the meta stamp, and the differ-only surfacing) | integration test | ✅ |
| AC6 | guard (grep) + measurement (cost) | integration test ×2 + `gate.sh` | ✅ |

`EXCLUSIONS: 1 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **The report is not the fix, by design.** Reloading is explicitly out of scope, so the operator still
  has to notice the field and restart. This ticket makes the silence impossible; it does not make the
  build correct. **No expiry** — it is the ticket's own boundary, stated so the next field round does
  not read a reported divergence as a handled one.

### Proving test

`tests/test_config_provenance.py::test_a_config_edited_after_load_is_reported_by_the_next_build`

### Rollback + porting

Rollback: revert three source files, delete the new module and test file, restore two count pins and
both budgets. The meta key becomes an orphan row a pre-175 reader ignores. Porting: `app` only.

### SCOPE

`SCOPE: M` — one identity, one meta key, three fields on two tools; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Identity = file bytes + the derived `CA_*` slice; content only | implemented-as-approved |
| The env slice derived from `KNOB_KEYS` + the CMD pattern, no language named | implemented-as-approved |
| A missing file hashes a stable marker; reading never raises | implemented-as-approved |
| The verdict stated where it rides; `index_config_build` conditional | implemented-as-approved |
| `standard`+ on two tools; nothing on nav payloads | implemented-as-approved |
| The index stamps the config that built it | implemented-as-approved |
| `config_stale` compares against the env the Config was resolved from | **corrected during execute** — below |

### Empirical outputs

**One correction during execute, and it changed the API for the better.** `config_stale(config, env)`
defaulted to `os.environ`, so a `Config` loaded from an explicit env dict compared against a different
env and read **stale while nothing had moved** — caught immediately by two of my own tests:

```
>   assert status[CONFIG_STALE] is False
E   assert True is False
```

The fix is the honest framing rather than a patch: a running process's own environment cannot change
under it, so the file is the only axis that can move. The slice is stored on `Config` and the
comparison re-derives against it — and `config_stale` now takes no env argument at all, which is the
API that cannot be got wrong.

**The mechanism, on a real tree:**

```
identity      : 1dbb33f
stale (same)  : False
stale (env+)  : True          # CA_WORKERS 1 -> 2
no-file id    : 46634e3       # stable, not empty
deterministic : True
```

**Three red runs (R6.5):**

```
1. nothing published (the pre-175 payloads)
   E  the verdict rides; silence is not the clean answer
   E  assert 'config_stale_process' in {'indexed': True, 'files': 1, ...}   3 failed, 9 passed
2. the verdict omitted on the matching case (061 applied to a verdict)
   E  the verdict rides; silence is not the clean answer                    2 failed, 10 passed
3. a timestamp added to the identity
   E  no timestamp reaches the id                                          1 failed, 11 passed
```

**Cost:** `config_stale` is one small read plus a hash — 500 calls under a 1 ms/call budget, and it
runs on two tools rather than every payload. **No nav payload byte changed**, asserted.

**A pre-existing flake observed, not caused:**
`test_bytecode_invalidation.py::test_ac4_a_same_second_same_size_edit_is_a_stale_import` failed once
in a full-suite run and passed alone and on the next full run. It requires two writes to land inside
one wall-clock second, which a loaded suite can straddle. Recorded rather than ignored; it is not in
this diff's blast radius.

**Green run:**

```
$ .venv/bin/pytest -q
2419 passed in 139.47s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 82 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_a_config_edited_after_load_is_reported_by_the_next_build` — the episode: build clean, add the second adapter to the file, build again, `config_stale_process: true`; red run 1 |
| AC2 | `test_the_cheap_path_and_nav_payloads_carry_nothing` (minimal status and `nav_result` both unchanged) + `test_the_verdict_is_stated_not_omitted` (the fields pinned where they do ride) |
| AC3 | `test_the_no_config_path_still_names_an_identity` |
| AC4 | `test_the_identity_is_content_only` (same bytes new mtime; another directory) + `test_the_identity_is_stable_across_processes` (a real subprocess) + `test_only_the_env_the_config_reads_moves_the_identity`; red run 3 |
| AC5 | `test_the_index_can_say_which_config_built_it` — the meta stamp, absent when equal, present when the running config differs |
| AC6 | `test_no_language_is_named_by_the_identity`; `gate.sh` R1.1/R2.2 green; no `contract.py` edit ⇒ **no bump (R3), confirmed** |
| — | `test_a_deleted_config_file_reads_as_a_divergence`; `test_a_hand_built_config_says_nothing` (R5.6); `test_the_added_cost_is_one_small_read` |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2403 passed / 0 failed` at `33c36dd` →
`2419 passed / 0 failed`. ruff + mypy green. `scripts/gate.sh` → `GATE GREEN`.

### Learning loop

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen >= 2 | 0 routed to a destination | 0 cannot promote (reason) | 2 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `prove-the-guard-fails` (R6.5) gains 175: three red runs.
- `count-pin-in-blast-radius` (P5) gains 175: a new core module moved two pinned counts, and the suite
  found both. Recorded as a `seen:` bump on a promoted rule.
- **New:** `175-C1` (type-2, `an-identity-must-be-comparable-against-what-produced-it`) — a provenance
  hash must be re-derived against **the same inputs it was built from**, or it reports divergence on
  inputs that never moved. Concretely: `config_stale` defaulting to `os.environ` made every
  explicitly-env'd caller stale. The general form is to ask *which of this identity's inputs can
  actually change under a running process* — freeze the rest and compare only the mutable axis. seen=1.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. Self-checks: the field
episode replayed end-to-end through the real build tool, an API flaw caught by my own tests and fixed
by reframing rather than patching, three red runs, determinism proven across a real second process,
Scope 4 implemented rather than deferred, the nav-payload decision recorded and pinned, and a doc
budget **raised with a written argument** after three consecutive tickets had already pruned for theirs.
