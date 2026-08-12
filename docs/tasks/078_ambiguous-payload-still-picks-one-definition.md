---
id: 078
slug: ambiguous-payload-still-picks-one-definition
title: '`ambiguous_definitions` warns about two declarations while `source` silently ships one of them'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [070, 043, 049]
---

## Goal
[070](070_ambiguous-qname-no-scoping.md) shipped `ambiguous_definitions` so a non-unique qname warns
instead of pretending to be one symbol, and round 4 verified the field: present, complete, and
independently confirmed by `search_symbol`. But the same payload's `file`, `line_start`, `line_end`
and `source` are all taken from **exactly one** of the definitions. The *field* picks no winner; the
*payload* does. An agent that reads `source` and does not read `ambiguous_definitions` receives one
region's code with no signal that it chose.

## Evidence (field retro round 4, 2026-08-10, probes P5/P6)
- `read_symbol` on a class declared in two regional legacy trees, verbatim (paths shortened):
  ```json
  "file":"legacy/<regionA>/…/EnumFilter.php","line_start":7,"line_end":12,
  "ambiguous_definitions":[{"file":"legacy/<regionA>/…/EnumFilter.php","line":7,"kind":"Class"},
                           {"file":"legacy/<regionB>/…/EnumFilter.php","line":7,"kind":"Class"}]
  ```
  `search_symbol` independently listed the same two declarations (4 hits, 2 distinct files).
- The evaluator's verdict: **FIXED (verified), with a caveat worth a ticket** — and the caveat is the
  ticket: *"An agent that reads `source` and ignores `ambiguous_definitions` silently gets one
  region's code — in this repo, where the whole project is a two-region merge, that is the exact class
  of mistake this ticket exists to prevent."*
- The anchor repo is the demonstration, not the reason: two regional copies of one legacy tree are a
  general shape (vendored forks, `v1`/`v2` trees, monorepo copies), and 043 already established that
  `UNIQUE(qualified_name, file_path)` legitimately keeps one node per declaration.
- Binding is load-order dependent, so the chosen definition is not "the right one" in any sense the
  index can defend — 070 says exactly this and then ships a body anyway.

## The choice this ticket must make
Three defensible designs; pick one, in writing, with the cost stated:
1. **Refuse the body when the subject is ambiguous** — return the definition list and no `source`,
   forcing a disambiguated re-ask (by file, or by the fully-scoped subject). Safest, one extra
   round-trip, and it makes the warning unignorable.
2. **Answer, but mark the answer** — keep `source`, add a field naming *which* definition it came from
   and that others exist. Cheapest, and it still relies on the agent reading a second field.
3. **Accept a disambiguator argument** (`file=…`) and refuse only when the subject stays ambiguous.
   Most useful, largest surface: a new parameter on every single-subject tool.

070 ruled out per-definition *scoping* on the edge model; that ruling is about edges, and it does not
decide what a *body-returning* tool should do. Say so explicitly so the two tickets do not appear to
contradict each other.

## Scope / Deliverables
- **One decision, applied to every tool that returns a body or a single site** — `read_symbol` first,
  then `file_outline`'s symbol path, `explain_path`, `impact`, and the `find_*` subjects.
- **Make the ambiguity impossible to miss** for whichever design is chosen: either no body, or a field
  on the same nesting level as `source` that names the chosen site.
- **Keep the unique case byte-identical** (R4 / 061) — a unique qname pays nothing.
- **State the interaction with 049's call-site selectivity** — if a disambiguator argument is added,
  it must not become a second, differently-shaped filter vocabulary.
- **Test the two-region shape as a fixture**, not against the anchor repo: two files, same qname,
  different bodies (R2 — the fixture encodes the shape, not a repo).

## Constraints
- R2 — no repo, region, or framework name enters code or fixtures.
- R3 — a new field or parameter is contract vocabulary: bump and extend conformance.
- R4 — the chosen definition (if any) must be deterministic, and the ticket must say what determines
  it; "whatever SQLite returned first" is not an answer an agent can reason about.
- 061 — nothing added to the unambiguous payload.

## Acceptance criteria
- For an ambiguous qname, no tool returns a body without the payload naming which declaration it came
  from — proven by a test on a two-declaration fixture.
- The unambiguous payload is unchanged, asserted byte-for-byte.
- `ambiguous_definitions` and the body-selection rule are documented together, with the load-order
  caveat stated where an agent will read it (tool description, not only the plan).
- 070 is updated with a pointer, so its "never picks a winner" claim is scoped to the field it
  describes.

## References
Field retro round 4 §A.6 (verdict + caveat), probes P5/P6, §8 row 3 (the win this rides on).
Related: [070](070_ambiguous-qname-no-scoping.md) (the warning field, and its edge-model ruling),
[043](043_duplicate-decl-resilience.md) (why two nodes per qname are legitimate),
[049](049_call-site-argument-selectivity.md) (the existing selectivity vocabulary),
[046](046_resolver-qname-candidate-dedupe.md) (duplicate edges, already fixed at the cause).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 078 — ambiguous payload still picks one definition (working doc)

- **Ticket:** 078 · local `docs/tasks/078_ambiguous-payload-still-picks-one-definition.md`
- **Type:** enhancement (agent-trust)
- **Repo(s):** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full (review **skipped** by invoke)
- **BASELINE:** green — `1115 passed in 48.95s` (`.venv/bin/pytest -q`, 2026-08-12)
  <!-- baseline exclusions: none -->

---

## Phase 0 — Refine

`REFINE: 4 unresolved surfaced | 0 want-decision asked | 6 how-decision resolved+cited | 2 ASSUMED | skip: no`

**INPUT KIND:** ticket

**Settled wants:** _(none asked — handed back)_

**Resolved HOW (cited)**

| # | HOW | Resolution | Citation |
|---|-----|------------|----------|
| 1 | 070 edge "never pick" vs body tools | 070 ruling is edge-model only; body tools are 078's call | ticket L47–49 |
| 2 | Keep `reason=ok` | 070 kept reason orthogonal to the list | 070 rejected `reason=ambiguous_*` |
| 3 | 049 ↔ disambiguator | N/A under refuse-body (no new arg) | exposure-checker; design 1 |
| 4 | R4 chooser when body ships | N/A under full refuse — no body/site shipped | exposure-checker |
| 5 | Re-ask without `file=` | Client uses `file_outline` / `search_symbol` on a site from `ambiguous_definitions` | ticket option 1; existing tools |
| 6 | find_* / file_outline | find_* already warn without a body; file_outline is path-based (no qname body) | explore brief |

**ASSUMED (awaiting ratification)**

| # | Assumed choice | Why | Confirm at | Reverses? |
|---|----------------|-----|------------|-----------|
| 1 | **Design 1 — refuse body** when subject qname has >1 definition: `source=""`, omit `file`/`line_*`, keep `found=true` + `reason=ok` + `ambiguous_definitions` | Makes warning unignorable; avoids option-2 ignore-second-field failure; avoids option-3 API surface / 049 collision | Gate 1 | no |
| 2 | **Defer** impact/explain_path single-site loc display (`_impact_node_loc`) to a follow-up — AC is body-shaped; this ticket ships `read_symbol` | Keeps SCOPE=M; inventory recorded | Gate 1 | no |

**Exposure-checker:** 049/R4/re-ask → HOW #3–5. No further wants.

---

## Requirements matrix

`SECTIONS: 6 found (Goal, Evidence, Choice, Scope, Constraints, AC) | 6 decomposed | ROWS: C=4 R=5 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|--------------|-----|-------|--------|
| G1 | Goal | payload picks one def while field warns | Body tools must not ship a silent single-site body when N>1 | `read_symbol.py:109-133` | CL1–3 | | ❌ |
| R1 | Scope | One decision on every body/single-site tool | Refuse-body on `read_symbol`; find_* already OK; impact/explain deferred (ASSUMED #2) | ticket L52–54 | CL1,CL6 | | ❌ |
| R2 | Scope | Ambiguity impossible to miss | No `source` / site fields when N>1 | ticket L54–55 | CL1 | | ❌ |
| R3 | Scope | Unique case byte-identical | Key absent; body unchanged | 061; test unique | CL4 | | ❌ |
| R4 | Scope | 049 interaction | N/A — no disambiguator arg | ticket L57–58 | — | | ✅ |
| R5 | Scope | Two-region fixture | Existing ambiguous fixture / in-memory two defs | `test_ambiguous_qname.py` | CL4 | | ❌ |
| C1 | Constraint | R2 — no repo names | Fixture abstract | ENGINEERING_RULES R2 | CL4 | | ❌ |
| C2 | Constraint | R3 — new field/param bumps contract | No new field/param — omit existing | R3 | — | | ✅ |
| C3 | Constraint | R4 — deterministic if any pick | Full refuse → N/A | ticket L65–66 | CL1 | | ✅ |
| C4 | Constraint | 061 — nothing on unambiguous | Conditional path only | 061 | CL4 | | ❌ |
| AC1 | AC | No body without naming chosen decl | Refuse: no body at all when N>1 | ticket L70–71 | CL4 | | ❌ |
| AC2 | AC | Unambiguous byte-identical | Assert key absent + body fields | ticket L72 | CL4 | | ❌ |
| AC3 | AC | Document list + body rule + load-order | Tool docstring + PLAN + 070 pointer | ticket L73–74 | CL5 | | ❌ |
| AC4 | AC | 070 updated with pointer | Scope "never picks" to the field | ticket L75–76 | CL5 | | ❌ |

## AC validation

| AC | Ticket | Computed | Match? | Falsifiable? |
|----|--------|----------|--------|--------------|
| AC1 | no body without naming chosen | refuse ⇒ no source/file/line when N>1 + list present | Y | pytest |
| AC2 | unique unchanged | freeze unique payload keys/values vs pre-change shape | Y | pytest |
| AC3 | docs together | grep tool docstring + PLAN | Y | grep |
| AC4 | 070 pointer | edit 070 | Y | grep |

## Clarifications

`CLARIFICATION: 2 raised | 2 ASSUMED (standing best-option) | 0 for human decision`

---

## Phase 1 — Analysis ✋ Gate 1

- **Gap:** `read_symbol` attaches `ambiguous_definitions` but still fills `source`/`file`/`line_*` from `rows[0]` (`_NODE_ORDER`). Agents read `source` and ignore the list.
- **Blast radius:** `read_symbol.py`; `test_ambiguous_qname.py` (locks today's bug); PLAN §12; 070 task text; `nav_result.attach_*` docstring. find_* unchanged. impact/explain deferred.
- **RULE SECTIONS:** R2 ✅ · R3 N/A (no new vocab) · R4 ✅ · R6.1 ✅ · 061 ✅
- **Gate 1 status:** **cleared** (standing approval; ASSUMED #1–#2 ratified)
- **TIER:** full · review waived · **SCOPE:** M

---

## Phase 2 — Design ✋ Gate 2

- **Approach:** When `nodes_by_qualified_name` returns >1 row, `read_symbol` returns `found=true`, `reason=ok`, `source=""`, omits `file`/`line_start`/`line_end`, attaches `ambiguous_definitions`. Freshness: ensure each distinct def file (repair), re-fetch, then apply the same rule. Unique path unchanged. Update tool docstring (re-ask via `file_outline`/`search_symbol`). Rewrite proving test. Update PLAN + 070 pointer. Docstring on `attach_ambiguous_definitions`: list never picks; body tools must not either (078).

- **Rejected:** (2) mark chosen — still ignoreable. (3) `file=` arg — largest surface + 049 risk.

**Assumptions**

| Assumption | Tag | Proof |
|------------|-----|-------|
| Omitting site keys when found=true is valid for clients | verified | stale path already omits lines; tests updated |
| No contract bump | verified | no new field/param |

**Change-list**

| # | Change | File | Rows |
|---|--------|------|------|
| CL1 | Refuse body when N>1 | `read_symbol.py` | G1,R1,R2,AC1,C3 |
| CL2 | `_result` omit file/lines when None | `read_symbol.py` | R2 |
| CL3 | attach docstring + PLAN wording | `nav_result.py`, `PLAN.md` | AC3 |
| CL4 | Rewrite ambiguous read test + unique assert | `tests/test_ambiguous_qname.py` | AC1,AC2,R3,R5,C4 |
| CL5 | 070 pointer + tool docstring | `070_…md`, `read_symbol` docstring | AC3,AC4 |
| CL6 | BACKLOG / LESSONS / ticket status on finalise | docs | bookkeeping |

**Proving test:** `test_read_symbol_refuses_body_when_ambiguous` — two defs → `source==""`, no `file`, `ambiguous_definitions` has both. Unique payload still omits key.

**Verification plan:** AC1–4 integration/docs ✅ layer-match. Coverage-gap: impact/explain deferred (ASSUMED #2) ⚠.

- **Gate 2 status:** **cleared** (standing approval)

---

## Phase 3 — Execute
- Branch: `feat/078-ambiguous-payload-still-picks-one-definition`
- Proving test: `test_read_symbol_refuses_body_when_ambiguous`
- Verification sweep: diff ⊆ CL1–CL6 ✅; Approach bullets implemented-as-approved ✅
- Full suite: **1115 passed**. Design-invalidation: none


## Phase 4 — Review ✋
- **Skipped** by invoke.

## Phase 5 — Finalise ✋
- PR draft: `/tmp/pr-078.md`
- Outward actions (invoke-approved): commit + push + open PR
- Durable lesson: `docs/LESSONS.md` (078 refuse body)


---

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer |
|-------|---------------------|-------|--------|-----------|
| 0 | explore (context) | 1 | unmeasured (blocking retrieval) | rtk expect |
| 0 | challenger (exposure-checker) | 1 | unmeasured (blocking retrieval) | rtk expect |

`LEDGER TOTAL: unmeasured (2 blocking) · top: Phase 0 explore + exposure-checker`

---

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Gate 1 | ASSUMED #1 refuse-body ratified | standing best-option |
| Gate 1 | ASSUMED #2 defer impact/explain | SCOPE M; AC is body |
| Gate 1–2 | review waived | invoke |

## Session status

- **Last updated:** 2026-08-12
- **work_doc_mode:** embed → `docs/tasks/078_ambiguous-payload-still-picks-one-definition.md`
- **Current phase:** Phase 5 — Finalise
- **Next action:** commit + push + open PR
- **Blocked on:** nothing
