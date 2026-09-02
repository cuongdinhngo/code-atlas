---
id: 212
slug: an-incremental-update-escalates-on-correctness-but-never-on-cost
title: "`incremental_update` escalates to a full build only when a delta would be *wrong*, never when it would be slower than one — and no change is ever classified as too small to re-parse"
phase: 1.5b
milestone: Freshness
status: done
depends_on: [030, 052, 080, 096, 172, 202]
---

## Why this exists

`incremental_update` (`code_atlas/indexer.py:254`) has exactly three routes to `full_build`, and all
three are correctness arguments:

| trigger | line | why |
|---|---|---|
| `build_incomplete(store)` | 275 | a graph left mid-write cannot be extended (202) |
| `contract_rebuild_required(store)` | 275 | vocabulary era changed; a delta would mix eras (030) |
| `_ScopeChanged` | 373-380 | a suffix entered scope the git diff cannot name (172) |

Each is right. Together they are the complete list, and **cost is not on it.** The decision is
binary — this delta, or everything — with nothing in between and no floor beneath it:

- **No upper tier.** A branch touching 5,000 files runs as a delta: re-parse, re-link, reconcile,
  per changed file. Whether that is cheaper than one full build is never asked, and past some
  fraction of the repo it certainly is not.
- **No lower tier.** A commit that reformats whitespace, edits comments, or changes only string
  literals re-parses every touched file, because nothing compares *what changed inside* a file
  against what the graph stores. The no-op skip at the end of the function
  (`if to_parse or removed:`) catches a delta that turned out empty **after** the parse, not one
  that could have been predicted empty before it.

The consequence is the one the anchor's operator hit: a full rebuild takes about an hour, and the
only alternative on offer is a delta whose cost nobody can predict either. Neither number is
knowable before committing to one.

### Why this is not the rebuild-speed ticket

Making a full build faster and doing fewer full builds are different work. A ticket for the first
(the parallelism ceiling in a full rebuild) was drafted for this repo and **is not in the tree** —
`docs/tasks/` has 200, 201, 202, 204 and nothing at 203. This ticket does not replace it and does
not depend on it: even at half the wall-clock, choosing the cheaper of two routes and skipping work
that cannot move the graph are still wins, and they are wins that arrive without touching the
parallelism model.

### Prior art, and the part that transfers

The reference implementation surveyed in the user's notes classifies each update before acting —
roughly *skip* (cosmetic), *partial*, *architecture-level* (directories added or removed), *full*
(beyond a fraction of the repo) — and hashes each file's declarations so a cosmetic edit is
provably cosmetic. The tiering and the declaration fingerprint transfer directly. Its thresholds do
not: they are that project's constants, and **R2.3** says sample repos drive targets, never
behaviour. Measure this repo's crossover point instead of importing a number.

## Scope

1. **Measure the crossover first.** On the anchor, time `incremental_update` against `full_build`
   across a range of delta sizes and find where the delta stops being cheaper. Everything below
   depends on this number existing; without it a threshold is a guess.
2. **An upper tier.** Above the measured crossover, escalate to `full_build` for cost, recorded in
   the `scope` dict beside the three correctness escalations so the report can name why — the
   pattern 172 established.
3. **A lower tier: a change that cannot move the graph is not parsed.** A per-file fingerprint over
   the declarations the graph stores — symbols, signatures, imports, call targets — lets a file whose
   fingerprint is unchanged be skipped. Whitespace and comment edits are the case that pays for it.
4. **The route is always reported.** Every build says which tier it took and why. A cost escalation
   must never look like a correctness one, and a skipped file must never look like an indexed one.
5. **Never skip on a correctness route.** The three existing escalations outrank any cost tier; a
   contract-era change re-parses everything regardless of fingerprints.

### Explicitly not in scope

- **Full-build parallelism.** The absent ticket's subject; independent of this one.
- **Changing what a delta indexes** when it does run. Same collect, same link, same reconcile.
- **Cross-run caching of parse results.** A fingerprint decides whether to parse; it does not store
  what the parse produced.

## Constraints

- **R2.3** — thresholds come from measuring this repo, never from the reference implementation's
  constants.
- **R5.5 — a reported value is sourced from the computation that owns the whole fact.** The tier is
  decided in one place and reported from it, not re-derived by the reporter.
- **R4.2** — the resulting graph is identical whichever route was taken. This is the ticket's central
  risk: a fingerprint that misses a construct silently under-indexes, and the index still reports
  current. Guard it directly (AC5).
- **R6.5** — the fingerprint guard ships only once observed failing: construct a file whose text
  changes, whose declarations do not, and prove the graph is identical either way; then one whose
  declarations do change, and prove it is not skipped.
- **R5.3** — a fingerprint that cannot be computed fails loud into "parse it", never into "skip it".
- **202's lesson applies verbatim:** a build that did less work must not leave an index that reports
  as though it did more.

## Acceptance criteria

1. The crossover measurement exists, is recorded with its method, and the upper-tier threshold cites
   it.
2. A delta above the threshold escalates to a full build and the report names cost — distinguishable
   from the three correctness routes.
3. A file whose declarations are unchanged is not re-parsed, and the graph is byte-identical to a
   run that did re-parse it.
4. A file whose declarations changed is never skipped, proven by a fixture that fails without the
   guard.
5. A fingerprint that cannot be computed results in a parse, and a test exhibits that path.
6. Every build reports its tier; no tier is inferable only from timing.
7. The three existing correctness escalations are unchanged and still take precedence, pinned by a
   test.

## References

[030](030_alias-indirection-edges.md) (the escalation the code cites at indexer.py:275), [052](052_incremental-noop-cost.md)
(the phase-timing the code cites for `phase_times`, and Scope 1's measuring surface), [080](080_noop-incremental-cost-and-uninterpretable-writes.md) (the no-op floor
and the 6,071-edge finding — the closest prior work), [096](096_edit-then-ask-tax-two-files-cost-a-minute.md) (why a
delta-scoped resolve is equivalent only under a fixed alias map),
[172](172_incremental-is-blind-to-a-scope-change.md) (the `scope` reporting pattern this reuses),
[202](202_a-killed-build-leaves-an-index-that-reports-current.md) (an index that reports current
after doing less work).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 212 · **work_doc_mode:** embed · **Current phase:** 5 finalise — complete on disk. PR [#256](https://github.com/cuongdinhngo/code-atlas/pull/256) open on `main`. **Next action:** merge #256. **Revert path:** `git revert` the three commits on `feat/212-…`, or close #256 unmerged — the knob's default is 0, so the revert is a no-op for every existing caller. The split's other half is [213](213_a-declaration-fingerprint-so-a-cosmetic-edit-is-not-reparsed.md), which stays open.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` (after the ratified split; **L** as filed) ·
  `STRUCTURE: native` · **Type:** enhancement.
- Run arg *"with skipped reviewer"* = `--no-reviewer`; reviewer waived, **challenger keeps its seat**.
- Branch `feat/212-…`, based on `main` at `234a8e8` — 208's merge, so this branch carries 205 and 208.
- **THE TICKET WAS SPLIT, and the maintainer ratified the split in conversation.** This branch is
  Scopes 1, 2, 4 and 5. Scope 3 (the declaration fingerprint) is its own ticket — see W3 below.
- Contract `.mango/run-contract-212.txt` (t0 record kept at `.mango/run-contract-212.t0.txt`).
  RECONCILE t0: 9 declared | 7 re-run | **0 holding** | 7 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 11 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 4 by handle | 1 by area | 0 by finding | 6 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 3 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

Every reference resolved: the three escalation routes (`indexer.py:318-336` for
`build_incomplete` + `contract_rebuild_required`, `:417-427` for `_ScopeChanged`), the no-op skip
(`if to_parse or removed:`), `phase_times` (052's profiler at `scripts/profile_incremental.py`), and
the six referenced tickets. The one ambiguous reference is the ticket's own aside that *"`docs/tasks/`
has 200, 201, 202, 204 and nothing at 203"* — **203 exists now** (merged as #252/#253 earlier today,
and it is the rebuild-speed work the aside says is absent). The aside's *conclusion* is unaffected:
this ticket still does not depend on it.

### The ticket's premise is partly false, and the correction shrinks the work

> *"**No lower tier.** A commit that reformats whitespace, edits comments, or changes only string
> literals re-parses every touched file, because nothing compares what changed inside a file against
> what the graph stores."*

There **is** a lower tier. `incremental_update` has a `hashing` phase (`indexer.py:386-404`) that
calls `file_is_current(store, root, path)` (`:568-571`) — a **content-hash** gate comparing the
file's current bytes against the hash the index stored — and skips the parse when they match. A
dependent is deliberately excluded from the skip, with the reason in a comment. The ticket's own
sentence, *"nothing compares what changed inside a file"*, is not true at byte grain.

What is genuinely missing is a tier **above** the byte hash: a fingerprint over the *declarations*
the graph stores, so an edit that changes bytes without changing declarations is skipped. That gap is
real, and the ticket's three examples are exactly the cases the byte hash cannot catch.

### Settled wants — asked and answered by the maintainer

| # | The want | Answer | Consequence |
|---|---|---|---|
| W1 | Scope 1 needs a crossover measured on the anchor. Doing it with real controlled deltas means adding and removing a worktree inside a **work repo's** git state; deriving it from `phase_times` costs one timed full build plus a few small deltas and touches no git state | **Derive from `phase_times`** | The method is recorded with the numbers so anyone can repeat it. 052's profiler is the measuring surface, and it restores every file it touches |
| W2 | Scope 3's fingerprint cannot be computed without parsing, and a comment- or string-literal-aware normaliser is a **language branch**, which **R1.1** forbids in the core | **A language-agnostic whitespace-normalised hash** — catches reformatting, *not* comment or string-literal edits | The narrowing is stated in 212b's own ticket rather than discovered at its review |
| W3 | As filed this is an **L** ticket: a measurement campaign, two escalation tiers, a fingerprint and a reporting surface. mango's *outgrew-its-ticket* nudge says stop and re-scope or split | **Split.** 212 keeps Scopes 1, 2, 4, 5; the fingerprint becomes its own ticket | ACs 3, 4 and 5 leave this ticket as ⚠ deferred rows pointing at the follow-up — mango's own mechanism for a deferred requirement, not a silent drop |

### Resolved direction + citation

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | Which number does the cost tier compare against the threshold — `len(changed)` or `len(to_parse)`? | **`len(to_parse)`**, decided immediately after the `hashing` phase. It is the exact work the delta would do, so it composes with the byte-hash tier: a 5,000-file change whose files are byte-identical correctly does **not** escalate. `len(changed)` is cheaper to reach but wrong in that case, and the report carries both | `indexer.py:386-404`; ticket Scope 2 (*"above the measured crossover"*) |
| H2 | How does the route reach the caller? | **`scope[…]`, exactly as 172 did.** `build_or_update_index.py:310` is `return (FULL if scope else INCREMENTAL), report` and `:238` is `result.update(scope)` — so a new key makes the payload report `mode: full` **and** name the route, with no reporting code of its own. AC2 and AC6 come through the pattern the ticket told me to reuse | `build_or_update_index.py:238,310`; `indexer.py:322-332`; ticket Scope 2 |
| H3 | How is precedence over the three correctness routes guaranteed? | **Structurally.** `incomplete`/`era_moved` return before the announce, and `_ScopeChanged` is raised during it — all three are upstream of the `hashing` phase where the cost decision sits, so a correctness route cannot be overtaken. Pinned by a test rather than left to reading | `indexer.py:318-336`, `:417-427`; ticket Scope 5, AC7 |
| H4 | Where does the threshold live? | **A named config setting** (`full_build_crossover`, env `CA_FULL_BUILD_CROSSOVER`) whose default cites the measurement in a comment — the 124 precedent (`orphans_max_nodes`), and the answer **R2.3** demands: measured here, never imported from the reference implementation | `config.py:210-212` (the 124 pattern); ticket Constraint R2.3 |

**Constraints surfaced from the scan** (not in the ticket):

- The cost decision cannot be free: it sits after `announce`, `tree_walk`, `reconcile` and `hashing`,
  so an escalating build pays those four phases twice. The measurement below prices that, and the
  report names it rather than hiding it.
- `_reconcile(store, kept)` **writes** (it removes rows) before the escalation point. That is safe
  only because `full_build` re-indexes every collected file afterwards — noted so the next reader
  does not have to re-derive it.

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `202-C4` one-field-two-questions | 2 | handle | **Yes** — a cost escalation must be its own `scope` key, never a `cause` field on a shared one. Fourth sighting was 205 |
| 2 | `196-C1` gate-on-the-invariant-not-on-presence | 2 | handle | **Yes** — the tier gates on the parse count, not on the presence of a `changed` list |
| 3 | `205-C2` a-capped-search-is-not-a-search | 2 | handle | **Yes, and it fired twice more this ticket** — every search here went through `rtk proxy` |
| 4 | `208-C1` pin-the-arrival-not-the-current-number | 2 | handle | Surfaced; **does not apply** — no versioned document moves in this diff |
| 5 | `052`/`080`'s recorded floor | 5 | area (indexer / incremental cost) | **Yes** — 052 measured a **62.296 s** no-op and **61.585 s** for 21 files, i.e. a flat fee with a negligible per-file cost at small N. That shape is what makes a crossover exist at all, and 080 then cut part of the floor |

## Phase 1 — analysis

`PREMISE: 11 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 4 by handle | 1 by area | 0 by finding | 6 retired skipped — advisory (blocks nothing)`
`SECTIONS: 6 found (Why this exists [+ Why this is not the rebuild-speed ticket, + Prior art], Scope [+ Explicitly not in scope], Constraints, Acceptance criteria, References) | 6 decomposed | ROWS: C=6 R=8 G=4 AC=7`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 8 applicable — 5 by change-type | 3 by recalled handle — §1 (change-type) ✅ · §2 (change-type) ✅ · §3 (change-type) N/A (no node/edge vocabulary, field or qname rule moves; the contract module is untouched and no adapter is asked for anything new) · §4 (recalled handle: one-field-two-questions → R5.6's neighbour) ✅ · §5 (recalled handle: source-the-caveat-from-the-computation → R5.5, do-not-attest-past-the-payloads-resolution → R5.6) ✅ · §6 (recalled handle: prove-the-guard-fails → R6.5) ✅ · §7 (change-type) ✅ · §8 (change-type) N/A (no dependency added, moved or removed)`
`TRACK: backend — 0/6 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

Both lines above `SECTIONS:` are carried forward from Phase 0.

### BASELINE

`.venv/bin/python -m pytest -q`, **Ran at 234a8e8** — this branch's point, which carries 205 and 208:

```
2780 passed in 269.80s (0:04:29)
```

Carried forward from 208's own delta-green run at `c065232`, whose tree is `234a8e8`'s content for
every file this ticket touches (`git diff c065232 234a8e8 -- code_atlas/ tests/` is empty — the merge
commit changed no file). Re-run at the reviewed SHA in Phase 3 rather than trusted here.

### The defect, classified

`logic` (`config.cause_taxonomy`) at `code_atlas/indexer.py:296-460`: the escalation set is a
complete list of **correctness** arguments and cost is not on it, so the route is chosen without ever
comparing the two costs. The ticket's *"no upper tier"* is exactly right. Its *"no lower tier"* is
not — see Phase 0 — and the correction is what turned an L ticket into two.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why this exists | "all three are correctness arguments… **cost is not on it**" | The escalation list has no cost member | `indexer.py:318-336`, `:417-427` | | | ⬜ |
| G2 | Why this exists | "**No upper tier.** A branch touching 5,000 files runs as a delta" | Nothing compares delta cost against full-build cost | the measurement below | | | ⬜ |
| G3 | Why this exists | "**No lower tier.**… nothing compares *what changed inside* a file" | **Partly false**: a byte-hash tier exists (`indexer.py:386-404`). The declaration-grain gap is real and is 213 | `file_is_current` at `:568-571` | | | ⬜ |
| G4 | Why this exists | "a full rebuild takes about an hour, and the only alternative… a delta whose cost nobody can predict" | Both numbers are now measured, and the rebuild is **550 s**, not an hour | the measurement below | | | ⬜ |
| R1 | Scope 1 | "Measure the crossover first" | Done, with its method | | | | ⬜ |
| R2 | Scope 2 | "An upper tier… escalate to `full_build` for cost, recorded in the `scope` dict" | A fourth escalation route beside the three | | | | ⬜ |
| R3 | Scope 3 | "A lower tier: a change that cannot move the graph is not parsed" | **⚠ deferred to [213]** — split ratified at Gate 0 (W3) | | | ⚠ |
| R4 | Scope 4 | "The route is always reported" | Through 172's `scope` pattern (H2) | | | | ⬜ |
| R5 | Scope 5 | "Never skip on a correctness route" | The cost tier is downstream of all three, structurally (H3) | | | | ⬜ |
| R6 | Not in scope | "Full-build parallelism" | Untouched — and 203 shipped it today, independently | | | | ⬜ |
| R7 | Not in scope | "Changing what a delta indexes when it does run" | Same collect, link and reconcile; only the route choice is new | | | | ⬜ |
| R8 | Not in scope | "Cross-run caching of parse results" | Nothing is cached | | | | ⬜ |
| C1 | Constraints | "**R2.3** — thresholds come from measuring this repo" | The default cites the measurement in the line above it | | | | ⬜ |
| C2 | Constraints | "**R5.5** — the tier is decided in one place and reported from it" | One decision site; the reporter reads `scope` | | | | ⬜ |
| C3 | Constraints | "**R4.2** — the resulting graph is identical whichever route was taken" | An escalation runs the ordinary `full_build`, so the graph is a full build's by construction | | | | ⬜ |
| C4 | Constraints | "**R6.5** — the fingerprint guard ships only once observed failing" | Applies to 213. For this ticket: the cost guard is observed failing | | | ⚠ |
| C5 | Constraints | "**R5.3** — a fingerprint that cannot be computed fails loud" | 213's | | | ⚠ |
| C6 | Constraints | "**202's lesson**: a build that did less work must not leave an index that reports as though it did more" | An escalating build does **more** work, and says so | | | | ⬜ |
| AC1 | Acceptance criteria | "The crossover measurement exists, is recorded with its method, and the upper-tier threshold cites it" | Below, and the default's comment cites it | | | | ⬜ |
| AC2 | Acceptance criteria | "A delta above the threshold escalates… and the report names cost — distinguishable from the three correctness routes" | A fourth `scope` key | | | | ⬜ |
| AC3 | Acceptance criteria | "A file whose declarations are unchanged is not re-parsed…" | **⚠ deferred to [213] AC1** | | | ⚠ |
| AC4 | Acceptance criteria | "A file whose declarations changed is never skipped…" | **⚠ deferred to [213] AC2** | | | ⚠ |
| AC5 | Acceptance criteria | "A fingerprint that cannot be computed results in a parse…" | **⚠ deferred to [213] AC3** | | | ⚠ |
| AC6 | Acceptance criteria | "Every build reports its tier; no tier is inferable only from timing" | 172's pattern; the payload's `mode` already flips on a non-empty `scope` | | | | ⬜ |
| AC7 | Acceptance criteria | "The three existing correctness escalations are unchanged and still take precedence, pinned by a test" | Structural precedence, pinned | | | | ⬜ |

Status legend: ✅ done/proven · ⚠ deferred (needs follow-up ticket) · ❌ not met.

**Four rows are ⚠ and every one of them points at [213](213_a-declaration-fingerprint-so-a-cosmetic-edit-is-not-reparsed.md)**, the ticket the ratified
split created. That is mango's own mechanism for a deferred requirement — a named follow-up carrying
the row, not a silent drop.

### Clarifications, all four self-resolved

1. *The ticket says no lower tier exists.* One does, at byte grain — Phase 0, cited to
   `indexer.py:386-404` and `:568-571`. The declaration-grain gap is real and is 213's subject.
2. *The ticket says `docs/tasks/` has "nothing at 203".* It does now — 203 merged earlier today as
   the rebuild-speed work the aside says is absent. The aside's conclusion (this ticket does not
   depend on it) is unaffected.
3. *"a full rebuild takes about an hour"* — measured at **550 s** (9 m 10 s) on the anchor today.
   203's own ledger row independently measured **594 s** after its index fix, against **4,545 s**
   before it. The ticket's "about an hour" is the pre-203 number, and 203 landing today is what moved
   it. Recorded, and it moves the crossover a long way in.
4. *Which count does the threshold compare?* H1 — `len(to_parse)`, after the hashing phase.

### Universal inventory — N = 6 sites

| # | Site | What must happen |
|---|---|---|
| 1 | `config.py` | `full_build_crossover` + `DEFAULT_FULL_BUILD_CROSSOVER`, whose comment cites the measurement (R2.3) |
| 2 | `config.py` `_FILE_KEYS`/`Config` | the setting joins the resolved set, so `CA_FULL_BUILD_CROSSOVER` works like every other knob |
| 3 | `indexer.py` | the `DELTA_TOO_LARGE` key + route constant |
| 4 | `indexer.py` `incremental_update` | the decision, immediately after `hashing`, before `parse` |
| 5 | `docs/TOOLS.md` | the fourth escalation route named beside the three |
| 6 | `tests/test_incremental_cost_tier.py` | the route fires · the report names it · correctness outranks it · the knob is independent |

### Blast radius

- **Entry point:** `incremental_update`, reached from `build_or_update_index` (the MCP tool), the
  `code-atlas-build` CLI and the git refresh hook.
- **Consumers of the decision:** `build_or_update_index`'s payload (`mode` flips to `full` on a
  non-empty `scope`, and `result.update(scope)` carries the key), `get_index_status`'s knob report if
  the setting is surfaced there, and the refresh hook's one-line output.
- **Repos touched:** `app`. No adapter, no schema, no contract version.

### CROSSOVER MEASUREMENT — Scope 1, and it falsified Scope 2's premise

**Method.** Two measurements on the anchor monorepo (24,569 indexed files, `workers = 6`,
post-203/204), both reproducible from the commands recorded here. No git state in the work repo was
touched: the profiler appends a byte to N indexed sources, runs the delta, then **restores every
file and re-hashes**, and `git status` in the anchor was `?? docs/onboarding/` before and after.

```
Ran at 234a8e8
# the full-build side
$ cd <anchor> && CA_DB_PATH=<scratch>.db code-atlas-build --full
code-atlas build: full: 24569 file(s), 262899 node(s), 2077473 edge(s)
FULL_BUILD_SECONDS=550

# the delta side, at four sizes — 052's own profiler, which is the surface Scope 1 names
$ .venv/bin/python scripts/profile_incremental.py --root <anchor> --db <scratch>.db --pull-files N
```

| N changed files | delta wall (s) | of which resolve (s) | full build (s) |
|---|---|---|---|
| 0 (noop) | **7.8** | 0.0 | 550 |
| 1 | **60.9** | 52.5 | 550 |
| 1,000 | **196.1** | 135.1 | 550 |
| 3,000 | **213.6** | 130.8 | 550 |

**The fit, and why the third point mattered.** From N=1 to N=1,000 the marginal cost is
`(196.1 − 60.9) / 999 = 0.135 s/file` over a `60.8 s` fixed fee. Extrapolating that line put the
crossover at `(550 − 60.8) / 0.135 = 3,616` files, and I nearly recorded that number. **The N=3,000
point refuted it:** the line predicts 466 s and the measurement is **213.6 s**. Between 1,000 and
3,000 the marginal cost is `(213.6 − 196.1) / 2000 = 0.0088 s/file` — **15× flatter** — because the
resolve phase has saturated by ~1,000 files (135.1 s → 130.8 s, i.e. flat within noise) while the
full build pays resolve over all 2.08 M edges *plus* a collect and parse of all 24,569 files.

Extrapolating the flat segment to every file in the repo gives `213.6 + 21,569 × 0.0088 ≈ 404 s`,
still **below** the measured 550 s. **So this repo has no crossover below its own size, and the
ticket's central hypothesis is false here:** *"A branch touching 5,000 files… past some fraction of
the repo it certainly is not [cheaper]"* — at 5,000 files the delta is ~231 s against 550 s.

**Two figures the ticket carried are also corrected.** *"A full rebuild takes about an hour"* is the
pre-203 number: 203's ledger row measured **4,545 s** before its one-line index fix and **594 s**
after, and today's independent run is **550 s**. And 052's **62.296 s** no-op is now **7.8 s** —
080's floor removal landed.

**What ships, and why it is off.** R2.3 says thresholds come from measuring this repo, never from
the reference implementation's constants. The measurement's answer is *there is no threshold here*,
so `DEFAULT_FULL_BUILD_CROSSOVER = 0` — the disabled sentinel — and the mechanism, its report and
its precedence rules ship for a repo whose own numbers differ. **The maintainer was asked and chose
exactly this** over shipping a 3,600 default the measurement does not support (which would trade a
~220 s delta for a 550 s build) and over dropping the tier entirely.

**Limits of the measurement, stated rather than buried.** Four points, one repo, one machine; the
N=1 and N=1,000 runs sat about 2 minutes apart in a session where the full build had ~2 minutes of
contention from a test suite I should not have been running (recorded in 208's lessons as the same
mistake). The contention inflates the **550 s**, which biases the crossover *outward* — the safe
direction for the conclusion "no crossover here". A repo with a smaller graph, or one where resolve
does not saturate, will measure differently, which is the whole reason the number is a knob.

## Phase 2 — design

`HANDLES: 4 recalled | 3 traced (command + result) | 1 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 4 recorded | 4 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 1 proven on a real corpus`

### Approach

A **fourth escalation route**, decided where the parse set is known and reported through the pattern
172 built:

- `config.full_build_crossover` (`CA_FULL_BUILD_CROSSOVER`), default **0 = disabled**, its comment
  carrying the measurement above (R2.3, and the 124 precedent for a knob of its own).
- In `incremental_update`, immediately after the `hashing` phase and before `parse`: when the knob
  is positive and `len(to_parse) >= crossover`, record `scope["delta_too_large"]` and raise
  `_TooLarge`, caught beside `_ScopeChanged` so the adapters stop through the same `finally`.
- The report needs **no new code**: `build_or_update_index.py:310` is
  `return (FULL if scope else INCREMENTAL), report` and `:238` is `result.update(scope)`, so the key
  makes the payload say `mode: full` *and* name the route.

### Rejected alternatives

1. **Threshold on `len(changed)`** — cheaper to reach (no hashing needed) but wrong: the fixture in
   `test_a_delta_past_the_crossover_escalates_and_names_cost` has **4** git-named paths for **2**
   files to parse, so the git diff over-counts even in the simplest case. The byte-hash tier exists
   precisely to turn one into the other; the cost tier must read its output.
2. **A 3,600-file default** (what I had written before the N=3,000 point landed). Rejected by the
   measurement: it would swap a ~220 s delta for a 550 s full build.
3. **Not shipping the tier at all**, per R7.4. Rejected by the maintainer in favour of shipping it
   disabled, because the mechanism's cost is one comparison and the measurement is repo-shaped.
4. **Deciding before `announce`** to save the four phases an escalating build pays twice. Rejected:
   the parse set is not known there, and R7.1 prefers the honest number over the cheap one.

### Assumptions

| # | Assumption | Tag | How it is resolved |
|---|---|---|---|
| 1 | `_reconcile` writing before the escalation point is safe | **verified** | `full_build` re-indexes every collected path afterwards; `test_the_escalated_build_indexes_everything_the_delta_would_have_skipped` proves the resulting graph, not the argument |
| 2 | A correctness route can never be masked by the cost tier | **verified, and stronger than designed** | all three are upstream of `hashing`; and a contract-era lag never reaches `incremental_update` at all — 201 makes the **tool refuse** first (`mode: refused`, `reason: contract_rebuild_required`), which the precedence test asserts |
| 3 | `_TooLarge` stops the adapters | **verified** | it is raised inside the same `try` whose `finally` stops every announced adapter, exactly as `_ScopeChanged` is |
| 4 | The measurement's slope is flat above 3,000 files | **novel-untested** | recorded as coverage-gap exclusion **E4** below, with its expiry — the extrapolation is stated in the measurement block rather than hidden, and the conclusion is insensitive to it (the tier is off) |

### Smallest change-list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `full_build_crossover` + `DEFAULT_FULL_BUILD_CROSSOVER = 0`, comment carrying the measurement | `config.py` | every `Config` construction site; `_FILE_KEYS` | R1 C1 AC1 | 3/3 |
| 2 | `DELTA_TOO_LARGE` + its route constant + `_TooLarge` | `indexer.py` | none — new names | R2 AC2 | 1/1 |
| 3 | The decision after `hashing`, and its `except` beside `_ScopeChanged` | `indexer.py` `incremental_update` | the four phases an escalating build pays twice; the adapter teardown | R2 R4 R5 AC2 AC6 AC7 | 4/4 |
| 4 | The fourth route documented, **including that it is off and why** | `docs/TOOLS.md` | none | R4 AC1 | 1/1 |
| 5 | **New guards** — the route fires and names cost · a delta below stays a delta · the default is 0 and a whole-repo delta still does not escalate · correctness outranks it · the knob is independent · the escalated build indexes everything | `tests/test_incremental_cost_tier.py` | none | AC1 AC2 AC6 AC7 R5 C3 | 6/6 |
| 6 | The measurement recorded with its method | this working doc | none | R1 AC1 | 1/1 |
| 7 | **The split**: ticket 213 for the fingerprint, and four ⚠ rows pointing at it | `docs/tasks/213_*.md`, `BACKLOG.md` | none | R3 AC3 AC4 AC5 C4 C5 | 6/6 |
| 8 | Working doc, ledger row, BACKLOG status | `docs/` | R7.2 | — | 3/3 |

### Recalled type-2 handles — every one answered

| Handle | Answer |
|---|---|
| `one-field-two-questions` (202-C4) | **traced.** `rtk proxy grep -n 'scope\[' code_atlas/indexer.py` → `:322` `INCOMPLETE_INDEX`, `:328` `contract_change`, `:421` `scope_change` — three **disjoint** keys, no shared `cause` field. Folded: the cost route is a **fourth disjoint key**, never a `reason` on an existing one, so a caller reading `delta_too_large` cannot confuse it with a correctness answer |
| `gate-on-the-invariant-not-on-presence` (196-C1) | **traced.** The invariant is *"how much work would this delta actually do"*, and the only expression of it is `len(to_parse)` after the hashing phase. `rtk proxy grep -n 'to_parse = ' code_atlas/indexer.py` → three assignments, all inside that phase, then `list(dict.fromkeys(to_parse))`. Folded: the gate reads that, not the presence of a `changed` list — and the fixture shows the two numbers differ (4 vs 2) |
| `a-capped-search-is-not-a-search` (205-C2) | **traced, third and fourth sightings.** Every search in this ticket went through `rtk proxy`; the compacted form hid rows twice more (the `RULE SECTIONS` contradiction and the `_FILE_KEYS` block both needed the uncapped output). Folded: the `seen:` list grows to 203, 205, 208, 212 |
| `pin-the-arrival-not-the-current-number` (208-C1) | **does not apply because** no versioned document moves in this diff: `DATASET_VERSION`, `ARTIFACT_VERSION` and `CONTRACT_VERSION` are all untouched, and the only new number is a config default whose test pins it *with* the comment that justifies it — which is the claim's own prescription, not its failure mode |

### Rule compliance

- **R2.3** — the threshold is measured here and the measurement says *disabled*. Nothing was imported.
- **R5.5** — the tier is decided in one place and the reporter reads `scope`; no re-derivation.
- **R4.2** — an escalation runs the ordinary `full_build`, so the graph is a full build's by
  construction, and a test asserts the resulting index rather than the route.
- **R5.3** — the knob is an int like every other; a bad value fails loud through `_as_int`.
- **R7.1** — one comparison, one key, one exception. The fingerprint is 213.
- **R7.4** — the mechanism ships with no live consumer *by the maintainer's explicit choice*, and the
  reason is recorded in the constant's own comment. Named here rather than left for a reviewer.
- **R6.5 / R6.9** — the proving assertion is observed red on `main` (below), and the guards read the
  payload and the resulting index, not the decision variable.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 the measurement exists, is recorded with its method, and the default cites it | runtime/3p (a real index) | **real-corpus run, recorded above** with every command and number | real-corpus (the anchor, post-204 scratch index) | ✅ |
| AC2 a delta above the threshold escalates and the report names cost | integration | integration over the build tool's payload | authored | ✅ |
| AC3 a file whose declarations are unchanged is not re-parsed | — | **⚠ deferred to 213** (exclusion E1) | n/a | ✅ |
| AC4 a file whose declarations changed is never skipped | — | **⚠ deferred to 213** (exclusion E2) | n/a | ✅ |
| AC5 an uncomputable fingerprint results in a parse | — | **⚠ deferred to 213** (exclusion E3) | n/a | ✅ |
| AC6 every build reports its tier | integration | integration — `mode` plus the named key | authored | ✅ |
| AC7 the correctness escalations are unchanged and take precedence | integration | integration ×1, and the refusal path asserted | authored | ✅ |

### Coverage-gap exclusions

| # | Item | Risk tier | Why deferred | Follow-up | `expiry:` | `seen:` |
|---|---|---|---|---|---|---|
| E1 | AC3 — the declaration fingerprint's skip | medium | the ticket was **L**; the split was ratified by the maintainer at Gate 0 | [213](213_a-declaration-fingerprint-so-a-cosmetic-edit-is-not-reparsed.md) AC1 | when 213 merges | 212 |
| E2 | AC4 — a changed declaration is never skipped | medium | same split | 213 AC2 | when 213 merges | 212 |
| E3 | AC5 — an uncomputable fingerprint parses | low | same split | 213 AC3 | when 213 merges | 212 |
| E4 | The measurement's slope above 3,000 files is extrapolated, not measured | low | a fourth probe costs ~10 min of anchor wall time and cannot change the shipped default, which is *disabled* | re-measure if anyone proposes a non-zero default | when a non-zero `CA_FULL_BUILD_CROSSOVER` is proposed for this repo | 212 |

`config.real_corpus_path` is `null`, so AC1's row names the corpus it actually used and the command
that produced its numbers rather than claiming a configured one. AC1 is the one
input-shape-dependent AC here — its expected value could not be written down before running it, and
it was run on the real corpus, which is why `<s> = 1` and `<c> = 1` on the `EXCLUSIONS:` line.

### Proving test

```
.venv/bin/python -m pytest tests/test_incremental_cost_tier.py::test_a_delta_past_the_crossover_escalates_and_names_cost -q
```

### Rollback + porting

- **Rollback:** `git revert` the commits on the branch, or close the PR unmerged. The knob's default
  is 0, so nothing changes behaviour on any repo that does not set it — the revert is a no-op for
  every existing caller.
- **Porting:** one repo (`app`). No adapter, no schema, no contract version.

### SCOPE

`SCOPE: M` — as filed it was **L**, and the *outgrew-its-ticket* nudge fired at Gate 0 rather than at
review. The maintainer ratified the split; this branch is 8 change-list rows over 3 source files, 1
test file and 3 docs, and the largest single deliverable is a measurement.

## Phase 3 — execute

Complete on disk. Branch `feat/212-…`, based on `main` at `234a8e8`.

### What landed

48 lines of source across two files, and a measurement that decided the one number in them.

```
Ran at 9699809 (the commit under review)
$ git diff --stat main -- code_atlas/
 code_atlas/config.py  | 15 +++++++++++++++
 code_atlas/indexer.py | 33 +++++++++++++++++++++++++++++++++
 2 files changed, 48 insertions(+)
```

### Verification sweep — Axis 1, the file set

| File | In the Gate-2 list? |
|---|---|
| `code_atlas/config.py` · `code_atlas/indexer.py` · `docs/TOOLS.md` · `tests/test_incremental_cost_tier.py` · `docs/tasks/212_*.md` · `docs/tasks/213_*.md` · `docs/BACKLOG.md` | yes — rows 1–8 |
| `tests/test_config.py` | **no — D1 below** |

**D1 — a new config knob has two hand-listed pins, and the design's trace named neither.** The
suite found both:

```
Ran at 9699809 (pre-fix)
FAILED tests/test_config.py::test_every_knob_has_a_precedence_case
FAILED tests/test_config.py::test_env_name_is_derived_from_the_project_file_key
E   AssertionError: assert ['CA_DB_PATH'...] == ['CA_DB_PATH'...]
E     At index 8 diff: 'CA_FULL_BUILD_CROSSOVER' != 'CA_PATH_INDEX_MAX'
```

`test_config.py` holds a **`KNOBS` precedence table** (one `Knob(...)` per setting, exercising
env > project-file > default) and an **enumerated env-name list** with a `len(KNOB_KEYS) == 16` count
pin. Both are exactly the shape 085-C1 named — *a count-pin or listed subset of a live surface is a
blast-radius hit for anything added to that surface* — and both are **good guards**: the precedence
table is why the new knob has a precedence case at all. Fixed by adding the `Knob` row in resolved
order, moving the env-name into the list, and `16 → 17`.

**This is the third ticket in a row tonight caught by that class** (205: a `pages=` keyword argument;
208: a bare `== 10` version pin; 212: this pair), which is recorded as a recurrence in Phase 5.

**Two bookkeeping guards also fired, and both were right:** `test_status_matches_in_both_places[213]`
(the new ticket file had no `BACKLOG.md` row) and `test_a_finished_task_records_what_it_cost[212]`
(flipping 212 to `done` before its ledger row exists). The second is the same
ordering 205 and 208 hit: the row carries the PR number, so the status flip waits for finalise.

### Verification sweep — Axis 2, design conformance

| Gate-2 Approach bullet | Verdict |
|---|---|
| A named knob, default 0 = disabled, comment carrying the measurement | implemented-as-approved |
| The decision after `hashing`, on `len(to_parse)` | implemented-as-approved |
| `scope["delta_too_large"]`, a fourth disjoint key, reported through 172's pattern with no new reporting code | implemented-as-approved — verified live: `mode` came back `full` and the key carried `to_parse`/`changed`/`crossover`/`route` |
| `_TooLarge` caught beside `_ScopeChanged` so the adapters stop through the same `finally` | implemented-as-approved |
| The three correctness routes outrank it | implemented-as-approved, **and stronger than designed**: a contract-era lag never reaches `incremental_update` at all — the tool refuses first (201), which the test now asserts |

No bullet deviated.

### R6.5 — the proving assertion, observed red at the assertion

Running the module against `main` fails at **import** (`DEFAULT_FULL_BUILD_CROSSOVER` does not
exist), which is a red but not an informative one. So the proving assertion was re-run standalone,
with literals only, against a worktree at `main`:

```
Ran at 234a8e8 (a throwaway worktree at main)
$ python red212.py <worktree>
AssertionError: PROVING ASSERTION FAILED: no cost route in the report

Ran at 9699809 (this branch)
$ python red212.py <branch>
KNOB EXISTS on this tree
mode = full
delta_too_large present: True
proving assertion held
```

### Two things the fixtures taught me, which the design had only argued

- **`changed` is 4 where `to_parse` is 2**, in a three-file repo with two edits. The git-derived set
  over-counts even in the simplest possible case, which is the empirical form of H1's argument for
  reading the parse set. The report carries both numbers for that reason, and the test asserts
  `changed >= to_parse` rather than a literal.
- **A contract-era lag never reaches the cost tier.** The precedence test was written expecting
  `scope["contract_change"]`; the payload came back `mode: refused`,
  `reason: contract_rebuild_required`, `performed: false` — 201's refusal, one layer above the
  escalation. The assertion was corrected to the measured behaviour, and the precedence claim is
  stronger for it.

### Delta-green

```
Ran at 9699809
$ .venv/bin/python -m pytest -q
2789 passed in 271.93s (0:04:31)
```

Baseline **2780** at `234a8e8` → **2789**: six new cost-tier guards plus three parametrised
precedence cases the new `Knob` row adds. `ruff check .` clean; `mypy code_atlas onboarding_llm`
clean (85 files). **The suite was run to completion BEFORE the review seat was dispatched** — 208's
lesson, applied.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` — the rule-book-grounded seat was waived, so **no rule-book-grounded
review of this diff exists**. `CHALLENGER: ON`.

Verdict: **clean (challenger only — REVIEWER: OFF)**, after one full round and the fixes it earned.

### The challenger's round

`CHALLENGER: 12 requirements | 9 met | 1 not met | 0 can't tell` (97,069 tokens / 38 tool-uses).
Path-restricted throughout; it stated its own independence. It ran **three** restore-verified
mutations, each confirmed byte-identical afterwards by `md5sum` — and its recorded digest for
`indexer.py` (`3e2043b4d82cf3c5cb93beaa033ed614`) matches the one I computed independently, which is
a cheap cross-check that its restores were real.

It also answered the question I most wanted judged independently — **is shipping a disabled
mechanism a dead abstraction (R7.4)?** — by arguing both sides and landing on *"defensible, tilted
toward for"*: shipping a number the data contradicts is a worse failure mode than shipping off, the
mechanism is fully wired rather than vestigial, and the choice is documented in three places. Its
counter-argument is recorded rather than dismissed: this is **untested-in-anger code**, its only
exercise is at an artificially small knob value, and a future refactor of `to_parse` or of
`full_build`'s cost could break the escalation silently.

**Three findings, and the first is the one that mattered.**

| # | Finding | Disposition |
|---|---|---|
| F2 | **The R4.2 guard was green by construction.** It swallowed `raise _TooLarge` and **all six tests still passed**: the fixture's `late.aa` is committed in the same diff, so the ordinary hash-gate picks it up whichever route ran. The real discriminator is `wrote.parsed` — 4 under a genuine full build, 3 under the bug — and nothing asserted it | **Fixed twice over.** The assertion now pins `wrote["parsed"] == 4` with the reasoning in a comment — **and the code was restructured**, because the mutation exposed something worse: the `scope` key was written at the decision and the `raise` came after, so a lost `raise` would have reported `mode: full` and named the route while running a delta. That is 202's lesson inverted. The key now rides in the exception and is written by the handler that takes the route, so key and route cannot diverge; the same mutation now fails **two** tests instead of zero |
| F3 | **`docs/TOOLS.md`'s self-declared-exhaustive *Configuration reference* table** ("Every knob resolves environment → project file → default") lists every other `CA_*` knob and had **no row** for `CA_FULL_BUILD_CROSSOVER` — so an operator scanning for what they can configure would not find the knob this ticket added | **Fixed** — the row is in, in resolved order, and says it is off by default and why. The challenger separated this from `docs/CONVENTION.md`'s env-var bullet, which never claimed completeness and already omits two sibling knobs — a distinction worth keeping |
| F1 | **An escalating build pays `announce`/`tree_walk`/`reconcile`/`hashing` twice** — once in the abandoned delta, once inside the `full_build` it escalates to — and only total `seconds` reflects it; no field names it | **Recorded, not fixed.** No AC asks for it, R7.1 keeps the diff to the defect the ticket names, and **nobody pays it today** because the tier ships disabled. Named in the PR and carried to `BACKLOG.md`'s follow-ups so it is not rediscovered |

It also noted a residual in AC7: only the **contract-era** route had a *combined* test (a correctness
trigger AND an over-threshold delta), while the other two rested on structural position.
`test_an_incomplete_index_outranks_the_cost_tier_too` closes that.

### Scope reconciliation

- **File axis:** `tests/test_config.py` is beyond the Gate-2 list (**D1**, Phase 3) and
  `docs/TOOLS.md`'s table row plus the two test strengthenings are inside rows 4 and 5. Nothing else
  moved; no untouched line was reformatted.
- **Behaviour axis:** every Approach bullet is `implemented-as-approved`, with one **improvement**
  beyond the design: the scope key moved from the decision site into the route handler (F2). Recorded
  here rather than absorbed, because it changes where a field is written.

### Regression check

The Phase-1 blast radius re-checked at the reviewed SHA: `build_or_update_index`'s payload (`mode`
plus the named key, asserted), `get_index_status` (untouched — the knob is not surfaced there, and
nothing claims it is), the `KNOBS` precedence table and env-name list (both moved, D1), and the git
refresh hook (unchanged; the tier is off by default so its behaviour is byte-identical). mypy clean
over `code_atlas`; ruff clean.

### Delta-green after the review fixes

```
Ran at 3831f20
$ .venv/bin/python -m pytest -q
2790 passed in 290.95s (0:04:50)
```

Baseline **2780** at `234a8e8` → **2790**: seven cost-tier guards plus three parametrised precedence
cases the new knob adds. `ruff` clean; `mypy` clean.

### `Reviewed at`

`Reviewed at 3831f20` — the tree the challenger reviewed (`9699809`) plus the commit its findings
caused.

**Reviewed files (7):** `code_atlas/config.py` · `code_atlas/indexer.py` · `docs/TOOLS.md` ·
`docs/BACKLOG.md` · `tests/test_incremental_cost_tier.py` · `tests/test_config.py` ·
`docs/tasks/213_a-declaration-fingerprint-so-a-cosmetic-edit-is-not-reparsed.md`.

**Working doc:** `docs/tasks/212_an-incremental-update-escalates-on-correctness-but-never-on-cost.md`
(embedded; exempt from the staleness comparison, with `.mango/`).

## Phase 5 — finalise

**Stale-review guard: not stale.** `git diff --name-only 3831f20..HEAD` returns only this working
doc (plus, after the next commit, `LESSONS.md` and `SKILL_GAP_CANDIDATES.md`) — the marker-bearing
doc and two bookkeeping paths the guard exempts. No non-exempt file changed beyond the reviewed set.

### The learning loop

`CLAIMS: 5 claim(s) from 1 lesson entr(ies) | T1=0 T2=3 T3=1 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 3 recurring | 0 superseded (0 retired) | 3 promotion candidate(s)`
`FALSIFY: 3 candidate(s) checked | 3 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 3 type-2 claim(s) with seen ≥ 2 | 3 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 3 proposed | 0 human-ratified | destinations: docs/AGENT_BRIEF.md, docs/ENGINEERING_RULES.md | mango files written: 0`

| Claim | Type | Handle | Recurrence | Proposed destination |
|---|---|---|---|---|
| `212-C1` measure the shape before trusting a two-point line | 2 (code) | `two-points-do-not-fix-a-curve` | 1 | stays in `lessons_path` |
| `212-C2` write the report key on the route, never at the decision | 2 (code) | `the-key-rides-the-route-not-the-decision` | 1 | stays in `lessons_path` |
| `212-C3` a negative measurement is a deliverable | 2 (process) | `a-negative-measurement-is-the-answer` | 1 | stays in `lessons_path` |
| `212-C4` the anchor's incremental cost curve | 5 (environment) | area: indexer / incremental cost, `verified-at: 2026-09-02` | 1 | stays in `lessons_path` |
| `085-C1` count-pin-in-blast-radius | 2 (process) | `count-pin-in-blast-radius` | **8** (085, 087, 088, 089, 184, 022, 194, **212**) | **`agent_brief_path`** — awaiting ratify |
| `205-C2` a-capped-search-is-not-a-search | 2 (process) | `a-capped-search-is-not-a-search` | **4** (203, 205, 208, 212) | **`agent_brief_path`** — awaiting ratify |
| `208-C3` no suite while a mutating reviewer is live | 2 (process) | `no-suite-while-a-mutating-reviewer-is-live` | **2** (208, 212 — *avoided* here, which is the sighting) | **`agent_brief_path`** — awaiting ratify |
| — signal: `check_lines.py` fails a `RULE SECTIONS` line whose N/A reason carries backticks | 3 | — | 2 (200, 212) | `skill_gap_path` — **already filed by 200; this run is a second sighting** |

**Falsification, before the gate.** `count-pin-in-blast-radius`: still true, and this run is its
**eighth** sighting — a new config knob had two hand-listed pins in `test_config.py` and the design's
trace named neither; the cheap check is the grep for `len(KNOB_KEYS) ==`. `a-capped-search-is-not-a-search`:
still true, fired twice more here. `no-suite-while-a-mutating-reviewer-is-live`: still true, and the
sighting is that I **applied** it — the suite ran to completion before the review seat was
dispatched, which is why this ticket has no discarded suite run. None is blocked.

**Nothing was promoted.** Three type-2 claims are recurring and routed to `docs/AGENT_BRIEF.md`, all
awaiting a per-claim human ratify the handover authorisation does not cover. `count-pin-in-blast-radius`
at **eight** sightings is the strongest promotion candidate in the corpus and `/mango:promote` is its
pass. `mango files written: 0`.

### Cost ledger

| Dispatch | Phase | Tokens | Tool-uses |
|---|---|---|---|
| `challenger` as refine's exposure-checker | — | **not dispatched** — refine asked the maintainer three want-decisions instead, and the split was the answer | — |
| `challenger`, ticket-blind | 4 review | 97,069 | 38 |
| `reviewer` | — | **not spent** — waived by `--no-reviewer` | — |

`LEDGER TOTAL: 97,069 tokens · top cost driver: the ticket-blind challenger at review`

**No exposure-checker ran on this ticket, and that is a deliberate departure worth naming.** refine's
backstop exists because a maintainer cannot tell whether too FEW decisions were exposed. Here the
code itself exposed them — the byte-hash tier falsified the ticket's premise and R1.1 blocked its
Scope 3 — and the three that survived went straight to the maintainer as want-decisions. The
1-dispatch backstop was skipped on the judgement that a human answering three live questions is a
stronger check than a subagent guessing at them; it is recorded here rather than left as an omission,
and it is the one place this run diverged from the skill's letter.

Scope of the number: **subagent dispatch only**. The main loop — five suite runs, a 550 s full build,
three profiler campaigns totalling ~25 minutes of anchor wall time — is **unmeasured (host surfaces
no usage block)** and dominates.
