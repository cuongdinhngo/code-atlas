---
id: 370
slug: path-built-imports-beyond-php
title: 'A TS require built from __dirname plus a path imports nothing'
phase: 2
milestone: Coverage
status: todo
depends_on: [353, 363, 294, 295]
---

## Why this exists

353 made a PHP include built as `__DIR__ . '/x.php'` an exact includer-relative edge, and
`ROOT . '/x.php'` a `HEURISTIC` tail the core links by a unique path suffix. 363 then let
`include_graph` call a file nothing can reach a confident zero. Both are core-side once the adapter
emits the tail. Measured with the TS adapter's `--file` mode on 2026-10-08: `require(__dirname +
'/lib/x')`, `require(path.join(__dirname, 'lib', 'y'))`, `` require(`${__dirname}/lib/z`) `` and
`require(ROOT + '/lib/w')` each emit only `CALLS "require"` — no `IMPORTS`, no literal tail, and no
`unmodelled_resolution` stamp. The Python half (`run_path`, `exec`-of-a-file) is 373.

## Scope

1. A `require` whose argument is `__dirname` joined to literals (by `+`, a template, or
   `path.join`/`path.resolve`) is an exact relative `IMPORTS`; another head with a `/…` literal tail
   is a `HEURISTIC` tail, as 353. Anything else stays `(dynamic)` and stamps the file (295).
2. Only node builtins are spec (R2.1); no bundler alias or framework loader.

## Acceptance criteria

- **AC1:** `include_graph imported_by lib/x.js` lists the `__dirname`-built `require`, in each of
  the `+`, template and `path.join` forms.
- **AC2:** `require(ROOT + '/lib/w')` links by unique path suffix at `HEURISTIC`.
- **AC3:** A `require(name)` with no literal still stamps the file and `find_orphans` stays unmeasured.
- **AC4:** ADAPTER_PLAYBOOK §1.1's path-built row reads `370` for TS.
