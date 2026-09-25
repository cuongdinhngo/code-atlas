---
id: 337
slug: the-elision-hint-names-the-default-not-the-cap-that-fired
title: "read_symbol with max_lines says 'body elided above 600 lines' for a 62-line method — the hint names the default threshold, not the cap that elided the body"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [288]
---

## Why this exists (field retro, 2026-09-25)

`read_symbol` with `max_lines=40` on a 62-line method returned the signature and the hint
*"body elided above 600 lines"*. The reader is told a threshold that did not fire.

`_body_elided_hint` (`read_symbol.py:59-64`) always prints `BODY_LINE_THRESHOLD`. The cap that
decided is `_effective_body_cap` (`read_symbol.py:315-321`), which returns `max_lines` when given.
Probed on `main` (`927aeb9`): `max_lines=3` on a 7-line method → the same 600-line hint.

## Goal

The hint names the cap that elided the body.

## Scope / Deliverables

1. `_body_elided_hint` takes the effective cap and says which one it was (`max_lines=40` or the
   default).

## Constraints

- **061 / R6.7** — the default-cap payload is byte-identical; the threshold stays one site.

## Acceptance criteria

- **AC1** `max_lines=3` on a 7-line body → the hint names 3 and `max_lines`; red on today's code.
- **AC2** A 700-line body with no `max_lines` → today's hint, byte-identical.

## References
`code_atlas/tools/read_symbol.py:59-64,315-321,362-384`; ticket 288.
