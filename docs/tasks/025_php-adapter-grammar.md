---
id: 025
slug: php-adapter-grammar
title: PHP adapter — full 8.5 grammar coverage
phase: 1
milestone: M0
status: done
depends_on: [007]
---

## Goal
Close the construct gap the task 006 spike left, so the adapter covers the **full PHP 8.5 grammar**
(§6, R2.1) rather than the subset two fixtures happened to reach.

Split out of task 007 at its Gate 0: 007 shipped the streaming protocol, which alone unblocks 008 and
009. This card carries the language coverage, which only task 012 waits on.

## Scope / Deliverables

Task 007's analysis built a **42-construct inventory** by expanding the language spec, not the
ticket's prose; 18 were already satisfied by the 006 spike. The 23 below are what remain. Each is one
per-item row — review confirms **every** one, not a total.

**Nodes**
- Backed enums: capture `Enum_::$scalarType` (a pure enum must stay distinguishable from a backed one).
- Anonymous classes (`namespacedName` is `null`, so the spike skips them entirely).
- Property declared types (`Stmt\Property::$type` — today only params carry a type).
- Promoted constructor properties (`Node\Param::$flags != 0`).
- Property hooks (PHP 8.4, `Node\PropertyHook`).
- `ClassConst` modifiers (`final`, visibility) and typed class constants.
- Enum cases (`Stmt\EnumCase`) — **as `ClassConst`**, see the decision below.
- Closures (`Expr\Closure`) and arrow functions (`Expr\ArrowFunction`).
- Global `const` (`Stmt\Const_`) → the `Const` node kind, which the contract reserves and nothing emits.

**Edges**
- `USES_TRAIT` from `Stmt\TraitUse` — a trait used by a class currently produces **no edge, silently**.
- Trait adaptations (`insteadof` / `as` aliasing).
- `CALLS` from `Expr\NullsafeMethodCall` (`$o?->m()`) — a class distinct from `MethodCall`.
- First-class callables `f(...)` distinguished from a call (`CallLike::isFirstClassCallable()`).
- `NEW` for anonymous classes, and `new $var` as `DYNAMIC` (R5.2).
- `IMPORTS`: aliases (`UseItem::$alias`), function/const import types (`Use_::TYPE_*`), and
  `Stmt\GroupUse` including mixed-type group use.

**Other**
- Attributes captured raw on declarations, into the node `extra` field (`contract.NODE_FIELDS` has no
  `attributes` field). Raw name + args only — framework *meaning* is the Phase-2 enrichment layer (R2.3).

## Decisions inherited from task 007's Gate 0

These were ratified by the user on 2026-07-31 and are **not** re-open questions:

- **Anonymous declarations use line-anchored qualified names** — `\Ns\Class::method::{closure@42}`,
  `\Ns::{class@17}`, `path.php::{fn@8}`. The start line is a pure function of the file's own text, so
  it satisfies R4.2; unlike an ordinal, inserting one closure does not rename every later one. Add a
  `:col` suffix only if two anonymous declarations are ever found opening on the same line.
- **Enum cases reuse the `ClassConst` node kind**, with enum-ness recorded in `extra`. This avoids a
  `CONTRACT_VERSION` bump — PLAN §4.4 reserves v2 for task 019 — and matches PHP's own reflection
  hierarchy, where `ReflectionEnumUnitCase extends ReflectionClassConstant`.

## Acceptance criteria
- Each construct above is asserted over a spec-driven fixture (R6.1, R6.2) — **in this task**, not
  deferred. Task 012 owns the cross-adapter conformance matrix (R3.4), not this ticket's correctness.
- "Correct" means: for each construct, the emitted rows match an expected
  `(kind, qualified_name, [modifiers/params/extra])` tuple, `contract.validate()` returns `[]`,
  `ok` is `true`, and `nodes` is non-empty — a valid but empty result proves nothing.
- No repo/framework names in adapter source (grep-gate clean, R2.2).
- No `CONTRACT_VERSION` bump (both vocabulary decisions above were chosen to avoid one).

## References
Plan §6, §7, §2. Task 007's working doc carries the full 42-row inventory with the current state of
each row measured by running the adapter, plus the citations for why nullsafe calls, property hooks
and global `const` are in scope despite not being named in 007's original prose.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 025 — PHP adapter — full 8.5 grammar coverage (working doc)

- **Ticket:** 025 · [docs/tasks/025_php-adapter-grammar.md](025_php-adapter-grammar.md) (raw above separator)
- **Type:** enhancement
- **Repo(s) / Porting:** `app` (`.`) only
- **SCOPE:** L
- **STRUCTURE:** native
- **TRACK:** backend — 0/N touched files under UI paths
- **TIER:** full
- **BASELINE:** green — `.venv/bin/python -m pytest -q` → **398 passed** in 20.45s (untouched `3322718`)
  <!-- baseline exclusions: none -->
- **work_doc_mode:** `embed` → this doc lives below the separator in the ticket file itself (harness `work_doc_mode: embed`)

---

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`

Checked as existing: `docs/tasks/007_php-adapter-visitor.md` (42-row inventory), `adapters/php/src/Visitor.php`, `code_atlas/contract.py` (`NODE_FIELDS` / `Const` kind), Plan §6/§7/§2, R2.1. To-be-created deliverables (fixtures/assertions) do not count as missing.

`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

`refine skipped: 0 unresolved product-decisions` — Gate-0 decisions H1/H3 already user-ratified (2026-07-31); the 23/19 construct list is an AC-count mismatch for analysis, not a product-direction ask; encoding of adaptations/FCC/hooks without a contract bump is analysis/design HOW (direction already constrained by AC “No `CONTRACT_VERSION` bump”).

**INPUT KIND:** ticket (single deliverable — not an epic).

**Exposure-checker:** skipped (refine skip path).

---

## Requirements matrix

`SECTIONS: 5 found (Goal, Scope / Deliverables, Decisions inherited, Acceptance criteria, References) | 5 decomposed | ROWS: C=2 R=4 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | Close the construct gap so the adapter covers the **full PHP 8.5 grammar** (§6, R2.1) | Emit correct contract nodes/edges for every remaining grammar construct; protocol already shipped in 007 | `Visitor.php` covers named class-likes + subset of edges; 19 ❌ inventory rows among 1–41 (see Inventory) | CL#1 | | ❌ |
| R1 | Scope / Deliverables | The 23 below are what remain. Each is one per-item row | Counted **for-each-of-N** → Inventory rows I1–I19 (**N=19 ratified** at Gate 1; ticket “23” treated as stale) | 007 inventory `docs/tasks/007_php-adapter-visitor.md:151-194`; ticket bullets lines 24–46 | CL#2+#3 | | ❌ |
| R2 | Scope / Deliverables | Nodes: backed enums, anon classes, property types, promoted props, property hooks, ClassConst modifiers/typed, enum cases as ClassConst, closures/arrows, global Const | Implement each as contract nodes without new `NODE_KINDS` (hooks/enum-ness via `extra` / existing kinds) | Skips: anon at `Visitor.php:61-63`; no EnumCase/Const_/Closure/Arrow/PropertyHook/promoted; property type unread | CL#1 | | ❌ |
| R3 | Scope / Deliverables | Edges: USES_TRAIT, adaptations, NullsafeMethodCall, FCC≠call, NEW anon/`$var` DYNAMIC, IMPORTS alias/type/GroupUse | Implement each edge path; **EDGE_FIELDS has no `extra`** — adaptations/FCC encoding must use node `extra`, omit CALLS for FCC | No TraitUse/GroupUse/Nullsafe; New_ Name-only `Visitor.php:110`; Use_ drops alias/type | CL#1 | | ❌ |
| R4 | Scope / Deliverables | Attributes raw on declarations into node `extra` (no framework meaning) | Capture `attrGroups` → `extra.attributes` raw name+args (R2.3) | No attr path today | CL#1 | | ❌ |
| C1 | Decisions inherited | Anonymous qnames line-anchored (`::{closure@42}`, `::{class@17}`, `::{fn@8}`); `:col` only on same-line collision | Binding encoding for I2/I8/I9; R4.2 | Ticket lines 52–55; 007 H1 | CL#1 | | ✅ (constraint locked) |
| C2 | Decisions inherited | Enum cases reuse `ClassConst`; enum-ness in `extra`; no `CONTRACT_VERSION` bump | Binding for I7; forbids new kinds/fields | Ticket lines 56–58; 007 H3; R3.1 | CL#1+#3 | | ✅ (constraint locked) |
| AC1 | Acceptance criteria | Each construct above asserted over a spec-driven fixture **in this task**; 012 owns conformance matrix | One proving assertion per inventory item (R6.1/R6.2); not deferred to 012 | Ticket lines 61–62 | CL#2+#3 | | ❌ |
| AC2 | Acceptance criteria | “Correct” = expected `(kind, qname, [modifiers/params/extra])`, `validate()==[]`, `ok` true, `nodes` non-empty | Falsifiable per-item tuple tests (non-vacuity) | Ticket lines 63–65; 006/007 bar | CL#3 | | ❌ |
| AC3 | Acceptance criteria | No repo/framework names in adapter source (R2.2) | Grep-gate clean on authored adapter PHP | CI `guardrails` R2.2; must stay clean | CL#3 | | ❌ |
| AC4 | Acceptance criteria | No `CONTRACT_VERSION` bump | `CONTRACT_VERSION` stays `1`; no new NODE/EDGE kinds or fields | `contract.py:19` | CL#3 | | ❌ (constraint; prove unchanged) |

Status legend: ✅ done/proven · ⚠ deferred · ❌ not met.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 (denominator) | “The **23** below are what remain” | **N = 19** (ratified) — inventory ❌ rows 8,9,12,13,14,16,17,19,20,21,26,27,30,32,34,36,37,38,41 | **Y** (corrected) | measurable — inventory row ids | User approved Q1 option 1 (N=19); “23” is stale arithmetic |
| AC2 (“correct”) | pinned tuple + validate + ok + non-empty nodes | Same pinning; reusable from 007 | Y | measurable via pytest | — |
| AC3 (R2.2) | grep-gate clean | denylist `laravel\|symfony\|wordpress\|drupal\|magento` in authored adapters | Y | greppable | — |
| AC4 (no version bump) | no bump | `CONTRACT_VERSION == 1` pre and post; NODE_KINDS/EDGE_KINDS/FIELDS unchanged | Y | greppable / assert | — |

## Inventory (universal “all/every/no” — for-each construct)

- **Denominator / total N: 19** (ratified Gate 1) — remaining grammar ❌ rows from 007 inventory, excluding row 42 (protocol, done in 007).
- Regression of the **22** already-✅ grammar rows is covered by existing `tests/test_php_adapter_spike.py` / server suite — not re-listed here; must stay green vs BASELINE.

| # | Item (007 inventory #) | Ph3/4 proven by | Status |
|---|------------------------|-----------------|--------|
| I1 | Backed enum scalar type (8) | | ❌ |
| I2 | Anonymous class + H1 qname (9) | | ❌ |
| I3 | Property declared type (12) | | ❌ |
| I4 | Promoted constructor property (13) | | ❌ |
| I5 | Property hooks (14) | | ❌ |
| I6 | ClassConst modifiers + typed (16) | | ❌ |
| I7 | Enum case as ClassConst + extra (17) | | ❌ |
| I8 | Closure → Function, H1 qname (19) | | ❌ |
| I9 | Arrow function → Function, H1 qname (20) | | ❌ |
| I10 | Global `const` → Const (21) | | ❌ |
| I11 | USES_TRAIT from TraitUse (26) | | ❌ |
| I12 | Trait adaptations insteadof/as (27) | | ❌ |
| I13 | CALLS from NullsafeMethodCall (30) | | ❌ |
| I14 | FCC distinguished from call (32) | | ❌ |
| I15 | NEW anon class + `new $var` DYNAMIC (34) | | ❌ |
| I16 | IMPORTS alias (36) | | ❌ |
| I17 | IMPORTS function/const type (37) | | ❌ |
| I18 | IMPORTS GroupUse (38) | | ❌ |
| I19 | Attributes raw in node `extra` (41) | | ❌ |

### Surface inventory

`SURFACES: n/a — TRACK=backend`

## Clarifications

`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`

**Self-resolved (cited):**

- **S1 — Assertion site is this task, not 012.** Ticket AC lines 61–62 + R6.1; 012 owns R3.4 matrix only.
- **S2 — No new contract vocabulary.** AC4 + C2 + R3.1; encode hooks / enum-ness / adaptations / attributes via existing kinds + node `extra` (edges have **no** `extra` — `contract.py:68-76`).
- **S3 — FCC is not a CALLS edge.** Inventory “distinguished from a call” + `CallLike::isFirstClassCallable()`; do not emit plain CALLS for `f(...)` (design picks REFERENCES vs omit).
- **S4 — H1/H3 are locked.** Ticket “not re-open questions”; 007 Gate 0 2026-07-31.
- **S5 / Q1 — Denominator N=19.** User approved Recommended (2026-08-01): treat ticket/007 “23” as stale; checklist is I1–I19.

## Phase 1 — Analysis ✋ Gate 1

**Per-goal gap analysis (enhancement).**

| Goal | Current (`path:line`) | Target | Gap |
|------|------------------------|--------|-----|
| Full PHP 8.5 grammar (R2.1, §6) | `Visitor.php` named ClassLike + Property/ClassConst/Use_/New_(Name)/calls/Include_; skips anon (`:61-63`); no TraitUse/EnumCase/Closure/Const_/Nullsafe/GroupUse/attrs | Emit I1–I19 correctly under C1/C2/AC4 | **19 constructs** (N ratified); concentrated in Visitor enter paths |

**Handler / entry point + blast radius.**

- Entry: `adapters/php/src/Visitor.php` (primary), possibly small `Parser.php` untouched.
- Consumers: `tests/test_php_adapter_spike.py`, `tests/test_php_adapter_server.py`, indexer via `SubprocessAdapter` — must stay green (BASELINE 398).
- Contract: **read-only** under AC4 (no bump). `extra` on nodes is already legal.
- Not touched: `code_atlas/` core, store, resolver, tools (R1.1/R1.4).
- No `db-map` under `docs/`.

`TRACK: backend — 0/N touched files under UI paths`

`RULE SECTIONS: §1 ✅ · §2 ✅ · §3 ✅ · §4 ✅ · §5 ✅ · §6 ✅ · §7 ✅ · §8 N/A (no new adapter deps) — 7/7 applicable checked`

- **§1** ✅ — all work under `adapters/php/`; no core language branch; no new abstraction (R1.2).
- **§2** ✅ — R2.1 drives inventory; R2.2 → AC3; R2.3 → attributes raw only (R4).
- **§3** ✅ — R3.1/AC4 forbid vocabulary change; R3.3 bare edges; R3.4 deferred to 012.
- **§4** ✅ — R4.2 → C1 line-anchored qnames.
- **§5** ✅ — R5.2 → I13 HEURISTIC, I15 DYNAMIC for `new $var`.
- **§6** ✅ — R6.1/R6.2 → AC1/AC2 per-item fixtures.
- **§7** ✅ — R7.1/R7.2 status sync at finalise; R7.5 comments ≤3 lines.
- **§8** N/A — no new Composer deps expected (nikic already present).

**Encoding premises for design (HOW, not re-asked):** node `extra` for backed type, enum-ness, attributes, property type/hooks, IMPORTS metadata as needed; USES_TRAIT edges plain; adaptations on owning class/trait `extra` (no edge.extra); FCC ≠ CALLS.

**Self-audit:** sections 5=5 · AC table complete · BASELINE green · inventory N=19 ratified · RULE SECTIONS emitted · STRUCTURE native · TRACK backend · TIER full · **j=0**.

- **Gate 1 status:** cleared (Q1 → N=19 approved)

---

## Phase 2 — Design ✋ Gate 2

**Approach.** Extend `adapters/php/src/Visitor.php` only — add enter-paths for I1–I19 under the existing `declare`/`open`/`edge` helpers. Keep `CONTRACT_VERSION=1` and existing NODE/EDGE kinds/fields. Anything that is not already a first-class field (`modifiers`, `params`) goes in node `extra` (edges have no `extra`). Ship **one** spec-driven fixture that reaches every remaining construct, plus a new pytest module with **one assertion per inventory row** (R6.1/R6.2; review confirms every I-row). Drive proofs through the real PHP adapter (`--file`), same layer as task 006/007.

**Encoding map (HOW, locked by AC4/C1/C2/S2/S3):**

| I# | Emit |
|----|------|
| I1 | `Enum` node `extra.scalar_type` from `Enum_::$scalarType` |
| I2 | `Class` with H1 qname `\Ns\{class@L}` / `path::{class@L}` / `\Ns\C::m::{class@L}`; push scope even when `namespacedName` is null |
| I3 | `Property` `extra.type` via existing `typeName()` |
| I4 | On constructor `ClassMethod`, each `Param` with `$flags != 0` → `Property` node (`$name`, modifiers from flags) |
| I5 | `Property` `extra.hooks` = list of hook names (`get`/`set`); no new node kind |
| I6 | `ClassConst` `modifiers` + `extra.type` when typed |
| I7 | `ClassConst` for `EnumCase`; `extra.enum_case` = true (H3) |
| I8/I9 | `Function` nodes; H1 qnames `::{closure@L}` / `::{fn@L}`; capture params/`static` in modifiers when set |
| I10 | `Const` node from `Stmt\Const_` (global) |
| I11 | `USES_TRAIT` edge per trait name on `TraitUse` |
| I12 | Owning class/trait `extra.trait_adaptations` (alias / insteadof records) — no edge.extra |
| I13 | `CALLS` + `HEURISTIC`, same shape as `MethodCall` |
| I14 | If `CallLike::isFirstClassCallable()` → **emit no CALLS** (omit, not REFERENCES) |
| I15 | Anon `NEW` → target = anon class qname; `new $var` → `DYNAMIC`, `target_raw` = `(dynamic)` |
| I16–I18 | `IMPORTS` edges keep FQN `target_raw`; File `extra.imports[]` = `{fqn, alias, type}` for alias + function/const + GroupUse expansion |
| I19 | Declaration `extra.attributes` = `[{name, args}]` raw (R2.3) |

**Rejected alternatives.**

- **Bump `CONTRACT_VERSION` for `EnumCase` / `PropertyHook` kinds or edge `extra`.** Rejected by AC4/C2/R3.1; PLAN §4.4 reserves v2 for task 019.
- **Split I1–I19 across follow-up tickets.** Rejected — 025 *is* the split from 007; one Visitor change-list keeps the for-each inventory reviewable in one PR.
- **Only grow `namespaced.php` + spike tests.** Rejected — spike owns 006 shapes; grammar needs a dedicated fixture so every I-row is reachable (LESSONS 002 / R6.2).

**Assumptions**

| Assumption | verified / novel-untested | Spike / proving-test resolution |
|------------|---------------------------|----------------------------------|
| nikic exposes `Enum_::$scalarType`, `EnumCase`, `TraitUse`+adaptations, `PropertyHook`, `NullsafeMethodCall`, `GroupUse`, `UseItem::$alias`, `CallLike::isFirstClassCallable()`, anon `Class_` with `namespacedName=null` | **verified** | Live PHP spike (2026-08-01): JSON dump confirmed each shape against nikic ^5 |
| `contract.validate()` rejects unknown top-level node keys → metadata must live in `extra` / `modifiers` / `params` | **verified** | `contract.py:251-254` `_check_keys` |
| Existing spike assertions use `<=` on qname sets — adding `Status::Active` / File.extra does not break them; CALLS-all-HEURISTIC still holds if namespaced gains no new non-heuristic CALLS | **verified** | Read `tests/test_php_adapter_spike.py:74-156`; namespaced has no FCC/nullsafe today |

**Smallest change-list**

| # | Change | File/area | Ph2 covered by | k/N |
|---|--------|-----------|----------------|-----|
| 1 | Implement I1–I19 enter-paths + H1 qname helper + encoding map above | `adapters/php/src/Visitor.php` | G1, R2, R3, R4, C1, C2, AC2, AC4 | 8/11 matrix rows that need code |
| 2 | Spec-driven fixture reaching every I-row (one file or small cluster under `tests/fixtures/php/`) | `tests/fixtures/php/grammar*.php` (**new**) | R1, AC1, AC2 | 3/11 |
| 3 | Per-row proving tests: expected `(kind, qname, …)` + `validate()==[]` + `ok` + non-empty nodes; FCC asserts **no** CALLS at that site; R2.2 denylist grep on authored adapter PHP | `tests/test_php_adapter_grammar.py` (**new**) | R1, AC1, AC2, AC3, AC4 | 5/11 |
| 4 | **Proof collateral** — adjust spike/server only if a new emission breaks an exact assertion (enum case node, File.extra, USES_TRAIT if fixture edited) | `tests/test_php_adapter_spike.py` (± server) | AC2 regression vs BASELINE | collateral |
| 5 | **Proof collateral** — status sync frontmatter + BACKLOG row when landing | `docs/tasks/025_…md`, `docs/BACKLOG.md` | R7.2 | collateral |

Union of Ph2 column covers G1,R1–R4,C1–C2,AC1–AC4. Inventory I1–I19 each maps to change #1+#2+#3.

**Test blast-radius (producers/consumers).** Consumers of Visitor output: `test_php_adapter_spike.py`, `test_php_adapter_server.py`, indexer via SubprocessAdapter. Spike uses subset asserts (`<=`) for qnames — safe when enum cases appear. Exact CALLS confidence list on namespaced — do **not** add non-heuristic CALLS to that fixture. Server tests use the same fixtures for protocol, not exact node sets. No core type/symbol change → no Python typecheck fan-out.

**Rule compliance.** R1.1/R1.4 — adapter only. R2.1/R2.2/R2.3 — constructs + raw attributes + no framework names. R3.1/AC4 — no vocabulary bump. R4.2 — H1 line-anchored qnames. R5.2 — HEURISTIC nullsafe / DYNAMIC `new $var`. R6.1/R6.2 — fixture + per-construct asserts. R7.5 — comments ≤3 lines. CONVENTION §3 — leading `\` FQNs + `::` members.

**Verification plan**

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 (each of 19) | integration (real PHP parse) | integration — parametrized tests over I1–I19 via `--file` | ✅ |
| AC2 (tuple + validate + ok + nodes) | integration | same tests assert tuple + `contract.validate()` | ✅ |
| AC3 (R2.2) | logic (authored source grep) | unit — grep denylist over `adapters/php/src` excluding vendor | ✅ |
| AC4 (no version bump) | logic | unit — assert `CONTRACT_VERSION==1` and NODE/EDGE field tuples unchanged | ✅ |
| C1/C2 | integration | H1/H3 tuples inside AC1 rows I2/I7/I8/I9 | ✅ |

**Coverage-gap exclusions:** none.

**Proving test.** `tests/test_php_adapter_grammar.py` — parametrized (or one named test per I-row) asserting each construct’s expected tuple against the grammar fixture via the real adapter. **Fails pre-change** (missing nodes/edges); **passes post-change**. Invocation: `.venv/bin/python -m pytest tests/test_php_adapter_grammar.py -q`.

**Rollback.** Revert the branch / Visitor + new fixture/test files; no DB/schema/contract migration. **Porting:** single repo `app` only.

**SCOPE confirmed:** L (19 constructs, one Visitor surface — unchanged from analysis).

- **Gate 2 status:** cleared (user approved 2026-08-01)

---

## Phase 3 — Execute

- **Branch:** `feat/025-php-adapter-grammar`
- **Commits:** `8602a65` — Cover the remaining PHP 8.5 grammar constructs in the adapter.
- **Proving test added:** `tests/test_php_adapter_grammar.py` — 19 per-row tests + AC3/AC4 + non-empty validate
- **Verification sweep — BOTH axes.**
  - *File axis:* diff ⊆ approved list ✅ (Visitor.php, grammar.php, test_php_adapter_grammar.py, BACKLOG + task frontmatter). Zero stray refs ✅. Spike/server untouched (no collateral needed) ✅.
  - *Behaviour axis:*

  | Approved Gate-2 bullet | Classification | Notes |
  |------------------------|----------------|-------|
  | Extend Visitor only for I1–I19 under declare/open/edge | implemented-as-approved | `adapters/php/src/Visitor.php` |
  | Metadata in node `extra`; no contract bump | implemented-as-approved | AC4 tests lock vocabulary |
  | One grammar fixture + per-row pytest | implemented-as-approved | `grammar.php` + I1–I19 tests |
  | Real PHP `--file` proofs | implemented-as-approved | same harness as 006 |
  | Encoding map (FCC omit CALLS, File.extra.imports, adaptations, hooks, H1/H3) | implemented-as-approved | verified live dump before tests |

- **Design-conformance deviations:** none
- **Design-invalidation / re-gate:** none
- **Full suite:** 420 passed (was BASELINE 398; +22 grammar/AC tests)

**Inventory Ph3/4 proven by (delta):**

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| I1 | Backed enum scalar type | `test_i1_backed_enum_captures_scalar_type` | ✅ |
| I2 | Anonymous class + H1 qname | `test_i2_anonymous_class_uses_line_anchored_qname` | ✅ |
| I3 | Property declared type | `test_i3_property_declared_type_is_captured` | ✅ |
| I4 | Promoted constructor property | `test_i4_promoted_constructor_property_is_emitted` | ✅ |
| I5 | Property hooks | `test_i5_property_hooks_are_listed_in_extra` | ✅ |
| I6 | ClassConst modifiers + typed | `test_i6_class_const_modifiers_and_type_are_captured` | ✅ |
| I7 | Enum case as ClassConst | `test_i7_enum_case_is_a_class_const_with_enum_flag` | ✅ |
| I8 | Closure → Function | `test_i8_closure_is_a_function_with_line_anchored_qname` | ✅ |
| I9 | Arrow → Function | `test_i9_arrow_function_is_a_function_with_line_anchored_qname` | ✅ |
| I10 | Global/file `Const` | `test_i10_file_level_const_uses_the_const_node_kind` | ✅ |
| I11 | USES_TRAIT | `test_i11_trait_use_emits_uses_trait_edges` | ✅ |
| I12 | Trait adaptations | `test_i12_trait_adaptations_are_on_the_owning_class` | ✅ |
| I13 | Nullsafe CALLS | `test_i13_nullsafe_method_call_is_a_heuristic_call` | ✅ |
| I14 | FCC ≠ CALLS | `test_i14_first_class_callable_emits_no_calls_edge` | ✅ |
| I15 | NEW anon + DYNAMIC | `test_i15_new_anonymous_and_dynamic_variable` | ✅ |
| I16 | IMPORTS alias | `test_i16_import_alias_is_recorded_on_the_file_node` | ✅ |
| I17 | IMPORTS function/const type | `test_i17_function_and_const_import_types_are_distinguished` | ✅ |
| I18 | IMPORTS GroupUse | `test_i18_group_use_including_mixed_types_is_expanded` | ✅ |
| I19 | Attributes raw | `test_i19_attributes_are_raw_on_the_declaration` | ✅ |

Matrix Ph3/4: G1/R1–R4/AC1–AC4 → `tests/test_php_adapter_grammar.py` ✅ (pending review confirm)

---

## Decision log

| When | Decision |
|------|----------|
| Gate 1 | **Q1:** N=19 ratified (user approved Recommended); ticket/007 “23” is stale arithmetic |
| Design | FCC → omit CALLS (not REFERENCES); IMPORTS metadata on File `extra.imports`; adaptations on class `extra.trait_adaptations`; property hooks in `extra.hooks` |
| Gate 2 | Approach + change-list approved (user 2026-08-01) |

---

## Cost ledger (dispatch only)

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 1 — analysis | extractor (`3480a9ab`) — 007 inventory + Visitor + contract extract | 1 | unmeasured (blocking retrieval) |
| 4 — review | `mango:reviewer` (`529061cb`) | 1 | unmeasured (blocking retrieval) |
| 4 — review | `mango:challenger` (`cd853272`) | 1 | unmeasured (blocking retrieval) |

---

## Phase 4 — Review

- **Round 1 — reviewer:** CHANGES REQUESTED (conditional LGTM once findings 1–3 land)
  1. C1 same-line anon qname collision — fixed (`anonymousOccurrences` + `:n` suffix; NEW peeks without register)
  2. IMPORTS edge line per-statement regression — fixed (`$use->getStartLine()`)
  3. ruff E501 on separator comment — fixed
- **Round 1 — challenger (ticket-blind):** 22/23 met · 1 can't-tell (pure vs backed enum distinguishability unasserted) · ACs met. Pure-enum assertion added in verify-only.
- **Round 2 — verify-only (main-loop, no re-dispatch):** findings 1–3 present as described; `tests/test_php_adapter_grammar.py` + spike **35 passed**; full suite **421 passed**; ruff clean on new test file; multi-line group-use IMPORTS lines = 3,4,5.
- **Scope reconciliation:** file ⊆ list ✅ · behaviour: H1 collision completed (ordinal `:n` on clash, not source column — same uniqueness intent as C1) ✅
- **Proving test:** green vs BASELINE 398 → 421 (delta-green)
- **Inventory:** I1–I19 all ✅ (19/19)
- **Clean:** yes

**Reviewed at** `f627152`  
**Reviewed files:** `adapters/php/src/Visitor.php`, `tests/fixtures/php/grammar.php`, `tests/test_php_adapter_grammar.py`, `docs/BACKLOG.md`, `docs/tasks/025_php-adapter-grammar.md`  
**Working-doc path (exempt):** `docs/tasks/025_php-adapter-grammar.md`

---

## Session status

- **Phase:** 5 finalise — outward actions in progress (A/B/C approved)
- **Branch:** `feat/025-php-adapter-grammar`
- **Reviewed at:** `f627152` (working-doc bump after marker is exempt)
- **Status:** done (frontmatter + BACKLOG)
