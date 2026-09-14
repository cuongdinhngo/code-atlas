---
id: 280
slug: a-parser-accepts-what-the-runtime-rejects
title: 'A parse-failure count answers "what could not be parsed", a reader uses it as "what cannot run", and the two differ by every compile-stage error a parser accepts by construction — a handoff built a PHP-8 upgrade argument on 2 when `php -l` found 10, including a live fatal the count was being used to rule out'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [058]
---

## Why this exists (field retro — a PHP 5.6 monolith, 2026-09-13, round 19 §4)

A prior session's handoff built its central structural argument on the index's parse-failure count:
*"66 parse failures… only 2 are the project's own code"*, concluding the PHP 8 syntax problem was a
document-generation problem. The next session ran `php -l` over the same scope and found **10**.

Four files fail to compile on *every* runtime, 5.6 included, and the index accepted all four —
a re-assigned auto-global used as a parameter name, an abstract method with a body, a redeclared
function, a method call in a property initialiser. All are **compile-stage** errors; a parser accepts
them by construction. So is the one that mattered: an unparenthesized nested ternary, valid on 5.6,
**fatal on 8.0**, in live view code. It is not among the 66, and the 66 were being used to rule out
exactly that.

This is not a defect in the parser. It is a defect in a count that invites one reading and supports
another, with nothing on it to say which — and the evidence that the trap is real is that a previous
session had already fallen into it and the next nearly inherited the conclusion:

> *"Gate on `php -l` against the target runtime, not on the index's parse-failure count. The index
> remains the right tool for reachability and reference counts; it is the fatal surface it
> structurally understates."*

`parse_failures` (files with `parsed_ok = 0`) ships on `standard`, with `parse_failure_paths` on
`verbose` (058). Both say how many files the adapter could not parse. Neither says that a file it
*could* parse may still be unable to run.

## Scope / Deliverables

- **One sentence where the count is** — the field, the tool description, and §12's row say the count
  is syntax the adapter could not parse, and that compile-stage errors are not detected, so it is a
  floor on brokenness and never a fatal surface.
- **A route, not only a caveat** (R5.4c): the reader is pointed at the runtime's own checker for the
  question they are actually asking. The core runs nothing — it names the class of tool.
- **Say it once.** The sentence lands where the number is served; `docs/` gets a pointer, not a copy
  (R7.6).

## Constraints

- R4/R4.1: the core does not execute a language runtime, now or as part of this.
- R1.1: the wording is language-agnostic — "the language's own compiler/linter", never `php -l` in
  core code or a per-language string.
- 061 / 223: no new field, no new payload weight on `minimal`; this is wording on what already ships.
- The count itself does not change — 058's semantics stay, including `parse_failures` mirroring
  `failed` exactly rather than a subset.

## Acceptance criteria

- The disclaimer is present wherever `parse_failures` is served, pinned by a test so it cannot be
  dropped silently.
- The tool description and CONVENTION §6's row agree with it in the same commit.
- No language name appears in the core wording.
- A fixture file that parses and cannot compile still counts as parsed, and the payload's wording is
  what makes that honest.

## References
`code_atlas/tools/get_index_status.py` (`parse_failures`, `parse_failure_paths`),
field retro round 19 §4 / §6.3 / §8 (fatal-surface dimension, 3/10),
[058](058_list-parse-failures.md).
