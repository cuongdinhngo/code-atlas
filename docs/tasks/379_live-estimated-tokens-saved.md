---
id: 379
slug: live-estimated-tokens-saved
title: 'Tokens-to-answer is measured only in benchmarks; nothing counts it on the repo a user actually runs'
phase: 2
milestone: Adoption
status: done
depends_on: [260]
---

## Why this exists

The product claim — tokens-to-answer against a grep + `Read` baseline — is measured only by
`scripts/tokens_to_answer.py` over fixtures and pinned samples. On a user's own repo nothing says
which tools save tokens and which only cost them (a miss pays its response for nothing).

context-mode shows live savings, but its baseline credits every byte it indexed as "saved" and
prices it at the output-token rate (its `src/server.ts:1036-1068`; idea only, ELv2) — an inflated
figure this project must not copy. 260's `fit` counters already wrap every served tool once
(`tools/fit.py:40`), store counts only in `meta`, survive shadow rebuilds and stay out of nav
payloads (`docs/design/fit.md`). A cost counter fits beside them.

**Measure-first:** the honest baseline is an estimate. This ticket ships only if design shows it
can be stated without being mistaken for the benchmark tiers.

## Scope

1. Per served call: response tokens (`estimate_tokens` over the serialised response) and a
   baseline = tokens of the distinct files the response cites, first 20 in payload order (the
   benchmark's cap, `tokens_to_answer.py:717-736`). Tools that cite no file are not eligible; a
   miss counts its response against a zero baseline.
2. Counts only, per tool, in `meta` beside the fit counts; no qname, path or session in a key.
3. Read through `get_index_status(verbose)` (which stays self-excluded), reset with the fit reset.
4. Every surface labels it "est. grep+Read baseline" and never as the fixture or sample tier.
5. **Not in scope:** dollars, model prices, a statusline. A statusline is a new host surface and
   a separate maintainer decision (`hooks/state.py:15`, R1.2/099).

## Assumptions to prove at design

- File size source: a `files.size_bytes` column (content-derived, deterministic, but a schema
  bump and a rebuild) vs `stat` at count time (cheap, but measures the working tree). Decide.
- The per-call serialisation cost on large payloads is acceptable; **UNVERIFIED** that FastMCP's
  bytes equal `json.dumps(sort_keys=True)`.

## Acceptance criteria

- **AC1:** on a fixture, one `read_symbol` records baseline = `ceil(file bytes / 4)` and response
  = `estimate_tokens` of the result; a second identical call exactly doubles both. Bytes, not the
  benchmark's decoded chars, is a stated approximation: equal for ASCII, higher otherwise.
- **AC2:** every nav payload is byte-identical with counting on and off; two
  `get_index_status(standard)` calls are byte-identical while the counters move.
- **AC3:** no `meta` key contains a fixture qname or path; the rows survive a shadow rebuild.
- **AC4:** the README and TOOLS.md state what the number is and is not, in one place each.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 379 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W3 and merges after #58. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 375 - 376 - 377 - 378 - 379`, no flags —
  `REVIEWER: ON` · `CHALLENGER: ON`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/379-live-estimated-tokens-saved` off `feat/378-search-did-you-mean-by-edit-distance` (PR #58 — stacked).
  Contract `.mango/run-contract-379.txt`. RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 3 retired skipped — advisory (blocks nothing)`
`REFINE: 10 unresolved surfaced | 3 want-decision asked | 7 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `tools/fit.py:40` (`wrap`), `docs/design/fit.md`, `scripts/tokens_to_answer.py`'s grep path,
`estimate_tokens`, `get_index_status(verbose)` and `reset_fit_counts` resolve.

**Recall (handle).** 362-C1 `widen-every-query-that-shares-the-page` — the new rows ride every read the fit rows
ride: the bump, the shadow carry, the list, the reset (H4).

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 39,123 tokens) added W2 and H7–H9; kept W1 a want.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the size source | how | `stat` at count time — a `files` column is a schema bump, a full rebuild and a release (CHANGELOG's two costs), and the modelled grep+Read reads today's tree too |
| H2 | which files an answer cites | how | strings under `file` / `file_path` / `path`, depth-first in payload order, kept only when a repo file (`resolves_inside`, 375), distinct, first 20 (`max_read_files`) |
| H3 | the counted calls | how | every call `fit` counts — the same wrapper (`fit.py:40`); `get_index_status` stays self-excluded |
| H4 | storage | how | `cost:<tool>\|<field>` beside `fit:`; carried by the shadow, cleared by `reset_fit_counts` |
| H5 | the read | how | `get_index_status(verbose)`: `est_tokens_vs_grep_read` + `est_tokens_note` |
| H6 | response tokens | how | `estimate_tokens(json.dumps(result, sort_keys=True, default=str))` — FastMCP's exact bytes stay UNVERIFIED, hence "est." |
| H7 | eligibility | how | per call: `cited_calls` counts answers that cited a file — a tool whose `cited_calls` is 0 cited none; no hand list (R6.7) |
| H8 | a per-file cap | how | none: the benchmark reads each matched file whole (`tokens_to_answer.py` `grep_scan`) |
| H9 | an uncountable answer | how | skipped, never spoiled — the fit counter's rule |
| W1 | ship at all | want | **ASSUMED (awaiting ratification):** ship — the field name, the note and both docs say "est." and "not a benchmark tier" |
| W2 | a derived "saved" and a total | want | **ASSUMED (awaiting ratification):** neither — raw per-tool numbers only, so no single figure can be quoted as the product claim |
| W3 | the field's name | want | **ASSUMED (awaiting ratification):** `est_tokens_vs_grep_read`, not "saved" |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=2 R=4 G=1 AC=4`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

378's final gate, the base of this branch: `21 passed · 0 failed · 0 skipped` — `GATE GREEN`. Ran at 255b9437.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "nothing says which tools save tokens and which only cost them" | per-tool est. response vs est. baseline | ✅ |
| C1 | Why | "an inflated figure this project must not copy" | no indexed-bytes credit; cited files only | ✅ |
| C2 | Scope 5 | dollars, prices, a statusline out | none added | ✅ |
| R1 | Scope 1 | response + cited-file baseline, first 20 | H2, H6 | ✅ |
| R2 | Scope 2 | counts only in `meta`, no subject in a key | H4 | ✅ |
| R3 | Scope 3 | read via verbose, reset with fit | H4, H5 | ✅ |
| R4 | Scope 4 | labelled est., never a tier | the note, README, TOOLS.md | ✅ |
| AC1 | AC | baseline `ceil(bytes/4)`, response `estimate_tokens`; doubles | | ✅ |
| AC2 | AC | payloads identical; `standard` identical | | ✅ |
| AC3 | AC | no subject in a key; survives a shadow | | ✅ |
| AC4 | AC | README and TOOLS.md, one place each | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — exact row equality, then every count ×2 | |
| AC2 | yes — wrapped == bare; `standard` JSON equal across a counted call | |
| AC3 | yes — keys `cost:read_symbol\|…` only; `list_cost_counts` after a real rebuild with a mid-build bump | |
| AC4 | yes — one README paragraph, one TOOLS.md clause | |

### Rule sections

`RULE SECTIONS: 7 applicable — 6 by change-type | 1 by recalled handle — §R1.4 (change-type) ✅ the meta writes and reads sit in store.py · §R4.2 (change-type) ✅ nav payloads and the standard status unchanged; counts only in verbose · §R5.6 (change-type) ✅ the note separates an estimate from a measured tier · §R6.5 (change-type) ✅ the field absent on the prior code · §R6.7 (change-type) ✅ eligibility derived per call, no tool list · §R7.5 (change-type) ✅ comments ≤ 3 lines · §R1.8 (recalled handle widen-every-query-that-shares-the-page) ✅ one _write_counts behind both counters; carry, list and reset each cover cost:`

## Phase 2 — design

### Approach

1. `store.py`: `COST_KEY_PREFIX`, `COST_FIELDS`, `bump_cost_counts`, a shared `_write_counts`, `_COUNT_ADD_SQL`;
   the shadow carry, `list_cost_counts` and `clear_fit_counts` cover `cost:`.
2. `fit.py`: `cited_files`, `record_cost`, called in the same wrapper as `record`; the field and note constants.
3. `get_index_status` verbose: the rows and the note; the docstring names them.
4. README, TOOLS.md, CHANGELOG.

### Rejected alternatives

- **A `files.size_bytes` column** — a schema bump and a full rebuild for a counter (H1).
- **A derived "saved" and a total** — the figure most likely to be quoted as the product claim (W2).
- **A list of eligible tools** — drifts when a tool starts citing files; `cited_calls` derives it (R6.7).
- **Credit every indexed byte** — context-mode's inflation, which the ticket rules out.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| the per-call cost | verified | `record_cost` median 0.61 ms on a 20-file `search_symbol` page, 0.27 ms on an 18,375-char `architecture_overview` (fresh index of this repo) |
| FastMCP's bytes = `json.dumps(sort_keys)` | novel-untested, not load-bearing | the figure is labelled an estimate (H6); a tokenizer swap lives in `estimate_tokens` |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | cost rows | `code_atlas/store.py` | the fit write path (shared helper), the shadow carry, the reset | R2, R3, AC3 | 1/1 |
| 2 | recording | `code_atlas/tools/fit.py` | every served call (the wrapper) | R1, AC1 | 1/1 |
| 3 | the read | `code_atlas/tools/get_index_status.py` | verbose payload only | R3, R4 | 1/1 |
| 4 | proving tests | `tests/test_est_tokens.py`, `tests/test_rebuild_behind_a_shadow_index.py` | — | AC1–AC3 | 2/2 |
| 5 | docs | `README.md`, `docs/TOOLS.md`, `CHANGELOG.md` | the doc budgets | R4, AC4 | 3/3 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

### Recalled handles

| # | Handle | Answer |
|---|---|---|
| 1 | `widen-every-query-that-shares-the-page` | traced — `grep -n 'FIT_KEY_PREFIX' code_atlas/store.py` → the bump, `_carry_fit_counts`, `list_fit_counts`, `clear_fit_counts`; each now covers `cost:` (the list by its own method) |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — wrapper + store | `fit.wrap(read_symbol)` on a seeded index | n/a | ✅ |
| AC2 | integration | bare vs wrapped; `get_index_status` twice | n/a | ✅ |
| AC3 | integration — a real rebuild | `rebuild()` with a bump mid-build | n/a | ✅ |
| AC4 | doc | the README paragraph, the TOOLS.md clause | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_est_tokens.py tests/test_fit_counts.py tests/test_rebuild_behind_a_shadow_index.py`.

### Rollback

`git revert`; leftover `cost:` rows are inert meta.

## Phase 3 — execute

Commits `d4eac023` (code, tests), `9a9606ee` (docs). **Red first** (R6.5): a new field, so the prior code
lacks it — the same script before and after: `est field present: False | fit rows: 1` →
`est field present: True | fit rows: 1`; the test module itself fails to import on the prior store.

```
$ .venv/bin/python -m pytest -q tests/test_est_tokens.py tests/test_fit_counts.py tests/test_rebuild_behind_a_shadow_index.py
25 passed in 26.49s
Ran at 286f859c
```

```
$ scripts/gate.sh
21 passed · 0 failed · 0 skipped
GATE GREEN — all 21 checks passed
Ran at 286f859c
```

**Verification sweep.** File axis: the diff is the change list; `ruff check`, `mypy code_atlas` clean.
Behaviour axis: Approach 1–4 implemented as approved.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. Reviewed at 50577bfa — files: `code_atlas/store.py`, `code_atlas/tools/fit.py`,
`code_atlas/tools/get_index_status.py`, `tests/test_est_tokens.py`, `tests/test_rebuild_behind_a_shadow_index.py`,
`README.md`, `docs/TOOLS.md`, `docs/design/fit.md`, `CHANGELOG.md`; working doc: this file.

- **`reviewer` round 1 — conditional LGTM** (52,306 tokens): keys, no schema change, self-exclusion, the
  containment-safe walk, R6.7, R7.5, R1.1/R4 checked. Findings: (1) `docs/design/fit.md` — the doc readers are
  told to read first — did not say the reset now clears `cost:` too; (2) the definition sat in three places (README,
  TOOLS.md, the tool docstring). (3, minor) a cap/escape test — already present
  (`test_only_repo_files_are_cited_first_twenty_in_payload_order`).
- **Round 2 — verify-only, main loop, no re-dispatch:** `50577bfa` adds one pointer line to `fit.md` and trims the
  docstring to "read `est_tokens_note` first"; both fixes stay inside the named findings. Re-ran the affected proof:
  `tests/test_est_tokens.py tests/test_doc_size_budget.py tests/test_fit_counts.py` → `21 passed`.
- **`challenger` round 1** (ticket-blind, 54,700 tokens): 11 met · 0 not met · 0 can't tell. Residuals: a
  working-tree baseline is not content-deterministic (H1, by design); a file cited in another shape (`file:line`
  text) is not counted.

Verdict: clean. Matrix `Ph3/4 proven by`: R1–R3, AC1–AC3 → `tests/test_est_tokens.py` + the rebuild test; R4,
AC4 → README, TOOLS.md, the note; C1–C2 → the diff.

## Phase 5 — finalise

**Durable lesson.** None new.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/379-live-estimated-tokens-saved`; open the PR against 378's branch (stacked on #58).
Deferred to the maintainer: ratify W1–W3; merge.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 39,123 |
| 4 review | `reviewer` | 1 | 52,306 |
| 4 review | `challenger` (ticket-blind) | 1 | 54,700 |

`LEDGER TOTAL: 146,129 · top cost driver: 4 review/challenger`
