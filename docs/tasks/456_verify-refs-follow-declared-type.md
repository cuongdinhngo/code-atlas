---
id: 456
slug: verify-refs-follow-declared-type
title: "verify_refs follows a dotted chain through a field's or property's declared type"
phase: 2
milestone: "Field gaps — Python/TS consumer"
status: done
depends_on: [443]
---

## Why this exists

A field report from a second consumer repo (the Python/TS consumer: Python + TypeScript, 406 files; full
`--format jsonl` export on 2026-11-27, 1,610 rows, 73 actionable). Of the 73 actionable rows, 70 are
`gone` / `missing_on_live_container`, and none of them is real. The largest group that is
clearly a bug: the doc names `a.b.c`, `a.b` resolves to a **field or property**, and `c` is a member
of that field's **declared type**. `_member` only looks at the field itself and its ancestors, so the
row comes out `gone`.

| Doc ref | Container matched | Declared type | Member that exists |
|---|---|---|---|
| `Timeline.theme.vars` | `ir.Timeline::theme` | `Theme` | `Theme.vars` (`studio/core/ir.py:348`) |
| `diagram.nodes`, `diagram.modes` | `ir.Article::diagram` | `Diagram \| None` | `Diagram.nodes`, `Diagram.modes` (`ir.py:147,149`) |
| `caption_style.y` | `recipes.Recipe::caption_style` | `CaptionStyle` | `CaptionStyle.y` (`studio/core/recipes.py:69`) |
| `ctx.cancelled` | `pipeline.Pipeline::ctx` (a `@property`) | returns `StepContext` | `StepContext.cancelled` (`core/ports.py:39`) |
| `error.message` | `api.errors.ErrorResponse::error` | `ErrorBody` | `ErrorBody.message` (`api/errors.py:29`) |

Each one is a false `gone` on a doc that is true. A user who trusts `actionable` edits correct docs,
and a user who sees the noise stops trusting the tool.

## Scope

1. When the container is a field or attribute with a declared type annotation, or a property or
   method with a return annotation, resolve the next segment on that type. Read the type from
   `store.declared_types` (the adapter's `extra.type`) and reuse the resolver's chain walk
   (`resolver.py`, the `declared` / `documented` loop). Do not build a second walk. The core never
   parses `X | None` or `Optional[X]` (R1.1). If an adapter leaves a union unnormalised, fix that
   adapter.
2. Follow every segment the same way (`a.b.c.d`), and stop at the first one with no type.
3. If the type resolves and declares the member → `ok` (reason `via_declared_type`, with the site).
   If the type resolves but does not declare it → apply the current `_member` rules to that type.
   If there is no type, or it is not indexed (`dict`, `Any`, an external class) → `unknown`
   (`untyped_container`), never `gone`.
4. Language-free where the adapters emit a type. Python and TypeScript fields and properties are
   enough for the fixture. Say which adapters emit nothing.

## Acceptance

1. Fixtures (`tests/test_verify_refs_declared_type.py`): field → class → member `ok`; `X | None`
   `ok`; property return type `ok`; a member missing on the declared type keeps today's verdicts;
   a `dict`-typed field → `unknown`, not actionable.
2. Re-run the Python/TS consumer's export (or a scratch copy). The five refs above (8 rows) are no longer
   actionable. Report the actionable count before and after.
3. The anchor's instruction `gone` count does not rise. Report it.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Last updated:** 2026-11-27
- **Current phase:** finalise
- **Next action:** the maintainer merges #189, then this PR; 457 runs next, stacked on this branch
- **Blocked on:** nothing
- **KEY:** 456 · **work_doc_mode:** embed · `TRACK: backend` · Run mode: `autorun 456 - 457 - 458 - 459 - 460 - 461 - 462`,
  first — `REVIEWER: ON` · `CHALLENGER: ON` · `cost_tier: standard`. The handover delegates decisions, so a
  want-decision is `ASSUMED`, never silent.
- Branch `feat/456-verify-refs-follow-declared-type` from `docs/451-progress-note` tip `8f14cd50` (#189), in a worktree.
  Contract `.mango/run-contract-456.txt`; RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 2 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 4 want-decision asked | 8 how-decision resolved+cited | 4 ASSUMED | skip: no`

`_member` (`doc_refs.py:613`), `store.declared_types` (`store.py:3221`), the resolver's `declared` / `documented` loop
(`resolver.py:562`) and `extra.type` resolve; `tests/test_verify_refs_declared_type.py` is to be created. Ambiguous:
the consumer's `file:line` sites live in another repo — read there, all five containers exist. Recalled: 438-C1
`area:verify_refs`, 450-C1 `inheritance-walk-needs-the-languages-precedence` (handles), 398-C1 (area: worktrees).
The exposure-checker ran before any code and returned 7 (H6–H8, W1–W4).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the type comes from | how | `declared_types` as the resolver reads it (`_declared_class` over the ancestry, `resolver.py:685`), then the member's resolved `REFERENCES` edges when they reach exactly one `TYPE_KINDS` node — every adapter emits those from an annotation (task 232: `parse.py:743-790`, `parse.js:454-461`, `Visitor.php:1092`). Python and TS `extra.type` is source spelling (`Diagram \| None`), which the core may not parse (R1.1); no adapter or contract change |
| H2 | depth | how | every segment, stop at the first with no type (ticket Scope 2) |
| H3 | no type | how | `unknown` (`untyped_container`), never `gone` (Scope 3) |
| H4 | member absent on the type | how | today's `_member` rules on that type (Scope 3) |
| H5 | which containers | how | a value or callable node (`Property`, `ClassConst`, `Const`, `Function`, `Method`); a class, table or namespace keeps today's walk (Scope 1 names fields, properties and methods) |
| H6 | two class types (`A \| B`) | how | `unknown` with reason `several_container_types` — R5.6: the reader acts differently than on an absent type |
| H7 | new reasons | how | reasons live in `doc_refs.py`, not `contract.py`, so they are not contract vocabulary (R3.2) |
| H8 | strength | how | unchanged: `strength()` keys on kind and origin only (`doc_refs.py:859`) |
| W1 | the five refs' target | want | **ASSUMED:** `ok` (`via_declared_type`), not merely `unknown` |
| W2 | the before/after counts | want | **ASSUMED:** reported, not a floor; AC3 compares the anchor before and after on one index copy |
| W3 | adapters that emit no type | want | **ASSUMED:** reported, not fixed here — H1 needs no adapter change |
| W4 | `list[Foo]` | want | **ASSUMED:** followed to `Foo` (the adapters strip containers before the edge); a known false `ok` only when the element type declares the member |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=0 R=4 G=1 AC=3`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/6 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "Each one is a false `gone` on a doc that is true" | a typed container's member resolves on its type | ✅ |
| R1 | Scope 1 | "resolve the next segment on that type … Do not build a second walk" | H1, H5 | ✅ |
| R2 | Scope 2 | "Follow every segment the same way (`a.b.c.d`)" | H2 | ✅ |
| R3 | Scope 3 | "`ok` (reason `via_declared_type`, with the site) … `unknown` (`untyped_container`), never `gone`" | H3, H4, H6 | ✅ |
| R4 | Scope 4 | "Say which adapters emit nothing" | PHP, Python, TS emit the edges; SQL emits no type — the PR says so | ✅ |
| AC1 | Acc 1 | "field → class → member `ok`; `X \| None` `ok`; property return type `ok`; … `dict` → `unknown`" | five fixture rows | ✅ |
| AC2 | Acc 2 | "The five refs above (8 rows) are no longer actionable" | computed: the docs now hold **9** rows of those five refs (one more `Timeline.theme.vars` copy); all 9 | ✅ |
| AC3 | Acc 3 | "The anchor's instruction `gone` count does not rise" | before/after on one index copy | ✅ |

**Gap.** `Resolver.symbol` matches the container `Timeline.theme` to the property `Timeline::theme`, and `_member`
(`doc_refs.py:613`) walks only that property's own ancestry, so `vars` is looked for on a property and git finds it
nowhere in `ir.py`'s history under that name — `gone`.

`BASELINE: green — verify_refs, query CLI, language-agnostic, untrusted-output, contract-schema, doc-budget and bookkeeping suites: 803 passed`

Ran at 8f14cd50 (pre-change)
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q -p no:cacheprovider $(cat .mango/baseline-456.list)
803 passed in 31.90s
```

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 no language branch: the walk reads node kinds and edges, R1.4 the new query lives in store.py · §2 (change-type) ✅ R2.2 the core names no repo or framework · §3 (change-type) ✅ R3.1/R3.2 the new kind subset is named in contract.py, no vocabulary moves · §4 (change-type) ✅ R4.2 the type candidates are sorted, so one answer per index · §5 (change-type) ✅ R5.6 untyped and two-typed containers are unknown, never gone or ok · §6 (change-type) ✅ R6.1 a fixture over a built index, R6.5 seen failing on the base · §7 (change-type) ✅ R7.2 ledger rows, R7.5 comments ≤ 3 lines, R7.6 the docs line replaces what it supersedes · §9 (change-type) ✅ R9.1 the new row fields are listed as untrusted`

## Phase 2 — design

`HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- `inheritance-walk-needs-the-languages-precedence` — traced: the member is looked for on the type's ancestry through
  `Resolver._ancestry`, which is `resolver.ancestry` over `hierarchy_parents` (kind order, never edge order).

  Ran at 8f14cd50 (pre-change)
  ```
  $ grep -n "def ancestry" -A3 code_atlas/resolver.py; grep -n "ORDER BY source_qname, kind" code_atlas/store.py
  717:def ancestry(container: str, parents: Mapping[str, tuple[str, ...]]) -> list[str]:
  718:    """``container`` then its ancestors, breadth-first in ``hierarchy_parents`` order.
  3256:            "ORDER BY source_qname, kind, target_raw, file_path, line, id",
  ```
- `area:verify_refs` — does not apply because the new lookup is one indexed edge seek per container
  (`idx_edges_src`), cached per run, not a scan of git history per reference.

**Approach.** (1) `contract.VALUE_KINDS` names `Property`, `ClassConst`, `Const`. (2) `store.referenced_types(qname)`:
the distinct `TYPE_KINDS` targets of a node's resolved `REFERENCES` edges. (3) `doc_refs.Resolver._type_of(owner)`:
`declared_types` read through `_declared_class` over the owner's container ancestry, else the one referenced type;
`None` when absent, a marker when several. (4) `_member` first: an owner of a value or callable kind is replaced by its
type — no type → `unknown untyped_container`, several → `unknown several_container_types`, the member declared on the
type or its ancestors → `ok via_declared_type` with the site and the type; otherwise today's rules on the type node.
(5) `symbol()` resolves a container no qname names (`a.b.c`) segment by segment through the same step, so `a.b.c.d`
works and stops at the first untyped segment. **Rejected:** normalise each adapter's `extra.type` (ticket's Scope 1
fallback) — a contract field change, a v22 bump and a forced rebuild for a fact the graph already holds as edges;
parse the type text in the core — R1.1. **Assumptions:** every adapter emits a member's annotation as `REFERENCES`
from that member — `verified` on the consumer's index for all five containers (one `Class` target each) and by the
fixture build through the real adapters.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| kind subset | `code_atlas/contract.py` | none identified (a named subset, no vocabulary) | R1 |
| edge query | `code_atlas/store.py` | `test_sql_confinement.py` (SQL stays in store) | R1 |
| the walk | `code_atlas/doc_refs.py` | `test_verify_refs*.py` (property containers today read `gone`), `query --verify-refs`, the stored session summary | R1–R3 |
| proving test | `tests/test_verify_refs_declared_type.py` | — | AC1 · 5/5 |
| docs | `docs/TOOLS.md` (verify_refs reasons), `CHANGELOG.md` | `test_doc_size_budget.py` | R4, R7.6 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration (a built index through the real Python and TS adapters) | integration: fixture repo built and scanned | authored | ✅ |
| AC2 | e2e (the consumer's corpus) | manual-recorded: before/after `--verify-refs --format jsonl` on a backup copy of its index | n/a | ✅ |
| AC3 | e2e (the anchor's corpus) | manual-recorded: the same, instruction class | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `tests/test_verify_refs_declared_type.py` (fails on the base: the four `ok` rows read `gone` or
`unknown not_declared_on_container`). Rollback: revert the commit. Porting: one repo.

## Phase 3 — execute

Main loop, no `implementer` (Cost ledger), in a worktree, at `b7fab515`. **Sweep.** Axis 1: the diff is the approved
list (`contract.py`, `store.py`, `doc_refs.py`, the proving test, `TOOLS.md`, `CHANGELOG.md`); `ruff` and `mypy`
clean. Axis 2: approach (1)–(5) implemented-as-approved, plus one **deviation**: the consumer's first after-run showed
`owners[0]` picks one of several same-named containers blindly — three `channels` members, three element types — so
`_one_owner` takes the union of every typed match's types and answers `several_container_types` when they differ
(H6 applied to the match, not only to one annotation). Fixture row `box.vars`.

Ran at 8f14cd50 (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_verify_refs_declared_type.py   # base + the new test only
12 failed in 2.56s
```


## Phase 4 — review

`REVIEWER: ON` · `CHALLENGER: ON`. Review step: `reviewer` (Sonnet; `cost_tier: standard`, no high-stakes path), then
the ticket-blind `challenger` on the raw ticket (`git show 8f14cd50:<this file>`) + the branch diff.

- **Reviewer round 1** at `b7fab515` (68,015 tokens): CHANGES REQUESTED, conditional LGTM on 1–3. **Taken**
  (`a8daab22`): (1) a method's `REFERENCES` also name its parameters' and decorators' types, so they answer for a
  callable only when it declares a return and takes no parameter — not the reviewer's "callables read `declared_types`
  only", which loses the consumer's `@property` `ctx` (`extra.type` `StepContext` is source spelling); (2) fixture
  rows `Timeline.build.vars` (a parameter type), `Timeline.make.nodes` (return + parameter), `Timeline.made.f` (a class
  decorator), seen failing on `b7fab515`; (3) `resolver.declared_class` is public; (4)–(5) plain statements, no
  `assert`. **Recorded:** (6) `_one_owner` checks types only when the first match is typed — a class first keeps
  today's walk. The "declared type wins" order cannot be exhibited on Python or TS fixtures: their `extra.type` is
  source spelling and never a qname; only PHP's is.
- **Reviewer round 2** (verify-only, main loop, at `a8daab22`): the three named fixes present as described; only the
  affected proof re-run.

The three new rows were seen red on the superseded round-1 tree `b7fab515` (its code, this test file):
`3 failed, 12 passed` — `Timeline.build.vars`, `Timeline.make.nodes`, `Timeline.made.f`.

Ran at a8daab22
```
$ env -u CA_… PYTHONPATH=$PWD .venv/bin/python -m pytest -q $(cat .mango/baseline-456.list) tests/test_sql_confinement.py tests/test_release_discipline.py tests/test_verify_refs_declared_type.py
869 passed in 32.98s
```

**AC2 — the consumer**, base code and this branch run back to back on one backup copy of its index (its HEAD
`503eeda`; the index is behind it, so both runs read the same stale facts):

Ran at a8daab22
```
before (8f14cd50): 1936 rows, 77 actionable
after  (a8daab22): 1942 rows, 14 actionable — the five refs' 9 rows ok via_declared_type, none actionable
newly actionable: occlusion.json ×2, storyboard.json — file names read as `member.suffix`, 458's class
```

**AC3 — the anchor**, base code and this branch on one backup copy of its index:

Ran at a8daab22
```
before (8f14cd50): 92728 rows, 357 actionable — instruction gone 28, moved 0
after  (a8daab22): 92881 rows, 306 actionable — instruction gone 16, moved 0
newly actionable: 1 reference row, `unknown history_unanswered` → `gone removed` (the git budget between runs)
```

- **Challenger round 1** at `a8daab22` (68,116 tokens): 11 rebuilt · 10 met · AC3 can't tell (the anchor still
  running). Finding A (three `x.json` rows newly `gone`) is the recorded delta, 458's class. Scope notes
  (`several_container_types`, `VALUE_KINDS`, `referenced_types`, `_one_owner`, the callable rule) — accepted: each
  serves R5.6 and is tested.
- **Challenger round 2** (resumed, AC3 only, 1,400 tokens): the anchor numbers re-derived from the raw exports.

`CHALLENGER VERDICT: 11 requirement(s) rebuilt | 11 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

Reviewed at a8daab22 — files: `code_atlas/contract.py`, `code_atlas/store.py`, `code_atlas/doc_refs.py`,
`code_atlas/resolver.py`, `tests/test_verify_refs_declared_type.py`, `docs/TOOLS.md`, `CHANGELOG.md`; working doc
`docs/tasks/456_verify-refs-follow-declared-type.md`.

`Ph3/4 proven by`: R1–R3, AC1 → `tests/test_verify_refs_declared_type.py` (15); R4 → the CHANGELOG line; AC2, AC3 →
the corpus blocks above. Deviation: `resolver.py` joined the change list for finding 3 (a rename, no behaviour).

## Phase 5 — finalise

Stale-review guard: only bookkeeping after `a8daab22` — not stale.

**Durable lessons.** 456-C1 `diff-every-row-not-the-target-rows` (type 2, first sighting) and a second sighting of
411-C1 `a-baseline-needs-a-frozen-tree` (the consumer's HEAD moved between the first before and after runs, which
read as a phantom regression until both ran back to back), both in `docs/LESSONS.md`.

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/AGENT_BRIEF.md | mango files written: 0`

Falsify: still true — this run's consumer pair (75 vs 77 actionable on the same code) differed only by the time
between runs. Proposed for `AGENT_BRIEF.md`: a before/after pair runs back to back on one frozen copy. Unratified, so
written nowhere; `/mango:promote` is the cross-ticket pass.

### Outward actions

Under the handover: push `feat/456-verify-refs-follow-declared-type`; open its PR against `docs/451-progress-note`
(#189, stacked). Deferred to the maintainer: ratify W1–W4 and the AGENT_BRIEF proposal; merge after #189.
Revert: revert the branch's commits.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 49,642 |
| 3 execute | `implementer` — not dispatched (main loop implemented) | — | unmeasured (main-loop spend, not a dispatch) |
| 4 review | rule-book `reviewer` | 1 | 68,015 |
| 4 review | ticket-blind `challenger` | 1 | 68,116 |
| 4 review | ticket-blind `challenger` | 2 | 1,400 (resumed: 69,516 cumulative − 68,116) |

`LEDGER TOTAL: 187,173 · top cost driver: 4 review / challenger` — main loop unmeasured.
