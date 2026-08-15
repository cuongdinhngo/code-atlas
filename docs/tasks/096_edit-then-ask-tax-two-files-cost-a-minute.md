---
id: 096
slug: edit-then-ask-tax-two-files-cost-a-minute
title: 'A 2-file incremental costs 59 s while a no-op costs 2 s — the tax that keeps the graph out of the work'
phase: 1.5b
milestone: Cost
status: done
depends_on: [080, 052, 016]
---

## Goal
[080](080_noop-incremental-cost-and-uninterpretable-writes.md) landed and the field confirms it
exactly: a no-op incremental went from 56.1 s to **2.113 s** (~26×), `wrote.edges` from 6,071 to
**0**, two consecutive no-ops byte-identical. 080 named the general small-delta case as an explicit
follow-up. This is that follow-up, and round 5 measured its shape:

| files changed | seconds |
|---|---|
| 0 | 2.113 / 2.106 |
| 2 | **59.25** |
| 14 | 61.6 |

**The cliff is entirely between zero and one**, and above one the size of the delta barely matters.
080 removed the idle-poll tax and left the edit-then-ask tax untouched — and the edit-then-ask tax is
the one an agent actually pays, because it is levied exactly when the agent has just written code and
wants to ask about it.

## Why this is a behaviour ticket, not a performance ticket
Round 5 is the first round to show cost changing *what the agent asked*, not just what it paid:

- 16 code-atlas calls in a ~5 hour session: **8 in the opening analysis, 7 in the closing review, 1
  build in between** (§6). Across roughly three hours of actual porting the graph was asked nothing.
- The evaluator's own explanation: *"I batched my questions into two clusters because each refresh
  cost a minute, and batching is why I asked the graph nothing during the three hours when I was
  actually writing the code it could have checked."*
- One of the things it could have checked in that window was the closure count it was deriving by
  hand — the miscount that shipped into a committed comment and cost a second commit on an open PR
  (§8, §11.3).
- In-work build time: **181.7 s for 35 changed files** — roughly two orders of magnitude more wall
  clock than the session's entire code-atlas token cost (~3,050 tokens, well under 1 %).

Retro §11.7: *"If the goal is for the graph to be consulted during work rather than around it, the
sub-minute incremental for small deltas is the enabling change, not a nice-to-have."*

**Qualified the same day — cost is the *second* constraint (field interview §4).** Asked what it
would have asked at a 1 s refresh, the evaluator predicted "substantially different", checked its
transcript, and downgraded to "slightly": two real calls, both of the form *I just wrote this, is it
what I think it is*. Then the adversarial pass, which this ticket must not ignore: **the two calls it
most needed and did not make required no rebuild at all** — `file_outline` on a months-old legacy file
and `search_symbol kind:"Function"` for a name sweep. Both would have cost ~1 s at any point in the
session. *"Cost shaped my cadence; framing shaped my misses, and the misses are where the value was."*

So this ticket buys back ~5 wasted calls, one wrong belief and one follow-up commit — real, and worth
doing — but it does **not** buy adoption. Do not fund it as the adoption fix; that is
[099](099_write-time-signal-seam.md), and a read-time signal is the thing that genuinely *depends* on
this floor existing.

## Scope / Deliverables
- **Profile a small nonempty delta on a large index** and name the dominant phase, the way 052 did
  for the no-op. 080's analysis already points at full-graph `resolve_edges` / enrichment running
  regardless of delta size — confirm or refute with a phase breakdown before designing anything.
- **Scope the late writers to the delta.** 080's rejected alternative ("delta-scope `resolve_edges`
  for all incrementals, persist resolved state") is this ticket's likely core. It needs **new schema
  or persisted resolver state** — treat the schema decision as the ticket's main design question, not
  an implementation detail.
- **Set a target and state it as a target, not a hope.** Design must name the seconds a 1–5 file
  delta should cost on the anchor scale and what phase floor makes that achievable.
- **Prove correctness, not just speed.** A delta-scoped resolve must produce a graph
  byte-identical to the full-resolve path for the same tree (R4) — that equivalence is the proving
  test, and it is worth more than the timing.
- **Re-measure in the field.** Anchor-repo before/after seconds for 0 / 2 / 14 / ~273-file deltas,
  recorded here. 080's precedent applies: the operator's anchor numbers are a **confirming follow-up,
  not a merge gate** (ASSUMED-A) — the fixture proof ships with the fix.

## Constraints
- R4 — determinism is the gate: identical input must produce identical rows whichever path computed
  them. A delta-scoped resolver that drifts from the full resolver is worse than a slow one.
- R3 / schema — a persisted-resolver-state schema bump needs the mismatch-recovery path (050) to
  handle it, and the migration verdict must be written down.
- R1.1 — no language branch; resolution scoping is core mechanics.
- Full builds stay untouched (080's boundary).
- Do not absorb 080's no-op guard — it landed, it works, and this ticket must not regress it. A no-op
  must still cost ~2 s and report `wrote.edges: 0` after this change.

## Acceptance criteria
- A phase profile of a small nonempty delta on a large synthetic index is recorded in this ticket.
- A fixture test proves the delta-scoped path and the full path produce identical graph rows for the
  same tree.
- A no-op incremental still short-circuits: `wrote.edges: 0`, two runs identical (080's ACs re-run
  green).
- Anchor before/after seconds for 0 / 2 / 14 / large deltas are recorded as the confirming follow-up.
- If the schema route is rejected in design, the ticket records the rejected alternative and what the
  achievable floor is without it.

## References
Field retro round 5 §6 (required 080 measurement table), §11.7, §1 (call distribution); candidate 5.
Related: [080](080_noop-incremental-cost-and-uninterpretable-writes.md) (the no-op fix; this is its
named follow-up — see its ASSUMED-B and rejected alternatives),
[052](052_incremental-noop-cost.md) (the original profile + `scripts/profile_incremental.py`),
[053](053_refresh-on-checkout-hook.md) (inherits any floor), [016](016_incremental-git.md),
[061](061_payload-weight.md) (the standing rule that cost is a win, correctness a gate — this ticket
is the case where cost *became* a correctness cost).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 096 — edit-then-ask tax (working doc)

- **Ticket:** 096 · local-file `docs/tasks/096_edit-then-ask-tax-two-files-cost-a-minute.md`
- **Type:** core mechanics (incremental resolve scoping) + proving test
- **Repo(s) / Porting:** app only
- **SCOPE:** L
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **work_doc_mode:** embed (plain local-file ticket, hand-authored — not a scaffold stub)
- **BASELINE:** green — `scripts/docker-test.sh` on `main` @ `8be8cfb`: **1196 passed**.
- **mango version:** run under 1.10.1 (Phase 0 evidence gathered under 1.10.0, re-derived here).

---

## Phase 0 — Refine

`PREMISE: 11 reference(s) checked | 0 missing | 0 ambiguous`
`RECALL: 6 claim(s) surfaced | 1 by symbol | 2 by area | 3 does-not-apply | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise check — every source the ticket cites as already existing resolves:**
tickets 080 / 052 / 053 / 016 / 061 / 099 / 050 all exist under `docs/tasks/`;
`scripts/profile_incremental.py` exists; `resolve_edges` (`resolver.py:18`) and
`apply_indirection_rules` (`enrichment.py:91`) are the two late writers 080 named;
`_count_late_writes` (`indexer.py`) is where they run. **PREMISE HOLDS.**

**Recalled claims (advisory).** Matched: `skip-dynamic-means-unlinkable` (094-C1, **by symbol** —
this ticket edits the very `iter_unresolved_edges` that claim is about); `derived-not-listed-invariant`
(→ **R6.7**, by area); `prove-the-guard-fails` (093-C3, by area — tests). Does not apply:
`sibling-meta-non-int` (no persisted-meta shape change), `try-instead-tool-name` (no payload field),
`route-must-answer` (no route).

**HOW-decisions (resolved + cited, 0 handed back):**
1. **Where the cost is** — measured, not assumed. See the phase profile below. Cited: ticket Scope
   bullet 1 ("confirm or refute with a phase breakdown **before designing anything**").
2. **Schema or no schema** — the ticket's named main design question. `idx_edges_raw(target_raw, kind)`
   **already exists** (`store.py:91`), so the delta lookup is already indexed. Resolved: **no schema
   change**; the rejected persisted-state alternative is recorded under AC5 at design.
3. **Full builds untouched** — `resolve_edges(delta=None)` keeps today's behaviour verbatim. Cited:
   ticket Constraint 4 (080's boundary).

---

## Phase 1 — Analysis

### The phase profile (AC1)

Synthetic index, fake adapter, every file emitting **one unresolvable** `CALLS` edge with a
**unique** `target_raw` (a shared target lets the resolver dedup a 1000-key batch into one lookup
and understates `resolve` by ~15% — the first measurement made that mistake and was redone).

| index | delta | wall | `wrote.edges` | `resolve` |
|---|---|---|---|---|
| 5k files / 5k residue | 0 | 0.057 s | 0 | — (080 guard) |
| 5k | 2 | 0.095 s | 2 | < 0.015 s |
| 5k | 14 | 0.158 s | 14 | < 0.015 s |
| 20k files / 20k residue | 0 | 0.150 s | 0 | — (080 guard) |
| 20k | **2** | 0.241 s | 2 | **0.074 s** |
| 20k | **14** | 0.344 s | 14 | **0.078 s** |
| 60k files / 60k residue | 0 | 0.365 s | 0 | — (080 guard) |
| 60k | **2** | 0.793 s | 2 | **0.408 s** |
| 60k | **14** | 0.899 s | 14 | **0.405 s** |

**Verdict: 080's pointer CONFIRMED, and sharpened.** `resolve` appears the instant the delta is
non-empty and is **flat across a 7× delta change** at every scale (20k: 0.074 → 0.078 s; 60k:
0.408 → 0.405 s) while `parse` scales normally (0.023 → 0.126 s). Resolve is O(unresolved residue),
not O(delta): 3× the residue (20k → 60k) is 5.5× the resolve time, and at 60k resolve **overtakes
`tree_walk` as the single largest phase**. That is the ticket's cliff, reproduced in miniature — at
60k a 2-file delta costs **2.17×** a no-op (0.365 → 0.793 s) while 2 → 14 files adds only 13%.

**Enrichment is NOT a co-cause.** `_view_data_edges` already does indexed per-setter lookups
(`enrichment.py:160`), so it is O(rule matches), not O(graph). The one late writer that scans the
whole graph is `resolve_edges`. Scoping it is the whole ticket.

**Honest bound on this profile.** The synthetic reproduces the *shape*, not the anchor's absolute
seconds (0.074 s here vs the field's ~57 s). Per 080's ASSUMED-A precedent the anchor numbers are
the operator's confirming follow-up; the fixture proof is what ships (AC4).

### Requirements matrix

`SECTIONS: 6 found (Goal, Why-behaviour, Scope / Deliverables, Constraints, Acceptance criteria, References) | 6 decomposed | ROWS: G=2 R=5 C=5 AC=5`

| ID | Source | Verbatim (abbrev.) | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|--------------------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | cliff is entirely between zero and one; sub-minute small delta is the enabling change | Make resolve proportional to the delta | profile above: resolve flat 0.074→0.078 | CL1–CL3 | equivalence + scoped-scan test | ⬜ |
| G2 | Why-behaviour | buys back ~5 calls + one wrong belief; does **not** buy adoption | Do not scope-creep into 099's read-time signal | ticket §"Qualified the same day" | — (boundary) | no read-time signal in diff | ⬜ |
| R1 | Scope | profile a small nonempty delta; name the dominant phase **before designing** | Done in Phase 1, not Phase 2 | profile above | — (done) | recorded in ticket | ⬜ |
| R2 | Scope | scope the late writers to the delta; schema decision is the main design question | Delta-scope `resolve_edges`; enrichment already bounded | `enrichment.py:160`; `resolver.py:33` | CL1, CL2, CL3 | equivalence test | ⬜ |
| R3 | Scope | set a target, as a target not a hope | Name seconds + the phase floor | profile floor = tree_walk+announce | CL5 (doc) | target recorded | ⬜ |
| R4 | Scope | delta-scoped graph **byte-identical** to full resolve (R4) — the proving test | `snapshot()` equality, incremental vs fresh full build | `tests/test_incremental.py:73` | CL4 | proving test | ⬜ |
| R5 | Scope | anchor before/after 0/2/14/~273 recorded | Operator follow-up, not a merge gate | ticket says so explicitly | CL5 (doc) | recorded as follow-up | ⬜ |
| C1 | Constraints | R4 determinism is the gate | Drift is worse than slow | R4.2 | CL4 | equivalence test | ⬜ |
| C2 | Constraints | schema bump needs 050 recovery + written migration verdict | Only if schema route taken | `idx_edges_raw` already exists | CL5 (AC5 record) | no schema change in diff | ⬜ |
| C3 | Constraints | R1.1 — no language branch | Core mechanics only | R1.1 | CL1–CL3 | CI grep-gate | ⬜ |
| C4 | Constraints | full builds stay untouched (080's boundary) | `delta=None` ⇒ today's path verbatim | `resolver.py:18` | CL2 | full-build tests unchanged | ⬜ |
| C5 | Constraints | must not regress 080's no-op guard | no-op still short-circuits, `wrote.edges: 0` | `indexer.py` empty-delta guard | — (untouched) | 080 ACs re-run green | ⬜ |
| AC1 | AC | phase profile recorded in this ticket | Artifact | — | CL5 | table above | ⬜ |
| AC2 | AC | fixture test: delta-scoped == full, identical rows | Proving test | — | CL4 | proving test | ⬜ |
| AC3 | AC | no-op still short-circuits, two runs identical | 080 ACs re-run | — | — | `tests/test_noop_incremental.py` green | ⬜ |
| AC4 | AC | anchor before/after recorded as confirming follow-up | **Not verifiable in-session** (operator's anchor) | ticket: "not a merge gate" | CL5 | recorded as follow-up | ⬜ |
| AC5 | AC | if schema rejected, record the alternative + achievable floor | Conditional artifact — **triggered** | `idx_edges_raw` exists | CL5 | rejected-alt section | ⬜ |

`AC VALIDATION: 5 AC | 4 falsifiable in-session | 1 operator-deferred (AC4, ticket-sanctioned) | 0 unfalsifiable`
`CLARIFICATIONS: j = 0 blocking` — AC4's deferral is resolved by the ticket's own text, so no Gate 0.

### Rule sections (step 11 — union of two sources, 1.10.1)

`RULE SECTIONS: 8 applicable | 7 by change TYPE | 1 by recalled handle (h = 1) | 0 unanswered`

| Section | Source | Answer (what in *this* change it constrains) |
|---|---|---|
| R1.1 zero language branches | TYPE | Resolve scoping is language-agnostic core mechanics; no `if language ==`. |
| R1.3 dependency direction | TYPE | resolver → store, never the reverse; indexer computes the key set. |
| R1.4 SRP / store owns SQLite | TYPE | The scoped-stream SQL lands in `store.py` only; resolver passes a key set, no SQL. |
| R3.2 `contract.py` single source | TYPE | No new kind, no vocabulary change; FQN kind set read from `contract`, not re-listed. |
| R4.2 identical input → identical output | TYPE | **The ticket's own gate** — delta path must equal full path row-for-row. |
| R4.3 single SQLite writer | TYPE | Unchanged: resolve still writes in one `apply_resolution` txn. |
| R6.4 guardrail tests are real tests | TYPE | The equivalence test must be able to fail — see `prove-the-guard-fails`. |
| **R6.7 derived-not-listed** | **handle** (`derived-not-listed-invariant` recalled) | The scoped stream must derive its FQN-kind set from `contract.FQN_EDGE_KINDS`, never re-type the kinds in SQL. |

### The correctness trap this ticket turns on

A file-scoped resolve alone is **wrong**. Concretely: file A holds an unresolved edge to `\X`; the
delta adds file B declaring `\X`. A is *not* a dependent — `file_paths_targeting` matches on
`target_qname`, which is still NULL for A's edge — so A is never reparsed. A **full** resolve links
A's edge; a naive delta-scoped one does not. That divergence is exactly what C1/R4 forbids, and it
is the proving test's shape.

### Blast radius

`tests/test_sql_confinement.py` pins `len(core_modules()) == 38` (LESSONS 072) — this change adds
**no new core module**, so that guard is not invalidated. Full-build paths and 080's no-op guard are
untouched by construction.

- **Gate 1 status:** awaiting confirm

---

## Phase 2 — Design

### Approach

`resolve_edges` grows an **optional delta scope**. `delta=None` is today's behaviour byte-for-byte
(full builds, `reparse_file`) — C4 holds by construction. With a scope, the resolver streams only
the unresolved edges the delta could possibly have changed the answer for:

- **edges emitted by the parsed files** (`file_path IN to_parse`) — their rows were just re-written
  as bare, so they must resolve; and
- **edges whose lookup key the delta could now satisfy** (`target_raw IN K`), where
  `K = qnames declared by the parsed files ∪ bare names of Method nodes in them`. The second half
  is what the HEURISTIC bare-name second pass (`resolver.py:81`) matches on.
- **every non-FQN kind streams exactly as today** (INCLUDES resolves by *computed path*, not by
  `target_raw`, so a key-based scope cannot reason about it). Conservative on purpose.

**Why that is equivalent to a full resolve (C1 / R4.2).** A full resolve links an edge iff its
lookup key matches a node. For a residue edge *not* emitted by a parsed file and whose key is not
in `K`: the node set changed only inside the parsed files, so the lookup that failed last run fails
identically now — leaving it NULL *is* what the full path produces. Removals cannot turn a NULL into
a match. The one remaining dependency is `_lookup_raw`, which is a pure function of `target_raw`
**given the alias map** — so the scope is used only when the alias map is unchanged (below).

**The predicate is on the key, not on `target_raw` (review fix).** Those are not the same string:
`_lookup_raw` rewrites a raw through the alias map, whole name (`\Ns\Aka` → `\Ns\Real`) and
container (`\Ns\Aka::run` → `\Ns\Real::run`) alike. The first cut compared `target_raw` against `K`,
so an edge naming the **alias** of a class the delta declares fell out of scope in a file no delta
lists — unlinked where a full resolve links it. `delta_scope` therefore widens `K` by each key's
alias **pre-images** (backwards closure over the map, cycle-safe), which restores
`raw ∈ K ⟺ _lookup_raw(raw) ∈ K` for exactly the rewrites the lookup performs. A superset is safe:
a raw in scope that does not resolve is simply streamed and dropped, as it was before.

**Alias guard.** `alias_targets()` is snapshotted **before the parse phase** and again after
enrichment. If the two differ, the delta scope is discarded and the run does a **full** resolve.
This is exact rather than heuristic: an unchanged alias map makes `_lookup_raw` identical for every
residue edge, which is the last thing the equivalence argument needs. The scan is over the small
`ALIASES` set, not the graph — and the same map, already in hand, is what the pre-image widening
above is computed from (no third scan). **Pinning the map was necessary but not sufficient:** it
makes the rewrite stable, it does not make the scope see through it.

### Rejected alternatives

1. **Persisted resolver state / new schema column** (`resolve_attempted_at` watermark) — *the route
   the ticket assumed was required*. Rejected: it needs a schema bump, which drags in the 050
   mismatch-recovery path and a written migration verdict (C2) — **and it still needs the same
   "what did this delta add" computation** to know when to invalidate the watermark. Strictly more
   machinery for the same answer. The enabling fact is that `idx_edges_raw(target_raw, kind)`
   already exists (`store.py:91`), so the delta lookup is already indexed.
   **Achievable floor without it (AC5):** resolve becomes O(delta keys + non-FQN residue) instead of
   O(total residue), with zero schema surface and no migration.
2. **File-scoped only** — reuse the existing `file_path=` parameter. Simplest, and **incorrect**:
   the cross-file trap (Phase 1) leaves an edge unlinked that a full resolve links. Fails C1.
3. **Also scope out the kinds the resolver ignores** (`IMPORTS`, `CONTAINS` — streamed and dropped
   today). Output-equivalent and a further win, but a wider behaviour change than this ticket needs.
   **Named follow-up, not silently absorbed** (080's precedent for its own follow-up).
4. **Micro-optimise the lookup batches** — leaves the cost O(residue); the cliff survives. Not a fix.

### Target (R3) — stated as a target

- **Fixture (measurable here):** on the 20k-residue synthetic, `resolve` for a 1–5 file delta drops
  to **< 10%** of its full-scan time (0.074 s → < 0.008 s), and total wall for a 2-file delta lands
  **within 20% of the no-op floor** (0.150 s → ≤ 0.18 s, from 0.241 s).
- **Anchor (operator's confirming follow-up, AC4):** a 1–5 file delta should cost **the no-op floor
  plus parse**, i.e. **< 5 s** against the field's 59.25 s. The floor is `tree_walk` (the git collect
  walk), which 080 left at ~2 s — that phase, not resolve, is what a further ticket would attack.

### Change list (smallest set, traced to matrix rows)

| # | Change | File | Traces |
|---|--------|------|--------|
| CL1 | `node_names_in_files(paths, *, kind)`; delta predicate in `_iter_unresolved_edges` | `code_atlas/store.py` | R2, C3 |
| CL2 | `DeltaScope` + key computation (incl. alias pre-images) + `delta=` param; `delta=None` unchanged | `code_atlas/resolver.py` | R2, C4 |
| CL3 | alias-stability snapshot; pass the scope through `_count_late_writes` | `code_atlas/indexer.py` | R2, C1, C5 |
| CL4 | proving tests (equivalence ×2, alias reach ×2, alias fallback, scope-actually-narrows) | `tests/test_delta_resolve.py` | R4, AC2, AC3 |
| CL5 | ticket Resolution (profile, target, rejected alt, follow-up), PLAN §19, BACKLOG, LESSONS | docs | R1, R3, R5, AC1, AC4, AC5 |

**No new core module** — `tests/test_sql_confinement.py`'s `len(core_modules()) == 38` stays valid.

### Rule-compliance check

`RULE SECTIONS: 8 applicable | 8 answered | 0 unanswered`

- **R1.1** — no `if language ==`; resolve scoping is language-agnostic. ✅
- **R1.3** — resolver imports store; store never imports resolver. ✅
- **R1.4** — all SQL in `store.py`; the resolver passes a key set and the kind set, writes no SQL. ✅
- **R3.2** — no new kind, no vocabulary change; the FQN kind set is **passed in from
  `contract.FQN_EDGE_KINDS`**, never re-typed in `store.py`. No `contract_version` bump. ✅
- **R4.2** — the equivalence test is the gate; the alias guard pins the map and the pre-image widening closes the reach through it (both found in review, both proven by sabotage). ✅
- **R4.3** — single writer unchanged; resolve still commits via one `apply_resolution`. ✅
- **R6.4** — the guard is made to fail: test 4 asserts the scoped stream is strictly smaller than the
  full stream, so an inert "optimisation" fails the suite (`prove-the-guard-fails`, 093-C3). ✅
- **R6.7** (applicable via recalled handle `derived-not-listed-invariant`) — `store.py` re-lists **no**
  kinds; the scoped-kind set is derived at the call site from `contract.FQN_EDGE_KINDS`. ✅

`HANDLES: 3 recalled | 3 answered | 0 unanswered`

| Handle | Answer |
|--------|--------|
| `skip-dynamic-means-unlinkable` (094-C1, by symbol) | **traced** — the delta predicate is ANDed with the existing `skip_dynamic` clause, never replaces it; test 4's fixture keeps a DYNAMIC `REFERENCES` row and asserts it still streams. |
| `derived-not-listed-invariant` (→ R6.7) | **traced** — kind sets derived from `contract`, passed in; no literal kind list added to `store.py`. |
| `prove-the-guard-fails` (093-C3) | **traced** — test 4 exists precisely so a no-op scope fails. |

### Proving test

`pytest tests/test_delta_resolve.py::test_delta_resolve_links_residue_a_new_file_satisfies`

Fails pre-096 only if the scope is naive; the *point* of the test is that the shipped scope keeps
the graph identical to a full build in the exact case a file-scoped resolve gets wrong. Companion:
`test_delta_scope_actually_narrows_the_scan` (else the change is inert), plus the existing
`tests/test_noop_incremental.py` re-run green for AC3/C5.

### Verification plan

1. `scripts/docker-test.sh` — full gate green, no test removed.
2. Re-run the 20k synthetic profile; record before/after in the ticket (AC1 + target).
3. `tests/test_noop_incremental.py` green (080 not regressed, C5).

- **Gate 2 status:** awaiting confirm

---

## Phase 3 — Execute

- **Branch:** `fix/096-edit-then-ask-tax` (first cut as `perf/`, corrected — `perf` is not in
  `branch_strategy`'s `feat|fix|chore|docs`).
- **Proving test added:** `tests/test_delta_resolve.py`
- **Verification sweep:** file axis ✅ — diff is exactly CL1–CL5, nothing outside the approved list.
  - R1.1 grep: no `if language ==` under `code_atlas/` ✅
  - R1.4 grep: SQL appears in `store.py` only ✅
  - R6.7 grep: **zero** edge-kind literals added to `store.py` by this diff — `scoped_kinds` arrives
    from `contract.FQN_EDGE_KINDS` via the caller ✅
- **Guard proven to fail (093-C3, empirical not asserted):** with `delta_scope`'s key set stubbed to
  `set()` — a file-only scope — **5 of 8 tests fail** (re-measured after review), including both
  equivalence tests and both alias tests. Restored, 8/8 pass. The proving test therefore measures
  the thing it claims to.
- **Empirical:**

```
$ scripts/docker-test.sh
# baseline (main @ 8be8cfb): 1196 passed
# post-change:               1202 passed  (+6 new tests, none removed)
# after the second review:   1204 passed  (+2 alias-reach tests)
# ruff + mypy: green
```

---

## Resolution

**Where the cost was.** 080's pointer confirmed and narrowed: of the two late writers, only
`resolve_edges` scans the whole graph. `apply_indirection_rules` is already O(rule matches) via
indexed per-setter lookups (`enrichment.py:160`), so it is **not** a co-cause. `resolve` measured
**flat across delta size** at both scales — O(residue), not O(delta).

**The fix.** `resolve_edges` takes an optional `DeltaScope`. `delta=None` is today's path
byte-for-byte (full builds, `reparse_file` — C4). With a scope it streams only unresolved edges
that are emitted by the parsed files **or** whose `target_raw` is a key the delta now declares
(`qnames_in_files` ∪ bare `Method` names, the two halves of the lookup surface, ∪ the **alias
pre-images** of both — `_lookup_raw` reaches a key through the alias map, so a scope that did not
invert that rewrite skipped an edge naming an alias of the delta's class). Non-FQN kinds stream
unscoped, because `INCLUDES` resolves by *computed path*, which a key-based scope cannot reason
about.

**Why keyed on declarations, not files.** File A can hold an unresolved edge to a class file B
adds. A is **not** a dependent — `file_paths_targeting` matches `target_qname`, still NULL — so a
file-scoped resolve leaves it unlinked forever while a full resolve links it. The key set is what
makes the scope equivalent, and stubbing it out fails 5 of 8 tests.

**The bound.** Equivalence holds only while the alias map is fixed (`_lookup_raw` is key-pure given
that map). The map is snapshotted **before the parse** — after would already contain the new rows
and silently miss the change — and any difference falls back to a full resolve. **Pinning it is not
sufficient** (review): a fixed map still *rewrites*, so the key set carries each key's alias
pre-images. Reverting that widening fails two tests and only those two.

### Measured (AC1, and the target from Phase 2)

| index | delta | wall before → after | `resolve` before → after |
|---|---|---|---|
| 20k residue | no-op | 0.150 → 0.153 s | — (080 guard, both) |
| 20k | 2 files | 0.241 → **0.187 s** | 0.074 → **0.0089 s** (8.3×) |
| 20k | 14 files | 0.344 → 0.314 s | 0.078 → ~0.01 s |
| 60k residue | no-op | 0.365 → 0.387 s | — (080 guard, both) |
| 60k | **2 files** | 0.793 → **0.421 s** (1.88×) | 0.408 → **0.0197 s** (**20.7×**) |
| 60k | 14 files | 0.899 → **0.541 s** | 0.405 → **0.0246 s** |

**Against the stated target, honestly scored:**

- 60k (where `resolve` was the largest phase): resolve is **4.8%** of its former time — target was
  < 10% ✅; 2-file wall is **8.8%** above the no-op floor — target was ≤ 20% ✅.
- 20k: resolve is **12%** of former (target < 10% ❌ **missed**); 2-file wall is **22%** above the
  floor (target ≤ 20% ❌ **missed**). Not restated to fit: at 20k `tree_walk` (0.091 s) dominates and
  `resolve` never was the bottleneck, so there was less to win than the target assumed.

**The benefit scales with the residue** — which is the diagnosis working as predicted, and means the
anchor (far larger residue than 60k) should see more than the 20.7× measured here, not less.

**What is *not* claimed.** Resolve is not O(1) in the residue: 20k → 0.0089 s, 60k → 0.0197 s, still
residue-dependent but sub-linear. What was removed is the **per-edge lookup work** (`nodes_by_
qualified_names` + the bare-name second pass + sibling inserts) for edges the delta cannot affect;
what remains is a single filtered index scan, ~20× cheaper. Making *that* proportional would mean
attacking `tree_walk`, which is now the largest phase in every row above.

### Rejected alternatives (AC5 — the schema route **was** rejected)

1. **Persisted resolver state / new schema column** (the route the ticket assumed was required).
   Rejected: needs a schema bump → 050 mismatch-recovery + a written migration verdict (C2), **and
   still needs the same "what did this delta declare" computation** to invalidate the watermark.
   Strictly more machinery for the same answer. **Achievable floor without it:** exactly the table
   above — 20.7× on resolve at 60k, no schema surface, no migration.
2. **File-scoped only** — incorrect (the cross-file trap). Fails C1/R4.2.
3. **Also scope out the kinds the resolver ignores** (`IMPORTS`, `CONTAINS` are streamed and then
   dropped today). Output-equivalent and a further win on a `use`-heavy PHP repo. **Named follow-up**,
   not absorbed — it widens the behaviour change beyond what this ticket needs.
4. **Micro-optimise the lookup batches** — leaves the cost O(residue); the cliff survives.

### Follow-ups (named, not silently dropped)

- **Anchor re-measure (AC4)** — 0 / 2 / 14 / ~273-file deltas on the anchor monorepo. Operator's,
  per 080's ASSUMED-A precedent; a confirming follow-up, not a merge gate.
- **Scope out resolver-ignored kinds** (rejected alt 3).
- **`tree_walk` is now the floor** — 0.28 s of the 0.42 s 2-file wall at 60k. Any further cut to the
  edit-then-ask tax is a git-collect ticket, not a resolver one.

- **Gate 3 status:** cleared (autonomous) → review

---

## Phase 4 — Review ✋

Challenger **waived** at solve invocation (`with skipped challenge`). Reviewer pass run in the
main loop (0 dispatch — this host does not surface subagent usage, so a dispatched row would have
read `unmeasured` regardless).

**Verdict: CHANGES REQUESTED → fixed → clean.** One real defect, found by reading the diff against
the rule book rather than by the tests:

- **`code_atlas/indexer.py` — enrichment's rows were never resolved under a delta scope.**
  `apply_indirection_rules` deletes and re-inserts every rule row *after* the parse, always bare,
  under the synthetic `INDIRECTION_FILE` path. That path is never in `to_parse`, and the rows'
  `target_raw` need not be a key the delta declares — so a fresh `ALIASES` row stayed
  `target_qname: NULL` on every incremental while a full build linked it. Reproduced as a snapshot
  diff (`ONLY INCREMENTAL: ('ALIASES','\Facade',None,'\Dup',…)` vs `ONLY FULL: (…,'\Dup',…)`),
  then fixed by putting the bookmark in scope unconditionally.
  **Why the equivalence tests missed it:** every fixture in `test_delta_resolve.py` was built
  without indirection rules, so the bookmark had no rows to leave behind. The suite gained
  `test_enrichment_rows_resolve_under_a_delta_scope`, which fails without the fix.

**Second review pass (on the PR, maintainer-requested).** One further real defect, same class as
the first — an equivalence hole the tests could not see:

- **`code_atlas/resolver.py` — the scope compared `target_raw`, but the lookup key is
  `_lookup_raw(target_raw)`.** That function rewrites a raw through the alias map, whole name
  (`\Ns\Aka` → `\Ns\Real`) and container (`\Ns\Aka::run` → `\Ns\Real::run`). So an edge naming
  the **alias** of a class the delta declares was out of scope — in a file no delta lists, its key
  never compared — and stayed `target_qname: NULL` where a full resolve linked it. Reproduced as a
  control/scoped pair on a seeded store (full resolve links `\Ns\Real`; scoped left `None`), then
  fixed by widening the key set with each key's **alias pre-images** (backwards closure over the
  map, cycle-safe). The map is already in hand from the stability snapshot, so there is no extra
  scan.
  **Why the equivalence tests missed it:** no fixture in `test_delta_resolve.py` had an `ALIASES`
  row *and* a residue edge naming the alias — the alias work in the suite was the fallback guard,
  which is the map **changing**, not the map being **traversed**.

All three fixes were re-proven by sabotage, not assertion: stubbing the key set fails 5 of 8 tests;
reverting the bookmark scope fails its regression test alone; reverting the alias pre-images fails
the two new alias tests and only those two.

- **Reviewed at:** `0128f64` + the review fix, then `58341b3` + the alias fix (files: `store.py`,
  `resolver.py`, `indexer.py`, `tests/test_delta_resolve.py`)
- **Ph3/4 proven by:** `tests/test_delta_resolve.py` (8 tests) · `tests/test_noop_incremental.py`
  (080's ACs, green) · Docker full gate (**1204 passed**)

## Phase 5 — Finalise ✋

- Planned outward actions (standing AGENTS.md approval + this solve): commit, push branch, open PR.
- Durable lesson: `docs/LESSONS.md` — 096 entry + claims 096-C1/C2/C3/C4.
- Revert: revert the PR commit; `delta=None` restores the prior path exactly.

### Learning loop

`CLAIMS: 3 claim(s) from 1 lesson entry | T1=0 T2=3 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded | 0 promotion candidate(s)`
`FALSIFY: 3 candidate(s) checked | 3 still-true | 0 falsified | 0 not cheaply checkable`
`PROMOTION: 0 proposed (all three are seen: 096 only — one sighting each)`

All three claims are new handles at n = 1, so none is a promotion candidate; `/mango:promote` is
the cross-ticket pass when a second sighting arrives.

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| — | none dispatched (challenge waived; main-loop only) | — | n/a — 0 dispatches | RTK present, not depended on |

`LEDGER TOTAL: 0 dispatches, so 0 rows — the ledger is complete, not empty by omission.`
`Top cost driver: the synthetic-index profiling runs (5k/20k/60k, before and after), not the diff.`

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Gate 1 | proceed; AC4 recorded as operator-deferred | ticket calls it a confirming follow-up, not a merge gate |
| Gate 2 | delta scope keyed on declarations; **no schema** | `idx_edges_raw` already indexes the lookup; watermark route needs the same computation plus a migration |
| Ph3 | branch renamed `perf/` → `fix/` | `perf` is not in `branch_strategy` |
| Gate 4 | review found the enrichment gap; fixed + regression test | equivalence is the gate (C1/R4.2) |
| final | commit + push + PR | AGENTS.md standing + this solve |

## Session status

- **Last updated:** 2026-08-15
- **Current phase:** finalise
- **work_doc_mode:** embed · `docs/tasks/096_edit-then-ask-tax-two-files-cost-a-minute.md`
- **Next action:** open the PR
- **Blocked on:** none
