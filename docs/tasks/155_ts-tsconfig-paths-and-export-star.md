---
id: 155
slug: ts-tsconfig-paths-and-export-star
title: An aliased specifier and an `export *` both resolve to nothing — the two module shapes 019 left bare
phase: 2
milestone: M7
status: done
depends_on: [019]
---

## Why this exists

Two module shapes resolve to nothing today, both documented as open in
`adapters/typescript/README.md`:

1. **tsconfig `paths`/`baseUrl`.** `imports.js` handles a specifier starting with `.` and returns
   `null` otherwise, so `@app/models` — the alias style most TS monorepos use — never names a file and
   every edge through it stays bare. In a repo built on aliases that is *most* of the import graph.
2. **`export * from "./m"`.** `parse.js` `emitReExport` emits the module dependency (`IMPORTS`) and
   nothing per name, because a file-at-a-time parse cannot enumerate what `./m` exports. A barrel
   built from `export *` therefore stops resolving where a named re-export would have carried through
   (019 shipped the named half as `ALIASES`).

## Scope / Deliverables

- Read `tsconfig.json` `baseUrl`/`paths` — the nearest one up the tree, `extends` followed — and
  resolve an aliased specifier through it to the same repo-relative file a relative specifier gets.
  The file is read from disk by the adapter, so the core stays language-blind (R1.1) and the config is
  the *language's* standard, not any repo's names (R2).
- Cost note: this is per-file work in a fanned-out worker (019's finding #5). Cache per process, and
  say what the lookup costs on a pinned sample rather than assuming it is free.
- `export *`: state the honest answer. Either the core's existing `ALIASES` chain can carry a
  whole-module re-export, or it cannot be resolved file-at-a-time and the `IMPORTS`-only behaviour is
  correct and gets documented as a known limit — **decided in writing**, not left as a silent gap.
- Fixtures: an alias-resolved import, an `extends`-chained tsconfig, and a barrel of both kinds.

## Acceptance criteria

1. An `@alias/...` import produces an edge whose `target_raw` names the defining file, and the proving
   test drives the real indexer+resolver to `RESOLVED` (the shape `test_ts_import_resolution.py` uses).
2. A missing/malformed `tsconfig.json` degrades to bare, never crashes the parse — soft-fail, one file
   at a time (§4.1).
3. The `export *` verdict is written in the adapter README, with the reason.
4. Red run recorded per guard (R6.5); no `contract_version` bump (R3).

## Out of scope

- Node `node_modules` resolution / package `exports` maps. An external package is out of the indexed
  tree by definition; a bare target is the right answer there.
- Path aliases from bundler configs (webpack, vite). Not the language standard (R2).

## References

`adapters/typescript/src/imports.js`, `src/parse.js` `emitReExport`, `README.md` *Still out of scope*;
ENGINEERING_RULES R1.1, R2, R3, R6.5; PLAN §4.1, §4.4; task 019.

---

## Session status

- **KEY:** 155 · **work_doc_mode:** embed · **Run args:** autorun, "with skipped review" (challenger OFF; Gate 4 waived).
- **Phase:** 5 finalise — complete; → PR.
- **BASELINE:** an aliased specifier resolved to nothing today (`imports.js` returned null for non-`.`); delta-green via Docker (node adapter + resolver + `fcntl`).

## Phase 0 — refine

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

References resolve: `imports.js` (`resolveRelative` returned null for non-`.`), `parse.js emitReExport` (`parse.js:244`), README *Still out of scope*. The one open decision — resolve `export *` per-name or not — is the ticket's own "decide in writing"; resolved as a HOW by the file-at-a-time constraint (cited below), not a want-decision.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend (0 UI files) · **SCOPE:** M · **TIER:** full

`SECTIONS: 3 found (Scope/Deliverables, Acceptance criteria, Out of scope) | 3 decomposed | ROWS: C=2 R=4 G=1 AC=4`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ · §R2 (change-type) ✅ · §R3 (change-type) ✅ · §R6.5 (change-type) ✅ · §R7.2 (change-type) ✅`
`BASELINE: red — an @alias import resolves to nothing today; the alias proving test is the guard. Delta-green via Docker before PR`

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Status |
|---|---|---|---|---|
| G1 | preamble | two module shapes resolve to nothing | Aliases resolve; `export *` decided in writing | open |
| R1 | Scope 1 | read tsconfig baseUrl/paths (nearest, extends followed); resolve alias to the file | `imports.js` resolves non-`.` via nearest tsconfig; core stays blind (R1.1) | open |
| R2 | Scope 2 | cost note: cache per process; say the cost on a sample | parse + resolution cached; measured µs/lookup recorded | open |
| R3 | Scope 3 | `export *`: decide + document | Verdict: IMPORTS-only (file-at-a-time limit), in README | open |
| R4 | Scope 4 | fixtures: alias import, extends-chain, barrel of both kinds | `aliased.ts` + inline tsconfigs; `reexport_barrel` already covers both kinds | open |
| AC1 | AC1 | `@alias` import → edge target names the file; proving test drives to RESOLVED | Falsifiable: alias + extends tests to RESOLVED | open |
| AC2 | AC2 | missing/malformed tsconfig degrades to bare, never crashes (§4.1) | Falsifiable: malformed-tsconfig test | open |
| AC3 | AC3 | `export *` verdict in README with reason | Falsifiable: README section | open |
| AC4 | AC4 | red run per guard (R6.5); no contract bump (R3) | Falsifiable: recorded red-run; no contract.py change | open |
| C1 | Out-of-scope | no node_modules / package `exports` | boundary — bare target is right for externals | binding |
| C2 | Out-of-scope | no bundler (webpack/vite) aliases | boundary — not the language standard (R2) | binding |

### AC validation

All four ACs falsifiable (indexer-to-RESOLVED / malformed-soft-fail / README / recorded red-run). No want-decision. The `export *` decision is a HOW the file-at-a-time constraint settles, cited — not a user choice.

### Root cause (taxonomy: logic)

`imports.js resolveRelative` returned `null` for any specifier not starting with `.`, so `@app/models` — the alias style most TS monorepos use — named no file and every edge through it stayed bare. `export *` emits `IMPORTS` only because a file-at-a-time parse cannot enumerate the re-exported module's names.

### Blast radius

`adapters/typescript/src/imports.js` (tsconfig resolver), `src/parse.js` (`resolveSpec` uses the combined resolver), `README.md`, new fixture `tests/fixtures/typescript/resolve/aliased.ts`, `tests/test_ts_import_resolution.py` (3 tests). No `code_atlas/`, no contract, no store.

## Phase 2 — design

### Approach

`imports.js` gains `resolveSpecifier = resolveRelative ?? resolveAlias`. `resolveAlias` walks from the
importing file's dir to the repo root for the **nearest** `tsconfig.json`, loads it via
`ts.readConfigFile` (JSONC), follows a relative `extends`, and resolves the specifier through
`paths` (longest key wins, `*` captured) then bare `baseUrl`, reusing `resolveWithExt` so the same
source-over-compiled and extension rules apply. `parse.js:171` swaps `resolveRelative` for
`resolveSpecifier`, so every import/require/re-export edge benefits with no core change (R1.1).

**Caching (R2).** The parsed config is cached per tsconfig path; resolution is cached per
`(configDir, specifier)` — an external `chalk`/`node:fs` import stats ~14 dead `baseUrl` candidates,
and the same specifier recurs across a build.

**`export *` verdict (R3, AC3): IMPORTS-only, a documented file-at-a-time limit.** A named re-export
aliases the name (it is written in the file); `export *` names nothing, and enumerating `./m`'s
exports needs `./m` and its transitive `export *`s — whole-program knowledge a file-at-a-time parse
lacks. A shallow one-level read would resolve some names and silently miss re-exported ones, worse
than an honest bare edge. Recorded in the README.

### Rejected alternatives

- **Resolve `export *` by reading `./m` from disk** — one level is inconsistent (misses transitive re-exports), and full resolution is a whole-program pass the v1 contract does not have. Rejected; documented as a limit.
- **`ts.parseJsonConfigFileContent`** (full program) — resolves extends but also globs files and is far heavier than reading baseUrl/paths. Rejected for the cheap manual `extends` follow.
- **node_modules / bundler alias resolution** — out of the indexed tree / not the language standard (R2). Out of scope.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

### Verification plan (per-AC)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration | `test_tsconfig_paths_alias_resolves…` + `test_extends_chained…` (indexer+resolver → RESOLVED) | ✅ |
| AC2 | logic (soft-fail) | `test_malformed_tsconfig_degrades_to_bare_never_crashes` | ✅ |
| AC3 | docs | README "Module aliases and `export *`" section | ✅ |
| AC4 | validation | recorded red-run (alias disabled → both alias tests fail) + no contract.py change | ✅ |

### Proving test

`test_tsconfig_paths_alias_resolves_to_the_defining_module` + `test_extends_chained_tsconfig_inherits_paths`
in `tests/test_ts_import_resolution.py`: build a tiny project with tsconfig `paths` (and an `extends`
chain), full_build, assert `src/aliased.ts::make` NEW → `src/models.ts::User` at RESOLVED. Fails
pre-change (alias → null) and — per AC4 — fails if `resolveAlias` is disabled. Invocation:
`pytest tests/test_ts_import_resolution.py -q` (Docker: node adapter + resolver).

### SCOPE

`SCOPE: M` — a resolver in the adapter + one call-site swap + fixtures/tests + README. No core, contract, or store. Branch `feat`.

## Phase 3 — execute

**Branch:** `feat/155-tsconfig-paths-export-star`

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `resolveSpecifier = resolveRelative ?? resolveAlias`; nearest tsconfig, extends followed, paths+baseUrl | implemented-as-approved |
| config parse cached per tsconfig; resolution cached per (configDir, specifier) | implemented-as-approved |
| `export *` verdict (IMPORTS-only) in README with reason | implemented-as-approved |
| fixtures: aliased.ts + inline extends chain; reexport_barrel covers both re-export kinds | implemented-as-approved |

No deviations. `SCOPE: M` held.

### Verification sweep (Axis 1)

Diff = `adapters/typescript/src/{imports.js,parse.js}`, `adapters/typescript/README.md`,
`tests/fixtures/typescript/resolve/aliased.ts` (new), `tests/test_ts_import_resolution.py`,
`docs/tasks/155_*.md`, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`. No `code_atlas/`, no contract (R3), no store.

### Empirical outputs

Alias resolution (adapter `--file`): `@app/models` → `src/models.ts`; the `new User()` NEW targets
`src/models.ts::User`. Extends-chain inherits paths → same. Malformed tsconfig → `ok:true`, alias
stays bare `@app/models` (soft-fail, §4.1).

Cost (R2, cache warm, per non-relative lookup): alias-hit ~81 µs; external bare-miss ~54 µs with the
(configDir, specifier) result cache (~877 µs on the first, uncached miss — stats ~14 dead baseUrl
candidates once per distinct specifier per config-dir).

AC4 red-run — `resolveAlias` disabled in `resolveSpecifier`:
```
test_tsconfig_paths_alias_resolves_to_the_defining_module FAILED (target_qname None)
test_extends_chained_tsconfig_inherits_paths FAILED
```
imports.js restored byte-identical (grep of the alias call = 2).

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_tsconfig_paths_alias_resolves…` + `test_extends_chained…` (RESOLVED) |
| AC2 | `test_malformed_tsconfig_degrades_to_bare_never_crashes` |
| AC3 | README "Module aliases and `export *`" |
| AC4 | recorded red-run + no `contract.py`/`contract_version` change |

## Phase 5 — finalise

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

A straightforward feature slice against a stable seam produced no new durable engineering lesson.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; review phase waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Gate 4 waived, not reintroduced. Self-check: tsc gate green, alias/extends/malformed tests green in Docker, AC4 red-run recorded, imports.js restored. Maintainer reviews on the PR.
