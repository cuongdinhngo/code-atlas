---
id: 305
slug: versioned-change-assurance-evidence-bundle
title: "A check result is not yet a portable proof — define a versioned Change Assurance evidence bundle"
phase: 3
milestone: Change-Assurance
status: todo
depends_on: [303]
---

## Parent epic

[304 — Change Assurance](304_change-assurance-makes-every-important-change-carry-evidence.md).

## Goal

Turn 303's in-process result into a portable artifact a CI job can retain or a reviewer can paste
into a PR without losing provenance or caveats.

## Scope / Deliverables

1. A separately versioned evidence-bundle schema wrapping 303's result object. It names repository
   identity, base/head revisions, server/config build, graph completeness, confidence, truncation,
   reasons and every included claim.
2. Deterministic JSON plus Markdown rendered from that one schema. Markdown is a view, never a
   second computation.
3. A writer to an explicit output path and an offline validator that can reject unsupported,
   malformed or cross-repository bundles.
4. No default repository write: stdout remains valid, and writing requires an explicit path.
5. Documentation for storing JSON/Markdown as CI artifacts or pasting Markdown into a PR. No
   provider API call is added.

## Constraints

- The bundle version is not `CONTRACT_VERSION`, `DATASET_VERSION` or `ARTIFACT_VERSION`; bump only
  the document whose shape moves (R3.5).
- No graph query, build, traversal or policy decision lives in the writer/renderer.
- A caveat in JSON must appear in Markdown or Markdown must refuse to attest that section.
- Paths outside an explicitly selected output location are never removed or overwritten.

## Acceptance criteria

- A 303 fixture result round-trips through write/read/validate with byte-identical canonical JSON.
- JSON and Markdown name the same revisions, counts, verdicts and caveats; a consumer-level test
  fails when a caveat is dropped from Markdown.
- Unknown newer versions are refused directionally; malformed older artifacts never read as empty
  evidence.
- Two runs over identical input produce byte-identical files.
- The default command writes no tracked file and performs no network/provider action.
- A bundle from a different `index_root` is rejected when validated against the current repository.

## Out of scope

- Posting to GitHub/GitLab, editing a PR body, artifact retention policy or signing with a remote
  identity provider.
- Recomputing or judging any evidence from 303.

## References

[303](303_pre-pr-evidence-is-scattered-across-tools.md), [304](304_change-assurance-makes-every-important-change-carry-evidence.md),
`code_atlas/tools/claim.py`, `code_atlas/onboarding/dataset.py`,
`code_atlas/onboarding/artifact.py`, ENGINEERING_RULES R3.5, R4.2, R5.6 and R6.9.
