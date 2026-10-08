---
id: 370
slug: path-built-imports-beyond-php
title: 'A require built from __dirname plus a path, or a module loaded by file path, imports nothing'
phase: 2
milestone: Coverage
status: todo
depends_on: [353, 363, 294, 295]
---

## Why this exists

353 made a PHP include built as `__DIR__ . '/x.php'` an exact includer-relative edge, and
`ROOT . '/x.php'` a `HEURISTIC` tail the core links by a unique path suffix. 363 then let
`include_graph` call a file nothing can reach a confident zero. Both are core-side once the adapter
emits the tail. Measured with each adapter's `--file` mode on 2026-10-08:

- **TypeScript (CommonJS):** `require(__dirname + '/lib/x')`, `require(path.join(__dirname, 'lib',
  'y'))`, `` require(`${__dirname}/lib/z`) `` and `require(ROOT + '/lib/w')` each emit only
  `CALLS "require"`. No `IMPORTS`, no literal tail, and no `unmodelled_resolution` stamp.
- **Python:** `runpy.run_path(os.path.join(os.path.dirname(__file__), 'x.py'))` and
  `exec(open(...).read())` emit plain `CALLS` with the path dropped, and no stamp —
  `maybe_stamp_dynamic_import` covers `import_module`, `__import__` and `spec_from_file_location`
  only. A literal `import_module('pkg.mod')` is stamped dynamic though its target is a literal.

## Scope

1. **TS:** a `require` whose argument is `__dirname` joined to literals (by `+`, a template, or
   `path.join`/`path.resolve`) is an exact relative `IMPORTS`; another head with a `/…` literal tail
   is a `HEURISTIC` tail, as 353. Anything else stays `(dynamic)` and stamps the file.
2. **Python:** `run_path`/`exec`-of-a-file stamp `unmodelled_resolution` (the honesty fix, 295); a
   `__file__`-relative path gets 353's treatment. A literal `import_module`/`__import__` argument
   becomes an `IMPORTS` of that module rather than a stamp. Each is decided in design, not assumed.
3. Only node and Python builtins are spec (R2.1); no bundler alias or framework loader.

## Acceptance criteria

- **AC1:** `include_graph imported_by lib/x.js` lists the `__dirname`-built `require`.
- **AC2:** A Python file loaded only by `run_path(dirname(__file__)/…)` is `imported_by` its loader.
- **AC3:** A `require(name)` with no literal still stamps the file and `find_orphans` stays unmeasured.
- **AC4:** ADAPTER_PLAYBOOK §1.1's path-built row reads `370` for both adapters.
