---
id: 428
slug: tool-surface-manifest
title: "The tool surface is pinned — every tool declares honest annotations and closed schemas, and a committed manifest makes any change a reviewed diff"
phase: 2
milestone: Trust
status: todo
depends_on: [423]
---

## Why this exists

The 24 tools declare no MCP `annotations`, so a client cannot tell the read-only queries from the
two tools that write (`build_or_update_index`, `generate_onboarding`). Input schemas are whatever
FastMCP generates, unaudited. Nothing pins tool names, descriptions or schemas, so a changed
description — the vector a "rug pull" uses — would ship as an unreviewed side effect. Error answers
and stdout discipline are not tested for what they leak.

## Acceptance

1. **Annotations:** every query tool `readOnlyHint: true`, `openWorldHint: false`; the two writers
   `readOnlyHint: false`, `destructiveHint: false`, `idempotentHint: true`. A test reads them from
   the live server.
2. **Closed schemas:** `additionalProperties: false` on every input schema; closed domains are
   enums; free strings are length-bounded. A test walks every schema.
3. **Manifest:** `tests/fixtures/tool_manifest.json` (names, descriptions, schemas, annotations)
   generated from the live server by a script that prints the diff; a test fails on drift; a change
   needs a CHANGELOG line (R9.4). Seen failing on an edited description.
4. **Error hygiene:** a tool error is an `isError` result with no traceback and no host path
   outside the repo (fixtures: a bad argument, an unreadable index).
5. **stdout is MCP only:** a test starts the server over stdio with an adapter that prints to
   stdout and sees only well-formed JSON-RPC frames.
6. **stdio only:** a test refuses an HTTP or SSE transport under `code_atlas/` (SEC-MCP-01).

## Call sites

`code_atlas/main.py` (tool registration, `TOOL_NAMES`), `code_atlas/tools/*`, new
`scripts/gen_tool_manifest.py`, `tests/fixtures/tool_manifest.json`, `docs/TOOLS.md`;
standard rows SEC-MCP-01..05, 07.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 428 · **work_doc_mode:** embed · **Current phase:** 2 design · **Next action:** execute.
- `TRACK: backend` · Run mode: `autorun 427 - 430 - 424 - 425 - 428 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/428-tool-surface-manifest`, **stacked on `feat/425-dependency-lock-and-audit`** (#126).
  Contract `.mango/run-contract-428.txt`. RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 9 unresolved surfaced | 2 want-decision asked | 7 how-decision resolved+cited | 2 ASSUMED | skip: no`

**Premise.** `code_atlas/main.py` (`build_server`, `serve`, `TOOL_NAMES`), `code_atlas/tools/*`, `docs/TOOLS.md`
resolve; `scripts/gen_tool_manifest.py` and `tests/fixtures/tool_manifest.json` are to be created. FastMCP 3.4.11
(the lock's) offers `server.tool(fn, annotations=…)`, `FastMCP(mask_error_details=…, strict_input_validation=…)`.
Recall (type 2, by handle): 427-C1 `a-loader-guard-misses-the-entry-that-loads-nothing` (the annotation test reads
the served list, every tool, not the names one file lists); 424-C1 `a-subset-reader-must-fail-closed` (the schema
walk refuses a schema node it does not recognise).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where annotations are set | how | in `serve()` (`main.py`), one table by name: the two writers (`build_or_update_index`, `generate_onboarding`) get `readOnlyHint: false, destructiveHint: false, idempotentHint: true`; every other tool `readOnlyHint: true, openWorldHint: false` |
| H2 | closing the schemas | how | `strict_input_validation=True` on the server, so an unknown argument is refused, and one post-registration pass sets `additionalProperties: false` on every object and a `maxLength` on every free string; closed domains already typed `Literal` become `enum` |
| H3 | the manifest | how | `scripts/gen_tool_manifest.py` lists names, descriptions, input schemas and annotations from a live `build_server` over a fixture config; `--write` regenerates, the default prints the diff and exits 1 on drift |
| H4 | the CHANGELOG link (R9.4) | how | a commit-range check beside `attribution_markers.py`: a range that changes `tool_manifest.json` without touching `CHANGELOG.md` fails — in CI on pull requests and in the gate |
| H5 | error hygiene | how | `mask_error_details=True`; a test drives a bad argument and an unreadable index and asserts `isError`, no `Traceback`, and no path outside the repo |
| H6 | stdout discipline | how | a subprocess test speaks JSON-RPC to `code-atlas` over stdio with an adapter that writes to its own stdout and stderr, and reads only well-formed frames back |
| H7 | stdio only | how | an AST test refuses `run(transport=…)` other than stdio and any `sse` / `http` / `streamable` transport import under `code_atlas/` (SEC-MCP-01) |
| W1 | the default string bound | want | **ASSUMED (awaiting ratification):** 4,096 characters for a free string (a query, a path, a qname); a field that legitimately carries more (none known) gets its own bound |
| W2 | strict validation | want | **ASSUMED (awaiting ratification):** an unknown argument is an error, not ignored — a client sending an old parameter name now hears it |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Acceptance · Call sites) | 3 decomposed | ROWS: C=1 R=0 G=1 AC=6`
`CLARIFICATION: 9 raised | 9 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/10 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

W1–W2 count as self-resolved because the handover handed them back; each stands `ASSUMED` for the maintainer.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a changed description … would ship as an unreviewed side effect" | annotations, closed schemas, a pinned manifest | ⚠ |
| AC1 | Acc 1 | "every query tool `readOnlyHint: true` … A test reads them from the live server" | H1 | ⚠ |
| AC2 | Acc 2 | "`additionalProperties: false` … enums … length-bounded" | H2, W1, W2 | ⚠ |
| AC3 | Acc 3 | "manifest … generated from the live server … a test fails on drift; a change needs a CHANGELOG line" | H3, H4 | ⚠ |
| AC4 | Acc 4 | "an `isError` result with no traceback and no host path outside the repo" | H5 | ⚠ |
| AC5 | Acc 5 | "sees only well-formed JSON-RPC frames" | H6 | ⚠ |
| AC6 | Acc 6 | "a test refuses an HTTP or SSE transport" | H7 | ⚠ |
| C1 | Call sites | "rows SEC-MCP-01..05, 07" | each closes on its test | ⚠ |

`BASELINE: green — the suite on feat/425-dependency-lock-and-audit at 42fa2351 (Docker: 5474 passed, 8 skipped)`

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.8: one annotation table and one schema pass in serve() · §3 (change-type) N/A because no contract vocabulary changes; the tool surface is the MCP schema, pinned by the manifest · §5 (change-type) ✅ R5.3: an unknown argument fails loud · §6 (change-type) ✅ R6.5: each guard seen failing; R6.7: the manifest is generated, never hand-kept · §7 (change-type) ✅ R7.2, R7.5, R7.6 · §9 (change-type) ✅ R9.4: a surface change needs a CHANGELOG line; R9.6`

## Phase 2 — design

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- 427-C1: the annotation and schema tests iterate the live server's `list_tools()`, never `TOOL_NAMES` alone, so a
  tool registered outside the table is still read.
- 424-C1: the schema walk raises on a node shape it does not know (`$ref`, `anyOf` it cannot close) instead of
  passing it.

**Approach.**
1. `main.py`: `FastMCP(…, mask_error_details=True, strict_input_validation=True)`; `serve()` passes the
   annotations from one table; a `close_schemas(server)` pass after registration.
2. `scripts/gen_tool_manifest.py` + `tests/fixtures/tool_manifest.json` + `tests/test_tool_manifest.py` (drift,
   seen red on an edited description).
3. `scripts/surface_changelog.py` (range check) in `ci.yml` and `gate.sh` (parity).
4. Tests: `tests/test_tool_surface.py` (annotations, closed schemas, an unknown argument refused, error hygiene,
   stdio frames, no HTTP/SSE).
5. Docs: SEC-MCP-01..05, 07 rows; `docs/TOOLS.md` (annotations, the manifest); SECURITY.md; CHANGELOG.

**Rejected:** hand-annotating each tool module (24 edits, and a 25th tool would ship without one — R1.8);
a manifest of names only (a description change is the vector the ticket names).

**Change list:** `code_atlas/main.py`, new `scripts/gen_tool_manifest.py`, new `scripts/surface_changelog.py`,
new `tests/fixtures/tool_manifest.json`, new `tests/test_tool_manifest.py`, new `tests/test_tool_surface.py`,
`.github/workflows/ci.yml`, `scripts/gate.sh`, `tests/test_ci_and_gate_agree.py`, `docs/TOOLS.md`,
`docs/SECURITY_STANDARD.md`, `SECURITY.md`, `CHANGELOG.md`; bookkeeping.

**Proving tests:** `tests/test_tool_surface.py`, `tests/test_tool_manifest.py` — each arm seen red on the base.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
