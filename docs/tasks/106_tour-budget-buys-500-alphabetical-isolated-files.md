---
id: 106
slug: tour-budget-buys-500-alphabetical-isolated-files
title: Onboarding — the tour budget buys the 500 alphabetically-first isolated files, so the walk never expands (M11)
phase: 3
milestone: M11
status: done
depends_on: [087, 088]
---

## Why this exists (measured on a real repo, not guessed)

`generate_onboarding` was run against the maintainer's private PHP monorepo (18,926 indexed files,
schema 4 / contract 5, index built 2026-08-14) with default knobs. It wrote 504 artifacts and
`truncated: true`. The overview is sound — 10 layers, 62 cross-layer edges, real signal about which
trees depend on which. **Everything downstream of the node budget is not:**

| Observation (counted from the emitted `manifest.json`) | Result |
|---|---|
| Module pages emitted | 500 |
| Pages whose `outgoing` **and** `incoming` are both empty | **500 / 500** |
| Pages with an empty `docline` | **500 / 500** |
| Tour stops whose rationale is `entry point (zero inbound)` | **500 / 500** |
| Layers represented among the 500 pages | **4 of 10** (`alpha` 442, `Zend` 56, `(root)` 1, `config` 1) |
| Pages from `src` (4,698 modules), `beta` (5,378), `tests` (2,040), `lib` (546), `public`, `scripts` | **0** |

A reader gets 500 pages that each say: file name, role `entry-point`, layer, `Summary: (none)`,
`outgoing: (none)`, `incoming: (none)`. That is strictly less than `ls` gives, and the reading order
is 500 consecutive lines carrying one identical rationale string — zero entropy.

## Mechanism (not a summarizer problem, not an LLM problem)

`store.py::_tour_entry_seeds` (`store.py:1809`) selects the seeds as
`… WHERE file_path NOT IN (<has inbound edge>) GROUP BY file_path ORDER BY file_path LIMIT ?`
with the limit set to the whole node budget. This repo holds **8,477 files with zero inbound
cross-file edge** against `DEFAULT_IMPACT_MAX_NODES = 500` (`config.py:50`), so:

1. round 1 admits 500 seeds and the budget is **already exhausted**;
2. `_tour_expand` (`store.py:1850`) therefore adds nothing — the walk **never traverses one edge**;
3. every admitted node is a seed with zero inbound by construction, and none of their targets are
   admitted, so every page's neighbour lists are empty and every stop's rationale is the seed label;
4. the 500 that survive are chosen by **`ORDER BY file_path`** — pure ASCII order. `Zend/…` sorts
   first, then `bootstrap.php`, `config/`, `legacy/alpha/…`, and the budget dies inside `legacy/alpha`.
   `lib/`, `beta/`, `public/`, `scripts/`, `src/`, `tests/` never get a turn.

So the cut is alphabetical, not architectural, and it systematically selects the nodes carrying the
**least** relational information in the graph. Raising `CA_IMPACT_MAX_NODES` does not fix the shape —
with 8,477 seeds the budget still goes to seeds before any expansion, just more of them.

The pinned public repos hid this: `symfony/demo` has 51 modules and 30 entry points, so 500 covers
the whole graph and the walk expands normally. **The defect needs entry points ≫ budget to fire.**

## What this ticket must decide (do NOT pre-empt it here)

Candidate signals, to be judged on the three pinned repos **plus** a fixture whose entry-point count
exceeds the budget (the shape that exposed this):

- **Rank the seeds** by graph mass (fan-out, reachable-set size, symbol count) instead of
  `file_path`, so the budget buys the roots that lead somewhere. 105 already established graph mass
  over count as the right tie-break for layer election.
- **Reserve budget for expansion** — spend only a fraction on seeds so `_tour_expand` always runs,
  making the reading order an actual dependency order rather than a seed dump.
- **Spread the budget across layers** so a reading order cannot represent 4 of 10 layers.
- **Report what the budget dropped** — `truncated: true` is honest but says nothing about *which*
  8,000 files, or that the omission is systematic. A counted drop summary would let a reader see the
  cut instead of inheriting it.

**Explicitly rejected in advance (R2.2):** naming `Zend`, `legacy`, `vendor`, `tests` or any other
directory in the core, and any repo-specific ordering. The signal must come from graph shape. R4.2
determinism holds — whatever replaces `ORDER BY file_path` must be a total, reproducible order.

## Acceptance criteria
- **AC1** — the chosen signal is recorded in the design phase with the alternatives and why, and
  holds R1.1 (no language branch), R2.2 (no directory stop-list) and R4.2 (determinism: identical
  index → byte-identical `tour.md`).
- **AC2** — on a graph where entry points exceed the budget, the emitted tour **expands**: a counted
  majority of stops carry a rationale other than the seed label, and pages carry non-empty neighbour
  lists. The count is recorded, not asserted.
- **AC3** — the three pinned public repos (`laravel/laravel`, `symfony/demo`, `brick/math`) do not
  regress: their tours stay architecturally sensible, with the assignment recorded per repo.
- **AC4** — a fixture pins the entry-points-≫-budget shape so this cannot silently return, per
  `LESSONS.md` handle `fixture-shape-begs-the-question`.
- **AC5** — re-run against the same private monorepo and record the new layer coverage among pages
  (currently 4 of 10) and the new stop-rationale distribution.

## Out of scope
- Page *content* emptiness where the node genuinely has no neighbours and no docblock — that is 107.
- The summarizer seam (085) and the LLM summarizer (090): `Summary: (none)` on 500 view templates is
  a real limit of `StructuralSummarizer`, but paying an LLM to describe the wrong 500 files fixes
  nothing until the selection is fixed.
- Layer election (104/105) — the overview is the part that already works.

## References
- Evidence: this ticket's table, counted from the emitted `manifest.json` of the private-monorepo run.
- `code_atlas/store.py` (`tour_subgraph` `:563`, `_tour_entry_seeds` `:1809`, `_tour_expand` `:1850`).
- `code_atlas/config.py:50` (`DEFAULT_IMPACT_MAX_NODES`).
- 087 `docs/tasks/087_guided-tour-tool.md`; 088; 105 (graph mass over count). PLAN §14, §15 (M11).

<!-- ===================== mango working doc (embed) — raw ticket above ===================== -->

## Session status
- **Runner:** `/mango:solve 106 with skipped review & challenger` — standing maintainer approval to
  suggest + do the best option, pass all gates, then commit + push + open PR.
- **`CHALLENGER: OFF` (`--no-challenger`).** **`REVIEW: skipped`** (operator-waived) — no reviewer
  dispatch; verification runs in the main loop and is recorded empirically below.
- **work_doc_mode:** embed (plain local-file ticket, untracked at start). **Branch:**
  `fix/106-tour-budget-buys-500-alphabetical-isolated-files`.
- `STRUCTURE: native` · `TRACK: backend` · `SCOPE: M` · `TIER: full`.
- **Outward-action authorisation:** push branch + open PR are covered by the maintainer's standing
  durable approval (`AGENTS.md`, *Maintainer workflow*) plus this invocation. Merge / force-push /
  branch-delete remain out — they need a separate confirmation.
- **Phase:** Phase 5 — finalise, **PR [#132](https://github.com/cuongdinhngo/code-atlas/pull/132) open**. **Outcome: all five ACs met** (AC3 and AC5 proven on real
  repos this session, not deferred).

## Phase 0 — refine
`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved | 0 ASSUMED | skip: no`

Premise check: every source 106 references as already existing resolves —
`store.py::tour_subgraph:563`, `::_tour_entry_seeds:1809`, `::_tour_prune_seen:1789`,
`::_tour_expand:1850`, `config.py:50` (`DEFAULT_IMPACT_MAX_NODES = 500`), `docs/PLAN.md` §14/§15,
`docs/LESSONS.md` handle `fixture-shape-begs-the-question`, `scripts/cross_repo_samples.json`,
tasks 087/088/105. No `PREMISE FALSIFIED`.

The four candidates in *What this ticket must decide* are **how-decisions** (technical, evidence-
resolvable), not want-decisions: the ticket already fixes the goal (the budget must buy nodes that
form a reading order) and pre-rejects the R2.2 stop-list. Under the standing approval they are
resolved in Phase 2 with citations, not asked. Single deliverable → ticket path, not epic.

## Phase 1 — analysis

### Requirements matrix

| # | Source | Requirement | Type | Status | Proven by |
|---|---|---|---|---|---|
| G1 | title + *Why this exists* | The node budget must buy nodes that form a **reading order** — the walk must expand — instead of the alphabetically-first zero-inbound files | G | met | `test_guided_tour_expands_when_entry_points_exceed_the_budget` — red `40 == 10` pre-fix, green after |
| R1 | *decide* bullet 1 | Seed selection ranked by a **graph signal**, not `file_path` | R | met | `_tour_ranked` ordered `out_degree DESC, file_path ASC` (`store.py`) |
| R2 | *decide* bullet 2 | Budget **reserved for expansion**, so `_tour_expand` always runs | R | met | `_TOUR_SEED_BUDGET_DIVISOR = 4` cap in `tour_subgraph` |
| R3 | *decide* bullet 3 | Spread the budget across layers | R | **rejected** (Phase 2 §Rejected) | layer assignment is pure `onboarding/` code; doing it in SQL breaks R1.4 |
| R4 | *decide* bullet 4 | Report what the budget dropped | R | **rejected** (Phase 2 §Rejected) | 107 owns the counted-composition payload; `truncated` already carries the honest bit |
| C1 | R1.1 | No language branch in the core | C | met | CI grep-gate green in the Docker run |
| C2 | R2.2 + ticket | No directory / repo / framework stop-list in the ranking | C | met | ranking reads degrees only; CI grep-gate green |
| C3 | R4.2 | Total, reproducible order; identical index → byte-identical tour | C | met | byte-stability test + tie test; pinned JSON identical across runs |
| C4 | R4.3 | Bounded SQL traversal; never load the whole graph | C | met | one grouped scan + `LIMIT ?`; no recursive CTE, no whole-graph load |
| C5 | R7.1 / R1.2 | Smallest useful change; no new abstraction | C | met | diff = +67/−26 in `store.py`, no new module, no new seam |
| C6 | R7.5 | Every comment ≤ 3 lines | C | met | every added comment ≤ 3 lines |
| AC1 | AC1 | Chosen signal recorded with alternatives + why; holds R1.1/R2.2/R4.2 | AC | met | Phase 2 §Decision + §Rejected, and Phase 3 §Deviation |
| AC2 | AC2 | On entry-points-≫-budget: tour **expands** — counted majority of stops carry a non-seed rationale; pages carry non-empty neighbours | AC | met | Phase 3 §AC2 — 10 seeds + 30 reached (75 % non-seed); anchor repo 125 + 375 |
| AC3 | AC3 | Three pinned public repos do not regress; assignment recorded per repo | AC | met | Phase 3 §AC3 — all three pins byte-identical before/after |
| AC4 | AC4 | A fixture pins the entry-points-≫-budget shape | AC | met | `_wide_entry_repo` + recorded red run (R6.5) |
| AC5 | AC5 | Re-run the private monorepo; record new layer coverage + stop-rationale distribution | AC | met | Phase 3 §AC5 — 4 → 6 layers, 500/500 → 0/500 empty pages, 0 → 100,853 edges |

**Counts:** 1 G · 4 R · 6 C · 5 AC = **16 rows, 0 unfilled cells** (every `Proven by` cell
carries the *planned* proof named below; each is re-stated as an observed result in Phase 3).

### AC validation
Every AC is checkable **this session**: AC2/AC4 by an authored fixture; AC3 by re-indexing the three
pins from `scripts/cross_repo_samples.json` (php + composer present on this host); AC5 against the
maintainer's private monorepo index (schema 4, built 2026-08-14) that produced the ticket's evidence.
No AC needs a deferral. `CLARIFICATIONS: 0 asked (standing approval) | 0 outstanding`.

## Phase 2 — design

### Decision

**D1 — the seed signal: module out-degree (COUNT DISTINCT target module), `DESC`, then `file_path ASC`.**
An entry seed has zero inbound *by construction*, so 105's mass (Σ fan_in + fan_out) degenerates to
fan_out for exactly this population; distinct target modules is the module-grain form of "this root
leads somewhere". Cost is one `GROUP BY` with a `LIMIT` — no traversal (R4.3).

**D2 — the intake cap: `seed_cap = max(1, max_nodes // _TOUR_SEED_BUDGET_DIVISOR)`, divisor 4.**
Guarantees `_tour_expand` at least ¾ of the budget, which is what AC2's "counted majority of non-seed
stops" needs. `max(1, …)` keeps a 1-node budget legal (087's existing `[ENTRY]` assertion). A repo
whose entry count is under the cap is untouched — `symfony/demo` has 30 entries against a cap of 125 —
so the three pins cannot regress by construction.

**D3 — the refill loop becomes ranked and batched.** `_tour_lowest_unseen()` (`LIMIT 1`, path order)
→ `_tour_ranked_unseen(limit)` ordered `(fan_in + fan_out) DESC, file_path ASC`, batch size
`min(room, seed_cap)`. The cap is only *safe* because this loop refills: a scripts-only repo where
nothing expands still ends with the same coverage, admitted in mass order instead of alphabetical
order. Two wanted side-effects — refill rounds stop buying alphabetical junk, and the loop's
iterations drop from ~O(room) single-file rounds to ~⌈room / seed_cap⌉ (500-budget worst case ~4
rounds, not ~375). Mass here is 105's Σ fan_in + fan_out, because a refill candidate — unlike an entry
seed — may have inbound.

**Determinism (R4.2/C3):** both orders terminate in `file_path ASC` over a `GROUP BY file_path`, so
each is a **total** order. **R1.1/R2.2 (C1/C2):** the ranking reads degrees only — no path shape, no
directory name, no language. **R1.4:** all selection stays in `store.py`; `onboarding/tour.py` keeps
the pure ordering it already owns and is untouched.

### Rejected alternatives

| Candidate | Why not |
|---|---|
| **Reachable-set size per seed** (the ideal rank) | Needs a recursive CTE per candidate — 8,477 of them on the evidence repo — turning *selection* into an unbounded traversal (R4.3, perf). The walk already does the reaching; paying twice buys ordering only. |
| **Raw outgoing edge count** | A file calling one collaborator 50× would outrank a file touching 5 modules. Distinct targets is the honest breadth. |
| **Symbol count / file size** | Not graph shape. A large isolated file would win the budget — the exact defect. |
| **Seed cap = half the budget** | Leaves a 50/50 split at best, so "a majority of stops are reached-from" would be a coin flip rather than a guarantee. |
| **An absolute seed cap (e.g. 64)** | Does not scale with a raised `CA_IMPACT_MAX_NODES`; a divisor keeps the ratio invariant. |
| **Expand between every seed batch** | Reaches the same end state as D2+D3 (the refill loop already does) at more SQL round-trips and more branching (R7.1). |
| **R3 — layer-spread quota** | Layer assignment lives in pure `onboarding/layers.py`; running quotas in SQL puts layer semantics inside the store (R1.4), and plumbing layers down into the store inverts the dependency (R1.3). Mass-ranking already fixes the defect (R7.1). |
| **R4 — drop-summary payload field** | 107 AC3 owns counted composition; `truncated` already carries the honest bit. Widening two tool payload shapes here duplicates a sibling ticket (R7.1). |

### Approved change list

| # | File | Change |
|---|---|---|
| 1 | `code_atlas/store.py` | `_TOUR_SEED_BUDGET_DIVISOR`; rank `_tour_entry_seeds`; `_tour_lowest_unseen` → `_tour_ranked_unseen(limit)`; `tour_subgraph` seed cap + batched refill; docstrings |
| 2 | `code_atlas/tools/guided_tour.py` | docstring: how the budget is spent |
| 3 | `code_atlas/tools/generate_onboarding.py` | docstring: same bound sentence |
| 4 | `tests/test_guided_tour.py` | `_wide_entry_repo` fixture + proving test + degree-tie totality test + refill-coverage test |
| 5 | `README.md:196`, `docs/PLAN.md:411`, `docs/BACKLOG.md`, ticket frontmatter | docs match the new selection rule; status + token ledger |

**Nothing else.** No new module, no new seam, no payload-shape change, no contract change, no schema
change (C5 / R1.2 / R3-contract).

### Assumptions check
- **A1** — `nodes` holds a row for every indexed file, so both ranked queries see the whole candidate
  set. Already relied on by `_tour_lowest_unseen` today.
- **A2** — out-degree is expressible as one `LEFT JOIN` + `COUNT(DISTINCT tgt.file_path)`, no
  per-row correlated subquery.
- **A3** — the four existing tour tests that pin budget behaviour survive: budget-1 `[ENTRY]`
  (cap → 1, ENTRY is the only zero-inbound file); the unreachable cycle (refill batch admits both
  members in one round instead of one-then-expand, same file set); the cycle repo at budget 2
  (`ROUTES` is the only zero-inbound file, so the cap is not binding); the one-cycle graph
  (no entry seeds → refill ranked, mass tie → `file_path ASC` → `ISO_X`, unchanged).

### Named proving test
`tests/test_guided_tour.py::test_guided_tour_expands_when_entry_points_exceed_the_budget` — a fixture
with more zero-inbound roots than the budget, each root carrying a chain. It asserts the walk
**expands**: seeds ≤ cap, a counted majority of stops carry a non-seed rationale, and the reached
files are the high-out-degree roots' successors. Per R6.5 (`prove-the-guard-fails`) it is run against
the **pre-fix** store and the red is recorded before the fix lands.

### Verification plan
1. `pytest -q tests/test_guided_tour.py tests/test_generate_onboarding.py tests/test_onboarding_*.py`
2. Observed-red: proving test against pre-fix `store.py`.
3. Full Docker gate `scripts/docker-test.sh` (delta-green vs `main`).
4. AC3: re-index the three pins from `scripts/cross_repo_samples.json`, diff each tour before/after.
5. AC5: re-run `generate_onboarding` on the private monorepo; record layer coverage + rationale mix.

## Phase 3 — execute

Branch `fix/106-tour-budget-buys-500-alphabetical-isolated-files`. Diff is **5 files**, a subset of
the approved change list; nothing outside it.

### What landed
- `code_atlas/store.py` — `_TOUR_SEED_BUDGET_DIVISOR = 4`; `_tour_build_out_degree()` (one grouped
  scan into a temp table + unique index); `_tour_entry_seeds(limit)` and `_tour_ranked_unseen(limit)`
  now share `_tour_ranked(where, limit)` ordered `out_degree DESC, file_path ASC`;
  `tour_subgraph` caps seed intake at `max(1, max_nodes // 4)` and refills with
  `min(room, seed_cap)` ranked batches; `_tour_drop_temps` drops the new table. **+67 / −26.**
- `code_atlas/tools/guided_tour.py`, `code_atlas/tools/generate_onboarding.py` — docstrings state how
  the budget is spent (these are the user-facing tool descriptions).
- `tests/test_guided_tour.py` — `_wide_entry_repo` + 3 tests (**+116**).
- `README.md:196`, `docs/PLAN.md:411` — the selection rule as documented now matches the code.

### Deviation from Gate 2 (recorded, not absorbed)
**D1/D3 refined mid-execute: one signal, out-degree, for both seed and refill ranking.** Gate 2
approved out-degree for seeds and 105's mass (Σ fan_in + fan_out) for refills. Implemented that way
first and **measured it**: the two-sided mass table cost **6.125 s** of a **10.096 s**
`tour_subgraph` on the anchor monorepo, and the inbound half fed only the refill ranking. Dropping it
is *simpler* (one signal, one grouped scan), matches D1's own rationale — what the reading order wants
next is a file that **leads** somewhere — and cost **5.969 s** instead of 10.096 s for a
**byte-identical** subgraph (files 500, edges 100,853, entries 125) and byte-identical pinned-repo
tours. Same files, same file, no new helper: inside the approved change list.

Also reverted, not kept: a `ruff format` pass had reformatted **204 unrelated lines** of `store.py`.
CI runs `ruff check`, not `ruff format --check`, so that churn was scope, not compliance — the file was
restored and the change re-applied at **+67 / −26**.

### AC2 — the walk expands (observed red, then green)
Pre-fix, the proving test failed exactly as the ticket describes:
`assert len(seeded) == 10` → **`AssertionError: assert 40 == 10`**, all 40 stops seeds, `iso/thin*`
isolated files filling the budget (R6.5 `prove-the-guard-fails` — the guard was observed failing
before the fix landed). Post-fix, budget 40 over 40 entry points: **10 seeds + 30 reached**, 75 %
non-seed, no `iso/` file admitted.

### AC3 — the three pinned repos, before vs after: **byte-identical**
Re-indexed each pin at its pinned SHA (`laravel_app` 26 files, `symfony_demo` 51, `brick_math` 32),
dumped each tour with the fix and again with `store.py` stashed, and diffed the JSON:

| Pin | Entry points | Stops | Rationale mix | Before vs after |
|---|---|---|---|---|
| `laravel/laravel` | 23 | 26 | entry 23 · reached 3 | identical |
| `symfony/demo` | 30 | 51 | entry 30 · cycle 5 · reached 15 | identical |
| `brick/math` | 9 | 32 | entry 9 · cycle 11 · reached 12 | identical |

As predicted at Gate 2: each pin's entry count (23/30/9) is under the cap (125), so the cap never
binds and no pin can regress. The defect needs entry points ≫ budget.

### AC5 — the anchor monorepo (18,926 indexed files), before vs after

| Measure | Before | After |
|---|---|---|
| Stops carrying the seed label `entry point (zero inbound)` | **500 / 500** | **125 / 500** |
| Stops with a non-seed rationale | 0 | **375** (cycle 332 · reached 43) = 75 % |
| Module pages with **both** neighbour lists empty | **500 / 500** | **0 / 500** |
| Layers represented among the pages | **4** (alpha 442 · Zend 56 · (root) 1 · config 1) | **6** (beta 300 · src 149 · alpha 42 · lib 6 · public 2 · config 1) |
| Pages under the vendored `Zend/` tree | 56 | **0** |
| Subgraph edges the walk traversed | **0** | **100,853** |

`src` (4,698 modules) and `beta` (5,378) — invisible before — now hold 449 of the 500 pages.

**Still `(none)`:** all 500 pages carry an empty summary. That is `StructuralSummarizer` on files with
no class docblock, explicitly **out of scope** here (085 / 090 own the summarizer, 107 owns what to do
with an absent one). 106 claims the neighbours and the selection, not the prose.

### Cost, stated plainly
`tour_subgraph` best-of-3 on the anchor monorepo: **3.554 s → 5.969 s** (+2.4 s). The pre-fix number is
fast because it did nothing — 0 subgraph edges. The added time is one grouped out-degree scan over the
edge table; `generate_onboarding` end-to-end on that repo is ~14 s. No new index on a persisted table,
so **no schema change** and no migration.

## Phase 4 — review (waived by run argument)
`REVIEW: skipped (operator-waived)` · `CHALLENGER: OFF (--no-challenger)`. Verification ran in the
main loop:

1. **Delta-green, Docker** (`scripts/docker-test.sh`, Linux + PHP adapter): **1461 passed, 0 failed**
   in 78.18 s. Collected count `main` **1458** → branch **1461** = **+3 authored tests, none removed**.
2. `ruff check` clean; `mypy` clean over **51 source files** — the count-pin is unchanged because the
   change adds no module under `code_atlas/`.
3. **Scope sweep:** `git diff --stat` = `store.py` (+67/−26), `guided_tour.py`, `generate_onboarding.py`,
   `tests/test_guided_tour.py` (+116), `README.md`, `docs/PLAN.md`, `docs/BACKLOG.md`, ticket file.
   Every path is in the Gate-2 list; no payload key, schema, or contract touched.
4. **Determinism (R4.2):** both ranked orders end in `file_path ASC` over a `GROUP BY file_path`;
   `test_guided_tour_is_byte_stable_across_two_runs` and the tie test pin it, and the pinned-repo
   JSON dumps were byte-identical across runs.
5. **R1.1/R2.2:** ranking reads degrees only — no path shape, no directory name, no language; CI
   grep-gates green inside the Docker run.

### Cost ledger
**0 dispatches — no subagent was dispatched this run.** Review waived, challenger off, refine
self-resolved, and the analysis reading was done in the main loop (disclosed). A run that dispatched
N subagents ends with N rows: **N = 0**. Main-loop spend: **unmeasured (host does not surface usage)**.

## Phase 5 — finalise
- Commits: `8ef64bb` (fix + tests + docs), `670bf9a` (tickets 106/107 + backlog), plus this
  bookkeeping commit. Branch `fix/106-tour-budget-buys-500-alphabetical-isolated-files` pushed.
- **PR [#132](https://github.com/cuongdinhngo/code-atlas/pull/132)** opened from
  `.github/pull_request_template.md`, every section filled, self-check complete.
- Outward actions taken: **push branch**, **open PR** — both covered by the standing durable
  approval in `AGENTS.md` (*Maintainer workflow*) plus this invocation. **Not taken:** merge,
  force-push, branch delete, release — each needs a separate confirmation.
- **Revert path:** unmerged → close #132 + `git push origin --delete
  fix/106-tour-budget-buys-500-alphabetical-isolated-files`. Merged → revert the squash commit; the
  only core change is the tour selection SQL, no schema/contract/payload to undo.
- **Lesson captured** below for `docs/LESSONS.md` promotion at the maintainer's ratification.
