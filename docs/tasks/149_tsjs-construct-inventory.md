---
id: 149
slug: tsjs-construct-inventory
title: Name the TS/JS construct inventory before any parsing exists (R6.2)
phase: 2
milestone: M7
status: todo
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
`generics` · `decorators` · `arrow-closure` · `default-export` · `re-export-barrel` ·
`namespace-declare` · `jsx` · `syntax-error`

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
