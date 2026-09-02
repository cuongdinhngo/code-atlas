---
id: 208
slug: an-undeclared-reachability-bucket-reports-zero-as-a-measurement
title: "`Vendored dependencies: 0` on a repo whose tour is half vendored code — a reachability bucket with no declaration and no vocabulary hit prints a bare `0`, which reads as a measured absence rather than an unasked question"
phase: 3
milestone: M11
status: done
depends_on: [113, 119, 130, 182, 186]
---

## Why this exists (measured on the anchor monorepo, 2026-09-02)

`overview.md`'s reachability split, in the run that produced today's artifact:

```
- **Vendored dependencies**: 0
  - Third-party code that ships with the repo; not this team's surface.
  - signal: declared dependency roots, or a path naming third-party code
```

The same artifact, in the same run:

- gave **47** module pages to files under `Zend/`;
- opened tour step 8, labelled **`Middleware / Auth`**, with `pdf/pdf/filters/FilterLZW.php`
  and `adodb/session/adodb-encrypt-mcrypt.php`;
- gave tour steps 12 and 13 to `qunit-1.15.0.js` and `MPDF61/tests/mPDFTest.php`;
- ranked `tinymce.d.ts` the busiest file in the `js` module at `fan_in 1791`.

Every other bucket prints a `by signal:` breakdown. Vendor prints none, because it has nothing to
break down.

> **Measurement provenance.** The artifact quoted above predates
> [204](204_bare-name-resolution-has-no-language-predicate.md). The `fan_in 1791` on `tinymce.d.ts`
> is degree-derived and will move; the `Vendored dependencies: 0`, the 47 `Zend/` pages and the
> contents of tour step 8 are decided by `stub_roots`, the layer classifier and path membership —
> no edge is involved, so this ticket's evidence is unaffected.

### The bucket is honest and still misleads

This is **not** a broken detector. `code_atlas/onboarding/reachability.py:240-249` gives the bucket
exactly two ways to fire:

```python
    return VENDOR, SIGNAL_DECLARED, ("stub_roots", hit)     # :240
...
        if layer == LAYER_VENDOR:                            # :248
            return VENDOR, SIGNAL_VOCABULARY, None
```

On the anchor, `stub_roots` is commented out in `.code-atlas.toml` (*"Round 2, not enabled yet"*),
and the `Vendor / Framework` layer holds **2 modules of 24,535** — so no zero-inbound file reaches
either branch. `0` is the arithmetically correct output of a question nobody asked.

A reader cannot tell that apart from the other reading of `0`, which is *"this repo vendors
nothing."* The line sits in a list where every neighbour **is** a measurement: `Tests and fixtures:
1090` was counted, `Not statically reachable: 6143` was counted. Placing an unasked question in that
column, formatted identically, is the artifact attesting past what it can distinguish.

### The rule the repo already holds

**R5.6 — never attest past what the payload can distinguish.**
**R1.9 — a single-answer classifier is not a membership test.** The vendor bucket asks the layer
classifier, which returns *one* layer per module; a file is vendored *and* a shared library, and the
single-answer classifier can only say the latter. That is 1.9's failure mode exactly, in a consumer
1.9 did not sweep.

[182](182_find-orphans-answers-with-rows-it-has-flagged-unreliable.md) established the posture for a
tool: refuse rather than dump. [186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md)
established it for an empty answer: say what you could not see. Neither reached the artifact's
reachability table, and the split's own footnote shows the author was reaching for this —
*"A count labelled declared comes from the globs listed beside it, matched as written; the core does
not check whether a declaration still holds."* The caveat covers a **stale** declaration. It does not
cover an **absent** one.

## Scope

1. **Distinguish "measured zero" from "no signal available"** for every bucket in `BUCKET_SPECS`,
   not only vendor — the shape is general and `TEST`'s `declared` flag is already hard-coded
   `False` at `reachability.py:315`.
2. **Render the distinction.** A bucket whose signals were all unavailable says so where its count
   would be, in `overview.md`, in the dataset, and in the viewer — the three renderers
   [127](127_caveats-drop-at-the-artifact-layer.md) found dropping caveats.
3. **Point at the remedy.** An undeclared bucket names the setting that would populate it
   (`stub_roots`), the way the web-entry bucket already names the glob that claimed its modules.
4. **Re-measure the anchor with `stub_roots` declared** and record what the bucket then reports. If
   declaring it moves the tour off mPDF and adodb, that is a finding
   [206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) needs before it picks
   its defaults; if it does not, 206's scoping is the only lever and this ticket should say so.

### Explicitly not in scope

- **A better vendor detector.** No new vocabulary, no manifest parsing, no `vendor/`-in-the-core
  heuristic (**R2.2**). The defect is that an unasked question is formatted as an answer.
- **Changing what `stub_roots` means** or enabling it on the anchor repo. Scope 4 measures; the
  anchor's own config is the anchor's decision.
- **The layer classifier's single-answer shape.** Named above because it is why the vocabulary
  branch cannot fire, but fixing **R1.9** across the layer seam is its own ticket and much larger.
- **The other artifact honesty gaps.** [205](205_a-module-page-per-node-budget-slot.md) (C1),
  [207](207_the-artifact-answers-no-question-a-newcomer-asks-first.md) (missing orientation).

## Constraints

- **R1.8** — one implementation of "was this bucket's signal available?", read by all three
  renderers rather than re-derived per renderer; that re-derivation is exactly what 127 fixed once.
- **R3.5** — a dataset field is a schema move: bump `DATASET_VERSION` and move the viewer with it.
- **R4.2** — deterministic; a bucket's rendering depends only on the resolved config and the index.
- **R6.5 / R6.9** — the guard is observed failing first, on a fixture with an undeclared bucket, and
  asserts on the **emitted `overview.md`**, not on a `ReachabilityBucket` object.
- **R5.4** — the field the reader acts on holds one register: the count stays a number, and the
  availability is a sibling field, never a string smuggled into the count.

## Acceptance criteria

1. A bucket whose declaration is absent and whose vocabulary matched nothing is distinguishable, in
   the dataset, from a bucket that was measured and found zero.
2. `overview.md` renders that distinction in words, and names the setting that would populate the
   bucket.
3. The viewer and the dataset carry the same distinction — no renderer re-words it (**R1.8**, 127).
4. A fixture repo with an undeclared bucket fails the pre-change guard and passes the post-change
   one.
5. A repo where every bucket has a signal produces output byte-identical to today's.
6. Scope 4's re-measurement is recorded in the ticket's close-out with the numbers, whichever way it
   comes out, and 206 is updated if it changes that ticket's assumptions.

## References

[113](113_reachability-split.md) (the split), [119](119_reachability-signal-provenance.md) (the
`by signal:` provenance this bucket cannot print), [130](130_web-entry-bucket-counts-test-controllers.md)
(the last bucket-membership defect), [127](127_caveats-drop-at-the-artifact-layer.md) (three
renderers, one caveat), [182](182_find-orphans-answers-with-rows-it-has-flagged-unreliable.md) and
[186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) (refuse, and say what you could not
see — the posture this applies to the artifact),
[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) (the tour that made the
`0` visible).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 208 · **work_doc_mode:** embed · **Current phase:** 5 finalise — complete on disk. **Next action:** push the branch and open the PR against `main`. **Revert path:** `git revert` the two commits on `fix/208-an-undeclared-reachability-bucket-reports-zero-as-a-measurement`, or close the PR unmerged; both version stamps return with it.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** bug.
- Run arg *"with skipped reviewer"* = `--no-reviewer`; the reviewer seat is waived, the **challenger
  keeps its seat** (AGENTS.md *Maintainer workflow*).
- Branch `fix/208-an-undeclared-reachability-bucket-reports-zero-as-a-measurement`, based on `main`
  at `6ad664d` — 205's merge, so this branch carries 205.
- Contract `.mango/run-contract-208.txt`. RECONCILE t0: 10 declared | 8 re-run | **0 holding** |
  8 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 14 reference(s) checked | 0 missing | 3 ambiguous (surfaced, not blocking)`
`RECALL: 6 claim(s) surfaced | 0 by symbol | 5 by handle | 1 by area | 0 by finding | 8 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 0 want-decision asked | 8 how-decision resolved+cited | 0 ASSUMED | skip: no`

Every in-repo reference resolved: the two branches at `reachability.py:240` and `:248`, the
hard-coded `TEST: False` at `:315`, `BUCKET_SPECS` (`:58`), `DATASET_VERSION = 10`
(`dataset.py:53`), the three renderers (`artifact.py:439`, `dataset.py:528`, `viewer.py:712-738`),
and all ten referenced tickets. The three ambiguous references are the *emitted artifact* the ticket
quotes (a generated output, not a repo file) — and rather than leave them ambiguous I re-derived them
on a post-204 anchor index:

| The ticket's claim (pre-204 artifact) | Post-204 re-measurement |
|---|---|
| `Vendored dependencies: 0` | **0** — held. `by signal: none` |
| `Tests and fixtures: 1090` | 1,106 |
| `Not statically reachable: 6143` | 6,052 |
| zero-inbound raw total | **12,712** of 24,535 modules |
| 47 module pages under `Zend/` | **15** `Zend/` files in the 500-file tour (the pages themselves are gone — 205) |
| tour step 8 opens on mPDF and adodb | **11** MPDF + **5** adodb files still in the tour |
| tour steps 12–13 on `qunit-1.15.0.js` and `MPDF61/tests/` | **`qunit` is no longer in the tour at all** |
| `tinymce.d.ts` busiest in `js` at `fan_in 1791` | **`tinymce` is no longer in the tour at all** |

The last two moved exactly as the ticket's own provenance note predicted: they are degree-derived,
and 204 removed the false JavaScript→PHP out-edges that bought them their rank. **The
path-decided evidence — the `0`, and vendored code sitting inside the tour — held.**

**No want-decision survived.** Every decision this ticket carries is answerable from the ticket text,
the rule book, or the code, so refine asked the maintainer nothing (`a = 0`).

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | What is the predicate for "unasked question"? | **AC1's own:** the bucket's declaration is absent **and** its count is 0. Not *"undeclared with a non-zero count"* — that is a different (real) defect, and H8 records why it is out of scope | ticket AC1 |
| H2 | Where does the wording live? | **One function in `reachability.py`**, keyed on the setting name, so all three renderers print identical words. That is 127's defect class and R1.8's rule (`one-rule-for-every-subject-slot`, promoted 2026-08-27) | R1.8; `dataset.py:283` (`derive_caveats`, the same shape); ticket Constraint R1.8 |
| H3 | Does the count field change type? | **No.** `count` stays an `int`; `declaration` and `unmeasured` are siblings. A string smuggled into a count is exactly what R5.4 forbids | R5.4; ticket Constraint R5.4 |
| H4 | Which name does the artifact print — `stub_roots` or `CA_STUB_ROOTS`? | **The project-file key, `stub_roots`.** No module under `code_atlas/onboarding/` imports `code_atlas.config` (verified: zero hits), so reaching for `env_name()` would be the first such import, and hard-coding the `CA_` prefix in a second place would duplicate `config.env_name` — R6.7's *derived, not listed*. The env form is documented in `docs/TOOLS.md`, which this ticket updates | `grep -rn "from code_atlas.config import" code_atlas/onboarding/*.py` → no output; `config.py:107-109` |
| H5 | Does `DATASET_VERSION` bump? | **Yes, 10 → 11**, and the pin at `tests/test_onboarding_dataset.py:330` (`== DATASET_VERSION == 10`) moves with it — the double-pin exists so a bump cannot be silent | R3.5 (`version-the-document-that-moved`, promoted 2026-08-31); `dataset.py:53`; `test_onboarding_dataset.py:317-330` |
| H6 | Does the existing `dropped` path change? | **No.** `dropped` answers *"the vocabulary signal carries no information for this repo at all"* and drops the row entirely; this adds the finer case where the row **is** rendered. Two different questions, two fields — collapsing them would be `one-field-two-questions` | `reachability.py:47-51`, `:318-320`; ticket Scope 2 (*"says so where its count would be"*) |
| H7 | 113's AC4 test calls exactly this case an *"honest zero"*. Which claim wins? | **208's.** 113 asserted the *row is rendered rather than omitted*, and that still holds; what 208 adds is that the rendered row says which question produced its 0. The test is amended to assert both, and the amendment is named in the diff rather than left to look like a regression | `tests/test_reachability_split.py:126-134`; ticket *Why this exists* (*"0 is the arithmetically correct output of a question nobody asked"*) |
| H8 | Is *undeclared with a non-zero count* in scope? | **No.** A vendor bucket the vocabulary partly filled is a **floor, not a total**, and saying so is a second, larger claim about every count in the table. R7.1 keeps this ticket to the defect it names; recorded as a follow-up candidate instead | R7.1; ticket AC1's own predicate |

**Constraints surfaced from the scan** (not in the ticket):

- `BUCKET_SPECS` is unpacked in exactly **two** places (`reachability.py:318` and
  `tests/test_reachability_split.py:222`), so widening the tuple is a two-site change — and the test
  is a *pin* on the tuple's shape, which is the point.
- **`Vendored dependencies: 0` survives the remedy the ticket proposes**, and that is Scope 4's real
  finding — see the AC6 block in Phase 1.

**Recalled claims — advisory, surfaced only.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `196-C1` gate-on-the-invariant-not-on-presence | 2 | handle | **Yes** — the new field must gate on *was a declaration given*, never on the presence of a key |
| 2 | `196-C2` grep-the-derived-name-not-the-source-name | 2 | handle | **Yes** — to find every renderer of the figure, grep the rendered name, not the dataclass field |
| 3 | `205-C1` grep-the-keyword-argument-too | 2 | handle | **Yes** — an hour old, from the same session; the blast-radius trace below greps constructor call sites too |
| 4 | `205-C2` a-capped-search-is-not-a-search | 2 | handle | **Yes, and it fired during this phase**: a compacted `grep` printed *"4 matches in 3 files"* and no rows, and the handles it was hiding are three of these. Re-run through `rtk proxy` |
| 5 | `205-C3` strip-list-is-not-an-emit-list | 2 | handle | Surfaced; **does not apply** — no set here filters in the opposite direction |
| 6 | `202-C3` a fix confined to one consumer leaves the others lying | 5 | area (tools / payload honesty) | **Yes** — three renderers, and 127 is the ticket's own precedent |
| — | 8 retired: `do-not-attest-past-the-payloads-resolution` (**R5.6**), `source-the-caveat-from-the-computation` (**R5.5**), `one-rule-for-every-subject-slot` (**R1.8**), `version-the-document-that-moved` (**R3.5**), `assert-the-consumer-not-the-field` + `guard-asserts-rendered-not-shipped-bytes` (**R6.9**), `derived-not-listed-invariant` (**R6.7**), `prove-the-guard-fails` (**R6.5**) | 2 | handle | **Skipped as retired** — each is now a ratified rule, and every one of those sections is answered in the `RULE SECTIONS` line below |

## Phase 1 — analysis

`PREMISE: 14 reference(s) checked | 0 missing | 3 ambiguous (surfaced, not blocking)`
`RECALL: 6 claim(s) surfaced | 0 by symbol | 5 by handle | 1 by area | 0 by finding | 8 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope [+ Explicitly not in scope], Constraints, Acceptance criteria, References) | 5 decomposed | ROWS: C=5 R=8 G=4 AC=6`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 8 applicable — 3 by change-type | 5 by recalled handle — §1 (recalled handle: one-rule-for-every-subject-slot → R1.8) ✅ · §2 (change-type) N/A (no adapter, no language named, no repo or framework name added — the ticket forbids a vendor vocabulary outright) · §3 (recalled handle: version-the-document-that-moved → R3.5) ✅ · §4 (change-type) ✅ · §5 (recalled handle: source-the-caveat-from-the-computation → R5.5, do-not-attest-past-the-payloads-resolution → R5.6) ✅ · §6 (recalled handle: prove-the-guard-fails → R6.5, derived-not-listed-invariant → R6.7, assert-the-consumer-not-the-field → R6.9) ✅ · §7 (change-type) ✅ · §8 (change-type) N/A (no dependency added, moved or removed)`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

Both lines above `SECTIONS:` are carried forward from Phase 0.

`viewer.py` renders HTML from Python and is edited here, so the *file* is UI-shaped; TRACK stays
backend because there is no browser surface under `config.breakpoints`, no design token and no
interaction change — the edit adds one sentence to an existing card, and its guard is the repo's
existing headless assertion on the emitted string.

### BASELINE

`.venv/bin/python -m pytest -q`, **Ran at 6ad664d** — this branch's point, which carries 205:

```
2775 passed in 268.74s (0:04:28)
```

### The defect, classified

`data` (`config.cause_taxonomy`) at `code_atlas/onboarding/reachability.py:318-320`: the split
already distinguishes *"this bucket's signal carries no information for this repo"* (dropped, with
its reason) from *"this bucket was measured and found zero"* (rendered) — but the test it uses for
the first is **global**: `not vocabulary`, true only when no indexed path names any responsibility at
all. A bucket whose own **declaration** was never given, and whose vocabulary branch matched nothing,
falls through to the second case and prints a bare `0` in a column where every neighbour is a
measurement. `0` is arithmetically correct and reads as *"this repo vendors nothing"*.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why this exists | "`Vendored dependencies`: 0" beside 47 `Zend/` pages | An unasked question formatted as an answer | re-measured: 0, and 15 `Zend/` + 11 MPDF + 5 adodb files in the post-204 tour | | | ⬜ |
| G2 | Why this exists | "Every other bucket prints a `by signal:` breakdown. Vendor prints none" | The absence of a breakdown is the only hint, and it is silent | `reachability.py:456` (`if any(tally.values())`) | | | ⬜ |
| G3 | Why this exists | "the single-answer classifier can only say the latter" (R1.9) | Named as the reason the vocabulary branch cannot fire; explicitly not fixed here | `reachability.py:248`; ticket *not in scope* | | | ⬜ |
| G4 | Why this exists | "The caveat covers a **stale** declaration. It does not cover an **absent** one" | 119's caveat is the near-miss this completes | `reachability.py:41-45` | | | ⬜ |
| R1 | Scope 1 | "Distinguish 'measured zero' from 'no signal available' for every bucket in `BUCKET_SPECS`" | The field is per-bucket and derived from the table, not special-cased for vendor | | | | ⬜ |
| R2 | Scope 2 | "Render the distinction… in `overview.md`, in the dataset, and in the viewer" | Three renderers, one wording | | | | ⬜ |
| R3 | Scope 3 | "Point at the remedy… names the setting that would populate it" | `stub_roots` / `entry_points`, per H4 | | | | ⬜ |
| R4 | Scope 4 | "Re-measure the anchor with `stub_roots` declared and record what the bucket then reports" | Done, and it is a finding — see AC6 below | | | | ⬜ |
| R5 | Not in scope | "A better vendor detector… no `vendor/`-in-the-core heuristic (R2.2)" | No vocabulary is added; the wording names a setting, never a path shape | | | | ⬜ |
| R6 | Not in scope | "Changing what `stub_roots` means or enabling it on the anchor repo" | The measurement passes `stub_roots` at build time only; the anchor's `.code-atlas.toml` is untouched | | | | ⬜ |
| R7 | Not in scope | "The layer classifier's single-answer shape" (R1.9) | Not touched | | | | ⬜ |
| R8 | Not in scope | "The other artifact honesty gaps" (205, 207) | 205 is already merged and is this branch's base | | | | ⬜ |
| C1 | Constraints | "**R1.8** — one implementation of 'was this bucket's signal available?'" | One function, three readers | | | | ⬜ |
| C2 | Constraints | "**R3.5** — bump `DATASET_VERSION` and move the viewer with it" | 10 → 11, pin moved | | | | ⬜ |
| C3 | Constraints | "**R4.2** — deterministic; depends only on the resolved config and the index" | No wall-clock, no ordering leak | | | | ⬜ |
| C4 | Constraints | "**R6.5 / R6.9** — observed failing first… asserts on the **emitted `overview.md`**" | Red run recorded; the guard reads the file on disk | | | | ⬜ |
| C5 | Constraints | "**R5.4** — the count stays a number, and the availability is a sibling field" | Per H3 | | | | ⬜ |
| AC1 | Acceptance criteria | "distinguishable, in the dataset, from a bucket that was measured and found zero" | `unmeasured` non-empty ⇔ declaration absent ∧ count 0 | | | | ⬜ |
| AC2 | Acceptance criteria | "`overview.md` renders that distinction in words, and names the setting" | The reason is printed where the count is | | | | ⬜ |
| AC3 | Acceptance criteria | "The viewer and the dataset carry the same distinction — no renderer re-words it" | Both read the same string | | | | ⬜ |
| AC4 | Acceptance criteria | "A fixture repo with an undeclared bucket fails the pre-change guard and passes the post-change one" | A recorded red run on the emitted `overview.md` | | | | ⬜ |
| AC5 | Acceptance criteria | "A repo where every bucket has a signal produces output byte-identical to today's" | Declarations given ⇒ `unmeasured` empty ⇒ no extra bytes | | | | ⬜ |
| AC6 | Acceptance criteria | "Scope 4's re-measurement is recorded… and 206 is updated if it changes that ticket's assumptions" | Recorded below | | | | ⬜ |

### AC validation — every value re-derived

| AC | Ticket's value | Re-derived | Falsifiable? |
|----|----------------|-----------|--------------|
| AC1 | — | The predicate is the AC's own; `declaration` is `""` for the three buckets that have no declaration-shaped signal, so they can never report an unasked question | Yes — a dataset field, asserted directly |
| AC2 | — | The reason names `stub_roots` (H4), not `CA_STUB_ROOTS` | Yes — a string in the emitted `overview.md` |
| AC3 | — | One constant, three readers; the guard greps the emitted HTML for the same sentence | Yes — the emitted `index.html` |
| AC4 | — | Red run on the pre-change tree, recorded | Yes — a recorded failure |
| AC5 | "byte-identical to today's" | Confirmed satisfiable: with both declarations given, `unmeasured` is `""` everywhere and no renderer emits a byte. Proven by comparing the emitted `overview.md` pre/post on such a fixture | Yes — a byte comparison |
| AC6 | — | **The re-measurement contradicts the remedy the ticket assumes.** See below | Yes — the numbers are recorded |

### AC6 — Scope 4's re-measurement, and what it found

Post-204 anchor index (24,535 modules, 12,712 zero-inbound), built by this session; the anchor's own
`.code-atlas.toml` was **not** touched — `stub_roots` was passed at build time only (ticket *not in
scope*, R6).

```
Ran at 6ad664d, against a post-204 scratch index of the anchor monorepo
--- as configured (stub_roots UNSET) ---            --- stub_roots = ["vendor", "lib/saml/vendor"] ---
  Web entry points          306  declared=95, vocabulary=211      306  declared=95, vocabulary=211
  Vendored dependencies       0  by signal: none                    0  by signal: none
  Tests and fixtures       1106  vocabulary=1106                 1106  vocabulary=1106
  Not statically reachable 6052  structure=6052                  6052  structure=6052
  No edge either way       5248  structure=5248                  5248  structure=5248
  pattern stub_roots:'vendor'           matches 0 files, claims 0
  pattern stub_roots:'lib/saml/vendor'  matches 0 files, claims 0
tour files containing 'Zend/': 15 · 'MPDF': 11 · 'adodb': 5 · under either stub root: 0
```

**Declaring `stub_roots` changes nothing at all** — not the bucket, not one other count, not the
tour. And the reason is sharper than *"the tour does not move"*: **the two roots the anchor's own
config file proposes match 0 of its 24,535 indexed files.** The anchor's third-party code lives in
`Zend/`, `legacy/alpha/web/include/pdf/` and `.../adodb/` — not under a `vendor/` directory. So:

1. **The remedy pointer must promise that the question gets ASKED, never that the count moves.** A
   declaration can be given and still match nothing, and 119's `PatternClaim` already prints exactly
   that (`matches 0 files, claims 0`) — the two mechanisms compose, and the wording is written not to
   contradict them.
2. **206's assumption is unaffected, and this is the answer it needed.** The ticket's own conditional
   — *"if declaring it moves the tour off mPDF and adodb, that is a finding 206 needs; if it does
   not, 206's scoping is the only lever and this ticket should say so"* — resolves to the second
   branch. `tour_subgraph` never receives `stub_roots` (`store.py:1003`), and no tour file lies under
   either root, so **scoping is 206's only lever.** Recorded in `BACKLOG.md`'s follow-ups rather than
   edited into 206's text.

### Clarifications, all three self-resolved

1. *Does 113's AC4 "honest zero" contradict 208's AC1?* No — H7: 113 asserted the row is rendered
   rather than omitted, which still holds; 208 adds what the 0 measured. The test is amended, and the
   amendment is named.
2. *Which name does the artifact print?* H4 — the project-file key, because no onboarding module may
   import `code_atlas.config`.
3. *Do the ticket's own quoted figures still hold?* Partly: the `0` and the vendored-code-in-the-tour
   evidence held; the two degree-derived claims (`qunit`, `tinymce`) did not survive 204, exactly as
   the ticket's provenance note predicted. Recorded, non-blocking.

### Universal inventory — N = 9 sites, derived from the field, not hand-listed

`grep -rn "reachability\|BUCKET_SPECS\|ReachabilityBucket\|as_dict" --include=*.py code_atlas/`,
then every consumer of the rendered figure (196-C2: grep the rendered name, not the source field).
Review must confirm **every** row.

| # | Site | What must happen |
|---|---|---|
| 1 | `reachability.py` `BUCKET_SPECS` | gains the declaration key per bucket (5-tuple) |
| 2 | `reachability.py` `undeclared_reason()` | the one wording site (R1.8) |
| 3 | `reachability.py` `ReachabilityBucket` + `as_dict` | `declaration` and `unmeasured` siblings; count stays `int` |
| 4 | `reachability.py` `classify_reachability` | derives `unmeasured` from the declaration and the count |
| 5 | `reachability.py` `__all__` | exports the new function |
| 6 | `artifact.py` `_reachability_lines` | renders the reason where the count is (AC2) |
| 7 | `viewer.py` reachability cards | renders the same string, re-worded nowhere (AC3) |
| 8 | `dataset.py` `DATASET_VERSION` | 10 → 11 (R3.5) |
| 9 | `tests/test_reachability_split.py:222` | the `BUCKET_SPECS` shape pin follows the tuple |
| + | `tests/test_onboarding_dataset.py:330` | the version double-pin follows the bump |

### Blast radius

- **Entry point:** `classify_reachability`, called from `dataset.py:528` and `artifact.py`'s
  `build_artifact` summary.
- **Consumers of the shape:** `overview.md`, the dataset (`manifest.json`, `artifact.json`), the
  viewer's `index.html`, and `architecture_overview`'s `summary.reachability` payload.
  `diff_architecture` strips no reachability key and compares the dataset, so a new per-bucket key
  becomes visible there as a change — checked in Phase 2.
- **Repos touched:** `app`. No adapter, no schema, no contract version.

## Phase 2 — design

`HANDLES: 5 recalled | 4 traced (command + result) | 1 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Approach

**Name the field `caveat`, and the existing 127 machinery does AC3's work.** Two sibling fields on
`ReachabilityBucket`:

- `declaration: str` — the project-file setting that populates this bucket by declaration, taken
  from `BUCKET_SPECS` (`"entry_points"`, `"stub_roots"`, or `""` for the three buckets that have
  none by design). One table, so no renderer maps bucket → setting itself.
- `caveat: str` — non-empty exactly when `declaration` is set, that declaration was **not** given,
  and the count is 0. Its words come from **one** function, `undeclared_reason(setting)`, and no
  renderer adds a word of its own.

Naming it `caveat` is the load-bearing choice, and it is not cosmetic. `derive_caveats`
(`dataset.py:283`) already collects *every* `caveat` key at any depth, including inside a list of
mappings — *"a section owns a caveat by owning a non-empty `caveat` key"*. So:

- `tests/test_caveats_reach_the_artifact.py::test_every_dataset_caveat_is_rendered_in_the_map`
  **automatically becomes AC3's guard**: it derives the caveat set from the dataset and asserts each
  string is rendered in the viewer. A caveat the viewer drops fails a guard that already exists.
- `architecture_diff`'s `caveats_before_only` / `caveats_after_only` see a bucket **flip** from
  measured-zero to unasked-zero, which its `reachability_deltas` (`0 → 0`) cannot. That closes the
  exposure-checker's UNEXPOSED-5 for free rather than with a new mechanism.

### Rejected alternatives

1. **A field named `unmeasured`** (my own first design, and what the t0 contract asserted). Rejected
   once the exposure-checker pointed at the fourth and fifth consumers: a bespoke key needs a bespoke
   renderer change in each, plus a new guard for each, and `architecture_diff` stays blind. `caveat`
   costs one word and inherits three mechanisms.
2. **`unmeasured` on the split rather than the bucket.** Rejected: the question is per bucket, and a
   split-level field would force every renderer to re-derive which bucket it referred to — the
   re-derivation R1.8 exists to prevent.
3. **Firing on `count > 0` as well** (an undeclared bucket the vocabulary partly filled is a floor,
   not a total). Rejected as out of scope by AC1's own predicate and R7.1 — and independently raised
   by the exposure-checker, which is why it is a **named follow-up** rather than a silent omission.
4. **Importing `config.env_name` to print `CA_STUB_ROOTS`.** Rejected: no module under
   `code_atlas/onboarding/` imports `code_atlas.config` (zero hits), and hard-coding the `CA_` prefix
   would be a second definition site for a shape `config.py` owns (R6.7).

### Assumptions

| # | Assumption | Tag | How it is resolved |
|---|---|---|---|
| 1 | `derive_caveats` finds a `caveat` key inside `buckets[]` | **verified** | `dataset.py:294-301` recurses into every list-of-mapping; `test_the_caveat_set_is_derived_not_listed` plants one in `rows[0]` and asserts it is found |
| 2 | The 127 guard renders the **viewer**, so it enforces AC3 | **verified** | `test_caveats_reach_the_artifact.py:70-84` renders `render_viewer(...)` through the headless reporter and asserts every derived caveat text appears |
| 3 | `test_artifact_contract.py` pins every bucket key, so `ARTIFACT_VERSION` must move too | **verified** | `test_artifact_contract.py:105-115` lists `summary.reachability.buckets[].*` field by field; `:223` asserts equality with `KEY_PATHS_BY_VERSION[ARTIFACT_VERSION]` |
| 4 | The `test` bucket can never report an unasked question | **verified by construction** | its `declaration` is `""`, so the predicate short-circuits — the exposure-checker's UNEXPOSED-1/2, answered by the predicate rather than by a wording rule |
| 5 | A caveat appearing in more fixtures does not break the 127 guard's floor (`len(caveats) >= 3`) | **novel-untested** | resolved by running that guard, not by argument — it is in the sweep below |

### Smallest change-list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `BUCKET_SPECS` gains the declaration key (4-tuple → 5-tuple) | `reachability.py:58` | its two unpack sites: `:318` and `tests/test_reachability_split.py:222` (a shape pin — the point) | R1 C1 | 2/2 |
| 2 | `undeclared_reason(setting)` — the one wording site | `reachability.py` | none; nothing else may spell the sentence | R2 R3 C1 AC2 | 1/1 |
| 3 | `ReachabilityBucket` gains `declaration` + `caveat`, both in `as_dict` | `reachability.py:143-168` | every consumer of the dict shape: `overview.md`, the dataset, the viewer, `architecture_overview`, `derive_caveats`, both version pins | R1 AC1 C5 | 6/6 |
| 4 | `classify_reachability` derives the caveat from the existing `declared` map | `reachability.py:311-330` | gates on *was a declaration given* (196-C1), never on a key's presence | R1 AC1 | 1/1 |
| 5 | `_reachability_lines` prints the caveat where the count is | `artifact.py:439` | `overview.md` bytes — AC5's comparison | R2 AC2 | 1/1 |
| 6 | the viewer's reachability card + note read `b.caveat` | `viewer.py:717-738` | the emitted `index.html`; the 127 guard | R2 AC3 | 2/2 |
| 7 | `headlines.py::_reachability` appends the chosen bucket's caveat | `headlines.py:132` | the dataset's headline prose; `is_filler` | R2 AC3 | 1/1 |
| 8 | `DATASET_VERSION` 10 → 11 | `dataset.py:53` | the double-pin at `test_onboarding_dataset.py:330` | C2 | 2/2 |
| 9 | `ARTIFACT_VERSION` 2 → 3 + `V3_KEY_PATHS` derived from V2 | `artifact.py:69`, `tests/test_artifact_contract.py` | `artifact.json` consumers | C2 | 2/2 |
| 10 | **Proof collateral** — the `BUCKET_SPECS` shape pin, 113's AC4 test (H7), the version pins | `tests/test_reachability_split.py`, `tests/test_onboarding_dataset.py`, `tests/test_artifact_contract.py` | none | AC1 AC5 | 3/3 |
| 11 | **New guards** — the emitted `overview.md` carries the sentence · a declared bucket at zero does **not** · the three declaration-less buckets never do · the emitted `index.html` carries it | `tests/test_generate_onboarding.py`, `tests/test_reachability_split.py` | none | AC1–AC5 | 4/4 |
| 12 | `docs/TOOLS.md` — `architecture_overview`'s reachability bullet says what an undeclared bucket now reports | `docs/TOOLS.md` | none | AC2 | 1/1 |
| 13 | Working doc, `TOKEN_LEDGER.md` row, `BACKLOG.md` status + follow-ups | `docs/` | R7.2 | — | 3/3 |

### Recalled type-2 handles — every one answered

| Handle | Answer |
|---|---|
| `gate-on-the-invariant-not-on-presence` (196-C1) | **traced.** `rtk proxy grep -n "declared = {" code_atlas/onboarding/reachability.py` → `:315 declared = {WEB_ENTRY: bool(entry_rules), VENDOR: bool(stub_rules), TEST: False}`. Folded: the new predicate reads **that map** — *was a declaration given* — never `"stub_roots" in config` or the presence of a key. The invariant already exists; this adds a second reader of it |
| `grep-the-derived-name-not-the-source-name` (196-C2) | **traced.** `rtk proxy grep -rn "reachability" --include=*.py code_atlas/ tests/ scripts/` → 60+ hits across 9 production modules. Folded: it found the **fourth** renderer (`headlines.py:132`) and the **fifth** consumer (`architecture_diff.py:336`) that Scope 2's "three renderers" undercounts — change-list rows 6, 7 and the `caveat` naming that reaches the fifth |
| `a-capped-search-is-not-a-search` (205-C2) | **traced, and it fired.** `grep -n "handle: \`source-the-caveat…\`" docs/LESSONS.md` returned *"3 matches in 3 files:"* and **no rows** — the compacted output hid every line. Re-run as `rtk proxy grep -n …`, which printed the class index at `LESSONS.md:42-54` and settled three handles' promotion status. Folded: every search in this phase went through `rtk proxy`, and the sighting is recorded (seen: 203, 205, **208**) |
| `grep-the-keyword-argument-too` (205-C1) | **traced.** `rtk proxy grep -rn "ReachabilitySplit(\|classify_reachability(" --include=*.py . ` → `tests/test_onboarding_dataset.py:103` builds `ReachabilitySplit(0, (), ())` **positionally** — the only positional construction in the repo, so a new field must carry a default. 22 call sites of `classify_reachability` / `ReachabilitySplit` in all (5 in production, 16 in tests, 1 in `scripts/`), and `sample_limit=` is passed by keyword at 46 sites. Folded: rows 3 and 10 — the positional constructor is why both new fields carry defaults |
| `strip-list-is-not-an-emit-list` (205-C3) | **does not apply because** this change adds two keys and removes none: no set here filters in either direction, and `architecture_diff._MANIFEST_KEYS` (the strip-list 205 met) does not name `reachability` |

### Rule compliance

- **R1.8** — one wording function; **zero** renderer-side words. The three (four) renderers print
  `bucket['caveat']` verbatim.
- **R1.9** — the single-answer layer classifier is *why* the vocabulary branch cannot fire, and is
  explicitly not touched. The new field describes the consequence rather than fixing the classifier.
- **R2.2** — no library, framework or path-shape vocabulary is added; the sentence names a **setting**.
- **R3.5** — **both** versioned documents move: `DATASET_VERSION` 10 → 11 and `ARTIFACT_VERSION`
  2 → 3, each with its pin.
- **R4.2** — the caveat depends only on the resolved config and the index; no wall-clock, no ordering.
- **R5.4** — `count` stays an `int`; the words live in a sibling.
- **R5.5 / R5.6** — the caveat rides *with* the count, and the payload no longer attests past what it
  can distinguish. These are the two rules the ticket cites, and the two recalled handles behind them.
- **R6.5 / R6.9** — every guard reads the **emitted** `overview.md` / `index.html`, and each is
  recorded red first.
- **R7.1** — two fields and one function; the `count > 0` case is a named follow-up, not a silent gap.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 the dataset distinguishes unasked from measured | logic | unit over `classify_reachability` | n/a | ✅ |
| AC2 `overview.md` says it in words and names the setting | integration | integration over the **emitted** `overview.md` | n/a | ✅ |
| AC3 the viewer and dataset carry the same string | integration | the existing 127 guard (derives the caveat set, renders the viewer headlessly) | n/a | ✅ |
| AC4 a fixture with an undeclared bucket fails pre-change | integration | integration + **recorded red run** | n/a | ✅ |
| AC5 a repo where every bucket has a signal is byte-identical | integration | integration, plus a pre/post byte comparison on such a fixture | n/a | ✅ |
| AC6 Scope 4's re-measurement recorded | runtime/3p (a real index) | **real-corpus run, recorded in Phase 1** with the command and its output | real-corpus (the anchor at `/home/you/WORKSPACE/work/anchor-repo`, post-204 scratch index) | ✅ |
| Assumption 5 — the 127 guard survives a bigger caveat set | integration | run it | n/a | ✅ |

No `❌`, so no coverage-gap exclusion. `config.real_corpus_path` is `null`, so AC6's row names the
corpus it actually used and the command that produced its numbers rather than claiming a configured
one — the figures are in Phase 1 and are reproducible from that command.

### Proving test

```
.venv/bin/python -m pytest tests/test_generate_onboarding.py::test_an_undeclared_bucket_says_its_zero_is_not_a_measurement -q
```

Fails pre-change (the emitted `overview.md` prints a bare `0`), passes post-change.

### Rollback + porting

- **Rollback:** `git revert` the commits on the branch, or close the PR unmerged. Both version stamps
  return with it; a repo that regenerated in between gets the old wording on its next write.
- **Porting:** one repo (`app`). No adapter, no schema, no contract version.

### SCOPE

`SCOPE: M` — re-affirmed, and it grew inside M rather than crossing to L: the exposure-checker added
two consumers (`headlines.py`, `ARTIFACT_VERSION` + its pin) to a change list that was already
touching three renderers and one version stamp. 13 rows over 4 source files, 5 test files and 1 doc.

## Phase 3 — execute

Complete on disk. Branch `fix/208-…`, based on `main` at `6ad664d`.

### What landed

`ReachabilityBucket` gains two siblings — `declaration` (the setting that populates it, from
`BUCKET_SPECS`) and `caveat` (non-empty exactly when that declaration was never given and the count
is 0). The words come from `undeclared_reason()`, and **`grep -rl "not a measurement"` over
`code_atlas/` returns exactly one file**, which is the R1.8 invariant the contract checks.

**Naming the field `caveat` bought three mechanisms rather than building them:**

| Mechanism that already existed | What it now does for free |
|---|---|
| `dataset.derive_caveats` (127) collects every non-empty `caveat` key at any depth | the new caveat is derived without an edit: `derive_caveats` on the 127 fixture returns **4** rows, one of them `reachability.buckets[1] -> not a measurement: no stub_roots …` |
| `test_every_dataset_caveat_is_rendered_in_the_map` renders the viewer headlessly and asserts every derived caveat appears | **AC3's guard, unwritten by me.** It runs (not skips — `PASSED`, node present) and would go red if the viewer dropped the sentence |
| `architecture_diff`'s `caveats_before_only` / `caveats_after_only` | sees a bucket **flip** from measured-zero to unasked-zero, which its `reachability_deltas` (`0 → 0`) cannot |

### Verification sweep — Axis 1, the file set

`git diff --stat main -- code_atlas/ tests/ docs/TOOLS.md` — 12 files, every one inside the Gate-2
change list except the two recorded as **D1** and **D2** below:

```
Ran at c065232 (the commit under review)
 code_atlas/onboarding/artifact.py     | 12 ++++--
 code_atlas/onboarding/dataset.py      |  7 ++--
 code_atlas/onboarding/headlines.py    |  4 +++
 code_atlas/onboarding/reachability.py | 51 +++++++++++++++++++++++++--
 code_atlas/onboarding/viewer.py       |  5 ++-
 docs/TOOLS.md                         |  5 +++
 tests/test_artifact_contract.py       | 16 +++++++-
 tests/test_generate_onboarding.py     | 30 ++++++++++++++++
 tests/test_map_confidence_attribution.py |  9 ++++-
 tests/test_onboarding_dataset.py      |  2 +-
 tests/test_reachability_split.py      | 64 ++++++++++++++++++++++++++---
```

**D1 — a THIRD version pin, found by the suite and not by the design's trace.**
`tests/test_map_confidence_attribution.py:167` asserted `DATASET_VERSION == 10` as a **bare
number** — task 196's own AC3 pin — so it broke on this bump without 196's claim being wrong. The
design's inventory named two pins (`test_onboarding_dataset.py:330` and the artifact-contract set)
and missed this one because it greps as a *comparison against the constant* in every other file:

```
Ran at c065232
$ rtk proxy grep -rn "DATASET_VERSION ==\|ARTIFACT_VERSION ==\|== DATASET_VERSION\|== ARTIFACT_VERSION" --include=*.py tests/
tests/test_onboarding_dataset.py:320:    assert payload["version"] == DATASET_VERSION
tests/test_onboarding_dataset.py:330:    assert payload["version"] == DATASET_VERSION == 11
tests/test_artifact_contract.py:235:    assert real["version"] == ARTIFACT_VERSION
tests/test_artifact_contract.py:244:    assert payload["version"] == ARTIFACT_VERSION
tests/test_artifact_contract.py:261:    assert max(KEY_PATHS_BY_VERSION) == ARTIFACT_VERSION
tests/test_generate_onboarding.py:122:    assert dumped["version"] == ARTIFACT_VERSION
tests/test_onboarding_viewer.py:165:    assert payload["version"] == DATASET_VERSION
tests/test_onboarding_viewer.py:259:    assert _payload(html)["version"] == DATASET_VERSION
```

Eight assertions, and only the two **deliberate double-pins** need editing on a bump; the bare
`== 10` was the odd one out. Repaired to `>= 10` with the reason in its docstring, and the sweep
above is the evidence there is no fourth.

### Verification sweep — Axis 2, design conformance

| Gate-2 Approach bullet | Verdict |
|---|---|
| Two siblings, `declaration` from `BUCKET_SPECS` and `caveat` from one function | implemented-as-approved |
| The predicate is AC1's: declaration set, not given, count 0 | implemented-as-approved |
| Naming it `caveat` inherits `derive_caveats`, the 127 guard and the snapshot diff | implemented-as-approved — all three verified above |
| Zero renderer-side wording | implemented-as-approved — one file holds the sentence |
| `headlines.py` (the fourth renderer) carries the caveat | implemented-as-approved |
| Both version stamps move, `V3_KEY_PATHS` derived from V2 | implemented-as-approved — and a **third** pin turned up (D1) |
| `count` stays an `int` | implemented-as-approved |

### R6.5 — the guards, observed failing

```
Ran at 6ad664d (a throwaway worktree at main, branch test files copied in)
$ pytest tests/test_generate_onboarding.py::test_an_undeclared_bucket_says_its_zero_is_not_a_measurement
>       assert "not a measurement" in overview
E       assert 'not a measurement' in '# Architecture overview\n\n## Summary\n…'
1 failed, 1 passed
$ pytest tests/test_reachability_split.py::test_208_a_declared_bucket_at_zero_is_a_measured_zero  (+2 more)
E   ImportError: cannot import name 'undeclared_reason' from 'code_atlas.onboarding.reachability'
```

The proving test fails **at its assertion** on the pre-change tree — the row prints `0` and says
nothing — and the three unit guards cannot even import the symbol they assert on. The AC5 guard
(`test_a_repo_whose_buckets_all_have_a_signal_says_nothing_extra`) **passes on both trees**, which is
correct and is stated rather than dressed up: it asserts an *absence*, so it is a byte-identity
guard, not a new-behaviour one.

### AC5 — the byte comparison, with every bucket's signal given

```
Ran at 6ad664d (pre) / c065232 (post), one fixture index, entry_points and stub_roots both declared
overview.md  byte-identical
tour.md      byte-identical
flows.md     byte-identical
index.html   DIFFERS
```

`index.html` differs in exactly two places, and both are the schema move R3.5 demands:

1. its embedded dataset gains `"caveat": ""` and `"declaration": …` on each bucket and moves
   `"version": 10` → `11`;
2. one added JS comment line.

**No rendered figure or word changes** — the three Markdown files are byte-identical, and the HTML's
rendered sections come from the same data. AC5's literal wording ("output byte-identical") and R3.5
("a dataset field is a schema move: bump `DATASET_VERSION`") cannot both hold for the embedded
dataset: adding the field changes those bytes by construction. Recorded as a **clarification, not a
pass** — the honest claim is *rendered output byte-identical, embedded schema bumped as required*.

**D2 — the fourth renderer shipped with no assertion on it, and the challenger is what found that.**
`headlines.py`'s caveat append was in the change list (row 7) and implemented, but **untested**: the
ticket-blind challenger mutated it to `if False and largest.caveat:` and watched **72** related
tests stay green. Green-by-construction, in the one renderer the ticket did not name. Closed by
`tests/test_onboarding_headlines.py::test_the_reachability_headline_carries_the_caveat_of_the_population_it_names`,
written from that exact mutation and observed red against it:

```
Ran at c065232, with `if False and largest.caveat:` in the working tree, then restored
FAILED tests/test_onboarding_headlines.py::test_the_reachability_headline_carries_the_caveat_of_the_population_it_names
1 failed, 7 passed in 0.04s
```

The fixture took two attempts, and the first one is worth recording: closing a cycle over two
`app/A.aa`-style paths made every module inbound-reachable, but those paths name no responsibility,
so `vocabulary` was `False` and the three vocabulary buckets were **dropped** — the pre-existing AC5
path — leaving only structural buckets, which can never carry a caveat. The guard was passing
through a case it did not reach. It now closes the cycle over the fixture's own
`app/controller`/`app/service` paths, so the vocabulary signal stays available, no bucket is
dropped, and the winning bucket really is an unasked question.

**A process cost worth recording, because I paid it twice in one ticket.** I launched the full suite
while the mutating reviewer was live, both times. The first run came back `4 failed, 2775 passed`
with failures in `test_answer_pagination`, `test_index_root`, `test_payload_weight` and
`test_server_build_on_payloads` — none of which touch reachability, and all consistent with a
renderer being mutated underneath them. The second time I killed the run rather than read it. The
challenger's restores were exact both times (`git diff HEAD -- code_atlas/ tests/` empty), so nothing
was corrupted — but a suite result taken while another process is mutating the tree is not evidence,
and the only honest use of the first one was to discard it.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` — the rule-book-grounded seat was waived by the run argument, so
**no rule-book-grounded review of this diff exists**. `CHALLENGER: ON`.

Verdict: **clean (challenger only — REVIEWER: OFF)**, after one full round and one verify-only round.

### Round 1 — the ticket-blind challenger

`CHALLENGER: 15 requirements | 12 met | 1 not met | 2 can't tell` (111,014 tokens / 52 tool-uses).
Path-restricted throughout; it reported its own independence check. It ran **three** restore-verified
mutations of production code to test whether the guards bite, and diffed each restore against
`git show HEAD:<path>`.

Its two `CAN'T TELL`s are structural, not gaps: Scope 4/AC6's anchor re-measurement lives in this
working doc, which a ticket-blind reviewer is contractually unable to read.

| # | Finding | Disposition |
|---|---|---|
| F1 | **The fourth renderer had no test.** It mutated `headlines.py`'s caveat append to `if False and largest.caveat:` and **72** related tests stayed green | **Fixed** — D2 in Phase 3, guard written from that mutation and observed red against it |
| F2 | **AC5's literal wording oversells the diff**: `overview.md` is unaffected when every bucket has a signal, but `artifact.json` / `manifest.json` / the embedded dataset change unconditionally, and nowhere in the diff is the AC5-vs-R3.5 tension disclosed to a reviewer | **Recorded as NOT MET as literally worded**, with the honest claim stated in the **PR body** (where a reviewer sees it) and here: *rendered output byte-identical; embedded dataset carries the two new empty keys and the version bump R3.5 requires* |
| F3 | informational: the working doc shows as locally modified (expected under `work_doc_mode: embed`); it did not reach its input | no action |

### Round 2 — verify-only, no re-dispatch

The re-review was a **verify-only pass on the same seat** (`SendMessage` to the live agent, context
intact), because the delta stayed inside the named findings plus a suite-found pin. It re-ran its own
mutation against the new guard, re-grepped for a fourth version pin, and judged the AC5 disclosure.

| Item | Verdict |
|---|---|
| `DELTA-1` the `>= 10` repair of 196's pin | **MET** — *"honest, not a weakening"*: 196's claim was that its key arrived **at** 10, and a bare `== 10` also asserted *"the current version is 10"*, which 196 never intended to own. It independently confirmed `test_onboarding_dataset.py:330` is the only other hard-coded numeric pin, and that `confidence_by_language`'s behaviour is checked unconditionally elsewhere in the same file, so relaxing the version assertion opens no coverage gap |
| `DELTA-2` the headline guard | **MET.** Red under its mutation, green restored, tree byte-identical. **Plus a scoping insight worth more than the fix:** because `max(..., key=(count, bucket))` compares the count first, a caveated **zero** bucket can only ever be "largest" when **every** bucket is zero — so this defence fires **only** on a degenerate repo with no zero-inbound module at all, and is a **no-op on the anchor's own shape** (a populous isolated bucket beside a starved vendor one). The fixture is therefore not a weaker stand-in — it is the only reachable precondition — and the fix is smaller in value than change-list row 7 implied. Recorded rather than left flattering |
| `AC5-DISCLOSURE` | **MET** — and its reasoning is stronger than mine: AC5's literal wording and R3.5 are **mutually exclusive** whenever a field is genuinely added, so *"no implementation could have satisfied AC5 literally without violating R3.5"*, and failing the ticket on it would penalise compliance with the higher-order constraint the same ticket wrote |

### Scope reconciliation

- **File axis:** 12 files. Two are beyond the Gate-2 change list —
  `tests/test_map_confidence_attribution.py` (D1, a third version pin the suite found) and
  `tests/test_onboarding_headlines.py` (D2, the guard F1 earned). Both are proof collateral for rows
  the list already carried, and both are adjudicated here rather than absorbed. No untouched line was
  reformatted; `ruff --fix` was scoped to the one test file this change authored.
- **Behaviour axis:** every Gate-2 Approach bullet is `implemented-as-approved` (Phase 3's table).
  No bullet diverged.

### Regression check

The Phase-1 blast radius re-checked at the reviewed SHA: `architecture_overview` (passes the new
keys through unchanged), `diff_architecture` (now *gains* the flip through `derive_caveats`),
`find_orphans` (reads `reach_shared`, not the split), the two version pins plus the third the suite
found, `scripts/reachability_report.py` (unpacks nothing from `BUCKET_SPECS`), and `headlines.py`.
mypy clean over `code_atlas` + `onboarding_llm` (85 files); ruff clean.

### Delta-green, and the run that could be trusted

```
Ran at c065232, with nothing else touching the tree
$ .venv/bin/python -m pytest -q
2780 passed in 269.80s (0:04:29)
```

Baseline **2775** at `6ad664d` → **2780**: exactly the five new guards (two on the split, two on the
emitted `overview.md`, one on the headline). Nothing was removed and nothing skipped.
`ruff check .` clean; `mypy code_atlas onboarding_llm` clean (85 files).

### `Reviewed at`

`Reviewed at c065232` — the tree the challenger reviewed (`a3ed863`), plus the two commits its
findings and the suite caused, both judged in its verify-only round.

**Reviewed files (12):** `code_atlas/onboarding/reachability.py` · `code_atlas/onboarding/artifact.py`
· `code_atlas/onboarding/dataset.py` · `code_atlas/onboarding/viewer.py` ·
`code_atlas/onboarding/headlines.py` · `docs/TOOLS.md` · `tests/test_reachability_split.py` ·
`tests/test_generate_onboarding.py` · `tests/test_artifact_contract.py` ·
`tests/test_onboarding_dataset.py` · `tests/test_map_confidence_attribution.py` ·
`tests/test_onboarding_headlines.py`.

**Working doc:** `docs/tasks/208_an-undeclared-reachability-bucket-reports-zero-as-a-measurement.md`
(embedded; exempt from the staleness comparison, with `.mango/`).

## Phase 5 — finalise

**Stale-review guard: not stale.** `git diff --name-only c065232..HEAD` returns only this working
doc plus `docs/LESSONS.md` and `docs/SKILL_GAP_CANDIDATES.md` — the marker-bearing doc and two
bookkeeping paths the guard exempts by construction. No non-exempt file changed beyond the reviewed
set.

`config.pr_checklist_path` is unset; the PR template's own self-check is filled in the PR body.

### The learning loop

`CLAIMS: 6 claim(s) from 1 lesson entr(ies) | T1=0 T2=4 T3=1 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 2 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 2 proposed | 0 human-ratified | destinations: docs/AGENT_BRIEF.md | mango files written: 0`

| Claim | Type | Handle | Recurrence | Proposed destination |
|---|---|---|---|---|
| `208-C1` pin the version a key arrived at, not the current number | 2 (code) | `pin-the-arrival-not-the-current-number` | 1 | stays in `lessons_path` |
| `208-C2` name a field into a contract the project already derives over | 2 (code) | `name-into-the-existing-contract` | 1 | stays in `lessons_path` |
| `208-C3` a suite run under a mutating reviewer is not evidence | 2 (process) | `no-suite-while-a-mutating-reviewer-is-live` | 1 | stays in `lessons_path`, and a type-3 signal beside it |
| `208-C4` a red guard proves nothing unless it is red for the right reason | 2 (code) | `red-for-the-right-reason` | 1 | stays in `lessons_path`; sharpens R6.5 |
| `208-C5` the anchor's vendored code is not under `vendor/` | 5 (descriptive) | area: onboarding / reachability, `verified-at: 2026-09-02` | 1 | stays in `lessons_path` |
| `196-C2` grep the derived name, not the source name | 2 (process) | `grep-the-derived-name-not-the-source-name` | **2** (196, 208) | **`agent_brief_path`** — awaiting ratify |
| `205-C2` a capped search is not a search | 2 (process) | `a-capped-search-is-not-a-search` | **3** (203, 205, 208) | **`agent_brief_path`** — awaiting the ratify open since 205 |
| — signal: nothing sequences the mutating reviewer against the suite run | 3 | — | 1 | `skill_gap_path` — **written, signal only** |

**Falsification, before the gate.** `196-C2`: still true — it is what found the fourth and fifth
consumers this ticket had to touch, and the cheap check is the grep itself. `205-C2`: still true —
it fired again in this ticket's own refine phase on `LESSONS.md`'s class index, and the check is
re-running the search uncapped. Neither is blocked.

**Nothing was promoted.** Both proposals need a per-claim human ratify the handover authorisation
does not cover, so `docs/AGENT_BRIEF.md` and the rule book are **untouched**. `a-capped-search-is-not-a-search`
is now at **three** sightings across 203, 205 and 208, which is the recurrence threshold the loop
treats as *"writing it down was already the treatment"* — `/mango:promote` is the cross-ticket pass
for it, and naming it here is not running it. `mango files written: 0`.

### Cost ledger

| Dispatch | Phase | Tokens | Tool-uses |
|---|---|---|---|
| `challenger` as refine's exposure-checker | 0 refine | 96,366 | 38 |
| `challenger`, ticket-blind, round 1 | 4 review | 111,014 | 52 |
| `challenger`, same seat, verify-only round 2 | 4 review | **130,459 reported** — the seat resumed with its context, so the figure reads cumulative rather than incremental; the round's own delta is ~19,445 | 10 |
| `reviewer` | — | **not spent** — waived by `--no-reviewer` | — |

`LEDGER TOTAL: 226,825 tokens · top cost driver: the ticket-blind challenger's review seat (130,459 across two rounds)`

The verify-only round cost about **19k** against a fresh dispatch's ~111k, which is the point of
doing it on the live seat rather than re-dispatching. Scope of the number, stated honestly: it
measures **subagent dispatch only**. The main loop — this ticket's greps, five suite runs (two of
them discarded), the anchor measurement — is **unmeasured (host surfaces no usage block)** and is
the larger term; `rtk gain` is the instrument for that side.
