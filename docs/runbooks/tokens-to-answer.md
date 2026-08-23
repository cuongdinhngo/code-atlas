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
python3 scripts/tokens_to_answer.py                              # report only
python3 scripts/tokens_to_answer.py --min-ratio 0.63 --min-recall 1.0  # CI gates
```

The report lands under `artifacts/` (gitignored). The pure-Python gate tests
(`estimate_tokens`, `aggregate`, `assert_benchmark`, grep path, recall scoring) run in CI with no PHP; the
`@needs_php` test builds the fixtures and runs every committed question end to end.

## Automatic gate (every PR)

The `test` job in [`ci.yml`](../../.github/workflows/ci.yml) runs
`python scripts/tokens_to_answer.py --min-ratio 0.63 --min-recall 1.0 --markdown … --notice` on every
PR — it fails on a wrong answer, a recall miss / `confidently_wrong`, or if the ratio regresses. It
runs on **3.13 only** (a token count does not vary by interpreter) and reports in four places, so
nobody has to open a log:

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

**The floor is a behavior-lock, not the value claim.** Most committed fixtures are 4-file toy repos
where `get_index_status` overhead makes code-atlas *cost more* than reading one tiny file: the named
questions alone measured ≈ **0.288** (1666 vs 479 tokens over 10 questions, all correct). The
**onboarding class** (task 121) raised the fixture aggregate to **0.789** over 13 ratio-eligible
questions, because its questions are the first fixture-tier questions that make grep read more than one
file. The full token win (ratio ≫ 1) still appears only on realistic repos — that is the **sample
tier**, measured on schedule, not per PR.

## Local tier (a repo already on disk) — task 045

The fixture tier needs the tree committed here; the sample tier needs it clonable from a public pin.
Neither fits the repo the §19 pivot actually names as the evaluation anchor: a **large private
monorepo already on this machine**. The local tier is for that case.

```bash
export CA_PHP_CMD="php $(pwd)/adapters/php/index.php --server"
python scripts/tokens_to_answer.py --local --questions /abs/path/outside/this/repo/questions.json
```

A local question sets `"source": "local"` and an absolute `root`. The tree is used **in place** — no
copy, no `git init`, no rebuild — and the index is whatever `root`'s own `.code-atlas.toml` resolves,
because a real repo costs minutes to build and re-paying that per run makes the harness unusable. A
missing index is a loud `FileNotFoundError` naming the path, never a zero-token "answer". Pass
`--local-build` to build one anyway.

```json
{"questions": [{
  "id": "who-calls-charge", "source": "local", "root": "/abs/path/to/your-repo",
  "atlas_path": [{"tool": "find_callers", "args": {"qname": "\\Billing::charge"}}],
  "expected": ["Invoice::finalise"],
  "grep": {"pattern": "->charge\\(", "globs": ["*.php"], "max_read_files": 20}
}]}
```

**Keep the question file and the report outside this repository.** Both name someone's tree. The
report therefore defaults to `artifacts/tokens-to-answer-local-report.json` — deliberately *not* the
`artifacts/tokens-to-answer-report.json` that [`ci.yml`](../../.github/workflows/ci.yml) uploads — and
the markdown verdict says in words that the numbers belong to that repo and not to this one. `--local`
is opt-in, mutually exclusive with `--samples`, and never used by CI; the committed question set is
guarded against a `local` row by `test_questions_file_is_well_formed`.

One caveat before trusting a local ratio: `run_grep_path` models grep as "scan the tree, then read
every matched file whole", and it walks the **whole** tree per question — ignore rules do not apply,
because a real agent's grep sees those files too. It is bounded in memory (at most `max_read_files`
bodies at a time) but still O(repo) in time, so expect seconds per question on a repo-sized tree.

### Onboarding class on a repo of your own (local tier)

The two shapes the committed tiers **cannot** measure are the two a large legacy monorepo has most of:
*"does this feature exist on both mirror subtrees, or only one?"* (a mirror pair needs 25 shared
relative paths before it is reported, so no toy fixture can carry one and neither pinned sample has one)
and *"which files implement the &lt;named business screen&gt;?"* on a tree nobody can hold in their head.
Run those where such a tree exists, with this template — **kept outside this repository**, because every
line of it names someone's code:

```json
{"questions": [
  {"id": "onb_local_layers", "source": "local", "root": "/abs/path/to/your-repo",
   "tier": "onboarding", "ratio_eligible": false,
   "ratio_note": "grep+Read cannot produce a layering.",
   "question": "What are this codebase's top-level layers, and how do they depend on each other?",
   "atlas_path": [{"tool": "architecture_overview", "args": {"detail_level": "standard"}}],
   "expected": ["<a layer name you verified by hand>"],
   "expected_set": ["<every layer you expect>", "..."]},

  {"id": "onb_local_mirror", "source": "local", "root": "/abs/path/to/your-repo",
   "tier": "onboarding",
   "question": "Does <feature> exist on both mirror subtrees, or only one?",
   "atlas_path": [{"tool": "architecture_overview", "args": {"detail_level": "standard"}},
                  {"tool": "search_symbol", "args": {"query": "<feature>", "detail_level": "minimal"}}],
   "grep": {"pattern": "<feature>", "globs": ["*.php"], "max_read_files": 20},
   "expected": ["<the path on side A>", "<the path on side B, or the one you proved absent>"],
   "expected_set": ["<complete, established by hand first>"],
   "grep_evidence": ["<a line grep must surface>"]},

  {"id": "onb_local_screen", "source": "local", "root": "/abs/path/to/your-repo",
   "tier": "onboarding",
   "question": "Which files implement the <named business screen>?",
   "atlas_path": [{"tool": "search_symbol", "args": {"query": "<screen>", "detail_level": "minimal"}}],
   "grep": {"pattern": "<screen>", "globs": ["*.php"], "max_read_files": 20},
   "expected": ["<a qname you verified by hand>"],
   "expected_set": ["<complete, established by hand first>"],
   "grep_evidence": ["<a line grep must surface>"]}
]}
```

```bash
export CA_PHP_CMD="php $(pwd)/adapters/php/index.php --server"
python scripts/tokens_to_answer.py --local --questions /abs/path/outside/this/repo/onboarding.json
# rows land in artifacts/tokens-to-answer-local-report.json — per question, not just the aggregate
```

Three rules, or the numbers are worthless:

1. **Establish every ground truth by hand, written down before the tools run.** Do not let the map
   define its own correct answer — that is the one failure mode this measurement cannot recover from.
2. **Do not include `generate_onboarding`.** It writes `docs/onboarding/` into the tree it is pointed
   at; the committed fixture tier measures it on an isolated copy for exactly that reason.
3. **Report per question, not the aggregate.** An average hides the case where the map wins big on two
   and loses on six — which is precisely what happened on `symfony/demo`.

### First local-tier measurement

Run against one large private PHP monorepo (~19k indexed files, PSR-4 + non-namespaced legacy),
5 questions, **5/5 answered correctly on both paths** — grep found the evidence too, it just paid for
it. **Aggregate ratio 178.3** (grep 838,988 / code-atlas 4,705 tokens):

| Question kind | code-atlas | grep+`Read` | ratio |
|---|---|---|---|
| `find_references` on a legacy base class | 517 | 324,243 | 627.2 |
| `find_callers` on a region predicate | 774 | 256,303 | 331.1 |
| `find_callers` on a DB builder | 648 | 212,184 | 327.4 |
| `find_implementations` on an interface | 611 | 27,750 | 45.4 |
| `read_symbol` on one class | 2,155 | 18,508 | 8.6 |

The spread is the finding, not the aggregate. Relation queries on names that appear across a thousand
legacy files are where the index earns its cost; `read_symbol` — where grep's own answer is already
narrow — wins by less than an order of magnitude. Read the aggregate as "dominated by the widest
question", and pick questions that match the work you actually do.

### What this metric cannot see

That first run also exposed that every nav row came back twice on this repo, and the obvious inference
— "so the real ratio is about twice as good" — is **wrong**. Task 046 removed the duplication and the
run was repeated against the rebuilt index:

| | before 046 | after 046 |
|---|---|---|
| code-atlas tokens | 4,705 | **4,704** |
| aggregate ratio | 178.318 | **178.356** |
| distinct answers in a 10-row response | 5 | **10** |

The ratio moved by 0.02 %. `max_results` fills the response budget either way, so removing the
duplicates did not make the answer cheaper — it **doubled the information at the same price**, and
tokens-to-answer is blind to that by construction: it counts what a payload costs, never what it
carries. A tool returning ten duplicates and a tool returning ten distinct answers score identically.

### Recall gates, cost wins (task 055)

Treat the ratio as a **cost** measure, not a quality measure. **Recall is the gate; cost is the win.**
A cheaper answer that finds less of a known ground-truth set is a regression — CI enforces that with
`--min-recall 1.0` on the fixture tier alongside `--min-ratio 0.63`.

- **`expected_set`** — complete hand-written ground truth; the harness reports `recall`, `found`,
  `missing`.
- **`confidently_wrong`** — empty `results` when ground truth is non-empty. Counted separately from a
  partial-recall miss (some hits, not all): the empty answer is what makes an agent stop using the tool.
- **Symptom-first / session recipes** (`session_path`) mix native `grep` / `read_file` with MCP tools and
  report session tokens, files read, and **index-use share** (MCP calls / all calls). Short named
  fixture recipes are MCP-only, so they do not pretend to measure that share.
- **Whole-graph questions** exercise `impact` / `reachable_from` / `find_orphans` (and similar). When
  there is no fair grep baseline, set `ratio_eligible: false` so they do not dilute the cost aggregate.

Private-repo symptom sets stay **outside** this repository (same rule as the local tier, task 045).

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
work also moves it: the ratio has drifted **0.302 → 0.293 → 0.286 → 0.282 → 0.367** (1409 → 1452 →
1484 → 1696 → 1305 atlas tokens) as tasks 033 and 035 added `reason` / `total_count` to every payload
and task 061 then trimmed the dead fields back out. The 1484 → 1696 step was **observed** during task
045 and is not attributed: 045 changed no payload, and a stash-and-compare run proved the fixture
report byte-identical across its diff. Whatever widened those responses did so without updating this
line — which is the argument for re-reading the floor before calling a breach a retrieval regression.

**Task 071 broke the series, and the fix is why the current number is comparable at all.** Putting an
absolute `index_root` on every answer made the count a function of *where the checkout lives*: the same
code, same 14/14 answers, measured **0.326** with the fixture workdir at `/tmp/w`, **0.277** sixty
characters deeper, and **0.236** at ~110 characters. A floor calibrated on one path reads as a
retrieval regression on another. `normalize_env_paths` now substitutes a fixed-width placeholder for
`index_root` / `db_path` **in the counted blob only** — a field's presence is still paid for, so adding
one still moves the number, while moving the repo does not. Post-fix the fixture tier is **0.336**
(1426 atlas tokens), identical across all three workdirs, and the floor is **0.27**. Figures before
this paragraph were counted with verbatim paths and are not strictly comparable to it.

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
| `expected_set` | the **complete** ground-truth set, so 055's recall gate scores the answer |
| `tier` | question class — `named` (default), `whole_graph`, `symptom`, `onboarding` |
| `ratio_eligible` | `false` when no fair grep baseline exists |
| `ratio_note` | **required** whenever the question is out of the ratio: why, in one sentence. It reaches the report row, so the artifact carries the reason too |

State an answer you can verify exactly — `expected` is the falsifiable check, not "looks
plausible". Prefer symbols already asserted by other tests so the ground truth stays grounded.

## Onboarding class (task 121)

`ROADMAP.md` §5 gated the whole onboarding phase on an onboarding question-class here plus the
recall gate, and for three milestones the file held **zero** of them. The class now exists: twelve
questions tagged `tier: onboarding`, ten on the committed fixture `tests/fixtures/php/onboarding` and
two on the pinned `symfony/demo`. It covers a newcomer's shapes — layers and their crossings, a reading
order, what depends on a hub, what a change breaks, is this file dead, which files implement a feature,
where a page is pulled in, which declaration produced a count, write me a committable map, and which
paths name no responsibility at all.

Nine of the twelve are **out of the cost ratio on purpose**: a layering, a reading order, a blast radius
and a whole-graph negative are not things a grep pattern returns, and each says so in its `ratio_note`
rather than carrying a baseline invented to flatter the comparison.

**Read the verdict, both halves, in
[`docs/benchmarks/121_onboarding-question-class.md`](../benchmarks/121_onboarding-question-class.md)** —
the class is cheaper than hand-mapping where the question is a lookup, and **wrong** where the question
is a reading order (tickets 129 · 130 · 131 came out of the run).

## Sample tier (pinned public repos) — the real value claim (task 042)

The fixture floor above is a behaviour-lock, not the win. The **sample tier** runs the same recipes
against the pinned public repos in
[`cross_repo_samples.json`](../../scripts/cross_repo_samples.json) — real trees where a grep pattern
matches many files an agent must read whole while code-atlas returns the one resolved answer.

**Observed aggregate ratio: `98.2`** (grep `435,338` / code-atlas `4,433` tokens over 5 questions,
5/5 answered correctly) — i.e. code-atlas is ~**98×** cheaper here. Per-question ratios range from
`19.3` (symfony/demo `Post::getId` callers) to `147.4` (brick/math `BigInteger` references). This is
the number the fixtures cannot show (there the aggregate is 0.789, and grep still wins on volume
on the named questions). Adding task 121's two onboarding questions moved this aggregate to
**69.06** — not a regression, but an aggregate now spanning two question classes: an onboarding
lookup that makes grep read five files cannot show the ~100× that a `find_references` over a
40-file tree shows.

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
runs it on `workflow_dispatch` and weekly (Monday 06:30 UTC) with floor `55` (≈ `0.8 × observed`,
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
