---
id: 163
slug: read-symbol-minimal-is-byte-identical-to-standard
title: '`read_symbol` `detail_level: "minimal"` is byte-identical to `standard` — a documented knob that does nothing'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [014, 066]
---

## Why this exists (field retro rounds 7 & 9)

`read_symbol` advertises a `detail_level` of `minimal` / `standard`, but the two return exactly the
same bytes — verified across two rounds:

> Round 9 (**7-F**): `read_symbol` at `minimal` and at `standard` on the same method — *"same keys,
> same full doc comment, same full body, same `line_start`/`line_end`. Not one byte differs."*
> Unchanged from round 7, which found the same.

Elsewhere `minimal` earns its name — `get_index_status`'s `minimal` deliberately drops provenance and
`edge_health` to stay ~100 tokens (task 066). On `read_symbol` it is a promise the payload does not
keep: a caller who asks for the cheap shape pays the full shape and cannot tell.

## Root cause

- `code_atlas/tools/read_symbol.py:33` declares `DetailLevel = Literal["minimal", "standard"]` and
  threads `detail_level` through every code path.
- `code_atlas/tools/read_symbol.py:260` — `_result()`, the found-symbol payload builder, opens with
  `del detail_level, db_path`: the parameter is **explicitly discarded**. The payload keys are the
  same for both levels; the `source` slice (`_slice` → `declaration_slice`, `read_symbol.py:226-228`)
  is the full declaration **plus the contiguous comments above it** regardless of level.
- `_empty()` (`read_symbol.py:234`) does the same `del detail_level`.

So the knob has no effect anywhere in `read_symbol`.

## Scope — pick one, record why

- **Option A — remove the knob.** Drop `detail_level` from `read_symbol`'s signature and payload
  plumbing. Honest: `read_symbol` returns a symbol's declaration; there is no cheaper useful shape, so
  the parameter should not exist. Simplest, and it removes a misleading affordance.
- **Option B — make `minimal` actually trim.** Have `minimal` return the declaration **without** the
  contiguous comment block that `standard`'s `source` carries above the signature. This also narrows
  the 8-H trap (the returned `line_start`/`line_end` name the symbol, while `source` silently includes
  the docblock above — a caller splicing by the range gets different text than `source`); a comment-free
  `minimal` `source` would then match its own range.

Design chooses A or B with the reason recorded; do **not** ship both. Default recommendation: **A**
(YAGNI / R7.1) unless a measured caller wants the trimmed body.

### Explicitly not in scope

Changing `get_index_status`'s `detail_level`, which is correct and load-bearing (066).

## Constraints

- **R7.1** — smallest thing that makes the surface honest; removing a no-op parameter is smaller than
  inventing behaviour for it.
- **R3** — `detail_level` is a tool argument, not contract vocabulary; no `contract_version` bump.
- **061** — if Option B, the `minimal` payload must be measurably smaller than `standard`, not merely
  differently shaped.
- **R4.2** — deterministic either way.

## Acceptance criteria

1. Either `read_symbol` no longer accepts `detail_level` (Option A), **or** its `minimal` payload is
   measurably smaller than `standard` on a symbol that has a docblock (Option B) — pinned by a test.
2. The chosen option and the reason for rejecting the other are recorded in the working doc.
3. No existing caller/test silently breaks: every reference to `read_symbol(..., detail_level=...)` is
   re-read and updated with the verdict recorded.
4. Determinism holds (R4.2); no `contract_version` bump (R3).

## References

Field retro rounds 7 & 9, finding **7-F** (and touches **8-H** — range vs. docblock in `source`).
`code_atlas/tools/read_symbol.py:33,226-228,234,260`. Related:
[014](014_search-read-outline.md) (read_symbol's origin), [066](066_limit-clamped-silently.md)
(where `minimal` genuinely trims and why it matters).

---
MANGO WORKING DOC (below this line is NOT part of the raw ticket)

## Session status
- Phase: finalise (complete). TIER: full. SCOPE: S. CHALLENGER: ON.
- work_doc_mode: embed (plain local-file ticket).
- Reviewed at: challenger-only (reviewer waived by run args; challenger ON).

## refine
PREMISE: 2 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)
RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)
REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes

## analysis
CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision
RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — §R7.1 (rulebook) ✅, §R3 (rulebook) ✅, §R4.2 (rulebook) ✅, §061 (task) ✅, §R5 (rulebook) ✅
SECTIONS: 3 found (Scope, Constraints, Acceptance criteria) | 3 decomposed | ROWS: C=4 R=2 G=1 AC=4

## design — chosen option and why the other was rejected (AC2)
**Option B chosen** (make `minimal` actually trim), **Option A rejected**. The ticket recommended A
(remove the knob) by default, but A is not viable here: `tests/test_mcp_server.py` enforces the **R5
invariant that every registered tool exposes `detail_level`** (`declared_levels()` +
`set(declared) == set(TOOL_NAMES)`); removing it from `read_symbol` would break that contract and
force editing a load-bearing invariant. B keeps the uniform surface, makes the knob meaningful, and
**also closes the 8-H trap**: `minimal`'s `source` is now the declaration range alone, so it matches
the returned `line_start`/`line_end`, while `standard` keeps the docblock. Implemented with one
additive `include_comments` flag on `source_slice.declaration_slice` (default `True`, so the
onboarding read-through caller (118) is unchanged).

EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor
HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (n/a) | 0 unanswered

## execute
No design-invalidated escalation; no stuck-detector trips. All ACs met.

## review (challenger-only — reviewer waived)
CHALLENGER: ON. Ticket-blind challenger verdict: **PASS**. AC1/AC3/AC4 MET with path:line; AC2
(record the chosen option + rejection reason) it marked CAN'T TELL only because it may not read this
working doc — recorded above. All constraints (R3 no bump, R4.2 determinism, R5 invariant intact,
8-H closed, R7.1 additive) MET; no scope creep. It also caught a stale `PLAN.md` read_symbol row,
now corrected. Result: clean (reviewer only — CHALLENGER: ON).

### Cost-ledger
| phase | dispatch | round | tokens |
|---|---|---|---|
| review | challenger (ticket-blind) | 1 | 55,210 |

main-loop: unmeasured (host surfaces no usage block).

## finalise
Delta-green in Docker (`scripts/docker-test.sh`, linux): pytest 2083 passed / 1 skipped / 0 failed;
`gate.sh` in-container — ruff · mypy · pytest · tokens-to-answer (ratio ≥ 0.63) · R1.1/R2.2/R4.1
grep-gates · php -l · composer validate all PASS; phpstan `[OK]` with dev deps. Doc budgets intact
(PLAN 24000/24000, BACKLOG under).

CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified
FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)
RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)
RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (none) | 0 left in lessons_path
PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0
LEDGER TOTAL: 55210 · top cost driver: review/challenger
