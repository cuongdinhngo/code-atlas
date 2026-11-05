---
id: 435
slug: index-status-token-claim
title: "README's \"~100-token get_index_status\" — make the number true and hold it with a test"
phase: 2
milestone: Docs
status: done
depends_on: []
---

## Why this exists

`README.md:190` calls `get_index_status` "the cheap (~100-token) entry point", in a README that says
its numbers are measured, not asserted. Measured 2026-11-04 on this repo's own index (784 files) with
`code-atlas query get_index_status`:

| `detail_level` | chars | ~tokens (chars/4) |
|---|---:|---:|
| `standard` (default) | 3,236 | ~809 |
| `minimal` | 830 | ~207 |
| `verbose` | 5,021 | ~1,255 |

The default is about 8× the claim, and even `minimal` is about 2×. (The brief measured 2,042 / 971 on
Flask and called the level `brief`; the level is `minimal` now.) A skeptical reader checks this number
first.

## Acceptance

1. The README number is true: either `minimal` gets down to about 100 tokens, or the README states the
   measured value and names the `detail_level` that gives it. The analysis picks one and records why.
2. A test measures `get_index_status` on a pinned in-repo fixture and fails when the README's number
   is off by more than ±20%, like the repo's other doc/number agreement tests.
3. If `minimal`'s shape changes, the byte-identical rule for `minimal` on a built index (061,
   `code_atlas/tools/get_index_status.py:278`) and the staleness verdict fields still hold.
   `stale_process` stays a verdict.

## Out of scope

- Per-response metadata on the other tools (brief A3).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 435 · **work_doc_mode:** embed · **Current phase:** done · merged in #160 as `07e63404`.
- `TRACK: backend` · Run mode: `autorun 434 - 435 - 436 --no-reviewer`, second — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON` ·
  `cost_tier: standard`. The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `docs/435-index-status-token-claim` from `main` at `e08d4b75`. Contract `.mango/run-contract-435.txt`. RECONCILE t0:
  `4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run`. Budget: unknown.

## Phase 0 — refine

`PREMISE: 2 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

`README.md:190` and `code_atlas/tools/get_index_status.py:278` resolve. H1 — which half of AC1: **correct the README**, keep
the payload. The review brief's own non-goal says never trade honesty fields for brevity, and `minimal`'s fields are
pinned by `tests/test_mcp_server.py::test_every_part_section_12_names_is_in_the_minimal_payload` and its 545-char budget;
reaching ~100 tokens would drop one of them. The ticket offers both halves, so this is a how-decision.

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Acceptance · Out of scope) | 3 decomposed | ROWS: C=0 R=0 G=1 AC=3`
`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/2 touched files under UI paths`
`SCOPE: S`
`TIER: full`
`STRUCTURE: native`

Measured on `tests/test_mcp_server.py`'s fresh fixture with `estimate_tokens`: `minimal` 519 chars / 130 tokens, `standard`
2,047 chars / 512 tokens. On this repo's own, behind index `minimal` is 830 chars: the behind fields add the rest.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "A skeptical reader checks this number first" | the README number is true | ⚠ |
| AC1 | Acc 1 | "the README states the measured value and names the `detail_level` that gives it" | H1 | ⚠ |
| AC2 | Acc 2 | "fails when the README's number is off by more than ±20%" | a test beside `MINIMAL_BUDGET` | ⚠ |
| AC3 | Acc 3 | "If `minimal`'s shape changes …" | not triggered: the payload is unchanged | ⚠ |

`BASELINE: green — tests/test_mcp_server.py on main at e08d4b75: 78 passed`

`RULE SECTIONS: 2 applicable — 2 by change-type | 0 by recalled handle — §6 (change-type) ✅ R6.5: the test seen red on the old "~100" · §7 (change-type) ✅ R7.2, R7.5, R7.6`

## Phase 2 — design

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

**Approach.** README: call it with `detail_level: "minimal"`, "~130-token on a fresh index", and `standard` "about four times
that". `tests/test_mcp_server.py`: `test_the_readme_quotes_what_the_minimal_payload_measures` reads the README number and
compares it with `estimate_tokens` of the fixture's `minimal` payload, ±20%; the budget comment stops saying "~100-token".
**Rejected:** a smaller `minimal` — it drops a field 061/316/429 pinned; a hard-coded number in the test — it would agree
with the README and drift from the payload together.
**Change list:** `README.md`, `tests/test_mcp_server.py`, `docs/PLAN.md`, `docs/CONVENTION.md` (added at review); bookkeeping (`docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, this file).
**Proving test:** `tests/test_mcp_server.py::test_the_readme_quotes_what_the_minimal_payload_measures`.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

## Phase 3 — execute

Main loop, no dispatch. **Verification sweep:** 2 files, both on the change list. **Seen failing (R6.5):** the README put
back to "~100" → the test red (1 failed); "~130" → green. Every test file that reads the README plus the doc-size
budget: 546 passed, 2 deselected (the host's PATH-tool skew pair). `ruff check` clean.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`. The rule-book reviewer was waived by the run's argument; no reviewer
step ran (no `reviewer`, no `reviewer-max`, no native `/code-review`).

- **`challenger` round 1** (ticket-blind, 51,727 tokens, at `e4011822`): 2 met · 1 partly met (AC1) · 1 can't tell (the
  analysis record, which it may not read).
  - **Important 1, taken** in `022ac39c`: `docs/PLAN.md:491` and `docs/CONVENTION.md:222` still said "~100 tok". Both now name
    `minimal` at ~130; PLAN sat at its 20,000-token ceiling, so the same row drops "bounded" to stay there.
  - **Important 2, taken** in `022ac39c`: "~130 on a fresh index" read as true only for the fixture. Measured after
    `code-atlas-build` on this repo (784 files, current): `minimal` 539 chars, ~134 tokens; behind, ~215. The README now
    says ~130 on a current index and ~200 on a behind one, and why.
  - **Minor, taken:** the regex anchors on the number, not the sentence. **Not taken:** a second, behind fixture for the
    ~200 figure — the behind payload grows with what it names, so one fixed number would pin a repo, not the tool;
    `json.dumps` vs the wire — `estimate_tokens` is the repo's one definition and the budget test uses the same.
- Seen after the fix: with the README at "~100" the test is red; at "~130" green. README-reading tests + budgets: 546 passed.

Verdict: clean (challenger only — REVIEWER: OFF), both Importants landed.
`Ph3/4 proven by`: AC1 → the README sentence and the measurements above; AC2 →
`test_the_readme_quotes_what_the_minimal_payload_measures`; AC3 → not triggered (no payload change); G1 → AC1 + AC2.

Reviewed at 022ac39c

## Phase 5 — finalise

**Durable lesson.** 435-C1 `a-claim-lives-in-every-copy` (new, type 2).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

**The final gate.** Docker on the final tree (the host gate is red on two tests that fail identically on `main` —
the host's PATH `code-atlas` is 0.9.1):

Ran at 58fa1bc4

```
$ scripts/docker-test.sh
5722 passed, 8 skipped in 725.94s (0:12:05)
```

### Outward actions

Under the handover: push `docs/435-index-status-token-claim`; open its PR against `main`. Deferred to the maintainer: merge.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 4 review | ticket-blind `challenger` | 1 | 51,727 |

`LEDGER TOTAL: 51,727 · top cost driver: 4 review / challenger` — main loop unmeasured.
