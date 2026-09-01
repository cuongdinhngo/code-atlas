---
id: 201
slug: a-forced-full-rebuild-is-silent-and-unroutable
title: 'A contract bump escalates to a 73-minute full rebuild with no word to the caller, inside a call that cannot outlive its client — and 050 already answers this for the other version key'
phase: 1.5b
milestone: Freshness
status: in-progress
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 201 · **work_doc_mode:** embed · **Current phase:** 2 design — complete; Gates 0-2 closed. Contract bound at Gate 2.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** enhancement.
- Run arg *"with skipper reviewer"* = **reviewer seat only** (AGENTS.md); the challenger keeps its seat.
- Run mode `autorun` — stops at the PR, never merges.
- Contract `.mango/run-contract-201.txt`. **One condition struck at t0:** `NO-CONTRACT-BUMP`
  reported HOLDING on an empty run — "no bump" is the *starting* state, so a negative acceptance
  criterion cannot be a contract condition. It is proven by the diff instead.
- RECONCILE t0: 7 declared | 5 re-run | 0 holding | 5 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 20 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 2 by handle | 2 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 1 want-decision asked | 6 how-decision resolved+cited | 1 ASSUMED | skip: no`

The ambiguous reference is the **anchor monorepo's MCP transcript** — a field log outside this
checkout. Every in-repo claim the ticket makes was re-derived: `grep -rn 'cancel' code_atlas/` → **0**,
`fastmcp>=3,<4` at `pyproject.toml:12`, `scope_change` at `indexer.py:327`, `CONTRACT_VERSION = 9` at
`contract.py:25` (so the field run's 8 → 9 bump is consistent with the tree).

**Handed-back want — `ASSUMED (awaiting ratification)`.**

| # | The want | Chosen direction | Status |
|---|---|---|---|
| W1 | AC6 asks for a replay on the anchor monorepo — 21,588 files, 7.2 M lines. No such corpus exists here (`config.real_corpus_path` is unset). What counts as satisfying AC6? | **Prove the mechanism, exclude the scale.** The two claims AC6 makes are separable: *the MCP call returns the refusal in under a second where it previously died at 3600 s* is provable on a fixture and is proven; *on the anchor monorepo* is not, and is recorded as coverage-gap exclusion **E1**. Unlike 200's AC5 this is a **scale** gap, not an unmeasured criterion — the behaviour is proven, the corpus is not | ASSUMED — handed back by the maintainer's *"you have my approvals to choose the best approach"*; needs an explicit confirm |

**Resolved + cited.** H1–H2 are mine; H3–H6 come from the exposure-checker, which found five and
whose remaining one is answered by H3's design.

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | Does the refusal also fire for `code-atlas-build`? | **No.** The refusal exists because an MCP call cannot outlive its client; a shell has no RPC deadline. If the CLI refused, the route the refusal *names* would itself refuse — a loop. The CLI opts in, so 176's contract ("the shell/CI route to a first and a full build") is unchanged | ticket Scope 1 (*"on the build tool's own path"*) and Scope 1's route; `cli.py:81`; 176 |
| H2 | Which single argument is Scope 2's opt-in? | **A new `allow_full_rebuild: bool = False`**, not the existing `full=True`. The checker verified `full=True` never reaches `indexer.py:239` (`build_or_update_index.py:222` returns `full_build` first), so it was never the silent path; and reusing it would force the CLI to pass `full=True` on **every** run, destroying its documented incremental default | `build_or_update_index.py:222`; `cli.py:81,113`; ticket Scope 2 |
| H3 | What exit code does the contract refusal get from `code-atlas-build`? | **None — it cannot reach it.** H1 makes the CLI opt in, so the payload it sees on a contract bump is the escalated `mode: full`, which is already exit `0`. 176's four-code map is untouched, and AC7 is exercised against the payload the CLI can actually produce | `cli.py:43-58`; ticket Scope 4 |
| H4 | Does AC5's *"pending full-rebuild requirement"* cover 172's scope change too? | **Contract-version only.** Detecting a scope change means launching adapters; `get_index_status` states it opens nothing and must not create an index as a side effect. A read tool that spawns six subprocesses to predict a rebuild is a different tool | `get_index_status.py:6-8`; ticket Scope 3 and Scope 1, both anchored to `indexer.py:239` |
| H5 | Which command string does the refusal name? | **`code-atlas-build --full`**, beside the in-band `allow_full_rebuild=true`. Both work under H1, and `--full` is the one that is unambiguously a full build whatever the index says | `cli.py:113`; ticket Scope 1 |
| H6 | At which `detail_level` does AC5's field appear? | **`standard` and `verbose`**, following 159 — its cited precedent attaches `unconfigured_adapters` at exactly those levels, and `get_index_status`'s default is already `standard` | `get_index_status.py:65,80,172`; ticket Scope 3 |

**Recalled claims — advisory.**

| handle | key | why it matches | what it warns |
|---|---|---|---|
| `one-field-two-questions` | 189, 022 — type 2, **recurrence 2, rejected 2026-08-30**, "re-propose on a third, independent sighting" | by handle: AC4 is about one field answering two questions | if AC4 turns out to be a genuine third sighting, it routes at finalise rather than sitting in lessons |
| `gate-on-the-invariant-not-on-presence` | 196-C1, proposed | by handle: a new disclosure is added | gate the refusal on the invariant `indexer.py:239` already decides, never on a field's presence |
| `drift-is-vs-the-index-commit-not-the-working-tree` | 166, proposed, area *freshness* | by area | staleness is measured against the index's commit, not the working tree |
| `identity-names-the-loaded-process-not-the-disk` | 164, proposed, area *index-status / identity* | by area | a status field must name the loaded process's view, not what a later disk read would say |

Two skipped as retired: `derived-not-listed-invariant` (**R6.7**) and `prove-the-guard-fails`
(**R6.5**), both now binding rules checked by the rule-section sweep.

## Phase 1 — analysis

`PREMISE: 20 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 2 by handle | 2 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists [+ Field evidence], Scope [+ Explicitly not in scope], Constraints, Acceptance criteria, References) | 5 decomposed | ROWS: C=9 R=4 G=2 AC=7`
`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

Both lines above `SECTIONS:` are carried forward from Phase 0, not re-run.

### BASELINE

`.venv/bin/python -m pytest -q`, run at aced82e — the **pre-change** tree, which is this branch's
point and equals `main`:

```
2694 passed in 162.62s (0:02:42)
```

Green, so the Definition of Done stays *all green*, with no baseline exclusions. Written as a
reference point rather than an empirical-output block for the tree under review — a baseline
measures the tree *before* the change, so the provenance axis would refuse it, correctly by its own
rule and wrongly for this artifact (lesson 200-C2).

### Requirements matrix

| ID | Source | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|
| G1 | Why this exists | the tool knows the escalation is coming before parsing a file, and must say so then | `indexer.py:239-242` returns `full_build` with no disclosure | open |
| G2 | Why this exists | the route that can serve a forced full rebuild exists and nothing points at it | `cli.py:113` `--full`; no payload names it | open |
| R1 | Scope 1 | detect at the build tool's own path and *return* — `mode`, a machine-readable reason, the route; no counts (060) | the 050 shape at `build_or_update_index.py:236-248` | open |
| R2 | Scope 2 | one argument opts in and builds in-band | H2 — `allow_full_rebuild` | open |
| R3 | Scope 3 | `get_index_status` names the pending requirement, omitted when clean | `get_index_status.py:131-135` is the 159 shape to mirror | open |
| R4 | Scope 4 | 176's exit-code map covers the new payload | `cli.py:43-58` | open |
| C1 | Not in scope | no async / background build | 177 settled it; nothing here starts a thread | open |
| C2 | Not in scope | no build-speed change | no parse or resolve code is touched | open |
| C3 | Not in scope | the fastmcp cancelled-request response is not owned here | `grep -rn cancel code_atlas/` → 0 | open |
| C4 | Not in scope | no change to *when* a rebuild is forced (030 AC1) | the predicate is extracted verbatim, not altered | open |
| C5 | Not in scope | no refresh hook wired into anyone's project | no `contrib/` change | open |
| C6 | Constraints | no contract bump (R3), no language branch (R1.1), deterministic (R4.2) | `contract.py` untouched | open |
| C7 | Constraints | the refusal fires only where line 239 already escalates — proven by mutating the stored key, not by reading the branch | one predicate, one definition site | open |
| C8 | Constraints | the doc budgets | **already discharged** — see clarification 2 | open |
| C9 | Constraints | no durable claim on disk that can lie later (072) | the refusal writes nothing; `set_meta` is not reached | open |
| AC1 | AC | returns without parsing a file, asserted on work done; payload names reason + route | red before the fix | open |
| AC2 | AC | a matching version reaches the normal incremental path with **no new field** (061) | pre-201 payload pinned | open |
| AC3 | AC | the opt-in performs the in-band full build, `mode: full` | | open |
| AC4 | AC | 172's escalation and 201's are distinguishable in the payload | `scope_change` vs a new `contract_change` | open |
| AC5 | AC | `get_index_status` names it, and says nothing when none is pending | omit-when-clean | open |
| AC6 | AC | replay: refusal in under a second; `code-atlas-build` completes outside the RPC | **mechanism proven, anchor scale excluded (E1)** | partial |
| AC7 | AC | `--status` and the exit-code map exercised against the new payload | | open |

### AC validation

| AC | Ticket's value | Re-derived | Falsifiable? |
|---|---|---|---|
| AC1 | *"without parsing a file"* | assert **no build ran at all**: `full_build` and `incremental_update` are never entered, spied, plus elapsed under the ticket's own one-second bar | yes — stronger than "no file parsed", and it is what the payload claims |
| AC2 | *"gains no field"* | the exact key set of an incremental payload, compared before and after | yes |
| AC3 | `mode: full` | the literal `FULL` constant | yes |
| AC4 | *"distinguishable"* | `scope_change` and `contract_change` are **disjoint keys**, and the refusal carries neither | yes — three states, three shapes |
| AC5 | *"names … and says nothing when none is pending"* | key present iff the predicate is true | yes, both directions |
| AC6 | *"under one second"* · *"on the anchor monorepo"* | **1.0 s** is the ticket's own bar and is asserted on a fixture; the anchor corpus is exclusion **E1** | half yes, half excluded |
| AC7 | 176's four codes | `0` built · `3` nothing to do · `4` busy · `1` failed, from `cli.py:20-23` | yes |

No AC is input-shape-dependent: every value above is written down before the run.

### Clarifications — all five self-resolved

1. **How is AC1's *"without parsing a file"* asserted "on elapsed work, not only payload shape"?**
   By spying that neither `full_build` nor `incremental_update` is entered, plus the ticket's own
   sub-second bar. *Cited:* ticket AC1; `indexer.py:239`.
2. **C8 says `BACKLOG.md` and the tier-1 sum have no room, and names ~48 tokens to prune or a
   `TIER1_BUDGET` raise.** **Already discharged.** Commit `aced82e` raised `BACKLOG.md` 8,200 → 8,300
   and `TIER1_BUDGET` 25,200 → 25,300, argued in both test comments, for exactly the 200/201/202
   rows. 201 adds a status word and a ledger row. *Cited:* `tests/test_doc_size_budget.py:83`;
   `tests/test_agent_chain_budget.py`.
3. **AC4 under the opt-in path.** A refusal is distinguishable by `mode` alone, but the *opt-in*
   path runs a full build and must still be distinguishable from 172's. It gets a `contract_change`
   record mirroring `scope_change` — one field per cause, neither overloaded. *Cited:*
   `indexer.py:323-325`, whose own comment already calls the contract bump *"the same class of
   change … and the same answer"*.
4. **What does AC7's `--status` mean against a payload?** `--status` reads the write lock, not a
   build payload (`cli.py:60-77`), so it is exercised in the same flow — no build running → exit
   `3` — while the **exit-code map** is exercised against the escalated `mode: full` payload the CLI
   can now produce. *Cited:* `cli.py:60-77`, `:43-58`.
5. **Does the refusal need `detail_level`?** No — it is a refusal, not a report; the 050 and 064
   refusals beside it carry no `detail_level` branch either. *Cited:*
   `build_or_update_index.py:88-108,236-248`.

### Universal inventory — N = 3

The one *"all/every"* requirement is AC4's distinguishability, over the three escalation states a
caller can land in:

| # | State | Payload shape |
|---|---|---|
| 1 | contract bump, not opted in | `mode: refused` · `reason: contract_rebuild_required` · route |
| 2 | contract bump, opted in | `mode: full` · `contract_change: {…}` |
| 3 | adapter scope moved (172) | `mode: full` · `scope_change: {…}` |

Review confirms **every** row, not a total.

### Gap analysis

| Goal | Current | Target | `path:line` |
|---|---|---|---|
| the caller learns the escalation before it costs 73 minutes | `indexer.py:239` returns `full_build` silently | a returned refusal naming reason and route | `indexer.py:239-242` |
| the two escalations are told apart | only `scope_change` exists | `contract_change` beside it | `indexer.py:327` |
| "call this first" warns of the pending rebuild | `get_index_status` says nothing about it | one omit-when-clean field | `get_index_status.py:111-129` |

### Blast radius

**Repo:** `app`. **Entry points:** the `build_or_update_index` MCP tool and the `code-atlas-build`
console script. **Touched:** `code_atlas/indexer.py`, `code_atlas/tools/build_or_update_index.py`,
`code_atlas/tools/get_index_status.py`, `code_atlas/cli.py`, plus tests and docs. **Dependents
traced at design.** No `db-map` exists, so no schema dependents. No adapter and no payload
vocabulary moves, so `tests/contract/` is untouched.

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) ✅ · §2 (change-type) N/A (no adapter is touched and no language is named) · §3 (change-type) ✅ · §4 (change-type) ✅ · §5 (change-type) ✅ · §6 (change-type) ✅ · §7 (change-type) ✅ · §8 (change-type) N/A (no dependency is added or moved)`

- **§1** — R1.1 (no language branch enters the core), R1.8 (one decision, one implementation: the
  forced-full predicate gets a single definition site that `indexer.py`, the build tool and
  `get_index_status` all read).
- **§3** — checked, not N/A: the change **reads** `CONTRACT_VERSION` and must not move it. R3.1 is
  satisfied because no node/edge vocabulary, field or qname rule changes; `contract.py` is untouched.
- **§4** — R4.2: the refusal is a pure function of two stored strings.
- **§5** — R5.3 (the refusal is returned, never raised), R5.4 (`reason` holds one register and the
  prose goes in a sibling), R5.6 (the payload never attests past what it can distinguish — hence
  three disjoint shapes for three states).
- **§6** — R6.5 (each guard observed failing), R6.7 (the predicate derived, not restated), R6.9
  (assert at the consumer: the tool payload and the status payload, not the private predicate alone).
- **§7** — R7.2 (ledger row), R7.6 (docs pruned as added).

No section is `PROVISIONAL`.

## Phase 2 — design

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Approach

**One predicate, three readers, three disjoint payload shapes — and the shell keeps its contract.**

1. `indexer.contract_rebuild_required(store)` becomes the **single definition site** (R1.8/R6.7) of
   the decision `indexer.py:239` already makes. Line 239 calls it; so do the build tool and
   `get_index_status`. The rule itself does not move — 030 AC1 is untouched (C4).
2. The build tool checks it **before opening a build at all** and *returns* the 050 shape:
   `mode: refused`, `reason: contract_rebuild_required`, the stored and current versions, and the
   route — `code-atlas-build --full` plus the in-band `allow_full_rebuild=true`. No counts (060).
3. `allow_full_rebuild: bool = False` is Scope 2's one argument. When set, the build proceeds and
   `incremental_update` records `contract_change` into the existing `scope` dict — the same
   mechanism 172 already uses for `scope_change`, so `_run` returns `mode: full` with no new
   machinery. The two causes are **disjoint keys**, never one overloaded field.
4. `code-atlas-build` passes `allow_full_rebuild=True`, so the shell route never meets the refusal
   it is the answer to, and 176's four-code map is untouched.
5. `get_index_status` attaches `full_rebuild_required` at `standard`/`verbose`, omitted when the
   predicate is false — the 159 shape, in the function that already reads the store.

### Rejected alternatives

| # | Alternative | Why rejected |
|---|---|---|
| A1 | Reuse the existing `full=True` as Scope 2's opt-in | `full=True` returns `full_build` before the incremental path (`build_or_update_index.py:222`), so it was **never** the silent escalation this ticket is about. Worse, the CLI would then have to pass `full=True` on every run to keep working, destroying its documented incremental default |
| A2 | Let `code-atlas-build` refuse too, and add a fifth exit code | The refusal's own payload names `code-atlas-build` as the route. A refusing route is a loop, and a new exit code is surface 176 did not ask for. The shell has no RPC deadline, which is the entire reason the refusal exists |
| A3 | One `escalation` field carrying a `cause` | This is `one-field-two-questions` (189, 022) walking back in. Two disjoint keys cost nothing and cannot be read as one axis |
| A4 | Make `get_index_status` predict 172's scope change too | It would have to launch every adapter to compare announced suffixes. `get_index_status.py:6-8` says it opens nothing and must not create an index as a side effect; a read tool that spawns six subprocesses is a different tool |

### Assumptions

| # | Assumption | Tag | Resolution |
|---|---|---|---|
| A-1 | `indexer.py:239` is the only site deciding a contract-forced full | **verified** — `grep -n CONTRACT_VERSION_KEY code_atlas/indexer.py` names one comparison; the extraction is verbatim |
| A-2 | The `scope` dict already reaches the payload | **verified** — `build_or_update_index.py:180` `result.update(scope)`, and `_run` returns `FULL if scope else INCREMENTAL` |
| A-3 | No third-party or runtime behaviour is assumed | **verified** — the change is two string comparisons and a dict key; nothing new is spawned, stored or fetched |

### Smallest change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `contract_rebuild_required()`; line 239 calls it; `contract_change` recorded into `scope` on escalation | `code_atlas/indexer.py` | `incremental_update` is called by the build tool **and** `code-atlas-refresh` (`hooks/refresh.py`) — proof collateral, traced below | R1, C4, C7, AC4 | 1/1 |
| 2 | `allow_full_rebuild` param, `CONTRACT_REBUILD_REQUIRED` reason, `_contract_refused()` | `code_atlas/tools/build_or_update_index.py` | the tool's MCP signature — a new optional arg with a default; `tests/test_mcp_server.py`'s R5 `detail_level` invariant | R1, R2, AC1, AC3 | 2/2 |
| 3 | `full_rebuild_required`, omit-when-clean, at `standard`/`verbose` | `code_atlas/tools/get_index_status.py` | `_attach_build_state` has two callers (`:171` unbuilt with `store=None`, `:253` built) — both traced | R3, AC5 | 1/1 |
| 4 | pass `allow_full_rebuild=True` | `code_atlas/cli.py` | 176's exit map, unchanged by construction | R4, AC7 | 1/1 |
| 5 | The proving test + AC2/AC3/AC4/AC5/AC6/AC7 assertions | `tests/test_contract_rebuild_refusal.py` (new) | none identified | AC1-AC7 | 7/7 |
| 6 | The tool row gains the refusal and the new argument | `docs/TOOLS.md` | `tests/test_documented_tool_count.py` reads it — the count does not move | R1, R7.6 | 1/1 |
| 7 | status `todo` → `done`, frontmatter, ledger row | `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, this file | `tests/test_backlog_bookkeeping.py`, `tests/test_doc_size_budget.py` | R7.2 | 1/1 |

**Proof collateral, traced not assumed.**

Ran at aced82e390e23b28565fb92102862394ac524c2d.

```
$ grep -rn "incremental_update\|_attach_build_state" code_atlas/ tests/ --include=*.py
tests/test_imports_link_the_file_they_name.py:24:from code_atlas.indexer import incremental_update
tests/test_imports_link_the_file_they_name.py:282:        incremental_update(config, store, ("src/widgets.ts",))
code_atlas/indexer.py:1:"""``full_build`` and ``incremental_update`` — one repo into one index (§8.1 / §8.3).
code_atlas/indexer.py:64:# Named phases for optional ``phase_times`` on ``incremental_update`` (task 052 profiler).
code_atlas/indexer.py:220:def incremental_update(
tests/test_noop_incremental.py:19:from code_atlas.indexer import full_build, incremental_update
tests/test_noop_incremental.py:66:        report = incremental_update(config, store, changed)
tests/test_noop_incremental.py:81:        first = incremental_update(config, store, changed)
tests/test_noop_incremental.py:83:        second = incremental_update(config, store, changed)
tests/test_noop_incremental.py:110:        incremental_update(config, store, changed)
code_atlas/tools/get_index_status.py:111:def _attach_build_state(
code_atlas/tools/get_index_status.py:171:        _attach_build_state(status, config, None)
code_atlas/tools/get_index_status.py:253:    _attach_build_state(enriched, config, store)
code_atlas/tools/build_or_update_index.py:22:from code_atlas.indexer import BuildReport, full_build, incremental_update
code_atlas/tools/build_or_update_index.py:230:    report = incremental_update(config, store, changed, progress=progress, scope=scope)
tests/test_vendor_stub_index.py:355:    from code_atlas.indexer import incremental_update
tests/test_vendor_stub_index.py:373:    report = incremental_update(config, store, changed=[])
tests/test_build_without_adapter_silent.py:16:from code_atlas.indexer import full_build, incremental_update
tests/test_build_without_adapter_silent.py:61:        incremental_update(config, store, ["src/a.aa"])
tests/test_alias_indirection.py:264:    """AC1: meta.contract_version lag → incremental_update rebuilds fully (finding 5)."""
tests/test_alias_indirection.py:265:    from code_atlas.indexer import incremental_update
tests/test_alias_indirection.py:286:        report = incremental_update(config, store, ["src/alias_indirection.php"])
tests/test_delta_resolve.py:16:from code_atlas.indexer import full_build, incremental_update
tests/test_delta_resolve.py:57:        incremental_update(config, store, changed)
tests/test_delta_resolve.py:76:        incremental_update(config, store, changed)
tests/test_delta_resolve.py:186:        incremental_update(config, store, gitutil.changed_paths(tmp_path, last))
tests/test_profile_incremental.py:1:"""Task 052: profile incremental_update phases (measure-only; no optimisation)."""
tests/test_profile_incremental.py:11:from code_atlas.indexer import INCREMENTAL_PHASES, full_build, incremental_update
tests/test_profile_incremental.py:81:        r1 = incremental_update(config, store, [], phase_times=first)
tests/test_profile_incremental.py:84:        r2 = incremental_update(config, store, [], phase_times=second)
tests/test_incremental.py:18:from code_atlas.indexer import full_build, incremental_update
tests/test_incremental.py:144:        report = incremental_update(config, store, changed)
tests/test_incremental.py:223:        incremental_update(config, store, changed)
tests/test_incremental.py:265:        incremental_update(config, store, changed)
tests/test_incremental.py:299:        incremental_update(config, store, changed)
tests/test_incremental.py:348:        report = incremental_update(config, store, changed)
tests/test_build_report_counts.py:20:from code_atlas.indexer import full_build, incremental_update
tests/test_build_report_counts.py:213:        report = incremental_update(config, store, ["twin/a.aa"])
tests/test_build_report_counts.py:275:        delta = incremental_update(config, store, changed)
tests/test_indirection_enrichment.py:17:from code_atlas.indexer import full_build, incremental_update
tests/test_indirection_enrichment.py:176:    third = incremental_update(config, store, ())
```

Every consumer is in the change list or unaffected: `hooks/refresh.py` calls `incremental_update`
through the same tool and therefore inherits the escalation record exactly as it inherited 172's;
both `_attach_build_state` callers are in file 3.

### Recalled handles — traced

**`one-field-two-questions`** (189, 022 — recurrence 2, rejected 2026-08-30).

Ran at aced82e390e23b28565fb92102862394ac524c2d.

```
$ grep -rn "escalated_to" code_atlas/ --include=*.py
code_atlas/indexer.py:330:                "escalated_to": "full",
```

One escalation cause is recorded today, under one key. Folded into the design as **A3 rejected**: the
second cause gets its **own** key rather than a `cause` discriminator inside a shared one. Whether
this is the third, independent sighting the class index asks for is judged at finalise, not here.

**`gate-on-the-invariant-not-on-presence`** (196-C1).

Ran at aced82e390e23b28565fb92102862394ac524c2d.

```
$ grep -rn 'if unwired:|if collection is not None:|if complete is not None' code_atlas/tools/get_index_status.py
code_atlas/tools/get_index_status.py:127:    if complete is not None and complete != BUILD_COMPLETE:
code_atlas/tools/get_index_status.py:134:    if unwired:
code_atlas/tools/get_index_status.py:264:    if collection is not None:
```

Three omit-when-clean attachments, each gated on a **value**, and `:127` on the invariant rather
than the key's presence — the shape this change copies. `full_rebuild_required` is attached iff the
predicate is true, never iff a meta key exists.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration (the tool over a real store and a real git repo) | integration — build the fixture, mutate the stored key, call the tool; spy that neither builder is entered | authored | ✅ |
| AC2 | integration | integration — the incremental payload's key set, unchanged | authored | ✅ |
| AC3 | integration | integration — `allow_full_rebuild=True` → `mode: full` and the file lands in the graph | authored | ✅ |
| AC4 | logic | integration — three states, three disjoint shapes, asserted per state | authored | ✅ |
| AC5 | integration | integration — field present iff pending, at `standard`; absent when clean | authored | ✅ |
| AC6 (mechanism) | integration | integration — the refusal returns under the ticket's own 1.0 s bar | authored | ✅ |
| AC6 (anchor scale) | runtime | **manual-recorded** | n/a | ❌ → **E1** |
| AC7 | integration | integration — `--status` with no build running → exit 3; `exit_code()` over the escalated payload → 0 | authored | ✅ |

No AC is input-shape-dependent — every expected value is written down before the run, so
`authored` fixtures are the right provenance and no corpus is wanted. `config.real_corpus_path` is
unset, which costs this plan nothing.

### Coverage-gap exclusions

**E1 — AC6's anchor-monorepo replay.**
- *item:* the 21,588-file / 7.2 M-line replay proving the refusal returns in under a second **on that
  corpus**, where the previous run died at 3600 s
- *risk tier:* low — the mechanism is proven on a fixture and the refusal does no work whose cost
  could scale with corpus size; it is two string comparisons before any store or git call
- *why deferred:* no anchor corpus exists on this host and `config.real_corpus_path` is unset
- *follow-up:* the next field-retro round against the anchor monorepo records the timing
- `expiry: when a field-retro round is next run against the anchor monorepo (docs/runbooks/field-retro.md)`
- `seen: []` — first occurrence of this class

### Proving test

**`tests/test_contract_rebuild_refusal.py::test_a_lagging_contract_version_refuses_without_building`** — red before the change (the stored key is mutated and a 73-minute-class full build starts), green after.

```
.venv/bin/python -m pytest tests/test_contract_rebuild_refusal.py -q
```

### Rollback + porting

`git revert` the commit. Every change is additive: one extracted predicate, one optional argument
defaulting to today's behaviour for `full=True`, one new payload key per escalation cause, one
omit-when-clean status field. No contract bump, no schema change, no adapter change. One repo, so no
porting order.

`SCOPE: M` — unchanged. Four source files, one new test file, two doc files; no tier crossed.
