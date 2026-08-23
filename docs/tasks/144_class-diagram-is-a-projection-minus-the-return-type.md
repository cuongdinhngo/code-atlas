---
id: 144
slug: class-diagram-is-a-projection-minus-the-return-type
title: A class diagram is a projection of rows the graph already holds — except the return type, which the adapter never emits
phase: 3
milestone: Presentation
status: todo
depends_on: [002, 112, 116]
---

## Why this exists

Almost every field a class diagram needs is already stored, at the **resolved** tier — this is a
projection, not an inference:

- `NodeKind` covers `Class · Interface · Trait · Enum · Method · Property · ClassConst`.
- `EXTENDS · IMPLEMENTS · USES_TRAIT` are all in `contract.FQN_EDGE_KINDS`, so they are name-resolved
  rather than guessed.
- `modifiers` carries visibility, `static`, `readonly`, `abstract` (`adapters/php/src/Visitor.php`
  `propertyModifiers`/`methodModifiers`).
- `params` carries **`name` and `type`** (`Visitor.php:334`), and a property's declared type is emitted
  as `extra['type']` (`Visitor.php:344`).

**The one hole:** method and function declarations emit `modifiers` + `params` and **no return type**
(`Visitor.php:123-127`). A rendered signature is therefore half-typed — arguments carry their types and
the result does not.

Filling it is the same move the property node already makes: an `extra` key, precedent in the same
file. What must **not** be assumed is the contract question — 129's precedent: the trigger is whether an
index built before and updated after would mix eras. For return types it would, so the
`contract_version` decision is recorded in this ticket, not skipped because `extra` is free-form.

Provenance: the architecture review of 2026-08-23.

## Scope

1. Return type on `Method`/`Function` nodes via `extra`, with the `contract_version` decision written
   down and a conformance test either way (R3.1).
2. A deterministic mermaid `classDiagram` emitter, **scoped to a subject** — one class plus its
   ancestry, or one module — never the whole repo.
3. Inheritance edges come from `FQN_EDGE_KINDS` only. **Associations come from declared types only**
   (property `extra['type']`, param `type`).
4. Visibility from `modifiers`; `is_test` nodes filtered or labelled, not silently mixed in (130's
   family).
5. Member cap disclosed when it bites (108/124).

## Acceptance criteria

- **AC1** Red first (R6.5): a fixture class renders a known diagram body, byte-identical (R4.2).
- **AC2** No association arrow originates from an **inferred** receiver — asserted, because that is
  [137](137_php-local-type-table.md)'s territory and its tier is not this diagram's to claim.
- **AC3** A class with no declared types renders inheritance only **and says so** — an empty association
  set is not silence.
- **AC4** Return types appear in the rendered signature, and the `contract_version` decision is
  reflected in the conformance suite.
- **AC5** A capped member list says it was capped.
- **AC6** No repo/framework/language name in the emitter (R2.2, CI-gated).

## Out of scope

- **Inferred associations** — 137 owns the receiver problem; until it lands, an inferred arrow would be
  a guess drawn as a fact.
- **A whole-repo class diagram.** Unbounded by construction; AC2 of 116 exists because the last
  unbounded rendering was 31 MB.
- **Sequence diagrams** — see 143's Out of scope for the two blockers.
