---
id: 383
slug: re-run-a-signed-claim
title: 'A signed claim says a reviewer can re-run it, but nothing re-runs one'
phase: 2
milestone: Trust
status: done
depends_on: [382]
---

**Reopened 2026-10-11 by the maintainer:** the anchor project runs this as soon as it ships; that consumer is the evidence the 2026-10-10 deferral waited for.

## Why this exists

`sign: true` on `impact`, `impact_modules`, `find_callers`, `find_references` and
`get_index_status` adds a one-line `claim` (`docs/design/impact-and-claims.md` §"Signing a claim"):

```
code-atlas/1 tool=impact subject="app/Http/A.php,app/B.php,+2" question=blast-radius answer=25 tier=RESOLVED seeds=4 seeds_dropped=0 ... rev=a1b2c3d ref=main index=current ...
```

The design's own test of a claim is that it can be re-run; "a claim that cannot be re-run is
decoration". Today re-running one means a human reading the line, rebuilding the tool call by hand
and comparing numbers by eye.

Claims are pasted into more than PR bodies: a consuming repo's own documentation — design notes,
knowledge pages, runbooks — cites code the same way, and goes stale silently when the code moves.
A re-run that answers **holds / changed / unverifiable** turns every pasted claim into a check the
consuming repo can run in its own lint. code-atlas verifies the line; it never stores or reads the
page around it beyond finding claim lines.

The subject is truncated in the line (`+2`), so a re-run needs the full subject, which the line
does not carry today.

## Scope

1. A claim line carries enough to rebuild its call: either the full subject, or a short digest of
   it plus the rule that a digest-only claim is `unverifiable` without the original subject.
   Decide at design; the line stays one line.
2. `code-atlas query --verify-claim '<line>'` (on 382's CLI) re-runs the call at the current index
   and returns `{status: holds | changed | unverifiable, then: {...}, now: {...}, rev_then, rev_now}`.
   `changed` names each key that moved (`answer`, `tier`, `seeds_dropped`, …).
3. `--verify-claims <file>` scans a text file for claim lines and verifies each.

## Assumptions to prove at design

- Whether verification belongs on the CLI only or also as an MCP tool. The tool count is pinned at
  24 by tests, so a new tool needs its own justification; the default is CLI-only.
- A claim signed by an older `code-atlas/N` format version either verifies or answers
  `unverifiable` with the version named — never a false `holds`.

## Acceptance criteria

- **AC1:** a claim signed at rev A re-verified at rev A answers `holds` for each of the five tools.
- **AC2:** a fixture change that adds a caller makes the `find_callers` claim answer `changed` with
  `answer` named as the moved key.
- **AC3:** a claim whose subject no longer resolves answers `changed` with the tool's `reason`,
  not `holds` and not a crash.
- **AC4:** `--verify-claims` on a markdown file with three claims and prose around them verifies
  exactly the three.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 383 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1 and merges. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun 383 - 384 - 385 with skipped reviewer` —
  `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/383-re-run-a-signed-claim` off `main` (`f1112a6c`). Contract `.mango/run-contract-383.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 15 unresolved surfaced | 1 want-decision asked | 14 how-decision resolved+cited | 1 ASSUMED | skip: no`

**Premise.** The five signing tools, `docs/design/impact-and-claims.md` §"Signing a claim", 382's `code_atlas/query.py`
and the claim formatter `code_atlas/tools/claim.py` resolve. Recall: the live type-2 handles name source-literal
reading, page widening and probes — none is a class this change touches.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 48,457 tokens) added H12–H15.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | full subject or digest | how | the full call — Scope 1's digest-only line is `unverifiable` by its own rule, and "a claim that cannot be re-run is decoration" (design doc) |
| H2 | how the call rides the line | how | one last key, `call=`: compact sorted JSON of every non-default argument (`claim.call_args`), `sign` dropped; the line's grammar quotes it (`claim.py` docstring), R4.2 sorted keys |
| H3 | the format version | how | `code-atlas/1` → `code-atlas/2`: a new key on a published line moves its own version (R3.5) |
| H4 | an older line | how | any other version is `unverifiable`, `reason: claim_format`, `format` named — ticket assumption 2, R5.6 |
| H5 | CLI or MCP tool | how | CLI only — the ticket's default; the count stays 24 |
| H6 | what is compared | how | every key but the question (`tool`, `subject`, `question`, `call`) and provenance (`rev`, `ref`, `index`, `dirty_indexed`, `server`, `build`) — Scope 2 names `answer`, `tier`, `seeds_dropped` |
| H7 | a lost subject | how | the tool signs nothing (`impact`), so `now` is its `reason` and the verdict `changed` — AC3 |
| H8 | a refusal (`error` key) | how | `unverifiable` with that error — R5.6 |
| H9 | exit status | how | `3` when any claim did not hold — Why ¶3, "a check the consuming repo can run in its own lint" |
| H10 | the scanner | how | the inverse of `render`, anywhere in a line, `tool=` required; verdicts carry `source` — Scope 3, AC4 |
| H11 | counters | how | none bumped — 382's rule (`build_server(count=False)`) |
| H12 | which index answers | how | the project's, as `code-atlas query` finds it (382 H9); documented |
| H13 | a behind index | how | `holds` stays a statement about the indexed tree; the verdict adds `index_now` |
| H14 | what `holds` covers | how | the asserted counts, not the set; documented — the line asserts counts (`claim._answer`) |
| H15 | untrusted lines | how | the tool must be served and not a writer; a call carrying `reset_fit_counts` is `call_rejected` (`claim.NOT_REPLAYED`) |
| W1 | the signed line grows 16 tokens (+59 → +75; cap 60 → 80) | want | **ASSUMED (awaiting ratification):** accept it — the cap exists so growth is deliberate, and this is the field that makes the line re-runnable |

Not taken from the checker: an ordinal per claim on a shared line, and zero claims failing a lint — a page may hold none.

## Phase 1 — analysis

`SECTIONS: 4 found (Why this exists · Scope · Assumptions to prove at design · Acceptance criteria) | 4 decomposed | ROWS: C=1 R=3 G=1 AC=4`
`CLARIFICATION: 15 raised | 15 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

CI on `main`'s tip `f1112a6c` (PR #66's merge commit, this branch's base): `CI` — success. Ran at f1112a6c.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "a check the consuming repo can run in its own lint" | re-run a pasted claim from a shell | ✅ |
| C1 | Why | "it never stores or reads the page around it beyond finding claim lines" | the scanner reads, stores nothing | ✅ |
| R1 | Scope 1 | the line carries enough to rebuild its call | H1–H3 | ✅ |
| R2 | Scope 2 | `--verify-claim` → status, then, now, rev_then, rev_now; `changed` names keys | H6–H9 | ✅ |
| R3 | Scope 3 | `--verify-claims <file>` | H10 | ✅ |
| AC1 | AC | holds at rev A for each of the five tools | | ✅ |
| AC2 | AC | an added caller → `changed`, `answer` named | | ✅ |
| AC3 | AC | a lost subject → `changed` with the tool's `reason` | | ✅ |
| AC4 | AC | three claims in Markdown, exactly three verified | | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — status per tool, parametrised over the five signers | `then == now`, `answer` present |
| AC2 | yes — `answer` in `changed`, `1 → 2` | a second committed file indexed at the new HEAD |
| AC3 | yes — `reason` in `changed`, `now.reason == no_such_symbol` | both branches: `find_callers` signs, `impact` signs nothing |
| AC4 | yes — tools and `source` lines equal the three | fenced, inline-code and bare claims; prose naming `code-atlas/2` and `code-atlas/1` |

**Assumptions answered.** CLI only (H5). An older line is never a `holds` (H4,
`test_an_older_format_claim_is_unverifiable_and_names_its_version`).

### Rule sections

`RULE SECTIONS: 6 applicable — 6 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ claim.py and query.py name no language · §R3.5 (change-type) ✅ the line's new key bumps CLAIM_SCHEMA to code-atlas/2, no other constant · §R4.2 (change-type) ✅ call JSON is sort_keys, the line order fixed · §R5.6 (change-type) ✅ an older format, an unreadable call and a refusal answer unverifiable, never holds · §R6.5 (change-type) ✅ the new tests fail on main (14/14) · §R7.5 (change-type) ✅ comments ≤ 3 lines`

## Phase 2 — design

### Approach

1. `claim.py`: `CLAIM_SCHEMA = "code-atlas/2"`; `call_args(tool, locals())` keeps every non-default argument but
   `NOT_REPLAYED`; `sign(..., call=)` appends `call=<json>` last; `find_claims`, `asserted`, `moved_keys` read it back.
2. The five signing tools capture `call` on entry and pass it to `claim.sign`.
3. `query.py`: `--verify-claim LINE` and `--verify-claims FILE|-`; one client re-asks each call with `sign: true` and prints
   one verdict line; exit `3` when any did not hold.
4. Docs: the design record's signing section, README, CHANGELOG.

### Rejected alternatives

- **A digest of the subject** — a digest-only claim is unverifiable without the subject, which the page never holds.
- **Each argument as its own `arg.x=` key** — loses types (`"2"` vs `2`, lists) and needs the schema to rebuild them.
- **An MCP tool** — the count is pinned at 24 and no agent flow needs it.

### Assumptions

| Assumption | verified / novel-untested | Evidence |
|---|---|---|
| `locals()` on entry holds exactly the tool's parameters | verified | `test_the_line_carries_the_call_that_rebuilds_it` |
| a replayed JSON call validates as the original | verified | AC1 through FastMCP's in-memory client |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | the call key, the reader | `code_atlas/tools/claim.py` | every signed line; tests that parse it | R1 | 1/1 |
| 2 | capture `call` | the five signing tools | their signed payloads | R1 | 5/5 |
| 3 | verify modes | `code_atlas/query.py` | 382's batch path (shared `_call`) | R2, R3 | 1/1 |
| 4 | proving tests; the token cap 60 → 80; the doc example | `tests/test_verify_claim.py`, `tests/test_claim_signing.py` | — | AC1–AC4, W1 | 2/2 |
| 5 | docs | `docs/design/impact-and-claims.md`, `README.md`, `CHANGELOG.md` | doc budgets | G1 | 3/3 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | bookkeeping tests | — | 3/3 |

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — sign and re-run through the MCP call path | `query.main` both ways, five tools | n/a | ✅ |
| AC2 | integration | a second indexed file at a new HEAD | n/a | ✅ |
| AC3 | integration | the subject's row dropped from the index | n/a | ✅ |
| AC4 | integration | a Markdown page through `--verify-claims` | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_verify_claim.py`.

### Rollback

`git revert`; nothing is stored. A line signed by this version reads `unverifiable` to an older reader, never `holds`.

## Phase 3 — execute

Commits `a7a89485` (code, tests), `8329d851` (docs). **Red first** (R6.5): the new file copied into a worktree of
`main` (`f1112a6c`) fails 14 of 14 — `query` has no verify mode and `claim` no `find_claims`.

```
$ scripts/gate.sh
  PASS pytest -q
21 passed · 0 failed · 0 skipped
GATE GREEN — all 21 checks passed
Ran at ce5e4f73
```

The first gate run on `ce5e4f73` went red on `phpstan` alone — an internal error from a stale `/tmp/phpstan`
cache naming another session's deleted worktree; this branch touches no PHP. Cleared, re-run green above.

**Verification sweep.** File axis: the diff is the change list; `ruff check`, `mypy code_atlas` clean (99 files).
Behaviour axis: Approach 1–4 implemented as approved; H13 and H15 landed with the exposure-checker's items.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. Reviewed at e953278e — files: `code_atlas/query.py`,
`code_atlas/tools/claim.py`, the five signing tools, `tests/test_verify_claim.py`, `tests/test_claim_signing.py`,
`docs/design/impact-and-claims.md`, `README.md`, `CHANGELOG.md`; working doc: this file.

- **`challenger` round 1** (ticket-blind, 62,570 tokens): 8 met · 0 not met · 0 can't tell. Findings: a bare value in
  backticks truncated the parse (fails safe, `call_unreadable`); a line asserting nothing could read `holds`; `holds`
  covers counts, not sets (documented); duplicate keys, last wins (hand edits only, not taken). Fixed in `e953278e`:
  a backtick is a quote trigger, and an empty `then` is `unverifiable` (`nothing_asserted`), both tested.

Verdict: clean (challenger only — REVIEWER: OFF). Matrix `Ph3/4 proven by`: R1–R3, AC1–AC4 →
`tests/test_verify_claim.py`; W1 → `tests/test_claim_signing.py::test_the_opt_in_costs_one_line`; G1, C1 → the diff and
the design record.

## Phase 5 — finalise

**Durable lesson.** None new.

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

### Outward actions

Under the handover: push `feat/383-re-run-a-signed-claim`; open the PR against `main`.
Deferred to the maintainer: ratify W1; merge.

### Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | exposure-checker (`challenger`) | 1 | 48,457 |
| 4 review | `challenger` (ticket-blind) | 1 | 62,570 |

`LEDGER TOTAL: 111,027 · top cost driver: challenger`
