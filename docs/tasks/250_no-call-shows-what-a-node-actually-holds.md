---
id: 250
slug: no-call-shows-what-a-node-actually-holds
title: 'No call shows what a node actually holds, so "the adapter never captured this" and "a tool declines to return it" are indistinguishable from the outside — and a consuming agent guessed wrong in the optimistic direction'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [247, 231, 244]
---

## Why this exists (field retro — anchor-repo, 2026-09-11, round 17, verification pass)

Round 17's retro asserted that column types were *"sitting right there in the index, with no way to
get them out"*, and ranked opening that door as its top ask. The assertion was wrong — the adapter
never captures them ([247](247_the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key.md))
— and the interesting part is **why a careful agent got it wrong**.

It was asked to re-run the question under a constraint: answer using code-atlas tools only, then
separate, per missing fact, *(i) the index holds it but no tool returns it* from *(ii) the index never
captured it*, and state the evidence for the choice. Its answer on column data type:

> **Not distinguishable.** `read_symbol` on a stored procedure returns `params` with full types —
> `{"name": "@bondAmount", "type": "money"}` — so the SQL adapter does parse T-SQL type syntax; it is
> not type-blind. But that only proves types are captured for callable parameters. `read_symbol`'s
> contract says `minimal`, and every non-callable kind, omit both, so a Column never carries a type
> field. That is a surface rule; it says nothing about whether the node stores one. **I have no call
> that shows me a Column node's raw contents, so I have no evidence to choose.**

It then retracted its own headline claim. The retraction is the finding: **the evidence needed to
avoid the error does not exist on the surface at any price.** The agent reasoned correctly from
everything it could see and still had to guess, and the direction it guessed — toward the index being
richer than it is — is the one that wastes a maintainer's round.

The same undecidability hit every other fact it was asked about, each with a different false signal:

| Fact | What the agent had | Why it could not conclude |
|---|---|---|
| Column data type | `declared_types: true` on the `sql` stamp | The flag is true of callable `params`; the agent had first read it as covering columns |
| `NOT NULL`, `IDENTITY` | `modifiers: false` on `sql`, `true` on php/ts | Whether SQL nullability *is* a "modifier" is nowhere defined — php's `modifiers` means `public`/`static`. Called "a strong hint, not evidence" |
| Primary key | `search_symbol`'s `kind` enum offers `Table`/`Column`/`ForeignKey`, no `PrimaryKey`; `ForeignKey` returns 1,093 real nodes | Correctly inferred constraints are modellable in principle and PK simply has no kind — the one case it got right, and only from an enum |

Note what carried the two near-misses: a **capability flag** and an **argument enum**. Neither is a
statement about node contents; both were pressed into service because nothing else was available.

## Root cause

Every read path projects. `search_symbol`'s `_hit` returns `{qname, kind, file, line}` (plus 239's FK
target for a `Column`); `read_symbol` returns a source slice and, since 242, `params` on callable
kinds only; `file_outline` returns positions. `extra` — the free-form seam every adapter uses for the
facts that do not fit `NODE_FIELDS`, and where 236 put the FK's child and referenced tables — is
written by adapters, read by `store.py` and several tools, and **exposed by none of them**.

The capability stamps (231/244) were built to answer "what does this index hold", and they do it at
the granularity of *language × named flag*. That granularity cannot answer a question about one kind
(`does a Column carry a type?`), and it has no negative form: a fact with no flag is silent, which
R5.6 correctly forbids reading as a zero — leaving the agent with exactly the "can't tell" it
reported, and no route out of it.

## Scope

A way for a caller to see what a node actually holds, so "not captured" is checkable rather than
inferrable.

Two candidate shapes, to be decided in phase 2 — the ticket does not bind one:

- **A raw-fields view on an existing tool.** `read_symbol` at a new detail level, or a flag, returning
  the node's stored `NODE_FIELDS` and `extra` keys verbatim for one qname. Cheapest, keeps the surface
  at 24 tools, and is the natural home — the agent already reached for `read_symbol` and got a source
  slice.
- **Per-kind capability reporting.** Extend the 231/244 stamp from *language × flag* to name which
  fields each kind actually carries in **this** index, derived from the index rather than declared by
  the adapter. Answers the question without a new read path, and is the honest generalisation of what
  the stamp already claims to be.

The first is the working assumption; the second may subsume it.

## Constraints

- **R5.6 — derive it, do not declare it.** A per-kind report that an adapter *announces* repeats the
  231 failure one level down: the adapter would be asserting what it believes it emits. Read it off
  the index, so the answer is about the graph the caller is querying.
- **R4.2 — deterministic.** Identical index, identical field report. A sampled answer ("most Columns
  carry a type") is a different and weaker claim; if sampling is used, say so in the payload.
- **Not a source dump.** This exposes which fields are populated, not a new way to read bodies.
  `extra` holds adapter-specific values and the answer must stay bounded — key presence and counts,
  not every value in a 20,808-node kind.
- **R1.1.** The report is keyed by contract kind, never by language name in the core.
- **Omit-when-empty (061).** This rides an explicit request; nothing is added to the default payload
  of any existing call.

## Acceptance criteria

- **AC1** For a given qname, a caller can obtain which `NODE_FIELDS` and which `extra` keys that node
  actually carries, without reading source and without opening the database.
- **AC2** The three facts of this retro are decidable from tool output alone: a `Column` in a
  pre-[247](247_the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key.md)
  index reports no type, nullability or identity key; after 247 it reports them. The same call
  distinguishes the two indexes.
- **AC3** A `Column` with an FK reports the key 239 attaches; one without reports its absence — the
  caller can tell "this column has no FK" from "this tool does not return FKs".
- **AC4** The answer is bounded on the widest kind in the index and does not scale with node count.
- **AC5** No existing payload changes shape — every current tool's output is byte-identical
  before and after (the 022 AC3 check).

## References

- `code_atlas/tools/search_symbol.py` (`_hit`), `code_atlas/tools/read_symbol.py` (`_attach_params`,
  the 242 kind gate), `code_atlas/tools/file_outline.py`.
- `code_atlas/contract.py` — `NODE_FIELDS`, and `extra` as the frozen-fields escape hatch (236).
- [231](231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md) /
  [244](244_no-channel-announces-a-capability-change.md) — the capability stamp whose granularity this
  extends, and the `declared_types` flag the agent over-read.
- [247](247_the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key.md)
  — the capture gap this ticket makes visible. Filing both is deliberate: 247 fixes one instance,
  250 makes the next one checkable instead of guessable.
