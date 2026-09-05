---
id: 214
slug: a-bare-exec-links-to-nothing-and-the-zero-says-no-matches
title: 'A schema-unqualified `EXEC X` links to nothing, so `find_callers` answers `no_matches` on a proc with 42 call sites — 604 of 696 EXEC sites (86.8 %) on the anchor are written that way'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [184, 186, 204, 160]
---

## Why this exists (field retro round 13 §13, §16)

Round 13 is the first round that could ask a SQL question. It asked six and got **two harmful
answers**, both the same shape:

> `find_callers("dbo.Score_Calc")` → `total_count: 0`, `reason: "no_matches"` — against **42**
> grep-verified `EXEC` sites. `find_callers("dbo.Score_Calc_BETA")` → **0 vs 6**, all exact-case.

The retro isolated the cause in five further calls, ruling out the two obvious suspects: **not case**
(`Score_Calc_BETA` fails with six exact-case sites) and **not double definition**
(`usp_CleanOrphanedMemberReferences` has two definitions and resolves to **1 caller, RESOLVED**).

> **The discriminator is qualification: `EXEC dbo.X` links, `EXEC X` does not — and 604 of 696 EXEC
> sites (86.8 %) are bare.**

Corroborated independently by the per-language `edge_health` 183 shipped: SQL is **14.6 % linked**
against **13.2 % qualified**. The two numbers agree, from opposite directions.

**The chain is three hops and every hop is in this repo:**

1. `adapters/sql/src/scan.js:400` emits `target_raw: qname` verbatim — for `EXEC Score_Calc` that
   is `Score_Calc`, with `confidence_tier: "RESOLVED"`.
2. The core resolves a `CALLS` edge by `target_raw` against the declared qname, which is
   `dbo.Score_Calc`. No match.
3. The bare-name fallback cannot catch it either: `code_atlas/resolver.py:19` fixes
   `_BARE_NAME_KIND = "Method"`, and a T-SQL procedure is a `Function` node. **SQL's HEURISTIC count
   is 0** — there is no guessing tier for this language at all.

So the edge is dropped, and `find_callers` reports the drop as a **modelled zero**.

**Why this is the round's only harmful payload class.** `no_matches` means *"I model this relation and
the answer is none"*. Here the truth is *"this call form is not linked"*. A reader deletes a live
stored procedure on that answer. The retro's §17 names it as the one place the tool made a competent
reader worse: *"a wrong answer I would have shipped into a report had the mandated grep not caught
it."*

**The honest field already exists and works.** [186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md)
shipped `relation_unmodelled_for_language` (`code_atlas/tools/nav_result.py:67`), and round 13
confirmed it fires correctly, first try, on a third language — for a **view's importers**, where
nobody would be badly misled. It is pointed away from the defect. **This is not a missing capability;
it is a capability wired to the wrong case.**

## Scope

1. **A schema-unqualified `EXEC X` resolves to the declared object** when the resolution is
   unambiguous — the T-SQL rule that an unqualified routine name resolves against the default schema
   (**R2: the language spec, not this repo's names**). Where the object lives decides tier: an
   unambiguous default-schema match is not a guess of the same class as a bare method name.
2. **Where it lives is a design decision, and R1.1 constrains it.** Two candidate homes: the adapter
   normalising `target_raw` (a language rule, in the file that already encodes T-SQL syntax) or a
   generic core mechanism the adapter opts into. **A branch on `language == "sql"` under
   `code_atlas/` is not one of the options.** Design records the choice and why.
3. **Ambiguity refuses rather than guesses.** More than one candidate for a bare `EXEC X` must not
   silently pick one; the existing ambiguity surface (`ambiguous_definitions`) is the precedent.
4. **The residual zero says what it is.** Whatever Scope 1 cannot link — a target that is genuinely
   ambiguous, a dynamic `EXEC(@sql)`, a proc declared inside a string — answers
   `relation_unmodelled_for_language`, **not** `no_matches`. This half needs no schema bump and no
   rebuild.
5. **Measure it on the anchor.** Report the qualified/bare census and the linked share before and
   after. If Scope 1 moves SQL's linked share by little, that is the finding and it is reported;
   Scope 4 still ships, because the honest zero is worth more than the edges.

### Explicitly not in scope

- **Views as symbols.** 1,263 `CREATE VIEW` statements are File nodes only, and `dbo.WRB` — the fact
  that motivated adapter #3 — is still outside the graph. That is a separate gap in tier 1a's scope,
  not this ticket. See *References*.
- **A proc declared inside dynamic SQL** (`EXEC('CREATE TRIGGER …')`). A parse-tier gap; it lands in
  Scope 4's honest zero, not in Scope 1's resolution.
- **Widening the bare-name HEURISTIC fallback across languages.** [204](204_bare-name-resolution-has-no-language-predicate.md)
  deliberately restricted it, and deleted 342,758 false edges by doing so. This ticket does not
  reopen that.
- **Any PHP↔SQL crossing.** `cross_language.pairs` is `{}` by design.

## Constraints

- **R1.1** — zero language branches in the core. If the rule cannot be expressed without one, it
  belongs in the adapter.
- **R2** — the rule encodes T-SQL's default-schema resolution, never the anchor repo's habit of
  writing `dbo`. A repo whose objects live in another schema must not be silently mis-linked.
- **R4.2** — deterministic: identical input, identical rows.
- **R5.2** — a link weaker than what the edge claimed is never reported as stronger.
- **R5.6** — silence is not evidence. Scope 4 is this rule applied to the exact case that broke it.
- **R6.9** — assert at the consumer: the proving test reads `find_callers`' payload, not the resolver's
  internal state.

## Acceptance criteria

1. A fixture where `EXEC X` is called against a single declared `dbo.X` links, and `find_callers` on
   the declared qname returns that call site.
2. A fixture where two candidates exist does **not** silently link one; the ambiguity is visible in
   the payload.
3. Every `CALLS` edge Scope 1 cannot link answers `relation_unmodelled_for_language` with its hint —
   **never** `no_matches` — pinned by a test that fails before the change.
4. A repo whose routines are declared in a non-`dbo` schema is not mis-linked to `dbo`, pinned by a
   fixture.
5. No `if language ==` under `code_atlas/` (the existing CI grep gate stays green).
6. Scope 5's before/after census is recorded with its method, including a negative result.

## References

Field retro round 13 §13 (the isolation chain), §4 (the zero taxonomy), §16 (this ticket, named as
the one change to make), §17 (the harm), §15.a (the narrowed `.sql` carve-out — *"who calls a stored
procedure"* is the entry this ticket exists to remove).
[184](184_tsql-source-adapter-tier-1a.md) (tier 1a, which emits the edge),
[186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) (the reason string
this reuses), [204](204_bare-name-resolution-has-no-language-predicate.md) (why the bare-name fallback
is language-restricted), [160](160_a-zero-answer-never-names-the-index-language-coverage.md) (the
zero-answer disclosure this joins).
`adapters/sql/src/scan.js:389` (the `EXEC` scan), `:400` (the edge, with `target_raw` verbatim),
`code_atlas/resolver.py:19` (`_BARE_NAME_KIND = "Method"`), `:185` (`_link_by_bare_name`),
`code_atlas/tools/nav_result.py:67` (`REASON_RELATION_UNMODELLED_FOR_LANGUAGE`),
`code_atlas/tools/find_callers.py:111` (the `bare_name_truncated` precedent for a non-`no_matches`
zero).
