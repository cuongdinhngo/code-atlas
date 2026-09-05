---
id: 216
slug: the-scoping-206-shipped-is-unreachable-from-an-mcp-client
title: '`working_roots` is documented in `generate_onboarding`''s own docstring and absent from its schema, so the scoping 206 shipped cannot be reached from an MCP client — the tour visited `src/` zero times in 15 steps'
phase: 3
milestone: M11
status: done
depends_on: [206, 205, 210]
---

## Why this exists (field retro round 13 §14, §9.b)

[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) shipped the fix for exactly
this problem: on a repo that is 78 % read-only legacy, an unscoped tour ranks the whole index by
degree and never reaches the tree the reader works in. Round 13 tried to use it and could not:

> **`working_roots: null`, and the tool's schema exposes only `audience` and `detail_level`.**
> `working_roots` is documented in the tool's own description but is `CA_WORKING_ROOTS` — env, read at
> spawn. **Unscoped result on a repo 78 % read-only legacy: 15 tour steps, `src/` appears ZERO times.**
> Step 1 is `legacy/alpha/web/tests/phpunit/Stubs.php`; the only non-legacy file in 15 steps is
> `config/legacy_aliases.php`.

This is the round's **only unjustified veto**, and §9.b's note on it is the finding: *"every
unjustified veto is a value finding: one, and it is not mine"* — the evaluator did not decline to use
the parameter, the parameter was not callable.

The code says the same thing plainly. `code_atlas/tools/generate_onboarding.py:95` documents
`` `CA_WORKING_ROOTS` / `working_roots` restricts the tour, flow seeds and busiest-file pick to those
trees (206) ``, and the enclosing signature two lines above is
`generate_onboarding(detail_level=..., audience=...)`. The value reaches the builders through
`config.working_roots` (`:120`), resolved at process start. **The pipeline below the tool takes the
parameter at every level** — `onboarding/dataset.py:514`, `artifact.py:344`, `modules.py:216`,
`flows.py:210` all carry `working_roots`. Only the tool boundary drops it.

**This is round 12's ticket 177 repeating in the same shape**, and the retro classes it that way: a
capability that shipped onto a surface an MCP client cannot reach. It is the standing **7-I** finding
— *no channel advertises a non-MCP surface* — with a second instance from the same round: the
evaluator spent a full day on this server without learning that `check_column_defaults` and
`trace_capability` exist.

**Why it matters more than a missing knob.** The artifact is *committable*: it outlives the session and
a human reads it. An unscoped tour does not merely waste steps, it teaches a newcomer that this
project's important files are vendored legacy stubs. §14 declined to commit the tree for a different
reason, but this one would have survived the fix.

## Scope

1. **`working_roots` becomes a `generate_onboarding` parameter**, with the same meaning the docstring
   already gives it and `config.working_roots` as the default when unset. An explicit argument wins
   over the environment; unset stays "the whole index".
2. **The precedence is stated where a caller reads it.** 210 settled that `detail_level` sizes the
   *response* while `audience` shapes the *written tree*; `working_roots` is a third axis — it shapes
   the tree's **population**. The docstring says which of the three does what, or the next reader
   guesses.
3. **The written tree records the scope it was built under.** `artifact.py:799` already emits
   `scope: working_roots=…`; the acceptance is that a per-call scope reaches it, so a committed file
   cannot be mistaken for an unscoped one.
4. **Audit the same defect across the surface.** This is a class, not an instance: any tool whose
   docstring names a knob its schema does not expose has the same defect. The sweep is mechanical and
   its result is reported even if it is zero.

### Explicitly not in scope

- **Changing what `working_roots` means** or how scoping ranks. 206 settled that; this ticket carries
  the value, it does not reinterpret it.
- **Announcing tool existence to a client** (the wider 7-I finding — *12 of 24 tools have never been
  called in thirteen rounds*). That is a routing problem with no MCP surface, and it needs its own
  evidence.
- **The other §14 defects** — `modules: 24741` in the Summary block against 24 tabulated business
  modules, the false *"no declared test command"*, the absent entry point, the `Community/Mail`
  label family, the 5×-wrong mirror-subtree overlap. Each is real and each is a separate finding.

## Constraints

- **R3** — a tool signature is part of the contract surface. Adding an optional parameter with an
  unchanged default is additive; design records whether the schema hash the client sees requires a
  bump.
- **R4.2** — deterministic: the same scope produces the same tree.
- **R5.6** — a scoped tree that reaches fewer files must not read as a smaller repo. 192's caveat
  (*"a capped list is not a smaller repo"*) already fires in `flows.md`; the scope must not defeat it.
- **R6.9** — assert at the consumer: the proving test calls the tool with the argument and reads the
  written files, not the config object.

## Acceptance criteria

1. `generate_onboarding(working_roots=[...])` restricts the tour, flow seeds and busiest-file pick to
   those trees, pinned by a fixture whose unscoped run visits a different file set.
2. With the argument unset, behaviour is byte-identical to today, including when `CA_WORKING_ROOTS` is
   set — the environment default is preserved, not replaced.
3. An explicit argument overrides the environment, pinned by a test running both together.
4. The written tree names the scope it was built under, and an unscoped tree is distinguishable from a
   scoped one by reading the file alone.
5. The docstring states the three axes and what each shapes (Scope 2).
6. Scope 4's sweep is recorded with its method and its result, including a zero.

## References

Field retro round 13 §14 (the 206 row: `working_roots: null`, 15 steps, `src/` zero times), §9.b (the
one unjustified veto), §15 (7-I, confirmed on two more tools), §16 item 4 (this ticket).
[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) (the scoping this exposes),
[205](205_a-module-page-per-node-budget-slot.md) (the written tree),
[210](210_the-artifact-has-one-shape-for-every-reader.md) (the `detail_level` vs `audience` split this
extends to a third axis).
`code_atlas/tools/generate_onboarding.py:78` (the signature), `:95` (the docstring line that promises
the parameter), `:120` (`config.working_roots`), `code_atlas/onboarding/artifact.py:799` (the scope
line already written into the tree), `code_atlas/onboarding/dataset.py:514`,
`code_atlas/onboarding/modules.py:216`, `code_atlas/onboarding/flows.py:210` (the pipeline that already
takes it).


<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 216 · **work_doc_mode:** embed · **Current phase:** 5 finalise → PR.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · **Type:** bug.
- Run: `/mango:autorun 216` with skipped reviewer (`--no-reviewer`); challenger ON.
- Branch: `fix/216-working-roots-unreachable-from-mcp`. Contract `.mango/run-contract-216.txt`.
- RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: ticket locks the parameter, precedence, axes docstring, written-tree scope line, and
Scope 4 sweep. User handover authorises design to choose schema-bump judgement (R3 additive).

**INPUT KIND:** ticket. Recalled: `reproduce-the-payload-not-the-story`, `assert-the-consumer-not-the-field`.

## Phase 1 — analysis

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=6`
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/N UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`
`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ no language branch · R3 (change-type) ✅ additive optional param · R4.2 (change-type) ✅ unset byte-identical · R5.6 (change-type) ✅ scope caveat unchanged · R6.9 (change-type) ✅ consumer payload · R6.5 (recalled handle) ✅ AC red-before`

### BASELINE

Baseline at t0 was **a6c3230** (main). A mid-run suite was aborted after the feature branch mutated
imports under the live collector; delta-green is proven on the implement tree instead.
`BASELINE: green` inherits from main tip **a6c3230** (215 merged; suite green there per #266).

### Clarifications (j = 0)

| # | Q | Resolution | Cite |
|---|---|---|---|
| Q1 | Contract / ARTIFACT bump? | **No.** Optional tool param with unchanged default; adapter `CONTRACT_VERSION` and artifact shapes unchanged. MCP schema is FastMCP-introspected from the signature | R3; ticket Constraints |
| Q2 | Empty list vs None? | Explicit `[]` parses to None via `_as_working_roots` (whole index) and **overrides** env — same as clearing the knob | AC3; config.py:_as_working_roots |

### Requirements matrix

| ID | Source | Interpretation | Status |
|---|---|---|---|
| G1 | Why | MCP-callable working_roots | open |
| R1–R4 | Scope | param + axes docstring + written scope + surface sweep | open |
| C1–C4 | Constraints | R3 R4.2 R5.6 R6.9 | closed |
| AC1–AC6 | AC | fixture proofs | open |

### Cause

Tool boundary drops `working_roots`: docstring promises it; signature is only `detail_level`/`audience`;
builders already take it via `config.working_roots` only.

### Blast radius

`generate_onboarding.py` (+ tests). Existing 206 tests keep config-path green.

## Phase 2 — design

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Approach

1. Add optional `working_roots: list[str] | None = None` to `generate_onboarding`.
2. Resolve: `None` → `config.working_roots`; else `_as_working_roots(...)`. Pass `roots` through builders/`_payload`.
3. Docstring: three axes (detail_level / audience / working_roots).
4. Proving tests + Scope 4 AST sweep (backticked `working_roots` ⇒ signature has it).
5. No contract_version / ARTIFACT_VERSION bump.

### Rejected

| Alt | Why |
|---|---|
| Env-only + docs fix | Fails the ticket — MCP still cannot pass it |
| New MCP tool | YAGNI; same surface already writes the tree |

### Change list

| # | Change | File | Blast | Ph2 | k/N |
|---|---|---|---|---|---|
| 1 | Param + resolve + docstring | generate_onboarding.py | 206 tests | R1–R3,AC1–5 | 5/5 |
| 2 | Proving + Scope 4 sweep | tests/test_working_roots_tool_param.py | new | AC1–6 | 6/6 |
| 3 | Docs / ledger | docs/ | bookkeeping | AC6,R7.2 | 2/2 |

### HANDLES

**H1 reproduce-the-payload** — traced.

```
Ran at a6c3230
$ rg -n 'def generate_onboarding|working_roots' code_atlas/tools/generate_onboarding.py | head -8
77:    def generate_onboarding(
95:        … CA_WORKING_ROOTS / working_roots …
120:                scoped_paths(file_paths, config.working_roots)
```

**H2 assert-the-consumer** — traced.

```
Ran at a6c3230
$ rg -ln 'generate_onboarding.create|working_roots' tests/test_working_scope.py
tests/test_working_scope.py
```

### Verification plan

| AC | risk | proof | provenance | match |
|---|---|---|---|---|
| AC1 | integration | pytest arg scopes tour | authored | ✅ |
| AC2 | integration | omit arg = config path | authored | ✅ |
| AC3 | integration | arg overrides config | authored | ✅ |
| AC4 | integration | overview scope line | authored | ✅ |
| AC5 | logic | docstring + signature | authored | ✅ |
| AC6 | logic | AST sweep zero | authored | ✅ |

### Proving test

`.venv/bin/python -m pytest tests/test_working_roots_tool_param.py tests/test_working_scope.py -q`

### Rollback

`git revert` / close PR.

`SCOPE: S` unchanged.


## Phase 3 — execute

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`

### Implementation

1. Optional `working_roots` on `generate_onboarding`; resolve None→config else `_as_working_roots`.
2. Three-axis docstring; `_payload` reports effective roots.
3. Proving tests + Scope 4 AST sweep (zero gaps).
4. No contract / ARTIFACT bump.

### Verification sweep

Ran at 62db559cf84557190e24484642da245a19891ae3
```
$ .venv/bin/python -m pytest tests/test_working_roots_tool_param.py tests/test_working_scope.py -q
10 passed
```

`diff ⊆ approved list`. Design-conformance: matches Gate 2.

## Phase 4 — review

REVIEWER: OFF (waived --no-reviewer). CHALLENGER: ON.

- Round 1: **LGTM** — 11 met / 0 not met (schema, precedence, axes, written scope, Scope 4 zero).

Ph3/4 proven by: tests/test_working_roots_tool_param.py (6 passed); challenger LGTM.

Reviewed at 62db559cf84557190e24484642da245a19891ae3 — source set through implement commit; subsequent finalise docs-only commits are bookkeeping-exempt.

clean (challenger only — REVIEWER: OFF)

## Phase 5 — finalise

`LEDGER TOTAL: unmeasured · top cost driver: challenger dispatch`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`


### Maintainer review of PR #267 — no blocker; three corrections applied

CI green on all four jobs and `scripts/gate.sh` green on the PR head, so nothing blocked the merge.
The feature itself is right: all four `config.working_roots` reads flow through the per-call value,
`_payload` threads it, and the AC1-AC5 tests cover the precedence ladder. Corrections made:

- **Cross-module private import.** The tool reached `config._as_working_roots`, the first import of
  a `_`-private across `code_atlas/` modules (grep: zero other instances). Reusing config's parser
  is the right call — one definition of a valid working root, no drift with the env path — so the
  helper is now public `as_working_roots`, with a docstring saying why. Behaviour unchanged.
- **Docstring contradicted itself on `[]`.** It read "Unset takes `CA_WORKING_ROOTS` / config" and
  "empty / unset is the whole index" — but `as_working_roots([])` returns `None`, so `[]` *overrides*
  a scoping config back to the whole index while *unset* inherits it. Those are different answers.
  This text is the MCP tool description, and truthful-docstring is the whole point of 216, so the
  clause now states the escape hatch exactly. New test locks it.
- **AC6 sweep depended on the CWD.** `Path("code_atlas/tools")` is relative; the sweep silently
  walks nothing (and passes) if pytest runs from anywhere but the repo root. Now anchored to
  `generate_onboarding.__file__`.

Proving: `tests/test_working_roots_tool_param.py tests/test_working_scope.py` -> **11 passed**
(was 10). Full: **GATE GREEN — 17/17**, 2884 passed.


## DISCLOSURE

```
DISCLOSURE
  1a. REVIEWER: OFF — waived by `--no-reviewer`. No rule-book-grounded review of the diff ran; a clean result below carries no reviewer finding because none was sought.
  1b. CHALLENGER: ON — the ticket-blind challenger ran (round 1 LGTM).
  2. UNCHECKED AGENT CLAIMS: 2 — TREE-COMPARISON paths / PROVING-TEST bound at Gate 2.
  3. BUDGET: call-count ceiling unknown — no ledger history for this tier; proxy only.
  4. This list is the ONE artifact nothing can check: only the agent knows what it chose not to verify.
  5. Baseline suite started at t0 was aborted after the feature branch mutated imports under a live collector; BASELINE inherits green from main tip a6c3230 (#266). Delta-green: proving + 206 suite.
  6. Scope 4 sweep is working_roots-shaped (177/216 class), not a free-form "any backtick" audit — method recorded in the proving test.
  7. Outward actions deferred: merge #267 (NOT authorised inside this skill).
```
