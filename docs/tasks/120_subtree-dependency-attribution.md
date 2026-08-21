---
id: 120
slug: subtree-dependency-attribution
title: '"Can this subtree be deleted?" — subtree dependency with duplicate-declaration attribution — evidence-gated'
phase: 1.5b
milestone: Coverage
status: todo
depends_on: [017, 043, 078, 115]
---

> **Status: proposed with its gate attached, not scheduled.** The need is measured and sharp, but it is
> **n = 1** — the same discipline [098](098_correspondence-relation-seam.md) is held to. The gate is in
> "Evidence gate" below. What is *not* in doubt is the defect this ticket documents: the naive way to answer
> the question is wrong by 5.7×, and today nothing but the naive way exists.

## Why this exists (measured, anchor monorepo, 2026-08-21)

The anchor's standing plan is `git rm -r legacy/`. The question that gates it — *what still depends on this
subtree?* — was asked in a live session, and answering it took hand-written SQL over `graph.db`, because no
tool aggregates dependencies at subtree grain. `impact`, `include_graph`, `find_callers` and `find_orphans`
all answer **per subject**; `reachable_from` answers from **declared roots**. None answers *tree → tree*.

**The first hand-written answer was wrong, and wrong in the direction that matters.** Attributing each edge
target to the first file declaring that qname produced:

| | naive attribution | correct attribution |
|---|---|---|
| `src → legacy` (RESOLVED) | 23,086 | **4,013** |
| `legacy → src` (RESOLVED) | 1 | not separable from the above |

The naive number is inflated **5.7×** and reads as "legacy does not depend on src at all", which inverts the
real relationship: legacy reaches src through `config/legacy_aliases.php`, which holds **1,819 DYNAMIC
REFERENCES** into `Src\…` — an alias bridge that carries no static edge at all.

The cause is duplicate declaration, at scale this repo makes ordinary: **22,282 symbols are declared in more
than one file** and **6,426 in more than one tree** (the same 62 % mirror overlap 115 already reports between
`legacy/alpha` and `legacy/beta`). With correct attribution the honest answer is two numbers, never one:

- **4,013** resolved edges from **739 `src/` files** onto symbols declared **only** in legacy — collapsing the
  alpha/beta mirrors, **284 distinct legacy paths**. This is a deletion blocker list.
- **16,857** resolved edges from `src/` whose target is declared in **both** trees — **unattributable from the
  graph alone**. Not a smaller blocker list and not a safe one: an unknown.

Concentration is the useful shape: the blockers are infrastructure, not features —
`web/system/Reference.php` (800 edges), `include/Builder.php` (528), `include/pdf` (340),
`Form` (244), `Config` (185), `Database` (156).

## Scope (if the gate opens)

One read-only report, deterministic, SQL confined to `store.py` (R1.4), node-budgeted (R4.3):

- Given a subtree, the edges crossing **into** it from outside and **out** of it, split by
  `confidence_tier` and by **target-declaration status**: declared only inside the subtree, or also declared
  elsewhere.
- The dependent-file list on the outside, and the depended-on path list inside, each with an edge count so the
  list can be prioritised rather than merely read.
- **The unattributable count is never omitted.** Reporting an attributable number without its unattributable
  companion is precisely the error the naive query made; the shape of the answer must make that error
  unavailable.
- No new relation and no correspondence claim — this ticket says "both trees declare this name", never "these
  two files are versions of each other". That is 098's question and stays there.

## Evidence gate

Ships only when **both** hold, and the numbers are written down either way:

1. A **second** repository — a public pin or a second adopter — shows the same question with the same shape:
   a subtree scheduled for removal, and duplicate declarations that make naive attribution wrong. 115 measured
   **zero** mirrored subtrees across three public pins, so this is not assumed.
2. The question cannot be answered acceptably by composing what already ships. If `impact` plus
   `search_symbol` plus one documented recipe gets there, the recipe ships instead of a tool (R1.2).

Until then this ticket is the record of the measurement, and the anchor's answer stays a one-off script whose
numbers are quoted above.

## Acceptance criteria (when built)

1. **AC1.** Reproduces this session's anchor numbers exactly: 4,013 attributable · 16,857 unattributable ·
   739 dependent `src/` files · 284 mirror-collapsed legacy paths.
2. **AC2.** Output makes the unattributable share structurally unavoidable — a caller cannot read a blocker
   count without reading the unknown count beside it.
3. **AC3.** Tier is never flattened: HEURISTIC edges are reported apart from RESOLVED, since the anchor's
   1.06 M heuristic edges under `max_results = 10` would otherwise dominate every total.
4. **AC4.** Dynamic bridges are surfaced, not silently missing — a subtree reached only through an alias file
   reports that, so "no static edge" is never rendered as "no dependency".
5. **AC5.** Node-budgeted like `impact`/`reach`, with truncation disclosed (R4.3); no whole-graph load.
6. **AC6.** No language branch and no repo-specific name anywhere in the implementation (R1.1 / R2).
