---
id: 305
slug: versioned-change-assurance-evidence-bundle
title: "A check result is not yet a portable proof — define a versioned Change Assurance evidence bundle"
phase: 3
milestone: Change-Assurance
status: done
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 305 — Versioned Change Assurance evidence bundle (working doc)

- **Ticket:** 305 · **TIER:** full · **TRACK:** backend · **SCOPE:** S · **BASELINE:** green
- **Depends on:** 303 (open PR #408) — this branch fast-forwarded 303 tip; disclose stack.
- **reviewer:** off · **challenger:** on

## Phase 0 — Refine
`PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
**INPUT KIND:** ticket.

`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`
| H1 | Bundle module | `code_atlas/evidence_bundle.py` + `--bundle-json/--bundle-md` on check | ticket Scope; R3.5 |
| H2 | Version constant | `EVIDENCE_BUNDLE_VERSION = 1` separate from CONTRACT/DATASET/ARTIFACT | ticket Constraints; R3.5 |
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

## Requirements matrix
`SECTIONS: 5 found (Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=4 R=5 G=1 AC=6`
`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R3.5 (change-type) ✅ · R4.2 (change-type) ✅ · R5.6 (change-type) ✅ · R7.2 (change-type) ✅`
`BASELINE: green`

## Phase 2 — Design
**Approach.** Pure wrap/render/validate module; check CLI gains explicit write flags only.
`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
**PROVING TEST:** `.venv/bin/python -m pytest tests/test_evidence_bundle.py -q`

## Phase 3 — Execute
Diff ⊆ list: evidence_bundle.py, check flags, tests, runbook note, module-count bump, bookkeeping.
`.venv/bin/python -m pytest tests/test_evidence_bundle.py -q` → 8 passed.

## Phase 4 — Review
`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — VERDICT CLEAN (agent e5971ac8). Gate 4: challenger CLEAN; reviewer waived.
`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop`

## Phase 5 — Finalise
Outward: push + open PR. Depends on #408 (303).
