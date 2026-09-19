---
id: 293
slug: the-dot-spelling-is-a-near-miss-in-every-language-that-is-not-php
title: '287 banded `Class::method` as a direct hit because it is the spelling every stack trace uses, but it keyed the band on `MEMBER_SEPARATOR in query` — so `Class.method`, the spelling every TypeScript, Python and Java stack trace uses, still falls to the substring band, and 249''s separator repair cannot reach it because that repair is gated on `no_matches`, the gate 287 already found unreachable'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [287, 249, 253]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

287 is right about the finding and half-right about the population. The argument it shipped on — *an
agent pastes the spelling its stack trace, its ticket and its code review use* — is not a PHP fact.
PHP writes that spelling `Class::method`; TypeScript, Python and Java write it `Class.method`. The
guard added at `code_atlas/store.py:395` is `contract.MEMBER_SEPARATOR.casefold() not in q: return
False`, so only the PHP spelling reaches the boundary-suffix band.

Measured against the shipped predicate:

```
is_direct_match('Class::method', 'method', 'App\Svc\Class::method')      -> True
is_direct_match('Class.method',  'method', 'src/svc.ts::Class::method')  -> False
is_direct_match('Class.method',  'method', 'pkg/mod.py::Class::method')  -> False
```

The three qnames are the same shape; the three queries are the same *intent*. Two of them answer
`reason: substring_match` and rank below every trigram neighbour, which is the payload 287 exists to
stop an agent reading as "not really this one".

249's `member_separator_variant` already knows the variant spellings (`contract.py:288-302`) and
`search_symbol` calls it — but only in the `no_matches` branch (`tools/search_symbol.py:283`). A
`Class.method` query on a TS repo *has* hits; it is the substring band that is wrong, not the count.
That is the same reasoning 287 recorded for `::`, applied to the adapters that shipped after it.

## Scope / Deliverables

- **One definition site, extended** (R6.7): `is_direct_match` tries `contract.member_separator_variant`
  on a query that carries no `MEMBER_SEPARATOR`, and bands a boundary-suffix variant exactly as 287
  bands the direct spelling. `search_symbol`'s `reason` and the ordering band stay one decision.
- **No language branch** (R1.1): the variant alphabet is contract data (`_CONTAINER_SEPARATORS`, `member_separator_variant`), never
  a per-language rule and never a lookup of the subject's language.
- **The payload says which spelling matched.** A hit reached through a variant keeps 249's near-miss
  vocabulary in `reason`; banding must not silently claim the query was spelled as stored.

## Constraints

- **Byte-identical where nothing changes** (061 / R5.6): a query with no separator of any kind, and a
  query already carrying `::`, produce the same rows in the same order as today.
- **287's boundary rule is reused, not re-derived** — the character before the suffix must be a
  namespace/path separator, so `Foo_EntityPlan.getItem` is not a direct match for
  `EntityPlan::getItem`. `_` is an identifier character.
- The predicate runs as a SQLite UDF per candidate row; the variant is computed once per query, never
  per row.

## Acceptance criteria

- `is_direct_match('Class.method', 'method', 'src/svc.ts::Class::method')` is `True`, and the same for
  the `pkg/mod.py::Class::method` and PHP forms above.
- A TS fixture search for `UserService.getUser` returns the method in the direct band with a `reason`
  that names the separator variant, not `substring_match`.
- The underscore case stays `False`, pinned by its own test.
- A search that matched nothing before still matches nothing, and the 249 `no_matches` repair path is
  unchanged.

## References
`code_atlas/store.py:380-400`, `code_atlas/contract.py:288-302`,
`code_atlas/tools/search_symbol.py:283-295`,
[287](287_the-spelling-every-stack-trace-uses-is-a-near-miss.md),
[249](249_a-miss-whose-only-defect-is-the-separator-spelling-gets-no-route.md).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 293 — Class.method is a direct match (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: extend `_member_boundary_suffixes` via `member_separator_variant`; boundary charset includes `:` so `file::Class::method` matches; reason `separator_normalised` when only the variant arm fires — cites ticket Scope bullets 1–3 + 287 store.py boundary.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=3 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | Class.method falls to substring | extend is_direct_match | D1 | AC1 | ✅ |
| C1 | Constraints | R1.1 / contract data | member_separator_variant | D1 | — | ✅ |
| C2 | Constraints | 061 no-sep / :: unchanged | early arms | D1 | AC4 | ✅ |
| C3 | Constraints | 287 boundary reused | `\\/.:` | D1 | AC3 | ✅ |
| C4 | Constraints | UDF once per query | lru_cache suffixes | D1 | — | ✅ |
| R1 | Scope | one site extended | store.is_direct_match | D1 | AC1 | ✅ |
| R2 | Scope | reason names variant | separator_normalised | D2 | AC2 | ✅ |
| R3 | Scope | 249 no_matches unchanged | no gate move | D1 | AC4 | ✅ |
| AC1 | AC | predicate True for three forms | proving | D3 | proving | ✅ |
| AC2 | AC | TS fixture direct + reason | proving | D3 | proving | ✅ |
| AC3 | AC | underscore False | proving | D3 | proving | ✅ |
| AC4 | AC | no-sep / miss path unchanged | proving | D3 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: 287 keyed the band on MEMBER_SEPARATOR in query; Class.method never entered.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R6.7 (change-type) ✅ · R4.2 (change-type) ✅`

Ran at e297f69bd35f5f33ee364c756b3f86b2cb1b8b7b

```
$ .venv/bin/python -m pytest tests/test_class_method_direct_match.py tests/test_separator_spelling_near_miss.py -q --tb=no
............                                                             [100%]
12 passed in 0.58s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: cache variant suffixes; widen boundary to include `:`; search_symbol reason separator_normalised when only variant arm matches.
- Rejected: move 249 no_matches gate (ticket forbids); language branch (R1.1).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_dot_member_separator_direct_match.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | is_direct_match + suffixes | store.py | search order/reason | 1/1 |
| D2 | reason separator_normalised | search_symbol.py | payload reason | 1/1 |
| D3 | proving | tests/test_dot_member_separator_direct_match.py | — | 1/1 |

## Phase 3 — Execute

**Branch:** feat/293-dot-member-separator-direct-match
**Axis 1:** store · search_symbol · proving.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at e297f69bd35f5f33ee364c756b3f86b2cb1b8b7b

```
$ .venv/bin/python -m pytest tests/test_dot_member_separator_direct_match.py -q --tb=no
....                                                                     [100%]
4 passed in 0.18s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — round-1 NOT CLEAN (colon on :: arm); fixed; verify-only.
agent 0d084867-e931-4de0-a812-4feee72c9c3b

Verify-only:

Ran at e297f69bd35f5f33ee364c756b3f86b2cb1b8b7b

```
$ .venv/bin/python -m pytest tests/test_dot_member_separator_direct_match.py tests/test_class_method_direct_match.py -q --tb=no
........                                                                 [100%]
8 passed in 0.30s
```

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_dot_member_separator_direct_match.py — passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN — all 20 checks passed (`scripts/gate.sh`)
PR: https://github.com/cuongdinhngo/code-atlas/pull/390

## Review finding — the exactness predicate had grown a second definition site, 2026-09-19

`search_symbol` needs 167's exact/prefix arm alone to decide `separator_normalised`, and the branch
re-typed it as a private `_exact_or_prefix`. `is_direct_match`'s own docstring calls itself the one
definition site (R6.7) precisely so the reason code and the ordering band cannot drift; a copy of
half of it is that drift, and it drifts silently because every guard still passes.

Hoisted to `store.is_exact_or_prefix_match`, which `is_direct_match` now calls for its first arm and
`search_symbol` calls for its reason. One site, two readers.

**Left as designed, not a finding:** `Class.method` direct-matches `src/svc.ts::Class::method` while
`Class::method` does not, because 287/061 keep the native spelling off path-shaped qnames. The
asymmetry follows each language's own spelling and is pinned by
`test_double_colon_query_stays_off_path_shaped_qnames`.

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
