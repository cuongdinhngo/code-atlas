---
id: 221
slug: a-zero-is-modelled-when-every-caller-is-in-another-language
title: '`find_callers` answers `reason=no_matches` on a stored proc with five live PHP callers, because 186''s predicate asks whether the relation is unmodelled *for the subject''s own language* and never whether the index models the crossing at all — `cross_language.linked: 0` in the same server''s status payload is the predicate it needed'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [214, 204, 186, 160]
---

## Why this exists

Field round 14, in a PHP-over-T-SQL repo, called `find_callers` on two stored procedures in one
session. **The same tool, the same zero, two different reasons — and only one of them was honest.**

| Subject | Real callers (grep) | `reason` returned | Honest? |
|---|---:|---|---|
| `dbo.MemberStatisticsList` — callers are SQL-side bare `EXEC` | 8 | `relation_unmodelled_for_language` + `try_instead_hint` | **yes** |
| `dbo.getUnplannedChange` — callers are **PHP** `querySP('name')` | **5** | **`no_matches`** | **no** |

The second is a **modelled zero**: a confident claim that no caller exists, on a proc whose callers
include the very model the field agent's own PR was modifying. Their words: *"Had I quoted that zero
into either PR body, I would have shipped a false claim to a tech-lead review."*

**Why the honest string does not fire.** `find_callers.py:298` upgrades `no_matches` only when
`unlinked_calls > 0` — `count_unlinked_by_target_raw((lookup, subject_name))`. A SQL-side `EXEC X`
leaves an unlinked edge whose `target_raw` **is** the proc name, so 214's path catches it. A PHP
`querySP('getUnplannedChange')` leaves an edge whose `target_raw` is **`querySP`**; the proc
name is an *argument*, not a target. Nothing matches, so the zero stays `no_matches`. 186's
`relation_unmodelled_for_language` cannot help either: it asks `store.language_emits_none_of(language
of the subject's file, CALLER_KINDS)`, and T-SQL emits plenty of CALLS — just none that reach PHP.

**The index already knows.** 204 shipped `_cross_language_edges` (`store.py:772`), and on this corpus
it reads:

```
cross_language: { RESOLVED: 0, HEURISTIC: 0, DYNAMIC: 0, linked: 0, pairs: {} }
```

in a repo whose entire data layer is PHP calling T-SQL by name. **That row explains every structural
miss the round recorded, and it is published only at `detail_level: verbose` on `get_index_status` —
a call nobody makes during work — and never in the answers it invalidates.**

**The reputational cost is already paid and is measurable.** The consumer repo's committed
`CLAUDE.md`, loaded by every agent on that team, carries a permanent carve-out — *"code-atlas SQL:
bare EXEC never links… grep is primary for SQL callers/writers"* — and the field agent's project
memory carries a second. Those exist **only because a zero and an unmeasured are indistinguishable**.
One `reason` string retires them.

## Scope

1. **Widen the honest-zero predicate to the cross-language case.** When `total_count == 0`, the
   subject is indexed, and the index models **no linked edge from any other language into the
   subject's language**, the answer is not authoritative: return
   `reason=relation_unmodelled_for_language` (or a sibling name if the reviewer prefers the two cases
   distinguishable) plus the `try_instead_hint`, not `no_matches`.
2. **Read the predicate from a build-time stamp, never per answer.** `_cross_language_edges` is a
   full-graph scan — its own docstring records **~3.2 s on the 2.19 M-edge anchor, "one scan per
   build, never per answer"**. Persist the pair census in `meta` beside `COVERED_LANGUAGES_KEY` /
   `COVERED_SUFFIXES_KEY` (`store.py:46-47`) and read that. A per-answer scan is an automatic
   rejection.
3. **Carry `authoritative: false`.** `find_callers` already imports `attach_authoritative_caveats`
   and lists `authoritative` in `CLAIM_CARRY` (`find_callers.py:54`), but only the
   sibling-definitions path sets it (`:325`). This case is the same class of partition and must mark
   itself the same way, so the caveat reaches the signed `claim` line.
4. **Say it where it is read.** The census belongs on the answer it invalidates, not only in
   `verbose` status. Follow 160/173's discipline: the note rides a **low-confidence answer only**, so
   a confident answer stays byte-identical (061/AC3) — this ticket must not add a field to answers
   that have hits.

**Not in scope:** modelling the crossing (that is [222](222_the-cross-language-link-is-one-rule-target-away-from-machinery-that-exists.md));
the `ambiguous_definitions` explanation gap (Notes); changing 214's SQL-side path, which works.

## Acceptance criteria

- **AC1** On a fixture with PHP calling a T-SQL proc through a string argument, `find_callers` on
  that proc returns a non-`no_matches` reason with `authoritative: false`, and the reason reaches the
  signed `claim` line. **R6.5: prove the guard fails first** — the same test on today's code must
  show `no_matches`.
- **AC2** A subject whose language pair **is** modelled and genuinely has no callers still returns
  `no_matches`. Widening the honest zero must not make every zero unmeasured; that would retire the
  distinction 065/186 exist to draw.
- **AC3** The predicate costs no per-answer scan: pinned by a test asserting the census is read from
  `meta`, and that answering does not execute the `_cross_language_edges` query.
- **AC4** An index built before this stamp existed answers as it does today rather than guessing —
  silence is not evidence (R5.6), the rule 173 already applies to `covered_languages`.
- **AC5** A confident answer (hits > 0) is byte-identical to before the change (061/AC3).

## Exclusions

- **E1** The field evidence comes from a private consumer repo. Reproduce the shape as a fixture in
  `tests/`; do not make an anchor-only claim (R2 — the fixture encodes the *language crossing*, not
  that repo's `querySP`).

## Notes

**The neighbouring gap, deliberately left out of scope but recorded here so it is not re-derived.**
Both subjects came back with `ambiguous_definitions` naming two files — the DDL export and an 8.3 MB
schema-baseline migration that declares 328 of 452 procs a second time. That is what kills 214's
unique-match arm on that corpus, and it is the consumer repo's `.codeatlasignore` gap, not a
code-atlas defect. **But nothing in any payload connects `ambiguous_definitions` to "and that is why
your `EXEC` did not resolve."** The field agent found it only by running a retro. Worth its own
ticket; it is not this one.
