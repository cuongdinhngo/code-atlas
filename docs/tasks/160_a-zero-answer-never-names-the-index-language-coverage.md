---
id: 160
slug: a-zero-answer-never-names-the-index-language-coverage
title: 'A zero answer never names the index language coverage — a false negative wears a modelled zero''s clothes'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [065, 129, 093, 159]
---

## Why this exists (field retro rounds 8–9, 2026-08-25/26)

Both rounds name this as **the single change worth making** — the one place the tool was *actively
misleading* rather than merely unhelpful, and it landed on the exact question a ticket turned on:

> Round 8 (8-A): `search_symbol("DialogueService")` → `total_count: 1` (a PHP test method) against
> **281 `.js` files** that reference it. `search_symbol("iziToast")` → `no_matches` while
> `public/js/iziToast.min.js` sits unindexed. *"A false negative wearing a modelled zero's clothes."*
>
> Round 9 (9-C): `search_symbol("storeCRM")` → **7 hits, every one `restoreCRM`** (a trigram
> substring), at `reason: "ok"`. `storeCRM` is a JS function. *"The only payload this round I would
> call harmful."*
>
> Round 9 (9-B / a second 065 exception): `include_graph(src/.../ledger_screen_beta.php, imported_by)` →
> a bare `results: []` with **no `reason`**, while the same call on a sibling file returns
> `relationship_not_modelled` + a hint, and the `imports` side reports `unresolved_includes: 19`.
> *"Inconsistent honesty is more dangerous than uniform silence."*

The fact needed already exists one call away — `indexed_suffixes` (task 159) — but is absent from the
payload making the claim.

## Root cause

- **No language reason exists.** `code_atlas/tools/nav_result.py:18-76` (`NAV_REASONS`) has no
  `language_not_indexed`. `relation_reason()` (`nav_result.py:297-303`) collapses a symbol in an
  unindexed language to `no_such_symbol` — **indistinguishable from a typo**. `search_symbol.py:184-187`
  and `find_references.py:167` build their empty reason from that vocabulary, so a zero answer can never
  say *"this index holds one language."*
- **`include_graph` inbound can carry nothing.** The `imports` side always attaches
  `unresolved_includes` (`include_graph.py:112-114,141-148`); the `imported_by` side sets a `reason`
  only when `count_unlinked_includes_mentioning(basename) > 0` (`include_graph.py:71-79`), so on an
  empty inbound answer with no unlinked mentions the `reason` stays `None` and
  `nav_result()` (`nav_result.py:201-202`) ships a bare `results: []` (`include_graph.py:80-91`).

## Scope

- **Every empty / zero answer names the index's language coverage.** Thread the coverage fact from
  159 (indexed suffixes / languages indexed, shared source of truth) into the zero-answer path of
  `search_symbol` and the `find_*` tools. A new `language_not_indexed` reason (or the coverage carried
  beside the existing reason) so that `search_symbol("iziToast") → no_matches` reads *"no PHP symbol;
  this index contains no JavaScript"* instead of *"nothing here."*
- **Make the `include_graph` inbound fallback unconditional** (or surface an inbound unresolved count),
  so `imported_by` never ships a bare `results: []` with no reason. Close the second 065 exception; the
  inbound side must be at least as honest as the `imports` side.
- **Consider the substring-at-`reason: ok` case (9-C).** `search_symbol("storeCRM")` returning 7
  `restoreCRM` hits at `reason: "ok"` is the harmful shape; at minimum, when the subject has no *exact*
  hit and the index holds only some languages, the coverage note must accompany the substring matches.
  Whether to change `reason` itself is a design call — record it.

### Explicitly not in scope

Inferring a subject's language from its bare name (a name alone does not name a language). The fix
states *what the index covers*, not *what language the subject is*.

## Constraints

- **R1.1** — no language branch in the core. The coverage list is data (from 159's source of truth);
  no `if language == …`.
- **R3 / R3.2** — a new `NAV_REASONS` member is tool-payload vocabulary, not contract vocabulary (no
  `contract_version` bump; precedent for `reason` additions is in PLAN §12). Any test touching the
  reason set derives it from the constant, never re-typing members (R6.7).
- **061** — the coverage note attaches on the empty / low-confidence path only, never on a confident
  non-empty answer.
- **R4.2** — deterministic.

## Acceptance criteria

1. `search_symbol` / `find_references` returning empty for a subject whose language is not indexed
   carry a reason or field that names the index's language coverage — pinned by a test on an index
   built with a strict suffix subset, shown to differ from a genuine same-language typo miss.
2. `include_graph(..., "imported_by")` never returns a bare `results: []` with no `reason`; the
   `relationship_not_modelled` fallback (or an inbound unresolved count) is unconditional — pinned by
   a test on the file pair that reproduced 9-B's asymmetry.
3. A confident non-empty answer is byte-identical to today (061).
4. Any new reason member is imported from `NAV_REASONS`; no `contract_version` bump (R3); the R1.1
   grep-gate stays green.
5. Determinism holds (R4.2).

## References

Field retro rounds 8–9, findings **8-A** / **9-C** (language coverage in zero answers) and **9-B**
(the second 065 exception on `include_graph` inbound). `code_atlas/tools/nav_result.py:18-76,201-202,297-303`,
`code_atlas/tools/search_symbol.py:184-187`, `code_atlas/tools/find_references.py:167`,
`code_atlas/tools/include_graph.py:71-79,80-91,112-114,141-148`. Related:
[065](065_empty-answer-cannot-explain-itself.md) (an empty answer must explain itself — this is a new
exception), [129](129_include_graph_imports-is-a-silent-zero-for-a-namespaced-file.md) (the imports-side
silent zero), [093](093_try-instead-is-not-a-callable-tool-name.md). Shares its coverage source of
truth with [159](159_get-index-status-does-not-name-available-but-unconfigured-adapters.md).
