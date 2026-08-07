---
id: 059
slug: view-databag-edge
title: 'The handler → template data-bag edge is unmodelled — the primary defect in two consecutive field sessions'
phase: 1.5b
milestone: Coverage
status: todo
depends_on: [030, 040]
---

## Goal
Two external field sessions, two real defects, **one missing edge kind**.

- **Round 1.** A handler publishes a list into a view scope under a **string key**; the template reads a
  differently-named bare variable. Five controller/template pairs, all rendering empty tables. That
  session made **zero graph queries** for the whole defect, because no tool models the link.
- **Round 2.** The mirror image: a handler reads request keys the template never emits — and, in the
  instance the ticket had missed, a key the template emits in one of two rendering branches only.

Neither end is a symbol. The producer side is a string literal in an array passed to a setter; the
consumer side is a bare variable in mixed markup. The relationship between them is a **string key**, and
the index has no vocabulary for it. Everything code-atlas does — name resolution, callers, references,
implementations, impact — is blind to the single most common defect shape in this codebase.

The round-1 retro guessed, marked `UNVERIFIED`, that this generalises to any MVC-ish codebase with a
data-bag view layer. Round 2 is the second data point. It is now the strongest single signal either
retro produced, and it is the one thing on the list that a language server does not solve either — this
is not a race against Serena, it is unclaimed ground.

## The decision this ticket exists to force
**Do framework-shaped edges belong in the graph at all?**

R2 is unambiguous: adapters encode the language spec, never a framework, and CI grep-gates it. So the
producer side — "this framework's view setter takes a key here" — cannot live in the PHP adapter. But
[040](040_framework-indirection-data.md) already built the legal channel: framework indirection as
**data in a rules file outside `adapters/`**, applied by `enrichment.py`. That is the precedent, and it
is the shape this should take if the answer is yes.

The consumer side is the harder half. Reading bare variables out of mixed markup is a parsing job no
current adapter does, and template files are ignored today
([041](041_legacy-framework-hardening.md) ignores `.blade.php`). Options, to be decided here rather than
assumed:

1. **Producer side only.** Record what a handler publishes and under which keys, from rules. Cheap, and
   already answers "what does this handler put in scope" — half of round 1's question.
2. **Both sides**, with a template reader. Answers the whole question and costs a new parsing surface.
3. **Neither** — declare it permanently out of scope and say so in PLAN §1's non-goals, so the next
   field retro stops reporting it as a gap.

Option 3 is a legitimate outcome. Recording *why* is the deliverable either way.

## Scope / Deliverables
- **A design note, before any code**, choosing among the three and stating the reasoning. This is the
  deliverable; implementation is a follow-up ticket.
- **If 1 or 2:** the contract impact (a new edge kind is a `contract_version` bump and conformance
  tests, R3), the rules-file shape, and what the nav answer looks like.
- **If 3:** the PLAN §1 non-goal wording, and a note in the onboarding runbook telling an operator this
  shape is grep's job.
- **Measure the ground first.** Before choosing, count how often the shape occurs in the anchor repo —
  how many handler/template pairs, how many keys. Two anecdotes are two anecdotes; a count is what
  should decide whether this is worth a contract bump.

## Constraints
- **R2 holds absolutely.** No framework knowledge in any adapter, no repo names anywhere. The rules-file
  layer is the only legal channel and CI enforces it.
- **Contract changes are versioned (R3)** — a new edge kind bumps `contract_version` and updates the
  conformance suite. That cost is part of the decision, not a detail after it.
- **Determinism (R4)** — rules are data; no inference, no LLM.
- **Do not widen the adapter's file set casually.** Template files are ignored today for reasons
  (041); reversing that has a build-cost and parse-failure impact that must be measured.
- **Nothing about a private repo enters this repository** — the shape may be described, its identifiers
  may not.

## Acceptance criteria
- A written decision among the three options, with the anchor-repo occurrence count that informed it.
- If implementation is chosen: a follow-up ticket with the contract impact spelled out.
- If declined: PLAN §1 non-goals and the runbook updated so this stops being reported as a gap.
- The design note names what a language server does *not* solve here, so the scope decision is made
  against the real alternative rather than against grep.

## References
[040](040_framework-indirection-data.md) — framework indirection as data outside `adapters/`, the legal
precedent and the mechanism; `code_atlas/enrichment.py` (how rules become rows);
[041](041_legacy-framework-hardening.md) (template files ignored today); `contract.py` (`EDGE_KINDS`,
what a new kind costs); R2 and its CI grep-gate; PLAN §1 (non-goals).
Prior record: [`BACKLOG.md`](../BACKLOG.md) open observations, where this has sat unticketed since round 1.
Origin: field retro round 1 §6a.1 and round 2 §A.6 — the same missing edge, both directions.
