---
id: 012
slug: contract-conformance-tests
title: Contract-conformance & PHP coverage tests (M2)
phase: 1
milestone: M2
status: todo
depends_on: [007, 002]
---

## Goal
The LSP-substitutability guarantee: every adapter passes the same schema tests (§16).

## Scope / Deliverables
- `tests/contract/`: schema-conformance harness every adapter must pass (asserts emitted JSON + known node/edge counts).
- `tests/fixtures/php/`: namespaced, global, underscore(PSR-0), trait+conflict-resolution, enum, attributes, closures/arrow-fns, first-class-callable, include, static-vs-instance-call, syntax-error.
- CI **grep-gate**: assert zero language branches in `code_atlas/`; ban repo/framework names in adapter source.
- **CI:** the `guardrails` job never installs dependencies, so the `--exclude-dir=vendor` added in task 006 has **never been exercised there** — that gate currently passes over a tree with no `vendor/` in it. Move R2.2 into a pytest assertion in the `test` job, where `composer install` has run and the exclusion can actually be wrong. Keep the shell gate as a second layer; negative-control both (R6.4, R6.5).

## Acceptance criteria
- PHP adapter passes the conformance harness on all fixtures.
- Grep-gate fails the build on a planted `if language ==` or framework name.

## References
Plan §16, §2.
