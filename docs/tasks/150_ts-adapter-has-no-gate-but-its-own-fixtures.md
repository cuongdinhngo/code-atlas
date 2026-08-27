---
id: 150
slug: ts-adapter-has-no-gate-but-its-own-fixtures
title: The TS adapter's only validation is its own fixtures — no static analyser (R6.6), no cross-repo run (R6.3)
phase: 2
milestone: M7
status: done
depends_on: [019, 018, 148]
---

## Why this exists

Adapter #2 landed in [019](019_typescript-adapter.md) with ~500 lines of authored JavaScript and
**zero static analysis**. `adapters/typescript/package.json` declares one script (`start`) and no
devDependencies; `scripts/gate.sh:121` runs `npm ci --prefix adapters/typescript` and then nothing
else for that language. Compare the PHP adapter in the same job: `composer validate --strict`,
`php -l`, **`phpstan level max`**. R6.6 says every language gets a static analyser at its strictest
clean setting and *"each later adapter brings the equivalent"* — for adapter #2 that has simply not
happened, and the rule is unmet while the adapter is on the release path.

The second half is worse, because it is the half that would have caught real defects. R6.3 wants
several varied repos indexing without crashes and with sane counts, *"no single repo defines
correct"*. `scripts/cross_repo_validate.py` is that reporter — and it is PHP-shaped end to end:
`resolve_php_cmd()` at line 105, `env["CA_PHP_CMD"]` at line 166, a hard-wired
`adapters/php/index.php` argv at line 37, and `scripts/cross_repo_samples.json` whose own
`contract_note` says *"Pinned public PHP samples"*. So the TS adapter has never been run against a
repo it did not ship its own fixtures for.

**The evidence that this is not hypothetical.** 019's review found five defects. All five were
invisible to a green 2039-test fixture suite, and three of them are exactly what a first real-repo
run surfaces on contact:

| defect | why a fixture suite could not see it |
|---|---|
| `declarations_only` dropped every CommonJS `IMPORTS` | the one fixture in that test was ESM |
| a default-import of `export default class Foo` resolved to a qname no node had | no fixture used a *named* default export — the commonest TS/React shape |
| a NodeNext `./x.js` specifier matched a compiled `./x.js` over the `./x.ts` source | no fixture tree had both, which any repo that commits build output does |

This is `fixture-shape-begs-the-question` (R6.3's own class, `105-C2`) sighted on adapter #2, and
[148](148_r22-framework-sweep-cannot-fail-for-adapter-2.md) already recorded the sibling shape: a
guardrail that cannot fail for this adapter. Filing the feature slices ahead of these two gates would
add surface to an adapter whose only judge is the fixtures its author wrote.

## Scope / Deliverables

**A — R6.6: a static analyser for the TS adapter, strictest clean.**
- The adapter source is authored as CommonJS **`.js`**, so "the equivalent of PHPStan max" is a
  *choice*, not a given: `tsc` with `checkJs`+`strict` over `adapters/typescript/**/*.js`, an ESLint
  config at its strictest, or both. **Design resolves which and writes down why** — this ticket does
  not pre-pick it.
- Wired into `scripts/gate.sh` **and** `.github/workflows/ci.yml` in the `adapters` job, beside the
  PHP three, following the gate's existing shape: a real `_run` when the tool is on PATH, `_record
  SKIP` when it is not — never a silent pass (R6.5, and the gate exits 2 on a skip).
- Findings are fixed, not suppressed: no baseline file, no blanket `eslint-disable`, no
  `@ts-nocheck` (R6.6 is explicit that suppression is not how a finding is closed).
- The tool and its config live under `adapters/typescript/` and never reach the Python core (R8.1);
  `node_modules/` stays git-ignored with the lockfile committed (R8.3).

**B — R6.3: cross-repo validation for TypeScript on ≥ 3 varied public repos.**
- Generalise `scripts/cross_repo_validate.py` from one language to a per-adapter reporter — the same
  move [147](147_contract-harness-is-php-shaped.md) made for `tests/contract/`: the adapter argv and
  the sample list become **data**, so adding a language is a row, not an edit to the module body.
  The PHP path must come out byte-identical (its floors are pinned to a SHA).
- A TS/JS sample set pinned by SHA with `min_files`/`min_nodes`/`min_edges` floors, in
  `scripts/cross_repo_samples.json`'s existing shape and **named by repo, never by framework** — the
  samples file already sits outside `adapters/` for exactly that reason (R2.2).
- Sample **variety is the deliverable**, not the count: at minimum a `.ts`-only library, a
  mixed `.ts`/`.js` app, and one that commits compiled output beside its sources (the tree that
  exposed defect #3 above). Design names the three and says what shape each contributes.
- Floors are set from a recorded good run at the pinned SHA (~80% of it, matching the PHP note), and
  the reporter prints the real inputs each floor came from so it can be re-justified (R6.3's
  committed-reporter half).

## Acceptance criteria

1. `scripts/gate.sh` and `ci.yml` both run a static analyser over the TS adapter source at its
   strictest setting, and the run is **clean with no suppressions**; the check `SKIP`s (never
   `PASS`es) when the tool is absent, and `gate.sh` still exits 2 on that skip.
2. The chosen analyser and the rejected alternative are written down — in the adapter README, with
   the reason — so the next adapter does not re-litigate it.
3. `cross_repo_validate.py` runs both adapters from one code path, with the adapter argv and sample
   list as data; the PHP run's reported numbers are unchanged.
4. ≥ 3 pinned TS/JS repos index with `failed == 0` and every floor met, including one tree that
   carries compiled `.js` beside `.ts`.
5. A red run is recorded for each new guard (R6.5): the analyser fails on a deliberately
   ill-typed line, and a floor fails when its sample SHA is moved back.
6. Any defect the cross-repo run finds is filed, not fixed silently in this ticket — the point of
   the gate is to learn what the fixtures hid.

## Out of scope

- **Fixing whatever the cross-repo run turns up.** Findings become tickets; this ticket ships the
  gate, and a mixed change would hide how much the gate actually caught.
- Feature breadth: `allowJs`/JSDoc, tsconfig `paths`, `semantic_types` —
  [154](154_ts-allowjs-and-jsdoc-types.md), [155](155_ts-tsconfig-paths-and-export-star.md),
  [153](153_ts-declared-and-inferred-types.md).
- Adapters #3–#4. Still deferred (PLAN §19).

## References

PLAN §4.4, §15 (M7); ENGINEERING_RULES R6.3, R6.5, R6.6, R8.1, R8.3, R2.2; tasks 018 (the PHP
cross-repo run this mirrors), 147, 148, 019.

---

## Session status

- **KEY:** 150
- **work_doc_mode:** embed (below this separator).
- **Run args:** autorun, "with skipped review" (maintainer). Challenger OFF; reviewer/Gate 4 waived — maintainer reviews on the PR.
- **Phase:** 5 finalise — complete; delta-green in Docker; → PR #192.
- **BASELINE:** bare pytest red on Windows (`import fcntl`); delta-green via Docker (`scripts/docker-test.sh`), the host that also carries the node TS adapter.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

Surfaced references all resolve: `adapters/typescript/package.json`, `scripts/gate.sh:121`, `scripts/cross_repo_validate.py` (`resolve_php_cmd`/`CA_PHP_CMD`/`adapters/php/index.php`), `scripts/cross_repo_samples.json`, `.github/workflows/ci.yml` (adapters job), `adapters/php/index.php`.

Recall (advisory, by handle): `105-C2 fixture-shape-begs-the-question` (type-2, seen 084/103/104/086/105/106 — a promotion candidate) — "when an AC needs a real-repo judgement, ship a committed reporter, not an ad-hoc run"; precedent `scripts/layer_report.py`. Directly governs Deliverable B: the pinned `cross_repo_samples.json` + committed reporter IS that shape.

Two HOW-decisions the ticket explicitly delegates to design (both resolved+cited, neither a want-decision — the acceptance bar is fully set by the ticket, so `j = 0`):
- **Which static analyser** (ticket line 50 "Design resolves which and writes down why"). Resolved: `tsc --checkJs --strict`. See design.
- **Which 3 TS/JS repos** (ticket lines 67-69 "Design names the three"). Resolved empirically; see design.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend (0 UI files) · **SCOPE:** M · **TIER:** full

`SECTIONS: 3 found (Scope/Deliverables, Acceptance criteria, Out of scope) | 3 decomposed | ROWS: C=6 R=8 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 7 applicable — 6 by change-type | 1 by recalled handle — §R6.3 (recalled handle 105-C2) ✅ · §R6.6 (change-type) ✅ · §R6.5 (change-type) ✅ · §R8.1 (change-type) ✅ · §R8.3 (change-type) ✅ · §R2.2 (change-type) ✅ · §R7.2 (change-type) ✅`
`BASELINE: red — bare pytest fails at collection (import fcntl, Windows platform exclusion); delta-green via Docker before PR`

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | preamble | "ship the gate … learn what the fixtures hid" | Two gates (static analyser + cross-repo run) exist for the TS adapter; found defects are FILED, not fixed here | none today | open |
| R1 | A | "static analyser for the TS adapter, strictest clean" | An analyser runs over `adapters/typescript/**` at its strictest *clean* setting | none | open |
| R2 | A | "Wired into gate.sh AND ci.yml … `_run`/`_record SKIP`, never a silent pass" | Both runners run it; SKIP (exit 2) when tool absent | `gate.sh` phpstan shape | open |
| R3 | A | "Findings fixed, not suppressed: no baseline, no blanket disable, no @ts-nocheck" | Clean with zero suppressions | — | open |
| R4 | A | "tool + config under adapters/typescript/; never reach the core (R8.1); node_modules ignored, lock committed (R8.3)" | Config local; `.gitignore` keeps node_modules; lock committed | `.gitignore`, lock | open |
| R5 | B | "Generalise cross_repo_validate.py … adapter argv + sample list as DATA … PHP byte-identical" | One code path, per-language adapter cmd as data; PHP counts unchanged | `resolve_php_cmd`/`index_root` PHP-only today | open |
| R6 | B | "TS/JS sample set pinned by SHA with floors, named by repo not framework (R2.2)" | Samples in existing shape, `language`-tagged, repo-named | `cross_repo_samples.json` | open |
| R7 | B | "variety is the deliverable: .ts-only lib, mixed .ts/.js app, one committing compiled .js beside .ts" | 3 shapes named + justified | — | open |
| R8 | B | "floors from a recorded good run (~80%); reporter prints real inputs each floor came from" | Floors ≈80% of measured; report records files/nodes/edges | report JSON already records counts | open |
| AC1 | AC1 | analyser runs in gate.sh + ci.yml, clean no suppressions; SKIPs (never PASS) when absent, gate exits 2 | Falsifiable: read both runners; run clean; absence → SKIP+exit2 | new gate.sh/ci.yml blocks | open |
| AC2 | AC2 | chosen analyser + rejected alternative written in README with reason | Falsifiable: README section names tsc + rejects eslint w/ reason | README edit | open |
| AC3 | AC3 | both adapters from one code path, argv+samples as data; PHP numbers unchanged | Falsifiable: unit test on per-language cmd; PHP counts identical | `test_index_root`/new unit | open |
| AC4 | AC4 | ≥3 pinned TS/JS repos index with failed==0, floors met, incl. one compiled-.js-beside-.ts tree | Falsifiable: Docker cross-repo run green on 3 repos | measured run | open |
| AC5 | AC5 | red run recorded per new guard: analyser fails on ill-typed line; a floor fails when SHA moved back | Falsifiable: recorded red outputs | red-run capture | open |
| AC6 | AC6 | any cross-repo defect is FILED, not fixed here | Falsifiable: findings → new tickets, not in this diff | — | open |
| C1 | Out-of-scope | no fixing what the run turns up | boundary | — | binding |
| C2 | Out-of-scope | no feature breadth (allowJs/JSDoc/paths/semantic_types → 153/154/155) | boundary; `noImplicitAny` deferral points at 154 | — | binding |
| C3 | Out-of-scope | adapters #3–#4 stay deferred | boundary | — | binding |
| C4 | R8.1 | analyser + config never reach the Python core | tsconfig lives under adapters/typescript only | — | binding |
| C5 | R8.3 | node_modules ignored, lockfile committed | — | — | binding |
| C6 | R2.2 | samples named by repo, never framework; outside adapters/ | samples in scripts/ | — | binding |

### AC validation (independently re-derived)

- All six ACs are falsifiable (read-both-runners / run-clean / unit test / Docker green / recorded red output / diff-is-gate-only). None a bare ✅.
- No AC-value mismatch. "≥3 repos, floors ≈80%, clean no suppressions" all taken verbatim from the ticket; the ticket sets the whole acceptance bar, so refine raised no want-decision.
- The analyser-choice tension ("strictest" vs "clean") is resolved by the ticket's own "the equivalent is a *choice*, Design resolves which" — a HOW, cited; design records tsc-strict-minus-`noImplicitAny` with the deferral pointer to 154.

### Root cause (taxonomy: validation)

The TS adapter is on the release path with no static analyser (`package.json` had one `start` script, no dev tooling) and a cross-repo reporter (`cross_repo_validate.py`) hard-wired to PHP (`resolve_php_cmd`, `env["CA_PHP_CMD"]`, `_DEFAULT_PHP`). Both guardrails structurally cannot fail for adapter #2 — R6.6 unmet, R6.3 never exercised.

### Blast radius

- Analyser: `adapters/typescript/{tsconfig.json,package.json,package-lock.json}`, `src/parse.js` (2 real findings), `scripts/gate.sh`, `.github/workflows/ci.yml`, `adapters/typescript/README.md`.
- Cross-repo: `scripts/cross_repo_validate.py` (per-adapter generalisation), `scripts/cross_repo_samples.json` (TS rows), `tests/test_cross_repo_validation.py` (manifest test grows to multi-adapter).
- PHP path: byte-identical (php samples keep no `language` → default `php` → `resolve_adapter_cmd("php") == resolve_php_cmd()`).
- Repos touched: `app` only. No core (`code_atlas/`), no contract, no store, no schema.

## Phase 2 — design

### Approach

**A — analyser.** `tsc --checkJs --strict` over `index.js`+`src/**/*.js`, configured by a committed
`adapters/typescript/tsconfig.json`, `@types/node` pinned in `devDependencies`. One strict flag held
off — `noImplicitAny` — because the source is deliberately untyped and full strict reports ~72
implicit-any params that only per-parameter JSDoc (task 154) closes; the tsconfig carries a forward
pointer and 154 flips it on. Not a suppression: no baseline, no `@ts-nocheck`, no `eslint-disable`.
Two genuine findings fixed in `src/parse.js` (unknown-typed catch var; internal-API `parseDiagnostics`
via a documented cast). Wired into `gate.sh` (binary-guarded `_run`, else `_record SKIP` → exit 2) and
`ci.yml` (setup-node + `npm ci` + tsc), beside the PHP three.

**B — cross-repo.** `cross_repo_validate.py` gains an `_ADAPTERS` data table `{language: {env, default}}`;
`resolve_php_cmd` becomes `resolve_adapter_cmd(language)` (PHP wrapper kept); `index_root(language=…)`
sets that language's env var; each sample declares `language`. PHP samples omit it → default `php` →
byte-identical. Reporter rows gain a descriptive `language` key (counts unchanged).

### Rejected alternatives

- **ESLint (strictest preset)** — a linter, not a type analyser; phpstan's analogue is type analysis, and `typescript` is already a committed dep, so tsc adds no new toolchain. ESLint adds a large devDep tree. Rejected.
- **Full `--strict` incl. `noImplicitAny`** — not clean on intentionally-untyped source; annotating every param is task 154's JSDoc work. Turning it on now would either force suppressions (banned by AC3) or pull 154 into this ticket. Rejected; deferred with a pointer.
- **A per-language `if language == …` branch in the reporter** — a code branch is exactly what task 147 removed for the conformance harness; kept it as an `_ADAPTERS` data row instead.

### The HOW-decisions (delegated by the ticket)

- **Analyser = tsc.** Recorded in `README.md` (AC2), reason above.
- **The three repos** (empirical, indexed in Docker to set floors — the `105-C2` committed-reporter shape): a `.ts`-only library, a mixed `.ts`/`.js` repo, and one committing compiled `.js` beside `.ts`. Named + counted in execute.

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

`105-C2` (fixture-shape-begs-the-question) traced: the deliverable is a committed re-runnable reporter over pinned real repos (`cross_repo_validate.py` + `cross_repo_samples.json`), not an ad-hoc run — exactly what the handle prescribes; floors are set from a recorded good run and the report prints the inputs.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | config (gate wiring) | read both runners + run tsc clean | ✅ |
| AC2 | docs | README section | ✅ |
| AC3 | logic (per-language cmd) | unit test + PHP-unchanged reasoning | ✅ |
| AC4 | integration (real repos) | Docker cross-repo green on 3 | ✅ |
| AC5 | validation (guard fails) | recorded red outputs (tsc; floor) | ✅ |
| AC6 | process | findings filed as tickets, not in diff | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

### Proving test

`test_resolve_adapter_cmd_is_per_language` + `test_manifest_covers_both_adapters` in
`tests/test_cross_repo_validation.py`: the first asserts `resolve_adapter_cmd("typescript")` yields the
node adapter command and `"php"` the php one (the data-driven one-code-path claim, AC3); the second
asserts the manifest carries both languages with the three TS shapes and valid floors/sha/url (AC4
shape). Fails pre-change (`resolve_adapter_cmd` did not exist; manifest was PHP-only). Full delta-green
+ the live 3-repo Docker run before the PR.

Invocation: `pytest tests/test_cross_repo_validation.py -q`.

### SCOPE

`SCOPE: M` — analyser config + 2 source fixes + two runner edits + a reporter generalisation + samples
+ one test rewrite. No core, contract, store, or schema. Branch `feat` matches.

## Phase 3 — execute

**Branch:** `feat/150-ts-adapter-gate`

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `tsc --checkJs --strict` via committed `tsconfig.json`, `@types/node` pinned, `noImplicitAny` deferred to 154 | implemented-as-approved |
| 2 real findings fixed in `parse.js` (unknown catch var; `parseDiagnostics` cast), no suppressions | implemented-as-approved |
| Wired into `gate.sh` (binary-guarded `_run`/`_record SKIP`) + `ci.yml` (setup-node + npm ci + tsc) | implemented-as-approved |
| README records tsc chosen, ESLint rejected, with reasons (AC2) | implemented-as-approved |
| `cross_repo_validate.py` per-adapter `_ADAPTERS` data table; `resolve_php_cmd` wrapper kept; PHP byte-identical | implemented-as-approved |
| 3 TS samples (ky / mqttjs / socketio) pinned by SHA with ≈80% floors, repo-named | implemented-as-approved |

No deviations. `SCOPE: M` held.

### Verification sweep (Axis 1 — file set)

Diff = `adapters/typescript/{tsconfig.json,package.json,package-lock.json,README.md,src/parse.js}`,
`scripts/{gate.sh,cross_repo_validate.py,cross_repo_samples.json}`, `.github/workflows/ci.yml`,
`tests/test_cross_repo_validation.py`, this working doc + `docs/BACKLOG.md`/`docs/TOKEN_LEDGER.md`
(finalise). All in the approved list; no file outside; no core/contract/store/schema touched. `.mango/`
is pre-existing untracked.

### Empirical outputs

Analyser clean (`tsc -p adapters/typescript/tsconfig.json`): `No errors found`, exit 0.

Red-run AC5 (analyser): an ill-typed line yields
```
src/qname.js(19,28): error TS2322: Type 'string' is not assignable to type 'number'.  → exit 2
```
Red-run AC5 (floor): ky `min_edges` raised to 999999 →
```
public_failed: 1 — PlausibleCountsError: ky: edges must be >= 999999, got 7781
```

Cross-repo run, one code path, both adapters (Docker, node+php in image), `public_ok=6 public_failed=0`:
```
laravel_app  php         files=28   nodes=76    edges=460    failed=0
symfony_demo php         files=60   nodes=461   edges=1678   failed=0
brick_math   php         files=32   nodes=887   edges=3753   failed=0   (PHP counts unchanged vs 018)
ky           typescript  files=54   nodes=543   edges=7781   failed=0
mqttjs       typescript  files=80   nodes=725   edges=6208   failed=0
socketio     typescript  files=371  nodes=3533  edges=60651  failed=0   (compiled .js beside .ts)
```

### Findings for follow-up (AC6 — filed, not fixed here)

The cross-repo run surfaced **no crash and no floor miss** on the three pinned TS repos (`failed=0`
across 505 TS/JS files). No new defect ticket is owed from this run; the gate now exists to catch the
next one. (Construct-level resolution depth — member calls, aliases, `export *` — is already owned by
150's siblings 152/153/155, not re-filed here.)

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `gate.sh`/`ci.yml` tsc blocks (binary-guarded SKIP→exit 2); `tsc -p …` clean exit 0 |
| AC2 | `adapters/typescript/README.md` "Static analysis (R6.6)" section |
| AC3 | `test_resolve_adapter_cmd_is_per_language` + PHP counts identical in the 6-sample run |
| AC4 | cross-repo run: ky/mqttjs/socketio `failed=0`, floors met, socketio = compiled-beside-source |
| AC5 | recorded tsc `TS2322` red-run + floor `PlausibleCountsError` red-run |
| AC6 | no defect filed (run was clean); gate committed for the next run |

## Phase 5 — finalise

### Delta-green (Docker / Linux host — node + php in the image)

```
full suite → 2133 passed, 1 skipped, 0 failed (165.58s)  [ruff + mypy + pytest, image default CMD]
tsc -p adapters/typescript/tsconfig.json → No errors found (exit 0)
cross-repo (6 samples) → public_ok=6 public_failed=0
```
Bare pytest on Windows is red at collection (`import fcntl`) — the recorded platform exclusion;
delta-green confirmed in-container per README *Testing*.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

New claim `150-C1` (type-2, `analyser-choice-for-an-untyped-adapter`, seen: 150) recorded in
LESSONS.md as `proposed`; seen=1 → not a promotion candidate, legitimately stays in lessons_path.

`105-C2 fixture-shape-begs-the-question` was surfaced by **advisory recall at refine** (not a claim
this finalise captures), and it applied — the deliverable is a committed re-runnable reporter over
pinned real repos, exactly its prescription. Its cross-ticket recurrence (seen ≥ 2 across 084/103/104/086/105/106)
is `/mango:promote`'s pass to route, not a single ticket's finalise; this run neither re-counts nor
edits it.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; review phase waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

0 subagent dispatches this run → ledger complete with 0 rows.

### Review

SKIPPED per run arg "with skipped review" (AGENTS.md convention). Gate 4 waived, not reintroduced.
Self-checks stood in: tsc clean, ruff clean repo-wide, per-language unit test green on host, and the
full Docker delta-green below. Maintainer reviews on the PR.
