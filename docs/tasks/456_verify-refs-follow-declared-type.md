---
id: 456
slug: verify-refs-follow-declared-type
title: "verify_refs follows a dotted chain through a field's or property's declared type"
phase: 2
milestone: "Field gaps — tiny-studio"
status: todo
depends_on: [443]
---

## Why this exists

A field report from a second consumer repo (tiny-studio, Python + TypeScript, 406 files; full
`--format jsonl` export on 2026-11-27, 1,610 rows, 73 actionable). Of the 73 actionable rows, 70 are
`gone` / `missing_on_live_container`, and none of them is real. The largest group that is
clearly a bug: the doc names `a.b.c`, `a.b` resolves to a **field or property**, and `c` is a member
of that field's **declared type**. `_member` only looks at the field itself and its ancestors, so the
row comes out `gone`.

| Doc ref | Container matched | Declared type | Member that exists |
|---|---|---|---|
| `Timeline.theme.vars` | `ir.Timeline::theme` | `Theme` | `Theme.vars` (`studio/core/ir.py:348`) |
| `diagram.nodes`, `diagram.modes` | `ir.Article::diagram` | `Diagram \| None` | `Diagram.nodes`, `Diagram.modes` (`ir.py:147,149`) |
| `caption_style.y` | `recipes.Recipe::caption_style` | `CaptionStyle` | `CaptionStyle.y` (`studio/core/recipes.py:69`) |
| `ctx.cancelled` | `pipeline.Pipeline::ctx` (a `@property`) | returns `StepContext` | `StepContext.cancelled` (`core/ports.py:39`) |
| `error.message` | `api.errors.ErrorResponse::error` | `ErrorBody` | `ErrorBody.message` (`api/errors.py:29`) |

Each one is a false `gone` on a doc that is true. A user who trusts `actionable` edits correct docs,
and a user who sees the noise stops trusting the tool.

## Scope

1. When the container is a field or attribute with a declared type annotation, or a property or
   method with a return annotation, resolve the next segment on that type. Take `X | None`,
   `Optional[X]` and a single-class union apart; resolve the type's name through the same matcher
   the container used.
2. Follow every segment the same way (`a.b.c.d`), and stop at the first one with no type.
3. If the type resolves and declares the member → `ok` (reason `via_declared_type`, with the site).
   If the type resolves but does not declare it → apply the current `_member` rules to that type.
   If there is no type, or it is not indexed (`dict`, `Any`, an external class) → `unknown`
   (`untyped_container`), never `gone`.
4. Language-free where the adapters emit a type. Python and TypeScript fields and properties are
   enough for the fixture. Say which adapters emit nothing.

## Acceptance

1. Fixtures (`tests/test_verify_refs_declared_type.py`): field → class → member `ok`; `X | None`
   `ok`; property return type `ok`; a member missing on the declared type keeps today's verdicts;
   a `dict`-typed field → `unknown`, not actionable.
2. Re-run the tiny-studio export (or a scratch copy). The five refs above (8 rows) are no longer
   actionable. Report the actionable count before and after.
3. The anchor's instruction `gone` count does not rise. Report it.
