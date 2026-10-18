---
id: 404
slug: typed-property-bare-name-search
title: "`search_symbol` for a PHP property's bare name returns only near-misses"
phase: 2
milestone: Retrieval
status: todo
depends_on: []
---

## Why this exists

From the anchor project's Round-3 feedback: `search_symbol "isInRespite"` for `public bool $isInRespite` returned
substring near-misses, and `git grep` found it. On `main` the PHP adapter stores the name as `$isInRespite`
(`Visitor.php:496`), so a bare query is neither an exact match nor a prefix, and `$` is not a separator in the
suffix check (`store.py:470-505`).

## Scope

1. An exact search for `name` matches a property stored as `$name`, ranked as an exact hit. The adapter's stored
   name is unchanged (R3).

## Acceptance criteria

- **AC1:** `search_symbol "isInRespite"` ranks `C::$isInRespite` first, as an exact match.
- **AC2:** `search_symbol "$isInRespite"` is unchanged.
