---
id: 078
slug: ambiguous-payload-still-picks-one-definition
title: '`ambiguous_definitions` warns about two declarations while `source` silently ships one of them'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [070, 043, 049]
---

## Goal
[070](070_ambiguous-qname-no-scoping.md) shipped `ambiguous_definitions` so a non-unique qname warns
instead of pretending to be one symbol, and round 4 verified the field: present, complete, and
independently confirmed by `search_symbol`. But the same payload's `file`, `line_start`, `line_end`
and `source` are all taken from **exactly one** of the definitions. The *field* picks no winner; the
*payload* does. An agent that reads `source` and does not read `ambiguous_definitions` receives one
region's code with no signal that it chose.

## Evidence (field retro round 4, 2026-08-10, probes P5/P6)
- `read_symbol` on a class declared in two regional legacy trees, verbatim (paths shortened):
  ```json
  "file":"legacy/<regionA>/…/EnumFilter.php","line_start":7,"line_end":12,
  "ambiguous_definitions":[{"file":"legacy/<regionA>/…/EnumFilter.php","line":7,"kind":"Class"},
                           {"file":"legacy/<regionB>/…/EnumFilter.php","line":7,"kind":"Class"}]
  ```
  `search_symbol` independently listed the same two declarations (4 hits, 2 distinct files).
- The evaluator's verdict: **FIXED (verified), with a caveat worth a ticket** — and the caveat is the
  ticket: *"An agent that reads `source` and ignores `ambiguous_definitions` silently gets one
  region's code — in this repo, where the whole project is a two-region merge, that is the exact class
  of mistake this ticket exists to prevent."*
- The anchor repo is the demonstration, not the reason: two regional copies of one legacy tree are a
  general shape (vendored forks, `v1`/`v2` trees, monorepo copies), and 043 already established that
  `UNIQUE(qualified_name, file_path)` legitimately keeps one node per declaration.
- Binding is load-order dependent, so the chosen definition is not "the right one" in any sense the
  index can defend — 070 says exactly this and then ships a body anyway.

## The choice this ticket must make
Three defensible designs; pick one, in writing, with the cost stated:
1. **Refuse the body when the subject is ambiguous** — return the definition list and no `source`,
   forcing a disambiguated re-ask (by file, or by the fully-scoped subject). Safest, one extra
   round-trip, and it makes the warning unignorable.
2. **Answer, but mark the answer** — keep `source`, add a field naming *which* definition it came from
   and that others exist. Cheapest, and it still relies on the agent reading a second field.
3. **Accept a disambiguator argument** (`file=…`) and refuse only when the subject stays ambiguous.
   Most useful, largest surface: a new parameter on every single-subject tool.

070 ruled out per-definition *scoping* on the edge model; that ruling is about edges, and it does not
decide what a *body-returning* tool should do. Say so explicitly so the two tickets do not appear to
contradict each other.

## Scope / Deliverables
- **One decision, applied to every tool that returns a body or a single site** — `read_symbol` first,
  then `file_outline`'s symbol path, `explain_path`, `impact`, and the `find_*` subjects.
- **Make the ambiguity impossible to miss** for whichever design is chosen: either no body, or a field
  on the same nesting level as `source` that names the chosen site.
- **Keep the unique case byte-identical** (R4 / 061) — a unique qname pays nothing.
- **State the interaction with 049's call-site selectivity** — if a disambiguator argument is added,
  it must not become a second, differently-shaped filter vocabulary.
- **Test the two-region shape as a fixture**, not against the anchor repo: two files, same qname,
  different bodies (R2 — the fixture encodes the shape, not a repo).

## Constraints
- R2 — no repo, region, or framework name enters code or fixtures.
- R3 — a new field or parameter is contract vocabulary: bump and extend conformance.
- R4 — the chosen definition (if any) must be deterministic, and the ticket must say what determines
  it; "whatever SQLite returned first" is not an answer an agent can reason about.
- 061 — nothing added to the unambiguous payload.

## Acceptance criteria
- For an ambiguous qname, no tool returns a body without the payload naming which declaration it came
  from — proven by a test on a two-declaration fixture.
- The unambiguous payload is unchanged, asserted byte-for-byte.
- `ambiguous_definitions` and the body-selection rule are documented together, with the load-order
  caveat stated where an agent will read it (tool description, not only the plan).
- 070 is updated with a pointer, so its "never picks a winner" claim is scoped to the field it
  describes.

## References
Field retro round 4 §A.6 (verdict + caveat), probes P5/P6, §8 row 3 (the win this rides on).
Related: [070](070_ambiguous-qname-no-scoping.md) (the warning field, and its edge-model ruling),
[043](043_duplicate-decl-resilience.md) (why two nodes per qname are legitimate),
[049](049_call-site-argument-selectivity.md) (the existing selectivity vocabulary),
[046](046_resolver-qname-candidate-dedupe.md) (duplicate edges, already fixed at the cause).
