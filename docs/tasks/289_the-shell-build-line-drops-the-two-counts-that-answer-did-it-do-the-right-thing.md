---
id: 289
slug: the-shell-build-line-drops-the-two-counts-that-answer-did-it-do-the-right-thing
title: '`BuildReport` carries `removed`, `parsed`, `failed` and `fingerprint_skipped`, and the MCP tool ships all of them under `wrote` — but the shell command the runbook sends every agent to prints only files, nodes and edges, so an incremental run that deleted 1,212 files looks identical to one that indexed fewer, and the reader is left deciding whether to trust a count the payload already holds'
phase: 1.5b
milestone: Agent-fit
status: todo
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

## References
`code_atlas/cli.py:36-58`, `code_atlas/indexer.py:170-185,237,441`,
`code_atlas/tools/build_or_update_index.py:415-421`,
[201](201_a-forced-full-rebuild-is-silent-and-unroutable.md),
[177](177_a-long-build-is-indistinguishable-from-a-hang.md),
[051](051_build-report-edge-undercount.md).
Origin: field retro round 24 §6, 2026-09-15.
