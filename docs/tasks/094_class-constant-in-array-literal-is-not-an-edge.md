---
id: 094
slug: class-constant-in-array-literal-is-not-an-edge
title: 'A `::class` constant in a routing array is `relationship_not_modelled`, while a DYNAMIC tier sits unused'
phase: 1.5b
milestone: Coverage
status: done
depends_on: [030, 011, 002]
---

## Goal
The anchor repo's front controller builds a routing table whose values are `Foo::class` constants in
an array literal, then dispatches through a variable method name. Asked *who consumes this new
controller*, `find_references` answered `relationship_not_modelled`; asked on the method,
`no_matches`. Both are honest, and both leave the single most common "who wires this up" question in
a legacy PHP monolith unanswerable by the graph.

The model already has somewhere to put this. `edge_health` reports a `DYNAMIC` confidence tier
carrying **2,956 edges** on that index. A `Foo::class` constant in a literal array is a *textual,
unambiguous* mention of a class — strictly more information than nothing, and exactly what a
low-confidence tier is for. A `DYNAMIC`-tier hit with an honest tier label is better than a refusal.

## Evidence (field retro round 5, 2026-08-14, **real work**)
- 5 `find_references` calls across two new controllers produced three flavours of nothing;
  the question was answered by `grep` on one file (§7.1, §8 "lost" row).
- After commit + rebuild: `reason: "relationship_not_modelled"` for a class whose consumer references
  it as a `::class` constant in an array literal (§4 row 2).
- Retro's own verdict: **"partly wrong to be silent"** — `edge_health.by_tier.DYNAMIC` = 2,956 on the
  same payload, so the tier exists and is populated by other rules.
- Cost recorded: 5 calls and a wrong belief about *why* the answer was empty (§7.1).
- The evaluator's regression test asserts on the front controller's **source text** for the same
  reason — the repo's own test had to do by regex what the graph declined to model.
- Carve-out (a) in §10 exists because of this: *"not for routing tables built from `::class`
  constants plus variable-method dispatch — grep the front controller"*.

## Scope / Deliverables
- **Emit an edge for a `::class` constant used as a value**, at `DYNAMIC` confidence, from the
  enclosing declaration (file/function/method) to the named class. Start with the array-literal case
  that the field met; decide in design whether a bare `Foo::class` argument or assignment is in the
  same rule or a follow-up.
- **Name the edge kind honestly.** It is a *mention*, not a call and not an instantiation. Decide
  whether the existing indirection vocabulary (030) covers it or a new `edge_kind` is needed — a new
  kind is a contract change (R3) and must be justified against reusing one.
- **Make the tier legible at the answer.** A `find_references` result whose only hits are `DYNAMIC`
  must say so in a way an agent reads as *candidate list, not answer* — round 4's all-`HEURISTIC`
  hazard (§A carry-over) applies with more force at a lower tier.
- **Do not model the dispatch.** The variable-method invocation stays unmodelled; this ticket answers
  *which classes does this table name*, not *does control flow reach this action*. Say so in the
  ticket's resolution so the carve-out in §10 can be narrowed precisely, not deleted.
- **Re-measure the carve-out.** After the fix, the §7.1 question must be re-asked against the anchor
  index and the answer recorded here.

## Constraints
- R1.1 — the rule belongs in the **PHP adapter**; `::class` is PHP syntax and the core must not learn
  it. The core sees an edge with a tier, nothing more.
- R2 — encode the language construct, never the anchor repo's front controller or its route names.
  The fixture must be a generic array-of-`::class` table, not a copy of the repo's.
- R3 — a new `edge_kind` bumps `contract_version` and extends the conformance suite; reusing an
  existing kind does not.
- R4 — deterministic ordering of the new edges.
- Scale: the anchor index holds 1.79 M edges, 64 % already `HEURISTIC`. Measure the edge-count delta
  this rule adds before merging; a rule that inflates a low-confidence tier by a large factor makes
  every answer noisier and needs a cost verdict, not just a correctness one.

## Acceptance criteria
- A fixture with `['a' => Foo::class, 'b' => Bar::class]` produces `DYNAMIC`-tier edges to both
  classes, pinned by an adapter conformance test and a store-level test.
- `find_references` on `Foo` returns the mention with its tier, and the payload makes the tier's
  meaning legible without reading source.
- The edge-count delta on a full anchor build is recorded in this ticket (before/after totals and the
  `by_tier` breakdown).
- The `no_matches` answer for the variable-method dispatch is unchanged, and a test says so.
- §10's carve-out (a) is rewritten in the retro-derived docs to cover only the dispatch half.

## References
Field retro round 5 §7.1, §4 row 2, §8 ("Does the front controller reach `displayAction`?" — lost),
§10 carve-out (a); candidate 3.
Related: [030](030_alias-indirection-edges.md) (alias & literal-indirection edges — the precedent
rule), [011](011_resolver.md), [059](059_view-databag-edge.md) and
[062](062_view-databag-producer.md) (the last time a string-keyed seam was modelled),
[067](067_first-page-not-representative.md) (low-tier results read as answers).

## Resolution
**Kind:** reuse `REFERENCES` (already the mention vocabulary). No new `edge_kind`, no
`contract_version` bump. Added to `FQN_EDGE_KINDS` so the resolver links an FQN `target_raw`.
Leftover unlinked `REFERENCES` still feed `relationship_not_modelled` (065 planted rows unchanged).

**Scope of the construct:** every `Foo::class` `ClassConstFetch` (array value, argument, or
assignment). Array-only would encode the field's routing table (R2). `$obj::class` / `Foo::CONST`
are out.

**Tier:** `DYNAMIC`, as the ticket asked. `skip_dynamic` now still yields `REFERENCES` so a
linkable FQN is not dropped with `(dynamic)` CALLS. Linked tier stays `DYNAMIC` (`_weaker_tier`).

**Legibility:** per-hit `confidence_tier` + `authoritative: false` when every returned hit is
`DYNAMIC`. `reason` stays `ok`.

**Dispatch:** `$this->$action()` is unchanged (`no_matches` on `Foo::run`).

**§10 carve-out (a)** narrowed in PLAN §19 to the dispatch half only.

**Anchor delta:** not measured here (no private checkout). Coverage-gap exclusion; operator paste
of before/after `edge_health.by_tier` is a follow-up, not a merge gate (080/074).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 094 — class constant in array literal is not an edge (working doc)

- **Ticket:** 094 · local-file `docs/tasks/094_class-constant-in-array-literal-is-not-an-edge.md`
- **Type:** feature / coverage
- **Repo(s) / Porting:** app only
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `main` at `76bcac4` (097 merged). Docker delta-green recorded at execute.

---

## Phase 0 — Refine

`PREMISE: 14 reference(s) checked | 0 missing | 3 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 7 unresolved surfaced | 0 want-decision asked | 3 how-decision resolved+cited | 7 ASSUMED | skip: no`

Resolved: `find_references`, `relationship_not_modelled`, `no_matches`, `DYNAMIC`,
`REFERENCES` / `FQN_EDGE_KINDS` / `UNMODELLED_REFERENCE_KINDS`, `Visitor.php`, tickets
030/011/002/059/062/067, PLAN §8.2/§12/§19. Ambiguous: “anchor repo”, “§10 carve-out (a)”
(sentence lives on this ticket / PLAN §19, not a standalone retro file), “retro-derived docs”.

**INPUT KIND:** ticket. **work_doc_mode:** embed.

**Recalled:** `derived-not-listed-invariant`, `prove-the-guard-fails`, `try-instead-tool-name`,
`route-must-answer`.

**HOW (cited):**
1. Rule in the PHP adapter — R1.1 / ticket C.
2. Encode `ClassConstFetch` `::class`, not a front controller — R2 / ticket C.
3. Reuse `REFERENCES` unless a new kind is justified — ticket Scope + R3.

**ASSUMED (standing best-option, Gate 1):**

| # | Choice | Why |
|---|--------|-----|
| A | All-DYNAMIC page → `authoritative: false`; `reason` stays `ok` | 031/070 precedent; a new reason would look like failure |
| B | Reuse `REFERENCES` + add to `FQN_EDGE_KINDS`; `skip_dynamic` still yields `REFERENCES` | Ticket wants DYNAMIC *and* a find_references hit; resolver skipped all DYNAMIC |
| C | No new kind / no contract bump | `REFERENCES` is the mention vocabulary; 030 CALLS/NEW would lie |
| D | Carve-out rewrite in PLAN §19 + ticket Resolution | No standalone retro file; PLAN already cites 094 |
| E | Same rule for every `Foo::class`, not array-only | R2 |
| F | Anchor delta = coverage-gap (operator paste) | No private checkout; 080/074 |
| G | Variable-method dispatch stays unmodelled | Ticket Scope |

**Exposure-checker:** [Exposure-checker](8cb13c71-37d9-4298-807b-ed448dc18038) `UNEXPOSED: 4` ≡ A, B, C, D.

---

## Requirements matrix

`SECTIONS: 6 found | 6 decomposed | ROWS: C=5 R=5 G=2 AC=5`

| ID | Source | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------------|-----|-------|--------|
| G1 | Goal | Emit a mention edge at DYNAMIC | CL1–CL3 | proving parse test | ✅ |
| G2 | Goal | find_references answers who names this class | CL3–CL4 | proving nav test | ✅ |
| R1 | Scope | Edge from enclosing decl to named class | CL1 | fixture source_qname | ✅ |
| R2 | Scope | Honest kind; justify vs new | CL2 | REFERENCES, no bump | ✅ |
| R3 | Scope | Tier legible as candidate list | CL4 | authoritative:false | ✅ |
| R4 | Scope | Do not model dispatch | CL1 | callers no_matches | ✅ |
| R5 | Scope | Re-measure carve-out / rewrite §10 | CL5 | PLAN §19; AC3 gap | ⚠ |
| C1 | R1.1 | PHP adapter only | CL1 | Visitor.php | ✅ |
| C2 | R2 | Generic fixture | CL6 | class_const_mention.php | ✅ |
| C3 | R3 | New kind ⇒ bump | CL2 | no new kind | ✅ |
| C4 | R4 | Deterministic | CL1 | visitor order | ✅ |
| C5 | Scale | Measure anchor delta | — | coverage-gap | ⚠ |
| AC1 | Fixture both classes DYNAMIC | CL1, CL6 | proving parse + store | ✅ |
| AC2 | find_references + tier legible | CL4 | proving nav | ✅ |
| AC3 | Anchor before/after | — | Resolution | ⚠ |
| AC4 | Dispatch no_matches + test | CL6 | test_variable_method… | ✅ |
| AC5 | Carve-out dispatch-only | CL5 | PLAN §19 | ✅ |

`CLARIFICATION: 7 raised | 7 ASSUMED A–G | j=0`

---

## Phase 1 — Analysis ✋ Gate 1

- **Root cause:** `data` — adapter never emitted `::class`; `REFERENCES` was unlinked and skipped as DYNAMIC.
- **Handler:** Visitor `ClassConstFetch` + FQN opt-in + skip_dynamic exception + authoritative flag.
- **Gate 1:** cleared (standing approval, A–G)

---

## Phase 2 — Design ✋ Gate 2

- **Approach:** Emit `REFERENCES`/`DYNAMIC` for `Name::class`. Opt `REFERENCES` into `FQN_EDGE_KINDS`.
  `skip_dynamic` keeps unlinkable DYNAMIC out but still yields `REFERENCES`. `_weaker_tier` keeps
  DYNAMIC. All-DYNAMIC `find_references` sets `authoritative: false`.
- **Rejected:** new kind (R3 tax); HEURISTIC-only (ticket asked DYNAMIC); show unlinked in nav
  (would flip 065's FQN-planted empty into a hit without resolve); array-only (R2).

**Assumptions:** nikic `ClassConstFetch` + NameResolver FQN — verified by proving parse test.
`skip_dynamic` test seed is INCLUDES — still skipped. No novel 3p.

**Change-list:** CL1 Visitor; CL2 contract FQN_EDGE_KINDS + schema tests; CL3 store skip_dynamic;
CL4 find_references authoritative + docstring; CL5 PLAN/CONVENTION/README/BACKLOG; CL6 fixture+tests.

`HANDLES: 4 recalled | 1 traced | 3 does not apply | 0 unanswered`

| Handle | Answer |
|--------|--------|
| `derived-not-listed-invariant` | **traced** — FQN set still derived from `contract.FQN_EDGE_KINDS`; schema test pins the frozenset. |
| `prove-the-guard-fails` | **does not apply because** no new enumeration guard. |
| `try-instead-tool-name` | **does not apply because** no new `try_instead` value. |
| `route-must-answer` | **does not apply because** no new route. |

**Proving test:** `pytest tests/test_class_const_mention.py::test_array_of_class_constants_emits_dynamic_references`

- **Gate 2:** cleared (standing approval)

---

## Phase 3 — Execute

- **Branch:** `fix/094-class-constant-in-array-literal-is-not-an-edge`
- **Proving test added:** `tests/test_class_const_mention.py`
- **Verification:** file axis ⊆ list. Behaviour as approved.
- **Empirical:**

```
$ scripts/docker-test.sh
# ruff + mypy green
# 1195 passed in 77.67s (main baseline 1191, +4 tests)
```
- **Design-invalidation:** none

## Phase 4 — Review ✋

**WAIVED** (`with skipped review`). No `Reviewed at`.

## Phase 5 — Finalise ✋

- Outward: commit, push, PR (AGENTS.md + this solve).
- Durable lesson → `docs/LESSONS.md`.

### Learning loop

`CLAIMS: 2 | T2=1 T5=1 | 0 unclassified`
`RECURRENCE: 1 recurring (derived-not-listed) | already R6.7`
`PROMOTION: 0 new class`

---

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens |
|-------|---------------------|-------|--------|
| 0 refine | exposure-checker (challenger) | 1 | unmeasured (host does not surface usage) |

`LEDGER TOTAL: unmeasured (host does not surface usage) · top cost driver: refine exposure-checker`

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Gate 1 | A–G ratified | standing best-option |
| Gate 2 | REFERENCES + skip exception + authoritative:false | 094/065/R2/R3 |
| Gate 4 | review waived | solve invocation |

## Session status

- **Last updated:** 2026-08-15
- **Current phase:** done (PR #108)
- **work_doc_mode:** embed · `docs/tasks/094_class-constant-in-array-literal-is-not-an-edge.md`
- **Next action:** none
- **Blocked on:** none

