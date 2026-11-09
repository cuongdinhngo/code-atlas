---
id: 445
slug: tool-description-budget
title: "compute and verify_refs: one-line descriptions, and the 434 budget question put to §19"
phase: 2
milestone: "0.11 Verify & Compute"
status: done
depends_on: [434, 440, 441]
---

## Why this exists

Pre-flight A7. 440 and 441 raised 434's caps (+600 description and +1,100 surface per tool, +135 for
the template ids) rather than fit. The ask: revert to 434's caps and shorten the two descriptions.

## Finding

434's caps cannot hold 26 tools by shortening only these two. The 24 tools 434 measured already use
10,066 of the 10,100 description cap and 23,580 of the 23,635 surface cap; the two new closed input
schemas alone are 1,888 chars (`json.dumps`), against 55 left.

## Scope

1. Both descriptions cut to one line (`compute` 485 → 168, `verify_refs` → 160); the detail moved to
   `docs/TOOLS.md` *Behaviour by tool*.
2. The allowance cut to the measured minimum: description `+300` (was `+1,200`), surface `+2,170`
   (was `+2,535`). Reverting fully would need ≥ 2,161 chars cut from the other 24 tools; §19 kept
   the allowance instead (446).

## Acceptance

- `tests/test_tool_surface_budget.py` passes at the tightened caps; `list_tools()` reported against
  0.10.0's 23,580.

## Result

Descriptions 10,394 (cap 10,400); surface 25,796 (cap 25,805) against 0.10.0's 23,580: +9.4%
(the state check measured +11.0% before the cut). §19 (2026-11-09): the allowance stays; no trim.

## Cost ledger

Covered by 443's one review (90,836). Main loop unmeasured.

Merged in #170 as `83da5186`; released as `v0.11.0`.
