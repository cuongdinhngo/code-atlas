---
id: 005
slug: adapter-protocol
title: Adapter protocol & subprocess driver
phase: 1
milestone: Core
status: todo
depends_on: [002]
---

## Goal
Language-neutral driver for long-lived adapters over JSONL (§4.1, §4.3).

## Scope / Deliverables
- `adapter.py`: `LanguageAdapter` Protocol (`name`, `extensions`, `capabilities`, `start/parse/stop`).
- Subprocess driver: spawn adapter in `--server` mode, feed newline-delimited requests, read JSONL results, handle `ok:false` per file without breaking the stream.
- Extension→adapter lookup (**not** a registry yet — YAGNI until adapter #2).

## Acceptance criteria
- Driver survives a per-file parse error (returns error result, stream continues).
- One process boot amortized across many files; clean `stop()`.
- No `if language == …` branches; adapters resolved purely by extension.

## References
Plan §4.1, §4.3, §2 (OCP/DIP/YAGNI).
