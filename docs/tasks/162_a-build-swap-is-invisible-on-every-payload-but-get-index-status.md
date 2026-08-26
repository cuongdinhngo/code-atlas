---
id: 162
slug: a-build-swap-is-invisible-on-every-payload-but-get-index-status
title: 'A build swap is invisible on every payload but get_index_status — carry a cheap server_build stamp, without forcing the signing git read onto the hot path'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [125, 077, 100]
---

## Why this exists (field retro rounds 8–9, 2026-08-25/26)

Task 125 put `server_version` / `server_build` on `get_index_status`, and the retros confirm it works —
but only there. Every other answer is still unattributable to a binary, and both rounds hit the cost:

> Round 8 (**8-D** / 7-G): the server build was swapped mid-session (`6a8ae85` → `cec2938`), the only
> signal a bare `Connection closed`. *"Every cross-boundary regression verdict in a session is void,
> silently."*
>
> Round 9 (**9-D**): *"I know the build did not change only because I sampled twice by hand."* `sign`
> already carries `build=cec2938`, but it is opt-in and off, so the **default** answer stays
> unattributable.

The project's evaluation loop is its most valuable instrument (the reasoning that justified 125). A
regression verdict that cannot name which binary produced each answer is not reproducible.

## Root cause, and why the retro's proposed fix is the wrong size

The retro's headline fix was *"flip `sign: true` to default on every tool."* That is more expensive
than it looks:

- The full signed line needs `revision_fields()` (`claim.py:59-78`), which needs a staleness dict,
  which needs `compute_staleness()` — **a git HEAD read plus a dirty scan per call**
  (`staleness.py:63-73`). `impact.py:91` guards `compute_staleness` behind `sign=True` **precisely so
  the hot path pays no git**. Flipping the default would put a git read on every mechanism answer,
  against 061 / the cheap-path discipline.

But the build id itself is cheap:

- `server_identity()` is `@lru_cache(maxsize=1)` and touches git **only on the first call of the
  process** (`build_info.py:62-66`); every later call is a dict lookup. `server_fields()`
  (`claim.py:81-84`) is therefore ~free after warm-up.

So the fix is to carry the **cheap** half (`server_build`) always, and leave the **expensive** half
(the revision-bearing `claim` line) opt-in.

## Scope

- **Stamp `server_build` (and `server_version`) on the payload of the read/nav/mechanism tools**, drawn
  from the lru-cached `server_identity()` — no git on the hot path. This closes 8-D/7-G: a build swap
  becomes visible on any answer, not only on a `get_index_status` call.
- **Do not flip `sign` default.** The full `claim` line stays opt-in; this ticket adds only the build
  identity, not the revision fields that cost a git read.
- **Reuse `get_index_status`'s existing shape** (`get_index_status.py:105`, `_server_fields`) as the one
  source, so two tools do not spell the field differently.
- **Measure the byte cost** and record it (061): the field is ~2 short strings; confirm `minimal` and
  the common answer grow only by that.

### Explicitly not in scope

- Making the revision (`rev`/`ref`/`index`) ride the default payload — that needs the git read `sign`
  guards, and is a separate cost decision.
- 9-E (`dirty_indexed_files`): assessed as a **non-finding** — the field measures uncommitted
  working-tree drift by design (047); after the retro's files were committed, `0` was correct and the
  index-vs-disk drift was reported by `staleness: behind`. No change.

## Constraints

- **061 / R7.1** — additive; the increment is one build id, measured, not a git read.
- **R4.2** — deterministic: `server_identity()` is a pure function of the installed artifact (no
  timestamps), already asserted by 125's tests.
- **R4.1 / R1.4** — the stamp is a formatter read of package identity; it opens no store and, after the
  cache is warm, spawns no git. No language branch (R1.1).
- **R3** — `server_build` is a tool-payload field, not contract vocabulary; no `contract_version` bump.

## Acceptance criteria

1. The default (`sign=false`, `standard`) payload of the read/nav/mechanism tools carries
   `server_build` (and `server_version`), pinned by a test; two builds of the same version are
   distinguishable from any such payload alone.
2. No new git subprocess is spawned on the hot path — proven, e.g. by asserting `server_identity` is
   consulted from cache and `compute_staleness` is **not** called when `sign=false` (contrast
   `impact.py:91`).
3. The field spelling matches `get_index_status`'s existing `server_build` / `server_version` exactly
   (one source of truth).
4. The byte growth on `minimal` / the common answer is measured and stated (061).
5. Determinism holds (R4.2); the R1.1 grep-gate stays green.

## References

Field retro rounds 8–9, findings **8-D** / **7-G** (build swap invisible) and **9-D** (sign is opt-in,
so the default is unattributable). `code_atlas/build_info.py:62-66` (`server_identity`, lru-cached),
`code_atlas/tools/claim.py:59-84` (`revision_fields` needs staleness; `server_fields` is cheap),
`code_atlas/tools/staleness.py:63-73` (the git read `sign` guards), `code_atlas/tools/impact.py:91`
(the guard this ticket must not undo), `code_atlas/tools/get_index_status.py:105` (`_server_fields`,
the source of truth). Builds on [125](125_no-payload-names-the-server-build.md),
[100](100_claim-signing-output-mode.md) (the opt-in claim line), [077](077_index-cannot-name-the-revision-it-describes.md).
