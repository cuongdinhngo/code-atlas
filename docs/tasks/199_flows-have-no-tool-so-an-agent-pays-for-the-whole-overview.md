---
id: 199
slug: flows-have-no-tool-so-an-agent-pays-for-the-whole-overview
title: "Capability flows have no tool of their own, so an agent asking about one request pays for the whole overview"
phase: 3
milestone: M11
status: done
depends_on: [197]
---

## Why this exists

[197](197_no-surface-follows-one-request-from-entry-to-the-data-it-writes.md) shipped capability
flows to the surfaces a **reader** uses — the 112 dataset, the viewer, and a committed `flows.md`.
It deliberately shipped **no agent-facing surface**, and that was not a preference: it was measured.

197 tried one (`summary.flows` on `architecture_overview`) and the repo's own gate rejected it:

```
GATE FAILED: tokens-to-answer ratio 0.53 is below the floor 0.63 (grep 3065 / atlas 5786 tokens)
precision 0.944 | unexpected 6
```

Two distinct defects, both properties of the surface rather than of the flows:

1. **Cost.** To read one 4-file trace an agent bought the entire overview payload — layer table,
   layer×layer matrix, hubs, reachability split, capability table, mirrors — ~2,400 tokens against
   `grep`'s 852.
2. **Over-answering.** `summary.flows` returns **every** flow, so a question about **one** request
   claimed 6 files belonging to other requests. Those files are not wrong; the *question* cannot be
   asked of that surface.

197 reverted it and recorded AC8 as exclusion **E3** with `expiry: when 199 lands`. This ticket is
that expiry.

## Scope

1. A tool that answers **one** capability question — an entry symbol, a file, or a business module —
   and returns only the flows that subject participates in.
2. Payload sized like the other nav tools: the trace, its hops with layer and confidence tier, its
   ending, its attribution. Not the dataset, not the layer table.
3. A `tier: onboarding` question in the 121 harness of the shape *"what happens when a user does
   X?"*, ground truth **hand-read before the tool runs** — the criterion 197 could not meet.

### Explicitly not in scope

- Re-deriving flows. `code_atlas/onboarding/flows.py` already builds them; this is a query surface
  over the same derivation, never a second notion of a flow (PLAN §1).
- Widening `architecture_overview`. Measured and rejected above.

## Constraints

- **The gate is the acceptance test, not a report:** `--min-ratio 0.63 --min-recall 1.0
  --min-precision 1.0` must stay green **with the new question in the registry**. A tool that cannot
  beat `grep` on its own question has not earned its payload, and saying so in writing is what
  [121](121_onboarding-question-class-never-measured.md) and `ROADMAP.md` §5 require.
- **R4.3** — bounded like every nav tool; **R4.2** — byte-identical output; **R1.1/R1.4**.
- The tool surface is an invariant with many readers (`TOOL_NAMES`, `TOOLS.md`, PLAN, the MCP
  conformance tests) — 194's blast-radius lesson applies.

## Acceptance criteria

1. One tool answers one subject's flows; a subject that matches nothing **refuses with a reason**
   rather than returning an empty list (182).
2. Its payload carries no aggregate the question did not ask for.
3. The 121 harness gains the behaviour question, and the **gate stays green at the existing floors**
   — no floor is lowered to accommodate it.
4. `flows.py` is unchanged except where the query genuinely needs it.

## References

[197](197_no-surface-follows-one-request-from-entry-to-the-data-it-writes.md) (the flows, the
measurement, and E3), [121](121_onboarding-question-class-never-measured.md) (the question class and
its narrowing), [182](182_find-orphans-answers-with-rows-it-has-flagged-unreliable.md) (refuse rather
than dump), [194](194_default-filled-column-defect-class-query.md) (the tool-surface blast radius).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 199 · **work_doc_mode:** embed · **Current phase:** 5 finalise — complete on disk.
- `TRACK: backend` · `TIER: full` · `SCOPE: L` · `STRUCTURE: native` · **Type:** enhancement.
- Run arg: *"with skipped review"* = **reviewer seat only**; the challenger keeps its seat.
- Contract `.mango/run-contract-199.txt`. **One condition was struck at t0:** `FLOORS-UNCHANGED`
  reported HOLDING on an empty run, because "no floor was lowered" is the *starting* state. A
  negative acceptance criterion can never be a contract condition; it is proven by the diff.

## Phase 0 — refine

`PREMISE: 11 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 5 by handle | 0 by area | 0 by finding | 6 retired skipped — advisory (blocks nothing)`
`REFINE: 8 unresolved surfaced | 5 want-decision asked | 3 how-decision resolved+cited | 5 ASSUMED | skip: no`

**The exposure-checker corrected the brief it was given.** My dispatch called a new refusal reason a
"contract-vocabulary question". It is not: `NavReason` (`nav_result.py:19-38`) is not the R3 node/edge
contract, so adding to it needs no `contract_version` bump. The correction is right and is recorded
rather than quietly absorbed.

It also found the fork the ticket hides completely — **W6**, below. `flows.py` is reusable as the
ticket demands, but its *inputs* (`layer_of`, `owner_of_dir`) are themselves whole-repo aggregate
computations, which is the machinery this ticket exists to stop paying for. The ticket never raises it.

**Settled wants — all five handed back** (*"you have my approval to choose the best approach"*), so
each is `ASSUMED (awaiting ratification)`.

| # | The want | Chosen direction | Status |
|---|----------|------------------|--------|
| W2 | How does a *business module* subject resolve? | **Exact match on `Flow.module`** — no reverse lookup is needed, because `flows.py:121` already carries the owning module on every flow. Keyed on `BusinessModule.module` (the directory path, always present) and **never on `.label`**, which is optional 198 prose: keying on it would make the tool's answer depend on whether an LLM seam is enabled | ASSUMED |
| W3 | Subject is a MIDDLE hop — whole flow, or a suffix from there? | **The whole flow.** Scope 1 says *"the flows that subject participates in"*, and participation is membership; a suffix would also be a **second notion of a flow**, which the ticket's own exclusion forbids. `flows.py` needs no change (AC4) | ASSUMED |
| W4 | Generic `NavReason`, or a tool-specific constant like 182's? | **The generic register, and no new constant.** `REASON_NO_SUCH_SYMBOL` for a subject the index does not hold; `REASON_NO_MATCHES` for one it holds that joins no flow. 182 minted constants because it had a walk-budget state with no generic equivalent; here both states have exact ones, and a synonym is the duplication R7.6 forbids | ASSUMED |
| W5 | Who verifies the hand-read ground truth is not self-flattering? | **The ticket-blind challenger, which has never seen my reading.** The trace was hand-read and written into this doc *before the tool existed* (below); the challenger is asked at review to re-derive it from the fixture itself. Existing machinery, no new role | ASSUMED |
| W6 | Where do `layer_of` / `owner_of_dir` come from per call? | **The same aggregate machinery the overview uses** — `assign_layers` + `refine_layers` + `find_business_modules`. A cheaper per-path substitute would let this tool and `architecture_overview` report **different layers for the same file**, and PLAN §1 is explicit that the map never runs a second pipeline. The ticket's complaint is payload tokens, not compute; that the tool is cheap in tokens and **not** in compute is disclosed, not hidden | ASSUMED |

**Resolved + cited.**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| H1 | One polymorphic subject string, or typed parameters? | **Three optional typed parameters — `qname`, `path`, `module` — exactly one supplied.** No sniffing, and no cross-kind collision to tie-break, which dissolves the checker's row 2 rather than answering it | `impact.py:151`'s `paths`/`qnames` split; 101 (nav tools take one subject at a time) |
| H2 | The tool's name | **`trace_capability`** — verb-first `snake_case` | CONVENTION §2 (*"Tools: `snake_case` verb-first"*) |
| H3 | Where do the flows come from? | **`build_flows` unchanged**, then filtered. Not re-derived | ticket *Explicitly not in scope*; PLAN §1 |

### Hand-read ground truth — recorded BEFORE the tool existed (Scope 3's criterion)

Read from the fixture source alone (`tests/fixtures/php/onboarding/*.php`), by hand, before a single
line of `trace_capability` was written. This is the reading the challenger is asked to check.

**Question:** *"What happens when a user opens the invoice list — what does that request touch, from
the entry point to the data?"* · **Subject:** `\Shop\Controllers\InvoiceController::index`

| # | hop | file | why |
|---|-----|------|-----|
| 1 | `\Shop\Controllers\InvoiceController::index` | `controllers/InvoiceController.php` | the entry |
| 2 | `\Shop\Services\InvoiceService::recent` | `services/InvoiceService.php` | `count($service->recent())` |
| 3 | `\Shop\Lib\Clock::now` | `lib/Clock.php` | `$clock->now()` in `recent` |
| 4 | `\Shop\Repositories\InvoiceRepository::findRecent` | `repositories/InvoiceRepository.php` | `return $repo->findRecent($clock)` |
| 5 | `\Shop\Models\Invoice` | `models/Invoice.php` | `new Invoice()` in `findRecent` |

**Deliberately NOT in this request's answer** — and this is the list that makes the question
discriminating, because every one of them is reachable by a `grep` for `Invoice`:

- `\Shop\Jobs\ReminderJob::run` — a **different** entry that calls the same service
- `\Shop\Reports\InvoiceReport::render` — a different entry that calls the same repository
- `\Shop\Legacy\RetiredExporter::dump` — a different entry
- `render_invoice_page` (`views/invoice_page.php`) — `require_once`d by the controller and **never
  called**; an `INCLUDES` edge is not a call
- `settings` (`config/settings.php`) — referenced by nothing
- `\Shop\Models\Invoice::total` — declared, never called on this path

## Phase 1 — analysis

`SECTIONS: 6 found (Why this exists · Scope · Explicitly not in scope · Constraints · Acceptance criteria · References) | 6 decomposed | ROWS: C=3 R=5 G=1 AC=4`
`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`
`BASELINE: green — 2661 passed in 159.32s`
`TRACK: backend — 0/16 touched files under UI paths`
`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §1 (change-type) ✅ · §2 (change-type) ✅ · §3 (change-type) ✅ · §4 (change-type) ✅ · §5 (change-type) ✅ · §6 (change-type) ✅ · §7 (change-type) ✅`

```
Ran at 924d75b910ac711c325a2702498e208bbc6df895
$ .venv/bin/pytest -q
2661 passed in 159.32s (0:02:39)
```

§8 is **N/A because** the change adds no dependency. The rulebook carries no `handle:` field, so the
recalled-handle source contributes 0 sections.

- §1 ✅ R1.4 — the tool reads `store.py` and calls `flows.py`; neither imports the other. R1.1 — no
  language name anywhere; the subject is whatever the graph holds.
- §2 ✅ the benchmark question runs on the **pre-existing** 121/197 fixture, not one authored to suit
  this tool.
- §3 ✅ `contract.py` untouched, and no `NavReason` is added either (W4).
- §4 ✅ R4.3 — `build_flows` is already bounded by `max_flows`/`max_nodes`; R4.2 — same graph, same
  payload.
- §5 ✅ R5.6 — a subject that joins no flow refuses with a reason, never an empty list (AC1). R5.4 —
  a refusal that routes names a callable tool.
- §6 ✅ R6.5 the proving test is shown red first; R6.3 the fixture is not shaped to the implementation.
- §7 ✅ R7.2/R7.6 — five docs carry the tool count and `test_documented_tool_count.py` enforces they
  agree with `len(TOOL_NAMES)`.

**AC validation — the two values that matter, both re-derived.**

| AC | Ticket's value | Computed here | Verdict |
|----|----------------|---------------|---------|
| AC1 | refuses with a reason | `REASON_NO_SUCH_SYMBOL` / `REASON_NO_MATCHES`, both already in `nav_result.py` | falsifiable; no new vocabulary |
| AC2 | *"no aggregate the question did not ask for"* | falsifiable as a key-set assertion on the payload | falsifiable as written |
| AC3 | gate green at `0.63 / 1.0 / 1.0` | floors confirmed at `gate.sh:132-133`; **current ratio 0.665**, atlas 3328 / grep 2213 | agrees; headroom pinned below |
| AC4 | `flows.py` unchanged except where needed | falsifiable: `git diff --stat` on that one file | falsifiable as written |

**Clarifications, all four self-resolved.** (1) the floors are `0.63 / 1.0 / 1.0`, `gate.sh:132-133`.
(2) **the ratio is an aggregate sum, not a per-question average** — `tokens_to_answer.py:578-582`
divides `grep_sum` by `atlas_sum` over every ratio-eligible correct row. This is load-bearing and is
why 197 failed; the arithmetic is in the design below. (3) a new `NavReason` would need no
`contract_version` bump (`nav_result.py:19-38` is not R3.1) — but (4) **no new reason is needed at
all**, because both states already have exact constants.

## Phase 2 — design

`HANDLES: 5 recalled | 5 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Why the measurement will pass, derived before building it

The gate's ratio is `grep_sum / atlas_sum` **summed across questions**, floor `0.63`. Adding a
question costing `a` atlas tokens and `g` grep tokens keeps the aggregate green when

```
(2213 + g) / (3328 + a) >= 0.63     =>     g >= 0.63a - 116
```

197 spent the whole overview: `a ≈ 2400`, so it needed `g ≥ 1396` and `grep` gave 852 — hence 0.53.
A per-subject payload is `a ≈ 250` (five hops of five short keys, plus a nav envelope), needing
`g ≥ 41`. Reading even one matched fixture file already exceeds that. **The defect 197 hit was the
payload, and this arithmetic says so before a line is written** rather than after a gate failure.

### Handles — each answered with a command

| handle | verdict | command + result |
|---|---|---|
| `count-pin-in-blast-radius` (9, P5) | **traced** | `git grep -ln check_column_defaults` → **15** files for 194's tool. Of those, `test_documented_tool_count.py` forces `README.md` · `AGENTS.md` · `docs/PLAN.md` · `docs/BACKLOG.md` · `docs/TOOLS.md` to state `len(TOOL_NAMES)`, and `test_recognition_probe_protocol.py:60` derives its coverage from `TOOL_NAMES`, so the runbook goes red without a new row. All folded in below |
| `deepest-wins-is-not-a-membership-test` (3) | **traced** | `git grep -n 'def responsibility_layer\|def reading_seed_rank\|def names_test_responsibility'` → `layers.py:226`, `layers.py:235`, `reachability.py:210`. **The lesson binds directly here:** the subject filter IS a membership test, so it uses **exact equality** against `step.qname` / `step.file` / `Flow.module`, never a prefix or deepest-wins predicate |
| `assert-the-consumer-not-the-field` (2) | **traced** | `git grep -n 'estimate_tokens' scripts/tokens_to_answer.py` → tokens are counted on `json.dumps(response)` at `:165`. AC2 is therefore asserted on the **payload key set the agent receives**, not on a dataclass |
| `derived-not-listed-invariant` (R6.7) | **traced** | `tests/test_documented_tool_count.py:29` derives the expected count from `len(TOOL_NAMES)` and `:35` proves the sweep is not vacuous. No hand-kept list is added; the five prose counts move to 24 |
| `route-must-answer` (R5.4) | **traced** | `git grep -c TRY_INSTEAD code_atlas/tools/nav_result.py` → 15 sites. A refusal here routes to `architecture_overview` only where that tool genuinely answers; a subject absent from the index routes to `search_symbol`, which enumerates qnames |

### Approach

A new tool, `code_atlas/tools/trace_capability.py`, taking exactly one of `qname` / `path` /
`module`. It opens the store once, pulls the same bounded rows `generate_onboarding` pulls, builds
flows with `build_flows` **unchanged**, and returns only the flows whose membership test the subject
satisfies — by exact equality on `step.qname`, `step.file`, or `Flow.module`.

The payload is a nav envelope plus the matching flows: `seed`, `seed_file`, `module`, `steps` (each
`qname` · `file` · `layer` · `kind` · `tier`), `layers`, `ended`, `sink`. **No layer table, no
matrix, no hubs, no reachability split, no capability table, no mirrors** — that key-set exclusion is
AC2, asserted as a key set.

### Rejected alternatives

1. **Widen `architecture_overview` with a subject filter.** Rejected: measured and rejected by 197,
   and the ticket forbids it. The envelope is the cost, not the filter.
2. **A cheaper per-path layer lookup** instead of the full `LayerAssignment` (the exposure-checker's
   W6). Rejected: it would report a different layer for the same file than `architecture_overview`
   reports, which is a worse defect than the compute it saves (PLAN §1).
3. **Trace forward from the subject** rather than filtering built flows. Rejected: for a middle hop
   that answers *"what happens from here"*, a different question, and it is the second notion of a
   flow the ticket's exclusion forbids.
4. **Return a suffix of the flow** for a middle-hop subject. Rejected with W3 — see above.
5. **`ratio_eligible: false` with a written note.** The registry permits it (`onb_layers_and_dependencies`
   uses it). Rejected: `grep` genuinely *can* attempt this question, so exempting it would dodge the
   ticket's own constraint that a tool which cannot beat `grep` has not earned its payload.

**Why item 0 exists, and why it is not scope creep.** `build_flows` needs `layer_of` and
`owner_of_dir`, which `build_dataset` assembles inline from `compute_metrics` → `assign_layers` →
`refine_layers` and `find_business_modules` → `directory_owners`. A second copy of that assembly in
the tool is not a second *notion* of a flow, but it is a second *path to one*, and two paths drift.
W6 rejected a cheaper attribution precisely because the tool and the overview must not disagree about
the same file; copying the assembly reintroduces that risk through the back door. One function, two
callers, and `flows.py`'s diff is an addition rather than a change to the derivation.

### Assumptions

| # | Assumption | Tag |
|---|------------|-----|
| A1 | `Flow.module` is populated, so a module subject needs no reverse lookup | **verified** — `flows.py:121`, set from `directory_owners` at `dataset.py:577` |
| A2 | `build_flows` needs no change for a filtered query | **verified** — filtering is over its output; `flows.py` diff will be empty (AC4) |
| A3 | Tokens are counted on the payload, so compute cost cannot flatter or spoil the ratio | **verified** — `tokens_to_answer.py:150-168` |
| A4 | The five documented tool counts are enforced, so none can be missed silently | **verified** — `tests/test_documented_tool_count.py` |

No `novel-untested` third-party or runtime assumption remains.

### Change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|--------|-------------|--------------|----------------|-----|
| 0 | `flows_from_graph(...)` — the seeds + layer + module assembly `build_dataset` does inline, lifted to one pure function both callers use | `code_atlas/onboarding/flows.py`, `code_atlas/onboarding/dataset.py` | `build_dataset` calls it instead of assembling inline; **this is the AC4 "except where the query genuinely needs it" clause being used**, decided at design rather than recorded later as a deviation. Duplicating the assembly in the tool would let the tool and the map disagree about the same flows — the exact defect W6 rejected | AC4, C2, R1 | 0/10 |
| 1 | the tool | `code_atlas/tools/trace_capability.py` (new) | none inbound; it is the new surface | R1, R2, C2, AC1, AC2 | 1/10 |
| 2 | `TOOL_NAMES` + server wiring | `code_atlas/main.py` | `test_mcp_server.py` (`declared == TOOL_NAMES`), `test_documented_tool_count.py` (5 docs), `test_recognition_probe_protocol.py` (runbook) — all derived, all go red without the rest of this list | C3, AC1 | 2/10 |
| 3 | the recognition map line | `code_atlas/tools/prompts.py` | `which_tool` prose; no test derives it, so it is folded in deliberately | C3 | 3/10 |
| 4 | the conformance invoker row | `tests/contract/tool_parity.py` | hand-written per tool — the one place in the trace that is a list, not a derivation | C3 | 4/10 |
| 5 | the runbook row | `docs/runbooks/tool-recognition-probe.md` | derived from `TOOL_NAMES` by `test_recognition_probe_protocol.py:60` | C3 | 5/10 |
| 6 | tool row + count 23 → **24** | `docs/TOOLS.md` | `test_documented_tool_count.py` | R7, C3 | 6/10 |
| 7 | count 23 → **24** | `README.md`, `AGENTS.md`, `docs/PLAN.md`, `docs/BACKLOG.md` | same guard; `AGENTS.md` is tier-1 so `test_agent_chain_budget.py` also binds | R7, C3 | 7/10 |
| 8 | the behaviour question | `scripts/tokens_to_answer_questions.json` | the gate's aggregate ratio — the arithmetic above | R3, C1, AC3 | 8/10 |
| 9 | the suite; then BACKLOG status + frontmatter, ledger, LESSONS | `tests/test_trace_capability.py` (new), `docs/` | `test_backlog_bookkeeping.py`, `test_doc_size_budget.py` | R7, AC1–AC4 | 9/10 |

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|----|-----------|----------------|--------------------|--------------|
| AC1 | integration | integration — a built index; a subject that joins no flow, and one absent from the index, each asserted to carry its reason | n/a | ✅ |
| AC2 | logic | unit — the payload's key set, asserted as a set against a frozen allow-list | n/a | ✅ |
| AC3 | runtime/3p | **the benchmark itself**, run at the unchanged floors with the question in the registry | n/a — the expected trace is hand-read above, before the tool existed | ✅ |
| AC4 | logic | unit — `git diff --stat` names no `flows.py` change | n/a | ✅ |

No `❌`. No AC is input-shape-dependent: each names its own expected value, and AC3's is the
hand-read table in Phase 0 plus the floors. The fixture caveat is real but is a **disclosure**, not a
coverage-gap exclusion — inventing one here would manufacture a `j > 0` stop out of a checkbox.

### Proving test

`tests/test_trace_capability.py::test_one_request_is_traced_without_the_other_requests_files`
— builds the onboarding fixture index, asks `trace_capability(qname="\\Shop\\Controllers\\InvoiceController::index")`,
and asserts the payload names all five hand-read hops **and none of the six files belonging to other
requests**. That second half is the defect 197 measured (`precision 0.944 | unexpected 6`) and is
what a per-flow surface cannot pass.

```
.venv/bin/pytest tests/test_trace_capability.py -q
```

### Rollback + porting

Revert the branch. The tool is additive; `flows.py`, `contract.py` and `NavReason` are untouched, so
nothing downstream changes shape. One repo, so no porting order.

`SCOPE: L` — raised from the ticket's implicit sizing at analysis: 9 change-list items across 12
files, a new MCP tool, and a measurement that gates the whole thing.

## Phase 3 — execute

**Verification sweep — both axes.**

*Axis 1, file set.* 23 files. Every one traces to a change-list row; nothing sits outside it. But
the change list said **12 files** and the realized set is 23 — see the blast-radius finding below,
which is this ticket's main lesson and is recorded as a deviation, not absorbed.

*Axis 2, design conformance.* Every Gate-2 Approach bullet is `implemented-as-approved` except D1–D3
below. W1–W6 were all implemented as chosen; W6 in particular held — the tool derives `metrics`,
`assignment` and `modules` with the same three calls the map uses, and a test proves they agree.

**AC3 — the measurement, which is this ticket's acceptance test.**

```
Ran at 924d75b910ac711c325a2702498e208bbc6df895 (branch point) + this branch's working tree
$ .venv/bin/python scripts/tokens_to_answer.py --min-ratio 0.63 --min-recall 1.0 --min-precision 1.0
{"questions": 31, "atlas_correct": 31, "atlas_tokens": 3698, "grep_tokens": 3065,
 "ratio": 0.829, "ratio_questions": 14, "recall": 1.0, "confidently_wrong": 0,
 "precision_questions": 18, "precision": 1.0, "unexpected": 0}
$ bash scripts/gate.sh
  PASS tokens-to-answer (ratio >= 0.63, recall 1.0, precision 1.0)
  17 passed · 0 failed · 0 skipped
GATE GREEN — all 17 checks passed
```

| | 197 (`summary.flows`) | 199 (`trace_capability`) |
|---|---|---|
| ratio | **0.53** (floor 0.63) ❌ | **0.829** ✅ |
| precision | 0.944 | **1.0** |
| unexpected | 6 | **0** |
| precision-measured questions | 17 | **18** |

The baseline was **0.665**, so the new question did not merely clear the floor — it **raised the
aggregate**. No floor was touched; `gate.sh:132-133` still reads `0.63 / 1.0 / 1.0`.

### The blast radius was 22 sites and the trace found 15

The design's `HANDLES` row for `count-pin-in-blast-radius` ran `git grep -ln check_column_defaults`
and folded in all 15 files. The gate found seven more, in three kinds:

| kind | sites | why the trace could not see them |
|---|---|---|
| **listed, then judged N/A** | `test_sql_confinement`, `test_core_is_language_agnostic`, `test_total_count_semantics` | the trace named them and I dismissed them. A dismissal is recorded as coverage and nothing re-checks it |
| **lists 194's tool is not in** | `tokens_to_answer.bind_tools`, `tokens_to_answer._TOOL_NAMES`, the question registry | no grep for a member can surface a list that never held it — structurally blind, not merely incomplete |
| **tables demanding a REASON** | `docs/TOOLS.md` unbatched verdict, `docs/design/impact-and-claims.md` unsigned caveat | both forced a design answer that existed nowhere: *why is this tool not batched*, *why does it not sign a claim* |

The third kind is the guard working as designed, and both answers are now written down.

### Negative controls (R6.5) — three, each observed red

**Control A — 197's defect: return every flow.** `matched = list(built.flows)`:

```
FAILED tests/test_trace_capability.py::test_one_request_s_answer_excludes_the_other_request_s_entry
FAILED tests/test_trace_capability.py::test_the_traced_hops_are_the_hand_read_ones_in_order
FAILED tests/test_trace_capability.py::test_ac1_a_subject_that_joins_no_flow_refuses_rather_than_answering_empty
FAILED tests/test_trace_capability.py::test_a_file_subject_matches_a_middle_hop_and_returns_the_WHOLE_flow
FAILED tests/test_trace_capability.py::test_the_tool_and_the_map_agree_about_the_same_flows
5 failed, 9 passed
```

**This control failed the FIRST time, and that was the finding.** Against the onboarding fixture the
mutation left the proving test green, because all four of that fixture's flow seeds are the same
controller — `jobs/`, `reports/` and `legacy/` read as no entry layer, so *"every flow"* and *"this
request's flows"* are one set there. **199's stated second defect is not reproducible on the fixture
the ticket names**, and 197's `unexpected 6` came from the overview envelope rather than from other
requests' flows. A two-entry seeded repo was built to make the discrimination visible at all.

**Control B — membership by prefix.** `step.file.startswith(subject)`:
```
FAILED tests/test_trace_capability.py::test_the_qname_and_path_predicates_are_exact_too
```
`deepest-wins-is-not-a-membership-test` (130, 131, 197) pointed straight at this predicate, and the
guard exists because of it.

### The hand-read ground truth disagreed with the model, and the model won

The reading recorded in Phase 0 lists **five** files including `lib/Clock.php`. The tool answers
four. `flows.py` traces one **path to a sink**; `Clock::now` is called from two hops on that path
without lying on it. The ticket's own words are *"from entry to the data it writes"* — a path, not a
reachable set — so the model is right and the question was read one notch broader. The Phase-0
record is left exactly as written; the test carries the correction **with its reason**, and the
benchmark question is worded as a path question rather than quietly fitted to the output.

### Deviations from the approved change list

| # | Deviation | Why |
|---|-----------|-----|
| D1 | 12 files planned, **23** realized | the blast-radius finding above. Seven sites the trace could not or did not reach, plus the two new files |
| D2 | `total_count` **dropped** from the payload after it was written | the tool pages nothing, so it duplicated `len(results)` — 196's F3 class. `truncated` was widened to cover `flows_cut`, so an answer the global cap may have shortened still says so (R5.6) |
| D3 | a strict-prefix flow is **suppressed**, and the count reported as `subsumed` | `build_flows` emits one flow per (seed, sink) pair, so a seed reaching two nodes in the domain layer yields two paths, one contained in the other. Right for the map, over-answering for a per-subject question. `flows.py` is unchanged; the suppression is the query surface's own |

## Phase 4 — review

Reviewer seat **waived** by run arg; the ticket-blind challenger ran and returned **11 of 13 met,
1 NOT met, 1 precedented-but-unimproved**. It ran the benchmark and the mutations itself rather than
trusting a test name, which is what makes the verdict worth anything.

### F1 — R5.6 NOT MET, and the real defect was worse than the one named

The challenger's mutation: `_incomplete()` → `return False` deletes the whole honesty feature and
**310 tests still pass**. No test drove `truncated=True`; the envelope test only asserted the key
exists.

Closing it found a second, larger hole. `_incomplete` checked `walk_truncated or flows_cut > 0`, but
`build_flows` caps at **seed selection** (`ranked_seeds[:max_flows]`), so a dropped flow is never
built and `flows_cut` stays `0`. Measured on a two-entry repo at `max_results=1`:

```
\App\InvoiceController: reason=ok        n=1 truncated=False
\App\ReportController:  reason=no_matches n=0 truncated=False
```

`ReportController` **is indexed and does have a flow.** The cap never traced its seed, so the tool
refused — with `truncated: false`. That is not a silent partial; it is a **refusal that is
confidently wrong**, which is the failure 182's *refuse-rather-than-dump* rule assumes cannot happen
and R5.6 forbids by name. `seeds_traced < seeds_found` is now the third arm of `_incomplete`, and
both arms are tested — the answered subject and the falsely-refused one.

The challenger pointed at the right function for a smaller reason than the one that was there.

### F2 — AC3's margin is more pattern-dependent than the green result shows

Asked whether the benchmark question's `grep.pattern` was chosen to flatter, the challenger ran a
sensitivity sweep and the answer is **partly yes**:

| pattern | files matched | grep tokens | aggregate ratio |
|---|---|---|---|
| `Invoice` (shipped) | 6 | 852 | **0.830** |
| `InvoiceController` | 1 | 102 | **0.630** — at the floor |
| `function index` | 1 | 108 | 0.630 |
| `InvoiceController::index` | 0 | 6 | **0.604 — below the floor** |

**The pattern was not invented for this ticket** — `Invoice` is reused verbatim from the
pre-existing `onb_feature_files`, confirmed by reading the registry — and an agent asking *"what
happens when a user opens the invoice list"* would grep the domain noun before it knew the class
name. **The pattern is kept, and the table is disclosed rather than the pattern changed:** switching
to one that passes by rounding distance would flatter less and inform less. The maintainer can see
exactly how much of the aggregate rests on this one choice.

### F3 — R4.3, precedented and deliberately not tightened

Every call still loads the whole graph and recomputes layers, modules and flows to answer about one
subject. That is `architecture_overview`'s existing pattern, and W6 chose it on purpose: a cheaper
per-path attribution would let this tool and the map disagree about the same file. The ticket's
complaint is payload tokens, and the tool is cheap in tokens and **not** in compute. Disclosed.

### The challenger's own disclosure, which counts against this run

It reported reading `docs/LESSONS.md` and `docs/TOKEN_LEDGER.md` despite the instruction not to —
so **this seat was not fully blind**, and its narrative judgements are worth less than a clean run's.
Its numeric and mutation findings are self-produced and reproducible, and F1 was reproduced here
before being fixed. Recorded rather than discounted: `work_doc_mode: embed` already makes blindness
a manual construction (197's type-3 skill gap), and this is the second run where the mitigation
leaked.

## Phase 5 — finalise

`CLAIMS: 8 claim(s) from 1 lesson entr(ies) | T1=0 T2=7 T3=1 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 2 recurring | 2 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 10 candidate(s) checked | 9 still-true (proceed) | 1 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 2 type-2 claim(s) with seen ≥ 2 | 2 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`LEDGER TOTAL: unmeasured (host surfaces no usage block) · top cost driver: main-loop execute · 2 subagent dispatch, 189.7k measured`

**One candidate was falsified, and it is the ticket's own.** The ten checked are design's four
assumptions (A1–A4), the six exposure-checker decisions (W1–W6, H1 folded)… and the ticket's stated
second defect, *"`summary.flows` returns every flow, so a question about one request claimed 6 files
belonging to other requests"*. That is **false on the fixture the ticket names**: all four of its
flow seeds are the same controller, so every flow IS this request's. 197's `unexpected 6` came from
the overview envelope. The requirement survives — a per-subject tool is still right — but its stated
*cause* did not, and a two-entry repo had to be built before the defect could be seen at all.
Recorded as `199-C3` rather than quietly rewritten.

**The two recurring classes** are `count-pin-in-blast-radius` (10, AGENT_BRIEF P5) and
`read-the-syntax-not-the-text` (4, R6.7) — both already binding as rules, so both are routed and
neither needs promotion. The one promotion candidate is not this ticket's:
`deepest-wins-is-not-a-membership-test` still stands at recurrence 3 with an open destination, and
this ticket used it rather than adding to it.

### DISCLOSURE

**The reviewer seat was OFF** (waived by run arg). **The challenger seat was ON** — and by its own
statement **it was not fully blind**: it read `docs/LESSONS.md` and `docs/TOKEN_LEDGER.md` after
being told not to. A morning reader should discount its narrative and keep its numbers, which are
reproducible and were reproduced here.

Unverified, deliberately not done, or true-but-uncomfortable, in full:

- **AC3's margin is pattern-dependent.** The shipped grep pattern gives 0.830; a narrower and
  equally defensible one gives 0.604, **below the floor**. The table is in Phase 4. The pattern was
  reused from an existing question rather than chosen here, but the aggregate's health rests
  materially on that one string.
- **The tool is cheap in tokens and not in compute.** Every call reloads the whole graph and
  recomputes layers, modules and flows to answer about one subject. The benchmark cannot see this —
  it counts payload bytes — and W6 chose it deliberately over a cheaper attribution that could
  disagree with the map. Not measured, not improved.
- **`docs/tasks/197`'s exclusion E3 is discharged by this ticket**, which was its stated `expiry`.
- **Main-loop token spend is unmeasured**; the call-count ceiling was recorded `unknown` at t0
  rather than invented.
- **`FLOORS-UNCHANGED` was struck from the contract at t0** — "no floor was lowered" holds on an
  empty run, so it describes something other than this run's work. AC3's no-lowering half is proven
  by the diff, not by a condition. This is the second ticket in a row where a negative acceptance
  criterion could not be a contract condition.
- **The hand-read ground truth was corrected by the model**, not the reverse; the Phase-0 record is
  left as first written and the disagreement is stated.
- **Three deviations** (D1 the 12→23 file set, D2 `total_count` dropped after being written, D3
  prefix suppression) and the blast-radius finding: the trace found 15 of 22 sites.
