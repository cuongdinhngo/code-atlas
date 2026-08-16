---
id: 100
slug: claim-signing-output-mode
title: 'The agent pasted nine kinds of evidence into its PR and zero graph payloads — while holding the strongest one'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [017, 057, 061]
---

## Goal
The field session's PR body pastes **nine** kinds of counted evidence: an HTTP status, two byte
counts, a header count, a row count, two verbatim JavaScript `alert()` strings, a test count, an
assertion count. It contains **zero** code-atlas output — although the session had already run
`impact` over the four changed paths and received
`seeds_dropped: 0, frontier_skipped_non_resolved: 0`, 25 rows all `confidence_tier: "RESOLVED"`.

The claim that went into the PR instead was prose: *"No product code, no `src/` consumer."* A reader
cannot check it. The payload that could have signed it was already on screen and was discarded.

The evaluator's own reading, offered against its own interest: *"my behaviour treated the browser as
an evidence source and code-atlas as a search layer — which is, verbatim, the decision this file
feeds."* And its diagnosis: *"the gap between 'the tool knows' and 'the reviewer can check' was, in
this session, entirely me — and that is a product problem, not a discipline problem, because I pasted
every other tool's evidence unprompted."*

That is the argument for this ticket. Every other tool in that session shipped output the agent could
quote. code-atlas ships JSON that answers a question and reads like an internal payload, so it stops
at the agent.

## Why this is the strategic ticket, not a formatting nicety
code-atlas cannot win the "find the code" race — that premise was refuted in §19 (2026-08-08), and
grep on the anchor tree measures 0.07–8.7 s at every scope. What survives is the class of claim a
text search **cannot make**: a *modelled zero*, a *second independent count*, and *identity across a
rename*. Those are not search results — they are **attestations**. An attestation that never reaches
the artifact where the claim is made has, for practical purposes, not been produced.

The consumer already exists in this project's own workflow: a gated lifecycle in which *every claim is
a counted artifact* and a PR template that must be filled with evidence. code-atlas is the natural
producer for the rows about code relationships, and today it produces none of them in quotable form.

## Generality — why this one survives the "n = 1, one repo" filter
Nothing here is a property of the anchor repository. Every project that reviews code has an artifact
where claims are made — a PR body, a review comment, a commit message, a changelog — and in every one
of them *"nothing depends on this"* is a claim a reader cannot check. The behaviour observed is the
agent's, not the repo's: it quoted every tool that produced quotable output and paraphrased the one
that did not. That is a property of the payload format, which every user of this server receives.

The counter-hypothesis worth naming: perhaps agents simply do not paste MCP output, and a quotable
line would go unused. The next field round settles it at no cost — ship the line and look at whether
it appears in the artifact.

## Scope / Deliverables
- **A quotable line per answer**, opt-in, carrying the four things a reader needs to re-run it:
  **subject · question · answer · revision**. The revision half is already available
  ([077](077_index-cannot-name-the-revision-it-describes.md): `last_ref`/`head_ref`;
  [071](071_answers-do-not-name-their-tree.md): `index_root`) and is what makes the line checkable
  rather than decorative.
- **Decide the surface**: a `detail_level` value, a per-call flag, or a separate rendering of the
  same payload. Weigh against [061](061_payload-weight.md) — the default answer must not grow.
- **Start with the tools whose answers are attestations, not lists:** `impact` (a modelled zero,
  with `seeds_dropped` / `frontier_skipped_non_resolved`), `find_callers` / `find_references`
  (a counted set at a named tier), `get_index_status` (what revision the answer describes). A list of
  rows is not a claim and does not need signing.
- **The line must degrade honestly.** A signed line for an answer whose tier is `HEURISTIC`, or whose
  index is `behind`, must say so *in the line* — a quotable artifact that hides its own weakness is
  worse than no artifact. This is the same rule 067 and 073 established for the payload.
- **A worked example in the docs**: the exact line the field session should have pasted for
  *"nothing in `src/` depends on these four new paths"*, next to the prose it actually shipped.
- **Do not build a report generator.** One line per answer, quotable by a human or an agent. Anything
  larger belongs to Phase 3.

## Constraints
- **R4** — the line is a rendering of the payload the tool already computed; identical input, identical
  line. No new computation, no LLM phrasing.
- **R3** — if the line becomes part of the tool contract, the conformance suite must pin it.
- **061** — off by default, or free. Measure the token delta.
- **R1.1** — no language branch; the line's vocabulary is the contract's, not PHP's.
- Honesty over quotability: if an answer cannot be stated in one line without losing a caveat, it does
  not get a line. Record which answers those are — that list is itself a finding.

## Acceptance criteria
- `impact`'s modelled zero renders a one-line attestation naming subject, question, answer, and the
  revision it describes; pinned by a test.
- An answer over a `behind` index, or one whose hits are non-`RESOLVED`, renders a line that says so;
  pinned by a test.
- Default payloads are byte-identical to today (R4), with the token delta of the opt-in measured and
  recorded.
- The docs show the field session's real claim beside the line that would have signed it.
- A recorded list of answers deliberately left unsigned, with the caveat each would have lost.

## References
Field interview (round-5 companion, 2026-08-14) §2 (the four claims and the "zero graph payloads"
finding), §7.4 (*"the sharpest question in the instrument … it deserves to be its own section"*),
§8.1 ("reaching the shipped artifact — 10 %"), §8.4 item 6, §8.5. `docs/PLAN.md` §19 —
*Founding-premise benchmark (2026-08-08)*, "what survives is relationships, not locations".
Related: [017](017_impact-engine.md) (the attestation that already exists),
[077](077_index-cannot-name-the-revision-it-describes.md) and
[071](071_answers-do-not-name-their-tree.md) (what makes a line checkable),
[057](057_answer-pagination.md) and [067](067_first-page-not-representative.md) (a count that can be
audited), [061](061_payload-weight.md).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Phase:** 5 — Finalise (final gate); Gates 1–2 and 4 cleared 2026-08-16
- **KEY:** 100 · **branch:** `feat/100-claim-signing-output-mode`
- **STRUCTURE:** native
- **TRACK:** backend — 0/14 touched files under UI paths
- **SCOPE:** M
- **TIER:** full
- **work_doc_mode:** embed (plain local-file ticket, hand-authored — not a scaffold stub)
- **BASELINE:** green
- **Challenger:** WAIVED by operator instruction (2026-08-16). Reviewer agent still runs.
- **Autonomous-run envelope:** `RUN CONTRACT` at `~/.mango/runs/code-atlas/100/RUN_CONTRACT.txt`
  (mini-spec A1) — ceiling `PR`, precedent found, 5 termination conditions, 2 UNBOUND until Gate 2.

**BASELINE artifact.** `scripts/docker-test.sh` on `main` @ `7177b43` — **1222 passed in 74.12s**,
exit 0 (ruff · mypy · pytest). 0 baseline exclusions.

---

## Phase 0 — Refine

`PREMISE: 19 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 8 claim(s) surfaced | 0 by symbol | 4 by handle | 4 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 4 unresolved surfaced | 1 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise check.** Every source ticket 100 cites as already existing resolves. Payload/tool
references: `impact` (`tools/impact.py`), `seeds_dropped` + `frontier_skipped_non_resolved`
(`impact.py:62-63`), `confidence_tier` / `RESOLVED` (`contract.py` `CONFIDENCE_TIERS`),
`find_callers`, `find_references`, `get_index_status`, `detail_level` (`impact.py:14`),
`index_root` (`nav_result.py:178`), `last_ref` / `head_ref` (`staleness.py:51,77`). Tickets
017, 057, 061, 067, 071, 073, 077 all present under `docs/tasks/`. `docs/PLAN.md` §19
*Founding-premise benchmark* present. **Ambiguous (1, non-blocking):** "Field interview (round-5
companion, 2026-08-14)" is an external document, not a repo path — prose reference, never a
falsified premise. **PREMISE HOLDS.**

**Recalled claims (advisory — injected nothing, blocked nothing).**
By handle (4), matched on the *shape* of the change (a new core module other modules import, plus a
shared payload vocabulary): `try-instead-tool-name` (093-C1 → R5.4), `derived-not-listed-invariant`
(093-C2 / 095-C1 / 097-C1 → R6.7), `prove-the-guard-fails` (093-C3 → R6.5), `route-must-answer`
(093-C4 — no rulebook destination, so it adds no applicable section).
By area (4): `099-C1` *channel-cannot-carry-unasked-information* (agent-fit / product position — this
ticket is the payload-side twin of that finding), `097-C2` (routing surface / recognition — a
description cannot make the agent notice; nor can a payload field), `040-C1` (docs inventory lags a
new core module), `038-C1` (store/tools payload shaping, R3.2).
Does not apply: `scope-by-key-not-by-file`, `pin-the-table-a-purity-claim-rests-on`,
`late-writer-outside-the-delta`, `invert-the-rewrite-the-lookup-applies`,
`skip-dynamic-means-unlinkable` (resolver/indexer internals); `structural-silence-over-stateful-latch`,
`hook-event-is-part-of-the-contract` (hooks); `sibling-meta-non-int` (store/census).

**WANT-decision asked and ratified (1).**
**W1 — the line's text form.** Answer: **`key=value` record**, one line, machine-parsable and
human-readable, one key per caveat. Rationale given by the human: a caveat that is its own key
cannot be dropped silently when the answer degrades (AC2), which prose form allows.

**HOW-decisions (resolved + cited, 0 handed back, 0 ASSUMED).**
1. **The surface is a per-call opt-in flag on the attesting tools — not a `detail_level` value, not a
   separate rendering.** Cited: AC3 (*default payloads byte-identical*) + Constraint 061 (*off by
   default*) force opt-in; `detail_level` is a **global verbosity axis** that is currently **inert on
   nav payloads** — `del detail_level` at `nav_result.py:171` (`nav_result`), `:141` (`empty_nav`),
   `:200` (`list_result`) — so a third enum value would wire verbosity to perform attestation and
   would widen the `Literal` on every tool including the ones Scope says must stay unsigned; and
   Scope bullet 6 (*"Do not build a report generator"*) excludes a separate rendering pass.
2. **Which tools sign.** Cited Scope bullet 3: `impact`, `find_callers`, `find_references`,
   `get_index_status`. Excluded, per *"a list of rows is not a claim"*: `search_symbol`,
   `file_outline`, `find_orphans`, `include_graph`, `find_implementations`, `find_view_data`,
   `read_symbol`, `explain_path`, `reachable_from`. That exclusion list is AC5's deliverable.
3. **The revision half comes from the existing staleness source.** Cited: `compute_staleness()`
   (`staleness.py:63`) already returns `last_commit` / `head_commit` / `head_ref` / `staleness`, with
   `last_ref` omitted-not-null pre-077 (`staleness.py:51`). Nav payloads today carry only
   `index_root` (`nav_result.py:178`), so a signed call costs **one extra git HEAD read** — that read
   is the 061 delta AC3 must measure.

---

## Phase 1 — Analysis

### Requirements matrix

`SECTIONS: 7 found (Goal, Why this is the strategic ticket, Generality, Scope / Deliverables, Constraints, Acceptance criteria, References) | 7 decomposed | ROWS: C=5 R=6 G=3 AC=5`

| ID | Source | Verbatim (abbrev.) | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|--------------------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | nine kinds of counted evidence in the PR, **zero** code-atlas output, while holding `seeds_dropped: 0` and 25 `RESOLVED` rows | The answer never reached the artifact where the claim was made | ticket ¶1; `impact.py:62-63` | CL1, CL9 | README worked example beside the prose that shipped; AC4 test | ✅ |
| G2 | Why strategic | what survives is the class of claim a text search **cannot** make — a modelled zero, a second count, identity across a rename: **attestations** | Sign attestations, not searches | PLAN §19; `impact.py:34-35` (065 modelled zero) | CL1, CL10 | PLAN §12 *Claim signing* section | ✅ |
| G3 | Generality | nothing here is a property of the anchor repo; the behaviour is the agent's, not the repo's | R2 standard-over-sample: no repo names in the line | R2.2 | CL1 | R1.1/R2.2 grep clean on `claim.py`; CI gate green | ✅ |
| R1 | Scope | a quotable line per answer, **opt-in**, carrying subject · question · answer · revision | 4 named components, all four present or the line is not emitted | 077/071 supply the revision half | CL1 | `test_impact_modelled_zero_...` asserts all four components | ✅ |
| R2 | Scope | **decide the surface** — `detail_level` value, per-call flag, or separate rendering; weigh against 061 | Per-call flag (HOW-1, cited) | `nav_result.py:171,141,200` | CL1–CL5 | `test_sign_is_published_on_exactly_the_attesting_tools` | ✅ |
| R3 | Scope | start with tools whose answers are **attestations, not lists** | `impact`, `find_callers`, `find_references`, `get_index_status` | Scope bullet 3 | CL2–CL5 | same test — signers == 4, denominator derived from `TOOL_NAMES` | ✅ |
| R4 | Scope | the line must **degrade honestly** — `HEURISTIC` tier or a `behind` index must say so **in the line** | Caveats are their own keys (W1) | `staleness.py:37-45`; R5.2 | CL1 | `test_a_behind_index_says_so_in_the_line`, `test_a_heuristic_hit_is_never_claimed_resolved`, `test_find_references_carries_the_authoritative_caveat` | ✅ |
| R5 | Scope | a worked example in the docs — the exact line the field session should have pasted, next to the prose it shipped | Both strings present in one doc | ticket ¶*"No product code, no `src/` consumer."* | CL9 | `test_the_docs_show_the_field_claim_beside_the_line_that_would_have_signed_it` | ✅ |
| R6 | Scope | **do not build a report generator**; one line per answer | No new tool, no aggregation | R7.1 / R7.4 | CL1 | no new tool — `set(published) == set(TOOL_NAMES)` still holds (14) | ✅ |
| C1 | Constraints | **R4** — a rendering of the payload already computed; identical input → identical line; no new computation, no LLM phrasing | Pure function of the payload + staleness read | R4.1 / R4.2 | CL1 | `claim.py` imports no store and no git; full gate green | ✅ |
| C2 | Constraints | **R3** — if the line becomes part of the tool contract, the conformance suite must pin it | Tool-payload key ≠ adapter contract (see CLR-2) | `tests/contract/` is adapter-only | CL6 | pinned in `tests/`, not `tests/contract/`; `CONTRACT_VERSION` unchanged at 5 | ✅ |
| C3 | Constraints | **061** — off by default, or free. Measure the token delta | Default byte-identical; delta measured with `tokens.estimate_tokens` | `code_atlas/tokens.py` | CL6 | `test_the_opt_in_costs_one_line` — measured +51 (`impact`) / +46 (`find_callers`) | ✅ |
| C4 | Constraints | **R1.1** — no language branch; the line's vocabulary is the contract's, not PHP's | No suffix/language key anywhere in the renderer | R1.1 grep-gate | CL1 | grep-gate clean; `mypy` over 41 source files | ✅ |
| C5 | Constraints | honesty over quotability — an answer that cannot be stated in one line without losing a caveat gets **no line**; record which | The AC5 list is a *finding*, not paperwork | ticket Constraint 5 | CL1, CL9 | `test_impact_refuses_to_sign_an_answer_whose_subject_never_resolved` + the README exclusion table | ✅ |
| AC1 | AC | `impact`'s **modelled zero** renders a one-line attestation naming subject, question, answer, revision; **pinned by a test** | Test asserts all four components on an empty `impact` answer | `impact.py:34-35` | CL1, CL2, CL6 | `test_impact_modelled_zero_is_signed_with_subject_question_answer_and_revision` ✅ | ✅ |
| AC2 | AC | an answer over a `behind` index, or whose hits are non-`RESOLVED`, renders a line that **says so**; pinned by a test | Two negative-ish tests, each made to fire (R6.5) | `staleness.py:37-45` | CL1, CL6 | 3 degradation tests, each with a positive control ✅ | ✅ |
| AC3 | AC | default payloads **byte-identical** to today (R4), with the token delta of the opt-in **measured and recorded** | Byte-identity test + a recorded number | `tests/test_payload_weight.py`; `tokens.py` | CL1, CL6 | `test_the_default_payload_is_byte_identical_and_carries_no_claim` + the delta test ✅ | ✅ |
| AC4 | AC | the docs show the field session's real claim **beside** the line that would have signed it | Both strings greppable in one doc | ticket ¶1 | CL9, CL6 | `test_the_docs_show_the_field_claim_beside_the_line_that_would_have_signed_it` ✅ | ✅ |
| AC5 | AC | a recorded list of answers **deliberately left unsigned**, with the caveat each would have lost | ≥1 entry per excluded tool, each naming its caveat | HOW-2 exclusion list | CL9, CL6 | `test_every_unsigned_tool_is_recorded_with_the_caveat_it_would_have_lost` (10 rows) ✅ | ✅ |

**AC falsifiability.** All 5 acceptance values are falsifiable in-session (each is a test assertion
or a greppable document string). **0 manual-check exclusions recorded**, so no AC may carry a bare
`✅`.

### Clarifications

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

- **CLR-1 — does AC1's "modelled zero" mean an *empty* `impact` answer, or any `impact` answer?**
  Self-resolved: `impact.py:34-35` — *"an empty answer is a modelled zero for those kinds"* (task
  065). AC1's pinned test is therefore the **empty** case specifically; signing applies to every
  `impact` answer, and AC4's worked example is the non-empty 25-row case.
- **CLR-2 — does a new payload key require a `contract_version` bump (R3.1)?**
  Self-resolved: **no.** R3.1 covers node/edge vocabulary, fields and qname convention — the adapter
  contract, pinned by `tests/contract/`. Tool-payload keys shipped at `CONTRACT_VERSION = 5` without a
  bump: `index_root` (071, `tests/test_index_root.py`), `try_instead_hint` (093). C2 is satisfied by a
  dedicated test in `tests/`, not by `tests/contract/`.
- **CLR-3 — what measures AC3's token delta?**
  Self-resolved: `code_atlas/tokens.py::estimate_tokens` — the single definition site already used by
  061's payload-weight test and 099's hard cap. No second estimator (R6.7).

### Cause / gap analysis (enhancement)

| Goal | Current | Target | Gap |
|---|---|---|---|
| G1 | `impact` returns `seeds_dropped` / `frontier_skipped_non_resolved` / tiered rows as JSON only (`impact.py:54-64`) | the same numbers rendered as one quotable line | no rendering path exists |
| G2 | the revision half exists but only on `get_index_status` / `build_or_update_index` (`staleness.py:63`); nav payloads carry `index_root` alone (`nav_result.py:178`) | the attestation names the revision it describes | the two halves are never joined |
| G3 | — | the renderer names no repo, no framework, no language | must be enforced by the R1.1/R2.2 grep-gates |

### Blast radius

**14 files.** New core module `code_atlas/tools/claim.py`; edits to `nav_result.py`, `impact.py`,
`find_callers.py`, `find_references.py`, `get_index_status.py`; new `tests/test_claim_signing.py`;
docs (`README.md`, `docs/PLAN.md`, `docs/BACKLOG.md`, this file, `docs/LESSONS.md`).

**Pinned-count trap, in the change list rather than a surprise at the gate (LESSONS 072).** A new
module under `code_atlas/` moves **both** guardrail denominators: `tests/test_core_is_language_agnostic.py:42`
and `tests/test_sql_confinement.py:32`, each currently `== 40` → `41`.

Repos touched: `app` (the only entry in `config.repos`). No `db-map` exists; no schema dependents.

**Fan-out:** none dispatched. `config.explore_fanout` is true, but the session's standing instruction
is that no subagent runs unless the operator asked for it; the operator asked for the **reviewer**
only. Recorded as a disclosure item, not a silent skip.

### Rule sections

`RULE SECTIONS: 19 applicable — 16 by change-type | 3 by recalled handle — §R1.1 (change-type) ✅, §R1.2 (change-type) ✅, §R1.3 (change-type) ✅, §R1.4 (change-type) ✅, §R3.1 (change-type) N/A (tool-payload key, not node/edge vocabulary — CLR-2), §R3.2 (change-type) ✅, §R4.1 (change-type) ✅, §R4.2 (change-type) ✅, §R5.2 (change-type) ✅, §R6.1 (change-type) ✅, §R6.4 (change-type) ✅, §R7.1 (change-type) ✅, §R7.2 (change-type) ✅, §R7.3 (change-type) ✅, §R7.4 (change-type) ✅, §R7.5 (change-type) ✅, §R5.4 (recalled handle, PROVISIONAL) ✅, §R6.5 (recalled handle) ✅, §R6.7 (recalled handle) ✅`

| § | Source | What in *this* change it constrains |
|---|---|---|
| R1.1 | change-type | The renderer reads `kind` / `confidence_tier` from the contract vocabulary; no branch keys on language or suffix. CI grep-gate covers the new module. |
| R1.2 | change-type | One renderer function, no registry and no base class — the flag is a parameter, not a strategy object. |
| R1.3 | change-type | `tools/claim.py` imports `contract` / `staleness`; nothing imports it back. |
| R1.4 | change-type | The renderer only formats; it never queries SQLite and never parses. |
| R3.1 | change-type | **N/A because** the added key is a tool-payload field, not node/edge vocabulary, fields, or qname convention — `index_root` (071) and `try_instead_hint` (093) both shipped at `CONTRACT_VERSION = 5`. |
| R3.2 | change-type | The key name is declared once and imported — no second literal in the tools that attach it. |
| R4.1 | change-type | Formatting plus one git HEAD read. No model, no network. |
| R4.2 | change-type | Same payload + same index ⇒ byte-identical line; key order fixed, no dict iteration order dependence. |
| R5.2 | change-type | The line never claims `RESOLVED` for a `HEURISTIC` hit — AC2 is this rule made testable. |
| R5.4 | **recalled handle** (PROVISIONAL) | The `key=value` form *is* this rule: each machine-readable value gets its own key; prose caveats do not share a field with a count. Provisional → surfaced, never gate-blocking. |
| R6.1 | change-type | AC1–AC3 each land a test; no AC ships on inspection. |
| R6.4 | change-type | The degraded-line tests are real tests, not smoke. |
| R6.5 | **recalled handle** | Both pinned sweeps (`40 → 41`) move deliberately, and the AC2 guards are **made to fail** before they are trusted. |
| R6.7 | **recalled handle** | The signed/unsigned tool split is **derived** from which tools call the renderer, never a hand-kept list in the test. |
| R7.1 | change-type | One line per answer; no report generator (Scope bullet 6). |
| R7.2 | change-type | PLAN + BACKLOG + this ticket's frontmatter updated before the PR. |
| R7.3 | change-type | Logical commits, imperative messages, no AI-attribution trailer. |
| R7.4 | change-type | If only one tool ends up signing, the renderer stays a function — no interface with one implementer. |
| R7.5 | change-type | Every new comment ≤ 3 lines. |

### Universal inventory

R3/AC5 carry a universal ("start with the tools whose answers are attestations" / "record which
answers are left unsigned"). Denominator **N = 14 registered tools**, derived from
`main.TOOL_NAMES` (`main.py:36-51`) rather than hand-listed (R6.7): **4 sign** — `impact`,
`find_callers`, `find_references`, `get_index_status`; **10 are recorded exclusions**, each with
the caveat it would have lost — `build_or_update_index`, `search_symbol`, `file_outline`,
`read_symbol`, `find_implementations`, `find_view_data`, `include_graph`, `reachable_from`,
`find_orphans`, `explain_path`. Review must confirm **all 14**, not a total.

Per-item checklist (AC5 is a "do X for each of N" requirement — one row per item, not an aggregate):

| # | Tool | Signs? | Caveat it would have lost |
|---|---|---|---|
| 1 | `impact` | **yes** | — |
| 2 | `find_callers` | **yes** | — |
| 3 | `find_references` | **yes** | — |
| 4 | `get_index_status` | **yes** | — |
| 5 | `build_or_update_index` | no | to be recorded at Gate 2 |
| 6 | `search_symbol` | no | to be recorded at Gate 2 |
| 7 | `file_outline` | no | to be recorded at Gate 2 |
| 8 | `read_symbol` | no | to be recorded at Gate 2 |
| 9 | `find_implementations` | no | to be recorded at Gate 2 |
| 10 | `find_view_data` | no | to be recorded at Gate 2 |
| 11 | `include_graph` | no | to be recorded at Gate 2 |
| 12 | `reachable_from` | no | to be recorded at Gate 2 |
| 13 | `find_orphans` | no | to be recorded at Gate 2 |
| 14 | `explain_path` | no | to be recorded at Gate 2 |

- **Gate 1 status:** ✅ confirmed by the operator

---

## Phase 2 — Design

### Approach

**One renderer module, four opt-in call sites, zero change to any default payload.**

`code_atlas/tools/claim.py` is a **pure formatter**: it takes an already-computed payload plus an
already-computed staleness dict and returns the same payload with one added key, `claim`, holding a
single `key=value` line. It never opens a store, never reads git, never branches on language — the
tool that already holds the open store passes `compute_staleness(store, config,
include_dirty_count=True)` in. That keeps R1.4 (the renderer formats; it does not query) and R4.1/R4.2
(no I/O of its own ⇒ same inputs, same bytes) true by construction rather than by discipline.

**The line's grammar** (fixed key order — R4.2 forbids dict-iteration-order output):

```
<schema> tool=<name> subject=<quoted> question=<fixed-per-tool> answer=<n> [tier=<weakest>]
         [<tool-specific payload keys, verbatim>] [truncated=true] rev=<short> ref=<name> index=<state> [dirty_indexed=<n>]
```

AC1's four required components — **subject · question · answer · revision** — are always present or
the line is not emitted. Everything in brackets is a **caveat key**: present exactly when the caveat
is real, absent otherwise. That is what W1 bought — a caveat that owns a key cannot be dropped
silently the way a caveat inside a prose clause can.

**Worked example (AC4).** What the field session actually shipped:

> No product code, no `src/` consumer.

What it was already holding, unrendered:

```
code-atlas/1 tool=impact subject="app/Http/A.php,app/B.php,+2" question=blast-radius answer=25 tier=RESOLVED seeds_dropped=0 frontier_skipped_non_resolved=0 rev=a1b2c3d ref=main index=current
```

And the modelled zero AC1 pins:

```
code-atlas/1 tool=impact subject="app/Http/A.php,app/B.php,+2" question=blast-radius answer=0 seeds_dropped=0 frontier_skipped_non_resolved=0 rev=a1b2c3d ref=main index=current
```

`seeds_dropped=0` is what separates *a modelled zero* from *a query that found nothing because it
asked wrong* — which is precisely the claim a text search cannot make (G2).

**Two grammar decisions that correct my own Gate-0 preview**, stated rather than absorbed:
1. **`question=` is always present**, including on the degraded `find_callers` example, where my
   preview omitted it. R1 names four components; three is not four.
2. **Tool-specific keys keep their payload names verbatim** — `frontier_skipped_non_resolved=0`, not
   the shorter `frontier_skipped=0` I previewed. A second spelling would be a second vocabulary for
   one value (R3.2's spirit), and it would break the line's re-derivability from the payload.
What the operator ratified was the `key=value` **form**; both corrections keep that form.

**`tier=` is emitted only when there are hits, and always names the WEAKEST tier present** (R5.2 —
never claim the stronger tier). An empty answer carries no `tier` because there is nothing to tier;
`answer=0` plus the modelled-zero counts is the claim.

### Rejected alternatives

1. **A new `detail_level` value (`"signed"`).** Rejected: `detail_level` is a global verbosity axis,
   inert on nav payloads today (`nav_result.py:141,171,200` all `del` it). Wiring verbosity to perform
   attestation widens the `Literal` on all 14 tools — including the 10 that must stay unsigned — to
   express a per-tool capability. It also makes signing mutually exclusive with `minimal`, which is a
   coupling nobody asked for.
2. **A separate `sign_answer` tool that re-renders a prior payload.** Rejected by Scope bullet 6
   (*"Do not build a report generator"*) and by R7.1: it costs a tool slot out of 14, doubles the
   call count for one line, and would have to re-read the index to name the revision — breaking C1's
   *"no new computation"*.
3. **Signing every tool.** Rejected by Scope bullet 3 and C5: a `search_symbol` page is a list of
   rows, not a claim. Signing it would produce a quotable artifact that asserts nothing, which is
   worse than none — the same failure `route-must-answer` (093-C4) records for routes.
4. **Emitting the line to stderr / a log instead of the payload.** Rejected: the agent's context is
   the payload; anything else does not reach the artifact where the claim is made (G1).

### Assumptions

| # | Assumption | Tag | Resolution |
|---|---|---|---|
| A1 | `compute_staleness(store, config, include_dirty_count=True)` is callable from a nav tool while its store is open | **verified** | `get_index_status.py` and `build_or_update_index.py` both already call it against an open store (`staleness.py:63`) |
| A2 | Adding a keyword param with a default to a FastMCP-registered tool publishes it in `inputSchema` without disturbing the other 10 tools' schemas | **novel-untested (3p/runtime)** | **Resolved by shaping the proof as integration**: `test_sign_is_published_on_exactly_the_attesting_tools` lists tools over a live MCP client (the `test_mcp_server.py:446` pattern) and asserts `sign` appears on exactly 4 of `main.TOOL_NAMES` and on none of the other 10. It **fails if the assumption is false.** |
| A3 | `tokens.estimate_tokens` is the sanctioned measure for AC3's delta | **verified** | `code_atlas/tokens.py` docstring names 061 and 099 as its two callers; a second estimator would violate R6.7 |

**No unresolved `novel-untested` assumption remains.**

### Smallest change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| CL1 | New pure renderer: `CLAIM_SCHEMA`, `CLAIM_KEY`, `sign()` | `code_atlas/tools/claim.py` *(new)* | New core module ⇒ **both** pinned guardrail denominators move (CL7, CL8); imported by CL2–CL5 | R1, R2, R4, C1, C4, W1 | 1/14 |
| CL2 | `sign: bool = False` + attach on the modelled zero and the hit path | `code_atlas/tools/impact.py` | `tests/test_impact.py`, `tests/test_empty_answer_cannot_explain_itself.py` — both call with defaults, so unaffected (AC3) | R3, AC1 | 2/14 |
| CL3 | `sign: bool = False` + attach | `code_atlas/tools/find_callers.py` | `tests/test_nav_tools.py`, `tests/test_bare_name_callers_silent_drop.py` | R3, AC2 | 3/14 |
| CL4 | `sign: bool = False` + attach | `code_atlas/tools/find_references.py` | `tests/test_nav_tools.py`, `tests/test_class_const_mention.py` | R3 | 4/14 |
| CL5 | `sign: bool = False` + attach (`answer=<staleness>`, no redundant `index=`) | `code_atlas/tools/get_index_status.py` | `tests/test_get_index_status_health.py`, `tests/test_index_ref.py` | R3 | 5/14 |
| CL6 | Proving test + AC2/AC3/AC5 tests | `tests/test_claim_signing.py` *(new)* | none identified | AC1, AC2, AC3, AC5, C3, C5 | 6/14 |
| CL7 | Pinned denominator `40 → 41` | `tests/test_core_is_language_agnostic.py:42` | Guards the guard against vacuity (comment at `:41`) | C4, R6.5 | 7/14 |
| CL8 | Pinned denominator `40 → 41` | `tests/test_sql_confinement.py:32` | Same sweep, second axis | C4, R6.5 | 8/14 |
| CL9 | *Signing a claim* section: worked example + the 10-tool exclusion list | `README.md` | Doc inventory lags a new core module (040-C1) | R5, AC4, AC5, C5 | 9/14 |
| CL10 | Tool table + §12 note that 4 tools sign | `docs/PLAN.md` | R7.2 | G2 | 10/14 |
| CL11 | Status row + Token-usage row for 100 | `docs/BACKLOG.md` | R7.2 + the AGENTS.md token-ledger rule | — (bookkeeping) | 11/14 |
| CL12 | `status: done → done` + this working doc | `docs/tasks/100_claim-signing-output-mode.md` | R7.2 | — (bookkeeping) | 12/14 |
| CL13 | Lesson entry + claim records | `docs/LESSONS.md` | learning loop | — (bookkeeping) | 13/14 |
| CL14 | **Proof collateral** — confirm the published-schema test still reads only `detail_level` | `tests/test_mcp_server.py:441` | Traced: the assertion indexes `schema["properties"]["detail_level"]` only, so a new sibling property does not break it. **No edit expected**; listed so an edit here is not an execute surprise | AC3 | 14/14 |

**Test blast-radius trace (mechanical).** `grep -rn "inputSchema\|properties" tests/` returns exactly
one schema-shaped assertion — `test_mcp_server.py:441-449` — and it reads
`schema["properties"]["detail_level"]`, not the property set. `grep -rln` for the four signing tools
returns **20+ test modules**, every one of which calls with default arguments; that is why AC3's
byte-identity claim has the **entire 1222-test baseline as its collateral** rather than one golden.

### Recalled handles — answered by name

`HANDLES: 4 recalled | 3 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

| Handle | Answer |
|---|---|
| `try-instead-tool-name` (093-C1 → **R5.4**, PROVISIONAL) | **traced.** `grep -rn "try_instead\b\|try_instead_hint" code_atlas/tools/nav_result.py` → `:297 payload["try_instead"] = TRY_INSTEAD_SEARCH_SYMBOL`, `:310 payload["try_instead"] = try_instead`, `:312 payload["try_instead_hint"] = hint`. The register split is real and enforced at the payload layer. **Folded into the design:** the `claim` line puts **every** machine-readable value in its own key and carries **no prose field at all** — no key holds a sentence. Nothing folded into the change list; the rule is satisfied by CL1's grammar. |
| `derived-not-listed-invariant` (093-C2/095-C1/097-C1 → **R6.7**) | **traced.** `grep -rn "TOOL_NAMES" tests/*.py` → `test_explain_path.py:103`, `test_routing_surface.py:60`, `test_mcp_server.py:166,207,304`. The established pattern is to derive the denominator from `main.TOOL_NAMES`. **Folded into CL6:** the AC5 test derives all 14 names from `main.TOOL_NAMES` and asserts `signers ∪ excluded == set(TOOL_NAMES)`; only the 4-name signer policy is stated, never the 14-name denominator. |
| `prove-the-guard-fails` (093-C3 → **R6.5**) | **traced.** `grep -rn "vacuit\|would pass" tests/test_core_is_language_agnostic.py` → `:41 # Guards the guard: an empty module list or an empty name list would pass vacuously.` **Folded into CL6:** AC2's two degraded-line assertions are each paired with a **positive control** on the same fixture (a `RESOLVED`/`current` payload asserted **not** to carry the degraded key), so a renderer that emitted nothing at all would fail rather than pass vacuously. |
| `route-must-answer` (093-C4) | **does not apply because** this change adds no routing field: `claim` renders an answer the tool already computed and never names a tool for the reader to call next, so there is no route whose usefulness could be checked. |

### Rule compliance

Every section from the Gate-1 `RULE SECTIONS` line holds as answered there. The three that the design
actively shapes:

- **R5.4 (PROVISIONAL, recalled handle)** — the `key=value` grammar *is* this rule: one register per
  key, no prose sharing a field with a count. Surfaced, not enforced as a block (it is unratified).
- **R6.7** — the AC5 denominator is derived from `main.TOOL_NAMES`, never listed.
- **R5.2** — `tier=` names the **weakest** tier present, so the line can never claim `RESOLVED` over a
  `HEURISTIC` hit. AC2 is this rule made falsifiable.

### Verification plan (per AC, layer-matched)

| AC | Risk layer | Proof artifact | Layer-match |
|---|---|---|---|
| AC1 | **integration** — needs a built index, a real `impact` walk and a git revision read | integration test over a temp repo + index (`tests/test_claim_signing.py`) | ✅ |
| AC2 | **integration** — a `behind` index and `HEURISTIC` edges only exist in a real store | 2 integration tests, each with a positive control | ✅ |
| AC3 | **integration** — byte-identity is a property of real payloads, not of the formatter | integration test asserting `claim ∉ payload` at default, **plus the full 1222-test baseline** as collateral | ✅ |
| AC4 | **logic** — the risk is that a document does not contain the two strings | grep-shaped unit test over `README.md` | ✅ |
| AC5 | **runtime/3p** — the published `inputSchema` is FastMCP's output, not ours (assumption A2) | integration test over a **live MCP client** listing tools | ✅ |

**No `❌`. No coverage-gap exclusions recorded** — every AC is proven at or above its risk layer.

### Proving test

`tests/test_claim_signing.py::test_impact_modelled_zero_is_signed_with_subject_question_answer_and_revision`

Asserts that `impact(paths=[...], sign=True)` over a built index whose walk returns no rows produces
a `claim` line carrying **all four** required components plus `seeds_dropped=0`. **Fails pre-change**
(`impact` raises `TypeError: unexpected keyword argument 'sign'`); passes post-change.

Exact invocation:

```
scripts/docker-test.sh pytest -q "tests/test_claim_signing.py::test_impact_modelled_zero_is_signed_with_subject_question_answer_and_revision"
```

### Rollback + porting

**Rollback:** revert the branch. No migration, no persisted state, no index-schema change — the only
on-disk artifact is source. A partial revert is also safe: deleting `claim.py` and the four `sign`
parameters restores today's behaviour exactly, because no default path reads either.
**Porting:** `config.repos` holds one entry (`app`). Nothing to port.

### SCOPE

`SCOPE: M` — **unchanged from analysis.** 14 change-list items, of which 5 are bookkeeping/docs and 2
are one-line denominator bumps. No tier crossing, no branch-type drift (`feat/` carries a feature).

- **Gate 2 status:** ✅ confirmed by the operator

---

## Phase 3 — Execute

### Verification sweep — Axis 1 (file set)

```
$ git status --porcelain
 M README.md
 M code_atlas/tools/find_callers.py
 M code_atlas/tools/find_references.py
 M code_atlas/tools/get_index_status.py
 M code_atlas/tools/impact.py
 M docs/PLAN.md
 M docs/tasks/100_claim-signing-output-mode.md
 M tests/test_core_is_language_agnostic.py
 M tests/test_sql_confinement.py
?? code_atlas/tools/claim.py
?? tests/test_claim_signing.py
```

**11 files. `diff ⊆ approved change list` — no file outside it.** CL1–CL10 and CL12 are the eleven.
CL11 (`docs/BACKLOG.md`) and CL13 (`docs/LESSONS.md`) are finalise-phase bookkeeping, still to come.
**CL14 predicted "no edit expected" and no edit occurred** — `tests/test_mcp_server.py:441` indexes
`schema["properties"]["detail_level"]`, so a new sibling property left it untouched. The design-time
trace was right; recording it here is the proof, not the prediction.

```
$ grep -nEi "if +lang|language *==|\.php|php|laravel|symfony" code_atlas/tools/claim.py
  (no output — no language branch, no framework or sample name)
```

### Verification sweep — Axis 2 (design conformance)

Walked each Gate-2 Approach bullet:

| # | Approved bullet | Verdict |
|---|---|---|
| 1 | pure formatter — no store, no git, no language branch | implemented-as-approved |
| 2 | fixed key order (R4.2) | implemented-as-approved |
| 3 | the four components always present, or no line | implemented-as-approved |
| 4 | each caveat owns a key, present exactly when real | implemented-as-approved |
| 5 | `question=` always present (Gate-2 correction 1) | implemented-as-approved |
| 6 | tool-specific keys keep their **payload** names verbatim (Gate-2 correction 2) | **deviated → D2** |
| 7 | `tier` = weakest present; omitted with no hits | implemented-as-approved |
| 8 | opt-in `sign` flag on exactly the 4 attesting tools | implemented-as-approved |
| 9 | no line when there is no index | **deviated → D1** (widened) |

### Deviations (recorded, surfaced to review — not absorbed)

**D1 — `impact` also refuses to sign when no seed resolved.** Gate 2 approved one no-line rule (no
index). Execute added a second. **Why:** the probe below shows the payload cannot distinguish an
absent subject from a genuine zero, so a line there would be a false attestation — the exact harm
this ticket exists to prevent. Traces to **C5** (*"if an answer cannot be stated in one line without
losing a caveat, it does not get a line"*), already an approved matrix row. Pinned by
`test_impact_refuses_to_sign_an_answer_whose_subject_never_resolved`.

**D2 — the `impact` line carries `seeds=<n>`, computed in the tool rather than read from the
payload.** This is the one departure from Gate-2 correction 2 (*keys keep their payload names
verbatim, so the line stays re-derivable from the payload*). **Why:** seeds are returned **inside**
`results`, so `answer=25` alone cannot be read as *25 dependents* rather than *25 seeds and zero
dependents* — and "nothing depends on this" is the precise claim ticket 100 exists to make quotable.
`answer == seeds` is now the modelled zero. Cost: one line field is no longer re-derivable from the
payload alone. Adjudication is review's.

### Finding — NOT fixed here (would be scope creep)

**F1 — `impact` reports `seeds_dropped: 0` for a subject that resolved to no seeds at all.**
`store.py:1009-1011` returns `ImpactResult([], 0, 0)` before any counting, so a wholly unresolvable
subject is indistinguishable from a clean modelled zero. Measured:

```
$ impact(qnames=["\App\Nope"], sign=True)
--- missing qname: results=0 seeds_dropped=0
```

This is pre-existing `impact` behaviour, not something this diff introduced. Signing it would have
promoted an internal inaccuracy into a quotable claim, which D1 prevents. **Fixing the count itself
is outside the approved change list** — recorded for a follow-up ticket rather than absorbed.

### Empirical output

**Proving test (AC1) — fails pre-change, passes post-change.** Pre-change the parameter does not
exist, so the call raises `TypeError: impact() got an unexpected keyword argument 'sign'`.

```
$ scripts/docker-test.sh pytest -q "tests/test_claim_signing.py::test_impact_modelled_zero_is_signed_with_subject_question_answer_and_revision"
(green — folded into the full gate below)
```

**Full CI gate (ruff · mypy · pytest) in Docker:**

```
$ scripts/docker-test.sh
All checks passed!
Success: no issues found in 41 source files
1235 passed in 90.72s (0:01:30)
```

**Delta accounting — 1222 (`main`) → 1235, every one of the +13 explained:**

| Source | Δ | Evidence |
|---|---|---|
| `tests/test_claim_signing.py` | +10 | the file's own collection |
| two `core_modules()` parametrizations, 40 → 41 | +2 | `test_core_is_language_agnostic.py:47,57` |
| `consumers()` gained `claim.py` (it imports `contract`) | +1 | `test_contract_sole_source.py:57`; `consumers()` returns **28**, `claim.py` in the set |

`mypy` reporting **41** source files is the same 40 → 41 move, independently.

**Measured token delta (AC3 / C3 / 061):**

```
impact         default=  78 tok  signed= 129 tok  delta=+51 tok (205 chars)
find_callers   default=  53 tok  signed=  99 tok  delta=+46 tok (186 chars)
```

Real emitted lines from that run:

```
code-atlas/1 tool=impact subject=\App\UserRepo::save question=blast-radius answer=1 tier=RESOLVED seeds=1 seeds_dropped=0 frontier_skipped_non_resolved=0 rev=c617dc2 ref=master index=current
code-atlas/1 tool=find_callers subject=\App\UserRepo::save question=callers answer=0 reason=no_matches frontier_skipped_non_resolved=0 rev=c617dc2 ref=master index=current
```

### One correction the tests forced

The first draft of the test parser used `shlex.split`, which applies POSIX escaping and **ate the
backslashes in a PHP FQN** (`\App\UserRepo::save` → `AppUserRepo::save`). The failure was in the
test's reader, not the renderer: the line's grammar is space-separated `key=value` with double
quotes and no escapes, and a regex splitter round-trips it exactly. Recorded because "machine
parsable" was the operator's stated reason for choosing this form at Gate 0 — and the first tool
reached for could not parse it. The parser now says why it is not `shlex`.

### SCOPE

`SCOPE: M` — unchanged. 11 files touched of 14 approved; no tier crossing; branch type `feat/`
matches a feature. **No outgrew-its-ticket nudge raised.**

- **Phase 3 status:** ✅ complete → review

---

## Phase 4 — Review ✋

**Reviewed at `eec0019`** (files: `code_atlas/tools/claim.py`, `impact.py`, `find_callers.py`,
`find_references.py`, `get_index_status.py`, `tests/test_claim_signing.py`, the two pinned-count
tests, `README.md`, `docs/PLAN.md`, this file).

**Challenger: WAIVED** by operator instruction (2026-08-16). Recorded, not silently skipped — see
the disclosure note at the end of this section.

### Round 1 — `reviewer` → **CHANGES REQUESTED** (2 Important, 0 Critical)

**Finding 1 — `get_index_status`'s claim dropped its own declared caveat at `minimal`.**
`CLAIM_CARRY = ("parse_failures",)` sourced the caveat off the **payload**, but that key is only
added at `standard`/`verbose`; at `minimal` the payload carries the raw `failed` key instead. So a
`minimal` line was signed **without** `parse_failures` while the failures were real. Reproduced by
the reviewer on the existing health fixture:

```
MINIMAL claim:  code-atlas/1 tool=get_index_status ... answer=2 index=unknown
STANDARD claim: code-atlas/1 tool=get_index_status ... answer=2 parse_failures=1 index=unknown
minimal has failed: 1
minimal has parse_failures key: False
```

This is exactly the C5 harm — a quotable artifact hiding its own weakness — and it was **untested**:
no test in `tests/test_claim_signing.py` exercised `get_index_status`'s line content, so AC2/R6.1
was not in fact met for that signer. **Fixed:** the count comes from `counts["failed"]` (computed
unconditionally in `_status`) via `extra=`, emitted only when non-zero.

**Finding 2 — `_value` left an embedded `"` unbalanced.** A value holding a `"` was quote-wrapped
without escaping, producing `"He said "hi""` — which breaks the project's own test-side parser and
any downstream one. **Fixed, but not the way the reviewer proposed.** The suggestion was to fold
`"` → `'`; that was rejected because folding **silently rewrites the subject** of a claim whose
whole purpose is to be re-checked against the repo. An inner quote is now **doubled**
(RFC-4180 style), which is lossless and still introduces **no escape character**, so a separator
backslash survives verbatim. The reviewer adjudicated the substitution and agreed it is the better
fix.

### Round 2 — `reviewer` (verify-only) → **LGTM**

- Re-ran the reviewer's own Finding-1 reproduction against the new code: `minimal` now carries
  `parse_failures=1` identically to `standard`.
- Confirmed "omit when zero" is right and not a regression: every existing `parse_failures`
  assertion (`test_get_index_status_health.py`, `test_list_parse_failures.py`,
  `test_legacy_hardening.py`) is payload-level and none pinned `parse_failures=0` inside a line.
  It also makes this signer consistent with the other three (`truncated`, `authoritative`,
  `dirty_indexed` are all present-only-when-real).
- **Fuzzed the updated `_TOKEN` regex rather than eyeballing it:** every string of length 0–4 over
  `{", space, comma, =, \, a, b}` (2,801 cases) and length 5–6 over `{", space, comma, =, \, a}`
  (54,432 cases), each rendered with trailing keys to probe post-quote parsing — **0 failures**,
  including the three shapes flagged by name (value that is only quotes, trailing quote, adjacent
  quoted tokens).
- Independently re-ran the Docker gate rather than trusting the report.

### A guard that fired on its author

The Finding-2 docstring named a language — *"a PHP FQN"* — **inside `code_atlas/tools/claim.py`**.
The R1.1 grep-gate failed the build on it (`test_no_core_module_names_a_language[claim.py]`). It was
invisible to review round 1 because the text did not exist yet when that sweep ran. Reworded; all
five touched core files re-grepped clean. **Recorded as a process fact:** an R1.1 sweep is not a
once-per-ticket action — a later commit that only edits a docstring can reintroduce exactly what it
checks for.

### Scope reconciliation

`eec0019` touches only Finding 1's and Finding 2's files plus their test file — no new file, no
other tool. `diff ⊆ approved change list` still holds. **No outgrew-its-ticket nudge.**

### Deviations & finding — adjudicated

| Item | Verdict |
|---|---|
| **D1** — `impact` refuses to sign when no seed resolved | **accepted.** Traces to C5; signing there would promote an internal ambiguity into a quotable claim |
| **D2** — `seeds=<n>` computed in-tool, not carried from the payload | **accepted.** `len(seeds)` is a list the tool already computed; `answer == seeds` is the only unambiguous statement of the modelled zero |
| **F1** — `store.py:1009-1011` reports `seeds_dropped=0` for an unresolvable subject | **correctly left unfixed.** Pre-existing, outside the change list; D1 neutralises the one place this diff could have turned it into a signed falsehood. Follow-up ticket |

### Final gate

```
$ scripts/docker-test.sh
All checks passed!
Success: no issues found in 41 source files
1238 passed in 60.53s (0:01:00)
```

`main` baseline 1222 → 1238. **+16, all accounted:** +13 as itemised in Phase 3, plus **+3** from the
review-fix tests (`test_a_parse_failure_rides_the_line_at_every_detail_level`,
`test_a_clean_index_carries_no_parse_failure_key`,
`test_a_quoted_value_round_trips_and_does_not_corrupt_the_rest_of_the_line`). No test removed.

**Disclosure — the challenger did not run.** Ticket 016 and the 2/2 field record say the reviewer
alone is not a proven substitute for the human at this gate. Two Important defects were found by the
reviewer here; whether a ticket-blind challenger would have found a third is **unknown and untested**
on this ticket.

- **Gate 4 status:** ✅ clean at `eec0019`

---

## Phase 5 — Finalise ✋

### Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Notes |
|---|---|---|---|---|
| 0 refine | exposure-checker | — | **0 (not dispatched)** | session standing instruction: no subagent unless the operator asked. Disclosed, not silently skipped |
| 1 analysis | Explore fan-out | — | **0 (not dispatched)** | same reason; `config.explore_fanout` is true |
| 4 review | `mango:reviewer` | 1 | **134,921** | 54 tool-uses, 649 s |
| 4 review | `mango:reviewer` | 2 (verify) | **161,099** | 16 tool-uses, 272 s |

`LEDGER TOTAL: 296,020 · top cost driver: phase 4 / mango:reviewer`

Every row carries a real number — no `unmeasured` cell this run; both dispatches returned a usage
block via task-notification.

### Decision log

| # | Decision | Where |
|---|---|---|
| 1 | The surface is a per-call `sign` flag, not a `detail_level` value or a separate rendering | Phase 0 HOW-1 |
| 2 | The line's form is `key=value`, one key per caveat | Phase 0 W1 (operator) |
| 3 | A tool-payload key needs no `contract_version` bump | Phase 1 CLR-2 |
| 4 | `seeds=` rides the impact line although it is not a payload key | Phase 3 D2 (review-accepted) |
| 5 | An `impact` answer with no resolved seed gets no line | Phase 3 D1 (review-accepted) |
| 6 | An inner `"` is doubled, not folded to `'` | Phase 4 Finding 2 (review-accepted) |
| 7 | `parse_failures` is sourced from `counts`, and omitted when zero | Phase 4 Finding 1 |
