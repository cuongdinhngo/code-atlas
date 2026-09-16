---
id: 284
slug: the-stale-process-warning-names-a-divergence-and-never-an-effect
title: '`server_stale_process` reports that the package on disk moved under the process and names a restart, but never whether any tool contract moved with it — so three consecutive field rounds read it, could not decide, ignored it, and one of them reported a `find_references` payload the shipped code cannot produce; the warning that cannot be acted on is the warning that costs a round of evidence'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [267, 170, 164]
---

## Why this exists (field retros — the anchor repo, rounds 24, 25 and 26, 2026-09-15)

267 made the stale-process warning actionable in the narrow sense: it names an action
(`restart_mcp_server_process`) and what differs (`code_atlas_package_bytes_on_disk`,
`build_info.py:27`). Three rounds later the field verdict is that neither answers the question a
reader actually has — *does this change any answer I am about to act on?* All three rounds recorded
`server_stale_process: true` on every payload, all three deliberately ignored it, and the third wrote:

> *"'I ignored the staleness warning and got away with it' is a bad habit for a tool to be training."*

The cost is not the noise. `server_build` is a **content hash** of the loaded tree frozen at import
(`_content_build_id`, `build_info.py:59`; `_capture_loaded_build_id`, `:70`), so on a diverged process
it resolves to no commit in any repo — while `server_repo_head` (`:130`) names the *checkout's* HEAD,
which moves under a long-lived process. A retro quoting both cannot reconstruct which code answered.

That is not hypothetical. Round 24 reported `find_references` on a PHP class answering
`relationship_not_modelled` with `unlinked_edge_kinds: ["IMPORTS"]`; the shipped code routes exactly
that branch into 252's member union and answers `via_members`
(`find_references.py:498-506`). Either the process predated 252 or the subject had no indexed
`CONTAINS` children — and nothing in the payload lets a reader tell those apart. Three rounds of field
evidence therefore have no resolvable provenance, which is the one thing the retro protocol buys.

The docstring already states the intent the payload does not reach: *"a retro can never quote a commit
that did not answer"* (`build_info.py:1-9`). A content hash that names nothing satisfies the letter and
loses the purpose.

## Scope / Deliverables

- **Say whether the drift is answer-affecting.** A stale payload carries a verdict a reader can act
  on — e.g. `server_stale_impact` distinguishing "no tool contract changed" from "a tool's payload
  shape changed" — derived from stored evidence (the loaded vs on-disk contract/tool surface), never
  from a guess or a timestamp.
- **Make the loaded build locatable, or say plainly that it is not.** When `server_build` is a content
  hash rather than a commit, the payload must mark it as such, so a reader does not spend a round
  trying to `git log` it.
- **`server_repo_head` must read as what it is** — the checkout's HEAD, not the running server's.
  Rename or document it at its definition site; three rounds recorded it as describing the server.

## Constraints

- R5.6: the impact verdict rides stored evidence, never inference from version strings.
- R4.2: identical artifact → identical fields; no timestamps, no mtimes in any published value
  (`_probe_state` stays out of every id, `build_info.py:80-82`).
- 061: a process that matches its disk stays byte-identical — this ticket adds nothing to the
  `stale_process: false` payload.
- Cost: no re-hash per payload; 164 measured that walk at 6.35 ms and 170 replaced it with the
  `sys.modules` stat probe. Whatever this reads must sit behind the same "only when the disk moved" gate.

## Acceptance criteria

- A diverged process whose tool contract is unchanged carries an impact verdict saying so.
- A diverged process whose contract *did* change carries the opposite verdict, and the two are
  distinguishable without reading source.
- A `server_build` that is a content hash is marked as not-a-commit.
- A matching process's payload is byte-identical to today's.
- No published field derives from a timestamp or an mtime.

## References
`code_atlas/build_info.py:1-9,27,59,70,115-131,158-177`,
`code_atlas/tools/find_references.py:498-506`,
[267](267_the-warning-an-autonomous-agent-cannot-act-on.md),
[170](170_server-identity-is-cached-so-a-later-build-swap-is-unreportable.md),
[252](252_a-class-reference-question-costs-n-plus-one-calls.md).
Origin: field retros rounds 24 §6, 25 §6 and 26 §1, 2026-09-15 — the same finding three rounds running.

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 284 — stale-process impact + build kind (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** M · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 3 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

HOW: (1) impact field = `server_stale_impact` with values `tool_contract_unchanged` / `tool_contract_changed` — ticket Scope bullet 1 names the shape; R5.6 requires distinguishable states. (2) mark content-hash builds with `server_build_kind: content_hash` only on the stale path — AC3 + 061 (matching stays byte-identical). (3) keep `server_repo_head` name; document at definition/emit sites that it is checkout HEAD — ticket Scope bullet 3 allows rename *or* document; document is lower blast (CONVENTION + emit docstring). Citations: ticket Scope/AC; R5.6; 061.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=3 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | warning must say if answers change | impact verdict from stored surface hash | D1 | AC1–2 | ✅ |
| C1 | Constraints | R5.6 stored evidence | tool-surface hash frozen at import vs disk | D1 | AC1–2 | ✅ |
| C2 | Constraints | R4.2 no timestamps | probe mtimes stay out of published fields | D1 | AC5 | ✅ |
| C3 | Constraints | 061 matching byte-identical | new fields only when stale | D1 | AC4 | ✅ |
| C4 | Constraints | cost behind disk-moved gate | surface re-hash only in `_compute_identity` diverge branch | D1 | — | ✅ |
| R1 | Scope | impact verdict | `server_stale_impact` | D1 | AC1–2 | ✅ |
| R2 | Scope | mark content-hash build | `server_build_kind` | D1 | AC3 | ✅ |
| R3 | Scope | repo_head = checkout | document at emit site + CONVENTION | D2 | — | ✅ |
| AC1 | AC | unchanged contract → impact says so | proving | D3 | proving | ✅ |
| AC2 | AC | changed contract → opposite | proving | D3 | proving | ✅ |
| AC3 | AC | content hash marked not-a-commit | proving | D3 | proving | ✅ |
| AC4 | AC | matching byte-identical | proving | D3 | proving | ✅ |
| AC5 | AC | no timestamp/mtime fields | proving | D3 | proving | ✅ |

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: 267 named action + axis but not whether any tool answer changed; `server_build` as content hash looks like a commit; `server_repo_head` was read as the answering process.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R4.2 ✅ · R5.6 ✅ · R5.5 ✅ · R7.6 ✅`

Ran at eea1bd43a83e515b50e69dc42615680218ca1c92

```
$ .venv/bin/python -m pytest tests/test_server_build.py tests/test_actionable_stale_warnings.py tests/test_server_identity_is_live.py -q --tb=no
................................                                         [100%]
32 passed in 2.94s
```

`BASELINE: green`

## Phase 2 — Design

- Approach: freeze `_LOADED_TOOL_SURFACE_ID` over `contract.py` + `build_info.py` + `tools/**/*.py`; on diverge compare to disk → `server_stale_impact`; emit `server_build_kind: content_hash`; document `server_repo_head` as checkout HEAD; matching path untouched.
- Rejected: rename `server_repo_head` → `server_checkout_head` (larger blast; ticket allows document). Rejected: always-on impact field (violates 061). Rejected: re-hash full tree for impact (cost; ticket wants tool surface).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_stale_process_impact.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | impact + build_kind on stale path | code_atlas/build_info.py | every stale payload | 1/1 |
| D2 | CONVENTION + payload.md wording | docs/CONVENTION.md, docs/design/payload.md | docs | 1/1 |
| D3 | proving tests | tests/test_stale_process_impact.py (+ pin in test_server_build.py) | — | 1/1 |

## Phase 3 — Execute

**Branch:** feat/284-stale-process-impact-and-build-kind
**Axis 1:** build_info · docs · proving tests.
**Axis 2:** implemented-as-approved.

**Verification sweep**

Ran at eea1bd43a83e515b50e69dc42615680218ca1c92

```
$ .venv/bin/python -m pytest tests/test_stale_process_impact.py -q --tb=no
.....                                                                    [100%]
5 passed in 0.05s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)

CHALLENGER: on — CLEAN (10 met / 0 not met / 0 can't tell). agent 72d02034-d55e-4cbc-b260-499bcfd175f2

`SCOPE ≡ approved list: yes`
`DIFF ⊆ approved list: yes`
`PROVING TEST: tests/test_stale_process_impact.py — 5 passed`
`DESIGN-CONFORMANCE: self-check passed`
`REVIEW: CLEAN`

## Phase 5 — Finalise

Outward actions (approved by handover): push feature branch; open PR. Never merge.
Gate: GATE GREEN (.mango/gate-284.log)
PR: https://github.com/cuongdinhngo/code-atlas/pull/378

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger on; main-loop unmeasured |

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`
