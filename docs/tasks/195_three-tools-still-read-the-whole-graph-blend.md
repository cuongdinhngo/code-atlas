---
id: 195
slug: three-tools-still-read-the-whole-graph-blend
title: '183 split the tier mix per language for one caller; three other tools still read the whole-graph blend'
phase: 1.5b
milestone: Measure
status: done
depends_on: [183]
---

## Why this exists

183 built `edge_health_by_language` because *"a whole-graph blend cannot be attributed"*, and wired it
into `get_index_status`. Three other callers still read the un-split number:

```
code_atlas/tools/find_orphans.py:114        health = store.edge_health() ...
code_atlas/tools/generate_onboarding.py:99  confidence = store.edge_health()["by_tier"]
code_atlas/tools/reachable_from.py:55       health = store.edge_health() ...
```

Round 12 §13 recorded what that costs, on the two-language index: *"**Cannot answer.** No per-language
breakdown exists in any payload. Whole-graph HEURISTIC fell 68.9 % → **53.51 %**, still **+9.6 pp**
over PHP-only. **This is a measurement the tool cannot make about itself**."*

**Claim `183-C1` predicted exactly this and named its own destination**: *"the actionable form is a
roll-out checklist item (enumerate the aggregates this new dimension makes ambiguous), which belongs
to whichever ticket adds adapter #3."* [184](184_tsql-source-adapter-tier-1a.md) is that ticket, and
its AC3 forbids a `code_atlas/` diff — so the enumeration lands here instead of being absorbed there.

**The number is already wrong, today, with two languages.** This does not wait on a third.

## Scope

1. Enumerate every consumer of the whole-graph aggregate, from the code and not from memory — the
   three above are the trace, not an assumption.
2. For each, decide and record: does it want the whole-graph number, the subject's slice, or both? A
   confidence figure attached to a per-language answer that reports a cross-language blend is the
   defect; a genuinely whole-graph headline is not.
3. Where a slice is wanted, read the stamp 183 already writes — no second scan, no second fold. 183's
   own lesson is that two folds make the split stop summing to the whole.

### Explicitly not in scope

- Any new aggregate. This re-points existing readers at an existing stamp.
- `get_index_status`, already correct (183).
- The `unattributed` residue's definition — 183 settled it and it stays as is.

## Constraints

- **183's arithmetic invariant** — the slices plus `unattributed` must equal the whole; that
  reconciliation is the only check an outside reader has.
- **R1.1** — read the stamp by language key, never branch on a language name.
- **R6.5** — each re-pointed caller ships with a red run showing the blended number where the slice
  was wanted.

## Acceptance criteria

1. Every consumer of `edge_health()` is enumerated with a recorded decision (slice / whole / both).
2. Each caller that wanted a slice reads the 183 stamp, and its payload is pinned by a test that fails
   on the blended value.
3. The slices-plus-residue reconciliation still holds, pinned as 183 pinned it.
4. No `contract_version` bump.

## References

Field retro round 12 §13 (*"a measurement the tool cannot make about itself"*, the +9.6 pp).
[183](183_edge-health-has-no-per-language-breakdown.md) and its claim `183-C1`
(`an-aggregate-outlives-the-world-that-named-it`, `docs/LESSONS.md`).

---

## Session status

- **KEY:** 195 · **work_doc_mode:** embed · **Phase:** 2 design — complete; Gates 0/1/2 closed.
- `TRACK: backend` · `TIER: full`. Run arg: *"with skipped review"* — both seats off.
- Approach chosen by the agent on the maintainer's hand-back (*"choose the best approach"*).

## Phase 0 — refine

`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

Two, both settled by the ticket's own text: **(a)** what each consumer wants — Scope 2 fixes the test
(*"a confidence figure attached to a per-language answer that reports a cross-language blend is the
defect; a genuinely whole-graph headline is not"*); **(b)** where the slice comes from — Scope 3 says
the 183 stamp, *"no second scan, no second fold"*. No want-decision: the ticket specifies intent
completely.

## Phase 1 — analysis

`PREMISE: 11 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`

All three cited call sites resolve **at the exact lines the ticket names** —
`find_orphans.py:114`, `generate_onboarding.py:99`, `reachable_from.py:55`. Also resolved: tasks 183
and 184, claim `183-C1` in `docs/LESSONS.md`, rules R1.1 and R6.5, and the symbols `edge_health`,
`stamped_edge_health_by_language`, `EDGE_HEALTH_BY_LANGUAGE_KEY`.

`RECALL: 6 claim(s) surfaced | 0 by symbol | 5 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

The change **threads a value through callers** (a stamp produced at build time, consumed in two
payloads) — recall trigger 3. By handle: `an-aggregate-outlives-the-world-that-named-it` (this
ticket exists because of `183-C1`) · `do-not-attest-past-the-payloads-resolution` (R5.6) ·
`prove-the-guard-fails` · `count-pin-in-blast-radius` · `derived-not-listed-invariant`. By area:
`empty-seam-inputs-masquerade-as-missing-data`.

`SECTIONS: 5 found | 5 decomposed | ROWS: C=3 R=3 G=1 AC=4`

Sections: *Why this exists* · *Scope* (with *Explicitly not in scope*) · *Constraints* ·
*Acceptance criteria* · *References*. `STRUCTURE: native`.

| ID | Source | Verbatim (abridged) | Interpretation | Status |
|---|---|---|---|---|
| G1 | round 12 §13 | *"a measurement the tool cannot make about itself"* | the +9.6 pp becomes attributable from these payloads | open |
| C1 | Constraints | slices + `unattributed` == the whole | pinned **in these payloads**, not only in 183's test | open |
| C2 | Constraints | R1.1 — read by language key, never branch on a name | the stamp is a dict; nothing reads a language name | open |
| C3 | Constraints | R6.5 — a red run per re-pointed caller | recorded below | open |
| R1 | Scope 1 | *"enumerate every consumer … from the code"* | a grep, not a memory; see the trace | open |
| R2 | Scope 2 | *"decide and record: whole, slice, or both"* | four consumers, four recorded decisions | open |
| R3 | Scope 3 | *"read the stamp 183 already writes"* | `stamped_edge_health_by_language()`; no second fold | open |
| AC1 | AC | every consumer enumerated with a decision | the table below | open |
| AC2 | AC | slice-wanting callers read the stamp, pinned by a test that fails on the blend | 8 of 12 red pre-change | open |
| AC3 | AC | the reconciliation still holds, pinned as 183 pinned it | its own test, reusing 183's `total_by_tier` | open |
| AC4 | AC | no `contract_version` bump | nothing in the adapter contract moves | open |

### Scope 1 — every consumer, from the code

Ran at `9b8d08813eac03865cb8a003632e5a800408edb7`.

```
$ grep -rn "edge_health()" --include=*.py code_atlas/ onboarding_llm/
code_atlas/tools/generate_onboarding.py:99:            confidence = store.edge_health()["by_tier"]
code_atlas/tools/find_orphans.py:114:            health = store.edge_health() if detail_level == "standard" else None
code_atlas/tools/get_index_status.py:245:        "edge_health": store.edge_health(),
code_atlas/tools/reachable_from.py:55:            health = store.edge_health() if detail_level == "standard" else None
```

Re-run on the tree under review, so the enumeration is not a claim about an earlier tree: the two
re-pointed callers still hold their blend at the same lines, which is the point — the split was
**added beside** it, not swapped in.

Four, not three: the ticket named the three it was about and `get_index_status` is the one 183
already fixed. The trace confirms there is no fifth.

### Scope 2 — the recorded decision for each

| Consumer | Wants | Decision |
|---|---|---|
| `reachable_from` | **both** | The walk starts at configured entry points and crosses languages, so the blend genuinely **is** this answer's denominator and must not be replaced. It is also uninterpretable alone, which is round 12 §13 exactly. **Attach the stamp beside it.** |
| `find_orphans` | **both** | Same walk, same reason. |
| `generate_onboarding` | **whole — deferred, and this is the one to argue with** | Its confidence census is a genuinely whole-graph headline for a whole-repo document, so the number is *right*. But it is equally unattributable, and the honest fix is not the re-point this ticket scopes itself to: `confidence` is a field of a **versioned published schema** (`DATASET_VERSION` 7) read by `headlines.py` and by `viewer.py`'s JavaScript. Adding to it is a schema bump plus a renderer change — *a new aggregate on a published surface*, which this ticket's own *Explicitly not in scope* rules out. **Filed as [196](196_the-system-map-cannot-attribute-its-own-confidence.md).** |
| `get_index_status` | already correct | 183 did it; out of scope by the ticket. |

### Clarifications

`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

1. **Is a cross-language walk's blend the defect?** *Self-resolved:* no — Scope 2's own sentence
   exempts *"a genuinely whole-graph headline"*. The defect is that it cannot be attributed, so the
   answer is `both`, not `slice`.
2. **Does `generate_onboarding` belong in this ticket?** *Self-resolved:* no, on the ticket's own
   *Explicitly not in scope* line (*"Any new aggregate. This re-points existing readers at an
   existing stamp."*) — a field in a versioned schema with a renderer behind it is not a re-point.

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) ✅ the stamp is read by key; no language name appears · §2 (change-type) N/A (no adapter touched) · §3 (change-type) ✅ AC4 — nothing in the adapter contract moves · §4 (change-type) ✅ the stamp is written once per build and read, never recomputed · §5 (change-type) ✅ R5.6 — a pre-183 index omits the field rather than claiming one language · §6 (change-type) ✅ 12 assertions, 8 red pre-change · §7 (change-type) ✅ the deferred consumer is a filed ticket, not a silence · §8 (change-type) N/A (no dependency added)`

### Blast radius

One shared helper (`reach_shared.reach_payload`) is the only place the payload grows, and both
callers pass through it. Nothing else reads the key. Repos touched: `app`.

`TRACK: backend — 0/7 touched files under UI paths`
`SCOPE: S` — three source files, one new test, one filed follow-up.

## Phase 2 — design

### Approach

Add one optional argument to `reach_payload` and attach it when present; both callers read
`store.stamped_edge_health_by_language()` inside the block they already open. The blend stays exactly
where it was — this is additive, and the field it adds is the one round 12 asked for.

**The stamp, never a recomputation.** `stamped_edge_health_by_language()` returns `None` on a
pre-183 index and the docstring says why a fallback would be wrong: it would put the `GROUP BY` the
stamp exists to avoid back on the answer path, and an empty dict would claim a one-language graph for
an index that never measured itself. `None` therefore means the key is **absent**, which is a test of
its own.

### Rejected alternatives

1. **Replace the blend with the slice.** Rejected: both tools walk **across** languages from
   configured entry points, so no single slice is this answer's denominator. Replacing it would make
   the caveat wrong rather than merely unattributable.
2. **Compute the split on the answer path** (`store.edge_health_by_language()`). Rejected by Scope 3
   and by 183's own lesson: two folds make the split stop summing to the whole, and it puts a
   `GROUP BY` over a 2.1 M-row table on every call.
3. **Do `generate_onboarding` here too.** Rejected on the ticket's *Explicitly not in scope*; filed
   as 196 rather than dropped.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| 1 | The stamp is written by every full build, so a freshly built index has it | **verified** — 183's own tests build and read it; the new tests build and read it through two different tools |
| 2 | `None` from the stamp is reachable in practice | **verified** — a test blanks the meta key and asserts the field is absent, not invented |
| 3 | No payload-shape test pins the exact key set of these two payloads | **verified** — the full suite is green with the key added |

### Change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| CL-1 | one optional argument, attached when present | `code_atlas/tools/reach_shared.py` | the only place both payloads grow | R3, AC2 | 1/1 |
| CL-2 | read the stamp beside the blend | `code_atlas/tools/reachable_from.py` · `code_atlas/tools/find_orphans.py` | none — same store block, same detail-level gate | R1, R2 | 2/2 |
| CL-3 | **the proving test** | `tests/test_reachability_payloads_attribute_their_confidence.py` (new) | reuses 183's two-language harness rather than building a second | AC2, AC3, C1 | 1/1 |
| CL-4 | the deferred consumer, filed | `docs/tasks/196_…md` · `docs/BACKLOG.md` | — | R2 | 1/1 |
| CL-5 | status, spend row, claims | `docs/BACKLOG.md` · `docs/TOKEN_LEDGER.md` · `docs/LESSONS.md` | `test_backlog_bookkeeping` | — | 1/1 |

### Recalled handles — every one answered

`HANDLES: 5 recalled | 3 traced (command + result) | 2 does not apply (reason) | 0 unanswered`

| Handle | Command | Result → what it changed |
|---|---|---|
| `an-aggregate-outlives-the-world-that-named-it` | `grep -rn "edge_health()" --include=*.py code_atlas/ onboarding_llm/` | **4 consumers**, one already fixed by 183. This is the enumeration `183-C1` said belonged to whichever ticket makes the aggregate ambiguous; it is Scope 1 and it is above. |
| `do-not-attest-past-the-payloads-resolution` | `sed -n '744,760p' code_atlas/store.py` | The stamp returns `None` for a pre-183 index **by design**, with the docstring naming a computed fallback as the wrong answer. The payload therefore omits the key rather than inventing a one-language graph — its own test. |
| `prove-the-guard-fails` | disabled the attach, re-ran the file | **8 of 12 red.** The 4 that stayed green are the two that assert the field's *absence* (pre-183 stamp, `minimal`), which is the correct behaviour under both versions — recorded so the red count is not read as 12. |
| `count-pin-in-blast-radius` | — | **does not apply because** the change adds an optional payload key and no file, symbol, or tool: it moves no count. The full-suite run is the check, and it is green. |
| `derived-not-listed-invariant` | — | **does not apply because** nothing here lists anything: the field's content is the stamp verbatim, and its language keys come from the store's own census. |

By area: `empty-seam-inputs-masquerade-as-missing-data` — the absent-key case is exactly that shape,
and it is the reason the pre-183 test exists.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match |
|---|---|---|---|---|
| AC1 | manual-recorded | the Scope 1 trace and the decision table above | n/a | ✅ |
| AC2 | integration | the new test, over a real two-language build | authored | ✅ |
| AC3 / C1 | integration | reconciliation, reusing 183's `total_by_tier` | authored | ✅ |
| C2 | logic | no language name appears in the diff | n/a | ✅ |
| C3 | manual-recorded | the red run above, 8 of 12 | n/a | ✅ |
| AC4 | logic | nothing in `contract.py` moves | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

No AC asserts that an answer is *sensible*; each asserts an exact key set or an exact sum. The
deferred `generate_onboarding` consumer is a **filed ticket**, not a coverage-gap exclusion: nothing
about it is unproven, it is simply out of this ticket's declared scope.

### Proving test

`tests/test_reachability_payloads_attribute_their_confidence.py` — 12 assertions across both tools.

`.venv/bin/python -m pytest tests/test_reachability_payloads_attribute_their_confidence.py -q`

### Rollback + porting

Revert the branch: the optional argument and the two reads go, and both payloads return to the blend
alone. One repo; no porting.

`SCOPE: S` — confirmed from Phase 1.

`BASELINE: green — 2591 passed, 1 skipped in 170.59s`

**Inherited, not re-measured, and that is a deviation from analysis step 9.** The figure is 194's
delta-green at `f3e82ca66a84cecf633341bf3037f676bd240520`, the tree that became this branch's base by
squash merge plus one docs-only commit. It is stated rather than quietly used, and it is in
DISCLOSURE.

```
scripts/docker-test.sh — at f3e82ca, the tree main was squashed from (inherited baseline)
All checks passed!
2591 passed, 1 skipped in 170.59s (0:02:50)
```

### Delta-green

Ran at `9b8d08813eac03865cb8a003632e5a800408edb7` — the tree under review.

```
$ scripts/docker-test.sh
All checks passed!
2605 passed, 1 skipped in 156.74s (0:02:36)
```

**+14, no new failure, the same one structural skip.** Twelve are the new file's assertions (six
functions over two tools); the other two are `test_backlog_bookkeeping`'s parametrised cases gained
by filing 196 and by 195 reading `done`.

## Phase 3 — execute

**No deviation from the approved change list.** Every file touched is CL-1…CL-5.

**The proving test's red run, counted honestly: 8 of 12 (R6.5).** With the attach disabled, four
assertions stayed green — the pre-183-stamp case and `minimal`, both of which pin the field's
*absence* and are correct under either version. Reporting the file's total as the red count would
have counted assertions that were never going to move. Claim `195-C3`.

**Scope 1 found a consumer the ticket did not name.** The ticket listed three; the grep found four,
the fourth being `get_index_status` — which 183 itself fixed, and which is exactly the one a filer
working from that change would omit. This is `183-C1`'s handed-forward enumeration being discharged,
and it is its second sighting. Claim `195-C1`.

**Tier 1 went over budget and was paid from its own duplicates.** Filing 196 added a `docs/BACKLOG.md`
row and pushed the chain to 25,214 against 25,200. Two BACKLOG lines were removed because `AGENTS.md`
already carries both verbatim — *"M10–M12 are complete"* and *"Shipped for daily use at task 014"* —
bringing it to 25,193. **No raise.** Claim `195-C4`.

## Phase 5 — finalise

`CLAIMS: 4 claim(s) from 1 lesson entr(ies) | T1=0 T2=3 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 6 candidate(s) checked | 6 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 1 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/AGENT_BRIEF.md | mango files written: 0`
`LEDGER TOTAL: unmeasured · top cost driver: execute (main-loop)`

`prove-the-guard-fails` is already R6.5, so its sighting is a `seen:` bump.
`an-aggregate-outlives-the-world-that-named-it` reaches **recurrence 2** and cannot be promoted by an
unattended run — promotion needs a human ratify, and `183-C1`'s record has been updated in place
(`seen: 183, 195`, and its handed-forward destination marked discharged) rather than filed as a
second block, per the corpus's one-record-per-handle rule.

### DISCLOSURE

**Nobody reviewed this.** Both seats off, waived by the run arg *"with skipped review"*, recorded
`off` in the RUN CONTRACT. Clean here means *clean, nobody looked*.

- **The baseline was inherited, not re-measured.** Analysis step 9 says capture it on the untouched
  checkout; this run took 194's delta-green figure for the tree main was squashed from. The delta is
  still verifiable — main is that tree plus a docs-only commit, and 194's run was green with all
  checks passing — but the step was skipped and this is the record of it.
- **The `generate_onboarding` consumer is deferred, and it is the one to argue with.** Its confidence
  figure is what a *human* reads, which is arguably where attribution matters most. Deferred to
  **196** on this ticket's own scope line; if a reviewer disagrees, the answer is to close 196 here
  rather than to file it.
- **The reconciliation is pinned, the residue is not re-derived.** The `unattributed` bucket's
  definition is 183's and this ticket does not re-examine it — an edge whose file carries no language
  still lands there, and no test here asks whether that is the right home.
- **A stale stamp reads as current.** `stamped_edge_health_by_language()` returns whatever the last
  build wrote; nothing in these payloads cross-checks it against the graph's present state, so on a
  dirty index the split can describe an earlier tree than the answer beside it does.
- **`call-ceiling`, `token-budget` and `LEDGER TOTAL` are unknown/unmeasured** — this host surfaces
  no usage block.
