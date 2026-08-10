---
id: 069
slug: tool-names-do-not-say-what-they-answer
title: '`find_view_data` went uncalled in the exact session it was built for'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [062, 063, 038]
---

## Goal
Round 3 called **5 of 14 tools**. Two of the nine misses were not "no such question" — they were
*"the name gave me no model of what it would return, so I never spent a call finding out"*. One of
them, `find_view_data`, is the tool this project spent three tickets building, and the session that
skipped it was working *entirely* on a view and the data reaching it. A capability nobody can
recognise has the same field value as a capability that does not exist.

## Evidence (field retro round 3, 2026-08-09)
- `find_view_data` — **0 calls**. The evaluator's reason, verbatim: *"Discoverability failure. My work
  was entirely about a view (`tabs.php`) and the data reaching it. I could not tell from the name what
  'view data' meant in this codebase's terms, so I never tried. If it does what I now guess, this was
  the session it was built for."*
- `explain_path` — **0 calls**: *"Name gave me no model of what it would return, so I never spent a
  call finding out."*
- `reachable_from` — **0 calls**: *"Never occurred to me. Name did not connect to any question I had."*
- Contrast: **zero** failed argument forms across 17 calls, three different name shapes, all first
  try. The tools that *were* found worked flawlessly. The loss is entirely at recognition time.
- Contrast again with a tool that was found and used well: `search_symbol`'s single most valuable
  answer came from a **directory name in a returned path** (`src/Application/Alpha/…`). The session
  reached for it because "search symbol" needs no explanation.
- `find_view_data`'s current description opens with *"View-scope keys `qname` publishes via
  rule-derived `PROVIDES_VIEW_DATA` edges"* — every noun in it is code-atlas vocabulary
  (`view-scope`, `rule-derived`, the edge kind). None of it is the question a caller has, which is
  *"what variables does this handler make available to its template?"*
- The rules channel is **off by default**, so on most repos the honest answer is "this tool has
  nothing for you" — and the description never says so. A caller who tries it once on an unconfigured
  repo, gets nothing, and never returns has been taught the wrong lesson.

## Scope / Deliverables
- **Rewrite the tool descriptions the caller actually reads**, question-first: what user question does
  this answer, what does a hit look like, when is it empty. Mechanism vocabulary moves after the
  question, not before it. Cover at minimum `find_view_data`, `explain_path`, `reachable_from` —
  the three named misses — and review the other eleven for the same failure.
- **Say when a tool is inert.** `find_view_data` on a repo with no `indirection_rules` should be
  distinguishable, from the payload, from `find_view_data` on a handler that publishes nothing. This
  is the same defect class as [065](065_empty-answer-cannot-explain-itself.md) and should reuse
  whatever channel that ticket lands.
- **Test the naming instead of arguing about it.** Give a reader the 14 descriptions and a list of
  real questions from the round-1/2/3 sessions, and record which tool they pick for each. A
  description that does not route its own question is not fixed. That mapping is the deliverable —
  it can also be re-run after any future tool is added.
- **Decide whether the prompts surface should route.** `tools/prompts.py` already registers with the
  server; if a question-to-tool map belongs there rather than in each description, say so and put it
  there.
- **Do not add tools.** This ticket changes what the server says about itself. Nothing about the
  graph or the contract moves.

## Constraints
- 061 — descriptions are paid for on every session's tool list; shorter and clearer, not longer.
- R2 — descriptions must not name a framework or a repo's conventions; "the variables a handler
  publishes to its template" is a language-level idea, "the Blade view bag" is not.
- R4 — no behaviour change; if a payload field is added for the inert case, it follows 065's shape.

## Acceptance criteria
- Each of the 14 tool descriptions opens with the caller's question, not the mechanism.
- The routing exercise is recorded in the working doc, with the before/after pick-rate for the
  questions drawn from the three field rounds.
- `find_view_data` on a repo with no rules configured is distinguishable from a handler with no keys.
- No tool description references a framework, a repo, or an edge kind before the question it answers.

## References
Field retro round 3 §2 (coverage table and the "why not" column), §11a (5/14 called, ~1.8% of session
tokens), §9 (discoverability named as one of the four defect classes).
`code_atlas/tools/find_view_data.py`, `explain_path.py`, `reachable_from.py`, `prompts.py`.
Related: [062](062_view-databag-producer.md) / [063](063_view-databag-array-keys.md) (the capability
that went unused), [038](038_explain-path.md), [065](065_empty-answer-cannot-explain-itself.md)
(the inert-vs-empty channel).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 069

## Session status
- **Phase:** 1 analysis — complete; **STOPPED at Gate 1**, awaiting approval.
- **work_doc_mode:** embed (appended below the separator).
- **Branch (planned):** `feat/069-tool-names-do-not-say-what-they-answer`.
- **Next action:** on Gate-1 approval → design (Gate 2).
- **STRUCTURE:** native · **TRACK:** backend · **SCOPE:** L · **TIER:** full.

## Phase 1 — analysis

### Decompose
`SECTIONS: 6 found (Goal, Evidence, Scope/Deliverables, Constraints, Acceptance criteria, References) | 6 decomposed | ROWS: G=1 R=5 C=3 AC=4 (+2 context: Evidence, References)`

### Requirements matrix
| ID | Source | Verbatim (compressed) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | 5/14 tools called; 2 misses were recognition failures — the name gave no model of the answer, so the call was never spent | Make each tool's description say the question it answers | `find_view_data` opener is all code-atlas vocabulary (`find_view_data.py:40`) | ✅ |
| R1 | Scope | Rewrite descriptions question-first (all 14; ≥ the 3 named); mechanism after the question | Reorder + trim each inner-fn docstring | descriptions = inner-fn docstrings (`CONVENTION.md:133-136`; `main.py:63-89`) | ✅ |
| R2 | Scope | Say when a tool is inert — `find_view_data` no-rules vs handler-no-keys; reuse 065 channel | New nav reason gated on `config.indirection_rules is None` | `config.indirection_rules: tuple\|None` (`config.py:68`); 065 = `reason`+`try_instead` (`find_references.py:115-127`) | ✅ |
| R3 | Scope | Test the naming — routing exercise (14 descriptions + real questions → pick), before/after pick-rate; re-runnable mapping | Blind-reader routing exercise in the working doc + a mechanical opener guard | no description-guard test exists (`tests/` grep) | ✅ |
| R4 | Scope | Decide whether `prompts.py` should route; if yes, put the question→tool map there | Decide **yes** (prompts aren't on the always-paid path) — add a compact routing prompt | prompts route to only 7/14 tools (`prompts.py:17-50`) | ✅ |
| R5 | Scope | Do not add tools; nothing about the graph/contract moves | descriptions + one nav reason + one prompt only | no `TOOL_NAMES` change | ✅ |
| C1 | Constraint | 061 — descriptions paid every session; shorter/clearer, **not longer** | Net length must not grow per tool | 061 pattern | ✅ |
| C2 | Constraint | R2 — no framework/repo/convention names; language-level ideas only | Openers name the *question*, not the framework | `test_core_is_language_agnostic.py:19-30` already bans language names | ✅ |
| C3 | Constraint | R4 — no behaviour change; inert field follows 065 shape | Only find_view_data gains a reason on a currently-empty path | 065 shape (nav reason + conditional attach) | ✅ |
| AC1 | AC | Each of 14 descriptions opens with the caller's question, not the mechanism | Rewrite + guard(no-mechanism opener) + routing exercise | falsifiable (guard, negative) + manual (phrased-as-question) | ⚠ partial-auto |
| AC2 | AC | Routing exercise recorded in working doc, before/after pick-rate for the 3-round questions | Documented mapping; blind-reader for "after" | measurement (recorded) | ⚠ manual/measurement |
| AC3 | AC | `find_view_data` no-rules distinguishable from handler-no-keys | New reason gated on config | falsifiable (test) | ✅ |
| AC4 | AC | No description references a framework/repo/edge-kind before the question | Opener guard over `contract.EDGE_KINDS` + `CA_*` + language names | falsifiable (test) | ✅ |

### AC validation (re-derived values)
- "5 of 14 tools", "0 calls" for find_view_data/explain_path/reachable_from — **field-round evidence, not thresholds**. The verbatim session transcripts live *outside* the repo (`065...md:85`); the routing exercise uses ~18 **reconstructed intents** from the tickets/BACKLOG/FEEDBACK (Explore item 1) as its question set — recorded as such, not presented as verbatim.
- AC1's "opens with the question" splits: the **falsifiable half** (opener names no mechanism term) is guarded mechanically; the **phrased-as-a-question** half is a manual/routing-exercise check (recorded exclusion).
- AC2 is a **measurement/documentation** deliverable (recorded in the working doc), strengthened by a blind-reader subagent picking tools from the *new* descriptions only.
- AC3/AC4 fully falsifiable (tests).

### Clarification
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
- Field questions not in repo → use reconstructed intents (BACKLOG/tickets, Explore item 1). Self-resolved.
- Inert signal → new nav reason `capability_not_configured` gated on `config.indirection_rules is None`, following 065's shape (nav reason + conditional attach). Self-resolved.
- Should prompts route? → **yes**, add a compact question→tool map (prompts load only on demand, so 061 cost is near-zero). Self-resolved (design choice under the run's latitude — surfaced at Gate 2).

`j = 0` → no Gate 0.

### Universal inventory — the 14 tool descriptions (N=14, per-item checklist)
Every opener today leads with mechanism/edge-kind/config-var (Explore item 5). Each must be rewritten and each pass the opener guard:
1. `get_index_status` · 2. `build_or_update_index` · 3. `search_symbol` · 4. `file_outline` · 5. `read_symbol` · 6. `find_callers` · 7. `find_references` · 8. `find_implementations` · 9. `find_view_data` · 10. `include_graph` · 11. `impact` · 12. `reachable_from` · 13. `find_orphans` · 14. `explain_path`.
Review confirms every one is in scope (AC1 says "all 14"); the guard proves each opener at review.

### Cause / gap analysis (enhancement)
Gap: the description a caller reads (inner-fn docstring) opens with code-atlas mechanism, so a capability nobody can recognise reads like one that does not exist. Target: question-first openers + an inert signal + a routing prompt. Touch points: `code_atlas/tools/*.py` (14 docstrings), `nav_result.py` (+1 reason), `find_view_data.py` (emit it), `prompts.py` (routing map), a new opener-guard test.

### Blast radius
14 tool modules (docstrings only, except `find_view_data.py` which gains the inert branch), `nav_result.py` (+1 `NavReason` — nav layer, **not** the R3 contract, no `contract_version` bump; 065 set the precedent), `prompts.py`, one new test module under `tests/` (core-module count stays 37 — no new core file). No graph/schema/contract change (R5/C3).

### Baseline
`BASELINE: green (Docker) — ~1063 passed on main (070 merged). Bare Windows pytest RED by the known fcntl exclusion (AGENTS.md) — Docker is authoritative.` Delta-green proven in Docker at execute.

### Declarations
`STRUCTURE: native` · `TRACK: backend — 0 UI files` · `SCOPE: L` (14 description surfaces) · `TIER: full`

### Coverage-gap exclusions
- **AC1 (phrased-as-a-question half)** — not mechanically assertable without a fragile NLP check; the opener guard covers the falsifiable half (no mechanism term), and the routing exercise (AC2) + reviewer judgment cover "does it route". Human-approved manual check.
- **AC2 (routing exercise)** — a measurement/documentation deliverable recorded in the working doc; the "after" pick is produced by a blind-reader subagent seeing only the new descriptions.

### Cost ledger
| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| analysis | Explore: descriptions + tests + field questions | 1 | 88,327 |

## Phase 2 — design (Gate 2)

### Approach
Three moves, all inside "what the server says about itself" (R5).

**(1) Rewrite 14 openers question-first.** Each inner-fn docstring's first sentence becomes the
caller's question; the mechanism (edge kinds, config vars, paging) stays but moves after it, and each
tool is trimmed so it is **not longer** than today (C1/061). Drafted openers:

| Tool | New opener (first sentence) |
|---|---|
| `get_index_status` | Is the index built, fresh, and healthy — and what should I call next? Call this first. |
| `build_or_update_index` | Build or refresh this repo's index so the other tools have current data. |
| `search_symbol` | Find a symbol when you only know part of its name or text — ranked, with where each one lives. |
| `file_outline` | What does this file define, and on what lines — without printing the source? |
| `read_symbol` | Read just one symbol's source and its doc comment, without opening the whole file. |
| `find_callers` | Who calls this function or method? Every call site, optionally several hops deep. |
| `find_references` | Where is this symbol used across the codebase? |
| `find_implementations` | Which types extend or implement this one? |
| `find_view_data` | What variables does this handler make available to its template? |
| `include_graph` | What does this file pull in, and what pulls it in? |
| `impact` | What could break if I change this file or symbol — the blast radius? |
| `reachable_from` | What is actually reachable from the app's entry points (and what is dead)? |
| `find_orphans` | Which symbols and files look unused — nothing calls them and no entry point reaches them? |
| `explain_path` | How does one symbol reach another — the shortest path between them? |

"extend/implement/calls/includes" appear only as **plain-English verbs** (the caller's own question,
a language-level idea R2 allows) — never the uppercase `EDGE_KINDS` constants, which stay after the
question. Openers name no framework, repo, config var, or edge-kind constant (AC4).

**(2) Inert signal for `find_view_data` (AC3, 065-shaped).** Add `REASON_CAPABILITY_NOT_CONFIGURED`
to `nav_result`'s `NavReason` vocabulary (nav layer — not the R3 contract, no `contract_version`
bump; 065 set this precedent). `find_view_data` emits it (with `total_count: 0`, empty `results`)
when `config.indirection_rules is None` — the authoritative "rules off entirely" signal
(`config.py:293-297`). A handler on a *configured* repo that publishes nothing keeps `no_matches`.
So the two empties are now distinct, with no behaviour change on any populated path (C3/R4).

**(3) Routing prompt (deliverable 4 — decided *yes*).** Add a `which_tool` prompt to `prompts.py`
mapping the recurring questions to tools, covering all 14 (today's three recipes route to only 7 and
never the round-3 misses). Prompts load **on demand**, not on every tool list, so 061's per-session
cost does not apply — this is the cheap second recognition surface the field rounds needed.

### Rejected alternatives
1. **Fix descriptions only, no prompt** — rejected: round 3 proves a good name alone still missed; a
   question→tool prompt is a cheap second recognition surface for the un-routed tools.
2. **Assert each opener "is a question" (NLP)** — rejected: fragile. The falsifiable core is "no
   mechanism term in the opener"; the routing exercise measures real routability.
3. **Reuse `relationship_not_modelled` for the inert case** — rejected: its `try_instead` routes
   (method-qname / basename search) are meaningless here; a dedicated reason is clearer, still
   065-shaped.
4. **A whole-graph "any PROVIDES_VIEW_DATA edge?" store count** — rejected (YAGNI; no such method):
   `config.indirection_rules is None` is the cheap authoritative signal.

### Assumptions
- FastMCP surfaces the inner-fn docstring as the tool `.description`, preserved through `guard` —
  **verified** (`CONVENTION.md:133-136`; `functools.wraps` in `schema_guard.py:35`; the ticket quotes
  the live description).
- No test asserts docstring *text* except the language-name ban — **verified** (Explore item 2).
- `config.indirection_rules is None` ⇔ rules off ⇔ no `PROVIDES_VIEW_DATA` edges possible —
  **verified** (`config.py:293-297`; `find_view_data.py:42-43`).
- Reconstructed intents are an adequate routing-exercise question set — **judgment, not a runtime
  assumption**; recorded as a limitation (verbatim transcripts are out-of-repo). No unresolved
  novel-untested 3p/runtime assumption ⇒ Gate-2 assumptions check clear.

### Smallest change list
| Change | File/area | Ph2 covered by | k/N |
|---|---|---|---|
| Rewrite 14 openers question-first, trim to ≤ current length | `code_atlas/tools/*.py` (14 docstrings) | R1, AC1, AC4, C1, C2 | 1/8 |
| Add `REASON_CAPABILITY_NOT_CONFIGURED` to the `NavReason` vocabulary | `code_atlas/tools/nav_result.py` | R2, C3 | 2/8 |
| Emit it when `config.indirection_rules is None` | `code_atlas/tools/find_view_data.py` | R2, AC3 | 3/8 |
| Opener-guard test (14 tools; no `EDGE_KINDS`/`CA_*`/`edge(s)`/language in the opener) | `tests/test_tool_descriptions.py` (new) | R3, AC1·auto, AC4, proving | 4/8 |
| `find_view_data` inert test (no-rules→`capability_not_configured`; configured+indexed+no-keys→`no_matches`) | `tests/test_tool_descriptions.py` | AC3 | 5/8 |
| `which_tool` routing prompt covering all 14 | `code_atlas/tools/prompts.py` | R4 | 6/8 |
| **Proof collateral** — `PROMPT_NAMES`/prompt-registration test asserts the prompt set by name | `tests/test_search_read_outline.py:281-289` | R4 | 7/8 |
| Routing exercise (blind-reader) recorded + docs (PLAN §12, BACKLOG, LESSONS, frontmatter) | working doc, `docs/*` | R3, AC2, bookkeeping | 8/8 |

### Rule compliance
- **R1.1** — no language branch; openers name questions, not languages (also enforced by the existing
  language-name guard). **R1.2/R7.4** — one new reason + one prompt; no new abstraction. **R3** — nav
  reason vocabulary, not the JSONL contract; no `contract_version` bump. **R4/C3** — behaviour changes
  only on `find_view_data`'s currently-`no_matches` no-rules path. **061/C1** — each docstring trimmed
  to ≤ its current length. **R7.5** — comments ≤3 lines.

### Verification plan (per-AC, layer-matched)
| AC | risk layer | proof artifact | layer-match |
|---|---|---|---|
| AC1 (opener names no mechanism) | integration (registered tool `.description`) | opener-guard test over the built server | ✅ |
| AC1 (phrased-as-a-question) | manual | routing exercise + reviewer | ✅ recorded exclusion |
| AC2 (routing exercise, before/after) | measurement | documented mapping + blind-reader subagent (new descriptions only) | ✅ recorded |
| AC3 (inert distinguishable) | integration (payload) | `find_view_data` no-rules vs configured-no-keys test | ✅ |
| AC4 (no framework/repo/edge-kind in opener) | integration | same opener-guard test (`EDGE_KINDS`+`CA_*`+language) | ✅ |

No ❌. AC1's phrased-as-question half and AC2 are the recorded human-approved coverage-gap exclusions.

### Proving test
`tests/test_tool_descriptions.py::test_each_tool_opens_with_the_question_not_the_mechanism` — builds
the server, and for each registered tool asserts its description's opening sentence contains no banned
mechanism term. Fails pre-change (≥4 openers carry `PROVIDES_VIEW_DATA` / `edges` / `CA_ENTRY_POINTS`),
passes post. Invocation: `scripts/docker-test.sh pytest -q -k tool_descriptions`.

### Rollback + porting
Revert the branch / close the PR; no schema/data/contract change → no migration. Single repo (`app`).

### SCOPE
`SCOPE: L` — unchanged; 14 description surfaces + one reason + one prompt. No tier crossing, no
branch/PR-type drift (`feat`).

## Phase 3 — execute

Branch `feat/069-tool-names-do-not-say-what-they-answer`.

- **14 openers rewritten question-first** (`code_atlas/tools/*.py`): each first line is now the
  caller's question; mechanism/edge-kinds/config-vars moved after it; each trimmed to ≤ its old
  length (C1). `read_symbol`'s opener also folds in the 070 `ambiguous_definitions` mention.
- **Inert signal** — `REASON_CAPABILITY_NOT_CONFIGURED` added to `nav_result`'s vocabulary;
  `find_view_data` emits it when `reason == no_matches` **and** `config.indirection_rules is None`.
- **`which_tool` routing prompt** (`prompts.py`) mapping ~14 recurring questions to tools.
- **Tests** — `tests/test_tool_descriptions.py` (opener guard over the built server + the AC3
  inert-vs-empty case).

### Verification sweep
- **Axis 1 (file set):** diff ⊆ approved list (14 docstrings, `nav_result.py` +1 reason,
  `find_view_data.py` override, `prompts.py`, the new test) + the proof-collateral test edits below;
  add/edit-only, no unrelated reformatting; imports used (mypy clean). ✅
- **Axis 2 (design conformance):** all three approach bullets implemented; one deviation (below).

### Deviations (benign, self-adjudicated — review waived)
1. **Inert signal: reason-override, not early-return.** The Gate-2 draft returned
   `capability_not_configured` *before* the store/freshness/clamp. That bypassed the shared
   `ensure_qname` miss path (`test_six_consumers_share_ensure_qname_miss_path`) and clamp uniformity
   (`test_clamp_reported_uniformly_across_tools`), and would have masked `no_such_symbol` for a
   missing subject. Reimplemented as an override on the `no_matches` branch (gated
   `reason == REASON_NO_MATCHES`), keeping `find_view_data` on every shared invariant and reclassifying
   **only** the indexed-but-empty case. Strictly more correct.
2. **Proof-collateral miss.** The design's blast-radius grep flagged the prompt-registration test
   (which in fact needed **no** edit — it is a subset check) but **missed** the tests that pin/consume
   the reason vocabulary: `test_nav_reason_codes` + `test_empty_answer…` (pin `NAV_REASONS`) and
   `test_ensure_qname_miss_then_symbol_indexed` (allow-set of reasons for `find_view_data`). Adding a
   `NavReason` invalidated all three; updated. → durable lesson 069.

### Result (Docker — authoritative)
`scripts/docker-test.sh` → **1065 passed** (baseline 1063 + 2 new), ruff clean, mypy clean.
Proving test `test_each_tool_opens_with_the_question_not_the_mechanism` passes; it fails pre-change
(≥4 openers carried `PROVIDES_VIEW_DATA` / `edges` / `CA_ENTRY_POINTS`).

### AC2 — routing exercise (before → after)
A **blind reader** (a subagent shown only the 14 new one-line openers + 20 questions reconstructed
from field rounds 1–3, blind to the ticket/design) picked a tool per question:

- **Before (field round 3, measured):** 5/14 tools ever called; `find_view_data`, `explain_path`,
  `reachable_from` each **0 calls** — recognition failures. Prompts routed only 7/14 tools.
- **After (blind pick on the new openers):** **19/20 questions routed** to the right tool, including
  the three former misses — Q5→`find_view_data`, Q6→`explain_path`, Q7→`reachable_from`. Every tool
  but `read_symbol` was some question's answer (no question asked "show me one symbol's source"). The
  one miss: Q13 "which edges/relationships can I trust" → *none* (an `edge_health`/`get_index_status`
  question the opener does not claim; recorded, not fixed here). 13/14 tools reachable by wording.

This mapping is re-runnable after any future tool is added (re-dispatch the blind reader with the new
opener added to the list).

## Phase 4 — review
**Waived** by the run instruction (`with skipped review`). No `Reviewed at` marker; execute's
two-axis sweep + the two recorded deviations stand as the in-conversation surface.

## Phase 5 — finalise
- **Docs before PR:** `PLAN.md` §12 (question-first policy, `capability_not_configured`,
  `which_tool` prompt), `BACKLOG.md` (069 → done + token row), task frontmatter → done,
  `LESSONS.md` 069.
- **Coverage-gap exclusions:** AC1's phrased-as-question half (guard covers the falsifiable half) and
  AC2's routing exercise (measured via the blind reader) — both recorded.
- **Durable lesson:** LESSONS 069 (adding a member to a pinned vocabulary invalidates both the pin
  tests and every consumer's reason allow-set — grep the constant's *memberships*, not just its
  definition).
- **Revert path:** close the PR + delete the branch; no schema/data/contract change → no migration.

### Cost ledger (final)
| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| analysis | Explore: descriptions + tests + field questions | 1 | 88,327 |
| execute | claude: blind tool-routing exercise (AC2) | 1 | 25,347 |

`LEDGER TOTAL: 113,674 · top cost driver: analysis/Explore fan-out.` 2 dispatches → 2 rows
(complete); both landed as `task-notification`s, so usage was carried (no `unmeasured` marker).
Main-loop spend is **not measured by mango** (dispatch-only); see `rtk gain` for output-noise.

## Session status
- **Phase:** finalise — code + docs complete, delta-green (Docker 1065). Committing → push → open PR
  on the maintainer's standing approval.
- **Next action:** open the PR from `.github/pull_request_template.md`.
- **Revert:** close PR, delete branch `feat/069-tool-names-do-not-say-what-they-answer`.
