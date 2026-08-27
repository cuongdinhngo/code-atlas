---
id: 170
slug: server-identity-is-cached-so-a-later-build-swap-is-unreportable
title: '`server_identity` is `@lru_cache`d, so the divergence check runs once — a build swap after the first payload can never be reported, and silence does not say which'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [164, 162, 125]
---

## Why this exists (field retro round 11)

164 fixed 10-A and round 11 verified it **non-circularly** (`/proc` + `stat` + `git reflog`, never the
stamp itself): the process imported at a tree carrying `e591f02`, the repo later moved to `331ac06`, and
every payload correctly read `e591f02`. That half works and it is what made round 11's §12 possible at
all. **The remaining half does not fire:**

```
21:18:48  appended a comment to code_atlas/build_info.py — a real content change to a loaded module,
          48 minutes after import
then      read_symbol(...)                    → server_build: "e591f02", no stale_process
          get_index_status --verbose --sign   → server_build: "e591f02", no stale_process, no repo_head
```

> Round 11 §12.c: *"**Closed — with a narrow third layer.** … Whether that is by design or a defect
> **I cannot tell from the payload** — and R-2 says that inability is the finding. The practical
> consequence is small; the reporting consequence is not: **a reader cannot distinguish "no divergence
> detected" from "divergence not checked."**"*
> §0.a: for the last 12 minutes of the session the checkout genuinely differed from the process and no
> payload said so — *"harmless here **only because** the delta was a docs-only commit… The harmlessness
> was luck of the delta, not a property of the design."*
> §14.a adds the carve-out this ticket exists to retire: ***`server_build` names the loaded code, not
> the current checkout.***

## Root cause

- `code_atlas/build_info.py:77` — `@lru_cache(maxsize=1)` on `server_identity()`. The divergence
  comparison at `:89` (`_content_build_id() == _LOADED_BUILD_ID`) therefore runs **once**, on the first
  call, and every later payload reuses that dict. A swap after the first answer is structurally
  unreportable — which is the same *class* of staleness 164's own docstring (`:3-9`) says the field
  exists to make legible in-band.
- `code_atlas/build_info.py:89-97` — the matching branch returns `{version, build}` and the diverged
  branch adds `stale_process` / `repo_head`. **Absence of the field is the only signal of the matching
  case**, so a payload cannot say *"checked, and the disk still matches"*; 061's omit-when-empty rule is
  correct for a value and wrong for a **verdict**.
- The cost that motivated the cache is real and measured: 164 recorded the hash walk at **6.35 ms /
  72 files / 780 KB** (`docs/TOKEN_LEDGER.md`, row 164). Re-hashing on every payload is not the answer;
  a cheaper freshness probe is.

## Scope

Make the divergence verdict live, and make it legible.

1. The divergence check re-evaluates after the first call, at a cost that does not scale with payload
   count — design picks and records the probe (an `st_mtime`/`st_size` sweep of the loaded modules; a
   bounded interval; an explicit invalidation) and states its rejected alternatives.
2. A reader can distinguish **checked-and-matching** from **not-checked**. One field, one verdict; the
   design records whether it rides every payload or only `get_index_status` + `sign`.

### Explicitly not in scope

- Reloading modules, restarting, or acting on the divergence. The tool reports; the operator restarts.
- The `+dirty` worktree axis (`:51`) — orthogonal and already correct.
- Changing `_LOADED_BUILD_ID`'s freeze-at-import semantics: that is 164's fix and it verified.

## Constraints

- **Cost** — no full re-hash per payload. The added per-call cost is measured and recorded against
  164's 6.35 ms baseline and the tokens-to-answer gate.
- **R4.2** — identical loaded artifact ⇒ identical id, across processes and hosts; no timestamps in the
  id itself.
- **061** — if the verdict field is added to every payload, its bytes are measured and pinned (164's
  stamp is already 49 B unconditional, measured in round 11 §6); if it is not, the omission is a
  recorded design decision, not an accident.
- **R1.1** no language branch · **R3** no bump · the wheel / no-checkout path (125) unchanged.

## Acceptance criteria

1. A test simulates a post-first-call divergence (loaded module content changes after `server_identity`
   has already answered once) and the next payload reports it — fails on today's code.
2. A payload can be read as *checked and matching* rather than as *silent*; pinned for both the matching
   and the diverged case.
3. The added per-call cost is measured, recorded, and does not re-hash the package tree per payload.
4. A server whose disk never moves is byte-identical to today, or the byte delta is measured and pinned.
5. The wheel / no-checkout path still names a build (125) and is unchanged; the `+dirty` axis unchanged.
6. Determinism (R4.2), no language branch (R1.1), no contract bump (R3).

## References

Field retro round 11 §12.c (**the third layer**), §0.a (12 minutes of undisclosed divergence in the
session itself), §14 row 10-A (verified, layer noted), §14.a (the new carve-out this retires), §6
(the 49 B unconditional stamp). `code_atlas/build_info.py:3-9,51,77,89-97`; 164's measured hash-walk
row in [`TOKEN_LEDGER.md`](../TOKEN_LEDGER.md). Related:
[164](164_server-build-names-the-repo-not-the-running-process.md) (the fix this completes),
[162](162_a-build-swap-is-invisible-on-every-payload-but-get-index-status.md),
[125](125_no-payload-names-the-server-build.md).
