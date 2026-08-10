---
id: 075
slug: read-symbol-confident-zero-on-unnormalised-qname
title: '`read_symbol` answers `found: false` with `reason: "ok"` for a class the index holds — one leading backslash apart'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [065, 070, 014]
---

## Goal
`read_symbol` looks a qname up verbatim. The index stores namespaced PHP qnames with a **leading
backslash**; an agent that writes the same name without it gets
`{"found": false, "stale": false, "source": "", "reason": "ok"}` for a class that exists. No
`try_instead`, no hint that a normalisation exists, and `reason: "ok"` — the vocabulary's strongest
"this answer is fine". This is the confident zero the project has spent three field rounds hunting,
and it is reachable by a one-character typo rather than by a modelling gap.

## Evidence (field retro round 4, 2026-08-10, contract v5 / schema 4, post-reconnect build)
- In the work — not a probe — the evaluator asked for a base class as `Ns\Sub\Enum` (no leading `\`)
  and received verbatim:
  ```json
  {"indexed":true,"qname":"Ns\\Sub\\Enum","found":false,"stale":false,
   "source":"","index_root":"<REPO>","reason":"ok"}
  ```
  The class exists at `…/Enum.php:17`, with `__construct` at 26–30 and `get()` at 94–97. The index
  holds it as `\Ns\Sub\Enum`, **with** the backslash — `file_outline` on the same path returned all
  10 symbols and their exact lines, which is how the false negative was caught.
- **What believing it would have cost.** The evaluator was reviewing a dispatched agent's PR that
  added `extends Enum` and justified it by that base class supplying `__construct` and `get()`. The
  next action on `found: false` was to report that the agent had invented a base class — a **false
  CRITICAL on a correct PR**, in a repo whose `CLAUDE.md` instructs agents to trust the graph over
  `grep`. One extra `file_outline` call was the entire margin.
- Round 4's §9 ("if you could change exactly one thing") is this defect, and the two most valuable
  findings in that retro were both found **outside** the fix-verification section — this is one of
  them.
- Counted context: 1 wrong of 8 hand-verified results that session; the only *wrong* one, and the
  only one that arose inside real work rather than a probe.

## Why `reason: "ok"` is the defect, not the missing normalisation
Normalisation is the fix an agent cannot perform for itself; honesty is the fix that keeps the tool
trustworthy even when the lookup legitimately misses. 065 gave the `find_*` family a usable three-way
distinction (`no_such_symbol` / `index_stale` / `ok` + `try_instead`), and round 4 confirmed it works
— including following `try_instead: "file_outline"` to a brand-new symbol. `read_symbol` was never
brought into that vocabulary: it has a `found` boolean and a `reason` that is always `ok`.

## Scope / Deliverables
- **Normalise the subject qname before lookup.** A leading `\` is optional, everywhere a qname is
  accepted, for every tool that takes one — not only `read_symbol`. State the normalisation in one
  place; do not re-derive it per tool.
- **Forbid `reason: "ok"` on a not-found answer.** `found: false` must carry a reason that says
  *which* kind of nothing this is. Pick and pin the vocabulary: at minimum `no_such_symbol`; add a
  distinct value when the miss is explained by the *question's* form rather than the index's contents.
- **Name the route out.** When the lookup misses but a candidate exists under normalisation or a
  suffix match, attach `try_instead: "search_symbol"` (or the tool that would find it) — 065's
  mechanism, reused rather than reinvented.
- **Decide and record the sibling surface.** `read_symbol`, `file_outline`'s symbol arguments,
  `find_*` subjects, `impact`, `explain_path` — each gets an explicit verdict on whether it accepts
  an unnormalised qname today and what it will do after this change.
- **This is the same class of defect as [076](076_bare-name-subject-reads-as-absence.md)** (a bare,
  unqualified subject answering `no_such_symbol`). Design them together; ship one reason-vocabulary
  change if that is the smaller diff, and say so in the design.

## Constraints
- R3 — a new `reason` value is contract vocabulary: bump `contract_version` and extend the
  conformance tests, or reuse an existing value and justify it.
- R4 — normalisation must be deterministic and total: the same input always resolves to the same
  stored form, and a qname that is already normalised is byte-identical to today.
- 061 — attach `try_instead` only when it names a real route; no unconditional field.
- Do not paper over a genuine absence: a symbol that truly is not indexed must still be reported
  absent, with the reason that says so.

## Acceptance criteria
- `read_symbol("Ns\Sub\Enum")` and `read_symbol("\Ns\Sub\Enum")` return the **same** answer for a
  class stored with the backslash; a test pins both forms.
- No payload in the tool surface can carry `found: false` (or an empty result) together with
  `reason: "ok"` — proven by a test that asserts the combination is unreachable.
- A miss that normalisation or suffix-matching could explain carries a `try_instead` naming a tool
  that then finds the symbol, and the test follows that route to a hit.
- Every tool accepting a qname has a recorded verdict, and the ones that normalise are covered.

## References
Field retro round 4 §1 call 4, §3 row 1, §4 row 1, §9, §A.1 (`IMPROVED, not fixed` — the `find_*`
family is honest, `read_symbol` is not). Related:
[065](065_empty-answer-cannot-explain-itself.md) (the reason/`try_instead` mechanism this extends),
[070](070_ambiguous-qname-no-scoping.md) (the other qname-shape ticket),
[076](076_bare-name-subject-reads-as-absence.md) (same class, subject side),
[014](014_search-read-outline.md) (`read_symbol`), [033](033_nav-reason-codes.md) (empty ≠ unknown).
