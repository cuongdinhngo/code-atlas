---
id: 148
slug: r22-framework-sweep-cannot-fail-for-adapter-2
title: The R2.2 framework sweep lists only PHP frameworks — it cannot fail for adapter #2
phase: 2
milestone: M7
status: done
depends_on: [012, 146]
---

## Why this exists

R2 is *standard over sample*: an adapter encodes the language spec, never a repo's framework. The
grep-gate that enforces it can only see PHP:

    FRAMEWORK_NAME = re.compile(r"laravel|symfony|wordpress|drupal|magento", re.IGNORECASE)
    # tests/contract/test_guardrail_gates.py:24, and the same alternation in .github/workflows/ci.yml

A TypeScript adapter naming `react`, `vue`, `next`, `express` or `nest` passes that sweep clean. The
gate would report GREEN on precisely the violation R2 exists to catch.

The tell that this is an oversight and not a scope decision is one line away: `EXCLUDED_DIR_NAMES`
already carries `node_modules`. The *exclusion* was made adapter-#2-ready; the *inventory* was not.

Same failure class as [146](146_gate-can-pass-on-stale-bytecode.md) — a check that cannot fail — and
it is worth closing on its own, independent of whether [019](019_typescript-adapter.md) is ever
started.

## Scope

- Extend the inventory to the JS/TS ecosystem's framework names.
- Keep **one** copy. The shell gate in `ci.yml` and the pytest twin are hand-kept copies today
  (the module's own comment says "Regexes match `.github/workflows/ci.yml`"), and two copies of a
  list drift in opposite directions (R6.7). Either derive one from the other, or assert they are
  equal.
- One planted negative control per ecosystem, alongside the existing
  `test_r22_planted_framework_name_fails`.

## Acceptance criteria

1. **AC1.** A planted `react` / `vue` / `next` / `express` / `nest` name under `adapters/` **fails**
   the sweep, proven by a planted control, not by inspection.
2. **AC2.** `ci.yml`'s alternation and the pytest alternation are not two independently maintained
   lists: either one is read from the other, or a test fails when they differ (R6.7).
3. **AC3.** No authored file in the tree starts failing — the change adds reach, it does not
   reinterpret existing source.
4. **AC4.** The vacuous-sweep guard is preserved: excluding `vendor/`/`node_modules/` must still
   leave a non-empty authored set (R6.5).

## Not in scope

The R1.1 language-branch regex, which is a different gate with a different failure mode. Any adapter
source.

## References
R2, R2.2, R6.5, R6.7; PLAN §6.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->
<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review + challenger waived per run args)
- **Branch:** `chore/148-r22-framework-sweep-cannot-fail-for-adapter-2`
- **CHALLENGER:** OFF (--no-challenger; review waived per run args)
- **work_doc_mode:** embed
- **TIER:** full · **SCOPE:** M
- **refine:** 1 how-decision resolved (derive vs assert-equal → derive from one file)

## Requirements matrix

| ID | Kind | Requirement | Ph3 | Ph4 | Notes |
|---|---|---|---|---|---|
| G1 | G | The R2.2 gate must be able to fail for a JS/TS adapter that names its framework | ✅ | waived | AC1 controls green (react/vue/nextjs/express/nestjs caught) |
| R1 | R | Extend the inventory to the JS/TS ecosystem's framework names | ✅ | waived | `framework_denylist.txt` — react…nest.js |
| R2 | R | Keep **one** copy — ci.yml + gate.sh + pytest not independently maintained | ✅ | waived | all three derive from `framework_denylist.txt` |
| R3 | R | One planted negative control per ecosystem, alongside the existing one | ✅ | waived | `test_r22_denylist_covers_each_ecosystem` (6 params) |
| AC1 | AC | A planted react/vue/next/express/nest name under `adapters/` **fails**, by control | ✅ | waived | `test_r22_denylist_covers_each_ecosystem` + shell red-run |
| AC2 | AC | ci.yml and pytest alternations are not two hand-kept lists (derive, or test on drift) | ✅ | waived | `test_r22_shell_gate_derives_from_the_denylist` |
| AC3 | AC | No authored file starts failing — adds reach, does not reinterpret existing source | ✅ | waived | `test_r22_bare_next_and_nest_do_not_trip_the_sweep`; 0 hits adapters/+core |
| AC4 | AC | Vacuous-sweep guard preserved (vendor/node_modules exclusion leaves non-empty set) | ✅ | waived | existing R6.5 test kept; `test_r22_denylist_is_non_empty` added |
| C1 | C | Not the R1.1 language-branch regex; no adapter source touched | ✅ | waived | diff is denylist + gate/ci/test only |
| C2 | C | R6.7 no drifting duplicate · R6.5 guard-the-guard · R2.3 tests/scripts may name pinned repos | ✅ | waived | denylist under unswept tests/ |

**AC-validation:** all four mechanically testable. **Clarifications (j):** 0 — standing approval.

**Blast radius (read):** the alternation is hand-copied in **three** places — `.github/workflows/ci.yml`
(`234`, `240`), `scripts/gate.sh` (`190`–`191`), `tests/contract/test_guardrail_gates.py:24`. The
shell gates sweep `adapters/` **and** `code_atlas/`; the pytest sweeps `adapters/` only. **AC3 hazard:**
bare JS names collide with real code/prose — `express` ⊂ "expression" (2 adapter files), `nested` (1);
bare `next` hits `adapters/php/README.md` + 9 core files (Python `next()`), bare `nest` hits 2 core
files. Word boundaries are mandatory, and `next`/`nest` must use the framework spelling (`next.js`,
`nest.js`), not the bare word. `.github` is in `.dockerignore`, so a test reading `ci.yml` is red on
the mandated Docker host (147's finding) — hence derive-from-file, not assert-equal-reading-ci.yml.

## Design

**Approach — one canonical denylist file; all three consumers derive from it.**

1. **`tests/contract/framework_denylist.txt` (new, the single source).** One ERE alternative per line:
   `laravel symfony wordpress drupal magento react vue angular svelte express nuxt nextjs next\.js
   nestjs nest\.js`. Lives under `tests/` because `tests/`/`scripts/` are deliberately unswept (R2.3,
   ci.yml comment) — so the file cannot self-match.
2. **`test_guardrail_gates.py`.** `FRAMEWORK_NAME` is derived: read the file, strip blanks/comments,
   `re.compile(r"\b(?:" + "|".join(alts) + r")\b", re.I)`. Word boundaries make `express`≠"expression"
   and the js-suffixed forms avoid the bare `next`/`nest` collisions.
3. **`scripts/gate.sh` + `.github/workflows/ci.yml`.** Build the pattern at runtime from the same file
   (`grep -vE '^[[:space:]]*(#|$)' … | paste -sd'|' -`), then `grep -rEin "\b(${fw})\b"`. An empty/
   missing file is a loud FAIL, never a vacuous pass (R6.5).
4. **Tests added:** `test_r22_denylist_covers_each_ecosystem` (AC1, one planted control per ecosystem)
   · `test_r22_denylist_is_non_empty` (R6.5 guard-the-guard on the new file) ·
   `test_r22_shell_gate_derives_from_the_denylist` (AC2 — gate.sh references the file and carries no
   hand-kept literal). The existing vacuous-sweep test (AC4) and single-name planted test are kept.

**Rejected alternatives.**
- *Assert-equal test that reads `ci.yml`* — would be red on the mandated Docker host (`.github` is
  dockerignored; 147's finding). Derivation from one file is the stronger R6.7 form and avoids it.
- *Bare `next`/`nest` in the alternation* — fails AC3 (PHP `next()`, "the next request", core `next()`).
- *Substring matching (no `\b`)* — `express`⊂"expression", `nest`⊂"nested"; mass false positives.
- *Fold in the `.dockerignore` fix for 146's ci.yml test* — out of scope; left as the follow-up
  already filed on PR #174.

**Rule-compliance.** R2.2: the gate now catches JS/TS framework names. R6.7: one denylist, derived
three ways — no hand-kept copy. R6.5: empty-denylist and vacuous-sweep both fail loud, proven by
controls. R2.3: denylist under unswept `tests/`.

**Proving test(s):** `test_r22_denylist_covers_each_ecosystem` (AC1) · `test_r22_shell_gate_derives_from_the_denylist`
(AC2) · `test_r22_authored_adapter_source_has_no_framework_names` stays green (AC3) ·
`test_r22_authored_adapter_sweep_is_non_empty_under_vendor_exclusion` + `test_r22_denylist_is_non_empty` (AC4/R6.5).

**Change-list (files):** `tests/contract/framework_denylist.txt` (new) · `tests/contract/test_guardrail_gates.py`
· `scripts/gate.sh` · `.github/workflows/ci.yml`. No core, no adapter source.

## Execute — proof

- **Proving tests (green):** 17/17 in `test_guardrail_gates.py`, incl. `test_r22_denylist_covers_each_ecosystem[laravel|react|vue|nextjs|express|nestjs]`
  (AC1), `test_r22_bare_next_and_nest_do_not_trip_the_sweep` (AC3), `test_r22_denylist_is_non_empty`
  (R6.5), `test_r22_shell_gate_derives_from_the_denylist` (AC2), `test_r22_authored_adapter_source_has_no_framework_names`
  (AC3). 147's AC4/AC2 guards still green.
- **Shell derivation reproduced:** pattern `\b(laravel|…|nest\.js)\b`; adapters/ 0 hits, code_atlas/ 0 hits,
  planted `react` → 1, bare `next()`/"nested"/"next request" → 0.
- **R6.5 red-runs recorded (shell layer):** a planted `react` name in `adapters/` → sweep FAILED;
  empty denylist → the `[ ! -s … ]` FAIL branch fires (not a vacuous pass).
- **ruff:** clean. **gate.sh:** `bash -n` OK. **mypy:** unaffected (core untouched).
- **Delta-green host:** Windows dev host + Docker full suite (below).
- **Scope sweep:** diff = approved change-list exactly (`framework_denylist.txt` new · `test_guardrail_gates.py`
  · `scripts/gate.sh` · `.github/workflows/ci.yml` + working doc). Core diff empty; no adapter source.

## Counted lines — finalise

CLAIMS: 2 claim(s) from 1 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified
RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)
FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)
RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path
PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md (R6.5, R6.7 — already binding; seen bumped) | mango files written: 0
LEDGER TOTAL: 0 tokens · top cost driver: none (solo main-loop run; no subagents dispatched)

- Both claims are sightings of handles already binding as rules (R6.5, R6.7); `seen:` bumped in
  `LESSONS.md` (rec 12→13, 15→16). No new rule proposed, so `/mango:promote` has nothing to carry.

## Counted lines — design

HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply | 0 unanswered
EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor

- **HANDLES trace.** `prove-the-guard-fails` (R6.5) → execute records red-runs: a bare-`next` planted
  control must NOT fire (AC3), and each ecosystem's framework name MUST fire (AC1); empty denylist
  fails. `derived-not-listed-invariant` (R6.7) → the alternation is read from one file by all three
  consumers, never re-listed.

## Counted lines — analysis

PREMISE: 2 references checked | 0 missing | 0 ambiguous (surfaced, not blocking)
RECALL: 2 claims surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)
REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no
SECTIONS: 5 found (Why this exists, Scope, Acceptance criteria, Not in scope, References) | 5 decomposed | ROWS: C=2 R=3 G=1 AC=4
CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision
RULE SECTIONS: 4 applicable — 2 by change-type | 2 by recalled handle — R2.2 (change-type) ✅ | R6.1 (change-type) ✅ | R6.5 (recalled: prove-the-guard-fails) ✅ | R6.7 (recalled: derived-not-listed-invariant) ✅

## Cost ledger

| phase | dispatch | tokens |
|---|---|---|
| analysis+design | main loop | unmeasured (host does not surface usage; review/challenger waived) |
