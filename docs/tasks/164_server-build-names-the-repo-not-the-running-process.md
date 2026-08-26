---
id: 164
slug: server-build-names-the-repo-not-the-running-process
title: '`server_build` names the repo HEAD, not the code the process loaded — the field built to make a build verifiable reports a commit that did not answer'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [162, 125, 100]
---

## Why this exists (field retro round 10, 2026-08-26)

162 shipped `server_build` on every Pillar-1 payload so an answer could name the binary that produced
it (8-D / 9-D). Its first field outing produced a **confident falsehood**, and it is the round's
headline:

> The MCP server process started at **19:55:05**. The files carrying 158–163 were written to disk at
> **20:02:19** — seven minutes later. Every payload that carried a stamp reported **`3d70ab2`**, the
> post-fix SHA, while the process was running pre-fix code. **0 of 6 fixes fired in real work; all 6
> fire on a freshly-started server on the same commit.**
>
> "Had I trusted `server_build` — which is exactly what 162 was built to let me do — I would have filed
> six *shipped but does not work in the field* findings. All six would have been wrong."

This is **worse than the 8-D it repairs**: an unstamped payload is a known unknown; a stamp read from
the repository is a wrong answer wearing the fix's clothes. Two servers on one machine (pids 7301 and
11699, started 10 minutes apart across the write) reported the **same build** and had **different
behaviour**.

The file's own docstring already states the invariant this breaks: *"a retro must never quote a commit
that did not answer"* (`build_info.py:1-7`).

## Root cause

- `code_atlas/build_info.py:38-47` — `_git_build_id()` returns `gitutil.head_commit(root)[:7]` for the
  **checkout the package sits in**. That is the repository's HEAD, not the code Python imported.
- `code_atlas/build_info.py:60-64` — `server_identity()` is `@lru_cache(maxsize=1)`, so the value is
  computed once **at first call**, not at import. A `git pull` between process start and first call is
  therefore already invisible; one after the first call is equally invisible.
- The `+dirty` guard (`build_info.py:47`) defends the **worktree-dirty** axis only. The
  **process-vs-repo** axis — the one a long-lived stdio server lives on — is undefended.
- `code_atlas/build_info.py:49-57` — `_content_build_id()`, a sha256 over every `.py` **under the
  loaded package root**, is exactly the honest identifier, but it runs only as a fallback when no git
  checkout is found.

An editable install with a checkout — the maintainer's and every developer's normal setup — takes the
git branch every time, so the honest identifier is the one path that never runs where it is needed.

## Scope

Make the stamp describe the **process**, and disclose the divergence rather than hide it.

1. Derive the build id from the **loaded package** (the `_content_build_id()` shape), computed once,
   for every install mode — checkout, wheel, container alike.
2. When a git checkout is present, keep the commit as **context, not identity**: report the repo's HEAD
   alongside, and set **`stale_process: true`** when the loaded-content id does not correspond to that
   HEAD's content.
3. `server_provenance()` (`build_info.py:67-76`) carries the new field to every Pillar-1 payload that
   162 already stamps — one spelling, no per-tool work.

The exact field names and whether the git commit stays under `server_build` or moves beside it are a
**design decision**, recorded with the rejected alternative. The binding requirement is: *an answer must
never name a commit whose code did not produce it, and a divergence must be visible in-band.*

### Explicitly not in scope

- Restarting, reloading or hot-swapping the server. This ticket makes divergence **legible**, not
  impossible.
- Pillar-2 onboarding payloads (162's recorded scope boundary stands).
- `sign` / `claim` output shape beyond inheriting the corrected provenance.

## Constraints

- **R4.2 determinism** — identical loaded artifact ⇒ identical id. No timestamps, no pid, no mtime in
  the id itself.
- **Hot path** — `server_identity()` is lru-cached and 162 measured ~53–60 B per payload against a
  test-pinned ≤ 80 B. A content hash walks the package tree **once per process**; prove the per-payload
  cost is unchanged and the one-time cost is bounded.
- **R3** — provenance is payload furniture, not contract vocabulary. No `contract_version` bump.
- **R1.1** — no language branch.
- **061** — omit-when-empty: a process that matches its repo adds no new field.

## Acceptance criteria

1. A server whose loaded code differs from the checkout's HEAD reports a build id derived from the
   **loaded code**, and carries `stale_process: true` (or the design's recorded equivalent) — pinned by
   a test that simulates the divergence without a real `git pull`.
2. A server whose loaded code matches HEAD is **byte-identical** to today's payload (061).
3. The per-payload byte cost stays within 162's pinned budget; the one-time cost of hashing the package
   tree is measured and recorded.
4. Determinism holds (R4.2): the same loaded artifact yields the same id across processes and hosts.
5. No `contract_version` bump (R3); no language branch (R1.1).
6. The wheel / no-checkout path still names a build (125's original guarantee) and is unchanged.

## References

Field retro round 10 §0.a, §12, §12.c, §15 (**the round's single requested change**), §14 (7-G / 8-D /
9-D reopened *because of their own fix*). `code_atlas/build_info.py:1-7,38-47,49-57,60-64,67-76`.
Related: [162](162_a-build-swap-is-invisible-on-every-payload-but-get-index-status.md) (the fix this
repairs), [125](125_no-payload-names-the-server-build.md) (the origin),
[100](100_claim-signing-output-mode.md) (`sign`).
