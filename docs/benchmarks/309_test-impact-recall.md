# 309 — Candidate-test recall on real changes

**What this measures.** Whether [308](../tasks/308_changed-code-to-candidate-test-files-report.md)'s
report finds the test files that actually exercise a change, on changes nobody here wrote. It
produces a promotion verdict and nothing else: no selective execution, no runner arguments, no
gate. Candidates only — the project's normal full suite remains authoritative.

Reporter: [`scripts/test_impact_recall.py`](../../scripts/test_impact_recall.py) (R6.3 — the
judgement ships as a committed, re-runnable reporter). Corpus:
[`scripts/test_impact_corpus.json`](../../scripts/test_impact_corpus.json).

## Pre-registration — committed before the first counted run

The bar below is **`BAR` in the reporter**, so the verdict is computed from it rather than chosen
after the numbers are known. It was committed in its own commit, ahead of any measurement; the
counted run is the commit after it. A negative measurement is a valid result and blocks promotion.

| Registered value | Setting |
|---|---|
| Qualifying corpus | upstream commits in repos already pinned by `scripts/cross_repo_samples.json` |
| Corpus floor | ≥ 12 scenarios, ≥ 3 repositories, ≥ 2 languages |
| Metric | micro-averaged recall = matched labelled test files / all labelled test files |
| Promote (eligible for an opt-in selective-run ticket) | recall ≥ 0.90 |
| Retain report-only | 0.60 ≤ recall < 0.90 |
| Insufficient evidence | recall < 0.60, or the corpus floor unmet |
| Precision | **not computed** — the labels are not exhaustive (below) |

### AC1 is NOT met, and this is the first thing to read

AC1 asks for a bar that is explicit, **human-ratified** *and* committed before the first counted
run. Only part of that holds, and the shortfall is not repairable inside this ticket.

| AC1 clause | Status |
|---|---|
| explicit | met — `BAR` in the reporter, and the table above |
| committed before the first counted run | met — `cd3a018` predates the run; `git show cd3a018:docs/benchmarks/309_test-impact-recall.md` still reads *"Filled by the counted run"* where the results now sit |
| human-ratified | **not met** — the values were agent-drafted under a standing "act autonomously" mandate, and the maintainer's explicit ratification came *after* the measurement existed |

The sequence, reconstructed from git and `.mango/` rather than asserted: `cd3a018` committed the
bar → the first counted run produced 0.824 → the ticket-blind challenger found that a blanket
mandate is delegation, not ratification → the maintainer was asked directly and ratified the values
exactly as committed (`.mango/ratification-309.txt` records the exchange verbatim). **That
ratification was not blind.** A human blessing a threshold they have already seen the result
against is not pre-registration, even when the threshold does not move — nobody can now say what
they would have chosen without the number in front of them.

It cannot be fixed after the fact either. Re-running the reporter now would put a ratification
before a counted run in the git order while everyone involved already knows the answer; that is a
manufactured timeline, and worse than recording the gap. Closing AC1 honestly needs a *fresh*
registration ratified blind, before a fresh count.

**What the gap can and cannot have done.** AC1 exists to stop a bar being set so that selective
execution looks justified. The measured verdict **blocks** promotion, so the failure mode this
criterion guards did not occur and a gamed bar would have pointed the other way. That bounds the
residual risk; it does not close the criterion. A reader who wants the promotion decision made on a
blind bar should treat this measurement as evidence and not as the registration.

## Ground truth — upstream co-change

For each scenario, the production paths are the non-test source files an **upstream** commit
modified, and the expected test files are the test-directory source files **the same commit**
modified. The labels are therefore the project maintainers' own judgement about which tests a
change needed, recorded before code-atlas existed and independent of any graph query.

Each commit's diff was read and kept only where the test edit demonstrably exercises the production
edit; `hand_verification` in the corpus records that reading per scenario, and `rejected` records
what was thrown out and why, so the reverse-chronological selection cannot be cherry-picked
silently. `scripts/test_impact_recall.py` re-derives both path lists from git on every run and
**refuses** a scenario whose committed labels no longer match its commit.

**The labels are not exhaustive.** A commit's authors touch the tests they judged necessary, never
every test that exercises the change. So an unlabelled candidate is not a false positive, and
precision is not computed (309 scope item 3) — recall is the only axis this corpus can carry.

## Miss causes

Every missed label lands in exactly one bucket, so the totals reconcile with the miss count by
construction (`aggregate()` raises otherwise). The cascade, in order:

| Cause | Reached when |
|---|---|
| `stale_or_incomplete_index` | the test file is absent from the index, or carries no nodes |
| `missing_test_role_classification` | the graph links it to a seed, but nothing classifies it as a test |
| `reporter_defect` | the graph links it to a seed, it *is* classified as a test, and the run was not truncated |
| `traversal_or_page_bound` | the run truncated, or the file reaches a seed only at depth ≥ 2 |
| `unmodelled_dynamic_relationship` | no static link, but the file has an unresolved call site naming a seed |
| `runner_only_discovery` | no static link and no outbound edges at all — only the runner can find it |
| `unclassified` | none of the above |

## Results

### 309 baseline (depth-1 walk) — historical

The first counted run (308's direct-inbound walk) recorded **recall_micro 0.8235** /
`report_only_retained`, with 14/17 matched and all 3 misses at inbound depth 2. That figure is the
baseline 312 compares against; it is not recomputed here.

### 312 re-run (depth-2 walk) — current

Reporter and corpus **unmodified**. Re-run with `.venv/bin/python scripts/test_impact_recall.py`
(~35 s). The walk under test is `code_atlas.candidate_tests` at `DEFAULT_MAX_DEPTH = 2`.

```json
{
  "labelled_test_files": 17,
  "languages": [
    "php",
    "python",
    "typescript"
  ],
  "matched": 16,
  "miss_causes": {
    "missing_test_role_classification": 0,
    "reporter_defect": 0,
    "runner_only_discovery": 0,
    "stale_or_incomplete_index": 0,
    "traversal_or_page_bound": 1,
    "unclassified": 0,
    "unmodelled_dynamic_relationship": 0
  },
  "missed": 1,
  "precision": null,
  "precision_not_computed_because": "the labels are a commit's own test edits, never the exhaustive set of tests that exercise it, so an unlabelled candidate is not a false positive (309 scope item 3)",
  "recall_macro": 0.9333,
  "recall_micro": 0.9412,
  "repos": [
    "brick_math",
    "flask",
    "ky",
    "requests"
  ],
  "scenarios": 15,
  "statement": "Candidates only — the project's normal full suite remains authoritative. Unlisted tests are not safe to skip.",
  "verdict": "eligible_for_opt_in_selective_run_ticket",
  "verdict_reason": "recall 0.941 >= 0.9"
}
```

| Scenario | Language | Matched / labelled | Miss cause |
|---|---|---|---|
| `flask@89992954ec71` | python | 0 / 1 | `traversal_or_page_bound` |
| `flask@7203feabf723` | python | 1 / 1 | — |
| `flask@de8429ffda8c` | python | 1 / 1 | — |
| `flask@06ea505ce2b2` | python | 1 / 1 | — |
| `requests@6f66281a1d63` | python | 1 / 1 | — |
| `requests@6f205ff422bc` | python | 1 / 1 | — |
| `requests@6404f345e562` | python | 1 / 1 | — |
| `requests@a4f9a5999bdb` | python | 1 / 1 | — |
| `brick_math@7d1678e93ab2` | php | 1 / 1 | — |
| `brick_math@4d606566ae5e` | php | 1 / 1 | — |
| `brick_math@a7a2a73742be` | php | 2 / 2 | — |
| `brick_math@391597d65cfa` | php | 1 / 1 | — |
| `ky@0bda554d448c` | typescript | 1 / 1 | — |
| `ky@294fe63be57d` | typescript | 2 / 2 | — |
| `ky@be60db582496` | typescript | 1 / 1 | — |

**Candidate-count growth (unique test paths, same indexes, `max_depth` 1 → 2).**

| Scenario | d1 candidates | d2 candidates | Δ | Matched / labelled (d2) |
|---|---:|---:|---:|---|
| `flask@89992954ec71` | 3 | 4 | +1 | 0 / 1 |
| `flask@7203feabf723` | 22 | 22 | 0 | 1 / 1 |
| `flask@de8429ffda8c` | 4 | 19 | +15 | 1 / 1 |
| `flask@06ea505ce2b2` | 6 | 17 | +11 | 1 / 1 |
| `requests@6f66281a1d63` | 2 | 5 | +3 | 1 / 1 |
| `requests@6f205ff422bc` | 2 | 5 | +3 | 1 / 1 |
| `requests@6404f345e562` | 2 | 5 | +3 | 1 / 1 |
| `requests@a4f9a5999bdb` | 1 | 4 | +3 | 1 / 1 |
| `brick_math@7d1678e93ab2` | 4 | 5 | +1 | 1 / 1 |
| `brick_math@4d606566ae5e` | 3 | 5 | +2 | 1 / 1 |
| `brick_math@a7a2a73742be` | 4 | 5 | +1 | 2 / 2 |
| `brick_math@391597d65cfa` | 4 | 4 | 0 | 1 / 1 |
| `ky@0bda554d448c` | 2 | 15 | +13 | 1 / 1 |
| `ky@294fe63be57d` | 6 | 15 | +9 | 2 / 2 |
| `ky@be60db582496` | 6 | 15 | +9 | 1 / 1 |
| **Total** | **71** | **145** | **+74** | **16 / 17** |

The two recovered labels (`brick_math@a7a2a73742be`, `ky@be60db582496`) each added only +1
path — cheap. Several already-green scenarios roughly doubled their candidate set with no recall
gain (`flask@de8429ffda8c` +15, `ky@0bda554d448c` +13, `flask@06ea505ce2b2` +11) — that is the cost
of the 0.824 → 0.941 lift, reported as the trade rather than as an unqualified improvement
(312 AC5).

**What the run itself declares unmeasured — read this before the number.** Every one of the 15
scenarios reports `depth_bound`: the walk stopped at hop 2 with production symbols still carrying
unexplored callers, so 0.9412 is a floor for this walk and says nothing about hop 3. Three scenarios
additionally report `truncated_page` — `flask@7203feabf723`, `brick_math@7d1678e93ab2` and
`brick_math@a7a2a73742be` — where the edge budget (`max(impact_max_nodes, page_limit)`, shared by the
whole BFS rather than per seed) ran out and the walk stopped early; 309's depth-1 run truncated on
none. All three still matched every label they carry, but their candidate sets are lower bounds. The
per-scenario `unmeasured` lists in `artifacts/309-test-impact-recall.json` are the record.

**Provenance.** code-atlas `8a0c4d9f1e2c` · contract v10 ·
Python 3.13.14 · Linux-7.0.0-31-generic-x86_64-with-glibc2.39 · host `dev-host`. Each scenario's
index revision is its own `head` in `artifacts/309-test-impact-recall.json` (that path is
`.gitignore`d — the figures are reproduced by re-running, never read from the repo). Two consecutive
runs produced a byte-identical aggregate (R4.2).

## Verdict — `eligible_for_opt_in_selective_run_ticket`

Recall **0.9412** clears the pre-registered 0.90 promotion line (and the 0.60 retain line). Compared
with the 309 baseline **0.824**, the delta is attributable to widening the walk to depth 2 — the bar
was not moved (312 Constraints / AC6). The verdict follows the number: an opt-in selective-run
ticket is now *eligible to be proposed*, not implemented here.

**What recovered, what did not.** `ky@be60db582496` and `brick_math@a7a2a73742be` — the two façade /
package-entry misses 309 named — now match. `flask@89992954ec71` remains a single
`traversal_or_page_bound` miss reported at diagnostic inbound depth 2, and that pairing is not a
contradiction: the diagnostic (`scripts/test_impact_recall.py:145`) walks *files* — reaching a file
promotes every symbol in it to the next frontier — while the candidate walk follows *symbols*, so a
file-level hop 2 can be a symbol-level hop 3 or further. The change set truncated on nothing and
produced 4 candidates, none of them `tests/test_basic.py`; the residual is depth, measured on a
finer graph than the diagnostic uses.

**What this licenses.** Still nothing in the runner. The report stays `mode: report_only`, the full
suite stays authoritative, and no flag, path or sentence proposes skipping an unlisted test
(`tests/test_impact_recall.py` fails if one does). Selective execution remains a separately proposed
ticket.

## Pre-registration for the NEXT count — ratified blind, 2026-09-20

309's own AC1 could not be closed (above). The decision it was guarding has not happened yet: the
promotion call belongs to the successor measurement, after 308's walk is widened past depth 1, and
**that number does not exist**. So the bar for it was put to the maintainer *before* any of that work
was written, and ratified:

| Registered for the next count | Setting |
|---|---|
| Promote | recall ≥ 0.90 |
| Retain report-only | 0.60 ≤ recall < 0.90 |
| Corpus floor | ≥ 12 scenarios, ≥ 3 repositories, ≥ 2 languages |

Unchanged from 309's bar on purpose: holding the thresholds fixed makes the next figure directly
comparable to **0.824**, so the delta is attributable to the widened walk and not to a moved yardstick.
This registration *is* blind — nobody has seen the number it will judge — which is precisely what
309's own registration was not.

**What a reader should distrust first.** AC1 is not met — the bar was ratified after the
measurement, not before it (see *AC1 is NOT met* above; that section, not this line, is the full
account). The labels are 17 test files over 15
commits — enough to clear the registered floor, not enough to place a tight interval around 0.82.
And the corpus is four small, well-factored open-source libraries; a large application with dynamic
dispatch and fixture indirection would very likely score worse, not better.
