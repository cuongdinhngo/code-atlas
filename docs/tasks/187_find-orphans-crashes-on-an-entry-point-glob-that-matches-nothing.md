---
id: 187
slug: find-orphans-crashes-on-an-entry-point-glob-that-matches-nothing
title: '`find_orphans` raises `OperationalError: no such table: temp.reach_seen` when `CA_ENTRY_POINTS` matches no indexed file — a typo in a glob crashes the tool instead of answering'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [185, 031, 124]
---

## Why this exists

Found by **185**'s cross-language tool-parity matrix on its first real run, on **both** languages —
so it is not a language fault, it is the first time any test asked `find_orphans` a question over a
real indexed graph with entry points configured.

```
CA_ENTRY_POINTS="\App\Calls\Service::run"        # a QNAME, but entry points are PATH GLOBS
find_orphans() -> OperationalError: no such table: temp.reach_seen
```

Reproduced in a fresh process, with no prior tool call, on a PHP graph and a TS graph.

## The defect, at source

`entry_seeds()` (`reach_shared.py:19`) resolves `config.entry_points` as **path globs**. A glob that
matches no indexed file returns `[]` — a legitimate outcome (a typo, a renamed directory, a
not-yet-indexed tree).

`store.reachable_from()` handles that correctly and cheaply:

```python
# store.py:1662-1663
if not ordered_seeds:
    return ReachabilityResult([], [], 0, False, False)      # returns BEFORE creating the temps
```

`store.find_orphans()` then calls it with `retain_temps=True` and reads the temp tables that early
return never created:

```python
# store.py:1851-1861
reach = self.reachable_from(seeds, depth=depth, max_nodes=max_nodes, retain_temps=True)
...
conn.execute("INSERT OR IGNORE INTO temp.reach_excluded (qname) SELECT qname FROM temp.reach_seen")
```

So `reachable_from` returns an honest empty answer and `find_orphans` raises. **Two consumers of one
walk disagree about whether the empty case is reachable** — R1.8's shape, one layer down.

## Why it matters more than the crash

`find_orphans`' own docstring promises the opposite behaviour: *"unset entry points yield
`status=no_roots_configured`"* — and unset really does (`find_orphans.py` returns `no_roots` before
opening the store). **Configured-but-matching-nothing is the case nobody wrote**, and it is the more
likely misconfiguration of the two: an unset variable is obvious, a stale glob is not. A raise also
crosses the tool boundary as a stack trace rather than an answer with a next action, which is what
050 exists to prevent.

## Status update (2026-08-28, by 182)

**182 removed the crash from the tool path.** `find_orphans` now returns
`status: roots_matched_nothing` before it can reach the store, so the reported repro no longer raises
— pinned by `test_roots_that_match_no_file_refuse_and_name_themselves`, whose red run reproduces this
exact `OperationalError`.

**What remains is the store-level contract, which is the more general half.**
`store.reachable_from` still returns before creating its temps on an empty seed list, and
`store.find_orphans` still reads them — so any *other* caller of `retain_temps=True`, now or later,
crashes the same way. Scope 2 below is the live part; Scope 1 and 3 are delivered.

## Scope

1. An entry-point set that resolves to **zero** seeds returns an answer, not a raise. Design records
   which answer: `no_roots_configured` is taken, so the honest report is a distinct state — the roots
   were configured and matched nothing, which is a fact about the *config*, not about orphans.
2. **One walk, one empty-case contract (R1.8).** Fix it where the disagreement is — either
   `reachable_from` creates its temps before the early return, or `find_orphans` handles the empty
   result without reading them. Design says which and why, and the other consumer of
   `retain_temps=True`, if any, is enumerated by grep.
3. The answer names what was configured and that it matched nothing, so the caller can fix the glob
   without reading source (082).

### Explicitly not in scope

- Changing what an entry point *is* (a path glob, PLAN §11). Accepting qnames is a separate ticket
  and arguably a mistake — a qname-shaped entry point is what produced this report.
- `reachable_from`'s behaviour, which is already correct.
- The orphan definition, the walk budget, or 124's reliability flags.

## Constraints

- **050** — a schema/config problem arrives as an answer with a next action, never a stack trace.
- **R5.6** — the answer must not claim "no orphans" for a walk that never ran; those are different.
- **061** — a resolving entry-point set is byte-identical to today.
- **R6.5** — the guard ships only once observed failing: the red run is the `OperationalError` above.

## Acceptance criteria

1. `CA_ENTRY_POINTS` matching no indexed file returns a payload, not a raise — pinned by a test that
   fails on today's code with `OperationalError`.
2. The payload distinguishes *"no roots configured"* from *"roots configured, matched nothing"*, and
   neither reads as *"no orphans"* — pinned.
3. The empty-case contract lives in one place; every `retain_temps=True` consumer is enumerated and
   covered — pinned.
4. A resolving entry-point set is byte-identical (061), pinned.
5. `reachable_from` untouched, pinned by its existing tests.

## References
Found by [185](185_no-tool-is-ever-asked-a-question-over-a-second-languages-graph.md)'s parity matrix.
`code_atlas/store.py:1662-1663` (the early return), `:1851-1861` (the temp read);
`code_atlas/tools/reach_shared.py:19` (`entry_seeds`); `code_atlas/tools/find_orphans.py`
(`no_roots`). Related: [031](031_reachability-and-orphans.md) (the walk),
[124](124_find-orphans-reliability.md), [050](050_schema-mismatch-is-an-answer.md).

## Session status

- **KEY:** 187 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, ticket 1 of 2: 187 → 191) · envelope in `.mango/run-contract-187.txt`.
- **Branch:** `fix/187-one-empty-case-contract-for-the-reach-walk` (off `main` at `54f23e4`)
- **Phase:** 2 design — complete.
- **BASELINE:** green — `2476 passed, 0 failed` at `54f23e4` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

1. **Which of Scope 2's two options, and does AC5 forbid the first?** → **HOW-decision, resolved.**
   The ticket itself delegates it (*"Design records which answer"*, *"Design says which and why"*),
   so it is not a want-decision. AC5's *"`reachable_from` untouched"* is read as **behaviourally**
   untouched — its `ReachabilityResult` is identical for every input — because the literal reading
   would forbid the first option the same ticket's Scope 2 offers, and *Explicitly not in scope*
   says *"`reachable_from`'s **behaviour**, which is already correct"*. Resolved in favour of the
   first option; the trace that it holds is AC5's own pin below.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** S · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 3 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 1 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=4 R=3 G=1 AC=5`
`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`
`SURFACES: 1 — code_atlas/store.py (GraphStore.reachable_from / GraphStore.find_orphans)`
`RULE SECTIONS: 11 applicable — 7 by change-type | 4 by recalled handle — §R1.8 (recalled handle: one-rule-for-every-subject-slot) ✅ · §R4.2 (change-type) ✅ · §R5.3 (change-type) ✅ · §R5.6 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ · §R7.1 (recalled handle: a-decision-is-only-shared-as-far-as-it-is-factored) ✅ · §R7.2 (change-type) ✅ · §R7.5 (change-type) ✅ · §R7.6 (change-type) ✅`
`BASELINE: green — 2476 passed, 0 failed, 0 skipped at 54f23e4 (bare pytest, Linux host)`

**Premise.** Every construct the ticket cites exists; three of its four line refs have drifted, which
is the ambiguity and nothing more: the early return is `store.py:1756-1757` (cited as `1662-1663`),
the temp read is `store.py:1946-1953` (cited as `1851-1861`), and `entry_seeds` is
`reach_shared.py:23` (cited as `:19`). The 2026-08-28 status update is accurate — 182 put
`status: roots_matched_nothing` in front of the store, so **Scope 1 and 3 are delivered and Scope 2
is the whole of the live work**.

**Recall.** `one-rule-for-every-subject-slot` (R1.8, by handle) — the ticket's own framing.
`a-decision-is-only-shared-as-far-as-it-is-factored` (179-C1, by handle) — *a shared helper inside a
decision is the strongest disguise the class has*, which is exactly the shape here.
`prove-the-guard-fails` (R6.5) and `derived-not-listed-invariant` (R6.7), both by handle. By symbol:
`temp.reach_seen` — LESSONS' 186 entry already records this crash verbatim and says *"Filed as 187,
not fixed here."*

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | a typo in a glob crashes the tool instead of answering | the tool half is done (182); the **store** half is not | `store.py:1946` reads temps `1756` never made | open |
| R1 | Scope 1 | zero seeds return an answer, not a raise | delivered by 182 at the tool; owed at the store | `find_orphans.py` `ROOTS_MATCHED_NOTHING` | delivered |
| R2 | Scope 2 | one walk, one empty-case contract (R1.8) | **the live work** — fix it in `reachable_from` | see design | open |
| R3 | Scope 3 | the answer names what was configured and matched nothing | delivered by 182 | `entry_points_unmatched` | delivered |
| AC1 | AC 1 | matching no file returns a payload, not a raise; red run = `OperationalError` | re-aimed at the **store**, where the raise still lives | red run 1 | open |
| AC2 | AC 2 | `no_roots_configured` ≠ `roots_matched_nothing` ≠ "no orphans" | delivered by 182, pinned | `test_find_orphans_refuses_what_it_cannot_answer.py` | delivered |
| AC3 | AC 3 | the contract lives in one place; every `retain_temps` consumer enumerated and covered | derive the consumer set, don't list it (R6.7) | 1 consumer in `code_atlas/` | open |
| AC4 | AC 4 | a resolving entry-point set is byte-identical (061) | no assertion edited anywhere | baseline 2476 | open |
| AC5 | AC 5 | `reachable_from` untouched, pinned by its existing tests | **behaviourally** untouched (Ph0 §1) | `test_reachability*.py` | open |
| C1 | Constraint | 050 — a config problem arrives as an answer, not a stack trace | the store must not raise on a legitimate empty | — | binding |
| C2 | Constraint | R5.6 — never claim "no orphans" for a walk that never ran | the store reports `reached=0`; the tool refuses | — | binding |
| C3 | Constraint | 061 — a resolving set is byte-identical | AC4's pin | — | binding |
| C4 | Constraint | R6.5 — the guard ships only once observed failing | two red runs recorded | — | binding |

### Root cause (taxonomy: logic)

**`retain_temps=True` is a promise with an unguarded exit.** It means *"the walk's temp tables are
still there for you to read"*, and `reachable_from` has **two** ways out — the walk's `finally`,
which honours it, and an empty-seed `return` that fires **before the `try` block ever opens**. On
that path no temp table is created and none of the caller's reads can work. The answer it returns is
correct; the resource contract it returns under is not.

The same early return also skips `self._reach_drop_temps()`, which sits one line *below* it — so an
empty-seed walk cannot clear a previous retained walk's tables either. That is the same defect facing
the other way: not a crash, but a later reader silently served the previous question's rows.

### Blast radius

`code_atlas/store.py` only, plus one new test file. No tool, adapter, contract, schema or payload
change; `contract_version` untouched (R3.1 N/A).

## Phase 2 — design

`HANDLES: 4 recalled | 4 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Delete the special case; do not add a second one

The two options Scope 2 offers are not equal. Handling the empty result inside `find_orphans` leaves
the trap armed for consumer #2 — the ticket calls that *"the more general half"* — so the fix belongs
where the promise is made.

And the promise can be kept by **removing code**, because the walk already computes the empty answer.
Traced through the loop with `ordered_seeds == []`: both `executemany` calls are no-ops, the
`len(...) > max_nodes` prune is false, the first hop reads an empty `reach_frontier` and breaks, the
container back-fill iterates nothing, `depth_exhausted` is false (the frontier is empty at every
`depth`), `seen_count = 0`, `unproven_total = 0`, `budget_exhausted = 0 >= max_nodes` is false since
`max_nodes >= 1` is already enforced, and both row queries return `[]`. That is
`ReachabilityResult([], [], 0, False, False, False)` — **the value the early return hardcodes**.

So the special case never computed a different answer. It only skipped the temp creation the
`retain_temps` contract promises and the drop that keeps a stale walk from being re-read. Deleting it
makes the postcondition total — *when `reachable_from` returns, the retained temps exist* — and
leaves one implementation of the empty case where there were two (**R1.8**).

### The consumer set is derived, not listed (R6.7)

`_reach_drop_temps` carried its table names as a literal tuple in a method body, so a guard asserting
*"the retained temps exist"* would have had to re-type them. The names move to
`_REACH_RETAINED_TEMPS` (the four the contract promises) and `_REACH_TEMPS` (those plus the two
per-hop scratch tables, which an empty walk never creates); the drop iterates the latter and the
guard imports the former. Consumer N+1 arriving with `retain_temps=True` fails the enumeration guard
rather than crashing in the field.

### Rejected

- **Handle the empty result in `store.find_orphans`** — Scope 2's second option. Fixes one caller and
  leaves the promise broken for the next; it is also a *second* empty-case decision, which is the
  R1.8 violation the ticket is about.
- **Refuse at the store with a new status** — duplicates the refusal 182 already put in the tool. One
  decision, one place; the store reports `reached=0` / `nodes_total=N` and the tool decides (R5.6/C2).
- **Raise `ValueError` on empty seeds (R5.3 "loud on programmer errors")** — an entry-point glob that
  matches nothing is a *data* outcome, not a programmer error; `entry_seeds` returns `[]` legitimately
  and 050/C1 says that must arrive as an answer.
- **Guard the reads in `find_orphans` with `CREATE TEMP TABLE IF NOT EXISTS`** — makes a stale table
  from a previous walk indistinguishable from a fresh empty one. That is the silent-wrong-answer half.

### Change list (traced to the matrix)

| # | Path | Change | Rows |
|---|---|---|---|
| 1 | `code_atlas/store.py` | delete the empty-seed early return in `reachable_from`; ≤3-line comment naming the contract | R2, AC1, AC3 |
| 2 | `code_atlas/store.py` | hoist `_REACH_RETAINED_TEMPS` / `_REACH_TEMPS` to module constants; `_reach_drop_temps` iterates `_REACH_TEMPS` | AC3 |
| 3 | `tests/test_reachability_empty_seeds.py` (new) | the proving test + the retained-temps contract + the no-leak guard + the derived consumer guard | AC1, AC3, AC5 |
| 4 | `docs/BACKLOG.md` | 187 `todo` → `done` | R7.2 |
| 5 | `docs/tasks/187_*.md` | frontmatter status + this working doc | R7.2 |
| 6 | `docs/TOKEN_LEDGER.md` | one spend row | R7.2 |
| 7 | `docs/LESSONS.md` | the durable claim (finalise) | P1 |

### The proving test

`tests/test_reachability_empty_seeds.py::test_orphans_over_seeds_that_resolve_to_nothing_answer_instead_of_raising`
— builds a real two-file graph, calls `store.find_orphans([], ...)` (what `entry_seeds` hands over
when every glob misses) and asserts an `OrphanResult` comes back with `reached == 0`. Red on today's
code with `OperationalError: no such table: temp.reach_seen` — the ticket's own repro, one layer down.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

Every path touched is on the approved change list and nothing else is: `code_atlas/store.py`,
`tests/test_reachability_empty_seeds.py` (new), `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`,
`docs/LESSONS.md`, this file. Production change is **−2 lines**: the two-line early return removed,
`_reach_drop_temps`' literal tuple replaced by the module constant it now iterates. No tool, adapter,
resolver, payload or schema change; `contract_version` untouched.

### Red runs (R6.5), all on the pre-fix tree at `54f23e4`

| # | Test | What failed, verbatim |
|---|---|---|
| 1 | `…_answer_instead_of_raising` (AC1) | `sqlite3.OperationalError: no such table: temp.reach_seen` at `code_atlas/store.py:1960` — the ticket's own repro, one layer down |
| 2 | `…_leaves_every_promised_table_readable_on_the_empty_path` (AC3) | `reach_seen is not readable after seeds=[]` — the promise `retain_temps=True` makes |
| 3 | `…_clears_a_previous_retained_walks_tables` | a previous walk's `reach_seen` still in `temp.sqlite_master` after an empty walk — the silent half |

### The consumer guard failed on prose before it failed on code

AC3's guard was first written as a text sweep for the string `retain_temps=True` under
`code_atlas/`. Its first run reported **two** consumers, `('store.py', 'find_orphans')` and
`('store.py', '')` — the second being the comment that documents the contract. That is exactly the
envelope false positive 190 recorded one ticket earlier, arriving from the other direction: there a
crude text guard reported a defect that was only prose, here it reported a *consumer* that was only
prose. Rewritten to walk the **AST** for a `retain_temps` keyword argument bound to `True`, so it
reports on code and can never report on a comment or a docstring. Carried into the learning loop
below as `187-C1`.

### Empirical outputs

| Measure | Before | After |
|---|---|---|
| exits from `reachable_from` that break the `retain_temps` promise | 1 | **0** |
| implementations of the empty-seed case | 2 (the early return, the walk) | **1** (the walk) |
| empty walk clears a previous retained walk | no | **yes** |
| definition sites for the reach temp-table names | 1 literal tuple in a method body | **1 module constant, imported by the guard** |
| production lines | — | **−2** |
| tests | 2476 | **2481** |

**Verification coverage:** 5 AC, all 5 covered — AC1/AC3/AC5 by the new file (5 tests, 3 with a
recorded red run); AC2 by `test_find_orphans_refuses_what_it_cannot_answer.py`, delivered by 182 and
re-run unchanged; AC4 by the whole suite green with **no existing assertion edited**.

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest` from `.venv`):** `2476 passed / 0 failed` at `54f23e4`
→ `2481 passed / 0 failed` on the branch tree. `scripts/gate.sh` → `GATE GREEN — all 15 checks
passed` (15 passed · 0 failed · 0 skipped), which is what counts under R6.5.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 4 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 4 type-2 claim(s) with seen >= 2 | 4 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `one-rule-for-every-subject-slot` (R1.8) gains 187 → 6: two consumers of one walk disagreeing about
  the empty case, which is what the ticket itself diagnosed.
- `prove-the-guard-fails` (R6.5) gains 187 → 26: three red runs recorded before the fix.
- `derived-not-listed-invariant` (R6.7) gains 187 → 19: the temp-table names moved to one definition
  site so the guard imports them.
- **New:** `187-C1` (type-2, `read-the-syntax-not-the-text`), seen 187 **and** 190 — recurrence 2,
  destination **R6.7**, left for `/mango:promote` and a human to ratify. Nothing written to a rule
  file here.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived; the maintainer reviews
on the PR. Self-checks: the fix **removes** a branch rather than adding one, and the claim that this
is safe is not an argument but a trace — the walk's own return value for an empty seed list was
computed line by line and matched against the constant the deleted branch hardcoded, then pinned by
`test_the_empty_walk_returns_what_the_special_case_used_to_hardcode`. Scope 2's other option was
rejected in writing because it leaves the promise broken for consumer #2, which is the half the
ticket calls general. The one clarification (AC5 vs Scope 2) was resolved against the ticket's own
words rather than assumed away.
