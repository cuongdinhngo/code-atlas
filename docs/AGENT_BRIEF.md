# Agent brief — code-atlas

**Process** rules for working this repo: how the lifecycle is *run*, not how the code is *built*.
Code rules live in [`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) and win on any code question; this
file never restates one. Each rule here earned its place by costing something — the incident is cited,
and a rule whose incident stops recurring should be retired rather than kept for tidiness.

Rules are `P<n>`. Same status vocabulary as the rule book: `PROVISIONAL (awaiting ratification)`
until a second incident confirms the shape.

---

## P1 — A claim's `seen:` list grows when the handle is **answered**, not when a lesson is written

`PROVISIONAL (awaiting ratification)` — from the `/mango:promote` run of 2026-08-15.

When a design phase recalls a handle and answers it **traced** — the class bound this change, and the
working doc's `HANDLES` table says how — append this ticket's key to that claim's `seen:` list in
`LESSONS.md`, in the same commit. Do **not** append on a `does not apply` answer: recurrence must
count where the class did work, or promotion fires on recall frequency instead of on the heuristic
actually recurring.

**Why it costs.** Recurrence is promotion's only gate. Left to grow only when someone writes a *new*
lesson, it under-counts every class that keeps being honoured rather than re-broken — which is
precisely the class most worth promoting. Measured: `prove-the-guard-fails` read as recurrence **1**
while it had in fact bound three tickets (093, 096, 099), and would have gone unpromoted;
`derived-not-listed-invariant` had two uncredited sightings and R6.7 cited two of its three claims.

**Falsifier.** A working doc whose `HANDLES` table records a `traced` answer for a handle whose
claim record does not list that ticket in `seen:`.

## P2 — Before proposing a promotion, **read** the destination section; the grep is not the check

`PROVISIONAL (awaiting ratification)` — same run.

`/mango:promote`'s idempotency step greps the destination for the **handle slug** and the **claim
IDs**. That finds a rule promoted from *this* class. It cannot find a rule that already covers the
same ground under a different handle, because nothing links them. So before a candidate goes to a
human, read the destination's relevant section and say plainly whether the substance is already
there — and if it is, propose **widening the existing rule** rather than adding a near-duplicate.

**Why it costs.** A near-duplicate rule is worse than no rule: two rules for one principle drift
apart, and a reader who satisfies one believes they are done. Measured: `prove-the-guard-fails` was
proposed as a new `R6.8` while **R6.5** already carried its special case (*"the exclusion itself
needs a test asserting the sweep is still non-empty"*); it landed as a widening of R6.5 instead.

**Falsifier.** Two rules in `ENGINEERING_RULES.md` whose falsifiers would be tripped by the same
diff.

## P3 — Record a deviation from the ticket text as a deviation, in the ticket

`PROVISIONAL (awaiting ratification)` — from 099, 2026-08-15. Handle
`record-the-deviation-as-a-deviation` (`LESSONS.md` `PROM-C3`, seen promote-2026-08-15, 101).

A ticket is written at a point in time and the code moves under it. When shipping something the
ticket's own words contradict, say so in the Resolution — what the ticket said, what shipped, and
which later ticket changed the ground — and, where it is testable, assert the superseded form is
**absent**.

**Why it costs.** A silent "correction" is indistinguishable from a misread requirement at review
time. Measured: 099's evidence table asked the untracked signal to warn about `no_such_symbol`; 092
had since changed that to `not_indexed`, so the shipped line says `not_indexed` and a test asserts
`no_such_symbol` never appears.

**Falsifier.** A diff that contradicts a quoted ticket requirement with no deviation note in the
working doc.

## P4 — A quoted gate result names the commit it was run at, and that commit is the last one

`PROVISIONAL (awaiting ratification)` — promoted from `LESSONS.md` `100-C3` (handle
`re-run-the-sweep-after-the-last-edit`, seen 100, 101, 102) by the `/mango:promote` run of 2026-08-16.

A sweep, grep-gate or suite run is evidence about **one commit**, never about a ticket. Before quoting
one as done — in a working doc, a PR body, or a cost ledger — re-run it after the **final** edit,
including a docs-only or bookkeeping commit, and record the SHA it describes beside the count.

**Why it costs.** The claim is honest when measured and false when read, and no reviewer can catch it:
the text that breaks it post-dates the review. Measured three times. In **100** the Phase-3 R1.1 sweep
was clean and a later commit's *docstring* reintroduced a language name in a core module, failing the
build. In **101** the delta-green claim was *"true when it was measured and stale when it was
committed"* — the docs commit flipped `status: todo → done` in both places, which is exactly what arms
`test_backlog_bookkeeping.py::test_a_finished_task_records_what_it_cost`, and that test then demanded a
Token-usage row that did not exist yet; the class had been recalled at refine and judged *"does not
apply"*, and it was the one that fired. In **102** the ordering was built around it up front and the
gate re-ran at the final SHA — no incident.

**Falsifier.** A working doc, PR body or ledger quoting a gate result whose recorded SHA is not the
branch tip — or quoting a count with no SHA at all, which is the same failure with the evidence
removed.

## P5 — Blast-radius tracing enumerates count-pins, not just globs

`PROVISIONAL (awaiting ratification)` — handle `count-pin-in-blast-radius` (`LESSONS.md` `085-C1`,
seen 085, 087–089).

When a change adds a member to a surface (a tool, a core module, a registered name), a Gate-2
blast-radius trace lists not only the globs that auto-cover it but every test that count-pins or
lists a subset of that surface (`len(...) == N`, a hard-coded member list). A matched pin enters the
approved change list.

**Why it costs.** A glob auto-covers the new member and reads as full coverage; the `len(...) == N`
beside it does not, and the bump surfaces later as an execute-phase deviation instead of a planned
edit.

**Falsifier.** A blast-radius cell listing only globbing guards for a surface the change extends,
with a `len(...)==N`/listed-subset pin on it unlisted and later caught as a deviation.

## P6 — A verified assumption holds only for the path and tree it was checked on

`PROVISIONAL (awaiting ratification)` — handle `re-verify-the-assumption-on-a-new-path`
(`LESSONS.md` `102-C1`, seen 102, 107, 122).

When a change adds a call path parallel to the one an assumption was verified on, re-verify on the
new path; when a ticket inherits a count measured before a sibling landed, re-measure at current
HEAD. A Gate-2 "verified" is not transitive to a path the same change introduces.

**Why it costs.** The assumption was true of the loop it was read against and false of the loop the
same change added; the count was measured before the sibling that moved it. No reviewer catches it —
the breaking path post-dates the check.

**Falsifier.** An assumption marked verified read against one branch while an added parallel branch
is unguarded, or an AC citing a count not re-measured at pickup HEAD.

---

## Not in scope here

- **Code rules** → [`ENGINEERING_RULES.md`](ENGINEERING_RULES.md).
- **Gaps in the mango harness itself** → [`SKILL_GAP_CANDIDATES.md`](SKILL_GAP_CANDIDATES.md).
  No lesson from this repo edits a mango skill; the signal is recorded for its maintainer.
- **Project facts and findings** → [`LESSONS.md`](LESSONS.md) and [`PLAN.md`](PLAN.md) §19.

## P7 — A dimension's second value makes every aggregate over it a blend

`PROVISIONAL (awaiting ratification)` — handle `an-aggregate-outlives-the-world-that-named-it`
(`LESSONS.md` `183-C1`, `195-C1`).

When a change gives a dimension its second value — a second adapter, tenant, region or repo —
enumerate every aggregate over that dimension **from the code**, and record per consumer whether it
wants the whole, the slice, or both. The enumeration is a change-list item. Distinct from P5, which
fires when a change **adds a member to a surface**: this one fires with no code change at all.

**Why it costs.** The aggregate needs no edit to become wrong, so nothing fails: `edge_health`
silently became a blend when a second language arrived, and the enumeration found **four** consumers
where the ticket named three — the one it missed was the one the previous change had already fixed.

**Falsifier.** A change adding producer #2 whose change list carries no aggregate enumeration.
