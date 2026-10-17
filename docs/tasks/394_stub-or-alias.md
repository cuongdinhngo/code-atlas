---
id: 394
slug: stub-or-alias
title: 'read_symbol returns an empty-bodied base method or a test-bootstrap stub as the answer, and does not say where the real one is'
phase: 2
milestone: Trust
status: todo
depends_on: [286, 252]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). Four PRs read a
correct body of the wrong code:

- F1 (1 PR): `read_symbol Base::render` returned an empty body. The implementation lives in two
  subclasses, which were found by name.
- F2 (2 PRs): a class is `class_alias`-ed to a stub in the test bootstrap. Neither `read_symbol`
  nor `search_symbol` said so, and the agent found it by reading a test's docblock, or by probing a
  swallowed exception.
- F3 (1 PR): global functions have test-bootstrap copies, so `search_symbol` was ambiguous until
  `path_prefix` was added.

286 names a mirror twin. The same cue is missing for an override and for an alias.

## Scope

1. A `read_symbol` hit whose body is empty or abstract carries `implemented_by`: the overriding
   methods, capped, with paths (read from the inheritance edges the index holds).
2. The PHP adapter already emits `ALIASES` for a literal `class_alias` (`Visitor.php`). Measure
   whether the anchor's bootstrap aliases reach the store, then `read_symbol` / `search_symbol` on
   either name names the other from that edge — no new relation, with its path. An alias declared in a
   file the index already classes as a test is labelled `test_double`.
3. On an ambiguous name where every other candidate lives in a test path, the production row comes
   first, and `ambiguity: "test_copies"` is set.

## Acceptance criteria

- **AC1:** `abstract`-free `Base::m(){}` with two overriding subclasses: `read_symbol Base::m`
  lists both in `implemented_by`.
- **AC2:** `class_alias('StubForm', 'Form')` in `tests/bootstrap.php`: `read_symbol Form` names
  the stub and labels it `test_double`.
- **AC3:** A symbol with no override, alias or test copy is byte-identical.

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 394 · **work_doc_mode:** embed · **Current phase:** 2 design · **Next action:** execute. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 388 - 389 - 394 - 390 - 391 - 393 - 395 - 392 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/394-stub-or-alias`, **stacked on `feat/389-worktree-overlay`** (both edit `read_symbol` /
  `search_symbol`, and every PR of this run edits the same bookkeeping rows). Contract `.mango/run-contract-394.txt`.

## Phase 0 — refine

`PREMISE: 7 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 16 unresolved surfaced | 4 want-decision asked | 12 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `read_symbol`, `search_symbol`, `ALIASES` (`contract.py:80`), `class_alias` in `adapters/php/src/Visitor.php:670`,
the 286 mirror twin (`read_symbol._attach_mirror_twin`), `path_prefix`, `subject_ambiguous` (078) resolve.
`implemented_by`, `test_double`, `ambiguity: "test_copies"` are to-be-created. Ambiguous: "the anchor's bootstrap aliases".

**Recall.** None matched: the change adds a module only `read_symbol` / `search_symbol` import, threads no value through
callers, and adds no shared vocabulary beyond naming an existing edge kind.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 44,371 tokens) raised eight; H6–H10 and W3–W4 came from it.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where overrides come from | how | linked `EXTENDS` / `IMPLEMENTS` edges onto the method's class, walked 4 levels, nearest level first, each subtype's own `Class::m` row; capped at 20, `implemented_by_truncated` past it ("from the inheritance edges the index holds", Scope 1) |
| H2 | "empty or abstract" without a body grammar | how | `abstract` in the stored `modifiers`, or no edge leaving the method but containment — what an empty body emits in every adapter (R1.1; exposure #2) |
| H3 | the alias pointer | how | `ALIASES` read both ways — `alias_of` (subject is the alias) / `aliased_as` — with the edge's file and line; no new relation (Scope 2) |
| H4 | `test_double` | how | the declaring file's rows' `is_test` (the index's own verdict, Scope 2), the path convention only for a file with no rows (exposure #6) |
| H5 | an alias whose real class is not indexed (exposure #5) | how | named by its `target_raw` as stored; no lookup is invented |
| H6 | test copies in `read_symbol` | how | one production row plus test copies answers the production row with `ambiguity: "test_copies"` and the copies in `ambiguous_definitions` — Scope 3's "the production row comes first"; any other mix keeps 078's refusal. **Tripwire:** narrows 078 for that one shape (exposure #3) |
| H7 | test copies in `search_symbol` | how | within a page, a qname's production row leads its copies; `ambiguity` on the answer |
| H8 | aliases on search rows | how | type rows at `standard`, omitted when none (061) — AC3 holds (exposure #4) |
| H9 | `ALIASES` constant | how | names an existing kind in `contract.py`; no vocabulary change (R3.1) |
| H10 | AC3 | how | every pointer omit-when-empty |
| W1 | Scope 2's anchor measurement + AC-field | want | **asked, settled by the maintainer (2026-10-17):** E1 |
| W2 | traits (exposure #1) | want | **ASSUMED (awaiting ratification):** an override reached through `USES_TRAIT` is not followed |
| W3 | cap order (exposure #7) | want | **ASSUMED (awaiting ratification):** nearest subtype level first, qname order within it |
| W4 | page-level ordering (exposure #8) | want | **ASSUMED (awaiting ratification):** production-first holds within a page; a copy may sit on an earlier page under relevance order |

## Phase 1 — analysis

`PREMISE: 7 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=1 R=3 G=1 AC=4`
`CLARIFICATION: 16 raised | 16 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

Stacked on 389's tip; `main`'s full suite `4565 passed, 4 skipped, 1 xfailed in 522.39s (0:08:42)`. Ran at daa6baa0.

### Gap analysis (enhancement)

| Goal | Current | Target |
|---|---|---|
| F1 empty base | a body, no pointer (`read_symbol.py` found path) | `implemented_by` |
| F2 alias stub | `ALIASES` stored, read only by the resolver (`resolver.py:115`) | `aliases` on read and search |
| F3 test copies | `subject_ambiguous` refusal (078) | the production row, flagged |

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "The same cue is missing for an override and for an alias" | pointers beside the body | ⏳ |
| C1 | Scope 2 | "no new relation" | read existing edges | ⏳ |
| R1 | Scope 1 | "carries `implemented_by` … capped, with paths" | H1, H2 | ⏳ |
| R2 | Scope 2 | "names the other from that edge … `test_double`" | H3–H5, H8 | ⏳ |
| R3 | Scope 3 | "the production row comes first, and `ambiguity: \"test_copies\"`" | H6, H7 | ⏳ |
| AC1 | AC | both overrides listed | | ⏳ |
| AC2 | AC | `read_symbol Form` names the stub, `test_double` | | ⏳ |
| AC3 | AC | no override/alias/copy: byte-identical | | ⏳ |
| AC4 | AC-field | anchor replay | W1 → E1 | ⏳ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — exact qname list | plus the "body that works" negative |
| AC2 | yes — exact `aliases` entry | both directions, and the search row |
| AC3 | yes — no pointer key on three answers | |
| AC4 | no — the anchor | E1 |

### Rule sections

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ emptiness read from modifiers and edges, never a body grammar · §R1.8 (change-type) ✅ one symbol_pointers module for both tools · §R3.1 (change-type) N/A because the ALIASES constant names an existing kind · §R5.2 (change-type) ✅ an override is a linked subtype row, never a guess · §R5.6 (change-type) ✅ test_double from the index's own role · §R6.5 (change-type) ✅ seen red before the pointers · §R7.6 (change-type) ✅ TOOLS read_symbol row extended beside 286, nothing retold · §R7.7 (change-type) ✅ formatter hunks outside the edit reverted`

## Phase 2 — design

### Approach

1. `code_atlas/tools/symbol_pointers.py` (new): `implemented_by`, `aliases`, `test_copies_first`.
2. `read_symbol`: one production row plus copies answers it; a found hit carries the pointers (`_attach_pointers`).
3. `search_symbol`: production-first per qname within a page, `ambiguity`; type rows carry `aliases` at `standard`.
4. `contract.ALIASES`. Docs: TOOLS.md, both docstrings, CHANGELOG.

### Rejected alternatives

- **An adapter-stamped `empty_body` flag** — a contract bump (R3.1) for a cue the graph already carries.
- **Attach `implemented_by` to every overridden method** — wider than Scope 1's "empty or abstract".

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| the PHP adapter stamps `abstract` in `modifiers` | verified | `parse_file` on `abstract public function a();` → `['public', 'abstract']` (scratch run) |
| an empty body emits no edge but containment | verified | `test_ac1_…` (`Base::render() {}` qualifies; `test_a_method_with_a_body_…` does not) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | the pointers module (new) | `code_atlas/tools/symbol_pointers.py` | core-module count pins (`test_core_is_language_agnostic.py`, `test_sql_confinement.py`, P5) | R1–R3 | 1/1 |
| 2 | wiring | `code_atlas/tools/read_symbol.py`, `code_atlas/tools/search_symbol.py` | read/search payloads (omit-when-empty); 078's refusal tests | R1–R3 | 2/2 |
| 3 | `ALIASES` constant | `code_atlas/contract.py` | none identified | C1 | 1/1 |
| 4 | proving test | `tests/test_symbol_pointers.py` (new) | — | AC1–AC3 | 1/1 |
| 5 | proof collateral | the two count-pin tests | P5 | R1 | 2/2 |
| 6 | docs | `docs/TOOLS.md`, `CHANGELOG.md` | doc budgets | G1 | 2/2 |
| 7 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — PHP build + tool | real build, two subclasses | authored | ✅ |
| AC2 | integration | real `class_alias` in `tests/bootstrap.php` | authored | ✅ |
| AC3 | integration | three answers carry no pointer | authored | ✅ |
| AC4 | runtime — anchor | manual-recorded (E1) | n/a | ❌ → E1 |

**E1 (coverage-gap exclusion, escalated).** Scope 2's measurement and AC-field · risk: low-medium · why: the anchor
index is not on this machine · escalated, answered by the maintainer 2026-10-17 · follow-up: on the anchor, count
`ALIASES` rows whose file is under the test bootstrap (`SELECT count(*) FROM edges WHERE kind='ALIASES'`), and
replay F1–F3 · `expiry: when the anchor index is available to a maintainer run` · `seen: 378, 384, 388, 389, 394`.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_symbol_pointers.py`.

### Rollback

`git revert`; nothing stored moves. Merge after #73 (stacked).
