---
id: 464
slug: tools-hidden-by-allowlist
title: "Say which tools a `CA_TOOLS` allow-list hides, so an upgrade's new tools are not lost silently"
phase: 2
milestone: "0.11 Verify & Compute"
status: todo
depends_on: [268]
---

## Why this exists

Round-4 field read on the anchor (2026-11-27, 819 PRs over 3 weeks, 128 with the 0.11 trial lines
filled in). `verify_refs` and `compute` were used **0** times. That was not because agents chose
not to use them: the anchor's `CA_TOOLS` still listed the 24 tools of 0.10, so the session never
received either tool. All 120 "not used" lines meant "not available", and 442 never started.

- `allowed_tools()` (`code_atlas/main.py`) serves exactly the names listed. A list written for one
  version freezes the tool set: every tool a later version adds stays off, and nothing says so.
- The server instructions are already cut to the tools that are served (268, `instructions.py`).
  The plugin's `SKILL.md` is static text, so it still routes to `compute` and `verify_refs`.
- `get_index_status` already receives the served set (`create(config, registered)`), but only
  uses it for suggestions. No field names what was cut.

## Scope

1. `get_index_status` adds `tools_not_served`: the names in `TOOL_NAMES` that `CA_TOOLS` leaves
   out, plus one hint (unset `CA_TOOLS`, or add the names). Omitted when nothing is cut
   (omit-when-empty, 061). Shown at `minimal` too, because it explains every later miss.
2. The SessionStart state line adds `hidden by CA_TOOLS: <names>` (or a count past 3) whenever
   the cut hides a tool. Wording is decided in design. The line is what a person sees; status is
   what an agent sees.
3. `SKILL.md` gains one sentence: a tool named here that is not in your tool list is hidden by
   `CA_TOOLS`. Say so in the answer instead of silently falling back to grep.
4. Upgrade note in README and CHANGELOG: when `CA_TOOLS` is set, new tools are not served.

Out of scope: a deny-list or `+new` syntax for `CA_TOOLS`. One allow-list stays the only knob
(R1.2); this ticket makes its cost visible, nothing more.

## Acceptance

1. `CA_TOOLS` = the 0.10 list → status `tools_not_served == ["compute", "verify_refs"]` with
   the hint; `CA_TOOLS` unset → no field (golden).
2. The state hook under the same env shows the hidden count; unset → line unchanged byte for byte.
3. `tests/test_claude_code_plugin.py` holds the `SKILL.md` sentence.
4. The anchor, with the field shipped: the status read before the restart in 442 names the two
   tools. Report it.
