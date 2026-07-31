---
id: 014
slug: search-read-outline
title: Search / read / outline + FTS (M3 — first daily release)
phase: 1
milestone: M3
status: todo
depends_on: [010, 004]
---

## Goal
The daily-usable core: find, outline, and read symbols cheaply (§12). **Ship point.**

## Scope / Deliverables
- `search_symbol(query, kind?, namespace?, limit?)` — ranked `{qname, kind, file:line}` (FTS + name).
- `file_outline(path)` — symbols + line ranges, no body.
- `read_symbol(qname)` — source of just that class/method + docblock.
- Efficiency prompts: `explore_area`, `find_usages` (status → search/outline → read only what's needed).
- **CI:** this is the first tagged release, so it needs a release path — at minimum a build/install check (`pip install .` from a clean checkout) proving the package installs outside the dev venv, and a tag-triggered workflow if artifacts are published.

## Acceptance criteria
- Search returns ranked, relevant symbols on the fixture repo within `CA_MAX_RESULTS`.
- `read_symbol` returns only the target's source + docblock (not the whole file).
- Tagged as the first daily-usable release.

## References
Plan §12, §15 (M3).
