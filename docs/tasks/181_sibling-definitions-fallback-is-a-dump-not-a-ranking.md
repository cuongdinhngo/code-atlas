---
id: 181
slug: sibling-definitions-fallback-is-a-dump-not-a-ranking
title: '`sibling_definitions` at `ranked_by: "path"` is a 93-row alphabetical dump wearing a ranking''s shape — and 91 % of the session''s disclosure bytes'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [171, 168, 169]
---

## Why this exists (field retro round 12 §12.d)

171 shipped the ordering 165's caveat needed, and round 12 fired it three times. **The good basis is
excellent and the fallback is a dump — and both arrive in the same field, with the same shape.**

*Case A — `find_references(…ModelMember)`, `sibling_definitions_ranked_by: "shared_subtree_with_subject"`:*

```
1. legacy/alpha/web/model/model/member/ModelMember.php:21   Class
2. legacy/beta/web/model/model/member/ModelMember.php:12    Class
```

**2 siblings, both exactly right** — the three-way split this anchor is defined by, named in two rows.

*Case B — `impact(paths:[ModelMember.php])`, `sibling_definitions_ranked_by: "path"`:*

```
1. legacy/alpha/web/application/interimPlan/model/index.php:57   Method
2. legacy/alpha/web/model/entity/EntityMember.php:662          Method
…  legacy/alpha/web/include/adodb/adodb-active-record.inc.php:121    Method
```

**93 entries. 42 (45 %) are real `ModelMember` twins; 51 (55 %) share only a method name** — `adodb`
internals, API controllers, `AddressModel`, `AbstractRateDetail`. `path` is alphabetical, so
`application/` sorts above `model/` and the needed twin sits at position ~6.

**The defect is not the ordering.** 171's AC held: the order is deterministic and drops nothing. The
defect is that **a sort and a ranking are indistinguishable in the payload**, so a caller who does not
branch on `ranked_by` reads case B's first row as if it were case A's. Round 12 recorded it as the
round's design finding — *fired, noticed, changed nothing*.

**It is also the round's cost headline.** Batch C's new fields cost ≈8.9 KB across a 15-call session;
**8.1 KB of that is this one block on this one call** (§6). 91 % of the disclosure bill buys a list
that is 55 % noise for the question asked.

### Why `path` is reached at all

`impact`'s twinned-seed disclosure (169) passes `subject_file=None` — a path request has no single
subject file, so the subtree basis has nothing to measure against and 171 correctly falls back. **The
fallback is doing the only honest thing available; the payload just does not say that it is a
fallback.**

## Scope

1. **The shape says which it is.** When the ordering has no evidence to rank by, the payload must
   say so in a way a caller can branch on without knowing the value vocabulary — design picks and
   records: `sibling_definitions_ranked_by: null` plus an explicit `sibling_ranking: "unranked"`, or
   a value whose name carries it. **A caller must not have to know that `"path"` means *unranked*.**
2. **Cap the unranked list, and name the cap.** An unranked 93-row list is a dump; `find_orphans`
   already has the vocabulary for this shape (`walk_truncated`). Ranked lists stay uncapped — nothing
   is dropped when position is meaningful.
3. **Give `impact`'s path seeds a basis if a cheap one exists.** A path request has no subject file,
   but it does have the **seed's own file** per twinned seed. Whether ranking each seed's siblings
   against that seed's path is reachable at 171's cost budget is a design question this ticket
   delegates — and if it is, `path` stops being reached on the tool where it does most damage.
4. **Cheap noise reduction, if it is honest.** 55 % of case B's rows share only a trailing name with
   no relationship to the subject. Whether the graph already holds something that separates *a twin
   of this class* from *a method with the same name on an unrelated class* — the sibling's own
   container kind or qname prefix — is a design question. **Recording "no, it does not" is a valid
   answer**; guessing is not (161 AC1).

### Explicitly not in scope

- Dropping sites from a **ranked** list. 171's *"noise for one question, not for every question"*
  stands.
- Resolving the binding. The edge model is qname-keyed with no target node id (161's AC1 deviation).
- Changing when the caveat fires. A frequent true caveat is not a false one.
- `find_orphans`' own refusal — [182](182_find-orphans-answers-with-rows-it-has-flagged-unreliable.md).

## Constraints

- **061** — a subject with no sibling stays byte-identical; a ranked answer with ≥ 2 siblings keeps
  today's rows and order unless the basis itself changes.
- **Cost** — 171's budget: a sort over rows already fetched, ~1.35 ms worst case. No query per
  sibling, none per caller. **A cap is a byte saving and must be measured as one.**
- **R5.5** — the payload says what it ranked by, or that it could not rank.
- **R6.7** — one ordering site, shared by `find_callers`, `find_references` and `impact`.
- **R1.1** no language branch · **R3** no bump · **R4.2** deterministic within and across bands.

## Acceptance criteria

1. An unranked disclosure is distinguishable from a ranked one **by shape, not by knowing the value
   vocabulary** — pinned on one payload of each kind, including the `impact` path-seed case.
2. An unranked list is capped, the cap is named in the payload, and the total is still reported —
   pinned; a ranked list is uncapped and byte-identical to today.
3. Scope 3's verdict is recorded: either path seeds gain a per-seed basis (pinned) or the reason they
   cannot is written down.
4. Scope 4's verdict is recorded, with the measurement or the reason it is unmeasurable.
5. No-sibling and one-sibling payloads byte-identical (061).
6. Byte delta on case B measured against the 8.1 KB field figure.
7. Determinism (R4.2), no language branch (R1.1), no bump (R3).

## References

Field retro round 12 §9.a (cases A and B in full), §12.d (the design finding), §6 (8.1 KB of 8.9 KB),
§14.a (proposed carve-out: *"do not read the top rows when `ranked_by` is `path`"*). Round 11 §12.d
is where 171 itself came from. **Provenance note:** 171's AC was proven on authored fixtures only, and
this is the property those fixtures could not test — *for a ranking, "deterministic and lossless" is a
precondition, not an acceptance criterion.*
`code_atlas/tools/nav_result.py:538-544,558`; `code_atlas/tools/impact.py:158-166`. Related:
[171](171_sibling-definitions-fires-on-most-calls-and-is-unranked.md),
[168](168_find-references-never-got-165s-twin-disclosure.md),
[169](169_impact-path-seed-walks-every-symbol-and-its-twins.md).

## Session status

- **KEY:** 181 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended batch) · envelope in `.mango/run-contract-181.txt`.
- **Branch:** `feat/181-sibling-fallback-is-a-dump` (stacked on `feat/175-…`)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2419 passed, 0 failed` at `af4d4b6` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

Three how-decisions, all delegated by name:

1. Scope 1 — the shape that says which it is → *Approach*.
2. Scope 3 — whether path seeds can gain a basis → **implemented, measured, and DECLINED**; see the
   verdict. This is the ticket's real finding.
3. Scope 4 — whether the graph holds a twin-vs-same-name discriminator → **yes, and it is a
   container fact, not a path fact**; filed as **189** with the measurement.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous`
`RECALL: 2 claim(s) surfaced | 1 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=5 R=4 G=1 AC=7`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 9 applicable — 8 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.5 (change-type) ✅ — it decided Scope 3 · §R6.1 (change-type) ✅ · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.7 (change-type) ✅ · §R7.2 (change-type) ✅ · §R7.6 (change-type) ✅`
`BASELINE: green — 2419 passed, 0 failed, 0 skipped at af4d4b6 (bare pytest, Linux host)`

**Premise:** all five citations resolve. `nav_result.py:571-605` is `rank_sibling_sites` +
`attach_sibling_definitions`; the fallback at `:580` returned `RANK_PATH` and the basis was published
unconditionally at `:604`. `impact.py:158-166` passes `subject_file=None`, which is why the fallback is
reached there. **The ticket's own provenance note is the key premise and it is correct:** 171's AC was
proven on authored fixtures, and *"deterministic and lossless" is a precondition for a ranking, not an
acceptance criterion.*

**Recall:** `prove-the-guard-fails` (R6.5, by handle). `rank_sibling_sites` (by symbol — 171's own
work, now under review by its successor).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | a sort and a ranking are indistinguishable in the payload; 91 % of the disclosure bill | one verdict field, and a cap | round 12 §9.a, §6 | open |
| R1 | Scope 1 | the shape says which it is, branchable without knowing the value vocabulary | `sibling_definitions_ranked` boolean; `"path"` retired | `:604` | open |
| R2 | Scope 2 | cap the unranked list, name the cap; ranked lists uncapped | cap 10 + truncated + total | `find_orphans`' shape | open |
| R3 | Scope 3 | give path seeds a basis if a cheap one exists | **reachable, measured, DECLINED** | see verdict | open |
| R4 | Scope 4 | cheap noise reduction if honest; "no" is a valid answer | the discriminator is the container; filed as 189 | `definition_sites` drops qname | open |
| AC1 | AC 1 | unranked distinguishable from ranked **by shape**, incl. the `impact` case | Falsifiable: one payload of each + the tool | proving test ×3 | open |
| AC2 | AC 2 | unranked capped, cap named, total reported; ranked uncapped and byte-identical | Falsifiable: both asserted | proving test ×2 | open |
| AC3 | AC 3 | Scope 3's verdict recorded, pinned or the reason written down | **the reason is a pinned measurement** | proving test | open |
| AC4 | AC 4 | Scope 4's verdict recorded with the measurement or the reason | filed as 189 with the evidence | ticket 189 | open |
| AC5 | AC 5 | no-sibling and one-sibling byte-identical | Falsifiable: four fields asserted absent | proving test | open |
| AC6 | AC 6 | byte delta on case B measured against 8.1 KB | Falsifiable: measured | proving test + measurement | open |
| AC7 | AC 7 | R4.2, R1.1, no bump | Falsifiable: repeat equality + grep-gates | proving test + `gate.sh` | open |
| C1 | Constraint | 061 — no sibling byte-identical; a ranked answer keeps today's rows and order | ranked path untouched | — | binding |
| C2 | Constraint | 171's cost budget; a cap is a byte saving and must be measured as one | measured at 87.9 % | — | binding |
| C3 | Constraint | R5.5 — the payload says what it ranked by, **or that it could not** | the second clause is the fix | — | binding |
| C4 | Constraint | R6.7 — one ordering site, three tools | unchanged, still one | — | binding |
| C5 | Constraint | R1.1 · R3 · R4.2 within and across bands | no branch, no bump | — | binding |

### Root cause (taxonomy: presentation / signal design)

**A fallback was given the same shape as the thing it falls back from.** 171 needed to name its basis
(R5.5) and had two bases to name, so it named both — and `"path"` reads as a basis while meaning *there
was no basis*. Every honest property held: deterministic, lossless, documented. The one thing that did
not hold is that a caller cannot act on it without knowing the vocabulary, which is the exact
definition of a signal that fires and changes nothing.

### Blast radius

- `nav_result.py`: `RANK_PATH` **retired**, `SIBLING_RANKED` / `SIBLING_TRUNCATED` / `SIBLING_TOTAL`
  and a cap added; `rank_sibling_sites` returns `str | None`; `attach_sibling_definitions` gains the
  verdict and the cap.
- All four consumers (`find_callers`, `find_references`, `impact`, `impact_modules`) inherit through
  the one site — **no consumer changed** (R6.7 earning its keep).
- 171's own test loses `RANK_PATH` and gains the `basis is None` assertion.
- No store change, no query, no contract change.

## Phase 2 — design

### Approach

**One boolean is the verdict; the basis is the value.** At ≥ 2 sites,
`sibling_definitions_ranked: true|false` is **always** present — that is what a caller branches on, and
it needs no vocabulary. `sibling_definitions_ranked_by` rides only when there *is* a basis to name.
This is 170's rule reapplied one field over: a verdict is stated, a value is conditional.

**`"path"` is retired, not annotated.** An honest name cannot mislead, so the misleading value is
removed from the vocabulary rather than documented. `rank_sibling_sites` returns `None` for the
no-evidence case; the rows are still path-sorted for determinism (R4.2), because *alphabetical is a
sort* and the payload now says exactly that.

**The unranked list is capped at 10, with the total.** An unranked list has no meaningful position, so
row 11 is not less relevant than row 1 — it is equally unordered, and 93 of them cost 8.7 KB. The
population is still reported (`sibling_definitions_total`) so nothing is hidden (066/123). **A ranked
list is never capped**: position is the answer, and dropping a row would remove it. Pinned both ways.

### Scope 3 verdict — reachable, implemented, MEASURED, and DECLINED. This is the ticket's finding.

A one-path request has no subject *symbol* but it does have a subject **file**, and it is already on
the row that found the twin (`_split_twinned` reads `rows[0]`). So the basis is reachable at zero
cost. I implemented it — `SeedPlan.twinned_files` plus a `sibling_subject_file` property that refuses
to pick when there is more than one — and then measured it on case B's own shape:

```
subject : src/alpha/model/member/ModelMember.php
siblings: src/beta/model/member/ModelMember.php        <- the answer
          src/alpha/vendor/lib000/Unrelated0.php ... x40   <- share only the method name

basis "shared_subtree_with_subject":
  position  1 : src/alpha/vendor/lib000/Unrelated0.php
  position 41 : src/beta/model/member/ModelMember.php  <- LAST
```

**The anchor's twins live in sibling regions (`alpha` / `beta`) while the same-name noise lives inside the
subject's own region.** Shared-subtree depth rewards being *near*, and a twin is by definition *far* —
so the basis measures the wrong axis for exactly this case. Shipping it would have traded an honest
`ranked: false` for a `ranked: true` whose first row is noise: **181's own defect with a
better-sounding label.**

So the implementation was reverted and the measurement kept as a pinned test
(`test_the_subtree_basis_would_rank_the_real_twin_BELOW_the_noise`). AC3 asks for the verdict pinned
*or* the reason written down; this is both.

### Scope 4 verdict — the discriminator exists, it is a CONTAINER fact, and it is filed as 189

*"Is this a twin of my class, or a same-named method on an unrelated one?"* is answered by the
sibling's **container**: `\Alpha\ModelMember::getName` and `\Beta\ModelMember::getName` share a
container trailing name; `\Vendor\Unrelated0::getName` does not. The rows are already fetched —
`definition_sites` publishes `{file, line, kind}` and drops `qualified_name`.

Not done here, and the reason is R5.5 rather than cost: ranking on the container **without publishing
it** states a basis the payload's own rows cannot be checked against, and publishing it adds bytes to
every sibling row on four call sites — the very axis this ticket exists to reduce. Filed as **189**
with the measurement attached, and 189 also carries the sharper question this raises: **if a twin is a
container fact, `shared_subtree_with_subject` may be wrong for `find_callers` too** — round 12's case A
worked only because it had two siblings and no noise to outrank.

### Rejected alternatives

- **`ranked_by: null` plus a separate `sibling_ranking: "unranked"`** (the ticket's first suggestion).
  Rejected: `null` in a payload is a value this repo omits, and it needs *two* fields to answer one
  question. A boolean verdict plus a conditional value is one fewer thing to read.
- **Keeping `"path"` and documenting it.** The carve-out round 12 proposed (§14.a: *"do not read the
  top rows when `ranked_by` is `path`"*). Rejected: a carve-out a reader must remember is what this
  ticket is filed against.
- **Capping the ranked list too.** Position is the answer there; a cap would drop the answer.
- **Filtering the unranked list to likely twins.** Out of scope (nothing is dropped from a ranked
  list) and it needs 189's discriminator to be honest at all.
- **Ranking path seeds by subtree anyway** — the Scope 3 verdict above, with the measurement.

### Assumptions

| Assumption | Tag |
|---|---|
| A per-seed basis would improve case B | **falsified by measurement** — it ranks the real twin **last**; the whole Scope 3 verdict turns on this |
| The subtree basis is right for the qname path | **held, but narrowly** — case A had no noise to outrank; 189 carries the re-examination |
| The container is available for a better basis | verified — `_split_twinned` holds the rows; `definition_sites` drops the qname |
| An unranked list can be capped without hiding anything | verified — the total rides, so the population is still stated (066) |
| One ordering site means no consumer changes | verified — four consumers, zero edits |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| Retire `RANK_PATH`; `SIBLING_RANKED` / `SIBLING_TRUNCATED` / `SIBLING_TOTAL` + cap; `rank_sibling_sites -> str \| None`; the verdict and cap in `attach_sibling_definitions` | `code_atlas/tools/nav_result.py` | one ordering site, four consumers | R1, R2, AC1–AC2, AC5, AC7 | 1/1 |
| 171's fallback test asserts `basis is None` | `tests/test_sibling_ranking.py` | one test | R1 | 1/1 |
| Proving tests (10), incl. the Scope 3 counterfactual | `tests/test_sibling_disclosure_is_a_ranking_or_says_not.py` (new) | new file | AC1–AC7 | 1/1 |
| Scope 4's follow-up, with the measurement | `docs/tasks/189_*.md`, BACKLOG | new row | R4, AC4 | 1/1 |
| BACKLOG; ledger; LESSONS; working doc | `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `prove-the-guard-fails` (R6.5) — **traced.** Three red runs below, one per property.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | logic (one payload of each) + integration (the `impact` path-seed case) | integration test ×3 | ✅ |
| AC2 | logic (93 sites capped; 93 ranked uncapped) | integration test ×2 + red runs 2, 3 | ✅ |
| AC3 | **measurement** (the counterfactual ranking, pinned) | integration test | ✅ |
| AC4 | analysis (verdict) | recorded above + ticket 189 | ✅ |
| AC5 | logic (four fields asserted absent below two sites) | integration test | ✅ |
| AC6 | measurement (bytes before/after, against 8.1 KB) | integration test + recorded figure | ✅ |
| AC7 | logic (repeat equality) + guard (grep-gates) | integration test + `gate.sh` | ✅ |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **The noise is still there — 55 % of case B's rows still share only a name.** This ticket makes the
  list honest and small; it does not make it relevant. **Expiry:** ticket **189**, which carries the
  container discriminator and the re-examination of the subtree basis. Recorded because a capped
  10-row unranked list could otherwise read as "solved" when the reader still has 10 rows of which
  ~5 are noise.

### Proving test

`tests/test_sibling_disclosure_is_a_ranking_or_says_not.py::test_a_ranked_and_an_unranked_disclosure_differ_by_shape`

### Rollback + porting

Rollback: revert `nav_result.py`, delete the new test file, restore 171's assertion and the 189 row.
No persisted state, no schema or contract change. Porting: `app` only.

### SCOPE

`SCOPE: M` — one ordering site's vocabulary and a cap; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `sibling_definitions_ranked` always present at ≥ 2 sites | implemented-as-approved |
| `"path"` retired from the vocabulary, not annotated | implemented-as-approved |
| Unranked capped at 10 with the total; ranked never capped | implemented-as-approved |
| Determinism preserved in both modes | implemented-as-approved |
| One ordering site; no consumer edited | implemented-as-approved |
| Scope 3's basis implemented, measured, reverted | **implemented then deliberately reverted** — the verdict |

### Empirical outputs

**AC6 — the byte measurement, against the field's 8.1 KB:**

```
before (171 shape): 8,705 B for 93 rows
after  (181 shape): 1,054 B for 10 rows + total + truncated
saved             : 7,651 B  (87.9%)
scaled to the field's 8.1 KB figure: ~0.98 KB
```

So the block that was **91 % of a 15-call session's new disclosure bytes** becomes about 12 % of its
old size, and the reader is told the population it was cut from.

**AC3 — the Scope 3 counterfactual, which is why Scope 3 was declined:**

```
basis "shared_subtree_with_subject" over case B's shape
  position  1 : src/alpha/vendor/lib000/Unrelated0.php     <- same region as the subject
  position 41 : src/beta/model/member/ModelMember.php  <- the answer, LAST
```

**Three red runs (R6.5):**

```
1. the retired "path" basis restored (171's shape)
   E  assert not True                      # ranked: true for an unranked list
   E  8705 B -> 8705 B (0% saved)                                    6 failed, 4 passed
2. the unranked cap removed (the 93-row dump)
   E  assert 93 == 10   /   assert 41 == 10
   E  8705 B -> 8773 B (-1% saved)
3. a RANKED list capped too (position dropped)
   E  assert 10 == 93                                                1 failed, 9 passed
```

Red 1 is the pre-181 payload and it fails **six** tests, including the byte measurement — which is the
useful part: the shape fix and the byte fix are the same change.

**Green run:**

```
$ .venv/bin/pytest -q
2429 passed in 147.38s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 82 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_a_ranked_and_an_unranked_disclosure_differ_by_shape`, `test_the_retired_value_is_gone_from_the_vocabulary`, `test_the_impact_path_seed_reports_unranked_and_is_capped` (case B through the real tool) |
| AC2 | `test_an_unranked_list_is_capped_and_says_so` + `test_a_ranked_list_is_never_capped`; red runs 2 and 3 |
| AC3 | `test_the_subtree_basis_would_rank_the_real_twin_BELOW_the_noise` — the verdict **is** the pinned measurement |
| AC4 | recorded above; filed as **189** with the evidence |
| AC5 | `test_no_sibling_and_one_sibling_stay_byte_identical` — four fields asserted absent |
| AC6 | `test_the_byte_saving_on_case_b_is_measured` (> 85 % asserted; 87.9 % measured) |
| AC7 | `test_the_order_is_deterministic_in_both_modes`; `gate.sh` R1.1/R2.2 green; no `contract.py` edit ⇒ **no bump (R3), confirmed** |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2419 passed / 0 failed` at `af4d4b6` →
`2429 passed / 0 failed`. ruff + mypy green. `scripts/gate.sh` → `GATE GREEN`.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen >= 2 | 0 routed to a destination | 0 cannot promote (reason) | 1 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `prove-the-guard-fails` (R6.5) gains 181: three red runs.
- **New:** `181-C1` (type-2, `a-fallback-must-not-wear-the-shape-it-falls-back-from`) — when a computed
  answer has a *"could not compute it"* branch, the two must differ **in shape**, not in a value the
  caller has to interpret. 171 named its fallback `ranked_by: "path"`; every honest property held
  (deterministic, lossless, documented) and a caller still read row 1 as meaningful. The test: can a
  reader branch correctly **without knowing the value vocabulary**? seen=1.
- **Second, and worth more than the fix:** 181's Scope 3 was implemented, measured, and **reverted**,
  because the measurement showed the basis ranks the wanted row **last**. A basis that is available is
  not therefore a basis that is right, and `ranked: true` on a bad basis is worse than `ranked: false`.
  That is 189's ticket, and the evidence is a committed test rather than a paragraph.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. Self-checks: a delegated
design question implemented, measured, and **declined on the measurement**; the counterfactual kept as
a committed test rather than a claim; the byte saving measured against the field's own figure; three
red runs, the first of which fails six tests because the shape fix and the byte fix are one change;
and the residual noise recorded as an exclusion with ticket 189 as its expiry.
