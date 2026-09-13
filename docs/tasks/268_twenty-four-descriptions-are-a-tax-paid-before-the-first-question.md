---
id: 268
slug: twenty-four-descriptions-are-a-tax-paid-before-the-first-question
title: 'Ship the six-tool profile as an opt-in preset and pay down the operational debt that makes the server wrong by default in a worktree, silent on a first run, and expensive on a single walk — none of which needs a measurement first'
phase: 1.5b
milestone: Adoption
status: done
depends_on: [260, 071, 119]
---

## Why this exists

Field round 18's keep-list is six tools: `get_index_status`, `search_symbol`, `read_symbol`, `find_callers`, `find_references`, `impact`. Twenty-four descriptions are a recognition tax the model pays before it asks anything. `CA_TOOLS` already exists (`main.py:160`), so **offering** the profile is nearly free — while **changing the default** without a number repeats the mistake this project has spent five rounds refusing. This ticket offers; [260](260_the-fit-number-cannot-be-observed-only-benchmarked.md) produces the number that may later change the default.

Four operational defects ride along, each cheap and each observed:

- **Worktree.** Parallel agents sit on worktrees; the server usually `cd`s to main. `index_root` tells the truth (071) and `CA_DB_PATH` is a runbook workaround — nobody reads a runbook at dispatch. Returning main's symbols with `reason: ok` to a worktree caller has been seen in a field probe.
- **First run is silent about roots.** `reachable_from` / `find_orphans` refuse without `CA_ENTRY_POINTS` — correct, and unhelpful. [119](119_reachability-signal-provenance.md) proved a stale glob put 560 files in the wrong bucket, so *nominating* candidates is not *guessing*.
- **One walk fills the context.** `reachable_from` at `standard` is ~160 KB (`impact_max_nodes` 500). Called once, never again.
- **Install friction.** Cloning the code-atlas monorepo and filling absolute paths is why a project does not switch the server on.

## Scope / Deliverables

- **Documented six-tool `CA_TOOLS` preset**, opt-in. **Default surface unchanged.**
- **Worktree-correct DB by default:** cwd inside a git worktree ⇒ the DB resolves under that worktree, or the call refuses with a reason naming `index_root` ≠ cwd. Never main's rows under `reason: ok`.
- **Nominate roots, never fill them:** first-run `get_index_status` proposes `CA_ENTRY_POINTS` / `CA_STUB_ROOTS` candidate globs with `files_matched`, for a human or agent to confirm. No auto-application.
- **`minimal` default on large walks** (`reachable_from`, `find_orphans`, verbose `architecture_overview`); `standard` on request.
- **One-line install** (`uvx` / `pipx`), enabling each adapter whose runtime is present.

## Constraints

- Do not change the default tool set in this ticket — that decision waits on 260's counter and [200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md)'s probe.
- Nomination is not inference: candidates are listed, never applied, and a stale glob must stay visible as stale (119).
- No editor settings written (036/099).

## Acceptance criteria

- The preset is documented and tested; a test pins the default surface is still 24 (`tests/test_documented_tool_count.py` unchanged).
- A worktree fixture: the DB resolves under the worktree, or the payload refuses naming `index_root`; a test pins that main's rows can never return with `reason: ok` from a worktree cwd.
- First-run status lists candidate globs with `files_matched` and applies none.
- `reachable_from` default payload size drops measurably on a pinned sample, with `standard` still reachable by argument.
- The one-line install is exercised in CI or in the Docker test path.

## References
[260](260_the-fit-number-cannot-be-observed-only-benchmarked.md), [119](119_reachability-signal-provenance.md), `code_atlas/main.py:160`, `docs/runbooks/parallel-agents.md`, `docs/runbooks/onboarding-a-repo.md` §4, field retro round 18 keep-list.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 268 — six-tool preset and ops debt (working doc)

- **Ticket:** 268
- **Type:** enhancement
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 touched files under UI paths
- **TIER:** full
- **BASELINE:** green

---

## Phase 0 — Refine

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**refine skipped:** ticket locks opt-in preset, worktree refuse, nominate-not-apply, minimal large walks, one-line install.
**INPUT KIND:** ticket.

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=5 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | 24 descriptions are a tax | opt-in six-tool preset | D2 | AC1 | ✅ |
| C1 | Constraints | do not change default tool set | FIELD18 opt-in only | D2 | AC1 | ✅ |
| C2 | Constraints | nomination not inference | candidates only | D4 | AC3 | ✅ |
| C3 | Constraints | no editor settings | — | — | — | ✅ |
| R1 | Scope | documented CA_TOOLS preset | FIELD18_TOOLS | D2 | AC1 | ✅ |
| R2 | Scope | worktree-correct DB | outside DB refuse | D3 | AC2 | ✅ |
| R3 | Scope | nominate roots | status candidates | D4 | AC3 | ✅ |
| R4 | Scope | minimal large walks | three tools | D5 | AC4 | ✅ |
| R5 | Scope | one-line install | Docker RUN help | D6 | AC5 | ✅ |
| AC1 | AC | preset + default 24 | proving | D2 | proving | ✅ |
| AC2 | AC | worktree fixture | proving | D3 | proving | ✅ |
| AC3 | AC | candidates no apply | proving | D4 | proving | ✅ |
| AC4 | AC | minimal default | proving | D5 | proving | ✅ |
| AC5 | AC | install in Docker | Dockerfile | D6 | proving | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

---

## Phase 1 — Analysis

- Root cause: recognition tax + worktree routing + silent first-run roots + fat walks + install friction.
- TRACK: backend — 0/0 UI · SCOPE: M · TIER: full

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R1.1 ✅ · R2 ✅ · R7.6 ✅`

### BASELINE

```
Ran at 307bd284aef1a9c859a76396c7ed404c362a3a92
$ .venv/bin/python -m pytest tests/test_documented_tool_count.py -q --tb=no
6 passed
```

`BASELINE: green`

---

## Phase 2 — Design

- Approach: §19 first; FIELD18_TOOLS; worktree_guard via schema_guard; nominate_roots on status; minimal defaults; Docker help check.
- Rejected: change default tool set (waits on 260); auto-apply globs (119).

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_six_tool_preset_and_ops.py::test_field18_preset_is_six_and_default_is_still_full -q`

| # | Change | File |
|---|--------|------|
| D1 | section-19 | PLAN.md |
| D2 | FIELD18_TOOLS | main.py |
| D3 | worktree refuse | worktree_guard.py, schema_guard.py |
| D4 | nominate | nominate_roots.py, get_index_status.py |
| D5 | minimal defaults | reachable_from, find_orphans, architecture_overview |
| D6 | install + docs | Dockerfile, TOOLS, README |

---

## Phase 3 — Execute

**Branch:** feat/268-six-tool-preset-and-ops-debt
**Implemented:** D1–D6.

**Verification sweep**

```
Ran at b90f1f6d874a148db073c279e1a41d6b4c7fe345
$ .venv/bin/python -m pytest tests/test_six_tool_preset_and_ops.py tests/test_architecture_overview.py -q --tb=no
16 passed in 1.33s
```

---

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived.
**CHALLENGER: ON** — round-1 NOT CLEAN (AC4 size); round-2 CLEAN.

---

## Phase 5 — Finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`

Outward: push + PR authorised. Deferred: merge. DISCLOSURE: gate.sh / local CI / remote CI skipped per operator waiver.
