---
id: 070
slug: ambiguous-qname-no-scoping
title: 'One qname, five definitions, 23 callers merged — no way to ask about one of them'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [043, 013, 011]
---

## Goal
`\getActiveStatus` has **five** definitions in the anchor repo. `find_callers` merges all 23 call
sites under that one qname and offers no way to scope to a definition. The caller cannot ask "who
calls *this* one", and nothing in the payload warns that the question is ambiguous. On this index
**22,261 qnames have more than one definition** — this is the common case, not an edge case.

## Evidence (anchor repo, index built 2026-08-09, queried directly)
```
\getActiveStatus  Function  legacy/alpha/web/include/member_transaction.php:20
\getActiveStatus  Function  legacy/beta/web/ajax.php:3440
\getActiveStatus  Function  legacy/beta/web/include/member_transaction.php:18
\getActiveStatus  Function  src/Application/Common/MemberTab/tabs_common.php:332
\getActiveStatus  Function  src/Utilities/member_transaction_functions.php:117
```
- `find_callers("\getActiveStatus")` → `total_count: 23`, every site correct, **no partition**.
- Qnames with >1 definition in `nodes` (Function/Method/Class): **22,261**.
- Both `src/` definitions are wrapped in `if (!function_exists('getActiveStatus'))`, so which one a
  given call site binds to is **load-order dependent**. The round-3 session had to answer that by
  reading the `require_once` order by hand.
- `search_symbol` does report the definitions separately — the ambiguity is visible on the *search*
  side and invisible on the *navigation* side. The evaluator listed this under false positives:
  *"Each is correct individually, but the qname is not unique and `find_callers` offers no way to
  scope to one definition."*
- Note for the record: the retro says four definitions; the index holds five. The retro's list came
  from a `search_symbol` page, which is itself consistent with a paging cap.

This interacts with [067](067_first-page-not-representative.md): merged results from five definitions,
ordered lexically, capped at 10, means page 1 can be entirely one definition's callers with no
indication that four other definitions exist.

## Scope / Deliverables
- **Warn before scoping.** The cheapest useful change is a payload signal that the subject qname
  resolves to more than one definition, with their `file:line`s. Ship that first — it converts a
  silently wrong reading into a visibly ambiguous one, and it may be enough.
- **Then evaluate scoping.** A way to say "callers of the definition at `path:line`" — an optional
  `defined_in` argument, or accepting a `path:line` subject. Design it, cost it, and say whether the
  edges even carry enough information to answer it: the resolver links call sites to a **qname**, so
  per-definition attribution may not exist in the graph at all. If it does not, say so plainly —
  "cannot be answered with the current edge model" is a valid, useful outcome.
- **Do not invent a binding.** Where the language makes binding load-order dependent
  (`function_exists` guards, conditional definitions), the honest answer is *ambiguous*, never a
  guess. R4 forbids a heuristic that looks like a fact.
- **Check which tools inherit this.** `find_callers`, `find_references`, `impact`, `reachable_from`,
  `explain_path` and `read_symbol` all take a qname; each needs a stated verdict.
- **Relationship to 043.** [043](043_duplicate-decl-resilience.md) made duplicate declarations not
  break the index. This ticket is the next question: now that they survive, how does a caller ask
  about one of them?

## Constraints
- R2 — `function_exists`-guarded redefinition is a PHP language fact and belongs in the adapter's
  understanding, never a repo's name.
- R1.1 — the core sees "N nodes share this qname"; it must not reason about why.
- R4 — no probabilistic pick of a "most likely" definition.
- 061 — the ambiguity signal is conditional: absent when the qname is unique.

## Acceptance criteria
- A fixture with two same-qname definitions and callers of each produces a nav payload that states
  the subject is ambiguous and lists the definition sites.
- A unique qname's payload is byte-identical to today's.
- The scoping design decision is recorded either way, with the edge-model limitation stated if
  scoping cannot be answered.
- The 22,261-count style measurement is re-run on the fixture corpus so the fixture reflects a real
  distribution, not a hand-built pair.

## References
Field retro round 3 §3 (false positives table), §7 (the "which definition does this call site bind
to" question the session had to answer by reading). `code_atlas/store.py:113` (`_NODE_ORDER`),
`code_atlas/tools/find_callers.py`, `code_atlas/tools/search_symbol.py`.
Related: [043](043_duplicate-decl-resilience.md) (duplicate declarations survive indexing),
[046](046_resolver-qname-candidate-dedupe.md) (candidate dedupe),
[067](067_first-page-not-representative.md) (why merged results hide behind page 1),
[011](011_resolver.md) (what an edge's target actually identifies).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 070

## Session status
- **Phase:** 1 analysis — complete; **STOPPED at Gate 1**, awaiting approval.
- **work_doc_mode:** embed (appended below the separator in this ticket file).
- **Branch (planned):** `feat/070-ambiguous-qname-no-scoping` (not yet created).
- **Next action:** on Gate-1 approval → design (Gate 2).
- **STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full.

## Phase 1 — analysis

### Decompose
`SECTIONS: 6 found (Goal, Evidence, Scope/Deliverables, Constraints, Acceptance criteria, References) | 6 decomposed | ROWS: G=1 R=5 C=4 AC=4 (+2 context: Evidence, References)`

### Requirements matrix
| ID | Source | Verbatim (compressed) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | `\getActiveStatus` has 5 defs; `find_callers` merges 23 callers, no scope, no warning; 22,261 qnames >1 def — the common case | Add a warning signal now; evaluate scoping and state a verdict | `find_callers.py` merges all edges by `target_qname` (no partition) | ✅ |
| R1 | Scope | Warn before scoping — payload signal that subject resolves to >1 def, with `file:line`s; ship first | Conditional key listing def sites | tools already fetch `nodes_by_qualified_name(qname, limit=1)` for the `indexed` check → widen it | ✅ |
| R2 | Scope | Then evaluate scoping (`defined_in`/`path:line` subject); say if edges carry enough info; "cannot be answered" is valid | Record the decision; edge model is the deciding fact | `resolver.py:65-78`, `_distinct_qnames` (126-132): edges store only `target_qname`; N defs collapse to one edge — "an edge cannot record a file" (046) | ✅ |
| R3 | Scope | Do not invent a binding — `function_exists`/load-order ⇒ answer is *ambiguous*, never a guess (R4) | Signal lists sites, picks none | AC-driven; no heuristic pick | ✅ |
| R4 | Scope | Check which tools inherit; each a stated verdict | Per-tool checklist (N=6) — see inventory | reads of all 6 tools done | ✅ |
| R5 | Scope | Relationship to 043 — now dup decls survive, how does a caller ask about one? | Framing; this ticket answers "warn; scoping unanswerable" | 043 = store keep-first dedupe (`store.py:1724-1745`) | ✅ |
| C1 | Constraint | R2 — `function_exists` redefinition is a PHP language fact → adapter, never a repo name | Core-only change; no adapter, no repo name | change touches `code_atlas/tools/` + tests only | ✅ |
| C2 | Constraint | R1.1 — core sees "N nodes share this qname"; must not reason about why | Signal is pure count/list of sites | no `if language ==`; no reason-about-why | ✅ |
| C3 | Constraint | R4 — no probabilistic pick of "most likely" def | List all sites; pick none | `read_symbol` still shows first-in-`_NODE_ORDER` but now flags ambiguity so it's not presented as "the" def | ✅ |
| C4 | Constraint | 061 — signal conditional; absent when unique | Attach only when >1 (= AC2) | 061 conditional-attach precedent (`attach_result_subtrees`) | ✅ |
| AC1 | AC | Fixture: two same-qname defs + callers of each → payload states ambiguous + lists def sites | Proving test (fixture build) | falsifiable: key present, ≥2 sites | ✅ |
| AC2 | AC | Unique qname payload byte-identical to today's | Conditional omission | falsifiable: key absent / payload eq | ✅ |
| AC3 | AC | Scoping design decision recorded either way, edge-model limit stated if unanswerable | Doc deliverable (task + PLAN §) | verified by inspection (doc section) | ⚠ manual-check (doc) |
| AC4 | AC | 22,261-style measurement re-run on fixture corpus (real distribution, not hand-built pair) | Measurement test over built fixture | falsifiable: count qnames >1 def ≥ N | ✅ |

### AC validation (re-derived values)
- "5 defs / 23 callers / 22,261 qnames >1 def" are **anchor-repo evidence figures, not thresholds this change must hit.** AC4 asks to re-run the *measurement style* on the *fixture* corpus, so the assertion is the fixture's own multiplicity (≥2 distinct ambiguous qnames, one with ≥3 defs) — a real distribution, not a single hand-built pair. Falsifiable ✅.
- AC1/AC2/AC4 falsifiable (key present+sites / key absent / measured count). AC3 is a **documentation** deliverable → recorded as a manual-check exclusion (verified by the doc section existing), not an automated test. Logged in Coverage-gap exclusions.

### Clarification
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
- Is scoping answerable? → **No**, per the edge model (`resolver.py:65-78`; `_distinct_qnames` 126-132). Self-resolved.
- Which tools get the *code* signal? → the 3 single-subject-qname tools (`find_callers`, `find_references`, `read_symbol`); the rest get a documented verdict. Self-resolved (design choice under the run's "do the best option" latitude — surfaced at Gate 2).
- Cap for the listed def sites? → reuse `DEFAULT_MAX_RESULTS = 50` (`config.py:44`); no new knob. Self-resolved.

`j = 0` → no Gate 0.

### Universal inventory — "which tools inherit" (N=6, per-item checklist)
| # | Tool | Takes single qname subject? | Inherits the merge? | Verdict |
|---|---|---|---|---|
| 1 | `find_callers` | yes | yes (merges callers of all defs) | **code signal** |
| 2 | `find_references` | yes | yes (merges refs of all defs) | **code signal** |
| 3 | `read_symbol` | yes | yes (silently returns first def) | **code signal** |
| 4 | `impact` | no (`qnames[]` seed set) | partially (seed merges) | **documented verdict** — inherits; multi-subject payload, defer to follow-up unless the warning proves insufficient |
| 5 | `explain_path` | no (from/to pair) | yes (endpoints merged) | **documented verdict** — inherits; defer as above |
| 6 | `reachable_from` | no (entry points, no qname subject) | no | **N/A** |
| + | `search_symbol` | (search side) | already lists defs as separate rows | **already-handled** (ticket §Evidence) |

### Cause / gap analysis (enhancement)
Gap: nav tools keyed on a single qname merge N definitions' edges (or pick the first) with no signal that the qname is non-unique. Current → target: add a conditional payload key listing the definition sites when >1 exists. Root touch points: `code_atlas/tools/{find_callers,find_references,read_symbol}.py`, shared shaping in `code_atlas/tools/nav_result.py`.

### Blast radius
Handlers: the 3 tools above. Shared helper: `nav_result.py` (existing module — **no new core module**, `core_modules()` stays 37). No store/schema/contract change (nav-payload key, not contract vocabulary). Repos touched: `app` (only). No adapter change (C1).

### Baseline
`BASELINE: green (Docker) — ~1056 passed on main@b78f9a2 (072 merged). Bare Windows pytest RED by the known fcntl platform exclusion (AGENTS.md) — Docker is authoritative.` Delta-green to be proven in Docker at execute/review.

### Declarations
`STRUCTURE: native` · `TRACK: backend — 0/… files under UI paths` · `SCOPE: M` · `TIER: full`

### Coverage-gap exclusions
- **AC3** (scoping design decision) — documentation deliverable, unmeasurable by test; verified by inspection of the recorded decision in this task doc + `PLAN.md`. Human-approved manual check.

### Cost ledger
| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| analysis | Explore: store qname methods + fixture map | 1 | 78,481 |

## Phase 2 — design (Gate 2)

### Approach
Two halves, per the ticket.

**(A) Warn — the shippable.** Add a conditional nav-payload key `ambiguous_definitions`: a list of
`{file, line, kind}` for every definition node sharing the subject qname, present **iff** the count
is >1 (061 conditional → AC2). Computed by widening the `nodes_by_qualified_name(qname, limit=1)`
call the three single-subject tools already make for their `indexed` check to `limit=max_results`
(50) — **zero new queries, no new store method**. Deterministic via `_NODE_ORDER` (R4). Shared
shaping lives in `nav_result.py` (existing module → `core_modules()` stays 37): `definition_sites()`
+ `attach_ambiguous_definitions()`, mirroring `attach_result_subtrees` (061/067).

**(B) Scope — the verdict.** "Callers of the definition at `path:line`" **cannot be answered with the
current edge model.** Edges store only `target_qname` (`resolver.py:65-78`); when N nodes share a
qname the resolver collapses them to one edge, explicitly *not* one per file, because "an edge cannot
record a file" (046, `_distinct_qnames`). Answering scoping would need edges to carry a resolved
*definition node id* — impossible for load-order-dependent `function_exists` bindings without
inventing a binding (R4). Recorded here + in `PLAN.md`; no code. This is the ticket-sanctioned
"cannot be answered" outcome (AC3).

### Rejected alternatives
1. **`defined_in` / `path:line` scoping argument** — rejected: not answerable with the current edge
   model (above); would force an R4-violating invented binding.
2. **A `reason=ambiguous_subject` nav reason** — rejected: ambiguity is orthogonal to `reason` (a
   payload can be `reason=ok` **and** ambiguous). A separate conditional key composes; a reason value
   would force a false either/or.
3. **New `count_nodes_by_qualified_name` + truncation marker** — rejected (YAGNI/R1.2): tools already
   fetch nodes-by-qname; observed max multiplicity is 5, a 50-cap never truncates in practice.
4. **Signal on all 6 tools now (incl. `impact`/`explain_path`)** — rejected for now: multi-subject
   payloads differ in shape; "ship the cheapest useful thing first, it may be enough" (ticket).
   Documented verdict + follow-up if the warning proves insufficient.

### Assumptions
- `nodes_by_qualified_name` returns one row per definition site (file/line/kind) — **verified**
  (`store.py:459-477`).
- `_NODE_ORDER` makes the list deterministic — **verified** (`store.py:113`).
- **The PHP adapter emits N distinct nodes for N `function_exists`-guarded same-qname definitions
  across files** — **novel-untested (runtime/3p)**. De-risked by shaping AC1/AC4 as **integration
  proofs over a real `full_build`** that assert node-multiplicity >1 for the fixture qname — they
  **fail if the assumption is false**. (Strongly supported by 043, whose point was that duplicate
  declarations *survive* indexing — but proven here, not assumed.)

### Smallest change list
| Change | File/area | Ph2 covered by | k/N |
|---|---|---|---|
| `AMBIGUOUS_DEFINITIONS` key + `definition_sites()` + `attach_ambiguous_definitions()` | `code_atlas/tools/nav_result.py` | R1, C4 | 1/13 |
| Widen subject fetch → `max_results`; attach signal | `code_atlas/tools/find_callers.py` | R1, R4·1, C2, C3 | 2/13 |
| Same | `code_atlas/tools/find_references.py` | R1, R4·2 | 3/13 |
| Same, attach on the `found=True` path | `code_atlas/tools/read_symbol.py` | R1, R4·3, C3 | 4/13 |
| New PHP fixture: ≥2 qnames redefined across files (one `function_exists`-guarded, ≥3 defs) + callers of each | `tests/fixtures/php/ambiguous/*.php` | AC1, AC4 | 5/13 |
| Proving test (fixture, `@needs_php`) | `tests/test_ambiguous_qname.py` | AC1, proving | 6/13 |
| Measurement test (fixture, `@needs_php`) — qnames with >1 def ≥ N | `tests/test_ambiguous_qname.py` | AC4 | 7/13 |
| Unit: unique qname byte-identical (key absent) | `tests/test_ambiguous_qname.py` | AC2 | 8/13 |
| Unit: `find_references` + `read_symbol` signal (in-memory) | `tests/test_ambiguous_qname.py` | R4·2, R4·3 | 9/13 |
| **Proof collateral** — grep existing tests for a multi-def single-qname seed asserting payload shape on the 3 tools; fold any hit in | `tests/*` | AC2 | 10/13 |
| Document scoping verdict + per-tool verdicts + the new key | this doc, `docs/PLAN.md` §12 + §19 | R2, R3, R4·4–6, AC3 | 11/13 |
| BACKLOG status + token row | `docs/BACKLOG.md` | bookkeeping | 12/13 |
| Durable lesson (if any) | `docs/LESSONS.md` | bookkeeping | 13/13 |

### Rule compliance
- **R1.1** — signal is pure "N nodes share this qname" (count/list); no `if language ==`, no
  reasoning about *why* (C2). **R1.2/R7.4** — reuses existing fetch + existing conditional-attach
  pattern; no new store method, no new module, no dead seam. **R1.4** — store owns SQL; tools shape.
  **R4** — deterministic list, picks no "winner" (C3). **R5.3** — no new failure mode; key simply
  omitted when unique. **R7.5** — comments ≤3 lines.

### Verification plan (per-AC, layer-matched)
| AC | risk layer | proof artifact | layer-match |
|---|---|---|---|
| AC1 (fixture ambiguous → signal + sites) | integration (adapter+store+tool) | `@needs_php` fixture-build test | ✅ |
| AC2 (unique byte-identical) | integration (payload over real SQLite) | in-memory seeded unit test (key absent) | ✅ |
| AC3 (scoping decision recorded) | documentation | manual-check exclusion (doc inspection) | ✅ (recorded exclusion) |
| AC4 (measurement on built fixture) | integration | `@needs_php` measurement test | ✅ |
| R4·2/·3 (find_references, read_symbol signal) | integration (payload) | in-memory seeded unit tests | ✅ |

No ❌. AC3's non-automatable row is the single recorded, human-approved coverage-gap exclusion.

### Proving test
`tests/test_ambiguous_qname.py::test_find_callers_flags_ambiguous_subject_with_definition_sites`
(`@needs_php`, fixture build): asserts `ambiguous_definitions` present with ≥2 `{file,line,kind}`
sites while callers stay merged. Fails pre-change (key absent), passes post.
Invocation: `scripts/docker-test.sh pytest -q -k ambiguous`.

### Rollback + porting
Revert branch / close PR; no schema/data/contract change → no migration. Single repo (`app`); no
shared-code porting.

### SCOPE
`SCOPE: M` — unchanged; no tier crossing, no branch/PR-type drift (`feat`).

## Phase 3 — execute

Branch `feat/070-ambiguous-qname-no-scoping`. Implemented the approved change list.

- `nav_result.py`: `AMBIGUOUS_DEFINITIONS` key + `definition_sites()` + `attach_ambiguous_definitions()`.
- `find_callers.py` / `find_references.py`: widened the existing `nodes_by_qualified_name(qname,
  limit=1)` indexed-check fetch to `limit=config.max_results`; attach the signal after the payload.
- `read_symbol.py`: widened all three qname fetches; attach on the `found=True` path (source shown is
  one of N; the rest are named).
- Fixture `tests/fixtures/php/ambiguous/{alpha,beta,common,util}.php`: `\getActiveStatus` in 3 files (one
  `function_exists`-guarded), `\formatDate` in 2, `\uniqueHelper` unique; callers of each.
- `tests/test_ambiguous_qname.py`: 6 tests (proving + measurement `@needs_php`; 4 in-memory payload).

### Verification sweep
- **Axis 1 (file set):** diff ⊆ approved change list (the 3 tools + `nav_result.py` + the fixture dir +
  the new test + docs/bookkeeping); add-only, no untouched-line reformatting; imports all used
  (mypy clean); every hunk maps to a matrix row. ✅
- **Axis 2 (design conformance):** both Gate-2 approach bullets `implemented-as-approved`. `read_symbol`
  still shows the first-in-`_NODE_ORDER` definition (deterministic) but now flags the rest — not a pick
  (C3). No `deviated` bullet.

### Deviations (benign, self-adjudicated — review waived)
- **R3.2 sole-source gate:** `definition_sites` was first written as a dict *literal*
  `{"file":…, "line":…, "kind":…}`; the `test_contract_sole_source` gate forbids a collection literal
  carrying contract vocabulary (`line`/`kind`). Rebuilt one-key-per-statement, matching the existing
  `edge_hit`/`_shape_hop` pattern — **same behaviour**, not a design change.
- Three ruff `E501` line-length fixes (two docstrings, one assert comment) — cosmetic.

### Result (Docker — authoritative; bare Windows `pytest` red by the fcntl exclusion)
`scripts/docker-test.sh` → **1063 passed** (baseline 1056 + 7 new), ruff clean, mypy clean.
Proving test `test_find_callers_flags_ambiguous_subject_with_definition_sites` passes; its
`ambiguous_definitions` key is net-new, so it necessarily failed pre-change. The novel-untested
assumption (adapter emits N nodes for `function_exists` redefinitions) held — the `@needs_php`
measurement passed. One transient `test_profile_incremental` wall-clock flake under concurrent
load; passed in isolation and on clean `main` → baseline exclusion (durable lesson 070).

## Phase 4 — review
**Waived** by the run instruction (`with skipped review`). No `Reviewed at` marker; the stale-review
guard is not applicable (nothing to compare against). Execute's two-axis sweep + the two self-adjudicated
benign deviations stand as the in-conversation surface.

## Phase 5 — finalise
- **Docs before PR:** `PLAN.md` §12 (three tool rows + ambiguity/scoping note), `BACKLOG.md` (070 →
  done + token row), task frontmatter → done, `LESSONS.md` (070). AC3 scoping verdict recorded in
  PLAN §12 + this doc's design.
- **Coverage-gap exclusions:** AC3 (documentation deliverable) — satisfied by the recorded verdict.
- **Durable lesson:** LESSONS 070 (load-sensitive timing test → isolate before calling it a regression).
- **Revert path:** close the PR + delete `feat/070-ambiguous-qname-no-scoping`; no schema/data/contract
  change → no migration.

### Cost ledger (final)
| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| analysis | Explore: store qname methods + fixture map | 1 | 78,481 |

`LEDGER TOTAL: 78,481 · top cost driver: analysis/Explore fan-out.` 1 dispatch → 1 row (complete). It
landed as a `task-notification`, so its usage block was carried (no `unmeasured` marker needed).
Main-loop spend is **not measured by mango** (dispatch-only); see `rtk gain` for the output-noise side.

## Session status
- **Phase:** finalise — **complete (PR #91).** Delta-green (Docker 1063 passed), pushed.
- **Next action:** maintainer review on [PR #91](https://github.com/cuongdinhngo/code-atlas/pull/91).
- **Revert:** close PR #91, delete branch `feat/070-ambiguous-qname-no-scoping`.
