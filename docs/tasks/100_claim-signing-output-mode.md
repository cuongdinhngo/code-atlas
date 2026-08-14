---
id: 100
slug: claim-signing-output-mode
title: 'The agent pasted nine kinds of evidence into its PR and zero graph payloads — while holding the strongest one'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [017, 057, 061]
---

## Goal
The field session's PR body pastes **nine** kinds of counted evidence: an HTTP status, two byte
counts, a header count, a row count, two verbatim JavaScript `alert()` strings, a test count, an
assertion count. It contains **zero** code-atlas output — although the session had already run
`impact` over the four changed paths and received
`seeds_dropped: 0, frontier_skipped_non_resolved: 0`, 25 rows all `confidence_tier: "RESOLVED"`.

The claim that went into the PR instead was prose: *"No product code, no `src/` consumer."* A reader
cannot check it. The payload that could have signed it was already on screen and was discarded.

The evaluator's own reading, offered against its own interest: *"my behaviour treated the browser as
an evidence source and code-atlas as a search layer — which is, verbatim, the decision this file
feeds."* And its diagnosis: *"the gap between 'the tool knows' and 'the reviewer can check' was, in
this session, entirely me — and that is a product problem, not a discipline problem, because I pasted
every other tool's evidence unprompted."*

That is the argument for this ticket. Every other tool in that session shipped output the agent could
quote. code-atlas ships JSON that answers a question and reads like an internal payload, so it stops
at the agent.

## Why this is the strategic ticket, not a formatting nicety
code-atlas cannot win the "find the code" race — that premise was refuted in §19 (2026-08-08), and
grep on the anchor tree measures 0.07–8.7 s at every scope. What survives is the class of claim a
text search **cannot make**: a *modelled zero*, a *second independent count*, and *identity across a
rename*. Those are not search results — they are **attestations**. An attestation that never reaches
the artifact where the claim is made has, for practical purposes, not been produced.

The consumer already exists in this project's own workflow: a gated lifecycle in which *every claim is
a counted artifact* and a PR template that must be filled with evidence. code-atlas is the natural
producer for the rows about code relationships, and today it produces none of them in quotable form.

## Scope / Deliverables
- **A quotable line per answer**, opt-in, carrying the four things a reader needs to re-run it:
  **subject · question · answer · revision**. The revision half is already available
  ([077](077_index-cannot-name-the-revision-it-describes.md): `last_ref`/`head_ref`;
  [071](071_answers-do-not-name-their-tree.md): `index_root`) and is what makes the line checkable
  rather than decorative.
- **Decide the surface**: a `detail_level` value, a per-call flag, or a separate rendering of the
  same payload. Weigh against [061](061_payload-weight.md) — the default answer must not grow.
- **Start with the tools whose answers are attestations, not lists:** `impact` (a modelled zero,
  with `seeds_dropped` / `frontier_skipped_non_resolved`), `find_callers` / `find_references`
  (a counted set at a named tier), `get_index_status` (what revision the answer describes). A list of
  rows is not a claim and does not need signing.
- **The line must degrade honestly.** A signed line for an answer whose tier is `HEURISTIC`, or whose
  index is `behind`, must say so *in the line* — a quotable artifact that hides its own weakness is
  worse than no artifact. This is the same rule 067 and 073 established for the payload.
- **A worked example in the docs**: the exact line the field session should have pasted for
  *"nothing in `src/` depends on these four new paths"*, next to the prose it actually shipped.
- **Do not build a report generator.** One line per answer, quotable by a human or an agent. Anything
  larger belongs to Phase 3.

## Constraints
- **R4** — the line is a rendering of the payload the tool already computed; identical input, identical
  line. No new computation, no LLM phrasing.
- **R3** — if the line becomes part of the tool contract, the conformance suite must pin it.
- **061** — off by default, or free. Measure the token delta.
- **R1.1** — no language branch; the line's vocabulary is the contract's, not PHP's.
- Honesty over quotability: if an answer cannot be stated in one line without losing a caveat, it does
  not get a line. Record which answers those are — that list is itself a finding.

## Acceptance criteria
- `impact`'s modelled zero renders a one-line attestation naming subject, question, answer, and the
  revision it describes; pinned by a test.
- An answer over a `behind` index, or one whose hits are non-`RESOLVED`, renders a line that says so;
  pinned by a test.
- Default payloads are byte-identical to today (R4), with the token delta of the opt-in measured and
  recorded.
- The docs show the field session's real claim beside the line that would have signed it.
- A recorded list of answers deliberately left unsigned, with the caveat each would have lost.

## References
Field interview (round-5 companion, 2026-08-14) §2 (the four claims and the "zero graph payloads"
finding), §7.4 (*"the sharpest question in the instrument … it deserves to be its own section"*),
§8.1 ("reaching the shipped artifact — 10 %"), §8.4 item 6, §8.5. `docs/PLAN.md` §19 —
*Founding-premise benchmark (2026-08-08)*, "what survives is relationships, not locations".
Related: [017](017_impact-engine.md) (the attestation that already exists),
[077](077_index-cannot-name-the-revision-it-describes.md) and
[071](071_answers-do-not-name-their-tree.md) (what makes a line checkable),
[057](057_answer-pagination.md) and [067](067_first-page-not-representative.md) (a count that can be
audited), [061](061_payload-weight.md).
