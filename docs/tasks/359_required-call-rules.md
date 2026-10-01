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
2. **Absence is tiered over everything the walk explores.** A violation is confirmed only when
   every edge of `kinds` met within `depth` is `RESOLVED`: the source's own edges and those of
   every intermediate symbol. Otherwise it is a candidate, with an `unresolved_outgoing` count
   over the whole explored frontier. In handler → helper → (unresolved), the handler is a
   candidate, not confirmed. A rule never reports a source as clean while the walk met an
   unresolved call.
3. **Calibration as data.** A rule may list `expect` with qnames known to violate and qnames known
   to pass, for example the fixed sites of past tickets. The per-rule report gives
   `expected_found` and `expected_missed`. A rule that misses one reads `calibration_failed`, and
   its rows are still returned.
4. Language-specific gate and sink names live only in the rule file. The core gains no names
   (R1.1, R2.2).
5. **This is a new evaluation path, not a flag on today's.** `architecture_rules.py` matches at file
   granularity: `ArchitectureRule.forbidden` holds globs, and `Violation` carries `source_file` and
   `forbidden_file`. `required` selects symbols and targets qnames, so it needs its own rule type,
   walk and report row. `forbidden` keeps its code path untouched, which is what AC5 pins.

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
- **AC6:** If `sources` matches zero symbols, the rule says so rather than reporting zero
  violations. Design decides between reusing `rule_matched_no_files` and adding a reason to the
  `NavReason` vocabulary (`code_atlas/tools/nav_result.py`). If it adds one, check whether that
  vocabulary is contract-frozen (R3) and, if so, bump and cut a release.
- **AC8:** handler → helper → gate, where helper also has an unresolved call: with `depth` 2 the
  handler passes (the gate is reached). In handler → helper → (unresolved only), the handler is a
  candidate, never confirmed.
- **AC7:** No repo or framework names appear under `code_atlas/` (R2.2 gate). Fixtures use
  stand-in names (R2.4).
