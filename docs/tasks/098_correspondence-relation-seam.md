---
id: 098
slug: correspondence-relation-seam
title: 'Is "this file is a copy/port of that file" a relation code-atlas should hold? — evidence-gated'
phase: 1.5b
milestone: Coverage
status: deferred
depends_on: [030, 011, 003]
---

> **Status: deferred, and deliberately so.** This ticket holds a hypothesis and its gate, not a plan.
> The demand is real and comes from the project's **first production user** — but it is **n = 1**, from
> a repository whose shape (one application maintained as two regional copies, mid-migration into a
> unified tree) is not the shape of most repositories, and code-atlas is a **general MCP server** whose
> every user would carry the cost. **The gate is in "Evidence gate" below.**

## Goal — the hypothesis
Some repositories contain **two files that are versions of each other**: a legacy source and the
module that replaced it, a vendored fork and its upstream, `v1/` and `v2/` of an API, a variant
maintained per region or per tenant. Where that is true, questions about *the pair* dominate the work
— has this been ported, and to what? did these two drift? — and code-atlas holds no relation that can
answer them, in any language.

The index already **notices** the pattern and refuses on it: two definitions of one qname in two trees
returns `subject_ambiguous` ([078](078_ambiguous-payload-still-picks-one-definition.md) — correct, and
a real improvement). The hypothesis is that one step further on is a useful primitive: *for this file
or symbol, what is its counterpart, and how do they differ?*

**Where this came from, and how much it weighs.** The anchor repo's dominant chore is exactly this,
and the round-5 field session spent its analysis phase doing by hand what the relation would answer —
reading 1,913 lines of two legacy sources and counting grid columns by eye to decide whether one port
or two. **This is a real user with a real need, not a lab exercise** — it is the project's first
production adopter and every finding this project has ever acted on came from it. What it is not is
*every* user: one customer's dominant chore is demand, not yet a requirement for a server that other
repositories will install. The relation is deferred because it costs everyone, not because the need
is doubted.

## The decision already taken, so it is not re-litigated
The field session proposed seeding the relation from a hand-maintained mapping file (~4,300 entries)
that its repo already keeps and CI-enforces.

**Rejected as proposed, and this part is settled.** Ingesting a specific repo's mapping format is
sample-over-standard (**R2**) — the exact thing CI gates, and the failure mode a public server cannot
afford. If this relation is ever built, what the core may learn is **one generic relation** — *this
file/symbol corresponds to that one*, carrying a **source** and a **confidence**, supplied by
declared configuration and never by adapter knowledge. Under that primitive, legacy↔replacement,
fork↔upstream and variant↔variant are the **same** relation with different sources, in any language.

## Evidence gate — what must be true before this leaves `deferred`
All three, and none of them is satisfied today:

1. **A second, independent repository** — not the anchor, ideally not PHP — where the same question
   recurs and is answered by hand. One user's dominant chore is demand, not yet a product requirement
   (**R1.2**: no abstraction until the second instance exists). Note what this gate does *not* say: it
   does not say the anchor's need is invalid, only that it cannot by itself decide a schema every user
   inherits.
2. **A statement of what it costs everyone else.** A relation carried in the schema is paid for by
   every user of the server, including the majority whose repositories contain no such pairs. Name the
   cost — storage, build time, payload weight, one more concept in the surface — and show it is near
   zero when the config declares nothing.
3. **A cheaper alternative rejected in writing.** Specifically: a repo that maintains such a mapping
   can already answer these questions with its own tooling. The question is not *is this useful* but
   *is this useful enough to belong in a general code index rather than beside one*.

**If the gate is met, the design must answer, in this order:**
1. **Is a correspondence an edge, or its own table?** It is not a call, an include, or an
   inheritance; it relates *files* as often as symbols, and it can be many-to-many.
2. **What are the admissible sources, and how does the core stay ignorant of their format?** A
   declared config source (path pairs the repo supplies) is the baseline. Weigh, and either adopt or
   reject with reasons: a **basename/path-shape** source computed from rows the core already holds
   — *N files share a basename across different roots* — which needs no adapter and no language
   knowledge at all, and which the same session shows is the shape behind its highest-value defect of
   the day (a shared front-end asset that was one region's lineage).
3. **What does a stale correspondence look like?** The strongest argument for holding this at all:
   *a mapping that nothing verifies is a mapping that is quietly wrong.* If the graph holds both
   sides, it can report that an entry points at a file that no longer defines what it claims.
4. **What does it refuse to answer?** Correspondence is asserted, not inferred. The tier and the
   source must ride on every hit so nobody mistakes a config assertion for a resolved edge.

## Evidence — all of it from one repository (field interview, 2026-08-14, §8.2, flagged by its author as opinion)
- §1 Moment 2: a split decision made by reading 1,196 + 717 lines end to end and counting columns by
  eye. The relation would have answered *"tree A defines 7 top-level functions, tree B defines 6, 4
  names differ"* in one call.
- §8.2 (2): that project keeps a dedicated pattern file for one defect class — *"the two copies
  diverged and someone assumed they hadn't."*
- §8.2 (3): two confirmed instances in three days of a shared asset belonging to one copy's lineage,
  silently disabling the other's UI with **nothing in any server log**.
- §6.5 / §8.2 (1): the session's one genuine win — *"has this been ported, and under what name?"* —
  was answered by name **similarity**, and the interview downgraded it precisely because similarity
  is not correspondence.

**How much this weighs.** One session, one repository, one session type, and an author who marked the
section as opinion and as a violation of the instrument's own "do not design" rule. It is enough to
open a hypothesis and write the gate. It is **not** enough to spend schema, build time and a concept
in the tool surface that every other user would carry.

## Scope / Deliverables — only if the gate opens
- **Design first, and expect the design to be most of the ticket.** Answer the four questions above
  with a written verdict each; a rejected alternative is a deliverable here, not a footnote.
- **A storage shape** for correspondences with `source` and `confidence`, and a migration verdict
  (schema bump ⇒ [050](050_schema-version-mismatch-recovery.md)'s recovery path must handle it).
- **One config-fed source**, format-declared by the core, populated by the repo. No repo's file
  format is hardcoded.
- **A query surface** — decide between extending an existing tool and adding one, against
  [061](061_payload-weight.md) and the interview's own §5 warning that the surface is already wider
  than one session can hold.
- **A staleness check**: given a declared correspondence, report when one side no longer holds what
  the other claims.
- **Explicitly out of scope:** inferring correspondences by similarity heuristics. That is an LLM-shaped
  judgement and would break **R4**; if the design wants it, it belongs in Phase 3 behind the
  Summarizer seam, not here.

## Constraints
- **R2 (CI-gated)** — no repo's names, paths, or mapping-file format in `code_atlas/` or any adapter.
  The anchor's mapping is a *test fixture at most*, never a dependency.
- **R1.1** — zero language branches; correspondence is language-agnostic by construction.
- **R4** — deterministic: asserted pairs in, identical rows out. No ranking, no fuzzy matching.
- **R1.2 / YAGNI** — one seam, one source to start. Do not build a plugin system for sources.
- **Zero cost when undeclared.** The majority of repositories have no such pairs. A user who declares
  nothing must pay nothing: no table growth, no build-time work, no extra field in any payload, no
  extra tool in the surface. If that cannot be achieved, the answer to this ticket is **no**.
- Scale: the anchor holds 18,926 indexed files; a many-to-many table over that must not slow status
  or nav answers. Measure.

## Acceptance criteria
- A written design verdict on each of the four questions, with rejected alternatives.
- A fixture repo with declared correspondences produces queryable pairs carrying `source` and
  `confidence`, pinned by tests.
- The staleness check reports a deliberately rotted correspondence in a fixture.
- A grep-gate (or an extension of the existing R2 gate) proves no repo-specific mapping format leaked
  into the core.
- Payload weight and query latency measured before/after on a large synthetic index.

## References
Field interview (round-5 companion, 2026-08-14) §1 Moment 2, §6.5, §8.1 ("fit to this repo's dominant
work type — 35 %"), §8.2 (1)(2)(3), §8.4 item 1, §8.5. Related:
[078](078_ambiguous-payload-still-picks-one-definition.md) (the refusal this builds past),
[030](030_alias-indirection-edges.md) (precedent for a non-call relation),
[003](003_config-and-ignore.md) (where a declared source would live),
[050](050_schema-version-mismatch-recovery.md) (schema migration),
[094](094_class-constant-in-array-literal-is-not-an-edge.md) (the other unheld relation from round 5).
