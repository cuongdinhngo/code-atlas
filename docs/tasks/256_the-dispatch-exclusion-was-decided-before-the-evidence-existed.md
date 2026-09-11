---
id: 256
slug: the-dispatch-exclusion-was-decided-before-the-evidence-existed
title: '222 shipped the string-literal→target rule engine and excluded dispatch semantics on the reasoning that "the field correctly assigns routing to grep" — two field rounds later grep did not catch it, a code review did, after a fix landed on the wrong one of two parallel renderers; the exclusion is discharged and what is missing is whether a rule may target a file'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [222, 221, 063]
---

## Why this exists (field retro — anchor-repo, 2026-09-11, rounds 18 and the BETA QA batch)

222 built exactly the machinery this needs — find every call to a named setter, take the Nth string
literal, emit a `HEURISTIC` edge to a templated target — and drew its boundary in E2:

> SELECT-list order and dispatch-table semantics are not [in reach] — do not claim them. […]
> routing/dispatch semantics, **which the field correctly assigns to grep**.

That was the right call on the evidence of the day. **The evidence has since arrived and it says the
opposite.** In the BETA QA session the evacuation photo had two renderers: a flat PHP file at the web
root that `public/js/evacuationList.js` AJAX-calls **by name**, and a parallel MVC model. The agent
fixed the MVC one. grep did not catch it. A code reviewer did, after the wrong fix was written:

> Could `find_callers` have caught it? No — the live dispatch is JS → a flat PHP file at the web root
> via an AJAX string. […] `find_callers` confirms reachability *within* the PHP call graph; it does
> not tell you which of two parallel PHP renderers the front end invokes.

Round 18 produced the same shape from the other direction: reachability there was decided by a
file-scope `require_once` taking the class name before any alias resolves — *"a load-order fact, not a
graph fact"*. The two together retire E2's premise: routing is not a question grep answers here, and
it cost a wrong shipped fix.

## Root cause

`CA_INDIRECTION_RULES` resolves a string literal to a **symbol** qname through `target_template`. The
dispatch case names a **file** — `getMemberEvacReport.php` as a string inside a `.js` file — and the
anchor repo's live rule file is one `view_data` entry, so nothing exercises a file-shaped target:

```json
{"view_data": [{"setter": "setData", "key_arg": 1, "key_from": "array_keys"}]}
```

So this is not new machinery. It is one question — *may a rule's target be a File node?* — plus the
disclosure that 251 also asks for: an answer about the PHP call graph must not read as an answer about
what the browser invokes.

## Scope

- **A file-shaped `target_template`.** A rule whose resolved target names an indexed file links to
  that `File` node. Tier stays `HEURISTIC` (or `DYNAMIC` — phase 2 decides); it is a string match, and
  the tiering must say so.
- **The caveat 251 also needs.** When a caller asks a reachability question about a subject whose
  language has a live string-dispatch surface, the answer states what it does not establish. Filing
  both is deliberate: 251 words the caveat, this ticket gives it something true to point at.
- **Not in scope:** discovering the mapping automatically. 222 refused that at 063 and 152 — `args`
  carries *"the category, never the value"* — and nothing here changes it. The rule stays the
  consumer's configuration, which is also what keeps R2 intact: the adapter learns no repo's names.

## Constraints

- **R2 — standard over sample.** The rule lives in the consumer's rule file. No adapter and no core
  file may name `main.php`, an AJAX convention, or any repo's dispatch shape.
- **R4.2 / 222's AC2** — with no rule configured the graph is byte-identical. This feature costs a
  non-user nothing, and that property is the reason 222 was allowed at all.
- **R5.6** — a string-matched edge is never `RESOLVED`. A dispatch answer says it is a candidate.
- **222's AC4** — a rule whose template resolves nothing reports that in `BuildReport`; a file-shaped
  target that matches no indexed file must fail the same loud way, not vanish.

## Acceptance criteria

- **AC1** A rule whose `target_template` resolves to an indexed file produces an edge to that `File`
  node, and `find_callers` / `find_references` on that file return the dispatching site.
- **AC2** The proving fixture is the field shape: a `.js` file containing a bare filename string, a
  PHP file of that name, no symbol relation between them — zero hits before, the dispatch site after.
- **AC3** With no rule configured, the graph is byte-identical (222 AC2, re-pinned).
- **AC4** A file-shaped template matching nothing is reported in `BuildReport`, not silently dropped.
- **AC5** Tier is never `RESOLVED`, and the payload names the rule that produced the edge (`rule: true`,
  as 222 already does).

## References

- [222](222_the-cross-language-link-is-one-rule-target-away-from-machinery-that-exists.md) — the engine,
  its E2 exclusion, and AC2's byte-identity property this must preserve.
- [221](221_a-zero-is-modelled-when-every-caller-is-in-another-language.md) — the crossing census that
  makes an unmeasured cross-language answer self-diagnosing.
- [251](251_the-resolved-caller-can-be-off-the-page.md) — the caveat half; this ticket is the half that
  makes the caveat pointable at a real edge.
- `.code-atlas/indirection-rules.json` in the anchor repo — the one live rule today, symbol-shaped.
