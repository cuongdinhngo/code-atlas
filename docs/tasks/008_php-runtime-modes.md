---
id: 008
slug: php-runtime-modes
title: PHP runtime invocation (host CLI / Docker)
phase: 1
milestone: M1
status: todo
depends_on: [005, 007]
---

## Goal
Run the PHP adapter whether or not PHP is on the host PATH (§9).

## Scope / Deliverables
- `CA_PHP_CMD` wiring: (A) host PHP CLI (default), (B) `docker compose exec -T php php`.
- Path mapping for Docker (`CA_HOST_ROOT`/`CA_CONTAINER_ROOT`); store repo-relative paths regardless.
- Document the tokenizer-only requirement (no app extensions needed for indexing).

## Acceptance criteria
- Same fixture parses identically under host mode and Docker mode (repo-relative paths match).
- Clear error if `CA_PHP_CMD` is unset/invalid.

## References
Plan §9.
