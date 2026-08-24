---
id: 019
slug: typescript-adapter
title: TypeScript/JavaScript adapter + a contract bump (M7)
phase: 2
milestone: M7
status: deferred
depends_on: [012, 011, 128, 147, 149]
---

## Goal
Second adapter behind the unchanged core — the real OCP/DIP test; hardens the contract (§4.4, §15).

## Scope / Deliverables
- `adapters/typescript/`: Node sidecar over the TypeScript Compiler API (via `ts-morph`); `allowJs` for JS.
- Module-scoped qnames (no FQNs), e.g. `src/user.ts::User::save`, `src/util.ts::default`.
- **Contract bump**: project-context resolution — `open_project(root)` holds the tsconfig program (or two-pass resolve) so cross-file edges come back `RESOLVED`. Bump `contract_version`.
- Advertise `semantic_types` capability; resolve ESM/CommonJS imports + tsconfig path aliases.
- If a registry is now warranted (adapter #2 exists), introduce the minimal one.
- **CI:** add `actions/setup-node` and an `npm ci` step for `adapters/typescript/`, mirroring what task 006 added for PHP. Commit the lockfile and keep `node_modules/` ignored (R8.3); the guardrail sweeps already exclude `node_modules/` (R6.5). The `test` job grows a second runtime — check whether it should split per adapter.

## Acceptance criteria
- Passes the same `tests/contract/` harness (with TS fixtures); core code unchanged (no new language branches).
- Cross-file type/import edges resolve as `RESOLVED`, not `HEURISTIC`.

## References
Plan §3, §4.4, §15 (M7), §17.

## Findings that changed this ticket (read of the tree, 2026-08-24)

Seven facts this ticket was written before. None of them reopens §19's *depth before breadth* pivot —
019 stays `deferred` until a human ratifies otherwise in writing.

1. **"contract v2" was stale in the title.** `contract.CONTRACT_VERSION` is **8**. The version number
   is deliberately no longer written down here or in PLAN §4.4 — it drifted once and would again.
2. **[128](128_typescript-adapter-m0-spike.md)'s `depends_on` ran backwards** (it declared 019). The
   spike is this ticket's gate, not its consumer. Fixed in 128.
3. **The import half may need no contract change at all.** `resolver.py:131,437` already promotes a
   uniquely-matched `target_raw` to `RESOLVED`, and CONVENTION §5 puts *name* resolution on the
   adapter while *node linking* stays in the core — which is exactly how the PHP adapter treats `use`.
   An adapter that resolves a specifier to `src/user.ts` and emits `src/user.ts::User` bare earns
   `RESOLVED` under the contract as it stands. Only **inferred** receiver types need more.
4. **And that need just got cheaper.** [137](137_php-local-type-table.md) shipped a PHP local type
   table for the same inferred-receiver problem a TS checker would solve, so §4.4's two options are
   now three, and the third needs no protocol change.
5. **One program per worker is the cost nobody priced.** `indexer._parse_group` fans a language's
   files across `min(workers, len(group))` **independent processes**. An `open_project(root)` holding
   a tsconfig program therefore loads it N times — N× resident memory, N× load latency. Option A
   needs a handshake capability that caps *that adapter's* worker count (data the adapter announces,
   so still no branch in the core, R1.6). Option B keeps the fan-out. That measurement is the
   deciding one and it belongs to the spike.
6. **`tests/contract/` admits one adapter** — [147](147_contract-harness-is-php-shaped.md).
7. **The R2.2 sweep cannot fail for this adapter** — [148](148_r22-framework-sweep-cannot-fail-for-adapter-2.md).

## Proposed breakdown — NOT filed

Parked here rather than filed as tickets, because filing them would read as a roadmap reorder that
§19 has not ratified. 147 · 148 · 149 **are** filed: they fix gates that are broken today and are
worth doing with or without this ticket.

| # | Ticket | Wave | Depends on |
|---|---|---|---|
| — | 147 · 148 · 149 (filed) | 0 — harness + guardrails + inventory | — |
| — | 128 (filed) | 1 — the spike, and the §4.4 evidence | 147, 149 |
| 150 | Ratify §4.4 with the worker fan-out measured — one program per worker is N× | gate | 128 |
| 151 | Contract bump: project-context lifecycle + a project-scoped capability that caps workers | 2, conditional on 150 | 150 |
| 152 | `adapters/typescript/` skeleton — handshake, declarations, CONTAINS, module-anchored qnames, `tsc`/eslint at strictest clean (R6.6), adapter README with the full argv | 3 | 149, 150 |
| 153 | ESM + CommonJS + tsconfig `paths` — the edges that must come back `RESOLVED`, emitted bare | 3 | 152 |
| 154 | Body edges — CALLS/NEW/REFERENCES, `args`/`arg_keys`, honouring `declarations_only` | 3 | 152 |
| 155 | Declared and inferred types — `extra['type']` plus a TS local type table in 137's shape; the `semantic_types` verdict | 3 | 153, 154, 137 |
| 156 | `allowJs` — `.js/.jsx/.mjs/.cjs` and JSDoc types | 3 | 155 |
| 157 | CI + `gate.sh` grow a Node runtime; cross-repo validation on ≥3 public repos (R6.3); **the R1.2 registry verdict**, which can only be taken once adapter #2 exists — expected *no registry*, since `indexer._announce` already loops `config.adapter_cmds` and `extension_index` already builds the map, but the answer must be written down either way | 4 | 152–156, 026 |
