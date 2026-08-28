---
id: 189
slug: a-twin-is-a-container-fact-not-a-path-fact
title: 'A twin is a container fact, not a path fact — `shared_subtree_with_subject` ranks the real twin BELOW same-region noise on the anchor''s layout'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [181, 171, 165]
---

## Why this exists

Filed by **181**, which implemented the basis its Scope 3 delegated, **measured it, and declined to
ship it.** The measurement is the ticket:

```
subject : src/alpha/model/member/ModelMember.php
siblings: src/beta/model/member/ModelMember.php        <- the answer the caller wants
          src/alpha/vendor/lib000/Unrelated0.php  ... x40  <- share only the method NAME

rank_sibling_sites(..., subject_file=subject) -> basis "shared_subtree_with_subject"
  position 1  : src/alpha/vendor/lib000/Unrelated0.php     <- same region, so it wins
  position 41 : src/beta/model/member/ModelMember.php  <- the answer, LAST
```

Pinned as `test_the_subtree_basis_would_rank_the_real_twin_BELOW_the_noise`.

**171's basis is right for the case it was built for and wrong for this one.** A subject's *twins*
live in **sibling regions** (`alpha` / `beta` / shared), while same-name *noise* lives **inside the
subject's own region**. Shared-subtree depth measures exactly the wrong axis: it rewards being near,
and a twin is by definition far.

So 181 shipped `sibling_definitions_ranked: false` plus a cap for path seeds, because an honest
*"cannot rank"* beats a `ranked: true` whose first row is noise — that would re-create 181's own
defect with a better-sounding label.

## The discriminator that would work, and why 181 did not use it

*"Is this sibling a twin of my class, or a same-named method on an unrelated one?"* is a question
about the **container**, not the path. `\Alpha\ModelMember::getName` and `\Beta\ModelMember::getName`
share a container trailing name; `\Vendor\Unrelated0::getName` does not.

The data is already fetched. `impact._split_twinned` holds both the subject row and the sibling rows
before `definition_sites` shapes them — and `definition_sites` (`nav_result.py`) publishes only
`{file, line, kind}`, dropping `qualified_name`. So using the container means one of:

1. **Rank on it without publishing it.** Cheapest, and it ranks on evidence the payload does not
   show — the reader sees `ranked_by: <container>` and cannot check a single row against it. R5.5's
   territory: a stated basis the payload cannot support.
2. **Publish the container per site.** Honest and checkable, but it adds bytes to every sibling row on
   every tool that discloses one (165/168/171/181's four call sites), which is exactly the cost axis
   181 was filed to reduce. Needs measuring against 181's ~1.05 KB.
3. **Publish it only for the unranked/capped case**, where the list is already 10 rows. Cheap, and it
   makes the field asymmetric between the ranked and unranked shapes — a new thing to explain.

## Scope

1. Decide between the three above, with the byte cost measured against 181's capped ~1.05 KB.
2. If a container basis ships, it is a **third** basis value beside `shared_subtree_with_subject`, and
   the choice between them is data-driven per call — not a global switch. Record how the choice is made
   and why it is not a threshold (161 AC1).
3. **Re-examine `shared_subtree_with_subject` itself.** If a twin is a container fact, the subtree
   basis may be wrong for `find_callers`/`find_references` too — round 12's case A worked only because
   it had **two** siblings and no noise to outrank. Measure it on a noisy subject before keeping it.

### Explicitly not in scope

- Dropping sites from a ranked list (171's rule stands).
- Resolving the binding (161's AC1 deviation).
- 181's cap and its `ranked` verdict — both shipped and both stay.

## Constraints

- **R5.5** — the payload says what it ranked by, and a stated basis the payload cannot support is
  worse than none.
- **Cost** — 171's budget: a sort over rows already fetched, no query per sibling. Any published field
  is measured against 181's ~1.05 KB.
- **061** — no-sibling and one-sibling payloads stay byte-identical.
- **R6.7** — one ordering site, shared by all four consumers.
- **R1.1** — `::` is the contract's member separator (CONVENTION §3), not a language fact; no branch.

## Acceptance criteria

1. A noisy subject ranks its real twin **first**, pinned on a fixture that mirrors the region layout
   above — and the test fails under `shared_subtree_with_subject`.
2. Whichever option is chosen, the basis a payload names is one the payload's own rows can be checked
   against, or the design records why not (R5.5).
3. Scope 3's re-examination is recorded: `shared_subtree_with_subject` is kept for the qname path with
   a measurement, or replaced.
4. Byte cost measured against 181's capped figure.
5. 061, R4.2, R1.1, no contract bump (R3).

## References
Filed by [181](181_sibling-definitions-fallback-is-a-dump-not-a-ranking.md) with the measurement
above (`tests/test_sibling_disclosure_is_a_ranking_or_says_not.py`). Round 12 §9.a (cases A and B),
§12.d. `code_atlas/tools/nav_result.py` (`rank_sibling_sites`, `definition_sites`);
`code_atlas/tools/impact.py` (`_split_twinned` holds the rows). Related:
[171](171_sibling-definitions-fires-on-most-calls-and-is-unranked.md) (the basis under review),
[165](165_find-callers-splits-across-twins-and-says-reason-ok.md).

## Session status

- **KEY:** 189 · **work_doc_mode:** embed · **Run args:** `--no-reviewer --no-challenger` ("with skipped review"); Gate 4 waived per AGENTS.md.
- **REVIEWER:** OFF · **CHALLENGER:** OFF · **Review phase:** SKIPPED per run arg (maintainer reviews on PR).
- **Lane:** `/mango:autorun` (unattended, ticket 2 of 3: 188 → 189 → 190) · envelope in `.mango/run-contract-189.txt`.
- **Branch:** `feat/189-a-twin-is-a-container-fact` (off `main` at `9b43d6e`, which carries 188)
- **Phase:** 5 finalise — complete; ready for PR.
- **BASELINE:** green — `2459 passed, 0 failed` at `9b43d6e` (bare `pytest`, this Linux host).

## Phase 0 — refine

`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

1. Scope 1's three options → **none of them as written**; see *The option the ticket did not cost*.
2. Scope 2's *"a third basis value, chosen per call, not a threshold"* → shipped; the choice is
   *"did this predicate partition the list?"*.
3. Scope 3's re-examination of `shared_subtree_with_subject` → **kept**, because it answers a
   different question, and its limit is pinned rather than argued.
4. Whether `impact`'s path seed gains a basis → **no**, and the reason is structural.

Not an epic.

## Phase 1 — analysis

**STRUCTURE:** native · **TRACK:** backend · **SCOPE:** S · **TIER:** full

`PREMISE: 4 reference(s) checked | 0 missing | 1 ambiguous (surfaced; it changed the discriminator)`
`RECALL: 3 claim(s) surfaced | 2 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (Scope, Explicitly not in scope, Constraints, Acceptance criteria) | 4 decomposed | ROWS: C=5 R=3 G=1 AC=5`
`CLARIFICATION: 0 raised | 0 self-resolved | 0 for human decision`
`RULE SECTIONS: 9 applicable — 8 by change-type | 1 by recalled handle — §R1.1 (change-type) ✅ · §R3 (change-type) ✅ — no contract touched · §R4.2 (change-type) ✅ · §R5.2 (change-type) ✅ · §R5.5 (change-type) ✅ — it decided the publish question · §R6.5 (recalled handle: prove-the-guard-fails) ✅ · §R6.7 (change-type) ✅ · §R7.2 (change-type) ✅ · §R7.6 (change-type) ✅`
`BASELINE: green — 2459 passed, 0 failed, 0 skipped at 9b43d6e (bare pytest, Linux host)`

**Premise:** the measurement 181 filed is exact and reproduces. **One premise is ambiguous in a way
that changes the answer**, and finding it is what made this ticket small.

### The ambiguity: "a container fact" names the right axis and the wrong datum

The ticket is right that the discriminating fact is about the **container**:
`\Alpha\ModelMember::getName` and `\Beta\ModelMember::getName` share a container trailing name;
`\Vendor\Unrelated0::getName` does not. It then assumes the datum has to be the container **qname**,
and prices all three of its options around publishing it.

**The core cannot read a container's trailing name.** `contract.split_qname` splits at
`MEMBER_SEPARATOR` (`::`), which yields the container *qname* — `\Alpha\ModelMember`. Getting
`ModelMember` out of that needs the container's own **native** separator, and naming one is
R1.1-barred (`\` for one language, `/` or `::` for another, `.` for a third). The alternatives are a
node lookup per sibling — which this ticket's own cost constraint forbids — or one extra lookup per
call, which is what 182 was bitten by.

**There is a container fact the core already has, for free: the file the container is declared in.**
The anchor's twin is another `ModelMember.php`; the noise is `Unrelated0.php`. Same axis, different
datum — and this one is already published on every site row as `file`.

### Requirements matrix

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | title/why | a twin is a container fact, not a path fact | right axis; **the datum is the container's file** | `split_qname` | open |
| R1 | Scope 1 | decide between the three options, cost measured vs 181's ~1.05 KB | **a fourth: 0 added bytes** | proving test | open |
| R2 | Scope 2 | a third basis value, chosen per call, not a threshold | `0 < matched < total` | proving test ×2 | open |
| R3 | Scope 3 | re-examine `shared_subtree_with_subject` before keeping it | **kept — different question**, limit pinned | proving test ×2 | open |
| AC1 | AC 1 | a noisy subject ranks its twin first; the test fails under the subtree basis | Falsifiable: position 1 + the old order | proving test ×4 | open |
| AC2 | AC 2 | the named basis is checkable against the payload's own rows (R5.5) | Falsifiable: re-derive the bands from `file` | proving test ×3 | open |
| AC3 | AC 3 | Scope 3's re-examination recorded | Falsifiable: both directions as tests | proving test ×3 | open |
| AC4 | AC 4 | byte cost measured against 181's capped figure | Falsifiable: **2 B**, and the rejected option's 1 KB+ | proving test ×2 | open |
| AC5 | AC 5 | 061, R4.2, R1.1, no contract bump | Falsifiable: shuffle-stability + a suffix-free fixture | proving test ×3 | open |
| C1 | Constraint | R5.5 — a stated basis the payload cannot support is worse than none | the predicate reads only published fields | — | binding |
| C2 | Constraint | cost — a sort over rows already fetched, no query per sibling | one `PurePosixPath(...).name` per row | — | binding |
| C3 | Constraint | 061 — no-sibling and one-sibling payloads byte-identical | no field added at all | — | binding |
| C4 | Constraint | R6.7 — one ordering site, shared by all four consumers | `rank_sibling_sites` unchanged in signature | — | binding |
| C5 | Constraint | R1.1 — `::` is the contract's separator, not a language fact | and the native one is never read | — | binding |

### Root cause (taxonomy: signal design)

**The ranking measured proximity and the caller was asking about identity.** 171 ranked by shared
subtree depth because "near" is the right answer to 165's own question — *which definition would a
simple-name reference here bind to?* Binding is local, so nearness is the evidence. Round 12 asked a
different question of the same field — *which of these is the regional copy of my class?* — and for
that question a twin is by definition **far**: it lives in a sibling region while same-name noise
lives inside the subject's own. One field, two questions, and the payload named the basis
(`shared_subtree_with_subject`) without the reader knowing which question it answered.

### Blast radius

- `nav_result.py`: `RANK_SHARED_FILE_NAME` and a two-band key inside `rank_sibling_sites`. **No
  signature change**, so `find_callers`, `find_references` and both `impact` paths inherit it with
  zero edits (R6.7 earning its keep for the second ticket running).
- No new payload field, so nothing to check under 061 and nothing to add to CONVENTION §6's table.
- 181's committed counterfactual is **discharged** and rewritten in place.

## Phase 2 — design

### The option the ticket did not cost

The ticket priced three ways of using the container **qname**:

1. rank on it without publishing it — R5.5 violation, a basis the reader cannot check;
2. publish it per site — bytes on every sibling row of four tools, the axis 181 was filed to reduce;
3. publish it only for the unranked/capped case — which is backwards for R5.5, since the unranked
   case has no basis to check.

**The fourth option: rank on the container's FILE NAME, which is already published.** The predicate
is `PurePosixPath(site["file"]).name == PurePosixPath(subject_file).name`. It reads no new datum, so:

- **R5.5 is satisfied at zero cost.** A reader holding the payload can recompute the bands from the
  `file` values in `sibling_definitions` — pinned by re-deriving them in a test.
- **AC4 is 2 bytes**: `shared_file_name_with_subject` is two characters longer than
  `shared_subtree_with_subject`. Against 181's capped ~1.05 KB, and against **> 1 KB** for the
  container-qname option on a 41-row ranked list (measured in the counterfactual, since 171's rule
  forbids capping a ranked list).
- **R1.1 holds without a special case.** A POSIX basename compare reads no suffix and no separator
  table; pinned on a fixture whose paths end in `.mod`.

Where a language does not name a type's file after the type, the predicate simply does not partition
the list — and then it is not named. **A wrong claim is never made, only a weaker one** (R5.6's shape).

### Scope 2: the basis is named only when it decided the order

This is 180's rule reused: *the basis names the ONE predicate the order is decided by.* So:

```
matched = |sites whose file name == the subject's|
partitioned = 0 < matched < |sites|
basis = shared_file_name_with_subject  if partitioned  else  shared_subtree_with_subject
```

If **every** site matches (round 12's case A — two definitions of one class in mirrored regions),
the band is uniform and nearness alone ordered the list; naming the file-name basis would misstate
what ranked it. If **no** site matches, the same, from the other side. `0 < matched < total` is a
structural question — *did this predicate split the list?* — with no tuned number in it, so 161 AC1
is satisfied and the rule holds identically at 2 sites and at 93 (pinned across five sizes).

### Scope 3: `shared_subtree_with_subject` is KEPT, and it is not a compromise

Re-examined as asked, and the verdict is that **171's basis was never wrong — it was answering 165's
question**. 165 exists because *"a simple-name reference may bind there"*, and binding is
namespace-and-path local, so nearest-first is the correct order for that question. 189's basis
answers *"which of these is my twin"*. Both are honest; the payload names which one ran, which is
exactly what R5.5 asks of it. Pinned in both directions:

- a mirrored-regions subject with no noise ranks **nearest first** and reports the subtree basis;
- the anchor's noisy subject ranks the **twin first** and reports the file-name basis.

**And the residual is pinned rather than described.** Forty vendor copies all *named*
`ModelMember.php` leave the band uniform, so the order falls back to nearness and the twin is not
first. The payload says `shared_subtree_with_subject`, so it never claims a twin ranking it did not
do — but the caller is not helped either. That is the honest limit of a free datum.

### Scope: `impact`'s path seed stays unranked, structurally

`attach_seed_refusals` flattens `[(seed_qname, sites), …]` from **every** twinned seed into one list,
so there is no single subject to rank against — which is why 181 passed `subject_file=None` there and
why 189 does not change it. Ranking per seed would mean grouping the disclosure per seed, a payload
shape change beyond this ticket. 181's cap and its `ranked: false` verdict are explicitly out of
scope and both stay, pinned.

### Rejected

- **The container qname as the datum** — unreachable in the core without a per-language separator
  (R1.1) or a lookup per sibling (the cost constraint). Implemented as a committed counterfactual
  showing it ranks correctly and what publishing it would cost.
- **Publishing the container only on the unranked shape** (the ticket's option 3) — the unranked
  shape has no basis to check, so it buys nothing for R5.5 and adds an asymmetry to explain.
- **A boolean `is_twin` per site** — a verdict where the payload can carry the evidence instead, and
  it would be the same bytes as the container with less information.
- **Capping the ranked list's low band** — 171's rule stands and is out of scope.
- **Re-ranking on the file's stem** (basename without suffix) — it would make `Foo.php` and `Foo.ts`
  twins across languages, which is a claim nothing supports, and it reads a suffix (R1.1).

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **Exclusion 1 (recorded limit):** a uniform band of same-named files falls back to nearness and
  does not separate a near copy from a twin. Expiry: the next field retro round — if the anchor
  exhibits that shape, it needs the container datum and therefore a contract or cost decision.
- **Exclusion 2 (AC1 is input-shape-dependent):** *"the twin ranks first"* is proven on a fixture
  built from round 12's measured layout, not on the anchor repo. The fixture is the field's own
  shape, transcribed, but it is still authored. Expiry: the next field retro round, where the same
  `find_callers` call on the anchor either shows the twin at position 1 or does not.

## Phase 3 — execute

### Design-conformance self-check (Axis 2)

| Approach bullet | Status |
|---|---|
| Rank on the container's **file name**, already published (0 added bytes) | implemented-as-approved |
| Basis named only when the predicate partitioned the list (180's rule) | implemented-as-approved |
| `shared_subtree_with_subject` kept, both directions pinned | implemented-as-approved |
| No signature change, so four consumers inherit it (R6.7) | implemented-as-approved |
| `impact`'s path seed unchanged and pinned | implemented-as-approved |
| Container-qname basis kept as a committed counterfactual with its cost | implemented-as-approved |

**Nothing needed correcting during execute** — but two things about the *existing* tests did.

**181's `test_a_qname_subject_still_ranks_as_it_did` is vacuous, and 189 found it by accident.** Its
body is `if SIBLING_DEFINITIONS in payload:` — and the payload it builds answers `reason:
index_stale`, because `tests/test_impact.seed_file` plants rows without on-disk bytes. So the
assertion never ran. My own first end-to-end test failed the same way, which is how it surfaced.
Fixed here by using `tests/test_nav_tools.seed_file`, which writes matching bytes; 181's test is
left as it is, because narrowing it is not this ticket's change list. Filed as a follow-up below.

**181's counterfactual is discharged, not deleted.** `test_the_subtree_basis_would_rank_the_real_twin_BELOW_the_noise`
pinned the defect 189 fixes, so it now fails by design. Rewritten in place as
`test_the_subtree_basis_counterfactual_is_DISCHARGED_by_189`, asserting the new order and pointing
at where the old one is still committed — the record of *why* the basis changed stays in the suite.

### Red runs (R6.5)

1. **The new proving file against the pre-change ordering:** 181's own counterfactual is the red run,
   and it is already in the suite — `assert str(ordered[-1]["file"]) == TWIN_PATH` ("the answer the
   caller wants is LAST") passed before this change and fails after. The new file re-computes that
   order inline (`test_the_same_fixture_put_the_twin_LAST_under_the_subtree_basis`) so the
   improvement is a **diff between two orders**, not an assertion about one.
2. **The partition rule, red both ways:** an all-match fixture and a no-match fixture each report
   `shared_subtree_with_subject`; a version that named the file-name basis unconditionally fails
   both, because the order in those two cases is decided entirely by nearness.
3. **The R1.1 fixture:** `.mod` paths rank correctly, so a suffix-reading implementation fails.

### Empirical outputs

| Measure | Before (171/181) | After (189) |
|---|---|---|
| anchor layout, position of the real twin | **41 of 41 (last)** | **1 of 41** |
| basis reported on that call | `shared_subtree_with_subject` | `shared_file_name_with_subject` |
| basis on case A (mirrored regions, no noise) | `shared_subtree_with_subject` | unchanged |
| basis when no site shares the file name | `shared_subtree_with_subject` | unchanged |
| payload fields added | — | **0** |
| bytes added on a 41-row ranked list | — | **2** (the basis name) |
| bytes the container-qname option would add | — | **> 1 000** (measured) |
| `impact(paths=[…])` disclosure | unranked, capped at 10 | unchanged, pinned |

**Verification coverage:** 5 AC, all 5 covered — 14 new tests in one file, plus 181's counterfactual
rewritten as discharged. No AC left to a claim.

## Phase 5 — finalise

**Delta-green (this Linux host, bare `pytest`):** `2459 passed / 0 failed` at `9b43d6e` →
`2475 passed / 0 failed` (14 new proving tests, plus the two bookkeeping parametrisations that
189's and 191's rows create). ruff + mypy green. `scripts/gate.sh` → `GATE GREEN — all 15 checks passed`.

**Docs, and one argued omission.** `sibling_definitions*` has never had a row in CONVENTION §6's
payload-field table — 181 shipped the family without one, under the same budget pressure — and 189
adds no field, only a second value for an existing one. Tier 1 stands at **25,145 / 25,150 tokens**,
so a row would have to be bought by pruning information rather than restatement. Recorded here
instead of taken silently (R7.6, P3).

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen >= 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

- `prove-the-guard-fails` (R6.5) gains 189 → 24. `source-the-caveat-from-the-computation` (R5.5)
  gains 189 → 6: the basis is named from what actually ordered the list, not from what was available.
- **New:** `189-C1` (type-2, `one-field-two-questions`). seen=1.
- **Follow-up filed:** ticket **191** — 181's `test_a_qname_subject_still_ranks_as_it_did` asserts
  under an `if` on a payload that answers `index_stale`, so it has never run. Found here, not fixed
  here.

### Cost ledger

`LEDGER TOTAL: 0 dispatch (solo main-loop; both review seats waived by run arg) · top cost driver: main-loop (unmeasured — host surfaces no usage block)`

### Review

SKIPPED per run arg "with skipped review". Reviewer **and** challenger waived. Self-checks: an
ambiguity in the ticket's own premise found by reading `split_qname` — the right *axis* with an
unreachable *datum* — which turned three costed options into a fourth that costs 2 bytes; the
rejected option implemented as a committed counterfactual rather than described; 180's
name-the-deciding-predicate rule reused instead of re-derived; a vacuous existing test found by
accident and filed rather than quietly patched; 181's counterfactual discharged in place so the
record of why the basis moved stays in the suite; and the residual — a uniform band of same-named
files is still unhelpful — pinned as a test with the next field round as its expiry.
