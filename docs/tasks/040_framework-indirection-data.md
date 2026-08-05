---
id: 040
slug: framework-indirection-data
title: Framework indirection as data (rules file outside adapters/)
phase: 1.5
milestone: Framework
status: in-progress
depends_on: [039, 030]
---

## Goal
Resolve the dispatch frameworks move out of static PHP — facades, container-by-string, array
callables, string-callback hooks — without teaching the adapter any framework. Encode the
indirections as **data** consumed by a core-side enrichment pass, so `find_callers` on a Laravel or
WordPress repo stops being quietly useless while adapters stay standard-only (§19 agent-first pivot;
PLAN §1 enrichment layer).

## Scope / Deliverables
- A rules/data file **outside `adapters/`** (so the R2.2 grep-gate stays clean) mapping known
  indirections to concrete edges, e.g.:
  - `Facade::method` → concrete class method (`Cache::get` → `Illuminate\Cache\Repository::get`)
  - `add_action('hook', 'fn')` / string-callback → CALLS edge
  - `[Controller::class, 'method']` array callables → CALLS edge
  - container id → class aliases
- A core enrichment pass that applies the rules to add edges, tagged with provenance and confidence
  tier (reuse task 030's alias/literal-indirection edge machinery).

## Constraints
- The mapping is **data, not code**, and lives outside `adapters/` (R2.2); the core applies generic
  rules with **no** `if framework == …` branches (R1.1).
- Added edges carry a distinguishable provenance and tier (HEURISTIC or rule-RESOLVED) — never
  silently promoted to plain RESOLVED (tier honesty, PLAN §8.2).
- Deterministic (R4); **empty/off by default** — no rules loaded ⇒ graph unchanged.

## Acceptance criteria
- With a facade rule loaded, `Cache::get` yields an edge to the concrete `Repository::get`; a
  string-callback hook yields a CALLS edge; an array callable yields a CALLS edge (planted fixtures).
- With no rules loaded, the graph is unchanged.
- Rule-added edges carry provenance/tier distinguishable from adapter-emitted edges.

## Constraints on sequence
Depends on task 039 (vendor stubs) so facade/container targets exist as nodes to link to, and on task
030 (alias & literal-indirection edges) whose contract vocabulary these edges reuse.

## References
`code_atlas/resolver.py`; task 030 (alias/literal-indirection edges, contract v2); task 039 (vendor
stubs). PLAN §1 (non-goal: framework-magic as planned optional enrichment), §8.2 (tiers). `R1.1`,
`R2.2`, `R4`. Feedback origin: [`FEEDBACK.md`](../FEEDBACK.md) rounds 1 & 2 ("framework indirection as
data, not code — a rules file outside adapters/").

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 040 — Framework indirection as data (working doc)

- **Ticket:** 040 · local `docs/tasks/040_framework-indirection-data.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `738 passed` (`.venv/bin/pytest -q`), main @ post-039
  <!-- baseline exclusions: none -->
- **work_doc_mode:** embed (plain local-file ticket)

---

## Phase 0 — Refine

`REFINE: 2 unresolved surfaced | 2 want-decision ASSUMED | 8 how-decision resolved+cited | skip: no`

**INPUT KIND:** ticket

Exposure-checker ([challenger](51238823-b4e1-40c5-90a9-d68240a6479a)) reported 0 WANT; refine **overrides** on acceptance-bar forks the ticket leaves open (provenance encoding; what ships as rules).

**Settled wants (ASSUMED under standing approval “suggest and do the best option, and pass all gates” — awaiting Gate 1 ratification):**

| # | Want | Chosen direction | Becomes |
|---|------|------------------|---------|
| W1 | How are rule edges “distinguishable” without an edge `provenance` column? | **HEURISTIC tier** for all rule-emitted edges; **no contract bump** this card. AC fixtures prove edges the adapter would not emit alone. Stronger provenance (`provenance` field / `rule-RESOLVED` tier) → follow-up if needed. | AC3 + Constraints |
| W2 | Does the product ship framework rule packs? | **No auto-loaded packs.** Opt-in path(s) via config (`CA_INDIRECTION_RULES`); CI uses **fixture rules** only. Framework names live in data/fixtures outside `adapters/` (R2.2). | Scope / off-by-default |

**Resolved HOW + citation:**

| # | HOW | Resolution | Citation |
|---|-----|------------|----------|
| H1 | Rules location | Outside `adapters/` | ticket Constraints; R2.2 scans adapters only |
| H2 | Off by default | Blank/unset config → no rules → graph unchanged | ticket AC; mirror `stub_roots` |
| H3 | Who applies | Core enrichment near/after `resolve_edges` | ticket Goal; `indexer.py` resolve call sites |
| H4 | No framework branches | Generic rule apply; data carries names | R1.1 / R2.2 |
| H5 | Edge kinds | callables/facade → CALLS; container id→class → ALIASES; reuse 030 | ticket Scope/AC |
| H6 | Tier honesty | Never plain RESOLVED (W1 → HEURISTIC) | ticket Constraints; PLAN §8.2 |
| H7 | Determinism | Same rules+graph → same edges | R4 |
| H8 | Depends | 039 stubs + 030 ALIASES/literal | ticket sequence |

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| 0 refine | extractor (030/039 facts) | 1 | unmeasured (blocking retrieval) |
| 0 refine | mango:challenger (exposure-checker) | 1 | unmeasured (blocking retrieval) |

---

## Requirements matrix

`SECTIONS: 6 found (Goal, Scope, Constraints, Acceptance criteria, Constraints on sequence, References) | 6 decomposed`
`ROWS: G=1 R=2 C=3 AC=3 W=2 Seq=1`

| ID | Source | Verbatim (short) | Interpretation | Ph1 | Ph2 | Ph3/4 | Status |
|----|--------|------------------|---------------|-----|-----|-------|--------|
| G1 | Goal | indirections as data + core enrichment | Rules file + core apply pass | ticket | Approach | `enrichment.py` + proving | ✅ |
| R1 | Scope | rules outside adapters/ for facade/callback/array/container | Generic schema; fixture rules | R2.2 | CL | `fixtures/indirection/` | ✅ |
| R2 | Scope | enrichment adds edges; provenance+tier; reuse 030 | HEURISTIC edges; ALIASES/CALLS | W1 | CL | AC3 test | ✅ |
| C1 | Constraints | data not code; no framework branches | rules outside adapters/; core generic | R1.1/R2.2 | — | R1.1 gate | ✅ |
| C2 | Constraints | distinguishable; never silent RESOLVED | W1 HEURISTIC | W1 | — | AC3 test | ✅ |
| C3 | Constraints | deterministic; off by default | config None; identity test | H2/H7 | — | AC2 test | ✅ |
| AC1 | AC | facade + string-callback + array callable planted | assert CALLS targets | plant | proving | `test_indirection_enrichment` | ✅ |
| AC2 | AC | no rules → graph unchanged | two builds / off snapshot | C3 | — | `test_rules_off_*` | ✅ |
| AC3 | AC | rule edges distinguishable tier/provenance | HEURISTIC on rule edges | W1 | — | `test_rule_edges_*` | ✅ |
| Seq1 | Sequence | depends 039 + 030 | 039 done; reuse ALIASES/literal | BACKLOG | — | — | ✅ |
| W1 | refine | provenance encoding | HEURISTIC / no bump | Phase 0 | — | AC3 | ✅ |
| W2 | refine | no shipped packs | fixture + CA_INDIRECTION_RULES | Phase 0 | — | C3 | ✅ |

## AC validation

| AC | Ticket | Computed | Match | Falsifiable |
|----|--------|----------|-------|-------------|
| AC1 | three planted edge shapes | assert target_qname / kind on fixtures | Y | measurable |
| AC2 | no rules → unchanged | snapshot equality stubs-off style | Y | measurable |
| AC3 | distinguishable | rule edges `confidence_tier==HEURISTIC` | Y (under W1) | measurable |

`CLARIFICATION: 2 raised | 2 ASSUMED standing | j=0 (pending Gate 1 ratify of ASSUMED)`
`TRACK: backend` · `SCOPE: M` · `TIER: full`
`RULE SECTIONS: §1 ✅ R1.1 · §2 ✅ R2.2 · §3 ✅ no bump (W1) · §4 ✅ R4 · §5 N/A · §6 ✅ tests · §7 ✅ docs`

### Gap

| Current | Target |
|---------|--------|
| No rules/enrichment | Opt-in rules file + core apply pass |
| Facade/callback CALLS missing | HEURISTIC edges when rules loaded |

### Gate 1

**ASSUMED W1–W2 ratified** by standing approval 2026-08-05 (“suggest and do the best option, and pass all gates”). **cleared.**

---

## Phase 2 — Design

### Approach

1. Config knob `indirection_rules` / `CA_INDIRECTION_RULES` (comma-separated repo-relative JSON paths; blank → off).
2. Module `code_atlas/enrichment.py`: load rules; emit HEURISTIC `ALIASES` + `CALLS` onto synthetic path `.code-atlas/indirection-rules`; `upsert_file` + `replace_file_rows` (idempotent). Missing rule file → `ConfigError` (R5.3).
3. Call `apply_indirection_rules` after parse / before `resolve_edges` on full, incremental, and (no-op if unset) leave reparse alone unless rules set — full/incremental only so one-file reparse stays cheap; rules are whole-graph.
4. Facade AC: plant CALLS to `Facades\Cache::get` + Repository method node; rules ALIASES facade→Repository; resolve remaps (030).
5. String/array AC: rules `calls` entries synthesize HEURISTIC CALLS (framework hooks have no adapter emission).
6. Off path: no config → enrichment skipped; reconcile drops synthetic file if present; graph matches rules-absent build.
7. Tests + PLAN/CONVENTION/BACKLOG; KNOBS coverage.

### Rejected alternatives

| Rejected | Why |
|----------|-----|
| Contract bump (`provenance` / `rule-RESOLVED`) | W1 — HEURISTIC + fixture distinguishability; YAGNI |
| Auto-load Laravel/WP packs in-repo | W2 — opt-in paths only; R2 spirit |
| Enrich inside PHP adapter | Violates R2.2 / ticket |
| Parse rule call-sites from AST in core | Language knowledge in core (R1.1); data `calls` list is enough |

### Assumptions

| Assumption | Tag |
|------------|-----|
| 030 alias remap of `Class::method` via ALIASES works for facades | verified (`resolver._lookup_raw`) |
| Synthetic file path survives reconcile when re-applied each build | verified (replace after reconcile) |

### Change list

| # | Change | File | Ph2 rows | k/N |
|---|--------|------|----------|-----|
| 1 | `indirection_rules` knob | `code_atlas/config.py` | H2,W2,C3 | 1/1 |
| 2 | load+apply enrichment | `code_atlas/enrichment.py` | G1,R1,R2,C1–C2 | 1/1 |
| 3 | wire before resolve | `code_atlas/indexer.py` | H3,AC* | 1/1 |
| 4 | proving + config tests | `tests/test_indirection_enrichment.py`, `test_config.py` | AC1–3 | 1/1 |
| 5 | fixture rules + planted PHP | `tests/fixtures/indirection/` | AC1 | 1/1 |
| 6 | Docs | PLAN, CONVENTION, BACKLOG, this doc | §7 | 1/1 |
| 7 | module-count guards | `test_core_is_language_agnostic.py`, `test_sql_confinement.py` | R1.1/R5 | 1/1 |

### Verification plan

| AC | Risk layer | Proof | Match |
|----|------------|-------|-------|
| AC1 | integration | planted PHP + rules → assert edges | ✅ |
| AC2 | integration | rules off snapshot identical | ✅ |
| AC3 | logic | rule edges HEURISTIC | ✅ |

**Proving test:** `tests/test_indirection_enrichment.py::test_facade_rule_resolves_call_to_concrete_method`
**Invocation:** `.venv/bin/pytest tests/test_indirection_enrichment.py -q`

### Gate 2

Standing approval clears Gate 2. **cleared.**

---

## Phase 3 — Execute

- Branch: `feat/040-framework-indirection-data`
- Commits (logical units; no AI co-author trailer):
  - `5926e2d` feat(040): apply framework indirection rules as core enrichment data.
  - (pending) docs(040): honesty fixes from review — PLAN §1, CONVENTION layout, R1.4.
- Proving test added: `tests/test_indirection_enrichment.py::test_facade_rule_resolves_call_to_concrete_method` ✅
- **Verification sweep — BOTH axes.** *File axis:* zero stray references ✅ · diff ⊆ approved list ✅ (row 7 = companion module-count guards for new `enrichment.py`) · each hunk maps to a row ✅. *Behaviour axis:* all Gate-2 Approach bullets `implemented-as-approved`.
- **Design-conformance deviations:** none

| Approved Gate-2 bullet | Status |
|------------------------|--------|
| 1 Config knob | implemented-as-approved |
| 2 enrichment.py HEURISTIC + synthetic file | implemented-as-approved |
| 3 wire full/incremental before resolve | implemented-as-approved |
| 4 Facade ALIASES + 030 remap | implemented-as-approved |
| 5 String/array CALLS from rules | implemented-as-approved |
| 6 Off path / remove synthetic | implemented-as-approved |
| 7 Tests + docs + knobs | implemented-as-approved |

- Suite: `.venv/bin/pytest -q` → **746 passed** (baseline 738 + new tests)

## Phase 4 — Review

- reviewer verdict: **CHANGES REQUESTED** → conditional LGTM (findings 1–3 docs) → **verify-only clean** ([reviewer](f8e3290e-868d-4c23-97b1-341273ffcf27))
- Re-review path: **verify-only** (main-loop) — findings 1–3 landed; proving+guards 124 passed; no scope change
- challenger (ticket-blind): **13 met · 0 not met · 0 can't tell** ([challenger](b19a2b27-043b-466d-b500-05bf2aa137ea))
- security agent: n/a
- Scope reconciliation: file axis ⊆ list ✅; behaviour axis all implemented-as-approved ✅; review doc honesty fixes within docs surface
- Regression: proving + config + language-agnostic + sql-confinement green
- Proving test: green; would fail without enrichment wire / rules (facade remap absent)
- Layer-match: AC1–3 integration/logic ✅
- Frontend rubric: n/a
- Proof-manifest: n/a
- `Ph3/4 proven by` filled: k=N (12/12 matrix rows ✅)
- **Clean?** yes
- **Reviewed at:** pending commit SHA after docs fix · reviewed files: full `main...HEAD` set including `docs/PLAN.md`, `docs/CONVENTION.md`, `docs/ENGINEERING_RULES.md`, `docs/tasks/040_framework-indirection-data.md` (working-doc path exempt for further bookkeeping)

## Session status

| Field | Value |
|-------|-------|
| Phase | 4 review clean → 5 finalise |
| Gates | 1 ✅ · 2 ✅ · review ✅ (standing) |
| Blocked on | push / PR (need separate explicit yes) |
