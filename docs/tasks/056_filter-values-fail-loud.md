---
id: 056
slug: filter-values-fail-loud
title: An unknown filter value returns an empty result instead of an error
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [014, 033]
---

## Goal
`search_symbol(query=…, kind="class")` returns `total_count: 0, reason: "no_matches"`. The class
exists. The stored kind is `"Class"` — `contract.NODE_KINDS` is capitalised — and `store.py`'s search
clause compares with `nodes.kind = ?` (`_fts_search_clause` → `_narrow(…, "nodes.kind = ?")`), an exact,
case-sensitive match. A value that can never match any row produces the same payload as a query that
genuinely found nothing.

Two things make this worse than a typo trap:

- **The vocabulary is not discoverable.** `kind` is typed `str | None` in the tool signature, so the
  published MCP schema offers no enum. The only way to learn the accepted spellings is to run the query
  *without* the filter and read the casing off the results — the filter is discoverable only by not
  using it.
- **It violates R5.3.** An unknown filter value is a caller error, and the rule is to fail loud rather
  than degrade quietly. `find_callers` already does exactly this for its own selectors: a bad `arg_is`,
  a zero `arg_position`, or one half of the pair raises ([049](049_call-site-argument-selectivity.md)).
  The two tools disagree about the same class of mistake.

Observed in field retro round 2 §3d — one of three ways that session received an empty result that read
as proof of absence. It cost one wasted call; the other two cost more
([054](054_bare-name-callers-silent-drop.md)).

## Scope / Deliverables
- **Reject an unknown `kind`** with a message naming the accepted values (R5.3), rather than returning
  zero rows. `find_callers`'s selector validation is the shape to copy.
- **Publish the vocabulary in the schema.** Type the parameter so the MCP client sees the allowed
  values, as `detail_level` already does with a `Literal`. `contract.NODE_KINDS` is the single source of
  truth (R3) — the tool must not restate the list.
- **Sweep the other filters for the same defect.** `namespace` on `search_symbol`, and any other
  free-string narrowing parameter: decide per parameter whether an unmatchable value is an error or a
  legitimate empty, and write down which and why. `namespace` is plausibly the latter — it is
  matched case-insensitively today — so this is a survey, not a blanket change.
- **Decide the case policy explicitly.** Either accept `"class"` and normalise, or reject it and say so.
  Do not do both, and do not leave it implicit. Recommendation: reject, because normalising invents a
  second spelling of a frozen vocabulary (R3) for the sake of one typo.

## Constraints
- **No contract change (R3).** `NODE_KINDS` is already the vocabulary; this exposes it, it does not
  extend it.
- **No language branch in the core (R1.1).**
- **Backward-compatible for correct callers** — a request that works today must be unchanged.
- **Cost stays at zero on the hot path**: validation is a set membership test before any SQL.

## Acceptance criteria
- `search_symbol(kind="class")` raises, and the message names the accepted values.
- `search_symbol(kind="Class")` is unchanged.
- The published input schema enumerates the accepted kinds, asserted through a `list_tools` call in the
  same style as `test_the_guard_leaves_the_published_input_schema_alone`.
- The kind list in the schema derives from `contract.NODE_KINDS`, asserted — a hand-copied list cannot
  drift.
- The filter survey is recorded in the Outcome, with a decision per parameter.
- `pytest`, `ruff`, `mypy` green.

## References
`code_atlas/tools/search_symbol.py` (the `kind: str | None` parameter, and the `detail_level` `Literal`
that shows the shape to follow); `code_atlas/store.py` `_fts_search_clause` / `_narrow`
(`nodes.kind = ?`), `_search_short`; `code_atlas/contract.py:22` (`NODE_KINDS`).
`code_atlas/tools/find_callers.py` `_args_at` — the existing loud-rejection precedent (049).
Rule: R5.3 (fail loud on caller/config errors), R3 (frozen vocabulary).
Origin: field retro round 2 §3d, mode 3.

## Outcome

**Shipped:** `search_symbol` rejects unknown `kind` with `ValueError` naming `NODE_KINDS` (exact
match; no case-fold). Published MCP `kind` enum is `list(NODE_KINDS)` via
`Annotated`/`Field(json_schema_extra=…)`. Proving tests in `tests/test_filter_values_fail_loud.py`.

### Filter survey (R3)

| Parameter | Decision | Why |
|-----------|----------|-----|
| `search_symbol.kind` | **error** | Frozen vocabulary; unknown spelling is a caller error (R5.3) — this ticket |
| `search_symbol.namespace` | **legitimate empty** | Open prefix domain; case-insensitive match (`store._with_namespace`); unmatched prefix is a real miss |
| `find_callers.arg_is` | **already error** (049) | Loud `ValueError` today; schema still free `str` (discoverability gap, not silent-empty) |
| `include_graph.direction` | **already OK** | `Literal` + runtime check |

Open search keys (`query`, `qname`, `path`, …) are out of survey — unmatched values are legitimate empties.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 056 — filter-values-fail-loud (working doc)

- **Ticket:** 056 · local `docs/tasks/056_filter-values-fail-loud.md`
- **Type:** bug
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N UI paths
- **TIER:** full
- **BASELINE:** green — `906 passed` (2026-08-08, untouched main)
- **work_doc_mode:** embed
- **working-doc path:** this file below separator

## Phase 0 — Refine

`REFINE: 1 unresolved surfaced | 0 want asked (standing→ASSUMED) | 3 how-decision resolved+cited | 1 ASSUMED | skip: no`

**INPUT KIND:** ticket

**Settled wants:** _(none yet — W1 ASSUMED pending Gate-1 confirm)_

**Resolved direction + citation (how-decision):**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| H1 | Unknown `kind` handling | Loud `ValueError` naming accepted values (find_callers `_args_at` shape) | ticket Scope L34–35; R5.3; `find_callers.py:151-152` |
| H2 | Schema vocabulary | `Literal` / enum from `contract.NODE_KINDS`, not a hand-copied list | ticket Scope L36–38; R3.2; `detail_level` precedent `search_symbol.py:23` |
| H3 | Filter survey | Per-parameter decide error vs legitimate empty; not blanket reject | ticket Scope L39–42 |

**ASSUMED (awaiting ratification):**

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses prior? |
|---|---------------|-------------|--------------------------|-----------------|
| W1 | Reject `"class"` (exact match to `NODE_KINDS`); do **not** normalise | Ticket recommendation + standing "do the best option"; R3 frozen vocabulary | **Gate 1** | no |

**Constraints from scan:** R1.1 no language branch; R3 no contract bump; R5.3 fail loud; hot-path validation = set membership before SQL; `None` = no filter (unchanged).

**Exposure-checker:** [Challenger](b36f0359-e2db-4c61-99ab-08b57deccf60) — no additional product-decisions.

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope/Deliverables, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=4 R=4 G=2 AC=6`

| ID | Source | Verbatim (abbrev) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 | Status |
|----|--------|-------------------|----------------|--------------|-----|-------|--------|
| G1 | Goal | Unknown kind → empty/`no_matches` same as true miss | Caller error must not read as proof of absence | `search_symbol.py:31,79`; store `kind = ?` | | | ✅ |
| G2 | Goal | Vocabulary not discoverable (`kind: str \| None`) | MCP schema must expose accepted kinds | `search_symbol.py:31`; vs `DetailLevel` Literal | | | ✅ |
| R1 | Scope | Reject unknown `kind` with message naming accepted values | Raise before SQL; message embeds `NODE_KINDS` | ticket L34–35; `_args_at` precedent | | | ✅ |
| R2 | Scope | Publish vocabulary in schema from `NODE_KINDS` | Parameter typed so `list_tools` shows enum; derive from contract | ticket L36–38; R3 | | | ✅ |
| R3 | Scope | Sweep other free-string narrowing filters | Per-param decision recorded in Outcome | inventory below | | | ✅ |
| R4 | Scope | Decide case policy explicitly | Reject lowercase (W1 ASSUMED) XOR normalise — not both | ticket L43–45 | | | ✅ |
| C1 | Constraints | No contract change | Do not edit `NODE_KINDS` / bump `contract_version` | R3.1 | | | ✅ |
| C2 | Constraints | No language branch in core | No `if language ==` under `code_atlas/` | R1.1 | | | ✅ |
| C3 | Constraints | Backward-compatible for correct callers | `kind="Class"` / `kind=None` unchanged | ticket L51 | | | ✅ |
| C4 | Constraints | Cost zero on hot path | Set membership before any SQL | ticket L52 | | | ✅ |
| AC1 | AC | `kind="class"` raises; message names accepted values | Falsifiable: pytest `pytest.raises(ValueError)` + substring | ticket L55 | | | ✅ |
| AC2 | AC | `kind="Class"` unchanged | Falsifiable: same payload shape as today | ticket L56 | | | ✅ |
| AC3 | AC | Published schema enumerates kinds via `list_tools` | Falsifiable: assert enum/anyOf in inputSchema | ticket L57–58; style of `test_the_guard_leaves_the_published_input_schema_alone` | | | ✅ |
| AC4 | AC | Schema kind list derives from `NODE_KINDS` | Falsifiable: assert schema values == `list(NODE_KINDS)` (not a literal copy in test of a second list) | ticket L59–60 | | | ✅ |
| AC5 | AC | Filter survey in Outcome | Manual-check exclusion: human reads Outcome table | ticket L61 | | | ✅ |
| AC6 | AC | pytest, ruff, mypy green | Falsifiable commands | ticket L62 | | | ✅ |

### AC validation

| AC | Stated | Computed / falsifiable form | Match? |
|----|--------|------------------------------|--------|
| AC1 | raises + names values | `ValueError` whose `str` includes every `NODE_KINDS` entry (or joined list) | ✅ |
| AC2 | Class unchanged | no raise; results for real Class hits still returned | ✅ |
| AC3 | list_tools enum | `inputSchema.properties.kind` has enum/const list | ✅ |
| AC4 | from NODE_KINDS | `set(schema_enum) == set(NODE_KINDS)` | ✅ |
| AC5 | survey recorded | Outcome section present (manual) | ✅ exclusion |
| AC6 | green suite | commands exit 0 | ✅ |

### Universal inventory — free-string / vocabulary filters to survey (R3)

`INVENTORY N=4` (narrowing filters that are not open search keys like `query`/`qname`/`path`):

| # | Parameter | Current behaviour | Tentative decision (design confirms) |
|---|-----------|-------------------|--------------------------------------|
| F1 | `search_symbol.kind` | exact `kind = ?`; unknown → empty | **error** (this ticket) |
| F2 | `search_symbol.namespace` | case-insensitive prefix (`store.py` `_with_namespace`) | **legitimate empty** |
| F3 | `find_callers.arg_is` | already `ValueError` if unknown (049) | **already error**; schema still `str` (discoverability note, not silent-empty) |
| F4 | `include_graph.direction` | already `Literal` + runtime check | **already OK** |

Open search keys (`query`, `qname`, `path`, …) are **out of survey** — unmatched values are legitimate empties by nature.

`CLARIFICATION: 1 raised | 1 self-resolved as ASSUMED W1 (ticket rec + standing) | j=0` (confirm W1 at Gate 1, not Gate 0)

## Cause / gap

- **Cause taxonomy:** validation — caller-supplied enum treated as data filter instead of programmer error.
- **Root:** `search_symbol.py:31` types `kind: str | None`; store compares exact (`_narrow` → `nodes.kind = ?`); no membership check before SQL.
- **Gap:** MCP schema hides vocabulary; R5.3 violated vs `find_callers` selectors.

## Blast radius

- Entry: `code_atlas/tools/search_symbol.py`
- Dependents: MCP registration (`main.py` / FastMCP wraps `create`); tests for search + MCP schema
- Likely touch: `search_symbol.py`, new/extended tests; Outcome in task/BACKLOG; optional tiny helper if Literal built from `NODE_KINDS`
- No store/SQL change required if validation is tool-side; no adapter; no schema_version bump

`RULE SECTIONS: R1 (N/A — no language branch) | R3 ✅ (expose NODE_KINDS, no bump) | R5.3 ✅ | R6.1 ✅ tool tests | DB/a11y N/A`

`TRACK: backend — 0/N touched files under UI paths`

`SCOPE: M` · `TIER: full` (SCOPE≠S; survey N=4)

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker challenger | 1 | unmeasured (blocking retrieval) |

## Session status

- **Phase:** analysis complete → **Gate 1**
- Waiting: ratify ASSUMED W1 (reject lowercase) + approve matrix / proceed to design


## Decision log

| When | Decision | Gate |
|------|----------|------|
| 2026-08-08 | Standing: suggest best + pass all process gates; outward (push/PR) still need per-action OK | solve |
| 2026-08-08 | Gate 1 cleared; W1 ratified — reject lowercase, no normalise | Gate 1 |
| 2026-08-08 | Gate 2 cleared (standing) — approach below | Gate 2 |

## Phase 2 — Design

**Approach**
1. Before SQL in `search_symbol`, reject `kind is not None and kind not in NODE_KINDS` with `ValueError` shaped like `_args_at` (`unknown kind {k!r}: one of {', '.join(NODE_KINDS)}`).
2. Publish schema via `Annotated[str | None, Field(json_schema_extra={"enum": list(NODE_KINDS)})]` — enum list is `list(NODE_KINDS)`, not a second hand-copied vocabulary (spike verified FastMCP `list_tools` shows enum; pydantic does not pre-validate so our ValueError owns the message).
3. Record filter survey Outcome (F1–F4) in task Outcome + working doc; no code for F2–F4 beyond the survey text.
4. Case policy: exact membership only (W1).

**Rejected alternatives**
- `Literal[*NODE_KINDS]` — runtime OK, **mypy `valid-type` fail**; would force contract invert.
- Invert `contract.py` so `NODE_KINDS = get_args(NodeKind)` — cleaner typing but is a contract-module restructure; C1 says no contract change / expose-only.
- Case-fold `"class"` → `"Class"` — rejected by ratified W1 / R3 second spelling.

**Assumptions**
| Assumption | Tag |
|------------|-----|
| FastMCP publishes `json_schema_extra` enum on optional str | **verified** (spike 2026-08-08) |
| pydantic does not reject unknown enum before tool body when using json_schema_extra only | **verified** (spike) |
| Direct `create()` call raises same ValueError (not only MCP path) | novel-untested → proving test AC1 |

**Change list**

| # | Change | Path | Ph2 rows | k/N |
|---|--------|------|----------|-----|
| 1 | KindArg Annotated + `_require_kind` / inline check before SQL | `code_atlas/tools/search_symbol.py` | R1,R2,R4,C3,C4,G1,G2,AC1,AC2 | 9/9 |
| 2 | Proving + schema + Class-ok tests | `tests/test_filter_values_fail_loud.py` (new) | AC1–AC4,AC6 | 5/5 |
| 3 | Filter survey Outcome (F1–F4) | `docs/tasks/056_…` Outcome + BACKLOG/frontmatter done | R3,AC5 | 2/2 |
| 4 | Optional: extend published-schema assertion style near existing MCP test if needed | same new test file uses `list_tools` | AC3,AC4 | — |

**Proof collateral:** `tests/test_search_read_outline.py` kind/namespace tests unchanged for valid callers; `test_the_guard_leaves_the_published_input_schema_alone` may need `kind` in properties ≥ set — fold assert into new test rather than widening that guard test unless it breaks.

**Rule compliance:** R3 expose NODE_KINDS ✅ · R5.3 loud ✅ · R1.1 N/A · R6.1 tool tests ✅

**Verification plan**

| AC | risk layer | proof | match |
|----|------------|-------|-------|
| AC1 | logic | unit `pytest.raises` on `create()(…, kind="class")` | ✅ |
| AC2 | integration | unit/integration call `kind="Class"` on planted Class | ✅ |
| AC3 | integration | `list_tools` inputSchema enum | ✅ |
| AC4 | logic | `schema enum == list(NODE_KINDS)` | ✅ |
| AC5 | manual | Outcome table | ✅ exclusion |
| AC6 | integration | pytest/ruff/mypy | ✅ |

**Proving test:** `tests/test_filter_values_fail_loud.py::test_unknown_kind_raises_naming_accepted_values`  
Invoke: `pytest tests/test_filter_values_fail_loud.py -q`

**Rollback:** revert branch. **Porting:** app only.

**SCOPE:** M (unchanged)


## Phase 3 — Execute

- **Branch:** `fix/056-filter-values-fail-loud`
- **Implemented:** KindArg + `_require_kind`; proving/schema tests; Outcome filter survey; BACKLOG in_progress
- **Sweep axis 1:** diff ⊆ change list ✅ (`search_symbol.py`, new test file, task Outcome, BACKLOG)
- **Sweep axis 2:** approach bullets implemented-as-approved ✅ (no deviation)
- **Proving test:** `test_unknown_kind_raises_naming_accepted_values` — green
- **Suite:** pending full run at commit

## Session status

- **Phase:** execute → review
- Gates 1–2 cleared (standing)


## Phase 4 — Review

- **Reviewed at** `5b69d6c0b253661f901ae8099a123ba74dc95d2b`
- **Reviewed files:** `code_atlas/tools/search_symbol.py`, `tests/test_filter_values_fail_loud.py`, `docs/tasks/056_filter-values-fail-loud.md`, `docs/BACKLOG.md`
- **Reviewer:** [Reviewer](ff65b089-379c-4cbe-bb01-1cf868be7703) — **LGTM**
- **Challenger:** [Challenger](2f35a89d-5fad-4a6a-a970-c34cdf188a9b) — 14 met · 0 not met · 0 can't tell
- **Gate 4:** clean (standing — no stop)

## Cost ledger (dispatch)

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker challenger | 1 | unmeasured (blocking retrieval) |
| review | reviewer | 1 | unmeasured (blocking retrieval) |
| review | challenger | 1 | unmeasured (blocking retrieval) |

`LEDGER: 3 rows / 3 dispatches` — complete

## Durable lesson

`Literal[*NODE_KINDS]` fails mypy (`valid-type`) even when the tuple is inferred literals; publishing a contract-derived enum without a contract restructure needs `Annotated` + `Field(json_schema_extra={"enum": list(NODE_KINDS)})` (schema-only) plus an explicit `ValueError` for the R5.3 message.

## Session status

- **Phase:** finalise — waiting per-action approval for push / PR
- **Reviewed at** `5b69d6c` (stale-guard baseline)

