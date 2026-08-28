---
id: 180
slug: search-ranks-a-near-miss-above-exact-matches
title: '`search_symbol` ranks a substring near-miss above six exact matches — 167 computes exactness and then discards it for ordering'
phase: 1.5b
milestone: Agent-trust
status: todo
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
