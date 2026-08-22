---
id: 122
slug: exact-miss-shaping-discards-a-resolved-subject
title: '075 normalised the leading backslash for three tools; four `find_*` tools still decline over it — while holding the resolved qname in hand'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [075, 076, 065, 093]
---

## Why this exists (field retro round 6, 2026-08-21, 17-tool surface, anchor monorepo)

The evaluator asked `find_references` for a class using the same qname style that had just worked twice
on `read_symbol` — no leading `\`. It received:

```json
{"results": [], "reason": "name_not_qualified", "candidate_count": 1}
```

With the `\` prefixed, the same call returned **9 hits, 8 of them RESOLVED `EXTENDS`**. So the index
held the answer, knew there was exactly **one** candidate, and returned none of it.

**What it cost, and this is the number that matters.** After that one call the evaluator stopped
reaching for the index and used `grep` for every remaining question — **four tickets** of a five-ticket
session. One malformed subject, silently answered with an empty list, changed tool selection for the
rest of the session. The retro names it the most expensive thing that happened that round, above a
236 s index rebuild that cost nothing because it could be worked through.

## This is not a new defect class — it is [075](075_read-symbol-confident-zero-on-unnormalised-qname.md)'s scope, unfinished

075 is `done`, and its scope bullet reads:

> "**Normalise the subject qname before lookup.** A leading `\` is optional, everywhere a qname is
> accepted, **for every tool that takes one — not only `read_symbol`**. State the normalisation in one
> place; do not re-derive it per tool."
>
> "**Decide and record the sibling surface.** `read_symbol`, `file_outline`'s symbol arguments,
> `find_*` subjects, `impact`, `explain_path` — each gets an explicit verdict."

The shared place exists and works. `classify_missing_subject` (`nav_result.py:301`) returns four
statuses, and its own docstring states the intent verbatim:

> "a leading-anchor difference (`Ns\Sub\Enum` vs `\Ns\Sub\Enum`) resolves as one candidate"

That case returns `status="resolved_unique"` with **`resolution.qname` carrying the stored qname**.
Seven tools call the classifier. Three honour that status:

| Tool | Honours `resolved_unique` | Where |
|---|---|---|
| `read_symbol` | ✅ re-points and reads on | `read_symbol.py:190` |
| `explain_path` | ✅ | `explain_path.py:103` |
| `impact` | ✅ | `impact.py:148` |
| `find_references` | ❌ | `find_references.py:129` → `shape_exact_miss` |
| `find_callers` | ❌ | `find_callers.py:168` → `shape_exact_miss` |
| `find_implementations` | ❌ | `find_implementations.py:78` → `shape_exact_miss` |
| `find_view_data` | ❌ | `find_view_data.py:98` → `shape_exact_miss` |

The four failures share one function. `shape_exact_miss` (`nav_result.py:397`) has no
`resolved_unique` branch, so a uniquely-resolved subject falls into `if resolution.candidate_count:`
and is shaped as `name_not_qualified` — because `resolved_unique` also carries `candidate_count: 1`.
**The resolved qname is discarded by the payload shaper, one line before it would have been used.**

## Why the 3/4 split is the defect and not a design choice

075 predicted this exact failure mode and it happened anyway, two rounds later, in the sibling family
075 named: *"the forgiving tool teaches the habit that breaks the strict one"* (round 6 §8). An agent
trained by `read_symbol` reads `results: []` first and `reason` second. `candidate_count: 1` plus
`results: []` is the worst available shape — it proves the tool knows the unique answer and is
declining to give it.

## Scope

- **Give `shape_exact_miss` a `resolved_unique` verdict**, so the shared shaper can never again
  mis-file a resolved subject as under-qualified. One function, four callers.
- **Re-point the four `find_*` tools** onto `resolution.qname` and answer, matching `read_symbol`'s
  existing retry rather than inventing a second path (075's "state it in one place").
- **Make the re-point visible, not silent.** The answer is about a qname the caller did not type;
  disclose the normalisation the way 061 discloses every other conditional field, so a reader can tell
  a re-pointed answer from an exact hit.
- **Close 075's sibling-surface verdict as a test, not as prose.** An enumerating test over every tool
  that calls `classify_missing_subject` — the same shape 066 used for the clamp contract — so a new
  nav tool cannot join the family without an explicit verdict on this status.

### Not in scope

`ambiguous` (`candidate_count > 1`) stays a refusal with `try_instead: search_symbol`. Round 6
recorded that behaviour as **IMPROVED** over round 4 and it is correct: with six candidates the tool
genuinely does not know. This ticket is only about the case where it does.

## Acceptance criteria

1. **AC1.** For a namespaced subject that differs from the stored qname only by the leading anchor,
   all seven classifier callers return the same subject resolution — proven by one enumerating test
   over the tool list, so the count is the denominator and not a sample.
2. **AC2.** `find_references` on the round-6 subject shape returns the RESOLVED edges instead of
   `results: []`; the hit count and tiers match the leading-`\` form byte for byte.
3. **AC3.** A re-pointed answer names the qname it actually answered about; an exact hit is
   byte-identical to today (R4.2 — no payload churn on the common path).
4. **AC4.** `candidate_count: 1` with an empty `results` list is unreachable from any nav tool, and a
   test asserts the combination cannot be produced.
5. **AC5.** The `ambiguous` path is unchanged — same `reason`, same `candidate_count`, same
   `try_instead` — proven by a test that would fail if this change made ambiguity forgiving.
6. **AC6.** 075's sibling-surface bullet is marked closed in that ticket with the enumerating test as
   the evidence; a scope bullet that was recorded as done while three of seven tools honoured it is how
   this survived two field rounds.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 122 — exact-miss shaping discards a resolved subject (working doc)

- **Ticket:** 122 · local-file `docs/tasks/122_exact-miss-shaping-discards-a-resolved-subject.md`
- **Type:** bug
- **Repo(s) / Porting:** app (single repo)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/N touched files under UI paths
- **TIER:** full (SCOPE=M, universal N=7 > 1, not security-tagged)
- **BASELINE:** green — `.venv/bin/pytest -q` → **1687 passed** (untouched `main`, 2026-08-22)
  - baseline exclusions: none
- **CHALLENGER:** OFF (solve args: skipped review & Challenge)
- **Review:** SKIPPED (same args — waived gate, not reintroduced)

---

## Phase 0 — Refine

`PREMISE: 15 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 5 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

`refine skipped: 0 unresolved product-decisions`

**Premise detail (all referenced-as-existing, all resolved):**
`classify_missing_subject` / `shape_exact_miss` in `nav_result.py:301,396`; honour/decline sites in
`read_symbol.py:190`, `explain_path.py:103`, `impact.py:148`, `find_references.py:129`,
`find_callers.py:168`, `find_implementations.py:78`, `find_view_data.py:98`; tickets 075, 076, 065,
061, 066, 093.

**Recalled claims (ADVISORY):**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | 102-C2 `one-rule-for-every-subject-slot` | 2 | handle — four find_* consume one classifier | yes — one shared `unique_repoint`, not four copies |
| 2 | 102-C1 `re-verify-the-assumption-on-a-new-path` | 2 | handle — new `resolved_unique` branch | yes — shaper branch + every caller re-checked |
| 3 | 100-C1 `source-the-caveat-from-the-computation` | 2 | handle — `resolved_qname` from `resolution.qname` | yes — source from classifier, not the typed subject |
| 4 | 093-C3 `prove-the-guard-fails` | 2 | handle — AC4 unreachable-combo guard | yes — observe the combo red on pre-change shaper |
| 5 | 093-C2 `derived-not-listed-invariant` | 2 | handle — enumerating test denominator | yes — derive callers from `classify_missing_subject(` |

INPUT KIND: ticket (single deliverable). Exposure-checker: skipped (refine skipped).

---

## Requirements matrix

`SECTIONS: 6 found (Why this exists · This is not a new defect class · Why the 3/4 split · Scope · Not in scope · Acceptance criteria) | 6 decomposed | ROWS: C=3 R=4 G=3 AC=6`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why this exists | `results:[]` + `reason:name_not_qualified` + `candidate_count:1` | shaper files unique resolve as under-qualified | `nav_result.py:402-404` `if resolution.candidate_count` | 1/7 | | ✅ |
| G2 | 075 unfinished | 075 scope: normalise everywhere; sibling surface recorded | classifier exists; four find_* still decline | ticket table; `find_references.py:142` | 2/7 | | ✅ |
| G3 | 3/4 split | forgiving tool teaches the habit that breaks the strict one | find_* must match read_symbol's retry | `read_symbol.py:190-193` vs `shape_exact_miss` fall-through | 2/7 | | ✅ |
| R1 | Scope | Give `shape_exact_miss` a `resolved_unique` verdict | branch before `candidate_count` so it cannot emit `name_not_qualified` | `nav_result.py:396-406` | 1/7 | | ✅ |
| R2 | Scope | Re-point the four `find_*` onto `resolution.qname` and answer | same retry as `read_symbol._resolve_miss` | four miss `return shape_exact_miss(...)` sites | 2/7 | | ✅ |
| R3 | Scope | Make the re-point visible, 061-conditional | `resolved_qname` only when answered ≠ asked | 075 D3 named the field; 061 omit-empty | 3/7 | | ✅ |
| R4 | Scope | Enumerating test over every `classify_missing_subject` caller | denominator from code, 066 shape | 7 call sites (grep) | 4/7 | | ✅ |
| C1 | Not in scope | `ambiguous` stays refusal + `try_instead: search_symbol` | do not make many-candidates forgiving | `nav_result.py:323`; existing honesty tests | 5/7 | | ✅ |
| C2 | AC3 / R4.2 | exact hit byte-identical to today | no new field on the common path | R4.2; 061 omit when asked==answered | 3/7 | | ✅ |
| C3 | Scope / 061 | disclose like other conditional fields | helper omit-when-equal; no adapter bump | 075 D2 (tool-output, not adapter contract) | 3/7 | | ✅ |
| AC1 | AC | all seven callers same subject resolution | enumerating test, N=7 is the denominator | inventory below | 4/7 | `test_every_classifier_caller_honours_resolved_unique` | ✅ |
| AC2 | AC | `find_references` unanchored returns same hits/tiers as `\` form | fixture EXTENDS edges; compare results | honesty fixture + new edges | 2/7 | | ✅ |
| AC3 | AC | re-point names answered qname; exact hit unchanged | `resolved_qname` present iff re-point | attach helper | 3/7 | | ✅ |
| AC4 | AC | `candidate_count:1` + empty `results` unreachable | shaper + tool-surface guard | AC4 tests | 1/7 | | ✅ |
| AC5 | AC | ambiguous path unchanged | existing bare-name tests still pin the triple | `test_qname_subject_honesty.py` | 5/7 | | ✅ |
| AC6 | AC | 075 sibling-surface marked closed with enumerating test as evidence | edit 075 scope bullet + point at the test | 075 lines 57–59 | 6/7 | | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 |
|-------|---------------|------------------------|--------|--------------|--------|
| AC1 | all **seven** classifier callers | grep `classify_missing_subject(` under `tools/` excluding def = **7** modules | Y | yes — derived caller set | — |
| AC2 | hit count + tiers match leading-`\` form | retro's "9 hits / 8 RESOLVED EXTENDS" is **anchor-monorepo evidence**, not a fixture pin; AC text is match-the-`\`-form | Y (value is relative, not 9) | yes — `results`/`total_count`/tiers equal | — |
| AC3 | names answered qname; exact hit byte-identical | field `resolved_qname` iff asked≠answered (075 D3 + 061) | Y | yes — key presence + payload `==` | — |
| AC4 | combo unreachable from any nav tool | any payload with `results==[]` and `candidate_count==1` | Y | yes — enumerating assert | — |
| AC5 | ambiguous unchanged | existing tests pin reason + count + try_instead | Y | yes | — |
| AC6 | 075 bullet closed with enumerating test as evidence | 075 still lists the bullet as open scope | Y (to-do) | yes — grep 075 + test name | — |

No AC-value mismatch. No unfalsifiable AC. No uncodified standard to ratify (`resolved_qname` already named in 075 D3).

## Inventory (universal)

- **Denominator N=7** classifier callers (AC1 / R4) — per-item checklist:
  1. `read_symbol` — already honours
  2. `explain_path` — already honours
  3. `impact` — already honours
  4. `find_references` — declines today
  5. `find_callers` — declines today
  6. `find_implementations` — declines today
  7. `find_view_data` — declines today
- **Denominator N=4** find_* re-point (R2): references, callers, implementations, view_data.
- **AC4 "any nav tool":** every tool that can return `results` + `candidate_count` (the 7, plus any other nav tool the enumerating surface sweep already covers).

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| 1 | read_symbol | | |
| 2 | explain_path | | |
| 3 | impact | | |
| 4 | find_references | | |
| 5 | find_callers | | |
| 6 | find_implementations | | |
| 7 | find_view_data | | |

`SURFACES:` n/a — TRACK: backend.

## Clarifications

`CLARIFICATION: 6 raised | 6 self-resolved (cited) | 0 for human decision`

- Field name `resolved_qname` — 075 working-doc D3 / change-list item 5.
- Shaper line is `396` not ticket's `397` — function exists; off-by-one is not a miss.
- No adapter `contract_version` bump — 075 D2: tool-output field, like `limit_capped_to`.
- read_symbol stays byte-identical between forms (AC75.1); find_* disclose via new field only (AC3).
- AC2's "9 / 8 RESOLVED" is retro evidence, not the fixture pin.
- `file_outline` is a 075 sibling but **not** a classifier caller — outside N=7 (ticket table).

---

## Phase 1 — Analysis ✋ Gate 1

- **Root cause (logic):** `shape_exact_miss` (`nav_result.py:402`) treats any `candidate_count > 0` as `name_not_qualified`. `resolved_unique` also carries `candidate_count: 1` (`:322`), so a uniquely-resolved subject is shaped as under-qualified and `resolution.qname` is discarded. Four find_* call the shaper on every exact miss (`find_references.py:142` and siblings). `read_symbol` / `explain_path` / `impact` branch on `status` first and never reach that fall-through.
- **Handler / blast radius:** `shape_exact_miss` + four find_* miss paths; tests in `test_qname_subject_honesty.py`; 075 sibling bullet; CONVENTION §6; BACKLOG/frontmatter. `shape_exact_miss` callers also include `impact._explain_lost_subject` and `read_symbol` (untracked only) — shaper branch is their safety net. No schema / no adapter / no UI.
- **Rule-compliance section coverage:**

`RULE SECTIONS: 10 applicable — 7 by change-type | 3 by recalled handle — R1.1 (type) ✅ branches only on SubjectResolution.status, not language; R1.2 (type) ✅ helper stays in nav_result, no new seam; R1.4 (type) ✅ tools present, SQL stays in store; R3.1 (type) N/A because tool-output conditional field, not node/edge/qname convention (075 D2); R4.2 (type) ✅ exact-hit byte-identical (AC3/C2); R5.4 (type) ✅ resolved_qname holds one register (a stored qname); R6.1 (type) ✅ fixture-repo tool tests; R5.5 (handle source-the-caveat-from-the-computation, PROVISIONAL) ✅ sourced from resolution.qname — surfaced, does not gate-block; R6.5 (handle prove-the-guard-fails) ✅ AC4 observes the forbidden combo on the pre-change shaper; R6.7 (handle derived-not-listed-invariant, PROVISIONAL) ✅ caller set derived from classify_missing_subject( — surfaced, does not gate-block`

- **Self-audit:** RECALL emitted, sections 6=6, AC table complete, BASELINE green, j=0, inventory N=7, RULE SECTIONS answered, TRACK/TIER/SCOPE declared, no multi-clause want-decision.
- **Gate 1 status:** cleared by standing approval (solve args: choose approach + pass all gates).

---

## Phase 2 — Design ✋ Gate 2

- **Approach:**
  1. Add `unique_repoint(resolution) -> str | None` and `attach_resolved_qname(payload, asked, answered)` in `nav_result.py` (061 omit when equal).
  2. `shape_exact_miss`: handle `resolved_unique` **before** `candidate_count` — attach `resolved_qname`, never `name_not_qualified`. Defense in depth; tools must not rely on it to answer.
  3. Four find_* : on miss, if `unique_repoint` returns a stored qname, **re-run the lookup** (read_symbol's retry) and attach `resolved_qname` on the hit payload; else `shape_exact_miss` as today.
  4. Payload `qname` stays what the caller typed; `resolved_qname` is the stored form (visible, not silent).
  5. Enumerating test derives caller modules from `classify_missing_subject(` and requires an invoke arm per module (066 + R6.7).
- **Rejected alternatives:**
  - *Retry only, no shaper branch* — the ticket names the shaper as the defect; a future caller would re-introduce the fall-through. Rejected.
  - *Shaper-only (return a sentinel, no per-tool retry)* — shaper has no store, cannot fetch edges; AC2 would fail. Rejected.
  - *Rewrite payload `qname` to the stored form (read_symbol style) and skip `resolved_qname`* — silent on find_*; ticket requires visible disclosure. Rejected.
  - *Hardcode leading-`\` strip* — 075 already rejected (R1.1). Rejected.

**Assumptions**

| Assumption | verified / novel-untested | Spike / proving test |
|------------|---------------------------|----------------------|
| `resolved_unique` always has `candidate_count==1` | verified | `nav_result.py:322` |
| find_* classify only when `total==0 and not indexed` | verified | four miss guards |
| tool-output field needs no adapter bump | verified | 075 D2; `limit_capped_to` precedent |
| honesty fixture `\Ns\Sub\Enum` is unique | verified | existing `test_read_symbol_normalises_leading_anchor` |
| no novel 3p/runtime | verified | in-process tool calls over seeded store |

**Smallest change-list**

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|--------|-----------|--------------|----------------|-----|
| `unique_repoint` + `attach_resolved_qname` + `shape_exact_miss` `resolved_unique` branch | `code_atlas/tools/nav_result.py` | all `shape_exact_miss(` callers (4 find_* + impact + read_symbol untracked) | R1, R3, C2, C3, AC3, AC4 | 1/7 |
| Re-point retry + attach on hit | `find_references.py` `find_callers.py` `find_implementations.py` `find_view_data.py` | tool docstrings (MCP descriptions); signed-claim `subject_parts` still the asked qname | R2, G1–G3, AC2, AC3 | 2/7 |
| Enumerating + AC2–AC5 tests; EXTENDS seed for refs/impls | `tests/test_qname_subject_honesty.py` | existing honesty tests must stay green (ambiguous / absent / byte-identical read_symbol) | R4, AC1–AC5, C1 | 4/7 |
| Close 075 sibling-surface with test pointer | `docs/tasks/075_*.md` | 075 raw-ticket scope only | AC6 | 6/7 |
| Document `resolved_qname` | `docs/CONVENTION.md` §6 | nav payload readers | R3, C3 | 3/7 |
| Status sync | ticket frontmatter + `docs/BACKLOG.md` | `test_backlog_bookkeeping` | bookkeeping | 7/7 |
| Proof collateral: existing ambiguous/absent honesty tests | `tests/test_qname_subject_honesty.py` (no assertion change expected) | AC5 / C1 | 5/7 |

**HANDLES** (commands + verbatim output):

`HANDLES: 5 recalled | 5 traced (command + result) | 0 does not apply | 0 unanswered`

1. `one-rule-for-every-subject-slot` — **traced**
```
$ rg -n "shape_exact_miss\(|classify_missing_subject\(" code_atlas/tools --glob '*.py'
```
Four find_* each `return shape_exact_miss(...)` independently; impact/read_symbol already status-branch. Folded: one `unique_repoint` both the shaper and the four retries call.

2. `re-verify-the-assumption-on-a-new-path` — **traced**
Same grep: every `shape_exact_miss(` site listed (find_references:142, find_callers:190, find_implementations:91, find_view_data:97, impact:193, read_symbol:201). New branch is checked against all six, not only the four.

3. `source-the-caveat-from-the-computation` — **traced**
`resolution.qname` is assigned only at `nav_result.py:322` (`matches[0]`). `attach_resolved_qname` reads that, never the typed subject.

4. `prove-the-guard-fails` — **traced**
Pre-change: `shape_exact_miss({results:[]}, SubjectResolution("resolved_unique", q, 1))` today follows `if candidate_count` → `name_not_qualified` + `candidate_count:1`. AC4 test asserts that combo is gone (shaper) and unreachable from tools.

5. `derived-not-listed-invariant` — **traced**
```
$ rg -l "classify_missing_subject\(" code_atlas/tools --glob '*.py'
code_atlas/tools/explain_path.py
code_atlas/tools/find_callers.py
code_atlas/tools/find_implementations.py
code_atlas/tools/find_references.py
code_atlas/tools/find_view_data.py
code_atlas/tools/impact.py
code_atlas/tools/nav_result.py
code_atlas/tools/read_symbol.py
```
7 callers + definition. Test derives the 7, fails if a new module calls without an invoke arm.

- **Rule compliance:** R1.1/R1.2/R1.4/R4.2/R5.4/R6.1 as Phase 1; 061 conditional field; CONVENTION §6 one-module-per-tool unchanged.
- **Proving test:** `pytest -q tests/test_qname_subject_honesty.py::test_find_references_leading_anchor_matches_stored_form`
  - **Fails pre-change:** unanchored returns `results:[]` / `name_not_qualified` / `candidate_count:1`.
  - **Passes post-change:** `results` and tiers equal the leading-`\` call; `resolved_qname` only on the unanchored call.
  - Risk layer = integration (real tools over a seeded store) → integration proof. Layer-match ✅.

**Verification plan**

| AC | risk layer | proof artifact | layer-match? |
|----|------------|----------------|--------------|
| AC1 | integration | enumerating tool calls over derived caller set | ✅ |
| AC2 | integration | proving test (two find_references calls) | ✅ |
| AC3 | integration | proving test + exact-hit payload `==` | ✅ |
| AC4 | integration | shaper unit + tool-surface sweep | ✅ |
| AC5 | integration | existing bare-name honesty tests | ✅ |
| AC6 | integration (doc+test) | 075 text names the enumerating test | ✅ |

**Coverage-gap exclusions:** none.

**Proof manifest:** n/a (backend).

- **Rollback + porting:** revert the branch; no schema/index/adapter bump. Single repo `app`.
- **SCOPE confirmed:** M (unchanged).
- **Gate 2 status:** cleared by standing approval (solve args: choose the best approach + pass all gates).

---

## Phase 3 — Execute

- Branch: `fix/122-exact-miss-shaping-discards-a-resolved-subject`
- Commits: (this ship)
- Proving test added: `tests/test_qname_subject_honesty.py::test_find_references_leading_anchor_matches_stored_form`
- **Verification sweep — BOTH axes.** *File axis:* zero stray references ✅ · diff ⊆ approved list ✅ (plus PLAN §19 honesty paragraph and LESSONS P1/`seen:` + 122 lesson, folded as docs/bookkeeping) · each hunk maps to a row ✅. *Behaviour axis:* Approach bullets 1–5 `implemented-as-approved`.
- **Design-conformance deviations:** none.
- **Empirical output:**

```
$ .venv/bin/pytest -q tests/test_qname_subject_honesty.py::test_find_references_leading_anchor_matches_stored_form
1 passed

$ .venv/bin/pytest -q tests/test_qname_subject_honesty.py
18 passed in 0.98s

$ .venv/bin/ruff check code_atlas/tools/nav_result.py code_atlas/tools/find_*.py tests/test_qname_subject_honesty.py
All checks passed!

$ .venv/bin/mypy code_atlas/tools/nav_result.py code_atlas/tools/find_references.py code_atlas/tools/find_callers.py code_atlas/tools/find_implementations.py code_atlas/tools/find_view_data.py
Success: no issues found in 5 source files

$ .venv/bin/pytest -q --tb=no
1692 passed in 92.62s
```

BASELINE was 1687; delta +5 tests, 0 new failures.
- **Golden/snapshot change:** none.
- **Design-invalidation / re-gate:** none.

## Phase 4 — Review ✋

SKIPPED per solve args (`skipped review & Challenge`). Waived gate, not reintroduced. No `Reviewed at` marker (review did not run). Stale-review guard does not apply.

## Phase 5 — Finalise ✋ final gate

- Durable lesson: `docs/LESSONS.md` **122** + claims 122-C1 / 122-C2 (proposed; human confirms types at this gate).
- `CLAIMS: 2 claim(s) from 1 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
- `RECURRENCE: 0 recurring | 0 superseded | 0 promotion candidate(s)` (both `seen:` = 122 only)
- `FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified | 0 not cheaply checkable`
- `PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
- `/mango:promote` is the cross-ticket pass when a type-2 `seen:` list crosses 2 ticket keys.
- Outward actions (standing maintainer approval: commit + push + open PR): push branch; open PR via `gh`.

## Session status

- **Last updated:** 2026-08-22
- **Current phase:** complete (shipped)
- **work_doc_mode:** embed · path: this file below the separator
- **Next action:** none
- **Blocked on:** none

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| — | no subagent dispatched (refine skipped; review/challenger waived; no Explore fan-out) | — | unmeasured (host does not surface usage) | rtk=expect · none applied |

`LEDGER TOTAL: 0 dispatch · top cost driver: none (main-loop only)`

## Decision log

| When | Decision | Why |
|------|----------|-----|
| solve start | CHALLENGER OFF; review SKIPPED | user args |
| Gate 1 | cleared on standing approval | user: pass all gates |
| Gate 2 | approach as designed; cleared on standing approval | user: choose the best approach |
| Phase 0 | refine skipped | 0 unresolved product-decisions |

