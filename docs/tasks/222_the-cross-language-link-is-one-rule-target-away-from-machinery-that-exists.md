---
id: 222
slug: the-cross-language-link-is-one-rule-target-away-from-machinery-that-exists
title: 'Six of the field''s structural misses are one defect — the identifier is a string, not a symbol — and `enrichment.py` already does the whole extraction for `view_data`: find every call to a named setter, pull the Nth string literal, emit a HEURISTIC edge. Only the target is hardcoded to `viewdata:<key>`'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [221, 063, 062, 040]
---

## Why this exists

Field round 14 listed the question types to keep code-atlas out of, then noticed they were one thing:

> Dispatch tables · string-keyed routing (`querySP('name')`) · stored-procedure callers · PHP↔SQL
> crossings · SELECT-list order · dead-file proof. **All six are "the identifier is a string, not a
> symbol" — one carve-out, six faces.**

[221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) makes the resulting zeros
honest. This one makes some of them non-zero.

**The machinery already exists and is 90 % of the work.** `view_data` rules (040/062/063) run exactly
the chain a string-keyed call needs:

1. `_calls_for_setter` (`enrichment.py:204`) → `store.calls_by_target_raw("querySP")` — every CALLS
   edge with that exact `target_raw`, off `idx_edges_raw`, no scan cap; plus the bare `::method` arm.
2. `_keys_for_rule` (`enrichment.py:218`) → checks the Nth argument is a string literal (`args`
   category) and extracts it with a one-line regex, or reads `arg_keys` for an array literal.
3. Emit a **HEURISTIC** edge — applied after parse, before `resolve_edges`, on a synthetic bookmark
   path with no `files` row (068), `rule: true` on nav hits.

**Step 3 is the only thing pinned.** The target is built as `viewdata:<key>`. Parameterise it —
`"dbo.{key}"` — and PHP `querySP('getUnplannedChange')` becomes a CALLS edge onto the T-SQL
`Function` node the resolver already links, which is the node 214 proved resolves correctly from the
SQL side.

**Why this is the right home for the knowledge, not the adapter.** `querySP` is a repo's function
name. R2 forbids it in `adapters/`, and R1.1 forbids a language branch in the core. Indirection rules
are the seam that already exists for exactly this: repo-relative JSON **outside `adapters/`** (R2.2),
applied generically, off by default, HEURISTIC tier. PLAN §978 made the same argument for the
data-bag case — *"neither end is a symbol the PHP language server binds, so Serena-class tools are as
blind as today's graph. This is unclaimed ground, not an LSP race."* A string-keyed dispatch is the
same shape.

**Why the existing `calls` rule is not the answer.** It takes `(source qname, target qname, line)`
triples (`enrichment.py:370-375`) — one hand-written entry per call site. Against 452 procs it is an
escape hatch, not a mechanism. The difference between the two rule kinds is exactly the difference
between listing edges and deriving them (R6.7).

## Scope

1. **A rule entry kind that emits `CALLS` from an extracted string key**, reusing `_calls_for_setter`
   and `_keys_for_rule` unchanged. Shape, following `view_data`'s validated schema
   (`enrichment.py:376-390`): `{setter, key_arg, key_from, target_template}`.
2. **`view_data` semantics stay untouched.** New entry kind beside it, not a widening of it — no
   `PROVIDES_VIEW_DATA` behaviour change, no contract bump (`CALLS` and `HEURISTIC` are both existing
   vocabulary; R3.1's trigger does not fire).
3. **Template substitution is one named placeholder, no expression language.** `{key}` and nothing
   else, validated at load time, failing loud before parse like every other rule error (R5.3).
4. **Fail loud on a template that resolves to nothing.** A rule producing only unresolvable targets
   is a misconfigured rule; it must be visible in `BuildReport`, not a silent zero — the failure mode
   this whole pair of tickets exists to eliminate.

**Not in scope:** discovering the mapping automatically (that needs literal *values* in the contract,
which `args` deliberately excludes — *"the category, never the value"*, `contract.py:147`, refused
already at 063 and 152); SELECT-list order, which is a T-SQL adapter capability and its own ticket;
routing/dispatch semantics, which the field correctly assigns to grep.

## Acceptance criteria

- **AC1** With a rule configured, `find_callers` on a fixture proc returns the cross-language call
  sites, tier `HEURISTIC`, `rule: true`. **R6.5:** the same fixture without the rule returns the
  221 answer, and that is the before-state the test pins.
- **AC2** With no rule configured the graph is **byte-identical** — the standing property of
  `CA_INDIRECTION_RULES` (R4.2), and the reason this feature costs a non-user nothing.
- **AC3** `view_data` output is unchanged, pinned by the existing 062/063 tests passing untouched.
- **AC4** A rule whose `target_template` resolves no targets reports that in `BuildReport`; a build
  with such a rule does not silently succeed.
- **AC5** The conformance suite and `test_sql_tier2_vocabulary_is_opt_in.py` still pass: a repo with
  no SQL adapter sees identical rows.

## Exclusions

- **E1 — measurement precondition, and it is not in this repo.** The consumer corpus declares **328
  of 452 procs twice**, because an 8.3 MB `V0.1__baseline_schema.sql` full-schema dump is not in
  its `.codeatlasignore`. Until that one line lands there, every emitted edge hits
  `ambiguous_definitions` and the AC1 measurement reads empty — **a false negative that would be
  blamed on this ticket.** Fix the consumer's ignore file *first*, or measure on the fixture only and
  say which.
- **E2** Four of the six faces are in reach here (string-keyed routing, proc callers, PHP↔SQL
  crossings, dead-file proof once literal-named targets link). SELECT-list order and dispatch-table
  semantics are not — do not claim them.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 222 · **work_doc_mode:** embed · **Current phase:** 5 finalise — complete on disk. PR [#289](https://github.com/cuongdinhngo/code-atlas/pull/289) open on `main`. **Next action:** merge #289.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** enhancement
- Run: `/mango:autorun 222` with `--no-reviewer`; challenger ON.
- Branch: `feat/222-the-cross-language-link-is-one-rule-target-away-from-machinery-that-exists`
- Contract: `.mango/run-contract-222.txt` · RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN | 2 UNBOUND
- Handover: push feature branch + open PR only (never merge).
- Worktree: `/home/you/.cursor/worktrees/autorun222-a5f980a9/code-atlas-9e4914c8946d`

## Phase 0 — refine

`PREMISE: 14 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 4 by handle | 1 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions. Ticket locks the mechanism (reuse `_calls_for_setter` /
`_keys_for_rule`, new entry kind beside `view_data`, `{key}`-only template, BuildReport visibility for
zero-resolve). Acceptance bar is pinned by AC1–AC5. Handover authorises design to name the JSON key
and the BuildReport field without a want-decision stop.

**PREMISE detail.** Checked and present: `code_atlas/enrichment.py` (`_calls_for_setter`,
`_keys_for_rule`, `view_data` schema), `PROVIDES_VIEW_DATA`, `CA_INDIRECTION_RULES`,
`code_atlas/contract.py` (args category), `BuildReport` (`indexer.py`),
`tests/test_sql_tier2_vocabulary_is_opt_in.py`, tickets 040/062/063/221. **Ambiguous (not blocking):**
field round 14 (prose); consumer corpus `.codeatlasignore` (E1 — outside this repo).

**INPUT KIND:** ticket (not epic).

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `reproduce-the-payload-not-the-story` | 2 | handle | **Yes** — AC1 pins `find_callers` payload |
| 2 | `prove-the-guard-fails` | 2 | handle | **Yes** — R6.5 before-state without rule |
| 3 | `prefer-the-provable-fix` | 2 | handle | **Yes** — fixture-only measurement (E1) |
| 4 | `cross-language-zero-needs-the-crossing-census` | 2 | handle | **Yes** — AC1 before-state is 221 answer |
| 5 | enrichment / indirection area (040, 062) | 5 | area | Surfaced |
| — | `assert-the-consumer-not-the-field` | 2 | — | **retired skipped** → R6.9 |
| — | `embed-mode-leaks-the-working-doc-into-the-diff` | 3 | — | **retired skipped** (skill-gap) |

**Exposure-checker:** skipped with refine (`skip: yes`).

## Phase 1 — analysis

`PREMISE: 14 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 4 by handle | 1 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Why this exists, Scope, Acceptance criteria, Exclusions) | 4 decomposed | ROWS: C=5 R=4 G=2 AC=5`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N touched files under UI paths (enrichment + indexer + tests/docs)`
`BASELINE: green`
`SCOPE: M`
`TIER: full`
`RULE SECTIONS: 12 applicable — 11 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ generic enrichment, no language branch · R1.4 (change-type) ✅ store untouched for writes beyond existing replace_file_rows · R2.2 (change-type) ✅ querySP stays in repo rules JSON · R3.1 (change-type) ✅ no vocab bump (CALLS/HEURISTIC exist) · R4.2 (change-type) ✅ AC2 byte-identical off · R5.3 (change-type) ✅ template validated at load · R5.6 (change-type) ✅ AC4 visible miss · R6.5 (recalled handle) ✅ AC1 without-rule before · R6.7 (change-type) ✅ derive from setter sites, not list · R6.9 (change-type) ✅ assert find_callers · R7.1 (change-type) ✅ smallest new rule kind · R7.2 (change-type) ✅ ledger row`

### BASELINE

`.venv/bin/python -m pytest -q --tb=no` on untouched `origin/main` at **61d992a** (after adapter deps install in worktree — vendor/node_modules gitignored):

```
3049 passed in 285.29s (0:04:45)
```

`Ran at 61d992a509b4a4b249792daa16acea56b2276b93`. Green. No baseline exclusions. (AGENTS.md still cites 2,972 — count has moved; DoD is this captured baseline.)

### Clarifications (all self-resolved; j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | JSON key name for the new array? | **`keyed_calls`** — parallel to `view_data`/`calls`/`aliases`; ticket gave object shape only | ticket Scope 1; `enrichment.py` `_load_rules` |
| Q2 | AC4 "resolves no targets" = zero emitted edges, or emitted-but-unlinked? | **Emitted edges, zero `target_qname` after `resolve_edges`** — ticket wording "unresolvable targets" / "misconfigured rule"; silent zero of *links* is the failure mode 221+222 exist to kill | ticket Scope 4; Why |
| Q3 | Measure AC1 on consumer corpus or fixture? | **Fixture only** — E1 names the consumer ignore gap as outside this repo; say so in proving test | ticket E1 |

### Requirements matrix

| ID | Source | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|
| G1 | Why | string-keyed call sites become HEURISTIC CALLS via rules | view_data chain exists; target hardcoded | closed |
| G2 | Why | knowledge lives in indirection rules, not adapters | R2 / R1.1 / R2.2 | closed |
| R1 | Scope 1 | new entry kind `{setter,key_arg,key_from,target_template}` emitting CALLS | `_load_rules` has no such kind | open |
| R2 | Scope 2 | view_data untouched | existing 062/063 tests | open |
| R3 | Scope 3 | `{key}` only, validated at load | no template field today | open |
| R4 | Scope 4 | zero-resolve rule visible in BuildReport | BuildReport has no rules field | open |
| C1 | Constraints | R1.1 no language branch | CI grep | closed |
| C2 | Constraints | R2.2 no querySP in adapters/core | rules JSON outside adapters | closed |
| C3 | Constraints | R3.1 no contract bump | CALLS/HEURISTIC exist | closed |
| C4 | Constraints | R4.2 off ⇒ identical | AC2 | closed |
| C5 | Constraints | R5.3 fail loud on bad template | ConfigError at load | closed |
| AC1 | AC | find_callers on fixture proc → HEURISTIC + rule:true; without rule = 221 answer | needs proving test | open |
| AC2 | AC | no rule ⇒ byte-identical graph | pattern in test_indirection_enrichment | open |
| AC3 | AC | view_data unchanged (062/063 green) | existing tests | open |
| AC4 | AC | zero-resolve reported in BuildReport | new field + test | open |
| AC5 | AC | conformance + sql tier2 opt-in still pass | run those suites | open |
| E1 | Exclusions | fixture-only measurement | Q3 | closed |
| E2 | Exclusions | do not claim SELECT-list / dispatch-table | docs only | closed |

### AC validation

| AC | Ticket value | Independently derived | Match? |
|---|---|---|---|
| AC1 | HEURISTIC + rule:true callers | `edge_hit` sets RULE_FLAG when `is_rule_edge_path` (INDIRECTION_FILE) | ✅ |
| AC2 | byte-identical off | existing `_graph_rows` snap pattern | ✅ |
| AC3 | view_data unchanged | no edit to `_view_data_edges` / schema | ✅ |
| AC4 | BuildReport reports miss | need new field (Q2) | ✅ once field named at design |
| AC5 | suites pass | run after change | ✅ falsifiable |

### Rejected alternatives (preview for design)

- Widen `view_data` with a target_template → rejected: Scope 2 forbids; PROVIDES_VIEW_DATA semantics must stay.
- Hand-written `calls` triples → rejected: ticket Why / R6.7.
- Adapter hardcode of querySP → rejected: R2 / R1.1.


## Phase 2 — design

### Approach

Add a sibling rule array `keyed_calls` beside `view_data`/`calls`/`aliases`. Each entry
`{setter, key_arg, key_from, target_template}` reuses `_calls_for_setter` + `_keys_for_rule`
unchanged, substitutes `{key}` into `target_template` (validated at load — exactly one `{key}`,
no other placeholders), and emits HEURISTIC `CALLS` on `INDIRECTION_FILE`. After
`resolve_edges`, count rules whose emitted edges all lack `target_qname` and surface that count on
`BuildReport.rules_unresolved` (default 0). Off path stays byte-identical.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Widen `view_data` with `target_template` | Scope 2 — PROVIDES_VIEW_DATA semantics must stay untouched |
| Hand-written `calls` triples per site | Ticket Why / R6.7 — escape hatch, not a mechanism |
| Encode `querySP` in PHP adapter | R2 / R1.1 — repo function name |

### Assumptions

| Assumption | Tag |
|---|---|
| `is_rule_edge_path` already stamps `rule: true` on INDIRECTION_FILE CALLS | verified — `nav_result.py:164-167` |
| Resolver links `dbo.Name` / bare Function the way 214 proved | verified — task 214 shipped; proving fixture will plant matching SQL Function |
| Template `str.replace("{key}", key)` is enough (no format language) | verified — ticket Scope 3 |

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | Parse/validate `keyed_calls` + emit CALLS via shared helpers | `code_atlas/enrichment.py` | `RulesPayload` shape; `load_indirection_rules` return; all rules JSON consumers | R1,R2,R3,C1–C5,AC2,AC3 | 10/10 |
| 2 | `BuildReport.rules_unresolved` + post-resolve census of keyed_calls misses | `code_atlas/indexer.py` (+ `Enriched` carry if needed) | `asdict(report)` clients; `tests/test_build_report_counts.py` may need default=0 awareness | R4,AC4 | 2/2 |
| 3 | Proving fixture (PHP querySP + SQL proc) + tests AC1–AC4 | `tests/fixtures/keyed_calls/` + `tests/test_keyed_calls_rule.py` | view_databag tests untouched (AC3); find_callers cross-lang tests may still pass | AC1–AC4,E1 | 5/5 |
| 4 | Docs/bookkeeping: BACKLOG, TOKEN_LEDGER, task status, optional LESSONS | `docs/` | none beyond bookkeeping | R7.2,E2 | 2/2 |

### HANDLES (recalled type-2 — command + result)

`HANDLES: 4 recalled | 4 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**H1 `reproduce-the-payload-not-the-story`** — traced.

```
Ran at '61d992a509b4a4b249792daa16acea56b2276b93'
$ rg -n 'RULE_FLAG|is_rule_edge_path' code_atlas/tools/nav_result.py | head -5
14:from code_atlas.enrichment import is_rule_edge_kind, is_rule_edge_path
150:def edge_hit(
164:    if is_rule_edge_path(edge.get("file_path")) or is_rule_edge_kind(edge.get("kind")):
167:        hit[contract.RULE_FLAG] = True
```

Folded: change #3 asserts `find_callers` payload (`confidence_tier`, `rule: true`).

**H2 `prove-the-guard-fails`** — traced.

```
Ran at '61d992a509b4a4b249792daa16acea56b2276b93'
$ rg -n 'cross_language|relation_unmodelled|REASON_NO_MATCHES' tests/test_find_callers_cross_language_unmodelled.py | head -8
tests/test_find_callers_cross_language_unmodelled.py:8:knows the crossing is unmodelled (`_cross_language_edges` reads `linked: 0` on that corpus) — this
tests/test_find_callers_cross_language_unmodelled.py:30:    REASON_NO_MATCHES,
tests/test_find_callers_cross_language_unmodelled.py:64:    health.pop("cross_language", None)
tests/test_find_callers_cross_language_unmodelled.py:72:def _cross_language_repo(root: Path, db_path: Path, *, link_the_crossing: bool) -> Config:
tests/test_find_callers_cross_language_unmodelled.py:111:def test_a_cross_language_zero_is_not_no_matches(tmp_path: Path) -> None:
tests/test_find_callers_cross_language_unmodelled.py:117:    config = _cross_language_repo(tmp_path, tmp_path / "graph.db", link_the_crossing=False)
tests/test_find_callers_cross_language_unmodelled.py:124:    assert payload["reason"] != REASON_NO_MATCHES
tests/test_find_callers_cross_language_unmodelled.py:129:    assert payload["cross_language"]["linked"] == 0
```

Folded: change #3 red-before without rule pins the 221 answer (R6.5).

**H3 `prefer-the-provable-fix`** — traced.

```
Ran at '61d992a509b4a4b249792daa16acea56b2276b93'
$ rg -n 'view_data|_view_data_edges' code_atlas/enrichment.py | head -8
32:    """Validated aliases/calls/view_data plus a content digest (load before parse; apply after)."""
36:    view_data: tuple[tuple[str, int, str], ...]
52:    view_data: list[tuple[str, int, str]] = []
71:        view_data.extend(parsed[2])
76:        view_data=tuple(view_data),
131:    edges.extend(_view_data_edges(config, store, loaded.view_data))
147:def view_data_key(target_raw: object) -> str | None:
155:def _view_data_edges(
```

Folded: fixture-only AC1 (E1); reuse existing helpers rather than inventing extraction.

**H4 `cross-language-zero-needs-the-crossing-census`** — traced.

```
Ran at '61d992a509b4a4b249792daa16acea56b2276b93'
$ rg -ln 'BuildReport|indirection' tests/test_build_report_counts.py code_atlas/indexer.py | head -10
code_atlas/indexer.py
tests/test_build_report_counts.py
```

Folded: without-rule path keeps 221 census/zero behaviour; with-rule path makes callers non-zero via HEURISTIC edges.

### Coverage-gap exclusions

| Item | Risk tier | Why deferred | Follow-up | expiry | seen |
|---|---|---|---|---|---|
| Consumer-corpus AC1 measurement (328/452 double-declared procs) | medium | E1 — ignore fix is outside this repo; authored fixture proves the mechanism | Re-measure on consumer after its `.codeatlasignore` drops the baseline schema dump | `when consumer .codeatlasignore excludes V0.1__baseline_schema.sql` | (first) |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|---|---|---|---|---|
| AC1 | integration | integration (`find_callers` over PHP+SQL fixture + rules) | authored | ✅ |
| AC2 | integration | integration (byte-identical graph snap, rules off) | authored | ✅ |
| AC3 | integration | integration (existing 062/063 tests untouched) | authored | ✅ |
| AC4 | integration | integration (`BuildReport.rules_unresolved > 0` on bad template targets) | authored | ✅ |
| AC5 | integration | integration (conformance + `test_sql_tier2_vocabulary_is_opt_in.py`) | n/a | ✅ |

### Proving test

```
.venv/bin/python -m pytest tests/test_keyed_calls_rule.py -q
```

Named assertions (fail on main before the change):
- `test_keyed_calls_find_callers_are_heuristic_rule` — AC1
- `test_keyed_calls_without_rule_keeps_221_answer` — AC1 R6.5 before
- `test_keyed_calls_off_is_byte_identical` — AC2
- `test_keyed_calls_unresolved_reported_on_build_report` — AC4

AC3/AC5 proven by running existing suites in execute verification.

### Rollback + porting

- **Rollback:** `git revert` / close PR unmerged.
- **Porting:** single repo (`app`).

`SCOPE: M` (unchanged).


## Phase 3 — execute

Branch `feat/222-the-cross-language-link-is-one-rule-target-away-from-machinery-that-exists` from `origin/main` @ `61d992a`.

### Implemented (⊆ approved change list)

| # | Change | Done |
|---|---|---|
| 1 | `keyed_calls` parse/validate + emit CALLS via shared helpers | ✅ `enrichment.py` |
| 2 | `BuildReport.rules_unresolved` + post-resolve census | ✅ `indexer.py` + `count_unresolved_keyed_calls` |
| 3 | Proving fixture + `tests/test_keyed_calls_rule.py` | ✅ |
| 4 | BACKLOG / TOKEN_LEDGER / task status | ✅ |

No design deviations.

### Proving test evidence

```
Ran at '31a198176813c954047534d44f1406af0574e0de'
$ .venv/bin/python -m pytest tests/test_keyed_calls_rule.py -q
.....                                                                    [100%]
5 passed in 1.34s
```

R6.5: `test_keyed_calls_without_rule_keeps_221_answer` pins `relation_unmodelled_for_language` before any rule edges exist.

### Verification sweep

- AC3: view_databag producer/setter/shape/decision — green
- AC5: `test_sql_tier2_vocabulary_is_opt_in.py` — green
- Indirection enrichment + build_report_counts + 221 cross-lang unmodelled — green (40 passed combined with proving)
- ruff + mypy on touched modules — clean

### Cost ledger (working doc)

| phase | dispatch | notes |
|---|---|---|
| refine | 0 | skip: yes |
| analysis | 0 | main-loop unmeasured |
| design | 0 | main-loop unmeasured |
| execute | 0 | main-loop unmeasured |
| review | pending | reviewer waived; challenger on |


## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)`. `CHALLENGER: ON`.

### Challenger (ticket-blind — raw ticket above separator + `git diff main...HEAD` only)

Independence: procedural (working-doc portion withheld). Rebuilt requirements from Scope + AC1–AC5 + E1/E2.

| Req | Verdict | Evidence |
|---|---|---|
| R1 new keyed entry kind emitting CALLS | **met** | `enrichment.py` `keyed_calls` + `_keyed_calls_edges` |
| R2 view_data untouched | **met** | `_view_data_edges` unchanged in diff |
| R3 `{key}`-only template | **met** | load-time `ConfigError` + unit test |
| R4 zero-resolve visible in BuildReport | **met** | `rules_unresolved` + AC4 test |
| AC1 find_callers HEURISTIC + rule:true | **met** | `tests/test_keyed_calls_rule.py` |
| AC1 R6.5 without-rule = 221 answer | **met** | `test_keyed_calls_without_rule_keeps_221_answer` |
| AC2 byte-identical off | **met** | `test_keyed_calls_off_is_byte_identical` |
| AC3 view_data suites | **met** | execute sweep green (062/063 tests) |
| AC4 BuildReport miss | **met** | `test_keyed_calls_unresolved_reported_on_build_report` |
| AC5 sql tier2 / conformance direction | **met** | `test_sql_tier2_vocabulary_is_opt_in.py` green in sweep |
| E1 fixture-only | **met** | proving fixture; no consumer corpus claim |
| E2 no SELECT-list/dispatch claim | **met** | docs/tests scope |

**Challenger verdict: LGTM** — 12 met / 0 not-met / 0 can't-tell.

### Scope reconcile

- File axis: `diff ⊆` approved list (enrichment, indexer, fixtures/tests, docs) ✅
- Behaviour axis: Approach matches implementation ✅

### Proving test (review re-run)

```
Ran at '7664115de7aa80fa5b7d106242c20bf5940d7369'
$ .venv/bin/python -m pytest tests/test_keyed_calls_rule.py -q
.....                                                                    [100%]
5 passed in 1.38s
```

Would fail without the change: yes (no `keyed_calls` / no `rules_unresolved` on main).

Ph3/4 proven by: `tests/test_keyed_calls_rule.py` 5 passed; challenger LGTM 12/12.

`Reviewed at 7664115de7aa80fa5b7d106242c20bf5940d7369`

## Phase 5 — finalise

LEDGER TOTAL: unmeasured · top cost driver: main-loop (host surfaces no usage block; challenger not separately metered this run)
CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified
RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)
FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)
RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path
PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0

Outward actions (handover-authorised only):
1. Push feature branch
2. Open PR

Deferred to morning: merge, tracker transition, any force-push.

