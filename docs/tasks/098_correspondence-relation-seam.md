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

## Evidence from task 115 (structural mirror detection, landed 2026-08-20)

[115](115_mirror-subtree-detection.md) was written to be this ticket's evidence: produce the
correspondence set **structurally**, with no new edge kind and no `contract_version` bump, and measure
how large and how useful it is. It landed. Here is what it found, and the verdict is **keep 098
deferred** — the evidence weakens the case for a schema relation rather than strengthening it.

### What was measured
`find_mirror_subtrees` discovers sibling directories whose *relative path sets* overlap, gated on both
the shared count (≥ 25) and the Jaccard fraction (≥ 0.30). Run over every independent repository
available:

| repo | accepted pairs | best sibling pair, ungated | overlap | shared |
|---|--:|---|--:|--:|
| anchor monorepo | 1 | the two application subtrees | **0.615** | **4,244** |
| `laravel/laravel` @ `ff031db` | **0** | `tests/Feature` ↔ `tests/Unit` | 1.000 | **1** |
| `symfony/demo` @ `03fe256` | **0** | none shares any relative path | — | 0 |
| `brick/math` @ `b61d8e6` | **0** | none shares any relative path | — | 0 |

### Gate item 1 — a second, independent repository: **STILL NOT MET**
This is the finding that matters. A structural detector, run over three independent public
repositories, found the shape in **none** of them. `laravel/laravel`'s only candidate is a pair of
mirrored *test* directories sharing exactly one file — mirrored scaffolding, not a mirrored
application. So `n` is still **1**, and it is still the anchor. The demand has not generalised, and
this gate item is no closer to being satisfied than when 098 was deferred.

### Gate item 2 — what it costs everyone else: **ANSWERED — "nearly nothing, precisely because it is
not in the schema"**
115's cost on a repository without the shape is one bounded pass over a path list already in memory,
producing an empty list. No table, no edge kind, no column, no build-time cost, no payload weight, and
nothing for a user to configure. That is the cost profile gate item 2 asks a schema relation to
demonstrate — and 115 achieves it precisely *by not being in the schema*.

### Gate item 3 — a cheaper alternative rejected in writing: **THE ALTERNATIVE WAS NOT REJECTED — IT WORKS**
Gate item 3 asked for a cheaper alternative to be rejected in writing. The opposite happened. The
cheaper alternative — path-shape correspondence computed at presentation time from rows the core
already holds — was **built and it delivers the thing the user actually asked for**: paste a path, get
the parallel path, or be told there is no counterpart. The lookup, including the negative answer that
marks divergence, needs no relation in the graph.

### What 115 could not do, stated honestly
- **It compares paths, never contents.** A shared path means both subtrees hold a file of that name,
  not that the two files are copies. 098's design question 3 (*what does a stale correspondence look
  like?*) is therefore still unanswered by 115 — and it remains the strongest argument for holding a
  real relation, because a path-based map cannot notice drift.
- **It only finds *sibling* subtrees.** A legacy file and the module that replaced it in an unrelated
  part of the tree, or a vendored fork and its upstream, are invisible to it. 115 covers the
  region-copy shape and nothing else.
- **It cannot represent a many-to-many or hand-asserted mapping**, which 098's design question 1 treats
  as a requirement.

### Verdict
**098 stays `deferred`, and 115 is the reason it can afford to.** Gate item 1 is unmet and further from
being met than before, because the shape now has measured absence on three independent repositories
rather than merely no evidence. Gate items 2 and 3 are answered *against* a schema relation: the
presentation-layer answer is nearly free and sufficient for the region-copy case. What would reopen
this is narrower than the original hypothesis: a second repository with the shape, **plus** a demand
that path comparison provably cannot serve — drift detection between two files, or an asserted
many-to-many mapping. Until then, correspondence lives beside the index, not in it.

## Evidence from field retro round 17 (2026-09-11) — the drift half of the reopen condition, answered against a relation

Round 17 produced exactly the demand the Verdict above named as the reopen condition's second half:
its highest-value ticket's root cause was a **parameter-list difference between an object and its
`_beta` twin**, and its top-ranked ask was a `diff_twin` primitive — *"highest value by a distance"*.
115's path comparison provably cannot serve that, which is why the Verdict listed it.

It is servable without a relation, and this was measured rather than argued. On the anchor monorepo
at `contract_version: 10`, reading `nodes.params` and grouping by name:

| Measure | Value |
|---|--:|
| `X` / `X_beta` stored-procedure twin pairs | 148 |
| …whose parameter lists differ | **28** |
| …including the session's own root cause | `UpdateRecursiveActivitiesUntil`, `@maxRecursions` absent from the `_beta` twin |

No table, no edge kind, no `contract_version` bump, no declared source, no config — one column the
graph already holds, plus a name convention applied at presentation time, which is where R2 requires
a repository's naming to stay.

**What this changes about the gate.** Gate item 1 is untouched and still unmet: round 17 is the
anchor again, so `n` remains 1. What moves is the Verdict's *own* strongest remaining argument — that
a path-based map cannot notice drift, and only a real relation could. At **signature** granularity it
can, because the graph holds both sides at that granularity already. The reopen condition narrows
accordingly: the live cases are now an **asserted many-to-many mapping**, and drift *below* the
signature — two bodies that diverged while their parameter lists agree, which neither 115 nor
`params` can see.

The consequence is a ticket, and it is not this one:
[242](242_params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function.md)
— the same measurement showed `params` is reachable by no nav tool, so the answer above is in the
index and out of an agent's reach. **098 stays `deferred`; 242 is what the demand actually wanted.**

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
