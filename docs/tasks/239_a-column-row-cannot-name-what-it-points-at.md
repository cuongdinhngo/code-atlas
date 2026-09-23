---
id: 239
slug: a-column-row-cannot-name-what-it-points-at
title: 'A `search_symbol kind:"Column"` sweep returns every candidate column and nothing that ranks them, so the agent picks the wrong one — while the FK that would rank them is already in the graph as a v10 `ForeignKey` node and a `REFERENCES` edge'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [224, 236, 022]
---

## Why this exists (field retro — the anchor repo, 2026-09-11, round 16)

The round's single highest-leverage call, and the round's twenty-minute detour, were the same call.

A QA re-open asked which column carries a staff member's region. One sweep answered it:

```
search_symbol queries=["RegionCode","RegionID"] kind="Column"
→ dbo.Authen::RegionCode · dbo.Authen::RegionID · dbo.CommunityMemberDetails::RegionCode
  dbo.Site::RegionId · dbo.SiteGroup::RegionId · dbo.PostCodes::RegionID
  dbo.RegionAccess::RegionID · dbo.Depot::RegionID · dbo.PayerContract::RegionID
```

Nine candidates, each with its DDL file — a complete set no `grep` produces, because the ported code
reads the column under an alias (`r.Code AS RegionCode`) and never spells the table. The retro grades
this **A** and calls it "the best thing here".

**Then the same nine rows walked the agent into the trap.** `Authen.RegionID` is the
obvious-looking one and it is wrong: its FK points at `dbo.OperationalRegion`, a different table.
Nothing in the payload said so. The ranking came from a prose comment in `RosterAuth::updateAddress()`
and a `sys.foreign_keys` query against the live database. The retro's verdict on the dimension:
**D — "nine columns, no FK targets, no way to tell the right one from the trap without the live DB"**,
and its Ask 1, named as *"the highest-value small change I can name"*.

**What makes this a payload defect rather than a modelling gap: the answer was already indexed.**
Verified in this repo:

| The FK fact | Where it already lives | Landed |
|---|---|---|
| `REFERENCES` edge, `dbo.T::childCol` → target | `adapters/sql/src/scan.js:353,361`; `REFERENCES` in `EDGE_KINDS` + `FQN_EDGE_KINDS` (`contract.py:70,81`) | 224, 2026-09-08 |
| `ForeignKey` node carrying child/referenced tables and columns on `extra` | `contract.py` v10 `NodeKind` | 236, 2026-09-09 |
| Rendered relationships | `code_atlas/onboarding/er_diagram.py` (Pillar 2) | 224 |

Both predate the 2026-09-11 session, and a `CONTRACT_VERSION` bump forces the full rebuild that would
have populated them. **The row that returned the trap is `{qname, kind, file, line}` and nothing else**
(`code_atlas/tools/search_symbol.py`, `_hit`). Pillar 2 can draw the FK; the agent asking the first
question anyone asks of a schema cannot see it.

## Root cause

`_hit` builds one row shape for every node kind — the four positional fields plus `stub`. It is the
right default for a `Method` or a `File`, and for a `Column` it drops the one attribute that
disambiguates a set of same-named columns. There is no per-kind enrichment seam, so the FK cannot ride
the row even though the edge is resolved and addressable.

## Scope

- **A `Column` hit names its FK target when the schema declares one** — the referenced table (and
  column when the DDL gives it), read from the already-resolved `REFERENCES` edge / `ForeignKey` node,
  not re-parsed. `dbo.Authen::RegionID → dbo.OperationalRegion` printed in the row closes the trap in
  the same call that opens it.
- **Additive and kind-scoped (061 / R7.1)** — a `Column` with no FK, and every non-`Column` row, stays
  byte-identical to today. No new required field; no `NODE_FIELDS` change.
- **`detail_level` decides the cost**, per the tool's existing contract: settle in design whether the
  target rides `standard` (the retro's sweep used the default) or is opt-in, and pin the choice.
- **Determinism (R4.2)** — identical DDL yields identical rows and a stable target order for a
  multi-column FK.

### Explicitly not in scope

- **Any change to the SQL adapter or the contract.** The edge and the node exist; this ticket reads
  them. If analysis finds the edge is not reachable from a `Column` node as stored, that is a finding
  to report at Gate 1, not a licence to widen into `adapters/`.
- **The same enrichment on other kinds or tools** (`read_symbol`, `file_outline`, a `Property`'s type).
  One kind, one tool, one field — evidence-gated for the rest.
- **Ranking or re-ordering results.** The row states the fact; choosing among nine candidates stays the
  agent's judgment. Silently promoting a "best" column would be a guess wearing an answer's clothes.
- **The retro's other three findings** — deliberate-absence (§B), the two server identities (§S) and
  `file_outline` on procedural views (§F). Separate tickets if they earn one.

## Constraints

- **R1.1** — zero language branches in the core. The enrichment keys off contract vocabulary
  (`kind == "Column"`, a `REFERENCES` edge), never off SQL or a dialect; `if language ==` stays absent
  under `code_atlas/`.
- **R1.4** — `store.py` owns SQLite; the tool asks the store for the target, and neither imports an
  adapter.
- **R3** — no vocabulary or qname change, so `CONTRACT_VERSION` does not move. If design finds it must,
  that is a scope change to re-gate, not a bump to slip in.
- **R5.6 / 061** — the field is an answer the index holds, never an inference; a column whose FK is
  absent says nothing rather than guessing one.
- **223** — the envelope bills every answer. A sweep over nine columns must not grow the payload by
  more than the fact it adds; measure it.

## Acceptance criteria

1. A `search_symbol` hit for a `Column` whose DDL declares a foreign key carries the referenced target;
   pinned by a test over a fixture schema with an FK, a self-FK, and a multi-column FK.
2. A `Column` with no declared FK, and every non-`Column` kind, returns a row byte-identical to today —
   asserted, not asserted-by-absence.
3. The trap reproduces and closes on a fixture built to the field shape: two same-prefixed columns on
   one table, one pointing at a differently-named table, and the sweep distinguishes them in one call.
4. Determinism (R4.2) holds, including target order for a multi-column FK.
5. The R1.1 grep-gate stays green; `CONTRACT_VERSION` is unchanged.
6. Payload cost of the addition is measured and recorded against 223's envelope budget.

## References

Field retro — the anchor repo, 2026-09-11, round 16: §A (the call and the trap), §17 (the **D** grade), §19
Ask 1. Local file, maintainer-only — ticket keys and repo paths do not travel back here (R-7).
`code_atlas/tools/search_symbol.py` (`_hit`), `code_atlas/store.py`, `code_atlas/contract.py`
(v10 `ForeignKey`, `REFERENCES` in `EDGE_KINDS`/`FQN_EDGE_KINDS`).
Lineage: [224](224_foreign-key-is-discarded-by-the-column-reader-so-no-table-relates-to-any-other.md)
put the FK in the graph, [236](236_fk-constraint-re-emits-the-referenced-tables-kind.md) gave the
constraint its own kind after the same repo re-derived an FK answer wrong; this ticket is the third
round of one finding — **the FK is indexed, and the reader still cannot see it.**

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 239 — A Column row cannot name what it points at (working doc)

- **Ticket:** 239 · local file `docs/tasks/239_a-column-row-cannot-name-what-it-points-at.md`
- **Type:** bug / payload honesty
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 UI paths
- **TIER:** full
- **BASELINE:** green — related suite 21 passed on `b1f8810`

## Session status

- **Last updated:** 2026-09-11
- **Current phase:** finalise
- **Next action:** push feature branch + open PR (handover-authorised); merge not authorised
- **Blocked on:** none
- **work_doc_mode:** embed
- Run: `/mango:autorun 239` with `--no-reviewer`; challenger ON.
- Branch: `fix/239-a-column-row-cannot-name-what-it-points-at`
- Contract: `.mango/run-contract-239.txt`

---

## Phase 0 — Refine

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

**PREMISE detail.** Present: `code_atlas/tools/search_symbol.py` (`_hit`), `code_atlas/store.py` (`edges_by_source`), `code_atlas/contract.py` (`ForeignKey`, `REFERENCES`, `CONTRACT_VERSION`), `adapters/sql/src/scan.js` (REFERENCES emit), tasks 224/236/022, `tests/test_sql_foreign_key_references.py`. **Ambiguous (surfaced, not blocking):** private field names `Authen` / `OperationalRegion` — fixture encodes the shape (E1 analog / R2).

**INPUT KIND:** ticket (not epic).

**How-decision (self-resolved):** `detail_level` — the FK target rides **`standard`** (the retro's sweep used the default) and is omitted at **`minimal`** (subset contract, CONVENTION). Cite ticket Scope bullet 3 + CONVENTION `detail_level`.

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `do-not-attest-past-the-payloads-resolution` | 2 | handle | Yes — Column row must carry the FK fact the index already holds |
| 2 | `one-field-two-questions` | 2 | handle | Yes — new optional field, not an overload of `kind`/`qname` |
| 3 | `gate-the-disclosure-on-its-condition-not-the-row-count` | 2 | handle | Adjacent — omit-when-empty on the FK condition, not on hit count |

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria) | 5 decomposed | ROWS: C=5 R=4 G=1 AC=6`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 proven by | Status |
|----|--------|------------------|----------------|--------------|-----|-----------------|--------|
| G1 | Why | trap is nine Columns with no FK targets | Payload must name the referenced target | `_hit` drops FK | D1 | trap sweep test | ✅ |
| C1 | Constraints | R1.1 zero language branches | Enrichment keys off `kind==Column` + REFERENCES | | D1 | AC5 grep | ✅ |
| C2 | Constraints | R1.4 store owns SQLite | Tool asks `edges_by_source` | | D1 | code | ✅ |
| C3 | Constraints | R3 no contract bump | CONTRACT_VERSION stays 10 | | D1 | AC5 | ✅ |
| C4 | Constraints | R5.6 omit when absent | No FK ⇒ no field | | D1 | AC2 | ✅ |
| C5 | Constraints | 223 envelope | Measure payload delta | | D2 | AC6 | ✅ |
| R1 | Scope | Column hit names FK target from existing edges | Read REFERENCES; do not re-parse | scan.js emit | D1 | AC1 | ✅ |
| R2 | Scope | Additive kind-scoped | Non-Column + no-FK byte-identical | | D1 | AC2 | ✅ |
| R3 | Scope | detail_level decides cost | standard carries; minimal omits | | D1 | AC2 minimal | ✅ |
| R4 | Scope | Determinism incl. multi-col FK | Sorted unique targets | | D1 | AC1/AC4 | ✅ |
| AC1 | AC | FK / self-FK / multi-col pinned | | | D3 | test_column_hit_carries… | ✅ |
| AC2 | AC | no-FK + non-Column identical | | | D3 | test_no_fk… | ✅ |
| AC3 | AC | trap sweep distinguishes | proving | | D3 | test_trap_sweep… | ✅ |
| AC4 | AC | R4.2 order stable | | | D3 | AC1 determinism assert | ✅ |
| AC5 | AC | R1.1 green; version unchanged | | | D3 | test_contract_version… | ✅ |
| AC6 | AC | payload cost measured | | | D3 | test_payload_cost… | ✅ |

## AC validation

| AC | Match? | Falsifiable? |
|----|--------|--------------|
| AC1–AC5 | Y | greppable keys / CONTRACT_VERSION / pytest |
| AC6 | Y | std vs minimal byte delta on fixture |

## Inventory

- **N:** 1 tool (`search_symbol`) · 1 kind (`Column`)

| # | Item | Ph3/4 | Status |
|---|------|-------|--------|
| 1 | search_symbol Column enrichment | proving module | ✅ |

## Clarifications

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

1. Field name = `references` (edge-kind vocabulary), value = sorted `list[str]` of `target_qname or target_raw`, omit-when-empty. Cite Scope + R5.6/061.
2. `detail_level=standard` carries the field (retro default); `minimal` omits. Cite CONVENTION + Scope.

---

## Phase 1 — Analysis

- Root cause (`logic`/`payload`): `_hit` emits one shape for every kind; Column loses the REFERENCES fact already in the graph.
- Blast radius: `search_symbol` only; store API unchanged; no adapter.
- `TRACK: backend` · `SCOPE: M` · `TIER: full`

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R1.4 (change-type) ✅ · R2.2 (change-type) ✅ fixture shape not consumer names · R3 (change-type) ✅ no bump · R4.2 (change-type) ✅ sorted targets · R5.6 (change-type) ✅ omit absent · R6.1 (change-type) ✅ proving tests · R7.6 (change-type) ✅ PLAN table cell one clause`

### BASELINE

Related suite on ticket-landed HEAD `b1f8810` (pre-product change): `pytest tests/test_search_read_outline.py tests/test_sql_foreign_key_references.py tests/test_sql_alter_foreign_key_node.py -q` → **21 passed**.

`BASELINE: green`. No exclusions.

- **Gate 1 status:** cleared (autorun)

---

## Phase 2 — Design

- **Approach.** In `_hit`, when `detail_level != minimal` and `kind == Column`, call `store.edges_by_source(qname, kinds=("REFERENCES",))` and attach sorted unique targets as `references`. Pass `store` + `detail_level` from `_search_one`. No adapter/contract change. PLAN tool-table one clause. Fixture encodes trap + self-FK + composite.

- **Rejected.** (1) Re-parse DDL in the tool — rejected: ticket Scope / adapter exclusion. (2) New contract field on NODE_FIELDS — rejected: R3 / 061 optional omit. (3) Rank/reorder results — rejected: Scope exclusion.

**Assumptions**

| Assumption | Status |
|------------|--------|
| Column qname == REFERENCES source_qname | verified — 224 EXPECTED_RESOLVED |
| edges_by_source is the right API | verified — store.py:1290 |

**Smallest change-list**

| Change | File | Rows |
|--------|------|------|
| Enrich Column hits; docstring | `search_symbol.py` | G1,R1–R4,C* |
| Proving + AC tests | `tests/test_search_symbol_column_references.py` | AC1–AC6 |
| PLAN tool-table clause | `docs/PLAN.md` | R7.6 |

**Recalled handles**

| Handle | Answer |
|--------|--------|
| `do-not-attest-past-the-payloads-resolution` | traced — `_hit` gains the FK fact |
| `one-field-two-questions` | traced — new optional `references`, not overload |
| `gate-the-disclosure-on-its-condition-not-the-row-count` | traced — omit when no REFERENCES edges |

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**Proving test:** `pytest tests/test_search_symbol_column_references.py::test_trap_sweep_distinguishes_same_prefix_columns -q`

**Verification plan** — AC1–AC5 logic/unit ✅; AC6 integration ✅. `EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **Gate 2 status:** cleared (autorun)

## Decision log

| When | Decision | Why |
|------|----------|-----|
| t0 | reviewer off, challenger on | `/autorun 239 with skipped reviewer` |
| refine | standard carries `references` | retro used default; minimal is subset |
| design | field = sorted `list[str]` named `references` | edge vocabulary; determinism |

## Phase 3 — Execute

- **Branch:** `fix/239-a-column-row-cannot-name-what-it-points-at`
- **Commits:** pending
- **Proving test:** `tests/test_search_symbol_column_references.py::test_trap_sweep_distinguishes_same_prefix_columns`

- **Verification sweep.** File axis ✅ (`search_symbol.py`, proving test, PLAN, this ticket). Behaviour axis: implemented-as-approved.

- **Design-conformance deviations:** none

- **Empirical output**

R6.5 red-before (production `search_symbol.py` stashed on `b1f8810`): proving trap sweep → **FAILED** `KeyError: 'references'`.

Post-change:

Ran at d12820ae622d3fa3de91e55db5d9605e56249180

```
$ .venv/bin/python -m pytest tests/test_search_symbol_column_references.py tests/test_search_read_outline.py -q --tb=line
16 passed in 3.15s
```

AC6: std vs minimal sweep delta asserted `< 500` bytes on the trap fixture.

- **Golden/snapshot:** none
- **Design-invalidation:** none

## Phase 4 — Review

- **REVIEWER: OFF (`--no-reviewer`)** — no rule-book-grounded review of this diff exists.
- **CHALLENGER: ON** — [ticket-blind challenger](a36986ec-78f0-4853-b793-cf3bc6bbc630). Raw ticket + `git diff main...HEAD` excluding this file.
- **challenger result:** 13/14 reconstructed requirements **MET**; **AC6 can't tell** (ledger not in product commit — filled at finalise). 0 not met.
- **Scope reconciliation:** file + behaviour axes clean; no deviations.
- **Proving test would fail without the change?** Yes — R6.5 `KeyError: 'references'`.

Ran at d12820ae622d3fa3de91e55db5d9605e56249180

```
$ .venv/bin/python -m pytest tests/test_search_symbol_column_references.py::test_trap_sweep_distinguishes_same_prefix_columns -q --tb=line
.                                                                        [100%]
1 passed in 0.30s
```

- **Clean?** `clean (challenger only — REVIEWER: OFF)`
- **Reviewed at** `d12820ae622d3fa3de91e55db5d9605e56249180`
- **Reviewed files:** `code_atlas/tools/search_symbol.py`, `tests/test_search_symbol_column_references.py`, `docs/PLAN.md`, `docs/tasks/239_a-column-row-cannot-name-what-it-points-at.md` (exempt), `docs/LESSONS.md` (exempt), `docs/TOKEN_LEDGER.md`, `docs/BACKLOG.md`

## Phase 5 — Finalise

- **Stale-review guard:** product files unchanged since `d12820a`; bookkeeping is exempt/reviewed set.
- **Planned outward actions:**
  - [x] push branch — handover authorisation
  - [x] open PR via `gh` — handover authorisation — [#310](https://github.com/cuongdinhngo/code-atlas/pull/310)
  - [ ] merge — NOT authorised
- **Durable lesson:** recurrence of `do-not-attest-past-the-payloads-resolution` — the FK was indexed (224/236) and the first reader tool still omitted it.
- **Revert path:** revert the branch / close the PR without merge.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md (already R5.6) | mango files written: 0`

Classification is a proposal; human ratification deferred (`k = 0`). Class already carried by **R5.6** — bump `seen:` only; `/mango:promote` not required to invent a new rule.

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Notes |
|-------|---------------------|-------|--------|-------|
| Review | ticket-blind challenger | 1 | unmeasured (host does not surface usage) | reviewer OFF; 13/14 MET |

`LEDGER TOTAL: unmeasured · top cost driver: main-loop`
