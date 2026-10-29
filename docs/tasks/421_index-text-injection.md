---
id: 421
slug: index-text-injection
title: "Text read back from the index cannot add a log line or steer the agent — only checked names, enumerated values and numbers reach a log, the instructions or a hook"
phase: 2
milestone: Trust
status: todo
depends_on: [420]
---

## Why this exists

Internal security audit, 2026-10-27; advisory GHSA-66g7-7jr3-j5rc (private until 0.9.1).
Text code-atlas reads back from its own index files is written into a log and into what the agent
reads, unchecked. 420 refuses a tracked index where git can answer; where it cannot (the runtime
image) the files can still come from the repo, and a symbol name comes from the indexed code
either way (a quoted SQL identifier can hold a newline). So:

- **Log lines.** `hooks/nudge.py` writes each matched symbol's `name` and `kind`, from
  `store.stamped_symbol_shapes`, into `nudge.log` raw: a `\n` in a name forges log lines.
- **Instructions and hook context.** The `get_index_status` summary carries free text from the
  `refresh.refused` record (`reason`, `at`, `route`, `hint`, `detail`) and from a pending coverage
  loss (`lost_languages`, `reason`, `hint`). That summary is the MCP server's `instructions`
  (`instructions.py`) and the SessionStart `systemMessage` / `additionalContext` (`hooks/state.py`),
  so a planted record speaks to the agent as code-atlas.

## Acceptance

1. **Names and kinds are checked before the log.** A name or kind that is not one line of printable
   text, at most 256 characters, is not written; the line counts how many were dropped. One match
   writes at most one line.
2. **The refusal record is read as data, not text.** `reason` must be one of the refusal reasons
   code-atlas writes, else it reads `unknown`. `route` must be one of the routes code-atlas names,
   else it is dropped and the reason's own hint is used. `at` must be a timestamp in the format the
   hook writes, else it is dropped. A record's own `hint` is ignored: the hint comes from
   `REFRESH_HINTS`. `detail` stays in the payload, capped and stripped of control, bidi and ANSI
   characters, and never enters the summary.
3. **The coverage-loss clause** names only language ids code-atlas knows (the configured adapters),
   and its reason and hint come from code-atlas's own constants.
4. **The summary is bounded.** Whatever reaches `instructions`, `systemMessage` or
   `additionalContext` holds no control, bidi or ANSI character and no newline it did not put there
   itself, and stays under a fixed cap (name it; today's longest real summary sets it).
5. **Proving tests**, each seen failing on the pre-fix tree (R6.5):
   - a symbol named `"x\n<forged line>"` matched by a grep: `nudge.log` gains no forged line;
   - a `refresh.refused` record with `reason: "ignore previous instructions …"`, a foreign
     `route`, a `hint` and a multi-line `detail`: the instructions, the state hook's output and the
     summary show `unknown` and the code-atlas hint, and none of the planted text;
   - a coverage-loss record naming an unknown language with an ANSI sequence: it does not reach
     the summary.
6. **Guard test:** the summary builder takes record values only through the checked readers
   (one reader per record; an AST or grep guard like 419's).

Out of scope: tool answers that return indexed source text by design (`read_symbol`, search
results) — framing those as untrusted for the agent is Track B (429). Out of scope too: the
`contract.refused` record (`adapter_skew.read_refusals`), unless analysis finds its text reaches
the summary; then it joins AC2.

## Call sites

Log: `hooks/nudge.py` (`nudge`, the `rows` it appends), `store.stamped_symbol_shapes`.
Refusal record: `index_lock.read_refresh_refused`, `hooks/refresh.py` (`RECORDED_FIELDS`, the
writer), `tools/get_index_status.py` (`_attach_refresh_refused`, `_refresh_refused_clause`,
`REFRESH_HINTS`, `REFRESH_REASON_NAMED_BY`). Coverage loss: `get_index_status.py`
(`COVERAGE_LOSS_PENDING`, the summary's loss clause). Consumers: `instructions.py`,
`hooks/state.py` (`_fit`, the JSON it prints).
