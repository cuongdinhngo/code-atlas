---
id: 148
slug: r22-framework-sweep-cannot-fail-for-adapter-2
title: The R2.2 framework sweep lists only PHP frameworks — it cannot fail for adapter #2
phase: 2
milestone: M7
status: todo
depends_on: [012, 146]
---

## Why this exists

R2 is *standard over sample*: an adapter encodes the language spec, never a repo's framework. The
grep-gate that enforces it can only see PHP:

    FRAMEWORK_NAME = re.compile(r"laravel|symfony|wordpress|drupal|magento", re.IGNORECASE)
    # tests/contract/test_guardrail_gates.py:24, and the same alternation in .github/workflows/ci.yml

A TypeScript adapter naming `react`, `vue`, `next`, `express` or `nest` passes that sweep clean. The
gate would report GREEN on precisely the violation R2 exists to catch.

The tell that this is an oversight and not a scope decision is one line away: `EXCLUDED_DIR_NAMES`
already carries `node_modules`. The *exclusion* was made adapter-#2-ready; the *inventory* was not.

Same failure class as [146](146_gate-can-pass-on-stale-bytecode.md) — a check that cannot fail — and
it is worth closing on its own, independent of whether [019](019_typescript-adapter.md) is ever
started.

## Scope

- Extend the inventory to the JS/TS ecosystem's framework names.
- Keep **one** copy. The shell gate in `ci.yml` and the pytest twin are hand-kept copies today
  (the module's own comment says "Regexes match `.github/workflows/ci.yml`"), and two copies of a
  list drift in opposite directions (R6.7). Either derive one from the other, or assert they are
  equal.
- One planted negative control per ecosystem, alongside the existing
  `test_r22_planted_framework_name_fails`.

## Acceptance criteria

1. **AC1.** A planted `react` / `vue` / `next` / `express` / `nest` name under `adapters/` **fails**
   the sweep, proven by a planted control, not by inspection.
2. **AC2.** `ci.yml`'s alternation and the pytest alternation are not two independently maintained
   lists: either one is read from the other, or a test fails when they differ (R6.7).
3. **AC3.** No authored file in the tree starts failing — the change adds reach, it does not
   reinterpret existing source.
4. **AC4.** The vacuous-sweep guard is preserved: excluding `vendor/`/`node_modules/` must still
   leave a non-empty authored set (R6.5).

## Not in scope

The R1.1 language-branch regex, which is a different gate with a different failure mode. Any adapter
source.

## References
R2, R2.2, R6.5, R6.7; PLAN §6.
