---
id: 458
slug: verify-refs-file-suffix-is-a-path
title: "A bare word with a file suffix is a path, never a member reference"
phase: 2
milestone: "Field gaps — tiny-studio"
status: todo
depends_on: [443]
---

## Why this exists

Same field report as 456. `atoms.json`, `voice_pace.json`, `series.json` and `keys.ts` have no folder,
so they are classified as symbols: `atoms` + `.json`. The head then matches a member
(`series.SeriesAtoms::atoms`, `Pipeline::voice_pace`, `SqliteJobQueue::series`,
`preview/rail.tsx::Tip::keys`), and the "member" `json` / `ts` is `gone`. That is 10 actionable
rows, all false.

- `atoms.json` (5 rows): a data file written under the channel folder at run time (ADR 0016).
- `keys.ts` (`docs/ARCHITECTURE.md:66`): the real file `web/src/api/keys.ts`, written as a bare name
  in a table cell.

## Scope

1. A ref whose last segment is a known file suffix is kind `path`, not `symbol`. Use the suffix set
   the tree and the adapters already know (`.json .ts .tsx .py .md .yaml .sh .css .j2 …`), not a new
   list, if one exists.
2. A bare file name (no folder) resolves like other folderless paths: `ok` if exactly one file in
   the tree has that name (`keys.ts` → `web/src/api/keys.ts`), otherwise the current weak path rules.
   A name no branch ever held stays `never_existed` and is never actionable (443).

## Acceptance

1. Fixtures: `atoms.json` next to a class with member `atoms` → a path row, not a symbol row;
   `keys.ts` with one match in the tree → `ok`.
2. Re-run tiny-studio: the 10 rows above are not actionable.
