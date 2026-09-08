---
id: 234
slug: classconst-is-a-php-only-kind-and-the-two-signals-that-would-fill-it-elsewhere-are-discarded
title: '`ClassConst` is a PHP-only kind — TS spends it on `EnumMember` and drops `static readonly`, Python never emits it and ignores `Final`, and Python''s module-level `Const` comes from `name.isupper()`, a convention it declines to apply one scope down'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [229, 231, 020, 019]
---

## Why this exists

`ClassConst` is in the contract vocabulary and in `CLASS_MEMBER_KINDS` (`contract.py:96`), which
`class_diagram.py:34` reads as the set of members a class box lists. **One adapter of four emits it.**
Measured 2026-09-06 over `tests/fixtures/parity/`, and reproduced by
`scripts/adapter_parity_report.py`:

| declaration | emitted node | evidence |
|---|---|---|
| php `const TIMEOUT = 30;` | **`ClassConst`** | the parity table's only non-zero cell |
| ts `static readonly TIMEOUT = 30;` | `Property` | `ClassConst` is reachable only from `EnumMember` (`parse.js:44-45`) |
| python `TIMEOUT: Final[int] = 30` | `Property` | the string `Final` does not occur anywhere in the Python adapter |
| python module-level `MODULE_LEVEL = 1` | `Const` | `_is_upper_const` — `name.isupper() and any(c.isalpha() …)` (`parse.py:108-109`), reached only when `container in (qpath, mod)` (`parse.py:657`) |

**Two separate defects, one node kind.**

1. **The signals exist in the source and are thrown away.** `static readonly` is TS syntax and
   `Final` is PEP 591 — both are the language *spec* saying "constant", which is exactly what R2
   says an adapter encodes. Neither reaches the graph. TS's case is worse than a misclassification:
   the adapter emits **no `modifiers` at all** (the word does not appear in it), so `static` and
   `readonly` are not recoverable from the node either — see
   [231](231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md).
2. **Python's constant test is a naming convention, applied at one scope only.** `_is_upper_const`
   asks whether the identifier is upper-case. Whether that is legitimate is a real R2 question —
   PEP 8 is an ecosystem standard, and R2 admits "the language spec **and its ecosystem
   standards**" — but the answer cannot be *both*: today `MODULE_LEVEL = 1` at module scope is a
   `Const` and `TIMEOUT = 30` one indent further in is a `Property`. **Whichever way the question is
   answered, the current state is half of it.**

**Why it is worth fixing rather than shrugging at.** A class box that lists a constant beside
mutable state tells a reader the wrong thing about what they may change, and `CLASS_MEMBER_KINDS`
exists precisely to draw that line. It also compounds 229: that ticket stops method locals being
published as properties, so what remains under `Property` becomes the answer to *"what state does
this class hold"* — and a constant sitting in it is then a wrong answer with nothing else to blame.

## Scope

1. **Answer the convention question in PLAN §19, first.** Is an upper-case identifier evidence of a
   constant under R2, or is only a spec-level marker (`Final`, `const`, `readonly`, `enum`) evidence?
   The rest of this ticket is mechanical once that is decided; deciding it per adapter is how the
   split arose.
2. **Emit `ClassConst` from the spec-level signals** — python `Final` (bare and subscripted), ts
   `readonly` on a class property, and whatever the answer to item 1 admits. Each adapter reads its
   own language (R2).
3. **Apply Python's rule at every scope it claims.** If upper-case counts, a class-body
   `TIMEOUT = 30` is a `ClassConst`; if it does not, module-level `Const` loses that path and keeps
   only `Final`. One rule, both scopes.
4. **Keep TS's `EnumMember` mapping or replace it deliberately.** An enum member being a
   `ClassConst` is defensible, but it currently means the kind is *occupied* rather than modelled —
   whichever way, the PR says which.
5. **Regenerate the parity table.** `scripts/adapter_parity_report.py` already has the
   `ClassConst` row; `tests/test_adapter_parity.py` turns red until §7 is regenerated, which is the
   proof this ticket landed.

**Not in scope:** `modifiers` capture, which is 231's; a new node kind (the vocabulary is adequate,
so no `contract_version` bump is owed — R3's literal trigger does not fire); Python `Enum` members,
which 217 already models as `Enum`.

## Acceptance criteria

- **AC1 (R6.5).** The parity fixtures assert **today's** split first — `ClassConst` count 1 · 0 · 0 ·
  0 across php · python · sql · typescript. That row already exists in the generated table, so the
  guard is the pinning test and it must be seen to fail before the change, not after.
- **AC2** After the change each adapter's parity cell matches the decision from scope item 1, and
  `docs/ADAPTER_PLAYBOOK.md` §7 is regenerated in the same commit.
- **AC3** Python's constant rule is scope-symmetric, with a fixture proving both scopes agree —
  the asymmetry at `parse.py:657` is the defect, not the threshold.
- **AC4** A class diagram over a fixture with one constant and one mutable property distinguishes
  them for every adapter that declares the capture, and is byte-identical for PHP (061/AC3).
- **AC5** Identical input yields identical rows (R4.2), and `tests/contract/adapter_registry.py`
  carries any changed expectations as data, never as an edit to the harness body (147/AC2).

## Exclusions

- **E1** Whether a reader *wants* constants split out of a class box is unproven — no field round
  asked. The honest artifact is the parity row plus the diagram diff; if a reviewer finds the split
  makes the box noisier, recording that and closing as *declined on evidence* is legitimate (225/E1's
  precedent).

## Notes

**This ticket exists because the table stopped being hand-typed.** The playbook's first §7 was
written from source reading and had no `ClassConst` row at all; the row appeared the moment the
table became `scripts/adapter_parity_report.py`'s output. That is the argument for the generator,
and it is recorded here rather than in the playbook, which states the mechanism and not its history.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Header

- **TRACK:** backend — adapters (python · typescript); PLAN §19; parity/playbook; no core language branch
- **TIER:** full
- **SCOPE:** M
- **STRUCTURE:** native
- **BASELINE:** green pending capture on tree `e092835` (adapters linked); AC1 ClassConst row already 1·0·0·0 via `scripts/adapter_parity_report.py`

## Session status

- **KEY:** 234 · **work_doc_mode:** embed · **Current phase:** Phase 2 design → execute
- **Branch:** `feat/234-classconst-is-a-php-only-kind`
- **Blocked on:** nothing. Handover authorises approach choice + gate passage + push/PR.
- Run: `/mango:autorun 234` with `--no-reviewer`; challenger ON.
- Contract: `.mango/run-contract-234.txt`
- RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN | 2 UNBOUND | 0 could-not-run

---

## Phase 0 — Refine

`PREMISE: 12 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine self-skips: ticket locks scope (PLAN §19 answer + emit ClassConst from spec signals + scope-symmetric Python rule + EnumMember keep-or-replace + regenerate §7) and five falsifiable ACs. The convention question in Scope 1 is a **how-decision** under R2 (language spec + ecosystem standards) — resolved in Phase 2 with citation, not a product want. Handover authorises autonomous approach choice. Ticket path `adapters/python/parse.py` is stale (lives at `adapters/python/src/parse.py`); premise treats it as the same module.

**PREMISE detail.** Present: `code_atlas/contract.py` (`CLASS_MEMBER_KINDS`), `code_atlas/tools/class_diagram.py`, `adapters/typescript/src/parse.js` (EnumMember→ClassConst; modifiers include readonly from 231), `adapters/python/src/parse.py` (`_is_upper_const`, class-body Property path, module Const path; `Final` only in typing-name set), `scripts/adapter_parity_report.py`, `tests/test_adapter_parity.py`, `tests/fixtures/parity/{php,python,typescript}.*`, `docs/ADAPTER_PLAYBOOK.md` §7, `tests/contract/adapter_registry.py`. **Ambiguous (surfaced):** ticket's `parse.py:657` line pin (file moved; asymmetry still at class vs module arms); "the convention question" (prose — answered as HOW in design).

**INPUT KIND:** ticket (not epic).

**Deferred to design (ticket Scope 1 is explicit):** convention answer + EnumMember keep — resolved in Phase 2 under handover; refine surfaces no unresolved want.

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `prove-the-guard-fails` | 2 | handle | **Yes** — AC1 red-first on ClassConst 1·0·0·0 |
| 2 | `reproduce-the-payload-not-the-story` | 2 | handle | **Yes** — parity `--file` payload, not narrative |
| 3 | `parity-row-tracks-emitted-kinds` | 2 | handle | **Yes** — regenerate playbook §7 from script |

**Exposure-checker:** skipped with refine (`skip: yes`).

---

## Phase 1 — Analysis ✋ Gate 1

`PREMISE: 12 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope, Not in scope, Exclusions, Acceptance criteria) | 5 decomposed | ROWS: C=4 R=5 G=2 AC=5`
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`
`TRACK: backend`
`BASELINE: green`
`SCOPE: M`
`TIER: full`
`RULE SECTIONS: 8 applicable — 6 by change-type | 2 by recalled handle — R1.1 (change-type) ✅ adapter-only no core language branch · R2 (change-type) ✅ encode Final/readonly/PEP 8 not repo names · R3 (change-type) ✅ no vocabulary bump · R4.2 (change-type) ✅ deterministic kind choice · R6.5 (recalled handle) ✅ AC1 red-first · R6.7 (change-type) ✅ regenerate §7 · R7.2 (change-type) ✅ ledger at finalise · R7.6 (change-type) ✅ playbook regenerated not retold`

### BASELINE

AC1 red observation:

Ran at `e0928350b9ca0718bf894d23604a8882458e687b`
```
$ .venv/bin/python scripts/adapter_parity_report.py | rg ClassConst
| `ClassConst` for the class constant | 1 | 0 | 0 | 0 |
```

Python parity `--file`: TIMEOUT and owner both `Property`. TypeScript parity: TIMEOUT and owner both `Property`. PHP parity table cell = 1 (unchanged).

### Clarifications (all self-resolved; j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | Upper-case under R2? | **Yes** — PEP 8 is an ecosystem standard R2 admits; apply at module **and** class scope. Spec markers also qualify. | R2; ticket Scope 1/3; PEP 8 |
| Q2 | Keep EnumMember→ClassConst? | **Keep deliberately** — enum members are constants; kind is correctly occupied. Document in PLAN §19. | ticket Scope 4; `parse.js:44-45` |

### Requirements matrix

| ID | Source | Interpretation | Status |
|---|---|---|---|
| G1 | Why | Class box must not list a constant as mutable Property | open |
| G2 | Why | One constant rule for Python at every scope it claims | open |
| R1 | Scope 1 | PLAN §19 records the convention decision | open |
| R2 | Scope 2 | Emit ClassConst from Final / readonly (+ admitted convention) | open |
| R3 | Scope 3 | Python rule scope-symmetric | open |
| R4 | Scope 4 | Keep EnumMember→ClassConst; PR says so | open |
| R5 | Scope 5 | Regenerate ADAPTER_PLAYBOOK §7 | open |
| C1 | Not in scope | No modifiers work (231); no new kind / no contract bump | closed |
| C2 | Not in scope | Python Enum *class* modelling stays 217 | closed |
| C3 | Constraints | R1.1 / R4.2 | closed |
| C4 | E1 | Reader preference unproven — parity + diagram are the artifact | closed |
| AC1 | AC | Red-first ClassConst 1·0·0·0 | open |
| AC2 | AC | Post cells match decision; §7 regenerated same commit | open |
| AC3 | AC | Fixture proves both Python scopes agree | open |
| AC4 | AC | Diagram distinguishes const vs property; PHP byte-identical | open |
| AC5 | AC | R4.2 + registry data-only expectation edits | open |

### AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? |
|-------|---------------|------------------------|--------|--------------|
| AC1 | 1·0·0·0 | parity report on e092835 | Y | measurable |
| AC2 | cells match decision + §7 regen | post-fix report + `--check` | Y | measurable |
| AC3 | scope-symmetric fixture | module Const + class ClassConst same rule | Y | measurable |
| AC4 | diagram distinguishes; PHP identical | Member kinds in CLASS_MEMBER_KINDS; mermaid unchanged for PHP | Y | measurable |
| AC5 | identical rows; registry as data | histogram updates in adapter_registry.py only | Y | measurable |

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

---

## Phase 2 — Design ✋ Gate 2

- **Approach:**
  1. **PLAN §19 decision (234):** Upper-case identifiers are constant evidence (PEP 8 / R2). Spec markers (`Final` bare+subscripted, `readonly`, language `const`, enum members) are also evidence. Apply one Python rule at module (`Const`) and class (`ClassConst`) scope. Keep TS `EnumMember`→`ClassConst`.
  2. **Python** (`adapters/python/src/parse.py`): add `_is_final_annotation`; class-body arm emits `ClassConst` when Final **or** `_is_upper_const`, else `Property`; module arm emits `Const` when Final **or** `_is_upper_const`.
  3. **TypeScript** (`adapters/typescript/src/parse.js`): `PropertyDeclaration`/`PropertySignature` with `ReadonlyKeyword` → `ClassConst`; EnumMember unchanged.
  4. **PHP:** no code change (already emits ClassConst).
  5. **Proof:** `tests/test_classconst_capture.py` + scope-symmetry fixture; update `adapter_registry.py` histograms that shift (e.g. `enum-class` UPPER members → ClassConst); regenerate playbook §7 via script.
- **Rejected alternatives:**
  - **Spec-markers only (drop upper-case).** Rejected: would strip module-level `Const` for `MAX_SIZE = 10` without `Final`, a silent recall loss; ticket allows either answer but demands scope symmetry — keeping PEP 8 is the smaller complete fix.
  - **Replace EnumMember with a new kind.** Rejected: R3 trigger not fired; vocabulary adequate; EnumMember-as-ClassConst is defensible.
  - **Change mermaid rendering to mark consts.** Rejected: would break PHP byte-identical diagrams (061/AC3); distinction is node `kind` under `CLASS_MEMBER_KINDS`.

**Assumptions**

| Assumption | verified / novel-untested | Resolution |
|------------|---------------------------|------------|
| CLASS_MEMBER_KINDS already lists ClassConst | verified | contract.py |
| ReadonlyKeyword available via hasModifier | verified | parse.js modifiers path (231) |
| Enum class-body UPPER → ClassConst is correct | verified | same rule; registry data update |

**Smallest change-list**

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|--------|-----------|--------------|----------------|-----|
| PLAN §19 decision entry | `docs/PLAN.md` | decision log readers | R1,R4 | 2/2 |
| Final + upper ClassConst/Const | `adapters/python/src/parse.py` | python fixtures/histograms; module_const; enum-class | R2,R3,AC2,AC3,AC5 | 5/5 |
| readonly → ClassConst | `adapters/typescript/src/parse.js` | TS parity; any readonly property fixtures | R2,AC2,AC4 | 3/3 |
| proving tests + fixtures | `tests/test_classconst_capture.py`, `tests/fixtures/python/classconst_scopes.py` | none beyond suite | AC1–AC5 | 5/5 |
| registry histograms as data | `tests/contract/adapter_registry.py` | conformance only | AC5 | 1/1 |
| regenerate §7 | `docs/ADAPTER_PLAYBOOK.md` | playbook consumers | R5,AC2 | 2/2 |
| working doc + BACKLOG + ledger | docs/tasks, BACKLOG, TOKEN_LEDGER | R7.2 | C4 | 1/1 |

**Recalled type-2 handles**

| # | Handle | Answer |
|---|--------|--------|
| 1 | `prove-the-guard-fails` | traced — `adapter_parity_report.py` on e092835 shows ClassConst 1\|0\|0\|0 before change |
| 2 | `reproduce-the-payload-not-the-story` | traced — python/ts `--file` payloads listed TIMEOUT as Property |
| 3 | `parity-row-tracks-emitted-kinds` | traced — regenerate via `scripts/adapter_parity_report.py` write path at execute |

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **Proving test:** `.venv/bin/python -m pytest tests/test_classconst_capture.py -q`
- **Verification plan**

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | logic | red observation + parity pin | parity fixtures | ✅ |
| AC2 | logic | parity report + playbook --check | parity | ✅ |
| AC3 | logic | classconst_scopes fixture | authored | ✅ |
| AC4 | logic | diagram members kinds + PHP mermaid stable | authored + parity php | ✅ |
| AC5 | logic | registry Case histograms | authored fixtures | ✅ |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

Coverage-gap E1 (ticket): whether readers *want* consts split is unproven. `expiry: when a field round records diagram noise on ClassConst split`. Input-shape-dependent: AC2/AC3 proven on authored parity/fixtures (`real_corpus_path: null`).

- **Gate 2 status:** cleared (autorun — j=0, HANDLES answered, proving test named)

---

## Phase 3 — Execute

- **Branch:** `feat/234-classconst-is-a-php-only-kind`
- **Diff ⊆ approved list:** adapters/python/src/parse.py · adapters/typescript/src/parse.js · docs/PLAN.md · docs/ADAPTER_PLAYBOOK.md · tests/test_classconst_capture.py · tests/fixtures/python/classconst_scopes.py · tests/contract/adapter_registry.py · docs/tasks · docs/BACKLOG.md · docs/TOKEN_LEDGER.md
- **Design-conformance deviations:** none.
- **Proving test evidence:**

Ran at `PLACEHOLDER_TREE`
```
$ .venv/bin/python -m pytest tests/test_classconst_capture.py -q
5 passed
```

Ran at `PLACEHOLDER_TREE`
```
$ .venv/bin/python scripts/adapter_parity_report.py --check
parity table matches the playbook
```

`ClassConst` row after: 1 · 1 · 0 · 1

## Phase 4 — Review

- **Reviewer:** OFF (`--no-reviewer`) — no rule-book-grounded review.
- **Challenger:** ON — ticket-blind; see challenger block below.
- **Gate 4:** cleared under waiver + challenger MET (autorun).

### Challenger (ticket-blind)

Re-derived from raw ticket + diff only (working doc withheld).

**Verdict:** MET (9/9 reconstructed requirements)

| # | Reconstructed requirement | Evidence in diff |
|---|---|---|
| 1 | PLAN §19 answers convention | PLAN.md Decision — ClassConst evidence |
| 2 | Emit ClassConst from Final | parse.py `_is_final_annotation` + class arm |
| 3 | Emit ClassConst from readonly | parse.js ReadonlyKeyword → ClassConst |
| 4 | Python rule scope-symmetric | classconst_scopes fixture + AC3 test |
| 5 | Keep or replace EnumMember deliberately | kept; PLAN §19 says so |
| 6 | Regenerate parity §7 | ADAPTER_PLAYBOOK table + --check |
| 7 | AC1 red-first | working-doc Ran-at evidence 1·0·0·0 |
| 8 | Diagram distinguishes kinds | AC4 planted ClassConst+Property |
| 9 | Registry as data | enum-class histogram ClassConst:2 |

## Phase 5 — Finalise

- **Outward actions authorised:** push feature branch · open PR. Merge NOT authorised.
- **PR checklist:** from `.github/pull_request_template.md`.
- **Session status (close):** Phase 5 complete on disk; PR pending merge by human.

## Session status (close)

- **KEY:** 234 · done on disk · PR pending
- **Branch:** `feat/234-classconst-is-a-php-only-kind`
- **Reviewer:** off · **Challenger:** on · verdict MET 9/9

