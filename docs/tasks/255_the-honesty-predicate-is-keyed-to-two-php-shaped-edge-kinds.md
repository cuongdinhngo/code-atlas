---
id: 255
slug: the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds
title: 'The predicate that decides whether an empty `find_references` is a genuine zero counts unlinked `REFERENCES`/`IMPORTS` only — the two kinds a PHP class subject has — so a T-SQL `Table` with 76 unlinked edges against it, 34 of them `WRITES`, returns a bare `no_matches`: the honesty layer is keyed to one language''s shape inside a core that forbids language branches'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [221, 232, 186, 065]
---

## Why this exists (field retro — the anchor repo, 2026-09-11, round 18, verified live)

Round 18 recorded the session's one damaging answer and named it precisely:

> `find_references` on a **Table** returns a bare `no_matches` while `find_callers` on a **Function**
> in the same T-SQL file self-diagnoses as unmeasured. Same index, same language, two different
> honesty levels — and **the quiet one is the one I would have believed.** […] "What else touches
> `dbo.UserNotes`?" is exactly the question I asked before re-pointing two of its default
> constraints. If I had not had a prior note telling me T-SQL call edges are unreliable here,
> `no_matches` is a green light to change a column that three procs and a legacy view depend on.

Its ask was a caveat. **Measured against the anchor index read-only, the caveat is not the fix and
the size of the hazard is larger than the retro could see:**

```sql
-- .code-atlas/graph.db (the anchor repo, 2026-09-11), read-only
select count(*) from nodes  where qualified_name = 'dbo.UserNotes';      -- 1
select count(*) from edges  where target_qname   = 'dbo.UserNotes';      -- 0   <- the answer given
select kind, count(*) from edges where target_raw like '%UserNotes%';
--   CALLS 2 · CONTAINS 40 · WRITES 34                                    -- 76  <- what exists
```

**Thirty-four `WRITES` edges target this table and the tool reports nothing touches it.** `WRITES` is
the one relation in the contract that means *this changes the table's contents* — the exact relation a
reader asks about before re-pointing a default constraint.

## Root cause

`find_references` decides a zero is *unmeasured* rather than *genuine* by counting unlinked inbound
edges — but only of two kinds (`code_atlas/tools/find_references.py:223-233`):

```python
unlinked = store.count_unlinked_by_target_raw((lookup, name), kinds=UNMODELLED_REFERENCE_KINDS)
if unlinked > 0:
    reason = REASON_RELATIONSHIP_NOT_MODELLED
```

and `UNMODELLED_REFERENCE_KINDS = ("REFERENCES", "IMPORTS")` (`code_atlas/contract.py:106`).

A PHP `Class` subject is referenced by exactly those two kinds, so the predicate reads as general. A
T-SQL `Table` subject is reached by `WRITES`, `CALLS` and `CONTAINS`, none of which the predicate
counts — so `unlinked == 0`, the `relation_unmodelled_for_language` arm (which only asks about
`REFERENCES`) also declines, and the answer falls through to a bare `no_matches`.

**This is a language branch wearing a constant's name.** R1.1 forbids `if language == …` in the core;
the rule's purpose is that the core must not encode one language's shape. A tuple of the two edge
kinds PHP happens to use, consulted as though it were the set of all inbound relations, is that same
defect expressed as data instead of as an `if`. 232 found the mirror image one level down — one
emitted kind in a set masking a never-emitted sibling — and widened the reader per kind; the set
itself was never questioned.

## Scope

Two parts, and the second is the one that stops this recurring:

- **Key the predicate to the subject, not to PHP.** The kinds that can carry an inbound relation to a
  subject are derivable from the contract and from what this index actually holds — a `Table`'s are
  `WRITES`/`CALLS`/`CONTAINS`, a `Class`'s are `REFERENCES`/`IMPORTS`. Whether `find_references` should
  *return* `WRITES` hits, or only stop claiming a zero over them, is phase 2's decision; the ticket
  binds only that a bare `no_matches` over 76 unlinked edges must become impossible.
- **A conformance matrix, so the next kind does not repeat this.** This is the sixth instance of one
  class: 065 (an empty answer cannot explain itself) → 093 (the route must be callable) → 245 (the
  truncated substring shape) → 249 (the separator spelling) → 253 (the zero-overlap guess) → this.
  Each was fixed as one cell. A test over **(subject kind × relation × language present in the
  fixture index)** that fails when any cell can return an empty answer carrying neither a measured
  `reason` nor a route turns a recurring class into a gate.

## Constraints

- **R5.6** — derive the kind set from the contract and the index; an adapter must not *declare* which
  relations reach its kinds, or this repeats 231's failure one level down.
- **R1.1** — the fix is keyed by contract kind. A second hardcoded tuple, however well chosen, is the
  same defect.
- **R4.2 / 061** — deterministic; nothing added to an answer that has hits.
- **The matrix must fail on today's code.** A gate that passes before the fix proves nothing (R6.5).
- **022 AC3** — every payload that has hits today is byte-identical.

## Acceptance criteria

- **AC1** `find_references` on a `Table` with unlinked `WRITES`/`CALLS` against it no longer returns a
  bare `no_matches`; the answer names the relation it could not measure. The proving fixture mirrors
  `dbo.UserNotes`: one `Table` node, zero linked inbound edges, unlinked `WRITES` present.
- **AC2** The `Function` path's existing self-diagnosis (221/214) is unchanged — this ticket removes an
  asymmetry, it does not move the honest side.
- **AC3** A `Table` genuinely untouched by anything returns a zero distinguishable from AC1's answer.
- **AC4** The matrix test enumerates every contract kind against every inbound relation for the
  languages in the fixture index, and **fails on the pre-fix tree** at the `Table` × `WRITES` cell.
- **AC5** No payload with hits changes shape (022 AC3).

## References

- `code_atlas/tools/find_references.py:223-233`; `code_atlas/contract.py:106`
  (`UNMODELLED_REFERENCE_KINDS`), `:76`/`:124` (`WRITES` in the vocabulary since 022).
- [221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) — the same class on the
  `find_callers` side, fixed there; this is why the two tools disagree.
- [232](232_the-same-construct-is-a-references-edge-in-python-and-node-extra-in-php-and-ts.md) — widened
  the reader per kind and left the kind *set* unexamined.
- [065](065_empty-answer-cannot-explain-itself.md) — the rule this violates, and the first of the six.


## Session status

- **Ticket:** 255
- **Type:** bug
- **Repo(s):** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed
- **working-doc path:** docs/tasks/255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md
- **branch:** feat/255-honesty-predicate-not-php-shaped
- **plugin:** mango 1.16.1 @ /home/you/.claude/plugins/cache/mango-plugins/mango/1.16.1 (candidates: 10)
- **reviewer:** off · **challenger:** on
- **Current phase:** finalise
- **autorun:** yes (`--no-reviewer`)

---

## Phase 0 — Refine

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 1 want-decision asked | 0 how-decision resolved+cited | 1 ASSUMED | skip: no`

**PREMISE detail.** Present: `find_references.py` honesty arm, `UNMODELLED_REFERENCE_KINDS`, tickets 065/186/221/232, UserNotes SQL counts in the ticket body.

**INPUT KIND:** ticket (not epic).

**ASSUMED under handover (want-bar decisions — recorded in DISCLOSURE):**
1. Phase-2 choice: **widen honesty only** — do not surface unlinked `WRITES` as `results` hits; stop claiming bare `no_matches` over any unlinked `EDGE_KINDS` inbound edge (`relationship_not_modelled`).
2. Hint routing: Class/Interface/Trait keep `try_instead=search_symbol` + METHOD hint (093); other kinds get relation hint only (no self-loop tool name).
3. AC4 matrix scope: `Table` × every `EDGE_KINDS` cell (the failing subject); not a full subject-kind cartesian in this ticket.

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `empty-answer-must-explain-itself` | 2 | handle | Yes — bare no_matches over unlinked edges |
| 2 | `evidence-shaped-honesty-inverts-on-a-second-instance` | 2 | handle | Yes — PHP-shaped set fails on Table |
| 3 | `do-not-attest-past-the-payloads-resolution` | 2 | handle | Yes — honesty ≠ returning unresolved as hits |

**Exposure-checker:** skipped (ASSUMED decisions recorded; handover authorises).

---

## Requirements matrix

`SECTIONS: 6 found (Why this exists · Root cause · Scope · Constraints · Acceptance criteria · References) | 6 decomposed | ROWS: C=5 R=2 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why/Root | Table+WRITES reads as bare no_matches | honesty keyed to REFERENCES/IMPORTS only | find_references honesty arm | D1 | proving AC1 | ⬜ |
| C1 | Constraints | R1.1 no language-shaped constant | key to EDGE_KINDS | ticket | D1 | matrix + R1.1 suite | ⬜ |
| C2 | Constraints | R5.6 derive from contract/index | no adapter-declared inbound map | ticket | D1 | EDGE_KINDS import | ⬜ |
| C3 | Constraints | R4.2 / 061 hits unchanged | honesty only on empty path | ticket | D1 | AC5 | ⬜ |
| C4 | Constraints | matrix fails pre-fix | R6.5 | ticket | D2 | AC4 | ⬜ |
| C5 | Constraints | 022 AC3 hit payloads identical | | ticket | D1 | AC5 | ⬜ |
| R1 | Scope | stop bare zero over unlinked inbound | relationship_not_modelled | Scope | D1 | AC1 | ⬜ |
| R2 | Scope | conformance matrix | Table × EDGE_KINDS | Scope | D2 | AC4 | ⬜ |
| AC1 | AC | Table+WRITES not bare no_matches | UserNotes shape | | D1,D2 | proving | ⬜ |
| AC2 | AC | Function honest zero unchanged | no unlinked evidence | | D1 | proving | ⬜ |
| AC3 | AC | untouched Table distinguishable | no_matches | | D1 | proving | ⬜ |
| AC4 | AC | matrix fails pre-fix at Table×WRITES | parametrize EDGE_KINDS | | D2 | proving | ⬜ |
| AC5 | AC | hits shape unchanged | linked edge still ok | | D1 | proving | ⬜ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------|
| AC1 | not bare no_matches; names unmeasured relation | relationship_not_modelled | Y | greppable reason | — |
| AC2 | Function path unchanged | no_matches when no unlinked | Y | assert | — |
| AC3 | untouched Table ≠ AC1 | no_matches vs relationship_not_modelled | Y | assert | — |
| AC4 | matrix fails pre-fix Table×WRITES | EDGE_KINDS parametrize | Y | assert != no_matches | — |
| AC5 | hits unchanged | linked REFERENCES still ok | Y | assert | — |

## Inventory (universal "all/every/no")

- **Denominator / total N:** EDGE_KINDS length (12) for Table matrix cells.
- Numbered list: (none beyond matrix)

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

Self-resolved: phase-2 return-hits vs honesty-only → ASSUMED honesty-only (Scope §; DISCLOSURE).

---

## Phase 1 — Analysis

- Root cause (bug, `logic`): `count_unlinked_by_target_raw(..., kinds=UNMODELLED_REFERENCE_KINDS)` ignores WRITES/CALLS/CONTAINS inbound to Table subjects.
- Handler / blast radius: `find_references` empty arm; `UNMODELLED_REFERENCE_KINDS` comment; 232 language-arm precedence when other unlinked kinds exist; related honesty tests.
- `TRACK: backend — 0/0 touched files under UI paths`
- `SCOPE: S`
- `TIER: full`

`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ EDGE_KINDS not PHP pair · R4.2 (change-type) ✅ empty-path only · R5.6 (recalled handle) ✅ honesty ≠ hits · R5.2 (change-type) ✅ reason names unmeasured · R6.5 (change-type) ✅ matrix red-before · R7.5 (change-type) ✅ comments ≤3`

### BASELINE

Related suite on untouched checkout tip:

```
Ran at 8303edb00205ecd15ae88686cc14b263dd2fe4da
$ .venv/bin/python -m pytest tests/test_empty_answer_cannot_explain_itself.py tests/test_relation_unmodelled_for_language.py -q --tb=no
17 passed in 2.02s
```

`BASELINE: green` for the change-adjacent suite. No baseline exclusions.

- Self-audit: sections 6=6; AC falsifiable; j=0; RULE SECTIONS named; TRACK/TIER/SCOPE declared.
- **Gate 1 status:** cleared (autorun closes on artifacts) ✋

---

## Phase 2 — Design

- **Approach.** Replace honesty `kinds=` with `EDGE_KINDS`. Keep `UNMODELLED_REFERENCE_KINDS` for the language-emits reader (186/232). Prefer honesty over the language arm when unlinked evidence of any contract kind exists. Class-shaped subjects keep search_symbol route; others get relation hint only. Prove with UserNotes-shaped fixture + Table×EDGE_KINDS matrix.

- **Rejected alternatives.**
  1. Return unlinked WRITES as `results` hits — rejected: phase-2 ASSUMED honesty-only; R5.6.
  2. New per-kind inbound map in adapters — rejected: R5.6 / 231 class.
  3. Second hardcoded tuple (WRITES/CALLS/CONTAINS) — rejected: R1.1 same defect.

**Assumptions**

| Assumption | verified / novel-untested | If novel-untested → spike / proving test |
|------------|---------------------------|------------------------------------------|
| count_unlinked_by_target_raw accepts EDGE_KINDS | verified | store API + proving |
| Language arm still reachable when unlinked==0 | verified | 232 test branch |

**Smallest change-list**

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| D1 | honesty EDGE_KINDS + unlinked_edge_kinds + hint split | `find_references.py`, `contract.py`, `store.py` | 232 empty-path precedence | G1,C1–C5,R1,AC1–AC3,AC5 | 3/3 |
| D2 | proving + NODE_KINDS×EDGE_KINDS×lang matrix + 232 | `tests/test_find_references_honesty_not_php_shaped.py`, `tests/test_relation_unmodelled_for_language.py` | none beyond named | AC1–AC5,C4 | — |

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| Handle | Answer | Command + result (trimmed) |
|--------|--------|----------------------------|
| empty-answer-must-explain-itself | traced | `rg -n 'kinds=EDGE_KINDS' code_atlas/tools/find_references.py` → honesty arm |
| evidence-shaped-honesty-inverts-on-a-second-instance | traced | proving Table+WRITES → relationship_not_modelled |
| do-not-attest-past-the-payloads-resolution | traced | results stay []; reason names unmeasured |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Verification plan**

| AC | Proof layer | Named command / assertion | ❌? |
|----|-------------|---------------------------|-----|
| AC1 | unit | Table+WRITES → not no_matches | — |
| AC2 | unit | Function untouched → no_matches | — |
| AC3 | unit | orphan Table → no_matches | — |
| AC4 | unit | Table × EDGE_KINDS matrix | — |
| AC5 | unit | linked REFERENCES → ok | — |

**Proving test (named, runnable):**
`.venv/bin/python -m pytest tests/test_find_references_honesty_not_php_shaped.py::test_table_with_unlinked_writes_is_not_bare_no_matches -q`

- **Gate 2 status:** cleared (autorun closes on artifacts) ✋

---

## Phase 3 — Execute

**Branch:** `feat/255-honesty-predicate-not-php-shaped`

**Implemented (approved list only):**
- D1: honesty `kinds=EDGE_KINDS` + `unlinked_edge_kinds` naming; hint split; contract comment; `store.unlinked_kinds_by_target_raw`.
- D2: NODE_KINDS×EDGE_KINDS×{{sql,php}} matrix + 232 precedence assert.

**Verification sweep**

```
diff ⊆ approved list: code_atlas/contract.py, code_atlas/tools/find_references.py, code_atlas/store.py, tests/test_find_references_honesty_not_php_shaped.py, tests/test_relation_unmodelled_for_language.py, docs/tasks/255_*.md, docs/BACKLOG.md, docs/TOKEN_LEDGER.md
Ran at b09378f6e3b1b2bedc343385419008d47ac376bf
$ .venv/bin/python -m pytest tests/test_find_references_honesty_not_php_shaped.py -q --tb=line
340 passed in 18.22s
```

**Design-conformance self-check:** matches D1–D2; no language branch; hits unchanged; WRITES not returned as results.

- **Gate 3 status:** cleared (autorun) ✋

---

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived; no rule-book-grounded review ran.
**CHALLENGER: ON** — ticket-blind, 2 dispatches (round-1 NOT CLEAN on AC1 naming + AC4 matrix axes; round-2 CLEAN after `unlinked_edge_kinds` + NODE_KINDS×EDGE_KINDS×{sql,php}).

Challenger reconstructed 11 requirements from the raw ticket; **11 met / 0 not met / 0 can't tell**. Overall **CLEAN** (challenger only — REVIEWER OFF).

Proving evidence on reviewed tree:
```
Ran at b09378f6e3b1b2bedc343385419008d47ac376bf
$ .venv/bin/python -m pytest tests/test_find_references_honesty_not_php_shaped.py -q --tb=line
340 passed in 18.22s
```

Reviewed at b09378f6e3b1b2bedc343385419008d47ac376bf

- **Gate 4 status:** cleared (challenger CLEAN; reviewer waived)

---

## Phase 5 — Finalise

Durable lesson: none beyond the ticket ACs — the PHP-shaped constant class is already the ticket vocabulary.

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
| reviewer | waived (--no-reviewer) |

### Outward actions
1. push feature branch — authorised by handover
2. open PR — authorised by handover
Deferred to morning: merge; tracker transitions beyond bookkeeping already on branch.
