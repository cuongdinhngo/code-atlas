---
id: 300
slug: the-index-is-registered-permitted-and-never-chosen
title: 'The index is registered, permitted and never chosen — 0 tool calls in three uncoached sessions'
phase: 1.5b
milestone: Adoption
status: in-progress
depends_on: [074, 200, 266, 268]
---

## Goal
Three uncoached headless sessions asked an ordinary navigation question with all 24 code-atlas tools
**registered, connected and permitted**, and made **0 index calls** between them. Find out why an
agent that can use the index does not, and change whatever is responsible.

This is not a measurement of answer quality. It is prior to one: [074](074_does-the-index-harm-mechanism-questions.md)
cannot buy a granted arm until this moves, because a granted cell that never calls the index is a
native-tools cell wearing the arm's label.

## The evidence (protocol: [`benchmarks/074_mechanism-question.md`](../benchmarks/074_mechanism-question.md), *Preflight findings*)

| Session | Repo | Client | Tool calls | code-atlas calls |
|---|---|---|---|---|
| 2026-08-27, benchmark cell (granted) | anchor | Aug build | 68 | 0 |
| 2026-09-19, `probe --uncoached` | this repo | 2.1.278 | 10 | 0 |
| 2026-09-19, `probe --uncoached` | anchor | 2.1.278 | 25 | 0 |

In the two 2026-09-19 sessions the transcript header records 52 resident tools of which 24 are
code-atlas, the server `connected`, `ToolSearch` resident, and `permission_denials: []`. The work was
done with `Glob` / `Grep` / `Read`. Nothing was blocked and nothing was missing; the tools were simply
not selected. The anchor session cost $1.73 and took 26 turns.

`scripts/arm_preflight.py probe --uncoached` is the instrument, and it is cheap enough to re-run after
every candidate change.

## Findings (2026-09-19 autorun)

**Named cause.** The REACH_PROMPT navigation question ("how does this codebase route an incoming
request…") matched **no occasion** in the 266 five-occasion agent brief, and the registered tool
surface did not disturb a first-move `Glob`/`Grep`/`Read` prior. `trace_capability` already answered
that shape in `which_tool`, but agents never see MCP prompts (081) and the brief never named it.
Aligning the tool docstring alone was **not** enough; appending a sixth brief occasion that maps the
routing question → `trace_capability` **was**.

**Ruled out**

| Candidate | How | Result |
|---|---|---|
| 24-tool dilution (268) | `CA_TOOLS` = FIELD18 keep-list, uncoached, both repos | still 0 atlas calls |
| Session brief presence alone (old five occasions) | `--append-system-prompt-file` with pre-300 brief | still 0 atlas calls |
| Description vocabulary alone | rewrite `trace_capability` docstring; no brief | still 0 atlas calls (A2) |

**Interactive vs headless (counts).** August interactive field round: 22/117 atlas calls (19 %) with
consumer brief present (266). Headless REACH_PROMPT with tools registered but **no matching brief
occasion**: 0 atlas calls (n = 6 cells: A/B/C × this-repo + anchor). Headless REACH_PROMPT **with**
the post-300 brief occasion: REACHABLE on both repos. So the 19 % / 0 % gap is the **harness /
session-context** variable when the brief covers the question — not MCP registration, not dilution.

### Before / after (`probe --uncoached`, client 2.1.278)

| Cell | Repo | Condition | Tool calls | code-atlas | Exit |
|---|---|---|---|---|---|
| A | this | baseline 24-tool | 12 | 0 | 2 |
| B | this | + old five-occasion brief | 8 | 0 | 2 |
| C | this | FIELD18 only | 11 | 0 | 2 |
| A | anchor | baseline 24-tool | 24 | 0 | 2 |
| B | anchor | + old five-occasion brief | 19 | 0 | 2 |
| C | anchor | FIELD18 only | 15 | 0 | 2 |
| A2 | this | docstring fix, no brief | 13 | 0 | 2 |
| B2 | this | + sixth-occasion brief | 14 | 1 | 0 |
| A2 | anchor | docstring fix, no brief | 20 | 0 | 2 |
| B2 | anchor | + sixth-occasion brief | 21 | 5 | 0 |

**074.** Blocker restated: a granted arm still requires the consumer brief (with the routing occasion)
in session context — registration alone remains insufficient. Cells that load the updated brief can
reach the index unprompted on REACH_PROMPT; bare MCP registration cannot.

## Held-out check — the effect is the question's wording, 2026-09-19 (pre-merge review)

The ablation above varies the *component* (brief, dilution, docstring) but every arm asks the same
question, and that question's sentence is the one copied into the new `which_tool` line and the
`trace_capability` docstring. So B2 cannot distinguish "the brief now covers this shape" from "the
brief now contains this string". Two mechanism questions the brief and the docstring never saw,
same anchor, same config, same post-300 brief appended:

| Cell | Question | Tool calls | code-atlas | Exit |
|---|---|---|---|---|
| control | REACH_PROMPT (held-in) | 31 | **5** | 0 |
| H2 | "Where is the decision made about which handler runs for a given URL?" | 11 | **0** | 2 |
| H1 | "A user submits a form and a record ends up saved — which code executes between those points?" | 0 | — | discarded: the session asked a clarifying question instead of tracing |

The control reproduces the reported anchor result, so the difference is not the harness. **H2 is
topically the sixth occasion** — how a request reaches its handler — and still drew 0 index calls
while producing a full grep-and-read answer. The named cause therefore does not hold as stated: it
is not "the question matched no occasion", it is "the question was not the occasion's sentence".

**Consequences.** 300 stays open. A 074 granted cell asks a *frozen* question that is not
REACH_PROMPT — exactly H2's situation — so on this evidence it would come back 0 and void at $5.58.
The AC that closes this ticket now has to be met on questions the fix never saw, at n ≥ 3, not on
the one it was written from. Also noted for 074: the control ran against `staleness: behind`, and
Scope requires `current` for a counted cell.

**Not reverted:** the sixth occasion and the docstring rewrite stay on the branch. They may well be
improvements, and pulling them would invalidate the ablation that is worth keeping. What changes is
the claim made from them.

## Why this is not the same ticket as 200 or 268
[200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md) is about whether an agent can *recognise*
which tool answers a question; [268](268_twenty-four-descriptions-are-a-tax-paid-before-the-first-question.md)
is about what 24 descriptions cost before the first question. Both were argued from prompt shape. This
ticket has an instrument and n = 3 of the end state neither predicted: full availability, zero uptake.
Its findings may well close or re-aim one of them.

## Scope / Deliverables
- **Name the cause before changing anything.** Candidate classes to separate, not a fix list:
  tool descriptions that do not match the question's vocabulary; a first-move prior toward `Grep`
  that nothing in the surface disturbs; 24 descriptions diluting each other ([268](268_twenty-four-descriptions-are-a-tax-paid-before-the-first-question.md));
  no signal that an index for *this* repo exists and is current.
- **Establish whether the harness is the variable.** Every datapoint above is a **headless one-shot**
  session. The August field round reached 22 index calls in 117 (19 %) in an *interactive* session
  with the repo's `AGENTS.md` brief present ([266](266_the-artifact-that-would-make-an-agent-ask-is-in-our-repo-not-theirs.md)).
  Measure interactive vs headless with the same question before concluding the product is at fault.
- **Whatever changes, re-run the instrument** on both repos and record the before/after counts.

## Constraints
- Nothing repo-identifying from the anchor enters this repository — counts, verdicts and question
  *shapes* only (074 C1). Transcripts stay outside the tree.
- Do not coach the probe to make the number come out (074 C4). Coaching has its own mode and it is
  not evidence of uptake.
- R4 is not at stake: this measures agent behaviour, not server determinism.

## Acceptance criteria
- A named cause, or an explicit "not identified" with the candidates that were ruled out and how.
- The interactive-vs-headless question answered with counts, so the 19 % / 0 % gap is explained or
  shown to be the harness.
- If a cause is named and fixed: `probe --uncoached` on both repos, before and after, in this file.
- 074's blocker is either lifted (the granted arm can be built) or restated in 074 with what remains.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 300 — the index is registered, permitted and never chosen (working doc)

- **Ticket:** 300
- **Type:** enhancement (adoption / measurement)
- **Repo(s) / Porting:** app (.)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 UI paths
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed · path: `docs/tasks/300_the-index-is-registered-permitted-and-never-chosen.md`

## Session status
- **status:** in-progress (autorun)
- **branch:** feat/300-index-registered-permitted-never-chosen
- **reviewer:** off · **challenger:** on

---

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
- checked existing: `docs/benchmarks/074_mechanism-question.md`, `scripts/arm_preflight.py`, `docs/tasks/074_*`, `docs/tasks/200_*`, `docs/tasks/266_*`, `docs/tasks/268_*`
- ambiguous (not blocking): "interactive session" (prose harness contrast; no single path)

`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `a-cap-at-selection-leaves-no-trace-in-the-output` | 2 | selection/uptake shape | advisory only — no requirement injected |

`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

**INPUT KIND:** ticket.

**Settled wants:** none.

**Resolved direction + citation (how-decision):**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| H1 | How to measure interactive vs headless without a human at the keyboard | Treat *session context present* as the interactive proxy: same REACH_PROMPT via `probe --uncoached`, with vs without the 266 five-occasion agent-brief appended (`claude --append-system-prompt`). Cite August interactive 19% (22/117) as the historical interactive arm; new counts from brief-on/brief-off headless explain or falsify "harness". True TTY interactive is outside `arm_preflight` (script is always `claude -p`). | `scripts/arm_preflight.py:197-207`; ticket Scope L48–51; 266 brief; `claude --append-system-prompt` |
| H2 | What counts as "uptake fixed" for AC3 | Uncoached probe exit 0 (REACHABLE: ≥1 code-atlas call). Coaching (`PROBE_PROMPT` naming `get_index_status`) is never uptake evidence (C4). | `arm_preflight.py:133-151`; ticket AC + C4 |
| H3 | If 24-tool dilution appears causal, may default CA_TOOLS change? | No in this ticket without an explicit product re-open: 268 locked default=24 and shipped FIELD18 as opt-in. Dilution evidence → record counts + point at FIELD18 / restated 074 blocker; default flip is a separate decision. | 268 Constraints L32–33; `main.py` FIELD18_TOOLS |

**ASSUMED:** none.

**Constraints from scan:** 074 C1 (no anchor-identifying content); R4 not at stake; transcripts outside tree.

**Exposure-checker:** no further WANT; H1–H3 exhaust product/intent forks that would block autorun.

---

## Requirements matrix

`SECTIONS: 6 found (Goal · The evidence · Why this is not the same ticket as 200 or 268 · Scope / Deliverables · Constraints · Acceptance criteria) | 6 decomposed | ROWS: C=3 R=3 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | Find why agent does not use index; change what is responsible | Named cause + conditional fix | ticket L11–14 | D1–D4 | AC1/AC3 | ⬜ |
| C1 | Constraints | No anchor-identifying content | Counts/verdicts/shapes only | 074 C1 | D1 | file review | ⬜ |
| C2 | Constraints | Do not coach probe for uptake evidence | Brief-append is harness contrast, not coached PROBE_PROMPT | C4 | D2 | AC2 | ⬜ |
| C3 | Constraints | R4 not at stake | No determinism claim | ticket L59 | — | N/A | ✅ |
| R1 | Scope | Name cause before changing; separate candidate classes | Descriptions / Grep-prior / dilution / no-index-signal | L44–47 | D1 | AC1 | ⬜ |
| R2 | Scope | Harness variable: interactive vs headless with counts | Brief-on vs brief-off + cite Aug 19% | L48–51 | D2 | AC2 | ⬜ |
| R3 | Scope | Re-run instrument both repos; record before/after | probe --uncoached ×2 repos | L52 | D3–D4 | AC3 | ⬜ |
| AC1 | AC | Named cause or "not identified" with ruled-out how | Record in ticket + 074 | L62 | D1 | proving | ⬜ |
| AC2 | AC | Interactive-vs-headless answered with counts | Brief contrast counts in ticket | L63–64 | D2 | proving | ⬜ |
| AC3 | AC | If fixed: before/after both repos in this file | Tables in ticket body | L65 | D3–D4 | proving | ⬜ |
| AC4 | AC | 074 blocker lifted or restated | Edit 074 working/status note | L66 | D4 | proving | ⬜ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 Q |
|-------|---------------|------------------------|--------|--------------|----------|
| AC1 | named cause or not-identified + ruled-out | same | Y | greppable named string in ticket + ruled-out table | — |
| AC2 | interactive-vs-headless with counts | H1: brief-on/off counts + Aug 19% | Y | numeric atlas-call counts in ticket | — |
| AC3 | before/after probe both repos if fixed | exit codes + atlas-call counts | Y | `probe --uncoached` exit 0/2 | — |
| AC4 | 074 lifted or restated | 074 status/blocker prose updated | Y | grep 074 for restated blocker | — |

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
- Q1→H1, Q2→H2, Q3→H3 (Phase 0 citations)

---

## Phase 1 — Analysis

- Root question: selection failure under full availability (delivery already ruled out by 074 preflight).
- depends_on: 074 deferred, 200 blocked (AC5), 266/268 done — no unmerged code required; evidence already on main.
- TRACK: backend · SCOPE: M · TIER: full

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R7.2 (change-type) ✅ TOKEN_LEDGER row · R7.6 (change-type) ✅ findings in ticket/074 prune-as-add · R4 (change-type) N/A (ticket: agent behaviour not server determinism)`

### BASELINE

```
Ran at a81ce36a2fb8c2aaae5512effe1d5fe3eeb3a4f4
$ .venv/bin/python -m pytest tests/test_arm_preflight.py -q --tb=no
13 passed in 0.02s
```

`BASELINE: green`

---

## Phase 2 — Design

**Approach.** Separate candidate classes with cheap uncoached probes before any product edit: (A) baseline 24-tool uncoached both repos; (B) same + agent-brief append (harness/context); (C) FIELD18 `CA_TOOLS` without brief (dilution). Name the cause from which contrast flips REACHABLE. Then apply the smallest fix that address that class — expected: if B flips and A/C do not, cause is "no session signal / brief absent from headless harness", fix = instrument flag for brief contrast + restate 074 that granted arm requires consumer brief in session context (266 artifact), not MCP registration alone. If C flips, record dilution evidence pointing at FIELD18 (do not flip default — H3). If none flip, "not identified" with ruled-out table.

**Rejected alternatives.**
- Rewrite all 24 tool descriptions first — violates "name cause before changing"; 266 already argued descriptions do not open a list the model never looks at.
- Change default `CA_TOOLS` to six on first green dilution probe — blocked by 268 / H3.
- Coach REACH_PROMPT to name `get_index_status` — voids uptake evidence (C2/C4).

**Assumptions.**
- `claude -p` loads no consumer AGENTS.md brief unless present/imported or appended — verified by this-repo AGENTS.md lacking `code-atlas:agent-brief` (grep empty) + `--append-system-prompt` as injection. Tag: verified (scan).
- Anchor path available for re-probe locally; only counts enter the tree — verified (074-triage granted.json). Tag: verified.
- Brief-append is a valid interactive proxy, not coaching — novel-untested about *effect*; proving test includes brief-on vs brief-off contrast that fails the harness claim if counts stay 0/0. Tag: novel-untested → Gate-2 proving covers it.

### Smallest change-list

| # | Change | File/area | Blast radius | Ph2 | k/N |
|---|--------|-----------|--------------|-----|-----|
| D1 | Run + record class-separating probes (A/B/C) both repos; transcripts outside tree | `/tmp/ca300/*` (not committed) | none in-repo | R1,AC1,AC2 | 3/11 |
| D2 | Extend `arm_preflight probe` with optional `--append-system-prompt-file` for harness contrast (does not change default uncoached behaviour) | `scripts/arm_preflight.py`, `tests/test_arm_preflight.py` | probe CLI only; coached mode untouched | R2,C2,AC2 | 3/11 |
| D3 | Record named cause + before/after counts in ticket body (above separator) | `docs/tasks/300_*.md` raw section | BACKLOG/074 readers | AC1,AC3 | 2/11 |
| D4 | Restate or lift 074 blocker from findings | `docs/tasks/074_*.md`, possibly `docs/benchmarks/074_mechanism-question.md` Preflight | 074 deferred readers | AC4,G1 | 2/11 |
| D5 | Conditional product fix only if B/C names a product gap in-repo (e.g. setup tip / runbook) — no default CA_TOOLS flip | `scripts/setup.py` tip / `docs/runbooks/onboarding-a-repo.md` if needed | install path | G1,AC3 | 1/11 |
| D6 | Bookkeeping: BACKLOG remove, TOKEN_LEDGER, status done | `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, ticket frontmatter | none | R7.2 | 1/11 |

Proof collateral: `tests/test_arm_preflight.py` argv assertions for new flag.

`HANDLES: 1 recalled | 0 traced (command + result) | 1 does not apply (reason) | 0 unanswered`
- `a-cap-at-selection-leaves-no-trace-in-the-output` — **does not apply because** this change does not add a selection-cap or truncate tool-call traces; it measures uptake and may append optional session context to the probe only.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Verification plan

| AC | Layer | How proven | ❌? |
|----|-------|------------|-----|
| AC1 | docs | Named cause / not-identified section greppable in ticket | — |
| AC2 | integration | brief-on vs brief-off atlas-call counts recorded | — |
| AC3 | integration | before/after tables both repos if fix applied | — |
| AC4 | docs | 074 blocker restated or lifted | — |
| D2 | unit | `tests/test_arm_preflight.py` covers new flag | — |

**PROVING TEST:** `.venv/bin/python -m pytest tests/test_arm_preflight.py -q`

**SCOPE:** M


---

## Phase 3 — Execute

**Branch:** feat/300-index-registered-permitted-never-chosen

**Diff ⊆ approved list:** D1 probes (outside tree) · D2 arm_preflight flag · D3 ticket findings · D4 074/protocol · D5 sixth occasion + docstring + which_tool + goldens + runbook · D6 bookkeeping.

**Verification sweep**
```
Ran at $(will fill after commit)
$ .venv/bin/python -m pytest tests/test_arm_preflight.py tests/test_agent_brief_in_indexed_repo.py tests/test_skill_drift.py -q
```

**Live probe evidence (transcripts outside tree under /tmp/ca300/):** see Findings table in raw ticket.

Design-conformance: named cause recorded; harness answered with counts; before/after both repos; 074 restated.


---

## Phase 4 — Review

`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — VERDICT CLEAN (agent 987eecf1). Isolation note: full.diff contained working-doc hunks; challenger ignored them.

Gate 4: challenger CLEAN; reviewer waived.

## Phase 5 — Finalise

Outward actions authorised: (1) push feature branch (2) open PR.
Deferred: merge, force-push, deploy, tracker transitions beyond PR create.


Reviewed at 6fa3d8f1e41e55f6fd11e1808077f039a131d823

### Learning loop

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (explore + challenger + live probes)`

Durable finding recorded in ticket Findings + 074 protocol restatement (not a separate LESSONS row this run).

