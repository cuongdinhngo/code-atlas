---
id: 156
slug: r12-registry-verdict-now-adapter-2-exists
title: R1.2's condition is met — adapter #2 exists, so the registry verdict has to be written down either way
phase: 2
milestone: M7
status: todo
depends_on: [019]
---

## Why this exists

R1.2 defers every plugin registry, base class, factory and DI container *"until adapter #2 (TS/JS)
exists and proves the shape"*. As of [019](019_typescript-adapter.md) it exists. The rule's condition
is therefore satisfied, and the answer — whichever way it goes — is now owed in writing: leaving it
implicit is how "YAGNI" quietly becomes "nobody looked".

The expected answer is **no registry**, and the evidence is already in the tree: `indexer._announce`
(`indexer.py:576`) loops `config.adapter_cmds`, and the extension→adapter map is built from what each
adapter announces, so a second language cost **zero** new abstraction — the empty core diff on 019's
PR is the proof. But "expected" is not "recorded", and the reverse case deserves a fair read too: 019
did add a per-adapter registry on the *test* side (`tests/contract/adapter_registry.py`, task 147),
which is worth naming as the one place a table earned its keep.

## Scope / Deliverables

- A written verdict in PLAN §19 (the decision log): registry or no registry, with the evidence, and
  what would reverse it.
- R1.2's own text updated to record that its condition has been met and what the answer was, so the
  next reader is not sent to re-derive it.
- If the answer is *no registry*: say explicitly which mechanisms already do the job
  (`config.adapter_cmds`, the announced-extension map) so a future adapter author does not invent one.
- If the answer is *a registry*: the minimal one, and nothing more — but that is a change to the core
  and would need its own ticket, not this one.

## Acceptance criteria

1. PLAN §19 carries the verdict with a date and the evidence cited by path.
2. R1.2 in `docs/ENGINEERING_RULES.md` states that adapter #2 landed and what the answer was.
3. No core code changes in this ticket. It is a decision record; a decision to *build* something is a
   separate ticket (which is the honest outcome either way).

## Out of scope

- Adapters #3–#4. Still deferred (PLAN §19) and not evidence for this question.

## References

ENGINEERING_RULES R1.2, R1.3; `code_atlas/indexer.py:576`; `tests/contract/adapter_registry.py`;
PLAN §19; tasks 019, 147.
