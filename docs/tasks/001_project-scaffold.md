---
id: 001
slug: project-scaffold
title: Project scaffold & tooling
phase: 1
milestone: Setup
status: todo
depends_on: []
---

## Goal
Stand up the Python package and dev tooling so every later task has a home.

## Scope / Deliverables
- `pyproject.toml` (package `code_atlas`, deps: `fastmcp`; dev: `pytest`, `ruff`, `mypy`).
- Package skeleton per §5: `code_atlas/{main,config,contract,adapter,store,indexer,resolver,gitutil,ignore}.py` (stubs) + `code_atlas/tools/`.
- `adapters/` and `tests/{contract,fixtures,}` directories.
- `ruff`/`mypy`/`pytest` configured and runnable; a trivial passing test.
- CI (`.github/workflows/ci.yml`, already in repo) turns green: ruff · mypy · pytest + the R1.1/R2.2 grep-gates run on every PR.

## Acceptance criteria
- `pip install -e .` succeeds; `pytest` runs green; `ruff check` clean.
- Import `code_atlas` works; no per-language code anywhere in the package.
- CI passes on the PR: `test` job runs ruff/mypy/pytest (no longer skipped), `guardrails` job green.

## References
Plan §5 (architecture, repo layout).
