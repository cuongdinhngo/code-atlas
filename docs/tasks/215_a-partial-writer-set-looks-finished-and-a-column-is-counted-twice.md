---
id: 215
slug: a-partial-writer-set-looks-finished-and-a-column-is-counted-twice
title: '`check_column_defaults` saw 38 of 55 writers and said so with no marker, and reported one column twice — a 69 %-complete answer that looks finished retires the cross-check that would have caught it'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [194, 192, 022]
---

## Why this exists (field retro round 13 §12.d, §18.4)

[194](194_default-filled-column-defect-class-query.md) shipped the query round 12 named verbatim, and
round 13 called the result **the best single answer of the round**:

> `check_column_defaults("dbo.LedgerTrans", "ChangeUser")` → `default: "(user_name())"` — verified exact
> at `Tables/Data/LedgerTrans.sql:58` — `writers_total: 38`, `omitted_count: 36`, and the two exceptions
> by name, both of which genuinely name the column, for a reason their own comment gives.

And in the same paragraph: **"not trustworthy without the grep."** Three defects, measured:

| | Reported | True | Where |
|---|---|---|---|
| writers of the table | **38** | **55** | grep, cross-checked three ways |
| writers naming the column | **2** | **≥ 4** | same |
| rows for one column | **`total_count: 2`** | 1 | `dbo.LedgerTrans::ChangeUser` is declared in both the per-object file and the baseline migration |

The duplicate is a two-line defect: `_columns_of` builds `qnames` as a **sorted list** of `CONTAINS`
edge targets (`code_atlas/tools/check_column_defaults.py:71`), so a column declared twice yields two
identical qnames, two identical rows and a `total_count` of 2 for one column.

**The under-count is the important half, and it is not primarily this tool's fault.** The 17 invisible
writers fail at the tier below — the write-site edges 022 emits. The retro diagnosed each one:

| Missed writer | Form | Failing tier |
|---|---|---|
| `LedgerTransExtras` — a **trigger on the table** that `UPDATE`s `ChangeUser` | the whole `CREATE TRIGGER` sits inside `EXEC('…')`; the declaration is at `:26` **inside the string** | **parse** |
| `createAppraisalFromDiagnosis` — 2 INSERTs, **both naming the column** | the proc **is** a `Function` node with 2 definitions | **edge** — symbol present, `WRITES` absent |
| `Insert_AB_Trans_v1` — 6 writes | `insert into **Ledgertrans** (` — table name in a different case from the declaration | **edge** — T-SQL is case-insensitive; the matcher is not |
| `Insert_AA_Trans_v1` / `_beta` | `update LedgerTrans` with `SET` on the **next line** — **46 of 51** `UPDATE` sites in the anchor are written that way | **edge** |

**Why this ticket is about the marker, not only the misses.** 194's AC2 required that *a table with no
recorded writers* answer `table_has_no_writers` rather than zero — and it does, correctly. Nobody
specified the case that actually occurred: **a writer set that is present but partial.** The tool has
a coverage surface already (`attach_coverage_note`, from
[192](192_coverage-note-suppressed-on-a-partial-answer.md)) and it fires on *language* coverage, which
was never in doubt here.

Round 13's §18.4 is written about this answer, and it is the round's one genuinely new finding:

> **A wrong answer gets caught by the cross-check the project already mandates, while a 69 %-complete
> answer retires the cross-check by looking finished.** It is also the shape a tool acquires as it
> gets *better* — round 7's harmful ranking was crude enough to spot; this is not.

The cost is measured, not asserted: the retro wrote **three throwaway scripts, 86 lines, 19 minutes**,
all three to check this tool — the tool built to stop people writing throwaway scripts.

## Scope

1. **Dedupe by column identity.** One column is one row, whatever number of files declare it. A
   column declared in N places must not multiply `total_count`, and the extra declarations must not
   be silently discarded either — a column the graph holds twice is a fact about the graph.
2. **A partial writer set says it is partial.** Where the tool can know its writer set is incomplete,
   the payload says so, next to the number. The mechanism is 192's coverage note, applied to a
   condition it does not currently test.
3. **Name what would make it complete**, at whatever precision is available: the write forms that do
   not produce a `WRITES` edge are enumerable (the table above is four rows, three of them mechanical).
   A reader must be able to tell *"38 of the writes I can see"* from *"38 writes exist"*.
4. **Fix the two mechanical edge-tier misses** if design finds them in reach: a case-insensitive table
   match for a case-insensitive language (**R2** — T-SQL's rule, not the anchor's habit) and an
   `UPDATE … SET` whose `SET` is on the following line. Together they account for most of the 17. If
   either is larger than it looks, it splits out and Scope 2 still ships — **the marker is the
   ticket's floor, the edges are its ceiling.**

### Explicitly not in scope

- **The parse-tier miss** — a trigger whose whole body is a string literal (`EXEC('CREATE TRIGGER …')`).
  That is a `CREATE`-inside-dynamic-SQL gap in tier 1a and needs its own evidence; it lands under
  Scope 3's disclosure, not Scope 4's fix.
- **A live `INFORMATION_SCHEMA` probe.** R4 bars the core from a database, and 194 already recorded
  that the probe is the right tool for schema *state*.
- **Generalising the rule beyond SQL writers** before a second consumer asks (194's own boundary).
- **`find_callers`' bare-`EXEC` zero** — that is [214](214_a-bare-exec-links-to-nothing-and-the-zero-says-no-matches.md).

## Constraints

- **R4.2** — deterministic; identical graph ⇒ identical rows, dedupe included.
- **R5.6** — silence is not evidence, and this ticket extends it: **a partial count presented as a
  total is the same failure with a number attached.**
- **R6.3** — the judgement about the anchor ships as a committed re-runnable check, not a session run.
- **R6.9** — assert at the consumer: the proving test reads the payload a caller receives.
- **R7.6** — the disclosure earns its bytes. Round 13 measured mean disclosure at ≈1.2 KB/call, down
  from ~4 KB, and called that batch D's best property. A note that fires on every answer would give
  that back.

## Acceptance criteria

1. A column declared in two files produces **one** row and `total_count: 1`, pinned by a fixture that
   fails before the change.
2. A writer set the tool knows to be partial carries a marker naming that, and a complete one does
   **not** — both pinned. An unconditional note fails this criterion.
3. The marker names what is missing at the precision available (Scope 3), not merely that something
   is.
4. Any edge-tier fix taken under Scope 4 is proven by a fixture in the missed form — case-varied table
   name, or `SET` on the following line — and the anchor's before/after writer count is recorded.
5. `table_has_no_writers` still answers *unmeasured*, never *zero* (194's AC2 does not regress).
6. No `contract_version` bump beyond 022's.

## References

Field retro round 13 §12.d.1 (the three defects), §12's tier-diagnosis table (the four missed write
forms), §2.c (the three throwaway scripts, 86 lines / 19 min), §11.c (best artifact, and why it is not
trusted), §18.4 (*"partial, unmarked, and therefore trusted"* — the box the round says the next one
needs).
[194](194_default-filled-column-defect-class-query.md) (the tool, and the AC that covered the empty
case only), [192](192_coverage-note-suppressed-on-a-partial-answer.md) (the coverage-note mechanism),
[022](022_sql-schema-adapter.md) (tier 2, which emits the `WRITES` edges).
`code_atlas/tools/check_column_defaults.py:64` (`_columns_of`), `:71` (the list that should be a set),
`:85` (`_row`), `:190` (the `unmeasured` discriminator this builds on),
`code_atlas/tools/coverage.py:29` (`relation_unmodelled_for_language` and the note surface).
