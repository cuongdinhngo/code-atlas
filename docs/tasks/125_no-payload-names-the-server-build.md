---
id: 125
slug: no-payload-names-the-server-build
title: 'No payload on any of the 17 tools names the server build — every field retro has to be told its own subject by an operator'
phase: 1.5b
milestone: Measure
status: todo
depends_on: [082, 095, 100]
---

## Why this exists (field retro round 6, 2026-08-21)

Round 5's retro protocol asks the evaluator to confirm that the server process is the version under
evaluation *at the start and at the end of the session*. Round 6 could not answer it:

> "I cannot answer that from outside the tool. No payload on any of the 17 tools carries a server
> version or a code-atlas commit."

`get_index_status` — the tool whose entire job is *"what state am I in"* — carries
`contract_version: "5"` and `schema_version: "4"` (`get_index_status.py:187-188`). Both describe the
**index schema**, both have been unchanged since task 063, and neither can discriminate between round
5's build and round 6's. The `head_commit` it reports is the **indexed repository's** commit, not the
server's.

**How the evaluator actually identified the build:** by reading task numbers out of prose in the tools'
own `description` fields — `impact` cites 102, `search_symbol` cites 101, `get_index_status` cites
100/095/092 — and comparing them against round 5's "all tickets through 082". A ~20-task delta,
inferred from documentation strings. That is not a version API.

The version exists and is simply never surfaced: `pyproject.toml:7` holds `version = "0.1.0"`.

## Why this is a Measure ticket and not a nicety

The project's evaluation loop is its most valuable instrument — [PLAN §19](../PLAN.md#19-project-context--decision-log)
records that the founding *search speed* premise was **false**, and that was only discoverable because
the work is measured. Six field rounds now attribute findings, regression verdicts and "FIXED /
NOT FIXED" statuses to a build **identified by an operator's word**. Every one of those verdicts rests
on an unverifiable premise about which code answered.

This is the same defect class as [082](082_claims-nobody-outside-can-check.md) — a claim nobody outside
the session can check — applied to the identity of the answerer rather than to the answer.
[100](100_claim-signing-output-mode.md) built a quotable `claim` line naming subject, question, answer
and the revision the index describes. It names the revision of the **repo**. It cannot name the
revision of the **server** that produced it, so a signed claim is not reproducible by a third party who
has a different build.

## Scope

- **Report the server build on `get_index_status`** — the package version plus a build identifier
  precise enough to distinguish two commits of the same version. Additive field, per 061's
  omit-when-absent discipline.
- **Decide, and record, how the identifier is obtained when the server runs from an installed wheel
  rather than a git checkout.** A field that is present in development and silently absent in the
  shipped container would make the retro protocol worse, not better — it would look answered.
- **Carry it into 100's `claim` line**, so a quoted claim identifies both the indexed revision and the
  build that read it. That is what makes a claim checkable by someone else.
- **Keep it out of the default cheap path** if it costs anything measurable: `minimal` exists to be
  ~100 tokens (066's clarification 3), and this field belongs with the other provenance fields.

### Explicitly not in scope

Versioning the *contract* or the *schema* — those exist, are correct, and mean something different
(R3). This ticket adds a third, orthogonal identity: which code is running.

## Acceptance criteria

1. **AC1.** `get_index_status` reports the server's version and a build identifier; two builds of the
   same declared version are distinguishable from the payload alone.
2. **AC2.** The field is present when the server runs from the shipped container
   (`docker/Dockerfile.runtime`), not only from a git checkout — proven by an assertion that runs in
   that image, since a dev-only field is the failure mode this ticket is preventing.
3. **AC3.** `minimal` detail level's payload size is unchanged, or the increase is measured and stated.
4. **AC4.** 100's `claim` line carries the server identity alongside the index revision, and a test
   asserts a claim quoted from two different builds is textually distinguishable.
5. **AC5.** Determinism holds (R4.2): the identifier is derived from the installed artifact, never from
   a timestamp or a build clock, so identical input yields identical output.
6. **AC6.** The retro protocol's §0.a question is answerable from one call, and that is recorded in the
   evaluation harness docs so round 7 does not have to ask an operator.
