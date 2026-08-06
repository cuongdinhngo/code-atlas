---
id: 029
slug: php-receiver-resolution
title: PHP adapter — resolve $this / self / static / parent call receivers
phase: 1
milestone: M2
status: done
depends_on: [011, 025]
---

## Goal
Move the large, knowable class of instance/scope calls out of `HEURISTIC` into `RESOLVED` by naming
the receiver's type when one file already determines it — `$this->`, `self::`, `static::`, `parent::`
— so `find_callers` on those edges reports fact, not a name-match guess (§8.2). This is a PHP-standard
language fact (the enclosing class is lexically known), not a repo-specific rule (R2).

## Scope / Deliverables
- In the PHP adapter's visitor, when a method/static call's receiver is lexically bound to the
  enclosing class, emit `CALLS` with `target_raw = <EnclosingClassFQN>::<method>` at the **default**
  (RESOLVED-eligible) tier instead of the current unconditional `HEURISTIC`:
  - `$this->m()` / `$this?->m()` → `EnclosingClass::m` (only inside a class scope).
  - `self::m()` / `static::m()` → `EnclosingClass::m`.
  - `parent::m()` → resolve against the parent class FQN (from the `extends` clause) when the adapter
    knows it in-file; otherwise leave as today.
- The **core resolver is unchanged**: it already upgrades a unique FQN match to RESOLVED and honours
  inheritance via cross-file qname lookup, so the whole win is an adapter-side `target_raw` rewrite.
- Arbitrary `$x->m()` (receiver not lexically the enclosing class) stays `HEURISTIC`; `$x->$m()`
  stays `DYNAMIC`. No type inference of properties/params in this task (that is a separate follow-up).

## Constraints
- Only rewrite when the enclosing class is unambiguous at the call site — a call in a free function,
  closure without `$this` binding, or trait used by unknown classes must NOT fabricate a receiver.
  A trait's `$this->m()` resolves within the trait's own members; cross-class trait resolution is the
  core resolver's job, not a guess here.
- Never claim RESOLVED for a receiver one file cannot know (R5.2) — the tier stays the resolver's
  weaker-of choice; the adapter only stops *pre-downgrading* to HEURISTIC.
- Zero language branches leak into the core (R1.1); this is entirely inside `adapters/php/`.
- No contract vocabulary change — `CALLS` and existing tiers only, so no `contract_version` bump.

## Acceptance criteria
- Conformance fixtures: `$this->`, `self::`, `static::`, `parent::` calls emit
  `<ClassFQN>::method` and, after resolve, link `RESOLVED` to the correct declaration (including a
  method inherited from a parent class in another file) — asserted on the resolved `edges` rows.
- A negative fixture proves `$x->m()` and `$x->$m()` are unchanged (HEURISTIC / DYNAMIC), and a
  `$this->m()` inside a trait does not fabricate a false receiver.
- Before/after on a fixture repo shows a measurable drop in HEURISTIC `CALLS` with no RESOLVED edge
  pointing at the wrong declaration (pairs with task 028's health counts).
- Full contract-conformance + resolver + PHP coverage suites pass.

## References
Plan §8.2 (instance CALLS / receiver, tier rules), §6 (PHP standard, not a repo). `R5.2`, `R1.1`, `R2`.
`adapters/php/src/Visitor.php` (`enterInstanceCall` line ~342, `enterNamedCall`); `code_atlas/resolver.py`.
Feedback origin: external review Top-3 #1 ("resolve the receiver types you already know"). Highest
single-change leverage; prerequisite for trustworthy reachability (task 031).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 029 — PHP adapter — resolve $this / self / static / parent call receivers (working doc)

- **Ticket:** 029 · local `docs/tasks/029_php-receiver-resolution.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app — `adapters/php/` (+ tests/fixtures/docs)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full (universal receiver forms N=4)
- **BASELINE:** green — `578 passed in 22.92s`

---

## Phase 0 — Refine

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 1 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Settled wants:** AC3 bar = exact hand-count on planted fixture (option 1 — recommended; ratified by standing approval 2026-08-03).

**HOWs:** static→enclosing class; trait `$this`→trait FQN not consumer; core/resolver/contract unchanged.

**Exposure-checker:** [challenger](3a242c02-ae14-47ac-974b-00ca86317add) `EXPOSURE: 0`

---

## Requirements matrix

`SECTIONS: 5 found (Goal, Scope / Deliverables, Constraints, Acceptance criteria, References) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=4`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 | Status |
|----|--------|------------------|----------------|--------------|-----|-------|--------|
| G1 | Goal | Move knowable instance/scope calls from HEURISTIC→RESOLVED via lexical receiver | Adapter rewrites `target_raw` to `ClassFQN::method` | Visitor.php:342-348 | CL1 | ✅ | ✅ |
| R1 | Scope | `$this` / `self` / `static` / `parent` rewrite rules | Four forms; parent only when extends known in-file | Ticket bullets | CL1 | ✅ | ✅ |
| R2 | Scope | Core resolver unchanged; win is adapter `target_raw` | No resolver.py edit | resolver already FQN-links | CL1 | ✅ | ✅ |
| R3 | Scope | `$x->m` HEURISTIC; `$x->$m` DYNAMIC; no type inference | Negatives unchanged | enterReference Identifier-only | CL1–2 | ✅ | ✅ |
| R4 | Scope | Entirely in adapters/php; no contract bump | R1.1 / R3 | | CL1 | ✅ | ✅ |
| C1 | Constraints | No fabricate outside unambiguous class scope; trait = trait members | enclosingClassLike helper | | CL1 | ✅ | ✅ |
| C2 | Constraints | Never claim RESOLVED beyond what file knows; tier = weaker-of at resolve | Omit HEURISTIC pre-downgrade only | | CL1 | ✅ | ✅ |
| C3 | Constraints | Zero language branches in core | adapters/php only | | CL1 | ✅ | ✅ |
| C4 | Constraints | No contract vocabulary change | CALLS + tiers only | | CL1 | ✅ | ✅ |
| AC1 | AC | Fixtures emit ClassFQN::method; resolve RESOLVED incl. inherited parent other file | integration | | CL2–3 | ✅ | ✅ |
| AC2 | AC | Negatives: `$x->m`, `$x->$m`, trait no false receiver | | | CL2 | ✅ | ✅ |
| AC3 | AC | Exact hand-count HEURISTIC CALLS drop; no wrong RESOLVED | settled want #1 | | CL3 | ✅ | ✅ |
| AC4 | AC | Full contract + resolver + PHP coverage pass | | | CL* | ✅ | ✅ |

## AC validation

| AC | Ticket | Computed | Match | Falsifiable |
|----|--------|----------|-------|-------------|
| AC1 | ClassFQN::method + RESOLVED incl. cross-file parent | Plant Child extends Parent; parent::m → `\Parent::m` RESOLVED | Y | yes |
| AC2 | negatives unchanged | assert shapes | Y | yes |
| AC3 | measurable drop | exact N rewritten sites leave HEURISTIC | Y (want #1) | yes |
| AC4 | suites pass | regression | Y | yes |

## Inventory N=4

1. `$this` / `$this?->`  2. `self::`  3. `static::`  4. `parent::`

## Clarifications

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human` — want #1 ratified by standing approval as option 1.

---

## Phase 1 — Analysis ✋ Gate 1

- **Gap:** `enterInstanceCall` always HEURISTIC+bare name; `self::` → `\self::method` via fqn(). Need lexical rewrite to enclosing ClassLike FQN; parent from Class_ extends.
- **Blast:** `adapters/php/src/Visitor.php`; conformance shapes `STATIC_VS_INSTANCE_EDGE_SHAPES`; new fixtures/tests; PLAN §8.2 one-liner optional.
- **RULE SECTIONS:** R1.1 ✅ · R2 ✅ · R3 (no bump) ✅ · R5.2 ✅ · R6.1/R6.2 ✅ · DB/UI N/A
- **Gate 1:** cleared — standing approval 2026-08-03

---

## Phase 2 — Design ✋ Gate 2

- **Approach:**
  1. Add `enclosingClassLikeQname()` / `enclosingParentQname()` walking `$this->scope` for `ClassLike` / `Class_::extends`.
  2. `$this`/`$this?->` + Identifier method → `owner::method` at default tier when owner known; else keep HEURISTIC bare name.
  3. `self`/`static` StaticCall → enclosing ClassLike FQN::method; `parent` → extends FQN::method when known, else leave `\parent::…` as today.
  4. Update `static_vs_instance` golden; add receiver fixture + PHP proving test (parse + full_build resolve); hand-count HEURISTIC drop.
- **Rejected:** Type-infer `$x` / property types — out of scope. Resolver changes — ticket forbids.
- **Assumptions:** nikic `Variable` name `'this'` for `$this`; `Name::toString()` is `self`/`static`/`parent` (case-insensitive). **verified** (AST / php-parser). `$x->$m` currently emits no CALLS (Identifier guard) — leave unchanged (**verified** code).

| Change | File | Blast | Ph2 | k/N |
|--------|------|-------|-----|-----|
| 1. Lexical receiver rewrite | `adapters/php/src/Visitor.php` | all PHP CALLS edges | G1,R1–R4,C1–C4 | 9/9 |
| 2. Fixtures + golden shapes | `tests/fixtures/php/*`, `test_adapter_conformance.py` | R6.2 inventory | AC1–AC3 | 3/3 |
| 3. Proving tests (parse + resolve) | `tests/test_php_receiver_resolution.py` (new) | PHP/resolver suites | AC1–AC4 | 4/4 |
| 4. PLAN §8.2 note | `docs/PLAN.md` | readers | G1 | 1/1 |

- **Proving test:** `tests/test_php_receiver_resolution.py::test_lexical_receivers_resolve_to_enclosing_class_fqn`
- **Verification:** AC1–3 integration (real PHP adapter) ✅ · AC4 regression ✅
- **Gate 2:** cleared — standing approval 2026-08-03

---

## Phase 4 — Review ✋ (stop only if not clean)

**Reviewed at** `633bcfc2ca513277e0825c51846c0fdbeab0dedb` (code). Tip after bookkeeping: `9c2f166` (docs only). Working-doc path: `docs/tasks/029_php-receiver-resolution.md` (exempt from stale-review).

| Dispatch | Verdict |
|----------|---------|
| mango:reviewer round 1 ([Reviewer](f103d9ae-a28d-496f-9726-c4b2e71e202c)) | **CHANGES REQUESTED** — `enclosingParentQname` walked past innermost Class_ |
| mango:challenger round 1 ([Challenger](e18faac6-79cc-49ca-8eb9-37229de87fd1)) | ticket-blind — **11 met · 1 not met** (cross-file parent AC) · 0–1 can't tell |
| mango:reviewer round 2 verify ([Reviewer](a0efdaca-534d-46be-92c6-e26619e8be31)) | **LGTM** — parent walk fixed; NestedOuter + cross-file Base proven |
| mango:challenger round 2 ([Challenger](745dc7a6-b121-4d52-b8d7-c7445c33cc33)) | ticket-blind — **8 met · 0 not met · 2 can't tell** (soft AC3↔028; full suite not re-run in that pass — main ran **581**) |

### Reviewer detail round 1 ([Reviewer](f103d9ae-a28d-496f-9726-c4b2e71e202c)) @ `a2daf28`

- **Verdict:** CHANGES REQUESTED (conditional LGTM once finding 1 lands)
- **Finding 1 — Important · `Visitor.php:400-409`:** `enclosingParentQname()` skipped innermost `Class_` with `extends === null` and kept walking outward. Nested anonymous classes without a parent then inherited an *outer* class’s extends FQN → false RESOLVED-eligible receiver. Violates **R2.1**, **R5.2**, ticket **C1**.
- **Required fix:** stop at innermost `Class_`; return null when no extends; regression assert that nested anon without extends keeps `\parent::…`.
- **Scope vs approved list:** Visitor / fixtures+golden / proving tests / PLAN §8.2 — all match (modulo finding 1). No `code_atlas/` / contract / resolver edits.
- **Verified OK:** `$this`/`self`/`static` → enclosing FQN default tier; trait `$this` → trait FQN; `$x->m` HEURISTIC; `$x->$m` no CALLS; trait `parent::` left as `\parent::…`; proving RESOLVED after `full_build`; PHPStan max OK; comments ≤3 lines (R7.5).
- **Suite:** **581 passed** (baseline 578 → +3).

### Challenger detail round 1 ([Challenger](e18faac6-79cc-49ca-8eb9-37229de87fd1)) — ticket-blind @ `a2daf28`

`REQUIREMENTS: 13` · independence: raw ticket only (`029.work.md` excluded).

| # | Reconstructed requirement | Verdict | Evidence |
|---|---------------------------|---------|----------|
| 1 | `$this` / `$this?->` → enclosing FQN, default tier | **met** | `Visitor.php:342-355`; fixture + assert |
| 2 | `self` / `static` → enclosing FQN, default tier | **met** | `Visitor.php:360-370`; conformance + receiver fixture |
| 3 | `parent::` → extends FQN when known in-file; else leave | **met** | `enclosingParentQname`; `\App\Recv\Base::fromBase` |
| 4 | Core resolver unchanged | **met** | no `code_atlas/` in diff |
| 5 | `$x->m` HEURISTIC; `$x->$m` unchanged; no type inference | **met** | HEURISTIC path + Identifier gate |
| 6 | Unambiguous rewrite only; trait `$this` → trait FQN | **met** / soft **can't tell** (no free-fn fixture) | trait assert `\App\Recv\HasHook::hook` |
| 7 | Never claim RESOLVED beyond what one file knows (R5.2) | **met** | lexical omit-tier; `$x` stays HEURISTIC |
| 8 | Zero language branches in core (R1.1) | **met** | adapters/php only |
| 9 | No contract vocabulary / version bump | **met** | no contract edits |
| 10 | AC RESOLVED incl. parent method **in another file** | **met** (same-file) / **not met** (cross-file) | Base+Child in one file at this SHA |
| 11 | Negatives: `$x->m` / `$x->$m` / trait no false host | **met** | proving negatives |
| 12 | Measurable HEURISTIC CALLS drop; no wrong RESOLVED | **met** | conformance + proving hand-count |
| 13 | Contract + resolver + PHP suites pass | **met** | targeted **132 passed** |

**Summary:** mostly satisfies 029; **cross-file inherited-parent AC clause not met** at `a2daf28`.

### Reviewer detail round 2 verify ([Reviewer](a0efdaca-534d-46be-92c6-e26619e8be31)) @ `633bcfc`

- **Verdict:** **LGTM** — prior Important fixed; no new Critical/Important
- **Fix:** `Visitor.php:404-406` — innermost `Class_` only; null extends → leave `\parent::…`
- **Regression:** `NestedOuter` + assert `("\\parent::fromBase", None) in shapes` — PASSED
- **Cross-file parent AC:** `receiver_base.php` + `receiver_resolution.php`; proving `parsed == 2` + RESOLVED `\App\Recv\Base::fromBase` — PASSED
- **Suite:** proving+conformance 15 passed; full suite **581 passed** in 28.38s

### Challenger detail round 2 ([Challenger](745dc7a6-b121-4d52-b8d7-c7445c33cc33)) — ticket-blind @ `633bcfc`

`REQUIREMENTS: 10` · independence: raw ticket only (`029.work.md` excluded).

| # | Reconstructed requirement | Verdict | Evidence |
|---|---------------------------|---------|----------|
| 1 | `$this` / `$this?->` → enclosing FQN default tier | **met** | `Visitor.php:347-356`; `Child::go` ×4 |
| 2 | `self` / `static` → enclosing FQN default tier | **met** | `Visitor.php:365-370`; static_vs_instance rewrite |
| 3 | `parent::` → extends FQN / else leave; nested anon guard | **met** | Base rewrite + NestedOuter `\parent::fromBase` |
| 4 | AC cross-file: RESOLVED to parent method **in another file** | **met** | `receiver_base.php` + child file; proving `:84-96` |
| 5 | `$x->m` HEURISTIC; `$x->$m` unchanged | **met** | proving `:55`, `:57-58` |
| 6 | Trait `$this` does not fabricate host | **met** | `\App\Recv\HasHook::hook` |
| 7 | No false receiver outside unambiguous class-like / innermost parent | **met** | `enclosingClassLikeQname` / innermost walk |
| 8 | Core unchanged; R1.1; no contract bump | **met** | adapters/php + fixtures/tests + PLAN only |
| 9 | Measurable HEURISTIC drop; pairs with 028 health | **can't tell** (partial) | hand-count proven; no explicit 028 pairing in diff |
| 10 | Full contract + resolver + PHP suites pass | **can't tell** | challenger re-ran receiver tests 3/3 only |

**Summary from challenger:** cross-file inherited-parent AC **now met**. Soft can't-tells (AC3↔028 pairing; suites in that pass) do not block — main loop already ran full suite **581 green**.

### Scope reconcile

File set ⊆ change-list (Visitor, fixtures/golden, proving tests, PLAN §8.2) + fix commit NestedOuter/Base split. Approach bullets implemented-as-approved. Layer-match ✅. **Gate 4: clean.**

### Matrix Ph3/4

G1 / R1–R4 / C1–C4 / AC1–AC4 → ✅ · inventory `$this`/`self`/`static`/`parent` → ✅ · full suite **581 passed**.

- **Clean?** yes
- **Reviewed at:** `633bcfc` (code LGTM); tip `9c2f166` docs-only after bookkeeping

## Phase 5 — Finalise ✋ final gate

- **PR:** [#32](https://github.com/cuongdinhngo/code-atlas/pull/32)
- Outward actions approved by standing approval (suggest best / pass all gates):
  1. [x] bookkeeping (BACKLOG done, frontmatter, token row, lesson)
  2. [x] push + open PR
- Durable lesson: innermost `Class_` owns `parent::` — do not walk past a null-extends class to an outer parent (`029-C1` in `docs/LESSONS.md`).
- **Gate 5 status:** complete — PR [#32](https://github.com/cuongdinhngo/code-atlas/pull/32)

## Cost ledger

| phase | dispatch | round | tokens | notes |
|-------|----------|-------|--------|-------|
| refine | challenger (exposure) | 1 | unmeasured (host does not surface usage) | [3a242c02](3a242c02-ae14-47ac-974b-00ca86317add); EXPOSURE: 0 |
| review | reviewer | 1 | unmeasured (host does not surface usage) | [f103d9ae](f103d9ae-a28d-496f-9726-c4b2e71e202c); CHANGES REQUESTED |
| review | challenger | 1 | unmeasured (host does not surface usage) | [e18faac6](e18faac6-79cc-49ca-8eb9-37229de87fd1); 11 met / 1 not met |
| review | reviewer | 2 verify | unmeasured (host does not surface usage) | [a0efdaca](a0efdaca-534d-46be-92c6-e26619e8be31); LGTM |
| review | challenger | 2 | unmeasured (host does not surface usage) | [745dc7a6](745dc7a6-b121-4d52-b8d7-c7445c33cc33); 8 met / 0 not met / 2 can't tell |

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Phase 0 | AC3 = exact hand-count | recommended option 1; standing approval |
| Gate 1–2 | cleared | standing approval pass all gates |
| Gate 4 | clean after round-2 LGTM | parent walk + cross-file Base fixed |
| Phase 0 | work_doc_mode=embed (merged) | committed stub |

## Session status

- **Ticket:** 029
- **Current phase:** finalise (complete)
- **work_doc_mode:** embed
- **working_doc:** docs/tasks/029_php-receiver-resolution.md
- **Blocked on:** none
- **Next action:** none — PR #32 open
