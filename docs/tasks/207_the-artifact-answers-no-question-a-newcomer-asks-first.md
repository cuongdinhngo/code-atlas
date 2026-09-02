---
id: 207
slug: the-artifact-answers-no-question-a-newcomer-asks-first
title: "The onboarding artifact never reads a single declared project file, so it answers what the graph is and nothing a newcomer asks first — how to run it, how to test it, and which door a request comes in"
phase: 3
milestone: M12
status: todo
depends_on: [112, 117, 121, 206]
---

## Why this exists (measured on the anchor monorepo, 2026-09-02)

Nothing under `code_atlas/onboarding/` or `code_atlas/tools/generate_onboarding.py` mentions
`README`, `composer.json`, `package.json`, `docker-compose` or `Makefile`:

```
$ grep -rn "README\|composer.json\|package.json\|docker-compose\|Makefile" \
    code_atlas/onboarding/ code_atlas/tools/generate_onboarding.py
(no matches)
```

The artifact is derived **entirely** from the symbol graph. That is a deliberate and correct
property of the core — but it means the four files a human opens on day one are the four files
onboarding has never looked at.

### The questions the artifact does not answer

`overview.md`, `tour.md` and `flows.md` were read end to end. None of them contains:

- **how to run the system** — no command, no service, no port;
- **how to run its tests** — no test command, though `Unit` is the fourth-largest business module
  at 1,688 files and the artifact ranks `RegisterNotesControllerTest.php` at `fan_in 2519`;
- **what the system is for** — the word "aged care" appears nowhere; the anchor is a healthcare
  management system being merged across two countries, and the artifact describes it as 12 layers
  and 24,535 modules;
- **which door a request comes in** — the reachability split says *"Web entry points: 306"* and
  cites the glob `public/*.php` that claimed 95 of them, but never names one.

Meanwhile the anchor repo *has* every one of those answers, written down, in files the walk already
passes over: `README.md` holds Docker and SQL setup, `CLAUDE.md` holds the architecture patterns and
the region-branching idiom, `docker-compose.yml` names the services, `composer.json` names the test
runner.

### Why this is a gap and not a scope boundary

[121](121_onboarding-question-class-never-measured.md) narrowed the onboarding question class to
what the graph can answer, and that narrowing was right at the time — an unmeasured claim was worse
than a missing one. But the narrowing has hardened into an assumption that these questions are
**out of scope for the artifact**, when what they are is **out of scope for the graph**. Those are
different statements, and the artifact is where they diverge: it is the one surface whose audience
is a person rather than an agent, and it is the surface where a missing runbook is felt.

The distinction that keeps **R4.1** intact is *quote versus synthesise*. Reading a declared file and
reproducing a fenced excerpt with its path is I/O over the repo — the same thing the indexer already
does. Deciding what a project is *for* from prose is inference, belongs to the Phase-3 LLM seam
([090](090_llm-summarizer-impl.md), [117](117_llm-prose-for-map.md)), and is not asked for here.

## Scope

1. **An orientation section in `overview.md`, above the aggregates**, built only from declared
   project files: the excerpt, and the `path:line` it came from. Nothing without a citation.
2. **A declared list of what counts**, resolved like every other setting, defaulting to the
   ecosystem manifests **R2.1** already licenses the project to know (`composer.json`,
   `package.json`, `pyproject.toml`, `Makefile`, `docker-compose.y*ml`) plus the repo's root
   `README*` and agent-brief files. A repo that declares none gets the section omitted, not empty.
3. **Extract only structured, uninterpreted facts**: script/target names and their command lines,
   service names and published ports, the declared PHP/Node/Python version. A `scripts` key is a
   fact; a paragraph of README prose is a quote; neither is a summary.
4. **Name the entry points the reachability split counts.** The split already says 95 modules were
   claimed by `public/*.php`; list a bounded, ranked sample of them (**R5.8**) so the reader can
   open one.
5. **The section says what it could not find.** A repo with no declared test command gets a line
   saying no declared test command was found — never silence, and never a guess
   ([186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md)'s rule applied to the artifact).

### Explicitly not in scope

- **Prose about the domain.** What the system is *for* is the LLM seam's job; this ticket ships the
  citations that seam would need and stops there.
- **Running anything.** No command in the artifact is executed or validated. A stale script in
  `composer.json` is reproduced faithfully and attributed, exactly as written.
- **A new tool.** This is content in the committed artifact for a human reader. Whether an agent
  should be able to *query* it is a separate measurement, and [121](121_onboarding-question-class-never-measured.md)
  is where that gets decided.
- **Which tree is the reader's.** [206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md).

## Constraints

- **R4.1** — no LLM, no network in the core. Quote and cite; never summarise.
- **R2.2** — no repo's directory or file names hard-coded beyond documented ecosystem manifests,
  which **R2.1** already treats as knowable standards. The anchor's `CLAUDE.md` is reached because
  agent-brief files are a declared category, not because the string is in the source.
- **R5.6** — never attest past what the payload can distinguish. An excerpt is labelled an excerpt.
- **R5.3** — a malformed `composer.json` in a consumer repo must not fail the artifact build; it
  degrades to the "could not read" line (**R5.1**'s posture, applied to project files).
- **R4.2** — identical input, identical output: file order and excerpt boundaries are deterministic.
- **R7.1** — the smallest useful thing. Five facts a newcomer needs, cited. Not a runbook generator.

## Acceptance criteria

1. `overview.md` opens with an orientation section, and every line in it carries the path it came
   from.
2. A repo declaring a test command gets that command reproduced verbatim; a repo declaring none gets
   an explicit line saying so.
3. A named, bounded sample of web entry points appears beside the count that claims them.
4. A malformed or unreadable project file degrades to a stated gap and never aborts the build —
   proven by a fixture with deliberately broken JSON (**R6.5**: observed failing first).
5. No sentence in the section is generated from anything but a quoted or key-extracted value; a
   guard asserts at the consumer (**R6.9**) that every orientation line resolves to a source path.
6. A repo with no declared project files produces an artifact byte-identical to today's.
7. The 121 harness gains at least one first-day question of the shape *"how do I run the tests?"*,
   with ground truth hand-read before the run, and the gate stays green at existing floors.

## References

[112](112_onboarding-dataset-contract.md) (where an orientation block would live in the dataset),
[117](117_llm-prose-for-map.md) and [090](090_llm-summarizer-impl.md) (the seam that owns
interpretation, and why this ticket stops short of it),
[121](121_onboarding-question-class-never-measured.md) (the narrowing this ticket revisits, and the
harness that must accept it), [186](186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) (an
absence is stated, never silent), [206](206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md)
(the other half of a newcomer's first question).
