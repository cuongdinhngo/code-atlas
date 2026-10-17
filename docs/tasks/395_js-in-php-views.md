---
id: 395
slug: js-in-php-views
title: 'JavaScript inside a PHP view and AngularJS controller members are not symbols, so a template-to-controller question is Grep only'
phase: 2
milestone: Coverage
status: done
depends_on: [361]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). 361 links a JS
route string to its PHP action. The front-end code that the PHP views carry or call is still
outside the graph. 4 PRs:

- F1 (1 PR): handlers defined in an inline `<script>` block of a `.php` view are not indexed, so
  the handlers were found with Grep. (361 left inline `on*=` attributes out for the same reason.)
- F2 (1 PR, scored 4/10): the whole question was "which `ctrl.X(` calls in the region's template
  name no member of its AngularJS controller". Members declared as `self.X = function` /
  `$scope.X = …` inside the controller function are not symbols.
- F3 (1 PR): `ng-model="filters.x"` bindings in PHP templates are the consumers of a model key.
  Finding them took `git grep`.
- F4 (1 PR): a PHP `loadScripts(['js/x.js'])` list names the asset, but nothing links the
  page to the file, so "who loads this script" was Grep.

## Scope

1. Measure first: on the anchor index, count the PHP files with inline `<script>` blocks, and the
   `this.X = function` / `self.X = function` / `$scope.X =` member assignments. Order the items
   below by those counts.
2. The TS adapter emits members assigned on `this`, or on a local bound to `this`
   (`var self = this`), inside a plain function as Methods of that function — the ES5 constructor
   pattern, language spec only. Registration (`.controller(…)`) and `$scope` are framework
   semantics and stay out of the adapter (R2.2); `$scope` members get a count, not a rule.
3. Embedded `<script>` regions of a PHP file are handed to the JS reader with their offsets, so
   their functions are symbols of that file.
4. Template references (`ctrl.X(`, `ng-model`, an asset path in a declared include-list call) are
   declarative, through the existing `keyed_calls` rule file. No new rule kind (R1.2).

## Acceptance criteria

- **AC1:** `function EditCtrl(){ var self = this; self.save = function(){}; }`: `search_symbol save`
  finds it as a Method of `EditCtrl`.
- **AC2:** A `.php` view with `<script>function onPick(){}</script>`: `file_outline` lists `onPick`
  at its true line.
- **AC3:** With a rule, `ctrl.save(` in a template is a `HEURISTIC` caller of that member. A
  `ctrl.missing(` stays unlinked and is counted.
- **AC4:** An index with no such files is byte-identical.

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 395 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W2–W5 (above all the split to 396), runs E1, then merges after #77. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 388 - 389 - 394 - 390 - 391 - 393 - 395 - 392 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/395-js-in-php-views`, **stacked on `feat/393-factory-receiver`**. Contract `.mango/run-contract-395.txt`.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 14 unresolved surfaced | 5 want-decision asked | 9 how-decision resolved+cited | 4 ASSUMED | skip: no`

**Premise.** 361's route-string linking, the TS adapter (`adapters/typescript/src/parse.js`), `keyed_calls`
(`docs/TOOLS.md`) and `search_symbol` / `file_outline` resolve. Ambiguous: "the anchor index".

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 55,654 tokens) raised ten. Its first two set W3–W4:
a `.php` file's suffix has one adapter (`code_atlas/adapter.py` `extension_index`), so its `<script>` reaches the JS
reader only through a new handshake field and a contract bump, or a JS reader inside the PHP adapter; template text
is not a call, so `keyed_calls` cannot match it.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | what a "plain function" is | how | a named `function` declaration or a variable-bound function expression; an arrow cannot construct, and a class constructor's assignment is a field (R2) |
| H2 | whose `this` | how | an arrow inherits it; any other function, and a class, rebinds it — the spec's rule, as `thisClass` already reads it |
| H3 | the alias | how | `var x = this` in the function's own body, bound before the assignment and never reassigned |
| H4 | the value | how | a function or an arrow; any other value is not a callable member |
| H5 | the qname | how | `F::member`, the container convention every member already uses (CONVENTION §3) |
| H6 | a member assigned twice | how | one Method at its first assignment; both bodies source at it (R4.2: source order) |
| H7 | a nested declaration of the same name | how | it keeps the name; no member is emitted, so no duplicate qname |
| H8 | declarations-only mode (039) | how | the members are declarations, so they are emitted; their bodies are not walked |
| H9 | a member body's edges | how | sourced at the member, as a class method's are |
| W1 | AC-field (anchor) | want | **asked, settled by the maintainer (2026-10-17):** E1 |
| W2 | Scope 1's count and order | want | **ASSUMED (awaiting ratification):** the count rides E1; unmeasured, the order is cost — Scope 2 first, being spec-only and seam-free |
| W3 | Scope 3, `<script>` regions (AC2) | want | **ASSUMED (awaiting ratification):** deferred to 396 — a contract bump, or a second JS reader, on an unmeasured count |
| W4 | Scope 4, template references (AC3) | want | **ASSUMED (awaiting ratification):** deferred to 396 — no existing rule matches template text, and a new one breaks R1.2 |
| W5 | where the `$scope` count lands | want | **ASSUMED (awaiting ratification):** E1's replay, no new field |

## Phase 1 — analysis

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=4 G=1 AC=5`
`CLARIFICATION: 14 raised | 14 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/4 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

Stacked on 393. `main`'s full suite: `4565 passed, 4 skipped, 1 xfailed in 522.39s (0:08:42)`. Ran at daa6baa0.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| F2 controller members | `self.save = function` is no symbol | a Method of the controller function |
| F1/F3/F4 view references | not read | 396 |

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a template-to-controller question is Grep only" | the controller half becomes symbols | ⏳ |
| C1 | AC4 | "byte-identical" | output changes only where the pattern is | ⏳ |
| R1 | Scope 1 | "Measure first" | W2 → E1 | ⏳ |
| R2 | Scope 2 | "members assigned on `this` … as Methods" | H1–H9 | ⏳ |
| R3 | Scope 3 | "Embedded `<script>` regions" | W3 → 396 | ⏳ |
| R4 | Scope 4 | "Template references" | W4 → 396 | ⏳ |
| AC1 | AC | `search_symbol save` finds a Method of `EditCtrl` | | ⏳ |
| AC2 | AC | `file_outline` lists `onPick` | W3 → E2 | ⏳ |
| AC3 | AC | `ctrl.save(` a `HEURISTIC` caller | W4 → E2 | ⏳ |
| AC4 | AC | byte-identical | | ⏳ |
| AC5 | AC-field | anchor | W1 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — one row, its kind and qname | |
| AC2 | yes | E2 |
| AC3 | yes | E2 |
| AC4 | yes — the existing TS suites and conformance unchanged | |
| AC5 | no — the anchor | E1 |

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.2 (change-type) ✅ no new rule kind, Scope 4 deferred rather than one invented · §R2 (change-type) ✅ the spec's this-binding only, no controller or scope semantics · §R4.2 (change-type) ✅ source order, insertion-ordered maps · §R6.5 (change-type) ✅ seen red on 393's tip · §R7.6 (change-type) ✅ the TS README node table gains one row`

## Phase 2 — design

### Approach

1. TS adapter: `emitConstructorMembers` scans a named plain function's own body (H2) for aliases, reassignments and
   nested declarations, then emits each live member as a Method with its CONTAINS; `walk` sources a member's body at it.
2. Docs: TS README node table, CHANGELOG `Unreleased`; task 396 filed for Scopes 3–4.

### Rejected alternatives

- **The TS adapter also claiming `.php`** — `extension_index` refuses a suffix two adapters claim.
- **Reading `ctrl.X(` with a PHP-side pattern** — framework text in an adapter (R2.2).

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| a Function may contain a Method | verified | a nested function is already `F::inner`; nothing in the core keys a Method's container kind |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | constructor members | `adapters/typescript/src/parse.js` | TS/JS emission, only where the pattern is | R2, C1 | 1/1 |
| 2 | proving test | `tests/test_es5_constructor_members.py` (new) | — | AC1, AC4 | 1/1 |
| 3 | docs | `adapters/typescript/README.md`, `CHANGELOG.md` | doc budgets | G1 | 2/2 |
| 4 | the split | `docs/tasks/396_php-view-script-regions.md` (new) | backlog | R3, R4 | 1/1 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — TS adapter + build + tool | real build | authored | ✅ |
| AC2 | integration | — | — | ❌ → E2 |
| AC3 | integration | — | — | ❌ → E2 |
| AC4 | integration | the TS suites and conformance, unchanged | existing | ✅ |
| AC5 | runtime — anchor | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** AC-field and Scope 1's count · risk: low · why: the anchor index is not
on this machine · escalated, answered by the maintainer 2026-10-17 · follow-up: on the anchor, count PHP files with
inline `<script>` and the `this.X = function` / `self.X = function` / `$scope.X =` assignments; replay F2's question
before/after · `expiry: when the anchor index is available to a maintainer run` · `seen: 378, 384, 388, 389, 394, 390, 391, 393, 395`.

**E2 (scope exclusion, delegated).** AC2 and AC3 · risk: medium — F1, F3 and F4 stay Grep · why: W3–W4, a contract
seam on an unmeasured count · decided under the handover's delegation, awaiting ratification · follow-up: task 396 ·
`expiry: when 396 opens, gated on E1's count`.

`EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_es5_constructor_members.py` — red on 393's tip (`3 failed`), green after.

### Rollback

`git revert`; a full rebuild drops the members. Merge after #77 (stacked).

## Phase 3 — execute

Commit `6a83743d`.

**Red first.** The proving test with 393's `parse.js` (a66175f6): `3 failed in 1.73s`.

**Green after.** `3 passed in 1.67s`; `tests/contract` plus every `tests/test_ts_*.py`: `559 passed`, one red —
`test_ac4_exactly_one_module_spawns_an_adapter_in_one_shot_file_mode`, 390's own, fixed on 390 (`96c1d138`) and
carried in by the rebase. `tsc` clean. Ran at 6a83743d.

**Axis 1.** Change-list rows 1–4. **Axis 2.** Approach bullets 1–2 implemented as approved.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` — verdict **partial (challenger only — REVIEWER: OFF)**: the slice
built is clean; AC2 and AC3 are not met, by E2.

**Challenger** (ticket-blind: raw ticket plus `git diff a66175f6..HEAD` without this file; 1 dispatch, 57,355
tokens): 3 met · 5 not met (S2c, S3, S4, AC2, AC3 — E1/E2) · 3 can't tell (S1, AC4 by corpus, AC-field). Two Major,
four Minor:

| # | Finding | Resolution |
|---|---|---|
| M1 | `function save(){}` beside `this.save = function` gave two `C::save` nodes | a nested declaration keeps the name (H7, 3f81f3b4) |
| M2 | a repeated member merges into the first | kept and stated (H6): one Method, both bodies its |
| m1 | a reassigned alias still declared members | reassigned aliases drop out (3f81f3b4) |
| m2 | an alias used before its `var` declared members | bound before use (3f81f3b4) |
| m3 | an alias in a nested block was missed | the scan covers the function's own body (3f81f3b4) |
| m4 | `this['x'] =` is not read | kept: a computed name is not a declaration |

**Red first.** The challenger test against 6a83743d: `1 failed, 3 passed in 1.82s`. **Green after:** `4 passed in
1.85s`; `ruff`, `mypy`, `tsc` clean. Ran at 3f81f3b4.

| Row | Ph3/4 proven by | k/N |
|---|---|---|
| G1 / R2 / AC1 | `test_ac1_…`, `test_this_a_variable_bound_…`, `test_a_members_body_…`, `test_challenger_only_a_live_alias_…` | 4/4 |
| C1 / AC4 | TS suites and conformance unchanged | 1/1 |
| R3 / R4 / AC2 / AC3 | E2 → 396 | 0/4 (excluded) |
| R1 / AC5 | E1 | 0/2 (excluded) |

Reviewed at 3f81f3b4 — files: change-list rows 1–3. Working doc: `docs/tasks/395_js-in-php-views.md`.

## Phase 5 — finalise

**Durable lesson.** None new as a claim.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Stale-review guard: after 3f81f3b4 only this file, `docs/tasks/396_…`, `docs/BACKLOG.md` and `docs/TOKEN_LEDGER.md`
change. Not stale.

### Outward actions

Under the handover: push `feat/395-js-in-php-views`; open the PR against `main` (stacked on #77).
Deferred: ratify W2–W5 and the 396 split; E1; merge after #77.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 55,654 |
| 4 review | `challenger` (ticket-blind) | 1 | 57,355 |

`LEDGER TOTAL: 113,009 · top cost driver: challenger`
