---
id: 354
slug: empty-answers-that-name-the-wrong-cause
title: 'Two empty answers name the wrong cause: an unconfigured trace says no_matches, a misqualified name says index_stale'
phase: 2
milestone: Honesty
status: todo
depends_on: [073, 199, 246]
---

## Why this exists

Both answers are empty, and both send the agent the wrong way. Field retro, 2026-09-30.

1. **`trace_capability` with nothing configured.** With no `capabilities.toml`, no structural
   layout and no `CA_ENTRY_POINTS`, the flow set is empty and every subject answers `no_matches`
   (`code_atlas/tools/trace_capability.py:256`). 3 PRs read that as "this route joins no flow".
   `find_view_data` and `find_orphans` refuse the same situation by name instead (069); the reason
   text already exists (`code_atlas/onboarding/capabilities.py` `EMPTY_REASON`).
2. **A qualification miss on a behind index.** `read_symbol dbo.X`, where the declaration is `[X]`
   (qname `X`), answered `index_stale`. On a miss, `ensure_miss` runs before any name-variant lookup
   (`code_atlas/tools/read_symbol.py:182` vs `:212`). With several dirty files and an unnameable
   subject it returns `stale` (073), so `_resolve_miss` never gets to suggest `X`.

## Scope

1. `trace_capability` returns a not-configured reason, with `EMPTY_REASON`'s route, when the whole
   flow set is empty. `no_matches` stays for a subject absent from a non-empty set.
2. A miss tries the name-variant resolution before it declares `index_stale`. If a variant exists
   in a clean file, that is the answer (or its `try_instead`). Check `find_callers` and
   `find_references` for the same order and fix them the same way.

## Acceptance criteria

- **AC1:** On an index with no capability sources, `trace_capability(path=…)` returns the
  not-configured reason and a route, never `no_matches`.
- **AC2:** With one flow present, a subject outside it still answers `no_matches`.
- **AC3:** On a behind index with >1 dirty file, `read_symbol dbo.X` for a clean `[X]` answers the
  `X` candidate, not `index_stale`.
- **AC4:** A true miss on that index still answers `index_stale` (073 unchanged).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 354 · **work_doc_mode:** embed · **Current phase:** 2 design · **Next action:** commit, gate, challenger.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`, batch 356 → 354 → 355;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `fix/354-empty-answers-that-name-the-wrong-cause` off `main` (`5b4f1667`). Contract `.mango/run-contract-354.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 5 unresolved surfaced | 1 want-decision asked | 4 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Premise.** All six resolve on `5b4f1667`:
- `trace_capability.py:256` — the `REASON_NO_MATCHES` branch;
- `onboarding/capabilities.py` `EMPTY_REASON`;
- `find_view_data` / `find_orphans`, which refuse by name (069, `nav_result.py:60`);
- `read_symbol.py:182` (`ensure_miss`);
- `read_symbol.py:212` (`_resolve_miss`);
- `freshness.py` `ensure_miss`, with its 073 stale branch.

**Recall (by handle).** `343-C2` `formatter-rewrites-untouched-lines` and `344-C3`
`verify-the-shipped-artifact-not-the-working-tree`.

**Scan.** On a clean SQL index, `read_symbol dbo.Orders` for `CREATE TABLE [Orders]` (qname
`Orders`) already answered a bare `no_such_symbol`. `classify_missing_subject` matches only stored
names that *end with* the query (`nav_result.py:603`), never the reverse. So AC3 needs a variant as
well as the reorder.

The exposure-checker (ticket-blind `challenger`, 1 dispatch, 42,764 tokens) raised three items, and
two came from my own scan:

| # | Decision | Class | Resolution |
|---|---|---|---|
| A1 | what counts as "the whole flow set is empty" (unconfigured vs configured-but-zero) | want (bar) | **ASSUMED:** `capability_not_configured` when no flow was seeded **and** no entry point is declared. Declared entry points that trace nothing keep `no_matches` — that index is configured |
| H1 | which reason and route | how | `capability_not_configured` (the 069 vocabulary, `nav_result.py:61`). The route is `try_instead: get_index_status`, which nominates entry-point globs (TOOLS.md, 268), with a hint naming `CA_ENTRY_POINTS` |
| H2 | `EMPTY_REASON` names `capabilities.toml` | how | a TOML does not seed a flow — `flows.py:213` `seed_files` takes declared entry points and entry-named paths only — so the route names the entry-point knob alone, from one shared `ENTRY_POINTS_KNOB` (R6.7) |
| H3 | a variant whose own file is dirty | how | the variant's file becomes the named subject, so 246's named-subject branch repairs it within the cap or answers `index_stale` (`freshness.py` `ensure_miss`) |
| H4 | re-point onto `Orders`, or name it | how | name it in `candidates`, never re-point: the extra qualifier may name a different symbol (`Foo::bar` vs a global `bar`) — a confident wrong answer (R5), and the ticket's own "(or its `try_instead`)" |

A1 rests on the maintainer's up-front hand-back ("make the necessary decisions … without waiting
for further confirmation"); it reverses no prior decision and is surfaced in the PR.

## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (title, Why this exists, Scope, Acceptance criteria) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=4`
`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

H1–H4 cite the code or the rules; A1 cites the hand-back, so `j = 0`.

### BASELINE

`main` at `5b4f1667` is the tree CI run 36730042133 passed, on py3.12 and py3.13, with 4094 passed
and 4 skipped each (`git diff --quiet a2ee376e 5b4f1667` → exit 0). Per SG-2 it is not pasted as a
`$` evidence block.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "both send the agent the wrong way" | each empty answer names its real cause | |
| C1 | R1.1 | — | the variant is a component-boundary rule, language-free | |
| C2 | 061 | — | a quiet answer is byte-identical; new fields only on the new cases | |
| R1 | Scope 1 | not-configured reason + route when the flow set is empty | A1 | |
| R2 | Scope 2 | the variant before `index_stale` | `miss_subject_path` names the variant's file | |
| R3 | Scope 2 | the same for `find_callers` / `find_references` | both reach it through `ensure_qname` and `shape_exact_miss` | |
| AC1 | AC | not configured + a route, never `no_matches` | | |
| AC2 | AC | one flow present → `no_matches` outside it | | |
| AC3 | AC | `dbo.X` on a behind index → the `X` candidate | on all three tools | |
| AC4 | AC | a true miss → `index_stale` | | |

### AC validation

Every AC is falsifiable. The proof is a reason value or a field's presence in a real tool payload,
over a real index built with the fake adapter (AC1/AC2) or the SQL adapter (AC3/AC4).

### Gap analysis (bug · `logic`)

- **Now.**
  - `trace_capability` answers `no_matches` whenever `matched` is empty, including when
    `built.flows` is empty (`trace_capability.py:256`).
  - A zero-hit subject with no path in its qname is unnameable, so `ensure_miss` answers `stale` on
    more than one dirty file (`freshness.py`). That happens before `_resolve_miss` runs
    (`read_symbol.py:182`; `find_callers.py:262`; `find_references.py:354`).
  - The classifier has no reverse match.
- **Target.** Each empty answer names its cause.

### Blast radius

- `classify_missing_subject` / `shape_exact_miss` consumers: `read_symbol`, `find_callers`,
  `find_references`, `find_implementations`, `find_view_data`, `impact`, `explain_path`.
- The new status is a miss everywhere (`!= "resolved_unique"`), so each gains `candidates` only on a
  reverse match.
- `ensure_qname` (`find_callers`, `find_references`, …) and `read_symbol`'s miss call.
- `EMPTY_REASON`'s text is byte-identical (checked).
- Docs: TOOLS.md's `trace_capability` row; `design/payload.md`'s `resolved_qname` entry.

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the reverse variant is a component-boundary suffix rule that names no language or schema, §R5.3 (change-type) ✅ a reverse match is offered in candidates and never re-pointed onto, §R6.5 (change-type) ✅ AC1 and AC3 are seen red on the pre-change tree, §R6.7 (change-type) ✅ one ENTRY_POINTS_KNOB feeds EMPTY_REASON and the trace route and one miss_subject_path serves every miss, §R7.6 (change-type) ✅ the TOOLS row and the payload entry are extended in place`

## Phase 2 — design

### Approach

1. **`trace_capability`.** When `built.flows` is empty and `config.entry_points` is unset, answer
   `capability_not_configured` with `try_instead: get_index_status` and `ENTRY_POINTS_ROUTE`.
   `ENTRY_POINTS_KNOB` moves into `onboarding/capabilities.py`, and `EMPTY_REASON` is composed from
   it, byte-identical.
2. **The classifier.** A `stored_shorter` status: the longest stored qname the subject ends with at a
   component boundary, tried after the forward match and the untracked check. `shape_exact_miss`
   gives it `no_such_symbol` + `candidates` + a hint. `read_symbol`'s final miss goes through
   `shape_exact_miss`.
3. **The freshness guard.** `miss_subject_path` returns the subject's own path, else the file of its
   unique forward variant or its reverse candidate. `read_symbol` and `ensure_qname` use it, so the
   miss is decided on that file (246).

### Rejected alternatives

- **Re-point `dbo.Orders` onto `Orders`.** A wrong answer when the qualifier names another symbol (H4).
- **Skip the guard on a miss.** 073's `index_stale` for a true miss would go (AC4).
- **Quote `EMPTY_REASON` in the trace answer.** It names a TOML that seeds no flow (H2).

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | the SQL adapter stores `[Orders]` as `Orders` and `dbo.Insert_Order` as written | verified — scan |
| S2 | an index with no entry point and no entry-named path seeds no flow | verified — AC1 red on `5b4f1667` |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | not-configured answer, route | `code_atlas/tools/trace_capability.py`, `code_atlas/onboarding/capabilities.py` | `EMPTY_REASON` consumers (text unchanged) | R1, AC1, AC2 | 2/2 |
| 2 | `stored_shorter` + candidates | `code_atlas/tools/nav_result.py`, `code_atlas/tools/read_symbol.py` | the seven classifier consumers | R2, R3, AC3 | 2/2 |
| 3 | `miss_subject_path` | `code_atlas/tools/freshness.py` | `ensure_qname` callers; `read_symbol` | R2, R3, AC3, AC4 | 1/1 |
| 4 | tests | `tests/test_empty_answers_name_the_cause.py` (new) | — | AC1–AC4 | 1/1 |
| 5 | docs | `docs/TOOLS.md`, `docs/design/payload.md` | doc budgets | G1 | 2/2 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced in Phase 3.
- **`verify-the-shipped-artifact-not-the-working-tree`** — does not apply because this change ships no
  generated or installed artifact.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | `trace_capability` over a real fake-adapter index | n/a | ✅ |
| AC2 | integration | the same, with `CA_ENTRY_POINTS` tracing one real flow | n/a | ✅ |
| AC3 | integration | three tools over a real SQL-adapter index in a git repo with two dirty files | n/a | ✅ |
| AC4 | integration | the same index, a qname with no variant | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_empty_answers_name_the_cause.py`. On `5b4f1667`, AC1 and
both AC3 tests fail and AC2/AC4 pass (guards); all five pass after the change.

### Rollback

`git revert`. No index or contract change.
