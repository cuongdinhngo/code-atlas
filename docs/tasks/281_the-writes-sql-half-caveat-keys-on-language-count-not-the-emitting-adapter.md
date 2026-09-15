---
id: 281
slug: the-writes-sql-half-caveat-keys-on-language-count-not-the-emitting-adapter
title: 'The multi-language `WRITES` caveat fires on any index that covers ≥2 languages, not on the presence of a second `WRITES`-emitting adapter — correct only because SQL is the sole writer today, it is a confident over-attach the moment a second writer lands, and the honest key (which languages emit `WRITES`) is already stamped'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [278, 255, 264]
---

## Why this exists

278 (#362) made `find_references` on a `Table`/`Column` return the linked `WRITES` writer set and
attach `writes_sql_adapter_only` (`CAVEAT_WRITES_SQL_HALF`) when the answer is only the SQL half of a
multi-language repo. The gate is `_writes_answer_is_partial` (`code_atlas/tools/find_references.py:88`):

```python
def _writes_answer_is_partial(covered: str | None) -> bool:
    """True when the index covers ≥2 languages — the WRITES answer is the SQL half (278)."""
    if not covered:
        return False
    return len([name for name in covered.split(",") if name]) >= 2
```

It keys on the **count of covered languages**, not on **which languages emit `WRITES`**. Today only
the SQL adapter emits `WRITES`, so "≥2 covered languages" and "a non-SQL half exists that this answer
omits" happen to coincide, and the caveat is correct. The moment a second `WRITES`-emitting adapter
lands, the coincidence breaks: a repo covering SQL + that adapter would carry
`writes_sql_adapter_only` even though the answer already holds both writers — a confident caveat that
names a missing half that is not missing. No code changes for this to become wrong (255/264's recurring
shape: a language-count constant standing in for an edge-kind fact).

The honest signal already exists on the index. `EMITTED_KINDS_BY_LANGUAGE_KEY`
(`code_atlas/store.py:72`, stamped `code_atlas/indexer.py:1258`) records which kinds each language
emits, so "is there a covered language that emits `WRITES` and is not in this answer's set" is
answerable from the stamp, not inferred from a count.

## Scope / Deliverables

- **Key the caveat on emitters, not on language count.** Attach `writes_sql_adapter_only` (or a
  successor name if a second writer makes "sql" wrong) only when a covered language emits `WRITES` and
  is absent from the answer's contributing set — read from `EMITTED_KINDS_BY_LANGUAGE`, the same
  machinery 255/264 already use for the honesty predicate.
- **Name it for the shape, not the language.** If the caveat can now name more than SQL, the field/text
  must stop hard-coding "sql".

## Constraints

- R5.6: evidence, not inference — the caveat rides a stamped emitter fact, never a language count.
- R4.2: derived from stored rows, byte-reproducible.
- 061: a single-language or SQL-only-writer answer is unchanged; no new field where nothing is omitted.
- Do not widen 278's answer set — this ticket changes only *when the caveat fires*, not what is returned.

## Acceptance criteria

- A two-language index where the second language does **not** emit `WRITES` still attaches the caveat
  (unchanged from 278).
- A synthetic index where a second language **does** emit `WRITES`, and the answer already includes it,
  does **not** attach the caveat.
- The gate reads `EMITTED_KINDS_BY_LANGUAGE`, not `covered.split(",")` count.
- No existing 278 test changes verdict except the new emitter-based cases.

## References
`code_atlas/tools/find_references.py:88,568-570`, `code_atlas/tools/nav_result.py:702`
(`CAVEAT_WRITES_SQL_HALF`), `code_atlas/store.py:72` + `code_atlas/indexer.py:1258`
(`EMITTED_KINDS_BY_LANGUAGE`), [278](278_the-writer-set-is-computed-for-one-check-and-addressable-from-nothing.md),
[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md),
[264](264_the-honesty-predicate-is-still-one-language-s-shape-wearing-a-constant-s-name.md).
Origin: review of #362, 2026-09-15 (non-blocking follow-up).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 281 — WRITES caveat keys on emitters (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** S · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: rename caveat `writes_sql_adapter_only` → `writes_emitters_only` (and limit text) because a second WRITES-emitting covered language makes "sql" wrong while a non-emitting host language still triggers the caveat — ticket Scope "Name it for the shape, not the language". Citation: ticket Scope / Deliverables bullet 2.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=2 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | language-count gate over-attaches when second writer lands | key on EMITTED_KINDS | D1 | AC3 | ✅ |
| C1 | Constraints | R5.6 evidence not inference | stamped emitters | D1 | AC3 | ✅ |
| C2 | Constraints | R4.2 deterministic | derived from meta stamp | D1 | — | ✅ |
| C3 | Constraints | 061 / do not widen 278 answer set | caveat timing only | D1 | AC4 | ✅ |
| R1 | Scope | key caveat on emitters not language count | `_writes_answer_is_partial(covered, emitted)` | D1 | AC1–3 | ✅ |
| R2 | Scope | name for shape not language | `writes_emitters_only` | D1 | AC1 | ✅ |
| AC1 | AC | two-lang non-emitter still attaches | proving | D2 | proving | ✅ |
| AC2 | AC | all covered emit WRITES ⇒ no caveat | proving | D2 | proving | ✅ |
| AC3 | AC | gate reads EMITTED_KINDS not count | proving | D1 | proving | ✅ |
| AC4 | AC | existing 278 verdicts unchanged except new cases | proving | D2 | proving | ✅ |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: `_writes_answer_is_partial` keyed on `len(covered.split(",")) >= 2`; coincides with "non-SQL half exists" only while SQL is the sole WRITES emitter.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R5.6 ✅ · R4.2 ✅ · R7.6 ✅`

Ran at c2a50f0fc86cf65e7af93be2e34b1136bca113e4

```
$ .venv/bin/python -m pytest tests/test_table_writer_set_via_find_references.py -q --tb=no
.....                                                                    [100%]
5 passed in 0.37s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: read `stamped_emitted_kinds_by_language` beside `covered`; partial iff some covered language emits no `WRITES`; rename caveat to `writes_emitters_only`; TOOLS + docstring; proving case for two emitters.
- Rejected: keep `writes_sql_adapter_only` string (fails Scope "name for the shape"); key only on answer contributing languages without non-emitter arm (fails AC1).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_table_writer_set_via_find_references.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | emitter gate + rename | find_references · nav_result · TOOLS | Table/Column WRITES caveat | 3/3 |
| D2 | proving + two-emitter case | tests/test_table_writer_set_via_find_references.py | — | 1/1 |


## Phase 3 — Execute

**Branch:** feat/281-writes-caveat-keys-on-emitters
**Axis 1:** find_references · nav_result · TOOLS · proving test.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at c2a50f0fc86cf65e7af93be2e34b1136bca113e4

```
$ .venv/bin/python -m pytest tests/test_table_writer_set_via_find_references.py -q --tb=no
.....                                                                    [100%]
5 passed in 0.36s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — CLEAN (10 met · 0 not met · 0 can't tell); agent 102b9aad-344f-4a29-9efe-e79c45f69764
`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_table_writer_set_via_find_references.py — 5 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

PR review (#372): an unstamped index (`emitted is None`) dropped 278's caveat, claiming a complete writer set from an index that never measured itself — now falls back to the ≥2-covered-languages rule, matching `language_emits_none_of`'s "cannot say" precedent (R5.6). Proving: `test_unstamped_index_keeps_the_caveat` — 6 passed.

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN (.mango/gate-281b.log)
PR: https://github.com/cuongdinhngo/code-atlas/pull/372

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
