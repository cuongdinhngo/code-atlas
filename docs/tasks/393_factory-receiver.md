---
id: 393
slug: factory-receiver
title: 'A call on an object a factory returned, or on an untyped parameter, links to nothing, so find_callers lists only the test'
phase: 2
milestone: Coverage
status: done
depends_on: [362]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). 362 types a
receiver assigned from `new X()`. The field's next two shapes are still unlinked:

- F1 (1 PR): `find_callers Mailer::attach` returned only a test, because the
  production receiver is `$mail = Factory::make(); $mail->attach(…)`.
  `make()` declares `: Mailer` (or `@return Mailer`). The real call was found with Read.
- F2 (1 PR): `find_callers` missed the callers that receive `$model` as an untyped parameter. The
  only callers of that function pass one class, and the print paths were found with Grep.
- F3 (1 PR): a sweep confirmed callers with `find_callers` plus Grep "to be sure", because the
  answer could not say whether untyped receivers were in play.

## Scope

1. A local assigned from a call whose callee declares a return type (native, or `@return` at
   `HEURISTIC`) takes that type. That covers static factories and `$this->build*()`.
2. Measure F2 before building: count the untyped parameters on the anchor index whose resolved
   callers all pass one class. Infer from call sites only if that count justifies it. Otherwise file
   the count.
3. When an empty or partial answer has unresolved same-name calls on untyped receivers,
   `unresolved_receivers` counts them, so "is the list complete?" has an answer (F3).

## Acceptance criteria

- **AC1:** `$m = Factory::make(); $m->send();` with `make(): Mailer` gives
  `find_callers Mailer::send` one `HEURISTIC` row.
- **AC2:** The same with `@return Mailer` only.
- **AC3:** No existing `RESOLVED` edge changes tier, and an index with no such sites has the same
  edges and tiers (a docblocked method still gains `extra.doc_type`).

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 393 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W2–W4, runs E1, then merges after #76. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 388 - 389 - 394 - 390 - 391 - 393 - 395 - 392 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/393-factory-receiver`, **stacked on `feat/391-defaults-by-expr`**. Contract `.mango/run-contract-393.txt`.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 13 unresolved surfaced | 4 want-decision asked | 9 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** 362's `new X()` typing (`adapters/php/src/TypeTable.php`), `find_callers`, `confidence_tier`, the deferred
`()` chain (`code_atlas/resolver.py` `_resolve_deferred`) and `unlinked_same_name_sites` resolve. `unresolved_receivers`
is to-be-created. Ambiguous: "the anchor index".

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 64,777 tokens) raised ten;
its first is the AC1 contradiction (W3).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where `@return` is read | how | `MemberTypes`, beside the native types `memberOf` already reads (R1.4: one source) |
| H2 | native vs docblock | how | a native return type wins; `@return` is read only when there is none |
| H3 | docblock grammar | how | exactly one class, `?X` / `X\|null` allowed; unions, `X[]`, generics, PHP types and `self`/`static`/`$this` read as nothing (R5.6) |
| H4 | name resolution | how | the file's `NameResolver` context — `use` imports and the namespace — never a global guess (R2) |
| H5 | the tier mechanism | how | the adapter stores the docblock's class as `extra.doc_type`; the resolver reads it only after the native lookup misses and marks that chain `HEURISTIC` — a cross-file factory's type is only known in the core |
| H6 | `unresolved_receivers` cost | how | computed at query time from stored edges, omitted when zero — no index change (AC3) |
| H7 | inline `@var` | how | out of scope (exposure #8) |
| H8 | `extra.doc_type` vs the contract | how | `extra` is open per node kind; the edge and node vocabularies are unchanged, so no `contract_version` bump (R3) |
| H9 | the test fixture | how | cross-file factory (the F1 shape), with two classes declaring the method so a bare-name link cannot pass it |
| W1 | AC-field (anchor) | want | **asked, settled by the maintainer (2026-10-17):** E1 |
| W2 | Scope 2 — F2 call-site inference | want | **ASSUMED (awaiting ratification):** not built; the count needs the anchor index, so it rides E1's replay |
| W3 | AC1's tier for a native return type | want | **ASSUMED (awaiting ratification):** RESOLVED, as at base — AC1's `HEURISTIC` would move an existing edge, which AC3 forbids |
| W4 | what `unresolved_receivers` counts | want | **ASSUMED (awaiting ratification):** every caller edge in the subject's language whose raw target is the method's bare name — linked by name at `HEURISTIC` or not |

## Phase 1 — analysis

`PREMISE: 5 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=4`
`CLARIFICATION: 13 raised | 13 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/6 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

Stacked on 391. `main`'s full suite: `4565 passed, 4 skipped, 1 xfailed in 522.39s (0:08:42)`. Ran at daa6baa0.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| F1 factory receiver | a native return type links `RESOLVED` (`TypeTable.php` `memberOf`); `@return` is never read | `@return` links at `HEURISTIC` |
| F3 completeness | nothing says whether untyped receivers were in play | `unresolved_receivers` |

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "find_callers lists only the test" | the production factory call is a row | ⏳ |
| C1 | AC3 | "No existing `RESOLVED` edge changes tier" | H2, H6 | ⏳ |
| R1 | Scope 1 | "native, or `@return` at `HEURISTIC`" | H1–H5 | ⏳ |
| R2 | Scope 2 | "Measure F2 before building" | W2 → E1 | ⏳ |
| R3 | Scope 3 | "`unresolved_receivers` counts them" | H6, W4 | ⏳ |
| AC1 | AC | native `make(): Mailer` | W3 | ⏳ |
| AC2 | AC | `@return Mailer` only | | ⏳ |
| AC3 | AC | no tier moves; same edges and tiers | | ⏳ |
| AC4 | AC-field | anchor | W1 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — one row, its tier | W3: asserted `RESOLVED` |
| AC2 | yes — one `HEURISTIC` row; the twin class gets none | |
| AC3 | yes — the existing suites; `doc_type` absent without a docblock | |
| AC4 | no — the anchor | E1 |

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.4 (change-type) ✅ the store decodes doc_type · §R2 (change-type) ✅ the docblock grammar is the language's, names resolve through use · §R3 (change-type) ✅ no vocabulary change, extra is open · §R5.6 (change-type) ✅ a docblock link is HEURISTIC, unions read as nothing · §R6.5 (change-type) ✅ seen red on the base · §R7.6 (change-type) ✅ TOOLS row and PHP README extended in place`

## Phase 2 — design

### Approach

1. PHP: `MemberTypes` reads a method's `@return` when it has no native return type, resolved through the file's name
   context; `Visitor` stamps it on the Method as `extra.doc_type`.
2. Store: `declared_types(…, documented=True)` reads `doc_type`.
3. Resolver: a deferred chain step the native lookup misses tries `doc_type`; a chain that used one ends `HEURISTIC`.
4. `find_callers`: a Method's depth-1 answer counts `unresolved_receivers`, omitted when zero.
5. Docs: TOOLS `find_callers` row, PHP README, CHANGELOG `Unreleased`.

### Rejected alternatives

- **The adapter tiers the edge** — a cross-file factory's return type is unknown to the file making the call.
- **Call-site inference for untyped parameters (Scope 2)** — not without the anchor's count (W2).

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| the deferred chain carries a cross-file factory call | verified | `test_ac1_…` links at base |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | read `@return` | `adapters/php/src/MemberTypes.php`, `Parser.php`, `Visitor.php` | PHP emission: a new `extra` key on docblocked methods only | R1 | 3/3 |
| 2 | documented types | `code_atlas/store.py`, `code_atlas/resolver.py` | the deferred chain | R1, C1 | 2/2 |
| 3 | the count | `code_atlas/tools/find_callers.py` | a new omit-when-zero field | R3 | 1/1 |
| 4 | proving test | `tests/test_factory_receiver.py` (new) | — | AC1–AC3 | 1/1 |
| 5 | docs | `docs/TOOLS.md`, `adapters/php/README.md`, `CHANGELOG.md` | doc budgets | G1 | 3/3 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — PHP adapter + build + tool | real build, cross-file factory | authored | ✅ |
| AC2 | integration | the same with `@return` | authored | ✅ |
| AC3 | integration | the existing suites + the no-site test | authored | ✅ |
| AC4 | runtime — anchor | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** AC-field and Scope 2's count · risk: low · why: the anchor index is not on
this machine · escalated, answered by the maintainer 2026-10-17 · follow-up: on the anchor, `find_callers` for the
F1 method and the F3 sweep's subjects (before/after), and the count of untyped parameters whose resolved callers all
pass one class · `expiry: when the anchor index is available to a maintainer run` · `seen: 378, 384, 388, 389, 394, 390, 391, 393`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_factory_receiver.py` — red on the base (`2 failed, 2 passed`), green after.

### Rollback

`git revert`; a full rebuild drops `doc_type`. Merge after #76 (stacked).

## Phase 3 — execute

Commits `d1c1ca81` (code), `68647122` (docs), `2c892a81` + `0ca1f2fa` (challenger fixes).

**Red first.** The proving test with the base's `adapters/php/src` and `code_atlas` restored (8141543a): `2 failed, 2
passed in 3.50s` — AC2 and the count; AC1 and AC3 pass at base, as W3 says.

**Green after.** `4 passed in 1.75s` at the code commit; with the challenger's tests, see Phase 4.

**Axis 1.** Change-list rows 1–5. **Axis 2.** Approach bullets 1–5 implemented as approved. **P3 deviation:** AC1 is
asserted `RESOLVED`, not the ticket's `HEURISTIC` (W3).

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` — verdict **clean (challenger only — REVIEWER: OFF)**.

**Challenger** (ticket-blind: raw ticket plus `git diff` from the base without this file; 1 dispatch, 63,178 tokens):
4 met · 1 not met · 2 can't tell (Scope 2's count, E1) · AC1 noted as W3. One Major, four Minor:

| # | Finding | Resolution |
|---|---|---|
| M1 | `@return \App\Mailer` resolved against the namespace again (`\App\\App\Mailer`), so the twin class could link | a leading `\` is fully qualified as written (2c892a81) |
| m1 | `@return` inside prose read as a tag | the tag must open its docblock line (2c892a81) |
| m2 | `integer`, `scalar`, `namespace\X` produced dead `doc_type`s | added to the not-a-class list (2c892a81) |
| m3 | `null\|X` reads as nothing | kept: a missed link, never a wrong one (H3) |
| m4 | the count is index-wide by bare name, any language | kept to the subject's language (2c892a81); still not per class, which W4 states |

**Red first.** The three challenger tests against the pre-fix code: `3 failed, 3 passed in 2.60s`. **Green after:**
`tests/test_factory_receiver.py` `6 passed`; `ruff`, `mypy`, PHPStan clean. Ran at 2c892a81.

| Row | Ph3/4 proven by | k/N |
|---|---|---|
| G1 / R1 / AC2 | `test_ac2_…`, `test_challenger_a_qualified_return_…` | 2/2 |
| AC1 | `test_ac1_…` (W3) | 1/1 |
| C1 / AC3 | `test_ac3_…`; the existing suites unchanged | 2/2 |
| R3 | `test_scope3_…`, `test_challenger_another_languages_…` | 2/2 |
| R2 / AC4 | E1 | 0/2 (excluded) |

Reviewed at 2c892a81 — files: change-list rows 1–5. Working doc: `docs/tasks/393_factory-receiver.md`.

**PR review (#78).** A same-file docblocked factory now defers to the core (HEURISTIC); the downgrade applies only to a chain that links; `unresolved_receivers` counts unlinked calls and honours `exclude_tests`; `null|X` reads as `X|null` (supersedes m3); AC3 narrowed. Two tests added, `8 passed`.

## Phase 5 — finalise

**Durable lesson.** None new as a claim.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Stale-review guard: after 2c892a81 only docs (`0ca1f2fa`: a docstring and the TOOLS row), this file, `docs/BACKLOG.md` and
`docs/TOKEN_LEDGER.md` change. Not stale.

### Outward actions

Under the handover: push `feat/393-factory-receiver`; open the PR against `main` (stacked on #76).
Deferred: ratify W2–W4; E1 (with Scope 2's count); merge after #76.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 64,777 |
| 4 review | `challenger` (ticket-blind) | 1 | 63,178 |

`LEDGER TOTAL: 127,955 · top cost driver: exposure-checker`
