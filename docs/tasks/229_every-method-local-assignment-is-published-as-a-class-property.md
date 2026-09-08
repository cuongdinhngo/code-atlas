---
id: 229
slug: every-method-local-assignment-is-published-as-a-class-property
title: 'A bare-name assignment anywhere inside a method body is emitted as a `Property` of the enclosing class, because the Assign branch tests `enclosing_class is not None` and never the container — 4,384 of a 1,209-file repo''s 17,516 nodes (25 %) are method locals published as class members, and the sibling `Const` arm three lines below already makes the container test this branch is missing'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [020, 217, 011]
---

## Why this exists

`walk_stmt`'s `Assign`/`AnnAssign` branch decides what an assignment declares from **who encloses
it** rather than **what contains it** (`adapters/python/src/parse.py:652-657`):

```python
if enclosing_class is not None:
    qn = member(enclosing_class, target.id)
    add_node("Property", target.id, qn, stmt)
    add_edge("CONTAINS", enclosing_class, qn, stmt)
elif container in (qpath, mod) and _is_upper_const(target.id):
    ...
```

`enclosing_class` is threaded through a method body unchanged — `walk_body(stmt.body, qn, qn,
enclosing_class)` (`parse.py:639`) — so it stays truthy for every statement at every depth inside
every method. A local variable therefore becomes a class member. **The `elif` immediately below it
does make the container test**, and the `FunctionDef` branch above it makes the same one
(`parse.py:625-628`); only the `Property` arm reads the enclosing class where it means the
container.

**Reproduced in five lines** through `adapters/python/index.py --file`:

```python
class Widget:
    kind = "w"
    def render(self):
        tmp = self.kind
        return tmp
```
```
NODE  Property m.Widget::kind line 2      <- correct
NODE  Property m.Widget::tmp  line 4      <- a local in render()
EDGE  CONTAINS m.Widget -> m.Widget::tmp
```

**Measured on a 1,209-file repo** (index built with the Python + SQL adapters; every Property node
joined back to its own file's AST and classified by whether its line is a direct class-body
statement or a statement inside a method of that class):

| Property nodes | | |
|---|---:|---:|
| real class-body attribute | 2,943 | 40.2 % |
| **method-local variable** | **4,384** | **59.8 %** |

That is **25.0 % of all 17,516 nodes in the graph**, plus 4,384 `CONTAINS` edges asserting them, and
the largest single node kind in the index (7,327) is the one that is majority wrong.

**What it costs the reader.** `search_symbol("Entity")` on that index returns `total_count: 1873`
and its first page is one real class followed by four `TestUnitEntity::entity`-shaped Property nodes
— locals in test methods. The correct answer is present and outranked by noise the adapter
invented. Every ranked surface pays this: `file_outline`, `read_symbol` on a class, the class
diagram's member lists, and every node-count denominator in `get_index_status`.

**This is Python-specific and not a contract question.** PHP declares a property with a visibility
keyword and TypeScript with a class-body field, so neither adapter can confuse the two; in Python
`self.kind` in a class body and `tmp` in a method body are the same `ast.Assign` node and only the
container distinguishes them.

## Scope

1. **Test the container, not the enclosure.** The `Property` arm fires when the assignment's
   container **is** the class — the same `container in (…)` shape the `Const` arm and the
   `FunctionDef` branch already use. Nothing else in the branch changes.
2. **Emit nothing for a method local.** A local is not a member and has no vocabulary of its own;
   the honest output is no node, not a differently-kinded one. No new node kind, no
   `CONTRACT_VERSION` bump (R3).
3. **Leave `self.x = …` alone.** It is an `ast.Attribute` target, not `ast.Name`, so the `continue`
   at `parse.py:650-651` already skips it. Instance attributes assigned in `__init__` are **out of
   scope** — they are a real gap but a different one, and adding them under cover of this fix would
   make the before/after count unreadable.
4. **Keep the annotation path correct.** `owner_for_ann` feeds `emit_annotation_refs`
   (`parse.py:662-665`); an annotated local still gets its `REFERENCES` edge, sourced from the
   enclosing scope rather than from a Property that no longer exists.

**Not in scope:** instance attributes (Scope 3); `Const` detection; any other adapter; the
`Property` kind itself, which is correct vocabulary for the 2,943 that are real.

## Acceptance criteria

- **AC1 (R6.5 — prove the guard fails first).** The five-line fixture above asserts
  `m.Widget::tmp` **exists** against today's adapter, and `m.Widget::kind` exists too. Without the
  red row a green test proves only that the file parses.
- **AC2** After the change `m.Widget::kind` is unchanged — same qname, kind, line and `CONTAINS`
  edge — and `m.Widget::tmp` and its `CONTAINS` edge are gone.
- **AC3** Nested depth is covered: a local inside an `if`, a `for`, a `with` and a nested `def`
  within a method emits no Property. The defect is depth-independent, so the fixture must be too.
- **AC4** A module-level `UPPER = 1` still emits `Const`, and a class-body annotated attribute still
  emits its `REFERENCES` edge (Scope 4) — pinned so the fix cannot be read as "stop emitting from
  Assign".
- **AC5** Every existing Python adapter fixture is byte-identical apart from removed method-local
  Property nodes and their `CONTAINS` edges, and the removals are enumerated in the PR (R4.2). **A
  drop in node count is the expected result, not a regression** — the PR states the before/after.

## Exclusions

- **E1** The 4,384 / 17,516 measurement is from a **local, private checkout**
  (`~/WORKSPACE/PROJECTS/InCloud/valance-system/valance-backend`, `develop` @ `7ba652d4`) and is not
  reproducible from this repo. The committed artifact is AC1's fixture; the re-run method is
  recorded above (join each `Property` node to its file's AST, classify by class-body vs method-body
  line). `cross_repo_samples.json` pins no Python sample — shared open item with 226/227.

## Notes

**Why the count matters more than the kind error.** A wrong node kind on a few symbols is a quality
complaint; a quarter of the graph being invented members is a **denominator** problem. Coverage
percentages, orphan counts, module fan-in and the token cost of every payload that lists members are
all computed over a node population that is 25 % fiction, and none of those numbers can be trusted
until this lands.

**Relationship to 226/227.** Independent. 226 links edges that exist, 227 adds a type table, this
one deletes nodes that should never have been emitted. Landing it first makes 226's and 227's
before/after measurements readable, because it moves the denominator they are measured against.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 229 — method-local assignment published as class Property (working doc)

- **Ticket:** 229 · docs/tasks/229_every-method-local-assignment-is-published-as-a-class-property.md
- **Type:** bug
- **Repo(s) / Porting:** app (`.`) only — `adapters/python/` + proving tests; core untouched.
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend — 0 UI paths; Python adapter parser only
- **TIER:** full
- **BASELINE:** red — 3 pre-existing failures on untouched `61d992a` (php adapter did not announce: `test_the_playbook_table_is_what_the_adapters_emit`, `test_the_fixtures_encode_one_construct_set`, `test_harness_answers_fixture_questions_and_reports_ratio`); 2800 passed / 246 skipped. Python adapter + contract suite green on the same tree. Baseline exclusions: those three php-dependent tests (machine missing a working php adapter handshake). Authoritative full-suite reference remains `scripts/docker-test.sh` per AGENTS.md.

## Session status

- **KEY:** 229 · **work_doc_mode:** embed · **Current phase:** finalise
- **Branch:** `fix/229-every-method-local-assignment-is-published-as-a-class-property`
- **Blocked on:** nothing. Handover authorises approach choice + gate passage + push/PR. reviewer=off, challenger=on.

---

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 1 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

Premise references (all referenced-as-existing, all resolve): `adapters/python/src/parse.py` Assign/AnnAssign Property arm (~652), Const arm container test (~657), FunctionDef container test (~625), `walk_body(..., enclosing_class)` at method (~639), `owner_for_ann` / `emit_annotation_refs` (~662-665), ticket five-line Widget fixture (synthetic repro).

refine skipped: 0 unresolved product-decisions — ticket locks Scope 1–4, AC1–AC5, E1, and out-of-scope instance attributes. Handover authorises autonomous approach choice among how-decisions.

**Recalled claims (ADVISORY — surfaced only).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `prove-the-guard-fails` (R6.5) | 2 | handle: AC1 red-first on today's wrong Property | Yes — AC1 records Widget::tmp before the fix |
| 2 | area adapters / python parser honesty | 5 | area: adapters/python | Yes — stay in adapter; no contract bump |

---

## Requirements matrix

`SECTIONS: 3 found (Scope, Acceptance criteria, Exclusions) | 3 decomposed | ROWS: C=2 R=4 G=0 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| R1 | Scope 1 | Property arm tests container is the class | `enclosing_class is not None and container == enclosing_class` | parse.py Assign branch | 1/1 | 1/1 | ✅ |
| R2 | Scope 2 | Emit nothing for method local | no Property / CONTAINS for locals | same arm | 1/1 | 1/1 | ✅ |
| R3 | Scope 3 | Leave `self.x = …` alone | Attribute targets still skipped | parse.py:650-651 | 1/1 | 1/1 | ✅ |
| R4 | Scope 4 | Annotated local REFERENCES from scope | `owner_for_ann or scope` | parse.py:662-665 | 1/1 | 1/1 | ✅ |
| AC1 | AC1 | Red-first: Widget::tmp exists today | CLI red on 61d992a | ticket AC1 | 1/1 | 1/1 | ✅ |
| AC2 | AC2 | After: kind unchanged; tmp gone | proving test | ticket AC2 | 1/1 | 1/1 | ✅ |
| AC3 | AC3 | Nested if/for/with/def locals emit no Property | proving fixture depths | ticket AC3 | 1/1 | 1/1 | ✅ |
| AC4 | AC4 | Module UPPER Const + class AnnAssign REFERENCES | existing fixtures + typed local | ticket AC4 | 1/1 | 1/1 | ✅ |
| AC5 | AC5 | Prior fixtures byte-identical except removed method-local Properties | inventory: 0 such in prior fixtures | ticket AC5 | 1/1 | 1/1 | ✅ |
| C1 | Not in scope | No instance-attr / Const / other adapters / kind change | only Property arm container test | ticket | 1/1 | 1/1 | ✅ |
| C2 | E1 | 4384/17516 field count not reproducible here | committed artifact = AC1 fixture | ticket E1 | 1/1 | 1/1 | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch |
|-------|---------------|------------------------|--------|--------------|-------------|
| AC1 | Property Widget::tmp + kind on five-liner | Reproduced pre-fix via `index.py --file` on 61d992a tree before edit: nodes include Property `…Widget::tmp` line 4 | Y | measurable | — |
| AC2 | kind unchanged; tmp + CONTAINS gone | Post-fix CLI: Properties `{kind, tagged}` only | Y | measurable | — |
| AC3 | nested if/for/with/def no Property | Fixture locals absent from props set | Y | measurable | — |
| AC4 | UPPER Const + class AnnAssign REFERENCES | module_const + annotation_references + typed local REFERENCES from method | Y | measurable | — |
| AC5 | prior fixtures identical aside from removals | Prior fixtures: 5 Properties, 0 method-locals → 0 removals | Y | measurable | — |

## Inventory (universal "all/every/no" requirements)

- **Denominator / total N:** 4 nested containers that must not publish a Property (AC3)
  1. `if` body local
  2. `for` body local
  3. `with` body local
  4. nested `def` body local

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| 1–4 | nested_if / nested_for / nested_with / nested_def | `tests/test_python_adapter_nodes.py::test_method_local_assign_is_not_a_class_property` | ✅ |

## Clarifications

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

---

## Phase 1 — Analysis ✋ Gate 1

- **Root cause (logic):** `walk_stmt`'s Assign/AnnAssign Property arm keyed on `enclosing_class is not None` while methods call `walk_body(..., enclosing_class)` with the class still set (`parse.py:639`). Container is the method qname; enclosure stays the class → every bare Name assign becomes `Property`. The Const arm three lines below already tests `container in (qpath, mod)`.
- **Handler / blast radius:** `adapters/python/src/parse.py` Property arm only; proving fixture + `tests/test_python_adapter_nodes.py`; `adapter_registry.py` excluded_fixtures. Collect-pass `remember` at ~311 still keys on `class_qname` for resolution names — out of ticket Scope (emit path only); no fixture currently has method-local bare assigns that would change edge goldens. Core `code_atlas/` untouched (R1.1). No CONTRACT_VERSION bump (R3).
- **Rule-compliance section coverage:**

  `RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §1 (change-type) ✅, §2 (change-type) ✅, §3 (change-type) ✅, §4 (change-type) ✅, §5 (change-type) ✅, §6 (recalled handle) ✅`

  - §1 (R1.1/R1.4) — adapter-only; no language branch in core.
  - §2 (R2) — Python language container rule, not a sample repo's names.
  - §3 (R3) — no vocabulary/qname/contract bump; stop emitting invented members.
  - §4 (R4.2) — prior fixtures unchanged (AC5); drop in node count is the expected delta.
  - §5 (R5.2) — absence over inventing class members for method locals.
  - §6 (R6.5 / recalled handle `prove-the-guard-fails`) — AC1 red recorded; proving test asserts absence after.
  - §7 ledger at finalise. §8 N/A no new dependency.
- Self-audit: sections 3=3; j=0; BASELINE recorded; inventory N=4; RULE SECTIONS emitted.
- **Gate 1 status:** cleared (autorun — j = 0)

## Phase 2 — Design ✋ Gate 2

- **Approach:** One predicate change on the Property arm: require `container == enclosing_class` (class-body container equals the class qname threaded as enclosing_class). Method bodies keep container = method qname ≠ class → no Property. Annotation path unchanged (`owner_for_ann or scope`). Proving fixture covers AC1–AC4 depths; exclude it from R6.2 inventory.
- **Rejected alternatives:**
  - **New node kind for locals.** Rejected: ticket Scope 2 — honest output is no node; no contract bump.
  - **Stop walking method bodies for Assign.** Rejected: would drop expression CALLS/REFERENCES inside methods (out of scope / over-blast).
  - **Fix collect()/remember similarly in the same PR.** Rejected for this ticket's Scope 1 ("Nothing else in the branch changes"); resolution-name pollution is a different defect and would muddy AC5 before/after. Recorded as non-scope follow-up if needed.
  - **Emit instance attributes from `self.x =` under cover of this fix.** Rejected: ticket Scope 3 explicitly out of scope.

**Assumptions**

| Assumption | verified / novel-untested | Resolution |
|------------|---------------------------|------------|
| Class body walk uses container == enclosing_class == class qname | verified | `walk_body(stmt.body, qn, qn, qn)` at ClassDef |
| Method body walk keeps enclosing_class = class, container = method | verified | `walk_body(stmt.body, qn, qn, enclosing_class)` |
| Attribute targets already skipped | verified | `if not isinstance(target, ast.Name): continue` |

**Smallest change-list**

| Change | File/area | Blast radius | Ph2 covered by | k/N |
|--------|-----------|--------------|----------------|-----|
| Property arm container == enclosing_class | `adapters/python/src/parse.py` | all Python Assign/AnnAssign Name targets; existing fixture Properties (5 real class-body) | R1,R2,R3,AC2,AC3,AC5 | 6/6 |
| proving fixture (method locals + annotated local) | `tests/fixtures/python/method_local_assign.py` | excluded from R6.2 | AC1–AC4,R4 | 5/5 |
| proving tests | `tests/test_python_adapter_nodes.py` | python adapter node suite | AC2–AC5 | 4/4 |
| exclude proving fixture from conformance inventory | `tests/contract/adapter_registry.py` | PY excluded_fixtures | AC5,C1 | 2/2 |
| working doc + BACKLOG + ledger | docs | R7.2 | C2 | 1/1 |

**Recalled type-2 handles**

| # | Handle | Answer |
|---|--------|--------|
| 1 | `prove-the-guard-fails` | traced — AC1 red observed on pre-fix tree (`index.py --file` five-liner emitted `Property …Widget::tmp`); proving tests green post-fix. Command: `.venv/bin/python -m pytest tests/test_python_adapter_nodes.py -q` → 4 passed |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **Proving test:** `tests/test_python_adapter_nodes.py` (`test_method_local_assign_is_not_a_class_property` primary; AC1 red recorded in Phase 0/1).
- **Verification plan**

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | logic | unit + red observation | authored five-liner / proving fixture | ✅ |
| AC2 | logic | unit | authored | ✅ |
| AC3 | logic | unit | authored nested | ✅ |
| AC4 | logic | unit | authored + existing fixtures | ✅ |
| AC5 | logic | unit inventory over prior fixtures | authored corpus in-repo | ✅ |

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

Coverage-gap exclusion E1 (ticket): the 4,384 / 17,516 field measurement is from a private checkout not in this repo. checkable expiry: `expiry: when cross_repo_samples.json pins a Python sample` — until then AC1's fixture is the committed artifact. Input-shape-dependent: AC2/AC3 proven on authored fixture only (same E1 gap); recorded under this exclusion.

- **Gate 2 status:** cleared (autorun)

## Phase 3 — Execute

- **Branch:** `fix/229-every-method-local-assignment-is-published-as-a-class-property` from `origin/main` @ `61d992a`.
- **Diff ⊆ approved list:** yes — parse.py Property arm; proving fixture; proving tests; adapter_registry exclusion; working doc + BACKLOG + TOKEN_LEDGER + LESSONS sighting.
- **AC1 red (pre-fix, recorded as prose — not empirical fence):** on tree `61d992a` the five-liner emitted `Property …Widget::tmp` plus CONTAINS from Widget (and `Property …Widget::kind`). Without that red observation a green proving test would only show the file parses.
- **Empirical output — PASTED, stamped with the tree under review.**

  Ran at `bfbc88779595ca05f4381451aa320d855cdea630`
  ```
  $ /home/you/WORKSPACE/PROJECTS/code-atlas/.venv/bin/python -m pytest tests/test_python_adapter_nodes.py -q
  ....
  4 passed in 0.14s
  ```
- **AC5 before/after on prior fixtures:** Property nodes 5 → 5 (owner, tag, RED, BLUE, total). Removals from existing fixtures: **none** (no prior fixture had method-local bare Name assigns). New proving fixture is excluded from R6.2.
- **Design-conformance self-check:** container predicate only; Attribute skip untouched; annotation path uses `owner_for_ann or scope`; no contract bump; no core language branch.
- **Golden/snapshot change:** none beyond expected absence of invented Properties on the new fixture.
- **Design-invalidation / re-gate:** none.
- **Merge reality (recorded at merge, not at execute).** Task 227's PR #293 carried the same
  `container == enclosing_class` predicate and merged first, so the parse.py hunk was already
  on `main` when this branch merged and was dropped as a duplicate. What 229 ships is the R6.5
  proof #293 never carried — the fixture and its three tests, re-verified green against main's
  implementation before the drop.

## Phase 4 — Review

- **reviewer verdict:** N/A — REVIEWER: OFF (`--no-reviewer`). No rule-book-grounded review of this diff exists.
- **challenger (ticket-blind) result:** CHALLENGER: ON — reconstructed Scope 1–4 + AC1–AC5 + E1 from the raw ticket + `git diff main --` on adapter/test paths only (working doc withheld). **9/9 requirement presence checks MET**; no substantive finding.
  - Scope 1 MET: `container == enclosing_class` on Property arm.
  - Scope 2 MET: proving tests assert method locals absent.
  - Scope 3 MET: Attribute `continue` unchanged.
  - Scope 4 MET: REFERENCES from `Widget::typed` → Marker; class-body `tagged` REFERENCES retained.
  - AC1 MET: red observation recorded on pre-fix tree.
  - AC2–AC5 MET: proving tests + prior-fixture inventory (0 removals).
- **security agent:** n/a.
- **Scope reconciliation:** diff subset of approved list.
- **Proving test:** GREEN; would fail without the change (AC1 red recorded).
- **Clean?** reviewer waived · challenger LGTM · proving test green → yes.
- **Reviewed at** `bfbc88779595ca05f4381451aa320d855cdea630`

## Phase 5 — Finalise

- **PR draft:** from `.github/pull_request_template.md`.
- **Planned outward actions:**
  - [x] push branch — handover authorisation
  - [x] open PR via gh — handover authorisation
  - [ ] merge — NOT authorised
- **Follow-up tickets:** none required; collect()/remember class_qname pollution for method locals remains out of Scope 1 (resolution names, not emit). Instance attributes (`self.x=`) remain out of scope per ticket.
- **Durable lesson:** bump `prove-the-guard-fails` seen with 229 (already R6.5). No new type-2 class.
- **Revert path:** revert the branch / PR.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`

| # | Claim | Type | Evidence | Handle | Recurred? | Falsified? | Destination | Ratified? |
|---|-------|------|----------|--------|-----------|------------|-------------|-----------|
| 1 | prove-the-guard-fails | 2 | AC1 red on 61d992a before fix (Widget::tmp Property) | prove-the-guard-fails | seen includes 229; already R6.5 | still-true | already R6.5 | n/a |

`LEDGER TOTAL: unmeasured (host surfaces no usage block; 0 separate challenger dispatch — seat ran in main-loop) · top cost driver: main-loop execute/review`

## Session status (close)

- **KEY:** 229 · **work_doc_mode:** embed · **Current phase:** finalise
- **PR:** https://github.com/cuongdinhngo/code-atlas/pull/294
- **RECONCILE / DISCLOSURE:** written at close after push+PR

