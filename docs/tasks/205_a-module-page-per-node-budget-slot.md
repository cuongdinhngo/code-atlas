---
id: 205
slug: a-module-page-per-node-budget-slot
title: "`generate_onboarding` writes exactly `impact_max_nodes` module pages — 500 on every repo, each headed `Stop N of 500` while the tour beside it has 15 steps, and the 107 filler gate never fires because one edge counts as a fact"
phase: 3
milestone: M11
status: done
depends_on: [106, 107, 108, 109, 111, 118]
---

## Why this exists (measured on the anchor monorepo, 2026-09-02)

A regenerated `docs/onboarding/` is **505 files — 3.0 MB of bytes, 6.1 MB on disk**, because 500 of
them are sub-kilobyte files each taking a 4 K block. `modules/` is 3.6 MB of that disk figure — and
holds exactly **500** pages. Not "about 500": 500, because that is
`DEFAULT_IMPACT_MAX_NODES` (`code_atlas/config.py:54`).

The count is a node budget that leaks into a file count through four hops, none of which mean to
decide how many pages a repo gets:

```
code_atlas/tools/generate_onboarding.py:99   subgraph = store.tour_subgraph(max_nodes=config.impact_max_nodes)
code_atlas/tools/generate_onboarding.py:114  tour_files = subgraph.files
code_atlas/onboarding/artifact.py:375        stops = ordered_stops(tour_files, tour_edges, entry_points)
code_atlas/onboarding/artifact.py:385-398    one ModulePage per stop
```

`impact_max_nodes` is the **`impact` tool's** traversal ceiling. Nothing about it is a statement
that a reader wants 500 pages, and no repo — 200 files or 24,535 — gets a different number.

### What the 500 pages actually contain

Measured over the emitted tree (pre-204 index, `max_results = 10`):

| | |
|---|---|
| pages | 500 |
| page size | min 323 B · median **893 B** · max 1,964 B |
| pages rendering `No leading doc comment above the indexed declaration in this file.` | **277** |
| pages rendering a docline that is a bare comment delimiter (`/**` ×186, `/*` ×8, `/*!` ×5, `*/` ×2) | **201** |
| pages carrying a sentence that describes the file | **~2** |
| pages with `incoming: (none)` | 125 |
| pages with **both** lists empty | **0** |

The median page is under 900 bytes and carries: the path (already in the filename), a Role, a Layer,
a "Stop N of 500" line, and a truncated neighbour list. For 277 the Summary line is a sentence saying
there is no summary; for 201 more it is a comment delimiter like `/**`, which is worse — it *looks*
like a summary. Across all 500 pages, roughly **two** carry a sentence that describes the file.

> **Measurement provenance.** Every figure above was read off an artifact generated from the anchor's
> **field index before [204](204_bare-name-resolution-has-no-language-predicate.md) landed**, which
> carries 343,131 JavaScript/TypeScript-declared `CALLS` edges resolving to PHP targets — 100 %
> HEURISTIC, 0 RESOLVED — verified directly against `.code-atlas/graph.db` on 2026-09-02. Anything
> derived from **degree** is therefore contaminated, and JS files are the contaminated side: they
> carry the false out-edges that bought them their rank. The structural findings below do not depend
> on any edge and stand as written.

> For this ticket that touches two rows only: `incoming: (none)` (125) and `both lists empty` (0) are
> edge-derived and must be re-counted post-204 before C1's replacement criterion is chosen — Scope 3
> already says so. The page **count** (500), the page **sizes**, the 277 missing doclines and the
> `Stop N of 500` header are structural and do not move.

### The 107 gate cannot fire

[107](107_a-page-with-no-neighbours-and-no-summary-is-filler.md) named the defect *"a page with no
neighbours and no summary is filler"* and [109](109_onboarding-artifact-quality-gate.md) made C1 the
guard. As implemented (`code_atlas/onboarding/quality_gate.py`):

```python
if not (page.docline or page.fan_in or page.fan_out):  # C1: the 107 filler rule.
    raise QualityGateError("C1", page.file, "page carries no fact beyond its own path")
```

The measured `both lists empty` count is **0**, so C1 raised zero times on a run in which no page
carries a usable summary at all. The rule is an `and` over three signals where the reader's question is a
judgment about one: *does this page tell me something I could not read off the path?* A single
inbound edge — including a HEURISTIC one — satisfies it. C1 is a non-emptiness check wearing 107's
name, and the ticket that closed 107 is therefore closed against a guard that does not implement it.

### `Stop N of 500` against a 15-step tour

[111](111_tour-is-narrative-steps.md) replaced the 500-stop tour with narrative steps, and the gate
holds it there (`MAX_TOUR_STEPS = 15`). Today's `tour.md` has exactly 15 numbered sections, and their
`Covers N module(s)` figures sum to 500 — the steps *group* the same 500 modules, so the artifact is
not internally inconsistent in its arithmetic.

It is inconsistent in its **unit**. `artifact.py:720` renders every page header as:

```
## In the tour   Stop 65 of 500. entry point (zero inbound)
```

A reader who has just read a 15-step tour is told this file is stop 65 of 500. "Stop" means a tour
step in `tour.md` and a module slot in `modules/`, and nothing in either file says so. 111 moved the
tour off stops and left `pages` still enumerating them.

## Scope

1. **Decouple the page count from `impact_max_nodes`.** Whatever decides how many pages an artifact
   emits is its own resolved setting with its own name and default, not a borrowed traversal
   ceiling. `impact`'s budget stays where it is and keeps its current default.
2. **One meaning for "stop."** Either the page header cites the tour step it belongs to (`Step 9 of
   15 — Uncategorised (2/3)`), or it cites no tour position at all. Not a second numbering.
3. **Make C1 enforce what 107 specified.** A page earns emission by carrying a fact a reader could
   not get from the path. Pick the criterion deliberately and write it down — a docline, or a
   RESOLVED edge, or a named role that is not the default — and let the gate fail the run that
   violates it, per [109](109_onboarding-artifact-quality-gate.md)'s contract that `build_artifact`
   raises rather than writing a bad tree.
4. **A way to emit no pages at all.** `detail_level: minimal` currently omits the cache path and
   keeps all 500 pages. A reader who wants `overview.md` + `tour.md` + `flows.md` and no
   `modules/` tree has no way to ask.
5. **A size budget on the emitted tree**, asserted the way the repo already budgets its own docs
   (`tests/test_doc_size_budget.py`). 6.1 MB of generated Markdown landing in a consumer's repo is a
   number someone should have had to argue for.

### Explicitly not in scope

- **The aggregates.** `overview.md`'s mirror-subtree table, business-module table and reachability
  split are the artifact's load-bearing content and must come out byte-identical (R4.2). This
  ticket removes filler; it does not re-derive a single figure.
- **Which files are chosen.** Scoping the artifact to the tree a reader works in is
  [206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md). If 206 lands first,
  re-measure before setting a default here: the two tickets both move the page count and neither
  should be tuned against the other's stale number.
- **Re-tiering edges.** [204](204_bare-name-resolution-has-no-language-predicate.md) already did
  that. Note that 204 will change what the neighbour lists say and therefore what C1 sees, which is
  a reason to re-measure the docline/125/0 figures on a post-204 index before choosing C1's criterion —
  not a reason to wait.

## Constraints

- **R7.1** — the smallest useful thing. The defect is "a knob's default became a content decision";
  the fix is a knob of its own, not a new page format.
- **R6.5** — C1's replacement ships only once it has been **observed failing** on a page the current
  gate passes. On the anchor every one of the 500 is a candidate; commit one of each failure shape —
  the honest sentence and the bare `/**` — as fixtures.
- **R6.8** — AC3 below is phrased as a failure mode, so it needs a guard that can exhibit it.
- **R6.9** — assert at the consumer: the guard reads the **emitted tree**, not `ModulePage` objects.
- **R4.2** — identical input, identical output. A page-count change is a change to committed files
  in every downstream repo; the conformance tests and any golden artifact move with it.

## Acceptance criteria

1. The number of module pages is set by a named onboarding setting; changing `impact_max_nodes`
   alone changes no page count, and a test pins that independence.
2. No emitted page cites a tour position in a unit `tour.md` does not use.
3. A page carrying no fact beyond its own path fails the gate — demonstrated by a committed fixture
   that the pre-change gate passes and the post-change gate rejects.
4. A caller can request an artifact with no `modules/` tree, and the quality gate still runs over
   what is emitted.
5. `overview.md`, `tour.md` and `flows.md` are byte-identical to the pre-change run on the same
   index, except where AC2 changed a page header.
6. The emitted tree has an asserted size ceiling, and the number is argued in the test, not merely
   recorded.
7. `TOOLS.md` and the `generate_onboarding` docstring describe the new setting; per **R7.6** the
   text they supersede is deleted, not stacked on.

## References

[106](106_tour-budget-buys-500-alphabetical-isolated-files.md) (the budget first bought 500 files),
[107](107_a-page-with-no-neighbours-and-no-summary-is-filler.md) (the filler rule this closes for
real), [108](108_module-page-neighbour-list-is-unbounded.md) (the neighbour cap the pages already
carry), [109](109_onboarding-artifact-quality-gate.md) (the gate contract),
[111](111_tour-is-narrative-steps.md) (15 steps, and the `pages` reader it did not move),
[118](118_module-summary-seam-gets-empty-facts.md) (why the doclines are empty or are delimiters),
[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) (which files, as opposed
to how many).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 205 · **work_doc_mode:** embed · **Current phase:** 5 finalise — complete on disk. PR [#254](https://github.com/cuongdinhngo/code-atlas/pull/254) open on `main`. **Next action:** merge #254. **Revert path:** `git revert` the four commits on `fix/205-a-module-page-per-node-budget-slot`, or close #254 unmerged; a repo that regenerated in between gets its pages back on the next write, and `ARTIFACT_VERSION` returns to 1 with the revert.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** bug.
- Run arg *"with skipped reviewer"* = `--no-reviewer`; the reviewer seat is waived, the **challenger
  keeps its seat** (AGENTS.md *Maintainer workflow*).
- Branch `fix/205-a-module-page-per-node-budget-slot`, based on `main` at `f1c5bfb`.
- Contract `.mango/run-contract-205.txt` (re-authored at Gate 2 for the amended ACs, and once more
  at execute for one falsified condition — both times before the code it checks existed; the
  untouched t0 record is `.mango/run-contract-205.t0.txt`). RECONCILE t0: 11 declared | 9 re-run |
  **0 holding** | 9 BROKEN | 2 UNBOUND | 0 could-not-run.
- **The ticket's question was answered by removing its subject.** The maintainer's four want-answers
  say `modules/` should not be generated at all, so ACs 1–4 are amended (Phase 1, AC validation).

## Phase 0 — refine

`PREMISE: 14 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 11 claim(s) surfaced | 0 by symbol | 9 by handle | 2 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 4 want-decision asked | 6 how-decision resolved+cited | 1 ASSUMED | skip: no`

Every in-repo reference resolved: `DEFAULT_IMPACT_MAX_NODES = 500` (`config.py:54`), the four hops
(`generate_onboarding.py:99`, `:114`, `artifact.py:375`, `:399`), C1 (`quality_gate.py:75`),
`MAX_TOUR_STEPS = 15` (`quality_gate.py:19`), the `Stop {index} of {of}` header
(`artifact.py:720`), `tests/test_doc_size_budget.py`, `docs/TOOLS.md`, and all eight referenced
tickets. The two ambiguous references are the anchor monorepo's emitted tree (a generated output, not
a repo file) and *which* `.code-atlas/graph.db` the provenance note means — resolved by locating the
anchor index at `/home/you/WORKSPACE/work/anchor-repo`, which is **pre-204** (built
2026-09-01T14:26Z; #250 merged 2026-09-02T05:13Z), exactly as the ticket's caveat says.

**Re-measured on a post-204 anchor rebuild** (full build into a scratch DB, 24,569 files, 262,899
nodes, **2,077,473 edges** against the field index's 2,188,026), because Scope 3 requires the
edge-derived rows re-counted before C1's criterion is chosen:

| | ticket (pre-204) | post-204 re-measurement |
|---|---|---|
| module pages | 500 | 500 (`isolated` 0) |
| narrative tour steps | 15 | **13** |
| pages whose Summary renders `No leading doc comment …` | 277 | **412** |
| pages whose docline is a bare comment delimiter | 201 | 76 |
| pages carrying a sentence that describes the file | ~2 | **12** |
| page bytes | median 893 B | min 313 · median 1,096 · max 1,907 |
| `modules/` total | "3.6 MB on disk" | **575 KiB of content** (3.6 MB is 500 × 4 K blocks) |
| pages with `incoming: (none)` | 125 | 125 |
| pages with both lists empty | 0 | **0** |
| pages carrying ≥1 RESOLVED module edge | — | **496 / 500** |

The structural rows held; the docline split moved the wrong way (412 empty, not 277). Two figures
the ticket did not have: the emitted tree's bytes are dominated by `manifest.json` (1.5 MB) and
`index.html` (952 KB), **not** by the pages, so cutting pages wins on **file count** (505 → 5) and
on reader attention, not on megabytes.

**Settled wants — asked and answered by the maintainer.** All four answers say the same thing.

| # | The want | Answer (verbatim) | Consequence |
|---|---|---|---|
| W1 | How many module pages should an artifact emit, now that the count stops borrowing `impact_max_nodes`? Measured options: 60 pages = 84 KiB, 100 = 142 KiB, 0 = opt-in, 500 = rename only | *"Modules/ có nghĩa gì mà sinh ra, chả ai đọc cái cục nợ này cả"* | **No `modules/` tree.** The page-count budget is not needed, because there is no page count |
| W2 | What counts as "a fact beyond the path"? Measured: a RESOLVED edge or a real docline keeps 496/500; a real docline alone keeps 12/500 | *"Bỏ modules vì nó vô nghĩa"* | C1's page rule is **deleted with its subject** rather than tightened |
| W3 | How is a module the page budget cut accounted for, given `isolated` today means *no edge either way and no summary*? | *"Ko sinh modules"* | No budget, no cut, no second bucket. `isolated` goes too — the fact it carried is already in the dataset's `no-edge-either-way` reachability bucket |
| W4 | AC5 demands `overview.md` byte-identical, but `overview.md` is where the page counts are printed | *"[No preference]"* | Handed back → **A1 below (ASSUMED)** |

**Resolved direction + citation (how-decisions).** H4–H6 come from the exposure-checker.

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | Does the page-removal keep a way to ask for pages back? | **No.** An interface with one implementer and no near-term second gets deleted; a flag whose only value is the behaviour just judged worthless is a dead abstraction | R7.4; W1/W2 above |
| H2 | AC2's *"one meaning for stop"* — cite the tour step, or cite no tour position? | **Moot, and satisfied by construction:** the only renderer of `Stop N of M` is `render_module`, which is removed. The guard becomes *no emitted file cites a stop* | `artifact.py:720`; ticket AC2 |
| H3 | What happens to a repo whose committed `docs/onboarding/modules/` predates this change? | **`recorded_pages` and `_remove_recorded_pages` STAY.** They read the *previous* manifest, so the first regeneration after this change deletes exactly the pages the tool recorded writing, and nothing else. Removing them would strand every existing tree | R5.7 (`own-only-what-you-wrote`); `generate_onboarding.py:218-231` |
| H4 | AC6's ceiling — bytes, or `estimate_tokens` like the cited precedent? | **Bytes**, over the emitted tree. Every figure in the ticket's own *Why this exists* is a byte/MB figure, and Scope 5 says *"generated Markdown"*; `test_doc_size_budget.py` is followed for its **structure** (a per-item ceiling plus a not-slack check), not for its token function | ticket *Why this exists* table + Scope 5; `tests/test_doc_size_budget.py:111-152` |
| H5 | Does the manifest keep a `pages` key? | **No** — and `architecture_diff.py`'s operational-key set drops `"pages"` with it, or the diff starts reporting a removed key as architectural drift | `architecture_diff.py:22`; `artifact.py:798` |
| H6 | `ARTIFACT_VERSION` | **Bumped 1 → 2.** `as_dict` loses `pages` and `isolated`; the version exists precisely so a second renderer can refuse a shape it does not know | `artifact.py:77-79` (145's contract) |

**ASSUMED (awaiting ratification) — MANDATORY.**

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses a prior decision? |
|---|---|---|---|---|
| A1 | AC5's exception is **widened**: `tour.md` and `flows.md` stay byte-identical, and `overview.md` is identical **except that its two page-count lines are deleted** (`- module pages:` and `- modules with no page (isolated, no summary):`). Every aggregate — mirror subtrees, business modules, reachability split, layers, crossings, the mermaid graph — comes out byte-identical | W4 was handed back with *"[No preference]"* | **Gate 2** | No — it widens an exception the ticket's own *"Explicitly not in scope → the aggregates"* paragraph already implies |
| A1b | **Amended at Gate 4, on the challenger's finding:** the exception also covers the `- truncated:` line, on an index where a *page's* neighbour list would have been cut. `list_truncated` folded that cut into the same flag as the walk's; with no page there is nothing to cut, so the flag narrows and the line moves. A1's first form claimed byte-identity that is **false** on that class of index | the challenger reproduced it with a wide-hub fixture; the claim had no test behind it | **Gate 4 — ratified by the fix**, which pins the new semantics in `test_truncated_now_answers_only_the_walk_question` | No — it corrects an over-broad claim of mine, not a human decision |

**Constraints surfaced from the scan** (not in the ticket):

- **R5.7** binds the removal: the tool may delete only what its own manifest recorded, so the page
  cleanup must go through `recorded_pages`, never a `rmtree` of `modules/` (088's defect, exactly).
- **R5.8** (`rank-before-truncate`) stops applying to pages — nothing ranks or truncates them any
  more. That is an answer, not a dodge: the rule's subject leaves the code.
- The repo commits **no** `docs/onboarding/` tree of its own, so no committed artifact in *this*
  repo moves. The anchor repo has one, and H3 is its migration path.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 101,783 tokens / 31 tool-uses)
reported **3 un-exposed decisions — 2 want, 1 how**. It found AC5's unsatisfiability
(→ W4/A1), the `isolated`-vs-budget-cut mislabelling (→ W3), and the bytes-vs-tokens axis (→ H4).
All three were live; none had been exposed by me.

**Recalled claims — advisory, surfaced only.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `124-C1` walk-budget-named-for-the-tool-that-walks | 2 | handle | **Yes** — this ticket is its second sighting; the resolution is stronger than 124's (the borrowed budget's *consumer* goes, not just its name) |
| 2 | `133-C1` per-element-ceiling-leaves-total-unbounded | 2 | handle | **Yes** — AC6's ceiling is a total, not a per-page one |
| 3 | `085-C2` ac-failure-mode-needs-the-right-guard | 2 | handle | **Yes** — AC3 is a failure-mode AC; its guard must be seen red |
| 4 | `105-C2` fixture-shape-begs-the-question | 2 | handle | **Yes** — it is why the anchor was rebuilt post-204 instead of trusting the ticket's figures |
| 5 | `019-C1` prove-the-guard-fails | 2 | handle | Yes — R6.5 is binding on all four new guards |
| 6 | `126-C1` rank-before-truncate | 2 | handle | Surfaced; **N/A after W1** — no page ranking survives |
| 7 | `123-C1` total-count-is-the-true-total-not-the-page | 2 | handle | Yes — `total_count` in the payload counts written files, which drops by 500 |
| 8 | `122-C2` enumerating-test-closes-the-sibling-surface | 2 | handle | **Yes** — the 22-site inventory below is derived, not hand-listed |
| 9 | `118-C1` empty-seam-inputs-masquerade-as-missing-data | 2 | handle | **Yes** — 412 of 500 doclines are that class; removal retires it here |
| 10 | `194-C4` plan-tool-list-is-not-the-surface | 5 | area (docs) | Yes — `docs/TOOLS.md` is the surface AC7 must move |
| 11 | `202-C3` staleness has six consumers | 5 | area (tools/payload honesty) | Weakly — the shape (one fix, many payload consumers) is the 22-site inventory's justification |
| — | `127-C1` guard-asserts-rendered-not-shipped-bytes | 2 | handle | **Skipped: retired** (promoted to R6.9) |

## Phase 1 — analysis

`PREMISE: 14 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 11 claim(s) surfaced | 0 by symbol | 9 by handle | 2 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope [+ Explicitly not in scope], Constraints, Acceptance criteria, References) | 5 decomposed | ROWS: C=5 R=8 G=5 AC=7`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 8 applicable — 5 by change-type | 3 by recalled handle — §1 (change-type) ✅ · §2 (change-type) N/A (no adapter, no language named, no repo/framework name added) · §3 (change-type) ✅ · §4 (change-type) ✅ · §5 (recalled handle: own-only-what-you-wrote) ✅ · §6 (recalled handle: prove-the-guard-fails, guard-asserts-rendered-not-shipped-bytes, derived-not-listed-invariant) ✅ · §7 (recalled handle: per-element-ceiling-leaves-total-unbounded) ✅ · §8 (change-type) N/A (no dependency added, moved or removed)`
`TRACK: backend — 0/22 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

Both lines above `SECTIONS:` are carried forward from Phase 0.

### BASELINE

`.venv/bin/python -m pytest -q`, **Ran at f1c5bfb** — the untouched tree this branch starts from:

```
........................................                                 [100%]
2778 passed in 295.30s (0:04:55)
```

### The defect, classified

`logic` (`config.cause_taxonomy`), at `code_atlas/tools/generate_onboarding.py:99` →
`code_atlas/onboarding/artifact.py:399`: a **traversal budget** (`impact_max_nodes`, the `impact`
tool's node ceiling) reaches a **file count** through four hops, none of which decide how many files
a repo's committed artifact should hold. The measured consequence is 500 files per repo, 412 of them
rendering a sentence that says there is no summary, and a C1 guard that raised **0** times because a
single inbound edge — HEURISTIC included — satisfies its `or`.

The maintainer's answer removes the subject rather than the knob: **no `modules/` tree**. That
closes G1–G5 at once, and it is the smaller change (R7.1) — a deletion, not a new setting plus a new
selection rule plus a new accounting bucket.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why this exists | "`modules/` … holds exactly **500** pages. Not 'about 500': 500, because that is `DEFAULT_IMPACT_MAX_NODES`" | A traversal budget decides a file count | `generate_onboarding.py:99`, `artifact.py:399`, `config.py:54` | | | ⬜ |
| G2 | Why this exists | "roughly **two** carry a sentence that describes the file" | The pages carry no summary; post-204 it is 12 of 500 | re-measurement above | | | ⬜ |
| G3 | Why this exists | "A reader who has just read a 15-step tour is told this file is stop 65 of 500" | Two numbering units, one word | `artifact.py:720`; steps = 13 post-204 | | | ⬜ |
| G4 | Why this exists | "C1 is a non-emptiness check wearing 107's name" | The guard cannot fire on the defect it names | `quality_gate.py:75`; `isolated` = 0 measured | | | ⬜ |
| G5 | Why this exists | "505 files — 3.0 MB of bytes, 6.1 MB on disk" | The tree's file count is unargued | 505 → 5 files after removal | | | ⬜ |
| R1 | Scope 1 | "Decouple the page count from `impact_max_nodes`" | Satisfied by removing the page count | | | | ⬜ |
| R2 | Scope 2 | "One meaning for 'stop.'" | Satisfied by removing the only second numbering | | | | ⬜ |
| R3 | Scope 3 | "Make C1 enforce what 107 specified" | The page rule is deleted with the pages; C1 over the three prose slots stays | | | | ⬜ |
| R4 | Scope 4 | "A way to emit no pages at all" | Becomes the only behaviour | | | | ⬜ |
| R5 | Scope 5 | "A size budget on the emitted tree" | A total-bytes ceiling over the emitted tree, asserted at the consumer | | | | ⬜ |
| R6 | Not in scope | "The aggregates … must come out byte-identical (R4.2)" | Every aggregate table unchanged; only the two page-count lines go | | | | ⬜ |
| R7 | Not in scope | "Which files are chosen … is 206" | No selection logic is touched; the tour walk is untouched | | | | ⬜ |
| R8 | Not in scope | "Re-tiering edges. 204 already did that" | No tier logic touched; 204's index used only for measurement | | | | ⬜ |
| C1 | Constraints | "**R7.1** — the smallest useful thing" | A deletion, not a new page format or a new knob | | | | ⬜ |
| C2 | Constraints | "**R6.5** — … observed failing" | Each new guard recorded red against the pre-change builder | | | | ⬜ |
| C3 | Constraints | "**R6.8** — AC3 … phrased as a failure mode" | The guard must reach the failure, not pass beside it | | | | ⬜ |
| C4 | Constraints | "**R6.9** — assert at the consumer: the guard reads the **emitted tree**" | Guards read files on disk after `generate_onboarding` runs | | | | ⬜ |
| C5 | Constraints | "**R4.2** — identical input, identical output" | Byte-stability of what remains; ARTIFACT_VERSION bumped for the shape change | | | | ⬜ |
| AC1′ | Acceptance criteria (amended) | see AC validation | No `modules/` path is emitted, on any `impact_max_nodes` | | | | ⬜ |
| AC2′ | Acceptance criteria (amended) | see AC validation | No emitted file cites a stop position | | | | ⬜ |
| AC3′ | Acceptance criteria (amended) | see AC validation | The no-pages guard is seen red on the pre-change builder | | | | ⬜ |
| AC4′ | Acceptance criteria (amended) | see AC validation | The quality gate still runs and can still fail over what is emitted | | | | ⬜ |
| AC5′ | Acceptance criteria (amended) | see AC validation | `tour.md`/`flows.md` byte-identical; `overview.md` identical minus the two count lines | | | | ⬜ |
| AC6 | Acceptance criteria | "The emitted tree has an asserted size ceiling, and the number is argued in the test" | Total bytes over the emitted tree, argued from the post-204 measurement | | | | ⬜ |
| AC7 | Acceptance criteria | "`TOOLS.md` and the `generate_onboarding` docstring describe the new setting; per **R7.6** the text they supersede is deleted" | Both describe the removal; the superseded promises are deleted, not stacked | | | | ⬜ |

### AC validation — every value re-derived, and four ACs amended

The maintainer's want (W1–W3) removes the subject of ACs 1–4. Each is amended to the guard that is
still falsifiable on the change that ships; **the amendment is the acceptance bar, so it is surfaced
here for the maintainer to interject**, per AGENTS.md *Maintainer workflow*.

| AC | Ticket's value | Re-derived / amended | Falsifiable? |
|----|----------------|----------------------|--------------|
| AC1 | "The number of module pages is set by a named onboarding setting; changing `impact_max_nodes` alone changes no page count, and a test pins that independence" | **AC1′:** the emitted tree holds exactly `overview.md`, `tour.md`, `flows.md`, `manifest.json`, `index.html` and **no `modules/` path**, and that file set is identical at `impact_max_nodes` = 2 and = 500 | Yes — the emitted file set, listed |
| AC2 | "No emitted page cites a tour position in a unit `tour.md` does not use" | **AC2′:** no emitted file matches `Stop \d+ of \d+` | Yes — a grep over the emitted tree |
| AC3 | "A page carrying no fact beyond its own path fails the gate — demonstrated by a committed fixture that the pre-change gate passes and the post-change gate rejects" | **AC3′:** the guard that no page is emitted is **observed failing** against the pre-change builder, recorded (R6.5). The 412-page filler class is removed rather than gated, so a fixture *the gate rejects* no longer exists to build | Yes — a recorded red run |
| AC4 | "A caller can request an artifact with no `modules/` tree, and the quality gate still runs over what is emitted" | **AC4′:** the quality gate still runs on every write and can still **fail** on what is emitted — C4's step ceiling, C3's empty layer description, C1 over the three prose slots — each demonstrated red | Yes — three recorded red runs |
| AC5 | "`overview.md`, `tour.md` and `flows.md` are byte-identical to the pre-change run on the same index, except where AC2 changed a page header" | **AC5′ (A1 + A1b):** `tour.md` and `flows.md` byte-identical; `overview.md` identical except its two page-count lines are deleted **and, on an index where a page's neighbour list would have been cut, its `- truncated:` line** (A1b). Asserted on one index pre/post, plus a test pinning the narrowed flag | Yes — a byte comparison plus a two-directional flag test |
| AC6 | "asserted size ceiling, and the number is argued in the test" | Unchanged. Unit = **bytes** (H4). Post-204 measurement: `overview.md` 12,420 B · `tour.md` 5,036 B · `flows.md` ~3.3 KB · `modules/` **575 KiB gone** · `manifest.json` ~1.5 MB · `index.html` ~952 KB. The ceiling is a **total over the emitted tree** (133-C1: a per-file ceiling leaves the total free) | Yes — a total-bytes assertion |
| AC7 | "`TOOLS.md` and the … docstring describe the new setting" | There is no new setting, so both describe **the removal**; the two superseded `TOOLS.md` bullets (`:78-80` per-module pages, `:82` "Tour and pages bounded by `CA_IMPACT_MAX_NODES`") are **deleted** | Yes — a grep for the superseded text |

**Clarifications, all four self-resolved:**

1. *ACs 1–4 are unsatisfiable under the ratified want.* Amended above, cited to W1–W3 verbatim.
2. *The ticket's measured figures disagree with a post-204 index.* Re-measured and recorded; the
   ticket's own provenance note predicted exactly this (Scope 3).
3. *AC6's unit.* Bytes, not tokens — H4.
4. *A committed `modules/` tree already exists in the anchor repo.* R5.7's recorded-page removal is
   its migration path — H3.

### Universal inventory — N = 22 sites, derived from the symbols, not hand-listed

`grep -rn '\.pages\b|PAGES_DIR|render_module|recorded_pages|isolated|page_relpath|ModulePage'`
over `code_atlas/` plus the two docs surfaces. Review must confirm **every** row, not a total.

| # | Site | What must happen |
|---|---|---|
| 1 | `artifact.py` `ModulePage` dataclass | removed |
| 2 | `artifact.py` `OnboardingArtifact.pages` | removed |
| 3 | `artifact.py` `OnboardingArtifact.isolated` | removed (its fact lives in the dataset's reachability split) |
| 4 | `artifact.py` `as_dict` `pages`/`isolated` keys | removed; `ARTIFACT_VERSION` 1 → 2 |
| 5 | `artifact.py` `page_relpath` | removed |
| 6 | `artifact.py` `recorded_pages` | **kept** — reads a pre-205 manifest (R5.7 migration, H3) |
| 7 | `artifact.py` `PAGES_DIR` | **kept** — `_remove_recorded_pages` needs it to prune the empty tree |
| 8 | `artifact.py` `build_artifact` page loop + `isolated` accumulation | removed |
| 9 | `artifact.py` `render_module` | removed |
| 10 | `artifact.py` `render_overview` two count lines | removed |
| 11 | `artifact.py` `manifest_dict` `"pages"` key | removed |
| 12 | `artifact.py` `__all__` | pruned to what survives |
| 13 | `quality_gate.py` C1 page rule | removed |
| 14 | `quality_gate.py` C2 page-bytes rule + `MAX_PAGE_BYTES` | removed |
| 15 | `quality_gate.py` C5 isolated-module rule | removed (the SCC-member half stays) |
| 16 | `quality_gate.py` C6 duplicate/absent-page rules | removed |
| 17 | `quality_gate.py` C7 page-index order + isolated-sorted | removed |
| 18 | `quality_gate.py` `render_module` import + `max_results` parameter | pruned |
| 19 | `generate_onboarding.py` page write loop + imports | removed |
| 20 | `generate_onboarding.py` `isolated_modules` payload key | removed |
| 21 | `generate_onboarding.py` docstring | rewritten; superseded promises deleted (R7.6) |
| 22 | `architecture_diff.py:22` operational-key set | `"pages"` dropped (H5) |
| + | `docs/TOOLS.md:78-82` | the two superseded bullets deleted (AC7) |

### Blast radius

- **Entry point:** `generate_onboarding` (MCP tool) → `build_artifact` → `_write`.
- **Consumers of the removed shape:** `quality_gate.check_artifact`, `architecture_diff`'s
  operational-key set, `manifest.json`'s `pages` key, `.code-atlas/onboarding/artifact.json`'s
  `pages`/`isolated` keys. `viewer.py` renders the **dataset** alone and references no page — the
  self-contained `index.html` is unaffected.
- **Repos touched:** `app` (this one). No adapter, no schema, no contract version
  (`contract.py` untouched — this is not node/edge vocabulary).
- **Tests to move:** `test_generate_onboarding.py`, `test_onboarding_quality_gate.py`,
  `test_artifact_contract.py`, `test_architecture_diff.py`, `test_caveats_reach_the_artifact.py`,
  `test_onboarding_viewer.py` (page assertions only), plus any fixture asserting `modules/`.

## Phase 2 — design

`HANDLES: 9 recalled | 8 traced (command + result) | 1 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Approach

**Delete the subject, not the knob.** `generate_onboarding` stops emitting a `modules/` tree: the
`ModulePage` model, its renderer, the manifest's `pages` key, the `isolated` bucket that existed
only to explain a missing page, and the five quality-gate criteria that guarded pages all go. The
tour walk is untouched — `impact_max_nodes` keeps bounding the walk, which is what it is for
(`guided_tour` uses the same budget) — and every aggregate comes out byte-identical.

What survives, deliberately:

- **`recorded_pages` + `_remove_recorded_pages` + `PAGES_DIR`** — R5.7. They read the *previous*
  manifest, so the first write after this change deletes exactly the 500 pages the tool recorded
  writing in a downstream repo, and nothing it did not write. Removing them would strand every
  existing tree.
- **The 118 read-through seam** (`module_facts`, `summarize_modules`) — `build_steps` consumes the
  doclines for the narrative steps (`steps.py:334`), so the seam is not page machinery. Only
  `NO_DOCBLOCK` goes, because `render_module` was its only renderer and `steps.py:334` omits an
  empty docline instead of inventing a sentence about it.
- **C1 over the three prose slots, C3, C4, C7's layer/crossing order** — the gate keeps every check
  whose subject still exists.

### Rejected alternatives

1. **A named page budget with a small default (the ticket's Scope 1).** Rejected by W1/W2: it keeps
   412 pages whose Summary line says there is no summary, just fewer of them, and it adds a setting,
   a selection rule (which N of the 500 — `rank-before-truncate` applies) and a third accounting
   bucket. Three new mechanisms to ship a smaller pile of the thing judged worthless (R7.1).
2. **Keep the pages, tighten C1 to "a real docline".** Measured: keeps **12 of 500** on the anchor.
   The gate would then raise on almost every real repo unless the builder dropped the other 488 —
   which is the deletion, arrived at by the expensive route.
3. **`detail_level: minimal` emits no pages, `standard` keeps them.** Rejected: an interface with one
   implementer and no near-term second (R7.4), where the surviving branch is the behaviour just
   judged worthless. It would also leave every gate criterion, the `isolated` bucket and the second
   numbering alive behind a flag nobody sets.
4. **Extend the ceiling to `manifest.json` + `index.html`** (2.5 MB of the anchor's 2.6 MB tree).
   Rejected as out of scope: both are the load-bearing dataset the ticket explicitly protects, and
   they scale with `path_index_max`, not with this change. **Recorded as a follow-up candidate.**

### Assumptions

| # | Assumption | Tag | How it is resolved |
|---|---|---|---|
| 1 | `build_steps` is the other consumer of the doclines, so the 118 seam must stay | **verified** | `steps.py:116,141,297,314,326,334` |
| 2 | `viewer.py` (`index.html`) references no module page | **verified** | `grep -n "modules/\|render_module" code_atlas/onboarding/viewer.py` → no page reference; the only `overview.md` mention is the `<noscript>` block |
| 3 | Nothing in-repo reads `artifact.json`'s `pages`/`isolated` keys | **verified** | the only readers of a written artifact are `recorded_pages` (manifest) and `architecture_diff` (dataset keys) |
| 4 | A tree written by the **pre-change** tool is fully cleaned by the **post-change** tool | **novel-untested** | resolved by an integration proof, not by argument: `test_a_pre_205_tree_is_cleaned_on_the_next_write` writes a tree with the old builder, runs the new tool, and asserts `modules/` is gone and no foreign file was touched |
| 5 | `total_count`/`truncated` in the payload change meaning-free | **verified** | `_payload` counts `len(written)`: 505 → 5, so `len(written) > limit` flips to false while `artifact.truncated` (the walk) still drives the flag — no field changes definition |

### Smallest change-list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | Remove `ModulePage`, `OnboardingArtifact.pages`, `.isolated`, `page_relpath`, `render_module`, `NO_DOCBLOCK`, the page loop and the `isolated` accumulation; prune `__all__` | `code_atlas/onboarding/artifact.py` | `quality_gate`, `generate_onboarding`, `artifact.json`/`manifest.json` shape, 7 test files | G1 G2 G4 R1 R2 R3 R4 AC1′ AC2′ | 9/9 |
| 2 | `ARTIFACT_VERSION` 1 → 2 | `artifact.py:77` | `.code-atlas/onboarding/artifact.json` consumers (none in-repo); `test_artifact_contract` | C5 H6 | 2/2 |
| 3 | Delete `- module pages:` and `- modules with no page (isolated, no summary):` from `render_overview` | `artifact.py:603-604` | AC5′'s byte comparison; `test_generate_onboarding` | R6 AC5′ | 2/2 |
| 4 | Drop the `"pages"` key from `manifest_dict` | `artifact.py:798` | `architecture_diff`'s operational-key set; `recorded_pages` (legacy read only); `test_architecture_diff` | H5 AC1′ | 2/2 |
| 5 | Remove C1's page rule, C2 + `MAX_PAGE_BYTES`, C5's isolated rule, C6, C7's page-index and isolated-order checks, the `render_module` import and the now-unused `max_results` parameter | `code_atlas/onboarding/quality_gate.py` | `build_artifact`'s call site; `test_onboarding_prose:281`; `test_onboarding_quality_gate` | G4 R3 AC4′ | 3/3 |
| 6 | Stop writing pages in `_write`; **keep** `_remove_recorded_pages`, `recorded_pages`, `PAGES_DIR` | `code_atlas/tools/generate_onboarding.py` | the anchor's committed tree (migration path); `test_generate_onboarding`, `test_ignore` | R4 H3 AC1′ | 3/3 |
| 7 | Drop `isolated_modules` from the `standard` payload | `generate_onboarding.py:293` | MCP payload readers; `test_generate_onboarding` | W3 AC1′ | 2/2 |
| 8 | Rewrite the tool docstring — the per-module-page and `isolated_modules` promises **deleted**, not stacked (R7.6) | `generate_onboarding.py:69-91` | `docs/TOOLS.md` parity | AC7 C1 | 2/2 |
| 9 | Drop `"pages"` from the operational-key set | `code_atlas/onboarding/architecture_diff.py:22` | `diff_architecture` payloads; `test_architecture_diff` | H5 | 1/1 |
| 10 | `docs/TOOLS.md`: delete the two superseded bullets (`:78-80` per-module pages + `isolated_modules`, `:82` "Tour and pages bounded by `CA_IMPACT_MAX_NODES`"); state what the tool now writes | `docs/TOOLS.md` | none identified — README's roadmap and every runbook name no per-module page (traced below) | AC7 | 1/1 |
| 11 | **Proof collateral** — retire or re-point the page assertions the change invalidates: `test_generate_onboarding.py` (19 hits), `test_onboarding_quality_gate.py` (9), `test_module_facts.py` (8), `test_artifact_contract.py` (4), `test_ignore.py` (2), `test_onboarding_viewer.py` (2), `test_business_modules.py` (1) | `tests/` | none | AC1′–AC5′ | 7/7 |
| 12 | **New guards** (all at the emitted tree, R6.9): no `modules/` path and the file set is exactly the five names, at two `impact_max_nodes` values · no emitted file matches `Stop \d+ of \d+` · the gate still **fails** on what is emitted (C4 step ceiling, C3 empty layer description, C1 prose filler) · a pre-205 tree is cleaned on the next write · the emitted-Markdown ceiling plus its growth guard | `tests/test_generate_onboarding.py`, `tests/test_onboarding_quality_gate.py` | none | AC1′ AC2′ AC3′ AC4′ AC6 | 5/5 |
| 13 | Working doc, `TOKEN_LEDGER.md` row, `BACKLOG.md` status | `docs/` | R7.2 | — | 3/3 |

### Recalled type-2 handles — every one answered

| Handle (claim) | Answer |
|---|---|
| `walk-budget-named-for-the-tool-that-walks` (124-C1) | **traced.** `grep -rn "impact_max_nodes" --include=*.py code_atlas/` → 8 tool consumers: `impact.py:203`, `impact_modules.py:132`, `check_architecture_rules.py:88`, `guided_tour.py:56`, `explain_path.py:52`, `trace_capability.py:188`, `reachable_from.py:53`, `generate_onboarding.py:99,165`. Folded: `generate_onboarding.py:99` **keeps** the budget for the walk (identical to `guided_tour.py:56`) and loses the file count it was leaking into. No new setting — the second sighting of this class is closed by removing the borrowing consumer, not by renaming it |
| `per-element-ceiling-leaves-total-unbounded` (133-C1) | **traced.** `find docs/onboarding -name '*.md' -printf '%s\n' \| paste -sd+ \| bc` on the anchor → `503220`, of which `du -sb modules` → `481616` (95.7 %). Post-change the same three files are `12440 + 5798 + 3366 = 21604 B`. Folded: AC6's ceiling is a **total** over the emitted Markdown, and it is paired with a growth guard, because a per-file ceiling leaves the file count free — which is exactly how 500 files got there |
| `ac-failure-mode-needs-the-right-guard` (085-C2) | **traced.** `grep -cE 'modules/\|render_module' tests/test_generate_onboarding.py` → `19` assertions that **expect** pages. Folded: AC3′/AC4′ are failure-mode ACs, so their guards must reach the failure — the 19 existing assertions are inverted (change-list 11) and the gate's remaining criteria get three recorded red runs (change-list 12), rather than an AC closed by a test that passes beside the failure |
| `fixture-shape-begs-the-question` (105-C2) | **traced.** The ticket's figures were re-derived on a real corpus rather than trusted: full rebuild of the anchor into a scratch DB at this branch's code (`24569 file(s), 262899 node(s), 2077473 edge(s)`) then `measure205.py` → `docline shapes: {'delimiter': 76, 'empty': 412, 'substantive': 12}`, `pages with a RESOLVED module edge: 496`. Folded: the criterion the ticket asked me to pick was measured before the maintainer chose, and the measurement is what made "keeps 12/500" a visible option |
| `prove-the-guard-fails` (019-C1) | **traced.** `grep -n "MAX_PAGE_BYTES\|C2\|C6" tests/test_onboarding_quality_gate.py` → 9 page-criterion assertions today. Folded: R6.5 is binding on all five new guards; each is recorded red against the pre-change builder at execute, and the three surviving gate criteria are each driven to raise |
| `total-count-is-the-true-total-not-the-page` (123-C1) | **traced.** `sed -n '276,300p' code_atlas/tools/generate_onboarding.py` → `"total_count": len(written)` with `page = written[:limit]`. Folded: `total_count` stays the true total of files written (505 → 5) and `truncated` keeps folding `artifact.truncated`; no field changes definition, and assumption 5 records it |
| `enumerating-test-closes-the-sibling-surface` (122-C2) | **traced.** The 22-site inventory was derived: `grep -rnE '\.pages\b\|PAGES_DIR\|render_module\|recorded_pages\|isolated\|page_relpath\|ModulePage' code_atlas/` (not hand-listed), and per-test counts came from a loop over `tests/*.py`. Folded: AC1′'s guard asserts the emitted **file set** derived from `OVERVIEW_NAME`/`TOUR_NAME`/`FLOWS_NAME`/`MANIFEST_NAME`/`VIEWER_NAME`, so a sixth emitted file cannot ship unnoticed |
| `empty-seam-inputs-masquerade-as-missing-data` (118-C1) | **traced.** `grep -rn "NO_DOCBLOCK" --include=*.py code_atlas/ tests/` → `artifact.py:61` (definition), `artifact.py:699` (its **only** renderer), plus two assertions in `test_module_facts.py`. Folded: the sentence goes with the renderer; `steps.py:334` omits an empty docline rather than narrating its absence, so no filler moves into `tour.md` |
| `rank-before-truncate` (126-C1) | **does not apply because** no page ranking or truncation survives this change: `render_module` and the page list are removed, so R5.8's subject leaves the code entirely. The tour walk's own cut (`tour_subgraph`) is untouched and already ranks inside the statement that truncates |

### Rule compliance

- **R7.1** — a deletion, no new setting, no new format. The rejected alternative 1 is the version
  that adds three mechanisms.
- **R7.4** — no flag is left behind to re-enable pages (H1).
- **R7.6** — `docs/TOOLS.md`'s two bullets and the docstring's promises are **deleted** in the same
  commit that changes the behaviour.
- **R5.7** — the recorded-page removal is kept and is the migration path; no `rmtree`.
- **R4.2** — identical input → identical output for everything that remains; `ARTIFACT_VERSION`
  bumps because the object shape changed, which is what the version is for.
- **R6.5 / R6.8 / R6.9** — every new guard reads the emitted tree, and each is recorded red first.
- **R6.7** — the emitted file set in AC1′'s guard is derived from the module's own name constants.
- **R3.x** — N/A: no node/edge vocabulary, field or qname rule moves; `contract.py` is untouched, so
  no contract bump (`ARTIFACT_VERSION` is the artifact's own shape stamp, not the graph contract).

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1′ no `modules/`; the emitted set is exactly five names, at `impact_max_nodes` 2 and 500 | integration | integration (`generate_onboarding` writes a real tree in `tmp_path`) | n/a | ✅ |
| AC2′ no emitted file cites a stop position | integration | integration (regex over every emitted file) | n/a | ✅ |
| AC3′ the no-pages guard is observed failing on the pre-change builder | integration | integration + **recorded red run** | n/a | ✅ |
| AC4′ the gate still runs and can still fail on what is emitted (C4, C3, C1-prose) | integration | integration ×3, each driven to raise | n/a | ✅ |
| AC5′ `tour.md`/`flows.md` byte-identical; `overview.md` identical minus two lines | integration | integration (two runs on one index, byte comparison) | n/a | ✅ |
| AC6 emitted-Markdown total under an argued ceiling, and the ceiling bites | integration | integration at two fixture sizes (the growth guard) | n/a | ✅ |
| AC7 both doc surfaces describe the removal; superseded text deleted | logic | grep assertion over `docs/TOOLS.md` + the docstring, plus the diff | n/a | ✅ |
| Assumption 4 — a pre-205 tree is cleaned on the next write | integration | integration (old builder writes, new tool cleans) | n/a | ✅ |

No `❌`, so no coverage-gap exclusion is needed, and no AC is input-shape-dependent: every row
asserts a value writable before the run (a file set, a regex miss, a byte comparison, a total under
a constant). The ceiling's **number** is argued from the anchor measurement above; `config.real_corpus_path`
is `null`, so that argument lives in the test comment and in this doc, and the guard that makes the
number bite is the growth pair, not the corpus.

### The ceiling, argued

`MAX_EMITTED_MARKDOWN_BYTES = 131_072` (128 KiB) over `overview.md + tour.md + flows.md`.

- Measured on a 24,535-file repo at `max_results = 10`: **21,604 B**.
- Nothing in those three files scales with file count. Every section is capped by configuration:
  steps ≤ `MAX_TOUR_STEPS` (15), layer descriptions ≤ 12 (`SLOT_LIMITS`), and each table ≤
  `max_results` rows.
- The row-capped tables *do* scale with `max_results`, and the anchor runs it at 10 against a
  default of 50 — so a default-configured repo of that size lands near 60–70 KiB. 128 KiB is that
  figure with roughly 2× headroom, and the growth guard is what keeps the number honest rather than
  slack (`test_the_budgets_are_not_slack`'s discipline, applied to a tree whose fixture is tiny).

### Proving test

```
.venv/bin/python -m pytest tests/test_generate_onboarding.py::test_the_emitted_tree_carries_no_module_pages -q
```

Fails pre-change (the fixture's tree contains `modules/*.md`), passes post-change. The full sweep is
`.venv/bin/python -m pytest -q` against the 2,778-test baseline.

### Rollback + porting

- **Rollback:** `git revert` the commits on `fix/205-a-module-page-per-node-budget-slot`, or close
  the PR unmerged. A repo that regenerated in between gets its pages back on the next write, and
  `ARTIFACT_VERSION` returns to 1 with the revert.
- **Porting:** one repo (`app`). No adapter, no schema, no contract version.

### SCOPE

`SCOPE: M` — re-affirmed. The change list is 13 rows over 4 source files, 7 test files and 1 doc;
it is a deletion, and the largest row is proof collateral. No tier crossing, so the
*outgrew-its-ticket* nudge does not fire.

## Phase 3 — execute

Complete on disk. Branch `fix/205-a-module-page-per-node-budget-slot`, based on `main` at `f1c5bfb`.

### What landed

`generate_onboarding` writes **five files**, not 505. The `ModulePage` model, its renderer, the
manifest's `pages` key, the `isolated` bucket and the four quality-gate criteria whose subject was a
page are gone. The tour walk, every aggregate table, the 117 prose seam and the 118 read-through are
untouched.

Kept deliberately, each with a live consumer:

| Kept | Consumer | Why |
|---|---|---|
| `recorded_pages`, `_remove_recorded_pages`, `PAGES_DIR` | any repo whose committed tree predates 205 | R5.7 — the first write after 205 deletes exactly the pages the previous manifest recorded (proven, not argued: `test_a_pre_205_page_tree_is_cleaned_on_the_next_write`) |
| `_rationale_line`, `_shown_suffix` | `scripts/tour_report.py:45` | it renders the pre-111 "before" figure for the tour-byte benchmark |
| `"pages"` in `architecture_diff._MANIFEST_KEYS` | a pre-205 snapshot being diffed | the set is a **strip**-list; dropping the key would make 500 page paths read as architectural drift |
| the 118 read-through (`module_facts`, `summarize_modules`) | `build_steps` → the 117 prose seam | the doclines feed each step's prose facts (`steps.py:334`) |

### Verification sweep — Axis 1, the file set

`git diff --stat main` — 10 files, every one inside the Gate-2 change list:

```
Ran at 6b0998d (the commit under review)
 code_atlas/onboarding/architecture_diff.py         |   2 +
 code_atlas/onboarding/artifact.py                  | 190 +----------
 code_atlas/onboarding/quality_gate.py              |  47 +--
 code_atlas/tools/generate_onboarding.py            |  49 ++-
 docs/TOOLS.md                                      |  20 +-
 tests/test_artifact_contract.py                    |  37 +-
 tests/test_generate_onboarding.py                  | 369 ++++++++-----------
 tests/test_layer_diagram.py                        |   1 -
 tests/test_module_facts.py                         | 101 +++---
 tests/test_onboarding_prose.py                     |   6 +-
 tests/test_onboarding_quality_gate.py              | 192 +++-------
```

No stray references. Every removed symbol is unreachable from production code — `scripts/` and
`onboarding_llm/` included, the two trees the design's first trace forgot:

```
Ran at 6b0998d
$ grep -rn "ModulePage\|render_module\|page_relpath\|NO_DOCBLOCK\|MAX_PAGE_BYTES\|isolated_modules\|\.pages\b\|\.isolated\b" \
    --include=*.py code_atlas/ scripts/ onboarding_llm/ | grep -v pycache
exit=1   (no match)
```

Over `tests/` the same sweep returns six hits, and **every one asserts the name is absent** — five
in this ticket's own new guards, plus a pre-existing one at `test_onboarding_viewer.py:239`
(`assert "render_module" not in source`) that still passes. Recorded rather than filtered away: a
sweep whose result I would have had to describe as empty was not empty.

**Two deviations from the approved change list, both recorded rather than absorbed:**

- **D1 — change-list row 9 is REVERSED.** The design said to drop `"pages"` from
  `architecture_diff._MANIFEST_KEYS`; the code falsified it. That set is stripped from a snapshot
  **on load** (`architecture_diff.py:115`), so a pre-205 manifest diffed against a post-205 one
  needs the key stripped, not read. The file is still touched, but for a three-line comment saying
  why the entry stays. Contract condition `MANIFEST-DROPS-PAGES` was amended for the same reason,
  and **both amended conditions were then observed failing against `main`** in a throwaway worktree
  (exit 1 each), so the t0 guarantee holds for them; the untouched t0 contract is kept beside the
  live one at `.mango/run-contract-205.t0.txt`.
- **D2 — two proof-collateral files the design's blast-radius trace missed:**
  `tests/test_layer_diagram.py` (builds an `OnboardingArtifact(pages=())`) and
  `tests/test_onboarding_prose.py` (three `check_artifact(…, max_results=50)` calls; this one the
  design *did* name at `:281`, but only one of its three call sites). The trace pattern searched
  `\.pages\b` and `"pages"` — a **keyword argument** `pages=` matches neither. Recorded as a
  candidate lesson: an attribute-shaped grep does not find a symbol used as a keyword argument.

### Verification sweep — Axis 2, design conformance

| Gate-2 Approach bullet | Verdict |
|---|---|
| No `modules/` tree is emitted; the page model, renderer, manifest key and gate criteria go | implemented-as-approved |
| The tour walk keeps `impact_max_nodes`; nothing else borrows it | implemented-as-approved |
| Every aggregate comes out byte-identical | implemented-as-approved — proven below |
| `recorded_pages` + `_remove_recorded_pages` + `PAGES_DIR` stay as the migration path | implemented-as-approved |
| The 118 seam stays; only `NO_DOCBLOCK` goes with its renderer | implemented-as-approved |
| C1-prose, C3, C4, C5, C7's layer/crossing order stay | implemented-as-approved, with one refinement: **C5 now reads `artifact.stops` directly** rather than each page's `scc`. That is a superset of what it read before (every page was a stop; not every stop had a page), so the check widened rather than narrowed |
| `architecture_diff` drops the `"pages"` key | **deviated** — see D1 |

### AC5′ — the byte comparison, run pre-change vs post-change on one index

Both runs emit from the same fixture index; the pre-change side is a throwaway worktree at `main`.

```
Ran at f1c5bfb (pre) / 6b0998d (post)
$ .venv/bin/python emit.py <worktree at main>  →  wt-main: 9 files emitted, total_count=9
$ .venv/bin/python emit.py <this branch>       →  code-atlas: 5 files emitted, total_count=5

$ diff emit-main/FILES.txt emit-branch/FILES.txt
4,7d3
< modules/app/A.aa.md
< modules/app/B.aa.md
< modules/app/Leaf.aa.md
< modules/routes/web.aa.md

$ diff emit-main/tour.md  emit-branch/tour.md    → byte-identical
$ diff emit-main/flows.md emit-branch/flows.md   → byte-identical
$ diff emit-main/overview.md emit-branch/overview.md
10,11d9
< - module pages: 4
< - modules with no page (isolated, no summary): 0
```

`tour.md` and `flows.md` byte-identical; `overview.md` differs by exactly the two count lines A1
widened the AC for, and by nothing else. The emitted set loses exactly the four pages.

### R6.5 — every new guard observed failing against pre-change code

The seven new/repointed guards, run in a worktree at `main` with only the test file copied in:

```
Ran at f1c5bfb (a throwaway worktree at main, branch test file copied in)
FAILED tests/test_generate_onboarding.py::test_the_emitted_tree_carries_no_module_pages
FAILED tests/test_generate_onboarding.py::test_the_emitted_file_set_does_not_move_with_the_impact_budget
FAILED tests/test_generate_onboarding.py::test_no_emitted_file_cites_a_stop_position
FAILED tests/test_generate_onboarding.py::test_the_overview_no_longer_counts_pages_or_isolated_modules
FAILED tests/test_generate_onboarding.py::test_the_emitted_markdown_stays_under_its_ceiling
FAILED tests/test_generate_onboarding.py::test_the_tool_surfaces_do_not_promise_a_module_page_tree
FAILED tests/test_generate_onboarding.py::test_a_pre_205_page_tree_is_cleaned_on_the_next_write
7 failed in 1.90s
```

And the two surviving gate criteria the ticket's AC4′ names were **sabotage-proven** on this branch —
each check deleted in turn, each time exactly its own test went red and nothing else did:

```
Ran at 6b0998d for `quality_gate.py` and its test, which are byte-identical to the
committed tree; the production check was deleted in the working tree and restored
# C4's step ceiling deleted:
FAILED tests/test_onboarding_quality_gate.py::test_c4_tour_over_the_step_ceiling
1 failed, 11 passed in 0.05s
# C1's prose filler rule deleted:
FAILED tests/test_onboarding_quality_gate.py::test_c1_a_step_narrative_that_only_restates_its_own_title
1 failed, 11 passed in 0.04s
```

### A behaviour change worth naming: `truncated` now answers one question

`list_truncated` folded *"a page's neighbour list was capped"* into the same `truncated` flag as
*"the walk left an indexed file out."* The page half is gone, so the field now answers exactly one
question — the `one-field-two-questions` class (`189`, `022`, `202`), resolved here by deletion
rather than by splitting a key. Traced to change-list row 1, and `total_count` stays the true total
of files written: 505 → 5.

**Design assumption 5 was wrong, and the challenger is what falsified it.** I recorded this as
*"no payload field changes definition"*; it does. On an index whose page neighbour lists would have
been capped, pre-205 reported `truncated: true` and post-205 reports `false`, so `overview.md` and
`tour.md` are **not** byte-identical on that class of index — a third difference beside the two
deleted count lines, and one my fixture could not see because its lists were never cut. The
narrowing is still correct (a flag may not attest to a cut the artifact no longer contains, R5.6),
but the claim was over-broad. Corrected in A1b and **pinned** by
`test_truncated_now_answers_only_the_walk_question`, observed red against `main`.

### Delta-green against the recorded baseline

```
Ran at 6b0998d
$ .venv/bin/python -m pytest -q
2774 passed in 272.21s (0:04:32)
```

Baseline was **2,778 passed** at `f1c5bfb`. The **−4** is entirely inside the six touched test
files, and is accounted for rather than asserted:

```
Ran at 6b0998d / f1c5bfb
$ pytest <the six touched files> --collect-only
branch: 87 tests collected     main: 91 tests collected
```

The page-rendering suite (task 108's neighbour cap, the SCC stop line, the 8 KB before/after, the
duplicate/absent-page and page-order criteria) went with its subject; seven new guards and three
repointed ones came in. **No test outside those six files moved, and nothing was skipped.**

`.venv/bin/python -m ruff check .` → `All checks passed!`
`.venv/bin/python -m mypy code_atlas onboarding_llm` → `Success: no issues found in 85 source files`

### `scripts/gate.sh` — 14 passed · 3 failed, and all three are this machine, not this diff

```
Ran at 6b0998d
  FAIL mypy (code_atlas + onboarding_llm)
      scripts/gate.sh: 49: /home/you/WORKSPACE/PROJECTS/code-atlas/.venv/bin/mypy: not found
  FAIL pytest -q
      scripts/gate.sh: 49: /home/you/WORKSPACE/PROJECTS/code-atlas/.venv/bin/pytest: not found
  FAIL phpstan level max (R6.6)
      Internal error: "phar:///home/you/WORKSPACE/Projects/code-atlas/adapters/php/vendor/
      phpstan/phpstan/phpstan.phar/…/phpstorm-stubs/Core/Core.stub" is not a file
  14 passed · 3 failed · 0 skipped
```

**Diagnosed, not waved away.** `.venv/bin/mypy` exists; its shebang reads
`#!/home/you/WORKSPACE/Projects/code-atlas/.venv/bin/python3` — **`Projects`, where the
directory is `PROJECTS`** — so the kernel cannot find the interpreter and `sh` reports the script
itself as not found. **27** of the venv's console scripts carry that shebang, and PHPStan resolves
its bundled stubs through the same wrong-case path. The venv and `adapters/php/vendor` are
gitignored local state: `git diff --name-only main` names **no** file under either, so both failures
reproduce on `main` and neither can be this change's doing.

Each failing check was therefore run in the form that starts: `python -m mypy` over both packages is
clean (85 files), `python -m pytest -q` is the 2,774-green above. **PHPStan could not be run at all
on this machine** — it dies before analysing — and the PHP adapter is untouched by this diff
(`git diff --name-only main` lists no `adapters/` file). Recorded as an unproven check, not a pass.

The fix is environment-side and deliberately **not** in this diff: recreate `.venv` and
`adapters/php/vendor` from the correctly-cased path.

### Matrix progress

| ID | Ph3/4 proven by |
|---|---|
| G1, R1, AC1′ | `test_the_emitted_tree_carries_no_module_pages`, `test_the_emitted_file_set_does_not_move_with_the_impact_budget` |
| G2, R3 | the page whose Summary said there was no summary is gone with the tree; `test_a_missing_docblock_is_absence_at_the_seam_not_an_invented_sentence` holds 118's claim at the docline's surviving consumer |
| G3, R2, AC2′ | `test_no_emitted_file_cites_a_stop_position` |
| G4, AC4′ | `test_onboarding_quality_gate.py` — five criteria, each with a red fixture, two sabotage-proven |
| G5, R5, AC6 | `test_the_emitted_markdown_stays_under_its_ceiling` + `test_the_emitted_markdown_does_not_grow_with_the_repo` |
| R4 | there is no page mode left to ask for (H1) |
| R6, AC5′ | the pre/post byte comparison above |
| R7, R8 | no selection or tier logic touched; `git diff main -- code_atlas/resolver.py code_atlas/store.py` is empty |
| C1–C5 | R7.1 (a deletion), R6.5 (7 red runs + 2 sabotages), R6.8 (each failure-mode AC has a guard that reaches it), R6.9 (every guard reads the emitted tree), R4.2 (byte comparison + `ARTIFACT_VERSION` 2) |
| AC3′ | the seven-way red run above |
| AC7 | `test_the_tool_surfaces_do_not_promise_a_module_page_tree` |

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` — the rule-book-grounded seat was waived by the run argument, so
**no rule-book-grounded review of this diff exists**. `CHALLENGER: ON`.

Verdict: **clean (challenger only — REVIEWER: OFF)**, after two rounds. Round 1 was **not** clean.

### The challenger's round-1 result

`CHALLENGER: 12 requirements | 10 met | 1 not met | 0 can't tell` (128,653 tokens / 45 tool-uses).
It ran ticket-blind: its inputs were the raw-ticket extract and `git diff main..HEAD --
code_atlas/ tests/ docs/TOOLS.md`, path-restricted so `work_doc_mode: embed` could not leak the
working doc — the failure mode that cost 203 and 204 a discarded seat. It reported its own
independence check, and it **mutated production code four times to prove the guards bite**, each
time restoring the file and verifying with `md5sum` plus a clean `git status`.

Three of its ten `MET` verdicts (Scope 1 / Scope 3 / Scope 4) are met **because the subject was
removed**, not because the AC's literal letter was satisfied — it said so explicitly rather than
scoring them as passes, which is the call I wanted made independently.

**Two findings, both real, both fixed on this branch:**

| # | Finding | Fix |
|---|---|---|
| REQ-7 / F2 | **The byte-identity claim is false on a reproducible class of index.** `truncated=truncated or list_truncated` became `truncated=truncated`, and `overview.md`/`tour.md` both render that value. On a wide-hub fixture (`max_results=5`, a hub with 10 callees) pre-205 reported `truncated: true` and post-205 reports `false`. My AC5′ comparison could not see it: the cycle fixture's neighbour lists were never cut. The commit message repeated the over-broad claim | The narrowing **stands** — a flag may not attest to a cut the artifact no longer contains (R5.6) — but it is now **declared and pinned**: A1b widens AC5′'s exception, and `test_truncated_now_answers_only_the_walk_question` asserts both directions on exactly that fixture class. **Observed red against `main`** (`assert True is False`). The commit message was corrected before anything was pushed |
| F1 | **`index.html` ships a false claim to every downstream repo.** `viewer.py:774` wrote *"one page per module under `modules/`"* into the emitted page's `<noscript>` companion list — a promise the code stopped keeping, in the artifact itself rather than in a doc, and asserted by no test (`test_onboarding_viewer.py` checked only that `overview.md` and `tour.md` appeared). My change list missed it because I read a **truncated** grep of `viewer.py` and took the visible hits for all of them | The sentence now names `overview.md`, `tour.md` and `flows.md` — `flows.md` was missing from it too — and the existing degradation test grew three assertions: `flows.md` present, `modules/` absent, `per module` absent. **Observed red against `main`'s viewer** |

F3 is informational and outside this diff: `docs/tasks/210_*.md` quotes
`payload["isolated_modules"] = len(artifact.isolated)` as live code in its *Why this exists*. 210 has
not executed; whoever picks it up will find that line gone. Recorded in `BACKLOG.md`'s follow-ups
rather than edited into another ticket's text.

### Scope reconciliation

- **File axis:** the two fixes add `code_atlas/onboarding/viewer.py` and
  `tests/test_onboarding_viewer.py` to the touched set — **12 files**, two beyond the Gate-2 list.
  Both are the *consumers* the change list should have named (R6.9: the emitted page is a consumer
  of the promise; the flag is rendered into two committed files), so they are recorded as **D3** and
  adjudicated here rather than absorbed. Nothing else moved; no untouched line was reformatted.
- **Behaviour axis:** every Gate-2 Approach bullet is `implemented-as-approved` except the one
  already recorded as D1, plus assumption 5, which the challenger falsified (above).

### Regression check

The Phase-1 blast radius re-checked at the reviewed SHA: `architecture_diff` (the strip-list keeps
`"pages"`), `quality_gate` (five criteria, each with a red fixture), the `artifact.json`/`manifest`
consumers (`V2_KEY_PATHS` derived from V1), `scripts/tour_report.py` (`_rationale_line` kept), and
`onboarding_llm` (mypy clean over both packages). No caller of a removed symbol survives outside
tests, and every test hit asserts the name's **absence**.

### Delta-green after the two fixes

```
Ran at 01b5dc7
$ .venv/bin/python -m pytest -q
2775 passed in 295.45s (0:04:55)
```

**2,775** against the 2,778 baseline — the −3 is the round-1 −4 plus the one new guard the
challenger's finding earned. `ruff check .` clean; `mypy code_atlas onboarding_llm` clean (85 files).

### `Reviewed at`

`Reviewed at 01b5dc7` — the tree the challenger inspected plus the two rounds of fixes it caused.

**Reviewed files (13):** `code_atlas/onboarding/artifact.py` · `code_atlas/onboarding/quality_gate.py`
· `code_atlas/onboarding/architecture_diff.py` · `code_atlas/onboarding/viewer.py` ·
`code_atlas/tools/generate_onboarding.py` · `docs/TOOLS.md` ·
`tests/test_generate_onboarding.py` · `tests/test_onboarding_quality_gate.py` ·
`tests/test_artifact_contract.py` · `tests/test_module_facts.py` · `tests/test_layer_diagram.py` ·
`tests/test_onboarding_prose.py` · `tests/test_onboarding_viewer.py`.

**Working doc:** `docs/tasks/205_a-module-page-per-node-budget-slot.md` (embedded; exempt from the
staleness comparison, along with `.mango/`).

## Phase 5 — finalise

**Stale-review guard: not stale.** `git diff --name-only 01b5dc7..HEAD` returns only
`docs/tasks/205_a-module-page-per-node-budget-slot.md` — the marker-bearing working doc, which the
guard exempts by construction. No non-exempt file changed beyond the reviewed set, and the tree is
clean.

`config.pr_checklist_path` is unset, so there is no project finalise-checklist to walk; the PR
template's own self-check is filled in the PR body.

### The learning loop

`CLAIMS: 5 claim(s) from 1 lesson entr(ies) | T1=0 T2=3 T3=1 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 2 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 2 proposed | 0 human-ratified | destinations: docs/AGENT_BRIEF.md, docs/ENGINEERING_RULES.md | mango files written: 0`

| Claim | Type | Handle / key | Recurrence | Proposed destination |
|---|---|---|---|---|
| `205-C1` an attribute-shaped grep misses the same symbol as a keyword argument | 2 (process) | `grep-the-keyword-argument-too` | 1 | stays in `lessons_path` |
| `205-C2` a search piped through a cap is not a search | 2 (process) | `a-capped-search-is-not-a-search` | **2** (203, 205) | **`agent_brief_path`** — awaiting ratify |
| `205-C3` a strip-list is not an emit-list | 2 (code) | `strip-list-is-not-an-emit-list` | 1 | stays in `lessons_path` |
| `205-C4` this machine's wrong-case venv breaks the gate launcher | 5 (environment) | area: environment / gate, `verified-at: 2026-09-02` | 1 | stays in `lessons_path` |
| `202-C4` `one-field-two-questions`, fourth sighting | 2 (code) | `one-field-two-questions` | **4** (189, 022, 202, 205) | **`rulebook_path`** — awaiting the ratify it has been waiting for since 202 |
| — skill-gap SIGNAL: a run contract has no path for a condition the code falsifies after t0 | 3 | — | 1 | `skill_gap_path` — **written, signal only** |

**Falsification, before the ratification gate.** `205-C2`: still true — reproduced this run, and the
cheap check is re-running the same grep without the cap, which prints `viewer.py:774`. `202-C4`:
still true; this sighting is a *use* (the field narrowed by deletion), not a new defect, and the
check is a grep for a payload field folding two questions. Neither is blocked.

**Nothing was promoted.** Both proposals need a per-claim human ratify, and the handover
authorisation covers exactly two outward actions — push the branch, open the PR — so the rule book
and the agent brief are **untouched**. `/mango:promote` is the cross-ticket pass for the two
recurring classes; naming it here is not running it. `mango files written: 0`.

### Cost ledger

| Dispatch | Phase | Tokens | Tool-uses |
|---|---|---|---|
| `challenger` as refine's exposure-checker | 0 refine | 101,783 | 31 |
| `challenger`, ticket-blind | 4 review | 128,653 | 45 |
| `reviewer` | — | **not spent** — waived by `--no-reviewer` | — |

`LEDGER TOTAL: 230,436 tokens · top cost driver: the ticket-blind challenger at review`

Scope of that number, stated honestly: it measures **subagent dispatch only**. The main loop — this
run's own greps, test runs, the anchor rebuild's output — is **unmeasured (host surfaces no usage
block)**, and it is the larger term. For the output-noise side the optimizer's own analytics are the
instrument (`rtk gain`); mango does not self-instrument the main loop, and no dispatch-vs-noise split
is implied here.

### Two ceilings raised, with their arguments

`BACKLOG.md` 8,700 → 8,800 and `TIER1_BUDGET` 25,800 → 25,900, both argued in the tests that hold
them. Measured 8,751 and 25,845. The whole 100 is one two-line follow-up plus 205's row flipping to
`done`; R7.6 ran first on both files and came back empty, and the three other facts this run earned
went to `LESSONS.md` and this file rather than to a tier-1 doc — which is what kept it to one raise.

### Outward actions

| # | Action | Status |
|---|---|---|
| 1 | push `fix/205-a-module-page-per-node-budget-slot` (carrying the claims and the skill-gap signal, so the durable lesson reaches a shared ref before PR-open) | **done** |
| 2 | open PR against `main` | **done** — [#254](https://github.com/cuongdinhngo/code-atlas/pull/254) |
| 3 | push the bookkeeping commit (ledger row, BACKLOG status, the two ceilings) | **done** — same branch, same authorised action |
| 4 | ratify `205-C2` → `agent_brief_path` and `202-C4` → `rulebook_path` | **not taken** — a per-claim human ratify, which the handover authorisation does not cover. `/mango:promote` is the cross-ticket pass |
| 5 | merge #254 | **not taken inside this run** — `autorun` never merges |
| 6 | tracker comment / transition | **N/A** — the tracker is this repo; `BACKLOG.md` + the task frontmatter are the transition, and both are in the diff |
