---
id: 360
slug: build-stamps-head-read-at-the-end
title: 'A build stamps the HEAD it reads at the end, so a HEAD move mid-build leaves an index that says current but is not'
phase: 2
milestone: Freshness
status: todo
depends_on: [053, 166]
---

## Why this exists

`_record_meta` (`code_atlas/indexer.py:1396`) reads `gitutil.head_commit_and_ref` once parsing is
done and stores that SHA as `last_commit`. The diff an incremental parses is taken earlier
(`build_or_update_index.py:329`, `changed_paths(root, last)`), and a full build collects the tree
earlier still. If HEAD moves in between, the index stamps a commit whose changes it never parsed.

Seen 2026-10-01 on the anchor repo (~23k files):

| Time (+07) | Event |
|---|---|
| 14:19:41 | session-start build takes `write.lock` at HEAD `48b2089` |
| 14:19:57 | `git pull --ff-only` moves HEAD to `03420e7` (17 commits, 25 files added); `post-merge` refresh finds the lock held and skips (357) |
| after | the build finishes and stamps `last_commit = 03420e7` |

The result is worse than 357's "behind":

- `get_index_status` reports `current @ 03420e7`, while file and symbol counts match `48b2089`
  exactly.
- `file_outline` on a file added in that range answers `found: false`, `reason` ok.
- 035's read-through cannot repair it: `freshness.py:184` diffs `last_commit..HEAD`, which is now
  empty.
- `code-atlas-build` (incremental) exits 3 with `0 file(s)`. Only `--full` recovers.

357 assumes a dropped refresh leaves the index honestly `behind`. Because of this stamp, it can
leave it falsely `current` instead, so fixing 357 alone does not close the gap.

## Scope

1. Capture HEAD (SHA and ref) once, before the build reads the tree or the diff, and stamp that
   value. No second HEAD read feeds `last_commit`.
2. An incremental diffs `last..<captured>` and not `last..HEAD`. Otherwise a commit landing between
   the diff and the parse is half-seen.
3. When HEAD at publish time differs from the captured SHA, the index is `behind` against it, and
   nothing extra is needed for the state line to say so. 357's pending marker (or the next refresh)
   catches it up.

## Acceptance criteria

- **AC1 (proving test):** a build that HEAD moves past mid-parse (a test hook between collect and
  `_record_meta` commits a new indexable file) ends with `last_commit` equal to the pre-move SHA,
  `staleness: behind`, and an incremental that then parses the new file.
- **AC2:** the incremental path is covered the same way: the diff and the stamp name the same SHA.
- **AC3:** with HEAD unchanged during the build, `last_commit` and every existing freshness test are
  unchanged.
