---
id: 241
slug: the-suite-count-agents-md-pins-drifted-behind-the-suite
title: 'AGENTS.md calls itself "the one place these numbers are kept" for the suite count, and the number it keeps is 14 tests behind the suite'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [237, 238, 239, 240]
---

## Why this exists

AGENTS.md pins the expected suite count and declares itself the single place that holds it, so an
agent that runs `pytest` and gets a different number has to decide which side is wrong. On
2026-09-11 it read **3,277 passed / 3 skipped** while `main` at `b098373` produced **3,291 / 3** —
fourteen tests of drift accumulated across 237, 238, 239 and 240, none of which updated the line.

The failure mode is not the stale digit. It is that the drift points the wrong way: a session that
trusts the doc reads `3,291 > 3,277` as *tests appeared from nowhere*, and one that distrusts it
gets no value from a line whose whole purpose is to be trusted. Both readings cost a re-measure the
line existed to prevent.

## What changed

- Both counts re-measured on `main` at `b098373` and written back: bare `pytest` **3,291 / 3**,
  `scripts/docker-test.sh` **3,290 / 4**. Verification date moved to 2026-09-11.
A clause naming the direction of the error (a run *above* the pin is a stale doc, not a regression)
was drafted and then dropped: AGENTS.md sits at its 2,850-token budget, and R7.6 prunes rather than
raises. It is recorded here instead, which is where R7.6 says it belongs.

No code change; no test change; the skip composition is unchanged (Windows lock arm ×3, plus
`test_runtime_image_reports_server_build` in-image only).

## Evidence

```
$ git log --oneline -1
b098373 fix(239): Column search hits name their FK targets from REFERENCES edges (#310)

$ pytest -q
3291 passed, 3 skipped in 276.01s

$ scripts/docker-test.sh
3290 passed, 4 skipped in 286.54s
```

Host: Linux, `php` · `composer` · `node` · `docker` on PATH.

## Residue

The line has now drifted at least once per four tickets and nothing enforces it — the same shape
`tests/test_ci_and_gate_agree.py` was written to close for `ci.yml`/`gate.sh`. A guard asserting the
pinned count equals the collected count is possible but self-referential: adding it moves the number
it asserts, and every test-adding PR then edits a tier-1 doc. Left unbuilt deliberately, recorded
here so the next drift does not re-derive the trade-off.

## Token usage

| Phase | Tokens |
|---|---|
| Total | ~14k (main-loop only; no agent dispatch) |
