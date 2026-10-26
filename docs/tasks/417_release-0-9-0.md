---
id: 417
slug: release-0-9-0
title: "Release 0.9.0 — contract 20 for 411–416"
phase: 2
milestone: Release
status: done
depends_on: [411, 412, 413, 414, 415, 416]
---

## Why this exists

The maintainer, 2026-10-25: 411–415 add fields to answers and store new rule-file blocks, yet
shipped with contract 19 and an empty *Unreleased*. An index built before 411 kept one handler per
route key and none of the new blocks, so a 0.9.0 server reading it would answer as if complete.

## Acceptance

1. `CONTRACT_VERSION` is 20, and every adapter's handshake says 20.
2. `pyproject.toml`, the plugin, the marketplace and the hooks name 0.9.0 and contract 20.
3. CHANGELOG's top release is `0.9.0 · contract 20 · schema 9`, flags the rebuild and the adapter
   update, and lists 411–416; `tests/test_release_discipline.py` is green.

## Resolution

- The release is cut untagged, as 381 E3 and 390 require: `test_the_top_release_is_tagged` is a
  strict xfail until the maintainer pushes `v0.9.0`. `v0.8.0` was never tagged either.
- TOOLS.md no longer says the route table "does not move" the contract.
