---
id: 248
slug: a-table-is-addressable-and-its-columns-are-not-readable-from-it
title: 'A Table is addressable and its 20,808 columns are indexed, but nothing reads one from the other — read_symbol on a Table returns the CREATE line and stops'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [247, 242, 022]
---

## Why this exists (field retro — anchor-repo, 2026-09-11, round 17)

The retro's sharpest single observation, quoted: `read_symbol` on a table returned **one line** —
the `CREATE TABLE [dbo].[…] (` header, `line_start: 13, line_end: 13` — while `get_index_status`
declared `sql: {declared_types: true, params: true}` and the index held `Column` nodes for that very
table. The agent's verdict was *"the data is sitting right there, there is just no way to get it
out"*, and it ranked opening that door as the one change worth about eight `grep` passes in a single
review.

The verdict is right about the door and understates the table. Measured on the anchor index:

```
Table nodes with line_start == line_end:  1855 / 1855   (100%)
Column nodes:                            20,808
widest tables:  dbo.ContractAssets 585 cols · dbo.Member_Site 316 · dbo.Member_Site20181015 280
```

Every `Table` node in the graph is a **point**, not a range. `read_symbol` was not truncating — it
returned exactly the slice it was given.

## Root cause

Two independent halves, and either alone would produce the symptom.

**The node is a point.** `scan.js:326-327` emits a `Table` with `line_start: line, line_end: line`,
and `:318-319` keeps that shape when a later `CREATE` supersedes an earlier `ALTER` sighting. The
adapter never records where the table body ends, so `declaration_slice` has one line to cut. This is
defensible on its own — a 585-column table's full DDL is not something `read_symbol` should print by
default — but nothing compensates for it.

**Nothing walks `CONTAINS` downward for a caller.** The edge exists and is `RESOLVED`
(`scan.js:434-437`), and Pillar 2's ER diagram already reads it. No Pillar 1 tool traverses it:
`read_symbol` resolves one qname and slices source; `file_outline` lists a *file's* symbols, which on
a schema file means every table's columns interleaved with no grouping and a 585-row page for one
table's worth of answer. `class_diagram` does not know the `Table`/`Column` kinds at all (zero
matches for either).

So the container relation is indexed, resolved, and unreadable from the container.

## Scope

A read path from a `Table` to its columns, carrying per-column: name, declared type, `DEFAULT`, and —
once [247](247_the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key.md)
lands — nullability, identity and primary-key ordinal.

**Shape decision to make in phase 2, not assumed here.** The two candidates:

- **Extend `read_symbol` for `kind == "Table"`**, the way 242 extended it for callable kinds. Keeps
  the surface at **24 tools** (`tests/test_documented_tool_count.py` pins the count), and matches the
  precedent that a kind-specific enrichment rides the tool that already addresses that kind.
- **A new `table_columns` tool.** Cleaner paging story for a 585-column table, at the cost of a 25th
  tool and a `TOOLS.md` / recognition-map edit.

The first is the working assumption; the ticket does not bind it.

A consuming agent that verified this in the field ranked one thing above it: *"if I could add one
thing to code-atlas, I would pick [seeing a node's raw fields] before returning data types, because
it lets a user check what the index holds instead of inferring it from a capability flag."* That is
[250](250_no-call-shows-what-a-node-actually-holds.md), and it is not a substitute for this ticket —
250 makes the gap checkable, 248 closes it.

Whichever wins must also decide whether `Table` nodes should carry a real `line_end` (an adapter
change, and a second reason to sequence this behind 247) or keep the point and let the column list
be the answer.

## Constraints

- **R5.6 / the 242 precedent — never claim the stronger tier.** Where the adapter did not capture a
  fact, disclose it; do not emit a false value. A column with no captured nullability must not read
  as nullable, exactly as 242 refused to let `params: []` read as "takes no arguments". The
  per-language capability stamp (231/244) is the channel for saying which facts this index holds.
- **R1.1 — no language branch in the core.** The core may branch on *node kind* (`Table`), which is
  contract vocabulary, never on language. `CLASS_MEMBER_KINDS` is the precedent for naming a
  member-kind subset in `contract.py` rather than spelling kinds at the call site.
- **Bounded by default.** 585 columns is a real page. Reuse `clamp_limit` / `total_count` /
  `truncated` / `result_kinds`, and do not let a default call return the widest table in full.
- **Omit-when-empty (061).** A non-`Table` subject carries none of this, and a table with no indexed
  columns says so rather than returning an empty list that reads as "has no columns".

## Acceptance criteria

- **AC1** Addressing a `Table` qname returns its columns with name, declared type and `DEFAULT`,
  without printing the table's source. **Declaration order is not assertable until 247 lands** —
  every column of a `CREATE TABLE` currently shares the `CREATE` line and `_NODE_ORDER` sorts
  alphabetically, so the DDL order is not in the index. Return the order the store gives and say
  which order it is, rather than implying a declaration order the graph cannot support (R5.2).
- **AC2** With 247 landed, the same answer carries nullability, identity and primary-key ordinal;
  without 247, those keys are absent and the capability stamp says why — no `false`, no `null`.
- **AC3** A table wider than the result cap returns `truncated: true`, a `total_count` of the full
  column count, and a route to the next page; the default call on the 585-column table is bounded.
- **AC4** A `Table` that the index holds no `Column` for is distinguishable from a table whose
  columns were simply not paged in.
- **AC5** Non-SQL subjects are byte-identical before and after (the 022 AC3 shape), and a repo with
  no SQL adapter sees no new keys anywhere.
- **AC6** Tool count and its guard agree — 24 if `read_symbol` is extended, 25 with `TOOLS.md`, the
  recognition map and `tests/test_documented_tool_count.py` all updated if a new tool wins.

## References

- `adapters/sql/src/scan.js:318-319, 326-327` (`Table` emitted as a point), `:434-437` (`CONTAINS`).
- `code_atlas/tools/read_symbol.py` (`declaration_slice` consumer); `_attach_params` is the 242
  kind-gated enrichment precedent.
- `code_atlas/onboarding/er_diagram.py` — Pillar 2 already reads this relation; Pillar 1 does not.
- [242](242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md)
  — kind-gated enrichment plus disclosure, the model this should follow.
