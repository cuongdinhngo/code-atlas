---
id: 246
slug: ensure-miss-refuses-on-the-count-of-drifted-files-not-on-the-subject
title: '`ensure_miss` returns `stale` whenever more than one indexed file has drifted, and 166 widened drift to `indexed_commit..HEAD`, so three commits on a feature branch make every zero-hit answer `index_stale` no matter which file it asked about — the tool teaches its users to finish all symbol work before their first commit, and the field has learned it as a habit'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [073, 166, 035, 057]
---

## Why this exists (field retro round 17)

035 made freshness result-driven and 073 added the miss-driven case: a query that matched nothing may
spend the per-call reparse budget on the sole dirty indexed file, because absence is the one answer a
drifted index can invent. Both are right, and both are bounded by `READ_THROUGH_CAP = 1`.

The bound is applied to the **count of drifted files**, not to the subject:

```python
candidates = dirty_indexed_paths(self.store, self.config)
if not candidates:      return "ok"
if len(candidates) > 1: return "stale"
return self.ensure(candidates[0])
```

`code_atlas/tools/freshness.py`. Then 166 — correctly — widened what counts as drift: `dirty_indexed_paths`
unions `indexed_commit..HEAD` with the working tree, so a file changed and *committed* after the build
also drifts. The two together compose into a refusal nobody chose: **commit three files on a feature
branch and `len(candidates)` is 3 forever**, so every zero-hit query answers `index_stale` — including
one about a file untouched by any of them, whose rows the index can still vouch for.

The retro records the consequence as a habit rather than a complaint: *"all my symbol work happened
before the first commit, by habit learned from an earlier round. That habit should not be necessary."*
It calls the global refusal on a three-file diff **the single most annoying property of the tool in
day-to-day use**, and the session's status payload confirms the trigger: `staleness` flipped to
`behind` at the first branch, with `head_ref` on a feature branch.

The retro's own framing — *"serve reads from a `behind` index"* — is not what the code does, and the
distinction matters for the fix. There is no global refusal: `staleness: "behind"` is a status field,
and `FreshnessGuard.ensure` is per path. What refuses is narrower and stranger: a **count** standing
in for a subject.

## Scope

- **Decide the refusal on the subject, not on the population.** A zero-hit query whose subject is
  nameable (a qname, a path) has a subject to check; the count of unrelated drifted files is not
  evidence about it. Where the subject genuinely cannot be named, the honest answer stays `stale`.
- **State what absence can and cannot be proven from.** This is the ticket's real question: a zero on
  a subject whose own file is current is still not proof that nothing *elsewhere* matches, and 073's
  refusal exists for that. Name the tier the answer may claim (R5.2: never the stronger one) and
  disclose the residue — *"checked this subject's file; N other indexed files have drifted"* — rather
  than refusing whole.
- **Revisit `READ_THROUGH_CAP` on the same evidence, or reject doing so in writing.** One reparse per
  call is a conservative bound chosen for "one adapter call"; an answer spanning two drifted files is
  `stale` today for the same structural reason. Measure before changing it.
- **Out of scope:** background or automatic rebuilds, raising the cap without a measurement, and any
  change to `staleness`'s vocabulary (047/077/202 settled it).

## Constraints

- **R5.2 / R5.6** — a partially verified answer is never signed as a verified one. If the answer
  claims less, it must say so in `reason`, not in prose only.
- **035 / 073** — per-call repair stays bounded; this ticket must not make one query reparse a branch.
- **R4.2** — deterministic: the same working tree yields the same rows and the same `reason`.
- **061** — a clean tree must produce byte-identical payloads.
- **Cost** — `dirty_indexed_paths` runs a git diff per call already; a subject-scoped check must not
  add a second traversal per answer. Measure on the anchor-scale index.

## Acceptance criteria

- A zero-hit query about a subject whose file is current, on a branch with three unrelated committed
  changes to indexed files, returns an answer whose `reason` states what was verified — pinned by a
  test that builds exactly that state.
- The unnameable-subject case still returns `stale`, asserted.
- A clean tree is byte-identical to today.
- A written verdict on `READ_THROUGH_CAP`, with the measurement behind it.
- The field habit is retired in evidence: the same sequence the retro describes (index, branch,
  commit three files, ask a symbol question) runs green in a test.

## References

Field retro round 17 (2026-09-11, maintainer-local) §3 and §5 ask 2 — note that ask 2's framing
("serve reads from a `behind` index") misstates the mechanism; the defect is the count-based refusal
above. Related: [035](035_read-through-freshness.md) (result-driven repair),
[073](073_freshness-cannot-find-what-is-not-indexed.md) (the miss-driven case and its cap),
[166](166_read-symbol-answers-from-pre-repair-state-and-calls-it-no-such-symbol.md) (widened drift to
the indexed commit), [047](047_staleness-scoped-to-indexed-files.md) / [077](077_index-cannot-name-the-revision-it-describes.md) / [202](202_a-killed-build-leaves-an-index-that-reports-current.md) (the `staleness` vocabulary, deliberately untouched).

## Token usage

| Phase | Tokens |
|---|---|
| autorun | unmeasured (see TOKEN_LEDGER 246) |

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Ticket:** 246
- **Type:** bug
- **Repo(s):** app
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed
- **working-doc path:** docs/tasks/246_ensure-miss-refuses-on-the-count-of-drifted-files-not-on-the-subject.md
- **branch:** feat/246-ensure-miss-subject-not-count
- **plugin:** mango 1.16.1 @ /home/you/.claude/plugins/cache/mango-plugins/mango/1.16.1 (candidates: 5)
- **reviewer:** off · **challenger:** on
- **Phase:** finalise

---

## Phase 0 — Refine

`PREMISE: 8 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 3 claim(s) surfaced | 1 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions — ticket locks subject-scoped refusal, residue disclosure, READ_THROUGH_CAP verdict, and concrete ACs; handover authorises approach choices.

**PREMISE detail.** Present: `code_atlas/tools/freshness.py` (`ensure_miss`, `READ_THROUGH_CAP`, `dirty_indexed_paths`), `read_symbol.py` / `search_symbol.py` miss call sites, tickets 035/073/166/047/077/202, R5.2/R5.6 in `docs/ENGINEERING_RULES.md`.

**INPUT KIND:** ticket (not epic).

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `166-C1` | 2 | symbol (`dirty_indexed_paths` / indexed-commit drift) | Yes — drift signal stays; refusal axis changes |
| 2 | `do-not-attest-past-the-payloads-resolution` | 2 | handle → R5.6 | Yes — residue must be payload-visible |
| 3 | freshness / tools area | 5 | area | Yes — miss-driven repair family |

**Exposure-checker:** skipped (refine skip: yes).

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=5 R=4 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why | count of drifted files stands in for the subject; multi-file branch → every miss is index_stale | Refusal axis is wrong (population vs subject) | `freshness.py:68-72` | D1 | proving + field-habit tests | open |
| C1 | Constraints | R5.2 / R5.6 — partial never signed as verified; say so in reason/payload | Residue field required when answering with subject-only check | ENGINEERING_RULES R5.6 | D2 | assert field present | open |
| C2 | Constraints | 035/073 — per-call repair stays bounded | Cap stays 1; subject-scoped ensure spends at most one reparse | `READ_THROUGH_CAP=1` | D1, D4 | cap tests still green | open |
| C3 | Constraints | R4.2 deterministic | Same tree → same rows + same residue count | ticket | D1 | fixture deterministic | open |
| C4 | Constraints | 061 clean tree byte-identical | No new keys when zero other drifted | ticket AC | D2 | identity test | open |
| C5 | Constraints | Cost — no second dirty traversal per answer | Reuse one `dirty_indexed_paths` call; stash residue on guard | ticket Cost | D1 | no extra git call in ensure_miss | open |
| R1 | Scope | Decide refusal on subject, not population | `ensure_miss(subject_path=…)` | ticket Scope | D1 | unit + integration | open |
| R2 | Scope | Disclose residue when subject file current | `other_indexed_files_drifted: N` on miss answer | ticket Scope | D2 | proving test | open |
| R3 | Scope | Unnameable subject stays stale | `subject_path is None` + multi dirty → stale | ticket Scope | D1 | assert test | open |
| R4 | Scope | Verdict on READ_THROUGH_CAP with measurement | Keep 1; write measurement | ticket Scope | D4 | design verdict | open |
| AC1 | AC | zero-hit + subject file current + 3 unrelated drifted → answer discloses what was verified | read_symbol path-qname; not index_stale | ticket AC | D1,D2 | proving test | open |
| AC2 | AC | unnameable subject still stale | bare search / namespace qname multi-dirty | ticket AC | D1 | assert test | open |
| AC3 | AC | clean tree byte-identical | no residue key | ticket AC | D2 | identity | open |
| AC4 | AC | written READ_THROUGH_CAP verdict + measurement | design section | ticket AC | D4 | work doc | open |
| AC5 | AC | field habit sequence green | index→branch→commit 3→ask symbol | ticket AC | D1,D2 | field-habit test | open |

## AC validation

| AC | Concrete value | Falsifiable? | Notes |
|----|----------------|--------------|-------|
| AC1 | 3 unrelated committed drifts; subject file unchanged; miss returns non-`index_stale` + `other_indexed_files_drifted==3` | yes | fixture builds exact state |
| AC2 | unnameable + >1 dirty → `index_stale` | yes | search bare name or `\Ns\X` |
| AC3 | clean tree payload keys/bytes match pre-change shape for same miss | yes | omit-when-empty |
| AC4 | written verdict keeps cap=1 with measured multi-file cost | yes | design text |
| AC5 | same sequence as retro green | yes | integration test |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## RULE SECTIONS

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1.1 (rules) ✅, §1.4 (rules) ✅, §4.2 (rules) ✅, §5.6 (rules) ✅, §6.1 (rules) ✅, §6.2 (rules) ✅, §6.5 (rules) ✅, §7.6 (rules) ✅`

- §1.1 — subject naming uses indexed `files.path` / path-shaped qname only; no language→path map in core.
- §1.4 — freshness owns the guard; callers only pass an optional path.
- §4.2 / §5.6 — residue count is deterministic and payload-visible; never claim full-index absence when N>0.
- §6.1/§6.2/§6.5 — proving test red-before; fixture encodes the field habit.
- §7.6 — prune superseded 166 AC2 expectation in the same commit as the behaviour change.

**BASELINE:** green — freshness suites 16 passed on untouched checkout (Linux + venv pytest).

---

## Phase 2 — Design

### Approach

Subject-scope `FreshnessGuard.ensure_miss(subject_path: str | None)`. When `subject_path` is an indexed file path: ignore unrelated dirty files for the refuse/repair decision; `ensure` only that path if it drifted; record `other_indexed_files_drifted = len(candidates) - (1 if subject in candidates else 0)` from the **same** `dirty_indexed_paths` list (C5). When `subject_path is None` (unnameable): keep today's count gate (`>1 → stale`). Callers derive a nameable path only when the qname's container (or the qname itself) is a row in `files` — path-shaped subjects — never via language mapping (R1.1). Miss answers attach `other_indexed_files_drifted` when >0 (061 omit-when-empty). Miss `reason` stays `no_such_symbol` / `no_matches`; the structured field is what states the verification tier (R5.6). `READ_THROUGH_CAP` stays 1.

### Rejected alternatives

| Alt | Why rejected |
|-----|----------------|
| Raise READ_THROUGH_CAP with dirty count | Ticket forbids raising without measurement; one call must not reparse a branch (035/073/101). |
| Soften unnameable multi-dirty to ok | Ticket: unnameable stays stale — absence elsewhere is unprovable. |
| PSR-4 / language path guess for namespace qnames | R1.1 — language branch in core. |
| New NavReason enum member | Miss type is still absence; residue is orthogonal (061 weight); field matches `subject_refreshed_only` precedent. |

### Assumptions

| Assumption | Tag |
|------------|-----|
| Path-shaped qnames (`files.path` prefix before `::`) cover the ticket's nameable-subject AC and the field-habit pin | verified — existing 166/073 fixtures already use `src/*.aa::…` |
| Namespace-shaped misses remain unnameable and correctly stay stale under multi-drift | verified — no files-table hit for `\App\…` |
| One `dirty_indexed_paths` call suffices (no second git traversal) | verified — residue computed from same list |

### HANDLES (recalled type-2)

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `do-not-attest-past-the-payloads-resolution` traced → command: `rg -n "other_indexed_files_drifted|subject_refreshed_only" code_atlas/tools/` → result: no residue field yet; `subject_refreshed_only` is the omit-when-empty precedent. Fix adds `other_indexed_files_drifted` on partial miss.
- `166-C1` traced → command: `rg -n "changed_paths|LAST_COMMIT" code_atlas/tools/freshness.py` → result: drift-vs-indexed-commit stays; only the `len(candidates)>1` refuse axis changes.

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

- AC1/AC5 proven on authored git fixtures (three committed drifts), not the anchor corpus (`real_corpus_path` unset). Expiry: re-run the field-habit sequence against the maintainer's anchor once `real_corpus_path` is set.

### Approved change list (diff ⊆ this)

1. `code_atlas/tools/freshness.py` — `ensure_miss(subject_path=None)`; `other_indexed_files_drifted` on guard; `nameable_subject_path(store, qname)` via `files` table; `ensure_qname` passes nameable path on miss.
2. `code_atlas/tools/read_symbol.py` — miss path: pass nameable path into `ensure_miss`; attach residue field on miss answers when >0.
3. `code_atlas/tools/search_symbol.py` — miss path: pass nameable path when query itself is an indexed path (rare); bare queries stay unnameable.
4. `tests/test_ensure_miss_subject_not_count.py` — proving tests: AC1/AC2/AC3/AC5 (+ supersede 166 AC2 for nameable subject).
5. `tests/test_freshness_cannot_find_what_is_not_indexed.py` — update `test_read_symbol_committed_multi_drift_is_index_stale_not_absent` to expect repair-of-subject (246 supersedes 166 AC2 for nameable path).
6. Docs: working doc READ_THROUGH_CAP verdict; BACKLOG/TOKEN_LEDGER/LESSONS at finalise; task frontmatter status.

### Proving test

`tests/test_ensure_miss_subject_not_count.py::test_miss_on_current_subject_amid_three_unrelated_drifts_discloses_residue`

### D4 — READ_THROUGH_CAP verdict (AC4)

**Keep `READ_THROUGH_CAP = 1`.** Measurement: on the AC1 fixture (4 indexed files, 3 drifted unrelated + 1 current subject), a single `dirty_indexed_paths` call returns 3 paths; subject-scoped ensure performs **0** reparses when the subject file is current and **1** when it is the drifted subject (166 supersession case). Raising the cap to 3 would reparse the whole branch on one miss — the cost 035/073/101 forbade. Written rejection of raising the cap is this paragraph.

### Verification plan

| AC | Layer | Command / proof | ❌? |
|----|-------|-----------------|-----|
| AC1 | integration | proving test | |
| AC2 | integration | unnameable multi-dirty → index_stale | |
| AC3 | integration | clean miss omits residue key | |
| AC4 | design | D4 paragraph above | |
| AC5 | integration | field-habit sequence test | |

---


## Phase 3 — Execute

### Verification sweep

`diff ⊆ approved list` — freshness.py, read_symbol.py, search_symbol.py, new proving test, updated 073/166 consumer test, working doc.

### Empirical evidence

R6.5 red-before (probe: count-gated `ensure_miss` while the proving test was present): asserting
`reason == no_such_symbol` failed with `index_stale` — recorded in session, not as tree-under-review
evidence.

Ran at c2f3c78d4210bcb4fdb394a6d4d56ab774c6adf4
```
$ /home/you/WORKSPACE/PROJECTS/code-atlas/.venv/bin/python -m pytest tests/test_ensure_miss_subject_not_count.py tests/test_freshness_cannot_find_what_is_not_indexed.py tests/test_nav_reason_codes.py::test_reason_vocabulary_includes_index_stale_unused -q
15 passed
```

- **AC1** ✅ proving test
- **AC2** ✅ unnameable bare search → index_stale
- **AC3** ✅ clean miss omits residue key
- **AC4** ✅ D4 READ_THROUGH_CAP verdict (keep 1)
- **AC5** ✅ field-habit fixture in proving test

Design-conformance: subject-scoped ensure_miss; residue field; no language path map; cap unchanged.

## Gate self-check lines (for check_lines)

`SECTIONS: 5 found (Why this exists · Scope · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=5 R=4 G=1 AC=5`
`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1.1 (rules) ✅, §1.4 (rules) ✅, §4.2 (rules) ✅, §5.6 (rules) ✅, §6.1 (rules) ✅, §6.2 (rules) ✅, §6.5 (rules) ✅, §7.6 (rules) ✅`
`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`


## Phase 4 — Review

Reviewer: OFF (waived by --no-reviewer).

Challenger (ticket-blind, first pass): 2 not-met — (1) partial verification not in reason; (2) CAP written verdict only in work doc; plus ensure_qname consumers missing residue. Follow-up commit added REASON_SUBJECT_FILE_CHECKED, CAP=1 comment on READ_THROUGH_CAP, and finalize_subject_checked_miss on find_* miss paths.

Design deviation: expanded change list to nav_result.py, coverage.py, find_callers/references/implementations/view_data, and NAV_REASONS pin tests — required by challenger attestation; still within ticket Scope.

Challenger follow-up: finalize now runs after shape_exact_miss on find_* miss paths.

Reviewed at 42c68493f916a12ef12929c023e8699da872c56e

### Review round 2 — maintainer review on PR #320

**Finding 1 (accepted, fixed): the residue crossed subjects on the batch path.** `_search_one`
read `guard.other_indexed_files_drifted` unconditionally, but one guard serves every subject of a
sweep (101) and only `ensure_miss` resets it. A subject with hits therefore inherited the drift
count of an earlier subject's miss. Measured before the fix, the same query batched and alone:

```
queries=["src/Subject.aa::MissingSymbol", "Subject"]
  → "Subject": {..., "total_count": 1, "other_indexed_files_drifted": 3}
queries=["Subject"]
  → "Subject": {..., "total_count": 1}                     # no residue key
```

A confident, complete answer gained a field (061), the field said something untrue about that
subject, and the payload depended on what else was in the call. Fixed by reading the residue only
where it is computed, inside the miss branch. Pinned by
`test_batch_residue_belongs_to_the_subject_that_earned_it`, red before the fix on exactly that
assertion.

**Finding 2 (accepted, fixed): the branch was pushed with `ruff check .` failing.** Two errors, both
in files this PR edits — an unused `REASON_RELATION_UNMODELLED_FOR_LANGUAGE` import left behind in
`test_empty_answer_cannot_explain_itself.py`, and a 102-character docstring in
`test_freshness_cannot_find_what_is_not_indexed.py`. `ruff` is the first CI job; no `scripts/gate.sh`
run is recorded in this working doc, and Actions cannot run here, so nothing reported it.

**Reviewed and accepted as correct:** the R1.1 boundary (`nameable_subject_path` walks `::` prefixes
against `files` and never maps a namespace, so `\App\Foo::bar` stays unnameable and stale — the
ticket's own "where the subject genuinely cannot be named, the honest answer stays `stale`"); the
`READ_THROUGH_CAP = 1` verdict and its measurement; the design deviation that added
`REASON_SUBJECT_FILE_CHECKED` after the challenger's first pass, which is recorded above and is the
right call — a structured field alone leaves `reason` claiming clean-tree absence (R5.2).

**Worth stating plainly for the field:** this retires the habit for **path-shaped** subjects. A bare
`search_symbol("Name")` on a three-commit branch still answers `index_stale`, because that query
names no file and absence elsewhere stays unprovable. The ticket asked for exactly that boundary; the
part of the field complaint that survives it is a different question.

```
$ scripts/gate.sh
20 passed · 0 failed · 0 skipped
GATE GREEN — all 20 checks passed
```

## Phase 5 — Finalise

CLAIMS: 2 claim(s) from 2 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified

FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)

RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)

RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (n/a) | 0 left in lessons_path

PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0

LEDGER TOTAL: unmeasured · top cost driver: challenger (3 rounds)

