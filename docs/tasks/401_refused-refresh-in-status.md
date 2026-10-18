---
id: 401
slug: refused-refresh-in-status
title: "A refresh the hook skipped for an unusable adapter looks like a working refresh"
phase: 2
milestone: Freshness
status: todo
depends_on: [355, 381]
---

## Why this exists

From the anchor project's Round-3 feedback ("a broken setup looks exactly like a working one"). It is
also seen on this maintainer's machine: `.code-atlas/refresh.log` repeats `refresh skipped: no_usable_adapter`
while the session shows nothing. On `main` the refusal goes only to stderr and the log
(`hooks/refresh.py:52-56`). `get_index_status` predicts a refusal for `coverage_loss` alone
(`get_index_status.py:302-309`, 355).

## Scope

1. The refresh records its last outcome (skipped / refused, with the reason and time) where `get_index_status`
   reads it, and the status names it with the fix, as 381's skew line does at session start.

## Acceptance criteria

- **AC1:** with an adapter that fails its handshake, a hook refresh, then `get_index_status`, names
  `no_usable_adapter` and the time.
- **AC2:** the next successful refresh clears it.
