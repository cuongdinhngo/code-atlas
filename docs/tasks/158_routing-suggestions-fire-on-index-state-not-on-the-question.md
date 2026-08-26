---
id: 158
slug: routing-suggestions-fire-on-index-state-not-on-the-question
title: 'The mandated caller sweep is a habit, not a trigger — routing suggestions fire on index state, never on the question the agent just asked'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [081, 099, 069]
---

## Why this exists (field retro rounds 8–9, 2026-08-25/26)

Two consecutive rounds recorded the **same** miss, one round apart, with two different tool names —
the round's most expensive failure both times:

> Round 8 (§9): the checklist-mandated §P contract sweep (every caller of a tightened signature) was
> run with `grep`, not `find_callers`, even though `CLAUDE.md` names the tool verbatim and the agent
> carries a standing memory *"Symbol questions go to the index, not grep."* Bucket 4 — *knew it, it
> fit, did not think of it at the moment of cost.*
>
> Round 9 (§9): *"Who calls `saveCrm360`?"* was **the pivotal question** of the ticket — the single
> fact that turned a view-only change into a data-loss bug. It was answered by reading a 196-line body
> and grepping. One `find_callers` call would have answered it.

Both retros reach the identical verdict: **"The fix for bucket 4 is a workflow trigger, not a better
description. No description improvement would have changed this round."** The capability is correct
(round 8 probe #19: `arg_position`/`arg_is` exactly right, `args_unrecorded: 0`); it is simply never
invoked at the moment of cost. Every byte of value in round 8's ledger sits behind a call not made.

## Root cause — the routing surface is state-reactive, not question-reactive

- `code_atlas/tools/get_index_status.py:226-234` — `_suggestions()` is the **only** builder of
  `next_tool_suggestions`, and it reacts only to *index state*: it returns
  `[build_or_update_index]` when unbuilt or `staleness != CURRENT`, else `[]`. It never says
  *"you just asked about a method — here is who calls it."*
- `code_atlas/tools/nav_result.py:403-415` — `attach_try_instead()` is the per-answer routing rider,
  but it fires on **miss** paths only (`find_references.py:203`, `include_graph.py:94`). A *successful*
  `read_symbol` of a method body carries no pointer to `find_callers` / `impact`.
- `code_atlas/tools/prompts.py:71-75` — the only place *"Who calls this → `find_callers`"* /
  *"What breaks if I change this → `impact`"* is written down is the `which_tool` prompt (task 081),
  and `prompts.py:1-8` records that these prompts *"surface as human-invoked entries the model never
  sees — so across four field rounds no prompt was ever called."* The routing map exists on a channel
  the agent cannot reach.

So the one channel the agent *does* read (`next_tool_suggestions`, and per-payload `try_instead`)
never carries the next mechanism step for a question that succeeded.

## Scope

- **Make a routing suggestion ride on a successful answer, keyed to the answer's shape** — not only on
  a miss and not only on index staleness. The load-bearing case: a `read_symbol` / `file_outline` that
  returns a method or function body carries a suggestion pointing at `find_callers` / `find_references`
  / `impact` for that symbol ("who calls this · what breaks if I change it"). Reuse the existing
  `next_tool_suggestions` field or the `try_instead` rider; do not invent a third channel (093).
- **Decide the trigger for the §P signature sweep.** Round 8's mandated sweep is *"every caller of a
  tightened signature."* Evaluate whether the edit-index hook (036) can emit that suggestion when a
  diff changes a signature, so the trigger fires at edit time rather than relying on recall. Design
  may land this as a hook signal, a payload rider, or both — the ticket requires the decision recorded,
  not a specific channel.
- **Keep it out of the cheap path when it earns nothing** (061): a suggestion attaches only where a
  next step is genuinely likely, never on every payload.

### Explicitly not in scope

Auto-*executing* the suggested call. This ticket surfaces the routing at the moment of cost; whether a
client acts on it stays the client's decision.

## Constraints

- **R1.1** — no language branch. The suggestion keys on node kind (a method/function symbol), which is
  contract vocabulary, never on the language.
- **061 / R7.1** — additive, omit-when-absent; no field on a payload that has no next step to offer.
- **R4.2** — deterministic: the same answer yields the same suggestion.

## Acceptance criteria

1. A successful `read_symbol` of a method/function symbol carries a routing suggestion naming
   `find_callers` / `impact` for that symbol, pinned by a test; a `read_symbol` of a non-callable node
   does not (the suggestion is earned, not universal).
2. The suggested names are registered, callable tool names (093), asserted against the tool registry,
   not string literals.
3. A decision is recorded on the signature-change trigger: whether the edit-index hook (036) emits the
   §P caller-sweep suggestion, with the mechanism shown or explicitly declined with a reason.
4. The common payload for an answer with no plausible next step is byte-identical to today (061).
5. Determinism holds (R4.2).

## References

Field retro rounds 8–9, finding **8-C** / **9-F** (lineage **7-I** — `arg_position`/`arg_is`
invisible until a schema is fetched). `code_atlas/tools/get_index_status.py:226-234` (`_suggestions`),
`code_atlas/tools/nav_result.py:403-415` (`attach_try_instead`), `code_atlas/tools/prompts.py:1-8,71-75`
(the human-only routing map). Related: [081](081_routing-prompts-are-not-in-the-agents-surface.md)
(the prompts are unreachable), [099](099_write-time-signal-seam.md) (every decision made without the
graph wanted a line inside a `Read` already happening), [069](069_tool-names-do-not-say-what-they-answer.md),
[093](093_try-instead-is-not-a-callable-tool-name.md), [036](036_edit-index-hook.md).

---
MANGO WORKING DOC (below this line is NOT part of the raw ticket)

## Session status
- Phase: finalise (complete). TIER: full. SCOPE: S. CHALLENGER: ON.
- work_doc_mode: embed (plain local-file ticket).
- Reviewed at: challenger-only (reviewer waived by run args; challenger ON).

## refine
PREMISE: 3 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)
RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)
REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes

## analysis
CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision
RULE SECTIONS: 3 applicable — 3 by change-type | 0 by recalled handle — §R1.1 (rulebook) ✅, §061 (task) ✅, §R4.2 (rulebook) ✅
SECTIONS: 3 found (Scope, Constraints, Acceptance criteria) | 3 decomposed | ROWS: C=3 R=3 G=1 AC=5

## design
`nav_result.attach_next_tools(payload, kind)` sets `next_tool_suggestions = [find_callers, impact]`
when `kind in contract.CALLABLE_KINDS` (Function/Method) — reusing the existing field, not a third
channel (093), keyed on node kind not language (R1.1). read_symbol calls it only on the successful,
non-stale body-read path; misses/stale/ambiguous returns never reach it (AC4 byte-identical). The
tool names are literals in nav_result (it cannot import the tool modules — they import it), asserted
callable against `main.TOOL_NAMES` by the test (AC2).

**AC3 — signature-change trigger decision: DECLINED for the edit-hook, with reason.** The edit-index
hook (036) reparses a changed file but does not diff old-vs-new signatures, and its output channel
(hook stdout to the client) is separate from the tool-payload routing this ticket lands. Detecting a
"tightened signature" needs an AST-level before/after comparison the hook has no capability for today;
building it is a distinct, larger change. The landed trigger is the payload rider: the moment an agent
reads a callable body (the exact moment of cost in rounds 8-C/9-F), the answer names find_callers /
impact. A signature-diff-at-edit-time signal remains a future follow-up on 036, not this ticket.

**file_outline left uncovered (challenger scope note), with reason.** The Scope paragraph mentions
`file_outline`, but it returns a symbol *map* (line ranges, no body) listing many symbols — a single
call-level `next_tool_suggestions` cannot name which symbol's callers to fetch, and a per-hit rider
would fire on every row (061). AC1 names only `read_symbol` (a single body). The load-bearing case is
read_symbol; file_outline is out of the pattern by shape.

EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor
HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (n/a) | 0 unanswered

## execute
No design-invalidated escalation; no stuck-detector trips. AC1, AC2, AC4, AC5 met; AC3 decided (declined, above).

## review (challenger-only — reviewer waived)
CHALLENGER: ON. Ticket-blind challenger verdict: **PASS** — AC1/AC2/AC4/AC5 + R1.1 + 061 + no-third-
channel + miss/stale-exclusion all MET with path:line (it ran the new tests in Docker, 5 passed);
AC3 marked CAN'T TELL (the decision record lives in this working doc, above). Its one non-blocking
note (file_outline vs the Scope paragraph) is dispositioned above. Result: clean (reviewer only —
CHALLENGER: ON).

### Cost-ledger
| phase | dispatch | round | tokens |
|---|---|---|---|
| review | challenger (ticket-blind) | 1 | 57,441 |

main-loop: unmeasured (host surfaces no usage block).

## finalise
Delta-green in Docker (`scripts/docker-test.sh`, linux): pytest 2107 passed / 1 skipped / 0 failed;
`gate.sh` in-container — ruff · mypy · pytest · tokens-to-answer (ratio ≥ 0.63) · R1.1/R2.2/R4.1
grep-gates · php -l · composer validate all PASS; phpstan `[OK]` with dev deps.

CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified
FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)
RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)
RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (none) | 0 left in lessons_path
PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0
LEDGER TOTAL: 57441 · top cost driver: review/challenger
