---
id: 108
slug: module-page-neighbour-list-is-unbounded
title: Onboarding — a module page prints every neighbour, so the median page is 82 KB (M11)
phase: 3
milestone: M11
status: todo
depends_on: [088, 107]
---

## Why this exists (measured, anchor monorepo, commit `767a2ec7a4b4`)

`render_module` joins the **entire** neighbour tuple with no cap and no truncation flag
(`code_atlas/onboarding/artifact.py:394-395`):

```python
out = ", ".join(f"`{path}`" for path in page.outgoing) or _absent(page.fan_out)
incoming = ", ".join(f"`{path}`" for path in page.incoming) or _absent(page.fan_in)
```

Measured on the emitted tree (500 pages, `CA_IMPACT_MAX_NODES=500`):

| | Bytes |
|---|---:|
| median module page | 82,218 |
| p90 | 82,245 |
| largest page (644 neighbour paths) | 82,250 |
| pages ≥ 80 KB | **261 / 500** |
| all module pages | 24,643,326 |

Section breakdown of the median page — the four content fields total **29 bytes**:

```
## Role            13     ## Summary        10     ## In the tour  23,893
## Layer            6     ## Neighbours 58,196
```

One page is ≈ 20.5k tokens. **This is the only place in the repo that ignores the shared list
convention:** every other tool caps its list at `CA_MAX_RESULTS` and reports `truncated` (033/057/065).
`generate_onboarding`'s own payload already caps `results` — the page body does not.

`In the tour` has the same defect from a second cause: the SCC member list is printed in full on
**every** member of the cycle, so one 300-file cycle writes the same 24 KB three hundred times.

## Scope

- Cap both neighbour lists at `config.max_results`, and cap the SCC member list on the stop line.
- When a list is cut, say so in the page in the shape 107 already established for a different cause —
  `(N shown of M)` — so a cut list is never mistaken for the whole truth or for a real zero.
- Carry the cut into `manifest.json` and the `generate_onboarding` payload (`truncated` already exists).
- No new knob: reuse `CA_MAX_RESULTS`. R1.2 — no second abstraction for a cap that exists.

## Acceptance criteria

1. **AC1 (prove-the-guard-fails, R6.5).** A fixture module with `max_results + 5` neighbours emits a
   page listing exactly `max_results` of them; the test is observed red against today's code.
2. **AC2.** The page names the cut with both numbers, and a genuinely-empty list still renders the
   107 `_absent` wording — the two cases stay distinguishable.
3. **AC3.** Every member of an SCC larger than the cap gets the same capped, byte-identical stop line
   (R4.2 determinism).
4. **AC4.** Re-measured on the anchor repo: median page and total page bytes both reported in the
   working doc; median page under 8 KB at the default cap.
5. **AC5.** `manifest.json` and the payload agree with the pages about what was cut.

## Out of scope

The page's *shape* (whether a per-module page should exist at all) — that is 112/116. This ticket only
stops one page from being 82 KB.
