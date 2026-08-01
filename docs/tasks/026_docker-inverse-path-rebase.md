---
id: 026
slug: docker-inverse-path-rebase
title: Inverse Docker path rebase for path-shaped qnames (adapter #2)
phase: 2
milestone: M7
status: todo
depends_on: [008, 019]
---

## Goal
When Docker root mapping is set, rewrite **all** container-rooted string fields back to host/repo form — not only the current file's wire prefix — so path-shaped qnames from adapter #2 stay linkable (§9, CONVENTION §3).

## Scope / Deliverables
- Add `from_adapter_path` (container_root → relative/host) mirroring `to_adapter_path`.
- Apply it to string values on the reply (at least `file_path`, path-shaped `qualified_name` / `source_qname` / `target_qname` / `target_raw`) so a cross-file reference like `/app/src/user.ts::User::save` does not land in SQLite still container-flavoured.
- Keep PHP namespace qnames untouched (no leading container root).
- Prove with a fake-adapter fixture that emits a cross-file path-shaped qname under the container root.

## Acceptance criteria
- With both roots set, a reply string under `CA_CONTAINER_ROOT` is stored as the corresponding repo-relative (or host) form; relative/namespace qnames are unchanged.
- Resolver can link a path-shaped qname that was emitted with a container prefix (fixture).

## References
PR #20 review finding #2; `docs/CONVENTION.md` JS/TS path-anchored qnames; task 008 Approach §3 (per-file wire rebase only).
