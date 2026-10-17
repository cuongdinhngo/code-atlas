---
id: 396
slug: rules-stale
title: 'An index built under other indirection rules answers as current, and a rules-only change waits for a full rebuild'
phase: 2
milestone: Freshness
status: done
depends_on: [040, 080, 385]
---

## Why this exists

This comes from the anchor project (2026-10-17). The anchor drafted three more rule blocks
(`keyed_calls` table writes, a `routes` TSV) and stopped before committing them: no session could
tell whether its index had been built under them, so a rule-fed answer was unverifiable.

- F1: `load_indirection_rules` computes `RulesPayload.digest` (`enrichment.py:87-116`), and nothing
  stores or compares it. An index built before a rule edit, or with the knob off, still reports
  `current`. `find_view_data`, the rule-fed writers in `find_references` and a route lookup answer
  from the old rules with no label.
- F2: a true no-op incremental skips enrichment and the resolve (`indexer.py:598-619`, task 080).
  A rule edit with no source change is applied only by the next build that parses a file, or by
  `--full` (~550 s on the anchor). The anchor's setup doc has to say "a rule change applies only on
  `--full`", and the background refresh hooks never apply one.
- F3: a `routes` TSV is digested with its rule file, so the same gap covers a regenerated table.

Each session builds at a different time and from different rules, so a rule is only as
trustworthy as the least-recently-built index that answers with it.

## Scope

1. The build stores the rules digest in meta (empty when the knob is off).
2. `get_index_status` recomputes the digest from the rule files on disk and reports
   `rules_stale: true` with both digests when they differ; the summary names the build that
   clears it.
3. A rule-fed answer on a `rules_stale` index is labelled (`rules_stale`, never `ok`) and keeps its
   rows; an answer that reads no rule edge is unchanged.
4. An incremental build whose digest moved re-runs enrichment, `publish_routes` and the resolve
   scoped to the rules bookmark, even when nothing was parsed. Rules turned off clear the rows the
   same way.

## Acceptance criteria

- **AC1:** Build with a `view_data` rule, then edit the rule file: `get_index_status` reports
  `rules_stale: true`, and `find_view_data` answers labelled `rules_stale`.
- **AC2:** Then an incremental build with no source change: the new rule's edges are present, the
  build is not reported as a no-op, `rules_stale` is gone, and no file was re-parsed.
- **AC3:** Remove `indirection_rules`, incremental build: every rule-derived edge and the route
  table are gone.
- **AC4:** A routes TSV edited, nothing else: AC1 and AC2 hold for a route lookup.
- **AC5:** Digest unchanged: a no-op stays a no-op (same timing class as 080), and every answer is
  byte-identical.

- **AC-field:** on the anchor index, a rule edit followed by the background refresh answers
  `find_view_data` and a table's writers from the new rule with no `--full`; record the build time
  in the working doc.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 396 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W4, runs E1, then merges. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 396 - 398 - 397 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/396-rules-stale` off `main` (60d802c5). Contract `.mango/run-contract-396.txt`.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 17 unresolved surfaced | 4 want-decision asked | 13 how-decision resolved+cited | 4 ASSUMED | skip: no`

**Premise.** `load_indirection_rules` / `RulesPayload.digest` (`enrichment.py:87-116`), the no-op branch
(`indexer.py:598-619`), `publish_routes`, `get_index_status`, `find_view_data` and the routes TSV (385) resolve.
Ambiguous: "the anchor index".

**Recall (by handle).** `a-route-list-must-come-from-the-tools-verdict` (388-C1): the status flag and the tools'
label must ask one predicate. `seed-the-change-probe-with-the-first-answer` (374-C1): every build, the first
included, stores the digest. `widen-every-query-that-shares-the-page` (362-C1): enumerate every surface that reads
a rule edge or the route table.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 51,654 tokens) raised twelve; they are H3–H12 and W1–W2.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the digest lives | how | meta `indirection_rules_digest`, `""` when the knob is off (Scope 1), written by `_count_late_writes` beside `publish_routes` — the one call every build that applies rules makes |
| H2 | one predicate | how | `enrichment.rules_drift(config, store)` serves the status and every label (R1.8, 388-C1) |
| H3 | the label beside other reasons | how | `reason: ok` becomes `rules_stale`; any other reason stays, and `rules_stale: true` rides beside it — the 366 `ref_mismatch` pattern (`ref_check.py:188`), so "never ok" holds |
| H4 | `staleness` | how | unchanged; `rules_stale` is its own axis, as 178 split `index_complete` off `staleness` (`get_index_status.py:107-110`) |
| H5 | knob off, digest stored | how | stale; an incremental clears the rows (Scope 4's last sentence) |
| H6 | a rule file now missing or invalid | how | status never raises (050): `rules_stale: true`, `current: null`, `rules_error`; the build still fails loud (R5.3) |
| H7 | the build the summary names | how | `build_or_update_index` (an incremental); an escalation names itself on that tool's answer (172) |
| H8 | "not reported as a no-op" | how | `wrote.rules_reapplied: true`, `mode` stays `incremental` — `_run` reads a non-empty `scope` as a full build (`build_or_update_index.py:377`), and `asdict` carries a new field (`:513`) |
| H9 | the resolve's scope | how | `_count_late_writes` as is: the bookmark delta while the alias map holds, a full resolve when a rule alias moved it (096, `indexer.py:694-700`) |
| H10 | a build killed after enrichment | how | `build_complete = 0` is stamped before enrichment, so the next incremental escalates (202) and rewrites the digest |
| H11 | behind and rules-stale together | how | both reported; the flags are independent (H3/H4) |
| H12 | which bytes count | how | the existing digest: paths, rule bytes, TSV bytes (`enrichment.py:110-113`); a whitespace edit re-applies, never misses |
| H13 | the refresh hook | how | it already runs an incremental (`hooks/refresh.py:50`), so it applies a rule edit with no change of its own |
| W1 | which answers are rule-fed | want | **ASSUMED (awaiting ratification):** reason relabelled where the rows come from a rule — `find_view_data`, rule hits in `find_callers` / `find_references`, `trace_capability(route=)`, `impact(routes=)`; flag only on a route side-field (`search_symbol.routes`, `impact.routes` on a path/qname subject). A walk that crosses a rule edge (`impact` on a symbol, `explain_path`, `reachable_from`, `find_orphans`) is not labelled — no hit there carries `rule: true` |
| W2 | an index with no stored digest | want | **ASSUMED (awaiting ratification):** stale when rules are configured (it cannot show it was built under them, R5.6), current when not; one incremental clears it |
| W3 | Scope 3's `find_callers` | want | **ASSUMED (awaiting ratification):** included — Scope 3 says "a rule-fed answer", and `calls` / `keyed_calls` rules feed callers |
| W4 | AC-field (anchor) | want | **ASSUMED (awaiting ratification):** E1, the standing answer the maintainer gave 2026-10-17 (395 W1) |

## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=4 G=1 AC=6`
`CLARIFICATION: 17 raised | 17 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

`main`'s full suite: `4697 passed, 4 skipped, 1 xfailed in 573.67s (0:09:33)`. Ran at 60d802c5.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| F1 | the digest is computed and dropped | stored; status and rule-fed answers compare it |
| F2 | a rule-only edit waits for a parse or `--full` | an incremental re-applies it |
| F3 | a TSV edit is the same gap | covered by the same digest |

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a rule is only as trustworthy as the least-recently-built index" | every rule-fed answer knows its rules' age | ⏳ |
| C1 | AC5 | "a no-op stays a no-op … byte-identical" | the unchanged-digest path is untouched | ⏳ |
| R1 | Scope 1 | "stores the rules digest in meta" | H1 | ⏳ |
| R2 | Scope 2 | "`rules_stale: true` with both digests" | H2, H4, H6, H7 | ⏳ |
| R3 | Scope 3 | "labelled (`rules_stale`, never `ok`)" | H3, W1, W3 | ⏳ |
| R4 | Scope 4 | "re-runs enrichment, `publish_routes` and the resolve" | H5, H8, H9 | ⏳ |
| AC1 | AC | status stale, `find_view_data` labelled | | ⏳ |
| AC2 | AC | incremental applies, no parse, not a no-op | | ⏳ |
| AC3 | AC | rules removed → rows gone | | ⏳ |
| AC4 | AC | TSV edit → AC1/AC2 for a route | | ⏳ |
| AC5 | AC | unchanged digest → no-op, byte-identical | | ⏳ |
| AC6 | AC-field | anchor | W4 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — two fields | |
| AC2 | yes — edge present, `parsed == 0`, `rules_reapplied`, flag gone | |
| AC3 | yes — zero bookmark edges, no `routes` meta | |
| AC4 | yes — `trace_capability(route=)` reason before/after | |
| AC5 | yes — the 080 spies see no late writer; two answers compare equal | "same timing class" pinned as "no late writer ran" |
| AC6 | no — the anchor | E1 |

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.4 (change-type) ✅ enrichment computes the digest, the store only persists meta, tools only present · §R1.7 (change-type) ✅ the digest is its own meta key, not folded into the routes blob · §R1.8 (change-type) ✅ one rules_drift for the status and every label · §R4.2 (change-type) ✅ a rules-only incremental equals a full build of that state (AC2 asserts the rows) · §R5.6 (change-type) ✅ a pre-396 index is not attested current under rules (W2) · §R7.6 (change-type) ✅ TOOLS.md rows edited in place, CHANGELOG Unreleased, no new standing section`

## Phase 2 — design

### Approach

1. `enrichment.py`: `RULES_DIGEST_KEY`, `rules_digest(payload)`, and `rules_drift(config, store)` returning
   `(built, current, error)` when the files on disk differ from the build's, else `None`.
2. `indexer.py`: `_count_late_writes` stores the digest; `incremental_update` runs the late writers when nothing was
   parsed but the digest moved, and reports `rules_reapplied`.
3. `nav_result.py`: reason `rules_stale` and `attach_rules_stale(payload, config, store, relabel=…)`.
4. Tools: `find_view_data`, `find_callers`, `find_references`, `trace_capability`, `impact`, `search_symbol` call it
   per W1; `get_index_status` attaches `rules_stale` / `rules_digest` at every level and the summary names the build.
5. Docs: TOOLS.md, CHANGELOG `Unreleased`.

### Rejected alternatives

- **The digest as a `staleness` value** — `staleness` names the revision (178); a rule edit is not one.
- **Labelling in `schema_guard.guard`** — one place, but it would read every payload's shape to find a rule row.
- **A full resolve on every rule change** — 096 already scopes it, and widens it only when aliases move.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| a rules-only incremental parses nothing | verified | rule files and TSVs carry no adapter suffix, so `changed ∩ wanted` is empty |
| the bookmark-scoped resolve links the new rule edges | verified | `_count_late_writes` already adds `INDIRECTION_FILE` to the delta (`indexer.py:697-699`) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | digest helpers | `code_atlas/enrichment.py` | rules loading | R1, R2 | 1/1 |
| 2 | store and re-apply | `code_atlas/indexer.py` | every build; `BuildReport` gains a field | R1, R4, C1 | 1/1 |
| 3 | reason and label | `code_atlas/tools/nav_result.py` | `NAV_REASONS` (pinned by `tests/test_nav_reason_codes.py`) | R3 | 1/1 |
| 4 | the six rule-fed tools | `code_atlas/tools/{find_view_data,find_callers,find_references,trace_capability,impact,search_symbol}.py` | their envelopes, only when stale | R3 | 6/6 |
| 5 | status | `code_atlas/tools/get_index_status.py` | the summary, only when stale | R2 | 1/1 |
| 6 | tests | `tests/test_rules_stale.py` (new), `tests/test_nav_reason_codes.py` | — | AC1–AC5 | 2/2 |
| 7 | docs | `docs/TOOLS.md`, `CHANGELOG.md` | doc budgets | G1 | 2/2 |
| 8 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| Handle | Answer |
|---|---|
| `a-route-list-must-come-from-the-tools-verdict` | traced — `grep -n rules_drift code_atlas/tools/*.py` names one predicate in status and labels |
| `seed-the-change-probe-with-the-first-answer` | traced — the full build writes the digest (`test_ac5_…` reads it after the first build) |
| `widen-every-query-that-shares-the-page` | traced — `grep -rn "ROUTES_META_KEY\|RULE_FLAG" code_atlas/tools` → the six tools of row 4 |

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — build + rules + tool | real Python-adapter build, tool calls | authored | ✅ |
| AC2 | integration | real incremental, rows read back | authored | ✅ |
| AC3 | integration | real incremental with the knob removed | authored | ✅ |
| AC4 | integration | real build with a TSV, `trace_capability` | authored | ✅ |
| AC5 | integration | 080's spies plus two equal answers | authored | ✅ |
| AC6 | runtime — anchor | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** AC-field · risk: low · why: the anchor index is not on this machine ·
escalated, answered by the maintainer 2026-10-17 · follow-up: on the anchor, edit a rule, let the refresh hook run,
then ask `find_view_data` and a table's writers; record the build time · `expiry: when the anchor index is available
to a maintainer run` · `seen: 378, 384, 388, 389, 394, 390, 391, 393, 395, 396`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_rules_stale.py` — red on `main` (60d802c5), green after.

### Rollback

`git revert`; an index built by this branch keeps one unused meta key.

## Phase 3 — execute

Commits `e2c3738f` (code, tests), `81f0d4c7` (docs).

**Red first.** The proving test on `main` (60d802c5): `1 error during collection` — `RULES_DIGEST_KEY` does not exist.

**Green after.** `9 passed`; the related suites (`test_nav_reason_codes`, `test_route_table`, `test_noop_incremental`,
view-data, keyed-calls, status and build tests): `135 passed`. `ruff`, `mypy` clean. Ran at e2c3738f.

**Axis 1.** Change-list rows 1–7. Deviation: two more reason pins (`test_empty_answer_cannot_explain_itself.py`,
`test_relation_unmodelled_for_language.py` — `NAV_REASONS[-1]`) missed by the row-3 trace and found by the full
suite (P5); updated in `92592a0f`. **Axis 2.** Approach bullets 1–5 implemented as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` — verdict **clean (challenger only — REVIEWER: OFF)**.

**Challenger** (ticket-blind: raw ticket plus `git diff main..HEAD` without this file; 1 dispatch, 66,403 tokens):
9 met · 0 not met · 1 can't tell (AC-field, E1); Scope 3 "partly met" for M1.

| # | Finding | Resolution |
|---|---|---|
| M1 | walks over rule edges (`explain_path`, `reachable_from`, `find_orphans`, `impact` on a symbol) are not labelled | kept and recorded in W1: no hit there is flagged `rule: true`, so labelling them needs a new per-hop flag |
| m2 | a rule hit outside the returned page leaves the page unlabelled | kept: the rows shown are then not rule-fed |
| m3 | each rule-fed answer re-reads and hashes the rule files | kept: only when a hit is rule-fed; small next to the answer |
| m5 | no test for a delta that parses a file and moves the digest | `test_challenger_a_parse_and_a_rule_edit_…` (e04bcc61) |
| — | `impact(routes=)` untested; it carries no `reason`, so the relabel did nothing | an absent reason counts as `ok` (e04bcc61), `test_challenger_impact_on_a_route_…` |

**Red first.** The impact test against 81f0d4c7: `KeyError: 'reason'`. **Green after:** `11 passed`.

**Full suite** at e04bcc61: `2 failed, 4706 passed, 4 skipped, 1 xfailed in 668.07s` — the two reason pins above;
after `92592a0f` both pass (`17 passed`). The gate result is quoted in Phase 5.

| Row | Ph3/4 proven by | k/N |
|---|---|---|
| R1 / AC5 | `test_ac5_an_unchanged_digest_keeps_the_noop` | 1/1 |
| R2 / AC1 | `test_ac1_…` (both), `test_an_index_with_no_stored_digest_…`, `test_an_unreadable_rule_file_…` | 4/4 |
| R3 / AC1 / AC4 | `test_ac1_a_rule_edit_…`, `test_ac4_…`, `test_challenger_impact_…` | 3/3 |
| R4 / AC2 / AC3 | `test_ac2_…` (both), `test_ac3_…`, `test_challenger_a_parse_and_a_rule_edit_…` | 4/4 |
| C1 | `test_ac5_…`, 080's `test_noop_incremental.py` unchanged | 2/2 |
| AC6 | E1 | 0/1 (excluded) |

Reviewed at 92592a0f — files: change-list rows 1–7 plus the two pins. Working doc: `docs/tasks/396_rules-stale.md`.

## Phase 5 — finalise

**Durable lesson.** `396-C1` in `LESSONS.md`: a payload that omits `reason` reads as `ok`, so a relabel keyed on
`reason == "ok"` silently skips it. `seen:` gains 396 for the three traced handles (P1).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 1 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

`widen-every-query-that-shares-the-page` (362-C1) is at seen ≥ 2 again; it cannot promote in an unattended run —
`/mango:promote` is the maintainer's pass.

Stale-review guard: after 92592a0f only this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`
change. Not stale.

### Outward actions

Under the handover: push `feat/396-rules-stale`; open the PR against `main`. Deferred: ratify W1–W4; E1; merge.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 51,654 |
| 4 review | `challenger` (ticket-blind) | 1 | 66,403 |

`LEDGER TOTAL: 118,057 · top cost driver: challenger`

