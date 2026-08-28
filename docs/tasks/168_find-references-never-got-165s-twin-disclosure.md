---
id: 168
slug: find-references-never-got-165s-twin-disclosure
title: '`find_references` under-reports an alias-backed class by 4.7× and still says `reason: "ok"` — 165 fixed the tool 7-A moved to, not the tool it was filed against'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [165, 013, 122]
---

## Why this exists (field retro round 11)

165 shipped `sibling_definitions` + `authoritative: false` on `find_callers`, and round 11 verified it
in real work — it named a twin the evaluator would not have opened, and the disclosure changed a
shipped PR. **The same round measured the tool 7-A was originally filed against and found no caveat at
all:**

```
find_references(Alpha\Plan\Plan)
  →  total_count: 16,  4 in src/,  reason: "ok",  no `authoritative` field
```

against **19** real `new Plan(` / `extends Plan` sites under `src/` = **21.1 % coverage**, with
the registry line at `config/legacy_aliases.php:1357` routing the bare name to **both** region classes.

> Round 11 §12.e(f): *"the round's sharpest code finding."*
> §14 (7-A): *"**⚠️ SPLIT — the claim is half true, and the wrong half was fixed.** Fixed on
> `find_callers`… **NOT fixed on `find_references`** — 16 hits, 4 in `src/`, `reason:"ok"`, no
> `authoritative` field at all… r9 measured 0.6 %; better, still a 4.7× under-report at a confident
> `ok`."*
> §15 ranks this the round's **single requested change**.

The asymmetry is the defect: two tools answer the same twin-shaped question, one discloses the
partition and one presents it as whole. An agent that has learnt to trust `find_callers`' caveat has no
reason to suspect its sibling tool is silent.

## Root cause

- `code_atlas/tools/find_references.py:202-203` — `authoritative` is set **only** when
  `all(hit.get("confidence_tier") == "DYNAMIC" for hit in results)`. The caveat is keyed on **tier**,
  not on whether a same-named definition exists elsewhere, so a fully-RESOLVED partition reads clean.
- `code_atlas/tools/find_references.py:199` — `attach_ambiguous_definitions(result, definition_sites(nodes))`
  discloses duplicates of the **exact qname**. A twin under a *different* qname (`Alpha\…\Plan` vs a
  bare `Plan` in another tree) is not a duplicate of the qname asked for, so nothing attaches.
- `code_atlas/tools/find_callers.py:236-243` — the machinery already exists: one bounded
  `store.nodes_by_name(bare_name, …)`, filtered against the looked-up qname, rendered by
  `definition_sites`. It was pointed at one tool.
- `code_atlas/tools/find_references.py:168` — `reason = relation_reason(hit_total=…, symbol_indexed=…)`
  is a pure function of this qname's hit count, the same shape 165 repaired on `find_callers.py:253`.

## Scope

Give `find_references` the disclosure `find_callers` has, for a class-shaped subject.

1. When the subject's trailing name has ≥ 2 definitions under other qnames, disclose the sibling
   definition sites and carry the caveat (`authoritative: false`, or the design's recorded equivalent).
2. Keep the existing all-`DYNAMIC` caveat **distinguishable** from the new twin caveat — they are
   different reasons for the same field, and an agent that cannot tell them apart cannot act on either.
3. Design records which shape it chose and what it rejected (a count vs named sites; one field vs two).

### Explicitly not in scope

- **Ranking or filtering the siblings** — that is [171](171_sibling-definitions-fires-on-most-calls-and-is-unranked.md),
  which applies to both tools once this one has the field.
- Reading the alias registry as a data source. The graph does not model it; a caveat that says
  *"this count is a partition"* is the honest endpoint, not a resolved count.
- Changing the reference query, its ranking, or the FTS path.

## Constraints

- **061** — a subject with exactly one definition of its trailing name is **byte-identical** to today.
- **Cost** — one bounded query, the shape 165 measured at ~1.35 ms worst case. `find_references` is
  reached from sweeps; no per-row query.
- **R5.5** — the caveat is sourced from the computation that produced it, not from a table of names.
- **R1.1** no language branch · **R3** no bump (the field exists in this tool's vocabulary already) ·
  **R4.2** order-stable sites.

## Acceptance criteria

1. `find_references` on a subject whose trailing name has ≥ 2 definitions discloses the sibling sites
   and carries the caveat — pinned by a fixture with a twin pair, one reference to each.
2. The same call on a subject with a unique trailing name is byte-identical to today (061).
3. An answer whose hits are all `DYNAMIC` and an answer that is twin-partitioned are **distinguishable**
   in the payload; both cases pinned.
4. `attach_ambiguous_definitions` (exact-qname duplicates) and the new disclosure remain distinct and
   can both appear on one payload.
5. Added per-call cost measured and inside the tokens-to-answer gate.
6. Determinism (R4.2), no language branch (R1.1), no contract bump (R3).

## References

Field retro round 11 §12.e(f) (the measurement), §14 row 7-A (**SPLIT**), §15 (the round's one
requested change), §9.b (veto log — the carve-out this would let us narrow); round 9's 0.6 % on the
same tool. `code_atlas/tools/find_references.py:168,199,202-203`;
`code_atlas/tools/find_callers.py:236-243,253`. Related:
[165](165_find-callers-splits-across-twins-and-says-reason-ok.md) (the machinery),
[013](013_nav-tools.md), [122](122_exact-miss-shaping-discards-a-resolved-subject.md).

## Session status

- **KEY:** 168 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, 8-ticket batch) · envelope in `.mango/run-contract-168.txt`.
- **Branch:** `feat/168-find-references-twin-disclosure`
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2206 passed, 0 failed` at `85fdb87` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

Scope 3 asks design to record *"which shape it chose and what it rejected (a count vs named sites;
one field vs two)"*. A **how-decision**: 165 already shipped the shape on the sibling tool, and the
ticket's own framing (the asymmetry is the defect) settles it. Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 1 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=5 R=3 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 10 applicable — 9 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R1.8 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.4 (change-type) ✅ · §R5.5 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type) ✅ · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ · §R7.2 (change-type) ✅`
`BASELINE: green — 2206 passed, 0 failed, 0 skipped at 85fdb87 (bare pytest, Linux host)`

**Premise:** `find_references.py:202-203` (the caveat keyed on tier only), `:199`
(`attach_ambiguous_definitions` over exact-qname duplicates), `find_callers.py:236-243` (the existing
machinery) and `:168` (`relation_reason` as a pure function of this qname's hits) all resolve exactly
as described.

**Recall:** `165` (by symbol: `sibling_definitions` — the shape to copy, and the tests that pin it).
`derived-not-listed-invariant` (R6.7, by handle — the vocabulary must have one definition site, not a
copy per tool; traced below).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | the asymmetry: one tool discloses the partition, the other presents it as whole | give `find_references` the same disclosure | round 11 §14 (7-A) | open |
| R1 | Scope 1 | ≥ 2 definitions of the trailing name under other qnames ⇒ disclose sites + caveat | reuse 165's shape | `find_callers.py:236-243` | open |
| R2 | Scope 2 | keep the all-`DYNAMIC` caveat distinguishable from the twin caveat | name the reasons | `find_references.py:202-203` | open |
| R3 | Scope 3 | record the chosen shape and what was rejected | design record | — | open |
| AC1 | AC 1 | twin pair, one reference each ⇒ sites + caveat, pinned | Falsifiable: red→green | proving test | open |
| AC2 | AC 2 | unique trailing name ⇒ byte-identical (061) | Falsifiable: no new key | proving test | open |
| AC3 | AC 3 | all-`DYNAMIC` and twin-partitioned distinguishable; both pinned | Falsifiable: two payloads, and a both-fired case | proving test ×3 | open |
| AC4 | AC 4 | `ambiguous_definitions` and the new disclosure distinct, both on one payload | Falsifiable: one payload carrying both | proving test | open |
| AC5 | AC 5 | added per-call cost measured, inside the tokens-to-answer gate | Falsifiable: timing + gate green | benchmark + `gate.sh` | open |
| AC6 | AC 6 | R4.2, R1.1, no bump (R3) | Falsifiable: grep-gates, no `contract.py` edit | `gate.sh` | open |
| C1 | Constraint | 061 — one definition of the trailing name ⇒ byte-identical | omit every new key | — | binding |
| C2 | Constraint | Cost — one bounded query, ~1.35 ms budget; reached from sweeps; no per-row query | one `nodes_by_name` | — | binding |
| C3 | Constraint | R5.5 — the caveat is sourced from the computation, not a table of names | derived from the rows fetched | — | binding |
| C4 | Constraint | R1.1 no language branch · R3 no bump · R4.2 order-stable sites | — | — | binding |
| C5 | Constraint | ranking/filtering is **not** here — that is 171 | order stays the store's | — | binding |

### Root cause (taxonomy: logic / disclosure)

`authoritative` on `find_references` is keyed on **confidence tier** (`all(... == "DYNAMIC")`), and
`attach_ambiguous_definitions` is keyed on **exact-qname duplicates**. A fully-RESOLVED answer whose
subject has a twin under a *different* qname satisfies neither condition, so it reads clean. The
machinery to detect it already existed one file over; it had simply been pointed at one tool.

### Blast radius

- `nav_result.py`: the shared vocabulary + two helpers. Nothing existing changes meaning.
- `find_callers.py`: imports the constant instead of defining it, and emits `authoritative_caveats`
  beside the fields it already emitted. Its `kind="Method"` is unchanged.
- `find_references.py`: one bounded query on the indexed path, and the caveat block.
- 165's tests keep passing — the change is additive on `find_callers`.

## Phase 2 — design

### Approach

Move `SIBLING_DEFINITIONS` and the caveat vocabulary into `nav_result`, add
`sibling_definition_rows(store, bare_name, kind, lookup, limit)` and
`attach_authoritative_caveats(payload, caveats)` there, and call both from each tool. The sibling
query is keyed on **the subject's own kind**, taken from the resolved node — which is 054's rule (a
bare Method name and a Function qname are different subjects) expressed once, rather than the
constant `"Method"` copied into a second tool where the subject is a Class.

`authoritative: false` stays the actionable boolean (R5.4: one register); `authoritative_caveats` is
the sorted list of reasons — `all_hits_dynamic`, `sibling_definitions`, or both.

### Rejected alternatives

- **A count instead of named sites** (`sibling_definition_count: 8`). Rejected: round 11's evidence is
  that the disclosure was load-bearing *because it named a file the evaluator would not have opened*.
  A count restores the caveat and removes the only part that changed anyone's behaviour.
- **One field, no reasons** — keep `authoritative: false` alone. Rejected by Scope 2 and by R5.4: the
  two caveats call for **different actions** (widen the query vs distrust the tier), and a single
  boolean cannot carry both. This is the "one field vs two" question the ticket named.
- **A new `reason` value** (e.g. `reason: "twin_partitioned"`). Rejected: `reason` is the *relation*
  answer (`ok` / `no_matches` / …) and is a pure function of this qname's hit count; overloading it
  would make a true `ok` unstateable for a twin-partitioned subject, and 122 depends on that shape.
- **Copying `find_callers`' block into `find_references`.** Rejected by R6.7 — and 171 then has to
  rank in two places instead of one.

### Assumptions

| Assumption | Tag |
|---|---|
| `nodes[0]` carries the subject's `name` and `kind` on the indexed path | verified — `nodes` is `nodes_by_qualified_name(...)`, already fetched for the `indexed` check |
| Keying on the subject's kind is a generalisation, not a behaviour change, for `find_callers` | verified — it keeps `"Method"` explicitly; only `find_references` uses the subject's kind |
| Adding `authoritative_caveats` to `find_callers` does not break 165's tests | verified — 165 asserts on `authoritative` and `sibling_definitions`; the addition is additive |
| The sibling query is already paid on the indexed path | **false, and accounted for** — it is a new query on that path; measured below |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| Shared vocabulary + `sibling_definition_rows` + `attach_authoritative_caveats` | `code_atlas/tools/nav_result.py` | one definition site (R6.7) | R1, R2, AC6 | 1/1 |
| Import the constant; emit the named caveat | `code_atlas/tools/find_callers.py` | additive; 165's tests hold | R2, AC3 | 1/1 |
| The sibling query + the caveat block | `code_atlas/tools/find_references.py` | indexed path only | R1, R2, AC1–AC4 | 1/1 |
| Proving tests (6) | `tests/test_find_references_twins.py` (new) | new file | AC1–AC4 | 1/1 |
| README; BACKLOG; ledger; working doc | `README.md`, `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `derived-not-listed-invariant` (R6.7) — **traced.** One definition site, and the second tool cannot
  drift from it:

  ```
  $ grep -rn 'SIBLING_DEFINITIONS = ' code_atlas/     # Ran at 785f6fc41e6aa642158b73270d71765d971ad939
  code_atlas/tools/nav_result.py:523:SIBLING_DEFINITIONS = "sibling_definitions"
  ```

  (One hit. Before this change the constant lived in `find_callers.py`; a copy in `find_references`
  would have made 171's ranking a two-site change.)

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (a planted twin pair with a reference to each) | integration test | ✅ |
| AC2 | integration (a lone subject) | integration test | ✅ |
| AC3 | integration ×3 (twin-only, dynamic-only, both) | integration tests | ✅ |
| AC4 | integration (one payload carrying both facts) | integration test | ✅ |
| AC5 | measurement (200 calls at 40 twins vs none) + guard (`gate.sh` tokens-to-answer) | benchmark + gate | ✅ |
| AC6 | guard (grep-gates) + logic (no `contract.py` edit) | `gate.sh` | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`tests/test_find_references_twins.py::test_a_twin_partitioned_answer_discloses_the_sibling_and_is_not_authoritative`
— the 4.7× under-report, now stating that it is a partition. Plus
`::test_both_tools_now_answer_the_twin_question_the_same_way`, which is the asymmetry itself.

### Rollback + porting

Rollback: revert the three source files and the test file; the vocabulary move is the only
non-additive part and is internal. Porting: `app` only.

### SCOPE

`SCOPE: M` — one query and one caveat block, plus a vocabulary move; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Vocabulary + helpers in `nav_result`, one definition site | implemented-as-approved |
| Sibling query keyed on the subject's own kind in `find_references` | implemented-as-approved |
| `find_callers` keeps `"Method"` explicitly | implemented-as-approved |
| `authoritative: false` + `authoritative_caveats` (sorted, deduped) | implemented-as-approved |
| Every new key omitted when there is nothing to say (061) | implemented-as-approved |
| No ranking or filtering — that is 171 | implemented-as-approved |

No deviations. Diff ⊆ approved list.

### Empirical outputs

**Red run — the disclosure removed from `find_references`:**

```
$ .venv/bin/pytest -q tests/test_find_references_twins.py   # Ran at 85fdb876be9f5f494a6c7c28ae6ba983a271c6fe
E       KeyError: 'authoritative'
E       AssertionError: both reasons fired and both are named
E       assert ['all_hits_dynamic'] == ['all_hits_dynamic', 'sibling_definitions']
E       KeyError: 'sibling_definitions'
4 failed, 2 passed
```

The second and third lines are AC3 specifically: with the twin caveat gone, a subject that is *both*
dynamic and twin-partitioned reports only the tier reason — the half-truth 7-A named.

**AC5 — the measured cost**, at 40 twins (over 4× the field's nine sites):

```
$ .venv/bin/python  (benchmark, 200 calls each)             # Ran at 785f6fc41e6aa642158b73270d71765d971ad939
  40 twins: 0.681 ms/call
  no twin:  0.580 ms/call
```

+0.10 ms for the disclosure at 40 twins, against 165's ~1.35 ms budget. Both figures include the one
bounded query, which is now paid on every indexed answer — that is the honest accounting: the query
is new on this path, and 0.580 ms is what it costs when it finds nothing.

**Green run:**

```
$ .venv/bin/pytest -q                                        # Ran at 785f6fc41e6aa642158b73270d71765d971ad939
2208 passed in 126.13s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_a_twin_partitioned_answer_discloses_the_sibling_and_is_not_authoritative` + the red run |
| AC2 | `test_a_unique_trailing_name_is_byte_identical` — no `sibling_definitions`, no `authoritative`, no caveats |
| AC3 | `test_the_two_caveats_are_distinguishable` (both fire, both named) and `test_a_dynamic_only_answer_names_only_the_tier_caveat` |
| AC4 | `test_ambiguous_definitions_and_sibling_definitions_stay_distinct` — two same-qname sites *and* one other-qname twin on one payload |
| AC5 | the benchmark above; `gate.sh` tokens-to-answer green (ratio ≥ 0.63) |
| AC6 | `gate.sh` R1.1/R2.2 green; sites keep the store's `_NODE_ORDER` (R4.2); no `contract.py` edit ⇒ no bump |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2206 passed / 0 failed` at `85fdb87` →
`2208 passed / 0 failed`. ruff + mypy green.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`168-C1` (type-2, `fix-the-class-not-the-instance-when-two-tools-share-a-question`, seen: 168)
recorded as `proposed`. 165 repaired the tool the evaluator had moved to, not the tool the finding was
filed against, and the result was worse than either state alone: an agent that learns to trust one
tool's caveat has no reason to suspect its sibling is silent. When a caveat is added to one of two
tools answering the same question, the other tool's silence becomes a *stronger* false signal than it
was before. Falsification: not falsified — round 11 measured exactly this. seen=1 → stays in
`lessons_path`.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived — nothing but the author
looked at this diff; recorded as line one of `DISCLOSURE`. No `Reviewed at` marker ⇒ the stale-review
guard is waived. Self-checks: a red run isolating AC3, a cost measurement at 4× the field's twin
count, full suite delta-green, ruff/mypy green.
