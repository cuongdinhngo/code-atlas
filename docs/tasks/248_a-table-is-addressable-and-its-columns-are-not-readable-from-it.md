---
id: 248
slug: a-table-is-addressable-and-its-columns-are-not-readable-from-it
title: 'A Table is addressable and its 20,808 columns are indexed, but nothing reads one from the other — read_symbol on a Table returns the CREATE line and stops'
phase: 1.5b
milestone: Agent-fit
status: done
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
  ordered by the DDL's own column order, without printing the table's source. That order is **not**
  the node order — every column of a `CREATE TABLE` shares the `CREATE` line and `_NODE_ORDER` sorts
  alphabetically, which is why this ticket first read it as unrecoverable. It is carried by the
  `CONTAINS` **edge ids**, which follow the adapter's emission order. A claim that specific owes
  evidence from a real indexed `CREATE TABLE` rather than planted rows (R5.2).
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 248 — Table columns readable from read_symbol (working doc)

- **Ticket:** 248 · local file `docs/tasks/248_a-table-is-addressable-and-its-columns-are-not-readable-from-it.md`
- **Type:** coverage / payload
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 UI paths
- **TIER:** full
- **BASELINE:** green — related suite 25 passed / 5 skipped on `3548648b03e1b01ec13d7950c5ac57cf2e35bb0b`

## Session status

- **Last updated:** 2026-09-11
- **Current phase:** finalise
- **Next action:** push + open PR (authorised); merge not authorised
- **Blocked on:** none
- **work_doc_mode:** embed
- Run: `/mango:autorun 248` with `--no-reviewer`; challenger ON.
- Branch: `feat/248-table-columns-readable-from-table`
- Contract: `.mango/run-contract-248.txt`
- Worktree: `/tmp/code-atlas-wt-248`

---

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

**PREMISE detail.** Present: `adapters/sql/src/scan.js`, `code_atlas/tools/read_symbol.py`, `code_atlas/onboarding/er_diagram.py`, `code_atlas/contract.py` (`CLASS_MEMBER_KINDS` precedent), `tests/test_documented_tool_count.py`.

**INPUT KIND:** ticket (not epic).

**How-decision (self-resolved) — handover authorises best approach:**
1. **Extend `read_symbol` for `kind == "Table"`** (keep 24 tools). Cite ticket Scope working assumption + AC6 + 242 kind-gated enrichment precedent (`_attach_params` / `CALLABLE_KINDS`).
2. **Keep `Table` as a point `line_end`; column list is the answer.** Cite ticket Scope ("keep the point and let the column list be the answer") — no adapter span change; AC1 forbids printing the CREATE line as the product.

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `do-not-attest-past-the-payloads-resolution` | 2 | handle | Yes — CONTAINS indexed; Pillar 1 does not walk it from Table |
| 2 | `stamp-at-the-builder-not-the-wrapper` | 2 | handle | Yes — attach beside `_attach_params` on success path |
| 3 | `stamp-evidence-with-the-tree-under-review` | 2 | handle | Process — empirical blocks need `Ran at <sha>` |

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=3 G=1 AC=6`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 proven by | Status |
|----|--------|------------------|----------------|--------------|-----|-----------------|--------|
| G1 | Why | Table addressable; columns indexed; no read path | `read_symbol` on Table returns columns | point slice today | D1 | proving test || ✅ |
| C1 | Constraints | R5.6 / 242 — never claim stronger tier | Omit nullability/identity/pk without 247; no false/null | scan.js extra today | D1 | AC2 || ✅ |
| C2 | Constraints | R1.1 — no language branch; kind branch OK | Gate on `Table` via contract constant | CLASS_MEMBER_KINDS | D1 | R1.1 || ✅ |
| C3 | Constraints | Bounded by default; clamp_limit / total_count / truncated / result_kinds | Page columns; default ≤ CA_MAX_RESULTS | clamp_limit | D1 | AC3 || ✅ |
| C4 | Constraints | Omit-when-empty (061) | Non-Table unchanged; empty table distinct | 061 | D1 | AC4/AC5 || ✅ |
| R1 | Scope | Read path Table → columns (name, type, DEFAULT) | DDL order; no CREATE source | CONTAINS walk | D1 | AC1 || ✅ |
| R2 | Scope | Shape: extend read_symbol (working assumption) | 24 tools | AC6 | D1 | AC6 || ✅ |
| R3 | Scope | Keep point line_end; columns are the answer | No adapter span edit | scan.js point | D1 | diff ⊆ || ✅ |
| AC1 | AC | Table qname → columns name/type/DEFAULT, DDL order, no source | | | D3 | proving || ✅ |
| AC2 | AC | With 247: nullable/identity/pk; without: keys absent | 247 not on main → omit | | D3 | omit test || ✅ |
| AC3 | AC | Wide table: truncated + total_count + next-page route; default bounded | | | D3 | page test || ✅ |
| AC4 | AC | No-column table ≠ truncated empty page | | | D3 | empty vs page || ✅ |
| AC5 | AC | Non-SQL / non-Table byte-identical | | | D3 | twin bytes || ✅ |
| AC6 | AC | Tool count 24 (extend) or 25 (new) | extend → 24 | | D3 | documented count || ✅ |

## AC validation

| AC | Match? | Falsifiable? |
|----|--------|--------------|
| AC1 | Y | assert columns keys + order + empty/absent source for Table |
| AC2 | Y | assert nullable/identity/pk keys absent on current index |
| AC3 | Y | plant > max_results columns; assert truncated/total_count/offset |
| AC4 | Y | plant Table with 0 CONTAINS vs offset past end |
| AC5 | Y | Function/Class payload bytes equal before/after (or keys absent) |
| AC6 | Y | `tests/test_documented_tool_count.py` still 24 |

## Inventory

- **N:** 1 tool (`read_symbol`) · 0 new tool · 0 adapter span change

| # | Item | Ph3/4 | Status |
|---|------|-------|--------|
| 1 | read_symbol Table columns attach + paging | proving module | ✅ |

## Clarifications

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

1. Extend `read_symbol` (not new tool). Cite Scope working assumption + AC6 + 242.
2. Keep Table point; columns are the answer. Cite Scope alternative + AC1 no-source.

---

## Phase 1 — Analysis

- Root cause (`data`/`payload`): Table nodes are points (`scan.js` line_start==line_end); CONTAINS edges exist and are RESOLVED but no Pillar 1 tool walks them from the Table. `read_symbol` only slices the point.
- Blast radius: `read_symbol` success payload for `kind==Table` at `standard`; optional `limit`/`offset` kwargs (ignored for other kinds); contract constant naming Table; PLAN one clause; proving tests. Adapter unchanged. Tool count stays 24.
- `TRACK: backend` · `SCOPE: M` · `TIER: full`

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ kind not language · R1.4 (change-type) ✅ store edges API · R2.2 (change-type) ✅ fixture not repo names · R3 (change-type) ✅ no vocab bump (Table/Column/CONTAINS exist) · R4.2 (change-type) ✅ adapter spelling + edge-id order · R5.6 (change-type) ✅ omit uncaptured keys · R6.1 (change-type) ✅ proving tests · R7.6 (change-type) ✅ PLAN one clause`

### BASELINE

Related suite on HEAD `3548648b03e1b01ec13d7950c5ac57cf2e35bb0b` (pre-product change):
`pytest tests/test_read_symbol_params.py tests/test_search_read_outline.py tests/test_read_symbol_minimal_drops_docblock.py tests/test_check_column_defaults.py -q` → **25 passed, 5 skipped**.

`BASELINE: green`. No exclusions.

- **Gate 1 status:** cleared (autorun; `j = 0`)

---

## Phase 2 — Design

- **Approach.** On a successful `read_symbol` of `kind == Table` at `detail_level=standard`, walk `CONTAINS` edges, order by edge `id` (DDL insertion order — `_EDGE_ORDER` alphabetises `target_raw` and would scramble), load Column nodes, emit `columns: [{name, type?, default?}]` omitting absent defaults (061). Clear `source` to `""` so the CREATE header is not the product (AC1). Page with `clamp_limit` + optional `limit`/`offset` kwargs; attach `total_count`, `truncated`, `results_offset`, and `result_kinds` when truncated multi-kind would apply (Column-only → result_kinds stays omitted per 123). Empty CONTAINS → `no_indexed_columns: true`, no `columns` key (AC4). Non-Table / `minimal` / miss paths unchanged (AC5). Without 247, never emit nullability/identity/pk keys (AC2). Name `Table` via a contract constant beside `CLASS_MEMBER_KINDS`. Tool count stays 24 (AC6). No adapter `line_end` change (R3).

- **Rejected.** (1) New `table_columns` tool — rejected: AC6 prefers 24; 242 precedent is kind-gated enrichment on the addressing tool. (2) Expand Table `line_end` in the adapter — rejected: 585-col DDL is not the default answer; ticket allows keeping the point. (3) Sort columns by qname like `check_column_defaults` — rejected: AC1 requires DDL order; edge `id` preserves emission. (4) Contract version bump — rejected: vocabulary already has Table/Column/CONTAINS (R3).

**Assumptions**

| Assumption | Status |
|------------|--------|
| Edge `id` order equals DDL emission order for CONTAINS | verified — scan.js pushes column then edge in loop; SQLite autoincrement |
| Column `extra.type` / `extra.default` are the consumer keys | verified — scan.js:417–420 |
| 247 not on this branch → omit nullable/identity/pk | verified — main has no 247 |

**Smallest change-list**

| Change | File | Blast radius | Rows |
|--------|------|--------------|------|
| Contract constant for Table kind | `code_atlas/contract.py` | importers of contract; no behaviour alone | C2 |
| `_attach_columns` + optional limit/offset; clear Table source at standard | `code_atlas/tools/read_symbol.py` | MCP tool signature; existing read tests must tolerate additive kwargs/keys on Table only | G1,R1–R3,C*,AC* |
| Proving + AC tests | `tests/test_read_symbol_table_columns.py` | new file | AC1–AC6 |
| PLAN `read_symbol` row one clause | `docs/PLAN.md` | none beyond table cell | R7.6 |
| Task working doc + ledger/BACKLOG at finalise | this file · TOKEN_LEDGER · BACKLOG | docs | finalise |

**Recalled handles**

| Handle | Answer |
|--------|--------|
| `do-not-attest-past-the-payloads-resolution` | traced — `rg -n "columns\|CONTAINS\|__attach" code_atlas/tools/read_symbol.py` → only `_attach_params` at :155; no CONTAINS walk |
| `stamp-at-the-builder-not-the-wrapper` | traced — success path `_result` then `_attach_params` then `attach_next_tools` at :140–157; attach columns beside `_attach_params` |
| `stamp-evidence-with-the-tree-under-review` | does not apply because process/evidence provenance, not product payload shape |

`HANDLES: 3 recalled | 2 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

**Proving test:** `pytest tests/test_read_symbol_table_columns.py::test_table_read_returns_columns_in_ddl_order_without_source -q`

**Verification plan**

| AC | Layer | Plan |
|----|-------|------|
| AC1 | planted | Table + 3 Columns CONTAINS in non-alpha order; assert names order + empty source |
| AC2 | planted | assert no nullable/identity/primary_key keys on column rows |
| AC3 | planted | 5 cols, max_results=2; truncated/total_count/results_offset; page 2 |
| AC4 | planted | Table no edges → `no_indexed_columns`; offset past end with cols → empty page + total_count |
| AC5 | planted | Function payload key set unchanged (no columns keys) |
| AC6 | unit | documented tool count still 24 |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **Gate 2 status:** cleared (autorun; `u = 0`, `h == t + x`)

## Phase 3 — Execute

- **Branch:** `feat/248-table-columns-readable-from-table`
- **Worktree:** `/tmp/code-atlas-wt-248`
- **Proving test:** `tests/test_read_symbol_table_columns.py::test_table_read_returns_columns_in_ddl_order_without_source`

- **Verification sweep.** File axis ✅ (`contract.py` TABLE_KIND/COLUMN_KIND/CONTAINS; `read_symbol.py` `_attach_columns`; proving tests; PLAN clause + 059 prune). Behaviour axis: implemented-as-approved. Adapter untouched (R3). Tool count 24.

- **Design-conformance deviations:** none

- **Empirical output**

R6.5 red-before (production `read_symbol.py` lacked `_attach_columns`): asserting `columns` on a planted Table → **missing key**.


Ran at 8b72bfc9d80051a599dd914a008e8ba04821400b

```
$ .venv/bin/python -m pytest tests/test_read_symbol_table_columns.py::test_table_read_returns_columns_in_ddl_order_without_source -q --tb=line
.                                                                        [100%]
1 passed in 0.58s
```

Related module: `6 passed in 0.77s`

- **Golden/snapshot:** none
- **Design-invalidation:** none

## Phase 4 — Review

- **REVIEWER: OFF (`--no-reviewer`)** — no rule-book-grounded review of this diff exists.
- **CHALLENGER: ON** — [ticket-blind challenger](40c3707e-8adf-4711-b462-1c12ea8b5297). Raw ticket + `git diff origin/main...HEAD` excluding this file.
- **challenger result:** round 1 **NOT CLEAN** (ForeignKey CONTAINS inflated `total_count`/paging); fixed in `8b72bfc`. Round 2: **8/8 MET · CLEAN**.
- **Scope reconciliation:** file + behaviour axes clean after fix; PLAN 059 census prune is R7.6 budget collateral (disclosed).
- **Proving test would fail without the change?** Yes — R6.5 missing `columns` key.

Ran at 8b72bfc9d80051a599dd914a008e8ba04821400b

```
$ .venv/bin/python -m pytest tests/test_read_symbol_table_columns.py::test_table_read_returns_columns_in_ddl_order_without_source -q --tb=line
.                                                                        [100%]
1 passed in 0.53s
```

- **Clean?** `clean (challenger only — REVIEWER: OFF)`
- **Reviewed at** `8b72bfc9d80051a599dd914a008e8ba04821400b`
- **Reviewed files:** `code_atlas/contract.py`, `code_atlas/tools/read_symbol.py`, `tests/test_read_symbol_table_columns.py`, `docs/PLAN.md`, `docs/tasks/248_a-table-is-addressable-and-its-columns-are-not-readable-from-it.md` (exempt), `docs/LESSONS.md` (exempt), `docs/TOKEN_LEDGER.md`, `docs/BACKLOG.md`

## Phase 5 — Finalise

- **Stale-review guard:** product files unchanged since `8b72bfc9d80051a599dd914a008e8ba04821400b`; bookkeeping (LESSONS / TOKEN_LEDGER / BACKLOG / this file) is exempt.
- **Planned outward actions:**
  - [x] push branch — handover authorisation
  - [x] open PR via `gh` — handover authorisation — [#323](https://github.com/cuongdinhngo/code-atlas/pull/323)
  - [ ] merge — NOT authorised
- **Durable lesson:** when a container's `CONTAINS` children are heterogeneous (Column + ForeignKey), filter to the member kind **before** paging/`total_count` — otherwise AC3 lies.
- **Revert path:** revert the branch / close the PR without merge.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Classification is a proposal; human ratification deferred (`k = 0`). New type-2 handle `filter-contains-by-member-kind-before-page` — first sighting (`seen: 248`); not yet recurring so not in the n≥2 set.

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Notes |
|-------|---------------------|-------|--------|-------|
| Review | ticket-blind challenger | 1–2 | unmeasured (host does not surface usage) | reviewer OFF; r1 NOT CLEAN → fix → r2 CLEAN |

`LEDGER TOTAL: unmeasured · top cost driver: review/challenger (2 dispatch; reviewer OFF; main-loop unmeasured)`


## Decision log

| When | Decision | Why |
|------|----------|-----|
| t0 | reviewer off, challenger on | `/autorun 248 --no-reviewer` |
| refine | extend read_symbol; keep 24 tools | Scope working assumption + AC6 + 242 |
| refine | keep Table point; columns are answer | Scope + AC1 |
| design | order by edge id not `_EDGE_ORDER` | AC1 DDL order vs target_raw alpha |
| design | omit 247 fields | 247 not landed; R5.6 |

=======
