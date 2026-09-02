---
id: 209
slug: a-committed-artifact-cannot-say-which-summarizer-wrote-it
title: "A committed artifact cannot say whether its summaries came from an LLM or from the structural fallback, so `No leading doc comment above the indexed declaration in this file.` reads as a fact about the repo when it is a fact about the run"
phase: 3
milestone: M12
status: todo
depends_on: [085, 090, 117, 118, 205]
---

## Why this exists (measured on the anchor monorepo, 2026-09-02)

`generate_onboarding` takes a `Summarizer` and defaults it to the deterministic one
(`code_atlas/tools/generate_onboarding.py:64`):

```python
seam: Summarizer = StructuralSummarizer() if summarizer is None else summarizer
```

An MCP caller cannot pass one, so every artifact generated through the server is written by
`StructuralSummarizer`. On the anchor that produced **277 of 500** module pages whose Summary line
is:

```
No leading doc comment above the indexed declaration in this file.
```

That sentence is true. It is also, to a reader, indistinguishable from two very different worlds:

1. this repo's code carries no doc comments — a finding about the codebase;
2. the artifact was generated without the LLM seam configured — a finding about the run.

The artifact states neither. A person reading `docs/onboarding/` six months from now, or an agent
grepping it, has no way to tell which they are looking at. This is **R5.6** — never attest past what
the payload can distinguish — in the one artifact whose whole audience is a human.

### The provenance exists, and stops at the tool response

`_payload` at `code_atlas/tools/generate_onboarding.py:291` does carry the fact, at
`detail_level: standard`:

```python
payload["prose_calls"] = prose.calls
payload["prose_declined"] = prose.declined
```

Two problems. It describes the **117 prose seam**, not the **085/090 summarizer** that wrote the 277
lines; and it is in the *MCP response*, which is discarded, rather than in the *committed artifact*,
which is kept. The committed tree is what gets read later, and it is the one without the stamp.

The code even records why: *"Not in the dataset on purpose: a number that moved when the seam turned
on would break AC2."* That reasoning is sound for a **cost count** and is the tension this ticket has
to resolve, not override — see Constraints.

### Why this ranks above building anything new

The repo already owns the whole seam: `Summarizer` Protocol (085), an LLM implementation (090/091),
prose for the map (117), the `llm = ["anthropic>=0.69"]` optional dependency, a separate
`onboarding_llm` package and a `code-atlas-llm` entry point. **Nothing needs to be built to get
better summaries — the seam needs to be reachable, and the artifact needs to say which side of it
produced the text.** An evaluation of the artifact's quality that does not first establish which
summarizer ran is measuring a configuration, and this ticket is what makes that distinction
recordable.

## Scope

1. **Stamp the summarizer and prose implementation into the committed artifact**, by identity — not
   by call count. `overview.md` says which produced its text; the dataset carries the same field so
   the viewer and any agent read one fact (**R1.8**).
2. **Make the fallback sentence name its own cause.** `StructuralSummarizer`'s no-docline text
   distinguishes "this declaration has no doc comment" from "no summarizer beyond the structural one
   ran", because those are different sentences and only one is about the repo.
3. **A documented, reachable path to run with the LLM seam on**, from the CLI and from the MCP
   server, with what it costs. Today `summarizer=` is a Python keyword argument with no route
   through either surface — an implemented seam nobody can switch on.
4. **Measure both artifacts on the anchor and record the delta** — pages changed, summary lines that
   stopped being the fallback sentence, cost. That number is what decides whether the seam is worth
   a consumer's tokens, and no such measurement exists.

### Explicitly not in scope

- **Writing a better summarizer.** 090/091 exist. This ticket makes them reachable and their use
  visible.
- **Turning the seam on by default.** **R4.1** stands: the core stays LLM-free, the seam stays
  opt-in, and CI never needs a key.
- **Page count, page selection, or the orientation section.**
  [205](205_a-module-page-per-node-budget-slot.md), [206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md),
  [207](207_the-artifact-answers-no-question-a-newcomer-asks-first.md).

## Constraints

- **R4.1** — no LLM or network in the core, ever. The stamp is written by the core; the summarizing
  is not.
- **117's AC2** is the live tension: a *count* that moves when the seam turns on would break it. A
  *provenance identity* is a different register (**R5.4** — the field the reader acts on holds one
  register, prose gets a sibling). Resolve it explicitly in the design and say which reading of AC2
  survives; do not quietly widen it.
- **R3.5** — a dataset field is a schema move: bump `DATASET_VERSION`, move the viewer with it.
- **R4.2** — for a fixed summarizer, output stays byte-identical. The stamp is a function of the
  configuration, not of the wall clock.
- **R6.9** — the guard asserts on the emitted `overview.md`, not on a payload dict.

## Acceptance criteria

1. A committed artifact names the summarizer and prose implementation that produced it, in
   `overview.md` and in the dataset.
2. A no-docline summary line distinguishes an absent doc comment from an absent summarizer.
3. The LLM seam is selectable from the CLI and from the MCP server, and the path is documented in
   `TOOLS.md` with its cost.
4. Two artifacts generated on the same index with different summarizers differ in their stamp, and a
   test pins that; two generated with the same summarizer are byte-identical.
5. The anchor delta from Scope 4 is recorded in the ticket close-out with real numbers.
6. CI needs no API key and exercises the deterministic path unchanged.

## References

[085](085_onboarding-summarizer-seam.md) (the seam), [090](090_llm-summarizer-impl.md) and
[091](091_llm-layer-refinement.md) (the implementations nobody can reach),
[117](117_llm-prose-for-map.md) (the prose seam and the AC2 this must reconcile),
[118](118_module-summary-seam-gets-empty-facts.md) (why the fallback sentence is so common),
[205](205_a-module-page-per-node-budget-slot.md) (the 277 pages, counted).
