---
id: 207
slug: the-artifact-answers-no-question-a-newcomer-asks-first
title: "The onboarding artifact never reads a single declared project file, so it answers what the graph is and nothing a newcomer asks first — how to run it, how to test it, and which door a request comes in"
phase: 3
milestone: M12
status: done
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

---

MANGO WORKING DOC (below this line is NOT part of the raw ticket)

## Working doc (autorun 2026-09-04)

**KEY:** 207 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **reviewer:** OFF (`--no-reviewer`) · **challenger:** ON

### Phase 0 — refine

`PREMISE: 11 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 4 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 5 unresolved surfaced | 1 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

**The ticket's premise, re-run with a tree behind it.** The block in the ticket body above carries
no SHA, so it is not evidence about any tree under review (LESSONS 200-C2). Re-run here:

```
Ran at c26c48c28c42ad43eb7132833528b51853b4f396 (main, the pre-change tree — a BASELINE, which measures another tree by definition)
$ git grep -n -E "README|composer\.json|package\.json|docker-compose|Makefile" c26c48c28c42 \
    -- code_atlas/onboarding/ code_atlas/tools/generate_onboarding.py
(no matches)

Ran at 2201acf418e37dfd897e35b1cdff0f0f94809de0 (the tree under review)
$ git grep -c -E "composer\.json" HEAD -- code_atlas/onboarding/orientation.py
code_atlas/onboarding/orientation.py:3
```

**AC7 cannot be met by a tool payload without crossing the ticket's own boundary, and cannot be
recall-scored without one** — both halves discovered at review. The recipe reads the committed file;
the score is correctness and cost, not recall; and the 121-era guard that assumed otherwise was
widened. See Phase 4.

The ticket's central premise **holds** — `grep -rn "README\|composer.json\|package.json\|docker-compose\|Makefile" code_atlas/onboarding/ code_atlas/tools/generate_onboarding.py` returned nothing before this change. Scope 4's premise also holds but is **narrower than the ticket states**: the sample is not missing from the *data*, it has been in `ReachabilityBucket.sample` since 113 (`reachability.py:198`) and no renderer ever printed it. That makes Scope 4 a render change, not a computation.

**The want-decision**, answered under the operator's standing delegation: *AC6 read literally forbids AC3.*
"A repo with no declared project files produces an artifact byte-identical to today's" cannot hold
while Scope 4 adds an entry-point sample to **every** repo's `overview.md`. The two are
co-satisfiable on exactly one reading, and it is Scope 2's own wording: **the orientation section is
omitted, not emitted empty**. Taken, pinned by
`test_a_repo_with_no_declared_project_files_omits_the_section`, and disclosed.

How-decisions, each cited:
1. **The declared runtime is read by ecosystem spec, not by language name.** R1.1's guard bans every
   language name in `code_atlas/`, comments included — the first draft read `require.php` /
   `engines.node` and went red. Composer's spec makes a `require` key **without a `/`** a platform
   requirement (packages are always `vendor/name`); npm's `engines` is exactly the runtime map. The
   core now names nothing and picks up `ext-*` for free. R1.1's guard produced a better design.
2. **`docker-compose` is read by a deliberately shallow block-style scanner, and says so.** There is
   no stdlib YAML parser and R8.2 forbids a dependency. It reads the one unambiguous shape and
   reports a gap for anchors or flow style rather than guessing, because a guessed service name is
   worse than a stated absence (R5.6).
3. **The citation is anchored to a key position, not found by substring.** A bare
   `text.find(name)` cited every `pyproject.toml` script to the `name = "code-atlas"` line — a
   citation that resolves, to the wrong line. Each spelling is now `^`-anchored, with an unanchored
   `"key":` last resort so a compact one-line manifest still yields a line.
4. **A one-line agent brief is not a description.** This repo's own `CLAUDE.md` is the single line
   `@AGENTS.md`; quoting it answers nothing, so a prose excerpt must clear `MIN_EXCERPT_CHARS`, and
   only the first prose source contributes the "what it says it is" fact.

In-repo refs resolved: `reachability.py` (`sample`, `sample_truncated`), `artifact.py`
`_reachability_lines`, `config.py` `_as_repo_relative_list` / `KNOB_KEYS`, `dataset.py`,
`viewer.py`, `generate_onboarding.py`, `tests/contract/framework_denylist.txt` (no ecosystem
manifest name is on it), `tests/fixtures/php/onboarding`, R2.1/R2.2, R5.3, R6.9, tickets 113/121/186.
Ambiguous: the anchor's `CLAUDE.md`, `README.md` and `docker-compose.yml` — another checkout.

Recalled (advisory): `derived-not-listed-invariant` (R6.7), `prove-the-guard-fails` (R6.5),
`count-pin-in-blast-radius` (P5), `do-not-attest-past-the-payloads-resolution` (R5.6); area:
onboarding / artifact rendering.

### Phase 1 — analysis

`PREMISE: 11 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 4 by handle | 1 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists · Scope · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=6 R=5 G=1 AC=7`
`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`
`RULE SECTIONS: 10 applicable — 9 by change-type | 1 by recalled handle — §R1.1 (the core names no language) ✅ · §R2.1 (ecosystem standards are knowable) ✅ · §R2.2 (no repo's own names) ✅ · §R3.5 (dataset field ⇒ version bump + viewer) ✅ · §R4.1 (quote, never synthesise) ✅ · §R4.2 (deterministic order and boundaries) ✅ · §R5.3 (a consumer's broken file degrades) ✅ · §R5.8 (rank inside the truncate) ✅ · §R6.9 (assert the emitted markdown) ✅ · §R6.7 (derive the knob table) ✅`
`TRACK: backend — 0/N touched files under UI paths`
`BASELINE: green — main at c26c48c, 2825 passed`
`SCOPE: L`
`TIER: full`

Clarifications, all self-resolved:
1. *AC6 vs AC3* — resolved as above (cited Scope 2's wording).
2. *Does AC7 cross the "no new tool" line?* — resolved: **no tool is added**. The harness can only
   execute MCP tools (`scripts/tokens_to_answer.py` `run_atlas_path`), so a question answerable only
   from a written file cannot be scored at all. The existing `generate_onboarding` payload gains a
   bounded `day_one` block. Cited: the ticket's own *"121 is where that gets decided"* — AC7 is the
   decision.
3. *Is `CLAUDE.md` a repo's own name under R2.2?* — resolved: it is a member of the **agent-brief
   category**, alongside `AGENTS.md`, exactly as `composer.json` is a member of the manifest
   category; and the whole list is overridable by `project_files`. Cited: R2.1, and the ticket's own
   licensing of the category.

| ID | Type | Statement |
|---|---|---|
| G | G | The artifact answers a newcomer's first questions, from the repo's own declared files |
| R1 | R | An orientation section above the aggregates; nothing without a citation |
| R2 | R | A declared list of what counts, resolved like every other setting |
| R3 | R | Structured, uninterpreted facts only — a key is a fact, a paragraph is a quote |
| R4 | R | Name the entry points the reachability split counts (bounded, R5.8) |
| R5 | R | The section says what it could not find |
| C1 | C | R4.1 — quote and cite, never summarise; no LLM, no network |
| C2 | C | R2.2 — no repo's own names beyond documented ecosystem categories |
| C3 | C | R5.6 — an excerpt is labelled an excerpt; never attest past the payload |
| C4 | C | R5.3 — a malformed project file degrades, never aborts |
| C5 | C | R4.2 — deterministic file order and excerpt boundaries |
| C6 | C | R7.1 — five facts a newcomer needs. Not a runbook generator |
| AC1 | AC | The overview opens with the section; every line carries its path |
| AC2 | AC | A declared test command verbatim; none declared ⇒ an explicit line |
| AC3 | AC | A named, bounded entry-point sample beside the count |
| AC4 | AC | A malformed file degrades, proven by a broken-JSON fixture (observed failing) |
| AC5 | AC | No uncited sentence; a guard asserts it at the consumer |
| AC6 | AC | No declared project files ⇒ byte-identical to today's |
| AC7 | AC | The 121 harness gains a first-day question; floors stay green |

### Phase 2 — design

`HANDLES: 4 recalled | 4 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 1 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 1 input-shape-dependent AC(s) | 0 proven on a real corpus`

Handle traces (command → result):
1. `count-pin-in-blast-radius` — the suite found **five** pins, where the grep had found two:
   `DATASET_VERSION == 12`, both core-module-count guards, `len(KNOB_KEYS) == 18`, and the
   `env_name` ordering list in `test_config.py`. All five repaired. **Sighting 12.**
2. `derived-not-listed-invariant` — `docs/TOOLS.md`'s config table declares itself exhaustive and
   the ledger records it **missed by hand four times** (212's review found the fourth). Rather than
   a fifth hand-add, it is now derived from `KNOB_KEYS` by
   `test_the_documented_knob_table_lists_every_knob`, mutation-checked. **The class is discharged,
   not re-recorded.**
3. `prove-the-guard-fails` — four mutants, four caught; AC4's is observed **raising**, which is the
   literal thing R6.5 asks for.
4. `do-not-attest-past-the-payloads-resolution` — the compose reader refuses anchors and flow style
   and states that, rather than emitting a service name it cannot stand behind.

**Exclusion (1, with a checkable expiry).** The anchor figures the ticket quotes (306 web entry
points, `public/*.php` claiming 95, `Unit` at 1,688 files) are not reproducible here:
`.harness.json` `real_corpus_path` is `null`. **Expiry: the first run after `real_corpus_path`
becomes non-null.** This is the class's **fourth consecutive sighting** (206, 211, 209, 207) — see
`DISCLOSURE`; it was escalated on the third and is not re-argued here.

**Proving test:** `tests/test_orientation.py` (16 tests).

**Rejected alternative:** adding a YAML dependency to parse `docker-compose.yml` properly. R8.2
forbids a new runtime dependency for one section of one document, and the shallow reader's refusal
path is honest where a parser would only be more complete.

### Phase 3 — execute

What landed: `orientation.py` (new, the reader), the *Start here* section at the top of
`overview.md`, `CA_PROJECT_FILES`, the entry-point sample beside its count, `day_one` in the tool
payload, the dataset field + viewer line, `DATASET_VERSION` 12 → 13, the 121 question, and the
derived knob-table guard.

Verification: `scripts/gate.sh` → **GATE GREEN, 17/17, 0 skipped**. Full suite **2844 passed**
against a 2825 baseline. Benchmark: ratio **0.83** ≥ 0.63, recall **1.0**, precision **1.0**,
0 unexpected, with `onb_first_day_commands` at **1,557 tokens** — what opening the committed document actually costs — correct, and recall-exempt for the reason stated in Phase 4.

`diff ⊆` approved list: `orientation.py` (new), `artifact.py`, `dataset.py`, `viewer.py`,
`config.py`, `generate_onboarding.py`, `test_orientation.py` (new), `test_config.py`,
`test_onboarding_dataset.py`, `test_core_is_language_agnostic.py`, `test_sql_confinement.py`,
`tests/fixtures/php/onboarding/{composer.json,README.md}`, `scripts/tokens_to_answer_questions.json`,
`docs/TOOLS.md`, `docs/benchmarks/121_*.md`, this working doc, BACKLOG, TOKEN_LEDGER.

#### Acceptance criteria — close-out

| AC | Verdict | Evidence |
|---|---|---|
| AC1 | **MET** | `test_the_overview_opens_with_the_orientation_section` — asserts the section index is *before* `## Summary`, on the emitted file |
| AC2 | **MET** | `test_a_declared_test_command_is_reproduced_verbatim` (`` `test`: `phpunit --colors` — `composer.json:9` ``) and `test_a_repo_declaring_no_test_command_says_so` |
| AC3 | **MET** | `test_a_named_sample_appears_beside_the_count_that_claims_it`; the data existed since 113 and no renderer printed it |
| AC4 | **MET, observed failing first** | `test_a_malformed_manifest_degrades_to_a_stated_gap`; with the degradation removed the fixture raises `JSONDecodeError` through the build |
| AC5 | **MET** | `test_every_orientation_line_resolves_to_a_source_or_is_a_stated_gap` — every non-gap `- ` line in the emitted section must end `— \`<source>\`` |
| AC6 | **MET on the reconciled reading, now proved** | `test_the_orientation_path_changes_nothing_outside_its_own_section` excises the section and asserts the remainder is byte-identical. The literal reading forbids AC3; see Phase 0. Round 1 was right that stating the reconciliation is not proving it |
| AC7 | **MET** | `onb_first_day_commands`, ground truth hand-read from the fixture before the tools ran; a `session_path` that opens the committed `overview.md`, 1,557 tokens, correct. Recall-exempt with a stated reason — the harness cannot score recall on a native read, by design (Phase 4). Floors green |

### Phase 4 — review

`reviewer`: **OFF** (`--no-reviewer`) — no rule-book-grounded review of this diff exists.
`challenger`: **ON** — ticket-blind, on the raw ticket text and `git diff main...HEAD`.

**Round 1: CHANGES REQUESTED.** 14 met, 1 not met, 1 boundary crossed — and both blocking findings
were right, so both changed the shipped design.

**It disclosed its own independence breach before its findings**, unprompted: a repo-wide
`grep -rn "day_one"` put this working doc's and the ledger's rationale in front of it, including the
sentence defending the very scope question it had already flagged from the diff. It reported the
breach and scoped the compromise to that one finding rather than concealing it.

1. **The `day_one` payload crossed the ticket's own "not in scope: a new tool … 121 decides"
   boundary — and it named an alternative I had not found.** `scripts/tokens_to_answer.py` carries
   `read_file` as a **native session step** (`_NATIVE_TOOLS`), so a `session_path` recipe can
   generate the tree and then open the committed `overview.md` — the human-reader path the ticket
   actually ships. `day_one` is **removed**; the question now reads the file, and
   `onb_committable_map` gets its 173 tokens back (it had paid 225 for a field it never used).

   **Following that through found something better than a fix.** The rewritten question scored
   **recall 0.0** — because `_mcp_responses` excludes native steps *on purpose*: recall measures
   what the **index** answered, and a file read is not that. So the harness **structurally cannot
   recall-score a fact that lives in the committed artifact**, and the only way to have scored it
   was the payload the ticket forbade. That is 121-C1 from the other side — a measurement deferred
   may be one whose instrument cannot address its subject — and it forced widening
   `test_onboarding_questions_declare_ground_truth_for_recall`, a 121-era guard that quietly assumes
   **every** onboarding answer is index-answerable, which is the assumption 207 exists to revisit.
   Widened in the shape the file already uses next door for ratio exclusions: a stated reason in
   `expected_set_note`, never a quiet gap. Mutation-checked.

2. **AC6 was NOT MET on the literal reading, and it was right that a plain statement is not a
   proof.** The reconciliation was written down (Phase 0) but nothing asserted it. Now
   `test_the_orientation_path_changes_nothing_outside_its_own_section` excises exactly the inserted
   section and asserts the remainder is the untouched document **byte for byte** — mutation-checked
   with a line added outside the section, which goes red.

3. Non-blocking, taken anyway: `_TEST_NAMES` was an exact-match allowlist, so a target named
   `run-tests` was missed and misreported as a gap. Matching is now word-wise (`run-tests`,
   `ci:check` → found; `latest`, `contest` → not).

**Round 2 (verify-only, same live seat): LGTM.** It re-ran the AC6 guard under its own mutation
(a leaked line outside the section) and watched it fail, and it walked all 16 onboarding questions
to confirm the widened recall guard is used by exactly one — *"honest scope narrowing, not gate
erosion"*.

**One number in round 2 is wrong, and the reason is worth keeping.** It reported
`onb_committable_map` at **290 at all three SHAs**; three live harness runs measured **173 → 225 →
173**. Its 290 came from `docs/benchmarks/121`'s table, which is dated **2026-08-23** and has drifted
— 205 removed the page tree that payload listed. A reviewer took a stale documented figure as a
current measurement, so the table now carries a dated-value warning naming this exact case.

**CI went red once on `test_phase_times_cover_named_phases_and_sum_near_wall`** — a wall-clock
assertion (`WALL_TOLERANCE = 0.15`) on py3.12 while py3.13 passed, on a diff touching no build or
profiling path. Green on re-run. This is the class AGENTS.md already predicts. **Not "fixed" by
loosening the tolerance**, which would be editing a gate to fit a run; surfaced to the operator
instead.

### Phase 5 — finalise

`CLAIMS: 2 claim(s) from 1 lesson entr(ies) | T1=0 T2=2 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 4 recurring | 1 superseded (0 retired) | 1 promotion candidate(s)`
`FALSIFY: 4 candidate(s) checked | 2 still-true (proceed) | 2 falsified (BLOCKED) | 0 not cheaply checkable`
`RECURRING-T2: 4 type-2 claim(s) with seen ≥ 2 | 4 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 1 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`
`LEDGER TOTAL: unmeasured (host surfaces no usage block) · top cost driver: main-loop execute`

`FALSIFY` detail: the *"nothing under onboarding mentions a project file"* premise is **still true**;
the *"which door a request comes in — never names one"* premise is **still true**; but *"list a
bounded sample **of them**"* implies the sample must be **computed** — **falsified**: 113 already
computes it and stores it, so what was missing was three lines in a renderer, not a feature.
