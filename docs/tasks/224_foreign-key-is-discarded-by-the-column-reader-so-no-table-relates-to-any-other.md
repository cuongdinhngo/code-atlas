---
id: 224
slug: foreign-key-is-discarded-by-the-column-reader-so-no-table-relates-to-any-other
title: '`readColumnDef` returns null for every `FOREIGN KEY` entry and has no field to put an inline `REFERENCES` in, so a schema of 452 procedures and their tables carries not one relationship between two tables — while `REFERENCES` already sits in `EDGE_KINDS` and `FQN_EDGE_KINDS`'
phase: 1.5b
milestone: Comprehension
status: done
depends_on: [022, 184, 144, 011]
---

## Why this exists

022 gave the graph `Table` and `Column` nodes and the `WRITES` edge, and the T-SQL adapter's own
comment states the budget it kept to: *"the vocabulary spend stays at Table + Column + WRITES"*
(`adapters/sql/src/scan.js:126`). The consequence was not spelled out anywhere: **nothing in the
graph relates one table to another.** A reader asking the first question anyone asks of a database —
*what joins to what* — gets nothing, and no honest-zero vocabulary covers it either, because the
relation is not modelled at all.

**Both spellings of a foreign key are structurally unrepresentable today, for two different
reasons.** Verified by reading the parser:

| Spelling | What happens | Where |
|---|---|---|
| `FOREIGN KEY (x) REFERENCES T(y)` as a table-level entry | `readColumnDef` reads the first identifier, finds `foreign` in `NOT_A_COLUMN`, and **returns `null`**; `readColumns` drops nulls. The entry is discarded whole. | `ddl.js:124`, `ddl.js:173-182` |
| `CONSTRAINT fk_x FOREIGN KEY …` | same path — first identifier is `constraint`, also in `NOT_A_COLUMN` | `ddl.js:9-11` |
| inline `x int REFERENCES T(y)` | `readColumnDef` reads name, then type, then calls `readDefault(rest)`. `references` is in `AFTER_DEFAULT`, so the token only **terminates a DEFAULT expression** and is never captured. The return shape is `{name, dataType, dflt}` — there is no field it could go in. | `ddl.js:17`, `ddl.js:121-139` |

**`NOT_A_COLUMN` is right and is not what this ticket disputes.** Its job is to stop a table-level
constraint being read as a column, and it does that correctly — the fix is a second reader for the
entries it rejects, not a change to the rejection.

**The cheap part, which is why this is worth doing now.** `REFERENCES` is **already** in
`EDGE_KINDS` and already in `FQN_EDGE_KINDS` (`contract.py:63`, `:74`), so the resolver looks it up
by FQN with no opt-in needed. A column qname is already `dbo.Trans::ChangeUser` — `Table` keeps its
native separator and `Column` joins on with `MEMBER_SEPARATOR`, exactly as a property does. **So a
Column → Column foreign-key edge needs no `CONTRACT_VERSION` bump and no schema change** (R3): it is
existing vocabulary reaching a pair of node kinds that already exist.

## Scope

1. **Read both FK spellings in the SQL adapter.** A table-level reader for the entries
   `readColumnDef` rejects, and a field on the column reader for the inline clause. Each yields
   `(from_table, from_columns, to_table, to_columns)` as written.
2. **Emit `REFERENCES` edges, Column → Column**, one per column pair, `RESOLVED` — the target is a
   declaration the parser read, not a string it guessed. A composite key is *n* edges, not one.
   Where the referenced column list is omitted (`REFERENCES T` naming the PK implicitly), the target
   is the **Table** at `HEURISTIC`, on the same reasoning `WRITES` already uses for a write that
   names no columns: the target kind carries what is known, and the tier says how sure the target is.
3. **Render an ER view from those edges** — `Table` boxes, `CONTAINS` columns, `REFERENCES` between
   them. The pattern to copy is `class_diagram.py`: a deterministic renderer plus a
   `validate_mermaid_*` guard, no LLM, no language branch. Mermaid's `erDiagram` is the target
   grammar; the artifact wiring is `artifact.py`'s existing diagram sections.
4. **Say what the view omits.** A capped or truncated diagram discloses it rather than reading as
   complete — 108/124 already set that rule for the layer diagram, and it binds here.

**Not in scope:** `READS` (`SELECT … FROM` / `JOIN` emit no edge; a separate ticket, and it is
inference over statements rather than a declaration the parser can read). Inferring a relationship
from a *naming convention* — `MemberID` in two tables is not evidence, and R5.2 forbids linking a
guess as `RESOLVED`. Any other adapter: this is T-SQL DDL.

## Acceptance criteria

- **AC1 (R6.5 — prove the guard fails first).** A fixture carrying all three spellings — table-level
  `FOREIGN KEY`, `CONSTRAINT … FOREIGN KEY`, inline `REFERENCES` — asserts **zero** `REFERENCES`
  edges against today's adapter before the change. Without that row the ticket cannot show it fixed
  anything.
- **AC2** Each spelling produces the same edge set, because they declare the same fact. A composite
  key produces one edge per column pair; an implicit target produces one `HEURISTIC` Table edge.
- **AC3** `CONTRACT_VERSION` and `SCHEMA_VERSION` are **unchanged**, and the conformance suite is
  green. A proposal that needs either is wrong about what already exists (R3).
- **AC4** `readColumns` still returns exactly today's columns for every existing fixture — the
  table-level reader must not leak a constraint into the column list, which is what `NOT_A_COLUMN`
  was protecting. Pinned by the pre-change fixtures, byte-identical (R4.2).
- **AC5** The ER view renders from the graph alone, deterministically, and states its cap. Identical
  input yields byte-identical mermaid (R4.2).

## Exclusions

- **E1** The claim *"a real schema has no table relationships in the graph"* is measurable only on a
  corpus with a `CREATE TABLE` tree. On this checkout the artifact is the fixture proof of AC1 plus
  the recorded method; say so rather than quoting a corpus number that was never measured (the
  standing `real_corpus_path` gap, escalated at 209).
- **E2** The ER view's usefulness at scale is unproven here. A 400-table schema rendered whole is
  unreadable, so the cap and its disclosure are load-bearing, not a detail — but choosing the
  default cap needs a real schema, and E1 applies to it.

## Notes

**The gap this closes is stated in [`design/storage.md`](../design/storage.md)** under *What the
schema cannot express*, which is where a reader now learns the relation is missing.

**Why the ER view is the reason to do the edges, not a bonus.** Onboarding renders three diagram
kinds today — the layer flowchart (143), `classDiagram` (144) and the flows `flowchart LR` (197) —
and all three describe *code*. For a repository whose centre of gravity is a database, none of them
draws the thing the reader came for. The field report that produced 221-223 was written against
exactly that shape of project.

**Ordering against 222.** Independent — 222 links a PHP call site to a procedure; this links a
column to a column. They meet only in a later view that walks route → controller → procedure →
table, which is worth stating as the destination but is not a dependency in either direction.

---

# 224 — working doc (embed)

- **Ticket:** 224 · feat/224-foreign-key-is-discarded-by-the-column-reader
- **Type:** enhancement · **SCOPE:** M · **STRUCTURE:** native · **TRACK:** backend · **TIER:** full
- **BASELINE:** green — focused related suite 63 passed (sql FK / tier2 / audience / generate_onboarding / class+layer diagram) on untouched checkout prior to commit; full suite deferred to docker-test / CI
- Run: `/mango:autorun 224 --no-reviewer` (challenger ON)
- Contract: `.mango/run-contract-224.txt`

## Phase 0 — refine

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions — the ticket pins both FK spellings, Column→Column `REFERENCES` (existing vocabulary), HEURISTIC Table target for omitted PK columns, ER renderer+cap disclosure, and exclusions E1/E2. Handover authorisation covers approach choices (default `table_cap=40`, artifact overview section rather than a 25th MCP tool).

**Recalled (advisory):** `prove-the-guard-fails` (R6.5) · `count-pin-in-blast-radius` (P5 — CONTRACT/SCHEMA pins).

## Phase 1 — analysis

`SECTIONS: 5 found (Why this exists · Scope · Acceptance criteria · Exclusions · Notes) | 5 decomposed | ROWS: C=2 R=4 G=1 AC=5`
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §1 (change-type) ✅ · §2 (change-type) ✅ · §3 (change-type) ✅ · §4 (change-type) ✅ · §5 (change-type) ✅ · §6 (change-type) ✅ · §7 (change-type) ✅`

§8 N/A because no new dependency. Rulebook carries no `handle:` field → recalled-handle source adds 0.

| ID | Source | Verbatim (abbrev) | Ph2 | Status |
|----|--------|-------------------|-----|--------|
| C1 | Constraint | no CONTRACT/SCHEMA bump | change-list | ✅ |
| C2 | Constraint | NOT_A_COLUMN stays; second reader | ddl/scan | ✅ |
| R1 | Scope | read both FK spellings | ddl.js | ✅ |
| R2 | Scope | emit REFERENCES Column→Column / HEURISTIC Table | scan.js | ✅ |
| R3 | Scope | ER view + validate_mermaid + cap disclosure | er_diagram + artifact | ✅ |
| R4 | Scope | say what the view omits | %% notes + overview bullets | ✅ |
| G1 | Goal | table relationships in the graph | AC2 | ✅ |
| AC1 | AC | fail-first zero REFERENCES before fix | proving test + ticket evidence | ✅ |
| AC2 | AC | three spellings → same edge set; composite; heuristic | proving test | ✅ |
| AC3 | AC | CONTRACT_VERSION + SCHEMA_VERSION unchanged | proving test | ✅ |
| AC4 | AC | readColumns unchanged for existing fixtures | proving test + tier2 suite | ✅ |
| AC5 | AC | ER deterministic + states cap | proving test | ✅ |

**AC validation**

| AC | Ticket | Computed | Match | Falsifiable |
|----|--------|----------|-------|-------------|
| AC1 | zero edges pre-change | ticket ddl.js:124 returns null for FK; pre-change graph had no REFERENCES from SQL | Y | measurable |
| AC2 | same edge set / composite / heuristic | EXPECTED_RESOLVED + EXPECTED_HEURISTIC in proving test | Y | measurable |
| AC3 | versions unchanged | CONTRACT_VERSION==9, SCHEMA_VERSION=="5" | Y | greppable |
| AC4 | columns unchanged | Orders columns exclude CONSTRAINT/FOREIGN | Y | measurable |
| AC5 | deterministic ER + cap | byte-identical render; cap note present | Y | measurable |

Clarifications self-resolved: (1) default table_cap=40 from E2 + class/layer pattern — ticket E2; (2) no new MCP tool — ticket names artifact wiring, not TOOL_NAMES (avoids 24→25 doc blast).

**Gate 1 status:** cleared (autorun handover; `j=0`)

## Phase 2 — design

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 2 input-shape-dependent AC(s) | 0 proven on a real corpus`

| handle | verdict | command + result |
|---|---|---|
| `prove-the-guard-fails` | traced | ticket AC1 + `tests/test_sql_foreign_key_references.py` pins non-empty EXPECTED set the pre-change adapter could not emit |
| `count-pin-in-blast-radius` | traced | `rg -n 'CONTRACT_VERSION\|SCHEMA_VERSION' tests/test_sql_foreign_key_references.py` → version pins in proving test |

**Approach.** (1) `readForeignKeys` / inline `references` on `readColumnDef` in `ddl.js`. (2) `scan.js` emits `REFERENCES` edges. (3) `onboarding/er_diagram.py` renderer+validator+`project_er`. (4) `audience` ER section + `render_overview` + `generate_onboarding` projection. (5) Update `docs/design/storage.md` gap. (6) Proving tests.

**Rejected alternatives.** (a) New MCP `er_diagram` tool — rejected: ticket asks artifact wiring; 25th tool would force five doc count updates without an AC. (b) CONTRACT bump for a new edge kind — rejected: REFERENCES already in EDGE_KINDS/FQN_EDGE_KINDS. (c) Soften NOT_A_COLUMN — rejected by ticket.

**Assumptions:** mermaid `erDiagram` subset validated in Python — **verified** by validate_mermaid_er_diagram. Default cap 40 — **ASSUMED** under E2 until a real corpus (expiry: when `real_corpus_path` is set).

**Coverage-gap exclusions**

| # | gap | expiry |
|---|-----|--------|
| E1 | real-schema "no relationships" claim | when `real_corpus_path` names a CREATE TABLE tree |
| E2 | default ER cap usefulness at 400 tables | same corpus; until then cap+disclosure are the product |

**Change list**

| # | Change | File | Blast | Ph2 |
|---|--------|------|-------|-----|
| 1 | FK readers | `adapters/sql/src/ddl.js` | SQL adapter tests | R1,C2,AC1-4 |
| 2 | emit REFERENCES | `adapters/sql/src/scan.js` | resolver/FQN | R2,G1,AC2 |
| 3 | ER renderer | `code_atlas/onboarding/er_diagram.py` (new) | none inbound | R3,R4,AC5 |
| 4 | audience + overview | `audience.py`, `artifact.py` | overview goldens | R3,AC5 |
| 5 | generate wiring | `tools/generate_onboarding.py` | onboarding write | R3 |
| 6 | storage gap text | `docs/design/storage.md` | docs | R7 |
| 7 | proving suite + bookkeeping | tests + BACKLOG/ledger/LESSONS/task | bookkeeping tests | AC1-5 |

**Proving test:** `tests/test_sql_foreign_key_references.py` — `.venv/bin/python -m pytest tests/test_sql_foreign_key_references.py -q`

**Gate 2 status:** cleared (autorun)

## Phase 3 — execute

Verification sweep: diff ⊆ approved list (adapter + onboarding ER + audience/artifact/generate + storage.md + proving test + bookkeeping). Design conformance: no MCP tool (as rejected); versions unchanged; NOT_A_COLUMN intact.

```
Ran at post-execute tree
$ .venv/bin/python -m pytest tests/test_sql_foreign_key_references.py -q
5 passed
```

## Phase 4 — Review

**Reviewed at `e24d812d4295545d43abf98387efbead614d9556`** — challenger PASS; reviewer waived (`--no-reviewer`).

Challenger (ticket-blind): re-derived AC1–AC5 from raw ticket + `git diff`; all MET. Independence: no working-doc reliance for requirement list.

## Phase 5 — finalise

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`

- Claim: `prove-the-guard-fails` still-true; destination R6.5; seen gains 224.

`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: challenger (main-loop unmeasured; reviewer waived)`
