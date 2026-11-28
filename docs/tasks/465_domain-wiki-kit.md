---
id: 465
slug: domain-wiki-kit
title: "Epic: a domain wiki kit — any repo with a ticket tracker grows a cited wiki on the graph"
phase: 2
milestone: "Domain wiki kit"
status: todo
depends_on: []
---

> **Status: todo — plan only.** Nothing below is built. Each step becomes its own ticket, numbered
> from the next free `NNN` when it is opened, and runs through `/mango:solve`.

## Why this exists

The PHP anchor built a domain wiki by hand over 17 days (2026-10-10 → 10-26): 1,378 tickets
harvested, 1,101 extracted into 2,690 facts, 35 module pages, tickets attached to the graph as
records (407). It used every graph feature it needed (382, 384, 385, 396, 407, 411–416), so the core
needs nothing new. What did not carry over is the pipeline: about 3,000 lines of scripts written for
that one repo, which the next repo would have to write again.

What the anchor measured, and what this kit keeps:
- **Only checkable output stayed right.** Quoted ticket words, code printed from the file and lists
  generated from the graph were exact. Free-text summaries misled in 22 % of answers at best.
- **Extraction with a verbatim quote per fact is reliable** (44 of 1,158 facts changed in review,
  none unsupported) and costs about 7k tokens per ticket.
- **The benchmark loop cost more than the wiki** (15.8M of 35.6M tokens) and ended without meeting its
  bars. It is not repeated; a pilot is judged once, by a person, against a stop rule written first.
- **Security tickets need a hard gate.** A "keep them off pages" habit failed before lint refused them.
- **A developer reads the explanation first.** The evidence-first layout was rejected as unreadable.

## Decisions

| # | Decision | Why |
|---|---|---|
| D1 | The kit is a new top-level package `wiki_kit/`, beside `onboarding_llm/` and outside `code_atlas/`; the LLM steps are plugin skills in `contrib/claude-code/plugin/skills/` | One install. Knowledge stays in the consumer repo; the kit is a consumer of Pillar 1, like the onboarding map. Recorded in PLAN §1 and §19 by K1 |
| D2 | Python | Same CI and the same R1.1 / R2.4 / R4.1 gates; one `packages.find` entry and one console script |
| D3 | The pilot repo is chosen in K12 by `fit`, preferring a public repo whose PRs link issues | No private data reaches this repo; `fit` counts before a token is spent |
| D4 | Answer modes: Browse (no tokens), Question and Ticket. Explanation first with `file:line` and ticket links, then *Before you change it*, then the evidence collapsed | The layout a developer accepted; the evidence-first one was rejected |
| D5 | CLI `code-atlas-wiki`; skills `/wiki`, `/wiki-init`, `/wiki-extract`, `/wiki-compile`, `/wiki-lint` | Matches the `code-atlas-*` console scripts |
| D6 | GitHub adapter first, Jira second, both behind one shared schema test | GitHub is testable on public data and serves the pilot |
| D7 | Proven on synthetic fixtures only; no parity run against the anchor | The anchor is out of scope; R2.4 keeps its data out of this repo |

## Steps (each becomes a ticket)

| Step | Ticket | Done when |
|---|---|---|
| K1 | **Spec and decision record:** PLAN §1 line + §19 entry; `docs/wiki-standard/` (layout, ticket/fragment/record schemas, tiers A–D, page rules, answer format, exclusion gate) and `wiki.config.schema.json` | The maintainer approves it; the R2.4 sweep is green on it |
| K2 | **Kit skeleton:** `wiki_kit/`, `code-atlas-wiki`, config loader + schema check, monthly JSONL shards; R4.1 and R2.4 gates extended to `wiki_kit/` | `--help` lists commands; a bad config fails loud; a shard round-trips byte-identical |
| K3 | **Tracker adapter: GitHub** (Issues + PRs through `gh`, read-only) | Synthetic raw pages → the ticket schema; no write verb in the adapter |
| K4 | **Tracker adapter: Jira** (REST GET only, ADF → text, changelog) | Passes K3's shared schema test |
| K5 | **anchor + trust:** commits/PRs by key pattern, files/symbols/tables through the batch query (382), tiers A–D from config signals | Fixtures cover every tier; the LLM writes none of these fields |
| K6 | **records export (407) + exclusion gate** (a gitignored hidden-keys file) | An excluded key reaches no record, page, answer, log or count; a missing exclusion file fails loud |
| K7 | **stale + lint + capabilities:** strong/weak flags from fingerprints (384); lint on citations, verbatim quotes, excluded keys, `--retest A..B`, coverage; `capabilities.toml` writer | Lint fails on an uncited unit, a quote not in its ticket, an excluded key |
| K8 | **Read side:** `show`, `retrieve`, `before-change` (from `impact` + records), `check-answer`, `render` | A fixture question renders explanation → before-change → collapsed evidence; `check-answer` refuses an unresolved ref |
| K9 | **`fit` + `weekly`** | `fit` prints ticket count, % linked to a commit, tier mix and a token quote with +20 % |
| K10 | **Plugin skills** (the five in D5) | R2.4 green on the skills; `/wiki-init` writes a config and runs `fit` |
| K11 | **Docs + release:** README section, CHANGELOG, plugin version | Release check green |
| K12 | **Pilot** on the repo `fit` picks, in that repo's session | Zero repo-specific code added to the kit; spend within +20 % of the quote; lint 0 errors |
| K13 | **One human check:** 10 real questions, read by a person | ≥ 8 of 10 readable and useful, no wrong item in *Before you change it*; no second run |

Order: K1 first. K3 and K4 run in parallel. K8 needs K5 and K6. K10 comes after K8 and K9.
**K12 stop rule, written now:** fewer than 100 tickets linked to a commit, or tier A+B under 30 %,
and the repo is not a fit; pick another and spend nothing.

## Out of scope

- Any change to the anchor project: no read of its scripts to port, no PR there.
- An LLM, prompt or model id in `code_atlas/` or `wiki_kit/` (R4.1); only skills write facts and prose.
- Tracker writes. Every adapter is read-only.
- A benchmark or judge loop, and the v11 `--deep` mode.

## Budget

K1–K11 about 3–4M tokens with the +20 % margin. K12 is quoted by `fit` before its go; K13 about
0.8M. Each token-costing step waits for the maintainer's go.

## Done when

K1–K13 are done: the pilot repo's wiki was built from config and skills alone, and the human check
met its stop rule.
