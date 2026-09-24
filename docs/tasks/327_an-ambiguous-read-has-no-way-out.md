---
id: 327
slug: an-ambiguous-read-has-no-way-out
title: "read_symbol refuses an ambiguous qname and routes to search_symbol, which returns the same qname — four of five field sessions hit the dead end and sliced the file with sed"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [070, 078, 315, 049]
---

## Why this exists (field retros, 2026-09-23/24 — four batches)

078 made `read_symbol` refuse a qname with several definitions: `reason=subject_ambiguous`,
`ambiguous_definitions` (file + line), no body, `try_instead: search_symbol`
(`read_symbol.py:584-605`). Its re-ask path was *"use `file_outline` / `search_symbol` on a site from
`ambiguous_definitions`"* (078, design table row 5). **That path returns the same qname**, so the
re-ask refuses again. The field has now measured it:

| Batch | Subject shape | Fallback |
|---|---|---|
| FIELD-1621/1615 | a same-named global function in four page files (two regions × two trees) | `sed -n` |
| FIELD-1062/1634 | a table: one `CREATE`, five migration `ALTER`s, one function mentioning it | `grep` |
| FIELD-1426 | a stored procedure: canonical tree + a migration redefinition | `sed` |
| FIELD-1624/1626/1636 | a procedure in a snapshot + two migrations | `sed` |

Every session then did the thing the project rules call the wrong-tool tell. One also found
`line_start` alone refused (`read_symbol.py:137`), and `line_start/line_end` apply inside a resolved
symbol, not to choose between definitions.

**This revisits 078's rejected option 3** (`file=`), rejected for *"largest surface + 049 risk"*.
Both reasons are answerable now: the surface is one tool, not every single-subject tool; and 049's
concern — a second, differently-shaped filter vocabulary — is met by reusing `path_prefix`, which
315 shipped with fixed semantics on `search_symbol` and `find_references`.

## Goal

A caller holding `ambiguous_definitions` can read exactly one of them in one re-ask.

## Scope / Deliverables

1. **`read_symbol(qname, path_prefix=…)`** — filters the definition rows before the ambiguity test;
   one survivor answers with its body, two or more still refuse with the narrowed list.
2. **The refusal routes to itself with the argument named** — `try_instead` names `read_symbol`
   with `path_prefix` (the progress route, R5.4), not `search_symbol`.
3. **070 stands.** This picks a *definition to read*; it adds no per-definition edge scoping.

## Constraints

- **061** — a unique qname, and every call without `path_prefix`, is byte-identical.
- **R6.7** — reuse 315's `path_prefix` validation (`nav_result.py:150`), not a second parser.
- **R1.1** — no language branch; "canonical vs migration" ranking is **not** in scope (it would
  encode a repo's layout, R2.2).
- **R3** — a tool parameter, not contract vocabulary; no `contract_version` bump.

## Acceptance criteria

- **AC1** Fixture: one qname in two files; `path_prefix` naming one returns that body and its site.
- **AC2** A `path_prefix` matching both still refuses, listing both.
- **AC3** A `path_prefix` matching neither answers `no_such_symbol` naming the filter, not a body.
- **AC4** The refusal's `try_instead` names `read_symbol`; regression test for the unique case.
- **AC5** The agent brief teaches the argument in the same change (313's gate).

## Out of scope

- The same selector on `find_callers` / `impact` — do it on a sighting there (R1.2).
- Picking "the latest migration" automatically — a repo convention, not a language fact.

## References
`code_atlas/tools/read_symbol.py:86,137,584-605`; `code_atlas/tools/nav_result.py:150`;
tickets 049, 070, 078 (rejected option 3), 313, 315.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 327 — ambiguous read_symbol path_prefix (working doc)

- **Ticket:** 327 · local
- **Type:** bug / enhancement
- **Repo(s) / Porting:** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed · path: docs/tasks/327_an-ambiguous-read-has-no-way-out.md
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** finalise — next: push branch, open PR

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions — ticket revisits 078 rejected option 3 with 315's path_prefix already shipped.

## Requirements matrix

`SECTIONS: 7 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope · References) | 7 decomposed | ROWS: C=4 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | caller holding ambiguous_definitions can read one in one re-ask | path_prefix filter | D1 | AC1 | ✅ |
| R1 | Scope 1 | read_symbol(qname, path_prefix=…) filters before ambiguity | `_apply_path_prefix` | D1 | AC1–3 | ✅ |
| R2 | Scope 2 | refusal routes to itself with argument named | try_instead=read_symbol + HINT_PATH_PREFIX | D2 | AC4 | ✅ |
| R3 | Scope 3 | 070 stands — no per-definition edge scoping | read only | D1 | review | ✅ |
| C1 | Constraints | 061 unique + no path_prefix byte-identical | default path unchanged | D1 | AC4 unique | ✅ |
| C2 | Constraints | R6.7 reuse 315 validator | require_path_prefix | D1 | review | ✅ |
| C3 | Constraints | R1.1 no language branch | filter on file_path only | D1 | review | ✅ |
| C4 | Constraints | R3 no contract bump | tool param only | D1 | review | ✅ |
| AC1 | AC | path_prefix one file → that body | proving | D1 | proving | ✅ |
| AC2 | AC | path_prefix both → refuse both | proving | D1 | proving | ✅ |
| AC3 | AC | path_prefix neither → no_such_symbol naming filter | path_prefix echo | D1 | proving | ✅ |
| AC4 | AC | try_instead=read_symbol; unique regression | proving + ambiguous test | D2 | proving | ✅ |
| AC5 | AC | agent brief teaches argument (313 gate) | gen_skill + golden | D3 | proving | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause (bug, `logic`): `_refuse_ambiguous` routed to `search_symbol`; re-ask returns same qname → refuse again. Field measured sed/grep fallback.
- Blast radius: read_symbol; nav_result routes; 078 tests; agent brief / 313 gate.

`TRACK: backend — 0/6 touched files under UI paths`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R6.7 (change-type) ✅ require_path_prefix · R1.1 (change-type) ✅ no language branch · R5.4 (change-type) ✅ progress route to self with arg · R7.2 (change-type) ✅ ledger + BACKLOG`

`BASELINE: green`

## Phase 2 — Design

- Approach: add `path_prefix` param; filter rows with 315's under-prefix predicate before multiplicity; empty → no_such_symbol + echo filter; refuse → TRY_INSTEAD_READ_SYMBOL + HINT_PATH_PREFIX; brief teaches both the ambiguous trap and path_prefix on read.
- Rejected: auto-pick "latest migration" (R2.2 / out of scope); file= new filter vocabulary (049 — ticket chose path_prefix reuse).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | path_prefix filter + miss | code_atlas/tools/read_symbol.py | 078 tests | R1 R3 C* AC1–3 | 1/1 |
| D2 | READ_SYMBOL route + hint | code_atlas/tools/nav_result.py | 093 invariant | R2 AC4 | 1/1 |
| D3 | brief + golden | scripts/gen_skill.py · contrib/agent-brief.md | 313 gate | AC5 | 1/1 |
| D4 | proving + 078 assert | tests/test_read_symbol_path_prefix.py · test_ambiguous_qname.py | — | AC* | 1/1 |
| D5 | bookkeeping | docs/tasks/327_… · BACKLOG · TOKEN_LEDGER | — | R7.2 | 1/1 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | pytest | authored | ✅ |
| AC2 | integration | pytest | authored | ✅ |
| AC3 | integration | pytest | authored | ✅ |
| AC4 | integration | pytest | authored | ✅ |
| AC5 | integration | pytest completeness | golden | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_read_symbol_path_prefix.py -q`

`SCOPE: S`

## Phase 3 — Execute

**Branch:** feat/327-ambiguous-read-path-prefix

Ran at d8de3409a679fa4e7e17a6372482806feafc79f2

```
$ .venv/bin/python -m pytest tests/test_read_symbol_path_prefix.py tests/test_ambiguous_qname.py::test_read_symbol_refuses_body_when_ambiguous tests/test_ambiguous_qname.py::test_unique_qname_payload_omits_the_ambiguity_key tests/test_agent_brief_usage_completeness.py -q
11 passed in 1.27s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: OFF (--no-reviewer)
CHALLENGER: ON — round-1 CLEAN, 12 met / 0 not met / 0 can't tell.

Verdict: `clean (challenger only — REVIEWER: OFF)`

Ran at d8de3409a679fa4e7e17a6372482806feafc79f2

```
$ .venv/bin/python -m pytest tests/test_read_symbol_path_prefix.py tests/test_ambiguous_qname.py::test_read_symbol_refuses_body_when_ambiguous tests/test_ambiguous_qname.py::test_unique_qname_payload_omits_the_ambiguity_key tests/test_agent_brief_usage_completeness.py -q
11 passed in 1.27s
```

`REVIEW: CLEAN`
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`

`Reviewed at d8de3409a679fa4e7e17a6372482806feafc79f2` · reviewed files: code_atlas/tools/read_symbol.py, code_atlas/tools/nav_result.py, tests/test_read_symbol_path_prefix.py, tests/test_ambiguous_qname.py, scripts/gen_skill.py, contrib/agent-brief.md

## Phase 5 — Finalise

Outward: push feat/327-ambiguous-read-path-prefix, open PR. Never merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| review | challenger | 1 | unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: unmeasured (subagent dispatch only; host surfaces no usage) · top cost driver: review/challenger round 1`
