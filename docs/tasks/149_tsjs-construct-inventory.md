---
id: 149
slug: tsjs-construct-inventory
title: Name the TS/JS construct inventory before any parsing exists (R6.2)
phase: 2
milestone: M7
status: done
depends_on: [147]
---

## Why this exists

R6.2 is *spec-driven fixtures, not repo-driven*, and for PHP the list is **named** — in the rule text
and again as `R62_CASES` at `tests/contract/test_adapter_conformance.py:18`. For TS/JS no such list
exists. Whoever writes the first TS fixture will therefore pick constructs from whatever repo happens
to be open, which is the thing R2 forbids and the thing R6.2's wording was written to prevent.

Naming the list costs no parsing and no contract decision, so it is the one part of
[019](019_typescript-adapter.md) that can be settled **before** §4.4 is answered — and
[128](128_typescript-adapter-m0-spike.md) needs it, because its AC1 asks for "one module-scoped file
and one namespaced-equivalent module" without saying what either contains.

## Scope

One named inventory, each entry justified by the **ECMAScript / TypeScript specification**, never by a
framework or a repo:

`module-esm` · `module-cjs` · `class-heritage` · `interface-type-alias` · `enum-const-enum` ·
`generics` · `decorators` · `arrow-closure` · `default-export` · `default-export-named` ·
`re-export-barrel` · `namespace-declare` · `jsx` · `syntax-error`

Two entries are load-bearing and must not be dropped as exotic:

- **`namespace-declare`** — TS `namespace` / `declare module` is the *only* JS/TS construct with a
  native container separator, so it is the case that decides whether `MEMBER_SEPARATOR` bends
  (128's question 1). Without it that question has no fixture and cannot be answered.
- **`re-export-barrel`** — a barrel is where a `target_raw` must name the *defining* module rather
  than the re-exporting one, which is where `RESOLVED` is won or lost (CONVENTION §5: adapters emit
  bare edges, the core links them).

**Where it is written matters, and the budget decides it.** `ENGINEERING_RULES.md` has ~200 tokens of
headroom against `tests/test_doc_size_budget.py`, so R6.2 gets **one compact parenthesised list** in
the shape the PHP one already uses — and the per-entry justification (which spec construct, which
contract question it pins) lives in this task file and in 147's registration table. A thirteen-line
table in the rule book would blow the ceiling and would restate what a task file already holds (R7.6).

## Acceptance criteria

1. **AC1.** R6.2 names the TS/JS list beside the PHP one, as one compact list, and
   `ENGINEERING_RULES.md` stays under its budget with the slack guard still passing.
2. **AC2.** Every entry maps, in this file, to the spec construct it covers and to the one contract
   question it pins — a qname shape, an edge kind, or a confidence tier.
3. **AC3.** Each of 128's three §4.4 questions maps to at least one entry; `namespace-declare` and
   `re-export-barrel` are present.
4. **AC4.** Zero fixture files and zero adapter code land in this ticket. The deliverable is the
   named list.

## Not in scope

Writing the fixtures. Any parser choice. `allowJs` breadth and JSDoc, which are 019's.

## References
R2, R6.2, R7.6; PLAN §4.2 (qname convention), §4.4; CONVENTION §3, §5.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->
<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review + challenger waived per run args)
- **Branch:** `docs/149-tsjs-construct-inventory`
- **CHALLENGER:** OFF (--no-challenger; review waived per run args)
- **work_doc_mode:** embed
- **TIER:** full · **SCOPE:** S
- **refine:** skipped — 0 unresolved product-decisions (the 13-name inventory is given in Scope)
- **Note:** 147 relocated `R62_CASES` → `PHP_R62_CASES` in `tests/contract/adapter_registry.py`; the
  ticket's `test_adapter_conformance.py:18` reference is stale-but-resolvable (the named PHP list
  still exists), surfaced not blocking.

## Requirements matrix

| ID | Kind | Requirement | Ph3 | Ph4 | Notes |
|---|---|---|---|---|---|
| G1 | G | Name the TS/JS construct inventory (spec-driven) before any parsing exists | ✅ | waived | R6.2 names the list; deliverable is the list (AC4) |
| R1 | R | One named inventory of 13 entries, each spec-justified, never repo/framework | ✅ | waived | Scope list + inventory table |
| R2 | R | `namespace-declare` and `re-export-barrel` are load-bearing — must not be dropped | ✅ | waived | both present; pin Q1 and Q2 |
| R3 | R | Compact list in the rule book; per-entry justification in this task file (R7.6) | ✅ | waived | one parenthesised list; table here |
| AC1 | AC | R6.2 names the TS/JS list beside PHP's; ENGINEERING_RULES stays under budget | ✅ | waived | 4,066 ≤ 4,200; not-slack holds; budget tests green |
| AC2 | AC | Every entry maps here to its spec construct + the one contract question it pins | ✅ | waived | inventory table (13 rows) |
| AC3 | AC | Each of 128's three §4.4 questions maps to ≥1 entry; namespace-declare + re-export-barrel present | ✅ | waived | Q1/Q2/Q3 coverage line; both present |
| AC4 | AC | Zero fixtures, zero adapter code — the deliverable is the named list | ✅ | waived | diff = ENGINEERING_RULES + task file only |
| C1 | C | Not fixtures, not a parser choice, not allowJs/JSDoc (019's) | ✅ | waived | none in the diff |
| C2 | C | R7.6 — rule book does not restate what this task file holds; R2 spec-not-repo | ✅ | waived | map lives here, not in R6.2 |

**AC-validation:** AC1 measurable (token budget test); AC2/AC3 are the table below; AC4 is the diff.
**Clarifications (j):** 0 — the inventory is given; standing approval on wording/placement.

## Construct inventory — per-entry justification (the deliverable, AC2/AC3)

128's three §4.4 questions: **Q1** does `MEMBER_SEPARATOR` hold (qname shape)? · **Q2** `open_project(root)`
whole-program lifecycle vs two-pass (cross-module resolution)? · **Q3** does adapter #2 force a
`contract_version` bump, and what changes (node/edge vocabulary, tier)?

| entry | ECMAScript/TS spec construct | contract question it pins |
|---|---|---|
| `module-esm` | ES2015 `import` / `export` modules | Q1 module-path-anchored qname; Q2 IMPORTS resolves against the program |
| `module-cjs` | CommonJS `require` / `module.exports` | Q2 a module with no ESM still linked; tier for dynamic `require` (HEURISTIC vs DYNAMIC) |
| `class-heritage` | `class … extends … implements …` | Q3 do existing EXTENDS/IMPLEMENTS edge kinds suffice for a second language? |
| `interface-type-alias` | `interface` / `type X = …` | Q3 node vocabulary — Interface exists; a `type` alias is a new node or a capability |
| `enum-const-enum` | `enum` / `const enum` | Q3 Enum node reuse; `const enum` inlining → is a member reference DYNAMIC/absent? |
| `generics` | type parameters `<T>` | Q1 does the qname/signature carry type params, or are they erased? |
| `decorators` | `@decorator` (TC39 / TS) | Q3 a new edge/attribute kind (mirrors PHP attributes) or ignored? |
| `arrow-closure` | arrow fns / function expressions | Q1 anonymous-member qname suffix (the `{closure@line}` question, second language) |
| `default-export` | `export default …` (anonymous) | Q1 qname of an unnamed export; Q2 how a default import resolves to it |
| `default-export-named` | `export default class Foo {}` (named) | Q2 a named default resolves via ALIASES `::default`→`::Foo` — the React-component shape 019's matrix missed (task 157) |
| `re-export-barrel` | `export * from` / `export { x } from` | Q2 `target_raw` must name the **defining** module — where RESOLVED is won/lost |
| `namespace-declare` | TS `namespace` / `declare module` | Q1 the **only** construct with a native container separator — decides if `MEMBER_SEPARATOR` bends |
| `jsx` | JSX elements (`.tsx`) | Q3 does JSX add node/edge vocabulary or a capability flag, or is it ignored? |
| `syntax-error` | a malformed source file | R5.1 `ok:false` shape (mirrors PHP `syntax-error`); the mandatory error case |

**Inventory count: 14 entries** — this table is the authoritative count (13 at 149's ship +
`default-export-named`, added by task 157). R6.2 names the list and points here rather than restating a
number (R6.7).

**AC3 coverage:** Q1 → module-esm, generics, arrow-closure, default-export, **namespace-declare**;
Q2 → module-esm, module-cjs, default-export, default-export-named, **re-export-barrel**; Q3 → class-heritage,
interface-type-alias, enum-const-enum, decorators, jsx. Both load-bearing entries present.

## Design

**Approach.** Two edits, docs only:
1. `docs/ENGINEERING_RULES.md` R6.2 — add the TS/JS inventory as one compact parenthesised list
   beside the PHP one (same shape), tagged "per-entry map in task 149". Measured projection ~4,075
   tokens ≤ 4,200 budget, ≥ 3,360 not-slack floor.
2. This task file — the per-entry justification table above is the durable deliverable (AC2/AC3).

**Rejected alternatives.**
- *A 13-line table in `ENGINEERING_RULES.md`* — blows the ~200-token ceiling and restates what this
  task file holds (R7.6). The rule book gets the names; the justification lives here.
- *Add a TS entry to 147's `REGISTRY` now* — would need a TS `AdapterCli` + fixtures that do not
  exist, breaking the conformance run; and AC4 forbids adapter code/fixtures. The registry is the
  future home of the executable cases (019/128), not this ticket's.

**Rule-compliance.** R6.2: the TS/JS list is named, spec-justified, not repo-driven (R2). R7.6: the
rule book stays compact; detail lives in this task file. AC4: no code, no fixtures.

**Proving check.** `tests/test_doc_size_budget.py` (ENGINEERING_RULES under budget + not-slack) and
`tests/test_agent_chain_budget.py` (tier-1 sum) both green after the edit.

**Change-list (files):** `docs/ENGINEERING_RULES.md` (R6.2) · `docs/tasks/149_*.md` (this deliverable).
Plus bookkeeping at finalise: BACKLOG, TOKEN_LEDGER, LESSONS.

## Execute — proof

- **AC1 measured:** `docs/ENGINEERING_RULES.md` = 4,066 tokens (budget 4,200, not-slack floor 3,360).
  `tests/test_doc_size_budget.py` + `tests/test_agent_chain_budget.py` → 12 passed.
- **AC2/AC3:** the inventory table above (14 rows) maps each entry to its spec construct and the §4.4
  question it pins; Q1/Q2/Q3 each covered; `namespace-declare` + `re-export-barrel` present.
- **AC4:** diff = `docs/ENGINEERING_RULES.md` (R6.2) + `docs/tasks/149_*.md`. Zero fixtures, zero
  adapter code, no contract change.
- **Delta-green host:** doc-budget tests are platform-independent (pure `estimate_tokens`), green on
  the Windows dev host; full Docker suite run for the standing delta-green claim.
- **Scope sweep:** diff = approved change-list exactly + bookkeeping (BACKLOG, ledger, LESSONS).

## Counted lines — finalise

CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=1 T6=0 | 0 unclassified
RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)
FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)
RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path
PROMOTION: 0 proposed | 0 human-ratified | destinations: none (type-5 stays in lessons_path) | mango files written: 0
LEDGER TOTAL: 0 tokens · top cost driver: none (solo main-loop run; no subagents dispatched)

- One type-5 claim (`149-C1`, a stale cross-ticket file:line reference), confirmed, recurrence 1,
  stays in `LESSONS.md`. No type-2, so nothing for `/mango:promote`.

## Counted lines — design

HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply | 0 unanswered
EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor

## Counted lines — analysis

PREMISE: 2 references checked | 0 missing | 1 ambiguous (surfaced, not blocking)
RECALL: 0 claims surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)
REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes
SECTIONS: 5 found (Why this exists, Scope, Acceptance criteria, Not in scope, References) | 5 decomposed | ROWS: C=2 R=3 G=1 AC=4
CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision
RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R6.2 (change-type) ✅ | R2 (change-type) ✅ | R7.6 (change-type) ✅

## Cost ledger

| phase | dispatch | tokens |
|---|---|---|
| analysis+design | main loop | unmeasured (host does not surface usage; review/challenger waived) |
