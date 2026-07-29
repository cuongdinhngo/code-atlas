---
id: 002
slug: contract-schema
title: The contract — schema, version, validation
phase: 1
milestone: Contract
status: done
depends_on: [001]
---

## Goal
Define the single seam between core and adapters as a versioned, validated artifact (§4).

## Scope / Deliverables
- `contract.py`: node kinds (`File Namespace Class Interface Trait Enum Function Method Property ClassConst Const`) and edge kinds (`CONTAINS EXTENDS IMPLEMENTS USES_TRAIT CALLS NEW IMPORTS INCLUDES REFERENCES`).
- Node/edge field definitions; `confidence_tier ∈ {RESOLVED, HEURISTIC, DYNAMIC}`.
- Qualified-name convention documented + helpers.
- `contract_version` constant + capability-flags shape (e.g. `semantic_types`).
- A `validate(result)` function usable by both the indexer and the conformance tests.

## Acceptance criteria
- `validate()` accepts a known-good `{path, ok, nodes, edges}` and rejects malformed shapes with clear errors.
- Version constant exported; schema is the sole source of truth (no field lists duplicated in store/indexer).

## References
Plan §4 (4.1 protocol, 4.2 schema, 4.3 abstraction, 4.4 contract v2 note).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 002 — The contract: schema, version, validation (working doc)

- **Ticket:** 002 · docs/tasks/002_contract-schema.md · repo https://github.com/cuongdinhngo/code-atlas
- **Type:** enhancement (greenfield module — `contract.py` is a 1-line stub today)
- **Repo(s) / Porting:** `app` (`.`) — single repo, no porting
- **SCOPE:** M
- **STRUCTURE:** native (headers map to `ticket_header_schema`; `References` is an unmapped informational pointer, same as task 001)
- **TRACK:** backend (`config.track=backend`; 0/N touched files under UI paths — pure Python core + tests)
- **TIER:** full (SCOPE=M, 5 R-rows + 2 ACs, universal requirement with N=40 > 1 → not lite-eligible)
- **work_doc_mode:** `embed` (config) — ticket is a repo-local file, so the working doc is appended
  below the separator above; matches task 001. Challenger gets only the raw ticket text above the line.
- **BASELINE:** **green**
  - `pytest -q` → **1 passed** · `ruff check .` → **All checks passed** · `mypy code_atlas` → **no issues (11 source files)** · `git status` clean.
  - **Toolchain caveat (detect-not-assume):** the host had **no** `pytest`/`ruff`/`mypy` on PATH. Baseline was
    run after installing the project's own declared `[dev]` extra into a gitignored `.venv/`
    (`uv venv .venv && uv pip install -e ".[dev]"`; `.venv/` and `*.egg-info/` are in `.gitignore:11-12,17`),
    so the checkout stayed clean. Commands below therefore run as `.venv/bin/<tool>`.
  - baseline exclusions (pre-existing failures outside this change): **none**.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Acceptance criteria, References) | 4 decomposed | ROWS: C=0 R=5 G=1 AC=2`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | "Define the single seam between core and adapters as a versioned, validated artifact (§4)." | Make `code_atlas/contract.py` the executable single source of truth for the adapter seam: vocabulary + fields + version + validation. Today the seam exists only as prose. | `contract.py` is a 1-line docstring stub (`code_atlas/contract.py:1`); vocabulary lives only in `docs/PLAN.md:87-99` + `docs/CONVENTION.md:53-65` | 9/9 (all change-list items) | `contract.py` is the seam in code: 16 public symbols, `34 passed`, `mypy` clean over 11 files | ✅ |
| R1 | Scope | "`contract.py`: node kinds (`File Namespace Class Interface Trait Enum Function Method Property ClassConst Const`) and edge kinds (`CONTAINS EXTENDS IMPLEMENTS USES_TRAIT CALLS NEW IMPORTS INCLUDES REFERENCES`)." | Declare the **11** node kinds and **9** edge kinds as constants in `contract.py`, spelled exactly as in CONVENTION §3. Counted "for each of N" → per-item checklist (Inventory 1, items 1-20). | Same 11+9 spellings in `PLAN.md:88,91` and `CONVENTION.md:55-56`; zero of them exist in code (`grep -c 'USES_TRAIT' code_atlas/` → 0) | 2/2 (items 2, 7) | `contract.py:19,33`; asserted item-by-item at `test_contract_schema.py:55,71` (inventory 1 rows 1-20 all ✅) | ✅ |
| R2 | Scope | "Node/edge field definitions; `confidence_tier ∈ {RESOLVED, HEURISTIC, DYNAMIC}`." | Declare the **10** node fields, **7** edge fields, and the **3** confidence tiers (Inventory 1, items 21-40). | `PLAN.md:89,92` (fields) · `PLAN.md:92`/`CONVENTION.md:57-59` (tiers) · SQLite mirror `PLAN.md:254-268` | 2/2 (items 3, 7) | `contract.py:45,47,60,73,80`; asserted at `test_contract_schema.py:85,89,104,116,121` (inventory 1 rows 21-40 all ✅) | ✅ |
| R3 | Scope | "Qualified-name convention documented + helpers." | Document the qname convention **in `contract.py`** (docstring pointing at CONVENTION §3, not a second normative copy) and ship qname helper(s). Helper *set* is a Gate-2 decision, bounded by R7.4/R1.2 (no helper without a named near-term consumer). | Convention documented at `CONVENTION.md:60-64` + `PLAN.md:94-95`; no helper exists in code | 4/4 (items 1, 5, 7, 9) | docstring `contract.py:1-14`; `MEMBER_SEPARATOR` + helpers `contract.py:93,96,107`; `test_contract_schema.py:141-163`; docs pinned @ `9d6191e` | ✅ |
| R4 | Scope | "`contract_version` constant + capability-flags shape (e.g. `semantic_types`)." | Export a `CONTRACT_VERSION` constant and define the capability-flags shape (`{"semantic_types": true}`-style, per ISP R1.6 — advertised, never required). | `PLAN.md:97` (flags example), `PLAN.md:99` (versioned in meta), `PLAN.md:113-118` (v2 anticipated → integer series), rulebook R1.6 | 2/2 (items 4, 7) | `CONTRACT_VERSION` `contract.py:16`, `Capabilities`/`KNOWN_CAPABILITIES` `contract.py:90-91`; `test_contract_schema.py:130,134` | ✅ (see caveat 1) |
| R5 | Scope | "A `validate(result)` function usable by both the indexer and the conformance tests." | One `validate()` in `contract.py` consumed by **two** callers: `indexer.py` (per-file adapter result, must not break the stream — R5.1) and `tests/contract/` (R3.4 conformance). Its call/return shape is a Gate-2 decision constrained by both callers. | Both callers are stubs today (`indexer.py:1`, `tests/contract/.gitkeep`); R5.1/R5.3 + R3.4 constrain the shape | 2/2 (items 6, 7) — conformance-caller half proven; **indexer half is a recorded coverage-gap exclusion** → task 009 | `validate()` `contract.py:112`; the conformance suite **is** the second caller (`test_contract_schema.py:166`); non-raising shape proven at `:273` | ✅ for the shipped half · ⚠ indexer half excluded → task 009 |
| AC1 | AC | "`validate()` accepts a known-good `{path, ok, nodes, edges}` and rejects malformed shapes with clear errors." | Good 4-key payload → validates with no error; malformed payloads → rejected. **"clear" pinned at Gate 1 (Q1 → option a):** every rejection names the offending key path **and** what was expected; one asserted case per malformation class (5 classes). | Good/bad shapes both illustrated at `PLAN.md:82-84` (incl. the `ok:false` + `error` variant) | 2/2 (items 6, 7 — item 7 holds the proving test) | **proving test** `test_contract_schema.py:190` red→green; 5/5 malformation classes at `:190,201,211,222,231` | ✅ |
| AC2 | AC | "Version constant exported; schema is the sole source of truth (no field lists duplicated in store/indexer)." | (a) `CONTRACT_VERSION` importable from `contract.py`; (b) no field-list literal re-declared in the schema-consuming core modules (R3.2). **Q2 → durable test:** clause (b) is proven by a committed test (not a point-in-time grep, not a new CI gate) asserting the 5 consumers carry no re-declared vocabulary. Per-item checklist = Inventory 2. | `store.py:1`, `indexer.py:1`, `resolver.py:1`, `adapter.py:1`, `tools/__init__.py:1` are all 1-line stubs → 0 duplications now; R3.2 is the standing rule | 3/3 (items 4, 7 → AC2(a); item 8 → AC2(b)) | (a) `test_contract_schema.py:130`; (b) `test_contract_sole_source.py:58` over 5 consumers + non-vacuity guard `:51`, negative-controlled | ✅ |

Status legend: ✅ done/proven · ⚠ deferred (needs follow-up ticket) · ❌ not met.

> ⚠ **`Ph3/4 proven by` is EXECUTE-SELF-REPORTED, not reviewer-verified.** Phase 4 (review) was
> **skipped by explicit user decision**, so no `reviewer` and no ticket-blind `challenger` independently
> re-derived these requirements or re-ran these proofs. Every cell below cites a test that was actually
> run (`34 passed`), but the check that a self-reported `✅` matches reality was not performed by a second
> party. Treat the `✅`s as *"the author's evidence"*, not *"an independent verdict"*.

**`References` section decomposition:** informational pointer (Plan §4.1-4.4), no independent requirement.
It is consumed as the authority behind R1-R5 (each row cites it) and as the forward-compatibility note:
§4.4 says TS/JS will force a v2 protocol, so `CONTRACT_VERSION` must be a bumpable series (→ R4) and
the v1 shape must stay **file-at-a-time** (`PLAN.md:114`). No matrix row of its own.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 (a) | good result has keys `{path, ok, nodes, edges}` | **4** top-level keys, confirmed against the protocol sample at `PLAN.md:83`. The **error** variant is `{path, ok:false, error}` (`PLAN.md:84`) — 3 keys, also a *valid* result, not a malformed one | **Y** | ✅ measurable — key-set assertion over both documented variants | none |
| AC1 (b) | "rejects malformed shapes with **clear errors**" | rejection itself is measurable (a malformed payload must not validate); **"clear" had no measurable definition** in ticket, rulebook, or CONVENTION → raised as Q1 | Y (no value to mismatch) | ✅ **now falsifiable — bar ratified by the user at Gate 1 (Q1 option a)** | **RESOLVED:** every rejection must name (i) the offending field/key path (e.g. `nodes[0].kind`, `nodes[3].qualified_name`) and (ii) what was expected (allowed kind / required field / type). Asserted by test on **one case per malformation class**: unknown node kind · unknown edge kind · missing required field · wrong top-level shape · bad `confidence_tier`. Worked example the user approved: `nodes[0].kind: 'Klass' is not an allowed node kind (expected one of File, Namespace, Class, Interface, Trait, Enum, Function, Method, Property, ClassConst, Const)` |
| AC2 (a) | "Version constant exported" | `from code_atlas.contract import CONTRACT_VERSION` succeeds and is non-empty | **Y** | ✅ measurable — import + assertion | none |
| AC2 (b) | "no field lists duplicated in store/indexer" | Today **0** duplications — all 5 schema-consuming modules are 1-line stubs, so the clause is **vacuously true**; grep for any of the 17 field names in `store.py`/`indexer.py` → 0 hits | **Y** (computed 0 = ticket's 0) | ✅ **falsifiable and non-vacuous — bar ratified at Gate 1 (Q2 option a)** | **RESOLVED:** ship a **durable test** (e.g. `tests/test_contract_sole_source.py`) asserting none of the 17 field names / 20 kind literals is re-declared as a list in the 5 consumers (Inventory 2) — they must import from `code_atlas.contract`. Lives inside `config.test_command`, so tasks 004/009 hit it on duplication. **Explicitly not** a point-in-time grep and **not** a new CI gate (which would need `codify` ratification). |
| R1/R2 counts | 11 node kinds · 9 edge kinds · 3 tiers · 10 node fields · 7 edge fields | Re-derived independently from `PLAN.md:88-92` **and** `CONVENTION.md:55-59`: node kinds **11**, edge kinds **9**, tiers **3**, node fields **10**, edge fields **7** — the two docs agree, and the ticket's R1 list matches spelling-for-spelling | **Y — no mismatch** | ✅ greppable — count + exact-spelling assertion per item (Inventory 1) | none |

**Uncodified-standard items (detect-and-surface — not silently applied, not silently dropped):**
1. **Enforcement of R3.2** ("single source of truth") — the *rule* is codified (ENGINEERING_RULES §3 R3.2)
   but the **gate mechanism** is not. **Resolved at Gate 1 (Q2 → durable test):** enforcement lives in the
   test suite, so **no new CI gate and no rulebook line is invented by this ticket** — the `codify`
   ratification route stays unused. If a *CI* gate is ever wanted, it goes through `/mango:codify` then.
2. **"Clear error" message standard** — no codified error-message convention exists in the rulebook or
   CONVENTION §4. **Resolved at Gate 1 (Q1 → field-path + expectation):** the bar is ratified for
   **AC1 of this ticket only**, not adopted project-wide. Promoting it to a general convention would be a
   separate `/mango:codify` item; until then it may not gate-block any other ticket.

## Inventory (universal "all/every/no" requirements)

### Inventory 1 — contract vocabulary (R1 + R2): a counted "declare each of N"

- **Denominator / total N: 40** = 11 node kinds + 9 edge kinds + 3 confidence tiers + 10 node fields + 7 edge fields.
- Review must confirm **every** row (exact spelling, per CONVENTION §3 "fixed spelling — do not vary"); an aggregate `k/40` does not close R1/R2.

| # | Item | Group | Ph3/4 proven by (`path:line` / test) | Status |
|---|------|-------|--------------------------------------|--------|
| 1 | `File` | node kind | `contract.py:19` · asserted `test_contract_schema.py:55` | ✅ |
| 2 | `Namespace` | node kind | `contract.py:19` · asserted `test_contract_schema.py:55` | ✅ |
| 3 | `Class` | node kind | `contract.py:19` · asserted `test_contract_schema.py:55` | ✅ |
| 4 | `Interface` | node kind | `contract.py:19` · asserted `test_contract_schema.py:55` | ✅ |
| 5 | `Trait` | node kind | `contract.py:19` · asserted `test_contract_schema.py:55` | ✅ |
| 6 | `Enum` | node kind | `contract.py:19` · asserted `test_contract_schema.py:55` | ✅ |
| 7 | `Function` | node kind | `contract.py:19` · asserted `test_contract_schema.py:55` | ✅ |
| 8 | `Method` | node kind | `contract.py:19` · asserted `test_contract_schema.py:55` | ✅ |
| 9 | `Property` | node kind | `contract.py:19` · asserted `test_contract_schema.py:55` | ✅ |
| 10 | `ClassConst` | node kind | `contract.py:19` · asserted `test_contract_schema.py:55` | ✅ |
| 11 | `Const` | node kind | `contract.py:19` · asserted `test_contract_schema.py:55` | ✅ |
| 12 | `CONTAINS` | edge kind | `contract.py:33` · asserted `test_contract_schema.py:71` | ✅ |
| 13 | `EXTENDS` | edge kind | `contract.py:33` · asserted `test_contract_schema.py:71` | ✅ |
| 14 | `IMPLEMENTS` | edge kind | `contract.py:33` · asserted `test_contract_schema.py:71` | ✅ |
| 15 | `USES_TRAIT` | edge kind | `contract.py:33` · asserted `test_contract_schema.py:71` | ✅ |
| 16 | `CALLS` | edge kind | `contract.py:33` · asserted `test_contract_schema.py:71` | ✅ |
| 17 | `NEW` | edge kind | `contract.py:33` · asserted `test_contract_schema.py:71` | ✅ |
| 18 | `IMPORTS` | edge kind | `contract.py:33` · asserted `test_contract_schema.py:71` | ✅ |
| 19 | `INCLUDES` | edge kind | `contract.py:33` · asserted `test_contract_schema.py:71` | ✅ |
| 20 | `REFERENCES` | edge kind | `contract.py:33` · asserted `test_contract_schema.py:71` | ✅ |
| 21 | `RESOLVED` | tier | `contract.py:45` · asserted `test_contract_schema.py:85` | ✅ |
| 22 | `HEURISTIC` | tier | `contract.py:45` · asserted `test_contract_schema.py:85` | ✅ |
| 23 | `DYNAMIC` | tier | `contract.py:45` · asserted `test_contract_schema.py:85` | ✅ |
| 24 | `kind` | node field | `contract.py:47` · asserted `test_contract_schema.py:89` | ✅ |
| 25 | `name` | node field | `contract.py:47` · asserted `test_contract_schema.py:89` | ✅ |
| 26 | `qualified_name` | node field | `contract.py:47` · asserted `test_contract_schema.py:89` | ✅ |
| 27 | `file_path` | node field | `contract.py:47` · asserted `test_contract_schema.py:89` | ✅ |
| 28 | `line_start` | node field | `contract.py:47` · asserted `test_contract_schema.py:89` | ✅ |
| 29 | `line_end` | node field | `contract.py:47` · asserted `test_contract_schema.py:89` | ✅ |
| 30 | `modifiers` | node field | `contract.py:47` · asserted `test_contract_schema.py:89` | ✅ |
| 31 | `params` | node field | `contract.py:47` · asserted `test_contract_schema.py:89` | ✅ |
| 32 | `is_test` | node field | `contract.py:47` · asserted `test_contract_schema.py:89` | ✅ |
| 33 | `extra` | node field | `contract.py:47` · asserted `test_contract_schema.py:89` | ✅ |
| 34 | `kind` | edge field | `contract.py:60` · asserted `test_contract_schema.py:104` | ✅ |
| 35 | `source_qname` | edge field | `contract.py:60` · asserted `test_contract_schema.py:104` | ✅ |
| 36 | `target_qname` (optional — NULL until the resolver links it, `PLAN.md:233`) | edge field | `contract.py:60` · asserted `test_contract_schema.py:104` | ✅ |
| 37 | `target_raw` | edge field | `contract.py:60` · asserted `test_contract_schema.py:104` | ✅ |
| 38 | `file_path` | edge field | `contract.py:60` · asserted `test_contract_schema.py:104` | ✅ |
| 39 | `line` | edge field | `contract.py:60` · asserted `test_contract_schema.py:104` | ✅ |
| 40 | `confidence_tier` (defaults `RESOLVED`, `PLAN.md:264`) | edge field | `contract.py:60` · asserted `test_contract_schema.py:104` | ✅ |

**Required-vs-optional field policy is a Gate-2 decision, derived from a citation — not invented:** the
SQLite mirror at `PLAN.md:254-268` supplies the defaults (`is_test` → 0, `confidence_tier` → `'RESOLVED'`)
and `PLAN.md:233` establishes that `target_qname` is NULL until the resolver runs. Design must pin the
required set against those lines; analysis does not pre-pick it.

### Inventory 2 — AC2(b) "no field lists duplicated": the schema-consuming core modules

- **Denominator / total N: 5.** R3.2 names "Store, indexer, and tools"; `resolver.py` and `adapter.py`
  also consume the vocabulary, so the honest denominator is all five. Each is a 1-line stub today.

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| 1 | `code_atlas/store.py` | ast-parsed, 0 vocabulary literals ≥2 · `test_contract_sole_source.py:58[store.py]` | ✅ |
| 2 | `code_atlas/indexer.py` | ast-parsed, 0 vocabulary literals ≥2 · `test_contract_sole_source.py:58[indexer.py]` | ✅ |
| 3 | `code_atlas/resolver.py` | ast-parsed, 0 vocabulary literals ≥2 · `test_contract_sole_source.py:58[resolver.py]` | ✅ |
| 4 | `code_atlas/adapter.py` | ast-parsed, 0 vocabulary literals ≥2 · `test_contract_sole_source.py:58[adapter.py]` | ✅ |
| 5 | `code_atlas/tools/` | every `*.py` under `tools/` globbed + ast-parsed (`__init__.py` today) · `test_contract_sole_source.py:29,58` | ✅ |

### Surface inventory

**n/a** — TRACK=backend, zero frontend surfaces. `SURFACES` not applicable.

## Clarifications

`CLARIFICATION: 7 raised | 5 self-resolved (cited) | 2 for human decision → both answered at Gate 1 | j = 0 outstanding`

Q1 and Q2 were put to the user and **decided** (see below); no clarification remains open, so Gate 1 is
cleared. The tally is kept at its raised counts — the two human decisions are recorded, not retro-erased.

- **Self-resolved (cited):**
  1. **Initial `CONTRACT_VERSION` value?** → **1** (integer series). `PLAN.md:113` calls the next shape
     "anticipated contract **v2**" and `PLAN.md:118` says "Bump `contract_version` when this lands" — so
     v1 is the current shape and versions are a bumpable integer series, not semver.
  2. **Must `validate()` also accept the error result `{path, ok:false, error}`?** → **yes**. That variant
     is part of the protocol (`PLAN.md:84`) and R5.1 requires a bad file to return `ok:false` and
     "never break the stream"; the indexer validates *every* result, so rejecting the error variant
     would break exactly the degradation R5.1 mandates.
  3. **Where is the qname convention "documented" (R3)?** → in `contract.py`'s docstring, **pointing at**
     `CONVENTION.md:60-64`, not as a second normative copy. R3.2 makes `contract.py` the code-side single
     source of truth; CONVENTION §3 stays the human-facing doc, kept in sync by R3.1 on any bump.
  4. **Capability-flags shape?** → a flat name→bool mapping, per the worked example
     `{"semantic_types": true}` at `PLAN.md:97` and R1.6 (advertised optional the core *may* use, never a
     method every adapter must implement).
  5. **Does this ticket need a `contract_version` bump / conformance update under R3.1?** → **no bump**;
     R3.1 governs *changes* to an existing contract, and this ticket *establishes* v1. The conformance
     suite itself is task 012 (`docs/BACKLOG.md:24`), which depends on 002 — so R3.4 is satisfied
     forward, and the tests this ticket ships are `validate()`'s own (R6.1).

- **Human decisions taken at Gate 1 (both were acceptance-bar decisions → the user's to make):**
  - **Q1 — "clear errors" (AC1) → DECIDED: field path + expectation.** Every rejection names the offending
    key path **and** what was expected (allowed kind / required field / type); a test asserts one case per
    malformation class — unknown node kind · unknown edge kind · missing required field · wrong top-level
    shape · bad `confidence_tier` (**5 classes**). Approved example message:
    `nodes[0].kind: 'Klass' is not an allowed node kind (expected one of File, Namespace, Class, Interface, Trait, Enum, Function, Method, Property, ClassConst, Const)`.
    → AC1(b) is now falsifiable; no manual-check exclusion needed.
  - **Q2 — AC2(b) proof → DECIDED: durable test.** This ticket ships a committed test (e.g.
    `tests/test_contract_sole_source.py`) asserting none of the 17 field names / 20 kind literals is
    re-declared as a list in the 5 consumers of Inventory 2 — they must import from `code_atlas.contract`.
    Rejected: the point-in-time grep (vacuous while the consumers are stubs) and a third CI grep-gate
    (would add an uncodified gate needing `codify` ratification). The test rides inside
    `config.test_command`, so tasks 004/009 trip it the moment they duplicate a field list.
    **Traceability:** this is an interpretation of **AC2(b)**, not new scope — it maps to an existing
    matrix row, per lesson 001 in `docs/LESSONS.md`.

- **Deferred to Phase 2 (design choices, not blockers — analysis does not pre-pick):**
  `validate()`'s call/return shape (raise vs return an error list — constrained by R5.1 fail-soft for the
  indexer *and* R3.4 assertion use in tests); implementation vehicle (hand-rolled stdlib checks vs
  `jsonschema`/`pydantic` — R8.2 "keep core dependencies minimal, stdlib-first" biases stdlib and the
  project currently declares only `fastmcp`); the exact qname helper set (R7.4/R1.2 bound it); whether
  vocabulary constants are `frozenset`/`StrEnum`/tuples.

---

## Phase 1 — Analysis ✋ Gate 1

- **Gap analysis (enhancement, per goal G1).** Current: the seam is **prose only**. `code_atlas/contract.py:1`
  is a single docstring (`"""JSON contract: schema, validation, version (single source of truth). Stub — task 002."""`);
  `grep -rn 'CONTRACT_VERSION\|USES_TRAIT\|confidence_tier' code_atlas/` → **0 hits**. The vocabulary exists
  at `docs/PLAN.md:87-99` and `docs/CONVENTION.md:53-65`, where no code can import it and no test can
  falsify it. Target: `contract.py` as the executable single source of truth. Per-goal gaps →
  (a) no kind constants → **R1**; (b) no field/tier definitions → **R2**; (c) no qname docs/helpers in code
  → **R3**; (d) no version constant, no capability-flag shape → **R4**; (e) no `validate()` for the indexer
  or the conformance suite → **R5**; (f) nothing importable to assert against → **AC1/AC2**.

- **Handler / entry point + blast radius.** Entry point is the module `code_atlas/contract.py` (no runtime
  handler — it is a pure, dependency-free schema module; `main.py:1` is still a stub, so nothing executes it yet).
  - **Existing callers: zero.** All five schema consumers are 1-line stubs (`store.py:1`, `indexer.py:1`,
    `resolver.py:1`, `adapter.py:1`, `tools/__init__.py:1`) — verified by `wc -l code_atlas/*.py` → 1 line each.
    So the blast radius is **forward** (future tasks), not lateral.
  - **Forward dependents** (`docs/BACKLOG.md:14-24`): 004 SQLite store, 005 adapter protocol, 009 indexer,
    011 resolver, 012 conformance tests all declare `002` as a dependency; adapters 006/007 must emit this
    vocabulary. Anything named here becomes hard to change later without an R3.1 version bump — that is
    precisely why the ticket is scheduled second.
  - **Tooling coupling:** the CI **R1.1 grep-gate** (`ci.yml:46-53`) runs over `code_atlas/`, so
    `contract.py` must contain no `if … language … ==` / `match … language` construct. Note the pattern is a
    plain grep, so even a *docstring or comment* line containing `language` together with `==` would trip
    it — a real risk in a module whose whole purpose is "language-neutral vocabulary". Design should keep
    that wording out of one-line proximity.
  - **Repos touched:** `app` (`.`) only — `config.repos` has a single entry. No `db-map` exists
    (`config.db_kind` is null), so no schema-dependent widening applies.
  - **Fan-out:** not used. `config.explore_fanout` is true, but the whole surface is 11 one-line stubs plus
    two design docs already read in full — an Explore dispatch would return facts already in hand. 0 dispatches
    (see Cost ledger).

- **Rule-compliance section coverage** — applicable sections **derived from the change type**
  (*new pure-Python core module that defines the adapter seam, + its tests*; no migration, no UI, no adapter source):

  `RULE SECTIONS: §1 (R1.1 ✅ R1.2 ✅ R1.3 ✅ R1.4 ✅ R1.5 ✅ R1.6 ✅) · §2 (R2.1 ✅ R2.2 N/A R2.3 N/A) · §3 (R3.1 ✅ R3.2 ✅ R3.3 ✅ R3.4 ✅) · §4 (R4.1 ✅ R4.2 ✅ R4.3 N/A) · §5 (R5.1 ✅ R5.2 ✅ R5.3 ✅) · §6 (R6.1 ✅ R6.2 ✅ R6.3 N/A R6.4 ✅) · §7 (R7.1 ✅ R7.2 ✅ R7.3 ✅ R7.4 ✅ R7.5 ✅) · §8 (R8.1 N/A R8.2 ✅) — 27 sections applicable-or-N/A, 0 unchecked`

  | Rule | Verdict | Note |
  |------|---------|------|
  | R1.1 zero language branches | ✅ checked | Contract must be a language-neutral superset; CI greps `code_atlas/` (`ci.yml:46-53`) — see the docstring-proximity risk above |
  | R1.2 one seam, YAGNI | ✅ checked | This ticket **is** the one seam; no registry/base-class/DI may ride along (R1.2 defers those to adapter #2) |
  | R1.3 one-way dependency | ✅ checked | `contract.py` imports no parser and nothing from adapters; stdlib-only is the target (see R8.2) |
  | R1.4 SRP | ✅ checked | Schema/validation only — no SQLite, no parsing, no presentation |
  | R1.5 substitutability | ✅ checked | Same vocabulary + guarantees for every adapter; enforced later by R3.4/task 012 |
  | R1.6 capability flags (ISP) | ✅ **mandatory for R4** | Capability-flags shape is a named deliverable; must be *advertised optional*, never a required method — the core degrades when absent |
  | R2.1 language spec, not sample | ✅ checked | Node kinds like `Trait`/`USES_TRAIT` are the neutral superset (`PLAN.md:88`), not PHP-specific carve-outs |
  | R2.2 no repo/framework names | N/A | No adapter source in this change (gate at `ci.yml:55-63` scans `adapters/` only) |
  | R2.3 samples drive tests/perf only | N/A | No sample repo involved |
  | R3.1 version bump + conformance | ✅ checked | No *bump* — this establishes v1 (clarification 5); the version constant itself is R4 |
  | R3.2 `contract.py` is sole source of truth | ✅ **mandatory — this is AC2(b)** | Enforcement mechanism is the open Q2 |
  | R3.3 adapters emit bare edges | ✅ checked | Contract must model `target_raw` (bare) + optional `target_qname` (resolver-filled, `PLAN.md:233`) — inventory items 36-37 |
  | R3.4 adapters must pass `tests/contract/` | ✅ checked | Satisfied forward: `validate()` is the function the task-012 suite will use (R5) |
  | R4.1 no LLM/network in core | ✅ checked | Pure schema module; trivially satisfied and worth asserting for a validator (no remote schema fetch) |
  | R4.2 identical input → identical output | ✅ checked | `validate()` must be deterministic — no set-ordering leaking into error output (matters for Q1's message bar) |
  | R4.3 single SQLite writer | N/A | No SQLite in this change (R1.4 forbids it here) |
  | R5.1 per-file `ok:false` never breaks the stream | ✅ checked | Drives clarification 2 and constrains `validate()`'s shape (Phase-2 item) |
  | R5.2 HEURISTIC/DYNAMIC tiers | ✅ checked | The 3 tiers are inventory items 21-23; contract must never let a guess be spelled `RESOLVED` |
  | R5.3 loud on programmer errors, soft on data errors | ✅ checked | The two `validate()` callers sit on opposite sides of this line (indexer = data, tests = programmer) — the Phase-2 shape decision |
  | R6.1 no task done without tests | ✅ checked | Core-module change → tests asserting resolved behaviour; AC1/AC2 are the assertions |
  | R6.2 spec-driven fixtures | ✅ checked | Malformed-payload fixtures must be spec-shaped, not copied from a real repo |
  | R6.3 cross-repo validation | N/A | No indexing runs in this ticket |
  | R6.4 guardrail tests are real tests | ✅ checked | Directly relevant to **Q2** option (b) |
  | R7.1 smallest useful thing | ✅ checked | SCOPE=M; no speculative schema fields beyond `PLAN.md:89,92` |
  | R7.2 keep plan + backlog honest | ✅ checked | Status synced to `in-progress` in this file's frontmatter **and** `docs/BACKLOG.md:14` |
  | R7.3 small commits, no AI trailer | ✅ checked | Phase-3 discipline |
  | R7.4 no dead abstractions | ✅ checked | Bounds R3's helper set — a helper needs a named near-term consumer (004/011/012) |
  | R7.5 comments ≤ 3 lines | ✅ checked | Also in `CLAUDE.md`; the qname docs go in a **docstring**, not a comment block |
  | R8.1 adapter self-containment | N/A | No adapter touched |
  | R8.2 minimal core dependencies | ✅ checked | Biases `validate()` to stdlib over `jsonschema`/`pydantic` (Phase-2 item); project declares only `fastmcp` (`pyproject.toml:15`) |

- **Self-audit.** Sections decomposed **4/4** ✅ · AC table complete, every acceptance value independently
  re-derived (11/9/3/10/7 all match the ticket — no silent correction) ✅ · **AC1(b) was flagged not
  falsifiable and pinned by the user, not silently corrected — it may now carry a `✅` once proven** ✅ ·
  `BASELINE` captured = **green**, toolchain caveat recorded, 0 exclusions ✅ · **j = 0 outstanding** (both
  human decisions taken at Gate 1) ✅ · Inventory N=40 (per-item) and N=5 (per-item) set ✅ · matrix
  `Status` filled (all `❌`, pre-implementation) ✅ · `RULE SECTIONS` emitted, 27 sections checked-or-N/A,
  0 unchecked ✅ · `STRUCTURE=native`, `TRACK=backend`, `TIER=full`, `SCOPE=M` declared ✅ ·
  `SURFACES` n/a (backend) ✅ · 2 uncodified-standard items surfaced and resolved without authoring a
  rule ✅.

- **Gate 1 status:** **cleared** — Q1 answered (field path + expectation), Q2 answered (durable test).
  Design may start; the two ratified bars are binding inputs to it.

## Phase 2 — Design ✋ Gate 2

**Gate 1 confirmed cleared:** matrix + AC table filled, `CLARIFICATION` j = 0 outstanding, both Gate-1
bars (Q1 error message, Q2 durable test) ratified and carried in as binding inputs.

### Approach

One new module, `code_atlas/contract.py`, holding the seam as **plain data + one pure function** — no
classes, no registry, no base types (R1.2/R7.4):

1. **Vocabulary as ordered tuples**, not sets or enums: `NODE_KINDS` (11), `EDGE_KINDS` (9),
   `CONFIDENCE_TIERS` (3), `NODE_FIELDS` (10), `EDGE_FIELDS` (7) — spelled exactly as CONVENTION §3,
   in its declaration order. **Tuples specifically because of R4.2:** the Q1 error bar makes the allowed
   values part of the message text, and a `frozenset` would emit them in arbitrary order, so identical
   input would not give identical output. Membership is an `in` check over ≤11 items.
2. **Required-vs-optional split derived from the SQLite mirror, not invented.** Required node fields =
   `kind, name, qualified_name, file_path, line_start`; required edge fields =
   `kind, source_qname, target_raw, file_path, line`. Optional = the rest, because `PLAN.md:254-268`
   gives them defaults/nullability (`is_test` → 0, `confidence_tier` → `'RESOLVED'`) and `PLAN.md:233`
   establishes `target_qname` stays NULL until the resolver links it (R3.3 — adapters emit **bare** edges).
3. **`CONTRACT_VERSION = 1`** plus the capability-flags shape: a `Capabilities = dict[str, bool]` alias and
   `KNOWN_CAPABILITIES = ("semantic_types",)`. Per R1.6 a flag is **advertised, never required** — an
   absent flag is legal and the core degrades; an *unknown* flag name is reported, never honoured.
4. **Qname convention in the module docstring** (pointing at CONVENTION §3 as the human-facing copy, not
   a second normative one) + **two** helpers, each with a named near-term consumer as R7.4 demands:
   `split_qname()` (consumers: task 011 resolver, task 013/014 `namespace_tree`/`search_symbol`) and
   `join_qname()` (consumer: task 012 conformance assertions). The separator is the contract constant
   `MEMBER_SEPARATOR = "::"` — see **the flagged decision below**. No `normalize_qname()`: normalising a
   leading `\` would be PHP-shaped logic in the core, straight into an R1.1/R1.5 violation.
5. **`validate(result: object) -> list[str]`** — returns error strings, empty list means valid. Parameter
   typed `object` because the input is untrusted JSON off a subprocess pipe, so it may not even be a dict.
   Each message is `<field path>: <what was found> (expected <what>)`, satisfying the Q1 bar.

**Why return a list instead of raising** — the two callers in R5 sit on opposite sides of R5.3:
`indexer.py` handles a *data* error (a weird source file) and must set `parsed_ok=0` and keep going
without breaking the stream (R5.1), which a raising validator would fight with a try/except per file;
`tests/contract/` wants `assert validate(result) == []`. One return shape serves both.

**Unknown keys are errors, not ignored.** A key outside `NODE_FIELDS`/`EDGE_FIELDS` is reported. R3.1
makes any vocabulary/field change a versioned event, so an unexpected key is by definition a contract
violation — and this is what catches an adapter typo (`qualifiedName`) instead of silently dropping data.

### ✅ Resolved at Gate 2 — the member separator (was: under-specified for languages #3/#4)

**Decision (user, Gate 2): ratify `::` as the universal member separator and fix the docs in this ticket.**
`MEMBER_SEPARATOR = "::"` becomes a contract constant; change-list item **9** is now unconditional and
rewrites `PLAN.md:95` + `CONVENTION.md:62-63` so Python reads `module.Class::method` and C#
`Namespace.Type::Member`. The **container** keeps its language-native separator (`\`, `.`, `/`); only the
**member** boundary is uniform. Any future change to it is an R3.1 versioned event, not silent drift.
The analysis below is retained as the record of why the question was raised rather than assumed.

`split_qname`/`join_qname` need one universal member separator, and **the docs contradict themselves**:

| Source | Says |
|--------|------|
| `PLAN.md:94` / `CONVENTION.md:60` | "Qualified-name convention (**identical across languages**)" |
| PHP | `\Ns\Class::method` — `::` |
| JS/TS | `src/user.ts::User::save` — `::` |
| C# (`CONVENTION.md:62`) | `Namespace.Type.Member` "mapped onto the same shape" — **ambiguous** |
| Python (`PLAN.md:95`, `CONVENTION.md:62`) | `module.Class.method` — **`.`, not `::`** |

Adapters #1 (PHP) and #2 (TS) both use `::`, so `MEMBER_SEPARATOR = "::"` is correct for everything on
this milestone's horizon — but writing it into the core seam silently would bake a decision that
languages #3/#4 inherit, while `PLAN.md:95` still says dots. **Rejected alternatives at this gate:**
ship `::` but leave the docs contradictory and open a follow-up ticket (the contradiction would survive
into tasks 020/021); or ship no helpers until task 019 supplies evidence (would leave R3, a named
deliverable, only half-shipped).

### Rejected alternatives

| Rejected | Why |
|----------|-----|
| **`jsonschema`** for validation | Adds a runtime dependency against R8.2 (the project declares only `fastmcp`), and its stock messages don't carry the Q1 "field path + what was expected" shape — every message would need re-wrapping anyway, so the dependency buys nothing. |
| **`pydantic`** models | Heavier still, and exception-first: `ValidationError` is the wrong ergonomics for R5.1's fail-soft indexer path. Also imports a validation *framework* into the one seam R1.2 says to keep minimal. |
| **`StrEnum`** for kinds | The vocabulary crosses a JSON boundary as plain strings; an enum adds a second spelling (`NodeKind.CLASS` vs `"Class"`) and ceremony with no consumer asking for it (R7.4). Tuples are what `validate()` and the tests actually need. |
| **`frozenset`** for kinds | Fails R4.2 — the Q1 message embeds the allowed values, and set iteration order would make identical input produce different output. |
| **`normalize_qname()` helper** | Any normalisation worth having (forcing a leading `\`) is PHP-shaped → R1.1 language logic in the core. Left to the resolver to handle generically at task 011. |
| **A `Node`/`Edge` dataclass pair** | Speculative: nothing consumes typed objects yet (all five consumers are stubs), and it would create a second declaration of the field lists — the exact R3.2 duplication AC2(b) forbids. |
| **A third CI grep-gate for AC2(b)** | Rejected by the user at Gate 1 (Q2) in favour of a test inside `config.test_command`; a CI gate would also be an uncodified standard needing `codify` ratification. |

### Assumptions

| Assumption | verified / novel-untested | Evidence / de-risking |
|------------|---------------------------|-----------------------|
| `validate()` is pure logic — no I/O, no network, no subprocess, no DB | **verified** | It is a function over an already-parsed dict; R4.1 forbids network in the core, and nothing in the design opens a handle. **No novel third-party or runtime assumption exists in this design**, so step 3's blocker cannot apply. |
| Local `.venv` is Python **3.13**, CI is **3.12** | **verified** | `.venv/bin/python -V` → 3.13.14; `ci.yml:18` → `"3.12"`; `pyproject.toml:10` → `>=3.12`. Constraint: no 3.13-only syntax. `ruff target-version = "py312"` (`pyproject.toml:20`) mechanically catches a slip. |
| Zero existing consumers/assertions to invalidate | **verified** (mechanical, not a name grep) | `grep -rn --include='*.py' -E 'contract|CONTRACT_VERSION|validate\('` across **every** root → 1 hit, the stub's own docstring. Test roots enumerated: `tests/` + `tests/contract/` (empty) + `tests/fixtures/` (empty) — no `.py` asserting any vocabulary literal. |
| mypy will type-check the new module; ruff will lint the tests | **verified** | `pyproject.toml:28` `files = ["code_atlas"]` (tests are **not** type-checked); `ci.yml:30` runs `ruff check .` (tests **are** linted). |
| An unknown key in a node/edge is a contract violation, not forward-compat | **verified** by rule | R3.1 makes any field-vocabulary change require a `contract_version` bump, so a v1 core meeting an unknown key is seeing a violation by definition. |
| `MEMBER_SEPARATOR = "::"` is universal | **verified — ratified by the user at Gate 2** | Was flagged, not assumed: the docs contradicted each other for Python/C#. The user ratified `::` and approved the doc fix (change-list item 9), so this is now a decided contract constant, not an open assumption. |

### Smallest change-list

Every item traces to a matrix row. `#7` is process collateral traced to a rule rather than a row, and is
declared here up front so it is not an execute surprise.

| # | Change | File / area | Ph2 covered by | k/N |
|---|--------|-------------|----------------|-----|
| 1 | Module docstring: what the seam is + the qname convention, pointing at CONVENTION §3 | `code_atlas/contract.py` | R3, G1 | 1/1 |
| 2 | `NODE_KINDS` (11), `EDGE_KINDS` (9) ordered tuples | `code_atlas/contract.py` | R1 (inventory items 1-20) | 20/20 |
| 3 | `CONFIDENCE_TIERS` (3), `NODE_FIELDS` (10), `EDGE_FIELDS` (7) + the required-field tuples derived from `PLAN.md:254-268,233` | `code_atlas/contract.py` | R2 (inventory items 21-40) | 20/20 |
| 4 | `CONTRACT_VERSION = 1`, `Capabilities` alias, `KNOWN_CAPABILITIES` | `code_atlas/contract.py` | R4, AC2(a) | 2/2 |
| 5 | `MEMBER_SEPARATOR`, `split_qname()`, `join_qname()` | `code_atlas/contract.py` | R3 | 1/1 |
| 6 | `validate(result: object) -> list[str]` — result/node/edge/tier/capability checks, messages in the Q1 shape | `code_atlas/contract.py` | R5, AC1 | 2/2 |
| 7 | **Proving test + supporting suite:** good `ok:true` payload, good `ok:false` payload, and one case per malformation class (5) asserting field path **and** expectation; `CONTRACT_VERSION` import assertion; the 40 vocabulary items asserted exactly; `split_qname`/`join_qname` round-trip | `tests/contract/test_contract_schema.py` (new) | AC1, AC2(a), R1, R2, R3, R5 | 6/6 |
| 8 | **Durable sole-source test** (Q2): none of the 17 field names / 20 kind literals re-declared as a list in the 5 consumers of Inventory 2 | `tests/test_contract_sole_source.py` (new) | AC2(b) (inventory 2, 5 items) | 5/5 |
| 9 | Pin the member separator in the docs — Python `module.Class::method`, C# `Namespace.Type::Member` | `docs/PLAN.md:95`, `docs/CONVENTION.md:62-63` | R3 — **unconditional; ratified at Gate 2** | 1/1 |
| — | *Process collateral (declared, traced to rules not rows):* this working doc; `status: in-progress` → `done` in frontmatter + `docs/BACKLOG.md:14` (R7.2); token-spend row in `docs/BACKLOG.md` Token usage (CLAUDE.md "Token usage on PR") | `docs/tasks/002_*.md`, `docs/BACKLOG.md` | R7.2 + CLAUDE.md token rule | — |

**Test blast-radius (mechanical, real producers/consumers — not a shallow name grep).** Enumerated
across **every** test root, not just one directory: `grep -rn --include='*.py' -E 'contract|CONTRACT_VERSION|validate\('`
over the whole repo returns **1** hit (the stub's own docstring, `code_atlas/contract.py:1`);
`grep -rn -E 'qualified_name|confidence_tier|target_raw|USES_TRAIT|ClassConst' tests/` returns **0**.
Test roots: `tests/` (1 file, `test_smoke.py` — imports the package only), `tests/contract/` (empty),
`tests/fixtures/` (empty). **No existing assertion or call site is invalidated → zero proof-collateral
items.** Typecheck fan-out is nil for the same reason, and `mypy` does not cover `tests/`
(`pyproject.toml:28`). This is a genuinely greenfield module, which is why the collateral column is empty
rather than unexamined.

### Rule compliance

| Rule | How this design complies |
|------|--------------------------|
| **R1.1** zero language branches | Vocabulary is a neutral superset; no per-language logic. `normalize_qname()` was **rejected** precisely because it would be PHP-shaped. **Grep-proximity care:** `ci.yml:49` is a plain grep, so the docstring must not put `language` and `==` on one line, nor write `match … language` — a false positive would red the build in the one module whose subject *is* languages. |
| **R1.2 / R7.4** one seam, YAGNI | Plain constants + 1 function + 2 helpers. No registry, factory, base class, or dataclass. Each helper names its near-term consumer (011/012/013/014); the third helper was cut for lacking one. |
| **R1.3** one-way dependency | Imports stdlib only; nothing from `adapters/`, no parser. |
| **R1.4** SRP | Schema + validation only. No SQLite (that is `store.py`), no parsing, no presentation. |
| **R1.5** substitutability | One vocabulary, one validator, identical guarantees for every adapter — enforced later by R3.4/task 012. |
| **R1.6** capability flags (ISP) | `KNOWN_CAPABILITIES` is advertised-optional: absent flag is legal and the core degrades; never a method every adapter must implement. |
| **R3.1** version bump + conformance | No bump — this **establishes** v1 (Gate-1 clarification 5). Change-list #9 keeps the docs in step, and the conformance suite is task 012 which depends on 002. |
| **R3.2** sole source of truth | All field/kind lists exist **once**, in `contract.py`; change-list #8 is the durable guard the user chose. The rejected dataclass pair would have violated this. |
| **R3.3** bare edges | `target_raw` required, `target_qname` optional-and-NULL-until-resolved (`PLAN.md:233`) — the validator must not demand a resolved target. |
| **R4.1** no LLM/network in core | Pure function; no remote schema fetch, by construction. |
| **R4.2** identical input → identical output | The reason for tuples over `frozenset`: error messages embed the allowed values, so ordering must be canonical. Messages are emitted in field/kind declaration order. |
| **R5.1 / R5.3** fail-soft data, loud config | `validate()` **returns** errors and never raises on malformed data, so a bad file can be `parsed_ok=0` without breaking the stream. |
| **R6.1 / R6.2** tests, spec-driven | Two new test files; fixtures are hand-built spec-shaped payloads, not lifted from any repo. |
| **R7.1** smallest useful thing | One module + two test files + two doc lines. No schema field beyond `PLAN.md:89,92`. |
| **R7.5** comments ≤ 3 lines | The convention lives in the **module docstring** (a docstring, not a comment block); inline comments stay ≤ 3 lines. |
| **R8.2** minimal dependencies | Stdlib only — no `jsonschema`, no `pydantic`; `pyproject.toml` is untouched. |
| **CONVENTION §2, §4** | `snake_case` functions, `UPPER_SNAKE` constants, type hints on every public function, grouped imports, no wildcard. |

### Verification plan (per-AC, layer-matched)

| AC / requirement | risk layer | proof artifact | layer-match? |
|------------------|------------|----------------|--------------|
| **AC1(a)** good `{path, ok, nodes, edges}` and `{path, ok:false, error}` accepted | logic — a pure function over an in-memory dict; no I/O, no runtime surface where it could fail differently | unit: `validate()` on both documented payloads → `[]` | ✅ |
| **AC1(b)** malformed rejected with field path + expectation (5 classes) | logic — same pure function; the message text is its return value | unit: one assertion per malformation class, each checking the key path **and** the expectation clause | ✅ |
| **AC2(a)** `CONTRACT_VERSION` exported | logic — import-time | unit: `from code_atlas.contract import CONTRACT_VERSION` + assert | ✅ |
| **AC2(b)** no field lists duplicated in the 5 consumers | **source-level** — it can only fail in the *source text* of another module, which is exactly where the test looks | the durable sole-source test reading those 5 modules (Q2's ratified proof) | ✅ |
| **R1 + R2** all 40 vocabulary items, exact spelling | logic | unit: assert each tuple equals the exact expected sequence (per-item, not a count) | ✅ |
| **R3** qname helpers | logic | unit: `split_qname`/`join_qname` round-trip over the documented forms | ✅ |
| **R5** "usable by **the indexer**" | **integration** — usability by the indexer can only fail when the indexer actually wires it | **none possible in this ticket** — `indexer.py` is a 1-line stub (task 009). The *shape* that makes it usable (returns a list, never raises on malformed data) is unit-proven; the wiring is not. → **recorded coverage-gap exclusion** below | ❌ → **excluded (approved below)** |
| **R5** "usable by **the conformance tests**" | logic | unit: the new tests **are** that caller, using `assert validate(...) == []` | ✅ |

`SURFACES` n/a — TRACK=backend, so no per-surface proof manifest and no surface-coverage banner applies.

### Coverage-gap exclusions

| Item | Risk tier | Why deferred | Follow-up |
|------|-----------|--------------|-----------|
| R5 "usable by the indexer" — the integration half | medium | `indexer.py` is a 1-line stub; there is no indexer to integrate with inside this ticket, so no integration proof can exist here. Proving the shape (list-returning, non-raising) is the most this ticket can honestly prove. Recording it keeps a later challenger's "not met" distinguishable from a real miss. | **Task 009** (`docs/BACKLOG.md`, full-build indexer) wires `validate()` per file and asserts `parsed_ok=0` on a rejected result — the integration proof lands there. |

**APPROVED by the user at Gate 2.** Rejected alternatives: narrowing R5's interpretation so no gap is
recorded (would erase the trace that the indexer side was never proven), and pulling a minimal slice of
task 009 forward to prove it now (SCOPE M → L, pre-empting task 009's design).

### Proving test

**Name:** `tests/contract/test_contract_schema.py::test_validate_rejects_unknown_node_kind_with_field_path_and_expectation`

**Invocation:** `pytest tests/contract/test_contract_schema.py::test_validate_rejects_unknown_node_kind_with_field_path_and_expectation`
(plain `pytest` = `config.test_command` runs it as part of the suite; locally `.venv/bin/pytest` per the BASELINE caveat.)

**Assertion:** `validate({"path": "a.php", "ok": True, "nodes": [{"kind": "Klass", "name": "Klass", "qualified_name": "\\Klass", "file_path": "a.php", "line_start": 1}], "edges": []})`
returns exactly one error naming the key path `nodes[0].kind` **and** the expectation (the 11 allowed
node kinds, in canonical order).

**Fails pre-change:** `code_atlas.contract` has no `validate` — the import raises. **Passes post-change.**
It sits at the **logic layer**, which is this AC's risk layer (a pure function), and it is the single
assertion that pins the Q1 bar the user ratified.

### Rollback + porting

- **Rollback:** `git revert` the branch's commits, or delete the branch pre-merge. Nothing persists — no
  DB, no migration, no generated artifact, no config change, and **zero existing consumers** (verified
  above), so reverting cannot break another module. Restoring `contract.py` to its 1-line stub returns
  the repo to the current green baseline.
- **Porting:** none. `config.repos` has a single entry (`app` → `.`); no shared code, no ordering.

### SCOPE confirmed

**M — unchanged from analysis.** No tier crossing: 1 new production module, 2 new test files, 2 doc
lines. Branch type stays `feat` (`feat/002-contract-schema` per CONVENTION §7), matching the change
type — no branch/PR-type drift, so the *outgrew-its-ticket* nudge does not fire.

### Gate-2 self-audit

Every change-list item traces to a matrix row (`Ph2 covered by` filled `k/N`, item 9 conditional on the
flagged decision, process collateral declared and traced to R7.2/CLAUDE.md) ✅ · every assumption tagged;
**zero `novel-untested` third-party/runtime assumptions** (pure stdlib function — nothing to spike) ✅ ·
proving test named, layer-matched, and runnable via `config.test_command` ✅ · verification plan has one
`❌` (R5's integration half), recorded as a coverage-gap exclusion with follow-up task 009 and
**approved by the user at this gate** ✅ · blast radius traced mechanically across all test roots, not a
shallow grep → zero proof-collateral ✅ · rollback + porting recorded ✅ · SCOPE re-affirmed M ✅ ·
`DESIGN.md` **n/a** (TRACK=backend) ✅ · no surface manifest/banner applicable ✅ · member separator
ratified, so no assumption remains untagged ✅.

- **Gate 2 status:** **cleared** — `::` ratified as the universal member separator (docs fix is
  change-list item 9, now unconditional); the single coverage-gap exclusion approved. Execute may start.

## Phase 3 — Execute

- **Branch:** `feat/002-contract-schema`, cut from `main` (CONVENTION §7 `type/NNN-slug`). Cut from `main`
  deliberately, not from the unrelated `chore/mango-update-check-url` branch that happened to be checked out.
- **Commits** (logical units, no AI co-author trailer):

  | SHA | Commit | Change-list items |
  |-----|--------|-------------------|
  | `cc2136c` | Add the contract: vocabulary, version, qname helpers, validation | 1-7 |
  | `704a188` | Guard R3.2: no core module may re-declare the contract vocabulary | 8 |
  | `9d6191e` | Pin the qname member separator across all four languages | 9 |

- **Proving test added:** `tests/contract/test_contract_schema.py::test_validate_rejects_unknown_node_kind_with_field_path_and_expectation`
  - **pre-change:** `ImportError: cannot import name 'CONFIDENCE_TIERS' from 'code_atlas.contract'` — red, verified before writing the module.
  - **post-change:** `1 passed`. The asserted message is exactly the string ratified at Gate 1:
    `nodes[0].kind: 'Klass' is not an allowed node kind (expected one of File, Namespace, Class, Interface, Trait, Enum, Function, Method, Property, ClassConst, Const)`.
  - **Q1 bar coverage — 5/5 malformation classes**, each asserting the field path **and** the expectation:
    unknown node kind · unknown edge kind · missing required field · wrong top-level shape · bad `confidence_tier`.
- **DoD vs recorded `BASELINE: green`:** `pytest -q` → **34 passed** (baseline was 1) · `ruff check .` →
  **All checks passed** · `mypy code_atlas` → **no issues in 11 source files**. No new failure, no
  pre-existing failure to carry — baseline exclusions remain **none**.
- **Guardrail gates re-run locally** (the CI jobs, not trusted from the doc): **R1.1** grep over
  `code_atlas/` → **0 hits**; **R2.2** grep over `adapters/` → **0 hits**.

### Verification sweep — Axis 1 (file set)

| Check | Result |
|-------|--------|
| Zero stray references introduced | ✅ every symbol the tests import resolves (`missing: none`); the 16 public symbols are exactly those the change list names |
| Diff ⊆ approved change list | ✅ **7 paths, 0 outside the list** — see the hunk map below |
| No untouched-line reformatting | ✅ `docs/CONVENTION.md` = 3 lines changed, `docs/PLAN.md` = 1 line changed (diff inspected line-by-line); `contract.py` was a 1-line stub, so it has no pre-existing lines to reformat. **No formatter was run over any file.** |
| Each hunk maps to a matrix row | ✅ below |

| Path | Change-list item | Matrix row |
|------|------------------|-----------|
| `code_atlas/contract.py` | 1-6 | G1, R1, R2, R3, R4, R5, AC1, AC2(a) |
| `tests/contract/test_contract_schema.py` (new) | 7 | AC1, AC2(a), R1, R2, R3, R5 |
| `tests/test_contract_sole_source.py` (new) | 8 | AC2(b) |
| `docs/PLAN.md`, `docs/CONVENTION.md` | 9 | R3 |
| `docs/tasks/002_contract-schema.md`, `docs/BACKLOG.md` | declared process collateral | R7.2 + CLAUDE.md token rule |

**Non-vacuity check on the AC2(b) guard** (a guard that cannot fail proves nothing): appended
`COLUMNS = ["kind", "name", "qualified_name", "file_path"]` to `code_atlas/store.py` → the guard
**failed** as intended (`test_consumer_does_not_redeclare_the_contract_vocabulary[store.py]`); the line
was removed and `git diff code_atlas/store.py` is **empty**, so the stub is byte-identical to `main`.
The guard also asserts `len(VOCABULARY) == 38` and `len(consumers()) >= 5` so it cannot pass on an
empty vocabulary or an empty file list.

### Verification sweep — Axis 2 (design-conformance, per Gate-2 Approach bullet)

| Approved Gate-2 bullet | Verdict |
|------------------------|---------|
| 1. Vocabulary as ordered tuples, not sets/enums, in CONVENTION §3 order | **implemented-as-approved** — 5 tuples; asserted item-by-item (inventory 1) |
| 2. Required-vs-optional derived from `PLAN.md:254-268,233`, not invented | **implemented-as-approved** — `REQUIRED_*` tuples; `target_qname` optional, asserted by `test_target_qname_is_not_required_so_adapters_can_emit_bare_edges` |
| 3. `CONTRACT_VERSION = 1` + `Capabilities` alias + `KNOWN_CAPABILITIES` | **implemented-as-approved (with a caveat surfaced below)** |
| 4. Convention in the module docstring + exactly 2 helpers; no `normalize_qname` | **implemented-as-approved** — `split_qname`/`join_qname` only |
| 5. `validate(result: object) -> list[str]`, message = `<path>: <found> (expected <what>)` | **implemented-as-approved** |
| 6. Returns rather than raises, so both R5 callers are served | **implemented-as-approved** — `test_validate_never_raises_on_malformed_input` covers `None`, `42`, `str`, `[]`, `{}`, wrong-typed keys |
| 7. Unknown keys are errors, not ignored | **implemented-as-approved** — `test_validate_rejects_an_unknown_field_name` |

### Design-conformance deviations / caveats surfaced to review

| Approved Gate-2 bullet | What was implemented instead | `path:line` | Surfaced to review |
|------------------------|------------------------------|-------------|--------------------|
| Bullet 3's clause "an **unknown** flag name is reported, never honoured" | The **data shape** ships as approved (`Capabilities` alias + `KNOWN_CAPABILITIES`), but nothing *reports* an unknown flag — capability flags are advertised at the adapter handshake, which does not exist until task 005, so there is no call site to report from. Change-list item 4 only ever named the alias + tuple, so the file diff is a clean subset; this is disclosed because the **prose** of the bullet promised behaviour the ticket does not ship. | `code_atlas/contract.py:88-90` | **yes** — review to adjudicate: accept as consumer behaviour landing at task 005, or require a `validate_capabilities()` here |
| Implicit in bullet 5 — how deep does `validate()` type-check? | Type checks cover the **top level** (`result` is an object, `path` a string, `ok` a boolean, `nodes`/`edges` lists, rows are objects) plus key sets, kinds, and tiers. Per-field value types (e.g. `line_start` must be an int) are **not** checked — no approved item asked for it and all 5 ratified malformation classes are covered, so adding it would be gold-plating against R7.1. | `code_atlas/contract.py:112-141` | **yes** — disclosed so review can decide whether an adapter sending `line_start: "7"` should be rejected here or at task 009 |

Neither item puts a file outside the approved list, and neither is a silent `✅` for something unbuilt.

### Scope check

Diff is **7 paths / +754 lines**, of which 539 are this working doc. Production code is one module
(212 lines) and two test files. **`SCOPE: M` holds** — no tier crossing, so the *outgrew-its-ticket*
nudge does not fire. Branch type `feat` matches the change type; no branch/PR-type drift.

### Escalations

**None fired.** No design-invalidation (the Gate-2 approach worked as designed on the first pass) and the
stuck-detector never armed — the proving test went red → green in one attempt, so no failing signature
repeated (`config.stuck_threshold` = 3).

## Phase 4 — Review ✋ — **SKIPPED BY USER DECISION**

**Not run.** The user explicitly instructed "skip review, let /mango:finalise". Recorded here as a
human decision rather than left blank, so the gap is visible to anyone reading this doc or the PR.

What was therefore **not** done, stated plainly:

- **reviewer verdict:** none — no `mango:reviewer` dispatch.
- **challenger (ticket-blind) result:** none — no independent re-derivation of the requirements from the
  raw ticket. The withhold discipline was never exercised because no challenger ran.
- **Scope reconciliation / regression on Phase-1 callers:** self-checked at execute only (Axis 1 + Axis 2
  sweeps); not independently confirmed. Note the blast radius was zero existing callers, so there is
  little for a regression pass to find here.
- **Proving test result:** run by the author — red→green, `34 passed` against `BASELINE: green`. Not
  re-run by a second party.
- **Layer-match re-confirmation:** the one `❌` (R5 integration half) remains a human-approved
  coverage-gap exclusion from Gate 2; no reviewer re-confirmed it.
- **The 2 caveats surfaced at Phase 3** (capability-flag reporting; `validate()` type-check depth) were
  **never adjudicated** — they go into the PR body as open notes for the human reviewer instead.
- **Frontend rubric / proof manifest:** n/a (TRACK=backend).
- **`Reviewed at` marker:** **none recorded.** Consequence: finalise's stale-review guard has no SHA to
  diff against, so it is **vacuous** on this run — it cannot detect staleness because there is no
  reviewed set. Not a pass; an absent check.
- **Clean?** **Unknown — not assessed.** `Ph3/4 proven by` is author evidence, not a verdict.

## Phase 5 — Finalise ✋ final gate

- **PR draft:** `/tmp/pr-002.md` — built on `.github/pull_request_template.md` (CLAUDE.md requires that
  template; `config.pr_checklist_path` is null so the mango checklist hook is skipped). Every section
  filled; the 7 pre-PR self-check boxes each verified mechanically, not ticked by assertion:

  | Self-check box | Evidence |
  |----------------|----------|
  | R1.1 no language branch in core | grep re-run → 0 hits |
  | R2 adapters name no repo/framework | no adapter source touched; gate re-run → 0 hits |
  | R3 contract bump + conformance | **no bump owed** — establishes v1; conformance assertions ship here |
  | There is a test / smallest change | 34 assertions; 1 module + 2 test files |
  | Comments ≤ 3 lines | longest comment run = **1 line** in every touched file (checked mechanically) |
  | Related docs updated | PLAN §4.2, CONVENTION §3, BACKLOG status + token row, task frontmatter; **README needs none** (generic contract mention, no per-task status) |
  | No AI-attribution trailer | `git log main..HEAD` scanned → none |

- **Planned outward actions (each needs separate approval — all currently DRY-RUN, nothing executed):**
  - [x] **push branch** `feat/002-contract-schema` — **APPROVED + DONE.** 5 commits pushed to
        `origin/feat/002-contract-schema`; this is the shared ref that carries `docs/LESSONS.md` §002, so
        the durable lesson is not orphaned on a local branch.
  - [x] **open PR** — **APPROVED + DONE:** [#4](https://github.com/cuongdinhngo/code-atlas/pull/4), body
        from `/tmp/pr-002.md` on `.github/pull_request_template.md`.
  - [ ] tracker comment — **DECLINED by the user**; not run. The PR body already carries the proving-test
        result and the deferred exclusion, so nothing is lost.
  - [ ] tracker transition — **n/a**: the tracker is this repo's task files + BACKLOG, already updated in-branch
- **Follow-up tickets drafted for deferred (⚠) rows:** one — R5's excluded integration half. **Task 009
  already exists** (`docs/tasks/009_full-build-indexer.md`) and is the right home, so no *new* ticket was
  created; instead, **approved at this gate**, an explicit acceptance line was added to 009 so the
  exclusion cannot be silently forgotten: *"A result rejected by `contract.validate()` sets
  `files.parsed_ok=0` and never breaks the stream (R5.1) — this closes the R5 integration-proof exclusion
  deferred from task 002."* This file sits **outside the Gate-2 change list** and was edited only on
  explicit approval — recorded here as a deliberate, human-authorised scope addition, not a silent one.
- **Durable lesson:** recorded — **LESSONS.md §002, "A guard written before its consumers exist must be
  negative-controlled"** (`docs/LESSONS.md:6-14`). Lands on a shared ref via the approved branch push, so
  it is a repo artifact rather than an orphan on a local branch. The second candidate (verify an
  "identical across languages" claim against its own examples) was offered and declined.
- **Revert path:** branch `feat/002-contract-schema`, commits `cc2136c` · `704a188` · `9d6191e` ·
  `cdd45c8` (+ the lesson commit if approved). Pre-merge: delete the branch — nothing is pushed yet.
  Post-merge: `git revert` the merge commit; there is no migration, no persisted state, and zero existing
  consumers, so revert is behaviourally total. No tracker transition to undo.

---

## Cost ledger (descriptive — facts only, never auto-cuts)

Scope = **subagent dispatch only**. Main-loop output noise is **not** measured by mango (consult `rtk gain`).

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| Phase 1 | *(none — 0 dispatches; fan-out declined, see blast radius)* | — | 0 | RTK active on Bash output (`token_optimizer.rtk: expect`); saving per `rtk gain`, not attributable per-dispatch |
| Phase 2 | *(none — 0 dispatches; design judgment stayed on the main model per the delegation map)* | — | 0 | as above |
| Phase 3 | *(none — 0 dispatches; implementation + sweep ran in the main loop, shell checks via Bash not a model)* | — | 0 | as above |
| Phase 4 | *(none — review skipped by user decision, so no reviewer/challenger dispatch)* | — | 0 | n/a |
| Phase 5 | *(none — 0 dispatches)* | — | 0 | as above |

**Completeness gate: PASS.** Dispatches this run = **0** across all five phases (no `reviewer`, no
`challenger`, no `extractor`, no Explore fan-out). Rows = 5, one per phase, each carrying an explicit
`0` — no blank cell, no fabricated figure, no missing dispatch row.

`LEDGER TOTAL: 0 dispatch tokens · top cost driver: n/a (no subagent was dispatched on this run).`

### Main-loop spend — measured outside mango (the number the dispatch ledger cannot show)

mango's ledger is dispatch-scoped, and this run dispatched **nothing**, so `0` above is accurate but
tells you nothing about what the task actually cost. Since ~100% of task 002's cost was main-loop work,
the figures below are read directly from this session's Claude Code transcript
(`~/.claude/projects/-home-you-WORKSPACE-Projects-code-atlas/<session>.jsonl`, summing each
assistant message's `usage` block) from the `/mango:analysis 002` turn onward — so the earlier
version-check and harness-commit work is **excluded**, not folded in.

| Phase | API calls | Output | Fresh input (cache-write) | Cache reads |
|-------|-----------|--------|---------------------------|-------------|
| Phase 1 — analysis | 54 | 58.5k | 226.8k | 5.17M |
| Phase 2 — design | 35 | 53.2k | 64.1k | 5.64M |
| Phase 3 — execute | 35 | 79.6k | 86.4k | 6.96M |
| Phase 4 — review | 0 | — | — | — (skipped by user decision) |
| Phase 5 — finalise | 40 | 48.5k | 71.7k | 9.35M |
| **TASK 002 TOTAL** | **164** | **239.8k** | **449.0k** (+0.3k uncached) | **27.12M** |

**`TASK 002 MAIN-LOOP TOTAL: 689.2k fresh tokens (239.8k output + 449.3k input) · 27.12M cache reads ·
27.81M grand total · top output driver: Phase 3 execute (79.6k)`**

Read the two figures separately and do not add them casually: **689.2k** is the genuinely new work;
**27.12M** is context re-read from cache on each of 164 calls, which is what a long single-session
lifecycle costs and is priced very differently. Cache reads climb monotonically per phase (5.17M → 9.35M)
because the working doc itself grows and is re-read every turn — the largest single lever on this task's
cost, and the reason `solve`'s "emit deltas, not full artifacts" discipline exists.

**Comparison to task 001** is not apples-to-apples: 001's 113.6k is *dispatch* tokens (a reviewer +
challenger), a category this run has none of. Against task 002's 689.2k of main-loop work, 001's real
total was also never measured — so treat 001's row as a floor, not a total.

**Scope honesty.** The ledger measures **subagent dispatch only**. This run's real cost was almost
entirely **main-loop** work — file reads, the doc writes, the test/lint/grep output — which mango does
**not** measure, so a `0` here is **not** a claim that the task was free, and no dispatch-vs-noise split
should be inferred. For that layer, `rtk gain` is the instrument; note its counters are **lifetime and
cross-project** (its top rows are `eslint`/`vitest`, which this repo does not use), so its 22.7M/92%
figure **cannot be attributed to task 002** — it is reported here only as the pointer to the right
instrument, not as this task's number.

---

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Phase 1 | `work_doc_mode` = **embed** (append below the separator in the ticket file) | `.harness.json:13` sets `embed`; ticket is a repo-local file; matches task 001's placement |
| Phase 1 | Declined Explore fan-out despite `explore_fanout: true` | Whole surface is 11 one-line stubs + 2 docs read in full; a dispatch would return known facts |
| Phase 1 | Installed the project's `[dev]` extra into a gitignored `.venv/` to capture `BASELINE` | Host had no pytest/ruff/mypy; detect-not-assume requires actually running `config.test_command`, and `.gitignore:11-12,17` keeps the checkout clean |
| Phase 1 | `SCOPE=M`, `TIER=full` | 5 R-rows + 2 ACs + a 40-item universal inventory → not lite-eligible |
| Phase 1 | AC1(b) flagged not-falsifiable rather than silently pinned | Principle 1 — the acceptance bar is the user's to set (Q1) |
| Gate 1 | **Q1 → "clear errors" = offending key path + what was expected**, 5 asserted malformation classes | User's ratified acceptance bar; makes AC1(b) falsifiable so it can carry a `✅`. Scoped to this ticket, not adopted project-wide |
| Gate 1 | **Q2 → AC2(b) proven by a durable test**, not a point-in-time grep and not a CI gate | Enforcement must survive tasks 004/009; keeping it in `test_command` avoids adding an uncodified CI gate (which would need `codify` ratification). Traces to existing row AC2 — no new scope |
| Gate 1 | **Gate 1 cleared** | Both open clarifications decided; j = 0 outstanding. Next: `/mango:design 002` |
| Phase 2 | Vocabulary as ordered **tuples**, not `frozenset`/`StrEnum` | R4.2 — the Q1 message embeds the allowed values, so set ordering would break identical-input-identical-output; an enum adds a second spelling with no consumer (R7.4) |
| Phase 2 | `validate()` **returns** `list[str]`, never raises on malformed data | R5.1/R5.3 — the indexer must set `parsed_ok=0` and keep going; the conformance tests want `assert validate(...) == []`. One shape serves both callers |
| Phase 2 | **Stdlib only** — no `jsonschema`, no `pydantic` | R8.2; and neither library's stock messages carry the Q1 "field path + expected" shape, so the dependency would buy nothing |
| Phase 2 | **Two** qname helpers (`split_qname`, `join_qname`); `normalize_qname` cut | R7.4 — each kept helper names a near-term consumer (011/012/013/014); normalising a leading `\` would be PHP-shaped logic in the core → R1.1 |
| Phase 2 | Unknown node/edge keys are **errors** | R3.1 makes a field-vocabulary change a versioned event, so an unexpected key is a violation by definition — and it catches an adapter typo instead of dropping data |
| Phase 2 | Member separator **flagged for the user**, not silently assumed | `PLAN.md:94` says the qname convention is "identical across languages" but `PLAN.md:95` gives Python dots while PHP/TS use `::`; baking `::` into the core seam silently would commit languages #3/#4 |
| Phase 2 | R5's integration half recorded as a **coverage-gap exclusion** → task 009 | `indexer.py` is a stub; no integration proof can exist in this ticket. Recording it keeps a later "not met" distinguishable from a real miss |
| Gate 2 | **`::` ratified as the universal member separator**; `PLAN.md:95` + `CONVENTION.md:62-63` fixed in this ticket (item 9 now unconditional) | User's decision. Container keeps its language-native separator; only the member boundary is uniform. A future change is now an R3.1 versioned event rather than silent drift. Rejected: ship `::` with the docs left contradictory (survives into 020/021); ship no helpers until 019 (leaves R3 half-delivered) |
| Gate 2 | **Coverage-gap exclusion approved** (R5 integration half → task 009) | User's approval. Rejected: narrowing R5 so no gap is recorded (erases the trace); pulling task 009 forward (SCOPE M → L) |
| Gate 2 | **Gate 2 cleared** | Both items decided; verification plan has no unresolved `❌`. Next: `/mango:execute 002` on `feat/002-contract-schema` |

## Session status

- **Last updated:** 2026-07-29 — Phase 5 (finalise) complete; PR #4 open
- **Current phase:** Phase 5 done. Ticket is **awaiting human review on PR #4** — note Phase 4 was skipped, so PR #4 is the *first* time another party sees this diff
- **Next action:** a human reviews [PR #4](https://github.com/cuongdinhngo/code-atlas/pull/4) and adjudicates the 2 disclosed caveats (capability-flag reporting → task 005; `validate()` type-check depth). On merge, set `status: done` in this frontmatter **and** `docs/BACKLOG.md:14` (R7.2)
- **Blocked on:** human review of PR #4. Frontmatter still `in-progress` — deliberately not flipped to `done` before the PR merges.
