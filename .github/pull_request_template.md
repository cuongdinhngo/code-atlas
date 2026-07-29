## Summary
<!-- What this PR does and why, in 1-3 sentences. Link the task: docs/tasks/NNN_slug.md -->

## Changes
<!-- Bullet the smallest change list; each item should trace to the task's scope. -->
-

## Testing
<!-- The proving test: what fails before, passes after. Command used (e.g. `pytest ...`). -->
-

## Pre-PR self-check (docs/ENGINEERING_RULES.md)
- [ ] No language branch in the core (`code_atlas/` has no `if language == …`) — R1.1
- [ ] Adapters name no repo/framework; they encode the language standard only — R2
- [ ] Contract changes bump `contract_version` + update conformance tests — R3
- [ ] There is a test, and it is the smallest change that ships value
- [ ] Comments are ≤ 3 lines each
- [ ] Related docs updated (PLAN / BACKLOG + task frontmatter / CONVENTION / ENGINEERING_RULES / README)
- [ ] No `Co-Authored-By` / AI-attribution trailer on commits

## Notes
<!-- Anything reviewers should know: trade-offs, follow-ups, deferred items. -->
