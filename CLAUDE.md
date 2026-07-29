# CLAUDE.md — code-atlas

Guidance for AI coding agents working in this repo. This file is the always-loaded orientation; the docs
below hold the authoritative detail. **If anything here conflicts with them, they win — fix this file.**

**Read these before non-trivial work** (they govern every session):
- [`docs/PLAN.md`](docs/PLAN.md) — authoritative design (§-refs below point here).
- [`docs/ENGINEERING_RULES.md`](docs/ENGINEERING_RULES.md) — binding *how we build* rules (R1.1…). The pre-PR self-check at the bottom is your gate.
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

## Where things live
- Core: `code_atlas/` (`main.py` FastMCP, `config.py`, `contract.py`, `adapter.py`, `store.py`, `indexer.py`, `resolver.py`, `tools/`).
- Adapters: `adapters/<lang>/`, each self-contained and launched via `CA_<LANG>_CMD` (PHP first).
- Tests: `tests/contract/` — the conformance suite every adapter must pass. Full layout + naming in CONVENTION.md.

## Ship discipline (plan §15)
M0 spike → M1 full build → M2 resolver+contract tests → **M3 search/read/outline = first daily release (task 014)** → M4 scale → M5 incremental → M6 impact. Then adapters #2–#4, then onboarding.
