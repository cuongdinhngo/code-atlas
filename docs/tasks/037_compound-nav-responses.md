---
id: 037
slug: compound-nav-responses
title: Compound nav responses (call-site line) + consolidation A/B
phase: 1.5
milestone: Agent-fit
status: todo
depends_on: [013, 034]
---

## Goal
Make a nav answer complete in one call. The agent's next call after `find_callers` is always
"show me" — so returning the call-site line with each caller removes a round-trip, and round-trips
are the real token cost, not rows. Separately, evaluate consolidating the three relation tools into
one `find_relations(qname, relation)` — but decide it with the benchmark (034), not by assertion
(§19 agent-first pivot).

## Scope / Deliverables
- `find_callers` / `find_references` optionally return each site's source line/snippet (the line range
  is already known via `nodes`/`edges` — `read_symbol.py:76-78`, `file_outline.py:71-72`).
- An A/B experiment (measured on task 034): the three tools `find_callers`/`find_references`/
  `find_implementations` as-is vs a single `find_relations(qname, relation)`. Record the result and a
  decision; keep the winner.

## Constraints
- Token-frugal by default — the snippet is opt-in or capped (a compound response must not bloat the
  common case).
- No language branches (R1.1); store owns SQL (R1.4).
- **Consolidation is held behind the benchmark.** Merging tools trades schema tokens for a muddier
  per-tool description and collides with one-module-per-tool (R1.2) — do it only if 034 shows a net
  win; otherwise keep the three tools and ship only the compound response.

## Acceptance criteria
- `find_callers` can return each caller with its call-site line; default output stays token-frugal
  (snippet opt-in/capped), asserted.
- The 034 benchmark is run comparing the 3-tool surface vs `find_relations`, and the decision is
  recorded with its numbers.
- The chosen surface passes the full suite; if tools are merged, the contract/tool docs are updated.

## References
`code_atlas/tools/find_callers.py`, `find_references.py`, `find_implementations.py`;
`nav_result.py`; `read_symbol.py:76-78` (line ranges); task 034 (benchmark). PLAN §19; R1.2.
Feedback origin: [`FEEDBACK.md`](../FEEDBACK.md) round 3 ("fewer, more compound tools; round-trips
are the real cost").

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 037 — Compound nav responses + consolidation A/B (working doc)

- **Ticket:** 037 · local `docs/tasks/037_compound-nav-responses.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `684 passed in 37.36s` (`.venv/bin/pytest -q`), main @ `a1fd7b5`
  <!-- baseline exclusions: none -->
- **work_doc_mode:** embed (plain local-file ticket, not a breakdown scaffold stub)

---

## Phase 0 — Refine

`PREMISE: 10 reference(s) checked | 0 missing | 2 stale line-refs (non-blocking) | 0 ambiguous (blocking)`
`REFINE: 3 unresolved surfaced | 3 want-decision asked | 4 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise check** — every source the ticket cites as already existing resolves:

| # | Reference | Resolves | Note |
|---|-----------|----------|------|
| 1–3 | `find_callers.py` / `find_references.py` / `find_implementations.py` | ✅ | all three present |
| 4 | `nav_result.py` | ✅ | `edge_hit` **already** emits `file` + `line` (`:58-59`) |
| 5 | `read_symbol.py:76-78` (line ranges) | ⚠️ stale line-ref | capability resolves; 035 rewrote the file, ranges now at `:77-82` |
| 6 | `file_outline.py:71-72` | ⚠️ stale line-ref | those lines are now `_repo_relative` |
| 7 | task 034 benchmark (`scripts/tokens_to_answer.py`) | ✅ | 9 fixture questions, gate at ratio ≥ 0.24 |
| 8 | PLAN §19 | ✅ | agent-first pivot |
| 9 | R1.2 (one seam / YAGNI) | ✅ | `ENGINEERING_RULES.md:20` |
| 10 | FEEDBACK.md round 3 | ✅ | "round-trips are the real cost" |

Not premise-falsified: both stale refs are drifted line numbers under 035, not missing sources.

**Two findings from the scan that shape the whole card:**

- **F1 — the call site is already known.** `edges` carry `file_path` + `line` (`contract.EDGE_FIELDS`)
  and `edge_hit` already returns both. Deliverable 1 therefore adds **source text**, not location.
- **F2 — the current benchmark cannot see either A/B.** `run_atlas_path` counts
  `estimate_tokens(args) + estimate_tokens(response)` per call (`tokens_to_answer.py:106-107`) —
  no tool-schema term — and **all 9 questions are `get_index_status` + exactly one tool call**, so no
  recipe today chains `find_callers → read_symbol`. Measuring "a removed round-trip" or "a smaller
  tool surface" against the harness as it stands would return **0 difference by construction**, which
  would look like evidence and be an artifact. Both A/Bs need the harness extended first.

**Settled wants (want-decision — ASSUMED under standing approval 2026-08-04 "suggest and do the best
option, and pass all gates").**

| # | The want (in want-language) | Chosen direction | Becomes |
|---|-----------------------------|------------------|---------|
| 1 | When I ask who calls X, do I always get the call text, or only when I ask for it? | **Opt-in flag, default off** — `include_source=False` | W1 |
| 2 | How much of the call site do I want — the one line, or lines around it? | **The single call-site line, trimmed, per-line char cap** | W2 |
| 3 | The ticket says decide consolidation *with* the benchmark, but the benchmark is blind to it (F2). Extend the metric, or declare it undecidable and keep three tools? | **Extend the metric** — add a schema-cost term + a compound question, then follow the numbers | W3 |

*Why W1 over "always capped":* default-off leaves every existing response byte-identical, so the
already-thin ratio headroom (0.286 vs floor 0.24) cannot regress, and "token-frugal by default"
becomes assertable rather than argued.
*Why W2 over ±context:* the agent's follow-up is "show me the call" — one line answers it; ±2 lines
multiplies the added cost ~5× for the same answer.

**Resolved direction + citation (how-decision).**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | Where the snippet text comes from | Read `edge.file_path` at `edge.line`; tool layer reads files, store stays SQL-only | R1.4; `read_symbol.py` already reads source in the tool layer |
| 2 | Which tools get the flag | `find_callers` + `find_references` only — the ticket names those two | ticket Scope L19 |
| 3 | Cap shape | Per-line char cap **and** the existing `CA_MAX_RESULTS` row cap bounds site count | ticket Constraint L26-27 |
| 4 | Consolidation candidate lives where | Measured in the benchmark **first**; shipped into `code_atlas/` only if it wins | ticket C L29-31; R1.2 |

**ASSUMED (awaiting ratification) — ratified by standing approval at Gate 1.**

| # | Assumed choice | Why ASSUMED | Reverses prior? |
|---|----------------|-------------|-----------------|
| 1 | W1 opt-in `include_source`, default off | handed back as "best option" | no |
| 2 | W2 single line + char cap | handed back as "best option" | no |
| 3 | W3 extend the metric (schema term + compound question) rather than declare undecidable | handed back as "best option" | no |

**Want clauses (one matrix row each):**
- **W1:** `include_source` defaults off; a default call's payload is unchanged from today.
- **W2:** a site snippet is one trimmed line, capped in characters.
- **W3:** the consolidation decision cites numbers produced by an extended 034 metric.

**Constraints surfaced from the scan (beyond the ticket's own):**
- **C4 (derived, R4 + 035):** a snippet quoted from a **drifted** call-site file would be a
  confident lie. 035's `FreshnessGuard` refreshes only the **subject** file, and call sites live in
  *other* files (`docs/tasks/035…md` Approach #4, adjudicated). So a site snippet must be quoted only
  when that file's indexed hash still matches disk, and marked otherwise. Without this the compound
  response actively degrades trust — the opposite of §19.

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope / Deliverables, Constraints, Acceptance criteria) | 4 decomposed`
`ROWS: G=2 R=2 C=4 AC=3 W=3 → 14`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 | Status |
|----|--------|------------------|----------------|--------------|-----|-------|--------|
| G1 | Goal | "make a nav answer complete in one call" | Call-site text rides along, so "show me" needs no second call | ticket L12-14; F1 (`nav_result.py:58-59`) | Approach 1-2 | 107 vs 176 tokens | ✅ |
| G2 | Goal | "decide it with the benchmark, not by assertion" | Consolidation verdict must cite measured numbers | ticket L15-16; F2 | Approach 3-4 | A/B tables | ✅ |
| R1 | Scope | `find_callers`/`find_references` optionally return each site's line/snippet | `include_source` flag on both | ticket L19-20 | Approach 1-2 | 9 flag tests | ✅ |
| R2 | Scope | A/B: 3 tools vs one `find_relations`; record result + decision; keep winner | Measured A/B + recorded verdict | ticket L21-23 | Approach 3-4 | A/B + verdict | ✅ |
| C1 | Constraints | "token-frugal by default — opt-in or capped" | Default payload unchanged; snippet capped | ticket L26-27 | Approach 2 | byte-equality test | ✅ |
| C2 | Constraints | no language branches (R1.1); store owns SQL (R1.4) | No `if language`; file reads in tool layer | ENGINEERING_RULES §1 | Approach 1 | grep-gates green | ✅ |
| C3 | Constraints | consolidation held behind the benchmark; else keep 3 tools | Merge only on a measured net win | ticket L29-31; R1.2 | Approach 4 | verdict = keep 3 | ✅ |
| C4 | derived | (R4 + 035) never quote a drifted file as fact | Hash-check the site file; mark when stale | 035 Approach #4; `freshness.py` | Approach 1 | mutation-checked | ✅ |
| AC1 | AC | callers return call-site line; default stays frugal, **asserted** | Two tests: flag on, and default byte-identical | ticket L34-35 | Approach 1-2 | flag on/off tests | ✅ |
| AC2 | AC | benchmark run 3-tool vs `find_relations`; decision recorded with numbers | Extended metric + recorded verdict | ticket L36-37 | Approach 3 | numbers recorded | ✅ |
| AC3 | AC | chosen surface passes full suite; docs updated if merged | Full `pytest` green + doc sync | ticket L38 | Approach 5 | 702 passed | ✅ |
| W1 | refine | `include_source` default off | Default call unchanged | Phase 0 | Approach 2 | default unchanged | ✅ |
| W2 | refine | one trimmed line, char-capped | Snippet shape | Phase 0 | Approach 1 | cap test | ✅ |
| W3 | refine | extend the 034 metric rather than declare undecidable | Schema term + compound question | Phase 0 / F2 | Approach 3 | schema term real | ✅ |

## AC validation

| AC | Ticket says | Computed | Match | Falsifiable? |
|----|-------------|----------|-------|--------------|
| AC1 | call-site line available; default frugal, asserted | flag on ⇒ `source` per hit; flag off ⇒ payload equal to today's | Y | measurable — byte-equality assertion, and a degraded case (drifted file) must actually omit |
| AC2 | benchmark comparing the two surfaces, decision + numbers | extended metric emits both surfaces' totals; verdict recorded in this doc | Y | measurable — two numbers, recorded |
| AC3 | full suite; docs if merged | `pytest -q` green; PLAN/CONVENTION/runbook synced | Y | measurable — **was falsely Y at review round 1: `CONVENTION.md` was listed in scope but never touched, and its §6 "no source bodies from nav tools" rule contradicted `include_source`. Synced in round 2.** |

**AC2 honesty note.** AC2 as written is satisfiable *vacuously* against today's harness (run it, get
0 difference, "record" that). That would be a false green — see F2. The AC is therefore read as
requiring a metric that **can** distinguish the surfaces, which is why W3 exists.

## Inventory

`TOOLS TOUCHED N=2:` (1) `find_callers` (2) `find_references`
`SURFACES MEASURED N=2:` (A) three relation tools as-is (B) one `find_relations(qname, relation)`
`TRACK: backend`
`RULE SECTIONS: §1 ✅ (R1.1/R1.2/R1.4) · §2 N/A (no adapter change) · §3 N/A (no contract change — response shape only, as 033) · §4 ✅ (R4 determinism ⇒ C4) · §6 N/A · §7 ✅ (docs + token ledger)`
`CLARIFICATION: 3 raised | 3 ASSUMED via standing approval | j=0 at Gate 0`
`SCOPE: M` · `TIER: full` (two deliverables, one of them a measurement)

### Gap

| Current | Target | Path |
|---------|--------|------|
| `edge_hit` returns `file` + `line`, no text | optional `source` per hit | `nav_result.py:44-64` |
| No way to see a call without a second call | `include_source=True` on two tools | `find_callers.py`, `find_references.py` |
| Benchmark counts per-call args+response only | plus a per-session tool-schema term | `tokens_to_answer.py:93-111` |
| All 9 recipes are single-tool | one compound question with a 2-recipe A/B | `tokens_to_answer_questions.json` |
| Consolidation undecided, unmeasurable | measured verdict recorded | this doc |

### Blast radius

Entry: `nav_result.edge_hit` (+ a new site-snippet helper), `find_callers`, `find_references`,
`tokens_to_answer.py` (schema term + A/B), questions file, tests, PLAN/CONVENTION/runbook/BACKLOG.
Out of scope: `find_implementations` gains no flag (not named in Scope L19); `impact`,
`include_graph`, `reachable_from`, `find_orphans` untouched; no contract-version bump; **no new tool
shipped unless the A/B says so**.

### Gate 1

**ASSUMED W1–W3 ratified** by the standing approval given this session. `TIER: full`, `SCOPE: M`
— no tier drift. **cleared.**

---

## Phase 2 — Design

### Approach

1. **New `code_atlas/tools/call_site.py`** — `annotate(root, store, hits, *, max_chars)`. Groups hits
   by `file`, hash-checks each file once via `indexer.file_is_current` (C4), reads it once, and adds
   `source` (the `line`-th line, stripped, truncated at `max_chars` with `…`) to each hit. A drifted,
   missing, or unreadable file yields **no** `source` and `source_stale: true` for those hits only.
   Precedent for a tool-layer helper that reaches the filesystem: `freshness.py` (035).
2. **`find_callers` / `find_references`** gain `include_source: bool = False`. When false, nothing is
   called and the payload is **byte-identical** to today (W1/C1). When true, annotate the already
   built hit list before shaping — no extra SQL, no change to `edge_hit` (F1: `file`+`line` are
   already there), so `nav_result.py` is untouched.
3. **Extend the 034 metric (W3), two independent terms:**
   - **Round-trip term** — add one compound question to
     `tokens_to_answer_questions.json` (`call_sites_of_repo_put`, "where exactly is
     `App\Repo::put()` called?") whose atlas recipe is a **single** `find_callers(include_source=true)`
     call. It enters the existing gate, so the compound response is measured by the same ratio CI
     already enforces.
   - **Surface term** — new `scripts/relation_surface_ab.py` measures surface **A** (three tools) vs
     **B** (one `find_relations(qname, relation)`): tool-schema tokens (name + docstring + parameter
     schema, paid once per session) **plus** per-call arg+response tokens over the three relation
     questions, with B dispatching to the real tools so its response bytes are real.
4. **Decide from those numbers, then act.** Ship `find_relations` into `code_atlas/` **only** if B
   wins net (C3/R1.2); otherwise keep three tools and record the verdict with its numbers.
5. **Tests:** proving test for the flag, a byte-equality test for the default, a degraded-case test
   (drifted site file ⇒ no `source`, `source_stale`), a cap test, and a pure-Python test that the A/B
   actually measures both surfaces (a comparison that cannot differ is not evidence — F2).

### Rejected alternatives

| Rejected | Why |
|----------|-----|
| Always include the snippet (capped) | Changes every existing `find_callers`/`find_references` payload; the ratio headroom is already thin (0.286 vs 0.24 floor), and "frugal by default" stops being assertable |
| `± context` lines around the call | ~5× the added tokens for the same answer ("show me the call") |
| Quote the line unconditionally | A drifted file makes the tool confidently wrong — violates C4/R4 and inverts §19's trust goal |
| Ship `find_relations` now, measure later | Ticket C L29-31 holds it behind the benchmark; R1.2 forbids inventing the seam on one data point |
| Run the A/B on the harness as-is | Returns 0 difference **by construction** (F2) — a false green dressed as evidence |
| `CA_SITE_MAX_CHARS` env knob | YAGNI (R7.1) until a second value is wanted — same call as 035's `cap = 1` |
| Add the flag to `find_implementations` too | Not named in Scope L19; recorded as a follow-up instead of silent scope growth |

### Assumptions

| Assumption | Tag |
|------------|-----|
| Adding one question shifts the aggregate ratio; runbook figure must be re-read after | novel-untested → measured in Phase 3, runbook updated |
| `estimate_tokens` over name+docstring+param-schema is a fair schema proxy for a **comparison** | verified-by-consistency — same ~4 chars/token proxy the harness already declares |
| `file_is_current` is the right freshness primitive for a non-subject file | verified — 035 ships it, `freshness.py` uses it for the subject file |

### Change-list

| # | Change | File | Covers | k/N |
|---|--------|------|--------|-----|
| 1 | `annotate` + cap + freshness gate | `code_atlas/tools/call_site.py` (new) | R1, C1, C4, W2 | 4/4 |
| 2 | `include_source` flag | `code_atlas/tools/find_callers.py` | G1, R1, W1, AC1 | 4/4 |
| 3 | `include_source` flag | `code_atlas/tools/find_references.py` | R1, W1 | 2/2 |
| 4 | Compound question (round-trip term) | `scripts/tokens_to_answer_questions.json` | G1, AC2, W3 | 3/3 |
| 5 | Surface A/B measurement | `scripts/relation_surface_ab.py` (new) | G2, R2, AC2, W3 | 4/4 |
| 6 | Proving + degraded + cap + byte-equality tests | `tests/test_compound_nav_responses.py` (new) | AC1, C1, C4, W2 | 4/4 |
| 7 | A/B gate test (both surfaces really measured) | `tests/test_relation_surface_ab.py` (new) | AC2, G2, W3 | 3/3 |
| 8 | Core-module count guards 29→30 | `tests/test_core_is_language_agnostic.py`, `tests/test_sql_confinement.py` | C2 companion | 1/1 |
| 9 | Verdict + numbers recorded | this working doc | G2, R2, AC2, C3 | 4/4 |
| 10 | PLAN §12/§19, runbook, BACKLOG + token row | `docs/` | AC3, R7.2 | 2/2 |

### Verification plan

| Row | Layer | Proof |
|-----|-------|-------|
| AC1 / R1 / W1 | integration | flag on ⇒ `source` present; flag off ⇒ payload `==` a pre-flag snapshot |
| C1 / W2 | unit+integration | long line truncated at the cap; default response unchanged |
| C4 | integration | edit the caller file on disk ⇒ `source` absent, `source_stale: true` |
| AC2 / G2 / R2 / W3 | measurement | A/B script emits both surfaces' totals; recorded here with the verdict |
| AC3 / C2 | suite | `pytest -q` green; grep-gates unchanged |

### Named proving test

`tests/test_compound_nav_responses.py::test_find_callers_include_source_quotes_the_call_line`
Fails today: `find_callers()` has no `include_source` parameter (`TypeError`).
Invoke: `.venv/bin/pytest tests/test_compound_nav_responses.py -q`

### Gate 2

**cleared** under standing approval — approach = opt-in capped freshness-checked snippet + a
two-term extension of the 034 metric, with the consolidation verdict following the numbers.

---

## Phase 3 — Execute

**Branch:** `feat/037-compound-nav-responses` (from main @ `a1fd7b5`)

**Implemented:** change-list #1–10. Suite tip: **702 passed** (baseline 684 + 18).

### Axis 1 — file set

`diff ⊆ approved list ✅` — no file outside change-list #1–10.

### Axis 2 — design-conformance

| Approach bullet | Status |
|-----------------|--------|
| 1 `call_site.annotate` (group by file, hash-gate, cap) | implemented-as-approved |
| 2 `include_source` on both tools, `nav_result` untouched | implemented-as-approved |
| 3 Two-term metric extension (compound question + surface A/B) | implemented-as-approved |
| 4 Decide from the numbers, then act | implemented-as-approved — verdict below |
| 5 Tests incl. degraded case + "the metric can distinguish" | implemented-as-approved (+D1) |

### Deviations

| ID | What | Why | Trace |
|----|------|-----|-------|
| D1 | The C4 test was **rewritten** after a mutation check | First version drifted the file to a *shorter* one, so it passed via the missing-line path and stayed green with `file_is_current` deleted — a vacuous guard (LESSONS 034). Now the drift keeps the file the same length with the line populated, so only the hash check can catch it | Verification plan / C4 |
| D2 | Fixture splits caller and callee into **two** files | Same-file fixtures trip 035's subject-file guard before annotation runs, so C4 was unreachable. Two files is also the realistic shape | C4 |

### Measured results

**G1 — does the compound response remove a round-trip?** Same question, same correct answer
(`tests/fixtures/php/resolve`):

| Path | Relation calls | Relation tokens | + `get_index_status` preamble (73) |
|------|----------------|-----------------|------------------------------------|
| `find_callers(include_source=true)` | **1** | **107** | **180** |
| `find_callers` → `read_symbol` | 2 | 176 | 249 |

**−39% on the relation calls, −28% end-to-end**, for the identical answer, one round-trip removed.
Both paths were checked for correctness, not just cost.

Reproduce (the pair excludes the shared `get_index_status` preamble, which both paths pay
identically; `180` is what `scripts/tokens_to_answer.py` reports for the whole question):

```python
import sys; sys.path.insert(0, "scripts")
import tokens_to_answer as h  # CA_PHP_CMD must point at the adapter
root = h.prepare_fixture_root(Path("tests/fixtures/php/resolve"), Path("artifacts/roundtrip-ab"))
tools = h.bind_tools(h.build_index(root, Path("artifacts/roundtrip-ab/graph.db"), h._php_cmd_from_env()))
h.run_atlas_path(tools, [{"tool": "find_callers", "args": {
    "qname": "\\App\\Repo::put", "detail_level": "minimal", "include_source": True}}])[0]   # 107
```

**Gate impact.** The compound question joins the 034 gate: **10 questions, 10/10 correct, ratio
0.288** (was 0.286 over 9) — `--min-ratio 0.24` still passes, and the question would **fail** without
`include_source` since its `expected` includes the literal call text `$repo->put();`.

**G2/R2 — the consolidation A/B** (`scripts/relation_surface_ab.py`, 4 relation questions):

| Surface | Schema tokens (once/session) | Call tokens (4 calls) |
|---------|------------------------------|-----------------------|
| **A** — `find_callers` + `find_references` + `find_implementations` | 464 | 643 |
| **B** — one `find_relations(qname, relation)` | 223 | 670 |

`schema_delta −241` (B's one description is cheaper than three) · `call_delta +27` over 4 calls =
**6.75 tokens per call** (B's extra `relation` argument) · **break-even ≈ 35.7 relation calls per
session.**

| Relation calls in a session | Net delta | Cheaper surface |
|---|---|---|
| 1 | −234 | B |
| 10 | −174 | B |
| 20 | −106 | B |
| **36** | **+2** | **A** |
| 50 | +97 | A |
| 100 | +434 | A |

> **Corrected in review (round 1, Important).** The first version of this table read break-even
> **≈8.9 calls** — wrong by ~4×. `verdict()` multiplied the *aggregate* `call_delta` (27 tokens over
> **4** questions) by a call count, so its units were 4-call batches, not calls. My own prose gave it
> away in one sentence — "~7 tokens per call" and "break-even 8.9" cannot both hold, since 241/7 ≈ 34.
> Fixed at the source (`measure()` now publishes `call_delta_per_call`), with
> `test_break_even_is_in_calls_not_in_measured_batches` as the regression guard: the previous test
> only checked `verdict()`'s algebra against itself and **could not** catch a unit error in its input.

### Decision — keep the three tools; ship only the compound response

**The token evidence is equivocal, not supportive** — that is the honest reading of the corrected
numbers, and it is a change from what this doc first claimed:

1. **The crossover is ~36 relation calls, not ~9.** Below it a merged tool is genuinely cheaper, and
   plenty of real sessions sit below 36 relation calls. The original argument — "an agent passes the
   crossover inside one task" — **does not survive the correction** and is withdrawn.
2. **The whole effect is small in both directions.** Across 1–100 relation calls the spread is −234 to
   +434 tokens: well under 0.5% of a working context either way. Tokens therefore do not justify
   restructuring the tool surface — which is the actual question C3 asks.
3. **B's schema saving comes partly from documenting less** — exactly the "muddier per-tool
   description" cost the ticket names (C L29-31). Three focused descriptions are what an agent picks a
   tool *from*; the metric cannot price that, and it sits on the opposite side of the ledger from the
   241 tokens.
4. **R1.2** — merging collides with one-module-per-tool, and one data point is not the two
   implementations that reveal an abstraction.

So the ticket's rule ("merge **only if** 034 shows a net win") is not met: there is no net win, only a
small trade whose sign depends on session shape. Default applies — **keep the three tools**.

**Honest limits of this measurement.** The schema term is a `~4 chars/token` proxy (the estimator 034
declares) over docstrings **I authored on both sides**; editing one docstring mid-task moved
`schema_delta` from −240 to −241. So treat the crossover as an order of magnitude (tens of calls), not
a precise 35.7. `find_relations` is **not shipped** — it exists only inside the A/B script, so no
surface has to be removed later, and re-running the script is the way to revisit this.

### Ph3/4 proven by

| Row | Evidence |
|-----|----------|
| G1, R1, AC1, W1, W2 | `tests/test_compound_nav_responses.py` (9 tests) + the 107-vs-176 measurement |
| C1 | `test_default_call_is_byte_identical_to_the_pre_flag_payload` |
| C4 | `test_drifted_site_file_is_never_quoted` — **mutation-checked** (red without `file_is_current`) |
| C2 | no `if language ==` under `code_atlas/`; `call_site.py` reads files, store keeps the SQL |
| G2, R2, AC2, W3, C3 | `artifacts/relation-surface-ab.json` + the tables above; `tests/test_relation_surface_ab.py` (6 tests) pins that the metric can distinguish the surfaces |
| AC3 | `702 passed`; ruff + mypy clean |

### Matrix (Ph3)

All 14 rows → ✅ (evidence above).

---

## Phase 4 — Review

**Reviewed at** `8418654` (files: `call_site.py`, `find_callers.py`, `find_references.py`,
`relation_surface_ab.py`, questions file, both new test files, module-count guards, PLAN / runbook /
BACKLOG / this doc). Bookkeeping commits after this marker are exempt from the stale-review guard.

### Challenger (ticket-blind, raw ticket lines 1–44 only)

**10 met · 0 not met · 0 can't-tell** on its own reconstruction of the requirements. It independently
re-ran the suite (702 passed), the grep-gates, and `relation_surface_ab.py`, reproducing
`schema_delta −241` / `break_even 8.93` — so the recorded A/B numbers are reproducible, not asserted.
It also confirmed `find_relations` is **not** registered in `main.py` and `contract.py` is untouched,
i.e. the "keep three tools" verdict is what actually shipped.

| # | Rebuilt requirement | Verdict |
|---|---------------------|---------|
| 1–2 | `find_callers` / `find_references` optionally return the call-site line | met |
| 3 | A/B run on the 034 harness; result + decision recorded | met |
| 4 | Token-frugal by default (opt-in **and** capped) | met |
| 5 | No language branches (R1.1) | met |
| 6 | SQL stays in `store.py` (R1.4) | met |
| 7 | Consolidation held behind the benchmark; three tools kept | met |
| 8–10 | AC1 / AC2 / AC3 | met |

**Finding accepted and fixed — a documentation figure that could not be reproduced.** The challenger
could not derive PLAN's "107 vs 176" from the shipped harness, which reports **180** for the whole
question. It was right that the claim was unreproducible: 107/176 counted only the relation calls,
while 180 includes the 73-token `get_index_status` preamble both paths pay (107 + 73 = 180 ✓). The
numbers were correct but the framing was not checkable. Fixed in the Measured-results table above
(both forms + a reproduction snippet) and in `docs/PLAN.md`.

**Finding accepted — cost-ledger cells.** It flagged the BACKLOG row's blanket
`unmeasured (blocking retrieval)`. Correct: that text was carried over from 033/035/036, but this run
took its dispatch results as **task-notifications, which do carry a `<usage>` block**, so real numbers
exist and the honest marker does not apply. Corrected in the ledger below and in BACKLOG.

### Reviewer (`mango:reviewer` · round 1, at `8418654`)

- **Verdict:** **CHANGES REQUESTED** — 2 Important, 0 Critical. Explicitly *not* a conditional LGTM,
  because finding 1's fix rewrites a headline number rather than patching a constant.
- **Verified clean:** scope (diff = exactly the 13 approved files), R1.1 / R1.2 / R1.4 / R4, R7.5
  comment length, `call_site.py` correctness, suite 702, ruff, mypy. It **re-ran the C4 mutation
  itself** and confirmed the test goes red without `file_is_current`.

| Sev | Finding | Path | Resolution |
|-----|---------|------|------------|
| Important | **Break-even wrong by ~4×.** `verdict()` multiplied the *aggregate* `call_delta` (27 tokens over **4** questions) by a call count, so "8.9" was in units of 4-call batches, not calls. True value **35.7 calls** | `scripts/relation_surface_ab.py:161-181` + 3 docs | Fixed: `measure()` now publishes `call_delta_per_call`; `verdict(calls=…)` uses it; numbers and the sweep recomputed; **Decision §1 withdrawn and rewritten** |
| Important | **`CONVENTION.md` §6 contradicted and never synced** — it says nav tools return no source bodies, and the working doc's AC3 row claimed CONVENTION was synced when `git diff` showed it untouched | `docs/CONVENTION.md:108-109`; AC3 row | Fixed: §6 now carries the `include_source` exception (opt-in, one capped line, never from a drifted file); AC3 row corrected to record the false Y |

**Why finding 1 is the serious one.** It is the exact trap the AC2 honesty note was written to guard
against — a number that "looks like evidence and is an artifact" — in a shape I had not anticipated: a
unit error rather than the zero-difference tautology of F2. My own sentence contained the
contradiction ("~7 tokens per call" beside "break-even 8.9"; 241/7 ≈ 34) and I did not notice it. The
guard test I *had* written could not catch it, because it checked `verdict()`'s algebra against itself
rather than the units of its input — `test_break_even_is_in_calls_not_in_measured_batches` now does.

**Consequence for the decision.** The corrected crossover (~36 calls) does **not** support the
original "an agent passes that inside one task" argument, which is withdrawn. The decision still lands
on "keep three tools", but now rests on there being **no net win at all** (a −234…+434 token spread),
plus C3's unpriced description cost and R1.2 — not on the crossover. See the rewritten Decision.

## Cost ledger

| Phase | Dispatch | Round | Tokens | Tool uses | Duration |
|-------|----------|-------|--------|-----------|----------|
| Phase 4 | `mango:challenger` | 1 | **61,961** | 32 | 336 s |
| Phase 4 | `mango:reviewer` | 1 | **106,501** | 42 | 595 s |

`LEDGER: 2 dispatch rows | all cells carry real measured values | complete`

**Ledger correction.** Phases 0–3 dispatched **nothing** — the premise check, both A/B measurements
and every fix ran on the main model. An earlier draft of the BACKLOG row said "3 dispatch … refine
exposure-checker" and marked every cell `unmeasured (blocking retrieval)`; both were copied from
033/035/036 rather than observed. No exposure-checker ran, and both dispatches returned real `<usage>`
blocks. **Main-loop spend remains unmeasured** (the host surfaces per-subagent usage, not main-loop).
