---
id: 097
slug: recognition-probe-measures-names-not-recall
title: 'The recognition probe scored 14/14 off bare names — it cannot measure 081, and it misses the failure that costs'
phase: 1.5b
milestone: Measure
status: done
depends_on: [081, 069, 074]
---

## Goal
Round 5 ran the first blind recognition probe (`docs/runbooks/tool-recognition-probe.md`) and scored
**14 / 14**, including the `find_callers` vs `find_references` confusion the protocol says to watch.
The round's own reading of that score: **the probe is saturated, and the rate is close to
meaningless.**

Two independent reasons, both of which the protocol currently cannot detect:

1. **Seven of the fourteen answers were given without ever reading a description.** The harness
   defers MCP tool schemas — the agent sees a bare name list and must explicitly fetch a schema
   before a tool is callable. The evaluator fetched 7. [081](081_routing-prompts-are-not-in-the-agents-surface.md)
   moved routing *into the tool descriptions*, and §0.5 is its stated proxy measurement — but more
   than half the descriptions were never in context, so **the proxy measured names, not descriptions,
   and 081's mechanism is untested**. §A.7 is recorded `NOT OBSERVED` for exactly this reason.
2. **Recognition is not recall.** The evaluator named `file_outline` correctly at Q4, had loaded its
   description, and then did not call it at the moment it would have prevented a committed error —
   hand-counting a 1,196-line legacy file's functions, getting it wrong, and shipping "eight" into a
   comment and a tracking registry. The probe asks *given the question, name the tool*. Real work
   fails at *given the situation, notice there is a question*. **Only the second faculty cost
   anything this round.**

## Evidence (field retro round 5, 2026-08-14, §0.5 + §2 + §11.1–§11.3, §11.6)
- Declared before scoring: *"Only 7 of the 14 tool descriptions were ever loaded into context … For
  the other 7 my answer below is derived from the name alone."*
- Second declared caveat: the host repo's own agent guide pre-routes five tool names verbatim, which
  is routing priming from outside code-atlas and biases the rate upward.
- §2 coverage: **6 of 14 tools in the work, 7 of 14 including probes.** Of the 8 unused, 5 "did not
  fit"; the other 3 are exactly the tools whose descriptions were never loaded (`find_callers`,
  `include_graph`) or loaded-but-not-recalled (`file_outline`).
- §2's three buckets ("did not fit" / "did not know it would answer this" / "knew it, did not trust
  it") have **no slot for the answer that was true**: *knew it, it fit, did not think of it in the
  moment*. That happened twice — `file_outline` (§11.3) and `search_symbol kind:"Function"` (§7.3,
  the redeclare-trap question answered by a narrower `grep`).
- Probe P4, post-hoc, on the legacy source the evaluator had already read by hand: **7 functions + 2
  closures with line ranges, ~1 KB** — *"the exact map I read 1,196 lines to build, and the exact
  count I got wrong."*

## Scope / Deliverables
This ticket changes the **measurement protocol and the routing surface**, not the index.

- **Record resident descriptions before scoring §0.5.** The probe template must require the evaluator
  to state how many of the N tool descriptions were in context at scoring time, and to mark each
  answer as name-only or description-backed. A rate scored off names must be reported as such.
- **Make the probe discriminating again.** A test a bare name list passes at 100 % measures nothing
  about descriptions. Design a §0.5 variant that can fail — candidates to weigh: questions phrased in
  the user's words rather than the tool's, near-miss pairs that names alone cannot separate, or
  scoring routing *only* over tools whose descriptions were loaded. Pick one and say why.
- **Add the fourth coverage bucket to §2:** *"knew it, it fit, did not think of it."* Mis-filing a
  recall failure as a discovery failure sends the wrong fix — discovery wants better descriptions,
  recall wants a workflow trigger.
- **Decide what a recall trigger is, for the one case the field named.** `file_outline` on a large
  source file before porting/reading it is, per §11.3, *"the highest-leverage uncalled tool in this
  repository"* and nothing in the tool surface or the workflow says so. Decide where such a trigger
  can honestly live (tool description? `next_tool_suggestions`? the onboarding runbook?) — and if the
  answer is "outside code-atlas", record that verdict, because it bounds what 081-style fixes can
  ever achieve.
- **Feed 074.** This round is n = 1 for the session type *legacy→unified port*; the protocol change
  must not reset the counter.

## Constraints
- R4 / no LLM in the core — a "trigger" must not become a heuristic that makes the core
  non-deterministic. `next_tool_suggestions` is existing, deterministic machinery; anything beyond it
  needs a stated reason.
- 061 — a suggestion field that fires on every payload has a token cost; scope it to the occasions
  that earn it.
- The probe protocol is a doc change; do not let it grow into a benchmark harness. 055 and 074 own
  measurement infrastructure.
- Do not re-open 081's reclassification decision — it stands. This ticket says its *measurement* did
  not happen, not that it was wrong.

## Acceptance criteria
- `docs/runbooks/tool-recognition-probe.md` requires a resident-description count and per-answer
  name-only / description-backed marking, and the retro template's §0.5 asks for it.
- The revised §0.5 has at least one question shape that a bare name list demonstrably fails; the
  design records why that shape discriminates.
- §2's bucket list has four buckets, with the new one defined and its opposite fix named.
- A written verdict on where a `file_outline`-before-you-read trigger can live, with the decision and
  its rationale recorded here.
- 081's `NOT OBSERVED` verdict is re-scorable in round 6 — i.e. the protocol now produces a number
  that could distinguish "descriptions route well" from "names are self-evident".

## References
Field retro round 5 §0.5 (both caveats), §2, §A.7, §11.1, §11.2, §11.3, §11.6, §7.3; candidates 6
and 7.
Related: [081](081_routing-prompts-are-not-in-the-agents-surface.md) (the fix this was meant to
measure), [069](069_tool-names-do-not-say-what-they-answer.md) (question-first descriptions;
`find_view_data` lacked an *occasion*, not recognition — the same recall/discovery split),
[074](074_does-the-index-harm-mechanism-questions.md) (the n-counter this round advances),
[055](055_recall-benchmark.md), [044](044_onboarding-runbook.md).

## Resolution
**Two rates.** Name-inclusive `recognised/14` stays, labelled as such. The 081 proxy is the
description-backed rate (`recognised among description-backed / D`, `D` = answers marked
description-backed; `D` = `K` only if no schema loaded mid-probe). If `D = 0`, 081 is
`NOT OBSERVED`. If `K < 14`, a name-inclusive 14/14 is not an 081 score.

**Discriminating question.** Q4 is rewritten in the user's occasion, with no "outline": *"I am
about to port a thousand-line source file. I need its symbols and line ranges without reading the
body, so I do not count functions by hand."* Combined with scoring only over loaded descriptions,
a name-only pass can fail. Near-miss pairs stay as a confusion watch; they are not the 081
discriminator (round 5 already separated those off names).

**Retro template.** Created `docs/runbooks/field-retro.md` — the artifact AC1 named that did not
exist. §0.5 requires resident `K/14`, per-answer marking, and the two rates. §2 has four buckets;
the new one is *knew it, it fit, did not think of it* → workflow trigger, not a better description.

**`file_outline` trigger verdict.** The occasion lives in the tool description (after the
question-first opener) and in `docs/runbooks/onboarding-a-repo.md` §7. It does **not** live in
`next_tool_suggestions`: the core cannot see that the agent is about to Read a large file, and a
suggestion on every payload violates 061. **Bound on 081-style fixes:** descriptions can name the
occasion; they cannot make the agent notice.

**074.** This protocol change does not reset n. Round 5 remains n = 1 for *legacy→unified port*.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 097 — recognition probe measures names, not recall (working doc)

- **Ticket:** 097 · local-file `docs/tasks/097_recognition-probe-measures-names-not-recall.md`
- **Type:** docs / measurement protocol
- **Repo(s) / Porting:** app only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `scripts/docker-test.sh pytest -q` on untouched `main`: **1183 passed**.

---

## Phase 0 — Refine

`PREMISE: ~12 reference(s) checked | 0 missing | 1–2 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 5 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 5 ASSUMED | skip: no`

Resolved as existing: `docs/runbooks/tool-recognition-probe.md`, `file_outline.py`,
`next_tool_suggestions` (`get_index_status.py`), `docs/runbooks/onboarding-a-repo.md`, tickets
081/069/074/055/044, PLAN §19. Ambiguous / to-be-created (not PREMISE FALSIFIED): “the retro
template’s §0.5” — no such file existed. HOW: create thin `docs/runbooks/field-retro.md`.

**INPUT KIND:** ticket (single deliverable). **work_doc_mode:** embed (plain tracked local-file ticket).

**Recalled claims (advisory):** 093-C1 `try-instead-tool-name`; 093-C2 `derived-not-listed-invariant`;
093-C3 `prove-the-guard-fails`; 093-C4 `route-must-answer`. 081/069 by area: descriptions need an
*occasion*; a capability on an unseen channel is unshipped.

**HOW (cited):**
1. Probe protocol: resident count + name-only/description-backed marking — ticket Scope L51–53.
2. No LLM in core; no always-on suggestion field — R4, 061.
3. Do not re-open 081’s reclassification — ticket C.

**ASSUMED (awaiting ratification) — standing “best option”, confirmed at Gate 1:**

| # | Assumed choice | Why | Reverses prior? |
|---|----------------|-----|-----------------|
| A | Two rates: name-inclusive `recognised/14` (labelled) + description-backed / K as the 081 proxy. K=0 → `NOT OBSERVED` | Ticket Scope + AC5; a single 14/14 hid the unloaded half | no |
| B | Discriminating question: rewrite Q4 in occasion words, no “outline”. Combined with A | Current Q4 is almost the opener and still scored 14/14 off names | no |
| C | Create `docs/runbooks/field-retro.md` — missing retro template. Thin §0.5 + §2 | AC1 names an artifact that did not exist; 055/074 own harnesses | no |
| D | `file_outline` occasion in the description (after opener) **and** onboarding §7. Not `next_tool_suggestions` | 061 every-payload cost; core cannot see “about to Read”; R4 if size heuristics | no |
| E | 097 does not reset 074’s n=1 for *legacy→unified port* | Ticket Scope “Feed 074” | no |

**Constraints from scan:** R4, 061, do not grow a benchmark harness, do not reopen 081.

**Exposure-checker:** 1 dispatch ([Exposure-checker](3597f77f-de53-4c10-9d54-45c75fd09812)).
`UNEXPOSED: 2` — both already ASSUMED and shipped; no new WANT.
1. WANT: which artifact is “the retro template” — **ASSUMED C** (`docs/runbooks/field-retro.md`).
2. WANT: if the trigger lives in-repo, is the written verdict enough or must the surface change —
   **ASSUMED D** (verdict + description + onboarding; not `next_tool_suggestions`).

---

## Requirements matrix

`SECTIONS: 6 found (Goal, Evidence, Scope / Deliverables, Constraints, Acceptance criteria, References) | 6 decomposed | ROWS: C=4 R=5 G=2 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | 7/14 answers name-only; 081 untested | Two rates; 081 = description-backed / K | probe had one rate | CL1, CL2 | `test_probe_requires_resident_marking_and_two_rates` | ✅ |
| G2 | Goal | Recognition ≠ recall; file_outline named then unused | Fourth bucket + trigger verdict | retro §2 had 3 buckets | CL2, CL3, CL4 | retro test + resolution | ✅ |
| R1 | Scope | Record resident descriptions; mark each answer | Protocol steps 2–4 | probe.md Protocol | CL1 | proving test tokens | ✅ |
| R2 | Scope | Make the probe discriminating; pick one shape and say why | Q4 occasion-worded + score-over-loaded | old Q4 ≈ opener | CL1 | `test_file_outline_question_is_not_answerable_from_the_name` | ✅ |
| R3 | Scope | Fourth §2 bucket + opposite fix | *knew it, it fit, did not think of it* → workflow trigger | no retro file | CL2 | `test_retro_template_asks_for_resident_count_and_four_buckets` | ✅ |
| R4 | Scope | Decide where file_outline trigger can live | Description + onboarding; not next_tool_suggestions | file_outline.py opener; get_index_status suggestions | CL3, CL4 | description + onboarding tests + Resolution | ✅ |
| R5 | Scope | Feed 074; do not reset n | One sentence on 074 | 074 L100–101 | CL5 | `test_074_n_counter_is_not_reset` | ✅ |
| C1 | Constraints | R4 / no LLM in core | No size heuristic, no model in indexer | R4 | CL3 (rejected suggestions) | no core heuristic added | ✅ |
| C2 | Constraints | 061 — no every-payload suggestion | Occasion not on next_tool_suggestions | get_index_status.py | CL3 | Resolution + onboarding note | ✅ |
| C3 | Constraints | Probe is a doc; not a harness | field-retro.md is a template | 055/074 | CL1, CL2 | no new benchmark module | ✅ |
| C4 | Constraints | Do not reopen 081 reclassification | Prompts stay operator-facing | 081 done | — | README still operator-facing | ✅ |
| AC1 | AC | probe requires resident + markings; retro §0.5 asks for it | Both files carry the tokens | no retro file | CL1, CL2 | proving + retro tests | ✅ |
| AC2 | AC | ≥1 question a name list fails; design records why | Q4 + “Why Q4 discriminates” | old Q4 contained outline-adjacent wording | CL1 | Q4 test + probe § | ✅ |
| AC3 | AC | §2 has four buckets; new one defined + opposite fix | field-retro.md §2 table | 3 buckets in ticket | CL2 | retro test | ✅ |
| AC4 | AC | Written verdict on file_outline trigger | Resolution section | — | CL3, CL4 | ticket Resolution | ✅ |
| AC5 | AC | 081 NOT OBSERVED is re-scorable in round 6 | description-backed rate / K | single 14/14 | CL1 | proving test `NOT OBSERVED` | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? |
|-------|---------------|------------------------|--------|--------------|
| AC1 | resident count + markings; retro §0.5 asks | Y — both files | Y | greppable |
| AC2 | a name-list-failing shape + why | Q4 has no “outline”; probe records why | Y | greppable |
| AC3 | four buckets + opposite fix | §2 table | Y | greppable |
| AC4 | written verdict | Resolution | Y | present/absent |
| AC5 | 081 re-scorable | two rates + NOT OBSERVED when K=0 | Y | protocol text |

`CLARIFICATION: 5 raised | 5 self-resolved as ASSUMED A–E (standing best-option) | j=0`

---

## Phase 1 — Analysis ✋ Gate 1

- **Root cause:** `validation` — the probe scored recognition off names and had no slot for recall.
- **Handler:** protocol + retro template + `file_outline` occasion sentence + onboarding note.
- `RULE SECTIONS: R1.1 ✅ · R1.2 ✅ · R4.2 ✅ · R6.1 ✅ · R7.1 ✅`
- **Gate 1 status:** cleared (standing approval, ASSUMED A–E ratified)

---

## Phase 2 — Design ✋ Gate 2

- **Approach:** Rewrite the probe protocol (resident K, markings, two rates, occasion-worded Q4).
  Create `field-retro.md` with §0.5 and four §2 buckets. Add one occasion sentence to `file_outline`
  after the opener (069 stays green). Add the same occasion to onboarding §7. Record the verdict:
  descriptions can name the occasion; they cannot make the agent notice. Do not touch
  `next_tool_suggestions`. Do not reset 074’s n.
- **Rejected:** (1) near-miss pairs alone as the 081 discriminator — round 5 already separated
  `find_callers` / `find_references` off names. (2) `next_tool_suggestions` for file_outline — 061
  and the core cannot see “about to Read”. (3) A size heuristic in the core — R4. (4) Growing a
  benchmark harness — 055/074.

**Assumptions**

| Assumption | verified / novel-untested |
|------------|---------------------------|
| `test_tool_descriptions` only gates the opener line | verified — `_opener` is first line |
| `next_tool_suggestions` is status-only / build-when-stale | verified — `get_index_status.py` |
| Intended-tool set can be derived from `TOOL_NAMES` | verified — 14 tools, 14 probe rows |
| No 3p/runtime novelty | verified |

**Change-list**

| Change | File | Blast radius | Ph2 | k/N |
|--------|------|--------------|-----|-----|
| CL1 rewrite probe protocol + Q4 | `docs/runbooks/tool-recognition-probe.md` | 081 AC4 still a protocol, not a harness | G1, R1, R2, AC1, AC2, AC5 | 8/16 |
| CL2 create retro template §0.5 + §2 | `docs/runbooks/field-retro.md` (new) | none | R3, AC1, AC3 | 8/16 |
| CL3 occasion sentence after opener | `code_atlas/tools/file_outline.py` | 069 opener tests; MCP description | R4, AC4, C1, C2 | 8/16 |
| CL4 onboarding §7 occasion | `docs/runbooks/onboarding-a-repo.md` | latency table | R4, AC4 | 8/16 |
| CL5 074 n not reset + PLAN §19 shipped | `docs/tasks/074_…`, `docs/PLAN.md` | 074 counter | R5 | 8/16 |
| CL6 proving + surface-guard tests | `tests/test_recognition_probe_protocol.py` | `TOOL_NAMES` derivation | AC1–AC5, R1.1 | 8/16 |
| CL7 CONVENTION layout, README probe pointer, BACKLOG, ticket Resolution | docs / README | `test_readme_documents_all_prompts_as_operator_facing` still green | C4 | 8/16 |

`HANDLES: 4 recalled | 2 traced | 2 does not apply | 0 unanswered`

| Handle | Answer |
|--------|--------|
| `derived-not-listed-invariant` | **traced** — intended tools parsed from the probe table and compared to `main.TOOL_NAMES`. |
| `prove-the-guard-fails` | **traced** — `test_the_probe_surface_guard_can_actually_fail` injects `not_a_real_tool`. |
| `try-instead-tool-name` | **does not apply because** this change adds no `try_instead` field. |
| `route-must-answer` | **does not apply because** this change adds no route. |

**Proving test:** `pytest tests/test_recognition_probe_protocol.py::test_probe_requires_resident_marking_and_two_rates`

| AC | risk layer | proof | layer-match |
|----|------------|-------|-------------|
| AC1 | logic (doc tokens) | proving + retro tests | ✅ |
| AC2 | logic (Q4 text) | Q4 has no “outline” | ✅ |
| AC3 | logic (doc tokens) | retro four-bucket test | ✅ |
| AC4 | e2e (written verdict) | ticket Resolution | ✅ |
| AC5 | logic (protocol) | two rates + NOT OBSERVED | ✅ |

- **Gate 2 status:** cleared (standing approval)

---

## Phase 3 — Execute

- **Branch:** `docs/097-recognition-probe-measures-names-not-recall`
- **Proving test added:** `tests/test_recognition_probe_protocol.py`
- **Verification sweep:** file axis ✅ (diff ⊆ list). Behaviour: two rates, occasion Q4, four buckets,
  description+onboarding trigger, 074 n unchanged, no `next_tool_suggestions` change.
- **Empirical:**

```
$ scripts/docker-test.sh pytest -q
# baseline (main): 1183 passed
# post-change: 1191 passed in 56.08s (+8 new tests, none removed)
# first Docker run: 1 failed (097 marked done before the Token usage row) — fixed
```
- **Golden/snapshot:** none
- **Design-invalidation:** none

## Phase 4 — Review ✋

**WAIVED** at solve invocation (`with skipped review`). No `Reviewed at` marker. No reviewer/challenger
dispatch this phase.

## Phase 5 — Finalise ✋

- Planned outward actions (standing AGENTS.md + this solve): commit, push branch, open PR via `gh`.
- Durable lesson: written to `docs/LESSONS.md`.
- Revert: revert the PR commit.

### Learning loop

`CLAIMS: 2 claim(s) from 1 lesson entry | T1=0 T2=1 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true | 0 falsified | 0 not cheaply checkable`
`PROMOTION: 1 proposed | 0 human-ratified (already in R6.7 from 093/095) | mango files written: 0`

Cross-ticket: `derived-not-listed-invariant` seen 093, 095, 097 — already promoted to R6.7.
`/mango:promote` is the cross-ticket pass; this orchestrator does not invoke it. The new type-5
claim (recognition ≠ recall; descriptions name the occasion but cannot make the agent notice)
stays in `lessons_path` / PLAN §19.

---

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 0 refine | exposure-checker (challenger) | 1 | unmeasured (host does not surface usage) | none |

`LEDGER TOTAL: unmeasured (host does not surface usage) · top cost driver: refine exposure-checker`

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Gate 1 | ASSUMED A–E ratified | standing best-option |
| Gate 2 | Q4 + two rates; retro file; description+onboarding; not suggestions | 081/061/R4 |
| Gate 4 | review waived | solve invocation |
| final | commit + push + PR | AGENTS.md standing + this solve |

## Session status

- **Last updated:** 2026-08-15
- **Current phase:** done (PR #107)
- **work_doc_mode:** embed · `docs/tasks/097_recognition-probe-measures-names-not-recall.md`
- **Next action:** none
- **Blocked on:** none

