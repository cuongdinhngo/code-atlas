---
id: 065
slug: empty-answer-cannot-explain-itself
title: 'An empty answer cannot say why it is empty — three tools returned 0 for 1, 3348 and 2 real sites'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [033, 054, 056]
---

## Goal
`reason: "no_matches"` on a query the resolver **cannot link** is byte-identical to `no_matches` on a
symbol that genuinely has no references. Field round 3 hit this three times in one session, on
questions whose true answers were **1**, **3,348**, and **2** sites. Give an empty answer a channel to
say *"this relationship is not modelled"*, distinct from *"this relationship is empty"*.

## Evidence (field retro round 3, 2026-08-09, contract v5)
| Query | Payload | Truth |
|---|---|---|
| `find_references` on class `…\ServiceControllerMemberAllergies` | `results: []`, `total_count: 0`, `reason: "no_matches"` | 1 site — `config/legacy_aliases.php:509`, **the root cause of the bug being fixed** |
| `find_references` on class `\Src\System\RegionManager` | same shape | **3,348 sites across 614 files** |
| `include_graph(path, direction="imported_by")` | `results: []`, **`unresolved_includes: 0`** | 2 requirers, both via computed paths (`dirname(__DIR__, 2) . …`, `__DIR__ . '/../../…'`) |

The control proves the tools are **narrow, not broken**: `find_references` on a *method* qname
(`ModelMember::getActiveStatus`) returned 18 correct results in the same session.

Where the behaviour is already known and where it is not:
- `find_references`' docstring states it — *"Bare `IMPORTS` / `CONTAINS` / `REFERENCES` stay
  unlinkable until the resolver grows — they never appear here even though the SQL has no kind
  filter"* (`tools/find_references.py`). **The docstring carries the caveat; the payload does not.**
- `relation_reason()` (`tools/nav_result.py`) can only return `ok` / `no_such_symbol` / `no_matches` —
  it branches on `hit_total` and `symbol_indexed` and has no third input to branch on.
- `NAV_REASONS` has six values, none of which means "not modelled".
- `unresolved_includes` counts *outbound* bare/dynamic includes only —
  `_count_unresolved_imports` is called `if direction in ("imports", "both")`
  (`tools/include_graph.py:84`), so an `imported_by` query always reports `0`. The field is not
  wrong; it is **unanswerable in that direction and still prints a confident zero**.

Why this is the top item and not a nicety: the anchor repo's own `CLAUDE.md` instructs agents that
`find_references` / `impact` are *"required, not grep"* for "who calls this / what breaks if I change
it". An agent obeying that reads `total_count: 0` for `RegionManager` and concludes the project's
central region switch is dead code. The round-3 session escaped only because it routed around the
tools by instinct — it calls the loss **latent, not realised**.

## Scope / Deliverables
- **A new `reason` value for unmodelled relationships.** Add to `NAV_REASONS` something in the shape
  of `relationship_not_modelled`, emitted whenever the query kind is one the resolver cannot link —
  not guessed from an empty result, but decided from the query's own shape.
- **Say what to do instead.** The payload must carry a short, machine-stable hint (which tool or which
  name form *would* answer), not prose an agent has to parse. Keep it one field; R-061 weight rules
  still apply.
- **Decide the trigger honestly.** A class-shaped qname whose reference edges are all unlinked is
  the case in hand, but the rule must be derived from what the resolver links, not from a
  regex on the qname. If that decision cannot be made cheaply at query time, say so and record the
  cheaper approximation chosen.
- **`include_graph` must stop asserting completeness it cannot claim.** Either report inbound
  unresolved edges (an `unresolved_inbound` counter alongside `unresolved_includes`), or omit the
  field entirely for `imported_by` — a printed `0` that is structurally always `0` is worse than
  absent.
- **Every nav tool, not just these two.** Whatever channel is added must be emitted consistently by
  `find_references`, `include_graph`, `impact`, `reachable_from`, `explain_path` and
  `find_implementations`, or the next session learns to trust the wrong subset.

## Constraints
- R1.1 — no language branch; "which kinds does the resolver link" is contract vocabulary, not PHP.
- R3 — if the reason vocabulary is part of the contract surface, the version bump and
  `tests/contract/` update travel in the same change.
- R4 — deterministic: same index + same query ⇒ same reason, every time.
- 061 — do not reintroduce payload weight; this is one field, present only when it means something.
- Do **not** fix the underlying resolver gap here. This ticket makes the gap *legible*; linking
  class-level references is a separate, larger piece of work.

## Acceptance criteria
- `find_references` on a class qname whose reference edges are unlinked returns a reason distinguishable
  from a genuine zero, with a hint naming a route that does work.
- `find_references` on a method qname with real callers is unchanged (the 18-result control still
  returns `reason: "ok"` and 18 rows).
- A symbol that genuinely has zero references still reports the plain empty reason — the new value
  must not swallow the honest case.
- `include_graph(direction="imported_by")` no longer emits a field that is always `0`; whichever way
  it is resolved, a file with unresolvable inbound includes is distinguishable from one with none.
- A conformance test pins each reason value to a query shape, so the vocabulary cannot drift.

## References
Field retro round 3 §3, §4, §9 (`today-i-learned/ai/code-atlas/Retros/2026-08-09_…round3.md` — the
retro is outside this repo; the counts above are the artifact). `code_atlas/tools/nav_result.py`
(`NAV_REASONS`, `relation_reason`); `code_atlas/tools/find_references.py` (docstring carries the
caveat); `code_atlas/tools/include_graph.py:84,111` (`_count_unresolved_imports`, outbound only).
Related: [054](054_bare-name-callers-silent-drop.md) (a silent drop with a count that lied),
[056](056_filter-values-fail-loud.md) (an empty result standing in for an error),
[033](033_nav-reason-codes.md) (the `reason` field this extends).
