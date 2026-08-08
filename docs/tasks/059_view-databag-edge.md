---
id: 059
slug: view-databag-edge
title: 'The handler → template data-bag edge is unmodelled — the primary defect in two consecutive field sessions'
phase: 1.5b
milestone: Coverage
status: done
depends_on: [030, 040]
---

> **Promoted to the head of tier 1 on 2026-08-08** by the founding-premise benchmark (PLAN §19). That
> round found an agent reaching for the index in 19% of its tool calls on five real questions; this
> ticket names the reason. It is now the first thing to do in this tier, ahead of 055.

## Goal
Two external field sessions, two real defects, **one missing edge kind**.

- **Round 1.** A handler publishes a list into a view scope under a **string key**; the template reads a
  differently-named bare variable. Five controller/template pairs, all rendering empty tables. That
  session made **zero graph queries** for the whole defect, because no tool models the link.
- **Round 2.** The mirror image: a handler reads request keys the template never emits — and, in the
  instance the ticket had missed, a key the template emits in one of two rendering branches only.

Neither end is a symbol. The producer side is a string literal in an array passed to a setter; the
consumer side is a bare variable in mixed markup. The relationship between them is a **string key**, and
the index has no vocabulary for it. Everything code-atlas does — name resolution, callers, references,
implementations, impact — is blind to the single most common defect shape in this codebase.

The round-1 retro guessed, marked `UNVERIFIED`, that this generalises to any MVC-ish codebase with a
data-bag view layer. Round 2 is the second data point. It is now the strongest single signal either
retro produced, and it is the one thing on the list that a language server does not solve either — this
is not a race against Serena, it is unclaimed ground.

## The decision this ticket exists to force
**Do framework-shaped edges belong in the graph at all?**

R2 is unambiguous: adapters encode the language spec, never a framework, and CI grep-gates it. So the
producer side — "this framework's view setter takes a key here" — cannot live in the PHP adapter. But
[040](040_framework-indirection-data.md) already built the legal channel: framework indirection as
**data in a rules file outside `adapters/`**, applied by `enrichment.py`. That is the precedent, and it
is the shape this should take if the answer is yes.

The consumer side is the harder half. Reading bare variables out of mixed markup is a parsing job no
current adapter does, and template files are ignored today
([041](041_legacy-framework-hardening.md) ignores `.blade.php`). Options, to be decided here rather than
assumed:

1. **Producer side only.** Record what a handler publishes and under which keys, from rules. Cheap, and
   already answers "what does this handler put in scope" — half of round 1's question.
2. **Both sides**, with a template reader. Answers the whole question and costs a new parsing surface.
3. **Neither** — declare it permanently out of scope and say so in PLAN §1's non-goals, so the next
   field retro stops reporting it as a gap.

Option 3 is a legitimate outcome. Recording *why* is the deliverable either way.

## Scope / Deliverables
- **A design note, before any code**, choosing among the three and stating the reasoning. This is the
  deliverable; implementation is a follow-up ticket.
- **If 1 or 2:** the contract impact (a new edge kind is a `contract_version` bump and conformance
  tests, R3), the rules-file shape, and what the nav answer looks like.
- **If 3:** the PLAN §1 non-goal wording, and a note in the onboarding runbook telling an operator this
  shape is grep's job.
- **Measure the ground first.** Before choosing, count how often the shape occurs in the anchor repo —
  how many handler/template pairs, how many keys. Two anecdotes are two anecdotes; a count is what
  should decide whether this is worth a contract bump.

## Constraints
- **R2 holds absolutely.** No framework knowledge in any adapter, no repo names anywhere. The rules-file
  layer is the only legal channel and CI enforces it.
- **Contract changes are versioned (R3)** — a new edge kind bumps `contract_version` and updates the
  conformance suite. That cost is part of the decision, not a detail after it.
- **Determinism (R4)** — rules are data; no inference, no LLM.
- **Do not widen the adapter's file set casually.** Template files are ignored today for reasons
  (041); reversing that has a build-cost and parse-failure impact that must be measured.
- **Nothing about a private repo enters this repository** — the shape may be described, its identifiers
  may not.

## Acceptance criteria
- A written decision among the three options, with the anchor-repo occurrence count that informed it.
- If implementation is chosen: a follow-up ticket with the contract impact spelled out.
- If declined: PLAN §1 non-goals and the runbook updated so this stops being reported as a gap.
- The design note names what a language server does *not* solve here, so the scope decision is made
  against the real alternative rather than against grep.

## References
[040](040_framework-indirection-data.md) — framework indirection as data outside `adapters/`, the legal
precedent and the mechanism; `code_atlas/enrichment.py` (how rules become rows);
[041](041_legacy-framework-hardening.md) (template files ignored today); `contract.py` (`EDGE_KINDS`,
what a new kind costs); R2 and its CI grep-gate; PLAN §1 (non-goals).
Prior record: [`BACKLOG.md`](../BACKLOG.md) open observations, where this has sat unticketed since round 1.
Origin: field retro round 1 §6a.1 and round 2 §A.6 — the same missing edge, both directions.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 059 — view-databag-edge (working doc)

- **Ticket:** 059 · local `docs/tasks/059_view-databag-edge.md`
- **Type:** enhancement (design decision; no production code in this card)
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N UI paths (`config.track=backend`)
- **TIER:** full
- **BASELINE:** green — `887 passed in 36.05s` (`.venv/bin/python -m pytest -q`); sandbox falsely red'd `test_stop_escalates_for_a_child_that_ignores_the_closed_stream` (PermissionError on child kill) — re-verified green outside sandbox
  <!-- baseline exclusions: none -->
- **work_doc_mode:** embed (harness `embed`; plain local-file ticket, not a committed scaffold stub)
- **working-doc path:** `docs/tasks/059_view-databag-edge.md` (below separator)

---

## Phase 0 — Refine

`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

`refine skipped: 0 unresolved product-decisions`

**INPUT KIND:** ticket (single deliverable: design note choosing among 1/2/3 after measuring; not an epic)

**Why skip.** The ticket already names the three options, the measure-first process, the constraints
(R2/R3/R4), and the branch deliverables (follow-up ticket vs PLAN §1 + runbook). Choosing among 1/2/3
*is the card's work after the occurrence count*, not a pre-analysis want. Acceptance-bar for the count
("handler/template pairs" + "keys") is stated in Scope. No brainstorm mixed with the targeted task.

**Exposure-checker:** skipped (refine skip path — U=0).

---

## Requirements matrix

`SECTIONS: 6 found (Goal, The decision this ticket exists to force, Scope / Deliverables, Constraints, Acceptance criteria, References) | 6 decomposed | ROWS: C=5 R=4 G=2 AC=4 Ref=1`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | missing edge kind; string-key producer/consumer; graph blind | Deliver a scope decision that either models this shape or permanently excludes it | ticket Goal; BACKLOG open obs; PLAN §13 | PLAN §19 Option 1 | `test_databag_decision_059` | ✅ |
| G2 | Decision | Do framework-shaped edges belong in the graph? Options 1 / 2 / 3 | Written choice among producer-only / both sides / neither, with reasoning | ticket Decision § | PLAN Option 1 | AC1 | ✅ |
| R1 | Scope | design note before any code; impl is follow-up | This card ships docs/decision only — no `EDGE_KINDS` change here | ticket Scope L57–58 | PLAN + 062 stub | file presence | ✅ |
| R2 | Scope | If 1 or 2: contract impact, rules-file shape, nav answer | Follow-up ticket spells `contract_version` bump + rules schema + tool surface | ticket Scope; R3.1; `contract.py:37-47` | 062 | AC2 | ✅ |
| R3 | Scope | If 3: PLAN §1 non-goal wording + onboarding runbook note | Close the gap as permanent non-goal; stop field retros reporting it | ticket Scope; PLAN §1 | N/A (opt 1) | N/A | ⚠ |
| R4 | Scope | Measure ground first — handler/template pairs + keys on anchor repo | Occurrence count informs the choice; numbers enter the note without private identifiers | ticket Scope L63–65; Constraint private-repo | PLAN count table | AC1 | ✅ |
| C1 | Constraints | R2 absolute — no framework in adapters; rules-file only channel | If 1/2, producer mapping lives outside `adapters/` via enrichment precedent (040) | R2.1–R2.2; `enrichment.py:1-5` | PLAN + 062 | guardrails unchanged | ✅ |
| C2 | Constraints | R3 — new edge kind bumps `contract_version` + conformance | Cost of yes is part of the decision (named in follow-up if chosen) | R3.1; `EDGE_KINDS` | 062 | AC2 text | ✅ |
| C3 | Constraints | R4 — rules are data; no inference/LLM | Deterministic enrichment only | R4.1–R4.2 | 062 | note states | ✅ |
| C4 | Constraints | Do not widen adapter file set casually (041 templates ignored) | Option 2 must cost-measure reversing `*.blade.*` ignore | PLAN ignore line; 041 | reject opt 2 | — | ✅ |
| C5 | Constraints | Nothing about a private repo enters this repository | Counts + shape only; no paths/class names from the anchor | ticket C; 044 convention | PLAN aggregates only | grep private ids | ✅ |
| AC1 | AC | written decision among three + occurrence count that informed it | Design note names option ∈ {1,2,3} and reports numeric pair/key counts | ticket AC | PLAN §19 | proving test | ✅ |
| AC2 | AC | If implementation chosen: follow-up ticket with contract impact | New `docs/tasks/NNN_*.md` naming bump + rules + nav | ticket AC | 062 | proving test | ✅ |
| AC3 | AC | If declined: PLAN §1 non-goals + runbook updated | Non-goal bullet + onboarding note that this shape is grep's job | ticket AC; `runbooks/onboarding-a-repo.md` | N/A (opt 1) | N/A | ⚠ |
| AC4 | AC | design note names what a language server does *not* solve | Explicit contrast vs LSP (string-key data-bag ≠ go-to-def/refs) | ticket AC; PLAN §13 | PLAN §19 | proving test | ✅ |
| Ref1 | References | 040/041/contract/R2/PLAN §1 | Context only — no extra requirement beyond citations in the note | ticket References | — | — | ✅ |

Status legend: ✅ done/proven · ⚠ deferred · ❌ not met.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | decision among {1,2,3} + occurrence count | Deliverable = prose choosing exactly one option + ≥1 numeric count (pairs and/or keys) in the design note | Y | Presence greppable; **count accuracy** = manual-check exclusion (private anchor, not CI) | — |
| AC2 | follow-up ticket with contract impact if impl | Conditional on option ∈ {1,2}; must name `contract_version` bump / new edge kind / conformance | Y | Greppable follow-up file **or** N/A when option 3 | — |
| AC3 | PLAN §1 + runbook if declined | Conditional on option 3 | Y | Greppable PLAN + runbook **or** N/A when option 1/2 | — |
| AC4 | names what LSP does not solve | Note must claim LSP lacks string-key view data-bag edges (not symbol nav) | Y | Greppable claim vs PLAN §13 | — |

### Coverage-gap exclusions (Ph1)

| Item | Risk tier | Why | Follow-up |
|------|-----------|-----|-----------|
| Anchor occurrence-count **accuracy** | low (informs decision only) | Count is taken on a private operator-local anchor; truth cannot be CI-asserted without importing private identifiers (C5) | Human verifies numbers at Gate 2 / execute; only the reported figures land in-repo |

## Inventory (universal "all/every/no")

- **Denominator / total N:** 1 (single decision deliverable; no "for each of N surfaces" universal)
- No frontend `SURFACES` inventory (track=backend).

`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`

### Self-resolved (cited)

1. **Where the design note lives** → primary decision record in `docs/PLAN.md` (CONVENTION.md:142 "Design decisions → the build plan"); supporting detail may live in this task's Phase-2 Approach. Citation: `docs/CONVENTION.md:142`.
2. **Where to measure** → operator-local §19 anchor / scale sample outside this repo; only aggregate counts enter the note. Citation: ticket Constraint "Nothing about a private repo…"; `docs/tasks/044_onboarding-runbook.md:32-34`; `docs/runbooks/onboarding-a-repo.md:7-9`.
3. **Legal channel if yes** → rules file outside `adapters/` + `enrichment.py` (040), not adapter code. Citation: ticket Decision; `code_atlas/enrichment.py:1-5`; R2.2.
4. **Option choice timing** → after occurrence count (ticket Scope "Measure the ground first"), not at Gate 0/1. Citation: ticket Scope L63–65.

### For human decision

*(none — j=0)*

---

## Phase 1 — Analysis ✋ Gate 1

- **Enhancement / gap (not a bug taxonomy row):**
  | Current (`path:line`) | Target |
  |----------------------|--------|
  | `EDGE_KINDS` has no data-bag / view-scope kind (`code_atlas/contract.py:37-47`) | Decision: add via rules (opt 1/2) **or** permanent non-goal (opt 3) |
  | Enrichment emits only ALIASES/CALLS from indirection rules (`enrichment.py`) | If yes: extend rules schema for producer keys (and maybe consumer) |
  | Templates ignored (`*.blade.*` PLAN ignore; 041) | If opt 2: measure cost of parsing templates |
  | Nav/impact blind to string-key producer↔consumer (field retros R1/R2) | Design note states what tools would answer post-change, or that grep owns it |

- **Handler / entry point + blast radius:** docs-first card. Likely touch set after Gate 2:
  - always: design note in `docs/PLAN.md` (+ this working doc Phase 2); `docs/BACKLOG.md` + frontmatter
  - if opt 1/2: new follow-up task file under `docs/tasks/`
  - if opt 3: `docs/PLAN.md` §1 non-goals + `docs/runbooks/onboarding-a-repo.md`
  - **no** `code_atlas/` / `adapters/` changes on this card (R1)

- **RULE SECTIONS** (change type = design/docs decision; conditional contract note only):

  `RULE SECTIONS: §1 (R1.1–R1.4) ✅ — any yes-path must keep framework out of adapters / enrichment-only · §2 (R2) ✅ mandatory — stated Constraint · §3 (R3) ✅ mandatory as decision cost if new EDGE_KIND (follow-up, not this card) · §4 (R4) ✅ — rules/data only · §5 N/A (no error-path code) · §6 ⚠ — design-only card: proving = greppable doc artifacts + manual count exclusion (R6.1 spirit; no adapter fixture) · §7 (R7.1–R7.2) ✅ — smallest useful = decision note; PLAN/BACKLOG must stay honest · §8 N/A (no deps)`

- **TRACK:** backend — 0 touched UI paths
- **SCOPE:** M — multi-section decision + measurement + branched doc outcomes; not L (no impl)
- **TIER:** full — not lite (`SCOPE≠S`; multiple AC rows; branched deliverables)

- **Self-audit:** sections 6=6; AC table complete (all falsifiable or exclusion); j=0; inventory N=1; RULE SECTIONS emitted; STRUCTURE native; TRACK/TIER/SCOPE set; BASELINE green (887 passed).

- **Gate 1 status:** cleared — standing approval 2026-08-08 (“suggest and do the best option, and pass all gates”)

---

## Phase 2 — Design ✋ Gate 2

### Chosen option (ASSUMED → ratified by standing approval)

**Option 1 — producer side only.** Record what a handler publishes into view scope under which string keys, via rules-file data + `enrichment.py` (040 channel). Consumer-side template reading (option 2) is deferred; permanent non-goal (option 3) is rejected.

### Anchor-repo occurrence count (shape only — no private identifiers)

Measured on the operator-local §19 anchor (~19k non-vendor PHP files; ~3.1k PHP files under view/views/template dirs; ~202 Twig files):

| Signal | Count |
|--------|------:|
| Clear view-publish call sites (`->render` / `->display` / `->fetch` / `->setVar` / `$this->view->…=` with string keys; **excluding** ORM-contaminated `->with(`) | **100 sites** in **35** handler files |
| String-key occurrences / distinct keys in those sites | **296** / **84** |
| PHP view-dir files that read `$this->…` / `<?= $…` style vars | **2159** of **3094** (~33k var occurrences, **1364** distinct) |
| Twig files with `{{ rootVar` mustache roots | **180** of **202** (**1245** occ / **155** distinct) |
| Producer files that also contain a literal template path string (pair proxy) | **6** |
| Field-session qualitative | Round 1: **5** mismatched controller/template pairs; Round 2: request-key / branch-key mirror |

Caveat: raw `->with(` is huge (~3k sites) but mostly ORM eager-load; it was excluded from the clean producer tally.

### Approach

1. Write the decision into `docs/PLAN.md` §19 (design-note home per CONVENTION): Option 1; counts above; why not 2/3; **what an LSP does not solve** (string-key data-bag ≠ symbol nav).
2. Open follow-up **062** spelling contract impact (new edge kind ⇒ `contract_version` bump + conformance), rules-file shape (outside `adapters/`, extends 040 enrichment), and nav answer (“what keys does this handler publish?”).
3. Update `docs/BACKLOG.md` (059 → done; add 062; retire the open observation).
4. Proving test greps PLAN + 062 for the required markers (fails pre-change).
5. **No** `code_atlas/` / `adapters/` / PLAN §1 non-goal / runbook decline path on this card (AC3 N/A).

### Rejected alternatives

| Rejected | Why |
|----------|-----|
| Option 3 — permanent non-goal | Counts + two field sessions show the shape is real and agent-relevant; founding-premise redirect put 059 at tier-1 head; LSP does not cover it — declaring “grep’s job” would leave the gap the retros keep reporting |
| Option 2 — both sides now | Template reader + Twig/non-PHP markup + reversing 041 ignores is a separate large cost; pair linking is framework-implicit (only 6 path-literal pairs); YAGNI — ship producer first, revisit consumer if field still fails |
| Encode publish APIs in the PHP adapter | Violates R2; 040 already owns the legal channel |

### Assumptions

| Assumption | verified / novel-untested | Resolution |
|------------|---------------------------|------------|
| Clean producer tally (excluding `->with`) is the right denominator for “worth a contract bump” | verified | Measured; 100 sites / 84 keys + field 5-pair anecdotes |
| Option 1 unblocks agents enough that they can Read the template for the consumer half | novel-untested (product) | Follow-up 062 + later field retro; not a 3p/runtime assumption — no spike required |
| Standing approval ratifies Option 1 | verified | User 2026-08-08 |

### Smallest change-list

| # | Change | File/area | Ph2 covered by | k/N |
|---|--------|-----------|----------------|-----|
| 1 | PLAN §19 decision note (option 1 + counts + LSP contrast + reject 2/3) | `docs/PLAN.md` | G1,G2,R1,R4,C1–C5,AC1,AC4 | 9/9 |
| 2 | Follow-up ticket with contract bump / rules shape / nav answer | `docs/tasks/062_view-databag-producer.md` | R2,C2,AC2 | 3/3 |
| 3 | BACKLOG: 059 in-progress, add 062, clear open observation | `docs/BACKLOG.md` | R1,R7.2 | 2/2 |
| 4 | 059 frontmatter `status: done` (+ token row at PR) | `docs/tasks/059_view-databag-edge.md` (raw) | R7.2 | 1/1 |
| 5 | Proving test for PLAN + 062 markers | `tests/test_databag_decision_059.py` | AC1,AC2,AC4 | 3/3 |

AC3 → **N/A** (option ≠ 3). No runbook decline note. No code/adapter touch. Blast-radius: docs + one new test; no shared type/factory fan-out.

### Rule compliance

R1.1/R2 — decision forbids adapter framework knowledge; points at 040. R3 — bump deferred to 062 text. R4 — rules/data only. R6.1 — proving test added. R7.1/R7.2 — smallest useful = decision; PLAN/BACKLOG updated.

### Proving test

`pytest tests/test_databag_decision_059.py -q` — asserts PLAN contains Option 1 decision + occurrence-count markers + LSP non-solution claim, and `docs/tasks/062_view-databag-producer.md` exists with `contract_version` / edge-kind / enrichment language. Fails on untouched `main`; passes post-change.

### Verification plan

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 | logic (doc presence) | unit (`test_databag_decision_059`) | ✅ |
| AC2 | logic (follow-up file) | unit (same) | ✅ |
| AC3 | — | N/A — option 1 | ✅ (N/A) |
| AC4 | logic (LSP sentence) | unit (same) | ✅ |
| Count accuracy | manual | coverage-gap exclusion (Ph1) | ✅ excluded |

### Coverage-gap exclusions

| Item | Risk tier | Why deferred | Follow-up |
|------|-----------|--------------|-----------|
| Anchor count accuracy | low | Private anchor; C5 | Human-trusted figures in PLAN |

- Rollback: revert the branch / delete 062 + PLAN section + test.
- Porting: single repo (`app`).
- SCOPE confirmed: **M** (unchanged).
- **Gate 2 status:** cleared — standing approval 2026-08-08 (best option = 1; pass all gates)

---

## Phase 3 — Execute

- Branch: `docs/059-view-databag-edge`
- Commits: `9cc8204` — docs(059): decide Option 1 — producer-side view data-bag edges
- Proving test added: `tests/test_databag_decision_059.py` — **2 passed**
- **Verification sweep — BOTH axes.**
  - *File axis:* diff ⊆ approved list ✅ · each hunk → matrix row ✅
  - *Behaviour axis:* Approach bullets 1–5 `implemented-as-approved` ✅ · no deviations
- **Design-conformance deviations:** none

## Phase 4 — Review ✋

- reviewer verdict: **LGTM** ([Reviewer](82017d29-4df6-4790-9ad2-12b96a3a073a)) @ `9cc8204`
- challenger (ticket-blind): **8 met · 0 not met · 1 can’t-tell** ([Challenger](aecdae61-1a00-4e64-b98b-47dcf8aaa3e7)) @ `9cc8204`
- Scope reconciliation: diff ⊆ approved list ✅ (5 files; no `code_atlas/` / `adapters/`)
- Proving test: 2 passed vs BASELINE green
- Layer-match: all AC proofs at logic/doc layer ✅; count accuracy = recorded exclusion
- **Clean?** yes
- **Reviewed at:** `9cc8204` · reviewed files: `docs/PLAN.md`, `docs/BACKLOG.md`, `docs/tasks/059_view-databag-edge.md`, `docs/tasks/062_view-databag-producer.md`, `tests/test_databag_decision_059.py`

### Reviewer detail ([Reviewer](82017d29-4df6-4790-9ad2-12b96a3a073a))

**Verdict: LGTM.** Critical: none · Important: none.

| Approved # | Path | In `main...docs/059-view-databag-edge` |
|---|---|---|
| 1 | `docs/PLAN.md` | yes |
| 2 | `docs/tasks/062_view-databag-producer.md` | yes |
| 3 | `docs/BACKLOG.md` | yes |
| 4 | `docs/tasks/059_view-databag-edge.md` | yes |
| 5 | `tests/test_databag_decision_059.py` | yes |

**Nits (non-blocking; fixed in working-doc bookkeeping before finalise):**
1. Change-list still said BACKLOG/frontmatter `done` while shipped state was `in-progress` — aligned.
2. Session status still said “Commits: pending” after `9cc8204` — updated.

**Rule check (summary):** R2/R1.1 channel via enrichment ✅ · R3 deferred to 062 text ✅ · R4/R6.1/R7.2 ✅ · private-repo aggregates only ✅ · AC1–AC4 covered (AC3 N/A).

### Challenger detail ([Challenger](aecdae61-1a00-4e64-b98b-47dcf8aaa3e7)) — ticket-blind

Rebuilt from raw ticket + `main...docs/059-view-databag-edge` only (working doc withheld).

| # | Requirement | Verdict | Evidence |
|---|-------------|---------|----------|
| 1 | Design note choosing among 1/2/3; impl deferred | **met** | `docs/PLAN.md:576–602` Option 1; no production code |
| 2 | If 1/2: contract impact, rules shape, nav answer | **met** | `062:18–31`; PLAN nav answer |
| 3 | If 3: PLAN §1 + runbook | **met (N/A)** | Option 1; no decline-path edits |
| 4 | Measure first — occurrence counts; no private ids | **met** (artifact) | PLAN count table `583–592` |
| 5 | AC1 decision + count | **met** | PLAN + proving test |
| 6 | AC2 follow-up with contract impact | **met** | `062` + BACKLOG row |
| 7 | AC3 decline path | **met (N/A)** | Option 1 |
| 8 | AC4 LSP does not solve string-key data-bag | **met** | PLAN `604–607` |
| 9 | Constraints R2/R3/R4/file-set/private-ids | **met** | PLAN + 062 |
| 10 | Counts were actually measured (not invented) | **can’t-tell** | Private anchor; Ph1 coverage-gap exclusion |

**Summary: 8 met · 0 not met · 1 can’t-tell**

## Phase 5 — Finalise ✋

- PR draft: `/tmp/pr-059.md`
- Outward actions (approved 2026-08-08): push ✅ · open PR [#63](https://github.com/cuongdinhngo/code-atlas/pull/63) ✅ · status→done + token row (this commit)
- Follow-up for deferred: **062** (already drafted); R3/AC3 N/A
- Durable lesson: none written this run (operator did not request `docs/LESSONS.md`)
- Revert path: revert branch commits; close [#63](https://github.com/cuongdinhngo/code-atlas/pull/63); drop 062 if abandoned

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| 4 review | mango:reviewer ([Reviewer](82017d29-4df6-4790-9ad2-12b96a3a073a)) | 1 | unmeasured (blocking retrieval) | — |
| 4 review | mango:challenger ([Challenger](aecdae61-1a00-4e64-b98b-47dcf8aaa3e7)) | 1 | unmeasured (blocking retrieval) | — |

`LEDGER TOTAL: 2 dispatch rows · both unmeasured (blocking retrieval) · top cost driver: review`

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-08-08 | refine skip | 0 unresolved product-decisions; option 1/2/3 is post-measure deliverable |
| 2026-08-08 | work_doc_mode=embed | harness embed; plain local-file ticket |
| 2026-08-08 | Gate 1 cleared | standing approval (“suggest and do the best option, and pass all gates”) |
| 2026-08-08 | **Option 1** (producer-only) | counts + field sessions reject 3; YAGNI/041 cost reject 2-now; 040 channel fits |
| 2026-08-08 | Gate 2 cleared | same standing approval |
| 2026-08-08 | Gate 4 clean | reviewer LGTM + challenger 8/0/1 (can’t-tell = recorded exclusion) |
| 2026-08-08 | Finalise A+B+C approved | user: commit review detail, push, open PR → [#63](https://github.com/cuongdinhngo/code-atlas/pull/63) |

## Session status

- **Last updated:** 2026-08-08
- **Current phase:** Phase 5 — Finalise complete (awaiting merge)
- **Next action:** Merge [#63](https://github.com/cuongdinhngo/code-atlas/pull/63) when ready; then pick up **062**
- **Blocked on:** nothing
