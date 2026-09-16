---
id: 285
slug: a-class-hit-omits-the-one-fact-that-decides-whether-its-callers-typecheck
title: '`read_symbol` stamps `params` on a callable and `columns` on a Table, but a `Class` hit carries neither its declared `implements`/`extends` nor a route to `find_implementations` — so on a repo of partial ports, "the port took the methods and dropped the interface" is invisible at the one call an agent makes before trusting the class, and shipped as a production `TypeError`'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [242, 248, 158]
---

## Why this exists (field retro — the anchor repo, round 26 §6 / §9, 2026-09-15)

A ported class kept its static helper and lost its `implements` clause. Its consumer's constructor is
typed on the interface, so the call raised a `TypeError` at runtime — behind an early return, and
therefore invisible until an unrelated fix made the path reachable. Every gate was green.

The retro does not blame the tool; it blames the prompt it never wrote:

> *"`read_symbol` on the class would have shown `class ServiceViewFile {` with no `implements`.
> `find_implementations` on the interface — a tool in the roster I did not call once all session —
> would have listed the views and omitted this one. I never asked."*

The asymmetry is what makes this a payload ticket rather than a habit ticket. `read_symbol` already
stamps the adjacent structural fact for two other kinds — `params` on a callable (242) and a paged
`columns` list on a Table (248), each with an honest "not captured" spelling rather than an empty list
(`read_symbol.py:63-77`). A `Class` gets the body and nothing else, although the graph holds
`EXTENDS`/`IMPLEMENTS` as contract vocabulary (`contract.py:100`, `IMPL_KINDS`) and `find_implementations`
already walks them (`find_implementations.py:39-48`).

Round 25 §3 recorded why the adjacent field is worth more than the lookup it replaces: `params`
changed a fix *because it was next to what the session came for*, not because it was faster than
reading the signature. The same argument applies here, on a repo shape this project has indexed twice.

`attach_next_tools` (`nav_result.py:599-607`) is the second half: it is keyed on node kind and a
non-callable kind earns no field by design (158 / 061), so a `Class` read names no next step at all.

## Scope / Deliverables

- **A found `Class` at `standard` carries its declared supertypes** — the `EXTENDS`/`IMPLEMENTS`
  targets stored for that node, resolved qname where linked and the raw declared name where not, so an
  unresolved base is visible rather than dropped.
- **An honest negative, never an empty list.** A class that declares nothing says so; a language whose
  adapter does not emit `IMPL_KINDS` gets the `params_not_captured_by_adapter` treatment (242 / R5.6),
  not a list that reads as "implements nothing".
- **Route the follow-up.** Extend `attach_next_tools` so a `Class`/`Interface` hit names
  `find_implementations`, closing the loop the retro walked past.

## Constraints

- R1.1: keyed on contract node kinds and `IMPL_KINDS`, never on language.
- 061: `minimal` and every other kind stay byte-identical; no field where nothing is declared.
- R5.6: supertypes are stored edges, never re-parsed from the returned source at read time.
- R4.2: same index, same list, same order (declaration order, as `columns` is DDL order).

## Acceptance criteria

- A class declaring an interface and a base class lists both at `standard`; `minimal` omits them.
- A class declaring neither carries no field (061), and this is distinguishable from an adapter that
  does not emit `IMPL_KINDS`.
- A declared supertype the resolver could not link is still named, marked unresolved.
- A `Class` hit's `next_tool_suggestions` names `find_implementations`; a callable's is unchanged.
- A Table and a callable read byte-identically to today.

## References
`code_atlas/tools/read_symbol.py:63-77`, `code_atlas/contract.py:100` (`IMPL_KINDS`),
`code_atlas/tools/find_implementations.py:39-48`, `code_atlas/tools/nav_result.py:209,599-607`,
[242](242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md),
[248](248_a-table-is-addressable-and-its-columns-are-not-readable-from-it.md),
[158](158_routing-suggestions-fire-on-index-state-not-on-the-question.md).
Origin: field retro round 26 §6 / §9, 2026-09-15 — the round's single concrete ask.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 285 — Class hit carries declared supertypes (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** M · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 7 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: (1) field name `supertypes` + `supertypes_not_captured_by_adapter` mirroring params/242; capability `inheritance` on php/ts/python (KNOWN_CAPABILITIES optional). (2) Class+Interface get find_implementations via attach_next_tools — ticket Scope bullet 3. Citations: ticket Scope/AC; 242 pattern; R5.6.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | Class omits implements/extends | stamp supertypes on Class read | D1 | AC1 | ✅ |
| C1 | Constraints | R1.1 kind-keyed | Class/Interface + IMPL_KINDS | D1 | — | ✅ |
| C2 | Constraints | 061 minimal/other kinds | standard-only field; Table/callable unchanged | D1 | AC5 | ✅ |
| C3 | Constraints | R5.6 stored edges | edges_by_source IMPL_KINDS | D1 | AC3 | ✅ |
| C4 | Constraints | R4.2 order | edge id declaration order | D1 | AC1 | ✅ |
| R1 | Scope | declared supertypes | _attach_supertypes | D1 | AC1–3 | ✅ |
| R2 | Scope | honest negative | not_captured vs omit | D1 | AC2 | ✅ |
| R3 | Scope | route find_implementations | attach_next_tools | D2 | AC4 | ✅ |
| AC1 | AC | lists both at standard | proving | D3 | proving | ✅ |
| AC2 | AC | none vs not captured | proving | D3 | proving | ✅ |
| AC3 | AC | unresolved named | proving | D3 | proving | ✅ |
| AC4 | AC | Class nts; callable unchanged | proving | D3 | proving | ✅ |
| AC5 | AC | Table/callable byte-identical | proving | D3 | proving | ✅ |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: params/columns stamped for callables/Tables; Class had body only; attach_next_tools skipped non-callables.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 ✅ · R5.6 ✅ · R4.2 ✅ · R7.6 ✅`

Ran at 49933fb886cf8e3123064f5a21a4e15a8b4d351b

```
$ .venv/bin/python -m pytest tests/test_read_symbol_params.py tests/test_read_symbol_table_columns.py tests/test_routing_suggestion_on_read.py -q --tb=no
.......................                                                  [100%]
23 passed in 1.73s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: `_attach_supertypes` + `inheritance` capability; NEXT_TOOLS_FOR_TYPE; adapter stamps on php/ts/python.
- Rejected: re-parse source for implements (R5.6); always-on empty list (061); rename server fields.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_read_symbol_supertypes.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | supertypes attach + inheritance cap | read_symbol.py, contract.py, adapters | Class/Interface reads | 1/1 |
| D2 | next tools for type kinds | nav_result.py | Class/Interface nts | 1/1 |
| D3 | proving + handshake pins | tests/* | — | 1/1 |

## Phase 3 — Execute

**Branch:** feat/285-class-hit-carries-declared-supertypes
**Axis 1:** read_symbol · nav_result · adapters · contract · tests.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at 49933fb886cf8e3123064f5a21a4e15a8b4d351b

```
$ .venv/bin/python -m pytest tests/test_read_symbol_supertypes.py -q --tb=no
....                                                                     [100%]
4 passed in 0.34s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — CLEAN (12 met / 0 not met / 0 can't tell). agent 5d008c56-1858-4f5d-9c48-704626401c93

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_read_symbol_supertypes.py — 4 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN (.mango/gate-285.log)
PR: https://github.com/cuongdinhngo/code-atlas/pull/379

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
