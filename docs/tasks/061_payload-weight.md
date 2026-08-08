---
id: 061
slug: payload-weight
title: Every response carries fields that earn nothing — `db_path`, a fixed suggestion list, duplicate File rows
phase: 1.5b
milestone: Cost
status: done
depends_on: [010, 014, 033]
---

## Goal
Four payload costs found in field retro round 2, none of them large alone:

- **`db_path` rides on every nav and search response** at `detail_level="standard"`, which is the
  default (`nav_result.py` — `result["db_path"] = db_path` in both `empty_nav` and `nav_result`, and
  the same in `list_result`). It is an absolute filesystem path. Useful once, on `get_index_status`; on
  a `find_callers` result it is repeated overhead, and it is a routine leak for anyone pasting a
  response into an issue — it cost the round-2 session redaction work.
- **`next_tool_suggestions` returns every servable tool on every `get_index_status` call.** `_suggestions`
  appends all nav tools whenever there is an index, so the "suggestion" is the tool list, in a fixed
  order, on every call. It reacts to exactly one thing (adding `build_or_update_index` when staleness is
  not `current`).
- **`search_symbol` spends rows on `File` nodes pointing at classes already listed in the same
  response** — 2 of 10 rows in the session's call, a fifth of a hard-capped budget restating what the
  response already said.
- **`subject_refreshed_only: true`** appears on nav responses with no explanation in any tool
  description. The session could not tell whether it was informational or a warning that the answer was
  degraded, and ignored it. A field nobody can act on is either documentation debt or dead weight.

**This is deliberately the lowest tier.** The same retro measured code-atlas's total direct token cost
at roughly **2k out of a 250–300k-token session — under 1%**. Payload size is not where the leverage is,
and this ticket must not be worked before [054](054_bare-name-callers-silent-drop.md),
[055](055_recall-benchmark.md), [056](056_filter-values-fail-loud.md), [057](057_answer-pagination.md).
It is recorded so the observations are not lost, not because it is urgent.

## Scope / Deliverables
- **`db_path` off the per-response path.** Keep it on `get_index_status`, where a caller needs it once;
  drop it from nav and search payloads, or demote it to a detail level nobody uses by default.
- **`next_tool_suggestions`: make it react, or remove it.** Either it responds to the index's state
  (suggest a build when `dirty_indexed_files > 0`, drop tools that cannot help) or it is the tool list
  and the client already has that. Do not keep a field that is constant.
- **`search_symbol` result mix.** A `File` row whose path is the declaring file of a `Class` row in the
  same response is redundant. Decide: suppress it, rank it below, or leave it and document why. The
  `kind` filter would let a caller avoid it — but only once [056](056_filter-values-fail-loud.md) makes
  the vocabulary discoverable, so sequence accordingly.
- **`subject_refreshed_only`: explain it in the tool description or remove it.** Find out what it is
  meant to tell a caller and whether any caller can act on it.

## Constraints
- **No information may be lost quietly.** Anything removed must be obtainable another way, and the
  runbook must say where — this ticket is about weight, and dropping a field an operator relied on
  would trade a token problem for a debugging one.
- **`get_index_status` stays cheap** (both retros' answer to "what must not break") and stays the one
  place that reports `db_path`.
- **Determinism (R4.2)**; no contract or schema change (R3); no language branch in the core (R1.1).
- **Measure before and after.** A payload-size ticket that ships without a byte or token count has not
  demonstrated anything.

## Acceptance criteria
- A nav response at default arguments no longer carries `db_path`; `get_index_status` still does, both
  asserted.
- `next_tool_suggestions` either varies with index state — asserted across at least two states — or is
  gone.
- The `search_symbol` File/Class overlap decision is implemented and asserted, or documented with its
  reason.
- `subject_refreshed_only` is described where a caller will see it, or removed.
- Before/after payload sizes recorded in the Outcome for one representative call per tool.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/tools/nav_result.py` (`empty_nav`, `nav_result`, `list_result` — the three places
`db_path` is attached); `code_atlas/tools/get_index_status.py` `_suggestions`;
`code_atlas/tools/search_symbol.py` (result mix); `code_atlas/tools/find_implementations.py` and
`find_references.py` (`subject_refreshed_only=True`).
Relative-cost evidence: field retro round 2 §9 (code-atlas under 1% of session tokens) and §3e / §5.
Origin: field retro round 2 §3e and §5.

## Outcome

- **`db_path`:** dropped from nav/search/read/outline/reach/explain payloads; kept on
  `get_index_status` (and build reports). Alternate source: call status once.
- **`next_tool_suggestions`:** reactive — `[build_or_update_index]` when not indexed or not
  `current`; `[]` when current (asserted across both states).
- **`search_symbol`:** suppress `File` hits whose path matches a `Class` hit in the same page.
- **`subject_refreshed_only`:** emitted only when read-through reparsed the subject this call;
  documented on `find_callers` / `find_references` / `find_implementations` docstrings.
- **Sizes (fixture, compact JSON `separators=(",", ":")`):**
  - `get_index_status` (`standard`, current index): **680→508 B** (−172; before = prior full
    nav-tool suggestion list when current).
  - `find_callers` (default/`standard`, missing qname): **199→153 B** (−46; before includes
    synthetic prior `db_path`).
  - `search_symbol` (`standard`, empty-ish query): **131→85 B** (−46; before includes synthetic
    prior `db_path`).
- **Suite:** **956 passed**.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 061 — payload-weight (working doc)

- **Ticket:** 061 · local `docs/tasks/061_payload-weight.md`
- **SCOPE:** M · **TIER:** full · **TRACK:** backend
- **BASELINE:** green — tip `198f28a` / 949+ before change
- **work_doc_mode:** embed

## Phase 0 — Refine

`REFINE: 0 unresolved | skip: yes`

`refine skipped: 0 unresolved product-decisions`

**Exposure-checker:** [Challenger](dbbeb1f0-9832-4a1a-9216-82b972cff604) — none (ready). 054–057 done.

## Requirements matrix

`SECTIONS: 4 | ROWS: C=4 R=4 G=1 AC=6` — all ✅ after execute (see Outcome).

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker | 1 | unmeasured (blocking retrieval) |
| review | reviewer | 1 | unmeasured (blocking retrieval) |
| review | challenger | 1 | unmeasured (blocking retrieval) |
| review | reviewer | 2 | unmeasured (blocking retrieval) |
| review | challenger | 2 | unmeasured (blocking retrieval) |

## Decision log

| When | Decision |
|------|----------|
| 2026-08-08 | Standing: best option + pass all gates |
| 2026-08-08 | HOW: drop db_path from nav; reactive suggestions; suppress File∩Class; subject_refreshed_only only when repaired |
| 2026-08-08 | Review round 2 LGTM + challenger PASS at `dafc22e` |

## Session status

- **Phase:** finalise
- **Reviewed at:** `dafc22e6924b559cdc851ed10052c85803aa57ee`
- **Reviewed files:** tools/* (nav/search/status/find_*/read/outline/reach/explain), tests/test_payload_weight.py, test_mcp_server.py, CONVENTION, README, PLAN, runbook, LESSONS, BACKLOG, task 061
