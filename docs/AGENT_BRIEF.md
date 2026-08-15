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

`PROVISIONAL (awaiting ratification)` — from 099, 2026-08-15.

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

---

## Not in scope here

- **Code rules** → [`ENGINEERING_RULES.md`](ENGINEERING_RULES.md).
- **Gaps in the mango harness itself** → [`SKILL_GAP_CANDIDATES.md`](SKILL_GAP_CANDIDATES.md).
  No lesson from this repo edits a mango skill; the signal is recorded for its maintainer.
- **Project facts and findings** → [`LESSONS.md`](LESSONS.md) and [`PLAN.md`](PLAN.md) §19.
