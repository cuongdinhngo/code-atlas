---
id: 379
slug: live-estimated-tokens-saved
title: 'Tokens-to-answer is measured only in benchmarks; nothing counts it on the repo a user actually runs'
phase: 2
milestone: Adoption
status: todo
depends_on: [260]
---

## Why this exists

The product claim — tokens-to-answer against a grep + `Read` baseline — is measured only by
`scripts/tokens_to_answer.py` over fixtures and pinned samples. On a user's own repo nothing says
which tools save tokens and which only cost them (a miss pays its response for nothing).

context-mode shows live savings, but its baseline credits every byte it indexed as "saved" and
prices it at the output-token rate (its `src/server.ts:1036-1068`; idea only, ELv2) — an inflated
figure this project must not copy. 260's `fit` counters already wrap every served tool once
(`tools/fit.py:40`), store counts only in `meta`, survive shadow rebuilds and stay out of nav
payloads (`docs/design/fit.md`). A cost counter fits beside them.

**Measure-first:** the honest baseline is an estimate. This ticket ships only if design shows it
can be stated without being mistaken for the benchmark tiers.

## Scope

1. Per served call: response tokens (`estimate_tokens` over the serialised response) and a
   baseline = tokens of the distinct files the response cites, first 20 in payload order (the
   benchmark's cap, `tokens_to_answer.py:717-736`). Tools that cite no file are not eligible; a
   miss counts its response against a zero baseline.
2. Counts only, per tool, in `meta` beside the fit counts; no qname, path or session in a key.
3. Read through `get_index_status(verbose)` (which stays self-excluded), reset with the fit reset.
4. Every surface labels it "est. grep+Read baseline" and never as the fixture or sample tier.
5. **Not in scope:** dollars, model prices, a statusline. A statusline is a new host surface and
   a separate maintainer decision (`hooks/state.py:15`, R1.2/099).

## Assumptions to prove at design

- File size source: a `files.size_bytes` column (content-derived, deterministic, but a schema
  bump and a rebuild) vs `stat` at count time (cheap, but measures the working tree). Decide.
- The per-call serialisation cost on large payloads is acceptable; **UNVERIFIED** that FastMCP's
  bytes equal `json.dumps(sort_keys=True)`.

## Acceptance criteria

- **AC1:** on a fixture, one `read_symbol` records baseline = `ceil(file bytes / 4)` and response
  = `estimate_tokens` of the result; a second identical call exactly doubles both. Bytes, not the
  benchmark's decoded chars, is a stated approximation: equal for ASCII, higher otherwise.
- **AC2:** every nav payload is byte-identical with counting on and off; two
  `get_index_status(standard)` calls are byte-identical while the counters move.
- **AC3:** no `meta` key contains a fixture qname or path; the rows survive a shadow rebuild.
- **AC4:** the README and TOOLS.md state what the number is and is not, in one place each.
