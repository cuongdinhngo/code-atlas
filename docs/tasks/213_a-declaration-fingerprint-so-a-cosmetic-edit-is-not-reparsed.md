---
id: 213
slug: a-declaration-fingerprint-so-a-cosmetic-edit-is-not-reparsed
title: "The incremental byte-hash tier catches a file that did not change; nothing catches a file whose *declarations* did not change, so a reformat re-parses the tree"
phase: 1.5b
milestone: Freshness
status: todo
depends_on: [212, 052, 080]
---

## Why this exists

This is [212](212_an-incremental-update-escalates-on-correctness-but-never-on-cost.md)'s Scope 3,
split out at its Gate 0 when the ticket was measured against the code and found to be **L**. The
maintainer ratified the split; 212 shipped the upper tier (a cost escalation) and this ticket is the
lower one.

**212's premise needed correcting first, and the correction is this ticket's starting point.** 212
said *"No lower tier… nothing compares what changed inside a file against what the graph stores."*
There **is** one: `incremental_update`'s `hashing` phase (`code_atlas/indexer.py:386-404`) calls
`file_is_current` (`:568-571`), which compares the file's current bytes against the hash the index
stored and skips the parse when they match. A **dependent** is deliberately excluded from that skip,
with the reason in a comment beside it.

So the real gap is one tier up: a file whose **bytes changed** but whose **declarations did not** is
re-parsed. A reformat, a comment edit, a copyright-header bump: every touched file pays a full parse,
re-link and reconcile to produce rows the graph already holds.

### The constraint that shapes the answer, and it is not negotiable

A fingerprint over *declarations* cannot be computed without knowing the language: comments and
string literals are syntax. **R1.1 forbids a language branch in the core**, and the parse is what
produces declarations — so "hash the declarations, then decide whether to parse" is circular for the
run that would benefit.

The maintainer's ratified answer is the honest subset: a **language-agnostic, whitespace-normalised
hash**. Collapse every run of whitespace and hash the remainder.

- It **catches** the case 212's own sentence names first: a reformat, an indentation change, a line
  ending or trailing-whitespace sweep.
- It does **not** catch a comment edit or a string-literal change. Saying so here is the point — an
  implementer should not discover it at review.
- A fingerprint that cannot be computed (unreadable file, decode error) must fail loud into
  **"parse it"**, never into "skip it" (**R5.3**).

Two paths are explicitly rejected up front, so they are not re-litigated:

1. **A comment-aware normaliser in the core** — an R1.1 violation, and the rule has no exception for
   "just a small regex".
2. **A declaration digest in the adapter contract** — each adapter reporting a digest is a contract
   bump (**R3**) across three adapters, and the digest only exists *after* the parse, so it cannot
   save the parse that produced it. It would enable a *next-run* saving, which is a different (and
   larger) design.

## Scope

1. **A whitespace-normalised fingerprint stored per file**, beside the byte hash rather than
   replacing it: the byte hash stays the fast path, and the fingerprint is consulted only when the
   byte hash misses.
2. **A file whose fingerprint is unchanged is not parsed** — and the graph is identical to a run
   that did parse it (**R4.2**, and this ticket's central risk).
3. **The skip is reported.** A skipped file must never look like an indexed one (212's Scope 4, and
   202's lesson: a build that did less work must not leave an index that reports as though it did
   more).
4. **Never skip on a correctness route.** The three correctness escalations and 212's cost tier
   outrank the fingerprint; a contract-era change re-parses everything regardless.
5. **Measure what it buys** on the anchor: how many files a reformat-shaped commit skips, and the
   wall-clock difference. If the answer is "almost none on real commits", that is the finding, and
   the tier should not ship on a hope.

### Explicitly not in scope

- **Comment- or string-literal-aware normalisation** (R1.1) and **an adapter-side digest** (R3) —
  both rejected above.
- **Cross-run caching of parse results.** A fingerprint decides whether to parse; it never stores
  what a parse produced.
- **The upper tier**, which is [212](212_an-incremental-update-escalates-on-correctness-but-never-on-cost.md).

## Constraints

- **R1.1** — no language branch in the core. The normaliser sees bytes, never syntax.
- **R4.2** — the graph is identical whichever route was taken. A fingerprint that misses a construct
  silently under-indexes while the index still reports current; guard it directly.
- **R5.3** — a fingerprint that cannot be computed fails loud into "parse it".
- **R6.5** — the guard ships only once observed failing: a file whose text changes and whose
  declarations do not, proven identical either way; then one whose declarations do change, proven
  not skipped.
- **R6.9** — assert at the consumer: the guard reads the resulting graph, not the fingerprint value.

## Acceptance criteria

1. A file whose whitespace-normalised fingerprint is unchanged is not re-parsed, and the resulting
   graph is identical to a run that did re-parse it.
2. A file whose fingerprint changed is never skipped, proven by a fixture that fails without the
   guard.
3. A fingerprint that cannot be computed results in a parse, and a test exhibits that path.
4. The skip is visible in the build report; a skipped file is distinguishable from an indexed one.
5. The correctness escalations and 212's cost tier still take precedence, pinned by a test.
6. Scope 5's measurement is recorded with its method — including the honest answer if the saving is
   negligible on real commits.

## References

[212](212_an-incremental-update-escalates-on-correctness-but-never-on-cost.md) (the ticket this was
split from, and the upper tier), [052](052_incremental-noop-cost.md) (the phase timings and the
profiler that measures them), [080](080_noop-incremental-cost-and-uninterpretable-writes.md) (the
no-op floor), [202](202_a-killed-build-leaves-an-index-that-reports-current.md) (a build that did
less work must not report as though it did more).
