---
id: 430
slug: limits-and-containment
title: "The indexed repo cannot exhaust code-atlas or reach past it — every read, regex, reply and subprocess is bounded, every path contained, and adapters get a scrubbed environment"
phase: 2
milestone: Trust
status: todo
depends_on: [423]
---

## Why this exists

Containment covers most paths but not all: a configured stub root's files are walked unchecked
(342), read-through repair re-parses a file swapped for a link out (375), and the project file's
`host_root` / `container_root` are ungated (341). Resource use is bounded unevenly: no per-file
size cap before a parser, no cap on an adapter's reply line, repo-supplied regexes (architecture
rules) run without a limit, the adapter preflight has no timeout, and caps read from the project
file are not clamped. Adapter subprocesses inherit the whole environment, API keys and tracker
tokens included. git still reads the indexed repo's environment-driven config (`GIT_*` variables
the user's shell may carry).

## Acceptance

One fixture per limit, each seen failing first (R6.5):

1. **Size and reply caps:** a file above `CA_MAX_FILE_BYTES` (default named) is skipped and
   counted, never truncated silently; an adapter reply line above a cap fails that file loudly.
2. **Regex limit:** a repo-supplied pattern is length- and feature-limited (or run with a timeout
   engine); a catastrophic pattern is refused with the rule named.
3. **Timeouts and clamps:** every subprocess (adapter preflight included) has a timeout; every cap
   read from `.code-atlas.toml` is clamped to a ceiling written in the code.
4. **Containment complete:** stub-root files contained (`followlinks=False`, `resolves_inside`);
   read-through repair refuses a file that now resolves outside (closes 375's residual);
   `host_root` / `container_root` gated like `adapter_cmd`; reads that cross the trust line use
   `O_NOFOLLOW`.
5. **Scrubbed environments:** adapters run with an allow-listed environment (no `*_TOKEN`,
   `*_KEY`, `ANTHROPIC_*`, `GH_*`); git runs with `GIT_*` variables other than the ones
   code-atlas sets removed.
6. `generate_onboarding`'s `.code-atlas/onboarding/` cache joins 420's modes (`0700`/`0600`),
   closing 420's residual.
7. The BACKLOG follow-ups these close (341, 342/375 symlink residuals, parser-OOM cap, 420's
   cache modes) leave the list in the same commit.

## Call sites

`code_atlas/adapter.py`, `code_atlas/indexer.py`, `code_atlas/config.py`,
`code_atlas/containment.py`, `code_atlas/gitutil.py`, stub-root collection, read-through repair,
architecture-rule loading, `onboarding_llm/cache.py`; standard rows SEC-IN-01, 03, 09..13.
