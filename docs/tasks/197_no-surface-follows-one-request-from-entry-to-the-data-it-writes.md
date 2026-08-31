---
id: 197
slug: no-surface-follows-one-request-from-entry-to-the-data-it-writes
title: "Every onboarding surface is an aggregate — none follows one request from its entry point to the data it writes"
phase: 3
milestone: M11
status: done
depends_on: [113, 114, 111, 112, 022]
---

## Why this exists

The map answers *what this codebase is* and never *how one thing happens*. Every surface it renders
is an aggregate over the whole index — the layer table, the layer×layer matrix, the hubs, the
treemap, the 113 zero-inbound split, the 114 capability table, the 115 mirror panel. A reader who
has found the file for a named capability still cannot see the capability **run**: which entry point
starts it, which layers it crosses, and which table it ends up writing.

This is the gap a domain/flow layer fills in comparable tools, and there it is produced by an LLM
reading source. Here it does not have to be: contract **v9** (022) added `Table`, `Column` and
`WRITES`, which is the first release in which a forward walk has somewhere meaningful to *end*.
Before it, a trace ran out of vocabulary and trailed off.

**This is not the thing [121](121_onboarding-question-class-never-measured.md) refused.** 121
narrowed the phase away from a *curated reading order* — a pedagogical claim nothing can falsify. A
trace is the opposite: every hop is an edge carrying a confidence tier, a hop that cannot be proven
is reported rather than bridged, and a walk that hits its budget says so. It is falsifiable line by
line, which is the standard the rest of PILLAR 2 already holds.

## Scope

1. New `code_atlas/onboarding/flows.py` — pure derivation beside 113/114/115, no SQL, no LLM, no
   language branch (R1.1/R1.4/R4).
2. **Seeds** from the populations that already exist: 113's `web_entry` bucket plus the operator's
   declared `entry_points`, carrying 119's `signals` so a flow states whether its seed was declared
   or read from the responsibility vocabulary.
3. **Walk** over the `IMPACT_KINDS + WRITES` kind set. `IMPACT_KINDS` itself is **not** widened —
   `contract.py` feeds `impact`/`reachable_from`, and widening it would move every existing answer
   to buy one new surface. ~~Through `store.reachable_from`'s existing `kinds` parameter.~~
   **Superseded at Gate 2** (design, *Rejected alternative 1*): `reachable_from` returns a flat
   reachable **set** with no predecessor data, so no path can be reconstructed from it, and it is
   one SQL walk **per seed**. The walk is a parent-pointer BFS over one kind-filtered pull
   (`store.flow_edges`) instead.
4. **Steps** are the trace's own hops, ordered. ~~Layer rank (110) crossed with BFS depth, each SCC
   collapsed — the grouping `steps.py` (111) performs for the tour.~~ **Narrowed at Gate 2 (H5):**
   `build_steps` groups a *whole tour* into 5–15 buckets; a flow is a single path, so there is
   nothing to bucket and no cycle to collapse (BFS's `seen` set already makes a path acyclic).
   Each step carries its 110 layer, which is the part that transfers.
5. **Attribution**: each flow is assigned to a business module via `modules.module_of_path` (114),
   which is what supplies the capability level without naming anything.
6. **Cap and rank** before rendering. A repo with a thousand controllers must not emit a thousand
   flows. ~~Refuse rather than dump when the cap binds.~~ **Superseded by ratified want-decision
   W1a/W1b**: the maintainer chose a *global cap with a global ranking* that states what it cut, not
   a refusal — a refusal would leave a large repo with nothing to look at. The `find_orphans` (182)
   refusal is kept for the case it fits: **no seeds at all** (AC5).
7. Carry the result into the 112 dataset (`DATASET_VERSION` bump), render it in `viewer.py`, and
   emit a `flows.md` with a mermaid diagram (the 143 precedent: GitHub and VS Code render it, and the
   HTML map stays fetch-free).

### Explicitly not in scope

- `contract_version`. The adapter contract is untouched; `WRITES` already exists and `DATASET_VERSION`
  is not it (`dataset.py:11`).
- **Naming** a flow or a module in business language — that is the seam, and it is
  [198](198_a-business-module-is-labelled-by-its-directory-name.md).
- Any *curated reading order*. 121's narrowing stands: this ships a trace, not a syllabus.

## Constraints

- **R4.3** — bounded by `CA_IMPACT_MAX_NODES`, never a whole-graph load.
- **Store semantics are the honesty mechanism, not a limitation** — only `RESOLVED` edges expand the
  frontier (`store.py:1739`); HEURISTIC/DYNAMIC neighbours are recorded as unproven and never
  expanded. A flow therefore stops at a dynamic hop and **says so** (R5.6).
- **R4.2** — identical graph ⇒ byte-identical flows; sorted throughout, no timestamps.
- **R2.2** — no framework, product or repo name may appear. Seeds come from 110's ratified
  vocabulary and the operator's own declarations, never a new word list.

## Acceptance criteria

1. A flow is an ordered list of steps; each step carries its file, its 110 layer, and the confidence
   tier of the hop that reached it.
2. A flow whose walk hit the node budget reports `walk_truncated`, and every count derived from it
   reads as an under-estimate (140's rule).
3. A flow ending in a write names the **column** when the statement named it and reports `DYNAMIC`
   against the table when it did not — 022's own split, not a guessed column list.
4. Every flow is attributed to a business module, with an explicit `unattributed` bucket rather than
   a silent drop.
5. An index with no entry seeds **refuses with a reason**; an empty list is never returned as proof
   that no flow exists.
6. `DATASET_VERSION` is bumped and the dataset/artifact conformance tests move with it.
7. Identical input yields byte-identical output.
8. ~~The 121 onboarding question class gains a question of the shape *"what happens when a user does
   X?"*, its ground truth read out of the source by hand **before** the tool runs.~~
   **DEFERRED to [199](199_flows-have-no-tool-so-an-agent-pays-for-the-whole-overview.md) — not met
   on this ticket, and deliberately so.** The question was written, its ground truth hand-read, and
   it was **run**: the only agent-facing surface available took the repo's gate red
   (`ratio 0.53 < 0.63`, `precision 0.944`, 6 unexpected), because answering one request meant buying
   the whole `architecture_overview` payload. The surface was reverted rather than the floor lowered.
   Recorded as coverage-gap exclusion **E3**, `expiry: when 199 lands`. What 197 ships is the
   **reader-facing** half named in Scope 7; the agent-facing half needs its own narrow tool.

## References

[113](113_reachability-split.md) (the seed populations and their signals),
[114](114_business-module-table.md) (`module_of_path`, the attribution level),
[111](111_tour-is-narrative-steps.md) (the layer×depth grouping to reuse),
[112](112_onboarding-dataset-contract.md) (`DATASET_VERSION`),
[022](022_sql-schema-adapter.md) (`WRITES`, the sink that makes a trace terminate),
[121](121_onboarding-question-class-never-measured.md) (the narrowing this stays inside),
[138](138_architecture-rules-are-never-asked-of-the-graph.md) (the `kinds` parameter),
[182](182_find-orphans-answers-with-rows-it-has-flagged-unreliable.md) (refuse rather than dump).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 197 · **work_doc_mode:** embed · **Current phase:** 0 refine — complete; Gate 0 closed.
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · `STRUCTURE: native` · **Type:** enhancement.
- Run arg: *"with skipped review"*, clarified by the maintainer mid-run to mean **the reviewer seat
  only** — the review phase runs and the ticket-blind challenger stays ON. This **reverses** the
  reading AGENTS.md carries and that 195 recorded (*"both seats off"*); AGENTS.md still says
  otherwise and is a separate fix, not this ticket's.
- **BASELINE: green** — 2,608 passed / 0 failed / 0 skipped, bare `pytest` on the Linux dev host
  (125 s). Not the Docker route: this host is POSIX and carries the PHP adapter, so AGENTS.md's
  Windows exclusion does not apply. No baseline exclusions.

## Phase 0 — refine

`PREMISE: 18 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 11 claim(s) surfaced | 0 by symbol | 9 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 15 unresolved surfaced | 6 want-decision asked | 9 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Recalled claims (ADVISORY — surfaced only, injected nothing).**

| # | Claim (handle) | Type | Matched by | Relevant here? |
|---|----------------|------|-----------|----------------|
| 1 | `per-element-ceiling-leaves-total-unbounded` | 2 | handle — the change caps a derived population | **Yes** — drove want-decision W1; a per-module cap leaves the total unbounded |
| 2 | `count-pin-in-blast-radius` | 2 | handle — `DATASET_VERSION` bump pins counts across tests | Yes — the bump moves conformance fixtures |
| 3 | `derived-not-listed-invariant` | 2 | handle — new core module others import | Yes — flow kinds must be derived from a named subset, never re-listed |
| 4 | `stamp-at-the-builder-not-the-wrapper` | 2 | handle — value threaded through callers | Yes — flows are stamped in `build_dataset`, not in each renderer |
| 5 | `skip-dynamic-means-unlinkable` | 2 | handle — DYNAMIC hops | Yes — a DYNAMIC hop stops the trace and is reported |
| 6 | `denominator-is-the-population-not-the-subset` | 2 | handle — coverage counts | Yes — flow coverage is over all seeds, not over emitted flows |
| 7 | `empty-seam-inputs-masquerade-as-missing-data` | 2 | handle — seam inputs | Advisory only; 197 injects no seam (198 does) |
| 8 | `prove-the-guard-fails` | 2 | handle — new guard | Yes — the proving test must be shown red first (R6.5) |
| 9 | `measure-the-axis-the-defect-lives-on` | 2 | handle — new measurement | Yes — AC8's question must sit on the behaviour axis, not the structure axis |
| 10 | store / indexer / R1.4 / R5.1 | 5 | area | Yes — SQL stays in `store.py` |
| 11 | docs / R7.2 / R1.4 | 5 | area | Yes — BACKLOG + ledger bookkeeping |

**Settled wants (from the maintainer — become AC constraints).**

| # | The want | Chosen direction | Becomes AC constraint |
|---|----------|------------------|-----------------------|
| W1 | How is the flow list bounded on a repo with thousands of entry points? | **Global total cap with a global ranking** (module coverage + trace length); the cut is stated. Not a per-module cap. | AC: the cap is global; a cut list names how many were cut |
| W2 | Is a trace that reaches no sink still a flow? | **Yes — emitted, labelled `no-sink`.** | AC: `no-sink` flows are emitted and labelled, never dropped |
| W3 | One controller file with 15 action methods → how many flows? | **15 — one flow per entry symbol.** | AC: the seed unit is the entry **symbol**, not the file |
| W4 | One entry reaching 3 distinct sinks → how many flows? | **3 — one path per sink.** | AC: each flow is one path with exactly one end |
| W5 | A flow crossing several modules belongs to which? | **The entry point's module.** | AC: attribution keys on the seed's path |

**Resolved direction + citation (how-decisions — refine-resolved, every row cited).**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| H1 | Stop grain | File-level stops | 087's locked decision, `phase3-onboarding/ROADMAP.md` §4 M11 |
| H2 | Walk budget | `CA_IMPACT_MAX_NODES` | ticket Constraints; `tools/guided_tour.py:44` |
| H3 | Which edges a trace may cross | `IMPACT_KINDS` + `WRITES`; `IMPACT_KINDS` itself untouched | ticket Scope 3; `contract.py:113` |
| H4 | Seed population | 113's `web_entry` bucket + declared `entry_points` | `onboarding/reachability.py:30`; `tools/reach_shared.py:24` |
| H5 | Step grouping | Reuse the layer-rank × BFS-depth discipline and `_bfs_depth`; **not** `build_steps` wholesale — it takes a whole tour's `Sequence[TourStop]` and returns 5–15 steps for the tour, not for one trace | `onboarding/steps.py:57`, `:105` |
| H6 | A hop that cannot be proven | The trace stops there and says so | ticket Constraints; R5.6 |
| H7 | Set → ordered path | BFS with parent pointers over the **already-pulled in-memory edge list**, not a new store walk: `dependency_edges_with_tier()` applies no kind filter, so `WRITES` rows are already present | `store.py:812-830`; `tools/generate_onboarding.py:84` |
| H8 | AC8's measurement tier | The committed fixture `tests/fixtures/php/onboarding` — the only tier that is committed and re-runnable | 121; `benchmarks/121_onboarding-question-class.md` |
| H9 | `flows.md` diagram shape | One mermaid diagram **per flow**, not one aggregate — an aggregate would merge disjoint traces and lose the "one request" framing 143's matrix diagram legitimately has | ticket title; 143; `tour.md`'s one-entry-per-stop pattern |

**ASSUMED (awaiting ratification) — requires an explicit confirm at Gate 2.**

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses a prior decision? |
|---|----------------|-------------|--------------------------|----------------------------|
| A1 | The concrete "what happens when a user does X" scenario for AC8 is chosen from the committed fixture's own content once the fixture is read | The tier is derivable (H8); the **scenario** is not, and it is not concrete until the change list exists | Gate 2 | no |

**Constraints surfaced from the scan.**

- `dependency_edges_with_tier()` drops the edge **kind** (`store.py:812`), so identifying a `WRITES`
  hop or a `Table`/`Column` sink needs kind data the current pull does not carry. Design must choose
  a bounded store addition or a separate kind pull — SQL stays in `store.py` (R1.4).
- The artifact's whole-graph pulls are accepted for this surface (196 records why), so R4.3 binds the
  **trace walk**, not the edge pull.
- Comments ≤ 3 lines (AGENTS.md); no `if language ==` under `code_atlas/` (R1.1, CI grep-gated).

**Exposure-checker** (ticket-blind challenger, 1 dispatch): **5 un-exposed decisions found** — the
seed unit inside a file, set-vs-path plus multi-sink fan-out, the attribution key, AC8's concrete
instance, and the diagram shape. Three were genuine acceptance-bar wants and became **W3/W4/W5**;
two were resolved as **H8/H9** with a citation; the mechanism half of its item 2 became **H7**, where
its premise (that `reachable_from` offers no predecessor data) is correct but not binding, because
the edge list is already in memory. Its judgement that the ticket was *"not yet fully exposed"* was
right, and W3–W5 are its doing.

## Phase 1 — analysis

`PREMISE: 18 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)` *(carried forward from Phase 0 — not re-run)*
`RECALL: 11 claim(s) surfaced | 0 by symbol | 9 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)` *(carried forward)*
`SECTIONS: 6 found (Why this exists · Scope · Explicitly not in scope · Constraints · Acceptance criteria · References) | 6 decomposed | ROWS: C=4 R=10 G=1 AC=15`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`BASELINE: green — 2,608 passed / 0 failed / 0 skipped`
`TRACK: backend — 0/9 touched files under UI paths`
`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) ✅ · §2 (change-type) ✅ · §3 (change-type) N/A · §4 (change-type) ✅ · §5 (change-type) ✅ · §6 (change-type) ✅ · §7 (change-type) ✅ · §8 (change-type) N/A`
`SCOPE: L`
`TIER: full`

### Requirements matrix

| ID | Source | Verbatim (abridged) | Interpretation | Ph1 evidence | Status |
|----|--------|---------------------|----------------|--------------|--------|
| G1 | Why this exists | *"none follows one request from its entry point to the data it writes"* | Emit a falsifiable trace surface; the map today is aggregates only | Every onboarding surface enumerated (`dataset.py`, `viewer.py`, `reachability.py`, `modules.py`, `mirrors.py`) is an aggregate; none carries a path | open |
| R1 | Scope 1 | new `code_atlas/onboarding/flows.py`, pure | Pure derivation module beside 113/114/115 | Peer modules are pure; no store import in any of them | open |
| R2 | Scope 2 | seeds from `web_entry` + declared `entry_points`, carrying 119 signals | Reuse `classify_reachability`'s output, not a new seed rule | `reachability.py:254` returns `ReachabilitySplit` with per-bucket `signals` | open |
| R3 | Scope 3 | kind set `IMPACT_KINDS + WRITES`; `IMPACT_KINDS` untouched | Trace may cross WRITES; the global tuple does not move | `contract.py:113` feeds `impact`/`reachable_from` | open |
| R4 | Scope 4 | steps = layer rank × BFS depth, SCC collapsed; reuse `steps.py` | Reuse the **discipline** and `_bfs_depth`; `build_steps` itself is tour-shaped (see H5) | `steps.py:105` takes `Sequence[TourStop]`, returns 5–15 steps for a whole tour | open |
| R5 | Scope 5 | attribution via `module_of_path` | One call per flow, keyed on the **seed's** path (W5) | `modules.py:304` takes one path, returns one owner | open |
| R6 | Scope 6 | cap and rank; refuse rather than dump | **Global** cap + global ranking (W1); cut is stated | `find_orphans` refusal precedent (182) | open |
| R7 | Scope 7 | dataset + viewer + `flows.md` with mermaid | Three render surfaces (inventory N=3 below) | `dataset.py:45`, `viewer.py`, `artifact.py` | open |
| R8 | Not in scope | no `contract_version` bump | `contract.py` untouched | `dataset.py:11` states DATASET_VERSION is not the contract | open |
| R9 | Not in scope | no business naming | Naming is 198 | — | open |
| R10 | Not in scope | no curated reading order | 121's narrowing stands | `ROADMAP.md` §5 | open |
| C1 | Constraints | bounded by `CA_IMPACT_MAX_NODES` (R4.3) | The **trace walk** is bounded; the edge pull is already accepted whole-graph | 196 records why the artifact's whole-graph pulls are accepted | open |
| C2 | Constraints | only RESOLVED expands; a DYNAMIC hop stops the trace and says so | R5.6 + `skip-dynamic-means-unlinkable` (R5.2) | `store.py:1739` docstring | open |
| C3 | Constraints | identical graph ⇒ byte-identical flows | R4.2; sorted throughout, no timestamps | peer modules all assert this | open |
| C4 | Constraints | no framework/product/repo name (R2.2) | Seeds from 110's ratified vocabulary + operator declarations only | `layers.py:44` marks the vocabulary ratified STANDARD | open |
| AC1 | AC1 | ordered steps; each carries file, layer, tier | Falsifiable: assert the three keys per step | — | open |
| AC2 | AC2 | `walk_truncated` + counts read as under-estimates | Falsifiable: assert the flag and the note (140's rule) | `impact_modules.py:47` carries the exact note | open |
| AC3 | AC3 | names the column when named; DYNAMIC against the table when not | Falsifiable: two fixtures, one each | 022's own split | open |
| AC4 | AC4 | every flow attributed; explicit `unattributed` bucket | Falsifiable: bucket present even at zero | `impact_modules` precedent | open |
| AC5 | AC5 | no seeds ⇒ refuses with a reason | Falsifiable: assert the reason string, not an empty list | 182 | open |
| AC6 | AC6 | `DATASET_VERSION` bumped; conformance tests move | Falsifiable: computed value **8** (see AC validation) | `dataset.py:45` = 7 | open |
| AC7 | AC7 | identical input ⇒ identical output | Falsifiable: build twice, compare bytes | R4.2 | open |
| AC8 | AC8 | a 121 question of shape *"what happens when a user does X"*, ground truth hand-read first | Falsifiable: the benchmark file gains the row | `benchmarks/121_onboarding-question-class.md` | open |
| W1a | Phase 0 W1 | global total cap with global ranking | Clause 1 of 2 — the cap is **global**, not per-module | recall claim `per-element-ceiling-leaves-total-unbounded` | open |
| W1b | Phase 0 W1 | the cut is stated | Clause 2 of 2 — a cut list names how many were cut | 126's `result_subtrees` precedent | open |
| W2a | Phase 0 W2 | a no-sink trace is still emitted | Clause 1 of 2 | 113's split-don't-drop discipline | open |
| W2b | Phase 0 W2 | it is labelled `no-sink` | Clause 2 of 2 — the label is asserted, not implied | — | open |
| W3 | Phase 0 W3 | seed unit is the entry **symbol**, not the file | One controller file with k entry symbols ⇒ k flows | contradicts `_seeds_on_files`' combined-seed precedent, deliberately | open |
| W4 | Phase 0 W4 | one path per sink; each flow has exactly one end | k distinct sinks ⇒ k flows | — | open |
| W5 | Phase 0 W5 | attribution keys on the seed's path | Not the sink's | 114's question is "which file to open for capability X" | open |

### AC validation (values independently re-derived)

| AC | Ticket's value | Computed | Verdict |
|----|----------------|----------|---------|
| AC6 | *"`DATASET_VERSION` is bumped"* — no target named | **7 → 8** (`dataset.py:45` reads 7) | agrees; target pinned |
| — | artifact shape — ticket silent | **`ARTIFACT_VERSION` 1 → 2**: `artifact.py:71-73` says *"Bump when as_dict keys change"*, and the manifest gains a `flows.md` entry | ticket incomplete; pinned here |
| R6 | *"cap and rank"* — no number named | **`CA_MAX_RESULTS`**, the cap every other onboarding list already uses (`config.py:31`; TOOLS.md *"Every list is capped at `CA_MAX_RESULTS`"*) | ticket incomplete; pinned here |
| AC1 | *"ordered list of steps"* | No 5–15 grouping applies: a flow's steps are its own hops, not a tour's buckets | agrees once H5's narrowing is read |

**Manual-check exclusion (unmeasurable in CI, logged per design step 6):** *the mermaid diagram in
`flows.md` renders in GitHub and VS Code.* No CI check can assert a third-party renderer's output;
143 shipped the same exclusion for the layer flowchart. `expiry:` when a mermaid-rendering check
enters the gate. `seen:` 143, 197.

### Clarifications (all 4 self-resolved, cited)

1. **Bump target for `DATASET_VERSION`** → **8**; `dataset.py:45` reads 7.
2. **Does `artifact.json` bump too?** → **yes, `ARTIFACT_VERSION` 1 → 2**; `artifact.py:71-73`
   states the trigger is an `as_dict` key change, and `flows.md` joins the manifest.
3. **What number caps the flow list?** → **`CA_MAX_RESULTS`**; every other onboarding list uses it
   (`config.py:31`), so a second knob would be a new concept for no reason (R1.2/YAGNI).
4. **Does the trace need a new store read?** → **yes, one bounded addition**: the existing
   `dependency_edges_with_tier()` (`store.py:812`) drops the edge **kind**, so a `WRITES` hop and a
   `Table`/`Column` sink are indistinguishable in it. SQL stays in `store.py` (R1.4).

`j = 0` — every want-decision was answered by the maintainer in Phase 0; none is carried forward.

### Universal inventory — `N = 3` render surfaces (per-item checklist, not an aggregate)

| # | Surface | Must carry flows | Proven by |
|---|---------|------------------|-----------|
| 1 | the 112 dataset payload (`dataset.as_dict()`) | yes | dataset conformance test at `DATASET_VERSION` 8 |
| 2 | `viewer.py`'s offline page | yes | the DOM stub run (`tests/viewer_dom_stub.js`), not a grep over the HTML — 116's own rule |
| 3 | committed `flows.md` + manifest entry | yes | artifact contract test at `ARTIFACT_VERSION` 2 |

### Gap analysis (enhancement — current vs target, with `path:line`)

| Goal | Current | Target |
|------|---------|--------|
| Follow one request end to end | No module produces a path. `reachability.py:254` classifies zero-inbound files; `tour.py:184` orders a whole-repo reading list; `steps.py:105` buckets that list. All aggregate. | One `flows.py` emitting ranked, capped, attributed traces with per-hop confidence |
| Terminate a trace meaningfully | `IMPACT_KINDS` (`contract.py:113`) has no `WRITES`, so a walk cannot reach a `Table`/`Column` | Flow-local kind set adds `WRITES`; the global tuple is untouched |
| Say which hop is unproven | `dependency_edges_with_tier()` (`store.py:812`) carries a tier but **not** the kind | One bounded store read carrying kind + tier |

### Blast radius

`code_atlas/onboarding/flows.py` (new) · `dataset.py` (schema + version) · `artifact.py` (manifest +
version + `flows.md`) · `viewer.py` (one section) · `store.py` (one bounded read) ·
`tools/generate_onboarding.py` (wiring) · `tests/` (new + moved conformance) ·
`docs/benchmarks/121_onboarding-question-class.md` (AC8) · docs bookkeeping. **9 files**, one repo
(`app`). No adapter, no `contract.py`, no `.harness.json`.

### Rule-compliance coverage

| § | Applicable because | Answer |
|---|--------------------|--------|
| §1 | new core module + a store read | ✅ R1.1 no `if language ==` in `flows.py`; R1.4 the one SQL addition lives in `store.py`, `flows.py` imports no store; R1.2 no new seam — 198 owns the seam |
| §2 | seeds and sinks could tempt a word list | ✅ R2.2 seeds come from 110's ratified vocabulary + operator declarations; no framework or repo string enters `flows.py` |
| §3 | a versioned artifact moves | **N/A because** `contract.py` is untouched — `DATASET_VERSION`/`ARTIFACT_VERSION` are not `contract_version` (`dataset.py:11`, `artifact.py:71`) |
| §4 | the core must stay deterministic | ✅ R4/R4.1 no LLM in `flows.py` (198 adds the seam); R4.2 sorted, no timestamps; R4.3 the trace walk is bounded by `CA_IMPACT_MAX_NODES` |
| §5 | unproven hops and empty results | ✅ R5.6 a no-seed index refuses with a reason (AC5); R5.2 (`skip-dynamic-means-unlinkable`) a DYNAMIC hop stops the trace and is reported, never bridged |
| §6 | new module + new guard | ✅ R6.1 tests per new surface; R6.5 (`prove-the-guard-fails`) each new guard is observed red first; R6.7 (`derived-not-listed-invariant`) the flow kind set is derived from `IMPACT_KINDS + WRITES`, never re-listed; R6.3 the cap constant ships with a re-runnable reporter |
| §7 | docs and ledger | ✅ R7.2 BACKLOG + frontmatter + TOKEN_LEDGER row before the PR; R7.6 nothing retold that the ticket already holds |
| §8 | dependencies | **N/A because** no dependency is added or upgraded |

Three rules were pinned by a **recalled handle** rather than by change type alone — R5.2, R6.5 and
R6.7 — each inside a section already applicable, so the handle source adds **0** new sections while
naming exactly which rule bites.

## Phase 2 — design

`HANDLES: 9 recalled | 8 traced (command + result) | 1 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 3 recorded | 3 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Approach

`flows.py` is a **pure derivation module** beside 113/114/115 — no store import, no SQL, no LLM.
It takes rows the caller already pulled and returns a ranked, capped `FlowSet`:

1. **Seeds.** 113's `web_entry` bucket + declared `entry_points` give seed **files**; each expands to
   the entry **symbols** it declares (W3), so one controller with k actions yields k seeds.
2. **Trace.** BFS with **parent pointers** over the in-memory edge list restricted to
   `FLOW_KINDS = IMPACT_KINDS + (WRITES,)`. Only `RESOLVED` expands the frontier; a HEURISTIC/DYNAMIC
   neighbour becomes the trace's **terminal hop**, recorded with its tier and never expanded (C2, R5.2).
3. **Sink.** A `WRITES` target (`Table`/`Column`), a `Domain / Data` layer member, or a
   `PROVIDES_VIEW_DATA` target. **One flow per (seed symbol, sink) pair** (W4); no sink reachable ⇒
   one flow labelled `no-sink` (W2a/W2b).
4. **Attribute** on the **seed's** path via `module_of_path` (W5); an uncovered seed lands in an
   explicit `unattributed` bucket (AC4).
5. **Rank then cap.** Sort by (module coverage, trace length, path) and cap **globally** at
   `CA_MAX_RESULTS` (W1a); `flows_cut` names how many were dropped (W1b). The cap is applied to the
   **seed list before tracing**, so the ceiling bounds the work, not just the output.
6. **Bound.** Nodes visited across all traces ≤ `CA_IMPACT_MAX_NODES`; `walk_truncated` when it binds,
   and every derived count then reads as an under-estimate (C1, AC2).

### Rejected alternatives

| # | Alternative | Why rejected |
|---|-------------|--------------|
| 1 | `store.reachable_from(kinds=IMPACT_KINDS+WRITES)` per seed — the ticket's own Scope 3 | It returns a **flat set with no predecessor data** (`store.py:1739`), so no path can be reconstructed from it, and it is one SQL walk **per seed**. The exposure-checker raised this and was right. One kind-filtered pull + pure BFS replaces thousands of walks |
| 2 | Add `WRITES` to the global `IMPACT_KINDS` | Moves every existing `impact` / `reachable_from` / `explain_path` answer to buy one new surface (`contract.py:113`) |
| 3 | Surface flows on `architecture_overview` too | Outside Scope 7; a second consumer with no asked-for question is the speculative abstraction R1.2 forbids |

### Assumptions

| # | Assumption | Tag | Evidence |
|---|-----------|-----|----------|
| A1 | `WRITES` rows are reachable from the edge pull | **verified** | `store.py:824-826` applies no kind filter |
| A2 | `build_dataset` takes new keyword-only params with defaults without breaking callers | **verified** | T4 trace below found **10** call sites; existing optionals (`module_max: int = 0`) prove the shape |
| A3 | The viewer renders a new dataset key with no fetch | **verified** | `dataset.as_dict()` is embedded verbatim (`viewer.py` docstring); `connect-src 'none'` |

No `novel-untested` third-party or runtime assumption — nothing here leaves the process.

### Recalled type-2 handles — every one answered

| Handle | Answer | Command + actual result |
|--------|--------|-------------------------|
| `per-element-ceiling-leaves-total-unbounded` | **traced** | `grep -n "sample_max\|module_max" dataset.py` → `:410 sample_limit=reachability_sample_max`, `:417 limit=module_max` — both **per-element**. Folded in: the flow cap is applied to the **seed list**, globally, before tracing |
| `count-pin-in-blast-radius` | **traced** | `grep -rln "DATASET_VERSION\|ARTIFACT_VERSION" tests/` → `test_onboarding_dataset.py`, `test_artifact_contract.py`, `test_generate_onboarding.py`, `test_onboarding_viewer.py`. All **4** folded in as proof collateral |
| `derived-not-listed-invariant` | **traced** | `grep -rn "IMPACT_KINDS" tests/ code_atlas/` → `test_imports_link_the_file_they_name.py:210`, `store.py:1591`, `:1760`, `:1980`. `FLOW_KINDS` is **derived** as `IMPACT_KINDS + (WRITES,)`, never re-listed |
| `stamp-at-the-builder-not-the-wrapper` | **traced** | `grep -rn "build_dataset(" --include=*.py .` → **10** call sites: `generate_onboarding.py:134`, 4 tests, `scripts/viewer_report.py:66,:108`, `scripts/prose_cost_report.py:90,:105`, `build/lib/…`. Flows are stamped **inside `build_dataset`**; new params are keyword-only with defaults so all 10 keep working |
| `skip-dynamic-means-unlinkable` | **traced** | `grep -n "DYNAMIC\|unproven" store.py` → `:203 orphans with why, plus unproven (task 031)`. Same rule adopted: a DYNAMIC hop terminates the trace and is reported, never bridged |
| `denominator-is-the-population-not-the-subset` | **traced** | `grep -n "COVERAGE_NOTE" modules.py` → `:109`, `:112`. Flow coverage is stated over **all seeds**, not over emitted flows |
| `prove-the-guard-fails` | **traced** | `ls tests/test_onboarding_flows.py` → *No such file or directory*; `grep -rl "flows" code_atlas/onboarding/ \| wc -l` → `0`. The proving test is red because nothing it names exists |
| `measure-the-axis-the-defect-lives-on` | **traced** | `grep -c` over `benchmarks/121_onboarding-question-class.md` → **12** existing question rows, every one a **structure** question. AC8's row is the first on the **behaviour** axis |
| `empty-seam-inputs-masquerade-as-missing-data` | **does not apply because** | this change injects no seam: `flows.py` takes no `ProseWriter`, `Summarizer` or `LayerRefiner`, and 198 — not 197 — adds the prose slot |

### Smallest change list

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| 1 | `FlowStep`/`Flow`/`FlowSet` + `build_flows()` | `code_atlas/onboarding/flows.py` (new) | none identified — new file, no importer until #4 | R1, R4, W2–W5 | 1/9 |
| 2 | `flow_edges(kinds)` → `(source, target, kind, tier)`, kind-filtered in SQL | `code_atlas/store.py` | one new method; no existing signature moves (`dependency_edges_with_tier` untouched, so 143's caller is safe) | R3, C1 | 2/9 |
| 3 | seed-symbol expansion from the `web_entry` bucket | `code_atlas/onboarding/reachability.py` (read-only use) or `flows.py` | `ReachabilitySplit` is consumed by `architecture_overview.py` and `dataset.py` — **no field removed**, so both keep reading | R2, W3 | 3/9 |
| 4 | `flows=` keyword param + `flows` key; `DATASET_VERSION` 7 → **8** | `code_atlas/onboarding/dataset.py` | **10** `build_dataset` call sites (traced above) — keyword-only with a default keeps all 10 green; 4 test files pin the version | R7, AC6 | 4/9 |
| 5 | `flows.md` + manifest entry; `ARTIFACT_VERSION` 1 → **2** | `code_atlas/onboarding/artifact.py` | `test_artifact_contract.py` fails a shape change left at 1 (`artifact.py:72`); `generate_onboarding` removes only pages its manifest recorded | R7, AC6 | 5/9 |
| 6 | one flows section, every figure interpolated | `code_atlas/onboarding/viewer.py` | `tests/viewer_dom_stub.js` — 116's rule: a grep over the HTML is a false green | R7 (surface 2) | 6/9 |
| 7 | wire the new pull + pass `flows=` | `code_atlas/tools/generate_onboarding.py` | the tool's own docstring and `TOOLS.md` row | R7 | 7/9 |
| 8 | new tests + the 4 pinned conformance files | `tests/test_onboarding_flows.py` (new) + 4 traced files | proof collateral, planned not discovered | AC1–AC7, W1–W5 | 8/9 |
| 9 | AC8 question row; BACKLOG + frontmatter + `TOKEN_LEDGER` | `docs/benchmarks/121_…md`, `docs/BACKLOG.md`, this file, `docs/TOKEN_LEDGER.md` | R7.2 bookkeeping guard | AC8, R7.2 | 9/9 |

### Verification plan (per AC)

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|----|-----------|----------------|--------------------|-------------|
| AC1 | logic | unit | n/a | ✅ |
| AC2 | logic | unit (budget forced to 1) | n/a | ✅ |
| AC3 | integration | integration over a SQL fixture with a named + an unnamed write | authored | ✅ |
| AC4 | logic | unit | n/a | ✅ |
| AC5 | logic | unit (no-seed index refuses with a reason string) | n/a | ✅ |
| AC6 | integration | the 4 pinned conformance tests | n/a | ✅ |
| AC7 | integration | build twice, compare bytes | n/a | ✅ |
| AC8 | e2e | the committed benchmark row, ground truth hand-read first | authored | ✅ |
| W1a | **logic — but input-shape-dependent** (a **ranking**) | unit | **authored — no corpus configured** | ❌ → **exclusion E2** |
| W1b | logic | unit (`flows_cut` asserted) | n/a | ✅ |
| W2a/W2b | logic | unit | n/a | ✅ |
| W3 | logic | unit (k entry symbols ⇒ k flows) | n/a | ✅ |
| W4 | logic | unit (k sinks ⇒ k flows) | n/a | ✅ |
| W5 | logic | unit | n/a | ✅ |
| surface 2 | integration | `tests/viewer_dom_stub.js` headless DOM run | n/a | ✅ |

### Coverage-gap exclusions

- **E1 — the `flows.md` mermaid diagram renders in GitHub/VS Code.** Risk tier: low (presentation).
  Why deferred: no CI check can assert a third-party renderer. Follow-up: the same check 143 would
  need. `expiry: when a mermaid-rendering check enters scripts/gate.sh` · `seen: 143, 197` (2nd
  occurrence — not the third, so recorded, not escalated).
- **E2 — the flow ranking is proven on authored fixtures alone.** Risk tier: medium — a ranking is
  input-shape-dependent, and an authored fixture mirrors the assumption the code already makes (R6.3).
  Why deferred: `config.real_corpus_path` is `null` (verified: `python3 -c` over `.harness.json`
  printed `None`), so no corpus exists to run against. Follow-up: re-run the ranking against a real
  index and re-justify the constant, per R6.3's committed-reporter rule; ship
  `scripts/flow_report.py` alongside, as `layer_report.py`/`mirror_report.py` already do.
  `expiry: when config.real_corpus_path is configured` · `seen: 197` (first occurrence).
- **E3 — AC8 is not measured on this ticket.** Risk tier: medium — 121 exists because a surface
  shipped unmeasured. Why deferred: the only agent-facing surface available (`architecture_overview`)
  makes the gate red, measured above; the honest fix is a narrow tool, not a widened payload.
  Follow-up: **199**. `expiry: when 199 lands` · `seen: 197` (first occurrence).

### Proving test

`tests/test_onboarding_flows.py::test_flow_from_entry_symbol_reaches_the_named_column`

One flow from an entry **symbol**, three hops, ending on a `Column` the write statement named —
asserting the ordered steps, each step's layer and confidence tier, and the seed-keyed attribution.
Invocation: `.venv/bin/pytest tests/test_onboarding_flows.py -q`. **Currently red for the reason
R6.5 wants**: the module, the file and the store method it names all do not exist (traced above:
`ls` → *No such file or directory*, `grep -rl` → `0`).

### Rollback + porting

Rollback: revert the branch — `flows.py` and `flow_edges` are additive, and `DATASET_VERSION`/
`ARTIFACT_VERSION` revert with them; no migration, no persisted state outside the regenerable
`.code-atlas/onboarding/`. Porting: one repo (`app`); no shared code crosses `config.repos`.

`SCOPE: L` — unchanged from analysis. The change list is 9 items against the 9-file blast radius
analysis predicted; no tier crossing, no re-scope.

## Phase 3 — execute

`FALSIFY: 3 candidate(s) checked | 3 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`

The candidates are design's three Assumptions. **A1** (`WRITES` rows reach the pull) held — `flow_edges` returns them. **A2** (keyword-only params keep all 10 `build_dataset` call sites) held — the suite is green without touching one. **A3** (the viewer renders a new key with no fetch) held. The design *choices* that proved wrong are D1–D3 below, which is the deviation mechanism, not a falsified assumption.

**Red run, verbatim** (`ls tests/test_onboarding_flows.py` → *No such file or directory* at design
time; after the tests landed and before the sink split was fixed):

```
FAILED tests/test_onboarding_flows.py::test_flow_from_entry_symbol_reaches_the_named_column
FAILED tests/test_onboarding_flows.py::test_a_write_that_names_no_column_targets_the_table_at_dynamic
FAILED tests/test_onboarding_flows.py::test_one_flow_per_sink_when_a_seed_reaches_several
FAILED tests/test_onboarding_flows.py::test_the_cap_is_global_and_names_what_it_cut
5 failed, 7 passed
```

The red was a **real defect, not a missing file**: treating arrival in `Domain / Data` as a terminal
sink stopped every trace at the repository, one hop short of the column it came for. Fixed by
splitting **hard** sinks (`WRITES` / `PROVIDES_VIEW_DATA`, terminal) from **soft** ones (the domain
layer, which no longer stops the walk and is used only when no write was found at all).

### Deviations from the approved change list — recorded, not absorbed

| # | Deviation | Why | Matrix row |
|---|-----------|-----|------------|
| D1 | **Tried** `summary.flows` on `architecture_overview`, then **reverted it** | AC8 exposed a real contradiction — the 121 harness measures a **tool payload** and Scope 7 named no tool — so D1 was the attempt to fix it. **The measurement then rejected D1 itself** (below). Reverted on the maintainer's call; AC8 is deferred to **199** as exclusion E3. `architecture_overview.py` is untouched in the final diff | AC8, R7 |
| D2 | `FLOW_KINDS` moved from `contract.py` to `flows.py` | 022 AC3's guard sweeps every named subset `contract` exports and requires the tier-2 words to join none — *"a subset added later is covered without editing a list here"*. The guard was right and the design was wrong; the subset belongs to the consumer that walks it (138's `rule.kinds`). `contract.WRITES` stays: a bare string is not a swept subset | R3, R8 |
| D3 | `ARTIFACT_VERSION` **not** bumped after all | Phase 1's AC validation conflated `manifest_dict` with `OnboardingArtifact.as_dict()`. `ARTIFACT_VERSION` versions the pages/tour/stops object graph, which this change does not touch; the manifest gained `flows_doc` and carries `DATASET_VERSION` 8, which is the version that did move. `test_ac2_a_version_bump_without_a_new_pin_fails` caught it | AC6 |

**D1 was measured and rejected — the number, not an opinion.** With `summary.flows` on the tool and
AC8's question in the registry, the repo's own gate went red:

```
GATE FAILED: tokens-to-answer ratio 0.53 is below the floor 0.63 (grep 3065 / atlas 5786 tokens)
precision 0.944 | unexpected 6
```

To read a 4-file trace an agent had to buy the whole overview payload — layer table, matrix, hubs,
reachability, capability table, mirrors — ~2,400 tokens against grep's 852. And because
`summary.flows` returns **every** flow, a question about **one** request over-answered by 6 files,
which is precision correctly reporting a true property of the surface. After the revert:

```
ratio 0.661 | recall 1.0 | precision 1.0 | unexpected 0   (floor 0.63 / 1.0 / 1.0)
```

The lesson is 121's, arriving one step earlier this time: the measurement ran **before** the PR and
stopped the wrong surface from shipping. The agent-facing half needs its own narrow tool, which is
**199** — not a widened payload. All three deviations therefore **shrink** the final diff; the change
list stays at the approved **9** items and `SCOPE: L` is unchanged.

### Count pins moved (the `count-pin-in-blast-radius` trace paid off)

`test_core_is_language_agnostic` and `test_sql_confinement` both pin `len(core_modules()) == 75`;
`flows.py` makes it **76**. Both were named as proof collateral at design time, so neither was a
surprise. `test_onboarding_dataset` pinned `DATASET_VERSION == 7` → **8**.

### One process defect worth recording

Two `str.replace()` edits silently **no-opped** on an anchor that did not exist, and
`from __future__ import annotations` hid the resulting missing import until the code path actually
ran. Every later edit asserted its anchor count first. This is the same class as
`construct-the-premise-do-not-race-for-it`.

## Phase 4 — review

`CLAIMS: 5 claim(s) from 1 lesson entr(ies) | T1=0 T2=3 T3=1 T4=0 T5=1 T6=0 | 0 unclassified`

Reviewer seat waived by run arg; challenger ran and returned **BLOCK**. It was right, and the most
serious finding is one no test of mine would have caught.

### Actioned — real defects

| # | Finding | Fix |
|---|---------|-----|
| F1 | **Defect 130 reintroduced.** `seed_files` used bare `responsibility_layer`, which is deepest-wins, so `tests/controllers/FooTest.php`, `spec/handlers/YSpec.php` and `vendor/a/src/controllers/X.php` all read as **request entry points**. 130 was closed for exactly this | Seed selection now goes through 131's `reading_seed_rank`, which sinks a test or vendor path on **any** segment — one definition site, not a fourth copy. It also *gains* `public/index.php`, which the old check missed. New test `test_a_test_or_vendor_path_is_never_a_request_entry` |
| F2 | **119 provenance dropped** — no field said whether a seed was declared or vocabulary-read | `seed_files`/`seed_symbols` return `(path, signal)`; `Flow.signal` carries it to the payload. Declared `stub_roots` are honoured too. Two new tests |
| F3 | `truncated` diverges from `walk_truncated`, the repo's established name for this exact case (`impact_modules.py`, `find_orphans.py`) and the one the ticket quotes | Renamed throughout, payload included |
| F4 | `_deepest`'s docstring claimed "the furthest node"; it returns the sorted-last discovered qname — no depth is recorded | Renamed `_endpoint` and the docstring now says what it does, and why inventing a depth would be a claim the walk cannot back |
| F5 | `store.flow_edges` — the one new SQL method — had **no test of its own**; every flows test hand-builds its rows | Two tests over a real `edges` table: the kind filter, the kind column, the RESOLVED-beats-DYNAMIC roll-up, and the empty-kind-set case |
| F6 | The raw ticket still stated AC8, Scope 3, Scope 4 and Scope 6 as requirements that the diff does not meet | All four now say so **in the ticket**, with what superseded them. A criterion a later reader trusts must not read as satisfied when it was not |

### Answered — superseded, not dismissed

- **Scope 3 (`store.reachable_from`)** — superseded at Gate 2 (*Rejected alternative 1*): it returns
  a flat set with no predecessor data, so no path is reconstructible, and it is one SQL walk per
  seed. The challenger is ticket-blind and could not see that; its reading of the ticket was correct.
- **Scope 6 (refuse when the cap binds)** — superseded by ratified want-decision **W1a/W1b**.
- **C1 (R4.3, "unbounded pull")** — `flow_edges` is kind-filtered and sits beside
  `node_universe()` / `dependency_edges_with_tier()`, two pulls of the same shape already accepted
  at this call site because the artifact describes the whole repo (196). **The challenger still has
  half a point**: this is a *second* pull of overlapping rows, and design H7 had assumed one. Not a
  new R4.3 breach, but a cost worth a follow-up; recorded here rather than argued away.

### The disclosure the challenger volunteered — a real process defect

It reported that an unscoped `grep` over `git diff` surfaced working-doc content, because
`work_doc_mode: embed` puts the working doc **inside the ticket file**, and the ticket file is in the
diff. **The ticket-blind guarantee cannot hold under `embed` for any change that touches its own
ticket.** The separator prevents an honest reader from reading on; it cannot prevent a grep. The
agent flagged it instead of pretending its view was clean, and re-derived its verdicts independently.
This is a mango-level concern, not a repo one → `docs/SKILL_GAP_CANDIDATES.md`.
