---
id: 019
slug: typescript-adapter
title: TypeScript/JavaScript adapter + contract v2 (M7)
phase: 2
milestone: M7
status: deferred
depends_on: [012, 011]
---

## Goal
Second adapter behind the unchanged core — the real OCP/DIP test; hardens the contract (§4.4, §15).

## Scope / Deliverables
- `adapters/typescript/`: Node sidecar over the TypeScript Compiler API (via `ts-morph`); `allowJs` for JS.
- Module-scoped qnames (no FQNs), e.g. `src/user.ts::User::save`, `src/util.ts::default`.
- **Contract v2**: project-context resolution — `open_project(root)` holds the tsconfig program (or two-pass resolve) so cross-file edges come back `RESOLVED`. Bump `contract_version`.
- Advertise `semantic_types` capability; resolve ESM/CommonJS imports + tsconfig path aliases.
- If a registry is now warranted (adapter #2 exists), introduce the minimal one.
- **CI:** add `actions/setup-node` and an `npm ci` step for `adapters/typescript/`, mirroring what task 006 added for PHP. Commit the lockfile and keep `node_modules/` ignored (R8.3); the guardrail sweeps already exclude `node_modules/` (R6.5). The `test` job grows a second runtime — check whether it should split per adapter.

## Acceptance criteria
- Passes the same `tests/contract/` harness (with TS fixtures); core code unchanged (no new language branches).
- Cross-file type/import edges resolve as `RESOLVED`, not `HEURISTIC`.

## References
Plan §3, §4.4, §15 (M7), §17.
