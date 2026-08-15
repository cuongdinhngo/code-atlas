---
id: 074
slug: does-the-index-harm-mechanism-questions
title: 'The one repeated benchmark cell says the index may make control-flow answers worse — resolve it at n ≥ 3'
phase: 1.5b
milestone: Measure
status: in-progress
depends_on: [055, 067, 045]
---

## Goal
The founding-premise benchmark (PLAN §19, 2026-08-08) recorded one accidental repeat: the **mechanism
question**, run twice under the indexed arm's configuration — once with the server **denied**, once
with it **granted** — produced **opposite verdicts**. The denied run was right. It is recorded as a
threat to validity and left unresolved at n = 1. It is the only datapoint in the project suggesting the
index does not merely fail to pay for itself but **actively costs accuracy**, and it sits on the
question type the replacement claim is supposed to serve. Resolve it, and be willing to act on a bad
answer.

## Why this is not just noise
A mechanism is available, and it is already documented from a different field session.
[067](067_first-page-not-representative.md) recorded a *fully correct* `find_callers` result — 23 of
23, hand-verified — that made the session **worse**, because page 1 was 100 % of the tree the agent
must not touch and 0 % of the tree it had to change. The session "briefly read that page as *no `src/`
callers*" before `grep` contradicted it. That is the shape the hypothesis predicts: **a confident,
cheap, partial answer that terminates the reasoning which would have reached the truth.** Round 3
called that call the single question where the graph was a net loss, at roughly twice the tokens.

So there are two independent observations pointing the same way, and both are compatible with an
index that is *correct* and still harmful. A benchmark scoring precision and recall would rank them
exactly backwards — round 3's own words.

Countervailing evidence to hold at the same time: the agent reached for the index in **22 of 117 tool
calls (19 %)**. A 19 %-adoption arm losing on tokens measures **adoption**, not capability — that is
why PLAN calls fit the binding constraint. But the *wrong-cause* cell is not explained by low adoption:
being denied the tool made the answer **better**, which low adoption cannot produce.

## Scope / Deliverables
- **Re-run the mechanism question at n ≥ 3 per arm**, two arms only: server **granted** vs server
  **denied**, identical prompt, identical fresh headless session per cell, no coaching. Ground truth
  established by hand before the runs, as in the original protocol.
- **Score cause-correctness, not tokens.** Tokens are secondary here and must not decide the verdict —
  055 already established that the cost metric cannot see the worst failures.
- **Record the mechanism when the granted arm is wrong.** For each wrong answer, capture *which tool
  call preceded the wrong turn* and whether the payload was correct-but-unrepresentative (the 067
  shape), confidently empty (the [065](065_empty-answer-cannot-explain-itself.md) shape), or simply
  ignored. A verdict without a mechanism is not actionable.
- **Pre-register what each outcome causes**, before running, so the result cannot be argued after the
  fact:
  - *granted ≈ denied* → the original cell was session variance; delete the threat from §19 and stop
    spending on it.
  - *granted worse, mechanism identified* → the mechanism becomes a ticket, and the tool's description
    or ordering changes; 067 is likely already that ticket.
  - *granted worse, no mechanism* → **narrow the recommended scope in writing**: state in PLAN §19 and
    the README which question types the index is for, and which it should be kept out of. Scope
    narrowing is an acceptable, expected outcome of this ticket.
- **Extend to a second mechanism-shaped question** only if the first replicates. One question at n ≥ 3
  beats five at n = 1 — the original benchmark's chief weakness.

## Constraints
- Nothing repo-identifying from the anchor repo enters this repository. Aggregate counts, verdicts and
  question *shapes* only, as with every prior field record.
- The comparison arm is **native tools only**. A resident-LSP arm is out of scope: that server was
  uninstalled from the anchor repo on 2026-08-07, and the original run's LSP arm invoked it **zero
  times in 84 tool calls** — there is no answer-quality comparison to be had, and the project must not
  claim one.
- R4 is not at stake — this measures agent behaviour, not server determinism. Say so in the write-up so
  the variance is not mistaken for a server defect.
- Do not change any tool to make the number come out. This ticket produces a measurement and a decision;
  code changes belong to whatever ticket the mechanism names.

## Acceptance criteria
- n ≥ 3 per arm on one mechanism question, with per-run verdicts and the pre-registered consequences
  recorded before the runs.
- Each wrong granted-arm answer has a named mechanism or an explicit "not identified".
- PLAN §19's "unresolved" threat is either deleted (variance) or replaced by a scope statement naming
  the question types the index is not for.
- The README's and PLAN's value claims match the outcome, in the same change.

## Field observations (not the benchmark's arms — they do not substitute for a run)
| Round | Session shape | Mechanism shapes that arose | Verdict |
|---|---|---|---|
| Field retro 4 (2026-08-10) | review + orchestration, ~3 h | **2 of 6** — every control-flow and mechanism shape absent | No datapoint. A lead about *applicability*, not harm |
| Field retro 5 (2026-08-14) | legacy→unified **port**, ~5 h | **3 of 6** — first round to satisfy the "prefer a session with mechanism questions" rule | **n = 1: helped, narrowly** — *downgraded from "decisively" the same day; see the retraction below* |

**Retraction, from the round-5 interview (§6.5), applied here because this ticket's whole value is
that its cells are honest.** The retro claimed the graph prevented a latent fatal: a ported method had
been renamed **and recased** (`getActiveHPIOById` → `getActiveHpioById`) behind a feature flag off in
every environment smoked. **That claim is void — PHP method names are case-insensitive**, so the call
would have resolved at runtime and could never have fataled. What actually happened: the *class* was
ported under a different name and grep for the legacy class name returns **0 hits** in the unified
tree, so `search_symbol` collapsed a name-similarity hunt into one precise call. Real help, and
**no demonstrable defect prevented** — the evaluator states it cannot show that a case-insensitive
grep on the distinctive stem would have failed.

Round 5's remaining detail, because the sign is not uniform: it **lost** the one control-flow question
(front controller → `displayAction`, dynamic dispatch): 5 calls, three flavours of nothing, answered
by grep in one — and, importantly for this ticket, it produced a **wrong belief about the cause** of
the emptiness, which is mild harm of exactly the kind the benchmark's repeat suggested. Counts toward
the n as *helped narrowly, with a recorded harm*. Session type is now a named variable: this is n = 1
for **legacy→unified port**, and the original benchmark's cell was a bug hunt.
**097 does not reset this n.** That ticket changes how recognition is scored; it does not open a
new session-type counter. Round 5 remains n = 1 for legacy→unified port.

**Protocol consequence for the remaining runs.** The retraction was produced by a **second instrument
run on the same evaluator immediately after the retro** — six questions about the moments it did *not*
call the tool. A retro cannot audit itself; this pair caught a false headline within the hour. Every
remaining arm of this benchmark should carry the same interview tail, and the pair must be counted as
**one** observer, not two (the interviewee and the retro author are one context with one set of blind
spots).

## References
`docs/PLAN.md` §19 — *Founding-premise benchmark (2026-08-08)*, the "Threats, recorded rather than
hidden" paragraph (the repeat and its opposite verdicts) and the 22/117 adoption figure. Related:
[055](055_recall-benchmark.md) (why the cost metric cannot see this),
[067](067_first-page-not-representative.md) (an independent instance of correct-but-harmful),
[065](065_empty-answer-cannot-explain-itself.md) (confident emptiness as a candidate mechanism),
[045](045_tokens-to-answer-local-repo.md) (the local-tier harness).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# Working doc — 074

## Session status
- **Phase:** 1 analysis — complete; **STOPPED at Gate 1**, awaiting approval.
- **work_doc_mode:** embed (appended below the separator).
- **Kind:** measurement + decision ticket — **not a code change** (C4).
- **Split (Gate-0, maintainer-decided):** *"I prep, you run, I analyze."* This turn commits the
  pre-run package (pre-registration + protocol + rubric + capture template); the maintainer runs the
  n≥3 arms on the anchor repo; a later turn scores, applies the pre-registered outcome, edits
  PLAN §19 + README, and opens the PR.
- **Branch (planned):** `docs/074-does-the-index-harm-mechanism-questions` (measurement/docs, not `feat`).
- **STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full.

## Phase 1 — analysis

### Decompose
`SECTIONS: 6 found (Goal, Why-not-noise, Scope/Deliverables, Constraints, Acceptance criteria, References) | 6 decomposed | ROWS: G=1 R=5 C=4 AC=4 (+2 context: Why-not-noise, References)`

### Requirements matrix
| ID | Source | Verbatim (compressed) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | One accidental repeat (mechanism question, denied vs granted) gave opposite verdicts; denied was right; resolve at n≥3, act on a bad answer | Replicate the cell; decide from data | PLAN §19 threat para (551-588) | ✅ |
| R1 | Scope | Re-run mechanism question n≥3/arm, granted vs denied, identical prompt, fresh session, hand ground truth | **Maintainer runs** (anchor repo); I supply the exact protocol | needs anchor repo + headless MCP | ⏳ prep now, run pending |
| R2 | Scope | Score cause-correctness, not tokens (055: cost metric can't see worst failures) | Cause-correctness rubric; tokens recorded but non-deciding | 055 | ✅ rubric prepped |
| R3 | Scope | Record the mechanism when granted is wrong — which tool call preceded the wrong turn; 067 / 065 shape / ignored | Per-run capture template | 067, 065 | ✅ template prepped |
| R4 | Scope | Pre-register what each outcome causes, before running | The 3-outcome table, committed **before** runs | ticket §Scope | ✅ **prepped this turn** |
| R5 | Scope | Extend to a 2nd mechanism question only if the first replicates | Conditional; gated on R1 result | ticket §Scope | ✅ condition stated |
| C1 | Constraint | Nothing repo-identifying enters this repo — shapes/counts/verdicts only | Protocol names the question *shape*; maintainer uses the real question from private notes | every prior field record | ✅ |
| C2 | Constraint | Comparison arm is native tools only; no LSP arm | Two arms: granted / denied | LSP invoked 0× in 84 calls | ✅ |
| C3 | Constraint | R4 (determinism) not at stake — measures agent behaviour; say so in write-up | Write-up notes variance ≠ server defect | ticket §Constraints | ✅ noted in rubric |
| C4 | Constraint | Do not change any tool to make the number come out; measurement + decision only | No code/tool change in this ticket | — | ✅ |
| AC1 | AC | n≥3/arm, per-run verdicts + pre-registered consequences recorded **before** runs | Pre-registration committed now; verdicts filled after runs | — | ⏳ pre-reg done, verdicts pending |
| AC2 | AC | Each wrong granted answer has a named mechanism or explicit "not identified" | Capture template forces the field | — | ⏳ pending runs |
| AC3 | AC | §19 threat deleted (variance) or replaced by a scope statement | Templated both ways; applied after runs | — | ⏳ pending runs |
| AC4 | AC | README + PLAN value claims match the outcome, same change | Applied with AC3 | — | ⏳ pending runs |

### AC validation
- "n ≥ 3 per arm" — the falsifiable floor; two arms × ≥3 = **≥6 cells**. Falsifiable ✅.
- The verdicts/mechanisms (AC1 back-half, AC2) and the §19/README decision (AC3/AC4) are **contingent
  on measurement I cannot perform here** — recorded as maintainer-run, not invented. This is the
  honest reading of a benchmark ticket, not a coverage gap in code.
- No acceptance value is a vague adjective; "cause-correct" is pinned by the rubric below (a named
  ground-truth cause; the answer's stated cause matches or does not).

### Clarification
`CLARIFICATION: 1 raised | 0 self-resolved | 1 human-decided (Gate 0, resolved)`
- **Gate 0 (resolved):** the n≥3 runs need the anchor repo + headless MCP sessions — the maintainer's
  environment, not this repo. Maintainer chose *"I prep, you run, I analyze."* → this turn prepares
  the pre-run package and STOPS before the runs; no benchmark numbers are fabricated.

`j = 0` remaining → proceed (Gate 0 already cleared by the maintainer's choice).

### Measurement inventory (the cells the maintainer runs)
`ARMS: 2 (granted, denied) × n≥3 = ≥6 cells`, one mechanism question, identical prompt, fresh
headless session per cell, ground truth hand-established first. Optional R5 second question only if
the first replicates.

### Baseline
`BASELINE: green (Docker ~1065 on main) — unchanged. This ticket adds no code and no tests; the only
in-repo artifacts are docs (the pre-run package now; the §19/README decision later). C4 forbids a
code change.`

### Declarations
`STRUCTURE: native` · `TRACK: backend (docs/measurement)` · `SCOPE: M` · `TIER: full`
Branch/PR type is **`docs`**, not `feat` — no behaviour change (C4).

### Cost ledger
| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| _(none yet — no subagent dispatched)_ | | | |

## Phase 2 — design (Gate 2)

### Approach
This ticket's output is a **measurement and a decision**, not code. The design is the *protocol* that
makes the measurement honest and the decision unarguable. The maintainer runs it; I supply and commit,
**before any run**, four artifacts (below), then score and decide once the verdicts come back.

**Where it lives:** a self-contained protocol doc `docs/benchmarks/074_mechanism-question.md` (new
`docs/benchmarks/` home — this is a reusable measurement artifact the maintainer executes from and
pastes results into, cleaner than burying it in the working doc). The working doc links to it.

### Rejected alternatives
1. **Run a local toy-repo substitute for the anchor** — rejected: the phenomenon (a confident
   *partial* answer that terminates otherwise-correct reasoning) needs a real, large, ambiguous tree;
   a toy repo cannot reproduce it, so it would be measurement theater (worse than no data).
2. **Fabricate/estimate the n≥3 verdicts to "complete" the ticket now** — rejected outright: violates
   "every claim is a counted artifact" and the ticket's own "do not change any tool to make the number
   come out". A benchmark's value is that it can surprise us.
3. **Bury the pre-registration in the working doc** — rejected: it must be a clean artifact the
   maintainer runs from and that git timestamps *before* the runs; a dedicated doc is that artifact.

### Assumptions
- The maintainer can run fresh headless `claude` sessions on the anchor repo with the code-atlas MCP
  server **granted** (registered) and **denied** (absent / `CA_TOOLS=""`), no coaching — **verified**
  by the original 2026-08-08 run existing (PLAN §19).
- The original mechanism question's exact text lives in the private benchmark notes — **assumed**; the
  protocol references it by *shape* and asks the maintainer to reuse the exact original (C1: nothing
  repo-identifying enters this repo).
- No novel-untested third-party/runtime assumption in-repo (no code runs here). Gate-2 assumptions
  check clear.

### The four pre-run artifacts (committed this turn)
1. **Pre-registration (R4/AC1).** The three outcomes and their pre-committed consequences, verbatim
   from the ticket, as a table — so the result cannot be argued after the fact:
   - *granted ≈ denied* → session variance → **delete** the §19 threat; stop spending on it.
   - *granted worse, mechanism identified* → the mechanism becomes a ticket; tool description/ordering
     changes (067 likely already that ticket).
   - *granted worse, no mechanism* → **narrow the recommended scope in writing** in PLAN §19 + README
     (which question types the index is for, which to keep it out of).
2. **Protocol (R1).** Arms (granted/denied), n≥3, identical prompt, fresh session per cell,
   ground-truth-first, no coaching; native-tools-only comparison (C2, no LSP arm); the question
   *shape* (a control-flow / "how does X reach Y / what happens when Z" mechanism question) with the
   instruction to reuse the exact original from private notes.
3. **Scoring rubric (R2/C3).** Cause-correctness is the verdict: `correct | partial | wrong-cause`,
   judged against the hand-established ground-truth cause. Tokens recorded but **non-deciding** (055).
   A note that variance here is **agent behaviour, not an R4 server defect**.
4. **Mechanism-capture template (R3/AC2).** Per wrong granted-arm run: which tool call preceded the
   wrong turn; payload classification — `correct-but-unrepresentative (067)` / `confidently-empty
   (065)` / `ignored` / `other`; or an explicit **"mechanism not identified"**. Plus a results table
   skeleton (per-cell verdict) for the maintainer to paste into.

### Verification plan (per-AC, layer-matched)
| AC | risk layer | proof artifact | layer-match |
|---|---|---|---|
| AC1 (pre-reg before runs; n≥3 verdicts) | process/measurement | pre-registration committed now (git-timestamped before runs); verdicts table filled from the maintainer's runs | ✅ (pre-reg now; verdicts pending) |
| AC2 (named mechanism or "not identified") | measurement | capture template forces the field per wrong run | ⏳ pending runs |
| AC3 (delete or replace §19 threat) | documentation | both edits pre-drafted; the run outcome selects one | ⏳ pending runs |
| AC4 (README + PLAN match outcome) | documentation | applied in the same change as AC3 | ⏳ pending runs |

No layer mismatch: a measurement AC is proven by the recorded measurement, not by a unit test. There
is **no proving test** and that is correct for a benchmark ticket — the "proving" artifact is the
pre-registration + the recorded per-run verdicts. Recorded as such, not as a coverage gap.

### Rollback + porting
The pre-run package is additive docs; rollback = delete `docs/benchmarks/074_*.md`. The later
§19/README decision is a doc edit revertable by `git revert`. Single repo.

### SCOPE
`SCOPE: M` — unchanged. No tier crossing. Branch/PR type **`docs`** (C4: no behaviour change).

## Phase 3 — execute (prep portion)

Branch `docs/074-does-the-index-harm-mechanism-questions`. Wrote the pre-run package:
[`docs/benchmarks/074_mechanism-question.md`](../benchmarks/074_mechanism-question.md) — the
pre-registration (3 outcomes → consequences), protocol (2 arms × n≥3, identical prompt, fresh
session, ground-truth-first, native-only), cause-correctness rubric (tokens non-deciding; variance ≠
R4 defect), mechanism-capture template, and an empty results table for the maintainer to paste into.

### Verification sweep
- **Axis 1 (file set):** one new doc under `docs/benchmarks/` + this working doc; **no code, no
  tests** touched (C4). Diff ⊆ approved list. ✅
- **Axis 2 (design conformance):** all four pre-run artifacts present as designed; no proving test
  (correct for a benchmark). The pre-registration is committed **before** any run (git-timestamped),
  satisfying AC1's "recorded before the runs".

### Hard STOP — awaiting the maintainer's runs
Per the Gate-0 split (*"I prep, you run, I analyze"*), execute does **not** proceed to the runs, the
scoring, the §19/README decision, or the PR — those are pending real data I cannot produce here.
No benchmark numbers are invented. Committing + pushing the pre-run package now (so the
pre-registration is git-timestamped before any run); **no PR yet** — the PR is opened in the analysis
turn, once the results table is filled.

## Phase 4 — review
**Waived** by the run instruction. Nothing to review yet beyond the additive docs package.

## Phase 5 — finalise (partial — pre-registration shipped by maintainer decision)
The maintainer decided the pre-registration/protocol is a sufficient deliverable to ship now and to
stop here — the n≥3 runs are **not** performed in this cycle. So this PR ships the **prep half only**:
- **Done:** R2 (rubric), R3 (capture template), R4/AC1-front (pre-registration recorded **before** any
  run, git-timestamped). C1–C4 honoured (no code, native-only, no repo-identifying content).
- **Deferred to a follow-up** (needs the maintainer's anchor-repo runs): R1/R5 (the runs),
  AC1-back (n≥3 per-run verdicts), AC2 (mechanism per wrong cell), AC3/AC4 (delete-or-replace the
  §19 threat + sync README). PLAN §19's threat paragraph is therefore **left as-is** — deliberately,
  since resolving it requires the data this PR does not fabricate.
The PR is framed as a pre-registered protocol, not a resolved measurement. No benchmark numbers invented.

## Session status
- **Phase:** finalise — **pre-registration shipped (PR #93)**; runs + §19/README decision **deferred**
  (maintainer chose to stop after prep).
- **Ticket state:** `in-progress` — the measurement ACs (AC1-back/AC2/AC3/AC4) remain open for a
  future cycle when the anchor-repo runs are done; the pre-registration is banked and git-timestamped.
- **To resume:** run ≥6 cells (2 arms × n≥3) on the anchor repo per
  `docs/benchmarks/074_mechanism-question.md`, fill its results table, then score → apply the selected
  pre-registered outcome to PLAN §19 + README → decide R5.
- **Revert:** revert the PR / delete `docs/benchmarks/074_mechanism-question.md` + the branch.

### Cost ledger
| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| _(none — no subagent dispatched this run)_ | — | — | — |

`LEDGER TOTAL: 0 · no subagent dispatched.` All work on the main model (not measured by mango).

### Cost ledger
| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| _(none — no subagent dispatched this run)_ | — | — | — |

`LEDGER TOTAL: 0 · no subagent dispatched.` All work ran on the main model (not measured by mango).
