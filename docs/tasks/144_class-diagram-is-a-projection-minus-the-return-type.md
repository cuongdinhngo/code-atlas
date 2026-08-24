---
id: 144
slug: class-diagram-is-a-projection-minus-the-return-type
title: A class diagram is a projection of rows the graph already holds — except the return type, which the adapter never emits
phase: 3
milestone: Presentation
status: done
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

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->
<!-- mango:working-doc -->

## Session status

- **Phase:** finalise (execute complete; review/challenger waived)
- **Branch:** `feat/144-class-diagram-is-a-projection-minus-the-return-type`
- **CHALLENGER:** OFF
- **work_doc_mode:** embed
- **TIER:** full · **SCOPE:** M

## PREMISE / REFINE

`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`refine skipped: 0 unresolved product-decisions` — standing approval to choose approach and pass gates.

## Design

- **Bump `CONTRACT_VERSION` 6 → 7.** Method/Function return type in `extra['type']` (same key as
  properties). An index built before and updated after would mix eras; `incremental_update`
  full-rebuilds on stored vs current `contract_version`. No `SCHEMA_VERSION` bump — `extra` is
  already TEXT.
- New MCP tool `class_diagram` (21st): `qname` (type + ancestry) **or** `path` (TYPE_KINDS in file).
- Inheritance from `EXTENDS` / `IMPLEMENTS` / `USES_TRAIT` only. Associations from declared property
  / param / return types that resolve to FQNs already in the diagram. No CALLS/NEW.
- `limit` = per-class member cap (`clamp_limit` + `attach_limit_capped`); not a mermaid page →
  `NOT_PAGED_EMITTERS`.
- Path-segment `<<test>>` label (130); `nodes.is_test` unused by adapters.

## Requirements matrix

| ID | Ph3 | Ph4 | Notes |
|---|---|---|---|
| AC1 | ✅ | waived | golden mermaid body |
| AC2 | ✅ | waived | CALLS planted; no `-->` |
| AC3 | ✅ | waived | `%%` inheritance-only note |
| AC4 | ✅ | waived | return types + CONTRACT_VERSION == 7 |
| AC5 | ✅ | waived | `%% members capped` |
| AC6 | ✅ | waived | emitter source scan |

## Cost ledger

| phase | dispatch | tokens |
|---|---|---|
| execute | main loop | unmeasured (host does not surface usage; review/challenger waived) |

## Review of PR #169 — three defects fixed in-branch

The AC tests build `Association` rows by hand (AC1) or assert none appear (AC2), so the tool's own
declared-type path — `_members` → `_project` → arrows — shipped unexercised end to end. What that hid:

1. **The member cap made AC3's note lie.** Associations were read off the *capped* member prefix, so
   at `limit=1` a class with a declared `\App\Dep` property rendered `%% no declared-type
   associations — inheritance only` and set `association_note`. That is a positive claim about the
   code which the cap invented (130's family), and the arrow vanished with no count (108/124).
   Associations are now computed over every member; the ones whose member the cap dropped are
   counted, disclosed as `%% N declared-type association(s) hidden…` plus
   `associations_hidden_by_cap`, and they suppress the "no associations" note. They are counted, not
   drawn — an arrow off a member the box does not list is unreadable.
2. **A qname declared twice produced two boxes sharing one mermaid id.** Ids are positional and keyed
   by qname, so `class N1[…]` was emitted twice and `total_count` said 2 types where there is 1.
   Roots are now distinct and the duplication is disclosed through the existing
   `attach_ambiguous_definitions` (070/078) rather than merged away silently.
3. **`validate_mermaid_class_diagram` never ran on the diagram the tool returns** — only tests called
   it, the same gap 143 had. `render_class_diagram` now validates its own output. That exposed
   `_label` stripping only `"`: a name is adapter data, not vocabulary, so a newline in one broke the
   line structure. `_label` drops CR/LF, member lines run through it, and an association label also
   drops `:` (a second colon makes the relation line unparseable).

Also: identical inheritance rows are de-duplicated like associations already were, and the two bare
reason strings now use the pinned `REASON_OK` / `REASON_NO_MATCHES`.

Tests added: `test_the_cap_never_turns_a_declared_type_into_no_associations`,
`test_a_qname_declared_twice_is_one_box_and_says_so`,
`test_a_newline_in_a_member_name_cannot_break_the_diagram` — each verified red with only its own fix
reverted.

**Not fixed, noted:** `_members` loads every contained member before slicing, so `limit` bounds the
rendered box but not the query. That is what lets the hidden count be honest; a class with thousands
of members would pay for it.
