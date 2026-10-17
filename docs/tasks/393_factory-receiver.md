---
id: 393
slug: factory-receiver
title: 'A call on an object a factory returned, or on an untyped parameter, links to nothing, so find_callers lists only the test'
phase: 2
milestone: Coverage
status: todo
depends_on: [362]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). 362 types a
receiver assigned from `new X()`. The field's next two shapes are still unlinked:

- F1 (1 PR): `find_callers Mailer::createPdfAttachment` returned only a test, because the
  production receiver is `$mail = Builder::buildMail(); $mail->createPdfAttachment(…)`.
  `buildMail()` declares `: Mailer` (or `@return Mailer`). The real call was found with Read.
- F2 (1 PR): `find_callers` missed the callers that receive `$model` as an untyped parameter. The
  only callers of that function pass one class, and the print paths were found with Grep.
- F3 (1 PR): a sweep confirmed callers with `find_callers` plus Grep "to be sure", because the
  answer could not say whether untyped receivers were in play.

## Scope

1. A local assigned from a call whose callee declares a return type (native, or `@return` at
   `HEURISTIC`) takes that type. That covers static factories and `$this->build*()`.
2. Measure F2 before building: count the untyped parameters on the anchor index whose resolved
   callers all pass one class. Infer from call sites only if that count justifies it. Otherwise file
   the count.
3. When an empty or partial answer has unresolved same-name calls on untyped receivers,
   `unresolved_receivers` counts them, so "is the list complete?" has an answer (F3).

## Acceptance criteria

- **AC1:** `$m = Builder::buildMail(); $m->send();` with `buildMail(): Mailer` gives
  `find_callers Mailer::send` one `HEURISTIC` row.
- **AC2:** The same with `@return Mailer` only.
- **AC3:** No existing `RESOLVED` edge changes tier, and an index with no such sites is
  byte-identical.
