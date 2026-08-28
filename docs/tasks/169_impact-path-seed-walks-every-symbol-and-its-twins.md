---
id: 169
slug: impact-path-seed-walks-every-symbol-and-its-twins
title: 'An `impact` path seed expands to every symbol in the file and reports 29× the qname seed — 161 gave the qname seed a refusal and left the path seed walking twins'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [161, 017, 078, 165]
---

## Why this exists (field retro rounds 10 & 11)

Round 10's §15 ranked this ticket 6 of 6 and it did not ship. Round 11 fired it deliberately (R-18) and
it is the round's largest measured over-report:

```
impact(paths=["src/Application/Alpha/Plan/Plan.php"])
  →  176 nodes, spanning legacy/alpha, legacy/beta, src/compat, src/Application/Beta
     and legacy/alpha/web/saml/tests/…/SystemTest::testWriteFileMode,
     HEURISTIC 0.7, seeds_dropped: 1, ≈26 KB

impact(qnames=["Src\Application\Alpha\Plan\Plan::createPlan"])
  →  6 nodes, all RESOLVED, correct
```

> Round 11 §12.e(g′): *"**A 29× over-report.** Would it have hurt me? **YES — decisively.**
> **HOLD, and 10-G is confirmed a live loaded gun.** Narrow the wording: the *qname* half was fixed by
> 161; it is the **path seed** that walks the twin."*
> §14 (7-E): *"`impact` on a **non-core** file via path seed returned ≈26 KB — deliverable but 4.3× the
> next largest payload. **The inflation is the path seed, not the file's coreness.**"*
> §9.b: the evaluator declined the best-fit tool for a real blast-radius question and used
> `find_callers` instead — *"the veto I would have most wanted to break turned out to be protecting me
> from a 29× over-report."*

161 closed 9-A for a **shared qname**. The consuming repo's actual shape is a **shared trailing name
under different qnames**, which is why 165 had to exist for `find_callers` — and `impact`'s path seed
walks straight into it, at tier `RESOLVED`-looking confidence, on the one tool whose answer is acted on
destructively.

## Root cause

- `code_atlas/tools/impact.py:221-225` — when a path **does** hold indexed nodes, the branch appends
  every row's `qualified_name` **directly**, bypassing the local `take()` / `_resolve_seed` the qname
  branch uses at `:213`. Only the *empty* path is classified (`classify_missing_subject`, `:219`). So a
  path-derived seed is never classified, never counted as a resolution and never explained: one file
  becomes N seeds silently (the subject file here holds 102 symbols).
- `code_atlas/tools/impact.py:158` — `_split_ambiguous` asks
  `store.nodes_by_qualified_name(qname, …)` and treats `len(rows) > 1` as ambiguous. That detects a
  **duplicate of the exact qname**. A twin whose qname differs but whose trailing name is the same is
  invisible to it, so every path-derived seed is classified *walkable*.
- `code_atlas/tools/impact.py:100-101` — the walk then runs `store.impact_radius(walk_seeds, …)` over
  qname-keyed edges, and the bare-name HEURISTIC links pull in the twin's callers and callees. The
  payload's `seeds_dropped` counts nothing about this, because nothing was dropped.
- No field states **how many seeds one path expanded to**, so a reader cannot tell a 6-node answer
  about one symbol from a 176-node answer about 102 of them.

## Scope

Bring the path seed to parity with the qname seed 161 already fixed.

1. A path-derived seed goes through the **same classification** as a qname seed, so it can be disclosed,
   dropped or refused rather than silently walked.
2. A seed whose **trailing name** has a definition under another qname is disclosed — the 165 shape —
   or refused, whichever design records as the honest endpoint for a destructive answer.
3. The payload states the **seed expansion**: how many seeds the request's paths produced.

### Explicitly not in scope

- Changing the edge model. Edges are qname-keyed with no target node id; 161's AC1 deviation records
  that as architecturally settled, and this ticket must not reopen it.
- Dropping or re-tiering HEURISTIC rows. The tier is honest; the seed set is not.
- `impact_modules` — a follow-up if the seed fix does not inherit through the shared helper (140).

## Constraints

- **061** — a path seed on a file whose symbols have no same-named twins is byte-identical to today.
- **Cost** — `impact` is low-frequency and high-stakes; one bounded query per seed is acceptable, a
  query per walked node is not. Measure and record.
- **102** — a subject that produced no seed must still be distinguishable from a modelled zero.
- **R1.1** no language branch · **R3** no bump · **R4.2** order-stable seeds and sites.

## Acceptance criteria

1. A path seed over a fixture file whose symbols have same-named twins in another subtree either
   discloses the twins or refuses, and **never** returns a confident walk of one — pinned by a test
   that fails on today's code.
2. Every path-derived seed is classified by the same code path as a qname seed; a path subject that
   resolves to nothing is still counted and explained (102 unchanged).
3. The payload names the seed expansion (`seeds` / the design's recorded field) for a path request.
4. A path seed with no twinned symbols is byte-identical to today (061).
5. Cost measured; no per-node query added.
6. Determinism (R4.2), no language branch (R1.1), no bump (R3), and `impact_modules`' inheritance of
   the fix confirmed or filed.

## References

Field retro round 10 §15 ticket 6 (**not shipped**); round 11 §12.e(g′) (the 176-vs-6 measurement),
§9.b (the veto that paid off), §14 rows 10-G and 7-E (**the inflation is the path seed**), §14.a
carve-out (g′) rewording. `code_atlas/tools/impact.py:100-101,158,213,219,221-225`. Related:
[161](161_impact-resolves-a-shared-qname-to-one-twin-and-carries-no-freshness.md) (the qname half),
[165](165_find-callers-splits-across-twins-and-says-reason-ok.md) (the trailing-name shape),
[017](017_impact-engine.md),
[078](078_ambiguous-payload-still-picks-one-definition.md).

## Session status

- **KEY:** 169 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, 8-ticket batch — the last of them) · envelope in `.mango/run-contract-169.txt`.
- **Branch:** `feat/169-impact-path-seed-classification`
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2216 passed, 0 failed` at `2f39c25` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

Scope 2 leaves the endpoint open — *"disclosed — the 165 shape — **or** refused, whichever design
records as the honest endpoint for a destructive answer"*. A **how-decision**: `_split_ambiguous`
already answers the sibling question one qname over, inside this same function, so R1.8 settles it.
Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 2 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=4 R=3 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 10 applicable — 9 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R1.8 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.4 (change-type) ✅ · §R5.6 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type) ✅ · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ · §R7.2 (change-type) ✅`
`BASELINE: green — 2216 passed, 0 failed, 0 skipped at 2f39c25 (bare pytest, Linux host)`

**Premise:** `impact.py:221-225` (path rows appended raw, bypassing `take()`/`_resolve_seed`),
`:158` (`_split_ambiguous` keyed on exact-qname duplicates), `:100-101` (the walk over qname-keyed
edges) and the absence of any seed-expansion field all resolve exactly as described.

**Recall:** `161` (by symbol: the qname half, and its AC1 deviation settling that the binding is not
resolvable). `168`/`165` (by symbol: `sibling_definition_rows` — the trailing-name query, which
landed earlier tonight and is exactly what Scope 2 needs). `derived-not-listed-invariant` (R6.7, by
handle — the twin query must be the one 168 defined, not a third copy; traced below).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | a path seed expands to every symbol and reports 29× the qname seed | classify, disclose, and state the expansion | round 11 §12.e(g′) | open |
| R1 | Scope 1 | a path-derived seed goes through the same classification as a qname seed | route through `take()`/`_resolve_seed` | `impact.py:221-225` | open |
| R2 | Scope 2 | a seed whose trailing name is defined elsewhere is disclosed **or refused** | design picks; R1.8 says refuse | `impact.py:158` | open |
| R3 | Scope 3 | the payload states the seed expansion | a field on path requests | — | open |
| AC1 | AC 1 | twinned path seed discloses or refuses, never a confident walk of one — fails today | Falsifiable: red→green | proving test | open |
| AC2 | AC 2 | every path seed classified by the same code path; a path resolving to nothing still counted (102) | Falsifiable: `seeds_dropped` on a missing path | proving test | open |
| AC3 | AC 3 | the payload names the seed expansion | Falsifiable: field asserted | proving test | open |
| AC4 | AC 4 | a path seed with no twins is byte-identical (061) | Falsifiable: no new key, same rows | proving test | open |
| AC5 | AC 5 | cost measured; no per-node query added | Falsifiable: 40-seed path timed | proving test | open |
| AC6 | AC 6 | R4.2/R1.1/R3, and `impact_modules`' inheritance **confirmed or filed** | Falsifiable: verdict + a filed ticket | test + ticket 179 | open |
| C1 | Constraint | 061 — a path seed with no twinned symbols is byte-identical | omit every new key | — | binding |
| C2 | Constraint | Cost — one bounded query **per seed** acceptable; per walked node is not; measure | one `nodes_by_name` per seed | — | binding |
| C3 | Constraint | 102 — a subject that produced no seed stays distinguishable from a modelled zero | keep the `classify_missing_subject` arm | `impact.py:219` | binding |
| C4 | Constraint | R1.1 no language branch · R3 no bump · R4.2 order-stable | — | — | binding |

### Root cause (taxonomy: logic / seed planning)

Three silences stacked. The path branch never classified, so one file became N seeds with no record;
the ambiguity check asked the wrong question (exact qname, not trailing name), so every one of those
seeds looked walkable; and no field stated the expansion, so the inflated answer was indistinguishable
in shape from a correct small one.

### Blast radius

- `impact.py`: `resolve_seeds` gains a third return member; one new split function; the payload gains
  two conditional keys. `_split_ambiguous` and the qname path are untouched (161 preserved).
- `nav_result.py`: one hint constant.
- `impact_modules.py` shares `resolve_seeds`, so it inherits the classification half — see AC6.

## Phase 2 — design

### Approach

- **Classification.** The path branch calls `take(_resolve_seed(store, qname, max_results))`, the
  same gate the qname branch uses. `SeedSet` gains `from_paths` — the seeds a path expanded into —
  so the twin check can be aimed at exactly the seeds nobody asked for by name.
- **The twin split.** `_split_twinned` reuses **168's** `sibling_definition_rows`: same trailing
  name, same kind, other qname. A twinned seed is **disclosed and dropped from the walk**.
- **The expansion.** `seed_expansion: {"paths": n, "seeds": m}` on path requests only.
- **A route home.** When nothing is left walkable, `reason: subject_ambiguous` plus
  `try_instead: file_outline` and a hint naming the qname re-ask — the half 161 already made safe.

### Rejected alternatives

- **Disclose but still walk** (the softer reading of Scope 2). Rejected on R1.8 and on stakes:
  `_split_ambiguous` sits eight lines away and answers the sibling question by *not walking*, and
  `impact` is the one tool whose answer is acted on destructively. Marking a 29× walk
  `authoritative: false` leaves the 26 KB and the four wrong subtrees in the payload; the tier was
  never the problem, the seed set was. The ticket's own words: *"the tier is honest; the seed set is
  not."*
- **Apply the twin check to qname seeds too.** Rejected — out of scope and wrong: a caller who names
  `\East\Plan::createPlan` asked for that symbol. 161 settled the qname half, and round 11's
  rewording is explicit that *"it is the path seed that walks the twin"*.
- **Drop or re-tier the HEURISTIC rows** that pull the twin's neighbours in. Explicitly out of scope,
  and the tier is honest.
- **Refuse the whole call when any seed is twinned.** Rejected: a file with one twinned symbol and
  ninety clean ones still has a useful blast radius. Per-seed is the right granularity.
- **A third copy of the trailing-name query.** Rejected by R6.7 — 168 defined it; this is its third
  consumer.

### Assumptions

| Assumption | Tag |
|---|---|
| `_resolve_seed` short-circuits on an exact hit, so classifying a known-present row is one `limit=1` query | verified (`impact.py`, the docstring and the early return) |
| 168's `sibling_definition_rows` is importable and keyed on the subject's own kind | verified — merged as #208 earlier in this batch |
| Dropping twinned seeds cannot strand the qname seeds in the same call | **initially false, and caught by an existing test** — see *Empirical outputs* |
| `impact_modules` shares `resolve_seeds` | verified (`impact_modules.py:127`) — hence AC6's split verdict |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `SeedSet.from_paths`; path branch routed through `take()`/`_resolve_seed` | `code_atlas/tools/impact.py` | `impact_modules` inherits this half | R1, AC2 | 1/1 |
| `_split_twinned` reusing 168's query; twinned seeds disclosed + dropped | `code_atlas/tools/impact.py` | path-derived seeds only | R2, AC1 | 1/1 |
| `seed_expansion`; `try_instead` on a total refusal | `code_atlas/tools/impact.py` | path requests only | R3, AC3 | 1/1 |
| `TRY_INSTEAD_HINT_IMPACT_BY_QNAME` | `code_atlas/tools/nav_result.py` | one constant | R2 | 1/1 |
| Proving tests (8) | `tests/test_impact_path_seed.py` (new) | new file | AC1–AC6 | 1/1 |
| Follow-up ticket for the uninherited half | `docs/tasks/179_*.md` + BACKLOG | AC6 | AC6 | 1/1 |
| README; BACKLOG; ledger; working doc | `README.md`, `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `derived-not-listed-invariant` (R6.7) — **traced.** The trailing-name query has one definition site
  and three consumers; this ticket added the third rather than a third copy:

  ```
  $ grep -rln 'def sibling_definition_rows' code_atlas/     # Ran at efb7703e1e3c0050256ce379a0ceb125cc32f94c
  code_atlas/tools/nav_result.py
  $ grep -rln 'sibling_definition_rows(' code_atlas/tools/ | sort
  code_atlas/tools/find_callers.py
  code_atlas/tools/find_references.py
  code_atlas/tools/impact.py
  ```

### AC6 verdict — `impact_modules` inherits HALF, and the other half is FILED

| | `impact` | `impact_modules` |
|---|---|---|
| path seed classified through `_resolve_seed` (this ticket) | yes | **yes** — shared `resolve_seeds` |
| a lost subject counted in `seeds_dropped` (102) | yes | **yes** — same helper |
| shared-**qname** seed disclosed, not walked (161) | yes | **no** — never called `_split_ambiguous` |
| shared-**trailing-name** seed refused (this ticket) | yes | **no** — `_split_twinned` is not shared |

The missing half **predates this change** — `impact_modules` never had 161's split either — so it is
not a regression introduced here. Filed as
[179](179_impact-modules-inherits-half-the-seed-fix.md), and pinned by a test that will fail when
179 lands, with a comment saying so.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (a planted twinned file, a real walk) | integration test | ✅ |
| AC2 | integration (a path that resolves to nothing) | integration test | ✅ |
| AC3 | integration (the field asserted; absent on a qname request) | integration test ×2 | ✅ |
| AC4 | integration (an untwinned file still walks, no new keys) | integration test | ✅ |
| AC5 | measurement (a 40-symbol path, timed) | integration test | ✅ |
| AC6 | analysis (verdict) + integration (pinned) + a filed ticket | test + `docs/tasks/179` | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`tests/test_impact_path_seed.py::test_a_twinned_path_seed_is_never_a_confident_walk_of_one`.

### Rollback + porting

Rollback: revert `impact.py`, the one `nav_result` constant and the test file; 179 stays filed
either way. Porting: `app` only.

### SCOPE

`SCOPE: M` — one seed gate, one split, two payload keys; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Path branch through `take()`/`_resolve_seed`; `SeedSet.from_paths` | implemented-as-approved |
| `_split_twinned` reusing 168's query (R6.7, third consumer) | implemented-as-approved |
| Twinned path seeds disclosed **and** dropped from the walk | implemented-as-approved |
| `seed_expansion` on path requests only | implemented-as-approved |
| `try_instead: file_outline` + the qname hint on a total refusal | implemented-as-approved |
| Qname seeds untouched (161 preserved) | implemented-as-approved |

No deviations. Diff ⊆ approved list.

### Empirical outputs

**The over-report, measured pre- and post-fix on one fixture** — a 10-symbol file, every symbol
twinned in another subtree, each twin with five callers, plus one honest caller of the subject:

```
$ .venv/bin/python  (pre-169 impact.py restored from HEAD)  # Ran at 2f39c253bfad98c2ba536d72cc3ab6d55a9ee7df
  path seed  -> 11 nodes, reason: None, seeds_dropped: 0, seed_expansion: False, authoritative: False
  qname seed -> 2 nodes
  over-report: 6x

$ .venv/bin/python  (this branch, same fixture)             # Ran at efb7703e1e3c0050256ce379a0ceb125cc32f94c
  path seed  -> 0 nodes, reason: subject_ambiguous, seeds_dropped: 10,
                seed_expansion: {'paths': 1, 'seeds': 10}, sibling sites: 10
```

`reason: None` is the shape the field episode called `ok`: a 6× inflation with nothing in the
payload to notice it by. The fixture's ratio is smaller than the field's 29× only because it has ten
symbols rather than 102 — the mechanism is the one measured.

**Red run** — the twin split disabled:

```
$ .venv/bin/pytest -q tests/test_impact_path_seed.py        # Ran at 2f39c253bfad98c2ba536d72cc3ab6d55a9ee7df
E       KeyError: 'authoritative'
FAILED ::test_a_twinned_path_seed_is_never_a_confident_walk_of_one
1 failed, 6 passed
```

**A bug this change caused, caught by an existing test rather than by me.** The first implementation
partitioned `walk_seeds` into the path-derived subset, split *that*, and rebuilt the list from the
split's output — silently dropping every **qname**-derived seed in a mixed `paths=[…], qnames=[…]`
call. `test_impact.py::test_paths_and_qnames_union` failed with
`assert {'\\Changed'} == {'\\Changed', '\\Extra'}`. Fixed by keeping the non-path seeds explicitly.
Worth recording: the twin split's blast radius reached a case the new tests did not cover, and the
suite did.

**AC5 — cost:** a 40-symbol path at depth 1, 20 calls, asserted under 250 ms/call, passes. One
bounded query per seed; none per walked node.

**Green run:**

```
$ .venv/bin/pytest -q                                        # Ran at efb7703e1e3c0050256ce379a0ceb125cc32f94c
2226 passed in 160.05s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_a_twinned_path_seed_is_never_a_confident_walk_of_one` + the red run + the pre/post measurement |
| AC2 | `test_a_path_that_resolves_to_nothing_is_still_counted_and_explained` (102 intact) |
| AC3 | `test_the_payload_names_the_seed_expansion` and `test_a_qname_request_does_not_grow_the_expansion_field` |
| AC4 | `test_an_untwinned_path_seed_still_walks` — same rows, no new keys, `seeds_dropped: 0` |
| AC5 | `test_the_added_cost_is_one_bounded_query_per_seed` (40 seeds, timed) |
| AC6 | `test_impact_modules_inherits_the_classification_but_not_the_refusal` + the verdict table + ticket 179; `gate.sh` R1.1/R2.2 green; no `contract.py` edit ⇒ no bump |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2216 passed / 0 failed` at `2f39c25` →
`2226 passed / 0 failed`. ruff + mypy green.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`169-C1` (type-2, `an-expansion-with-no-name-is-an-unbounded-claim`, seen: 169) recorded as
`proposed`. When one requested subject silently becomes N internal subjects, every downstream count
is about a question the caller never asked, and no amount of per-row honesty recovers it — the fix is
to name the expansion, not to caveat the rows. Falsification: not falsified; the pre/post measurement
shows the inflated answer was shape-identical to a correct small one. seen=1 → stays in
`lessons_path`.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived — nothing but the author
looked at this diff; recorded as line one of `DISCLOSURE`. No `Reviewed at` marker ⇒ the stale-review
guard is waived. Self-checks: the over-report measured pre- and post-fix, a red run, a self-caused
bug caught by an existing test and recorded, an AC6 verdict with a filed follow-up, full suite
delta-green, ruff/mypy green.
