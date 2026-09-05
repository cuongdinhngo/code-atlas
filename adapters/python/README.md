# Python adapter (tier 1a)

Parses Python into the code-atlas contract vocabulary with the **stdlib `ast` module only** —
no `jedi`, no third-party runtime deps. Task 020. Depth (jedi, `NEW` promotion, typing
constructs) is a future tier-2 ticket.

## Runtime

- **Python ≥ 3.12.** That is the whole runtime — `dependencies = []` in `pyproject.toml`.
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

## What tier 1a emits

| Construct | Emitted as |
|---|---|
| module-level `def` / `class` | Function / Class + CONTAINS |
| package `__init__.py` | Namespace for the package |
| single / multiple bases | EXTENDS |
| instance / `@staticmethod` / `@classmethod` / `@property` | Method + `modifiers` |
| `async def` | `async` modifier |
| nested `def` | Function CONTAINS inside parent |
| `import` / `from` / `as` / relative | IMPORTS (+ ALIASES when names differ) |
| `f()` / `C()` / `obj.m()` | CALLS (`C()` stays CALLS; HEURISTIC when the receiver is unknown) |
| module `UPPER = …` / class-body assign | Const / Property |
| syntax error | `ok: false` |

Qualified names follow CONVENTION §3: File = repo-relative path; members use
`module.Class::method` (`MEMBER_SEPARATOR` is `::`).
