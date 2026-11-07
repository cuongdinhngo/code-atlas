---
id: 441
slug: compute-catalogue
title: "`compute`: the first eight templates, each with fixtures for its answer, caveat, empty and truncation"
phase: 2
milestone: "0.11 Verify & Compute"
status: todo
depends_on: [440, 437]
---

## Why this exists

Roadmap R3.4 (0.11). 440 ships the sandbox and the contract; this ships the questions the anchor's
survey found unanswerable or costly today (8 of 10), so the validation run (442) can measure whether
an agent reaches for `compute` unprompted.

## Scope

| Template | Question | Depends on |
|---|---|---|
| `unreferenced_objects` | Objects of kind K with no inbound edges from language L, split by evidence level | 440's absence split |
| `tier_mix` | Edge tier mix per edge kind × language pair | — |
| `calls_by_module` | Calls into a target set (qname or kind pattern), grouped by module | — |
| `untested_classes` | Classes with no edge from test files, per module | test-path config |
| `resolved_share` | RESOLVED share of CALLS per module | — |
| `includes_by_dir` | `include` / `require` counts per top directory | — |
| `multi_defined` | Objects defined more than once, with the live one | 437 |
| `variant_pairs` | Name-pattern pairs from config with one-sided use | config rule; the core only matches patterns |

Every pattern a template takes comes from params or a non-command toml key (430), never a repo's
names baked in (R2). No template branches on language (R1.1) — a language is a param value.

## Acceptance

1. Per template, fixture tests for: the answer, the caveat, an empty result with its reason, and
   truncation (`total_count` truthful when `truncated`).
2. `multi_defined` with no 437 order rule names that the live definition is unknown, never guesses.
3. Anchor (privacy rules in 442): p95 ≤ 3 s per template warm; the cold-cache timing recorded too.
