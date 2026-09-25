---
id: 333
slug: an-aliased-update-writes-to-its-alias
title: "UPDATE c SET … FROM dbo.T c emits WRITES onto the alias c, not dbo.T — the table's writer list and check_column_defaults lose every aliased update"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [278, 328]
---

## Why this exists (review of #451, 2026-09-25)

T-SQL's joined-update form names the **alias** after `UPDATE` and the table in the `FROM` clause.
`readUpdate` (`adapters/sql/src/ddl.js:497-520`) takes the first qualified name after `UPDATE` as the
table, so the statement below emits `WRITES` onto `c::ParentId` at `RESOLVED`:

```sql
UPDATE c SET ParentId = 1 FROM dbo.Child c JOIN dbo.Parent p ON p.Id = c.ParentId;
```

Probed on `main` after #452: `dbo.Alias_Upd c::ParentId 3 RESOLVED`; the plain form
`UPDATE dbo.Child SET …` emits `dbo.Child::ParentId` correctly. The aliased site is missing from
`find_references dbo.Child` and from `check_column_defaults`, and the edge claims `RESOLVED` for
a name that is not an object.

#451 fixed the same shape for `DELETE c FROM dbo.T c` with `deleteAliasTable` (`ddl.js`); the
UPDATE path was left out of that PR's scope.

## Goal

An aliased UPDATE writes to the table its alias names.

## Scope / Deliverables

1. **`readUpdate` resolves an alias** through the statement's `FROM` / `JOIN` sources, sharing one
   helper with `readDelete` (R6.7) — no second alias parser.
2. **Unresolvable alias** (no matching source) keeps today's target — never a guessed table.

## Constraints

- **R2.1** — T-SQL grammar only; no repo's table or procedure names.
- **R6.7** — one alias resolver for DELETE and UPDATE.
- **061** — a non-aliased UPDATE answers byte-identically.
- **R4.2** — identical input, identical rows.

## Acceptance criteria

- **AC1** `UPDATE c SET X = 1 FROM dbo.T c JOIN …` → `WRITES` onto `dbo.T::X`; red-arm on today's code.
- **AC2** `UPDATE t SET X = 1 FROM dbo.T AS t` (explicit `AS`) → the same.
- **AC3** `UPDATE dbo.T SET X = 1 WHERE …` is byte-identical (regression).

## Out of scope

- The loose statement classifier (`INSERT_RE` / `UPDATE_RE` match anywhere on a line) — a separate
  finding if a probe shows a false edge.

## References
`adapters/sql/src/ddl.js:497-520` (`readUpdate`), `deleteAliasTable` (328); `adapters/sql/src/scan.js`
statement flush; tickets 278, 328.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 333 — aliased UPDATE writes to its FROM source (working doc)

- **Ticket:** 333 · local · **SCOPE:** S · **TIER:** full · **TRACK:** backend
- **REVIEWER:** OFF · **CHALLENGER:** ON
- **Current phase:** review — round-3 fix unreviewed
- **Session status:** stopped — Gate 4 red after three challenger rounds (autorun abort list)

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW1: the UPDATE path scans FROM/JOIN from the first `FROM` after `SET`; the DELETE path keeps its
FROM-right-after-the-target guard — citation: Scope §1 (one resolver) + 061 (plain forms unchanged).

## Requirements matrix

`SECTIONS: 7 found (Why · Goal · Scope · Constraints · Acceptance · Out of scope · References) | 7 decomposed | ROWS: C=4 R=2 G=1 AC=3`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Goal | aliased UPDATE writes the aliased table | D1 | ✅ |
| R1 | Scope 1 | readUpdate shares readDelete's resolver | D1 | ✅ |
| R2 | Scope 2 | unmatched alias keeps today's target | D1 · D2 | ✅ |
| C1–C4 | Constraints | R2.1 R6.7 061 R4.2 | D1 | ✅ |
| AC1–AC3 | AC | proving | D2 | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: `readUpdate` took the first name after `UPDATE` as the table; 328's alias lookup
  required `FROM` right after the target, which the UPDATE form never has (`SET` comes first).
- Blast radius: `adapters/sql/src/ddl.js` only; no contract or core change.

`TRACK: backend — 0/N UI`

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R2.1 ✅ · R6.7 ✅ · R7.2 ✅`

`BASELINE: green`

## Phase 2 — Design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | k/N |
|---|--------|------|-----|
| D1 | `deleteAliasTable` → `aliasSourceTable(code, from, target)`; readUpdate + readDelete call it | adapters/sql/src/ddl.js | 1/1 |
| D2 | proving | tests/test_aliased_update_writes.py | 1/1 |
| D3 | edge-table row · bookkeeping | adapters/sql/README.md · docs | 1/1 |

| AC | risk | proof | provenance | match |
|----|------|-------|------------|-------|
| AC1–3 | integration | pytest | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_aliased_update_writes.py -q`

`SCOPE: S`

## Phase 3 — Execute

**Branch:** fix/333-aliased-update-writes-table

Ran at 94217c50005a0c25f37ffd4c40964bb09d689f47

```
$ .venv/bin/python -m pytest tests/test_aliased_update_writes.py tests/test_deletes_edge_kind.py -q
12 passed
```

Red arm on `main` (4d0c100): AC1 and AC2 fail (`c::X` / `a::X`), AC3 and the unmatched-alias arm pass.
Differential over 28 synthetic UPDATE/DELETE shapes, `main` vs branch `ddl.js`: 10 differ, each an
alias now resolved to its table (9 UPDATE, 1 derived-table DELETE that `main` sent to the inner
source); every non-aliased shape (plain, `TOP`, subquery, `OUTPUT`, temp/table variables, DELETE
forms) is byte-identical (061).

Full verification at `94217c5`: `scripts/gate.sh` → `GATE GREEN — all 20 checks passed`;
`scripts/docker-test.sh` → `4562 passed, 5 skipped` (4,554 + this ticket's 8).

## Phase 4 — Review

REVIEWER: OFF (`--no-reviewer`) · CHALLENGER: ON — three rounds, each NOT-CLEAN on a distinct shape the
shared resolver mis-scanned, each fixed with a proving arm:

| Round | Tree | Finding | Fix |
|---|---|---|---|
| 1 | `8477bab` | a subquery / derived table reusing the alias shadowed the outer source (UPDATE and DELETE) | depth-0 FROM/JOIN only (`3960290`) |
| 2 | `3960290` | an unterminated statement bled into the next `SELECT`'s FROM | stop at a depth-0 statement keyword (`6def398`) |
| 3 | `6def398` | a delimited `[Select]` read as that stop keyword | keywords inside `[]` / `""` skipped (`94217c5`) |

Informational, out of scope and unchanged from `main`: `APPLY` sources and CTE names are not resolved.
