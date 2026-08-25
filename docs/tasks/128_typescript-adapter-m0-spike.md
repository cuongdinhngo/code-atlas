---
id: 128
slug: typescript-adapter-m0-spike
title: TypeScript/JavaScript — M0 spike only, to answer §4.4 with evidence instead of anticipation (M7 precursor)
phase: 2
milestone: M7
status: done
depends_on: [012, 147, 149]
---

## Why this exists, and why now

[019](019_typescript-adapter.md) is the full M7 adapter and stays **deferred**. This ticket is its
**M0 equivalent** — the [006](006_php-adapter-spike.md)-shaped spike, and nothing beyond it.

**The dependency ran backwards until 2026-08-24.** This ticket used to declare `depends_on: 019`,
which is the reverse of what it is: 019 cannot start until the spike answers §4.4. It now depends on
[147](147_contract-harness-is-php-shaped.md) (the conformance harness admits one adapter today, so
AC1 has nowhere to run) and [149](149_tsjs-construct-inventory.md) (AC1 names two files without
saying what either contains).

PLAN §19 ratified *depth before breadth* because the anchor monorepo makes PHP measurable. **That still
holds and this ticket does not reopen it.** What has changed is what depth is buying: the last several
onboarding tickets — [098](098_correspondence-relation-seam.md),
[120](120_subtree-dependency-attribution.md), and the auto-doc proposal — are all held or shaped by
**n = 1**, and n = 1 is a property of having exactly one adapter, not of having too few PHP features.
This spike is the cheapest test of whether the contract survives contact with a second language.

**This reasoning is a proposal, not a decision.** Whoever picks the ticket up reads §19 and §4.4 first;
if they disagree, they say so in the PR and stop. Silently reordering the roadmap is the failure mode
this paragraph exists to prevent.

## Scope

- `adapters/typescript/` (019's name, not the work order's `adapters/ts/` — CONVENTION owns the path)
  parses **one module-scoped file** and **one namespaced-equivalent module** into contract JSON that
  passes `tests/contract/`.
- Nothing else: no resolver work, no tool changes, no core changes, no registry, no `contract_version`
  bump in this ticket.

## The deliverable is the §4.4 report

The spike exists to answer three questions with evidence. The write-up is worth more than the code:

1. **Does `MEMBER_SEPARATOR` hold?** TS/JS has no namespaces, so qnames are module-path-anchored
   (`src/user.ts::User::save`). Does the convention hold, or does it bend — and if it bends, where?
2. **Which of §4.4's two options does the spike actually need** — an `open_project(root)` lifecycle
   holding the tsconfig program, or the two-pass mode? The v1 protocol is file-at-a-time and the
   TypeScript Compiler API resolves imports and types only against a whole program.
3. **Does a second adapter force a `contract_version` bump, and if so, what exactly changes?** One
   answer, with evidence, not a guess.

## Acceptance criteria

1. **AC1.** One module-scoped file and one namespaced-equivalent module pass `tests/contract/`
   unchanged.
2. **AC2 — R1.1 is the acceptance test.** If making this work requires **any** branch under
   `code_atlas/` that keys on language, the contract leaked: **stop**, and write up where it leaked
   instead of adding the branch. That write-up closes the ticket successfully.
3. **AC3.** The three §4.4 answers land in PLAN §4.4, each with the evidence that produced it.
4. **AC4.** Core diff is empty. `adapters/typescript/` is self-contained and launched via
   `CA_TYPESCRIPT_CMD`, mirroring the PHP adapter's `CA_PHP_CMD` shape.
5. **AC5.** Time-boxed. If project-context resolution turns out to be larger than a spike, **that
   finding is the deliverable** — record it in PLAN §4.4 and close the ticket.

## Not in scope

Path aliases, ESM/CommonJS resolution breadth, `allowJs`, `semantic_types`, CI's second runtime, and
the adapter registry. All of that is 019.

---

MANGO WORKING DOC (below this line is NOT part of the raw ticket)

## Session status
- **Phase:** finalise
- **TIER:** full
- **TRACK:** backend
- **SCOPE:** M
- work_doc_mode: embed (plain local-file tracked ticket, not a scaffold stub)
- CHALLENGER: ON · review phase: ON (args revised mid-run 2026-08-25: "run mango review & challenger")
- branch: feat/128-typescript-adapter-m0-spike (created at design)
- working doc: this file, below the separator

## Phase 0 — refine

`PREMISE: 8 references checked | 0 missing | 0 ambiguous (surfaced, not blocking)`

Checked and resolved: 006, 012, 019, 147, 149 (all `docs/tasks/*`), PLAN §4.4 (line 202), PLAN §19
(line 699), and the `CA_PHP_CMD` / `CA_TYPESCRIPT_CMD` config surface (`code_atlas/config.py`,
`tests/test_config.py:266`). No source the ticket cites as already-existing is missing.

`RECALL: 4 claims surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

By handle (from `docs/LESSONS.md`): `prove-the-guard-fails` (147, 148 — a new guard ships with a
recorded red run), `derived-not-listed-invariant` (147, 148 — the registry row is derived data, not a
hand-listed set), `verify-cited-reference-at-pickup` (149 — re-verify a file:line citation before
building on it), `empty-seam-inputs-masquerade-as-missing-data` (118 — a valid parse with no imports
must not read as a failed one).

`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions. The ticket's want is unambiguous — a 006-shaped spike
plus the §4.4 write-up. The three §4.4 questions are the spike's *deliverable*, resolved by evidence in
design, not refinement gaps that block starting. The user invoking the ticket ratifies the §19
"proposal, not a decision" framing.

## Analysis (Gate 1)

`SECTIONS: 4 found (scope · deliverable · acceptance-criteria · not-in-scope) | 4 decomposed | ROWS: C=3 R=2 G=3 AC=5`

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

1. Which TS parser API — a whole-Program (`open_project`/tsconfig) or a single-file parse?
   → **`ts.createSourceFile`** (syntactic, file-at-a-time). Cited: §4.4 (line 209-218) — the two facts
   narrow the choice to "less to resolve than assumed"; a Program is needed only for `semantic_types`,
   which is out of scope.
2. Does a TS `namespace` nest its members with a native separator (`Foo.Bar`) or the contract's `::`?
   → **`::` uniformly**; the module path is the container root. Cited: `contract.py:8-12` docstring
   (`src/user.ts::User::save`) + `MEMBER_SEPARATOR` (`contract.py:167`).

Neither is a human decision (`j = 0`) — both resolve against the plan and the contract, and the user's
standing approval covers approach choice. No Gate 0.

`RULE SECTIONS: 9 applicable — 7 by change-type | 2 by recalled handle — R1.1 (AC2, no lang branch) ✅ · R1.2 (adapter #2 now exists — seam allowed) ✅ · R1.4 (adapter parses only, no store import) ✅ · R2 (fixtures encode the TS spec, not a repo) ✅ · R3 (Q3 — contract frozen unless a bump is proven) ✅ · R4.2 (createSourceFile is deterministic) ✅ · R6.2 (fixtures from the 149 named inventory) ✅ · R6.5 (new guards ship a red run) ✅ · R6.7 (registry row is derived, not hand-listed) ✅`

### Coverage matrix (TIER: full)

| id | source | requirement | how it is met | verified by |
|----|--------|-------------|---------------|-------------|
| G1 | §4.4 Q1 | answer MEMBER_SEPARATOR with evidence | `::` holds; module path is the root; TS `.` normalised | fixture exact_edge_shapes + PLAN §4.4 write-up |
| G2 | §4.4 Q2 | answer lifecycle vs two-pass with evidence | neither — createSourceFile, file-at-a-time | adapter uses no Program; both fixtures pass |
| G3 | §4.4 Q3 | answer contract_version bump with evidence | no bump — existing vocabulary only | `contract.validate()==[]`; CONTRACT_VERSION==8 |
| R1 | Scope | `adapters/typescript/` parses 2 files → contract JSON | Node sidecar, `typescript` pkg, `--file`/`--server` | conformance cases pass |
| R2 | Deliverable | §4.4 report (3 answers + evidence) | PLAN §4.4 updated | doc diff |
| AC1 | AC1 | 1 module-scoped + 1 namespaced module pass `tests/contract/` | registry row + 2 fixtures + ts_adapter_cli | `test_adapter_conforms[typescript:*]` |
| AC2 | AC2 | R1.1: no language branch under `code_atlas/` | sidecar + generic config; zero core edits | R1.1 sweep + empty core diff |
| AC3 | AC3 | the 3 §4.4 answers land in PLAN §4.4 with evidence | write-up cites fixtures + validate result | doc diff |
| AC4 | AC4 | core diff empty; launched via `CA_TYPESCRIPT_CMD` | `ADAPTER_CMD_ENV` already generic | `git diff code_atlas/` empty; test_config.py:266 |
| AC5 | AC5 | time-boxed; a "too big" finding is itself the deliverable | createSourceFile keeps it small; recorded if not | PLAN §4.4 |
| C1 | AC4 | no `code_atlas/` change | no core file touched | empty core diff |
| C2 | AC2 | no `if language ==` leak | sidecar only | R1.1 grep-gate |
| C3 | Not-in-scope | stay within the spike boundary (6 deferrals → 019) | see EXCLUSIONS at design | design gate |

### Design direction (settled at Gate 2)
- `adapters/typescript/`: `package.json` (pins `typescript`, committed lockfile), `index.js`
  (handshake + `--file`/`--server`, mirrors `index.php`), `src/parse.js` (createSourceFile walk),
  `README.md`. R2.2: adapter source names no framework.
- Two fixtures in `tests/fixtures/typescript/`: `module_scoped.ts` (case `module-esm`) and
  `namespaced.ts` (case `namespace-declare`).
- `tests/ts_adapter_cli.py` (delegates to `AdapterCli`; no `--file` literal — AC4 spawn guard) +
  a `typescript` entry in `tests/contract/adapter_registry.py` (data only — AC2 body guard).
- No Docker/CI change (EXCLUSION #5, "CI's second runtime" → 019): the `needs_node` availability
  marker skips the TS cases where node/`npm install` is absent, exactly as `needs_php` skips PHP.
  AC1 is proven on the dev host, where the subprocess-only conformance test runs without `fcntl`.

## Decision log
- 2026-08-25: deps 147+148+149 merged to main; 128 branches cleanly off a main holding all three.
- 2026-08-25: args revised mid-run — review phase and challenger both ON.

## Design (Gate 2)

### Assumptions (checked)
- Node ≥ 18 is present on the build host and in `docker/Dockerfile` (nodejs is installed there for the
  onboarding map). The `typescript` package is the only runtime dep, pinned by a committed lockfile.
- `ts.createSourceFile` gives a full syntactic AST without a Program — enough for nodes, intra-file
  edges, and `IMPORTS` (raw specifier). Verified against the TS compiler API surface.
- The core needs no change: `config.py`'s `ADAPTER_CMD_ENV` already turns `CA_TYPESCRIPT_CMD` into an
  adapter argv (test_config.py:266). Confirmed by reading `_adapter_cmds`.

### Verification plan
- `test_adapter_conforms[typescript:module-esm]` and `[typescript:namespace-declare]` — schema
  (`contract.validate()==[]`), kind histograms, and exact_edge_shapes (pins the `::` qname convention).
- `test_the_conformance_inventory_is_the_named_set[typescript]` — case keys == the named inventory,
  fixtures exist, none excluded.
- `git diff --stat code_atlas/` empty (AC4/C1). R1.1 sweep green (AC2/C2). R2.2 sweep green (no
  framework name in adapter source).
- New-guard red run (R6.5): temporarily break a fixture's expected histogram and a qname to prove the
  conformance case fails, then restore.

`HANDLES: 4 recalled | 4 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `prove-the-guard-fails` → traced: the verification plan ships a recorded red run for the new
  conformance cases before the green one.
- `derived-not-listed-invariant` → traced: the registry entry is a `Case`-valued row; the valid set is
  `set(adapter.cases)`, never a second hand-kept list (`test_adapter_conformance.py:51`).
- `verify-cited-reference-at-pickup` → traced: PREMISE re-verified §4.4/006/012/019/147/149 resolve
  before designing from them.
- `empty-seam-inputs-masquerade-as-missing-data` → traced: the adapter emits `ok=true` with a `File`
  node even for a bare module; a parse failure alone sets `ok=false` (mirrors `index.php`).

`EXCLUSIONS: 6 recorded | 6 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

All six §Not-in-scope items are deferred to **019** (the full M7 adapter); expiry is checkable — each
reopens when 019 is scheduled:
1. path aliases — expiry: 019
2. ESM/CommonJS resolution breadth — expiry: 019
3. `allowJs` — expiry: 019
4. `semantic_types` capability — expiry: 019
5. CI's second runtime — expiry: 019
6. adapter registry beyond the two spike cases — expiry: 019

## Review (Gate 4) — CLEAN
- CHALLENGER: ON — 9/9 reconstructed requirements met, 0 not met, 0 can't-tell (independence held; did not read this working doc).
- Reviewer (round 1): CHANGES REQUESTED — 3 findings (CALLS drops bare edges; header comment >3 lines; ruff E501). All fixed in `b00d2e2` + a red-run fixture for the CALLS fix.
- Reviewer (verify): LGTM — 63 passed, no regressions.
- **Reviewed at b00d2e2** (adapters/typescript/*, tests/fixtures/typescript/*, tests/ts_adapter_cli.py, tests/contract/adapter_registry.py, docs/PLAN.md §4.4).

### Cost ledger (subagent dispatch only)
| phase | dispatch | round | tokens |
|-------|----------|-------|--------|
| review | mango:challenger | 1 | 67,207 |
| review | mango:reviewer | 1 | 129,930 |
| review | mango:reviewer | verify | 51,201 |

## Finalise (final gate)

`CLAIMS: 4 claims from 1 lesson entry | T1=0 T2=3 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`

`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidates`

`FALSIFY: 4 candidates checked | 4 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`

`RECURRING-T2: 2 type-2 claims with seen ≥ 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`

`PROMOTION: 0 proposed | 0 human-ratified | destinations: none (recurring claims already binding as R6.5/R6.7; new claims at recurrence 1) | mango files written: 0`

`LEDGER TOTAL: 248,338 tokens · top cost driver: mango:reviewer (review + verify, 181,131)`

Learning loop: two seen-bumps to binding rules (`prove-the-guard-fails`→14 / R6.5,
`derived-not-listed-invariant`→17 / R6.7) and two new claims (128-C1 emit-don't-gate-on-resolution,
128-C2 per-container symbol scope for 019). No new cross-ticket promotion triggered.
