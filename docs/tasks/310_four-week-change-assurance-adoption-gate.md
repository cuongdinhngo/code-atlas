---
id: 310
slug: four-week-change-assurance-adoption-gate
title: "Capabilities do not make a must-have product — measure whether teams repeatedly use Change Assurance and miss it when removed"
phase: 3
milestone: Change-Assurance
status: blocked
depends_on: [260, 300, 305, 306, 307, 309]
---

## Parent epic

[304 — Change Assurance](304_change-assurance-makes-every-important-change-carry-evidence.md).

## Goal

Decide whether Change Assurance changed real review behaviour. The answer may be “useful, not
must-have”; shipping capabilities does not pre-decide the verdict.

## Pre-registered success bar

For teams using AI on large repositories, during one four-week field window:

- at least **80% of code-changing PRs** run Change Assurance; and
- at least **50% of reviews** use at least one emitted evidence item.

Both must pass. A denominator, exclusion or evidence-use classification is defined before collection.

## Scope / Deliverables

1. A field protocol defining cohort, repository-size floor, code-changing PR, assurance run,
   evidence-used-in-review, exclusions and privacy boundaries.
2. Local-only counting or a committed tally template; no telemetry or network collection.
3. Per-week and aggregate denominators/numerators with server build, config build and repository
   revision provenance.
4. Short interviews at the end of the window: which decision changed, which evidence was ignored,
   and what users did when assurance was deliberately unavailable for a controlled comparison.
5. Apply one predeclared verdict: must-have observed, useful but optional, adoption failure, or
   measurement invalid.

## Constraints

- No repository names, source, qnames or paths enter the committed result; counts and question
  shapes only.
- A tool invocation is not automatically evidence use. The review artifact must contain or cite an
  emitted claim, finding or bundle section.
- A failed/invalid assurance run remains in the run-rate denominator and is classified; deleting it
  would reward unreliability.
- The protocol measures workflow behaviour, not server determinism, and does not coach sessions to
  call the tool.

## Acceptance criteria

- Cohort and every numerator/denominator rule are frozen before week one.
- Four weekly records reconcile exactly to the aggregate and name host/client/server/config builds.
- The verify-use rate and review-evidence rate are both reported against their separate denominators.
- At least one removal-cost comparison or interview tests whether users notice the capability's
  absence rather than merely approving it in principle.
- The final verdict mechanically follows the two thresholds and validity rules.
- Negative or invalid results update the epic status honestly; they do not trigger wording changes
  that redefine success after measurement.

## Out of scope

- Product changes during the counted window, paid telemetry, provider analytics or a claim that one
  team generalises to every repository.

## References

[260](260_the-fit-number-cannot-be-observed-only-benchmarked.md),
[300](300_the-index-is-registered-permitted-and-never-chosen.md),
[304](304_change-assurance-makes-every-important-change-carry-evidence.md),
`docs/runbooks/field-retro.md`, `docs/runbooks/tool-recognition-probe.md`,
ENGINEERING_RULES R4, R5.5, R5.6 and R6.3.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 310 — Four-week adoption gate (working doc)
- **TIER:** full · **TRACK:** backend · **SCOPE:** M · **BASELINE:** green
- **Depends on:** 260, 300, 305, 306, 307, 309 — all `done`.
- **reviewer:** off · **challenger:** on
- **Branch:** `feat/310-four-week-change-assurance-adoption-gate`

## Session status
- **Current phase:** finalise. **Ticket ships `blocked`, not `done`.**

## Phase 0
`PREMISE: 7 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`
**INPUT KIND:** ticket.

The one unresolved item was **not** a want-decision, so it did not stop the run: *does a four-week
cohort exist to measure?* The repo answers it. [300](300_the-index-is-registered-permitted-and-never-chosen.md)
closed 2026-09-19 with **full availability, zero uptake** at n = 3 and named the residual cause —
the client's deferred delivery and whether `Grep` hurts — as *not this repo's to change*; AGENTS.md
declares a single-maintainer repo. No cohort exists.

The **how-decision**, resolved and cited: ship the half that must be frozen *before* week one and
leave the ticket open on the half that needs a window. Precedent is
[200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md), which ships its mechanism and stays
`blocked` on its field AC alone rather than closing on what it could reach.

| # | Claim (id) | Type | Matched by | Relevant? |
|---|------------|------|------------|-----------|
| 1 | `delegation-is-not-ratification` | 2 | handle | yes — the bar must be frozen before the count |
| 2 | `ac-failure-mode-needs-the-right-guard` → R6.5 | 2 | handle | yes — the template is the observed failing case |
| 3 | `guard-asserts-rendered-not-shipped-bytes` → R6.9 | 2 | handle | yes — text/JSON asserted, not the field |

`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis
`SECTIONS: 6 found (Goal · Pre-registered success bar · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 6 decomposed | ROWS: C=4 R=5 G=1 AC=6`
`RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — R4.2 (change-type) ✅ · R5.5 (change-type) ✅ · R5.6 (change-type) ✅ · R6.5 (recalled handle) ✅ · R7.2 (change-type) ✅ · R7.6 (change-type) ✅`
`BASELINE: green`

Gap: the ticket's deliverables split on whether they need field data. 1–3 (protocol, tally template,
per-week/aggregate counting with provenance) are **pre-window artifacts and AC1 demands they be
frozen before week one**. 4–5 (interviews, applied verdict) and ACs 2/3/4/6 need a cohort that does
not exist.

| ID | Source | Verbatim (abbrev) | Interpretation | Ph1 evidence | Ph3 | Status |
|----|--------|-------------------|----------------|--------------|-----|--------|
| C1 | Constraint | no repo names, source, qnames or paths | privacy guard rejects them | ticket | V7 + test | ✅ |
| C2 | Constraint | a tool invocation is not evidence use | separate numerator | ticket | protocol §2 | ✅ |
| C3 | Constraint | failed/invalid run stays in the denominator | attempt is the numerator | ticket | §3 + test | ✅ |
| C4 | Constraint | measures workflow, not server determinism | no coaching, no product change | ticket | §1, §7 | ✅ |
| R1 | Scope | field protocol with every definition | frozen runbook | — | protocol §§1–9 | ✅ |
| R2 | Scope | local-only counting or tally template | committed template + script | — | template + script | ✅ |
| R3 | Scope | per-week and aggregate with provenance | reconciliation + 5 build fields | — | V2, V6 | ✅ |
| R4 | Scope | end-of-window interviews | needs a cohort | — | — | ❌ no cohort |
| R5 | Scope | apply one predeclared verdict | mechanism shipped, unapplied | — | §8 + test | ⚠️ mechanism only |
| G1 | Goal | decide whether review behaviour changed | the verdict | — | — | ❌ no cohort |
| AC1 | AC | cohort and every rule frozen before week one | protocol committed | — | protocol | ✅ |
| AC2 | AC | four weekly records reconcile exactly | rule shipped, no records | — | V2 + test | ❌ no data |
| AC3 | AC | both rates on separate denominators | rule shipped, no records | — | §2 + test | ❌ no data |
| AC4 | AC | a removal-cost comparison or interview | V5 makes its absence invalid | — | V5 + test | ❌ no data |
| AC5 | AC | verdict mechanically follows thresholds | pure function, tested | — | §8 + test | ✅ |
| AC6 | AC | negative/invalid results update the epic honestly | 304 + BACKLOG say blocked | — | 304, BACKLOG | ✅ |

## Phase 2 — Design
**Approach:** freeze the instrument, run nothing. `docs/runbooks/change-assurance-field-protocol.md`
fixes cohort, the two denominators, exclusions, privacy, provenance, removal cost and the verdict
table. `scripts/change_assurance_tally.py` is a pure function from one committed JSON record to
`{run_rate, evidence_rate, validity_failures, verdict}` — validity is decided **before** any rate is
read, so a record that cannot support a verdict returns `measurement_invalid` rather than a number
with a caveat (R5.6). The committed template is deliberately empty and therefore **evaluates to
`measurement_invalid`**: the shipped guard is observed failing rather than asserted (R6.5).

**Rejected alternatives:** (a) marking 310 `done` on the protocol alone — the ticket's Goal is the
verdict, and closing on the instrument would be the 309 failure mode with a different mask;
(b) simulating a cohort to exercise ACs 2–4 — manufactured field data is worse than a recorded gap;
(c) lowering the 80/50 bars to something a single maintainer could clear — reopening a
pre-registered bar after seeing who is available to measure.

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
- `delegation-is-not-ratification` → the bar is the ticket's, quoted not re-derived; the protocol is
  frozen before any cohort exists, which is the strongest form of blind.
- `ac-failure-mode-needs-the-right-guard` → the committed template runs to `measurement_invalid`.
- `guard-asserts-rendered-not-shipped-bytes` → tests assert `render_text` / `render_json` output.

`EXCLUSIONS: 4 recorded | 4 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 4 input-shape-dependent AC(s) | 0 proven on a real corpus`

The four are ACs 2, 3, 4 and G1/R4. **Expiry, checkable:** a cohort meeting protocol §1 exists — one
team, ≥ 2,000 indexed files, availability for four consecutive weeks. Until then each is **unmet and
recorded unmet**, never narrated closed. They were **not** pre-approved by the maintainer; that is in
DISCLOSURE.

**APPROVED CHANGE LIST:**
1. `docs/runbooks/change-assurance-field-protocol.md` — the frozen protocol
2. `docs/runbooks/change-assurance-tally.template.json` — the committed record shape
3. `scripts/change_assurance_tally.py` — validity rules, two rates, mechanical verdict
4. `tests/test_change_assurance_tally.py` — proving fixtures
5. working doc / ticket frontmatter / BACKLOG / 304 / TOKEN_LEDGER

**PROVING TEST:** `.venv/bin/python -m pytest tests/test_change_assurance_tally.py -q`

## Phase 3 — Execute
Implemented the approved list. Proving test → 21 passed. Full suite → **4,369 passed / 4 skipped**
on Linux with php · composer · node present (the four green skips AGENTS.md documents).
`ruff check .` clean. No file under `code_atlas/` or `adapters/` was touched, so the R1.1 / R2.2 /
R4.1 sweeps are unaffected by construction.

**No field data was produced, and none was simulated.** The tally reports
`measurement_invalid` on the only record this repo can honestly commit.

## Phase 4 — Review
`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — round1 **NOT CLEAN**, two demonstrated defects, both fixed; round2 not re-dispatched (see DISCLOSURE).

The challenger disclosed a **partial independence compromise it could not avoid**: `work_doc_mode`
is `embed`, so `git diff` on the ticket file hands over this working doc. It states it built its
requirement list from the raw ticket and the shipped artifacts instead, and it disagreed with one of
our own gradings — which is not what a captured reviewer does. Recorded as a signal, not waved away.

| # | Finding | Verdict | Fix |
|---|---------|---------|-----|
| 1 | The privacy guard had real false negatives. Dotted qnames (`code_atlas.core.store.Store`, `com.example.service.UserService`) and bare repo/team names (`acme-webapp`, `billing-service`, `UserController`) were **not** caught — proven by running the shipped regexes. | upheld | Reproduced all five, then replaced the sniffer with a **closed vocabulary**: no free text is admitted at all, so no name can ride in on one. Widening the regex was rejected — no pattern separates the repo name `billing-service` from the words it is made of. The five strings are now parametrised cases. |
| 2 | `_validity_failures` re-derived `weeks` from the raw record, so a `null` entry inside a four-length list crashed with `AttributeError` instead of degrading to `measurement_invalid`. | upheld | `evaluate` now passes its dict-filtered list, and a non-dict entry is itself a V1 failure. |
| 3 | The protocol's Status line self-graded **AC6 unmet** while the working-doc table graded it met. AC6 asks that a negative result update the epic honestly without moving a threshold — which the diff does. | upheld (we under-claimed) | Status now reads "ACs 2, 3 and 4 and the Goal", and names AC1/AC5/AC6 met. |

Not upheld: nothing. The challenger found no redefinition of success, no moved threshold, no
false-pass path in the verdict function, and no scope creep.

**Round 2, self-found — the first fix did not go far enough.** Checking the PR's own claim that the
record "admits no free text at all" showed it did not: the template carried a top-level `note`, and
`"acme-webapp rollout, billing-service excluded"` passed every check. The same defect class the
challenger reported, surviving in the field its fix had not closed — a closed vocabulary is worth
nothing while any new key may carry free text beside it. A string is now admissible in exactly five
named slots and nowhere else; the template's commentary moved into the protocol.

## Phase 5 — Finalise
`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=0 T3=1 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen >= 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/SKILL_GAP_CANDIDATES.md | mango files written: 0`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: 87,102 fresh (1 dispatch) · top cost driver: main-loop (unmeasured)`

The one claim this run surfaced is **type 3, not type 2**: `embed-mode-leaks-the-working-doc-into-the-diff`
is a mango-level gap already carried in `SKILL_GAP_CANDIDATES.md` with sightings 197 and 199. This is
its **third**, appended to the existing entry rather than re-filed (R7.6). This repo never edits a
skill, so there is nothing to promote — the destination is the signal file, and it is already there.

