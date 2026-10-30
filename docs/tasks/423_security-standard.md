---
id: 423
slug: security-standard
title: "The security standard lives in the repo — every SEC criterion names the test, CI step or setting that holds it, and a conformance test refuses a row with none"
phase: 2
milestone: Trust
status: todo
depends_on: [422]
---

## Why this exists

0.9.1 (419–421) fixed one advisory, but the repo states no standard it holds itself to: a
criterion that is not written down cannot be checked, and one that is checked by nothing regresses
silently. The standard was drawn up in a 2026-10-27 audit against the MCP specification
(2026-07-28 security best practices and local-server guidance), OWASP (LLM and Agentic Top 10 2026,
MCP Top 10, MCP Security Cheat Sheet), CoSAI's MCP guide, OpenSSF Scorecard and the OSPS Baseline,
SLSA v1.2, the Docker/OWASP container rules and Claude Code's hooks and plugins references.
It has seven groups (`SEC-IN` untrusted repo input, `SEC-MCP` protocol and tool surface, `SEC-PI`
prompt injection and LLM output, `SEC-PL` plugin and hooks, `SEC-SC` supply chain and release,
`SEC-CT` container, `SEC-GV` governance). Tickets 424–431 close the open rows; this ticket makes
the standard binding first, so each later ticket fills its rows rather than inventing them.

## Acceptance

1. **`docs/SECURITY_STANDARD.md`** (tier 2, reached by pointer): one row per criterion — ID, the
   criterion, level (MUST/SHOULD), source, and **Verified by**: a test (`tests/…::name`), a CI step
   (a job/step name in a workflow), a repo setting checked by name, or `DOC` (a section that
   states it). A row not yet held reads `open: NNN` naming the ticket that closes it. A SHOULD row
   may be deferred only with its reason written in the row.
2. **Rule book §9 Security** in `docs/ENGINEERING_RULES.md`, short binding rules citing the IDs:
   the indexed repo, its index directory and database are untrusted input; a subprocess argument
   from repo, index or tool input is validated and fenced, and git runs hardened; every index
   write goes through `containment`; a tool-surface change is a reviewed diff with a CHANGELOG
   line; a security fix is developed privately and disclosed by advisory; every MUST criterion has
   a guard seen failing (R6.5). The size budget is raised only as argued, after R7.6 prunes.
3. **Conformance test** `tests/test_security_standard.py`: parses the standard and fails when a
   row's Verified-by names a test that does not exist, a CI step no workflow has, or an `open:`
   ticket whose task file is `done` or missing; and when a MUST row is deferred. Seen failing on a
   planted row with no guard (R6.5).
4. **Rows already held are wired now:** the criteria 419–421 closed point at their existing tests
   (`test_git_revision_arguments`, `test_index_artifact_trust`, `test_index_text_injection`, …),
   and rows held by existing guards (SQL confinement, no HTTP transport, adapter command gate)
   point at theirs; where no guard exists the row is `open:` on the ticket that adds one.
5. **`SECURITY.md` rewritten** from the standard's trust model: who is trusted for what (the user
   and their environment; the client's tool arguments; the indexed repo including a committed index
   — untrusted; network responses; dependencies and Actions as pinned), every network call
   code-atlas makes, every git command it runs, the client-side controls a user should keep on
   (tool approval, no auto-update of a branch-tracking marketplace), and the known limitations
   carried from 0.9.1 — naming git filter drivers (`filter.<name>.clean`/`process`), which no
   per-command override covers, among the repo config that still applies. A test keeps the listed
   git commands equal to the ones `gitutil` runs.

Out of scope: closing any open row — each belongs to 424–431. The repo-settings drift check is 424.

## Call sites

New: `docs/SECURITY_STANDARD.md`, `tests/test_security_standard.py`. Changed: `SECURITY.md`,
`docs/ENGINEERING_RULES.md` (§9, pre-PR self-check), `tests/test_doc_size_budget.py` (argued),
`code_atlas/gitutil.py` (read only, by the doc test).
