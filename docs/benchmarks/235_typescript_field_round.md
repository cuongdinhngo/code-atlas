# 235 — TypeScript adapter field round (playbook §5 / gate 4)

**Date:** 2026-09-08  
**Host:** `dev-host` · Linux 7.0.0-31-generic (x86_64)  
**Server tree:** `e0928350b9ca0718bf894d23604a8882458e687b` (code-atlas worktree used to build)  
**Adapter:** `CA_TYPESCRIPT_CMD` → `node adapters/typescript/index.js --server`

This is the first gate-4 field round for `typescript`. Protocol:
[`ADAPTER_PLAYBOOK.md`](../ADAPTER_PLAYBOOK.md) §5. No adapter fixes landed in 235 (AC5 / not in scope).

## Corpus (pinned SHAs)

Chosen by **shape**, not popularity. The three pinned samples
(`ky` library · `MQTT.js` mixed · `socket.io` compiled-beside-source) do not cover these shapes.

| id | shape | url | SHA |
|---|---|---|---|
| `typescript-eslint` | tsconfig monorepo with `references[]` + package path aliases (155 / IMPORTS miss shape) | https://github.com/typescript-eslint/typescript-eslint.git | `b6b86a15dd42aaa0e37054683cb5606c8fd203c2` |
| `jsdoc` | JSDoc-heavy `.js` package — 564 `@typedef`/`@param`/`@returns`/`@type`/`@callback` hits / 108 files (154's slot) | https://github.com/jsdoc/jsdoc.git | `ce0328e0f1c82554b3f2c2fdac1d4bc60df7e62a` |

## Builds

Two clean `full_build`s per repo; `graph.db` deleted between them (219). Ordered nodes+edges SHA-256 must match (R4.2).

| repo | files | parsed_ok | failed | nodes | edges | wall (1st) | determinism |
|---|---:|---:|---:|---:|---:|---:|---|
| typescript-eslint | 2708 | 2638 | 70 | 12669 | 41965 | 24.1 s | **pass** (identical hash) |
| jsdoc | 527 | 527 | 0 | 1999 | 18169 | 5.5 s | **pass** (identical hash) |

### Parse failures (typescript-eslint)

All **70** failures are under `**/fixtures/_error_/**` — intentional invalid fixtures for the
typescript-eslint AST spec suite. **Expected**, not an adapter defect. `parsed_ok` on non-error
sources is effectively 100 %.

## Node census vs grep (directional)

Grep patterns are line-start declaration heuristics — they over-count (comments, nested keywords,
ambient merges) and under-count (methods, exported consts). Read as a sanity check, not a floor.

### typescript-eslint

| kind | nodes | grep (approx) | note |
|---|---:|---:|---|
| Interface | 1739 | 1835 `interface` lines | close |
| Class | 351 | 2729 `class` lines | grep inflated (class expressions / nested) |
| Function | 1955 | 4323 `function` lines | methods + overloads inflate grep |
| Method | 1242 | — | |
| Enum | 68 | — | |
| ClassConst | 430 | — | **all 430** sit under an `Enum` qname — EnumMember emitted as `ClassConst` (234) |
| Property | 3013 | — | |
| File | 2638 | — | |

### jsdoc

| kind | nodes | grep (approx) | note |
|---|---:|---:|---|
| Function | 810 | 614 `function` lines | |
| Method | 379 | — | |
| Class | 54 | 0 TS `class` lines | JS `class` / constructor patterns |
| Interface | 14 | 0 | from JSDoc `@typedef` (154 working) |
| File | 527 | — | |

## Unlinked-edge ratio (split)

`CONTAINS` stores the child in `target_raw` and leaves `target_qname` null by design — **100 %
"unlinked" on the `target_qname` metric is expected**, not recoverable. Subtract it before any claim.

### typescript-eslint (after noting CONTAINS)

| kind | total | unlinked (`target_qname` null) | reading |
|---|---:|---:|---|
| CONTAINS | 10244 | 10244 | **expected** (target_raw) |
| CALLS | 24929 | 13928 (55.9 %) | mix of expected (external) + recoverable bare calls |
| IMPORTS | 5521 | 1753 (31.8 %) | mostly expected (npm / path-alias unresolved) — 155 shape |
| NEW | 695 | 597 (85.9 %) | |
| EXTENDS | 438 | 57 (13.0 %) | |
| IMPLEMENTS | 24 | 17 (70.8 %) | many targets outside the indexed tree |
| REFERENCES | **0** | — | **known gap 232** — adapter emits none |

### jsdoc

| kind | total | unlinked | reading |
|---|---:|---:|---|
| CONTAINS | 1743 | 1743 | **expected** |
| CALLS | 15590 | 10930 (70.1 %) | |
| IMPORTS | 367 | 211 (57.5 %) | |
| NEW | 447 | 305 (68.2 %) | |
| EXTENDS | 10 | 8 | |
| REFERENCES | 0 | — | same as TS column of 232 (no REFERENCES emission) |

## Nav-tool questions (grep-verified expected beside payload)

Including hits (AC3). `payload_count` is the page length; `total_count` when present is the tool's full tally.

### typescript-eslint

| tool | subject | grep check | payload | verdict |
|---|---|---|---|---|
| `find_implementations` | `…Rule.ts::RuleModule` | `implements RuleModule` → 0 line hits (implementations use other spellings / type aliases) | **1** (`reason=ok`, total=1) | **hit** — tool answered; grep spelling under-counts |
| `find_callers` | `…RuleContext::report` | `\.report\s*\(` → 353 | **50** page / **total=349** (`ok`) | **hit** |
| `find_references` | `…Rule.ts::RuleModule` | `\bRuleModule\b` → 68 | **2** (`ok`) | **shortfall** — consistent with zero `REFERENCES` edges (232); residual 2 come from other edge kinds |

### jsdoc

| tool | subject | grep check | payload | verdict |
|---|---|---|---|---|
| `find_implementations` | `…config.js::module` (Interface from typedef) | `implements module` → 0 | **0** (`no_matches`) | **honest zero** — JS has no `implements`; typedef Interfaces are not class-implemented |
| `find_callers` | `…jsdoc.js::getByLongname` | bare `getByLongname(` heavy | **50** page / **total=484** (`ok`) | **hit** |
| `find_references` | `…tag.js::Tag` | `\bTag\b` → 35 | **5** (`ok`) | **partial hit** — under-count vs bare-name grep (same REFERENCES gap family) |

## Findings filed

| observation | disposition |
|---|---|
| `REFERENCES` edges = 0 on both corpora; `find_references` under-counts vs grep | **Already ticketed** — 232. Not re-filed. |
| 430 `ClassConst` nodes, all EnumMembers (`extra.enum_case`) | **Already ticketed** — 234. `--file` probe confirms `enum Color { Red }` → `ClassConst`. Not re-filed. |
| 70 parse failures | **Dropped** — all `_error_` fixtures; reproducible outside the repo as intentional invalid input, not an adapter bug. |
| New adapter defect beyond 232/234 | **None.** AC5: a round that finds nothing new is a valid green close. |

## Cross-language census

Single-language indexes (typescript adapter only). No cross-language `linked: 0` signal to report;
`get_index_status(verbose)` requires the MCP `registered` map and was not used as a gate here — edge
health was read directly from SQLite (`edge_unlinked` tables above).

## Reproduction

```bash
# clone at the SHAs above, then from a code-atlas checkout:
CA_TYPESCRIPT_CMD="node $PWD/adapters/typescript/index.js --server" \
  python -c "from scripts.cross_repo_validate import index_root; from pathlib import Path; \
  print(index_root(Path('/path/to/checkout'), language='typescript'))"
```
