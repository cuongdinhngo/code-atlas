---
id: 082
slug: claims-nobody-outside-can-check
title: 'Two claims a field evaluator could not check: what `files` counts, and whether a busy build ever says so'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [068, 072, 028]
---

## Goal
Round 4 tried to verify two shipped fixes from the outside and could verify neither — not because they
are broken, but because nothing in the surface makes them checkable. **Part A:** `get_index_status`
publishes `files` / `parsed` / `failed` with no denominator, so 068's one-row correction is
unauditable. **Part B:** the evaluator could not make a build lose a race, so 072's `mode: "busy"` has
never been observed in the field. A fix that cannot be checked by its user is indistinguishable from a
fix that was not made — and this project's own history (round 2's stale server process, 060's
reproduced-then-refuted mismatch) is a record of what that costs.

## Part A — `files: 18,888` against a tree of 28,425 PHP files
- Round 4, §A.4: `files: 18,888` while `git ls-files '*.php'` = **28,425** (on-disk, excluding
  `vendor`/`node_modules`/worktrees: 28,427; adding `.inc`/`.phtml`: 28,442). The 9,537-file gap is
  presumably ignore rules and inclusion policy doing their job — but nothing in the payload discloses
  which policy produced 18,888, so a **±1** synthetic-bookmark drift is invisible from outside.
- The evaluator's verdict was **NOT EXERCISED**, with the honest reason: *"I cannot distinguish 18,888
  from 18,889 without knowing the denominator."* 068 was caught in round 3 precisely by two of our own
  numbers disagreeing by one; after the fix there is no way for an outsider to confirm it.
- Note the shape: this is the same class as 051 (a number that did not describe the thing it named) and
  058 (a count with no way to enumerate what it counted). 058's answer — publish the paths — is the
  precedent.
- **Deliverable:** publish the denominator. Collected vs kept vs indexed, the suffixes in force, and
  the skip counts by cause (ignore rule, suffix, size, unreadable), on the verbose status path where
  058 already put `parse_failures`. An outsider must be able to reconcile `files` against their own
  `git ls-files` without reading code-atlas source.

## Part B — five builds, zero `mode: "busy"`
- Round 4, §A.8: the evaluator ran a background loop hammering `code-atlas-poke` across four files and
  called `build_or_update_index` into it; the build won cleanly
  (`"mode":"incremental","wrote":{"files":4,…},"seconds":57.997`). Across five builds it never saw the
  refusal, and reported — correctly — that *"I cannot report the fix as working on the strength of
  never having lost a race."*
- **Correction to the retro's reasoning, verified in this repo:** it concluded no second builder is
  reachable because the console script starts the stdio server and `code-atlas-poke` reparses a single
  file. There is a third entry point — **`code-atlas-refresh`** (053) — which runs *the same path as*
  `build_or_update_index(full=false)` and already prints `skipped: another build is running`. So the
  race **is** reachable from the CLI; the surface simply does not tell an evaluator that, and the tool
  descriptions do not mention it. The finding stands, its cause moves: this is a documentation and
  affordance gap, not a missing capability.
- **Deliverable:** make the busy path observably testable. Document the `code-atlas-refresh` race
  recipe in the parallel-agents runbook, and add a supported way to exercise the refusal (a long-held
  build in the test suite already does this; what is missing is an operator-facing recipe with an
  expected payload beside it). Then have the next field round confirm the payload, not just the
  timings.

## Scope / Deliverables
- Part A: denominator fields on verbose `get_index_status`, with the skip causes counted; the
  bookmark's exclusion becomes checkable arithmetic rather than a claim.
- Part B: a documented, reproducible way for a user to see `mode: "busy"` with its staleness fields,
  plus the runbook line naming `code-atlas-refresh` as the second writer.
- **One line in each affected tool description** pointing at where the auditing data lives — the
  round-4 evidence is that agents read descriptions and do not read plans.
- Update 068 and 072 with pointers, so each records that its field verification is now possible.

## Constraints
- 061 — the denominator belongs on the **verbose** path; the default status payload must not grow.
- R4 — the skip counts are derived from the same walk that produces `files`, not a second traversal
  with its own answer; two ways to count is the defect, not the fix.
- R2 — no repo names in fixtures; the reconciliation test builds its own tree with known skips.
- Part B must not weaken the lock: exposing a way to *observe* contention is not a way to *create*
  corruption.

## Acceptance criteria
- Verbose `get_index_status` lets a reader reconcile `files` end to end: collected − skipped(by cause)
  = kept = `files`, proven by a fixture test where every term is asserted.
- With the rules channel on and off, the arithmetic still closes and the bookmark is visibly excluded
  (068's claim, now auditable).
- A documented recipe produces `mode: "busy"` with `performed: false` plus staleness fields, and a test
  pins that payload.
- 068 and 072 carry pointers here.

## References
Field retro round 4 §A.4 (`NOT EXERCISED`, the missing denominator), §A.8 (`NOT EXERCISED`, the race),
§11 item 3 (the pre-flight checks the wrong tense). Repo facts checked for this ticket:
`pyproject.toml:19-21` (three console scripts), `code_atlas/hooks/refresh.py:1-6,42-50` (`refresh`
runs the incremental path and reports a lost race). Related:
[068](068_rules-bookmark-counted-as-source-file.md) (the ±1 this makes auditable),
[072](072_busy-build-hides-staleness.md) (the refusal payload),
[058](058_list-parse-failures.md) (precedent: publish what a count counted),
[028](028_index-health-metrics.md) (the counters), [053](053_refresh-on-checkout-hook.md)
(`code-atlas-refresh`), [`runbooks/parallel-agents.md`](../runbooks/parallel-agents.md).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 082

## Session status
- **work_doc_mode**: embed (below separator; plain tracked ticket, not a scaffold stub)
- **Phase**: 5 finalise; Gates 0/1/2 cleared; **review WAIVED** (run arg "with skipped review")
- **Branch (planned)**: `feat/082-claims-nobody-outside-can-check`

## Phase 0 — Refine

### Premise check
`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
Resolved: `code-atlas-refresh` + `code_atlas/hooks/refresh.py:1-6,42-50` (exists; prints "skipped: another build is running"), `pyproject.toml:19-21` (3 console scripts), `docs/runbooks/parallel-agents.md` (exists), `get_index_status` tool (exists), tasks 068 + 072 (exist). No referenced-as-existing source missing → premise holds.

### Advisory recall
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
LESSONS.md is prose-format (not the structured claim-record shape); surfaced by area: **068** (synthetic anchors are edges, not source files — the ±1 Part A makes auditable), **072** (busy payload / staleness fields — Part B), **058** precedent (publish what a count counted — the Part A pattern). No `skill_gap_path` configured. Advisory only.

### Decision classification (Step 2 — every decision classified before asking)
All product-decisions are answerable from the ticket text / project convention → **how-decisions, resolved + cited**. No WANT the user is sole source of; the acceptance bar is already concrete and falsifiable in the ticket's AC block (tie-breaker (a) finds no open acceptance-bar want).

| # | Decision | Class | Resolution + citation |
|---|----------|-------|-----------------------|
| 1 | Part A field content: collected / kept / indexed + suffixes + skip-by-cause | HOW | Ticket §Part A Deliverable (lines 31-34) + 058 precedent (publish paths on verbose) |
| 2 | Skip-cause taxonomy | HOW | Ticket names exactly four: ignore rule, suffix, size, unreadable (line 33) |
| 3 | Placement = verbose path only | HOW | Constraint 061 (line 65); default payload must not grow |
| 4 | Derivation = single walk, not a second traversal | HOW | Constraint R4 (lines 66-67) |
| 5 | Part B recipe uses `code-atlas-refresh` as 2nd writer | HOW | Ticket §Part B (lines 44-49) + 053; refresh.py already reports the lost race |
| 6 | Recipe lives in `docs/runbooks/parallel-agents.md` | HOW | Ticket deliverable (line 59) |
| 7 | Busy payload pinned by a test | HOW | Existing `test_busy_build_staleness.py` is the model; add operator recipe + expected payload |
| 8 | One line in each affected tool description + pointers in 068/072 | HOW | Ticket deliverables (lines 60-62) |

### Open implementation risk (for analysis, NOT a refine want-decision)
Part A/R4: does the indexer's collect/skip walk **currently** attribute skips by cause, or must the walk be instrumented to count them without a second traversal? This is an analysis/design question (HOW refine cannot pre-resolve), flagged so analysis proves it against `code_atlas/indexer.py`.

### Exposure-checker verdict (1 dispatch, ticket-blind)
**No un-exposed WANT-level product-decisions.** "Unusually tight" ticket. Two HOW notes folded in:
- **9 (from #8):** `code-atlas-refresh` needs **no CLI change** — `refresh.py::_note()` only prints "skipped: another build is running"; Part B's AC requires a *test* pinning the payload + a runbook line, not new CLI output. Recipe/test go through the MCP `build_or_update_index` tool while `code-atlas-refresh` merely creates contention. HOW, cited `refresh.py:42-50` + ticket AC.
- **10 (from #10):** new verbose `get_index_status` fields — R3 judgment (new payload *fields* vs new vocabulary/qname). HOW for analysis, cited `docs/ENGINEERING_RULES.md` R3 + `contract.py`. Expected: additive fields, no `contract_version` bump — analysis confirms.

### REFINE count
`REFINE: 10 unresolved surfaced | 0 want-decision asked | 10 how-decision resolved+cited | 0 ASSUMED | skip: no`
No want-decision required the user; the acceptance bar is concrete in the ticket. Hand to analysis.

### Cost ledger
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker (challenger, ticket-blind) | 1 | 50,469 (9 tool-uses, 154 s) |

## Phase 1 — Analysis

### Premise / recall (carried from refine)
`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)` — 068, 072, 058 (area).

### Decomposition count
`SECTIONS: 6 found (Goal, Part A, Part B, Scope/Deliverables, Constraints, Acceptance criteria) | 6 decomposed | ROWS: C=4 R=6 G=1 AC=4`

### Requirements matrix
| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|----|--------|------------------|----------------|--------------|--------|
| G1 | Goal | make the two shipped fixes checkable from outside | Publish auditing data so an outsider can reconcile `files` and observe `busy` | neither is surface-checkable today | open |
| R1 | Part A / Scope | publish the denominator: collected vs kept vs indexed, suffixes in force, skip counts by cause | Add census fields to verbose status | `collect()` drops by suffix+ignore only; no per-cause count today (`indexer.py:323-346`) | open |
| R2 | Part A | outsider reconciles `files` vs their own `git ls-files` without reading source | Reconciliation arithmetic in the payload | `files`=`counts["files"]`=kept rows (`store.py:407-421`) | open |
| R3 | Part B / Scope | documented reproducible way to see `mode:"busy"` + staleness | Runbook recipe naming `code-atlas-refresh` as 2nd writer + expected payload | busy payload exists (072/079); refresh.py reports lost race (`refresh.py:42-50`) | open |
| R4 | Scope | one line in each affected tool description pointing at the auditing data | Docstring line in `get_index_status` (Part A) + `build_or_update_index` (Part B) | agents read descriptions, not plans | open |
| R5 | Scope | update 068 and 072 with pointers here | Pointer line in each task doc | — | open |
| R6 | Part B | add a supported way to exercise the refusal (test pins the payload) | Test asserts the recipe's busy payload | `test_busy_build_staleness.py` is the model | open |
| C1 | Constraint 061 | denominator on **verbose** path; default must not grow | Fields only under `detail_level="verbose"` | verbose adds `parse_failure_paths` (`get_index_status.py:164-170`) | open |
| C2 | Constraint R4 | skip counts from the **same walk** that produces `files`, not a 2nd traversal | Instrument `collect()`; store in meta; status reads it back | `collect()` is the single walk (`indexer.py:118,323`) | open |
| C3 | Constraint R2 | no repo names in fixtures; test builds its own tree with known skips | Synthetic fixture tree | R2 (CI-gated) | open |
| C4 | Constraint | Part B must not weaken the lock (observe != create corruption) | No lock change; recipe only observes | lock in build tool (053) | open |
| AC1 | AC | verbose lets a reader reconcile `files`: collected − skipped(by cause) = kept = `files`, fixture asserts every term | Falsifiable: fixture test asserts each term + closure | — | open |
| AC2 | AC | with rules channel on/off, arithmetic still closes + bookmark visibly excluded | Falsifiable: build both ways, assert closure + `files` identical | 068: bookmarks are edges not files | open |
| AC3 | AC | documented recipe produces `mode:"busy"` + `performed:false` + staleness, test pins it | Falsifiable: test asserts the payload | busy payload shipped (072) | open |
| AC4 | AC | 068 and 072 carry pointers here | Falsifiable: grep for the pointer | — | open |

### AC validation (falsifiability) + the taxonomy mismatch
- **AC1** falsifiable (fixture asserts collected/skipped/kept/files + closure). ok — **but see Q1: the cause set.**
- **AC2** falsifiable (two builds; assert closure + identical `files`; bookmark not in `files`). ok
- **AC3** falsifiable (test pins `mode/performed/staleness`). ok
- **AC4** falsifiable (grep 068/072 for the `082` pointer). ok

**Uncodified-standard nudge:** none — all standards applied are codified (R1.1/R2/R3/R4/R5.3, 061).

### CLARIFICATION
`CLARIFICATION: 3 raised | 2 self-resolved (cited) | 1 for human decision`

**Q1 (for human — AC-value vs reality) — the skip-cause taxonomy.** The ticket names four causes: *ignore rule, suffix, size, unreadable*. Computed against the code, only **two are collect-time skips**: **suffix** (`_suffix(path) not in wanted`) and **ignore rule** (`matcher.is_ignored`) — `indexer.py:344-346`. The other two:
- **"unreadable"** is not a collect skip — an unreadable/parse-failing file still gets a `files` row with `parsed_ok=0` and is counted as **`failed`**, already enumerable on verbose via `parse_failures` + `parse_failure_paths` (058). It belongs *inside* `files`, not in the skipped set.
- **"size"** — code-atlas applies **no size limit**; there is no such skip. Inventing one would be new inclusion policy (scope creep) and would change what gets indexed.

→ **Recommendation:** publish the two real collect causes (`suffix`, `ignore`); reconciliation is `collected − skipped_suffix − skipped_ignore = kept`, and `kept + stubs = files`, with `parsed`/`failed` partitioning `files` (unreadable = `failed`, already published). Do **not** add a size skip. Closes the arithmetic honestly, keeps R4/061. *(Standing approval: proceeding on this at Gate 1 unless told otherwise.)*

**Q2 (self-resolved, cited) — contract_version bump?** No. The frozen, versioned contract is the **adapter JSONL contract** (`contract.py`, R3); `get_index_status`'s tool payload is not that contract, and these are additive fields, not new vocabulary/qname. No bump. (R3; `contract.py`.)

**Q3 (self-resolved, cited) — where the census is computed.** In `collect()` at **full_build** (the single whole-tree walk), stored in `meta`, read back by verbose status (no 2nd traversal → R4). Incremental does not re-walk the whole tree, so the census reflects the last full build; the fixture AC uses a full build. (`indexer.py:118,323`; C2/R4.)

### Universal inventory (R4 "one line in each affected tool description")
Affected tool descriptions (N=2): **1.** `get_index_status` (Part A auditing data), **2.** `build_or_update_index` (Part B busy). Per-item — review confirms both, not a total.
Pointer updates (R5, N=2): **1.** task 068, **2.** task 072.

### Cause / gap analysis (enhancement)
Gap A: `collect()` returns only the kept tuple; the collected total and the two drop causes are computed-then-discarded. Target: return a census {collected, skipped_suffix, skipped_ignore}, store in meta, publish on verbose. `path:line` `indexer.py:323-346`, `store.py:407-421`, `get_index_status.py:164-170`.
Gap B: the busy path is reachable via `code-atlas-refresh` but no operator recipe documents it. Target: runbook recipe + a test pinning the payload. `path:line` `code_atlas/hooks/refresh.py:42-50`, `docs/runbooks/parallel-agents.md:58-68`.

### Blast radius
- Handlers: `get_index_status` (Part A), `build_or_update_index`/`refresh` (Part B docs).
- Touched: `code_atlas/indexer.py` (census in collect), `code_atlas/store.py` (meta key(s); generic key-value `meta` table → **no schema migration**), `code_atlas/tools/get_index_status.py` (verbose fields + docstring), `code_atlas/tools/build_or_update_index.py` (docstring line), `docs/runbooks/parallel-agents.md`, `docs/tasks/068*`, `docs/tasks/072*`, tests (new reconciliation fixture + busy-recipe test).
- Repo: `app` only. No core language branch (R1.1) — census is language-agnostic.

### RULE SECTIONS (by change type)
`RULE SECTIONS: R1.1, R2, R3, R4, R5.3, §061 — R1.1 ok (census language-agnostic), R2 ok (fixture builds own tree, no repo names), R3 ok/N-A (tool payload != adapter contract; additive fields, no vocabulary change), R4 ok (single collect walk; census stored+read, no 2nd traversal), R5.3 ok (census compute must not break the build), §061 ok (verbose-only). No DB-conventions section (no migration — generic meta KV). No UI/a11y section (backend).`

### BASELINE
`BASELINE: green` — Docker scoped run (index_status/indexer/busy/counts/collect/staleness/health/parse_fail): **94 passed, 0 failed**, 1036 deselected. Untouched checkout. DoD: delta-green.

### TRACK / SCOPE / TIER
`TRACK: backend — 0/N touched files under UI paths`
`SCOPE: M` (indexer census + store meta + verbose fields + 2 docstrings + runbook + 2 pointers + 2 test areas; additive, no migration)
`TIER: full` (universal "each affected tool description" N=2; multi-part; fixture + arithmetic ACs)

## Phase 2 — Design

### Gate 1 clearance
Matrix + AC filled; `j` resolved on standing approval → **Q1: publish the two real collect causes (suffix, ignore); no size skip; unreadable = existing `failed`.**

### Approach
**Part A — a collection census from the single collect walk, stored in meta, published on verbose.**
`collect()` already walks the tree once (git `ls-files`, or `_walk` fallback) and filters to kept. Partition that same `found` list in one pass into `{skipped_suffix, skipped_ignore, kept}` — the arithmetic `collected − skipped_suffix − skipped_ignore = kept` then **closes by construction** (it is a partition), and on a git repo `collected == len(git ls-files)`, exactly the outsider's denominator.
- `indexer.py`: add `CollectionCensus(collected, skipped_suffix, skipped_ignore, kept)` + internal `_collect_with_census(root, suffixes) -> (kept_tuple, census)`. Public **`collect()` delegates** to `_collect_with_census(...)[0]` — **signature unchanged**, so the 6 existing `collect()` test call sites and 2 prod sites keep working. Both build paths (`full_build:118`, `incremental_update:172`) already call `collect()` over the whole tree, so both capture the census; `_record_meta` gains a `census` param and stores it (JSON under one meta key).
- `store.py`: `COLLECTION_CENSUS_KEY = "collection_census"` + `collection_census() -> dict[str,int] | None` (parse the JSON meta; generic KV `meta` table → **no schema migration**).
- `get_index_status.py`: on **verbose only** (C1/061), when census meta present, add a `collection` block `{collected, skipped:{suffix, ignore}, kept, indexed_suffixes:[…]}`. Omitted (not null) for a pre-082 index (the 077 OMIT pattern). Outsider reconciles: `collected − skipped.suffix − skipped.ignore == kept`, and `kept + stubs == files` (both `stubs` and `files` already in the payload's counts). Docstring pointer line (R4).

**Part B — document the busy race; the payload pinning already exists, extend it once.**
The busy path is already reachable and tested: `test_git_refresh_hook.py:88` proves `code-atlas-refresh` reports the lost race, `:109` proves the build tool returns `mode:busy` under a held lock, and `test_busy_build_staleness.py` pins the full staleness payload. The **missing** artifact (per the ticket) is the operator-facing recipe.
- `docs/runbooks/parallel-agents.md`: add a "Reproduce a busy refusal" recipe naming `code-atlas-refresh` as the second writer, with the expected payload block beside it.
- Extend `test_git_refresh_hook.py::test_build_tool_returns_busy_when_lock_held` to also assert `performed is False` + the staleness fields — so the documented recipe's payload is test-backed at the recipe's own site (AC3).
- `build_or_update_index.py`: one docstring line pointing at the runbook recipe (R4).

**Cross-cutting:** pointer lines added to tasks 068 and 072 (R5).

### Rejected alternatives
- **A second `collection_census()` walk read at status time** — a second traversal with its own answer is exactly the R4 defect the ticket names ("two ways to count is the defect, not the fix"). Rejected — census is computed in the build's collect walk and read back from meta.
- **Change `collect()` to return `(kept, census)`** — breaks 6 existing test call sites + 2 prod sites that treat it as a bare tuple. Rejected for the internal `_collect_with_census` + thin delegating wrapper.
- **Add "size"/"unreadable" skip causes** — code-atlas applies no size limit, and unreadable = parse-time `failed` (already on verbose via 058). Inventing a size filter is new inclusion policy (scope creep) that changes what gets indexed. Rejected (Gate-1 Q1).
- **A new Part-B test file** — the pinning already exists across two suites; a new file duplicates it. Rejected for a one-assertion extension of the recipe's own test.

### Assumptions
- `collect()` is called over the whole tree on **both** full and incremental builds (`indexer.py:118,172`), so the census is fresh after every build — **verified** (read both call sites).
- `files` rows == `len(kept_source) + len(kept_stubs)`; a parse-failed file keeps its row (`parsed_ok=0`) so it stays inside `files`, not skipped — **verified** (`full_build:125,138`, `store.upsert_file:321-330`, `counts:407-421`).
- Bookmarks/rules edges never create a `files` row, so rules-on/off leaves `files` and the census identical (AC2) — **verified** (068; `indexer.py:547`).
- `meta` is a generic key-value table; adding a key needs no migration — **verified** (`store.set_meta/get_meta`).
- The busy path is reachable via `code-atlas-refresh` and already tested — **verified** (`test_git_refresh_hook.py:88,109-126`).
No `novel-untested` third-party/runtime assumption.

### Smallest change-list
| Change | File/area | Blast radius | Ph2 covered by | k/N |
|--------|-----------|--------------|----------------|-----|
| `CollectionCensus` + `_collect_with_census`; `collect()` delegates; capture census in both build paths | `indexer.py:118,172,323-346` | `collect()` callers (6 tests + 2 prod) — signature unchanged, none affected; `_record_meta` gains param (internal only, 0 test callers) | R1,C2,R4 | — |
| Store census in meta via `_record_meta` | `indexer.py:705-716` | new meta key, additive; no schema migration (generic KV) | R1,C2 | — |
| `COLLECTION_CENSUS_KEY` + `collection_census()` reader | `store.py` (constants + method) | none identified (new symbol) | R1,C1 | — |
| `collection` block on verbose + docstring pointer | `get_index_status.py:164-170` (verbose branch) + docstring | verbose keyset — no exact-keyset assert on verbose (minimal keyset test `:126` untouched) | R1,R2,R4,C1 | 1/2 (tool desc) |
| Docstring pointer to runbook recipe | `build_or_update_index.py` (docstring) | none identified | R4 | 2/2 (tool desc) |
| Busy reproduction recipe + expected payload | `docs/runbooks/parallel-agents.md:58-68` | none (docs) | R3 | — |
| Pointer to 082 | `docs/tasks/068_*`, `docs/tasks/072_*` | none (docs) | R5 | 1/2, 2/2 |
| **Proof collateral:** extend busy test to assert `performed:false` + staleness | `tests/test_git_refresh_hook.py:109-126` | that test only (additive assertions) | AC3,R6 | — |
| New reconciliation fixture test (census terms + closure + rules on/off) | `tests/test_files_reconciliation.py` (new) | none (new file) | AC1,AC2 | — |

**Test blast-radius (mechanical):** grep of `collect(` (6 test call sites: `test_indexer.py:204,219,222`, `test_legacy_hardening.py:97,139,140` — all expect a bare tuple → **unbroken** by the delegating wrapper); `_record_meta` (0 test callers); verbose-status exact-keyset asserts (**none**; `test_get_index_status_health.py:126` asserts the **minimal** keyset, which this change does not touch). No producer/consumer of `collect()`'s return shape is disturbed.

### Rule compliance
- **R4** (determinism / one count): census is a partition of the single collect walk, stored + read back — never a second traversal. ✅
- **R1.1** (no language branch): census counts by suffix/ignore, language-agnostic. ✅
- **061** (verbose-only): `collection` on verbose only; minimal/standard unchanged. ✅
- **R2** (standard over sample): fixture builds its own tree (wrong-suffix + built-in-ignored `vendor/` path + kept), no repo names. ✅
- **R3**: tool payload ≠ frozen adapter contract; additive fields, no vocabulary/qname change → no `contract_version` bump. ✅
- **R5.3**: census compute is pure counting in the existing walk; cannot raise a new failure. ✅
- **C4** (Part B lock): docs + assertions only; no lock change. ✅

### Verification plan (per-AC, layer-matched)
| AC | risk layer | proof artifact | layer-match? |
|----|-----------|----------------|--------------|
| AC1 (reconcile files end to end; every term asserted) | integration (real build → collect walk → store meta → verbose status) | integration fixture test | ✅ |
| AC2 (rules on/off closes; bookmark excluded) | integration | same fixture, two builds (rules set/unset) | ✅ |
| AC3 (recipe → mode:busy + performed:false + staleness; test pins) | integration (lock contention + tool) | extended `test_git_refresh_hook` busy test | ✅ |
| AC4 (068/072 carry pointers) | documentation | grep for the `082` pointer | ✅ |
| R4 (one line per affected tool desc) | documentation | grep the docstrings | ✅ |

No ❌ rows. No coverage-gap exclusions. `TRACK: backend` → no surfaces.

### Proving test
`tests/test_files_reconciliation.py::test_verbose_status_reconciles_files_end_to_end` — builds a fixture tree with a known split (N kept `.php`, M wrong-suffix, K tracked-but-ignored `vendor/*.php`), full build, verbose `get_index_status`, asserts `collection.collected`, `collection.skipped.suffix`, `collection.skipped.ignore`, `collection.kept` each == expected, that `collected − skipped.suffix − skipped.ignore == kept`, and `kept + stubs == files`. **Fails pre-change** (no `collection` field on verbose), **passes post-change**.
Invocation: `scripts/docker-test.sh pytest -q tests/test_files_reconciliation.py` (Windows `pytest` red via `fcntl`, per AGENTS.md).

### Rollback + porting
Rollback: revert `indexer.py`/`store.py`/`get_index_status.py`/`build_or_update_index.py` + the two docs + the two test edits; delete the new test. No schema/data migration. Single repo (`app`); no cross-repo porting.

### SCOPE
`SCOPE: M` — unchanged from analysis. Additive census (no signature change, no migration), verbose field, two docstrings, one runbook recipe, two pointers, one new test + one extended test. No tier crossing; branch type `feat` matches (additive capability). No outgrew-its-ticket nudge.

## Phase 3 — Execute

Branch `feat/082-claims-nobody-outside-can-check`. Implemented the approved change list only.

### Verification sweep
- **Axis 1 (file set):** diff = `indexer.py`, `store.py`, `build_or_update_index.py` (docstring), `get_index_status.py`, `docs/runbooks/parallel-agents.md`, `docs/tasks/068*` + `072*` (pointers), `docs/tasks/082*` (working doc), `tests/test_git_refresh_hook.py` (extended busy test), `tests/test_files_reconciliation.py` (new). All inside the approved list; no file outside; no untouched-line reformatting; each hunk maps to a matrix row.

```
$ git --no-pager diff --stat  (+ untracked test_files_reconciliation.py)
 code_atlas/indexer.py                     | 59 +++-
 code_atlas/store.py                       | 16 ++
 code_atlas/tools/build_or_update_index.py |  3 +-
 code_atlas/tools/get_index_status.py      | 29 ++-
 docs/runbooks/parallel-agents.md          | 29 +++
 docs/tasks/068_*.md                       |  4 +
 docs/tasks/072_*.md                       |  3 +
 tests/test_git_refresh_hook.py            |  4 +
```

- **Axis 2 (design conformance):** every Gate-2 Approach bullet `implemented-as-approved`:
  - `CollectionCensus` + `_collect_with_census`; `collect()` delegates (signature unchanged) — done.
  - census captured on both build paths (`full_build`, `incremental_update`), stored via `_record_meta` — done.
  - `store.py` `COLLECTION_CENSUS_KEY` + `collection_census()` reader (JSON, no migration) — done.
  - verbose `collection` block, omitted for pre-082 index; docstring pointer — done.
  - `build_or_update_index` docstring points at the runbook recipe — done.
  - runbook busy recipe + expected payload; 068/072 pointers — done.
  - busy test extended to assert `performed:false` + staleness — done.
  No `deviated` bullet.

### Test results (Docker — Windows `pytest` red via `fcntl`, per AGENTS.md)
```
$ scripts/docker-test.sh pytest -q -k "reconciliation or index_status or indexer or busy or counts
    or collect or staleness or health or parse_fail or refresh or store or legacy_hardening or view_databag"
212 passed, 922 deselected in 15.40s
```
Proving test `test_verbose_status_reconciles_files_end_to_end` passed; PHP AC2 test `test_arithmetic_closes_and_bookmark_excluded_with_rules_on_and_off` ran (0 skipped) and passed. Full CI gate result recorded below.

### Proven by
- **AC1** — `tests/test_files_reconciliation.py::test_verbose_status_reconciles_files_end_to_end` (every term + closure + kept+stubs==files) + `::test_collection_absent_before_first_build_and_omitted_pre_082` (061). Fails pre-082, passes post.
- **AC2** — `::test_arithmetic_closes_and_bookmark_excluded_with_rules_on_and_off` (census + files identical rules on/off; bookmark fired but is not a file).
- **AC3** — `tests/test_git_refresh_hook.py::test_build_tool_returns_busy_when_lock_held` (now asserts `performed:false` + staleness) + the runbook recipe.
- **AC4** — 068 + 072 carry the `082` pointer.
- **R4** — docstring pointer lines in `get_index_status` (collection) + `build_or_update_index` (runbook recipe).

### Full CI gate (delta-green)
```
$ scripts/docker-test.sh   # ruff + mypy + pytest
1134 passed in 54.43s
```
Baseline 94 scoped -> green; +4 tests from 082; no new failure. Delta-green proven.

## Phase 4 — Review
**WAIVED** per run argument "with skipped review". No reviewer/challenger dispatch; no `Reviewed at` marker. Scope held (diff subset of approved list); no outgrew-its-ticket nudge.

## Phase 5 — Finalise
Outward actions (maintainer standing approval + run arg "commit + push + open PR"): commit (code, tests, docs) -> push branch -> open PR from template.
