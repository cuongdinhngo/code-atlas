---
id: 012
slug: contract-conformance-tests
title: Contract-conformance & PHP coverage tests (M2)
phase: 1
milestone: M2
status: todo
depends_on: [007, 002]
---

## Goal
The LSP-substitutability guarantee: every adapter passes the same schema tests (§16).

## Scope / Deliverables
- `tests/contract/`: schema-conformance harness every adapter must pass (asserts emitted JSON + known node/edge counts).
- `tests/fixtures/php/`: namespaced, global, underscore(PSR-0), trait+conflict-resolution, enum, attributes, closures/arrow-fns, first-class-callable, include, static-vs-instance-call, syntax-error.
- CI **grep-gate**: assert zero language branches in `code_atlas/`; ban repo/framework names in adapter source.
- **CI:** the `guardrails` job never installs dependencies, so the `--exclude-dir=vendor` added in task 006 has **never been exercised there** — that gate currently passes over a tree with no `vendor/` in it. Move R2.2 into a pytest assertion in the `test` job, where `composer install` has run and the exclusion can actually be wrong. Keep the shell gate as a second layer; negative-control both (R6.4, R6.5).

## Acceptance criteria
- PHP adapter passes the conformance harness on all fixtures.
- Grep-gate fails the build on a planted `if language ==` or framework name.

## References
Plan §16, §2.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 012 — Contract-conformance & PHP coverage tests (working doc)

- **Ticket:** 012 · [docs/tasks/012_contract-conformance-tests.md](012_contract-conformance-tests.md) (raw above separator)
- **Type:** enhancement
- **Repo(s) / Porting:** `app` (`.`) only
- **SCOPE:** M (not confirmed — run stopped before analysis)
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** unset (stopped at Phase 0)
- **BASELINE:** not run (lifecycle stopped before analysis)
- **work_doc_mode:** `embed` → this doc lives below the separator in the ticket file itself (harness `work_doc_mode: embed`)

---

## Phase 0 — Refine (the FIRST phase; skip when the ticket is already clear)

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`

`REFINE: 1 unresolved surfaced | 1 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

**INPUT KIND:** ticket (single deliverable — not an epic).

**Settled wants (want-decision — from the user; become acceptance-criteria constraints analysis must honour).**

| # | The want (in want-language) | Chosen direction (NOT a tool) | Becomes AC constraint |
|---|-----------------------------|-------------------------------|-----------------------|
| 1 | 025 (grammar coverage) is still open — should 012 start now? | **Stop 012 — run 025 first** (user approved Recommended) | Do **not** execute 012 until 025 is `done`. Honour BACKLOG dependency. Resume `/solve 012` only after 025 lands. |

**Resolved direction + citation (how-decision — refine-resolved + CITED):**

| # | HOW-decision | Resolution | Citation (`file:line` / convention / rulebook § / ticket line) |
|---|--------------|------------|----------------------------------------------------------------|
| 1 | Dependency authority (frontmatter vs BACKLOG) | 012 waits on **025** (+ 002); ticket frontmatter `[007, 002]` is stale — sync when 012 resumes | `docs/BACKLOG.md:24`; `docs/tasks/025_php-adapter-grammar.md:15-16`; R7.2 |
| 2 | Fixture ownership vs 025 | 025 owns construct-level correctness fixtures+assertions; 012 owns the cross-adapter conformance matrix (R3.4) | `docs/tasks/025_php-adapter-grammar.md:61-62` |
| 3 | R2.2 placement + negative-control | Move R2.2 into a pytest assertion in the `test` job (where `composer install` ran); keep shell `guardrails` gate as second layer; negative-control both | ticket Scope lines 17–18; R6.4, R6.5 |

**ASSUMED (awaiting ratification):** none (user explicitly approved option 1).

**Constraints surfaced from the scan:**

- Adapter still lacks trait/closure/FCC/etc. emitters that 012’s fixture list needs (`adapters/php/src` has no `USES_TRAIT` / `Closure` / … matches) — confirms 025 must land first.
- Partial `tests/contract/test_contract_schema.py` already covers core-side schema/vocabulary; 012 adds the live-adapter harness + fixture counts.
- Partial `tests/fixtures/php/` exists (`namespaced`, `global_underscore`, `syntax_error`, `resolve/`); R6.2 list is not complete yet.
- `guardrails` job never runs `composer install`; R2.2 `--exclude-dir=vendor` is currently vacuous there (ticket Scope).

**Exposure-checker:** not dispatched — lifecycle **stopped** on settled want (W1) before Step 6; resume with a fresh refine/exposure-checker when 012 restarts after 025.

---

## Session status

- **Phase:** 0 refine — **STOPPED** (dependency gate)
- **Next:** run `/solve 025` (or equivalent); when 025 is `done`, resume `/solve 012` from a fresh/continued refine
- **Gate:** none open (human chose stop; no Gate 1)
- **Blocked by:** task 025 (`todo`)
