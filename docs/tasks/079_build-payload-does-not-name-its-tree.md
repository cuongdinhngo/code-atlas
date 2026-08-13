---
id: 079
slug: build-payload-does-not-name-its-tree
title: '`build_or_update_index` is the one payload with no `index_root` — and building is when the tree matters most'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [071, 060]
---

## Goal
071 added `index_root` so an answer names the tree it describes. Round 4 verified it on **8 of 8**
distinct nav payloads and found it **absent on all 4** `build_or_update_index` payloads, which carry
`db_path` instead. A build is a *write*, and the question "which tree am I writing about?" is more
consequential there than on any read: a parallel agent that builds from the wrong cwd corrupts the
index every later answer is drawn from.

## Evidence (field retro round 4, 2026-08-10, §0.a / §A.7 / §11 item 4)
- `index_root` present on `get_index_status`, `search_symbol`, `file_outline`, `read_symbol`,
  `find_callers`, `find_references`, `find_view_data` — every nav payload the session touched.
- Absent on 4 of 4 `build_or_update_index` calls, which instead carry `db_path` — the field 061
  deliberately stripped from nav payloads, so the build path is now the *only* place `db_path` still
  appears and the *only* place the source root does not.
- The evaluator, who was in the main checkout, could confirm the match by hand; the three agents it
  dispatched each ran in a `.worktrees/<slug>` where it would **not** have matched. The retro records
  that the mitigation was a hand-written warning in each agent's prompt.
- Round 4 also used `index_root` as its **process fingerprint** (§0.a): a payload without it proves a
  server older than the 071 batch. The build tool cannot serve that check today.

## Scope / Deliverables
- **Attach `index_root` to every `build_or_update_index` payload** — success, `busy` refusal, and every
  refusal path (no adapter, empty suffixes, schema mismatch), so the field is a reliable fingerprint
  rather than a per-branch accident.
- **Decide `db_path`'s fate on this payload.** 061 removed it from nav answers as dead weight; on a
  build it is arguably the one place it earns its bytes (an operator setting `CA_DB_PATH` for
  isolation reads it there). Keep or drop with a stated reason — do not leave it as the accident it is
  today.
- **Sweep for the remaining payload shapes.** Enumerate every tool response and state, per shape,
  whether it carries `index_root`; the audit is the deliverable, not just the two-line fix.
- **Fold in [077](077_index-cannot-name-the-revision-it-describes.md)'s field if that lands first** —
  a build payload that names the directory but not the revision only half-answers the question.

## Constraints
- R4 — same input, same payload; the field is read from config, not derived per call (071 collapsed 38
  re-derivations into `Config.index_root` — do not reintroduce one).
- 060 — the build payload's field names are load-bearing (`wrote` vs `graph`); add beside them without
  disturbing either group.
- R5.3 — a refusal path must not be able to raise while attaching the field.
- 061 — no field that means nothing; `index_root` always means something.

## Acceptance criteria
- All `build_or_update_index` outcomes (full, incremental, no-op, `busy`, each refusal) carry
  `index_root`; a test enumerates the outcomes rather than sampling one.
- A recorded, tested verdict on `db_path` on this payload.
- An audit table in the ticket or plan listing every payload shape and whether it names its tree, with
  no "unknown" rows.

## References
Field retro round 4 §0.a (fingerprint use), §A.7 (verified nav / absent on build), §11 item 4.
Related: [071](071_answers-do-not-name-their-tree.md) (the field and its `Config.index_root` source),
[061](061_payload-weight.md) (why `db_path` left the nav payloads),
[060](060_build-report-scale-naming.md) (the build payload's field groups),
[064](064_build-without-adapter-silent.md) (the refusal paths this must also cover),
[077](077_index-cannot-name-the-revision-it-describes.md) (the revision half).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 079

## Session status
- **work_doc_mode**: embed (below separator in this ticket file)
- **Phase**: 5 finalise; Gates 1+2 cleared; **review WAIVED** (run arg "with skipped review"); status done
- **STRUCTURE**: native | **TRACK**: backend | **SCOPE**: M | **TIER**: full
- **Branch (planned)**: `feat/079-build-payload-does-not-name-its-tree`
- **Baseline**: green (Docker scoped: 88 passed)

## Phase 1 — Analysis

### Decomposition count
`SECTIONS: 5 found (Goal, Evidence, Scope/Deliverables, Constraints, Acceptance criteria) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=3`

### Requirements matrix
| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|----|--------|------------------|----------------|--------------|--------|
| G1 | Goal | build is the one payload with no `index_root` | Add `index_root` to build payloads; a write needs its tree named most | build tool returns 3 dict shapes, none with `index_root`; all 16 other tool files carry it | open |
| R1 | Scope | Attach `index_root` to **every** payload — success, `busy`, every refusal (no adapter, empty suffixes, schema mismatch) | Uniform field across all outcomes so it is a fingerprint | `_result`, `_busy`, `_refused` return dicts; no-adapter/empty-suffix currently **raise `AdapterError`** (064) | open |
| R2 | Scope | Decide `db_path`'s fate; keep/drop with reason | Recorded, tested verdict | `db_path` on `_busy`, `_refused`, standard `_result`; absent on minimal success | open |
| R3 | Scope | Sweep every payload shape; audit table, no "unknown" rows | Enumerate all tool responses x states | see audit table below | open |
| R4 | Scope | Fold in 077's revision field | Build names both tree and revision | 077 done (`LAST_REF_KEY` stored at build); success payload has `last_commit`, not `last_ref` | open |
| C1 | Constraint | R4 — read from config, not derived per call | `Config.index_root` reused, no re-derivation | `config.index_root` property exists (071) | open |
| C2 | Constraint | 060 — don't disturb `wrote`/`graph` groups | Add beside, not inside | `_result` nests `wrote`; add sibling keys | open |
| C3 | Constraint | R5.3 — a refusal path must not raise while attaching field | Field attach can't throw | `index_root` is a pure `str` property | open |
| C4 | Constraint | 061 — no field that means nothing | `index_root` always meaningful | always a resolved abs path | open |
| AC1 | AC | All outcomes carry `index_root`; test **enumerates** outcomes | Falsifiable: test asserts field on each returned payload | — | open |
| AC2 | AC | Recorded, tested verdict on `db_path` | Falsifiable: verdict doc + test | — | open |
| AC3 | AC | Audit table listing every payload shape + names-its-tree, no "unknown" rows | Falsifiable: table present, 0 unknowns | see below | open |

### AC validation (falsifiability)
- **AC1** — falsifiable (a test enumerates each outcome and asserts `index_root`). ok
- **AC2** — falsifiable (verdict recorded here + a test asserts `db_path` presence). ok
- **AC3** — falsifiable (table present, count of "unknown" rows == 0). ok
No vague adjectives; no manual-check exclusions needed. No uncodified standards applied.

### Audit table — every payload shape x names its tree (deliverable R3/AC3)
`index_root` source = `Config.index_root` (071). "before" = state on untouched checkout.

| Tool | Payload shape / state | `index_root` before | after 079 |
|------|-----------------------|--------------------|-----------|
| get_index_status | unbuilt / mismatched / status (min/std/verbose) | yes (071) | yes |
| search_symbol | list_result (hit/empty/reason) | yes | yes |
| file_outline | nav/empty | yes | yes |
| read_symbol | nav/empty/ambiguous | yes | yes |
| find_callers / find_references / find_implementations | nav/empty | yes | yes |
| find_view_data / reachable_from / reach_shared / include_graph / find_orphans / impact / explain_path | nav/list/empty | yes | yes |
| **build_or_update_index** | success full/incremental/no-op (min+std) | **no** | yes |
| **build_or_update_index** | `busy` refusal | **no** | yes |
| **build_or_update_index** | schema-mismatch `refused` | **no** | yes |
| **build_or_update_index** | no-adapter / empty-suffix / handshake refusal | **no** (raises `AdapterError`) | yes (design decides shape) |

-> **0 "unknown" rows.** Only `build_or_update_index` lacked the field; that is exactly the ticket.

### CLARIFICATION
`CLARIFICATION: 2 raised | 0 self-resolved | 2 for human decision`

**Q1 (design-critical) — the no-adapter / empty-suffix / handshake refusal paths currently *raise* `AdapterError`; they do not return a payload.** The ticket lists them as refusals that must "carry `index_root`" and references 064 as "the refusal paths this must also cover." An exception cannot carry a payload field. Options:
- **(A, recommended)** Catch `AdapterError` at the *tool boundary* and return a structured refusal payload `{mode: "refused", reason: "no_adapter"|"empty_suffixes", ..., index_root, db_path}` — mirroring `schema_guard`'s philosophy ("a mismatch has to reach the caller as a payload naming the next action — a stack trace is what sent a field session back to grep"). Preserves 064's intent (no empty index written; refusal not success); updates 064's *tool-path* test to assert the payload (the `full_build`/`incremental_update` unit tests still assert the raise — indexer internals unchanged). Only option satisfying AC1's "each refusal ... carry index_root."
- (B) Leave those paths raising; audit-table them as "raises, not a payload." Contradicts the ticket's explicit enumeration and AC1.

-> **Recommend A.**

**Q2 — `db_path`'s fate (deliverable R2).** Recommend **KEEP** `db_path` on the build payload (current placement: busy, refused, standard success — and add to the new no-adapter refusal). Reason: a build is a *write*; `db_path` names the write target, the one payload where it earns its bytes (an operator setting `CA_DB_PATH` for isolation reads it back here). `index_root` (source tree) and `db_path` (write target) are different facts, side by side. 061 stripped it from *nav* payloads as dead weight; that reasoning does not apply to a write report.

-> **Recommend KEEP.**

*(User standing approval: "suggest and do the best option, pass all gates" — proceeding on A + KEEP unless told otherwise at Gate 1.)*

### Universal inventory (R1 "every payload") — N = 8
1. success — full build (standard)
2. success — full build (minimal)
3. success — incremental (standard) — same shape as (1)
4. success — no-op incremental -> full fallback (mode names actual) — same shape
5. `busy` refusal
6. schema-mismatch `refused`
7. no-adapter refusal
8. empty-suffix / invalid-handshake refusal

**N = 8 distinct outcome/shape combinations** (test must enumerate, not sample — AC1).

### Cause / gap analysis (enhancement)
Gap: `build_or_update_index.py` builds every payload as an inline dict literal and never reads `config.index_root`; all other tools route through `nav_result`/`get_index_status` which attach it. Target: `index_root` on all 8 outcomes. `path:line` — `code_atlas/tools/build_or_update_index.py:78-86` (`_busy`), `:163-174` (`_refused`), `:177-203` (`_result`); tool boundary `:48-64` (where `AdapterError` escapes).

### Blast radius
- Entry/handler: `build_or_update_index.create` -> `build_or_update_index` (`code_atlas/tools/build_or_update_index.py`).
- Touched repo: `app` only. Files: the build tool, its tests, `tests/test_build_without_adapter_silent.py` (064 tool-path assertion), plus a new enumerating test.
- No schema/db-map. No core language branch (R1.1) — `index_root` is language-agnostic.

### TRACK / SCOPE / TIER
`TRACK: backend — 0/N touched files under UI paths`
`SCOPE: M` (one tool file + 2-3 test files; converts a raise->payload)
`TIER: full` (universal requirement with N=8 > 1; enumerating AC). Not lite-eligible.

### BASELINE
`BASELINE: green` — Docker scoped run (build/busy/without_adapter/index_root/index_status): **88 passed, 0 failed**, 1030 deselected. Untouched checkout. Definition of Done: delta-green (no new failure).

## Phase 2 — Design

### Gate 1 clearance
Matrix + AC table filled; `j` resolved on standing approval → **Q1 = A** (convert refusal to payload), **Q2 = KEEP db_path**.

### Approach
Route the build tool's payloads through `config.index_root`, the same single source (071) every other tool reads:
1. **`_result`** (success, min + std) — add `"index_root": config.index_root` to the **base** dict (so both detail levels carry it). On **standard**, add `last_ref` beside `last_commit` via `staleness.last_ref_for_payload(store)` (077 fold-in; reads stored meta, no git spawn, no per-call derivation → R4). `wrote`/`graph` groups untouched (060/C2).
2. **`_busy`** — add `"index_root": config.index_root` (already carries `db_path` + revision fields).
3. **`_refused`** (schema mismatch) — add `"index_root": config.index_root` (already carries `db_path`).
4. **No-adapter / empty-suffix / handshake refusal** — currently `AdapterError` escapes the tool boundary. Catch `AdapterError` in the tool function (inside the lock `with`, after `held`) and return `_adapter_refused(...)`: `{mode: "refused", requested_full, performed: false, reason: "no_usable_adapter", detail: str(exc), index_root, db_path, seconds}`. One reason constant (no message-sniffing → deterministic, no hidden branch); `detail` carries the specifics. Mirrors `schema_guard`: any adapter-unusable condition → one fingerprinted payload naming the tree, still **no index written / not a success** (064's actual concern preserved).

`index_root` is a pure `str` property — attaching it cannot raise (C3/R5.3). Always a resolved abs path (C4/061).

### Rejected alternatives
- **Classify `no_adapter` vs `empty_suffixes` by inspecting `str(exc)`** — brittle string-sniffing, non-deterministic across message edits, smells like a branch. Rejected for one `reason` + `detail`.
- **Leave the two paths raising; audit them as "not a payload" (Q1-B)** — contradicts AC1 ("each refusal … carry index_root") and the ticket's explicit enumeration. Rejected.
- **Attach `last_ref` on minimal success too** — minimal deliberately omits `last_commit` (cheap path); the revision detail rides with the commit detail on standard. `index_root` (the fingerprint) still ships on minimal. Kept minimal cheap.

### Assumptions
- `config.index_root` is a stable resolved abs path — **verified** (`config.py:78-84`, 071).
- `last_ref_for_payload(store)` reads `LAST_REF_KEY` meta with no git spawn and returns `OMIT` only when the index predates 077 — **verified** (`staleness.py:51-60`); post-build `LAST_REF_KEY` is always written (077), so `OMIT` is guarded but won't occur here.
- `AdapterError` from the config-refusal + handshake sites propagates uncaught to the tool boundary (only `SchemaVersionError` is caught in `_build`) — **verified** (`build_or_update_index.py:124-141`, `indexer.py:502/510`, `adapter.py:229`).
No `novel-untested` third-party/runtime assumption.

### Smallest change-list
| Change | File/area | Ph2 covered by | k/N |
|--------|-----------|----------------|-----|
| `index_root` on `_result` base dict (min+std) | `build_or_update_index.py:189-203` | R1,G1,C1,C4 | 1/8, 2/8, 3/8, 4/8 |
| `last_ref` on standard `_result` (077 fold) | `build_or_update_index.py:198-203` + import `staleness` | R4 | — |
| `index_root` on `_busy` | `build_or_update_index.py:78-86` | R1 | 5/8 |
| `index_root` on `_refused` | `build_or_update_index.py:163-174` | R1 | 6/8 |
| Catch `AdapterError` → `_adapter_refused` payload (index_root+db_path) | `build_or_update_index.py:48-64` (+ new helper) | R1,Q1-A | 7/8, 8/8 |
| Keep `db_path` (busy/refused/std + new refusal); verdict recorded | this doc + test | R2,AC2 | — |
| Audit table (already written) | this doc | R3,AC3 | — |
| **Proof collateral:** rewrite tool-path test to assert refusal payload | `tests/test_build_without_adapter_silent.py:64-75` | R1,Q1-A | — |
| New enumerating proving test (8 outcomes) | `tests/test_build_payload_names_its_tree.py` (new) | AC1,AC2 | 8/8 |

**Test blast-radius (mechanical):** grep of `raises(AdapterError` / `index_root` / `last_ref` in build tests → only `test_build_or_update_index_surfaces_empty_adapters` (tool path) breaks; folded in above. The `full_build`/`incremental_update` `raises` tests (`:49,60,96`) assert indexer internals — **unchanged** (indexer still fails loud). Busy `last_ref` asserts (`test_busy_build_staleness.py:63,110`) are additive-safe.

### Rule compliance
- **R1.1** (no language branch): `index_root` is language-agnostic; single `reason` constant avoids any `if`-on-content. ok
- **R4** (determinism): field read from `Config.index_root` / stored meta, never re-derived per call. ok
- **060/C2**: `wrote`/`graph` untouched; new keys are siblings. ok
- **R5.3/C3**: field attach is a pure property read; the new refusal path *removes* a raise (converts to payload) — strictly fewer raises. ok
- **061/C4**: `index_root` always a resolved path; `reason`/`detail` always meaningful; `last_ref` omitted (not null) when it would predate 077. ok

### Verification plan (per-AC, layer-matched)
| AC | risk layer | proof artifact | layer-match? |
|----|-----------|----------------|--------------|
| AC1 (all 8 outcomes carry index_root; enumerated) | integration (real tool + fake-adapter subprocess, lock, schema) | integration test enumerating 8 outcomes | ✅ |
| AC2 (db_path verdict recorded + tested) | logic + doc | assertion in same test + verdict in this doc | ✅ |
| AC3 (audit table, 0 unknown rows) | documentation | table in this ticket (0 unknowns) — manual-recorded | ✅ |

No ❌ rows. No coverage-gap exclusions needed. `TRACK: backend` → no frontend surfaces.

### Proving test
`tests/test_build_payload_names_its_tree.py::test_every_build_outcome_names_its_tree` — enumerates the 8 outcomes (full min/std, incremental, no-op→full, busy, schema-refused, no-adapter, empty-suffix) and asserts `payload["index_root"] == str(config.root.resolve())` on each. **Fails pre-change** (field absent on all; no-adapter raises), **passes post-change**.
Invocation: `scripts/docker-test.sh pytest -q tests/test_build_payload_names_its_tree.py` (Windows `pytest` red via `fcntl` — Docker per AGENTS.md).

### Rollback + porting
Rollback: revert the single tool file + delete the new test + revert the one folded test. No schema/data migration. Single repo (`app`) — no cross-repo porting.

### SCOPE
`SCOPE: M` — unchanged from analysis. One tool file (~30 lines), one new test, one folded assertion. No tier crossing; branch type `feat` matches (additive payload fields). No outgrew-its-ticket nudge.

## Phase 3 — Execute

Branch `feat/079-build-payload-does-not-name-its-tree`. Implemented the approved change list only.

### Verification sweep
- **Axis 1 (file set):** diff = `code_atlas/tools/build_or_update_index.py`, `tests/test_build_without_adapter_silent.py` (folded proof collateral), `tests/test_build_payload_names_its_tree.py` (new proving test), this working doc. All inside the approved list; no file outside it; no untouched-line reformatting; each hunk maps to a matrix row (R1/R4/R2/AC1). ✅
- **Axis 2 (design conformance):** every Gate-2 Approach bullet `implemented-as-approved` — index_root on `_result` base (min+std), `last_ref` on standard, index_root on `_busy`/`_refused`, `AdapterError`→`_adapter_refused` payload, `db_path` KEEP. No `deviated` bullet.
- **Note (test-assertion correction, not a design deviation):** the folded 064 test first asserted the refused build leaves *no DB file*; the store is opened (creating an empty file) before the adapter check raises — pre-existing 064 behaviour. Corrected to assert 064's real invariant (no index written: `last_commit`/`indexed_suffixes` are `None`). No production-code change.

### Proven by
- **AC1** — `tests/test_build_payload_names_its_tree.py::test_every_build_outcome_names_its_tree` (7 outcomes parametrized) + `::test_the_enumeration_covers_every_shape_not_a_sample`. Fails pre-079, passes post.
- **AC2** — `::test_db_path_is_kept_on_the_write_payloads` (+ verdict recorded here: KEEP).
- **AC3** — audit table above (0 "unknown" rows).
- **077 fold** — `::test_standard_success_names_the_revision_too`.

### Test results (Docker — Windows `pytest` red via `fcntl`, per AGENTS.md)
Full CI gate green: **ruff + mypy + 1130 passed** (baseline 88 scoped → green; no new failure). Delta-green proven.

## Phase 4 — Review
**WAIVED** per run argument "with skipped review". No reviewer/challenger dispatch; no `Reviewed at` marker. Delta-green proven in execute (full CI gate: ruff + mypy + 1130 passed). Scope held (diff ⊆ approved list); no outgrew-its-ticket nudge.

## Phase 5 — Finalise
Outward actions (maintainer standing approval + explicit run arg "commit + push + open PR"):
1. Commit code + tests — done (`daa5e74`).
2. Commit docs (PLAN §12, BACKLOG status + token row, task doc).
3. Push `feat/079-build-payload-does-not-name-its-tree`.
4. Open PR from `.github/pull_request_template.md`.

## Cost ledger
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| analysis | (no subagent dispatched; main-loop only) | 1 | n/a |
| design | (no subagent dispatched; main-loop only) | 1 | n/a |
| execute | (no subagent dispatched; main-loop only) | 1 | n/a |
