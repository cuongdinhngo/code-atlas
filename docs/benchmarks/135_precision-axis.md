# 135 — precision, measured for the first time

**Status:** run, both committed tiers, 2026-08-23 (Linux, PHP 8.3.6).
**Ticket:** [`../tasks/135_harness-scores-recall-but-never-precision.md`](../tasks/135_harness-scores-recall-but-never-precision.md).
**Verdict:** the gate could not see a wrong answer. On the pinned `symfony/demo` the same answer that
scores **recall 1.0** scores **precision 0.5** — half of what it claims is not true. Reproduce with:

```bash
export CA_PHP_CMD="php $(pwd)/adapters/php/index.php --server"
python3 scripts/tokens_to_answer.py --min-ratio 0.63 --min-recall 1.0 --min-precision 1.0
python3 scripts/tokens_to_answer.py --samples --min-recall 1.0 --min-precision 1.0
```

## The hole, before and after — same question, same repo, same index

| harness | recall | `confidently_wrong` | precision | exit |
|---|---|---|---|---|
| pre-change (`ce38042`, main) | 1.0 | False | *not measured* | **0 — PASS** |
| this change | 1.0 | False | **0.5** | **1 — FAIL**, naming all four members |

```
GATE FAILED: precision below floor 1.0: onb_sample_web_surface precision 0.5 — unexpected:
tests/Controller/Admin/BlogControllerTest.php, tests/Controller/BlogControllerTest.php,
tests/Controller/DefaultControllerTest.php, tests/Controller/UserControllerTest.php
```

That is defect [130](../tasks/130_web-entry-bucket-counts-test-controllers.md) reaching a gate for the
first time. It was found by hand while running 121; nothing mechanical could see it until now.

## Why the denominator is declared, not derived

The obvious denominator — every identity string in the payload — is measurably wrong. Three
independent reasons, each observed on a **correct** answer:

| shape | measured | why an identity bag breaks |
|---|---|---|
| `find_callers` on `\App\Repo::put` | bag = 3 strings for a 1-member truth → **0.33** | the payload echoes the **query** in `qname` |
| any `results` row | `\App\User::save` **and** `User.php` | one member counted twice: cardinality becomes field-count |
| `find_orphans` | `unproven` sits beside `results` | R5.2's honest tiers would score as false claims |

So each question declares **`precision_scope`** — the path to the population it claims — or states in
**`precision_note`** why it has none. Scoring counts *items*, not strings; a truncated page is never
scored as a population; a row with `expected_set` and neither key is **refused**, so the axis cannot
default to green the way the recall gate did on the onboarding class (121).

## First run — every eligible question, every unexpected member

**Fixture tier:** 24 questions, 15 precision-eligible, **precision 1.0**, 0 unexpected. Eligible and
all at 1.0: `blast_radius_of_repo_put`, `call_sites_of_repo_put`, `callers_of_repo_put`,
`implementations_of_base`, `imported_by_registry`, `imports_of_app`, `onb_declared_entry_points`,
`onb_depends_on_shared_module`, `onb_hub_blast_radius`, `onb_layers_and_dependencies`,
`onb_read_first`, `onb_request_entry`, `reachable_from_entry`, `references_to_base`,
`symptom_persist_via_put`. **No false alarm on any correct answer** — that is the other half of the
proof, and the reason the floor could be set.

**Sample tier:** 8 questions, 2 eligible, **precision 0.75**, 4 unexpected.

| question | precision | claimed | unexpected |
|---|---|---|---|
| `onb_sample_layers` | 1.0 | 7 | — |
| `onb_sample_web_surface` | **0.5** | 8 | the four `tests/Controller/*Test.php` above |

## The 11 exclusions, and the one pattern in them

Every excluded row carries its reason in the report. They fall into three shapes, and only the third
is a finding about the harness rather than about the tool:

- **A ranked page is not a population** — `search_user`, `search_repo`, `onb_feature_files`,
  `onb_sample_feature_files`. A lower-ranked hit the question did not enumerate is a ranking
  decision. (Measured: `search_repo` would score 0.25 for a correct answer.)
- **A body is not a population** — `read_repo_put`, `read_user_save`: `read_symbol` has no `results`.
- **The question narrows the tool's population in its prose, not in its call** —
  `orphans_dead_unused` ("orphans *under namespace Dead*"), `onb_dead_file` ("is *this file* dead"),
  `onb_naming_debt`, `onb_committable_map`. `find_orphans` returns every orphan; the extras are
  correct answers to a wider question. Measured 0.154 and 0.143 for answers that are right.

That third shape is worth a follow-up: a question whose recipe cannot express its own narrowing can
never be precision-gated, and four of 26 are in that state. Making the narrowing part of the call
(rather than the prose) would move them into the axis.

## What is NOT claimed here

- **130 is not fixed.** This measures it; the fix is its own ticket, and this question is the proof
  that a gate will now catch the regression if it comes back.
- **Precision is not a cross-tier average worth quoting.** 15 eligible questions on toy fixtures and 2
  on one pinned repo; the number that means something is the per-question one.
- **The sample tier is still not in CI** (needs clone + PHP), so `onb_sample_web_surface` fails only
  when a maintainer runs `--samples`. The fixture floor is what CI enforces.
