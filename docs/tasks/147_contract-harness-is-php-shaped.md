---
id: 147
slug: contract-harness-is-php-shaped
title: The R3.4 conformance harness is PHP-shaped — `tests/contract/` cannot admit a second adapter
phase: 2
milestone: M7
status: done
depends_on: [012, 025]
---

## Why this exists

R3.4 says every adapter must pass `tests/contract/` and that "that test *is* the substitutability
guarantee". The test cannot keep that promise today: it is written for one adapter.

- `tests/contract/test_adapter_conformance.py:14` imports `tests.php_adapter_cli`, and `CASES`
  hardcodes `.php` fixture filenames with frozen per-file kind histograms.
- `tests/php_adapter_cli.py:19-21` hardcodes `adapters/php/index.php` and `tests/fixtures/php`.

The intent was already recorded — `php_adapter_cli.py`'s own docstring says "keep that contract here
so adapter #2 does not invent a fourth copy". The intent is there; the shape is not. So the first
thing adapter #2 meets is a harness it cannot enter, and the cheapest way past it is a fourth copy —
exactly what that docstring was written to prevent.

This is a defect in the gate as it stands, not preparation for a language. It is worth fixing whether
or not [019](019_typescript-adapter.md) is ever taken off `deferred`.

## Scope

- Split the harness into a **per-adapter matrix**: one `adapter_cli` helper parametrized by
  (adapter directory, one-shot entry argv, fixtures directory, availability marker), and a
  conformance module parametrized over the registered adapters.
- Registration is **data** — a table in the test package keyed by adapter directory name — never a
  branch on a language name.
- PHP becomes one entry in that table. Its case list and histograms move across unchanged.

## Acceptance criteria

1. **AC1.** Every PHP case survives with a byte-identical frozen histogram; no case dropped, no
   count edited.
2. **AC2.** Adding a second entry requires no edit inside the conformance module body — only a row
   in the registration table and its fixtures.
3. **AC3 — guards the guard (R6.5).** With zero adapters registered the module **fails**; it must
   never pass over an empty matrix, which is how a skipped check reads as a pass.
4. **AC4.** Exactly one place in `tests/` spawns an adapter in one-shot `--file` mode. The "fourth
   copy" the existing docstring forbids is still impossible after the split.

## Not in scope

Any TypeScript parsing. Any fixture for a second language — [149](149_tsjs-construct-inventory.md)
names that inventory and this ticket does not invent it. The second CI runtime and the `npm ci` step,
which are [019](019_typescript-adapter.md)'s.

## References
R3.4, R6.1, R6.5, R6.7; PLAN §4.2, §4.3.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->
<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review + challenger waived per run args)
- **Branch:** `chore/147-contract-harness-is-php-shaped` (not yet cut)
- **CHALLENGER:** OFF (--no-challenger; review waived per run args)
- **work_doc_mode:** embed
- **TIER:** full · **SCOPE:** M
- **refine:** skipped — 0 unresolved product-decisions (premise intact: both referenced files exist)

## Requirements matrix

| ID | Kind | Requirement | Ph3 | Ph4 | Notes |
|---|---|---|---|---|---|
| G1 | G | The R3.4 conformance harness admits a 2nd adapter without a "fourth copy" of the spawn | ✅ | waived | proven by AC1–AC4 together |
| R1 | R | One `adapter_cli` helper parametrized by (adapter dir, one-shot entry argv, fixtures dir, availability marker) | ✅ | waived | `tests/adapter_cli.py` — `AdapterCli` + `run_adapter_file` |
| R2 | R | Conformance module parametrized over the registered adapters | ✅ | waived | `_conformance_params()` iterates REGISTRY × cases |
| R3 | R | Registration is **data** — a table keyed by adapter dir name; never a branch on a language name | ✅ | waived | `adapter_registry.REGISTRY` keyed by `cli.name` |
| R4 | R | PHP is one table entry; its case list + histograms move across **unchanged** | ✅ | waived | conformance green (54 passed, PHP present) |
| AC1 | AC | Every PHP case survives byte-identical; no case dropped, no count edited | ✅ | waived | `test_adapter_conforms[php:*]` all green |
| AC2 | AC | Adding a 2nd entry needs no edit inside the conformance module **body** — only a table row + fixtures | ✅ | waived | `test_ac2_conformance_body_names_no_adapter_directory_literal` |
| AC3 | AC | With **zero** adapters registered the module **fails** (R6.5 guard-the-guard) | ✅ | waived | `test_the_registry_is_non_empty` — red-run recorded |
| AC4 | AC | Exactly **one** place in `tests/` spawns an adapter in one-shot `--file` mode | ✅ | waived | `test_ac4_exactly_one_module_spawns…` — red-run recorded |
| C1 | C | No TS parsing, no 2nd-language fixture, no CI runtime/`npm` (all 019/149) | ✅ | waived | diff is test-infra only; core diff empty |
| C2 | C | R1.1 — no language-name branch introduced (test infra table is data, keyed by dir name) | ✅ | waived | `test_r11_planted_language_branch_fails` green; no `if language ==` |

**AC-validation:** AC1/AC3/AC4 are mechanically testable; AC2 is proven by construction + a meta-assertion that the module body carries no per-adapter literal.
**Clarifications (j):** 0 — standing approval to choose the approach; no blocking WANT-decisions.

**Blast radius (read):** 4 one-shot `--file` spawn sites today — `php_adapter_cli.py:33` (canonical), `test_php_adapter_spike.py:112` (stray-copy fail-loud, rc=2), `test_php_adapter_grammar.py:109,135`, `test_php_adapter_server.py:253`. AC4 is **violated today** — the split must consolidate them. 10 modules import `ENTRY/FIXTURES/PHP/ROOT/needs_php/parse_file` from `php_adapter_cli`; those names must survive to keep AC1 churn-free.

## Design

**Approach — extract the generic spawn + a data registry; PHP becomes one row.**

1. **`tests/adapter_cli.py` (new, generic).** Holds the **single** `subprocess.run(... "--file" ...)`
   in `run_adapter_file(entry, repo_relative, *, timeout=60) -> CompletedProcess`. A frozen
   `AdapterCli` dataclass carries `(name, adapter_dir, entry, fixtures_dir, availability)` and exposes
   `parse_file(repo_relative) -> dict` (asserts rc 0 + one-line stdout, returns parsed JSON). This is
   the "one place" AC4 names.
2. **`tests/php_adapter_cli.py` (kept, now a PHP binding).** Builds the PHP `AdapterCli` instance and
   **re-exports** `ROOT, ADAPTER, ENTRY, AUTOLOAD, FIXTURES, PHP, needs_php, parse_file` so all 10
   importers stay byte-unchanged (AC1 churn control). `parse_file` delegates to the instance; no second
   `subprocess.run` here.
3. **`tests/contract/adapter_registry.py` (new, data).** `REGISTRY: dict[str, AdapterConformance]`
   keyed by adapter **directory name**. `AdapterConformance` = `(cli, named_inventory: frozenset,
   excluded_fixtures: frozenset, cases: dict[str, CaseSpec])`. PHP is the one entry; its `CASES`,
   `R62_CASES`, `INCLUDE_EDGE_SHAPES`, `STATIC_VS_INSTANCE_EDGE_SHAPES` **move here unchanged**.
   `CaseSpec` gains an optional 4th field `exact_edge_shapes` so the two deep-shape cases become data,
   not module-body branches (R6.7 shape).
4. **`tests/contract/test_adapter_conformance.py` (rewritten body).** Parametrizes over
   `[(name, case) for name in REGISTRY for case in REGISTRY[name].cases]`, applying each adapter's
   availability marker via `pytest.param(marks=…)`. No per-adapter literal in the body (AC2). Adds
   `test_registry_is_non_empty` (AC3) and the generic inventory test.
5. **AC4 consolidation.** Route `test_php_adapter_grammar.py` (:109,135) and `test_php_adapter_server.py`
   (:253) through `parse_file`. Route `test_php_adapter_spike.py`'s stray fail-loud test (:112) through
   `run_adapter_file` (it needs rc=2 from a relocated entry — the same one spawn, different entry).
   Add the AC4 guard in `test_guardrail_gates.py`: exactly one `tests/` module contains the `"--file"`
   argv literal (backtick/comment mentions don't match the quoted string).

**Rejected alternatives.**
- *Leave the PHP-specific `if case == …` deep blocks in the module body* — fails AC2's "no edit inside
  the module body"; they belong in the case data.
- *A base class / plugin ABC for adapters* — R1.2/R7.4: this is **test infrastructure** (a data table),
  not a core seam; the core keeps its single contract seam. No ABC.
- *Drop the FCC secondary assertion silently* — kept honest: its `{"CONTAINS": 3}` histogram already
  implies "no CALLS", so no `exact_edge_shapes` is needed for FCC and no coverage is lost; noted in a
  comment.

**Rule-compliance.** R1.1: the table keys on **directory name**, not a language name — no branch. R3.4:
the harness now *is* substitutable. R6.5: AC3 is the guard-the-guard (zero adapters ⇒ fail). R6.7: the
valid-adapter set is the registry, derived not listed. R6.1: guards are real pytest.

**Proving test(s).** `tests/contract/test_adapter_conformance.py` (PHP cases byte-identical, AC1),
`test_registry_is_non_empty` (AC3), the AC4 guard in `test_guardrail_gates.py`, and a meta-assertion
that the conformance body carries no `"php"` literal (AC2).

**Change-list (files):** `tests/adapter_cli.py` (new) · `tests/php_adapter_cli.py` (refactor to binding)
· `tests/contract/adapter_registry.py` (new) · `tests/contract/test_adapter_conformance.py` (rewrite
body) · `tests/contract/test_guardrail_gates.py` (+AC4 guard) · `tests/test_php_adapter_spike.py`,
`tests/test_php_adapter_grammar.py`, `tests/test_php_adapter_server.py` (route through the one spawn).
Core diff empty.

## Execute — proof

- **Proving tests (all green, PHP present on the Windows dev host):** `test_adapter_conforms[php:*]`
  (11 cases, AC1 byte-identical) · `test_the_conformance_inventory_is_the_named_set[php]` ·
  `test_the_registry_is_non_empty` (AC3) · `test_ac4_exactly_one_module_spawns_an_adapter_in_one_shot_file_mode`
  (AC4) · `test_ac2_conformance_body_names_no_adapter_directory_literal` (AC2). 54 passed / 0 skipped
  across `tests/contract/` + the 3 routed spawn modules; 13 passed / 31 skipped across the 10 helper
  importers (imports resolve, AC1 no churn).
- **R6.5 red-runs recorded:** planting a 2nd `--file` spawn → AC4 guard FAILED
  (`['_tmp_red_spawn.py', 'adapter_cli.py']`); clearing `REGISTRY` → `test_the_registry_is_non_empty`
  AssertionError.
- **ruff:** clean on all 8 files. **mypy:** unaffected (checks `code_atlas`+`onboarding_llm` only; its
  5 errors are the pre-existing Windows `fcntl` noise in `index_lock.py`, green on POSIX/Docker).
- **Delta-green host:** Windows dev host (`python` 3.12.10, PHP + composer vendor present). Full suite
  still requires Docker for the `fcntl`-bound modules (README *Testing*) — unchanged by this diff,
  which is test-infra only, core diff empty.
- **Scope sweep:** diff = the approved change-list exactly (8 files + working doc); `.mango/` is mango's
  pre-existing untracked workspace, not committed.

## Counted lines — finalise

CLAIMS: 2 claim(s) from 1 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified
RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)
FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)
RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path
PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md (R6.5, R6.7 — already binding; seen bumped) | mango files written: 0
LEDGER TOTAL: 0 tokens · top cost driver: none (solo main-loop run; no subagents dispatched)

- Both claims are sightings of handles already binding as rules (R6.5, R6.7); `seen:` bumped in
  `LESSONS.md` (rec 11→12, 14→15). No new rule proposed, so `/mango:promote` has nothing to carry.

## Counted lines — design

HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply | 0 unanswered
EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor

- **HANDLES trace.** `prove-the-guard-fails` (R6.5) → execute records a **red run** of the AC3
  zero-adapter guard and the AC4 spawn guard before the fix; applies. `derived-not-listed-invariant`
  (R6.7) → the valid-adapter set is `REGISTRY.keys()`, derived not listed; applies.

## Counted lines — analysis

PREMISE: 2 references checked | 0 missing | 0 ambiguous (surfaced, not blocking)
RECALL: 2 claims surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)
REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes
SECTIONS: 5 found (Why this exists, Scope, Acceptance criteria, Not in scope, References) | 5 decomposed | ROWS: C=2 R=4 G=1 AC=4
CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision
RULE SECTIONS: 5 applicable — 3 by change-type | 2 by recalled handle — R3.4 (change-type) ✅ | R1.1 (change-type) ✅ | R6.1 (change-type) ✅ | R6.5 (recalled: prove-the-guard-fails) ✅ | R6.7 (recalled: derived-not-listed-invariant) ✅

## Cost ledger

| phase | dispatch | tokens |
|---|---|---|
| analysis | main loop | unmeasured (host does not surface usage; review/challenger waived) |
