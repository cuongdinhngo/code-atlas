---
id: 384
slug: symbol-changed-since-revision
title: 'Nothing answers "has this method''s body changed since revision X" — a file diff is the finest grain'
phase: 2
milestone: Trust
status: deferred
depends_on: []
---

**Deferred 2026-10-10 — evidence gate:** the baseline to beat is `impact` on `git diff <rev>..HEAD` intersected with the anchored symbols (transitive, already shipped), plus `git log -L :<func>:<file>` for one symbol. Reopen only if a consumer measures that baseline as too noisy or too slow, with the numbers in this file.

## Why this exists

Anything written about code goes stale when the code changes, and the reader cannot tell. A
consuming repo that records "this behaviour was verified at revision X" and anchors the record to
a handful of methods needs to ask "did any of those methods change since X" — not "did any of
their files change". In legacy trees where a page script runs to thousands of lines, a file-level
diff flags nearly every record on every release and the signal drowns.

The index records build identity (`code_atlas/build_info.py`, `BUILD_KIND_CONTENT_HASH`) but no
per-symbol fingerprint, so the finest answer available is `git diff --name-only` plus `impact`.

The same question serves review ("which of the methods this PR claims to leave alone actually
changed?") and signed claims (383: a claim can still `hold` on its count while the body under it
changed). The records themselves stay in the consuming repo; code-atlas answers only about symbols.

## Scope

1. At build, store a normalised body fingerprint per symbol (whitespace- and comment-insensitive,
   decide at design), carried through incremental builds.
2. A way to ask, for a list of qnames or paths and a base revision: `unchanged | body_changed |
   signature_changed | moved | removed | unknown_at_base`. Exposed on 382's CLI; whether it is also
   a parameter on an existing tool (e.g. `impact`) is a design decision — the tool count stays 24.
3. The base revision's fingerprints come from a snapshot the consumer exports and keeps (one
   command, written where the consumer says) — the index is not required to keep history.

## Assumptions to prove at design

- Build-time cost on the anchor index is recorded; ship only if the full build slows by less than
  an agreed bound.
- Every adapter (PHP, TS/JS, Python, T-SQL) supplies a body range the hash can cover; an adapter
  that cannot answers `unknown`, never `unchanged`.

## Acceptance criteria

- **AC1:** a comment-only or whitespace-only edit answers `unchanged`; a one-token body edit
  answers `body_changed`; a parameter change answers `signature_changed`.
- **AC2:** a method moved to another file with an identical body answers `moved`, not
  `removed` + new.
- **AC3:** the build-time overhead on the anchor index is recorded in the task.
- **AC4:** a symbol absent from the base snapshot answers `unknown_at_base`, never `unchanged`.
