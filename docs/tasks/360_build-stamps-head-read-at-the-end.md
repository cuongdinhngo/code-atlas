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
(`code_atlas/tools/build_or_update_index.py:329`, `changed_paths(root, last)`), and a full build collects the tree
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
- 035's read-through cannot repair it: `code_atlas/tools/freshness.py:184` diffs `last_commit..HEAD`, which is now
  empty.
- `code-atlas-build` (incremental) exits 3 with `0 file(s)`. Only `--full` recovers.

357 assumes a dropped refresh leaves the index honestly `behind`. Because of this stamp, it can
leave it falsely `current` instead, so fixing 357 alone does not close the gap.

## Scope

1. Capture HEAD (SHA and ref) once, before the build reads the tree or the diff, and stamp that
   value. No second HEAD read feeds `last_commit`.
2. An incremental diffs against the captured SHA, never HEAD. `gitutil.changed_paths` reads HEAD
   twice (`since..HEAD` and the working tree vs `HEAD`, `gitutil.py:82-86`), so both reads must go.
   A single `git diff --name-only <since>` (working tree vs `since`) covers both without either.
3. When HEAD at publish time differs from the captured SHA, the index is `behind` against it, and
   nothing extra is needed for the state line to say so. 357's pending marker (or the next refresh)
   catches it up.
4. **Stamp old, never new.** The parse reads the working tree, not git objects, so a pull mid-parse
   leaves some files newer than the captured SHA. That is safe: the next incremental re-parses them,
   and re-parsing is idempotent. A stamp newer than the parsed content loses changes; this one only
   costs work.
5. The captured value reaches `_record_meta` as a parameter from both of its callers
   (`indexer.py:296` and `:600`, via `full_build` and `incremental_update`); `_record_meta` no
   longer calls `gitutil`. Design lists every caller of both, so no path keeps a HEAD re-read.

**Out of scope:** detecting an index already stamped falsely `current`. It cannot be told apart
cheaply, so the CHANGELOG entry tells an affected index to run `--full` once.

## Acceptance criteria

- **AC1 (proving test):** a build that HEAD moves past mid-parse (the test commits a new indexable
  file from the existing `progress=` callback; no production hook is added) ends with `last_commit` equal to the pre-move SHA,
  `staleness: behind`, and an incremental that then parses the new file.
- **AC2:** the incremental path is covered the same way: the diff and the stamp name the same SHA.
- **AC3:** with HEAD unchanged during the build, `last_commit` and every existing freshness test are
  unchanged.
- **AC4:** after AC1's build, 035's read-through answers `file_outline` on the new file with
  `found: true`, with no rebuild in between.
- **AC5:** an uncommitted edit made during the build is still seen by the next incremental (Scope 2's
  single diff keeps the working-tree half).
