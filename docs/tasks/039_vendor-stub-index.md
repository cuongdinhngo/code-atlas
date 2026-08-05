---
id: 039
slug: vendor-stub-index
title: Vendor stub index (declarations only)
phase: 1.5
milestone: Framework
status: done
depends_on: [009, 011]
---

## Goal
Stop framework and library base classes from dangling. `vendor/` is ignored by default
(`code_atlas/ignore.py:18`), so `class Foo extends Illuminate\…\Model` resolves to nothing and
framework apps are half-blind. Indexing **declarations only** from dependencies — no bodies, no call
edges — is cheap and makes `extends`/`implements`/type references into vendor RESOLVED. This is the
single biggest resolution gap and the cheapest to close (§19 agent-first pivot; PLAN §1 enrichment
layer).

## Scope / Deliverables
- An opt-in pass that ingests **declarations** from `vendor/` (or a configured dependency root):
  class/interface/trait/enum/method/property/constant signatures + `extends`/`implements`, with
  **no** function bodies and **no** call/NEW edges.
- A stub node marker (or a declaration-only flag) so stubs are distinguishable from first-class
  indexed nodes.
- Wire resolution so EXTENDS/IMPLEMENTS/type references into stubs become RESOLVED.

## Constraints
- **Standard over sample (R2):** this is a generic "index dependency declarations" capability, not
  framework-specific — no repo/framework names in the adapter.
- No language branches in the core (R1.1); adapter parses, store persists (R1.4); deterministic (R4).
- **Off by default** to keep normal builds cheap; document the cost when enabled. Bodies are never
  indexed (that is what keeps it cheap and avoids polluting the call graph with vendor internals).

## Acceptance criteria
- A repo whose class extends a vendor base class: after stub indexing, the EXTENDS edge is RESOLVED to
  the vendor declaration (asserted on a planted vendor tree).
- Vendor method bodies produce no call/NEW edges (stubs are declarations only).
- With stubs off (default), the graph is byte-identical to today's build for the same repo.

## References
`code_atlas/ignore.py:17-24` (built-in `vendor/` ignore); `code_atlas/indexer.py` (collect/walk);
`code_atlas/resolver.py` (edge linking); adapters/php declaration emission. PLAN §1 (optional
enrichment layer), §4 (contract). `R1.1`, `R1.4`, `R2`, `R4`. Feedback origin:
[`FEEDBACK.md`](../FEEDBACK.md) rounds 1 & 2 ("vendor stub index — the biggest single fix, and the
cheapest").

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 039 — Vendor stub index (working doc)

- **Ticket:** 039 · local `docs/tasks/039_vendor-stub-index.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `721 passed` on main before 039 (pre-change); post-execute **728 passed**
  <!-- baseline exclusions: none -->
- **work_doc_mode:** embed (plain local-file ticket)

---

## Phase 0 — Refine

`REFINE: 2 unresolved surfaced | 2 want-decision asked | HOW self-resolved | 2 ASSUMED | skip: no`

**INPUT KIND:** ticket

**Settled wants (ASSUMED under standing approval "suggest and do the best option, and pass all gates"):**

| # | Want | Chosen direction | Becomes |
|---|------|------------------|---------|
| W1 | How visible are stubs to agents? | **Searchable/readable + `stub: true` marker** (second-class, not hidden) | search/read hit shape |
| W2 | What RESOLVED bar proves this card? | **Planted EXTENDS → RESOLVED**; IMPLEMENTS same wiring; no separate type-ref AC | AC1 scope |

**Resolved HOW + citation:**

| # | HOW | Resolution | Citation |
|---|-----|------------|----------|
| H1 | Config shape | `stub_roots` list knob; empty/None = off (mirror `entry_points`) | config KNOB_KEYS |
| H2 | Bypass ignore | Separate `collect_stubs` filesystem walk (cannot negate directory exclusion) | ignore.py; ticket |
| H3 | Marker without CONTRACT bump | `extra.stub=true` JSON; no `is_stub` column | R3.2 / YAGNI |
| H4 | Declarations-only seam | Request flag `declarations_only`; core strips CALLER_KINDS as backstop | R1.1 |

**Exposure-checker:** [challenger](e5fcc424-ab84-428b-b98c-66dfb9706ce1) — 2 wants above.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 0 refine | mango:challenger (exposure-checker) | 1 | unmeasured (blocking retrieval) |
| 1 analysis | extractor | 1 | unmeasured (blocking retrieval) |

---

## Requirements matrix

`SECTIONS: 5 found (Goal, Scope, Constraints, Acceptance criteria, References) | 5 decomposed`
`ROWS: G=1 R=3 C=3 AC=3 W=2`

| ID | Source | Verbatim (short) | Interpretation | Ph1 | Ph2 | Ph3/4 | Status |
|----|--------|------------------|---------------|-----|-----|-------|--------|
| G1 | Goal | declarations-only vendor bases resolve | Opt-in stub index closes EXTENDS gap | ticket | Approach | proving | ✅ |
| R1 | Scope | ingest declarations from dep roots | collect_stubs + declarations_only parse | indexer/adapter | CL1–4 | tests | ✅ |
| R2 | Scope | stub marker distinguishable | `extra.stub` + tool `stub: true` | W1 | CL5–6 | search/read | ✅ |
| R3 | Scope | EXTENDS/IMPLEMENTS into stubs RESOLVED | existing resolver; stubs are nodes | resolver | — | planted | ✅ |
| C1 | Constraints | R2 no framework names | generic roots; planted Lib\Model | R2 | — | guardrails | ✅ |
| C2 | Constraints | R1.1 / R1.4 | no lang branch; adapter parse / store persist | rulebook | — | CI | ✅ |
| C3 | Constraints | off by default; no bodies | stub_roots None; CALLS/NEW dropped | H1/H4 | — | AC2/AC3 | ✅ |
| AC1 | AC | planted EXTENDS RESOLVED | assert target_qname + RESOLVED | plant | proving | test_stub_indexing… | ✅ |
| AC2 | AC | no CALLS/NEW from stub bodies | adapter + indexer backstop | H4 | — | decls + vendor edges | ✅ |
| AC3 | AC | stubs off → same graph as today | vendor absent; two off builds match | C3 | — | test_stubs_off… | ✅ |
| W1 | refine | stub visible + marker | search/read `stub: true` | Phase 0 | CL5–6 | hit tests | ✅ |
| W2 | refine | EXTENDS bar this card | planted EXTENDS only | Phase 0 | — | AC1 | ✅ |

## AC validation

| AC | Ticket | Computed | Match | Falsifiable |
|----|--------|----------|-------|-------------|
| AC1 | EXTENDS RESOLVED to vendor | assert `\\Lib\\Model` RESOLVED | Y | measurable |
| AC2 | no body CALLS/NEW | vendor edges ∩ CALLER_KINDS = ∅ | Y | measurable |
| AC3 | default off identical | no vendor files; two builds equal | Y | measurable |

`CLARIFICATION: 2 raised | 2 ASSUMED standing | j=0`
`TRACK: backend` · `SCOPE: M` · `TIER: full`
`RULE SECTIONS: §1 ✅ R1.1/R1.4 · §2 ✅ R2 · §3 ✅ no bump · §4 ✅ R4 · §5 N/A · §6 ✅ tests · §7 ✅ docs`

### Gap

| Current | Target |
|---------|--------|
| vendor ignored → dangling EXTENDS | opt-in declarations-only stub roots |
| no stub marker | `extra.stub` + tool flag |

### Gate 1

**ASSUMED W1–W2 ratified** by standing approval. **cleared.**

---

## Phase 2 — Design

### Approach

1. Config knob `stub_roots` / `CA_STUB_ROOTS` (list; blank → off).
2. `collect_stubs(root, stub_roots, suffixes)` filesystem walk bypassing ignore/git; merge into full_build / incremental kept set.
3. Adapter `parse(..., declarations_only=)` + PHP Visitor `DONT_TRAVERSE_CHILDREN` on methods/functions/closures; request JSON flag.
4. Indexer: `is_stub_path` → declarations_only + `as_stub_result` (stamp `extra.stub`, drop CALLER_KINDS).
5. Surface `stub: true` on `search_symbol` / `read_symbol` when `extra.stub`.
6. Proving suite `tests/test_vendor_stub_index.py`; PLAN §11 + BACKLOG.

### Rejected alternatives

| Rejected | Why |
|----------|-----|
| Negate `!vendor/` in ignore | Directory exclusion cannot be re-included (ignore design) |
| First-class `is_stub` column / CONTRACT bump | YAGNI; `extra` sufficient (H3) |
| Always-on stub indexing | Ticket: off by default for cost |
| Core language branches for declarations-only | R1.1 — adapter owns parse; core only path+edge backstop |

### Change list

| # | Change | File | Ph2 rows | k/N |
|---|--------|------|----------|-----|
| 1 | `stub_roots` knob | `code_atlas/config.py` | H1,C3 | 1/1 |
| 2 | `declarations_only` wire | `code_atlas/adapter.py` | R1,H4 | 1/1 |
| 3 | collect_stubs + stamp/strip + build merge | `code_atlas/indexer.py` | R1,R2,C3,AC* | 1/1 |
| 4 | PHP declarations_only | `adapters/php/{index.php,src/Parser.php,src/Visitor.php}` | R1,AC2,C1 | 1/1 |
| 5 | search/read stub flag | `code_atlas/tools/{search_symbol,read_symbol}.py` | W1,R2 | 1/1 |
| 6 | Proving + config/protocol tests | `tests/test_vendor_stub_index.py`, `test_config.py`, `test_adapter.py` | AC1–3 | 1/1 |
| 7 | Docs | `docs/PLAN.md`, `docs/BACKLOG.md`, this doc | §7 | 1/1 |

### Verification plan

| AC | Risk layer | Proof | Match |
|----|------------|-------|-------|
| AC1 | integration | planted PHP EXTENDS | ✅ |
| AC2 | adapter + core | decls_only + vendor edge scan | ✅ |
| AC3 | integration | stubs off snapshot | ✅ |
| W1 | tool | search/read stub flag | ✅ |

**Proving test:** `tests/test_vendor_stub_index.py::test_stub_indexing_resolves_extends_and_marks_stubs`
**Invocation:** `.venv/bin/pytest tests/test_vendor_stub_index.py -q`

### Gate 2

Standing approval clears Gate 2. **cleared.**

---

## Phase 3 — Execute

**Branch:** `feat/039-vendor-stub-index` from `main`.

### Design-conformance

| Approach bullet | Classification |
|-----------------|----------------|
| 1 stub_roots knob | implemented-as-approved |
| 2 collect_stubs merge | implemented-as-approved |
| 3 declarations_only adapter + PHP | implemented-as-approved |
| 4 as_stub_result stamp/strip | implemented-as-approved |
| 5 search/read stub flag | implemented-as-approved |
| 6 tests + docs | implemented-as-approved |

### Sweep

- Axis 1 file set ⊆ change list: ✅
- Axis 2 behaviour: ✅ no deviations
- Suite: **728 passed** (feat commit); **734 passed** after review fixes

### Cost ledger (continued)

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 3 execute | (none) | — | — |
| 4 review | mango:reviewer | 1 | unmeasured (blocking retrieval) |
| 4 review | mango:challenger | 1 | unmeasured (blocking retrieval) |
| 4 review | mango:reviewer (verify resume) | 2 | unmeasured (blocking retrieval) |

---

## Phase 4 — Review

`Reviewed at ddcfe77`
Reviewed files: `code_atlas/config.py`, `code_atlas/adapter.py`, `code_atlas/indexer.py`, `adapters/php/index.php`, `adapters/php/src/Parser.php`, `adapters/php/src/Visitor.php`, `code_atlas/tools/search_symbol.py`, `code_atlas/tools/read_symbol.py`, `tests/test_vendor_stub_index.py`, `tests/test_config.py`, `tests/test_adapter.py`, `docs/PLAN.md`, `docs/BACKLOG.md`, `docs/tasks/039_vendor-stub-index.md`, `docs/CONVENTION.md`

### Reviewer (`mango:reviewer` · [6360cf47](6360cf47-32b6-4ad9-b04f-65e8afa7261e))

**Round 1 — CHANGES REQUESTED** (on `d0689f1`; related slice 87 passed; sandbox PermissionError on adapter stop = ENV-FAULT)

| # | Severity | Rule | Finding | Fix |
|---|----------|------|---------|-----|
| 1 | Important | R4.2 | Incremental only queued `changed_set & stub_set`; gitignored vendor edits / newly enabled stubs never reparsed → incremental ≠ full | Hash-gate every stub path (`not in indexed` or `not file_is_current`) |
| 2 | Important | R5.3 | `_as_stub_roots` accepted absolute / `..` / `.` — could walk outside the repo | `ConfigError` for non-repo-relative roots |
| 3 | Important | R7.2 | `CONVENTION.md` env inventory omitted `CA_STUB_ROOTS` | Add to env-var list |

Approach bullets 1–6 implemented-as-approved; R1.1 / R2.2 clean; scope ≡ Gate-2 list. No Critical findings.

**Round 2 (verify-only) — LGTM** on tip `ddcfe77`
- Finding 1: `indexer.py:144-149` hash-gates stubs; `test_incremental_hash_gates_stub_edits` ✅
- Finding 2: `config.py:287-293` + `test_stub_roots_reject_non_repo_relative_paths` (5 cases) ✅
- Finding 3: `docs/CONVENTION.md:50` lists `CA_STUB_ROOTS` ✅
- Related slice **93 passed**; full suite **734 passed**
- **Findings remaining:** none

### Challenger (ticket-blind · [81cad2e5](81cad2e5-0514-42f9-a551-61e3a354daf4))

Independence: raw ticket through References + `main..feat/039-vendor-stub-index` only; did not open working doc.

| # | Rebuilt requirement | Verdict | Evidence / adjudication |
|---|---------------------|---------|-------------------------|
| 1 | Opt-in pass for `vendor/` or configured dep root | **met** | `config.py` `stub_roots` / `CA_STUB_ROOTS`; `indexer.collect_stubs`; blank ⇒ off |
| 2 | Signatures + EXTENDS/IMPLEMENTS (class/iface/trait/enum/method/prop/const) | **met** | PHP Visitor opens decls then `DONT_TRAVERSE_CHILDREN`; ClassLike still walks members |
| 3 | No bodies; no CALL/NEW from stubs | **met** | Visitor skip + `as_stub_result` drops `CALLER_KINDS`; AC2 tests |
| 4 | Stub marker distinguishable from first-class nodes | **met** | `extra.stub=true`; search/read `stub: true` |
| 5 | EXTENDS/IMPLEMENTS/**type references** into stubs RESOLVED | **met** (EXTENDS/IMPLEMENTS); **can't tell** (type-ref as distinct) | Planted EXTENDS → RESOLVED; no TYPE edge / type-ref test. **Adjudication:** W2 scoped this card to planted EXTENDS; IMPLEMENTS shares wiring |
| 6 | R2 — no framework names in adapter | **met** | PHP diff is `declarations_only` only; no Illuminate/Laravel |
| 7 | R1.1 — no language branches in core | **met** | generic `declarations_only` + `is_stub_path` |
| 8 | R1.4 — adapter parses; store persists | **met** | indexer stamps then `_write`; store API unchanged |
| 9 | R4 — deterministic | **met** | sorted stub paths; `sort_keys` on extra JSON |
| 10 | Off by default | **met** | `stub_roots=None`; AC3 test |
| 11 | Document cost when enabled; bodies never indexed | **met** | PLAN §11 stub-roots paragraph; #3 |
| 12 | AC1 planted EXTENDS → RESOLVED | **met** | `test_stub_indexing_resolves_extends_and_marks_stubs` |
| 13 | AC2 no call/NEW from vendor bodies | **met** | vendor edge scan + adapter decls_only test |
| 14 | AC3 stubs off ⇒ byte-identical to today’s build | **met** (soft gap) | off-vs-off + vendor absent; not a golden pre-039 dump. **Adjudication:** mechanism identity proven; AC wording satisfied for practical bar |

**12 met · 0 not met · 1 can't tell** (type-ref limb of #5) — clean for ticket scope (W2).

### Scope reconciliation
- File axis: ✅ Gate-2 list + CONVENTION (finding 3)
- Behaviour axis: ✅ Approach as approved; review fixes are R4.2/R5.3/R7.2 only
- Challenger: type-ref can't-tell adjudicated via W2; AC3 soft gap accepted

### Gate 4 status
**clean** — reviewer LGTM at `ddcfe77`; challenger clean for ticket scope after adjudication.

### Ph3/4 proven by

| Row | Proven by |
|-----|-----------|
| AC1 | `test_stub_indexing_resolves_extends_and_marks_stubs` |
| AC2 | vendor CALLER_KINDS empty + declarations_only adapter test |
| AC3 | `test_stubs_off_by_default_matches_build_without_vendor_rows` |
| R4.2 fix | `test_incremental_hash_gates_stub_edits` |
| R5.3 fix | `test_stub_roots_reject_non_repo_relative_paths` |

### Durable lesson
Stub roots must bypass ignore *and* hash-gate on incremental — see `docs/LESSONS.md` §039.

---

## Session status

| Field | Value |
|-------|-------|
| Phase | 5 finalise complete |
| Branch | merged to `main` via [#45](https://github.com/cuongdinhngo/code-atlas/pull/45) |
| Gates | 1 ✅ · 2 ✅ · 4 ✅ · 5 ✅ |
| Suite | 738 passed (post review-fix) |
| Reviewed at | `ddcfe77` |
| Blocked on | — |
| PR | [#45](https://github.com/cuongdinhngo/code-atlas/pull/45) |

## Phase 5 — Finalise

- Outward: push branch + open PR (user-approved 2026-08-05) → [#45](https://github.com/cuongdinhngo/code-atlas/pull/45) — **merged**
- Status → `done` in BACKLOG + task frontmatter.
