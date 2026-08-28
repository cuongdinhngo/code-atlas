---
id: 171
slug: sibling-definitions-fires-on-most-calls-and-is-unranked
title: '`sibling_definitions` fires on 83 % of calls and lists nine sites unranked — a caveat that always fires is a carve-out, not a signal'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [165, 168, 013]
---

## Why this exists (field retro round 11)

165 is the loop's first fix to change shipped work, and the same round found the limit of the shape it
chose. Round 11's §12.d — the *fired, noticed, changed nothing* box that produced 165 in the first
place — records it as this round's design finding:

> *"`authoritative: false` fired on **5 of 6** `find_callers` subjects… The one clean subject was
> `RegionManager::dualView` — a symbol invented after the port, with no twin. On the one call that
> mattered it was load-bearing. On the other four it was ~800 B I skipped. **A caveat that fires on
> 83 % of calls cannot be a signal to act on; it can only be a standing instruction — which is what a
> carve-out already is.** So 165 repaired the *instance* (it named the file) without repairing the
> *policy* (I still cross-check every sweep)."*
>
> *"**What it would have to do instead:** rank or filter the siblings… `sibling_definitions` currently
> lists nine files with equal weight, of which one was the one I needed and eight were noise I had to
> triage by hand. **That is the next 165, and it is the highest-value code ticket in this file.**"*

§9.a states the same conclusion from the obligation side: the disclosure made a mandated sweep
*survivable* — *"a grep I run because the tool pointed at a file is a different act from a grep I run
because I cannot trust the tool"* — but it *"cannot retire the cross-check as a policy, only aim it in
the instance."* §6 prices the noise: **807 B on the subject that mattered, ~800 B × 4 where it did not.**

## Root cause

- `code_atlas/tools/find_callers.py:236-243` — siblings are every `store.nodes_by_name(bare_name,
  kind="Method", limit=config.max_results)` row whose qname differs from the lookup, rendered by
  `definition_sites`. **No ordering, no weight, no partition** — the payload cannot say which sibling a
  given caller is likely to bind to, though the site list already carries the file path (and therefore
  the subtree) of each.
- `code_atlas/tools/find_callers.py:279-281` — the caveat attaches whenever `sibling_sites` is
  non-empty. In a tree where the same trailing name exists in two regions plus a compat layer, that is
  the ordinary case, not the exception.
- `kind="Method"` (`:239`) is a deliberate narrowing from 054's lesson (a Function `\App\put` is not a
  bare Method `put`) — but it means a **Function** twin is silently not disclosed. Worth confirming or
  recording as accepted.

## Scope

Turn the disclosure from a list into an ordering, without hiding anything.

1. Rank or partition `sibling_definitions` by evidence the graph already holds — the **subtree/region**
   of each site is available from the path in `definition_sites`; whether **import/`use` evidence** for
   the calling files is reachable at bounded cost is a design question the ticket delegates.
2. The full list stays available; ranking must not drop a site (the eight "noise" sites were noise for
   one question, not for every question).
3. Apply the same ordering to `find_references` once [168](168_find-references-never-got-165s-twin-disclosure.md)
   gives it the field — one definition site for the ordering (R6.7), not two.
4. Record whether the `kind="Method"` narrowing at `:239` stands, with the reason.

### Explicitly not in scope

- Resolving the binding. The edge model is qname-keyed with no target node id (161's AC1 deviation);
  this ticket ranks a disclosed partition, it does not turn it into an answer.
- Suppressing the caveat when it fires often. A frequent true caveat is not a false one; the fix is
  ordering, not silence.
- Reading the consuming repo's alias registry.

## Constraints

- **Cost** — 165's budget: one bounded query, ~1.35 ms worst case. Ranking must reuse rows already
  fetched; no query per sibling and none per caller.
- **061** — a subject with no sibling stays byte-identical; a subject with exactly one sibling should
  not grow.
- **R5.5** — the ordering is sourced from the computation, and the payload says what it ranked by.
- **R6.7** — one definition site for the ordering, shared with `find_references`.
- **R1.1** no language branch · **R3** no bump · **R4.2** the order is deterministic for identical input.

## Acceptance criteria

1. `find_callers` on a subject with ≥ 2 siblings returns them in a **stated, deterministic order** whose
   basis is named in the payload — pinned by a fixture with siblings in different subtrees.
2. No site is dropped by ranking; the count is unchanged from today for the same subject.
3. `find_references` uses the same ordering once 168 lands, from one definition site (R6.7) — pinned, or
   the dependency recorded if 168 has not landed.
4. A subject with no sibling is byte-identical to today (061); the one-sibling case is measured.
5. Added cost measured against 165's ~1.35 ms and the tokens-to-answer gate; no per-sibling query.
6. The `kind="Method"` narrowing is confirmed or changed, with the reason recorded.
7. Determinism (R4.2), no language branch (R1.1), no bump (R3).

## References

Field retro round 11 §12.d (**the round's design finding — "the next 165, and the highest-value code
ticket in this file"**), §9.a (survivable, not policy-repairing), §6 (the 807 B / ~800 B × 4 price),
§14.a carve-out (f). `code_atlas/tools/find_callers.py:236-243,279-281`. Related:
[165](165_find-callers-splits-across-twins-and-says-reason-ok.md) (the shape this completes),
[168](168_find-references-never-got-165s-twin-disclosure.md) (the second consumer),
[013](013_nav-tools.md), [054](054_bare-name-callers-silent-drop.md).

## Session status

- **KEY:** 171 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, 8-ticket batch) · envelope in `.mango/run-contract-171.txt`.
- **Branch:** `feat/171-rank-the-sibling-definitions`
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2208 passed, 0 failed` at `ae0fcea` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

Scope 1 delegates one question explicitly — *"whether **import/`use` evidence** for the calling files
is reachable at bounded cost is a design question the ticket delegates"*. A **how-decision**: the
answer is readable from the store's shape and the cost constraint. Resolved in Phase 2 →
*Rejected alternatives*. Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 3 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 1 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=6 R=4 G=1 AC=7`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 10 applicable — 9 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R1.8 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.4 (change-type) ✅ · §R5.5 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type) ✅ · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ · §R7.2 (change-type) ✅`
`BASELINE: green — 2208 passed, 0 failed, 0 skipped at ae0fcea (bare pytest, Linux host)`

**Premise:** `find_callers.py:236-243` (siblings unordered, unweighted, unpartitioned) and `:279-281`
(the caveat attaches whenever the list is non-empty) both resolve.

**One premise surfaced as ambiguous, not blocking.** The ticket's Scope 3 says *"apply the same
ordering to `find_references` **once 168 gives it the field**"*, and AC3 offers *"pinned, or the
dependency recorded if 168 has not landed"*. 168 **landed earlier tonight** (#208), so the dependency
is met and AC3 takes its first branch — but the line numbers the ticket cites moved when it did.

**Recall:** `165` (by symbol: `sibling_definitions` — the shape being completed).
`derived-not-listed-invariant` (R6.7, by handle — one ordering site, not one per tool; traced below).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | a caveat that always fires is a carve-out, not a signal | order it, so it says which site to open first | round 11 §12.d | open |
| R1 | Scope 1 | rank or partition by evidence the graph already holds (subtree from the path) | nearest-subtree-first | `definition_sites` carries `file` | open |
| R2 | Scope 2 | the full list stays available; ranking must not drop a site | reorder only | — | open |
| R3 | Scope 3 | same ordering on `find_references`, one definition site (R6.7) | shared function | 168's `nav_result` move | open |
| R4 | Scope 4 | record whether the `kind="Method"` narrowing stands, with the reason | verdict | `find_callers.py:239` | open |
| AC1 | AC 1 | ≥ 2 siblings ⇒ stated deterministic order, basis named in the payload | Falsifiable: order + basis asserted | proving test | open |
| AC2 | AC 2 | no site dropped; count unchanged | Falsifiable: length + set equality | proving test | open |
| AC3 | AC 3 | `find_references` uses the same ordering from one site, or the dependency recorded | Falsifiable: both tools asserted | proving test | open |
| AC4 | AC 4 | no sibling ⇒ byte-identical; the one-sibling case measured | Falsifiable: two tests | proving test ×2 | open |
| AC5 | AC 5 | cost measured against 165's ~1.35 ms; no per-sibling query | Falsifiable: timed under the budget | proving test | open |
| AC6 | AC 6 | the `kind="Method"` narrowing confirmed or changed, with reason | Falsifiable: verdict + source | design record | open |
| AC7 | AC 7 | R4.2, R1.1, no bump (R3) | Falsifiable: repeat-call equality, grep-gates | proving test + `gate.sh` | open |
| C1 | Constraint | one bounded query, ~1.35 ms; ranking reuses rows already fetched | a sort, not a lookup | — | binding |
| C2 | Constraint | 061 — no sibling byte-identical; one sibling should not grow | omit the basis under 2 | — | binding |
| C3 | Constraint | R5.5 — the ordering is sourced from the computation, and the payload says what it ranked by | name the basis | — | binding |
| C4 | Constraint | R6.7 — one definition site, shared with `find_references` | one function | — | binding |
| C5 | Constraint | R1.1 no language branch · R3 no bump · R4.2 deterministic | — | — | binding |
| C6 | Constraint | not in scope: resolving the binding, suppressing a frequent caveat, reading the alias registry | ordering only | — | binding |

### Root cause (taxonomy: presentation / signal design)

The disclosure is correct and complete, and therefore useless as a trigger: every site carries equal
weight, so acting on it means triaging all of them by hand — which is the same work the carve-out
already mandated. The graph already holds the evidence to order them (each site's path, hence its
subtree); nothing consumed it.

### Blast radius

- `nav_result.py`: the ordering function plus an attach helper. Both tools route through it.
- `find_callers.py` / `find_references.py`: each replaces a two-line attach with one call, and each
  needs the subject's own file — already fetched in both (`subject_nodes` / `nodes`).
- No store change, no query change, no new row read.

## Phase 2 — design

### Approach

`rank_sibling_sites(sites, subject_file)` sorts by `(-shared_directory_depth, file)` — the number of
leading directory components a site shares with the subject's own file, then the path as a
deterministic tie-break. `attach_sibling_definitions` attaches the ordered list and, **only when
there are ≥ 2 sites**, `sibling_definitions_ranked_by`. With no subject file the basis falls back to
`path`, and says so, rather than returning an unexplained order.

Both tools call it. Because 168 moved the sibling vocabulary into `nav_result`, this is one edit in
one place, and `find_references` inherited the ordering with no ordering code of its own.

### Rejected alternatives

- **Rank by import/`use` evidence for the calling files** — the option Scope 1 delegated. Rejected on
  cost and on truth. Cost: it needs the *callers* of each sibling, i.e. a query per sibling (nine on
  the field subject), on top of the one bounded query the budget already allows — the ticket forbids
  "a query per sibling and none per caller" explicitly. Truth: an `IMPORTS` edge from a caller's file
  is evidence about the *file*, not about the call site, so it would rank confidently on a weaker
  signal than the subtree. The subtree is free, already in the payload, and honest about what it is.
- **Partition into `likely` / `other` buckets** instead of one ordered list. Rejected: a bucket
  boundary is a threshold, and a threshold is a claim the graph cannot support (161's AC1 deviation
  settles that the binding is not resolvable). An order says "start here"; a partition says "these are
  wrong", which is more than is known.
- **Filter to the nearest subtree.** Explicitly out of scope, and it would drop the eight sites that
  are noise for one question and the answer to another.
- **Suppress the caveat when it fires often.** The ticket forbids it, and rightly: a frequent true
  caveat is not a false one.

### Assumptions

| Assumption | Tag |
|---|---|
| Each site's `file` is enough to derive its subtree | verified — `definition_sites` emits `file` for every site |
| The subject's own file is already fetched in both tools | verified — `subject_nodes` (callers) and `nodes` (references) |
| 168 landed, so AC3 takes its first branch | verified — merged as #208 earlier in this batch |
| A test asserting the ranked order would fail without ranking | **initially false, and fixed** — see *Empirical outputs*; the first two fixtures passed unranked |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `rank_sibling_sites` + `attach_sibling_definitions` + the basis vocabulary | `code_atlas/tools/nav_result.py` | one ordering site (R6.7) | R1, R2, R3, AC1–AC4 | 1/1 |
| Route through the helper; supply `subject_file` | `code_atlas/tools/find_callers.py` | replaces a two-line attach | R3, AC3 | 1/1 |
| Route through the helper; supply `subject_file` | `code_atlas/tools/find_references.py` | replaces a two-line attach | R3, AC3 | 1/1 |
| Proving tests (8) | `tests/test_sibling_ranking.py` (new) | new file | AC1–AC5, AC7 | 1/1 |
| README; BACKLOG; ledger; working doc | `README.md`, `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `derived-not-listed-invariant` (R6.7) — **traced.** One ordering site; the second tool cannot drift:

  ```
  $ grep -rln 'def rank_sibling_sites' code_atlas/     # Ran at ea35e3632804eab29237fb0f2042a5064591ccef
  code_atlas/tools/nav_result.py
  ```

### AC6 verdict — the `kind="Method"` narrowing STANDS

Confirmed and kept on `find_callers`, with the reason. A bare `run()` call site is a **function**
call, not a method call, so a `Function` twin of a method's trailing name is a *different subject*,
not a missed one — 054's lesson, and removing the narrowing would re-add the false positives 054
existed to remove. `find_references` keys on the **subject's own kind** instead of a constant (168),
which is the same rule expressed once rather than twice. Evidence:

```
$ grep -n 'kind="Method"' code_atlas/tools/find_callers.py           # Ran at ea35e3632804eab29237fb0f2042a5064591ccef
237:                if store.count_nodes_by_name(bare_name, kind="Method") > config.max_results:
250:                    kind="Method",
$ grep -n 'kind=str(nodes\[0\]\["kind"\])' code_atlas/tools/find_references.py
179:                        kind=str(nodes[0]["kind"]),
```

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (five twins at five distinct subtree depths) | integration test | ✅ |
| AC2 | integration (length + set equality) | integration test | ✅ |
| AC3 | integration (both tools, one fixture shape each) | integration test ×2 | ✅ |
| AC4 | integration (one sibling; no sibling) | integration test ×2 | ✅ |
| AC5 | measurement (200 calls under 165's budget) | integration test | ✅ |
| AC6 | analysis (verdict) | recorded above with source evidence | ✅ |
| AC7 | logic (two identical calls agree) + guard (grep-gates) | integration test + `gate.sh` | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`tests/test_sibling_ranking.py::test_siblings_come_back_nearest_subtree_first_and_the_basis_is_named`
— and it only became a proving test after the fixture was strengthened twice (below).

### Rollback + porting

Rollback: revert the three source files and the test file. Purely additive to the payload. Porting:
`app` only.

### SCOPE

`SCOPE: M` — one sort and one field, shared by two tools; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `rank_sibling_sites` sorts by shared subtree depth, path as tie-break | implemented-as-approved |
| The basis is named, and only with ≥ 2 sites (061) | implemented-as-approved |
| A missing subject file falls back to `path` and says so | implemented-as-approved |
| One ordering site; both tools route through it (R6.7) | implemented-as-approved |
| Nothing dropped, nothing filtered, nothing bucketed | implemented-as-approved |
| No query per sibling; a sort over rows already fetched | implemented-as-approved |

No deviations. Diff ⊆ approved list.

### Empirical outputs

**The proving test had to be made falsifiable twice, and that is the most useful thing in this
record.** R6.5 says a guard ships only once it has been observed failing. It was observed *passing*
against no ranking, twice:

1. **First fixture** — twins at `src/app/east/core/legacy`, `…/other`, `src/app/west/core`,
   `src/compat`, `vendor`. Nearest-subtree-first happened to equal **lexicographic** order, so the
   assertion could not tell ranking from the store's default. Red run failed only on the missing
   basis field, never on the order.
2. **Second fixture** — paths renamed so lexicographic order is nearly the reverse (`aaa_vendor` is
   furthest but sorts first). Still passed unranked: the rows arrive in **insertion** order, and the
   test planted them nearest-first.
3. **Third fixture** — planted in `sorted()` order, so insertion order is the lexicographic one and
   neither matches the ranked answer. Only now does the red run fail on the order itself:

```
$ .venv/bin/pytest -q tests/test_sibling_ranking.py   # Ran at ae0fcea4c93fd93e98261132bbb04df75a23de0f
E       AssertionError: assert ['aaa_vendor/...Plan.php'] == ['src/app/eas...Plan.php']
E         At index 0 diff: 'aaa_vendor/Plan.php' != 'src/app/east/core/zz_legacy/Plan.php'
```

The furthest twin was first without ranking and is last with it. The fixture now carries an assertion
of its own — `assert TWINS != LEXICOGRAPHIC` — so it cannot silently regress to case 1.

**AC5 — cost:** the ranking test asserts `< 1.35 ms/call` (165's budget) over 200 calls with five
siblings, and passes. Ranking adds no query: it sorts the rows the one bounded query already
returned.

**Green run:**

```
$ .venv/bin/pytest -q                                  # Ran at ea35e3632804eab29237fb0f2042a5064591ccef
2216 passed in 142.53s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_siblings_come_back_nearest_subtree_first_and_the_basis_is_named` (order asserted **before** the basis, so the order is what fails) |
| AC2 | `test_ranking_drops_nothing` — length and set equality |
| AC3 | `test_find_callers_uses_the_same_ordering` + the AC1 test on `find_references`; the R6.7 trace shows one site |
| AC4 | `test_one_sibling_does_not_grow_a_basis_field` and `test_no_sibling_is_byte_identical` |
| AC5 | `test_ranking_adds_no_query_and_no_measurable_cost` — 200 calls under 165's 1.35 ms |
| AC6 | the verdict recorded above, with the source evidence: the narrowing **stands** |
| AC7 | `test_the_order_is_deterministic_for_identical_input`; `gate.sh` R1.1/R2.2 green; no `contract.py` edit ⇒ no bump |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2208 passed / 0 failed` at `ae0fcea` →
`2216 passed / 0 failed`. ruff + mypy green.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`171-C1` (type-2, `an-ordering-test-must-defeat-both-default-orders`, seen: 171) recorded as
`proposed`. A test that asserts a computed order is vacuous unless the fixture defeats **both** the
lexicographic order and the insertion order — a fixture that accidentally agrees with either passes
against no implementation at all. Falsification: not falsified; observed directly, twice, in this
ticket, and only the third fixture produced a real red run. seen=1 → stays in `lessons_path`.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived — nothing but the author
looked at this diff; recorded as line one of `DISCLOSURE`. No `Reviewed at` marker ⇒ the stale-review
guard is waived. Self-checks: a proving test made falsifiable across three fixtures, a recorded AC6
verdict, full suite delta-green, ruff/mypy green.
