---
id: 029
slug: php-receiver-resolution
title: PHP adapter — resolve $this / self / static / parent call receivers
phase: 1
milestone: M2
status: todo
depends_on: [011, 025]
---

## Goal
Move the large, knowable class of instance/scope calls out of `HEURISTIC` into `RESOLVED` by naming
the receiver's type when one file already determines it — `$this->`, `self::`, `static::`, `parent::`
— so `find_callers` on those edges reports fact, not a name-match guess (§8.2). This is a PHP-standard
language fact (the enclosing class is lexically known), not a anchor-repo-specific rule (R2).

## Scope / Deliverables
- In the PHP adapter's visitor, when a method/static call's receiver is lexically bound to the
  enclosing class, emit `CALLS` with `target_raw = <EnclosingClassFQN>::<method>` at the **default**
  (RESOLVED-eligible) tier instead of the current unconditional `HEURISTIC`:
  - `$this->m()` / `$this?->m()` → `EnclosingClass::m` (only inside a class scope).
  - `self::m()` / `static::m()` → `EnclosingClass::m`.
  - `parent::m()` → resolve against the parent class FQN (from the `extends` clause) when the adapter
    knows it in-file; otherwise leave as today.
- The **core resolver is unchanged**: it already upgrades a unique FQN match to RESOLVED and honours
  inheritance via cross-file qname lookup, so the whole win is an adapter-side `target_raw` rewrite.
- Arbitrary `$x->m()` (receiver not lexically the enclosing class) stays `HEURISTIC`; `$x->$m()`
  stays `DYNAMIC`. No type inference of properties/params in this task (that is a separate follow-up).

## Constraints
- Only rewrite when the enclosing class is unambiguous at the call site — a call in a free function,
  closure without `$this` binding, or trait used by unknown classes must NOT fabricate a receiver.
  A trait's `$this->m()` resolves within the trait's own members; cross-class trait resolution is the
  core resolver's job, not a guess here.
- Never claim RESOLVED for a receiver one file cannot know (R5.2) — the tier stays the resolver's
  weaker-of choice; the adapter only stops *pre-downgrading* to HEURISTIC.
- Zero language branches leak into the core (R1.1); this is entirely inside `adapters/php/`.
- No contract vocabulary change — `CALLS` and existing tiers only, so no `contract_version` bump.

## Acceptance criteria
- Conformance fixtures: `$this->`, `self::`, `static::`, `parent::` calls emit
  `<ClassFQN>::method` and, after resolve, link `RESOLVED` to the correct declaration (including a
  method inherited from a parent class in another file) — asserted on the resolved `edges` rows.
- A negative fixture proves `$x->m()` and `$x->$m()` are unchanged (HEURISTIC / DYNAMIC), and a
  `$this->m()` inside a trait does not fabricate a false receiver.
- Before/after on a fixture repo shows a measurable drop in HEURISTIC `CALLS` with no RESOLVED edge
  pointing at the wrong declaration (pairs with task 028's health counts).
- Full contract-conformance + resolver + PHP coverage suites pass.

## References
Plan §8.2 (instance CALLS / receiver, tier rules), §6 (PHP standard, not a repo). `R5.2`, `R1.1`, `R2`.
`adapters/php/src/Visitor.php` (`enterInstanceCall` line ~342, `enterNamedCall`); `code_atlas/resolver.py`.
Feedback origin: external review Top-3 #1 ("resolve the receiver types you already know"). Highest
single-change leverage; prerequisite for trustworthy reachability (task 031).
