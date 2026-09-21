---
id: 313
slug: the-agent-brief-teaches-prose-tied-to-nothing
title: "The agent brief's usage rules are hand-authored prose tied to nothing in the shipped surface, so a param or capability lands green while the brief stays silent — kind:/namespace, the Table/Column writer set (278) and the dynamic-SQL refusal (296) are all untaught"
phase: 1.5b
milestone: Adoption
status: todo
depends_on: [266, 270, 278, 296]
---

## Why this exists (field-retro batch 2026-09-20/21, four rounds)

Four field retros on `anchor-repo` show the same shape: the capability the session needed was
**shipped and correct**, and the agent never reached for it — it asked "who calls this method?"
instead of `find_references` on the Column that would name the writers (the 278 case), eyeballed a
645-row result instead of a `kind:` filter that already exists, and read a dynamic-SQL miss as
absence. The most recent retro is the tell in the other direction: the `qname`-not-`symbol` lesson
**transferred** and cost zero calls that session — *because it is written in the brief*. What is in
the brief transfers; what is not, the agent re-derives or gets wrong.

The brief has two halves with very different drift protection. The routing lines are read live from
`RECOGNITION_MAP` and are structurally pinned (`scripts/gen_skill.py:289-315`; drift-guarded
`tests/test_agent_brief_in_indexed_repo.py:32`, `tests/test_routing_surface.py`). The **usage rules —
the substantive how-to-use-it lessons — are hand-authored prose** (`scripts/gen_skill.py:243-287`,
rendered `contrib/agent-brief.md:42-65`) **tied to nothing in the tool surface.** The only guard is
golden-bytes == generator output; no test asserts the rules mention any given tool, param, or
capability. So a new param (`kind`/`namespace`, `search_symbol.py:97-100`), a new capability (the
Table/Column writer set via `find_references`, task 278 done, `find_references.py:227-230`), or a new
refusal (`dynamic_sql` stamp, task 296 done, `tools/find_orphans.py:82-95`) ships green while the
brief stays silent. **The current gaps are that lag made concrete.**

This is Mechanism 3 (correct use once called), **not** an adoption/first-call claim: 081/097/099 and
300 already established that description and routing text have a proven ceiling and cannot *create*
the decision to call. This ticket does not re-litigate that. It closes the drift that lets the one
channel demonstrably shown to transfer (the brief) fall out of step with what shipped.

## Goal

Make it impossible to ship a routing tool's param, capability flag, or refusal status without the
agent brief either teaching it or waiving it out loud — and backfill the four gaps the retros hit.

## Scope / Deliverables

1. **A completeness gate** (a test beside `tests/test_agent_brief_in_indexed_repo.py`) that
   enumerates, for the routing tools the brief already names, their exposed params (from the tool
   signatures / `contract.NODE_KINDS`), advertised capability flags, and refusal `reason` codes, and
   asserts each is either mentioned in the rendered brief (`contrib/agent-brief.md`) or listed in an
   explicit, commented waiver set. A new one appearing untaught and unwaived fails red.
2. **Backfill the four measured gaps** in `USAGE_RULES` (`scripts/gen_skill.py:243-287`), regenerate
   the golden (`contrib/agent-brief.md`): (a) `kind:`/`namespace` filters exist and when to reach for
   them instead of scanning a large result set; (b) a Table/Column subject to `find_references`
   returns its **writers** (278) — the "what writes this column" question; (c) a dynamic-SQL /
   `EXEC`-created object is not a symbol and reads as absence — grep it, and `find_orphans` will say
   `resolution_unmodelled` (296); (d) `find_orphans` and its lack of a path scope.
3. **Keep the waiver set honest** — a waiver names why a param is deliberately not taught, so the gate
   is a decision point, not a rubber stamp.

## Constraints

- R6.7: the routing lines stay single-sourced from `RECOGNITION_MAP`; this ticket touches the
  usage-rules half and its gate, not the map.
- No new claim that this raises first-call adoption — that ceiling is 081/097/099/300's, not
  reopened here (R6.3: do not restate a decided question as if new).
- R7.6: the backfilled rules replace nothing (the brief has no stale line on these) — added, not
  retold; keep within `tests/test_doc_size_budget.py`.
- The gate reads the shipped surface, never a hand-copied list of it — a copy is the same drift one
  level up.

## Acceptance criteria

- **AC1** With the four gaps backfilled, the new gate passes; deleting any one backfilled rule (or
  its waiver) turns the gate red, naming the untaught param/capability/reason.
- **AC2** Adding a new `search_symbol` param in a fixture (or a new refusal reason) with no brief
  mention and no waiver fails the gate — exhibited by a test that introduces one.
- **AC3** The regenerated `contrib/agent-brief.md` teaches all four: the `kind:`/`namespace` filters,
  `find_references` on a Column/Table for writers, dynamic-SQL→grep + `resolution_unmodelled`, and
  `find_orphans` (no path scope) — each greppable in the golden.
- **AC4** The routing-line drift guards and R6.7 single-source tests still pass unchanged.

## Out of scope

- Re-writing tool descriptions or the `instructions` string to chase adoption (proven ceiling).
- Auto-rewriting the per-anchor-repo copies — those are re-emitted by `--write-agent-brief` and are a
  separate operational step (270); this ticket fixes the golden and its gate.
- Any change to `RECOGNITION_MAP` or the occasion set.

## References
`scripts/gen_skill.py:243-287` (USAGE_RULES), `:289-315` (render), `contrib/agent-brief.md:42-65`,
`tests/test_agent_brief_in_indexed_repo.py:32`, `code_atlas/tools/search_symbol.py:97-100`,
`code_atlas/tools/find_references.py:227-230`, `code_atlas/tools/find_orphans.py:41-46`,
[266](266_the-artifact-that-would-make-an-agent-ask-is-in-our-repo-not-theirs.md),
[270](270_the-brief-is-announced-nowhere-and-loaded-by-nobody.md),
[278](278_the-writer-set-is-computed-for-one-check-and-addressable-from-nothing.md),
[296](296_the-sql-adapter-names-the-dynamic-procs-and-stamps-nothing.md),
[081](081_routing-prompts-are-not-in-the-agents-surface.md),
[097](097_recognition-probe-measures-names-not-recall.md), ENGINEERING_RULES R6.3, R6.7, R7.6.
