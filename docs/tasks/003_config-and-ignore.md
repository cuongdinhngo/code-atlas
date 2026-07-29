---
id: 003
slug: config-and-ignore
title: Config (CA_*) & ignore rules
phase: 1
milestone: Setup
status: todo
depends_on: [001]
---

## Goal
Central config resolution and file-ignore logic (§11).

## Scope / Deliverables
- `config.py`: env `CA_*` → project file → defaults. Knobs: `CA_DB_PATH` (default `<repo>/.code-atlas/graph.db`), `CA_WORKERS`, `CA_MAX_RESULTS`, `CA_IMPACT_DEPTH=2`, `CA_IMPACT_MAX_NODES=500`, per-adapter `CA_<LANG>_CMD`, `CA_TOOLS` allow-list.
- `ignore.py`: built-ins (`vendor/ var/ uploads/ log/ node_modules/ .git/`) + `.gitignore` + optional `.codeatlasignore`.

## Acceptance criteria
- Precedence (env > project file > default) covered by tests.
- Ignore matcher unit-tested against built-ins, `.gitignore`, and `.codeatlasignore` cases.

## References
Plan §11.
