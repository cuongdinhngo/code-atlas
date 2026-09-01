---
id: 201
slug: a-forced-full-rebuild-is-silent-and-unroutable
title: 'A contract bump escalates to a 73-minute full rebuild with no word to the caller, inside a call that cannot outlive its client — and 050 already answers this for the other version key'
phase: 1.5b
milestone: Freshness
status: todo
depends_on: [030, 050, 172, 176, 177]
---

## Why this exists

Field run on the anchor monorepo, 2026-08-31. `build_or_update_index(full=false)` was called on an
index four commits behind. It ran for **73 minutes**, the client gave up at its 3600 s ceiling, and
the session lost all 24 tools until a manual `/mcp` reconnect. The index itself was written
correctly — this is not a correctness defect. It is a defect in what the tool *says* and *when*.

Two facts collided, and each is individually intended:

`indexer.py:239` — a stored `contract_version` that lags forces a full rebuild, "never mix
vocabulary eras" ([030](030_alias-indirection-edges.md) AC1, `PLAN.md:156`). Correct, and this run
was a legitimate 8 → 9 bump.

[177](177_a-long-build-is-indistinguishable-from-a-hang.md) deliberately **rejected the async
branch**: *"async needs the build to outlive the call (thread + job state — the out-of-scope second
process), job state survives SIGKILL (re-creating the durable false claim AC3 forbids)"*. Also
correct, and [072](072_busy-build-hides-staleness.md)'s bug class is exactly why.

Together they mean a forced full rebuild on a repo this size **cannot be delivered through the MCP
route at all** — and the tool knows the escalation is coming at line 239, before it has parsed a
single file, yet says nothing and starts a 73-minute job anyway. The caller learns the outcome by
watching a lock file.

**The precedent is already in the tree, one version key over.**
[050](050_schema-version-mismatch-recovery.md) meets a `schema_version` it cannot extend and
*returns* `mode: refused` with the reason — "returned rather than raised so the caller reads the
action, but it reports no counts". A lagging `contract_version` is the same class of finding — an
index this server cannot incrementally extend — and gets no equivalent answer.
[172](172_incremental-is-blind-to-a-scope-change.md) set the other half of the shape: an escalation
is recorded through `scope` and surfaced as `scope_change` + `mode: full`, so `wrote.files: 0`
cannot mean both "nothing to do" and "could not act". 201 asks for that disclosure to arrive
*before* the work instead of after it.

And the route that can serve this already exists:
[176](176_no-full-build-from-a-shell.md) shipped `code-atlas-build` as "the shell/CI route to a
**first** and a **full** build" with an exit-code map, and 177 gave it `--status`. Nothing points a
caller at it. The MCP tool is the only surface an agent sees, and on the one input it cannot serve
it neither refuses nor redirects.

### Field evidence

| | |
|---|---|
| corpus | 21,588 files · 7.2 M lines (91.5 % of files under two read-only `legacy/` trees) |
| written | 216,804 nodes · 2,087,606 edges · 2.18 GiB SQLite |
| phases | parse 68 min (~5 files/s) · resolve 4.5 min · meta ~1 s |
| client | cancelled at 3600 s; server answered id=5 `{"error":{"message":"Request cancelled"}}` |
| client, next line | `Received a response for an unknown message ID` → `STDIO connection dropped after 3622s uptime` |
| build | committed 11 min **after** the transport died; `build_complete=1`, `last_commit` = HEAD |
| session | 24 `mcp__code-atlas__*` tools unavailable until manual reconnect |

The transport death is downstream of a cancelled-request response that fastmcp 3.4.5 sends and the
client rejects — see *not in scope*. It is what turns a slow answer into a lost session, but the
defect this ticket owns is the 73 minutes that should never have started.

## Scope

1. **Answer before the work.** The forced-full condition at `indexer.py:239` is detected on the
   build tool's own path and *returned*, naming the reason and the route — the 050 shape, not a new
   one: `mode`, a machine-readable reason distinguishing a contract bump from
   [172](172_incremental-is-blind-to-a-scope-change.md)'s scope change, and the `code-atlas-build`
   command that can serve it. No counts, because nothing was built (060).
2. **An explicit opt-in still builds in-band.** A caller that has read the refusal and wants the
   full build through MCP anyway can ask for it in one argument. The refusal is for the *silent*
   escalation; a knowing caller is not blocked, and the timeout risk becomes a choice.
3. **`get_index_status` names the pending requirement.** It is documented "call this first"; a
   reader who does should learn a full rebuild is required *before* spending 73 minutes, in the
   shape [159](159_get-index-status-does-not-name-available-but-unconfigured-adapters.md) /
   174 already use for naming a cost rather than only a switch.
4. **`code-atlas-build`'s exit-code map covers the new payload** (176's `0` built · `3` nothing to
   do · `4` busy · `1` failed), so the shell route the refusal points at is not itself surprised
   by it.

### Explicitly not in scope

- **Async / background builds.** 177 settled this on the record and 072 names the bug class. This
  ticket takes the opposite direction: make the *short* answer arrive instantly, not the long one
  survive.
- **Making the build faster.** The core is single-process at 94 % of one CPU while six adapter
  workers idle at 0.5 %; that is a real measurement and a separate ticket if anyone wants it. 201
  changes no build time.
- **The fastmcp cancelled-request response.** code-atlas has no cancellation handling of its own
  (`grep -rn 'cancel' code_atlas/` → 0 hits); the response comes from fastmcp 3.4.5, pinned
  `fastmcp>=3,<4`, with 3.4.7 available. Verify against 3.4.7 and report upstream if it persists —
  not owned here.
- **Any change to when a rebuild is forced.** 030 AC1 is correct. 201 touches disclosure and
  routing only.
- **Wiring a refresh hook into anyone's project.** `contrib/git/` offers it; 036 / 099 settled the
  never-installed stance.

## Constraints

- **No contract bump** (R3), **no language branch** (R1.1), deterministic (R4.2).
- **The refusal must not become a wrong answer.** It fires only where line 239 already decides to
  escalate — proven by a test that mutates the stored key, not by reading the branch.
- **`BACKLOG.md` had no room, and the tier-1 sum has less.** Measured on the working tree:
  `BACKLOG.md` 8,134 at HEAD → 8,186 with 200's row → 8,230 with 201's, over its 8,200 ceiling;
  201 paid for itself by pruning the `015 AC2 operator run` follow-up (38 tokens, detail already
  held by 018), landing at **8,192**. The tier-1 chain sum is the tighter gate and is **not 201's
  bill**: 25,190 at HEAD against a 25,200 budget — ten tokens of headroom — so 200's row alone puts
  it 42 over and 201 adds 6. Whoever lands first prunes ~48 tokens or raises `TIER1_BUDGET` in
  `tests/test_agent_chain_budget.py` and argues it in the PR (R7.6).
- **No durable claim on disk.** Whatever the payload says, nothing new may be written that outlives
  the process and can lie later (072).

## Acceptance criteria

1. With a stored `contract_version` behind `CONTRACT_VERSION`, `build_or_update_index(full=false)`
   returns **without parsing a file** — asserted on elapsed work, not only on payload shape — and
   the payload names the reason and the `code-atlas-build` route. Proven by mutating the stored
   key, red before the fix.
2. A matching `contract_version` reaches the normal incremental path unchanged: the pre-201 payload
   gains no field on that path (061).
3. The explicit opt-in performs the in-band full build and reports it as 176's `mode: full`.
4. 172's scope-change escalation and 201's contract escalation are **distinguishable** in the
   payload — a caller can tell which one it hit.
5. `get_index_status` names the pending full-rebuild requirement, and says nothing when none is
   pending (the 159/174 omit-when-clean shape).
6. Replay on the anchor monorepo: the MCP call returns the refusal in **under one second** where it
   previously died at 3600 s, and `code-atlas-build` completes the same rebuild outside the RPC.
7. `code-atlas-build --status` and the exit-code map are exercised against the new payload.

## References

[030](030_alias-indirection-edges.md) (contract bump forces a full rebuild — AC1, the rule this
ticket does not touch), [050](050_schema-version-mismatch-recovery.md) (the returned-refusal shape,
for the other version key), [172](172_incremental-is-blind-to-a-scope-change.md) (escalation
recorded and surfaced; the `wrote.files: 0` ambiguity), [176](176_no-full-build-from-a-shell.md)
(`code-atlas-build`, the route nothing points at),
[177](177_a-long-build-is-indistinguishable-from-a-hang.md) (progress in the lock, and the async
branch rejected on the record), [072](072_busy-build-hides-staleness.md) (the durable-false-claim
bug class), [053](053_refresh-on-checkout-hook.md) (the refresh hook that keeps an index from
drifting this far),
[159](159_get-index-status-does-not-name-available-but-unconfigured-adapters.md) / 174 (naming a
cost, not only a switch).
Field log: the anchor monorepo's MCP transcript, 2026-08-31 14:48:41 Z cancel → 14:59:49 Z commit.
