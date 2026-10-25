---
id: 412
slug: records-direct-first
title: "`impact` records reached through a hub file drown the records about the subject itself"
phase: 2
milestone: Trust
status: done
depends_on: [407]
---

## Why this exists

A consumer's survey, 2026-10-25. `impact` on one save controller answered `records_total: 179`. All of
them came `via` the front-controller file, a hub that dispatches hundreds of routes. Only about 11
records named the controller's own symbols, and records about unrelated screens came first.

On `main`, `impact` builds its carriers in this order: walk seeds, the radius in walk order, then
files (`impact.py:286-293`). `records.attached` keeps each record under its first carrier and then
truncates at `page_limit` (`impact.py:294-297`). A record on a *member* of the seed sits wherever that
member falls in the radius, so a hub reached early can fill the page before it.

## Scope

1. Every record row carries `distance` (hops from the seed) and `direct: true|false`, beside the
   existing `via`. *Direct* means the record is attached to the seed, to a symbol the seed contains,
   or to the seed's own file. Design confirms that definition.
2. Rows are ordered direct first, then by distance, then as today.
3. Two new parameters on the tools that return records: `records: "direct" | "radius"` (default
   `radius`) and `records_limit`.
4. A `stop_at` list of globs in the `records` block. A file it matches carries no records into an
   answer whose seed is somewhere else. Its own `impact` still lists them.
5. Update the user docs for the records rule and the tools affected.

Out of scope: auto-flagging hubs by record fan-in. Revisit only if `stop_at` proves insufficient.

## Acceptance criteria

- **AC1:** In a fixture, a hub file carries 50 records and a leaf it reaches carries 2. `impact(leaf)`
  lists the 2 first, each `direct: true`.
- **AC2:** With `stop_at` covering the hub, none of the hub's 50 records is in that answer.
- **AC3:** With `records: "direct"`, exactly the 2 are returned.
- **AC4:** A caller passing neither parameter gets the same *set* of records as before, with the added
  fields.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 412 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W4 and merges #110 after #109. **Revert path:** `git revert` the branch's commits; no contract or schema moved.
- `TRACK: backend` · Run mode: `autorun 411 - 412 - 413 - 414 - 415 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/412-records-direct-first`, **stacked on `feat/411-route-key-collisions`** (#109). Contract `.mango/run-contract-412.txt`.
  RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 9 unresolved surfaced | 4 want-decision asked | 5 how-decision resolved+cited | 4 ASSUMED | skip: no`

**Premise.** `impact`'s carrier list and page cut (`impact.py:286-297` on `main`), `records.attached`, `via`,
`page_limit`, the `records` block resolve. Recall (type 2, by handle — a value threaded to a page several reads
share): 362-C1 `widen-every-query-that-shares-the-page`; 384-C1 `keep-first-hides-the-later-declaration`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 47,976 tokens) raised nine items, settled below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | "a symbol the seed contains" | how | qname containment: a target whose owner chain (`::`) reaches a seed (`contract.MEMBER_SEPARATOR`); a path seed already seeds every symbol of its file (`plan_seeds`) |
| H2 | `distance` | how | the radius row's `depth` (`store.impact_radius`); 0 for a direct record; carriers are read by depth, so a record keeps its least distance |
| H3 | ties | how | a stable sort by depth keeps today's order inside one depth, symbols before files |
| H4 | the seed sites | how | walked, ambiguous and twinned seeds are all seeds (`impact.py:288-290`), their files from `nodes_by_qualified_names` |
| H5 | `records_limit` | how | the repo's paging rule: clamped at `page_limit`, `limit_capped_to` when reduced (`config.clamp_limit`, 066, guarded by `test_limit_clamp_visible.py`); `< 1` is a `ValueError` like `depth` |
| W1 | `stop_at` | want | **ASSUMED (awaiting ratification):** a build-time key in the `records` block (digested, so an edit reads `rules_stale`); `fnmatch` over the carrier's repo-relative file, `*` crossing `/`; it stops a radius carrier — a hub symbol or the hub file — never a direct one |
| W2 | which tools take the parameters | want | **ASSUMED (awaiting ratification):** the parameters on `impact` only. `read_symbol` and `find_references` list the subject's own records — every row is direct, nothing pages them — so `records` and `records_limit` would change nothing there; their rows still carry `direct: true`, `distance: 0` (review F1) |
| W3 | `records_total` | want | **ASSUMED (awaiting ratification):** counts the rows the scope and `stop_at` kept (what `records_limit` pages); `records_stopped` counts the records `stop_at` alone kept out, omitted at 0 |
| W4 | AC4's "same set" | want | **ASSUMED (awaiting ratification):** the default set is today's plus the direct records today's carriers missed — a seed's member the walk never reached, a qname seed's own file. Scope 1 defines them as the subject's; dropping them would keep the defect |

## Phase 1 — analysis

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Why this exists · Scope · Out of scope · Acceptance criteria) | 4 decomposed | ROWS: C=1 R=5 G=1 AC=4`
`CLARIFICATION: 9 raised | 9 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/8 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

W1–W4 count as self-resolved because the handover handed them back; each stands `ASSUMED` for the maintainer.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a hub … can fill the page before it" | the subject's records lead the page | ✅ |
| C1 | Out of scope | no fan-in auto-flagging | `stop_at` is declared, never inferred | ✅ |
| R1 | Scope 1 | `distance`, `direct` beside `via` | `Record.as_row(via, distance)`; H1, H2 | ✅ |
| R2 | Scope 2 | direct first, then distance, then as today | `records.ranked`; H3 | ✅ |
| R3 | Scope 3 | `records`, `records_limit` | W2, H5 | ✅ |
| R4 | Scope 4 | `stop_at` | W1, W3 | ✅ |
| R5 | Scope 5 | docs | TOOLS.md (table row, records paragraph), `impact` docstring | ✅ |
| AC1 | AC1 | 2 leaf records first, `direct: true` | fixture: hub file with 50, leaf with 2 | ✅ |
| AC2 | AC2 | `stop_at` → none of the 50 | `stop_at: ["front.*"]` | ✅ |
| AC3 | AC3 | `records="direct"` → exactly the 2 | — | ✅ |
| AC4 | AC4 | neither parameter → same set + fields | W4; 407's suite unchanged | ✅ |

### AC validation

| AC | Falsifiable? | Definition |
|---|---|---|
| AC1 | yes | `impact(paths=[leaf])` rows 0–1 are `LEAF-1`, `LEAF-2`, `direct: true`, `distance: 0`; rows 2+ `direct: false` |
| AC2 | yes | with `stop_at`, the leaf's rows are exactly the 2; `records_stopped == 50`; the hub's own answer lists its 50 |
| AC3 | yes | `records="direct"` → `["LEAF-1", "LEAF-2"]`, `records_total == 2` |
| AC4 | yes | `tests/test_external_records.py` unchanged and green; `records_total == 52` with no parameter |

### Gap analysis (enhancement)

- Current: one carrier list in walk order, `attached` first-wins, cut at `page_limit` (`impact.py:286-297`).
- Target: direct carriers first (seeds, members, seed files), then the radius by depth, filtered by `stop_at`.

**Blast radius.** `records.py`, `enrichment.publish_records`, `impact` (signature, docstring), the brief's
surface-completeness guard (`test_agent_brief_usage_completeness.py`), the clamp guard (`test_limit_clamp_visible.py`),
407's suite, TOOLS.md.

### BASELINE

`BASELINE: green — 411's final gate on this stack: 4947 passed, 4 skipped, 1 xfailed, 2 host exclusions`

Ran at 7159f73b (411's gate; the base tip `a067695a` adds only its record). Host exclusions:
`test_install_skew.py::test_a_checkout_behind_the_core_is_named_with_its_fix`,
`test_release_discipline.py::test_the_plugin_hook_names_a_skew_against_the_installed_package` — they read the host's
installed tool through the live checkout and pass in a clean worktree (411's record).

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ seeds, members and files compared as strings, no language · §R1.7 (change-type) ✅ stop_at on its own meta key, records_stop_at · §R1.8 (change-type) ✅ one ranking, records.ranked · §R5.6 (change-type) ✅ records_stopped separates "hidden by stop_at" from "none" · §R5.8 (change-type) ✅ the rows are ranked before the records_limit cut, in the same function call chain · §R6.5 (change-type) ✅ the proving tests seen red · §R7.6 (change-type) ✅ TOOLS.md's impact row edited in place`

## Phase 2 — design

### Approach

1. `records.ranked(records, seeds, radius, stop_at, direct_only)`: direct carriers — the seeds, then every stored target
   a seed contains — at distance 0; then the radius `(carrier, depth, file)` sorted stably by depth, a carrier whose file
   matches `stop_at` skipped and its unseen records counted. Each record once, first carrier wins.
2. `Record.as_row(via, distance)` adds `distance` and `direct` only when a distance is given (`read_symbol` and
   `find_references` rows unchanged).
3. `RecordSet.stop_at` from the block; `publish_records` stores the union under `records_stop_at`.
4. `impact`: `records: "direct" | "radius"`, `records_limit` (clamped, `limit_capped_to`); seeds are the walked,
   ambiguous and twinned qnames, the paths, and the seeds' files; `records_stopped`.
5. Docs: TOOLS.md, the `impact` docstring; the brief guard waives the two parameters as `impact`'s side-field knobs.

### Rejected alternatives

- **Sort `attached`'s rows after the fact** — the first-wins carrier would still be the hub for a record on both.
- **Mark hubs by record fan-in** — out of scope (C1).
- **The parameters on all three tools** — W2: constants there.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| radius rows carry `depth` | verified | `store.impact_radius` keys (`store.py:3625`) |
| the hub is reached from the leaf | verified | AC1: 52 records, rows 2+ `direct: false` |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | ranking, `stop_at`, row fields | `code_atlas/records.py` | 407's suite | R1, R2, R4 | 3/3 |
| 2 | store `stop_at` | `code_atlas/enrichment.py` | rules digest (unchanged) | R4 | 1/1 |
| 3 | parameters, seeds, page | `code_atlas/tools/impact.py` | the tool description; claim `call_args` | R3, AC1–AC4 | 1/1 |
| 4 | tests | `tests/test_records_direct_first.py` (new), `tests/test_agent_brief_usage_completeness.py` (two waivers), `tests/test_limit_clamp_visible.py` (13 tools) | — | AC1–AC4 | 3/3 |
| 5 | docs | `docs/TOOLS.md` | doc budgets | R5 | 1/1 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `widen-every-query-that-shares-the-page` — traced: `rtk proxy grep -rn "records.attached" code_atlas` →
  `find_references.py:766`, `impact.py:300`, `read_symbol.py:441`; only `impact` pages a radius, the other two read
  the subject alone (W2). `records_total` and `records_stopped` are read from the same ranked list as the page.
- `keep-first-hides-the-later-declaration` — traced: `rtk proxy grep -n "if record.id not in seen" code_atlas/records.py`
  → `attached`'s first-wins; `ranked` keeps first-wins but orders carriers so the first is the nearest.

### Rule compliance

Phase 1's seven sections bind. R7.5 binds every comment.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — build, walk, ranking | a real build through the Python adapter, `impact` | n/a | ✅ |
| AC2 | integration | the same build with `stop_at` | n/a | ✅ |
| AC3 | integration | `records="direct"` | n/a | ✅ |
| AC4 | integration | 407's suite, the default answer | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_records_direct_first.py`

### Rollback

`git revert` the branch's commits; no contract or schema moved. One repo.

## Phase 3 — execute

Implemented in the main loop. Commits `fce06edd` (core + tests), `2c9a11ad` (docs).

**Red first** (R6.5): with `code_atlas/` stashed back to the base, `tests/test_records_direct_first.py` gives
`6 failed in 0.86s`.

**Green at execute:**

Ran at 2c9a11ad

```
$ .venv/bin/python -m pytest -q tests/test_records_direct_first.py tests/test_limit_clamp_visible.py tests/test_external_records.py
56 passed in 5.84s
$ .venv/bin/python -m pytest -q -k "record or impact or description or skill or brief or tool or claim or sign or route or status or limit"
1070 passed, 3890 deselected in 115.26s (0:01:55)
$ .venv/bin/ruff check code_atlas tests && .venv/bin/mypy code_atlas
All checks passed!
Success: no issues found in 105 source files
```

**Verification sweep.** File axis: every touched file is on the change list. Behaviour axis: Approach 1–5 implemented
as approved.

| # | Deviation | Trace | Effect |
|---|---|---|---|
| D1 | `records_limit` is clamped at the page | H5, first drafted as unbounded | `test_limit_clamp_visible.py` caught the missing signal; the repo's paging rule answers it |
| D2 | the two guard tests (brief waivers, clamp count) were missed by the first change list | row 4's blast radius | both guard every new parameter; they now name the two |

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.

- **`challenger` round 1** (ticket-blind, 61,470 tokens; raw ticket only): 10 met · 2 not met · 1 partly met.
  - F1 (Major) — `read_symbol` and `find_references` rows carried no `distance`/`direct` (Scope 1 "every record row") —
    **fixed** in `66970b60`: `attached` marks the subject's rows direct at 0; 407's exact-row test now names the fields.
    Their parameters stay on `impact` alone (W2, partly met by design).
  - F2 (Major) — AC4: a qname seed now lists its file's and members' records the old carriers missed — **kept as W4**:
    Scope 1 defines those as the subject's; `test_a_qname_seeds_own_file_is_direct_*` pins it.
  - F3 (Minor) — direct-row order unstated — **documented** in TOOLS.md (seeds, paths, seed files, members).
  - F4 (Minor) — `limit_capped_to` with no records rows — **fixed**: attached inside the rows branch.
  - F5 (Minor) — a module qname seed does not contain its classes (`.` is not the member separator) — **accepted as a
    limit**: a path seed covers the module; containment is the contract's `::`.
- **Round 2: verify-only, main loop.** The fixes stay inside `records.py`, `impact.py`, their tests and TOOLS.md.

```
$ .venv/bin/python -m pytest -q -k "record or impact or read_symbol or find_references or brief or limit"
935 passed, 4026 deselected in 60.95s (0:01:00)
```

Ran at 66970b60

Verdict: clean (challenger only — REVIEWER: OFF), W1–W4 standing for ratification.
`Ph3/4 proven by`: R1 → `test_ac1_*`, 407's `test_find_references_lists_*`; R2, AC1 → `test_ac1_*`,
`test_a_record_on_a_member_*`; R3, AC3 → `test_ac3_*`, `test_ac4_*`; R4, AC2 → `test_ac2_*`; AC4 → 407's suite,
`test_ac4_*`; R5 → TOOLS.md.

Reviewed at 66970b60. Files: `code_atlas/records.py`, `code_atlas/enrichment.py`, `code_atlas/tools/impact.py`,
`tests/test_records_direct_first.py`, `tests/test_external_records.py`, `tests/test_agent_brief_usage_completeness.py`,
`tests/test_limit_clamp_visible.py`, `docs/TOOLS.md`. Working doc: this file.

## Phase 5 — finalise

**Durable lesson.** Two claims, in `docs/LESSONS.md`:

`CLAIMS: 2 claim(s) from 1 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`

- 412-C1 `a-new-parameter-meets-the-surface-guards` (code, new): a tool parameter is read by the brief's
  surface-completeness guard and, if it is a `limit`, by the clamp guard; the first change list named neither.
- 362-C1 `widen-every-query-that-shares-the-page` (seen +412): the records page was read by `impact` alone, but the row
  shape by three tools — the challenger found two left out. Falsify: `rtk proxy grep -rn "records.attached" code_atlas`
  still names three readers (still true). → `docs/ENGINEERING_RULES.md`, the maintainer's `/mango:promote`.

**The final gate** (live checkout):

Ran at b4ae92c3

```
$ scripts/gate.sh
      2 failed, 4954 passed, 4 skipped, 1 xfailed in 666.27s (0:11:06)
GATE RED — 1 check(s) failed
```

The two failures are 411's host exclusions (`test_install_skew.py`, `test_release_discipline.py`, the host's installed
tool read through the live checkout). In a clean worktree at the same SHA:

```
$ .venv/bin/python -m pytest -q tests/test_install_skew.py tests/test_release_discipline.py
29 passed, 1 xfailed in 15.87s
```

Ran at b4ae92c3.

### Outward actions

Under the handover: push `feat/412-records-direct-first`; open its PR against `feat/411-route-key-collisions`.
Deferred to the maintainer: ratify W1–W4, merge after #109.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 47,976 |
| 3 execute | `implementer` — not dispatched; main loop implemented | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | ticket-blind `challenger` | 1 | 61,470 |

`LEDGER TOTAL: 109,446 · top cost driver: 4 review / challenger` — main loop unmeasured.
