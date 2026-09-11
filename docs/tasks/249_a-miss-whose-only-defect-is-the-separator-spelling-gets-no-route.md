---
id: 249
slug: a-miss-whose-only-defect-is-the-separator-spelling-gets-no-route
title: 'A miss whose only defect is the separator spelling returns a clean no_matches, and 245''s near-miss route cannot fire because the guessed name is not a substring of the real one'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [245, 224]
---

## Why this exists (field retro — the anchor repo, 2026-09-11, round 17)

A consuming agent guessed the qname form for a column as `IndividualSiteForms.ChangeDateTime` and
swept seven subjects in that shape. All seven returned a clean `no_matches`. The real form is
`dbo.IndividualSiteForms::ChangeDateTime` — the container keeps its native `.` separator and the
member joins on with `::` (CONVENTION §3). The retro's note: *"it knew it had a node matching under a
different separator and suggested nothing"*, and it scored the round a full turn lower for it.

The turn was lost to a **spelling of the separator**, not to a wrong name, a wrong table or a wrong
column. Both halves of the qname were exactly right.

## Root cause

[245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md) shipped the route
for a near-miss page — `reason=substring_match` now carries `try_instead: file_outline` and a
narrow-by-qname hint. It cannot fire here, and the reason is mechanical: **the guess is not a
substring of the truth.** Measured on the anchor index:

```
real column qname:   dbo.Benefit::psi_file
dotted spelling:     dbo.Benefit.psi_file
  exact matches:     0
  substring matches: 0
```

Replacing `::` with `.` breaks the substring relation in both directions, so FTS and the trigram
near-miss path both return an empty candidate set. With no candidates there is nothing to rank, so
the payload is a truthful, complete, useless `no_matches` — and 245's route, which is attached to a
*populated* near-miss page, has nothing to attach to.

The separator is also the one part of a qname an agent cannot infer. A container's separator is
native to its language (`\Ns\Class`, `module.Class`, `src/user.ts`, `dbo.Table`) while the member
join is always `contract.MEMBER_SEPARATOR`. An agent that knows the table and the column still has to
guess which of the two it is looking at, and `.` is the spelling every SQL tool in the world prints.

## Scope

Before a search declares `no_matches`, retry the query with member-separator normalisation, and if
that retry finds candidates, return them as the near-miss shape 245 already defined — with the route
245 already built.

Concretely: for a query containing a separator character, try the variant where the **last**
separator is `contract.MEMBER_SEPARATOR`. `dbo.Benefit.psi_file` → `dbo.Benefit::psi_file`. The
last one is the right one to move because the member join is always the final segment; moving every
separator would turn `\Ns\Class::method` into nonsense.

## Constraints

- **R1.1 — no language branch in the core.** Normalise on `contract.MEMBER_SEPARATOR`, which is
  contract vocabulary. No `if language == "sql"`, and no list of which languages use `.` — the fix is
  the same one for `module.Class.method` in Python as for `dbo.T.col` in T-SQL.
- **R5.6 / R5.2 — a retry result is not an exact hit.** A subject found only by normalising the
  separator is a **near-miss**: it keeps the `substring_match` register (or a sibling reason naming
  the normalisation), never `reason=ok`. The agent asked for a name that is not in the graph; what it
  gets back is a correction, and the payload must say which.
- **No second search per miss on the hot path.** This runs only where the answer is already empty, so
  it costs nothing on a hit. Do not add the retry ahead of the primary lookup.
- **Deterministic (R4.2).** Identical input, identical rows — the retry is a pure string transform
  plus the same store query, nothing heuristic about ranking.
- **One spelling of one piece of advice.** If the existing `TRY_INSTEAD_HINT_NARROW_BY_QNAME` already
  says what the agent should do next, reuse it; a separator correction is a different *finding* and
  may need its own hint, but not a second phrasing of the same re-ask (the 245 review's rule).

## Acceptance criteria

- **AC1** `search_symbol` for `dbo.T.col`, where `dbo.T::col` is indexed, returns that node as a
  near-miss with a reason naming the correction — not `no_matches`, and not `reason=ok`.
- **AC2** The same holds for `read_symbol`, which is where a qname guess most often lands.
- **AC3** A query that misses under both spellings still returns the unchanged `no_matches` payload,
  byte-identical to today — the retry adds nothing when it finds nothing.
- **AC4** A query with no separator at all runs exactly one lookup; no extra store round-trip.
- **AC5** A genuine `.`-separated qname that exists as indexed (a Python `module.Class`) is returned
  as an exact hit by the primary lookup and never reaches the retry.
- **AC6** No language name appears in the core diff (`tests/test_no_language_branches.py` stays
  green).

## References

- `code_atlas/contract.py` — `MEMBER_SEPARATOR` and the qname convention (CONVENTION §3).
- `code_atlas/tools/search_symbol.py` — `_search_one`, the `substring_match` near-miss path and
  `TRY_INSTEAD_HINT_NARROW_BY_QNAME`.
- [245](245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md) — the route this
  reuses, and the reason it cannot fire on an empty candidate set.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Ticket:** 249
- **Type:** bug
- **Repo(s):** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed
- **working-doc path:** docs/tasks/249_a-miss-whose-only-defect-is-the-separator-spelling-gets-no-route.md
- **branch:** fix/249-separator-spelling-near-miss
- **plugin:** mango 1.16.1 @ /home/you/.claude/plugins/cache/mango-plugins/mango/1.16.1 (candidates: 5)
- **reviewer:** off · **challenger:** on
- **Phase:** finalise
- **autorun:** yes (`--no-reviewer`)

---

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions

**PREMISE detail.** Present: `code_atlas/contract.py` (`MEMBER_SEPARATOR`), `code_atlas/tools/search_symbol.py` (`_search_one`, `substring_match`, `TRY_INSTEAD_HINT_NARROW_BY_QNAME`), `code_atlas/tools/read_symbol.py`, ticket 245, CONVENTION §3 via contract. **Ambiguous (surfaced, not blocking):** field subject `IndividualSiteForms.ChangeDateTime` — private field evidence; ACs pin the *shape* (dotted last segment → `::`), not the name (R2).

**INPUT KIND:** ticket (not epic).

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `try-instead-tool-name` | 2 | handle | Yes — 093 two-register; may add one HINT if separator is a different finding |
| 2 | `route-must-answer` | 2 | handle | Yes — route must make progress; reuse FILE_OUTLINE |
| 3 | `prove-the-guard-fails` | 2 | handle | Yes — red-before: dotted query is no_matches today |
| 4 | `derived-not-listed-invariant` | 2 | handle | Yes — no second spelling of the same advice |

**Exposure-checker:** skipped (refine skip: yes).

---

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria · References) | 6 decomposed | ROWS: C=5 R=4 G=1 AC=6`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why/Root | dotted guess yields no_matches; 245 cannot fire (guess not a substring of truth) | Empty candidate set blocks the near-miss route | measured substring 0/0 on dotted vs `::` | D1 | proving test | ⬜ |
| C1 | Constraints | R1.1 no language branch | Normalise on `MEMBER_SEPARATOR` only; no language name | ticket Constraints | D1 | `test_no_language_branches` / core grep | ⬜ |
| C2 | Constraints | R5.6/R5.2 retry is near-miss not ok | Reason names the correction; never `reason=ok` | ticket Constraints | D1 | assert reason ≠ ok | ⬜ |
| C3 | Constraints | No second search on hot path | Retry only when primary answer is already empty | ticket Constraints | D1 | AC4 no-sep single lookup | ⬜ |
| C4 | Constraints | R4.2 deterministic | Pure string transform + same store query | ticket Constraints | D1 | fixture deterministic | ⬜ |
| C5 | Constraints | One spelling of advice | New HINT only if separator is a different finding; reuse FILE_OUTLINE tool | 245 review rule | D1 | 093 invariant | ⬜ |
| R1 | Scope | Before no_matches, retry with last sep → MEMBER_SEPARATOR | `dbo.T.col` → `dbo.T::col` | ticket Scope | D1 | AC1 | ⬜ |
| R2 | Scope | Last separator only | Moving every sep would break `\Ns\Class::method` | ticket Scope | D1 | helper unit + AC1 | ⬜ |
| R3 | Scope | Return 245 near-miss shape when retry finds | Route 245 already built | search_symbol `_needs_narrowing_route` | D1 | try_instead attach | ⬜ |
| R4 | Scope | read_symbol same | Exact qname miss path | read_symbol `_resolve_miss` | D2 | AC2 | ⬜ |
| AC1 | AC | search_symbol dotted → near-miss naming correction | Not no_matches, not ok | today's empty | D1,D3 | proving | ⬜ |
| AC2 | AC | read_symbol same | | | D2,D3 | proving | ⬜ |
| AC3 | AC | both spellings miss → byte-identical no_matches | Retry adds nothing when empty | | D1 | identity assert | ⬜ |
| AC4 | AC | no separator → one lookup | | | D1 | helper None + spy/assert | ⬜ |
| AC5 | AC | real dotted qname that exists → exact hit, no retry | Python `module.Class` | primary path | D1 | exact hit reason=ok | ⬜ |
| AC6 | AC | no language name in core diff | | | D1 | language-branch test | ⬜ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------|
| AC1 | near-miss naming correction | Primary empty; variant hits → non-ok reason | Y | greppable reason + results | — |
| AC2 | read_symbol same | Exact miss arm can retry variant | Y | reason + found/source shape | — |
| AC3 | byte-identical empty | No new keys when variant also empty | Y | dict equality vs pre-retry empty | — |
| AC4 | one lookup | helper returns None when no sep | Y | call-count / None return | — |
| AC5 | existing dotted is ok | Primary finds → never enters retry | Y | reason=ok | — |
| AC6 | no language in core | R1.1 CI grep | Y | test_no_language_branches | — |

## Inventory (universal "all/every/no")

- **Denominator / total N:** 0 — no universal all/every over a closed inventory; ACs are shape pins.
- Numbered list: (none)

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

---

## Phase 1 — Analysis

- Root cause (bug, `logic`): `store.search_nodes` / FTS and the trigram near-miss path both require the guess to be a substring of an indexed qname. Replacing `::` with `.` breaks that relation in both directions (`search_symbol.py` `_search_one` settles `REASON_NO_MATCHES` at empty `total_count`). 245's route attaches only on a *populated* `substring_match` / truncated page (`_needs_narrowing_route`), so an empty candidate set never reaches it. `read_symbol` exact lookup by qname has the same empty miss (`_resolve_miss` → `REASON_NO_SUCH_SYMBOL`).
- Handler / entry point + blast radius: `_search_one` / `_single_payload` / `_batch_answer`; `read_symbol` miss arm; `contract.MEMBER_SEPARATOR` (+ new pure helper); `nav_result` reason vocabulary + optional new HINT; NAV_REASONS pin tests; 245 route tests must stay green.
- `TRACK: backend — 0/0 touched files under UI paths`
- `SCOPE: S`
- `TIER: full`

`RULE SECTIONS: 8 applicable — 7 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ MEMBER_SEPARATOR only, no language name · R4.2 (change-type) ✅ pure transform · R5.2 (change-type) ✅ near-miss not ok · R5.4 (change-type) ✅ FILE_OUTLINE progress · R5.6 (change-type) ✅ reason names correction · R6.1 (change-type) ✅ proving fixture · R6.5 (recalled handle) ✅ red-before empty dotted · R7.5 (change-type) ✅ comments ≤3 lines`

### BASELINE

Related suite on untouched checkout:

```
Ran at 3548648b03e1b01ec13d7950c5ac57cf2e35bb0b
$ PYTHONPATH=.scratch/wt-249 .venv/bin/python -m pytest tests/test_search_symbol_truncated_substring_route.py tests/test_nav_reason_codes.py tests/test_empty_answer_cannot_explain_itself.py tests/test_try_instead_is_a_callable_tool_name.py -q --tb=no
25 passed in 2.97s
```

`BASELINE: green` for the change-adjacent suite. No baseline exclusions.

- Self-audit: sections 6=6; AC falsifiable; j=0; RULE SECTIONS named; TRACK/TIER/SCOPE declared.
- **Gate 1 status:** cleared (autorun closes on artifacts)

---

## Phase 2 — Design

- **Approach.** Add `contract.member_separator_variant(query) -> str | None`: replace the **last** single-char container separator (`.` / `\` / `/`) with `MEMBER_SEPARATOR`, returning None when none exists, when the last separator-like token is already `::`, or when the variant equals the input. In `_search_one`, only when the primary answer would be `REASON_NO_MATCHES` at `offset==0`, if a variant exists, re-query the store with it; on hits, rebuild the page and set `reason=REASON_SEPARATOR_NORMALISED` (sibling of `substring_match` that names the correction). Extend `_needs_narrowing_route` to include that reason so 245's `FILE_OUTLINE` route attaches; add `TRY_INSTEAD_HINT_MEMBER_SEPARATOR` (different finding → different hint; same tool register). In `read_symbol`, on the clean exact-miss path before returning `no_such_symbol`, try the variant; on a unique hit, return the body with `reason=separator_normalised` (not `ok`), keep the asked `qname`, attach the same route+hint. Never retry ahead of a hit; never on a query with no separator.

- **Rejected alternatives.**
  1. Reuse `substring_match` as the reason — rejected: AC asks for a reason *naming the correction*; substring_match names a different finding.
  2. Silently remapping to `reason=ok` with the corrected qname — rejected: R5.6/R5.2 / AC1–2.
  3. Retry before primary lookup — rejected: ticket hot-path constraint / AC4–5.
  4. Language-specific separator tables — rejected: R1.1.
  5. Widen shared NARROW_BY_QNAME prose to cover separators — rejected: 245 review (one spelling of one advice).

**Assumptions**

| Assumption | verified / novel-untested | If novel-untested → spike / proving test |
|------------|---------------------------|------------------------------------------|
| FTS exact/qname lookup finds `dbo.T::col` when queried with that spelling | verified | existing Column indexing + proving seed |
| `nodes_by_qualified_name` is exact on `::` form | verified | read_symbol path today |
| Last-separator transform is enough for SQL dotted guesses and Python `module.Class.method` | verified | ticket Scope + AC1/AC5 |

**Smallest change-list**

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| D1 | `member_separator_variant` + search retry on empty → `separator_normalised` + route | `contract.py`, `search_symbol.py`, `nav_result.py` | NAV_REASONS pins; 245 tests; search exactness | G1,C1–C5,R1–R3,AC1,AC3–AC6 | 3/3 |
| D2 | read_symbol exact-miss retry → same reason/route | `read_symbol.py` | read miss tests | R4,AC2 | 1/1 |
| D3 | Proving tests for AC1–AC5 + update NAV_REASONS pins | `tests/test_separator_spelling_near_miss.py` (new) + pin tests | none beyond new module | AC1–AC6 | — |

`HANDLES: 4 recalled | 4 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| Handle | Answer | Command + result (trimmed) |
|--------|--------|----------------------------|
| try-instead-tool-name | traced | `rg -n 'TRY_INSTEAD_HINT_NARROW_BY_QNAME' code_atlas/tools/nav_result.py` → keep; add sibling HINT_MEMBER_SEPARATOR |
| route-must-answer | traced | reuse FILE_OUTLINE; assert try_instead ≠ search_symbol self-loop without corrected arg |
| prove-the-guard-fails | traced | proving test seeds `dbo.T::col`, queries `dbo.T.col`, asserts pre-fix shape is no_matches via red-before in test design |
| derived-not-listed-invariant | traced | new HINT is a different finding; 093 invariant still lists HINT_* as prose |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Verification plan**

| AC | Proof layer | Named command / assertion | ❌? |
|----|-------------|---------------------------|-----|
| AC1 | unit | proving test search dotted → separator_normalised + route | — |
| AC2 | unit | proving test read_symbol same | — |
| AC3 | unit | both miss → byte-identical to primary empty | — |
| AC4 | unit | no-sep helper None; single search | — |
| AC5 | unit | existing `module.Class` → reason=ok | — |
| AC6 | unit | language-branch suite | — |

**Proving test (named, runnable):**
`/home/you/WORKSPACE/PROJECTS/code-atlas/.venv/bin/python -m pytest tests/test_separator_spelling_near_miss.py::test_search_dotted_column_is_separator_normalised_near_miss -q`

- **Gate 2 status:** cleared (autorun closes on artifacts)

---

## Phase 3 — Execute

**Branch:** `fix/249-separator-spelling-near-miss` (isolated worktree `.scratch/wt-249`)

**Implemented (approved list only):**
- D1: `contract.member_separator_variant`; search retry on `no_matches` → `REASON_SEPARATOR_NORMALISED` + FILE_OUTLINE / HINT_MEMBER_SEPARATOR; NAV_REASONS pin.
- D2: `read_symbol` exact-miss `_separator_normalised_hit`.
- D3: `tests/test_separator_spelling_near_miss.py` + NAV_REASONS pin updates.

**Verification sweep**

```
diff ⊆ approved list: code_atlas/contract.py, code_atlas/tools/search_symbol.py, code_atlas/tools/read_symbol.py, code_atlas/tools/nav_result.py, tests/test_separator_spelling_near_miss.py, tests/test_nav_reason_codes.py, tests/test_empty_answer_cannot_explain_itself.py, tests/test_relation_unmodelled_for_language.py, docs/tasks/249_*.md, docs/BACKLOG.md
Ran proving suite:
$ PYTHONPATH=.scratch/wt-249 .venv/bin/python -m pytest tests/test_separator_spelling_near_miss.py -q --tb=line
7 passed in 0.40s
```

**Design-conformance self-check:** matches D1–D3; no language branch; retry only on empty primary; reason ≠ ok.

- **Gate 3 status:** cleared pending commit + check_lines execute (autorun)

---

## Phase 4 — Review

**Reviewer:** OFF (`--no-reviewer`) — waived; no rule-book-grounded review ran.
**Challenger:** ON — ticket-blind, 1 dispatch.

Challenger reconstructed 10 requirements from the raw ticket; **10 met / 0 not met / 0 can't tell**. Overall **CLEAN**. Mild note: BACKLOG row was still `todo` at review time (bookkeeping deferred to finalise).

Proving evidence on reviewed tree:
```
Ran at 48db0b8bb466ead4c3703353f5b4fdf19c0a41ec
$ PYTHONPATH=.scratch/wt-249 .venv/bin/python -m pytest tests/test_separator_spelling_near_miss.py -q --tb=line
7 passed in 0.39s
```

Reviewed at 48db0b8bb466ead4c3703353f5b4fdf19c0a41ec

- **Gate 4 status:** cleared (challenger CLEAN; reviewer waived)

---

## Phase 5 — Finalise

Durable lesson: none beyond the ticket ACs — recalled handles (`try-instead-tool-name`, `route-must-answer`, `prove-the-guard-fails`) already cover the advice/route pattern; the sibling reason `separator_normalised` is the ticket's own vocabulary, not a new heuristic class to promote.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: challenger (1) + main-loop`

### Token usage (working doc)

| Phase | Tokens |
|---|---|
| autorun main-loop | unmeasured (host surfaces no usage block) |
| challenger ×1 | unmeasured |
| reviewer | waived (`--no-reviewer`) |

