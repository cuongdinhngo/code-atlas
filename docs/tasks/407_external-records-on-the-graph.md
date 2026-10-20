---
id: 407
slug: external-records-on-the-graph
title: 'A record written about code (a QA ticket, an incident) cannot be attached to a symbol, so `impact` stops at code and the consumer keeps a copy that goes stale'
phase: 2
milestone: Trust
status: todo
depends_on: [382, 384, 385]
---

## Why this exists

The anchor repo keeps a domain wiki built from verified QA tickets. Each ticket has one JSON record
in the repo that already names the code it is about: qnames around the fix lines (628 of 993
records) and tables (137 of 993). The wiki answers two questions from that join that the graph
cannot:

- **"I am changing table `dbo.T`: what must be re-tested?"** The answer is the tickets whose fix
  touched it, each a behaviour a user saw break in one region. `impact` stops at code, so it names
  the procs and pages but none of that behaviour.
- **"Who writes this table, and which tickets changed it?"** The anchor generates one Markdown page
  per table (57 pages) by copying `find_references` writers out of the index and joining them to the
  records. The copy is frozen at its build revision, and 383 measured 22 of 57 writer claims changed
  within two weeks, almost all because new migrations added writers.

The consumer owns the records and their meaning. What it lacks is a place on the graph to hang them,
so every join is rebuilt by hand, outside the index, and dates the moment it is written. 385 set the
precedent: a declared data file the index reads (the route table) rather than a fact the adapters
parse.

## Scope

1. **Declared record sources.** The project config names one or more globs of JSON files. Each record
   has `id`, `title`, an optional `url` and `kind` (free text: `ticket`, `incident`, `adr`…), and
   `targets: [qname]`. The mapping from a consumer's own shape (the anchor nests its targets in two
   lists under one key) is either a small declared field map or a consumer-side export; decide at design.
   Nothing in the core names a tracker or a language (R1.1).
   **A source may be untracked or gitignored** (added 2026-10-20). The anchor plans to commit only
   the records' evidence and the LLM-written text, and to regenerate the code targets into a
   gitignored export on every pipeline run, so the declared file is never in `git ls-files`. The
   index's untracked-file skip (092) must not apply to record sources.
2. **Built with the index.** Records are read at build and on incremental refresh when a declared file
   changes, so the answer is always at the index's revision. A record is a node; each target is an
   edge to the symbol, at a tier that says it was declared, not resolved.
3. **Surfaced where the question is asked.** `impact` lists the records attached to any node in the
   radius, and `find_references` / `read_symbol` on a target list its records. Opt-in or always-on is
   a design decision; the tool count stays the same.
4. **Dangling targets are reported.** A target qname the index no longer holds (removed, renamed) is
   listed by the build and in `get_index_status`, never dropped silently. For the consumer this is a
   free stale signal beside 384's `--changed-since`.
5. **An exclusion list.** The consumer names records that must never be served (the anchor keeps open
   security weaknesses off every page; their ids live in a gitignored file). An excluded record is
   absent from every answer, and only its count shows in status.

## Assumptions to prove at design

- **A table defined in many files can be a target.** Today `impact` on such a table answers
  `subject_ambiguous` and walks nothing: on the anchor a typical table is declared in the SSDT tree,
  in the baseline migration and again in a later migration. Most of the anchor's tables are like this, so a record on a table needs a
  defined attachment (every definition, or a canonical one). This may need its own ticket first.
- **The radius crosses PHP into T-SQL.** 386 links PHP `EXEC` strings to procedures; whether
  `impact` from a PHP method reaches the tables those procs write, and so the records on them, is
  measured on the anchor before AC2 is promised.
- **Record count stays small next to symbols.** The anchor has about 1,000 records and 174,000 symbols.
  The build-time overhead is recorded.

## Acceptance criteria

- **AC1:** with a declared source, `find_references` on a target symbol lists the records attached to
  it, each labelled as declared, and a build at a later revision reflects edits to the record files
  with no consumer step.
- **AC2:** `impact` on a symbol lists the records attached anywhere in its radius, with the node that
  carried each one.
- **AC3:** a record whose target no longer exists is reported by the build and by `get_index_status`
  (count plus the first ids), and appears in no answer as if it were attached.
- **AC4:** an excluded record id appears in no tool answer and no CLI output; status reports only how
  many were excluded.
- **AC5:** an index with no declared source answers byte-identically to one built before this task.
- **AC6:** a declared source that git ignores is read at build; rewriting it (same ids, new targets)
  changes the records on the next refresh with no code change, and `rules_stale` fires until then.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 407 · **work_doc_mode:** embed · **Current phase:** 3 execute · **Next action:** review. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · Run mode: `autorun 407 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/407-external-records-on-the-graph` from `main` (`4c3a3659`, #96 merged). Contract `.mango/run-contract-407.txt`.
  RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 25 unresolved surfaced | 3 want-decision asked | 22 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `impact`, `find_references`, `read_symbol`, `get_index_status`, 384's `--changed-since` and 385's route
table (`code_atlas/routes.py`) resolve. Ambiguous: the anchor's fragment files live in a private client repo this run
may not read (the read was refused), so their shape is taken from the ticket's own description.
Recall: `widen-every-query-that-shares-the-page` (362-C1) — `find_references` builds its page from several reads, each
must carry the records; `an-absent-reason-is-ok` (396-C1) — `impact`'s envelope has no `reason`, so a rules-stale
relabel on it must read absence as `ok`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 44,959 tokens) added H14–H22 and W3.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the sources are declared | how | a `records` block in the `CA_INDIRECTION_RULES` file — 385's `routes` home, so the rules digest and 396's reapply cover the record files (Why: "385 set the precedent") |
| H2 | block shape | how | `sources` (repo-relative globs, contained), `fields` (dotted paths for `id`/`title`/`url`/`kind`, a list for `targets`), a constant `kind`, an optional `exclude` file — Scope 1 "a small declared field map"; 397's dotted `columns` |
| H3 | one file, how many records | how | an object is one record, a list is many — Scope 1 covers both a per-ticket file and a consumer-side export |
| H4 | what a target names | how | a stored qname or an indexed file; exact first, then a unique case-insensitive `Table` match (215's writer rule) |
| H5 | the declared label | how | every record row says `tier: HEURISTIC`, `rule: true` — Scope 2 "a tier that says it was declared"; R5.2 |
| H6 | which tools | how | `find_references` and `read_symbol` list the subject's records; `impact` lists records on its seeds (walked, ambiguous or twinned) and rows, each with `via` — Scope 3 |
| H7 | opt-in or always-on | how | always-on once a block is declared (declaring it is the opt-in); omitted when none attaches — 385's `routes` field on `impact`; AC5 |
| H8 | dangling | how | a (record, target) pair naming nothing indexed; counted, first 10 listed, never attached — 385's `routes_unresolved`; AC3 |
| H9 | exclusion | how | excluded ids are dropped at load, before any other step, never stored; only the count is — Scope 5, AC4 |
| H10 | bad record data | how | an unreadable file or a record with no `id` is skipped and counted, never named — R5.3 (data fails soft) |
| H11 | duplicate id | how | the first by sorted path wins, the rest counted as skipped — 385 H15 (first row wins) |
| H12 | incremental | how | records re-resolve whenever the late writers run (code moved or the digest moved) — Scope 2, 396 |
| H13 | rules stale | how | an answer carrying records gets 396's `rules_stale` label when the files moved since the build |
| H14 | exclude-file format | how | one id per line, `#` comments and blanks ignored, trimmed, exact match on `id` only — Scope 5 "their ids live in a gitignored file" |
| H15 | order of exclusion vs skip / dedupe | how | exclusion first; no message, count or list names an id from that file — AC4 |
| H16 | other surfaces | how | only the three tools plus status and the build result read records; the map, onboarding, `trace_capability` do not — Scope 3 names the surfaces; 385 H13 |
| H17 | page cost | how | the `impact` list is capped at `page_limit` with `records_total`; a `title` is cut at 200 characters — PLAN §1 "token-efficient" |
| H18 | unindexed path vs removed symbol | how | one bucket, "names nothing indexed" — 385 H16 |
| H19 | status / schema version | how | meta keys only: no `contract_version` or `SCHEMA_VERSION` move (R1.7 sibling key; 385 H12); TOOLS.md documents the fields |
| H20 | stored shape | how | one meta key for the attached records, one for the dangling pairs, one for the counts — R1.7 |
| H21 | no source block, an index built before 407 | how | no meta key → no field anywhere (AC5) |
| H22 | the build's overhead | how | measured on a synthetic 1,000-record set; the anchor's figure is unmeasured (W3) |
| W1 | Scope 2's "a record is a node; each target is an edge" | want | **ASSUMED (awaiting ratification):** a resolved lookup in the index's meta, as 385's W1. A node or edge kind moves `contract_version`, which cuts a release (R3.1), and a record node would reach every counting tool and the map. The lookup meets AC1–AC5 |
| W2 | an `exclude` file that is missing | want | **ASSUMED (awaiting ratification):** the build fails loud (`ConfigError`) rather than serving every record — a fresh clone without the gitignored file would otherwise publish the weaknesses Scope 5 keeps off |
| W3 | AC2's reach | want | **ASSUMED (awaiting ratification):** AC2 lists records on whatever the existing radius reaches; whether that radius crosses PHP into T-SQL on the anchor is unmeasured in this run (the anchor is unreadable here) and stays the maintainer's measurement |

## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=4 R=5 G=1 AC=10`
`CLARIFICATION: 25 raised | 25 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/14 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

The three want-decisions are counted self-resolved because the handover handed them back ("make the necessary
decisions"): each stands `ASSUMED (awaiting ratification)` for the maintainer at the PR, never settled.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "What it lacks is a place on the graph to hang them" | records attach to symbols inside the index, at its revision | ✅ |
| C1 | Scope 1 | "Nothing in the core names a tracker or a language (R1.1)" | the field map is data; no tracker or language name in `code_atlas/` | ✅ |
| C2 | Assumption 1 | "A table defined in many files can be a target" | attachment is by qname, so every definition carries it; an ambiguous `impact` seed still lists its records (H6) | ✅ |
| C3 | Assumption 2 | "The radius crosses PHP into T-SQL … measured on the anchor" | W3: AC2 is the existing radius; the anchor figure is unmeasured here | ⚠ W3 |
| C4 | Assumption 3 | "The build-time overhead is recorded" | measured on 1,000 synthetic records (H22) | ✅ |
| R1 | Scope 1 | declared record sources: globs, `id`/`title`/`url`/`kind`/`targets`, a field map | H1–H3 | ✅ |
| R2 | Scope 2 | built with the index; record = node, target = edge at a declared tier | H5, H12; **deviation W1**: a meta lookup | ⚠ W1 |
| R3 | Scope 3 | `impact`, `find_references`, `read_symbol` list records; tool count unchanged | H6, H7, H16 | ✅ |
| R4 | Scope 4 | dangling targets listed by the build and `get_index_status` | H8, H18 | ✅ |
| R5 | Scope 5 | an exclusion list; excluded records absent, count in status | H9, H14, H15, W2 | ✅ |
| AC1a | AC1 | `find_references` on a target lists its records, each labelled declared | `tier: HEURISTIC`, `rule: true` | ✅ |
| AC1b | AC1 | a later build reflects edits to the record files with no consumer step | an incremental build after a record edit, no other step | ✅ |
| AC2 | AC2 | `impact` lists the records anywhere in its radius, with the carrying node | `via` per row | ✅ |
| AC3a | AC3 | a dangling target is reported by the build (count + first ids) | the build result's `records` block | ✅ |
| AC3b | AC3 | … and by `get_index_status` | the same block, one helper (R1.8) | ✅ |
| AC3c | AC3 | … and appears in no answer as if attached | the dangling id is in no tool's `records` | ✅ |
| AC4a | AC4 | an excluded id appears in no tool answer and no CLI output | per-surface inventory below, N = 5 | ✅ |
| AC4b | AC4 | status reports only how many were excluded | `excluded: n`, no ids | ✅ |
| AC5 | AC5 | no declared source → byte-identical answers | per-surface inventory below, N = 5 | ✅ |
| AC6 | AC6 (added 2026-10-20) | a gitignored source is read; its rewrite moves the records on the next refresh; `rules_stale` until then | the glob reads disk, not `git ls-files`; the digest covers the file | ✅ |

### AC validation

| AC | Falsifiable? | Definition |
|---|---|---|
| AC1a | yes | `find_references(target)["records"]` holds the record's id with `tier == "HEURISTIC"` and `rule is True` |
| AC1b | yes | edit a record file's title and a target, run `incremental_update`, the answer moves |
| AC2 | yes | `impact` on a callee lists a record attached to its caller with `via == caller` |
| AC3 | yes | `dangling == 1` and the pair is listed in the build result and status; the id is absent from the target's answers |
| AC4 | yes | the excluded id's string occurs in none of the five answers' JSON (nor the CLI's stdout); `excluded == 1` |
| AC6 | yes | `qa/export.json` is gitignored and absent from `git ls-files`, yet served; rewritten, `rules_stale` is true until `incremental_update`, then the records move |
| AC5 | yes | with no block, none of the five answers carries a `records` key and the index has no records meta key; a rule file without the block answers equal to no rule file |

**Universal inventory — AC4a / AC5 (N = 5):** 1 `find_references` · 2 `read_symbol` · 3 `impact` · 4 `get_index_status`
· 5 the build result (`build_or_update_index` and the `code-atlas-build` CLI print one payload). Review confirms each.

### Gap analysis (enhancement)

- Current: records live outside the index; `impact`/`find_references`/`read_symbol` know only code
  (`code_atlas/tools/impact.py:172`, `find_references.py:281`, `read_symbol.py:105`).
- Target: a `records` rule block resolved at build (`enrichment.py` beside `publish_routes`, `:233`), stored in meta,
  read by the three tools, the status and the build result.

**Blast radius.** One repo (`app`). New `code_atlas/records.py`; `enrichment.py` (load, digest, publish);
`indexer.py` (`_count_late_writes`, `:740`); the three tools; `get_index_status.py`; `build_or_update_index.py`
(`_result`). Every rule-fed tool already reads the digest through `rules_drift`, so record-file edits mark answers
stale with no new code.

### BASELINE

`BASELINE: red — tests/test_release_discipline.py::test_the_top_release_is_tagged (399's strict xfail XPASSes now that v0.7.0 is tagged; recorded baseline exclusion B1, outside this change)`

```
$ scripts/gate.sh
  FAIL pytest -q
      [XPASS(strict)] v0.7.0 not yet tagged (399)
      FAILED tests/test_release_discipline.py::test_the_top_release_is_tagged - [XP...
      1 failed, 4869 passed, 4 skipped in 653.77s (0:10:53)
  20 passed · 1 failed · 0 skipped
GATE RED — 1 check(s) failed
Ran at 4c3a36594dfd4993e8a4666f941c71fde28af392
```

DoD: prove the delta green — B1 is the only failure allowed after the change.

### Rule sections

`RULE SECTIONS: 11 applicable — 11 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ records.py and the field map name no tracker or language; the casefold fallback keys on the contract's Table kind · §R1.4 (change-type) ✅ records.py reads files and shapes rows; SQLite stays behind store.py via enrichment · §R1.7 (change-type) ✅ the records and their counts are sibling meta keys, no existing blob widened · §R1.8 (change-type) ✅ status and the build result share records.status_block · §R2.4 (change-type) ✅ tests use invented ids and qnames · §R3.1 (change-type) ✅ no node kind, edge kind or field moves — W1 records why · §R4.2 (change-type) ✅ globs sorted, records stored sorted by id, targets in declared order · §R5.2 (change-type) ✅ a declared attachment is HEURISTIC + rule, never RESOLVED · §R5.3 (change-type) ✅ a bad block or a missing exclude file is a ConfigError; a bad record file is skipped and counted · §R5.6 (change-type) ✅ dangling, excluded and skipped are separate counts; a test drives each · §R6.5 (change-type) ✅ the new tests fail on main (no records module)`

## Phase 2 — design

### Approach

1. `code_atlas/records.py` (new core module, 385's `routes.py` shape): `read_blocks` validates a rule file's
   `records` value, expands each `sources` glob (sorted, contained), reads the `exclude` file first and drops those
   ids before any other step, maps each record through `fields`, digests every file it read; `resolve` keeps the
   targets `locate` finds and lists the rest as dangling pairs; `dump`/`load`; `attached` (records on a set of
   qnames, each with `via`); `status` (the counts block).
2. `enrichment.py`: `RulesPayload.records`; `publish_records` beside `publish_routes` stores the resolved records and
   the counts in two meta keys, or drops both; `indexer._count_late_writes` calls it, so a full build, a delta that
   parsed, and a delta whose digest moved all re-resolve (AC1b, H12).
3. Tools: `find_references` (main answer, keyed on the resolved `lookup`), `read_symbol` (found and refused
   answers), `impact` (walked, ambiguous and twinned seeds plus rows, `via`, capped at `page_limit` with
   `records_total`); a record-carrying answer gets 396's `rules_stale` side-label. `get_index_status` and the build
   result attach the counts block through one helper (R1.8). Every attach is a no-op without the meta key (AC5).
4. Docs: TOOLS.md (the rule block, the fields), CHANGELOG, PLAN (one line where §-routes are described, if any).

### Rejected alternatives

- **A `Record` node and a `DESCRIBES` edge (Scope 2's wording)** — W1: a contract bump (R3.1), a release, and a node
  every counting tool, the map and `search_symbol` would meet.
- **A `.code-atlas.toml` knob** — the rule file already carries the digest, the reapply on an incremental (396) and
  the `rules_stale` label; a second home would need all three again.
- **Read the record files at query time** — the answer would describe files the index never saw (R4.2), and a
  dangling target could not be counted by the build.
- **Opt-in parameter on each tool** — a new parameter on three tools for a block the consumer already opted into.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| the rules digest moving re-runs the late writers on an incremental | verified | `indexer.py:641` (`reapply`), 396's tests; AC1b's test re-proves it with records |
| a qname with several definitions is one stored qname, so attachment needs no choice | verified | R5.2 (046), `nodes_by_qualified_name` |
| 1,000 record files load in well under a second | novel-untested (own code, not 3p) | measured by the proving test's sibling `test_a_thousand_records_load_quickly` (C4) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | the record source, resolution, lookup, counts | `code_atlas/records.py` (new) | the two module pins (P5) | R1, R2, R4, R5, C1 | 1/1 |
| 2 | load + digest, publish | `code_atlas/enrichment.py`, `code_atlas/indexer.py` | `RulesPayload` consumers (one defaulted field); every rule-fed tool's `rules_drift` now digests record files | R1, R2, AC1b | 2/2 |
| 3 | the three tools | `tools/find_references.py`, `tools/read_symbol.py`, `tools/impact.py` | their payload goldens, if any key on the full key set; agent-brief completeness (no new parameter) | R3, AC1a, AC2, AC3c, AC4a, AC5 | 3/3 |
| 4 | status + build result | `tools/get_index_status.py`, `tools/build_or_update_index.py` | status summary/signing; the CLI prints the same payload | R4, R5, AC3a, AC3b, AC4b | 2/2 |
| 5 | tests | `tests/test_external_records.py`, the module pins | — | AC1–AC5, C2, C4 | 2/2 |
| 6 | docs | `docs/TOOLS.md`, `CHANGELOG.md`, `docs/PLAN.md` | doc size budgets | G1 | 3/3 |
| 7 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `widen-every-query-that-shares-the-page` — traced:
  `grep -n 'return signed(' code_atlas/tools/find_references.py` → `429` / `430` (serve-behind refusals: no subject
  answered), `502` (a miss: no subject), `761` (the answer). Records attach once, at `761`, on the resolved `lookup`,
  so the bare-name repoint and the table/column branches all reach it; `impact` carries records for every seed class
  `SeedPlan` holds (walk, ambiguous, twinned), not only the walked ones.
- `an-absent-reason-is-ok` — traced: `grep -rn 'def attach_rules_stale' -A22 code_atlas/tools/ | grep reason` →
  `nav_result.py:329  if relabel and payload.get("reason", REASON_OK) == REASON_OK:`. Records are a side-field, so
  they call it with `relabel=False`; the reason is never touched.

### Rule compliance

The eleven sections of Phase 1 bind the design unchanged.

R7.5 (≤ 3-line comments) and R7.6 (prune as you add) bind every change and are checked at execute.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1a | integration — rule file, build, tool | a real build through the Python adapter, `find_references` | n/a | ✅ |
| AC1b | integration | edit a record file, `incremental_update`, re-ask | n/a | ✅ |
| AC2 | integration | `impact` on a callee lists the caller's record with `via` | n/a | ✅ |
| AC3a–c | integration | a record naming a removed symbol: build result, status, the tools | n/a | ✅ |
| AC4a–b | integration | an excluded id: its string in none of the five answers, the CLI stdout; `excluded == 1` | n/a | ✅ |
| AC5 | integration | no block: no `records` key in the five answers, no meta key; rule file without the block answers equal to none | n/a | ✅ |
| AC6 | integration | a gitignored export, rewritten; status and the tool before and after an incremental | n/a | ✅ |
| C2 | integration | a SQL table in two files carries one record on both `find_references` and an ambiguous `impact` | n/a | ✅ |
| C3 | runtime (anchor) | — | n/a | excluded (W3) |

**Coverage-gap exclusion E1 — C3, the anchor's PHP → T-SQL reach.** item: C3 · risk tier: medium (AC2's usefulness
on the anchor, not its correctness) · why deferred: the anchor is a private client repo this run may not read ·
follow-up: the maintainer runs `impact` on an anchor PHP method with the block declared · expiry: when the maintainer
has run `impact` with a `records` block on the anchor index · seen: 407.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_external_records.py`

### Rollback

`git revert`; the records are two meta keys, dropped by the next build without the block. One repo, no porting.

`SCOPE: M` — unchanged.

## Phase 3 — execute

**The ticket moved mid-run (2026-10-20).** The maintainer de-identified the Why text and added to Scope 1 that a
source may be untracked or gitignored, with **AC6**. The approach already read sources from disk through the glob,
never `git ls-files`, and an incremental always compares the rules digest, so AC6 needed a test, not a design
change: a row each in the matrix, the AC table and the verification plan above. The fixture now gitignores its
export and its exclusion list, so every test proves the untracked read.

Commits `c66b94d9` (ticket), `6a678001` (core, tools, tests, module pins 104 → 105), `6a34e56d` (TOOLS.md,
CHANGELOG), `f2011141` (a split assertion).

**Red first** (R6.5) — on `4c3a3659`, before `records.py` existed:

```
$ .venv/bin/python -m pytest -q tests/test_external_records.py
ERROR tests/test_external_records.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
Ran at 4c3a36594dfd4993e8a4666f941c71fde28af392
```

**Green:**

```
$ .venv/bin/python -m pytest -q tests/test_external_records.py
17 passed in 4.86s
$ .venv/bin/python -m pytest -q -s tests/test_external_records.py -k thousand
1000 records read and resolved in 0.060s
$ .venv/bin/python -m pytest -q tests/test_impact*.py tests/test_find_references*.py tests/test_read_symbol*.py \
    tests/test_get_index_status_health.py tests/test_index_status_summary.py tests/test_rules_stale.py \
    tests/test_route_table.py tests/test_routes_from_json.py tests/test_indirection_enrichment.py \
    tests/test_build_report_counts.py tests/test_build_cli.py tests/test_agent_brief_usage_completeness.py \
    tests/test_tool_descriptions.py tests/test_payload_weight.py tests/test_mcp_server.py tests/test_incremental.py \
    tests/test_noop_incremental.py tests/test_claim_signing.py tests/test_keyed_calls_rule.py
758 passed in 87.78s (0:01:27)
$ .venv/bin/ruff check .
All checks passed!
$ .venv/bin/mypy code_atlas onboarding_llm
Success: no issues found in 113 source files
Ran at f20111416d748e5b97ded8a3bc94f51752728da1
```

The 758-test run ran at `6a678001`; nothing under `code_atlas/` changed after it.

**Verification sweep.** File axis: `git diff --stat 4c3a3659..HEAD` lists 15 files, all on the change list except
**D1**. `docs/PLAN.md` is untouched because it never described 385's route table, so it had nothing to update. No
language branch: `grep -n 'if .*language ==' code_atlas/records.py` exits 1. Behaviour axis: Approach 1–3 are
implemented as approved. In Approach 4, PLAN is D1. C4's overhead is 0.060 s for 1,000 records read and resolved,
on synthetic data.

| # | Deviation | Trace | Effect |
|---|---|---|---|
| D1 | `docs/PLAN.md` not edited | change list row 6 | none: PLAN names no route table, so it had no line for records to extend |
