# Agent brief — code-atlas

**Process** rules for working this repo: how the lifecycle is *run*, not how the code is *built*.
Code rules live in [`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) and win on any code question; this
file never restates one. Each rule here earned its place by costing something — the incident is cited,
and a rule whose incident stops recurring should be retired rather than kept for tidiness.

Rules are `P<n>`. Same status vocabulary as the rule book: `PROVISIONAL (awaiting ratification)`
until a second incident confirms the shape, then `Ratified <date>`. P1–P7 were ratified 2026-08-30
at recurrence ≥ 2; their incidents are phase-1 tickets and claim ids, which resolve in the phase-1
archive.

---

## P1 — A claim's `seen:` list grows when the handle is **answered**, not when a lesson is written

`Ratified 2026-08-30`.

When a design phase recalls a handle and answers it **traced** — the class bound this change, and the
working doc's `HANDLES` table says how — append this ticket's key to that claim's `seen:` list in
`LESSONS.md`, in the same commit. Do **not** append on a `does not apply` answer: recurrence must
count where the class did work, or promotion fires on recall frequency instead of on the heuristic
actually recurring.

**Why it costs.** Recurrence is promotion's only gate; left to grow only on a *new* lesson, it
under-counts the classes being honoured rather than re-broken — `prove-the-guard-fails` read 1 while
it had bound three tickets.

**Falsifier.** A working doc whose `HANDLES` table records a `traced` answer for a handle whose
claim record does not list that ticket in `seen:`.

## P2 — Before proposing a promotion, **read** the destination section; the grep is not the check

`Ratified 2026-08-30`.

`/mango:promote`'s idempotency step greps the destination for the **handle slug** and the **claim
IDs**. It cannot find a rule that already covers the same ground under a different handle. So before
a candidate goes to a human, read the destination's relevant section and say plainly whether the
substance is already there — and if it is, propose **widening the existing rule** instead.

**Why it costs.** Two rules for one principle drift apart, and a reader who satisfies one believes
they are done — `prove-the-guard-fails` was proposed as a new R6.8 while R6.5 already carried it.

**Falsifier.** Two rules in `ENGINEERING_RULES.md` whose falsifiers would be tripped by the same
diff.

## P3 — Record a deviation from the ticket text as a deviation, in the ticket

`Ratified 2026-08-30` — handle `record-the-deviation-as-a-deviation`.

A ticket is written at a point in time and the code moves under it. When shipping something the
ticket's own words contradict, say so in the Resolution — what the ticket said, what shipped, and
which later ticket changed the ground — and, where it is testable, assert the superseded form is
**absent**.

**Why it costs.** A silent "correction" is indistinguishable from a misread requirement at review
time.

**Falsifier.** A diff that contradicts a quoted ticket requirement with no deviation note in the
working doc.

## P4 — A quoted gate result names the commit it was run at, and that commit is the last one

`Ratified 2026-08-30` — handle `re-run-the-sweep-after-the-last-edit`.

A sweep, grep-gate or suite run is evidence about **one commit**, never about a ticket. Before quoting
one as done — in a working doc, a PR body, or a cost ledger — re-run it after the **final** edit,
including a docs-only or bookkeeping commit, and record the SHA it describes beside the count.

**Why it costs.** The claim is honest when measured and false when read, and no reviewer can catch
it: a later docstring put a language name in a core module after a clean sweep, and a `status: done`
flip armed a ledger test after a green suite.

**Falsifier.** A working doc, PR body or ledger quoting a gate result whose recorded SHA is not the
branch tip — or quoting a count with no SHA at all.

## P5 — Blast-radius tracing enumerates count-pins, not just globs

`Ratified 2026-08-30` — handle `count-pin-in-blast-radius`.

When a change adds a member to a surface (a tool, a core module, a registered name), a Gate-2
blast-radius trace lists not only the globs that auto-cover it but every test that count-pins or
lists a subset of that surface (`len(...) == N`, a hard-coded member list). A matched pin enters the
approved change list.

**Why it costs.** A glob reads as full coverage; the `len(...) == N` beside it surfaces later as an
execute-phase deviation instead of a planned edit.

**Falsifier.** A blast-radius cell listing only globbing guards for a surface the change extends,
with a `len(...)==N`/listed-subset pin on it unlisted and later caught as a deviation.

## P6 — A verified assumption holds only for the path and tree it was checked on

`Ratified 2026-08-30` — handle `re-verify-the-assumption-on-a-new-path`.

When a change adds a call path parallel to the one an assumption was verified on, re-verify on the
new path; when a ticket inherits a count measured before a sibling landed, re-measure at current
HEAD. A Gate-2 "verified" is not transitive to a path the same change introduces.

**Why it costs.** The assumption was true of the loop it was read against and false of the loop the
same change added. No reviewer catches it — the breaking path post-dates the check.

**Falsifier.** An assumption marked verified read against one branch while an added parallel branch
is unguarded, or an AC citing a count not re-measured at pickup HEAD.

## P7 — A dimension's second value makes every aggregate over it a blend

`Ratified 2026-08-30` — handle `an-aggregate-outlives-the-world-that-named-it`.

When a change gives a dimension its second value — a second adapter, tenant, region or repo —
enumerate every aggregate over that dimension **from the code**, and record per consumer whether it
wants the whole, the slice, or both. The enumeration is a change-list item. Distinct from P5, which
fires when a change **adds a member to a surface**: this one fires with no code change at all.

**Why it costs.** The aggregate needs no edit to become wrong, so nothing fails: `edge_health`
silently became a blend when a second language arrived.

**Falsifier.** A change adding producer #2 whose change list carries no aggregate enumeration.

## P8 — A change that moves graph counts re-runs cross-repo and re-floors in the same PR

`Ratified 2026-09-30` by the maintainer on one incident — handle `ungated-floor-drifts-silently`.

When a resolver, indexer or adapter change moves what a build emits, run
`scripts/cross_repo_validate.py --public-only` before the PR. A floor moved **by design** is
re-measured at ≈80% of the new build in the same PR, old→new counts in the manifest's
`contract_note`; a floor moved **by accident** is a regression.

**Why it costs.** The job is weekly and outside the gate: 258 cut socketio's edges by design, and
the stale floors failed 16 days later (issue #4), which took a bisect to tell apart (349).

**Falsifier.** A merged change after which `cross_repo_validate.py --public-only` fails on a floor
the change moved.

---

## Not in scope here

- **Code rules** → [`ENGINEERING_RULES.md`](ENGINEERING_RULES.md).
- **Gaps in the mango harness itself** → [`SKILL_GAP_CANDIDATES.md`](SKILL_GAP_CANDIDATES.md).
  No lesson from this repo edits a mango skill; the signal is recorded for its maintainer.
- **Project facts and findings** → [`LESSONS.md`](LESSONS.md) and [`PLAN.md`](PLAN.md) §19.
