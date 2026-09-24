---
id: 330
slug: impact-signs-a-zero-its-own-unlinked-sites-contradict
title: "impact signs 'nothing depends on this' for a method called only through a factory-built receiver — the unlinked same-name sites that find_callers and find_references already count never reach it"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [065, 272, 314]
---

## Why this exists (field retro, 2026-09-23 — FIELD-1621/1615 batch)

For a PR risk section the session asked `impact` on a base class's `display()` method, with
`sign=true`. It answered `answer == seeds` — a **modelled zero, signed**, with
`frontier_skipped_non_resolved: 0`. In fact the controller behind every chart page calls
`$instance->display()` on a receiver a class-map factory builds; the call is dynamic, so it is never
linked. The retro rated it 4/10: *"the signed zero is the most dangerous kind of answer for a PR
risk claim."*

**The honesty already exists, two tools over.** 272 made `find_references` report
`unlinked_same_name_sites` from `store.count_unlinked_by_target_raw` (`find_references.py:258,
552-558`), and `find_callers` counts `unlinked_calls` on its empty arm (`find_callers.py:231`, 272's
`:477`). `impact` consults neither: `CLAIM_CARRY` is `seeds_dropped` and
`frontier_skipped_non_resolved` (`impact.py:43`), and an unlinked edge is not in the frontier to be
skipped. Its docstring is accurate — *"resolver-linked IMPACT kinds only"* (`impact.py:170`) — but
a signed claim is read, not the docstring.

## Goal

An `impact` answer whose method seeds have unlinked same-name inbound sites says so, and does not
sign the empty frontier as authoritative.

## Scope / Deliverables

1. **Per method seed, count unlinked same-name sites** with the existing store query (272).
2. **Non-zero ⇒ disclose** the count and mark the answer `authoritative: false` with a named
   caveat; the signed `claim` carries the count rather than implying a closed zero.
3. **Route**, per 314: name `find_callers` on the seed / text search as the next step.

## Constraints

- **No new resolution** (272 C1) — typing factory receivers stays out of scope.
- **R6.7** — one count, from `count_unlinked_by_target_raw`; no second predicate.
- **061** — seeds with zero unlinked sites answer byte-identically, signed or not.
- **R4.2** — counts from stored rows only.

## Acceptance criteria

- **AC1** Fixture: a method whose only caller is `$f->make()->m()` (unlinked) → `impact` discloses
  one unlinked site and is not authoritative; red-arm on today's code.
- **AC2** The same call with `sign=true` does not emit a claim that reads as a closed zero.
- **AC3** A method with only resolved dependents is byte-identical (regression).

## References
`code_atlas/tools/impact.py:43,159-170`; `code_atlas/tools/find_references.py:258,552-558,589`;
`code_atlas/tools/find_callers.py:231`; `code_atlas/store.py:2099`; tickets 065, 272, 314.
