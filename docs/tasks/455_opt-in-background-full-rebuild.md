---
id: 455
slug: opt-in-background-full-rebuild
title: "A repo that opted in rebuilds in the background on a contract change, instead of waiting on `rebuild required`"
phase: 2
milestone: Freshness
status: todo
depends_on: [453, 356]
---

## Why this exists

Epic 451. `code-atlas-refresh` never runs a full rebuild (`hooks/refresh.py:67-69`, 053), and the
anchors' session hook stops at `incomplete` ("a human's call"). After an upgrade the index stays on
`rebuild required` until someone types the command; this repo shows it today (index v20, server v21).
The reason was a killed build leaving no index; 356 now builds behind a shadow and keeps serving the
old one, so that risk is gone.

## Scope

1. `code-atlas-setup` asks once (default no) whether this repo allows a background full rebuild;
   the answer is recorded under `.code-atlas/`.
2. Where allowed, SessionStart, on a contract change or `incomplete`, starts a detached
   (`setsid`, outside the hook's timeout) `code-atlas-build --full` under the write lock and says so
   in one line; a build already running starts nothing.
3. Where not allowed, the state line is unchanged.
4. PLAN §19 records the reversal of 202 / 053 for opted-in repos.

## Acceptance criteria

- **AC1:** an index stamped with an older contract, consent recorded → one detached full build
  starts; the old index answers until it publishes.
- **AC2:** no consent → no build, byte-identical state line.
- **AC3:** two session starts in a row start one build.
- **AC4:** killing the hook process does not kill the build.
