---
id: 415
slug: conditional-route-handlers
title: "A URL a front controller serves through different handlers by region, flag or parameter cannot be declared, so it cannot be traced"
phase: 2
milestone: Coverage
status: todo
depends_on: [411]
---

## Why this exists

A consumer's survey, 2026-10-25. In a front controller, one URL is served by different handlers
depending on a region switch, a feature flag or a further request parameter:

```php
if ($action === 'x' && FEATURE_ON) { (Region::isA() ? new XA : new XB)->save(); }
```

A route row holds one target (`routes.py:51-56`), so these pages cannot be declared. 549 endpoints of
the form `?action=X` had no handler in the route table, including the main pages questions are asked
about. The consumer can generate the rows itself, but has nowhere to put the conditions.

## Scope

1. A route row may declare several handlers. Each has a free-form `when` label (for example
   `region=A`, `flag=FEATURE_ON`, `param:save=1`) and an optional `source` (`file:line` of the
   dispatching code). Inline, TSV and JSON sources all accept them.
2. Rows with the same key and distinct `when` labels are one conditional route, not a 411 collision.
   The same key with different targets and no `when` is still a collision.
3. `trace_capability` returns one flow per handler, each carrying its `when` and `source`.
   `impact(routes=…)` includes every handler.
4. Conditions are labels for the reader. Nothing evaluates them.
5. Update the user docs for the routes rule.

Out of scope: an extractor that proposes `(param value → handler)` pairs from `if` chains. It is
language-specific, so it belongs in an adapter (R1.1), and would be its own ticket.

## Acceptance criteria

- **AC1:** A fixture route has two handlers, labelled `region=A` and `region=B`. `trace_capability`
  returns two flows, each with its label and source, and `impact` covers both.
- **AC2:** A single-handler route answers exactly as before.
