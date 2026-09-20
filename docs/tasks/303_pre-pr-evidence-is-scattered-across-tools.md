---
id: 303
slug: pre-pr-evidence-is-scattered-across-tools
title: "The graph can sign impact, check architecture rules and diff snapshots, but a pre-PR author must assemble the evidence by hand"
phase: 1.5b
milestone: Supervision
status: done
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 303 — Pre-PR evidence is scattered across tools (working doc)

- **Ticket:** 303
- **Type:** enhancement
- **Repo(s):** app (.)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 UI paths
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed

## Session status
- **status:** in-progress (autorun)
- **branch:** feat/303-pre-pr-evidence-is-scattered-across-tools
- **reviewer:** off · **challenger:** on

---

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
- `code_atlas/cli.py`, `code_atlas/tools/impact.py`, `code_atlas/tools/check_architecture_rules.py`, `code_atlas/tools/diff_architecture.py`

`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

**INPUT KIND:** ticket.

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| H1 | Automatic base discovery | `git merge-base HEAD` against `main`/`master`/`origin/main`/`origin/master` (first that resolves); `--base` overrides. Failure → `base_not_resolved`. | ticket Scope §2; `gitutil.changed_paths` since-arg |
| H2 | Module / entry point | New `code_atlas/check.py` + `code-atlas-check` console script (sibling of `code-atlas-build`). | ticket Scope §1; `pyproject.toml` console_scripts; `cli.py` pattern |
| H3 | Exit codes | `0` report_only success; `2` confirmed under `--fail-on-confirmed`; `1` any operational failure. | ticket Scope §5–6; `cli.py` OK/FAILED pattern |

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=6 R=6 G=1 AC=8`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | One shell command: impact + arch rules + drift | Compose existing tools | ticket | D1–D3 | AC1,AC7 | ☐ |
| C1 | Constraints | No 25th MCP tool | shell only | Constraints | D1 | review | ☐ |
| C2 | Constraints | No second pipeline | delegate factories | Constraints | D1–D3 | AC7 | ☐ |
| C3 | Constraints | May update graph.db; not committed onboarding | build + temp snapshot | Constraints | D2–D3 | AC4 | ☐ |
| C4 | Constraints | Missing rules → capability_not_configured | exit 1 | Constraints | D1 | AC4 | ☐ |
| C5 | Constraints | Missing baseline → snapshot_not_found | exit 1 | Constraints | D3 | AC4 | ☐ |
| C6 | Constraints | Deterministic JSON (no timestamps) | sort_keys dump | Constraints | D1 | AC6 | ☐ |
| R1 | Scope | `code-atlas-check` + build refresh | entry + build_or_update | Scope 1 | D1 | proving | ☐ |
| R2 | Scope | Changed paths vs base; print base/head | gitutil + discover | Scope 2 | D1 | AC5 | ☐ |
| R3 | Scope | One report: impact, rules, drift, caveats | result object | Scope 3 | D1–D3 | AC1 | ☐ |
| R4 | Scope | Text + JSON from one object | dual render | Scope 4 | D1 | AC6 | ☐ |
| R5 | Scope | Default report_only; `--fail-on-confirmed` | exit 0 vs 2 | Scope 5 | D1 | AC2,AC3 | ☐ |
| R6 | Scope | Operational failures independent | exit 1 | Scope 6 | D1 | AC4 | ☐ |
| AC1 | AC | Parity with underlying tools | same factories | AC1 | D1–D3 | proving | ☐ |
| AC2 | AC | Default exits 0 with confirmed shown | report_only | AC2 | D1 | proving | ☐ |
| AC3 | AC | `--fail-on-confirmed` → exit 2; candidates no | gate | AC3 | D1 | proving | ☐ |
| AC4 | AC | Distinct operational reasons + non-success | reasons enum | AC4 | D1–D3 | proving | ☐ |
| AC5 | AC | Committed+dirty indexed; disclose unindexed | path split | AC5 | D1 | proving | ☐ |
| AC6 | AC | Byte-identical JSON; text from same object | render | AC6 | D1 | proving | ☐ |
| AC7 | AC | Import guard — no second pipeline | ast/import test | AC7 | D1 | proving | ☐ |
| AC8 | AC | Red-first opt-in gate on fixture | test order | AC8 | D1 | proving | ☐ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 Q |
|-------|---------------|------------------------|--------|--------------|----------|
| AC1 | parity | same create() factories | Y | assert payloads | — |
| AC2 | report_only exit 0 | exit code map | Y | pytest | — |
| AC3 | fail-on-confirmed | exit 2 vs candidates | Y | pytest | — |
| AC4 | operational honesty | reason + exit 1 | Y | pytest | — |
| AC5 | changed-path truth | gitutil + indexable | Y | pytest | — |
| AC6 | deterministic dual | round-trip render | Y | pytest | — |
| AC7 | no second pipeline | import guard | Y | ast test | — |
| AC8 | red first | fail-on-confirmed before green | Y | test order | — |

---

## Phase 1 — Analysis

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R1.8 (change-type) ✅ · R4.2 (change-type) ✅ · R5.3 (change-type) ✅ · R6.5 (change-type) ✅ · R7.2 (change-type) ✅`

### BASELINE

Related suite: `pytest tests/test_architecture_rules.py tests/test_architecture_diff.py tests/test_build_cli.py -q` → 28 passed.

`BASELINE: green`

---

## Phase 2 — Design

**Approach.** Add `code_atlas/check.py` that (1) refreshes via `build_or_update_index.create`, (2) resolves base/head and changed paths via `gitutil`, (3) calls `impact.create(..., sign=True)`, `check_architecture_rules.create`, and architecture-diff against committed `docs/onboarding/manifest.json` vs an in-memory current snapshot assembled with the same `build_artifact`/`build_dataset`/`manifest_dict` path `generate_onboarding` uses (no committed write). One result object; text and JSON are pure renders. Extract `assemble_onboarding_snapshot` in `generate_onboarding.py` so snapshot assembly has one owner (R1.8).

**Rejected alternatives.** 25th MCP tool — Constraints C1. Second impact/rules walk — C2. Always write onboarding pages for "after" — C3 / R5.7.

### Smallest change-list

| # | Change | File/area | Ph2 | k/N |
|---|--------|-----------|-----|-----|
| D1 | `code_atlas/check.py` + console script + proving tests | code_atlas/, pyproject.toml, tests/ | R1–R6, AC1–AC8 | 8/11 |
| D2 | Extract in-memory snapshot assemble for drift "after" | `tools/generate_onboarding.py` | R3, C3, AC1 | 2/11 |
| D3 | Bookkeeping (BACKLOG, TOKEN_LEDGER, ticket status) | docs/ | R7.2 | 1/11 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**PROVING TEST:** `.venv/bin/python -m pytest tests/test_check_cli.py -q`

**SCOPE:** M

**Verification plan:** unit/integration on fixture repos (rules confirmed + candidate-only + missing rules/manifest/base); import-guard test; dual-render determinism; no ❌.

---

## Phase 3 — Execute

**Diff ⊆ approved list:** D1 `code_atlas/check.py` + console script + `tests/test_check_cli.py` · D2 `assemble_onboarding_snapshot` / `manifest_dict_for` in `generate_onboarding.py` · D3 bookkeeping pending finalise.

**Verification sweep**

`.venv/bin/python -m pytest tests/test_check_cli.py -q` → 12 passed (tree under review).

`diff ⊆ approved list`: yes — check CLI, generate_onboarding extract, pyproject script, proving tests only.

---

## Phase 4 — Review

`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — VERDICT CLEAN (agent c47e9784). Gate 4: challenger CLEAN; reviewer waived.
F1 fixed: confirmed gate uses rules `total_count` only; truncation stays in caveats.

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (implement + challenger)`

## Phase 5 — Finalise

Outward actions authorised: (1) push feature branch (2) open PR.

