---
id: 216
slug: the-scoping-206-shipped-is-unreachable-from-an-mcp-client
title: '`working_roots` is documented in `generate_onboarding`''s own docstring and absent from its schema, so the scoping 206 shipped cannot be reached from an MCP client — the tour visited `src/` zero times in 15 steps'
phase: 3
milestone: M11
status: todo
depends_on: [206, 205, 210]
---

## Why this exists (field retro round 13 §14, §9.b)

[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) shipped the fix for exactly
this problem: on a repo that is 78 % read-only legacy, an unscoped tour ranks the whole index by
degree and never reaches the tree the reader works in. Round 13 tried to use it and could not:

> **`working_roots: null`, and the tool's schema exposes only `audience` and `detail_level`.**
> `working_roots` is documented in the tool's own description but is `CA_WORKING_ROOTS` — env, read at
> spawn. **Unscoped result on a repo 78 % read-only legacy: 15 tour steps, `src/` appears ZERO times.**
> Step 1 is `legacy/alpha/web/tests/phpunit/Stubs.php`; the only non-legacy file in 15 steps is
> `config/legacy_aliases.php`.

This is the round's **only unjustified veto**, and §9.b's note on it is the finding: *"every
unjustified veto is a value finding: one, and it is not mine"* — the evaluator did not decline to use
the parameter, the parameter was not callable.

The code says the same thing plainly. `code_atlas/tools/generate_onboarding.py:95` documents
`` `CA_WORKING_ROOTS` / `working_roots` restricts the tour, flow seeds and busiest-file pick to those
trees (206) ``, and the enclosing signature two lines above is
`generate_onboarding(detail_level=..., audience=...)`. The value reaches the builders through
`config.working_roots` (`:120`), resolved at process start. **The pipeline below the tool takes the
parameter at every level** — `onboarding/dataset.py:514`, `artifact.py:344`, `modules.py:216`,
`flows.py:210` all carry `working_roots`. Only the tool boundary drops it.

**This is round 12's ticket 177 repeating in the same shape**, and the retro classes it that way: a
capability that shipped onto a surface an MCP client cannot reach. It is the standing **7-I** finding
— *no channel advertises a non-MCP surface* — with a second instance from the same round: the
evaluator spent a full day on this server without learning that `check_column_defaults` and
`trace_capability` exist.

**Why it matters more than a missing knob.** The artifact is *committable*: it outlives the session and
a human reads it. An unscoped tour does not merely waste steps, it teaches a newcomer that this
project's important files are vendored legacy stubs. §14 declined to commit the tree for a different
reason, but this one would have survived the fix.

## Scope

1. **`working_roots` becomes a `generate_onboarding` parameter**, with the same meaning the docstring
   already gives it and `config.working_roots` as the default when unset. An explicit argument wins
   over the environment; unset stays "the whole index".
2. **The precedence is stated where a caller reads it.** 210 settled that `detail_level` sizes the
   *response* while `audience` shapes the *written tree*; `working_roots` is a third axis — it shapes
   the tree's **population**. The docstring says which of the three does what, or the next reader
   guesses.
3. **The written tree records the scope it was built under.** `artifact.py:799` already emits
   `scope: working_roots=…`; the acceptance is that a per-call scope reaches it, so a committed file
   cannot be mistaken for an unscoped one.
4. **Audit the same defect across the surface.** This is a class, not an instance: any tool whose
   docstring names a knob its schema does not expose has the same defect. The sweep is mechanical and
   its result is reported even if it is zero.

### Explicitly not in scope

- **Changing what `working_roots` means** or how scoping ranks. 206 settled that; this ticket carries
  the value, it does not reinterpret it.
- **Announcing tool existence to a client** (the wider 7-I finding — *12 of 24 tools have never been
  called in thirteen rounds*). That is a routing problem with no MCP surface, and it needs its own
  evidence.
- **The other §14 defects** — `modules: 24741` in the Summary block against 24 tabulated business
  modules, the false *"no declared test command"*, the absent entry point, the `Community/Mail`
  label family, the 5×-wrong mirror-subtree overlap. Each is real and each is a separate finding.

## Constraints

- **R3** — a tool signature is part of the contract surface. Adding an optional parameter with an
  unchanged default is additive; design records whether the schema hash the client sees requires a
  bump.
- **R4.2** — deterministic: the same scope produces the same tree.
- **R5.6** — a scoped tree that reaches fewer files must not read as a smaller repo. 192's caveat
  (*"a capped list is not a smaller repo"*) already fires in `flows.md`; the scope must not defeat it.
- **R6.9** — assert at the consumer: the proving test calls the tool with the argument and reads the
  written files, not the config object.

## Acceptance criteria

1. `generate_onboarding(working_roots=[...])` restricts the tour, flow seeds and busiest-file pick to
   those trees, pinned by a fixture whose unscoped run visits a different file set.
2. With the argument unset, behaviour is byte-identical to today, including when `CA_WORKING_ROOTS` is
   set — the environment default is preserved, not replaced.
3. An explicit argument overrides the environment, pinned by a test running both together.
4. The written tree names the scope it was built under, and an unscoped tree is distinguishable from a
   scoped one by reading the file alone.
5. The docstring states the three axes and what each shapes (Scope 2).
6. Scope 4's sweep is recorded with its method and its result, including a zero.

## References

Field retro round 13 §14 (the 206 row: `working_roots: null`, 15 steps, `src/` zero times), §9.b (the
one unjustified veto), §15 (7-I, confirmed on two more tools), §16 item 4 (this ticket).
[206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) (the scoping this exposes),
[205](205_a-module-page-per-node-budget-slot.md) (the written tree),
[210](210_the-artifact-has-one-shape-for-every-reader.md) (the `detail_level` vs `audience` split this
extends to a third axis).
`code_atlas/tools/generate_onboarding.py:78` (the signature), `:95` (the docstring line that promises
the parameter), `:120` (`config.working_roots`), `code_atlas/onboarding/artifact.py:799` (the scope
line already written into the tree), `code_atlas/onboarding/dataset.py:514`,
`code_atlas/onboarding/modules.py:216`, `code_atlas/onboarding/flows.py:210` (the pipeline that already
takes it).
