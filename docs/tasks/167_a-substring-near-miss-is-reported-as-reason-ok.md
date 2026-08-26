---
id: 167
slug: a-substring-near-miss-is-reported-as-reason-ok
title: 'A substring near-miss is returned at `reason: "ok"` — asking for a symbol that does not exist yields a confident hit on a different one'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [014, 160, 093]
---

## Why this exists (field retro rounds 9 & 10)

160 deliberately deferred this, and round 10 verified on **fixed code** that it still bites:

```
search_symbol("storeCRM")  →  reason: "ok",  total_count: 7,
                              first result: \ModelMember::restoreCRM
```

> Round 9 (**9-C**): *"The only payload this round I would call harmful."*
>
> Round 10 §4: *"I asked for `storeCRM`; I was handed `restoreCRM` labelled `ok`. 9-C is live, and it is
> the single worst payload shape in the tool: **a substring near-miss is indistinguishable from a
> hit.**"*
>
> Round 10 §12.b: *"I asked for a symbol that does not exist and got a confident `ok` for a different
> one."* §15 ranks it ticket 5 of 6, and §14 records it **❌ CONFIRMED LIVE and harmful**.

Two rounds, same verdict, and it compounds the language-coverage gap 159/160 were built to close: in an
index that holds only some of a repo's languages, a JS identifier searched by name should be a **typed
refusal**, not a trigram near-miss on an unrelated PHP method. The absence the agent needs to see is
hidden by a hit it did not ask for.

## Root cause

- `code_atlas/tools/search_symbol.py:195` —
  `reason = REASON_OK if total_count > 0 else REASON_NO_MATCHES`.
  The reason is a pure function of **how many rows came back**, with no notion of **how they matched**.
- `code_atlas/tools/search_symbol.py:90` documents the matching as *"FTS trigram, or a name/qname
  prefix"* — so exact, prefix and substring hits are already distinguishable **at query time** and are
  then flattened into one undifferentiated `ok`.
- Because the reason reads `ok`, 160's `attach_coverage_note` — which fires only on
  `no_matches` / `no_such_symbol` (`code_atlas/tools/coverage.py:34-45`) — **never attaches**. The
  language-coverage note is suppressed by precisely the answer shape that most needs it.

## Scope

Make the match mode visible, so a near-miss cannot pass as a hit.

1. Carry **how each result matched** — an exact/prefix/substring discriminator on the row, or a
   payload-level `matched_on`, or a distinct `reason` (e.g. `substring_match`) when **no** result is an
   exact or prefix match. Design picks one and records the rejected alternatives.
2. When no result matches exactly or by prefix, the answer must be legible as a near-miss, and 160's
   coverage note must be able to ride it (the `storeCRM` case is exactly a language-coverage miss).

### Explicitly not in scope

- Changing the FTS query, the ranking, or dropping substring results. Substring matching is useful; it
  is the **labelling** that is wrong.
- The `find_*` family — a follow-up if the discriminator generalises.

## Constraints

- **R3** — a new `reason` value is nav vocabulary, not contract vocabulary; confirm against
  `contract.py` before choosing that shape. Prefer an additive field if it avoids the question.
- **061** — an answer containing an exact match must be byte-identical to today.
- **Cost** — `search_symbol` is a sweep tool with a batch envelope; the discriminator must not add a
  per-row query.
- **R1.1** — no language branch. (The subject's *language* is deliberately out of scope; 160 already
  settled that the note names the **index's** gap, not the subject's language.)
- **R4.2** — deterministic ordering and labelling.

## Acceptance criteria

1. `search_symbol` on a subject that exists only as a substring of other symbols is distinguishable from
   one that matched exactly — pinned by a test using the `storeCRM` / `restoreCRM` shape (generic
   fixture names, R2).
2. In that case 160's `unconfigured_adapters` note attaches when a coverage gap exists.
3. An answer containing an exact or prefix match is byte-identical to today (061).
4. The sweep/batch envelope carries the same discriminator as the single-subject path (160's AC1e
   lesson: the sweep path is the one that gets missed).
5. No per-row query added; cost measured against the tokens-to-answer gate.
6. Determinism (R4.2); no language branch (R1.1); contract impact confirmed and recorded (R3).

## References

Field retro round 9 finding **9-C**; round 10 §4, §12.b (**deferral tested, still bites**), §14
(confirmed live), §15 ticket 5. `code_atlas/tools/search_symbol.py:90,195`;
`code_atlas/tools/coverage.py:34-45`. Related: [160](160_a-zero-answer-never-names-the-index-language-coverage.md)
(the deferral's origin), [014](014_search-read-outline.md), [093](093_try-instead-is-not-a-callable-tool-name.md).
