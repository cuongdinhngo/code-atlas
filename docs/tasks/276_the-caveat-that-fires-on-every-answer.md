---
id: 276
slug: the-caveat-that-fires-on-every-answer
title: '`cross_language_relation_unmodelled` is language-scope, so in a multi-language repo it decorates every caller and reference payload — including a 78-site, fully-correct, single-language answer — and `authoritative: false` therefore fires identically on the answer an agent should act on and the one that would mislead it: a flag that is always on cannot warn'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [221, 238, 243]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 20 §5)

Every `find_callers` and `find_references` payload in that session carried:

```json
"authoritative": false,
"authoritative_caveats": ["cross_language_relation_unmodelled"],
"caveat_limits": {"cross_language_relation_unmodelled": "This answer is reachability within one
  language's call graph and does not establish which entry point the front end invokes."}
```

…including the 78-site PHP→PHP answer that was completely correct and that the session acted on, and
the answer that was a false zero ([272](272_a-partition-that-is-all-tests-answers-ok.md)). Same flag,
same caveat, opposite trustworthiness.

The predicate is deliberate and 221/238 argued it: an unmeasured crossing is unmeasured whether or
not this answer found in-language hits (`coverage.py:71–94`). What that argument did not weigh is
**dynamic range**. In a repo indexing three languages with no `*->php` pair, the condition holds for
every subject in the repo, forever — so the field partitions nothing, and the retro's conclusion is
the one any reader reaches: *"read the reason code, not the flag."* A flag nobody reads is tokens on
every payload plus a lost warning on the payload that needed one.

The retro's own suggestion — suppress when `cross_language.linked + .unlinked == 0` — is one
comparison, and it is **not obviously right**: a census of zero is the case where *nothing* was
measured. That tension is what this ticket has to resolve rather than assume.

## Scope / Deliverables

- **Decide, with the evidence, what `authoritative: false` is for** — and record the verdict in
  §19. Either it discriminates (and a condition true of every subject in the repo must not raise it),
  or it is a standing property of a language's coverage (and it belongs on `get_index_status` and in
  the tool description, charged once, not on every answer).
- **Whichever way it goes, one repo-wide truth is stated once.** 243 already bounds the census on the
  status payload; a per-answer copy of a per-repo fact is R7.6 applied to payloads.
- **Keep the discriminating cases discriminating.** Where a `*->L` pair exists in the census and this
  subject's answer could genuinely have crossed, the caveat stays.
- Measure the cost: the caveat plus `caveat_limits` prose on every nav answer, at the session call
  counts the retros record.

## Constraints

- 221/238 are decisions; this reopens them only with the field evidence above, and the outcome is a
  §19 entry either way — including *"no change, and here is why the retro's read is wrong"*.
- R5.6 is not negotiable: nothing here may turn an unmeasured crossing into an implied zero. If the
  caveat moves off the answer, the answer must still not claim authority it lacks.
- No language branch (R1.1): the predicate stays keyed to the stamped census.

## Acceptance criteria

- A §19 entry naming the verdict and the evidence it was decided on.
- A test that pins the chosen behaviour on a three-language index with an empty `cross_language`
  census, and on one with a real `*->L` pair.
- If the caveat narrows: a regression test that an answer which *could* cross still carries it.
- The tool descriptions and `docs/design/payload.md` agree with the new rule in the same commit.

## References
`code_atlas/tools/coverage.py:71–94`, `code_atlas/tools/nav_result.py:652`,
`code_atlas/tools/find_callers.py:458`, `code_atlas/tools/find_references.py:292`,
field retro round 20 §5 / §9, [243](243_the-capability-predicate-221-relies-on-is-attached-at-verbose-only.md),
[272](272_a-partition-that-is-all-tests-answers-ok.md), PLAN §19 (221, 238).
