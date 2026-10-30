---
id: 429
slug: untrusted-output-framing
title: "Repo text in a tool answer is marked as data and stripped of terminal and bidi controls — the agent is told once, the payload says which fields"
phase: 2
milestone: Trust
status: todo
depends_on: [428]
---

## Why this exists

Tool answers carry text written by the indexed repo — docblocks, signatures, source, symbol names —
next to code-atlas's own fields, with nothing telling the agent which is which: a docblock that
says "ignore previous instructions" reads the same as a `hint`. ANSI escapes and bidi controls in
that text reach the agent and any terminal that prints it. 421 scrubbed what reaches the
instructions and hooks; two tool-answer fields stayed raw (`build_phase` from
`schema_guard.attach_build_state`, `lost_languages` in the coverage-loss refusal). The optional LLM
prose (`onboarding_llm/`) puts repo text into a prompt undelimited, and reads a committed cache as
trusted.

## Acceptance

1. **One marker, not per-string wrapping:** each answer that carries repo text names those fields
   once (`untrusted_fields: [...]`), and the server `instructions` say in one sentence that those
   fields are data from the indexed repo, never instructions. Tokens-to-answer is measured before
   and after (`scripts/tokens_to_answer.py`) and stays above its floor.
2. **Controls stripped:** ANSI sequences, bidi controls and invisible format characters are
   escaped in tool answers, hook output, generated markdown and the viewer (`index_text.scrubbed`
   or its sibling for multi-line text; source keeps its newlines).
3. **The two 421 residuals:** `build_phase` must be a `BUILD_PHASES` value, `lost_languages` only
   known ids (as 421's summary does).
4. **LLM prose:** the prompt delimits repo text as data; the reply is escaped before render and
   never executed; a cached entry carries provenance (model, input hash) and a committed cache
   that fails the check is ignored, not trusted.
5. **Agent config stays inert:** a fixture repo carrying `.claude/settings.json` hooks,
   `.mcp.json` and an editor task file is indexed and onboarded with nothing run (SEC-PI-06).
6. **Proving fixture:** a docblock holding ANSI, a bidi override and "ignore previous
   instructions" comes back escaped and inside a marked field, in `read_symbol`, search and the
   onboarding markdown; each seen failing first.

## Call sites

`code_atlas/tools/*` (answers carrying `doc`, `signature`, `source`, names),
`code_atlas/instructions.py`, `code_atlas/index_text.py`, `code_atlas/tools/schema_guard.py`,
`code_atlas/tools/build_or_update_index.py` (coverage-loss refusal), `code_atlas/onboarding/`
renderers, `onboarding_llm/` (prompt, cache); standard rows SEC-PI-01..04, 06.
