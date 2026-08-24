---
id: 145
slug: artifact-json-is-a-cache-that-a-second-renderer-turns-into-a-contract
title: '`artifact.json` is a gitignored cache — the moment a second renderer reads it, it is a published contract nobody versioned'
phase: 3
milestone: Presentation
status: done
depends_on: [088, 112, 116, 118]
---

> **Two halves, and only the first is schedulable.** Phase A (the contract) can run now and is worth
> doing alone. Phase B (the web renderer) is **blocked on [118](118_module-summary-seam-gets-empty-facts.md)**
> — see "Why B waits".

## Why this exists

`generate_onboarding` writes two things: the committable artifact under `docs/onboarding/` (markdown,
`manifest.json`, the single-file `index.html`) and a regenerable cache at
`.code-atlas/onboarding/artifact.json`, which is
`json.dumps(artifact.as_dict(), sort_keys=True, ensure_ascii=False, indent=2)` — deterministic, and
described in the source as *"the gitignored regenerable cache"*.

That description is safe **only while the single consumer is in-tree**. `viewer.py` embeds
`dataset.as_dict()` verbatim, so today the shape can move freely and both sides move together. A second
renderer **outside** this repository — a Next/Nuxt app, or anything else — turns that file into a
**published interface**: it gains a consumer that cannot be updated in the same commit. R3 exists for
exactly that situation (contract frozen, versioned, conformance-tested), and nothing in it applies to
`artifact.json` today: no version, no conformance test, and docs that call it a cache.

**Phase A is therefore the real content of this ticket**, and it is worth shipping even if no web app is
ever written.

Provenance: the architecture review of 2026-08-23, in the discussion of moving onboarding onto a JS
stack.

## Scope — Phase A (the contract)

- A version on `artifact.json`, and a conformance test pinning the shape — the same discipline
  `tests/contract/` applies to the adapter seam.
- A made-to-fail guard: changing the shape without bumping the version fails.
- The docs that call it a free-form cache stop calling it that.

## Scope — Phase B (`onboarding_web/`, opt-in, outside the core)

Placement mirrors `onboarding_llm/` — outside `code_atlas/`, off by default — but **the mechanism is
different and the ticket must not blur it**: `onboarding_llm/` is Python injected through Protocol
seams; a JS app cannot be imported by the core at all. It is a downstream consumer, and **the contract
between them is a file on disk, not a Protocol**. That is why Phase A comes first.

Hard boundaries, which are most of the value of writing this down:

- **Never opens `graph.db`, never calls an MCP tool, never runs a second pipeline.** A number the app
  needs and the dataset lacks is added **to the dataset in the core** — not fetched around the side.
- **Node never reaches the core's build path.** `pytest` and `scripts/gate.sh` stay green with no npm
  installed. The repo has no Node today (the only `package.json` belongs to a cross-repo sample).
- **`index.html` stays the default committable artifact.** The app is a second renderer, not a
  replacement.
- **No network at runtime** — the offline property is a product claim (§1), not a viewer detail.

**The R4.2 conflict, stated rather than discovered later:** the single-file viewer is byte-identical
under `R4.2`/116 AC3. A Next/Nuxt static export is **not** reproducible by default (build id, hashed
chunks). This ticket must choose in writing: pin the build, or declare this artifact outside that gate
and say what replaces it.

## Why B waits

118, 130 and 131 have shipped. Phase B still waits on a **stack choice** (Next vs Nuxt), which this
ticket's Out of scope forbids deciding here.

## Acceptance criteria — Phase A

- **AC1** `artifact.json` carries a version; a conformance test pins the shape (R6.5, red first).
- **AC2** A shape change without a version bump fails the suite (made-to-fail, not assumed).
- **AC3** No doc still describes the file as a free-form cache.
- **AC4** Determinism unchanged: identical index → byte-identical file (R4.2).

Phase B's criteria are written when a stack is chosen; drafting them now would read as a commitment
this ticket's Out of scope forbids.

## Out of scope

- **Choosing Next vs Nuxt.** Both static-export; the maintainer picks the one they maintain comfortably.
  A ticket does not get to decide it.
- **Serving the app from a container.** Deployment, and it is separate — the read-only snapshot idea
  belongs with whatever ticket owns distribution.
- **Replacing the single-file viewer.**

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->
<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review/challenger waived)
- **Branch:** `feat/145-artifact-json-is-a-cache-that-a-second-renderer-turns-into-a-contract`
- **CHALLENGER:** OFF
- **work_doc_mode:** embed
- **TIER:** full · **SCOPE:** M · Phase A only

## PREMISE / REFINE

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`refine skipped: 0 unresolved product-decisions` — standing approval to choose approach and pass gates.
Phase B is out of scope (stack choice). 118 is done and no longer the A/B split.

## Design

- `ARTIFACT_VERSION = 1` on `OnboardingArtifact.as_dict` (not `contract_version`, not `DATASET_VERSION`)
- Pin key-paths in `tests/test_artifact_contract.py`; at v1 they must equal `V1_KEY_PATHS`; a later
  version must differ — that is AC2's made-to-fail
- Docs: PLAN / README / ROADMAP / CONVENTION / tool module stop calling the file a free-form cache
- File path unchanged: `.code-atlas/onboarding/artifact.json` (gitignored, regenerable)
- MCP payload key `cache` kept (path to the file); not a published-file-shape change

## Requirements matrix

| ID | Ph3 | Ph4 | Notes |
|---|---|---|---|
| AC1 | ✅ | waived | version + pinned key-paths |
| AC2 | ✅ | waived | v1 vs V1_KEY_PATHS; planted extra key witness |
| AC3 | ✅ | waived | standing-doc scan |
| AC4 | ✅ | waived | byte-identical `cache_json` |

## Cost ledger

| phase | dispatch | tokens |
|---|---|---|
| execute | main loop | unmeasured (host does not surface usage; review/challenger waived) |


## Review of PR #170 — the pin did not cover the shape it claimed to pin

`ARTIFACT_VERSION` and the docs were right. The conformance test was not: `key_paths` added
`key` for every top-level entry and `key[].field` for the keys of `value[0]` — one level, first
element only. It never descended into a `Mapping` value, so **`summary` was pinned as a bare key
and its whole sub-document was unpinned**: 39 of the 86 key-paths a real `generate_onboarding` run
writes had no row in `V1_KEY_PATHS`.

What sat in that gap is the part a second renderer is most likely to get wrong — the honesty
vocabulary 113/130/131 built: `summary.reachability.buckets[].sample` / `.count` /
`.sample_truncated`, `summary.reachability.caveat` and `.dropped`,
`summary.business_modules.coverage.note` / `.refused` / `.truncated`, and
`summary.mirrors.caveat`, whose own docstring says *"the caveat rides WITH the counts, so no
consumer can render one without the other."* Renaming or dropping any of them was a green suite.

Demonstrated, not argued: adding `"planted_new_key"` to the real `summary` — a shape change every
downstream renderer sees — left **all 25 tests green**, AC2's made-to-fail included. So did
renaming `sample_truncated` to `sample_cut`.

Fixed:

1. **`key_paths` recurses** into every mapping at any depth and unions over *every* list element,
   not `value[0]`. `V1_KEY_PATHS` is regenerated to the full 86-path set.
2. **The pin is taken over the artifact `generate_onboarding` actually writes**, not over
   `_sample()`. `summary` is a free-form `Mapping` on the dataclass, so a hand-built sample can
   only ever pin the keys the sample happens to carry — which is how the hole opened. `_sample()`
   keeps a test of its own: its paths must be a *subset*, never a superset.
3. **AC2 became a real made-to-fail.** It was `if ARTIFACT_VERSION == 1: assert observed ==
   V1_KEY_PATHS; return` — a copy of AC1 with a dead branch that asserted a v2 *must* have
   different keys, which is not true and would redden the suite for the wrong reason on the first
   bump. The pin is now `KEY_PATHS_BY_VERSION`, keyed by version: a re-shape without a bump is red
   *and* a bump without a new pinned set is red, each with a message that names which.
4. `HONESTY_KEY_PATHS` names the bounded-sample and caveat paths explicitly, so a rename is a
   break by name and not only by set difference.
5. AC3's doc scan missed `onboarding_llm/README.md`, which this PR itself edited; added.
   `onboarding_llm/server.py` still called those caches "like 088's onboarding cache" — reworded,
   since the point of Phase A is that the two are no longer the same kind of file.

Tests: AC1 verified red against a planted `summary` key and against a renamed `sample_truncated`;
the version-bump discipline verified red by setting `ARTIFACT_VERSION = 2` with no new pin.

**Not fixed, noted:** a path only reachable through a non-empty `mirrors.pairs` or
`business_modules.containers` is still unpinned — the `_cycle_repo` fixture produces neither. The
test docstring says so rather than implying the pin is exhaustive.
