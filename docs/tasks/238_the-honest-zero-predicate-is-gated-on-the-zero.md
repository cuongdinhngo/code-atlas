---
id: 238
slug: the-honest-zero-predicate-is-gated-on-the-zero
title: '221''s cross-language predicate is language-only but its call site is gated on `total_count == 0`, so a `find_callers` answer with hits returns `reason: "ok"`, `truncated: false`, every row `RESOLVED` on a subject whose real callers are in an unmodelled crossing — the dangerous shape is the confident non-zero, and no carve-out covers it because nothing looks wrong'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [221, 222, 186, 223]
---

## Why this exists

Field round 15 — five bug tickets in the same PHP/SQL Server monolith, run as one overnight batch —
called `find_callers` on a PHP method whose consumers are `$.ajax` sites in inline `<script>` blocks.

```
find_callers("Src\…\MaintenanceIntegrityModel::checkExists")
  → total_count: 8, truncated: false, reason: "ok"
  → 1 production caller + 7 test callers, every row confidence_tier RESOLVED
  → no authoritative field, no caveat, no try_instead, no cross_language block
```

Ground truth by `grep`: **39 files** reference that endpoint, of which **9 are live call sites**
passing the table/column pair as string literals. The payload named 8 and called itself `ok`.

The same server's status payload, same session, same build:

```json
"cross_language": { "by_tier": {...all 0}, "linked": 0, "pairs": {}, "unlinked": 0 }
```

php 1 102 114 linked edges, sql 22 011, typescript 183 794 — and **zero edges between any pair**.
The predicate that would have caught this was computed, stamped and sitting in `meta`.

### Why 221 does not fire here

[221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) shipped the right
predicate. `cross_language_relation_unmodelled` (`coverage.py:69`) asks a purely *language* question
— does the index model any linked `*->L` pair into the subject's language — and **never looks at the
hit count.** Its call site does:

```
find_callers.py:307    if outcome.total_count == 0 and indexed and subject_file is not None:
find_callers.py:327    elif reason == REASON_NO_MATCHES and cross_lang_census is not None:
find_callers.py:369    if unlinked_calls == 0 and cross_lang_census is not None:
```

Three gates, all on the zero. `find_references` is narrower still — its whole honesty arm is behind
`reason == REASON_NO_MATCHES and nodes` (`find_references.py:209`) and it never consults the census
at all, so the sibling question inherits none of 221.

**The count and the crossing are independent facts.** An index that models no `*->php` edge cannot
measure PHP's cross-language callers *whether it found eight of them or none*. 221 read the
predicate as an explanation for a zero; it is actually a statement about the scope of the answer, and
scope does not become knowable because some in-language hits exist.

### The non-zero is the dangerous shape, not the zero

| | Round 14's shape | Round 15's shape |
|---|---|---|
| Payload | `total_count: 0, reason: "no_matches"` | `total_count: 8, reason: "ok", truncated: false` |
| Reader's response | suspicious → greps → finds the 5 | **reassured** → does not grep |
| Carve-out in the consumer's `CLAUDE.md` | **exists** ("bare EXEC never links… grep is primary for SQL callers") | **none** — it is scoped to SQL zeros, and says nothing about a PHP method called from JS |

221's own framing was *"a zero and an unmeasured are indistinguishable."* The round-15 finding is
strictly worse: **a partial and a whole are indistinguishable, and the partial presents as
authoritative.** Reviewer discipline cannot close it, because every discipline the field built
triggers on a zero.

**What it cost, concretely.** The consumer repo's review checklist mandates a symbol-index caller
sweep for a contract-changing signature edit — which is exactly what that ticket was. Taking
`total_count: 8, reason: "ok"` at face value would have reported *"1 production caller, updated"*:
complete and wrong, missing nine call sites, four of them posting a pair the allowlist rejects —
**which is the defect the five tickets were about.** The field agent found them only by grepping for
a string literal while chasing the bug. Their verdict: *"That is luck, not process."*

**And it is the same failure the code was fixing.** The previous engineer's tests asserted the
allowlist reached the database, `find_callers` said one caller, four phantom columns shipped.
**The tool agrees with the mistake.** The round's cost line: a second permanent carve-out in a
team-read `CLAUDE.md` — *"a non-zero `find_callers` result is not a complete caller set when the
callers may be JS in `.php` views."*

## Scope

1. **Ungate the predicate from the count.** Read `cross_language_relation_unmodelled` whenever the
   subject is indexed and `subject_file` is known — `find_callers.py:307` — not only at
   `total_count == 0`.
2. **On a non-zero answer, carry `authoritative: false`** with a new caveat
   (`cross_language_relation_unmodelled` already exists as a constant, `nav_result.py:560`) and the
   census block. `authoritative` is already in `CLAIM_CARRY` (`find_callers.py:62`), so the caveat
   reaches the signed `claim` line with no new plumbing.
3. **Leave `reason` alone on a non-zero.** `reason: "ok"` with `authoritative: false` is the honest
   pair; a hits-bearing answer is not `relation_unmodelled_for_language`, and overloading that
   string would blur the zero case 221 exists to name. The zero path stays byte-identical.
4. **Give `find_references` the same arm.** Same predicate, same subject-language question, and
   round 15 asked the tool that question about the same class (`find_references` on
   `MaintenanceIntegrityModel`) in the same session.
5. **Bound the envelope.** The census rides only when the predicate fires — an index with a modelled
   `*->L` pair, a single-language graph, or no stamp is unchanged (R5.6, 173). Measure the sample-tier
   delta and record it; **223's regression was exactly this shape** and CI floors only the fixture tier.

**Not in scope:** modelling any crossing ([222](222_the-cross-language-link-is-one-rule-target-away-from-machinery-that-exists.md));
extracting JS embedded in `.php` (see Notes — a `<script>` block is `T_INLINE_HTML` to the PHP parser
and invisible to the TS one, so **no** cross-language pair, modelled or not, would reach it); the
`symbol`/`qname` alias ask (Notes).

## Constraints

- **The decision this ticket overturns must be logged, not silently reversed.** 221/AC5 and 061/AC3
  say a confident answer stays byte-identical. This ticket deliberately narrows that: a hits-bearing
  answer changes *when and only when* the index cannot measure the crossing. That is a PLAN §19 row,
  and the reviewer should reject it if the exception is not written down as an exception.
- **No per-answer scan.** `_cross_language_edges` is a full-graph scan, ~3.2 s on the 2.19 M-edge
  anchor. Read `stamped_cross_language_edges()` only (221/AC3), and note it now runs on *every*
  answer rather than only the empty ones — one `meta` read, and the test must pin that.
- **Zero language branches in the core** (R1.1). The predicate is a language *name* comparison
  against stamped data, never `if language == "php"`.

## Acceptance criteria

- **AC1** On a fixture where the subject's language has in-language hits and no modelled `*->L`
  pair, `find_callers` returns the hits, `authoritative: false`, the census block, and the caveat on
  the signed `claim` line. **R6.5: prove the guard fails first** — the same test on today's code must
  show `reason: "ok"` with no `authoritative` key.
- **AC2** A subject whose crossing **is** modelled, and a single-language graph, are byte-identical
  to today at every detail level. The caveat must not become the default on every answer.
- **AC3** `reason` is unchanged on both arms: `"ok"` stays `"ok"` when there are hits;
  the `total_count == 0` path still returns `relation_unmodelled_for_language` exactly as 221 left it.
- **AC4** `find_references` proves the same three states with its own test.
- **AC5** An index built before the census stamp existed answers as it does today (R5.6/173).
- **AC6** The sample-tier tokens-to-answer ratio is measured before and after and reported in the
  ticket's ledger row; a regression is a stated cost, not an unnoticed one (223).

## Exclusions

- **E1** The field evidence is a private consumer repo. Reproduce the *shape* as a fixture — a symbol
  in language A with same-language callers, plus a second indexed language and an empty pair census
  (R2: the fixture encodes the crossing, never that repo's names).

## Notes

**The gap under the gap, recorded so it is not re-derived.** Round 15's real callers are JavaScript
inside `.php` view files. `.js` is indexed and `.php` is indexed, but a `<script>` block in a `.php`
file belongs to neither parser. So even a fully modelled `js->php` pair would still miss these nine
sites — **which is why this ticket is honesty, not coverage.** Embedded-language extraction is its own
ticket and a much larger one; the census caveat is what makes the current answer safe to read
meanwhile. Worth noting the census would also have to stay honest *after* 222-style linking lands,
since a modelled pair would then suppress the caveat on exactly the case it cannot see.

**Two cheap adjacent asks from the same round, not bundled here.** (1) Accept `symbol` as an alias
for `qname` and name the failing argument in the error rather than dumping pydantic — 2 wasted calls,
first thing the agent did. (2) `staleness` is repo-global, so an index one commit behind on unrelated
files refuses every query about files that did not change — 4 of the round's 6 non-productive calls,
and the reason the tool was unavailable from the moment coding started.

## References

- [221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) — the predicate, and the
  zero-case call site this ticket widens.
- [222](222_the-cross-language-link-is-one-rule-target-away-from-machinery-that-exists.md) — modelling
  the crossing; explicitly not this ticket.
- [223](223_the-envelope-bills-every-answer-and-no-gate-noticed-it-growing.md) — why AC6 exists.
- Field round 15 (2026-09-10), maintainer's local retro — §0.b, §14, §18, §19.
