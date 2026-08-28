---
id: 180
slug: search-ranks-a-near-miss-above-exact-matches
title: '`search_symbol` ranks a substring near-miss above six exact matches — 167 computes exactness and then discards it for ordering'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [167, 014, 057]
---

## Why this exists (field retro round 12)

Round 12's **only harmful answer**, and the only DISAGREED row in a 10-of-10 PHP session:

> `search_symbol("showAttachment")` → page 1 of 46. Rows 1–2 are
> `public/js/timesheet.js::showAttachmentMsg` and its `legacy/beta` twin; rows 3–8 are six `legacy/*`
> PHP `\showAttachment`. **Zero `src/` rows on page 1**, though
> `src/Application/Alpha/Movement/Page/views/movement_list.php:1126` defines
> `function showAttachment($attachArray, $id)` — the definition the evaluator wanted.
> `reason: "ok"`. `grep -rn "function showAttachment" src/` returned **5 src hits in 0.013 s**.

Two distinct faults arrive in one payload, and only the second is new:

1. A **substring near-miss outranked exact matches**. This is the ranking, not the label.
2. `reason` was `"ok"` — **correct**, because exact matches *were* present. 167's contract is that
   `substring_match` fires when the first page holds *no* direct match. So the honest reading is
   *the label is right and the order is wrong*, which is worse than a wrong label: nothing in the
   payload warns that the top rows are not what was asked for.

## The defect, at source

`store.py:142` — `_SEARCH_ORDER = "nodes_fts.rank, nodes.qualified_name, nodes.file_path, nodes.id"`.
The order is **BM25 then alphabetical. There is no exactness tier in it at all.**

`search_symbol.py:220` — `_is_direct_match(query, row)` already answers *"is this an exact match or a
prefix of the row's name or qname?"*, case-insensitively and with no SQL. It is called at `:212` for
exactly one purpose: choosing between `reason: "substring_match"` and `reason: "ok"`.

**167 built the predicate, used it to label the answer, and left the ordering untouched.** A shorter
document scores better under BM25, so a near-miss in a small JS file outranks an exact match in a
large PHP one — which is precisely the shape adapter #2 made common (round 12 §13: *"the JS half made
a PHP answer worse"*).

## Scope

1. **Exactness becomes the primary sort key**, ahead of `nodes_fts.rank`: direct matches first,
   near-misses after, existing full ordering as the tie-break inside each band (R4.2).
2. **One definition site (R6.7).** The band is decided by the same predicate `reason` is decided by —
   `_is_direct_match`, not a second rule in SQL that can drift from it. Design records how a
   predicate that is deliberately not-SQL (R1.1: a run against the returned symbol, language-agnostic)
   reaches the ordering: re-rank the page in memory, widen the fetch and re-rank, or lift the
   predicate into the query.
3. **`total_count` and paging stay honest** (057/066). Re-ranking *within* a page is cheap and wrong
   at a page boundary: an exact match at rank 51 does not reach page 1 by sorting page 1. Design must
   state which of the two it delivers and what the other would cost — **a fix that only reorders the
   rows already fetched must say so in the payload or it is a second silent partition.**

### Explicitly not in scope

- Changing `reason`'s semantics. 167's rule is correct and stays: `substring_match` when the page
  holds no direct match. This ticket does not make `ok` mean less.
- Suppressing or filtering near-misses. They are legitimate results; the complaint is their position.
- Per-language weighting. *"Prefer PHP over JS"* is a repo preference and R2 forbids it in the core;
  the correct discriminator is exactness, which is language-agnostic.
- The FTS/trigram query itself, and `kind`/`namespace` filtering.

## Constraints

- **061** — a query whose page holds only direct matches, or only near-misses, is byte-identical:
  banding cannot reorder a homogeneous page.
- **Cost** — `search_symbol` is the highest-frequency tool and is reached from sweeps (101). No
  per-row query. An in-memory re-rank over rows already fetched is free; a widened fetch is not, and
  its cost must be measured against the tokens-to-answer gate.
- **R4.2** — deterministic: the full ordering already exists as the tie-break, so equal-band rows
  cannot reorder between runs.
- **R1.1** — no language branch; **R3** — no contract bump (ordering is not vocabulary), confirm.
- **057** — `offset` pages in search order; whatever order this establishes must be the one `offset`
  walks, or page 2 repeats page 1's rows.

## Acceptance criteria

1. A fixture where a substring near-miss scores better under BM25 than an exact match returns the
   **exact match first** — pinned by a test that fails on today's code.
2. `reason` is unchanged for every existing case: `ok` when a direct match is on the page,
   `substring_match` when none is, both pinned (167 untouched).
3. The band predicate has **one** definition site, shared with `reason` (R6.7), pinned.
4. Paging is coherent: `offset` walks the new order, and page 2 does not repeat page 1 — pinned.
5. A homogeneous page (all direct, or all near-miss) is byte-identical to today (061).
6. If the fix re-ranks only the fetched page, the payload says so and the design records why the
   whole-result-set alternative was rejected, with its measured cost.
7. Added cost measured against the tokens-to-answer gate; no per-row query.
8. Determinism (R4.2), no language branch (R1.1), contract impact confirmed (R3).

## References

Field retro round 12 §3 (the DISAGREED row), §6 (3.3× against the tool **and the wrong page**), §13
(*"the JS half made a PHP answer worse"*), §14 row 6-C (completeness harming, now on a second
language), §14 row 9-C/10-D (167 holds on PHP, fails a weaker form on JS).
`code_atlas/store.py:142`; `code_atlas/tools/search_symbol.py:212,220-230`. Related:
[167](167_a-substring-near-miss-is-reported-as-reason-ok.md) (built the predicate),
[057](057_answer-pagination.md) (search order is what `offset` walks).

## Session status

- **KEY:** 180 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, 10-ticket batch) · envelope in `.mango/run-contract-180.txt`.
- **Branch:** `feat/180-exactness-is-the-primary-search-order`
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2236 passed, 0 failed` at `dc90241` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

Scope 2 delegates one question explicitly — *"Design records how a predicate that is deliberately
not-SQL (R1.1) reaches the ordering: re-rank the page in memory, widen the fetch and re-rank, or lift
the predicate into the query."* A **how-decision**: the three options are readable from the store's
shape and are priced by the constraints the ticket already states. Resolved in Phase 2 → *Approach* /
*Rejected alternatives*. Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous`
`RECALL: 2 claim(s) surfaced | 1 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=6 R=3 G=1 AC=8`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 11 applicable — 9 by change-type | 2 by recalled handle — §R1.1 (change-type) ✅ · §R1.4 (change-type) ✅ · §R1.8 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.5 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ · §R7.2 (change-type) ✅ · §R7.6 (change-type) ✅`
`BASELINE: green — 2236 passed, 0 failed, 0 skipped at dc90241 (bare pytest, Linux host)`

**Premise:** all three citations resolve. `store.py:142` is `_SEARCH_ORDER` (BM25 then alphabetical,
no exactness tier). `search_symbol.py:212` is the one call site of `_is_direct_match`, deciding
`reason` only. `:220-231` is the predicate. Nothing had moved.

**Recall:** `rank-before-truncate` (by handle — R6.5-adjacent, seen 067, 126; **this is sighting 3**).
`derived-not-listed-invariant` (R6.7, by handle — one predicate site, not one per layer).
`167` (by symbol: `_is_direct_match` — the predicate this reuses).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | 167 computes exactness and then discards it for ordering | band on it | `store.py:142` has no exactness tier | open |
| R1 | Scope 1 | exactness becomes the primary sort key, ahead of `nodes_fts.rank` | direct first, existing ordering as in-band tie-break | — | open |
| R2 | Scope 2 | one definition site (R6.7); design records how a not-SQL predicate reaches the ordering | the predicate itself, lifted into the query | `_is_direct_match` is pure Python | open |
| R3 | Scope 3 | `total_count` and paging stay honest; say which of page-local / whole-set is delivered | whole result set, so nothing to disclose | `count_search_nodes` is order-free | open |
| AC1 | AC 1 | a near-miss scoring better under BM25 returns the exact match first, pinned by a test failing on today's code | Falsifiable: order asserted + red run | proving test | open |
| AC2 | AC 2 | `reason` unchanged for every existing case, both pinned | Falsifiable: `ok` and `substring_match` asserted | proving test | open |
| AC3 | AC 3 | the band predicate has **one** definition site, shared with `reason` (R6.7), pinned | Falsifiable: grep-derived, plus a SQL-vs-Python agreement test | proving test ×2 | open |
| AC4 | AC 4 | `offset` walks the new order; page 2 does not repeat page 1 — pinned | Falsifiable: two pages asserted disjoint and equal to the whole | proving test | open |
| AC5 | AC 5 | a homogeneous page (all direct, or all near-miss) is byte-identical (061) | Falsifiable: two tests | proving test ×2 | open |
| AC6 | AC 6 | if only the fetched page is re-ranked, the payload says so and the design prices the alternative | **branch not taken** — whole-set banding delivered; the alternative is priced below | proving test | open |
| AC7 | AC 7 | added cost measured against the tokens-to-answer gate; no per-row query | Falsifiable: statement count + timing + `gate.sh` | proving test + gate | open |
| AC8 | AC 8 | determinism (R4.2), no language branch (R1.1), contract impact confirmed (R3) | Falsifiable: repeat-call equality + grep-gates | proving test + `gate.sh` | open |
| C1 | Constraint | 061 — a homogeneous page is byte-identical: banding cannot reorder it | a constant band is a no-op | — | binding |
| C2 | Constraint | cost — highest-frequency tool, reached from sweeps (101). **No per-row query** | one statement, unchanged | — | binding |
| C3 | Constraint | R4.2 — the full ordering already exists as the in-band tie-break | reuse it verbatim | — | binding |
| C4 | Constraint | R1.1 no language branch; R3 no contract bump (confirm) | ordering is not vocabulary | — | binding |
| C5 | Constraint | 057 — whatever order this establishes must be the one `offset` walks | SQL-level, not page-level | — | binding |
| C6 | Constraint | not in scope: `reason`'s semantics, suppressing near-misses, per-language weighting, the FTS query, `kind`/`namespace` filtering | ordering only | — | binding |

### Root cause (taxonomy: logic / ranking)

Two facts about a row were computed in two different layers and only one of them reached the order.
BM25 is a **relevance** score and a shorter document scores better, so it is systematically wrong
about exactness: `preloadReport` in `n0.js` beats `\Ns\Area\Module0\loadReport` in a deep path with
params. 167 built the exactness predicate one layer above the query, used it to *label* the answer,
and left `ORDER BY` untouched — so the payload was honest and the page was still wrong. Adapter #2
made the shape common, because JS files are the short documents.

### Blast radius

- `store.py`: the predicate's new home, one registered SQLite scalar, one `ORDER BY` and one extra
  bound parameter. No schema change, no new table, no index.
- `search_symbol.py`: the predicate's old home loses it and imports it instead; one row-shaped
  wrapper; the `reason` branch is otherwise untouched.
- Every `search_nodes` caller inherits the order. `count_search_nodes` is order-free, so
  `total_count` cannot move.
- `_search_short` (queries under 3 chars) is **structurally homogeneous** — every row it returns is a
  name/qname prefix match, so `is_direct_match` is true for all of them and a band would be a
  constant. Deliberately not banded; noted rather than done.

## Phase 2 — design

### Approach

`is_direct_match(query, name, qualified_name)` moves from `search_symbol.py` into `store.py` — the
same direction `fts_term` already travels (tools import query helpers from the store; the store
imports nothing from tools, R1.4). `GraphStore.__init__` registers it on the connection as a
`deterministic=True` scalar named `ca_direct_match`, and `search_nodes` orders by

```
ORDER BY ca_direct_match(?, nodes.name, nodes.qualified_name) DESC,   -- the band (180)
         nodes_fts.rank, nodes.qualified_name, nodes.file_path, nodes.id   -- unchanged (R4.2)
```

**This is "lift the predicate into the query" without lifting a *copy* of it.** The thing SQLite
calls per row *is* the Python function `reason` calls, so R6.7 holds by construction rather than by
convention: there is no SQL spelling of the rule that can drift from the Python one. It also answers
Scope 3 in the strong direction — the band orders the whole result set, so an exact match BM25 ranked
at 51 reaches page 1, `offset` walks the banded order, and **no payload disclosure is owed** (AC6's
first branch is not taken).

### Rejected alternatives

- **Re-rank the fetched page in memory.** Free, and wrong exactly where the field defect was: the
  round-12 answer was *page 1 of 46*, and no amount of sorting page 1 brings the `src/` definition
  into it. The ticket permits it only with a payload confession, which is a second silent partition
  wearing a label. Its measured cost is ~0 and its measured value is 0 on the reported case.
- **Widen the fetch, then re-rank in memory.** Needs a widen factor, which is a threshold, which is a
  claim about how far a near-miss run can extend — unbounded in principle (46 pages of near-misses is
  a real observation, not a hypothetical). It buys a probabilistic version of what the UDF gives
  exactly, at strictly higher cost: it transfers every widened row into Python instead of one integer
  per row.
- **Re-implement the predicate as SQL** (`LOWER(name) LIKE ?||'%' OR …`). Cheaper per row and
  explicitly forbidden by Scope 2: a second definition site that can drift from the one deciding
  `reason`, so the order and the label could disagree — the exact pathology 180 exists to fix, moved
  one layer down.
- **Per-language or per-path weighting** ("prefer `src/` over `legacy/`"). Out of scope and R2-barred:
  a repo preference in the core.

### Assumptions

| Assumption | Tag |
|---|---|
| A near-miss really does outrank exact matches under BM25 for this shape | **verified by measurement before the design** — 2 near-misses in `*.js` ahead of 6 exact matches, reproduced standalone, then re-pinned as `test_the_fixture_defeats_both_default_orders` |
| `count_search_nodes` is order-independent, so `total_count` cannot move | verified — `SELECT COUNT(*)`, no ORDER BY |
| A parameter in `ORDER BY` binds after the `WHERE` parameters and before `LIMIT`/`OFFSET` | verified — the paging tests would be wrong-by-one otherwise, and the statement-trace test prints the bound SQL |
| `_search_short` needs no band | verified — its `WHERE` is the prefix predicate, so every row is a direct match |
| `nodes.name` / `nodes.qualified_name` are never NULL | **not relied on** — the scalar coerces `None` to `""` rather than trusting the schema |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `is_direct_match` + `_direct_match_udf` + `DIRECT_MATCH_SQL_FN` + `_SEARCH_BAND`; register the scalar; band `search_nodes` | `code_atlas/store.py` | one predicate site (R6.7); one ORDER BY | R1, R2, R3, AC1, AC3–AC8 | 1/1 |
| Drop the local predicate, import the shared one, `_direct` row wrapper; docstring states the order | `code_atlas/tools/search_symbol.py` | `reason` branch unchanged | R2, AC2, AC3 | 1/1 |
| Proving tests (11) | `tests/test_search_exactness_band.py` (new) | new file | AC1–AC8 | 1/1 |
| BACKLOG; ledger; LESSONS; working doc | `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `derived-not-listed-invariant` (R6.7) — **traced.** One predicate site; SQL cannot hold a copy:

  ```
  $ grep -rl 'def is_direct_match' code_atlas/     # Ran at 5fb8b1f
  code_atlas/store.py
  $ grep -rn 'def _is_direct_match' code_atlas/ ; echo "exit=$?"
  exit=1
  ```

- `rank-before-truncate` (067, 126 → **180**, sighting 3) — **traced.** This ticket is the class in
  its purest form: the ranking was computed, then the page was cut by a *different* order. The fix
  puts the ranking *inside* the statement that truncates, so the two cannot come apart. Recurrence
  now 3 and the class is still `proposed`; recorded in *Learning loop* below, **not promoted** — the
  destination is `rulebook_path` and promotion needs a human to ratify (`/mango:promote`).

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (the field shape, end to end through the tool) | integration test + its own non-degeneracy guard | ✅ |
| AC2 | integration (both `reason` values over banded pages) | integration test ×2 | ✅ |
| AC3 | guard (grep-derived) + logic (SQL scalar vs Python, 5 cases) | integration test ×2 | ✅ |
| AC4 | integration (page 1, page 2, and the whole list) | integration test | ✅ |
| AC5 | integration (all-direct; all-near-miss) | integration test ×2 | ✅ |
| AC6 | integration (an exact match ranked past page 1 by BM25 reaches page 1) | integration test | ✅ |
| AC7 | measurement (statement count; 200 calls timed) + gate (tokens-to-answer) | integration test + `gate.sh` | ✅ |
| AC8 | logic (two identical calls agree) + guard (grep-gates) | integration test + `gate.sh` | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

**AC1 is input-shape-dependent and that is stated, not hidden.** The proving fixture is authored, so
it demonstrates the ordering rule; it does not prove the field repo's 46-page answer now leads with
`src/`. What makes it more than a fixture is that the BM25 inversion was **measured before the design
was written** and is now pinned as an assertion of its own (below), so the fixture cannot quietly
stop exhibiting the defect it exists to exhibit.

### Proving test

`tests/test_search_exactness_band.py::test_an_exact_match_outranks_a_better_scoring_near_miss`

### Rollback + porting

Rollback: revert two source files and delete the test file; nothing persisted, no schema or contract
change, so an old index is unaffected. Porting: `app` only.

### SCOPE

`SCOPE: M` — one ORDER BY term and one moved predicate; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `is_direct_match` lives in `store.py`, the direction `fts_term` already travels (R1.4) | implemented-as-approved |
| Registered as a `deterministic=True` SQLite scalar; the band calls the predicate, not a copy | implemented-as-approved |
| Band ahead of `nodes_fts.rank`; the pre-existing full ordering is the in-band tie-break verbatim | implemented-as-approved |
| Whole result set, so `offset` walks it and no payload confession is owed | implemented-as-approved |
| `_search_short` left unbanded (structurally homogeneous) | implemented-as-approved |
| `reason`'s rule, `total_count`, the FTS query, `kind`/`namespace` untouched | implemented-as-approved |

No deviations. Diff ⊆ approved list.

### Empirical outputs

**The BM25 inversion, measured before any code changed** — the field report reproduced standalone
with generic names (R2), two near-misses in short `.js` documents ahead of six exact matches:

```
# standalone repro, pre-fix at dc90241 (not committed — its assertion is, see below)
('preloadReport', 'a.js',   -1.6943231441048035e-06)
('preloadReport', 'b.js',   -1.6943231441048035e-06)
('loadReport', 'src/deep/nested/module/area/view/list_0.php', -1.293725371324644e-06)
… five more exact matches …
```

That inversion is now a committed assertion (`test_the_fixture_defeats_both_default_orders`), so the
fixture states its own non-degeneracy — the near-misses lead under **both** default orders, BM25 and
insert order, and neither can be the reason a later assertion passes (171-C1).

**Red run (R6.5)** — band removed from `ORDER BY`, everything else in place:

```
$ .venv/bin/pytest -q tests/test_search_exactness_band.py     # band reverted
>       assert names[0] == f"\\Ns\\Area\\Module0\\{QUERY}"
E       AssertionError: assert 'preloadReport' == '\\Ns\\Area\\...0\\loadReport'
>       assert _names(payload) == [f"\\Ns\\Area\\Module{i}\\{QUERY}" for i in range(3)]
E       At index 0 diff: 'preloadReport' != '\\Ns\\Area\\Module0\\loadReport'
4 failed, 7 passed
```

The **7 that stay green are the point**: the two 061 homogeneous-page tests, the two `reason` tests
and the R6.7 grep guard *should* pass without the band, because the band is not what they assert.
A red run that turned the whole file red would mean the file was testing one thing.

**AC7 — cost, measured, and the honest number is not zero.** Same statement, same corpus, band on
and off, 3,000 matching rows, 200 calls:

```
rows matching: 3000
unbanded ms/call: 2.705
banded   ms/call: 4.007
```

`+1.30 ms` over 3,000 candidate rows — **≈ 0.43 µs per candidate row**, the cost of one Python
callback per row SQLite must sort anyway. On the reported field answer (46 pages ≈ 460 rows) that is
≈ 0.2 ms. It is **one statement, not one per row** — asserted by a statement trace, not by
inspection — and the tokens-to-answer gate is unmoved because ordering changes no payload bytes:

```
$ bash scripts/gate.sh
  PASS tokens-to-answer (ratio >= 0.63, recall 1.0, precision 1.0)
```

This is the price of correctness at the page boundary. The page-local alternative costs ~0 and does
not fix the reported answer; that trade is the design's, made explicitly.

**Green run:**

```
$ .venv/bin/pytest -q                                  # Ran at 5fb8b1f
2247 passed in 152.52s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_an_exact_match_outranks_a_better_scoring_near_miss`, over a fixture whose own non-degeneracy is asserted by `test_the_fixture_defeats_both_default_orders` |
| AC2 | `test_reason_is_unchanged_by_banding` + `test_a_page_of_only_near_misses_is_byte_identical` (167's `substring_match` still fires on a banded page) |
| AC3 | `test_the_band_predicate_has_one_definition_site` (grep-derived, and asserts the tool-side copy has not returned) + `test_the_sql_band_and_the_python_predicate_cannot_disagree` (5 cases) |
| AC4 | `test_offset_walks_the_banded_order_and_page_two_does_not_repeat_page_one` — pages disjoint **and** equal to the head of the unpaged answer |
| AC5 | `test_a_page_of_only_exact_matches_is_byte_identical` + `test_a_page_of_only_near_misses_is_byte_identical` |
| AC6 | `test_the_band_reaches_beyond_the_fetched_page` — 3 exact matches behind 12 near-misses under BM25, `limit=3`, all three on page 1. Branch not taken ⇒ no payload confession owed |
| AC7 | `test_banding_adds_no_query_and_no_measurable_cost` (1 statement, `< 5 ms/call`) + the measured `2.705 → 4.007 ms` above + `gate.sh` tokens-to-answer |
| AC8 | `test_the_banded_order_is_deterministic`; `gate.sh` R1.1/R2.2/R4.1 green; no `contract.py` edit ⇒ **no bump (R3), confirmed** |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2236 passed / 0 failed` at `dc90241` →
`2247 passed / 0 failed`. ruff + mypy green. `scripts/gate.sh` → `GATE GREEN`.

### Learning loop

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 1 cannot promote (reason) | 1 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: rulebook_path (rank-before-truncate) | mango files written: 0`

- `rank-before-truncate` — `seen:` 067, 126 → **067, 126, 180**, recurrence **3**. Sighting 3 is the
  class stated at its source: the rank and the truncation were in two different layers, and the fix
  is to put them in one statement. Still `proposed`; **not promoted here** — the destination is
  `rulebook_path` and only a human ratifies a rule. Falsification: not falsified; the defect was
  reproduced by measurement before the fix.
- `derived-not-listed-invariant` (R6.7) gains 180 as a sighting: the exactness band is *derived from*
  the predicate rather than re-spelled in SQL, so the SQL and the label cannot drift. Recorded as a
  `seen:` bump on a class that is already a binding rule, not a fresh claim.
- **New, and it is the reusable part of this ticket:** `180-C1` (type-2,
  `one-predicate-two-layers-is-the-drift`) — where a predicate must run inside a query *and* inside
  the code reading the query's rows, register the function rather than re-spelling it in SQL. A
  second spelling is a second definition site that no test compares. seen=1 ⇒ stays in
  `lessons_path`.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived — nothing but the author
looked at this diff; recorded as line one of `DISCLOSURE`. No `Reviewed at` marker ⇒ the stale-review
guard is waived. Self-checks: the defect measured before the design, a red run isolating exactly the
four ordering assertions, a fixture asserting its own non-degeneracy, a measured non-zero cost stated
rather than rounded to free, full suite delta-green and `GATE GREEN`.
