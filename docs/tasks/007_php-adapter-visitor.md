---
id: 007
slug: php-adapter-visitor
title: PHP adapter — full language coverage & server mode
phase: 1
milestone: M0
status: todo
depends_on: [006, 005]
---

## Goal
Complete the PHP adapter to the language standard and add streaming `--server` mode (§6, §7).

## Scope / Deliverables
- Nodes: `Namespace_, Class_ (abstract/final/readonly), Interface_, Trait_, Enum_ (pure/backed), anon classes, ClassMethod, Property (incl. promoted/typed/readonly), ClassConst, enum cases, Function_, closures, arrow fns, first-class callables`.
- Edges: `extends/implements`, `TraitUse`, `MethodCall/StaticCall/FuncCall`, `New_`, `Use_` (incl. group-use, function/const imports, aliases), `Include_`.
- Attributes captured raw on declarations.
- `ErrorHandler\Collecting` → bad file returns `ok:false`, stream continues.
- `--server` stdin loop matching the subprocess protocol; emits **bare** edges (targets as FQNs/names).

## Acceptance criteria
- Emits correct nodes/edges for each construct above (asserted in fixtures — task 012).
- No repo/framework names in adapter source (grep-gate clean).

## References
Plan §6, §7, §2 (standard over sample).
