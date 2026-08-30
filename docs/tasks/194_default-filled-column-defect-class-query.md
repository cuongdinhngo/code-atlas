---
id: 194
slug: default-filled-column-defect-class-query
title: 'One call for "which writers of this table omit this column, and what is its DEFAULT?" — the query that makes tier 2 pay'
phase: 2
milestone: M9+
status: todo
depends_on: [022]
---

## Why this exists (field retro round 12 §15)

Tier 2 puts column write-sites in the graph. This ticket is the **question that spends them**, and the
retro names it verbatim:

> The query that would have solved FIELD-1026 in one call:
> **"Which writers of `LedgerTrans` omit `ChangeUser`, and what is that column's DEFAULT?"**
> Answer: *all 20 `Insert_*_Trans*` procs omit it; `DEFAULT (user_name())`.*
> I needed four grep passes, a purpose-built `dbsweep.php` that maps each `INSERT` to its enclosing
> proc, and two `sqlcmd` round-trips to establish that.

And the class, also verbatim:

> **FIELD-1020, FIELD-1027, FIELD-962 and FIELD-1026 are one defect class** — *a column whose value comes
> from a DEFAULT because every writer omits it* — and it is mechanically detectable from tier 2. That
> is a `check_architecture_rules`-shaped query, not a search.

**Four tickets, one class, mechanically detectable.** That is the strongest demand signal any query in
this project has had before it was written.

## Scope

1. A rule shape over the tier-2 graph answering *"for table T and column C: which writers omit C, and
   what is C's declared DEFAULT?"* — a `check_architecture_rules`-shaped predicate, not a new search
   tool. Design records whether it is a new rule kind or a parametrisation of the existing engine.
2. The answer names the writers by qname and the column's DEFAULT expression as declared, with the
   count of writers that omit it against the total that write the table — a ratio, not a bare list.
3. Honest emptiness: a table with no recorded writers must not read as "no writer omits the column".
   R5.6 — silence is not evidence.

### Explicitly not in scope

- Anything tier 2 does not already put in the graph. This ticket adds **no** vocabulary.
- A runtime `INFORMATION_SCHEMA` probe. R4 bars the core from a live database, and
  [022](022_sql-schema-adapter.md) records that the probe is the right tool for schema *state*.
- Generalising the rule to non-SQL writers before a second consumer asks.

## Constraints

- **R4/R4.2** — deterministic; identical graph ⇒ identical rows.
- **R5.6** — a table the graph holds no writers for is *unmeasured*, and must say so rather than
  answering zero.
- **R6.3** — the judgement about a real repo ships as a committed re-runnable reporter, not a session
  run.

## Acceptance criteria

1. The one-call query returns writers-omitting-C, the total writers of T, and C's declared DEFAULT.
2. A table with no writers in the graph answers *unmeasured*, not *zero* — pinned by a test.
3. The four-ticket class is re-derivable: given a fixture reproducing the shape, the rule flags it.
4. No `contract_version` bump beyond 022's.

## References

Field retro round 12 §15 (the one-call query, the defect class, the by-hand cost).
[022](022_sql-schema-adapter.md) (tier 2, which this consumes),
[184](184_tsql-source-adapter-tier-1a.md) (tier 1a, which 022 builds on),
`code_atlas/architecture_rules.py:109` (`check_architecture_rules`, the shape this follows).
