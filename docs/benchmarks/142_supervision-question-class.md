# 142 — the supervision question-class, measured

**Status:** run, fixture tier, 2026-08-25. **Ticket:**
task 142 (phase-1 archive).
**Verdict:** the class is **cheap and correct where a tool answers it, and one member of the class is
answered by no tool at all** — the minimum acyclic cut-edge set (141, deferred). Both are recorded
below; the second is labelled, not scored as a miss.

**Provenance (AC4, 125's rule — do not quote a build that did not answer):**
- **host:** Docker Linux image `python:3.12-slim-bookworm`, Python 3.12.14, PHP 8.2.33 (`scripts/docker-test.sh`).
- **server build:** code-atlas branch `chore/142-supervision-question-class`, base `567a8da`. No `code_atlas/`
  change — this ticket adds fixtures, questions, a harness binding and this benchmark only.
- **index revision:** built fresh from the **committed** fixtures during the run
  (`tests/fixtures/php/{architecture_rules,architecture_drift,impact_modules,onboarding}`), so the
  numbers reproduce from the tree, not from an operator's local index.

## What was measured

Six questions, tagged `tier: supervision` in
[`../../scripts/tokens_to_answer_questions.json`](../../scripts/tokens_to_answer_questions.json),
covering the four supervision question types 138-141 name, plus the one no tool answers. Every
ground-truth answer was read out of the fixture by hand **before** the tools ran (121's discipline);
the tools then agreed.

The four supervision tools are **already shipped** — this ticket builds **no** tool. `impact_modules`
and `subtree_dependencies` were not bound in the tokens-to-answer harness; binding them (additive) is
the only harness change, and it is proven below not to move any existing question's numbers.

## Fixture tier — per question

`—` under recall/precision means the shape has no scoreable population, with the reason in the
question file. **No supervision question carries a grep baseline:** a rule-closure, an architectural
diff, a module rollup and a boundary cut are none of them things a pattern returns, so a baseline
would be an invented number flattering the comparison (AC2/AC3, same rule 121 wrote for its nine).

| question | type | tool | atlas | recall | precision |
|---|---|---|---|---|---|
| `sup_rule_holds_violation` | does this rule still hold | `check_architecture_rules` | 239 | — | — |
| `sup_rule_holds_clean` | does this rule still hold | `check_architecture_rules` | 178 | — | — |
| `sup_arch_drift` | what changed architecturally | `diff_architecture` | 438 | 1.0 | — |
| `sup_modules_reached` | which modules does this reach | `impact_modules` | 335 | 1.0 | 1.0 |
| `sup_can_split_partial` | can this be split (partial) | `subtree_dependencies` | 261 | 1.0 | 1.0 |
| `sup_can_split_unanswerable` | can this be split (cut set) | *none* | 474 | *unanswerable* | *unanswerable* |

**6/6 correct, recall 1.0 on every scored row, precision 1.0 on every scored row, `confidently_wrong`
0, `unexpected` 0.** The class is measured on **both axes**: `impact_modules` and
`subtree_dependencies` produce a recall *and* a precision number; `diff_architecture` produces a
recall number (its answer is per-section deltas, not one claimed population); the two
`check_architecture_rules` rows are correctness-and-cost only, because a confirmed violation keys on
`rule_id`/`source_file`/`forbidden_file`, not on the identity vocabulary the scorer reads.

### The hand-verified answers

- **`sup_rule_holds_violation`** — `domain-must-not-reach-http` is **violated**: `domain/Model.php`
  reaches `http/Front.php` transitively through `service/Bridge.php` (a RESOLVED closure a grep over
  the domain file cannot see — 138's evidence gate). `sup_rule_holds_clean` — the reverse rule
  `http-must-not-reach-domain` is **checked and holds** (`total_count` 0, `reason` ok, status
  `checked`), which is a different finding from *not configured* or *no such rule*.
- **`sup_arch_drift`** — between the two committed snapshots: one module added
  (`reports/InvoiceReport.php`), one cross-layer pair added (`Integration / Reporting → Shared
  Library`), one hub moved (`lib/Clock.php`, fan-in 3→4).
- **`sup_modules_reached`** — changing `\Fx\Billing\Invoice::total` reaches **5 modules**: billing
  (2 symbols), catalog (2, one only HEURISTIC), loyalty (1), shipping (1), and one file no module
  owns (`unassigned`, 1). 7 symbols total.
- **`sup_can_split_partial`** — `lib/` has **inbound 11, outbound 0** (all RESOLVED): five files
  depend on it (`legacy/`, `repositories/`, `reports/`, `services/`, `jobs/`), it depends on nothing.
  One-directional, so no cycle blocks the split — but heavily depended-upon. Re-measured 2026-09-08:
  task 232 made a declared class type a `REFERENCES` edge, which is what surfaced `jobs/ReminderJob.php`
  — it takes a `Clock` parameter and nothing else — so the ground truth here moved up, not the tool's
  precision down.

## The member no tool answers — recorded, not scored

`sup_can_split_unanswerable` asks for the **minimum acyclic cut-edge set** that would make `lib/`
extractable without breaking a cycle. **No tool returns it.** `subtree_dependencies` gives the cut
*cost* and direction, and `guided_tour`'s Tarjan finds the SCCs behind the reading order, but neither
returns the edge set whose removal makes a cyclic boundary acyclic — that is
[141](../tasks/141_extractability-cut-edges-and-the-cycles-that-block-it.md), deferred behind its
evidence gate. The harness marks the row `unanswerable: true` with a written reason and **no
`expected_set`**, so it is labelled, never scored as a recall zero (AC3/R4). This row **is** evidence
for 141's gate item 3: the hand-composition of the two existing tools stops short of the answer.

## AC5 — the existing classes' numbers did not move

The class carries **no ratio-eligible question**, so it adds zero rows to the cost ratio. Measured on
this build, with and without the two new `_TOOL_NAMES` entries the binding adds:

| harness | fixture ratio | ratio questions | `callers_of_repo_put` | `references_to_base` | `onb_layers_and_dependencies` |
|---|---|---|---|---|---|
| with the binding | 0.807 | 13 | 156 | 137 | 1359 |
| without it | 0.807 | 13 | 156 | 137 | 1359 |

Byte-identical: `get_index_status(minimal)` on a built index does not depend on the servable-tool
list, so binding `impact_modules`/`subtree_dependencies` moves nothing an existing question counts.
The fixture floor `--min-ratio 0.27` the proving path gates on is unchanged. (The 0.807 here is the
current baseline; [121](121_onboarding-question-class.md)'s 0.789 predates 137/129 and is historical.)

## Reproduce

```bash
export CA_PHP_CMD="php $(pwd)/adapters/php/index.php --server"
python scripts/tokens_to_answer.py --min-ratio 0.27 --min-recall 1.0 --min-precision 1.0
pytest -q tests/test_supervision_question_class.py
```

Deterministic: fixed recipes, committed fixtures and snapshots, no wall-clock in the report. On the
maintainer's Windows host run it in Docker (`scripts/docker-test.sh pytest -q
tests/test_supervision_question_class.py`) — the PHP adapter and POSIX `fcntl` are why bare `pytest`
is red there.

## What this measurement does not decide

- **Whether the class is worth serving.** That is 141's gate reading these numbers, not this ticket
  (Out of scope). What is shown: five of six members are cheap and correct; the sixth has no tool.
- **A capability-layout rollup at scale.** `sup_modules_reached` runs on the 140 fixture (four peer
  capability dirs); both public pins roll up to a single `unassigned` bucket (140's own finding), so
  no committed pin shows a rich module split. The saving at radius scale is 140's benchmark, not this.
- **Precision on the rule and drift shapes.** `check_architecture_rules` and `diff_architecture` have
  no single claimed population to over-include into; recall and correctness cover them. Making a rule
  violation's narrowing part of its call (so it could be precision-gated) is a harness follow-up.
