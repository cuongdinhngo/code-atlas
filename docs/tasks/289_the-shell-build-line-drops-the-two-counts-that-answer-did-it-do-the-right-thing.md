---
id: 289
slug: the-shell-build-line-drops-the-two-counts-that-answer-did-it-do-the-right-thing
title: '`BuildReport` carries `removed`, `parsed`, `failed` and `fingerprint_skipped`, and the MCP tool ships all of them under `wrote` — but the shell command the runbook sends every agent to prints only files, nodes and edges, so an incremental run that deleted 1,212 files looks identical to one that indexed fewer, and the reader is left deciding whether to trust a count the payload already holds'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [177, 201, 051]
---

## Why this exists (field retro — the anchor repo, round 24 §6, 2026-09-15)

After an incremental rebuild the indexed file count dropped by over a thousand and parse failures more
than halved. Both are consistent with deletions in the commit range — and the session had no way to
confirm it from the build's own output:

> *"Consistent with deletions in the range, but the status payload gives no way to confirm that — a
> `files_added` / `files_removed` pair in the build result would have saved me having to decide
> whether to trust it."*

Half of that already exists. `BuildReport` fields are *what this run wrote* (`indexer.py:170-185`) and
include `removed`, `parsed`, `failed`, `stubs` and `fingerprint_skipped`; `build_or_update_index`
ships the dataclass whole (`asdict(report)`, `build_or_update_index.py:421`). The loss is at the shell,
where `exit_code` prints one line naming three of them:

```python
_say(f"{mode}: {files} file(s), {wrote.get('nodes', 0)} node(s), {wrote.get('edges', 0)} edge(s)")
```

(`cli.py:53-57`). That shell path is not a convenience: 201 made it *the* route for a large rebuild
because an MCP call cannot outlive its client, and AGENTS.md sends every session to it. So the
run that most needs the reconciliation prints the least of it, and `removed` — the number that
explains a shrinking index — is computed, returned by the tool, and dropped by the command.

`added` is the genuinely missing half: `_reconcile` (`indexer.py:237,441`) returns what went away, and
nothing counts what is newly present. Whether the pair is worth carrying, or whether `removed` beside
`parsed`/`failed` already answers the question, is the design call this ticket makes.

## Scope / Deliverables

- **The shell build line reports what the run actually did** — at minimum `removed` and `failed`
  beside the counts it already prints, so a shrinking index is explained rather than guessed at.
- **Decide `added` on evidence.** Either count newly-present files at reconcile and report the pair, or
  record in the ticket why `removed` + `parsed` is sufficient and close it there. Do not add a counter
  that no reader distinguishes from `files`.
- **One spelling.** The shell line names the same fields as the MCP payload; a reader must not have to
  learn two vocabularies for one build.

## Constraints

- R7.6 / 061: one line, not a report. The shell output is read by agents in a terminal; every field
  earns its place or stays in the payload.
- R4.2: counts are what the run wrote (051's contract), never what the graph holds.
- Cost: no extra pass over the tree. Anything reported comes from state `_reconcile` already has.
- `--status` (177) is unchanged; this is the completion line, not the progress line.

## Acceptance criteria

- An incremental run that removed files prints that count; one that removed none is unchanged.
- A run with parse failures prints that count.
- Field names in the shell line match the `wrote` payload's.
- Exit-code behaviour is unchanged (`OK` / `NOTHING_TO_DO` / `FAILED` / `BUSY_PEER`).
- The ticket records the `added` decision either way.


## Decision — `added` (HOW, cited)

**Do not add an `added` counter.** `_reconcile` already returns `removed`; a newly-present count
would need a second vocabulary beside `files` (what this run wrote) and the ticket forbids a counter
readers cannot distinguish from `files` (Scope bullet 2). `removed` + `failed` (printed when
non-zero) answers the field question — whether a shrinking index / fewer parse failures came from
deletions — without a new BuildReport field or an extra tree pass (Constraints: cost / R4.2).

## References
`code_atlas/cli.py:36-58`, `code_atlas/indexer.py:170-185,237,441`,
`code_atlas/tools/build_or_update_index.py:415-421`,
[201](201_a-forced-full-rebuild-is-silent-and-unroutable.md),
[177](177_a-long-build-is-indistinguishable-from-a-hang.md),
[051](051_build-report-edge-undercount.md).
Origin: field retro round 24 §6, 2026-09-15.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 289 — shell build line removed/failed (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket
- **Current phase:** finalise
- **Session status:** autorun — reviewer off; challenger CLEAN; gate pending

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: no added counter — cites Scope bullet 2 (do not add a counter indistinguishable from files) and Constraints (no extra pass; _reconcile already returns removed). Print removed/failed only when non-zero so zero stays byte-identical (AC1 / 061).

## Requirements matrix

`SECTIONS: 6 found (Why · Scope · Constraints · Acceptance · Decision · References) | 6 decomposed | ROWS: C=4 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | shell drops removed | print removed/failed when non-zero | D1 | AC1 | ✅ |
| C1 | Constraints | one line / 061 | omit zeros | D1 | AC1 | ✅ |
| C2 | Constraints | R4.2 wrote counts | use wrote.* only | D1 | AC3 | ✅ |
| C3 | Constraints | no extra pass | no BuildReport change | D1 | — | ✅ |
| C4 | Constraints | --status unchanged | only exit_code line | D1 | AC4 | ✅ |
| R1 | Scope | report what run did | removed + failed | D1 | AC1 | ✅ |
| R2 | Scope | decide added | recorded Decision section | D3 | AC5 | ✅ |
| R3 | Scope | one spelling | payload field names | D1 | AC3 | ✅ |
| AC1 | AC | removed prints / none unchanged | proving | D2 | proving | ✅ |
| AC2 | AC | failed prints | proving | D2 | proving | ✅ |
| AC3 | AC | names match wrote | proving | D2 | proving | ✅ |
| AC4 | AC | exit codes unchanged | proving | D2 | proving | ✅ |
| AC5 | AC | added decision recorded | Decision section | D3 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: cli.exit_code prints files/nodes/edges only; BuildReport already has removed/failed.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 2 applicable — 2 by change-type | 0 by recalled handle — 061 ✅ · R4.2 ✅`

Ran at 1e594d3fb7112222300b530eac12feb27645a8e3

```
$ .venv/bin/python -m pytest tests/test_build_cli.py -q --tb=no
......                                                                   [100%]
6 passed in 1.50s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: append removed/failed only when non-zero; no added field.
- Rejected: always print zeros (breaks AC1 unchanged); add BuildReport.added (indistinguishable from files).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_shell_build_line_removed_failed.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | exit_code line | cli.py | stderr completion line | 1/1 |
| D2 | proving | tests/test_shell_build_line_removed_failed.py | — | 1/1 |
| D3 | added decision | docs/tasks/289_*.md | ticket record | 1/1 |

## Phase 3 — Execute

**Branch:** feat/289-shell-build-line-removed-failed
**Axis 1:** cli · proving · ticket decision.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at 1e594d3fb7112222300b530eac12feb27645a8e3

```
$ .venv/bin/python -m pytest tests/test_shell_build_line_removed_failed.py tests/test_build_cli.py -q --tb=no
...........                                                              [100%]
11 passed in 1.67s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — CLEAN. agent a656efdb-e819-4ceb-ac50-79129f2d1785

Ran at 1e594d3fb7112222300b530eac12feb27645a8e3

```
$ .venv/bin/python -m pytest tests/test_shell_build_line_removed_failed.py tests/test_build_cli.py -q --tb=no
...........                                                              [100%]
11 passed in 1.67s
```

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_shell_build_line_removed_failed.py — 5 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN
PR: https://github.com/cuongdinhngo/code-atlas/pull/383

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
