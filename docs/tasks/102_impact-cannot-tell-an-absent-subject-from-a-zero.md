---
id: 102
slug: impact-cannot-tell-an-absent-subject-from-a-zero
title: '`impact` reports `seeds_dropped: 0` for a subject it never found — the one number that separates a modelled zero from a failed query'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [017, 100]
---

## Goal
`impact` answers a subject it cannot resolve at all with `results: []` **and**
`seeds_dropped: 0` — the same pair it returns for a genuine modelled zero. The two are
indistinguishable in the payload, and `seeds_dropped` is precisely the field a reader consults to
tell them apart.

Measured during task 100:

```
$ impact(qnames=["\App\Nope"], sign=True)
results=0 seeds_dropped=0
```

`\App\Nope` is not in the index. Nothing was walked. The payload says a clean zero.

## Root cause
`code_atlas/store.py:1009-1011`:

```python
ordered_seeds = list(dict.fromkeys(q for q in seeds if q))
if not ordered_seeds:
    return ImpactResult([], 0, 0)
```

The empty-seed early return is taken **before** any counting, so the drop is never attributed.
Upstream, `impact._resolve_seed` (`code_atlas/tools/impact.py`) returns `None` for a qname that
neither matches exactly nor resolves uniquely, and `_seeds` simply skips it — so the information
that a seed was requested and lost exists at the call site and is discarded one frame later.

## Why this is worth a ticket, not a note
`impact`'s value is the class of claim a text search cannot make: **a modelled zero**. That claim
rests entirely on `seeds_dropped == 0` meaning *"every subject you named was found"*. When the field
is 0 because nothing was ever counted, the strongest answer this server produces is
indistinguishable from its weakest, and the reader has no way to tell.

Task 100 shipped a **workaround, not a fix**: `impact` refuses to attach a signed `claim` line when
the seed set is empty, so the ambiguity cannot become a quotable falsehood. That guard protects the
one consumer 100 added. **Every other reader of the payload is still misled** — including any agent
reading `seeds_dropped` directly, which is the documented way to interpret an empty `impact` answer
(PLAN §12; task 065).

## Scope / Deliverables
- **Attribute the drop.** A requested seed that does not resolve must be counted in `seeds_dropped`,
  including when it is the *only* seed. Decide where the count belongs — `store.impact_radius`
  cannot see what `_seeds` discarded, so this is likely a tool-side count added to the store's,
  not a change to the early return alone.
- **Distinguish the two zeros in the payload.** After the fix, `results: []` with
  `seeds_dropped: 0` means a modelled zero and nothing else. Consider whether a subject that
  resolved to *no seeds at all* also needs a `reason` (the nav vocabulary already has
  `no_such_symbol` / `name_not_qualified` / `not_indexed`, and `classify_missing_subject` is
  already called on this path) — an empty `impact` answer currently carries no `reason` at all.
- **Re-examine task 100's guard.** Once the payload can tell the two apart, the
  `if not sign or not seeds` refusal in `impact` may be replaceable by an honest line that names the
  drop (`seeds_dropped=1`). Removing the guard is **not** required by this ticket; deciding whether
  it should go is.
- **Multi-seed partial loss.** `impact(paths=[a, b])` where `a` resolves and `b` does not must
  report `seeds_dropped: 1`, not 0 — check whether this already works or shares the bug.

## Constraints
- **R4** — same index, same subject, same counts. No new query on the hit path.
- **061** — the fix must not add a field to the common (non-empty, nothing-dropped) answer.
- **R3** — `seeds_dropped` is an existing tool-payload field; changing what it counts is a
  **behaviour change to a documented number**. PLAN §12 and any test asserting `seeds_dropped == 0`
  must be re-read, not merely re-recorded (a changed expectation here is a behaviour change, not a
  golden to bump).
- **R1.1** — no language branch; resolution already runs through `classify_missing_subject`.

## Acceptance criteria
- `impact` over a subject absent from the index reports `seeds_dropped >= 1`, pinned by a test.
- `impact` over an indexed subject with no dependents still reports `seeds_dropped: 0`, pinned by a
  test on the same fixture — the two must be shown to differ, not merely asserted separately.
- A partial loss (one seed resolves, one does not) reports the count of the lost seeds.
- Every existing assertion on `seeds_dropped` is re-read and either still correct or corrected with
  the reason recorded; no expectation is updated to match new output without that reasoning.
- A decision recorded on task 100's `if not seeds` signing guard: kept, or removed with the
  replacement line shown.

## References
Found during task 100 (`docs/tasks/100_claim-signing-output-mode.md`, Phase 3 finding **F1**),
measured but deliberately not fixed there — outside that ticket's approved change list.
`code_atlas/store.py:1009-1011` (the early return), `code_atlas/tools/impact.py` (`_seeds`,
`_resolve_seed`). Related: [017](017_impact-engine.md) (the attestation itself),
[100](100_claim-signing-output-mode.md) (the workaround and the consumer that exposed this),
[065](065_empty-answer-cannot-explain-itself.md) (an empty answer must explain itself),
[075](075_read-symbol-confident-zero-on-unnormalised-qname.md) / [076](076_bare-name-subject-reads-as-absence.md)
(`classify_missing_subject`, already on this path).

---

## Session status

- **Phase:** 5 — Finalise (complete). **Next action:** review and merge
  [PR #117](https://github.com/cuongdinhngo/code-atlas/pull/117). The run stopped at the PR; there is
  no auto-merge.
- **KEY:** 102 · **branch:** `fix/102-impact-absent-subject-not-a-zero`
- **STRUCTURE:** native
- **TRACK:** backend
- **SCOPE:** M
- **TIER:** full
- **work_doc_mode:** embed (plain local-file ticket, hand-authored — not a scaffold stub)
- **BASELINE:** **green** — `scripts/docker-test.sh` on untouched `main` @ `b7e3b4b`: ruff · mypy ·
  `pytest -q` → **1262 passed**, exit 0. Definition of Done is therefore plain green, not delta-green;
  no baseline exclusion is carried.
- **Lane:** `/mango:autorun --no-challenger` — unattended lane, same phases and same gates, each closed
  on the counted artifact the phase emits rather than on a human typing "go". No auto-merge: the run
  stops when the PR exists.
- **Challenger:** OFF — waived by the `--no-challenger` argument. Reviewer agent still runs.
- **Handover authorisation:** the maintainer's standing, durable approval in `AGENTS.md`
  (*Maintainer workflow*) names exactly the two outward actions this lane needs — **push the feature
  branch**, **open the PR**. Nothing else: a merge, a force-push, a tracker transition or a release
  stops the run.
- **Autonomous-run envelope:** `RUN CONTRACT v1` at `.mango/run-contract-102.txt`, written and parsed
  back by `<mango>/scripts/run_contract.py` — **4** conditions (the 3 shipped floor conditions +
  `DOCS-TOKEN-ROW`), **1 UNBOUND** (`TREE-COMPARISON`'s paths) until Gate 2. `RECONCILE` at t0:
  `4 declared | 3 re-run | 0 holding | 3 BROKEN | 1 UNBOUND` — nothing struck, so every bound condition
  was observed in its failing state before any work existed. Merge strategy read from recent
  first-parent topology: **squash-or-rebase** (20 first-parent commits since the newest merge commit),
  so the floor uses a tree comparison and an ancestry predicate is refused.
- **Budget:** call-ceiling **unknown** — per-call estimate 4011 from 2 ledger rows (002, 003; 331 calls),
  but no token budget was supplied and this host does not surface main-loop usage. Recorded as unknown;
  nothing invented, nothing blocked.

---

## Phase 0 — Refine

`PREMISE: 22 reference(s) checked | 0 missing | 2 ambiguous (surfaced, not blocking)`
`RECALL: 10 claim(s) surfaced | 0 by symbol | 9 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 5 unresolved surfaced | 2 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise check.** Every source this ticket cites as already existing resolves.
Code: `code_atlas/store.py` and the early return verbatim at `:1009-1011`, `ImpactResult`
(`store.py:133`), `code_atlas/tools/impact.py` with `_seeds` (`:109`), `_resolve_seed` (`:131`),
`classify_missing_subject` (imported `:11`, defined `tools/nav_result.py`), the `seeds_dropped` field
(`impact.py:79`, `store.py:1015`), task 100's signing guard `if not sign or not seeds`
(`impact.py:83`), and the three nav reasons `no_such_symbol` / `not_indexed` /
`name_not_qualified` (`nav_result.py:33/34/41`). Docs: PLAN §12 (`docs/PLAN.md:392`); tasks 017, 061,
065, 075, 076, 100 all present under `docs/tasks/`; rules R1.1, R3, R4 present in
`docs/ENGINEERING_RULES.md`.
**Ambiguous (2, non-blocking):** *"any test asserting `seeds_dropped == 0`"* is a set, not a named
identifier — located anyway (`tests/test_impact.py`, `tests/test_claim_signing.py`); and *"the
documented way to interpret an empty `impact` answer"* is prose framing of 065, never a falsified
premise. **PREMISE HOLDS.**

**Scan finding that reshapes one Scope bullet.** `store.seeds_dropped` today counts **budget-pruned
seeds only** — it is assigned in exactly one place, `store.py:1050-1051`, when
`len(ordered_seeds) > max_nodes`. An unresolvable subject never reaches the store at all: `_seeds`
drops it (`impact.py:117`, `resolved is not None`) and an unknown *path* yields no rows
(`impact.py:123`). So the Scope bullet *"Multi-seed partial loss — check whether this already works or
shares the bug"* resolves to **shares the bug**, and it is not the early return alone: the count is
lost one frame upstream, solo seed or not. The early return at `:1010-1011` is the second half of the
same hole.

**Recalled claims (advisory — injected nothing, blocked nothing).**
By handle (9), matched on the shape of the change (a **shared payload vocabulary** extended, and a
**value threaded through callers** — the drop count is produced in the tool and consumed in the
payload): `do-not-attest-past-the-payloads-resolution` (100-C4 — *this ticket is the fix for that
claim's own evidence: its `evidence:` line is this bug*), `source-the-caveat-from-the-computation`
(100-C1 — the count must come from the computation that dropped the seed, not from the payload the
store returned), `route-must-answer` (093-C4, area *tool payloads / 065 / 075 / 076* — an answer the
reader cannot use is worse than none), `prove-the-guard-fails` (093-C3 → R6.5 — the new counter is a
guard and must be observed failing), `derived-not-listed-invariant` (095-C1, 093-C2, 097-C1 → R6.7 —
any test touching the reason vocabulary derives its set), `try-instead-tool-name` (093-C1 — a
machine-readable field holds one register), `re-run-the-sweep-after-the-last-edit` (100-C3 — process,
applied at execute).
By area (1): `100-C5` (type 5, area *impact / store* — seeds are returned inside `results`, so
`answer == seeds` is the modelled zero; the same payload this ticket makes honest).
Does not apply: `skip-dynamic-means-unlinkable`, `sibling-meta-non-int` (store/census accessor),
`scope-by-key-not-by-file`, `pin-the-table-a-purity-claim-rests-on`, `late-writer-outside-the-delta`,
`invert-the-rewrite-the-lookup-applies` (incremental delta), `structural-silence-over-stateful-latch`,
`hook-event-is-part-of-the-contract` (hooks), `lossless-repair-for-a-checkable-artifact`,
`increment-on-the-common-path`, `identity-check-misses-substance` (the promote pass itself).

**WANT-decisions asked (2) — both answered by the operator, both settled (no `ASSUMED` carried).**
- **W1 — does an empty `impact` answer say *why*?** Asked in want-language (*"should the empty answer
  also say why, or is the non-zero drop count enough?"*). **Settled: say why.** An answer that lost
  every subject carries a nav `reason` (`no_such_symbol` / `name_not_qualified` / `not_indexed`)
  alongside `seeds_dropped >= 1`, matching what 065 promised and what 075/076 already do —
  `classify_missing_subject` is on this path already, so no new query (R4). The common non-empty
  answer stays untouched (061). This is an **acceptance-bar** decision (it changes what counts as
  done for Scope bullet 2), so the tie-breaker files it as a want, not as a cited how.
- **W2 — does task 100's signing refusal stay?** **Settled: keep it.** A failed query still gets no
  quotable `claim` line; the line's word is `answer=0`, and signing that for a subject the index never
  held reads as a modelled zero to anyone who quotes it out of context. This closes the ticket's last
  AC (*"a decision recorded: kept, or removed with the replacement line shown"*) as **kept, with the
  reason recorded** — and it is a payload-surface decision the operator owns, not a derivable one.

**HOW-decisions (resolved + cited, 3).**
1. **The drop is counted tool-side and added to the store's count; the early return is not the fix on
   its own.** Cited the ticket's own Scope bullet 1 (*"`store.impact_radius` cannot see what `_seeds`
   discarded, so this is likely a tool-side count"*), the scan finding above
   (`store.py:1050-1051` is the sole assignment), and **R1.4** (`store.py` owns SQLite; the tool owns
   its payload — pushing subject resolution into the store would cross that boundary).
2. **An *ambiguous* seed counts as dropped, not only an absent one.** Cited `_resolve_seed`
   (`impact.py:131-140`), which returns `None` for both *"neither matches exactly nor resolves
   uniquely"*, and the ticket's Scope bullet 1 (*"A requested seed that does not resolve must be
   counted"*) — which is written about resolution, not about absence.
3. **An unknown *path* seed counts too, not just an unknown qname.** Cited the ticket's own multi-seed
   example `impact(paths=[a, b])` (Scope bullet 4) and `_seeds` (`impact.py:120-127`), where a path
   with no indexed nodes contributes nothing and is silently forgotten by the same mechanism.

**Direction, not tool.** Both wants were put as directions the operator can feel (*does the empty
answer explain itself* / *does a failed query get a quotable line*); where the count is incremented
and how the reason is attached are analysis's and design's calls, resolved above by citation.

**Epic detection:** single deliverable, one tool's payload — **ticket path**, `TIER: full` (a
behaviour change to a documented number under R3, touching store + tool + tests + docs; not lite).

**Exposure-checker dispatch: NOT run.** refine's 1-dispatch ticket-blind exposure check was not
dispatched — the challenger is OFF for this run by argument, and this session carries a standing
instruction against subagent dispatch except where the invocation names one. Disclosed rather than
silently skipped; same treatment as tickets 100 and 101. **Consequence, stated plainly:** nothing
independent re-derived this ticket's decision surface, so `REFINE: 5 unresolved surfaced` is a
self-reported count with no second opinion behind it.

---

## Phase 1 — Analysis

`PREMISE: 22 checked | 0 missing | 2 ambiguous` *(carried forward from Phase 0 — not re-run)*
`RECALL: 10 claim(s) surfaced | 0 by symbol | 9 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)` *(carried forward)*
`STRUCTURE: native`
`TRACK: backend — 0/7 touched files under UI paths`
`SCOPE: M`
`TIER: full`
`BASELINE: green — 1262 passed on main @ b7e3b4b (ruff · mypy · pytest, exit 0)`
`SECTIONS: 7 found (Goal · Root cause · Why this is worth a ticket · Scope/Deliverables · Constraints · Acceptance criteria · References) | 7 decomposed | ROWS: C=4 R=4 G=1 AC=5 (+3 evidence rows) = 17`
`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 8 applicable — 5 by change-type | 3 by recalled handle`

### Root cause — classified

**Cause class: `logic`** (`config.cause_taxonomy`). Two frames, one hole:

1. **`code_atlas/tools/impact.py:117`** — `_seeds` keeps a subject only when
   `resolved is not None`. A qname that neither matches exactly nor resolves uniquely is dropped
   here, and the `SubjectResolution` that explains *why* is computed one line earlier
   (`_resolve_seed`, `:139`) and thrown away. **`impact.py:120-127`** does the same for a path with
   no indexed nodes — it contributes no rows and no record that it was asked for.
2. **`code_atlas/store.py:1009-1011`** — the early return the ticket names. It is real, but it is the
   *second* half: by the time the store is called the dropped subjects are already gone.

**The count the ticket calls "the one number that separates a modelled zero from a failed query" is
today assigned in exactly one place — `store.py:1050-1051` — and only for a *budget prune*
(`len(ordered_seeds) > max_nodes`).** An unresolvable subject has never been counted, in any shape.
This resolves the ticket's own open question in Scope bullet 4 (*"check whether this already works or
shares the bug"*): **it shares the bug**, and not only via the early return — `impact(paths=[a, b])`
with `a` resolvable and `b` unknown returns `seeds_dropped: 0` today, with no early return involved.

### Requirements matrix

| ID | Source | Verbatim (abridged) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Goal | "`impact` answers a subject it cannot resolve at all with `results: []` **and** `seeds_dropped: 0` — the same pair it returns for a genuine modelled zero" | After the change the pair `results: [] + seeds_dropped: 0` means a modelled zero **and nothing else** | Reproduced by inspection: `impact.py:117` drops, `store.py:1050` is the only assignment | open |
| X1 | Root cause | "The empty-seed early return is taken **before** any counting" | Correct but incomplete — the drop is lost upstream in `_seeds`, solo or not | `impact.py:117`, `:120-127`; `store.py:1009-1011`, `:1050-1051` | evidence |
| X2 | Why a ticket | "**Every other reader of the payload is still misled** — including any agent reading `seeds_dropped` directly" | 100's guard protects one consumer; the payload field itself stays wrong | `impact.py:83` guard vs `impact.py:79` field | evidence |
| X3 | References | "Found during task 100 … Phase 3 finding **F1**, measured but deliberately not fixed there" | Provenance; also fixes the evidence line of lesson `100-C4` | `docs/LESSONS.md:51`; `docs/tasks/100_*.md` | evidence |
| R1 | Scope 1 | "A requested seed that does not resolve **must be counted** in `seeds_dropped`, including when it is the *only* seed" | Tool-side count added to the store's; covers absent **and** ambiguous (`_resolve_seed` returns `None` for both) and unknown **paths** | `impact.py:131-140`; refine H1/H2/H3 | open |
| R2 | Scope 2 | "Distinguish the two zeros … Consider whether a subject that resolved to *no seeds at all* also needs a `reason`" | **Settled by W1: yes.** An all-dropped empty answer carries a nav `reason`; the common answer is untouched | `nav_result.shape_exact_miss:396-406`; W1 | open |
| R3 | Scope 3 | "Re-examine task 100's guard … deciding whether it should go **is** [required]" | **Settled by W2: kept**, with the reason recorded — a failed query gets no quotable line | `impact.py:83`; W2 | open |
| R4 | Scope 4 | "`impact(paths=[a, b])` where `a` resolves and `b` does not must report `seeds_dropped: 1`" | Shares the bug — see Root cause; must be pinned by its own test | `impact.py:120-127` | open |
| C1 | Constraints | "**R4** — same index, same subject, same counts. No new query on the hit path" | `classify_missing_subject` already runs only after an exact-match miss (`_resolve_seed:137`), so the hit path pays nothing new | `impact.py:137-140`; R4.2 | open |
| C2 | Constraints | "**061** — the fix must not add a field to the common (non-empty, nothing-dropped) answer" | `seeds_dropped` already ships on every impact payload (`impact.py:79`); the new `reason` attaches **only** when the answer is empty and every subject was dropped | `impact.py:70-80`; `nav_result.nav_result:181` omits `reason` unless set | open |
| C3 | Constraints | "**R3** — changing what it counts is a **behaviour change to a documented number**. PLAN §12 and any test asserting `seeds_dropped == 0` must be **re-read**, not merely re-recorded" | Inventory B below (docs, N=3) and Inventory A (tests, N=3); each re-read with a recorded verdict | `docs/PLAN.md:425-427`; `README.md:216-218`, `:226-228` | open |
| C4 | Constraints | "**R1.1** — no language branch; resolution already runs through `classify_missing_subject`" | The classifier is language-neutral by construction (generic identifier lexis, `nav_result.py:286-289`); reuse it, add no branch | `nav_result.py:301-327` | open |
| AC1 | AC | "`impact` over a subject absent from the index reports `seeds_dropped >= 1`, pinned by a test" | Computed value for `qnames=["\App\Nope"]` is exactly **1** | AC validation below | open |
| AC2 | AC | "`impact` over an indexed subject with no dependents still reports `seeds_dropped: 0`, pinned by a test **on the same fixture** — the two must be shown to differ, not merely asserted separately" | One test, one fixture, both answers, an assertion that the two `seeds_dropped` values differ | `tests/test_claim_signing.py:137-149` shows the fixture already produces the modelled zero | open |
| AC3 | AC | "A partial loss (one seed resolves, one does not) reports the count of the lost seeds" | Computed value for one resolvable + one unknown is **1** | R4 row | open |
| AC4 | AC | "Every existing assertion on `seeds_dropped` is re-read and either still correct or corrected with the reason recorded" | Universal — **Inventory A, N = 3** (per-item checklist, not an aggregate) | grep over `tests/` | open |
| AC5 | AC | "A decision recorded on task 100's `if not seeds` signing guard: kept, or removed with the replacement line shown" | Falsifiable by artifact: the decision + its reason exist in this working doc | W2 (kept) | open |

### Universal inventory A — AC4's denominator (N = 3)

Every existing assertion on `seeds_dropped`, one row per item; review confirms **each**, not a total.

| # | Site | Asserts | Verdict after the change |
|---|---|---|---|
| A1 | `tests/test_impact.py:293` | `outcome.seeds_dropped == 1` after a **budget prune** (`max_nodes=2`, 3 seeds) | **Still correct, unchanged** — the store keeps counting budget prunes; this change adds a second contributor upstream, it does not move this one |
| A2 | `tests/test_claim_signing.py:145` | `found["seeds_dropped"] == "0"` on a resolved subject, modelled zero | **Still correct, unchanged** — nothing was requested that was not found |
| A3 | `tests/test_claim_signing.py:161` | `absent["seeds_dropped"] == 0` for `\App\Nope` | **Corrected to `== 1`** — this assertion *pins the defect*. Its docstring ("`seeds_dropped` stays 0 when no seed resolves, so the payload cannot tell an absent subject from a genuine zero") is the bug statement, and the reason for the surviving no-line guard changes with it (W2). Recorded as a **behaviour change**, not a golden bump |

### Universal inventory B — C3's denominator (N = 3)

Documented statements about what the number means. Historical records of a past *measurement*
(`PLAN.md:415`, `:750`; `BACKLOG.md:48`, `:195`, `:196`; `LESSONS.md:51`) are **not** in this
denominator — they describe what was true when measured and stay true as history.

| # | Site | Says | Verdict after the change |
|---|---|---|---|
| B1 | `docs/PLAN.md:425-427` | no line for an impact answer where no seed resolved, "**because** `impact_radius` returns `seeds_dropped = 0` for an empty seed set … so the payload cannot tell an absent subject from a genuine zero" | **Rewrite.** The stated *mechanism* becomes false; the *rule* survives on the W2 reason (a failed query is not an answer) |
| B2 | `README.md:216-218` | "`seeds_dropped=0` is what separates that zero from a query that found nothing because it asked wrong" | **Becomes true.** Today it is a promise the payload does not keep; after the change it is a fact. Worth one sentence saying the empty answer also names its reason |
| B3 | `README.md:226-228` | "When no line is emitted … an `impact` answer where no seed resolved" | **Kept, reason restated** (W2) |

### AC validation — every concrete value independently re-derived

| AC | Ticket's value | Recomputed | Match |
|---|---|---|---|
| AC1 | `seeds_dropped >= 1` for an absent subject | **exactly 1** — one requested subject, one drop (`_seeds` iterates `qnames` once) | ✅ (`>= 1` holds; the tighter `== 1` is what the test will pin) |
| AC2 | `seeds_dropped: 0` for an indexed subject with no dependents | **0** — confirmed live today by the passing `tests/test_claim_signing.py:145` on the same fixture | ✅ |
| AC3 | "the count of the lost seeds" for one-resolves-one-does-not | **1** | ✅ |
| AC4 | (no number stated) | **N = 3** — supplied by this phase, enumerated in Inventory A | ✅ (no mismatch; a denominator the ticket left open) |
| AC5 | (no number stated) | artifact-presence, falsifiable by grep | ✅ |

**Falsifiability.** 5 / 5 acceptance values are falsifiable (four by assertion, AC5 by artifact
presence). **0 manual-check exclusions recorded** — no AC needed one, so no coverage gap is carried
into design.

### Clarifications

`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision` — **Gate 0 clears.**

1. **Does a merged multi-subject answer carry a per-subject reason?** No — self-resolved. `impact`
   merges its seeds into one radius, which `docs/PLAN.md:438` already names as the live
   counter-example to 101's batch shape (*"`impact`'s seed merge (why 102 exists)"*). Resolution:
   attach the precise reason (via `nav_result.shape_exact_miss`, so `candidate_count` / `try_instead`
   / `untracked_path` ride along) **only when exactly one subject was requested**; for >1 subject
   attach the base classification `no_such_symbol` with no per-subject refinements — the weakest
   statement true of every dropped subject. Cited `100-C4` (*do not attest past the payload's
   resolution*) and `nav_result.py:396-406`.
2. **Does an unknown *path* seed use the same classifier as a qname?** Yes — self-resolved.
   `classify_missing_subject` is already path-shaped-subject aware: `_untracked_match_keys`
   (`nav_result.py:338-347`) branches on `PurePosixPath.suffix`/`stem`, which task 092 added for
   exactly this. One mechanism, no new branch (C4/R1.1).
3. **Does R3.1 require a `contract_version` bump?** No — self-resolved. R3.1 covers *node/edge
   vocabulary, fields, or qname convention*; `seeds_dropped` and `reason` are **tool payload**
   fields. Direct precedent in `docs/PLAN.md:453`: *"`reason=subject_ambiguous` (tool vocab in
   `NAV_REASONS`, not a `CONTRACT_VERSION` bump)"*. The change is still a documented-number behaviour
   change (C3), which is why Inventories A and B exist.
4. **Does `store.py`'s early return change?** No — self-resolved. At the store's own level
   `ImpactResult([], 0, 0)` is honest: nothing was walked and nothing was budget-pruned. The store
   cannot see a subject `_seeds` never passed it, and making it see one would push subject resolution
   into the SQLite layer, against **R1.4**. Cited `store.py:1009-1011`, `:1050-1051`.
5. **Is the `\App\Nope` answer still unsigned?** Yes — settled by **W2** at refine (kept, with the
   reason restated: the line's word is `answer=0`, and a question that was never answered should not
   acquire a quotable artifact).

### RULE SECTIONS — coverage from both sources

`RULE SECTIONS: 8 applicable — 5 by change-type | 3 by recalled handle — §1 (change-type) ✅ · §3 (change-type) ✅ · §4 (change-type) ✅ · §6 (change-type) ✅ · §7 (change-type) ✅ · R5.4 (handle try-instead-tool-name, PROVISIONAL) ✅ · R6.5 (handle prove-the-guard-fails) ✅ · R6.7 (handle derived-not-listed-invariant, PROVISIONAL) ✅ — N/A: §2, §8`

- **§1 Architectural boundaries** — constrains `impact.py` and `store.py`. **R1.1:** the drop count
  and the reason both come from `classify_missing_subject`, whose matching lexis is generic
  (`nav_result.py:286-289`); no `if language` is added. **R1.4:** the count lives in the tool, not in
  the store — see clarification 4.
- **§3 Contract** — constrains the payload change. **R3.1:** no `contract_version` bump (clarification
  3). **R3.2:** every reason value is imported from `nav_result`'s constants; no list is re-declared.
- **§4 Determinism** — constrains C1. **R4.2:** the classifier is a pure function of stored rows and
  the subject string; subject order is the caller's, so identical input gives identical counts.
  **R4.1:** no network/LLM.
- **§6 Testing** — constrains AC1–AC4. **R6.1:** tool change → tests over a fixture repo (the
  `indexed_repo` fixture already used at `tests/test_claim_signing.py:137`).
- **§7 Change discipline** — constrains the doc surface. **R7.1:** smallest thing — no new module,
  no new payload field on the common answer. **R7.2:** PLAN + BACKLOG + this frontmatter updated.
  **R7.5:** comments ≤ 3 lines.
- **R5.4 (handle `try-instead-tool-name`, PROVISIONAL)** — matched by the recalled handle
  `try-instead-tool-name` (093-C1). Constrains R2: if the empty answer attaches a route it must come
  from the existing `attach_name_not_qualified` / `attach_untracked_not_indexed` emitters, whose
  routes are registered tool names with prose kept in the `try_instead_hint` sibling. **Surfaced, not
  gate-blocking** — it is unratified, so a design that did not satisfy it would route through the
  `codify` ratify nudge rather than block Gate 1. This design does satisfy it.
- **R6.5 (handle `prove-the-guard-fails`)** — matched by the recalled handle (093-C3). The new
  counter is a guard: it must be **observed failing** against the pre-fix shape, recorded, not merely
  asserted green. Codified (not provisional) — this one does bind.
- **R6.7 (handle `derived-not-listed-invariant`, PROVISIONAL)** — matched by the recalled handle
  (095-C1/093-C2/097-C1). Constrains any test that touches the reason vocabulary: derive the set from
  `nav_result.NAV_REASONS`, never re-type members. Surfaced, not gate-blocking.
- **§2 Standard over sample** — `N/A because no adapter source is touched` (the change is core-only:
  `code_atlas/tools/`, tests, docs).
- **§8 Dependencies** — `N/A because no dependency is added or changed` (stdlib + existing modules).

**Uncodified standards applied at a gate: 0.** Every judgment above cites a codified or explicitly
provisional rule; nothing new is being enforced, so there is nothing to route through `codify`.

### Blast radius

- **Entry point:** `impact` (`code_atlas/tools/impact.py:26`), reached from `main.py`'s tool
  registration.
- **Producers/consumers of the changed value, traced (not grepped by name alone):**
  `_seeds` → `impact()` → `nav_result(..., seeds_dropped=…)` → the payload, and → `claim.sign`'s
  `CLAIM_CARRY` (`impact.py:20`), which already carries `seeds_dropped` onto the signed line. No other
  tool constructs a `seeds_dropped`; `store.impact_radius` is called from `impact.py:64` only.
- **Tests touching the value:** the 3 sites in Inventory A. **Docs:** the 3 sites in Inventory B.
- **Repos touched:** `app` (the single repo in `config.repos`).
- **Fan-out:** Explore agents **not dispatched** (session standing instruction). The blast radius above
  was traced by direct read of every call site rather than a name grep — `store.impact_radius` and
  `seeds_dropped` each have a single producer, both read in full.

### Gate 1 — self-audit

`RECALL:` carried forward, injected and blocked nothing · 7/7 sections decomposed · every acceptance
value falsifiable, 0 bare `✅`, 0 manual-check exclusions · `BASELINE: green` captured on the
untouched checkout · `j = 0` · Inventory A `N = 3` and Inventory B `N = 3` as per-item checklists ·
`RULE SECTIONS` emitted with each section's source and nothing bare · both ratified want-decisions
(W1, W2) are single-clause and each already carries its own matrix row (R2, R3) · `STRUCTURE: native`
· `TRACK: backend` · `SCOPE: M` · `TIER: full`.

**Gate 1 closes on the artifacts above** (autorun lane): `SECTIONS 7 found = 7 decomposed`,
`RULE SECTIONS` every applicable section answered or N/A-with-reason, `BASELINE` captured,
`CLARIFICATION … j = 0`.

---

## Phase 2 — Design

`HANDLES: 6 recalled | 6 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`SCOPE: M` *(unchanged from analysis)*
`Proving test: tests/test_impact.py::test_absent_subject_and_modelled_zero_differ_on_seeds_dropped`

### Pre-change measurement — the red state, run before any edit

Run now against a two-node planted graph (a `\Changed` class with one `\Caller`), so the ticket's
claim is re-measured on this checkout rather than quoted from task 100:

```
$ python3 - <<'PY'  (impact over a live GraphStore; full script in Phase 3)
absent          results=0 seeds_dropped=0 reason=None
modelled-zero   results=1 seeds_dropped=0 reason=None
partial-qnames  results=2 seeds_dropped=0 reason=None
partial-paths   results=2 seeds_dropped=0 reason=None
```

Four things this settles, none of them assumed: the ticket's headline reproduces; the modelled zero
is `results=1` (the seed itself — `100-C5`), **not** `results=0`, so AC2's fixture assertion must be
written against `seeds_dropped`, not against an empty `results`; **both** partial-loss shapes report
`0`, so Scope bullet 4 shares the bug in its qname form as well as the ticket's path form; and no
`reason` is attached anywhere on this path today.

### Approach

Count the drop **where the drop happens** — in the tool, one frame above the store — and let the
existing miss-classifier explain it.

1. **`_resolve_seed` returns a `SubjectResolution`, never `None`.** An exact match short-circuits to
   `SubjectResolution("resolved_unique", qname, 1)` **before** the classifier runs, so the hit path
   pays no new query (C1/R4). A miss returns whatever `classify_missing_subject` already computed —
   the information the current code discards one frame later.
2. **`_seeds` returns `_SeedSet(seeds, dropped)`** — a `NamedTuple` of the resolved seeds and one
   `SubjectResolution` per requested subject that produced **no** rows: a qname that resolves to
   nothing or to many, and a path `nodes_by_file_all` answers empty. A subject whose rows are all
   already `seen` is **not** dropped (it was found; it was a duplicate).
3. **`impact()` reports `outcome.seeds_dropped + len(seed_set.dropped)`** — the store's budget-prune
   count *plus* the tool's lost-subject count. Both causes are real drops of a requested seed, which
   is what the field is documented to mean; the store's own count and its early return are left
   untouched (clarification 4, R1.4).
4. **When nothing resolved, the empty answer says why** (W1). `_explain_lost_subject` attaches the
   reason **only** when `seed_set.seeds` is empty and `seed_set.dropped` is not — i.e. every subject
   the caller named was lost. One subject → `nav_result.shape_exact_miss`, verbatim, so
   `no_such_symbol` / `name_not_qualified` (+ `candidate_count` + `try_instead: search_symbol`) /
   `not_indexed` (+ `untracked_path` + `try_instead: build_or_update_index`) all arrive from the
   machinery 075/076/092 already ship. More than one subject → the base `no_such_symbol` and no
   per-subject refinement, because a merged radius cannot carry one reason per subject
   (`100-C4`: do not attest past the payload's resolution).
5. **Task 100's signing guard stays** (W2), re-expressed as `if not sign or not seed_set.seeds`. Its
   *stated reason* changes: not "the payload cannot tell the two apart" (it now can) but "a question
   that was never answered should not acquire a quotable `answer=0` line".

**Why the drop count is not moved into the store.** `store.impact_radius` receives a list of qnames.
It cannot distinguish "the caller asked for nothing" from "the caller asked for three subjects and
none resolved" — that distinction exists only where subject resolution happens, which is the tool.
Pushing resolution down would put `classify_missing_subject` inside the SQLite layer, against R1.4.

### Rejected alternatives

1. **Fix the early return in `store.py:1010-1011` alone** (the ticket's first reading). Rejected:
   measured above, `partial-qnames` and `partial-paths` both report `0` **without ever reaching that
   return**. It would fix one shape of the bug and leave two.
2. **A new `seeds_unresolved` field beside `seeds_dropped`.** Rejected on 061 + R7.1: it adds a field
   to a payload for a case the existing field already names, and every reader documented to consult
   `seeds_dropped` (PLAN §12, README, task 065) would still be misled by the old one.
3. **A new `no_such_path` reason for a dropped path subject.** Rejected on R7.1/R3: it grows the
   payload vocabulary for one case, and `classify_missing_subject` already answers a path-shaped
   subject usefully — including the genuinely valuable `not_indexed` + *"git add the untracked file,
   then rebuild"* when the path is an untracked indexable file (092). **Recorded limitation:** a
   truly unknown path therefore reports `no_such_symbol`, which is true at the class level ("nothing
   by that name is in the index") but is not path-specific. `file_outline` has the same gap today
   (it returns `found: false` with no reason at all), so this is a surface-wide follow-up, not a
   regression this ticket introduces.
4. **Return per-subject reasons for a multi-subject impact call** (101's batch shape). Rejected as
   out of scope: `impact` merges its seeds into one radius by design, which `docs/PLAN.md:438`
   already records as the live counter-example to the batch shape. Changing that is a different
   ticket.

### Assumptions

| # | Assumption | Tag | Evidence |
|---|---|---|---|
| 1 | `classify_missing_subject` accepts a **path-shaped** subject without raising and returns something useful | **verified by spike** | Ran it live: `no/such/file.php → status='absent' → {'reason': 'no_such_symbol'}`; `isEnabled → status='ambiguous', candidates=2 → {'reason': 'name_not_qualified', 'candidate_count': 2, 'try_instead': 'search_symbol'}` |
| 2 | `shape_exact_miss` mutates-and-returns, so it can be applied to a built `nav_result` payload | verified | `nav_result.py:396-406`; the same call shape as `find_callers.py:190` |
| 3 | A `resolved_unique` resolution can never reach the dropped list (where `shape_exact_miss` would mislabel it `name_not_qualified`, `candidate_count: 1`) | verified | `_seeds` appends to `dropped` only on `status != "resolved_unique"`; the spike shows exactly that mislabelling would occur otherwise, which is why the branch is on `status`, not on `qname is None` |
| 4 | `nodes_by_file_all` returns a `list`, so emptiness is testable without consuming an iterator | verified | `store.py:1706-1712` → `list[Row]` |
| 5 | Attaching `reason` cannot break `test_minimal_is_a_strict_reduction_of_standard` | verified | The attach is independent of `detail_level`, so the key appears in both payloads; `set(minimal) <= set(standard)` holds |

**0 unresolved `novel-untested` third-party/runtime assumptions.**

### Change list — smallest complete set, each row traced

`Ph2 covered by: 14/17 matrix rows` (X1–X3 are evidence rows and carry no change by design).

| # | Change | File / area | Blast radius | Ph2 covered by |
|---|---|---|---|---|
| 1 | `_resolve_seed` returns `SubjectResolution` (never `None`); exact hit short-circuits before the classifier | `code_atlas/tools/impact.py:131-140` | Sole caller is `_seeds` (trace T2) — no other module imports it | R1, C1, C4 |
| 2 | `_seeds` returns `_SeedSet(seeds, dropped)`; a lost qname **or** a path with no rows records its resolution | `impact.py:109-128` | One external caller: `tests/test_qname_subject_honesty.py:161-164` asserts on its return value → folded in as row 6 | R1, R4 |
| 3 | `impact()` reports `outcome.seeds_dropped + len(seed_set.dropped)` | `impact.py:61-80` | `CLAIM_CARRY` (`impact.py:20`) already carries the field, so a signed **partial-loss** answer now says `seeds_dropped=1` on its quotable line — intended, and the reason row 7 exists | G1, R1, R4, C2 |
| 4 | New `_explain_lost_subject` helper: reason attached only when every named subject was lost | `impact.py` (new, ~8 lines) | `test_mcp_server.py:397` (minimal ⊆ standard — holds, assumption 5); the 075/076 sweep at `test_qname_subject_honesty.py:139-154` | R2, C2, C4 |
| 5 | Guard restated `not seed_set.seeds`; the three comment/docstring sites carrying the now-false rationale rewritten (`impact.py:47-49`, `:81-82`, `:134-135`) | `impact.py` | Docstrings are read by the R1.1 CI grep-gate (`100-C3`) — the sweep must be re-run after this edit, not before | R3, C3 |
| 6 | **Proof collateral:** `impact._seeds(...) == [...]` → `impact._seeds(...).seeds == [...]` | `tests/test_qname_subject_honesty.py:161-164` | none identified | R1 |
| 7 | **Proof collateral:** A3 — `absent["seeds_dropped"] == 0` → `== 1`, docstring rewritten to state the surviving reason for the no-line guard; `CLAIM_KEY not in absent` kept | `tests/test_claim_signing.py:152-162` | none identified | AC4, AC5, R3 |
| 8 | New tests: the absent-vs-modelled-zero pair (**proving test**), partial loss in both shapes, store-prune + tool-drop summed, and the attached reason | `tests/test_impact.py` (new functions) | none identified — additive | AC1, AC2, AC3, R2, R4 |
| 9 | Add `impact` to the 075/076 *"no tool returns absence with `reason: ok`"* surface sweep | `tests/test_qname_subject_honesty.py:139-154` | The sweep's denominator grows by one tool; it now covers `impact` | R2 |
| 10 | Rewrite the mechanism sentence (B1) — the no-line rule survives on the W2 reason | `docs/PLAN.md:425-428` | none identified | C3 |
| 11 | B2 becomes a fact rather than a promise; B3's reason restated | `README.md:216-218`, `:226-228` | none identified | C3 |
| 12 | Status → `done` in both places + Token-usage row with the PR link | `docs/BACKLOG.md`, this file's frontmatter | **`tests/test_backlog_bookkeeping.py:75` requires a token row with a `[#N]` PR link for any task whose frontmatter says `done`** — so this row lands **after** the PR exists, and the full gate is re-run at that final SHA (see Ordering) | R7.2, AC4 |

### Answering every recalled type-2 handle (binding)

`HANDLES: 6 recalled | 6 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| # | Handle (claims) | Answer |
|---|---|---|
| H1 | `source-the-caveat-from-the-computation` (100-C1) | **traced** — `grep -rn "seeds_dropped" --include=*.py code_atlas/ tests/` → `store.py:138,1015,1051,1150`; `impact.py:20,47,79,82,135`; `test_claim_signing.py:135,145,153,161`; `test_impact.py:293`. The value is produced at `store.py:1051` (budget prune **only**) and read at `impact.py:79`. This claim is the design: the new count is sourced from the **computation that dropped the subject** (`_seeds`), not from the payload the store returned. All 5 test/doc consumers are folded into the change list (rows 7, 8, and Inventory A) |
| H2 | `do-not-attest-past-the-payloads-resolution` (100-C4) | **traced** — same command; `impact.py:20` `CLAIM_CARRY = ("seeds_dropped", …)` is the single consumer that signs over this value, and `impact.py:83` is the guard. Answered two ways: the multi-subject reason is deliberately the *base* class (change-list row 4) because a merged radius cannot resolve per-subject, and the signing guard is **kept** (W2), so nothing is attested past what the payload can distinguish |
| H3 | `route-must-answer` (093-C4) | **traced** — `grep -n "TRY_INSTEAD_[A-Z_]* =\|try_instead" code_atlas/tools/nav_result.py` → `:69 file_outline`, `:71 search_symbol`, `:80 build_or_update_index`, plus the two `*_HINT_*` prose siblings and the emitters at `:363`, `:387-388`. Every route this change can emit arrives through `shape_exact_miss`, so it is one of those three registered tool names and never `impact` itself; the prose stays in the `try_instead_hint` sibling |
| H4 | `try-instead-tool-name` (093-C1 → R5.4 PROVISIONAL) | **traced** — same command and output as H3. This change adds **no new route constant and no new emitter**: it reuses `attach_name_not_qualified` / `attach_untracked_not_indexed` unchanged, so the one-register rule is satisfied by construction rather than by a new judgment |
| H5 | `derived-not-listed-invariant` (095-C1, 093-C2, 097-C1 → R6.7 PROVISIONAL) | **traced** — `grep -rn "NAV_REASONS" --include=*.py code_atlas/ tests/` → `nav_result.py:45` (the definition) and `tests/test_nav_reason_codes.py` derives from it. No new member is added to `NAV_REASONS` (rejected alternative 3), and the new tests assert against the imported constants `REASON_NO_SUCH_SYMBOL` / `REASON_NAME_NOT_QUALIFIED` — no member is re-typed as a literal |
| H6 | `re-run-the-sweep-after-the-last-edit` (100-C3) | **traced** — `grep -n "def test_\|assert" tests/test_backlog_bookkeeping.py` → `:64 test_status_matches_in_both_places`, `:75 test_a_finished_task_records_what_it_cost` (requires `[#N]` + a spend naming `dispatch`/`fresh`). Change-list row 12 therefore **arms a test after the code is green**, exactly the shape 101 was bitten by. Folded into the Ordering below as a binding step: the full Docker gate re-runs at the **final** SHA, after the bookkeeping commit |

### Ordering (binding — derived from H6)

1. Commit code + tests + PLAN/README (rows 1–11). Frontmatter status `in-progress`.
2. Full Docker gate → delta-green recorded.
3. Push the branch, open the PR *(the two pre-authorised outward actions)*.
4. Commit row 12: status `done` in both places + the Token-usage row carrying `[#N]`.
5. **Re-run the full Docker gate at that final SHA** and record *that* number as the delta-green
   claim. Push.

### Rule compliance

| Rule | How this design complies |
|---|---|
| R1.1 | No language branch added. Both new branches key on `SubjectResolution.status` and on list emptiness; the classifier's matching lexis is the generic `[A-Za-z0-9_]` run at `nav_result.py:286-289` |
| R1.4 | The count and the reason live in the tool; `store.py` is not touched at all |
| R3.1 | No `contract_version` bump — tool payload fields, and no new `NAV_REASONS` member (precedent `PLAN.md:453`) |
| R3.2 | Reason values imported from `nav_result`; no list re-declared |
| R4.2 | Identical input → identical counts: subject order is the caller's, resolution is a pure function of stored rows, and `dict.fromkeys` ordering in the store is untouched |
| R5.4 (PROVISIONAL) | No new route constant or emitter (H4) |
| R6.1 | Tool change → tests over a fixture repo (`tests/test_impact.py`'s planted graph) |
| R6.5 | Every new assertion is **observed failing** first — the pre-change measurement above is the recorded red state; Phase 3 re-runs it per assertion |
| R6.7 (PROVISIONAL) | No re-typed vocabulary member (H5) |
| R7.1 | No new module, no new payload field on the common answer, no new reason vocabulary |
| R7.2 | PLAN, README, BACKLOG + frontmatter updated (rows 10–12) |
| R7.5 | The new helper carries a 3-line docstring; the rewritten comments stay ≤ 3 lines |
| 061 | The common answer (non-empty, nothing dropped) is byte-identical: `seeds_dropped` already shipped, and `reason` attaches only when every named subject was lost |

### Verification plan — proof at the layer where each requirement can fail

| ID | Risk layer | Proof artifact | Layer-match |
|---|---|---|---|
| AC1 (absent → `seeds_dropped >= 1`) | integration (tool + SQLite store + classifier) | integration test on a live `GraphStore` fixture — `test_absent_subject_and_modelled_zero_differ_on_seeds_dropped` | ✅ |
| AC2 (indexed subject, no dependents → `0`, **shown to differ**) | integration | the **same** test, same fixture, both calls, plus an assertion that the two values differ | ✅ |
| AC3 (partial loss → count of lost seeds) | integration | `test_partial_loss_counts_the_seed_that_was_lost` — both shapes (`qnames`, and the ticket's `paths=[a, b]`) | ✅ |
| AC4 (every existing assertion re-read) | logic + repo-state (3 named sites) | per-item: A1 & A2 proven by the **existing** tests still passing in the full gate; A3 by its corrected assertion. Verdicts recorded in Inventory A | ✅ |
| AC5 (decision recorded on 100's guard) | artifact + integration | the W2 decision recorded in this doc **and** the behaviour pinned by the surviving `CLAIM_KEY not in absent` assertion (`test_claim_signing.py:162`) | ✅ |
| R2 (empty answer explains itself) | integration | reason asserted in the proving test, **plus** `impact` added to the 075/076 surface sweep (row 9) | ✅ |
| R1 (drop counted where it happens) | integration | `test_budget_pruned_and_lost_seeds_are_summed` — proves the tool count is **added to** the store's, not substituted for it | ✅ |

**No `❌` rows. 0 coverage-gap exclusions recorded** — nothing is deferred to a manual check.

### Proving test

`tests/test_impact.py::test_absent_subject_and_modelled_zero_differ_on_seeds_dropped`

The assertion that fails pre-change and passes post-change: on one planted fixture, an absent subject
returns `seeds_dropped == 1` while an indexed subject with no dependents returns `seeds_dropped == 0`,
and the two are asserted **to differ**. Pre-change both are `0` (measured above), so the
differ-assertion is the one that goes red.

Invocation (full gate, the only supported way to run the suite):

```
scripts/docker-test.sh pytest -q tests/test_impact.py::test_absent_subject_and_modelled_zero_differ_on_seeds_dropped
```

### Rollback + porting

**Rollback:** `git revert` the branch's commits, or delete the branch before merge — the change is
confined to one tool module, three test files and three docs. No migration, no stored data, no index
rebuild: `seeds_dropped` is computed per call, so an existing `.code-atlas/graph.db` is unaffected in
both directions. **Porting:** `config.repos` holds one repo (`app`), and no adapter is touched, so
there is nothing to port.

### Gate 2 — self-audit

`HANDLES: 6 recalled | 6 traced | 0 does not apply | 0 unanswered` (`u = 0`, `h = t + x`) · every
change-list row traces to a matrix row (`14/17`, the 3 uncovered being evidence rows) · every
assumption tagged, the one runtime assumption **resolved by spike** · proving test named, runnable,
and at the risk layer · verification plan has **no ❌** and no coverage-gap exclusion · rollback and
porting recorded · `SCOPE: M` unchanged, no tier crossing.

**Gate 2 closes on those artifacts.** `TREE_PATHS` bound to `code_atlas tests docs README.md`.

---

## Phase 3 — Execute

Branch `fix/102-impact-absent-subject-not-a-zero` off `main` @ `b7e3b4b`.

### Every new assertion observed failing first (R6.5 / `prove-the-guard-fails`)

The five new tests were run against the **pre-change** `impact.py` (stashed) before it was restored:

```
$ git stash push -- code_atlas/tools/impact.py
$ scripts/docker-test.sh pytest -q tests/test_impact.py
>       assert payload["seeds_dropped"] == 1
E       assert 0 == 1
tests/test_impact.py:440: AssertionError
=========================== short test summary info ============================
FAILED tests/test_impact.py::test_absent_subject_and_modelled_zero_differ_on_seeds_dropped
FAILED tests/test_impact.py::test_partial_loss_counts_the_seed_that_was_lost
FAILED tests/test_impact.py::test_budget_pruned_and_lost_seeds_are_summed - a...
FAILED tests/test_impact.py::test_two_lost_subjects_carry_only_the_class_the_payload_can_prove
FAILED tests/test_impact.py::test_an_under_qualified_lost_subject_names_its_candidates
5 failed, 13 passed in 0.99s
```

**5 / 5 new assertions red on the pre-change source**, each on the count it exists to protect — not
one of them passes vacuously. The 13 pre-existing tests in that file stayed green throughout, which
is the negative control: the red is the new behaviour, not a broken fixture.

### Post-change behaviour, measured

Same probe as Phase 2, re-run after the change:

```
absent          results=0 seeds_dropped=1 reason='no_such_symbol'      claim=no
modelled-zero   results=1 seeds_dropped=0 reason=None                  claim=no
partial-qnames  results=2 seeds_dropped=1 reason=None                  claim=no
partial-paths   results=4 seeds_dropped=1 reason=None                  claim=no
ambiguous       results=0 seeds_dropped=1 reason='name_not_qualified'  claim=no   candidate_count=2 try_instead='search_symbol'
two-lost        results=0 seeds_dropped=2 reason='no_such_symbol'      claim=no
signed-partial  results=2 seeds_dropped=1 reason=None                  claim=yes
signed-absent   results=0 seeds_dropped=1 reason='no_such_symbol'      claim=no
```

`modelled-zero` is the row that matters as much as `absent`: it is **unchanged** — same count, no
`reason`, no new key — so the common answer stayed byte-identical (061/C2). `signed-partial` shows
the improvement riding onto the quotable line for free (`CLAIM_CARRY` already carried the field), and
`signed-absent` shows W2's guard still refusing to sign a question nothing answered.

### Delta-green (baseline `green`, 1262 on `main` @ `b7e3b4b`)

```
$ scripts/docker-test.sh
All checks passed!                                   (ruff)
Success: no issues found in 41 source files          (mypy)
1267 passed in 71.02s (0:01:11)                      (pytest)
```

**1267 passed, 0 failed — 1262 baseline + 5 new tests, none removed, none skipped.**
*(Re-run at the final SHA after the bookkeeping commit — see Phase 2 Ordering step 5; this number is
true for the code commit and is restated there.)*

### Axis 1 — file set

```
$ git status --porcelain
 M README.md
 M code_atlas/tools/impact.py
 M docs/PLAN.md
 M docs/tasks/102_impact-cannot-tell-an-absent-subject-from-a-zero.md
 M tests/test_claim_signing.py
 M tests/test_impact.py
 M tests/test_qname_subject_honesty.py
?? .mango/

$ git diff --stat
 README.md                          |  10 +-
 code_atlas/tools/impact.py         | 100 +++-
 docs/PLAN.md                       |  19 +-
 docs/tasks/102_….md                | 511 +++++++++++++++++++++
 tests/test_claim_signing.py        |   7 +-
 tests/test_impact.py               | 104 ++++-
 tests/test_qname_subject_honesty.py|   6 +-
 7 files changed, 720 insertions(+), 37 deletions(-)
```

**`diff ⊆ approved change list` ✅** — 6 source/doc files, all named at Gate 2 (rows 1–11), plus this
working doc. Row 12 (BACKLOG + frontmatter) is deliberately still absent: it lands after the PR
exists, per the binding Ordering. `.mango/` is the run envelope — **untracked and never committed**.

Hunk → matrix row: `impact.py` imports + `_SeedSet` + `_resolve_seed` + `_seeds` → R1/C1/C4;
`impact()` count + `_explain_lost_subject` → G1/R1/R2/R4/C2; guard + docstrings → R3/C3;
`test_impact.py` → AC1/AC2/AC3/R2/R4; `test_claim_signing.py` → AC4(A3)/AC5/R3;
`test_qname_subject_honesty.py` → R1 (proof collateral) + R2 (surface sweep); `PLAN.md`/`README.md` → C3.

**Stray-reference sweep:**

```
$ grep -rn "_seeds(" --include=*.py code_atlas/ tests/
code_atlas/tools/impact.py:82:            seed_set = _seeds(
code_atlas/tools/impact.py:132:def _seeds(
tests/test_qname_subject_honesty.py:163:        assert impact._seeds(
tests/test_qname_subject_honesty.py:166:        assert impact._seeds(…).seeds == []
code_atlas/tools/find_orphans.py:47 · reach_shared.py:18 · reachable_from.py:51 · test_reachability.py:284,286
```

Zero stray references. The four `entry_seeds` hits are a **different function** in
`reach_shared.py`, correctly untouched — named here so the reviewer can see they were checked rather
than missed.

```
$ grep -rn "stays 0\|cannot tell an absent" --include=*.py --include=*.md code_atlas/ tests/ docs/PLAN.md README.md
tests/test_untracked_files_are_invisible.py:5: … ``dirty_indexed_files`` stays 0 — a different question (073).
```

The one survivor is about a different field in a different tool. Every statement of the old, now-false
rationale is gone from the code, the tests and the two docs.

### Axis 2 — design conformance, per Gate-2 Approach bullet

| Approach bullet | Verdict |
|---|---|
| 1. `_resolve_seed` returns `SubjectResolution`, exact hit short-circuits before the classifier | **implemented-as-approved** (`impact.py:154-162`) |
| 2. `_seeds` returns `_SeedSet(seeds, dropped)`; lost qname **or** empty path recorded; duplicate ≠ drop | **implemented-as-approved** (`impact.py:132-151`) |
| 3. `impact()` reports `outcome.seeds_dropped + len(seed_set.dropped)` | **implemented-as-approved** (`impact.py:100`) |
| 4. Reason attached only when every named subject was lost; one subject → `shape_exact_miss`, many → base class | **implemented-as-approved** (`impact.py:101-102`, `:165-175`) |
| 5. 100's guard kept, re-expressed on `seed_set.seeds`, stated reason corrected | **implemented-as-approved** (`impact.py:103-106`) |
| Ordering (from H6) | in progress — steps 1–2 done, 3–5 pending |

### Deviations recorded

**D1 — `docs/PLAN.md` gained a new paragraph, not only the approved sentence rewrite.** Change-list
row 10 approved *"rewrite the mechanism sentence (B1)"*. The diff also **adds** a paragraph
documenting what `seeds_dropped` now counts and when `reason` appears. Traced to **C3** (R3: a
behaviour change to a documented number must be re-documented, not merely re-recorded) and **R7.2**.
Recorded as a deviation rather than absorbed, because it is an addition Gate 2 did not enumerate.
Additive, docs-only, no code effect. **Surfaced to review for adjudication.**

No other bullet deviated; no `deviated` behaviour sits under the clean Axis-1 diff.

### `Ph3/4 proven by` — progress

| Row | Proven by | State |
|---|---|---|
| G1, R1, R4, AC1, AC2, AC3 | `tests/test_impact.py` ×5 (red-then-green, both pastes above) | ✅ Ph3 |
| R2 | the reason assertions + `impact` added to the 075/076 surface sweep | ✅ Ph3 |
| R3, AC5 | W2 decision recorded (Phase 0) + `test_claim_signing.py:162` still pins `CLAIM_KEY not in absent` | ✅ Ph3 |
| AC4 | A1 & A2 green in the 1267 run, unmodified; A3 corrected with its reason recorded | ✅ Ph3 (3/3) |
| C1, C2, C4 | `modelled-zero` row unchanged in the probe; no `if language`; hit path unchanged | ✅ Ph3 |
| C3 | B1/B2/B3 rewritten (3/3); Inventory A re-read (3/3) | ✅ Ph3 |
| X1, X2, X3 | evidence rows — no change by design | n/a |

---

## Phase 4 — Review ✋

`CHALLENGER: OFF (--no-challenger)` · reviewer: `mango:reviewer` (Sonnet — `cost_tier: standard`,
diff not security-tagged and touching no auth / data access / schema migration) · read-only and
ref-based against `main..fix/102-impact-absent-subject-not-a-zero`, run in place at the reviewed SHA.

**Round 1 verdict: CHANGES REQUESTED — conditional LGTM on finding 1.** One Important finding, no
Critical. Scope reconciled clean on both axes: all 7 touched files map onto approved rows 1–11, no
hunk outside the list, no untouched-line reformatting, `docs/BACKLOG.md` correctly absent per the
deferred row 12.

### Finding 1 (Important) — a resolvable subject reported as an absent one, in the paths slot

The reviewer found the `qnames` loop guarded `classify_missing_subject`'s `resolved_unique` status
while the `paths` loop appended whatever came back. **Verified rather than accepted** — the same
subject string, measured on a live fixture:

```
impact(qnames=["App\Nope"]) -> results=2 seeds_dropped=0 reason=None
impact(paths=["App\Nope"])  -> results=0 seeds_dropped=1 reason='name_not_qualified' candidate_count=1
```

Confirmed, and reachable on today's PHP adapter — no TS speculation needed. The classifier re-points
an under-anchored subject (075/076), so a `paths` subject could resolve to a real qname and still be
counted lost; being the only drop, `shape_exact_miss` then labelled it `name_not_qualified` with
`candidate_count: 1`, because `resolved_unique` always carries a count of 1. **This is the defect
class the ticket exists to remove, reintroduced inside the fix for it** — assumption 3 at Gate 2 held
for the `qnames` path and I did not re-check it for the `paths` path I added.

**Landed** in `52ff0d1`. The reviewer's snippet duplicated the guard inside the paths loop; the fix
instead factors the rule into one `take()` closure both slots call, so the two cannot drift apart
again — same semantics, one site. Pinned by
`tests/test_impact.py::test_a_path_subject_that_resolves_uniquely_is_a_seed_not_a_drop`, observed
failing first:

```
$ git stash push -- code_atlas/tools/impact.py && scripts/docker-test.sh pytest -q tests/test_impact.py
>       assert by_path["seeds_dropped"] == 0
E       assert 1 == 0
FAILED tests/test_impact.py::test_a_path_subject_that_resolves_uniquely_is_a_seed_not_a_drop
1 failed, 18 passed in 1.87s
```

### Adjudications

- **Deviation D1** (`docs/PLAN.md` gained a paragraph, not only the approved sentence rewrite) —
  **accepted** by the reviewer under R7.2 and the AGENTS.md docs-before-PR rule: documenting a
  changed number's new semantics is required, not scope creep. Recorded rather than absorbed.
- **Minor observation, no action** — the multi-drop branch always emits the base `no_such_symbol`
  even when one lost subject individually classified `untracked` or `ambiguous`. Deliberate and
  Gate-2 approved ("many → base class"), pinned by
  `test_two_lost_subjects_carry_only_the_class_the_payload_can_prove`.

### Verify-only re-review (main loop, no re-dispatch)

The fix touched only `code_atlas/tools/impact.py` (approved row 2) and `tests/test_impact.py`
(approved row 8) — inside the approved set, so no scope change and no second dispatch.

1. **Named fix present as described** ✅ — one rule for both slots, shared rather than duplicated.
2. **Affected proof re-run** ✅ — red above, then the full gate below.
3. **Regression scan over the Phase-1 blast radius** ✅ — all 8 test modules that touch `impact`
   (`test_impact`, `test_claim_signing`, `test_qname_subject_honesty`, `test_mcp_server`,
   `test_reachability`, `test_config`, `test_schema_version_recovery`, `test_view_databag_decision`)
   green in the full run.

```
$ scripts/docker-test.sh
All checks passed!                            (ruff)
Success: no issues found in 41 source files   (mypy)
1268 passed in 62.70s (0:01:02)
```

**1268 passed** against the `BASELINE: green — 1262` on `main` @ `b7e3b4b`: +6 new tests, none
removed, none skipped, no new failure.

### Layer-match re-confirmation

Every row of the Gate-2 verification plan is re-confirmed at its risk layer: all seven proofs are
integration tests over a live `GraphStore`, none sits below the layer where its requirement can
fail. **No layer-match `❌`, and no coverage-gap exclusion was recorded or needed.**

### `Ph3/4 proven by` — k / N

| Requirement | Proven by | k/N |
|---|---|---|
| G1, R1, R2, R4, AC1, AC2, AC3 | `tests/test_impact.py` ×6, each observed red first | 7/7 |
| R3, AC5 | W2 decision recorded + `test_claim_signing.py:162` pins the surviving guard | 2/2 |
| AC4 — Inventory A, **per item** | A1 `test_impact.py:298` unchanged & green · A2 `test_claim_signing.py:145` unchanged & green · A3 corrected to `== 1` with the reason recorded | **3/3** |
| C3 — Inventory B, **per item** | B1 `PLAN.md` · B2 + B3 `README.md` | **3/3** |
| C1, C2, C4 | probe: the modelled-zero answer is unchanged; no new query on the hit path; no `if language` | 3/3 |

`k = N` on both universal inventories; no aggregate stands in for a per-item check.

### Gate 4 result

**clean (reviewer only — `CHALLENGER: OFF`).** Stated plainly: the ticket-blind challenger did not
run, so **no independent party re-derived the requirements from the raw ticket**. That criterion is
not met — it is *absent*. What did happen is a rule-book review that found a real Important defect
which the run's own author had missed, and that defect was confirmed by measurement before being
fixed.

`Reviewed at 52ff0d1b620d3db81f0734937820f36392b1b90a`
Reviewed files: `code_atlas/tools/impact.py` · `tests/test_impact.py` · `tests/test_claim_signing.py` ·
`tests/test_qname_subject_honesty.py` · `docs/PLAN.md` · `README.md`.
Working doc (exempt from the staleness comparison): this file,
`docs/tasks/102_impact-cannot-tell-an-absent-subject-from-a-zero.md` (`work_doc_mode: embed`).

---

## Phase 5 — Finalise ✋

**Stale-review guard: not stale.** `git diff --name-only 52ff0d1..HEAD` → empty; the only uncommitted
change is this working doc, which is exempt by definition. `pr_checklist_path` is `null`, so the
project finalise-checklist hook is skipped.

### Learning loop

`CLAIMS: 3 claim(s) from 1 lesson entr(ies) | T1=0 T2=2 T3=1 T4=0 T5=1 T6=0 | 0 unclassified`

The entry was bundled — a process claim, a code claim, a project fact and a harness gap in one
paragraph — and is split into: **102-C1** (`re-verify-the-assumption-on-a-new-path`, type 2,
process), **102-C2** (`one-rule-for-every-subject-slot`, type 2, code), **102-C3** (type 5, area
*impact / store / tool payloads*), and the type-3 **SG-2** signal below. The T-counts total 4 across
3 lessons-file claims plus 1 skill-gap signal, which is not written to `lessons_path`.

`RECURRENCE: 8 recurring | 0 superseded (0 retired) | 3 promotion candidate(s)`

Per `AGENT_BRIEF.md` **P1**, a claim's `seen:` grows when its handle is **answered traced**, not when
a lesson is written. All 6 recalled handles were answered `traced` (0 `does not apply`), so `102` is
appended to all 8 backing claim records in the same commit: `100-C1`, `100-C3`, `100-C4`, `093-C1`,
`093-C2`, `093-C4`, `095-C1`, `097-C1`. The 3 promotion candidates are the handles not yet carried by
a rule: `source-the-caveat-from-the-computation`, `re-run-the-sweep-after-the-last-edit`,
`do-not-attest-past-the-payloads-resolution`.

`FALSIFY: 3 candidate(s) checked | 3 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`

1. **`source-the-caveat-from-the-computation`** — still true, and this run is its sharpest instance:
   the count had to be sourced from the computation that dropped the subject, not from the payload
   the store returned. Cheaply checkable: `grep -rn "seeds_dropped" code_atlas/` shows one producer
   against several readers. **Checked, not merely repeated** — measured by live probe this run.
2. **`re-run-the-sweep-after-the-last-edit`** — still true, and it *changed this run's plan*: it
   produced the binding Ordering, because `tests/test_backlog_bookkeeping.py:75` is armed by the
   bookkeeping commit itself. Cheaply checkable: compare the SHA of the recorded gate run to `HEAD`.
3. **`do-not-attest-past-the-payloads-resolution`** — still true. Note carefully: **102 removed this
   claim's cited evidence** (the payload can now tell the two apart) — but that is the claim being
   *honoured by fixing the payload*, not falsified. It bound again here, in the decision that a
   merged multi-subject radius states only the base class it can prove for every subject.

`RECURRING-T2: 8 type-2 claim(s) with seen ≥ 2 | 8 routed to a destination | 0 cannot promote | 0 left in lessons_path`

| Claim (handle) | seen | Destination |
|---|---|---|
| 093-C1 `try-instead-tool-name` | 092, 093, 100, 101, 102 | already promoted → `ENGINEERING_RULES.md` **R5.4** |
| 093-C2 / 095-C1 / 097-C1 `derived-not-listed-invariant` | 093 … 102 | already promoted → **R6.7** |
| 093-C4 `route-must-answer` | 093, 101, 102 | `rulebook_path` — per **P2** the substance is **already in R5.4**; propose *widening R5.4's citation*, not a new rule |
| 100-C1 `source-the-caveat-from-the-computation` | 100, 101, 102 | `rulebook_path` (code subject) — candidate for `/mango:promote` |
| 100-C3 `re-run-the-sweep-after-the-last-edit` | 100, 101, 102 | `agent_brief_path` (process subject) — candidate for `/mango:promote` |
| 100-C4 `do-not-attest-past-the-payloads-resolution` | 100, 101, 102 | `rulebook_path` (code subject) — candidate for `/mango:promote` |

`l = 0`, `n = d + b` (8 = 8 + 0). **Cross-ticket promotion is `/mango:promote`'s pass, not this
phase's** — recurrence across tickets is invisible from inside one ticket, and this run only names
the candidates. Run it between tickets.

`PROMOTION: 3 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md, docs/AGENT_BRIEF.md | mango files written: 0`

**0 ratified is correct, not an omission:** the handover authorisation covers exactly two outward
actions (push the branch, open the PR) and grants no claim ratification. Every claim is written
`status: proposed (awaiting human confirm)`; nothing entered the rule book or the agent brief.

**Type-3 signal:** `SG-2 — design's Assumptions table has no per-call-path denominator`, recorded in
`docs/SKILL_GAP_CANDIDATES.md`. It names a check the phase could have run with what it already had —
enumerate the call paths that will consume the assumption *after* the change and record
`verified k/N paths`; this run's would have read **1/2** and blocked. **No mango file was written.**

### Cost ledger

| Dispatch | Tokens | Detail |
|---|---|---|
| `mango:reviewer` round 1 | **89.4k, measured** | 27 tool-uses, 356 s. Returned CHANGES REQUESTED / conditional LGTM with 1 Important finding — real, confirmed by measurement, and fixed |
| verify-only re-review | **0 — not dispatched** | Main-loop by default: the fix stayed inside approved rows 2 and 8, so no scope change and no second dispatch |
| `challenger` | **0 — waived** by `--no-challenger` | |
| refine exposure-checker | **0 — not dispatched** | Session standing instruction; disclosed, not silently skipped |
| analysis Explore fan-out | **0 — not dispatched** | Same; the blast radius was traced by direct read of every call site instead |

`LEDGER TOTAL: 89.4k dispatch · top cost driver: mango:reviewer round 1 (the only dispatch)`

**Scope, stated honestly:** the ledger measures **subagent dispatch only**. Main-loop spend — which
every recent row in this repo records as unmeasured, and which was the real cost here (the two Docker
gate runs, the probes, the working doc) — is **not measured by mango** on this host. No
dispatch-vs-noise split is claimed. For the output-noise side, `rtk gain` is the optimizer's own
analytics; RTK is live in this session and mango does not self-instrument the main loop.

**Ledger completeness gate:** 1 dispatch made, 1 dispatch row, and every row carries a real value or
an explicit reason. **Complete.**

### Delta-green at the FINAL SHA (100-C3, `re-run-the-sweep-after-the-last-edit`)

101's review finding was that a delta-green claim can be true when measured and stale when
committed, because the docs commit itself arms `tests/test_backlog_bookkeeping.py`. So the gate was
re-run **after** the bookkeeping commit `100db2e`, not quoted from before it:

```
$ scripts/docker-test.sh          # at 100db2e — status: done + the [#117] token row present
All checks passed!                            (ruff)
Success: no issues found in 41 source files   (mypy)
1268 passed in 94.54s (0:01:34)
```

The only commit after `100db2e` adds these lines to this working doc. No test reads the working
doc's body — `test_backlog_bookkeeping.py` reads a task file's `status:` frontmatter and the BACKLOG
tables, neither of which that commit touches — so this number is not stale for any gate.

### Revert path

Branch `fix/102-impact-absent-subject-not-a-zero`; commits `3078739` (code + tests), `94a7a10`
(PLAN/README + working doc), `52ff0d1` (review finding 1), plus the bookkeeping commits below.
`git revert` any of them independently, or delete the branch before merge. Nothing persists: no
migration, no stored data, no index rebuild — `seeds_dropped` is computed per call, so an existing
`.code-atlas/graph.db` is unaffected in both directions.

### RECONCILE — the closing artifact

```
RECONCILE
  conditions: 4 declared | 4 re-run | 3 holding | 1 BROKEN | 0 UNBOUND
  proven    : 2 shown BROKEN when forced | 4 shown HOLDING on a clean run
  phase     : close | challenger: off | branch: fix/102-impact-absent-subject-not-a-zero
    PR-EXISTS: HOLDING — OPEN
    TREE-COMPARISON: BROKEN
    LOCAL-HEAD-PUSHED: HOLDING
    DOCS-TOKEN-ROW: HOLDING
    PR-EXISTS: FORCE-UNPROVEN — `force-broken` ran but the check still reports HOLDING
    DOCS-TOKEN-ROW: FORCE-UNPROVEN — `force-broken` ran but the check still reports HOLDING
  READ THIS FIRST: a BROKEN condition describes the state of the world after the last push. It does
  not block the merge — this version stops at the PR and the human merges.
```

**Reading it.** `q = 1`, and the BROKEN condition is `TREE-COMPARISON` — `git diff --quiet main
<branch> -- code_atlas tests docs README.md` exits non-zero because the branch's change is **not in
`main`**. That is the expected and correct state for a run that stops at the PR; it flips to HOLDING
when the PR merges. The other three hold: the PR exists and is `OPEN`, local head equals the
remote's (nothing stranded), and the token row is in the table.

**Two conditions are `FORCE-UNPROVEN`, and that is a real weakness, not a formality.** `PR-EXISTS`
and `DOCS-TOKEN-ROW` were written with **no-op `force-broken` cases**, because forcing them would
mean deleting the PR or corrupting a committed doc — the first is on the abort list, the second
would leave the tree dirty after a push. So both were observed **holding**, never observed **failing**
at close, and a predicate never shown to fail is not evidence when it holds. Only `TREE-COMPARISON`
and `LOCAL-HEAD-PUSHED` were shown to flip both ways (`2 shown BROKEN when forced`). The forced pass
mutated `refs/remotes/origin/<branch>` by design; it was restored with `git fetch origin` and both
refs re-verified equal at `427031c` afterwards.

### Follow-ups drafted

**0 deferred (⚠) matrix rows**, so no follow-up ticket is owed by the matrix. Two items are recorded
for the maintainer's judgement rather than silently dropped:

1. **A path-shaped subject has no reason of its own.** An unknown path reports `no_such_symbol`
   (true at the class level, not path-specific), and `file_outline` returns `found: false` with no
   reason at all. A surface-wide `no_such_path` decision is a candidate ticket — deliberately not
   taken here (rejected alternative 3: vocabulary growth for one case).
2. **`/mango:promote`** has three type-2 classes at recurrence 3 waiting on a cross-ticket pass.

### DISCLOSURE — read this first in the morning

1. **CHALLENGER: OFF** — waived by `--no-challenger`. **Nothing independent re-derived the
   requirements from this ticket's raw text.** The clean verdict above is a reviewer-only result and
   is not evidence of independence. Weigh it against what did happen: the reviewer found a real
   Important defect the run's own author had missed.
2. **UNCHECKED AGENT CLAIMS: 0** — every value in the `RUN CONTRACT` was derived by a command whose
   real output the writer recorded.
3. **BUDGET: call-count ceiling unknown** — no token budget was supplied and this host surfaces no
   main-loop usage. A per-call estimate (4011, from ledger rows 002/003) exists but no ceiling was
   derivable, so none was invented and nothing was blocked. **A call-count ceiling would have been a
   proxy, not a measurement, in any case.**
4. **Two envelope conditions were never observed failing** — `PR-EXISTS` and `DOCS-TOKEN-ROW` carry
   no-op `force-broken` cases and are reported `FORCE-UNPROVEN`. Their HOLDING at close is weaker
   evidence than the other two conditions'. See RECONCILE above.
5. **Subagent dispatches deliberately not made:** refine's 1-dispatch exposure-checker, and
   analysis's Explore fan-out (`explore_fanout: true` in `.harness.json` permits it). Both skipped
   under this session's standing instruction against subagent dispatch, disclosed rather than
   silently skipped. **Consequence:** the exposure count (`REFINE: 5 unresolved surfaced`) and the
   blast-radius trace are both self-reported. The blast radius was mitigated by reading every call
   site directly instead of grepping names; the exposure count has no mitigation.
6. **A recorded limitation shipped:** an unknown *path* subject reports `no_such_symbol`, which is
   true at the class level but not path-specific. Rejected alternative 3 explains why; ticket
   candidate 1 in Follow-ups carries it forward.
7. **Deviation D1** (PLAN gained a paragraph beyond the approved sentence rewrite) was adjudicated
   **accepted** by the reviewer under R7.2. It is a docs-only addition, and it was recorded rather
   than absorbed.
8. **3 claim classifications and 3 promotion proposals are UNRATIFIED.** The handover authorisation
   covered two outward actions and grants no ratification, so every claim is written
   `status: proposed (awaiting human confirm)` and **nothing** entered the rule book or the agent
   brief. They need an explicit per-claim confirm.
9. **Outward actions deferred to the morning:** the **merge** (this lane never merges), any tracker
   transition, and any release. Only two outward actions were taken — the branch push and the
   PR-open — exactly the two the handover named.
10. **What no artifact in this run can check:** whether the *ticket itself* asked for the right
    thing. Every gate here measured conformance to the ticket, and the one independent check that
    would have questioned it was the challenger, which was off.
11. **`.mango/run-contract-102.txt` is untracked** and was never committed — the envelope lives
    outside the repo's history. `.mango/` is not in `.gitignore`, so it shows as an untracked
    directory in `git status` until you remove it.
