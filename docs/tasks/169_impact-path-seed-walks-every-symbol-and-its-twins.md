---
id: 169
slug: impact-path-seed-walks-every-symbol-and-its-twins
title: 'An `impact` path seed expands to every symbol in the file and reports 29× the qname seed — 161 gave the qname seed a refusal and left the path seed walking twins'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [161, 017, 078, 165]
---

## Why this exists (field retro rounds 10 & 11)

Round 10's §15 ranked this ticket 6 of 6 and it did not ship. Round 11 fired it deliberately (R-18) and
it is the round's largest measured over-report:

```
impact(paths=["src/Application/Alpha/Plan/Plan.php"])
  →  176 nodes, spanning legacy/alpha, legacy/beta, src/compat, src/Application/Beta
     and legacy/alpha/web/saml/tests/…/SystemTest::testWriteFileMode,
     HEURISTIC 0.7, seeds_dropped: 1, ≈26 KB

impact(qnames=["Src\Application\Alpha\Plan\Plan::createPlan"])
  →  6 nodes, all RESOLVED, correct
```

> Round 11 §12.e(g′): *"**A 29× over-report.** Would it have hurt me? **YES — decisively.**
> **HOLD, and 10-G is confirmed a live loaded gun.** Narrow the wording: the *qname* half was fixed by
> 161; it is the **path seed** that walks the twin."*
> §14 (7-E): *"`impact` on a **non-core** file via path seed returned ≈26 KB — deliverable but 4.3× the
> next largest payload. **The inflation is the path seed, not the file's coreness.**"*
> §9.b: the evaluator declined the best-fit tool for a real blast-radius question and used
> `find_callers` instead — *"the veto I would have most wanted to break turned out to be protecting me
> from a 29× over-report."*

161 closed 9-A for a **shared qname**. The consuming repo's actual shape is a **shared trailing name
under different qnames**, which is why 165 had to exist for `find_callers` — and `impact`'s path seed
walks straight into it, at tier `RESOLVED`-looking confidence, on the one tool whose answer is acted on
destructively.

## Root cause

- `code_atlas/tools/impact.py:221-225` — when a path **does** hold indexed nodes, the branch appends
  every row's `qualified_name` **directly**, bypassing the local `take()` / `_resolve_seed` the qname
  branch uses at `:213`. Only the *empty* path is classified (`classify_missing_subject`, `:219`). So a
  path-derived seed is never classified, never counted as a resolution and never explained: one file
  becomes N seeds silently (the subject file here holds 102 symbols).
- `code_atlas/tools/impact.py:158` — `_split_ambiguous` asks
  `store.nodes_by_qualified_name(qname, …)` and treats `len(rows) > 1` as ambiguous. That detects a
  **duplicate of the exact qname**. A twin whose qname differs but whose trailing name is the same is
  invisible to it, so every path-derived seed is classified *walkable*.
- `code_atlas/tools/impact.py:100-101` — the walk then runs `store.impact_radius(walk_seeds, …)` over
  qname-keyed edges, and the bare-name HEURISTIC links pull in the twin's callers and callees. The
  payload's `seeds_dropped` counts nothing about this, because nothing was dropped.
- No field states **how many seeds one path expanded to**, so a reader cannot tell a 6-node answer
  about one symbol from a 176-node answer about 102 of them.

## Scope

Bring the path seed to parity with the qname seed 161 already fixed.

1. A path-derived seed goes through the **same classification** as a qname seed, so it can be disclosed,
   dropped or refused rather than silently walked.
2. A seed whose **trailing name** has a definition under another qname is disclosed — the 165 shape —
   or refused, whichever design records as the honest endpoint for a destructive answer.
3. The payload states the **seed expansion**: how many seeds the request's paths produced.

### Explicitly not in scope

- Changing the edge model. Edges are qname-keyed with no target node id; 161's AC1 deviation records
  that as architecturally settled, and this ticket must not reopen it.
- Dropping or re-tiering HEURISTIC rows. The tier is honest; the seed set is not.
- `impact_modules` — a follow-up if the seed fix does not inherit through the shared helper (140).

## Constraints

- **061** — a path seed on a file whose symbols have no same-named twins is byte-identical to today.
- **Cost** — `impact` is low-frequency and high-stakes; one bounded query per seed is acceptable, a
  query per walked node is not. Measure and record.
- **102** — a subject that produced no seed must still be distinguishable from a modelled zero.
- **R1.1** no language branch · **R3** no bump · **R4.2** order-stable seeds and sites.

## Acceptance criteria

1. A path seed over a fixture file whose symbols have same-named twins in another subtree either
   discloses the twins or refuses, and **never** returns a confident walk of one — pinned by a test
   that fails on today's code.
2. Every path-derived seed is classified by the same code path as a qname seed; a path subject that
   resolves to nothing is still counted and explained (102 unchanged).
3. The payload names the seed expansion (`seeds` / the design's recorded field) for a path request.
4. A path seed with no twinned symbols is byte-identical to today (061).
5. Cost measured; no per-node query added.
6. Determinism (R4.2), no language branch (R1.1), no bump (R3), and `impact_modules`' inheritance of
   the fix confirmed or filed.

## References

Field retro round 10 §15 ticket 6 (**not shipped**); round 11 §12.e(g′) (the 176-vs-6 measurement),
§9.b (the veto that paid off), §14 rows 10-G and 7-E (**the inflation is the path seed**), §14.a
carve-out (g′) rewording. `code_atlas/tools/impact.py:100-101,158,213,219,221-225`. Related:
[161](161_impact-resolves-a-shared-qname-to-one-twin-and-carries-no-freshness.md) (the qname half),
[165](165_find-callers-splits-across-twins-and-says-reason-ok.md) (the trailing-name shape),
[017](017_impact-engine.md),
[078](078_ambiguous-payload-still-picks-one-definition.md).
