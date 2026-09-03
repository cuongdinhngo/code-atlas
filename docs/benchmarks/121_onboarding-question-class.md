# 121 — the onboarding question-class, measured

**Status:** run, both committed tiers, 2026-08-23. **Ticket:**
[`../tasks/121_onboarding-question-class-never-measured.md`](../tasks/121_onboarding-question-class-never-measured.md).
**Verdict:** the class is **cheaper than hand-mapping where the question is a lookup, and wrong where
the question is a reading order.** Both halves are below, with the numbers that produced them.

`ROADMAP.md` §5 gated the whole onboarding phase on this measurement and it never ran; M10-M12
shipped on defect-fixing evidence instead. This file is the gate finally running, in both directions.

## What was measured

Thirteen questions, tagged `tier: onboarding` in
[`../../scripts/tokens_to_answer_questions.json`](../../scripts/tokens_to_answer_questions.json) — eleven
against the committed fixture `tests/fixtures/php/onboarding` (a ten-module tree with path-derived
responsibility layers, a hub, a declared entry-point glob, an unreachable module and a module whose
path names no responsibility), two against the pinned `symfony/demo` at
`03fe25671b720b15103a2ff26934e94c87bd4d82`. Every ground-truth answer was read out of the source by
hand **before** the tools ran; where the tools then disagreed, the disagreement is recorded below
rather than absorbed into the expectation.

Three of the twelve carry a `grep` baseline. The other nine each carry a `ratio_note` saying why no
fair baseline exists — a layering, a reading order, a blast radius and a whole-graph negative are not
things a pattern returns, and inventing a baseline for them would only flatter the comparison (AC3).

## Fixture tier — per question

> **These atlas figures are dated 2026-08-23 and several have since moved** — `onb_committable_map`
> reads **173** today against the 290 below, because 205 removed the page tree its payload listed.
> Re-measuring the whole table is its own job and is **not** done here; a row added by a later
> ticket carries that ticket's own fresh number. Read a figure below as *what this class cost on
> 2026-08-23*, and take a live number from `artifacts/tokens-to-answer-report.json`. This note
> exists because a reviewer took 290 from this table as the current value and was wrong (207).

`ratio > 1` means code-atlas is cheaper. `—` means out of the ratio, with its reason in the question file.

| question | atlas | grep | ratio | recall |
|---|---|---|---|---|
| `onb_layers_and_dependencies` — layers and their crossings | 1,355 | — | — | 1.0 |
| `onb_read_first` — entry points and reading order | 328 | — | — | 1.0 |
| `onb_depends_on_shared_module` — who includes/calls the hub | 422 | 665 | **1.58** | 1.0 |
| `onb_hub_blast_radius` — what breaks if the hub changes | 326 | — | — | 1.0 |
| `onb_dead_file` — is this file dead | 1,124 | — | — | 1.0 |
| `onb_feature_files` — which files implement the feature | 638 | 852 | **1.34** | 1.0 |
| `onb_request_entry` — what pulls this page in | 157 | 159 | **1.01** | 1.0 |
| `onb_declared_entry_points` — which glob claimed the count | 1,355 | — | — | 1.0 |
| `onb_committable_map` — write the map to git | 290 | — | — | 1.0 |
| `onb_working_scope` — whether the generated map declares a scoped working tree | 173 | — | — | 1.0 |
| `onb_first_day_commands` — how do I run this project's tests (207) | 1,662 | — | — | n/a |
| `onb_audience_newcomer` — the day-one command **and** a reading order, from the newcomer tree (210) | 1,210 | — | — | n/a |
| `onb_audience_maintainer` — cross-layer coupling and duplicated subtrees, from the maintainer tree (210) | 1,538 | — | — | n/a |
| `onb_naming_debt` — which paths name no responsibility | 1,742 | — | — | 1.0 |

13/13 correct, recall 1.0, `confidently_wrong` 0. Whole fixture tier: **0.789** over 13 ratio-eligible
questions (was 0.29 before this class existed — the onboarding questions are the first fixture-tier
questions where the index wins, because they are the first that read more than one file).

## What an audience costs its own reader (210)

Each audience is scored on **its own** question class, out of the tree written for it. Neither
regresses — both answer correctly — and the newcomer pays less for the answer they came for:

| tree | question class | atlas | correct |
|---|---|---|---|
| `full` (today's artifact) | first-day command | 1,662 | ✅ |
| `newcomer` | first-day command **+ reading order** | **1,210** | ✅ |
| `maintainer` | cross-layer coupling + mirrors | 1,538 | ✅ |

The newcomer tree answers a **strictly larger** question — the command *and* the reading order —
for **27 % fewer tokens** than the single artifact spends on the command alone, because the
sections that reader never uses are not in the document. That is the ticket's claim, measured.

## Sample tier — a real repo

| question | atlas | grep | ratio | recall |
|---|---|---|---|---|
| `onb_sample_layers` — 7 layers, 51 modules, 11 crossings | 1,567 | — | — | 1.0 |
| `onb_sample_feature_files` — the blog administration screens | 1,356 | 6,312 | **4.66** | 1.0 |

Sample-tier aggregate moves **98.2 → 69.06**. That is not a regression: the aggregate now spans two
question classes, and an onboarding lookup that reads five files cannot show the ~100× a `find_references`
over a 40-file tree shows. The scheduled floor moves 78 → 55 (`0.8 × observed`) for the same reason.

## Where the map loses — established by hand, on `symfony/demo`

**1. ~~The reading order is not a reading order.~~ Closed by [131](../tasks/131_tour-ranks-configuration-ahead-of-the-front-controller.md), 2026-08-24.**
Re-measured on `symfony/demo` @ `03fe25671b720b15103a2ff26934e94c87bd4d82`, first five stops:

```
src/Controller/BlogController.php
src/Controller/Admin/BlogController.php
src/Controller/UserController.php
public/index.php
src/Command/AddUserCommand.php
```

The front controller is in the first five (AC1). Lint and bootstrap config no longer open the tour
(zero-outbound roots are not preferred seeds; Config sinks in reading-seed rank). The hand answer's
kernel / entity / repository sequence is still not reproduced — the tour remains a dependency walk,
not a curated syllabus.

**2. ~~Half the "web surface" is tests.~~ Closed by [130](../tasks/130_web-entry-bucket-counts-test-controllers.md), 2026-08-24.**
Reachability now checks every directory segment for a test role before the request-handling
vocabulary, so `tests/Controller/*Test.php` lands in `test`, not `web_entry`.

**3. `include_graph` cannot answer "what does this file include?" for a namespaced file.** The
INCLUDES edge is anchored on the file's *namespace* node, so `direction: imports` returns
`results: []` **with `unresolved_includes: 0`** — a silent zero — for every namespaced file, which in a
PSR-4 repo is all of them. `imported_by` works, and reports the includer's namespace qname in a field
named `path`. The pre-existing fixture has no namespace, which is why the suite never saw it. Filed as
[`129`](../tasks/129_include_graph_imports-is-a-silent-zero-for-a-namespaced-file.md). The class routes
around it: `onb_request_entry` and `onb_depends_on_shared_module` both ask `imported_by`.

## What this measurement cannot see

- **Precision.** The harness scores recall and cost, not over-inclusion. Finding #2 above passes every
  mechanical check — the four real controllers are all present — and is still a wrong answer. A
  precision metric is the obvious next instrument and does not exist yet.
- **Anything the graph does not hold, and the instrument says so.** Every other question above is
  a graph question, because that is what the class was narrowed to. 207 revisits the narrowing:
  `onb_first_day_commands` is the first question here whose answer is a **declared** fact quoted
  from a manifest, not a derived one. Two consequences the harness makes unavoidable. It is out of
  the ratio — a grep beats the index at reading `composer.json`, and the question measures whether
  the artifact answers a first-day question **at all**. And it cannot be **recall**-scored: the
  answer lives in the committed `overview.md`, and `_mcp_responses` excludes native file reads on
  purpose, because recall measures what the *index* answered. So it scores correctness and cost
  (1,557 tokens — what opening the document actually costs) and the `expected_set_note` states why,
  the same way a ratio exclusion states its reason. **This is 121-C1 again from the other side:** a
  measurement deferred may be one whose instrument cannot address its subject, and here the
  instrument's own anti-cheat is what draws the line the ticket asked 121 to draw.
- **Whether a human would act on the answer.** `onb_layers_and_dependencies` recalls 9 of 9 layers on
  the fixture; on `symfony/demo` the largest layer is `Uncategorised` (18 of 51 modules), because the
  responsibility vocabulary has no word for `Command`, `EventSubscriber`, `Security` or `Twig`. A
  complete, correct, low-information answer scores 1.0 here.
- **The mirror shape.** Two subtrees holding near-copies of each other need 25 shared relative paths
  before the pair is reported, so no committed fixture can carry one and neither pinned sample has one.
  That question lives in the **local-tier template** in
  [the runbook](../runbooks/tokens-to-answer.md#onboarding-class-on-a-repo-of-your-own-local-tier), for an
  operator to run against a tree that has one.

## Reproduce

```bash
export CA_PHP_CMD="php $(pwd)/adapters/php/index.php --server"
python scripts/tokens_to_answer.py --min-ratio 0.63 --min-recall 1.0        # fixture tier
python scripts/tokens_to_answer.py --samples --min-ratio 55                 # sample tier (clones)
```

Both are deterministic: fixed recipes, a pinned SHA, no wall-clock in the report, and the counted
payload normalises absolute paths so the ratio does not move with checkout depth (verified here — the
same run at `/tmp/…/scratchpad` and 60 characters deeper both give 2,733 / 2,155 / 0.789).
