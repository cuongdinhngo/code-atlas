---
id: 173
slug: coverage-claims-key-on-configured-not-indexed
title: 'Coverage claims key on what is *configured*, not on what is *indexed* — wiring an adapter deletes the coverage note and makes `indexed_suffixes` claim a language the graph does not hold'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [160, 159, 082]
---

## Why this exists (field episode, 2026-08-27 — and it is 8-A reopening through a new door)

159 and 160 exist so a zero on an index that holds only some of a repo's languages cannot read as
absence. **Both are keyed on `config.adapter_cmds` — whether the adapter is *launchable* — and neither
asks whether its files are actually *in the graph*.** So the act of flipping the switch, which every
round since 9 has asked for, produces this window:

| | before wiring | after wiring, before a full rebuild |
|---|---|---|
| `search_symbol("<a JS symbol>")` | `no_matches` **+ `unconfigured_adapters`** | `no_matches`, **note gone** |
| `indexed_suffixes` | `[".php", ".phtml"]` — true | **8 suffixes incl. `.js`** — false |
| JS files in the graph | 0 | **0** |

That is a **confident zero for an unindexed language** — 8-A's *"a false negative wearing a modelled
zero's clothes"*, and 9-C's *"the only payload this round I would call harmful"*, arriving as a
**consequence of the roll-out the retro recommends.** Round 11 §13 credited 167/159 for the harmful
shape being *"genuinely gone"*; it is gone only while the adapter stays off.

## Root cause

- `code_atlas/tools/coverage.py:22-24` — `coverage_gap(config)` returns
  `unconfigured_adapters(config.adapter_cmds)`. The gap is *"shipped but not launchable"*. Once
  `CA_<LANG>_CMD` is set the list is empty (`adapter.py:334-348`, omit-when-empty by 061), so
  `attach_coverage_note` attaches nothing — on every zero, for every tool, immediately.
- `code_atlas/indexer.py:239` — `_record_meta` runs **unconditionally**, before the
  `if to_parse or removed:` guard at `:242`. A no-op incremental therefore rewrites
  `INDEXED_SUFFIXES_KEY` (`:820`) to the newly-announced set while zero files of those suffixes were
  parsed. `indexed_suffixes` becomes a claim about the **adapters**, under a name that reads as a
  claim about the **index**.
- Nothing joins the two facts the store already holds: the suffix set in meta, and the suffixes that
  actually have rows in `files`.

## Scope

Make both claims answer *"what does the graph hold"*, not *"what could it hold"*.

1. `indexed_suffixes` reports suffixes the index **has files for** — or the payload distinguishes
   *claimed scope* from *achieved coverage* under two names. Design picks and records the rejected
   alternative; 082's collection identity must still reconcile.
2. The coverage note fires for a language that is configured but **has no indexed files**, not only
   for one that is unconfigured. The `enable` hint changes accordingly (the switch is already on; what
   is missing is a build).
3. The note stays self-gating and idempotent, and still never names the subject's own language (160's
   recorded boundary).

### Explicitly not in scope

- Why the build did nothing — [172](172_incremental-is-blind-to-a-scope-change.md). This ticket makes
  the *state* honest whatever the build did; 172 stops the state arising.
- Counting the invisible files — [174](174_unconfigured-adapters-names-the-switch-not-the-cost.md).
- Per-language node/edge statistics.

## Constraints

- **061** — a fully-wired, fully-indexed server adds nothing to any payload; a PHP-only server with no
  shipped second adapter is byte-identical to today.
- **Cost** — one bounded query at most, cached per build like the census; no per-answer scan of `files`.
- **R1.1** — keyed on suffix strings and row counts, never on a language name in the core.
- **160's boundary** — the note names the *index's* gap, not the subject's language.
- **R3** — new vocabulary, if any, is nav-level; confirm and record.

## Acceptance criteria

1. A test configures a second adapter, builds nothing, and asserts a zero answer **still** carries a
   coverage note — fails on today's code.
2. In that state `indexed_suffixes` (or its replacement pair) does not claim the unindexed suffix;
   082's `collected − skipped == kept` identity still reconciles.
3. A fully-indexed, fully-wired server is byte-identical to today (061), pinned.
4. The note remains self-gating/idempotent across the single and sweep envelopes (160 AC1e).
5. The added cost is measured; no per-answer table scan.
6. Determinism (R4.2), no language branch (R1.1), contract impact confirmed (R3).

## References

Field episode 2026-08-27, finding (3)'s consequence — surfaced while verifying findings (1)–(5) against
source, not observed directly. Round 11 §13 (*"the harmful shape is genuinely gone"* — true only while
the adapter is off), §4, §14 rows 8-A / 9-C. `code_atlas/tools/coverage.py:22-24,38-58`;
`code_atlas/adapter.py:334-348`; `code_atlas/indexer.py:239,242,820`. Related:
[160](160_a-zero-answer-never-names-the-index-language-coverage.md),
[159](159_get-index-status-does-not-name-available-but-unconfigured-adapters.md),
[082](082_claims-nobody-outside-can-check.md),
[172](172_incremental-is-blind-to-a-scope-change.md) (ship together).

## Session status

- **KEY:** 173 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, 8-ticket batch) · envelope in `.mango/run-contract-173.txt`.
- **Branch:** `feat/173-coverage-keys-on-indexed-not-configured`
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2190 passed, 0 failed` at `bfcb8a3` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

Scope 1 offers *"`indexed_suffixes` reports suffixes the index **has files for** — **or** the payload
distinguishes claimed scope from achieved coverage under two names"*, and asks design to pick. A
**how-decision**: the meta key's existing consumers settle it (see *Rejected alternatives*). Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=5 R=3 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 10 applicable — 9 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R1.8 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.4 (change-type) ✅ · §R5.6 (change-type) ✅ · §R6.1 (change-type) ✅ · §R6.2 (recalled handle: spec-driven-fixtures) ✅ · §R6.5 (change-type) ✅ · §R7.2 (change-type) ✅`
`BASELINE: green — 2190 passed, 0 failed, 0 skipped at bfcb8a3 (bare pytest, Linux host)`

**Premise:** `coverage.py:22-24` (gap = `unconfigured_adapters(config.adapter_cmds)`),
`adapter.py:334-348` (omit-when-empty), `indexer.py:820` (`_record_meta` writes
`INDEXED_SUFFIXES_KEY` from the announced set) and `store.py:37` all resolve as described.

**One premise surfaced as ambiguous, not blocking.** The ticket's root cause 2 says `_record_meta`
runs *"unconditionally, before the `if to_parse or removed:` guard at `:242`"*. **178 (merged earlier
in this batch) moved `_record_meta` to after that guard block** — it is still unconditional, so the
defect is unchanged, but the line numbers and the ordering claim no longer read literally. Recorded
rather than silently re-interpreted.

**Recall:** `spec-driven-fixtures` (R6.2, by handle — the two-language shape needs a second adapter,
and the fixture must encode the wire protocol, not a language; traced below). `160`/`8-A` (by area:
a zero that reads as absence) — the class this reopens.

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | wiring an adapter must not produce a confident zero for an unindexed language | key both claims on rows | field table | open |
| R1 | Scope 1 | `indexed_suffixes` reports what the index has files for, **or** two names | design picks; 082 must still reconcile | `collection.py:37` | open |
| R2 | Scope 2 | the note fires for configured-but-unindexed; the `enable` hint changes | a second key with a build hint | `coverage.py:22-24` | open |
| R3 | Scope 3 | the note stays self-gating and idempotent; never names the subject's own language | reuse `attach_coverage_note`'s gating | `coverage.py:38-58` | open |
| AC1 | AC 1 | configure a second adapter, build nothing, zero still carries a note — fails today | Falsifiable: red→green | proving test | open |
| AC2 | AC 2 | `indexed_suffixes` does not claim the unindexed suffix; 082's identity reconciles | Falsifiable: list + arithmetic | proving test | open |
| AC3 | AC 3 | fully-indexed, fully-wired is byte-identical (061) | Falsifiable: neither key present, no suffix pair | proving test | open |
| AC4 | AC 4 | self-gating/idempotent across single and sweep envelopes (160 AC1e) | Falsifiable: envelope carries it once, never per subject | proving test | open |
| AC5 | AC 5 | cost measured; no per-answer table scan | Falsifiable: timing + the stamp exists | proving test | open |
| AC6 | AC 6 | R4.2, R1.1, R3 | Falsifiable: grep-gates; no `contract.py` edit | `gate.sh` | open |
| C1 | Constraint | 061 — fully-wired fully-indexed adds nothing; PHP-only with no shipped second adapter byte-identical | omit both keys when empty | — | binding |
| C2 | Constraint | one bounded query at most, cached per build like the census; no per-answer scan | stamp in `_record_meta` | — | binding |
| C3 | Constraint | R1.1 — suffix strings and row counts, never a language name in the core | data-driven comparison | — | binding |
| C4 | Constraint | 160's boundary — the note names the *index's* gap, not the subject's language | unchanged gating | — | binding |
| C5 | Constraint | R3 — new vocabulary is nav-level; confirm and record | no `contract.py` edit | — | binding |

### Root cause (taxonomy: data / claim-keying)

Both claims answer *"what could the index hold"* under names that read as *"what does it hold"*.
`coverage_gap` asks whether the adapter is launchable; `indexed_suffixes` is stamped from the
announced set on every build, including a no-op. Nothing joined the suffix set in meta to the
suffixes that actually have rows in `files` — the store held both facts and never compared them.

### Blast radius

- `store.py`: two meta keys + two read methods. No schema change.
- `indexer.py::_record_meta`: two extra stamps per build.
- `coverage.py`: one new key, one new function; `coverage_gap` unchanged, so every 159/160 assertion holds.
- Five nav tools thread the stamp from inside their store block to their tail return. **No tool
  reopens the store** — the value is read once while it is already open.
- `collection.py`: `indexed_suffixes` changes meaning; `claimed_suffixes` appears only when they differ.

## Phase 2 — design

### Approach

Stamp both facts **once per build**, read them per answer:

- `_record_meta` writes `covered_suffixes` (one `LIMIT 1` probe per claimed suffix — bounded by the
  adapter count, never the row count) and `covered_languages` (one `DISTINCT` over `files.language`).
- `coverage.unindexed_languages(config, stamp)` returns configured languages absent from the stamp,
  each with `rebuild: "build_or_update_index(full=true)"` — the switch is on; what is missing is a
  build. Attached as **`unindexed_languages`**, beside `unconfigured_adapters`, both omit-when-empty.
- `collection` reports `indexed_suffixes` = held, and `claimed_suffixes` beside it **only when they
  differ** — so a fully-covered index grows no second name (061).

The stamp is read inside each tool's existing `with GraphStore(...)` block and passed to the tail
return, so no tool reopens the store and no answer scans `files`.

### Rejected alternatives

- **Redefine the `indexed_suffixes` *meta key* to mean "held".** Rejected: it is load-bearing
  elsewhere — `freshness.py:108` and `hooks/signal.py:123` read it to decide which suffixes count as
  indexable. If it meant "held", a newly-wired language's files would never register as dirty, so the
  first fix would break freshness for exactly the language the ticket is about. The meta key keeps
  meaning *claimed scope*; only the **payload** field changes meaning, which is where the misread was.
- **One key with a `reason` field** (`{language, reason: not_configured|not_indexed}`). Rejected:
  159/160 pin the `{language, enable}` shape, and 061 asks for byte-identity where nothing changed.
  Two keys keep the existing shape exactly and let a reader branch on presence, not on a string.
- **Compute coverage per answer** (`SELECT DISTINCT language FROM files` on each zero). Rejected by
  C2: a scan per answer, on the path a zero already takes.
- **Report per-language node/edge statistics.** Explicitly out of scope.

### Assumptions

| Assumption | Tag |
|---|---|
| `files.language` holds the adapter's announced name | verified (`store.py:404-408`, written by `_write`/`upsert_file`) |
| `config.adapter_cmds` keys match announced names in practice (`CA_PHP_CMD` → "php") | **verified for the shipped adapters**, and the comparison is data-driven either way (R1.1); a mismatch would over-report, never under-report |
| Every nav tool's tail return is reachable with the store closed | verified — that is why the stamp is read into a local inside the block, not passed as a store |
| A `LIMIT 1` suffix probe is bounded by adapter count | verified — ≤ 8 probes per build on the anchor's suffix set |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| `COVERED_SUFFIXES_KEY`/`COVERED_LANGUAGES_KEY`; `indexed_languages()`, `suffixes_with_files()` | `code_atlas/store.py` | two meta keys, no schema change | R1, R2, AC5 | 1/1 |
| Stamp both in `_record_meta` | `code_atlas/indexer.py` | once per build | R1, R2, AC5 | 1/1 |
| `unindexed_languages` + `UNINDEXED_KEY`; `covered_languages(store)` reader | `code_atlas/tools/coverage.py` | `coverage_gap` untouched ⇒ 159/160 hold | R2, R3, AC1 | 1/1 |
| Thread the stamp from the store block to the tail | 5 nav tools | no reopened store; no behaviour change when the stamp is absent | R2, AC1, AC4 | 1/1 |
| `indexed_suffixes` = held; `claimed_suffixes` when they differ | `code_atlas/tools/collection.py` | 082's arithmetic untouched | R1, AC2, AC3 | 1/1 |
| `second` handshake mode | `tests/fixtures/adapter/fake_adapter.py` | fixture only | AC1 | 1/1 |
| Proving tests (6) | `tests/test_coverage_keys_on_indexed.py` (new) | new file | AC1–AC5 | 1/1 |
| README; BACKLOG; ledger; working doc | `README.md`, `docs/*` | R7.2/R7.6 | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `spec-driven-fixtures` (R6.2) — **traced.** The two-language shape needed a second adapter. The new
  handshake encodes the wire protocol and an arbitrary token, not a language:

  ```
  $ grep -n -A 4 '"second": {' tests/fixtures/adapter/fake_adapter.py   # Ran at 8b26f033319211bfe4212a90564608ebec25ca26
  "second": {"name": "second", "extensions": [".cc"], "capabilities": {}, ...}
  ```

  The test also pins the shipped-adapter set with `monkeypatch.setattr(adapter, "ADAPTERS_DIR", …)`
  so 159's unwired note cannot muddy 173's — the repo's real `adapters/` would otherwise report php
  and typescript as unwired in every case.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (two real builds, two real adapters) | integration test | ✅ |
| AC2 | integration (a real graph + the 082 arithmetic) | integration test | ✅ |
| AC3 | integration (both languages present) | integration test | ✅ |
| AC4 | integration (single + sweep envelopes) | integration test | ✅ |
| AC5 | measurement (200 zero answers timed) + logic (the stamp exists) | integration test | ✅ |
| AC6 | guard (grep-gates) + logic (no `contract.py` edit) | `gate.sh` | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

AC1's shape depends on the adapter-name/config-key correspondence (`CA_SECOND_CMD` → an adapter
announcing `second`). Proven on the fixture, **not** on a real corpus: no repo with two wired
languages is available on this host. Recorded, not hidden.

### Proving test

`tests/test_coverage_keys_on_indexed.py::test_indexed_suffixes_does_not_claim_a_suffix_the_graph_has_no_files_for`
— the claim the field episode called false. Plus
`::test_a_configured_but_unindexed_language_still_carries_a_note` for AC1.

### Rollback + porting

Rollback: revert the source files, the fixture mode and the test file. The two meta keys are additive
and ignored by an older reader. Porting: `app` only.

### SCOPE

`SCOPE: M` — two stamps, one new payload key, one payload field re-keyed; branch `feat` matches.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Both facts stamped once per build in `_record_meta` | implemented-as-approved |
| `unindexed_languages` as a second key beside `unconfigured_adapters`, both omit-when-empty | implemented-as-approved |
| `indexed_suffixes` = held; `claimed_suffixes` only when they differ | implemented-as-approved |
| The stamp read inside the existing store block, never a reopened store | implemented-as-approved |
| A pre-173 index says nothing rather than guessing (R5.6) | implemented-as-approved |

No deviations. Diff ⊆ approved list.

### Empirical outputs

**Red run A — the note keys on "configured" only** (159/160's behaviour, the field state):

```
$ .venv/bin/pytest -q tests/test_coverage_keys_on_indexed.py      # Ran at bfcb8a39b44053e966fa5af62d514fc44b6d14bf
FAILED ::test_a_configured_but_unindexed_language_still_carries_a_note
FAILED ::test_the_note_is_self_gating_and_idempotent_across_the_sweep_envelope
2 failed, 4 passed
```

**Red run B — `indexed_suffixes` reports the claimed set** (today's meaning), which is the field
episode's second row exactly:

```
$ .venv/bin/pytest -q tests/test_coverage_keys_on_indexed.py      # Ran at bfcb8a39b44053e966fa5af62d514fc44b6d14bf
>       assert block["indexed_suffixes"] == [".aa"], "the graph holds only .aa files"
E       assert ['.aa', '.bb', '.cc'] == ['.aa']
1 failed, 5 passed
```

Three suffixes claimed, one held — the *"`indexed_suffixes`: 8 suffixes incl. `.js`, JS files in the
graph: 0"* row from the ticket's table.

**Green run:**

```
$ .venv/bin/pytest -q                                              # Ran at 8b26f033319211bfe4212a90564608ebec25ca26
2196 passed in 154.01s
$ .venv/bin/ruff check . && .venv/bin/mypy
All checks passed!  ·  Success: no issues found in 81 source files
```

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_a_configured_but_unindexed_language_still_carries_a_note` + red run A |
| AC2 | `test_indexed_suffixes_does_not_claim_a_suffix_the_graph_has_no_files_for` (list **and** the 082 identity re-asserted) + red run B |
| AC3 | `test_a_fully_indexed_wired_server_says_nothing_extra` — neither key, and no `claimed_suffixes` |
| AC4 | `test_the_note_is_self_gating_and_idempotent_across_the_sweep_envelope` — envelope once, never per subject, never on a confident answer |
| AC5 | `test_the_claim_is_read_from_meta_not_scanned_per_answer` — 200 zero answers under a 0.05 ms/call budget, and the stamps asserted |
| AC6 | `gate.sh` R1.1/R2.2 green (the comparison is over strings from the handshake); no `contract.py` edit ⇒ no bump |

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2190 passed / 0 failed` at `bfcb8a3` →
`2196 passed / 0 failed`. ruff + mypy green.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`173-C1` (type-2, `a-capability-claim-is-not-a-coverage-claim`, seen: 173) recorded as `proposed`.
A field named for what the system *holds* must be keyed on rows, not on configuration — and enabling
a capability is the moment the two diverge, so a note that keys on configuration goes quiet exactly
when it is most needed. Falsification: not falsified; red run A demonstrates the quiet directly.
seen=1 → stays in `lessons_path`.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived — nothing but the author
looked at this diff; recorded as line one of `DISCLOSURE`. No `Reviewed at` marker ⇒ the stale-review
guard is waived. Self-checks: two red runs reproducing both halves of the field table, full suite
delta-green, ruff/mypy green.
