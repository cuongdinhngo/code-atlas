---
id: 018
slug: cross-repo-validation
title: Cross-repo validation ("works on any repo")
phase: 1
milestone: M4
status: todo
depends_on: [015]
---

## Goal
Prove the adapter follows the language standard, not one sample (§2, §16).

## Scope / Deliverables
- Run the PHP adapter against several varied repos: a Laravel app, a Symfony app, a small PSR-4 library, and a large PHP monorepo.
- Assert: no crashes; sane node/edge counts; syntax errors isolated per file.
- Document any construct gaps found (feed back into task 007).
- **CI:** cloning several third-party repos is network-bound and slow, and one sample is not public. This belongs in a scheduled/opt-in workflow, never the per-PR gate; per-PR CI keeps only the spec-driven fixtures (R6.2).

## Acceptance criteria
- All sample repos index without crashing; counts are plausible.
- The large monorepo treated as one sample among several — no repo-specific behavior required.

## References
Plan §2 (standard over sample), §16, §17.
