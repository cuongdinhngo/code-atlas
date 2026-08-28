---
id: 182
slug: find-orphans-answers-with-rows-it-has-flagged-unreliable
title: '`find_orphans` returns 215,177 rows it has already flagged unreliable — 99.31 % of the graph, from entry points that reach almost nothing'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [124, 031, 119]
---

## Why this exists (field retro rounds 7–12; fired as a probe every round, never filed)

Carve-out **(e)** — *"`find_orphans` unavailable above ~10k files"* — has been HOLD for five rounds.
Round 12 fired it again and produced the number that makes it a defect rather than a limit:

```
find_orphans → 215,177 orphans of 216,664 nodes = 99.31 %
               walk_truncated: true
               authoritative: false
               entry_points: ["public/*.php"]
```

**The tool flagged its own answer unreliable and then returned 215,177 rows anyway.** Round 12's
verdict: *"a tool that returns 215,177 rows it has already flagged as unreliable is worse than one
that returns `status: roots_unreachable`."*

### The root cause is the roots, not the walk

`entry_points: ["public/*.php"]` is the configured start set. In the anchor, `public/main.php`
`chdir()`s into `legacy/*/web` and dispatches from there, so **the configured roots reach almost
nothing and nearly every node is correctly unreachable from them.** 99.31 % is not a bad algorithm
meeting a big repo — **it is a correct algorithm with the wrong roots**, and nothing in the payload
distinguishes those two readings. 124 fixed the *transport* limit; it did not touch this.

**Corollary from round 12 §12.e:** the top orphan rows were `.claude/skills/legacy-compare/probe.js`
— agent tooling newly indexed by adapter #2, now in the orphan population. A second language widened
the numerator of a fraction whose denominator was already wrong.

## Scope

1. **`walk_truncated` becomes a refusal, not a caveat.** A truncated walk cannot support a
   reachability claim, so the answer is a named refusal carrying what it *can* say (nodes visited,
   budget hit, the roots used) — never a row list. Design records the vocabulary and how 102's
   *"absent subject ≠ modelled zero"* distinction is preserved.
2. **An implausible orphan share is itself a refusal condition.** A share above a stated threshold is
   evidence the roots are wrong, not that the code is dead. Design picks the discriminator and
   **records why a bare threshold is or is not a claim the graph can support** (161 AC1 — a threshold
   is a claim; say what makes this one different, or reject it and find another discriminator).
3. **The roots become visible and correctable.** The payload names the entry points it used and how
   many nodes they reached; a root pattern that matched zero files is named. Whether the default set
   should be derived rather than configured is a design question this ticket delegates — **deriving
   dispatch roots from a `chdir()` is exactly the kind of fact §2.b says is not in the graph, so
   "configurable, and honest about what was configured" may be the correct endpoint.**

### Explicitly not in scope

- The transport/scale fix — [124](124_find-orphans-cannot-answer-at-scale.md), done.
- Reading the anchor's dispatch table. R2: the core encodes no repo's routing.
- Changing the reachability relation set or `IMPACT_KINDS`.
- Excluding agent tooling from the index. That is a consumer `.codeatlasignore` decision, recorded
  here only because it explains one row of the field output.

## Constraints

- **102** — a refusal must stay distinguishable from *"nothing is orphaned"*, which is a real and
  useful answer.
- **061** — a repo whose walk completes within budget and returns a plausible share is byte-identical.
- **Cost** — the walk is already budgeted by `config.orphans_max_nodes` (124); this adds no walk and
  no per-node query.
- **R5.2** — the refusal is sourced from the computation (budget hit, roots reached), never from a
  table of known-bad repos.
- **R5.6** — an index that cannot establish the condition says nothing rather than guessing.
- **R1.1** no language branch · **R3** confirm whether a refusal reason is nav or contract vocabulary
  · **R4.2** deterministic.

## Acceptance criteria

1. A fixture whose walk exceeds the node budget returns a **refusal with no row list** — pinned by a
   test that fails on today's code.
2. A fixture whose roots match no files names that, and refuses — pinned.
3. A genuine, complete, plausible orphan answer is byte-identical to today (061), pinned.
4. *"Nothing is orphaned"* remains distinguishable from *"cannot tell"* (102), pinned on both.
5. Scope 2's verdict is recorded: the discriminator chosen, or the reason a threshold was rejected.
6. The payload names the entry points used and the nodes they reached; a zero-match root is named.
7. No added walk, no per-node query — measured.
8. Determinism (R4.2), no language branch (R1.1), contract impact confirmed (R3).

## References

Field retro round 12 §9.b, §12.e (the 99.31 % measurement and the root-cause diagnosis), §14.a
carve-out (e) — **HOLD for five rounds with no ticket, which is why this one exists**; round 11
measured the same shape at 99.2 %. `code_atlas/tools/get_index_status.py:135-140`
(`orphans_max_nodes` / `orphans_reachability_walk`). Related:
[124](124_find-orphans-cannot-answer-at-scale.md) (the transport half, done),
[031](031_reachability-orphans.md) (the walk),
[119](119_reachability-signal-provenance.md) (signal provenance).

## Session status

- **KEY:** 182 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, final ticket of a 10-ticket batch) · envelope in `.mango/run-contract-182.txt`.
- **Branch:** `feat/182-find-orphans-unreliable-rows` (stacked on `feat/181-…`)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2429 passed, 0 failed` at `1796e0b` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

1. Scope 1's vocabulary → *Approach*, **and Scope 1 needed correcting**: `walk_truncated` is not one
   fact. See *The correction*.
2. Scope 2 — the implausible-share discriminator → **the threshold is REJECTED on 161 AC1**; see the
   verdict.
3. Scope 3 — whether default roots should be derived → **no**; see the verdict.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced; it corrected Scope 1)`
`RECALL: 2 claim(s) surfaced | 1 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=7 R=3 G=1 AC=8`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 10 applicable — 9 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R1.8 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.2 (change-type) ✅ — it decided Scope 2 · §R5.6 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R7.2 (change-type) ✅ · §R7.6 (change-type) ✅`
`BASELINE: green — 2429 passed, 0 failed, 0 skipped at 1796e0b (bare pytest, Linux host)`

**Premise:** the citations resolve and the ticket's root-cause diagnosis is right — 99.31 % is a
correct algorithm with the wrong roots, and nothing separated that from dead code.

**One premise is wrong, and it changes Scope 1.** The ticket says *"`walk_truncated` becomes a
refusal"*. But `walk_truncated` is `reach.truncated`, and at `store.py:1874` that is:

```python
truncated = depth_exhausted or seen_count >= max_nodes or unproven_total > max_nodes
```

**Three causes, and one of them is the caller's own `depth=`.** Refusing on all three would refuse
`find_orphans(depth=2)` — *"what is unreachable within two hops?"* — a legitimate question with a
legitimate answer. Scope 1 read literally would have shipped a new defect.

**Recall:** `prove-the-guard-fails` (R6.5, by handle). `OrphanResult` (by symbol — 124's transport fix,
whose `walk_truncated` this ticket splits).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | 215,177 rows already flagged unreliable, 99.31 % of the graph | refuse, and show the roots | round 12 §9.b | open |
| R1 | Scope 1 | `walk_truncated` becomes a refusal carrying what it can say; 102 preserved | **the BUDGET half only** | `store.py:1874` | open |
| R2 | Scope 2 | an implausible share is a refusal condition; say why a threshold is or is not supportable | **threshold rejected**; publish the ratio's inputs | 161 AC1 | open |
| R3 | Scope 3 | roots visible and correctable; a zero-match root named; whether defaults should be derived | named; deriving rejected | §2.b | open |
| AC1 | AC 1 | a walk over budget refuses with no row list — fails today | Falsifiable: status + empty results | proving test + red run | open |
| AC2 | AC 2 | roots matching no files named, and refused | Falsifiable: status + the pattern named | proving test | open |
| AC3 | AC 3 | a complete plausible answer byte-identical (061) | Falsifiable: five fields asserted absent | proving test | open |
| AC4 | AC 4 | *nothing orphaned* stays distinguishable from *cannot tell* (102) | Falsifiable: both, same empty list, different status | proving test | open |
| AC5 | AC 5 | Scope 2's verdict recorded | the threshold rejected, with the reason | see verdict | open |
| AC6 | AC 6 | the payload names the entry points and what they reached; a zero-match root named | Falsifiable: three fields | proving test ×3 | open |
| AC7 | AC 7 | no added walk, no per-node query — measured | Falsifiable: one shared path fetch + timing | proving test | open |
| AC8 | AC 8 | R4.2, R1.1, R3 confirmed | Falsifiable: repeat equality + grep-gates | proving test + `gate.sh` | open |
| C1 | Constraint | 102 — a refusal stays distinguishable from *nothing is orphaned* | different `status`, same empty list | — | binding |
| C2 | Constraint | 061 — a complete plausible answer byte-identical | new fields on refusals only | — | binding |
| C3 | Constraint | cost — no added walk, no per-node query | one shared `file_paths()` | — | binding |
| C4 | Constraint | R5.2 — sourced from the computation, never a table of bad repos | budget flag + reached count | — | binding |
| C5 | Constraint | R5.6 — an index that cannot establish the condition says nothing | refusals only where the fact is known | — | binding |
| C6 | Constraint | R1.1 · R4.2 · R3 confirm nav vs contract | `status` is tool vocabulary | — | binding |
| C7 | Constraint | not in scope: the transport fix (124), reading the dispatch table (R2), the relation set | untouched | — | binding |

### Root cause (taxonomy: signal design / config)

**The tool computed a correct answer to a question nobody asked, and could not say which question it
had answered.** `entry_points: ["public/*.php"]` names a start set; the anchor's `public/main.php`
`chdir()`s away and dispatches from elsewhere, so almost nothing is reachable *from those roots* —
which the walk reports faithfully. The payload published the *complement* (215,177 orphans) without
publishing the *premise* (three root files reached a handful of nodes), so the only two readings —
*"this code is dead"* and *"these roots are wrong"* — are indistinguishable. And 124 had already
established the honest word for a walk that could not finish; the tool said it and then answered
anyway.

### Blast radius

- `store.py`: `ReachabilityResult` and `OrphanResult` each gain fields — the **budget** half of
  `truncated`, plus `reached` / `nodes_total`. All three come from counts the walk already makes.
- `reach_shared.py`: two status constants, `refuse_reachability`, `unmatched_entry_patterns`, and
  `entry_seeds` gains an optional `paths` so the root report costs no second query.
- `find_orphans.py`: two early refusals and one conditional field.
- `reachable_from` **untouched** and pinned as such.
- 124's two budget-case pins are rewritten as refusals — the intended red run.

## Phase 2 — design

### The correction: `walk_truncated` is three facts, and only two of them are failures

`truncated = depth_exhausted or seen >= max_nodes or unproven > max_nodes`. So `ReachabilityResult`
gains `budget_exhausted` — the two budget causes, without the caller's own depth bound — and
`find_orphans` refuses on **that**. A requested depth limit keeps its rows and keeps 124's
`walk_truncated` caveat, which now means exactly *"you asked for a shallow walk"*. Pinned by
`test_a_deliberately_shallow_walk_still_gets_its_rows`, and red run 3 shows the literal reading of
Scope 1 breaking it.

### Approach

**Two refusals, both sourced from the computation (R5.2).**
`status: roots_matched_nothing` — the configured roots resolve to no indexed node, so no walk ever
started and every node is trivially "unreachable": an answer about the config, not the code.
`status: walk_budget_exhausted` — the walk hit `CA_ORPHANS_MAX_NODES`, so unreached and unreachable
cannot be told apart. Neither returns rows.

**Both carry the two numbers that make 99.31 % legible:** `roots_reached` and `nodes_total`. That is
the whole diagnosis, published as data — *three root files reached a handful of nodes out of 216,664*
reads as *the roots are wrong*, which no share alone can say.

**102 is preserved by `status`, not by emptiness.** *Nothing is orphaned* is `status: ok`,
`results: []`, `total_count: 0` — a real and useful answer. A refusal is the same empty list under a
different status, pinned side by side.

**061 holds exactly.** `roots_reached` / `nodes_total` / `message` ride refusals only;
`entry_points_unmatched` rides wherever it is non-empty. A complete plausible answer with every root
matching is byte-identical — five fields asserted absent.

### Scope 2 verdict — the threshold is REJECTED, and the ratio's inputs are published instead

The ticket asks me to record *why a bare threshold is or is not a claim the graph can support*. **It is
not.** 161 AC1's rule is that a threshold is a claim, and *"an orphan share above X % means the roots
are wrong"* is a claim about a repo's shape that no row supports: a genuinely dead 90 %-orphan repo
exists, and so does a healthy one with badly chosen roots. Any X would be tuned on one anchor and
would be wrong on the next — which is `fixture-shape-begs-the-question` (R6.3) in numeric form.

**And it is unnecessary**, which is the part worth recording. The field case carried
`walk_truncated: true`, so the **structural** condition already refuses it. The two structural
conditions are discrete facts about the computation — *the walk hit its budget*, *the roots matched
nothing* — not tuned numbers. What replaces the threshold is publishing `roots_reached` /
`nodes_total` so the reader judges plausibility with the evidence in hand, which is also exactly what
Scope 3 asked for.

### Scope 3 verdict — roots stay CONFIGURED, and honest about what was configured

Deriving dispatch roots would mean reading a `chdir()` and a dispatch table — a fact §2.b says is not
in the graph, and R2 forbids the core encoding any repo's routing. The ticket's own hedge is the right
answer: **"configurable, and honest about what was configured" is the endpoint.** So the payload names
`entry_points` (already), names any pattern that matched no file (`entry_points_unmatched`, even on a
complete answer, because a dead root silently narrows the population), and on a refusal names what the
roots reached.

### Rejected alternatives

- **A share threshold.** Above.
- **Refusing on all of `walk_truncated`.** The literal Scope 1; it refuses a deliberate `depth=`.
- **Returning rows with a stronger caveat.** Round 12's verdict is explicit that this is the defect:
  *"worse than one that returns `status: roots_unreachable`."*
- **Refusing inside the store.** Wrong layer (R1.4): the store has no payload to refuse on, and
  `reachable_from` legitimately wants the truncated set.
- **Also refusing in `reachable_from`.** Out of scope, and wrong: a partial reachable set is still a
  set of things that *are* reachable — a positive claim a budget cut only shortens. The orphan
  complement is the one a budget cut inverts.
- **Deriving default roots.** Above.

### Assumptions

| Assumption | Tag |
|---|---|
| `walk_truncated` means "hit the budget" | **falsified by reading the source** — it also means the caller's own `depth=`; this changed Scope 1 |
| A threshold could discriminate an implausible share | **rejected on 161 AC1**, and shown unnecessary: the structural condition already covers the field case |
| `reached` / `nodes_total` are free | verified — both are counts the walk already makes (`temp.reach_seen`, `nodes`) |
| Naming unmatched roots needs no extra query | **initially false, and fixed** — the first version re-opened the store and re-fetched `file_paths()`; `entry_seeds` now accepts the list |
| `reachable_from` needs no change | verified and pinned |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `budget_exhausted` on `ReachabilityResult`; `reached` / `nodes_total` / `budget_exhausted` on `OrphanResult` | `code_atlas/store.py` | counts already made | R1, AC6 | 1/1 |
| Two status constants; `refuse_reachability`; `unmatched_entry_patterns`; `entry_seeds(paths=…)` | `code_atlas/tools/reach_shared.py` | one refusal shape | R1, R3, AC7 | 1/1 |
| Two early refusals + `entry_points_unmatched` | `code_atlas/tools/find_orphans.py` | one tool | R1, R3, AC1–AC4 | 1/1 |
| 124's two budget pins rewritten as refusals | `tests/test_find_orphans_pagination.py` | 2 tests | AC1 | 1/1 |
| Proving tests (11) | `tests/test_find_orphans_refuses_what_it_cannot_answer.py` (new) | new file | AC1–AC8 | 1/1 |
| 187 narrowed; 190 filed; BACKLOG pruned to fit | `docs/*` | R7.6 | R7.2 | 1/1 |
| Ledger; LESSONS; working doc | `docs/*` | R7.2 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `prove-the-guard-fails` (R6.5) — **traced.** Three red runs, and red run 2 reproduces 187's crash
  verbatim.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (over-budget walk through the tool) | integration test + red run 1 | ✅ |
| AC2 | integration (a qname-shaped root, the 187 shape) | integration test + red run 2 | ✅ |
| AC3 | integration (five fields asserted absent) | integration test | ✅ |
| AC4 | integration (both answers, same empty list) | integration test | ✅ |
| AC5 | analysis (verdict) | recorded above | ✅ |
| AC6 | integration (three fields, incl. on a complete answer) | integration test ×3 | ✅ |
| AC7 | measurement (one shared path fetch; 20 refusals timed; payload size) | integration test | ✅ |
| AC8 | logic (repeat equality) + guard (grep-gates) | integration test + `gate.sh` | ✅ |

`EXCLUSIONS: 1 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **A refusal is not an answer.** After this, the anchor's `find_orphans` returns *nothing usable* —
  correctly, but the question *"what is dead in this repo?"* is still unanswered there, and the fix is
  a root set only the consumer can supply. **No expiry:** deriving roots is rejected above on §2.b/R2,
  so this is the designed endpoint, not a deferral. Recorded so the next round does not read a refusal
  as progress on the underlying question.

### Proving test

`tests/test_find_orphans_refuses_what_it_cannot_answer.py::test_a_budget_bound_walk_refuses_and_returns_no_rows`

### Rollback + porting

Rollback: revert three source files, delete the new test file, restore 124's two pins. No persisted
state, no schema or contract change. Porting: `app` only.

### SCOPE

`SCOPE: M` — two refusals and three published numbers; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Refuse on the **budget** half only; a requested depth keeps its rows | implemented-as-approved |
| Two named refusals, both sourced from the computation (R5.2) | implemented-as-approved |
| `roots_reached` / `nodes_total` on refusals; `entry_points_unmatched` wherever non-empty | implemented-as-approved |
| 102 preserved by `status`, pinned side by side | implemented-as-approved |
| No threshold | implemented-as-approved |
| `reachable_from` untouched | implemented-as-approved |
| No second query for the root report | **corrected during execute** — see below |

**One correction during execute:** the first version called a `matched_entry_files(store, roots)`
helper that re-fetched `store.file_paths()` — and on the complete-answer path it also **re-opened the
store**. That is an added query per call, which AC7 forbids. `entry_seeds` now takes the path list, the
tool fetches it once, and `unmatched_entry_patterns` is a pure function over it.

### Empirical outputs

**The premise correction, read out of the source before any code changed:**

```python
# store.py:1874, before
truncated = depth_exhausted or seen_count >= max_nodes or unproven_total > max_nodes
```

**Three red runs (R6.5):**

```
1. the budget refusal removed (124's shape: rows plus a caveat)
   E  assert 'ok' == 'walk_budget_exhausted'
   E  KeyError: 'roots_reached'
   E  assert 5974 < 2000            # the payload is 3x the size of the refusal
2. the roots-matched-nothing refusal removed
   E  sqlite3.OperationalError: no such table: temp.reach_seen
3. refusing on the WHOLE of walk_truncated (Scope 1 read literally)
   E  the caller asked for a shallow walk and gets an answer     2 failed, 26 passed
```

**Red run 2 reproduces 187's crash verbatim** — the defect 185's parity matrix found. So this ticket
removes the crash from the tool path as a side effect of AC2; 187 is narrowed rather than closed,
because `store.find_orphans` still reads temps that `store.reachable_from` may not have created, and
any other `retain_temps=True` caller would hit it.

**AC7 — cost:** one `file_paths()` fetch shared by the walk's seeds and the root report; 20 refusals
under a 250 ms/call budget; and the refusal payload is **under 2 KB against ~6 KB for the row version
at this fixture's scale** — which at the field's 215,177 rows is the whole point of the ticket.

**Green run:**

```
$ .venv/bin/pytest -q
2442 passed in 146.93s
$ bash scripts/gate.sh
GATE GREEN — all 15 checks passed
```

**A pre-existing flake seen a second time in this batch and now FILED (190):**
`test_ac4_a_same_second_same_size_edit_is_a_stale_import` needs two writes inside one wall-clock
second and went red once under full-suite load, green alone and green in `gate.sh`'s own pytest run.
175 recorded the first sighting; two is enough evidence, so it is a ticket rather than a note.

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_a_budget_bound_walk_refuses_and_returns_no_rows`; red run 1 |
| AC2 | `test_roots_that_match_no_file_refuse_and_name_themselves`; red run 2 (187's crash) |
| AC3 | `test_a_complete_plausible_answer_is_byte_identical` — five fields asserted absent |
| AC4 | `test_nothing_orphaned_stays_distinguishable_from_cannot_tell` + `test_unset_roots_keep_their_own_status` (three failures, three names) |
| AC5 | the Scope 2 verdict above: the threshold rejected on 161 AC1 **and** shown unnecessary |
| AC6 | `test_the_two_numbers_that_separate_dead_code_from_wrong_roots` + `test_an_unmatched_root_is_named_even_on_a_complete_answer` |
| AC7 | `test_the_refusal_adds_no_walk_and_no_per_node_query` — one shared fetch, 20 calls timed, payload under 2 KB |
| AC8 | `test_the_refusal_is_deterministic`; `gate.sh` R1.1/R2.2 green; no `contract.py` edit ⇒ **no bump (R3), confirmed** — `status` is tool vocabulary, like `no_roots_configured` before it |
| — | `test_a_deliberately_shallow_walk_still_gets_its_rows` (the correction); `test_reachable_from_is_untouched` |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2429 passed / 0 failed` at `1796e0b` →
`2442 passed / 0 failed`. ruff + mypy green. `scripts/gate.sh` → `GATE GREEN`.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen >= 2 | 0 routed to a destination | 0 cannot promote (reason) | 1 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `prove-the-guard-fails` (R6.5) gains 182: three red runs, one of which reproduces another ticket's
  crash.
- **New:** `182-C1` (type-2, `publish-the-premise-not-only-the-complement`) — when a tool answers with
  a **complement** (orphans, unreachable, unused), the reader cannot judge it without the **premise**
  the complement was taken against. 215,177 orphans of 216,664 nodes is unreadable; *three root files
  reached a handful of nodes* is the same fact and immediately actionable. Publish what the premise
  reached, not only what it excluded. Corollary, learned the hard way here: **a flag that is the OR of
  several causes cannot be turned into a refusal** without splitting it first — one of the causes was
  the caller's own request. seen=1.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. Self-checks: a Scope-1
premise falsified by reading the source *before* implementing it (the literal reading would have
shipped a new defect, and red run 3 proves it); Scope 2's threshold rejected on a cited rule **and**
shown unnecessary; an added query caught by my own AC and removed; three red runs, one reproducing
187's crash; a second-sighting flake promoted from a note to a ticket; and the residual — a refusal is
not an answer — recorded so it is not read as progress.
