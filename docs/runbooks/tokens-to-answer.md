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

## Sample tier (pinned public repos)

`source: sample` questions run against [`cross_repo_samples.json`](../../scripts/cross_repo_samples.json)
and need a clone+PHP environment, so they are **not** populated here yet — the harness lists any it
skips under `sample_questions_skipped` in the report rather than silently covering nothing.
