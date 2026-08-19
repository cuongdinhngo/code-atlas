---
id: 107
slug: a-page-with-no-neighbours-and-no-summary-is-filler
title: Onboarding — a module page with no neighbours and no summary is filler, and 500 of them read as coverage (M11)
phase: 3
milestone: M11
status: done
depends_on: [088, 106]
---

## Why this exists (measured on a real repo, not guessed)

Same run as 106 (private PHP monorepo, 18,926 indexed files, default knobs). Independently of *which*
modules the budget selects, `generate_onboarding` emits **one page per selected module unconditionally**
— including pages that carry no fact a reader cannot get from the file path:

```
# `legacy/alpha/web/application/reviewforms/view/index.php`
## Role
entry-point
## Layer
alpha
## Summary
(none)
## In the tour
Stop 232 of 500. entry point (zero inbound)
## Neighbours
- outgoing: (none)
- incoming: (none)
```

Counted from the emitted `manifest.json`: **500 / 500** pages have both neighbour lists empty and
**500 / 500** have an empty `docline`. 442 of them are PHP view templates under one legacy tree. The
tree is 3.4 MB on disk, of which `manifest.json` is 204 KB and `index.html` 249 KB.

**Why this is its own ticket, not 106's tail:** 106 changes *which* nodes are selected; even after it
lands, a real repo will always contain genuinely isolated modules (dead view scripts, one-off
utilities), and the current renderer will still spend a page on each and still present the result as
coverage. `truncated: true` plus "500 module pages" reads to a newcomer as *"500 modules documented"*
when the honest statement is *"500 modules named, 0 described, 0 connected."* A count of pages is not
a state of the world — the same distinction `README` already draws for this tool.

## What this ticket must decide (do NOT pre-empt it here)

- **Suppress or collapse the empty page.** A module with zero degree and no summary could be omitted
  entirely, or rolled into one counted list per layer (`442 isolated view templates under alpha — see
  list`), instead of 442 near-identical files.
- **Or make emptiness a stated finding.** Zero in, zero out, no docblock is itself information — an
  orphan candidate (`find_orphans` already owns that concept). If the page stays, it should say what
  the emptiness *means* rather than print three `(none)`s.
- **Report the composition of what was written.** Whatever the rule, the payload and the overview
  could carry a counted breakdown — pages with neighbours, pages with a summary, pages that are bare
  — so the reader can calibrate the tree instead of trusting a page count.
- **Decide the interaction with the viewer (089)** — a collapsed group must not leave the HTML with
  dead links, and `manifest.json` remains the only record of what the tool may later delete (050).

**Explicitly rejected in advance:** naming a directory, suffix, or framework convention to decide
"this file is not worth a page" (R2.2). The test must be graph shape plus the presence of a summary.

## Acceptance criteria
- **AC1** — the chosen rule is recorded in the design phase with alternatives and why, holding R1.1,
  R2.2 and R4.2 (identical index → byte-identical tree).
- **AC2** — on the private-monorepo run, the emitted tree no longer contains a page whose only content
  is a path, a role, a layer and three `(none)`s; the new page count and the counted composition are
  recorded before/after.
- **AC3** — the manifest keeps a complete record of every path the tool wrote, so regeneration still
  deletes only its own pages and still refuses a tree it did not write (050 / 088's rule); a test
  covers the collapsed-group case.
- **AC4** — the 089 viewer renders the new shape with no dead link, and its tests stay green.
- **AC5** — the three pinned public repos do not lose a page that carried real content; their page
  counts before/after are recorded.

## Out of scope
- Seed selection and budget spending — 106.
- Making `StructuralSummarizer` produce prose for a template with no class or docblock, and the LLM
  summarizer (085 / 090). This ticket decides what to do with an *absent* summary, not how to author
  one.
- Any change to `find_orphans` (031).

## References
- Evidence: the page sample and counts above, from the emitted `manifest.json` of the same run as 106.
- `code_atlas/onboarding/artifact.py` (`build_artifact`, `render_module`, `manifest_json`).
- `code_atlas/tools/generate_onboarding.py` (`_write`, `_payload`); `code_atlas/onboarding/viewer.py`.
- 088 `docs/tasks/088_generate-onboarding-markdown.md`; 089; 050 (the tool deletes only what it wrote);
  031 (`find_orphans`). PLAN §14, §15 (M11).

<!-- ===================== mango working doc (embed) — raw ticket above ===================== -->

## Session status
- **Runner:** `/mango:solve 107 with skipped review & challenger` — standing maintainer approval to
  suggest + do the best option, pass all gates, then commit + push + open PR.
- **`CHALLENGER: OFF` (`--no-challenger`).** **`REVIEW: skipped`** (operator-waived) — verification
  runs in the main loop and is recorded empirically.
- **work_doc_mode:** embed (plain local-file ticket; tracked since #132 but not a scaffold stub).
  **Branch:** `fix/107-a-page-with-no-neighbours-and-no-summary-is-filler`.
- `STRUCTURE: native` · `TRACK: backend` · `SCOPE: M` · `TIER: full`.
- **Phase:** Phase 5 — finalise, **PR [#133](https://github.com/cuongdinhngo/code-atlas/pull/133) open**. **Outcome: all five ACs met** (AC2 under the Gate-1 amendment).

## Phase 0 — refine
`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved-at-design | 0 ASSUMED | skip: no`

**Premise check — every referenced source resolves** (`onboarding/artifact.py`,
`onboarding/viewer.py`, `tools/generate_onboarding.py`, tasks 088 / 089 / 050 / 031, PLAN §14/§15).
No `PREMISE FALSIFIED`.

**But the ticket's headline evidence is STALE — 106 fixed half of it.** 107 was written from a
pre-106 run. Re-measured on the same anchor monorepo at `f3d48a9`:

| 107's claim (pre-106) | Re-measured (post-106) |
|---|---|
| "**500 / 500** pages have both neighbour lists empty" | **0 / 500** |
| "**500 / 500** have an empty `docline`" | **500 / 500** — unchanged |
| "442 of them are PHP view templates under one legacy tree" | those files are no longer selected at all |

The ticket **anticipated exactly this** ("even after it lands, a real repo will always contain
genuinely isolated modules … and the current renderer will still spend a page on each"). That
prediction holds — the defect reproduces post-106, just not on the repo 107 cites:

| Repo | Pages | **Bare** (no neighbours *and* no summary) | Pages with no summary |
|---|---|---|---|
| `laravel/laravel` (pinned) | 26 | **20 (77 %)** | 26 |
| `symfony/demo` (pinned) | 51 | **7** | 51 |
| `brick/math` (pinned) | 32 | 0 | 32 |
| sparse fixture (6 isolated + 1 pair) | 8 | **6 (75 %)** | 8 |
| anchor monorepo | 500 | **0** | 500 |

So the work is real and now has **real-repo witnesses** (laravel, symfony) rather than the anchor
repo. One second-order fact worth carrying into design: `StructuralSummarizer` yields **no docline on
any file of any repo measured** (26/26, 51/51, 32/32, 500/500), so the "no summary" half of the test
is currently never discriminating — the conjunction still belongs in the rule, because 090's LLM
summarizer turns it on.

The four candidates in *What this ticket must decide* are **how-decisions** resolved at Gate 2 under
the standing approval; 0 want-decisions.

## Phase 1 — analysis

### Requirements matrix

| # | Source | Requirement | Type | Status | Proven by |
|---|---|---|---|---|---|
| G1 | title + *Why this exists* | A page count must not read as coverage: a page whose only content is a path, a role, a layer and three `(none)`s must not ship as documentation | G | met | `test_generate_onboarding_suppresses_a_contentless_page_and_counts_it` — red pre-fix |
| R1 | *decide* bullet 1 | Suppress **or** collapse the contentless page | R | met | suppression for provably degree-0 modules (`build_artifact`) |
| R2 | *decide* bullet 2 | **Or** make emptiness a stated finding on the page | R | met | `_absent()` states the hidden count for a budget-cut list — **both** apply, to different populations |
| R3 | *decide* bullet 3 | Report the **counted composition** of what was written | R | met | overview line + `manifest.isolated` + viewer lines + `isolated_modules` |
| R4 | *decide* bullet 4 | Viewer (089) interaction: no dead link; manifest stays the record of what may be deleted | R | met | `stops[].page: null` + `test_the_viewer_names_the_modules_it_has_no_page_for` |
| C1 | R2.2 + ticket | The test is graph shape + summary presence — no directory, suffix, or framework name | C | met | test reads degrees + summary presence only; CI grep-gates green |
| C2 | R4.2 | Identical index → byte-identical tree | C | met | `test_generate_onboarding_composition_is_byte_stable` + pre-existing byte tests |
| C3 | 050 / 088 | The manifest records every path written, so regeneration deletes only its own pages and still refuses a foreign tree | C | met | `test_generate_onboarding_deletes_a_page_that_became_contentless` |
| C4 | R1.1 / R1.4 | No language branch; `artifact.py` stays pure presentation (no SQL, no store import) | C | met | no store import in `onboarding/`; CI grep-gate green |
| C5 | R7.1 | Smallest useful change | C | met | diff is a strict subset of the approved list (item 4 unneeded) |
| C6 | R7.5 | Comments ≤ 3 lines | C | met | every added comment ≤ 3 lines |
| AC1 | AC1 | Rule recorded with alternatives + why; holds R1.1/R2.2/R4.2 | AC | met | Phase 2 §Decision + §Rejected |
| AC2 | AC2 (**amended — see below**) | The emitted tree no longer contains a contentless page; page count + composition recorded before/after | AC | met | Phase 3 table — laravel 20→0, symfony 7→0 contentless pages |
| AC3 | AC3 | Manifest keeps a complete record of what was written; a test covers the suppressed/collapsed case | AC | met | Phase 3 §AC3 |
| AC4 | AC4 | Viewer renders the new shape with no dead link; 089 tests stay green | AC | met | Phase 3 §AC4 — all 089 tests green |
| AC5 | AC5 | The three pinned repos lose no page that carried real content; counts before/after recorded | AC | met | Phase 3 table — brick 32→32, anchor 500→500, stops unchanged everywhere |

**Counts:** 1 G · 4 R · 6 C · 5 AC = **16 rows, 0 unfilled cells.**

### AC validation — one AC needs amending, and I am proposing the amendment
**AC2 as written names "the private-monorepo run" as its proving ground. That is now vacuous:** post-106
the anchor repo emits **0** contentless pages, so the AC would pass without any code change — a
false-green. Proposed amendment, for ratification at Gate 1:

> **AC2 (amended)** — on the repos that *do* emit contentless pages — `laravel/laravel` (20 of 26),
> `symfony/demo` (7 of 51) and an authored sparse fixture (6 of 8) — the emitted tree no longer
> contains a page whose only content is a path, a role, a layer and three `(none)`s; page count and
> counted composition are recorded before/after for each. The anchor monorepo is re-run as a
> **no-regression** check (expected: unchanged at 500 pages, 0 bare).

This keeps the AC's intent (prove it on a real repo, not only a fixture — `LESSONS.md`
`fixture-shape-begs-the-question`) while pointing it at repos where the defect exists.
`CLARIFICATIONS: 0 asked (standing approval) | 1 AC amendment proposed`.

## Phase 2 — design

### The measurement that shaped the decision
A contentless page has two possible causes, and they need **opposite** treatments:

| Cause | laravel | symfony | brick | anchor | fixture @ budget 1 |
|---|---|---|---|---|---|
| **genuinely degree-0** in the full graph | **20** | **7** | 0 | 0 | 0 |
| **budget-cut** — has edges, none admitted | 0 | 0 | 0 | 0 | **1** (`routes/web.aa`) |

Suppressing the second kind would **hide a real dependency** — the module has neighbours, the walk
just could not afford them (102, `do-not-attest-past-the-payloads-resolution`). So R1 and R2 are not
alternatives, as Gate 1's matrix assumed; each is correct for one population.

### Decision
**D1 — a page is suppressed only when the module is *provably* contentless:** full-graph
`fan_in == fan_out == 0` **and** no summary. That is laravel's 20 and symfony's 7. The module keeps
its tour stop, so nothing disappears from the reading order.

**D2 — a budget-cut empty list states the number it is hiding**, instead of a bare `(none)`:
`- outgoing: (none admitted in this tour; 3 in the full graph)`. This needs the module's full-graph
degrees on the page, so `ModulePage` gains `fan_in` / `fan_out` — facts worth showing on every page.

**D3 — the composition is counted and named, not implied.** `OnboardingArtifact` gains
`isolated: tuple[str, ...]` (the suppressed paths, sorted). Everything else derives from it (R6.7):
`overview.md` gains `- modules with no page (isolated, no summary): M`; `manifest.json` gains
`isolated: [...]`; the viewer's summary gains the same count; the tool payload gains
`isolated_modules` at `standard` (alongside `cache`, `minimal` omits it).

**D4 — `manifest.stops[].page` becomes `null` for a suppressed module.** Today it is emitted
unconditionally, so suppression alone would leave a manifest full of dead links. The viewer already
handles the absence (`"No page for this stop."`, `viewer.py:159`), so this is the manifest's honesty,
not the viewer's rescue.

### Rejected alternatives

| Candidate | Why not |
|---|---|
| **Collapse into one `_isolated.md` per layer** | A second page *kind* to own, delete and link, plus a real path-collision risk (a repo may hold `modules/_isolated`), for no reader gain over a counted list in the overview. |
| **Keep the page, label it "candidate orphan"** | Over-claims. A framework-loaded file has no resolved edge and is still live (031; PLAN §776). The page may state the *degree*, never the conclusion. |
| **Suppress on "no admitted neighbours"**, ignoring full-graph degree | Hides a real dependency at the budget edge — the `routes/web.aa` case above. |
| **A separate `composition.json` sidecar** | Another artifact to own and delete (050). The overview is where a reader already looks. |
| **Report composition only, suppress nothing** | Fails AC2: the tree still ships pages whose only content is a path, a role, a layer and three `(none)`s. |

### Approved change list

| # | File | Change |
|---|---|---|
| 1 | `code_atlas/onboarding/artifact.py` | `ModulePage` += `fan_in`/`fan_out`; `OnboardingArtifact` += `isolated`; `build_artifact` suppresses provably-contentless pages and records them; `render_overview` += count line; `render_module` states a budget-cut empty list; `manifest_dict` `stops[].page` nullable += `isolated`; `as_dict` carries both |
| 2 | `code_atlas/onboarding/viewer.py` | one summary line for the isolated count |
| 3 | `code_atlas/tools/generate_onboarding.py` | `isolated_modules` on `standard`; docstring |
| 4 | `tests/test_generate_onboarding.py` | proving test + manifest/composition tests; **update** the budget-1 assertion (`- module pages: 1` → 0 pages + 1 isolated) — a deliberate behaviour change, recorded |
| 5 | `tests/test_onboarding_viewer.py` | viewer shows the count and no dead link |
| 6 | `README.md`, `docs/PLAN.md`, `docs/BACKLOG.md`, ticket frontmatter | docs match; status + token ledger |

No SQL, no store import in `onboarding/` (R1.4), no schema, no contract, no new module.

### Assumptions check
- **A1** — full-graph degrees are already in `build_artifact` via `compute_metrics` (`by_key`), so D1/D2
  need no new query. Verified: `by_key` is built there today.
- **A2** — suppressing a page cannot orphan the delete rule: the manifest records what was *written*,
  so a page suppressed this run but recorded last run is still deleted (050/088). Covered by AC3.
- **A3** — `_StubSummarizer` gives every module a docline, so the four existing structural tests keep
  all their pages; only the default-summarizer budget-1 test changes count.

### Named proving test
`tests/test_generate_onboarding.py::test_generate_onboarding_suppresses_a_contentless_page_and_counts_it`
— a sparse fixture (isolated modules + one connected pair). Asserts no page exists for an isolated
module, the overview counts it, the manifest names it with `page: null`, and the connected pair keeps
its pages. Run **red before the fix** (R6.5).

### Verification plan
1. `pytest` over the onboarding + viewer suites.
2. Observed-red for the proving test.
3. Pins before/after: laravel 26 → 6 pages (20 isolated), symfony 51 → 44 (7), brick 32 → 32 (0).
4. Anchor monorepo: no regression (expect 500 pages, 0 isolated).
5. Full Docker gate; determinism re-run for byte stability.

## Phase 3 — execute

Branch `fix/107-a-page-with-no-neighbours-and-no-summary-is-filler`. Diff is **7 files**, a **subset**
of the approved change list — one approved item proved unnecessary (below).

### What landed
- `code_atlas/onboarding/artifact.py` — `ModulePage` += `fan_in`/`fan_out`; `OnboardingArtifact` +=
  `isolated`; `build_artifact` skips a page when full-graph degree is 0 **and** there is no docline,
  recording the path; `render_overview` += the count line; `_absent()` renders a budget-cut empty list
  as `(none admitted in this tour; N in the full graph)`; `manifest_dict` emits `stops[].page: null`
  for a suppressed module and adds `isolated`; `as_dict` carries both.
- `code_atlas/onboarding/viewer.py` — `isolated` in the embedded payload + two summary lines
  (`pages`, `no page (isolated, no summary)`).
- `code_atlas/tools/generate_onboarding.py` — `isolated_modules` on `standard`; docstring.
- `tests/test_generate_onboarding.py` — `_sparse_repo` + 4 tests. `tests/test_onboarding_viewer.py` — 1 test.
- `README.md`, `docs/PLAN.md` — the rule as documented matches the code.

### One approved change proved unnecessary (scope under-run, recorded)
Gate 2 flagged that `test_generate_onboarding_overview_discloses_a_truncated_map` would need its
`- module pages: 1` assertion updated. **It did not.** D1 tests the **full-graph** degree, and
`routes/web.aa` has `fan_out = 1`, so it is never suppressed — the budget merely hid its neighbour, and
D2 makes that page say `(none admitted in this tour; 1 in the full graph)`. The test passes unchanged.
The flagged behaviour change was an artefact of the coarser rule considered at Gate 1, and the final
rule preserved it: **no existing assertion was rewritten to accommodate this change.**

### AC2 (amended) + AC5 — before vs after, all four repos

| Repo | Stops | Pages before → after | `isolated` | **Contentless pages** before → after |
|---|---|---|---|---|
| `laravel/laravel` | 26 (unchanged) | 26 → **6** | 20 | **20 → 0** |
| `symfony/demo` | 51 (unchanged) | 51 → **44** | 7 | **7 → 0** |
| `brick/math` | 32 (unchanged) | 32 → **32** | 0 | 0 → 0 |
| anchor monorepo | 500 (unchanged) | 500 → **500** | 0 | 0 → 0 (no regression) |

**Stop counts are identical everywhere** — nothing left the reading order; only the empty page is
gone. **AC5** holds exactly: every page dropped was one of the counted contentless ones
(laravel 26−20 = 6, symfony 51−7 = 44), and no repo lost a page carrying content.

The anchor repo's committed tree was regenerated on the new code: `module pages: 500`,
`modules with no page (isolated, no summary): 0`, `isolated_modules: 0` — the honest zero, and proof
the composition line reads correctly when there is nothing to report.

### AC3 / AC4
- **AC3** — `test_generate_onboarding_deletes_a_page_that_became_contentless`: a module that had an
  edge (page written, recorded in the manifest) loses it, and the next run **deletes** the page it
  wrote. The manifest stays the delete record; `recorded_pages` is untouched (050/088).
- **AC4** — `test_the_viewer_names_the_modules_it_has_no_page_for`: the embedded payload carries
  `isolated`, `pages` holds only the two real pages, `stops` still holds all five modules, and the
  page keeps its existing `"No page for this stop."` branch — no dead link. All 089 tests green.

### Observed red (R6.5)
3 of the 4 authored `generate_onboarding` tests failed before the fix — suppression, the budget-cut
wording, and the delete-on-becoming-contentless case. The 4th (byte-stability over the new shape)
**passed pre-fix** and is recorded as a no-regression guard, not a defect witness.

## Phase 4 — review (waived by run argument)
`REVIEW: skipped (operator-waived)` · `CHALLENGER: OFF (--no-challenger)`. Main-loop verification:

1. **Delta-green, Docker**: **1466 passed, 0 failed** in 100.03 s. `main` **1461** → branch **1466**
   = **+5 authored tests, none removed, none rewritten**.
2. `ruff check` clean; `mypy` clean over **51 source files** (no new module).
3. **Scope sweep:** 7 files, all in the Gate-2 list; item 4's test *update* was not needed, so the
   diff is a strict subset. No SQL added to `onboarding/` (R1.4), no schema, no contract.
4. **Payload shape change, named:** `isolated_modules` is new on `standard` — the change 106
   deliberately deferred to this ticket. `minimal` is unchanged (`cache` convention).
5. **R2.2/R1.1:** the suppression test reads degrees + summary presence only — no directory, suffix,
   framework or language token.
6. **R4.2:** `test_generate_onboarding_composition_is_byte_stable` plus the pre-existing byte-stability
   tests; `isolated` is sorted at construction.

### Cost ledger
**0 dispatches — no subagent was dispatched this run.** Review waived, challenger off, refine
self-resolved, all reading and measurement in the main loop (disclosed). N dispatched = **0 rows**.
Main-loop spend: **unmeasured (host does not surface usage)**.

## Phase 5 — finalise
- Commits: `7bb2833` (fix + tests + docs), `d431918` (working doc), plus this bookkeeping commit.
- **PR [#133](https://github.com/cuongdinhngo/code-atlas/pull/133)** from the template, every section
  filled, self-check complete. It states the stale-evidence correction and the ratified AC2 amendment.
- Outward actions taken: **push branch**, **open PR** (standing durable approval, `AGENTS.md`).
  **Not taken:** merge, force-push, branch delete, release.
- **Revert path:** unmerged → close #133 + delete the branch. Merged → revert the squash commit;
  `isolated_modules` / `manifest.isolated` / `stops[].page: null` are additive, so a revert restores
  the old tree on the next regeneration with no migration.
