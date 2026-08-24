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

**Read these before non-trivial work** — **tier 1**; every session pays for all of it, so it is capped at 25,000 tokens by `tests/test_agent_chain_budget.py`, measured by `scripts/agent_chain_cost.py`:
- [`docs/ENGINEERING_RULES.md`](docs/ENGINEERING_RULES.md) — binding *how we build* rules (R1.1…). The pre-PR self-check at the bottom is your gate.
- [`docs/AGENT_BRIEF.md`](docs/AGENT_BRIEF.md) — binding *how we run the lifecycle* rules (`P1`…`Pn`), each earned by a cited incident. Read them there; this file does not enumerate them, because the copy it used to keep went a rule out of date.
- [`docs/CONVENTION.md`](docs/CONVENTION.md) — naming, repo layout, the fixed contract vocabulary, style.
- [`docs/BACKLOG.md`](docs/BACKLOG.md) — tasks (`docs/tasks/NNN_slug.md`); keep status in sync there **and** in each task's frontmatter.

**Consult when you need it** — **tier 2**: reference, binding where a tier-1 rule cites it, but reached by a pointer and never read at session start:
- [`docs/PLAN.md`](docs/PLAN.md) — authoritative design; every `§`-ref below points here, and §19 is the decision log you open when a decision is questioned.
- [`docs/TOKEN_LEDGER.md`](docs/TOKEN_LEDGER.md) — one spend row per ticket (R7.2).
- [`docs/LESSONS.md`](docs/LESSONS.md) — the claim corpus promotion reads; its `seen:` counts are the only gate (P1).
- [`docs/SKILL_GAP_CANDIDATES.md`](docs/SKILL_GAP_CANDIDATES.md) — type-3 signals for mango's maintainer; this repo never edits a skill.

## What this is
**Two pillars, one graph** — PILLAR 1 the resolved relationships an agent asks for, PILLAR 2 the
rendering of what the code actually is, for a human supervising that agent or presenting the project.
Both read the same graph; the map never runs a second pipeline. Stated authoritatively — and this is
the only place to state it — in [`docs/PLAN.md`](docs/PLAN.md) §1.

A local-first **MCP server** that indexes a codebase into **SQLite** and exposes fast, name-resolved,
token-efficient **search / read / navigation / impact** tools. **Language-agnostic core + per-language
adapters**, joined by one versioned **JSON contract**. Roll-out order: **PHP → TypeScript/JavaScript →
Python → C#/.NET**. An Understand-Anything-style onboarding
layer is **Phase 3, and it has shipped** (M10-M12) — it emits a committable system map from the same
graph, deterministic by default with LLM prose opt-in and out of the core.

```
MCP client ──stdio──▶ core (Python/FastMCP) ──JSONL contract──▶ language adapter (PHP: nikic/php-parser)
                          │
                          ▼
                   SQLite .code-atlas/graph.db   (nodes · edges · files · fts5 · meta, WAL, incremental)
                          │
                          ▼
          onboarding enrichment (deterministic) ──▶ tools · markdown · system map
                          ╎ three Protocol seams, off by default
                          └╌╌▶ onboarding_llm/  (opt-in LLM prose — OUTSIDE the core)
```

## Non-negotiable rules (summary — authoritative detail in ENGINEERING_RULES.md)
- **Zero language branches in the core** — no `if language == …` under `code_atlas/`; a branch means the contract leaked (R1.1, CI-gated).
- **One seam, YAGNI** — the adapter contract is the only abstraction; no registry/base-classes/DI until adapter #2 exists (R1.2).
- **SRP boundaries** — adapters parse only; `store.py` owns SQLite; the two never import each other (R1.4).
- **Standard over sample** — adapters encode the language spec/PSRs, never a repo's names or framework; samples drive tests/perf only (R2, CI-gated).
- **Contract is frozen & versioned** — change vocabulary/qname ⇒ bump `contract_version` + update conformance tests; `contract.py` is the single source of truth (R3).
- **Deterministic core** — no LLM/network in the core; the onboarding LLM lives in `onboarding_llm/`,
  outside `code_atlas/`, injected through Protocol seams and off by default (R4/R4.1, CI-gated).
  Identical input → identical rows (R4.2).
- **Do NOT use the Claude Code Memory feature** for this project — decisions live in the plan (§19) and the repo.
- **Commits** — no `Co-Authored-By` / AI-attribution trailer.
- **Comments** — keep every code comment to **≤ 3 lines**; if it needs more, the code or a doc should carry it instead.
- **Docs before PR — prune as you add, cost included** — update every doc the change affects, and
  record the task's token spend in both its working-doc ledger and [`docs/TOKEN_LEDGER.md`](docs/TOKEN_LEDGER.md) (R7.2).
  **A change that adds to a standing doc removes what it supersedes in the same commit, and never
  retells what a task file, LESSONS.md or a benchmark already holds** (R7.6): every line here is
  charged to every future session. The pre-PR self-check gates the docs;
  `tests/test_backlog_bookkeeping.py` gates the spend and `tests/test_doc_size_budget.py` the size.
- **Pull requests** — when asked to open a PR, base it on `.github/pull_request_template.md` (fill every section, complete the pre-PR self-check). If the template is missing, propose one and create it first, then open the PR (CONVENTION §7).

## Where things live
- Core: `code_atlas/` (`main.py` FastMCP, `config.py`, `contract.py`, `adapter.py`, `store.py`, `indexer.py`, `resolver.py`, `tools/`).
- Onboarding: `code_atlas/onboarding/` (deterministic enrichment — metrics, layers, dataset, artifact,
  viewer, tour, mirrors, reachability, headlines, quality gate) + `onboarding_llm/` (the opt-in LLM
  implementers, kept outside the core by R4.1).
- Adapters: `adapters/<lang>/`, each self-contained and launched via `CA_<LANG>_CMD` (PHP first).
- Tests: `tests/contract/` — the conformance suite every adapter must pass. Full layout + naming in CONVENTION.md.
- Tooling: `.harness.json` (mango lifecycle config), `.github/workflows/ci.yml` (ruff · mypy · pytest + R1.1/R2.2/R4.1 grep-gates), `.github/pull_request_template.md`.
- Docker: `docker/Dockerfile` (test image), `docker/Dockerfile.runtime` (ship the server), `docker/compose.yaml`, `scripts/docker-test.sh`.

## Before a PR or a push — run `scripts/gate.sh`
**GitHub Actions cannot run for this repo** (private, no Actions budget: every job fails in seconds
with no logs). `scripts/gate.sh` **is** the gate — it mirrors all three CI jobs in `ci.yml`'s order:
entry points · ruff · mypy · pytest · tokens-to-answer · composer validate · `php -l` · phpstan ·
the four grep-gates. ~100 s here; `--fast` skips pytest and the benchmark for a quick loop.
**Only `GATE GREEN` counts — exit 2 means a check was skipped, which is not a pass (R6.5).** Keep it
in step with `ci.yml`: a check in one and not the other means one of them is lying about what was
verified.

## Running the full test suite — use Docker, never report it as unrunnable
The suite needs a **POSIX host** (the index lock imports `fcntl`) and the **PHP adapter**. On the
maintainer's **Windows** dev host bare `pytest` is red for both reasons. **This is a platform
limitation, not a regression** — do not conclude "the suite can't run" and do not ask how to run it.
Run it in Docker: the commands and the expected count are in [README *Testing*](README.md#testing)
(`scripts/docker-test.sh`, ~1679 passed / 0 skipped as of 2026-08-21).

Prove **delta-green** before a PR, and name the host that produced it. A bare-`pytest` red on
Windows is the known platform exclusion above — confirm green via Docker, then say so; don't leave
it as "unverified". To ship the server itself in a container, use `docker/Dockerfile.runtime`
(stdio; mount the repo at `/workspace`) — see README *Ship the server in a container*.

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
M0 spike → M1 full build → M2 resolver+contract tests → **M3 search/read/outline = first daily release (task 014)** → M4 scale → M5 incremental → M6 impact.
**Phase 3 onboarding shipped ahead of language breadth:** M10 (`architecture_overview` + layers) · M11
(`guided_tour`, `generate_onboarding`, the navigable system map) · M12 (opt-in LLM prose behind three
seams, out of the core) are **all complete** — 19 tools on the surface. Adapters #2–#4 stay **deferred**
(§19 pivot: depth before breadth).
