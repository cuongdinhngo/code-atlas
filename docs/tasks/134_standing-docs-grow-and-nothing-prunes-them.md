---
id: 134
slug: standing-docs-grow-and-nothing-prunes-them
title: The standing docs grew to 66k tokens of mostly retold narrative — prune them and gate the size
phase: 1.5b
milestone: Docs
status: done
depends_on: [132]
---

## Why this exists

Reported by the maintainer, not by a test: *"AI sinh docs quá dài, mỗi session lại thêm vào, mà không
có review và thanh lọc."* Measured on `03ac330`, `PLAN.md` + `BACKLOG.md` cost **56,039 tokens**, and
the growth had no brake — every session appended and none pruned. Both files are on `AGENTS.md`'s
*read before non-trivial work* list, so the whole of it is charged to every session (that is 133's
number, and this ticket moves it without touching 133's structural work).

The bulk was **retold, not recorded**. `BACKLOG.md` carried ~180 lines of round-by-round ordering
narrative already held by `FEEDBACK.md`, the task files and `benchmarks/`, plus a token ledger whose
cells had become per-ticket retrospectives — the ledger's job is spend and a PR link. `PLAN.md` §19
carried eleven field-retro session stories where the decision each produced was three lines of them.
`BACKLOG.md`'s own Conventions section already said *"landed narrative belongs in PLAN §19 or
LESSONS.md, not here"*: **the rule existed and nothing enforced it.**

## Scope

1. Prune both files: keep every table, decision, gate and live constraint; cut narrative that a task
   file, `LESSONS.md`, `FEEDBACK.md` or a `benchmarks/` file already holds, replacing it with a
   pointer. **No decision, ticket, gate or open follow-up is dropped.**
2. Compress the Token-usage ledger cells to the measured spend; the mango-phase detail stays in each
   task's embedded work doc.
3. **R7.6** — a standing document is pruned by the change that adds to it. Widen `AGENTS.md`'s
   docs-before-PR bullet and the pre-PR self-check to carry it.
4. **`tests/test_doc_size_budget.py`** — a per-file token ceiling using `estimate_tokens` (R6.7, one
   definition site), shipped with a recorded red run, plus a guard-the-guard test so a budget cannot
   be slack.

## Acceptance criteria

- **AC1** Both files are materially smaller, measured with `estimate_tokens` before and after.
- **AC2** No table row, decision, gate, ticket reference or open follow-up is lost; internal links
  across the standing docs still resolve.
- **AC3** R7.6 exists with a falsifier, and the pre-PR self-check asks for the prune.
- **AC4** The budget test fails on the pre-prune files. Red run recorded.
- **AC5** `tests/test_backlog_bookkeeping.py` still passes unchanged — the prune moves text, not the
  contract the guard reads.

## Widening, recorded as a deviation (P3)

The ticket was written for `PLAN.md` and `BACKLOG.md`. The maintainer then asked for
`ENGINEERING_RULES.md` — *"it is the project's standard, it cannot be this verbose"* — naming the
provenance lines specifically: *"putting a task's parameters in there means nothing and can cost more
tokens."*

That is right, and it has a precise argument rather than a stylistic one. **The rule book's `seen:`
lists had no reader.** `AGENT_BRIEF.md` P1 binds the sightings list in `LESSONS.md`, and
`/mango:promote` greps a destination only for the **handle slug** and the **claim IDs** to know a class
is already carried. So every provenance line is now `handle (claim-ids)` — nothing the tooling reads
was dropped — and the sightings stay in `LESSONS.md`'s class index alone. This **dissolves** lesson
`132-C2` (`rule-seen-list-drifts-from-the-index`), which had proposed reconciling the two copies on a
schedule: there is now one copy, so there is nothing to reconcile. Recorded there as resolved.

`ENGINEERING_RULES.md` and `CONVENTION.md` also joined the size ceiling. The rule book was pruned to
fit; **`CONVENTION.md` was frozen, not pruned** — its ceiling sits just above its current spend, so
the next convention arrives with a prune instead of on top. Its own prune is unticketed.

## Out of scope

- **Tiering the agent chain (133).** This ticket lowers the number; 133 still owns moving the ledger
  and §19 out of tier 1 and gating the tier.
- **Task files.** `132_docs-restructure.md` alone is 36 KB — the same disease, one directory over,
  and a task file is read on purpose rather than every session. Recorded here, not fixed.
- **`LESSONS.md`.** Its size is its function (P1's `seen:` counts); 133 already says so.

## Outcome

PR [#155](https://github.com/cuongdinhngo/code-atlas/pull/155). **Done.** `PLAN.md` **27,447 → 22,703** tokens (1,125 → 996 lines), `BACKLOG.md` **28,592 → 12,655**
(630 → 439 lines): **56,039 → 35,358**, a **37 %** cut with nothing lost from the change lists.

- **AC1/AC2** Every table kept intact; the 11-row *Where these tickets came from* table now honours
  its own promise of "one line each"; every follow-up bullet survives with its pointer. Link sweep
  over the 100 standing markdown files: **0 broken**.
- **AC4 red run:** with the pre-prune files restored — `docs/BACKLOG.md is 28,592 tokens against a
  budget of 14,000` and `docs/PLAN.md is 27,447 tokens against a budget of 24,000`, 2 failed.
- **AC5** `tests/test_backlog_bookkeeping.py` — **264 passed**, unchanged.
- **`ENGINEERING_RULES.md` 4,558 → 3,950 tokens**, all 38 rule ids and all 7 handles + claim ids
  intact. Two more red runs recorded: the pre-trim rule book at 4,558 against its 4,200 ceiling, and
  `CONVENTION.md` at 6,151 against 6,100 after one appended section.
- **`scripts/agent_chain_cost.py`** — 133's AC1, pulled forward because this ticket's ceilings were
  constants chosen from a session run, and R6.3's falsifier is *"a threshold whose only evidence is a
  fixture or a session transcript, with no committed reproducer"*. It derives the chain from
  `CLAUDE.md`'s `@import` and `AGENTS.md`'s own *read before non-trivial work* list rather than
  listing it (R6.7), and reports **7 files · 2,134 lines · 49,153 tokens**, byte-identical across
  runs. `tests/test_doc_size_budget.py` now derives the *bounded* set from it, which closed a real
  hole: `AGENTS.md` and `AGENT_BRIEF.md` were on the chain with no ceiling. Red run: adding
  `LESSONS.md` to the binding list fails with *"the chain binds files with no budget"*.
- **Side effect on 133.** The six standing docs measured here — `AGENTS.md`, `PLAN.md`, `BACKLOG.md`,
  `ENGINEERING_RULES.md`, `AGENT_BRIEF.md`, `CONVENTION.md` — go **70,329 → 49,150 tokens (−30 %)**
  with none of 133's structural moves. That is this ticket's own measurement, not 133's number: 133's
  tier-1 figure is whatever `scripts/agent_chain_cost.py` reports once its AC1 ships, and its
  **< 25,000** goal still needs the ledger and §19 to move.
