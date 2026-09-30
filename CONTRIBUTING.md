# Contributing to code-atlas

code-atlas has a single maintainer. Bug reports, reproductions and focused fixes are welcome. For
anything larger (a new tool, a payload field, a new adapter), **open an issue first**, so the design
can be agreed before you write code.

## Reporting a bug

A useful report includes:

- the language and the adapter involved;
- the tool call and its full payload;
- the answer you expected, and why you expected it;
- the output of `get_index_status`;
- your OS and your Python, Node and PHP versions.

The most valuable report is a **confidently wrong answer**: an edge, count or `ok` result that is
false. Say so plainly in the title. Silence or a missing edge matters too, but a wrong answer comes
first.

Security issues do not go in a public issue; see [`SECURITY.md`](SECURITY.md).

## Development setup

You need a POSIX host (Linux, macOS, or WSL2 on its native filesystem), Python ≥ 3.12, and the
runtime for each adapter: PHP ≥ 8.1 with Composer, and Node.js ≥ 18.

```bash
python3 -m pip install -e ".[dev]"
composer install --working-dir=adapters/php
npm ci --prefix adapters/typescript
npm ci --prefix adapters/sql
```

No host runtimes? `scripts/docker-test.sh` runs the full suite inside the Linux test image.

## Before you open a PR

Run the gate once, after your last edit:

```bash
scripts/gate.sh            # or: scripts/gate.sh --docker
```

It mirrors every CI job in order. **Only `GATE GREEN` counts**: a skipped check makes the gate
exit non-zero, because a check that did not run has not verified anything.

The binding rules are in [`docs/ENGINEERING_RULES.md`](docs/ENGINEERING_RULES.md). Its pre-PR
self-check is the checklist in the PR template. The rules most likely to bite are:

- **No language branch in the core.** Nothing under `code_atlas/` may test which language it is
  handling. A branch means the adapter contract leaked, and CI rejects it.
- **Adapters encode the language standard, never a sample repo's names or framework.** A fix that
  only makes one project's output look right will not be merged.
- **The adapter contract is versioned.** A change to its vocabulary or qname shape bumps
  `contract_version`, updates `tests/contract/`, and cuts a release: the package version plus a
  CHANGELOG entry flagging the full rebuild (`tests/test_release_discipline.py` enforces it).
- **The core is deterministic.** No network or LLM call under `code_atlas/`. The optional LLM
  package lives in `onboarding_llm/`.
- **Every fix carries a test that fails without it.**

Adding or changing an adapter? Read [`docs/ADAPTER_PLAYBOOK.md`](docs/ADAPTER_PLAYBOOK.md) first.
Naming, layout and the payload contract are in [`docs/CONVENTION.md`](docs/CONVENTION.md).

## Commits and pull requests

- **Branch:** `type/short-slug`, where `type` is one of `feat`, `fix`, `chore` or `docs`.
- **Commit subject:** `type(scope): imperative subject`. The body explains *why* when that is not
  obvious.
- **No `Co-authored-by:` or AI-attribution trailer.** CI rejects them (`scripts/attribution_markers.py`).
- **Commit identity:** author and committer email must be a personal or GitHub noreply address; CI
  rejects a corporate domain (`scripts/identity_markers.py`).
- **PR body:** fill in every section of [the PR template](.github/pull_request_template.md), and
  update any doc your change makes stale in the same PR.

The maintainer's own work runs through task files in `docs/tasks/`, a token ledger, and an agent
lifecycle harness (`.harness.json`). None of that is required of you. An issue and a PR are enough.

## License

By contributing, you agree that your contribution is licensed under the [MIT License](LICENSE).
