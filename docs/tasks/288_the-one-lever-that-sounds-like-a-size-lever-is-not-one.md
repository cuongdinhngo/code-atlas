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

## Scope / Deliverables

- **A body above a threshold degrades instead of shipping whole**, carrying the count and a route
  (`file_outline`, or a line range) rather than a silently truncated body — a caller must never be
  unable to tell an elided body from a short one.
- **Name the threshold where the reader can see it** — in the tool description, not only in source, so
  the degradation is predictable rather than surprising.
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

- A subject above the threshold returns no full body, carries its line count, and names a route.
- A subject below it is byte-identical to today at both detail levels.
- An elided answer is distinguishable from a complete one by a field, not by inspecting the source.
- The threshold is stated in the tool description and defined once.
- `minimal`'s 163 contract is unchanged.

## References
`code_atlas/tools/read_symbol.py:56-85,511-519`, `code_atlas/source_slice.py:29-44`,
[163](163_read-symbol-minimal-is-byte-identical-to-standard.md),
[061](061_payload-weight.md),
[245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md).
Origin: field retro round 25 §4 / §8.1, 2026-09-15 — the round's top-priority ask.
