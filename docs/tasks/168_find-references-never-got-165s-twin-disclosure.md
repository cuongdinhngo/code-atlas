---
id: 168
slug: find-references-never-got-165s-twin-disclosure
title: '`find_references` under-reports an alias-backed class by 4.7× and still says `reason: "ok"` — 165 fixed the tool 7-A moved to, not the tool it was filed against'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [165, 013, 122]
---

## Why this exists (field retro round 11)

165 shipped `sibling_definitions` + `authoritative: false` on `find_callers`, and round 11 verified it
in real work — it named a twin the evaluator would not have opened, and the disclosure changed a
shipped PR. **The same round measured the tool 7-A was originally filed against and found no caveat at
all:**

```
find_references(Alpha\Plan\Plan)
  →  total_count: 16,  4 in src/,  reason: "ok",  no `authoritative` field
```

against **19** real `new Plan(` / `extends Plan` sites under `src/` = **21.1 % coverage**, with
the registry line at `config/legacy_aliases.php:1357` routing the bare name to **both** region classes.

> Round 11 §12.e(f): *"the round's sharpest code finding."*
> §14 (7-A): *"**⚠️ SPLIT — the claim is half true, and the wrong half was fixed.** Fixed on
> `find_callers`… **NOT fixed on `find_references`** — 16 hits, 4 in `src/`, `reason:"ok"`, no
> `authoritative` field at all… r9 measured 0.6 %; better, still a 4.7× under-report at a confident
> `ok`."*
> §15 ranks this the round's **single requested change**.

The asymmetry is the defect: two tools answer the same twin-shaped question, one discloses the
partition and one presents it as whole. An agent that has learnt to trust `find_callers`' caveat has no
reason to suspect its sibling tool is silent.

## Root cause

- `code_atlas/tools/find_references.py:202-203` — `authoritative` is set **only** when
  `all(hit.get("confidence_tier") == "DYNAMIC" for hit in results)`. The caveat is keyed on **tier**,
  not on whether a same-named definition exists elsewhere, so a fully-RESOLVED partition reads clean.
- `code_atlas/tools/find_references.py:199` — `attach_ambiguous_definitions(result, definition_sites(nodes))`
  discloses duplicates of the **exact qname**. A twin under a *different* qname (`Alpha\…\Plan` vs a
  bare `Plan` in another tree) is not a duplicate of the qname asked for, so nothing attaches.
- `code_atlas/tools/find_callers.py:236-243` — the machinery already exists: one bounded
  `store.nodes_by_name(bare_name, …)`, filtered against the looked-up qname, rendered by
  `definition_sites`. It was pointed at one tool.
- `code_atlas/tools/find_references.py:168` — `reason = relation_reason(hit_total=…, symbol_indexed=…)`
  is a pure function of this qname's hit count, the same shape 165 repaired on `find_callers.py:253`.

## Scope

Give `find_references` the disclosure `find_callers` has, for a class-shaped subject.

1. When the subject's trailing name has ≥ 2 definitions under other qnames, disclose the sibling
   definition sites and carry the caveat (`authoritative: false`, or the design's recorded equivalent).
2. Keep the existing all-`DYNAMIC` caveat **distinguishable** from the new twin caveat — they are
   different reasons for the same field, and an agent that cannot tell them apart cannot act on either.
3. Design records which shape it chose and what it rejected (a count vs named sites; one field vs two).

### Explicitly not in scope

- **Ranking or filtering the siblings** — that is [171](171_sibling-definitions-fires-on-most-calls-and-is-unranked.md),
  which applies to both tools once this one has the field.
- Reading the alias registry as a data source. The graph does not model it; a caveat that says
  *"this count is a partition"* is the honest endpoint, not a resolved count.
- Changing the reference query, its ranking, or the FTS path.

## Constraints

- **061** — a subject with exactly one definition of its trailing name is **byte-identical** to today.
- **Cost** — one bounded query, the shape 165 measured at ~1.35 ms worst case. `find_references` is
  reached from sweeps; no per-row query.
- **R5.5** — the caveat is sourced from the computation that produced it, not from a table of names.
- **R1.1** no language branch · **R3** no bump (the field exists in this tool's vocabulary already) ·
  **R4.2** order-stable sites.

## Acceptance criteria

1. `find_references` on a subject whose trailing name has ≥ 2 definitions discloses the sibling sites
   and carries the caveat — pinned by a fixture with a twin pair, one reference to each.
2. The same call on a subject with a unique trailing name is byte-identical to today (061).
3. An answer whose hits are all `DYNAMIC` and an answer that is twin-partitioned are **distinguishable**
   in the payload; both cases pinned.
4. `attach_ambiguous_definitions` (exact-qname duplicates) and the new disclosure remain distinct and
   can both appear on one payload.
5. Added per-call cost measured and inside the tokens-to-answer gate.
6. Determinism (R4.2), no language branch (R1.1), no contract bump (R3).

## References

Field retro round 11 §12.e(f) (the measurement), §14 row 7-A (**SPLIT**), §15 (the round's one
requested change), §9.b (veto log — the carve-out this would let us narrow); round 9's 0.6 % on the
same tool. `code_atlas/tools/find_references.py:168,199,202-203`;
`code_atlas/tools/find_callers.py:236-243,253`. Related:
[165](165_find-callers-splits-across-twins-and-says-reason-ok.md) (the machinery),
[013](013_nav-tools.md), [122](122_exact-miss-shaping-discards-a-resolved-subject.md).
