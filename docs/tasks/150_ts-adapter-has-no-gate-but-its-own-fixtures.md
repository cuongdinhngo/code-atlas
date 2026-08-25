---
id: 150
slug: ts-adapter-has-no-gate-but-its-own-fixtures
title: The TS adapter's only validation is its own fixtures — no static analyser (R6.6), no cross-repo run (R6.3)
phase: 2
milestone: M7
status: todo
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
