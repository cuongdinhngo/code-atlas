---
id: 288
slug: the-one-lever-that-sounds-like-a-size-lever-is-not-one
title: '`read_symbol` returns a whole body at any size with nothing in the payload or the description warning that a subject is enormous, and `detail_level: minimal` — the one lever that sounds like it should help — only drops the docblock, so a 720-line method cost ~11,000 tokens to confirm two edits that a 40-line range would have shown'
phase: 1.5b
milestone: Agent-fit
status: todo
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
