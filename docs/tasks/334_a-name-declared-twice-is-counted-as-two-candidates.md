---
id: 334
slug: a-name-declared-twice-is-counted-as-two-candidates
title: "A bare EXEC to a proc declared in two files (a snapshot and a migration) links to nothing, because the uniqueness test counts nodes, not qnames — and a partial caller list then answers ok"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [214, 215, 321]
---

## Why this exists (field retros, 2026-09-25)

Two retros on one anchor repo hit the same wall on stored procedures. Every migrated proc is
declared twice: once in the schema snapshot, once in the latest migration. Both nodes carry the
**same** qname.

Probed on `main` (`927aeb9`) with `dbo.Gen` declared in `db/ssdt/Gen.sql` and
`db/migrations/V1__gen.sql`, called by `dbo.Caller` (`EXEC Gen`) and `dbo.Caller2` (`EXEC dbo.Gen`):

- `EXEC dbo.Gen` links: the exact-qname lookup hits (`resolver.py:157-163`).
- `EXEC Gen` stays unlinked (`target_qname` NULL). `_link_by_unique_function` requires
  `len(candidates) == 1` (`resolver.py:316`), and two nodes under one qname are two candidates.
- `find_callers dbo.Gen` answers **`reason: ok`, `total_count: 1`** — `Caller2` only. The
  unlinked-call count that would disclose `Caller` runs only when `total_count == 0`
  (`find_callers.py:461-471`). A partial answer is presented as whole.
- With only bare callers, the same subject answers `relation_unmodelled_for_language`: the relation
  *is* modelled, and the label tells the agent to stop trusting SQL callers altogether.

The BACKLOG follow-up from 321 names the same defect for tables (`resolver.py:230,254,277-279`):
two `Table` rows under one qname count as two candidates. One rule, four sites.

## Goal

Uniqueness means one **qname**, not one node — and an answer that left inbound sites unlinked says
so whether or not it found other callers.

## Scope / Deliverables

1. **Count distinct qnames** in every "unique candidate" test in `resolver.py` (the bare-Function
   pass and both casefold passes). Several nodes under one qname link to that qname.
2. **Disclose unlinked inbound sites on a non-empty answer**: when `find_callers` has hits and
   `count_unlinked_by_target_raw` is non-zero, the payload carries the count and
   `authoritative: false` with a named caveat. Today that count is read only on an empty answer.
3. Remove the 321 follow-up line from BACKLOG in the same commit (R7.6).

## Constraints

- **R1.1** — no language branch; the rule is about qnames, which every adapter emits.
- **R2** — no path convention (`migrations/`, `V<n>`) decides anything; two files, one qname.
- **Two different qnames stay ambiguous** — `dbo.Gen` and `audit.Gen` for a bare `Gen` is still
  unlinked (214's rule).
- **061** — an answer with no unlinked sites is byte-identical.

## Acceptance criteria

- **AC1** The probe above: `find_callers dbo.Gen` returns both callers, `reason: ok`; red on today's code.
- **AC2** `Gen` declared as `dbo.Gen` and `audit.Gen`: `EXEC Gen` stays unlinked (regression).
- **AC3** A table declared in one file and ALTERed in another: an unqualified `INSERT INTO T` links.
- **AC4** One linked caller plus one unlinked same-name site: the answer is non-authoritative and
  counts the unlinked site; red on today's code.

## Out of scope

- Choosing *which* of the two definitions is deployed (`read_symbol` still refuses as 327 designed).
- `impact` / `impact_modules` refusing an ambiguous seed (decision 9-A) — a separate question.

## References
`code_atlas/resolver.py:157-163,211-283,285-322`; `code_atlas/tools/find_callers.py:461-513`;
tickets 214, 215, 321, 327.
