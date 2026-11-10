---
id: 449
slug: read-symbol-pattern
title: "`read_symbol` takes a `pattern` and returns only the matching lines of a long body"
phase: 2
milestone: "Round-3 field gaps"
status: todo
depends_on: []
---

## Why this exists

Round-3 field feedback: a 300–670-line body is either elided or returned whole, and the question
was "where inside this method is X". Agents then fell back to `Read` with an offset, or to a guarded
`grep`, costing a round trip (asked for as `grep_in_symbol` / `pattern`, and as "a search string
inside a method"). `read_symbol` today takes `line_start` / `line_end` / `max_lines` only.

## Scope

1. A `pattern` parameter: a literal substring by default, case-insensitive. Regex only with
   `pattern_regex=true`, under the rules-file regex safety check (430: length, no backreference, no
   nested repeat).
2. The answer keeps the symbol header and returns each matching line with `context` lines around it
   (default 2, max 10), merged where they overlap, each with its absolute line number. It reports
   `pattern_matches` and, past a cap of 50, `pattern_truncated`.
3. No match is `pattern_matches: 0` with the symbol's span, so a caller knows the body was searched.
4. Tool surface: one parameter added — update `tool_manifest.json`, `docs/TOOLS.md` and the
   description budget.

## Acceptance

- On a fixture method of 400 lines, `pattern="needle"` returns the matching lines plus context, not
  the body; tokens are reported against the whole-body answer.
- A refused regex names the rule it broke; a closed schema still refuses an unknown argument.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 449 · **work_doc_mode:** embed · **Current phase:** review
- `TRACK: backend` · Run mode: `autorun 447 - 448 - 449 - 450`, third — `REVIEWER: OFF` (waived: "with skipped
  reviewer") · `CHALLENGER: ON` · `cost_tier: standard`. The handover delegates decisions, so a want-decision is
  `ASSUMED`, never silent.
- Branch `feat/449-read-symbol-pattern` from `main` at `89ecb16d`, built in a worktree. Contract
  `.mango/run-contract-449.txt` (mango 1.21.0), written before any code; RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run | 0 pending-merge`.

## Phase 0 — refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 6 want-decision asked | 2 how-decision resolved+cited | 6 ASSUMED | skip: no`

`read_symbol`'s `line_start` / `line_end` / `max_lines`, 430's safety check (`limits.checked_pattern`),
`tests/fixtures/tool_manifest.json` and `docs/TOOLS.md` resolve. Recalled by handle (a new tool parameter): 412-C1
`a-new-parameter-meets-the-surface-guards`, 430-C1 `redos-is-overlap-not-nesting`. The exposure-checker (1 dispatch)
returned 6; they fold in below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the regex safety rules | how | `limits.checked_pattern` unchanged, its refusal text named (ticket scope 1, 430) |
| H2 | where invalid input is refused | how | at the entry, before any return (R5.11) |
| W1 | "one parameter added" vs `pattern`, `pattern_regex`, `context` | want | **ASSUMED:** three parameters — scope 1–2 name all three; "one" read as one capability |
| W2 | `pattern` beside the body selectors | want | **ASSUMED:** `line_start`/`line_end` narrow the search; `full_body` / `max_lines` are refused beside it (they select a body the answer never returns) |
| W3 | the answer's shape | want | **ASSUMED:** `source` is the signature line; `pattern_hunks` = `{line_start, line_end, lines}`, each line `N> text` (a match) or `N: text` (context); `pattern_span` = the lines searched; `line_count` = the declaration's span |
| W4 | the cap of 50 | want | **ASSUMED:** 50 matching lines shown; `pattern_matches` is the true total; `pattern_truncated: true` past it |
| W5 | "tokens are reported against the whole-body answer" | want | **ASSUMED:** the AC test prints both estimates and requires the pattern answer under a fifth of the whole body |
| W6 | the description budget | want | **ASSUMED:** the description rewritten to fit 600 characters (the `path_outside_root` sentence stays in `docs/TOOLS.md`), `SURFACE_CAP` +225 for the three schema entries |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Scope · Acceptance) | 3 decomposed | ROWS: C=1 R=4 G=1 AC=2`
`CLARIFICATION: 8 raised | 8 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/6 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`STRUCTURE: native`

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "where inside this method is X" | one call answers it | ✅ |
| R1 | Scope 1 | "a literal substring by default, case-insensitive. Regex only with `pattern_regex=true`, under the rules-file regex safety check" | H1 | ✅ |
| R2 | Scope 2 | "keeps the symbol header … `context` lines … merged … absolute line number … `pattern_matches` … `pattern_truncated`" | W3, W4 | ✅ |
| R3 | Scope 3 | "No match is `pattern_matches: 0` with the symbol's span" | `pattern_span` | ✅ |
| R4 | Scope 4 | "update `tool_manifest.json`, `docs/TOOLS.md` and the description budget" | W6 | ✅ |
| C1 | Why | "`read_symbol` today takes `line_start` / `line_end` / `max_lines` only" | unchanged for a call with no `pattern` | ✅ |
| AC1 | Acc 1 | "a fixture method of 400 lines … the matching lines plus context, not the body; tokens are reported" | fixture, W5 | ✅ |
| AC2 | Acc 2 | "A refused regex names the rule it broke; a closed schema still refuses an unknown argument" | fixture + manifest | ✅ |

`BASELINE: green — read_symbol, tool-surface and limits suites on main at 89ecb16d: 255 passed`

Ran at 89ecb16d (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q <tool_manifest, tool_surface_budget, tool_descriptions, agent_brief_usage_completeness, limit_clamp_visible, tool_surface, read_symbol*, limits_and_containment>
255 passed in 28.76s
```

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §5 (change-type) ✅ R5.11 every new parameter checked at the entry, R5.6 a zero says what was searched · §6 (change-type) ✅ R6.1 a fixture over the tool, R6.5 seen red, R6.7 the manifest is generated · §7 (change-type) ✅ R7.2 ledger, R7.5 comments · §9 (change-type) ✅ R9.4 a surface change with a CHANGELOG line, R9.1 a regex from a tool call passes the safety check`

## Phase 2 — design

`HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- `a-new-parameter-meets-the-surface-guards` — traced: run on the first cut, before its commit, two guards were red —
  `test_the_descriptions_fit_the_budget_and_carry_no_references` (the description at 849 of 600 characters) and
  `test_the_whole_surface_with_schemas_stays_under_its_cap` (26,304 of 25,805); both folded into the change list (W6).
  The same guards on the committed tree:

Ran at 6c0e899e
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_tool_manifest.py tests/test_tool_surface_budget.py tests/test_tool_descriptions.py tests/test_agent_brief_usage_completeness.py tests/test_limit_clamp_visible.py tests/test_tool_surface.py
126 passed in 16.56s
```
- `redos-is-overlap-not-nesting` — does not apply because the change reuses `checked_pattern` as it stands and adds no
  rule of its own.

**Approach.** `_require_pattern` compiles the search at the entry (escaped literal, or the checked regex, both
`IGNORECASE`) and refuses the bad combinations; `_BodyOpts` carries it and `context`; `_found_body_payload` — the one
path every found read takes — answers a `pattern` with the signature, `pattern_span` and `_pattern_payload`'s merged,
numbered hunks. **Rejected:** a separate `grep_in_symbol` tool (a 27th tool for one parameter's job); returning the body
with matches marked (the AC asks for not the body).
**Proving test:** `tests/test_read_symbol_pattern.py`.

| Change | File | Blast radius | Ph2 covered by |
|---|---|---|---|
| parameter, entry checks, hunks | `code_atlas/tools/read_symbol.py` | every found read (`_found_body_payload`'s 4 callers) | R1–R3 · 3/3 |
| manifest | `tests/fixtures/tool_manifest.json` | `test_tool_manifest.py` | R4 |
| surface budget | `tests/test_tool_surface_budget.py` | `SURFACE_CAP` | R4 |
| proving test | `tests/test_read_symbol_pattern.py` | — | AC1–AC2 · 2/2 |
| docs | `docs/TOOLS.md`, `CHANGELOG.md` | — | R4, R9.4 |
| bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `test_backlog_bookkeeping.py` | R7.2 |

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1–AC2 | integration (a built index → the tool) | integration: full build + `read_symbol` | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

Rollback: revert the branch. Porting: one repo.

## Phase 3 — execute

Main loop, no `implementer` (`97bf626a`, `6c0e899e`), in a worktree. **Sweep.** Axis 1: the diff is the approved
files; `ruff`, `mypy` clean. Axis 2: the approach implemented-as-approved. AC1's tokens (`estimate_tokens`): pattern
answer 255, whole body 2,259.

The new tests on the base (only the test file added):

Ran at 89ecb16d (pre-change)
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_read_symbol_pattern.py
13 failed in 1.15s
```

Ran at 6c0e899e
```
$ PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_read_symbol_pattern.py <the baseline's suites>
268 passed in 33.35s
```
