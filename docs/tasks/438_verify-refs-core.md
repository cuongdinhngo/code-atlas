---
id: 438
slug: verify-refs-core
title: "`verify_refs`: find which references in agent docs no longer resolve — extraction, classes, states, CLI"
phase: 2
milestone: "0.11 Verify & Compute"
status: todo
depends_on: [384, 429, 430]
---

## Why this exists

Roadmap R1 (0.11). An agent loads `CLAUDE.md`, skills and docs as authoritative, and nothing checks
them against the code. arXiv 2610.30571 ("Stale Code Inconsistencies in Coding Agents") found agents
followed a stale instruction file in **90.1%** of convention choices, and Claude Code noticed the
conflict in 79 of 80 runs and still followed the file. On the anchor (survey 2026-11-07, counts
only): 177 agent-facing knowledge files hold 6,003 code references; **196 referenced paths existed
and are gone, 21 methods are missing on live classes, ~3.6% verifiably stale**.

The positioning: code-atlas tells the agent which of the things it was told are still true. This
ticket is the finder; 439 adds the fix (patches) and the surfaces an agent sees.

## Scope

1. **Corpus and priority classes**, default globs overridable by non-command `.code-atlas.toml`
   keys (430): `instruction` (`CLAUDE.md`, `AGENTS.md`, `.claude/rules/**`, `.claude/skills/**`,
   `.cursor/rules/**`, `.github/copilot-instructions.md`), `memory` (configured path), `reference`
   (`docs/**/*.md`, wiki folders), `archive` (maintainer globs — report-only, excluded from the
   counts 439's SessionStart line uses). Default for any corpus is maintained (roadmap §4.6).
2. **Extraction, language-free core** (R1.1). Candidates: file paths, qualified symbols, bare names in
   code spans, SQL object names in code spans, commands (counted, never executed). Symbol shapes are
   **adapter-declared reference shapes** (PHP `::`, Python dotted, SQL `schema.object`) carried by the
   handshake — a contract addition, so R3 applies. Code spans and fences are strong candidates; a
   prose word counts only on an exact indexed match.
3. **Exactly one state per reference, each with a `reason`:** `ok`, `moved` (successor via git
   rename detection `-M` or a `body_hash` match — 384, 437), `gone` (`last_seen_rev`, day-granularity
   date), `never_existed` (not in the index nor any branch's history), `ambiguous` (capped candidate
   list), `unknown` (never folded into `ok`, R5.6).
4. **Output is reference strings, never surrounding prose** (429): file, line, class, surrounding
   *kind* (list item, table cell, prose); doc-derived fields listed in `untrusted_fields`.
5. **CLI:** `code-atlas query --verify-refs [globs…] [--class …] [--format json|md]
   [--fail-on moved,gone]`, exit 0 by default; `--fail-on` is opt-in for pre-commit.
6. code-atlas **never writes** to the repo; git is read through `gitutil.py`.

## Acceptance

1. A fixture repo with known `ok`, `moved` (a rename and a body move), `gone`, `never_existed` and
   `ambiguous` references: each state asserted exactly, with its reason.
2. **429:** a doc holding instruction-like text yields reference rows only — no prose in the payload.
3. **430:** a toml cannot add a command through any key this ticket adds.
4. An `unknown` row is counted as unknown in every summary, never as `ok`.
5. `total_count` / `truncated` are truthful; an empty corpus explains itself (no file matched the
   globs ≠ every reference resolved).
6. Anchor: a full run over the 177 files in ≤ 30 s warm, reported privacy-safe (rules in 442).
