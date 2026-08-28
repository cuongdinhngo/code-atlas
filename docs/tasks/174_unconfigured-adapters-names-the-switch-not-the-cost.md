---
id: 174
slug: unconfigured-adapters-names-the-switch-not-the-cost
title: '`unconfigured_adapters` names the switch but not the cost — four rounds of "adapter contributes zero" and no payload ever said how many files were invisible'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [159, 082]
---

## Why this exists (field episode, 2026-08-27)

159 made the unwired adapter visible. Round 11 then recorded the adapter's **fourth** consecutive zero
contribution, caused by one absent env var — and the maintainer's reading of why the disclosure never
moved anyone:

> *"`unconfigured_adapters` nên nói cái giá, không chỉ nói nó tồn tại. Trước restart nó đọc
> `[{"language":"typescript","enable":"CA_TYPESCRIPT_CMD"}]`. Thiếu đúng con số quyết định: 3.294 file
> trong repo này khớp adapter đó và đang vô hình. Đây có lẽ là thay đổi duy nhất dễ nhất khiến adapter
> được bật từ mấy round trước, thay vì bốn round liền báo zero."*

*"An adapter exists"* is a fact about the product. *"3,294 files in **this** repo are invisible"* is a
fact about the reader's own cost, and it is the one that would have been acted on. Rounds 8–11 all
disclosed the former and all reported zero.

## Root cause, and why the obvious version does not work

- `code_atlas/adapter.py:334-348` — `unconfigured_adapters` knows only the **directory name** of each
  shipped adapter. Extensions come from the handshake (`adapter.py:118`,
  `announced = self._announced()["extensions"]`), and an unwired adapter is never launched — so the
  core cannot ask it what it would have claimed.
- The census cannot be joined either: `skipped.suffix` is a single total
  (`code_atlas/tools/collection.py:24-27`, from `census["skipped_suffix"]`) covering **every**
  unindexed suffix in the tree — `.css`, `.md`, images, lock files. **The 3,244-file figure is not
  derivable from it.** Any per-language split would need a suffix table in the core, which R1.1
  forbids.
- So the honest cheap form inverts the join: **the census reports a bounded histogram of the top
  unindexed suffixes** (`{".js": 2831, ".ts": 460, …}`), computed in the walk that is already
  happening, naming no language. The reader — or the agent — joins it with `unconfigured_adapters`.
  A shipped-adapter manifest read without launching is the alternative, and it is a bigger change.

## Scope

1. The collection census gains a bounded, deterministic histogram of the most common **skipped-by-suffix**
   extensions, with the cap and tie-break recorded. Language-agnostic by construction (R1.1).
2. It rides `get_index_status` where `skipped.suffix` already does, at the same detail levels.
3. Design records whether the histogram is enough on its own, or whether an adapter manifest should
   later let `unconfigured_adapters` state the count directly — and what that would cost.

### Explicitly not in scope

- Reading or launching an unwired adapter to learn its extensions. That is the bigger alternative
  above; this ticket must not smuggle it in.
- A suffix→language table anywhere in `code_atlas/` (R1.1).
- Per-language node/edge counts, and the coverage-note keying
  ([173](173_coverage-claims-key-on-configured-not-indexed.md)).

## Constraints

- **Cost** — counted inside the existing walk; no second pass over the tree, no new query at answer
  time. Bounded output (top-N), so a repo with 400 extensions cannot inflate the payload.
- **082** — the collection identity `collected − skipped_suffix − skipped_ignore == kept` still
  reconciles; the histogram is a breakdown of one term, never a replacement for it.
- **061** — omit when empty; a repo whose every suffix is indexed adds nothing.
- **R1.1** no language named in the core · **R4.2** deterministic order and tie-break · **R3** confirm
  no contract impact.

## Acceptance criteria

1. A build over a fixture tree with several unindexed suffixes reports a histogram whose entries sum
   to no more than `skipped.suffix`, with a recorded cap and a deterministic tie-break.
2. 082's collection identity still reconciles exactly, pinned.
3. The histogram appears on `get_index_status` at the recorded detail levels and is omitted when empty.
4. No new walk, no new answer-time query; the added build cost is measured.
5. `grep` for a suffix→language mapping in `code_atlas/` finds none (R1.1 gate green).
6. Determinism (R4.2), no contract bump (R3).

## References

Field episode 2026-08-27, finding (2) — reframed after checking the source: the maintainer proposed
deriving the count from `skipped.suffix`, which cannot carry it. Round 8 §13, round 9 §13, round 10 §13,
round 11 §13 (four consecutive zeros, all disclosed and none acted on).
`code_atlas/adapter.py:118,334-348`; `code_atlas/tools/collection.py:24-27`. Related:
[159](159_get-index-status-does-not-name-available-but-unconfigured-adapters.md) (what this completes),
[082](082_claims-nobody-outside-can-check.md) (the identity), [160](160_a-zero-answer-never-names-the-index-language-coverage.md).

## Session status

- **KEY:** 174 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended batch) · envelope in `.mango/run-contract-174.txt`.
- **Branch:** `feat/174-unconfigured-adapters-names-the-cost` (stacked on `feat/179-…`)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2379 passed, 0 failed` at `1c445b1` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

Scope 3 is a how-decision the ticket asks to be recorded: *"whether the histogram is enough on its
own, or whether an adapter manifest should later let `unconfigured_adapters` state the count
directly — and what that would cost."* Answered in *Scope 3 verdict*. Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=4 R=3 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 10 applicable — 8 by change-type | 2 by recalled handle — §R1.1 (change-type) ✅ · §R1.7 (recalled handle: sibling-meta-non-int) ✅ — it decided the storage shape · §R4.2 (change-type) ✅ · §R5.6 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.7 (change-type) ✅ · §R7.4 (change-type) ✅ · §R7.2 (change-type) ✅ · §R7.6 (change-type) ✅ — CONVENTION went over budget and was pruned`
`BASELINE: green — 2379 passed, 0 failed, 0 skipped at 1c445b1 (bare pytest, Linux host)`

**Premise:** every citation resolves, **and the ticket's own reframing is correct.** It records that
the maintainer originally proposed deriving the count from `skipped.suffix`, then checked the source
and found it cannot carry it — `skipped_suffix` is one total over every unindexed extension
(`.css`, `.md`, images, lock files). Confirmed at `indexer.py:512-516`: one integer, no breakdown.
And `unconfigured_adapters` really does know only the directory name, because an unwired adapter is
never launched and extensions arrive in the handshake.

**Recall:** `sibling-meta-non-int` (R1.7, by handle) — and it is the rule that decided the storage
shape, see *Approach*. `prove-the-guard-fails` (R6.5, by handle).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | four rounds said "an adapter exists" and none said how many files were invisible | publish the cost, not the switch | rounds 8–11 §13 | open |
| R1 | Scope 1 | the census gains a bounded deterministic histogram of skipped-by-suffix extensions, cap and tie-break recorded | top 10, count desc then suffix asc | `_collect_with_census` | open |
| R2 | Scope 2 | it rides `get_index_status` where `skipped.suffix` already does, at the same detail levels | inside `skipped` | `collection.py:24-27` | open |
| R3 | Scope 3 | record whether the histogram suffices, or whether a manifest should later state the count | verdict + cost | see verdict | open |
| AC1 | AC 1 | entries sum to ≤ `skipped.suffix`, with a recorded cap and deterministic tie-break | Falsifiable: sum + order asserted | proving test ×2 | open |
| AC2 | AC 2 | 082's identity still reconciles exactly | Falsifiable: the arithmetic asserted | proving test | open |
| AC3 | AC 3 | appears at the recorded detail levels; omitted when empty | Falsifiable: three levels + an all-indexed repo | proving test ×2 | open |
| AC4 | AC 4 | no new walk, no new answer-time query; the added build cost measured | Falsifiable: trace + timing + measurement | proving test + measurement | open |
| AC5 | AC 5 | `grep` for a suffix→language mapping in `code_atlas/` finds none | Falsifiable: grep-derived test | proving test + `gate.sh` | open |
| AC6 | AC 6 | determinism (R4.2), no contract bump (R3) | Falsifiable: repeat equality; no `contract.py` edit | proving test | open |
| C1 | Constraint | counted inside the existing walk; bounded output | one Counter increment; top-N at publish | — | binding |
| C2 | Constraint | 082 — the histogram breaks down one term, never replaces it | `suffix` stays the int | — | binding |
| C3 | Constraint | 061 — omit when empty | absent on an all-indexed repo | — | binding |
| C4 | Constraint | R1.1 no language named · R4.2 deterministic · R3 no contract impact | extensions only | — | binding |

### Root cause (taxonomy: signal design)

The disclosure was **true, complete and about the wrong subject.** 159 answered *"does this product
have an adapter you have not switched on?"* — a fact about the product. The reader's question is
*"what does leaving it off cost me, here, today?"* — a fact about their repo. Four rounds proved that
the first question, answered perfectly, moves nobody. And the reason nobody closed the gap is that
the obvious join is impossible: the core cannot ask an unwired adapter what it would have claimed,
and a suffix→language table in the core is R1.1-barred.

### Blast radius

- `indexer.py`: one Counter in the existing loop, one extra return value, one `set_meta`.
- `store.py`: one meta key and one reader, mirroring 095's `ignore_sources` exactly.
- `collection.py`: one attach helper and the cap.
- `CONVENTION.md`: the payload-field table gains the fields — and went over budget, so three
  `skipped.*` rows were consolidated into one and two retold rationales pruned (R7.6).
- No store schema change, no query at answer time, no contract change.

## Phase 2 — design

### Approach

**Invert the join.** The core cannot know that `.js` belongs to TypeScript, and must not learn. So it
publishes the half it *can* know — *"2,831 files ending `.js` were skipped for their extension"* — and
`unconfigured_adapters` publishes the other half — *"an adapter named `typescript` ships and is
unwired"*. The reader (or the agent) joins them. Both halves are in the same payload, which is what
makes the join cheap for the reader.

**R1.7 decided the storage shape, and this is the clearest instance of that rule in the corpus.** The
obvious home is a new field on `CollectionCensus` — but `store.collection_census()` reads that
structure back as `{key: int(value) for …}`. A `dict[str, int]` inside it would force widening a
**coercing reader**, trading a total contract for a conditional one and loosening the type for every
existing consumer. R1.7's falsifier is literally *"a non-int inside the census structure"*. So the
histogram goes on its **own meta key** (`skipped_suffix_counts`), with its own reader that int-casts
its own values — the same shape 095 already established for `ignore_sources`, which is the same kind
of datum for the same reason.

**The whole tally is counted; only the publisher cuts it.** `_collect_with_census` returns every
extension it skipped; `collection_field` ranks and takes the top 10. So the cap has **one** definition
site (R6.7) and `suffix_kinds` is the **true** denominator rather than a capped one — which is what
makes the cut visible instead of silent (066/123's lesson about a capped list needing its total).

**Cap and tie-break, recorded:** top **10** by count, then **suffix ascending**. Ten because the
answer is *"which extensions dominate what you are not indexing"* and a long tail of one-file
extensions answers nothing; ascending suffix because equal counts must not reorder between runs
(R4.2). A suffix-less file buckets as `(none)` rather than an empty string key nothing can read.

### Scope 3 verdict — the histogram is enough now; the manifest is a real but separate change

**Enough now.** The reader gets a number about their own repo, in the payload they already call
first, with no new mechanism. What it does *not* do is state the count **as the adapter's**: it says
`.js: 2831`, not `typescript: 2831`, so the last step is the reader's.

**The manifest would close that step, and here is its cost.** Each shipped adapter would need a
committed, launch-free manifest declaring its extensions (a file in `adapters/<name>/`), read by
`unconfigured_adapters`. That is: a new file format, a new parse path in the core, and — the real
cost — **a second source of truth for extensions**, which today come only from the handshake
(`adapter.py:118`). Two sources for one fact is exactly the drift R6.7 exists to prevent, and a
manifest that disagreed with the handshake would be worse than no manifest. It would need its own
conformance check tying the two together. **Recommendation: not worth it until a third adapter
exists**, at which point the manifest also buys the `not_applicable_by_language` claim 185 keeps
declaring by hand.

### Rejected alternatives

- **Derive the count from `skipped.suffix`.** The ticket's own original proposal, and the reason it
  was reframed: that term is one total over every unindexed extension in the tree. Not derivable.
- **A suffix→language table in the core.** R1.1, CI-gated, and the pinned test asserts none appeared.
- **Launch the unwired adapter to ask for its extensions.** Explicitly out of scope, and it makes a
  status read spawn a subprocess — the thing `indexed_suffixes` was stamped at build time to avoid
  (047).
- **A field on `CollectionCensus`.** Rejected on R1.7, above. This is the design's load-bearing call.
- **Publish every extension, uncapped.** The constraint forbids it, and rightly: a repo with 400
  extensions would put 400 rows on the tool the convention says to call first.
- **Cap in the walk rather than at publish.** Cheaper by nothing measurable, and it would make
  `suffix_kinds` a capped count — a denominator that lies about its own denominator.

### Assumptions

| Assumption | Tag |
|---|---|
| `skipped.suffix` cannot carry a per-language split | verified — one integer over every unindexed suffix |
| The census reader int-casts every value | **verified, and it decided the design** — `collection_census()` is `{key: int(value)}` |
| The histogram fits inside the existing loop | verified — one `Counter` increment on a branch already taken |
| Suffix-less files exist and need a bucket | verified — `Makefile` / `LICENSE`, pinned by a test |
| A cap in one place is enough | verified — the walk keeps the whole tally, so `suffix_kinds` stays true |
| `.bb` is a skipped suffix in the fixture | **initially false, and caught by a red test** — `.bb` is one of the fixture adapter's own extensions, so it is indexed; the tie-break test now uses `.gg` |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| Count skipped extensions in the existing loop; return them; stamp them | `code_atlas/indexer.py` | one Counter, one return value, one `set_meta` | R1, AC4 | 1/1 |
| `SKIPPED_SUFFIX_COUNTS_KEY` + its int-casting reader (R1.7 sibling key) | `code_atlas/store.py` | one key, one reader | R1, AC5 | 1/1 |
| `_attach_skipped_suffixes` + the cap; rides inside `skipped` | `code_atlas/tools/collection.py` | one helper | R2, AC1, AC3 | 1/1 |
| Payload-field table row; three `skipped.*` rows consolidated; two rationales pruned | `docs/CONVENTION.md` | R7.6 | R7.2 | 1/1 |
| Proving tests (11) | `tests/test_skipped_suffix_names_the_cost.py` (new) | new file | AC1–AC6 | 1/1 |
| BACKLOG; ledger; LESSONS; working doc | `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `sibling-meta-non-int` (R1.7) — **traced.** The census structure is untouched; the histogram has its
  own key and its own int-casting reader:

  ```
  $ grep -n 'int(value)' code_atlas/store.py
  ... collection_census: {key: int(value) for key, value in parsed.items()}
  ... ignore_source_counts: {str(key): int(value) ...}
  ... skipped_suffix_counts: {str(key): int(value) ...}     <- its own, not the census's
  ```

- `prove-the-guard-fails` (R6.5) — **traced.** Three red runs below.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (a real build over a mixed tree) + logic (order and tie-break) | integration test ×2 | ✅ |
| AC2 | integration (082's arithmetic asserted on the same payload) | integration test | ✅ |
| AC3 | integration (minimal/standard/verbose, plus `build_or_update_index`, plus an all-indexed repo) | integration test ×2 | ✅ |
| AC4 | measurement (statement trace + 50 blocks timed + a walk measurement) | integration test + recorded measurement | ✅ |
| AC5 | guard (grep-derived) | integration test + `gate.sh` | ✅ |
| AC6 | logic (repeat equality) + guard (no `contract.py` edit) | integration test | ✅ |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **The last step of the join is the reader's, and that is the whole point of the exclusion.** This
  ticket ships *"`.js`: 2,831"* beside *"an adapter named `typescript` is unwired"*; it does **not**
  ship *"typescript: 2,831"*. Whether that is enough to change the outcome is an **empirical claim
  about a human**, and four rounds of evidence say the previous disclosure was not. **Expiry:** the
  next field round — if the adapter is still unwired with the histogram present, the manifest option
  in *Scope 3 verdict* is what to build, and this exclusion is the reason.

### Proving test

`tests/test_skipped_suffix_names_the_cost.py::test_the_reader_can_join_it_with_the_unwired_adapter`

### Rollback + porting

Rollback: revert three source files, delete the test file, restore the CONVENTION rows. The meta key
becomes an orphan row a pre-174 reader ignores; no rebuild needed. Porting: `app` only.

### SCOPE

`SCOPE: M` — one Counter, one meta key, one payload field; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| The join inverted — extensions published, no language named | implemented-as-approved |
| Own meta key with its own int-casting reader (R1.7), census untouched | implemented-as-approved |
| The whole tally counted; the cut only at publish; one cap site | implemented-as-approved |
| Top 10, count desc then suffix asc; `(none)` bucket | implemented-as-approved |
| `suffix` stays the int, so 082 closes | implemented-as-approved |
| Rides inside `skipped`, wherever `collection` rides | implemented-as-approved |

**One correction during execute, recorded:** I first put `SKIPPED_SUFFIX_TOP_N` in **both**
`indexer.py` and `collection.py`, and a test asserted the two were equal. That is a second definition
site for one number dressed up as a guard (R6.7) plus a dead constant (R7.4) — the walk never uses a
cap. The indexer's copy and the equality assertion are both gone.

### Empirical outputs

**AC4 — the added build cost, measured.** 20,000 paths (6× the field repo's 3,294), 18,000 skipped,
the same loop with and without the Counter:

```
without histogram:   35.52 ms for 20000 paths (18000 skipped)  {}
with histogram   :   37.71 ms for 20000 paths (18000 skipped)  {'.js': 12000, '.css': 6000}
```

**+2.19 ms over 18,000 skipped paths ≈ +0.12 µs per skipped path.** At the field repo's scale that is
about 0.4 ms, once per build. **No second pass over the tree** (it is a branch already taken) and
**no answer-time query** — the reader is one `get_meta`, asserted by a statement trace, and 50
`collection` blocks run under a 25 ms/call budget.

**Three red runs (R6.5):**

```
1. the histogram not published (the pre-174 payload)
   E  assert 'suffix_top' in {'suffix': 2, 'ignore': 0, 'untracked': 0}     7 failed, 4 passed
2. the tie-break dropped, so insertion order is published
   E  equal counts fall back to the suffix, ascending                       1 failed, 10 passed
3. the cap removed, so the payload is unbounded
   E  assert 18 == 10                                                       1 failed, 10 passed
```

**A fixture error the tests caught rather than encoded:** the tie-break case originally used `.bb`,
which is one of the fixture adapter's **own** extensions — so it was indexed, not skipped, and the
expected ordering was wrong. Renamed to `.gg`, with the reason written into the test.

**Green run:**

```
$ .venv/bin/pytest -q
2390 passed in 132.20s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_the_total_says_what_it_is_made_of` (sum ≤ `skipped.suffix`) + `test_the_output_is_bounded_and_says_so` (cap, and the cut asserted visible) |
| AC2 | `test_the_identity_still_reconciles` — 082's arithmetic **and** the histogram summing to the term exactly on a fully-covered tree |
| AC3 | `test_it_appears_wherever_skipped_suffix_appears` (minimal / standard / verbose / `build_or_update_index`) + `test_it_is_omitted_when_every_suffix_is_indexed` |
| AC4 | the measurement above + `test_the_added_build_cost_is_one_counter_increment` (one statement, no `GROUP BY`, 50 blocks timed) |
| AC5 | `test_no_suffix_to_language_mapping_entered_the_core` (grep-derived) + `gate.sh` R1.1/R2.2 green |
| AC6 | `test_the_order_and_the_tie_break_are_deterministic`; no `contract.py` edit ⇒ **no bump (R3), confirmed** |
| — | `test_the_reader_can_join_it_with_the_unwired_adapter` — the proving test: both halves of the answer in one payload; `test_a_suffix_less_file_gets_its_own_bucket`; `test_a_pre_174_index_says_nothing` (R5.6, deleted **and** corrupt stamp) |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2379 passed / 0 failed` at `1c445b1` →
`2390 passed / 0 failed`. ruff + mypy green. `scripts/gate.sh` → `GATE GREEN`.

### Learning loop

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen >= 2 | 0 routed to a destination | 0 cannot promote (reason) | 2 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `sibling-meta-non-int` (R1.7) gains 174 — and it is the rule's clearest instance: the obvious home
  for the histogram was inside a structure whose reader int-casts every value.
- `prove-the-guard-fails` (R6.5) gains 174: three red runs, one per property (published, ordered,
  bounded).
- **New:** `174-C1` (type-2, `disclose-the-readers-cost-not-the-products-fact`) — a disclosure can be
  true, complete, and about the wrong subject. *"This product has a feature you have not enabled"* is
  a fact about the product; *"N files in your repo are invisible"* is a fact about the reader. Four
  rounds of the first, all correct, moved nobody. seen=1.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. Self-checks: R1.7 traced
and load-bearing rather than cited, the cap's second definition site found and removed during execute,
a fixture error caught by a red test rather than encoded, three red runs, the build cost measured at
6× field scale, and the residual human step recorded as an exclusion with the next round as its expiry.
