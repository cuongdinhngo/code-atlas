---
id: 345
slug: grep-time-symbol-nudge
title: 'A grep for a symbol gets one "ask code-atlas first" line — right after it, from adapter-declared shapes'
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
- Adapter `meta` declares `name`, `extensions`, `capabilities` and `contract_version`
  (`contract.py`, `validate_meta`) — no symbol shape, so the core has nothing to build a
  language-neutral pattern from. `META_FIELDS` is closed, so a new key is a contract change.
- PostToolUse speaks after the first grep, not before it. That is the earliest non-blocking seam;
  a PreToolUse block is out of scope (it would make Grep fail, not steer).

## Scope

1. **Contract: adapters declare their symbol shapes.** A new optional `meta` field lists the
   regex shapes that mark a grep pattern as a symbol search in that language — declarations
   (`function x`, `class X`), qualified references (`->x(`, `::x(`) **and the bare call `x(`**,
   the exact shape of the anchor skill's `grep -rn "methodName("`. Name the field for what it
   matches, not "declaration keywords". Bump `contract_version` and extend the conformance suite
   (R3); each adapter encodes its language standard, never a repo's names (R2).
2. **`code-atlas-nudge` console script**, the upstream of the anchor hook, shipped in 344's plugin.
   - Patterns come only from adapter `meta`, never widened by hand (the 200 poke-filter rule).
   - **Parse surface, closed:** the Grep tool's `pattern` / `path` / `glob` / `type`, and in Bash
     the first `grep`, `rg` or `git grep` of the command with its `--include`, `-g/--glob`,
     `-t/--type` and path arguments. Anything else (pipes past the first grep, `find -exec`,
     `xargs`) is silent — a missed nudge costs nothing, a wrong one costs trust.
   - **Scope rule:** a shape fires when the grep is unscoped or its scope includes that adapter's
     suffixes, and stays silent when the scope is limited to other suffixes only. That one generic
     rule yields the anchor's exemption — a proc name grepped over `*.php` is a string literal,
     Grep is right there — with no language branch in the core (R1.1).
   - Rate-limited to once per kind per session (keyed on the hook's `session_id`). It never
     blocks, always exits 0, and stays silent with no index.
   - Each firing appends one line to the index's log, so a later scoring run can count it.

## Acceptance criteria

- **AC1:** Replaying the anchor's grep shapes — a PHP method (`->x(`, bare `x(`), a SQL proc over
  `*.sql`, and the same shapes unscoped — fires the nudge once per kind, and a second replay in the
  same session stays silent. A literal-text grep (a config key, a comment), a proc name grepped over
  `*.php`, and a Bash shape outside the parse surface never fire.
- **AC2:** A drift test, in the manner of `test_poke_snippet_covers_every_adapter.py`, fails when an
  in-tree adapter ships without symbol shapes (optional in the contract, required in this repo).
- **AC3:** The README tells a project that wires its own grep-nudge hook to remove it once the
  plugin is installed, so each event gets one nudge, not two. The anchor's retirement is its own
  change, outside this repo.
- **AC4:** A test asserts each firing writes its log line (kind, adapter, session). Scoring the
  recognition effect is 200's AC5 and waits on 200; this ticket does not claim it.

## Out of scope

- sed/awk slices of a body by line range — the anchor's hook catches them, but they are a
  read-a-symbol signal, not a grep; `code-atlas-signal` (099) is where they belong.
- A PreToolUse block on Grep.

Only the plugin packaging depends on 344; the contract field and the script can land first.
