---
id: 374
slug: whole-install-skew-at-session-start
title: 'An install whose halves all lag a release hears nothing, and a stale adapter checkout surfaces only when a build fails'
phase: 2
milestone: Adoption
status: todo
depends_on: [348]
---

## Why this exists

This is the field report that meets the re-open condition of 348's decision in
[PLAN §19](../PLAN.md#19-project-context--decision-log): "an install that ran an old release
without knowing."

An anchor project (PHP + SQL + TS, ~22.9k files, Windows) observed the following on 2026-10-09:

- **No notice of 0.3.0.** The release shipped 2026-10-08. The anchor ran the 0.2.0 plugin with the
  0.2.0 tool install, and no line said a newer release existed. The 348 skew line compares the two
  halves only with each other, and the two halves agreed.
- **The adapter checkout is a third half, and nothing checks it before a build.** The checkout that
  `CA_<LANG>_CMD` points into had been pulled to contract 14. The first sign was a refused
  incremental build: `build_or_update_index` returned `no_usable_adapter`, with the detail
  `adapter 'php' speaks contract v14, but this core speaks v13`. Read tools kept serving a `behind`
  index, so the session ran on stale answers until the build was tried.
- **The skew line worked once a half moved.** After `claude plugin update`, the next session start
  printed `hooks expect code-atlas 0.3.0 but 0.2.0 is installed — run uv tool upgrade code-atlas`.
- **On Windows, `uv tool upgrade` fails halfway under a running server.** The package and six
  scripts moved to 0.3.0. Copying `code-atlas.exe` into `~/.local/bin` failed with
  `os error 32` (in use by the MCP server), so uv exited `Failed to upgrade code-atlas` even though
  the upgrade had mostly landed. Neither the README nor the skew line mentions this.
- **`server_stale_process: false` after the upgrade.** The server started on 0.2.0, then
  `uv tool upgrade` replaced the package under it. `get_index_status` then reported
  `server_version 0.2.0`, `server_stale_process: false`. A `/mcp` reconnect loaded 0.3.0. The cause
  was not traced. Both fields come from the memoised `_identity` (`build_info.py`), recomputed only
  when a loaded module's `(mtime, size)` moves. So either the disk still held 0.2.0 (uv may restore
  the old environment when it reports `Failed to upgrade`), or that probe missed the swap.
  **UNVERIFIED:** that the package itself reached 0.3.0 before the reconnect — how it was checked
  is not recorded.
- **The plugin did not update itself, and the reason is documented.** The Claude Code docs
  (`code.claude.com/docs/en/plugins/loading.md` and `install.md`, read 2026-10-09) say:
  - auto-update is **off by default** for third-party marketplaces;
  - it is enabled with `/plugin` → Marketplaces → *Enable auto-update*, or with `"autoUpdate": true`
    on the marketplace's `extraKnownMarketplaces` entry in a settings file;
  - it runs after the first message of an interactive session, after a random delay of up to ten
    minutes, and takes effect on `/reload-plugins` or the next launch.

  348's README records this as unmeasured (its A3).

The combined effect: once the plugin auto-updates, 348's skew line pulls the tool install along.
The adapter checkout still has no offline check, and the README does not yet say how to make the
plugin the half that moves first.

**What an offline check cannot see.** Scope 1–2 detect halves that *disagree*. In the 0.3.0 case
all three halves agreed on 0.2.0, so they stay silent there. Only auto-update (Scope 3) or a
re-decided release check (Scope 5) reaches that case; AC5 decides which.

## Scope

1. **An adapter ↔ core contract skew line at session start, offline.** For each configured
   adapter, `code-atlas-state` reports when the adapter's contract differs from
   `contract.CONTRACT_VERSION`. The line names the adapter, both contracts and the fix **for the
   side that is behind**, as 348's `skew_line` does: a checkout behind the core is pulled and its
   dependencies reinstalled; a core behind the checkout (the anchor's case, v13 vs v14) is
   upgraded. There is no network call (R4/R4.1), and the hook stays inside its 10 s timeout and
   silent with no index. How the contract is read is a design question; see the assumptions.
2. **One line for the whole install.** When more than one half lags, name each command, in the
   order they must run. A half lags when it is older than the newest of the three local halves.
   The order is: on Windows, disconnect the server first (the launcher lock, Scope 3); then tool,
   plugin, checkout; then reconnect the server (`/mcp`) or restart. The line is at most **90 tokens**
   (`estimate_tokens`, the state line's `TOKEN_BUDGET`).
3. **README *Upgrading*:**
   - replace "auto-update was not measured" with the documented behaviour above, and recommend
     enabling auto-update for this marketplace, at user level or in a project's
     `extraKnownMarketplaces` entry for an anchor's team;
   - on Windows, stop or disconnect the server before `uv tool upgrade`, or re-run it after;
   - a `/mcp` reconnect is enough to load the new server.
4. **Trace the `server_stale_process: false` observation.** First tell the two causes apart: did
   uv restore 0.2.0 on failure, or did the `(mtime, size)` probe miss files replaced with the same
   stamp? Then either fix the detection, or record why a running server cannot see the upgrade.
5. **Re-decide PLAN §19's 348 entry with this evidence.** Claude Code's auto-update already
   performs the network fetch outside the core. The question is whether that, together with
   Scope 1–2, closes the gap without a release check of code-atlas's own. Record the decision
   either way.

## Assumptions to prove at design

- **How the session-start hook learns an adapter's contract inside 10 s.** Two candidates were
  rejected while the ticket was reviewed:
  - *A build-time stamp compared with the core* catches nothing new. `meta.contract_version`
    already equals the core's contract at build time (the handshake forces it), and 347 already
    compares it. A checkout pulled after the build leaves the stamp equal to the core.
  - *Reading the constant from each adapter's entry file* makes the core parse PHP, TS and Python
    source (R1.1), and guess the entry file from a `CA_<LANG>_CMD` argv that may be a container.

  Two remain:
  - (a) launch each adapter and read its handshake with a short timeout. This is new for a hook
    that "never builds, reparses". It launches only `CA_<LANG>_CMD`, and a project file's
    `[adapter_cmd]` still needs `CA_TRUST_PROJECT_FILE=1` (341). Measure the cold start of all
    configured adapters together, on Windows, on the anchor.
  - (d) record a build or refresh that the handshake refused, as 355 records a refused refresh,
    and let the state line speak from it. This costs nothing at session start, but it speaks only
    after the first refused refresh.
- **Whether a project-level `extraKnownMarketplaces.<name>.autoUpdate` is honoured for a teammate
  who installed the plugin at user scope.** The docs imply it, but show only a managed-settings
  example. Measure it before the README recommends it.

## Acceptance criteria

- **AC1:** With the checkout's adapters on one contract and the core on another, in either
  direction, the `SessionStart` hook prints one line naming the adapter, both contracts and the
  fix for the side that is behind. It is silent when they match, silent with no index, and it
  exits 0 within the hook timeout. Each case is seen red first (R6.5).
- **AC2:** With the tool, the plugin and the checkout all on different versions, the hook names
  every half older than the newest one, with its command, in the Scope 2 order (the Windows
  disconnect step only on Windows), in at most 90 tokens.
- **AC3:** The README *Upgrading* section states the documented auto-update behaviour, how to turn
  it on per user and per project, the Windows launcher lock, and the `/mcp` reconnect.
- **AC4:** The `server_stale_process` observation is reproduced, the cause is named (uv restored
  the old package, or the probe missed the swap), and it is either fixed or explained in LESSONS.
- **AC5:** PLAN §19 carries the re-decided 348 entry, with its reason, including whether an
  install whose halves agree on an old release is told so.
