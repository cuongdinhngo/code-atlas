---
id: 191
slug: a-conditional-assertion-is-a-test-that-never-ran
title: '`test_a_qname_subject_still_ranks_as_it_did` asserts under an `if` on a payload that answers `index_stale`, so it has never run — and nothing in the suite can tell that apart from a pass'
phase: 1.5b
milestone: Coverage
status: done
depends_on: [189, 181]
---

## Why this exists

Found by **189** by accident: my own first end-to-end sibling test failed with
`KeyError: 'sibling_definitions_ranked_by'`, and the payload turned out to say
`reason: "index_stale"`. Tracing why led to 181's own test:

```python
def test_a_qname_subject_still_ranks_as_it_did(tmp_path, store):
    plant_case_a(store)
    payload = find_callers.create(config_for(tmp_path))("\\Alpha\\ModelMember")
    if SIBLING_DEFINITIONS in payload:          # <- never true
        assert payload[SIBLING_RANKED] is True
        assert payload[SIBLING_RANKED_BY] == RANK_SHARED_SUBTREE
```

`tests/test_impact.seed_file` plants rows **without matching on-disk bytes**, so `FreshnessGuard`
answers `index_stale` before the sibling disclosure is ever built. The `if` then swallows it, and
the test reports **green while asserting nothing**. It is 181's AC5/061 guard for case A, so the
thing 181 claimed was pinned is not.

`tests/test_nav_tools.seed_file` writes the bytes and is the helper that works here — 171's ranking
tests use it, which is why they do exercise the payload.

## Scope

1. Give the test a fresh index (`tests/test_nav_tools.seed_file`) so the payload it builds is
   `reason: "ok"`, and drop the `if` — the assertion must be unconditional or the test is not one.
2. Confirm what it then asserts is still true: after 189, case A's uniform file-name band reports
   `shared_subtree_with_subject`, so the original expectation stands unchanged.
3. **Sweep for the same shape.** `if <key> in payload:` guarding the only assertions in a test is a
   mechanically findable pattern; count the occurrences before deciding whether a guard is wanted.

### Explicitly not in scope

- Changing `tests/test_impact.seed_file` — other tests depend on its cheapness, and `impact` does
  not gate on freshness the way the nav tools do.
- Any production change. Nothing here is a defect in `code_atlas/`.

## Constraints

- **R6.5** — a test that cannot fail is not a guard. The fix must be shown failing against the
  shape it forbids.
- **R6.3** — do not swap one begged question for another: the new fixture must make the payload
  answer, not make the assertion trivially true.

## Acceptance criteria

1. The test asserts unconditionally and its payload answers `reason: "ok"` — pinned.
2. It is shown red against a deliberately wrong basis value, so it is observably a guard.
3. The sweep's count is recorded, and every other conditional-assertion site is either fixed or
   named with a reason it is legitimately conditional.

## References
Found by [189](189_a-twin-is-a-container-fact-not-a-path-fact.md) while replacing the basis 181
declined to ship. `tests/test_sibling_disclosure_is_a_ranking_or_says_not.py` (the test);
`tests/test_impact.py` / `tests/test_nav_tools.py` (the two `seed_file` helpers). Related:
[181](181_sibling-definitions-fallback-is-a-dump-not-a-ranking.md).

## Session status

- **KEY:** 191 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, ticket 2 of 2: 187 → 191) · envelope in `.mango/run-contract-191.txt`.
- **Branch:** `fix/191-a-conditional-assertion-is-a-test-that-never-ran` (rebased onto `main` at `894bed3`, which carries 187)
- **Phase:** 2 design — complete.
- **BASELINE:** green — `2481 passed, 0 failed` at `894bed3` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

1. **Scope 1's fix is necessary and not sufficient, and the ticket cannot know that yet.** Giving the
   test a fresh index makes the payload answer `reason: "ok"` — measured — and it *still* carries no
   `sibling_definitions`. Two further causes, both found by running it: the test calls
   **`find_callers`**, which gates the disclosure on `container is not None`, and `plant_case_a`'s
   subject is a **Class**, whose qname has no container; and the fixture plants only **one** sibling,
   below the two `attach_sibling_definitions` needs before it names a basis. HOW-decision, resolved
   below against 181's own module docstring, which names `find_references` for case A.
2. **Whether Scope 3 wants a guard.** The ticket says *"count the occurrences before deciding"*. The
   count is **2** and both are fixable, so a guard is wanted — reasoned in design, not assumed.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** S · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 1 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=3`
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`
`SURFACES: 2 — tests/test_sibling_disclosure_is_a_ranking_or_says_not.py, tests/test_qname_subject_honesty.py`
`RULE SECTIONS: 8 applicable — 5 by change-type | 3 by recalled handle — §R4.2 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.3 (recalled handle: fixture-shape-begs-the-question) ✅ · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ · §R6.8 (change-type) ✅ · §R7.2 (change-type) ✅ · §R7.6 (change-type) ✅`
`BASELINE: green — 2481 passed, 0 failed, 0 skipped at 894bed3 (bare pytest, Linux host)`

**Premise.** Every reference resolves and the diagnosis is correct as far as it goes:
`tests/test_impact.seed_file` plants rows without on-disk bytes, `FreshnessGuard` answers
`index_stale`, and the `if` swallows it. The **ambiguity** is Scope 2's prediction — *"after 189,
case A's uniform file-name band reports `shared_subtree_with_subject`, so the original expectation
stands unchanged."* The expectation does stand, and is confirmed by measurement below; but the test
as written cannot reach it even over a fresh index, for two reasons the ticket does not name.

**Recall.** `prove-the-guard-fails` (R6.5, by handle) — this ticket *is* the class, from the inside:
a guard that never ran. `fixture-shape-begs-the-question` (R6.3, by handle) — C2 names it, and the
repair must not swap one begged question for another. `derived-not-listed-invariant` (R6.7, by
handle) — Scope 3's sweep must derive its sites from the tree, not carry a list. By symbol:
`attach_sibling_definitions` / `rank_sibling_sites`, whose two thresholds (≥ 2 sites; a partitioning
file-name band) are what actually decide this payload.

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title | the test asserts under an `if` on a payload that answers `index_stale`, so it has never run | and two further reasons it could not have run | measured, Ph0 §1 | open |
| R1 | Scope 1 | fresh index, drop the `if` | `tests/test_nav_tools`-style seeding + unconditional asserts | `reason: ok` measured | open |
| R2 | Scope 2 | confirm what it asserts is still true | true — **and** the fixture and tool must be corrected to reach it | basis measured `shared_subtree_with_subject` | open |
| R3 | Scope 3 | sweep for the same shape; count before deciding on a guard | count = **2**; both fixable ⇒ guard | sweep output | open |
| AC1 | AC 1 | asserts unconditionally, payload answers `reason: "ok"` | pinned by the repaired test | — | open |
| AC2 | AC 2 | shown red against a deliberately wrong basis value | recorded red run | — | open |
| AC3 | AC 3 | the count recorded; every other site fixed or named with a reason | the second site is **fixed**, not named | `test_qname_subject_honesty.py:154` | open |
| C1 | Constraint | R6.5 — a test that cannot fail is not a guard | three red runs, incl. the sweep's own | — | binding |
| C2 | Constraint | R6.3 — do not swap one begged question for another | the payload must *answer*, not be made trivially true | — | binding |

### Root cause (taxonomy: validation)

**Three independent reasons the assertion could not fire, and the `if` hid all three.** (a) The
fixture's rows have no matching on-disk bytes, so `FreshnessGuard` answers `index_stale`. (b) The
test calls `find_callers`, which builds sibling sites only `if indexed and container is not None`
(`find_callers.py:244`), and `split_qname("\\Alpha\\ModelMember")` returns `(None, …)` — a Class
qname has no container, so a class-shaped subject can never carry the field from that tool.
`find_references` has no such gate and does build it — and 181's own module docstring names
**`find_references`** for case A, so the test had drifted from the case it documents. (c) The fixture
plants **one** sibling; `attach_sibling_definitions` names a basis only at **two or more**.

**A conditional assertion converts every one of those into a pass.** Fixing only (a), as Scope 1
literally reads, would have turned a silent green into a red — which is the honest outcome, but not
the one the ticket predicted.

### Blast radius

Tests only: `tests/test_sibling_disclosure_is_a_ranking_or_says_not.py`,
`tests/test_qname_subject_honesty.py`, one new sweep guard. **No production change** — the ticket's
own *Explicitly not in scope*, and pinned by an envelope condition.

## Phase 2 — design

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Repair the guard so it reaches the payload, on all three counts

A local `seed_file` in the test module writes the bytes and the matching digest, the way
`tests/test_nav_tools.seed_file` does. `plant_case_a` gains a **third** region so there are two
siblings, and every one of the three files is named `ModelMember.php` — which is the point:
`rank_sibling_sites` names `shared_file_name_with_subject` only when that predicate **partitioned**
the list, so a uniform band falls through to `shared_subtree_with_subject`. That is exactly Scope 2's
prediction, and it is now reached rather than asserted about.

The subject stays a **Class** and the tool becomes **`find_references`** — 181's own docstring for
case A. Measured on the repaired fixture:

| field | value |
|---|---|
| `reason` | `ok` |
| `sibling_definitions` | `src/beta/…/ModelMember.php`, `src/uk/…/ModelMember.php` |
| `sibling_definitions_ranked` | `True` |
| `sibling_definitions_ranked_by` | `shared_subtree_with_subject` |

### Scope 3: count first, then decide

The sweep is *"every test function whose assertions all sit inside an `if`/`while`"*, walked over the
AST of every `tests/test_*.py`. It reports **2**:

| Site | Why it is the class |
|---|---|
| `test_sibling_disclosure…py::test_a_qname_subject_still_ranks_as_it_did` | this ticket |
| `test_qname_subject_honesty.py::test_no_tool_returns_absence_with_reason_ok` | seven tools queried with an absent subject; the assertion runs only `if empty`. A tool that stopped reporting absence would skip its own check |

Two sites, both genuinely wrong, and one of them cost 181 an acceptance criterion it did not have —
so a guard is wanted. The second is **fixed, not named**: it asserts each payload *is* empty before
asserting its reason, which is R6.5's *a sweep is guarded against emptying itself* applied to the
sweep inside a test. The guard itself carries a non-vacuity assertion for the same reason, and an
explicit (empty) allowlist so a legitimately conditional site is named in the tree rather than
remembered.

### Rejected

- **Only doing Scope 1 literally** (fresh index + drop the `if`) — measured: the test goes **red**,
  because the tool and the fixture cannot produce the field. Shipping that would trade a false green
  for a false red.
- **Keeping `find_callers` and making the subject a Method** — also reaches the field, but it
  redefines case A, which 181 documents as a `find_references` payload over a class subject. The
  smaller, more faithful change is to fix the tool the test drifted away from.
- **Fixing `find_callers` so a class subject also discloses siblings** — a production change, which
  the ticket explicitly excludes. Recorded as a follow-up observation instead.
- **Recording the sweep's count in prose only** — R6.3: a judgement about the real tree ships as a
  committed, re-runnable reporter, or the count is true only on the day it was taken.

### Change list (traced to the matrix)

| # | Path | Change | Rows |
|---|---|---|---|
| 1 | `tests/test_sibling_disclosure_is_a_ranking_or_says_not.py` | local fresh-index `seed_file`; third region in `plant_case_a`; the test targets `find_references` and asserts unconditionally | R1, R2, AC1, AC2 |
| 2 | `tests/test_qname_subject_honesty.py` | assert each payload IS empty before asserting its reason | R3, AC3 |
| 3 | `tests/test_no_assertion_hides_under_a_conditional.py` (new) | the committed sweep, with a non-vacuity floor and an empty allowlist | R3, AC3 |
| 4 | `docs/BACKLOG.md` | 191 `todo` → `done`; the round-12 row's open/closed state | R7.2 |
| 5 | `docs/tasks/191_*.md` | frontmatter status + this working doc | R7.2 |
| 6 | `docs/TOKEN_LEDGER.md` | one spend row | R7.2 |
| 7 | `docs/LESSONS.md` | the durable claim (finalise) | P1 |

### The proving test

`tests/test_sibling_disclosure_is_a_ranking_or_says_not.py::test_a_qname_subject_still_ranks_as_it_did`
— unconditional, over a fresh index, asserting `reason: "ok"`, `ranked is True` and
`ranked_by == shared_subtree_with_subject`. Its red run is AC2's: flip the expected basis to
`RANK_SHARED_FILE_NAME` and it fails, which is the observation that it is a guard at all.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

Three test files and the docs; **no production file touched**, which is the ticket's own
*Explicitly not in scope* and is pinned by envelope condition
`A4-THE-CHANGE-EXISTS-AND-TOUCHES-NO-PRODUCTION-FILE`. One deviation from the change list, recorded:
row 4 also proposed a follow-up line in BACKLOG naming the `find_callers` asymmetry. **Reverted** —
`tests/test_agent_chain_budget.py` went red at `25,165 / 25,150` tokens, and R7.6's answer to a
standing doc at its ceiling is to prune, not to raise the budget. The observation is one paragraph
below instead, in this tier-2 file, and was never on the approved change list to begin with.

### Red runs (R6.5)

| # | Shape forbidden | What failed, verbatim |
|---|---|---|
| 1 | the assertion is not a guard (AC2) | expected basis flipped to `RANK_SHARED_FILE_NAME` → `AssertionError: assert 'shared_subtree_with_subject' == 'shared_file_..._with_subject'` |
| 2 | the fixture drops below the two-site threshold | third region removed → `Right contains one more item: 'src/uk/model/member/ModelMember.php'` |
| 3 | the sweep guard itself | run against the pre-fix tree, it names **both** sites: `test_qname_subject_honesty.py:154` and `test_sibling_disclosure…py:193` |

Red run 3 is the one that matters: the guard was seen failing on exactly the two occurrences that
motivated it, then seen passing once both were repaired.

### The `find_callers` asymmetry, recorded and not fixed

`find_callers` builds sibling sites only `if indexed and container is not None`
(`code_atlas/tools/find_callers.py:244`), and `split_qname` returns `(None, …)` for a Class qname —
so a class-shaped subject **can never** carry `sibling_definitions` from that tool.
`find_references` has no such gate (`find_references.py:182`) and does carry it for the same subject.
Whether that gate is right is a production question and out of scope here; it is not a defect this
ticket may fix, and it is written down rather than left in a session.

### Empirical outputs

| Measure | Before | After |
|---|---|---|
| assertions in `test_a_qname_subject_still_ranks_as_it_did` that can run | 0 | **4** |
| what its payload answers | `index_stale` | **`ok`** |
| sibling sites the fixture produces | 1 (below the basis threshold) | **2** |
| tests whose every assertion sits under a conditional | 2 | **0**, and guarded |
| test functions the sweep reads | — | 1,200+, with a floor of 500 so it cannot pass on an empty scan |
| production files changed | — | **0** |
| tests | 2481 | **2483** |

**Verification coverage:** 3 AC, all 3 covered — AC1 and AC2 by the repaired guard (unconditional,
`reason: "ok"`, red against a wrong basis); AC3 by the committed sweep plus the second site's
repair, which is a fix rather than a name.

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest` from `.venv`):** `2481 passed / 0 failed` at `894bed3`
→ `2483 passed / 0 failed` on the branch tree. The branch was rebased onto `main` after 187 merged,
so the baseline is 187's tree, not the 2476 this run started from. `scripts/gate.sh` → `GATE GREEN`.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 3 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 3 type-2 claim(s) with seen >= 2 | 3 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `prove-the-guard-fails` (R6.5) gains 191 → 27: the ticket **is** the class, seen from the inside.
- `fixture-shape-begs-the-question` (R6.3) gains 191 → 11: the repair had to make the payload
  *answer*, and the first two attempts at it (fresh index alone; fresh index + `find_references`)
  each still could not reach the field.
- `derived-not-listed-invariant` (R6.7) gains 191 → 20: the sweep reads the suite's AST and carries
  an allowlist of exceptions, not a list of sites.
- **New:** `191-C1` (type-2, `a-guard-fails-for-more-reasons-than-it-was-filed-for`), seen 191,
  recurrence 1 — stays in `lessons_path`.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived; the maintainer reviews
on the PR. Self-checks: Scope 1 taken literally was **measured** to leave the test red rather than
green, and the two further causes were found by running the thing rather than by reading it — which
is the whole point of a ticket about an assertion nobody ever ran. Scope 3's guard was decided on the
count the ticket asked for (2), not assumed, and the second site was repaired rather than excused.
One deviation from the approved change list was reverted rather than argued for, and it is recorded
above. The `find_callers` asymmetry the repair uncovered is written down and deliberately not fixed:
it is a production change, which this ticket forbids.
