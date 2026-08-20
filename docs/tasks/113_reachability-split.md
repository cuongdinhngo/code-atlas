---
id: 113
slug: reachability-split
title: Onboarding — "zero inbound" is four different populations, and reporting one number misleads (M11)
phase: 3
milestone: M11
status: todo
depends_on: [083, 112]
---

## Why this exists (measured, anchor monorepo)

`architecture_overview` and the artifact report **`module entry points: 8,477`** — every file with
`fan_in == 0`. The mockup's first draft turned that into *"45 % of files are entry points"*, and a
reviewer standing in for a first-day developer read it as *"this app has 8,475 endpoints"* and said it
would make them panic. That reading is the artifact's fault, not theirs.

Split by path shape, the same 8,475 files are four unrelated things:

| Population | Count |
|---|---:|
| web entry points (web root, controller dir, or an `index`/`main` file) | 1,000 |
| vendored libraries | 1,967 |
| tests and fixtures | 1,776 |
| **not statically resolvable** | **3,732** |
| ⤷ view/template files, loaded by dynamic `include` | 2,254 |
| ⤷ no inbound **and** no outbound edge | 512 |

Two conclusions the current single number hides: the real web surface is ~1,000, and the only population
worth investigating as possible dead code is **512** — not 3,732, because a PHP view with no static
inbound edge is a dynamic include, not dead. Calling those 3,732 files dead would be a false accusation
against the codebase.

## The R2.2 problem this ticket must solve honestly

The prototype detects vendored code by **library name** (`tcpdf`, `mpdf`, `adodb`, …). That is framework
naming and **would violate R2.2 if copied into the core**. Acceptable signals instead, in preference
order:

1. The language's own dependency standard — Composer's `vendor/` directory and the autoload roots
   declared in `composer.json`. This is a PSR/toolchain standard, not a repo's names, and it belongs in
   the **PHP adapter**, not the core, if it needs parsing.
2. Purely structural: no inbound *and* no outbound edge; or a subtree with no edge crossing its boundary.
3. Existing configuration the operator already sets (`stub_roots`), which is the operator's statement
   about their own repo rather than the core guessing.

If none of these can carry the vendor bucket cleanly, the honest outcome is **three buckets, not four**,
and the ticket says so rather than shipping a library-name list.

## Scope

- Classify zero-inbound files into the buckets above, using only R2.2-safe signals, and expose the
  split — never the single total — in `architecture_overview`, the dataset (112) and the artifact.
- Report the "worth investigating" bucket as a bounded sample plus a count, labelled as *a list to
  check, not a conclusion*.
- Keep the raw total available for anyone who wants it; it stops being the headline.

## Acceptance criteria

1. **AC1 (R6.5).** A fixture with one file in each bucket yields four (or three, per the judgment above)
   distinct counts — observed red against today's single number.
2. **AC2.** No library, framework or product name appears in the classifier; the R2.2 grep-gate covers
   the new code.
3. **AC3.** A view-like file with no inbound edge is never labelled dead; a file with no inbound *and* no
   outbound edge is, and the wording is a suspicion rather than a verdict.
4. **AC4.** Re-measured on the anchor repo and two pinned public repos; every bucket count recorded. A
   repo where a bucket is empty renders an honest zero, not an omitted row.
5. **AC5.** Any bucket the classifier cannot fill under R2.2 is dropped with the reason stated in the
   output, not silently merged into another bucket.

## Out of scope

Actually removing dead code, and resolving dynamic includes (that is the long-standing PSR-4 /
autoload-aware include follow-up in BACKLOG, not this ticket).
