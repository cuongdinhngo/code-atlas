# Tokens-to-answer benchmark (task 034 / §19 agent-first pivot)

Make the product thesis falsifiable: measure the tokens an agent spends reaching the **correct**
answer via code-atlas tools vs a grep+`Read` baseline. The metric is
`ratio = grep tokens / code-atlas tokens` over the questions code-atlas answers correctly —
`> 1` means code-atlas is cheaper. This replaces "no crash / sane counts" as the accuracy story
([cross-repo validation](cross-repo-validation.md) stays the smoke test).

Deterministic by design: each question is a **fixed recipe**, not a live model
([`scripts/tokens_to_answer.py`](../../scripts/tokens_to_answer.py)), so CI can gate on it (R4).

## Files

- Harness: [`scripts/tokens_to_answer.py`](../../scripts/tokens_to_answer.py)
- Ground truth: [`scripts/tokens_to_answer_questions.json`](../../scripts/tokens_to_answer_questions.json)
- Gate + proving path: [`tests/test_tokens_to_answer.py`](../../tests/test_tokens_to_answer.py)

## Run locally (needs the PHP adapter built)

```bash
export CA_PHP_CMD="php $(pwd)/adapters/php/index.php --server"
python3 scripts/tokens_to_answer.py                 # report only
python3 scripts/tokens_to_answer.py --min-ratio 1.0 # also gate (non-zero exit if it regresses)
```

The report lands under `artifacts/` (gitignored). The pure-Python gate tests
(`estimate_tokens`, `aggregate`, `assert_benchmark`, grep path) run in CI with no PHP; the
`@needs_php` test builds the fixtures and runs every committed question end to end.

## Automatic gate (every PR)

The `test` job in [`ci.yml`](../../.github/workflows/ci.yml) runs
`python scripts/tokens_to_answer.py --min-ratio 0.24 --markdown … --notice` on every PR — it fails on
a wrong answer or if the ratio regresses. It runs on **3.13 only** (a token count does not vary by
interpreter) and reports in four places, so nobody has to open a log:

| Where | What |
|---|---|
| **PR conversation** | One sticky comment, found by `COMMENT_MARKER` and **edited** on each push |
| **PR → Checks tab** | A `::notice::` annotation with the headline numbers |
| **Run → job summary** | The same markdown table |
| **Run → Artifacts** | `tokens-to-answer-report.json` (per-question rows) |

All four are emitted **whether the gate passes or fails** — a breach is exactly when the numbers need
to be visible, so `--markdown` / `--notice` are written before the exit code is returned
(`test_markdown_and_notice_are_emitted_even_when_the_gate_fails` pins this). The comment step needs
`permissions: pull-requests: write` on the job and is `continue-on-error` because a fork PR gets a
read-only token.

**The floor is a behavior-lock, not the value claim.** The committed fixtures are 4-file toy repos
where `get_index_status` overhead makes code-atlas *cost more* than reading one tiny file (observed
ratio ≈ **0.288**: 1666 vs 479 tokens over 10 questions, all answered correctly). The token win
(ratio ≫ 1) appears only on realistic repos, where grep matches many files an agent must read whole
— that is the **sample tier**, measured on schedule, not per PR.

## Surface A/B (task 037)

`scripts/relation_surface_ab.py` answers a question this ratio cannot: **three relation tools or one
`find_relations`?** The gate above counts only `args + response`, so it is blind to the tool *schema*
an agent carries all session — which is the only thing consolidation trades. The script measures both
terms (schema tokens once + per-call tokens, surface B dispatching to the real tools) and prints a
sweep, because a single data point hides the crossover:

```bash
export CA_PHP_CMD="php $(pwd)/adapters/php/index.php --server"
python scripts/relation_surface_ab.py --json artifacts/relation-surface-ab.json
```

Measured: three tools cost **464** schema tokens, one costs **223**; one tool then pays **6.75 tokens
per call** for its extra `relation` argument. Break-even ≈ **36 relation calls per session** — a merged
tool is cheaper below that, three tools above, and the whole spread is only −234…+434 tokens across
1–100 calls. Read the break-even from `call_delta_per_call`, **never** from the aggregate `call_delta`
(that mistake inflated it 4× in review). Verdict and full tables:
[`docs/tasks/037_compound-nav-responses.md`](../tasks/037_compound-nav-responses.md). Re-run it
whenever a relation tool's docstring changes materially — the schema term is prose-sensitive (editing
one docstring during 037 moved the break-even from 11.4 to 8.9).

Recalibrate the floor to `0.8 × observed` whenever the fixtures or recipes change. Response-shape
work also moves it: the ratio has drifted **0.302 → 0.293 → 0.286** (1409 → 1452 → 1484 atlas
tokens) as tasks 033 and 035 added `reason` / `total_count` to every payload, so the `0.24` floor now
carries 16% headroom rather than the intended 20%. Re-read the floor before assuming a failure is a
regression in retrieval rather than a wider response.

## Adding a question

Each entry is one agent question with a **known** correct answer plus the recipe for both paths:

| Field | Meaning |
|---|---|
| `id` | unique slug |
| `source` | `fixture` (committed dir, needs PHP) or `sample` (pinned public repo) |
| `root` | fixture directory, repo-relative (for `source: fixture`) |
| `atlas_path` | ordered `{tool, args}` calls a competent agent would make |
| `grep` | baseline search: `{pattern, globs?, max_read_files?}` |
| `expected` | substrings that MUST appear in the code-atlas responses |
| `grep_evidence` | substrings that must appear in what grep+`Read` surfaces (defaults to `expected`) |

State an answer you can verify exactly — `expected` is the falsifiable check, not "looks
plausible". Prefer symbols already asserted by other tests so the ground truth stays grounded.

## Sample tier (pinned public repos) — the real value claim (task 042)

The fixture floor above is a behaviour-lock, not the win. The **sample tier** runs the same recipes
against the pinned public repos in
[`cross_repo_samples.json`](../../scripts/cross_repo_samples.json) — real trees where a grep pattern
matches many files an agent must read whole while code-atlas returns the one resolved answer.

**Observed aggregate ratio: `98.2`** (grep `435,338` / code-atlas `4,433` tokens over 5 questions,
5/5 answered correctly) — i.e. code-atlas is ~**98×** cheaper here. Per-question ratios range from
`19.3` (symfony/demo `Post::getId` callers) to `147.4` (brick/math `BigInteger` references). This is
the number the fixtures cannot show (there, grep wins on volume at ~0.29).

### Reproduce

```bash
export CA_PHP_CMD="php $(pwd)/adapters/php/index.php --server"   # absolute adapter path
python scripts/tokens_to_answer.py --samples --min-ratio 78     # clones the pins, builds, gates
# reuse a warm clone cache and skip the network:
python scripts/tokens_to_answer.py --samples --skip-clone --cache-dir artifacts/tokens-to-answer-samples
```

`--samples` switches the harness to the sample tier: it groups `source: sample` questions by their
`sample` pin id, clones/checks out each pinned SHA (reusing `cross_repo_validate`'s machinery), builds
the index once per repo, then evaluates. Default (no `--samples`) behaviour is unchanged — fixtures
only — so the per-PR gate is untouched.

### Scheduled run

[`.github/workflows/tokens-to-answer-sample.yml`](../../.github/workflows/tokens-to-answer-sample.yml)
runs it on `workflow_dispatch` and weekly (Monday 06:30 UTC) with floor `78` (≈ `0.8 × observed`,
recalibrate from the first Linux run as with the fixture floor). Not per-PR: it needs a clone + PHP
and is slower. On failure it opens/comments a `tokens-to-answer-sample` issue (scheduled logs are easy
to miss).

### Coverage notes (falsifiable both ways)

- **Query kinds covered:** `find_implementations` (BigNumber subclasses), `find_references`
  (BigInteger, Tag), `find_callers` (BigNumber::isZero, Post::getId) — the kinds where grep over-reads.
- **`include_graph` ("who includes X") is intentionally not sampled here.** All three pinned repos are
  PSR-4 / Composer-autoloaded, so their `INCLUDES` edges are dynamic bootstrap `require`s with no
  resolved target — there is no verifiable "who includes X" answer to assert. The fixture tier already
  covers `include_graph` end to end.
- **laravel/laravel carries no sample question.** At the pinned SHA it is the application *skeleton*
  (~60 nodes, no cross-class callers, one `extends`), so it has no resolvable nav target rich enough
  for a grep-over-read question. It stays a cross-repo *build* sample (see
  [cross-repo validation](cross-repo-validation.md)); the nav questions live on brick/math and
  symfony/demo, which have real resolved graphs.
