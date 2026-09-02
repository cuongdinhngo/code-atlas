---
id: 206
slug: onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in
title: "Onboarding ranks the whole index by degree, so on a repo that is 78 % read-only legacy the tour visits `src/` zero times and opens with vendored `angular.js` — the artifact has no way to be told which tree the reader actually works in"
phase: 3
milestone: M11
status: todo
depends_on: [105, 111, 112, 121, 126, 131, 205]
---

## Why this exists (measured on the anchor monorepo, 2026-09-02)

The anchor repo is a migration: two read-only regional legacy trees (`legacy/alpha`, `legacy/beta`) are
being merged into one unified `src/`. Its `CLAUDE.md` says of `legacy/` — **"read only, never
modify"** — and every card a developer is given is work in `src/`.

The generated onboarding tour visits `src/` **zero times**:

```
$ grep -c 'src/' tour.md
0
```

Of the 500 module pages, by top-level tree:

| tree | pages |
|---|---|
| `legacy/` | 383 |
| `public/` | 57 |
| `Zend/` | 47 |
| **`src/`** | **12** |
| `config/` | 1 |

All **12** `src/` pages are `.js`. Not one PHP file under `src/` has a page — so `Database`,
`Model`, `RegionManager` and `FeatureFlags`, the four classes every card in the repo touches, do
not appear in the artifact at all.

### What the tour opens with

Reading order, step 1 — labelled `Views`:

```
legacy/beta/web/pages/modules/admin/CRM360/crmKanbanLead/js/angular.js
legacy/beta/web/pages/modules/admin/CRM360/crmKanbanLead/js/Chart.js
```

Step 8, labelled **`Middleware / Auth`** — *"Request middleware, filters, authentication and
sessions"*:

```
legacy/alpha/web/include/pdf/pdf/filters/FilterASCII85.php
legacy/alpha/web/include/pdf/pdf/filters/FilterLZW.php
legacy/alpha/web/include/adodb/session/adodb-encrypt-mcrypt.php
```

A vendored PDF library's ASCII85 stream filter and adodb's session encryption, presented to a new
developer as this system's authentication layer. Steps 2, 9 and 10 are `Uncategorised` and cover
**371 of the 500** modules — three-quarters of the tour is *"the path matched no responsibility
keyword"*.

> **Measurement provenance.** Every figure above was read off an artifact generated from the anchor's
> **field index before [204](204_bare-name-resolution-has-no-language-predicate.md) landed**, which
> carries 343,131 JavaScript/TypeScript-declared `CALLS` edges resolving to PHP targets — 100 %
> HEURISTIC, 0 RESOLVED — verified directly against `.code-atlas/graph.db` on 2026-09-02. Anything
> derived from **degree** is therefore contaminated, and JS files are the contaminated side: they
> carry the false out-edges that bought them their rank. The structural findings below do not depend
> on any edge and stand as written.

> **What this ticket must re-measure first (Scope 0).** The tree distribution, the twelve all-`.js`
> `src/` pages and the tour's opening are all degree-ranked. Removing 343,131 false out-edges from
> JS files moves them *down* the ranking, so a post-204 tour may look materially different — better
> or worse. **Do not tune a default against the numbers above.** Re-generate against a 204-corrected
> index, record the new distribution here, and only then choose. The argument for this ticket is
> structural and survives either way: no config key expresses a working scope, and R5.8 cuts against
> a population the reader cannot constrain.

### What 204 already moved (measured by a parallel session, 2026-09-02)

A regeneration against a 204-corrected index re-ranked the pages substantially:

| tree | pre-204 | post-204 |
|---|---|---|
| `legacy/` | 383 | 448 |
| `public/` | 57 | 1 |
| `Zend/` | 47 | 5 |
| **`src/`** | **12** | **43** |

So the `zero times` in this ticket's title is a pre-204 figure and the honest current number is that
the tour reaches `src/` at 43 pages of 500. This is a second-hand measurement — recorded here so
Scope 0 has a starting point, not as a substitute for it — and it cuts **both** ways: the ranking
moved *toward* the unified target tree once the false JavaScript out-edges were gone, which weakens
any argument that degree ranking is hopeless, while 448 of 500 pages still landing in the read-only
tree leaves the ticket's case intact. Confirm both columns in Scope 0 before choosing a default.

### Why this is not a ranking bug

Every one of those choices is *correct* for the ranking as specified. `angular.js` genuinely has
enormous out-degree. `error_handler.php` genuinely has `fan_in 3621` — `overview.md` names it the
busiest file in the `include` module and it is. The ranking is doing exactly what
[131](131_tour-ranks-configuration-ahead-of-the-front-controller.md) and
[105](105_dominant-subtree-loses-to-a-config-dir.md) tuned it to do.

The defect is upstream of ranking: **the artifact has no concept of a tree the reader works in.** On
a repo where 78 % of the files are deliberately frozen, degree over the whole index is a measure of
where the code *has been*, and the reader needs to know where it is *going*. No config key expresses
that. `entry_points` declares request-addressability, `stub_roots` declares dependency trees to
stub, and neither is "this is my working surface." Even `.codeatlasignore` cannot express it: the
anchor's ignore file already excludes vendored JS trees, and step 1 still opens with a copy of
`angular.js` that lives **inside a module directory** (`pages/modules/admin/CRM360/crmKanbanLead/js/`)
where no path rule can reasonably reach it.

### Why R5.8 makes this the ranking's problem, not the reader's

**R5.8 — rank inside the statement that truncates.** The tour truncates to 500 modules and 15 steps;
`flows.md` truncates to 10 flows of 287 from 10 of 11,680 seeds. Every one of those cuts is made
against a population the reader has no way to constrain, so the truncation reliably keeps the
largest frozen subtree and discards the small live one. Handing the ranking a scope is what lets
R5.8 hold on a monorepo.

## Scope

0. **Re-measure on a 204-corrected index before anything else.** Regenerate the artifact and record
   the tree distribution, the tour's opening and the `src/` page count. Every number in *Why this
   exists* is pre-204 and degree-ranked. This is the calibration step, not a formality: a default
   chosen against a contaminated ranking is a default chosen against noise.
1. **A resolved setting naming the reader's working roots** — one more key in the `Config` list
   beside `entry_points` and `stub_roots`, with the same `CA_*` environment form and the same
   "declared, matched as written" caveat the reachability split already prints.
2. **Every truncated onboarding population respects it**: tour modules, module pages, flow seeds,
   and the busiest-file pick in the business-module table. One decision, one implementation across
   every consumer (**R1.8**) — not four call sites each filtering their own way.
3. **The artifact states its scope in the artifact.** `overview.md` says which roots produced the
   tour and how many files that is of the index; a reader must never have to infer that a section
   is partial. Unset means today's behaviour, stated as "whole index".
4. **Out-of-scope code stays visible as context, never as a destination.** A scoped tour still shows
   that `src/Application/Alpha/Movement` calls into `legacy/`; it just does not spend a stop on the
   legacy file. The aggregates in `overview.md` continue to describe the whole index.
5. **The "what will I touch daily" ranking.** Within scope, rank the tour by what a person actually
   opens — a symbol with a docline and inbound edges from several distinct modules beats a
   1,700-fan-in type-definition file. This is the criterion [131](131_tour-ranks-configuration-ahead-of-the-front-controller.md)
   reached for and could not apply while the population was the whole index.

### Explicitly not in scope

- **Indexing less.** Scope is a *presentation* constraint. The graph keeps every file; cross-scope
  edges are exactly what makes a migration repo's artifact worth reading.
- **Inferring the roots.** No heuristic that guesses "your real code is `src/`". Declared or absent
  (**R2.2** — never encode a repo's directory names).
- **How many pages.** [205](205_a-module-page-per-node-budget-slot.md) owns the count. This ticket
  owns *which*.
- **The vendored-code question.** The `Vendored dependencies: 0` line is
  [208](208_an-undeclared-reachability-bucket-reports-zero-as-a-measurement.md). Scoping to `src/`
  happens to hide vendored files on this repo; that is a side effect, not the fix.

## Constraints

- **R2.2** — no repo's directory names in the core. `src`, `app`, `lib` appear in tests and docs,
  never in a default.
- **R1.8** — the scope predicate has one implementation. A guard greps for a second one.
- **R5.6** — never attest past what the payload can distinguish: a scoped section says it is scoped.
- **R4.2** — with the setting unset, output is byte-identical to today's.
- **R3.5** — if the dataset carries the scope, `DATASET_VERSION` bumps and the viewer moves with it;
  [145](145_artifact-json-is-a-cache-that-a-second-renderer-turns-into-a-contract.md) is the warning.
- The 121 harness is the check that this helped: a scoped artifact that answers **fewer** onboarding
  questions has failed, whatever it looks like.

## Acceptance criteria

1. A declared working scope changes which modules the tour, the pages and the flow seeds cover, and
   is settable from both the project file and the environment.
2. On the anchor repo scoped to `src/` and `public/`, the tour visits `src/` PHP files, and no step
   labelled `Middleware / Auth` is populated by a vendored PDF or database library.
3. Every scoped section states its scope and the count it was drawn from; `overview.md`'s
   whole-index aggregates are unchanged and still say so.
4. With no scope declared, the artifact is byte-identical to the pre-change run.
5. A cross-scope edge is still reachable from a scoped page's neighbour list — proven by a fixture
   with two trees and an edge between them.
6. The 121 harness gains a scoped-repo question and the gate stays green at the existing floors; no
   floor is lowered to accommodate it.
7. `TOOLS.md`, `CONVENTION.md` and the config documentation carry the new key, and per **R7.6** the
   text they supersede is deleted rather than appended to.

## References

[105](105_dominant-subtree-loses-to-a-config-dir.md) and
[131](131_tour-ranks-configuration-ahead-of-the-front-controller.md) (two previous attempts to fix
the tour's opening by tuning the ranking rather than the population),
[111](111_tour-is-narrative-steps.md) (the 15 steps being mis-spent),
[112](112_onboarding-dataset-contract.md) (where a scope field would live),
[121](121_onboarding-question-class-never-measured.md) (the harness that decides whether this
helped), [126](126_search-palette-clusters-into-one-subtree.md) (the same monorepo failure mode in
search), [205](205_a-module-page-per-node-budget-slot.md) (how many pages, as opposed to which),
[208](208_an-undeclared-reachability-bucket-reports-zero-as-a-measurement.md) (the vendored signal).
