---
id: 232
slug: the-same-construct-is-a-references-edge-in-python-and-node-extra-in-php-and-ts
title: 'A decorator and a type annotation are `REFERENCES` edges in Python and inert node `extra` in PHP and TS, so `find_references` on a class answers three different things for the same construct — and `language_emits_none_of` cannot say so, because one emitted kind in the set masks a never-emitted sibling'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [217, 019, 186, 094]
---

## Why this exists

`REFERENCES` is in `FQN_EDGE_KINDS` (`contract.py:73-75`) and in `UNMODELLED_REFERENCE_KINDS`
(`contract.py:99`) — the set 065's honesty evidence is drawn from. **Three adapters populate it from
three disjoint constructs, and the divergence is not a language difference.** Measured 2026-09-06 by
running each adapter's `--file` mode over one equivalent fixture — a class `User`, a class `Repo`
with a `User`-typed property, and a method taking and returning `User`:

| construct | php | typescript | python |
|---|---|---|---|
| type annotation (param · return · property) | `params[].type` + `extra.type`, **no edge** | `extra.type`, **no edge** | **`REFERENCES` ×2** |
| decorator / attribute | `extra.attributes`, **no edge** (`Visitor.php:1164-1169`) | `extra`, **no edge** (019:91) | **`REFERENCES`** |
| class-string mention (`Foo::class`) | **`REFERENCES` @ `DYNAMIC`** (`Visitor.php:293-299`) | — | — |

`REFERENCES` is emitted from **exactly one site** in the PHP adapter (`Visitor.php:294`) and from
**no site at all** in the TS adapter. So `find_references("User")`:

- on a Python repo returns every annotation and decorator site, at `RESOLVED`;
- on a PHP repo returns only `User::class` sites, at `DYNAMIC`;
- on a TS repo returns nothing, and calls it a match-free answer.

**The divergence was made knowingly, once, and never revisited.** 019:91 records TS's choice as
*"decorators + declared types on node `extra` (no edge, mirrors PHP attributes)"*. 217's own decision
row R3 records the opposite for Python and cites the same precedent to overrule it: *"128-C1; PHP
attrs are extra — **product choice here is edges**"*. Both are defensible reads. What no ticket did
is pick one, or make the answer disclose which read the repo in front of it got.

**The honest-zero machinery does not rescue it, and the code says so on purpose.**
`find_references.py:219-225` reaches for `relation_unmodelled_for_language(…,
kinds=UNMODELLED_REFERENCE_KINDS)`, whose predicate is `not any(kind in emitted for kind in kinds)`
(`store.py:857`) — **any one** kind in the set. The comment beside the call (`:222-224`) records the
consequence as intended:

> It does NOT fire while any one of the kinds is emitted for this language, which is why a TS subject
> still gets a genuine zero: IMPORTS is modelled there, REFERENCES alone is not.

**That claim is what this ticket disputes.** A zero on `find_references("User")` in a TS repo where
`User` is named as a type in every consumer is not genuine — it is the exact `no_matches`-on-a-live-
subject that 221 called *"a false claim to a tech-lead review"*. The mechanism is 221's, one tool
over: there, *"T-SQL emits plenty of CALLS — just none that reach PHP"*; here, TS emits plenty of
`IMPORTS` — just no `REFERENCES` ever. The comment is honest about the wiring and wrong about the
verdict — and the dates say why. The comment landed with 186 on **2026-08-28** (`02e1f47`), when no
adapter emitted `REFERENCES` from an annotation and the reading held. 217 landed on **2026-09-05**
(`5bf383d`) and created the divergence. Nothing re-read the comment in between.

## Scope

1. **Decide the construct question once, in the plan, not per adapter.** Does an annotation or a
   decorator naming a type produce an edge? PLAN §19 is where that decision lives, and the ticket's
   first deliverable is the entry — with the cost stated: 217 measured **928 annotation sites and
   536 decorator applications naming a first-party symbol** in one repo (217:134-140), so "edges"
   is a real change in graph size, and "extra only" is a real loss of `find_references` recall.
2. **Make the adapters agree with whatever is decided.** Either PHP and TS gain the annotation and
   decorator edges, or Python's are withdrawn to `extra`. A split answer is the one outcome this
   ticket may not leave standing. Each adapter encodes its own language's spelling (R2).
3. **Make the predicate per-kind.** `language_emits_none_of` answers for a *set*; the caller needs
   *"which of these kinds has this language never emitted"*. Widen it (or add a sibling) so a
   never-emitted kind is visible even when a peer in the set is populated, and keep R5.6's `None`
   for an index that never measured itself. **This is the reusable half of the ticket** — 221 and 226
   both want it.
4. **Disclose per kind on the answer.** A `find_references` zero over a language that emits no
   `REFERENCES` is not `no_matches`; it carries the 186 reason and `authoritative: false`. An answer
   with hits stays byte-identical (061/AC3).

**Not in scope:** the tier PHP assigns `Foo::class` (`DYNAMIC` is correct — a class-string is a
runtime name); widening `UNMODELLED_REFERENCE_KINDS` itself, which would move 065's evidence set;
`params`/`args` capture, which is
[231](231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md).

## Acceptance criteria

- **AC1 (R6.5).** One fixture per language, the same three declarations in each, asserts **today's**
  divergence first: 2 `REFERENCES` from Python, 0 from PHP, 0 from TS. That row is the ticket's
  evidence and must fail to exist before the change, not after.
- **AC2** After the change the three adapters agree on the fixture, and `tests/contract/adapter_registry.py`
  carries the expectations as data (147/AC2). If the decision is *withdraw*, Python's registry rows
  shrink and the PR says so — a visible output change, not a silent one (225/AC4's rule).
- **AC3** A `find_references` zero on a language that emits no `REFERENCES` returns the 186 reason
  with `authoritative: false`, **and** the same query on a language that does emit it and genuinely
  has none still returns `no_matches`. Widening the honest zero must not retire the distinction.
- **AC4** The per-kind predicate has its own test: a fixture index where a language emits `IMPORTS`
  and no `REFERENCES` reports the second as never-emitted while `language_emits_none_of` over the
  pair still answers `False`. Both readings are correct; the test pins that they differ.
- **AC5** Identical input yields identical rows (R4.2), and an index built before the per-kind stamp
  answers as it does today rather than guessing (R5.6 / 173).

## Exclusions

- **E1** The 928/536 figures are 217's, from one private repo, and they size the decision rather than
  proving it. Reproducing a ratio over a public corpus needs a pinned Python sample, which is
  [233](233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md).

## Notes

**Why this outranks its own fix.** Item 3 is worth landing even if item 1 decides *withdraw*: the
per-kind predicate is the missing primitive behind 221's cross-language zero and 226's unlinked
`EXTENDS`, and all three tools are currently reduced to a set-level answer that one populated kind
can hide.

**TS has never been measured in the field.** Every finding filed since round 13 — 221-230 — came
from a PHP, SQL or Python build over a real repo. TS's 3 pinned public samples (`ky`, `mqttjs`,
`socketio`, task 150) prove it *builds*; nothing has asked it a question an agent would ask. This
ticket and 231 are what reading its source produced; a field round would produce more, and the
protocol for one is [`../ADAPTER_PLAYBOOK.md`](../ADAPTER_PLAYBOOK.md) §4.
