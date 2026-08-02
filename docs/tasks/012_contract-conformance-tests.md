---
id: 012
slug: contract-conformance-tests
title: Contract-conformance & PHP coverage tests (M2)
phase: 1
milestone: M2
status: done
depends_on: [025, 002]
---

## Goal
The LSP-substitutability guarantee: every adapter passes the same schema tests (§16).

## Scope / Deliverables
- `tests/contract/`: schema-conformance harness every adapter must pass (asserts emitted JSON + known node/edge counts).
- `tests/fixtures/php/`: namespaced, global, underscore(PSR-0), trait+conflict-resolution, enum, attributes, closures/arrow-fns, first-class-callable, include, static-vs-instance-call, syntax-error.
- CI **grep-gate**: assert zero language branches in `code_atlas/`; ban repo/framework names in adapter source.
- **CI:** the `guardrails` job never installs dependencies, so the `--exclude-dir=vendor` added in task 006 has **never been exercised there** — that gate currently passes over a tree with no `vendor/` in it. Move R2.2 into a pytest assertion in the `test` job, where `composer install` has run and the exclusion can actually be wrong. Keep the shell gate as a second layer; negative-control both (R6.4, R6.5).

## Acceptance criteria
- PHP adapter passes the conformance harness on all fixtures.
- Grep-gate fails the build on a planted `if language ==` or framework name.

## References
Plan §16, §2.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 012 — Contract-conformance & PHP coverage tests (working doc)

- **Ticket:** 012 · [docs/tasks/012_contract-conformance-tests.md](012_contract-conformance-tests.md) (raw above separator)
- **Type:** enhancement
- **Repo(s) / Porting:** `app` (`.`) only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `424 passed in 17.62s` (`.venv/bin/pytest -q`; run required `all` perms so PHP adapter subprocesses are not sandboxed-hung). baseline exclusions: none
- **work_doc_mode:** `embed` → this doc lives below the separator in the ticket file itself (harness `work_doc_mode: embed`)

---

## Phase 0 — Refine (the FIRST phase; skip when the ticket is already clear)

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`

`REFINE: 2 unresolved surfaced | 0 want-decision asked (handed back → ASSUMED) | 3 how-decision resolved+cited | 2 ASSUMED | skip: no`

**INPUT KIND:** ticket (single deliverable — not an epic).

**Prior Phase-0 (dependency stop) — resolved:** 025 is now `done` in BACKLOG; the settled want "Stop 012 — run 025 first" is satisfied. This Phase 0 is the resume after that gate.

**Settled wants (want-decision — from the user; become acceptance-criteria constraints analysis must honour).**

| # | The want (in want-language) | Chosen direction (NOT a tool) | Becomes AC constraint |
|---|-----------------------------|-------------------------------|-----------------------|
| — | (none asked live this resume — user pre-approved "best option / pass all gates") | — | — |

**Resolved direction + citation (how-decision — refine-resolved + CITED):**

| # | HOW-decision | Resolution | Citation (`file:line` / convention / rulebook § / ticket line) |
|---|--------------|------------|----------------------------------------------------------------|
| 1 | Dependency authority (frontmatter vs BACKLOG) | Sync frontmatter `depends_on` to **[025, 002]** (both done) | `docs/BACKLOG.md:24`; R7.2 |
| 2 | Fixture ownership vs 025 | 025 owns construct-level correctness; 012 owns the cross-adapter conformance matrix (schema + known counts) | `docs/tasks/025_php-adapter-grammar.md:61-62`; R3.4 |
| 3 | R2.2 placement + negative-control | Move R2.2 into a pytest assertion in the `test` job (composer present); keep shell `guardrails` gate as second layer; negative-control both | ticket Scope lines 17–18; R6.4, R6.5 |

**ASSUMED (awaiting ratification) — MANDATORY:**

| # | Assumed choice | Why ASSUMED (handed back / recommendation) | Explicit confirm at gate | Reverses a prior decision? |
|---|----------------|--------------------------------------------|--------------------------|----------------------------|
| A1 | **Named R6.2 fixture inventory stays mandatory as separate files** under `tests/fixtures/php/` — `grammar.php` does **not** supersede the Scope list. Add missing named files; reuse existing named ones. | Exposure-checker WANT + user "best option"; ticket Scope + R6.2 name the inventory | Gate 1 | no (prior stop was only "wait for 025") |
| A2 | **Known node/edge counts** = frozen expected integers per fixture from a golden live-adapter run (not hand-waved "sane") | Acceptance-bar WANT; user "best option" | Gate 1 | no |

**Constraints surfaced from the scan:**

- 025 landed emitters for trait/closure/FCC/enum/etc.; `tests/test_php_adapter_grammar.py` owns construct correctness; `grammar.php` is the kitchen-sink for that.
- Partial `tests/contract/test_contract_schema.py` covers core-side schema/vocabulary; 012 adds the live-adapter harness + fixture counts.
- Existing named fixtures: `namespaced`, `global_underscore`, `attributes`, `syntax_error` (+ `grammar`, `resolve/`). Missing named Scope files: trait+conflict, enum, closures/arrow, FCC, include, static-vs-instance (and possibly a pure `global` if distinct from underscore).
- `tests/test_php_adapter_grammar.py:275-282` already has a narrow R2.2 denylist over `adapters/php/src/**/*.php` only — 012 still needs the ticketed move into `tests/contract/` (or equivalent) with vendor-exclusion + non-empty sweep + negative-control, runnable under the `test` job.
- `guardrails` never runs `composer install`; shell R2.2 `--exclude-dir=vendor` remains a second layer.

**Exposure-checker** ([challenger](1ee6a1e2-f581-43ac-b741-c24b661a611a), 1 dispatch): `UNEXPOSED: 1` — named fixture inventory vs supersede by `grammar.php` → filed as ASSUMED A1 above. No further unexposed decisions after classification.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=0 R=4 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | The LSP-substitutability guarantee: every adapter passes the same schema tests (§16). | Live-adapter harness under `tests/contract/` is the R3.4 substitutability gate (schema + known counts), shared by every adapter; PHP is the only adapter today. | `docs/PLAN.md:407`; R3.4; partial core-side `tests/contract/test_contract_schema.py` | | | ❌ |
| R1 | Scope | `tests/contract/`: schema-conformance harness every adapter must pass (asserts emitted JSON + known node/edge counts). | New harness drives the real adapter over fixtures; `contract.validate()` clean + frozen node/edge counts (A2). | Gap: no live-adapter count harness yet | | | ❌ |
| R2 | Scope | `tests/fixtures/php/`: namespaced, global, underscore(PSR-0), trait+conflict-resolution, enum, attributes, closures/arrow-fns, first-class-callable, include, static-vs-instance-call, syntax-error. | Eleven named construct fixtures (A1); missing files must be added; existing named ones reused. | Inventory F1–F11 below | | | ❌ |
| R3 | Scope | CI **grep-gate**: assert zero language branches in `code_atlas/`; ban repo/framework names in adapter source. | Keep shell R1.1 + R2.2 in `guardrails`; R1.1 already mirrored in `tests/test_core_is_language_agnostic.py`. | `.github/workflows/ci.yml:103-129` | | | ⚠ (partial — R1.1 ok; R2.2 vacuous in guardrails) |
| R4 | Scope | Move R2.2 into a pytest assertion in the `test` job… Keep the shell gate as a second layer; negative-control both (R6.4, R6.5). | Authored-source sweep with vendor exclusion + non-empty guard + planted-hit negative controls for R1.1 and R2.2 under pytest. | Narrow AC3 in `test_php_adapter_grammar.py:275-282` lacks vendor exclusion proof + negative-control | | | ❌ |
| AC1 | AC | PHP adapter passes the conformance harness on all fixtures. | For each of F1–F11: validate([]) and frozen counts match. | depends on R1+R2 | | | ❌ |
| AC2 | AC | Grep-gate fails the build on a planted `if language ==` or framework name. | Negative-control tests prove both gates trip on planted hits (not only that clean trees pass). | depends on R4 | | | ❌ |
| AC-A1a | refine A1 | Named R6.2 fixture inventory stays mandatory as separate files | Each of the 11 Scope categories has its own fixture file under `tests/fixtures/php/`. | A1 | | | ❌ |
| AC-A1b | refine A1 | `grammar.php` does not supersede the Scope list | Conformance matrix enumerates the named inventory; `grammar.php` may remain 025-only. | A1 | | | ❌ |
| AC-A2 | refine A2 | Known counts = frozen integers from a golden live-adapter run | Per-fixture expected `len(nodes)` / `len(edges)` (and syntax-error shape) are literal ints in the harness. | A2 | | | ❌ |

`PREMISE: 9 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)` *(carried from refine)*

Ambiguous (non-blocking): prose “CI grep-gate” maps to both shell `guardrails` and pytest mirrors — Scope R4 settles placement.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | PHP adapter passes harness on all fixtures | “all fixtures” = the 11 Scope/R6.2 categories (A1); pass = `validate()==[]` + frozen counts (A2) | Y (under A1/A2) | measurable | — |
| AC2 | Grep-gate fails on planted `if language ==` or framework name | Two planted negative controls (R1.1 pattern + R2.2 denylist token) must assert failure | Y | measurable | — |
| AC-A1a/b | (ASSUMED) | Separate files; grammar does not replace | Y if ratified | measurable (file inventory) | Gate 1: ratify A1 |
| AC-A2 | (ASSUMED) | Frozen ints per fixture | Y if ratified | measurable | Gate 1: ratify A2 |

## Inventory (universal "all/every/no" requirements)

- **Denominator / total N:** 11 (fixture categories) + 2 (grep-gate negative controls) — fixture checklist is the per-item “for each” set for AC1/R2.

| # | Item | Ph3/4 proven by (`path:line` / test) | Status ✅/⚠/❌ |
|---|------|--------------------------------------|----------------|
| F1 | namespaced | | ❌ |
| F2 | global | | ❌ |
| F3 | underscore (PSR-0) | | ❌ |
| F4 | trait + conflict-resolution | | ❌ |
| F5 | enum | | ❌ |
| F6 | attributes | | ❌ |
| F7 | closures / arrow-fns | | ❌ |
| F8 | first-class-callable | | ❌ |
| F9 | include | | ❌ |
| F10 | static-vs-instance-call | | ❌ |
| F11 | syntax-error | | ❌ |
| G-R1.1 | planted language-branch negative control | | ❌ |
| G-R2.2 | planted framework-name negative control (+ non-empty authored sweep under vendor exclusion) | | ❌ |

### Surface inventory

N/A — `TRACK: backend` (no UI surfaces).

## Clarifications

`CLARIFICATION: 2 raised | 0 self-resolved as HOW beyond Phase 0 | 2 for human decision (ASSUMED A1/A2 at Gate 1)`

| # | Item | Resolution |
|---|------|------------|
| 1 | A1 named inventory vs grammar supersede | ASSUMED — confirm at Gate 1 |
| 2 | A2 frozen counts bar | ASSUMED — confirm at Gate 1 |

`j = 2` at Gate 1 as ASSUMED confirms (not open design questions). No Gate 0 beyond that.

## Cause / gap analysis (enhancement)

| Goal slice | Current | Target | Evidence |
|------------|---------|--------|----------|
| Live-adapter conformance harness | Core-side schema tests only | Drive PHP adapter; schema + counts | `tests/contract/test_contract_schema.py` |
| R6.2 fixture set | 4 named + grammar kitchen-sink; 6+ Scope names missing as files | 11 named files | `tests/fixtures/php/` |
| R2.2 under `test` job | Shell gate vacuous without vendor; narrow grammar AC3 | Pytest sweep with vendor exclude + non-empty + negative controls; shell kept | `ci.yml:115-129`; `test_php_adapter_grammar.py:275-282` |
| R1.1 | Shell + `test_core_is_language_agnostic.py` | Keep; add planted negative control if not already covered | `tests/test_core_is_language_agnostic.py:40-44` has regex self-check on strings, not a planted file — AC2 still wants planted fail | 

## Blast radius

- **Entry:** new/extended tests under `tests/contract/` + fixtures under `tests/fixtures/php/`; possibly thin shared helper; CI `guardrails` unchanged as second layer.
- **Touches:** `tests/**`, `docs/tasks/012_*`, `docs/BACKLOG.md`; **does not** change `code_atlas/` or adapter emitters (025 already did).
- **Repos:** `app` (`.`) only.
- **db-map:** absent — N/A.

`TRACK: backend — 0/N touched files under UI paths`

## Rule-compliance section coverage

`RULE SECTIONS: §1 (boundaries) N/A — no core language branch added; §2 (standard over sample) ✅ applicable (fixtures + R2.2); §3 (contract) ✅ R3.4 harness; §4 N/A — no core determinism change; §5 N/A; §6 (testing) ✅ R6.2/R6.4/R6.5; §7 (change discipline) ✅ R7.2 backlog/frontmatter; §8 N/A — no new deps`

## Scope / Tier

- **SCOPE:** M — eleven fixtures + harness + dual-layer grep gates / negative controls; not a one-file fix.
- **TIER:** full — universal fixture inventory N=11 > 1; not lite-eligible.

---

## Decision log

| When | Decision | Rationale |
|------|----------|-----------|
| Gate 1 | Ratify A1 + A2; clear Gate 1 | User pre-approved "best option / pass all gates" on `/solve 012` |

---

## Phase 2 — Design

### Approach

Add a **live-adapter conformance harness** under `tests/contract/` that runs the real PHP adapter over **eleven named R6.2 fixtures**, asserts `contract.validate() == []` (or the syntax-error failure shape) and **frozen node/edge counts**. Add the missing fixture files as minimal, construct-focused PHP (025’s `grammar.php` stays the construct kitchen-sink; it is **not** on the conformance list). Add a **pytest R2.2 gate** (authored `adapters/` sweep, exclude `vendor/`/`node_modules/`, assert non-empty, plus planted negative controls for R1.1 and R2.2). Keep the shell `guardrails` job as the second layer unchanged in spirit.

### Rejected alternatives

| Alternative | Why rejected |
|-------------|--------------|
| Conformance only against `grammar.php` + existing files | Violates ratified A1 / ticket Scope / R6.2 named inventory |
| Install Composer in the `guardrails` job instead of pytest | Ticket explicitly moves R2.2 into the `test` job where vendor already exists; shell stays second layer |
| Hand-authored “sane” count ranges | Violates ratified A2 (frozen integers from a golden run) |

### Assumptions

| Assumption | Tag | Resolution |
|------------|-----|------------|
| PHP adapter emits valid contract JSON for new minimal fixtures | verified | 025 + existing spike/grammar/attribute tests |
| `adapters/php/vendor/` contains denylist tokens (e.g. Symfony) so an unscoped grep would fail | verified | spike this session: hits under `vendor/composer/ClassLoader.php` etc. |
| Planted-file negative controls via `tmp_path` + shared scan helpers are sufficient for AC2 | verified | same pattern as other tmp_path gates; proving tests assert the helper trips |
| Frozen counts from a golden `--file` run stay stable under R4.2 | verified | R4.2 + 025 line-anchored qnames; counts are structural |

### Smallest change-list

| # | Change | File/area | Ph2 covered by | k/N |
|---|--------|-----------|----------------|-----|
| 1 | Add missing named fixtures (minimal PHP per category); keep existing `namespaced` / `attributes` / `syntax_error`; add `global.php` + `underscore_psr0.php` (leave `global_underscore.php` for spike/server tests — proof collateral: no rename) | `tests/fixtures/php/*.php` | R2, AC1, AC-A1a, AC-A1b, F1–F11 | 11/11 fixtures |
| 2 | Live-adapter conformance harness: parametrize F1–F11; `validate` + frozen counts (syntax-error: `ok is False`, empty nodes/edges) | `tests/contract/test_adapter_conformance.py` (new) | G1, R1, AC1, AC-A2 | 1/1 harness |
| 3 | Guardrail pytest: R2.2 authored sweep with vendor/node_modules exclusion + non-empty guard; planted negative controls for R1.1 language-branch and R2.2 framework name | `tests/contract/test_guardrail_gates.py` (new) | R3, R4, AC2, G-R1.1, G-R2.2 | 1/1 gates module |
| 4 | Optional shared scan helpers if (3) would otherwise duplicate `test_core_is_language_agnostic` regexes — only if needed for DRY of the planted-control API | `tests/contract/_guardrails.py` or inline | R4 | 0–1 |
| 5 | Bookkeeping already in flight: `depends_on: [025, 002]`, status `in-progress` both places | ticket frontmatter + `docs/BACKLOG.md` | R7.2 | done |
| 6 | **Proof collateral — do not break:** leave `global_underscore.php` and spike/server/grammar AC3 alone unless a test fails; do not retarget 025 grammar tests to the new files | `tests/test_php_adapter_*.py` | blast-radius | monitor |

**Test blast-radius (mechanical):** consumers of `global_underscore.php` / `namespaced.php` / `syntax_error.php` / `attributes.php` stay on those paths. New files are additive. R2.2 grep consumers: grammar AC3 (src-only) remains; new contract gate is broader (`adapters/` authored) — no assertion invalidated. Shell `ci.yml` R2.2 unchanged.

### Rule compliance

- R1.1 — no new core language branches; only tests/docs.
- R2.2 / R6.4 / R6.5 — pytest gate with vendor exclusion + non-empty + negative controls; shell second layer.
- R3.4 — `tests/contract/` live-adapter harness is the substitutability guarantee.
- R6.1 / R6.2 — spec-driven named fixtures; harness asserts them.
- R7.2 — backlog/frontmatter sync.
- CONVENTION §1 — fixtures under `tests/fixtures/<lang>/`, contract tests under `tests/contract/`.

### Verification plan (per-AC)

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 (harness on all fixtures) | integration (live PHP adapter) | integration pytest parametrize F1–F11 | ✅ |
| AC2 (planted grep fails) | logic (scan helper over planted paths) | unit/integration pytest with `tmp_path` plants | ✅ |
| AC-A1a/b (named files; no grammar supersede) | logic (file inventory) | conformance param list == 11 named paths; `grammar.php` absent from list | ✅ |
| AC-A2 (frozen counts) | integration | literal expected ints per fixture in harness | ✅ |
| G1 / R1 / R3 / R4 | as above | covered by AC1/AC2 proofs | ✅ |

### Proving test

Pre-change fails (module/fixtures missing); post-change passes:

```text
.venv/bin/pytest -q tests/contract/test_adapter_conformance.py tests/contract/test_guardrail_gates.py
```

Named anchor: `tests/contract/test_adapter_conformance.py` — PHP adapter conforms on every named fixture (schema + frozen counts); plus `tests/contract/test_guardrail_gates.py` — planted R1.1 / R2.2 hits fail and authored R2.2 sweep is non-empty under vendor exclusion.

### Rollback + porting

- Revert the branch / delete the new test+fixture files; no schema or adapter code to roll back.
- Porting: `app` only; later adapters #2+ must pass the same harness (R3.4) — out of scope for 012.

### SCOPE confirm

**SCOPE: M** — unchanged (11 fixtures + harness + dual-layer gates). Did not outgrow to L.

---

## Phase 3 — Execute

**Branch:** `feat/012-contract-conformance-tests`

**Implemented (Axis 2 — design-conformance):**

| Approach bullet | Status |
|-----------------|--------|
| Live-adapter harness under `tests/contract/` over 11 named fixtures; validate + frozen counts | implemented-as-approved |
| Missing named fixtures added; `grammar.php` not on list; leave `global_underscore.php` for spike/server | implemented-as-approved |
| Pytest R2.2 with vendor exclusion + non-empty + planted R1.1/R2.2 negative controls | implemented-as-approved |
| Shell `guardrails` kept as second layer (unchanged) | implemented-as-approved |
| Optional shared helper file | not needed (inline helpers in `test_guardrail_gates.py`) — recorded; no deviation from behaviour |

**Deviations:** none behavioural.

**Verification sweep:**

- Axis 1 file set ⊆ change-list ✅ (`tests/fixtures/php/*` new, `tests/contract/test_*.py` new, docs bookkeeping)
- Axis 2 design-conformance ✅ (table above)
- Proving tests: `17 passed` for named modules; full suite **`441 passed`**
- ruff + mypy clean on new modules

**Frozen counts (golden `--file` run):**

| Fixture | nodes | edges |
|---------|------:|------:|
| namespaced.php | 15 | 20 |
| global.php | 4 | 5 |
| underscore_psr0.php | 6 | 8 |
| trait_conflict.php | 7 | 8 |
| enum.php | 7 | 6 |
| attributes.php | 14 | 14 |
| closures_arrow.php | 6 | 5 |
| first_class_callable.php | 4 | 3 |
| include_require.php | 1 | 2 |
| static_vs_instance.php | 5 | 10 |
| syntax_error.php | ok=false + error (no nodes/edges keys) | — |

**Matrix Ph3/4 proven by (delta):** F1–F11 → `tests/contract/test_adapter_conformance.py`; G-R1.1/G-R2.2 → `tests/contract/test_guardrail_gates.py`; G1/R1/AC1/AC-A* → conformance; R3/R4/AC2 → guardrails.

---

## Phase 4 — Review

**Reviewed at** `fafd31a18e32f6760b9d6ef444524d9653ab9a35`

**Reviewed files:** `docs/BACKLOG.md`, `docs/tasks/012_contract-conformance-tests.md`, `tests/contract/test_adapter_conformance.py`, `tests/contract/test_guardrail_gates.py`, `tests/fixtures/php/{closures_arrow,enum,first_class_callable,global,include_require,static_vs_instance,trait_conflict,underscore_psr0}.php`

| Critic | Result |
|--------|--------|
| mango:reviewer ([reviewer](f57501ff-e0ee-48b8-8d1b-f44f807a2270)) | **LGTM** — 0 Critical / 0 Important; proving 17 passed; diff ⊆ Gate-2 list |
| mango:challenger ([challenger](5641e0b8-e549-4c85-9685-84d277a2bd83)) | **9 met · 0 not met · 0 can't tell** (ticket-blind) |

**Scope reconcile:** file axis ✅ · behaviour axis ✅ · no outgrew-its-ticket.

**Verdict:** clean — Gate 4 does not stop.

**Matrix Status:** G1, R1–R4, AC1–AC2, AC-A1a/b, AC-A2, F1–F11, G-R1.1, G-R2.2 → ✅

---

## Cost ledger (subagent dispatch only)

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 0 refine | mango:challenger (exposure-checker) | 1 | unmeasured (blocking retrieval) |
| 1 analysis | mango:extractor | 1 | unmeasured (blocking retrieval) |
| 4 review | mango:reviewer | 1 | unmeasured (blocking retrieval) |
| 4 review | mango:challenger | 1 | unmeasured (blocking retrieval) |

**Roll-up:** **4 dispatch**, all `unmeasured (blocking retrieval)`. Main-loop unmeasured.

---

## Durable lesson

Planted negative-control files under pytest `tmp_path` live **outside** the repo root. Asserting `path.relative_to(ROOT)` on those plants raises `ValueError` and breaks the AC2 proof — assert on `Path` identity (or a planted tree rooted under the repo) instead.

---

## Session status

- **Phase:** 4 review clean → 5 finalise
- **Next:** final gate — outward actions
- **Gate:** final gate
- **Reviewed at:** `fafd31a`
- **Blocked by:** none
