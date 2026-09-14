---
id: 275
slug: four-green-rows-frame-two-red-ones-as-absence
title: 'A batched `search_symbol` spends one repair budget across every subject, so a sweep returns `index_stale, total_count: 0` beside four `ok` subjects in one payload with nothing on the envelope to separate them — and a refusal read as an absence nearly shipped a query against a table that does not exist'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [101, 246, 073]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 23 §4b)

One sweep, six subjects, `kind=Table`. Four resolved. `TranTypes` and `Schedule_Detail` came back
`reason: index_stale, total_count: 0` **inside the same response**. The docstring documents the
mechanism (`search_symbol.py:105–107`: *"a sweep shares one read-through repair budget across every
subject, so a subject whose file drifted may answer `index_stale` where a single call would have
repaired it"*), and the envelope says nothing.

Read in place, four green rows frame the two red ones as *these do not exist*. The two were not even
the same failure: `TranTypes` genuinely does not exist — the table is `dbo.LedgerTranType`, which the
same call surfaced under another subject — while `Schedule_Detail` exists as a **VIEW**, which the
`kind=Table` filter would have excluded regardless. One label hid both.

The near-miss is the point. A contract doc claimed a join against `TranTypes`. `index_stale` is
*consistent with* "stale index, table is fine", which would have shipped a read returning zero rows
forever. What caught it was querying the database, not the payload.

## Scope / Deliverables

- **A mixed sweep is flagged on the envelope** (call-level, never per subject — 061): when any
  subject answered `index_stale` while another answered `ok`, the envelope names the refused
  subjects and says the budget decided, not the graph.
- **A route on the refusal**: the single-subject call that would have spent the whole budget on it.
  A refusal an agent cannot act on is one it learns to ignore (267).
- **Spend the budget where it was asked for, not where it fell.** Today the order of `queries`
  decides which subject gets the one repair. Either state that rule in the payload or make it
  deterministic and stated; silence is what makes the mixed answer unreadable.
- **A filtered-out kind is not a miss.** `kind=Table` excluding a `View` of the same name is the
  other half of this misread: an excluded exact-name hit says so, rather than reading as absence
  (this is the 265 census rule, applied to `kind`).

## Constraints

- The per-call repair cap stays at 1 ([246](246_ensure-miss-refuses-on-the-count-of-drifted-files-not-on-the-subject.md)):
  this ticket changes what the payload *says*, not how much it reparses.
- 101's batch bound and the per-subject isolation stay — one miss must still not colour the rest.
- 061: a sweep where every subject answered `ok` gains nothing.
- R5.6: the envelope names the budget as the cause only where that is what happened.

## Acceptance criteria

- A fixture sweep with one drifted subject and three current ones returns the envelope flag naming
  the refused subject, and the three `ok` subjects are unchanged.
- The refused subject's entry carries the single-subject route.
- A sweep whose subject matches only a kind the filter excluded reports the exclusion, not an empty
  result set.
- A fully-`ok` sweep is byte-identical to today's payload.

## References
`code_atlas/tools/search_symbol.py:105–107,189–195`, `code_atlas/tools/freshness.py` (read-through
cap), field retro round 23 §4b / §4g #2,
[246](246_ensure-miss-refuses-on-the-count-of-drifted-files-not-on-the-subject.md),
[265](265_the-default-page-order-is-the-alphabet.md),
[267](267_the-warning-an-autonomous-agent-cannot-act-on.md).
