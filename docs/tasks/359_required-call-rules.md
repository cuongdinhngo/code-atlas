---
id: 359
slug: required-call-rules
title: 'A rule can forbid an edge but not require one, so a missing-check audit is rebuilt outside the index'
phase: 2
milestone: Coverage
status: todo
depends_on: [138]
---

## Why this exists

A field audit (2026-10-01, an anchor PHP + SQL Server project) runs a security-pattern census
outside code-atlas. It reads `graph.db` directly and hand-codes six graph engines. All six ask one
question: does every symbol in a set S call one of the gates G? For example, every ajax write
handler must call an access check, and every service setup must turn authentication on. With the
graph, 41 of the census's 41 ticket-proven checks pass. Without it, 25 pass.

The consumer pays twice. It re-implements what the server already owns: tiers, freshness and
mid-build detection. It also reads the SQLite schema, which is not a contract. 138's rules can only
say "must not reach", a check for an edge that is present. Requiring a gate is the absent-edge
form, and no rule can say it today.

## Scope

1. `check_architecture_rules` gains a rule mode, `required`, beside today's `forbidden`:
   - `sources` selects symbols with path globs, plus an optional name regex and node kind.
   - `required` names target qnames.
   - A source with no edge of `kinds` to any target within `depth` is a violation.
2. **Absence is tiered from the source's outgoing edges.** A violation is confirmed only when every
   outgoing edge of `kinds` from that source is `RESOLVED`. Otherwise it is a candidate, with an
   `unresolved_outgoing` count. A rule never reports a source as clean while it has an unresolved
   call.
3. **Calibration as data.** A rule may list `expect` with qnames known to violate and qnames known
   to pass, for example the fixed sites of past tickets. The per-rule report gives
   `expected_found` and `expected_missed`. A rule that misses one reads `calibration_failed`, and
   its rows are still returned.
4. Language-specific gate and sink names live only in the rule file. The core gains no names
   (R1.1, R2.2).

**Out of scope:**
- Tracking tickets or a taxonomy.
- Sinks that are text and never become an edge, such as echo, markup and `innerHTML`. Those stay
  with Grep or a SAST tool.
- A new tool. The surface stays at 24 tools, and a separate tool must make its own case against
  that pin.

## Acceptance criteria

- **AC1:** In a fixture of three handlers, two call the gate and one does not. The rule returns
  exactly one confirmed violation.
- **AC2:** A handler that reaches the gate only through an unresolved `$x->check()` is a
  candidate, with `unresolved_outgoing` ≥ 1, and never confirmed.
- **AC3:** Take handler → helper → gate. With `depth` 2 there is no violation; with `depth` 1 the
  handler violates.
- **AC4:** If `expect` lists a qname as violating and it is not, the rule reads
  `calibration_failed`.
- **AC5:** With no `required` rule, the `forbidden` rule output stays byte-identical (R4.2). An
  invalid `required` rule fails loudly at load (R5.3).
- **AC6:** If `sources` matches zero symbols, the rule says so, in the
  `rule_matched_no_files` family, rather than reporting zero violations.
- **AC7:** No repo or framework names appear under `code_atlas/` (R2.2 gate). Fixtures use
  stand-in names (R2.4).
