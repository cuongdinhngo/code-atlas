---
id: 383
slug: re-run-a-signed-claim
title: 'A signed claim says a reviewer can re-run it, but nothing re-runs one'
phase: 2
milestone: Trust
status: deferred
depends_on: [382]
---

**Deferred 2026-10-10 — evidence gate:** the first consumer that motivated this (knowledge pages citing code) anchors to symbols and checks them with `impact`, not with pasted claims. Reopen when a consumer actually pastes signed claims and needs them re-checked.

## Why this exists

`sign: true` on `impact`, `impact_modules`, `find_callers`, `find_references` and
`get_index_status` adds a one-line `claim` (`docs/design/impact-and-claims.md` §"Signing a claim"):

```
code-atlas/1 tool=impact subject="app/Http/A.php,app/B.php,+2" question=blast-radius answer=25 tier=RESOLVED seeds=4 seeds_dropped=0 ... rev=a1b2c3d ref=main index=current ...
```

The design's own test of a claim is that it can be re-run; "a claim that cannot be re-run is
decoration". Today re-running one means a human reading the line, rebuilding the tool call by hand
and comparing numbers by eye.

Claims are pasted into more than PR bodies: a consuming repo's own documentation — design notes,
knowledge pages, runbooks — cites code the same way, and goes stale silently when the code moves.
A re-run that answers **holds / changed / unverifiable** turns every pasted claim into a check the
consuming repo can run in its own lint. code-atlas verifies the line; it never stores or reads the
page around it beyond finding claim lines.

The subject is truncated in the line (`+2`), so a re-run needs the full subject, which the line
does not carry today.

## Scope

1. A claim line carries enough to rebuild its call: either the full subject, or a short digest of
   it plus the rule that a digest-only claim is `unverifiable` without the original subject.
   Decide at design; the line stays one line.
2. `code-atlas query --verify-claim '<line>'` (on 382's CLI) re-runs the call at the current index
   and returns `{status: holds | changed | unverifiable, then: {...}, now: {...}, rev_then, rev_now}`.
   `changed` names each key that moved (`answer`, `tier`, `seeds_dropped`, …).
3. `--verify-claims <file>` scans a text file for claim lines and verifies each.

## Assumptions to prove at design

- Whether verification belongs on the CLI only or also as an MCP tool. The tool count is pinned at
  24 by tests, so a new tool needs its own justification; the default is CLI-only.
- A claim signed by an older `code-atlas/N` format version either verifies or answers
  `unverifiable` with the version named — never a false `holds`.

## Acceptance criteria

- **AC1:** a claim signed at rev A re-verified at rev A answers `holds` for each of the five tools.
- **AC2:** a fixture change that adds a caller makes the `find_callers` claim answer `changed` with
  `answer` named as the moved key.
- **AC3:** a claim whose subject no longer resolves answers `changed` with the tool's `reason`,
  not `holds` and not a crash.
- **AC4:** `--verify-claims` on a markdown file with three claims and prose around them verifies
  exactly the three.
