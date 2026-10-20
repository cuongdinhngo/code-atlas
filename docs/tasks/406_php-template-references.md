---
id: 406
slug: php-template-references
title: "A PHP template's `ctrl.X(`, `ng-model` and asset-list references are not in the graph — evidence-gated"
phase: 2
milestone: Coverage
status: done
depends_on: [399]
---

## Why this exists

Split out of [399](399_php-view-script-regions.md) on 2026-10-19, so 399 carries only the inline
`<script>` half. The anchor's second field retro (2026-10-10 → 10-17) asked for:

- F2/F3: `ctrl.X(` and `ng-model="…"` in templates.
- F4: `loadScripts(['js/x.js'])` naming an asset.

Template references are not calls, so `keyed_calls` cannot match them. The rule fires on a parsed
call with a one-line string argument. An array-of-paths key (F4) is a new `key_from`.

**Anchor count (2026-10-19, `grep`, maintainer run):** `ng-model=` / `ctrl.X(` 1,716 whole repo, 1,669
under `src/`. **Evidence gate:** the count is in; this opens once 399 has shipped the embedded-region
seam, since a template's controller lives in that `<script>`.

## Scope

1. Template references are read through a declared rule, with no new rule kind unless none fits
   (395 AC3: `ctrl.save(` is a `HEURISTIC` caller; `ctrl.missing(` is counted).
2. An array-of-paths include list (F4) names its assets.

## Acceptance criteria

- **AC1:** 395's AC3, as written there.
- **AC2:** An index with no such files is byte-identical.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 406 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies A1–A4, merges, runs E1. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 406 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/406-php-template-references` off `main` (3635eeef). Contract `.mango/run-contract-406.txt`.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 4 want-decision asked | 8 how-decision resolved+cited | 4 ASSUMED | skip: no`

**Premise.** `keyed_calls` and `key_from` (`code_atlas/enrichment.py` `_keyed_call`), 395's AC3, and 399's embedded-region
seam (`code_atlas/embedded.py`, merged in #96) resolve.
**Recall.** `widen-every-query-that-shares-the-page` (362-C1): a new rule edge must reach the rule census, not only the
edges (H6). `read-a-literal-by-its-structure-not-a-regex` (361-C1): a list's entries come from the depth-aware split
`_top_level_entries`, each exactly one literal (H7). `a-zero-must-count-what-the-search-cannot-see` (363-C1): a reference
whose controller cannot be told is counted, not dropped (A2).

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 46,811 tokens) raised twelve. They are H1–H8 and A1–A4 below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the evidence gate | how | met: 399 shipped the region seam (#96, release 0.7.0), and the ticket says the count is in |
| H2 | which layer reads template text | how | the core, applying a rule file's regex to indexed files' text — rules live outside `adapters/` (R2.2) and the core holds no framework branch (R1.1); an adapter-side reader would be framework text in an adapter |
| H3 | the edge's source | how | the template's File node (qname = path, CONVENTION §3) at the match's line, as a guest edge sourced at the file is (399 H10) |
| H4 | the edge's tier | how | `HEURISTIC` with `rule: true`, as every rule edge (TOOLS.md, Indirection rule files) |
| H5 | where a miss is counted | how | `rule_keys_unresolved` and `rules_unresolved`, the existing rule census (TOOLS.md "Nothing is invented") — no new report field |
| H6 | every query behind the census | how | a template site and its stamps join `keyed_call_sites` / `keyed_call_groups`, so both counts see it (362-C1) |
| H7 | F4's list shape | how | `key_from: "list"`: an argument that is a `[…]` / `array(…)` literal; each top-level entry that is exactly one string is a key, any other entry names nothing; the call's first line, as `object` (361-C1, TOOLS.md) |
| H8 | what an asset path names | how | the template spells the stored File qname (`"public/{key}"`); `target_template` may name a File (256) |
| A1 | a new rule kind | want | **ASSUMED (awaiting ratification):** a `template_refs` section — text is no call, so no `keyed_calls` field fits (the ticket's own Why, 395 W4) |
| A2 | which controller `ctrl` names | want | **ASSUMED (awaiting ratification):** an optional per-file `context_pattern` whose named groups fill the template; a file where it finds no value, or two, links nothing and counts every reference |
| A3 | `ng-model` | want | **ASSUMED (awaiting ratification):** a rule may say `kind: "REFERENCES"`; it links when the member is a symbol, else it is counted |
| A4 | AC-field (395) on the anchor | want | **ASSUMED (awaiting ratification):** not 406's AC; recorded as E1 |

Out of scope: `.html` files (no adapter indexes them, so no File node to source an edge), `$scope` semantics (395 W5),
`key_pattern` on a list key (refused today for any `key_from` but `"string"`).

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=2 G=1 AC=3`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/6 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`BASELINE: red — tests/test_release_discipline.py::test_the_top_release_is_tagged`

### BASELINE

`.venv/bin/pytest -q` at 3635eeef, with this run's edits landing mid-run: `8 failed, 4860 passed, 4 skipped in 733.23s`.
The eight re-run on a clean worktree of 3635eeef: `1 failed, 7 passed in 5.35s` — seven reds were the edits (the server
saw its package bytes change). The one left, `test_the_top_release_is_tagged`, is pre-existing: 0.7.0 is untagged (399's
deferred step). **Baseline exclusion** — outside this change; the DoD is a green delta. Ran at 3635eeef.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| F2 `ctrl.X(` | template text is no edge; `find_callers` on `EditCtrl::save` is empty | a declared rule makes the view a `HEURISTIC` caller; a miss is counted |
| F3 `ng-model` | not read | the same rule, `kind: REFERENCES` |
| F4 `loadScripts([...])` | `key_from` reads a string, an object, or array keys (`enrichment.py` `_keyed_call`) | `key_from: "list"` names each asset File |

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "F2/F3 … F4" | the three shapes answer without Grep | ⏳ |
| C1 | AC2 | "byte-identical" | no rule → no row changes | ⏳ |
| R1 | Scope 1 | "read through a declared rule" | A1–A3, H2–H6 | ⏳ |
| R2 | Scope 2 | "an array-of-paths include list … names its assets" | H7–H8 | ⏳ |
| AC1 | AC | 395 AC3: `ctrl.save(` a `HEURISTIC` caller; `ctrl.missing(` counted | | ⏳ |
| AC2 | AC | byte-identical | | ⏳ |
| AC-field | 395 | the anchor replay | A4 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — one `find_callers` row (`rule: true`, `HEURISTIC`) and `rule_keys_unresolved == 1` | |
| AC2 | yes — every existing rule and enrichment suite unchanged, and a build without `template_refs` writes the same rows | rows, not database bytes |
| AC-field | no — the anchor is not on this machine | E1 |

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the core applies a declared regex to any indexed file; no language or framework name · §R1.2 (change-type) ✅ one new rule section where the ticket says none fits (A1); list is a value of the existing key_from · §R2.2 (change-type) ✅ ctrl, ng-model and loadScripts live only in the rule file and the test · §R4.2 (change-type) ✅ files in sorted order, matches in source order, edges sorted as keyed_calls sorts them · §R5.2 (change-type) ✅ every template edge HEURISTIC; an undecidable controller links nothing, never a guess · §R5.6 (change-type) ✅ template stamps join both censuses, so a zero never attests past them (362-C1) · §R7.6 (change-type) ✅ TOOLS.md's rule-file section gains two bullets and the stale "template text is no rule" claim is not repeated`

The three recalled handles are proposed claims, not promoted rules: they add 0 sections and are answered inline above.

## Phase 2 — design

### Approach

1. **`template_refs`** (A1–A3, H2–H4): a rule names `files` (globs over the repo-relative path), a `pattern` whose named
   groups fill `target_template`, an optional `context_pattern` whose groups, found once per file, fill it too, `{path}`
   the file read, and `kind` `CALLS` | `REFERENCES`. `enrichment.py` reads every indexed file a glob matches, in sorted
   order, and emits one `HEURISTIC` edge per match, sourced at the File at the match's line, on the rule bookmark.
2. **Census** (H5, H6): each match is a site with its stamp (none when the context is not one value), merged into
   `keyed_call_sites` / `keyed_call_groups`, so `rule_keys_unresolved` and `rules_unresolved` count it.
3. **`key_from: "list"`** (H7, H8): a `[…]` / `array(…)` argument; each top-level entry that is exactly one string
   literal (a double-quoted `$` excepted) is a key, through `_call_argument` and `_top_level_entries`.
4. Docs: TOOLS.md's rule-file section, PLAN §11's rule summary, CHANGELOG `Unreleased`.

### Rejected alternatives

- **A `keyed_calls` field for text** — a rule there fires on a parsed call's argument; template text has none (395 W4).
- **The PHP adapter reading attribute values** — `ng-*` is framework text in an adapter (R2.2).
- **Resolving `ctrl` by a short-name suffix match** — any `*::save` would do; a declared per-file binding names one.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| a rule edge from a view's File links an exact guest qname | verified | spike: `calls` rule `web/edit.php` → `web/edit.php::EditCtrl::save` gave one `HEURISTIC`, `rule: true` caller |
| the PHP adapter types a list literal `array` | verified | `--file` on `loadScripts([...])` and `array(...)`: `args: ['array']` |
| a changed template is re-read on incremental | verified | `indexer.py` `incremental_update`: any parse re-runs `_count_late_writes` |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `template_refs`, census, `key_from: "list"` | `code_atlas/enrichment.py` | rule builds only | R1, R2, AC1, C1 | 1/1 |
| 2 | proving test | `tests/test_php_template_references.py` (new) | — | AC1, AC2, R1, R2 | 1/1 |
| 3 | docs | `docs/TOOLS.md`, `docs/PLAN.md`, `CHANGELOG.md` | doc budgets | G1 | 3/3 |
| 4 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

The three recalled claims are proposed, not promoted (0 type-2 handles in the rule book); each is answered in Phase 0.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — PHP + TS adapters + build + tool | real build, `find_callers`, `BuildReport` | authored | ✅ |
| R1 `REFERENCES`, ambiguity | integration | real build, `find_references` / `find_callers` | authored | ✅ |
| R2 list | integration | real build, `find_references` on the File | authored | ✅ |
| AC2 | integration | rows equal with and without an empty `template_refs`; existing rule suites unchanged | authored + existing | ✅ |
| AC-field | runtime — anchor | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** AC-field · risk: low · why: the anchor index is not on this machine ·
escalated, answered by the maintainer 2026-10-17 (395 W1) · follow-up: on the anchor, write the two rules for its
`ng-controller` / `loadScripts` shapes and replay F2–F4 · `expiry: when the anchor index is available to a maintainer run` ·
`seen: 378, 384, 388, 389, 394, 390, 391, 393, 395, 399, 406`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/pytest -q tests/test_php_template_references.py` — red on 3635eeef (`9 failed, 1 passed`; the pass is AC2's
off state), green after.

### Rollback

`git revert`; the next build drops the rule rows.

## Phase 3 — execute

Commits `f1ad7366` (code + test), `e664f646` (docs).

**Red first.** The proving test on 3635eeef: `9 failed, 1 passed in 4.89s` — the pass is AC2's off state, which holds
before and after.

**Green after.** `tests/test_php_template_references.py` `10 passed in 3.82s`; with every rule suite
(`test_keyed_calls_*`, `test_indirection_enrichment`, `test_js_route_strings`, `test_string_arg_names_a_symbol`,
`test_keyed_string_arg_span`, `test_table_name_string_writes`, `test_rules_stale`, `test_core_is_language_agnostic`):
`410 passed in 30.80s`. `ruff check .` clean, `mypy` `no issues found in 112 source files`, doc budgets `9 passed`
after PLAN's addition was trimmed to fit (20,003 → under 20,000). Ran at e664f646.

**Axis 1.** Change-list rows 1–3, and row 4 at finalise. **Axis 2.** Approach bullets 1–4 implemented as approved; one
detail: `ruff format` would rewrite untouched lines of `enrichment.py`, so only the new lines were wrapped by hand
(the gate runs `ruff check`, not `format`).

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` — verdict **clean (challenger only — REVIEWER: OFF)**.

**Challenger** (ticket-blind: raw ticket plus `git diff 3635eeef..HEAD` without this file; 1 dispatch, 77,381 tokens):
6 met · 0 not met · 0 can't tell. No wrong link (a rival `EditCtrl::missing` in another view and a bare `missing()`
stayed unlinked); an incremental after editing two views gave the full build's rule rows. One Major, four Minor:

| # | Finding | Resolution |
|---|---|---|
| M1 | a list split over lines, or `array (…)` with a space, named nothing and was counted nowhere | an array-typed argument with no one-string entry counts in the rule's `keys_unread`; `array\s*\(` any case (0415f17c) |
| m1 | an entry carrying a comment is skipped silently | kept: one counted miss per unread list, as `object` does for a field |
| m2 | a `template_refs` rule that matches nothing counts nowhere | kept: `keyed_calls`' own `rules_unresolved` counts a rule that emitted and linked nothing, the same rule (`if group:`) |
| m3 | the documented `\bctrl\.` also matches `$ctrl.` / `vm.ctrl.` | the example and the test read `(?<![\w$.])ctrl\.`; the fixture's line 13 proves neither links (0415f17c) |
| m4 | a line by `count` per match, a file read per rule | newline offsets bisected; one read per file per build (0415f17c); edges also sort by `kind` |

**Red first.** The strengthened test against f1ad7366's `enrichment.py`: `1 failed, 9 passed in 3.62s`. **Green after:**
`10 passed in 3.58s`; the rule suites and doc budgets `419 passed in 28.20s`; `ruff`, `mypy` clean. Ran at 0415f17c.

| Row | Ph3/4 proven by | k/N |
|---|---|---|
| G1 / R1 / AC1 | `test_ac1_…`, `test_a_model_binding_…`, `test_an_undecidable_controller_…` | 3/3 |
| R2 | `test_a_list_of_asset_paths_…` | 1/1 |
| C1 / AC2 | `test_ac2_no_rule_writes_the_same_rows`; existing rule suites unchanged | 2/2 |
| AC-field | E1 | 0/1 (excluded) |

Reviewed at 0415f17c — files: change-list rows 1–3. Working doc: `docs/tasks/406_php-template-references.md`.

## Phase 5 — finalise

**Durable lesson.** A reader with a known blind spot (the call's first line) must count what it could not read; the
list reader shipped silent on a multi-line list until the challenger replayed one. Recorded as a third sighting of
363-C1 (`a-zero-must-count-what-the-search-cannot-see`), not a new claim.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 1 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`

Falsify: the strengthened list test against f1ad7366 — `1 failed, 9 passed`. Cannot promote: an unattended run;
`seen: 363, 397, 406` crosses two keys, so `/mango:promote` is the maintainer's cross-ticket pass.

Stale-review guard: after 0415f17c only this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`
change. Not stale.

### Outward actions

Under the handover: push `feat/406-php-template-references`; open its PR against `main`.
Deferred to the maintainer: ratify A1–A4, merge, E1 on the anchor, `/mango:promote` for 363-C1.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 46,811 |
| 4 review | ticket-blind `challenger` | 1 | 77,381 |

`LEDGER TOTAL: 124,192 · top cost driver: 4 review / challenger` — main loop unmeasured.
