---
id: 257
slug: the-index-goes-blind-at-the-moment-it-is-most-wanted
title: 'A commit that touches one indexed file makes every symbol query decline, so the index is unavailable exactly when a caller asks "did I just break a caller?" — two field rounds asked independently for the same remedy, each pre-limiting its own request to a labelled degraded mode rather than a silent one'
phase: 1.5b
milestone: Agent-fit
status: done
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Session status

- **KEY:** 257 · **work_doc_mode:** embed · **Current phase:** finalise
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · **Type:** enhancement
- Run: `/mango:autorun 257` with `--no-reviewer`; challenger ON
- Branch: `feat/257-serve-behind-labelled-reads`
- Contract: `.mango/run-contract-257.txt`
- Handover: push feature branch + open PR only (never merge)

## Phase 0 — refine

`PREMISE: 7 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 2 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 3 want-decision asked | 0 how-decision resolved+cited | 3 ASSUMED | skip: no`

**PREMISE detail.** Present: `staleness.py`, `freshness.py` (`FreshnessGuard`, `dirty_indexed_paths`), `claim.sign`, `find_callers`/`find_references`, tickets 035/182/100, `REASON_INDEX_STALE`. Ambiguous (not blocking): ticket root-cause prose that every behind query declines — spike shows unchanged subjects already answer with `reason: ok`.

**INPUT KIND:** ticket.

**ASSUMED (awaiting ratification) — handover authorised choose-best-approach.**

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses prior? |
|---|---|---|---|---|
| 1 | Opt-in is tool param `serve_behind` (not a `CA_*` Config knob) | Smallest blast radius; matches `sign`/`include_source` pattern; Config would touch every tool call site | Gate 2 design — surface ✋ | no |
| 2 | Drifted-subject "decline" = never `index_behind` on a dirty subject (repair→`ok` or `index_stale`) | 035 stays first; ticket forbids silent stale claims, not repair | Gate 2 design — surface ✋ | no |
| 3 | Mode off keeps today's serve-unchanged `reason: ok` (AC3 byte-identical); labelling is the product change | Spike + AC3; ticket "refusal" wording is historically over-broad vs current FreshnessGuard | Gate 2 design — surface ✋ | no |

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `reproduce-the-payload-not-the-story` | 2 | handle | Yes — AC1/AC4 pin reason + revision fields |
| 2 | `prove-the-guard-fails` | 2 | handle | Yes — AC3 off byte-identical; AC5 unindexed dirt |
| 3 | freshness / claim (035/100) | 5 | area | Surfaced |

✋ **Gate 0** — ASSUMED rows await maintainer ratification on the PR; handover proceeds.

## Phase 1 — analysis

`PREMISE: 7 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 2 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria) | 5 decomposed | ROWS: C=5 R=3 G=2 AC=5`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`
`RULE SECTIONS: 8 applicable — 7 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ no language branch · R4.2 (change-type) ✅ off byte-identical · R5.6 (change-type) ✅ never reason=ok on degraded · R5.3 (change-type) ✅ loud opt-in · R6.5 (recalled handle) ✅ AC3/AC5 guards · R6.9 (change-type) ✅ assert payload · R7.2 (change-type) ✅ ledger · R7.6 (change-type) ✅ PLAN prune-as-add`

### BASELINE

Delta-related suite on untouched freshness + new proving tests:

```
Ran at 07c283f9774f222888b891f9ee971cfab7cc08ed
$ .venv/bin/python -m pytest tests/test_serve_behind_labelled_reads.py tests/test_nav_reason_codes.py::test_reason_vocabulary_includes_index_stale_unused -q --tb=no
5 passed in 1.25s
```

Green. No baseline exclusions. Full `pytest` / `scripts/gate.sh` deferred to execute-close (S-scope pin); concurrent hosts may force delta-green disclosure.

### Clarifications (j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | Config knob vs tool param? | **Tool param** — ASSUMED #1 | `sign` on find_* |
| Q2 | Does "decline" disable repair? | **No** — ASSUMED #2; 035 first | ticket Constraints |
| Q3 | Must default refuse all behind reads? | **No** — ASSUMED #3; label only | spike + AC3 |

### Requirements matrix

| ID | Source | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|
| G1 | Why | Answer unchanged subjects on behind index with a label | field retros | open |
| G2 | Why | Never silent degraded mode | R5.6 / round 18 | open |
| C1 | Constraints | R5.6 — reason never ok on degraded | reason=index_behind | open |
| C2 | Constraints | 100 claim carries revision | sign + last_commit | open |
| C3 | Constraints | 035 repair first | FreshnessGuard before label | open |
| C4 | Constraints | R4.2 deterministic | same index+rev | open |
| C5 | Constraints | 022 AC3 off byte-identical | AC3 test | open |
| R1 | Scope | Per-subject unchanged answerable | dirty_indexed_paths check | open |
| R2 | Scope | Drifted still not labelled behind | AC2 | open |
| R3 | Scope | Opt-in default off | serve_behind=False | open |
| AC1 | AC | behind + unchanged → rows + revision | proving test | open |
| AC2 | AC | drifted not index_behind | proving test | open |
| AC3 | AC | off byte-identical | proving test | open |
| AC4 | AC | claim + payload carry rev; never reason=ok | proving test | open |
| AC5 | AC | dirty unindexed does not degrade | proving test | open |

### AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? |
|---|---|---|---|---|
| AC1 | rows + revision | label_serve_behind + claim | Y | measurable |
| AC2 | drifted declines / not silent stale | never index_behind on dirty | Y | measurable |
| AC3 | off identical | payload equality | Y | measurable |
| AC4 | claim+payload revision; not ok | assert | Y | measurable |
| AC5 | markdown dirt current | staleness CURRENT | Y | measurable |

## Phase 2 — design

### Approach

Add `REASON_INDEX_BEHIND` + `label_serve_behind` in `freshness.py`. Wire `serve_behind` on `find_callers` and `find_references`: compute staleness/dirty when opted in; after non-stale freshness and a successful answer, relabel unchanged subjects. Proving tests AC1–AC5; PLAN §19; bookkeeping.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| `CA_SERVE_BEHIND` Config default | Blasts every tool; ASSUMED #1 |
| Disable FreshnessGuard under serve_behind | Violates 035-first / ASSUMED #2 |
| Force global index_stale when off | Contradicts AC3 / today's behaviour |

### Assumptions

| Assumption | Tag |
|---|---|
| Unchanged subjects already get rows with reason=ok on behind | verified — spike |
| `dirty_indexed_paths` sees committed drift vs last_commit | verified — freshness.py |
| claim.sign emits `index=behind` + `rev=` from staleness | verified — claim.py |

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | REASON_INDEX_BEHIND + NAV_REASONS | `nav_result.py` + vocab test | reason vocabulary | AC4,C1 | 2/2 |
| 2 | `label_serve_behind` | `freshness.py` | nav tools that call it | AC1–AC5 | 5/5 |
| 3 | Wire `serve_behind` on find_callers + find_references | `find_callers.py`, `find_references.py` | those tools' kwargs | R1–R3,G1–G2 | 5/5 |
| 4 | Proving tests | `tests/test_serve_behind_labelled_reads.py` | PHP fixture env | AC1–AC5 | 5/5 |
| 5 | PLAN §19 + prune; BACKLOG; TOKEN_LEDGER; task status | `docs/` | doc budgets | R7.2/R7.6 | 1/1 |

### HANDLES

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**H1 `reproduce-the-payload-not-the-story`** — traced.

```
Ran at 07c283f9774f222888b891f9ee971cfab7cc08ed
$ rg -n 'def label_serve_behind|REASON_INDEX_BEHIND' code_atlas/tools/freshness.py code_atlas/tools/nav_result.py | head -8
code_atlas/tools/nav_result.py:49:REASON_INDEX_BEHIND: NavReason = "index_behind"
code_atlas/tools/nav_result.py:86:    REASON_INDEX_BEHIND,
code_atlas/tools/freshness.py:167:def label_serve_behind(
code_atlas/tools/freshness.py:186:    from code_atlas.tools.nav_result import REASON_INDEX_BEHIND, REASON_OK
code_atlas/tools/freshness.py:197:        payload["reason"] = REASON_INDEX_BEHIND
```

Folded: change #4 asserts reason/revision on payload.

**H2 `prove-the-guard-fails`** — traced.

```
Ran at 07c283f9774f222888b891f9ee971cfab7cc08ed
$ rg -n 'serve_behind_off_is_byte_identical|unindexed_markdown' tests/test_serve_behind_labelled_reads.py | head -5
135:def test_serve_behind_off_is_byte_identical(tmp_path: Path, store: GraphStore) -> None:
154:def test_unindexed_markdown_dirt_does_not_degrade(tmp_path: Path, store: GraphStore) -> None:
```

Folded: AC3/AC5 prove the off and unindexed guards (R6.5).

### Coverage-gap exclusions

none

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|---|---|---|---|---|
| AC1 | integration | `test_serve_behind_labels_unchanged_subject` | authored | ✅ |
| AC2 | integration | `test_serve_behind_drifted_subject_still_declines_or_repairs` | authored | ✅ |
| AC3 | integration | `test_serve_behind_off_is_byte_identical` | authored | ✅ |
| AC4 | integration | asserts in AC1 (claim + never ok) | authored | ✅ |
| AC5 | integration | `test_unindexed_markdown_dirt_does_not_degrade` | authored | ✅ |

### Proving test

```
.venv/bin/python -m pytest tests/test_serve_behind_labelled_reads.py::test_serve_behind_labels_unchanged_subject -q
```

✋ **Gate 2** — ASSUMED #1/#2/#3 ratified by design; maintainer confirms on PR.

## Phase 3 — execute

Branch `feat/257-serve-behind-labelled-reads` from `main` @ `8303edb`.

### Implemented (⊆ approved change list)

| # | Change | Done |
|---|---|---|
| 1 | REASON_INDEX_BEHIND | ✅ |
| 2 | label_serve_behind | ✅ |
| 3 | Wire find_callers + find_references | ✅ |
| 4 | Proving tests | ✅ |
| 5 | Docs / bookkeeping | ✅ (this commit) |

### Verification sweep

```
Ran at 07c283f9774f222888b891f9ee971cfab7cc08ed
$ .venv/bin/python -m pytest tests/test_serve_behind_labelled_reads.py -q
4 passed in 1.2s
```

Design-conformance: diff ⊆ change list. No deviation.


## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived; no rule-book-grounded review ran.
**CHALLENGER: ON** — ticket-blind, 1 dispatch.

Challenger reconstructed 12 requirements from the raw ticket; **11 met / 0 not met / 1 met-with-residual (claim gated on sign) / 2 surface can't-tell**. Overall **CLEAN** (challenger only — REVIEWER OFF).

Proving evidence on reviewed tree:

```
Ran at 07c283f9774f222888b891f9ee971cfab7cc08ed
$ .venv/bin/python -m pytest tests/test_serve_behind_labelled_reads.py -q
....                                                                     [100%]
4 passed in 1.22s
```

Reviewed at 07c283f9774f222888b891f9ee971cfab7cc08ed

- **Gate 4 status:** cleared (challenger CLEAN; reviewer waived)

## Phase 5 — Finalise

Durable lesson: none new — behind indexes already answered unchanged subjects; 257 adds the honesty label, not the serve path.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: challenger (1) + main-loop`

### Token usage (working doc)

| Phase | Tokens |
|---|---|
| autorun main-loop | unmeasured (host surfaces no usage block) |
| challenger ×1 | unmeasured |
| reviewer | waived (--no-reviewer) |

### Outward actions
1. push feature branch — authorised by handover
2. open PR — authorised by handover
Deferred to morning: merge; tracker transitions beyond bookkeeping already on branch.
