---
id: 449
slug: read-symbol-pattern
title: "`read_symbol` takes a `pattern` and returns only the matching lines of a long body"
phase: 2
milestone: "Round-3 field gaps"
status: todo
depends_on: []
---

## Why this exists

Round-3 field feedback: a 300–670-line body is either elided or returned whole, and the question
was "where inside this method is X". Agents then fell back to `Read` with an offset, or to a guarded
`grep`, costing a round trip (asked for as `grep_in_symbol` / `pattern`, and as "a search string
inside a method"). `read_symbol` today takes `line_start` / `line_end` / `max_lines` only.

## Scope

1. A `pattern` parameter: a literal substring by default, case-insensitive. Regex only with
   `pattern_regex=true`, under the rules-file regex safety check (430: length, no backreference, no
   nested repeat).
2. The answer keeps the symbol header and returns each matching line with `context` lines around it
   (default 2, max 10), merged where they overlap, each with its absolute line number. It reports
   `pattern_matches` and, past a cap of 50, `pattern_truncated`.
3. No match is `pattern_matches: 0` with the symbol's span, so a caller knows the body was searched.
4. Tool surface: one parameter added — update `tool_manifest.json`, `docs/TOOLS.md` and the
   description budget.

## Acceptance

- On a fixture method of 400 lines, `pattern="needle"` returns the matching lines plus context, not
  the body; tokens are reported against the whole-body answer.
- A refused regex names the rule it broke; a closed schema still refuses an unknown argument.
