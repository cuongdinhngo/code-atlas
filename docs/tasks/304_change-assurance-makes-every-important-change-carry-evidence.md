---
id: 304
slug: change-assurance-makes-every-important-change-carry-evidence
title: "EPIC — make every important change carry graph-derived evidence before review"
phase: 3
milestone: Change-Assurance
status: todo
depends_on: [100, 138, 139, 257, 260, 266]
kind: epic
children: [303, 305, 306, 307, 308, 309, 310, 312]
---

## Why this exists

code-atlas can answer relationship, impact, architecture-rule and architecture-drift questions, but
those answers remain optional calls. A team can open a risky PR without asking any of them, and the
reviewer receives prose rather than reproducible evidence. A must-have product is not one with more
tools; it is one whose absence makes the change workflow observably less safe.

This epic turns the existing graph into a **Change Assurance layer**:

```text
change → verify → evidence bundle → agent brief / policy / test candidates → review
```

Every stage reads the same local graph. Nothing edits source, uploads code, invents certainty or
runs a second analysis pipeline.

## North star

For teams using AI on large repositories, over one four-week field window:

- at least **80% of code-changing PRs** run Change Assurance; and
- at least **50% of reviews** use at least one emitted evidence item.

The final field gate may conclude that the capability is useful but not must-have. The metric is a
decision rule, not a number the implementation is allowed to manufacture.

## Settled product decisions

1. Evidence is deterministic **JSON plus Markdown**, stored as a CI artifact or pasted into a PR.
   It is not committed or posted to a provider automatically by default.
2. Verification reports by default. Only explicit policy turns confirmed `RESOLVED` violations
   into a failing exit; HEURISTIC candidates never fail a gate.
3. Test impact begins as candidate reporting only. The full suite stays authoritative until recall
   is proven on a real corpus and a later acceptance bar is ratified.
4. The core stays local-first, deterministic and language-agnostic. No child may add an LLM,
   network call, source mutation, provider-specific write or second graph pipeline.

## Epic architecture

- **303 — Verify command:** one shell orchestration result over changed paths, signed impact,
  architecture rules, drift and honesty fields.
- **305 — Evidence bundle:** a versioned portable wrapper, validator and Markdown rendering over
  303's result.
- **306 — Agent change brief:** bounded graph context from explicit paths/qnames or a base revision.
- **307 — Architecture budgets:** human-authored policy over confirmed rules and measured drift.
- **308 — Test candidates:** report-only changed-code → candidate-test relationships.
- **309 — Test recall gate:** pinned-corpus evidence before any selective-test proposal.
- **312 — Widen the candidate walk:** 309 measured every miss at inbound depth 2, so the walk
  moves past direct callers and re-runs 309's reporter against its already-registered bar.
- **310 — Adoption gate:** the four-week 80%/50% field decision and removal-cost interview.

Dependency order:

```text
303 → 305
  ├→ 306
  ├→ 307
  └→ 308 → 309 → 312
305 + 306 + 307 + 309 → 310
```

Tasks 301 and 302 remain graph-trust improvements outside this epic. Better language resolution
helps assurance, but the epic must remain useful and honestly caveated at today's coverage.

## Epic acceptance criteria

- Every child ships its own tests, evidence and lifecycle; the epic itself ships no product code.
- 303–309 produce no claim stronger than their payload can distinguish.
- JSON and Markdown are renderings of graph-derived facts with revision, freshness, confidence and
  truncation preserved.
- No child silently narrows the project's normal test command.
- 310 records the north-star denominators and numerators and applies the predeclared verdict even
  when the result is negative.

## Breakdown

`BREAKDOWN: 7 tickets proposed | 7 INVEST self-checks emitted (6 letters each) | 0 tickets flagged for re-split`

### 303 — Verify command

- **I:** composes landed capabilities; bundle persistence is outside it.
- **N:** command naming and base discovery remain design choices within locked behaviour.
- **V:** gives humans, agents and CI one repeatable pre-PR answer.
- **E:** existing CLI and tool factories make the boundary estimable.
- **S:** one shell command and one result object.
- **T:** parity, exit-policy, determinism and operational-reason tests are specified.

### 305 — Evidence bundle contract

- **I:** consumes 303 output without changing graph analysis.
- **N:** schema fields and Markdown layout can be designed independently.
- **V:** makes evidence portable, reviewable and re-validatable.
- **E:** existing artifact and dataset versioning are precedents.
- **S:** one schema, writer, validator and renderer.
- **T:** conformance, round-trip, provenance and byte-stability tests.

### 306 — Agent change brief

- **I:** consumes explicit seeds and impact APIs; no policy dependency.
- **N:** ranking and size ceilings remain design choices.
- **V:** gives an agent bounded context before grep/read work.
- **E:** seed planning and signed impact already exist.
- **S:** one deterministic brief; no MCP tool or LLM seam.
- **T:** relevance, caveat-preservation and token-ceiling tests.

### 307 — Architecture budgets

- **I:** evaluates 138/139 outputs independently of briefs and test impact.
- **N:** projects author policy values; the server does not choose thresholds.
- **V:** turns architectural drift into an executable review contract.
- **E:** confirmed/candidate partitions and snapshot diff already exist.
- **S:** one generic policy vocabulary and evaluator.
- **T:** confirmed breach, candidate-only, missing-baseline and determinism tests.

### 308 — Test-impact candidates

- **I:** reports graph candidates without changing a test runner.
- **N:** ranking can evolve behind a report-only contract.
- **V:** shortens test investigation while preserving the full suite.
- **E:** `is_test`, inbound partitions and changed paths already exist.
- **S:** one reporter; no skip mode or runner argv.
- **T:** planted callers, candidate wording, caveat and never-skip guards.

### 309 — Test-impact recall gate

- **I:** measures 308 and changes no product behaviour.
- **N:** corpus and recall floor are ratified during that ticket's refinement.
- **V:** prevents selective-test claims from shipping on fixture confidence.
- **E:** cross-repo reporters and supervision benchmarks are precedents.
- **S:** one pinned corpus, labelled changes and committed reporter.
- **T:** repeatable recall/precision output and a falsifiable promotion verdict.

### 310 — Must-have adoption field gate

- **I:** observes completed surfaces without implementing them.
- **N:** protocol details may adapt while the 80%/50% bars stay fixed.
- **V:** decides whether workflow changed rather than counting capabilities.
- **E:** local fit counters and field protocols already exist.
- **S:** one four-week cohort protocol and decision record.
- **T:** counted denominators, provenance and removal-cost interviews.

## Refine record

`PREMISE: 13 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`

`RECALL: 5 claim(s) surfaced | 0 by symbol | 4 by handle | 1 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`

`REFINE: 8 unresolved surfaced | 4 want-decisions asked | 4 how-decisions resolved+cited | 0 ASSUMED | skip: no`

The ambiguous reference was “must-have”, a product outcome rather than a resolvable identifier. The
four settled wants are epic-first delivery, artifact destination, test-impact safety and the
80%/50% adoption bar. Architecture and ticket boundaries were derived from tasks 100, 138, 139,
257, 260, 266 and 303 plus PLAN §1.

## Scaffold gate

The split was ratified in conversation before these stubs were authored.

`EPIC LESSON: 1 lesson written to docs/LESSONS.md`

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`

No child executes until this scaffold is committed on a shared ref from a dedicated docs branch.
Breakdown re-ratification is **Experimental**: adding/removing a child or reversing a settled product
decision requires a counted delta and explicit human re-approval.
