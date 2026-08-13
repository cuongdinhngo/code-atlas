---
id: 081
slug: routing-prompts-are-not-in-the-agents-surface
title: 'The four routing prompts have never been reachable by an agent — 069 fixed discoverability in a channel the agent cannot see'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [069, 017, 038]
---

## Goal
The server registers four prompts — `explore_area`, `find_usages`, `impact_of_change`, and
`which_tool` (069's answer to a capability nobody could find). Round 4's evaluator reported it could
not call `which_tool` and, crucially, **could not have**: in its client only the 14 tools are part of
the surface a model sees, while MCP prompts surface as human-invoked entries. Across four field rounds
no prompt has been exercised once. A routing hint the agent cannot reach cannot fix an agent's routing
problem, and a delivery channel with zero field evidence should not be counted as shipped capability.

## Evidence (field retro round 4, 2026-08-10, §0.5 and §A.5)
- Verbatim: *"The 4 prompts are not reachable from this client's tool surface; only the 14 tools are
  exposed to me. A prompt that the agent cannot invoke cannot fix a discoverability problem for that
  agent."*
- §A.5's verdict on 069 is **IMPROVED, not fixed**: the descriptions half is verified — first lines
  read *"Who calls this function or method?"*, *"Where is this symbol used across the codebase?"*,
  *"What does this file define, and on what lines?"*, *"What variables does this handler make available
  to its template?"*, *"Find a symbol from part of its name or text"* — while the `which_tool` half is
  **not exercisable** and the `capability_not_configured` half did not apply (this index has rules
  configured).
- Rounds 1–3 called 0 prompts as well; none of the three retros noticed, because none of them was
  asked. This ticket exists partly because round 4's questionnaire asked.
- Countervailing fact worth keeping: descriptions **did** work. The same session recorded
  `find_view_data` as *"not a discoverability failure this time: its description states the question it
  answers"* — it went uncalled because no view-data question arose, which is occasion, not recognition.

## The real question
Not "make prompts reachable" — that is a client's decision, not ours. The question is **where routing
guidance belongs when the only surface an agent reliably sees is the tool list**. Three candidate
answers, and the ticket must choose with the field evidence in hand:
1. **Descriptions carry it all** (069's verified half). Cheapest, already proven to work, bounded by
   how much text a description can hold before it dilutes.
2. **A tool that answers "which tool"** — routing as a callable, discoverable like everything else,
   at the cost of one more entry in a 14-tool surface and a description that must itself be
   self-explaining.
3. **Keep the prompts for humans and stop counting them as agent-facing** — document them as operator
   recipes, and move any agent-critical routing into (1).

## Scope / Deliverables
- **Establish the fact from outside**, not from our own assumptions: record which surfaces the target
  clients expose to a model (tools always; prompts as human entries in at least one client), and cite
  the observation rather than the docs.
- **Choose one of the three designs and apply it**, including deleting or relabelling what the chosen
  design makes dead. A registered prompt nobody can reach is payload weight in the same sense 061
  measured.
- **Re-verify 069's remaining halves** with a live probe: the `capability_not_configured` branch on an
  index with no `view_data` rule, and whatever replaces `which_tool`.
- **Give the next retro a real recognition test.** Round 4's §0.5 was voided by protocol order; the
  measurement it was meant to produce is still missing, and whatever ships here needs it as its
  acceptance evidence rather than a self-report.
- **State the cost of a 15th tool** if design 2 wins — 069's own reasoning was that a surface an agent
  scans has a budget.

## Constraints
- R1.2 / YAGNI — do not build a routing framework; the smallest thing that puts the guidance where the
  agent looks.
- 061 — if the prompts stay, they must earn their registration; if they go, say what replaces them.
- 069 stays authoritative for description *content*; this ticket is about the *channel*.
- No LLM in the core (R4) — routing guidance is static text or a deterministic tool, never a model
  call.

## Acceptance criteria
- A recorded, cited statement of which surfaces reach a model in the clients we target.
- One design chosen, implemented, and the alternatives rejected in writing.
- No registered capability remains that an agent cannot invoke, unless it is explicitly labelled
  operator-facing in the README and the plan.
- A recognition measurement exists that a future field round can run without contaminating itself.

## References
Field retro round 4 §0.5 (could not call it), §A.5 (`IMPROVED, not fixed`), §2 (`find_view_data`
description worked), §11 item 2 (probe-shaped evidence caveat). Related:
[069](069_tool-names-do-not-say-what-they-answer.md) (question-first descriptions + `which_tool`),
[017](017_impact-engine.md) (where the prompts were introduced),
[038](038_explain-path.md) (the tool round 4 expected to want and never called),
[061](061_payload-weight.md) (capability that earns nothing).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 081

## Session status
- **work_doc_mode**: embed (below separator; plain tracked ticket, not a scaffold stub)
- **Phase**: 5 finalise; Gates 0/1/2 cleared (4 ASSUMED confirmed); **review WAIVED** (run arg)
- **Branch (planned)**: `feat/081-routing-prompts-are-not-in-the-agents-surface`

## Phase 0 — Refine

### Premise check
`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
Resolved: the four prompts `explore_area`/`find_usages`/`impact_of_change`/`which_tool` (`code_atlas/tools/prompts.py:7-12,53`), registration (`code_atlas/main.py:90` → `prompts.register`), README §Prompts (`README.md:167-173`, lists 3 — `which_tool` absent), PLAN prompt mentions (`docs/PLAN.md:411,463`), tasks 069/017/038 (exist). No referenced-as-existing source missing → premise holds.

### Advisory recall
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
LESSONS.md is prose-format; surfaced by area: **069** (question-first descriptions — the "descriptions work" evidence this ticket leans on), **061** (capability that earns nothing — payload weight). No `skill_gap_path` configured. Advisory only.

### The central decision (WANT, handed back → ASSUMED)
The ticket's own "real question" is a WANT-level design choice among three directions. The user delegated it ("suggest and do the best option, pass all gates"), so per refine Step 4 it is recorded **ASSUMED (awaiting ratification)** and re-surfaces at Gate 1 for an explicit confirm.

**ASSUMED — Design 3: keep the prompts as labelled operator recipes; rely on tool descriptions (069) for agent routing; add no 15th tool.**
Reasoning against the field evidence + constraints:
- **Design 2 (a 15th `which_tool` tool)** contradicts 069's own "a scanned surface has a budget" and R1.2/YAGNI ("smallest thing, do not build a routing framework"). A 15th entry taxes every agent's scan to serve routing that descriptions already carry. Rejected.
- **Design 1 (descriptions carry it all, delete the prompts)** — the mechanism is already shipped (069, verified: `find_view_data` was recognised by its description). But *deleting* the prompts removes a cheap human affordance that prompt-surfacing clients do expose to operators; deletion is heavier than the defect requires.
- **Design 3 (chosen)** fixes the actual defect — a **category error**: prompts were counted as agent-facing capability when the agent's client never surfaces them to the model. It relabels them operator-facing (README + PLAN), keeps the cheap human recipes, and leans on descriptions (proven) for agent routing. Smallest thing that puts guidance where the agent looks; satisfies 061 (the explicit operator-facing label is how they earn registration) and AC3 (labelled operator-facing in README and plan).

### Decision classification (HOW — resolved + cited)
| # | Decision | Class | Resolution + citation |
|---|----------|-------|-----------------------|
| 1 | Surface fact (tools model-visible; prompts human-invoked) | HOW | Round 4 §0.5/§A.5 verbatim (ticket lines 20-22); cite the observation |
| 2 | Relabel operator-facing, don't delete | HOW | Design 3 (ASSUMED) + 061 (label = earns registration); ticket AC3 |
| 3 | which_tool stays an operator prompt (no replacement tool) | HOW | Design 3; R1.2/YAGNI (ticket C1) |
| 4 | Re-verify capability_not_configured via a test probe | HOW | Ticket deliverable 3; existing branch `test_tool_descriptions.py:63` / `test_freshness_cannot_find_what_is_not_indexed.py` |
| 5 | Recognition measurement = a documented blind-probe protocol | HOW | Ticket AC4; no such harness exists yet → create a runbook |
| 6 | which_tool map must cover all 14 tools (currently 14 listed) | HOW | Ticket (map is "for all 14 tools"); pin with a test |

### Open items for analysis (not refine wants)
- Whether the capability_not_configured re-verify already has a passing test or needs one (analysis checks `test_tool_descriptions.py:63`).
- Exact home for the recognition-probe protocol (a new `docs/runbooks/` file vs the retro harness) — analysis/design decides.

### Exposure-checker verdict (1 dispatch, ticket-blind)
**Not fully exposed** — surfaced **3 acceptance-bar WANTs** beyond the design choice. All delegated → recorded **ASSUMED (awaiting Gate-1 confirm)** with recommended resolutions (per tie-breaker (a), acceptance-bar decisions are WANTs, never silently resolved as HOW):

- **ASSUMED-A — target-client roster (AC1).** No roster exists in the repo (PLAN says "Claude Code / any MCP client"). **Resolution:** scope the cited surface fact to what is actually observable — the round-4 evaluator's client (the one with field evidence) **plus the MCP protocol fact** (tools are model-visible; prompts surface as human-invoked entries). Do **not** commit to separately probing Cursor/Desktop (no field access). Cite the observation, not the docs.
- **ASSUMED-B — recognition-measurement bar (AC4).** Underspecified in the ticket. **Resolution:** model it on 069's concrete instrument (`069:297-310` blind-reader pick-rate). Ship a documented **blind-probe protocol** (a runbook): a fixed set of natural-language questions, the agent picks a tool **without first seeing the recognition map** (no contamination), pick vs expected recorded, a stated recognition-rate bar. It is a re-runnable protocol artifact, not a self-report.
- **ASSUMED-C — AC3 audit boundary.** AC3 is phrased server-wide; the Goal is scoped to the 4 prompts. **Resolution (smallest honest reading, R1.2):** reconcile the **four prompts** (relabel operator-facing, incl. fixing README's missing `which_tool`), **plus a one-line recorded audit** confirming the only other registered capabilities are the 14 tools and all are agent-invocable — so AC3's "no registered capability an agent cannot invoke, unless labelled operator-facing" holds server-wide without a heavyweight sweep.

Plus **ASSUMED-D — Design 3** (the three-way choice, above).

### REFINE count
`REFINE: 9 unresolved surfaced | 0 want-decision asked | 6 how-decision resolved+cited | 4 ASSUMED | skip: no`
4 ASSUMED (Design 3 + A/B/C) surface at Gate 1 for one explicit confirm under standing approval. Hand to analysis.

### Cost ledger
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| refine | exposure-checker (challenger, ticket-blind) | 1 | 60,447 (17 tool-uses, 194 s) |

## Phase 1 — Analysis

### Premise / recall (carried from refine)
`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)` — 069, 061 (area).

### Decomposition count
`SECTIONS: 7 found (Goal, Evidence, The real question, Scope/Deliverables, Constraints, Acceptance criteria, References) | 7 decomposed | ROWS: C=4 R=5 G=1 AC=4`

### Chosen design (ASSUMED-D, for Gate-1 confirm)
**Design 3** — keep the four prompts as **labelled operator recipes**; agent routing already lives in tool descriptions (069, proven); **no 15th tool**. Rejected: Design 2 (15th tool contradicts 069's surface-budget + R1.2/YAGNI); Design 1's deletion (removes a cheap human affordance for no gain). Fixes the real defect: a **category error** — prompts were counted as agent-facing when the agent's client never surfaces them to the model.

### Requirements matrix
| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|----|--------|------------------|----------------|--------------|--------|
| G1 | Goal | a routing hint the agent can't reach can't fix routing; don't count unreachable channel as shipped | Put routing where the agent looks (descriptions); stop miscounting prompts | prompts registered `main.py:90`; model surface = 14 tools only | open |
| R1 | Scope | establish the surface fact from outside, cited | Record: tools model-visible; prompts human-invoked (round-4 obs + MCP protocol fact) | round 4 §0.5/§A.5 (ticket 20-22) | open |
| R2 | Scope | choose one design + apply; delete/relabel what it makes dead | Design 3: relabel prompts operator-facing (README+PLAN); keep them | README §Prompts unlabelled + missing `which_tool` (`README.md:167-173`) | open |
| R3 | Scope | re-verify 069's remaining halves via live probe | Focused test: `capability_not_configured` on no-rules index; `which_tool` map coherent | loose coverage only (`test_freshness…:131`); no focused test | open |
| R4 | Scope | give the next retro a real recognition test (not self-report) | New blind-probe runbook (model on 069's instrument) | no recognition harness exists in repo | open |
| R5 | Scope | state the cost of a 15th tool if design 2 wins | Record rejection reasoning citing 069's budget | Design 2 rejected | open |
| C1 | Constraint R1.2/YAGNI | smallest thing; no routing framework | Docs + label + 2 small tests; no new tool | — | open |
| C2 | Constraint 061 | prompts earn registration or say what replaces them | Explicit operator-facing label = earns it | — | open |
| C3 | Constraint | 069 authoritative for description content; this is about channel | Don't rewrite description text | 069 | open |
| C4 | Constraint R4 | no LLM in core; routing is static text/deterministic | Prompts already static; no model call added | `prompts.py` static | open |
| AC1 | AC | recorded, cited statement of which surfaces reach a model | Falsifiable: the statement exists + cites the observation | — | open |
| AC2 | AC | one design chosen, implemented, alternatives rejected in writing | Falsifiable: working doc records choice + rejections; code/docs reflect it | — | open |
| AC3 | AC | no registered capability an agent can't invoke, unless labelled operator-facing in README + plan | Falsifiable: grep README + PLAN for the operator-facing label on all 4 prompts; audit tools all invocable | — | open |
| AC4 | AC | a recognition measurement a future round can run without contaminating itself | Falsifiable: the protocol doc exists + specifies blind order + a pass bar | — | open |

### AC validation (falsifiability) + the 3 acceptance-bar ASSUMED items
- **AC1** falsifiable once the target-client scope is pinned → **ASSUMED-A**: cite the round-4 client observation + the MCP protocol fact (tools model-visible, prompts human-invoked); do not commit to probing Cursor/Desktop (no field access).
- **AC2** falsifiable (choice + rejections recorded here; docs/tests reflect Design 3). ✔
- **AC3** falsifiable (grep for the operator-facing label in README + PLAN on all 4 prompts) → **ASSUMED-C**: reconcile the 4 prompts + a one-line audit that the only other registered capabilities are the 14 tools, all invocable.
- **AC4** "recognition measurement … without contaminating itself" is vague → **ASSUMED-B**: pin it to 069's shape (`069:297-310`) — a blind-probe protocol with a fixed question set, tool picked **before** seeing the map, recorded pick vs expected, a stated recognition-rate bar. This is the AC-value the ticket left unmeasurable; recorded here as the proposed definition.

**Uncodified-standard nudge:** the recognition-rate **pass bar** (a number, e.g. "≥ X/Y questions map to the intended tool") has no codified rule. Surfaced as an uncodified standard → recorded as ASSUMED-B's proposed bar for Gate-1 ratification; it will **not** silently gate-block. Proposed: the protocol ships as a *re-runnable instrument* with the bar stated in it; mango does not enforce a specific number this ticket.

### CLARIFICATION
`CLARIFICATION: 4 raised | 0 self-resolved | 4 for human decision (all ASSUMED, delegated)`
Gate 0 folds into Gate 1 under the standing approval: **Design 3** (D) + **A** (client scope) + **B** (recognition bar) + **C** (AC3 boundary). All four surface at Gate 1 for one explicit confirm.

### Universal inventory (AC3 "no registered capability … / each affected doc")
- Registered capabilities to reconcile: **4 prompts** — 1. `explore_area`, 2. `find_usages`, 3. `impact_of_change`, 4. `which_tool`. Per-item: each must be labelled operator-facing in BOTH README and PLAN (review confirms all 4 × 2 surfaces).
- Other registered capabilities audited: **14 tools** (`TOOL_NAMES`, `main.py:36-51`) — all agent-invocable (no operator-only tool). One-line audit satisfies AC3 server-wide.
- `which_tool` map completeness: covers all **14** tools (verified — map lists all of `TOOL_NAMES`).

### Cause / gap analysis (enhancement)
Gap: `prompts.py` registers 4 prompts as capabilities; the agent's client surfaces only the 14 tools to the model, so the prompts are structurally unreachable by the agent — yet README (`167-173`) documents them as plain "Prompts" (agent-facing framing) and omits `which_tool`. Target: relabel operator-facing in README + PLAN, add `which_tool` to the README table, note the channel reality in `prompts.py` docstring; add the re-verify test + recognition-probe runbook. `path:line` `code_atlas/tools/prompts.py:1,15`, `README.md:167-173`, `docs/PLAN.md:411`.

### Blast radius
- Entry: `prompts.register` (`main.py:90`); the prompts themselves (`prompts.py`).
- Touched: `docs/PLAN.md` (§14 prompts), `README.md` (§Prompts), `code_atlas/tools/prompts.py` (module docstring label), a new `docs/runbooks/tool-recognition-probe.md`, `docs/tasks/069*` (pointer/cross-ref optional), tests (focused `capability_not_configured` re-verify + `which_tool`-map-covers-all-tools). No behaviour change to the prompts (they stay registered). Repo `app` only. No core language branch.

### RULE SECTIONS (by change type)
`RULE SECTIONS: R1.2, R4, §061, §069(content-authority) — R1.2 ✅ (docs + label + 2 tests, no framework, no 15th tool), R4 ✅ (no LLM; prompts stay static text), §061 ✅ (operator-facing label = earns registration), §069 ✅ (description *content* untouched; channel only). No DB-conventions (no migration). No UI/a11y (backend/docs).`

### BASELINE
`BASELINE: green` — Docker scoped run (tool_descriptions/prompt/view_data/freshness/mcp_server): **101 passed, 0 failed**, 1033 deselected. Untouched checkout. DoD: delta-green.

### TRACK / SCOPE / TIER
`TRACK: backend — 0/N touched files under UI paths` (docs + a docstring + 2 tests)
`SCOPE: M` (README + PLAN + prompts.py docstring + new runbook + 2 tests + the recorded design decision)
`TIER: full` (design choice + AC3 universal "no registered capability … unless labelled" N=4 + multi-deliverable + the recognition-measurement AC)

## Phase 2 — Design

### Gate 1 clearance
Matrix + AC filled; 4 ASSUMED confirmed on standing approval → **D** (Design 3), **A** (client scope = round-4 obs + MCP fact), **B** (recognition = blind-probe runbook modelled on 069), **C** (AC3 = 4 prompts + tools-invocable audit).

### Approach
A **documentation-and-instrument** change — no behaviour change to the prompts, no new tool (Design 3, R1.2). Fix the category error and give the next round a real measurement:
1. **`code_atlas/tools/prompts.py`** — module docstring relabels the four prompts as **operator-facing, human-invoked recipes** and records the channel fact (an agent's client surfaces the 14 tools to the model; MCP prompts surface as human entries). No code/behaviour change; `PROMPT_NAMES` and the four functions are untouched.
2. **`README.md`** — retitle §Prompts to "Operator prompts (human-invoked — not part of the agent tool surface)", **add the missing `which_tool` row**, and a one-line note that agent routing lives in the tool descriptions (069). Fixes the README defect (all 4 now present + labelled).
3. **`docs/PLAN.md`** — at the prompts mention (§14, ~L411): relabel operator-facing, record the **cited surface fact** (AC1), the **design decision + rejected alternatives in writing** (AC2), and the **cost of a 15th tool** (R5 — a scanned surface has a budget; 069).
4. **New `docs/runbooks/tool-recognition-probe.md`** — the recognition instrument (AC4/ASSUMED-B): a fixed question set (one intent per tool), **blind order** (the agent answers before seeing `which_tool`/any map — the non-contamination rule), pick-vs-intended scoring, and a stated recognition-rate bar. Modelled on 069's blind-reader pick-rate (`069:297-310`).
5. **New `tests/test_routing_surface.py`** — three pins:
   - `test_readme_documents_all_prompts_as_operator_facing` (**proving test**): every `PROMPT_NAMES` entry appears in README and the section is labelled operator-facing; **fails pre** (`which_tool` absent, no label), passes post.
   - `test_which_tool_map_covers_every_tool`: the `which_tool` map lists every `TOOL_NAMES` entry (currency guard; the "which_tool coherent" re-verify, R3).
   - `test_find_view_data_reports_capability_not_configured_without_rules`: 069's second half re-verified live — a built index with no `CA_INDIRECTION_RULES` returns `reason=capability_not_configured` on a found symbol (R3).

### Rejected alternatives
- **Design 2 — a 15th `which_tool` tool** — contradicts 069's surface-budget and R1.2/YAGNI; taxes every agent scan to serve routing descriptions already carry. Rejected (cost recorded in PLAN per R5).
- **Design 1 — delete the prompts** — the routing mechanism is already shipped in descriptions (069), but deleting removes a cheap human affordance prompt-surfacing clients do expose; heavier than the defect needs. Rejected.
- **Assert the recognition bar as a mango gate** — the pass-rate is an uncodified standard (ASSUMED-B); ship it *inside* the instrument, not as a gate mango enforces this ticket. Rejected (would author a rule).

### Assumptions
- The agent's client surfaces only tools (not prompts) to the model — **verified** by the round-4 field observation (ticket §0.5/§A.5) + the MCP protocol (prompts are human-invoked); this ticket cites the observation, not the docs.
- `which_tool`'s map already lists all 14 `TOOL_NAMES` — **verified** (`prompts.py:58-71` vs `main.py:36-51`).
- `capability_not_configured` is returned by `find_view_data` with no rules configured — **verified** (`find_view_data.py:97`); the new test pins it live.
- No behaviour change means no existing test breaks — **verified** (docstring + docs only; `PROMPT_NAMES`/functions untouched).
No `novel-untested` third-party/runtime assumption.

### Smallest change-list
| Change | File/area | Blast radius | Ph2 covered by | k/N |
|--------|-----------|--------------|----------------|-----|
| Docstring relabel operator-facing + channel fact | `code_atlas/tools/prompts.py:1` | none — no behaviour change; `PROMPT_NAMES`/functions untouched | R2,G1,C2 | 1-4/4 prompts |
| README §Prompts relabel + add `which_tool` + routing note | `README.md:167-173` | consumed by the new proving test | R2,AC3 | 1-4/4 |
| PLAN prompts relabel + surface fact + decision/rejections + 15th-tool cost | `docs/PLAN.md:~411` | none identified | R1,R5,AC1,AC2,AC3 | — |
| New recognition-probe runbook | `docs/runbooks/tool-recognition-probe.md` (new) | none | R4,AC4 | — |
| Proving test: README documents all prompts operator-facing | `tests/test_routing_surface.py` (new) | none (new file) | AC3,R2 | 4/4 |
| Test: `which_tool` map covers every `TOOL_NAMES` | same | none | R3 | — |
| Test: `capability_not_configured` live re-verify | same | none | R3 | — |

**Test blast-radius (mechanical):** grep of `prompts`/`PROMPT_NAMES`/`which_tool` across `tests/` → **no existing prompt test** (0 hits); the docstring/doc edits break nothing. README is a new consumer (the proving test), not a producer any test asserts today. `capability_not_configured` loosely covered at `test_freshness…:131` (a reason-set membership, unchanged) — the new focused test is additive.

### Rule compliance
- **R1.2/YAGNI** — docs + label + a runbook + 3 small tests; no new tool, no routing framework. ✅
- **R4** (no LLM in core) — prompts stay static text; nothing added calls a model. ✅
- **§061** — the explicit operator-facing label is how the prompts earn registration. ✅
- **§069** — description *content* untouched; this changes only the channel/framing. ✅
- **R2 (standard over sample)** — the recognition instrument is generic (intent per tool), names no repo. ✅

### Verification plan (per-AC, layer-matched)
| AC | risk layer | proof artifact | layer-match? |
|----|-----------|----------------|--------------|
| AC1 (cited surface statement) | documentation | recorded in working doc + PLAN, citing the field observation | ✅ |
| AC2 (design chosen + alternatives rejected in writing) | documentation | working doc + PLAN record | ✅ |
| AC3 (no unreachable capability unless labelled operator-facing in README+PLAN) | documentation/integration | `test_readme_documents_all_prompts_as_operator_facing` + PLAN grep + tools-invocable audit | ✅ |
| AC4 (re-runnable, non-contaminating recognition measurement) | documentation | the runbook exists + specifies blind order + a stated bar (manual-recorded) | ✅ |
| R3 (069 re-verify: capability + which_tool) | integration/logic | `test_find_view_data_reports_capability_not_configured_without_rules` + `test_which_tool_map_covers_every_tool` | ✅ |

No ❌ rows. No coverage-gap exclusions. `TRACK: backend` → no surfaces.

### Proving test
`tests/test_routing_surface.py::test_readme_documents_all_prompts_as_operator_facing` — asserts every `prompts.PROMPT_NAMES` entry appears in `README.md` and its prompts section is labelled operator-facing. **Fails pre-change** (README omits `which_tool` and carries no operator-facing label), **passes post-change**.
Invocation: `scripts/docker-test.sh pytest -q tests/test_routing_surface.py` (the `capability_not_configured` test builds an index — `fcntl`, Docker per AGENTS.md).

### Rollback + porting
Rollback: revert the `prompts.py` docstring, README, PLAN edits; delete the new runbook + test. No code behaviour, no schema. Single repo (`app`); no porting.

### SCOPE
`SCOPE: M` — unchanged from analysis. Docs (README, PLAN, prompts.py docstring), one new runbook, one new test file (3 tests). No behaviour change, no new tool. No tier crossing; branch type `feat` fits (the milestone is Agent-fit; a capability-correction + instrument). No outgrew-its-ticket nudge.

## Phase 3 — Execute

Branch `feat/081-routing-prompts-are-not-in-the-agents-surface`. Implemented the approved change list only.

### Verification sweep
- **Axis 1 (file set):** diff = `README.md`, `code_atlas/tools/prompts.py` (docstring), `docs/PLAN.md`, `docs/tasks/081*` (working doc), `docs/runbooks/tool-recognition-probe.md` (new), `tests/test_routing_surface.py` (new). All inside the approved list; no file outside; no untouched-line reformatting; each hunk maps to a matrix row.

```
$ git --no-pager diff --stat   (+ untracked runbook + test)
 README.md                       |  7 +-
 code_atlas/tools/prompts.py     |  9 +-
 docs/PLAN.md                    |  2 +-
```

- **Axis 2 (design conformance):** every Gate-2 Approach bullet `implemented-as-approved`:
  - `prompts.py` docstring relabels operator-facing + records the channel fact — done.
  - README §Prompts retitled operator-facing, `which_tool` row added, routing-in-descriptions note — done.
  - PLAN records the cited surface fact (AC1), the design decision + rejected alternatives (AC2), the 15th-tool cost (R5) — done.
  - New recognition-probe runbook (blind order, 14-question set, stated bar) — done.
  - New test file: proving test + which_tool-map-covers-all-tools + capability_not_configured re-verify — done.
  No `deviated` bullet. No behaviour change (prompts still registered; `PROMPT_NAMES`/functions untouched).

### Test results (Docker — Windows `pytest` red via `fcntl`, per AGENTS.md)
```
$ scripts/docker-test.sh pytest -q -k "routing_surface or tool_descriptions or view_data or freshness or mcp_server or prompt"
102 passed, 1035 deselected in 26.33s
```
Proving test `test_readme_documents_all_prompts_as_operator_facing` passed; `which_tool` map rendered via a real FastMCP `Client` and covers all 14 `TOOL_NAMES`; `capability_not_configured` re-verified live. Full CI gate below.

### Proven by
- **AC1** — cited surface fact recorded in PLAN §14 + this working doc (round 4 §0.5/§A.5).
- **AC2** — design decision + rejected alternatives recorded in PLAN §14 + Phase 2 here.
- **AC3** — `test_readme_documents_all_prompts_as_operator_facing` (README labels all 4 prompts operator-facing; PLAN carries the same framing) + the tools-all-invocable audit (14 `TOOL_NAMES`, no operator-only tool).
- **AC4** — `docs/runbooks/tool-recognition-probe.md` (blind order, fixed 14-question set, reproducible, stated bar).
- **R3 (069 re-verify)** — `test_which_tool_map_covers_every_tool` + `test_find_view_data_reports_capability_not_configured_without_rules`.

### Full CI gate (delta-green)
```
$ scripts/docker-test.sh   # ruff + mypy + pytest
1137 passed in 75.50s
```
Baseline 101 scoped -> green; +3 tests from 081; no new failure. Delta-green proven.

## Phase 4 — Review
**WAIVED** per run argument "with skipped review". No reviewer/challenger dispatch; no `Reviewed at` marker. Scope held (diff subset of approved list); no outgrew-its-ticket nudge.

## Phase 5 — Finalise
Outward actions (maintainer standing approval + run arg "commit + push + open PR"): commit (code+tests, docs) -> push branch -> open PR from template.
