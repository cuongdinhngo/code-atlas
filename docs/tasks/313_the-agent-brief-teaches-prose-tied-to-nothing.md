---
id: 313
slug: the-agent-brief-teaches-prose-tied-to-nothing
title: "The agent brief's usage rules are hand-authored prose tied to nothing in the shipped surface, so a param or capability lands green while the brief stays silent — kind:/namespace, the Table/Column writer set (278) and the dynamic-SQL refusal (296) are all untaught"
phase: 1.5b
milestone: Adoption
status: done
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

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 313 — agent brief usage completeness gate (working doc)

- **Ticket:** 313 · local
- **Type:** enhancement
- **Repo(s) / Porting:** app
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed · path: docs/tasks/313_the-agent-brief-teaches-prose-tied-to-nothing.md
- **Current phase:** finalise

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions — ticket names the four gaps, the gate shape, and the out-of-scope boundaries.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=3 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | impossible to ship untaught param/capability/refusal | completeness gate + backfill | D1–D2 | AC1–AC3 | ✅ |
| C1 | Constraints | R6.7 routing stays map-sourced | touch USAGE_RULES + gate only | D2 | AC4 | ✅ |
| C2 | Constraints | no new first-call adoption claim | usage rules only | — | — | ✅ |
| C3 | Constraints | R7.6 add not retell | new section; no stale delete | D2 | docs | ✅ |
| C4 | Constraints | gate reads shipped surface | AST params + module constants | D1 | AC2 | ✅ |
| R1 | Scope | completeness gate beside brief tests | tests/test_agent_brief_usage_completeness.py | D1 | AC1–AC2 | ✅ |
| R2 | Scope | backfill four measured gaps | USAGE_RULES + regenerate golden | D2 | AC3 | ✅ |
| R3 | Scope | honest waiver set | PARAM_WAIVERS / REFUSAL_WAIVERS with why | D1 | AC1 | ✅ |
| AC1 | AC | gate passes; delete rule → red naming item | proving | D1 | proving | ✅ |
| AC2 | AC | new param without mention/waiver fails | monkeypatch fixture | D1 | proving | ✅ |
| AC3 | AC | golden teaches all four | greppable golden | D2 | proving | ✅ |
| AC4 | AC | routing drift guards unchanged | existing tests | — | adjacent | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: USAGE_RULES are hand prose with only golden-bytes drift guard — no pin to tool params / capabilities / refusal tokens.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R6.7 (change-type) ✅ · R6.3 (change-type) ✅ · R7.6 (change-type) ✅ · R7.2 (change-type) ✅`

Ran at 96ef956986ecdfc12e99452a860aa4fa6bf5a8c3

```
$ .venv/bin/python -m pytest tests/test_agent_brief_in_indexed_repo.py tests/test_routing_surface.py -q --tb=no
.......                                                                  [100%]
7 passed in 0.69s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: AST-enumerate OCCASIONS tool params; discover writer capability via `_writes_targets`; discover refusal tokens from `reach_shared` + `RESOLUTION_DYNAMIC_SQL`; require brief mention or commented waiver; backfill four USAGE_RULES; regenerate `contrib/agent-brief.md`.
- Rejected: hand-copied param roster (same drift one level up); changing RECOGNITION_MAP/OCCASIONS (out of scope).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_agent_brief_usage_completeness.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | completeness gate + waivers | tests/test_agent_brief_usage_completeness.py | tests | 1/1 |
| D2 | USAGE_RULES backfill + golden | scripts/gen_skill.py · contrib/agent-brief.md | brief | 1/1 |
| D3 | bookkeeping | docs/tasks/313_… · BACKLOG · TOKEN_LEDGER | docs | 1/1 |

## Phase 3 — Execute

**Branch:** feat/313-agent-brief-usage-completeness-gate

**Verification sweep**

Ran at 96ef956986ecdfc12e99452a860aa4fa6bf5a8c3

```
$ .venv/bin/python -m pytest tests/test_agent_brief_usage_completeness.py -q --tb=no
.....                                                                    [100%]
5 passed in 0.51s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — round-1 NOT CLEAN → fix → round-2 CLEAN (19 met / 0 not met / 0 can't-tell)
agent 0c3ef8f5-360b-419d-852a-0a79c58ecf6a

`REVIEW: CLEAN`
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`

Ran at 96ef956986ecdfc12e99452a860aa4fa6bf5a8c3

```
$ .venv/bin/python -m pytest tests/test_agent_brief_usage_completeness.py -q --tb=no
.....                                                                    [100%]
5 passed in 0.58s
```

## Phase 5 — Finalise

Outward: push + PR. Never merge.

## Cost ledger

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
