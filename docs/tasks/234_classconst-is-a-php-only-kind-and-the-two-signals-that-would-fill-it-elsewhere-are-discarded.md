---
id: 234
slug: classconst-is-a-php-only-kind-and-the-two-signals-that-would-fill-it-elsewhere-are-discarded
title: '`ClassConst` is a PHP-only kind — TS spends it on `EnumMember` and drops `static readonly`, Python never emits it and ignores `Final`, and Python''s module-level `Const` comes from `name.isupper()`, a convention it declines to apply one scope down'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [229, 231, 020, 019]
---

## Why this exists

`ClassConst` is in the contract vocabulary and in `CLASS_MEMBER_KINDS` (`contract.py:96`), which
`class_diagram.py:34` reads as the set of members a class box lists. **One adapter of four emits it.**
Measured 2026-09-06 over `tests/fixtures/parity/`, and reproduced by
`scripts/adapter_parity_report.py`:

| declaration | emitted node | evidence |
|---|---|---|
| php `const TIMEOUT = 30;` | **`ClassConst`** | the parity table's only non-zero cell |
| ts `static readonly TIMEOUT = 30;` | `Property` | `ClassConst` is reachable only from `EnumMember` (`parse.js:44-45`) |
| python `TIMEOUT: Final[int] = 30` | `Property` | the string `Final` does not occur anywhere in the Python adapter |
| python module-level `MODULE_LEVEL = 1` | `Const` | `_is_upper_const` — `name.isupper() and any(c.isalpha() …)` (`parse.py:108-109`), reached only when `container in (qpath, mod)` (`parse.py:657`) |

**Two separate defects, one node kind.**

1. **The signals exist in the source and are thrown away.** `static readonly` is TS syntax and
   `Final` is PEP 591 — both are the language *spec* saying "constant", which is exactly what R2
   says an adapter encodes. Neither reaches the graph. TS's case is worse than a misclassification:
   the adapter emits **no `modifiers` at all** (the word does not appear in it), so `static` and
   `readonly` are not recoverable from the node either — see
   [231](231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md).
2. **Python's constant test is a naming convention, applied at one scope only.** `_is_upper_const`
   asks whether the identifier is upper-case. Whether that is legitimate is a real R2 question —
   PEP 8 is an ecosystem standard, and R2 admits "the language spec **and its ecosystem
   standards**" — but the answer cannot be *both*: today `MODULE_LEVEL = 1` at module scope is a
   `Const` and `TIMEOUT = 30` one indent further in is a `Property`. **Whichever way the question is
   answered, the current state is half of it.**

**Why it is worth fixing rather than shrugging at.** A class box that lists a constant beside
mutable state tells a reader the wrong thing about what they may change, and `CLASS_MEMBER_KINDS`
exists precisely to draw that line. It also compounds 229: that ticket stops method locals being
published as properties, so what remains under `Property` becomes the answer to *"what state does
this class hold"* — and a constant sitting in it is then a wrong answer with nothing else to blame.

## Scope

1. **Answer the convention question in PLAN §19, first.** Is an upper-case identifier evidence of a
   constant under R2, or is only a spec-level marker (`Final`, `const`, `readonly`, `enum`) evidence?
   The rest of this ticket is mechanical once that is decided; deciding it per adapter is how the
   split arose.
2. **Emit `ClassConst` from the spec-level signals** — python `Final` (bare and subscripted), ts
   `readonly` on a class property, and whatever the answer to item 1 admits. Each adapter reads its
   own language (R2).
3. **Apply Python's rule at every scope it claims.** If upper-case counts, a class-body
   `TIMEOUT = 30` is a `ClassConst`; if it does not, module-level `Const` loses that path and keeps
   only `Final`. One rule, both scopes.
4. **Keep TS's `EnumMember` mapping or replace it deliberately.** An enum member being a
   `ClassConst` is defensible, but it currently means the kind is *occupied* rather than modelled —
   whichever way, the PR says which.
5. **Regenerate the parity table.** `scripts/adapter_parity_report.py` already has the
   `ClassConst` row; `tests/test_adapter_parity.py` turns red until §7 is regenerated, which is the
   proof this ticket landed.

**Not in scope:** `modifiers` capture, which is 231's; a new node kind (the vocabulary is adequate,
so no `contract_version` bump is owed — R3's literal trigger does not fire); Python `Enum` members,
which 217 already models as `Enum`.

## Acceptance criteria

- **AC1 (R6.5).** The parity fixtures assert **today's** split first — `ClassConst` count 1 · 0 · 0 ·
  0 across php · python · sql · typescript. That row already exists in the generated table, so the
  guard is the pinning test and it must be seen to fail before the change, not after.
- **AC2** After the change each adapter's parity cell matches the decision from scope item 1, and
  `docs/ADAPTER_PLAYBOOK.md` §7 is regenerated in the same commit.
- **AC3** Python's constant rule is scope-symmetric, with a fixture proving both scopes agree —
  the asymmetry at `parse.py:657` is the defect, not the threshold.
- **AC4** A class diagram over a fixture with one constant and one mutable property distinguishes
  them for every adapter that declares the capture, and is byte-identical for PHP (061/AC3).
- **AC5** Identical input yields identical rows (R4.2), and `tests/contract/adapter_registry.py`
  carries any changed expectations as data, never as an edit to the harness body (147/AC2).

## Exclusions

- **E1** Whether a reader *wants* constants split out of a class box is unproven — no field round
  asked. The honest artifact is the parity row plus the diagram diff; if a reviewer finds the split
  makes the box noisier, recording that and closing as *declined on evidence* is legitimate (225/E1's
  precedent).

## Notes

**This ticket exists because the table stopped being hand-typed.** The playbook's first §7 was
written from source reading and had no `ClassConst` row at all; the row appeared the moment the
table became `scripts/adapter_parity_report.py`'s output. That is the argument for the generator,
and it is recorded here rather than in the playbook, which states the mechanism and not its history.
