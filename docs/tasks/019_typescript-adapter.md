---
id: 019
slug: typescript-adapter
title: TypeScript/JavaScript adapter + a contract bump (M7)
phase: 2
milestone: M7
status: in-progress
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

## Breakdown — filed 2026-08-25 as tasks 150–157

This section used to park a proposed 150–157 as **NOT filed**, because filing them would have read as a
roadmap reorder §19 had not ratified. That ratification arrived (2026-08-25), so the parking reason
expired and the tickets are filed. Two of the proposals were never needed: proposed **150** (ratify
§4.4 with the worker fan-out measured) and **151** (a contract bump for project-context resolution)
both collapsed into 128's written *no-bump* verdict — the adapter resolves per file and the core links
it `RESOLVED` as the contract stands, proven by an empty core diff.

The rest were re-cut around what is actually left after this ticket's slices, so the filed numbers do
**not** map one-to-one onto the old proposals:

| filed | what it covers | was |
|---|---|---|
| [150](150_ts-adapter-has-no-gate-but-its-own-fixtures.md) | no static analyser for the adapter (R6.6) and no cross-repo run (R6.3) — **do first** | 152's R6.6 half + 157's R6.3 half |
| [151](151_ts-member-calls-emit-no-edge.md) | `obj.method()` emits no edge at all — `128-C1` on the member branch — **do first** | not proposed; found reviewing this ticket |
| [152](152_ts-call-args-and-arg-keys.md) | `args`/`arg_keys` on call edges | 154's remainder |
| [153](153_ts-declared-and-inferred-types.md) | the TS local type table in 137's shape + the `semantic_types` verdict | 155 |
| [154](154_ts-allowjs-and-jsdoc-types.md) | `allowJs` breadth and JSDoc as a type source | 156 |
| [155](155_ts-tsconfig-paths-and-export-star.md) | tsconfig `paths`/`baseUrl` and `export *` per-name | 153's remainder |
| [156](156_r12-registry-verdict-now-adapter-2-exists.md) | the R1.2 registry verdict, now its condition is met | 157's remainder |
| [157](157_r62-inventory-has-no-named-default-export-case.md) | R6.2's inventory has no named-`export default` case | not proposed; the one gap the review left open |

147 · 148 · 149 were filed and shipped earlier — they fixed gates that were broken with or without
this ticket.

## Progress — reopened 2026-08-25 (human-ratified)

Shipping in slices on `feat/019-typescript-adapter`. §4.4's gate (150) resolved by 128's written
verdict — **no `contract_version` bump, no project-context lifecycle**: the adapter resolves each
specifier per file and emits the defining module's qname, which the core links RESOLVED as the
contract stands (so proposed 151 collapsed into "no bump", proven by an empty core diff).

**Landed so far:**
- **Nodes/constructs (152, 154-partial):** all 13 of 149's inventory. `type`-alias→Interface,
  `const enum`, module `const`→Const, name-bound & anonymous functions, `::default` for an unnamed
  default export; decorators + declared types on node `extra` (no edge, mirrors PHP attributes).
- **Cross-file RESOLVED (153):** relative + `require` specifier resolution (extension/index, and a
  NodeNext `./x.js` to the `./x.ts` **source** ahead of a compiled sibling), ESM/CJS import bindings,
  namespace-member `ns.Foo`, and `export … from` → ALIASES naming the defining module (barrel
  resolution, 149's load-bearing case). A named `export default class Foo` aliases `::default` to
  `::Foo`, the only path a default-import has to it. All four proven end-to-end by
  `tests/test_ts_import_resolution.py` (real indexer+resolver, every case RESOLVED).
- **`declarations_only` (154-partial):** drops CALLS/NEW body edges, keeps CONTAINS/EXTENDS/
  IMPLEMENTS/IMPORTS structure — for CommonJS as well as ESM, which reach the walk by different
  paths, so the server test runs both module systems.
- **Body edges are sourced at their scope (154-partial):** a call in a method is sourced at the
  method, not its class, matching the PHP adapter's container stack. `tests/contract/` froze only
  `(kind, target_raw, tier)`, so a whole adapter could disagree about `source_qname` and stay green;
  the shape is now a 4-tuple including the source, for **every** adapter.
- **Node runtime (157-partial):** `npm ci` for `adapters/typescript` in `docker/Dockerfile`,
  `.github/workflows/ci.yml`, and `scripts/gate.sh`, so the `needs_node` tests run rather than skip.

**Not in this ticket — filed as its own ticket, see the breakdown above:** the two gates the adapter
still has none of (150); `args`/`arg_keys` (152); the
`semantic_types` type table (153); `allowJs`/JSDoc (154); tsconfig `paths` and `export *` (155); the
R1.2 registry verdict (156); the named-`export default` conformance case (157).

**A sixth defect, filed as [151](151_ts-member-calls-emit-no-edge.md) and then folded in here on
maintainer instruction.** `obj.method()` produced **no edge whatsoever**, where PHP emits the bare
method name at `HEURISTIC` (`Visitor.php:648`) — `128-C1` recurring on the member branch. The fix
emits the bare name at `HEURISTIC` and `(dynamic)`/`DYNAMIC` for a computed callee, and the tier is
what makes the core link it at all (`resolver.py`'s bare-member branch runs only on an edge that
claims `HEURISTIC`). Measured on four real JS files: **22 → 96 CALLS edges**, so 77% of call edges had
been missing. Two existing conformance cases gained the edges they had been silently dropping.

**Delta-green:** Docker full suite **2056 passed / 1 skipped / 0 failed** on the final tree (linux host,
`scripts/docker-test.sh`; the lone skip is the pre-existing docker-in-docker `test_server_build`).
`scripts/gate.sh`: GATE GREEN, 14 passed / 0 skipped.

**Spend:** 4 explore-agent dispatch ≈ 177,238 tokens (scout of the spike, PHP reference, contract/
resolver, harness/inventory); main-loop unmeasured (host surfaces no usage block).
