---
id: 109
slug: onboarding-artifact-quality-gate
title: Onboarding — a quality gate on the emitted artifact, so filler cannot ship again (M11)
phase: 3
milestone: M11
status: todo
depends_on: [088, 108]
---

## Why this exists

Tasks 106 and 107 both shipped, were released, and were only caught by a human opening the HTML and
reading it. Both defects are **mechanically detectable** and both are named in the checklist of the
reference tool this design borrows from (`graph-reviewer`, Checks 6 and 7):

- *"No summaries that are empty or just restate the filename"* — code-atlas emitted 500/500 pages whose
  only content was the path (107).
- *"Tour has between 5 and 15 steps"* — code-atlas emitted 500 stops and called it a tour (111).

There is no gate between `build_artifact` and disk. Every onboarding defect so far has been found by
eye, after release. This ticket adds the missing gate, **before** 110–116 change the artifact's shape,
so the new shape is born gated.

## Scope

A deterministic checker over the in-memory `OnboardingArtifact` (no IO, no LLM), enforced by tests and
run in CI like the R1.1/R2.2 grep-gates:

| Check | Rule |
|---|---|
| C1 | no page whose body carries no fact absent from its own path (the 107 rule, as an invariant) |
| C2 | every page under a byte ceiling (the 108 rule, as an invariant) |
| C3 | every layer has a non-empty `description` (enables 110) |
| C4 | tour step count within `[5, 15]` once 111 lands; until then, assert the *current* count and fail on regression past a recorded ceiling |
| C5 | referential integrity: every path named in the tour, manifest and layer sets exists in the node set |
| C6 | no duplicate page paths; no page for a module absent from the tour |
| C7 | byte-stability: two builds of the same index produce identical output (R4.2) |

Failure is loud: `build_artifact` raises rather than writing a bad tree, matching the 050 precedent of
refusing rather than overwriting.

## Acceptance criteria

1. **AC1 (R6.5).** Each check has a test that is observed red against a deliberately-bad artifact
   fixture, and the seven fixtures are distinct — one per check.
2. **AC2.** Reverting task 107's fix makes C1 red; reverting 108's makes C2 red. Proven by patching the
   fixture, not by reverting the repo.
3. **AC3.** The gate runs on the anchor monorepo artifact and passes, with the C2 ceiling and C4 count
   recorded in the working doc as the numbers the gate now defends.
4. **AC4.** CI fails when the gate fails; the failure message names the check and the offending path.
5. **AC5.** The gate adds no measurable time to `generate_onboarding` on the anchor repo (report before
   and after).

## Out of scope

Judging *content quality* — whether a summary is any good is 117's problem. This gate only catches
structural filler, which is what shipped twice.
