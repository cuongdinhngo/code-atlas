---
id: 382
slug: batch-query-from-a-shell
title: 'Every answer is reachable only through an MCP session; a script that needs a thousand answers has no way to ask'
phase: 2
milestone: Adoption
status: todo
depends_on: []
---

## Why this exists

The only shell entry point that touches the index is `code-atlas-build`
(`code_atlas/cli.py:110`, "Build or update this repo's code-atlas index from a shell"). Every
*question* goes through the MCP server, so it is asked by an LLM agent, one tool call at a time,
paying context for each payload.

Deterministic consumers need many answers and no model:

- a script in a consuming repo that anchors its own records (tickets, test docs, notes) to code —
  per record, `impact_modules` on the files a fix touched, `find_references` on the tables it names,
  `search_symbol` for the qnames it cites. A batch of a thousand such records is ordinary;
- CI checks that re-implement a graph question with `grep` because they cannot call the tool;
- re-running signed claims (383).

Routing those through an agent spends tokens on answers no model needs to read, and makes a
deterministic pipeline depend on a model. What the consumer stores, and where, stays in the
consuming repo; this ticket only gives it a way to ask.

## Scope

1. `code-atlas query <tool> --args '<json>'` prints the tool's payload as JSON — the **same payload**
   the MCP tool returns for the same arguments at the same revision.
2. `code-atlas query --batch <file.jsonl>`: one `{"tool": ..., "args": {...}}` per line in, one
   payload per line out, in order, over a single opened index (no per-line startup).
3. Exit status: `0` answered (including an honest empty with `reason`), non-zero only for a usage
   error or an unreadable index. An empty answer is not a failure.
4. Read-only: `build_or_update_index` and `generate_onboarding` are refused by `query` (they
   already have entry points with their own locking).

## Assumptions to prove at design

- The served tools can be invoked without the MCP transport (tool functions take plain args and
  return the payload dict). Decide whether `fit` counters (260) and the live token counter (379)
  count shell calls, and say so.
- One process can hold the index open for a batch without fighting the writer lock that git-hook
  refreshes take.

## Acceptance criteria

- **AC1:** for every read tool in `main.TOOL_NAMES`, a fixture shows `query` output equal to the
  MCP payload for the same args at the same rev (payload equality, not "similar").
- **AC2:** a 1,000-line batch over a fixture index runs in one process; its wall time is recorded
  in the task.
- **AC3:** an empty answer exits `0` and carries the same `reason` / `try_instead` the tool gives.
- **AC4:** the tool count (24) is unchanged — `query` is a CLI over existing tools, not a new tool.
