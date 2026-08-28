---
id: 186
slug: a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language
title: 'A zero answer still cannot say "this relation is not modelled for this file''s language" — 160 recorded the carve-out, and a second language turned it into a confident false negative'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [160, 183, 185]
---

## Why this exists

160 shipped the language-coverage note and **wrote its own limit down**
(`tests/test_zero_answer_coverage.py` docstring):

> *"The note names what the index does not cover, **never the subject's own language** (160 out of
> scope)."*

On a single-language index that carve-out costs nothing. On a two-language index it produces a
**confident false negative**:

`include_graph(path="…/thing.ts", direction="imported_by")` returns `reason: "no_matches"` — a
genuine zero, meaning *"nothing imports this file"*. The truth is *"TypeScript does not use
`include`; this relation is `IMPORTS` here, and this tool does not read it."*

The mechanism is visible at `include_graph.py:76`: the honest arm
(`relationship_not_modelled`) fires only when `count_unlinked_includes_mentioning(...) > 0` — it needs
**unlinked `INCLUDES` edges as evidence**. The TS adapter emits no `INCLUDES` at all, not even
unlinked, so the evidence is zero and the tool falls through to the confident zero. **The better the
adapter, the more confident the wrong answer** — that is the inversion worth fixing.

This is 102's class (*absent subject ≠ modelled zero*) applied to a **relation kind** instead of a
subject, and it is the one honesty gap that only appears once the product stops being single-language.

## Why the obvious fix is forbidden, and what replaces it

The obvious fix — *"if the file's language is typescript, `include_graph` does not apply"* — is a
language branch in the core and **R1.1 forbids it, CI-gated.** That is presumably why 160 carved it
out rather than solving it.

**But the honest answer is a data question, not a language condition.** *"Has this edge kind ever
been emitted for this file's language in this index?"* is a join — `edges ⋈ files.language` — and the
core may ask it without knowing what any language is. **183 builds exactly that table**, which is why
this ticket depends on it rather than duplicating the query.

## Scope

1. A nav answer that is empty **because the relation kind has no presence for the subject file's
   language in this index** says so, distinctly from a genuine zero and distinctly from
   `relationship_not_modelled`'s existing unlinked-evidence meaning. Design fixes the reason code and
   states whether it extends `NavReason` or reuses one (R3: nav vocabulary vs contract vocabulary).
2. The verdict is derived from **index data**, never from a language name in the core (R1.1). Design
   records the source — 183's per-build per-language stamp, or a bounded query — and why the other
   was rejected.
3. It reaches the tools where the gap is provable today: `include_graph`, `find_references`. Design
   records whether every nav tool needs it or only the vocabulary-gated ones, and why.
4. `try_instead` is honest where an equivalent exists: for `include_graph` on a language whose
   dependency edge is `IMPORTS`, the route is `find_references` — a hint that names a **callable
   tool** (the 093 rule), not a language.

### Explicitly not in scope

- Teaching `include_graph` to read `IMPORTS`. Merging two relation kinds into one tool is a contract
  and naming decision (069's territory), not a honesty fix, and it must not be smuggled in here.
- Making any adapter emit more vocabulary.
- The declared-state matrix — [185](185_no-tool-is-ever-asked-a-question-over-a-second-languages-graph.md)
  owns that, and this ticket is what makes 185's `empty_relation_not_modelled` state observable in a
  payload rather than only in a test.
- `not_applicable_by_language` as a *language* fact (TS has no traits). The index cannot know that; it
  can only report absence. Design must state this limit rather than blur it — an absent relation and an
  impossible relation are different claims, and only the first is derivable here.

## Constraints

- **R1.1** — no `if language == …` under `code_atlas/`. The verdict comes from rows.
- **R5.6 / 102** — an index that cannot support the claim says nothing rather than guessing. A
  pre-183 index must not silently report "not modelled" for everything.
- **061** — a single-language index is byte-identical to today, and so is every confident non-empty
  answer (160 AC3 already pins the second half).
- **R5.2** — the reason must be sourced from the computation, not inferred from an empty list.
- **Cost** — the verdict is a meta/stamp read on the answer path, never a `GROUP BY` per call (183's
  constraint, inherited).
- **R6.7** — one definition site shared with 185's state vocabulary if both need it.

## Acceptance criteria

1. `include_graph(imported_by)` on a file whose language emits no `INCLUDES` returns the new reason,
   **not** `no_matches` — pinned, and failing on today's code.
2. The same call on a PHP file with genuinely no inbound includes still returns `no_matches` — the
   two are not collapsed, pinned.
3. `relationship_not_modelled`'s existing unlinked-evidence arm is unchanged, pinned (160/065).
4. A single-language index and every confident non-empty answer are byte-identical (061), pinned.
5. An index built before the per-language stamp existed says nothing rather than guessing (R5.6),
   pinned.
6. `try_instead` names a callable tool, verified by the existing `test_try_instead_is_a_callable_tool_name`
   guard.
7. No language branch under `code_atlas/` — R1.1 grep-gate green.

## References

`tests/test_zero_answer_coverage.py` docstring (160's recorded carve-out, quoted above);
`code_atlas/tools/include_graph.py:28,76` (`_INCLUDE`, the unlinked-evidence arm);
`code_atlas/store.py:1062` (`count_unlinked_includes_mentioning` — the evidence a second language
never produces); `code_atlas/contract.py:78` (`UNMODELLED_REFERENCE_KINDS`);
`code_atlas/tools/nav_result.py:26,45,87` (the reason vocabulary and the `try_instead` routes).
Verified 2026-08-28: the TS adapter's sources contain no `INCLUDES` literal. Related:
[160](160_a-zero-answer-never-names-the-index-language-coverage.md) (the carve-out's owner),
[183](183_edge-health-has-no-per-language-breakdown.md) (the per-language data this needs),
[185](185_no-tool-is-ever-asked-a-question-over-a-second-languages-graph.md) (the matrix that would
have caught this).

## Session status

- **KEY:** 186 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended batch) · envelope in `.mango/run-contract-186.txt`.
- **Branch:** `feat/186-zero-answer-names-the-unmodelled-relation` (stacked on `feat/185-…`)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2355 passed, 0 failed` at `11c354f` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

Three how-decisions, each delegated by name and each answerable from the index's own shape:

1. Scope 1 — *"Design fixes the reason code and states whether it extends `NavReason` or reuses one
   (R3)."* → *Approach*.
2. Scope 2 — *"Design records the source — 183's per-build per-language stamp, or a bounded query —
   and why the other was rejected."* → *Approach* / *Rejected alternatives*. **183's stamp turned out
   not to carry the needed fact**; see the premise correction.
3. Scope 3 — *"whether every nav tool needs it or only the vocabulary-gated ones, and why."* →
   *Approach*.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 6 reference(s) checked | 0 missing | 2 ambiguous (surfaced; both corrected by measurement)`
`RECALL: 3 claim(s) surfaced | 1 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=6 R=4 G=1 AC=7`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 11 applicable — 8 by change-type | 3 by recalled handle — §R1.1 (change-type) ✅ · §R1.8 (recalled handle) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.2 (change-type) ✅ · §R5.4 (change-type) ✅ — clause (c) drove the route decision · §R5.6 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.7 (change-type) ✅ · §R7.2 (change-type) ✅`
`BASELINE: green — 2355 passed, 0 failed, 0 skipped at 11c354f (bare pytest, Linux host)`

**Premise 1 — the defect is real and was reproduced before any code changed.** On a TS fixture graph,
`src/models.ts` is imported by `src/app.ts` and `src/barrel.ts`, and
`include_graph('src/models.ts', 'imported_by')` returned **`no_matches`** — the confident false
negative, exactly as the ticket describes. The mechanism is as described too:
`count_unlinked_includes_mentioning` needs unlinked `INCLUDES`, and TS emits none, so the honest arm
cannot fire.

**Premise 2 is wrong: *"183 builds exactly that table"* — it does not.** 183's stamp is keyed by
`(language, confidence_tier)`; the question here is about **edge kind**. Verified by reading the
stamp:

```
edge_health_by_language -> {"by_language": {"typescript": {"by_tier": {...}, "linked": …}}}
                                                            ^ tiers, not kinds
```

So this ticket has to produce the fact, not just read it. It does so by **extending 183's single
statement** rather than adding a second scan (below).

**Premise 3 is wrong: Scope 3's second tool has no gap to fix.** 185 measured `find_references`
**answering** on TS, and the reason is precise: it reads `UNMODELLED_REFERENCE_KINDS =
("REFERENCES", "IMPORTS")`, and TS emits `IMPORTS`. So a TS `find_references` zero is a **real** zero.
The rule is still wired into it — see *Approach* — but it correctly does not fire, and that is pinned.

**Recall:** `one-rule-for-every-subject-slot` (R1.8, by handle — one verdict, both consumers).
`prove-the-guard-fails` (R6.5, by handle). `REASON_RELATIONSHIP_NOT_MODELLED` (by symbol — the arm
this must not disturb).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | 160's carve-out became a confident false negative on two languages | name the cause | reproduced | open |
| R1 | Scope 1 | an empty answer says the relation is unmodelled for the subject's language, distinctly from a genuine zero and from `relationship_not_modelled` | a new `NavReason` | `nav_result.py:20-37` | open |
| R2 | Scope 2 | derived from index data, never a language name (R1.1); record the source and the rejected one | a per-language emitted-kind stamp | 183's stamp is tier-keyed | open |
| R3 | Scope 3 | reaches `include_graph` and `find_references`; record whether every nav tool needs it | both, via one helper; only the vocabulary-gated ones | `_INCLUDE`, `UNMODELLED_REFERENCE_KINDS` | open |
| R4 | Scope 4 | `try_instead` is honest where an equivalent exists; a route names a callable tool (093) | **no route** — measured, none exists | see AC6 | open |
| AC1 | AC 1 | `include_graph(imported_by)` on such a file returns the new reason, not `no_matches` — failing today | Falsifiable: red run 1 | proving test | open |
| AC2 | AC 2 | the same call on a PHP file with no inbound includes still returns `no_matches` | Falsifiable: both asserted | proving test | open |
| AC3 | AC 3 | `relationship_not_modelled`'s unlinked-evidence arm unchanged | Falsifiable: precedence test + red run 2 | proving test | open |
| AC4 | AC 4 | a single-language index and every confident non-empty answer are byte-identical | Falsifiable: omitted `reason` asserted | proving test | open |
| AC5 | AC 5 | a pre-stamp index says nothing (R5.6) | Falsifiable: stamp deleted; plus two more holes | proving test ×2 | open |
| AC6 | AC 6 | `try_instead` names a callable tool | Falsifiable: **no route emitted**, and the would-be route measured empty | proving test | open |
| AC7 | AC 7 | no language branch under `code_atlas/` | Falsifiable: grep-gate | `gate.sh` | open |
| C1 | Constraint | R1.1 — the verdict comes from rows | a stamp read | — | binding |
| C2 | Constraint | R5.6/102 — an index that cannot support the claim says nothing | `None` ⇒ silent | — | binding |
| C3 | Constraint | 061 — single-language and confident answers byte-identical | empty answers only | — | binding |
| C4 | Constraint | R5.2 — the reason is sourced from the computation, not inferred from an empty list | the verdict decides, not the emptiness | — | binding |
| C5 | Constraint | cost — a meta read per answer, never a `GROUP BY` | stamped per build | — | binding |
| C6 | Constraint | R6.7 — one definition site, shared with 185's vocabulary if both need it | one helper; 185 imports the reason string | — | binding |

### Root cause (taxonomy: data / signal design)

Two honest mechanisms were both written for one language and each covers a case the other cannot. The
`relationship_not_modelled` arm keys on **evidence that the relation exists but is unlinked** — which
requires the adapter to emit the kind at all. A second adapter that emits the kind *never* produces
that evidence, so the arm is structurally unreachable for it, and the fall-through is a confident
zero. **The stronger the adapter, the more confident the wrong answer** — because "no unlinked rows"
reads as "nothing to report" instead of "nothing was ever recorded here".

### Blast radius

- `store.py`: 183's census query gains `edges.kind` in its `GROUP BY` and returns a second fact; one
  new meta key; one reader; one derived predicate; one `language_of_file` lookup.
- `indexer.py`: one extra `set_meta` from the census already being computed — **no second scan**.
- `nav_result.py`: one `NavReason`, one hint constant.
- `coverage.py`: one shared helper — the module that already owns "what this index does not cover".
- `include_graph.py` / `find_references.py`: one `elif` each, both after the existing arm.
- `tests/contract/tool_parity.py`: 185's `empty_relation_not_modelled` cell now declares the payload
  reason, and the matrix checks it — the loop between the two tickets closes.
- Three vocabulary pins grow by one member (167's precedent, expected).

## Phase 2 — design

### Approach

**One statement, two facts.** 183's `edge_health_by_language` already pays a full scan of `edges`
joined to `files`. Adding `edges.kind` to its `GROUP BY` yields the emitted-kind sets for free, so the
query became `edge_language_census() -> LanguageEdgeCensus(health, kinds)` and 183's public method is
now a one-line view over it (R1.8: one query definition, two consumers). `_record_meta` stamps both
keys from the one census. **A second scan would have doubled 183's measured ~1.0 s/build to ~2.0 s.**

**The verdict is a data question.** `language_emits_none_of(language, kinds)` answers *"has this
language emitted **any** of these kinds in this index?"* — `True` when none, `False` when any, and
`None` when the index cannot say. `relation_unmodelled_for_language(store, file_path, kinds)` wraps it
with the file→language lookup and collapses every unknown to `False`, because silence is not evidence
(R5.6). **No language name appears anywhere in the core**; the grep-gate is unmoved.

**`ANY`, not `ALL` — and that precision is the design.** The verdict fires only when the language
emits **none** of the kinds the tool reads. A rule that fired on a *partly* modelled relation would
replace one false claim with another: TS emits `IMPORTS` but not `REFERENCES`, so a TS
`find_references` zero is a real zero and must keep saying so. Pinned by
`test_find_references_does_not_fire_while_one_kind_is_modelled`.

**A new `NavReason`, appended: `relation_unmodelled_for_language`.** Not a reuse. `capability_not_configured`
means *a config switch is off* — flip it and every language answers. `relationship_not_modelled`
means *the relation exists here and is unlinked* — a strictly stronger claim than this one can make.
Nav vocabulary, not contract: **no `contract_version` bump** (167's precedent for exactly this shape).

**The new arm is an `elif` after the existing one, in both tools.** So every path that used to reach
`relationship_not_modelled` still does, and the new reason only occupies ground that used to be a
confident `no_matches`. AC3 is then structural rather than careful — and red run 2 proves the
precedence matters on the one shape where both could fire.

**Scope 3's answer: only the vocabulary-gated tools.** `include_graph` and `find_references` are the
two that read a *fixed kind set* and go empty when it is absent. A tool keyed on nodes
(`search_symbol`, `file_outline`, `read_symbol`) has no relation to be unmodelled; `impact` /
`reachable_from` walk `IMPACT_KINDS`, whose members every adapter emits, so the verdict could never
fire and adding it would be a dead branch (R7.4). Recorded rather than done.

### AC6 / Scope 4 verdict — hint, and NO route. Measured, not assumed.

Scope 4 says *"for `include_graph` on a language whose dependency edge is `IMPORTS`, the route is
`find_references`."* **Measured, `find_references` cannot answer:**

```
find_references('src/models.ts') -> reason='relationship_not_modelled' total=0 rows=0
find_references('src/service.ts') -> reason='relationship_not_modelled' total=0 rows=0
```

Cause: TS `IMPORTS` edges carry a **resolved repo path** in `target_raw` and `target_qname is None` —
the resolver's path-linking branch covers `INCLUDES` only (`resolver.py:115`), and `FQN_EDGE_KINDS`
excludes `IMPORTS`. So **no registered tool can enumerate the importers of a TS file today.** R5.4
clause (c) is explicit about that case: *"Where no registered tool can, emit the hint and no route:
naming a tool that cannot answer is worse than naming none."* So the payload carries
`try_instead_hint` and deliberately no `try_instead`, matching the shape 093 already established for
this tool's other arm. **The route becomes correct the moment `IMPORTS` is linked — filed as 188**,
whose Scope 4 is *"186's hint-and-no-route is revisited"*. The test asserts the would-be route is
empty, so the day it answers, the test fails and the decision is revisited rather than forgotten.

### Rejected alternatives

- **A bounded query per answer** instead of a stamp. Rejected on the constraint inherited from 183:
  `include_graph` is a per-answer path and the query is a full `edges` scan (measured ~1.0 s at
  2.1 M rows). A stamp read is one statement with no `GROUP BY`, asserted by a trace.
- **Reuse `relationship_not_modelled`.** Rejected: it is a stronger claim (*the relation exists
  here*) and the whole point is that this index has no evidence either way. Collapsing them would
  make 065's distinction unrecoverable.
- **Reuse `capability_not_configured`.** Rejected: it means a switch is off, and no switch fixes this.
- **A branch on the language name.** R1.1, CI-gated, and presumably why 160 carved this out.
- **Report `not_applicable_by_language`** (the language *cannot* have this relation). Explicitly out
  of scope, and correctly: an index can observe **absence**, never **impossibility**. TS having no
  traits is a language fact no row proves. The ticket asked for this limit to be stated rather than
  blurred, and the reason code says *unmodelled*, not *impossible*.
- **A second scan for the kind stamp.** Rejected on 183's measured number; the census gives both.

### Assumptions

| Assumption | Tag |
|---|---|
| 183's stamp already carries per-language edge kinds | **falsified by reading it** — it is tier-keyed; hence the census extension |
| `find_references` is the honest route for a TS file | **falsified by measurement** — it returns zero rows; hint and no route |
| `find_references` has a gap to fix on TS | **falsified** (185's measurement) — it answers, because `IMPORTS` is modelled |
| A language with files but no edges is distinguishable from an unmeasured one | **initially false, and fixed** — the census now seeds every indexed language with an empty kind set; red run 3 pins it |
| The verdict rides empty answers only | verified — both call sites are inside an already-empty branch, and AC4 asserts an omitted `reason` on a confident answer |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `edge_language_census` (one statement, two facts); `EMITTED_KINDS_BY_LANGUAGE_KEY`; reader; `language_emits_none_of`; `language_of_file`; 183's method as a view | `code_atlas/store.py` | one query definition | R2, AC5 | 1/1 |
| Stamp the second key from the census already computed | `code_atlas/indexer.py` | no second scan | R2 | 1/1 |
| `REASON_RELATION_UNMODELLED_FOR_LANGUAGE` + its hint | `code_atlas/tools/nav_result.py` | one vocabulary member | R1 | 1/1 |
| `relation_unmodelled_for_language` — one definition site | `code_atlas/tools/coverage.py` | shared by both tools | R3, C6 | 1/1 |
| One `elif` after the existing arm, in each tool | `include_graph.py`, `find_references.py` | additive | R1, R3, AC1–AC3 | 1/1 |
| 185's matrix declares + checks the payload reason for this state | `tests/contract/tool_parity.py`, `test_tool_parity.py` | closes 185↔186 | R1 | 1/1 |
| Proving tests (11) + three vocabulary pins | `tests/test_relation_unmodelled_for_language.py` (new), 3 existing | new file | AC1–AC7 | 1/1 |
| A new ticket for the unlinked `IMPORTS` | `docs/tasks/188_*.md`, BACKLOG | new row | — | 1/1 |
| BACKLOG; ledger; LESSONS; working doc | `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `one-rule-for-every-subject-slot` (R1.8) — **traced.** One helper, two consumers, asserted:

  ```
  $ grep -rl 'def relation_unmodelled_for_language' code_atlas/
  code_atlas/tools/coverage.py
  $ grep -rl 'relation_unmodelled_for_language(' code_atlas/tools/
  code_atlas/tools/coverage.py  code_atlas/tools/find_references.py  code_atlas/tools/include_graph.py
  ```

- `prove-the-guard-fails` (R6.5) — **traced.** Three red runs below.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (real TS build; the importers asserted to exist first) | integration test + red run 1 | ✅ |
| AC2 | integration (real PHP build) | integration test | ✅ |
| AC3 | integration (a seeded cross-language shape where both arms could fire) + red run 2 | integration test | ✅ |
| AC4 | integration (a confident answer's `reason` is absent) | integration test | ✅ |
| AC5 | integration (stamp deleted; unindexed file; unnamed language) | integration test ×2 | ✅ |
| AC6 | measurement (the would-be route returns zero rows) + payload assertion | integration test | ✅ |
| AC7 | guard (grep-gates) + logic (vocabulary membership) | `gate.sh` + integration test | ✅ |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **The verdict reports absence, never impossibility — and that gap is permanent, not deferred.** An
  index can say *"this language has emitted no `INCLUDES` here"*; it can never say *"this language
  cannot have `INCLUDES`"*. So a language that simply has none of a construct **in this repo** gets
  the same answer as one where the construct does not exist. **Expiry:** none — this is a stated limit
  of the evidence, recorded because the ticket asked for it to be stated rather than blurred. The
  distinction lives in 185's declared matrix (`not_applicable_by_language`), where a human asserts it.

### Proving test

`tests/test_relation_unmodelled_for_language.py::test_the_false_negative_is_reproduced_then_named`

### Rollback + porting

Rollback: revert five source files, delete the new test file, revert three pins and 185's cell. The
meta key becomes an orphan row a pre-186 reader ignores; no rebuild needed. Porting: `app` only.

### SCOPE

`SCOPE: M` — one derived fact, one reason, two `elif`s; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| One statement, two facts; 183's method becomes a view (R1.8) | implemented-as-approved |
| The verdict is a stamp read; no language name in the core | implemented-as-approved |
| `ANY` semantics — fires only when the language emits none of the kinds | implemented-as-approved |
| A new appended `NavReason`; no contract bump | implemented-as-approved |
| `elif` after the existing arm in both tools | implemented-as-approved |
| Only the vocabulary-gated tools; the rest recorded, not wired | implemented-as-approved |
| Hint and no route, on the measurement | implemented-as-approved |

**One addition beyond the approved list, recorded as such:** the census seeds `kinds` with **every**
indexed language, so a language with files and zero edges answers `True` ("emitted none") rather than
`None` ("never measured"). Found while writing AC3 — the seeded fixture's second language had no
edges, and the verdict went silent on the very case it exists for. One line; red run 3 pins it.

### Empirical outputs

**The false negative, reproduced before any code changed:**

```
IMPORTS rows: ('src/app.ts',       'src/models.ts', target_qname=None, RESOLVED)
              ('src/barrel.ts',    'src/models.ts', target_qname=None, RESOLVED)
include_graph('src/models.ts', imported_by) -> reason='no_matches'   n=0     # two files DO import it
```

**After:**

```
include_graph('src/models.ts',  imported_by) -> reason='relation_unmodelled_for_language'  n=0
include_graph('src/service.ts', imported_by) -> reason='relation_unmodelled_for_language'  n=0
```

**The predicate, on real graphs:**

```
emitted kinds: {'typescript': ['ALIASES','CALLS','CONTAINS','EXTENDS','IMPLEMENTS','IMPORTS','NEW']}
language_emits_none_of('typescript', ('INCLUDES',))              -> True
language_emits_none_of('typescript', ('REFERENCES','IMPORTS'))   -> False   # so find_references stays honest
language_emits_none_of('typescript', ('REFERENCES',))            -> True
language_emits_none_of('php',        ('INCLUDES',))              -> False
```

**Three red runs (R6.5):**

```
1. the language arm removed from include_graph  (i.e. the pre-186 code)
   E  assert 'no_matches' == 'relation_unmodelled_for_language'
   E  typescript:include_graph must be empty for the reason it declares, and the payload must say
      so itself — a bare empty cannot tell the causes apart; got 'no_matches'      4 failed, 102 passed
2. the language arm placed BEFORE the unlinked-evidence arm (precedence inverted)
   E  unlinked evidence outranks the language verdict — the relationship really does exist
                                                                                  1 failed, 10 passed
3. the census NOT seeded with every indexed language
   E  assert None is True        # a zero-edge language reads as "never measured"  1 failed, 10 passed
```

**Red run 1 fails 185's parity matrix too** — the cell that declares `relation_unmodelled_for_language`
is exactly the one 186 makes true, so the two tickets check each other.

**The mechanism generalised to a third "language" nobody designed it for.**
`test_ensure_qname_miss_then_symbol_indexed` began reporting the new reason for the **fixture**
adapter, which emits only `CONTAINS`. That is correct — an empty `find_references` on a `fake` file
genuinely is unmeasured — so the assertion set was widened with the reason written down, not silenced.

**Cost:** the answer path is one statement with no `GROUP BY` (trace-asserted) and 100 empty inbound
answers run under a 25 ms/call budget. The build path gains **nothing**: the second stamp comes from
183's existing scan.

**Green run:**

```
$ .venv/bin/pytest -q
2368 passed in 130.08s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_the_false_negative_is_reproduced_then_named` — asserts the importers exist **first**, so the test cannot pass on an empty fixture; red run 1 |
| AC2 | `test_a_genuine_php_zero_is_still_no_matches` |
| AC3 | `test_unlinked_evidence_still_wins_over_the_language_verdict` — a seeded cross-language shape where a PHP-like file `include`s a TS-like file, so both arms could fire; red run 2 |
| AC4 | `test_a_confident_answer_is_byte_identical` — an **omitted** `reason` is the confident shape |
| AC5 | `test_a_pre_186_index_says_nothing_rather_than_guessing` + `test_an_unindexed_file_and_an_unknown_language_say_nothing` |
| AC6 | `test_no_route_is_emitted_because_no_tool_can_answer` — and it asserts the would-be route is empty, so the day 188 lands, this test fails and the decision is revisited |
| AC7 | `test_the_new_reason_joins_the_vocabulary_once`; `gate.sh` R1.1/R2.2 green; no `contract.py` edit ⇒ **no bump (R3), confirmed** |
| — | `test_find_references_does_not_fire_while_one_kind_is_modelled` — the `ANY` boundary; `test_the_verdict_is_a_stamp_read_not_a_group_by` — the cost; `test_one_rule_two_consumers` — R1.8 |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2355 passed / 0 failed` at `11c354f` →
`2368 passed / 0 failed`. ruff + mypy green. `scripts/gate.sh` → `GATE GREEN`.

### Learning loop

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen >= 2 | 0 routed to a destination | 0 cannot promote (reason) | 2 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `one-rule-for-every-subject-slot` (R1.8) gains 186: one verdict helper, two consumers.
- `prove-the-guard-fails` (R6.5) gains 186: three red runs, and run 2 is the one that proves the
  precedence between two honest arms.
- **New:** `186-C1` (type-2, `evidence-shaped-honesty-inverts-on-a-second-instance`) — an honest arm
  that keys on *evidence the thing exists but is unlinked* is structurally unreachable for a producer
  that never emits the vocabulary at all, so the fall-through is a confident zero **and the better
  producer gets the worse answer.** When adding instance #2 of any producer, ask of every
  evidence-keyed caveat: can this producer generate the evidence? seen=1.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. Self-checks: the defect
reproduced before any code changed, **three of the ticket's premises falsified by measurement** (183's
stamp shape, `find_references`' gap, and the suggested route), an R5.4(c) route decision taken on a
measurement and wired so it fails when it stops being true, three red runs, a self-caused silence
found and fixed, and a follow-up (188) filed with the evidence attached.
