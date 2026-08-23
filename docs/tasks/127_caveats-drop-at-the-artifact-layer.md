---
id: 127
slug: caveats-drop-at-the-artifact-layer
title: Onboarding — a caveat the dataset carries can vanish in the rendered map, and nothing notices (M11)
phase: 3
milestone: M11
status: done
depends_on: [100, 112, 113, 116, 119]
---

## Why this exists (measured on this tree, 2026-08-23)

[100](100_claim-signing-output-mode.md)'s finding was *"the tool held evidence-grade payloads that
never reached the artifact."* The same defect class is recurring **one layer out**: a caveat the
onboarding dataset carries can be absent from the generated `index.html`, and no test can tell.

This is R5.5's own falsifier — *"a caveat present at one detail level and absent at another for the
same underlying fact"* — with the rendered artifact as the other detail level.

**Confirmed instance (one, not the three proposed).** Verified against the current generator before
writing any code:

| Proposed instance | Verdict |
|---|---|
| `summary.mirrors` path-not-bytes caveat missing from the map | **Not reproducible.** `viewer.py` renders `MIR.caveat` twice — as the mirror section's note and under *"What this page cannot tell you"*. |
| Reachability renders the web-entry-point count without the globs that produced it | **Confirmed.** `dataset.py` hands `declared_entry_points` to `split_reachability`, which consumes the globs and keeps none of them; `ReachabilityBucket` is `bucket · label · signal · note · count · sample · sample_truncated`. The map prints the count and the signal *sentence*, never the patterns or the per-signal split. |
| Search-palette truncation | Covered by [126](126_search-palette-clusters-into-one-subtree.md); this ticket only proves the guard would have caught it. |

The confirmed instance is [119](119_reachability-signal-provenance.md) exactly — README already
documents why `reachable_from` is left unsigned (*"the claim is only as good as `CA_ENTRY_POINTS`,
which the line cannot carry"*), and the map renders the derived number carrying neither the globs nor
the caveat. 119 measured what that costs: a stale declaration moved the bucket **901 → 341** and
nothing in the output could expose it. **The two close as one change.**

## Scope

**The guard is the deliverable.** The fixes are its first customers.

- **One derivation, at one definition site.** `OnboardingDataset` (`dataset.py`) is the contract every
  renderer reads — [112](112_onboarding-dataset-contract.md) made it so. "Present in the dataset,
  absent in the rendered page" is therefore the *definition* of the drop, and a caveat list kept
  anywhere else is precisely the hand-kept list R6.7 forbids. Derive the caveat set by walking the
  dataset's own sections; never enumerate it.
- **The guard.** For every derived caveat, assert a corresponding string in the generated
  `index.html`. Run it against the current generator first and record the red run (R6.5).
- **Close 119 with it.** Carry the declarations into the dataset: per bucket
  `signals: {declared: N, vocabulary: N}`, and per declared pattern the pattern itself with
  `files_matched` and `zero_inbound_claimed`. Render them beside the count in the map, the markdown
  and the `architecture_overview` payload. Classification, bucket order and the raw total move by
  nothing (119 AC1/AC4/AC6).
- **119 AC2 is restated.** Its numbers (341 = 93 + 248, 901 = 653 + 248) are anchor measurements and
  the anchor is not on this host. The assertion becomes the *arithmetic* on a fixture — a bucket count
  equals declared + vocabulary, and a pattern's `files_matched` may exceed its `zero_inbound_claimed`
  — with the anchor figures recorded as unverified here rather than dropped.

## Acceptance criteria

1. **AC1 (red first).** The guard fails on the pre-change generator for the entry-point globs, and
   would have failed for 126's truncation disclosure. A guard whose first run is green proves nothing.
2. **AC2.** The caveat set is **derived** from the dataset: adding a caveat-bearing field to the
   dataset extends the guard with no test edit (R6.7), proven by a test that adds one.
3. **AC3.** Per-bucket `signals` and per-pattern `files_matched` / `zero_inbound_claimed` appear in all
   three renderers; a pattern matching nothing reports zero rather than being omitted (119 AC3).
4. **AC4.** Classification is unchanged — bucket counts, bucket order and `total` are identical before
   and after, asserted in a test (119 AC1).
5. **AC5.** Deterministic and SQL-free: computed from the metrics 113 already walks, byte-stable
   (R4.2/R4.3), no new query.
6. **AC6.** No judgment: nothing in the output calls a declaration stale, wrong or suspicious (119 AC6).

## Not in scope

No rendering abstraction. One derivation function and one guard — R1.2 and R7.4; a `CaveatRenderer`
with one caller is the dead abstraction those rules name.

---
<!-- working doc (work_doc_mode: embed) — everything above this line is the ticket -->

## Session status

- **Current phase:** complete (shipped) — PR [#151](https://github.com/cuongdinhngo/code-atlas/pull/151)
- **work_doc_mode:** embed (plain local-file ticket)
- **SCOPE:** M · **TIER:** full
- **CHALLENGER:** OFF (`--no-challenger`, run args) · **Review:** SKIPPED (run args)
- **Branch:** `fix/126-search-palette-clusters-into-one-subtree` (shipped with 126 — 127's guard is
  126's disclosure test, and 127 closes 119; one PR carries all three)
- **BASELINE:** 1749 passed (after 126)

## Phase 1 — Analysis: requirements matrix

| # | Kind | Requirement | Source | Proven by |
|---|---|---|---|---|
| G1 | G | A caveat the dataset carries cannot silently fail to be rendered | ticket §Why | AC1, AC2 |
| R1 | R | Derive the caveat set from the dataset payload; never enumerate it (R6.7) | ticket §Scope | AC2 |
| R2 | R | Guard: every derived caveat appears in the **rendered** page | ticket §Scope | AC1 |
| R3 | R | Per bucket, `signals: {declared, vocabulary, structure}` | 119 §Scope | AC3, AC4 |
| R4 | R | Per declared pattern: the pattern, `files_matched`, `zero_inbound_claimed` | 119 §Scope | AC3 |
| R5 | R | All three renderers carry it: overview payload, markdown, map | 119 §Scope | AC3 |
| C1 | C | Classification, bucket order and `total` unchanged | 119 AC1 | AC4 |
| C2 | C | Deterministic, SQL-free, byte-stable (R4.2/R4.3) | 119 AC5 | existing byte-stability test |
| C3 | C | No judgment: nothing calls a declaration stale or wrong | 119 AC6 | AC6 |
| C4 | C | No rendering abstraction (R1.2/R7.4) | ticket §Not in scope | diff review |
| AC1 | AC | Guard red on the pre-change generator; green after | ticket | new guard test |
| AC2 | AC | A new caveat-bearing field is covered with no guard edit | ticket | derivation test |
| AC3 | AC | Signals + per-pattern claims in all three renderers; a glob matching nothing reports 0 | ticket | new tests |
| AC4 | AC | Bucket counts, order and total identical; a dropped bucket stays dropped | ticket | new tests |
| AC5 | AC | Byte-stable, no new query | ticket | existing tests |
| AC6 | AC | No judgment wording | ticket | new test asserts the caveat text is descriptive |

**Clarifications needed: 0.**

## Phase 2 — Design

**The derivation site, and why it is the definition site.** `OnboardingDataset.as_dict()` — the payload
[112](112_onboarding-dataset-contract.md) made *the* contract every renderer reads. `derive_caveats`
walks that payload recursively and yields `(dotted-section, text)` for **every mapping that owns a
non-empty `caveat` key**. So "a section owns a caveat" is a structural fact about the contract, not a
list someone maintains: a section that grows a `caveat` is covered the moment it exists (R6.7).

**The guard runs under `node`, against rendered text — not against the file.** The page embeds the whole
dataset as JSON, so a file-level `in html` check would pass vacuously for every caveat forever. The
guard asserts each caveat appears in a **rendered section's** text via the existing DOM harness. That
is the assertion R5.5 actually wants: rendered, not merely shipped.

**Approach, in three moves.**

1. `reachability.py` — `_bucket_of` also returns *which* signal decided the bucket
   (`declared` · `vocabulary` · `structure`); the split gains per-bucket `signals`, a
   `patterns` list (`pattern` · `kind` · `files_matched` · `zero_inbound_claimed`, attributed to the
   first matching pattern so the numbers stay disjoint), and one `caveat` naming what a declared count
   is. `files_matched` counts indexed modules the pattern matches — the set 113 already walks, so no
   new query.
2. `dataset.py` — `PathIndex` gains the cap `caveat` that the map currently hardcodes in its own
   wording, single-sourcing it (this is the second red instance); `derive_caveats` lands here.
3. Renderers — `viewer.py` renders the signals, the pattern rows and both caveats; `artifact.py` and
   the dataset text summary render the same facts as lines. `architecture_overview` needs no change:
   it serialises `split.as_dict()`.

**Rejected alternatives.**
- *A module-level `CAVEATS = [...]` registry* — the hand-kept list R6.7 forbids, and the exact thing
  that drifts when caveat N+1 arrives.
- *Assert against the raw HTML* — vacuously green, since the dataset is embedded verbatim.
- *A `CaveatRenderer` seam* — one implementer, no second caller: R1.2 and R7.4.
- *Judging the declaration* (flagging a glob whose `files_matched` far exceeds its claims) — 119 AC6
  forbids it. The numbers go beside each other; the operator decides.

**Change list (approved scope).**
`code_atlas/onboarding/reachability.py` · `code_atlas/onboarding/dataset.py` ·
`code_atlas/onboarding/viewer.py` · `code_atlas/onboarding/artifact.py` ·
`tests/test_caveats_reach_the_artifact.py` (new) · docs (BACKLOG rows for 127 **and 119**, both
frontmatters, token ledger).

**Proving test.** `test_every_dataset_caveat_is_rendered_in_the_map` — red on the pre-change generator
for the reachability caveat and the path-index caveat, green after.

**Rule compliance.** R6.7 derived, not listed · R6.5 red run recorded · R5.5 the caveat is sourced
from the computation that owns the fact · R4.2 fixed key order, sorted patterns · R1.2/R7.4 no new
abstraction · R2.2 no repo names (patterns come from config, printed as given).

## Phase 3 — Execute summary

- `code_atlas/onboarding/reachability.py` — `_bucket_of` now returns *what proved* the bucket
  (`declared` · `vocabulary` · `structure`) and which pattern did it; `ReachabilityBucket.signals`
  tallies all three kinds (zeros included); new `PatternClaim` reports each declaration's
  `files_matched` beside its `zero_inbound_claimed`, attributed first-match so the claims stay
  disjoint; `DECLARATION_CAVEAT` rides on the split.
- `code_atlas/onboarding/dataset.py` — `PathIndex.caveat` single-sources the search-cap sentence the
  map used to hardcode; **`derive_caveats`** walks the payload and yields every section that owns a
  non-empty `caveat`; `DATASET_VERSION` 6 → 7.
- `code_atlas/onboarding/viewer.py` — bucket cards carry the tally, the reach note carries the caveat
  and one row per declared glob, and the provenance list now renders `path_index.caveat` instead of
  rebuilding it.
- `code_atlas/onboarding/artifact.py` + the dataset text summary — the same facts as markdown lines.
- `code_atlas/tools/architecture_overview.py` — **unchanged**; it serialises `split.as_dict()`.
- `tests/test_caveats_reach_the_artifact.py` — 7 tests: the rendered-caveat guard, the derivation
  test, per-pattern claims incl. a glob matching nothing, the signal arithmetic, classification
  unchanged + a dropped bucket staying dropped, the no-judgment check, and a mutation showing the
  guard has teeth.

**RED RUN (R6.5), recorded before any renderer changed.** With the dataset carrying the caveats and
the page still rendering its own wording:

```
tests/test_caveats_reach_the_artifact.py::test_every_dataset_caveat_is_rendered_in_the_map
E  AssertionError: ['reachability']
```

The dataset knew; the page did not. **GREEN after the three renderers carry it.**

**Delta-green:** 1749 → **1756 passed** (+7). `scripts/gate.sh` → **GATE GREEN, 12/12, 0 skipped**.

## Decision log

- **The guard asserts RENDERED text, not the file.** The page embeds the whole dataset as JSON, so
  `caveat in html` is green for every caveat forever. The guard runs the page under `node` and reads
  the rendered sections — the only formulation that can fail.
- **Instance #1 of the review was not reproducible and no code was written for it.** `MIR.caveat`
  already renders twice. It is now *guarded*, which is the durable part.
- **`path_index.caveat` was green on arrival, and single-sourced anyway.** The Python wording matches
  what the map built by hand, so the guard passed; moving the sentence into the dataset means either
  side drifting now turns it red (R5.5).
- **119 AC2 restated, not dropped.** Its anchor figures (341 = 93 + 248) are not measurable on this
  host; the assertion became the arithmetic — every bucket's tally sums to its count, and a
  declaration's `files_matched` and `zero_inbound_claimed` are reported separately. The anchor
  numbers stay unverified here, and say so.
- **No judgment shipped** (119 AC6): a test asserts the caveat contains none of *stale · wrong ·
  suspicious · false · should*.

## Cost ledger

| Phase | Dispatch | Tokens | Notes |
|---|---|---|---|
| refine / analysis / design / execute | none | 0 | no subagent dispatched this run |
| review | — | — | SKIPPED (run args) |
| **Total** | **0 dispatch** | **0** | main-loop spend unmeasured (host surfaces no usage block) |
