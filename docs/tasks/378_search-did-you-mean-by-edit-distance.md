---
id: 378
slug: search-did-you-mean-by-edit-distance
title: 'A one-letter typo in a symbol name answers empty, and the token route cannot suggest the right name'
phase: 2
milestone: Retrieval
status: done
depends_on: [180, 253]
---

## Why this exists

`fts_term` (`store.py:458`) searches the whole query as one literal trigram phrase, so a
misspelled name has no substring hit. The miss path then tries `token_candidates` (253), which
ranks names sharing a `name_tokens` token (`contract.py:371-389`, `TOKEN_CANDIDATE_K=5`). A typo
inside the distinctive token defeats it. Observed on this repo's index, 2026-10-09, one sweep:

- `full_biuld` → `results: []`; the five candidates matched only `full`, and
  `indexer.full_build` is not among them.
- `resolves_insdie` → `containment.resolves_inside` ranked 4th of 5.
- `estimate_tokesn` → `tokens.estimate_tokens` ranked 1st (rescued by the `estimate` token).

Each miss costs a guessed retry or a fall-back to grep + `Read` — the exact cost the product
exists to remove (PLAN §1 Goals). context-mode corrects typos by Levenshtein with thresholds
1/2/3 by word length, but ties go to scan order (its `src/store.ts:144-148, 1195-1240`; idea only,
ELv2). 253's rejected alternatives never considered edit distance.

## Scope

1. A store method (`store.py` stays the sole SQLite owner) returns names within an edit distance
   of the query: prefilter by trigram OR over the query's 3-grams, then Levenshtein on casefolded
   `name`, ordered by `(distance, casefolded name, qname)` — a total order (R4.2).
2. `search_symbol` consults it when a subject's results are empty, alongside or after
   `token_candidates`. Suggestions live beside `results`, never in it (R5.6); each carries its
   distance.
3. An exact or prefix hit never takes this path; a `queries` sweep applies it per subject.
4. The tool description names the new field; the 24-tool surface does not grow.

## Assumptions to prove at design

- Whether the field merges into `candidates` (with `edit_distance`) or is its own reason — and
  whether either moves `CONTRACT_VERSION` (101's CL-1 reasoning says payload vocabulary does not;
  confirm against the sole-source gate).
- The prefilter keeps the cost bounded on the anchor index (~22.9k files); measure, do not assume.

## Acceptance criteria

- **AC1:** on a fixture, `getUserByld` suggests `getUserById` at distance 1.
- **AC2:** two equidistant names come back in name order; 50 repeated calls are byte-identical.
- **AC3:** a query with an exact hit returns exactly today's answer (byte-identical).
- **AC4:** on this repo's index, `full_biuld` suggests `full_build`.
- **AC5:** the miss-path cost on the anchor index is recorded in the task, against today's.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 378 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W3, measures AC5 on the anchor, and merges after #57. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 375 - 376 - 377 - 378 - 379`, no flags —
  `REVIEWER: ON` · `CHALLENGER: ON`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/378-search-did-you-mean-by-edit-distance` off `fix/377-nudge-only-when-the-index-can-answer` (PR #57 — stacked).
  Contract `.mango/run-contract-378.txt`. RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 3 retired skipped — advisory (blocks nothing)`
`REFINE: 15 unresolved surfaced | 3 want-decision asked | 12 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `fts_term` (`store.py:458`), `token_candidates` / `_token_candidates`, `name_tokens`
(`contract.py:376`), `TOKEN_CANDIDATE_K`, `queries` (101) and the 24-tool surface resolve.

**Recall (handle).** 362-C1 `widen-every-query-that-shares-the-page` — the change threads a new list through the
single and the sweep payload; both renderers are covered (H11).

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 40,564 tokens) added W2–W3 and H9–H12; flagged W1's
zero margin for AC4 (`full_biuld` → `full_build` is 2 edits at a 10-character tail, the bound being 2).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the field | how | `did_you_mean` beside `candidates`, reason stays `token_candidates`; no new `NavReason`; `CONTRACT_VERSION` unchanged — a payload key is tool vocabulary (`nav_result.py`'s "tool vocab — not CONTRACT_VERSION") |
| H2 | the store pass | how | FTS `name : ("abc" OR …)`, a length window and the UDF bound in SQL; sorted `(distance, casefolded name, qname, id)` and cut after (R5.8) |
| H3 | what is compared | how | the query's last segment after `.` `::` `->` `\` `/` `#` (`name_tail`) with `name` |
| H4 | K and filters | how | `TOKEN_CANDIDATE_K`; File rows out, as 253; `kind` / `namespace` / `path_prefix` honoured |
| H5 | when it runs | how | the zero-overlap token branch only (`offset == 0`) — Scope 3 |
| H6 | AC5 on the anchor | how | not on this machine: measured on the two largest local sample indexes; coverage-gap exclusion |
| H7 | the metric | how | plain Levenshtein, the ticket's word; a transposition costs 2 |
| H8 | the hint | how | "candidates exist" when either list is non-empty |
| H9 | overlap with `candidates` | how | independent lists — AC1's `getUserByld` shares the token `user` with its answer, so a dedupe would fail AC1 |
| H10 | short / spaced queries | how | a tail under 3 characters or holding whitespace has no trigram: `[]` |
| H11 | an empty list | how | the field is omitted, so a no-suggestion miss stays 253's payload |
| H12 | per-qname rows | how | the ticket's order ends in `qname` — one row per qname |
| W1 | the bound by length | want | **ASSUMED (awaiting ratification):** ≤ 5 chars → 1, ≤ 10 → 2, else 3 — context-mode's 1/2/3 |
| W2 | AC5's bar | want | **ASSUMED (awaiting ratification):** record the cost; no hard ceiling — the PR review's 200k-node adversarial index measured 42–302 ms |
| W3 | same-name crowding | want | **ASSUMED (awaiting ratification):** keep per-qname rows; five `EmailAddress` copies can fill the list (seen on adventureworks) |

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=2 R=4 G=1 AC=5`
`CLARIFICATION: 15 raised | 15 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/5 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

377's final gate, the base of this branch: `21 passed · 0 failed · 0 skipped` — `GATE GREEN`. Ran at 43a187f9.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "Each miss costs a guessed retry" | a typo answers the name it meant | ✅ |
| C1 | Scope 1 | "`store.py` stays the sole SQLite owner" | the SQL and the UDF live in `store.py` | ✅ |
| C2 | Scope 4 | "the 24-tool surface does not grow" | a field, no tool | ✅ |
| R1 | Scope 1 | pigeonhole piece prefilter (PR review; trigram OR missed short typos), Levenshtein, total order | H2 | ✅ |
| R2 | Scope 2 | beside `results`, each with its distance | H1 | ✅ |
| R3 | Scope 3 | never on a hit; per subject in a sweep | H5 | ✅ |
| R4 | Scope 4 | the description names the field | tool docstring, TOOLS.md | ✅ |
| AC1 | AC | `getUserByld` → `getUserById`, 1 | | ✅ |
| AC2 | AC | name order; 50 calls identical | | ✅ |
| AC3 | AC | an exact hit byte-identical | the pass monkeypatched to raise | ✅ |
| AC4 | AC | this repo: `full_biuld` → `full_build` | a fresh index of this branch | ✅ |
| AC5 | AC | the anchor's cost recorded | exclusion; samples measured | ⚠ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `did_you_mean[0] == {qname, name, kind, edit_distance: 1}` | |
| AC2 | yes — order `parseRows`, `ParseRowz`; `json.dumps` identical ×50 | `parseCols` is 3 edits, past the bound |
| AC3 | yes — equal payloads with the pass refusing | |
| AC4 | yes — the tool on a fresh index of this repo | recorded below, not a unit test: it needs this repo's index |
| AC5 | manual-check exclusion — the anchor is not on this machine | see Coverage-gap exclusions |

### Rule sections

`RULE SECTIONS: 7 applicable — 6 by change-type | 1 by recalled handle — §R1.4 (change-type) ✅ the SQL and the UDF sit in store.py · §R4.2 (change-type) ✅ a total order ending in id; deterministic UDF · §R5.6 (change-type) ✅ suggestions never in results or total_count · §R5.8 (change-type) ✅ the cut follows the distance order · §R6.5 (change-type) ✅ AC1–AC3 and the sweep red on the prior code · §R7.5 (change-type) ✅ comments ≤ 3 lines · §R1.8 (recalled handle widen-every-query-that-shares-the-page) ✅ both renderers, single and sweep, read hits.did_you_mean`

## Phase 2 — design

### Approach

1. `store.py`: `name_tail`, `edit_distance_limit`, a bounded `edit_distance`, the UDF `ca_edit_distance`, and
   `GraphStore.edit_distance_names(...)`.
2. `search_symbol`: `_Hits.did_you_mean`; `_did_you_mean` on the token branch; both renderers add the field when non-empty.
3. The tool docstring, TOOLS.md and CHANGELOG name `did_you_mean`.

### Rejected alternatives

- **Merge into `candidates` with `edit_distance`** — a token candidate and a spelling match are different
  evidence; one list would sign a word match with a distance it does not have (R5.6).
- **A new reason** — the answer is still a zero-overlap miss; the reason names the miss, the field the evidence.
- **Damerau distance** — the ticket names Levenshtein; a transposition stays 2.
- **Scan every name with the UDF** — no prefilter; the ticket's Scope 1 asks for the trigram OR.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| the field moves no contract | verified | `CONTRACT_VERSION` is the adapter contract (R3.5); `nav_result` vocabulary is tool vocab |
| the cost is bounded | verified on the samples | the AC5 table below; the anchor is an exclusion |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | the store pass | `code_atlas/store.py` | every `GraphStore` connection registers one more UDF | R1, C1 | 1/1 |
| 2 | the field | `code_atlas/tools/search_symbol.py` | single and sweep payloads on the token branch | R2, R3 | 1/1 |
| 3 | proving tests | `tests/test_search_did_you_mean.py` | — | AC1–AC3, R3 | 1/1 |
| 4 | docs | `docs/TOOLS.md`, `CHANGELOG.md` | — | R4 | 2/2 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

### Recalled handles

| # | Handle | Answer |
|---|---|---|
| 1 | `widen-every-query-that-shares-the-page` | traced — `grep -n 'answer\["candidates"\]\|payload\["candidates"\]' code_atlas/tools/search_symbol.py` → `542`, `592`: both renderers, each now adds `did_you_mean` |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — SQL + tool | `search_symbol` over a seeded store | n/a | ✅ |
| AC2 | integration | the same, 50 calls | n/a | ✅ |
| AC3 | integration | the same, the pass refusing | n/a | ✅ |
| AC4 | integration — a real index | the tool on a fresh full build of this branch | real-corpus | ✅ |
| AC5 | runtime cost at anchor scale | manual-recorded on two samples | real-corpus | ❌ → exclusion |

**Coverage-gap exclusions**

| Item | Risk tier | Why deferred | Follow-up | Expiry | Seen |
|---|---|---|---|---|---|
| AC5's anchor figure | medium until measured — a synthetic 200k-node index of 30 common words costs 42–302 ms per miss (PR review) | the anchor (~22.9k files, Windows) is not on this machine | measure `full_biuld`-style misses on the anchor | expiry: when the anchor index is available to a maintainer run | first |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_search_did_you_mean.py tests/test_zero_overlap_token_candidates.py`.

### Rollback

`git revert`; no stored state.

## Phase 3 — execute

Commits `2b52e9ad` (code, tests), `9ad429fb` (docs). **Red first** (R6.5): the five tool tests, run on the prior
code (the import of the new helpers removed): `4 failed, 1 passed` — AC1, AC2, the sweep and AC3 (AC3 only because
the method it patches did not exist); the no-suggestion case passed before too.

**AC4 — the tool on a fresh full build of this branch** (`CA_DB_PATH=<scratch> code-atlas-build --full` at
`2b52e9ad`: `702 file(s), 9792 node(s), 54574 edge(s), 4 failed`):

| query | `did_you_mean` | `candidates` (253) |
|---|---|---|
| `full_biuld` | `code_atlas.indexer.full_build` (2) | five `FULL…` names, no `full_build` |
| `resolves_insdie` | `code_atlas.containment.resolves_inside` (2) | it, 4th of 5 |
| `estimate_tokesn` | `code_atlas.tokens.estimate_tokens` (2) | it, 1st |

**AC5 — miss-path median of 7 calls, before → after** (the anchor is an exclusion):

| index | nodes | query | before | after | suggestion |
|---|---|---|---|---|---|
| pydantic | 17,422 | `model_valdiate` | 50.1 ms | 62.6 ms | `model_validate` (2) |
| pydantic | 17,422 | `validate_pytohn` | 35.3 ms | 44.1 ms | `validate_python` (2) |
| adventureworks_oltp | 6,752 | `EmailAdress` | 275.3 ms | 278.7 ms | `EmailAddress` (1) ×5 |
| this repo | 9,792 | `resolves_insdie` | — | 9.7 ms | `resolves_inside` (2) |

The store pass alone on pydantic: `__init_` 4.0 ms, `test_valdate` 11.6 ms, `test_model_validate_jsn` 31.8 ms
(none in bound), `valdiator` 2.3 ms. This repo's "before" was not comparable: restoring the old files dirtied
the tree, so the old code answered `index_stale`.

```
$ .venv/bin/python -m pytest -q tests/test_search_did_you_mean.py tests/test_zero_overlap_token_candidates.py
12 passed in 1.53s
Ran at 255b9437
```

```
$ scripts/gate.sh
21 passed · 0 failed · 0 skipped
GATE GREEN — all 21 checks passed
Ran at 255b9437
```

**Verification sweep.** File axis: the diff is the change list; `ruff check`, `mypy code_atlas` clean.
Behaviour axis: Approach 1–3 implemented as approved, except H9 — a first draft dropped a qname already in
`candidates`; AC1 showed it hid the answer, and the lists are independent.

## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. Reviewed at 9ad429fb — files: `code_atlas/store.py`,
`code_atlas/tools/search_symbol.py`, `tests/test_search_did_you_mean.py`, `docs/TOOLS.md`, `CHANGELOG.md`;
working doc: this file.

- **`reviewer` round 1 — LGTM** (49,615 tokens): R1.4, R3.2, R4.2, R5.6, R5.8 checked; every trigram quoted, the
  query and bounds bound as parameters. Advisories: (1) a swapped pair costs 2, so a transposed short name misses —
  stated in `edit_distance`'s docstring (`e120b070`, docstring only, verify-only in the main loop; OSA left to W1's
  ratification); (2) the SQL has no LIMIT before the sort — bounded by the length window and the UDF bound, measured
  above; (3) W1 stays flagged.
- **`challenger` round 1** (ticket-blind, 51,524 tokens): 8 met · 1 not met · 2 can't tell. Not met: AC5 — it read
  the task file before this doc was written; the cost now stands in Phase 3, and the anchor figure is the recorded
  exclusion. Can't tell: the contract question and the cost bound — both answered in Phase 2 (Assumptions).
- **PR #58 review** (general-purpose, 81,613 tokens): (1) the trigram-OR prefilter dropped a typo inside a
  short name (`paxse` → nothing, then a hint saying the name may be absent); (2) common trigrams made it near-linear;
  (3) the hint named `candidates` when only `did_you_mean` had entries. Fixed: the prefilter splits the segment
  into bound + 1 pieces — a name within the bound keeps one whole (pigeonhole, property-tested) — matched through
  the trigram index when every piece has 3+ characters, else a `name` scan; the UDF is memoised per name; a new
  `TRY_INSTEAD_HINT_DID_YOU_MEAN`. 200k-node synthetic, old → new: `get_settinsg` 616 → 186 ms, `proces_order`
  452 → 78 ms, `update_user_itme` 1,258 → 302 ms, `paxse`/`rendr` 0/25 → 43/42 ms (no 5-letter names there; the new test seeds them).

Verdict: clean — AC5's "not met" corresponds to the recorded coverage-gap exclusion. Matrix `Ph3/4 proven by`:
R1–R3, AC1–AC3 → `tests/test_search_did_you_mean.py`; AC4 → the Phase 3 table; R4, C2 → the docstring, no new tool.

## Phase 5 — finalise

**Durable lesson.** None new — H9 (a dedupe that would hide AC1's answer) is this ticket's own design note.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/378-search-did-you-mean-by-edit-distance`; open the PR against 377's branch
(stacked on #57). Deferred to the maintainer: ratify W1–W3; AC5 on the anchor; merge.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 40,564 |
| 4 review | `reviewer` | 1 | 49,615 |
| 4 review | `challenger` (ticket-blind) | 1 | 51,524 |
| PR review | general-purpose | 1 | 81,613 |

`LEDGER TOTAL: 223,316 · top cost driver: PR review`
