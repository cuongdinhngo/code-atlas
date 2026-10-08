---
id: 368
slug: python-module-scope-receiver
title: 'A Python call on a module-level variable built by Foo() is unqualified, though the same call in a function resolves'
phase: 2
milestone: Coverage
status: todo
depends_on: [227, 362]
---

## Why this exists

362's F1 taught the PHP type table to bind `$x = new X()` at a file's top level, so `$x->m()` in an
included view resolves. TS already does this at module scope. Python does not. Measured with
`adapters/python/index.py --file` on 2026-10-08:

```python
class Foo:
    def bar(self): ...
x = Foo()
x.bar()                      # CALLS target_raw "bar", HEURISTIC — unqualified
def g():
    y = Foo(); y.bar()       # CALLS "m.Foo::bar" — resolved
if __name__ == '__main__':
    z = Foo(); z.bar()       # CALLS "m.Foo::bar" — resolved
```

Module-level scripts, notebooks exported to `.py`, and settings modules are where this shape lives.
The unqualified edge falls to `_link_by_bare_name`, which links only a unique same-language match.

## Scope

1. The module-level walk keeps one local type table across the module's top-level statements,
   with pass 2's forgetful rules unchanged (playbook §2): a rebind the table cannot read re-opens it.
2. A binding made inside a module-level `if`/`for`/`while`/`try`/`with` branch re-opens the name
   after it (forgetful: no join across branches); `if __name__ == '__main__'` keeps today's handling.
3. A function body does not see a module binding made after it, or rebound before it is called —
   only the module's own top-level statements read the table.

## Acceptance criteria

- **AC1:** On the fixture above, `x.bar()` is `CALLS m.Foo::bar`.
- **AC2:** `x = Foo(); x = make(); x.bar()` leaves `x.bar()` unqualified (forgetful).
- **AC3:** A function reading a module-level `x` stays unqualified (no flow across scopes).
- **AC4:** `if c: x = Foo()` then `x.bar()` at module level stays unqualified.
- **AC5:** ADAPTER_PLAYBOOK §1.1's module-scope row reads `368` for Python.
