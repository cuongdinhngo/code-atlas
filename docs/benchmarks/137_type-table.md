# 137 — what the PHP local type table moved

**Status:** run, three pinned public repos, 2026-08-24 (Linux, PHP 8.3.6).
**Ticket:** task 137 (phase-1 archive).
**Baseline:** [136](136_heuristic-causes.md), reproduced on this host before any change.
**Verdict:** the HEURISTIC share is **not** two thirds of the graph, and it never was two thirds
because of missing type information. It is **1–4 %**, and what remains is the late binding 136
predicted plus receivers whose declaring member is not indexed.

```bash
python scripts/edge_health_report.py     # the table below
```

## The move

| repo | HEURISTIC before | after | share of all edges |
|---|---|---|---|
| `laravel/laravel` @ `ff031db` | 87 | **5** | 19.2 % → **1.1 %** |
| `symfony/demo` @ `03fe256` | 568 | **61** | 36.1 % → **3.9 %** |
| `brick/math` @ `b61d8e6` | 1 659 | **98** | 36.3 % → **2.6 %** |

Both targets 136 handed over are met: `brick_math` ≤ 200 (AC1), `symfony_demo` ≤ 450 (AC2).
`laravel_app` had no HEURISTIC target — its claims are now qualified names, which is what tells an
operator what to stub.

## Three mechanisms, measured separately

Each landed as its own commit, and the ticket asked for exactly that.

| | brick_math | symfony_demo | laravel_app |
|---|---|---|---|
| baseline | 1 659 | 568 | 87 |
| **hierarchy walk** — a method an ancestor or trait declares | 1 386 | 444 | 84 |
| **+ local type table** — a receiver this file types | 1 109 | 204 | 34 |
| **+ chain walk** — a receiver only the graph can type | **98** | **61** | **5** |

The order is the interesting part. The first two are what PLAN §1 promised, and on `brick/math`
they moved a third of the share. The last one — following `$a->b()->c()` into the file that
declares `b` — moved **twice as much as both of the others together**, because a fluent library is
mostly that shape. 136 could not see this: it classified by *cause*, and the cause of all of it is
"local type information". What it could not say is that most of that information is one file away.

## The number 136 could not predict

136 set the ceiling at "settleable **and** already linked": 92.5 % for `brick/math`. The result is
98.9 %. The ceiling was not wrong — it was a ceiling on a **type table alone**. The chain walk is
not a type table; it reads declared types the adapter had already recorded on nodes (144's
return types), so it settles receivers no single file could.

## Recall, proved rather than assumed

`all edges` on `brick/math` falls 4 573 → 3 753. A drop that size is what a **recall regression**
looks like, so it was checked against a baseline worktree at `2455835` rather than explained away:

| | baseline | after |
|---|---|---|
| distinct CALLS sites | 1 590 | **1 590** |
| sites that reach a target | 1 010 | **1 200** |
| sites that lost a target | — | **0** |
| CALLS rows | 3 041 | 2 218 |

Every call site still exists and none stopped reaching a target. The 823 rows that disappeared are
multi-candidate name-match siblings — one call site guessing at three or four same-named methods —
replaced by a single resolved edge. That is the precision axis [135](135_precision-axis.md) added,
moving for the first time.

## The benchmark answered two questions better, and said so by going red

`scripts/tokens_to_answer.py` failed its **precision** floor on two questions. Neither was a false
positive: both `expected_set`s had frozen the *old* under-reach as if it were the truth.

- **`reachable_from_entry`** gained `\Lib\Helper::go`, `\Lib\Service::run`, `\Lib\Child`,
  `\Lib\Child::ping`, `\Lib\Impl`, `\Lib\Impl::x`, `\Lib\IFace`. Reachability only walks
  RESOLVED edges, and `$h = new \Lib\Helper(); $h->go()` was a bare-name guess — so the traversal
  stopped **at** `Helper` and never entered `go()`. Those seven are what the fixture put behind it.
  `\Lib\Maybe` and `\Dead\Unused` are still unreached, which is what the question is for.
- **`onb_hub_blast_radius`** gained `InvoiceController::index` and `ReminderJob::run`, both of which
  reach `Clock::now` through `$service->recent()` on a typed parameter. They were always in the
  blast radius; the answer could not see them.

This is the ticket's point arriving where it counts. A HEURISTIC edge is not merely a weaker label —
it is **not traversed**, so every under-resolved receiver silently truncates an impact answer. The
share falling from a third to a fortieth is the headline; two whole-graph questions getting their
missing members back is the effect.

## What is left, and why none of it is a type table's job

| cause | brick_math | symfony_demo | laravel_app |
|---|---|---|---|
| `late_bound_or_string_name` | 90 | 28 | — |
| `unwalkable_receiver_chain` | 4 | 28 | — |
| `unknown_receiver` | 4 | 5 | 5 |

- **Late binding** is `static::m()` and string method names. 136 called this the one cause an LSP
  defer is right for and put it at ≤ 0.6 %; it is now the *majority* of what remains, which is what
  a residual is supposed to look like. It rose in absolute terms only because `static::` on an
  inherited method now names a real class at HEURISTIC instead of an unlinkable `\static::m` at
  RESOLVED — an honest tier replacing a false one.
- **`unwalkable_receiver_chain`** is new here: the receiver is a member's declared type, and the
  member is unindexed or declares no type. This is 136's `vendor/` cap wearing its own name — it is
  a missing *declaration* or a missing *target*, and no amount of type information closes it.
- **`unknown_receiver`** is down to 4–5 per repo, from 87–1 035.

`laravel/laravel` is still bounded at zero linkable, exactly as 136 said: every remaining receiver
points into `vendor/`. Turning 039's stub roots on is still the
separate decision it always was, and this page is still the evidence for it.
