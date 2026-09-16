---
id: 288
slug: the-one-lever-that-sounds-like-a-size-lever-is-not-one
title: '`read_symbol` returns a whole body at any size with nothing in the payload or the description warning that a subject is enormous, and `detail_level: minimal` — the one lever that sounds like it should help — only drops the docblock, so a 720-line method cost ~11,000 tokens to confirm two edits that a 40-line range would have shown'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [163, 061, 245]
---

## Why this exists (field retro — the anchor repo, round 25 §4, 2026-09-15)

One call returned a 720-line method body — roughly 11,000 tokens — to confirm two edits had landed. A
line-range read of the surrounding 40 lines would have answered it. The retro is explicit that this is
not user error:

> *"nothing in the payload or the tool description warns that a subject is enormous, and the one lever
> that sounds like it should help does not apply."*

That lever is `detail_level: minimal`. 163 defined it as *the declaration range alone, no docblock*
(`read_symbol.py:511-519` → `source_slice.py:29-44`), which is the right contract for the mismatch 163
fixed — and for a method the declaration range **is** the body, so `minimal` removes a comment block
and nothing else. The parameter is honest about what it does and silent about what a reader assumed it
does.

This is the only item in that round that cost real tokens for no return, on a tool the same round rates
the workhorse. It is also the shape 245 already treated elsewhere: an answer that is technically
complete and practically unusable earns a **route**, not a truncation.

The retro proposes both fixes and prefers the second, for a reason worth keeping:

> *"a `max_lines` parameter … or automatic degradation: above N lines, return the symbol's outline plus
> the signature, and say `body_elided: true, line_count: 720, use file_outline or a line range`. The
> second is better, because it turns the failure into a routing hint rather than a truncation."*

## The counter-evidence, which bounds the fix

A second round the same day read a **508-line** method whole and calls it the decisive call of its
session:

> *"Seeing that needs the whole method at once. Any `sed`-a-range or `grep -A20` approach reads one of
> the three sites and misses the interaction … precisely how the previous two attempts at this ticket
> shipped an incomplete fix."*

It priced it honestly — *"roughly 8k tokens in one response … for a method that size it bought a
correct diagnosis that two prior sessions missed, so it paid"* — and named the guarantee that makes it
worth paying for: symbol boundaries come from the parse, not from `sed` arithmetic.

So the two rounds do not disagree about the threshold; they disagree about what happens at it. **The
failure is that the caller has no choice, in either direction.** One session paid 11k tokens it did not
want; the other needed the whole body and would have been wrong without it. A degradation that removes
the whole-body read trades this ticket's cost for the other round's defect.

That round also names the missing half: *"I wanted lines 1040–1100 of a method I had already read; the
only options were all of it again or fall back to `sed`."* A line-range read **within** a symbol is the
same fix from the other side, and it is what makes an elided answer actionable rather than merely honest.

## Scope / Deliverables

- **A body above a threshold degrades instead of shipping whole**, carrying the count and a route
  (`file_outline`, or a line range) rather than a silently truncated body — a caller must never be
  unable to tell an elided body from a short one.
- **Name the threshold where the reader can see it** — in the tool description, not only in source, so
  the degradation is predictable rather than surprising.
- **The whole body stays reachable, always.** The route must name how to get it, and a caller that
  asks for it gets it — the degradation is a default, never a ceiling. A large body is expensive, not
  wrong: one round's decisive call was a 508-line method read whole.
- **A line range within a symbol.** Let a caller read `line_start…line_end` of a resolved subject
  without re-reading it whole and without falling back to `sed` — the read that makes an elided answer
  actionable, and the one a session asked for by name.
- **Decide `max_lines` in design, not here.** An explicit caller-set cap is a reasonable addition
  beside the automatic route; it is not a substitute for it, because the caller who needs it is the one
  who did not know the subject was large.

## Constraints

- 061: a subject under the threshold is byte-identical to today, `minimal` and `standard` both.
- R4.2: the threshold is a constant, not a token estimate that could drift with a tokenizer.
- R6.7: one definition site for the threshold; `file_outline` and `read_symbol` must not each hold one.
- Never a silent truncation — the field's standing objection across rounds is refusals that read as
  answers, and a body cut without a marker is that failure with the sign flipped.
- Do not repurpose `minimal`: 163's contract (slice matches its own `line_start`/`line_end`) stays.

## Acceptance criteria

- A subject above the threshold returns no full body by default, carries its line count, and names a route.
- The same subject's full body is still obtainable in one call by a caller that asks for it.
- A line range inside a resolved symbol returns exactly those lines, with boundaries from the parse.
- A subject below it is byte-identical to today at both detail levels.
- An elided answer is distinguishable from a complete one by a field, not by inspecting the source.
- The threshold is stated in the tool description and defined once.
- `minimal`'s 163 contract is unchanged.

## References
`code_atlas/tools/read_symbol.py:56-85,511-519`, `code_atlas/source_slice.py:29-44`,
[163](163_read-symbol-minimal-is-byte-identical-to-standard.md),
[061](061_payload-weight.md),
[245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md).
Origin: field retro round 25 §4 / §8.1, 2026-09-15 — the round's top-priority ask; bounded by the
round-16 retro of the same date (§1.3), which reads a 508-line body whole and calls it decisive.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 288 — read_symbol body elision (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** M · **BASELINE:** green · **INPUT KIND:** ticket
- **Current phase:** finalise
- **Session status:** autorun — reviewer off; challenger CLEAN; gate pending

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: BODY_LINE_THRESHOLD=600 — cites ticket counter-evidence (508-line decisive read stays whole by default; 720-line wasteful case elides). full_body + optional max_lines + line_start/line_end — cites Scope bullets 3–5 and "Decide max_lines in design".

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=5 R=5 G=1 AC=7`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | minimal is not a size lever | auto-elide + route, not repurpose minimal | D1 | AC1 | ✅ |
| C1 | Constraints | 061 below-threshold identical | no new fields under threshold | D1 | AC4 | ✅ |
| C2 | Constraints | R4.2 constant threshold | BODY_LINE_THRESHOLD in source_slice | D1 | AC6 | ✅ |
| C3 | Constraints | R6.7 one definition site | single constant; TOOLS cites it | D1 | AC6 | ✅ |
| C4 | Constraints | never silent truncation | body_elided field + signature only | D1 | AC5 | ✅ |
| C5 | Constraints | do not repurpose minimal | 163 contract unchanged | D1 | AC7 | ✅ |
| R1 | Scope | degrade above threshold | elide + line_count + route | D1 | AC1 | ✅ |
| R2 | Scope | name threshold in description | docstring + TOOLS.md | D3 | AC6 | ✅ |
| R3 | Scope | whole body always reachable | full_body / max_lines | D1 | AC2 | ✅ |
| R4 | Scope | line range within symbol | line_start/line_end clamped | D1 | AC3 | ✅ |
| R5 | Scope | decide max_lines in design | optional caller cap | D1 | proving | ✅ |
| AC1 | AC | above: no full body + count + route | proving | D2 | proving | ✅ |
| AC2 | AC | full body obtainable | proving full_body | D2 | proving | ✅ |
| AC3 | AC | line range exact | proving | D2 | proving | ✅ |
| AC4 | AC | below identical both levels | proving | D2 | proving | ✅ |
| AC5 | AC | elided distinguishable by field | body_elided | D2 | proving | ✅ |
| AC6 | AC | threshold in description, once | docstring + constant | D2 | proving | ✅ |
| AC7 | AC | minimal 163 unchanged | proving minimal | D2 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: read_symbol always ships the full declaration slice; minimal only drops the docblock (163), so a 720-line method costs ~11k tokens with no route.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R4.2 ✅ · R6.7 ✅ · 061 ✅`

Ran at 98561c078bc472c5266d72cf8abb3d0e9388206d

```
$ .venv/bin/python -m pytest tests/test_read_symbol_minimal_drops_docblock.py -q --tb=no
....                                                                     [100%]
4 passed in 0.20s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: BODY_LINE_THRESHOLD=600 in source_slice (R6.7); default elide to signature + body_elided/line_count/try_instead; full_body and max_lines; line_start/line_end clamped range.
- Rejected: repurpose minimal (163); silent truncate; threshold <508 (would force opt-in on the decisive field read).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_read_symbol_body_elision.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | threshold + elision/range/full_body | source_slice.py, read_symbol.py | read_symbol payload | 1/1 |
| D2 | proving | tests/test_read_symbol_body_elision.py | — | 1/1 |
| D3 | name threshold | docs/TOOLS.md, docs/design/payload.md | docs | 1/1 |

## Phase 3 — Execute

**Branch:** feat/288-read-symbol-body-elision
**Axis 1:** source_slice · read_symbol · proving · docs.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at 98561c078bc472c5266d72cf8abb3d0e9388206d

```
$ .venv/bin/python -m pytest tests/test_read_symbol_body_elision.py tests/test_read_symbol_minimal_drops_docblock.py -q --tb=no
..........                                                               [100%]
10 passed in 0.35s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — round-1 NOT CLEAN (minimal elision range mismatch); fixed line_end=decl_start + hint carries declaration span; round-2 CLEAN. agents 746ed5d4-1c68-4905-9c52-219da40e7ce5 / b5638127-156e-4790-a676-1626bae5992c

Verify-only:

Ran at 98561c078bc472c5266d72cf8abb3d0e9388206d

```
$ .venv/bin/python -m pytest tests/test_read_symbol_body_elision.py tests/test_read_symbol_minimal_drops_docblock.py -q --tb=no
..........                                                               [100%]
10 passed in 0.35s
```

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_read_symbol_body_elision.py — 6 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN
PR: https://github.com/cuongdinhngo/code-atlas/pull/382

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
