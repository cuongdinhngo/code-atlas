---
id: 462
slug: help-prints-usage
title: "`code-atlas --help` prints usage instead of starting the MCP server"
phase: 2
milestone: "Field gaps — Python/TS consumer"
status: todo
depends_on: []
---

## Why this exists

Same field report as 456. `code-atlas --help` (and `-h`) starts the MCP stdio server and waits on stdin,
so there is no usage. An agent checking whether `verify_refs` can run in CI concluded it was
**MCP-only** and wrote that into the consumer's ADR. In fact `code-atlas query --verify-refs …
--fail-on moved,gone` exists, and only the README (`README.md:396`) says so. The CLI is the
part that makes a CI gate possible, and nothing on the command line shows it.

## Scope

1. `code-atlas --help` / `-h` prints usage and exits 0: the subcommands (`query`, …), the main
   `query` flags (`--verify-refs`, `--format`, `--fail-on`, `--refs-diff`), and one line saying that
   no arguments starts the MCP server.
2. `code-atlas query --help` lists every query flag (argparse's own help is enough).
3. No arguments → the MCP server, as today (hosts launch it that way).

## Acceptance

1. Test: `--help` exits 0 within 2 s with stdin closed, and its output contains `--verify-refs`.
2. Test: no arguments still serves MCP (the existing smoke test passes).
