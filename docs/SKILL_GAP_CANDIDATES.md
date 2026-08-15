# Skill-gap candidates — signals for the mango maintainer

Type-3 claims: a mango phase that could have run a check and did not. **Nothing here edits a mango
skill.** This repo records the signal; mango changes only through a normal version release.

Each entry names the phase, what it did, what it could have done instead, and the incident.

---

## SG-1 — `promote` step 4 checks for the *class*, not for the *substance*

- **phase:** `/mango:promote`, step 4 (idempotency)
- **observed:** 2026-08-15, code-atlas
- **status:** open

**What it does.** Greps the destination file for the handle slug and the group's claim IDs, and skips
a class already carrying a rule.

**What it misses.** A rule that already covers the same ground **under a different handle** has
neither the slug nor the IDs, so the grep is a clean miss and the candidate is proposed as new. The
step's own output requirement — paste the command and its result — makes the miss look like a
verified negative.

**The incident.** `prove-the-guard-fails` (recurrence 3) was proposed as a new rule while **R6.5**
already carried its special case: *"the exclusion itself needs a test asserting the sweep is still
non-empty; a filter that swallows the authored files restores the 0/0 vacuity the guard existed to
remove."* Caught by the human, not by the step. It shipped as a widening of R6.5.

**A doable check the step could name.** Before proposing, **read** the destination section the
candidate would join and state whether the substance is already present — and if it is, propose
widening the existing rule instead. That is a read the phase can perform with what it already has; it
does not need new tooling. Recorded in this project as [`AGENT_BRIEF.md`](AGENT_BRIEF.md) **P2**,
which is the local workaround, not a fix to mango.

**Why it matters beyond one repo.** The failure is silent and self-confirming: a skipped semantic
check and a genuine "not yet recorded" produce identical output, and the resulting near-duplicate
rule is exactly the drift a rule book exists to prevent.
