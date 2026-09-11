---
id: 242
slug: params-is-stored-by-every-adapter-and-surfaced-by-one-tool-that-cannot-render-a-free-function
title: '`params` is stored by every adapter, indexed into `nodes_fts`, and read by exactly one tool — `class_diagram`, which renders class members only — so a signature is invisible to every nav tool, and on the anchor monorepo 604 stored-procedure signatures the graph holds cannot be reached by any call'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [231, 234, 049, 078]
---

## Why this exists (field retro round 17)

231 made `params` uniform: every shipped adapter emits it, and `capabilities_by_language` stamps
which ones do. The field session then spent its most valuable ticket answering a question `params`
already contains — *how do these two signatures differ?* — with `ls` plus `grep` over two files, and
closed by asking for a new `diff_twin` tool. Neither the session nor its retro knew the answer was
in the index, because **no nav tool returns `params`**.

The one consumer is `class_diagram` (`code_atlas/tools/class_diagram.py:246`, with 231's
`params_not_captured_by_adapter` disclosure at :104). A class diagram renders class-like members, so
a `Function` — a free function, a module-level function, **a stored procedure** — has no route to its
own signature. `read_symbol`, `search_symbol`, `file_outline` and `find_callers` name none of it at
any `detail_level`.

The remaining route is `read_symbol` returning the body and letting the reader parse the header out
of it, which is the token cost the tool exists to avoid — and for the subject measured below it is
not even available: the proc has two definitions, so 078 correctly refuses with
`subject_ambiguous` and **no body at all**.

## Evidence — measured on the anchor monorepo, 2026-09-11

Index at `contract_version: 10`, 19,352 PHP + 3,012 SQL + 2,519 TypeScript files.

| Measure | Value |
|---|--:|
| `sql` `Function` nodes (stored procedures) | 670 |
| …carrying a non-empty `params` with declared types | **604** |
| Nav tools that can return any of it | **0** |

The parameter lists are present and typed:

```
CheckLedgerDays  [{"name":"@CustomerCode","type":"varchar(8)"},{"name":"@StartDate","type":"datetime"},…]
```

**The session's own root cause, recomputed from `nodes.params` alone** — 148 `X` / `X_beta` twin pairs
exist, 28 differ in their parameter list, and one of the 28 is the defect the session spent its
analysis phase finding by hand:

```
dbo.UpdateRecursiveActivitiesUntil      [@endDate, @maxActivities, @maxRecursions]
dbo.UpdateRecursiveActivitiesUntil_beta   [@endDate, @maxActivities]
only in the first: ['@maxRecursions']
```

That is a ~30-line read over one column. It needs no new relation, no edge kind, no
`contract_version` bump and no configuration — which is also why it settles
[098](098_correspondence-relation-seam.md)'s last open argument rather than reopening it (see
References).

## Scope

- **Surface `params` on `read_symbol`.** The declaration's parameter list — name and declared type
  per entry, the adapter's own spelling, no normalisation (R4.2). Present at `standard`; decide and
  state whether `minimal` carries it.
- **Decide `file_outline` explicitly, with a reason either way.** It is the symbol map, and a map of
  20 methods with signatures may be the answer 245's reader wanted; it is also payload weight on
  every outline ([061](061_payload-weight.md), [223](223_the-envelope-bills-every-answer-and-no-gate-noticed-it-growing.md)).
  A written *no* is a deliverable here, not an omission.
- **Honesty when the field is absent.** `params` empty and `params` not captured by the adapter are
  opposite claims. 231 already stamps `capabilities_by_language`; reuse that predicate — never emit
  an empty list that reads as "takes no arguments" (R5.2, R5.6).
- **Out of scope:** any twin/diff/compare tool, any name-convention knowledge (`_beta` and friends are
  a repository's naming, R2), and `args`/`arg_keys` at call sites — `find_callers` already filters on
  those and this ticket does not touch them.

## Constraints

- **R1.1** — no language branch; `params` is a contract node field (CONVENTION §3) and the core reads
  it the same way for every language.
- **R5.2 / R5.6** — an absent capability is disclosed, never rendered as a zero. The
  `capabilities_by_language` stamp is the predicate; a pre-231 index must say it cannot tell.
- **R3** — `params` is already in the contract at its current version. If this ticket needs no
  vocabulary change, it must not bump `contract_version`; if it does, say why in the design.
- **061 / 223** — the envelope is already budgeted and gated. Measure the added bytes per row on a
  large index before and after, and state the cost on a subject with 79 parameters (the anchor holds
  one).
- **R4.2** — identical input, identical rows. No re-ordering, no type inference, no filling a missing
  type from a default.

## Acceptance criteria

- `read_symbol` on a `Function`, a `Method` and a stored procedure returns the parameter list with
  declared types, pinned by tests for at least PHP, TypeScript and SQL.
- A subject whose language's adapter does not capture `params` returns the disclosure, not an empty
  list — asserted against a stamp that says so.
- A written verdict on `file_outline`, with the payload measurement that decided it.
- Payload weight measured before/after; the numbers land in the task file.
- The two-call route is demonstrated end to end: from two qnames to a parameter-list difference, with
  no file read and no new tool.

## References

Field retro round 17 (2026-09-11, maintainer-local) §2.6 and §5 ask 1. Related:
[231](231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md) (made
`params` uniform and stamped the capability),
[234](234_classconst-is-a-php-only-kind-and-the-two-signals-that-would-fill-it-elsewhere-are-discarded.md)
(the same one-adapter-accident shape, one kind over),
[078](078_ambiguous-payload-still-picks-one-definition.md) (why the body route is closed for the
measured subject), [061](061_payload-weight.md) /
[223](223_the-envelope-bills-every-answer-and-no-gate-noticed-it-growing.md) (the weight this must
argue against), [098](098_correspondence-relation-seam.md) — **this ticket is the measurement that
answers 098's last open argument.** 098 held that drift detection was the strongest remaining case
for a correspondence *relation*, because 115's path comparison cannot see drift. Drift at signature
granularity turns out to need no relation: the graph already holds both sides at the granularity
that matters. 098 stays `deferred`; its verdict wants this recorded.

## Token usage

| Phase | Tokens |
|---|---|
| — | not yet started |
