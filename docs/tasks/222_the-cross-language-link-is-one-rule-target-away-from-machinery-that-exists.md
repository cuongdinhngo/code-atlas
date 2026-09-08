---
id: 222
slug: the-cross-language-link-is-one-rule-target-away-from-machinery-that-exists
title: 'Six of the field''s structural misses are one defect — the identifier is a string, not a symbol — and `enrichment.py` already does the whole extraction for `view_data`: find every call to a named setter, pull the Nth string literal, emit a HEURISTIC edge. Only the target is hardcoded to `viewdata:<key>`'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [221, 063, 062, 040]
---

## Why this exists

Field round 14 listed the question types to keep code-atlas out of, then noticed they were one thing:

> Dispatch tables · string-keyed routing (`querySP('name')`) · stored-procedure callers · PHP↔SQL
> crossings · SELECT-list order · dead-file proof. **All six are "the identifier is a string, not a
> symbol" — one carve-out, six faces.**

[221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) makes the resulting zeros
honest. This one makes some of them non-zero.

**The machinery already exists and is 90 % of the work.** `view_data` rules (040/062/063) run exactly
the chain a string-keyed call needs:

1. `_calls_for_setter` (`enrichment.py:204`) → `store.calls_by_target_raw("querySP")` — every CALLS
   edge with that exact `target_raw`, off `idx_edges_raw`, no scan cap; plus the bare `::method` arm.
2. `_keys_for_rule` (`enrichment.py:218`) → checks the Nth argument is a string literal (`args`
   category) and extracts it with a one-line regex, or reads `arg_keys` for an array literal.
3. Emit a **HEURISTIC** edge — applied after parse, before `resolve_edges`, on a synthetic bookmark
   path with no `files` row (068), `rule: true` on nav hits.

**Step 3 is the only thing pinned.** The target is built as `viewdata:<key>`. Parameterise it —
`"dbo.{key}"` — and PHP `querySP('getUnplannedChange')` becomes a CALLS edge onto the T-SQL
`Function` node the resolver already links, which is the node 214 proved resolves correctly from the
SQL side.

**Why this is the right home for the knowledge, not the adapter.** `querySP` is a repo's function
name. R2 forbids it in `adapters/`, and R1.1 forbids a language branch in the core. Indirection rules
are the seam that already exists for exactly this: repo-relative JSON **outside `adapters/`** (R2.2),
applied generically, off by default, HEURISTIC tier. PLAN §978 made the same argument for the
data-bag case — *"neither end is a symbol the PHP language server binds, so Serena-class tools are as
blind as today's graph. This is unclaimed ground, not an LSP race."* A string-keyed dispatch is the
same shape.

**Why the existing `calls` rule is not the answer.** It takes `(source qname, target qname, line)`
triples (`enrichment.py:370-375`) — one hand-written entry per call site. Against 452 procs it is an
escape hatch, not a mechanism. The difference between the two rule kinds is exactly the difference
between listing edges and deriving them (R6.7).

## Scope

**Blocked on [231](231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md) for Python:** the cross-language rule needs `args` capture from the calling language; without it every `key_from` mode bottoms out empty.

1. **A rule entry kind that emits `CALLS` from an extracted string key**, reusing `_calls_for_setter`
   and `_keys_for_rule` unchanged. Shape, following `view_data`'s validated schema
   (`enrichment.py:376-390`): `{setter, key_arg, key_from, target_template}`.
2. **`view_data` semantics stay untouched.** New entry kind beside it, not a widening of it — no
   `PROVIDES_VIEW_DATA` behaviour change, no contract bump (`CALLS` and `HEURISTIC` are both existing
   vocabulary; R3.1's trigger does not fire).
3. **Template substitution is one named placeholder, no expression language.** `{key}` and nothing
   else, validated at load time, failing loud before parse like every other rule error (R5.3).
4. **Fail loud on a template that resolves to nothing.** A rule producing only unresolvable targets
   is a misconfigured rule; it must be visible in `BuildReport`, not a silent zero — the failure mode
   this whole pair of tickets exists to eliminate.

**Not in scope:** discovering the mapping automatically (that needs literal *values* in the contract,
which `args` deliberately excludes — *"the category, never the value"*, `contract.py:147`, refused
already at 063 and 152); SELECT-list order, which is a T-SQL adapter capability and its own ticket;
routing/dispatch semantics, which the field correctly assigns to grep.

## Acceptance criteria

- **AC1** With a rule configured, `find_callers` on a fixture proc returns the cross-language call
  sites, tier `HEURISTIC`, `rule: true`. **R6.5:** the same fixture without the rule returns the
  221 answer, and that is the before-state the test pins.
- **AC2** With no rule configured the graph is **byte-identical** — the standing property of
  `CA_INDIRECTION_RULES` (R4.2), and the reason this feature costs a non-user nothing.
- **AC3** `view_data` output is unchanged, pinned by the existing 062/063 tests passing untouched.
- **AC4** A rule whose `target_template` resolves no targets reports that in `BuildReport`; a build
  with such a rule does not silently succeed.
- **AC5** The conformance suite and `test_sql_tier2_vocabulary_is_opt_in.py` still pass: a repo with
  no SQL adapter sees identical rows.

## Exclusions

- **E1 — measurement precondition, and it is not in this repo.** The consumer corpus declares **328
  of 452 procs twice**, because an 8.3 MB `V0.1__baseline_schema.sql` full-schema dump is not in
  its `.codeatlasignore`. Until that one line lands there, every emitted edge hits
  `ambiguous_definitions` and the AC1 measurement reads empty — **a false negative that would be
  blamed on this ticket.** Fix the consumer's ignore file *first*, or measure on the fixture only and
  say which.
- **E2** Four of the six faces are in reach here (string-keyed routing, proc callers, PHP↔SQL
  crossings, dead-file proof once literal-named targets link). SELECT-list order and dispatch-table
  semantics are not — do not claim them.
