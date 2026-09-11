---
id: 194
slug: default-filled-column-defect-class-query
title: 'One call for "which writers of this table omit this column, and what is its DEFAULT?" — the query that makes tier 2 pay'
phase: 2
milestone: M9+
status: done
depends_on: [022]
---

## Why this exists (field retro round 12 §15)

Tier 2 puts column write-sites in the graph. This ticket is the **question that spends them**, and the
retro names it verbatim:

> The query that would have solved TKT-1026 in one call:
> **"Which writers of `LedgerTrans` omit `ChangeUser`, and what is that column's DEFAULT?"**
> Answer: *all 20 `Insert_*_Trans*` procs omit it; `DEFAULT (user_name())`.*
> I needed four grep passes, a purpose-built `dbsweep.php` that maps each `INSERT` to its enclosing
> proc, and two `sqlcmd` round-trips to establish that.

And the class, also verbatim:

> **TKT-1020, TKT-1027, TKT-962 and TKT-1026 are one defect class** — *a column whose value comes
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

---

## Session status

- **KEY:** 194 · **work_doc_mode:** embed · **Phase:** 2 design — complete; Gates 0/1/2 closed.
- `TRACK: backend` · `TIER: full`. Run arg: *"with skipped review"* — both seats off.
- **Approach chosen by the agent** on the maintainer's hand-back (*"choose the best approach"*).
  The ticket offered two homes and design rejected both; see *Rejected alternatives*.

## Phase 0 — refine

`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

Three, all how-decisions the ticket or the code settles: **(a)** where the predicate lives (the
ticket names two candidates and asks design to choose — *Scope 1*); **(b)** whether it takes one
column or scans a table (AC1 names T *and* C, AC3 asks for the class to be *flagged*, so both);
**(c)** what an empty answer means (AC2 fixes it: *unmeasured*, never *zero*). No want-decision
survived: the ticket is fully specified as to intent, and every open point is answerable from the
ticket text or the code.

## Phase 1 — analysis

`PREMISE: 14 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`

Resolved: `code_atlas/architecture_rules.py:109` (`check_architecture_rules`), tasks 022 and 184,
rules R4, R4.2, R5.6, R6.3, R6.7, R1.2, R1.8, the contract words `Table`/`Column`/`WRITES`, and
`code_atlas/main.py`'s `TOOL_NAMES`. Ambiguous, surfaced: the four anchor tickets (TKT-1020, 1027,
962, 1026) are named as evidence from a repo outside this checkout.

`RECALL: 8 claim(s) surfaced | 0 by symbol | 7 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

The change **introduces a new core module other modules import** — recall trigger 2 — so the type-2
surface is wide: `count-pin-in-blast-radius` (085…184, 022) · `derived-not-listed-invariant` ·
`prove-the-guard-fails` · `one-rule-for-every-subject-slot` (R1.8) ·
`do-not-attest-past-the-payloads-resolution` (R5.6) · `route-must-answer` (R5.4) ·
`fixture-shape-begs-the-question` (R6.3). By area: `empty-seam-inputs-masquerade-as-missing-data`.

`SECTIONS: 5 found | 5 decomposed | ROWS: C=3 R=3 G=1 AC=4`

Sections: *Why this exists* · *Scope* (with *Explicitly not in scope*) · *Constraints* ·
*Acceptance criteria* · *References*. `STRUCTURE: native` — the ticket carries `Scope`,
`Constraints` and `Acceptance criteria` headers the schema maps.

| ID | Source | Verbatim (abridged) | Interpretation | Status |
|---|---|---|---|---|
| G1 | round 12 §15 | *"the query that would have solved TKT-1026 in one call"* | one call replaces four greps, a `dbsweep.php` and two `sqlcmd` round-trips | open |
| C1 | Constraints | R4/R4.2 — deterministic | identical graph ⇒ identical rows, in a fixed order | open |
| C2 | Constraints | R5.6 — silence is not evidence | a table with no recorded writers is *unmeasured* | open |
| C3 | Constraints | R6.3 — a committed re-runnable reporter | the judgement ships as a test, not a session run | open |
| R1 | Scope 1 | *"a rule shape over the tier-2 graph"* | a predicate over table/column/writer | open |
| R2 | Scope 2 | *"names the writers by qname … a ratio, not a bare list"* | omitters **and** the total, not one number | open |
| R3 | Scope 3 | *"honest emptiness"* | C2 at the payload | open |
| AC1 | AC | writers-omitting-C, total writers of T, C's DEFAULT | the three fields of one answer | open |
| AC2 | AC | *"answers unmeasured, not zero — pinned by a test"* | its own test, not an assertion inside another | open |
| AC3 | AC | *"given a fixture reproducing the shape, the rule flags it"* | a **scan**, so the column argument is optional | open |
| AC4 | AC | *"no `contract_version` bump beyond 022's"* | the graph already holds everything needed | open |

### Clarifications

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

1. **Which of the ticket's two homes?** *Self-resolved — neither.* See *Rejected alternatives*; the
   ticket asks design to choose and design's answer is that both candidates are the wrong shape.
2. **One column or a scan?** *Self-resolved: both.* AC1 names T and C; AC3 asks for the class to be
   flagged from a fixture, which requires a scan. One optional argument covers both.
3. **Is a "writer" a routine or a file?** *Self-resolved: a routine* — `WRITES.source_qname` is the
   enclosing proc/function/trigger (`adapters/sql/src/scan.js`, `writes()`), and round 12 §15's
   answer names procs (*"all 20 `Insert_*_Trans*` procs"*), not files.

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) ✅ a new tool module reads the store through its existing API and adds no language branch · §2 (change-type) N/A (no adapter touched) · §3 (change-type) ✅ AC4 — no vocabulary moves, so no bump · §4 (change-type) ✅ fixed ordering, no network · §5 (change-type) ✅ R5.6 is AC2, the ticket's own headline constraint · §6 (change-type) ✅ proving test plus the parity matrix · §7 (change-type) ✅ four documented tool counts are derived, not listed, and PLAN pays for its row by a prune · §8 (change-type) N/A (no dependency added)`

The rule book carries no `handle:` annotations, so the recalled-handle source adds no section.

### Blast radius

A 23rd tool is the widest mechanical surface in this repo, and every part of it is a count pin —
which is exactly the class `count-pin-in-blast-radius` reached recurrence 7 on in 022. This trace
greps **the invariant** (what derives from `TOOL_NAMES`), not the spelling.

`TRACK: backend — 0/13 touched files under UI paths`
`SCOPE: M` — one new module and a wide but entirely mechanical perimeter; no new vocabulary, no
adapter change, no store change.

## Phase 2 — design

### Approach

**One new MCP tool, `check_column_defaults`, rule-shaped.** It takes a `table` and an optional
`column`; with no column it scans every column of the table that declares a `DEFAULT`, which is what
makes AC3's *"the rule flags it"* a scan rather than a lookup. Per column it returns the declared
`default`, the total writer count, and — only when they are measurable — the writers that **named**
the column and the writers that **omitted** it. Everything it needs is already in the graph (AC4:
no bump).

**Honest emptiness is the payload's shape, not a note on it (C2 / AC2).** A writer that named no
columns reaches the table through a `WRITES` onto the `Table` itself (022's discriminator), so it is
**`unmeasured`** for every column — it may or may not set `ChangeUser` and the graph cannot say. Such
a writer is listed under `unmeasured`, never under `omitted_by`. A column whose table has **no**
recorded writers carries `status: "table_has_no_writers"` and **omits the `omitted_by` key
entirely** — an empty list there would read as *"nobody omits it"*, which is exactly the zero R5.6
forbids (061's omit-when-empty, used for its honesty rather than its byte count).

### Rejected alternatives

1. **A new rule kind inside `check_architecture_rules`** — the ticket's first candidate.
   **Rejected:** that engine's whole vocabulary is path-set reachability — `sources` and `forbidden`
   are path globs and `Violation` carries `source_file`/`forbidden_file`/`via_qname`. This predicate
   has no file in it. Fitting it in means a second rule shape inside one dataclass, a second
   violation shape inside one outcome, and one tool whose payload means two different things.
2. **A parametrisation of the existing engine** — the ticket's second candidate. **Rejected for the
   same reason**, one step weaker: there is no parameter that turns a path-reachability check into a
   node-shape predicate.
3. **Extend `find_references` / `find_callers` to walk `WRITES`.** Rejected: the headline question is
   a *set difference* (writers of T minus writers of C) plus a node attribute (the DEFAULT). No
   existing tool composes that, and widening `CALLER_KINDS` would change every existing caller
   answer on a SQL graph.
4. **A `code_atlas/column_defaults.py` engine with a thin tool wrapper**, mirroring
   `architecture_rules.py`. **Rejected by R1.2:** that split exists there because the engine carries
   a config loader, a rule-file format and a digest. This predicate is ~60 lines with one consumer;
   a second module for it is the speculative split the rule forbids.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| 1 | `WRITES.source_qname` is the enclosing routine, not the file | **verified** — `scan.js` `writes()` uses `current.qname`, falling back to the path only outside any routine |
| 2 | A `Column` node's `extra` reaches the tool as a JSON string, not a dict | **verified** — 022's integration test had to `json.loads` it |
| 3 | Adding a tool needs no store change | **verified** — `edges_by_target` / `edges_by_source` / `nodes_by_qualified_names` cover it |
| 4 | Every perimeter file that must change is reachable from `TOOL_NAMES` | **verified** — the H-a trace below enumerates all 17 readers |

### Change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| CL-1 | the tool | `code_atlas/tools/check_column_defaults.py` (new) | none — it reads the store's existing API | R1, R2, R3, AC1, AC2, AC3 | 1/1 |
| CL-2 | import · `TOOL_NAMES` · registration | `code_atlas/main.py` | **the single invariant the whole perimeter derives from** | R1 | 1/1 |
| CL-3 | description + `which_tool` route | `code_atlas/tools/prompts.py` | `test_tool_descriptions` asserts `set(descriptions) == set(TOOL_NAMES)`; R5.4 needs the route to answer | R1 | 1/1 |
| CL-4 | `INVOKERS` entry + a per-language `Expect` ×3 | `tests/contract/tool_parity.py` | 185/186 — a tool with no declaration is a special case, which is the thing parity forbids | AC1 | 4/4 |
| CL-5 | tool count, tool row, **unbatched row with a reason >20 chars** | `docs/TOOLS.md` | `test_batched_subject_sweep` reads the section and the table | R2 | 3/3 |
| CL-6 | tool count ×3 | `README.md` | `test_documented_tool_count` derives it from `TOOL_NAMES` | — | 3/3 |
| CL-7 | tool count ×1 | `AGENTS.md` | same test **and** the tier-1 token budget | — | 1/1 |
| CL-8 | one probe row | `docs/runbooks/tool-recognition-probe.md` | `test_recognition_probe_protocol` — intended tools must equal the surface | — | 1/1 |
| CL-9 | one tool-table row | `docs/PLAN.md` §12 | **PLAN has 8 tokens of headroom** — the row is paid for by a prune (R7.6) | R1 | 1/1 |
| CL-10 | **the proving test** | `tests/test_check_column_defaults.py` (new) | — | G1, AC2, AC3 | 1/1 |
| CL-11 | status, spend row, claims | `docs/BACKLOG.md` · `docs/TOKEN_LEDGER.md` · `docs/LESSONS.md` | `test_backlog_bookkeeping` | C3 | 1/1 |

### Recalled handles — every one answered

`HANDLES: 7 recalled | 5 traced (command + result) | 2 does not apply (reason) | 0 unanswered`

| Handle | Command | Result → what it changed |
|---|---|---|
| `count-pin-in-blast-radius` | `grep -rln "TOOL_NAMES" code_atlas/ tests/` | **17 readers.** 022 reached recurrence 7 by grepping a *spelling*; this trace greps **the invariant** — everything that derives the tool surface — and that is the whole perimeter. Twelve of the seventeen are derived and will fail loudly on their own; the five that need an authored entry are CL-2 … CL-5 and CL-8. |
| `derived-not-listed-invariant` | `sed -n '25,40p' tests/test_documented_tool_count.py` | The four documented counts are **already derived** from `len(TOOL_NAMES)` and pinned; there is no new hand-kept list to add, and CL-5..CL-8 are edits to counts a test owns. |
| `one-rule-for-every-subject-slot` | `grep -n "R1.8" docs/ENGINEERING_RULES.md` | R1.8 binds when two or more call sites decide the same thing. This tool has **one** subject slot (`table`) and one optional filter (`column`), resolved in one place; no second call site decides it. |
| `do-not-attest-past-the-payloads-resolution` | `grep -n "^REASON_" code_atlas/tools/nav_result.py` | The existing vocabulary already carries every empty case this tool has (`not_indexed`, `no_such_symbol`, `no_matches`, `relation_unmodelled_for_language`); the per-column `unmeasured` state is a **status on the row**, so the payload never attests past what the graph resolved. |
| `route-must-answer` | `grep -rln "which_tool" code_atlas/` | `prompts.py` carries the recognition map, so CL-3 is one edit, not two — a route added without a description would fail `test_tool_descriptions`. |
| `fixture-shape-begs-the-question` | — | **does not apply because** the proving test asserts the *set arithmetic* over a fixture whose shape is round 12 §15's, published in the retro before this code existed; it is not a shape chosen to make this implementation pass. |
| `empty-seam-inputs-masquerade-as-missing-data` | — | **does not apply because** this tool has no seam and no configuration knob: it reads the graph directly, so there is no unconfigured state for an empty answer to be confused with. |

### Rule compliance

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) ✅ one module, no language branch, store reached through its API · §2 (change-type) N/A (no adapter touched) · §3 (change-type) ✅ AC4 — the graph already holds every fact · §4 (change-type) ✅ sorted qnames throughout, no network · §5 (change-type) ✅ R5.6 is the ticket's headline, and it is the payload shape · §6 (change-type) ✅ proving test plus three parity columns · §7 (change-type) ✅ counts are derived; PLAN pays for its row by a prune · §8 (change-type) N/A (no dependency added)`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|---|---|---|---|---|
| G1 / AC1 | integration | `tests/test_check_column_defaults.py` — index → tool | authored | ✅ |
| AC2 | integration | its own test, per the AC's *"pinned by a test"* | authored | ✅ |
| AC3 | integration | the scan over a fixture of round 12 §15's shape | authored | ✅ |
| AC4 | logic | `CONTRACT_VERSION == 9` unchanged, asserted | n/a | ✅ |
| C1 | logic | two runs over one index compared byte-for-byte | n/a | ✅ |
| C3 | manual-recorded | the reporter is a committed test, not a session run | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

No AC here is input-shape-dependent: every one asserts an exact set or an exact string, not that an
answer is *sensible*. The corpus question 022 deferred is about the **scanner's** extraction, and it
stays 022's; this ticket asserts arithmetic over whatever the graph holds.

### Proving test

`tests/test_check_column_defaults.py::test_the_one_call_answers_round_12s_question` — builds round
12 §15's shape and asserts the single call returns the omitting writers, the total, and
`(user_name())`. Fails pre-change because the tool does not exist.

`.venv/bin/python -m pytest tests/test_check_column_defaults.py -q`

### Rollback + porting

Revert the branch: the tool leaves `TOOL_NAMES` and every derived count follows it back to 22. One
repo; no porting.

`SCOPE: M` — confirmed from Phase 1.

`BASELINE: green — 2572 passed, 1 skipped in 152.27s`

Ran at `cfd6efb6cd8ab4d633de0406c2bfc9c113c23355` — this branch's first commit, before any code.

```
scripts/docker-test.sh — at the branch point, NOT the tree under review
All checks passed!
2572 passed, 1 skipped in 152.27s (0:02:32)
```

Not written as a `$ `-prefixed empirical-output record: that shape asserts *this is the tree under
review*, and a baseline is by definition the tree before the change (see the type-3 signal 022 filed).

## Phase 3 — execute

**Two deviations from the approved change list, both recorded.**

**1. CL-4's perimeter was five authored entries; it was eleven.** The `HANDLES:` trace grepped
`TOOL_NAMES` — the invariant, as 022's claim demanded — found 17 readers and predicted five would
need an authored entry. Twelve did fail on their own, exactly as predicted. The six extra were
`tests/test_limit_clamp_visible.py` (`== 10`), `tests/test_mcp_server.py`'s `TOOL_NAMES` tuple pin,
`tests/test_total_count_semantics.py`'s emitter list **and** its parametrised truncation case (which
needed a SQL seed no PHP node could stand in for), and — the two that were not in the `TOOL_NAMES`
family at all — `assert len(core_modules()) == 74` in `test_core_is_language_agnostic.py` and
`test_sql_confinement.py`. **Adding a file under `code_atlas/` moves a different invariant from
adding a tool, and this change moved both.** Claim `194-C1`.

**2. CL-9 was dropped on evidence.** It planned a row in `docs/PLAN.md` §12's tool table, paid for by
a prune against PLAN's 8 tokens of headroom. A count first: PLAN mentions **18 of 23** tools and
already omitted 4 of the 22 that existed before this ticket, so its table is not the surface —
`docs/TOOLS.md` is, and `tests/test_documented_tool_count.py` pins it. Adding the row would have
spent budget maintaining a list nothing maintains. Claim `194-C4`.

**The proving test was red first, on a real false negative (R6.5).** `writers_total` was computed
over the *defaulted* columns' writers only, so a routine writing only undefaulted columns never
entered the population — and on the fixture `omitted_by` came back **empty**, i.e. the tool answered
*"no writer omits `ChangeUser`"* about a table where two of four do. The denominator is the
population that writes the table, not the subset the filter selected. Claim `194-C2`.

**Parity, measured not assumed.** PHP and TS declare `not_applicable_by_language` — neither language
declares a table, so no subject of this tool exists in it, which is a different fact from a relation
an adapter *could* emit and does not. SQL **answers**, on `dbo.Audit`, the one fixture table that
declares a `DEFAULT`; nothing writes it, so the answering path is the `table_has_no_writers` arm —
the honest one — rather than a modelled zero.

### Delta-green

Ran at `f3e82ca66a84cecf633341bf3037f676bd240520` — the tree under review.

```
$ scripts/docker-test.sh
All checks passed!
2591 passed, 1 skipped in 170.59s (0:02:50)
```

**+19 against the 2572 baseline, no new failure, the same one structural skip.** The 19 are the 7
proving tests, 3 parity cells, and 9 across the perimeter guards that now cover a 23rd tool.

## Phase 5 — finalise

`CLAIMS: 5 claim(s) from 1 lesson entr(ies) | T1=0 T2=4 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 7 candidate(s) checked | 7 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: execute (main-loop)`

Both recurring handles are already binding — `count-pin-in-blast-radius` → AGENT_BRIEF P5 (now at 8,
with 194 adding *a change can move more than one invariant*) and `prove-the-guard-fails` → R6.5 —
so each sighting is a `seen:` bump and nothing is proposed. The three new handles are at recurrence 1
and propose nothing by design.

### DISCLOSURE

**Nobody reviewed this.** Both seats off, waived by the run arg *"with skipped review"* and recorded
`off` in the RUN CONTRACT. Clean here means *clean, nobody looked*.

- **The approach was the agent's, on the hand-back** (*"choose the best approach"*). It **rejects
  both homes the ticket named** for the predicate. That is the judgement to check first: if a
  reviewer thinks the rule engine should have carried it, the whole module is the wrong shape.
- **The tool is proven on authored fixtures only.** Its arithmetic is exact so no AC is
  input-shape-dependent, but nothing here says whether real T-SQL produces write-sites the arithmetic
  reads correctly — that is 022's deferred AC7 and it stays deferred.
- **`writers_total` counts routines the graph recorded, and the graph is only as complete as the
  scanner.** A table written through `MERGE`, through dynamic SQL, or from a file outside the index
  contributes nothing, and the ratio will read as confident. The `unmeasured` population covers only
  writers the scanner **parsed and could not attribute to a column** — not writers it never saw.
- **`_WALK` is 10,000 edges per subject.** A table with more writers than that is silently truncated
  in the arithmetic; no test exercises that ceiling.
- **`column` accepts a bare name and qualifies it against the table.** A column whose name contains
  `::` would be mis-parsed; T-SQL cannot produce one, so this is reasoned, not tested.
- **PLAN's tool table is left inconsistent, deliberately** — it now names 18 of 23. That is recorded
  as claim `194-C4` rather than fixed, because fixing it is a docs ticket of its own.
- **`call-ceiling`, `token-budget` and `LEDGER TOTAL` are unknown/unmeasured** — this host surfaces
  no usage block.
