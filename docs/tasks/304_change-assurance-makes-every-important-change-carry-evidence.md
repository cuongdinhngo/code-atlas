---
id: 304
slug: change-assurance-makes-every-important-change-carry-evidence
title: "EPIC — make every important change carry graph-derived evidence before review"
phase: 3
milestone: Change-Assurance
status: done
depends_on: [100, 138, 139, 257, 260, 266]
kind: epic
children: [303, 305, 306, 307, 308, 309, 310, 312]
---

## Why this existed

code-atlas answers relationship, impact, architecture-rule and drift questions, but those answers
were optional calls. The epic's bet was that packaging them — `change → verify → evidence bundle →
brief / policy / test candidates → review` — would make the change workflow observably safer.

## Outcome — closed 2026-09-20, the bet did not pay

**The packaging half was removed in the same week it shipped.** 303, 305, 306 and 307 landed, were
never called by anything, and were deleted: 1,776 production lines and 1,233 test lines. The
measurement half (308 + 309 + 312) is kept.

Three facts decided it, each checkable from the tree at the removal commit:

1. **Nothing consumed the layer.** `evidence_bundle`, `change_brief` and `architecture_policy` had
   exactly one importer between them — `check.py` — and `code-atlas-check` was invoked by no
   script, no `gate.sh` check and no `ci.yml` job. A closed loop of four modules feeding one
   command nobody ran.
2. **None of it reached an agent.** The whole layer was CLI-only; the MCP surface stayed at 24
   tools and none of them came from this epic. MCP is the only surface an agent on an anchor repo
   touches, so the layer was unreachable from the work it was built to make safer.
3. **No child but 309 produced a number.** 303, 305, 306 and 307 shipped tests and zero evidence
   that a review went differently because they existed. 310 was to supply that evidence end-to-end
   and was dropped before it ran (see its ticket).

**What the anchor retros say instead.** Thirty-one rounds of real sessions on a 23,380-file repo
rank the tools by use — `find_callers` 393, `read_symbol` 358, `find_references` 319,
`search_symbol` 312, `impact` 257 — and score `impact` **5/10 twice**, for two named reasons:
`subject_ambiguous` on the repo's most defect-dense file category, and unranked output that buries
ten production callers under sixty rows of legacy twins and tests. The fix asked for is the
production/test and `src/`-vs-`legacy/` split `find_callers.py:633` already computes and
`impact.py` does not mention once. **Building packaging on top of a 5/10 engine cannot exceed
5/10** — the epic spent its budget one layer above its bottleneck.

## What survives

- **308 `candidate_tests.py`** — changed code → candidate test files, report-only. Kept because it
  is the one child with a measurement attached and a question an agent actually asks. It has no
  MCP surface either; it earns one or it follows the rest out.
- **309 + 312 — the measurement method.** `scripts/test_impact_recall.py` and
  [`benchmarks/309_test-impact-recall.md`](../benchmarks/309_test-impact-recall.md): ground truth
  from upstream maintainers' own test edits, a committed re-runnable reporter, a bar ratified
  before the run. It measured recall **0.9412** and caught the walk stopping one hop early. This is
  reusable for any future claim about the graph and is the epic's real product.
- **The honesty discipline**, which predates the epic and was confirmed by it: round 29 quotes
  `sign: true` returning `index=behind` mid-session — *"it says so instead of pretending. That is
  the right behaviour and it is worth keeping."*

## Settled decisions that outlive the epic

1. Test impact stays **report-only**; the full suite remains authoritative. No child ever shipped a
   skip list and none may.
2. The core stays local-first, deterministic and language-agnostic — no LLM, network call, source
   mutation or second pipeline entered it.
3. **A capability with no caller and no number is not shipped, it is stored.** Recorded as the
   epic's lesson: reach the surface the user is on before building a layer above it.
