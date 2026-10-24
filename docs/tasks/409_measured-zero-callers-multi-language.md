---
id: 409
slug: measured-zero-callers-multi-language
title: "`find_callers` on a caller-less PHP method answers `relation_unmodelled_for_language` on any multi-language index — keep a measured zero"
phase: 2
milestone: Honesty
status: in-progress
depends_on: [221, 238, 393]
---

## Why this exists

Issue [#101](https://github.com/cuongdinhngo/code-atlas/issues/101), 2026-10-24. On the anchor (PHP,
T-SQL, JS/TS) every empty `find_callers` on a PHP method answers `relation_unmodelled_for_language`,
never `no_matches` — five PRs in 19–23 Oct needed a Grep pass to claim "unused".

**Confirmed in code (2026-10-24):** `find_callers` upgrades `no_matches` whenever
`coverage.cross_language_relation_unmodelled` returns a census, i.e. whenever another language is
covered and no `*->L` pair exists. No language links into PHP on the anchor, so the upgrade fires
even when PHP→PHP resolution measured the subject completely (no `unresolved_bare_calls`, no
`unresolved_receivers`, no unlinked same-name sites). The flag meant for an unseen crossing hides a
measured zero.

## Scope

1. Upgrade to `relation_unmodelled_for_language` only when another covered language holds
   **unlinked** edges that could name the subject (same short name), or its stamped capabilities say
   it can call into L.
2. Otherwise answer `no_matches`, carrying the crossing as a field
   (`cross_language_unmeasured: [<lang>, …]`), not as the reason. `authoritative` stays honest (R5.6).
3. Check `find_references` and `impact` for the same census-only upgrade and apply the same rule.

Out of scope: calls from file-scope code in `include`d scripts (anchor #3679).

## Acceptance criteria

- AC1: A PHP method with no callers in a PHP+SQL fixture answers `no_matches` with
  `cross_language_unmeasured` naming SQL.
- AC2: The same method with an unlinked same-name site in the other language still answers
  `relation_unmodelled_for_language`.
- AC3: The 221/238 tests keep their verdicts or are re-decided in this ticket with the reason stated.
- AC4: P8: `cross_repo_validate.py` re-run; any moved reason counts re-floored.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 409 · **work_doc_mode:** embed · **Current phase:** 2 design · **Next action:** execute. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · Run mode: `autorun 408 - 409 - 410 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/409-measured-zero-callers`, **stacked on `feat/408-per-call-caller-root`** (#104). Contract `.mango/run-contract-409.txt`.
  RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 7 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 4 want-decision asked | 8 how-decision resolved+cited | 4 ASSUMED | skip: no`

**Premise.** `find_callers`, `find_references`, `impact`, `relation_unmodelled_for_language`, `no_matches`,
`unresolved_bare_calls`, `unresolved_receivers` resolve, as do tasks 221, 238 and 393. Ambiguous: "its stamped
capabilities say it can call into L" — no such capability exists (`contract.KNOWN_CAPABILITIES`, `contract.py:298`).
Recall (type 2, by handle — the change narrows a reason every empty answer shares): 363-C1
`a-zero-must-count-what-the-search-cannot-see` — a zero from a search must count the rows the search cannot match.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 68,575 tokens) raised eleven items, settled below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | which tools carry the census-only upgrade | how | `find_callers` alone: `find_references` reads the census on hits only (`find_references.py:726`) and upgrades an empty answer by emitted kind (`:629`, `:662`); `impact` has no census (`grep -c census code_atlas/tools/impact.py` → 0) |
| H2 | same-language completeness (393's `unresolved_receivers`) | how | unchanged: 393 made it a field, never a reason (`find_callers.py:665`); `unresolved_bare` and `unlinked_calls` still escalate first (`:603–607`) |
| H3 | the 238/276 hit-path caveat | how | unchanged for hits; it no longer reaches an empty answer, which is the hit arm's own scope ("Hits whose …", `:693`) |
| H4 | one query per empty answer, or a stamp | how | one bounded `EXISTS … LIMIT 1`, only on an empty answer that the census would have upgraded; the census stays a stamp read (221's `test_the_predicate_is_a_stamp_read_not_a_scan`) |
| H5 | which edges count as naming the subject | how | an unlinked `CALLS`/`NEW` from a file of another language whose `target_raw` is the subject's name or qname, or whose `arg_strings` holds one as a whole string — 398 stores a call's literal arguments there (`store.py:206`) |
| H6 | case | how | SQLite `LIKE` and the `target_raw` index are what the store already matches by (`count_unlinked_by_target_raw`, `store.py:2752`) |
| H7 | the reason and hint docs | how | the `find_callers` docstring and TOOLS.md say what now upgrades; the hint text is unchanged (it describes an unmeasured crossing, still true when it fires) |
| H8 | P8 | how | N/A: no build output moves; the change is a query-time reason |
| W1 | does a string argument "name" the subject (221's field shape: `querySP('proc')`) | want | **ASSUMED (awaiting ratification):** yes — otherwise 221's proc with five live callers is a confident zero again. 221's fixture, whose caller edge names the proc nowhere, is re-decided: it gains the argument the PHP adapter has emitted since 398, and a copy without it answers `no_matches` (AC3) |
| W2 | the ticket's capability clause | want | **ASSUMED (awaiting ratification):** dropped — no capability says "can call into L", and adding one is a contract bump (R3.1) for a signal the edges already carry |
| W3 | `authoritative` on the new `no_matches` | want | **ASSUMED (awaiting ratification):** not lowered. Every name another language could reach the subject by was searched; `cross_language_unmeasured` names the languages whose crossing has no linked edge at all (R5.6: the field separates the two states) |
| W4 | which languages `cross_language_unmeasured` lists | want | **ASSUMED (awaiting ratification):** every other covered language — the census already says none has a linked pair into L — sorted, at every detail level |

## Phase 1 — analysis

`PREMISE: 7 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=3 G=1 AC=4`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

W1–W4 count as self-resolved because the handover handed them back; each stands `ASSUMED` for the maintainer.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "The flag meant for an unseen crossing hides a measured zero" | an empty `find_callers` on a fully measured subject answers `no_matches` | ✅ |
| C1 | Scope 2 | "`authoritative` stays honest (R5.6)" | the field separates "measured zero" from "unmeasured crossing" (W3) | ✅ |
| C2 | Out of scope | "calls from file-scope code in `include`d scripts" | untouched | ✅ |
| R1 | Scope 1 | "upgrade … only when another covered language holds unlinked edges that could name the subject … or its capabilities say …" | H5, W1; the capability clause dropped (W2) | ✅ |
| R2 | Scope 2 | "otherwise `no_matches`, carrying `cross_language_unmeasured`" | W4 | ✅ |
| R3 | Scope 3 | "check `find_references` and `impact`" | H1: no census-only upgrade there; no change | ✅ |
| AC1 | AC1 | PHP method, no callers, PHP+SQL → `no_matches` + field naming SQL | seeded fixture | ✅ |
| AC2 | AC2 | an unlinked same-name site in the other language → still unmodelled | by `target_raw` and by `arg_strings` | ✅ |
| AC3 | AC3 | 221/238 keep their verdicts or are re-decided with the reason | W1 re-decides 221's fixture shape | ✅ |
| AC4 | AC4 | P8 re-run, moved counts re-floored | H8: no graph count moves | ✅ |

### AC validation

| AC | Falsifiable? | Definition |
|---|---|---|
| AC1 | yes | `reason == "no_matches"`, `cross_language_unmeasured == ["sql"]`, no `authoritative`, no `cross_language` |
| AC2 | yes | an `sql` edge `target_raw == name`, or a `php` edge `arg_strings == ["name"]`, flips AC1's subject to `relation_unmodelled_for_language` with the census attached |
| AC3 | yes | the 221/238 suite passes with the fixture's argument added; the argument removed → `no_matches` |
| AC4 | yes | `scripts/cross_repo_validate.py` reads build output only; no build code changes (`git diff --stat` touches no `store` writer, indexer or adapter) |

**Inventory — R3 (N = 3):** 1 `find_callers` (changed) · 2 `find_references` (no census upgrade, `:629`/`:662`) ·
3 `impact` (no census). Review confirms each.

### Root cause (bug — `logic`)

`find_callers.py:608`: `elif reason == REASON_NO_MATCHES and cross_lang_census is not None` upgrades every empty
answer whose language has no linked `*->L` pair (`coverage.cross_language_relation_unmodelled`, `coverage.py:81`). It
asks whether **any** crossing into L is modelled, never whether anything in another language could name **this**
subject. A language nothing links into (PHP on a PHP + T-SQL + JS index) therefore never answers `no_matches`.

**Blast radius.** `find_callers.py` (the arm, the docstring), `store.py` (one read), the 221/238 test file (fixture
argument, re-decided arm), TOOLS.md, CHANGELOG. Consumers of the reason: the signed claim (reason + authoritative,
unchanged in shape), `escalate_zero_production` (reads the reason after; a `no_matches` stays its input).

### BASELINE

`BASELINE: green — scripts/gate.sh at the stacked base: 21 passed · 0 failed · 0 skipped, GATE GREEN`

Ran at c733cedfec3a774aee526756ab632466b1f35640 (408's final gate; the base tip adds only that gate's record to 408's
task file).

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the evidence compares an edge's language with the subject's, never names one · §R1.4 (change-type) ✅ the query lives in store.py · §R1.8 (change-type) ✅ one store read decides the arm · §R5.6 (change-type) ✅ no_matches + cross_language_unmeasured vs relation_unmodelled_for_language, a test drives each · §R6.5 (change-type) ✅ AC1's test fails on the base · §R7.6 (change-type) ✅ the docstring and TOOLS.md sentences are rewritten in place`

The recalled handle (363-C1) is a lesson, not a rule-book section: it is answered at design (`HANDLES`).

## Phase 2 — design

### Approach

1. `GraphStore.named_from_another_language(raws, *, language, kinds)`: does an unlinked edge of `kinds`, in a file
   (or region, 399) of a language other than `language`, name one of `raws` — as its `target_raw`, or as a whole string
   in its `arg_strings`? One `EXISTS … LIMIT 1`.
2. `find_callers`: on an empty answer the census would have upgraded, the upgrade needs that read to say yes (raws:
   the stored qname and the short name). Otherwise the answer stays `no_matches` and carries
   `cross_language_unmeasured` — the other covered languages, sorted. The 238/276 hit-path caveat requires hits.
3. Tests: 221's fixture caller gains `arg_strings` (W1); new tests for AC1/AC2 and the re-decided arm.
4. Docs: the `find_callers` docstring sentence, TOOLS.md's reason line, CHANGELOG.

### Rejected alternatives

- **A build-time stamp of every string another language passes** — a table the size of the literal corpus, to save
  one bounded read on the empty-answer path.
- **Match `target_raw` only (the ticket's literal proposal)** — 221's field shape names the proc only as an argument,
  so its confident zero would return (W1).
- **A new "calls into L" capability** — W2: a contract bump for a signal the edges carry.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| `arg_strings` holds a JSON list of a call's literal string arguments | verified | `store.py:206`; on `adventureworks_oltp`: `('guest', '["auth/login"]')` |
| the read is cheap enough for the empty-answer path | verified | `adventureworks_oltp` (330,867 edges, 223,931 unlinked): a no-hit `EXISTS` over unlinked `arg_strings` took 33.3–35.6 ms; the anchor (2.19 M edges) is unmeasured here |
| the hit-path caveat never needed an empty answer | verified | today an empty answer with a census is always upgraded first (`find_callers.py:608`), so the `elif` at `:691` saw only hits |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | the evidence read | `code_atlas/store.py` | none identified — a new method | R1, AC2 | 1/1 |
| 2 | the arm, the field, the docstring | `code_atlas/tools/find_callers.py` | the signed claim (reason only); `escalate_zero_production`'s input | R1, R2, AC1, C1 | 1/1 |
| 3 | tests | `tests/test_find_callers_cross_language_unmodelled.py` | 221/238's assertions (W1) | AC1–AC3 | 1/1 |
| 4 | docs | `docs/TOOLS.md`, `CHANGELOG.md` | doc size budgets | G1 | 2/2 |
| 5 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `a-zero-must-count-what-the-search-cannot-see` — traced: `rtk proxy grep -n "arg_strings\|target_raw" code_atlas/store.py | head -3`
  → `206: kwargs TEXT, arg_strings TEXT, kwarg_strings TEXT, language TEXT);` and `210: CREATE INDEX … idx_edges_raw
  ON edges(target_raw, kind)`. The zero searches both places another language names a callee; what neither can see —
  a crossing with no name at all — is the `cross_language_unmeasured` field, so the zero never claims it.

### Rule compliance

The six sections of Phase 1 bind the design unchanged. R7.5 binds every comment.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — store + tool | seeded PHP + SQL index, stamped census, `find_callers` | n/a | ✅ |
| AC2 | integration | the same with an `sql` same-name edge, and with a `php` string argument | n/a | ✅ |
| AC3 | integration | the 221/238 file, fixture with and without the argument | n/a | ✅ |
| AC4 | logic | the diff touches no build path | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_find_callers_cross_language_unmodelled.py`

### Rollback

`git revert`; no stored state. One repo.

`SCOPE: M` — unchanged.
