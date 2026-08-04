---
id: 041
slug: legacy-framework-hardening
title: Legacy/framework hardening — encoding, .blade.php, extra extensions
phase: 1.5
milestone: Robustness
status: todo
depends_on: [009]
---

## Goal
Stop silent losses on real-world PHP trees. Three concrete leaks: non-UTF8 legacy files soft-fail and
vanish from the graph with no signal; `.blade.php` views match the `.php` suffix and get sent to the
adapter as symbol-less HTML; and non-`.php` sources (Drupal `.module`/`.inc`, `.phtml` views) index
as nothing. None is an architecture limit — they are robustness gaps that make coverage look complete
when it isn't (§19 agent-first pivot).

## Scope / Deliverables
- **Encoding hardening:** a file that isn't valid UTF-8 is decoded via a defined fallback or counted
  in `parse_failures` — never silently dropped with `parsed_ok=0` and no signal.
- **Blade ignore rule:** exclude `.blade.php` so those files aren't routed to the PHP adapter
  (they currently match via last-segment `.php` suffix — `code_atlas/indexer.py:161`).
- **Extra extensions:** let the PHP adapter announce additional extensions (`.phtml`, `.module`,
  `.inc`) so they index; extension routing already flows from the adapter handshake
  (`code_atlas/indexer.py:247`), so this is an adapter-announce change, not a core change.

## Constraints
- The extension set stays **configurable via the adapter handshake**, never hardcoded in the core
  (R1.1); the core adds no language branches.
- Any file that cannot be decoded/parsed must surface in `parse_failures` (visible via task 028's
  `edge_health`), never a silent absence.
- Blade exclusion is an ignore rule, consistent with the existing built-in ignore patterns
  (`code_atlas/ignore.py:17-24`).

## Acceptance criteria
- A non-UTF8 fixture is either indexed or counted in `parse_failures` — never silently absent
  (asserted).
- `.blade.php` files are ignored (not sent to the adapter), proven on a fixture tree.
- A `.phtml`/`.module` fixture indexes when the adapter announces that extension; unchanged when it
  doesn't.

## References
`code_atlas/indexer.py:161` (suffix match), `:247` (extension_index from handshake);
`code_atlas/ignore.py:17-24` (built-in ignores); `adapters/php/index.php:27` (`extensions => ['.php']`);
task 028 (`parse_failures` / `edge_health`). PLAN §1, §19. Feedback origin:
[`FEEDBACK.md`](../FEEDBACK.md) rounds 1 & 2 ("configurable extensions + encoding hardening;
non-UTF8 files vanish silently; Blade matches .php").
