---
id: 160
slug: a-zero-answer-never-names-the-index-language-coverage
title: 'A zero answer never names the index language coverage — a false negative wears a modelled zero''s clothes'
phase: 1.5b
milestone: Agent-trust
status: done
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

---
MANGO WORKING DOC (below this line is NOT part of the raw ticket)

## Session status
- Phase: finalise (complete). TIER: full. SCOPE: M. CHALLENGER: ON.
- work_doc_mode: embed (plain local-file ticket).
- Reviewed at: challenger-only (reviewer waived by run args; challenger ON).

## refine
PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)
RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)
REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes

## analysis
CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision
RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §R1.1 (rulebook) ✅, §R3 (rulebook) ✅, §061 (task) ✅, §R4.2 (rulebook) ✅
SECTIONS: 3 found (Scope, Constraints, Acceptance criteria) | 3 decomposed | ROWS: C=4 R=3 G=1 AC=5

## design
`coverage.attach_coverage_note` attaches `unconfigured_adapters` (159's shared source) to an
**indexed, empty, no_matches/no_such_symbol** answer — self-gating and idempotent, so it is safe at
every return point of search_symbol / find_references / find_callers / find_implementations /
find_view_data (single-subject). The batch/sweep envelope gets it via `attach_coverage_gap` when any
swept subject came back empty (AC1e). The note names what the index does NOT cover — never the
subject's own language (out of scope). include_graph inbound: an empty answer is never bare —
`no_matches` for a genuine zero, `relationship_not_modelled` (+hint) when unlinked text mentions the
file (keeps 065's distinction; closes 9-B). No new NAV_REASONS member, no contract bump (R3).

**9-C (substring-at-`reason: ok`) — deferred, recorded.** The `storeCRM`→`restoreCRM` case is a
*non-empty* answer, so attaching the note there changes confident-answer semantics and interacts with
pagination (which page holds the exact hit). It is a "Consider / design call" in the ticket, not a
numbered AC. Deferred as a distinct follow-up; the numbered ACs (empty answers + include_graph) are
landed. `attach_coverage_gap` is the reusable seam a future 9-C fix would call.

EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor
HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (n/a) | 0 unanswered

## execute
No design-invalidated escalation; no stuck-detector trips. AC1 (empty), AC2, AC3, AC4, AC5 met.

## review (challenger-only — reviewer waived)
CHALLENGER: ON. First pass verdict: mostly PASS but flagged **AC1e** — the search_symbol batch/sweep
path (`queries=[...]`) did not carry the note, reproducing 8-A through the sweep API — and a docstring
on `attach_coverage_gap` that claimed a 9-C wiring that did not exist. Both addressed in response:
the batch envelope now attaches the gap (search_symbol.py, pinned by
`test_search_symbol_sweep_names_the_coverage_gap`); the docstring now describes its real callers. All
other ACs it judged MET with path:line. Result after fixes: clean (reviewer only — CHALLENGER: ON).

### Cost-ledger
| phase | dispatch | round | tokens |
|---|---|---|---|
| review | challenger (ticket-blind) | 1 | 104,253 |

main-loop: unmeasured (host surfaces no usage block).

## finalise
Delta-green in Docker (`scripts/docker-test.sh`, linux): pytest 2102 passed / 1 skipped / 0 failed;
`gate.sh` in-container — ruff · mypy · pytest · tokens-to-answer (ratio ≥ 0.63) · R1.1/R2.2/R4.1
grep-gates · php -l · composer validate all PASS; phpstan `[OK]` with dev deps. Docs within budget.

CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified
FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)
RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)
RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (none) | 0 left in lessons_path
PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0
LEDGER TOTAL: 104253 · top cost driver: review/challenger
