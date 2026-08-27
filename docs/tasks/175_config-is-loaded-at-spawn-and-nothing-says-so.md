---
id: 175
slug: config-is-loaded-at-spawn-and-nothing-says-so
title: 'Config is read once at spawn and no payload says so — editing `.code-atlas.toml` then building returns a silent, unchanged success'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [164, 170]
---

## Why this exists (field episode, 2026-08-27)

The maintainer edited `.code-atlas.toml` to add the second adapter, ran a build, and got a success that
described the old world:

```
edit .code-atlas.toml   → adds the adapter
build                   → indexed_suffixes: [".php", ".phtml"],  wrote.files: 0,  2.6 s
```

> *"Không field nào báo 'config trên đĩa khác config tôi đã load'. Đây cùng lớp với 164/10-A nhưng lệch
> một tầng: 164 giờ đóng dấu code đã load, còn config đã load thì không có gì tương đương. Đề xuất:
> hash config lúc startup, so với file trên đĩa khi build, khác thì báo `config_stale_process` — đối
> xứng với `server_stale_process`."*

The diagnosis is exact. 164 closed *"which code answered"* (10-A) and 170 is open on *"which code
answered **now**"*. **Neither covers *which config answered*** — and config is the axis that decides
what the index even contains, which makes a silent stale read here more consequential than a stale
build id.

## Root cause

- `code_atlas/main.py:170` — `build_server(load_config(Path.cwd(), os.environ)).run()`. The `Config` is
  built **once**, at process start, from `.code-atlas.toml` (`config.py:22`, `PROJECT_FILE`) plus the
  environment, and bound into every tool's closure (e.g. `tools/build_or_update_index.py:51`).
- Nothing re-reads the file, and nothing hashes it. There is no `config` equivalent of
  `build_info._LOADED_BUILD_ID` (`build_info.py:74`), so no payload can compare loaded config against
  disk.
- `indexer._record_meta` records the *effects* of the config (`indexed_suffixes`, census) but never the
  *identity* of the config that produced them, so the index cannot be asked which config built it
  either.

## Scope

Give config the provenance 164 gave code, on the same shape.

1. Hash the loaded project config at startup — the file's bytes plus the `CA_*` environment the config
   reads — and expose the identity where `server_build` already rides.
2. When the file on disk differs from the loaded hash, say so: `config_stale_process` (or the design's
   recorded field name), with the same omit-when-empty discipline (061).
3. The build tool checks it at build time, because that is the moment the divergence costs a whole
   build (this episode).
4. Record whether the index should also store the config identity that built it — a separate claim from
   the process's, and possibly its own follow-up.

### Explicitly not in scope

- **Reloading** the config, or restarting the server. Report; the operator restarts. (A reload would
  change tool bindings mid-session, which is a different and much larger decision.)
- The environment axis of adapter launch commands beyond what the config reads.
- `server_identity`'s own caching bug — [170](170_server-identity-is-cached-so-a-later-build-swap-is-unreportable.md).

## Constraints

- **Cost** — one small file read plus a hash, at startup and at build time only. Never per payload:
  `server_build` already costs 49 B unconditionally (round 11 §6), and this must not add a second
  standing tax without measuring it.
- **R4.2** — same config bytes + same env ⇒ same identity, across processes and hosts; no timestamps.
- **061** — omit when the config matches, or measure and pin the byte delta if it always rides.
- **No-config path** — a repo with no `.code-atlas.toml` (env-only, or defaults) must still answer, and
  its identity must be stable (cf. 125's wheel path).
- **R1.1** no language branch · **R3** no bump.

## Acceptance criteria

1. A test loads a config, mutates the file on disk, and asserts the next build reports the divergence —
   fails on today's code.
2. A build whose config file is unchanged is byte-identical to today, or the added bytes are measured
   and pinned.
3. The no-config / env-only path names an identity and does not raise (125's guarantee).
4. Determinism (R4.2): identical bytes and env produce an identical identity across two processes.
5. Whether the index stores the config identity that built it is decided and recorded — implemented or
   filed with evidence.
6. No language branch (R1.1), no contract bump (R3).

## References

Field episode 2026-08-27, finding (3) — the maintainer's own diagnosis, verified in source.
`code_atlas/main.py:170`; `code_atlas/config.py:22,131`; `code_atlas/build_info.py:74`;
`code_atlas/tools/build_or_update_index.py:51`. Round 11 §12.c (the same class, one layer up), §6 (the
49 B standing cost of the code axis). Related:
[164](164_server-build-names-the-repo-not-the-running-process.md) (the shape to mirror),
[170](170_server-identity-is-cached-so-a-later-build-swap-is-unreportable.md) (the sibling defect),
[172](172_incremental-is-blind-to-a-scope-change.md) (what the silence cost this episode).
