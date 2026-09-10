---
id: 238
slug: the-honest-zero-predicate-is-gated-on-the-zero
title: '221''s cross-language predicate is language-only but its call site is gated on `total_count == 0`, so a `find_callers` answer with hits returns `reason: "ok"`, `truncated: false`, every row `RESOLVED` on a subject whose real callers are in an unmodelled crossing — the dangerous shape is the confident non-zero, and no carve-out covers it because nothing looks wrong'
phase: 1.5b
milestone: Agent-trust
status: done
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 238 — The honest-zero predicate is gated on the zero (working doc)

- **Ticket:** 238 · local file `docs/tasks/238_the-honest-zero-predicate-is-gated-on-the-zero.md`
- **Type:** bug
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/0 touched files under UI paths
- **TIER:** full
- **BASELINE:** green — related suite 42 passed on untouched HEAD; no baseline exclusions

## Session status

- **Last updated:** 2026-09-10
- **Current phase:** finalise
- **Next action:** push feature branch + open PR (handover-authorised); merge not authorised
- **Blocked on:** none
- **work_doc_mode:** embed
- Run: `/mango:autorun 238` with `--no-reviewer`; challenger ON.
- Branch: `fix/238-the-honest-zero-predicate-is-gated-on-the-zero`
- Contract: `.mango/run-contract-238.txt` bound at Gate 2
- Product SHA: `15893963d914b052187a7544d74a378e39ba3d5d`

---

## Phase 0 — Refine

`PREMISE: 16 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 5 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions

**PREMISE detail.** Present: `code_atlas/tools/coverage.py` (`cross_language_relation_unmodelled` @69), `code_atlas/tools/find_callers.py` (gates @307/327/369, `CLAIM_CARRY` @62), `code_atlas/tools/find_references.py` (@209), `code_atlas/tools/nav_result.py` (`CAVEAT_CROSS_LANGUAGE_UNMODELLED` @560), `stamped_cross_language_edges` / `_cross_language_edges` in `code_atlas/store.py`, `REASON_NO_MATCHES`, PLAN.md §19, tasks 221/222/223/186. **Ambiguous (surfaced, not blocking):** `MaintenanceIntegrityModel` and the consumer `CLAUDE.md` — private field evidence, declared synthetic by E1.

**INPUT KIND:** ticket (not epic).

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | 192-C1 `gate-the-disclosure-on-its-condition-not-the-row-count` | 2 | handle | Yes — census gated on `total_count == 0` |
| 2 | 196-C1 `gate-on-the-invariant-not-on-presence` | 2 | handle | Yes — hits-present still cannot measure `*->L` |
| 3 | `prove-the-guard-fails` | 2 | handle | Yes — AC1 R6.5 red-before |
| 4 | 221-C1 `cross-language-zero-needs-the-crossing-census` | 2 | handle | Yes — this ticket widens that census off the zero |
| 5 | 165-C1 `disclose-a-partition-as-a-partition` | 2 | handle | Yes — `authoritative: false` on a partial caller set |

**Exposure-checker:** skipped (refine skip: yes).

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope · Constraints · Acceptance criteria · Exclusions) | 5 decomposed | ROWS: C=3 R=6 G=1 AC=6`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why this exists | a hits-bearing `find_callers` answer on an unmeasurable crossing presents as `ok` | The dangerous shape is the confident non-zero, not the zero 221 named | `find_callers.py:307` gates the census on `total_count == 0` | D1, D2 | proving test `:323-344` + `find_callers.py:311-316,376-379` | ✅ |
| C1 | Constraints | The decision this ticket overturns must be logged, not silently reversed | PLAN §19 row: hits-bearing answers change iff the index cannot measure the crossing | 221/AC5 + 061 omit-when-empty | D7 | `docs/PLAN.md:1009-1013` + table cell `:501` | ✅ |
| C2 | Constraints | No per-answer scan; read `stamped_cross_language_edges()` only | Predicate already does this; now runs on every indexed answer with a subject file | `coverage.py:83`; `_cross_language_edges` stays build-time | D1, D6 | `test_the_hit_answer_is_a_stamp_read_not_a_scan` `:399-422` | ✅ |
| C3 | Constraints | Zero language branches in the core (R1.1) | Predicate compares stamped language names, never `if language == "php"` | `coverage.py:80-92` | D1 | `coverage.py:78-91` (challenger) | ✅ |
| R1 | Scope 1 | Ungate the predicate from the count whenever indexed and `subject_file` is known | Drop `total_count == 0 and` at `find_callers.py:307` | `find_callers.py:307` | D1 | `find_callers.py:311-316` | ✅ |
| R2 | Scope 2 | On a non-zero answer, carry `authoritative: false` + caveat + census; `authoritative` already in `CLAIM_CARRY` | Attach whenever census is not None, including hits; `reason` stays `ok` | `find_callers.py:62,369-371` | D2 | `find_callers.py:376-379` + proving test | ✅ |
| R3 | Scope 3 | Leave `reason` alone on a non-zero; zero path stays byte-identical to 221 | Do not reuse `relation_unmodelled_for_language` on a hits-bearing answer | ticket Scope 3 | D1, D2 | `test_zero_path_reason_is_unchanged` `:375-380`; proving `reason==ok` | ✅ |
| R4 | Scope 4 | Give `find_references` the same arm | Same predicate, same attach; zeros keep today's reason (deviation vs 221 rewrite) | `find_references.py:209` never consults the census | D3 | `find_references.py:190-194,261-263` + AC4 tests | ✅ |
| R5 | Scope 5 | Bound the envelope: census rides only when the predicate fires; measure sample-tier delta | Modelled `*->L`, single-language, or no stamp unchanged; AC6 records cost | ticket Scope 5 / 223 | D1, D8 | AC2 tests + sample-tier 67.376→67.376 | ✅ |
| R6 | Exclusions E1 | Reproduce the *shape* as a fixture, never the consumer repo's names (R2) | Language A subject with in-language callers + second language + empty pair census | E1 / R2.2 | D4, D5 | `_hits_unmodelled_repo` `:260-320` `A\\Widget::ping` | ✅ |
| AC1 | AC | hits + no `*->L` → hits, `authoritative: false`, census, caveat on `claim`; R6.5 red-before | Proving test | today's `reason: ok` with no `authoritative` | D4 | `test_in_language_hits_on_an_unmodelled_crossing_are_not_authoritative`; red `KeyError: 'authoritative'` | ✅ |
| AC2 | AC | modelled crossing, and a single-language graph, byte-identical at every detail level | Caveat must not become the default | 221 AC2 fixtures reuse | D4 | `test_modelled_crossing_hits_stay_byte_identical`; `test_single_language_hits_stay_byte_identical` | ✅ |
| AC3 | AC | `reason` unchanged on both arms: `ok` stays `ok` with hits; zero path still 221's string | | ticket AC3 | D4 | proving `reason==ok`; `test_zero_path_reason_is_unchanged` | ✅ |
| AC4 | AC | `find_references` proves the same three states with its own test | | no census import today | D5 | `test_find_references_in_language_hits_on_an_unmodelled_crossing`; `test_find_references_modelled_and_single_language_and_pre_stamp` | ✅ |
| AC5 | AC | Pre-census-stamp index answers as today (R5.6/173) | `stamped_cross_language_edges()` is None → no attach | 221 `_drop_census` | D4, D5 | `test_pre_stamp_hits_say_nothing`; find_references prestamp branch | ✅ |
| AC6 | AC | Sample-tier tokens-to-answer measured before and after; regression is a stated cost | Not a pass/fail floor | `scripts/tokens_to_answer.py --samples` | D8 | 67.376 → 67.376 (delta 0); ledger row 238 | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | hits + `authoritative: false` + census + caveat on `claim`; today's code `ok` with no `authoritative` | Confirmed: `find_callers.py:307` skips census when `total_count != 0` | Y | greppable payload keys | — |
| AC2 | modelled `*->L` and single-language byte-identical | Predicate returns None in both cases (`coverage.py:88-92`) | Y | dict equality vs stamp-deleted | — |
| AC3 | `ok` stays `ok` on hits; zero still `relation_unmodelled_for_language` | Scope 3 forbids overloading the 221 string on hits | Y | `payload["reason"]` | — |
| AC4 | find_references same three states | `find_references.py` has no census call | Y | own tests | — |
| AC5 | pre-stamp unchanged | reader returns None when nested `cross_language` absent (`store.py:893-901`) | Y | `_drop_census` control | — |
| AC6 | sample-tier before/after reported | 223 floors only fixture tier; sample is the product claim | Y | two numbers in the ledger row | — |

## Inventory (universal "all/every/no")

- **Denominator / total N:** 2
- The two tools that must grow the arm:
  1. `find_callers`
  2. `find_references`

| # | Item | Ph3/4 proven by (`path:line` / test) | Status ✅/⚠/❌ |
|---|------|--------------------------------------|----------------|
| 1 | find_callers | `find_callers.py:311-316,376-379` + proving test | ✅ |
| 2 | find_references | `find_references.py:190-194,261-263` + AC4 tests | ✅ |

## Clarifications

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

- Self-resolved (with citation):
  1. 221's `test_a_confident_answer_is_byte_identical` seeds a *linked* `php->sql` edge, so the crossing **is** modelled — it remains AC2's control, not the test AC1 reddens. Cite `tests/test_find_callers_cross_language_unmodelled.py:242-256`.
  2. `find_references` never received 221's arm. "Same arm" (Scope 4) = compute the census whenever indexed+`subject_file`, attach on any non-None, rewrite `reason` only on a zero that is still `no_matches` (221's naming), leave `ok` on hits (AC3). Cite ticket Scope 3–4.
  3. AC6 is a recorded cost, not a CI floor — 223 already gates the fixture tier. Cite ticket AC6 / 223.
- For human decision: none

---

## Phase 1 — Analysis

- Root cause (bug, `logic`): `cross_language_relation_unmodelled` is a language-scope fact (`coverage.py:69-93`) and never looks at hit count; `find_callers.py:307` still requires `total_count == 0` before reading it, so a partial in-language set presents as `reason=ok` with no caveat. `find_references.py:209` never consults the census at all.
- Handler / entry point + blast radius: `find_callers.create` / `find_references.create`; consumers of `authoritative` via `CLAIM_CARRY`; 221 test module; PLAN §19; sample-tier envelope when the predicate fires. `test_relation_unmodelled_for_language.py:225` is include_graph 186 — out of blast radius.
- `TRACK: backend — 0/0 touched files under UI paths`
- `SCOPE: M`
- `TIER: full`

`RULE SECTIONS: 9 applicable — 8 by change-type | 1 by recalled handle — R1.1 (change-type) ✅ predicate compares stamped language names never if language == php · R1.4 (change-type) ✅ tools present; store owns the stamp · R2.2 (change-type) ✅ fixture encodes the crossing not consumer names · R3 (change-type) ✅ reason string reused no contract bump · R5.5 (change-type) ✅ census sourced from the language-scope stamp not the hit count · R5.6 (change-type) ✅ pre-stamp indexes say nothing · R6.1 (change-type) ✅ fixture tests for both tools · R7.6 (change-type) ✅ PLAN §19 exception prunes the 221/AC5 confident-hit claim · R6.5 (recalled handle) ✅ AC1 red-before on today's ok-without-authoritative`

### BASELINE

Related suite on untouched code:

```
Ran at 627a3b5f3a5ec1157ab5bb7e559606347260b118
$ .venv/bin/python -m pytest tests/test_find_callers_cross_language_unmodelled.py tests/test_find_references_twins.py tests/test_relation_unmodelled_for_language.py tests/test_references_construct_agreement.py tests/test_claim_signing.py -q --tb=line
..........................................                               [100%]
42 passed in 5.02s
```

`BASELINE: green` for the change-adjacent suite. Full-suite delta-green at execute (AGENTS.md expected 3,222 on Linux with adapters). No baseline exclusions.

- Self-audit: sections 5=5; AC table falsifiable; j=0; RULE SECTIONS named not bare ticks; TRACK/TIER/SCOPE declared; recall injected nothing.
- **Gate 1 status:** cleared (autorun closes on artifacts)

---

## Phase 2 — Design

- **Approach.** Drop the `total_count == 0` conjunct so `cross_language_relation_unmodelled` runs whenever the subject is indexed and `subject_file` is known. When the census is not None, `attach_cross_language_census` + `attach_authoritative_caveats([CAVEAT_CROSS_LANGUAGE_UNMODELLED])` on every such answer; `reason` stays `ok` on hits. The existing 221 zero rewrite (`reason=relation_unmodelled_for_language` + try_instead) is untouched. Mirror that arm in `find_references` (it currently has no census import): attach on any non-None census, and on a zero still sitting at `no_matches` apply 221's reason+hint. Reuse 221's fixture helpers; add a fixture with in-language hits, a second indexed language, and an empty pair census (R2/E1). Log the 221/AC5 narrowing as a PLAN §19 exception and prune the "hit answers stay untouched" wording in that test's docstring plus the `find_callers` tool table cell. Measure sample-tier `--samples` before/after.

- **Rejected alternatives.**
  1. Overload `reason=relation_unmodelled_for_language` on hits — rejected: ticket Scope 3; blurs the zero 221 exists to name.
  2. New caveat string — rejected: `CAVEAT_CROSS_LANGUAGE_UNMODELLED` already exists (`nav_result.py:560`); a second name is R1.8 drift.
  3. Per-answer `_cross_language_edges` — rejected: ticket C2 / 221/AC3 (~3.2 s scan).

**Assumptions**

| Assumption | verified / novel-untested | If novel-untested 3p/runtime → spike or integration-shaped proving test |
|------------|---------------------------|--------------------------------------------------------------------------------|
| `stamped_cross_language_edges()` is a meta read, not the GROUP BY scan | verified — 221 `test_the_predicate_is_a_stamp_read_not_a_scan`; re-pin on a hit answer | — |
| `attach_authoritative_caveats` unions caveats when siblings/DYNAMIC also fire | verified — `nav_result.py:669-676` `sorted(set(caveats))` | — |
| Predicate already returns None for modelled `*->L`, single-language, and missing stamp | verified — `coverage.py:83-92` | — |

**Smallest change-list**

| Change | File/area | Blast radius (side-effect surface) | Ph2 covered by | k/N |
|--------|-----------|------------------------------------|----------------|-----|
| Ungate census read (drop `total_count == 0 and`); attach census+caveat whenever census is not None; keep 221 zero reason rewrite | `code_atlas/tools/find_callers.py` | MCP docstring (clients read it); envelope when predicate fires; 221 tests | G1, R1, R2, R3, C2, C3 | 6/6 |
| Same arm: import predicate + `attach_cross_language_census`; compute when indexed+subject_file; attach; zero still-`no_matches` → 221 reason+hint | `code_atlas/tools/find_references.py` | MCP docstring; `CLAIM_CARRY` already has `authoritative`; DYNAMIC/sibling caveats union | R4, AC4 | 2/2 |
| Docstring: the predicate is a language-scope fact, not a zero-only explainer | `code_atlas/tools/coverage.py` | callers of the predicate (the two tools above) | R1 | 1/1 |
| AC1 proving test (in-language hits, second language, empty pairs) + R6.5 red-before; keep 221 zeros; retitle AC5 docstring (modelled-crossing hits stay identical); pin stamp-read on a hit answer | `tests/test_find_callers_cross_language_unmodelled.py` | `test_a_confident_answer_is_byte_identical` stays the AC2 modelled-hit control | AC1, AC2, AC3, AC5, C2, R6 | 6/6 |
| AC4: same three states for `find_references` on the shared fixture helpers | same test module (own test functions) | none identified beyond the new tests | AC4, AC5 | 2/2 |
| Tool descriptions name delivered honesty (unmodelled `*->L` ⇒ `authoritative:false` even with hits) | `find_callers.py` / `find_references.py` docstrings | MCP client LLM | R2, R4 | 2/2 |
| PLAN §19 exception (221/AC5 narrowed); prune the `find_callers` table cell that currently omits this | `docs/PLAN.md` | R7.6 — add by replacing the stale "hits stay untouched" implication | C1, R7.6 | 2/2 |
| Record sample-tier `--samples` before/after in the ticket ledger row | execute empirical output + `docs/TOKEN_LEDGER.md` at finalise | fixture-tier CI floor unchanged (223) | AC6, R5 | 2/2 |

**Recalled type-2 handles**

| # | Handle (class slug) | Answer: traced (command + output) / `does not apply because <reason>` |
|---|---------------------|----------------------------------------------------------------------|
| 1 | `gate-the-disclosure-on-its-condition-not-the-row-count` | traced — `rg -n "total_count == 0 and indexed" code_atlas/tools/find_callers.py code_atlas/tools/find_references.py` → `find_callers.py:307: if outcome.total_count == 0 and indexed and subject_file is not None:` (the conjunct D1 drops). Folded as D1. |
| 2 | `gate-on-the-invariant-not-on-presence` | traced — same command; hits-present still cannot measure `*->L`. Folded as D1/D2. |
| 3 | `prove-the-guard-fails` | traced — AC1 requires today's `reason=ok` with no `authoritative`; proving test asserts that red-before. Folded as D4. |
| 4 | `cross-language-zero-needs-the-crossing-census` | traced — `rg -n "cross_language_relation_unmodelled\(" code_atlas tests --glob '*.py'` → def `coverage.py:69` and sole call `find_callers.py:310`. Folded as D1/D3 (second call site). |
| 5 | `disclose-a-partition-as-a-partition` | traced — `rg -n "CLAIM_CARRY" code_atlas/tools/find_callers.py code_atlas/tools/find_references.py` → both already carry `authoritative`. Folded as D2 (no new plumbing). |

`HANDLES: 5 recalled | 5 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- Rule compliance: R1.1/R1.4/R2.2/R3/R5.5/R5.6/R6.1/R6.5/R7.6 as RULE SECTIONS. No contract bump. No `_cross_language_edges` on the answer path.
- **Proving test** (fails pre-change, passes post-change): `pytest tests/test_find_callers_cross_language_unmodelled.py::test_in_language_hits_on_an_unmodelled_crossing_are_not_authoritative -q`

**Verification plan**

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|------------|----------------|--------------------|--------------|
| AC1 | logic | unit | n/a | ✅ |
| AC2 | logic | unit | n/a | ✅ |
| AC3 | logic | unit | n/a | ✅ |
| AC4 | logic | unit | n/a | ✅ |
| AC5 | logic | unit | n/a | ✅ |
| AC6 | integration | integration | n/a | ✅ |

No real corpus configured (`config.real_corpus_path` is null). AC1–AC5 expected keys are writable before running (not input-shape-dependent). AC6 is "two numbers appear in the ledger", not a heuristic over corpus shape.

**Coverage-gap exclusions**

| Item | Risk tier | Why deferred | Follow-up | Expiry | Seen |
|------|-----------|--------------|-----------|--------|------|
| *(none)* | | | | | |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- Rollback: revert the branch. Porting: n/a (single repo).
- SCOPE confirmed: M
- **Gate 2 status:** cleared (autorun closes on artifacts)

## Decision log

| When | Decision | Why |
|------|----------|-----|
| t0 | reviewer off, challenger on | `/autorun 238 with skipped reviewer` |
| refine | skip: yes | ticket locks the five scope items, reason policy, and fixture shape |
| analysis | j = 0 | three clarifications cited, none WANT |
| design | reuse existing caveat constant; do not change `reason` on hits | ticket Scope 2–3 |

## Phase 3 — Execute

- **Branch:** `fix/238-the-honest-zero-predicate-is-gated-on-the-zero`
- **Commits:** `15893963d914b052187a7544d74a378e39ba3d5d` (`fix(238): treat an unmodelled crossing as a partition even when there are hits`)
- **Proving test added:** `tests/test_find_callers_cross_language_unmodelled.py::test_in_language_hits_on_an_unmodelled_crossing_are_not_authoritative`

- **Verification sweep — BOTH axes.**
  - File axis: zero stray references ✅ · diff ⊆ approved list ✅ (6 files: `find_callers.py`, `find_references.py`, `coverage.py`, the 221 test module, `PLAN.md`, this ticket) · each hunk maps to a row ✅
  - Behaviour axis: ungating + attach-on-hits implemented-as-approved; find_references zeros **deviated** (no 221 reason rewrite — AC3/AC4 three states are hits / modelled+single-lang / reason-unchanged, not a new zero reason)

- **Design-conformance deviations**

  | Approved Gate-2 bullet | What was implemented instead | `path:line` | Surfaced to review |
  |------------------------|------------------------------|-------------|--------------------|
  | find_references: on a zero still `no_matches`, apply 221's reason+hint | Hits-only attach (`total_count > 0`); zeros keep today's reason so AC3 stays byte-identical | `find_references.py` census attach | yes |
  | PLAN §19 prune the table cell only | Also compacted the T-SQL retro tail and 219's E1 sentence to stay under PLAN's 23,150 token ceiling (R7.6) | `docs/PLAN.md` | yes |

- **Empirical output**

R6.5 red-before (production ungate stashed):

```
Ran at 627a3b5f3a5ec1157ab5bb7e559606347260b118 (production files reverted; proving test present)
$ .venv/bin/python -m pytest tests/test_find_callers_cross_language_unmodelled.py::test_in_language_hits_on_an_unmodelled_crossing_are_not_authoritative -q --tb=line
FAILED ... KeyError: 'authoritative'
1 failed in 1.38s
```

Post-change related suite:

```
Ran at 15893963d914b052187a7544d74a378e39ba3d5d
$ .venv/bin/python -m pytest tests/test_find_callers_cross_language_unmodelled.py tests/test_find_references_twins.py tests/test_relation_unmodelled_for_language.py tests/test_references_construct_agreement.py tests/test_claim_signing.py tests/test_doc_size_budget.py -q --tb=line
...........................................................              [100%]
59 passed in 7.31s
```

AC6 sample-tier (`--samples --skip-clone`, pins brick_math + symfony_demo, both single-language so the predicate does not fire):

```
before (production stashed): ratio 67.376  atlas_tokens 6555  grep_tokens 441650
after:                       ratio 67.376  atlas_tokens 6555  grep_tokens 441650
delta: 0
```

- **Golden/snapshot change:** none
- **Design-invalidation / re-gate:** none

## Phase 4 — Review

- **REVIEWER: OFF (`--no-reviewer`)** — no rule-book-grounded review of this diff exists.
- **CHALLENGER: ON** — [ticket-blind challenger](1afcf3e0-3a27-45be-9866-2509d1b6b8d1). Payload: raw ticket above the mango separator + `git diff main...HEAD` excluding this ticket file. Independence is procedural (working doc withheld), not cryptographic.
- **challenger result:** 11/12 reconstructed requirements **MET**; **AC6 can't tell** (ledger not in the product commit — filled at finalise). No `not met`. Product verdict: all reconstructed product requirements met.
- **Adjudication of extras (not AC fails):**
  1. `find_callers.py:376` `elif cross_lang_census is not None` is not `total_count > 0` — **accepted**: Gate-2 Approach said attach whenever census is not None. The 221 zero reason rewrite is still the first branch. `find_references` hits-only is the recorded Phase-3 deviation.
  2. `attach_authoritative_caveats` replaces the caveats list (`nav_result.py:675-676`), so a sibling caveat then an unmodelled attach drops `CAVEAT_SIBLING_DEFINITIONS`. Pre-existing on the 221 zero path; now reachable on hits. Ticket did not require combining. **Accepted as DISCLOSURE**, not a clean-blocker.
  3. PLAN T-SQL / 219 E1 prunes — **accepted** (Phase-3 R7.6 deviation).
- **Scope reconciliation:** file axis `diff ⊆` approved list (product files at `1589396`). Behaviour axis: find_references zeros **deviated** as recorded; challenger extras adjudicated above. Layer-match: all AC rows ✅, e=0.
- **Proving test would fail without the change?** Yes — R6.5 red-before `KeyError: 'authoritative'` on `627a3b5` with production ungated files stashed.

```
Ran at 15893963d914b052187a7544d74a378e39ba3d5d
$ .venv/bin/python -m pytest tests/test_find_callers_cross_language_unmodelled.py::test_in_language_hits_on_an_unmodelled_crossing_are_not_authoritative tests/test_find_callers_cross_language_unmodelled.py -q --tb=line
..............                                                           [100%]
14 passed in 2.08s
```

- **Clean?** `clean (challenger only — REVIEWER: OFF)` — reviewer criterion ABSENT, not met.
- **Reviewed at** `15893963d914b052187a7544d74a378e39ba3d5d`
- **Reviewed files:** `code_atlas/tools/find_callers.py`, `code_atlas/tools/find_references.py`, `code_atlas/tools/coverage.py`, `tests/test_find_callers_cross_language_unmodelled.py`, `docs/PLAN.md`, `docs/tasks/238_the-honest-zero-predicate-is-gated-on-the-zero.md` (working-doc path, exempt), `docs/LESSONS.md` (exempt), `docs/TOKEN_LEDGER.md`, `docs/BACKLOG.md`

## Phase 5 — Finalise

- **Stale-review guard:** product files unchanged since `1589396`; bookkeeping (this doc, lessons, ledger, backlog) is the reviewed-set / exempt set.
- **PR draft:** from `.github/pull_request_template.md`.
- **Planned outward actions:**
  - [x] push branch — handover authorisation
  - [x] open PR via `gh` — handover authorisation — [#307](https://github.com/cuongdinhngo/code-atlas/pull/307)
  - [ ] merge — NOT authorised
  - [ ] tracker transition — NOT authorised
- **Follow-up tickets:** none. Challenger extras stay in DISCLOSURE.
- **Durable lesson:** recurrence of `192-C1` `gate-the-disclosure-on-its-condition-not-the-row-count` (221 gated a language-scope census on `total_count == 0`).
- **Revert path:** revert the branch / close the PR without merge.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`

Classification is a proposal (`status: proposed`). Human ratification deferred to morning (`k = 0`). Cross-ticket class → `/mango:promote` between tickets; this phase does not write the rule.

Falsify of `192-C1`: still true (a disclosure gated on emptiness cannot describe a partial). Cheap check: `rg -n "total_count == 0 and indexed and subject_file" code_atlas/tools/find_callers.py` — conjunct gone at `:311`. Checked this run, not only restated.

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Notes |
|-------|---------------------|-------|--------|-------|
| Review | ticket-blind challenger | 1 | unmeasured (host does not surface usage) | reviewer OFF; 11/12 MET, AC6 can't-tell then filled |

`LEDGER TOTAL: unmeasured · top cost driver: main-loop`

Main-loop spend is unmeasured on this host. Call-count ceiling was `unknown` at t0.

