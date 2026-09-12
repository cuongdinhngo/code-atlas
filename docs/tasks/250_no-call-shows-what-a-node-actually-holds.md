---
id: 250
slug: no-call-shows-what-a-node-actually-holds
title: 'No call shows what a node actually holds, so "the adapter never captured this" and "a tool declines to return it" are indistinguishable from the outside — and a consuming agent guessed wrong in the optimistic direction'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [247, 231, 244]
---

## Why this exists (field retro — the anchor repo, 2026-09-11, round 17, verification pass)

Round 17's retro asserted that column types were *"sitting right there in the index, with no way to
get them out"*, and ranked opening that door as its top ask. The assertion was wrong — the adapter
never captures them ([247](247_the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key.md))
— and the interesting part is **why a careful agent got it wrong**.

It was asked to re-run the question under a constraint: answer using code-atlas tools only, then
separate, per missing fact, *(i) the index holds it but no tool returns it* from *(ii) the index never
captured it*, and state the evidence for the choice. Its answer on column data type:

> **Not distinguishable.** `read_symbol` on a stored procedure returns `params` with full types —
> `{"name": "@bondAmount", "type": "money"}` — so the SQL adapter does parse T-SQL type syntax; it is
> not type-blind. But that only proves types are captured for callable parameters. `read_symbol`'s
> contract says `minimal`, and every non-callable kind, omit both, so a Column never carries a type
> field. That is a surface rule; it says nothing about whether the node stores one. **I have no call
> that shows me a Column node's raw contents, so I have no evidence to choose.**

It then retracted its own headline claim. The retraction is the finding: **the evidence needed to
avoid the error does not exist on the surface at any price.** The agent reasoned correctly from
everything it could see and still had to guess, and the direction it guessed — toward the index being
richer than it is — is the one that wastes a maintainer's round.

The same undecidability hit every other fact it was asked about, each with a different false signal:

| Fact | What the agent had | Why it could not conclude |
|---|---|---|
| Column data type | `declared_types: true` on the `sql` stamp | The flag is true of callable `params`; the agent had first read it as covering columns |
| `NOT NULL`, `IDENTITY` | `modifiers: false` on `sql`, `true` on php/ts | Whether SQL nullability *is* a "modifier" is nowhere defined — php's `modifiers` means `public`/`static`. Called "a strong hint, not evidence" |
| Primary key | `search_symbol`'s `kind` enum offers `Table`/`Column`/`ForeignKey`, no `PrimaryKey`; `ForeignKey` returns 1,093 real nodes | Correctly inferred constraints are modellable in principle and PK simply has no kind — the one case it got right, and only from an enum |

Note what carried the two near-misses: a **capability flag** and an **argument enum**. Neither is a
statement about node contents; both were pressed into service because nothing else was available.

## Root cause

Every read path projects. `search_symbol`'s `_hit` returns `{qname, kind, file, line}` (plus 239's FK
target for a `Column`); `read_symbol` returns a source slice and, since 242, `params` on callable
kinds only; `file_outline` returns positions. `extra` — the free-form seam every adapter uses for the
facts that do not fit `NODE_FIELDS`, and where 236 put the FK's child and referenced tables — is
written by adapters, read by `store.py` and several tools, and **exposed by none of them**.

The capability stamps (231/244) were built to answer "what does this index hold", and they do it at
the granularity of *language × named flag*. That granularity cannot answer a question about one kind
(`does a Column carry a type?`), and it has no negative form: a fact with no flag is silent, which
R5.6 correctly forbids reading as a zero — leaving the agent with exactly the "can't tell" it
reported, and no route out of it.

## Scope

A way for a caller to see what a node actually holds, so "not captured" is checkable rather than
inferrable.

Two candidate shapes, to be decided in phase 2 — the ticket does not bind one:

- **A raw-fields view on an existing tool.** `read_symbol` at a new detail level, or a flag, returning
  the node's stored `NODE_FIELDS` and `extra` keys verbatim for one qname. Cheapest, keeps the surface
  at 24 tools, and is the natural home — the agent already reached for `read_symbol` and got a source
  slice.
- **Per-kind capability reporting.** Extend the 231/244 stamp from *language × flag* to name which
  fields each kind actually carries in **this** index, derived from the index rather than declared by
  the adapter. Answers the question without a new read path, and is the honest generalisation of what
  the stamp already claims to be.

The first is the working assumption; the second may subsume it.

## Constraints

- **R5.6 — derive it, do not declare it.** A per-kind report that an adapter *announces* repeats the
  231 failure one level down: the adapter would be asserting what it believes it emits. Read it off
  the index, so the answer is about the graph the caller is querying.
- **R4.2 — deterministic.** Identical index, identical field report. A sampled answer ("most Columns
  carry a type") is a different and weaker claim; if sampling is used, say so in the payload.
- **Not a source dump.** This exposes which fields are populated, not a new way to read bodies.
  `extra` holds adapter-specific values and the answer must stay bounded — key presence and counts,
  not every value in a 20,808-node kind.
- **R1.1.** The report is keyed by contract kind, never by language name in the core.
- **Omit-when-empty (061).** This rides an explicit request; nothing is added to the default payload
  of any existing call.

## Acceptance criteria

- **AC1** For a given qname, a caller can obtain which `NODE_FIELDS` and which `extra` keys that node
  actually carries, without reading source and without opening the database.
- **AC2** The three facts of this retro are decidable from tool output alone: a `Column` in a
  pre-[247](247_the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key.md)
  index reports no type, nullability or identity key; after 247 it reports them. The same call
  distinguishes the two indexes.
- **AC3** A `Column` with an FK reports the key 239 attaches; one without reports its absence — the
  caller can tell "this column has no FK" from "this tool does not return FKs".
- **AC4** The answer is bounded on the widest kind in the index and does not scale with node count.
- **AC5** No existing payload changes shape — every current tool's output is byte-identical
  before and after (the 022 AC3 check).

## References

- `code_atlas/tools/search_symbol.py` (`_hit`), `code_atlas/tools/read_symbol.py` (`_attach_params`,
  the 242 kind gate), `code_atlas/tools/file_outline.py`.
- `code_atlas/contract.py` — `NODE_FIELDS`, and `extra` as the frozen-fields escape hatch (236).
- [231](231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md) /
  [244](244_no-channel-announces-a-capability-change.md) — the capability stamp whose granularity this
  extends, and the `declared_types` flag the agent over-read.
- [247](247_the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key.md)
  — the capture gap this ticket makes visible. Filing both is deliberate: 247 fixes one instance,
  250 makes the next one checkable instead of guessable.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 250 — No call shows what a node actually holds (working doc)

- **Ticket:** 250 · local file `docs/tasks/250_no-call-shows-what-a-node-actually-holds.md`
- **Type:** enhancement
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 UI paths
- **TIER:** full
- **BASELINE:** green — related suite 57 passed on `8303edb00205ecd15ae88686cc14b263dd2fe4da`

## Session status

- **Last updated:** 2026-09-12
- **Current phase:** finalise
- **Next action:** push feature branch + open PR (handover-authorised); merge not authorised
- **Blocked on:** none
- **work_doc_mode:** embed
- Run: `/mango:autorun 250 --no-reviewer`; challenger ON.
- Branch: `feat/250-no-call-shows-what-a-node-actually-holds`
- Contract: `.mango/run-contract-250.txt`

---

## Phase 0 — Refine

`PREMISE: 12 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 2 want-decision asked | 1 how-decision resolved+cited | 2 ASSUMED | skip: no`

**PREMISE detail.** Present: `code_atlas/tools/search_symbol.py` (`_hit`), `code_atlas/tools/read_symbol.py` (`_attach_params`), `code_atlas/tools/file_outline.py`, `code_atlas/contract.py` (`NODE_FIELDS`, `extra`), tasks 061, 022, 231, 236, 239, 242, 244, 247. No missing resolvable identifiers.

**INPUT KIND:** ticket (not epic).

**How-decisions (self-resolved):**

1. **Shape — raw-fields view on an existing tool** (not a 25th tool; not the per-kind stamp this ticket). Citation: ticket Scope "The first is the working assumption"; CONVENTION §2 tools stay at 24 (`tests/test_documented_tool_count.py`); AGENTS.md "24 tools on the surface".

**ASSUMED (awaiting ratification) — handover authorised choose-the-best-approach:**

| # | Assumed choice | Why ASSUMED | Explicit confirm at gate | Reverses a prior decision? |
|---|----------------|-------------|--------------------------|----------------------------|
| 1 | AC2 evidence is fixture-shaped Column.extra (keys absent vs present), not two historical `graph.db` files | Acceptance-bar / evidence type; 247 already landed so a pre-247 index is not on this checkout | design / DISCLOSURE | no |
| 2 | The same call reports 239's derived `references` / `references_unresolved` as key presence (same `_hit` predicate on `REFERENCES` edges), not only stored `extra` | Exposure-checker [e0584966](e0584966-5b24-4ba9-b808-94a76bbffeb7); AC3 vs AC1; `search_symbol.py:389-399` attaches those keys from edges, they are not Column.extra | design / DISCLOSURE | no |

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `do-not-attest-past-the-payloads-resolution` | 2 | handle | Yes — absence of a key must mean "not stored", never "tool omitted it" |
| 2 | `prove-the-guard-fails` | 2 | handle | Yes — proving test red before the flag exists |
| 3 | `capability-signal-on-the-first-call-channel` | 2 | handle | Weigh: this ticket is a per-node read, not a stamp on `get_index_status` |

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch): found the AC3-vs-AC1 stored-vs-attached question; classified WANT; recorded as ASSUMED #2.

**Constraints from the scan:** R5.6, R4.2, R1.1, 061 omit-when-empty, 24-tool pin, extra is already a NODE_FIELD (no contract bump for a new column).

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria) | 5 decomposed | ROWS: C=5 R=2 G=2 AC=5`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 proven by | Status |
|----|--------|------------------|----------------|--------------|-----|-----------------|--------|
| G1 | Why | uncaptured vs unexposed indistinguishable | One call shows populated NODE_FIELDS + extra keys for a qname | agent guessed column types exist | D1 | AC1 | ✅ |
| G2 | Root cause | every read path projects; extra unexposed | Do not infer from stamps/enums; read the node row | `search_symbol._hit`; `read_symbol` source slice | D1 | AC1–AC3 | ✅ |
| C1 | Constraints | R5.6 derive, do not declare | Report what this index stores, never an adapter announcement | ticket Constraints | D1 | AC2 | ✅ |
| C2 | Constraints | R4.2 deterministic | Identical node → identical field report | ticket Constraints | D1 | proving | ✅ |
| C3 | Constraints | Not a source dump | Key presence (+ counts); no extra values; no kind-wide dump | ticket Constraints | D1 | AC4 | ✅ |
| C4 | Constraints | R1.1 | Keyed by contract kind / stored columns, never language name in core | ticket Constraints | D1 | R1.1 sweep | ✅ |
| C5 | Constraints | Omit-when-empty (061) | Explicit request only; default payloads unchanged | ticket Constraints | D1 | AC5 | ✅ |
| R1 | Scope | raw-fields view on existing tool | `read_symbol` flag (not a new tool, not a new detail_level default) | ticket working assumption | D1 | AC1, AC5 | ✅ |
| R2 | Scope | per-kind stamp may subsume | Out of this ticket; stamp stays language × flag | ticket Scope | — | N/A this change | ✅ |
| AC1 | AC | NODE_FIELDS + extra keys for a qname | Without source or opening the db | ticket AC1 | D3 | proving | ✅ |
| AC2 | AC | pre-247 Column has no type/null/identity; post-247 has them | Fixture extras, same call distinguishes | ticket AC2; ASSUMED #1 | D3 | proving | ✅ |
| AC3 | AC | Column with FK reports 239's key; without reports absence | Presence of `references` / `references_unresolved` from stored REFERENCES | ticket AC3; ASSUMED #2; `_hit` | D3 | proving | ✅ |
| AC4 | AC | bounded on widest kind; no scale with node count | Per-qname keys only; O(fields+extra keys+edge kinds) | ticket AC4 | D3 | proving | ✅ |
| AC5 | AC | every current tool byte-identical (022 AC3) | Flag default off; `TOOL_NAMES` derived, still 24 | ticket AC5 | D3 | identity test | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-----------------|
| AC1 | NODE_FIELDS + extra keys for one qname | `NODE_FIELDS` is 10-tuple in `contract.py:132-143`; extra is one of them; "carries" = non-null / extra key present | Y | greppable keys on the explicit-request payload | — |
| AC2 | pre-247 no type/nullability/identity; after 247 reports them | 247 writes `type`/`data_type`, `nullable`, `identity` on Column.extra; this checkout is post-247 | Y | two fixture nodes, same call | ASSUMED #1 (fixtures, not historical DBs) |
| AC3 | 239 key present vs absent | `_hit` attaches `references` / `references_unresolved` from REFERENCES edges, not extra | Y | Column with/without REFERENCES | ASSUMED #2 (include those keys as presence) |
| AC4 | bounded; no scale with node count | payload size = populated fields + extra key names + at most the 239 pair; independent of kind cardinality | Y | payload key count vs fixture kind size | — |
| AC5 | every tool byte-identical | `TOOL_NAMES` length 24; flag default false | Y | default `read_symbol` + other tools unchanged | — |

## Inventory

- **Denominator / total N:** 24 (`code_atlas.main.TOOL_NAMES`, derived — R6.7). AC5 is "every current tool"; the proving check derives the set, it does not list 24 literals.

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| 1 | Default payloads across `TOOL_NAMES` stay byte-identical when the new flag is unset | AC5 identity test | ✅ |

`TRACK: backend — 0/0 touched files under UI paths`

## Clarifications

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

1. Shape = raw-fields flag on `read_symbol` — ticket Scope working assumption + 24-tool pin.
2. AC2 evidence = fixture extras — handover + 247 extra keys (`ASSUMED` #1).
3. AC3 includes 239's edge-derived keys as presence — ticket AC3 + `search_symbol.py:389-399` (`ASSUMED` #2).

---

## Phase 1 — Analysis

- **Gap (enhancement / honesty):** `read_symbol` returns a source slice (+ params/columns projections). `search_symbol._hit` returns `{qname, kind, file, line}` plus 239's FK pair. `extra` is persisted and unread on the surface. Capability stamps answer language × flag, not "does this Column carry a type?".
- **Cause taxonomy:** data (facts stored, not projected) + validation (R5.6: absence vs omission).
- **Blast radius:** `code_atlas/tools/read_symbol.py` (`create` signature, `_result`); tests for the new flag; `tests/test_documented_tool_count.py` stays 24; docs (PLAN/BACKLOG/ledger). No adapter. No `contract_version` bump (no new NODE_FIELD). Count-pins: `TOOL_NAMES`, `DetailLevel` if we add a level (we will not — flag instead).
- `TRACK: backend` · `SCOPE: M` · `TIER: full` (AC5 N=24 > 1; not lite).

`RULE SECTIONS: 9 applicable — 9 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R1.4 (change-type) ✅ · R3 (change-type) ✅ · R4.2 (change-type) ✅ · R5.6 (change-type) ✅ · R6.1 (change-type) ✅ · R6.5 (change-type) ✅ · R6.7 (change-type) ✅ · R7.6 (change-type) ✅`

Recalled handles `do-not-attest-past-the-payloads-resolution` and `prove-the-guard-fails` union into R5.6 / R6.5 already listed. `capability-signal-on-the-first-call-channel` is AGENT_BRIEF, not a rulebook section.

### BASELINE

Related suite on untouched `main` `8303edb00205ecd15ae88686cc14b263dd2fe4da`:

Ran at 8303edb00205ecd15ae88686cc14b263dd2fe4da

```
.venv/bin/python -m pytest tests/test_read_symbol_minimal_drops_docblock.py tests/test_read_symbol_params.py tests/test_read_symbol_table_columns.py tests/test_search_read_outline.py tests/test_documented_tool_count.py tests/test_optional_field_capture.py tests/test_sql_tier2_vocabulary_is_opt_in.py -q --tb=line
.........................................................                [100%]
57 passed in 5.86s
```

`BASELINE: green — no failing items`. No baseline exclusions.

- **Gate 1 status:** ✋ surfaced (autorun proceeds on standing + handover; `j = 0`)

---

## Phase 2 — Design

- **Approach.** Add an explicit `stored_fields: bool = False` flag on `read_symbol` (same shape as `include_source` on find_callers — default off, 061). When true and a unique node is found, attach one object:

  - `node_fields`: names from `contract.NODE_FIELDS` (except `extra`) whose stored value is non-NULL / non-empty
  - `extra_keys`: sorted keys of parsed `extra` (always present; `[]` = no extra keys — R5.6)
  - on `kind == Column` only: `references` and `references_unresolved` as **always-present lists** (empty = no FK; reuse `search_symbol._column_reference_targets` so AC3 uses the same 239 predicate). Other kinds omit that pair (239 is kind-scoped).

  Values of extra are never returned. The flag is independent of `detail_level` (a `minimal` + `stored_fields=True` call is still not a source dump). Default payloads stay byte-identical.

- **Rejected.** (1) New 25th tool — rejected: 24-tool pin, agent already called `read_symbol`. (2) New `detail_level="raw"` — rejected: `test_mcp_server` publishes `DetailLevel` as the enum; a third level is a wider contract than a default-off flag. (3) Per-kind capability stamp (ticket's second shape) — rejected this ticket: stamp remains language × flag (231/244); it cannot name one Column's keys and would re-declare rather than derive (C1). (4) Returning extra values — rejected: C3 / "not a source dump".

**Assumptions**

| Assumption | Status |
|------------|--------|
| `extra` on a planted node is JSON object or dict (same as 242/247/248 tests) | verified — `test_read_symbol_params.py` / `_plant_table` |
| FastMCP publishes a new bool kwarg with default False without breaking `CALLS` | verified — `include_source` already ships this way; `CALLS` for READ omits the flag |
| `_column_reference_targets` import from `search_symbol` is acyclic | verified — search_symbol does not import read_symbol |
| Empty `references: []` on Column distinguishes "no FK" from "tool does not return FKs" (key absent on non-Column) | verified — 239 is kind-scoped at `_hit`; we keep that split |

**Smallest change-list**

| Change | File | Blast radius | Ph2 | k/N |
|--------|------|--------------|-----|-----|
| `stored_fields` flag + `_attach_stored_fields` | `code_atlas/tools/read_symbol.py` | MCP schema (auto); `test_mcp_server` CALLS (default omit); `_result` unchanged when flag false | R1,C1–C5,AC1–AC4 | 8/8 |
| Reuse 239 predicate | import `_column_reference_targets` | `search_symbol.py` stays owner; no second implementation (R1.8) | AC3 | 1/1 |
| Proving + AC tests | `tests/test_read_symbol_stored_fields.py` | planted-node helpers like 242/248; `len(TOOL_NAMES)==24` pin in `test_read_symbol_table_columns.py:323` stays green | AC1–AC5 | 5/5 |
| PLAN tool cell + prune | `docs/PLAN.md` (~L497) | one clause on the existing `read_symbol` row; no new §19 narrative | C5,R7.6 | 1/1 |
| Working doc / backlog / ledger / lesson | docs | `test_backlog_bookkeeping.py` | R7.2 | 1/1 |

**Recalled handles**

| Handle | Answer |
|--------|--------|
| `do-not-attest-past-the-payloads-resolution` | traced — extra is projected (type/default/stub) never listed; `_hit` omits empty `references`; this change always emits `extra_keys` and, on Column, both 239 lists |
| `prove-the-guard-fails` | traced — `stored_fields` is absent in `read_symbol.py` today (count 0) |
| `capability-signal-on-the-first-call-channel` | does not apply because this change adds a per-qname explicit-request field on `read_symbol`, not a stamp on `get_index_status` |

Ran at 8303edb00205ecd15ae88686cc14b263dd2fe4da

```
rg -c "stored_fields" code_atlas/tools/read_symbol.py || echo "rg_exit_1 count=0"
0 matches for 'stored_fields'
rg_exit_1 count=0
```

Ran at 8303edb00205ecd15ae88686cc14b263dd2fe4da

```
sed -n '389,400p' code_atlas/tools/search_symbol.py
    # Kind-scoped (061): only Column at standard; read existing REFERENCES edges (239).
    if (
        store is not None
        and detail_level != "minimal"
        and row["kind"] == "Column"
    ):
        resolved, unresolved = _column_reference_targets(store, str(row["qualified_name"]))
        if resolved:
            hit["references"] = resolved
        if unresolved:
            hit["references_unresolved"] = unresolved
    return hit
```

`HANDLES: 3 recalled | 2 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

**Proving test:** `.venv/bin/python -m pytest tests/test_read_symbol_stored_fields.py::test_pre_247_column_has_no_type_nullability_or_identity_key -q`

Fails pre-change (`TypeError` / unexpected kwarg `stored_fields`). Passes post-change: a planted Column whose extra has only what a pre-247 row held (`{}` or type-less) reports no `type`/`nullable`/`identity` in `extra_keys`.

**Verification plan**

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|------------|----------------|--------------------|--------------|
| AC1 | integration | integration (planted GraphStore + tool) | authored | ✅ |
| AC2 | integration | same module; pre vs post extra | authored | ✅ |
| AC3 | integration | Column ± REFERENCES edges | authored | ✅ |
| AC4 | logic | key-count bound vs planted wide extra | authored | ✅ |
| AC5 | integration | default call vs flag-off; 24 tools unchanged | n/a (signature default) | ✅ |

No input-shape-dependent AC (each names the keys it expects). No real corpus configured; none required.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Rollback.** Revert the feature-branch commits. One repo (`app`). No porting.

**SCOPE:** M (unchanged). **TIER:** full.

- **Gate 2 status:** ✋ surfaced (autorun proceeds on standing + handover; `u = 0`, `h == t + x`, no ❌)

---

## Phase 3 — Execute

- **Branch:** `feat/250-no-call-shows-what-a-node-actually-holds`
- **Proving test:** `tests/test_read_symbol_stored_fields.py::test_pre_247_column_has_no_type_nullability_or_identity_key`

- **Verification sweep.**
  - Axis 1 (files): `code_atlas/tools/read_symbol.py`, `tests/test_read_symbol_stored_fields.py`, `docs/PLAN.md` (tool cell), this working doc. ⊆ approved list. No adapter, no 25th tool, no `DetailLevel` change.
  - Axis 2 (behaviour): Approach bullets `implemented-as-approved` — flag default off; `stored_fields` object is keys not values; Column always has both 239 lists; other kinds omit them; 239 predicate reused from `search_symbol._column_reference_targets`.

- **Design-conformance deviations:** none.

- **Empirical output**

Product tree fd1e506ae540d4d5da5fd0c5a79325c8e1140ab8 (later commits are bookkeeping / PLAN wording). Re-run at that tree for check_lines `--tree`.

Ran at fd1e506ae540d4d5da5fd0c5a79325c8e1140ab8

```
$ .venv/bin/python -m pytest tests/test_read_symbol_stored_fields.py -q --tb=line
.......                                                                  [100%]
7 passed in 0.82s
```

Ran at fd1e506ae540d4d5da5fd0c5a79325c8e1140ab8

```
$ .venv/bin/python -m pytest tests/test_read_symbol_stored_fields.py tests/test_read_symbol_params.py tests/test_read_symbol_table_columns.py tests/test_read_symbol_minimal_drops_docblock.py tests/test_mcp_server.py tests/test_documented_tool_count.py tests/test_search_read_outline.py -q --tb=line
........................................................................ [ 58%]
....................................................                     [100%]
124 passed in 13.89s
```

- **Golden/snapshot:** none
- **Design-invalidation:** none

---

## Phase 4 — Review

- **REVIEWER: OFF (`--no-reviewer`)** — no rule-book-grounded review of this diff exists.
- **CHALLENGER: ON** — ticket-blind challenger [37e350ca](37e350ca-9d61-46f8-8159-e4fa9dfb3499). Raw ticket (above separator) + `git diff main...HEAD` on product paths only.
- **challenger result:** **11/11 MET — CLEAN**.
- **Verdict:** `clean (challenger only — REVIEWER: OFF)`
- **Scope reconciliation:** file + behaviour axes clean.
- **Proving test would fail without the change?** Yes — `stored_fields` is not a parameter on `main`.
- **Layer-match:** no ❌.

Reviewed at fd1e506ae540d4d5da5fd0c5a79325c8e1140ab8

Reviewed files: `code_atlas/tools/read_symbol.py`, `tests/test_read_symbol_stored_fields.py`, `docs/PLAN.md`

Working-doc path (stale-review exempt): `docs/tasks/250_no-call-shows-what-a-node-actually-holds.md`

- **Gate 4 status:** ✋ surfaced (autorun proceeds; challenger CLEAN; reviewer waived)

---

## Phase 5 — Finalise

**Durable lesson.** 239's FK keys are derived from `REFERENCES` edges at hit time; they are not Column.extra keys. A raw-fields view that only listed `extra_keys` would fail AC3.

### 250-C1 — An edge-attached hit key is not a stored extra key

- type: 2 (code) · handle: `edge-attached-is-not-stored-extra`
- status: proposed (awaiting human confirm)
- seen: 250
- evidence: `search_symbol._hit` attaches `references` / `references_unresolved` from stored edges; Column.extra does not hold them. AC3 required always-present lists on the raw-fields view.
- destination: stays in lessons_path

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (autorun)`

**P1.** Class-index `seen:` bumped for traced handles `do-not-attest-past-the-payloads-resolution` and `prove-the-guard-fails` (already R5.6 / R6.5).

**Gate:** `scripts/gate.sh` GATE GREEN — 20 passed · 0 failed · 0 skipped (Linux host; second run after PLAN.md R7.6 prune).

**Outward actions (handover-authorised):** (1) push feature branch (2) open PR. Merge not authorised.

**Token-usage (working doc).** 2 challenger dispatches unmeasured; reviewer off; main-loop unmeasured. See `docs/TOKEN_LEDGER.md` row 250.

