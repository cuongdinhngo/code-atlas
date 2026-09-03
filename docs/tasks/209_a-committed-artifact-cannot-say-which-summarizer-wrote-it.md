---
id: 209
slug: a-committed-artifact-cannot-say-which-summarizer-wrote-it
title: "A committed artifact cannot say whether its summaries came from an LLM or from the structural fallback, so `No leading doc comment above the indexed declaration in this file.` reads as a fact about the repo when it is a fact about the run"
phase: 3
milestone: M12
status: done
depends_on: [085, 090, 117, 118, 205]
---

## Why this exists (measured on the anchor monorepo, 2026-09-02)

`generate_onboarding` takes a `Summarizer` and defaults it to the deterministic one
(`code_atlas/tools/generate_onboarding.py:64`):

```python
seam: Summarizer = StructuralSummarizer() if summarizer is None else summarizer
```

An MCP caller cannot pass one, so every artifact generated through the server is written by
`StructuralSummarizer`. On the anchor — pre-204 index, `max_results = 10` — **not one of the 500
pages carries a usable summary**. They
fail in two shapes: 277 render the honest sentence,

```
No leading doc comment above the indexed declaration in this file.
```

and 201 more render a bare comment delimiter — `/**` on 186 of them, `/*`, `/*!` or `*/` on the rest —
presented in the same `## Summary` position as though it were prose. Roughly two pages in five
hundred carry a sentence that describes their file.

The honest sentence is true. It is also, to a reader, indistinguishable from two very different
worlds:

1. this repo's code carries no doc comments — a finding about the codebase;
2. the artifact was generated without the LLM seam configured — a finding about the run.

The artifact states neither. A person reading `docs/onboarding/` six months from now, or an agent
grepping it, has no way to tell which they are looking at. This is **R5.6** — never attest past what
the payload can distinguish — in the one artifact whose whole audience is a human.

### The figures move with the index, so a page census must name one

Regenerating against a 204-corrected index changes the split substantially:

| | pre-204 | post-204 |
|---|---|---|
| pages rendering the fallback sentence | 277 | **412** |
| pages rendering something else | 223 | 88 |
| of those, a bare comment delimiter | 201 | 75 |

Docline coverage gets **worse**, and that is not a regression: 204 correctly promotes undocumented
`legacy/` modules into the page set and demotes the documented framework trees that false JavaScript
edges had been holding up. A truer ranking with less prose in it.

Two consequences for this ticket. Any figure it pins must name the index it came from — the numbers
above are the two that exist today. And the defect gets *worse* as the graph gets *better*: at 412
of 500 the artifact is approaching the state where the only thing a Summary section ever says is
that it has nothing to say, which is exactly when a reader most needs to know whether that is the
repo talking or the configuration.

### The provenance exists, and stops at the tool response

`_payload` at `code_atlas/tools/generate_onboarding.py:291` does carry the fact, at
`detail_level: standard`:

```python
payload["prose_calls"] = prose.calls
payload["prose_declined"] = prose.declined
```

Two problems. It describes the **117 prose seam**, not the **085/090 summarizer** that wrote those
lines; and it is in the *MCP response*, which is discarded, rather than in the *committed artifact*,
which is kept. The committed tree is what gets read later, and it is the one without the stamp.

The code even records why: *"Not in the dataset on purpose: a number that moved when the seam turned
on would break AC2."* That reasoning is sound for a **cost count** and is the tension this ticket has
to resolve, not override — see Constraints.

### Why this ranks above building anything new

The repo already owns the whole seam: `Summarizer` Protocol (085), an LLM implementation (090/091),
prose for the map (117), the `llm = ["anthropic>=0.69"]` optional dependency, a separate
`onboarding_llm` package and a `code-atlas-llm` entry point. **Nothing needs to be built to get
better summaries — the seam needs to be reachable, and the artifact needs to say which side of it
produced the text.** An evaluation of the artifact's quality that does not first establish which
summarizer ran is measuring a configuration, and this ticket is what makes that distinction
recordable.

## Scope

1. **Stamp the summarizer and prose implementation into the committed artifact**, by identity — not
   by call count. `overview.md` says which produced its text; the dataset carries the same field so
   the viewer and any agent read one fact (**R1.8**).
2. **Make the fallback sentence name its own cause.** `StructuralSummarizer`'s no-docline text
   distinguishes "this declaration has no doc comment" from "no summarizer beyond the structural one
   ran", because those are different sentences and only one is about the repo.
3. **A documented, reachable path to run with the LLM seam on**, from the CLI and from the MCP
   server, with what it costs. Today `summarizer=` is a Python keyword argument with no route
   through either surface — an implemented seam nobody can switch on.
4. **Measure both artifacts on the anchor and record the delta** — pages changed, summary lines that
   stopped being the fallback sentence, cost. That number is what decides whether the seam is worth
   a consumer's tokens, and no such measurement exists.

### Explicitly not in scope

- **Writing a better summarizer.** 090/091 exist. This ticket makes them reachable and their use
  visible.
- **Turning the seam on by default.** **R4.1** stands: the core stays LLM-free, the seam stays
  opt-in, and CI never needs a key.
- **Page count, page selection, or the orientation section.**
  [205](205_a-module-page-per-node-budget-slot.md), [206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md),
  [207](207_the-artifact-answers-no-question-a-newcomer-asks-first.md).

## Constraints

- **R4.1** — no LLM or network in the core, ever. The stamp is written by the core; the summarizing
  is not.
- **117's AC2** is the live tension: a *count* that moves when the seam turns on would break it. A
  *provenance identity* is a different register (**R5.4** — the field the reader acts on holds one
  register, prose gets a sibling). Resolve it explicitly in the design and say which reading of AC2
  survives; do not quietly widen it.
- **R3.5** — a dataset field is a schema move: bump `DATASET_VERSION`, move the viewer with it.
- **R4.2** — for a fixed summarizer, output stays byte-identical. The stamp is a function of the
  configuration, not of the wall clock.
- **R6.9** — the guard asserts on the emitted `overview.md`, not on a payload dict.

## Acceptance criteria

1. A committed artifact names the summarizer and prose implementation that produced it, in
   `overview.md` and in the dataset.
2. A no-docline summary line distinguishes an absent doc comment from an absent summarizer.
3. The LLM seam is selectable from the CLI and from the MCP server, and the path is documented in
   `TOOLS.md` with its cost.
4. Two artifacts generated on the same index with different summarizers differ in their stamp, and a
   test pins that; two generated with the same summarizer are byte-identical.
5. The anchor delta from Scope 4 is recorded in the ticket close-out with real numbers.
6. CI needs no API key and exercises the deterministic path unchanged.

## References

[085](085_onboarding-summarizer-seam.md) (the seam), [090](090_llm-summarizer-impl.md) and
[091](091_llm-layer-refinement.md) (the implementations nobody can reach),
[117](117_llm-prose-for-map.md) (the prose seam and the AC2 this must reconcile),
[118](118_module-summary-seam-gets-empty-facts.md) (why the fallback sentence is so common),
[205](205_a-module-page-per-node-budget-slot.md) (the page census these figures come from).

---

## Working doc (autorun 2026-09-04)

**KEY:** 209 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **reviewer:** OFF (`--no-reviewer`) · **challenger:** ON

### Phase 0 — refine

`PREMISE: 13 reference(s) checked | 1 missing | 1 ambiguous (surfaced, not blocking)`
`PREMISE FALSIFIED: 1 referenced-as-existing source(s) missing — the sentence "No leading doc comment above the indexed declaration in this file." (the ticket title, and Scope 2 which asks to reword it)`
`RECALL: 6 claim(s) surfaced | 0 by symbol | 5 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 6 unresolved surfaced | 1 want-decision asked | 5 how-decision resolved+cited | 0 ASSUMED | skip: no`

**The ticket's central artifact does not exist any more.** `grep -rl 'No leading doc comment' code_atlas/`
returns nothing: 205 removed the per-module page tree, and the 412 pages that rendered the sentence
went with it. `tests/test_module_facts.py:80` already asserts `"No leading doc comment" not in tour`.
So **Scope 2 has no sentence to reword** — see AC2 below for how it is discharged rather than skipped.

**Two more of the ticket's premises are false**, both recorded under `FALSIFY` in Phase 5: the LLM
seam *is* reachable (`code-atlas-llm` + `CA_ONBOARDING_SUMMARIZER=llm`), and `docs/TOOLS.md`'s
"33 calls per build" understates the real cap by 12 and attributes a prose-only ceiling to all
enrichment.

**The one want-decision** — *does 209 still ship with its headline defect already closed by 205?* —
was **answered by the operator's standing delegation** ("make the necessary decisions… complete the
work autonomously"), not assumed. Answer: **yes**. Scope 1 (the stamp) is untouched by 205, is the
part the ticket calls load-bearing, and is what AC1/AC4 test. This is disclosed as the run's single
delegated product decision.

How-decisions, each cited:
1. **Stamp all three seams, not the two the ticket names.** R1.8 — one derivation site; layer names
   (091) are equally seam-written and would otherwise keep the same defect. Cost: one field.
2. **The stamp reads the object that ran, not the config that asked.** LESSONS 201-C2. Both
   defaults now resolve in `generate_onboarding.create`, so the effective refiner is nameable.
3. **`ProseRun` exposes the writer object, not a name.** `prose.py`'s docstring forbids importing
   `code_atlas.onboarding`, so a `"none"` spelled there would be a second copy of the sentinel.
4. **The section goes at the END of `overview.md`.** It is provenance, and 207 owns the top.
5. **The `DATASET_VERSION` pin stays EXACT (`== 12`), not `>=`.** P5 — the pin's whole value is
   tripping on the next field-add. 196 relaxed a *different* pin (`>= 10`) whose job is a floor.

In-repo refs resolved: `generate_onboarding.py` seam default + `_payload`, `summary.py`
(`Summarizer`/`StructuralSummarizer`), `prose.py` (`ProseRun`, `SLOT_LIMITS`), `dataset.py`
(`DATASET_VERSION`), `viewer.py` `stampLine`, `onboarding_llm/server.py`, `pyproject.toml`
`llm = ["anthropic>=0.69"]`, `code-atlas-llm` entry point, `docs/TOOLS.md` LLM section, tickets
085/090/091/117/118/205, R4.1's CI grep gate. Ambiguous: the anchor's 500-page census (pre/post-204)
— another checkout, not this one.

Recalled (advisory): `label-what-ran-not-what-was-recorded` (201-C2), `count-pin-in-blast-radius`
(P5), `prove-the-guard-fails` (R6.5), `derived-not-listed-invariant` (R6.7),
`an-identity-must-be-comparable-against-what-produced-it` (175-C1); area: config / provenance.

### Phase 1 — analysis

`PREMISE: 13 reference(s) checked | 1 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 6 claim(s) surfaced | 0 by symbol | 5 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists · Scope · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=5 R=4 G=1 AC=6`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 9 applicable — 8 by change-type | 1 by recalled handle — §R1.8 (one place decides what an audience/stamp emits) ✅ · §R3.5 (dataset field ⇒ version bump + viewer) ✅ · §R4.1 (core imports no LLM) ✅ · §R4.2 (stamp is a function of configuration) ✅ · §R5.6 (never attest past what the payload distinguishes) ✅ · §R6.7 (derive the cost figure) ✅ · §R6.9 (assert the emitted markdown) ✅ · §R7.6 (prune as you add) ✅ · §R6.5 (prove the guard fails) ✅`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green — main at e052ffb, 2818 collected, 0 failed`
`SCOPE: M`
`TIER: full`

Clarifications, all self-resolved:
1. *Does the ticket still ship with AC2's subject gone?* — resolved: yes, see Phase 0.
2. *Does `artifact.json` need the stamp too, i.e. an `ARTIFACT_VERSION` bump?* — resolved: **no**.
   AC1 names `overview.md` and *the dataset*; the stamp is a dataset field, so `DATASET_VERSION`
   alone moves. Cited: AC1, R3.5.
3. *AC5's anchor delta?* — resolved as **E1**: `.harness.json` `real_corpus_path` is `null`.

| ID | Type | Statement |
|---|---|---|
| G | G | A committed artifact can say which side of the seam wrote its text |
| R1 | R | Stamp the summarizer and prose implementation by identity, in `overview.md` and the dataset |
| R2 | R | Make the no-docline line name its own cause |
| R3 | R | A documented, reachable path to run the seam on, with its cost |
| R4 | R | Measure both artifacts on the anchor and record the delta |
| C1 | C | R4.1 — no LLM/network in the core; the stamp is written by the core |
| C2 | C | 117's AC2 tension: a *count* that moves breaks it; an *identity* is a different register (R5.4) |
| C3 | C | R3.5 — bump `DATASET_VERSION`, move the viewer with it |
| C4 | C | R4.2 — byte-identical for a fixed summarizer |
| C5 | C | R6.9 — the guard asserts the emitted `overview.md`, never a payload dict |
| AC1 | AC | The artifact names the summarizer and prose implementation, in markdown and in the dataset |
| AC2 | AC | A no-docline line distinguishes absent doc comment from absent summarizer |
| AC3 | AC | The seam is selectable from CLI and MCP, documented in `TOOLS.md` with its cost |
| AC4 | AC | Different summarizers differ in the stamp; the same one is byte-identical |
| AC5 | AC | The anchor delta recorded with real numbers |
| AC6 | AC | CI needs no API key; the deterministic path is unchanged |

**C2 resolved explicitly, as the ticket demands.** The reading of 117's AC2 that survives is
*"no **count** in the dataset moves when the seam turns on"*. `provenance` is an identity, not a
count: it holds three class names and no tallies, and `prose_calls`/`prose_declined` stay in the MCP
response exactly where 117 put them. AC2 is not widened — a run with the seam **on** still writes a
dataset whose every number is seam-independent.

### Phase 2 — design

`HANDLES: 5 recalled | 5 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

Handle traces (command → result):
1. `count-pin-in-blast-radius` — `grep -rn 'DATASET_VERSION ==\|>=' tests/` → 2 pins
   (`test_onboarding_dataset.py:331` exact, `test_map_confidence_attribution.py:173` a floor);
   `grep -rn 'OnboardingDataset(' ` → 1 test constructor, keyword-only. Full suite then found a
   **third and fourth**: both core-module-count guards. **3 pins moved, all repaired**; the field is
   defaulted so no constructor breaks.
2. `label-what-ran-not-what-was-recorded` — mutating `implementation_name(seam)` to the literal
   `"StructuralSummarizer"` left 4 of 5 tests green; the swap test caught it. **Traced and pinned.**
3. `an-identity-must-be-comparable-against-what-produced-it` — the stamp's only mutable axis is the
   injected seam; nothing hashes env or bytes, so 175-C1's staleness trap cannot arise here.
4. `prove-the-guard-fails` — four mutants run, four caught (see Phase 3).
5. `derived-not-listed-invariant` — `MAX_PROSE_CALLS` is **45**, `docs/TOOLS.md` said **33**;
   6+12+15 = 33 is the pre-198 sum, so the figure went stale when 198 added the module slot. Fixed
   and guarded by `test_the_documented_prose_cap_is_the_real_one`.

**Exclusion (1, with a checkable expiry).** AC5's anchor delta is not measurable on this checkout:
`.harness.json` `real_corpus_path` is `null`. **Expiry: the first run after `real_corpus_path`
becomes non-null.** This is the class's **third consecutive sighting** (206 E1, 211 E1, 209 E1), so
it is **escalated, not re-recorded**: it is a harness-configuration gap the operator owns, and three
tickets have now shipped ACs unmeasured for the same single missing value. Escalation is in
`DISCLOSURE` line 5.

**Proving test:** `tests/test_provenance_stamp.py` (8 tests).

**Rejected alternative:** adding a `name` property to the `Summarizer` Protocol. It would force every
existing and future implementation to change (R1.2 — the seam is the one abstraction, and widening
it for a label the core can already read is a cost with no buyer). `type(obj).__name__` needs no
seam change and works for an impl the core has never seen.

### Phase 3 — execute

What landed:
- **`code_atlas/onboarding/provenance.py`** (new) — `Provenance` (three names) and
  `implementation_name`, the single derivation. `NONE` is the one spelling of "nothing injected".
- **`generate_onboarding.py`** — resolves the summarizer **and** the layer-refiner default at the
  tool, builds the `Provenance` from the effective objects, passes it to `build_dataset` and to
  `render_overview`.
- **`prose.py`** — `ProseRun.writer` exposes the injected writer object.
- **`dataset.py`** — `provenance` field (defaulted), `as_dict()` key, `DATASET_VERSION` 11 → 12.
- **`artifact.py`** — `H_PROVENANCE` + `_provenance_lines`, rendered at the end of `overview.md`.
- **`viewer.py`** — a `provLine` paragraph reading the same dataset field (R3.5's viewer half).
- **`docs/TOOLS.md`** — the stale "33 calls" replaced by a per-seam cost table (prose ≤ 45; layer
  names one, conditional; **summaries one call per tour module, uncapped by the seam and sized by
  `CA_IMPACT_MAX_NODES`**), plus where to read a committed tree's own stamp.

Mutants run, all caught: (a) `overview.md` stops rendering the section → 2 tests red; (b) the stamp
hardcodes the default name → the swap test red; (c) the viewer's `put` target renamed → red;
(d) the viewer's element removed → red. Mutant (b) is the one that matters: it is the exact defect
LESSONS 201-C2 describes.

**A green-by-construction guard was found and fixed in my own change.** The first viewer test
asserted the sentence appeared in the HTML — but the sentence lives in the embedded JS whether or
not the page ever displays it, so mutant (c) stayed green. Replaced with the two halves that make it
render: the `id="provLine"` element **and** a `put` targeting that exact id.

Verification: `scripts/gate.sh` → **GATE GREEN, 17/17, 0 skipped** on this Linux host (PHP present,
so `pytest` and the benchmark both ran). Full suite **2825 passed** against a 2818 baseline.

`diff ⊆` approved list: `provenance.py` (new), `dataset.py`, `artifact.py`, `viewer.py`, `prose.py`,
`generate_onboarding.py`, `test_provenance_stamp.py` (new), `test_onboarding_dataset.py`,
`test_core_is_language_agnostic.py`, `test_sql_confinement.py`, `docs/TOOLS.md`, this working doc,
BACKLOG, TOKEN_LEDGER.

**The benchmark is unmoved by this ticket, and that is checked rather than assumed.** No question in
`scripts/tokens_to_answer_questions.json` reads `overview.md`'s bytes — the five whose `atlas_path`
matches "overview" all call the `architecture_overview` **tool**. The gate's floors hold (recall 1.0,
precision 1.0, ratio 0.83 ≥ 0.63). `docs/benchmarks/121_*.md`'s table is a **dated** 2026-08-23
measurement whose figures already differ from today's for reasons predating 209; restating them here
would misdate them (R7.6), so it is left alone and flagged as its own job.

#### Acceptance criteria — close-out

| AC | Verdict | Evidence |
|---|---|---|
| AC1 | **MET** | `test_the_default_run_names_every_seam_in_the_committed_overview`, `test_the_committed_manifest_carries_the_same_stamp` |
| AC2 | **MET BY SUPERSESSION — not skipped** | Its subject was deleted by 205; `grep -rl 'No leading doc comment' code_atlas/` is empty and `test_module_facts.py:80` pins the absence. The cause AC2 wanted named is now named **once, globally**, in the provenance section — strictly better than repeating it on 412 pages. Nothing in the tree renders a no-docline *line* to distinguish. |
| AC3 | **PARTIALLY MET** | Cost + route now documented in `TOOLS.md`, and the MCP route already existed (`code-atlas-llm` + `CA_ONBOARDING_SUMMARIZER=llm`) — the ticket's "no route through either surface" is false for MCP. **The CLI half is N/A: no CLI writes the artifact.** `code-atlas-build` only builds the index (`cli.py:107-119` — `--status`, `--full`, nothing else). Adding an onboarding subcommand is a **new surface**, not a stamp; left out of the change list and surfaced to the operator. |
| AC4 | **MET** | `test_a_different_summarizer_changes_the_stamp_and_nothing_else_moves`, `test_the_same_summarizer_twice_is_byte_identical` |
| AC5 | **NOT MET — E1, recorded** | `real_corpus_path: null`. Third consecutive sighting; escalated, expiry recorded. |
| AC6 | **MET** | Every test uses a local `_ShoutySummarizer`; `anthropic` is never imported. `R4.1 no LLM in core` gate PASS. |

### Phase 4 — review

`reviewer`: **OFF** (`--no-reviewer`) — no rule-book-grounded review of this diff exists.
`challenger`: **ON** — ticket-blind, on the raw ticket text and `git diff main...HEAD`.

**Round 1: CHANGES REQUESTED.** 7 of 9 reconstructed requirements met; both NOT-MET findings traced
to one root cause — the viewer change and the whole close-out were still **uncommitted** when the
diff was reviewed, so `main...HEAD` showed a `provenance` field *populated, serialised and correct
with every renderer still printing the old one*, which is the R6.9 failure mode verbatim. Its
`git diff HEAD --stat` saw the filenames and correctly called it unfinished bookkeeping rather than
missing work. **Fixed by committing** — the viewer half and its element-plus-`put` guard are in the
reviewed tree from `Round 2` onward.

It raised one finding that was **not** just bookkeeping: the C2 / 117-AC2 resolution existed in this
working doc but nowhere a code reader would find it. A two-line comment now states the register at
the site that makes the choice (`generate_onboarding.py`, the `Provenance(...)` construction).

It also independently reached two of refine's conclusions without the ticket's framing: that AC3's
route **already existed** before this ticket ("worth a sanity check with the ticket author since it
undercuts the ticket's own framing"), and that stamping `layers` is beyond AC1's literal wording —
flagged, explicitly not blocked, which matches how it is recorded above.

**Round 2 (verify-only, same live seat): LGTM.**

### Phase 5 — finalise

`CLAIMS: 2 claim(s) from 1 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 4 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 4 candidate(s) checked | 1 still-true (proceed) | 3 falsified (BLOCKED) | 0 not cheaply checkable`
`RECURRING-T2: 4 type-2 claim(s) with seen ≥ 2 | 4 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`
`LEDGER TOTAL: unmeasured (host surfaces no usage block) · top cost driver: main-loop execute`

**`FALSIFY` reports 3 of the ticket's 4 checkable premises false.** The grammar labels that BLOCKED;
the harness declares no gate on it, and the ticket ships on its surviving premise — but a morning
reader should read this row first:
1. *"412 of 500 pages render the fallback sentence"* → **falsified**: 205 removed the pages.
2. *"`summarizer=` is a Python keyword argument with no route through either surface"* → **falsified**
   for MCP: `onboarding_llm/server.py:47-55` builds it from `CA_ONBOARDING_SUMMARIZER`.
3. *"spend is capped at 33 calls per build"* (`TOOLS.md`) → **falsified**: 45 since 198.
4. *"the provenance stops at the tool response"* → **still true**, and it is what this ticket fixes.

PR opened under the handover authorisation (push + open PR). The merge is authorised separately and
explicitly by the operator's same message and is taken outside the skill, which never auto-merges.

### RECONCILE + DISCLOSURE

```
RECONCILE
  conditions: 8 declared | 8 re-run | 8 holding | 0 BROKEN | 0 UNBOUND | 0 could-not-run
  phase     : close | reviewer: off | challenger: on
```

At **t0**, before any work existed, all 7 bound conditions were observed **BROKEN** against the real
world and none was struck — that is the part of this contract that earned its claim.

```
DISCLOSURE
  1a. REVIEWER: OFF — waived by `--no-reviewer`. No rule-book-grounded review of the diff ran; a
      clean result carries no reviewer finding because none was sought.
  1b. CHALLENGER: ON — the ticket-blind challenger ran (round 1 CHANGES REQUESTED, round 2 LGTM).
  2. UNCHECKED AGENT CLAIMS: 0 — every contract value was derived by a command.
  3. BUDGET: call-count ceiling 853 (proxy, per-call estimate 2344, source: budget.py over 4 ledger
     rows from 208/212, 138 calls total) — a proxy, not a measurement. Main-loop spend is the larger
     term and this host surfaces no usage block, so the run's true cost is unmeasured.
  4. This list is the ONE artifact nothing can check.
  5. ESCALATION — `.harness.json` `real_corpus_path` is `null`, and this is the **third consecutive
     ticket** (206, 211, 209) to ship an AC unmeasured for that one missing value. It is a
     harness-configuration gap the operator owns, not a per-ticket risk to re-record a fourth time.
  6. DELEGATED PRODUCT DECISION — refine raised one want-decision (*does 209 still ship with its
     headline defect already closed by 205?*) and nobody was awake to answer it. It was **not**
     silently adopted as an ASSUMED: it was answered under the operator's explicit standing
     delegation to "make the necessary decisions". If that delegation is read narrowly, this is the
     one decision in the run that should have waited until morning.
  7. A CONTRACT CONDITION WAS MIS-AUTHORED AND CORRECTED AT CLOSE. `STAMP-IN-DATASET` grepped for
     the word "summarizer" in `dataset.py` — a spelling, in a file that never carries it — and went
     BROKEN at close as a false red. Re-authored against the invariant (`as_dict` emits the
     `provenance` key) and re-run. The invariant itself was independently proven by
     `test_the_committed_manifest_carries_the_same_stamp` throughout. This is P5's own lesson
     (*"needs the invariant, not the spelling"*) landing on the contract that was meant to enforce it.
  8. AC3's CLI half is judged **N/A** rather than unbuilt, on the ground that no CLI writes the
     artifact. That is a judgement about what the ticket meant, not a measurement.
  9. NOT VERIFIED: that the LLM path actually produces better summaries. Nothing here runs an LLM —
     the stamp records which side of the seam ran, and says nothing about which side is better. That
     was Scope 4's job and Scope 4 is E1.
 10. `docs/benchmarks/121_*.md`'s figures already differ from a fresh run for reasons predating this
     ticket, and its global question counts undercount the JSON (13/11/2 vs 15/12/3). Deliberately
     not touched here; it needs its own re-measurement.
```
