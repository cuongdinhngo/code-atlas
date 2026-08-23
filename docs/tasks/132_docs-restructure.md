---
id: 132
slug: docs-restructure
title: The doc set costs an agent ~66k tokens before it knows what binds it — give every standing doc a boundary
phase: 1.5b
milestone: Docs
status: done
depends_on: []
---

## Why this exists (measured on this tree, 2026-08-23, commit `1f85f9a`)

The two pillars have been decided and are not written down anywhere. Placing them is the occasion;
the reason to do it now is that the doc set has no stated boundaries, so **five documents each hold a
piece of "what this project is" and none of them is marked authoritative**, and the chain an agent is
told to read before touching anything costs **~66,500 tokens across 7 files**.

This is Pillar 1's own metric turned on the repo's prose. Nothing here changes behaviour: no code, no
tests beyond the three that parse these files, no rule invented.

---

## 1. Measurement

### 1.1 The set — 28 markdown files outside `docs/tasks/` (129 task files excluded)

| Doc | Lines | Last commit | Inbound (standing / tasks) | Outbound md |
|---|---|---|---|---|
| `README.md` | 611 | 08-23 | 3 / 0 | 27 |
| `AGENTS.md` | 115 | 08-22 | 3 / 0 | 6 |
| `CLAUDE.md` | 1 | 08-01 | 0 / 0 | 1 (`@AGENTS.md`) |
| `docs/PLAN.md` | 1082 | 08-23 | 8 / 1 | 31 |
| `docs/BACKLOG.md` | 612 | 08-23 | 9 / 7 | 142 |
| `docs/LESSONS.md` | 1767 | 08-23 | 4 / 4 | 0 |
| `docs/CONVENTION.md` | 228 | 08-22 | 5 / 0 | 4 |
| `docs/ENGINEERING_RULES.md` | 208 | 08-22 | 5 / 1 | 5 |
| `docs/AGENT_BRIEF.md` | 98 | 08-17 | 2 / 0 | 5 |
| `docs/FEEDBACK.md` | 247 | **08-06** | 4 / 9 | 2 |
| `docs/SKILL_GAP_CANDIDATES.md` | 149 | 08-17 | 1 / 0 | 1 |
| `docs/phase3-onboarding/PHASE3_ONBOARDING.md` | 201 | 08-23 | 2 / 10 | 10 |
| `docs/phase3-onboarding/ONBOARDING_MOCKUP.md` | 228 | 08-21 | 4 / 0 | 10 |
| `docs/phase3-onboarding/mockup/README.md` | 33 | 08-20 | 0* / 0 | 1 |
| `docs/benchmarks/121_onboarding-question-class.md` | 107 | 08-23 | 5 / 0 | 5 |
| `docs/benchmarks/074_mechanism-question.md` | 100 | 08-10 | **0 / 1** | 1 |
| `docs/runbooks/onboarding-a-repo.md` | 349 | 08-22 | 2 / 3 | 4 |
| `docs/runbooks/tokens-to-answer.md` | 336 | 08-23 | 4 / 3 | 4 |
| `docs/runbooks/parallel-agents.md` | 130 | 08-13 | 2 / 2 | 5 |
| `docs/runbooks/cross-repo-validation.md` | 88 | 08-02 | 4 / 0 | 2 |
| `docs/runbooks/field-retro.md` | 77 | 08-22 | 2 / 0 | 1 |
| `docs/runbooks/tool-recognition-probe.md` | 85 | 08-18 | 3 / 0 | 1 |
| `docs/runbooks/scale-sample.md` | 39 | 08-02 | 1 / 0 | 1 |
| `adapters/php/README.md` | 126 | 08-06 | 1 / 0 | 2 |
| `onboarding_llm/README.md` | 72 | 08-21 | 1 / 0 | 0 |
| `contrib/claude-code/README.md` | 41 | 08-04 | 0* / 0 | 1 |
| `contrib/git/README.md` | 45 | 08-08 | 0* / 0 | 1 |
| `.github/pull_request_template.md` | 22 | 07-29 | 0† / 0 | 0 |

\* reached by a **directory** link, not a file link (`README.md` → `contrib/claude-code/`,
`contrib/git/`, `docs/phase3-onboarding/`; `ONBOARDING_MOCKUP.md` → `mockup/`). Not orphans.
† named in prose by `AGENTS.md` and `CONVENTION.md` §7, never linked; GitHub loads it by convention.

**Broken links: zero, across all 28 standing docs.** (213 "broken" targets exist under
`docs/tasks/` — every one is a markdown link in a cost ledger whose
target is a bare agent-session UUID (`Challenger` → `de2207ce-…`), not a path. Out of scope; noted in §6.)

**Zero-inbound verdicts.** `CLAUDE.md` is the entry point (the harness loads it; it is one line).
`README.md` is the other entry point. The only real dead weight is
`docs/benchmarks/074_mechanism-question.md` — reachable from its own ticket and nothing else, while
its sibling `121_…` is cited by README, PLAN, BACKLOG and a runbook. It is a measurement record, so
the answer is a role line, not a deletion.

### 1.2 (a) The agent chain — the cost of the current structure to Pillar 1's caller

`CLAUDE.md` (`@AGENTS.md`) → `AGENTS.md` → *"Read these before non-trivial work (they govern every
session)"*.

| Tier | Files | Lines | Tokens (chars/4) |
|---|---|---|---|
| **1 — told to read** | CLAUDE.md · AGENTS.md · PLAN.md · ENGINEERING_RULES.md · AGENT_BRIEF.md · CONVENTION.md · BACKLOG.md | **2,344** | **~66,500** |
| **2 — pointed to as binding** | LESSONS.md (*"read this before proposing a new rule"*) · SKILL_GAP_CANDIDATES.md | 1,916 | ~34,100 |
| **closure** | 9 files | **4,260** | **~100,700** |

Two of the three biggest files are not reference material an agent consults — they are read in full
because the chain says so: `BACKLOG.md` is **~27,500 tokens** (612 lines, but the token ledger's rows
are enormous) and `PLAN.md` is **~26,900**. Together they are **82 %** of tier 1.

### 1.3 (b) Drift — PLAN vs `contract.py` and `store.py`

**They agree, and the plan says so, because it weakens the cut.** Checked programmatically against
`code_atlas/contract.py`:

| Vocabulary | `contract.py` | PLAN §4.2 | CONVENTION §3 |
|---|---|---|---|
| Node kinds | 11 | 11/11 identical | 11/11 identical |
| Edge kinds | 11 | 11/11 identical | 11/11 identical |
| Node fields | 10 | 10/10 identical | 10/10 identical |
| Edge fields | 9 | 9/9 identical | 9/9 identical |
| Confidence tiers | 3 | 3/3 | 3/3 |
| `ARG_LITERALS` | 6 | 6/6 | 6/6 |
| `contract_version` | 5 | 5 | "bump on any change" |

PLAN §10's SQL block is byte-equivalent to `store.py`'s `DDL` modulo `IF NOT EXISTS` and three
elided trigger bodies; `schema_version` is `"4"` in both.

**Two things the diff does find:**

1. **One real drift, already shipped.** PLAN §10's `meta` comment lists **5** keys
   (`schema_version, contract_version, last_commit, last_ref, built_at`). `store.py` defines **9** —
   `indexed_suffixes`, `collection_census`, `untracked_indexable`, `ignore_sources` exist in code and
   in no document (`ignore_sources` appears in PLAN §11 in another role). A hand-kept list drifted
   silently, which is exactly R6.7's falsifier.
2. **The vocabulary is enumerated three times, not twice** — `contract.py` (SSoT per R3.2),
   PLAN §4.2, **and CONVENTION §3** (*"the fixed contract vocabulary"*). H2 as written would have
   moved the drift risk from one doc to another.

**What carries the cut is a rule this repo already has, not the diff.** R6.7: *"A guard that needs
'every valid X' derives the set; it never lists it… A hand-kept list is precisely what drifts when
member N+1 arrives, and it drifts silently."* And the pattern is already in PLAN itself — §12 opens
with *"the payload contract … is specified once in `CONVENTION.md` §6 and is **not** repeated per tool
below."* PLAN §4.2/§10 is the one place that rule was never applied.

Also undocumented anywhere in prose (correctly, and the pointer should keep it that way): 14 named
subsets and flags in `contract.py` — `TYPE_KINDS`, `CALLABLE_KINDS`, `CALLER_KINDS`, `IMPL_KINDS`,
`UNMODELLED_REFERENCE_KINDS`, `IMPACT_KIND_WEIGHTS`, `ARG_SELECTORS`, `RESULT_FIELDS`, `META_FIELDS`,
the four `REQUIRED_*_FIELDS`, `KNOWN_CAPABILITIES`, `STUB_FLAG`, `RULE_FLAG`, `VIEW_DATA_PREFIX`.

---

## 2. The five hypotheses

### H1 — AGENTS.md ⊕ AGENT_BRIEF.md should be one file — **REFUTED, and the defect is the reverse**

The stated shape does not hold. `AGENT_BRIEF.md` (98 lines) is four incident-cited process rules
P1–P4 and nothing else. The textual overlap with `AGENTS.md` is **one line** — the router bullet that
summarises it.

Two facts kill the merge:

- **`AGENT_BRIEF.md` has a machine writer.** It was created 2026-08-15 by a `/mango:promote` run and
  grew P4 by another on 08-17 (2 commits, both promotions). P2 makes it a promotion *destination*
  (*"read the destination's relevant section"*). Merging it into `AGENTS.md` would point automated
  rule promotion at the file loaded into every session's context.
- **`AGENTS.md` is not a router — it is the sole home of binding rules**, and two other documents
  cite it as the authority: `BACKLOG.md:461` (*"see the 'Token usage on PR' rule in AGENTS.md"*) and
  `BACKLOG.md:600` (*"Standing approval per AGENTS.md"*). `tests/test_backlog_bookkeeping.py`'s
  docstring and two assertion messages also name `AGENTS.md` as the rule's source.

What *is* true is the inverse of H1, and it is worth fixing. Of `AGENTS.md`'s 12 non-negotiable
bullets, **11 restate a rule that lives elsewhere** (R1.1, R1.2, R1.4, R2, R3, R4 → ENGINEERING_RULES;
comments ≤ 3 lines → R7.5; docs-before-PR → the ENGINEERING_RULES self-check; commits / PR template →
CONVENTION §7; no Memory → CONVENTION §8) and **one originates there** (Token usage on PR). Add the
`scripts/gate.sh` doctrine and the maintainer standing approval, and an always-loaded orientation file
is the only home of three PR-gating rules.

**Second finding: its summary of AGENT_BRIEF is already stale.** It enumerates *"keeping `seen:`
honest, reading a rule's destination…, recording a deviation…"* — P1, P2, P3. P4 landed 08-17 and was
never added. A hand-kept list, drifting silently, in the file that tells agents what binds them.

### H2 — PLAN's schema sections should be shape + reasoning + pointer — **CONFIRMED, on R6.7, not on the diff**

See §1.3. The fields agree today; the argument is that three copies of one vocabulary is the shape
R6.7 forbids, one copy has already drifted (the `meta` keys), and PLAN §12 already demonstrates the
fix. Scope correction: the cut is **PLAN → pointer**, with **CONVENTION §3 kept** as the doc-side
home, because §3 carries per-kind semantics `contract.py` does not (what `REFERENCES` means, what
`PROVIDES_VIEW_DATA`'s synthetic target is, the qname convention worked per language).

### H3 — README and PLAN state the value claim twice — **CONFIRMED, and it is four places, not two**

The value claim appears in: `README.md:3-6` (lead), `README.md:28-42` (*Measured, not asserted*),
`docs/PLAN.md:6` (opening paragraph), `docs/PLAN.md:27` (§1 Goals), and again in §19's pivot entry.
None is marked authoritative. The founding-premise refutation is stated twice at length —
`README.md:74-86` and PLAN §19's struck clause + block quote — but that pair is *labelled*: README
links to §19 twice inside the section. So the refutation is a legible duplication; the **value claim
is not**. This is precisely what "PILLAR 1 authoritative in PLAN §1" fixes.

### H4 — FEEDBACK.md has no stated role — **REFUTED as stated; the real defect is that it ended**

Its first paragraph states the role better than a table row could: *"A running log of external
comments… **Ordered latest-first.** This is a record, not a decision: any conclusion that changes the
product is ratified in `PLAN.md` §19 and reflected in `BACKLOG.md`."* README's doc table already gives
it a line.

The findings are different:

- **It stops at Round 4 (2026-08-06) and the repo is on round 6.** Rounds 5 and 6 went to
  `BACKLOG.md`'s *Where these tickets came from* table and `docs/runbooks/field-retro.md`. Three
  commits total, none since 08-06 — the oldest standing doc in `docs/`. A "running log" that isn't.
- **README's one-liner is false.** It claims FEEDBACK holds *"external review rounds **and the field
  retros they produced**"*. The field retros are in PLAN §19 and BACKLOG.

Neither fold is right: PLAN §19 already ratifies its conclusions, and BACKLOG links it 9 times from
task files. It needs a closing line and an honest pointer.

### H5 — `PHASE3_ONBOARDING.md` is misnamed — **CONFIRMED, plus a staleness finding**

Three defects: the file repeats its own directory name; a phase is chronological and this one is
`Status: delivered`; and its own title is already the better name (*"Phase 3 — Onboarding: roadmap &
brainstorm"*).

The staleness finding is the one that costs something: its status block says *"Two quality defects…
are open as **118** and **119**"*. **119 is `done`** — closed inside 127 on 2026-08-23. A delivered
record that carries a live status block has to be maintained forever, and it wasn't.

`docs/onboarding/` is **not available** as a new home: that is where `generate_onboarding` writes the
committable artifact.

### Additional overlaps found (not on the list)

- **The 17-tool surface is described in full twice.** `README.md` §Tools (155 lines, column
  *Returns*) and `PLAN.md` §12 (106 lines, columns *Key args | Answers*) each name all 17 tools;
  `main.py`'s `TOOL_NAMES` is the source of truth. The columns differ enough to be two jobs
  (operator-facing vs design-facing) and PLAN §12 already delegates the payload contract to
  CONVENTION §6 — so this is a **deliberate non-change**; see §6.
- **`AGENTS.md`'s Docker section duplicates `README.md:541-550`** (the `fcntl` platform exclusion and
  the two `scripts/docker-test.sh` invocations), adding only the agent-facing instruction *"do not
  report it as unrunnable"* and the expected pass count.
- **A guard clause keyed on a heading that no longer exists.**
  `tests/test_backlog_bookkeeping.py` splits the token table with
  `tail.partition("## Suggested order")` — BACKLOG has no such heading, so the token-row regex reads
  to EOF, through `## Conventions`. Benign today, silently wrong the day a section is appended.
  Its own ticket; see §6.

---

## 3. Role table — one row per standing document

Destination: **`CONVENTION.md` §8 (Docs & tracking)**, which today is three bullets and is already
the doc-governance section. Not README — README's job is to let a reader leave in ten seconds, and a
12-row three-column table is not that. README keeps its 6-row reader-facing table plus a pointer.

Rows derived from what each file contains today, not from its title.

| Doc | Reader | Answers | Is **NOT** |
|---|---|---|---|
| `README.md` | a human deciding whether to install | what it does, what it measured, how to install and configure, what every tool returns | not the design record; not a rule book; never the authority for a number — it cites the runbook that produced it |
| `AGENTS.md` | an agent at session start | orientation: what this is, where things live, which docs bind, how the maintainer authorises finishing steps, how to run the gate and the suite | **not a rule origin** — every rule here is a summary with a destination; not a lifecycle rule book (→ `AGENT_BRIEF.md`) |
| `CLAUDE.md` | the Claude Code harness | one line: `@AGENTS.md` | not content, ever |
| `PLAN.md` | anyone asking *why is it shaped this way* | **§1 the pillars (authoritative)**; the design and its reasoning; §19 the durable decision log — what was measured, what was refuted | not the vocabulary of record (→ `contract.py`, `CONVENTION.md` §3); not a schema listing (→ `store.py`); not task status (→ `BACKLOG.md`) |
| `BACKLOG.md` | anyone asking *what is open, what landed, what it cost* | the ticket table, the shipped record by phase, the token ledger | not rationale (→ PLAN §19); not lessons (→ `LESSONS.md`); not a rule origin — its two back-pointers to `AGENTS.md` are the smell C6 fixes |
| `ENGINEERING_RULES.md` | an agent about to write code | the binding *how we build* rules R1.1…, several CI-gated, each with a falsifier; the pre-PR self-check | not process (→ `AGENT_BRIEF.md`); not naming or style (→ `CONVENTION.md`); not evidence (→ `LESSONS.md`) |
| `AGENT_BRIEF.md` | an agent running the lifecycle | the binding *how we run it* rules P1…, each earned by a cited incident. **A `/mango:promote` destination** | never restates a code rule (it says so itself); not orientation; not a harness gap log (→ `SKILL_GAP_CANDIDATES.md`) |
| `CONVENTION.md` | an agent naming or placing something | repo layout, naming, the fixed contract **spelling** and per-kind semantics (§3), Python style, tool/payload conventions (§6), git, **the doc role table (§8)** | not the authoritative field set (→ `contract.py`); not design reasoning (→ PLAN) |
| `LESSONS.md` | an agent about to propose a rule | per-task claims with handles and `seen:` counts — the corpus rules are promoted from | not a rule (a claim is promoted, not applied); not a decision log |
| `SKILL_GAP_CANDIDATES.md` | the mango maintainer | type-3 signals: a phase that could have run a check and did not | not a change to any mango skill — this repo never edits one |
| `FEEDBACK.md` | anyone auditing an outside claim | external review rounds 1–4 (2026-08-04/05) and the repo-verified assessment of each, **series closed** | not a decision (→ PLAN §19); not the field retros (→ PLAN §19, `runbooks/field-retro.md`, BACKLOG) |
| `phase3-onboarding/ROADMAP.md` | anyone asking how Pillar 2 was decided | the delivered M10–M12 roadmap, the deterministic/LLM split, the architecture-vs-rules placement | not current status (→ `BACKLOG.md`); not the ticket list — its §7 table is a historical copy |
| `phase3-onboarding/ONBOARDING_MOCKUP.md` | a reviewer of the system map | the design note the map was reshaped from (2026-08-19), and which parts are deterministic vs prose | not shipped behaviour (→ README, PLAN §14) |
| `docs/runbooks/*.md` | an operator reproducing a number | one protocol each, re-runnable, with the conditions the number holds under | never a summary — the caveat travels with the number |
| `docs/benchmarks/*.md` | a reader checking one measurement | the raw result of one question class, cited from its ticket | not a claim about the product — README/PLAN quote these, never the reverse |
| `adapters/php/README.md`, `onboarding_llm/README.md`, `contrib/*/README.md`, `phase3-onboarding/mockup/README.md` | someone working in that directory | how to run/launch what is in this directory | not repo-level anything |
| `.github/pull_request_template.md` | the author opening a PR | the sections and the self-check every PR fills | not the rule it checks (→ ENGINEERING_RULES, AGENTS.md) |

The **Is NOT** column is what the restructure buys. Six of these boundaries are already honoured in
practice and merely unstated; three are actively broken today (AGENTS.md as a rule origin, PLAN as a
vocabulary listing, README as the authority for FEEDBACK's contents).

---

## 4. Where the pillars go

**Adopted, with one adaptation.**

- **`PLAN.md` §1 — authoritative. Adopted.** A new `### The two pillars` subsection at the top of §1,
  above *Goals*, carrying the given wording verbatim: PILLAR 1 — GRAPH, PILLAR 2 — ONBOARDING, SHARED
  CONSTRAINT. Supervision leads Pillar 2's prose, and the note that `onboarding/` is the older name
  goes in the same subsection so nobody renames code from it. §1's existing Goals bullets stay where
  they are — they are the *how*, and they already read as consequences of the pillars.
- **`README.md` — two sentences plus a link. Adopted.** README's lead states Pillar 1 well already
  and does not state Pillar 2 at all: onboarding appears only in the status blockquote and the tool
  table. Two sentences after the lead, then a link to PLAN §1.
- **`BACKLOG.md` reorganised by pillar. Adapted, for two measured reasons.**
  1. **Split `## Open work` into two tables** (`## Open work — Pillar 1 · Graph`,
     `## Open work — Pillar 2 · Onboarding`), every row moved verbatim, `Theme` column untouched.
     The existing `Theme` column already carries the split — Phase 3 / M10–M12 → Pillar 2 (30 rows),
     everything else → Pillar 1 (217 rows) across 28 theme values.
  2. **Do NOT add a `Pillar` column, and do NOT re-sort the historical phase sections.**
     `tests/test_backlog_bookkeeping.py`'s `TASK_ROW` regex is positional — `| NNN | title | theme |
     status |` — so a fifth column silently moves `status` out of the capture and the guard passes
     while comparing nothing. And the `## Phase 1 / 1.5 / 1.5b / Phase 2` sections are a *ship-order*
     record; sorting them by pillar destroys the one thing they answer.

The ladder does fall out of the split without a new document, which is the part of the proposal worth
keeping: the two Open-work tables are the two pillars' live surfaces.

---

## 5. The changes, in order — one logical change per commit (R7.3)

Every step: run `scripts/gate.sh`, then re-run the link sweep over the touched files. Three tests
parse these documents and are the ones that can go red — name them in each commit's verification:
`tests/test_backlog_bookkeeping.py` (BACKLOG structure), `tests/test_routing_surface.py`
(README prompt names + `"Operator prompts, not agent routing"` in PLAN), `tests/test_view_databag_decision.py`
(six pinned phrases in PLAN, all in §12 L530 and §19 L1038–1069 — **clear of every section C2 touches**).

### C1 — Place the pillars

- **Files:** `docs/PLAN.md` (§1, new subsection above *Goals*), `README.md` (two sentences after the
  lead + link), `AGENTS.md` (*What this is* gains one clause naming both pillars and pointing at
  PLAN §1).
- **Moves:** nothing moves. This adds the one input that is not derivable from the repo.
- **Deletes:** nothing.
- **Links:** README gains `docs/PLAN.md#1-goals--non-goals`; AGENTS.md's existing PLAN link is
  reused. §1's heading text is unchanged, so `PLAN.md#19-…` and the other four existing anchors are
  unaffected.
- **Breaks:** nothing.

### C2 — Cut PLAN §4.2 and §10 to shape + reasoning + pointer

- **Files:** `docs/PLAN.md` only.
- **§4.2 — moves out:** the four enumerations (node kinds, node fields, edge kinds, edge fields),
  the tier list and the `ARG_LITERALS` list. Replaced by one sentence in §12's own idiom: the
  vocabulary is defined once in `code_atlas/contract.py` (`NODE_KINDS`, `NODE_FIELDS`, `EDGE_KINDS`,
  `EDGE_FIELDS`, `CONFIDENCE_TIERS`, `ARG_LITERALS`) and spelled with its per-kind semantics in
  `CONVENTION.md` §3; it is not repeated here.
- **§4.2 — stays:** every paragraph of reasoning. Why the handshake is what keeps the core
  language-agnostic; the five wire rules; the failure split; **why `args` carries a category and
  never a value**; why `arg_keys` absent ≠ empty; the qname-convention argument including the JS/TS
  case that pressure-tests it; capability flags as ISP; §4.3 and §4.4 untouched.
- **§10 — moves out:** the 30-line `CREATE TABLE` block. Replaced by the inventory in prose (5
  tables · one external-content fts5 table · 3 mirror triggers · 8 indexes · WAL / `foreign_keys` /
  `busy_timeout`) plus a pointer to `store.py`'s `DDL`.
- **§10 — stays, verbatim:** `qualified_name` is unique per file not globally, and its consequence
  for the resolver; the same-file keep-first dedupe; `schema_version` is `"4"` and enforced loud,
  with the **direction** argument and the "no query tool rebuilds" line; the R4.2 determinism
  carve-out; column defaults. None of it exists anywhere else.
- **§10 — fixes the one measured drift:** the `meta` key comment stops listing 5 of 9 keys and
  points at `store.py`'s `*_KEY` constants (R6.7).
- **Links:** two new source pointers (`code_atlas/contract.py`, `code_atlas/store.py`); one new doc
  link to `CONVENTION.md#3-the-contract-vocabulary-fixed-spelling--do-not-vary`, which already exists.
- **Breaks:** nothing. No inbound link targets §4.2 or §10 (PLAN's inbound anchors are §19 ×5 and
  §12's `#tools`-style README anchors). `tests/contract/test_contract_schema.py` asserts against
  `contract.py`, never against PLAN.

### C3 — Close the FEEDBACK series and fix the pointer that misdescribes it

- **Files:** `docs/FEEDBACK.md` (one line under the header), `README.md` (doc-table row).
- **Moves:** a pointer only. FEEDBACK's header line gains: the series closed at Round 4
  (2026-08-06); later rounds are in PLAN §19, `runbooks/field-retro.md` and BACKLOG's *Where these
  tickets came from*. README's row drops the false *"and the field retros they produced"* and names
  rounds 1–4.
- **Deletes:** nothing. No merge — PLAN §19 ratifies its conclusions and 9 task files cite it.
- **Links:** FEEDBACK gains `runbooks/field-retro.md` and `BACKLOG.md#where-these-tickets-came-from`
  (heading exists, L354).
- **Breaks:** nothing.

### C4 — Move the doc role table into CONVENTION §8

- **Files:** `docs/CONVENTION.md` (§8 gains the §3 table above), `README.md` (§Documentation keeps
  its 6 reader-facing rows, gains a pointer to CONVENTION §8).
- **Moves:** README's *Answers* column supplies the seed rows; the *Reader* and *Is NOT* columns are
  new, derived in §3 of this plan.
- **Deletes:** nothing. **No new document — the UPPER_SNAKE set is unchanged** (13 standing
  UPPER_SNAKE files in, 13 out; one renamed by C6).
- **Links:** README gains `docs/CONVENTION.md#8-docs--tracking`. CONVENTION §8's three existing
  bullets stay; the table sits above them.
- **Breaks:** nothing. No inbound link targets `README.md#documentation`.

### C5 — Make AGENTS.md an honest router

Four moves, each to a destination read first (P2):

1. **Token usage on PR → `ENGINEERING_RULES.md` R7.2**, widened. R7.2 already reads *"Keep the plan
   and backlog honest… task status updates both BACKLOG.md and the task file's frontmatter"* — the
   ledger clause is the same rule's other half, so this is a widening, not an R7.6.
   **Repoint `BACKLOG.md:461`** from *"the 'Token usage on PR' rule in AGENTS.md"* to R7.2, and
   `tests/test_backlog_bookkeeping.py`'s two assertion messages + docstring with it.
2. **The `scripts/gate.sh` doctrine → `ENGINEERING_RULES.md` R6.5**, widened. R6.5 already says
   *"This generalises to every guard, not only a sweep"*; "exit 2 means a check was skipped, so only
   `GATE GREEN` counts, and a gate that shrank to what this machine can run has not verified the
   tree" is that sentence at the gate level. AGENTS.md already cites R6.5 for it.
3. **The Docker duplication → cut to a pointer.** `README.md:541-550` already carries the `fcntl`
   exclusion and both `scripts/docker-test.sh` invocations. AGENTS.md keeps only the agent-facing
   instruction (*this is a platform limitation, not a regression; prove delta-green in Docker; do not
   report the suite as unrunnable*) and the expected count, and links README.
4. **Fix the stale AGENT_BRIEF summary.** Replace the hand-kept *"keeping `seen:` honest, reading a
   rule's destination…, recording a deviation…"* (P1–P3; P4 missing since 08-17) with the rule range
   and the destination. R6.7 applied to prose.

The **maintainer standing approval stays in `AGENTS.md`** — it is the authorization record and no
other document can hold it; `BACKLOG.md:600`'s *"per AGENTS.md"* stays valid.

- **Breaks:** `BACKLOG.md:461`'s prose pointer (updated in the same commit). No anchor breaks.

### C6 — Rename `PHASE3_ONBOARDING.md` → `ROADMAP.md`, and unstale its status block

Ordered last: it is the highest-churn, lowest-value step, and nothing above depends on it.

- **Files:** `git mv docs/phase3-onboarding/PHASE3_ONBOARDING.md docs/phase3-onboarding/ROADMAP.md`
  \+ **36 references across 15 files**: `docs/PLAN.md` (3), `docs/BACKLOG.md` (1),
  `docs/LESSONS.md` (1), `docs/runbooks/tokens-to-answer.md` (1),
  `docs/benchmarks/121_onboarding-question-class.md` (1), and 9 task files
  (083 ×2, 084 ×2, 085 ×2, 086, 087 ×2, 088, 089, 090, 091 ×3, 121).
- **Also fixes:** the status block says 118 and 119 are open. **119 is `done`** (closed in 127).
- **Deletes:** nothing.
- **Breaks:** all 36, every one mechanical (`git mv` + one `sed`), and the link sweep proves the fix.
- **Not done here:** renaming the **directory** `docs/phase3-onboarding/` → a pillar name. It costs
  **26 more references across 20 files** including `README.md` and `CONVENTION.md` §1's layout tree,
  and `docs/onboarding/` — the obvious name — is taken by `generate_onboarding`'s output. Its own
  ticket, with that collision as the first thing to decide.

---

## 6. What this is NOT doing, and why

- **Not touching `README.md` §Tools or `PLAN.md` §12.** The 17-tool surface is described twice, but
  the columns are two different jobs (*Returns* for an operator, *Key args | Answers* for a designer)
  and PLAN §12 already delegates the payload contract to CONVENTION §6. Collapsing them is a real
  ticket with a real reader question behind it; it is not link hygiene.
- **Not rewriting a single paragraph.** Content moves or is cut. The three places this plan changes
  wording at all are the pillar text (given, verbatim), the four sentences that replace a deleted
  enumeration with a pointer, and the two false/stale statements (README's FEEDBACK row, the
  118/119 status line). Anything else that reads badly is another ticket.
- **Not touching `LESSONS.md` (1,767 lines).** It is the biggest file in tier 2 and its size is its
  function: a claim corpus with `seen:` counts that P1 grows per ticket. Compressing it would break
  promotion's only gate.
- **Not reducing the agent chain by deleting anything.** The ~66.5k number is measured, not acted on
  here. Two candidate follow-ups it argues for, both out of scope: BACKLOG's token ledger (the
  larger half of its ~27.5k) does not need to be in an agent's session-start read, and PLAN's §19
  (385 lines) is a decision log an agent consults, not one it reads whole. Splitting either is a
  structural change that needs its own measurement.
- **Not fixing the 213 UUID pseudo-links** in `docs/tasks/*` cost ledgers — an agent-session UUID
  used as a link target should be plain text. Cosmetic, task-scoped, 129 files.
- **Not fixing `tests/test_backlog_bookkeeping.py`'s dead `partition("## Suggested order")`.** A real
  latent guard defect found on the way (§2), but it is a test change, not a docs change, and it wants
  a red run of its own (R6.5).
- **Not proposing a new UPPER_SNAKE document.** None was needed: the role table went to CONVENTION
  §8, the pillars to PLAN §1, the ladder fell out of BACKLOG's existing `Theme` column.

---

## 7. Where the numbers keep their conditions

Per the constraint that a number arriving without its caveat is a regression, not a move. None of
C1–C6 relocates a measured claim; these are the claims in the blast radius, recorded so a later
reviewer can check they still read correctly:

| Claim | Condition that must travel with it | Where it lives now |
|---|---|---|
| tokens-to-answer | **~69× aggregate** across the whole question set on three pinned public repos; **95–114×** on relation queries alone. The **98.2×** figure is *one local-tier run over 5 questions* (`tokens-to-answer.md:293`) and the **178.3×** is another (`:156`) — neither is the headline | README *Measured, not asserted* → `runbooks/tokens-to-answer.md` |
| Phase 3's own cost gate (121) | **cheaper for lookups** (12/12 correct, recall 1.0) **and wrong for reading order** (1 of 5 on a canonical repo) — both halves, always | README, PLAN, BACKLOG → `benchmarks/121_…md` |
| blind field round 5 | 8 of 8 checked claims exact, **zero false statements**; every failure that round was silence or ambiguity | README, PLAN §19 |
| the founding premise | struck, **not deleted**, because every decision was taken under it; measured false 2026-08-08 on a ~19k-file private monorepo | PLAN §19 (authoritative) + README §*Founding premise, refuted* (labelled, links back twice) |
| `confidently_wrong = 0` / no-op rebuild 56.1 s → 2.113 s (26×) | the conditions in §19's own entries | PLAN §19 |

**Correction to the source prompt:** it names "98x tokens-to-answer" as a measured claim to preserve.
The repo's headline is **~69×**; 98.2× is a single local-tier run. Preserving "98x" as the claim would
itself be the regression the constraint forbids.

---

## 8. Where this plan disagrees with the prompt it came from

The prompt asked for this section, having been written from six files without the git history.

1. **H1 is refuted, and merging would be actively harmful.** `AGENT_BRIEF.md` is a `/mango:promote`
   destination — both its commits are promotion runs. Merging it into the always-loaded orientation
   file points automated rule promotion at every session's context. The defect is the mirror image:
   `AGENTS.md` originates rules it should only summarise.
2. **H2's diff came back clean, and the cut still stands — on R6.7, not on drift.** The prompt said
   agreement weakens the cut. It does. What replaces it is stronger: the repo already forbids
   hand-kept copies of a derivable set, PLAN §12 already applies the fix one section later, and the
   *one* hand-kept list that did drift (`meta` keys, 5 of 9) is the falsifier firing.
3. **H2's scope was one document short.** `CONVENTION.md` §3 is a third copy. Cutting only PLAN would
   have moved the risk rather than removed it.
4. **H4 is refuted as stated.** FEEDBACK.md states its role in its own second paragraph, better than
   a table row would. The defect is that the series ended in August and the pointer describing it is
   false.
5. **"BACKLOG reorganised by pillar" has a hard constraint the prompt could not have known.**
   `tests/test_backlog_bookkeeping.py` parses the table positionally, so the obvious implementation —
   a `Pillar` column — would make the guard pass while comparing nothing. Two tables, not one column.
6. **The role table does not belong in README.** README's own stated job is to let the wrong reader
   leave in ten seconds. `CONVENTION.md` §8 is the doc-governance section and was the right
   destination, which is what P2 asks you to check before proposing anywhere else.
7. **"98x" is not this repo's claim.** See §7.
8. **The measurement the prompt was proudest of is the one that argues for work this plan defers.**
   ~66.5k tokens over 7 files is real, but the fix is not in any of C1–C6: it is BACKLOG's token
   ledger and PLAN §19, and both need their own measurement before anyone moves them. This plan makes
   the boundaries stateable; it does not make the chain cheaper. Saying so is the point of §6.

---

## 9. Execution notes — what the plan got wrong

Recorded per P3: a deviation from the ticket text is written down as a deviation, not silently
corrected.

**The plan adopted a change and never gave it a commit.** §4 adopts splitting BACKLOG's Open work by
pillar, and §5's ordered change list runs C1–C6 without it. It shipped as **C1b**, immediately after
C1, on the maintainer's instruction. A change list that does not contain a change the plan adopted is
the review defect the list exists to prevent.

**D2 was wrong, in the direction that would have justified more change.** §4 and C1b's commit message
claim a fifth `Pillar` column would move `status` out of `TASK_ROW`'s capture group and leave the
guard passing while comparing nothing. Measured before the guard was touched: it **fails** either way
— `Pillar 1` does not match `[a-z-]+` so the row drops and `len(backlog_statuses()) ==
len(task_files())` catches it; a lowercase value like `graph` matches and is caught per task as an
unknown status. The positional parse was unclear and brittle; it was not vacuous. The two-table split
is still right, on its other stated reason — the phase sections answer ship order, which a pillar sort
destroys — and on the maintainer's decision. The correction is in `dff4c72`'s message; `c4412af` was
deliberately **not** amended.

Consequence worth stating: after the guard fix a `Pillar` column *is* now a safe edit (red run 4 adds
one and the suite passes). The constraint that shaped C1b no longer exists; the decision it shaped
stands on its own merits.

**C6's reference count was 29 across 17 files, not 36 across 15.** §5 counted `git grep -o` hits
including the file's own self-references. The material miss is a file class the audit did not look in:
**`tests/test_onboarding_question_class.py`** names the document in its docstring. A mention, not a
filesystem read, so nothing was load-bearing — but §1's sweep covered markdown only, and a rename
audit that does not grep the test tree is not finished. Task 133's AC3 inherits this: enumerate, do
not eyeball.

**What the plan said it would not do, and did not do.** No prose reworded in passing; README §Tools
and PLAN §12 untouched; `LESSONS.md` not compressed; the 213 task-ledger UUID pseudo-links left alone;
no new UPPER_SNAKE document (13 in, 13 out, one renamed). The one item promoted out of §6 into work
was the `test_backlog_bookkeeping.py` fix, on the maintainer's instruction, and it shipped with four
recorded red runs (R6.5).

## Outcome

**Done.** Nine commits: C1 pillars · C1b BACKLOG split · C2 PLAN §4.2/§10 cut · C3 FEEDBACK closed ·
C4 role table → CONVENTION §8.1 · C5 AGENTS.md derouted to R7.2/R6.5 · C6 rename + status block ·
the guard fix · task 133 filed.

PR [#153](https://github.com/cuongdinhngo/code-atlas/pull/153). Measured at commit `3807888`: link sweep **28 standing docs, 0 broken**; `test_backlog_bookkeeping`
**264 passed** (261 before, +1 test and +2 parametrised ids for tasks 132/133); ruff and mypy clean on
the one touched source file. The tier-1 agent-chain cost this ticket measured — ~66,500 tokens over 7
files — is **unchanged by design**; acting on it is [133](133_agent-chain-is-one-tier.md).
