---
id: 303
slug: pre-pr-evidence-is-scattered-across-tools
title: "The graph can sign impact, check architecture rules and diff snapshots, but a pre-PR author must assemble the evidence by hand"
phase: 1.5b
milestone: Supervision
status: todo
depends_on: [100, 138, 139, 257]
---

## Parent epic

[304 — Change Assurance](304_change-assurance-makes-every-important-change-carry-evidence.md).
This ticket owns orchestration and one result object. Portable artifact versioning belongs to 305.

## Why this exists

The product already computes the evidence a reviewer needs:

- [100](100_claim-signing-output-mode.md) makes impact and relationship answers quotable;
- [138](138_architecture-rules-are-never-asked-of-the-graph.md) separates confirmed architecture
  violations from HEURISTIC candidates;
- [139](139_map-is-a-snapshot-so-nothing-shows-architectural-drift.md) compares two architecture
  snapshots; and
- [257](257_the-index-goes-blind-at-the-moment-it-is-most-wanted.md) labels answers from a behind
  index instead of silently presenting them as current.

Those capabilities are separate MCP calls. A pre-PR author must know which ones to invoke, choose a
base revision, refresh the index, preserve every caveat and manually turn several payloads into one
review artifact. The evidence exists but there is no repeatable shell workflow a human, agent or CI
job can run.

## Goal

One deterministic shell command answers: **what did this change affect, what moved
architecturally, and which declared architecture rules are now confirmed broken?** It composes the
existing graph and tools; it does not create another analysis pipeline.

## Scope / Deliverables

1. Add a shell entry point, provisionally `code-atlas-check`, that refreshes the current index
   through the existing build route and then reads the same tool/domain functions as MCP.
2. Determine the changed path set against a named base revision. `--base <ref>` overrides automatic
   discovery; the selected base and head are always printed. Failure to derive either is an explicit
   `base_not_resolved` operational error, never an empty change.
3. Produce one report containing:
   - changed indexed paths and the signed `impact` answer for them;
   - confirmed and candidate results from `check_architecture_rules`;
   - architecture drift from the committed onboarding manifest to a current, non-committed
     snapshot; and
   - freshness, coverage, truncation and confidence caveats from every source.
4. Support deterministic text for humans and JSON for CI. Both formats are renderings of one result
   object and carry the same counts, reasons and revision identity.
5. **Report by default.** Confirmed violations appear prominently but exit successfully.
   `--fail-on-confirmed` returns a distinct failing exit code only when at least one confirmed
   `RESOLVED` architecture violation exists. HEURISTIC candidates never fail the gate.
6. Operational failures—build refusal, incomplete index, unresolved base, malformed rules,
   unavailable baseline snapshot, schema mismatch or truncated evidence that cannot support the
   requested verdict—return non-success independently of `--fail-on-confirmed`.

## Constraints

- No 25th MCP tool. This is a shell consumer of the existing surface.
- No second graph, resolver, traversal or architecture-diff implementation. Shared decisions have
  one implementation (R1.8); the command delegates to the same factories/domain functions.
- The check may update `.code-atlas/graph.db`; it must not rewrite committed onboarding pages or
  delete files. Any current snapshot needed for comparison is built in memory or in owned temporary
  storage.
- A missing architecture-rules configuration is reported as `capability_not_configured`, not a clean
  pass. A missing architecture baseline is `snapshot_not_found`, not "no change".
- Default mode is informational. Only the explicit flag turns confirmed violations into a policy
  gate; candidates and unmeasured relationships stay visible and non-gating.
- Identical repository state, base and configuration yield byte-identical JSON apart from no
  timestamps or durations being included.

## Acceptance criteria

- **AC1 — parity.** On one fixture repository, the command's impact rows, signed claim, architecture
  violations and architecture diff equal direct calls to the existing underlying tools at the same
  revision.
- **AC2 — default report mode.** A confirmed violation is rendered with its rule id and path, while
  the default invocation exits successfully and labels the result `report_only`.
- **AC3 — opt-in gate.** The same fixture with `--fail-on-confirmed` returns the documented
  confirmed-violation exit code. A candidate-only fixture does not.
- **AC4 — operational honesty.** Missing rules, missing/incompatible snapshot, unresolved base,
  incomplete build and unsupported truncation each produce a distinct reason and non-success exit;
  none renders a clean report.
- **AC5 — changed-path truth.** Committed branch changes and dirty indexed files are both included;
  dirty unindexed documentation is disclosed but does not invent graph impact.
- **AC6 — deterministic dual rendering.** Two runs over the same state produce byte-identical JSON,
  and the text/JSON conformance test proves both are derived from the same result object.
- **AC7 — no second pipeline.** A guard proves the command imports and delegates to the existing
  build, impact, rule-check and architecture-diff implementations rather than re-declaring their
  graph logic.
- **AC8 — red first.** The confirmed-violation fixture is observed failing the opt-in gate before
  the implementation is accepted; default report mode remains green on that same fixture.

## Out of scope

- Choosing or authoring a project's architecture rules.
- Posting a PR comment, editing a PR body or integrating with one hosting provider.
- Fixing violations, suggesting code changes or mutating source.
- Treating test selection as proven impact; this graph does not yet model a complete
  change-to-test guarantee.

## References

[100](100_claim-signing-output-mode.md),
[138](138_architecture-rules-are-never-asked-of-the-graph.md),
[139](139_map-is-a-snapshot-so-nothing-shows-architectural-drift.md),
[257](257_the-index-goes-blind-at-the-moment-it-is-most-wanted.md),
`code_atlas/cli.py`, `code_atlas/tools/impact.py`,
`code_atlas/tools/check_architecture_rules.py`,
`code_atlas/tools/diff_architecture.py`, PLAN §1, ENGINEERING_RULES R1.4, R1.8, R4.2, R5.2,
R5.3, R5.5, R5.6, R6.5 and R6.9.
