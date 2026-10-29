---
id: 422
slug: release-0-9-1
title: "Release 0.9.1 — the security fixes 419–421, published with GHSA-66g7-7jr3-j5rc"
phase: 2
milestone: Release
status: done
depends_on: [418, 419, 420, 421]
---

## Why this exists

419–421 fix GHSA-66g7-7jr3-j5rc and were built in the advisory's private fork. A fix reaches users
only as a tagged release, and the advisory names that release as its patched version.

## Acceptance

1. `pyproject.toml`, the plugin, the marketplace and the hooks name 0.9.1; contract 20 and schema 9
   are unchanged, so the entry flags neither a rebuild nor an adapter update.
2. CHANGELOG's top release is `0.9.1 · contract 20 · schema 9`, with a *Security* section naming
   the advisory and the one upgrade step (untrack a committed index); `test_release_discipline` is
   green, the tag test a strict xfail until `v0.9.1` is pushed.
3. Merged through the advisory, `v0.9.1` tagged on the merge, the advisory published with patched
   version 0.9.1 and a CVE requested.

## Resolution

- Cut in the fork on the stacked branch, untagged, as 417 was. Gate and Docker are run on the fork,
  where Actions never run; the merge, the tag and the publication are the maintainer's.
