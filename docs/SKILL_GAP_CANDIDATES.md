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

---

## SG-2 — `execute` step 5 records the sweep once; it does not re-run it after a later commit

- **phase:** `mango:execute`, step 5 (verification sweep, Axis 1)
- **observed:** 2026-08-16, code-atlas ticket 100
- **status:** open

**What it does.** Requires the scope greps to be recorded as **empirical output** — the command and
its actual result pasted, not prose. That rule worked exactly as written.

**What it misses.** The sweep is scoped to *the change*, not to *the final state of the change*.
Nothing re-runs it after a later commit, so a paste that was honest when produced can be stale by
the time it is read — and both the phase and the review round that saw it will report clean.

**The incident.** The Phase-3 R1.1/R2.2 grep over the five touched core files came back clean and was
pasted into the working doc. A later commit, made to address a review finding, added a **docstring**
naming a language inside `code_atlas/tools/claim.py`. The project's own CI gate caught it
(`test_no_core_module_names_a_language[claim.py]`), but nothing in the lifecycle did: the recorded
sweep still read clean, and review round 1 had run before the text existed.

**A doable check the phase could name.** Re-run the recorded sweep commands against the **final**
reviewed SHA before the phase reports complete, and paste that second result beside the first — or
state plainly that the paste describes an earlier SHA. The commands are already written down; only
their re-execution is missing.

**Why it matters beyond one repo.** Any project whose scope discipline rests on a grep has this
shape. The gap is worst where the project has **no** CI gate for the same rule — here the build
failed loudly, but a project relying on the lifecycle's sweep alone would have shipped it, with a
clean pasted artifact standing as the evidence that it had not.
