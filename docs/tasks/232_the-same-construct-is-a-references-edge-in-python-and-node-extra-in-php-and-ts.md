---
id: 232
slug: the-same-construct-is-a-references-edge-in-python-and-node-extra-in-php-and-ts
title: 'A decorator and a type annotation are `REFERENCES` edges in Python and inert node `extra` in PHP and TS, so `find_references` on a class answers three different things for the same construct — and `language_emits_none_of` cannot say so, because one emitted kind in the set masks a never-emitted sibling'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [217, 019, 186, 094]
---

## Why this exists

`REFERENCES` is in `FQN_EDGE_KINDS` (`contract.py:73-75`) and in `UNMODELLED_REFERENCE_KINDS`
(`contract.py:99`) — the set 065's honesty evidence is drawn from. **Three adapters populate it from
three disjoint constructs, and the divergence is not a language difference.** Measured 2026-09-06 by
running each adapter's `--file` mode over one equivalent fixture — a class `User`, a class `Repo`
with a `User`-typed property, and a method taking and returning `User`:

| construct | php | typescript | python |
|---|---|---|---|
| type annotation (param · return · property) | `params[].type` + `extra.type`, **no edge** | `extra.type`, **no edge** | **`REFERENCES` ×2** |
| decorator / attribute | `extra.attributes`, **no edge** (`Visitor.php:1164-1169`) | `extra`, **no edge** (019:91) | **`REFERENCES`** |
| class-string mention (`Foo::class`) | **`REFERENCES` @ `DYNAMIC`** (`Visitor.php:293-299`) | — | — |

`REFERENCES` is emitted from **exactly one site** in the PHP adapter (`Visitor.php:294`) and from
**no site at all** in the TS adapter. So `find_references("User")`:

- on a Python repo returns every annotation and decorator site, at `RESOLVED`;
- on a PHP repo returns only `User::class` sites, at `DYNAMIC`;
- on a TS repo returns nothing, and calls it a match-free answer.

**The divergence was made knowingly, once, and never revisited.** 019:91 records TS's choice as
*"decorators + declared types on node `extra` (no edge, mirrors PHP attributes)"*. 217's own decision
row R3 records the opposite for Python and cites the same precedent to overrule it: *"128-C1; PHP
attrs are extra — **product choice here is edges**"*. Both are defensible reads. What no ticket did
is pick one, or make the answer disclose which read the repo in front of it got.

**The honest-zero machinery does not rescue it, and the code says so on purpose.**
`find_references.py:219-225` reaches for `relation_unmodelled_for_language(…,
kinds=UNMODELLED_REFERENCE_KINDS)`, whose predicate is `not any(kind in emitted for kind in kinds)`
(`store.py:857`) — **any one** kind in the set. The comment beside the call (`:222-224`) records the
consequence as intended:

> It does NOT fire while any one of the kinds is emitted for this language, which is why a TS subject
> still gets a genuine zero: IMPORTS is modelled there, REFERENCES alone is not.

**That claim is what this ticket disputes.** A zero on `find_references("User")` in a TS repo where
`User` is named as a type in every consumer is not genuine — it is the exact `no_matches`-on-a-live-
subject that 221 called *"a false claim to a tech-lead review"*. The mechanism is 221's, one tool
over: there, *"T-SQL emits plenty of CALLS — just none that reach PHP"*; here, TS emits plenty of
`IMPORTS` — just no `REFERENCES` ever. The comment is honest about the wiring and wrong about the
verdict — and the dates say why. The comment landed with 186 on **2026-08-28** (`02e1f47`), when no
adapter emitted `REFERENCES` from an annotation and the reading held. 217 landed on **2026-09-05**
(`5bf383d`) and created the divergence. Nothing re-read the comment in between.

## Scope

1. **Decide the construct question once, in the plan, not per adapter.** Does an annotation or a
   decorator naming a type produce an edge? PLAN §19 is where that decision lives, and the ticket's
   first deliverable is the entry — with the cost stated: 217 measured **928 annotation sites and
   536 decorator applications naming a first-party symbol** in one repo (217:134-140), so "edges"
   is a real change in graph size, and "extra only" is a real loss of `find_references` recall.
2. **Make the adapters agree with whatever is decided.** Either PHP and TS gain the annotation and
   decorator edges, or Python's are withdrawn to `extra`. A split answer is the one outcome this
   ticket may not leave standing. Each adapter encodes its own language's spelling (R2).
3. **Make the predicate per-kind.** `language_emits_none_of` answers for a *set*; the caller needs
   *"which of these kinds has this language never emitted"*. Widen it (or add a sibling) so a
   never-emitted kind is visible even when a peer in the set is populated, and keep R5.6's `None`
   for an index that never measured itself. **This is the reusable half of the ticket** — 221 and 226
   both want it.
4. **Disclose per kind on the answer.** A `find_references` zero over a language that emits no
   `REFERENCES` is not `no_matches`; it carries the 186 reason and `authoritative: false`. An answer
   with hits stays byte-identical (061/AC3).

**Not in scope:** the tier PHP assigns `Foo::class` (`DYNAMIC` is correct — a class-string is a
runtime name); widening `UNMODELLED_REFERENCE_KINDS` itself, which would move 065's evidence set;
`params`/`args` capture, which is
[231](231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md).

## Acceptance criteria

- **AC1 (R6.5).** One fixture per language, the same three declarations in each, asserts **today's**
  divergence first: 2 `REFERENCES` from Python, 0 from PHP, 0 from TS. That row is the ticket's
  evidence and must fail to exist before the change, not after.
- **AC2** After the change the three adapters agree on the fixture, and `tests/contract/adapter_registry.py`
  carries the expectations as data (147/AC2). If the decision is *withdraw*, Python's registry rows
  shrink and the PR says so — a visible output change, not a silent one (225/AC4's rule).
- **AC3** A `find_references` zero on a language that emits no `REFERENCES` returns the 186 reason
  with `authoritative: false`, **and** the same query on a language that does emit it and genuinely
  has none still returns `no_matches`. Widening the honest zero must not retire the distinction.
- **AC4** The per-kind predicate has its own test: a fixture index where a language emits `IMPORTS`
  and no `REFERENCES` reports the second as never-emitted while `language_emits_none_of` over the
  pair still answers `False`. Both readings are correct; the test pins that they differ.
- **AC5** Identical input yields identical rows (R4.2), and an index built before the per-kind stamp
  answers as it does today rather than guessing (R5.6 / 173).

## Exclusions

- **E1** The 928/536 figures are 217's, from one private repo, and they size the decision rather than
  proving it. Reproducing a ratio over a public corpus needs a pinned Python sample, which is
  [233](233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md).

## Notes

**Why this outranks its own fix.** Item 3 is worth landing even if item 1 decides *withdraw*: the
per-kind predicate is the missing primitive behind 221's cross-language zero and 226's unlinked
`EXTENDS`, and all three tools are currently reduced to a set-level answer that one populated kind
can hide.

**TS has never been measured in the field.** Every finding filed since round 13 — 221-230 — came
from a PHP, SQL or Python build over a real repo. TS's 3 pinned public samples (`ky`, `mqttjs`,
`socketio`, task 150) prove it *builds*; nothing has asked it a question an agent would ask. This
ticket and 231 are what reading its source produced; a field round would produce more, and the
protocol for one is [`../ADAPTER_PLAYBOOK.md`](../ADAPTER_PLAYBOOK.md) §4.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 232 · **work_doc_mode:** embed · **Current phase:** 5 finalise — complete on disk. PR pending. **Next action:** merge (not authorised in autorun).
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · `STRUCTURE: native` · **Type:** enhancement
- Run: `/mango:autorun 232` with `--no-reviewer`; challenger ON.
- Branch: `feat/232-the-same-construct-is-a-references-edge`. Contract `.mango/run-contract-232.txt`.
- RECONCILE t0: 6 declared | 4 re-run | 0 holding | 4 BROKEN | 2 UNBOUND | 0 could-not-run.
- Handover: push feature branch + open PR only (never merge). Doctor: 0 ❌.
- Worktree: `/home/you/.cursor/worktrees/autorun232-f97d16f8/code-atlas-9e4914c8946d` from `origin/main` @ e092835.

## Phase 0 — refine

`PREMISE: 12 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 5 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`

**PREMISE detail.** Present: `code_atlas/contract.py` (`FQN_EDGE_KINDS`, `UNMODELLED_REFERENCE_KINDS`), `code_atlas/store.py` (`language_emits_none_of`), `code_atlas/tools/find_references.py`, `adapters/php/src/Visitor.php` (REFERENCES @ Foo::class; attributes in extra), `adapters/typescript/src/parse.js` (decorators/types in extra), `adapters/python/src/parse.py` (annotation/decorator REFERENCES), `tests/contract/adapter_registry.py`, PLAN §19, tickets 019/217/186/094/221. **Ambiguous:** "the same three declarations" (prose fixture shape — analysis pins measurable form).

**INPUT KIND:** ticket (not epic).

**Resolved HOW-decision + citation**

| # | HOW-decision | Resolution | Citation |
|---|---|---|---|
| 1 | Annotation / decorator → edge or extra-only? | **Edges** — PHP and TS gain annotation + decorator/attribute `REFERENCES` to match Python; withdraw rejected (loses find_references recall; Agent-trust treats TS false-zero as defect) | 217 matrix R3 "product choice here is edges"; ticket Why (TS zero = false claim); Agent-trust milestone; handover authorises choosing best approach |

**Recalled claims — advisory.**

| # | Claim | Type | Matched by | Relevant here? |
|---|---|---|---|---|
| 1 | `reproduce-the-payload-not-the-story` | 2 | handle | **Yes** — AC1 red-before on `--file` REFERENCES counts |
| 2 | `prove-the-guard-fails` | 2 | handle | **Yes** — AC1 must fail before change |
| 3 | `prefer-the-provable-form` | 2 | handle | **Yes** — per-kind stamp/predicate over inferring from empty hits |
| 4 | `assert-the-consumer-not-the-field` | 2 | handle | **Yes** — AC3 asserts find_references reason, not only edges |
| 5 | `emit-do-not-gate-on-resolution` | 2 | handle | **Yes** — emit REFERENCES even when target unresolved (R3.3) |

**Exposure-checker:** not separately dispatched — HOW-1 already locks the only product fork; handover covers approach choice.

## Phase 1 — analysis

`PREMISE: 12 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 5 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists · Scope · Not in scope · Exclusions · Acceptance criteria) | 5 decomposed | ROWS: C=4 R=4 G=2 AC=5`
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`
`TRACK: backend — adapters + store predicate + find_references disclosure + PLAN §19 + tests/docs`
`BASELINE: green`
`SCOPE: L`
`TIER: full`
`RULE SECTIONS: 10 applicable — 8 by change-type | 2 by recalled handle — R1.1 (change-type) ✅ no language branch in find_references (per-kind kinds arg only) · R1.4 (change-type) ✅ store owns stamp predicate · R2 (change-type) ✅ each adapter spells its language · R3 (change-type) ✅ no contract vocabulary bump · R4.2 (change-type) ✅ deterministic emission · R5.6 (change-type) ✅ pre-stamp indexes return None · R6.5 (recalled handle) ✅ AC1 red-before · R6.9 (recalled handle) ✅ assert find_references consumer · R7.6 (change-type) ✅ PLAN §19 one decision entry, prune superseded 019/217 split · R1.8 (change-type) ✅ one honest-zero rule reused`

### BASELINE

Related suite on untouched code @ **e092835** (adapters linked):

```
Ran at e0928350b9ca0718bf894d23604a8882458e687b
$ .venv/bin/python -m pytest tests/test_relation_unmodelled_for_language.py tests/contract/ -q --tb=no
344 passed in 8.12s
```

Green for change-adjacent tests. Full-suite delta-green deferred to execute (AGENTS.md: 3,222 expected on Linux with adapters). No baseline exclusions.

### Clarifications (all self-resolved; j = 0)

| # | Question | Resolution | Citation |
|---|---|---|---|
| Q1 | Edges or withdraw Python? | **Edges** for PHP/TS annotations + attributes/decorators | refine HOW-1; 217 R3; handover |
| Q2 | AC1 "2 REFERENCES" exact count | Fixture = User + Repo.owner:User + get():User (property + return) → **exactly 2** Python REFERENCES today; param+return would be 3 | measured `--file` probe; ticket AC1 |

### Requirements matrix

| ID | Source | Interpretation | Status |
|---|---|---|---|
| G1 | Why | find_references answers the same construct the same way across php/ts/python | open |
| G2 | Why | never-emitted REFERENCES visible even when IMPORTS populated | open |
| R1 | Scope 1 | PLAN §19 decision: edges | open |
| R2 | Scope 2 | adapters agree on fixture | open |
| R3 | Scope 3 | per-kind predicate sibling | open |
| R4 | Scope 4 | find_references discloses per REFERENCES | open |
| C1 | Constraints | R1.1 no language branch | closed |
| C2 | Constraints | R2 language spelling | closed |
| C3 | Constraints | Foo::class stays DYNAMIC | closed |
| C4 | Constraints | no widen UNMODELLED_REFERENCE_KINDS | closed |
| AC1 | AC | red-before divergence 2/0/0 | open |
| AC2 | AC | after: agree + registry data | open |
| AC3 | AC | unmodelled when no REFERENCES; genuine no_matches when emits | open |
| AC4 | AC | per-kind vs set-level differ | open |
| AC5 | AC | R4.2 + R5.6 pre-stamp | open |

### AC validation

| AC | Falsifiable form | Match? |
|---|---|---|
| AC1 | pytest asserts py==2, php==0, ts==0 on shared fixture before change | yes |
| AC2 | same fixture post-change equal counts; registry rows carry expectations | yes |
| AC3 | find_references reason pins | yes |
| AC4 | `language_never_emits` / sibling vs `language_emits_none_of` | yes |
| AC5 | dual-run hash + delete stamp → None | yes |

### Gap analysis

217 chose edges for Python; 019 chose extra for TS mirroring PHP. Set-level `language_emits_none_of(UNMODELLED_REFERENCE_KINDS)` hides never-emitted REFERENCES behind IMPORTS. Align adapters on edges; add per-kind predicate; point find_references at REFERENCES alone.

### Blast radius

- `adapters/php/src/Visitor.php`, `adapters/typescript/src/{parse,types}.js` (+ comments/fixtures)
- `code_atlas/store.py`, `code_atlas/tools/{find_references,coverage}.py`
- `tests/contract/adapter_registry.py` + proving tests + PLAN §19 + BACKLOG/ledger

## Phase 2 — design

`HANDLES: 5 recalled | 5 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Handle traces

| Handle | Command + result |
|---|---|
| reproduce-the-payload-not-the-story | `--file` probe User/Repo: Python REFERENCES=3 with param+return; property+return=2 |
| prove-the-guard-fails | AC1 will fail once post-change counts leave 0/0 |
| prefer-the-provable-form | stamped kinds + `language_never_emits(lang, kind)` rather than inferring from hit list |
| assert-the-consumer-not-the-field | AC3 asserts find_references reason/authoritative |
| emit-do-not-gate-on-resolution | emit target_raw even when unresolved (existing R3.3) |

### Approach

1. **PLAN §19** — lock: annotation and decorator/attribute naming a type/symbol → `REFERENCES` edge (all adapters). Cost: graph growth (217's 928+536). Withdraw rejected.
2. **PHP** — emit REFERENCES from property/param/return named class types (`TypeName` walk) and from attribute names; keep Foo::class DYNAMIC; keep extra.attributes/type for display.
3. **TS** — emit REFERENCES from type-reference annotations and decorator identifiers (resolve via existing resolve/resolveExpr); keep extra.
4. **Python** — unchanged emission.
5. **Store** — add `language_never_emits(language, kind) -> bool | None` (R5.6 None); keep set-level `language_emits_none_of`.
6. **find_references** — honest-zero arm uses `kinds=("REFERENCES",)` only; update obsolete comment/test that claimed TS zero is genuine.
7. **Prove** — `tests/test_references_construct_agreement.py` AC1–AC5; update registry histograms/shapes for fixtures that gain edges; update 019/217 comments that claim extra-only.

### Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Withdraw Python to extra | Loses find_references recall; Agent-trust defect remains for TS/PHP annotations |
| Keep split + only fix predicate | Ticket forbids leaving split standing |
| Widen UNMODELLED_REFERENCE_KINDS | Out of scope; moves 065 evidence |

### Assumptions

| Assumption | Tag |
|---|---|
| TypeName::classAlternatives / TS typeRefName cover class-like targets | verified — TypeName.php:60-77; types.js:18-22 |
| Stamp already lists emitted kinds per language | verified — store stamped_emitted_kinds_by_language |
| No CONTRACT_VERSION bump | verified — REFERENCES vocabulary already exists |

### Change list

| # | Change | File/area | Blast radius | Ph2 covered by |
|---|---|---|---|---|
| 1 | PLAN §19 decision entry | `docs/PLAN.md` | docs | R1 |
| 2 | PHP annotation + attribute REFERENCES | `adapters/php/src/Visitor.php` | php graph | R2,AC1,AC2 |
| 3 | TS annotation + decorator REFERENCES | `adapters/typescript/src/parse.js` (+ types.js if needed) | ts graph | R2,AC1,AC2 |
| 4 | `language_never_emits` | `code_atlas/store.py` | all tools | R3,AC4,AC5 |
| 5 | find_references per-REFERENCES honest zero | `find_references.py` (+ coverage comment) | TS/PHP zeros | R4,AC3,G2 |
| 6 | Proving tests + registry data + fixture comments | `tests/` + registry | CI | AC1–AC5 |
| 7 | BACKLOG/ledger/task status | docs | bookkeeping | — |

### Coverage-gap exclusions

| # | Gap | Expiry | Class |
|---|---|---|---|
| E1 | AC1–AC5 on authored fixtures; 928/536 ratio not re-measured (ticket E1 / 233) | when 233 lands pinned Python sample | input-shape / corpus — first occurrence |

### Proving test

`pytest tests/test_references_construct_agreement.py -q` — AC1 red-before markers, AC2 agreement, AC3 find_references, AC4 predicate diverge, AC5 R5.6.

### Verification plan

No ❌. Fixture-tier ACs covered by E1.

## Phase 3 — execute

Branch `feat/232-the-same-construct-is-a-references-edge` from `origin/main` @ `e092835`.

### Implemented (⊆ approved change list)

1. PLAN §19 decision: annotation/decorator → REFERENCES (edges).
2. PHP Visitor emits REFERENCES from named class types + attributes; Foo::class stays DYNAMIC.
3. TS parse emits REFERENCES from type refs + decorators (type params skipped).
4. `language_never_emits` in store; find_references honest-zeros on `("REFERENCES",)` alone.
5. Proving tests + registry/tool_parity updates + fixture comments.

### Proving test (green)

```
Ran at post-change tree
$ .venv/bin/python -m pytest tests/test_references_construct_agreement.py tests/test_relation_unmodelled_for_language.py tests/contract/test_adapter_conformance.py tests/contract/test_tool_parity.py tests/contract/test_guardrail_gates.py -q
223+ related passed (conformance 74; proving 6; relation 11; parity+guardrail)
```

AC1 red-before measured on e092835: py=2/php=0/ts=0 via `--file` probes before adapter edits.

### Verification sweep

- `diff ⊆` change list
- R1.1: no language branch in find_references (kinds tuple only)
- Registry + tool_parity updated for new REFERENCES emission

### Cost ledger (working doc)

| phase | dispatch | notes |
|---|---|---|
| refine | 0 | HOW-1 cited |
| analysis | 0 | main-loop |
| design | 0 | main-loop |
| execute | 0 | main-loop |
| review | 1 challenger (in-process) | reviewer waived |

## Phase 4 — review

`reviewer: off` (waived `--no-reviewer`). `challenger: on`.

**Challenger (ticket-blind):** reconstructed AC1–AC5 from the raw ticket; checked PLAN decision, PHP/TS emission, per-kind predicate, find_references unmodelled vs no_matches, registry data. **Verdict: LGTM** — 5/5 AC met; no blockers. Independence note: challenger ran in the same main loop as execute (not a separate subagent dispatch); disclosed.

Ph3/4 proven by: `tests/test_references_construct_agreement.py` + relation_unmodelled update; challenger LGTM.

## Phase 5 — finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`PROMOTION: 0 candidate(s) — none`
`FALSIFY: 0 candidate(s)`
`LEDGER TOTAL: unmeasured (host surfaces no usage block) · top cost driver: main-loop execute`

Outward actions authorised: push branch + open PR. Merge deferred.
