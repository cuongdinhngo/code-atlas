---
id: 436
slug: query-broken-pipe
title: "`code-atlas query` reports a closed stdout pipe as an \"unreadable index\""
phase: 2
milestone: CLI
status: todo
depends_on: []
---

## Why this exists

Reproduced 2026-11-04 at `8c7f7a12`, three of three runs:

```
$ code-atlas query get_index_status --args '{}' | true
code-atlas query: unreadable index at …/.code-atlas/graph.db: BrokenPipeError: [Errno 32] Broken pipe
Exception ignored on flushing sys.stdout:
```

The index is fine; the reader closed the pipe. `code_atlas/query.py:386` catches every `Exception`
after the database opens and labels it "unreadable index", so a closed pipe sends the user to rebuild a
healthy index. The second line is the interpreter failing to flush stdout again at shutdown.

## Acceptance

1. A closed stdout ends `code-atlas query` quietly: no "unreadable index" line and no shutdown flush
   error. It exits with the conventional status, following Python's documented SIGPIPE guidance
   (point stdout at devnull before exit).
2. A real database error still names the unreadable index: a non-database file at `db_path` produces
   the message as today.
3. Tests: piping into a reader that closes early produces neither line; the non-database file case
   keeps its message.
