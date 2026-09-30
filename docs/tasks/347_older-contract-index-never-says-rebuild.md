---
id: 347
slug: older-contract-index-never-says-rebuild
title: 'An index from an older contract reads as behind or current, never as rebuild-required'
phase: 2
milestone: Adoption
status: done
depends_on: [201, 316, 322]
---

## Why this exists

After a contract bump, every existing index needs a full rebuild. The status payload knows it:
`get_index_status` sets `full_rebuild_required` (`code_atlas/tools/get_index_status.py:238`).

The one sentence every channel lifts does not say so. `_compose_summary`
(`code_atlas/tools/get_index_status.py:311`) reads `staleness` and never reads
`full_rebuild_required`. That summary is the MCP `instructions` state line (`instructions._state`)
and the `code-atlas-state` hook line (`code_atlas/hooks/state.py`). So an anchor project that
upgrades code-atlas is never told its index is from another era.

## Evidence (this repo, 2026-09-29, server at contract v13)

- `graph.db` meta: `contract_version = 10`, `schema_version = 6`.
- `get_index_status()["summary"]` returns
  `behind @ bfb1e74 · 622 files · 8,456 symbols (read tools still serve) — run build_or_update_index`.
- The same payload holds `full_rebuild_required = {'reason': 'contract_rebuild_required', 'route':
  'code-atlas-build --full', 'in_band_option': 'allow_full_rebuild=true'}`.
- Following the summary's route (`build_or_update_index`, `full=false`) is refused
  (`contract_rebuild_required`). The advice points at a call that cannot succeed.
- When HEAD has not moved, the summary reads `current … · healthy`. The state hook is then silent
  (`state.py`: silent when `staleness == current`). The grep nudge (345) is silent too, because an
  older index stamps no `symbol_shapes`. Nothing tells the user why.

## Scope

1. When `full_rebuild_required` is set, the summary names it, whatever the staleness: the stored and
   current contract versions, and the route that works (`code-atlas-build --full`, or
   `allow_full_rebuild=true` in band). It stays one sentence, lifted (316, R6.7).
2. The state hook speaks for such an index even when it is `current`.
3. Nothing else changes: no auto-rebuild (202: a hook never starts a full build).

## Acceptance criteria

- **AC1:** On an index whose stored `contract_version` is below `CONTRACT_VERSION`, the summary
  names both versions and the full-rebuild route. It does not tell the user to run
  `build_or_update_index` without the opt-in. This holds for `behind` and for `current`.
- **AC2:** On that index at an unmoved HEAD, `code-atlas-state` prints the line on `SessionStart`.
- **AC3:** The server `instructions` carry the same line and still fit `CLIENT_CAP` (343).
- **AC4:** A same-era index's summary is byte-identical to today's.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 347 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer merges PR #10, then PR [#11](https://github.com/cuongdinhngo/code-atlas/pull/11) (retarget to `main` once #10 merges). **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun`; *"with
  skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `fix/347-rebuild-required-summary`, stacked on `fix/346-signal-reaches-the-model` (PR #10).
  The stack exists only so the two tickets' ledger rows cannot conflict; there is no code dependency.
  Contract: `.mango/run-contract-347.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 2 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**Premise.** Every reference resolves:
- `get_index_status.py`: `full_rebuild_required` (then `:238`) and `_compose_summary` (then `:311`).
- `instructions._state`.
- `state.py`, which is silent on `current`.
- `CLIENT_CAP`.
- the `contract_rebuild_required` refusal.

**Recall.**
- By area: `343-C1`, the 2,048-character prefix.
- By handle: `343-C2` and `344-C3`. Both apply because the payload field gains two keys, which is a
  shared vocabulary.

**Refine skipped.** The ticket names the channel, the words and the ACs, and holds no product
decision.

## Phase 1 — analysis

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 2 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Why this exists, Evidence, Scope, Acceptance criteria) | 4 decomposed | ROWS: C=2 R=3 G=1 AC=4`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/7 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

### BASELINE

The base is `fix/346-signal-reaches-the-model` at `ad366bad`. Its full gate ran green:
`GATE GREEN — all 21 checks passed` (346, Phase 4). It was not re-run here: this is the untouched
tree, and the checker refuses a pre-change evidence block (SG-2).

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "an anchor project … is never told its index is from another era" | the lifted sentence names the era | met |
| C1 | Scope 1 | "one sentence, lifted (316, R6.7)" | composed from payload fields only | constraint |
| C2 | Scope 3 | "no auto-rebuild (202)" | no build path touched | constraint |
| R1 | Scope 1 | "the summary names it, whatever the staleness … versions … route" | new first branch after `not indexed` | met |
| R2 | Scope 2 | "The state hook speaks … even when it is `current`" | the silence test also requires no pending rebuild | met |
| R3 | Scope 3 | "Nothing else changes" | same-era payloads untouched | met |
| AC1 | AC | "names both versions and the full-rebuild route … behind and … current" | unit and real-store tests | met |
| AC2 | AC | "`code-atlas-state` prints the line on `SessionStart`" | hook test and live run | met |
| AC3 | AC | "`instructions` carry the same line and still fit `CLIENT_CAP`" | cap test (N = 6), real render, live probe | met |
| AC4 | AC | "same-era … byte-identical" | existing exact-string pins, plus omit-when-empty at minimal | met |

### Clarifications — 3, all self-resolved

1. **Where the versions come from.** The versions ride inside the `full_rebuild_required` field
   itself (`stored_contract` / `server_contract`), so the summary stays a pure function of its
   payload (C1). `contract_version` is only on `standard`+ (`get_index_status.py`, `enriched`).
2. **`minimal`.** The field is attached there too. The ticket says "the summary names it" with no
   level named, and the summary is on every level (316, `test_index_status_summary.py`). It is
   omitted when nothing is pending, so a same-era `minimal` payload is unchanged (AC4).
3. **"below" vs "differs".** `contract_rebuild_required` is `!=` (`indexer.py:348`). The wording
   is neutral (`index contract vX, server vY`), so a downgrade reads correctly too.

### Blast radius

- **Producers:** `get_index_status.py` (`_compose_summary`, the field's two attach sites) and
  `state.py` (silence).
- **Consumers of the summary:** `instructions._state`, `state.state_line`, and the lead key of
  every `get_index_status` payload.
- **Consumers of the field:** `tests/test_contract_rebuild_refusal.py`, which reads `reason` and
  `route`. `build_or_update_index`'s refusal builds its own payload (`_contract_refused`) and never
  reads this field.
- **Docs:** `docs/TOOLS.md`, in the `get_index_status` row and the state-line section.

### Rule sections

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ nothing names a language, §R4.2 (change-type) ✅ the summary is a pure function of the payload so identical input gives identical text, §R6.5 (change-type) ✅ the same-era absence is asserted at minimal and standard not assumed, §R6.7 (change-type) ✅ versions and routes are read from the one field and the indexer constants never retyped`

## Phase 2 — design

### Approach

1. `_attach_rebuild_pending(status, store)` is the one attach site. It adds `stored_contract` and
   `server_contract` to the field. It is called from `_attach_build_state` (`standard`+) and from
   the `minimal` path.
2. `_compose_summary`: after `not indexed`, a pending rebuild returns
   `rebuild required @ <rev> · <scale> — index contract vX, server vY — run \`<route>\` (or
   build_or_update_index <in_band_option>)`.
3. `state.state_line`: `current` is silent only when no rebuild is pending.
4. Tests:
   - the pure-function summary on `current` and on `behind`;
   - the real store at `minimal` and at `standard` (the proving test);
   - `minimal`'s same-era absence;
   - the state hook at an unmoved HEAD;
   - the cap test's N going from 5 to 6.
5. Docs: `TOOLS.md`.

### Rejected alternatives

- **Read `contract_version` off the payload.** It is absent at `minimal`, and adding it there
  changes every same-era `minimal` payload (AC4).
- **Recompute `contract_rebuild_required` inside `_compose_summary`.** That would be a second source
  of truth, and the summary would no longer be a pure function (316).

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| A1 | The new sentence keeps instructions under `CLIENT_CAP` on the widest state | verified — cap test and real render (1,759 ≤ 2,048) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | attach site and summary branch | `code_atlas/tools/get_index_status.py` | every status payload (omitted when same-era) | R1, R3 | 1/1 |
| 2 | silence rule | `code_atlas/hooks/state.py` | SessionStart / PreCompact line | R2 | 1/1 |
| 3 | tests | `tests/test_contract_rebuild_refusal.py`, `tests/test_index_status_summary.py`, `tests/test_session_state_hook.py`, `tests/test_server_instructions.py` | proof collateral | AC1–AC4 | 4/4 |
| 4 | docs | `docs/TOOLS.md` | doc budgets | R1, R2 | 1/1 |

`HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines` — traced.** I ran `.venv/bin/ruff format --diff
  code_atlas/tools/get_index_status.py`. The only proposal was to delete one blank line at `:533`,
  a line this change did not touch, and it was not applied. `state.py` → `1 file already
  formatted`.
- **`verify-the-shipped-artifact-not-the-working-tree` — does not apply**, because the change ships
  no plugin file and no generated artifact.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | real-store status at minimal and standard | n/a | ✅ |
| AC2 | integration | the hook's `main` on stdin, plus a live console-script run | n/a | ✅ |
| AC3 | runtime/3p | cap test, plus a live `claude -p` quoting the instructions' first line | n/a | ✅ |
| AC4 | logic | the existing exact-string pins, plus the omit-when-empty test | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_contract_rebuild_refusal.py -k pending_rebuild_at_an_unmoved_head`.
Before the change the summary starts `current …` (see the ticket's Evidence), so the test fails.
After the change it passes.

### Rollback

`git revert`. One repo, no migration.

## Phase 3 — execute

Commit `c95ff050` on `fix/347-rebuild-required-summary`.

Ran at c95ff050

```
$ .venv/bin/python -m pytest -q tests/test_contract_rebuild_refusal.py tests/test_index_status_summary.py tests/test_session_state_hook.py tests/test_server_instructions.py
46 passed in 10.61s
$ .venv/bin/python -m pytest -q tests/test_contract_rebuild_refusal.py -k pending_rebuild_at_an_unmoved_head
2 passed, 11 deselected in 1.69s
```

**Live, on this repo's own index** (contract v10, server v13):

Ran at c95ff050

```
$ echo '{"hook_event_name":"SessionStart","source":"startup"}' | CLAUDE_PROJECT_DIR=$PWD .venv/bin/code-atlas-state
code-atlas: rebuild required @ bfb1e74 · 622 files · 8,456 symbols — index contract v10, server v13 — run `code-atlas-build --full` (or build_or_update_index allow_full_rebuild=true)
$ instructions.render(...) → 1759 chars (CLIENT_CAP 2048)
$ claude -p "… Quote its FIRST line exactly …" --strict-mcp-config --mcp-config ca347.json
rebuild required @ bfb1e74 · 622 files · 8,456 symbols — index contract v10, server v13 — run `code-atlas-build --full` (or build_or_update_index allow_full_rebuild=true)
```

**Sweep.**
- Axis 1: the diff is the 7 files in the change list.
- Axis 2: Approach bullets 1–5 were implemented as approved. No deviation.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `c95ff050`): 7 met · 0 not met · 0 can't tell.**
- It re-ran the four named test files (46 passed) and a wider `-k` selection (797 passed).
- It ran the state hook and the summary on this repo's v10 index. Both print the
  `rebuild required …` line.

It raised two minor notes, and neither needs a change:
- The field gains two keys. That is intended and documented in `TOOLS.md`.
- A schema mismatch still returns first. That is out of the ticket's scope, which is the contract era.

`Ph3/4 proven by`: G1, R1–R3, AC1–AC4 — 8/8.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at c95ff050 — the diff `fix/346-signal-reaches-the-model..c95ff050`. Working doc:
`docs/tasks/347_older-contract-index-never-says-rebuild.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `c95ff050` only bookkeeping changes, which is exempt. That covers this doc,
`docs/BACKLOG.md` (the row closed) and `docs/TOKEN_LEDGER.md`.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

No durable lesson. The defect was one unread field, and the fix is pinned by its tests.

### Outward actions

1. Push `fix/347-rebuild-required-summary` — pre-authorised.
2. Open PR #11 with base `fix/346-signal-reaches-the-model` — pre-authorised.

Deferred to the maintainer: the merges, #10 first, then #11.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | review | `challenger`, round 1 | 48,510 fresh |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 48,510 · top cost driver: review/challenger`
