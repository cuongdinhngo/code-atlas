---
id: 346
slug: signal-line-never-reaches-the-model
title: 'The read-time signal prints plain stdout, which Claude Code never shows the model'
phase: 2
milestone: Adoption
status: todo
depends_on: [099, 344]
---

## Why this exists

`code-atlas-signal` (099) exists to put one line inside a `Read` result. It prints that line as
plain stdout (`code_atlas/hooks/signal.py`, `main`: `print(line)`).

## Evidence (Claude Code 2.1.284, 2026-09-29, found by 345)

- A PostToolUse hook on `Read` that printed a marker as plain text: asked to quote any text a hook
  added, the model answered `NONE`.
- The same marker as `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": …}}`
  was quoted back verbatim.
- Until 344 the signal never fired at all (a `|`-joined `if` never matches). Since 344 it fires,
  and its line still does not reach the model.

## Scope

1. Emit the signal's line as `hookSpecificOutput.additionalContext` for the event it ran on
   (`PostToolUse` for `Read`, `PreToolUse` for `Write`), as `code-atlas-nudge` does (345).
2. Keep the 150-token cap and the silence rules unchanged.

## Acceptance criteria

- **AC1:** A test asserts the signal's stdout is that JSON shape, naming the event from the payload.
- **AC2:** A live `claude -p` session on an indexed repo quotes the signal's line after a `Read`.
- **AC3:** The `Write` (PreToolUse) path is proven the same way, or the ticket records why it could not be.
