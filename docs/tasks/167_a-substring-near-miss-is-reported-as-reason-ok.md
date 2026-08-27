---
id: 167
slug: a-substring-near-miss-is-reported-as-reason-ok
title: 'A substring near-miss is returned at `reason: "ok"` — asking for a symbol that does not exist yields a confident hit on a different one'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [014, 160, 093]
---

## Why this exists (field retro rounds 9 & 10)

160 deliberately deferred this, and round 10 verified on **fixed code** that it still bites:

```
search_symbol("storeCRM")  →  reason: "ok",  total_count: 7,
                              first result: \ModelMember::restoreCRM
```

> Round 9 (**9-C**): *"The only payload this round I would call harmful."*
>
> Round 10 §4: *"I asked for `storeCRM`; I was handed `restoreCRM` labelled `ok`. 9-C is live, and it is
> the single worst payload shape in the tool: **a substring near-miss is indistinguishable from a
> hit.**"*
>
> Round 10 §12.b: *"I asked for a symbol that does not exist and got a confident `ok` for a different
> one."* §15 ranks it ticket 5 of 6, and §14 records it **❌ CONFIRMED LIVE and harmful**.

Two rounds, same verdict, and it compounds the language-coverage gap 159/160 were built to close: in an
index that holds only some of a repo's languages, a JS identifier searched by name should be a **typed
refusal**, not a trigram near-miss on an unrelated PHP method. The absence the agent needs to see is
hidden by a hit it did not ask for.

## Root cause

- `code_atlas/tools/search_symbol.py:195` —
  `reason = REASON_OK if total_count > 0 else REASON_NO_MATCHES`.
  The reason is a pure function of **how many rows came back**, with no notion of **how they matched**.
- `code_atlas/tools/search_symbol.py:90` documents the matching as *"FTS trigram, or a name/qname
  prefix"* — so exact, prefix and substring hits are already distinguishable **at query time** and are
  then flattened into one undifferentiated `ok`.
- Because the reason reads `ok`, 160's `attach_coverage_note` — which fires only on
  `no_matches` / `no_such_symbol` (`code_atlas/tools/coverage.py:34-45`) — **never attaches**. The
  language-coverage note is suppressed by precisely the answer shape that most needs it.

## Scope

Make the match mode visible, so a near-miss cannot pass as a hit.

1. Carry **how each result matched** — an exact/prefix/substring discriminator on the row, or a
   payload-level `matched_on`, or a distinct `reason` (e.g. `substring_match`) when **no** result is an
   exact or prefix match. Design picks one and records the rejected alternatives.
2. When no result matches exactly or by prefix, the answer must be legible as a near-miss, and 160's
   coverage note must be able to ride it (the `storeCRM` case is exactly a language-coverage miss).

### Explicitly not in scope

- Changing the FTS query, the ranking, or dropping substring results. Substring matching is useful; it
  is the **labelling** that is wrong.
- The `find_*` family — a follow-up if the discriminator generalises.

## Constraints

- **R3** — a new `reason` value is nav vocabulary, not contract vocabulary; confirm against
  `contract.py` before choosing that shape. Prefer an additive field if it avoids the question.
- **061** — an answer containing an exact match must be byte-identical to today.
- **Cost** — `search_symbol` is a sweep tool with a batch envelope; the discriminator must not add a
  per-row query.
- **R1.1** — no language branch. (The subject's *language* is deliberately out of scope; 160 already
  settled that the note names the **index's** gap, not the subject's language.)
- **R4.2** — deterministic ordering and labelling.

## Acceptance criteria

1. `search_symbol` on a subject that exists only as a substring of other symbols is distinguishable from
   one that matched exactly — pinned by a test using the `storeCRM` / `restoreCRM` shape (generic
   fixture names, R2).
2. In that case 160's `unconfigured_adapters` note attaches when a coverage gap exists.
3. An answer containing an exact or prefix match is byte-identical to today (061).
4. The sweep/batch envelope carries the same discriminator as the single-subject path (160's AC1e
   lesson: the sweep path is the one that gets missed).
5. No per-row query added; cost measured against the tokens-to-answer gate.
6. Determinism (R4.2); no language branch (R1.1); contract impact confirmed and recorded (R3).

## References

Field retro round 9 finding **9-C**; round 10 §4, §12.b (**deferral tested, still bites**), §14
(confirmed live), §15 ticket 5. `code_atlas/tools/search_symbol.py:90,195`;
`code_atlas/tools/coverage.py:34-45`. Related: [160](160_a-zero-answer-never-names-the-index-language-coverage.md)
(the deferral's origin), [014](014_search-read-outline.md), [093](093_try-instead-is-not-a-callable-tool-name.md).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 167 · **work_doc_mode:** embed · **Run args:** `--no-challenger` (skipped review); Gate 4 waived per AGENTS.md.
- **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Branch:** `feat/167-search-symbol-labels-substring-near-miss`
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** red (Windows `import fcntl`); delta-green via Docker.

## Phase 0 — refine

`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

Fully specified; the discriminator shape (row flag / `matched_on` / distinct reason) the ticket labels a design decision (HOW). Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 2 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=5 R=2 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type) ✅ · §R7.2 (change-type) ✅`
`BASELINE: red — bare pytest fails at collection (import fcntl, Windows platform exclusion); delta-green via Docker`

**Premise:** `search_symbol.py:90,195`, `coverage.py:34-45`, `nav_result.NAV_REASONS`, `store.search_nodes` all resolve.
**Recall:** `160-C1` (self-gating-attach-audit-every-entry, by symbol — the sweep path must carry it too), `159-C1` (discoverability, by symbol).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | a substring near-miss must not pass as a confident hit | make the match mode visible | `search_symbol.py:195` | open |
| R1 | Scope 1 | carry how each result matched (row flag / `matched_on` / distinct `reason`) when no exact/prefix | design picks one; distinct reason chosen | `search_symbol.py:90` | open |
| R2 | Scope 2 | when no exact/prefix match, legible as a near-miss + 160's note can ride it | new reason + coverage extension | `coverage.py:42` | open |
| AC1 | AC 1 | substring-only subject distinguishable from an exact match — `storeCRM`/`restoreCRM` shape, generic names | Falsifiable: seeded near-miss test | proving test | open |
| AC2 | AC 2 | 160's `unconfigured_adapters` note attaches on the near-miss when a gap exists | Falsifiable: coverage note test | proving test | open |
| AC3 | AC 3 | an exact/prefix answer is byte-identical to today (061) | Falsifiable: exact/prefix → ok, no note | pin test | open |
| AC4 | AC 4 | sweep/batch carries the same discriminator (160 AC1e) | Falsifiable: queries=[...] near-miss test | proving test | open |
| AC5 | AC 5 | no per-row query; cost measured | Falsifiable: in-memory classify; benchmark green | — | open |
| AC6 | AC 6 | determinism (R4.2), no language branch (R1.1), contract impact confirmed (R3) | Falsifiable: grep-gate; NavReason not in contract.py | — | open |
| C1 | Constraint | R3 — new reason is nav vocabulary, not contract; confirm vs contract.py | `NAV_REASONS` in nav_result.py, not contract.py | binding |
| C2 | Constraint | 061 — exact-match answer byte-identical | =AC3 | binding |
| C3 | Constraint | Cost — no per-row query on the sweep | in-memory over returned page | binding |
| C4 | Constraint | R1.1 — no language branch | query-vs-name compare | binding |
| C5 | Constraint | R4.2 — deterministic ordering + labelling | pure fn of query + rows | binding |

### AC validation

All ACs falsifiable; none a bare ✅. **R3 contract impact confirmed:** `NavReason`/`NAV_REASONS` live in `code_atlas/tools/nav_result.py` (tool layer), not `contract.py`; a new nav reason is not contract vocabulary → **no `contract_version` bump**. Two tests pin the vocabulary exactly (`test_nav_reason_codes`, `test_empty_answer_cannot_explain_itself`) and are updated in the same diff (the tuple + newest-last pin).

### Root cause (taxonomy: logic)

`search_symbol.py:195` — `reason = REASON_OK if total_count > 0 else REASON_NO_MATCHES`: the reason is a pure function of the row count, with no notion of *how* they matched, even though exact/prefix/substring are distinguishable at query time. Because the near-miss reads `ok`, 160's `attach_coverage_note` (gated on `no_matches`/`no_such_symbol`, `coverage.py:44`) never fires — the coverage note is suppressed by exactly the shape that most needs it.

### Blast radius

- `search_symbol.py` (reason logic + a pure classifier), `coverage.py` (note gating), `nav_result.py` (one new reason).
- The classifier is shared via `_search_one` → both single and sweep paths carry it (AC4).
- Two vocabulary-pinning tests updated. No contract/store/resolver change.
- `find_*` family explicitly out of scope (follow-up if the discriminator generalises).

## Phase 2 — design

### Approach

Add nav reason `REASON_SUBSTRING_MATCH = "substring_match"`. In `_search_one`, once `total_count > 0` and `status != stale`, classify the **first page** (`rows[:cap]`, which already carry `name`/`qualified_name`): if no row is an exact match or a prefix of the query (`_is_direct_match`, case-insensitive, in-memory), the reason is `substring_match`; otherwise `ok` (byte-identical). Gate on `offset == 0` so paging past the ranked head stays byte-identical. Extend `attach_coverage_note` to attach on a `substring_match` answer **despite** its non-empty `results` (the requested symbol is absent — the rows are near-misses). The sweep envelope's coverage-gap trigger also fires on any `substring_match` subject (AC4).

### Design decisions (the HOWs the ticket delegated)

- **A distinct `reason` (`substring_match`), not a per-row `matched_on` flag.** It is what makes 160's note able to ride the answer (the note gates on `reason`), it is one word not a per-row field (cost), and it reads at the payload level where the agent judges the answer. **Rejected:** a per-row `matched_on` discriminator — leaves `reason: ok`, so the coverage note still never attaches (AC2 fails) and it adds a per-row field (cost). **Rejected:** payload-level `matched_on` alongside `reason: ok` — same AC2 failure; the reason is the field the agent and 160 both key on.
- **First-page-only (`offset == 0`).** Ranked search puts exact/prefix hits first, so page 1 having none is the honest near-miss signal; paging stays byte-identical (AC3).

### Assumptions

| Assumption | Tag |
|---|---|
| `search_nodes` rows carry `name` + `qualified_name` (REQUIRED_NODE_FIELDS) | verified (contract.py:136) |
| Ranked FTS surfaces an exact/prefix match on page 1 if one exists | verified (reasoning; `_SEARCH_ORDER`) — first-page gate makes the miss case honest |
| Classifying in memory adds no query | verified (no SQL in `_is_direct_match`) |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `REASON_SUBSTRING_MATCH` in Literal + constant + `NAV_REASONS` | `code_atlas/tools/nav_result.py` | two vocabulary-pin tests | R1, AC6 | 1/1 |
| `_is_direct_match` + reason logic (offset==0, first page) | `code_atlas/tools/search_symbol.py` | single + sweep via `_search_one`; docstring updated | R1, AC1, AC3, AC4, AC5 | 1/1 |
| envelope coverage-gap trigger includes substring_match | `code_atlas/tools/search_symbol.py` | batch path | R2, AC4 | 1/1 |
| `attach_coverage_note` rides substring_match despite results | `code_atlas/tools/coverage.py` | genuine-absence path unchanged | R2, AC2 | 1/1 |
| Update the two vocabulary-pin tests | `tests/test_nav_reason_codes.py`, `tests/test_empty_answer_cannot_explain_itself.py` | — | AC6 | 1/1 |
| Proving tests (near-miss, exact/prefix, sweep, coverage helper) | `tests/test_zero_answer_coverage.py` | new tests | AC1, AC2, AC3, AC4 | 1/1 |
| Docs: BACKLOG, TOKEN_LEDGER, LESSONS | `docs/*` | R7.2 | R7.2 | 1/1 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

(RECALL surfaced 2 by symbol, 0 type-2 handles. The `160-C1` symbol match is honoured in-design: `_search_one` is the shared entry so the sweep path carries the discriminator — the AC1e lesson — and a proving test pins the sweep envelope.)

### Rule compliance

R1.1 (query-vs-name string compare, not a language switch) ✅ · R3 (nav reason, not contract; no bump — confirmed) ✅ · R4.2 (pure fn of query + ordered rows) ✅ · R6.1/R6.5 (proving tests, red pre-fix) ✅ · R7.2 ✅.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (seeded store + FTS) | integration (seeded near-miss) | ✅ |
| AC2 | logic (note gating) + integration | unit (coverage helper) + integration | ✅ |
| AC3 | logic (exact/prefix → ok) | integration (seeded exact + prefix) | ✅ |
| AC4 | integration (sweep envelope) | integration (queries=[...]) | ✅ |
| AC5 | logic (no query) | code inspection + benchmark in full suite | ✅ |
| AC6 | logic + guard (R1.1 grep, contract test) | unit + grep-gate | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

### Proving test

`test_substring_near_miss_is_labelled_and_carries_the_gap` — seed `resetPaginate`, search `paginate`; fails pre-fix (`reason: ok`, no note), passes after (`substring_match` + `unconfigured_adapters`). Plus exact/prefix byte-identical, sweep-envelope, and coverage-helper tests. `pytest tests/test_zero_answer_coverage.py -k substring`.

### Rollback + porting

Rollback: revert the three tool files + test updates. Porting: `app` only.

### SCOPE

`SCOPE: M` — three small tool edits + tests + bookkeeping; branch `feat` matches (a new honesty label).

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| `REASON_SUBSTRING_MATCH` added to nav vocabulary | implemented-as-approved |
| `_is_direct_match` + first-page reason logic in `_search_one` | implemented-as-approved |
| coverage note + sweep envelope ride substring_match | implemented-as-approved |

No deviations. Diff ⊆ approved list.

### Empirical outputs

After fix (Docker/Linux):
```
ruff check code_atlas/ tests/ → All checks passed!
mypy code_atlas               → MYPY-OK (72 files)
targeted vocab + coverage     → 26 passed
full suite                    → 2124 passed, 1 skipped, 0 failed (158.50s)
```
AC5: `_is_direct_match` is pure in-memory string comparison over the returned page — no SQL, no per-row query. Payload delta = the reason word + 160's existing note (only when a coverage gap exists).

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_substring_near_miss_is_labelled_and_carries_the_gap` (red→green) |
| AC2 | `test_coverage_note_rides_a_substring_match_with_results` + AC1 test |
| AC3 | `test_exact_and_prefix_matches_stay_ok_and_byte_identical` |
| AC4 | `test_sweep_substring_near_miss_names_the_gap_on_the_envelope` |
| AC5 | code inspection (no SQL in classifier); benchmark green in full suite |
| AC6 | R1.1 grep clean; NavReason not in contract.py; two vocab-pin tests updated |

## Phase 5 — finalise

**Delta-green (Docker/Linux):** full suite `2124 passed, 1 skipped, 0 failed`; ruff+mypy green (72 files). Bare pytest red on Windows (`fcntl`) — recorded exclusion.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`167-C1` (type-2, `label-how-it-matched-not-just-how-many`, seen: 167) recorded as `proposed`. seen=1 → stays in lessons_path. Relates to 160/065.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; review phase skipped by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer + challenger waived; no `Reviewed at` marker → stale-review guard waived. Self-checks: proving tests red→green, full suite delta-green, ruff/mypy green.
