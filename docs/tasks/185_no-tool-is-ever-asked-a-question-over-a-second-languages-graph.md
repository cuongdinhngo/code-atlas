---
id: 185
slug: no-tool-is-ever-asked-a-question-over-a-second-languages-graph
title: 'The multi-language claim stops at the adapter boundary — 147 made conformance a per-adapter matrix, but no test asks any of the 22 tools a question over a second language''s graph'
phase: 1.5b
milestone: Coverage
status: done
depends_on: [147, 012, 019]
---

## Why this exists

code-atlas is a multi-language server whose anchor repo happens to be PHP. The PHP repo is the
**test subject**, not the product. Everything that proves the product is language-agnostic stops one
layer short of the surface an agent actually calls:

| Layer | Proven for two languages? | By what |
|---|---|---|
| Adapter output | **yes** | `tests/contract/test_adapter_conformance.py` — a per-adapter matrix (147), `REGISTRY` holds PHP + TS, cases are data in `adapter_registry.py`, empty registry FAILS (R6.5) |
| Indexer + store | **yes, for TS** | `test_ts_import_resolution.py` / `test_ts_semantic_types.py` run `full_build` + `GraphStore` |
| **The 22 tools** | **no** | no test in `tests/` imports `code_atlas.tools` and asks anything over a TS-indexed graph |

Swept all 140 files in `tests/`: the only ones that build a TS graph are the two above, and neither
imports a tool. `test_class_diagram.py:179` mentions `"typescript"` solely as an R2.2 denylist
string. So **"22 tools × every language" is tested for PHP and *asserted* for TypeScript** — the
strongest sentence the repo can honestly say today is *"the adapter conforms"*.

## What that gap already costs, concretely

Three tools are gated on vocabulary a given adapter may never emit, and nothing pins what they
should do about it:

| Tool | Gated on | PHP | TS/JS |
|---|---|---|---|
| `include_graph` | `INCLUDES` (`include_graph.py:28`) | emits it | **never emits it** — TS uses `IMPORTS` |
| `find_references` | `UNMODELLED_REFERENCE_KINDS` = `REFERENCES` + `IMPORTS` | both | `IMPORTS` only |
| `find_view_data` | `PROVIDES_VIEW_DATA` | config-driven for every language (`enrichment.py:186`), so empty by default for **all** of them |

`class_diagram` / `find_implementations` lose `USES_TRAIT` for TS, which is **correct** — TypeScript
has no traits. That is exactly why the matrix needs three states and not two: *answers*, *empty
because the relation is not modelled for this language*, and *not applicable by language design*.
Today all three collapse into the same empty payload, and no test can tell them apart.

**This is the ticket that makes adapter #3 and #4 safe to add.** 184's tier 1a emits only `Function`
and `CALLS`, so it is the most extreme column this matrix will ever hold — roughly half the surface
declaring an empty. Landing 184 without this matrix ships ~10 tools' worth of confident zeros over
378,790 lines and calls it coverage.

## Scope

1. A **cross-language tool-parity matrix**, one layer above 147's and built the same way: the
   expectations are **data**, adding a language is a row of declarations, and the test body is never
   edited (147 AC2 is the precedent to copy).
2. For each registered adapter × each of `main.py`'s `TOOL_NAMES`, a declared expected state from a
   closed set — at minimum `answers` · `empty_relation_not_modelled` · `not_applicable_by_language`.
   Design fixes the vocabulary and records why each state is distinguishable from the others **in the
   payload**, not only in the test.
3. **Guard-the-guard, the same way 147 did it.** An `(adapter, tool)` pair with no declaration
   FAILS; an empty matrix FAILS. A new adapter must not be able to land with an undeclared surface.
4. Design records the **fixture strategy**: whether one small per-language fixture repo can drive all
   22 tools, or whether some tools (`architecture_overview`, `guided_tour`, `generate_onboarding`)
   need a shaped fixture, and what the suite costs per run.

### Explicitly not in scope

- **Fixing** any of the three gaps above. This ticket makes the state declared and checked;
  [186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) owns turning a
  declared `empty_relation_not_modelled` into an honest payload.
- Adding an adapter, or `.sql`/Python/C# fixtures. The matrix must accept a new column; filling one
  is that adapter's ticket.
- Per-language output *quality* (ranking, resolution rate). 183 owns the measurement.
- Asserting identical payloads across languages. Parity is **the declared state matching**, never
  byte equality — two languages legitimately answer differently.

## Constraints

- **R1.1** — the matrix is data keyed by the adapter's own handshake language string. A test may name
  a language (tests are not the core); the **core** must gain no branch from this work.
- **R2 / R2.2** — fixtures encode each language's spec, never a repo's names. No the anchor repo shapes.
- **R6.5** — an unrunnable column is `skipped`, and `0 skipped` is the evidence it ran; a matrix that
  silently skips TS reads as green while proving nothing. Use the `availability` marks
  `adapter_registry.py` already carries.
- **R6.7** — one definition site for the state vocabulary, shared with 186 if 186 needs it at runtime.
- **Cost** — 22 tools × n adapters is the whole suite's shape; design states the per-run cost and
  whether any tool is declared-only rather than executed, and why.

## Acceptance criteria

1. The matrix exists as data, covers `TOOL_NAMES` × `REGISTRY`, and **fails today** for at least the
   three gated tools above (`include_graph`, `find_references`, `find_view_data` on TS).
2. An undeclared `(adapter, tool)` pair fails; an empty matrix fails — both made to fail, pinned.
3. Adding a hypothetical adapter is a data row plus fixtures, with no edit to the test body — pinned
   the way 147 AC2 is.
4. A tool that legitimately differs by language (`USES_TRAIT` on TS) is declared
   `not_applicable_by_language` and is **not** a failure.
5. TS columns run for real; `0 skipped` on a host with Node, `skipped` (never green) without it.
6. No new language branch under `code_atlas/` — R1.1 grep-gate stays green.
7. The suite's added wall-clock is measured and recorded in the working doc.

## References

`tests/contract/test_adapter_conformance.py` + `tests/contract/adapter_registry.py` (`REGISTRY`,
`AdapterConformance`, `availability`) — the pattern this ticket lifts one layer, from 147/012.
`code_atlas/main.py:47` (`TOOL_NAMES`, 22 tools). `code_atlas/tools/include_graph.py:28,76`;
`code_atlas/contract.py:78` (`UNMODELLED_REFERENCE_KINDS`); `code_atlas/enrichment.py:186`
(`PROVIDES_VIEW_DATA` is config-driven, not adapter-emitted). AGENTS.md's roll-out order
(PHP → TS/JS → Python → C#/.NET) and PLAN §18.2. Related:
[147](147_contract-harness-is-php-shaped.md) (the per-adapter matrix),
[019](019_typescript-adapter.md) (adapter #2),
[183](183_edge-health-has-no-per-language-breakdown.md) (the per-language measurement),
[184](184_tsql-source-adapter-tier-1a.md) (the column that most needs this to exist first).

## Session status

- **KEY:** 185 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended batch) · envelope in `.mango/run-contract-185.txt`.
- **Branch:** `feat/185-cross-language-tool-parity` (stacked on `feat/183-…`, PR based on it)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2260 passed, 0 failed` at `bbec170` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

Both are how-decisions the ticket delegates by name and answers itself by pointing at 147:

1. Scope 2 — *"Design fixes the vocabulary and records why each state is distinguishable from the
   others in the payload."* Resolved in *Approach* / *The state vocabulary*.
2. Scope 4 — *"Design records the fixture strategy … and what the suite costs per run."* Resolved in
   *Approach* / *Fixture strategy*, with the measured number.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 6 reference(s) checked | 0 missing | 2 ambiguous (surfaced; BOTH corrected by measurement — see below)`
`RECALL: 3 claim(s) surfaced | 1 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=4 R=4 G=1 AC=7`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 10 applicable — 7 by change-type | 3 by recalled handle — §R1.1 (change-type) ✅ · §R1.8 (recalled handle) ✅ · §R2.2 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.2 (change-type) ✅ · §R6.3 (recalled handle: fixture-shape-begs-the-question) ⚠ recorded, see EXCLUSIONS · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.7 (change-type) ✅ · §R7.2 (change-type) ✅ · §R7.6 (change-type) ✅`
`BASELINE: green — 2260 passed, 0 failed, 0 skipped at bbec170 (bare pytest, Linux host)`

**Premise: the gap itself is real and reproduced.** No test imported `code_atlas.tools` and asked
anything over a TS-indexed graph. Confirmed before writing code.

**Two of the ticket's three predicted gaps are wrong, and measurement is what settled it.** The
ticket's table predicts `include_graph`, `find_references` and `find_view_data` all fail on TS. What
22 tool calls over a real TS graph actually show:

| Tool | ticket predicts | measured |
|---|---|---|
| `include_graph` | fails on TS | **confirmed** — `reason: no_matches`, `results: []` |
| `find_references` | fails on TS | **wrong** — `reason: ok`, `total_count: 1`. TS emits `IMPORTS`, which is *in* `UNMODELLED_REFERENCE_KINDS`, so the tool answers; what it loses is `REFERENCES`, a narrower fact |
| `find_view_data` | fails on TS | **not a language gap at all** — `capability_not_configured` on **both** languages, because `PROVIDES_VIEW_DATA` comes from enrichment rules, never from any adapter |

`class_diagram` / `find_implementations` losing `USES_TRAIT` likewise does **not** empty either tool:
both answer on TS. So **no tool is empty for a trait reason**, which is what AC4's example assumed.
This is recorded as a deliberate departure from AC4's literal wording in *AC4 verdict* below.

**Recall:** `one-rule-for-every-subject-slot` (R1.8, by handle — and it earned its keep, see the
`find_orphans` crash). `prove-the-guard-fails` (R6.5, by handle — 147's guard-the-guard is the
pattern being lifted). `REGISTRY` (by symbol — the matrix this one sits above).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | the multi-language claim stops at the adapter boundary | ask every tool over every language's graph | swept `tests/`, 0 hits | open |
| R1 | Scope 1 | a cross-language parity matrix, expectations as **data**, test body never edited | 147 AC2's shape, one layer up | `adapter_registry.py` | open |
| R2 | Scope 2 | `TOOL_NAMES` × `REGISTRY`, declared state from a closed set; design fixes the vocabulary | five states, each with a checkable obligation | `main.py:47` | open |
| R3 | Scope 3 | guard-the-guard: undeclared pair FAILS, empty matrix FAILS | derived from `TOOL_NAMES`/`REGISTRY` | `test_the_registry_is_non_empty` | open |
| R4 | Scope 4 | design records the fixture strategy and the per-run cost | reuse each language's spec fixtures; measured | `tests/fixtures/<lang>/` | open |
| AC1 | AC 1 | matrix exists as data, covers `TOOL_NAMES` × `REGISTRY`, **fails today** for the gated tools | Falsifiable: red run A | proving test | open |
| AC2 | AC 2 | undeclared pair fails; empty matrix fails — both made to fail | Falsifiable: red runs B, C, E | proving test ×3 | open |
| AC3 | AC 3 | adding an adapter is a data row + fixtures, no test-body edit | Falsifiable: red run E | proving test | open |
| AC4 | AC 4 | a legitimate per-language difference is declared and is not a failure | **departure recorded** — see verdict | proving test | open |
| AC5 | AC 5 | TS columns run for real; `0 skipped` with Node, `skipped` without | Falsifiable: suite output + the availability mark | proving test | open |
| AC6 | AC 6 | no new language branch under `code_atlas/` | Falsifiable: grep-gate | `gate.sh` | open |
| AC7 | AC 7 | added wall-clock measured and recorded | Falsifiable: measured below | measurement | open |
| C1 | Constraint | R1.1 — matrix keyed by the adapter's handshake string; a **test** may name a language | keyed by adapter dir name | — | binding |
| C2 | Constraint | R2/R2.2 — fixtures encode the language spec, never a repo's names | reuse the R6.2 fixtures | — | binding |
| C3 | Constraint | R6.5 — an unrunnable column is `skipped`; `0 skipped` is the evidence it ran | reuse `cli.availability` | — | binding |
| C4 | Constraint | R6.7 — one definition site for the state vocabulary, shareable with 186 | `tool_parity.STATES` | — | binding |

### Root cause (taxonomy: config / test coverage)

The repo's language-agnosticism is proven bottom-up — contract, then adapter, then indexer/store —
and each layer's proof was written when it was the newest layer. The tools were the **first** layer
built, against the only adapter that existed, so their tests are PHP-shaped for the same reason the
early code was: there was nothing else to be shaped by. Adapter #2 landed with a green suite because
nothing in that suite could see the tools' single-language assumption.

### Blast radius

- **Test-side only.** Two new files under `tests/contract/`. No `code_atlas/` change at all, which is
  why AC6 is satisfied by construction rather than by care.
- `adapter_registry.REGISTRY` gains a second consumer, so a new adapter now fails **two** guards
  instead of one. That coupling is the point of AC2/AC3.
- Suite wall-clock: measured below.

## Phase 2 — design

### Approach

**`tests/contract/tool_parity.py` holds the data; `tests/contract/test_tool_parity.py` holds a body
that never changes.** Adding a language is a `ToolParity` row: its `AdapterCli` (reused, so
availability and the launch argv are not re-derived), its fixture globs, an entry-point glob, a
`subjects` dict, and one `Expect` per tool. `INVOKERS` maps each tool to *how to call it* and *which
payload key means it answered* — language-independent, so adding a language never touches it, while
adding a **tool** does, and `set(INVOKERS) == set(TOOL_NAMES)` makes that mandatory rather than
optional (R6.7).

### The state vocabulary — five states, because "empty" has four causes

| State | Obligation the test enforces |
|---|---|
| `answers` | the principal collection is non-empty |
| `answers_without` | non-empty, **and** every declared kind is absent from this language's graph |
| `empty_relation_not_modelled` | empty, **and** every declared kind is absent from this language's graph |
| `not_applicable_by_language` | empty, **and** the missing language feature is named |
| `empty_capability_not_configured` | empty, **and** the payload's own `reason` matches the declaration |

**Every state carries a checkable obligation, so a declaration cannot be a rubber stamp** — that is
the design's load-bearing idea. A cell claiming *"this answer is narrower because `USES_TRAIT` is
missing"* is checked against the graph's actual edge kinds; red run D shows the guard biting on a
false claim.

**Why five rather than the ticket's three.** `find_view_data`, `check_architecture_rules` and
`diff_architecture` are empty on **both** languages for a **configuration** reason, and the payload
already says so in its own words (`capability_not_configured`, `snapshot_not_found`). Folding those
into `empty_relation_not_modelled` would have declared a language gap where none exists — the exact
error 185 exists to stop. And `answers_without` exists because the real per-language differences
measured here are *narrowings of a non-empty answer*, not empties.

**Distinguishable in the payload, not only in the test (Scope 2).** Today: `answers` vs the rest is
distinguishable (non-empty vs empty). `empty_capability_not_configured` is distinguishable *by the
payload alone* — it carries its own `reason`, which the test asserts. `answers_without` is
distinguishable in the graph but **not** in the payload: nothing tells a reader that a TS
`class_diagram` has no trait row because TS has no traits. `empty_relation_not_modelled` vs
`not_applicable_by_language` are **not distinguishable in the payload at all** — both are a bare
empty. That is precisely 186's ticket, and this design deliberately stops at declaring the state so
186 has a vocabulary to make honest. `STATES` is exported from one module for 186 to import (R6.7/C4).

### Fixture strategy (Scope 4)

**Reuse each language's existing R6.2 spec fixtures** — `tests/fixtures/php/*.php` and
`tests/fixtures/typescript/*.{ts,tsx,js}` plus each `resolve/` subdirectory — copied into a git repo
under `src/`, with a `.code-atlas.toml` naming the adapter, then `full_build`. No new fixtures, so
R2.2 holds for free: these files already encode the language spec rather than a repo.

They are rich enough for **all 22 tools** with no shaping: PHP yields 24 files / 190 nodes / 301
edges across 10 edge kinds; TS yields 30 files across 7 kinds. `architecture_overview`, `guided_tour`
and `generate_onboarding` — the three the ticket flagged as possibly needing a shaped fixture — all
answer (`total_count` 4 / 23 / 17 on PHP, 3 / 29 / 22 on TS). **No tool is declared-only; all 44 cells
execute.**

The two builds are module-scoped, so 44 cells pay 2 builds rather than 44.

### AC4 verdict — a recorded departure, with the measurement behind it

AC4 asks that `USES_TRAIT`-on-TS be declared `not_applicable_by_language` and not be a failure.
**Measured, neither `class_diagram` nor `find_implementations` is empty on TS** — both answer.
Declaring them `not_applicable_by_language` would therefore assert something false, and the test's
own obligation for that state (*empty*) would fail. They are declared `answers_without` with
`kinds=("USES_TRAIT",)` and a named reason, which is checked against the graph and is strictly more
informative: it says the answer is *real and narrower*, not absent.

**`not_applicable_by_language` is retained in the closed set with no occupant today.** It is not dead
weight: 184's tier-1a column (`Function` + `CALLS` only) is the case it exists for, and 186 needs the
vocabulary complete. Recorded rather than quietly dropped.

### Rejected alternatives

- **Assert payload equality across languages.** Explicitly out of scope, and wrong: two languages
  legitimately answer differently. Parity is the declared state matching.
- **One shared cross-language fixture repo.** Would put two languages in one graph, so a per-language
  expectation could be satisfied by the *other* language's rows — the fixture would beg the question.
- **Declare states without executing the tools.** Cheapest and worthless: a declaration nothing runs
  is documentation. All 44 cells execute, and the whole file costs ~1.6 s.
- **Derive `kinds` per tool from source** instead of declaring it. Attractive (R6.7) but not
  available: `include_graph` names `INCLUDES` in a module constant, `find_references` reads
  `contract.UNMODELLED_REFERENCE_KINDS`, and `class_diagram` filters kinds inline. Declaring the
  kinds and **checking them against the graph** gets the anti-drift property without inventing a
  parser for the core.
- **Fix the `find_orphans` crash here.** Out of scope; filed as **187** with the red run attached.

### Assumptions

| Assumption | Tag |
|---|---|
| The spec fixtures alone drive all 22 tools | **verified by measurement** — all 44 cells execute, none declared-only |
| Entry points are path globs, not qnames | **verified the hard way** — a qname-shaped entry point crashed `find_orphans`; see 187 |
| `cli.availability` can be reused as the cell's skip mark | verified — `_params()` attaches it, and `0 skipped` on this host proves the columns ran |
| Adding a language needs no body edit | verified by red run E: a registered adapter with no column fails |
| No `code_atlas/` change is needed | verified — the diff is test-side and docs only |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| The matrix: states, `Expect`, `Invoker`, `INVOKERS`, two language columns | `tests/contract/tool_parity.py` (new) | data + one call table | R1, R2, R4, AC1–AC5 | 1/1 |
| The body: 6 guards + the executed matrix | `tests/contract/test_tool_parity.py` (new) | new file | R3, AC1–AC5 | 1/1 |
| A new ticket for the crash the matrix found | `docs/tasks/187_*.md`, BACKLOG | new row | — | 1/1 |
| BACKLOG; ledger; LESSONS; working doc | `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `prove-the-guard-fails` (R6.5) — **traced.** Five red runs recorded below.
- `one-rule-for-every-subject-slot` (R1.8) — **traced, and it found a live defect.** Two consumers of
  one walk disagreed about the empty case:

  ```
  $ grep -n 'retain_temps' code_atlas/store.py | head -3
  1662:        if not ordered_seeds:            # reachable_from returns BEFORE creating the temps
  1851:        reach = self.reachable_from(seeds, ..., retain_temps=True)
  1861:            "INSERT OR IGNORE INTO temp.reach_excluded (qname) SELECT qname FROM temp.reach_seen"
  ```

  `reachable_from` answers empty; `find_orphans` raises. Filed as **187**, not fixed here.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (real builds, 44 executed cells) | the matrix + red run A | ✅ |
| AC2 | guard (declaration completeness, emptiness) | red runs B, C, E | ✅ |
| AC3 | guard (a registered adapter with no column) | red run E | ✅ |
| AC4 | analysis (verdict) + integration (`answers_without` checked against the graph) | recorded verdict + red run D | ✅ |
| AC5 | suite output (`0 skipped`) + the availability mark | measured below | ✅ |
| AC6 | guard (grep-gate) | `gate.sh` | ✅ |
| AC7 | measurement | measured below | ✅ |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **R6.3 / `fixture-shape-begs-the-question` — recorded.** The matrix proves the tools answer over
  each language's **spec fixtures**, not over a real repo of that language. A TS repo with a build
  step, path aliases and `node_modules` may still produce answers these fixtures cannot exhibit.
  Mitigated, not removed, by using the R6.2 spec inventory rather than authored-for-this-test files.
  **Expiry:** `cross_repo_validate.py` already pins three real TS repos (150) — extending it to call
  tools rather than only count rows is the natural next step and is a separate ticket.

### Proving test

`tests/contract/test_tool_parity.py::test_tool_parity` (44 cells) — `[typescript:include_graph]` is
the one that carries the original report.

### Rollback + porting

Rollback: delete two test files and the 187 ticket row. No source change, so nothing to revert in
`code_atlas/`. Porting: `app` only.

### SCOPE

`SCOPE: M` — two test-side files, no core change; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Expectations as data; body never edited to add a language | implemented-as-approved (red run E proves it) |
| Five states, each with a checkable obligation | implemented-as-approved |
| `INVOKERS` derived against `TOOL_NAMES` (R6.7) | implemented-as-approved |
| Reuse each language's R6.2 spec fixtures; no new fixtures | implemented-as-approved |
| Module-scoped builds; all 44 cells execute | implemented-as-approved |
| `cli.availability` reused as the skip mark | implemented-as-approved |
| No `code_atlas/` change | implemented-as-approved |

No deviations. Diff ⊆ approved list. **One departure from an AC's literal wording** (AC4) is recorded
above with the measurement that forced it — a recorded deviation, not a silent one.

### Empirical outputs

**The measurement that drove every declaration** — 22 tools over each language's real graph:

```
php:        24 files / 190 nodes / 301 edges / kinds: ALIASES CALLS CONTAINS EXTENDS IMPLEMENTS
                                                      IMPORTS INCLUDES NEW REFERENCES USES_TRAIT
typescript: 30 files /              kinds: ALIASES CALLS CONTAINS EXTENDS IMPLEMENTS IMPORTS NEW
php        : 22 tool calls in 0.11s
typescript : 22 tool calls in 0.22s
```

The three empties are `find_view_data` / `check_architecture_rules` / `diff_architecture` on **both**
languages, and `include_graph` on TS only. Everything else answers on both.

**Five red runs (R6.5):**

```
A. typescript:include_graph declared `answers`  (the naive parity expectation)
   E  typescript:include_graph is declared answers but results is empty; reason='no_matches'
   1 failed, 94 passed
B. one tool declaration removed from the TS column
   E  typescript: undeclared ['find_view_data'], unknown []
   2 failed, 91 passed
C. PARITY emptied
   E  no languages declared — the parity matrix would be vacuously green
   E  every conformance-registered adapter must declare a tool-parity column: missing ['php', 'typescript']
   2 failed, 2 passed, 4 skipped
D. a rubber-stamp `answers_without` naming a kind the graph DOES hold
   E  typescript:class_diagram claims the answer is shaped by a missing CALLS,
      but this language's graph holds CALLS edges
   1 failed, 94 passed
E. a hypothetical adapter #3 registered for conformance with no parity column   (AC3)
   E  every conformance-registered adapter must declare a tool-parity column: missing ['hypothetical']
   1 failed, ...
```

**D is the one worth reading.** Without it, `answers_without` would be a comment: any cell could
claim any missing kind and stay green. C shows the emptied matrix does not read as green.

**AC5 — the TS column runs for real:** `95 passed in 1.61s`, **`0 skipped`**, on this host with Node
and `npm install` present. Without Node, `cli.availability` marks every TS cell `skipped` — the
`0 skipped` line is the evidence the column ran, exactly as C3 requires.

**AC7 — added wall-clock, measured:**

```
$ .venv/bin/pytest -q tests/contract/test_tool_parity.py --durations=4
1.06s setup  (the two module-scoped full_build calls)
0.50s call   typescript:build_or_update_index
0.37s call   php:build_or_update_index
0.01s call   php:explain_path
95 passed in 2.46s
```

**~1.6–2.5 s for the whole file**, of which 1.06 s is the two builds and 0.87 s is the two
`build_or_update_index` cells (which by their nature run an incremental build). The remaining 42
cells cost about 0.01 s each. Full-suite wall-clock is unchanged within run-to-run noise.

**A live defect found, and filed rather than fixed:** `find_orphans` raises
`OperationalError: no such table: temp.reach_seen` when `CA_ENTRY_POINTS` resolves to zero seeds —
reproduced in a fresh process on **both** languages. It is the first time any test asked
`find_orphans` a question over a real graph with entry points configured. Root cause traced to
`store.py:1662` (early return before the temps exist) vs `:1861` (read of those temps). Filed as
**187**; out of 185's scope, and the matrix uses a resolving glob so it covers the tool's real path.

**Green run:**

```
$ .venv/bin/pytest -q
2355 passed in 122.02s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_tool_parity` (44 cells) + red run A: `[typescript:include_graph]` fails the moment parity is naively assumed |
| AC2 | `test_every_tool_is_declared_for_every_language` (red B), `test_the_parity_matrix_is_non_empty` + `test_the_matrix_covers_exactly_the_registered_adapters` (red C) |
| AC3 | red run E — a conformance-registered adapter with no column fails; the body is untouched by adding a column |
| AC4 | **departure recorded** (see verdict): `answers_without` + `kinds` + `because`, checked against the graph; `test_each_declaration_is_well_formed` requires the reason, red D proves the kind check bites |
| AC5 | `95 passed, 0 skipped` with Node; `cli.availability` on every cell; `test_no_language_is_silently_skipped` |
| AC6 | `gate.sh` R1.1 green, and no `code_atlas/` file is in the diff |
| AC7 | the `--durations` output above; ~1.6–2.5 s |
| — | `test_the_two_languages_disagree_somewhere_and_that_is_the_point` — a matrix whose columns are identical proves nothing, so that is asserted too |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2260 passed / 0 failed` at `bbec170` →
`2355 passed / 0 failed`, `0 skipped`. ruff + mypy green. `scripts/gate.sh` → `GATE GREEN`.

### Learning loop

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen >= 2 | 0 routed to a destination | 0 cannot promote (reason) | 2 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `prove-the-guard-fails` (R6.5) gains 185: five red runs, and red D is the one that turned
  `answers_without` from a comment into an assertion.
- `fixture-shape-begs-the-question` (R6.3) gains 185, recorded as an exclusion with an expiry.
- **New:** `185-C1` (type-2, `a-declared-state-needs-a-checkable-obligation`) — a test matrix whose
  cells are labels is documentation; give every state an obligation derived from the world (here: the
  graph's actual edge kinds), so a wrong declaration fails rather than passing quietly. seen=1.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. Self-checks: two of the
ticket's three predicted gaps disproved by measurement before any declaration was written, an AC
departure recorded with the evidence that forced it, five red runs, a live crash found and filed as
187 rather than absorbed, and the per-run cost measured rather than estimated.
