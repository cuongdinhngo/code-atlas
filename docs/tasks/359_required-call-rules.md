---
id: 359
slug: required-call-rules
title: 'A rule can forbid an edge but not require one, so a missing-check audit is rebuilt outside the index'
phase: 2
milestone: Coverage
status: todo
depends_on: [138]
---

## Why this exists

A field audit (2026-10-01, an anchor PHP + SQL Server project) runs a security-pattern census
outside code-atlas. It reads `graph.db` directly and hand-codes six graph engines. All six ask one
question: does every symbol in a set S call one of the gates G? For example, every ajax write
handler must call an access check, and every service setup must turn authentication on. With the
graph, 41 of the census's 41 ticket-proven checks pass. Without it, 25 pass.

The consumer pays twice. It re-implements what the server already owns: tiers, freshness and
mid-build detection. It also reads the SQLite schema, which is not a contract. 138's rules can only
say "must not reach", a check for an edge that is present. Requiring a gate is the absent-edge
form, and no rule can say it today.

## Scope

1. `check_architecture_rules` gains a rule mode, `required`, beside today's `forbidden`:
   - `sources` selects symbols with path globs, plus an optional name regex and node kind.
   - `required` names target qnames.
   - A source with no edge of `kinds` to any target within `depth` is a violation.
2. **Absence is tiered over everything the walk explores.** A violation is confirmed only when
   every edge of `kinds` met within `depth` is `RESOLVED`: the source's own edges and those of
   every intermediate symbol. Otherwise it is a candidate, with an `unresolved_outgoing` count
   over the whole explored frontier. In handler → helper → (unresolved), the handler is a
   candidate, not confirmed. A rule never reports a source as clean while the walk met an
   unresolved call.
3. **Calibration as data.** A rule may list `expect` with qnames known to violate and qnames known
   to pass, for example the fixed sites of past tickets. The per-rule report gives
   `expected_found` and `expected_missed`. A rule that misses one reads `calibration_failed`, and
   its rows are still returned.
4. Language-specific gate and sink names live only in the rule file. The core gains no names
   (R1.1, R2.2).
5. **This is a new evaluation path, not a flag on today's.** `architecture_rules.py` matches at file
   granularity: `ArchitectureRule.forbidden` holds globs, and `Violation` carries `source_file` and
   `forbidden_file`. `required` selects symbols and targets qnames, so it needs its own rule type,
   walk and report row. `forbidden` keeps its code path untouched, which is what AC5 pins.

**Out of scope:**
- Tracking tickets or a taxonomy.
- Sinks that are text and never become an edge, such as echo, markup and `innerHTML`. Those stay
  with Grep or a SAST tool.
- A new tool. The surface stays at 24 tools, and a separate tool must make its own case against
  that pin.

## Acceptance criteria

- **AC1:** In a fixture of three handlers, two call the gate and one does not. The rule returns
  exactly one confirmed violation.
- **AC2:** A handler that reaches the gate only through an unresolved `$x->check()` is a
  candidate, with `unresolved_outgoing` ≥ 1, and never confirmed.
- **AC3:** Take handler → helper → gate. With `depth` 2 there is no violation; with `depth` 1 the
  handler violates.
- **AC4:** If `expect` lists a qname as violating and it is not, the rule reads
  `calibration_failed`.
- **AC5:** With no `required` rule, the `forbidden` rule output stays byte-identical (R4.2). An
  invalid `required` rule fails loudly at load (R5.3).
- **AC6:** If `sources` matches zero symbols, the rule says so rather than reporting zero
  violations. Design decides between reusing `rule_matched_no_files` and adding a reason to the
  `NavReason` vocabulary (`code_atlas/tools/nav_result.py`). If it adds one, check whether that
  vocabulary is contract-frozen (R3) and, if so, bump and cut a release.
- **AC8:** handler → helper → gate, where helper also has an unresolved call: with `depth` 2 the
  handler passes (the gate is reached). In handler → helper → (unresolved only), the handler is a
  candidate, never confirmed.
- **AC7:** No repo or framework names appear under `code_atlas/` (R2.2 gate). Fixtures use
  stand-in names (R2.4).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 359 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews and merges the PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`, batch 360 → 357 → 358 → 359;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `feat/359-required-call-rules` off `main` (`41ba7996`). Contract `.mango/run-contract-359.txt`, written
  after the first change commit (see DISCLOSURE). RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 16 unresolved surfaced | 0 want-decision asked | 16 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** All six resolve on `41ba7996`: `check_architecture_rules` (the tool), `architecture_rules.py`
(`ArchitectureRule.forbidden` globs, `Violation.source_file` / `forbidden_file`), `rule_matched_no_files`
(`architecture_rules.py:28`, `nav_result.py:67`), the `NavReason` vocabulary (`nav_result.py`), the R2.2
gate (`ci.yml` guardrails), and 138's rule file shape (`tests/fixtures/architecture_rules/rules.json`).

**Recall (by handle — a new rule type other modules import).** `343-C2` `formatter-rewrites-untouched-lines`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 45,914 tokens) surfaced X1–X7. It
labelled X1, X3 and X6 "want"; each is answered by the ticket or the code, cited below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | how a file marks a required rule | how | a `required` key (Scope 1: "a rule mode, `required`, beside today's `forbidden`"); `forbidden` / `direction` / `transitive` on it fail at load (R5.3) |
| H2 | source selection | how | path globs, one `kind` from `NODE_KINDS`, a `name` regex searched in the node's `name` (Scope 1) |
| H3 | `depth` default | how | none — mandatory int ≥ 1 (R5.3: a hidden default would silently change what "violates" means); `kinds` defaults to `IMPACT_KINDS`, as forbidden does (`architecture_rules.py:_optional_kinds`) |
| H4 | where the walk lives | how | `store.required_walk` (R1.4: only `store.py` touches SQLite); only RESOLVED edges expand, as `reachable_from` (`store.py:3147`) |
| H5 | the three outcomes | how | reached → pass; not reached over an all-RESOLVED, untruncated walk → confirmed; else candidate (Scope 2) |
| H6 | AC6's choice | how | reuse `rule_matched_no_files` for zero sources **or** zero targets present — "every declared rule matched no file on one side" is the same shape (`nav_result.py:65`); no `NavReason` change, so no R3 bump |
| H7 | calibration semantics | how | a `violating` expectation is met only by a **confirmed** row — "HEURISTIC-only evidence is a candidate, never a gate failure" (`architecture_rules.py:4`); a `passing` one only by a matched source with no row |
| H8 | payload and AC5 | how | required rows follow forbidden rows; forbidden rows, reports and digest unchanged when no required rule exists (Scope 5) |
| H9 | row order | how | file order, then node order — deterministic (R4.2) |
| X1 | a source that is itself a target | how | passes: a seed is reached at hop 0, as `reachable_from` seeds are (`store.py` `reach_seen … is_seed`) |
| X2 | some required qnames missing from the index | how | named in `targets_missing` on the rule report (R5.6: never attest past what the payload can distinguish) |
| X3 | `kind` omitted | how | every node in the matched files — Scope 1 calls the kind "optional" |
| X4 | one qname, several nodes | how | one source per qname; an `expect` qname that is no source counts as missed |
| X5 | NULL target / NULL tier | how | a NULL target is unresolved; a NULL tier reads RESOLVED, as `reachable_from`'s `COALESCE` does |
| X6 | what `unresolved_outgoing` counts | how | edges met — Scope 2: "an `unresolved_outgoing` count over the whole explored frontier" |
| X7 | a rule with zero violations | how | `checked` (`STATUS_CHECKED`), distinct from `rule_matched_no_files` |

## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (title, Why this exists, Scope, Out of scope, Acceptance criteria) | 5 decomposed | ROWS: C=3 R=5 G=1 AC=8`
`CLARIFICATION: 16 raised | 16 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

`main` at `41ba7996`: CI run 36876561135 concluded `success`. Ran at 41ba7996.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "does every symbol in a set S call one of the gates G?" | answered by the server, not a consumer's SQL | ✅ |
| C1 | Out of scope | no new tool; the surface stays 24 | `check_architecture_rules` gains the mode | ✅ |
| C2 | Out of scope | text sinks stay with Grep | not modelled | ✅ |
| C3 | Scope 4 | gate names only in the rule file | no names under `code_atlas/` | ✅ |
| R1 | Scope 1 | the `required` mode: sources, required, kinds, depth | `RequiredRule` + loader | ✅ |
| R2 | Scope 2 | absence tiered over the whole walk | `store.required_walk` counts every non-RESOLVED edge | ✅ |
| R3 | Scope 3 | `expect` → `expected_found` / `expected_missed` / `calibration_failed` | rule report | ✅ |
| R4 | Scope 4 | R1.1, R2.2 | grep gates | ✅ |
| R5 | Scope 5 | own type, walk and row; forbidden untouched | split loop; digest unchanged | ✅ |
| AC1 | AC | one confirmed of three | test | ✅ |
| AC2 | AC | unresolved `$x->check()` → candidate | test | ✅ |
| AC3 | AC | depth 2 passes, depth 1 violates | test | ✅ |
| AC4 | AC | calibration_failed | test | ✅ |
| AC5 | AC | forbidden byte-identical; invalid rule loud | digest pins + 7 load cases | ✅ |
| AC6 | AC | zero sources says so | `rule_matched_no_files` | ✅ |
| AC7 | AC | no repo/framework names | R2.2 gate | ✅ |
| AC8 | AC | helper's unresolved call: gate reached passes; unresolved only → candidate | two tests | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1–AC4, AC6, AC8 | yes — counts, statuses and row qnames in the tool payload | |
| AC5 | yes — two digests recorded on `41ba7996` for 138's fixtures, asserted after; seven malformed rules each raise `ConfigError` naming the field | |
| AC7 | yes — the R2.2 grep gate in `scripts/gate.sh` | |

### Gap analysis (enhancement)

- **Now.** `_load_rules` requires `forbidden` (`architecture_rules.py`); the walk is file-to-file
  reachability; no rule can express an absent edge.
- **Target.** A second rule type with its own symbol-level walk and report row.

### Blast radius

- `architecture_rules.load_architecture_rules` / `check_architecture_rules`: the tool is the only
  caller (`grep -rn "architecture_rules" code_atlas`).
- `CheckOutcome` gains two defaulted fields; the tool's row and rule shapes gain a branch each.
- The `NavReason` vocabulary, `main.TOOL_NAMES` (24) and every count-pin on the surface are untouched (P5).
- Docs: `docs/TOOLS.md` (the tool row and a rule-file section — the format had no doc before).

### Rule sections

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the walk and rule type carry no language branch, §R1.4 (change-type) ✅ the walk's SQL is in store.required_walk; architecture_rules.py only calls it, §R2.2 (change-type) ✅ gate names live in the rule file; tests use stand-ins, §R3 (change-type) N/A because no NavReason, node or edge vocabulary changes (H6), §R4.2 (change-type) ✅ ordered rows and a digest; forbidden digests pinned, §R5.3 (change-type) ✅ a malformed required rule raises ConfigError naming its field, §R6.5 (change-type) ✅ every new test fails on 41ba7996: a required rule does not load there, §R7.5 (change-type) ✅ every new comment ≤ 3 lines`

## Phase 2 — design

### Approach

1. **`store.required_walk(seed, targets, kinds, depth, max_nodes)`** → `RequiredWalk(reached,
   unresolved_outgoing, truncated)`: BFS by hop; RESOLVED edges expand or reach; every other edge
   met is counted; a seed that is a target is reached; `max_nodes` truncates.
2. **`architecture_rules`**: `RequiredRule`, `RequiredViolation`, `RequiredRuleReport`
   (`targets_missing` included); `_load_required_rule` (fail loud per field); `_check_required`
   and `_required_sources`; `check_architecture_rules` runs forbidden rules on their old loop, then
   required ones; the digest adds keys only when a required rule exists.
3. **The tool**: required rows appended after forbidden rows in `results` / `candidates`; the rule
   shape branches on report type; the docstring names the mode.
4. **`docs/TOOLS.md`**: the tool row, and a rule-file section for both modes.

### Rejected alternatives

- **A flag on the forbidden rule.** Scope 5: file-granular rows cannot carry a symbol and a count.
- **Reuse `reachable_from`.** It drops unlinked edges (`WHERE e.target_qname IS NOT NULL`), the very
  ones Scope 2 must count, and pays temp tables per source.
- **A new `NavReason` for zero sources.** A contract question (R3) for a shape `rule_matched_no_files`
  already names.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | an unresolved `$x->check()` is stored as a CALLS edge with a NULL target or a non-RESOLVED tier | verified — `contract.py` tiers; 138's HEURISTIC fixture |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `required_walk`, `RequiredWalk` | `code_atlas/store.py` | new method only | R2, AC2, AC3, AC8 | 1/1 |
| 2 | rule type, loader, evaluation | `code_atlas/architecture_rules.py` | the tool | R1, R3, R5, AC1, AC4–AC6 | 1/1 |
| 3 | payload rows and rule shape | `code_atlas/tools/check_architecture_rules.py` | tool payload | R5, AC5 | 1/1 |
| 4 | proving tests | `tests/test_required_call_rules.py` (new) | — | AC1–AC8 | 1/1 |
| 5 | docs | `docs/TOOLS.md` | doc budget | R1 | 1/1 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced: `ruff format --diff` over the three edited core
  files proposes hunks only on lines this change does not own (none mention the new symbols); not
  applied. The new test file was formatted.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC4, AC6, AC8 | integration | the tool over a seeded file-backed index | n/a | ✅ |
| AC5 | integration | digests on 138's fixtures + load errors through the tool | n/a | ✅ |
| AC7 | static | R2.2 grep gate | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_required_call_rules.py`. Every required-rule test fails on
`41ba7996` (the loader demands `forbidden`); AC5's digest pins hold there by construction.

### Rollback

`git revert` the branch commits. A rule file with a `required` rule fails loud on the old code.

## Phase 3 — execute

Commits on `feat/359-required-call-rules`: `ca5ced8e` (the change), `e7e83140` (X1, X2), `cb2dda7a`
(the challenger's findings 1–4).

**Sweep.**
- Axis 1 — file set: the change list exactly.
- Axis 2 — design conformance: bullets 1–4 as approved. `ruff check`, `mypy code_atlas` clean.
- `tests/test_required_call_rules.py` + `tests/test_architecture_rules.py`: 31 passed. A related
  sweep (`-k "architecture or instruction or description or docstring or nav or mcp_server or
  contract or tool_names or surface or budget or skill"`): 646 passed, 98 skipped (adapter tests
  whose deps the worktree lacks), on `ca5ced8e`.
- The TOOLS.md example loads as one `ArchitectureRule` and one `RequiredRule`.
- **Red first.** The test file copied onto a worktree of `41ba7996`: 20 failed, 1 passed — the one is
  AC5's forbidden digest pin, which holds there by construction.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `e7e83140`, 57,888 tokens): 12 met · 0 not met · 1 can't
tell.** The can't-tell is AC1. It assumed the test skipped with the adapter tests, but the test seeds
its index directly: `test_one_handler_of_three_skips_the_gate` passed in the main loop on
`cb2dda7a`. It found no off-by-one in depth, cycles are safe, and truncation forces a candidate.
Findings:

1. Scope 2's "never clean while the walk met an unresolved call" against AC8's pass. The code follows
   AC8, the more specific clause. **Fixed in docs:** a reached target is a pass.
2. Calibration is stricter than the ticket's words: only confirmed rows meet a `violating` entry.
   **Fixed in docs** (H7 is the decision).
3. `rule_matched_no_files` outranks `calibration_failed`. **Fixed in docs.**
4. Required rows are not canonically sorted. **Fixed:** they are sorted by `(rule_id, source_file,
   source_qname)` before the digest.
5. A forbidden rule ignores stray required-only keys. **Left:** rejecting them would touch the
   forbidden path, which AC5 pins.

The fixes stay inside the reviewed files, so the verify ran in the main loop with no re-dispatch:
40 passed (the required, architecture and doc-budget tests) on `cb2dda7a`.

`Ph3/4 proven by`: G1, C1–C3, R1–R5, AC1–AC8 — 17/17.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at cb2dda7a — the diff `main..cb2dda7a`. Working doc: `docs/tasks/359_required-call-rules.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `cb2dda7a` only bookkeeping changed — this doc, `docs/BACKLOG.md`,
`docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`, all exempt.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

No new lesson: the review's findings were wording and ordering, none a recurring class. Per P1,
`343-C2` gains 359 (the formatter handle was traced).

### Outward actions

1. Push `feat/359-required-call-rules` — pre-authorised.
2. Open the PR — pre-authorised.

Deferred to the maintainer: the merge.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 45,914 |
| 2 | review | `challenger`, round 1 | 57,888 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 103,802 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits.
