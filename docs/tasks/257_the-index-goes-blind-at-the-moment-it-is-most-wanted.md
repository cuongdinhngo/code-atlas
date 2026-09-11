---
id: 257
slug: the-index-goes-blind-at-the-moment-it-is-most-wanted
title: 'A commit that touches one indexed file makes every symbol query decline, so the index is unavailable exactly when a caller asks "did I just break a caller?" — two field rounds asked independently for the same remedy, each pre-limiting its own request to a labelled degraded mode rather than a silent one'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [035, 182, 100]
---

## Why this exists (field retros — the anchor repo, 2026-09-11, rounds 17 and 18)

Two sessions, written independently, asked for the same thing and neither asked for it naively.

Round 17, ask #2:

> **Serve reads from a `behind` index for unchanged files.** Global refusal on a three-file diff forces
> an unnatural "do all your symbol work before you start editing" discipline. You already track
> `dirty_indexed_files`; answer for the rest and mark the response.

Round 18, ask #4, which had just been bitten by it mid-implementation:

> the index goes blind the moment I commit, which is precisely when I most want to ask "did I just
> break a caller?". A read-only mode that answers from the last built revision and *labels every row
> with that revision* would be more useful to me than a refusal — **I can judge a two-commit-old
> answer, I cannot judge nothing.** I recognise this cuts against the honesty property that makes the
> rest of the tool trustworthy, so treat it as a request for a **clearly-labelled degraded mode, not
> for a silent one.**

Round 18 also fixed the rule's wording, which matters for scoping this: staleness is driven by dirty
*indexed* files, not a dirty tree — four modified markdown files kept `staleness: current` and
`dirty_indexed_files: 0`. So the cliff is narrow and sharp: documentation churn costs nothing, and one
commit touching one `.php` file stops every symbol query.

Two independent askers, each volunteering the constraint that protects the property they value, is the
strongest signal in the retro corpus for a change that touches the honesty layer.

## Root cause

Staleness is evaluated for the answer, not for the subject. A `behind` index declines globally
(`reason: index_stale`, `try_instead: file_outline`) even when the subject's own file is byte-identical
to what was indexed — and the store already knows which files drifted, because `dirty_indexed_files`
is computed and reported. The refusal is correct in its intent (182: a stale row is worse than no row)
and over-broad in its reach.

## Scope

A **labelled** read from a `behind` index, off by default, in which every row states the revision it
describes.

Phase 2 decides the shape; the ticket binds the properties, not the mechanism:

- **Per-subject, not per-index.** A subject whose file is unchanged since the build is answerable; a
  subject in a drifted file is not, and still declines.
- **The label is not optional and not a footnote.** Every row, or the payload that carries them, names
  the revision. A degraded answer that can be quoted without its revision is the silent mode both
  askers explicitly refused.
- **Opt-in.** The default stays today's refusal, so no existing caller silently starts reading old
  rows.

## Constraints

- **R5.6** — the answer says what it is. `reason` is never `ok` on a degraded read.
- **100's `claim` line** — an answer that can be quoted must carry the revision it describes; this is
  the existing mechanism for exactly that and should be reused, not re-invented.
- **035's read-through repair stays first.** Where the subject's file can be reparsed cheaply, repair
  it and answer fresh — degraded mode is the fallback, not the shortcut.
- **R4.2** — deterministic for a given index and revision.
- **022 AC3** — with the mode off, every payload is byte-identical to today's.

## Acceptance criteria

- **AC1** With the mode on and the index one commit behind, a query about a subject in an **unchanged**
  file returns rows, each carrying the revision the index describes.
- **AC2** With the mode on, a subject in a **drifted** file still declines — the degraded mode widens
  what is answerable, never what is claimed.
- **AC3** With the mode off, behaviour is byte-identical to today (the proving pair for 022 AC3).
- **AC4** No degraded row can be quoted without its revision: the `claim` line and the payload both
  carry it, and a test pins that a degraded answer never reports `reason: ok`.
- **AC5** The distinction round 18 corrected is pinned by a test: dirty *unindexed* files (markdown)
  do not degrade anything.

## References

- `code_atlas/tools/staleness.py`, `code_atlas/tools/freshness.py` (`FreshnessGuard`), and the
  `REASON_INDEX_STALE` arms in each navigation tool.
- [035](035_read-through-freshness.md) — read-through repair, which this must not replace.
- [182](182_find-orphans-answers-with-rows-it-has-flagged-unreliable.md) — the refusal this narrows rather than reverses.
- [100](100_claim-signing-output-mode.md) — the `claim` line, the existing carrier for "which revision is this true of".
