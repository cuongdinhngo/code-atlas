---
id: 126
slug: search-palette-clusters-into-one-subtree
title: Onboarding — the map's search palette reproduces the clustering defect 067 fixed, beside the panel that exists to prevent it (M11)
phase: 3
milestone: M11
status: done
depends_on: [067, 115, 116]
---

## Why this exists (reviewed dataset, anchor monorepo, 2026-08-23)

The Ctrl+K palette in the generated `index.html` orders matches in store order and truncates at 40.
On the reviewed dataset a query for a term present in both mirror subtrees matched **1,178 paths**,
displayed **40**, and **40 of 40 were `legacy/alpha/`** — nothing from `legacy/beta/`, nothing from `src/`.

That is [067](067_first-page-not-representative.md)'s exact finding, one layer out:
`find_callers` page 1 clustered into whichever subtree sorted first, and 067 answered it with
`result_subtrees`. The palette has the same defect and **no mitigation at all**.

**It is worse here than a ranking nit, because of where it sits.** The mirror panel two sections up
exists to prevent "fixed ALPHA, forgot BETA" — its own lede says so. The search tool beside it answers a
query for a mirrored file by showing one side only, teaching the reader that the file exists on one
side. **The artifact contradicts its own section**, and the section is the one about not trusting one
side of a mirror.

The cause is three lines (`code_atlas/onboarding/viewer.py`, `search()`):

```js
var hits = exact.concat(part);
hits.slice(0, SHOWN_MAX).forEach(...)
```

`PATHS` is embedded in index order, `exact`/`part` are appended in that order, and the slice takes the
first 40. No score is computed, so the displayed page is decided by which subtree the indexer walked
first.

## Scope

Two parts, both inside `search()` / `draw()` — no new section, no new dependency.

- **Rank before truncating.** Score every match: exact › basename match › path-substring; shorter path
  before longer; lexicographic last so the order is total and byte-stable (R4.2). Then guarantee **at
  least one survivor per top-level subtree present in the full match set**, evicting the lowest-ranked
  member of the most over-represented subtree.
- **Disclose the span.** When the displayed page is truncated *and* the full match set spans more than
  one top-level subtree, the hint names them — the artifact-layer equivalent of 067's
  `result_subtrees`. The subtree set is **derived from the matches**; no `"alpha"`/`"beta"`/`"src"` literal
  reaches the generator ([115](115_mirror-subtree-detection.md) already shipped region names in output
  keys once — R2.2, and the viewer suite's own sweep greps for exactly that).

## Acceptance criteria

1. **AC1 (red first).** A fixture whose term matches in two subtrees, with more matches than the page
   size and all of subtree A sorting first, shows a subtree-B path on page 1. Recorded failing against
   the pre-change generator (R6.5).
2. **AC2.** The disclosure string is present when and only when the page is truncated across more than
   one top-level subtree — absent on an untruncated page, absent on a truncated single-subtree page.
3. **AC3.** Ranking is total and deterministic: the same dataset renders byte-identical `index.html`,
   and a reversed input order produces the same displayed page (R4.2).
4. **AC4.** No region, repo or framework name enters the generator; the subtree labels come from the
   matched paths (R2.2).
5. **AC5.** No new runtime dependency, no new section in the page, and the palette stays a single pass
   over the embedded `PATHS` (the cap is what it always was).

## Not in scope

The embedded path index cap (`INDEX_PARTIAL`) and its wording are 116's and stay as they are: this
ticket changes *which* matches survive the page, never how many paths are embedded.

---
<!-- working doc (work_doc_mode: embed) — everything above this line is the ticket -->

## Session status

- **Current phase:** complete (shipped) — PR [#151](https://github.com/cuongdinhngo/code-atlas/pull/151)
- **work_doc_mode:** embed (plain local-file ticket)
- **SCOPE:** M · **TIER:** full
- **CHALLENGER:** OFF (`--no-challenger`, run args) · **Review:** SKIPPED (run args)
- **Branch:** `fix/126-search-palette-clusters-into-one-subtree`
- **BASELINE:** 1739 passed (main after the README rewrite, 2026-08-23)

## Phase 1 — Analysis: requirements matrix

| # | Kind | Requirement | Source | Proven by |
|---|---|---|---|---|
| G1 | G | Page 1 of a palette search represents the match set instead of the indexer's walk order | ticket §Why | AC1 |
| R1 | R | Score every match before truncating: exact › basename › path-substring, shorter path first, lexicographic last | ticket §Scope | AC1, AC3 |
| R2 | R | Guarantee ≥1 survivor per top-level subtree present in the full match set | ticket §Scope | AC1 |
| R3 | R | Truncated page spanning >1 top-level subtree names them (067's `result_subtrees`, artifact layer) | ticket §Scope | AC2 |
| C1 | C | No new runtime dependency; no new page section; cap unchanged | ticket §AC5 | AC5 |
| C2 | C | Subtree labels derived from matched paths — no region/repo/framework literal (R2.2) | ticket §Scope | AC4 |
| C3 | C | Byte-identical `index.html` for an identical dataset; total ordering (R4.2) | ticket §AC3 | AC3 |
| C4 | C | Deterministic core, no LLM/network (R4/R4.1) | rulebook | full suite |
| AC1 | AC | Two-subtree fixture, A sorts first, >page-size matches → a B path on page 1; red first (R6.5) | ticket | new test |
| AC2 | AC | Disclosure present iff truncated across >1 subtree | ticket | new test |
| AC3 | AC | Same dataset → byte-identical page; reversed input → same displayed page | ticket | new test + existing determinism test |
| AC4 | AC | No region name in the generator | ticket | existing R2.2 sweep (`test_onboarding_viewer.py`) |
| AC5 | AC | Single pass over `PATHS`, no new dependency, no new section | ticket | diff review |

**Clarifications needed: 0.** AC validation: 5 ACs, each with a named prover, none untestable.

## Phase 2 — Design

**Approach.** Three additions inside the palette's own JS, nothing outside it:

1. `subtreeOf(path)` — the first path segment, from the data.
2. `rank(path, q)` → `0` exact · `1` basename equals · `2` basename contains · `3` path contains;
   sort by `(rank, length, path)`, a **total** order, so the displayed page cannot depend on input
   order (C3).
3. `represent(ranked, cap)` — take the first `cap`, then for each subtree present in the full match
   set but absent from the page (visited in ranked order of its best member), evict the lowest-ranked
   page member of the **most over-represented** subtree and insert that subtree's best member.
   **Only evicts while the maximum per-subtree count is ≥ 2**, so representation never churns a
   subtree back out; the page is re-sorted into ranked order afterwards.
4. `draw()` appends the disclosure when `cut > 0 && trees.length > 1`, naming the subtrees
   (lexicographic, first six then `+N more` so the sentence itself cannot run away).

**Rejected alternatives.**
- *Round-robin the subtrees* — makes rank subordinate to path shape; a basename hit could lose page 1
  to a substring hit in another tree. Representation is a floor, not a quota.
- *Cap per subtree* — needs a policy number nothing in the dataset justifies, and shrinks the page
  when a query genuinely lives in one tree.
- *Fix it in `dataset.py` by pre-sorting `file_paths`* — the palette would still slice one tree first
  for any query whose matches cluster; and it would move a rendering concern into the contract (112).

**Change list (approved scope).**
- `code_atlas/onboarding/viewer.py` — `search()` / `draw()` only.
- `tests/viewer_dom_stub.js` — report the displayed item texts and the rendered hint (harness only).
- `tests/test_onboarding_viewer.py` — three tests (AC1, AC2, AC3).
- Docs: BACKLOG row + this frontmatter, token ledger.

**Proving test.** `test_palette_page_one_represents_every_subtree` — the AC1 fixture: 60 `alpha/`, 60
`beta/` and 1 `src/` path all matching `member`, `alpha/` first in dataset order. Red before the
change (all 40 displayed rows are `alpha/`), green after.

**Rule compliance.** R1.1 n/a (no core language branch) · R2.2 subtree names derived (AC4) · R4.2
total ordering (AC3) · R1.2/R7.4 no abstraction added, three functions in the existing script ·
R6.5 red run recorded before the guard ships.

## Phase 3 — Execute summary

- `code_atlas/onboarding/viewer.py` — `subtreeOf` / `rankOf` / `ranked` / `represent` added to the
  palette script; `search()` ranks before truncating and returns `trees` (the subtrees the **full**
  match set spans); `draw()` names them when the page is truncated across more than one.
- `tests/viewer_dom_stub.js` — the harness now drives the page's own `draw()` and reports the
  displayed item texts plus the rendered hint. Report-only, as the file's header requires.
- `tests/test_onboarding_viewer.py` — four tests: page-1 representation (AC1), basename-over-path
  ranking (AC1), disclosure present-iff (AC2), input-order independence (AC3).

**RED RUN (R6.5), recorded before the fix.** `pytest -q tests/test_onboarding_viewer.py -k palette`
→ **4 failed**. The AC1 failure reproduced the reviewed anchor shape on a fixture: **121 paths
matched, 40 displayed, 40 of 40 from `alpha/`** — no `beta/`, no `src/`.

**GREEN after.** Same command → 4 passed; `tests/test_onboarding_viewer.py` 25 passed.
**Delta-green:** 1745 → **1749 passed** (+4). `scripts/gate.sh` → **GATE GREEN, 12/12, 0 skipped**.

Rendered hint on the AC1 fixture:

```
Showing 40 results, 81 further path matches not listed. The matches span 3 top-level subtrees:
alpha, beta, src.
```

**Deviation from the ticket: none.** The diff is a subset of the approved change list.

## Decision log

- **Representation is a floor, not a quota.** Rank stays primary; each subtree in the full match set
  keeps exactly one guaranteed row, paid for by the most over-represented subtree, and a subtree's
  last row is never evicted. Round-robin was rejected at design: it would let a substring hit in one
  tree outrank a basename hit in another.
- **Ties break on length then name**, per the review's own wording, which means the shorter of two
  mirrored trees takes most of the page — the floor plus the disclosure is what makes that honest,
  and no quota was invented to even it out.
- **`NAMED_TREES = 6`.** The disclosure sentence is itself bounded; beyond six it says `and N more`
  rather than growing without limit.

## Cost ledger

| Phase | Dispatch | Tokens | Notes |
|---|---|---|---|
| refine / analysis / design / execute | none | 0 | no subagent dispatched this run |
| review | — | — | SKIPPED (run args) |
| **Total** | **0 dispatch** | **0** | main-loop spend unmeasured (host surfaces no usage block) |
