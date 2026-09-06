---
id: 231
slug: params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature
title: '`params` is emitted by PHP alone and `args`/`arg_keys` by PHP and TS alone, so a method signature, a call-site argument filter and every `CA_INDIRECTION_RULES` edge are a per-adapter accident the payload presents as a language fact — and 222''s cross-language link inherits the gap silently'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [049, 063, 040, 020, 222]
---

## Why this exists

`NODE_FIELDS` and `EDGE_FIELDS` (`contract.py:121-144`) carry four optional fields with live
consumers. R1.6 makes them optional by design — *"an absent flag is legal and the core degrades
without it"*. **What was never decided is whether the core is allowed to degrade silently, and it
does.** Measured today by running each adapter's own `--file` mode over one equivalent fixture per
language:

| optional field | php | typescript | python | sql | who reads it |
|---|---|---|---|---|---|
| `params` (callable) | `[{name,type}]` | **`null`** | **`null`** | **`[]`** on a proc with two declared parameters | `class_diagram.py:220`, `onboarding/module_facts.py:25` |
| `extra.type` (return / property) | `\User` | `User` | **absent** | `data_type` on `Column` | signature display, type table |
| `args` (CALLS/NEW) | `["string","number"]` | `["string","number"]` | **`null`** | **`null`** on `EXEC … @a = 5` | `find_callers` arg filter (049), `enrichment.py:168` |
| `arg_keys` | `[null,null]` | `[null,null]` | **`null`** | **`null`** | `enrichment.py:231` (063) |
| `modifiers` | `["private","static"]` | **`null`** — the word `modifiers` does not appear in the adapter | `["staticmethod"]`; **no visibility** | `[]` | `class_diagram.py` (a UML `+`/`-`/`#` marker) |

The fixture is three lines per language and the same in each — a class `User`, a class `Repo` with a
typed property, and one method taking and returning `User`; plus a two-line call `q("name", 3)`, a
`private static` method, and for SQL `CREATE PROCEDURE dbo.Pay @amount int, @who nvarchar(50) = 'x'`
called as `EXEC dbo.Pay @amount = 5, @who = 'bob'`.

**Three consequences, in ascending severity.**

1. **A class diagram is a signature for PHP and a bare name for everything else.**
   `class_diagram.py:220` reads `params`, so the same request against a Python or TS repo renders
   `find()` where a PHP repo renders `find(User $u): User`. The renderer is correct; it was handed
   nothing. Nothing in the payload says which of the two happened.
2. **`find_callers`'s argument filter is inert on a Python repo, and the one disclosure that exists
   is the wrong grain.** 049 built the filter over `args` and — to its credit — also built
   `args_unrecorded`, *"how many call sites the filter could not judge"* (`find_callers.py:104-106`,
   set at `:192-196` and carried onto a miss at `:219-220`). So the tool is not silent. But the
   count is **per call site**, not per adapter: an agent reading `total_count: 0` beside
   `args_unrecorded: 47` cannot tell "these particular sites pass a variable" from "this language
   records no arguments at all, so the filter will never work here". **This is the shape the fix
   should take for the other three fields** — 049 proved the disclosure is cheap; nothing generalised
   it, and nothing raised it to the adapter.
3. **`CA_INDIRECTION_RULES` yields zero edges on a Python repo, and 222 is being built on it.**
   Both `key_from` modes bottom out in `_parse_args` (`enrichment.py:289-292`): `null` → `None` →
   `[]`, in `_keys_from_arg_keys` (`:247`) and in the `string` arm (`:234-236`) alike. So 040's
   machinery — the machinery [222](222_the-cross-language-link-is-one-rule-target-away-from-machinery-that-exists.md)
   describes as *"already extracts it and only the target is hardcoded"* — cannot fire for a
   Python-over-SQL repo at all. **222 does not know this**, and a Python consumer is exactly who
   would ask for it next.

**The fix mechanism is already named in the code and was never honoured.** `_keys_from_arg_keys`'s
own docstring (`enrichment.py:249-253`) ends: *"adapter #2 should advertise capture via an R1.6
capability."* `KNOWN_CAPABILITIES` (`contract.py:185`) still holds exactly one entry,
`semantic_types`, declared by exactly one adapter.

## Scope

1. **Emit what the language puts in the file.** Python's `ast` carries `arg.annotation`,
   `returns`, and a `Call`'s `args`/`keywords`; TS carries `node.parameters`, `node.modifiers` and
   `ts.getJSDocType` — `types.js` already reads the last for its own type table; T-SQL spells a
   parameter list between the routine name and `AS`, and a named argument as `@p = <literal>`. Every
   adapter has the data in hand at the emission site and drops it. Fill `params`, `extra.type`,
   `modifiers`, `args` and `arg_keys`, each in its own language's spelling (R2 — no repo's names, no
   framework).
2. **Declare capture, do not infer it.** Add the capability names the docstring asks for to
   `KNOWN_CAPABILITIES` and to each adapter's handshake. An adapter that does not capture a field
   says so once, at handshake, instead of every consumer guessing from a `null`.
3. **Disclose at the answer, not only at the handshake.** Follow 160/173's discipline: a filter or a
   diagram that came back thin *because the adapter declared no capture* says so, and a request that
   had the data stays byte-identical. A confident answer must not grow a field.
4. **Record the dependency in 222.** 222's scope gains one line: the cross-language rule needs
   `args` capture from the calling language, so it is blocked for Python until item 1 lands there.

**Not in scope:** inferring a type Python does not write (an unannotated parameter stays unknown —
guessing is R5.2); `is_test`, which no adapter meaningfully sets and `class_diagram.py:253` already
records as unused; `ClassConst` classification, which is
[234](234_classconst-is-a-php-only-kind-and-the-two-signals-that-would-fill-it-elsewhere-are-discarded.md).

**SQL is in scope, and an earlier revision of this ticket wrongly excluded it** on the premise that
it "has no parameters or call arguments to capture". `CREATE PROCEDURE dbo.Tag @name nvarchar(50),
@n int = 3` declares two, and `EXEC dbo.Tag @name = 'name', @n = 3` passes two; both are dropped.
The premise was never measured — it is why `scripts/adapter_parity_report.py` exists and why the
table above is now generated rather than typed. **228 lands first**: the reader that would pick up a
parameter list is the same tokenizer that currently reads `IF` as a table name.

## Acceptance criteria

- **AC1 (R6.5).** The three-line fixture above, one per language, asserts **today's** output first:
  `params is None` for Python and TS, `args is None` for Python. Without that row a green test after
  the change proves nothing, because `null` and `[]` both render as an empty signature.
- **AC2** The same fixture then yields the same shape from every adapter that declares capture, and
  the conformance registry (`tests/contract/adapter_registry.py`) carries the new expectations as
  data, never as an edit to the harness body (147/AC2).
- **AC3** A `find_callers` argument filter against a Python fixture returns the matching site, and
  the same filter against an adapter that declares no capture returns a non-`no_matches` reason with
  `authoritative: false` — the 186 pattern, reused, not re-invented.
- **AC4** `CA_INDIRECTION_RULES` produces at least one edge on a Python fixture whose call passes a
  string key, proving 040's path is live for a second language.
- **AC5** Identical input yields identical rows (R4.2), and a PHP answer that already had `params` is
  byte-identical to before the change (061/AC3).

## Exclusions

- **E1** The parity table above was measured with each adapter's one-shot `--file` mode on
  2026-09-06, not over a pinned corpus — Python and SQL have none, which is
  [233](233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md).
  The per-field verdicts are exact; any *ratio* over a real repo waits on 233.

## Notes

**Why this is one ticket and not four.** The four fields have four consumers, but one cause: the
contract made them optional and nothing ever asked an adapter to say which it fills. Fixing one
field leaves the other three lying in the same way, and the capability declaration in item 2 is a
single edit that covers all of them.

**The scoreboard belongs in the playbook, not here.** The measured table above is this ticket's
evidence; the standing version an adapter author checks against lives in
[`../ADAPTER_PLAYBOOK.md`](../ADAPTER_PLAYBOOK.md) §3 (R7.6 — one copy, and this one is dated).
