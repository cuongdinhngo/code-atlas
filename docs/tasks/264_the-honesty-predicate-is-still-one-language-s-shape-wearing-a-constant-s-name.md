---
id: 264
slug: the-honesty-predicate-is-still-one-language-s-shape-wearing-a-constant-s-name
title: 'After 255, one subject kind counts its inbound relations correctly and the rule that made it wrong is unchanged: each tool still decides for itself what a genuine zero is, so the next Table-shaped kind, the next `WRITES` cousin, the next C# construct re-pays the same bug — make the predicate derive from the contract and let a tool that bypasses it fail a test'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [255, 232, 065]
---

## Why this exists

[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md) shipped: a T-SQL `Table` with 34 inbound `WRITES` no longer answers `no_matches`. What it fixed was one predicate, in one tool, against one subject kind. **The class survives.** `UNMODELLED_REFERENCE_KINDS` was a tuple of the two kinds a PHP class happens to have, consulted as though it were the set of all inbound relations — 255's own words: *a language branch wearing a constant's name*, in a core where R1.1 forbids language branches.

The next adapter that introduces a kind this predicate cannot see re-creates the defect silently. C#/.NET ([021](021_csharp-adapter.md)) is the obvious candidate and it has not been written yet — which makes this the cheapest moment to make the repeat impossible.

An empty inbound answer is genuine **only** after the tool has counted every inbound kind the contract holds for that subject's kind. If any exist and are unlinked, the reason is *unmeasured*, never `no_matches`.

## Scope / Deliverables

- **A `subject kind → inbound kinds` mapping in `contract.py`**, derived from the vocabulary the contract already owns — not a second hand-kept table (R6.7).
- **One shared empty-answer predicate** that every nav tool calls. No tool decides `no_matches` on its own.
- **A conformance test that fails a bypass**: a nav tool reaching the `no_matches` reason without consulting the shared predicate is a red test, not a quiet disagreement. Property-shaped over `(subject kind × inbound kind)` so a new kind is covered the day it enters the contract.
- **Design constraint, binding: derive, do not extend.** The mapping must be a derived view of existing vocabulary so **`contract_version` does not bump**. A bump forces consumers into a 9–20-minute full rebuild and the observed consequence is that they stay on the old server — which costs more honesty than this ticket buys.

## Constraints

- If the design cannot avoid a vocabulary change, **stop**: the atomic-swap upgrade path ships first, in its own ticket, and this one waits. A single PR that changes both the honesty layer and the upgrade path is not reviewable.
- R1.1: no language branch, and no constant that is one language's shape in disguise — the test must be able to catch the disguised form, which is what 255 could not.
- Whether a tool *returns* the newly-counted kinds stays out of scope; this ticket binds only that a bare `no_matches` over existing unlinked inbound edges becomes impossible.

## Acceptance criteria

- A matrix test over every `(subject kind × inbound kind)` the contract holds; adding a kind without extending the mapping fails it.
- Every nav tool's `no_matches` path routes through the one predicate; a test asserts there is no second implementation.
- `contract_version` unchanged, pinned by a test.
- The 255 fixture and the PHP-class fixture both still pass unchanged.

## References
[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md), [232](232_the-same-construct-is-a-references-edge-in-python-and-node-extra-in-php-and-ts.md), [065](065_empty-answer-cannot-explain-itself.md), `code_atlas/contract.py:106`, `docs/ENGINEERING_RULES.md` R1.1 / R3 / R6.7.
