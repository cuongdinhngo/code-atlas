---
id: 459
slug: verify-refs-memory-links-resolve-in-memory
title: "Links inside host memory resolve against the memory folder first"
phase: 2
milestone: "Field gaps — tiny-studio"
status: todo
depends_on: [443]
---

## Why this exists

Same field report as 456. Claude Code's memory index `<agent-memory>/MEMORY.md` links to its sibling
files: `[Title](language-en-work-vn-chat.md)`. All 6 links in tiny-studio's index come back
`never_existed` / `no_branch_ever_held_it`, but each file exists in the memory folder next to the
index. The link is checked against the repo tree only.

They are not actionable today, so nothing breaks. But the memory class is the one 443 made the
default, and a broken memory link is exactly what an agent needs to know. Today a deleted memory file
and a present one get the same answer, so the class cannot report the one stale case that matters.

## Scope

1. For a corpus file under `<agent-memory>/`, resolve a relative link against that file's folder in
   the memory dir first, then against the repo as today.
2. Found in memory → `ok` (reason `exists_in_memory`). Missing in both → `gone`, actionable, in the
   memory class (an edit, no diff, as 443 says). A memory file has no git history, so there is no
   rename lookup.
3. A repo file still cannot claim the `<agent-memory>/` namespace (SEC-IN-03, unchanged).

## Acceptance

1. Fixture memory dir: an index linking one present and one missing sibling → `ok` and actionable
   `gone`.
2. tiny-studio: the 6 index links are `ok`.
