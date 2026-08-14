---
id: 092
slug: untracked-files-are-invisible-and-answer-no-such-symbol
title: 'An untracked file is silently skipped, then answers `no_such_symbol` for a class that is on disk'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [073, 082, 065]
---

## Goal
An agent wrote four new classes, rebuilt the index, and asked who consumes them. It got
`reason: "no_such_symbol"` — the vocabulary's word for *there is no such thing* — for a class that
existed on disk at `…/Controller/SiteMaintenanceController.php:17`. The cause was that the files
were **untracked**: `collect()` takes `git ls-files` as the walked set
(`code_atlas/indexer.py:366-367`), so an untracked file is not skipped-by-rule, it is never seen at
all. Every surface read green while this was true — the build reported `wrote:{files:14,…}` with no
mention of a skip, and `get_index_status` reported `dirty_indexed_files: 0`, which is literally true
(an unindexed file cannot be a dirty *indexed* file) and actively misleading.

The vocabulary already owns the right word — `not_indexed` (`code_atlas/tools/nav_result.py:21`) —
and the miss path did not reach for it. This is the round's §9 primary finding and the only one that
demonstrably cost the evaluator working time.

## Evidence (field retro round 5, 2026-08-14, **real work** — not a probe)
- Verbatim, after creating the file and rebuilding:
  ```json
  {"indexed":true,"qname":"\\…\\SiteMaintenanceController","results":[],
   "reason":"no_such_symbol","total_count":0}
  ```
- Build payload for the same rebuild: `{"mode":"incremental","wrote":{"files":14,…},"graph":{…}}` —
  no skip count, no untracked count.
- `get_index_status` at the same moment: `dirty_indexed_files: 0`.
- The reason changed only after `git add` + commit + rebuild — to
  `relationship_not_modelled`, which was the *correct* nothing (§4 row 2). Until that commit,
  **two independent nothings were stacked and indistinguishable** (retro §11.4): untracked
  invisibility and an unmodelled edge kind, both presenting as `results: []`.
- Consequence recorded in the retro's verdict (§10): a written carve-out — *"not for files you have
  just written and not yet committed"* — against a repo whose agent guide makes code-atlas mandatory
  for symbol questions.
- The evaluator attributed the empty answer to staleness, routed to `grep`, and had to correct the
  report to the operator when asked directly. **Right answer, wrong reason** — the failure mode 065
  exists to prevent.

## What "honest" looks like here
The agent most likely to ask about a file is the agent that just wrote it. Three states must be
distinguishable from the payload alone:
1. **On disk, indexable suffix, not ignored, but untracked** → `not_indexed`, with a `try_instead`
   naming the remedy. Never `no_such_symbol`.
2. **On disk and deliberately excluded** (suffix or ignore rule) → already covered by 082's census;
   the miss path should say which.
3. **Nowhere on disk** → `no_such_symbol` stays correct and this ticket changes nothing.

## Scope / Deliverables
- **Report the skip.** Add an untracked bucket to the collection census
  (`CollectionCensus`, `code_atlas/indexer.py:333-344`) and surface it on
  `get_index_status(verbose)` under `collection.skipped` **and** on the build payload. The 082
  identities must still close by construction — decide in design whether untracked files enter
  `collected` (changing the `git ls-files` denominator claim at `indexer.py:338`) or sit beside it as
  a separate walk; state the choice and why.
- **Classify the miss.** When a single-subject lookup misses and the subject maps to a path that
  exists on disk with an indexed suffix and is not ignored, return `not_indexed`, not
  `no_such_symbol`. Reuse `classify_missing_subject` (075/076) rather than adding a second classifier.
- **Give it a route.** `try_instead` must name the remedy, and must obey [093](093_try-instead-is-not-a-callable-tool-name.md) —
  a real tool name plus a prose hint, not an identifier-shaped instruction.
- **Bound the disk check.** The classification runs on the miss path only; a hit must not pay for it,
  and the check must not walk the tree (066's disclose-the-bound precedent).
- **Decide the qname→path direction explicitly.** A qname does not carry a path. Record in design how
  the miss path finds candidate files for an unindexed subject (adapter-free heuristic? a bounded
  suffix scan of the untracked set collected above?) — and if the answer is "only reachable via the
  untracked census", say so and scope the fix to that.

## Constraints
- R1.1 — no language branch in the core; "indexable suffix" is already config, not PHP knowledge.
- R4 — the untracked count must be deterministic for a given tree; no timestamp or ordering effects.
- R3 — `not_indexed` is existing vocabulary; adding no new reason value means no `contract_version`
  bump, but the conformance suite must gain the case.
- Cost: the census runs inside the existing single walk (082's rule — no rival second traversal).
- The fix must not make an untracked file *indexed*. Indexing untracked files is a separate decision
  with its own blast radius; this ticket makes the skip **visible**, not the skip go away.

## Acceptance criteria
- A test creates an untracked file with an indexed suffix, builds, and asserts: the build payload and
  `get_index_status(verbose)` both carry a non-zero untracked count, and the 082 identities still
  reconcile.
- A single-subject lookup for a symbol in that file returns `reason: "not_indexed"` with a
  `try_instead`, and the whole payload is pinned.
- After `git add` + rebuild, the same lookup returns the real answer; a symbol that is nowhere on disk
  still returns `no_such_symbol`.
- `dirty_indexed_files: 0` alongside a non-zero untracked count is covered by a test that documents
  the two are different questions.

## References
Field retro round 5 §4 row 1, §5 ("the gap 077 does not close"), §9 primary, §11.4; candidate 1.
Related: [073](073_freshness-cannot-find-what-is-not-indexed.md) (read-through freshness repairs only
rows it already found — this is the same blind spot on the collection side),
[082](082_claims-nobody-outside-can-check.md) (the census this extends),
[065](065_empty-answer-cannot-explain-itself.md), [075](075_read-symbol-confident-zero-on-unnormalised-qname.md)
and [076](076_bare-name-subject-reads-as-absence.md) (the classifier to reuse),
[093](093_try-instead-is-not-a-callable-tool-name.md).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 092

## Session status
- **work_doc_mode**: embed (below separator; plain tracked ticket, not a scaffold stub)
- **Phase**: 5 finalise; Gates 0/1/2 cleared (7 ASSUMED A–G confirmed); **review WAIVED** (run arg — no `Reviewed at` marker)
- **Branch**: `fix/092-untracked-files-are-invisible-and-answer-no-such-symbol`
- **TIER**: full · **SCOPE**: M · **TRACK**: backend · **STRUCTURE**: native

## Phase 0 — Refine

### Premise check
`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
Resolved as existing: `indexer.py` `collect`/`_collect_with_census`/`CollectionCensus`; `nav_result.py` `REASON_NOT_INDEXED` + `classify_missing_subject`; tickets 073, 082, 065, 075, 076, **093 exists**; `get_index_status` `_collection_field`. Ambiguous (not blocking): prose “the miss path.”

### Advisory recall
`RECALL: 2 claim(s) surfaced | 0 by symbol | 0 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
LESSONS.md is prose (no type-2 `handle:` records). Area: **028** (index-status/parse-health), **041** (ignore/indexer). On merits (not recall-injected): **082** (census is a partition of one walk), **069** (reuse `not_indexed` — do not add a NAV_REASONS member), **060** (`wrote` is the delta), **075** (nav reason ≠ adapter `contract_version`).

### REFINE count
`REFINE: 13 unresolved surfaced | 0 want-decision asked | 7 how-decision resolved+cited | 7 ASSUMED | skip: no`

### HOW (resolved + cited)
| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Where classification lives | Extend `classify_missing_subject`; no second classifier | ticket Scope; `nav_result.py:216` |
| 2 | Indexable suffix | Config/handshake suffixes, not PHP | R1.1; `indexer.py` `_suffix`/`wanted` |
| 3 | Do not index untracked | Census + miss honesty only | ticket Constraints |
| 4 | No new `reason` / no `contract_version` bump | Reuse `not_indexed` | ticket C; LESSON 075 |
| 5 | Non-git | Untracked bucket 0; `_walk` already sees disk | `indexer.py:366-367` |
| 6 | 082 identity preserved | Untracked sits **beside** `collected`, not inside it | `indexer.py:337-338`; 082 |
| 7 | Bound | Miss path reads stored path list; no tree walk at query time | ticket Scope; 066 |

### ASSUMED (awaiting Gate-1 confirm — standing “best option”)
| ID | Assumed choice | Why | Reverses prior? |
|----|----------------|-----|-----------------|
| A | Untracked **beside** the 082 partition. `collected == len(git ls-files)` unchanged. New `skipped.untracked`. | Changing the denominator breaks 082’s outsider claim | no |
| B | Census numerator = untracked paths with **indexable suffix AND not ignored** (honest state 1) | State 2 stays 082; counting `.txt` would inflate the bucket the miss path uses | no |
| C | qname→path **only** via stored untracked-indexable path list from last build. Match last ident of the type part **and** `PurePosixPath(hay).stem` to file stem. No adapter parse, no tree walk | Ticket’s “if only via census, say so” | no |
| D | `try_instead` = `"build_or_update_index"` (real MCP tool). Sibling `try_instead_hint` = git-add-then-rebuild prose. Omit hint when empty (061). Do **not** put git-add in the identifier slot (093) | 093 exists and 092 ships first | no |
| E | Miss payload names the matching path (`untracked_path` unique / `untracked_paths` many). Index remains `indexed: true` (DB exists). New *meaning* of `not_indexed` vs today’s “no DB” | Ticket honest-state 1; 061 omit empty | no |
| F | State 2 (ignored / wrong suffix) stays **082 census only** this ticket; those lookups still `no_such_symbol` | Ticket Scope “already covered by 082”; miss-path naming of ignore is 095 | no |
| G | **073 wins**: `ensure_qname` → `index_stale` before the untracked check. AC pins `dirty_indexed_files: 0` beside non-zero untracked | Freshness already returns first (`find_callers.py:109-125`) | no |

### Exposure-checker
Ticket-blind challenger found 5 unexposed decisions (census placement, numerator, qname→path, try_instead shape, 073 vs untracked). Folded into ASSUMED A–G.

### Cost ledger
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker (challenger, ticket-blind) | 1 | unmeasured (blocking retrieval) |

## Phase 1 — Analysis

`PREMISE:` and `RECALL:` carried from refine.
`STRUCTURE: native`
`SECTIONS: 7 found (Goal, Evidence, What honest looks like, Scope / Deliverables, Constraints, Acceptance criteria, References) | 7 decomposed | ROWS: C=5 R=5 G=4 AC=4`

### Requirements matrix
| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|----|--------|------------------|----------------|--------------|--------|
| G1 | Goal | untracked file → `no_such_symbol` for a class on disk | Make the skip visible; never index the file | `indexer.py:366-367` `git ls-files` | open |
| G2 | Honest 1 | on disk, indexable, not ignored, untracked → `not_indexed` + `try_instead` | Reuse `REASON_NOT_INDEXED`; `indexed: true` | `nav_result.py:33`; `empty_nav` is the *unbuilt* use | open |
| G3 | Honest 2 | deliberately excluded → 082 census; miss path should say which | **ASSUMED F**: census only this ticket | `_collection_field` | open |
| G4 | Honest 3 | nowhere on disk → `no_such_symbol` unchanged | Negative control | existing miss | open |
| R1 | Scope | untracked bucket on census + verbose status + build payload; 082 identities still close | `skipped.untracked` beside partition; collection sibling on build **not** inside `wrote` (060) | `CollectionCensus`; `_result` nests `wrote` | open |
| R2 | Scope | miss + maps to indexable untracked path → `not_indexed`; reuse classifier | Extend `classify_missing_subject`; all 5 `no_such_symbol` emitters inherit | callers listed in inventory | open |
| R3 | Scope | `try_instead` names remedy; obey 093 | real tool + `try_instead_hint` | 093 ticket; `attach_try_instead` | open |
| R4 | Scope | miss path only; no tree walk | stored path list; git spawn at **build** | 066 | open |
| R5 | Scope | decide qname→path explicitly | **ASSUMED C**: census stems only | — | open |
| C1 | Constraint | R1.1 no language branch | suffix from config | CI grep-gate | open |
| C2 | Constraint | R4 deterministic count | sorted git `-z` paths | `gitutil.ls_files` pattern | open |
| C3 | Constraint | R3 no new reason; conformance gains the case | reuse `not_indexed`; pin payload in tests (nav reason suite, not adapter contract) | LESSON 075 | open |
| C4 | Constraint | census in existing single walk; no rival traversal | second **git spawn** (`ls-files -o`), not a second filesystem walk | 082 | open |
| C5 | Constraint | do not index untracked | `kept` unchanged | ticket | open |
| AC1 | AC | untracked file + build → non-zero untracked on build payload **and** verbose status; 082 identities reconcile | falsifiable | — | open |
| AC2 | AC | single-subject lookup → `not_indexed` + `try_instead`; whole payload pinned | falsifiable | — | open |
| AC3 | AC | after `git add` + rebuild, same lookup = real answer; nowhere = `no_such_symbol` | falsifiable | — | open |
| AC4 | AC | `dirty_indexed_files: 0` beside non-zero untracked is a different question | falsifiable | 073 `dirty_paths` excludes untracked | open |

### AC validation
All four ACs are falsifiable (counts, reason strings, payload keys, identity arithmetic). No manual-check exclusion. No uncodified-standard nudge.

### CLARIFICATION
`CLARIFICATION: 7 raised | 0 self-resolved (cited) | 7 for human decision (all ASSUMED A–G)`
Gate 0 folds into Gate 1 under standing approval: **A–G confirmed**.

### Universal inventory (R2 — each single-subject tool that emits `no_such_symbol` on absent)
`N=5` — review/proof must confirm **each**, not a total:
1. `find_callers`
2. `find_references`
3. `find_implementations`
4. `find_view_data`
5. `read_symbol`
`explain_path` / `impact` call the classifier only to re-point unique seeds (no `no_such_symbol` channel) — N/A for the emit requirement; they inherit “untracked ≠ resolved_unique” automatically.

### Cause / gap (bug — taxonomy: `logic`)
`collect()` walks `git ls-files` only (`indexer.py:366-367`). Untracked files are never in `found`, so they are not skipped-by-rule and never counted. Build `wrote` and `dirty_indexed_files` (tracked∩indexed) stay green. Miss path classifies absent → `no_such_symbol` (`relation_reason` / `_resolve_miss`). Target: count state-1 untracked at collect; classify that miss as `not_indexed`.

### Blast radius
Handler: `_collect_with_census` + `classify_missing_subject`. Touched: `gitutil`, `indexer`, `store` (new meta key + reader), `get_index_status`, `build_or_update_index`, `nav_result`, 5 tools above, tests, docs. Repo `app` only. **No** `NAV_REASONS` member add (069 collateral avoided). `collection_census()` int-casts every JSON value — **must not** store the path list on that key.

### RULE SECTIONS
`RULE SECTIONS: R1.1 ✅, R1.2 ✅, R1.4 ✅ (store owns meta; indexer collects; tools present), R3 ✅ (no adapter vocab change), R4.2 ✅, R5.3 N/A (not a fail-loud config error), 060 ✅ (collection sibling, not inside wrote), 061 ✅ (omit empty hint/path), 066 ✅ (bound = stored list, not a walk). No DB-conventions (generic KV meta). No UI.`

### BASELINE
`BASELINE: green` — `scripts/docker-test.sh pytest -q` on untouched checkout: **1160 passed** in 81.58s. DoD: verification command passes (delta-green vs this baseline).

### TRACK / SCOPE / TIER
`TRACK: backend — 0/N touched files under UI paths`
`SCOPE: M` (census + classifier + 5 emitters + tests; not a new subsystem)
`TIER: full` (universal N=5 > 1; not lite-eligible)

## Phase 2 — Design

### Gate 1 clearance
Matrix + AC filled; ASSUMED A–G confirmed on standing approval.

### Approach
1. **Build-time census (beside 082).** After the existing `ls-files` partition, spawn `git ls-files -o -z --exclude-standard`. Filter to claimed suffix ∩ not-ignored. `CollectionCensus.skipped_untracked = len(that set)`. Stamp ints on `collection_census` meta; stamp the **sorted path tuple** on a **separate** meta key (`untracked_indexable`) because `GraphStore.collection_census()` int-casts every value (`store.py:437`).
2. **Publish.** Verbose `get_index_status.collection.skipped.untracked`. Standard `build_or_update_index` payload gets a `collection` sibling (same shape as verbose status) — **not** inside `wrote` (060). Minimal build omits it (061 cheap path). Pre-092 census: `.get("skipped_untracked", 0)`.
3. **Miss path.** `classify_missing_subject`: after zero indexed suffix-matches, match stored untracked stems to last ident of the type part (`split_qname` container or whole) **and** `PurePosixPath(hay).stem`. Status `"untracked"` + `untracked_paths`. Shared `shape_exact_miss` / `attach_untracked_not_indexed` used by all 5 emitters. `try_instead=build_or_update_index`, `try_instead_hint` prose, `untracked_path` (unique).
4. **073 first** (already). Non-git: untracked=0. `kept` unchanged — files stay unindexed.

### Rejected alternatives
- **Fold untracked into `collected`** — breaks `collected == git ls-files` (082). Rejected (A).
- **Index untracked files** — ticket forbids; separate blast radius. Rejected (C5).
- **Query-time tree walk / adapter parse of untracked files** — rival traversal + language knowledge. Rejected (R4, R1.1, ticket bound).
- **New `reason` value** — vocabulary already owns `not_indexed`; 069 pin tests + allow-sets. Rejected (C3).
- **Put git-add in `try_instead`** — 093 forbids identifier-shaped instructions. Rejected (D).

### Assumptions
- `git ls-files -o --exclude-standard` lists untracked not gitignored — **verified** (git man; same `-z` as `ls_files`).
- `collection_census()` int-cast forbids paths on that JSON — **verified** `store.py:437`.
- `dirty_paths` never includes untracked — **verified** `gitutil.py:76-78`.
- Fake adapter qname is `{path}::Thing` — **verified** `fake_adapter.py:75`. Proving test uses that qname so post-`git add` is an exact hit.
- Reusing `not_indexed` while `indexed: true` does not break unbuilt tests (`indexed: false`) — **verified** `empty_nav` / `test_nav_reason_codes.py:68`. Layer-matched by the proving test.
No novel-untested 3p/runtime assumption.

### HANDLES
`HANDLES: 0 recalled | 0 traced | 0 does not apply | 0 unanswered`

### Change-list (every item traces to a matrix row)
| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| 1 | `ls_untracked` (`ls-files -o -z --exclude-standard`), sorted | `code_atlas/gitutil.py` | `dirty_paths` docstring (already states untracked never appear); tests | R1,C2,C4 | 1/14 |
| 2 | `skipped_untracked` on `CollectionCensus`; `_collect_with_census` returns kept+census+paths; `_record_meta` stamps both keys | `code_atlas/indexer.py` | `collect()` still `[0]`; `full_build`/`incremental_update` unpack; 082 identity | R1,C4,C5,AC1 | 2/14 |
| 3 | `UNTRACKED_INDEXABLE_KEY` + `untracked_indexable_paths()`; add to `META_KEYS` | `code_atlas/store.py` | `test_store.py` parametrize `META_KEYS` (auto-covers); `collection_census()` stays ints | R1,R4,C2 | 3/14 |
| 4 | `skipped.untracked` on verbose collection; docstring | `code_atlas/tools/get_index_status.py` | 082 tests identity (must still close); pre-092 `.get` | R1,AC1,AC4 | 4/14 |
| 5 | `collection` sibling on standard build payload (reuse `_collection_field`); not inside `wrote`; omit on minimal | `code_atlas/tools/build_or_update_index.py` | 060 `wrote` keyset tests; `_REPORT_KEYS.isdisjoint` | R1,C3/060,AC1 | 5/14 |
| 6 | `SubjectResolution.untracked`; classify after indexed miss; `TRY_INSTEAD_BUILD`; `attach_untracked_not_indexed` + `shape_exact_miss` | `code_atlas/tools/nav_result.py` | 5 emitters; `NAV_REASONS` **unchanged** (069) | G2,R2,R3,R5,C1,C3 | 6/14 |
| 7 | Wire `shape_exact_miss` on exact miss | `find_callers.py` | inventory 1 | R2 | 7/14 |
| 8 | same | `find_references.py` | inventory 2 | R2 | 8/14 |
| 9 | same | `find_implementations.py` | inventory 3 | R2 | 9/14 |
| 10 | same | `find_view_data.py` | inventory 4 | R2 | 10/14 |
| 11 | `_resolve_miss` handles `untracked` | `read_symbol.py` | inventory 5 | R2 | 11/14 |
| 12 | Proving test + 082 identity with untracked present; post-add; nowhere; dirty=0 | `tests/test_untracked_files_are_invisible.py` | `test_files_reconciliation.py` (collateral: `skipped.untracked` key on all-committed tree) | AC1–AC4,G4 | 12/14 |
| 13 | 082 test asserts `skipped.untracked` present (0 when all committed) | `tests/test_files_reconciliation.py` | identity line unchanged | AC1 | 13/14 |
| 14 | PLAN / CONVENTION / BACKLOG / LESSONS / frontmatter | `docs/*` | token table | docs-before-PR | 14/14 |

**Mechanical blast-radius greps (producers/consumers):**
- `CollectionCensus` / `_collect_with_census` / `collection_census()` — only indexer construct + store int-cast + `_collection_field`.
- `NAV_REASONS` / `REASON_NOT_INDEXED` — **not adding a member**; unbuilt tests keep `indexed: false`.
- `asdict(census)` → JSON ints only.
- `classify_missing_subject` — 7 call sites; 5 emit `no_such_symbol`.
- 060 `_REPORT_KEYS.isdisjoint` — `collection` is extra top-level, not a report field.

### Rule compliance (design)
R1.1 stem/ident matching, no `if language`. R1.2 no new framework. R1.4 store KV, indexer collect, tools present. R3 no adapter bump. R4 sorted paths. 060/061/066 as above.

### Verification plan
| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 | integration (git + build + status) | integration test: untracked `.aa`, build, census | ✅ |
| AC2 | integration (lookup after build) | same test: `find_callers` payload pinned | ✅ |
| AC3 | integration (git add + rebuild) | same test: real answer + nowhere `no_such_symbol` | ✅ |
| AC4 | integration (status health vs census) | same test: `dirty_indexed_files==0` and `skipped.untracked>0` | ✅ |
| R2 per-item 2–5 | logic (shared `shape_exact_miss`) | unit: classifier status + one extra tool (`read_symbol`) on the same fixture | ✅ |

### Proving test
`tests/test_untracked_files_are_invisible.py::test_untracked_indexable_file_is_visible_not_absent`
Invocation: `pytest tests/test_untracked_files_are_invisible.py -q`
Fails pre-change (`skipped.untracked` missing / reason `no_such_symbol`); passes post-change.

### Rollback + porting
`git revert` the PR. One repo (`app`). No schema migration (additive meta).

### SCOPE reaffirm
`SCOPE: M` — unchanged; N=5 emitters is the inventory, not an L rewrite. Branch type `fix/` matches the defect.

## Phase 3 — Execute

Branch: `fix/092-untracked-files-are-invisible-and-answer-no-such-symbol`. Change-list 1–14 implemented. No deviation from Gate-2 approach.

**Proving test (empirical):**
```
.venv/bin/pytest tests/test_untracked_files_are_invisible.py tests/test_files_reconciliation.py … -q
33 passed in 3.82s
```

**Axis 1 — file set:** diff ⊆ change-list (gitutil, indexer, store, get_index_status, build_or_update_index, nav_result, 5 emitters, proving test, 082 collateral, docs). No stray imports.

**Axis 2 — design-conformance:** census beside 082 ✅; sibling meta for paths ✅; `shape_exact_miss` on all 5 emitters ✅; `try_instead` real tool + hint ✅; 073 still first ✅; `wrote` untouched ✅.

**Verification (empirical):**
```
scripts/docker-test.sh  →  ruff + mypy clean; 1162 passed in 54.18s
BASELINE was 1160 passed. Delta = +2: proving test + `META_KEYS` parametrize gained `untracked_indexable`.
```

Ph3/4 proven by: `test_untracked_indexable_file_is_visible_not_absent`.

## Phase 4 — Review

**WAIVED at solve time** (run arg `/solve 092 with skipped review`). No reviewer, no challenger, no `Reviewed at` marker at that point.

**Review done on the PR** (maintainer asked for it on #102; in-session, 0 dispatch). Three findings, all fixed on the branch:

| # | Finding | Fix |
|---|---------|-----|
| R1 | The 092 exact-miss shortcut in `find_callers` / `find_view_data` returns before the shared fall-through, silently dropping `subject_refreshed_only` (073) and `args_unrecorded` (049). Reachable: `ensure_miss()` repairs the sole dirty file, the symbol is gone, the answer no longer says it refreshed. | Attach both on the miss itself; regression test `test_repaired_miss_still_names_the_repair_and_the_unrecorded_args` |
| R2 | `_untracked_match_keys` fed a path-shaped qname's **trailing ident** into the key set — that ident is the file extension, so `src/Missing.aa::Thing` matched an untracked `src/aa.aa`. | Stem-only when the subject is path-shaped; test `test_untracked_match_is_the_stem_not_the_extension` |
| R3 | `build_or_update_index` imported the private `_collection_field` from the `get_index_status` **tool** module — the repo's only tool→tool import. | Moved to `code_atlas/tools/collection.py` (`reach_shared` precedent); CONVENTION now states the rule |

Also corrected: the "full gate 1162 / baseline 1160" recorded below was a stale count. Re-measured in Docker — `main` **1160**, branch pre-review **1165**, branch post-review **1167**.

Not changed (judged in scope of other tickets): `impact` / `explain_path` only consume `resolved_unique`, so the new `untracked` status is inert there; the untracked path list on `untracked_indexable` is uncapped, which is bounded in practice because `_indexable_untracked` applies the ignore matcher (`vendor/`, `node_modules/`).

## Phase 5 — Finalise

### Durable lesson
See `docs/LESSONS.md` §092. Split claims:

| ID | Claim | Type (proposal) | Destination (proposal) | seen: | Falsify |
|----|-------|-----------------|------------------------|-------|---------|
| C1 | A partition of `git ls-files` cannot name untracked files; sit the count beside it | 5 (this collect walk) / 2 handle `census-beside-walk` | LESSONS + PLAN §12 (descriptive) | 092 | still true (`ls_files` vs `ls_untracked`) |
| C2 | `collection_census()` int-casts every value — path lists need a sibling meta key | 5 | LESSONS | 092 | `store.py` still int-casts |
| C3 | Reuse `not_indexed` + `indexed: true` rather than a new reason | 5 (nav vocab) | LESSONS + CONVENTION §6 | 092 | `NAV_REASONS` unchanged; proving test |
| C4 | `try_instead` stays a real tool; prose in `try_instead_hint` | 2 handle `try-instead-tool-name` | LESSONS; 093 owns the audit | 092 | proving test pins both fields |

`CLAIMS: 4 split | 0 type-3 | 0 recurrence ≥2 keys`
No `/mango:promote` this run (`seen:` is one ticket). Type-2 handles not promoted (first occurrence). PLAN/CONVENTION updates are this ticket's descriptive ship, not a cross-ticket promotion.

**Falsification:** all four still true and cheaply greppable. None blocked.

**Coverage-gap exclusions:** none.
**Skill-gap:** none (`config.skill_gap_path` unset; no skipped doable check).

### Cost ledger
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker (challenger, ticket-blind) | 1 | unmeasured (blocking retrieval) |

| review (on PR #102) | none — in-session, no subagent | 1 | 0 dispatch |

Ledger complete: 1 dispatch → 1 row, plus one 0-dispatch in-session review round on the PR. `unmeasured (blocking retrieval)` is the honest host marker.

### Outward actions (standing approval: commit + push + PR)
1. Commit on `fix/092-…`
2. Push branch
3. `gh pr create` from `.github/pull_request_template.md`
