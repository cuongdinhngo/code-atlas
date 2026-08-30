---
id: 192
slug: coverage-note-suppressed-on-a-partial-answer
title: 'The coverage disclosure self-suppresses on any answer carrying results, so a partial answer is the one shape it never reaches'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [160, 173, 186]
---

## Why this exists (field retro 8-A, re-confirmed round 12 §14 row 6-C)

`attach_coverage_note` names the index's language-coverage gap on an empty answer. It returns early on
any answer that has results:

```python
    if payload.get("results"):
        return payload
```

`code_atlas/tools/coverage.py:119-120`. So the disclosure covers **absence** and never covers a
**partial** — which is the shape that has actually cost an answer, twice, measured:

- **Round 8 §4 (8-A).** `search_symbol("DialogueService")` returned **1** hit, a PHP test method.
  Ground truth: **281 `.js` files** reference it. The retro's words: *"`total_count: 1` on a symbol
  with 281 real sites is a false negative wearing a modelled zero's clothes"* — and *"nothing in any
  `no_matches` or low-`total_count` answer names the index's language coverage, while
  `get_index_status` holds `indexed_suffixes` one call away."*
- **Round 12 §14 row 6-C.** *"STILL INVERTED, now on JS… r9 showed completeness harming via
  `legacy/`; r12 shows the same shape with a new language added to it."*

**The trend is the argument.** The failure got worse when a language was added, both times, with no
code change. A third adapter ([184](184_tsql-source-adapter-tier-1a.md)) makes it worse a third time,
and that adapter cannot fix it — its AC3 forbids a `code_atlas/` diff.

**This is not the 186 census and not a new one.** 186 asks *"does the subject's language emit these
kinds?"*; that verdict is silent whenever the language does emit them, which is exactly the partial
case. The gap here is one condition in a function that already exists and already knows the answer.

## Scope

1. Let the coverage disclosure reach an answer that **carries results** and is nonetheless partial
   with respect to the index's coverage. The verdict stays a data question with no language name
   (R1.1) and reuses `attach_coverage_gap`; design records what makes an answer "partial" without
   re-deriving 186's or 173's existing predicates.
2. Keep it self-gating and idempotent, as the docstring promises for every return point — a confident
   exact answer must not grow a note (160's original carve-out survives).
3. Prove the no-false-alarm property: an answer complete with respect to the indexed languages gets
   **no** note. This is what makes the change safe to apply to non-empty payloads at all.

### Explicitly not in scope

- Any new node or edge vocabulary. Zero contract cost.
- The cross-language pair census, and per-subject unlinked-edge evidence — both were considered for
  184 and rejected: the first cannot separate a legitimately empty language pair from a gap, the
  second is inert until edges exist that never get emitted.
- Ranking. 6-C's other half is a ranking finding and belongs with 167/180.

## Constraints

- **R5.6** — silence is not evidence. Where the index cannot say, withhold the claim rather than
  inventing one; `relation_unmodelled_for_language` already answers `False` on every silence and this
  must not regress that.
- **R1.1** — the verdict reads the index's own stamps, never a language name.
- **R6.5** — the guard ships with a recorded red run: the note must be shown absent before the change
  on a payload that carries results.

## Acceptance criteria

1. An answer carrying results, partial with respect to the index's coverage, carries the disclosure —
   pinned by a test that fails before the change on the same payload.
2. An answer complete with respect to the indexed languages carries **no** note (no false alarm),
   pinned separately.
3. A confident exact/prefix answer is unchanged — 160's carve-out and 167's `substring_match` path
   both still behave as their tests assert.
4. No `contract_version` bump.

## References

Field retro round 8 §4 (8-A, the 1-vs-281 measurement), round 12 §14 row 6-C. `coverage.py:103-123`.
Related: [160](160_a-zero-answer-never-names-the-index-language-coverage.md) (the note's origin and its own carve-out),
[186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) (the per-language census this is **not**),
[184](184_tsql-source-adapter-tier-1a.md) (the third adapter that widens this, and whose AC3 bars it
from fixing it).

---

## Session status

- **KEY:** 192 · **work_doc_mode:** embed · **Run args:** `/mango:autorun 192 with skipped review`.
- **REVIEWER:** OFF · **CHALLENGER:** OFF — both waived by the run arg; the maintainer reviews on the PR.
- **Branch:** `fix/192-coverage-note-on-a-partial-answer` (off `main` at `12150c1`).
- **Current phase:** 5 finalise.

## Phase 0 — refine

`PREMISE: 9 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 3 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

Premise: `coverage.py:119-120`, `attach_coverage_gap`, `REASON_SUBSTRING_MATCH`, `REASON_NO_MATCHES`,
`REASON_NO_SUCH_SYMBOL`, tasks 160 · 173 · 186 · 061 — all resolve. Not an epic.

**Recalled (advisory):** `evidence-shaped-honesty-inverts-on-a-second-instance` (186-C1, handle) —
the closest relative, and the reason this is *not* that fix; `prove-the-guard-fails` (R6.5, handle);
`read-the-syntax-not-the-text` (190/187, handle) — **which then bit this very ticket**, see Phase 3;
`verify-cited-reference-at-pickup` (149-C1, area: process).

**How-decisions (resolved + cited, not asked):**

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| H1 | What makes an answer "partial"? | The **index** has a coverage gap. Not a property of the row count | `coverage.py:84-99` — `attach_coverage_gap` already answers exactly this |
| H2 | Why is widening safe on every answer? | Omit-when-empty: a fully-wired, fully-indexed server stays byte-identical | 061 / `attach_coverage_gap` docstring |
| H3 | Does the sweep pay N times? | No — the per-subject rule is untouched; only the single-answer path moves | `test_coverage_keys_on_indexed.py:125-126` |

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** S · **TIER:** full

`SECTIONS: 5 found (Why this exists, Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 5 decomposed | ROWS: C=3 R=3 G=1 AC=4`
`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 5 applicable — 3 by change-type | 2 by recalled handle — §R1.1 (change-type) ✅ the verdict reads config/stamps, no language name · §R5.6 (change-type) ✅ silence still withholds the claim; `unindexed_languages` returns [] on an unstamped index · §R7.6 (change-type) ✅ two 160 assertions replaced in place, not appended beside · §R6.5 (recalled handle: prove-the-guard-fails) ✅ red run recorded below · §R6.7 (recalled handle: derived-not-listed-invariant) ✅ the gap list stays derived from `shipped_adapters`, never re-listed`
`BASELINE: green`

**Gap analysis.** Current: `if payload.get("results"): return payload` (`coverage.py:119-120`) — the
disclosure covers absence only. Target: it covers **incompleteness**, which is what 8-A and round 12
6-C both measured. The gap is one condition.

## Phase 2 — design

**Approach.** Gate the disclosure on **the condition it describes** — does the index have a coverage
gap — instead of on the size of the result. One boolean moves; `attach_coverage_gap` is unchanged and
keeps supplying omit-when-empty.

**Rejected:** a new `partial` reason code (a reason is a routing verdict and this is a disclosure —
174's *"disclose the reader's cost, not the product's fact"*); a per-language pair census (considered
for 184 and rejected there — it cannot separate a legitimately empty language pair from a gap); a new
payload field (`unconfigured_adapters` already means exactly this and a second name would drift).

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`prove-the-guard-fails`** — `git stash`-free red run below; `KeyError: 'unconfigured_adapters'`.
- **`read-the-syntax-not-the-text`** — `grep -rn "total_count" code_atlas/tools/coverage.py` returned
  my own new docstring line, and `test_total_count_semantics` reddened on it. Traced, and it landed.
- **`derived-not-listed-invariant`** — `grep -rn "unconfigured_adapters" code_atlas/` returns only
  `coverage.py` (the key) and its writers; the list itself comes from `shipped_adapters`, unlisted.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `tests/test_zero_answer_coverage.py::test_a_partial_answer_now_carries_the_note`.

```
# red run — 160's carve-out restored:
E   KeyError: 'unconfigured_adapters'
1 failed in 0.04s
```

## Phase 3 — execute

**Blast radius, traced before the edit and confirmed by the suite** — applying claim `184-C4` from the
previous ticket, which is why this one found its readers up front rather than at the gate:

| Test | Why it moved |
|---|---|
| `test_zero_answer_coverage.py` ×2 | **160's own AC3, reversed.** Replaced with the argument, not deleted |
| `test_coverage_keys_on_indexed.py` | the confident-answer line; the per-subject rule is untouched |
| `test_batched_subject_sweep.py` ×1 | a whole-payload pin gains the key |
| `test_answer_pagination.py` | a key-set pin gains the key |
| `test_total_count_semantics.py` | **not a payload pin** — see below |

**Two findings this ticket did not expect:**

1. **A source-TEXT guard read my prose.** Writing the literal `total_count` into `coverage.py`'s new
   docstring registered the module as a `total_count` emitter and reddened a scan with nothing to do
   with this change. Third sighting of `read-the-syntax-not-the-text`, which is now **recurrence 3 and
   overdue for ratification**. Fixed by rewording the docstring — widening someone else's guard is not
   this ticket's business.
2. **The working tree did not match the branch.** `adapters/sql/node_modules`, left from 184 and
   gitignored, survived `git checkout main`, so `shipped_adapters` reported a third adapter on a branch
   that has none and every payload pin was measured against it. 26 MB removed (the source is safe at
   `cb5afc3`). Recorded as claim `192-C4`.

**A third finding, from the rebase onto a main that had gained 184.** Two things moved that no test
guards:

1. **A `seen:` sighting was silently dropped.** 184 took `prove-the-guard-fails` from 25 to 26; this
   ticket's own 25→26 edit then had nothing to apply to, so 192's red run vanished from the ledger.
   P1 makes `seen:` the *only* gate on promotion, so a lost sighting is a rule that never ripens —
   and **nothing fails when it happens**. Restored to 27 by hand.
2. **A payload pin had to be measured twice.** `unconfigured_adapters` listed two adapters when this
   branch was cut and three once 184 landed, so the pin this ticket had already corrected was wrong
   again for a reason that has nothing to do with this ticket.

Both are the same shape: **two tickets incrementing one shared counter, reconciled by a merge that
picks one.** Recorded as claim `192-C5`.

## Phase 5 — finalise

`CLAIMS: 5 claim(s) from 1 lesson entr(ies) | T1=0 T2=3 T3=0 T4=0 T5=2 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 5 candidate(s) checked | 5 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 1 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: execute (main-loop)`

**The promotion candidate is `read-the-syntax-not-the-text`**, now at **recurrence 3 (190, 187, 192)
and overdue** — it was proposed on 2026-08-29 and this is its third sighting. Proposed only;
`/mango:promote` and a human ratify own it.

### DISCLOSURE

1a. **REVIEWER: OFF** · 1b. **CHALLENGER: OFF** — both waived by the run arg. **Nothing but the author
    looked at this diff.**
2. **Two of task 160's assertions were reversed**, deliberately and with the argument recorded in
   their docstrings. A reviewer who disagrees with the reversal should read those two tests first.
3. **The tree did not match the branch for part of this ticket** (`adapters/sql/node_modules` from
   184), so any payload assertion I read before removing it was measured against a third adapter that
   was not in the branch. Everything reported here was re-measured after.
4. **The pin was measured twice and the second measurement is the one that counts** — see the rebase
   finding above.
5. **`gotchas_path` / `drift_path` do not exist**, so anything of that kind is surfaced here only.
6. **Call ceiling `unknown`** — no ledger history in the `fresh/calls` shape.
7. **Deferred:** the merge.
