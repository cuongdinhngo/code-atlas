---
id: 210
slug: the-artifact-has-one-shape-for-every-reader
title: "`detail_level` on `generate_onboarding` changes the MCP response and not one byte of the written artifact, so a first-week developer and the engineer auditing coupling are handed the same 505-file tree"
phase: 3
milestone: M12
status: done
depends_on: [088, 112, 121, 205, 207, 209]
---

## Why this exists (measured on the anchor monorepo, 2026-09-02)

`generate_onboarding` takes `detail_level: DetailLevel = "standard"`, and everything it gates lives
in `_payload` (`code_atlas/tools/generate_onboarding.py:291`):

```python
if detail_level == "standard":
    payload["cache"] = f"{CACHE_DIR}/{CACHE_NAME}"
    payload["isolated_modules"] = len(artifact.isolated)
    payload["prose_calls"] = prose.calls
    payload["prose_declined"] = prose.declined
```

Every one of those is a field of the **MCP response**, which the caller reads once and drops. The
**written artifact** — `overview.md`, `tour.md`, `flows.md`, `modules/`, `index.html`,
`manifest.json` — is byte-identical at `minimal` and at `standard`. The knob named for how much
detail the reader wants does not reach the thing the reader keeps.

So the artifact has exactly one shape, and on the anchor that shape is 505 files — 3.0 MB of content occupying 6.1 MB on disk (500 sub-kilobyte files against a 4 K block).

### The two readers want opposite artifacts

This was measured by reading the generated tree as each:

| | first-week developer | engineer auditing the system |
|---|---|---|
| wants | where my work lives, how to run it, ten files to open | coupling hotspots, mirror-subtree overlap, what is unreachable |
| the tour | 15 steps, none of them in the tree they will edit | irrelevant — they know the layout |
| `modules/` (500 pages, 3.6 MB on disk) | median 893 B, mostly path restatement | irrelevant — they query the graph |
| `overview.md` aggregates | unreadable — 12 layers, 24,535 modules, a 99-row cross-layer table | **this is the whole value** |
| what is missing | run/test commands, entry-point names, domain vocabulary | confidence attribution on the aggregates |

The load-bearing content for one is noise for the other, and the artifact spends **3.6 of its 6.1 MB on disk**
on the section neither of them named as their primary need.

### Why a knob, and why not just cut

[205](205_a-module-page-per-node-budget-slot.md) removes filler and
[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) narrows the population, and
both are right independently. Neither answers *who is this for*, and without that the page count is
being argued in the abstract: 500 is indefensible for both readers, but the right number for a
newcomer (a handful, deeply written) and for an auditor (zero) are different numbers, not one
compromise. **R5.8** — rank inside the statement that truncates — needs to know what the reader is
optimising for before it can rank.

The prior art is external: the reference implementation surveyed in the user's notes carries a
persona axis (non-technical / junior / experienced) through its viewer, and it changes what is shown
rather than only how much. The idea transfers; its architecture does not (see Constraints).

## Scope

1. **An audience setting that reaches the written artifact**, not only the response. Two named
   audiences to start (**R7.1**) — the newcomer and the maintainer — with the current output as one
   of them or as an explicit third.
2. **Each audience is a stated content contract, not a verbosity dial.** Write down, per audience,
   which sections are emitted and why that reader needs them. A newcomer artifact that is the
   maintainer's with fewer bytes has failed the ticket.
3. **The artifact says which audience it was written for**, beside 209's summarizer stamp — a
   committed tree that cannot say who it is for cannot be judged, or regenerated to match.
4. **Reconcile with `detail_level` rather than adding a second knob beside it.** Either
   `detail_level` grows to reach the artifact, or it stays a payload knob and the audience setting
   is separate and documented as such. One decision, written down (**R1.8**).
5. **Measure both artifacts against the 121 harness.** An audience that answers fewer questions of
   its own class than today's single artifact is not shipped.

### Explicitly not in scope

- **A viewer feature.** The reference implementation puts persona in a React store; this is about
  the committed Markdown, which is what code-atlas ships and what a consumer commits.
- **New content.** [207](207_the-artifact-answers-no-question-a-newcomer-asks-first.md) owns the
  orientation section. This ticket routes existing and 207's content to a reader; it does not author
  any.
- **More than two audiences.** Three named personas with overlapping needs is the gold-plating
  **R7.1** exists to prevent.

## Constraints

- **R4.1 / R4.2** — the audience is a resolved setting, so output stays deterministic per audience.
  No inference of who is reading.
- **R1.8** — one place decides what an audience emits; the Markdown writer, the dataset and the
  viewer all read that decision rather than re-deriving it, which is
  [127](127_caveats-drop-at-the-artifact-layer.md)'s lesson.
- **R3.5** — the dataset carries the audience; bump `DATASET_VERSION`.
- **R7.4 — no dead abstractions.** Two audiences with one real difference between them is a
  configuration flag wearing a bigger name; if the content contracts in Scope 2 come out nearly
  identical, that is the finding, and the ticket closes as *not built* with the measurement recorded.
- **Do not adopt the reference implementation's shape.** Its pipeline is orchestrated by prompt files
  the host LLM executes, which trades **R4.2** for flexibility; borrow the axis, keep the
  deterministic core.

## Acceptance criteria

1. An audience setting changes which sections the written artifact contains, provably, on the anchor.
2. Each audience has a written content contract naming its sections and the reader need each serves.
3. The artifact states its audience, and regenerating with the same audience is byte-identical.
4. The existing `detail_level` behaviour is either extended or explicitly left alone, and `TOOLS.md`
   says which — with the superseded text deleted (**R7.6**).
5. The 121 harness scores each audience on its own question class; neither regresses against
   today's artifact.
6. If Scope 2's contracts prove near-identical, the ticket closes unbuilt with that comparison
   recorded, and the BACKLOG row says so.

## References

[088](088_generate-onboarding-markdown.md) (the written artifact),
[112](112_onboarding-dataset-contract.md) (where the audience field lives),
[121](121_onboarding-question-class-never-measured.md) (the harness that judges each audience),
[127](127_caveats-drop-at-the-artifact-layer.md) (three renderers, one decision),
[205](205_a-module-page-per-node-budget-slot.md) (how many pages — a question this reframes),
[207](207_the-artifact-answers-no-question-a-newcomer-asks-first.md) (the newcomer content this
routes), [209](209_a-committed-artifact-cannot-say-which-summarizer-wrote-it.md) (the other stamp
the artifact should carry).

---

MANGO WORKING DOC (below this line is NOT part of the raw ticket)

## Working doc (autorun 2026-09-04)

**KEY:** 210 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **reviewer:** OFF (`--no-reviewer`) · **challenger:** ON

### Phase 0 — refine

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 3 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 4 unresolved surfaced | 1 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

The premise **holds**: everything `detail_level` gated lived in `_payload`, and the written tree was
byte-identical at `minimal` and `standard`. One figure in the ticket is **already stale in this
repo's favour** — *"505 files, 3.0 MB"* is pre-205; 205 removed the module page tree and five files
are written now. The defect survives the correction: five files of one shape is still one shape.

**The want-decision**, answered under the operator's standing delegation: **R7.4 asks whether this
ticket should be built at all**, and that is a product call. It was answered by doing Scope 2
**first** and measuring, rather than by preference — see Phase 2. Answer: **build**.

How-decisions, each cited:
1. **`detail_level` stays a payload knob** (Scope 4). It carries one meaning on **24 tool modules** —
   how much of the *response* — and the response is discarded. Growing it to reshape the committed
   tree would make files a repo checks into git depend on a per-call argument, so a regenerate at a
   different `detail_level` would silently rewrite them. Written down in `TOOLS.md`, superseded text
   deleted (R7.6/AC4).
2. **Three values, two named audiences.** `full` is the ticket's own licensed *"current output as …
   an explicit third"*. It keeps a pre-210 committed tree describable and stops either reader's
   contract being the union of the other's. The *"more than two audiences"* exclusion targets three
   overlapping **personas**; this is two personas plus the status quo.
3. **The audience is a resolved setting AND a tool argument.** R1.8 governs *what an audience
   emits* — one table — not how the value arrives. Config alone would have made AC5 unmeasurable:
   the harness passes tool args, and cannot rewrite a fixture's `.code-atlas.toml` per question.

In-repo refs resolved: `generate_onboarding._payload`, `artifact.render_overview` and every
section renderer, `dataset.as_dict`, `viewer.py`, `config.py` `KNOB_KEYS`, `scripts/tokens_to_answer.py`
(`run_session_path`, `_NATIVE_TOOLS`), tickets 088/112/121/127/205/207/209, R1.8, R3.5, R7.1, R7.4.
Ambiguous: the anchor's 505-file tree — another checkout, and pre-205.

Recalled (advisory): `count-pin-in-blast-radius` (P5), `prove-the-guard-fails` (R6.5),
`derived-not-listed-invariant` (R6.7); area: onboarding / artifact shape.

### Phase 1 — analysis

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 3 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists · Scope · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=5 R=5 G=1 AC=6`
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 7 applicable — 6 by change-type | 1 by recalled handle — §R1.8 (one place decides) ✅ · §R3.5 (dataset field ⇒ version bump + viewer) ✅ · §R4.1 (no inference of who is reading) ✅ · §R4.2 (deterministic per audience) ✅ · §R5.3 (a bad setting degrades, never aborts) ✅ · §R7.4 (no dead abstraction — measured, not assumed) ✅ · §R6.5 (prove the guard fails) ✅`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green — main at 6ba5ebb, 2844 passed`
`SCOPE: L`
`TIER: full`

Clarifications, both self-resolved:
1. *Does touching `viewer.py` cross "not in scope: a viewer feature"?* — resolved: **no**. The
   exclusion names a persona control in a viewer store. R1.8 and R3.5 require every renderer of the
   dataset to move with the field, so one sentence stating the audience is compliance, not a
   feature. Flagged in the PR rather than assumed.
2. *Is AC1's "on the anchor" met?* — resolved: **E1**, `real_corpus_path` null. Proven on a seeded
   fixture against the emitted markdown instead.

| ID | Type | Statement |
|---|---|---|
| G | G | The committed artifact has a shape per reader, and says which |
| R1 | R | An audience setting that reaches the WRITTEN artifact |
| R2 | R | Each audience is a stated content contract, not a verbosity dial |
| R3 | R | The artifact says which audience it was written for |
| R4 | R | Reconcile with `detail_level`; one decision, written down |
| R5 | R | Measure both audiences against the 121 harness |
| C1 | C | R4.1/R4.2 — a resolved setting; no inference of who is reading |
| C2 | C | R1.8 — one place decides; markdown, dataset and viewer read it |
| C3 | C | R3.5 — the dataset carries the audience; bump `DATASET_VERSION` |
| C4 | C | R7.4 — near-identical contracts ⇒ close unbuilt with the measurement |
| C5 | C | Do not adopt the reference implementation's prompt-orchestrated shape |
| AC1 | AC | The setting changes which sections the written artifact contains |
| AC2 | AC | Each audience has a written contract naming its sections and the need each serves |
| AC3 | AC | The artifact states its audience; same audience ⇒ byte-identical |
| AC4 | AC | `detail_level` extended or explicitly left alone, `TOOLS.md` says which |
| AC5 | AC | The harness scores each audience on its own class; neither regresses |
| AC6 | AC | Near-identical contracts ⇒ close unbuilt, recorded, BACKLOG row says so |

### Phase 2 — design

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

**AC6's measurement, taken BEFORE anything was wired.** The two contracts were written, then
compared by set arithmetic rather than by eye:

```
newcomer sections : 4  ['layers', 'orientation', 'provenance', 'summary']
maintainer        : 9  ['community', 'crossings', 'diagram', 'layers', 'mirrors',
                        'modules', 'provenance', 'reachability', 'summary']
symmetric diff    : 7  ['community', 'crossings', 'diagram', 'mirrors', 'modules',
                        'orientation', 'reachability']
document diff     : 1  ['tour']
is one a subset of the other?  False
```

**Neither is the other minus a few bytes** — `orientation` is newcomer-only, six aggregates are
maintainer-only — so R7.4's *close unbuilt* branch does not apply and the ticket ships. That
comparison is now `test_the_contracts_are_not_near_identical`, so a later edit collapsing the two is
a red build rather than a lost finding.

Handle traces (command → result):
1. `count-pin-in-blast-radius` — the suite found **six** pins: `DATASET_VERSION == 13`, both
   core-module-count guards, `len(KNOB_KEYS) == 19`, the `env_name` ordering list, and — the one
   worth noting — **207's own new `test_the_documented_knob_table_lists_every_knob` caught the
   missing `CA_AUDIENCE` row**, one ticket after it was written to stop exactly that. **Sighting 13.**
2. `prove-the-guard-fails` — three mutants, three caught.
3. `derived-not-listed-invariant` — the section list is named by **key**, not by heading text, so a
   heading can be reworded without silently re-partitioning the audiences.

**Exclusion (1, with a checkable expiry).** AC1's *"on the anchor"* — `real_corpus_path` is `null`.
**Expiry: the first run after it becomes non-null.** Fifth consecutive sighting (206, 211, 209, 207,
210); escalated at 209 and not re-argued.

**Proving test:** `tests/test_audience.py` (10 tests).

**Rejected alternative:** growing `detail_level` to reach the artifact. It would give one argument
two meanings across 24 tools and make committed files depend on a per-call value — see Phase 0.

### Phase 3 — execute

What landed: `audience.py` (the one contract table), the section and document gating in
`render_overview` and `_write`, `CA_AUDIENCE` plus the tool argument, the audience statement in
`overview.md` / `manifest.json` / the viewer, `DATASET_VERSION` 13 → 14, the `TOOLS.md`
reconciliation, and two per-audience harness questions.

Verification: `scripts/gate.sh` → **GATE GREEN, 17/17, 0 skipped**. Full suite **2858 passed**
against a 2844 baseline. Benchmark floors hold (ratio 0.83, recall 1.0, precision 1.0).

`diff ⊆` approved list: `audience.py` (new), `artifact.py`, `dataset.py`, `viewer.py`, `config.py`,
`generate_onboarding.py`, `test_audience.py` (new), `test_config.py`, `test_onboarding_dataset.py`,
`test_core_is_language_agnostic.py`, `test_sql_confinement.py`,
`scripts/tokens_to_answer_questions.json`, `docs/TOOLS.md`, `docs/benchmarks/121_*.md`, this working
doc, BACKLOG, TOKEN_LEDGER.

#### Acceptance criteria — close-out

| AC | Verdict | Evidence |
|---|---|---|
| AC1 | **MET on a fixture; "on the anchor" is E1** | `test_the_audience_changes_which_sections_the_written_tree_holds`, on the emitted markdown. Newcomer 5 sections / 1,517 B, maintainer 9 / 3,730 B, full 10 / 4,077 B |
| AC2 | **MET** | `audience.py`'s `CONTRACTS`; `test_every_contracted_section_states_why_that_reader_needs_it` asserts every entry carries its reason |
| AC3 | **MET** | `test_the_artifact_states_its_audience`, `test_regenerating_with_the_same_audience_is_byte_identical` |
| AC4 | **MET** | `detail_level` **left alone**, and `TOOLS.md` says so with the superseded paragraph replaced |
| AC5 | **MET** | Each audience scored on its own class: newcomer 1,210 ✅, maintainer 1,538 ✅, full 1,662 ✅. The newcomer tree answers a *strictly larger* question for 27 % fewer tokens |
| AC6 | **N/A — the branch it names was not taken** | The contracts are not near-identical: 7 sections and 1 document differ and neither is a subset of the other. Measured before wiring; pinned by a test |

### Phase 4 — review

`reviewer`: **OFF** (`--no-reviewer`) — no rule-book-grounded review of this diff exists.
`challenger`: **ON** — ticket-blind, on the raw ticket text and `git diff main...HEAD`.

**Round 1: LGTM** — 11 met, 0 not met, 2 correctly-unexercised, 1 environment-gated (AC1's anchor
half). It re-derived the 7-section symmetric difference from the dataclass literals and re-ran the
benchmark and the full suite itself rather than taking the numbers on trust. **All three of its
non-blocking findings were taken:**

1. **A contract's stated reason overstated what was built.** The newcomer `SUMMARY` entry claimed
   *"four lines, not a table"* while the renderer emits the identical six-line block for both
   audiences. A content contract that misdescribes its own output is the defect this ticket is
   about, one level up. Reworded to what is true: the same block, and what made the aggregates
   unreadable was the 99-row crossings table, which this contract does not include.
2. **A latent landmine, and the best finding of the review.** `render_overview` returned early once
   `LAYERS` was absent, *before* the `DIAGRAM` and `CROSSINGS` gates — so a future audience wanting
   the diagram but not the layer list would silently lose it. **No shipped audience hits it and no
   test would have caught it**, which is exactly why it was worth fixing. Every section now gates on
   its own contract entry, pinned by
   `test_a_sections_presence_never_depends_on_another_sections`, which renders through a probe
   contract and goes red when the early return is restored.
3. **A stale docstring.** `generate_onboarding` still claimed it *"writes five files"*, false for
   the maintainer audience's four.

It also **disclosed an independence breach unprompted**: a routine `git diff` of `BACKLOG`/
`TOKEN_LEDGER` surfaced this ticket's authored ledger rationale. It scoped the damage precisely —
every overlapping fact had already been derived independently, and the one figure it could not
re-derive (the full `17/17` gate) is named rather than adopted.

**A tooling observation worth the operator's attention**, made in passing: this session's `rtk`
proxy **silently dropped `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` and the task file from
`git diff --stat`** — 14 files/637 lines against `/usr/bin/git`'s 17/811. A filtered diff listing
that omits files without saying so is a way to miss a change.

**Round 2 (verify-only, same live seat): LGTM.**

### Phase 5 — finalise

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 3 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 3 candidate(s) checked | 2 still-true (proceed) | 1 falsified (BLOCKED) | 0 not cheaply checkable`
`RECURRING-T2: 3 type-2 claim(s) with seen ≥ 2 | 3 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured (host surfaces no usage block) · top cost driver: main-loop execute`

`FALSIFY` detail: *"everything `detail_level` gates lives in `_payload`"* — **still true**. *"the
written artifact is byte-identical at minimal and standard"* — **still true**. *"505 files, 3.0 MB"*
— **falsified**: pre-205; five files are written now. The defect survives its own stale figure.
