# Change Assurance adoption — field protocol (task 310)

**Frozen 2026-09-20, before week one, and deliberately before a cohort exists.** Every definition,
denominator, exclusion and verdict rule below is fixed now so that none of them can be chosen after
a number is seen. 309 paid for this rule: a bar ratified after its measurement existed is not a bar,
and the gap had to ship recorded rather than closed ([LESSONS](../LESSONS.md),
`delegation-is-not-ratification`).

**The window has not run.** This file is the instrument, not a result. What it does not contain is
any weekly record, any rate and any verdict — see *Status* at the bottom.

## 1 Cohort

A cohort member is one **team** — not one repository and not one person — that:

- uses an AI coding agent on its main repository as ordinary practice, and
- works a repository at or above the **size floor: 2,000 indexed files**, measured by
  `get_index_status` at week one and recorded, and
- has Change Assurance available for the whole window (`code-atlas-check` installed and an index
  built), with no product change landing during the counted weeks.

A team that loses availability mid-window is **excluded whole**, not partially: its weeks do not
enter either denominator, and the exclusion is recorded with its cause. Teams are identified in the
committed record by an opaque id (`team-1`, `team-2`). Nothing else about them is committed.

## 2 The two rates, and why they have separate denominators

They answer different questions and dividing them by the same number would hide which one failed.

| Rate | Numerator | Denominator |
|---|---|---|
| **Run rate** | code-changing PRs on which an assurance run was **attempted** | all code-changing PRs |
| **Evidence rate** | reviews whose artifact **contains or cites** an emitted claim, finding or bundle section | all reviews of code-changing PRs |

**Code-changing PR** — a PR whose diff touches at least one file with an indexed suffix
(`INDEXED_SUFFIXES` in the index meta). A docs-only or config-only PR is not code-changing and
enters neither denominator.

**Assurance run** — an invocation of `code-atlas-check` (or the MCP equivalent) against that PR's
head, whatever its exit status.

**Evidence used in review** — the review artifact quotes, links or restates an emitted claim,
finding or bundle section. **A tool invocation is not evidence use** (ticket constraint 2): a run
that nobody read counts in the run rate and not in the evidence rate. That asymmetry is the point.

## 3 Failed and invalid runs stay in the denominator

A run that errored, timed out or produced an operational reason (`snapshot_not_found`,
`base_not_resolved`, `capability_not_configured`) **remains in the run-rate numerator as an
attempt**, and is classified. Deleting it would reward unreliability — the product would score
better the more often it broke. Every failed or invalid run carries one classification, and a record
whose classification count does not equal its failed-plus-invalid count is **invalid**, not silently
accepted.

Classifications are a **closed set**, so recording one cannot smuggle in a name:
`operational` · `timeout` · `index_unavailable` · `config` · `crash` · `other`.

## 4 Exclusions, declared before collection

Three, and their codes are the only admissible values:

- `reverted_within_24h` — a PR reverted within 24 h; the review did not happen.
- `bot_authored_no_human_review` — a bot-authored PR nobody reviewed.
- `index_unavailable_over_one_day` — a team-week where the index was down more than one working day.

Anything else is **not** an exclusion. An exclusion invented mid-window makes the measurement
invalid rather than smaller.

## 5 Privacy boundary

Counts and question shapes only. **No repository name, source, qname or path enters the committed
record** (ticket constraint 1).

The guard is a **closed vocabulary, not a filter on suspicious-looking text**, and that choice was
forced: no pattern can tell the repository name `billing-service` from the English words it is made
of.

So the record admits a string in **exactly five places**, and nowhere else: `frozen_at`,
`cohort.teams[]`, `weeks[].failure_classifications[]`, `weeks[].exclusions[].reason` and
`removal_cost_probe.kind`. Four of the five are closed sets — teams are `team-1`, `team-2`;
classifications come from §3; exclusions from §4's three codes; the probe is `removal_comparison`
or `interview`. **A string anywhere else fails the count, including a free-text note**, because an
unpoliced field is precisely where a repository name arrives. A second check rejects
identifier-shaped strings — paths, source suffixes, `::` and backslash qnames, dotted qnames,
camelCase — as a net under the vocabulary, never as the mechanism.

The committed template carries no commentary for this reason; what it is for is stated here.

Provenance shas and build strings are required and are exempt: they name what answered, not whose
code it was. Transcripts and interview notes stay outside this tree, which is also why the probe
records only its kind.

## 6 Provenance, per week

Each weekly record names **host build, client build, server build, config build and repository
revision**. A `server_build` ending `+dirty` is recorded verbatim; see
[`field-retro.md`](field-retro.md) §0.a for why a dirty build's findings are not reproducible from a
commit id. A week missing any of the five is invalid.

## 7 Removal cost — the question an approval rating cannot answer

At least one of, recorded before the verdict is read:

- a **removal comparison**: assurance is deliberately unavailable for a bounded period and what the
  team did instead is recorded; or
- **interviews** at the end of the window: which decision changed, which evidence was ignored, and
  what they did when it was absent. The answers stay outside this tree (§5); the record carries
  only `interview`.

Approving of a capability in principle is not missing it. A record with no removal-cost probe is
**invalid** — not "must-have with a caveat".

## 8 The verdict, mechanically

The thresholds are the ticket's, fixed before this file existed: **run rate ≥ 0.80** and
**evidence rate ≥ 0.50**, both required.

| Condition, evaluated in order | Verdict |
|---|---|
| any validity rule in §9 fails | `measurement_invalid` |
| run ≥ 0.80 **and** evidence ≥ 0.50 | `must_have_observed` |
| run ≥ 0.80 **and** evidence < 0.50 | `useful_but_optional` |
| run < 0.80 | `adoption_failure` |

The asymmetric case is declared on purpose: **run < 0.80 with evidence ≥ 0.50 is still
`adoption_failure`**. A tool that a minority leans on heavily has not changed the team's review
behaviour, and reading that case as a success after seeing it is exactly the move pre-registration
exists to prevent.

## 9 Validity rules

1. Exactly four weekly records.
2. The declared aggregate reconciles **exactly** to the sum of the weeks — no rounding, no residual.
3. Both denominators are greater than zero.
4. Failed-plus-invalid runs equal the number of classifications.
5. A removal-cost probe is recorded (§7).
6. Every week carries all five provenance fields.
7. No identifying content (§5).

A violated rule names itself in the output. `measurement_invalid` is a real result and is reported
as one; it is not a reason to re-run until the number is better.

## 10 Running the count

```
.venv/bin/python scripts/change_assurance_tally.py docs/runbooks/change-assurance-tally.template.json
```

Local-only: it reads one committed JSON record and writes nothing but stdout. No telemetry, no
network, no provider analytics (ticket *Out of scope*). `--json` emits the same object it renders.

## Status — the window has not run, and this file cannot report one

Ticket 310 stays **blocked**. What is frozen: §§1–9 and the counter that applies them. What is
missing is the cohort: task [300](../tasks/300_the-index-is-registered-permitted-and-never-chosen.md)
closed 2026-09-19 with *full availability, zero uptake* at n = 3, and named the residual cause —
the client's deferred delivery and whether `Grep` hurts — as **not this repo's to change**. There is
no team cohort to observe, so **ACs 2, 3 and 4 and the Goal** are unmet and recorded unmet rather
than narrated closed. AC1, AC5 and AC6 are met: the rules are frozen, the verdict is mechanical, and
the epic and BACKLOG record `blocked` without a threshold moving. When a cohort exists, this protocol is already frozen and the first week can be counted
against it without anyone choosing a definition that day.
