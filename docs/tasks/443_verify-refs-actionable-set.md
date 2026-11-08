---
id: 443
slug: verify-refs-actionable-set
title: "verify_refs counts the actionable set: strong moved/gone rows, a full export, a stored session line"
phase: 2
milestone: "0.11 Verify & Compute"
status: in-progress
depends_on: [438, 439]
---

## Why this exists

The 0.11 state check (2026-11-08, `~/code-atlas-review/state-check-0.11.md`) found that R4 would fail on
noise, not on the idea: on the anchor `verify_refs` read 78,985 references and called ~42% of them not
`ok`, against ~3.6% real staleness in the survey. The default answer was ~85k tokens, the session line
took 10.7 s, the CLI could not save a baseline (1,000-row cap), and the instruction class had no patch.
Pre-flight A1–A5 (roadmap R1, one 0.11 generation).

## Scope

1. **Noise, measured** (anchor, counts only): of 22,448 `ambiguous`, 18,301 are bare names in code
   spans; of 5,045 `never_existed`, 3,083 are slash words with no suffix and 1,664 paths no branch held.
2. **`strength` and `actionable`** per row, language-free: strong = a path git or the tree knows, a
   path with a folder and a suffix, or an adapter-shaped symbol, written as code; actionable = moved or
   gone, strong, not archive. `never_existed` and `ambiguous` are never actionable.
3. **Surfaces count the actionable set only**: the default MCP answer (counts per class and state, up to
   20 compact rows, instruction first), the session line, `--fail-on`; a reference doc's weak rows leave
   every summary unless `strength` asks.
4. **Memory by default**: the host's project memory folder (SEC-IN-03: the host chooses it); its rows
   are edits, never a diff.
5. **`--format jsonl`** streams every row uncapped, keyed `(class, file, ref)`; **`--refs-diff`** counts
   fixed / new / unchanged actionable rows per class.
6. **Instruction rows** (A3): a member its class does not declare is `ok` through an ancestor, `moved`
   by body, `gone` only with git evidence, else `unknown`; gone paths name `nearest_existing`; instruction
   files resolve first. Raising git's rename limit changed nothing on the anchor (5,320 renames either way).
7. **Session line** reads counts a build/refresh stored with `refs_session_line`; a moved index or edited
   docs say so; it never scans.

## Acceptance

1. Fixtures: strong vs weak, actionable vs not (`tests/test_verify_refs_actionable.py`).
2. Export row count == `total_count`; the diff helper counts actionable rows only.
3. Default answer ≤ 6,000 chars on the anchor; `total_count` / `truncated` truthful; 429 fields kept.
4. Session line p95 ≤ 1 s on the anchor; a test proves the session path never scans.
5. Instruction `moved` / `gone` before and after, reported.

## Result (anchor scratch copy, counts only)

Filled by the pre-flight report, `~/code-atlas-review/preflight-0.11.md`.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|

Main loop unmeasured.
