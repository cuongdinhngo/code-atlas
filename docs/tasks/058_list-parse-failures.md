---
id: 058
slug: list-parse-failures
title: '`parse_failures: 29` — nobody can find out which 29 files the index cannot see'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [009, 028]
---

## Goal
`get_index_status` reports `failed: 29` / `parse_failures: 29` on the anchor repo. It reported the same
29 in field retro round 1 and again in round 2, on a tree that moved by several commits in between —
stable, with no attrition. **No tool lists them.**

Those 29 files are a hole in every answer the index gives: nothing in them is searchable, no symbol they
declare can be a caller, an implementor, or a target. A nav tool that returns nothing because the
declaring file failed to parse reports the same empty answer as one where the symbol truly has no
callers — the same false-absence family as [054](054_bare-name-callers-silent-drop.md) and
[056](056_filter-values-fail-loud.md), arriving by a different route.

29 out of 18,872 is 0.15%, which sounds ignorable until you cannot tell whether it is 29 generated
fixtures or 29 controllers. The round-2 session said exactly that and could go no further.

**The data already exists.** `files.parsed_ok` is a column in the schema (`store.py` DDL); the build
writes it and `counts()` aggregates it. Only the listing is missing.

## Scope / Deliverables
- **Expose the failing paths.** A store method over `files.parsed_ok = 0` and a way for an operator or
  agent to read it. Prefer extending an existing surface to adding a fourteenth tool — `detail_level`
  on `get_index_status` is the obvious candidate, but see the constraint below.
- **Bounded, and never on the cheap path.** The list must not ride on the `standard` status payload;
  `get_index_status` staying cheap is what both field retros named as the thing that must not break. A
  capped list behind an explicit request, or a separate lightweight call.
- **Say why, if the reason is already known.** The build knows whether a file failed on a syntax error,
  an encoding problem, or an adapter timeout — check whether that survives to the store, and record the
  answer. If it does not, listing paths alone is still the deliverable; do not grow the schema for it
  here (R3).
- **A note in the onboarding runbook** telling an operator to check the list after the first build, so
  a systematic failure (one directory, one encoding, one PHP version) is caught at onboarding rather
  than two field retros later.

## Constraints
- **`get_index_status` cost must not move for existing callers** — asserted, at both detail levels.
- **No schema change (R3)** unless the failure *reason* turns out to need a column, in which case that
  becomes its own ticket rather than riding along here.
- **SQL stays in the store (R1.4)**; no language branch in the core (R1.1).
- **Determinism (R4.2)** — the listing is ordered, so two runs return the same rows in the same order.
- **The list is bounded.** A repo where 40,000 files failed must not return 40,000 paths.

## Acceptance criteria
- On a fixture with at least one unparseable file, the failing path is retrievable, and the count
  matches `parse_failures`.
- The `standard` and `minimal` `get_index_status` payloads are unchanged for callers that do not ask
  for the list, asserted.
- The listing is capped, and says so when it truncates.
- Ordering is stable across two runs (R4.2).
- The runbook tells an operator to check the list after the first build.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/store.py` — the `files` DDL (`parsed_ok INT DEFAULT 1`) and `counts()`, which already
aggregates it; `code_atlas/tools/get_index_status.py:121` (`parse_failures`, the count with no list
behind it); `code_atlas/indexer.py` `_parse_all` / `_write` (where `parsed_ok` is set).
Cheapness constraint: field retro round 1 §7 and round 2 §7 both name `get_index_status` as the thing
that must not break.
Origin: field retro round 2 §0 and §6a — the same 29 across both rounds, unlistable.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 058 — list-parse-failures (working doc)

- **Ticket:** 058 · local `docs/tasks/058_list-parse-failures.md`
- **Type:** enhancement
- **Repo(s):** app (`.`)
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend — 0/N UI
- **TIER:** full (multi-file store+tool+tests+docs; not quick/single-row)
- **BASELINE:** green — `924 passed` (2026-08-08, untouched main)
- **work_doc_mode:** embed
- **working-doc path:** this file below separator

## Phase 0 — Refine

`REFINE: 0 unresolved product-decisions | skip: yes`

`refine skipped: 0 unresolved product-decisions`

**INPUT KIND:** ticket

**Exposure-checker:** [Challenger](095749d1-2100-47af-aaea-535e5f88ba66) — none (ready).

**HOW premises (analysis, cited — not refine wants):**

| # | Decision | Resolution | Citation |
|---|----------|------------|----------|
| H1 | Surface | Third `detail_level` on `get_index_status` (`verbose`), not a 14th tool | ticket L29–31 |
| H2 | Cheap path | List never on `minimal`/`standard` | ticket L32–34, L44 |
| H3 | Cap | `config.max_results` + truncation flag | PLAN / nav `truncated`; ticket L49 |
| H4 | Order | `ORDER BY path` | R4.2; `store.file_paths` |
| H5 | Reason | Does **not** survive to store (`files` DDL / `upsert_file` have no error col; indexer discards `ParseResult.error`) → paths only; no schema here | ticket L35–38; `store.py` DDL; `indexer.py` upsert |

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope/Deliverables, Constraints, Acceptance) | 4 decomposed | ROWS: C=5 R=4 G=2 AC=6`

| ID | Source | Verbatim (abbrev) | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|-------------------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | No tool lists the failed files | Expose paths for `parsed_ok=0` | ticket L12–26 | CL1–2 | | ✅ |
| G2 | Goal | Data already in `files.parsed_ok` | Listing only; no new persistence | store DDL + counts | CL1 | | ✅ |
| R1 | Scope | Store method + operator/agent read | `failed_paths` + `verbose` status | L29–31 | CL1–2 | | ✅ |
| R2 | Scope | Bounded; never on cheap path | Cap + not on min/std | L32–34 | CL2 | | ✅ |
| R3 | Scope | Say why if known; else paths | Reason absent → paths only | H5 | CL-note | | ✅ |
| R4 | Scope | Runbook note after first build | Onboarding §3 → call verbose | L39–41 | CL4 | | ✅ |
| C1 | Constraints | Cost unchanged for existing callers | Assert min/std key/payload shape | L44 | CL3 | | ✅ |
| C2 | Constraints | No schema change (R3) | No DDL | L45–46 | CL1 | | ✅ |
| C3 | Constraints | SQL in store (R1.4); no lang branch | store method only | L47 | CL1 | | ✅ |
| C4 | Constraints | Deterministic order (R4.2) | ORDER BY path; two-run assert | L48 | CL1 | | ✅ |
| C5 | Constraints | List bounded | LIMIT max_results + truncated | L49 | CL2 | | ✅ |
| AC1 | AC | Path retrievable; count matches | fixture ≥1 fail | L52–53 | CL2 | | ✅ |
| AC2 | AC | standard/minimal unchanged | key-set assert | L54–55 | CL3 | | ✅ |
| AC3 | AC | Cap + says when truncates | truncated flag | L56 | CL2 | | ✅ |
| AC4 | AC | Stable order two runs | equality | L57 | CL2 | | ✅ |
| AC5 | AC | Runbook tells check after build | grep runbook | L58 | CL4 | | ✅ |
| AC6 | AC | pytest/ruff/mypy green | CI | L59 | verify | | ✅ |

`CLARIFICATION: 0 raised | 5 HOW (H1–H5) | j=0`

**Cause:** presentation gap — count without listing.

**Blast radius:** `store.py`, `get_index_status.py`, tests, onboarding runbook, PLAN §12.

`RULE SECTIONS: R1.1 N/A | R1.4 ✅ | R3 ✅ (no schema) | R4.2 ✅ | R5.2 spirit (honest truncation)`

`SCOPE: S` · `TIER: full`

## AC validation

| AC | Ticket | Computed | Match | Falsifiable |
|----|--------|----------|-------|-------------|
| AC1 | path + count match | `len(paths)≤cap`; `parse_failures==failed` | Y | Y |
| AC2 | min/std unchanged | frozen key sets / no list keys | Y | Y |
| AC3 | capped + truncate signal | `parse_failures_truncated` | Y | Y |
| AC4 | stable order | two calls identical | Y | Y |
| AC5 | runbook note | string present | Y | Y |
| AC6 | green | commands | Y | Y |

## Inventory

N/A (no universal all/every inventory beyond AC2's two detail levels — enumerated in tests).

## Clarifications

`CLARIFICATION: 0 raised | 5 self-resolved (H1–H5) | j=0`

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker | 1 | unmeasured (blocking retrieval) |
| review | reviewer | 1 | unmeasured (blocking retrieval) |
| review | challenger | 1 | unmeasured (blocking retrieval) |

## Decision log

| When | Decision |
|------|----------|
| 2026-08-08 | Standing: best option + pass process gates; push/PR need per-action OK |
| 2026-08-08 | Gate 1 cleared (standing) — refine skip + H1–H5 |
| 2026-08-08 | Gate 2 cleared (standing) — approach below |
| 2026-08-08 | Gate 4 clean after CONVENTION §6 fix (reviewer finding 1) |

## Session status

- **Phase:** done — PR [#68](https://github.com/cuongdinhngo/code-atlas/pull/68)
- **Reviewed at:** `e5be6c387031d6f3ffd63dbd46de5c781361fb80`
- **Reviewed files:** `code_atlas/store.py`, `code_atlas/tools/get_index_status.py`, `tests/test_list_parse_failures.py`, `tests/test_mcp_server.py`, `docs/runbooks/onboarding-a-repo.md`, `docs/PLAN.md`, `docs/CONVENTION.md` (+ working doc / LESSONS exempt)

## Phase 2 — Design

**Approach**
1. `GraphStore.failed_paths(limit: int) -> tuple[str, …]` — `WHERE parsed_ok = 0 ORDER BY path LIMIT ?`.
2. `get_index_status` `DetailLevel = Literal["minimal","standard","verbose"]`. `verbose` = full `standard` payload + `parse_failure_paths` (capped at `config.max_results`) + `parse_failures_truncated` (`failed > len(paths)`). Unbuilt/mismatched: same as standard (no list keys).
3. Assert AC2: minimal/standard never gain list keys; proving test plants >cap failures.
4. Runbook §3: after first build, call `get_index_status(detail_level="verbose")`.
5. PLAN §12: document `verbose` for this tool only; reason does not persist (H5).

**Rejected:** 14th tool (ticket prefer extend); schema for reason (own ticket); list on `standard` (cheap-path constraint); opaque pagination (cap+flag enough for ops).

**Change list**
| # | Change | Path | Rows |
|---|--------|------|------|
| 1 | `failed_paths(limit)` | `code_atlas/store.py` | R1,C3,C4,C5 |
| 2 | `verbose` + list fields | `code_atlas/tools/get_index_status.py` | R1,R2,C1,AC1–4 |
| 3 | Proving + cheap-path tests | `tests/test_list_parse_failures.py` | AC1–4,C1 |
| 4 | Runbook note | `docs/runbooks/onboarding-a-repo.md` | R4,AC5 |
| 5 | PLAN §12 note | `docs/PLAN.md` | docs |
| 6 | MCP schema / loud-fail for STATUS `verbose` | `tests/test_mcp_server.py` | AC6 |
| 7 | CONVENTION §6 `verbose` | `docs/CONVENTION.md` | R7.2 |

**Proving test:** `test_verbose_lists_failed_paths_capped_stable` — plant 3 failed files, `max_results=2`, verbose returns 2 paths in path order, `truncated=True`, `parse_failures=3`; second call identical; standard/minimal lack list keys.

## Phase 3 — Execute

Done on `fix/058-list-parse-failures`. Commits: `85d8b99` (impl), `a42ae54` (MCP tests), `e5be6c3` (CONVENTION), `ecc8115` (LESSONS). Suite: **927 passed**.

## Phase 4 — Review

- Reviewer [894bafe3](894bafe3-d190-452c-b9aa-9ae1f0a68b7d): CHANGES REQUESTED → CONVENTION §6 fixed → LGTM condition met.
- Challenger [6d9c575c](6d9c575c-0c31-487e-898e-dfd963be946c): 15/15 met.
- Proving test green. Gate 4: **clean**.

## Phase 5 — Finalise

Push + PR approved (standing). Opened [#68](https://github.com/cuongdinhngo/code-atlas/pull/68).
Cost summary: 3 subagent dispatches, all `unmeasured (blocking retrieval)`; top driver = review pair.

