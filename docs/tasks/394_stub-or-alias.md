---
id: 394
slug: stub-or-alias
title: 'read_symbol returns an empty-bodied base method or a test-bootstrap stub as the answer, and does not say where the real one is'
phase: 2
milestone: Trust
status: todo
depends_on: [286, 252]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). Four PRs read a
correct body of the wrong code:

- F1 (1 PR): `read_symbol Base::render` returned an empty body. The implementation lives in two
  subclasses, which were found by name.
- F2 (2 PRs): a class is `class_alias`-ed to a stub in the test bootstrap. Neither `read_symbol`
  nor `search_symbol` said so, and the agent found it by reading a test's docblock, or by probing a
  swallowed exception.
- F3 (1 PR): global functions have test-bootstrap copies, so `search_symbol` was ambiguous until
  `path_prefix` was added.

286 names a mirror twin. The same cue is missing for an override and for an alias.

## Scope

1. A `read_symbol` hit whose body is empty or abstract carries `implemented_by`: the overriding
   methods, capped, with paths (read from the inheritance edges the index holds).
2. A `class_alias('Real', 'Alias')` with literal arguments emits an alias relation, and
   `read_symbol` / `search_symbol` on either name names the other, with its path. A literal call in
   a test path is labelled `test_double`.
3. On an ambiguous name where every other candidate lives in a test path, the production row comes
   first, and `ambiguity: "test_copies"` is set.

## Acceptance criteria

- **AC1:** `abstract`-free `Base::m(){}` with two overriding subclasses: `read_symbol Base::m`
  lists both in `implemented_by`.
- **AC2:** `class_alias('StubForm', 'Form')` in `tests/bootstrap.php`: `read_symbol Form` names
  the stub and labels it `test_double`.
- **AC3:** A symbol with no override, alias or test copy is byte-identical.
