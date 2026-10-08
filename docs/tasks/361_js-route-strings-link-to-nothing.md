---
id: 361
slug: js-route-strings-link-to-nothing
title: 'A route string in JavaScript links to nothing, so a PHP action called only from the front end reads as uncalled'
phase: 2
milestone: Coverage
status: done
depends_on: [352, 221]
---

## Why this exists

This comes from a field retro on an anchor PHP + SQL Server project (2026-09-30 → 10-07, 49
scored PRs). It is the gap reported most often: in 8 PRs the agent fell back to Grep, because the
real caller of a PHP action is a JS string.

- F1 (1 PR): `find_callers` on `deleteItemAction` → `relation_unmodelled_for_language`. The caller
  is `$.post('…action=deleteItem')`.
- F2 (2 PRs): `main.php?module=…&control=…&action=…` URLs in JS.
- F3 (2 PRs): a `{module, action}` JSON envelope, and AngularJS `$http.post` calls to one service
  endpoint script.
- F4 (1 PR): jQuery `ajax` URL literals in views.
- F5 (2 PRs): `onclick` attributes, and DOM ids in PHP `echo` strings, that name `public/js`
  functions.

The answer is honest, since 221 marks the zero as unmeasured. The gap is that the edge the agent
needs is never built.

## Scope

1. 352 shipped as the existing `keyed_calls` rule (222), which links only when the argument *is*
   the whole key (TOOLS.md *Configuration reference*). A route string is not: the key sits inside
   a URL. Extend `keyed_calls` with an optional key pattern whose capture fills `{key}` in
   `target_template`, so the rule file declares the project's route grammar (`action=X` →
   `XAction`, a `{module, action}` pair → a service method). Edges stay `HEURISTIC`,
   `rule: true`; nothing is hard-coded. No new rule kind (R1.2).
2. An inline `on*="fn(…)"` attribute string in a PHP view links to the JS function it names. When
   no definition matches, it stays unlinked and is counted. The anchor project excludes
   `public/js` (`path_excluded`), so prove this on a fixture, not on the anchor.
3. With no rule, the graph is unchanged.

## Acceptance criteria

- **AC1:** On a fixture with `$.post('main.php?action=deleteItem')`, `find_callers` on
  `…::deleteItemAction` returns the JS caller at `HEURISTIC`, with `rule: true`.
- **AC2:** A `{module, action}` object literal passed to a declared callee resolves the same way.
- **AC3:** A route string that names no action stays unlinked and is counted in
  `rule_keys_unresolved`. No edge is invented.
- **AC4:** An index with no rule of this kind is byte-identical.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 361 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews and merges the PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`, batch 365 → 366 → 361 → 362 → 364 → 363;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `feat/361-js-route-strings-link-to-nothing` from `main` (`fb256ec5`). Contract `.mango/run-contract-361.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 5 want-decision asked | 5 how-decision resolved+cited | 5 ASSUMED | skip: no`

**Premise.** `keyed_calls` (`enrichment.py` `_keyed_calls_edges`), `target_template`,
`rule_keys_unresolved` (`indexer.py:194`), TOOLS.md *Configuration reference*, `rule: true` (068) — all resolve.

**Recall (by handle — a shared rule vocabulary is extended).** `343-C2` `formatter-rewrites-untouched-lines`.

**Spike.** The TS adapter on `$.post('main.php?…&action=deleteItem', {id: id})` emits `CALLS post`,
`args: ['string','array']`, `arg_keys: [null, ['id']]`; `$.ajax({url: …})` → `ajax`, `args: ['array']`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 50,978 tokens) surfaced X1–X9; H1 is the
run's own. Want-decisions were handed back by the handover → **ASSUMED (awaiting ratification)**; the maintainer ratified them 2026-10-08 after the PR #34–#39 review.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | read `{module, action}` values (`arg_keys` holds keys only) | want | **Ratified 2026-10-08:** a core reader of the call's own one-line source — `_literal_fields` over `_call_argument`'s text (352's mechanism). No contract change (R3). Whole top-level `name: 'v'` / `'name' => 'v'` entries only; a nested, concatenated, `$`-interpolated or repeated field names nothing, a spread voids all. No language branch (R1.1) |
| X2 | several placeholders | want | **Ratified 2026-10-08:** a string `key_pattern`'s named groups fill exactly the same-named placeholders, else `{key}` — the loader refuses any other template (R5.3); `key_from: "object"` fills each placeholder, `{key}` included, from a same-named field, and a call lacking one yields no edge |
| X3 | pattern dialect | want | **Ratified 2026-10-08:** Python `re`, `search`, first match; named groups (all non-empty), else group 1, else the whole match, as `{key}`; no match → no route, not counted. The rule file is the repo's own trusted config, so no ReDoS guard |
| X4 | `$.ajax({url: …})` (F4) | how | out of reach: the URL is an object field, not a string argument (spike); filed to BACKLOG Follow-ups |
| X5 | Scope 2 (`on*=` attributes) | want | **Ratified 2026-10-08: deferred** — no call edge exists for an attribute (the PHP adapter would need an HTML-attribute reader) and a bare `fn` from PHP cannot link to `path::fn` without a resolver change (R5.2 forbids guessing). Filed to Follow-ups; deviation (P3) |
| X6 | cross-language bare-name linking | how | not made — see X5 |
| X7 | a URL the pattern does not match | how | not a route: no edge, not counted — TOOLS.md "Nothing is invented" (a variable argument is treated the same) |
| X8 | AC4 | how | the no-rule path returns before any rule code (`apply_indirection_rules`, `NOTHING`); a rule file without the new keys loads to the same edges (222/352 tests unchanged) |
| X9 | one literal read by two rules | want | **Ratified 2026-10-08:** one site per `(source, line, literal)` — counted once when no rule links it (today's key-based identity would count it per rule) |
| H1 | `key_pattern` with `key_from: "object"` or `"array_keys"` | how | refused at load: a pattern reads a string key |

## Phase 1 — analysis

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=4`
`CLARIFICATION: 10 raised | 10 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

`main` at `fb256ec5` has the tree of `4e05c246`, on which `scripts/gate.sh` printed
`GATE GREEN — all 21 checks passed`. Ran at 4e05c246.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "the edge the agent needs is never built" | a rule builds it | ✅ |
| C1 | Scope 1 | "nothing is hard-coded"; "No new rule kind (R1.2)" | `keyed_calls` grows two keys | ✅ |
| R1 | Scope 1 | key pattern / route grammar in the rule file | `key_pattern`, `key_from: "object"` | ✅ |
| R2 | Scope 2 | `on*=` attributes → JS function | X5: deferred, filed | ⚠ deferred |
| R3 | Scope 3 | no rule → graph unchanged | AC4 | ✅ |
| AC1 | AC | `$.post('…action=deleteItem')` → caller at HEURISTIC, `rule: true` | real PHP + TS build | ✅ |
| AC2 | AC | `{module, action}` object resolves the same way | same build | ✅ |
| AC3 | AC | names no action → unlinked, counted in `rule_keys_unresolved` | `BuildReport.rule_keys_unresolved == 1` | ✅ |
| AC4 | AC | no rule → byte-identical | no indirection rows, count 0 | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — one result, `confidence_tier == "HEURISTIC"`, `rule is True`, source `…::removeItem` | |
| AC2 | yes — same on `archiveItemAction`, source `…::archiveItem` | |
| AC3 | yes — `rule_keys_unresolved == 1`; the only unlinked rule row is `\App\ItemsController::nopeAction`; no row for `health.php` | |
| AC4 | yes — zero `INDIRECTION_FILE` edges, count 0 | "byte-identical" read as: the no-rule path writes no rule row (X8) |

### Gap analysis (enhancement)

- **Now.** `_keys_for_rule` keys only a whole-literal argument; the loader rejects any placeholder but `{key}`.
- **Target.** A rule declares where the key sits; the template takes named placeholders.

### Blast radius

- `RulesPayload.keyed_calls` / `_keyed_calls_edges` / the loader — `enrichment.py` only (grep: no other user).
- `count_unresolved_keyed_calls` / `count_unresolved_keyed_sites` read the stamps, unchanged in shape.
- Every test touching rules (22 files, 318 tests) green after the change.
- Docs: TOOLS.md *Configuration reference*; BACKLOG Follow-ups.

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the literal-field reader matches a quote/colon shape, never a language name · §R1.2 (change-type) ✅ keyed_calls is extended; no new rule kind · §R2.2 (change-type) ✅ jQuery/AngularJS appear only in the test fixture; the core names no framework · §R4.2 (change-type) ✅ edges and sites stay sorted · §R5.2 (change-type) ✅ rule edges stay HEURISTIC; an unmatched literal links nothing · §R5.3 (change-type) ✅ an unfillable template or a bad regex fails loud at load · §R6.5 (change-type) ✅ red on main, and the site-count test fails with the per-key identity restored`

## Phase 2 — design

### Approach

1. **`KeyedCall`** (NamedTuple) replaces the 4-tuple; `_keyed_call` validates one entry.
2. **`_keyed_values`** yields `(literal, placeholder values)` per call site: string keys through
   `key_pattern`, object keys through `_literal_fields`.
3. **`_keyed_calls_edges`** fills the template with `_fill` and keys sites by the literal.
4. **Docs** — TOOLS.md; BACKLOG Follow-ups for X4 and X5.

### Rejected alternatives

- **Values in the adapter contract** (`arg_values`): a contract bump and two adapters for a fact the
  call's own line already holds; 352 reads string keys from that line too.
- **A new rule kind for routes** — R1.2; the ticket says no.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | the TS adapter's `CALLS` for `$.post(...)` carries `args` and the call line | verified — spike |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | rule shape, loader, values, sites | `code_atlas/enrichment.py` | rule builds only | R1, C1, AC1–AC4 | 1/1 |
| 2 | fixture + proving tests | `tests/fixtures/js_route_strings/*`, `tests/test_js_route_strings.py` (new) | — | AC1–AC4, X9 | 2/2 |
| 3 | docs | `docs/TOOLS.md`, `docs/BACKLOG.md` | doc budgets | R1, R2 | 2/2 |
| 4 | bookkeeping | this file, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced: `ruff format` ran on the new test file only;
  `enrichment.py` had `ruff check` only (`All checks passed!`).

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | full build with the real PHP and TS adapters, `find_callers` | authored | ✅ |
| AC2 | integration | same | authored | ✅ |
| AC3 | integration | same, `BuildReport` + edge rows | authored | ✅ |
| AC4 | integration | build without rules | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_js_route_strings.py`.

### Rollback

`git revert`. A rule file using the new keys then fails loud at load (R5.3), which names the cause.

## Phase 3 — execute

Commit `a9cdb881`. **Order deviation:** code before this doc's design text (design settled in the
exposure classification first).

**Red first** — the proving file on `main` (`fb256ec5`): `3 failed, 2 passed, 3 errors`; the fixture's
rules were refused (`target_template must contain exactly the placeholder '{key}' (found
['module', 'action'])`) and two malformed rules did not raise. The site-count test fails with the
old per-key site identity restored (`assert 4 == 2`).

On `a9cdb881` the file gave `9 passed in 1.98s` (superseded by Phase 4's run).

**Sweep.** Axis 1: `git diff --name-only main..HEAD` = change-list items 1–3 exactly; `ruff check`,
`mypy code_atlas` clean. Axis 2: Approach 1–4 as approved. Rule suites (22 files): `318 passed`.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `a9cdb881`, 57,297 tokens): 6 met · 1 not met · 1 can't tell.**
The "not met" is Scope 2 — deferred (X5), recorded in BACKLOG, awaiting the maintainer's
ratification; the "can't tell" is AC4's "byte-identical", read here as X8. Dispositions:

1. **High: a nested object's field read as the call's own.** **Fixed** in `d10f8e8b` — fields come
   from a depth-aware split; an entry counts only when it is exactly a name and one string.
2. **Medium: half a concatenation / a ternary branch read as a value.** **Fixed** by the same.
3. **Low: a quoted key with a space read as its tail.** **Fixed** (the quote is a backreference).
   The new parametrised test fails 5/9 on `a9cdb881` and passes now.
4. **Low: shorthand / template values, multiline calls, a group-less pattern.** **Documented** in
   TOOLS.md: they name nothing, only one-line calls are read, and the whole match fills `{key}`.
5. **Low: mixed named/unnamed groups.** **Left:** named groups win; the loader's message names them.

Verify-only (main loop — every fix is inside the approved files):

Ran at d10f8e8b:
```
$ .venv/bin/python -m pytest -q tests/test_js_route_strings.py
18 passed in 1.87s
```
Every test touching rules plus the doc budget: `337 passed in 19.75s` on the same tree.

`Ph3/4 proven by`: G1, C1, R1, R3, AC1–AC4 — 8/8; R2 deferred (X5, follow-up filed) — 8/9.

Verdict: **clean (challenger only — REVIEWER: OFF)**, with R2 a recorded deferral.

Reviewed at d10f8e8b — the diff `main..d10f8e8b`. Working doc: `docs/tasks/361_js-route-strings-link-to-nothing.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `d10f8e8b` only bookkeeping changes — this doc, `docs/TOKEN_LEDGER.md`,
`docs/LESSONS.md` and `docs/BACKLOG.md`, all exempt.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

`361-C1` is type 2 (code), handle `read-a-literal-by-its-structure-not-a-regex`: a regex over a
literal's text matches nested and partial values; a reader that splits at top-level delimiters and
requires the whole entry to be one literal is what keeps a rule from linking a guess. First sighting.
Per P1, `343-C2` gains 361 (traced).

### Outward actions

1. Push `feat/361-js-route-strings-link-to-nothing` — pre-authorised.
2. Open the PR against `main` — pre-authorised.

Deferred to the maintainer: none.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 50,978 |
| 2 | review | `challenger`, round 1 | 57,297 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 108,275 · top cost driver: review/challenger`

**Gate.** `scripts/gate.sh` on `73ccdc5c`: `GATE GREEN — all 21 checks passed` (Linux, bare pytest). P8 does not
apply: no public sample uses the new rule keys, so no graph count moves.

**Revert path.** `git revert` the branch commits; a rule file using the new keys then fails loud at load.
