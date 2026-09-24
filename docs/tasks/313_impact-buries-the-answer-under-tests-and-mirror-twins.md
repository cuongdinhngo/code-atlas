---
id: 313
slug: impact-buries-the-answer-under-tests-and-mirror-twins
title: "`impact` returns every row at the same weight, so ten production callers arrive under fifty tests and mirror twins"
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [262, 265, 277, 282, 298]
---

## Why this exists

Two field rounds scored `impact` **5/10** for the same mechanism, and it is the only tool with a
repeated score that low. The finding, in the round's own words: *"It contains the right answer and
buries it."* Sixty nodes at depth 2 — roughly twenty mirror twins of the same file and another
fifteen tests — against ten production callers that `find_callers` had already named. The ask was
explicit: **give `impact` the production/test and outside-the-mirror split `find_callers` already
computes.**

The data is one file away and already stored:

- `find_callers._test_census` (`code_atlas/tools/find_callers.py:636`) reads `is_test` per row and
  labels the basis with `stored_test_source` (262, with 298's path-convention fallback).
  `impact.py` does not mention `is_test` once.
- The mirror side is stamped at build time by `mirror_search.py` — measured from external inbound
  edges, **no directory names** (277/282, R2-safe) — and only `search_symbol` and `read_symbol`
  read it.

So this is not new analysis. It is two stored facts reaching a third tool.

## Goal

Make `impact`'s page-one rows the ones a reader acts on: every row says whether it is test or
production and whether it sits on a mirrored subtree, and a caller can exclude tests **before**
paging rather than after.

## Scope / Deliverables

1. **Per-row role on `impact` results** — each row carries its test/production role and the basis
   that decided it, reusing `symbol_role` rather than a second classifier.
2. **`exclude_tests` on `impact`**, filtering as a **store predicate before paging** (R1.4), so
   page one is production rows and not the production rows that survived a page of tests. This is
   the `find_callers` contract, applied to the same question one hop out.
3. **Mirror labelling on `impact` rows** — a row on a stamped pair names its counterpart, or the
   honest negative when the twin is not indexed, exactly as `search_symbol` and `read_symbol` do.
   No stamp ⇒ no field and no cost (061).
4. **The same per-row role on `search_symbol`**, which the field round named beside `impact` and
   which also has zero `is_test` today.
5. Ranking may use the new labels, but only within today's bands — an ordering change is stated in
   the payload the way `search_order` already states the mirror rule (265/277).

## Constraints

- **No aggregate census above depth 1.** `find_callers` reports `production_count` / `test_count`
  at depth 1 only, because above it the answer is a BFS total a partition cannot add up to
  (165/262). `impact` is multi-hop by definition, so this ticket ships **row properties**, which
  are honest at any depth, and must not ship counts that imply a partition of the radius (R5.5).
- **`src/` vs `legacy/` is the stamped mirror pair, never a directory list.** Naming a repo's
  layout in the core is R2; the stamp is measured from external inbound edges and already exists.
- No language branch in the core (R1.1); only `store.py` touches SQLite (R1.4).
- Identical graph and change set produce byte-identical ordering (R4.2).
- `minimal` stays a subset: a new field is omitted there, never added (CONVENTION §6).
- Omit-when-empty (061) — an unmirrored, test-free repo pays nothing.

## Acceptance criteria

- **AC1** A fixture whose changed symbol is reached by both production and test callers returns
  rows labelled with their role, and the label names the basis (`adapter` vs `path_convention`).
- **AC2** `exclude_tests=true` returns a page whose production rows are the same ones a full page
  would have contained — proven by a fixture where tests outnumber the page limit, so a
  filter-after-paging implementation fails it (R6.8).
- **AC3** A fixture on a stamped mirror pair labels the counterpart, and a fixture whose twin is
  **not** indexed gets the honest negative rather than a path that does not exist (282).
- **AC4** No count, total or census is emitted that partitions a multi-hop radius; a test asserts
  the absence, so a later well-meant addition fails rather than ships (R5.5).
- **AC5** `search_symbol` carries the same per-row role, and the existing band order is unchanged
  unless the payload states the new rule.
- **AC6** `minimal` omits every new field; `standard` carries them — asserted on both tools.
- **AC7** A repo with no mirror stamp and no test-classified nodes produces byte-identical payloads
  to today, so the feature is free where it does not apply (061, R4.2).

## Out of scope

- Fixing `subject_ambiguous` on a name defined in two trees. That is the *other* half of the same
  field finding — `impact` answering nothing at all rather than answering noisily — and it needs a
  seed-disambiguation design, not a labelling one. Separate ticket.
- `impact_modules`, which already rolls up by module and splits by tier.
- Any adapter change. `is_test` is stored today (262/298); if a language classifies tests poorly
  that is a recorded cause and a separate ticket.
- Selective test execution of any kind — 308's report-only contract is untouched.

## References

`code_atlas/tools/impact.py`, `code_atlas/tools/find_callers.py:615-640`,
`code_atlas/tools/search_symbol.py`, `code_atlas/mirror_search.py`, `code_atlas/symbol_role.py`,
`code_atlas/store.py::inbound_test_rows`,
[262](262_the-contract-marks-test-code-and-no-tool-reads-it.md),
[277](277_page-one-ranks-the-tree-that-cannot-run.md),
[282](282_a-mirror-hit-names-a-counterpart-that-is-not-in-the-index.md),
[`docs/TOOLS.md`](../TOOLS.md), CONVENTION §6, ENGINEERING_RULES R1.1, R1.4, R2, R4.2, R5.5, R6.8.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 313 — impact row roles + mirror labels (working doc)

- **Ticket:** 313 · local (key collides with the done agent-brief 313 — see Decision log)
- **Type:** enhancement
- **Repo(s) / Porting:** app
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **INPUT KIND:** ticket
- **work_doc_mode:** embed · path: docs/tasks/313_impact-buries-the-answer-under-tests-and-mirror-twins.md
- **REVIEWER:** OFF (--no-reviewer) · **CHALLENGER:** ON
- **Current phase:** review

## Phase 0 — Refine

`PREMISE FALSIFIED: 1 referenced-as-existing source(s) missing — find_callers._role_census (Why this exists, line 22)`
`PREMISE: 9 reference(s) checked | 1 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

Premise resolution (human, by standing handover): `_role_census` never existed (`git show 3c399e9:code_atlas/tools/find_callers.py` has only `_test_census`); the cited `path:line` lands inside `_test_census`, whose behaviour matches the ticket's claim. The maintainer's handover ("make the necessary decisions … without waiting for further confirmation") is taken as the "correct the ticket" resolution: line 22 now names `_test_census` (`find_callers.py:636`). Disclosed.

refine skipped: 0 unresolved product-decisions — fields, predicate and omit rules all follow existing conventions (cited in Phase 1).

## Requirements matrix

`SECTIONS: 7 found (Why this exists · Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope · References) | 7 decomposed | ROWS: C=6 R=5 G=1 AC=7`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Goal | page-one rows are the ones a reader acts on | row role + mirror label + pre-paging exclude | D1–D4 | AC1–AC3 | ✅ |
| R1 | Scope 1 | per-row role + basis, reusing `symbol_role` | `test_role_source` on test rows via `stored_test_source` | D1 D2 | AC1 | ✅ |
| R2 | Scope 2 | `exclude_tests` as a store predicate before paging | reuse `_exclude_test_sources_predicate` inside the walk's expand SQL | D1 D2 | AC2 | ✅ |
| R3 | Scope 3 | mirror counterpart or honest negative on rows | `mirror_counterpart` / `mirror_no_counterpart` via `resolve_counterpart` | D3 D2 | AC3 | ✅ |
| R4 | Scope 4 | same per-row role on `search_symbol` | `_hit` adds `test_role_source` at standard | D4 | AC5 | ✅ |
| R5 | Scope 5 | ranking may use labels, only within bands, stated | ordering unchanged (not taken) → nothing to state | — | AC5 AC7 | ✅ |
| C1 | Constraints | no aggregate census above depth 1 | no count/total/census added | D2 | AC4 | ✅ |
| C2 | Constraints | mirror pair is the stamp, never a dir list | stamp-only (`load_mirror_search_stamp`) | D3 | AC3 | ✅ |
| C3 | Constraints | no language branch; only store touches SQLite | predicate + flag read live in `store.py` | D1 | gate R1.1 grep | ✅ |
| C4 | Constraints | byte-identical ordering (R4.2) | walk order untouched; labels are pure row adds | D1 D2 | AC7 | ✅ |
| C5 | Constraints | `minimal` stays a subset | new fields omitted in minimal | D2 D4 | AC6 | ✅ |
| C6 | Constraints | omit-when-empty (061) | production rows / unmirrored rows carry nothing | D2 D3 D4 | AC7 | ✅ |
| AC1 | AC | rows labelled with role + basis (adapter vs path_convention) | fixture with both sources | D2 | proving | ✅ |
| AC2 | AC | exclude_tests page == production rows of full answer, tests > limit | node budget < test count | D1 D2 | proving | ✅ |
| AC3 | AC | counterpart named; unindexed twin → honest negative | two fixtures | D3 | proving | ✅ |
| AC4 | AC | no count partitioning a multi-hop radius; test asserts absence | key-absence assertion | D2 | proving | ✅ |
| AC5 | AC | search_symbol per-row role; band order unchanged | order-equality + label | D4 | proving | ✅ |
| AC6 | AC | minimal omits every new field, standard carries — both tools | two-level assertion | D2 D4 | proving | ✅ |
| AC7 | AC | no stamp + no test nodes → byte-identical payloads | json.dumps equality vs a pre-change expectation | D2 D4 | proving | ✅ |

Out of scope (recorded, no rows needed beyond fencing): `subject_ambiguous` seed disambiguation, `impact_modules`, adapter changes, selective test execution — none touched.

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

- Q1 (self-resolved): per-row role field shape → `test_role_source` on test rows only, absence = production — the name `find_callers` already ships at payload level (`find_callers.py:570`), the value from `symbol_role.stored_test_source`; omit-when-empty per 061 (CONVENTION §6) is what makes AC7 hold.

## Phase 1 — Analysis

- Gap: `impact.py` never reads `is_test` (0 hits); `store.impact_radius` (`store.py:2636`) returns `qname/score/depth/file/line/confidence_tier` and prunes the node budget by score with tests competing for it; mirror stamp is read only by `search_symbol` (`search_symbol.py:273`) and `read_symbol` (`read_symbol.py:566`). `search_symbol._hit` (`search_symbol.py:716`) drops `is_test` though `NODE_FIELDS` carries it.
- Blast radius: `impact_radius` has 3 callers (`impact.py:204`, `impact_modules.py:133`, `architecture_rules.py:252`) — the new keyword defaults off, so two are untouched; row shape unchanged for all three. `_exclude_test_sources_predicate` has 2 callers in `store.py` (edge alias `edges`).
- TRACK: backend — 0/0 UI

`TRACK: backend — 0/6 touched files under UI paths`

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ predicate is kind-free SQL in store.py, no language test · R1.4 (change-type) ✅ the only SQL is in store.py; tools call methods · R2 (change-type) ✅ mirror side from the stamp, test role from is_test/path segments, no repo names · R4.2 (change-type) ✅ walk ORDER BY untouched; labels iterate rows in order · R5.5 (change-type) ✅ no count above depth 1 — AC4 asserts absence · R6.8 (change-type) ✅ AC2 fixture makes filter-after-paging fail · R7.2 (change-type) ✅ ledger row + BACKLOG removal in this PR`

Baseline record — pre-change tree `660281a140e52a4ccd0a71f1e43bfd9b639c79bc` (historical: not proof for the tree under review; re-run in Phase 4). Command `.venv/bin/python -m pytest -q --tb=line -p no:cacheprovider`, output tail:

```
.......sss..................................................             [100%]
4376 passed, 4 skipped in 362.21s (0:06:02)
```

`BASELINE: green`

## Phase 2 — Design

- Approach:
  - A1 `store.impact_radius` gains `exclude_test_sources` (default off): the walk's expand SQL ANDs the existing `_exclude_test_sources_predicate` (262), so a test source never enters `impact_best`, never spends the node budget and never expands — filtered before any prune or page (R1.4, R6.8).
  - A2 `store.test_node_keys(qnames)` returns the `(qname, file)` pairs stored `is_test = 1`; `impact` labels each row whose `(qname, file)` is in it with `test_role_source` from `symbol_role.stored_test_source` — no second classifier.
  - A3 `mirror_search.label_mirror_rows` puts `mirror_counterpart` (indexed twin) or `mirror_no_counterpart: true` on rows whose `file` sits on a stamped pair, through the same `resolve_counterpart` `read_symbol` uses; no stamp ⇒ nothing read, nothing added.
  - A4 `search_symbol._hit` adds `test_role_source` for a stored test row at `standard`.
  - A5 every new field is skipped at `minimal`; no ordering change, so no `search_order` text changes; no count, total or census is added.
- Rejected: filtering rows after `impact_radius` returns (a page of tests would already have spent the budget — the exact AC2 failure); a `role: production|test` on every row (grows every payload, breaks AC7's byte-identity); ranking tests below production (optional per Scope 5, changes R4.2 order and would need a stated rule — not taken).

**Assumptions:** `_exclude_test_sources_predicate` is valid inside the walk's `JOIN edges e` once the alias is a parameter — verified (plain SQL, same columns). `NODE_FIELDS` carries `is_test` into search rows — verified (`contract.py:166`, `store.py:168`).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|--------|------|--------------|----------------|-----|
| D1 | `exclude_test_sources` on the walk; predicate alias param; `test_node_keys` | code_atlas/store.py | `impact_modules`, `architecture_rules` call the walk (default off → unchanged); 2 predicate callers keep alias `edges` | R2 R1 C3 | 1/1 |
| D2 | `exclude_tests` param; row role + mirror labels at standard; docstring | code_atlas/tools/impact.py | MCP description (tool_descriptions tests); brief completeness gate (param already waived) | R1 R2 R3 C1 C5 C6 | 1/1 |
| D3 | `label_mirror_rows` | code_atlas/mirror_search.py | new function; existing helpers untouched | R3 C2 | 1/1 |
| D4 | `test_role_source` on search hits at standard | code_atlas/tools/search_symbol.py | search goldens asserting exact hit keys on test paths | R4 C5 | 1/1 |
| D5 | proving tests AC1–AC7 | tests/test_impact_row_roles.py | new file | AC1–AC7 | 1/1 |
| D6 | TOOLS.md impact row; ticket status; BACKLOG row removed; TOKEN_LEDGER row | docs/TOOLS.md · docs/tasks/313_impact… · docs/BACKLOG.md · docs/TOKEN_LEDGER.md | doc size budget; backlog bookkeeping test | R7.2 | 1/1 |

Rule compliance: R1.1/R1.4/R2/R4.2/R5.5 as Phase 1; CONVENTION §6 (minimal subset) by A5; R7.5 comments ≤ 3 lines.

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | integration (tool over a real SQLite store) | n/a | ✅ |
| AC2 | integration | integration (node budget < test count) | n/a | ✅ |
| AC3 | integration | integration (stamped store, indexed + unindexed twin) | n/a | ✅ |
| AC4 | logic | integration (key-absence on the payload) | n/a | ✅ |
| AC5 | integration | integration (search order + label) | n/a | ✅ |
| AC6 | integration | integration (both detail levels, both tools) | n/a | ✅ |
| AC7 | integration | integration (literal pre-change payload captured on 9f152b4-era main) | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_impact_row_roles.py -q`

Rollback: revert the branch's commits; no schema, no migration, no stored data. Porting: single repo.

`SCOPE: M` (unchanged)

## Phase 3 — Execute

**Branch:** feat/313-impact-row-roles

Pre-change record — tree `660281a` plus the uncommitted proving test, before any source edit (historical). Command `.venv/bin/python -m pytest tests/test_impact_row_roles.py -q --tb=line`:

```
E   TypeError: create.<locals>.impact() got an unexpected keyword argument 'exclude_tests'
7 failed in 1.18s
```

**Verification sweep**

Ran at 4ef68a36d1867678f44c3430265a932caf960701

```
$ git diff --name-only main..HEAD
code_atlas/mirror_search.py
code_atlas/store.py
code_atlas/tools/impact.py
code_atlas/tools/search_symbol.py
docs/BACKLOG.md
docs/TOOLS.md
docs/tasks/313_impact-buries-the-answer-under-tests-and-mirror-twins.md
tests/test_impact_row_roles.py
$ .venv/bin/python -m pytest tests/test_impact_row_roles.py -q --tb=no
.......                                                                  [100%]
7 passed in 1.37s
$ .venv/bin/ruff check code_atlas -q && .venv/bin/mypy code_atlas
Success: no issues found in 93 source files
```

Every file is on the D1–D6 list (`docs/TOKEN_LEDGER.md` lands at finalise with the dispatch count).

Deviation (behaviour axis, recorded for review): A2 approved a new `store.test_node_keys`; implemented instead with the existing `store.nodes_by_qualified_names(qnames, limit=1)` — `_NODE_ORDER` makes `limit=1` the same node the walk took `file`/`line` from, so no new store method and no new SQL. Smaller than approved; same behaviour.

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed — A1 implemented-as-approved · A2 deviated (recorded above) · A3 implemented-as-approved · A4 implemented-as-approved · A5 implemented-as-approved`

