---
id: 204
slug: bare-name-resolution-has-no-language-predicate
title: 'The bare-name HEURISTIC fallback never asks what language the call was written in, so 342,758 JavaScript built-in calls link to PHP methods — 16 % of the anchor''s whole edge graph, and `files.language` was populated the whole time'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [046, 137, 183, 185, 186]
---

## Why this exists (measured on the anchor monorepo, 2026-09-01)

`resolve_edges` ends with a last-chance fallback: a `CALLS` edge whose receiver could not be
determined is linked to **any node in the graph that shares the method's bare name**
(`code_atlas/resolver.py:175-184`):

```python
if by_name:
    method_hits = store.nodes_by_names(
        [name for _, name in by_name], kind="Method", limit=max_candidates
    )
    for edge, name in by_name:
        methods = method_hits.get(name, [])
        if methods:
            # Weaker than what the edge claimed, never stronger: the name matched, the
            # receiver did not (R5.2).
            _queue_candidates(edge, methods, "HEURISTIC", links, siblings)
```

The comment is honest about the receiver and silent about the **language**. `nodes_by_names` filters
on `kind="Method"` and nothing else, so a `.push()` written in JavaScript is offered every `push`
method in the index, including every PHP one. On a repo holding more than one language that is not a
weak link — it is a link to a callee that cannot be called.

### What it costs on the anchor

24,569 files, 2,188,026 edges, three adapters (`files.language`: php 19,155 · sql 2,980 ·
typescript 2,434). Counting every edge **declared in** a `.js`/`.ts` file whose `target_qname`
resolves to a node **in** a `.php` file:

| | edges |
|---|---|
| JS/TS-declared edges with a resolvable target | 467,919 |
| …of which the target is a PHP file | **342,758 (73.3 %)** |
| …of those, tier `RESOLVED` | **0** |
| …of those, tier `HEURISTIC` | 342,758 (100 %) |
| Share of the whole 2.19 M edge graph | **15.7 %** |

**Zero cross-language edges are `RESOLVED`.** The resolver never legitimately resolves across a
language boundary; it only ever *guesses* across one. That asymmetry is the finding: the fallback is
the sole producer of these edges, so a language predicate on that one call site removes all of them
and nothing else.

The top targets are not obscure collisions. They are the JavaScript standard library:

| edges | target the resolver chose | what the call site actually is |
|---|---|---|
| 10,233 | `\Zend_Db_Table_Abstract::find` | `Array.prototype.find` |
| 10,108 | `\LoggerNDC::push` | `Array.prototype.push` |
| 6,822 | `\adLDAPUsers::find` | `Array.prototype.find` |
| 6,714 | `\Zend_Cache_Frontend_Function::call` | `Function.prototype.call` |
| 5,928 | `\ADODB_Session::filter` | `Array.prototype.filter` |
| 5,247 ×4 | `\Zend_Cache_Backend_{Apc,File,Interface,Memcached}::test` | `RegExp.prototype.test` |
| 5,054 ×2 | `\PHPExcel_Token_Stack::push`, `\Src\Utilities\UtilBase::push` | `Array.prototype.push` |

Note the `::test` row: **one** `regex.test(x)` in JavaScript fans out to four PHP classes at once,
because `max_candidates` caps the fan-out per name but does not filter it. The multiplication is why
this reaches 16 % of the graph from a fallback that was meant to be a last resort.

The reverse direction is 309 edges — PHP call sites are usually qualified, so they rarely reach the
fallback. And PHP↔SQL cross-language edges are **0**: the T-SQL adapter emits schema-qualified qnames
(`dbo.Foo`), which have no bare-name collision surface. The defect is specific to the bare-name path,
not to multi-language indexing as such.

### The data to fix it has been in the schema the whole time

`store.language_of_file(path)` already exists (`code_atlas/store.py:788`) and reads
`files.language`, which is populated for 100 % of indexed files on the anchor. The resolver holds
`edge["file_path"]` for every edge it is about to link. Nothing needs to be collected, migrated or
inferred from a suffix — the join is available and simply never made.

### Why 183/185/186 did not catch this

The three tickets that took multi-language seriously all measured from the **outside**:

- **183** gave `edge_health` a per-language breakdown — but it keys on the language of the file the
  edge was *declared in*, so all 342,758 of these count as healthy `typescript` HEURISTIC edges.
  Today's `confidence_by_language` reports `typescript: 445,728 HEURISTIC` and reads as an adapter
  that resolves poorly, when three quarters of that number is one resolver bug.
- **185** asked the 22 tools a question over a second language's graph and checked they answered.
  These edges make the tools answer *more*, not less.
- **186** taught a zero answer to say "this relation is unmodelled for this language". The failure
  here is the opposite polarity: a confident **non**-zero answer, which no coverage note covers.

Every one of the three would still pass after this ticket lands. That is the argument for it being
its own ticket rather than a tail on 186.

### Blast radius beyond the number

These are ordinary `CALLS` edges, so every tool that walks `CALLS` inherits them: `find_callers`,
`impact`, `impact_modules`, `reachable_from`, `explain_path`, `subtree_dependencies`,
`architecture_overview` and the onboarding artifact. The field symptom that surfaced this was an
onboarding module page for a JavaScript controller whose entire **Neighbours** section named
`Zend/Db/Statement/Pdo.php` and `Zend/Mail/Protocol/Smtp.php` — every listed neighbour false, on a
page a newcomer is meant to read first (see 205, which depends on this).

## Scope

1. **Measure first, on the anchor, before changing anything.** Record the four counts in the table
   above and the per-tool effect on at least `find_callers` and `impact` for one JS symbol, so the
   fix has a before to be judged against (P4). The counting query belongs in the ticket's PR, not in
   a scratch file.
2. **Give the bare-name fallback a language predicate.** The candidate set for a bare-name `CALLS`
   link is restricted to nodes declared in files of the **same** `files.language` as the call site.
   The predicate goes in the candidate query, not in a post-filter, so `max_candidates` still selects
   from the legal set rather than being spent on candidates that are then discarded.
3. **Decide the cross-language escape, and write down why.** Some repos genuinely call across a
   language boundary (FFI, a PHP template emitting a JS callback name). This ticket's position is
   that a *bare-name* match is never sufficient evidence of one, so the default is same-language and
   the escape — if any — is an explicit configured pair, never an inference. If the implementer
   disagrees, that argument belongs in the PR with a counter-example from a real repo.
4. **Make `edge_health` able to see this class of defect.** 183's per-language rows count the
   declaring language only. Add a cross-language count so the same measurement can be taken next
   time without hand-written SQL — a row saying how many linked edges cross a language boundary and
   at which tier. On a fixed index that row reads 0; a non-zero value with no configured escape is
   the regression signal.
5. **A test that is red on today's resolver.** A two-language fixture where one language declares a
   method whose bare name a call in the other language also uses. Observed red before the fix
   (R6.5), or the test proves nothing.

## Constraints

- **Not a re-tier.** Dropping these to `DYNAMIC` would keep 342,758 false edges and merely relabel
  them. The edge is wrong, not uncertain.
- **The count will drop, and that is the point.** `edges` falls by roughly 15 % on the anchor and
  `linked` falls with it. Any test or recorded number that asserts a total edge count on a
  multi-language fixture is asserting the bug; update it in the same commit and say so.
- **Index-invalidating.** Existing indexes carry the false edges; the fix only takes effect on a
  rebuild. Decide whether this warrants a `contract_version` bump (which forces one, per 002) or a
  documented "rebuild to benefit", and state the choice in the PR.
- **The tier-1 chain is at its ceiling.** 203's `BACKLOG.md` row took it to 25,298 against
  `TIER1_BUDGET = 25_300`. This ticket's row and 205's do not fit; per R7.6 and the 175 / 192-195 /
  200-202 precedent, prune first and raise the budget with an argument, both in the same PR.

## Acceptance criteria

1. **AC1.** A two-language fixture in which a bare-name call in language A shares its method name
   with a declaration in language B produces **no** edge between them, and the test is recorded red
   against the pre-fix resolver (R6.5).
2. **AC2.** On a rebuilt anchor index, edges declared in a `.js`/`.ts` file whose target resolves
   into a `.php` file number **0** — measured by the same query recorded in scope 1.
3. **AC3.** Same-language bare-name resolution is unchanged: the PHP-only edge count and tier
   histogram on a PHP-only fixture are byte-identical before and after.
4. **AC4.** `edge_health` reports a cross-language row, and it reads 0 on the rebuilt anchor.
5. **AC5.** The before/after `find_callers` and `impact` answers for one named JS symbol are in the
   PR body, showing which callers disappeared and that none of them was real.
6. **AC6.** The decision from scope 3 is written where a reader of the resolver will meet it — a
   comment at the fallback, not only in this ticket.

## Not in scope

- **Modelling real cross-language calls.** If a repo needs FFI edges, that is a new relation with its
  own evidence, not a widening of a bare-name guess.
- **The HEURISTIC tier's same-language precision.** A `.push()` matching 12 PHP `push` methods in the
  same language is 046's fan-out question and stays as it is here.
- **The onboarding pages that surfaced this.** Filed as 205, which depends on this ticket: the page
  renderer's own defects are separate from the edges it renders.

## References

- `code_atlas/resolver.py:175-184` — the fallback, and the comment that names the receiver but not
  the language
- `code_atlas/store.py:788` — `language_of_file`, the join that was never made
- `code_atlas/store.py:1058-1062` — `nodes_by_names`, filtered on `kind` alone
- [183](183_edge-health-has-no-per-language-breakdown.md) — per-language rows that count the
  declaring language only
- [185](185_no-tool-is-ever-asked-a-question-over-a-second-languages-graph.md) ·
  [186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) — the
  multi-language work this sits beside, and why neither would fail today
- [046](046_resolver-qname-candidate-dedupe.md) · [137](137_php-local-type-table.md) — the
  candidate-set and receiver-typing work this fallback is the last resort after

## Session status

- **KEY:** 204 · **work_doc_mode:** embed · **Current phase:** 5 finalise. **Revert path:** `git revert` the commits on `fix/204-…`, or close the PR unmerged.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** bug.
- Run: `/mango:autorun 204 --no-reviewer`, unattended. `--no-reviewer` waives the rule-book
  reviewer **only**; the ticket-blind challenger keeps its seat. See `DISCLOSURE` in the PR body.
- Contract `.mango/run-contract-204.txt`. RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN
  | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 12 reference(s) checked | 1 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 6 claim(s) surfaced | 1 by symbol | 3 by handle | 2 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

Every in-repo citation is exact at `a502e8f`: the fallback is `resolver.py:175-184`,
`language_of_file` is `store.py:788`, `nodes_by_names` is `store.py:1058-1062`. The **missing**
reference is `205`, which the ticket cites as filed — it is not yet on disk (it is the next ticket in
this run). The **ambiguous** one is the anchor field log, re-derived below.

**Re-derived, and the ticket's headline number is wrong by 1.84×.** P6/P4: the ticket's counts are
`(edge, candidate-node)` **join rows**, not edges. Measured on the field index at
`built_at 2026-09-01T14:26:32Z`, `last_commit 61591c6`:

| the ticket says | what it counted | distinct edges |
|---|---|---|
| 467,919 JS/TS-declared edges with a resolvable target | join rows | **311,427** |
| **342,758** cross-language (73.3 %) | join rows | **186,266** by extension · **186,417** by `files.language` |
| **15.7 %** of the 2.19 M-edge graph | from the join rows | **8.53 %** |

The over-count *is* the defect's own mechanism: `max_candidates` bounds the fan-out per name but
does not filter it, so one `push()` becomes three sibling edges. Every qualitative claim holds
unchanged — 100 % `HEURISTIC`, 0 `RESOLVED`, 100 % `CALLS`, and one fallback produces all of them.
**Two of the ticket's claims are refuted** and are folded in as H2 and H4 below.

**No want-decision.** All four unresolved points are how-decisions the ticket delegates *with* a
requirement to argue them; none is a product decision, so `j` stays 0 and the run does not stop.

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | Scope 3 — is there a cross-language escape? | **None. Not even a configured language pair.** A bare name is not evidence of a boundary crossing, so an escape would be an unexercised path with no real-repo counter-example behind it (R1.2/R7.4). A genuine FFI edge is a new relation with its own evidence | ticket Scope 3 + *Not in scope*; R1.2; R7.4 |
| H2 | Does the predicate belong on **every** cross-language link, or only the bare-name one? | **Only the bare-name one.** The ticket's *"zero cross-language edges are RESOLVED"* is **false**: `tests/fixtures/adapter/fake_adapter.py`'s own `dep/extends_b.cc` EXTENDS `\Dup` declared in a `fake` file and resolves at **RESOLVED**. An exact qualified name matching across a boundary *is* evidence; a bare name is not. The predicate goes on the guess, never on the match | the fixture trace in Phase 2; R5.2 |
| H3 | `contract_version` bump, or a documented "rebuild to benefit"? | **Documented rebuild.** `contract_version` is the adapter↔core JSON contract (R3) and **no adapter can see this change** — the emitted JSON is byte-identical. `SCHEMA_VERSION` would make every existing index refuse to open (`SchemaVersionError`), which is worse than carrying stale edges. The new `cross_language` row **is** the detection: non-zero on an old index says rebuild | R3; `store.py:449-453`; ticket Constraints |
| H4 | Where does an unattributed call site land? | **It keeps the unfiltered candidate set.** `edge_language_census` already models an `unattributed` bucket, so a language-less file is a real state, and it is not *known* to cross a boundary. Dropping those edges would be a second behaviour change hidden inside this one | `store.py:721-723`; R7.1 |

**Recalled claims — advisory.** By handle: `rank-before-truncate` (**R5.8**, 067/126/180),
`count-pin-in-blast-radius` (**P5**, 10 sightings), `the-fixture-can-hide-the-defect-it-was-chosen-for`
(199-C3). By area: `assert-the-consumer-not-the-field` (**R6.9**, 198-C1) and
`an-aggregate-outlives-the-world-that-named-it` (**P7**, 183/195). By symbol:
`fixture-shape-begs-the-question` (**R6.3**) on `nodes_by_names`. Skipped as retired:
`prove-the-guard-fails` (**R6.5** — binding, not advisory).

## Phase 1 — analysis

`PREMISE: 12 reference(s) checked | 1 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 6 claim(s) surfaced | 1 by symbol | 3 by handle | 2 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope, Constraints, Acceptance criteria, Not in scope [+ References]) | 5 decomposed | ROWS: C=4 R=5 G=2 AC=6`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

Both lines above `SECTIONS:` are carried forward from Phase 0.

### BASELINE

`.venv/bin/python -m pytest -q`, run in a clean worktree at **a502e8f** — the pre-change tree, with
the gitignored adapter dependencies symlinked in so nothing skips:

```
2739 passed in 278.52s (0:04:38)
```

Green, and exactly README *Testing*'s bare-`pytest` expectation of 2,739 passed / 0 skipped, so the
DoD stays *all green* and there are no baseline exclusions. Recorded as a reference point, not as
evidence for the tree under review (lesson 201-C1).

### Requirements matrix

| ID | Source | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|
| G1 | Why this exists | a `CALLS` edge must never name a callee in a language that cannot call it | `nodes_by_names` filtered on `kind` alone | closed |
| G2 | Why this exists | the measurement must be repeatable without hand-written SQL next time | no payload carries a cross-language count | closed |
| R1 | Scope 1 | measure first, on the anchor, and keep the query in the PR | done in Phase 0; the query is in the PR body | closed |
| R2 | Scope 2 | the predicate is in the **candidate query**, not a post-filter | R5.8's shape | closed |
| R3 | Scope 3 | decide the escape and write down why | H1 | closed |
| R4 | Scope 4 | `edge_health` can see the class | H2 refined what "the class" is | closed |
| R5 | Scope 5 | a two-language fixture, red before the fix | the red run is in Phase 3 | closed |
| C1 | Constraints | **not a re-tier** — the edge is wrong, not uncertain | no tier constant is touched | closed |
| C2 | Constraints | the count will drop; update any test pinning it, and say so | traced in Phase 2 — **one** pin moved, and it moved *up* | closed |
| C3 | Constraints | index-invalidating: bump or document | H3 | closed |
| C4 | Constraints | the tier-1 chain is at its ceiling | discharged **without** a raise — see below | closed |
| AC1 | AC | a two-language fixture produces no cross-boundary edge, red before | `tests/test_cross_language_bare_name.py` | closed |
| AC2 | AC | 0 such edges on a rebuilt anchor, by scope 1's query | rebuild at `0438186` | closed |
| AC3 | AC | same-language resolution byte-identical | 15 existing resolver tests use one language | closed |
| AC4 | AC | `edge_health` reports a cross-language row, 0 on the rebuilt anchor | measured 0; scope refined, see AC validation | closed |
| AC5 | AC | before/after `find_callers` and `impact` for one named JS symbol | in the PR body | closed |
| AC6 | AC | the scope-3 decision is at the fallback, not only in the ticket | `_link_by_bare_name`'s docstring | closed |

**C4, discharged without a budget raise.** Measured at `a502e8f`: tier-1 chain **25,246** against
`TIER1_BUDGET = 25_300` — 54 tokens of headroom, not the 2 the ticket predicted (203's row was never
taken, because this run reordered to 204 → 205 → 203). This ticket's `BACKLOG.md` row costs 42
tokens: **25,288 / 25,300**, `BACKLOG.md` **8,276 / 8,300**. Both fit, so nothing is pruned and no
number moves. **12 tokens remain**, which 205 and 203 cannot both fit — the raise and its argument
belong to whoever files the next row, exactly as R7.6 intends.

### AC validation

| AC | Ticket's value | Re-derived | Falsifiable? |
|---|---|---|---|
| AC1 | *"produces **no** edge between them"* | the linked-target set for one JS call site | yes — red run recorded |
| AC2 | *"number **0**"* | scope 1's query, re-run against the rebuilt index | yes |
| AC3 | *"byte-identical before and after"* | the whole existing resolver suite is single-language | yes |
| AC4 | *"reads 0"* | measured **0** on the rebuilt anchor, literally, at every tier. Refined, not restated: 0 is this anchor's answer, **not an invariant** — an `EXTENDS` to a qname another language declares resolves at `RESOLVED` and is a legitimate crossing (the repo's own fixture has one). The row reports the boundary; 204 removes only the bare-name guesses across it | yes |
| AC5 | *"which callers disappeared and that none was real"* | `find_callers` on `Array.prototype.push`'s chosen target, before and after | yes |
| AC6 | *"a comment at the fallback"* | the `_link_by_bare_name` docstring | yes, by inspection |

No AC is input-shape-dependent; `config.real_corpus_path` is unset, and the anchor is reached
directly rather than through it.

### Clarifications — all four self-resolved

1. **Is a bare `.push()` in TypeScript even reaching this fallback, or is it an adapter gap?**
   Reaching it. 186,417 of 186,417 have a `target_raw` with no `::` — a bare name — and the TS
   adapter reports `capabilities.semantic_types = true`, so what it *could* type it already typed.
   *Cited:* the Phase 0 query; the anchor's `.code-atlas.toml` adapter note.
2. **Do the 206 chain-shaped php→ts edges (`\Builder::buildChartPdf()::setContent`) also go through
   this fallback?** Yes. `_resolve_subtypes`' `unmatched()` returns every broken chain into
   `by_name`, so a chain whose receiver type the graph does not hold ends up as a bare-name lookup
   for its last member. That is why AC2/AC4 can reach 0 rather than 206.
   *Cited:* `resolver.py` `_resolve_subtypes` docstring and `unmatched()`.
3. **Does grouping `by_name` per language cost a query per language?** Yes — one
   `nodes_by_names` call per distinct call-site language, so 3 on the anchor instead of 1. The map it
   groups by is one whole-run `SELECT path, language FROM files` beside the alias and hierarchy maps
   `resolve_edges` already builds. *Cited:* `resolver.py:104-110`.
4. **Does the join in `_nodes_batched` change the `qualified_name` path at all?** No. The join and
   the predicate are both conditional on `language`, and `nodes_by_qualified_names` never passes it;
   the columns are switched to `nodes.`-qualified spellings, which is a no-op rewrite. Proven by the
   whole existing suite, which never sets `language`. *Cited:* `store.py` `_nodes_batched`.

### Blast radius

`nodes_by_names` has **two** callers: `nodes_by_name` (the singular wrapper) and the resolver
fallback. `_nodes_batched` has **three**: those two plus `nodes_by_qualified_names`. The
`cross_language` row rides `edge_language_census`, whose stamp has **two** consumers —
`get_index_status` (verbose) and `find_orphans` (standard) — and both receive it by carrying the
stamped dict verbatim, so neither needs an edit (R1.8).

**`count-pin-in-blast-radius` (P5), traced.** Grepping the suite for an asserted total on a
multi-language fixture found **one**: `test_edge_health_per_language.py`'s
`total_by_tier(computed)["HEURISTIC"] == 2`. It is **unaffected** — the fixture's crossing edges are
FQN-resolved, not bare-name (H2). The pin this change actually moves is the **new**
`cross_language.linked`, which goes 1 → 2 against my first draft of the assertion, because the
`RESOLVED` `EXTENDS` crossing is real and I had not counted it. Recorded as the finding it is.

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) ✅ · §2 (change-type) ✅ · §3 (change-type) ✅ · §4 (change-type) ✅ · §5 (change-type) ✅ · §6 (change-type) ✅ · §7 (change-type) ✅ · §8 (change-type) N/A (no dependency is added or moved)`

- **§1** — R1.1: the predicate compares *the call site's language to the candidate's*; it never
  names a language, so no branch keys on which one it is. R1.4: the resolver asks, `store.py` joins.
  R1.7: `cross_language` is a **sibling key** inside the census, not a widening of a coercing reader.
  R1.8: one `_tier_block` fold for every bucket, including the new one.
- **§2** — checked, not N/A: `php`, `typescript` and `second`/`fake` appear only in *tests* and in
  the anchor's own config; the core and the adapters gain no language token.
- **§3** — checked: `contract.py` is untouched and no adapter can observe the change (H3).
- **§4** — R4.2: `pairs` is emitted in sorted key order and the census stamp is `sort_keys=True`.
- **§5** — R5.2 (the tier still grades the target; nothing is re-tiered), R5.6 (a pre-204 stamp
  reports **no** row rather than a 0 it never measured), R5.8 (the predicate rides the truncating
  statement).
- **§6** — R6.2/R6.3 (the fixture is the repo's spec-driven `fake`/`second` adapter, never a real
  language name), R6.5 (both red runs recorded in Phase 3), R6.9 (the census row is asserted on the
  `get_index_status` **payload**, not only on the store method).
- **§7** — R7.1 (the unattributed case keeps today's behaviour rather than widening scope), R7.2,
  R7.3 (two commits, one logical change each), R7.5 (every new comment ≤ 3 lines), R7.6 (C4).

No section is `PROVISIONAL`.

## Phase 2 — design

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Approach

**Join the language the schema already had, inside the statement that truncates.**

1. `store.file_languages()` — one whole-run `path → language` map, built beside `alias_targets()`
   and `hierarchy_parents()` in `resolve_edges`. The two existing maps set the shape; a per-edge
   `language_of_file` call would be one round per edge.
2. `nodes_by_names(..., language=...)` carries the predicate into `_nodes_batched`, which adds
   `JOIN files ON files.path = nodes.file_path` and `AND files.language = ?` **only** when a
   language is given. `max_candidates` then selects from the legal set (R5.8) instead of being spent
   on rows a post-filter would throw away — which is what makes one `regex.test()` stop fanning out
   to four PHP classes.
3. `_link_by_bare_name(...)` extracts the fallback, groups `by_name` by the call site's language and
   makes one call per group. The scope-3 decision lives in its docstring (AC6).
4. `store._cross_language_edges()` adds the `cross_language` block to the census, in the same
   `_tier_block` shape as every other bucket plus a `pairs` map naming the boundary.

### Rejected alternatives

| # | Alternative | Why rejected |
|---|---|---|
| A1 | Post-filter the candidates the existing query returns | `max_candidates` is 10 on the anchor. Ten PHP `push` methods would be selected and then all discarded, leaving the same call unlinked as if no same-language method existed — the defect inverted. R5.8 exists for exactly this |
| A2 | Re-tier the false edges to `DYNAMIC` | The ticket's C1, and R5.2: `DYNAMIC` means *unlinkable*, so this would keep 186,417 false edges and relabel them. The edge is wrong, not uncertain |
| A3 | Drop the whole bare-name fallback | It is the only thing linking a same-language dynamic receiver, and 046/137 exist because that link is wanted. The bug is the missing predicate, not the fallback |
| A4 | A `configured_language_pairs` escape, off by default | H1: no real-repo counter-example, so it ships as an unexercised path (R7.4). A repo that genuinely needs FFI edges needs a relation with evidence, not a widened guess |
| A5 | Bump `contract_version` to force a rebuild | H3: the adapters emit byte-identical JSON, so the contract did not change. Overloading it would make it mean "resolver semantics moved too" and re-version every adapter's conformance suite for a change no adapter can see |
| A6 | Filter the new census query to `CALLS`/`HEURISTIC` so it runs faster | It would be blind to the next producer of a cross-language link — and it is that producer, not this one, that the row exists to catch. Measured cost of the general form: 3.2 s on 2.19 M edges |

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| A-1 | `files.language` is populated for every indexed file on the anchor | **verified** — `php 19155 · sql 2980 · typescript 2434`, summing to the 24,569 in `files` |
| A-2 | the join adds no ambiguity: no `nodes` column name collides with a `files` one | **verified** — `files` is `path, hash, language, parsed_ok, updated_at`; `contract.NODE_FIELDS` shares none, and the spellings are `nodes.`-qualified regardless |
| A-3 | the new census query is affordable on the build path | **measured** — 3.2 s on the 2.19 M-edge anchor, against a 91-minute full build and a 63.8 s three-file incremental |
| A-4 | no third-party or runtime behaviour is assumed | **verified** — stdlib `sqlite3` only |

### Smallest change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `file_languages()` | `code_atlas/store.py` | one caller, the resolver | R2 | 1/1 |
| 2 | `language=` on `nodes_by_names` / `_nodes_batched` | `code_atlas/store.py` | 3 callers, traced above | R2, AC3 | 1/1 |
| 3 | `_link_by_bare_name` + the scope-3 decision | `code_atlas/resolver.py` | the fallback only | R2, R3, AC1, AC6 | 2/2 |
| 4 | `_cross_language_edges()` + the census key | `code_atlas/store.py` | 2 stamp consumers, neither edited | R4, AC4 | 1/1 |
| 5 | the two-language fixture and AC1/AC3 | `tests/test_cross_language_bare_name.py` (new) | none | AC1, AC3, R5 | 3/3 |
| 6 | the census row asserted at the consumer | `tests/test_edge_health_per_language.py` | the one moved pin, traced above | AC4, R4 | 3/3 |
| 7 | status, frontmatter, ledger row | `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, this file | `tests/test_backlog_bookkeeping.py` | R7.2, C4 | 1/1 |

Nothing under `docs/CONVENTION.md` or `docs/PLAN.md` moves: no vocabulary, no tool, no decision the
plan records. `docs/TOOLS.md` is untouched — the `cross_language` row rides an existing field.

### Recalled handles — traced

**`rank-before-truncate` (R5.8).** `sed -n '/_nodes_batched/,/return grouped/p' code_atlas/store.py`,
run at a502e8f — the pre-change tree:

```
  FROM nodes WHERE {key_column} IN ({placeholders}){kind_sql}
") WHERE rn <= ? "
```

The `ROW_NUMBER()` window and the `rn <= ?` cut are already in one statement; the predicate joins
them rather than sitting above them. Folded in as **A1 rejected**.

**`count-pin-in-blast-radius` (P5).** `grep -rn "HEURISTIC.*== [0-9]" tests/`, run at a502e8f:

```
tests/test_edge_health_per_language.py:136:    assert total_by_tier(computed)["HEURISTIC"] == 2
```

One pin on a multi-language fixture, and H2 explains why it does not move: that fixture's crossings
are FQN matches, not bare-name guesses. The pin that *did* move is the new one I wrote — recorded
above rather than quietly corrected.

**`the-fixture-can-hide-the-defect-it-was-chosen-for` (199-C3).** The two-language fixture carries a
**same-language** `push` declaration (`src/queue.ts`) beside the two PHP ones. Without it, a green
run could mean *"the predicate works"* or *"nothing was linkable at all"* — and the second reading
would have passed a fallback that had simply been deleted.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | logic | integration — `resolve_edges` over a seeded two-language store | authored | ✅ |
| AC2 | integration | the anchor rebuilt at `0438186`, scope 1's query re-run | **real corpus** | ✅ |
| AC3 | integration | the whole existing suite, plus the same-language control in the new file | existing | ✅ |
| AC4 | integration | the `get_index_status` **verbose payload** (R6.9), plus the anchor's own row | authored + real corpus | ✅ |
| AC5 | integration | `find_callers` / `impact` before and after, one named JS symbol | real corpus | ✅ |
| AC6 | logic | inspection — the docstring at the fallback | n/a | ✅ |

No ❌, so no exclusion is recorded and the counted line closes with zeros.

### Proving test

**`tests/test_cross_language_bare_name.py::test_a_bare_name_call_never_links_across_a_language_boundary**
— red before the change, where the fallback links `\LoggerNDC::push` and
`\PHPExcel_Token_Stack::push`, the ticket's own top-two targets.

```
.venv/bin/python -m pytest tests/test_cross_language_bare_name.py -q
```

### Rollback + porting

`git revert` the two commits. The change is subtractive on the resolver (fewer edges) and additive on
the census, so a revert restores the old graph on the next rebuild and nothing on disk is
orphaned. One repo, no porting order.

`SCOPE: M` — unchanged.

## Phase 3 — execute

Two commits, one logical change each: `589b8cc` the predicate, `f90cef8` the census row. Ran at
f90cef8 unless stated.

### Axis 1 — file set

`git diff --stat a502e8f <code-final>` — a property of two named commits, reproducible from any
tree, so it is recorded as a reference point rather than as tree-under-review output (201-C1). The
commits after this point are docs-only:

```
 git diff --stat a502e8f f90cef8
 code_atlas/resolver.py                 |  48 +++++++++++---
 code_atlas/store.py                    |  74 +++++++++++++++++++--
 tests/test_cross_language_bare_name.py | 113 +++++++++++++++++++++++++++++++++
 tests/test_edge_health_per_language.py |  55 ++++++++++++++
 4 files changed, 273 insertions(+), 17 deletions(-)
```

Four files against seven approved rows — rows 1–4 are all `code_atlas/store.py` and
`code_atlas/resolver.py`; row 7 is the docs commit below. **diff ⊆ approved list**, nothing extra.

### Axis 2 — the red runs (R6.5)

**AC1.** `git stash push code_atlas/resolver.py code_atlas/store.py`, then
`pytest tests/test_cross_language_bare_name.py -q`. Deliberately the **pre-change** tree a502e8f —
a red run is not evidence about the tree under review, so it is recorded as a reference point and
not as an empirical-output block (201-C1):

```
E         At index 0 diff: '\LoggerNDC::push' != 'queue.ts::Queue::push'
E         Left contains 2 more items, first extra item: '\PHPExcel_Token_Stack::push'
E       AssertionError: assert 3 == 1
FAILED test_a_bare_name_call_never_links_across_a_language_boundary
FAILED test_the_same_language_bare_name_link_still_happens
2 failed, 1 passed in 0.67s
```

The pre-fix resolver picks the ticket's own top-two targets, and the one call fans
out to **3** edges — the sibling multiplication that makes 186,417 edges read as 342,758 join rows.

**AC4.** `_cross_language_edges` and its census key removed,
`pytest tests/test_edge_health_per_language.py -q -k "cross_language or measures or pre_204"` —
again the pre-change tree, recorded the same way:

```
E           KeyError: 'cross_language'
3 failed, 1 passed, 8 deselected in 0.81s
```

### Axis 3 — the suite on the tree under review

Ran at f90cef8.

```
$ .venv/bin/python -m pytest -q
FAILED tests/test_backlog_bookkeeping.py::test_the_guard_has_something_to_check
FAILED tests/test_backlog_bookkeeping.py::test_a_finished_task_records_what_it_cost[204]
2 failed, 2745 passed in 298.10s (0:04:58)
```

2,745 = the baseline's 2,739 plus this ticket's 6. Both failures are the R7.2
bookkeeping pair for a `done` task whose `TOKEN_LEDGER.md` row cannot exist until its PR has a
number. With the row added, **CI on PR #250 is 2,747 passed / 0 failed / 0 skipped on both py3.12
and py3.13** — the two bookkeeping tests included — plus the tokens-to-answer gate at ratio 0.835,
recall 1.0, precision 1.0, `confidently_wrong` 0. CI is the authoritative run here: a concurrent
session was filing tickets 205-208 into this repo's shared working tree during the run, so no local
full-suite run after that point sees only this branch, and CI does.

### Axis 4 — the anchor, rebuilt

**Provenance.** The rebuild ran against a worktree at `0438186`. `git diff 0438186 f90cef8 --
code_atlas/` is **empty** — the two differ only in one test docstring and an import order — so this
evidence is the tree under review's `code_atlas/` bytes exactly. Fresh DB at
`scratchpad/anchor204/graph.db`; the field index was **not** touched, so the before-state survives as
evidence. `last_commit 61591c6` on both, so the corpus is identical.

```
                                   BEFORE (field, 2026-09-01)     AFTER (0438186)
nodes                                            262,899               262,899
edges                                          2,188,026             2,077,473   −110,553
linked                                         1,399,944             1,263,405   −136,539
by_tier RESOLVED                               1,052,737             1,052,748        +11
by_tier HEURISTIC                              1,118,754             1,008,190   −110,564
by_tier DYNAMIC                                   16,535                16,535          0
AC2  ticket's scope-1 query (join rows)          342,758                     0
     cross-language distinct edges              186,726                     0
AC4  edge_health.cross_language          absent (pre-204)   linked 0, pairs {}
```

Ran at 0438186. **`DYNAMIC` is unmoved** — C1 held, nothing was re-tiered. **`RESOLVED` went *up* by
11**: removing the foreign candidates left some names with a single legal hit, which 046 links at
`RESOLVED` rather than as a multi-match guess. PHP-declared edges moved by −285 `HEURISTIC` / +11
`RESOLVED`, which is exactly the 103 bare-name php→ts links and their siblings — the only PHP-side
movement, and it is the fix, not a regression.

**AC5**, `\PHPExcel_Token_Stack::push` — one declaration, so the subject is unambiguous:

```
BEFORE  find_callers total_count=5083   callers by language={'php': 27, 'typescript': 5056}
        impact  results=500  truncated=True   frontier_skipped_non_resolved=1818
AFTER   find_callers total_count=27     callers by language={'php': 27}
        impact  results=8    truncated=False  frontier_skipped_non_resolved=3
```

Ran at 0438186. **All 5,056 callers that disappeared are TypeScript**, and a `.js`/`.ts` file cannot
call a PHP class method — none of them was real. The 27 PHP callers are untouched. `impact` is the
sharper result: it was **budget-cut at 500 nodes by false edges** and now answers *completely* with
8. A truncated wrong answer became a complete right one.

### Design conformance

Every row of the change list landed as designed; no deviation to record. The one thing the design
did not predict is the `RESOLVED +11` above — a strict improvement, recorded rather than folded in.

## Phase 4 — review

`--no-reviewer` waived the rule-book reviewer, so **no rule-book-grounded review of this diff
exists**. The ticket-blind challenger kept its seat and its verdict is below.

### Scope reconciliation

diff ⊆ approved list (Axis 1). No file outside rows 1–7. `docs/PLAN.md`, `docs/CONVENTION.md`,
`docs/TOOLS.md` and `contract.py` are untouched, as designed.

### Proving test

`tests/test_cross_language_bare_name.py::test_a_bare_name_call_never_links_across_a_language_boundary`
— red at a502e8f (Axis 2), green at f90cef8 (Axis 3).

**Ph3/4 proven by:** Axis 2's two red runs · Axis 3's 2,745-pass suite · Axis 4's anchor pair.

### Challenger — ticket-blind, LGTM

Dispatched twice. **The first run destroyed its own blindness** and said so: it ran an unrestricted
`git diff a502e8f..HEAD -- . ':!code_atlas' ':!tests'`, which printed this file — `work_doc_mode:
embed` puts the working doc *inside the ticket*, so any diff wide enough to include `docs/` hands the
reviewer the author's reasoning. It self-disclosed rather than reporting a compromised verdict, and
was stopped. That is `embed-mode-leaks-the-working-doc-into-the-diff`, seen again, and it is a
**type-3 signal**: an embed-mode challenger brief should path-restrict every git command by
construction, not by the orchestrator remembering to say so.

The second run was briefed to restrict every git command to `code_atlas/` and `tests/`, confirmed its
independence held, and returned **LGTM — 11 met · 6 can't tell · 0 not met**. It did not take the red
run on trust: it copied the new test files into its own `git worktree` at `a502e8f` and reproduced
**5 failed / 10 passed** there against 15/15 green at HEAD.

All 6 *can't tell* are evidence the ticket itself locates outside the diff — Scope 1, AC5 and the
index-invalidation decision live in the PR body; AC2 and AC4's anchor zero need the rebuild. None is
a gap in the code.

**Two findings folded in, neither blocking:**

1. **A theoretical double-count in `_cross_language_edges`.** The join is
   `edges.target_qname = nodes.qualified_name`, and `nodes` is only `UNIQUE(qualified_name,
   file_path)`. Two files of *different* languages declaring the same literal qname would put one
   edge in two `(src, tgt)` buckets and double it in the total. Structurally near-impossible under
   the shipped qname formats — `\Ns\Class::method` (PHP), `file.ts::Class::method` (TS),
   `dbo.Foo` (T-SQL) cannot collide — but it was undocumented, and now is.
2. **AC3 is met by the suite, not by the literal fixture the ticket describes.** There is no
   dedicated PHP-only fixture asserting a byte-identical tier histogram. What proves it is stronger
   and already existed: **every** resolver test in `tests/test_resolver.py` seeds one language, and
   all of them pass unchanged, inside a CI run that is 2,747 green. Structurally, when every
   candidate shares the call site's language the predicate excludes nothing. Recorded as a deviation
   from the AC's wording rather than closed by writing a redundant test (R7.1).

The challenger also re-derived the `language = ''` fallback as a deliberate, tested hole and asked
that it be flagged loudly: **an adapter that ships without populating `files.language` gets none of
this fix.** That is in the PR notes.

## Phase 5 — finalise

`CLAIMS: 3 claim(s) from 1 lesson entr(ies) | T1=0 T2=3 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`FALSIFY: 3 candidate(s) checked | 3 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/SKILL_GAP_CANDIDATES.md | mango files written: 0`
`LEDGER TOTAL: 1 dispatch, 92,920 tokens (challenger, 45 tool-uses) · top cost driver: main loop (unmeasured — the host surfaces no usage block)`

### Claims

- **204-C1** — *a count quoted from a join is not a count of the joined rows.* The ticket's
  342,758 / 15.7 % are `(edge, candidate-node)` pairs; the edges are 186,417 / 8.53 %. Re-deriving a
  cited number before building on it is what caught it. type: 2 · handle:
  `re-derive-the-cited-count-before-you-build-on-it` · seen: 204 · recurrence 1.
- **204-C2** — *`work_doc_mode: embed` leaks the working doc into any diff wide enough to include
  `docs/`, so a ticket-blind reviewer's brief must path-restrict every git command by construction.*
  type: 2 · handle: `embed-mode-leaks-the-working-doc-into-the-diff` · **seen: 204 + prior — recurrence 2.**
- **204-C3** — *a shared working tree is not a controlled tree.* A concurrent session filed tickets
  205-208 and edited both budget tests mid-run, and the checkout directory was renamed under a
  running process. Every verification after that point moved to an isolated `git worktree`, and CI
  became the authoritative suite run. type: 2 · handle: `verify-in-a-tree-only-you-are-writing-to` ·
  seen: 204 · recurrence 1.

**204-C2 reaches recurrence 2** and is routed to `docs/SKILL_GAP_CANDIDATES.md` as a **type-3**
signal: it is mango's challenger brief that should carry the path restriction, and **this repo never
edits a skill**. Proposed, not ratified.

### Outward actions

| # | Action | Authorisation | State |
|---|---|---|---|
| 1 | push `fix/204-…` | handover, explicit | **done** |
| 2 | open PR #250 | handover, explicit | **done** |
| 3 | merge #250 | the user's separate, explicit *"you have my approval to merge if PR is ready"* — **not** an autorun action; autorun never merges | done outside the skill |
| 4 | tracker transition | none | **deferred** — no tracker beyond the PR |
