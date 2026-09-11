---
id: 252
slug: a-class-reference-question-costs-n-plus-one-calls
title: 'A class-level `find_references` returns zero hits and routes to a two-step costing one `search_symbol` plus one `find_callers` per member, so the commonest first question about a class — what touches it at all — is the most expensive answer on the surface'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [245, 168, 065]
---

## Why this exists (field retro — anchor-repo, 2026-09-11, round 18)

The consuming agent's first move on the photo bug was the obvious one — ask what references
`MemberPhotoResolver`. Its account:

> `find_references` on the `MemberPhotoResolver` **class** returned `results: []` with
> `reason: relationship_not_modelled` and `try_instead: search_symbol` + a hint to re-ask with a
> `Class::method` qname. […] It's the one place a naive expectation ("find everything that references
> this class") fails silently-ish — but the tool tells you why and what to do, so it cost one
> redirected call, not a wrong conclusion.

The retro grades this mildly and the grade is too kind, because it prices only the redirect. 065's
rule — a refusal with no route is a trap — is satisfied; 093's stronger rule, that **the route must
make progress**, is satisfied only in the sense that the reader ends up somewhere. What the route
actually costs is one `search_symbol` to enumerate the members, then one `find_callers` per member:
for `MemberPhotoResolver` (`browserSrc`, `embeddedSrc`, `resolve`, `storedValue`) that is five
calls, and the reader must then union four payloads by hand and decide what the union means.

The agent paid it and got the right answer. The finding is the price, not the outcome: the question
asked most often first about a class is the only navigation question on the surface whose cost scales
with the subject's member count.

## Root cause

`find_references` answers a single relation — resolved edges whose `target_qname` is the subject.
When that set is empty and unlinked `REFERENCES`/`IMPORTS` exist for the bare name, it correctly
declines to call the zero genuine and hands over a route
(`code_atlas/tools/find_references.py:223-233`):

```python
if unlinked > 0:
    reason = REASON_RELATIONSHIP_NOT_MODELLED
    try_instead = TRY_INSTEAD_SEARCH_SYMBOL
    try_instead_hint = TRY_INSTEAD_HINT_METHOD_QNAME
```

Every part of that is right under the rules it was built to. What is missing is that the tool already
sits on the data the reader is about to assemble: the class's members are `CONTAINS` children, and
each member's inbound `CALLS`/`NEW` edges are exactly what the `n` follow-up calls will fetch. The
union is one query's distance away and is instead sold as `n + 1` calls of the reader's own work.

## Scope

A class-level answer that is a **union over the subject's own members**, computed in the call the
reader already made.

Shape decisions left to phase 2 — the ticket does not bind one:

- **Whose members.** Declared members only, or inherited too. Declared-only is the working assumption:
  it is derivable without a resolution pass and it matches what the two-step would have produced.
- **What the hit says.** Each row must name the member it arrived through, or the union is a list of
  call sites that appear to reference a class that nothing references.
- **What the answer is called.** It is not a `REFERENCES` edge set and must not wear that name. The
  relation "a caller of a member of this class" is a derived aggregate, and the payload says so.

## Constraints

- **R5.6 — never dress a derivation as a modelled edge.** `reason` stays distinct from `ok`; the union
  cannot claim the class-reference relation the graph does not hold. This is the same discipline 249
  used for `separator_normalised`.
- **Tiering survives the union.** Each hit keeps its own tier; the answer's weakest tier governs any
  claim line, exactly as `find_callers` does today.
- **24 tools stay 24** (`tests/test_documented_tool_count.py`) — this lands on `find_references`, not
  as a new tool.
- **R4.2 / R1.1** — deterministic union order; keyed by contract kind, never by language.
- **Bounded.** A class with hundreds of members must not fan out unboundedly; the answer pages like
  every other navigation answer (057) and says when it capped.

## Acceptance criteria

- **AC1** A class subject with unlinked references and called members returns the union **in one
  call**, each hit naming the member it came through and carrying its own tier.
- **AC2** The payload's `reason` distinguishes the union from a modelled class-reference answer; no
  reader can mistake it for `ok`.
- **AC3** A class whose members genuinely have no callers still returns an honest zero, and that zero
  is distinguishable from today's `relationship_not_modelled`.
- **AC4** The 065/093 route survives wherever the union is not available, so no answer loses its
  route (the regression this must not cause).
- **AC5** Every other tool's payload is byte-identical (022 AC3).

## References

- `code_atlas/tools/find_references.py:223-233` — the decline and the two-step route.
- `code_atlas/tools/nav_result.py` — `REASON_RELATIONSHIP_NOT_MODELLED`, `TRY_INSTEAD_SEARCH_SYMBOL`,
  `TRY_INSTEAD_HINT_METHOD_QNAME`.
- [065](065_empty-answer-cannot-explain-itself.md) / [093](093_try-instead-is-not-a-callable-tool-name.md)
  — the route rules this keeps while removing the reason to use them.
- [245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md) /
  [249](249_a-miss-whose-only-defect-is-the-separator-spelling-gets-no-route.md) — the precedent for
  answering a near-miss in the call that missed, rather than routing the reader to re-ask.
