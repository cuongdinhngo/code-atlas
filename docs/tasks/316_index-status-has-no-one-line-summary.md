---
id: 316
slug: index-status-has-no-one-line-summary
title: "get_index_status answers freshness in a wall of dense JSON with no one-line summary a reader can lift, so every routine is-it-fresh check reparses the payload"
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [077]
---

## Why this exists (field-retro batch 2026-09-20/21 — asked in all four)

Every retro in the batch, and the two before, made the same small ask: *"still a wall of JSON for
'is it fresh?'; a one-line human summary at the top would help."* The payload is rich and honest and
that is correct for diagnosis — but the routine call is a yes/no freshness check, and today it means
parsing the dict to find `staleness` + `last_commit`. The one existing quotable line, `claim`, is
opt-in behind `sign=true` (`get_index_status.py:156-158`, `:371-388`) and is agent/provenance-facing,
not a guaranteed top-of-payload summary.

## Goal

Put one lifted, human-readable sentence of ground truth at the head of every `get_index_status`
payload, without removing or duplicating the structured fields below it.

## Scope / Deliverables

1. **A leading `summary` string** assembled at the three payload sites (`_status`
   `get_index_status.py:356-441`, `_unbuilt` `:304-336`, `_mismatched` `:339-353`), e.g.
   `"current @ 7efaa91 · 13,377 files · 146,048 symbols · healthy"` /
   `"behind by 6 commits @ 7efaa91 (read tools still serve) — run build_or_update_index"` /
   `"not indexed — run build_or_update_index"`.
2. **Derived, never a second source of truth** — the summary is composed from the same fields it
   precedes (staleness, counts, `last_commit`, edge health), so it cannot disagree with them.
3. **Present at every detail level**, since the freshness check is exactly the `minimal` call.

## Constraints

- 061: it adds a field, it removes none; the structured payload is unchanged below it.
- The summary reuses the ref/revision naming from 077 (`head_ref`/`last_ref`), not a new vocabulary.
- R4.2: identical status → identical summary string.
- It states only what the payload already proves — no new judgment, no health claim the fields don't
  support.

## Acceptance criteria

- **AC1** Every `get_index_status` payload (built / behind / unbuilt / schema-mismatch) leads with a
  `summary` string naming freshness, revision and scale in one line.
- **AC2** The summary is a pure function of the structured fields — a test mutates a count/staleness
  fixture and the summary tracks it, with no independent data path.
- **AC3** The summary is present at `minimal` detail level.
- **AC4** The existing fields and the opt-in `claim` line are unchanged.

## Out of scope

- Changing the structured payload shape or the `sign=true` claim line.
- A terse mode that *omits* fields — this adds a header, it does not slim the body.

## References
`code_atlas/tools/get_index_status.py:304-336`, `:339-353`, `:356-441`, `:156-158`, `:371-388`,
[077](077_index-cannot-name-the-revision-it-describes.md), ENGINEERING_RULES R4.2.
<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 316 — index-status one-line summary (working doc)
- **TIER:** full · **TRACK:** backend · **SCOPE:** S · **BASELINE:** green
- **Depends on:** 077 (done)
- **reviewer:** off · **challenger:** on
- **Branch:** `feat/316-index-status-one-line-summary`
- **work_doc_mode:** embed

## Session status
- **Current phase:** finalise

## Phase 0
`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`
| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| 1 | How to lead the payload | Construct `{"summary": …, **rest}` (insertion order); not post-assign | nav_result list_result pattern; claim.py appends last |
| 2 | Behind/healthy wording without inventing counts | No commit-distance field → "behind @ sha …"; healthy only when edge_health.unlinked==0 | ticket Constraints; edge_health at standard+ |
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis
`SECTIONS: 5 found (Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=4 R=3 G=1 AC=4`
`RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — R4.2 (change-type) ✅ · R5.6 (change-type) ✅ · R7.2 (change-type) ✅`
`BASELINE: green`

| ID | Source | Interpretation | Status |
|----|--------|----------------|--------|
| C1 | 061 add field remove none | _with_summary only | ✅ |
| C2 | 077 ref vocab | last_commit/head_ref unchanged | ✅ |
| C3 | R4.2 | pure _compose_summary | ✅ |
| C4 | no new judgment | only existing fields | ✅ |
| R1 | summary at 3 sites | _unbuilt/_mismatched/_status | ✅ |
| R2 | derived | _compose_summary(payload) | ✅ |
| R3 | every detail level | wrap all returns | ✅ |
| G1 | one lifted sentence | AC1 | ✅ |
| AC1-AC4 | see proving test | ✅ | ✅ |

## AC validation
| AC | Match? | Falsifiable? |
|----|--------|--------------|
| AC1 | Y | greppable summary first key |
| AC2 | Y | unit test mutates fixture |
| AC3 | Y | minimal assert |
| AC4 | Y | claim + structured keys remain |

## Phase 2 — Design
**Approach:** `_compose_summary` pure fn + `_with_summary` leading wrap on all three builders; mismatched re-composes after schema merge.
**Rejected:** (a) architecture_overview-style late assign — puts summary last; (b) inventing commit distance — not in payload.
`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
**APPROVED CHANGE LIST:**
1. `code_atlas/tools/get_index_status.py` — compose + wrap
2. `tests/test_index_status_summary.py` — proving
3. `tests/test_get_index_status_health.py` — _MINIMAL_KEYS + summary
4. working doc / BACKLOG / TOKEN_LEDGER
**PROVING TEST:** `.venv/bin/python -m pytest tests/test_index_status_summary.py -q`
**TREE_PATHS:** `code_atlas/tools/get_index_status.py tests/test_index_status_summary.py tests/test_get_index_status_health.py docs/tasks/316_index-status-has-no-one-line-summary.md docs/BACKLOG.md docs/TOKEN_LEDGER.md`
**Gate 2 status:** cleared (autorun)

## Phase 3 — Execute
Implemented. Proving green.
`PROVING TEST:` `.venv/bin/python -m pytest tests/test_index_status_summary.py -q` → 3 passed.

## Phase 4 — Review
`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — round1 NOT CLEAN (AC1 scale on behind/unbuilt); round2 CLEAN (agent 5ca3ce1a). Gate 4: challenger CLEAN; reviewer waived.

## Phase 5 — Finalise
`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop`
