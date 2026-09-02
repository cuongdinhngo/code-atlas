---
id: 208
slug: an-undeclared-reachability-bucket-reports-zero-as-a-measurement
title: "`Vendored dependencies: 0` on a repo whose tour is half vendored code — a reachability bucket with no declaration and no vocabulary hit prints a bare `0`, which reads as a measured absence rather than an unasked question"
phase: 3
milestone: M11
status: todo
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
