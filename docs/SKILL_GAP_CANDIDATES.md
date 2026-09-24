# Skill-gap candidates — signals for the mango maintainer

Type-3 claims: a mango phase that could have run a check and did not. **Nothing here edits a mango
skill.** This repo records the signal; mango changes only through a normal version release.

Each entry names the phase, what it did, what it could have done instead, and the incident.

---

## SG-3 — `autorun`'s envelope scripts assume a POSIX shell; on Windows the checks run under cmd.exe

- **phase:** `/mango:autorun` — `scripts/run_contract.py` (`write`, deriving `value`) and
  `scripts/reconcile.py` (`run`, executing each condition's `check`)
- **observed:** 2026-08-17, code-atlas, task 083 (second autorun in this repo)
- **status:** open

**What it does.** Both scripts run a condition's `derived-by` / `check` command via
`subprocess.run(command, shell=True)`. On a POSIX host that is `/bin/sh -c <command>`, so the floor
checks — written as shell one-liners — run as intended.

**What it misses.** On Windows, `subprocess(shell=True)` invokes **`cmd.exe /c <command>`**, not a
POSIX shell. `cmd.exe` ignores single quotes and treats `&&`, `"`, `|`, `(`, `)` as its own
metacharacters regardless of quoting. The `LOCAL-HEAD-PUSHED` floor check the skill prescribes —
`L=$(git rev-parse --verify -q <branch>) && R=$(...) && test "$L" = "$R"` — is therefore split by
`cmd.exe` at the first `&&` and fails with `'R' is not recognized…`, reporting a spurious result that
has nothing to do with whether the head is pushed. The two floor checks that are single native
commands (`gh pr view …`, `git diff --quiet …`) work; only the one needing shell composition breaks.

**The incident.** Building the RUN CONTRACT for task 083 on the Windows dev host, the prescribed
`LOCAL-HEAD-PUSHED` check errored under `cmd.exe` before the run could start. Workaround: wrap the
POSIX body in `bash -lc "…"` **inside cmd double-quotes** (cmd double-quotes protect `&&`; the body
uses `[[ -n $L && $L = $R ]]` so no inner double-quotes are needed), and resolve refs with
`git rev-parse --verify -q` so an absent branch reports BROKEN rather than the empty-vs-empty HOLDING
the skill already warns about. The rest of the envelope (t0 clean, gate-2 bind, close 3/3 holding)
then ran correctly.

**A doable check the scripts could name.** Either (a) run the shell command explicitly through a
POSIX shell — `subprocess.run(["bash", "-lc", command])` / honour `SHELL` — so the prescribed
one-liners are portable, or (b) document in the skill that on a non-POSIX host each floor `check`
must be a single native command or a `bash -lc` wrapper inside cmd double-quotes. Neither needs new
tooling; (a) is a one-line change to how the command is spawned.

**Why it matters beyond one repo.** `autorun`'s whole value is that the harness — not the agent —
decides each condition. A checker that mis-fires for a shell reason on the maintainer's own platform
undercuts exactly that guarantee: the agent has to hand-repair the check, which is the manual step
the envelope exists to remove. Any Windows-hosted mango user hits this the first time a floor check
needs shell composition.

---

## SG-2 — `design`'s Assumptions table has no per-call-path denominator

- **phase:** `/mango:design`, step 3 (Assumptions)
- **observed:** 2026-08-16, code-atlas, task 102
- **status:** open

**What it does.** Requires every assumption to be tagged `verified | novel-untested`, and every
`novel-untested` third-party/runtime one to be resolved by a spike or by an integration-shaped
proving test. Task 102 did exactly that: a spike was run, its output pasted, and the assumption
tagged `verified`.

**What it misses.** An assumption is verified **against a call path**, and the step records no
denominator for how many call paths the change will have. Task 102's assumption 3 —
*"a `resolved_unique` resolution can never reach the miss-explainer"* — was true of the one loop that
existed and false of the second loop the same change added. The spike output even showed the
mislabelling that would occur (`classify('Nope') -> resolved_unique … 'reason': 'name_not_qualified'`)
and was cited as the reason the guard keys on `status` — for one caller. The tag read `verified` for
the change as a whole.

**The incident.** The reviewer found it: `impact(qnames=["App\Nope"])` returned `results=2
seeds_dropped=0` while `impact(paths=["App\Nope"])` returned `results=0 seeds_dropped=1
reason=name_not_qualified` — a resolvable subject reported as absent, which is the defect class the
ticket was opened to remove, reintroduced inside its own fix. Every gate before review passed:
`diff ⊆ approved list`, design-conformance clean on all five approach bullets, 5/5 new guards
observed failing first, full suite green.

**A doable check the step could name.** When an assumption is about a **code path** (*"X can never
reach Y"*), enumerate the call paths that will consume the assumption **after** the change — the
change list already names them — and record the assumption as `verified k/N paths`. Task 102's would
have read `1/2` and blocked. This needs no new tooling: the change list and the blast-radius trace
are already in front of the phase.

**Why it matters beyond one repo.** A `verified` tag on an assumption is one of the few things later
phases do not re-derive — review re-checks scope and behaviour, not the Assumptions table — so a
half-verified assumption travels all the way to the reviewer, who is the last line rather than a
second line. Here the reviewer caught it; a run with the challenger waived and a less thorough
reviewer would have shipped it.

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

## Type-3 signals from the 8-ticket `/mango:autorun` batch (2026-08-28, mango 1.14.0)

**`check_lines.py --tree` cannot express a deliberately pre-fix red run.** R6.5 requires a guard to
have been observed failing, so a working doc's red-run record necessarily names the tree *before*
the fix. The evidence-provenance axis counts that as evidence "from ANOTHER tree" and returns exit
2, which `autorun` reads as "the gate does not close". Every ticket in this batch that records a red
run trips it — 8 of 8. Suggested shape: a marker the doc can carry (e.g. `Ran at <sha> (pre-fix)`)
that the checker counts on its own axis rather than as a stale tree. First seen: 176; seen in all
eight.

## Type-3 signal from 184 (2026-08-30, mango 1.14.0)

**`check_lines.py`'s `PLACEHOLDER_RE` cannot tell a template slot from a real angle-bracketed
identifier.** The pattern is `r"<[A-Za-z][A-Za-z0-9 _/+()-]*>|\.\.(?!\d)"`, and it matched `<LANG>`
inside `CA_<LANG>_CMD` — a genuine environment-variable convention this project documents at
`code_atlas/config.py:25`. The `RULE SECTIONS:` line was rejected as *"unfilled template placeholder
— the line was copied, not emitted"* when nothing had been copied and every count was correct. The
only workaround was to reword the prose around the identifier, which makes the doc worse to serve the
checker. Suggested shape: exempt a match that sits inside backticks, or require the placeholder to be
one of the tokens the templates actually ship. First seen: 184.

## A counted line is truncated at a nested backtick, and reported as a contradiction (022)

`check_lines.py`'s `find_emissions` reads a counted line out of a backticked span. A legitimate
markdown code span **inside** that line — `` `scan.js` `` in a `RULE SECTIONS:` reason — closes the
span early, so the body it hands to `parse_line` stops there. The line then fails its `text_rules`
with *"the count of sections enumerated on the line does not match `<n> applicable`"*: a
**contradiction** verdict for a line that is internally consistent and merely unread.

The same grammar asks for reasons rich enough to name a file (`§1 … `scan.js` parses …`), so the
collision is between two shipped expectations, not agent style. The diagnosis cost a debug harness
around `find_emissions` because the reported finding pointed at the count, not the truncation.

**Signal, not a fix** — this repo never edits a skill. A verdict distinguishing *truncated body* from
*contradicted count* would have named it immediately.

## A baseline is required to come from another tree, and the evidence guard refuses it for that (022)

`analysis` step 9 mandates a baseline captured **on the untouched checkout** — a different tree, by
definition. `check_lines`'s evidence guard refuses any empirical-output record whose `Ran at` SHA is
not the tree under review, with *"A green suite from a tree that is no longer the code satisfies
every gate above it; this evidence is REFUSED"* — and **exit 2, so the gate does not close**.

Both are right about their own case. A baseline written in the shipped `$ <command>` shape therefore
fails the run it was mandated by, and the only way out is to stop writing the baseline in that shape
— which costs the machine-checkable provenance the shape exists to give. 022 took that way out and
said so in the doc. 313 (2026-09-24) took the same way out.

**Signal, not a fix.** A record kind that says *this is the pre-change tree, and here is its SHA*
would let the guard check a baseline's provenance instead of refusing it.

## `work_doc_mode: embed` leaks the working doc into the diff the challenger reads (197)

The ticket-blind challenger is given *"only the re-fetched raw ticket + the diff"*, and `analysis`
step 2 keeps the guarantee by putting the working doc **below a separator line** in the same file
under `embed`, *"so the review phase can hand the challenger only the raw ticket without leaking the
design — preserving the challenger-blind guarantee in both modes."*

It does not preserve it. Under `embed`, the working doc lives **inside the ticket file**, and on any
ticket whose change touches its own ticket file — which is every ticket, because the phases are
written there — the working doc is **part of the diff**. On 197 the challenger self-disclosed that an
unscoped `grep` over `git diff` surfaced the cost ledger and the design rationale, including the
conclusion for a finding it was about to report. It flagged this rather than presenting a clean view,
and re-derived its verdicts independently — but the leak is structural, not a lapse.

The separator stops an honest reader from scrolling on. It cannot stop a grep, and `git diff` has no
notion of it.

**Second sighting, 199 — and the manual mitigation leaked too.** 196 and 199 both handed the
challenger an extracted raw ticket plus a diff with the working doc, `LESSONS.md` and
`TOKEN_LEDGER.md` filtered out, and told it not to read them. On 196 that held. On **199 it did
not**: the challenger's own independence statement reports it read `LESSONS.md` and
`TOKEN_LEDGER.md` anyway. Nothing enforced the instruction, because nothing could — the files are in
the checkout it is standing in. **A guarantee that depends on a prompt holding is not a guarantee**,
and hand-filtering shifts the failure from structural to silent: on 197 the leak was disclosed by
the leaking grep, here it was disclosed only because the agent volunteered it.

**Third sighting, 310 — the leak is now load-bearing enough to change a verdict.** The challenger
was told to read only above the separator. `git diff` on the ticket file returned the whole file,
including the self-graded AC table, and it said so up front. It then disagreed with one of those
gradings (AC6, which the doc under-claimed), which is the one outcome that shows the leak did not
simply capture it — but a guarantee that survives only because the reviewer chose to disagree is
still not a guarantee. Three sightings, three different failure shapes: structural leak (197),
silent prompt-mitigation failure (199), unavoidable whole-file diff (310).

**Signal, not a fix.** Options a maintainer might weigh: hand the challenger a diff with the ticket
file's below-separator hunks stripped; write the working doc to a separate path during review even
under `embed`; run the challenger against a checkout that does not contain the narrative docs at
all; or state plainly in the skill that `embed` and ticket-blindness are incompatible and let a
project choose. This repo cannot fix it — it never edits a skill.

## check_lines.py parses an enumerated tail from the line's last backtick (seen: 200)

A `RULE SECTIONS:` line enumerating eight sections failed the internal-contradiction rule
(*"the count of sections enumerated on the line does not match `<n> applicable`"*) while
`parse_line` on the same body returned `n=8, k=8, m=0` and `_count_sections` returned 8. The only
difference was a nested `` `contract.py` `` inside one section's `N/A (reason)`; removing the inner
backticks made the line pass. A counted line whose reason legitimately names a file cannot carry it
in code ticks. Type-3 signal only — no mango file was edited.

## A run contract has no path for a condition the code FALSIFIES after t0 (seen: 205)

`autorun`'s RUN CONTRACT is written before any work and only `UNBOUND ${…}` placeholders may be
bound later (Gate 2). But a condition can encode a **wrong requirement** that the code then
disproves: `MANIFEST-DROPS-PAGES` asserted `architecture_diff` should drop its `"pages"` key, and the
code showed the opposite is correct (the set is a strip-list). `DOCS-DROP-THE-PROMISE` was
mis-specified in the same pass — its predicate was the bare word `per-module`, which `impact_modules`
legitimately uses.

Leaving both in place would have reported `q = 2 BROKEN` at close on conditions that were never real
requirements — a false red a morning reader has to decode. Amending them silently would destroy the
t0 guarantee.

What this run did, for want of a named path: re-authored the contract from its spec, kept the
untouched original beside it as `.mango/run-contract-205.t0.txt`, and **observed both amended
conditions failing against `main` in a throwaway worktree** so the t0 guarantee held for them too.
That works, but it is invented per-run rather than mechanised. A named `amend` sub-command that
requires a recorded failing observation of the new predicate against the base ref would make it
auditable. Type-3 signal only — no mango file was edited.

## Nothing sequences the mutating reviewer against the main loop's suite run (seen: 208)

`review`'s brief asks the ticket-blind challenger to **mutate production code** to prove the guards
bite, and says so explicitly ("run it against the shape it forbids"). The main loop, meanwhile, is
expected to run `config.test_command` for the delta-green record. Both operate on the **same
working tree**, and nothing in the skill says they may not overlap.

In this ticket they overlapped twice. The first full suite returned `4 failed, 2775 passed` with
failures in four files that have nothing to do with the ticket's subject — a result whose only
honest use was to discard it; the second run was killed. The challenger's restores were byte-exact
both times, so nothing was corrupted, and the clean run afterwards was `2780 passed`. The cost was
two suite runs' wall time and a moment of believing four regressions existed.

The git-isolation principle already forbids a subagent from mutating **shared git state**; a
working-tree mutation is not git state, so it is permitted and correct — the gap is that the phase
gives the main loop no rule about running a suite while such a seat is live. A one-line ordering
constraint would close it: dispatch the mutating reviewer, or run the suite, never both at once —
or have the reviewer mutate inside its own worktree, which the env-parity section already discusses
for a different reason. Type-3 signal only — no mango file was edited.

## Second sighting: the backticked-N/A-reason bug in `check_lines.py` (seen: 200, 212)

The signal 200 filed fired again, identically. A `RULE SECTIONS:` line enumerating eight sections
failed the internal-contradiction rule while its counts were correct, because one section's
`N/A (reason)` legitimately named a module in code ticks. Removing the inner backticks made the line
pass unchanged otherwise.

Two sightings, one year apart in ticket numbers and one session apart in time, is the recurrence that
turns a curiosity into a fix worth making: the parser reads an enumerated tail from the line's last
backtick, so any reason that names a file cannot say so in the repo's own convention for naming
files. Type-3 signal only — no mango file was edited.

## The pre-PR self-check attests checks the verification sweep never ran (seen: 255, 251, 258)

Three branches in the 2026-09-12 merge round each ran a sweep over their own proving test file, then
filed a self-check reporting the repo-wide checks green. All three were wrong in a different place:
255/#332 merged with three suites red, 251/#336 shipped `docs/PLAN.md` over its ceiling with
`tests/test_doc_size_budget.py` claimed green, and 258/#337 shipped `mypy` red plus a red
`tests/test_build_report_counts.py`. Nothing downstream catches it — this repo's Actions report
`fail` in ~3 s without running, which `AGENTS.md` records — so the self-check is the only gate before
a human reads the diff.

**What the phase does.** `execute` step 5 records a verification sweep; the PR template's self-check
is then filled in from the ticket's own scope.

**A doable check the phase could name.** Have the sweep emit the *command it ran* beside its result,
and have the self-check accept only lines it can match to one — an unmatched claim renders as
`not run`, not as a tick. That is bookkeeping over what is already on the page, not new tooling.
Type-3 signal only — no mango file was edited. The repo-side half is `sweep-scope-cannot-attest-the-gate`
in [`LESSONS.md`](LESSONS.md).
