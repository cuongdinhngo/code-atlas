---
id: 244
slug: no-channel-announces-a-capability-change
title: 'Every honesty mechanism this project has built delivers in a response, so a user who has already concluded that a question is unanswerable never calls again and never learns the fix shipped — three instances in one session, and the only regression class the test suite structurally cannot catch, because nothing in the repo goes red'
phase: 1.5b
milestone: Adoption
status: done
depends_on: [243, 221, 099, 100]
---

## Why this exists (field retro round 17)

The project's answer to a false zero has been, consistently and correctly, **to make the answer
honest**: `reason` on every empty result, `try_instead`, `truncated`, `cross_language`,
`server_stale_process`. The round-17 retro's §6 *What to keep* is that list, and §4 argues its value
against a shell tool that reports 14 matches as 0 with no signal.

Every one of those mechanisms is a field in a response. A response reaches a caller. It does not
reach a **non-caller**, and a user who has concluded that a class of question is unanswerable is a
non-caller by definition. The conclusion is self-sealing: obeying *"don't ask X"* generates no
evidence against itself, so it survives every fix to X indefinitely.

This is a regression class with no guard, and it cannot have the usual kind: when a shipped
capability goes unused because the user's model of the tool is stale, **nothing in this repo turns
red**. The suite is green, the gate is green, and the capability is worth zero.

## Evidence — three instances in one session

1. **A memory that over-generalised, and cost the session's most valuable question.** An earlier
   round measured `find_callers` on a T-SQL procedure returning 0 against a real 42 and recorded
   *"grep is primary for SQL callers and writers."* Round 17 did not call code-atlas about T-SQL at
   all, and its retro counted that as a saving. The memory was right about **callers** — re-measured
   2026-09-11, the same shape still has 0 linked inbound edges (what 221/238 changed is that the zero
   is now *disclosed*, not that it became non-zero). It was wrong about **T-SQL**: the question the
   session actually needed — how two signatures differ — was in the index the whole time
   ([242](242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md)).
   Nothing distinguished "this relation is unmodelled" from "this language is out of scope", so one
   measured miss retired a whole language.
2. **A shipped capability with no name to ask for.** `find_mirror_subtrees` landed with 115 and is
   reachable through `architecture_overview` and `subtree_dependencies`, but is not itself a tool
   name. Round 17's highest-ranked wish — *"`diff_twin` for the ALPHA/BETA convention … highest value by
   a distance"* — is half of what already ships.
3. **A predicate one `detail_level` out of reach.** [243](243_the-capability-predicate-221-relies-on-is-attached-at-verbose-only.md),
   which is this ticket's narrowest case and is ticketed separately because it is fixable on its own.

Five rounds of this backlog have recorded roll-out as the binding constraint and deliberately kept it
off the board because *"this backlog accepts only code"*. Instances 1-3 are the counter-argument: the
binding constraint has a code-shaped face, and this ticket is only that face.

## Scope

**Cheapest mechanism first, and prove it is needed before building the next one.** This ticket is
deliberately allowed to close having shipped one small thing.

- **Establish what a reader can already learn without calling a nav tool.** `get_index_status` is the
  session's first call and the only channel that reaches a non-caller. Inventory what it says today
  about *what this index can and cannot answer* — as opposed to how big and how fresh it is.
- **Name the unit.** A capability statement is not a statistic: *"CALLS across php→sql: not
  modelled"* is actionable, `linked: 0` is a number the reader must interpret. 231's
  `capabilities_by_language` stamp and 204's `cross_language` census are both already on disk; decide
  whether the unit is derived from them or declared beside them.
- **Decide the delivery, cheapest admissible option and no more.** Candidates, to be accepted or
  rejected in writing: a field at `standard` (243's shape); an entry in `next_tool_suggestions`; a
  line in the `claim` string (100); the write-time signal seam (099/240). Rejecting the larger ones
  is a deliverable.
- **Out of scope, explicitly:** notifying anybody, versioning the tool surface, anything that reaches
  outside the process, and any LLM-written prose (R4). Also out of scope: a change to the memory or
  documentation of any consumer repository — this ticket buys a channel, not a correction.

## Constraints

- **R4 / R4.1** — deterministic, no network, no LLM. A capability statement is derived from stamps
  the build already wrote.
- **061 / 223 / test_agent_chain_budget** — the first call of every session is the most expensive
  place in the product to add a sentence. Whatever ships here is measured and bounded, and a
  single-language index with nothing to disclose must stay byte-identical.
- **R5.2 / R5.6** — never claim a capability the stamp cannot vouch for; a pre-stamp index says it
  cannot tell.
- **R1.2 / YAGNI** — one channel. Do not build a capability registry, a subscription, or a
  negotiation.
- **R7.6** — if the honest answer is that this belongs in a doc rather than a payload, say so and
  prune rather than add.

## Acceptance criteria

- A written inventory of what `get_index_status` tells a non-caller today about answerability, and
  the gap named in one sentence.
- One mechanism shipped, with every rejected candidate rejected in writing.
- The added cost on the cheap path measured; byte-identical output asserted for an index with nothing
  to disclose.
- A test that fails if the mechanism stops reflecting a stamped capability change — the guard this
  regression class has never had.
- Instances 1 and 2 above re-checked against the shipped mechanism: would a session reading only the
  first call now avoid each conclusion? Answer in the task file, with the payload quoted.

## References

Field retro round 17 (2026-09-11, maintainer-local) §2.6, §4, §5, §6. Related:
[243](243_the-capability-predicate-221-relies-on-is-attached-at-verbose-only.md) (the narrow
instance), [242](242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md)
(the capability instance 1 never found),
[221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) /
[238](238_the-honest-zero-predicate-is-gated-on-the-zero.md) (the fixes that shipped and went
unread), [099](099_write-time-signal-seam.md) /
[240](240_the-read-time-signal-is-offered-to-codex-and-not-to-claude-code.md) (the existing
out-of-band seams), [100](100_claim-signing-output-mode.md) (the `claim` line the same retro used
verbatim), [065](065_empty-answer-cannot-explain-itself.md) (where the in-band line of work began).
PLAN §19's evidence filter classes this finding as agent-subject — *"how an agent frames a task, when
it is receptive to information"* — which generalises by default and needs no second repository.

## Token usage

| Phase | Tokens |
|---|---|
| autorun (main-loop) | unmeasured (host surfaces no usage block) |

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 244 — No channel announces a capability change (working doc)

- **Ticket:** 244 · local file `docs/tasks/244_no-channel-announces-a-capability-change.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 touched files under UI paths
- **TIER:** full
- **BASELINE:** green — related suite 28 passed / 3 skipped on untouched HEAD; no baseline exclusions
- **INPUT KIND:** ticket (not epic)

## Session status

- **Last updated:** 2026-09-11
- **Current phase:** finalise
- **Next action:** push + open PR
- **Blocked on:** none
- **work_doc_mode:** embed
- Run: `/mango:autorun 244 --no-reviewer`; challenger ON.
- Branch: `feat/244-no-channel-announces-a-capability-change`
- Worktree: `/tmp/code-atlas-wt-244`
- Contract: `.mango/run-contract-244.txt`

---

## Phase 0 — Refine

`PREMISE: 12 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: ticket locks inventory+unit+delivery-decision+one-mechanism ACs and constraints (R4/061/R5.6/R1.2/R7.6); candidate fork (field / suggestion / claim / write-time seam) is an in-design HOW choice under handover authorisation — no WANT left open.

**PREMISE detail.** Present: `get_index_status`, `capabilities_by_language` / `stamped_capabilities_by_language` / `CAPABILITIES_BY_LANGUAGE_KEY`, `cross_language`, `next_tool_suggestions`, `claim` (task 100), write-time signal seam (099/240), `find_mirror_subtrees`, tasks 243/242/221/238/231. **Ambiguous (surfaced, not blocking):** field retro round 17 (maintainer-local); private anchor monorepo session memories.

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `capability-signal-on-the-first-call-channel` (243-C1) | 2 | handle | Yes — attach on the first-call channel |
| 2 | `do-not-attest-past-the-payloads-resolution` | 2 | handle | Yes — pre-stamp silence |
| 3 | `stamp-at-the-builder-not-the-wrapper` | 2 | handle | Yes — attach from `_status`, stamp already at build |

**Exposure-checker:** skipped (refine skip: yes).

---

## Inventory — what `get_index_status` tells a non-caller today (AC1)

At default `standard`, a built index already reports size/freshness (`files`/`nodes`/`edges`/`staleness`/`server_*`), whole-graph `edge_health`, `parse_failures`, `dirty_indexed_files`, `unconfigured_adapters` (languages that could be wired), and — since 243 — a bounded `cross_language` census on multi-language indexes. `next_tool_suggestions` only names `build_or_update_index` when stale/unbuilt. `claim` is opt-in (`sign=false` by default).

**Gap (one sentence):** nothing on the first-call channel names which *per-language adapter capabilities* (R1.6 flags already stamped by 231) this index can answer — so a reader can still conclude a language is "out of scope" when only a relation is unmodelled.

**Unit:** the stamped `capabilities_by_language` map (per-language R1.6 flags). A capability statement here is the flag map itself (e.g. `sql.params: true`), not a free-prose sentence — isomorphic to *"params captured for sql"* under R4, derived from the stamp already on disk (231), not declared beside it.

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Evidence · Scope · Constraints · Acceptance criteria) | 5 decomposed | ROWS: C=5 R=4 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why | honesty reaches callers only; non-caller never learns | Ship one first-call channel for stamped capabilities | inventory above | D1 | proving tests | ✅ |
| C1 | Constraints | R4/R4.1 deterministic, no LLM/network | Derive from build stamps only | stamp readers | D1 | stamp-read path | ✅ |
| C2 | Constraints | 061/223 cheap path bounded; nothing-to-disclose byte-identical | Omit when stamp absent/empty/all-false; measure delta | ticket | D1 | omit + budget tests | ✅ |
| C3 | Constraints | R5.2/R5.6 never claim beyond stamp | Omit pre-231 | store reader | D1 | `test_nothing_to_disclose…` | ✅ |
| C4 | Constraints | R1.2 YAGNI — one channel | No registry/subscription | ticket | D1 | single field | ✅ |
| C5 | Constraints | R7.6 prune rather than retell | PLAN cell only; no standing-doc retell | ticket | D3 | PLAN hunk | ✅ |
| R1 | Scope | Inventory + gap named | Written above | this doc | — | AC1 | ✅ |
| R2 | Scope | Name the unit | Stamp map derived from 231 | above | D1 | field name | ✅ |
| R3 | Scope | Decide delivery; reject larger in writing | Field at standard; reject suggestion/claim/write-time | design | D2 | rejected alts | ✅ |
| R4 | Scope | OOS: notify, version surface, outside process, LLM, consumer memory | No such changes | ticket | — | untouched | ✅ |
| AC1 | AC | inventory + gap sentence | Written in Inventory | | — | this doc | ✅ |
| AC2 | AC | one mechanism + rejections written | Field; three rejects | | D2 | design + code | ✅ |
| AC3 | AC | cost measured; nothing-to-disclose byte-identical | delta ≤200 B; omit path | | D3 | budget + omit tests | ✅ |
| AC4 | AC | test fails if mechanism stops reflecting stamp change | plant+mutate stamp | | D3 | proving test | ✅ |
| AC5 | AC | instances 1–2 re-checked with payload quote | Written in Re-check | | — | this doc | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | inventory + gap | inventory section present | Y | greppable section | — |
| AC2 | one mechanism + rejects | field + rejected alts | Y | code + prose | — |
| AC3 | cost + byte-identical | delta 99 B fixture; omit tests | Y | numeric + key absence | — |
| AC4 | stamp-change guard | mutate meta → payload changes | Y | assertion | — |
| AC5 | instance re-check | written answers | Y | prose+quote (manual) | — |

## Inventory (universal)

- **Denominator / total N:** 1 (`get_index_status` attach path)

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| 1 | standard attach of capabilities_by_language | proving module | ✅ |

## Clarifications

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

- Self-resolved (with citation):
  1. Unit = stamped `capabilities_by_language` map (derived from 231), not free prose — R4 + ticket "decide whether derived from them or declared beside them"; cite `store.stamped_capabilities_by_language` / ticket Scope.
  2. Delivery = field at `standard` — mirrors 243's first-call pattern (`capability-signal-on-the-first-call-channel`); cite LESSONS 243-C1 + ticket candidates.
  3. Reject `next_tool_suggestions` / `claim` / write-time seam — suggestions name tools not flags; claim is opt-in (`sign`); write-time seam reaches outside this ticket's in-process channel (099 OOS for "notify"). Cite `_suggestions`, claim docstring, ticket OOS.
- For human decision: none

---

## Phase 1 — Analysis

- Root cause (enhancement / `config`): `capabilities_by_language` is stamped at build (231) and read by `read_symbol` / `class_diagram` / `find_callers`, but `get_index_status._status` never attaches it — so the only channel that reaches a non-caller cannot announce what the index can answer.
- Handler / blast radius: `get_index_status._status`; PLAN §12 cell; new proving module.
- `TRACK: backend — 0/0 touched files under UI paths`
- `SCOPE: S`
- `TIER: full`

`RULE SECTIONS: 8 applicable — 7 by change-type | 1 by recalled handle — R1.4 (change-type) ✅ tools present; store owns stamp · R1.6 (change-type) ✅ flags remain optional · R4.2 (change-type) ✅ stamp read not scan · R5.6 (change-type) ✅ pre-stamp silence · R6.1 (change-type) ✅ fixture proves attach/omit/mutate · R7.6 (change-type) ✅ PLAN cell updated · R1.2 (change-type) ✅ one field no registry · R5.6 (recalled handle) ✅ do-not-attest`

### BASELINE

Related suite on untouched code:

```
Ran at 1788c369cc32c1214160a1d8e204c7dffdf30e74
$ .venv/bin/python -m pytest tests/test_cross_language_at_standard.py tests/test_get_index_status_health.py tests/test_optional_field_capture.py tests/test_read_symbol_params.py -q --tb=no
..........s...s.....s..........                                          [100%]
28 passed, 3 skipped in 4.85s
```

`BASELINE: green` for the change-adjacent suite. No baseline exclusions.

- **Gate 1 status:** cleared (autorun closes on artifacts; `j = 0`)

---

## Phase 2 — Design

- **Approach.** Before the `standard` early return, call `_attach_capabilities_by_language`: read `stamped_capabilities_by_language()`, omit when stamp is None/empty or every flag is false, else attach a sorted copy under top-level `capabilities_by_language`. One meta read (R4.2). Update PLAN §12. Prove with `tests/test_capabilities_at_standard.py` including a stamp-mutation guard.

- **Rejected alternatives.**
  1. `next_tool_suggestions` entry — rejected: suggestions name servable tools; capability flags are not tools; inventing a hint like `read_symbol` for every `params:true` language is noisy and not the unit.
  2. `claim` line (100) — rejected: `sign` defaults off, so a non-caller who never opts in still learns nothing; wrong default for the first-call channel.
  3. Write-time signal seam (099/240) — rejected: ticket OOS ("notifying anybody", "outside the process"); this ticket buys an in-band channel.
  4. Free-prose answerability sentences — rejected: R4; the flag map is the deterministic statement form.

**Assumptions**

| Assumption | verified / novel-untested | Notes |
|------------|---------------------------|-------|
| `stamped_capabilities_by_language` is a meta read | verified — store.py:876+ | — |
| Omit when no True flag keeps empty fake adapters identical | verified — fixture stamp `{"fake":{}}` | AC3 |

**Smallest change-list**

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|--------|-----------|--------------|----------------|-----|
| Attach `capabilities_by_language` at standard with omit rules | `code_atlas/tools/get_index_status.py` | MCP docstring | G1,R2,R3,C1–C4 | 4/4 |
| Proving suite: attach, mutate, omit, single-lang, budget | `tests/test_capabilities_at_standard.py` | — | AC2–AC4 | 4/4 |
| PLAN §12 cell | `docs/PLAN.md` | R7.6 | C5 | 1/1 |
| Working doc + ledger/lesson/backlog at finalise | `docs/tasks/244_…`, TOKEN_LEDGER, LESSONS, BACKLOG | bookkeeping | finalise | — |

**Recalled type-2 handles**

| # | Handle | Answer |
|---|--------|--------|
| 1 | `capability-signal-on-the-first-call-channel` | traced — attach before standard return in `get_index_status.py` |
| 2 | `do-not-attest-past-the-payloads-resolution` | traced — early return when stamp None/empty/all-false |
| 3 | `stamp-at-the-builder-not-the-wrapper` | traced — reader only; stamp remains indexer/meta write |

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **Proving test:** `.venv/bin/python -m pytest tests/test_capabilities_at_standard.py::test_standard_carries_stamped_capabilities_by_language -q`

**Verification plan**

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|------------|----------------|--------------------|--------------|
| AC1 | docs | inventory section | n/a | ✅ |
| AC2 | logic | unit + design rejects | n/a | ✅ |
| AC3 | logic | unit + recorded delta | n/a | ✅ |
| AC4 | logic | unit (stamp mutate) | n/a | ✅ |
| AC5 | docs | re-check section | n/a | ✅ |

No real corpus configured. AC1–AC5 are not input-shape-dependent on a private corpus.

**Coverage-gap exclusions**

| Item | Risk tier | Why deferred | Follow-up | Expiry | Seen |
|------|-----------|--------------|-----------|--------|------|
| *(none)* | | | | | |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**AC3 measurement (recorded).** Fixture-scale `standard` delta with planted two-language caps = **99 bytes**. Empty/`{}`/all-false stamps omit (byte-identical to pre-field).

- Rollback: revert the branch.
- **Gate 2 status:** cleared (autorun closes on artifacts)

## Decision log

| When | Decision | Why |
|------|----------|-----|
| t0 | reviewer off, challenger on | `/autorun 244 --no-reviewer` |
| refine | skip: yes | AC + constraints locked; delivery fork is HOW under handover |
| design | field at standard; reject suggestion/claim/write-time/prose | first-call channel + R4 + OOS |

---

## Phase 3 — Execute

- **Branch:** `feat/244-no-channel-announces-a-capability-change`
- **Proving test added:** `tests/test_capabilities_at_standard.py::test_standard_carries_stamped_capabilities_by_language`

- **Verification sweep — BOTH axes.**
  - File axis: diff ⊆ approved list ✅ (`get_index_status.py`, proving module, `PLAN.md`, this ticket) · each hunk maps to a row ✅
  - Behaviour axis: field at standard when a True flag exists; omit otherwise; stamp mutation reflected — as approved

- **Design-conformance deviations:** none

- **Empirical output**

```
Ran at 34fbe1dd788af91559c0f9d635267a487c208fe6
$ .venv/bin/python -m pytest tests/test_capabilities_at_standard.py -q --tb=no
....                                                                     [100%]
4 passed in 1.23s
```

R6.5 red-before (attach call stripped; proving test present): AssertionError `assert 'capabilities_by_language' in {…}` — 1 failed.

### Re-check instances (AC5)

**Instance 1** (over-generalised "T-SQL out of scope"): a session reading only `get_index_status` at `standard` on an index that stamped `sql.params: true` now sees:
```
"capabilities_by_language": {…, "sql": {"params": true, "args": true, …}, …}
```
paired with 243's `cross_language.linked: 0` when crossings are unmodelled. That distinguishes "language in scope / signatures captured" from "CALLS across languages not modelled" — **yes, avoids the conclusion.**

**Instance 2** (`find_mirror_subtrees` has no tool name): this mechanism does **not** name onboarding helpers — no stamp exists for tool aliases. Rejected candidates (suggestion inventing `diff_twin`, claim, write-time) stay rejected. **No — instance 2 remains a tool-naming gap outside this one-mechanism close.**

---

## Phase 4 — Review

- **Reviewer:** waived (`--no-reviewer`) — no rule-book-grounded review exists
- **Challenger:** ON — ticket-blind on raw ticket + product diff (working doc excluded)

**Challenger report (round 1):** NOT CLEAN — 3 can't-tell on writing-only ACs (isolation) + soft finding (key-set vs byte-identical).
**Fix:** omit tests assert full payload equality (`empty == silent`).
**Challenger report (round 2):** 8 met · 0 not met · 3 can't-tell (writing ACs only, by isolation). Soft finding closed.
**Orchestrator reconcile:** inventory, rejected alternatives, and instance 1/2 re-checks are present in this embed working doc (AC1/AC2/AC5). Writing can't-tell under challenger isolation is expected for embed mode; code ACs clean → overall **clean (challenger only — REVIEWER: OFF)**.

- **Scope reconciliation:** diff ⊆ approved list (product paths + bookkeeping)
- **Proving test:** green (4 passed in module)
- **Clean?** `clean (challenger only — REVIEWER: OFF)`
- **Reviewed at** `060e59ad3fbbf5304b057447fa0b7a6404b1fdba`
- **Reviewed files:** `code_atlas/tools/get_index_status.py`, `tests/test_capabilities_at_standard.py`, `docs/PLAN.md`, `docs/tasks/244_no-channel-announces-a-capability-change.md` (working-doc path, exempt), `docs/LESSONS.md` (exempt), `docs/TOKEN_LEDGER.md`, `docs/BACKLOG.md`

### Review round 2 — maintainer review on PR #319

**Finding (accepted, fixed): the field answered for languages this index holds nothing of.** 231
stamps the capabilities of every adapter that *announced*, not of every language the graph covers,
so the map named each configured adapter regardless of the repo. Measured on the branch:

```
files written: lib/core.aa          (only the `fake` language)
stamp:         {"fake": {}, "second": {}}
covered:       fake
```

With the four shipped adapters the unfiltered field is **417 bytes / ~105 estimated tokens** — and
the same 417 bytes on a PHP-only repo, three quarters of it about languages the index cannot answer
about either way. That is the ticket's sharpest constraint (*"the first call of every session is the
most expensive place in the product to add a sentence"*) spent on a non-answer, and it is also the
wrong unit: 244's question is what **this index** can answer, not which adapters are installed.

**Fix:** scope the map to 173's covered-languages stamp, read through the existing
`tools/coverage.covered_languages` helper. An index with no coverage stamp (pre-173) is **not**
filtered — no stamp is not evidence of no coverage (R5.6). Two tests pin both halves.

**Not changed, recorded instead:** a *globally* all-false stamp is omitted, so on such an index a
measured "captures nothing" is indistinguishable from pre-231 silence. Unreachable today — every
shipped adapter declares at least one true flag, and `sql.modifiers: false` already rides the field
alongside its true siblings — and 061 covers the empty-map case. Worth revisiting only if an adapter
ever ships with no optional field at all.

**AC3 restated with the real number.** The recorded 99 B is fixture scale (2 languages, 3 flags).
Four-language worst case after the fix is 417 B; a single-language index pays only its own row.

```
$ scripts/gate.sh
20 passed · 0 failed · 0 skipped
GATE GREEN — all 20 checks passed
```

## Phase 5 — Finalise

- **Stale-review guard:** product files unchanged since `060e59ad3fbbf5304b057447fa0b7a6404b1fdba` at review; bookkeeping (this doc, lessons, ledger, backlog) is exempt.
- **PR draft:** from `.github/pull_request_template.md`.
- **Planned outward actions:**
  - [x] push branch — handover authorisation
  - [x] open PR via `gh` — handover authorisation
  - [ ] merge — NOT authorised
  - [ ] tracker transition — NOT authorised
- **Durable lesson:** bump `243-C1` `capability-signal-on-the-first-call-channel` `seen: 243, 244` (recurrence).
- **Revert path:** revert the branch / close the PR without merge.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

Falsify of `243-C1` / `capability-signal-on-the-first-call-channel`: still true — without `_attach_capabilities_by_language` before the standard early return, `test_standard_carries_stamped_capabilities_by_language` fails (R6.5 red-before). Routed to `docs/AGENT_BRIEF.md` as a proposed process brief candidate (recurrence-2); human ratification deferred to `/mango:promote` — not auto-written.

## Cost ledger

`LEDGER TOTAL: unmeasured · top cost driver: challenger×2 + main-loop`

| Phase | Tokens |
|---|---|
| refine→design→execute (main-loop) | unmeasured |
| challenger ×2 (dispatch) | unmeasured |
| reviewer | waived |

