---
id: 161
slug: impact-resolves-a-shared-qname-to-one-twin-and-carries-no-freshness
title: '`impact` binds a shared qname to one arbitrary twin at tier RESOLVED, and carries no freshness field for an answer acted on destructively'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [017, 070, 078, 077]
---

## Why this exists (field retro rounds 8–9, 2026-08-25/26)

`impact` answers *"what breaks if I change this?"* — the answer a developer acts on **destructively**
(round 9's author deleted directories on it). Two rounds found it silently wrong or silently
undated on exactly that question.

**9-A — a shared global binds to the wrong twin, and the whole radius is downstream of it.**

> Seed `src/.../MemberTab/tabs.php`. `impact` bound `showNewMemberScreen` — defined **in the seed
> file itself at :87** — to the **legacy ALPHA** definition at `legacy/.../tabs.php:39`, tier `RESOLVED`.
> **5 of 6 rows (83%) were `legacy/` files the change cannot affect; 0 rows were the file's real `src/`
> consumers.** `seeds_dropped: 0`, no `reason`, every row `RESOLVED` — nothing in the payload suggests
> anything is wrong. And this repo's `CLAUDE.md` **routes developers to this exact call.**

The asymmetry that makes it dangerous: a *bare-name* ambiguity is dropped and counted; a *shared exact
qname* is silently resolved to one. `read_symbol` already refuses this case with `subject_ambiguous`
— *"same ambiguity, same index, opposite honesty"* (round 9 §15).

**8-E — no freshness field at all.**

> `impact` calls answered about files already deleted in the working tree, correctly, with nothing in
> the payload naming the revision. No `staleness`, no `built_at`, no `source_stale`. A blast-radius
> answer is exactly the kind acted on destructively; `sign=true` gives a revision, the default payload
> gives none.

## Root cause

- **Seed resolution short-circuits on the first exact hit.** `code_atlas/tools/impact.py:176-184`
  (`_resolve_seed`) returns `SubjectResolution("resolved_unique", …)` when
  `store.nodes_by_qualified_name(qname, limit=1)` is non-empty — `limit=1`, so N identical-qname
  definitions collapse to one. `store.py:2461-2467` (`_impact_node_loc`) then picks **one arbitrary**
  node's file/line (`limit=1`, whichever `_NODE_ORDER` yields first). No same-file / same-tree
  preference.
- **The honest path exists but is not taken here.** A bare name that is not an exact qname falls to
  `classify_missing_subject` and an `ambiguous` status is dropped and counted (`impact.py:135-198`).
  `REASON_SUBJECT_AMBIGUOUS` (`nav_result.py:49`) and `attach_ambiguous_definitions`
  (`nav_result.py:512-523`) exist and are used by `find_references` (`find_references.py:198`) — but
  `impact` never emits either.
- **Freshness never reaches the body.** `impact.py:91` calls `compute_staleness(...)` **only** when
  `sign=True`, feeding the optional `claim` line (`impact.py:111-119`). The `nav_result(...)` payload
  (`impact.py:94-104`) carries `depth` / `seeds_dropped` / `truncated` but no `staleness` /
  `built_at` / `source_stale` / `last_commit`. Contrast `get_index_status.py:166-167` and
  `find_references.py:110-112` (`FreshnessGuard`).

## Scope

- **Resolve a shared qname honestly.** When a seed qname has N > 1 definitions, prefer a definition in
  the **same file**, then the **same directory subtree** as the seed; if still ambiguous, emit
  `subject_ambiguous` with the candidates (as `read_symbol` / `find_references` already do) rather than
  silently walking one twin's subtree at tier `RESOLVED`. The preference is a general graph/path
  heuristic — **never** a repo- or framework-specific rule (R2).
- **Carry freshness in-band.** Add `staleness` (and the revision it is a zero *at*) to the default
  `impact` payload, via the same `FreshnessGuard` / `compute_staleness` the other tools use — not only
  behind `sign=true`. A `seeds_dropped: 0` that a reader relies on before deleting code must name the
  revision that zero is true at.

### Explicitly not in scope

Per-subject reasons for a multi-seed `impact` call (`impact` merges seeds into one radius by design —
PLAN §12, task 102). This ticket is about a *single* seed whose qname is shared, and about the payload's
freshness.

## Constraints

- **R1.1** — no language branch. Same-file / same-tree preference keys on node file path and the seed's
  path, which are language-neutral. **R2** — no repo/framework names (the `legacy/alpha` ↔ `legacy/beta`
  twin shape is the *symptom*, not the rule; the fix is general same-tree preference).
- **R3** — `subject_ambiguous` is existing tool vocabulary (no `contract_version` bump); changing what
  a seed resolves to is a **behaviour change** — re-read every test asserting an `impact` seed binding
  or `seeds_dropped`, don't merely re-record.
- **R4 / R4.2** — same index, same subject, same result; the tie-break among equal-distance candidates
  must be deterministic (e.g. path order), not arbitrary.
- **061** — freshness rides the existing payload shape; measure any size change on the cheap path.

## Acceptance criteria

1. On a planted graph with the same qname defined in the seed file and in a sibling subtree, `impact`
   on the seed resolves to the **same-file** definition and its real consumers — not the sibling twin —
   pinned by a test that fails on today's `limit=1` short-circuit.
2. When N > 1 definitions are equidistant (no same-file/same-tree winner), `impact` emits
   `subject_ambiguous` with the candidates rather than a confident `RESOLVED` walk of one — pinned by a
   test.
3. The default (`sign=false`) `impact` payload carries a freshness signal (`staleness` and the revision
   the answer describes), pinned by a test; `minimal`'s size change, if any, is measured and stated.
4. Every existing assertion on an `impact` seed binding / `seeds_dropped` is re-read, each verdict
   recorded (R3); no expectation is updated to match new output without that reasoning.
5. No language branch (R1.1 grep-gate green); no repo/framework name in the heuristic (R2 grep-gate
   green). Determinism holds (R4.2).

## References

Field retro rounds 8–9, findings **9-A** (shared-qname mis-binding) and **8-E** (`impact` carries no
freshness). `code_atlas/tools/impact.py:91,94-104,111-119,135-198,176-184`,
`code_atlas/store.py:2461-2467`, `code_atlas/tools/nav_result.py:49,512-523`,
`code_atlas/tools/find_references.py:110-112,198`, `code_atlas/tools/get_index_status.py:166-167`.
Related: [017](017_impact-engine.md) (the engine), [070](070_ambiguous-qname-no-scoping.md) (one qname,
five definitions merged), [078](078_ambiguous-payload-still-picks-one-definition.md)
(`ambiguous_definitions` warns while `source` ships one), [077](077_index-cannot-name-the-revision-it-describes.md),
[102](102_impact-cannot-tell-an-absent-subject-from-a-zero.md) (the seed-drop count this builds on).

---
MANGO WORKING DOC (below this line is NOT part of the raw ticket)

## Session status
- Phase: finalise (complete). TIER: full. SCOPE: M. CHALLENGER: ON.
- work_doc_mode: embed (plain local-file ticket).
- Reviewed at: challenger-only (reviewer waived by run args; challenger ON).

## refine
PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)
RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)
REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes

## analysis
CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision
RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — §R1.1 (rulebook) ✅, §R2 (rulebook) ✅, §R3 (rulebook) ✅, §R4.2 (rulebook) ✅
SECTIONS: 3 found (Scope, Constraints, Acceptance criteria) | 3 decomposed | ROWS: C=4 R=2 G=1 AC=5

## design — AC1 deviation, recorded for maintainer review
The ticket Scope §1 asks for a same-file → same-tree → ambiguous *cascade* that resolves a shared
qname to the same-file definition **and its real consumers, not the twin's**. That last clause is
**architecturally unimplementable** under the current contract, and the ticket-blind challenger
**independently verified** it against `store.py`: edges reference their target by `target_qname`
(a string), never a node id (`store.py` edges schema), and `impact_radius` walks purely by
`e.target_qname = f.qname` (`store.py:1415-1424`). So the graph cannot tell which twin a caller
targets — a same-file-preferred seed would still pull the identical mixed caller set. "Its real
consumers, not the sibling twin's" cannot be answered without a schema change, which is out of this
ticket's blast radius (`store.py` unchanged).

Delivered instead the ticket's own cited desired endpoint: **subject_ambiguous parity with
read_symbol** ("same ambiguity, same index, opposite honesty", round 9 §15, quoted in the ticket's
own root-cause). `_split_ambiguous` routes any seed qname with >1 definitions to
`ambiguous_definitions` + (when nothing else walked) `reason=subject_ambiguous`, rather than walking
one arbitrary twin at tier RESOLVED. A genuinely unique seed still walks (regression-pinned). This is
a deliberate deviation from Scope §1's literal cascade, grounded in the verified edge model; flagged
in the PR for the maintainer.

AC3 freshness: `compute_staleness` is now unconditional (not sign-gated); `_attach_freshness` adds
`staleness` + `last_commit` to the default payload. **Measured (AC3 / 061):** the cheap-path delta is
24 B (`staleness` alone) to ~83 B (`staleness` + a full 40-char `last_commit`) — bounded, never
scaling with the radius; pinned ≤ 90 B by a test.

AC4: every impact test file was re-run green in Docker (`test_impact.py`, `test_qname_subject_honesty`,
`test_impact_modules`, `test_claim_signing`, `test_server_build`) — none asserts an exact impact
payload and none plants a duplicate-qname fixture, so neither the new `staleness` field nor the
shared-qname refusal path contradicts any existing seed-binding / `seeds_dropped` expectation. Verdict
per file: unchanged, no expectation edited. The one moved test
(`test_impact_hot_path…` → `test_build_stamp_needs_no_git_on_the_hot_path` on find_references) is the
disclosed consequence of impact now reading git by design.

EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor
HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (n/a) | 0 unanswered

## execute
No design-invalidated escalation; no stuck-detector trips. AC2/AC3/AC5 met; AC1 delivered as a
verified, recorded deviation (subject_ambiguous); AC4 re-run green.

## review (challenger-only — reviewer waived)
CHALLENGER: ON. Verdict: AC2/AC3-freshness/AC5/R1.1/R2/R4.2 MET with path:line; AC1 NOT MET as
literally worded — but the challenger **independently verified** the qname-keyed edge model makes it
unimplementable and called the subject_ambiguous substitution "defensible / the honest alternative".
AC3 size-measurement clause it flagged unaddressed — **fixed**: a measured, test-pinned byte bound
added. AC4 it marked CAN'T-TELL-from-diff but empirically no regression — the verdict is recorded
above. Result: clean on the delivered design (reviewer only — CHALLENGER: ON), AC1 deviation flagged
for the maintainer on the PR.

### Cost-ledger
| phase | dispatch | round | tokens |
|---|---|---|---|
| review | challenger (ticket-blind) | 1 | 85,056 |

main-loop: unmeasured (host surfaces no usage block).

## finalise
Delta-green in Docker (`scripts/docker-test.sh`, linux): pytest 2111 passed / 1 skipped / 0 failed
(+ the AC3 measurement test since); `gate.sh` in-container — ruff · mypy · pytest · tokens-to-answer
(ratio ≥ 0.63) · R1.1/R2.2/R4.1 grep-gates · php -l · composer validate all PASS; phpstan `[OK]`.

CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified
FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)
RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)
RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (none) | 0 left in lessons_path
PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0
LEDGER TOTAL: 85056 · top cost driver: review/challenger
