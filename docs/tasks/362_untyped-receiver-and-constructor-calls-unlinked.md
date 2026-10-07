---
id: 362
slug: untyped-receiver-and-constructor-calls-unlinked
title: 'A call on a variable assigned from new X() in a view, or a constructor call, links to nothing, so find_callers answers relation_unmodelled'
phase: 2
milestone: Coverage
status: todo
depends_on: [258, 336]
---

## Why this exists

This comes from the anchor project's field retro (2026-10-02 → 10-06). In each case below,
`find_callers` returned an empty answer with `relation_unmodelled_for_language`, and the callers
had to come from Grep.

- F1 (1 PR): `getStartDate` is called on `$editor`, which an included view assigns with
  `new X(...)`. 14 view and report call sites were invisible.
- F2 (1 PR): `find_callers` on `Widget::__construct`. Each `new Widget(` site is a `NEW` edge to
  the class, not a caller of the constructor, so `arg_is` could not narrow the call sites by their
  `$type` literal.
- F3 (2 PRs): one regional copy's `Widget::validate`, called via `$this->` in its own class, is
  unlinked, while its twin in the other regional tree resolves.
- F4 (1 PR): `ReportModel::heading` returned an empty answer with `authoritative: false` and no
  candidates.

## Scope

1. Infer local types for `$x = new X(...)` at file or top-level scope (an included view), so that
   `$x->m()` resolves at `HEURISTIC`.
2. `find_callers` on `X::__construct` reads the `NEW` edges onto `X` as its callers, with their
   argument shapes, so `arg_position` and `arg_is` apply.
3. Before changing the resolver, measure why a same-class `$this->m()` resolves for one twin and
   not the other (F3). Then fix the cause, or file it.
4. Where the answer is still empty, the 258 proximity expansion lists the unlinked same-name sites
   instead of a bare zero.

## Acceptance criteria

- **AC1:** In a fixture view, `$o = new Foo(); $o->bar();` gives `find_callers Foo::bar` one
  `HEURISTIC` row.
- **AC2:** `find_callers Foo::__construct` returns each `new Foo(...)` site, and `arg_is` can
  filter them.
- **AC3:** A fixture reproduces the F3 asymmetry, and the asymmetry is either resolved or
  documented with its cause.
- **AC4:** No existing `RESOLVED` edge changes tier.
