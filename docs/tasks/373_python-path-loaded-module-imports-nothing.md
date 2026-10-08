---
id: 373
slug: python-path-loaded-module-imports-nothing
title: 'A Python module loaded by file path is unstamped, and a literal import_module reads as dynamic'
phase: 2
milestone: Coverage
status: todo
depends_on: [353, 363, 295, 370]
---

## Why this exists

The Python half of 370. Measured with `adapters/python/index.py --file` on 2026-10-08:
`runpy.run_path(os.path.join(os.path.dirname(__file__), 'x.py'))` and `exec(open(...).read())` emit
plain `CALLS` with the path dropped and no stamp — `maybe_stamp_dynamic_import` covers
`import_module`, `__import__` and `spec_from_file_location` only. A literal
`import_module('pkg.mod')` is stamped dynamic though its target is a literal.

## Scope

1. `run_path` / `exec`-of-a-file stamp `unmodelled_resolution` (the honesty fix, 295).
2. A `__file__`-relative path (`os.path.join(os.path.dirname(__file__), …)`, `Path(__file__).parent
   / …`) gets 353's treatment: an exact relative `IMPORTS`.
3. A literal `import_module('pkg.mod')` / `__import__('pkg.mod')` becomes an `IMPORTS` of that
   module instead of a stamp. Standard library only (R2.1).

## Acceptance criteria

- **AC1:** A file loaded only by `run_path(dirname(__file__)/…)` is `imported_by` its loader.
- **AC2:** `exec(open(p).read())` with a computed `p` stamps the file; `find_orphans` stays unmeasured.
- **AC3:** `import_module('pkg.mod')` is an `IMPORTS` of `pkg.mod`; a computed argument still stamps.
- **AC4:** ADAPTER_PLAYBOOK §1.1's path-built row reads `373` for Python.
