---
id: 345
slug: grep-time-symbol-nudge
title: 'A grep for a symbol gets one "ask code-atlas first" line — at the decision, from adapter-declared shapes'
phase: 2
milestone: Adoption
status: todo
depends_on: [344]
---

## Why this exists

344 installs the hooks, but none of them speaks when the agent reaches for Grep on a structural
question. Of the channels in 344's table, only a PostToolUse hook on `Bash|Grep` sees that moment.

## Evidence (anchor repo, 2026-09-29)

- **A concrete procedure step beats a general rule.** The anchor repo's CLAUDE.md routed symbol
  questions to code-atlas, and its SessionStart hooks restated it. Even so, sessions running a project
  skill answered caller questions with Grep, because the skill's own step said
  `grep -rn "methodName("`. The fix there was to rewrite six skills by hand. A new anchor project
  won't know it needs to.
- **The one channel that fired at the decision was project-local.** The anchor repo wrote its own
  PostToolUse(`Bash|Grep`) hook, `.claude/hooks/code-atlas-symbol-nudge.sh`. It spots a grep for a
  symbol (`function x`, `->x(`, `::x(`, `class X`, or a proc/table name over `*.sql`), or a sed/awk
  slice of a body by line range, and injects one "ask code-atlas first, keep Grep as the cross-check"
  line. It is rate-limited to once per kind per 15 minutes and silent without an index or a
  registration. None of that exists upstream.
- Adapter `meta` declares only `extensions` today (`contract.py`, `validate_meta`), so the core
  has nothing to build a language-neutral pattern from.

## Scope

1. **Contract: adapters declare their symbol shapes.** A new optional `meta` field lists the
   regex shapes that mark a grep as a symbol search in that language — declarations (`function x`,
   `class X`) and references (`->x(`, `::x(`) alike, so name it for what it matches, not
   "declaration keywords". Bump `contract_version` and extend the conformance suite (R3); each
   adapter encodes its language standard, never a repo's names (R2).
2. **`code-atlas-nudge` console script**, the upstream of the anchor hook, shipped in 344's plugin.
   - Patterns come only from adapter `meta`, never widened by hand (the 200 poke-filter rule).
   - A shape fires only when the grep's scope (path, glob or type) is that adapter's own suffixes.
     That one generic rule yields the anchor's exemption — a proc name grepped in host-language
     source is a string literal, Grep is right there — with no language branch in the core (R1.1).
   - Rate-limited per kind per session. It never blocks, always exits 0, and stays silent with no
     index.

## Acceptance criteria

- **AC1:** Replaying the anchor's grep shapes (PHP method, SQL proc over `*.sql`) fires the nudge
  once, and a second replay within the window stays silent. A literal-text grep (a config key, a
  comment) and a proc name grepped over `*.php` never fire.
- **AC2:** A drift test, in the manner of `test_poke_snippet_covers_every_adapter.py`, fails when an
  adapter ships without symbol shapes.
- **AC3:** A project that already wires the anchor's local hook gets one nudge per event, not two.
  Either the plugin's nudge detects that and stands down, or the anchor retires its hook, and the
  README says which.
- **AC4:** The recognition effect is scored the way 200's AC5 scores the other channels, or this
  ticket says why it could not be.
