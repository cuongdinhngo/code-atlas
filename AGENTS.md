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

**Read these before non-trivial work** — **tier 1**; every session pays for all of it, so it is capped by `tests/test_agent_chain_budget.py`, measured by `scripts/agent_chain_cost.py`:
- [`docs/ENGINEERING_RULES.md`](docs/ENGINEERING_RULES.md) — binding *how we build* rules (R1.1…). The pre-PR self-check at the bottom is your gate.
- [`docs/AGENT_BRIEF.md`](docs/AGENT_BRIEF.md) — binding *how we run the lifecycle* rules (`P1`…`Pn`), each earned by a cited incident. Read them there; this file never copies them — a copy went a rule out of date.
- [`docs/CONVENTION.md`](docs/CONVENTION.md) — naming, repo layout, the fixed contract vocabulary, style.
- [`docs/BACKLOG.md`](docs/BACKLOG.md) — tasks (`docs/tasks/NNN_slug.md`); keep status in sync there **and** in each task's frontmatter.

**Consult when you need it** — **tier 2**: reference, binding where a tier-1 rule cites it, but reached by a pointer and never read at session start:
- [`docs/PLAN.md`](docs/PLAN.md) — authoritative design; every `§`-ref below points here, and §19 is the decision log you open when a decision is questioned.
- [`docs/TOKEN_LEDGER.md`](docs/TOKEN_LEDGER.md) — one spend row per ticket (R7.2).
- [`docs/LESSONS.md`](docs/LESSONS.md) — the claim corpus promotion reads; its `seen:` counts are the only gate (P1).
- [`docs/ADAPTER_PLAYBOOK.md`](docs/ADAPTER_PLAYBOOK.md) — the standard for building and judging an adapter: the two tiers, the optional-field decisions, the five gates, the traps already paid for. Read before touching `adapters/`.
- [`docs/SKILL_GAP_CANDIDATES.md`](docs/SKILL_GAP_CANDIDATES.md) — type-3 signals for mango's maintainer; this repo never edits a skill.

## What this is
**Two pillars, one graph** — PILLAR 1 the resolved relationships an agent asks for, PILLAR 2 the
rendering of what the code actually is, for a human supervising that agent or presenting the project.
Both read the same graph; the map never runs a second pipeline. Stated authoritatively — and this is
the only place to state it — in [`docs/PLAN.md`](docs/PLAN.md) §1.

A local-first **MCP server** that indexes a codebase into **SQLite** and exposes fast, name-resolved,
token-efficient **search / read / navigation / impact** tools. **Language-agnostic core + per-language
adapters**, joined by one versioned **JSON contract** (order and status: §3). An
Understand-Anything-style onboarding
layer is **Phase 3, and it has shipped** (M10-M12) — it emits a committable system map from the same
graph, deterministic by default with LLM prose opt-in and out of the core.

```
MCP client ──stdio──▶ core (Python/FastMCP) ──JSONL contract──▶ language adapter (php · typescript · sql · python)
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
- **One seam, YAGNI** — the adapter contract is the only abstraction; **verdict: no registry** (R1.2).
- **SRP boundaries** — adapters parse only; `store.py` owns SQLite; the two never import each other (R1.4).
- **Standard over sample** — adapters encode the language spec and its ecosystem standards, never a repo's names or framework; samples drive tests/perf only (R2, CI-gated).
- **Contract is frozen & versioned** — change vocabulary/qname ⇒ bump `contract_version` + conformance tests + cut a release; `contract.py` is the single source of truth (R3).
- **Deterministic core** — no LLM/network in the core; the onboarding LLM lives in `onboarding_llm/`,
  outside `code_atlas/`, injected through Protocol seams and off by default (R4/R4.1, CI-gated).
  Identical input → identical rows (R4.2).
- **Do NOT use the Claude Code Memory feature** for this project — decisions live in the plan (§19) and the repo.
- **Commits** — no `Co-Authored-By` / AI-attribution trailer.
- **Comments** — keep every code comment to **≤ 3 lines**; if it needs more, the code or a doc should carry it instead (R7.5).
- **Docs before PR — prune as you add, cost included** — update every doc the change affects, and
  record the task's token spend in both its working-doc ledger and [`docs/TOKEN_LEDGER.md`](docs/TOKEN_LEDGER.md) (R7.2).
  **A change that adds to a standing doc removes what it supersedes in the same commit, and never
  retells what a task file, LESSONS.md or a benchmark already holds** (R7.6): every line here is
  charged to every future session. The pre-PR self-check gates the docs;
  `tests/test_backlog_bookkeeping.py` gates the spend and `tests/test_doc_size_budget.py` the size.
- **Pull requests** — when asked to open a PR, base it on `.github/pull_request_template.md` (fill every section, complete the pre-PR self-check). If the template is missing, propose one and create it first, then open the PR (CONVENTION §7).

## Where things live
**The map is [`docs/CONVENTION.md`](docs/CONVENTION.md) §1** — a second copy here is one more thing
to keep in step, and it drifted. Only the boundaries that decide where your change may go:
- Core `code_atlas/` is language-agnostic; `store.py` is the only file that touches SQLite (R1.4).
- `code_atlas/onboarding/` is deterministic; the LLM implementers live in `onboarding_llm/`, outside
  the core by R4.1 (CI grep-gated).
- `adapters/<lang>/` is self-contained and launched via `CA_<LANG>_CMD`; `tests/contract/` is the
  conformance suite every adapter must pass.

## Indexing a real repo — from a shell
`code-atlas-build` builds; `--status` reads a running build's live phase, which no MCP tool can.
A full rebuild serves the old index until it publishes (356); never delete `graph.db`. `workers` is not a throughput
knob. Every timing and its conditions: [`runbooks/onboarding-a-repo.md`](docs/runbooks/onboarding-a-repo.md).

## Before a PR or a push — run `scripts/gate.sh` **once, when the work is done**
**Not per edit** — iterate on targeted `ruff`/`mypy`/`pytest`, batch every fix, then one gate run.
**`gh pr checks` is not the gate:** Actions run after the push; the local gate runs before it.
**Only `GATE GREEN` counts — exit 2 means a check was skipped, which is not a pass (R6.5).**
**Cross-repo is outside the gate:** a change moving graph counts runs `cross_repo_validate.py` and re-floors (P8).
The gate mirrors `ci.yml` (`tests/test_ci_and_gate_agree.py`); `--docker` adds the image build and
covers a missing runtime.
**The gate's tokens-to-answer ratio is the *fixture* tier and sits below 1 by design** (floor 0.63) —
the product claim is the *sample* tier over the pinned repos (`--samples`, ~69x). Never quote one as
the other.

## Running the full test suite — never report it as unrunnable
**Runtime supported on native Windows; test suite + dev loop stay POSIX** —
run under WSL2, never `/mnt/*`; the rest is in README.
The suite needs a **POSIX host** (four tests import `fcntl`/`resource`) and **every adapter**: `php` + `composer`, `node` for both the TS and SQL adapters, and a
Python ≥ 3.12 interpreter —
with all of them present, bare `pytest` is the fastest route. Missing either condition it goes red —
**a platform limitation, not a regression** — so don't conclude "the suite can't run"; run it in
Docker instead: `scripts/docker-test.sh`. **Expected count — the one place these numbers are
kept:** `scripts/docker-test.sh` **4,081 passed / 5 skipped** (2026-09-30, after 351).
Bare `pytest` on Linux (`php` · `composer` · `node` · `docker` on PATH) was 4,084 / 4 on the same
tree — re-measure on POSIX, never derive. Green skips: the Windows lock arm (3) and the
`gitutil` wedge; in-image also `test_runtime_image_reports_server_build`.

Prove **delta-green** before a PR and name the host: a red run on a host missing an adapter is the
exclusion above — confirm green via Docker and say so, never "unverified". Ship the server in a
container via `docker/Dockerfile.runtime` (stdio; mount at `/workspace`).
**Run Docker once, before the PR** — the gate rule above, applied to `docker-test.sh`: batch every
fix (review's included) into one run; CI re-verifies.

## Maintainer workflow — single-maintainer repo; don't re-ask what's already authorized
- **Finishing a task runs through to the PR without pausing to confirm:** commit in logical units →
  push the **feature branch** → open a PR from `.github/pull_request_template.md` (docs + token ledger
  updated first, per the rules above). This is the maintainer's standing, durable approval recorded
  here — it *is* the per-action approval mango asks for on these finishing steps; the maintainer
  reviews on the PR.
- **Still stop and confirm** for irreversible / higher-blast actions: force-push, history rewrite,
  deleting a branch/tag, committing to `main` directly, merging a PR, or publishing an image/release.
- **Honor the run's args:** waiving review is **two decisions**, and mango takes them separately —
  `--no-reviewer` waives the rule-book reviewer (~108k/round), `--no-challenger` waives the
  ticket-blind challenger (~58k). **"with skipped review" means `--no-reviewer` only**; the review
  phase still runs and the challenger keeps its seat. Don't reintroduce a waived gate; still surface
  each ✋ gate in-conversation so the maintainer can interject, but proceed on the standing approval
  rather than waiting.

## What has shipped
**Phase 1** (closed 2026-09-27, plan §15): core, onboarding and four adapters — **24 tools**, plus the
console scripts in `pyproject.toml`; C#/.NET is the only adapter left. **Phase 2 so far:** release
0.2.0 ([`CHANGELOG.md`](CHANGELOG.md)) and the Claude Code plugin (`contrib/claude-code/plugin/`).
Open work: [`docs/BACKLOG.md`](docs/BACKLOG.md).
