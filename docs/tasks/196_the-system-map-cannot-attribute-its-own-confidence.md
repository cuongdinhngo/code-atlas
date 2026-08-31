---
id: 196
slug: the-system-map-cannot-attribute-its-own-confidence
title: "The committable system map reports one blended confidence figure and cannot say which language earned it"
phase: 1.5b
milestone: Measure
status: done
depends_on: [195]
---

## Why this exists

[195](195_three-tools-still-read-the-whole-graph-blend.md) enumerated every consumer of the
whole-graph `edge_health()` aggregate and re-pointed the two it could: `find_orphans` and
`reachable_from` now carry the 183 per-language split beside the blend. The third consumer is
`code_atlas/tools/generate_onboarding.py:99`:

```
confidence = store.edge_health()["by_tier"]
```

It is a **genuinely whole-graph headline** — the artifact describes the whole repo — so the number is
right. It is also the one a human reads. PILLAR 2 exists so a person supervising an agent can see
what the code actually is, and on a two-language index the map's confidence figure is a blend that
names no language, which is round 12 §13's complaint pointed at the audience it matters most for.

## Why 195 did not do it

195's *Explicitly not in scope* is *"Any new aggregate. This re-points existing readers at an existing
stamp."* `confidence` is not a payload caveat: it is a field of the **versioned published dataset
schema** (`DATASET_VERSION`, currently 7 — `code_atlas/onboarding/dataset.py:45`), read by
`code_atlas/onboarding/headlines.py:186` and rendered by `code_atlas/onboarding/viewer.py:398`'s
JavaScript. Adding to it is a schema bump and a renderer change on a committed artifact, not a
re-point — a different ticket, deliberately.

## Scope

1. Carry the per-language split into the onboarding dataset from the **183 stamp**, not a second fold
   (195's Scope 3 and 183's own lesson: two folds stop summing to the whole).
2. Bump `DATASET_VERSION` and update the artifact/dataset conformance tests.
3. Render it where a human reads the confidence figure, so the map can say which language earned it.

### Explicitly not in scope

- `contract_version`. The adapter contract is untouched; `DATASET_VERSION` is not it
  (`dataset.py:11`).
- Any new *measurement*. The stamp already exists; this is a second reader of it.

## Constraints

- **183's arithmetic invariant** — the slices plus `unattributed` must equal the whole, pinned in the
  dataset as 195 pinned it in the payloads.
- **R5.6** — a pre-183 index has no stamp; the map must say so rather than claim one language.
- **R4.2** — identical graph ⇒ identical artifact bytes.

## Acceptance criteria

1. The dataset carries the per-language split, read from the stamp, and reconciles against the whole.
2. An index with no stamp renders the blend with the attribution **stated as unavailable**, not
   silently omitted and not invented.
3. `DATASET_VERSION` is bumped and the conformance tests move with it.
4. No `contract_version` bump.

## References

[195](195_three-tools-still-read-the-whole-graph-blend.md) (the enumeration and the deferral),
[183](183_edge-health-has-no-per-language-breakdown.md) and claim `183-C1`. Field retro round 12 §13.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 196 · **work_doc_mode:** embed · **Current phase:** 5 finalise — complete on disk.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** enhancement.
- Run arg: *"with skipped review"* = **reviewer seat only** (AGENTS.md as clarified in `cdd4a60`);
  the ticket-blind challenger keeps its seat.
- Contract: `.mango/run-contract-196.txt`; t0 RECONCILE ran all 5 bound conditions **BROKEN**, none
  struck.

## Phase 0 — refine

`PREMISE: 9 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 5 by handle | 0 by area | 0 by finding | 7 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 3 want-decision asked | 4 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise drift, recorded not blocking.** Every referenced identifier resolves, but three of the
ticket's *stated values* have moved since it was written: `DATASET_VERSION` is **9**, not the 7 the
ticket names (`dataset.py:56`); `generate_onboarding.py:99` is now `:103`; `viewer.py:398` is now
`:406`. 197 and 198 both bumped the version after 196 was filed. This is drift in a value, not a
falsified premise — the identifier is what the check resolves, and all nine resolve.

**The exposure-checker earned its dispatch.** It found a **third** human-facing render site this
session's own enumeration had missed — `viewer.py:757`, the *"What this page cannot tell you"*
caveats bullet, which prints the same `pct(HEUR, CONF)` figure as the stats row at `:426` for a
different purpose. A two-site plan would have shipped an attribution that contradicts the limits
card standing beside it.

**Settled wants — all three handed back by the maintainer** (*"you have my approval to choose the
best approach"*), so each is recorded `ASSUMED (awaiting ratification)` per refine step 4, not as a
settled fact.

| # | The want | Chosen direction | Status |
|---|----------|------------------|--------|
| W1 | Which of the three human-facing confidence sites get the attribution? | **One new `confBy` slot in `#overview`, and nothing else.** Not the stats row (`:426`), whose job is the figure; not the caveats bullet (`:757`), which states a limit; not `headlines.py`, whose cards compete for a scored slot budget 198 has just re-costed. One slot, always rendered, is the whole of AC2's *"stated, not omitted"* | ASSUMED |
| W2 | Does the map suppress a single-bucket split the way `get_index_status:283` does? | **No suppression.** 061's byte-parsimony reasoning is about a payload an agent parses; this is a committed document a human reads, and *"every dependency here is one language"* is a coverage fact a newcomer otherwise has to infer. A deliberate divergence from PILLAR 1's tool, on PILLAR 2's audience | ASSUMED |
| W3 | What does a present-but-degenerate stamp render? | **The reconciliation decides it, not a bucket count.** The split is rendered only when its tier sums equal the whole; otherwise the slot states it cannot attribute and why. One rule covers the empty stamp, the thin stamp and the detectable half of the stale stamp | ASSUMED |

**Resolved + cited.**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| H1 | Where does the split come from? | The **183 stamp**, never a second fold | ticket Scope 1; `store.py:744` docstring; P7 |
| H2 | Which version moves? | `DATASET_VERSION` **9 → 10**; `contract_version` untouched | ticket *Explicitly not in scope*; `dataset.py:11` |
| H3 | Raw stamp dict, or a typed shape? | **Typed frozen dataclasses**, like every other dataset field | `dataset.py:161-185`; `dataset_json` sorts keys (R4.2) |
| H4 | Does a stale stamp need its own caveat? | **No new mechanism.** Every other `generate_onboarding` field is read live; the ticket forbids a second measurement. The reconciliation catches the detectable half; the rest is an inherited limit, disclosed | `generate_onboarding.py:103-106`; ticket *Explicitly not in scope*; 195's own DISCLOSURE |

## Phase 1 — analysis

`SECTIONS: 7 found (Why this exists · Why 195 did not do it · Scope · Explicitly not in scope · Constraints · Acceptance criteria · References) | 7 decomposed | ROWS: C=3 R=5 G=2 AC=4`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`BASELINE: green — 2646 passed in 151.12s`
`TRACK: backend — 0/7 touched files under UI paths`
`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §1 (change-type) ✅ · §2 (change-type) ✅ · §3 (change-type) ✅ · §4 (change-type) ✅ · §5 (change-type) ✅ · §6 (change-type) ✅ · §7 (change-type) ✅`

```
Ran at 3880beff5c8ab4a56d9df3005e3b08b21750cd2c
$ .venv/bin/pytest -q
2646 passed in 151.12s (0:02:31)
RC=0
```
The branch point, bare `pytest` on the Linux dev host. §8 is **N/A because** the change adds no dependency: every import is stdlib or already inside
`code_atlas.onboarding`.

- §1 ✅ R1.4 — the one new store read sits in `generate_onboarding.py` beside the blend it attributes;
  `dataset.py` gets rows, never a connection. R1.1 — no language name is written anywhere in the
  core; every bucket key comes from the stamp.
- §2 ✅ the split's keys are whatever the index measured. The tests use the `fake`/`second` fixture
  adapters (`tests/fixtures/adapter/fake_adapter.py`), never a real language name.
- §3 ✅ `contract.py` untouched — AC4. `DATASET_VERSION` is the dataset's own version (`dataset.py:11`).
- §4 ✅ R4.2 — the split is a sorted fold over a stamp already on disk; identical graph, identical bytes.
- §5 ✅ R5.6 — three states, one of which explicitly says *cannot attribute*, and none of which invents
  a language.
- §6 ✅ R6.5 the proving test is shown red first; R6.9 the render is proven through
  `viewer_dom_stub.js` under `node`, because a grep over the HTML sees zero rendered figures.
- §7 ✅ R7.2/R7.6 — BACKLOG, frontmatter, ledger; and `PLAN.md:637` stops re-listing a
  `DATASET_VERSION` value that `dataset.py` owns (R6.7's `derived-not-listed-invariant`).

**AC validation — one value re-derived and corrected.**

| AC | Ticket's value | Computed here | Verdict |
|----|----------------|---------------|---------|
| AC1 | *"reconciles against the whole"* | per-tier sum over every bucket == `confidence[tier]` | falsifiable as written |
| AC2 | *"stated as unavailable"* | a named string present in the rendered slot | falsifiable as written |
| AC3 | *"`DATASET_VERSION` is bumped"* — body says "currently 7" | **9 → 10**; `dataset.py:56` reads 9 | ticket's stated value stale; target pinned |
| AC4 | *"No `contract_version` bump"* | `contract.py` absent from the diff | falsifiable as written |

All four falsifiable; **0 manual-check exclusions**.

**Clarifications, all four self-resolved.** (1) AC3's stale "7" → **9 → 10**, `dataset.py:56`.
(2) raw dict or typed shape → typed, `dataset.py:161-185`. (3) does `contract_version` move → **no**,
ticket *Explicitly not in scope*. (4) is summing the stamp "a second fold" → **no**: Scope 1 forbids
re-deriving the split with a second `GROUP BY`; C1 *requires* the arithmetic over what the stamp
already holds.

## Phase 2 — design

`HANDLES: 5 recalled | 5 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Handles — every recalled type-2 class, answered with a command

| handle | verdict | command + result |
|---|---|---|
| `attribute-the-aggregate-do-not-replace-it` (195) | **traced** | `git grep -n 'edge_health()' -- code_atlas/` → 4 readers: `find_orphans.py:114`, `generate_onboarding.py:103`, `get_index_status.py:245`, `reachable_from.py:55`. Three already carry the split; `:103` is the one 195 deferred here. The blend **stays** — this attributes it, never replaces it |
| `version-the-document-that-moved` (197) | **traced** | `git grep -n DATASET_VERSION -- code_atlas/ tests/ docs/` → one **hard** pin, `tests/test_onboarding_dataset.py:326` (`== DATASET_VERSION == 9`); two soft pins in `test_onboarding_viewer.py:165,259` compare to the constant and need no edit; `docs/PLAN.md:637` states a stale literal `7`. All folded in as proof collateral |
| `assert-the-consumer-not-the-field` (198) | **traced** | `git grep -n 'HEUR' -- code_atlas/onboarding/viewer.py` → `:426` stats row, `:757` caveats bullet — the two places the number reaches a human, plus `headlines.py:120-129`. The proving test asserts the **rendered** slot through `viewer_dom_stub.js`, never the dataclass field |
| `stamp-at-the-builder-not-the-wrapper` (162) | **traced** | `git grep -n 'stamped at the builder' -- code_atlas/` → `dataset.py:450` (197's flows). The split is built the same way: inside `build_dataset`, so no renderer re-derives a second notion of it |
| `empty-seam-inputs-masquerade-as-missing-data` (118) | **traced** | `git grep -n 'is None' -- code_atlas/onboarding/dataset.py` → only `:419`'s refiner default. The new field is **never `None`**: it is always a `ConfidenceSplit`, whose `available: False` states the absence rather than encoding it as a missing key — which is exactly what 118 was |

### Approach

`store.stamped_edge_health_by_language()` is read in `generate_onboarding.py` beside the blend it
attributes and handed to `build_dataset` as a keyword-only argument. The builder folds it into one
new typed field:

```
ConfidenceSplit(rows: tuple[LanguageConfidence, ...], available: bool, note: str)
LanguageConfidence(language: str, tiers: tuple[KindCount, ...], linked: int, unlinked: int)
```

`available` is **not** "a stamp was found" — it is "the split's per-tier sums equal `confidence`".
That single predicate answers three of the four states the exposure-checker enumerated: no stamp,
an empty or thin stamp, and the detectable half of a stale one. When it is false the slot says so
and names the reason; it never renders a language that cannot account for the number beside it.

One new viewer slot, `confBy`, in `#overview`. Always rendered, three readings: the per-language
split; *"attribution unavailable — this index predates the per-language stamp"*; or
*"attribution unavailable — the recorded split does not reconcile against this graph"*.

### Rejected alternatives

1. **Attribute inside the stats row and the caveats bullet** (`:426` / `:757`). Rejected: the same
   fact rendered twice in two regions with different jobs, and R7.6's duplication rule applies to a
   rendered document as much as to a doc. One slot, referenced from nowhere, is smaller and cannot
   drift against itself.
2. **Extend the `confidence` headline** (`headlines.py:186`). Rejected: headlines are ranked against
   a scored slot budget 198 has just re-costed; widening the sentence changes the 117 prose seam's
   input and competes for a card a newcomer needs for something else.
3. **Recompute the split live with `edge_health_by_language()`.** Rejected: that is the second fold
   Scope 1 and P7 forbid, and it puts a `GROUP BY` back on the answer path the stamp exists to keep
   it off.
4. **Suppress below two buckets, as `get_index_status:283` does.** Rejected: see W2 — 061 optimises
   a payload's bytes, and this is a document whose reader benefits from the single-language fact.

### Assumptions

| # | Assumption | Tag |
|---|------------|-----|
| A1 | `_tier_block` uses one fold rule for the whole and for every slice, so the sums are comparable | **verified** — `store.py:660-670`, and `test_edge_health_per_language.py:99` already asserts it in the payloads |
| A2 | Two fixture adapters can build a two-language index inside a test | **verified** — `tests/test_edge_health_per_language.py:38-46` does exactly this |
| A3 | A new keyword-only parameter with a default keeps every `build_dataset` call site green | **verified** — 197 did the same for `flow_edges`; 6 call sites, traced below |

No `novel-untested` third-party or runtime assumption remains.

### Change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|--------|-------------|--------------|----------------|-----|
| 1 | `LanguageConfidence` + `ConfidenceSplit`; `confidence_by_language` field; `as_dict` key; `__all__`; `DATASET_VERSION` 9 → **10**; the version comment extended past 7 | `code_atlas/onboarding/dataset.py` | **6** `build_dataset` call sites (`git grep -c 'build_dataset(' -- code_atlas/ tests/`) — keyword-only with a default keeps all 6 green; `quality_gate.check_dataset` reads the shape | R1, R2, C1, C2, AC1, AC2, AC3 | 1/7 |
| 2 | read the stamp beside the blend; pass it in | `code_atlas/tools/generate_onboarding.py` | the only new store read; no new SQL, no new query | R1, AC1 | 2/7 |
| 3 | `<p class="sub" id="confBy">` in `#overview`; the JS that fills it | `code_atlas/onboarding/viewer.py` | `SECTION_OF.overview` in the DOM stub must gain `confBy` or the render is never observed — R6.9 | R3, AC1, AC2 | 3/7 |
| 4 | proof collateral: the hard version pin 9 → 10 | `tests/test_onboarding_dataset.py:326` | — | AC3 | 4/7 |
| 5 | proof collateral: `SECTION_OF.overview` += `confBy` | `tests/viewer_dom_stub.js:72` | — | AC1, AC2 | 5/7 |
| 6 | the new suite | `tests/test_map_confidence_attribution.py` | — | AC1–AC4 | 6/7 |
| 7 | BACKLOG row + frontmatter `done`; ledger row; LESSONS entry; `PLAN.md:637` drops the stale literal version | `docs/` | tier-1 budget; `test_doc_size_budget.py`, `test_backlog_bookkeeping.py` | R7 | 7/7 |

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | integration — build a two-adapter index, generate the map, assert the split and its arithmetic | n/a | ✅ |
| AC2 | integration | integration — render with no stamp, assert the **rendered** slot states unavailability | n/a | ✅ |
| AC3 | logic | unit — the version pin | n/a | ✅ |
| AC4 | logic | unit — `contract.py` absent from the diff, `contract_version` unmoved | n/a | ✅ |

No `❌`. Every AC names its own expected value, so none is input-shape-dependent and no corpus is
wanted (`config.real_corpus_path` is `null` in any case).

### Proving test

`tests/test_map_confidence_attribution.py::test_the_map_names_the_language_that_earned_the_figure`
— builds a two-language index from the `fake`/`second` fixture adapters, generates the map, runs it
under `tests/viewer_dom_stub.js`, and asserts the `overview` section names **both** buckets beside
the confidence figure. Red before the change (no field, no slot); green after.

```
.venv/bin/pytest tests/test_map_confidence_attribution.py -q
```

### Rollback + porting

Revert the branch. Every element is additive: a new dataclass, a new keyword-only parameter with a
default, a new HTML slot. `DATASET_VERSION` returns to 9 with it. One repo (`config.repos` has a
single entry), so there is no porting order.

`SCOPE: M` — unchanged from analysis. 7 change-list items, one new file, no new seam, no new
dependency.

## Phase 3 — execute

**Verification sweep — both axes.**

*Axis 1, file set.* The realized diff is 10 files; every one traces to a change-list row and no file
sits outside it.

```
Ran at 2718dada595fbe46dff2468b15ccbc749abe35d8
$ git diff --stat main..feat/196-map-confidence-attribution
 code_atlas/onboarding/dataset.py            | 105 ++++++++++++++-
 code_atlas/onboarding/viewer.py             |  13 ++
 code_atlas/tools/generate_onboarding.py     |   3 +
 docs/BACKLOG.md                             |   2 +-
 docs/PLAN.md                                |   2 +-
 tests/test_map_confidence_attribution.py    | 180 ++++++++++++++++++++++++
 tests/test_onboarding_dataset.py            |   8 +-
 tests/viewer_dom_stub.js                    |   2 +-
```

*Axis 2, design conformance.* Every Gate-2 Approach bullet is `implemented-as-approved` except the
two deviations recorded below. No bullet was implemented differently and left unrecorded.

**Delta-green.**

```
Ran at 2718dada595fbe46dff2468b15ccbc749abe35d8
$ .venv/bin/pytest -q
2656 passed in 146.55s (0:02:26)
$ bash scripts/gate.sh
  17 passed · 0 failed · 0 skipped
GATE GREEN — all 17 checks passed
```
Baseline was 2646; the ten new tests are this ticket's. The suite ran on the **code** tree of
`2718dad`; the only files carrying uncommitted edits at that moment were `docs/LESSONS.md`,
`docs/TOKEN_LEDGER.md` and this working doc, none of which any behavioural test reads.

### The two negative controls (R6.5)

Both were observed red, and the first is the more interesting.

**Control 1 — revert the renderer, keep the field.** `git stash push code_atlas/onboarding/viewer.py`
leaves `confidence_by_language` fully populated, correct, and asserted by eight tests. Result:
**8 passed, 2 failed** — both render assertions, neither field assertion.

```
FAILED tests/test_map_confidence_attribution.py::test_the_map_names_the_language_that_earned_the_figure
FAILED tests/test_map_confidence_attribution.py::test_ac2_the_unavailable_statement_reaches_the_rendered_page
2 failed, 8 passed in 0.69s
```

That is 198's shipped defect reproduced on purpose: a field wired, tested and green, with no reader.
The eight field-level tests are exactly the suite that would have let it ship.

**Control 2 — remove the reconciliation comparison.** Deleting the two lines that compare the tier
sums turns the stale-stamp refusal into an acceptance:

```
FAILED tests/test_map_confidence_attribution.py::test_ac2_a_stamp_that_does_not_add_up_is_refused_rather_than_shown
1 failed, 9 passed in 0.69s
```

### What the gate caught that the blast-radius trace did not

The trace grepped `DATASET_VERSION` and reported every pin folded into the change list. The gate
failed on a **fifth** pin the trace could not see, because it is written as a bare literal:

```
      >       assert payload["version"] == 9
      E       assert 10 == 9
      tests/test_onboarding_dataset.py:316: AssertionError
```

Its own docstring still read *"the key is present at DATASET_VERSION 8"* — it had gone stale through
two bumps. Fixed by pinning against the **constant**, not by writing a third copy of the number: that
test is about `flows`, and the version has a test of its own. Recorded as `196-C6`, a ninth sighting
of `count-pin-in-blast-radius` (AGENT_BRIEF P5).

### Deviations from the approved change list

| # | Deviation | Why | Trace |
|---|-----------|-----|-------|
| D1 | Change-list item 4 said *"the hard version pin 9 → 10"*, singular. Two pins in that file moved, and the second was **converted to the constant** rather than bumped | The literal pin is the defect, not its value; bumping it would leave the same trap for the next bump | item 4, AC3 |
| D2 | `docs/LESSONS.md`'s class index gained **three** rows beyond this ticket's own claims — `deepest-wins-is-not-a-membership-test` (rec 3), `assert-the-consumer-not-the-field` (2) and `version-the-document-that-moved` (2) | The table states it holds *"every type-2 handle at recurrence ≥ 2"* and held none of the three; a script over the file's own `seen:` lists found them. `deepest-wins-is-not-a-membership-test` has been due promotion since 197 with nothing surfacing it, **because** it was never entered here | item 7, R6.7 |

### A process defect in this run, not in the change

Restoring after control 2 with `git checkout code_atlas/onboarding/dataset.py` deleted **all seven**
uncommitted edits to that file — a negative control runs on an uncommitted tree, so the command that
undoes the control also deletes what it was controlling. Rebuilt from the edit script and re-verified;
filed as `196-C3`. Control 1 used a backup copy and had no such exposure.

## Phase 4 — review

Reviewer seat **waived** by run arg; the ticket-blind challenger ran and returned
**8 met · 1 met-with-a-caveat · 0 not met · 0 can't-tell**, with four findings. All four were
actioned; two of them were real gaps, not polish.

### F1 — "read the stamp, never a second fold" was enforced by nothing but my own reading

The requirement the ticket is most explicit about (*Explicitly not in scope*: "Any new
*measurement*") had **no test behind it**. Every scenario builds the index once, so the persisted
stamp and a live re-fold are byte-identical and no assertion can tell them apart. The challenger
named the exact mutation: swap `stamped_edge_health_by_language()` for `edge_health_by_language()`
at `generate_onboarding.py:105` — 15 tests, all green.

The guard doctors the stamp's language **names** while leaving its arithmetic intact, so the split
still reconciles and is still shown, but can only carry those names if it was read rather than
recomputed. Observed on the mutation:

```
FAILED tests/test_map_confidence_attribution.py::test_the_split_is_read_from_the_stamp_and_not_recomputed_from_the_graph
1 failed, 14 passed in 1.10s
```

This one matters beyond the AC. `MISMATCH_NOTE` exists to catch a stamp that has drifted from the
live graph — and a live re-fold **can never drift**, so the mutation would have quietly disabled the
refusal this whole design turns on, while every test stayed green.

### F3 — I shipped two fields nobody reads, in the same change that guards against exactly that

`LanguageConfidence.linked` / `.unlinked` were populated from the stamp and serialized into the
published shape, and no renderer read either. That is 118's and 198's defect class, committed by the
change whose own proving test is a negative control for it. They are pruned: `linked`/`unlinked`
answer *did the edge resolve a name*, which is a different axis from *which tier earned it*, and
this ticket is about the second. The shape is smaller, and `DATASET_VERSION` was already moving.

### F2 and F4 — cheap, so closed rather than argued

F2: only `NO_STAMP_NOTE` was proven to reach HTML; the other two refusals were asserted at the
return value. Now parametrized over all three. F4: the per-language `% below exact` was never
asserted, so swapping `pct(heur, all)` would have rendered a wrong number every test accepted.
Observed on that mutation:

```
FAILED tests/test_map_confidence_attribution.py::test_the_rendered_share_is_the_heuristic_share_of_that_language
1 failed, 14 passed in 1.09s
```

### What the challenger did not find

No scope creep, no `store.py` or `contract.py` diff, no language branch, no non-determinism. It ran
the suite itself under real `node` rather than trusting a test name — which is the check that makes
its verdict on the render path worth anything.

## Phase 5 — finalise

`CLAIMS: 8 claim(s) from 1 lesson entr(ies) | T1=0 T2=8 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 3 recurring | 1 superseded (0 retired) | 3 promotion candidate(s)`
`FALSIFY: 6 candidate(s) checked | 6 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 3 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 2 cannot promote (reason: promotion is /mango:promote's human-gated decision, and autorun may not take it) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured (host surfaces no usage block) · top cost driver: main-loop execute · 2 subagent dispatch, 158.6k measured`

**The six falsify candidates** are design's three assumptions (A1 the shared fold rule, A2 the
two-adapter fixture, A3 a defaulted keyword-only parameter) and the three `ASSUMED` wants (W1 one
render slot, W2 no single-bucket suppression, W3 reconciliation as the gate). All six survived the
challenger; none was falsified, and the challenger explicitly agreed with W3's direction by calling
the arithmetic gate structural rather than presence-based.

**The three recurring classes** are `count-pin-in-blast-radius` (9 — already binding as
AGENT_BRIEF P5, so routed, not a candidate), `assert-the-consumer-not-the-field` (2) and
`version-the-document-that-moved` (2). The third promotion candidate is not this ticket's:
`deepest-wins-is-not-a-membership-test` reached recurrence 3 at 197 and had never been entered in
the class index, which is why nothing surfaced it as due. It is entered now.

**Promotion is not this run's to make.** `PROMOTION` is all zeros because promoting a class is
`/mango:promote`'s decision with a human at the gate, and `autorun` may not take it. The three
candidates are recorded where that command reads them.

### DISCLOSURE

**The reviewer seat was OFF** (waived by the run arg `with skipped review`). **The ticket-blind
challenger seat was ON**, ran once, and returned four findings — two of them real gaps that a fully
green 15-test suite did not see. A morning reader should read this as *"clean, the blind reviewer
looked; the rule-book reviewer did not."*

Unverified or deliberately not done, in full:

- **Main-loop token spend is unmeasured.** The host surfaces no usage block, so only the two
  subagent dispatches are counted. The call-count ceiling was recorded `unknown` at t0 rather than
  invented, because `budget.py ceiling` returned `unknown` for this tier's rows.
- **A stale stamp that still reconciles is undetectable here** and is knowingly shipped that way.
  The tier sums catch a stamp whose numbers moved; a stamp written by an earlier build whose totals
  happen to match still renders. Detecting it needs the second fold the ticket forbids. This is
  195's inherited limit, not a new one.
- **AC4 could not be a contract condition.** "No `contract_version` bump" is green on an empty run,
  so the strike rule would have removed it — a condition that HOLDS before any work describes
  something other than the work. It is proven by a test and by the diff instead.
- **`_confidence_split` is exercised end-to-end for two of its four returns.** The `available` path
  and `NO_STAMP_NOTE` run through a real index and a real `node` render; `MISMATCH_NOTE` and
  `NO_EDGES_NOTE` reach HTML through a constructed `ConfidenceSplit`, not through the fold. The
  renderer branches once on `.note`, so the risk is low — but it is not the same proof.
- **The exposure-checker and the challenger were given filtered inputs by hand.** `work_doc_mode` is
  `embed`, so the working doc ships inside the ticket file and inside the diff; the challenger was
  handed an extracted raw ticket and a diff with the working doc, `LESSONS.md` and `TOKEN_LEDGER.md`
  removed. Its independence statement confirms it read none of them — but the mitigation is manual
  and would not survive a less careful run. Already filed as a type-3 skill gap at 197.
- **Two deviations from the approved change list** (D1, D2 above) and **one process defect in this
  run** (`git checkout` deleting seven uncommitted edits, `196-C3`).
