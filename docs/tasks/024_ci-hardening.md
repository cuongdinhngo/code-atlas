---
id: 024
slug: ci-hardening
title: CI hardening — close the skeleton's fail-open gaps
phase: 1
milestone: Setup
status: in-progress
depends_on: [001]
---

## Goal
`ci.yml` was written in task 001 while `code_atlas/` and `tests/` were still empty, and it still carries
that scaffolding. Two of its steps are **fail-open**: they skip themselves rather than fail when what
they check is missing. Close those, and add the cheap checks the repo's own rules already require but
nothing enforces.

## Scope / Deliverables
- **Remove the two `if: hashFiles(...)` conditions** on the mypy and pytest steps (`ci.yml:40`, `:44`).
  They existed because the directories were empty at scaffold time; today their only remaining effect
  is that deleting or renaming `code_atlas/` or `tests/` makes CI **skip the check and pass green**. A
  guard that cannot fail is not evidence (LESSONS 002).
- **Remove the dead `else pip install ruff mypy pytest` fallback** (`ci.yml:25`) — `pyproject.toml` is
  not optional.
- **Lint the PHP adapter's authored source**: `php -l` on `adapters/php/**/*.php` outside `vendor/`,
  and `composer validate --strict --no-check-publish` so `composer.json` and the committed lock cannot
  drift apart (R8.3).
- **Run the Python matrix the project claims to support**: `requires-python = ">=3.12"` but CI pins
  3.12 only, while development happens on 3.13. Test both.
- **Gate R7.3**: no `Co-Authored-By` / AI-attribution trailer. The rule is codified and nothing checks
  it; grep the PR's commit range.
- **Speed, not correctness**: cache pip and Composer, and add a `concurrency` group so a superseded
  push cancels its predecessor.

## Acceptance criteria
- Deleting `code_atlas/` or `tests/` makes CI **red**, not green — proven by running the workflow's own
  logic against a tree with the directory removed, not by reading the YAML.
- A planted PHP syntax error in `adapters/php/src/` fails the build; a syntax error inside `vendor/`
  does **not** (the lint is scoped to authored source, R6.5).
- A `composer.json` edited out of step with `composer.lock` fails the build.
- A planted `Co-Authored-By:` trailer on a commit in the PR range fails the build.
- The suite passes on both 3.12 and 3.13.

## Out of scope — owned elsewhere
Each of these is recorded on the task that owns it, so this ticket does not grow to hold the whole
roadmap's CI needs:
- moving the R2.2 gate from the `guardrails` job (which never installs dependencies, so its
  `--exclude-dir=vendor` has never been exercised there) into a pytest assertion that runs where
  `vendor/` actually exists — **task 012**;
- `fetch-depth: 0` for git-history tests — **task 016**;
- Docker-mode, Node, .NET and LLM/network runtimes — **tasks 008, 019, 021, 022/023**;
- the 112k-file scale run and cross-repo validation, neither of which belongs in per-PR CI —
  **tasks 015, 018**.

## References
`.github/workflows/ci.yml`, ENGINEERING_RULES R6.4, R6.5, R7.3, R8.3; LESSONS 002 (a guard that cannot
fail), LESSONS 003 (a grep-gate matches prose too), LESSONS 006 (the first vendored dependency).
Surfaced while closing task 006, which was the first task to put real dependencies under `adapters/`.
