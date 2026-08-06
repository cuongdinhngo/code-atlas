---
id: 044
slug: onboarding-runbook
title: Onboarding runbook — installing code-atlas on a large legacy repo
phase: 1.5b
milestone: Adoption
status: done
depends_on: [014, 039, 043]
---

## Goal
Write down what a first install on a **large, legacy, someone-else's** repo actually costs and where it
goes wrong, so the next operator does not rediscover it. The README's three-command path is right for a
small repo and silent about everything that only appears at ~19k files: a twenty-minute first build, a
`.gitignore` negation smuggling a vendored tree into the index, and one knob that decides whether the
database is 1 GB or 2 GB. Closes the long-standing "indexing-hygiene doc note" follow-up in
[`BACKLOG.md`](../BACKLOG.md) and records two design findings the trial surfaced.

## Scope / Deliverables
- **`docs/runbooks/onboarding-a-repo.md`** — eight sections plus a checklist: verify the grammar
  version (not `php -v`) before choosing Docker; build once outside the MCP client and measure it;
  triage parse failures into "bundled library" vs "invalid PHP"; the four knobs that matter at scale;
  ignore hygiene including the `.gitignore`-negation trap; register the MCP server at local scope
  without touching a committed `.mcp.json`; verify every tool with its expected latency; read the
  health numbers honestly.
- **README pointer** from the Install section, so the runbook is findable from the entry point.
- **Two new BACKLOG follow-ups** for what the trial exposed as design smells rather than doc gaps:
  `max_results` doubling as the resolver's fan-out cap, and the reachability payload size at
  `detail_level="standard"`.

## Constraints
- **No repo-specific identifiers.** The validation sample is a private monorepo and the repo was
  deliberately anonymised for public release (commit `a3879cc`). Measurements are attributed to "one
  large private PHP monorepo" with its shape described, never its name or paths — same convention as
  PLAN §19 / §6.1.
- **Descriptive, not normative.** The runbook records what the software does and what was measured; it
  introduces no rule and changes no behaviour. Anything that should become a rule belongs in
  ENGINEERING_RULES, and anything that should become code belongs in a ticket.
- Every number in it is a measurement taken during the trial, cited with the `file:line` that explains
  the mechanism — no estimates presented as observations.

## Acceptance criteria
- The runbook exists, is linked from the README Install section, and names no private repo, path, or
  organisation.
- Each quantitative claim in it traces to a measurement taken on the trial repo, and each mechanism
  claim to a `file:line` in this checkout.
- The "indexing-hygiene doc note" follow-up in `BACKLOG.md` is marked captured and points at the
  runbook section that captures it.
- `pytest` and `ruff` stay green (`test_backlog_bookkeeping.py` in particular, which gates the
  status/token bookkeeping this ticket has to satisfy).

## References
Measured during the trial: full build 18,867 files / 1,008 s / 99.85 % `parsed_ok` / 1,133 MB at
`max_results = 10`, against 21,425 files / 1,220 s / 2,115 MB at the default 50. Fan-out mechanism:
`indexer.py:118` → `resolver.py:129`. Ignore precedence: `ignore.py:57-65`. Tracked-only collection:
`indexer.py:264`. Root resolution for the MCP wrapper: `main.py:104`. Stub-root overlap guard:
`indexer.py:329`. Parser grammar selection: `adapters/php/src/Parser.php:24`.
