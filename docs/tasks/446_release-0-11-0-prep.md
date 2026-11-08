---
id: 446
slug: release-0-11-0-prep
title: "0.11.0 prepared: contract 21, the version, the CHANGELOG — and the §19 entry to ratify"
phase: 2
milestone: "0.11 Verify & Compute"
status: in-progress
depends_on: [443, 444, 445]
---

## Why this exists

Pre-flight A8–A9. 437 and 438 deferred the contract bump to the 0.11 release, so a pre-437 index read
`current` against 0.11 code. R4 needs every run on one code and index generation.

## Scope (prepared, not released)

1. `CONTRACT_VERSION` 21; every adapter handshake, PLAN and the PHP README say 21. A pre-0.11 index now
   leads `get_index_status` with `rebuild required` and an incremental build refuses (contract check).
2. Version 0.11.0 in `pyproject.toml`, `uv.lock`, the marketplace, the plugin and the generated hooks;
   README and AGENTS name 0.11.0. CHANGELOG `## 0.11.0 — 2026-11-08 · contract 21 · schema 9`, both
   upgrade flags set. `test_the_top_release_is_tagged` is a strict xfail until `v0.11.0` exists.
3. **Not done (maintainer):** set the date, merge, sign and push the tag.

## PLAN §19 — draft entry for the maintainer (not ratified)

**Decision — 0.11 Verify & Compute: the assumed decisions of 437–441 and the pre-flight (443–446).**
The task files hold 18 want-decisions marked ASSUMED (the state check said 20; the tables hold 18).

| # | Decision | Recommend | Why |
|---|---|---|---|
| 437 W1 | the core derives `definition_ordinal` from path globs, not the adapter | ratify | a repo's layout is no adapter's business (R2); globs are language-free (R1.1) |
| 437 W2 | the contract bump waits for the 0.11 release | ratify | one bump for 0.11; done in 446 |
| 438 W1 | `qualified` shapes join the handshake without their own bump | ratify | the same 0.11 bump |
| 438 W2 | a doc's path reads from the root, its folder, then a unique tracked ending | ratify | instruction `never_existed` 546 → 221 on the anchor |
| 439 W1 | MCP `format: patch` answers edits; the diff is the CLI's | ratify | a diff carries doc lines (429) |
| 439 W2 | archive rows are never patched | ratify | an archive records what was true then |
| 439 W3 | the session line is opt-in (`refs_session_line`) | ratify as amended | 443: it reads a stored summary, never scans |
| 439 W4 | a folder split two ways is `moved`, no patch | ratify | no single successor |
| 439 W5 | one shape per field (`successor` qname + `site`) | ratify | 429's frame |
| 440 W1 | +600 description / +1,100 surface per added tool | revert by default — see 445 | 434's caps cannot hold two more tools without cutting 2,161 chars from the 24 |
| 440 W2 | two proving templates (`no_referrer` too) | ratify | an absence needs a template to prove it |
| 440 W3 | a third level, `mention_unchecked` | ratify | R5.6: a cut grep is not "no mention" |
| 440 W4 | the authorizer also allows RECURSIVE and FTS's `data_version` read | ratify | the deadline interrupts a runaway CTE; FTS needs the read |
| 441 W1 | `untested_classes` reads the indexed `is_test` role | ratify | no new config key |
| 441 W2 | `variant_pairs` from params, else toml | ratify | the core matches patterns only |
| 441 W3 | `tier_mix` rows gain the language pair | ratify | 440 unreleased |
| 441 W4 | `calls_by_module` takes a qname GLOB or a kind | ratify | both shapes the roadmap names |
| 441 W5 | +130 surface for the template ids | revert by default — see 445 | as 440 W1 |
| 443 P1 | strength: links count as code for paths; a path git knows is strong anywhere | ratify | a link target is a deliberate path |
| 443 P2 | memory = the host's project memory folder unless `refs_memory` is set | ratify | SEC-IN-03: the host, never the repo, picks a host directory |
| 443 P3 | a missing member is `gone` only with git evidence; inherited is `ok` | ratify | 46 instruction rows were false `gone` |
| 443 P4 | export 1,800 s and stored summary 120 s of git history; MCP stays 12 s | ratify | instruction + memory alone need ~60 s on the anchor |
| 443 P5 | diff key `(class, file, ref)` with multiplicity, never the line | ratify | a reflowed doc is not a fix |
| 443 P6 | patches only for actionable rows | ratify | a weak bare-name move is not proven |
| 444 P1 | `multi_defined` = one (kind, qname); namespaces are not objects | ratify | 3,253 → the anchor's real redefinitions |
| 445 P1 | the allowance cut to the measured minimum (+300 / +2,170) until §19 decides | maintainer | revert needs a 24-tool trim ticket |

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|

Main loop unmeasured.
