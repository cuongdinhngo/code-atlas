---
id: 179
slug: impact-modules-inherits-half-the-seed-fix
title: '`impact_modules` inherits 169''s seed classification but not its twin refusal — and never had 161''s either'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [169, 161, 140]
---

## Why this exists

Filed by [169](169_impact-path-seed-walks-every-symbol-and-its-twins.md) AC6, which required
`impact_modules`' inheritance of the seed fix to be *"confirmed or filed"*. It is **half inherited**,
and the missing half predates 169.

| | `impact` | `impact_modules` |
|---|---|---|
| path seed classified through `_resolve_seed` (169) | yes | **yes** — both call `resolve_seeds` |
| a lost subject counted in `seeds_dropped` (102) | yes | **yes** — same helper |
| shared-**qname** seed disclosed, not walked (161) | yes | **no** — never called `_split_ambiguous` |
| shared-**trailing-name** seed refused (169) | yes | **no** — `_split_twinned` is not shared |

`impact_modules.py:127-132` calls `resolve_seeds` and hands `seed_set.seeds` straight to
`store.impact_radius`. So a module rollup over a twinned file walks both twins and rolls their
modules together — the same 29× shape 169 measured, one aggregation layer up, where it is *harder*
to notice because the output is module names rather than symbols.

## Scope

1. Route `impact_modules`' seeds through the same two splits `impact` uses (`_split_ambiguous`,
   `_split_twinned`), from one definition site — not a copy (R6.7, R1.8).
2. The rollup payload discloses what was refused, in whatever shape the module surface makes honest;
   a module list that silently lost a seed is worse than one that names the loss.
3. Confirm whether the two tools should share one seed-resolution entry point outright, or whether
   the module surface legitimately wants different behaviour — and record the answer.

### Explicitly not in scope

- Changing the rollup shape or the module table.
- The edge model (161's AC1 deviation stands).

## Constraints

- **061** — a rollup over untwinned seeds is byte-identical.
- **R6.7 / R1.8** — one decision, one implementation; the splits are `impact`'s and must not be copied.
- **Cost** — 140's shared-helper budget; one bounded query per seed, never per rolled-up node.

## Acceptance criteria

1. `impact_modules` over a file whose symbols have same-named twins does not roll the twin's modules
   into the answer — pinned by a test that fails on today's code.
2. Whatever is refused is named in the payload; `seeds_dropped` accounts for it.
3. The splits have one definition site shared with `impact` (R6.7), pinned.
4. An untwinned rollup is byte-identical (061).
5. Determinism (R4.2), no language branch (R1.1), no contract bump (R3).

## References

Filed by 169's AC6. `code_atlas/tools/impact_modules.py:127-132`; `code_atlas/tools/impact.py`
(`_split_ambiguous`, `_split_twinned`, `resolve_seeds`). Related:
[169](169_impact-path-seed-walks-every-symbol-and-its-twins.md),
[161](161_impact-resolves-a-shared-qname-to-one-twin-and-carries-no-freshness.md),
[140](140_impact-modules.md).
