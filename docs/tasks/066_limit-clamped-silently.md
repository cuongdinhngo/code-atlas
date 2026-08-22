---
id: 066
slug: limit-clamped-silently
title: '`limit: 30` returns 10 rows and nothing in the payload says it was clamped'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [057, 033]
---

## Goal
Every paging tool computes `cap = config.max_results if limit is None else min(limit, config.max_results)`.
A caller who asks for 30 and gets 10 receives **no field saying the request was reduced**. Make the
clamp visible in the answer.

## Evidence (field retro round 3, 2026-08-09)
- The session passed `limit: 30` to `find_callers` **twice** and got exactly **10** rows both times.
  Nothing in either payload named `max_results`, the clamp, or the requested value.
- `truncated: true` and `total_count: 23` were both present and correct — so the caller could tell
  *more exist*, but not *why this page stopped at 10 when 30 were asked for*. Those are different
  questions: the first is about the result set, the second is about whether the tool honoured the call.
- The anchor repo's `CLAUDE.md` already carries a hand-written warning — *"`max_results` is 10, so
  read `total_count` for the real number"*. **A previous reader was burned by this and patched it in
  prose, in a file the server does not control.** That is the signal worth acting on: the server is
  exporting a caveat into every consumer's documentation.
- The same expression appears in `find_references`, `find_callers`, `find_view_data`,
  `search_symbol`, `file_outline` and friends; `include_graph` and `impact` do not take `limit`
  at all and simply use `config.max_results`.
- Round 3 also recorded that `max_results` does double duty on the anchor repo — it caps returned
  rows **and** the resolver's candidate fan-out — and that the session learned this only from a
  comment in the repo's own config file, not from the server.

## Scope / Deliverables
- **Report the clamp where it happens.** When `limit > config.max_results`, the payload says so —
  the requested value, the effective value, or a boolean; pick one and use it everywhere. One field,
  present only when a clamp actually occurred (061 weight discipline).
- **Decide clamp vs error, and record why.** Silently reducing is one option; rejecting a
  `limit` above the ceiling with a loud error (R5.3, as [056](056_filter-values-fail-loud.md) did for
  unknown filter values) is the other. The ticket must choose deliberately and write the reason down,
  because "accept the argument and ignore it" is the one option field evidence rules out.
- **Every tool that takes `limit`, uniformly.** A caveat that holds for five tools and not the sixth
  is worse than none.
- **State the ceiling where the caller can read it.** `get_index_status` (or the tool description)
  should carry the effective `max_results`, so a caller can size requests without reading the
  server's config file. Include which meanings the knob governs — rows returned, and resolver
  candidate fan-out — since a caller who thinks it only trims output will mis-read `total_count`.

## Constraints
- R4 — behaviour is deterministic; the clamp must not become host- or timing-dependent.
- 061 — no field on payloads where nothing was clamped.
- 057 — paging semantics (`offset`, `truncated`, `total_count`) stay exactly as they are; this ticket
  adds a signal, it does not change what a page contains.
- Do not raise `max_results` as the fix. The cap exists for measured reasons on the anchor repo
  (at 50 the graph carries 4.8M heuristic edges / 2.1 GB; at 10, 2.6M).

## Acceptance criteria
- A call with `limit` above the ceiling produces a payload from which the caller can tell, without
  reading server config, that the request was reduced — or a loud error, if that is the option chosen.
- A call with `limit` at or below the ceiling is byte-identical to today's payload.
- All tools accepting `limit` behave the same way; a test enumerates them so a new tool cannot
  silently opt out.
- The effective `max_results` is discoverable from the server, and its double duty is stated there.

## References
Field retro round 3 §4 ("`limit` is silently clamped"), §8 (the clamp named as half of the one
question where the graph was a net loss). `code_atlas/tools/find_callers.py`,
`find_references.py`, `find_view_data.py` (the shared `min(limit, config.max_results)` expression);
`code_atlas/config.py` (`max_results`). Related: [057](057_answer-pagination.md) (paging and
`total_count` auditing), [056](056_filter-values-fail-loud.md) (the fail-loud precedent for an
argument the server will not honour), [061](061_payload-weight.md) (why this is one conditional field).


<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 066 — `limit` clamped silently (working doc)

- **Ticket:** 066 · docs/tasks/066_limit-clamped-silently.md
- **Type:** enhancement (payload honesty — clamp visibility)
- **Repo(s) / Porting:** app (`.`) — core only; no adapter change
- **SCOPE:** M
- **STRUCTURE:** native  <!-- Goal→G, Scope/Deliverables→R, Acceptance criteria→AC, Constraints→C -->
- **TRACK:** backend — all changes under `code_atlas/` (Python core), no UI
- **TIER:** full
- **BASELINE:** red (platform-only)
  <!-- baseline exclusions (pre-existing, outside this change, this Windows dev box):
       (1) `import fcntl` (Unix-only) in code_atlas/index_lock.py breaks every test importing main.py
           (e.g. test_search_read_outline.py — where search_symbol/file_outline are tested);
       (2) PHP-adapter subprocess tests need the adapter.
       Delta-relevant suites GREEN: tests/test_store.py + tests/contract + nav = 158 passed / 13 skipped.
       DoD = delta-green; CI (Linux) runs the full suite. -->

---

## Requirements matrix

`SECTIONS: 6 found (Goal, Evidence, Scope/Deliverables, Constraints, Acceptance criteria, References) | 6 decomposed (Evidence + References = context, 0 rows) | ROWS: C=4, R=4, G=1, AC=4`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "A caller who asks for 30 and gets 10 receives no field saying the request was reduced. Make the clamp visible in the answer." | Every clamping tool surfaces that a `limit` was reduced. | shared expr at `find_callers.py:93` etc. | chg 3–7 | `test_clamp_reported_uniformly_across_tools` (5 tools) | ✅ |
| R1 | Scope | "Report the clamp where it happens … the requested value, the effective value, or a boolean; pick one and use it everywhere. One field, present only when a clamp actually occurred (061)." | One conditional field, single representation, uniform across tools. | `nav_result`/`list_result` build all 5 payloads | chg 1, 2 (`clamp_limit` + `attach_limit_capped`) | clamp test + `test_no_field_when_request_is_honoured` | ✅ |
| R2 | Scope | "Decide clamp vs error, and record why … 'accept the argument and ignore it' is the one option field evidence rules out." | Deliberate decision recorded: clamp-with-signal vs fail-loud. | 056 fail-loud precedent; 057 soft paging | decided: clamp-with-signal (Design §Rejected) | recorded | ✅ |
| R3 | Scope | "Every tool that takes `limit`, uniformly. A caveat that holds for five tools and not the sixth is worse than none." | All N=5 limit-taking tools behave identically. | Inventory N=5 below | chg 3–7 + guard chg 9 | `test_no_limit_taking_tool_opts_out_of_the_signal` | ✅ |
| R4 | Scope | "State the ceiling where the caller can read it. `get_index_status` (or the tool description) should carry the effective `max_results` … which meanings the knob governs — rows returned, and resolver candidate fan-out." | Ceiling + its double duty discoverable from the server. | `get_index_status._status` (`get_index_status.py:128,138`) | chg 8 | `test_status_reports_max_results_and_double_duty` | ✅ |
| C1 | Constraint | "R4 — behaviour is deterministic; the clamp must not become host- or timing-dependent." | Clamp signal is a pure function of `limit` + `max_results`. | `cap = min(limit, max_results)` is pure | chg 1 (pure fn) | `test_clamp_limit_helper_is_pure` + clamp test (called twice) | ✅ |
| C2 | Constraint | "061 — no field on payloads where nothing was clamped." | Field omitted when `limit <= max_results` (or `limit is None`). | 061 weight discipline; `attach_try_instead` pattern | chg 2 (omit when not clamped) | `test_no_field_when_request_is_honoured` | ✅ |
| C3 | Constraint | "057 — paging semantics (`offset`, `truncated`, `total_count`) stay exactly as they are; this ticket adds a signal, it does not change what a page contains." | Additive only; page contents/paging unchanged. | `edges_by_target` offset path unchanged | chg 3–8 (additive only) | `test_no_field_when_request_is_honoured` (paging intact) | ✅ |
| C4 | Constraint | "Do not raise `max_results` as the fix. The cap exists for measured reasons on the anchor repo." | The ceiling value is not changed. | `DEFAULT_MAX_RESULTS` untouched (`config.py:130`) | n/a — value not changed | n/a | ✅ |
| AC1 | AC | "A call with `limit` above the ceiling produces a payload from which the caller can tell, without reading server config, that the request was reduced — or a loud error, if that is the option chosen." | Clamp visible at point of use (or error). | — | chg 3–7 | `test_clamp_reported_uniformly_across_tools` | ✅ |
| AC2 | AC | "A call with `limit` at or below the ceiling is byte-identical to today's payload." | No field/behaviour change on the non-clamp path. | — | chg 3–7 (attach gated on clamped) | `test_no_field_when_request_is_honoured` | ✅ |
| AC3 | AC | "All tools accepting `limit` behave the same way; a test enumerates them so a new tool cannot silently opt out." | An enumerating test over the N=5 tools guards uniformity. | — | chg 9 (source-scan opt-out guard) | `test_no_limit_taking_tool_opts_out_of_the_signal` | ✅ |
| AC4 | AC | "The effective `max_results` is discoverable from the server, and its double duty is stated there." | `get_index_status` carries the ceiling + governs list. | — | chg 8 | `test_status_reports_max_results_and_double_duty` | ✅ |

Status legend: ✅ done/proven · ⚠ deferred · ❌ not met · ⬜ pending phase.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | clamp visible without server config (or loud error) | call each tool with `limit > max_results`; assert the clamp field (or the raised error) | Y | Falsifiable (integration test) | — |
| AC2 | `limit ≤ ceiling` byte-identical to today | call with `limit ≤ max_results` and with `limit=None`; assert clamp field absent, payload otherwise unchanged | Y | Falsifiable (test) | — |
| AC3 | all limit-taking tools uniform; enumerating test | a test iterating the N=5 tools (registry/param-introspection) so a new limit-taker must opt in | Y | Falsifiable (enumerating test) | — |
| AC4 | ceiling + double duty discoverable from server | assert `get_index_status` payload carries `max_results` value + `governs` (rows + resolver fan-out) | Y | Falsifiable (test) | — |

No numeric acceptance values to re-derive; no mismatches. All ACs falsifiable → no manual-check exclusions. No uncodified standard applied (R4/061/057 are codified/ticketed).

## Inventory (universal "all/every/no" requirements)

**R3 / AC3 — "every tool that takes `limit`, uniformly."** Counted "do X for each of N" → per-item checklist.
- **Denominator / total N = 5** (tools with a user-facing `limit: int | None` that clamps to `max_results`):

| # | Tool | Clamp site | Ph3/4 proven by | Status |
|---|------|-----------|-----------------|--------|
| 1 | `find_callers` | `find_callers.py:93` | | ⬜ |
| 2 | `find_implementations` | `find_implementations.py:49` | | ⬜ |
| 3 | `find_references` | `find_references.py:63` | | ⬜ |
| 4 | `find_view_data` | `find_view_data.py:48` | | ⬜ |
| 5 | `search_symbol` | `search_symbol.py:63` | | ⬜ |

Out of scope at ship (no user `limit` param → nothing to clamp): `include_graph`
(`include_graph.py:66`). **`file_outline` was out of scope then and is closed by
[123](123_file-outline-total-count-is-the-page-length.md)** — it now takes `limit`, routes through
the clamp helpers, and is in the enumerating test denominator (N=6). **`find_orphans` closed by
[124](124_find-orphans-cannot-answer-at-scale.md)** — same clamp contract (N=7). AC3's enumerating test must be built so that if either later grows a
`limit` param, it is forced into the clamp-signal contract.

## Clarifications

`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`

- Self-resolved:
  1. **Clamp-with-signal vs fail-loud error (R2)?** → Recommend **clamp-with-signal**. 057 established `limit`/`offset` as soft paging knobs; a `limit` above the ceiling is a legitimate "give me as many as you can", not the typo class 056 fails loud on (unknown *filter values* → wrong semantics). The anchor `CLAUDE.md` warning ("read `total_count` for the real number") shows callers want a soft, visible clamp, not rejection. Final lock at Gate 2 under the operator's standing approval. Cited: ticket 37–40, [056], [057].
  2. **Field representation — requested / effective / boolean (R1)?** → Recommend the **effective value** (`limit_capped_to: <cap>`): strictly more informative than a boolean, reveals the ceiling at point of use (helps AC1 "without reading server config"), still one conditional field (061). Design locks the name. Cited: ticket 34–36.
  3. **Which `get_index_status` detail levels carry the ceiling (R4/AC4)?** → `standard` + `verbose` (the `enriched` payload) plus the docstring; `minimal` stays the ~100-tok cheap path. Cited: `get_index_status.py:136,148`.
  4. **`file_outline` named in the ticket but has no user `limit`.** → Out of scope for the clamp signal (it never reduces a request); N=5. Cited: `file_outline.py:36`.

j = 0 → **no Gate 0.**

---

## Phase 1 — Analysis ✋ Gate 1

- **Gap analysis (enhancement).** Current: all five tools share `cap = config.max_results if limit is None else min(limit, config.max_results)` and then silently discard the excess — no payload field records that `limit` was reduced (`find_callers.py:93`, `find_implementations.py:49`, `find_references.py:63`, `find_view_data.py:48`, `search_symbol.py:63`). `truncated`/`total_count` answer "more exist" (about the result set) but not "the tool honoured fewer than you asked" (about the call). The ceiling and its double duty (returned rows **and** resolver candidate fan-out) live only in the server's config, so a burned reader hand-patched a caveat into the anchor repo's `CLAUDE.md`. Target: one conditional field at each clamp site + the ceiling surfaced on `get_index_status`.
- **Handler / entry point + blast radius.** Entry points: the N=5 tools. Shared seam: `code_atlas/tools/nav_result.py` (`nav_result` for find_*, `list_result` for search_symbol) — the natural home for a `clamp_limit()` helper + attach. Ceiling surface: `get_index_status._status`/`_unbuilt` (`get_index_status.py:113,73`). Config: `config.max_results` (`config.py:63,130`) — read-only for this ticket (C4). No store/schema/contract change.
- **Self-audit:** every section decomposed (6/6); AC table complete, all 4 ACs falsifiable, none carrying a bare ✅; BASELINE captured (red, platform-only, exclusions listed, delta suites green); inventory N=5 set as a per-item checklist; matrix Status filled (⬜ pending later phases); STRUCTURE=native, TRACK=backend, TIER=full, SCOPE=M declared; j=0. No frontend → no SURFACES.
- **Gate 1 status:** waiting on user

## Phase 2 — Design ✋ Gate 2

### Approach — clamp-with-signal via one shared helper

**Decision (R2): clamp-with-signal, not fail-loud.** A `limit` above the ceiling is a legitimate "give me as many as you can" (057 made `limit`/`offset` soft paging knobs), not the typo-class 056 rejects (unknown *filter values* → wrong semantics). The anchor `CLAUDE.md` caveat ("read `total_count` for the real number") is evidence callers want a soft, *visible* clamp. Rejecting would break existing callers who pass generous limits expecting a page. "Accept and ignore" is ruled out by the ticket; this is the remaining coherent option.

**Field (R1): one conditional field `limit_capped_to: <cap>`** — the *effective* value. It is strictly more informative than a boolean and reveals the ceiling at point of use, so a caller can tell the request was reduced **without a second call** (AC1). Present only when a clamp actually occurred (061).

**Mechanism (R3, uniformity):**
1. `config.clamp_limit(limit, max_results) -> (cap, clamped)` — the single home for `cap = max_results if limit is None else min(limit, max_results)`; `clamped = limit is not None and limit > max_results`. Pure → deterministic (C1).
2. `nav_result.attach_limit_capped(payload, *, cap, clamped)` — sets `limit_capped_to = cap` iff `clamped` (omit otherwise → C2), mirroring `attach_try_instead`.
3. Each of the N=5 tools swaps its inline expression for `cap, clamped = clamp_limit(...)` (keeping its `cap < 1` guard) and calls `attach_limit_capped` on the results payload. Early error/empty returns (stale, no_such_symbol, missing db) are not result pages → no attach.

**Ceiling surface (R4/AC4):** `get_index_status` `standard`/`verbose` payload gains
`"max_results": {"value": <n>, "governs": ["returned_rows", "resolver_candidate_fanout"]}` (double duty stated in the answer, not just docs; `minimal` stays the ~100-tok cheap path). Verified core-level: `indexer.py:262,303` feed `max_results` to `resolve_edges` as `max_candidates`.

### Rejected alternatives

- **Fail-loud error on `limit > ceiling` (like 056):** breaks legitimate large-page callers and contradicts 057's soft paging; 056's precedent is for arguments the server *cannot honour meaningfully* (typo'd enums), not a scalar it can satisfy up to a bound. Rejected, reason recorded (R2).
- **Boolean `limit_clamped: true`:** satisfies AC1 minimally but forces a second `get_index_status` call to learn the ceiling; the effective value is one field and more useful. Rejected.
- **Raise `max_results`:** explicitly forbidden (C4 — 4.8M vs 2.6M edges at 50 vs 10). Not considered.
- **Inline the signal in each tool (no shared helper):** invites drift across 5 tools and fails AC3's "cannot silently opt out". Rejected for a shared helper + a source-scan guard.

### Assumptions

| Assumption | verified / novel-untested | resolution |
|------------|---------------------------|------------|
| All 5 tools build dict payloads a helper can mutate before return | verified | `nav_result`/`list_result` return `dict` |
| `max_results` double duty (rows + resolver fan-out) is core, not anchor-specific | verified | `indexer.py:262,303` → `resolve_edges(max_candidates=config.max_results)` |
| A source scan for `limit: int | None` uniquely identifies user limit-takers (not the internal `limit: int` helpers) | verified | `find_callers._callers` uses `limit: int`; the 5 tool factories use `limit: int | None` |
| `get_index_status` + the 5 tools import without the `fcntl` chain | verified | import check this phase |
| Adding a payload field is not a frozen-contract change (R3.1) | verified | R3 governs node/edge vocabulary/qname; nav/status payloads are presentation |

No `novel-untested` third-party/runtime assumption → Assumptions check clear.

### Smallest change-list (every item traces to a matrix row)

| # | Change | File/area | Ph2 covered by | k/N |
|---|--------|-----------|----------------|-----|
| 1 | `clamp_limit(limit, max_results) -> (cap, clamped)` | `code_atlas/config.py` | R1, C1, C4 | 3/3 |
| 2 | `attach_limit_capped(payload, *, cap, clamped)` (omit when not clamped) | `code_atlas/tools/nav_result.py` | R1, C2 | 2/2 |
| 3 | Use helpers in `find_callers` | `tools/find_callers.py` | R3(#1), G1, AC1, AC2 | 4/4 |
| 4 | Use helpers in `find_implementations` | `tools/find_implementations.py` | R3(#2), G1, AC1, AC2 | 4/4 |
| 5 | Use helpers in `find_references` | `tools/find_references.py` | R3(#3), G1, AC1, AC2 | 4/4 |
| 6 | Use helpers in `find_view_data` | `tools/find_view_data.py` | R3(#4), G1, AC1, AC2 | 4/4 |
| 7 | Use helpers in `search_symbol` | `tools/search_symbol.py` | R3(#5), G1, AC1, AC2 | 4/4 |
| 8 | `max_results` + `governs` on status; docstring | `tools/get_index_status.py` | R4, AC4 | 2/2 |
| 9 | New tests: behavioural (5 tools), non-clamp absence, source-scan opt-out guard, status field | `tests/test_limit_clamp_visible.py` | G1, R3, AC1, AC2, AC3, AC4, C1, C2, C3 | 9/9 |
| 10 | Docs: PLAN (tool rows + status), BACKLOG (status + token), task frontmatter | `docs/*` | R7.2 | — |

**Test blast-radius (mechanical):** grep the touched tool payloads for existing exact-key assertions that pass `limit > max_results`. Any hit is folded here as *proof collateral*; the non-clamp path is byte-identical, so tests using `limit=None` or `limit ≤ ceiling` are unaffected (e.g. `test_nav_results_flag_truncation` uses `max_results=2` + default limit → no clamp). Some `search_symbol`/`file_outline` assertions live in `test_search_read_outline.py` (fcntl-blocked locally, CI-covered) — the execute grep will confirm and any collateral is recorded.

### Rule compliance

- **R1.1/R2.2:** no language branch, no repo names (pure numeric/limit logic). **R1.4:** `clamp_limit` is limit-policy → `config.py`; payload attach → `nav_result.py`; store/resolver untouched. **R3:** no node/edge vocabulary change → no `contract_version`/`SCHEMA_VERSION` bump. **R4:** `clamp_limit` is pure. **R7.1/R7.5:** additive field, shared helper, comments ≤3 lines. **057/061:** paging unchanged; field only when clamped.

### Verification plan (per-AC, layer-matched)

| AC / req | risk layer | proof artifact | layer-match |
|----------|-----------|----------------|-------------|
| AC1 clamp visible at point of use | integration (tool payload) | parametrized test over 5 tools, `limit=max_results+N` → assert `limit_capped_to == cap` | ✅ |
| AC2 `limit ≤ ceiling` unchanged | integration | `limit=None` and `limit ≤ ceiling` → assert `limit_capped_to` absent, rest unchanged | ✅ |
| AC3 uniform; new tool can't opt out | static/source | source-scan test: every `tools/*.py` with `limit: int | None` references `clamp_limit` + `attach_limit_capped` | ✅ |
| AC4 ceiling + double duty from server | integration | `get_index_status` over a built store → assert `max_results.value` + `governs` | ✅ |
| G1 make clamp visible | integration | same as AC1 | ✅ |
| C1 deterministic | logic | `clamp_limit` pure; repeated-call assertion | ✅ |
| C2 no field when not clamped | integration | AC2 test | ✅ |
| C3 paging semantics unchanged | integration | assert `total_count`/`truncated`/`offset` behaviour intact alongside the clamp | ✅ |
| C4 ceiling value unchanged | static | `DEFAULT_MAX_RESULTS` untouched | ✅ |

No layer-match ❌.

### Proving test

`tests/test_limit_clamp_visible.py::test_clamp_reported_uniformly_across_tools` — parametrized over the 5 tools; seeds enough rows, calls each with `limit = max_results + 5`, asserts `result["limit_capped_to"] == max_results`. **Fails pre-change** (field absent → KeyError), **passes post-change**. Invocation: `python -m pytest tests/test_limit_clamp_visible.py -q`. Integration layer = AC1/G1/R3 risk layer.

### Rollback + porting

Additive; no DDL/schema/contract change. Rollback = revert the branch. Single repo (`app`), core-only; no adapter porting.

### SCOPE confirmed

**M** — unchanged. 5 uniform tool edits + 2 helpers + status + tests; no cross-tier growth, no branch/PR-type drift (`fix`). No *outgrew-its-ticket* nudge.

- **Gate 2 status:** waiting on user

## Phase 3 — Execute

- **Branch:** `fix/066-limit-clamped-silently` (off `main`, which now carries 067 via merged PR #86 — no conflict; the clamp code sits beside 067's `result_subtrees` in `find_callers`/`find_references`).
- **Commits (logical units, no AI trailer):** (1) `clamp_limit` + `attach_limit_capped` helpers; (2) route the 5 tools through them; (3) `max_results` on `get_index_status`; (4) tests; (5) docs.
- **Proving test added:** `tests/test_limit_clamp_visible.py::test_clamp_reported_uniformly_across_tools` (parametrized over the 5 tools) — confirmed **fails pre-change** (symbol/field absent) and **passes post-change**.
- **Verification sweep — BOTH axes.**
  - *File axis:* diff = `config.py`, `tools/nav_result.py`, the 5 tools, `tools/get_index_status.py`, new `tests/test_limit_clamp_visible.py` + docs bookkeeping — **⊆ approved change list ✅**; additive only, **zero untouched-line reformatting ✅**; each hunk maps to a matrix row ✅ (chg1→R1/C1/C4; chg2→R1/C2; chg3–7→R3/G1/AC1/AC2; chg8→R4/AC4; chg9→AC1/AC2/AC3/AC4/C1/C2/C3).
  - *Behaviour axis (design-conformance):* all Gate-2 Approach bullets `implemented-as-approved` (clamp-with-signal; effective-value field `limit_capped_to`; shared `clamp_limit`+`attach_limit_capped`; 5 tools uniform; `max_results`+`governs` on status standard/verbose, minimal cheap). **No deviations.**
- **Results:** new file + delta suites = **200 passed / 13 skipped** (`test_limit_clamp_visible` 21 + store 142/contract + nav). `ruff` clean on all of `code_atlas/`; `mypy` clean on changed files; guardrail gates **4 passed**.
- **Baseline-aware DoD:** delta-green. Failures on this Windows box are the recorded baseline exclusions (`fcntl`; PHP-adapter subprocess) — untouched; CI (Linux) runs the full suite.

## Phase 4 — Review ✋

**Skipped this run per explicit operator instruction ("with skipped review").** No `mango:reviewer`/`mango:challenger` dispatched (Decision log + Cost ledger = 0 dispatch). The execute-phase two-axis sweep is the substitute record; no ticket-blind challenger independence check ran.

## Phase 5 — Finalise ✋ final gate

- **PR draft:** scratchpad `pr-066.md` → opened as [#87](https://github.com/cuongdinhngo/code-atlas/pull/87).
- **Outward actions (operator pre-approved all in the run args):**
  - [x] push branch `fix/066-limit-clamped-silently`
  - [x] open PR #87 via `gh` from `.github/pull_request_template.md`
  - [x] push bookkeeping commit (BACKLOG PR link + durable lesson) on the same branch
  - [ ] tracker comment / transition — not requested this run
- **Stale-review guard:** review skipped by instruction → no `Reviewed at` marker; recorded as an explicit operator waiver, not a silent pass. PR diff vs `main` verified 066-only (`main` is an ancestor; 067's code not re-included).
- **Durable lesson:** `## 066` added to `docs/LESSONS.md` (report a partially-honoured argument at point of use + state a knob's double duty + a source-scan uniformity guard; enumerate limit-takers from code).
- **Revert path:** additive; no schema/contract/version change. `git revert` the five commits or drop the branch.

---

## Cost ledger (descriptive — facts only)

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| — | (no subagent dispatched) | — | — | — |

`LEDGER TOTAL: 0 · top cost driver: n/a (no dispatch)`

---

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-08-10 Gate 1 | Analysis complete; TIER=full, SCOPE=M, TRACK=backend, j=0 | Native structured ticket; uniform clamp signal across N=5 tools |
| 2026-08-10 (operator directive) | Review phase (Gate 4) to be **skipped** this run per explicit operator instruction "with skipped review"; all gates pre-approved | Operator standing approval in the run args |

## Session status

- **Last updated:** 2026-08-10 (Phase 3 complete; review skipped per instruction)
- **Current phase:** Phase 5 — Finalise, at the final gate
- **Next action:** Commit the logical units, then (per operator approval) push branch + open PR from the template.
- **Blocked on:** nothing — operator pre-approved the outward actions
