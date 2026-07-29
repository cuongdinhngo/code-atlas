---
id: 006
slug: php-adapter-spike
title: PHP adapter spike (M0)
phase: 1
milestone: M0
status: todo
depends_on: [002]
---

## Goal
Prove nikic/php-parser emits valid contract JSON for real PHP (§6, §7).

## Scope / Deliverables
- `adapters/php/`: `composer.json` (nikic/php-parser ^5), `index.php` (`--file` mode), `src/Visitor.php`.
- Parse with `createForNewestSupportedVersion()` (8.5) + `NameResolver` for FQNs.
- Emit contract nodes/edges for at least: a namespaced file **and** a global/underscore (PSR-0) file.

## Acceptance criteria
- `php index.php --file <namespaced>.php` and `<global-underscore>.php` each produce schema-valid JSON.
- FQNs resolved (`\Ns\Class::method`); global/underscore names handled as first-class.

## References
Plan §6, §7, §15 (M0).
