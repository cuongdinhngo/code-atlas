---
id: 203
slug: a-rebuild-is-gil-bound-and-its-operating-knowledge-is-unroutable
title: 'A full rebuild sustains ~4.5 files/s because reply decode and the single writer share one GIL — and the operating knowledge that would have kept a caller out of that hour is in a runbook no agent is ever routed to'
phase: 1.5b
milestone: Freshness
status: done
depends_on: [052, 096, 176, 177, 200, 201]
---

## Why this exists

Field run on the anchor monorepo, 2026-09-01. Enabling the T-SQL adapter changed `.code-atlas.toml`,
which forces a full rebuild — correct, and exactly the escalation
[201](201_a-forced-full-rebuild-is-silent-and-unroutable.md) taught the build tool to *announce*. 201
fixed the silence. It did not touch the number the silence was hiding: **the rebuild took 91
minutes**.

While it ran, the driver process held **0.97 of one core** and its six PHP adapter subprocesses sat
at **~0.6 % CPU each**, on a 16-core host at load average **1.34**. The adapters were not the
bottleneck; they were idle, waiting.

**The runbook already names half of the cause** — `onboarding-a-repo.md` §2: *"Throughput is
dominated by the write path, not the parser. The same adapter parses ~490 files/s single-threaded in
isolation, while a full build with six workers sustains ~19 files/s end-to-end — the difference is
the single SQLite writer plus the `nodes_fts` trigram triggers. Adding workers past a handful buys
little."*

**What nothing names is the decode side.** `_parse_group` (`indexer.py:884`) fans work across
`threading.Thread`, not processes, and each worker thread runs `json.loads(line)`
(`adapter.py:165`) on the adapter's reply — pure Python, holding the **same GIL the writer needs**.
The writer is single-threaded by construction (`indexer.py:839`, *"writing every result on this
thread"*) and back-pressures through a `workers*2`-bounded queue (`indexer.py:889`). So *"adding
workers past a handful buys little"* is understated in a way that matters: past the first, an extra
worker buys **nothing**, and every one taken adds GIL contention to the writer it is already
blocked on. `workers` reads like a throughput knob and is not one.

Two further costs sit on the same path and are unnamed anywhere:

`replace_file_rows` (`store.py:481`) wraps `_delete_rows(path)` plus both inserts in
`with self._conn:` — **one transaction per file**, 24,569 of them on this run. And a full build
**never truncates**, so every path already present in a 2.2 GiB index pays a real delete against
live indexes and the `nodes_fts` triggers before its first insert. The runbook's own healthy
baseline was measured writing to a **disposable `/tmp/trial/graph.db`** (§2), i.e. the one case
where that delete costs nothing. Whether that difference is what separates 18.7 files/s from 4.5 is
**not established** — see *Not in scope* — and this ticket asks for it to be measured before
anything is changed.

### The half that makes the other half expensive to live with

The operating knowledge needed to avoid this hour **already exists** and is good:
`docs/runbooks/onboarding-a-repo.md` §2 (build outside the client, measure it), §3b (budget the
incremental), [176](176_no-full-build-from-a-shell.md)'s `code-atlas-build`,
[177](177_a-long-build-is-indistinguishable-from-a-hang.md)'s `--status`. **Nothing routes an agent
to any of it.** Measured on the tree at HEAD:

- `AGENTS.md`, the declared `context_file`, matches **zero** of `runbook` · `onboarding-a-repo` ·
  `code-atlas-build` · `--status` · `rebuild`.
- `get_index_status` on a stale index returned `next_tool_suggestions: ["build_or_update_index"]` —
  it points at the MCP route 201 taught to refuse this very input, and never at the shell route that
  can serve it, at `--status`, or at the runbook.
- `code-atlas-build` appears to a model only as a `route` string inside a refusal payload it has to
  provoke first.

The observable consequence is an agent that re-derives the same operating facts every session. This
run cost tool calls rediscovering that `--status` exists, that the CLI is the right route, and that
`CA_PHP_CMD` lives only in the MCP env — knowledge already written down, in a file the agent was
never told to open. That is [200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md)'s finding
("the one channel a model does see") pointed at operations rather than at recognition, and it is why
this ticket carries both halves: the perf fix changes the number, and the routing fix is what stops a
caller walking into the number.

### Field evidence

| | |
|---|---|
| corpus | 24,569 files — 19,155 php · 2,980 sql · 2,434 typescript |
| written | 262,899 nodes · 2,188,026 edges · 2.2 GiB SQLite |
| full rebuild, populated DB | **5,470 s (~91 min)** ≈ 4.5 files/s end-to-end |
| parse phase, sampled 44 s | 225 files = **5.1 files/s** |
| driver CPU, same 45 s window | 4,371 ticks = **0.97 core**, pegged |
| six php adapters | ~0.6 % CPU lifetime · host load 1.34 / 16 cores |
| incremental, **0** files changed | **5.5 s** |
| incremental, 1 edit → 3 files | **63.8 s** (8,069 edges) |
| runbook §2 healthy baseline | 18,867 files / 1,008 s = 18.7 files/s, **fresh `/tmp` DB** |
| [201](201_a-forced-full-rebuild-is-silent-and-unroutable.md), same repo, populated DB | parse 68 min ≈ 5 files/s · resolve 4.5 min |

Two readings the table settles. **Resolve is not the cost** — 201 measured it at 4.5 minutes against
68 minutes of parse, so the hour is the parse/write path and nowhere else. And the **~5 files/s is
reproducible**: 201 and this run measured it independently, five weeks apart, on the same repo.

### Numbers in the runbook that no longer hold

Found while reading it, and cheap to correct alongside:

1. §3b: *"**~62 s** for `build_or_update_index(full=false)` … whether **0** or **21** files changed —
   a flat fee"*. Measured today: **0 files = 5.5 s**, 3 files = **63.8 s**. The fee is not flat any
   more — [096](096_edit-then-ask-tax-two-files-cost-a-minute.md)'s delta-scoped resolve closed the
   no-op — so a reader budgets 62 s for something that costs 5, and the sentence that taught "it is
   flat" now teaches the wrong shape.
2. §2 cites `store.py:75-84` for the `nodes_fts` triggers. They are at `store.py:122-138`.

### 096's prediction for this repo has never been measured

[096](096_edit-then-ask-tax-two-files-cost-a-minute.md) is `done`. It measured on **synthetic 20k and
60k-residue fixtures** with sub-second walls — 2 files went 0.793 s → 0.421 s, `resolve` 0.408 s →
0.0197 s (20.7×) — and its Resolution closes on a prediction: *"The benefit scales with the residue …
which means the anchor (far larger residue than 60k) should see more than the 20.7× measured here,
not less."*

**Nobody measured the anchor.** Today's 3-file incremental is the first such number and it is
**63.8 s**. That is not evidence 096 regressed — its pre-fix anchor cost is unrecorded, so there is
nothing to compare against, and resolve may well be 20× cheaper inside that 63.8 s. It is evidence
that the phase which now owns the wall is **unidentified on the only corpus anyone runs this on**,
and that a shipped prediction about this repo was never checked against it (P6: an assumption holds
only for the tree it was verified on). Scope 1 closes both.

## Scope

1. **Measure before fixing — on the anchor, both paths.** Run the existing
   `scripts/profile_incremental.py` on this repo for 096's own scenarios (it has never been run
   here), and extend it to the full-build path. Settle which of the three named costs owns the wall:
   GIL-contended decode · one-transaction-per-file · per-path delete into a populated DB. Report
   fresh-DB vs populated-DB as a controlled pair, since the only fresh-DB number on record
   (18.7 files/s) is from a different repo and cannot carry the comparison.
2. **Take the decode off the writer's GIL** — whichever the measurement justifies: decode in the
   adapter-owning process, a process pool for the worker seat, or a framing the core does not have
   to `json.loads` per file. `workers` must end up meaning what a reader thinks it means, or stop
   being offered as a throughput knob.
3. **A full build that will discard a covered language refuses first.** `meta.covered_languages`
   already records `php,sql,typescript`. A shell `code-atlas-build --full` resolves adapters from
   `.code-atlas.toml` plus env, and this run would have silently dropped **all 19,155 PHP files** had
   `CA_PHP_CMD` — which lives only in the MCP server's env block — not been exported by hand. The
   index can compare what it covers against what the run can parse, and refuse in the 050/201 shape
   rather than write the loss.
4. **Route the operating knowledge to the agent channel.** The content exists; give it one home a
   model actually reads — `AGENTS.md` pointing at it, and `next_tool_suggestions` naming
   `code-atlas-build` / `--status` on the states where the MCP route cannot serve. No new prose that
   restates the runbook (R7.6): this is routing, not authoring.
5. **Correct the two stale runbook facts** in *Numbers in the runbook that no longer hold*.

## Constraints

- **No contract bump** (R3), **no language branch** (R1.1), deterministic (R4.2).
- **The perf claim is measured on the anchor, never asserted.** A before/after pair at a named SHA,
  same corpus, same DB starting state — P4: the gate names the commit it ran at.
- **Scope 2 must not weaken 072's rule.** Whatever moves off the GIL, nothing new may outlive the
  process and be able to lie later.
- **The tier-1 chain has two tokens of headroom.** Measured on the working tree at the commit that
  files this ticket: baseline 25,246, this ticket's `BACKLOG.md` row +52, total **25,298** against
  `TIER1_BUDGET = 25_300` (`tests/test_agent_chain_budget.py`). The row was already cut once to fit
  — it is titled by its slug, the 201/202 shape, not by a prose finding. **Whoever picks this up
  pays for their own row by pruning (R7.6) or raises the budget and argues it in the PR**, and
  re-measures rather than trusting this line (P4).

## Acceptance criteria

1. A profile run on the anchor attributes **both** walls — the full build and 096's 2-file
   incremental — across decode · write · delete · resolve, with the fresh-vs-populated pair
   reported, and states plainly whether 096's "more than 20.7× here" prediction holds. Red-before-fix is not applicable; the
   deliverable is the number that scope 2 is then chosen against.
2. After scope 2, a full rebuild of the anchor at the same SHA and the same DB starting state is
   **measurably faster**, with both runs' SHAs recorded. A fix that does not move the number is
   reverted, not kept.
3. `workers > 1` produces a throughput gain that scales, or the knob's documentation states the
   ceiling it actually has. Proven by a two-point measurement, not by reasoning about the GIL.
4. With `meta.covered_languages` naming a language the current run cannot parse, `code-atlas-build
   --full` **refuses and writes nothing** — asserted by the index being unchanged afterwards, not
   only by the payload. Red before the fix: today the same input silently rewrites the index without
   that language.
5. A fresh agent session, given only `AGENTS.md`, reaches `code-atlas-build --status` and the
   runbook's build guidance **without** provoking a refusal payload first. Probed the way
   `tool-recognition-probe.md` probes recognition.
6. `get_index_status` names the shell route on the states that need it and stays silent otherwise
   (the 159/174 omit-when-clean shape).
7. The two corrected runbook facts match a re-measurement at the landing SHA.

## Not in scope

- **Why this repo sustains ~5 files/s where the runbook's baseline sustained 18.7.** The two runs
  differ in repo, language mix *and* DB starting state; the populated-DB delete is a hypothesis with
  a mechanism (`store.py:481`, `store.py:122-138`) and no measurement. Scope 1 exists to settle it,
  and no fix should be chosen before it does.
- **The `nodes_fts` trigram triggers themselves.** Named by the runbook as part of the write cost;
  changing the search index is a separate ticket with its own recall evidence.
- **Splitting this ticket.** The perf half and the routing half are filed together because the
  routing gap is what turns the perf cost into a surprise. A maintainer who wants them separate
  should split at scopes 1–3 / 4–5; nothing in either half depends on the other landing.

## References

[052](052_incremental-noop-cost.md) (the flat-fee measurement §3b quotes, now stale on the
no-op), [096](096_edit-then-ask-tax-two-files-cost-a-minute.md) (delta-scoped resolve; closed the no-op, and
carries the anchor prediction nobody measured), [176](176_no-full-build-from-a-shell.md) (`code-atlas-build`, still the route nothing points
at), [177](177_a-long-build-is-indistinguishable-from-a-hang.md) (`--status`, and the async branch
rejected on the record), [200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md) (the one
channel a model does see — this ticket is that finding aimed at operations),
[201](201_a-forced-full-rebuild-is-silent-and-unroutable.md) (announced the escalation; owns the
field evidence for parse 68 min / resolve 4.5 min).
Field log: the anchor monorepo, 2026-09-01 — full rebuild 12:45 → 14:16 Z, adapter-enable
config change, `config_identity c30ed5e → 2efae9c`.

## Session status

- **KEY:** 203 · **work_doc_mode:** embed · **Current phase:** 5 finalise — **complete.** Scopes 1, 3 and 5 landed in PR #252 (merged); scopes 2 and 4 in the PR below.
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · `STRUCTURE: native` · **Type:** bug + perf.
- Run: `/mango:autorun 203 --no-reviewer`, unattended, third of three tickets after 204 (merged,
  PR #250) and 205 (deferred — see below).
- **This PR delivers scopes 1, 3 and 5. Scopes 2 and 4 stay open**, and the ticket's own
  *Not in scope* sanctions the split: *"A maintainer who wants them separate should split at
  scopes 1–3 / 4–5; nothing in either half depends on the other landing."* What is left and why:
  - **Scope 2** (take the decode off the writer's GIL) is *by the ticket's own instruction* chosen
    against scope 1's number — *"no fix should be chosen before it does"*. The number is now on the
    record; picking between a process pool, adapter-side decode and a new framing is an
    architectural decision for a maintainer, not for an unattended run at 03:00.
  - **Scope 4** (route the operating knowledge to the agent channel) edits `AGENTS.md`, a tier-1
    file. PR #251 is open and unmerged and raises `TIER1_BUDGET` to 25,700 for its own eight rows;
    adding to `AGENTS.md` from a second branch would make both PRs' budget arithmetic wrong. It
    waits for #251 to land.

## Phase 0 — refine

`PREMISE: 14 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 2 by handle | 1 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

The ambiguous reference is the anchor field log. Two ticket claims were **superseded by events**
before work started, and neither is a defect in the ticket:

1. *"`CA_PHP_CMD` … lives only in the MCP server's env block"* — no longer true. The anchor's
   `.code-atlas.toml` now carries all three adapter commands in `[adapter_cmd]`, with a comment
   naming exactly this incident. The specific field trigger is mitigated **by configuration**; the
   general defect scope 3 describes is not, and is fixed here.
2. The tier-1 headroom the ticket measured (*"two tokens"*) is stale twice over: 204's row took the
   54 that were free, and PR #251 raises the ceiling again. Re-measured below.

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | Is scope 3's comparison covered-vs-**configured** or covered-vs-**started**? | **Configured.** An adapter that is configured and then fails to boot already refuses as `no_usable_adapter` — observed live during this run. Comparing against the started set would duplicate that guard and would need the adapters launched twice | the live refusal in Phase 3; `adapter.py` announce path |
| H2 | Does the coverage guard carry a `route`? | **No route, a hint instead.** R5.4c: no registered tool can configure an adapter, and naming one that cannot answer is worse than naming none. `code-atlas-build --full` is precisely the thing being refused | R5.4; `_coverage_refused` |
| H3 | Does the guard fire on an incremental too? | **Full builds only.** A full build *replaces* the index, so a missing language is discarded rather than skipped. An incremental leaves the existing rows alone. Smallest useful thing (R7.1) | ticket Scope 3 (*"A full build …"*); R7.1 |

**Recalled claims — advisory.** By handle: `prove-the-guard-fails` (**R6.5**),
`an-aggregate-outlives-the-world-that-named-it` (**P7** — `covered_languages` is exactly such an
aggregate, and this ticket is about it being overwritten by the run that invalidates it). By area:
`verify-cited-reference-at-pickup`, which is what caught the two superseded claims above. Skipped as
retired: `count-pin-in-blast-radius` (no count pin moves here).

## Phase 1 — analysis

`PREMISE: 14 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 2 by handle | 1 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`SECTIONS: 6 found (Why this exists, Field evidence, Scope, Constraints, Acceptance criteria, Not in scope [+ References]) | 6 decomposed | ROWS: C=4 R=5 G=2 AC=7`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`BASELINE: green`
`SCOPE: L`
`TIER: full`

### BASELINE

`pytest -q` in an isolated worktree at **fb1a36c** — this branch's parent — with its own `uv venv`
and the three adapter dependency directories **copied**, not symlinked:

```
2677 passed, 70 skipped in 237.92s (0:03:57)
```

Zero failures. The 70 skips are this host's, not this branch's: 2,677 + 70 = **2,747**, exactly the
count CI reports as fully green on the same commit. Recorded as a reference point, not as evidence
for the tree under review (201-C1). **The shared checkout could not produce a baseline at all** —
see the environment note in Phase 3.

### Requirements matrix

| ID | Source | Interpretation | Status |
|---|---|---|---|
| G1 | Why this exists | a rebuild's cost must be attributable, not folk knowledge | **scope 1 — closed** |
| G2 | Why this exists | operating knowledge must reach the agent channel | **scope 4 — OPEN** |
| R1 | Scope 1 | measure before fixing, on the anchor, both paths | **partially closed** — full-build pair delivered; 096's incremental scenarios deferred, reason below |
| R2 | Scope 2 | take the decode off the writer's GIL | **OPEN** — chosen against R1 by the ticket's own instruction |
| R3 | Scope 3 | a full build that would discard a covered language refuses first | **closed** |
| R4 | Scope 4 | route the operating knowledge | **OPEN** — tier-1 collision with PR #251 |
| R5 | Scope 5 | correct the two stale runbook facts | **closed** |
| C1 | Constraints | no contract bump, no language branch, deterministic | closed — `contract.py` untouched; the guard compares two runtime sets and names no language |
| C2 | Constraints | the perf claim is measured, never asserted | closed — every number below is a command's output at a named SHA |
| C3 | Constraints | scope 2 must not weaken 072 | **n/a** — scope 2 is not attempted |
| C4 | Constraints | the tier-1 chain has two tokens of headroom | closed — re-measured, and the ticket's figure was stale; see below |
| AC1 | AC | a profile attributing both walls, fresh-vs-populated pair, and 096's prediction | **partial** — the pair is delivered; the decode/write/delete split and 096's prediction are not |
| AC2 | AC | a rebuild measurably faster after scope 2 | **OPEN** — scope 2 not attempted |
| AC3 | AC | `workers > 1` scales, or the ceiling is documented | **OPEN** |
| AC4 | AC | a full build discarding a covered language refuses and writes nothing | **closed**, red before |
| AC5 | AC | a fresh session reaches `--status` from `AGENTS.md` alone | **OPEN** — scope 4 |
| AC6 | AC | `get_index_status` names the shell route where needed | **OPEN** — scope 4 |
| AC7 | AC | the corrected runbook facts match a re-measurement | **closed** |

**C4, re-measured — the ticket's figure was stale in both directions.** At `fb1a36c` the chain is
**25,288 / 25,300**: 12 tokens free, not the 2 the ticket predicted, because 204's row took the 54
that were actually free. This ticket's open row costs 54, so **25,342** — over. R7.6 applied first
and found nothing honest to cut: no id appears in two tables and every `done` row is already
slug-titled. So the ceiling is raised **25,300 → 25,400** and `BACKLOG.md` **8,300 → 8,400**, argued
in both test comments. **PR #251 raises the same two constants to 25,700 / 8,700** for its own eight
rows; whichever lands second re-measures with `scripts/agent_chain_cost.py` rather than trusting the
other's pre-merge figure, and both comments say so.

### Clarifications — all three self-resolved

1. **Why were 096's incremental scenarios not run, when the ticket asks for them by name?**
   `profile_incremental.py` appends a byte to an indexed **source file** in `--root` and writes to
   the index there. The anchor is a 13 GB client monorepo that a **second Claude session was working
   in throughout this run**. Mutating its sources and its index — even transiently and even
   restored — is a write to shared state no handover authorised. Copying the checkout to get a
   writable one is 13 GB for four timing numbers. Deferred with the reason recorded, not silently
   dropped. *Cited:* `profile_incremental.py` docstring, scenarios (b) and (c).
2. **Is the full-build pair a fair controlled comparison?** Yes for the one variable it isolates.
   Same corpus, same `last_commit 61591c6`, same code, same host, same knobs, back-to-back, and the
   **only** difference is whether the target DB already held 262,899 nodes and ~2.08 M edges. It is
   *not* controlled against the runbook's 18.7 files/s figure, which is a different repo.
3. **Does the coverage guard belong in `indexer.py` or in the build tool?** The predicate in
   `indexer.py` beside `contract_rebuild_required` and `build_incomplete`, the payload in the tool —
   the shape 201 and 202 both used, so a third refusal reads like the first two (R1.8).

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) ✅ · §2 (change-type) ✅ · §3 (change-type) ✅ · §4 (change-type) ✅ · §5 (change-type) ✅ · §6 (change-type) ✅ · §7 (change-type) ✅ · §8 (change-type) N/A (no dependency is added or moved)`

- **§1** — R1.1: the guard compares `covered_languages` against `config.adapter_cmds` and names no
  language. R1.8: the predicate/payload split follows 201 and 202 exactly.
- **§2** — checked: the test's two languages are the fixture adapter's `fake` and `second` tokens.
- **§3** — `contract.py` untouched; no adapter can observe the change.
- **§4** — R4.2: `coverage_loss` returns a sorted tuple; the payload's lists are sorted.
- **§5** — R5.4c (**hint, no route** — H2), R5.6 (a first build has no stamp, so the guard is silent
  rather than guessing), R5.3 (a missing adapter command is a config error and fails loud).
- **§6** — R6.2 (spec-driven fixture tokens), R6.5 (the red run is in Phase 3, and it is
  behavioural — an `ImportError` red was rejected as proving nothing), R6.9 (the guard is asserted
  on the **index**, not only on the payload).
- **§7** — R7.1 (full builds only — H3), R7.2, R7.5, R7.6 (C4).

No section is `PROVISIONAL`.

## Phase 2 — design

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 1 proven on a real corpus`

### Approach

**Measure the one variable nobody had isolated; guard the loss that had no guard; correct the two
facts that had gone stale. Leave the architecture decision to the maintainer who now has the number.**

1. **Scope 1** — two full builds of the anchor, back-to-back, same code, same corpus, same commit,
   same knobs, differing **only** in whether the target database already held the graph. The
   runbook's healthy 18.7 files/s was measured against a disposable `/tmp` DB on a *different*
   repo, so it could never carry this comparison; this pair can.
2. **Scope 3** — `indexer.coverage_loss(store, configured)` compares `meta.covered_languages`
   against `config.adapter_cmds`, and `_coverage_refused` returns the 050/201 shape. Predicate in
   `indexer.py` beside `contract_rebuild_required` and `build_incomplete`, payload in the tool —
   the shape both prior refusals use (R1.8).
3. **Scope 5** — two corrections, each verified against the tree rather than retyped from the
   ticket.

### Rejected alternatives

| # | Alternative | Why rejected |
|---|---|---|
| A1 | Run `profile_incremental.py` on the anchor as scope 1 literally asks | It appends a byte to an indexed **source file** and writes to the index in `--root`. A second Claude session was working in that 13 GB client monorepo throughout this run. Recorded as exclusion **E1** rather than done unsafely or dropped in silence |
| A2 | Copy the anchor checkout to get a writable one | 13 GB duplicated into `/tmp` for four timing numbers, leaving a client monorepo lying in scratch. Disproportionate |
| A3 | Compare covered languages against the **started** adapter set | H1: an adapter that is configured and then fails to boot already refuses as `no_usable_adapter` — observed live in this very run. This would duplicate that guard and need the adapters launched twice |
| A4 | Give the coverage refusal `route: code-atlas-build --full` | R5.4c. That route is the thing being refused, and no registered tool can configure an adapter. A hint, and no route |
| A5 | Fire the guard on incrementals too | An incremental does not replace the index, so a missing language is not discarded. H3 / R7.1 |
| A6 | Attempt scope 2 with the pair's number in hand | The ticket forbids it: *"no fix should be chosen before it does"*. Process pool vs adapter-side decode vs a new framing is an architecture decision, and an unattended run is the wrong place for it |

### Exclusions

| # | Excluded | Why | Expiry (checkable) |
|---|---|---|---|
| **E1** | 096's two incremental scenarios on the anchor (scope 1, second half) | A1 — the profiler mutates sources and the index in a repo another session was actively using | Discharged when `profile_incremental.py --root <a writable anchor clone>` is run and its report is attached to this ticket. Checkable: the ticket has no `phases` block for the incremental path |
| **E2** | The decode / write / delete attribution *within* the full-build wall | Needs per-call-site instrumentation of `_parse_group` and `replace_file_rows`; the fresh-vs-populated pair isolates the **delete** hypothesis without it, which is the one scope 1 names as unmeasured | Discharged when scope 2 lands, which needs the split to choose between its three candidates. Checkable: AC1's "attributes both walls across decode · write · delete · resolve" is still open |

**`1 input-shape-dependent AC` / `1 proven on a real corpus`** — AC1 *is* an input-shape
question: its answer depends on whether the target database already holds the graph, which is
the whole point of the pair. So it is classified as shape-dependent and discharged on the real
corpus rather than on a fixture, which could not exhibit a 2.2 GiB starting state at all.

### Smallest change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `COVERAGE_LOSS*` constants + `coverage_loss()` | `code_atlas/indexer.py` | one caller, the build tool | R3, AC4 | 1/1 |
| 2 | `_coverage_refused` + the check + `allow_coverage_loss` | `code_atlas/tools/build_or_update_index.py` | the MCP signature gains one optional arg, defaulting to the safe side | R3, AC4 | 2/2 |
| 3 | the guard's fixture and AC4 | `tests/test_coverage_loss_refusal.py` (new) | none | R3, AC4 | 6/6 |
| 4 | the two stale facts | `docs/runbooks/onboarding-a-repo.md` | none | R5, AC7 | 2/2 |
| 5 | the ticket, its row, the two budget constants | `docs/BACKLOG.md`, `tests/test_doc_size_budget.py`, `tests/test_agent_chain_budget.py`, this file | those two tests; **collides with PR #251 by design** | C4, R7.2 | 1/1 |

`contract.py` untouched. No ledger row: the ticket is **not** `done`, so R7.2's spend row is not yet
owed — it is owed by the PR that closes scopes 2 and 4.

### Recalled handles — traced

**`prove-the-guard-fails` (R6.5).** The first red run was an `ImportError` — the test module could
not even import `COVERAGE_LOSS` off the pre-fix tree:

```
E   ImportError: cannot import name 'COVERAGE_LOSS' from 'code_atlas.indexer'
1 error in 0.08s
```

**That was rejected as evidence.** A collection error proves the constant is new, not that the
behaviour was wrong. The constant was inlined and the run repeated so it exercised behaviour; that
run is in Phase 3 and it is the one this ticket rests on.

**`an-aggregate-outlives-the-world-that-named-it` (P7).** `covered_languages` is exactly such an
aggregate, and the sharpest fact in the red run is that the offending build **overwrote it** — the
stamp naming the dropped language was destroyed by the run that dropped it, so afterwards nothing on
disk recorded the loss. `test_the_refusal_leaves_the_index_untouched` asserts the stamp survives,
which is why that assertion is on the index and not on the payload (R6.9).

### Verification plan

| AC / scope | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| Scope 1 | integration | two full anchor builds, wall clock at a named SHA | **real corpus** | ✅ |
| Scope 1 (2nd half) | integration | ❌ **excluded — E1**, expiry recorded | — | ❌ |
| AC1 (decode/write/delete split) | integration | ❌ **excluded — E2**, expiry recorded | — | ❌ |
| AC4 | integration | the guard, asserted on the **index** and the payload | authored, spec-driven | ✅ |
| AC7 | logic | both corrected facts re-derived from the tree | existing | ✅ |

Two ❌, both recorded exclusions with checkable expiries, so `EXCLUSIONS: e == n` holds at 2.

### Proving test

**`tests/test_coverage_loss_refusal.py::test_the_refusal_leaves_the_index_untouched`** — the one that
asserts the *index*, not the payload. Red before the change, where the build proceeds and the
`second` language's files and its stamp are both gone.

```
.venv/bin/python -m pytest tests/test_coverage_loss_refusal.py -q
```

### Rollback + porting

`git revert`. The guard is additive and defaults to the safe side; the one behaviour change is that
a full build which would silently narrow coverage now refuses, and `allow_coverage_loss=true`
restores the old behaviour for a caller who means it. One repo, no porting order.

`SCOPE: L` — unchanged, and the ticket stays open.

## Phase 3 — execute

Three commits: `7b49995` the coverage guard, `3df8c2b` the runbook facts, `f644eb6` the ticket and
the budgets.

### Axis 1 — file set

`git diff --stat 48ee6b0 <tip>` — a property of two named commits, so it is a reference point rather
than tree-under-review output (201-C1):

```
 code_atlas/indexer.py                     |  21 +
 code_atlas/tools/build_or_update_index.py |  43 +
 docs/BACKLOG.md                           |   1 +
 docs/runbooks/onboarding-a-repo.md        |  16 +-
 docs/tasks/203_…md                        | (this file)
 tests/test_agent_chain_budget.py          |   5 +-
 tests/test_coverage_loss_refusal.py       | 148 +
 tests/test_doc_size_budget.py             |   6 +-
```

Eight files against five approved rows; rows 1–2 are the two core files, row 3 the test, row 4 the
runbook, row 5 the four bookkeeping files. **diff ⊆ approved list.**

### Axis 2 — the red run (R6.5)

**The first attempt was rejected as evidence.** Reverting the core made the module fail to *import*
`COVERAGE_LOSS` — which proves the constant is new, not that the behaviour was wrong:

```
E   ImportError: cannot import name 'COVERAGE_LOSS' from 'code_atlas.indexer'
1 error in 0.08s
```

So the constant was inlined and the run repeated against the pre-fix core, exercising behaviour.
This is the run the ticket rests on:

```
FAILED test_a_full_build_refuses_to_discard_a_covered_language
FAILED test_the_refusal_leaves_the_index_untouched
FAILED test_the_refusal_names_no_route_because_no_tool_can_answer
FAILED test_the_caller_can_opt_in_to_the_narrowing
4 failed, 2 passed in 3.21s
```

The two passes are the two asserting the guard does **not** fire — a first build, and a widening
run — correctly green on both sides. After: `6 passed`.

### Axis 3 — SCOPE 1, the controlled pair

Two full builds of the anchor, back-to-back on an idle host, **same code** (this branch), same
corpus (`last_commit 61591c6`), same knobs (`workers 6`, `max_results 10`), read-only against the
sources with `CA_DB_PATH` in a scratchpad. The **only** difference is whether the target database
already held the graph. The anchor's own index was never touched.

| | wall | files/s | target DB at start |
|---|---|---|---|
| **populated** | **4,545 s · 75.8 min** | **5.41** | 1.16 GiB, 262,899 nodes / 2.08 M edges |
| **fresh** | **1,751 s · 29.2 min** | **14.03** | empty |
| | **2.60× · 46.6 min** | | |

Both runs wrote **identical** output — 24,569 files, 262,899 nodes, 2,077,473 edges — so the pair
differs in wall clock and nothing else (R4.2). For reference, [201](201_a-forced-full-rebuild-is-silent-and-unroutable.md)
measured the field rebuild at 5,470 s / 4.49 files/s against a **2.2 GiB** populated index.

**AC1's open question is settled.** The ticket asked whether the populated-DB delete is what
separates 18.7 files/s from 4.5 and said *"no fix should be chosen before it does"*. It is the
dominant term: **the starting state alone costs 2.6× — 46.6 minutes of a 75.8-minute rebuild.**

**And the pair decomposes into two distinct effects, which the single wall figure hid.** Sampling
the live lock during the fresh run:

| files done | files/s |
|---|---|
| 0 → 7,250 | **43.2** |
| 7,250 → 10,051 | 23.3 |
| 10,051 → 12,614 | 21.4 |
| 12,614 → 14,615 | 16.7 |
| 14,615 → 18,231 | 13.7 |
| 18,231 → 19,663 | 11.0 |
| 19,663 → 21,033 | 10.5 |
| 21,033 → 22,297 | **9.7** |

1. **An index-size term, present in both runs.** On an empty database the rate falls **43.2 → 9.7
   files/s** as rows accumulate. Nothing about the source files changed; the per-file write got
   dearer as `nodes`/`edges` and the `nodes_fts` trigram index grew. The populated run is **flat at
   5.41 from its first file** because it begins at the far end of this curve.
2. **A pre-existing-rows term, in the populated run only.** At comparable index size the fresh run
   still sustains ~9.7 files/s against the populated run's 5.41 — a further **~1.8×**. The fresh
   run never deletes: `replace_file_rows` (`store.py:481`) wraps `_delete_rows(path)` plus both
   inserts in one transaction, and on an empty database that delete matches nothing. This is the
   ticket's own hypothesis, and it is the residue after the size term is accounted for.

**This is the number scope 2 must now be chosen against, and it reframes the choice.** The ticket's
premise was that decode shares the writer's GIL. That may still be true, but it is not where the
hour goes: **the wall is dominated by what the write path does per file as the index grows**, and
moving `json.loads` off the writer's thread cannot touch either term measured above. A maintainer
picking between a process pool, adapter-side decode and a new framing should know that the
best case for all three is bounded by the ~29 minutes a fresh build already costs. Truncating the
tables before a full build, or deferring the FTS index, are candidates this pair makes visible and
the ticket never listed.

### Axis 4 — scope 5, both facts re-derived

`grep -n "CREATE TRIGGER IF NOT EXISTS nodes_ai" code_atlas/store.py` → `126`; the trigger block
runs `122-138`, not the `75-84` the runbook cited. The step-not-flat-fee correction takes 052's
~62 s and this ticket's own field pair (0 files = 5.5 s, 3 files = 63.8 s) — measured on the anchor
and quoted from the ticket's *Field evidence*, not re-run here (**E1**).

### Design conformance

Every row of the change list landed as designed. Two things the design did not predict, both
recorded rather than folded in: the **two-term decomposition** above, and that the fresh run is
**29.2 min, not the ~46 min I estimated earlier** — that earlier estimate came from a run sharing
the host with a `pytest` suite, which is why this pair was re-run on an idle host.

### Axis 5 — the suite

`pytest -q` in the isolated worktree, on an idle host after the pair finished:

```
2685 passed, 70 skipped in 282.24s (0:04:42)
```

Zero failures. 2,685 = the baseline's 2,677 plus this ticket's 8 (six guard cases and the two
`test_backlog_bookkeeping` params a new task file adds). **Superseded twice since**: three tests
added for the challenger's findings, then `main` merged in — the merged tree runs
`2704 passed, 70 skipped`, and **CI at the tip `f45313f` reports 2,774 passed / 0 failed / 0
skipped** on py3.12 and py3.13 with the tokens-to-answer gate green (ratio 0.835, recall 1.0,
precision 1.0). CI is the authority; the 70 local skips are this host's, not this branch's.

## Phase 4 — review

`--no-reviewer` waived the rule-book reviewer, so **no rule-book-grounded review of this diff
exists**. The ticket-blind challenger kept its seat and returned **CHANGES REQUESTED — 8 met · 3 not
met · 4 can't tell**. Both of its findings were real; each was verified in the code before being
accepted, and a third defect surfaced while fixing the first. Full verdict and response are the PR
comment; the substance:

1. **The guard covered one of five `full_build` call sites.** Two are escalations inside
   `incremental_update`, and one fires *precisely because* the adapter set narrowed
   (`_require_unchanged_scope`). A default `full=False` request — the commonest shape — still
   discarded the language silently. **The ticket's own defect, by the path the fix did not cover.**
2. **Case was folded on the configured side only.** Config keys are lowercased at load; the stamp
   comes from the adapter's announced `name`, which the contract never lowercases (unlike
   `extensions`, which it explicitly does). A mixed-case name would refuse a configured language.
3. **Mine, found while fixing 1** — and the challenger's hedge (*"writes nothing: MET for the tested
   `--full` path; not proven for the escalation paths"*) is what pointed at it.
   `incremental_update` stamps `build_complete = 0` **before** reaching `full_build`, so refusing
   there left the index marked incomplete: 202's `staleness: incomplete` for a build that never ran.
   That contradicted AC4 and this PR's own claim. The check moved ahead of every write.

All three fixed in `13ee043`, each with a red run against the previous commit. **172's
`test_a_removed_adapter_is_named_too` asserted exactly the dangerous input**, so 203 supersedes it
there: the test now asserts the refusal on the default path and 172's `scope_change` payload behind
`allow_coverage_loss=True`. Both contracts hold; the second now costs a deliberate argument.

**#251 merged first**, so this branch merged `main` in and re-measured both budget constants against
the merged tree. `BACKLOG.md` needed no raise (8,699 / 8,700); `TIER1_BUDGET` went 25,700 → 25,800
for 203's one row, measured 25,711, with R7.6 applied first and nothing left to reclaim.

### Scope reconciliation

diff ⊆ approved list (Axis 1). `contract.py`, `PLAN.md` and `CONVENTION.md` untouched, as designed.
**The ticket stays open**: scopes 2 and 4 are unattempted, with reasons in *Session status*, and the
matrix marks R2/R4/AC2/AC3/AC5/AC6 `OPEN` rather than closed.

**Ph3/4 proven by:** Axis 2's behavioural red run · Axis 3's controlled pair on the real corpus ·
Axis 5's 2,685-pass suite.

## Phase 5 — finalise

`CLAIMS: 3 claim(s) from 1 lesson entr(ies) | T1=0 T2=3 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`FALSIFY: 3 candidate(s) checked | 3 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: 0 dispatch at the time of writing · top cost driver: main loop (unmeasured — the host surfaces no usage block)`

**No `TOKEN_LEDGER.md` row.** R7.2 owes one at `done`; 203 is `in-progress`, so the row is owed by
the PR that closes scopes 2 and 4. `tests/test_backlog_bookkeeping.py` enforces exactly this.

### Claims

- **203-C1** — *a wall-clock difference can hide two independent terms, and the pair that proves the
  headline can also decompose it if you sample the run instead of only timing it.* The fresh/populated
  ratio is 2.60×, but sampling the live lock split it into an index-size term (43.2 → 9.7 files/s
  within the fresh run) and a pre-existing-rows term (~1.8× residue). The second is the one the
  ticket hypothesised; the first it never named. type: 2 · handle:
  `sample-the-run-do-not-only-time-it` · seen: 203 · recurrence 1.
- **203-C2** — *a red run that fails at import proves the symbol is new, not that the behaviour was
  wrong.* Reverting the core made the module fail to collect; that was rejected and the constant
  inlined so the run exercised behaviour. type: 2 · handle:
  `an-import-error-is-not-a-red-run` · **seen: 203 + `prove-the-guard-fails` (R6.5) — recurrence 2.**
- **203-C3** — *`ps` output filtered by a wrapper made a live process look dead, and the misreading
  put three full builds on one database.* The reliable liveness test was the artifact itself — whether
  the write lock's counter advanced. type: 2 · handle: `test-liveness-by-the-artifact-not-by-ps` ·
  seen: 203 · recurrence 1.

**203-C2 reaches recurrence 2** against **R6.5**, whose falsifier is *"a guard test whose PR claims a
defect class is prevented with no recorded red run"*. It is routed to `docs/LESSONS.md` as a
**sharpening of R6.5's existing falsifier**, not a new rule: a collection error is not a red run.
Proposed, not ratified — the rule book is the human's to change.

### Outward actions

| # | Action | Authorisation | State |
|---|---|---|---|
| 1 | push `fix/203-a-rebuild-is-gil-bound` | handover, explicit | **done** |
| 2 | open the PR | the maintainer's explicit *"open the PR for 203 once the pair finishes"* | **done** |
| 3 | merge | **not taken.** 203 is `in-progress`, and the budget lines conflict with PR #251 by design — the merge order is a decision for the maintainer | **deferred** |
| 4 | tracker transition | none | **deferred** — no tracker beyond the PR |
