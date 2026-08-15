# AGENTS.md — code-atlas

Guidance for AI coding agents working in this repo. This file is the always-loaded orientation and the
single source of truth for it — Cursor and friends read `AGENTS.md` directly, Claude Code reaches it
through a one-line `CLAUDE.md` that imports this file. Edit here, never there. The docs below hold the
authoritative detail. **If anything here conflicts with them, they win — fix this file.**

<!-- mango:standing-context (regenerate with /mango:init — do not hand-edit) -->
**Harness:** `.harness.json` at the repo root governs mango. Session basics before acting:
`test_command` = `pytest`; `rulebook_path` = `docs/ENGINEERING_RULES.md` (every rule judgment
reads that file — do not copy rules here); `tickets_dir` / `work_dir` = `docs/tasks`;
`work_doc_mode` = `embed`; `branch_strategy` = `feat|fix|chore|docs/<NNN>-<slug>`;
`tracker.cli` = `gh`.
**Standing constraints (every phase):** the human holds every ✋ gate (silence ≠ approval); no
outward action without a separate explicit approval per action; tracker writes go through
`tracker.cli`, never MCP; stay inside the approved change list; every claim is a counted artifact.
Validate with `/mango:doctor`. Run a ticket with `/mango:solve <KEY>`.
<!-- /mango:standing-context -->

**Read these before non-trivial work** (they govern every session):
- [`docs/PLAN.md`](docs/PLAN.md) — authoritative design (§-refs below point here).
- [`docs/ENGINEERING_RULES.md`](docs/ENGINEERING_RULES.md) — binding *how we build* rules (R1.1…). The pre-PR self-check at the bottom is your gate.
- [`docs/AGENT_BRIEF.md`](docs/AGENT_BRIEF.md) — binding *how we run the lifecycle* rules (P1…): keeping `seen:` honest, reading a rule's destination before proposing a new one, recording a deviation from a ticket as a deviation.
- [`docs/CONVENTION.md`](docs/CONVENTION.md) — naming, repo layout, the fixed contract vocabulary, style.
- [`docs/BACKLOG.md`](docs/BACKLOG.md) — tasks (`docs/tasks/NNN_slug.md`); keep status in sync there **and** in each task's frontmatter.

## What this is
A local-first **MCP server** that indexes a codebase into **SQLite** and exposes fast, name-resolved,
token-efficient **search / read / navigation / impact** tools. **Language-agnostic core + per-language
adapters**, joined by one versioned **JSON contract**. Roll-out order: **PHP → TypeScript/JavaScript →
Python → C#/.NET**. An Understand-Anything-style onboarding layer is Phase 2.

```
MCP client ──stdio──▶ core (Python/FastMCP) ──JSONL contract──▶ language adapter (PHP: nikic/php-parser)
                          │
                          ▼
                   SQLite .code-atlas/graph.db   (nodes · edges · files · fts5 · meta, WAL, incremental)
```

## Non-negotiable rules (summary — authoritative detail in ENGINEERING_RULES.md)
- **Zero language branches in the core** — no `if language == …` under `code_atlas/`; a branch means the contract leaked (R1.1, CI-gated).
- **One seam, YAGNI** — the adapter contract is the only abstraction; no registry/base-classes/DI until adapter #2 exists (R1.2).
- **SRP boundaries** — adapters parse only; `store.py` owns SQLite; the two never import each other (R1.4).
- **Standard over sample** — adapters encode the language spec/PSRs, never a repo's names or framework; samples drive tests/perf only (R2, CI-gated).
- **Contract is frozen & versioned** — change vocabulary/qname ⇒ bump `contract_version` + update conformance tests; `contract.py` is the single source of truth (R3).
- **Deterministic core** — no LLM/network in the core (that's Phase-2 onboarding only); identical input → identical rows (R4).
- **Do NOT use the Claude Code Memory feature** for this project — decisions live in the plan (§19) and the repo.
- **Commits** — no `Co-Authored-By` / AI-attribution trailer.
- **Comments** — keep every code comment to **≤ 3 lines**; if it needs more, the code or a doc should carry it instead.
- **Docs before PR** — before opening a PR, update every doc the change affects (PLAN, BACKLOG + task frontmatter, CONVENTION, ENGINEERING_RULES, README) so the docs match the work. The PR self-check gates this.
- **Token usage on PR** — before opening a PR, record the task's token spend in its working-doc cost ledger (`docs/tasks/NNN_slug.work.md`) **and** add/update its row in the Token usage table in [`docs/BACKLOG.md`](docs/BACKLOG.md). No PR without the token spend recorded in both places.
- **Pull requests** — when asked to open a PR, base it on `.github/pull_request_template.md` (fill every section, complete the pre-PR self-check). If the template is missing, propose one and create it first, then open the PR.

## Where things live
- Core: `code_atlas/` (`main.py` FastMCP, `config.py`, `contract.py`, `adapter.py`, `store.py`, `indexer.py`, `resolver.py`, `tools/`).
- Adapters: `adapters/<lang>/`, each self-contained and launched via `CA_<LANG>_CMD` (PHP first).
- Tests: `tests/contract/` — the conformance suite every adapter must pass. Full layout + naming in CONVENTION.md.
- Tooling: `.harness.json` (mango lifecycle config), `.github/workflows/ci.yml` (ruff · mypy · pytest + R1.1/R2.2 grep-gates), `.github/pull_request_template.md`.
- Docker: `docker/Dockerfile` (test image), `docker/Dockerfile.runtime` (ship the server), `docker/compose.yaml`, `scripts/docker-test.sh`.

## Running the full test suite — use Docker, never report it as unrunnable
`test_command` is `pytest`, but the full suite needs a **POSIX host** (the index lock imports `fcntl`)
and the **PHP adapter** (`php` + `composer install`). On the maintainer's **Windows** dev host bare
`pytest` is red — `fcntl` breaks collection of every module importing `main.py`, and the PHP-adapter
subprocess tests can't launch. **This is a platform limitation, not a regression** — do not conclude
"the suite can't run" and do not ask how to run it. Run it in Docker:

- `scripts/docker-test.sh` — builds `docker/Dockerfile` (Linux + PHP adapter) and runs the CI gate
  `ruff · mypy · pytest -q`. Expect **~1049 passed, 0 skipped**. Scope it by passing a command, e.g.
  `scripts/docker-test.sh pytest -q -k php`.
- Prove **delta-green here** before a PR. A bare-`pytest` red on Windows is the known platform
  exclusion above — confirm green via Docker, then say so; don't leave it as "unverified".
- Ship the server itself in a container with `docker/Dockerfile.runtime` (stdio; mount the repo at
  `/workspace`) — see README *Ship the server in a container*.

## Maintainer workflow — single-maintainer repo; don't re-ask what's already authorized
- **Finishing a task runs through to the PR without pausing to confirm:** commit in logical units →
  push the **feature branch** → open a PR from `.github/pull_request_template.md` (docs + token ledger
  updated first, per the rules above). This is the maintainer's standing, durable approval recorded
  here — it *is* the per-action approval mango asks for on these finishing steps; the maintainer
  reviews on the PR.
- **Still stop and confirm** for irreversible / higher-blast actions: force-push, history rewrite,
  deleting a branch/tag, committing to `main` directly, merging a PR, or publishing an image/release.
- **Honor the run's args:** `/mango:solve … with skipped review` means run without the review phase and
  don't reintroduce a waived gate; still surface each ✋ gate in-conversation so the maintainer can
  interject, but proceed on the standing approval rather than waiting.

## Ship discipline (plan §15)
M0 spike → M1 full build → M2 resolver+contract tests → **M3 search/read/outline = first daily release (task 014)** → M4 scale → M5 incremental → M6 impact. Then adapters #2–#4, then onboarding.
