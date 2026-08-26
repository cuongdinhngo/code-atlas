---
id: 165
slug: find-callers-splits-across-twins-and-says-reason-ok
title: '`find_callers` on a fully-qualified twin silently omits callers bound to its sibling definition, and says `reason: "ok"`'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [013, 054, 161, 122]
---

## Why this exists (field retro round 10, 2026-08-26)

The round's one **wrong turn in real work**, and it landed on a checklist-mandated §P contract sweep —
the single question type the consuming repo's own process says grep cannot satisfy:

> `find_callers` on the fully-qualified `\Src\System\Event\EventRunner::bedPriceCheck` returned
> **2 src callers + 2 tests** and **omitted `public/getChangeMaintenance.php:1192`** — the one call site
> that actually TypeErrors under the signature change. That file has no `use` statement, so its bare
> `EventRunner::` binds to the **`legacy/` twin**. `reason: "ok"`, `total_count` confident, no marker.
>
> "A confident false *one call site*. Recovered only because I ran the bare-name query **and** a grep
> cross-check. Had I trusted it, the PR would have claimed a swept surface it had not swept."
>
> §16: *"Did it make you worse anywhere? **Yes, once.** … Saved only by a grep cross-check that
> `CLAUDE.md`, not the tool, taught me to run."*

Round 9 recorded this shape on `find_references` (7-A) and the retro's verdict is that **it has now
moved to `find_callers`**: the alias/twin split under-reports **callers**, not just references — and
`find_callers` is the tool the mandated sweep routes to.

**Priority note from the retro's §16 and the maintainer's review:** this must land **before** any
roll-out work. At reach 1, a confidently-partial sweep is caught by one developer's cross-check habit;
at reach N that habit is prose in a `CLAUDE.md` nobody is obliged to read.

## Root cause

- `code_atlas/find_callers.py:232` — `reason = relation_reason(hit_total=outcome.total_count,
  symbol_indexed=indexed)`. The reason is a pure function of *this qname's* hit count. Nothing asks
  whether the same trailing name is defined elsewhere and carrying callers of its own.
- `code_atlas/find_callers.py:214-225` — `unresolved_bare_calls` exists, but it counts a **different
  failure**: bare CALLS sites that target *nothing* after the alphabetical Method cap (054). The round-10
  case is the opposite — the call site resolved **successfully**, to a real sibling node. It is not
  unresolved, it is attributed elsewhere.
- `code_atlas/find_callers.py:255` — `attach_ambiguous_definitions(result, definition_sites(subject_nodes))`
  fires on `nodes_by_qualified_name(lookup)`, i.e. **exact-qname** twins only. `\Src\…\EventRunner::bedPriceCheck`
  and `\EventRunner::bedPriceCheck` are different qnames, so the disclosure never triggers.
- Contrast `code_atlas/tools/find_references.py:202-203`, which already sets
  `result["authoritative"] = False` when the answer is caveated. `find_callers` has no equivalent.

The graph is not wrong — the edges are correct per qname. The **payload** is wrong: it presents a
partition of the callers as the whole of them.

## Scope

Make `find_callers` disclose that the subject has siblings and that callers may sit on them.

1. When the subject's **trailing name** (the `bare_name` already computed at `find_callers.py:214`)
   has definitions under other qnames, disclose them — the `definition_sites` shape `read_symbol` and
   `impact` already return (078 / 161), so the agent sees the same three trees it sees elsewhere.
2. Caveat the count: `authoritative: false` (find_references' spelling, `find_references.py:203`) or a
   counted `callers_on_siblings: N`, so a swept-surface claim cannot be made from a partition.
3. `reason` must stop reading `"ok"` for an answer that is knowingly partial, **or** the caveat must be
   prominent enough that `ok` is survivable. Design records which, and why.

Whether the sibling callers are **counted** (one extra query) or merely **named** (sites only) is a
design decision with a measured cost, recorded with the rejected alternative.

### Explicitly not in scope

- Merging twins, or picking one. The repo's premise is that the same identifier is legitimately defined
  three times; 161 already established that **refusal beats an arbitrary choice**.
- `find_references` (7-A's original home) — same class, different tool; a follow-up if the mechanism
  generalises.
- Any change to edge storage or the resolver.

## Constraints

- **R1.1** — no language branch; the trailing-name split is a qname-shape question, not a PHP one.
- **061** — omit-when-empty: a subject with no siblings must be byte-identical to today.
- **R3** — no new contract vocabulary; no `contract_version` bump.
- **R4.2** — order-stable site lists (161's `_split_ambiguous` precedent).
- **Cost** — `find_callers` is a hot mechanism tool. The sibling lookup must be one bounded query, and
  its per-call cost measured against the tokens-to-answer gate.

## Acceptance criteria

1. `find_callers` on a qname whose trailing name has ≥ 2 definitions discloses the sibling definition
   sites and carries the caveat (`authoritative: false` or the design's recorded equivalent) — pinned by
   a fixture with a twin pair, one caller on each.
2. The same call on a subject with exactly one definition is **byte-identical** to today (061).
3. An answer that is knowingly partial cannot present a bare `reason: "ok"` with an uncaveated
   `total_count`; the chosen shape and its rejected alternative are recorded in the working doc.
4. The added per-call cost is measured and stays within the tokens-to-answer gate.
5. `unresolved_bare_calls` / `bare_name_truncated` (054) behaviour is unchanged — this is a distinct
   failure and both must remain distinguishable.
6. Determinism (R4.2), no language branch (R1.1), no bump (R3).

## References

Field retro round 10 §3 #16, §7 (row `bedPriceCheck`), §10.d (*"I got it right because I did not believe
`find_callers`"*), §14 (7-A **moved to `find_callers`**), §14.a (carve-out (f) **extended to
`find_callers`**), §15 ticket 4. `code_atlas/tools/find_callers.py:214-225,232,255`;
`code_atlas/tools/find_references.py:202-203`. Related: [013](013_nav-tools.md),
[054](054_bare-name-callers-silent-drop.md), [161](161_impact-resolves-a-shared-qname-to-one-twin-and-carries-no-freshness.md)
(refusal over arbitrary binding), [122](122_exact-miss-shaping-discards-a-resolved-subject.md).
