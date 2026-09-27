---
id: 340
slug: a-commit-author-is-never-checked-so-the-employer-logon-came-back
title: "A commit's author and committer are never checked, so the employer logon 325 rewrote out of history came back the next day"
phase: 1
milestone: Agent-trust
status: done
depends_on: [325]
---

## Why this exists (public-launch audit, 2026-09-27)

325 rewrote the Windows-domain-logon author name out of history and deleted `.mailmap`. One day
later **six commits on `main`** (2026-09-24, merges and a docs sync for 318/320-323) carry that
logon again as **both author and committer name** — made from a host whose `user.name` is still
the domain logon. Nothing caught it: `test_no_client_identifiers.py` sweeps **tracked files**, and
the R7.3 CI step (`ci.yml`, "no co-author or AI-attribution trailer") reads commit **messages**.
Commit metadata is read by nothing, and GitHub serves it raw.

325 said it itself: *a sweep cannot certify itself*. The tree now has a certificate; the commit
headers do not.

## Goal

A commit whose author or committer identity carries an employer or client marker cannot reach
`main` unnoticed.

## Scope / Deliverables

1. A check over the author name, author email, committer name and committer email of every commit
   in the change range, reusing the structural arms 325 already defines (Windows domain logon,
   corporate second-level domain, email outside the allowlist) and the vocabulary digests — one
   definition site for each pattern (R6.7), not a second copy.
2. Wired where R7.3's range check already runs, and mirrored in `scripts/gate.sh`
   (`tests/test_ci_and_gate_agree.py` keeps them in step).

## Constraints

- **Must not go red on today's `main`.** The six offending commits are removed by the history
  rewrite that precedes going public, not by this ticket; the check binds the change range, as
  R7.3 does, not all reachable history.
- **R6.5** — an empty range must not pass vacuously (R7.3's own precedent).
- Neither this ticket nor the check's source spells out the logon it detects (325 finding 5).

## Acceptance criteria

- **AC1** A commit in range whose author name has the Windows-domain-logon shape → the check fails
  and names the commit; red on today's code (nothing checks it).
- **AC2** Same for a committer email on a corporate second-level domain.
- **AC3** A range of clean commits (maintainer's public identity, GitHub's merge identity) passes.
- **AC4** An empty range fails loudly rather than passing.

## References
`tests/test_no_client_identifiers.py` (`WINDOWS_LOGON`, `CORPORATE_TLD`, `ALLOWED_EMAIL_DOMAINS`);
`.github/workflows/ci.yml` R7.3 step; `scripts/gate.sh`; `tests/test_ci_and_gate_agree.py`;
ticket 325 ("What this does not fix").

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 340 — a commit's identity is checked like the tree is (working doc)

- **Ticket:** 340 · local · **SCOPE:** S · **TIER:** full · **TRACK:** backend
- **REVIEWER:** OFF (`--no-reviewer`) · **CHALLENGER:** ON
- **Current phase:** finalise
- **Session status:** done — autorun, PR open

## Phase 0 — Refine

`PREMISE: 7 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions — the ticket was written in the same session as the
maintainer's direction (run 340/341/342 before going public), and its Scope names the site (R7.3's).

Recalled (advisory): `prove-the-guard-fails` (R6.5 — the check must be seen red on a planted
offending commit); `sweep-scope-cannot-attest-the-gate` (the pre-PR claim must come from the gate,
not from this ticket's own test file).

## Requirements matrix

`SECTIONS: 7 found (Why · Goal · Scope · Constraints · Acceptance · References · title) | 7 decomposed | ROWS: C=3 R=2 G=1 AC=4`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Goal | an employer/client marker in a commit identity cannot reach `main` unnoticed | D1–D3 | ✅ |
| R1 | Scope 1 | check author+committer name+email of each commit in range; 325's arms, one definition site | D1 | ✅ |
| R2 | Scope 2 | spent in ci.yml's R7.3 job and gate.sh; `test_ci_and_gate_agree` row | D2 | ✅ |
| C1 | Constraints | range-bound, green on today's `main` | D2 | ✅ |
| C2 | R6.5 | empty range fails loudly | D1 | ✅ |
| C3 | 325 finding 5 | no literal of what it detects in source or ticket | D1, D3 | ✅ |
| AC1–AC4 | AC | proving | D3 | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: the patterns exist (`tests/test_no_client_identifiers.py`) but are bound to
  `git ls-files` content; R7.3's range check reads `%B` only. No reader of `%an %ae %cn %ce`.
- Blast radius: the de-identification test module (patterns move out, imports come in); ci.yml
  `guardrails` job; `scripts/gate.sh`; `tests/test_ci_and_gate_agree.py` SHARED_CHECKS.
- The `guardrails` job has no `setup-python`; the runner's `python3` runs a stdlib-only script, so
  the shared module must import nothing outside the stdlib.

`TRACK: backend — 0/N UI`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.8 ✅ (patterns defined once, imported by test and check) · R6.5 ✅ (planted red commit; empty range fails; ≥80-digest guard kept) · R2.4 ✅ (no literal of the detected strings) · R7.5 ✅ (comments ≤ 3 lines)`

`BASELINE: green`

## Phase 2 — Design

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `prove-the-guard-fails` → traced: AC1/AC2 tests run the check over a temp repo whose commit
  carries a planted marker and assert a non-zero exit naming the commit.
- `sweep-scope-cannot-attest-the-gate` → traced: `scripts/gate.sh` is the pre-PR claim, not the
  proving file.

| # | Change | File | k/N |
|---|--------|------|-----|
| D1 | stdlib module owning the identity patterns + `commit_identity_offences(range)` + CLI (empty range → exit 2) | scripts/identity_markers.py | 1/1 |
| D1b | de-identification test imports the patterns from D1 instead of defining them | tests/test_no_client_identifiers.py | 1/1 |
| D2 | spend in R7.3's steps and the agreement table | .github/workflows/ci.yml · scripts/gate.sh · tests/test_ci_and_gate_agree.py | 1/1 |
| D3 | proving tests + bookkeeping | tests/test_commit_identity.py · docs/TOKEN_LEDGER.md · docs/tasks/340_… | 1/1 |

| AC | risk | proof | provenance | match |
|----|------|-------|------------|-------|
| AC1 | author name logon | pytest over a temp git repo | authored | ✅ |
| AC2 | committer corp email | pytest over a temp git repo | authored | ✅ |
| AC3 | clean range passes | pytest over a temp git repo | authored | ✅ |
| AC4 | empty range | pytest, exit code | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_commit_identity.py tests/test_no_client_identifiers.py tests/test_ci_and_gate_agree.py -q`

Rejected alternatives: a pytest arm over all reachable history (red on today's `main` until the
rewrite — C1); a second copy of the regexes in the shell step (R1.8); a pre-commit hook (local-only,
not a gate CI can enforce).

`SCOPE: S`

## Phase 3 — Execute

**Branch:** fix/340-commit-identity-guard

Ran at 32fd3cd

```
$ .venv/bin/python -m pytest tests/test_commit_identity.py tests/test_no_client_identifiers.py tests/test_ci_and_gate_agree.py -q
40 passed
```

Red arms: with the logon arm removed from `STRUCTURAL`, AC1 and the CLI exit test fail (2 failed,
4 passed); without `scripts/identity_markers.py` the proving file does not collect. On real history,
`python3 scripts/identity_markers.py 2c184a4~40..2c184a4` exits 1 naming exactly the six commits of
2026-09-24, author and committer each — the check finds the incident it was written for.

Design conformance: D1–D3 implemented-as-approved; D1b also routes the tree sweep's email arm through
the shared `email_allowed` (R1.8), and R2.4's gate sentence was trimmed to hold the 5,880 ceiling.

## Phase 4 — Review

REVIEWER: OFF (`--no-reviewer`) · CHALLENGER: ON — round 1 on `b812b00`: **FINDINGS 7/1/0**.

| # | Finding | Disposition |
|---|---|---|
| 1 | the planted merge-bot address kept the local part, the `@` and the first domain label inside one literal, which the tree sweep's email arm reads as an out-of-allowlist address — `test_no_email_outside_the_allowed_domains` red | fixed in `32fd3cd` (split at the `@`); the named proving command re-run green, 40 passed |

Verdict: `clean after fix (challenger only — REVIEWER: OFF)`; no round 2 was dispatched for a
one-literal fix whose failing test is in the proving command.

## Phase 5 — Finalise (learning loop)

Lesson: `docs/LESSONS.md` § 340 — first sighting of `a-tracked-file-sweep-is-blind-until-commit`.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: 64159 · top cost driver: review/challenger ×1 (1 dispatch; main-loop unmeasured)`
