---
id: 107
slug: a-page-with-no-neighbours-and-no-summary-is-filler
title: Onboarding — a module page with no neighbours and no summary is filler, and 500 of them read as coverage (M11)
phase: 3
milestone: M11
status: todo
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
