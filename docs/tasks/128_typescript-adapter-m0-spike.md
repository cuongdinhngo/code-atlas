---
id: 128
slug: typescript-adapter-m0-spike
title: TypeScript/JavaScript — M0 spike only, to answer §4.4 with evidence instead of anticipation (M7 precursor)
phase: 2
milestone: M7
status: todo
depends_on: [012, 147, 149]
---

## Why this exists, and why now

[019](019_typescript-adapter.md) is the full M7 adapter and stays **deferred**. This ticket is its
**M0 equivalent** — the [006](006_php-adapter-spike.md)-shaped spike, and nothing beyond it.

**The dependency ran backwards until 2026-08-24.** This ticket used to declare `depends_on: 019`,
which is the reverse of what it is: 019 cannot start until the spike answers §4.4. It now depends on
[147](147_contract-harness-is-php-shaped.md) (the conformance harness admits one adapter today, so
AC1 has nowhere to run) and [149](149_tsjs-construct-inventory.md) (AC1 names two files without
saying what either contains).

PLAN §19 ratified *depth before breadth* because the anchor monorepo makes PHP measurable. **That still
holds and this ticket does not reopen it.** What has changed is what depth is buying: the last several
onboarding tickets — [098](098_correspondence-relation-seam.md),
[120](120_subtree-dependency-attribution.md), and the auto-doc proposal — are all held or shaped by
**n = 1**, and n = 1 is a property of having exactly one adapter, not of having too few PHP features.
This spike is the cheapest test of whether the contract survives contact with a second language.

**This reasoning is a proposal, not a decision.** Whoever picks the ticket up reads §19 and §4.4 first;
if they disagree, they say so in the PR and stop. Silently reordering the roadmap is the failure mode
this paragraph exists to prevent.

## Scope

- `adapters/typescript/` (019's name, not the work order's `adapters/ts/` — CONVENTION owns the path)
  parses **one module-scoped file** and **one namespaced-equivalent module** into contract JSON that
  passes `tests/contract/`.
- Nothing else: no resolver work, no tool changes, no core changes, no registry, no `contract_version`
  bump in this ticket.

## The deliverable is the §4.4 report

The spike exists to answer three questions with evidence. The write-up is worth more than the code:

1. **Does `MEMBER_SEPARATOR` hold?** TS/JS has no namespaces, so qnames are module-path-anchored
   (`src/user.ts::User::save`). Does the convention hold, or does it bend — and if it bends, where?
2. **Which of §4.4's two options does the spike actually need** — an `open_project(root)` lifecycle
   holding the tsconfig program, or the two-pass mode? The v1 protocol is file-at-a-time and the
   TypeScript Compiler API resolves imports and types only against a whole program.
3. **Does a second adapter force a `contract_version` bump, and if so, what exactly changes?** One
   answer, with evidence, not a guess.

## Acceptance criteria

1. **AC1.** One module-scoped file and one namespaced-equivalent module pass `tests/contract/`
   unchanged.
2. **AC2 — R1.1 is the acceptance test.** If making this work requires **any** branch under
   `code_atlas/` that keys on language, the contract leaked: **stop**, and write up where it leaked
   instead of adding the branch. That write-up closes the ticket successfully.
3. **AC3.** The three §4.4 answers land in PLAN §4.4, each with the evidence that produced it.
4. **AC4.** Core diff is empty. `adapters/typescript/` is self-contained and launched via
   `CA_TYPESCRIPT_CMD`, mirroring the PHP adapter's `CA_PHP_CMD` shape.
5. **AC5.** Time-boxed. If project-context resolution turns out to be larger than a spike, **that
   finding is the deliverable** — record it in PLAN §4.4 and close the ticket.

## Not in scope

Path aliases, ESM/CommonJS resolution breadth, `allowJs`, `semantic_types`, CI's second runtime, and
the adapter registry. All of that is 019.
