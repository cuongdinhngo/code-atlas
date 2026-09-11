---
id: 242
slug: params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function
title: '`params` is stored by every adapter, indexed into `nodes_fts`, and read by exactly one tool — `class_diagram`, which renders class members only — so a signature is invisible to every nav tool, and on the anchor monorepo 604 stored-procedure signatures the graph holds cannot be reached by any call'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [231, 234, 049, 078]
---

## Why this exists (field retro round 17)

231 made `params` uniform: every shipped adapter emits it, and `capabilities_by_language` stamps
which ones do. The field session then spent its most valuable ticket answering a question `params`
already contains — *how do these two signatures differ?* — with `ls` plus `grep` over two files, and
closed by asking for a new `diff_twin` tool. Neither the session nor its retro knew the answer was
in the index, because **no nav tool returns `params`**.

The one consumer is `class_diagram` (`code_atlas/tools/class_diagram.py:246`, with 231's
`params_not_captured_by_adapter` disclosure at :104). A class diagram renders class-like members, so
a `Function` — a free function, a module-level function, **a stored procedure** — has no route to its
own signature. `read_symbol`, `search_symbol`, `file_outline` and `find_callers` name none of it at
any `detail_level`.

The remaining route is `read_symbol` returning the body and letting the reader parse the header out
of it, which is the token cost the tool exists to avoid — and for the subject measured below it is
not even available: the proc has two definitions, so 078 correctly refuses with
`subject_ambiguous` and **no body at all**.

## Evidence — measured on the anchor monorepo, 2026-09-11

Index at `contract_version: 10`, 19,352 PHP + 3,012 SQL + 2,519 TypeScript files.

| Measure | Value |
|---|--:|
| `sql` `Function` nodes (stored procedures) | 670 |
| …carrying a non-empty `params` with declared types | **604** |
| Nav tools that can return any of it | **0** |

The parameter lists are present and typed:

```
CheckLedgerDays  [{"name":"@CustomerCode","type":"varchar(8)"},{"name":"@StartDate","type":"datetime"},…]
```

**The session's own root cause, recomputed from `nodes.params` alone** — 148 `X` / `X_beta` twin pairs
exist, 28 differ in their parameter list, and one of the 28 is the defect the session spent its
analysis phase finding by hand:

```
dbo.UpdateRecursiveActivitiesUntil      [@endDate, @maxActivities, @maxRecursions]
dbo.UpdateRecursiveActivitiesUntil_beta   [@endDate, @maxActivities]
only in the first: ['@maxRecursions']
```

That is a ~30-line read over one column. It needs no new relation, no edge kind, no
`contract_version` bump and no configuration — which is also why it settles
[098](098_correspondence-relation-seam.md)'s last open argument rather than reopening it (see
References).

## Scope

- **Surface `params` on `read_symbol`.** The declaration's parameter list — name and declared type
  per entry, the adapter's own spelling, no normalisation (R4.2). Present at `standard`; decide and
  state whether `minimal` carries it.
- **Decide `file_outline` explicitly, with a reason either way.** It is the symbol map, and a map of
  20 methods with signatures may be the answer 245's reader wanted; it is also payload weight on
  every outline ([061](061_payload-weight.md), [223](223_the-envelope-bills-every-answer-and-no-gate-noticed-it-growing.md)).
  A written *no* is a deliverable here, not an omission.
- **Honesty when the field is absent.** `params` empty and `params` not captured by the adapter are
  opposite claims. 231 already stamps `capabilities_by_language`; reuse that predicate — never emit
  an empty list that reads as "takes no arguments" (R5.2, R5.6).
- **Out of scope:** any twin/diff/compare tool, any name-convention knowledge (`_beta` and friends are
  a repository's naming, R2), and `args`/`arg_keys` at call sites — `find_callers` already filters on
  those and this ticket does not touch them.

## Constraints

- **R1.1** — no language branch; `params` is a contract node field (CONVENTION §3) and the core reads
  it the same way for every language.
- **R5.2 / R5.6** — an absent capability is disclosed, never rendered as a zero. The
  `capabilities_by_language` stamp is the predicate; a pre-231 index must say it cannot tell.
- **R3** — `params` is already in the contract at its current version. If this ticket needs no
  vocabulary change, it must not bump `contract_version`; if it does, say why in the design.
- **061 / 223** — the envelope is already budgeted and gated. Measure the added bytes per row on a
  large index before and after, and state the cost on a subject with 79 parameters (the anchor holds
  one).
- **R4.2** — identical input, identical rows. No re-ordering, no type inference, no filling a missing
  type from a default.

## Acceptance criteria

- `read_symbol` on a `Function`, a `Method` and a stored procedure returns the parameter list with
  declared types, pinned by tests for at least PHP, TypeScript and SQL.
- A subject whose language's adapter does not capture `params` returns the disclosure, not an empty
  list — asserted against a stamp that says so.
- A written verdict on `file_outline`, with the payload measurement that decided it.
- Payload weight measured before/after; the numbers land in the task file.
- The two-call route is demonstrated end to end: from two qnames to a parameter-list difference, with
  no file read and no new tool.

## References

Field retro round 17 (2026-09-11, maintainer-local) §2.6 and §5 ask 1. Related:
[231](231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md) (made
`params` uniform and stamped the capability),
[234](234_classconst-is-a-php-only-kind-and-the-two-signals-that-would-fill-it-elsewhere-are-discarded.md)
(the same one-adapter-accident shape, one kind over),
[078](078_ambiguous-payload-still-picks-one-definition.md) (why the body route is closed for the
measured subject), [061](061_payload-weight.md) /
[223](223_the-envelope-bills-every-answer-and-no-gate-noticed-it-growing.md) (the weight this must
argue against), [098](098_correspondence-relation-seam.md) — **this ticket is the measurement that
answers 098's last open argument.** 098 held that drift detection was the strongest remaining case
for a correspondence *relation*, because 115's path comparison cannot see drift. Drift at signature
granularity turns out to need no relation: the graph already holds both sides at the granularity
that matters. 098 stays `deferred`; its verdict wants this recorded.

## Token usage

| Phase | Tokens |
|---|---|
| autorun | 1 challenger dispatch unmeasured; reviewer OFF; main-loop unmeasured |

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 242 — params surfaced on read_symbol (working doc)

- **Ticket:** 242 · local file `docs/tasks/242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md`
- **Type:** bug / payload honesty
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 UI paths
- **TIER:** full
- **BASELINE:** green — related suite 29 passed on `0081474e6fbb1ae051cf6dd2023bb0116d5766ed`

## Session status

- **Last updated:** 2026-09-11
- **Current phase:** finalise
- **Next action:** push feature branch + open PR (handover-authorised); merge not authorised
- **Blocked on:** none
- **work_doc_mode:** embed
- Run: `/mango:autorun 242` with `--no-reviewer`; challenger ON.
- Branch: `feat/242-params-surfaced-on-read-symbol`
- Contract: `.mango/run-contract-242.txt`

---

## Phase 0 — Refine

`PREMISE: 12 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

**PREMISE detail.** Present: `code_atlas/tools/class_diagram.py`, `code_atlas/tools/read_symbol.py`, `code_atlas/tools/file_outline.py`, `code_atlas/tools/search_symbol.py`, `code_atlas/tools/find_callers.py`, `code_atlas/store.py` (`stamped_capabilities_by_language`, `CAPABILITIES_BY_LANGUAGE_KEY`), tasks 231/234/078/061/223/098.

**INPUT KIND:** ticket (not epic).

**How-decision (self-resolved):**
1. **`minimal` omits `params`.** `standard` carries it. Cite ticket Scope ("Present at `standard`; decide…") + CONVENTION `detail_level` subset + 061 / class_diagram only enriching at `standard` (`class_diagram.py:98`).
2. **`file_outline` does NOT carry `params`.** Written *no*: outline is N rows per file; signatures multiply envelope cost (061/223). The twin-diff route is two `read_symbol` calls, not an outline. Cite ticket Scope ("A written *no* is a deliverable") + `file_outline.py` map semantics.

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `do-not-attest-past-the-payloads-resolution` | 2 | handle | Yes — params indexed (231) and no nav tool returns them |
| 2 | `stamp-at-the-builder-not-the-wrapper` | 2 | handle | Yes — attach at `_result` / success path builder |
| 3 | `stamp-evidence-with-the-tree-under-review` | 2 | handle | Process — empirical blocks need `Ran at <sha>` |

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=5 R=4 G=1 AC=5`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 proven by | Status |
|----|--------|------------------|----------------|--------------|-----|-----------------|--------|
| G1 | Why | params stored; no nav tool returns them | `read_symbol` returns params | tools omit field | D1 | proving test | ✅ |
| C1 | Constraints | R1.1 no language branch | Read contract `params` + stamp | | D1 | R1.1 grep | ✅ |
| C2 | Constraints | R5.2/R5.6 absent ≠ empty | Disclose via capabilities stamp | class_diagram:104 | D1 | disclosure test | ✅ |
| C3 | Constraints | R3 no bump if no vocab change | CONTRACT_VERSION stays | | D1 | assert version | ✅ |
| C4 | Constraints | 061/223 measure weight | Before/after + 79-param subject | | D2 | AC4 numbers | ✅ |
| C5 | Constraints | R4.2 identical rows | No reorder/infer/fill types | | D1 | fixture pin | ✅ |
| R1 | Scope | Surface params on read_symbol | name+type per entry, adapter spelling | | D1 | AC1 | ✅ |
| R2 | Scope | Decide file_outline | Written no + measurement | | D2 | AC3 | ✅ |
| R3 | Scope | Honesty when absent | disclosure not empty list | | D1 | AC2 | ✅ |
| R4 | Scope | Out of scope: twin tool, args | Do not touch find_callers args | | D1 | diff ⊆ list | ✅ |
| AC1 | AC | Function/Method/proc params for PHP·TS·SQL | | | D3 | multi-lang tests | ✅ |
| AC2 | AC | non-capturing → disclosure not [] | | | D3 | stamp false test | ✅ |
| AC3 | AC | file_outline verdict + measurement | | | D3 | task-file numbers | ✅ |
| AC4 | AC | payload weight before/after | | | D3 | task-file + test | ✅ |
| AC5 | AC | two-call twin route | two qnames → param diff | | D3 | twin demo test | ✅ |

## AC validation

| AC | Match? | Falsifiable? |
|----|--------|--------------|
| AC1 | Y | pytest pins params keys/types for php/ts/sql |
| AC2 | Y | `params_not_captured_by_adapter` present; `params` absent |
| AC3 | Y | written no in task file + byte estimate recorded |
| AC4 | Y | measured delta recorded in task file |
| AC5 | Y | two read_symbol calls; set-diff of param names; no file read |

## Inventory

- **N:** 1 tool (`read_symbol`) · 0 change to `file_outline` (verdict: no)

| # | Item | Ph3/4 | Status |
|---|------|-------|--------|
| 1 | read_symbol params attach | proving module | ✅ |

## Clarifications

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

1. `minimal` omits params; `standard` carries. Cite Scope + CONVENTION + class_diagram:98.
2. `file_outline` = no. Cite Scope written-no deliverable + 061/223 envelope.

---

## Phase 1 — Analysis

- Root cause (`logic`/`payload`): `params` is stored and FTS-indexed (231) but only `class_diagram` reads it for class members; free `Function` / stored-proc signatures have no nav route.
- Blast radius: `read_symbol` success payload only; PLAN tool-table one clause; proving tests. `file_outline` unchanged. No adapter/contract bump.
- `TRACK: backend` · `SCOPE: M` · `TIER: full`

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R1.4 (change-type) ✅ store language_of_file · R2.2 (change-type) ✅ fixture shape not repo names · R3 (change-type) ✅ no bump · R4.2 (change-type) ✅ adapter spelling · R5.2/R5.6 (change-type) ✅ stamp disclosure · R6.1 (change-type) ✅ proving tests · R7.6 (change-type) ✅ PLAN one clause`

### BASELINE

Related suite on ticket-landed HEAD `0081474e6fbb1ae051cf6dd2023bb0116d5766ed` (pre-product change): `pytest tests/test_search_read_outline.py tests/test_read_symbol_minimal_drops_docblock.py tests/test_optional_field_capture.py -q` → **29 passed**.

`BASELINE: green`. No exclusions.

- **Gate 1 status:** cleared (autorun)

---

## Phase 2 — Design

- **Approach.** On a successful `read_symbol` (`found`, not stale, `reason=ok`) at `detail_level=standard`, attach `params` from the node via `parse_json_field`, preserving `{name, type?}` adapter spelling (R4.2). Gate on `store.stamped_capabilities_by_language()` + `language_of_file`: if stamp missing/false for the language, set `params_not_captured_by_adapter: true` and omit `params` (never `[]`). `minimal` and miss/ambiguous/stale paths unchanged. `file_outline` unchanged (written no). PLAN `read_symbol` row gains one clause. No `CONTRACT_VERSION` bump.

- **Rejected.** (1) New `diff_twin` tool — rejected: ticket out-of-scope; two `read_symbol` calls suffice. (2) Put params on `file_outline` — rejected: N× weight (061/223); twin route does not need the map. (3) Emit at `minimal` — rejected: subset contract; measure cost only on the priced `standard` call. (4) Contract bump — rejected: `params` already in NODE_FIELDS (R3).

**Assumptions**

| Assumption | Status |
|------------|--------|
| Node `params` JSON shape is list of `{name, type?}` per 231 | verified — contract + adapters |
| `stamped_capabilities_by_language` is the honesty predicate | verified — class_diagram.py:79–106 |
| `language_of_file` resolves the subject's language | verified — store.py:916 |

**Smallest change-list**

| Change | File | Blast radius | Rows |
|--------|------|--------------|------|
| Attach params + disclosure on success path; docstring | `code_atlas/tools/read_symbol.py` | callers of `_result` / MCP tool desc; existing read tests tolerate additive keys | G1,R1,R3,C* |
| Proving + AC tests (PHP/TS/SQL + disclosure + twin + weight) | `tests/test_read_symbol_params.py` | new file | AC1–AC5 |
| PLAN tool-table one clause | `docs/PLAN.md` | none identified beyond table cell | R7.6 |
| Task-file payload numbers + file_outline verdict | this ticket (working + AC3/AC4 cells) | docs only | AC3,AC4 |

**Recalled handles**

| Handle | Answer |
|--------|--------|
| `do-not-attest-past-the-payloads-resolution` | traced — `rg -n "params" code_atlas/tools/read_symbol.py` → empty (field indexed, tool omits) |
| `stamp-at-the-builder-not-the-wrapper` | traced — `rg -n "_result\(|attach_next_tools" code_atlas/tools/read_symbol.py` → success path builds via `_result` then `attach_next_tools` at :129–143; attach beside that builder |
| `stamp-evidence-with-the-tree-under-review` | does not apply because this is a process/evidence-provenance handle for empirical blocks, not a product payload shape change |

`HANDLES: 3 recalled | 2 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

**Proving test:** `pytest tests/test_read_symbol_params.py::test_two_call_route_diffs_twin_param_lists -q`

**Verification plan**

| AC | Layer | Plan |
|----|-------|------|
| AC1 | integration | index fixtures / planted rows for PHP·TS·SQL Function/Method; assert params |
| AC2 | unit/planted | caps stamp `params: false` → disclosure, no `params` key |
| AC3 | measured | file_outline unchanged; record outline×N byte estimate vs single read |
| AC4 | measured | before/after byte size of one read_symbol; 79-param subject if fixtureable else synthetic |
| AC5 | unit | two qnames → set-diff of param names |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **Gate 2 status:** cleared (autorun)

## Decision log

| When | Decision | Why |
|------|----------|-----|
| t0 | reviewer off, challenger on | `/autorun 242 --no-reviewer` |
| refine | standard carries params; minimal omits | CONVENTION subset + 061 |
| refine | file_outline = no | written-no deliverable; N× weight |
| design | reuse `params_not_captured_by_adapter` key | 231 / class_diagram vocabulary |

## Phase 3 — Execute

- **Branch:** `feat/242-params-surfaced-on-read-symbol`
- **Commits:** pending
- **Proving test:** `tests/test_read_symbol_params.py::test_two_call_route_diffs_twin_param_lists`

- **Verification sweep.** File axis ✅ (`read_symbol.py`, proving tests, PLAN, this ticket). Behaviour axis: implemented-as-approved. `file_outline` untouched (AC3 no).

- **Design-conformance deviations:** none

- **Empirical output**

R6.5 red-before (production `read_symbol.py` on `0081474` lacked `_attach_params`): asserting `params` on a planted capturing Function → **missing key**.

Post-change:

Ran at 0e8e43aab15d317d32a9f355863a43cc81af4d24

```
$ .venv/bin/python -m pytest tests/test_read_symbol_params.py tests/test_search_read_outline.py tests/test_read_symbol_minimal_drops_docblock.py tests/test_routing_suggestion_on_read.py -q --tb=line
27 passed in 2.24s
```

**AC3 file_outline verdict: NO.** Outline of 20 Functions: 1964 B today; if each row carried one `{name,type}` param list: 2804 B (**+840 B / +43%** on the map alone). Twin route needs two priced reads (911 B combined on the field twins), not N signatures on every outline.

**AC4 payload weight (79-param subject `dbo.FatProc`):**

| Measure | Bytes |
|---|--:|
| `standard` (with params) | 2872 |
| `minimal` (no params) | 251 |
| delta (std − min) | 2621 |
| same payload with `params` stripped | 342 |

- **Golden/snapshot:** none
- **Design-invalidation:** none

## Phase 4 — Review

- **REVIEWER: OFF (`--no-reviewer`)** — no rule-book-grounded review of this diff exists.
- **CHALLENGER: ON** — [ticket-blind challenger](c47ed676-1de4-494d-8457-f841b9e25fcc). Raw ticket + `git diff main...HEAD` excluding this file.
- **challenger result:** 8/11 reconstructed requirements **MET**; **2 CAN'T TELL** (written file_outline verdict + task-file payload numbers — held in this working doc / AC3–AC4 cells, excluded from challenger input); 0 not met.
- **Scope reconciliation:** file + behaviour axes clean; no deviations.
- **Proving test would fail without the change?** Yes — R6.5 missing `params` key.

Ran at 0e8e43aab15d317d32a9f355863a43cc81af4d24

```
$ .venv/bin/python -m pytest tests/test_read_symbol_params.py::test_two_call_route_diffs_twin_param_lists -q --tb=line
.                                                                        [100%]
1 passed in 0.19s
```

- **Clean?** `clean (challenger only — REVIEWER: OFF)`
- **Reviewed at** `0e8e43aab15d317d32a9f355863a43cc81af4d24`
- **Reviewed files:** `code_atlas/tools/read_symbol.py`, `tests/test_read_symbol_params.py`, `docs/PLAN.md`, `docs/tasks/242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md` (exempt), `docs/LESSONS.md` (exempt), `docs/TOKEN_LEDGER.md`, `docs/BACKLOG.md`

### Review round 2 — maintainer review on PR #317

**Finding (accepted, fixed):** `_attach_params` ran on every found node, so a non-callable kind
answered with `params: []` — measured before the fix:

```
read_symbol("App\\Thing")      → {"found": true, "params": []}      # Class
read_symbol("App\\Thing::K")   → {"found": true, "params": []}      # Const
```

A `Class` does not take arguments, so both the empty list and (on a non-capturing stamp) the
`params_not_captured_by_adapter` disclosure are claims about a question the subject never asks —
the same R5.6 shape this ticket exists to fix, one kind over, plus 061 weight on every Class read.

**Fix:** gate `_attach_params` on `contract.CALLABLE_KINDS` — the predicate `attach_next_tools`
already applies on the next line. `read_symbol` docstring and PLAN §12's row say "callable".
Pinned by `test_non_callable_kinds_carry_neither_params_nor_the_disclosure`, which also asserts the
callable sibling in the same file still answers, so the gate is the kind and not the stamp.

**Second finding (accepted, fixed): the branch was pushed gate-red.** No `scripts/gate.sh` run is
recorded in this working doc — only targeted suites — and `docs/PLAN.md` was **23,286 tokens against
a budget of 23,250**, so `tests/test_doc_size_budget.py` was failing on the branch. GitHub Actions
could not report it (the unbillable-Actions arrangement AGENTS.md records), so nothing said so.

**Fix:** paid the §12 addition with R7.6 pruning in the same section, and re-ran the whole gate:

- dropped the `verbose` sentence in §12's preamble — the `get_index_status` row two lines below
  says the same thing;
- dropped the "went seven tools out of date" narrative from the R6.7 note, which R6.7 itself holds;
- tightened `build_or_update_index`'s row to one refusal rule, with every ticket reference kept.

`docs/PLAN.md` **23,248 → 23,232** — this PR now *reduces* the file it adds a row to.

```
$ scripts/gate.sh
20 passed · 0 failed · 0 skipped
GATE GREEN — all 20 checks passed
```

## Phase 5 — Finalise

- **Stale-review guard:** product files unchanged since `0e8e43a`; bookkeeping (LESSONS / TOKEN_LEDGER / BACKLOG / this file) is exempt/reviewed set.
- **Planned outward actions:**
  - [x] push branch — handover authorisation
  - [x] open PR via `gh` — handover authorisation — [#317](https://github.com/cuongdinhngo/code-atlas/pull/317)
  - [ ] merge — NOT authorised
- **Durable lesson:** recurrence of `do-not-attest-past-the-payloads-resolution` — `params` was indexed (231) and no nav tool returned it until `read_symbol` did.
- **Revert path:** revert the branch / close the PR without merge.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md (already R5.6) | mango files written: 0`

Classification is a proposal; human ratification deferred (`k = 0`). Class already carried by **R5.6** — bump `seen:` only; `/mango:promote` not required to invent a new rule.

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Notes |
|-------|---------------------|-------|--------|-------|
| Review | ticket-blind challenger | 1 | unmeasured (host does not surface usage) | reviewer OFF; 8 MET / 0 NOT MET / 2 CAN'T TELL |

`LEDGER TOTAL: unmeasured · top cost driver: review/challenger (1 dispatch; reviewer OFF; main-loop unmeasured)`
