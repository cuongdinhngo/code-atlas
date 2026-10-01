---
id: 352
slug: string-arg-names-a-symbol-rule
title: 'A call whose string argument names a class or a proc links to nothing, so its callers read as zero'
phase: 2
milestone: Coverage
status: done
depends_on: [040, 062, 335]
---

## Why this exists

A field retro (2026-09-30, 19 PRs on an anchor PHP + SQL Server project) scored code-atlas 7.2/10.
The two most-repeated misses were one shape: the target of a call is a string argument.

- **Class by string (4 PRs):** `Widget::make('SaveButton')` builds the class `SaveButton`.
  `find_callers SaveButton::render` answered `relation_unmodelled_for_language`; Grep found them.
- **Proc by string (2 PRs):** `$db->runProc('Insert_Order_v1', $params)` calls the SQL proc of that
  name. `find_callers Insert_Order_v1` answered `no_matches` over 7 PHP call sites.

(Names are stand-ins, R2.4.) 335 already links a literal that *is* T-SQL (`'EXEC X @p'`). A bare
name handed to a wrapper is not language grammar, so R2.2 keeps it out of the adapter.

## Scope

1. A new `CA_INDIRECTION_RULES` entry kind: calls to `<callee>` whose argument `<n>` is a string
   literal emit a HEURISTIC edge (`NEW` or `CALLS`, as the rule says) to the symbol that literal
   names. It extends PLAN §11's rule files (040/062/063); v1 `calls` takes exact qname pairs only,
   while `view_data` setters already extract one-line string args, so the extraction exists.
2. The target resolves through the normal resolver, across languages (PHP → SQL `Function`).
   No match stays unlinked and counted, never invented.
3. Edges carry `rule: true` like every rule edge (068). No rules ⇒ graph unchanged.

## Acceptance criteria

- **AC1:** With a rule for a `make(<class>)` callee, `find_callers <Class>::<method>` reaches the
  sites that build `<Class>` through it, at HEURISTIC, each hit `rule: true`.
- **AC2:** With a rule for a `runProc(<proc>)` callee, `find_callers <proc>` on a SQL proc lists the
  PHP call sites, at HEURISTIC.
- **AC3:** A literal naming no indexed symbol emits no edge and is counted in the build report.
- **AC4:** A non-literal argument (`$name`, concatenation) contributes nothing.
- **AC5:** No rule file ⇒ byte-identical graph (R4.2); an invalid rule fails loud before parse (R5.3).
- **AC6:** Zero repo or framework names under `adapters/` or `code_atlas/` (R1.1, R2.2 gates).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 352 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews and merges the PR, and ratifies ASSUMED A1–A2. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`, batch 352 → 353;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `feat/352-string-arg-names-a-symbol` off `main` (`2ad87272`). Contract `.mango/run-contract-352.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 1 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 2 want-decision asked | 1 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** Five resolve on `2ad87272`: `CA_INDIRECTION_RULES` (`config.py:502`), PLAN §11's rule
files (040/062/063), `view_data`'s one-line string extraction (`enrichment.py` `_keys_for_rule`),
335's T-SQL literal edge, and the `rule: true` flag (068). **One is missing from the ticket:** its
premise "v1 `calls` takes exact qname pairs only" overlooks **`keyed_calls` (222)**, which already
emits a HEURISTIC `CALLS` edge from a string argument through `target_template`
(`enrichment.py` `_keyed_calls_edges`). PLAN §11 never listed it, which is how the ticket missed it.

**Spike (scratch repo, the real PHP adapter, a `make` rule).**

| Literal at the call site | Template | Linked? |
|---|---|---|
| `'SaveButton'` | `{key}::render` | no — the stored qname is `\App\Widgets\SaveButton` |
| `'App\Widgets\SaveButton'` | `{key}::render` | no — the leading `\` is missing |
| `'SaveButton'` | `\App\Widgets\{key}::render` | **yes**, HEURISTIC, `rule: true` |
| `'App\Widgets\SaveButton'` | `\{key}::render` | **yes** |
| `'Nowhere'` | either | no, and **`rules_unresolved` stayed 0** — it counts rules, not literals |
| `$dyn`, `'Save' . $dyn` | either | nothing emitted (`args` = `[null]`) |

So the class shape (AC1) and the proc shape (AC2 — `tests/test_keyed_calls_rule.py` already proves
PHP `querySP('x')` → a SQL proc) work today with a template that spells the stored qname. The field
miss was that no user doc describes `keyed_calls`, and a literal naming nothing is never counted.

**Recall (by handle).** `343-C2` `formatter-rewrites-untouched-lines`.

The exposure check ran in the main loop (the spike above); no dispatch.

| # | Decision | Class | Resolution |
|---|---|---|---|
| A1 | a new rule entry kind (Scope 1) or the existing `keyed_calls` | want (scope) | **ASSUMED:** reuse `keyed_calls`. It already is "calls to `<callee>` whose argument `<n>` is a string literal emit a HEURISTIC edge to the symbol that literal names"; a second kind would duplicate it (R1.2). `kind: NEW` is not added: AC1 asks for `find_callers <Class>::<method>`, which a `CALLS` edge to `{key}::<method>` answers and a `NEW` edge to the class would not |
| A2 | what AC3's "emits no edge and is counted" means | want (bar) | **ASSUMED:** no **link** is made (the unlinked rule edge stays, as 222's AC4 test requires), and the build report counts the **call site** once — `rule_keys_unresolved` — however many rules tried its literal |
| H1 | where the format is documented | how | TOOLS.md's *Configuration reference* owns every knob (PLAN §11, R6.7), so the rule-file format goes there and §11 points to it |

A1–A2 rest on the maintainer's up-front hand-back; neither reverses a prior decision, and both are
surfaced in the PR.

## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 1 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (title, Why this exists, Scope, Acceptance criteria) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=6`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/8 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

H1 cites PLAN §11; A1–A2 cite the hand-back, so `j = 0`.

### BASELINE

`main` at `2ad87272` is CI run 36795547832's tree (4117 passed / 4 skipped on py3.13). Per SG-2 it is
not pasted as a `$` block.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "the target of a call is a string argument" | a literal naming a class or proc links to it | |
| C1 | R2.2 | "A bare name handed to a wrapper is not language grammar" | rules, never the adapter | |
| C2 | Scope 3 | "No rules ⇒ graph unchanged" | | |
| R1 | Scope 1 | a string-argument rule kind | A1: `keyed_calls` | |
| R2 | Scope 2 | resolves through the normal resolver; no match unlinked and counted | A2 | |
| R3 | Scope 3 | `rule: true` | 068, unchanged | |
| AC1 | AC | class by string → `find_callers <Class>::<method>` | | |
| AC2 | AC | proc by string → PHP sites | 222's test | |
| AC3 | AC | literal naming nothing → no link, counted | A2 | |
| AC4 | AC | non-literal contributes nothing | | |
| AC5 | AC | no rules byte-identical; invalid rule loud | 222's tests | |
| AC6 | AC | no repo names in core/adapters | gate R1.1/R2.2 | |

### AC validation

Each AC is falsifiable on a real PHP build: AC1 and AC3 read `find_callers` and `BuildReport`, AC4
reads the rule edges by line, AC2/AC5 are 222's tests (`test_keyed_calls_rule.py`), AC6 is the gate.

### Gap analysis

- **Now:** `keyed_calls` links both shapes when the template spells the stored qname, but nothing
  user-facing documents it, and a literal that links nowhere is invisible unless its whole rule fails.
- **Target:** the format and both recipes in TOOLS.md; `BuildReport.rule_keys_unresolved`.

### Blast radius

- `enrichment.Enriched` gains a field; `apply_indirection_rules` and `_keyed_calls_edges` return it.
- `BuildReport` gains `rule_keys_unresolved`, which reaches `build_or_update_index` through `asdict`
  (`build_or_update_index.py:454`).
- Docs: TOOLS.md (*Configuration reference* row + a subsection), PLAN §11.

### Rule sections

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R1.2 (change-type) ✅ no new rule kind is added beside keyed_calls, §R2.2 (change-type) ✅ nothing under adapters/ changes, §R4.2 (change-type) ✅ the count is a pure function of the rule rows and sites are emitted sorted, §R5.2 (change-type) ✅ rule edges stay HEURISTIC and an unmatched literal is never linked, §R7.6 (change-type) ✅ PLAN §11's stale v1 list is edited in place and the format lives once in TOOLS.md`

## Phase 2 — design

### Approach

1. **Count.** `_keyed_calls_edges` also returns, per `(source, line, key)` site, the stamps every rule
   emitted for it. `count_unresolved_keyed_sites` queries each distinct target once and counts the
   sites none of whose stamps linked. `BuildReport.rule_keys_unresolved` carries it on both build paths.
2. **Docs.** TOOLS.md *Indirection rule files*: the format, the two recipes, "spell the stored qname",
   and the two counters. PLAN §11 lists `keyed_calls` and points there.

### Rejected alternatives

- **A new entry kind** (A1). It would duplicate `keyed_calls`.
- **Normalise a template's missing leading `\`.** That reads PHP's qname spelling in the core (R1.1).
- **Drop the unlinked rule edge.** 222's AC4 test pins that the edge is emitted, unlinked.

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | per-site count | `code_atlas/enrichment.py`, `code_atlas/indexer.py` | build report, build tool payload | R2, AC3 | 2/2 |
| 2 | docs | `docs/TOOLS.md`, `docs/PLAN.md` | doc budgets | R1, G1 | 2/2 |
| 3 | tests | `tests/test_string_arg_names_a_symbol.py`, `tests/fixtures/string_arg_symbol/` (new) | proof | AC1, AC3, AC4 | 2/2 |
| 4 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced in Phase 3.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | real PHP build + `find_callers` | n/a | ✅ |
| AC2 | integration | `test_keyed_calls_rule.py::test_keyed_calls_find_callers_are_heuristic_rule` (PHP → SQL) | n/a | ✅ |
| AC3 | integration | `BuildReport.rule_keys_unresolved` on the same build | n/a | ✅ |
| AC4 | integration | rule edges by line | n/a | ✅ |
| AC5 | integration | `test_keyed_calls_off_is_byte_identical`, `test_keyed_calls_template_must_be_exactly_key` | n/a | ✅ |
| AC6 | static | gate R1.1 / R2.2 | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_string_arg_names_a_symbol.py`. On `2ad87272` AC3 fails and
AC1/AC4 pass — they pin 222's mechanism for the class shape, which the spike showed already works.

### Rollback

`git revert`. One additive report field; no schema or contract change.

## Phase 3 — execute

Commits on `feat/352-string-arg-names-a-symbol`: `04b75016` (the change), `5fac20ce` (the
challenger's D2: the key read from its own argument).

**Proving test, red on the pre-change tree** (`2ad87272`, before any source edit):

    E       AttributeError: 'BuildReport' object has no attribute 'rule_keys_unresolved'. Did you mean: 'rules_unresolved'?
    1 failed, 2 passed in 0.66s

**Sweep.**
- **Axis 1 — file set.** The diff is the change list.
- **Axis 2 — design conformance.** Approach 1–2 as approved, plus D1.
- **Handle `formatter-rewrites-untouched-lines`, traced.** `ruff format --diff code_atlas/enrichment.py`
  proposed five hunks; one was on a line this change wrote (`apply_indirection_rules`, applied), and
  four on untouched lines (`_view_data_edges`, `_keyed_calls_edges`, `_nth_string_literal`,
  `_load_rules`) were not applied.

| # | Approved | Implemented instead | `path:line` | Surfaced |
|---|---|---|---|---|
| D1 | key read as the Nth quoted string on the line (222's extraction, unchanged) | `_call_argument` splits the one `<callee>(` call's arguments at top-level commas and takes the key only from an argument that is one whole literal; a line calling the setter twice yields none | `code_atlas/enrichment.py` `_call_argument` | yes |

D1 is shared with `view_data` (062): `tests/test_view_databag_producer.py` stays green, including a
`put($bag, 'extra', 1)` whose key is the second argument.

Ran at 5fac20ce

```
$ scripts/gate.sh
  PASS bytecode invalidation (checked-hash, 146)
  PASS entry points (derived from [project.scripts])  — code_atlas.egg-info
  PASS ruff check .
  PASS mypy (code_atlas + onboarding_llm)
  PASS npm ci (adapters/typescript)
  PASS npm ci (adapters/sql)
  PASS php adapter runtime deps present (pytest coverage)
  PASS pytest -q
  PASS tokens-to-answer (ratio >= 0.63, recall 1.0, precision 1.0)
  PASS composer validate --strict (R8.3)
  PASS php -l (authored source)  — 8 file(s)
  PASS phpstan level max (R6.6)
  PASS tsc --checkJs --strict (R6.6, TS adapter)
  PASS tsc --checkJs --strict (R6.6, SQL adapter)
  PASS ruff check (R6.6, Python adapter)
  PASS mypy --strict (R6.6, Python adapter)
  PASS R1.1 no language branch in core
  PASS R2.2 no repo/framework name
  PASS R4.1 no LLM in core
  PASS R7.3 no AI-attribution trailer  — 2 commit(s)
  PASS R2.4 commit identity  — 2 commit(s)
  21 passed · 0 failed · 0 skipped
GATE GREEN — all 21 checks passed
```

A first gate run on `04b75016` was stopped before its pytest step finished, because the D1 edits
landed in the working tree under it; it is not counted.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `04b75016`, 56,124 tokens): AC1, AC3, AC5, AC6 met · AC2 met
by inheritance (222's test) · AC4 not met · Scope 1 partial.** Its findings:

1. **An interpolated `"Save$dyn"` is a string to the adapter** (049's category), so its raw text is
   tried as a key. Accepted: it can name no symbol, so it links nothing and is counted; TOOLS.md says
   so. Rejecting `$` in a key would read PHP's interpolation syntax in the core (R1.1).
2. **A key read from the wrong literal** — `make('Save' . $dyn, 'Other')` with `key_arg: 2` took
   `'Save'`, which could link a real class falsely. **Fixed (D1)**, with
   `test_the_key_is_read_from_its_own_argument_never_a_neighbouring_literal` and a receiver line
   (`lookup('Nowhere')->make('SaveButton')`) in the fixture.
3. **AC4's test covered one-argument calls only.** Fixed with 2.
4. **No 352 test on the incremental path.** Both paths reach the count through `_count_late_writes`;
   accepted.
5. **TOOLS.md overclaimed "nothing is emitted".** Fixed: it names what is tried and counted.
6. **No `NEW` kind.** Accepted as A1.

**Round 2 (the same agent resumed, on `5fac20ce`, 59,931 tokens cumulative): 2, 3, 5 met; 1 accepted
and documented.**

`Ph3/4 proven by`: G1, C1–C2, R1–R3, AC1–AC6 — 12/12.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at 5fac20ce — the diff `main..5fac20ce`. Working doc: `docs/tasks/352_string-arg-names-a-symbol-rule.md`
(embedded).

## Phase 5 — finalise

Stale-review guard: after `5fac20ce` only this doc, `docs/BACKLOG.md` (the row closed) and
`docs/TOKEN_LEDGER.md` change; all are exempt.

**Durable lesson: none new.** The premise miss (a ticket written without the phase-1 mechanism that
already does it) is the class PLAN §11's edit fixes at its source: §11 now lists every rule kind.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

1. Push `feat/352-string-arg-names-a-symbol` — pre-authorised.
2. Open the PR — pre-authorised.

Deferred to the maintainer: the merge; ratifying ASSUMED A1–A2.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | review | `challenger`, round 1 | 56,124 |
| 2 | review | `challenger`, round 2 (resumed; cumulative) | 59,931 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 116,055 · top cost driver: review/challenger`

**Revert path:** `git revert` the branch commits.
