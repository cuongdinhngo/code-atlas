---
id: 165
slug: find-callers-splits-across-twins-and-says-reason-ok
title: '`find_callers` on a fully-qualified twin silently omits callers bound to its sibling definition, and says `reason: "ok"`'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [013, 054, 161, 122]
---

## Why this exists (field retro round 10, 2026-08-26)

The round's one **wrong turn in real work**, and it landed on a checklist-mandated §P contract sweep —
the single question type the consuming repo's own process says grep cannot satisfy:

> `find_callers` on the fully-qualified `\Src\System\Event\EventRunner::bedPriceCheck` returned
> **2 src callers + 2 tests** and **omitted `public/getChangeMaintenance.php:1192`** — the one call site
> that actually TypeErrors under the signature change. That file has no `use` statement, so its bare
> `EventRunner::` binds to the **`legacy/` twin**. `reason: "ok"`, `total_count` confident, no marker.
>
> "A confident false *one call site*. Recovered only because I ran the bare-name query **and** a grep
> cross-check. Had I trusted it, the PR would have claimed a swept surface it had not swept."
>
> §16: *"Did it make you worse anywhere? **Yes, once.** … Saved only by a grep cross-check that
> `CLAUDE.md`, not the tool, taught me to run."*

Round 9 recorded this shape on `find_references` (7-A) and the retro's verdict is that **it has now
moved to `find_callers`**: the alias/twin split under-reports **callers**, not just references — and
`find_callers` is the tool the mandated sweep routes to.

**Priority note from the retro's §16 and the maintainer's review:** this must land **before** any
roll-out work. At reach 1, a confidently-partial sweep is caught by one developer's cross-check habit;
at reach N that habit is prose in a `CLAUDE.md` nobody is obliged to read.

## Root cause

- `code_atlas/find_callers.py:232` — `reason = relation_reason(hit_total=outcome.total_count,
  symbol_indexed=indexed)`. The reason is a pure function of *this qname's* hit count. Nothing asks
  whether the same trailing name is defined elsewhere and carrying callers of its own.
- `code_atlas/find_callers.py:214-225` — `unresolved_bare_calls` exists, but it counts a **different
  failure**: bare CALLS sites that target *nothing* after the alphabetical Method cap (054). The round-10
  case is the opposite — the call site resolved **successfully**, to a real sibling node. It is not
  unresolved, it is attributed elsewhere.
- `code_atlas/find_callers.py:255` — `attach_ambiguous_definitions(result, definition_sites(subject_nodes))`
  fires on `nodes_by_qualified_name(lookup)`, i.e. **exact-qname** twins only. `\Src\…\EventRunner::bedPriceCheck`
  and `\EventRunner::bedPriceCheck` are different qnames, so the disclosure never triggers.
- Contrast `code_atlas/tools/find_references.py:202-203`, which already sets
  `result["authoritative"] = False` when the answer is caveated. `find_callers` has no equivalent.

The graph is not wrong — the edges are correct per qname. The **payload** is wrong: it presents a
partition of the callers as the whole of them.

## Scope

Make `find_callers` disclose that the subject has siblings and that callers may sit on them.

1. When the subject's **trailing name** (the `bare_name` already computed at `find_callers.py:214`)
   has definitions under other qnames, disclose them — the `definition_sites` shape `read_symbol` and
   `impact` already return (078 / 161), so the agent sees the same three trees it sees elsewhere.
2. Caveat the count: `authoritative: false` (find_references' spelling, `find_references.py:203`) or a
   counted `callers_on_siblings: N`, so a swept-surface claim cannot be made from a partition.
3. `reason` must stop reading `"ok"` for an answer that is knowingly partial, **or** the caveat must be
   prominent enough that `ok` is survivable. Design records which, and why.

Whether the sibling callers are **counted** (one extra query) or merely **named** (sites only) is a
design decision with a measured cost, recorded with the rejected alternative.

### Explicitly not in scope

- Merging twins, or picking one. The repo's premise is that the same identifier is legitimately defined
  three times; 161 already established that **refusal beats an arbitrary choice**.
- `find_references` (7-A's original home) — same class, different tool; a follow-up if the mechanism
  generalises.
- Any change to edge storage or the resolver.

## Constraints

- **R1.1** — no language branch; the trailing-name split is a qname-shape question, not a PHP one.
- **061** — omit-when-empty: a subject with no siblings must be byte-identical to today.
- **R3** — no new contract vocabulary; no `contract_version` bump.
- **R4.2** — order-stable site lists (161's `_split_ambiguous` precedent).
- **Cost** — `find_callers` is a hot mechanism tool. The sibling lookup must be one bounded query, and
  its per-call cost measured against the tokens-to-answer gate.

## Acceptance criteria

1. `find_callers` on a qname whose trailing name has ≥ 2 definitions discloses the sibling definition
   sites and carries the caveat (`authoritative: false` or the design's recorded equivalent) — pinned by
   a fixture with a twin pair, one caller on each.
2. The same call on a subject with exactly one definition is **byte-identical** to today (061).
3. An answer that is knowingly partial cannot present a bare `reason: "ok"` with an uncaveated
   `total_count`; the chosen shape and its rejected alternative are recorded in the working doc.
4. The added per-call cost is measured and stays within the tokens-to-answer gate.
5. `unresolved_bare_calls` / `bare_name_truncated` (054) behaviour is unchanged — this is a distinct
   failure and both must remain distinguishable.
6. Determinism (R4.2), no language branch (R1.1), no bump (R3).

## References

Field retro round 10 §3 #16, §7 (row `bedPriceCheck`), §10.d (*"I got it right because I did not believe
`find_callers`"*), §14 (7-A **moved to `find_callers`**), §14.a (carve-out (f) **extended to
`find_callers`**), §15 ticket 4. `code_atlas/tools/find_callers.py:214-225,232,255`;
`code_atlas/tools/find_references.py:202-203`. Related: [013](013_nav-tools.md),
[054](054_bare-name-callers-silent-drop.md), [161](161_impact-resolves-a-shared-qname-to-one-twin-and-carries-no-freshness.md)
(refusal over arbitrary binding), [122](122_exact-miss-shaping-discards-a-resolved-subject.md).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 165 · **work_doc_mode:** embed (below separator) · **Run args:** `--no-challenger` (skipped review); Gate 4 waived per AGENTS.md convention.
- **CHALLENGER:** OFF (--no-challenger) · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Branch:** `feat/165-find-callers-discloses-twin-siblings`
- **Phase:** 1 analysis — complete, awaiting Gate 1.
- **BASELINE:** red (platform-excluded, `import fcntl` on Windows); delta-green via Docker before PR.

## Phase 0 — refine

`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

Fully specified: scope, 6 ACs, constraints, explicit not-in-scope. The two open items (counted-vs-named siblings; `reason` handling) the ticket itself labels design decisions — HOW, resolved in design. No acceptance-bar decision for the user. Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** M · **TIER:** full

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 2 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=8 R=3 G=1 AC=6`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 7 applicable — 6 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R3 (change-type) ✅ · §R4.2 (change-type) ✅ · §R5.5 (recalled handle: source-the-caveat-from-the-computation) ✅ · §R6.1 (change-type) ✅ · §R6.5 (change-type) ✅ · §R7.2 (change-type) ✅`
`BASELINE: red — bare pytest fails at collection (import fcntl, Windows platform exclusion); delta-green via Docker before PR`

**Premise:** references resolve — `find_callers.py:214` (`container, bare_name = split_qname`), `:219` (`count_nodes_by_name`), `:232` (`relation_reason`), `:255` (`attach_ambiguous_definitions(... definition_sites(subject_nodes))`), `find_references.py:202-203` (`result["authoritative"] = False`), `store.nodes_by_name` (`store.py:798`). Field-retro §-refs are prose.

**Recall (advisory):** `122-C1` (branch-on-status-not-shared-count, by symbol/area), `161-C1` (honest-endpoint-when-model-cannot-answer, by symbol), `source-the-caveat-from-the-computation` / **R5.5** (by handle — the new caveat must be sourced from the sibling computation).

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Scope preamble | "Make `find_callers` disclose that the subject has siblings and that callers may sit on them" | A partition of callers must not read as the whole | `find_callers.py:232,255` | open |
| R1 | Scope 1 | subject's trailing `bare_name` has definitions under other qnames → disclose them (`definition_sites` shape, 078/161) | one bounded `nodes_by_name(bare_name, kind)` query; sites of qname≠subject | `store.nodes_by_name` (store.py:798), `definition_sites` (nav_result.py:516) | open |
| R2 | Scope 2 | caveat the count: `authoritative: false` (find_references) or counted `callers_on_siblings: N` | mark the answer non-exhaustive; find_references' spelling | `find_references.py:203` | open |
| R3 | Scope 3 | `reason` must not read `ok` for a knowingly-partial answer, OR the caveat is prominent enough | design records which + why | — | open |
| AC1 | AC 1 | qname whose trailing name has ≥2 defs discloses sibling sites + caveat — fixture: twin pair, one caller each | Falsifiable: seeded twin test asserts `sibling_definitions` + `authoritative:false` | proving test | open |
| AC2 | AC 2 | one-definition subject **byte-identical** to today (061) | Falsifiable: no-sibling payload unchanged | pin test (extend `test_unique_qname_payload_omits...`) | open |
| AC3 | AC 3 | partial answer cannot present bare `reason:ok` + uncaveated `total_count`; shape + rejected alt recorded | Falsifiable: test asserts caveat present when siblings exist | proving test + working doc | open |
| AC4 | AC 4 | added per-call cost measured, within tokens-to-answer gate | Falsifiable: one bounded query; measured + recorded | measurement | open |
| AC5 | AC 5 | `unresolved_bare_calls`/`bare_name_truncated` (054) unchanged and distinguishable | Falsifiable: distinct field; 054 tests still green | existing 054 tests | open |
| AC6 | AC 6 | determinism (R4.2), no language branch (R1.1), no bump (R3) | Falsifiable: `_NODE_ORDER` stable; grep-gate; contract test | — | open |
| C1 | Constraint | R1.1 no language branch (qname-shape question) | — | binding |
| C2 | Constraint | 061 omit-when-empty (no siblings → byte-identical) | =AC2 | binding |
| C3 | Constraint | R3 no new contract vocabulary / no bump | — | binding |
| C4 | Constraint | R4.2 order-stable site lists | `nodes_by_name` orders by `_NODE_ORDER` | binding |
| C5 | Constraint | Cost — one bounded sibling query, measured | =AC4 | binding |
| C6 | Not-in-scope | No merging/picking twins (161: refusal beats arbitrary) | disclose only | boundary |
| C7 | Not-in-scope | `find_references` not touched (same class, follow-up) | find_callers only | boundary |
| C8 | Not-in-scope | No edge-storage / resolver change | payload-layer only | boundary |

### AC validation (independently re-derived)

All ACs falsifiable; none carries a bare ✅. No AC-value mismatch. AC1's trigger re-derived: the honest condition is "a definition exists under a **different** qname with the same trailing name" (`nodes_by_name(bare_name,kind)` filtered to `qname != subject`), which is byte-equivalent to the ticket's "≥2 definitions" when the subject is unique, and correctly does **not** fire for exact-qname duplicate declarations (those are the existing `ambiguous_definitions` case) — a distinction the design records.

### Root cause (taxonomy: logic)

`find_callers.py:255` disclosure fires only on `definition_sites(subject_nodes)` where `subject_nodes = nodes_by_qualified_name(lookup)` — **exact-qname** twins. A sibling under a *different* qname with the same trailing name (`\EventRunner::bedPriceCheck` vs `\Src\…\EventRunner::bedPriceCheck`) never triggers it, and `relation_reason` (`:232`) is a pure function of this qname's own hit count. The graph edges are correct per qname; the payload presents a partition as the whole.

### Blast radius

- Handler: `code_atlas/tools/find_callers.py` (add sibling lookup + disclosure).
- Store: `nodes_by_name` already exists (`store.py:798`) — no store change.
- Helpers: `definition_sites` reused (nav_result.py:516). New payload field `sibling_definitions` + `authoritative`.
- Tests: `tests/test_ambiguous_qname.py` (twin fixture pattern + seed helpers) is the home for the proving test.
- Universal inventory `N=1` change site (find_callers). `find_references` explicitly out of scope.
- Repos: `app` only. No contract/schema/resolver change.

## Phase 2 — design

### Approach

In `find_callers`, after `container, bare_name = split_qname(lookup)` (`:214`), when the subject is **method-shaped and indexed** (`indexed and container is not None` — the same gate the existing `unresolved_bare` check uses), run **one bounded query** `store.nodes_by_name(bare_name, kind="Method", limit=config.max_results)` and keep the rows whose `qualified_name != lookup`. Those are the **sibling definitions** — same trailing method name, different qname. Shape them with the existing `definition_sites` helper. When any exist:
- `result["sibling_definitions"] = <sites>`
- `result["authoritative"] = False` (find_references' spelling, `find_references.py:203`)
- carry `authoritative` on the claim line (add to `CLAIM_CARRY`), so a signed answer discloses it too.

Runs on the **success path** (the round-10 case had 4 real callers and omitted a 5th on the sibling), independent of `total_count`. Byte-identical when no sibling exists (061). The subject's own exact-qname duplicate declarations keep going to `ambiguous_definitions` (different concern) — `sibling_definitions` is filtered to `qname != lookup`, so the two disclosures never overlap.

### Design decisions (the HOWs the ticket delegated)

- **Named sites, not counted callers (R2/Scope-2, cost).** Disclose sibling *definition sites* via **one** `nodes_by_name` query + `authoritative: false`. **Rejected:** counting callers on each sibling (`callers_on_siblings: N`) — that is one `count_edges_by_target` per sibling, i.e. **N unbounded queries**, violating the "one bounded query" cost constraint. Naming the sites is one query and already lets the agent re-ask `find_callers` per sibling qname.
- **Keep `reason` semantics; make `authoritative: false` the marker (R3/Scope-3).** The answer *does* have real callers, so `reason: ok` is truthful about "callers exist"; what is false is exhaustiveness, which `authoritative: false` names precisely — exactly the find_references precedent the ticket cites. **Rejected:** a new `reason` value (e.g. `subject_has_siblings`) — it would collide with the hits-exist semantics an agent branches on, and diverge from find_references for the same class of caveat. Cross-tool consistency + the prominent `authoritative` field make `ok` survivable (Scope-3's second option).
- **Field name `sibling_definitions`** (not reusing `ambiguous_definitions`): the two mean different things — `ambiguous_definitions` = same qname, load-order binding; `sibling_definitions` = different qname, same simple name. A distinct field keeps each honest.

### Assumptions

| Assumption | Tag |
|---|---|
| `nodes_by_name(bare_name, kind="Method")` returns the subject + every same-named Method twin | verified (store.py:798, `idx_nodes_name`) |
| One extra indexed lookup per method call is within the cost budget | novel-untested → resolved by AC4 measurement (single `WHERE name=? AND kind=?` on an index, limit-bounded) |
| No-sibling payload is byte-identical | verified (field added only when `sibling_sites` non-empty) |

### Smallest change-list

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|
| Sibling lookup after `split_qname`; attach `sibling_definitions` + `authoritative:false` | `code_atlas/tools/find_callers.py` | new payload fields (omit-when-empty); `unresolved_bare` path untouched | R1, R2, R3, AC1, AC2, AC3, AC5, AC6 | 1/1 |
| Add `authoritative` to `CLAIM_CARRY` | `code_atlas/tools/find_callers.py` | claim line gains the caveat only when present | R2 | 1/1 |
| Proving test (twin pair) + byte-identical pin + measurement | `tests/test_ambiguous_qname.py` | new tests; existing 070/054 tests unchanged | AC1, AC2, AC3, AC4 | 1/1 |
| Docs: BACKLOG status, TOKEN_LEDGER, LESSONS | `docs/*` | R7.2 bookkeeping test | R7.2 | 1/1 |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `source-the-caveat-from-the-computation` (R5.5) — **traced.** The caveat (`authoritative:false` + `sibling_definitions`) is sourced from the same `nodes_by_name` computation that owns the whole sibling fact, not re-derived downstream. Command run to confirm the store method exists and is bounded:
  ```
  $ grep -n "def nodes_by_name" code_atlas/store.py
  798:    def nodes_by_name(self, name: str, *, kind: str | None = None, limit: int) -> list[Row]:
  ```
  The disclosure reads directly from that query's rows (filtered `qname != lookup`) → one owner, no second producer that could disagree (R5.5 falsifier absent).

### Rule compliance

R1.1 (trailing-name split is qname-shape, not PHP) ✅ · R3 (no contract vocab; `sibling_definitions`/`authoritative` are payload furniture) ✅ · R4.2 (`nodes_by_name` orders by `_NODE_ORDER`) ✅ · R5.5 (caveat sourced from the owning computation) ✅ · R6.1/R6.5 (proving test, red pre-change) ✅ · R7.2 ✅.

### Verification plan (per-AC, layer-matched)

| AC | risk layer | proof artifact | layer-match? |
|---|---|---|---|
| AC1 | integration (twin nodes + callers in a store) | integration (seeded store, `test_ambiguous_qname` style) | ✅ |
| AC2 | logic (no-sibling payload unchanged) | unit/integration (seeded unique subject) | ✅ |
| AC3 | logic (caveat present iff partial) | integration | ✅ |
| AC4 | logic (one bounded query) | measurement (manual-recorded) + query-shape assertion | ✅ |
| AC5 | integration (054 behaviour intact) | existing `test_bare_name_callers_silent_drop` re-run | ✅ |
| AC6 | logic + guard (R1.1 grep-gate, no bump) | unit + grep-gate | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor`

### Proving test

`test_find_callers_discloses_sibling_definitions_on_a_twin` in `tests/test_ambiguous_qname.py`: seed two `Method` twins with the same short name `bedPriceCheck` under **different** qnames (`\Src\EventRunner::bedPriceCheck`, `\EventRunner::bedPriceCheck`), one caller each; call `find_callers` on the Src twin. Assert its own caller is returned (`total_count == 1`), `authoritative is False`, and `sibling_definitions` names the `\EventRunner::bedPriceCheck` site. **Fails pre-change** (no `sibling_definitions`, no `authoritative`). Plus a byte-identical pin for a solo method (AC2). Invocation: `pytest tests/test_ambiguous_qname.py -k sibling` (full suite via Docker before PR).

### Rollback + porting

Rollback: revert `find_callers.py` + the added tests (single module). Porting: `app` only.

### SCOPE

`SCOPE: M` — one core module + tests + bookkeeping; no tier crossing. Branch `feat` matches.

## Phase 3 — execute

**Branch:** `feat/165-find-callers-discloses-twin-siblings`

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Sibling lookup via one bounded `nodes_by_name(bare_name, kind="Method")`, filtered `qname != lookup` | implemented-as-approved |
| Attach `sibling_definitions` + `authoritative:false` when siblings exist; add `authoritative` to CLAIM_CARRY | implemented-as-approved |
| Byte-identical when no sibling; `ambiguous_definitions` (exact-qname) untouched | implemented-as-approved |

No deviations. Diff ⊆ approved list (`find_callers.py`, `test_ambiguous_qname.py`, this doc).

### Empirical outputs

Targeted tests (Docker/Linux):
```
tests/test_ambiguous_qname.py → 11 passed  (9 existing + 2 new; proving test + byte-identical pin)
```
AC4 cost (Docker, 200 same-named siblings, whole call):
```
per-call ms (200 siblings): 1.352
sites: 49 (bounded by max_results=50) | authoritative: False | total_count: 1
bytes without sibling fields: 361 | with: 2762   # sibling payload only when siblings exist
```
Full suite: `2122 passed, 1 skipped, 0 failed (162.21s)`. ruff + mypy: green (72 files). R1.1 grep: clean (no language branch).

**Proving test:** `test_find_callers_discloses_sibling_definitions_on_a_twin` — fails pre-change (no `sibling_definitions`/`authoritative` → KeyError), passes after.

### Ph3/4 proven by

| AC | proven by |
|---|---|
| AC1 | `test_find_callers_discloses_sibling_definitions_on_a_twin` |
| AC2 | `test_find_callers_solo_method_is_byte_identical` + existing `test_unique_qname_payload_omits_the_ambiguity_key` |
| AC3 | proving test asserts `authoritative:false` beside `reason:ok` + `total_count` |
| AC4 | measured ~1.35 ms worst-case; one bounded query; 0 bytes when no sibling |
| AC5 | existing `test_bare_name_callers_silent_drop` green (054 path untouched) |
| AC6 | R1.1 grep clean; no `contract.py` change; `nodes_by_name` `_NODE_ORDER`-stable |

## Phase 5 — finalise

**Delta-green (Docker / Linux):** full suite `2122 passed, 1 skipped, 0 failed`; ruff + mypy green (72 files); R1.1 grep clean. Bare pytest red on Windows (`import fcntl`) — recorded platform exclusion.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

`165-C1` (type-2, `disclose-a-partition-as-a-partition`, seen: 165) recorded as `proposed`. seen=1 → stays in lessons_path. Relates to 161/070/R5.5.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; review phase skipped by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

0 subagent dispatches → ledger complete with 0 rows.

### Review

SKIPPED per run arg "with skipped review". Reviewer + challenger waived; no `Reviewed at` marker → stale-review guard waived consistently. Self-checks: full suite delta-green, ruff/mypy green, proving test passing.
