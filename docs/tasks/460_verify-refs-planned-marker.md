---
id: 460
slug: verify-refs-planned-marker
title: "A planned reference reports `planned`, and a marker whose target now exists says so"
phase: 2
milestone: "Field gaps — tiny-studio"
status: todo
depends_on: [443]
---

## Why this exists

Same field report as 456. tiny-studio's conventions now hold a "shared building blocks" catalogue.
Each row is ✅ (it exists) or ⏳ with the task that will build it, e.g. `web/src/lib/errors.ts` (T30.2).
Specs and ADRs name files that a later task creates, too. Those rows come back
`never_existed`. That is correct, and not actionable, so they are silent.

The useful signal is the other way round, and nothing reports it:
- a planned file that now **exists**, so the marker should be dropped;
- a planned ref whose task is closed but whose file never came.

The consumer is writing its own CI test for this (ADR 0018). A general marker would let any repo get
it from `verify_refs`.

## Scope

1. Read a configurable planned marker on the ref's line or table row (default: none; config such as
   `refs_planned_markers = ["⏳", "(planned)"]`). Such a row reports state `planned` and is never
   actionable while its target is absent.
2. A `planned` row whose target now resolves → `ok` with reason `planned_but_exists`, counted in the
   summary as "markers to drop". Language-free, no tracker integration.
3. No marker configured → today's behaviour, byte for byte.

## Acceptance

1. Fixtures: a marked absent path → `planned`; a marked existing path → `planned_but_exists`; no
   config → unchanged output (golden).
2. The summary and `--format md` list `planned_but_exists` rows; `--fail-on` can name it.
