---
id: 179
slug: impact-modules-inherits-half-the-seed-fix
title: '`impact_modules` inherits 169''s seed classification but not its twin refusal — and never had 161''s either'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [169, 161, 140]
---

## Why this exists

Filed by [169](169_impact-path-seed-walks-every-symbol-and-its-twins.md) AC6, which required
`impact_modules`' inheritance of the seed fix to be *"confirmed or filed"*. It is **half inherited**,
and the missing half predates 169.

| | `impact` | `impact_modules` |
|---|---|---|
| path seed classified through `_resolve_seed` (169) | yes | **yes** — both call `resolve_seeds` |
| a lost subject counted in `seeds_dropped` (102) | yes | **yes** — same helper |
| shared-**qname** seed disclosed, not walked (161) | yes | **no** — never called `_split_ambiguous` |
| shared-**trailing-name** seed refused (169) | yes | **no** — `_split_twinned` is not shared |

`impact_modules.py:127-132` calls `resolve_seeds` and hands `seed_set.seeds` straight to
`store.impact_radius`. So a module rollup over a twinned file walks both twins and rolls their
modules together — the same 29× shape 169 measured, one aggregation layer up, where it is *harder*
to notice because the output is module names rather than symbols.

## Scope

1. Route `impact_modules`' seeds through the same two splits `impact` uses (`_split_ambiguous`,
   `_split_twinned`), from one definition site — not a copy (R6.7, R1.8).
2. The rollup payload discloses what was refused, in whatever shape the module surface makes honest;
   a module list that silently lost a seed is worse than one that names the loss.
3. Confirm whether the two tools should share one seed-resolution entry point outright, or whether
   the module surface legitimately wants different behaviour — and record the answer.

### Explicitly not in scope

- Changing the rollup shape or the module table.
- The edge model (161's AC1 deviation stands).

## Constraints

- **061** — a rollup over untwinned seeds is byte-identical.
- **R6.7 / R1.8** — one decision, one implementation; the splits are `impact`'s and must not be copied.
- **Cost** — 140's shared-helper budget; one bounded query per seed, never per rolled-up node.

## Acceptance criteria

1. `impact_modules` over a file whose symbols have same-named twins does not roll the twin's modules
   into the answer — pinned by a test that fails on today's code.
2. Whatever is refused is named in the payload; `seeds_dropped` accounts for it.
3. The splits have one definition site shared with `impact` (R6.7), pinned.
4. An untwinned rollup is byte-identical (061).
5. Determinism (R4.2), no language branch (R1.1), no contract bump (R3).

## References

Filed by 169's AC6. `code_atlas/tools/impact_modules.py:127-132`; `code_atlas/tools/impact.py`
(`_split_ambiguous`, `_split_twinned`, `resolve_seeds`). Related:
[169](169_impact-path-seed-walks-every-symbol-and-its-twins.md),
[161](161_impact-resolves-a-shared-qname-to-one-twin-and-carries-no-freshness.md),
[140](140_impact-modules.md).

## Session status

- **KEY:** 179 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended batch) · envelope in `.mango/run-contract-179.txt`.
- **Branch:** `feat/179-impact-modules-twin-refusal` (stacked on `feat/186-…`)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2368 passed, 0 failed` at `90af851` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

Scope 3 is a how-decision the ticket asks to be answered and recorded: *"Confirm whether the two
tools should share one seed-resolution entry point outright, or whether the module surface
legitimately wants different behaviour."* Answered in *Scope 3 verdict*. Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous`
`RECALL: 2 claim(s) surfaced | 1 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=3 R=3 G=1 AC=5`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 9 applicable — 8 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R1.8 (recalled handle: one-rule-for-every-subject-slot) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.6 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type) ✅ · §R6.7 (change-type) ✅ · §R7.2 (change-type) ✅`
`BASELINE: green — 2368 passed, 0 failed, 0 skipped at 90af851 (bare pytest, Linux host)`

**Premise:** all three citations resolve and the ticket's four-row table is exactly right.
`impact_modules.py:127-132` called `resolve_seeds` and handed `seed_set.seeds` straight to
`store.impact_radius`. `impact.py:106-125` held both splits **inline in the tool body**, which is why
nothing could inherit them: they were not a shared callable, they were a paragraph.

**The gap was already pinned by a test that asked to be updated.**
`test_impact_path_seed.py::test_impact_modules_inherits_the_classification_but_not_the_refusal`
carried the note *"if this starts failing, 179 has landed — update it"*. It is the red run and it is
now inverted rather than deleted.

**Recall:** `one-rule-for-every-subject-slot` (R1.8, by handle — the class this ticket is a textbook
instance of). `resolve_seeds` (by symbol — the half that *was* shared, and the reason the other half
looked shared).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | half inherited, and the missing half predates 169 | share the whole decision | the four-row table | open |
| R1 | Scope 1 | route through the same two splits, from one definition site — not a copy | extract `plan_seeds` | splits were inline | open |
| R2 | Scope 2 | the rollup discloses what was refused; a module list that silently lost a seed is worse | one shared attacher | — | open |
| R3 | Scope 3 | confirm whether the two tools should share one entry point outright, and record | **yes, outright** | see verdict | open |
| AC1 | AC 1 | a rollup over a twinned file does not roll the twin's modules in — failing today | Falsifiable: red run | proving test | open |
| AC2 | AC 2 | whatever is refused is named; `seeds_dropped` accounts for it | Falsifiable: both asserted | proving test | open |
| AC3 | AC 3 | the splits have one definition site shared with `impact` (R6.7) | Falsifiable: grep-derived + behavioural | proving test ×2 | open |
| AC4 | AC 4 | an untwinned rollup is byte-identical (061) | Falsifiable: four fields asserted absent | proving test | open |
| AC5 | AC 5 | determinism (R4.2), no language branch (R1.1), no contract bump (R3) | Falsifiable: repeat equality + grep-gates | proving test + `gate.sh` | open |
| C1 | Constraint | 061 — untwinned rollup byte-identical | additive only | — | binding |
| C2 | Constraint | R6.7/R1.8 — one decision, one implementation; the splits are `impact`'s | extract, do not copy | — | binding |
| C3 | Constraint | cost — 140's budget; one bounded query per seed, never per rolled-up node | the splits are per-seed | — | binding |

### Root cause (taxonomy: logic / shared-decision boundary)

**The seed decision was shared exactly as far as it had been factored, and no further.**
`resolve_seeds` was a function, so both tools got it; the two splits were twenty lines of tool body,
so only the tool that owned the body got them. Nothing was copied and nothing drifted — the second
consumer simply never received a decision that had never been packaged as one. That is R1.8's failure
mode in its quietest form: not two implementations disagreeing, but one implementation reachable from
one place.

And the consequence is **worse on the rollup than on `impact`**. `impact` names symbols, so a reader
can see `\West\Plan::createPlan` in an answer about `east/`. The rollup names *modules*, so the
twin's module arrives as a name and a count — indistinguishable from a real dependency.

### Blast radius

- `impact.py`: the inline block becomes `SeedPlan` + `plan_seeds` + `attach_seed_refusals` +
  `attach_seed_expansion`. The tool body shrinks by ~35 lines and its behaviour is unchanged — asserted
  by its own existing tests, untouched.
- `impact_modules.py`: three call sites, `seeds_dropped` arithmetic, and the claim's `seeds` count.
- No store change, no query change, no new row read, no contract change.

## Phase 2 — design

### Approach

**Extract the decision, then hand it to both tools.** `plan_seeds(store, paths, qnames, max_results)
-> SeedPlan` runs `resolve_seeds` and both splits and returns `walk_seeds`, `from_paths`,
`ambiguous_sites`, `twinned_sites`, `dropped`, plus a `refused` property that is the exact
`seeds_dropped` contribution. `attach_seed_refusals(payload, plan)` carries the disclosure —
`sibling_definitions`, `authoritative_caveats`, `ambiguous_definitions`, the `subject_ambiguous`
reason, the `try_instead` route and `explain_lost_subject` — verbatim from `impact`, so `impact`'s
payload cannot move. `attach_seed_expansion(payload, plan, paths)` carries 169's third disclosure.

**Not a copy, and the tests prove it by derivation rather than by eye:** `grep -rl` asserts
`_split_ambiguous`, `_split_twinned`, `plan_seeds` and `attach_seed_refusals` each live in exactly one
file, and `plan_seeds(` is called from exactly two. A behavioural test then asserts the two tools'
`reason`, `seeds_dropped`, `sibling_definitions` and `try_instead` are **equal** for the same subject —
so even a future copy that passed the grep would have to keep agreeing.

### Scope 3 verdict — share it OUTRIGHT

**Yes: one entry point, no per-surface behaviour.** The module surface differs in its *rows* — a
rollup by module, with counts and an exemplar — and in nothing else that touches the seed question.
*"Which seeds may honestly be walked"* has one right answer per graph, and the rollup is acted on
destructively for the same reason `impact` is (140's whole premise is that the rollup is the shape the
decision is actually made in). A tool-specific relaxation here would mean *"this surface may walk a
seed the other refuses"*, which is not a design choice, it is a bug with a rationale.

The one legitimate difference is where the disclosure *lands*, and that is why the attacher is a
separate function from the planner: `impact_modules` builds its payload first and then has the
refusals attached, including an override of its unconditional `reason: ok`.

### Rejected alternatives

- **Call the two splits from `impact_modules` directly.** Cheapest edit, and it re-creates the defect
  one level up: the *order* of the splits, the `from_paths` narrowing and the `keep` filter are part of
  the decision, so a second caller assembling them by hand is a second implementation of the
  composition even while sharing the pieces. 169's own comment about which seeds the twin check
  applies to is exactly the kind of thing that would drift.
- **Refuse in `store.impact_radius`.** Wrong layer (R1.4): the store persists and queries; deciding
  that a seed is not honestly walkable is a tool-level judgement, and the store has no payload to
  disclose it on.
- **Mark the rollup non-authoritative and walk anyway.** 169 settled this for `impact` and the
  argument is stronger here: the tier was never the problem, the seed set was, and leaving the twin's
  module in the list with a caveat leaves the reader with a module they must now disprove.
- **Give `impact_modules` its own, softer rule.** Rejected as Scope 3's verdict above.

### Assumptions

| Assumption | Tag |
|---|---|
| `impact`'s payload is unchanged by the extraction | verified — its 37 existing tests pass untouched |
| The fixture really would roll up the twin's module without the refusal | **verified twice** — the red run rolls up 3 symbols where 0 is correct, and `test_the_twin_really_would_have_been_rolled_up` asserts both subtrees are independently reachable |
| `impact_modules` needs the `reason` overridden, not set | verified — it writes `reason: ok` unconditionally, so the attacher runs after the payload is built |
| The splits cost one query per seed, not per rolled-up node | verified — both iterate `seeds`, and the timing test holds at 40 files |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `SeedPlan` + `plan_seeds` + `attach_seed_refusals` + `attach_seed_expansion`; the tool body routed through them | `code_atlas/tools/impact.py` | one decision site | R1, R2, AC3 | 1/1 |
| Route the rollup through all three; fix `seeds_dropped` and the claim's `seeds` | `code_atlas/tools/impact_modules.py` | inherits the refusal | R1, R2, AC1, AC2 | 1/1 |
| Invert 169's gap-pinning test (it asked to be updated) | `tests/test_impact_path_seed.py` | one test | AC1 | 1/1 |
| Proving tests (9) | `tests/test_impact_modules_seed_refusal.py` (new) | new file | AC1–AC5 | 1/1 |
| BACKLOG; ledger; LESSONS; working doc | `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `one-rule-for-every-subject-slot` (R1.8) — **traced.** One site for each part of the decision, and
  exactly two callers of the composition:

  ```
  $ grep -rl 'def plan_seeds\|def _split_twinned\|def _split_ambiguous\|def attach_seed_refusals' code_atlas/
  code_atlas/tools/impact.py
  $ grep -rl 'plan_seeds(' code_atlas/tools/
  code_atlas/tools/impact.py   code_atlas/tools/impact_modules.py
  ```

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (a twinned rollup, and the fixture's own non-degeneracy) | integration test ×2 + red run | ✅ |
| AC2 | integration (`seeds_dropped`, disclosure fields, route) | integration test | ✅ |
| AC3 | guard (grep-derived) + integration (the two tools asserted equal) | integration test ×2 | ✅ |
| AC4 | integration (four fields asserted absent on an untwinned rollup) | integration test | ✅ |
| AC5 | logic (repeat equality) + measurement (40 files) + guard (grep-gates) | integration test ×2 + `gate.sh` | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

**AC1 is input-shape-dependent, stated not hidden.** The twin shape is authored. What lifts it above a
fixture is the second test, which asserts the two subtrees are *independently* reachable — so the
fixture cannot silently stop being able to conflate them.

### Proving test

`tests/test_impact_modules_seed_refusal.py::test_a_twinned_rollup_does_not_roll_up_the_twins_modules`

### Rollback + porting

Rollback: revert two source files, delete the new test file, restore the inverted test. No persisted
state, no schema or contract change. Porting: `app` only.

### SCOPE

`SCOPE: M` — an extraction plus three call sites; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| The decision extracted, not copied; one site per part | implemented-as-approved |
| `impact`'s payload unchanged by the extraction | implemented-as-approved (37 existing tests untouched) |
| The rollup inherits refusal, disclosure, count and route | implemented-as-approved |
| Planner and attacher separate, so the rollup can override its own `reason` | implemented-as-approved |
| Share it outright — no per-surface seed behaviour | implemented-as-approved |

**One addition beyond the AC list, recorded as such:** `impact_modules` also gains 169's
`seed_expansion`. It is not a refusal, so AC2 does not require it — but leaving it out would have
reproduced *this ticket's own complaint one field over*, on the surface where a one-file-to-N-seeds
expansion is hardest to see. Additive, omitted on a qname call (061), and pinned both ways.

### Empirical outputs

**Red run (R6.5)** — the rollup walking plan-less seeds again, i.e. the pre-179 behaviour:

```
$ .venv/bin/pytest -q tests/test_impact_modules_seed_refusal.py tests/test_impact_path_seed.py
E  AssertionError: nothing walkable, so nothing rolled up
E  assert [{'assigned':...ols': 3, ...}] == []          <- the twin's module, with a count
E  AssertionError: assert 'ok' == 'subject_ambiguous'
E  AssertionError: both twinned seeds are accounted for (102)
E  assert 0 == 2
5 failed, 12 passed
```

**The first line is the defect**: a rollup that reports a module with three symbols where the honest
answer is nothing at all. And note it fails *both* files — 169's gap-pinning test flips too, from
"the gap exists" to "the gap is closed", which is the shape a filed-and-then-fixed AC should have.

**AC5 — cost:** the splits are per-seed, so 20 rollups over a 40-file subtree stay under a
250 ms/call budget (140's shape). No query is added per rolled-up node.

**Green run:**

```
$ .venv/bin/pytest -q
2379 passed in 167.21s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_a_twinned_rollup_does_not_roll_up_the_twins_modules`, with `test_the_twin_really_would_have_been_rolled_up` asserting the fixture can still conflate; plus the inverted 169 test |
| AC2 | the same test: `seeds_dropped == 2`, `sibling_definitions` present, `authoritative: false`, `try_instead: file_outline` |
| AC3 | `test_the_splits_have_one_definition_site` (grep-derived, four symbols and the caller set) **and** `test_both_tools_agree_on_which_seeds_are_walkable` (four fields asserted equal across the two tools) |
| AC4 | `test_an_untwinned_rollup_is_byte_identical` — four fields asserted absent |
| AC5 | `test_the_decision_is_deterministic`; `test_the_refusal_adds_no_per_rolled_up_node_query`; `gate.sh` R1.1/R2.2 green; no `contract.py` edit ⇒ **no bump (R3), confirmed** |
| — | `test_a_shared_qname_seed_is_refused_too` — 161's half, which the rollup never had at all, not even before 169; `test_the_rollup_says_how_far_one_path_expanded` — the recorded addition |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2368 passed / 0 failed` at `90af851` →
`2379 passed / 0 failed`. ruff + mypy green. `scripts/gate.sh` → `GATE GREEN`.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen >= 2 | 0 routed to a destination | 0 cannot promote (reason) | 1 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `one-rule-for-every-subject-slot` (R1.8) gains 179, and it is the clearest instance in the corpus:
  **the decision was shared exactly as far as it had been factored.** Recorded as a `seen:` bump on a
  binding rule, with the sharpening below.
- **New:** `179-C1` (type-2, `a-decision-is-only-shared-as-far-as-it-is-factored`) — when a second
  consumer must inherit a decision, check whether the decision is a **callable** or a **paragraph in
  one tool's body**. A shared helper *inside* the decision (here `resolve_seeds`) makes the whole
  decision look shared, and the second consumer silently gets the prefix. seen=1.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. Self-checks: the defect
reproduced by red run with the twin's module visible in the output, a fixture that asserts its own
ability to exhibit the defect, AC3 proven by derivation *and* behaviourally, Scope 3 answered with a
reason, one recorded addition beyond the AC list, and 169's gap-pinning test inverted rather than
deleted.
