---
id: 270
slug: the-brief-is-announced-nowhere-and-loaded-by-nobody
title: 'The five-occasion brief 266 shipped is named in no document a user reads — not README, not the onboarding runbook, not setup''s closing line — and on Claude Code it is loaded by nothing: the hardcoded memory list is `CLAUDE.md` / `CLAUDE.local.md`, and `AGENTS.md` is not in it, so the artifact that fixes recognition repeats 266''s own failure one level down'
phase: 1.5b
milestone: Adoption
status: done
depends_on: [266, 200, 240, 244]
---

## Why this exists

[266](266_the-artifact-that-would-make-an-agent-ask-is-in-our-repo-not-theirs.md) moved the brief out of
`contrib/skill/` — *"a place no agent working in a consumer repo ever reads"* — and into the indexed
tree. The move was right. **Two links in the chain were left unbuilt, and each reproduces the defect
266 was written to remove.**

**1. No channel announces it.** Grep for `write-agent-brief` / `agent brief` across `README.md`,
`docs/**` and `contrib/**`, excluding `docs/tasks/`: **four hits, none of them a place a user looks** —
`PLAN.md:976` (the §19 decision), `TOOLS.md:241` (`CA_PROJECT_FILES`, unrelated), `TOKEN_LEDGER.md:27`
(the spend row) and `contrib/agent-brief.md:5` (the generated artifact naming its own regeneration
command). **Zero hits in `README.md`**, **zero in `docs/runbooks/`**, **zero in
`contrib/claude-code/README.md`**. README's Quick start ends at *"call `get_index_status` →
`build_or_update_index`"* — the exact line where the brief should be offered. `scripts/setup.py`
carries the `--write-agent-brief` flag but its closing `Done.` never mentions it, so the one screen
every installer reads stays silent. The maintainer learned the feature existed by asking, 2026-09-13
— not from any document.

**2. On Claude Code, `AGENTS.md` is loaded by nothing.** The hardcoded project-memory list in the
shipped binary (`claude 2.1.270`) is `["CLAUDE.md","CLAUDE.local.md"]`; `"AGENTS.md"` occurs in that
binary only inside the Codex-import path. This repo never noticed because its own `CLAUDE.md` carries
an `@AGENTS.md` import — a consumer repo has no reason to. **Field instance, 2026-09-13, `anchor-repo`:**
the brief was written correctly, the repo's 15 KB `CLAUDE.md` had no import, and the brief was inert
until a `CLAUDE.local.md` holding `@AGENTS.md` was added by hand. This is [240](240_the-read-time-signal-is-offered-to-codex-and-not-to-claude-code.md)'s
class — an offer shipped for a host that is not the one the field rounds run on.

Both defects are docs-and-offer shaped. Neither needs a measurement first, and neither changes a tool.

## Scope / Deliverables

- **README, after Quick start:** a short subsection — what the brief is (five occasions, not 24
  descriptions), the command, and **the load requirement per host** (Claude Code reads `CLAUDE.md` /
  `CLAUDE.local.md`; Cursor reads `AGENTS.md` directly).
- **`scripts/setup.py` closing line names the flag** when a PROJECT was given and the flag was not —
  the one screen an installer reads.
- **`docs/runbooks/onboarding-a-repo.md`:** the brief becomes a step in the onboard sequence, next to
  the hook offer.
- **Make the brief reachable on Claude Code — offered, never installed.** `write_agent_brief` detects
  a `CLAUDE.md` in the target that lacks an `@AGENTS.md` import and **prints the one line to add**. It
  writes nothing to `CLAUDE.md`.
- **Record the boundary in PLAN §19 before any code.** 266's entry authorises writing `AGENTS.md`
  into the indexed tree. Appending an import line to a repo's **existing, team-committed** `CLAUDE.md`
  is a different act with a different blast radius — the same reason 266 needed its own entry against
  [036](036_edit-index-hook.md)/[099](099_write-time-signal-seam.md). Decide it first; this ticket's
  recommendation is **print, never write**.

## Constraints

- No 25th tool, no new env knob, no editor settings (036/099 unchanged).
- The brief's body stays generated from `which_tool` (R6.7) — the new README text must not become a
  second hand-kept copy of the occasions or the tool list.
- R7.6: the README subsection removes what it supersedes; `tests/test_doc_size_budget.py` stays green.

## Acceptance criteria

- A test asserts `--write-agent-brief` appears in `README.md` **and** in
  `docs/runbooks/onboarding-a-repo.md`, and that the README text names no tool the generator does not
  (R6.7 drift guard extended).
- `scripts/setup.py PROJECT` without the flag prints the offer line; a test pins it.
- `write_agent_brief` against a fixture repo whose `CLAUDE.md` lacks `@AGENTS.md` returns/prints the
  import line and leaves `CLAUDE.md` byte-identical; with the import present it says nothing. Both
  arms tested.
- PLAN §19 carries the `CLAUDE.md`-import boundary decision, committed **before** the code change.
- Docs budget and `tests/test_agent_brief_in_indexed_repo.py` stay green.

## References
`README.md` §Quick start, `scripts/setup.py:121,178`, `scripts/gen_skill.py:269`,
`docs/runbooks/onboarding-a-repo.md`, `contrib/claude-code/README.md`,
[266](266_the-artifact-that-would-make-an-agent-ask-is-in-our-repo-not-theirs.md),
[240](240_the-read-time-signal-is-offered-to-codex-and-not-to-claude-code.md),
[200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md),
[244](244_no-channel-announces-a-capability-change.md), PLAN §19 (266 entry, `PLAN.md:976`).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 270 — brief announced + Claude Code load offer (working doc)

- **Ticket:** 270
- **Type:** enhancement
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 touched files under UI paths
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed · path: docs/tasks/270_the-brief-is-announced-nowhere-and-loaded-by-nobody.md

---

## Phase 0 — Refine

`PREMISE: 11 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**Recalled claims (advisory):** `243-C1` / handle `capability-signal-on-the-first-call-channel` — announce the brief on the channels a user/agent actually reads (README, setup Done, runbook), not only in PLAN/ledger.

**refine skipped:** ticket locks README after Quick start, setup offer line, runbook step, print-never-write for CLAUDE.md import, §19-first.
**INPUT KIND:** ticket.
**Note:** depends_on includes blocked 200; same as 266 — proceed without closing 200 AC5.

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=3 R=5 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | brief announced nowhere; Claude Code loads AGENTS.md via nothing | announce + print import offer | D2–D5 | ACs | ✅ |
| C1 | Constraints | no 25th tool / env / editor settings | 036/099 unchanged | — | — | ✅ |
| C2 | Constraints | brief body from which_tool (R6.7) | README names no tool generator lacks | D4 | AC1 | ✅ |
| C3 | Constraints | R7.6 prune; doc budget green | | D4–D5 | AC5 | ✅ |
| R1 | Scope | README after Quick start | subsection: what/command/per-host load | D4 | AC1 | ✅ |
| R2 | Scope | setup closing names flag | PROJECT without flag → offer line | D3 | AC2 | ✅ |
| R3 | Scope | runbook step next to hook offer | | D5 | AC1 | ✅ |
| R4 | Scope | print import line; never write CLAUDE.md | write_agent_brief detect | D2 | AC3 | ✅ |
| R5 | Scope | PLAN §19 boundary before code | print, never write | D1 | AC4 | ✅ |
| AC1 | AC | --write-agent-brief in README + runbook; R6.7 drift | test | D4–D5 | proving | ✅ |
| AC2 | AC | setup PROJECT without flag prints offer | test | D3 | proving | ✅ |
| AC3 | AC | missing @AGENTS.md → print; CLAUDE.md byte-identical; present → silent | both arms | D2 | proving | ✅ |
| AC4 | AC | §19 committed before code | commit order | D1 | history | ✅ |
| AC5 | AC | docs budget + test_agent_brief_in_indexed_repo green | | D6 | AC5 | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

---

## Phase 1 — Analysis

- Root cause: 266 wrote the brief into AGENTS.md but no user-facing channel announces `--write-agent-brief`, and Claude Code's memory list never loads AGENTS.md unless CLAUDE.md imports it — consumer repos lack this repo's `@AGENTS.md` import.
- TRACK: backend — 0/0 UI · SCOPE: M · TIER: full

`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R6.7 ✅ · R7.6 ✅ · R5.6 ✅`

### BASELINE

```
Ran at cb3a52034ce9f8aae530629a90137ad5af0d2f5f
$ .venv/bin/python -m pytest tests/test_agent_brief_in_indexed_repo.py tests/test_doc_size_budget.py -q --tb=no
13 passed
```

`BASELINE: green`

---

## Phase 2 — Design

- Approach: §19 first (print, never write CLAUDE.md); extend `write_agent_brief` to detect missing `@AGENTS.md` in CLAUDE.md and print the one-line import; setup Done offer when PROJECT given without flag; README subsection + runbook step; tests pin all three ACs.
- Rejected: appending import into CLAUDE.md (team-committed; blast radius vs 266's AGENTS.md write — ticket recommendation + 036/099 posture). Editing contrib/claude-code/README (References only, not Scope).

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
- `capability-signal-on-the-first-call-channel`: traced — announce on README / setup Done / runbook (first-read channels); result: keep D3–D5.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_agent_brief_announce_and_claude_load.py -q`

| # | Change | File |
|---|--------|------|
| D1 | §19 CLAUDE.md-import boundary | docs/PLAN.md |
| D2 | detect + print import offer; never write CLAUDE.md | scripts/gen_skill.py |
| D3 | setup Done offer line | scripts/setup.py |
| D4 | README subsection after Quick start | README.md |
| D5 | runbook brief step | docs/runbooks/onboarding-a-repo.md |
| D6 | proving + announce/R6.7 tests | tests/test_agent_brief_announce_and_claude_load.py (+ extend existing as needed) |
| D7 | backlog/ledger/task status | docs/BACKLOG.md, docs/TOKEN_LEDGER.md, task frontmatter |

---


---

## Phase 3 — Execute

**Branch:** feat/270-the-brief-is-announced-nowhere-and-loaded-by-nobody
**Implemented:** D1–D7. D1 committed first (`9cb12ea`), then code/docs/tests.

**Verification sweep**

```
Ran at 20a43bea5742844e1e9a4555a1e5d0051c2d2056
$ .venv/bin/python -m pytest tests/test_agent_brief_announce_and_claude_load.py tests/test_agent_brief_in_indexed_repo.py tests/test_doc_size_budget.py -q --tb=no
19 passed in 0.57s
```

---

## Phase 4 — Review

**REVIEWER: OFF (--no-reviewer)** — waived.
**CHALLENGER: ON** — round-1 CLEAN (11/11 reconstructed requirements MET).

---

## Phase 5 — Finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`

Outward: push + PR authorised. Deferred: merge, tracker transitions.

---

## Session status

- **Last updated:** 2026-09-13
- **Current phase:** finalise
- **Next action:** push + open PR (authorised)
- **Blocked on:** none
