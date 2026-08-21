---
id: 118
slug: module-summary-seam-gets-empty-facts
title: Onboarding — every module page says `Summary: (none)`, and the cause is the seam, not the repo (M11)
phase: 3
milestone: M11
status: todo
depends_on: [085, 090, 107, 117]
---

## Why this exists (measured, anchor monorepo, 2026-08-21)

Every one of the **500 / 500** emitted module pages carries `Summary: (none)`. That number is not new —
[117](117_llm-prose-for-map.md) opens with it. What is new is the **cause**, and 117 recorded it wrongly:

> "because `StructuralSummarizer` needs a docblock and **this codebase has none**"

**Falsified.** The anchor repo does have docblocks — `public/AddressScreenAjax.php` opens with a nine-line
one naming the caller, the delegate and the remediation ticket. The docblock never reaches the summarizer,
on any repo, for two independent reasons:

1. **The caller passes empty facts.** `code_atlas/onboarding/artifact.py:325`:

   ```python
   facts = [NodeFacts("", "", by_key[stop.file]) for stop in stops if stop.file in by_key]
   ```

   `signature` and `doc` are hardcoded `""`, so `StructuralSummarizer._first_line("")` returns `""` for
   every module of every repository. The deterministic path cannot produce a summary — not "does not
   here", *cannot*.

2. **The graph holds no docblock to pass.** `NODE_FIELDS` in `contract.py` is
   `kind · name · qualified_name · file_path · line_start · line_end · modifiers · params · is_test · extra`
   — no doc field. `read_symbol` returns a docblock only because it reads the file from disk by line range,
   never from the graph.

### Three consequences, each measured

- **The opt-in LLM path does not fix it either.** `onboarding_llm/summarizer.py` receives the same
  `NodeFacts`; its system prompt asks the model to work from "its path, signature, docblock, and structural
  role" while two of those four are empty strings. Setting `CA_ONBOARDING_SUMMARIZER` buys a sentence guessed
  from the file path — filler with confidence, which 109's C1 `is_filler` then refuses for part of the spend.
  The seam is wired such that its own implementer is starved.
- **107's isolation rule is half dead code.** `artifact.py`: `if not summary.docline and not degrees.fan_in
  and not degrees.fan_out`. The first clause is permanently true, so the rule that decides which modules get
  no page at all is edges-only in practice. It reads as a two-signal rule and behaves as a one-signal rule.
- **`(none)` misattributes the cause to the repository.** A newcomer reading 500 pages of `Summary: (none)`
  concludes this codebase is undocumented. The correct statement is that the artifact has no docblock source.

## Scope

Smallest change that makes the field real, with **no contract change** (R1.2 / YAGNI):

- Source the module's **leading docblock and its representative signature at build time by read-through** —
  the same on-disk read `read_symbol` already performs against `line_start`/`line_end`, reusing that path
  rather than adding a second one. 500 short reads, deterministic, no LLM, no network.
- Pass the real `signature` / `doc` into `NodeFacts` so both the structural default **and** the 090 implementer
  finally receive what their contracts promise.
- When a module genuinely has no docblock, render the reason, not `(none)` — the absence is a fact about that
  file and must read as one.
- Re-examine 107's isolation rule once `docline` can be non-empty, and cover its first clause with a test that
  fails if the clause becomes unreachable again.

### Rejected for now — a `doc` field in the contract

Storing docblocks as a node field would serve every tool, not just onboarding, but it costs a
`contract_version` bump, an adapter change and a conformance-suite update (R3) for a field only the
onboarding artifact needs today. Read-through carries no schema cost and no staleness question the
existing freshness work (035) has not already answered. Revisit when a second consumer needs it.

## Acceptance criteria

1. **AC1.** On the anchor repo, the share of emitted pages carrying a non-empty summary is measured and
   recorded — before (0 / 500) and after. A page count, not an adjective.
2. **AC2.** With no LLM opted in, the summary comes from the file's own docblock; identical input yields
   byte-identical output (R4.2), and no timestamp or absolute path enters the page.
3. **AC3.** A module with no docblock states that, and never renders `(none)`; the wording attributes the
   absence to the file, not to the tool.
4. **AC4.** With `CA_ONBOARDING_SUMMARIZER` set, the summarizer receives a non-empty `signature` and `doc`
   for a module that has them — asserted at the seam, so the starvation cannot return silently.
5. **AC5.** 107's isolation rule keeps both clauses meaningful, proven by a test that fails if `docline` is
   unconditionally empty again.
6. **AC6.** 109's gate still passes on the anchor, and the median page stays under `MAX_PAGE_BYTES`.
7. **AC7.** 117's "this codebase has none" premise is corrected in that ticket with the evidence above —
   a wrong recorded cause is how the defect survived three tickets.
