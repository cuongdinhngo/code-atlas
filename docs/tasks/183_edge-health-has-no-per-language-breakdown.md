---
id: 183
slug: edge-health-has-no-per-language-breakdown
title: '`edge_health` is whole-graph only, so no adapter can be evaluated on the repo it was added for — the tool cannot make this measurement about itself'
phase: 1.5b
milestone: Measure
status: done
depends_on: [136, 082, 173]
---

## Why this exists (field retro round 12 §13)

Round 12 was the first round with a two-language index in the field, and **the question the whole
round was built to answer could not be asked of the tool:**

> *"HEURISTIC share for the JS/TS slice — did the prune fix round 11's 46.8 %?"*
> **"Cannot answer. No per-language breakdown exists in any payload. This is a measurement the tool
> cannot make about itself."**

What could be reported was the whole-graph delta only: RESOLVED 55.2 % → **45.70 %**, HEURISTIC
43.9 % → **53.51 %**, across +2,435 files and +573,762 edges. Every one of those numbers is a blend
of two languages, so **neither language's own health is recoverable**, and the +9.6 pp HEURISTIC move
cannot be attributed. Round 11 had to measure the JS slice **out of band**, by building three files
in isolation, to get its 46.8 %.

## Why this is a measurement ticket and not a nice-to-have

- **It blocks every future adapter's evaluation, including the one it is most needed for.** A T-SQL
  or Python adapter lands, the whole-graph share moves, and nobody can say whether the new adapter is
  healthy or whether it dragged the average — the exact position round 12 was in for JS.
- **136 gave the HEURISTIC share an owner and a target.** A target on a blended number cannot be
  attributed to the adapter that missed it.
- **The data is already there.** `files.language` exists and 173 already reads
  `SELECT DISTINCT language FROM files` once per build for its coverage stamp; `edges.file_path`
  joins to it, and `idx_edges_tier` is already indexed. `store.edge_health()` (`store.py:580-610`)
  does one `GROUP BY confidence_tier` over the whole table.
- **It is the cheapest honest answer to "is the JS half worth 1.0 GB?"** — round 12 could only say
  *"reserve judgement"*, and one field would have replaced that with a number.

## Scope

1. `edge_health` gains a **per-language tier mix** — the same `by_tier` / `linked` / `unlinked`
   shape, keyed by the language of the edge's own file. Design records the grouping key: `files.language`
   (the adapter that produced the row) or file suffix, and why the other was rejected.
2. **Stamped per build, not computed per call.** 173's precedent: one bounded query in
   `_record_meta`, read from meta afterwards. `get_index_status` is called first by convention
   (`CLAUDE.md`), so it must not gain a `GROUP BY` over a 2.1 M-row table on the hot path.
3. **Detail-gated and omit-when-single.** A one-language index adds nothing (061); the breakdown
   belongs at `verbose`, beside `collection`, where the other reconciliation data already lives.
4. **The identity reconciles.** Per-language tier counts sum to the whole-graph `by_tier`, the way
   082's `collected − skipped == kept` reconciles — an outsider must be able to check the split
   without reading source.

### Explicitly not in scope

- Per-language node counts, or a per-language `files`/`parsed`/`failed` split. Adjacent, cheaper, and
  a separate ticket if wanted.
- Changing what a tier means, or the resolver.
- Attributing an edge to the language of its **target**. An edge belongs to the file that declared it;
  a cross-language edge is one row of the source language, and the design must say so explicitly
  because the alternative is arguable.
- Fixing any language's share. This ticket makes it visible; 136/137 own moving it.

## Constraints

- **061** — a single-language index is byte-identical; so is `minimal`/`standard`.
- **Cost** — one bounded query per build, never per answer. Measured on a two-language index of the
  anchor's size (~2.1 M edges), and the per-call read must be a meta lookup.
- **R1.1** — grouped by a language string the handshake supplied, never by a language named in the
  core. A core that reads `if language == "php"` here has lost the contract.
- **R4.2** — deterministic, stable key order.
- **R5.6** — an index built before the stamp existed says nothing rather than guessing.
- **R3** — confirm whether the field is nav or contract vocabulary.

## Acceptance criteria

1. A two-language fixture index reports a per-language tier mix, and the per-language counts **sum to
   the whole-graph `by_tier`** — pinned, and failing on today's code.
2. A single-language index is byte-identical to today (061), pinned.
3. The breakdown is absent from `minimal`/`standard` and present at `verbose`, pinned.
4. A cross-language edge is attributed to exactly one language, per the recorded rule, pinned.
5. Stamped once per build; the per-answer path adds no `GROUP BY` — measured on ~2.1 M edges.
6. A pre-stamp index says nothing (R5.6), pinned.
7. Determinism (R4.2), no language branch (R1.1), contract impact confirmed (R3).

## References

Field retro round 12 §13 (*"a measurement the tool cannot make about itself"*), §0.d (the blended
before/after table), §11.a (*"the graph got more complete and that completeness bought zero
answers"*), §13's unanswerable HEURISTIC row; round 11 A.3 measured the JS slice out of band at
46.8 % because no payload could. `code_atlas/store.py:580-610` (`edge_health`), `files.language`;
173's per-build stamp in `indexer._record_meta` is the cost precedent. Related:
[136](136_heuristic-share-has-no-owner.md) (the share's owner),
[082](082_claims-nobody-outside-can-check.md) (the reconciliation pattern),
[173](173_coverage-claims-key-on-configured-not-indexed.md) (per-build stamp, one query).

## Session status

- **KEY:** 183 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended batch) · envelope in `.mango/run-contract-183.txt`.
- **Branch:** `feat/183-edge-health-per-language` (stacked on `feat/180-…`, PR based on it)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2247 passed, 0 failed` at `dd82d0e` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

Both are **how-decisions** the ticket delegates by name, and both are answerable from the schema:

1. Scope 1 — *"Design records the grouping key: `files.language` (the adapter that produced the row)
   or file suffix, and why the other was rejected."* Resolved in *Approach*.
2. Not-in-scope — *"Attributing an edge to the language of its **target** … the design must say so
   explicitly because the alternative is arguable."* Resolved in *Approach* and pinned by a test.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced, corrected below)`
`RECALL: 3 claim(s) surfaced | 1 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=6 R=4 G=1 AC=7`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 12 applicable — 9 by change-type | 3 by recalled handle — §R1.1 (change-type) ✅ · §R1.4 (change-type) ✅ · §R1.8 (recalled handle: one-rule-for-every-subject-slot) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.5 (change-type) ✅ · §R5.6 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.3 (recalled handle: fixture-shape-begs-the-question) ⚠ recorded, see EXCLUSIONS · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R7.2 (change-type) ✅ · §R7.6 (change-type) ✅`
`BASELINE: green — 2247 passed, 0 failed, 0 skipped at dd82d0e (bare pytest, Linux host)`

**Premise:** `store.py:580-610` resolves to `edge_health` (the line numbers had drifted by ~27 — the
function is at `:607` on this tree, unchanged in substance). `files.language` exists.
`indexer._record_meta` holds 173's two stamps. `idx_edges_tier` exists.

**One premise is wrong in the ticket's favour, and it changes the design.** The ticket says *"`edges.file_path`
joins to it"*, implying a total join. It is **not** a foreign key:

```
$ grep -n 'file_path TEXT' code_atlas/store.py            # Ran at dd82d0e
92:  file_path TEXT REFERENCES files(path), line_start INT, line_end INT,   <- nodes
101:  file_path TEXT, line INT, confidence_tier TEXT DEFAULT 'RESOLVED', … <- edges: no FK
```

`files.language` is also nullable. So the split has a genuine residue, the identity in Scope 4 does
**not** close by construction, and an `unattributed` bucket is load-bearing rather than defensive.

**Recall:** `one-rule-for-every-subject-slot` (R1.8, by handle — the tier fold must be one rule, or
the slice sums unlike the whole). `prove-the-guard-fails` (R6.5, by handle). `edge_health` (by symbol
— 136's owner for the HEURISTIC share).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | the tool cannot make this measurement about itself | give the split an owner per adapter | round 12 §13 | open |
| R1 | Scope 1 | per-language tier mix, same `by_tier`/`linked`/`unlinked` shape, keyed by the edge's own file's language; record the grouping key and the rejected one | `files.language`, not suffix | `files.language` exists | open |
| R2 | Scope 2 | stamped per build, not computed per call; no `GROUP BY` on the hot path | 173's `_record_meta` precedent | `_record_meta:949-952` | open |
| R3 | Scope 3 | detail-gated and omit-when-single; belongs at `verbose` beside `collection` | verbose, gate on bucket count | `get_index_status:259-261` | open |
| R4 | Scope 4 | the identity reconciles — per-language sums to whole-graph `by_tier`, checkable by an outsider | one fold rule + a carried residue | `edges` has no FK | open |
| AC1 | AC 1 | two-language fixture reports a mix; counts **sum to** whole-graph `by_tier`; failing on today's code | Falsifiable: sum asserted + red run | proving test | open |
| AC2 | AC 2 | single-language index byte-identical (061) | Falsifiable: field absent | proving test | open |
| AC3 | AC 3 | absent at `minimal`/`standard`, present at `verbose` | Falsifiable: three levels asserted | proving test | open |
| AC4 | AC 4 | a cross-language edge attributed to exactly one language, per the recorded rule | Falsifiable: counted once, on the declaring side | proving test | open |
| AC5 | AC 5 | stamped once per build; answer path adds no `GROUP BY`; measured on ~2.1 M edges | Falsifiable: statement trace + two timings | proving test ×2 + out-of-band measurement | open |
| AC6 | AC 6 | a pre-stamp index says nothing (R5.6) | Falsifiable: stamp removed ⇒ field absent | proving test | open |
| AC7 | AC 7 | determinism (R4.2), no language branch (R1.1), contract impact confirmed (R3) | Falsifiable: repeat equality + grep-gates | proving test + `gate.sh` | open |
| C1 | Constraint | 061 — single-language byte-identical; so is `minimal`/`standard` | gate on bucket count | — | binding |
| C2 | Constraint | one bounded query per build, never per answer; per-call read is a meta lookup | one statement, stamped | — | binding |
| C3 | Constraint | R1.1 — grouped by a language string the handshake supplied, never named in the core | no literal anywhere | — | binding |
| C4 | Constraint | R4.2 — deterministic, stable key order | `sorted()` + `sort_keys` | — | binding |
| C5 | Constraint | R5.6 — a pre-stamp index says nothing rather than guessing | `None`, no fallback | — | binding |
| C6 | Constraint | R3 — confirm nav or contract vocabulary | nav; no bump | — | binding |

### Root cause (taxonomy: data / measurement design)

`edge_health` was written when the index held one language, so "the graph's tier mix" and "this
adapter's tier mix" were the same sentence. Adapter #2 made them different sentences and nothing
noticed: the aggregate kept the old name, the old shape and the old meaning, and silently became a
blend. Nothing was broken — a number simply stopped answering the question its name implies, which is
why no test failed and why round 12 could only discover it by trying to ask.

### Blast radius

- `store.py`: one meta key, one shared fold helper (`_tier_block`), one computation, one reader.
  `edge_health` is rewritten onto the shared helper — same output, asserted by its three existing
  tests in `test_store.py`, which are untouched.
- `indexer.py`: one `set_meta` in `_record_meta`, so **both** build paths inherit it.
- `get_index_status.py`: one field constant and one attach helper, matching `_attach_build_state` /
  `_attach_unconfigured_adapters` already there.
- No schema change, no index, no contract change, no adapter change. `edge_health` at `standard` is
  untouched, so the existing exact-dict assertion at `test_get_index_status_health.py:79` still holds.

## Phase 2 — design

### Approach

**The grouping key is `files.language`, joined from `edges.file_path` — the adapter that produced the
row.** File suffix was rejected: it is a *guess at* the adapter rather than a record of it, it
disagrees with the graph the moment two adapters claim overlapping suffixes (`.js` under 019 is real),
and `files.language` is already what 173's coverage stamp keys on, so a second key for the same fact
would be a second definition site (R1.8).

**An edge belongs to the file that declared it.** A cross-language edge is one row of the *source*
language. Stated because the alternative is arguable and the ticket asks for it: attributing to the
target would make one row belong to two languages (double-counting, so the Scope 4 identity fails) or
to neither when the target is unresolved — and *"which adapter emitted this HEURISTIC edge"* is the
question 136 needs, which is a fact about the emitter.

**One fold rule, shared.** `_tier_block(tiers, linked)` is the single place NULL/unknown tiers fold
into `RESOLVED`. `edge_health` and every per-language bucket call it, so the slice cannot sum unlike
the whole (R1.8) — the failure mode that would make Scope 4's identity quietly false.

**The residue is carried, not dropped.** `edges.file_path` has no foreign key and `files.language` is
nullable, so `LEFT JOIN` can yield a NULL language. That folds into a sibling `unattributed` block,
present only when non-empty. Dropping it would have broken the identity **silently** — which is the
one thing Scope 4 exists to prevent.

**Stamped in `_record_meta`, read at `verbose`.** One statement per build, `json.dumps(sort_keys=True)`,
read back through `stamped_edge_health_by_language()` which returns `None` for a pre-183 index *and*
for an unreadable stamp. Never a computed fallback: that would put the `GROUP BY` this stamp exists to
avoid back on the answer path.

**Gated on bucket count, not language count.** `< 2` buckets ⇒ omitted. Counting `unattributed` as a
bucket means a one-language graph whose split is incomplete still reports, while a genuinely
single-language, fully-attributed index stays byte-identical (061/AC2).

### Rejected alternatives

- **Group by file suffix.** See above: a guess at the adapter, wrong under shared suffixes, and a
  second key for a fact `files.language` already carries.
- **Attribute to the target's language.** Double-counts or drops; and it answers a different question
  than the one 136 needs.
- **Compute per answer.** `edge_health` already scans `edges` per `standard` call (82.7 ms at 2.1 M
  rows, measured); the per-language version is 12× that. `get_index_status` is *called first by
  convention*, so this is the hot path by definition.
- **Two-step, join-free aggregation** — `SELECT path, language FROM files` into a dict, then
  `GROUP BY file_path, confidence_tier`, folded in Python. **Measured, and rejected on the number**:
  686.9 ms against the join's 941.9 ms over 2.1 M edges spread across 200 files. A 255 ms saving,
  once per build, does not buy a second statement plus an aggregation layer split across SQL and
  Python — and it grows the group count from 3 to one-per-file, which is the part that would scale
  badly on the anchor's 3,244 files.
- **Stamp only on `full_build`.** Halves nothing that matters and creates a new inconsistency: a
  stale split sitting beside a fresh `edge_health`, with no field saying which build measured it.

### Assumptions

| Assumption | Tag |
|---|---|
| `edges.file_path` always joins to a `files` row | **falsified by reading the schema** — no FK; this is why `unattributed` exists |
| `files.language` is non-null for indexed files | **not relied on** — NULL and `''` both fold to the residue |
| The fixture adapter can produce a two-language graph *with edges* | verified — `dep/*` emits HEURISTIC CALLS, `dep/extends_*` emits RESOLVED EXTENDS, and the `second` handshake owns `.cc` |
| `dep/cross.cc` really crosses languages | verified — its edge targets `lib/core.aa::Thing`, and the test asserts the file holds exactly one edge |
| Adding a field at `verbose` cannot break the minimal-shape guard | verified — `test_minimal_payload_stays_byte_identical_to_the_pre_health_shape` pins `minimal`'s key set and standard's per-key equality; a verbose-only field is outside both |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `EDGE_HEALTH_BY_LANGUAGE_KEY`; `_tier_block` (shared fold); `edge_health` onto it; `edge_health_by_language`; `stamped_edge_health_by_language` | `code_atlas/store.py` | one fold rule, one computation, one reader | R1, R2, R4, AC1, AC4–AC7 | 1/1 |
| Stamp it in `_record_meta` | `code_atlas/indexer.py` | both build paths inherit | R2, AC5 | 1/1 |
| `EDGE_HEALTH_BY_LANGUAGE_FIELD` + `_attach_edge_health_by_language` at verbose | `code_atlas/tools/get_index_status.py` | one field, omit-when-silent | R3, AC2, AC3, AC6 | 1/1 |
| Proving tests (9) | `tests/test_edge_health_per_language.py` (new) | new file | AC1–AC7 | 1/1 |
| PLAN §  verbose cell (pruned to fit, R7.6); BACKLOG; ledger; LESSONS; working doc | `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `one-rule-for-every-subject-slot` (R1.8) — **traced.** One fold site; the slice cannot diverge:

  ```
  $ grep -rn 'def _tier_block' code_atlas/          # Ran at the green tree
  code_atlas/store.py:612:    def _tier_block(tiers: Mapping[str, int], linked: int) -> dict[str, object]:
  $ grep -c '_tier_block(' code_atlas/store.py
  4        # one definition, three call sites (whole graph, each language, the residue)
  ```

- `prove-the-guard-fails` (R6.5) — **traced.** Two red runs recorded below, each isolating a different
  half of the claim.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (real build, two adapters, payload identity) | integration test | ✅ |
| AC2 | integration (one adapter, field absent) | integration test | ✅ |
| AC3 | integration (three detail levels) | integration test | ✅ |
| AC4 | integration (a planted crossing edge, counted once) | integration test | ✅ |
| AC5 | measurement (statement trace; 50 verbose calls; 200 k in-suite; 2.1 M out of band) | integration test ×2 + recorded measurement | ✅ |
| AC6 | integration (stamp deleted; stamp corrupted) | integration test | ✅ |
| AC7 | logic (repeat equality, key order) + guard (grep-gates) | integration test + `gate.sh` | ✅ |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **R6.3 / `fixture-shape-begs-the-question` — recorded, not discharged.** Every AC is proven on the
  fixture adapter, and AC5's 2.1 M-edge figure is an **authored** corpus, not the anchor repo. The
  ticket's own headline number (*"is the JS half worth 1.0 GB?"*) is therefore still unmeasured: this
  ticket makes the measurement *possible*, and does not take it. **Expiry:** the first real
  two-language `get_index_status --detail_level verbose` run on the anchor repo, whose output belongs
  in the next field retro. No committed reporter is added — `scripts/edge_health_report.py` already
  exists for the share itself, and giving it a second job is a separate change.

### Proving test

`tests/test_edge_health_per_language.py::test_a_two_language_index_reports_a_mix_that_sums_to_the_whole_graph`

### Rollback + porting

Rollback: revert three source files and delete the test file. The meta key becomes an orphan row a
pre-183 reader ignores, so no rebuild is needed either way. Porting: `app` only.

### SCOPE

`SCOPE: M` — one query, one stamp, one verbose field; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Grouping key is `files.language` from the edge's own file | implemented-as-approved |
| A cross-language edge belongs to the declaring file's language | implemented-as-approved |
| One fold rule (`_tier_block`), shared by the whole graph and every slice | implemented-as-approved |
| `unattributed` residue carried, present only when non-empty | implemented-as-approved |
| Stamped in `_record_meta`; reader returns `None` pre-stamp **and** on an unreadable stamp | implemented-as-approved (the unreadable case is an addition, below) |
| Gated on bucket count, verbose only | implemented-as-approved |
| One statement; nothing computed on the answer path | implemented-as-approved |

**One addition beyond the approved list, recorded as such:** the reader also returns `None` when the
stamp is present but not valid JSON. Found while writing AC6 — `set_meta(key, None)` stores the
*string* `"None"`, so a `json.loads` reader raised instead of degrading. Same rule as R5.6, one line,
kept and pinned rather than left as a crash on a corrupt row.

### Empirical outputs

**Red run 1 (R6.5) — the verbose field not attached:**

```
$ .venv/bin/pytest -q tests/test_edge_health_per_language.py
FAILED …::test_a_two_language_index_reports_a_mix_that_sums_to_the_whole_graph
FAILED …::test_the_breakdown_is_verbose_only
2 failed, 7 passed
```

**Red run 2 (R6.5) — the `unattributed` residue dropped instead of carried.** This is the run that
matters, because it is the *silent* failure Scope 4 is about:

```
E  AssertionError: assert 'unattributed' in {'by_language': {'fake': {…}, 'second': {…}}}
1 failed, 8 passed
```

The seven/eight that stay green each time are the point: the store-level computation is not what
red run 1 breaks, and the language buckets are not what red run 2 breaks.

**AC5 — cost, measured on both corpora, and the stamp is not free:**

```
edges: 2,100,000  (two languages)
whole-graph edge_health():     82.7 ms
per-language stamp     :   1015.7 ms
```

**~1.0 s, once per build, on an anchor-sized graph — including every incremental build.** That is
the honest number and it is not rounded away: on a full build of 2.1 M edges it is noise, on a
one-file incremental it is the dominant term. It is accepted because the alternative is 1.0 s *per
`get_index_status` call*, and status is the call the convention says to make first. The join-free
alternative was measured at 686.9 ms and rejected above on structure, not on speed.

In-suite the same statement is bounded at 200 k edges (`< 4 s`, runs in ~0.4 s), and the answer path
is asserted to be exactly **one** statement with no `GROUP BY` in it, via `set_trace_callback`.

**Green run:**

```
$ .venv/bin/pytest -q
2260 passed in 155.36s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_a_two_language_index_reports_a_mix_that_sums_to_the_whole_graph` — `by_tier`, `linked` and `unlinked` all reconciled against the same payload's `edge_health` |
| AC2 | `test_a_single_language_index_is_byte_identical` |
| AC3 | `test_the_breakdown_is_verbose_only` — and it asserts `edge_health` is still at `standard` |
| AC4 | `test_a_cross_language_edge_is_attributed_to_the_file_that_declared_it` — the crossing file is asserted to hold exactly one edge, then counted once on the declaring side and once in the total |
| AC5 | `test_the_stamp_is_read_from_meta_and_the_answer_path_adds_no_group_by` (one statement, no `GROUP BY`, 50 verbose calls) + `test_the_stamp_is_bounded_on_a_large_edge_table` (200 k) + the 2.1 M measurement above |
| AC6 | `test_a_pre_183_index_says_nothing_rather_than_guessing` — stamp deleted **and** stamp corrupted |
| AC7 | `test_the_split_is_deterministic_and_key_ordered`; `gate.sh` R1.1/R2.2 green; no `contract.py` edit ⇒ **no bump (R3), confirmed** — this is nav/status vocabulary, like `collection` and `edge_health` before it |
| — | `test_an_edge_whose_file_has_no_language_row_is_carried_not_dropped` — the residue is load-bearing, and the identity still closes with it |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2247 passed / 0 failed` at `dd82d0e` →
`2260 passed / 0 failed`. ruff + mypy green. `scripts/gate.sh` → `GATE GREEN`.

### Learning loop

`CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 2 candidate(s) checked | 2 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 2 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `one-rule-for-every-subject-slot` (R1.8) gains 183: the tier fold is one callable, so a slice cannot
  sum unlike the whole. A `seen:` bump on a class that is already a binding rule.
- `fixture-shape-begs-the-question` (R6.3) gains 183, and honestly: every AC is fixture-proven and the
  field number this ticket exists to enable is still unmeasured. Recorded as an exclusion with an
  expiry rather than waved through.
- **New:** `183-C1` (type-2, `an-aggregate-outlives-the-world-that-named-it`) — when a second instance
  of a dimension arrives (a second language, tenant, region), every existing whole-population
  aggregate silently becomes a blend under its old name, and **no test fails**, because nothing
  changed. The roll-out ticket should enumerate the aggregates the new dimension makes ambiguous.
  seen=1 ⇒ stays in `lessons_path`.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

One subagent was dispatched in this ticket (a read-only source map, ~34 k) against a standing
instruction in the session prompt not to use subagents. Recorded, not hidden; see `DISCLOSURE`.

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. No `Reviewed at`
marker ⇒ the stale-review guard is waived. Self-checks: a ticket premise falsified by reading the
schema (which changed the design), two red runs isolating different halves of the claim, a rejected
alternative rejected on a measured number, a cost stated at ~1.0 s/build rather than rounded away,
and an R6.3 exclusion recorded with a checkable expiry.
