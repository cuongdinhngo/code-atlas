---
id: 439
slug: verify-refs-patches-and-surfaces
title: "`verify_refs`: ready-to-apply patches, the MCP tool, and a count-only SessionStart line"
phase: 2
milestone: "0.11 Verify & Compute"
status: done
depends_on: [438, 434]
---

## Why this exists

Roadmap R1.4–R1.5 (0.11). The study 438 cites shows a warning alone does not change what an agent
does — it noticed the conflict and followed the file anyway. **Success means the file gets
corrected**, so every finding carries the cheapest correction: a successor, and where it is
deterministic, a patch. And an agent only uses what it can reach: an MCP tool, plus one line at
session start that names the instruction-file count first.

## Scope

1. **Patches, not edits.** For a `moved` row with exactly one successor, emit a unified diff that
   replaces the reference string in place; nothing else on the line changes. Grouped per file and per
   priority class, so all instruction-file rows apply in one step. `gone` / `never_existed` /
   `ambiguous` rows get a hint, no patch. code-atlas never applies one.
2. **CLI:** `--format patch` on 438's `--verify-refs`.
3. **MCP tool `verify_refs`:** globs, class filter, state filter, `format`, limit. Payload: per-file
   summary, capped rows, `total_count`, `truncated`, `untrusted_fields`; reference strings only (429).
   Read-only annotations, closed input schema (428); the description stays within 434's budget.
   Adding a tool moves the count pinned by tests (`main.TOOL_NAMES`, BACKLOG's tool count).
4. **SessionStart line**, opt-in and count-only, inside `hooks/signal.py`'s 150-token budget, the
   instruction class first, e.g. `code-atlas: 3 refs in instruction files no longer resolve (2 moved —
   patch ready); 41 in other docs.` `archive` rows never count. Nothing runs in the edit loop.

## Acceptance

1. Fixture: each single-successor `moved` row yields a patch that `git apply --check` accepts and that
   changes only the reference string; a two-successor row yields none.
2. The MCP payload of a doc holding instruction-like text carries reference strings only (429).
3. The SessionStart line never exceeds the signal budget, reports `unknown` separately from `ok`, and
   is absent unless opted in.
4. The tool surface test and 434's description budget stay green with the new tool counted.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 439 · **work_doc_mode:** embed · **Current phase:** done · merged in #167 as `4e0a37d9`.
- `TRACK: backend` · Run mode: `autorun 439 - 441`, first — `REVIEWER: OFF` (waived: "with skipped reviewer") ·
  `CHALLENGER: ON` · `cost_tier: standard`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/439-verify-refs-surfaces` from `main` at `e7896fa1`. Contract `.mango/run-contract-439.txt`
  (mango 1.21.0), written before any code; RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 5 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 0 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 5 want-decision asked | 2 how-decision resolved+cited | 5 ASSUMED | skip: no`

438's `doc_refs.verify_refs`, `main.TOOL_NAMES`, 429's `untrusted.FIELDS`, 434's caps and `hooks/signal.py`'s
`TOKEN_BUDGET = 150` resolve. Ambiguous: `hooks/signal.py` is the Read/Write hook; the SessionStart hook is
`hooks/state.py`. Recalled by area: 440-C1 (a deadline is an answer only if the scan fits), 438-C1.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the replacement's spelling | how | the successor written as the doc wrote the reference: root- or doc-relative (`posixpath.relpath`), a trailing `/` kept; a symbol keeps the doc's member separator and leading `\` |
| H2 | a doc with no newline at end of file | how | a small own diff writer emits `\ No newline at end of file`; `difflib` does not |
| W1 | scope 3 wants `format` and scope 1 a diff, but 429 forbids doc prose in the payload — a diff carries the doc's lines | want | **ASSUMED:** the tool's `format: patch` answers `edits` (file, line, ref, replacement) and `apply_with`, the CLI route that prints the diff |
| W2 | scope 1 groups per priority class, archive included? | want | **ASSUMED:** archive rows are never patched — an archive records what was true then |
| W3 | scope 4: "inside `hooks/signal.py`'s budget", opt-in how? | want | **ASSUMED:** the line rides `code-atlas-state` at `SessionStart` only, capped by `signal.TOKEN_BUDGET`; opt-in is `refs_session_line` (toml/env); its git history is capped at 3 s, past which rows are `unknown`, counted |
| W4 | AC1's "two-successor row" — 438 never produced one | want | **ASSUMED:** a folder whose files moved to two folders is `moved`, `git_rename_split`, with `successors` and a hint, no patch |
| W5 | 429's frame refuses a field holding two shapes; 438 gave `successor` a string (path) or an object (symbol) | want | **ASSUMED:** one shape per field — a symbol's `successor` is its qname beside `site`; an ambiguous path lists `candidate_paths` (438 is unreleased) |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=3 R=4 G=1 AC=4`
`CLARIFICATION: 7 raised | 7 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/34 touched files under UI paths`
`SCOPE: L`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "Success means the file gets corrected" | every finding carries its cheapest correction | ⚠ |
| C1 | Scope 1 | "code-atlas never applies one" | patches are printed / listed, never written | ⚠ |
| C2 | Scope 3 | "reference strings only (429)" | W1 | ⚠ |
| C3 | Scope 4 | "Nothing runs in the edit loop" | SessionStart only, never Read/Write | ⚠ |
| R1–R4 | Scope 1–4 | patches · `--format patch` · the tool · the line | as written, W1–W5 | ⚠ |
| AC1–AC4 | Acc 1–4 | as written | `tests/test_verify_refs_surfaces.py`; AC4 the surface tests | ⚠ |

`BASELINE: green — tests/test_verify_refs.py, test_tool_surface_budget.py, test_tool_manifest.py, test_untrusted_output.py, test_session_state_hook.py, test_config.py on main at e7896fa1: 130 passed, 57 skipped (adapter deps absent in the throwaway worktree)`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1 no language branch: the separator comes from the doc · §5 (change-type) ✅ R5.6 unknown counted apart from ok · §6 (change-type) ✅ R6.5 seen red, R6.7 the new tool joins every walk · §7 (change-type) ✅ R7.2, R7.5, R7.6`

## Phase 2 — design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**Approach.** `doc_refs.py`: `scan()` (every row, sorted, annotated) and `summarize()` (counts, the state filter, the
cap) split `verify_refs`; `_annotate` sets `patch_ready` or a `hint`; `patches()` builds one diff per file, instruction
first, replacing only bounded occurrences of the reference on its line; `session_line()`. `query.py`: `--format patch`,
`--state`. `tools/verify_refs.py`: the 26th tool. `hooks/state.py`: `refs_line` at `SessionStart`. `config.py`:
`refs_session_line`. Wiring: `TOOL_NAMES`, routing map, `untrusted.FIELDS`, manifest, pins, docs, the generated skill.
**Rejected:** the diff in the MCP payload (W1); a separate SessionStart command (one hook already runs there);
`difflib` (no end-of-file marker).
**Proving test:** `tests/test_verify_refs_surfaces.py`.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

## Phase 3 — execute

Main loop, no `implementer` (`ac4f9d02`). **R6.5:** on `main` the test cannot import the tool; while building, AC1's
split row read `ok` (an emptied folder `git mv` leaves behind) and the surface cap was 96 chars over until the
description was cut. **This repo (counts only):** the session line takes 3.4 s; a full scan 3.4 s, 10,638 rows.

## Phase 4 — review

`REVIEWER: OFF` (waived by the run's args — no rule-book seat looked) · `CHALLENGER: ON`. Review step: the ticket-blind
`challenger` alone, at `ac4f9d02`.

- **`challenger` round 1** (68,413 tokens): 9 met · 2 not met. **Taken:** High 1 — a CRLF doc's patch failed
  `git apply` (`read_text` normalises line endings): `patches()` now reads bytes. High 2 — `splitlines` broke at
  U+2028: diff and extractor both count lines at `\n`. Medium 3 — five `verify_refs` paths a live answer reaches
  left the unreachable list. A CRLF + U+2028 test was seen red on `ac4f9d02`, green on `a8c08fb0`.
  **Not taken:** `--state`, `detail_level` and `markdown` (every tool takes `detail_level`; the filter is scope 3's on
  the CLI too); the session line's trailing route pointer.
- **`challenger` round 2** (verify-only, at `a8c08fb0`): its final line, transcribed:

`CHALLENGER VERDICT: 11 requirement(s) rebuilt | 11 met | 0 not met | 0 can't tell | 0 not-met covered by a recorded exclusion`

Residual it named, unprobed: a doc with lone-`\r` line endings has its rows skipped (counted), never mis-patched.

Verdict: clean (challenger 11 of 11; no rule-book reviewer). `Ph3/4 proven by`: AC1–AC3 →
`tests/test_verify_refs_surfaces.py` (13); AC4 → `tests/test_tool_surface_budget.py`, `test_tool_manifest.py`.

- **`challenger` round 3** (verify-only, at `404cf5f4`): the gate-driven docs-only range `a8c08fb0..404cf5f4` —
  no code changed; 11 met.

Reviewed at 404cf5f4

## Phase 5 — finalise

**Durable lesson.** 439-C1 `text-read-for-meaning-cannot-feed-a-byte-exact-writer` (new, type 2).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

**One gate-driven change, re-reviewed by round 3.** Gate run 1 at `3d595ad0` was RED on one pin: the
claim-signing doc's unsigned-tools list must name every tool (`docs/design/impact-and-claims.md` gained the
`verify_refs` row, `404cf5f4`). Docs only; the challenger's round 3 saw it. Run 2:

Ran at 404cf5f4

```
$ scripts/gate.sh
26 passed · 0 failed · 0 skipped
GATE GREEN — all 26 checks passed
```

### Outward actions

Under the handover: push `feat/439-verify-refs-surfaces`; open its PR against `main`. Deferred: ratify W1–W5; merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 4 review | ticket-blind `challenger` | 1 | 68,413 |
| 4 review | ticket-blind `challenger` | 2 | 4,380 (resumed: 72,793 cumulative − 68,413) |
| 4 review | ticket-blind `challenger` | 3 | 1,919 (resumed: 74,712 cumulative − 72,793) |

`LEDGER TOTAL: 74,712 · top cost driver: 4 review / challenger` — main loop unmeasured.

**After the PR — CI only.** CI's test job failed two tests the local gate passed: the CLI and SessionStart tests load
their config from the environment, and this host's shell exports `CA_PYTHON_CMD`, CI's does not — so the moved
symbol's old body could not be parsed and read `unknown`. The tests now name the adapter as 438's CLI test does; seen
red with every `CA_*` unset, green after. Test-only change, after `Reviewed at` and the gate; CI re-verifies.
