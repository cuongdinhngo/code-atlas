---
id: 225
slug: the-flow-walk-is-breadth-first-over-a-sorted-adjacency-so-it-is-not-a-sequence
title: 'A sequence view over `flows.py` would assert an order the walk never established — `_adjacency` drops `edges.line` and sorts alphabetically, and `_trace` is breadth-first, so today''s step order is deterministic but is not call order'
phase: 3
milestone: Comprehension
status: done
depends_on: [197, 144, 112]
---

## Why this exists

197 built the one onboarding surface that follows a single capability *running* rather than
aggregating: `flows.md`, one trace per capability, every hop an edge carrying a confidence tier, a
hop that cannot be proven **terminating** the trace instead of being bridged. It renders as
`flowchart LR` (`artifact.py:856-860`).

The obvious next step — render the same trace as a mermaid `sequenceDiagram` — **is not a renderer
swap, and treating it as one would ship a false claim.** A flowchart asserts only *reaches*; a
sequence diagram asserts *this happened, then this*. The data behind `flows.md` does not carry that,
for two independent reasons found by reading the module:

| | What it does | Why it blocks a sequence |
|---|---|---|
| `_adjacency` (`flows.py:237-244`) | takes `(source, target, kind, tier)` 4-tuples and returns `source -> ((target, kind, tier), …)`, **`tuple(sorted(set(rows)))`** | `edges.line` is not in the tuple at all, so call order never enters the module. The sort is alphabetical by target — its docstring says *"sorted so the walk is order-stable (R4.2)"*, which is determinism, not chronology |
| `_trace` (`flows.py:253`) | **BFS** from the seed | breadth-first visits every hop at depth 1 before any at depth 2. That is the right shape for *what does this reach*; it is the wrong shape for *what does this do first* |

`FlowStep` (`flows.py:99-115`) carries `qname · file · layer · kind · tier` — no line, and no
container, so there is also nothing to name a participant with yet.

**`edges.line` exists and is populated** (`store.py:116`), so the ordering fact is in the graph and
has simply never been carried into this module. That is the whole ticket: two small widenings, and
one honesty decision about what to do when the order is genuinely unknowable.

## Scope

1. **Carry `line` into the trace.** Widen the adjacency tuple to include it, order a source's
   outgoing hops by `(line, target)` — `target` breaks ties so R4.2 still holds when two calls share
   a line — and put it on `FlowStep`.
2. **Walk in call order within a frame.** Order the hops *out of one source* by line; the walk's
   overall shape stays 197's and its termination rules are untouched. Whether the walk becomes
   depth-first is a design decision this ticket must **state and justify**, not assume: DFS follows
   one call to its end before the next, which is what a sequence diagram draws.
3. **Name participants.** `contract.split_qname` already yields `(container, member)`, so a hop in
   `App\\Foo::bar` participates as `App\\Foo`. A hop with no container participates as itself.
   No new vocabulary.
4. **Render `sequenceDiagram`,** with the `class_diagram.py` pattern: deterministic renderer plus a
   `validate_mermaid_*` guard, no LLM, no language branch. `flowchart LR` stays — the two answer
   different questions and 197's is not superseded.
5. **Say when the order is not known.** Two hops on the same line, a hop reached through a
   `HEURISTIC` or `DYNAMIC` edge, or a `walk_truncated` trace cannot claim ordering. The diagram
   discloses that rather than drawing a confident arrow (R5.6 / 108's rule that a cap is stated).

**Not in scope:** conditionals, loops and `alt`/`opt` blocks — control flow is not in the graph, and
a sequence diagram that invents branches is worse than one that draws a straight line. Cross-request
sequences. Any change to `flows.md`'s termination or ranking rules (197 owns them).

## Acceptance criteria

- **AC1 (R6.5).** A fixture whose call order differs from its alphabetical order proves today's
  module returns the alphabetical one. Without that row the change cannot be shown to have done
  anything, because both orders are deterministic and a green test proves nothing on its own.
- **AC2** The same fixture then traces in source order, and its `sequenceDiagram` messages appear in
  that order.
- **AC3** Ordering is disclosed, not assumed: a trace containing a same-line pair, an unproven hop
  or a truncation renders with that stated. A reviewer must be able to see which arrows are claims
  and which are proven.
- **AC4** Identical input yields byte-identical mermaid and byte-identical `flows.md` payload fields
  other than the new ones (R4.2). **If `flows.md`'s existing step order changes, that is a visible
  output change and the PR says so** — it is a fix, but it is not silent.
- **AC5** `flowchart LR` output for an existing fixture is unchanged unless AC4's reordering touches
  it, and the manifest stays valid against 112's schema.

## Exclusions

- **E1** Whether a sequence view is *worth* the surface is unproven. The maintainer asked for it
  after finding onboarding *"not really impressive"* on a real project, which is a demand signal, not
  a measurement. The honest artifact is the diagram plus its cost in the token ledger; if the
  rendered result reads as noise on a real trace, recording that and closing as *declined on
  evidence* is a legitimate outcome.

## Notes

**The `line` widening has value independent of the diagram.** Any answer that lists several call
sites in one function currently presents them in whatever order the query returned. `edges.line` is
already stored; carrying it through the trace is the first place it becomes visible.

**Why this is filed separately from 224.** Both came from the same question — the maintainer's read
that onboarding is missing a sequence view and an ER view — but they share no code: 224 is a T-SQL
DDL reader and a Column → Column edge, this is a walk order and a renderer. Filing them as one
ticket would have coupled a parser change to a diagram decision.

**The destination worth stating.** A trace that begins at a real HTTP route rather than a configured
entry point, runs through a controller, reaches a procedure through 222's cross-language link and
ends at a table 224 can relate to another table, is one continuous picture. None of the three
tickets delivers it alone, and none of them depends on the others to be worth shipping.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 225 — A sequence view over `flows.py` (working doc)

- **Ticket:** 225 · docs/tasks/225_the-flow-walk-is-breadth-first-over-a-sorted-adjacency-so-it-is-not-a-sequence.md
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`) only; no shared/ported code.
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend — 0/14 touched files under UI paths (deterministic markdown renderer, no UI surface)
- **TIER:** full
- **BASELINE:** green — authoritative reference is `scripts/docker-test.sh` (2971 passed / 1 structural skip, per AGENTS.md, verified 2026-09-06 on Linux). Native Windows subset run below confirms the affected modules.
  <!-- baseline exclusions (pre-existing failures outside this change): test_onboarding_viewer.py::test_a_repo_path_cannot_break_out_of_the_dataset_script_tag — WinError 123 (Windows rejects the `a<` fixture filename POSIX allows); a host/platform difference AGENTS.md records (POSIX-only), not a regression, and outside this change. -->

  Baseline capture on the untouched checkout `aee89594` (prose, not an evidence record — the
  pre-change tree is context, not proof for the reviewed tree, per lesson 201-C1). Command:
  `pytest tests/test_onboarding_flows.py tests/test_onboarding_dataset.py tests/test_generate_onboarding.py tests/test_artifact_contract.py tests/test_trace_capability.py tests/test_onboarding_viewer.py -q`
  → `1 failed, 100 passed, 8 skipped`; the one failure is the recorded platform exclusion above.
  The delta-green proof for the reviewed tree is stamped in Phase 3.

---

## Phase 0 — Refine

`PREMISE: 7 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

Premise references (all referenced-as-existing, all resolve): `flows.py:237-244` (`_adjacency`), `flows.py:253` (`_trace` BFS), `flows.py:99-115` (`FlowStep`), `store.py:116` (`edges.line` populated), `artifact.py:856-860` (`flowchart LR` render), `contract.split_qname`, `class_diagram.py` (renderer+validator pattern).

refine self-skips: the ticket is fully specified (5 scope items, 5 falsifiable ACs, E1). The one open design decision (DFS vs BFS) is explicitly delegated to the ticket to *state and justify* — a how-decision resolved in Phase 2, not a product-decision for the user. The user's invocation ("choose the best approach, pass all gates") pre-authorises it.

**Recalled claims (ADVISORY — surfaced only).**

| # | Claim (id) | Type | Matched by (symbol / area / finding) | Relevant here? |
|---|------------|------|--------------------------------------|----------------|
| 1 | `assert-the-consumer-not-the-field` (198-C1, 196-C4, 196-C8 -> R6.9) | 2 | handle: shape is a new renderer + a field (`line`) added for a reader | Yes — the new `line` field and the sequence renderer must be proven at the rendered mermaid (the consumer), not only on `FlowStep.line`. |

---

## Requirements matrix

`SECTIONS: 3 found (Scope, Acceptance criteria, Exclusions) | 3 decomposed | ROWS: C=2 R=5 G=0 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| R1 | Scope 1 | Carry `line` into the trace; widen adjacency tuple; order a source's outgoing hops by `(line, target)`; put it on `FlowStep` | `_adjacency` rows gain line; sort key `(line, target)`; `FlowStep.line` | `flows.py:237-244,99-115`; `edges.line` at `store.py:116` | 1/1 | 1/1 | ✅ |
| R2 | Scope 2 | Walk in call order within a frame; state/justify DFS vs BFS; termination rules untouched | Order neighbours by line; keep BFS (justified); `_trace` termination unchanged | `flows.py:253-295` | 1/1 | 1/1 | ✅ |
| R3 | Scope 3 | Name participants via `split_qname`; container else self; no new vocabulary | Participant = `split_qname(qname)[0] or qname` | `contract.py:224` | 1/1 | 1/1 | ✅ |
| R4 | Scope 4 | Render `sequenceDiagram` with the `class_diagram.py` pattern + `validate_mermaid_*` guard; no LLM; no language branch; flowchart stays | New `sequence_diagram.py`; `render_flows` emits both blocks | `class_diagram.py`; `artifact.py:856-865` | 1/1 | 1/1 | ✅ |
| R5 | Scope 5 | Say when order is not known (same-line pair, HEURISTIC/DYNAMIC hop, truncation) — disclose, don't draw a confident arrow (R5.6) | Unproven-order message rendered as a claim + `%%` note; truncation noted | R5.6 `flows.py:57-67` | 1/1 | 1/1 | ✅ |
| AC1 | AC1 (R6.5) | A fixture whose call order differs from alphabetical proves today's module returns the alphabetical one | Proving test: fails pre-change (alphabetical), passes post-change (line order) | ticket AC1 | 1/1 | 1/1 | ✅ |
| AC2 | AC2 | The same fixture traces in source order; its `sequenceDiagram` messages appear in that order | Ordered messages match line order | ticket AC2 | 1/1 | 1/1 | ✅ |
| AC3 | AC3 | Ordering disclosed, not assumed: same-line pair / unproven hop / truncation renders stated; reader can tell claims from proven | Dashed message + `%%` note for unproven order; diagram note on truncation | ticket AC3; R5.6 | 1/1 | 1/1 | ✅ |
| AC4 | AC4 | Identical input -> byte-identical mermaid and byte-identical `flows.md` payload other than the new fields (R4.2); if existing step order changes, PR says so | Determinism test; disclose any real-sample flowchart reorder | R4.2 | 1/1 | 1/1 | ✅ |
| AC5 | AC5 | `flowchart LR` unchanged unless AC4's reordering touches it; manifest valid against 112's schema | Flowchart render path untouched; `DATASET_VERSION` bumped for the new key (R3.5) | `artifact.py`; `DATASET_VERSION` | 1/1 | 1/1 | ✅ |
| C1 | Not in scope | No conditionals/loops/`alt`/`opt`; no cross-request; no change to 197's termination/ranking | Straight-line sequence only; walk termination/ranking untouched | ticket "Not in scope" | 1/1 | 1/1 | ✅ |
| C2 | E1 | Worth is unproven; honest artifact = diagram + its token-ledger cost; declining on evidence is legitimate | Ship the diagram + record cost; do not tune | ticket E1 | 1/1 | 1/1 | ✅ |

Status legend: ✅ done/proven · ⚠ deferred · ❌ not met.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable -> Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | proving test: pre-change returns alphabetical order | a fixture where line-order != alphabetical-order -> path differs (A->C->D->SINK vs A->B->D->SINK) | Y | measurable/greppable (asserted path membership) | — |
| AC2 | messages appear in source order | sequence messages = ordered steps; distinct lines -> deterministic order | Y | measurable (message order asserted) | — |
| AC3 | ordering disclosed for the 3 unknown-order cases | dashed `-->>` + `%% order unknown` note; truncation note | Y | measurable (grep the note / arrow) | — |
| AC4 | byte-identical mermaid + payload other than new fields | equality over `as_dict()` on reordered edge input | Y | measurable (byte equality) | — |
| AC5 | flowchart unchanged; manifest valid | flowchart render path untouched; `DATASET_VERSION` 14->15 | Y | measurable (golden + version test) | — |

## Inventory (universal "all/every/no" requirements)

- **Denominator / total N:** 3 (the three unknown-order cases AC3/R5 must each disclose)
- Numbered list:
  1. same-line pair (two outgoing hops from one source share a line)
  2. a hop reached through a HEURISTIC or DYNAMIC edge
  3. a `walk_truncated` trace

| # | Item | Ph3/4 proven by (`path:line` / test) | Status ✅/⚠/❌ |
|---|------|--------------------------------------|----------------|
| 1 | same-line pair | test_onboarding_sequence_diagram.py::test_same_line_pair_is_disclosed | ✅ |
| 2 | heuristic/dynamic hop | test_onboarding_sequence_diagram.py::test_unproven_hop_is_a_claim_not_an_arrow | ✅ |
| 3 | truncated trace | test_onboarding_sequence_diagram.py::test_truncated_trace_is_disclosed | ✅ |

## Clarifications

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

- Self-resolved: none.
- For human decision: none (j = 0).

---

## Phase 1 — Analysis ✋ Gate 1

- **Gap analysis (enhancement):** `flows.py` never carries `edges.line` (`_adjacency` at `flows.py:237-244` drops it and sorts alphabetically by target) and `_trace` (`flows.py:253`) is BFS, so `flow.steps` order is deterministic (R4.2) but not call order. `FlowStep` (`flows.py:99-115`) has no `line`. There is no `sequenceDiagram` renderer — `render_flows` (`artifact.py:818-866`) emits only `flowchart LR`. Target: carry the line through the trace, render a straight-line sequence that discloses unknown order, keep the flowchart.
- **Handler / entry point + blast radius:** producer chain `store.flow_edges` (`store.py:903`) -> `flows_from_graph`/`build_flows` (`flows.py:399,329`) -> `dataset.build_dataset` (`dataset.py:522,577`) -> `render_flows` (`artifact.py:818`). Consumers of `flow_edges`' shape: `tools/generate_onboarding.py:128`, `tools/trace_capability.py:181` (both pass the rows straight through — no logic change). The new `line` key rides `FlowStep.as_dict` -> `Flow` -> `FlowSet` -> `dataset.as_dict` -> `manifest_dict` (guarded by `DATASET_VERSION`). Tests touching the shape: `test_onboarding_flows.py` (hand-built 4-tuples -> widen to 5), `test_onboarding_dataset.py`/`test_artifact_contract.py` (version pins), `test_generate_onboarding.py` (flows.md golden).
- **Rule-compliance section coverage:**

  `RULE SECTIONS: 6 applicable — 5 by change-type | 1 by recalled handle — §1 (change-type) ✅, §3 (change-type) ✅, §4 (change-type) ✅, §5 (change-type) ✅, §7 (change-type) ✅, §6 (recalled handle) ✅`

  - §1 (R1.1 no language branch; R1.4 SRP) — the renderer is positional and language-agnostic (no `if language`); the SQL widening stays in `store.py`, parsing/storage untouched. Constrains `sequence_diagram.py` and `store.flow_edges`.
  - §3 (R3.5 version the document that moved) — the new `line` key on the dataset shape bumps `DATASET_VERSION` 14->15; `ARTIFACT_VERSION` bumps only if `flows` rides `OnboardingArtifact.as_dict` (verified at execute).
  - §4 (R4.2 determinism) — every new order is a total sort (`(line, target)`, `MIN(line)`, `%%` notes emitted deterministically); constrains `_adjacency`, `store.flow_edges`, the renderer.
  - §5 (R5.6 do-not-attest-past-resolution; R5.2 dynamic terminates) — AC3 disclosure IS this rule; the walk still terminates an unproven hop.
  - §6 (R6.1 test bar; R6.9 assert-the-consumer — the recalled handle) — proving test + a rendered-mermaid assertion, not only `FlowStep.line`.
  - §7 (R7.5 comments ≤3 lines; R7.6 prune; R7.2 token ledger) — docs pruned as added; ledger row on close.
  - §2 (standard over sample) N/A because no adapter changes. §8 (dependencies) N/A because no new dependency.
- Self-audit: sections decomposed = found (3); every AC falsifiable; BASELINE captured; j = 0; inventory N = 3; matrix Status filled; RULE SECTIONS emitted with sources; TRACK/TIER/SCOPE/STRUCTURE declared.
- **Gate 1 status:** cleared (autorun — j = 0)

## Phase 2 — Design ✋ Gate 2

- **Approach:**
  1. `store.flow_edges` (`store.py:903`): add `MIN(line)` as a 5th selected column, returning `(source, target, kind, tier, line)` with `line: int | None` (NULL -> None). `MIN` is deterministic; `GROUP BY`/`ORDER BY` unchanged.
  2. `flows.py`: `_adjacency` rows become `(target, kind, tier, line)`, each source's hops sorted by `(line is None, line or 0, target, kind, tier)` so a missing line sorts last and ties are total-ordered (R4.2). `FlowStep` gains `line: int | None = None` (+ `as_dict`). `_trace` stays **BFS** (see rejected alternative) but now expands neighbours in line order; `parents` records `(node, kind, tier, line)`, and a hop whose line **ties with another outgoing hop from the same source** is stored as `line=None` (order genuinely unknown). `_path_to` puts the line on each step; the seed step's line is `None`. `build_flows`/`flows_from_graph` widen the `edges` type to the 5-tuple.
  3. `sequence_diagram.py` (new, mirrors `class_diagram.py`): `render_sequence_diagram(flow)` -> deterministic `sequenceDiagram`; participants are positional ids (`P0…`) labelled with `split_qname(qname)[0] or qname`; one message per consecutive step. A message is **proven-order** iff `tier == RESOLVED` and `step.line is not None`; otherwise it renders `-->>` + a `%% order unknown: <reason>` note (unproven hop / same-line-or-unrecorded). A `walk_truncated` flow appends a `%% walk truncated …` note. `validate_mermaid_sequence_diagram(text)` is a Python syntax-subset guard (no Node/npm) raising `ValueError` on a miss.
  4. `artifact.py render_flows`: after the existing `flowchart LR` block, emit a second mermaid `sequenceDiagram` block per flow via the new renderer. The flowchart block is byte-for-byte untouched.
  5. Bump `DATASET_VERSION` 14->15 (R3.5).
- **Rejected alternatives:**
  - **DFS walk.** DFS follows one call to its end, which superficially suits a sequence. Rejected: (a) the ticket says "the walk's overall shape stays 197's" and 197's termination/reachability guarantees are defined over BFS; (b) each rendered flow is a single **linear** seed->sink path in *both* diagrams, so DFS buys no ordering fidelity the chain does not already have while it changes depth semantics and enlarges the blast radius; (c) BFS + line-ordered neighbours already carries call order into frontier expansion (Scope 2's literal ask) and stays deterministic. Justification cited: ticket Scope 2, R4.2, task 197.
  - **A separate second walk for the sequence.** Rejected: two notions of a flow drift (the 199 lesson); one walk feeds both renderers.
  - **New `order_known` field on `FlowStep`.** Rejected: "no new vocabulary" (Scope 3) — `line=None` already means "order not established," so the single `line` field carries both the value and its own absence.

**Assumptions**

| Assumption | verified / novel-untested | Resolution |
|------------|---------------------------|------------|
| `edges.line` is populated and nullable | verified | `store.py:116`; `MIN(line)` handles NULL -> None |
| `split_qname` yields `(container, member)` with container None for a bare name | verified | `contract.py:224-232` |
| No JSON schema rejects an added `steps[].line` key | verified | grep found no `jsonschema`; manifest is permissive; version bump covers the shape (R3.5) |
| The mermaid subset validator needs no Node | verified | `class_diagram.py:146` / `layer_diagram.py:152` are Python-only |

**Smallest change-list**

| Change | File/area | Blast radius (side-effect surface) | Ph2 covered by | k/N |
|--------|-----------|------------------------------------|----------------|-----|
| `flow_edges` selects `MIN(line)`; returns 5-tuple | `code_atlas/store.py` | `flows_from_graph`/`build_flows` callers; `test_onboarding_flows.py::test_flow_edges_*` (assert 5-tuple) | R1 | 1/1 |
| `FlowStep.line`; `_adjacency` line+sort; `_trace` line-ordered BFS + same-line->None; `_path_to`; widen `edges` type | `code_atlas/onboarding/flows.py` | every hand-built edge tuple in `test_onboarding_flows.py` (-> 5-tuple); `dataset.py` type hint | R1,R2,R5 | 3/3 |
| widen `flow_edges` param type hint | `code_atlas/onboarding/dataset.py` | none identified (annotation only) | R1 | 1/1 |
| `render_sequence_diagram` + `validate_mermaid_sequence_diagram` + dataclasses | `code_atlas/onboarding/sequence_diagram.py` (new) | new module imported by `artifact.py`; `CONVENTION.md` module map | R3,R4,R5 | 3/3 |
| `render_flows` emits a `sequenceDiagram` block per flow | `code_atlas/onboarding/artifact.py` | `flows.md` golden in `test_generate_onboarding.py`; flowchart must stay byte-identical | R4,AC5 | 2/2 |
| bump `DATASET_VERSION` 14->15 | `code_atlas/onboarding/dataset.py` | `test_onboarding_dataset.py`, `test_artifact_contract.py`, `test_generate_onboarding.py` version pins | AC5 | 1/1 |
| proving test + widen edges to 5-tuple + disclosure tests | `tests/test_onboarding_flows.py` | none (test) | AC1,AC2,AC4 | 3/3 |
| renderer + disclosure + determinism tests | `tests/test_onboarding_sequence_diagram.py` (new) | none (test) | AC2,AC3,AC4,R3,R4 | 4/4 |
| version-pin + flows.md golden updates | `tests/test_generate_onboarding.py`, `tests/test_onboarding_dataset.py`, `tests/test_artifact_contract.py` | none (test) | AC5,AC4 | 2/2 |
| working doc; status; module map; plan note; token ledger | `docs/tasks/225_*.md`, `docs/BACKLOG.md`, `docs/CONVENTION.md`, `docs/PLAN.md`, `docs/TOKEN_LEDGER.md` | R7.6 doc-size budget | R7.2,C2 | 2/2 |

**Recalled type-2 handles**

| # | Handle (class slug) | Answer |
|---|---------------------|--------|
| 1 | `assert-the-consumer-not-the-field` (R6.9) | traced — the new `line` field and the renderer are asserted at the *consumer*: `test_onboarding_sequence_diagram.py` asserts the rendered `sequenceDiagram` text (message order, `-->>` claim arrows, `%%` notes), not only `FlowStep.line`; and `render_flows` is asserted to emit the block. Command at execute: `python -m pytest tests/test_onboarding_sequence_diagram.py -q`. This is exactly R6.9's "assert the consumer, not the field." |

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **Rule compliance:** R1.1 (no language branch — positional/`split_qname`), R1.4 (SQLite stays in `store.py`), R4.2 (total sort keys, `MIN`), R5.6 (AC3 disclosure), R3.5 (`DATASET_VERSION` bump), R6.9 (assert the consumer), R7.5 (comments ≤3 lines).
- **Proving test:** `tests/test_onboarding_flows.py::test_call_order_by_line_differs_from_alphabetical` — a seed whose two RESOLVED outgoing hops reach a shared node, the earlier-*line* hop alphabetically *later*; pre-change the trace goes through the alphabetically-first hop, post-change through the earlier-line hop. Fails pre-change, passes post-change. Invocation: `python -m pytest tests/test_onboarding_flows.py -k call_order_by_line -q`.

**Verification plan**

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | logic | unit (proving test) | n/a | ✅ |
| AC2 | logic | unit (sequence render order) | n/a | ✅ |
| AC3 | logic | unit (disclosure notes/arrows) | n/a | ✅ |
| AC4 | logic | unit (byte-equality on reordered input) | n/a | ✅ |
| AC5 | logic | unit (flowchart golden unchanged + version pin) | n/a | ✅ |

Every AC asserts `f(x) == y` over authored graph rows (a value/format comparison), not a judged-"sensible" output — so fixture provenance is `n/a` throughout and no real corpus is wanted.

**Coverage-gap exclusions:** none.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- **Rollback + porting plan:** single-repo; revert the branch. No shared/ported code.
- SCOPE confirmed: M (5 core files incl. one new module + tests + docs; a version bump; no tier crossing to L).
- **Gate 2 status:** cleared (autorun)


## Phase 3 — Execute

- **Branch:** `feat/225-flow-sequence-diagram`
- **Commits (logical units; no AI co-author trailer):** `feat(225): render a capability trace as a sequenceDiagram, in call order` — the reviewed source tree `74de6ec` (source + tests + PLAN + working doc through Phase 2; amended to fold the ruff fixes, the two count-guard pins, and the challenger-round-1 fixes into one logical commit before any push). A follow-up bookkeeping commit carries this Phase 3/4/5 working-doc update.
- **Proving test added:** `tests/test_onboarding_flows.py::test_call_order_by_line_differs_from_alphabetical` — observed RED on the pre-change line-blind (alphabetical) sort, GREEN after.
- **Verification sweep — BOTH axes.**
  - *File axis:* zero stray references ✅ (no 4-tuple flow-edge literal remains in `code_atlas/`) · diff ⊆ approved list ✅ *with four recorded blast-radius test additions* (below) · each hunk maps to a matrix row ✅.
  - *Behaviour axis (design-conformance self-check):* every Gate-2 Approach bullet `implemented-as-approved`:
    1. `store.flow_edges` returns the 5-tuple with the winning tier's earliest line — implemented-as-approved (`store.py:903`, refined per challenger; see Phase 4).
    2. `_adjacency` line order + same-line→None; `FlowStep.line`; BFS kept & now justified in-code — implemented-as-approved (`flows.py:99-121,247-274,281-323`).
    3. new `sequence_diagram.py` renderer + validator, positional participants — implemented-as-approved.
    4. `render_flows` emits the sequence block, flowchart byte-identical — implemented-as-approved (`artifact.py:864-873`).
    5. `DATASET_VERSION` 14→15 — implemented-as-approved.

- **Design-conformance deviations** (the change-list under-named four blast-radius consumers; all mechanical shape/count updates forced by the 5-tuple widening or the new core module, surfaced to review):

  | Approved Gate-2 bullet | What was implemented instead | `path:line` |
  |------------------------|------------------------------|-------------|
  | `test_generate_onboarding.py` named as the flows.md consumer | the populated-flows consumer that asserts a rendered flow is `test_working_scope.py`; the R6.9 consumer assertion (flowchart + sequenceDiagram) landed there; `test_generate_onboarding.py` needed no edit | `tests/test_working_scope.py:86-89` |
  | module-count guard not named | a new core module bumps the pinned count 82→83 in **two** guards | `tests/test_core_is_language_agnostic.py:45`, `tests/test_sql_confinement.py:35` |
  | viewer test not named | it hand-builds flow-edge tuples, widened to 5-tuple | `tests/test_onboarding_viewer.py:634` |
  | `CONVENTION.md` / `test_artifact_contract.py` named as edits | neither needed a change (CONVENTION's onboarding entry is a generic "one module per concern"; the artifact contract version did not move — flows ride `manifest_dict`/`DATASET_VERSION`, not `OnboardingArtifact.as_dict`/`ARTIFACT_VERSION`) | — (no-op) |

- **Empirical output — PASTED, stamped with the tree under review.**

  Ran at `74de6ec2ac7c28c57bd9cd6c620bb98e716bac5c`
  ```
  $ python -m pytest tests/test_onboarding_flows.py::test_call_order_by_line_differs_from_alphabetical -q
  1 passed
  ```

  Proving test RED before the change (line-blind sort), GREEN after — the guard is seen failing (R6.5):
  Ran at `74de6ec2ac7c28c57bd9cd6c620bb98e716bac5c`
  ```
  $ (temporarily set _adjacency sort to line-blind alphabetical) python -m pytest -k call_order_by_line -q
  FAILED tests/test_onboarding_flows.py::test_call_order_by_line_differs_from_alphabetical
  assert 'App\\Zebra::z' in ['App\\Ctrl::act', 'App\\Alpha::a', 'App\\Repo::save', 'dbo.T::C']
  1 failed  (restored → 1 passed)
  ```

  Native affected subset (Windows host; the one platform-only exclusion deselected):
  Ran at `74de6ec2ac7c28c57bd9cd6c620bb98e716bac5c`
  ```
  $ python -m pytest <affected onboarding/flows/store modules> -q -k "not break_out_of_the_dataset"
  310 passed, 8 skipped, 1 deselected in 26.47s
  ```

  Authoritative full suite via `scripts/docker-test.sh` (ruff · mypy · pytest on Linux — fcntl + every adapter present), the delta-green proof for the reviewed tree:
  Ran at `74de6ec2ac7c28c57bd9cd6c620bb98e716bac5c`
  ```
  $ sh scripts/docker-test.sh
  ruff check .    -> All checks passed!
  mypy code_atlas -> Success: no issues found in 83 source files
  pytest -q       -> 3034 passed, 1 skipped (0:04:18) — the 1 skip is the structural test_runtime_image_reports_server_build; REAL_DOCKER_EXIT=0
  ```

- **Golden/snapshot change:** none — no pinned `flows.md` golden moved; the real sample's flow order did not change, so AC4/AC5's "if the existing step order changes, the PR says so" is a no-op here (it did not change). The only intentional shape change is the additive `steps[].line` key, covered by the `DATASET_VERSION` bump.
- **Design-invalidation / re-gate:** none.

## Phase 4 — Review ✋

- **reviewer verdict:** N/A — the rule-book reviewer was **waived by `--no-reviewer`**. No rule-book-grounded review of this diff exists; the challenger below is the only independent eye.
- **Re-review path:** the challenger's round-1 findings were fixed in the main loop and re-confirmed **verify-only** (no re-dispatch): the fixes sit inside Scope 1's own requirement and the approved change-list, not a scope change, so the challenger's full re-derivation is not paid twice.
- **challenger (ticket-blind) result:** round 1 — **9 met, 2 partial, 2 can't-tell**, two substantive findings, both **accepted and fixed**:
  1. *Correctness (real):* `flow_edges` took `MIN(line)` across the whole `(source,target,kind)` group, so a group whose winning tier is RESOLVED could report a **losing** (e.g. DYNAMIC) row's line — a line the trace then attests order on. **Fixed:** the line is now `MIN(line)` **within the winning tier** (`COALESCE` over RESOLVED→HEURISTIC→DYNAMIC, mirroring the tier `CASE`), `store.py:914-919`; regression test `test_flow_edges_takes_the_line_of_the_winning_tier_not_the_lowest` (RESOLVED@50 + DYNAMIC@5 → reports 50), which the challenger correctly noted was previously untested.
  2. *Scope 2 (justification visibility):* the BFS-vs-DFS decision was **stated but not justified** anywhere in `code_atlas/`/`tests/` (the justification lived only in PLAN/working-doc, which the challenger rightly did not read). **Fixed:** a ≤3-line justification added to `_trace` (`flows.py:286-290`) — BFS kept because each flow renders as one linear seed→sink path in both diagrams, so DFS buys no ordering the chain lacks while changing termination semantics.
  - The two *can't-tell* items are process/PR-body matters outside the diff: AC4's "PR says so" is discharged in the PR body (no reorder occurred — stated); AC5's manifest schema has **no** `jsonschema`/`additionalProperties` enforcement anywhere in `code_atlas/` (verified), and the new key is additive under the bumped `DATASET_VERSION`.
  - The challenger's AC2 note (wanting one integrated trace→render test) was also addressed: `test_a_traced_flow_renders_its_messages_in_call_order` builds a flow through `build_flows` and renders it, asserting call-order messages end-to-end.
- **security agent:** n/a (no security-tagged surface).
- **Scope reconciliation:** diff ⊆ approved list + four recorded blast-radius test additions (Phase 3); no reformatting of untouched lines; no pre-existing dead code deleted.
- **Regression on Phase-1 callers:** `store.flow_edges` consumers (`generate_onboarding`, `trace_capability`) pass the rows through unchanged; the full Docker suite is green (below).
- **Proving test result + "would it fail without the change?":** GREEN post-change; RED pre-change (pasted in Phase 3) — yes, it fails without the change. Judged vs `BASELINE` (delta-green: no new failure; the one Windows platform failure is the recorded exclusion, absent on Linux/Docker).
- **Layer-match re-confirmation:** every AC's risk layer is logic; every proof is a logic-layer unit test — no `❌`.
- **Ph3/4 proven by filled (k/N):** see matrix (all 1/1).
- **Clean?** reviewer waived · challenger's every finding landed with a regression test · no layer-match ❌ · k=N · proving test green · Docker delta-green → **yes**.
- **Reviewed at** `74de6ec2ac7c28c57bd9cd6c620bb98e716bac5c` · reviewed files: `code_atlas/store.py`, `code_atlas/onboarding/{flows,sequence_diagram,artifact,dataset}.py`, and the test files in the change-list.

## Phase 5 — Finalise ✋ final gate

- **PR draft:** `/tmp/pr-225.md` (from `.github/pull_request_template.md`).
- **Planned outward actions (each needs approval):**
  - [x] push branch `feat/225-flow-sequence-diagram` — covered by the handover authorisation (AGENTS.md Maintainer workflow standing approval + the explicit invocation).
  - [x] push bookkeeping (working-doc + BACKLOG + TOKEN_LEDGER) — folded onto the same branch.
  - [x] open PR via `gh` — covered by the handover authorisation.
  - [ ] tracker comment / transition — not requested; skipped.
  - [ ] merge — **NOT** in autorun; the human merges.
- **Follow-up tickets drafted for deferred (⚠) rows:** none — no deferred rows.
- **Durable lesson** (asked every run): written to `docs/LESSONS.md` — *`aggregate-the-line-with-the-tier-it-reports`*: when one SQL `GROUP BY` row reports both a chosen **tier** and a **line**, aggregate the line **within the chosen tier**, not across the whole group, or the row attests a value (the call line) sourced from a row it did not choose (R5.5). Landed on the pushed branch.
- **Revert path:** single-repo; revert the branch / the one feature commit. No shared state touched.

### Learning loop

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

| # | Claim (id) | Type (proposed) | Evidence | Handle | Recurred? (`seen:`) | Falsified? | Proposed destination | Human ratified? |
|---|------------|-----------------|----------|--------|---------------------|------------|----------------------|-----------------|
| 1 | 225-C1 | 2 (code) | `store.flow_edges` bare `MIN(line)` handed a RESOLVED edge a DYNAMIC row's line; challenger found it untested; fixed + regression test | `aggregate-the-line-with-the-tier-it-reports` | seen: 225 (first) | still-true (a test proves it) | stays in `lessons_path` (recurrence 1) | pending final gate |

---

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| Review | ticket-blind `challenger` | 1 | 93154 | RTK expected on shell (main-loop); not applied to the dispatch |

`LEDGER TOTAL: 93154 · top cost driver: Review/challenger` — main-loop spend is unmeasured (the host surfaces no usage block at runtime); `reviewer` was OFF (`--no-reviewer`), so its ~108k/round was not spent.

---

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-09-07 | Gate 0/1 cleared, `j=0` | ticket fully specified; the sole design choice (DFS vs BFS) is a how-decision the ticket delegates; the user pre-authorised "choose the best approach". |
| 2026-09-07 | Gate 2 cleared; walk stays **BFS**, ordered by line | each flow renders as one linear path in both diagrams, so DFS buys no ordering fidelity while enlarging blast radius and touching 197's termination (ticket Scope 2, R4.2, 197). |
| 2026-09-07 | `line=None` reused as the "order unknown" signal | Scope 3's "no new vocabulary": the single `line` field carries both the value and its own absence (same-line tie, unrecorded, non-RESOLVED). |
| 2026-09-07 | Change-list amended with 4 blast-radius test consumers | the 5-tuple widening / new core module forced shape+count updates in `test_working_scope`, `test_onboarding_viewer`, `test_core_is_language_agnostic`, `test_sql_confinement`; recorded, not silently absorbed. |
| 2026-09-07 | `CONVENTION.md` / `test_artifact_contract.py` dropped from the change-list | neither moved: CONVENTION's onboarding entry is generic; flows ride `DATASET_VERSION` (bumped), not `ARTIFACT_VERSION`. |
| 2026-09-07 | challenger round-1 correctness fix accepted | `MIN(line)` narrowed to the winning tier; the finding was real and untested — fixed with a regression test rather than deferred. |
| 2026-09-07 | SCOPE stays **M** | 5 core files incl. one new module + tests + docs, one version bump; no tier crossing to L. |

## Session status

- **Last updated:** 2026-09-07 (finalise — review clean, delta-green on Docker)
- **Current phase:** finalise
- **Next action:** push branch, open PR, then close bookkeeping (frontmatter done · BACKLOG · TOKEN_LEDGER)
- **Blocked on:** nothing
