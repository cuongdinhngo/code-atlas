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

Counted run on the commit after the pre-registration commit. Re-run with
`.venv/bin/python scripts/test_impact_recall.py`; the full run costs about 40 s and rebuilds an
index per scenario, so it is re-runnable rather than a session transcript (R6.3).

```json
{
  "labelled_test_files": 17,
  "languages": [
    "php",
    "python",
    "typescript"
  ],
  "matched": 14,
  "miss_causes": {
    "missing_test_role_classification": 0,
    "reporter_defect": 0,
    "runner_only_discovery": 0,
    "stale_or_incomplete_index": 0,
    "traversal_or_page_bound": 3,
    "unclassified": 0,
    "unmodelled_dynamic_relationship": 0
  },
  "missed": 3,
  "precision": null,
  "precision_not_computed_because": "the labels are a commit's own test edits, never the exhaustive set of tests that exercise it, so an unlabelled candidate is not a false positive (309 scope item 3)",
  "recall_macro": 0.8333,
  "recall_micro": 0.8235,
  "repos": [
    "brick_math",
    "flask",
    "ky",
    "requests"
  ],
  "scenarios": 15,
  "statement": "Candidates only — the project's normal full suite remains authoritative. Unlisted tests are not safe to skip.",
  "verdict": "report_only_retained",
  "verdict_reason": "recall 0.824 >= 0.6"
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
| `brick_math@a7a2a73742be` | php | 1 / 2 | `traversal_or_page_bound` |
| `brick_math@391597d65cfa` | php | 1 / 1 | — |
| `ky@0bda554d448c` | typescript | 1 / 1 | — |
| `ky@294fe63be57d` | typescript | 2 / 2 | — |
| `ky@be60db582496` | typescript | 0 / 1 | `traversal_or_page_bound` |

**Provenance.** code-atlas `cd3a018b769e` · contract v10 ·
Python 3.13.14 · Linux-7.0.0-31-generic-x86_64-with-glibc2.39 · host `dev-host`. Each scenario's index revision
is its own `head`, recorded per row in `artifacts/309-test-impact-recall.json`; the index is rebuilt
from scratch at that revision, never reused across scenarios. Two consecutive runs produced a
byte-identical aggregate (R4.2).

## Verdict — `report_only_retained`

Recall **0.8235** clears the 0.60 retain line and misses the 0.90 promotion line, so
the pre-registered bar **blocks** an opt-in selective-run ticket. That is the bar doing its job: a
measurement taken to justify skipping work came back saying the evidence is not there yet, and the
verdict follows the number rather than the intent (309 AC5).

**Every miss has the same cause, and it is not noise.** All 3 missed labels sit at
**inbound depth 2**: the test file references the package entry point or a sibling façade, which in
turn reaches the changed symbol. 308 walks *direct* inbound edges only, so a test one hop further
out is invisible to it — in `ky@be60db582496` that is `test/base-url.ts` importing `source/index.ts`
rather than `source/core/Ky.ts`, and in `brick_math@a7a2a73742be` it is `BigDecimalTest.php`
reaching `BigInteger::nthRoot()` through `BigDecimal`. No scenario truncated, none was stale, and
nothing was misclassified as production: the one bound that matters here is traversal depth.

**What this licenses.** Nothing in the runner. The report stays `mode: report_only`, the full suite
stays authoritative, and no flag, path or sentence added by this ticket proposes otherwise
(`tests/test_impact_recall.py` fails if one does). The named follow-up this measurement earns is a
*separate* ticket to widen the walk beyond depth 1 and re-run this reporter — improving the metric
is out of 309's scope by its own *Out of scope* section, and re-running a bar to make it pass is
what pre-registration exists to prevent.

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
