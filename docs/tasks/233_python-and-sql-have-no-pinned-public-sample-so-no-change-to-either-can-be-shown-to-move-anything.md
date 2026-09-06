---
id: 233
slug: python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything
title: 'Python and SQL have no row in `cross_repo_samples.json`, so seven reports and every before/after measurement cover PHP and TS only — 137 could prove the type table moved 36.3 % → 2.6 % and 227 has no way to prove the same thing, on machinery that is already language-parameterised and needs two data rows'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [018, 150, 147, 228]
---

## Why this exists

`scripts/cross_repo_samples.json` holds **six** pinned public samples: three PHP (018) and three
TS/JS (150). **Zero Python. Zero SQL** — two of the four shipped adapters.

Everything that measures a change over real code reads that file:
`cross_repo_validate.py`, `edge_health_report.py`, `layer_report.py`, `module_report.py`,
`reachability_report.py`, `layer_diagram_report.py`, `tokens_to_answer.py`. All seven therefore
report on half the adapters.

**What that costs, concretely.** [137](../benchmarks/137_type-table.md) could state that the PHP
local type table took the HEURISTIC share from **36.3 % → 2.6 % on `brick/math`** and **36.1 % →
3.9 % on `symfony/demo`**, with a baseline reproduced on the same host before the change.
[227](227_python-has-no-local-type-table-so-every-member-call-is-heuristic.md) proposes the same
change for Python and **cannot make that claim at all** — there is no before, so there can be no
after. The same holds for 229's node-count correction, 230's source roots, and 231/232's field
parity: each would land with a fixture proving the mechanism and nothing proving the size.

**The machinery is already language-parameterised and the gap is data.** `edge_health_report.py:220`
reads `sample.get("language", "php")` and hands it to `index_root(root, language=…)`;
`cross_repo_validate.py:46-49` resolves the adapter command from `_ADAPTERS`, a dict keyed by
language — 147 moved that out of a code branch precisely so a new language is a row. Today that dict
names `php` and `typescript`, and `:247-249` refuses an unknown language by design. So this ticket
is **two rows in `_ADAPTERS`, four to six rows in the sample manifest, and their measured floors** —
not a code path.

**The one place a branch survives.** `layer_report.py:41-43` pins expected layer names per sample id
(`laravel_app`, `symfony_demo`, `brick_math`) — three PHP entries with no shape for anything else.
A Python or SQL sample needs its row there or that report has nothing to assert.

## Scope

1. **Add two rows to `_ADAPTERS`** — `python` → `CA_PYTHON_CMD`, `sql` → `CA_SQL_CMD`, with the same
   default shape the existing two use. Data, not a branch (147).
2. **Pin Python samples by *shape*, not by popularity.** The shapes that decide open tickets:
   a **`src/`-layout package** (230's source root is invisible without one), a **decorator-heavy
   framework app** (217/232's annotation and decorator counts), and a **flat package with deep
   member calls** (227's type table, 229's method-local assignments). Candidates worth evaluating:
   `pallets/flask`, `pydantic/pydantic`, `psf/requests`. **The implementer pins the SHA and measures
   the floors; this ticket does not guess either** — the manifest's own contract note sets floors at
   ≈80 % of a known-good smoke at the pinned SHA.
3. **Pin SQL samples, and accept that public T-SQL is scarce.** `microsoft/sql-server-samples` is the
   obvious source. **228 must land first**: today the adapter publishes a table named `IF` from
   `CREATE TABLE IF NOT EXISTS` and a column named `COLUMN` from `ALTER TABLE … ADD COLUMN`, so
   floors measured now would pin the defect as the baseline. Ordering, not a blocker on scope.
4. **Give each new sample its `layer_report.py` shape row,** or state in the PR which report is
   deliberately left unasserted for it and why (R5.6 — silence is not evidence).
5. **Re-run 137's protocol per language and file the results as benchmarks.** One `benchmarks/`
   file per language with the same columns 137 used, so 227 and 231 have a before to move.

**Not in scope:** the private consumer repos — they stay operator-local via
`CODE_ATLAS_SCALE_SAMPLE`, and a claim that cannot be reproduced from a pinned public SHA is an
anchor-only claim (R2). Fixing what the new samples reveal: each finding is its own ticket, as
221-232 were.

## Acceptance criteria

- **AC1** `cross_repo_validate.py` runs green over at least one Python and one SQL sample, with
  `failed=0` and floors recorded in the manifest's contract note beside the existing PHP and TS
  figures, naming the host and date (018's discipline).
- **AC2 (R6.5)** The floors are shown to bite: lowering a sample's `min_nodes` below its measured
  value and re-running must fail. A floor nobody has seen fail is not a gate.
- **AC3** `edge_health_report.py` produces a per-cause breakdown for a Python sample, and that table
  is committed as the baseline 227 will be measured against — dated, with the host named.
- **AC4** Every report that reads the manifest either asserts something for each new sample or
  states in the PR why it does not. A report silently skipping two of four languages is the state
  this ticket exists to end.
- **AC5** Determinism holds across the added languages: two clean runs over one pinned sample
  produce identical ordered rows (R4.2).

## Exclusions

- **E1** Network and both toolchains are required, so this cannot join per-PR CI — the same
  constraint `cross_repo_validate.py` already documents (`workflow_dispatch` / weekly schedule, or
  local). The deliverable is the committed floors and the benchmark files, not a green CI job.
- **E2** Repo choice is a judgement this ticket deliberately leaves open beyond the shape list in
  scope item 2. A sample chosen for stars rather than shape teaches nothing about the adapter.

## Notes

**Why the gap survived four adapters.** 018 pinned samples for PHP because PHP was the whole
product; 150 pinned them for TS because 150 was *"the TS adapter has no gate but its own fixtures"*.
020 · 217 (Python) and 184 · 022 (SQL) shipped against fixtures and the conformance registry, both of
which prove **construct correctness** and neither of which can show a **ratio over real code** —
the distinction [`../ADAPTER_PLAYBOOK.md`](../ADAPTER_PLAYBOOK.md) §4 now makes a required gate
rather than a habit.
