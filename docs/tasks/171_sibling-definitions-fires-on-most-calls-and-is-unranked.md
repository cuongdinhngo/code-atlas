---
id: 171
slug: sibling-definitions-fires-on-most-calls-and-is-unranked
title: '`sibling_definitions` fires on 83 % of calls and lists nine sites unranked — a caveat that always fires is a carve-out, not a signal'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [165, 168, 013]
---

## Why this exists (field retro round 11)

165 is the loop's first fix to change shipped work, and the same round found the limit of the shape it
chose. Round 11's §12.d — the *fired, noticed, changed nothing* box that produced 165 in the first
place — records it as this round's design finding:

> *"`authoritative: false` fired on **5 of 6** `find_callers` subjects… The one clean subject was
> `RegionManager::dualView` — a symbol invented after the port, with no twin. On the one call that
> mattered it was load-bearing. On the other four it was ~800 B I skipped. **A caveat that fires on
> 83 % of calls cannot be a signal to act on; it can only be a standing instruction — which is what a
> carve-out already is.** So 165 repaired the *instance* (it named the file) without repairing the
> *policy* (I still cross-check every sweep)."*
>
> *"**What it would have to do instead:** rank or filter the siblings… `sibling_definitions` currently
> lists nine files with equal weight, of which one was the one I needed and eight were noise I had to
> triage by hand. **That is the next 165, and it is the highest-value code ticket in this file.**"*

§9.a states the same conclusion from the obligation side: the disclosure made a mandated sweep
*survivable* — *"a grep I run because the tool pointed at a file is a different act from a grep I run
because I cannot trust the tool"* — but it *"cannot retire the cross-check as a policy, only aim it in
the instance."* §6 prices the noise: **807 B on the subject that mattered, ~800 B × 4 where it did not.**

## Root cause

- `code_atlas/tools/find_callers.py:236-243` — siblings are every `store.nodes_by_name(bare_name,
  kind="Method", limit=config.max_results)` row whose qname differs from the lookup, rendered by
  `definition_sites`. **No ordering, no weight, no partition** — the payload cannot say which sibling a
  given caller is likely to bind to, though the site list already carries the file path (and therefore
  the subtree) of each.
- `code_atlas/tools/find_callers.py:279-281` — the caveat attaches whenever `sibling_sites` is
  non-empty. In a tree where the same trailing name exists in two regions plus a compat layer, that is
  the ordinary case, not the exception.
- `kind="Method"` (`:239`) is a deliberate narrowing from 054's lesson (a Function `\App\put` is not a
  bare Method `put`) — but it means a **Function** twin is silently not disclosed. Worth confirming or
  recording as accepted.

## Scope

Turn the disclosure from a list into an ordering, without hiding anything.

1. Rank or partition `sibling_definitions` by evidence the graph already holds — the **subtree/region**
   of each site is available from the path in `definition_sites`; whether **import/`use` evidence** for
   the calling files is reachable at bounded cost is a design question the ticket delegates.
2. The full list stays available; ranking must not drop a site (the eight "noise" sites were noise for
   one question, not for every question).
3. Apply the same ordering to `find_references` once [168](168_find-references-never-got-165s-twin-disclosure.md)
   gives it the field — one definition site for the ordering (R6.7), not two.
4. Record whether the `kind="Method"` narrowing at `:239` stands, with the reason.

### Explicitly not in scope

- Resolving the binding. The edge model is qname-keyed with no target node id (161's AC1 deviation);
  this ticket ranks a disclosed partition, it does not turn it into an answer.
- Suppressing the caveat when it fires often. A frequent true caveat is not a false one; the fix is
  ordering, not silence.
- Reading the consuming repo's alias registry.

## Constraints

- **Cost** — 165's budget: one bounded query, ~1.35 ms worst case. Ranking must reuse rows already
  fetched; no query per sibling and none per caller.
- **061** — a subject with no sibling stays byte-identical; a subject with exactly one sibling should
  not grow.
- **R5.5** — the ordering is sourced from the computation, and the payload says what it ranked by.
- **R6.7** — one definition site for the ordering, shared with `find_references`.
- **R1.1** no language branch · **R3** no bump · **R4.2** the order is deterministic for identical input.

## Acceptance criteria

1. `find_callers` on a subject with ≥ 2 siblings returns them in a **stated, deterministic order** whose
   basis is named in the payload — pinned by a fixture with siblings in different subtrees.
2. No site is dropped by ranking; the count is unchanged from today for the same subject.
3. `find_references` uses the same ordering once 168 lands, from one definition site (R6.7) — pinned, or
   the dependency recorded if 168 has not landed.
4. A subject with no sibling is byte-identical to today (061); the one-sibling case is measured.
5. Added cost measured against 165's ~1.35 ms and the tokens-to-answer gate; no per-sibling query.
6. The `kind="Method"` narrowing is confirmed or changed, with the reason recorded.
7. Determinism (R4.2), no language branch (R1.1), no bump (R3).

## References

Field retro round 11 §12.d (**the round's design finding — "the next 165, and the highest-value code
ticket in this file"**), §9.a (survivable, not policy-repairing), §6 (the 807 B / ~800 B × 4 price),
§14.a carve-out (f). `code_atlas/tools/find_callers.py:236-243,279-281`. Related:
[165](165_find-callers-splits-across-twins-and-says-reason-ok.md) (the shape this completes),
[168](168_find-references-never-got-165s-twin-disclosure.md) (the second consumer),
[013](013_nav-tools.md), [054](054_bare-name-callers-silent-drop.md).
