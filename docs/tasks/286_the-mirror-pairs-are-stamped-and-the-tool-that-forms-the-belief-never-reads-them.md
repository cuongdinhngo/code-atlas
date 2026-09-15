---
id: 286
slug: the-mirror-pairs-are-stamped-and-the-tool-that-forms-the-belief-never-reads-them
title: '277 stamps the mirrored subtree pairs and only `search_symbol` reads them, so `read_symbol` returns a perfect body for a port that no request reaches and says nothing about the twin that serves it — the caveat naming that exact limit is printed on `find_callers`, which is not where an agent forms the belief "this is the code that runs"'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [277, 282, 276]
---

## Why this exists (field retro — the anchor repo, round 24 §4, 2026-09-15)

A ticket named a controller action by qname. `read_symbol` on exactly that qname returned a perfect,
current body whose emitted payload lacked a key the front end reads — so the session concluded the
feature was broken, wrote that into its notes, and nearly shipped a fix to working code. The live
request is served by the **mirror twin** under the read-only tree; the ported symbol is not reachable.
Live measurement overturned it; the graph did not.

The tool answered correctly. The retro's diagnosis is where the payload is misplaced:

> *"That caveat is exactly right and it is printed on the **wrong tool**. It appears on `find_callers`,
> where I was already thinking about reachability. It does **not** appear on `read_symbol`, which is
> where an agent forms the belief 'this is the code that runs'."*

`read_symbol` today has exactly one ambiguity signal, and it is keyed on the **same qname** resolving
to several definitions (`subject_ambiguous` + `ambiguous_definitions`, `read_symbol.py:79-85`). Two
rounds rate that refusal load-bearing and it stays. A mirror twin is a *different* qname in a
different subtree, so nothing fires — the honest refusal and the silent wrong answer are the same tool
one namespace apart.

The ingredient already exists and is already stamped. 277 derives the mirrored subtree pairs at build
time and 282 restricted a counterpart to files the index actually holds; `mirror_search.py` is imported
by `search_symbol`, `indexer` and `store` — and by nothing else. So the fact that would have stopped
this is computed, deterministic, honest about divergence, and addressable from one tool. That is 278's
shape exactly, and 278 is the ask the field ranked first the round before.

## Scope / Deliverables

- **A found symbol whose file sits on one side of a stamped mirror pair says so**, naming the indexed
  counterpart — reusing 282's rule that a counterpart is named only when it is in the index, so a
  genuinely diverged file gets the honest negative rather than a synthesized path.
- **The field must not claim dispatch.** It says a twin exists and that this tool cannot say which one
  a request reaches; it never asserts which is live. The existing `caveat_limits` wording is the
  precedent — a boundary, not a verdict.
- **Decide the scope of the signal once.** Whether it belongs on every mirrored hit or only where the
  kind makes dispatch plausible is a 061 judgement to argue in design, not to assume here.

## Constraints

- R1.1 / R2: mirrored-tree pairs come from the stamped derivation, never from a path convention, a
  framework name or a repo's directory names.
- 061: a repo with no stamped pairs stays byte-identical — this must cost nothing on a single-tree repo.
- R5.6: the counterpart is an indexed file (282), never a string the pair rule can spell.
- Do not weaken `subject_ambiguous`: two rounds call the refusal load-bearing and it is unchanged here.
- R4.2: same index, same decision.

## Acceptance criteria

- A `read_symbol` hit inside a stamped mirror pair whose counterpart is indexed names it.
- The same hit whose counterpart is **not** indexed gets the honest negative, not a synthesized path.
- A repo with no stamped pairs produces byte-identical payloads to today.
- No field asserts which side a request reaches.
- 277's ordering and 282's counterpart tests still pass.

## References
`code_atlas/mirror_search.py:110,119`, `code_atlas/tools/read_symbol.py:79-85`,
`code_atlas/tools/search_symbol.py:327-329`,
[277](277_page-one-ranks-the-tree-that-cannot-run.md),
[282](282_a-mirror-hit-names-a-counterpart-that-is-not-in-the-index.md),
[278](278_the-writer-set-is-computed-for-one-check-and-addressable-from-nothing.md).
Origin: field retro round 24 §4, 2026-09-15 — "the most useful thing in this retro".
