---
id: 101
slug: nav-tools-take-one-subject-at-a-time
title: 'A ten-name sweep is ten calls, so the agent used a shell loop — a shape mismatch no cost metric can see'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [014, 013, 066]
---

## Goal
Before writing a single line of the port, the field session needed to know whether any of **ten**
helper-function names it was about to introduce were already taken globally. `search_symbol` with
`kind: "Function"` answers that exactly, and it never got called. Not from ignorance and not from
cost — from **granularity**: the graph takes one subject per call, so ten names is ten round-trips,
while a shell loop is one call for all ten.

The evaluator picked the tool whose shape matched the question. Its own account: *"I framed the task
as a sweep and picked the tool with a loop."* The sweep found a real collision — a global `getState`
with a **different signature** — and that finding drove the design of ~1,900 lines of the diff.

This is a distinct failure mode from every adoption finding so far, and the interview is right that no
existing metric sees it: [096](096_edit-then-ask-tax-two-files-cost-a-minute.md) measures *cost per
call*, and the problem is not that a call is slow. **Ten calls is the wrong granularity for one
question.** Any tool that answers *"is this name taken"* will keep losing to a shell loop until it can
take a list.

## Evidence (field interview, 2026-08-14, §1 Moment 1 and §7.3)
- §1 Moment 1, "why didn't you call it": ***"(f) other — shape mismatch, not ignorance.** I had 10
  names to check at once. The graph is one-subject-per-call, so that is 10 round-trips; the shell loop
  is one call."*
- The command actually run: `grep -rn "function <name>(" src/ public/` over 10 candidate names — a
  sweep that searched **two directories**, where the graph would have searched the whole index.
- Round 5 §7.3 recorded the same event from the retro side and called it *"a recall failure"*. The
  interview refines that: it was not recall — the tool was known and it did not fit the question's
  shape.
- §7.3 of the interview states the general form: *"Any tool that answers 'is this name taken' will lose
  to a sweep until it can take a list."*

## Generality — why this one survives the "n = 1, one repo" filter
The question that lost — *are any of these N names already taken?* — is not specific to a migration or
to PHP. Renaming a batch of symbols, checking a list of candidate identifiers before generating code,
auditing a set of paths named in a diff: all are list-shaped, and an agent facing a list-shaped
question will reach for the tool that takes a list. The mismatch is between **the granularity of the
question and the granularity of the interface**, and both sides of that are code-atlas's, not the
anchor's.

Bounded on purpose: this ticket batches subjects, and does not become a query language.

## Scope / Deliverables
- **Decide which tools take a list of subjects, and which must not.** `search_symbol` is the clear
  case (a name-availability sweep). `impact` already takes multiple paths. Single-answer tools like
  `read_symbol` may be wrong to batch — a batched body read is just a file read. Record the verdict
  per tool rather than batching everything (**R1.2**).
- **Bound the fan-out and disclose the bound**, following [066](066_limit-clamped-silently.md): a
  batched call must say how many subjects it accepted, how many it clamped, and which. A silently
  truncated sweep is worse than ten honest calls, because a sweep's whole purpose is completeness.
- **Keep the per-subject answer shape.** The result must remain addressable per subject — a merged
  result set would re-create [070](070_ambiguous-qname-no-scoping.md)'s defect at batch scale.
- **Answer the empty-subject case per subject.** Each subject carries its own `reason`; one miss in a
  batch of ten must not colour the other nine (065's rule, applied element-wise).
- **Measure the win.** Ten single calls vs one batched call: tokens and wall clock, on a large index.
  If the saving is only latency and not tokens, say so — the argument here is *shape*, and it should
  survive on shape, not on a number that flatters it.

## Constraints
- **R4** — deterministic ordering: results follow the caller's subject order, not the store's.
- **061** — a batched payload must not repeat per-subject boilerplate ten times; that would trade a
  shape problem for a weight problem.
- **R3** — a changed input shape touches the tool contract and the conformance suite.
- **R1.2 / YAGNI** — one batched tool first, proven in the field, before the pattern spreads.
- Cost: a batch must not fan out into an unbounded index scan; the bound is part of the contract.

## Acceptance criteria
- `search_symbol` (or the tool the design selects) accepts N subjects, returns N addressable answers
  with per-subject reasons, and pins the whole payload in a test.
- Exceeding the bound reports the clamp and names what was dropped (066's rule), with a test.
- Single-subject calls are byte-identical to today (R4).
- Tokens and wall clock for 10 single calls vs 1 batched call are recorded on a large index.
- A written per-tool verdict on which tools do **not** get a list, with reasons.

## References
Field interview (round-5 companion, 2026-08-14) §1 Moment 1, §7.3, §8.4 item 3. Related:
[066](066_limit-clamped-silently.md) (disclose the bound), [065](065_empty-answer-cannot-explain-itself.md)
(per-subject reasons), [070](070_ambiguous-qname-no-scoping.md) (why answers must stay addressable),
[014](014_search-read-outline.md) and [013](013_nav-tools.md) (the tools),
[096](096_edit-then-ask-tax-two-files-cost-a-minute.md) (the cost metric that cannot see this).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Phase:** 0 — Refine (complete) → 1 Analysis
- **KEY:** 101 · **branch:** `feat/101-nav-tools-take-one-subject-at-a-time`
- **STRUCTURE:** native
- **TRACK:** backend
- **SCOPE:** M (declared at analysis)
- **TIER:** full
- **work_doc_mode:** embed (plain local-file ticket, hand-authored — not a scaffold stub)
- **BASELINE:** pending (Docker gate running on `main` @ `b37a153`)
- **Challenger:** WAIVED by operator instruction (2026-08-16). Reviewer agent still runs.
- **Gate policy this run:** the operator granted standing approval for every ✋ gate up to and
  including commit + push + open PR. Each gate is still surfaced in-conversation before it is crossed.
- **Autonomous-run envelope (mini-spec 2, amended §0b):** `RUN CONTRACT` at
  `~/.mango/runs/code-atlas/101/contract.txt` — ceiling `PR`, precedent found, **6** termination
  conditions, **3 UNBOUND** until Gate 2. Writer/validator + reconciler at
  `~/.mango/runs/code-atlas/101/harness/`, **29 tests green** (M6). Floor is a **tree comparison**
  (M2), an ancestry predicate is refused because the repo squash-merges (M3), and every condition
  declares both a `force-broken` and a `force-holding` case (M4).

---

## Phase 0 — Refine

`PREMISE: 24 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 12 claim(s) surfaced | 0 by symbol | 7 by handle | 5 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 1 want-decision asked | 7 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Premise check.** Every source ticket 101 cites as already existing resolves.
Tools/symbols: `search_symbol` (`code_atlas/tools/search_symbol.py:39`), its `kind` parameter
(`:41`) and `contract.NODE_KINDS` including `Function` (`code_atlas/contract.py:31`), `impact`
already taking `paths: list[str]` (`code_atlas/tools/impact.py:27`), `read_symbol`
(`code_atlas/tools/read_symbol.py`), the per-answer `reason` channel (`nav_result.py:18-56`),
`clamp_limit` + `attach_limit_capped` (`config.py:334`, `nav_result.py:343`), `CONTRACT_VERSION = 5`
(`contract.py:21`), the conformance suite (`tests/contract/`).
Tickets: 013, 014, 061, 065, 066, 070, 096 all present under `docs/tasks/`. Rules R1.2, R3, R4, R6.1
present in `docs/ENGINEERING_RULES.md`.
**Ambiguous (1, non-blocking):** *"Field interview (round-5 companion, 2026-08-14) §1 Moment 1, §7.3,
§8.4 item 3"* is an external document, not a repo path — a prose reference, never a falsified
premise. **PREMISE HOLDS.**

**Recalled claims (advisory — injected nothing, blocked nothing).**
By handle (7), matched on the shape of the change (a **shared payload vocabulary** extended, and a
**value threaded through callers**): `derived-not-listed-invariant` (→ R6.7),
`prove-the-guard-fails` (→ R6.5), `try-instead-tool-name` (→ R5.4),
`do-not-attest-past-the-payloads-resolution` (100-C4), `source-the-caveat-from-the-computation`
(100-C1), `route-must-answer` (093-C4, no rulebook destination),
`record-the-deviation-as-a-deviation` (PROM-C3 → P3).
By area (5): `099-C1` *channel-cannot-carry-unasked-information* (agent-fit positioning — 101 is the
**interface-granularity** twin of that finding), `097-C2` (routing surface / recognition — a
description cannot make an agent notice a tool; nor can a batch parameter), `038-C1` (store/tools
payload shaping under the R3.2 sole-source gate — directly binding on any new payload literal),
`037-C1` *aggregate-vs-per-unit normalized at the producer* and `037-C2` *withdraw the argument when
the number moves* — both bind **AC4**, which asks for a 10-call-vs-1-call measurement.
Does not apply: `sibling-meta-non-int` (store/census accessor), `scope-by-key-not-by-file`,
`pin-the-table-a-purity-claim-rests-on`, `late-writer-outside-the-delta`,
`invert-the-rewrite-the-lookup-applies`, `skip-dynamic-means-unlinkable` (resolver/indexer
internals), `structural-silence-over-stateful-latch`, `hook-event-is-part-of-the-contract` (hooks),
`lossless-repair-for-a-checkable-artifact` (artifact quoting), `re-run-the-sweep-after-the-last-edit`
(process, applied at execute rather than recalled as a design constraint),
`increment-on-the-common-path`, `identity-check-misses-substance` (the promote pass itself).

**WANT-decision asked (1) — handed back, so `ASSUMED (awaiting ratification)`.**
**W1 — the value of the subject bound, and its knob.** Surfaced to the operator, who had granted a
standing "pick the best option". Assumption taken: a **new `max_subjects` knob, default 25**, resolved
through the existing `KNOB_KEYS`/`CA_MAX_SUBJECTS` ladder (`config.py:26-39`). Rationale: the field
incident is a **ten**-name sweep, so 10 must sit comfortably inside the bound; 25 leaves headroom
without inviting a batch that is really a query language (Scope: *"this ticket batches subjects, and
does not become a query language"*). The per-subject `limit` keeps today's meaning, so worst-case
work is `max_subjects × limit`, bounded and caller-visible rather than an unbounded index scan.
**Confirm or override at Gate 1.**

**HOW-decisions (resolved + cited, 7).**
1. **`search_symbol` is the tool that takes the list; nothing else changes.** Cited Scope bullet 1
   (*"`search_symbol` is the clear case (a name-availability sweep)"*) and R1.2 / Constraint
   *"one batched tool first, proven in the field, before the pattern spreads"*. The per-tool verdict
   for every other tool is AC5's deliverable, not a second implementation.
2. **The surface is a new optional `queries: list[str] | None` beside `query`, never a widened
   `query`.** Cited AC3 (*"Single-subject calls are byte-identical to today (R4)"*): widening
   `query` to `str | list[str]` changes the declared JSON-schema type of a parameter every existing
   client already sends, so single-subject calls would not be byte-identical at the schema level.
   A new optional parameter leaves the existing schema entry untouched.
3. **The batched payload is a list of per-subject answers in caller order, never a merged set.**
   Cited Scope bullets 3–4 (*"Keep the per-subject answer shape … a merged result set would
   re-create 070's defect at batch scale"*, *"Each subject carries its own `reason`"*) and R4
   (*"results follow the caller's subject order, not the store's"*). Note the live counter-example
   in this repo: `impact` merges its seeds into one radius, which is exactly why ticket **102**
   exists — 101 must not repeat it.
4. **Passing both `query` and `queries` is a config/programmer error and fails loud.** Cited R5.3
   (*"Fail loud on config/programmer errors"*) — the alternative (silently preferring one) hides a
   caller bug behind a plausible answer.
5. **Repeated subjects are answered per input element; no dedupe.** Cited AC1 (*"accepts N subjects,
   returns N addressable answers"*) — dedupe would make the answer list a different length from the
   subject list and destroy positional addressability.
6. **The read-through freshness budget stays per *call*, shared across subjects — and each subject
   discloses the consequence in its own `reason`.** Cited `FreshnessGuard`'s `READ_THROUGH_CAP = 1`
   (`freshness.py:14`, *"Cap reparses per tool call"*) and the ticket's Cost constraint (*"a batch
   must not fan out into an unbounded index scan"*). Scaling the cap with the subject count would
   turn one call into up to `max_subjects` adapter reparses — the exact fan-out the ticket forbids.
   **This is a real, disclosable weakening**: ten single calls today get ten repair budgets; one
   batched call gets one. It is carried as a matrix row and must land in the docstring, not be
   discovered by a caller. (`do-not-attest-past-the-payloads-resolution`, 100-C4.)
7. **AC5's "written per-tool verdict" lands in `docs/PLAN.md` beside the tool surface, not in a new
   file.** Cited R7.2 (*"A design decision updates the plan"*) and R7.4 / 061 — a one-off doc for one
   table is a dead artifact.

**Exposure-checker dispatch: NOT run.** refine's 1-dispatch exposure check was not dispatched — this
session carries a standing instruction against subagent dispatch except where the invocation names
one. Disclosed rather than silently skipped; same treatment as ticket 100.

---

## Phase 1 — Analysis

`PREMISE: 24 checked | 0 missing | 1 ambiguous`
`RECALL: 12 claim(s) surfaced | 0 by symbol | 7 by handle | 5 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`STRUCTURE: native`
`TRACK: backend — 0/9 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`BASELINE: green`
`SECTIONS: 7 found (Goal · Evidence · Generality · Scope / Deliverables · Constraints · Acceptance criteria · References) | 7 decomposed | ROWS: C=5 R=5 G=3 AC=5`
`CLARIFICATION: 6 raised | 5 self-resolved (cited) | 1 for human decision`
`RULE SECTIONS: 17 applicable — 14 by change-type | 3 by recalled handle — §R1.1 (change-type) ✅ · §R1.2 (change-type) ✅ · §R1.4 (change-type) ✅ · §R3.1 (change-type) N/A (adapter node/edge vocabulary only — see CL-1) · §R3.2 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.3 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.4 (change-type) ✅ · §R6.6 (change-type) ✅ · §R7.1 (change-type) ✅ · §R7.2 (change-type) ✅ · §R7.3 (change-type) ✅ · §R7.5 (change-type) ✅ · §R5.4 (handle try-instead-tool-name) ✅ · §R6.5 (handle prove-the-guard-fails) ✅ · §R6.7 (handle derived-not-listed-invariant) ✅`

**BASELINE artifact.** `scripts/docker-test.sh` on `main` @ `b37a153` — **1240 passed in 61.16s**,
exit 0 (ruff · mypy · pytest). 0 baseline exclusions.

**Rules judged N/A, with the reason.** R1.3 / R1.5 / R1.6 (no adapter boundary is touched);
R2.1–R2.3 (no adapter source changes); R5.1 / R5.2 (no parse or resolver path); R6.2 / R6.3 (no new
language fixtures, no cross-repo claim); R8.1–R8.3 (no dependency change); R3.1 — see **CL-1**.

### Requirements matrix

| ID | Source | Verbatim (abridged) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | *"the graph takes one subject per call, so ten names is ten round-trips, while a shell loop is one call for all ten"* | The defect is **interface granularity**, not cost. Fix = let one call carry a list of subjects. | `search_symbol(query: str, …)` — one subject, `search_symbol.py:40` | open |
| G2 | Evidence | *"(f) other — shape mismatch, not ignorance"* / the run used `grep -rn "function <name>(" src/ public/` | The evaluator knew the tool; shape lost. So the fix must be a **shape** change, and no amount of description/routing substitutes (`097-C2`). | field interview §1 Moment 1, §7.3 (external doc, prose reference) | open |
| G3 | Generality | *"Bounded on purpose: this ticket batches subjects, and does not become a query language."* | Batching only. No boolean/filter/expression surface, no second batched tool this ticket. | R1.2 + Constraint 4 | open |
| R1 | Scope 1 | *"Decide which tools take a list of subjects, and which must not … Record the verdict per tool"* | `search_symbol` gets `queries`. A **verdict per tool** for all 14 in `main.TOOL_NAMES` (universal — see inventory). | `main.py:36-51` | open |
| R2 | Scope 2 | *"a batched call must say how many subjects it accepted, how many it clamped, and which"* | Three disclosures: accepted count, clamped count, **and the dropped subjects by name**. Stronger than today's numeric `limit_capped_to` — see **CL-2**. | `attach_limit_capped`, `nav_result.py:343` | open |
| R3 | Scope 3 | *"Keep the per-subject answer shape … a merged result set would re-create 070's defect at batch scale"* | Answers are a **list**, positionally addressable, in caller order. Never a union. | `impact` merges seeds → ticket 102 exists; `impact.py:54,112` | open |
| R4 | Scope 4 | *"Each subject carries its own `reason`; one miss in a batch of ten must not colour the other nine"* | `reason` is computed per subject from that subject's own query, never lifted from the batch (`source-the-caveat-from-the-computation`, 100-C1). | `NavReason`, `nav_result.py:18-56` | open |
| R5 | Scope 5 | *"Measure the win. Ten single calls vs one batched call: tokens and wall clock … If the saving is only latency and not tokens, say so"* | A recorded A/B, normalized per unit at the producer (`037-C1`), and the argument withdrawn if the number moves (`037-C2`). | AC4 | open |
| C1 | Constraints 1 | *"R4 — deterministic ordering: results follow the caller's subject order, not the store's"* | Answer *i* corresponds to `queries[i]`. No sort, no dedupe, no reordering. | R4.2 | open |
| C2 | Constraints 2 | *"061 — a batched payload must not repeat per-subject boilerplate ten times"* | Envelope fields (`indexed`, `index_root`, `truncated` roll-up) live **once** at the top; per-subject entries carry only what varies. | `list_result`, `nav_result.py:188-208` | open |
| C3 | Constraints 3 | *"R3 — a changed input shape touches the tool contract and the conformance suite"* | Read as: the **tool's published input schema** changes, and the repo's schema/sole-source guards must still pass. `CONTRACT_VERSION` is the **adapter** contract and does **not** bump — **CL-1**. | `CONTRACT_VERSION` history: 002, 049, 062, 063 — all adapter vocabulary; ticket 100 (payload change) never touched `contract.py` | open |
| C4 | Constraints 4 | *"R1.2 / YAGNI — one batched tool first, proven in the field, before the pattern spreads"* | Exactly one tool gains a list this ticket. No registry, no shared "batchable" base. | R1.2 | open |
| C5 | Constraints 5 | *"a batch must not fan out into an unbounded index scan; the bound is part of the contract"* | Two bounds: `max_subjects` (new knob) and the existing per-subject `limit`. Both disclosed. **And** the read-through repair budget stays **per call** — see HOW-6 / **CL-5**. | `READ_THROUGH_CAP = 1`, `freshness.py:14` | open |
| AC1 | AC 1 | *"accepts N subjects, returns N addressable answers with per-subject reasons, and pins the whole payload in a test"* | `len(answers) == len(queries)` for N ≤ bound; a golden-payload test pins the full dict. | — | open |
| AC2 | AC 2 | *"Exceeding the bound reports the clamp and names what was dropped (066's rule), with a test"* | Guard must be **observed failing** before it ships (R6.5 / `prove-the-guard-fails`). | — | open |
| AC3 | AC 3 | *"Single-subject calls are byte-identical to today (R4)"* | The **payload** for a `query=`-only call is unchanged dict-for-dict. The tool's **input schema** necessarily gains `queries` — **CL-3**. | `functools.wraps` preserves the published signature, `schema_guard.py:35` | open |
| AC4 | AC 4 | *"Tokens and wall clock for 10 single calls vs 1 batched call are recorded on a large index"* | A recorded measurement with the index size stated. "Large" pinned to the largest index reproducible in this repo — **CL-4**. | — | open |
| AC5 | AC 5 | *"A written per-tool verdict on which tools do **not** get a list, with reasons"* | One verdict per tool, denominator **N = 14**, derived from `main.TOOL_NAMES` not re-typed (R6.7). | `main.py:36-51` | open |

**References section** — decomposed as traceability only, 0 requirement rows: 066 (disclose the
bound) → R2/AC2; 065 (per-subject reasons) → R4; 070 (answers stay addressable) → R3; 014/013 (the
tools) → R1; 096 (the cost metric that cannot see this) → G1.

### Universal inventory — AC5's denominator (N = 14)

AC5 says *"which tools do **not** get a list"*, which is an "every tool" requirement. The inventory is
**derived** from `main.TOOL_NAMES` (R6.7), never re-typed; review must confirm **all 14**, not a total.

| # | Tool | # | Tool |
|---|---|---|---|
| 1 | `get_index_status` | 8 | `find_implementations` |
| 2 | `build_or_update_index` | 9 | `find_view_data` |
| 3 | `search_symbol` | 10 | `include_graph` |
| 4 | `file_outline` | 11 | `impact` |
| 5 | `read_symbol` | 12 | `reachable_from` |
| 6 | `find_callers` | 13 | `find_orphans` |
| 7 | `find_references` | 14 | `explain_path` |

### AC validation — every value independently re-derived

| AC | Ticket's value | Re-derived value | Falsifiable? | Verdict |
|---|---|---|---|---|
| AC1 | "N subjects" (N unstated) | N ≤ `max_subjects`; **25** assumed (W1) | yes — `len(answers) == len(queries)` | **mismatch → CL-6 (the one human item)** |
| AC2 | "reports the clamp and **names what was dropped** (066's rule)" | 066 as shipped reports a **number** (`limit_capped_to`), not names. AC2 is strictly stronger and needs a new list field. | yes — assert the dropped names appear | **mismatch → CL-2**; AC2's text wins |
| AC3 | "byte-identical to today" | Payload: byte-identical. Input schema: **cannot** be, the ticket's own Goal requires a new parameter. | yes — dict equality against a pre-change golden | **scope mismatch → CL-3** |
| AC4 | "on a large index" | Undefined here. Largest reproducible: this repo's own tree. Stated with its node/edge counts; if that is not "large", say so rather than re-fit (`037-C2`). | yes — recorded numbers | **definition pinned → CL-4** |
| AC5 | "a written per-tool verdict" | N = 14, derived from `main.TOOL_NAMES` | yes — count of verdicts == 14 | ✅ as written |

0 manual-check exclusions: every AC above is falsifiable.

### Clarifications

**Self-resolved (5), each cited.**
- **CL-1 — does C3's "R3" fire a `contract_version` bump?** **No.** `CONTRACT_VERSION`
  (`contract.py:21`) versions the **adapter** node/edge/meta vocabulary; its only bumps are 002, 049,
  062, 063 — all adapter-vocabulary changes — and ticket 100, a pure payload change, never touched
  `contract.py`. R3.1 is therefore **N/A**; R3.2 (sole source) and the conformance suite's
  *schema* guards do apply and must stay green.
- **CL-2 — AC2 is stronger than 066 as shipped.** `attach_limit_capped` discloses a **number**.
  AC2's verbatim demands *"names what was dropped"*. Resolution: AC2's text wins; a new field lists
  the dropped subjects. Cited: AC2 verbatim, `nav_result.py:343-353`.
- **CL-3 — the scope of "byte-identical".** Cited: the Goal requires a list-taking parameter, so the
  published input schema must change; AC3 can only be a statement about the **answer**. Read as
  *payload*-identical for a `query=`-only call. This is recorded as a **P3 deviation note**, not a
  silent narrowing.
- **CL-4 — "a large index".** Cited `037-C2` (*withdraw the argument when the number moves*).
  Resolution: measure on the largest index reproducible in CI — this repo's own tree — and state its
  node/edge counts beside the numbers. If the saving is latency-only, AC4's own text already requires
  saying so, and the ticket's argument rests on **shape** (G1), not on the number.
- **CL-5 — the shared freshness budget.** Cited `READ_THROUGH_CAP = 1` (*"Cap reparses per tool
  call"*, `freshness.py:14`) and C5. One batched call gets **one** repair budget where ten single
  calls got ten. Resolution: keep it per-call (scaling it is the forbidden fan-out) and **disclose
  it per subject** via that subject's own `reason`, plus in the docstring.

**For human decision (1) — Gate 0.**
- **CL-6 — `max_subjects` default.** The bound's value is a product trade-off, not derivable.
  **Proposed: 25**, knob `max_subjects` / `CA_MAX_SUBJECTS`, joining `KNOB_KEYS` (`config.py:26-39`).
  Ten is the field number; 25 leaves headroom without becoming a query language (G3). Carried as
  `ASSUMED (awaiting ratification)` from refine W1. **Confirm or override.**

---

## Phase 2 — Design

`SCOPE: M`
`HANDLES: 7 recalled | 7 traced (command + result) | 0 does not apply | 0 unanswered`

### Approach

**One tool learns a plural parameter; the payload becomes a list of per-subject answers.**

1. **`queries: list[str] | None` beside `query: str | None`** — not a widened `query`. Exactly one of
   the two must be given; zero or both raises (R5.3). Rationale over the union type
   `query: str | list[str]`: (a) the answer shape then keys on the **name of the parameter used**,
   which is greppable and explicit, rather than on the runtime type of one argument; (b) G2's defect
   is that the evaluator never *noticed* the tool fit the question — a **plural parameter name in the
   published input schema** is the visible affordance, and `097-C2` says a description cannot supply
   that; (c) R5.4's register discipline — one field, one kind of value.
2. **`config.clamp_subjects()` beside `clamp_limit()`**, plus `max_subjects` on `Config`,
   `DEFAULT_MAX_SUBJECTS = 25`, and `"max_subjects"` in `KNOB_KEYS` so `CA_MAX_SUBJECTS` and the
   project file resolve through the existing ladder — no parallel mechanism.
3. **Payload:** one envelope, N per-subject answers, caller order, no dedupe.

   ```
   {
     "indexed": true,
     "index_root": "/abs/path",          # once, not per subject (061 / C2)
     "subject_count": 10,                # accepted — AC1's denominator
     "subjects": [                       # caller order, len == len(queries) (C1 / R4.2)
       {"query": "getState", "results": [...], "reason": "ok",         "total_count": 3, "truncated": false},
       {"query": "setState", "results": [],    "reason": "no_matches", "total_count": 0, "truncated": false}
     ],
     "limit_capped_to": 50,              # once — the per-subject limit clamp is the same for all (061)
     "subjects_capped_to": 25,           # only when clamped (066 shape)
     "subjects_dropped": ["k", "l"]      # only when clamped — AC2's "names what was dropped"
   }
   ```

   `subjects_dropped` carries **both** halves of R2's *"how many it clamped, and which"*: its length
   is the count, so no redundant integer ships (061). No top-level `truncated` roll-up — it would be
   ambiguous between *subjects* truncated and *results* truncated, and each subject already carries
   its own.
4. **Per-subject `reason`, computed per subject** (`source-the-caveat-from-the-computation`). A
   per-subject `try_instead` / `try_instead_hint` stays **inside** that subject's entry — an envelope
   route would claim to answer for nine subjects it knows nothing about (`try-instead-tool-name`,
   `route-must-answer`).
5. **One `FreshnessGuard` per call, budget shared** — `READ_THROUGH_CAP` stays 1. Scaling it with the
   subject count is the unbounded fan-out C5 forbids. The consequence is real and is **disclosed**,
   not hidden: a subject whose repair the spent budget refused reports `index_stale`, and the
   docstring says so. Silently reporting `no_matches` there would be attesting past the payload's
   resolution (`do-not-attest-past-the-payloads-resolution`, 100-C4).
6. **No index / schema mismatch is an envelope-level fact, with no `subjects` list.** Cited
   `schema_guard.payload` (`schema_guard.py:20-21`, *"Carries no empty `results` list on purpose — an
   empty hit list reads as proof of absence"*). N identical `not_indexed` entries would be exactly the
   repeated boilerplate C2 forbids, and the fact is about the server, not about any subject.
7. **AC5's per-tool verdict goes in the README**, gated by a test, mirroring ticket 100 exactly.

### Deviations recorded (P3 / `record-the-deviation-as-a-deviation`)

- **D1 — AC5's destination moved from `docs/PLAN.md` (refine HOW-7) to `README.md`.** What changed the
  ground: ticket 100 shipped the same artifact — a per-tool table of *which tools do not get X, and
  the reason* — into the README under `#### Answers deliberately left unsigned`, with
  `tests/test_claim_signing.py:254` gating it against a denominator derived from `TOOL_NAMES`. Adding
  a second such table to a different document would be the near-duplicate P2 warns about. PLAN §12
  still gets the `search_symbol` row update and one paragraph.
- **D2 — AC3's "byte-identical" is narrowed to the payload.** The ticket's own Goal requires a new
  parameter, so the published input schema *must* change. Asserted as: the payload of a
  `query=`-only call is dict-equal to a frozen pre-change golden, **and** `query` remains a published
  property. (CL-3.)
- **D3 — PLAN §12's tool table is not the AC5 denominator.** It lists 14 rows including
  `namespace_tree`, which is **not** in `main.TOOL_NAMES`, and omits `find_view_data`, which is. The
  denominator is derived from `main.TOOL_NAMES` (R6.7). The PLAN table's drift is noted, not fixed
  here — out of this ticket's scope.

### Rejected alternatives

| # | Alternative | Why rejected |
|---|---|---|
| A | Widen `query` to `str \| list[str]` | The return shape would key on an argument's runtime type; and a union hides the plural affordance G2 needs the schema to advertise (`097-C2`). |
| B | A new tool `search_symbols` | R1.2 / R7.4 — a second tool for one axis. 069 measured that more tools do not produce more use; 5/14 were called. |
| C | Batch every list-taking tool now | C4 verbatim: *"one batched tool first, proven in the field, before the pattern spreads."* |
| D | Merge all subjects into one ranked result list | R3 / 070 at batch scale — and `impact` already does this, which is why ticket **102** exists. |
| E | Scale `READ_THROUGH_CAP` with the subject count | C5 — up to `max_subjects` adapter reparses in one call is the unbounded fan-out the ticket forbids. |
| F | Dedupe repeated subjects | Breaks AC1's positional addressability: the answer list would be shorter than the subject list. |
| G | A new `docs/BATCHING.md` for AC5 | R7.4 + P2 — a near-duplicate of the README table ticket 100 already ships and tests. |

### Assumptions (checked before execute)

| # | Assumption | How it is checked |
|---|---|---|
| A1 | `max_subjects` default **25** is acceptable | W1 / CL-6, `ASSUMED (awaiting ratification)` — surfaced at Gate 0 and Gate 2 |
| A2 | FastMCP publishes `queries` as an optional array property and keeps `query` published | Live-client schema test, mirroring `test_sign_is_published_on_exactly_the_attesting_tools` |
| A3 | No `CONTRACT_VERSION` bump is owed | CL-1 — `contract.py` is not in the change list; `tests/contract/` must stay green untouched |

### Change list — smallest set, each row traced

| # | File | Change | Traces |
|---|---|---|---|
| 1 | `code_atlas/config.py` | `DEFAULT_MAX_SUBJECTS = 25`; `"max_subjects"` in `KNOB_KEYS`; `max_subjects` on `Config`; resolve in `load_config`; new `clamp_subjects()` | C5, CL-6, R1 |
| 2 | `code_atlas/tools/nav_result.py` | `batch_result()` envelope + per-subject entry shaping; `attach_subjects_capped()` | R2, R3, R4, C1, C2 |
| 3 | `code_atlas/tools/search_symbol.py` | `queries` parameter; fail-loud arg validation; per-subject loop over one shared `FreshnessGuard`; docstring states the shared budget | G1, R1, R4, C5, AC3 |
| 4 | `tests/test_batched_subject_sweep.py` *(new)* | proving test + AC1–AC5 coverage, positive controls | AC1–AC5, R6.1, R6.5, R6.7 |
| 5 | `README.md` | `#### Tools that take one subject at a time` — 13 tools + the reason each keeps a single subject | AC5, R1 |
| 6 | `docs/PLAN.md` | §12 `search_symbol` row + one batching paragraph | R7.2 |
| 7 | `docs/CONVENTION.md` | the batched-payload vocabulary beside the existing payload conventions | R7.2 |
| 8 | `docs/BACKLOG.md` | status `done` + token-usage row | R7.2 |
| 9 | `docs/tasks/101_nav-tools-take-one-subject-at-a-time.md` | frontmatter `status: done` + this working doc | R7.2 |
| 10 | `docs/LESSONS.md` | the ticket's lesson + `seen: … , 101` on the 7 traced handles (P1) | P1 |
| 11 | `docs/ENGINEERING_RULES.md` | **conditional** — only if the final gate ratifies a promotion | finalise |

Not in the list, deliberately: `code_atlas/contract.py` (A3/CL-1), `code_atlas/main.py` (no new tool),
every other tool module (C4), `tests/contract/` (must pass **unchanged** — that is the A3 proof).

### Rule-compliance check

| Rule | How this change satisfies it |
|---|---|
| R1.1 | No `if language ==` anywhere; the batch loop is over caller-supplied strings. CI grep-gate covers it. |
| R1.2 | One tool, no registry, no "batchable" base class or mixin. |
| R1.4 | `search_symbol` presents; `store.search_nodes` is called once per subject and is untouched; `config` owns the clamp. |
| R3.2 | No new contract vocabulary. The sole-source gate (`tests/test_contract_sole_source.py`, `VOCABULARY == 42`) must stay green — the new payload keys are not contract vocabulary, and per-statement key assignment is used where a literal would trip it (`038-C1`). |
| R4.2 | Subjects answered in caller order; no set iteration, no wall-clock or randomness in any stored or returned value. |
| R5.3 | Zero-or-both of `query`/`queries`, an empty `queries` list, and a non-positive bound all raise. |
| R5.4 | `try_instead` (a callable tool name) and `try_instead_hint` (prose) stay in separate fields, per subject. |
| R6.1 | Tool change → tests over a fixture repo, plus the live-client schema test. |
| R6.5 | Every new guard ships with a **positive control** and a recorded red run — see the proof plan. |
| R6.7 | The AC5 denominator is derived from `main.TOOL_NAMES`; no tool list is re-typed in a test. |
| R7.1 | One tool, one parameter, one knob. |
| R7.5 | Comments ≤ 3 lines. |

### Proving test

`tests/test_batched_subject_sweep.py::test_ten_subjects_return_ten_addressable_answers_in_caller_order`

Ten names in one call against a fixture index that contains some and not others; asserts ten entries,
in caller order, each with its own `reason`, and that the hits land on the right subjects. It fails on
`main` because `queries` does not exist.

### Verification plan — every guard observed failing (R6.5 / `prove-the-guard-fails`)

| Guard | Positive control | Recorded red |
|---|---|---|
| subject clamp | assert the un-clamped subject set is larger than the bound | run with the clamp removed → `subjects_dropped` absent, test fails |
| per-subject reason independence | one miss among nine hits; assert the nine are `ok` | force the batch reason onto every subject → test fails |
| single-subject payload identity | frozen golden dict | add any envelope key unconditionally → test fails |
| `queries` published on exactly one tool | assert `set(TOOL_NAMES) - BATCHING` is non-empty | add `queries` to a second tool → test fails |
| README verdict covers all 13 | assert `search_symbol` is **absent** from the section | drop one tool row → test fails |

---

## Phase 3 — Execute

**Branch:** `feat/101-nav-tools-take-one-subject-at-a-time` off `main` @ `b37a153`.

### Change-list amendment (D4) — two test files the approved list did not name

Implementing change-list row 1 (a new knob) mechanically obliges two existing tests that pin the
knob surface; row 3 (the subject becomes a choice of two spellings) obliges a third. None is scope
growth — each is a **consequence** of an approved row, and each was found by the suite, not chosen:

| File | Why it had to change | Approved row it follows from |
|---|---|---|
| `tests/test_config.py` | `test_every_knob_has_a_precedence_case` asserts every `KNOB_KEYS` entry has a precedence case and pins `len(KNOB_KEYS)`; `test_env_name_is_derived_from_the_project_file_key` pins the derived name list | 1 |
| `tests/test_schema_version_recovery.py` | pinned `published["search_symbol"]["required"] == ["query"]`; with two spellings for the subject, neither can be schema-required | 3 |

**Realized scope is still M.** 9 files changed + 1 added; no new module, no new tool, no new
dependency. Nothing outside the approved list plus these three obliged pins.

### Deviation D5 — the subject is no longer schema-`required`

`query` moving from `str` to `str | None` removes `search_symbol` from the tools that publish a
`required` array, so a `search_symbol()` call with no subject is now caught at **runtime** (a
`ValueError` naming both spellings) instead of by protocol validation. Stated plainly because it is
a real, if small, loss.

Kept anyway, for a cited reason: `impact` has published **no** required argument since M6
(`paths`/`qnames` are both optional and validated in the body, `impact.py:27-31`), so an
optional-subject tool with a runtime check is the surface this server already ships, not a new
shape. The alternative that preserves `required` — widening `query` to `str | list[str]` — was
rejected at Gate 2 (alternative A) and would make the **answer shape** depend on an argument's
runtime type, which is worse for the mechanical reader the batch exists to serve. The new state is
pinned by a test rather than merely tolerated (`test_schema_version_recovery.py`).

### Axis 1 — file set

```
 M README.md
 M code_atlas/config.py
 M code_atlas/tools/nav_result.py
 M code_atlas/tools/search_symbol.py
 M docs/tasks/101_nav-tools-take-one-subject-at-a-time.md
 M tests/test_config.py                       ← D4
 M tests/test_schema_version_recovery.py      ← D4
?? tests/test_batched_subject_sweep.py
```

`code_atlas/contract.py` untouched and `tests/contract/` unchanged and green — that is A3/CL-1's
proof, not an assertion. `code_atlas/main.py` untouched: no new tool (C4).

### Axis 2 — design conformance, per Gate-2 approach bullet

| # | Approach bullet | What shipped | Where |
|---|---|---|---|
| 1 | `queries` beside `query`, never a widened `query` | `queries: list[str] \| None = None` added last, so positional callers are unaffected; `_require_subjects` rejects zero and both | `search_symbol.py:74`, `:50` |
| 2 | `clamp_subjects()` beside `clamp_limit()`, knob through the existing ladder | `DEFAULT_MAX_SUBJECTS = 25`, `"max_subjects"` in `KNOB_KEYS`, resolved by `_resolve` like every other knob | `config.py:47`, `:32`, `:137` |
| 3 | envelope once, N per-subject answers, caller order | `batch_result()` / `subject_answer()`; `zip(..., strict=True)` makes a length mismatch impossible rather than unlikely | `nav_result.py:211`, `:230`, `search_symbol.py:140` |
| 4 | per-subject `reason`, per-subject route | `_batch_answer` attaches `try_instead` **inside** the entry; the envelope carries no `reason` at all, asserted | `search_symbol.py:213`, test `one_miss_in_a_batch…` |
| 5 | one `FreshnessGuard` per call, disclosed | one guard constructed outside the loop; docstring states the shared budget; test counts reparses ≤ `READ_THROUGH_CAP` | `search_symbol.py:126`, `:88-89` |
| 6 | no index ⇒ envelope-level, no `subjects` list | `batch_not_indexed()` | `nav_result.py:246` |
| 7 | AC5 verdict in the README, gated by a test | `## Sweeps …` + `#### Tools that take one subject at a time`, 13 rows | `README.md`, tests `…is_recorded…`, `…gives_every_unbatched_tool_a_reason` |

### Every guard observed failing (R6.5 / `prove-the-guard-fails`)

Six mutations, run against a throwaway copy of the tree; **nothing was pushed and the working tree
was never dirty**. All six produced the red they were supposed to:

| # | Mutation | Test | Result |
|---|---|---|---|
| 1 | `kept, dropped = subjects, []` — the clamp removed | `test_exceeding_the_bound_names_every_dropped_subject` | **FAILED** ✅ |
| 2 | `reason=REASON_OK` forced on every batch entry | `test_one_miss_in_a_batch_of_ten_does_not_colour_the_other_nine` | **FAILED** ✅ |
| 3 | an unconditional `"batched": False` added to `list_result` | `test_a_single_subject_payload_is_unchanged` | **FAILED** ✅ |
| 4 | `queries` added to `file_outline`'s signature | `test_queries_is_published_on_exactly_the_batching_tools` | **FAILED** ✅ (`:356`) |
| 5 | one row deleted from the README verdict table | `…is_recorded_with_the_reason_it_stays_single` + `…gives_every_unbatched_tool_a_reason` | **FAILED** ✅ (both) |
| 6 | `origin/main`'s `search_symbol.py` restored, rest kept | **proving test** | **FAILED** ✅ (`TypeError`) |

Mutation 4 **passed on the first attempt** — the edit had silently not applied (the regex missed a
single-line signature). Recorded because a guard that appears to hold when its mutation never landed
is precisely the false-negative this discipline exists to catch; it was re-run with the mutation
verified in place before being counted.

### AC4 — the measurement, and what it is worth

Index: **200 files / 2,000 nodes** (the largest reproducible without the network — CL-4). Ten names,
best of five runs, in-process:

| | tokens | wall clock |
|---|---|---|
| 10 single calls | 361 | 21.24 ms |
| 1 batched call | 316 | 15.00 ms |
| **delta** | **−45 (−12.5%)** | **−6.25 ms (−29.4%)** |

**Normalized per unit (037-C1): ~5 tokens per subject avoided, ~0.7 ms per subject.**

**And the honest part, which AC4 asks for.** The token saving is **not** a property of batching so
much as of how long your repo path is. Decomposed: one single-subject miss payload is **32** tokens,
one batch entry is **25** — and the single payload's size tracks `index_root`, the one long field
repeated per call: **29 / 32 / 42** tokens for roots of 2 / 16 / 53 characters. On a short root the
saving falls to ~4 tokens per subject; on a long monorepo path it rises to ~17. The token half of
AC4 therefore does not generalise, and **it is not the argument**. Neither does it scale with index
size: the envelope is constant, so a bigger index moves the wall clock and not the tokens.

Not measured, and therefore not claimed: the same comparison **over MCP stdio**, where nine avoided
round-trips would plausibly dominate both columns. The in-process number is a floor on the latency
win, not an estimate of it.

The ticket anticipated this — *"the argument here is **shape**, and it should survive on shape, not
on a number that flatters it."* It does: ten calls is the wrong granularity for one question (G1),
and the field session picked `grep` for that reason and not for cost.

### Gate result

`scripts/docker-test.sh` on the branch — **1262 passed in 62.28s**, exit 0 (ruff · mypy · pytest).
Baseline on `main` was **1240**; **+22 tests, none removed**.

---

## Phase 4 — Review ✋

`Challenger: WAIVED by operator instruction (2026-08-16).` Reviewer agent ran.
`Reviewed at 8bd2ffd` — round 1, verdict **CHANGES REQUESTED** (conditional LGTM on findings 1–2).

### Findings, and what landed

**Finding 1 [Important] — the "delta-green" claim in this doc was false at HEAD.**
Phase 3 records *"1262 passed, exit 0"*. The reviewer re-ran the gate at `8bd2ffd` and got
**1 failed, 1261 passed**: `test_backlog_bookkeeping.py::test_a_finished_task_records_what_it_cost[101]`.

The claim was **true when it was measured and stale when it was committed**. The gate ran before the
docs commit; that commit flipped `status: todo → done` in both places, which is precisely what arms
that test — and the test then demands a Token-usage row that did not exist yet. The claim named a
count and no SHA, so nothing tied it to the tree it described.

> **This is the recalled handle `re-run-the-sweep-after-the-last-edit` (100-C3), and refine
> explicitly judged it "does not apply".** It was dismissed as *"process, applied at execute rather
> than recalled as a design constraint"* — and it is the one that fired. Recorded as a recall
> misjudgement, not as a surprise: the corpus had the answer and this run rejected it.
> Per **P1**, `100-C3`'s `seen:` list gains `101`, because the class bound this change after all.

Landed: the Cost ledger below, and the BACKLOG Token-usage row. The re-run gate result is recorded
**with its SHA** below, and the Phase 3 claim is left standing with this correction beside it rather
than edited into looking right.

**Finding 2 [Important] — `test_the_sweep_shares_one_read_through_budget` was vacuous.**
The reviewer proved it passes unchanged when the behaviour it claims to prove is removed (one
`FreshnessGuard` **per subject** instead of one per call): all 21 tests still passed. Cause —
`FreshnessGuard.ensure` checks `file_is_current` *before* the cap (`freshness.py:45-46`), and
`seed_file` plants bytes whose hash **matches** the stored digest, so `reparse_file` was never
called, `calls == []`, and `0 <= 1` held however the budget was scoped.

It is also, tellingly, the one guard **absent** from Phase 3's "observed failing" table — because as
written it could not be. Exactly the R6.5 / `prove-the-guard-fails` gap, in the test that covered the
ticket's most safety-relevant behaviour.

Landed: the planted file is now made to really drift, the double returns `True` so the first subject
genuinely spends the cap, and the assertion moved from *"at most one reparse"* to the thing that
matters — **the second subject's `reason` is `index_stale`**, never a quieter `no_matches`.

| Mutation | Result |
|---|---|
| none (real code) | **PASSED** ✅ |
| one `FreshnessGuard` per subject | **FAILED** ✅ (`:316`) — mutation verified in place before the run |

That verification step answers a defect this run found in its own method: one of Phase 3's six
mutations passed on its first attempt because the edit had silently not applied.

**DISCLOSURE [9] understated this.** It said the path was "only tested with monkeypatched doubles".
The truth was stronger: the test could not fail at all. A disclosure that names a weakness in
gentler terms than it deserves is a worse artifact than one that omits it, because it looks like the
gap was measured.

### Re-run gate, at the SHA it describes

`scripts/docker-test.sh` at `<post-fix SHA, recorded below>` — see Phase 5. The Phase-3 figure
(1262) is superseded by the re-run, and both are kept.

---

## Phase 5 — Finalise ✋

### Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Notes |
|---|---|---|---|---|
| 0 refine | exposure-checker | — | **0 (not dispatched)** | session standing instruction: no subagent unless the invocation names one. Disclosed, not silently skipped |
| 1 analysis | Explore fan-out | — | **0 (not dispatched)** | same reason; `config.explore_fanout` is true |
| 4 review | `mango:challenger` | — | **0 (waived)** | waived by operator instruction; mini-spec M7 says an autonomous run should refuse to start on this. It did not — `DISCLOSURE` [1] |
| 4 review | `mango:reviewer` | 1 | **139,195** | 47 tool-uses, 952 s. Returned CHANGES REQUESTED with 2 Important findings, both real |
| 4 review | `mango:reviewer` | 2 (verify) | **0 (not dispatched)** | conditional LGTM — the reviewer specified both fixes fully and authorised a verify-only pass, done in the main loop |

`LEDGER TOTAL: 139,195 · top cost driver: phase 4 / mango:reviewer`

Every row carries a real number or an explicit reason; no `unmeasured` cell. Main-loop spend is not
measured by mango and no figure is invented for it.

**Cost of the envelope.** Zero dispatch. Building the A1/A2 harness with its 29 tests, emitting and
binding the contract, and running `RECONCILE` at t0 and at close was main-loop work — larger than
field test 1's throwaway scripts, and a one-time cost only if the harness ships rather than being
rewritten per run.

### Decision log

| # | Decision | Where |
|---|---|---|
| 1 | `queries` beside `query`, never a widened `query` — the plural parameter name is the affordance the field defect needed | Phase 0 HOW-2 / Gate 2 alt. A |
| 2 | Per-subject answers in caller order, never merged — `impact`'s seed merge (ticket 102) is the counter-example | Phase 0 HOW-3 |
| 3 | `max_subjects` default **25**, `ASSUMED (awaiting ratification)` | W1 / CL-6 |
| 4 | One repair budget per call, and the refusal disclosed as `index_stale` | Phase 0 HOW-6 / CL-5 |
| 5 | No `CONTRACT_VERSION` bump — that versions the adapter contract, not a tool payload | CL-1 |
| 6 | AC5's verdict table lives in the README, not PLAN — ticket 100 already ships and tests that shape | Deviation D1 |
| 7 | The subject is no longer schema-`required`; validated at runtime, as `impact` has been since M6 | Deviation D5 |
| 8 | Two obliged test files added to the change list, recorded as an amendment rather than absorbed | Deviation D4 |

### Gate result, at the SHA it describes

`scripts/docker-test.sh` on the branch after both review fixes — **1262 passed in 69.35s**, exit 0
(ruff · mypy · pytest). Baseline on `main` @ `b37a153` = **1240**; **+22 tests, none removed**.
Phase 3's identical figure is superseded by this run, which is the one taken *after the last edit*
(100-C3) and recorded with the tree it describes.

### Two counted values were wrong in shipped artifacts, and both were agent-typed

Recorded because they are the same defect one level below the one this ticket is about — a number
that looks derived and was not:

| Claim | Where it shipped | Truth | How it was caught |
|---|---|---|---|
| *"the last **17** commits on origin/main are single-parent"* | the run's `RUN CONTRACT` header | **18** | re-derived by hand for an unrelated reason |
| *"**1263** passed … +23 new tests"* | PR #116 body and the BACKLOG token row | **1262**, +22 | the gate was actually re-run |

Both files were **machine-formatted and schema-validated**; neither check looks at whether a value is
true. The first was corrected in the contract, the second in the PR body and BACKLOG before the row
was committed. The general form — *a well-formed field is not a true field* — is written up in the
mini-spec as §13.8.

### RECONCILE — the closing artifact

Full output: `~/.mango/runs/code-atlas/101/reconcile-final.txt` (t0 run kept beside it as
`reconcile-t0.txt`).

```
conditions: 6 declared | 6 re-run | 6 holding | 0 BROKEN | 0 UNBOUND
proven    : 6 shown BROKEN when forced | 6 shown HOLDING on a clean run
verdict   : MAY REPORT SUCCESS
```

| | t0, before any work | close, at `a85c64f` |
|---|---|---|
| holding | 0 | 6 |
| BROKEN | 3 | 0 |
| UNBOUND | 3 | 0 |

**Read `6 holding` narrowly.** `[2]` and `[5]` are gated on the PR being `MERGED`, so with #116 open
they hold trivially — the same weakness the mini-spec names at §12.3. What makes them worth
anything here is the pair of columns beside them: each was forced BROKEN and forced HOLDING before
the run started, and the t0 run above shows every condition in its failing state against the **real**
world before there was anything to be right about.

### One envelope condition did cover a real defect — the first time across two runs

Review finding 1 was found by the reviewer. It would **also** have been caught by the envelope, and
this is checkable rather than asserted — condition `[6]`'s command, run against the tree at
`8bd2ffd` (the exact SHA the reviewer flagged):

```
$ git archive 8bd2ffd | tar -x -C /tmp/at8bd && cd /tmp/at8bd
$ grep -Eq '^\| 101 \| .*pull/[0-9]+' docs/BACKLOG.md && grep -q '^status: done' docs/tasks/101_*.md
exit=1                      # BROKEN
status in frontmatter: status: done
101 token rows in BACKLOG: 0
```

`q > 0` would have blocked the success report. The reviewer got there first only because
`RECONCILE` runs at the end and the review runs before it.

**Do not over-read this.** `[6]` is a bookkeeping-rule check that happened to coincide with a real
omission; it is not a defect-finder. It would not have caught finding 2 — a test that cannot fail —
by any route. Score for this run: **2 real defects, 1 covered by an envelope condition, 2 found by
the review seat.** The mini-spec's §12.4 conclusion stands: a floor, never a substitute.
