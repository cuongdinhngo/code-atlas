# Python adapter (tier 1a + tier 2 framework visibility)

Parses Python into the code-atlas contract vocabulary with the **stdlib `ast` module only** —
no `jedi`, no third-party runtime deps. Tasks 020 (tier 1a), 217 (tier 2), and 227 (local type
table / `semantic_types`).

## Runtime / grammar floor

- **Python ≥ 3.12.** The adapter refuses to handshake/serve on older interpreters (exit 2)
  because `ast.parse` is bound to the running grammar — a different host would otherwise
  yield different rows (R4.2). `dependencies = []` in `pyproject.toml`.
- Own analyser (R6.6): `ruff` + `mypy --strict` over this directory, driven by the
  adapter-local `pyproject.toml` (not the core's mypy `files` list).

## Launch argv

```bash
python adapters/python/index.py --file <path>
python adapters/python/index.py --server
CA_PYTHON_CMD="python /abs/path/adapters/python/index.py --server"
```

`CA_PYTHON_CMD` is the whole argv, `--server` included — the core appends nothing to it
(CONVENTION §5).

## What it emits

| Construct | Emitted as |
|---|---|
| module-level `def` / `class` | Function / Class + CONTAINS |
| package `__init__.py` | Namespace for the package |
| single / multiple bases | EXTENDS |
| `typing.Protocol` / `abc.ABC` (and aliases) | Interface; implementors → IMPLEMENTS |
| `enum.Enum` (and aliases) | Enum |
| instance / `@staticmethod` / `@classmethod` / `@property` | Method + `modifiers` |
| `__init__` / `__new__` in a class body | Method + `extra.constructor`: `Foo(…)` passes its arguments to both, so `find_callers` on either lists the class's calls (367) |
| other decorators | REFERENCES to the decorator target |
| param / return / AnnAssign named types | REFERENCES (builtins / `Any` / `None` skipped) |
| `async def` | `async` modifier |
| nested `def` | Function CONTAINS inside parent |
| `import` / `from` / `as` / relative | IMPORTS (+ ALIASES when names differ) |
| `f()` / `C()` / `obj.m()` | CALLS (`C()` stays CALLS; `obj.m()` is RESOLVED to `<Class>::m` when a local type table binding names the receiver — param/`AnnAssign` annotation or `x = Foo()`; else HEURISTIC) |
| module-level `x = Foo()` then `x.m()` | the module's top-level statements share one table (368): a binding inside an `if`/`for`/`try`/`with` does not outlive it, any other write (unpack, loop target, `import`, `except … as`, walrus, augmented) re-opens the name, a loop's writes are open from its first pass, a star import or an `exec`/`globals()`/`vars()`/`locals()` call clears the table, a name a function declares `global` is never typed, and a function body never reads the table |
| `self.x.m()` | `self.<attr>` types are read once per class, from the class body **and** every method in it, so method order never changes the answer; an annotation outranks an inferred `self.x = Foo()`, and disagreement drops the attribute |
| module `UPPER = …` / class-body assign | Const / Property |
| syntax error | `ok: false` |

Qualified names follow CONVENTION §3: File = repo-relative path; members use
`module.Class::method` (`MEMBER_SEPARATOR` is `::`).
