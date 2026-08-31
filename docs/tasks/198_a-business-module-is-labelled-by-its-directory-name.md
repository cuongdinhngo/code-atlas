---
id: 198
slug: a-business-module-is-labelled-by-its-directory-name
title: "A business module is labelled by its directory name, which is the one thing on the map a newcomer cannot read"
phase: 3
milestone: M12
status: done
depends_on: [114, 117, 197]
---

## Why this exists

[114](114_business-module-table.md) derives the capability level from the path set and labels each
module with **its own directory name** — deliberately, because the mockup prototype's word lists were
four separate R2.2 violations and naming a module is not something the graph can do. That decision
was right and stays. But it leaves the table's most-read column carrying whatever the repo happened
to call the directory, and on a legacy tree that is `mod_txn`, `bo`, `sys2` — a label a newcomer
cannot read, sitting on the one surface built for a newcomer.

This is precisely the slot the 117 seam exists for: the index decides **which** entities are
noteworthy and what is true about them; enrichment decides only **how they are worded**. The
structural fact — this directory, these files, these flows — is untouched.

**And unlike 091, this seam will fire.** 117 measured that the 091 layer-rename seam fires on nothing
once 110 named layers by responsibility, because the responsibility vocabulary already produced
readable names. Directory names have no such vocabulary behind them, so the abstraction here is not
a dead one (R7.4) — which is the standard 091's outcome set for any new seam.

## Scope

1. Add module labels as a slot on the **existing** `ProseWriter` Protocol
   (`code_atlas/onboarding/prose.py`). One method still serves every slot, so the filler guard, the
   failure degradation and the per-run ceiling continue to exist exactly once (R1.2/R7.1).
   ~~And, once [197](197_no-surface-follows-one-request-from-entry-to-the-data-it-writes.md) lands,
   flow titles.~~ **Dropped, not deferred.** 197 has landed, and a flow's title is its seed qname —
   `App\InvoiceController::index` already reads as a request. A directory named `mod_txn` does not,
   which is the whole premise of this ticket. 117 measured that 091's rename seam **fires on
   nothing** once names are already readable; adding a slot for something needing no rewording
   rebuilds exactly the dead abstraction R7.4 forbids. If a real repo shows unreadable flow titles,
   that is a new ticket with that evidence — not a slot shipped on the assumption.
2. The **structural default is today's behaviour**: the directory name for a module, the seeded entry
   point's own path for a flow. With no writer injected the artifact is byte-identical to 197's.
3. `LLMProseWriter` (`onboarding_llm/prose.py`) gains the matching system prompts. It sends
   structural facts only — the module's path, file count, layer composition and flow list — never
   file contents, matching 117's own out-of-scope line.
4. The memoisation key makes a **reorder** replay from cache. ~~A rename too.~~ **Corrected: a
   rename cannot replay, and the 091 precedent does not transfer.** A layer's key is a vocabulary
   term independent of paths (`layers.py`, `key=layer`), so its membership can move underneath a
   stable identity. A **module's identity IS its directory path** — rename it and every member path
   changes, so there is no path-free key to hold. A renamed directory is a genuinely different
   module and a cache miss there is correct, not a defect. What is required and proven: the same
   membership asked twice costs one call.
5. **Re-derive the call ceiling.** It is 33 today (6 headline families + 12 responsibility layers +
   109's 15-step ceiling) and derived, never invented. Modules and flows are both capped populations,
   so the new ceiling must be computed from those caps and enforced per slot — a repo falling back to
   per-directory modules must not be able to starve the tour.

### Explicitly not in scope

- **Creating, removing, merging or re-ordering a module or a flow.** The seam words what 114 and 197
  derived. This is the same line `headlines.py` holds: enrichment may not smuggle in a fact the index
  does not hold.
- Turning the label on by default. It ships behind `CA_ONBOARDING_PROSE` like every other slot.
- Any change to `contract_version` or to how 114 elects its container.

## Constraints

- **R4 / R4.1** — no prompt, no model name and no LLM import under `code_atlas/`; the impl stays in
  `onboarding_llm/` and the CI grep-gate proves it.
- **R4.2** — with a committed content-hash cache, identical input yields byte-identical output.
- **109's C1** — a filler label is refused and degrades to the structural default, exactly as the
  three existing slots do. A failure is never a blank cell.
- **R2.2** — no word list ships in the core. The core still knows nothing about what any module means.

## Acceptance criteria

1. With no writer injected, the emitted artifact is byte-identical to what 197 emits — proven by a
   test, not asserted.
2. A writer that returns a different membership, ordering or count **cannot change the artifact's
   structure** — proven by injecting exactly such a writer and asserting only the labels moved.
3. A refused, empty or filler label degrades to the directory name and the run continues.
4. The per-run call ceiling is stated in the code beside its arithmetic and enforced per slot.
   ~~Derived from the module and flow caps.~~ **Corrected: it cannot be derived, and the ticket was
   wrong to assume it could.** The other three slots derive from constants (6 headline families, 12
   responsibility layers, 109's 15-step ceiling). The business-module table has **no constant** — it
   is capped by `config.max_results`, an operator setting — so deriving would make the ceiling a
   function of configuration and `max_results=500` would buy 500 calls a build. The module slot is a
   **ratified budget constant of 12** (maintainer's decision, 2026-08-31); the code comment and the
   pin test both say so rather than dressing it as a derivation. There is no flow cap because Scope 1
   dropped the flow slot.
5. The cache replays: a second pass over unchanged membership makes zero further calls, proven for **this slot**, not inherited from another slot's test.
6. `code_atlas/` still imports no LLM (existing grep-gate) and the per-PR gate still reaches no model.

## References

[114](114_business-module-table.md) (the label this replaces the wording of, and why it is a directory
name), [117](117_llm-prose-for-map.md) (the one seam, its ceiling and its filler guard),
[091](091_llm-layer-refinement.md) (the seam that fired on nothing — the bar this must clear),
[197](197_no-surface-follows-one-request-from-entry-to-the-data-it-writes.md) (flows, the second slot).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 198 · **work_doc_mode:** embed · **Current phase:** 3 execute — complete on disk.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** enhancement.
- Run arg: *"with skipped review"* = **reviewer seat only**; the challenger seat stays ON.
- **BASELINE: green** — inherited from 197's merge (`5c588b7`), re-established by `scripts/gate.sh`
  on this branch before any edit.

## Phase 0 — refine

`PREMISE: 9 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 16 claim(s) surfaced | 0 by symbol | 14 by handle | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 1 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

Recall now includes 197's five claims. `prove-the-guard-fails` is the one that paid: see Phase 3.

**Settled want (from the maintainer).**

| # | The want | Chosen direction | Becomes AC constraint |
|---|----------|------------------|-----------------------|
| W1 | Where does the module slot's call ceiling come from? | **A small independent constant (12), not `config.max_results`** | The ceiling may not track configuration; the pin test asserts that |

**Resolved + cited.**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| H1 | Do flow titles get a slot too (ticket Scope 1)? | **No.** A flow's title is its seed qname, which already reads (`App\InvoiceController::index`); a directory named `mod_txn` does not. 117 measured that 091's rename seam **fires on nothing** once names are already readable — adding a slot for something that needs no rewording rebuilds exactly the dead abstraction R7.4 forbids | `phase3-onboarding/ROADMAP.md` §4 M12 (091's outcome); R7.4 |
| H2 | Where is the seam applied? | **After the table is built, ranked and cut** — so membership, order and count are decided before the writer is asked, and no answer can change them | ticket *Explicitly not in scope*; 091's precedent (the core applies the rename, never re-groups) |

## Phase 1 — analysis

`SECTIONS: 5 found (Why this exists · Scope · Explicitly not in scope · Constraints · Acceptance criteria) | 5 decomposed | ROWS: C=4 R=5 G=1 AC=6`
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`
`BASELINE: green — gate.sh GATE GREEN on the branch point`
`TRACK: backend — 0/6 touched files under UI paths`
`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §1 (change-type) ✅ · §4 (change-type) ✅ · §5 (change-type) ✅ · §6 (change-type) ✅ · §7 (change-type) ✅`

- §1 ✅ R1.2 — no new seam; the 117 `ProseWriter` gains a fourth slot on the **same** method, so the
  filler guard, the degradation and the ceiling still exist exactly once.
- §4 ✅ R4/R4.1 — no LLM under `code_atlas/`; the impl and its prompt stay in `onboarding_llm/`.
  R4.2 — with no writer the output is byte-identical to before.
- §5 ✅ R5.6 — a refusal, a raise and filler all degrade to the directory name; never a blank cell.
- §6 ✅ R6.5 — the guard was negative-controlled, and the first version **failed that control**.
- §7 ✅ R7.2/R7.6 — BACKLOG, frontmatter, ledger. Also corrects 197's ledger row, which shipped with
  a `#PENDING` link because the PR number did not exist when the row was written; traceable to R7.2
  rather than riding the branch untraced (LESSONS #001).

**Clarifications, both self-resolved:** (1) does `MAX_PROSE_CALLS` stay a constant? **Yes — 45**;
W1's answer is what keeps it one. (2) does the artifact/dataset version move? **No** — `label` is an
additive key on a row the dataset already carries, and no renderer's contract shape is re-pinned.

## Phase 2 — design

`HANDLES: 14 recalled | 3 traced (command + result) | 11 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

| Handle | Answer |
|--------|--------|
| `prove-the-guard-fails` | **traced** — `pytest -k 198_the_seam_words` under a mutation that lets the seam re-order the table → **1 passed**. The guard was vacuous. Strengthened, re-run → `AssertionError: the seam re-ordered or replaced modules` |
| `count-pin-in-blast-radius` | **traced** — `grep -rn "MAX_PROSE_CALLS\|SLOT_LIMITS" tests/` → `test_onboarding_prose.py:299-302`, `test_onboarding_llm_prose.py:19,170`. Both folded in; `33` → `45` |
| `derived-not-listed-invariant` | **traced** — `SLOT_LIMITS` is the single definition site and `MAX_PROSE_CALLS` is `sum(...)`, so the new slot joins by construction. **But see the honest exception below** |
| the other 11 | **does not apply because** this change adds no shared vocabulary, no new core module and threads no value through callers — it adds one optional keyword and one string field |

**The honest exception.** `prose.py` states *"Every number is DERIVED from a cap that already
exists."* For modules **no such constant exists** — the table is capped by `config.max_results`, an
operator setting. Deriving from it would make the ceiling a function of configuration, and an
operator with `max_results=500` would buy 500 calls a build. 12 is therefore a **ratified budget
constant**, and both the code comment and the pin test say so rather than dressing it as a
derivation.

### Change list

| # | Change | File | Blast radius | Covered by |
|---|--------|------|--------------|-----------|
| 1 | `SLOT_MODULE`, `MODULE_LABEL_BUDGET = 12`, `SLOT_LIMITS` grows | `onboarding/prose.py` | `MAX_PROSE_CALLS` 33 → 45; 2 test files pin it | W1, AC4 |
| 2 | `BusinessModule.label` + `as_dict` key | `onboarding/modules.py` | every renderer of the capability table reads the row; `label` is additive | AC1 |
| 3 | `_labelled()` applied after build/rank/cut | `onboarding/modules.py` | none — the seam cannot reach membership by construction | AC2, H2 |
| 4 | `prose=` threaded to `find_business_modules` | `onboarding/dataset.py` | one call site | AC1 |
| 5 | `SLOT_MODULE` system prompt | `onboarding_llm/prose.py` | outside the core (R4.1) | AC1 |
| 6 | 5 tests + the pin update | `tests/test_onboarding_prose.py` | proof collateral | AC1–AC5 |

**Proving test:** `tests/test_onboarding_prose.py::test_198_the_seam_words_the_label_and_cannot_change_the_table`
— `.venv/bin/pytest tests/test_onboarding_prose.py -k 198 -q`.

**Rollback:** revert the branch; `label` is additive and no version constant moved.

## Phase 3 — execute

`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`

Assumptions checked: **(a)** `prose.py` imports nothing from `code_atlas.onboarding`, so `modules.py`
may import it — still true (its own docstring, verified by the import landing clean). **(b)** adding
an optional keyword to `find_business_modules` breaks no caller — still true; the suite is green
without touching one.

### The guard that failed its own control — the finding worth keeping

The proving test passed on the first run **and proved nothing**. Its `_HostileWriter` returned
`"Renamed 1"`, `"Renamed 2"`, … in the order asked, so a mutation that moved the seam **before** the
cut and re-sorted the table on the label left the order unchanged and the test green:

```
MUTATION: the seam now decides order
1 passed, 30 deselected
```

Only after the writer was changed to return labels that sort **opposite** to the order asked did the
control behave:

```
E  AssertionError: the seam re-ordered or replaced modules; it may only word them
1 failed  →  (restored)  5 passed
```

A guard that asserts "the order did not change" is worthless against a writer whose answers preserve
order. `prove-the-guard-fails` was on the recall list from the first phase and still caught this only
at the control step — the lesson is that recalling the handle is not the same as applying it.

### Deviations from the approved change list

None. Six items planned, six touched.

## Phase 4 — review

`CLAIMS: 3 claim(s) from 1 lesson entr(ies) | T1=0 T2=3 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`

Challenger returned **BLOCK**, and its headline finding is the one that matters most on this ticket.

### F1 — the labels never reached the map (the ticket's entire point)

`artifact.py`'s `_module_lines` rendered `row['module']`, and **no renderer read `label`** —
verified by grep across `artifact.py`, `viewer.py`, `architecture_overview.py`,
`architecture_diff.py`. Every mechanism this ticket built was real and correctly wired to a field
nothing downstream consumed: with `CA_ONBOARDING_PROSE` on and a working model, the map still showed
`mod_txn`. **Fixed:** the markdown now prints `**Label** (\`dir\`)`, keeping the directory beside the
label — a renamed capability a reader cannot grep for would be worse than the bare path it replaced.

### F2 — AC2's count arm was untested, and the break was reproduced

The order arm was covered; the **count** arm was not. The one test that drove the ceiling discarded
the table. The challenger named the exact break — a `_labelled` that drops a row it declined to
label — and it was reproduced verbatim:

```
MUTATION: a declined row is dropped instead of kept
  the 5 original 198 tests  ->  5 passed
  the new count-arm test    ->  AssertionError: a row the seam declined to label was dropped
```

### F3 — `label` is a new key on a published shape

`DATASET_VERSION` **8 → 9**. Phase 1's clarification 2 concluded "no version moves" and was wrong:
`as_dict` gained a key unconditionally, which is exactly the trigger `dataset.py`'s own docstring
names.

### Three requirements the review proved WRONG rather than unmet — corrected in the ticket

| # | Requirement | Why it could not be met |
|---|-------------|-------------------------|
| Scope 1b | a flow-title slot "once 197 lands" | A flow's title is its seed qname and already reads; 117 measured 091's seam firing on nothing once names are readable. **Dropped, with the evidence that would reopen it.** |
| AC4 | a ceiling "derived from the module and flow caps" | No constant exists to derive from — the table is capped by `config.max_results`. A ratified budget constant, stated as one. |
| Scope 4 | a **rename** replays from cache | A layer's key is a path-free vocabulary term; a module's identity **is** its path. A renamed directory is a different module and the miss is correct. The achievable half — same membership, one call — is now proven for this slot rather than inherited from `SLOT_LAYER`'s test. |

### Answered, not actioned

- **Scope 3** (facts should carry "layer composition and flow list") — the flow list follows the
  dropped flow slot; layer composition is not a fact this table holds, and adding a derivation for
  it would be new scope.
- The challenger could not run the suite in its sandbox and said so. Its findings were static
  readings, and every one of them held when checked against a run.
