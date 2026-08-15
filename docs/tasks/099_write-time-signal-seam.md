---
id: 099
slug: write-time-signal-seam
title: 'Every decision the agent made without the graph wanted one line inside a file read, not a tool call'
phase: 1.5b
milestone: Agent-fit
status: done
depends_on: [097, 069, 036]
---

## Goal
Asked to name the three most consequential decisions it made **without** calling code-atlas, the
field session named three — and all three wanted the **same delivery channel: one line riding along
with a file read it was already performing**. **None of them wanted a tool call.**

This reframes four rounds of adoption findings. The project has been treating low adoption as a
*routing* problem (069, 081: better names, better descriptions) and then as a *cost* problem (080,
096: make refresh cheap). The interview says it is a **position** problem: by the time an agent
formulates a query, it has already framed the task in a way that has no slot for one — and the
moment the signal would have changed the outcome is the moment the agent is *reading or writing a
file*, not the moment it is choosing a tool.

The strongest evidence is that cost cannot explain it. The two highest-value uncalled queries —
`file_outline` on a legacy file untouched for months, and `search_symbol kind:"Function"` for a
name-collision sweep — needed **no rebuild at all**; the index was already current for both. Each
would have cost ~1 s at any point in the five hours, and neither was made.

## Evidence (field interview, 2026-08-14, §1 / §3 / §4)
The three moments, with the line the evaluator says would have had to appear, and where:

| Moment | The one line | Where it had to appear |
|---|---|---|
| Deciding globals vs closures for a ported page | *"`getState` is already declared globally in this repo — 1 other definition, different signature, at `…/View/SG.php:74`"* | **At the moment the name was typed into a `Write`/`Edit`** — "by the time I would have queried, I had already decided" |
| Deciding one shared port vs two region-specific ports | *"This file defines 7 top-level functions and 2 closures: `getEnt:29`, `getStates:42`, `siteDisplay:56`, …"* | **Inside the `Read` result for the legacy file it was already opening** |
| Deciding which front-end asset the port should load | *"This file references `js/<name>.js`; 2 files with that basename exist, in different regional trees"* | **Inside the `Read` result**, as the eye passed the `<script src=` line |

- §3, the one uninvited interruption, independently converges on the same thing: fire at the `Read`
  that opens the file about to be ported, say the outline, **~150 tokens** — *"past ~300 I would skim
  it; past ~500 I would learn to treat it as chrome and stop seeing it."*
- §3 also names where an interruption would **cost**: inside browser-probe output and inside ~40 CI
  shell results, where it was pattern-matching one field under a fixed schema — *"I would have started
  truncating my own reads"* — and on every `Write` during authoring.
- §3's second fire, and the only other one it will name: at the first `Write` creating a new file
  under the indexed tree — *"this path is untracked; symbol queries about it will answer
  `no_such_symbol` until it is committed and reindexed"* ([092](092_untracked-files-are-invisible-and-answer-no-such-symbol.md)'s
  defect, met at the moment it is created rather than an hour later).
- §7.6: the value also leaks *after* the call — `impact`'s 25 rows caught a committed error, then the
  evaluator wrote a prose summary and discarded the payload. *"The tool did its job; I was the lossy
  step."*

## Generality — why this one survives the "n = 1, one repo" filter
The evidence is a single session on the anchor repo — a **real user, and the first**, but one user.
What makes this finding portable is that **its subject is the agent, not the repository**: an agent frames
a task, reads files, writes files, and only then — if at all — chooses a tool. The three moments are
about *when an agent is receptive to information*, and nothing in them depends on that repo's
migration, its regional split, or PHP. The same convergence would be predicted for a Python service
or a TypeScript monorepo, and the next field round can falsify it cheaply: if the signal is shipped
and the next evaluator tunes it out or never mentions it, the finding was session-specific.

The two lines it proposes are equally repo-neutral: *what does this file define* is `file_outline`,
which exists for every language the server will ever support, and *this path is untracked* is a
property of git, not of any codebase.

## The question this ticket must answer before it writes code
**Is a write-time/read-time signal something code-atlas may ship at all?** An MCP server answers when
asked; it does not sit in the host's file-read path. The channel the interview points at is a **host
hook**, not an MCP tool — and the harness this project ships (`.harness.json`, agent hooks) already
has that shape.

So the deliverable is a **seam and a verdict**, not a feature:
- If the honest answer is *"this cannot live in code-atlas; it lives in the host's hook config,
  and what we ship is a fast, quiet, hook-shaped entry point"* — that is a legitimate and valuable
  outcome, and it bounds what 069/081-style description work can ever achieve.
- If a signal can be attached to payloads the agent already receives (`next_tool_suggestions` is the
  existing deterministic precedent), scope it to the occasions that earn it.

## Scope / Deliverables
- **A written verdict** on where the signal can honestly live: host hook · payload rider · both ·
  neither. With the reasoning, because this decision shapes the product's position.
- **A hook-shaped entry point** if the verdict allows one: a single command, sub-second, that takes a
  path and returns the outline line at the token budget the field named (**~150 tokens**, hard cap),
  with no build and no lock contention.
- **A silence rule.** The field named exactly where an interruption destroys value; encode it. A
  signal that fires on every read is chrome within three invocations — that is a measured claim from
  the field, not a guess.
- **The two lines, and only those two, to start** (R1.2/YAGNI): the file outline at read time, and
  the untracked warning at create time. The field explicitly refused to name a third.
- **A recall measurement**, coordinated with [097](097_recognition-probe-measures-names-not-recall.md):
  the next field round must be able to say whether the signal was *seen*, *acted on*, or *tuned out*.

## Constraints
- **R4** — deterministic and LLM-free; a signal is a lookup, never a judgement.
- **R1.1** — no language branch; "what does this file define" is already language-agnostic.
- **Cost is a hard gate here, not a preference:** a read-time signal that needs a rebuild is not a
  read-time signal. It must answer from the index as-is and say so when the index is behind, rather
  than blocking on freshness.
- **061** — the token cap is the design, not a tuning parameter.
- Do not widen into the host's business: code-atlas may *offer* a hook-shaped surface; wiring it is
  the host's decision, and the docs must say so.

## Acceptance criteria
- The verdict is written, with rejected alternatives.
- If an entry point ships: it returns the outline for a large file in **< 1 s** on a large index, at
  **≤ 150 tokens**, with a test pinning both bounds.
- The untracked-at-create signal is covered by a test and cross-referenced from 092.
- A documented silence rule, plus a test that the signal is absent on the occasions named.
- README/runbook says how a host would wire it, and states plainly that code-atlas does not wire
  itself into anyone's editor.

## References
Field interview (round-5 companion, 2026-08-14) §1 (all three moments + the convergence note), §3,
§4 (the adversarial pass: framing, not latency), §7.6, §8.1 ("reaching the moment of decision — 25 %"),
§8.4 item 2. Related: [097](097_recognition-probe-measures-names-not-recall.md) (recognition vs
recall — the same finding measured from the other side),
[069](069_tool-names-do-not-say-what-they-answer.md) and
[081](081_routing-prompts-are-not-in-the-agents-surface.md) (routing work whose ceiling this bounds),
[036](036_edit-index-hook.md) (the existing hook precedent),
[092](092_untracked-files-are-invisible-and-answer-no-such-symbol.md) (the second signal's defect),
[096](096_edit-then-ask-tax-two-files-cost-a-minute.md) (cost — the *second* constraint).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 099 — write-time signal seam (working doc)

- **Ticket:** 099 · local-file `docs/tasks/099_write-time-signal-seam.md`
- **Type:** seam + verdict + hook entry point
- **Repo(s) / Porting:** app only
- **SCOPE:** L
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **work_doc_mode:** embed (plain local-file ticket, hand-authored)
- **BASELINE:** green — `scripts/docker-test.sh` on `main` @ `4786f19`: **1204 passed**.

---

## Phase 0 — Refine

`PREMISE: 12 reference(s) checked | 0 missing | 0 ambiguous`
`RECALL: 8 claim(s) surfaced | 0 by symbol | 3 by area | 5 does-not-apply | 0 retired skipped — advisory`
`REFINE: 4 unresolved surfaced | 0 want-decision asked | 4 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise check.** Every source the ticket cites as already existing resolves: `code_atlas/hooks/`
holds **`poke.py` (036)** and **`refresh.py` (053)** — the hook precedent is real and shipped, with
console scripts `code-atlas-poke` / `code-atlas-refresh` in `pyproject.toml`;
`next_tool_suggestions` exists on `get_index_status`; `store.untracked_indexable_paths()` (092)
exists; `file_outline` exists; tickets 036/069/081/092/096/097 all present; README §hook and
`docs/runbooks/onboarding-a-repo.md` already document manual hook install. **PREMISE HOLDS.**

**Recalled claims (advisory).** Matched by area: **097-C2** (*descriptions can name the occasion;
they cannot make the agent notice*) — this ticket is that claim's follow-through, and 097 already
recorded the same verdict for `file_outline`'s trigger; **`derived-not-listed-invariant`** (→ R6.7)
— the silence rule enumerates occasions, so it must derive what it can; **`prove-the-guard-fails`**
— a silence rule that cannot be made to fire is untested. Does not apply: `scope-by-key-not-by-file`,
`pin-the-table-a-purity-claim-rests-on`, `late-writer-outside-the-delta` (all resolver-internal),
`skip-dynamic-means-unlinkable`, `sibling-meta-non-int`.

**HOW-decisions (resolved + cited, 0 handed back):**
1. **The verdict is host-hook, not payload rider.** Cited: 097's Resolution already decided this for
   the same signal — *"the core cannot see that the agent is about to Read, and a suggestion on every
   payload violates 061"*. The channel exists and is shipped (036/053). **This ticket does not
   re-open that; it builds the entry point 097 named as the missing "workflow trigger".**
2. **Two signals only** — ticket Scope bullet 4, R1.2/YAGNI. The field refused to name a third.
3. **The silence rule is structural, not stateful.** Cited: §3 names *where* interruption costs
   (browser-probe output, ~40 CI shell results, every `Write` during authoring). Those are other
   tools and existing-file writes — excludable by construction, with no session state to keep.
4. **Token cap is enforced, not documented.** 061 / ticket Constraint 4 — the cap is the design.

---

## Phase 1 — Analysis

### Requirements matrix

`SECTIONS: 8 found (Goal, Evidence, Generality, The question…, Scope / Deliverables, Constraints, Acceptance criteria, References) | 8 decomposed | ROWS: G=2 R=5 C=5 AC=5`

| ID | Source | Verbatim (abbrev.) | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|--------------------|----------------|--------------|----------------|-----------------|--------|
| G1 | Goal | all three decisions wanted one line riding along with a file read; **none** wanted a tool call | Position problem, not routing/cost | interview §1 table | CL1, CL2 | signal fires at the Read occasion | ⬜ |
| G2 | Goal | cost cannot explain it — both top uncalled queries needed no rebuild | The entry point must not build | §1; 096 landed | CL1 | no-build test | ⬜ |
| R1 | Scope | written verdict: host hook · payload rider · both · neither, with reasoning | **host hook**, not payload rider | 097 Resolution; 036 precedent | CL5 | Verdict section | ⬜ |
| R2 | Scope | hook-shaped entry point: one command, sub-second, path → outline, ~150 tokens, no build, no lock contention | `code-atlas-signal` console script | `hooks/poke.py` shape | CL1, CL3 | budget + latency test | ⬜ |
| R3 | Scope | a silence rule — encode where interruption destroys value | Structural exclusions, no session state | §3 (probe output, CI shells, authoring writes) | CL1 | silence tests | ⬜ |
| R4 | Scope | the two lines and only those two (R1.2) | outline@Read + untracked@create | §1, §3 second fire | CL1 | both signals tested; no third | ⬜ |
| R5 | Scope | recall measurement coordinated with 097 | Retro §2 bucket 4 gains a *seen / acted / tuned out* row | `docs/runbooks/field-retro.md` | CL4 | runbook test | ⬜ |
| C1 | Constraints | R4 — deterministic, LLM-free; a lookup never a judgement | Reads the index, no model | R4.1 | CL1 | no LLM/network in diff | ⬜ |
| C2 | Constraints | R1.1 — no language branch | Outline is already language-agnostic | R1.1 | CL1 | CI grep-gate | ⬜ |
| C3 | Constraints | cost is a **hard gate**: no rebuild; answer from the index as-is, say so when behind | Never calls a build; degrades to a stale note | 035 read-through is a *query* path, not this | CL1 | no-build + stale test | ⬜ |
| C4 | Constraints | 061 — the token cap **is** the design | Hard cap, enforced in code | 061 | CL1, CL2 | budget test | ⬜ |
| C5 | Constraints | do not widen into the host's business; docs say wiring is the host's | Ship the surface, never wire it | README hook §, 036 precedent | CL5 | README/runbook wording + test | ⬜ |
| AC1 | AC | verdict written, with rejected alternatives | Artifact | — | CL5 | Verdict section | ⬜ |
| AC2 | AC | < 1 s on a large index, ≤ 150 tokens, test pinning **both** | Two bounds, both pinned | — | CL1, CL3 | budget + latency test | ⬜ |
| AC3 | AC | untracked-at-create covered by a test, cross-referenced from 092 | Test + a line in 092 | `untracked_indexable_paths()` | CL1, CL5 | test + 092 xref | ⬜ |
| AC4 | AC | documented silence rule + test that the signal is **absent** on the named occasions | Negative tests | §3 | CL1, CL3, CL5 | silence tests | ⬜ |
| AC5 | AC | README/runbook says how a host would wire it, and that code-atlas does not wire itself | Docs | README §hook | CL5 | docs test | ⬜ |

`AC VALIDATION: 5 AC | 5 falsifiable in-session | 0 operator-deferred | 0 unfalsifiable`
`CLARIFICATIONS: j = 0 blocking`

### Rule sections (step 11 — union of two sources)

`RULE SECTIONS: 9 applicable | 8 by change TYPE | 1 by recalled handle (h = 1) | 0 unanswered`

| Section | Source | Answer (what in *this* change it constrains) |
|---|---|---|
| R1.1 zero language branches | TYPE | The outline is read from the index; the hook never inspects a suffix to decide *how* to parse. |
| R1.2 one seam, YAGNI | TYPE | Two signals only — the field refused a third, and so does the code. |
| R1.3 dependency direction | TYPE | `hooks/` → `store`/`config`; nothing imports the hook back. |
| R4.1 no LLM/network in core | TYPE | The signal is an index lookup plus a git check. No model, no network. |
| R4.2 identical input → identical output | TYPE | Same index + same path ⇒ same line, byte for byte. |
| R6.4 guardrail tests are real | TYPE | The silence rule has **negative** tests, and they are made to fire. |
| R6.5 sweeps cover authored source, guarded against vacuity | TYPE | The two pinned `core_modules()` counts move 38 → 40 deliberately (LESSONS 072). |
| R7.1 ship the smallest useful thing | TYPE | A verdict plus one command; wiring stays the host's. |
| **R6.7 derived-not-listed** | **handle** | The silence rule keys off *which tool* and *whether the file is indexed* — derived from the store and the hook payload, not a hand-kept path list. |

### The verdict this ticket owes (decided, detail at Gate 2)

**Host hook — not a payload rider, not both.** `next_tool_suggestions` rides payloads the agent
receives *after asking*; the whole finding is that the agent never asks. The core cannot observe a
`Read`, and a suggestion on every payload is the 061 cost 097 already rejected. The channel that
*can* observe a Read is the host's hook surface, which code-atlas already ships twice (036, 053).
**Bound recorded:** this is the ceiling on 069/081-style description work — no description reaches
an agent that never opens the tool list.

### Blast radius

Two new modules under `code_atlas/` ⇒ **both pinned counts** (`test_core_is_language_agnostic.py:42`,
`test_sql_confinement.py:32`) move 38 → 40. LESSONS 072 is exactly this trap; it is in the change
list, not a surprise at the gate.

- **Gate 1 status:** awaiting confirm

---

## Phase 2 — Design

### The verdict (AC1) — host hook, not a payload rider

**Where the signal can honestly live: the host's hook surface. Not a payload rider. Not both.**

A payload rider (`next_tool_suggestions`) reaches the agent *after it asks a question*. The whole
finding is that the agent never asks — by the time it would query, it has already framed the task.
The core cannot observe a `Read`; a suggestion attached to every payload is the 061 cost that
**097 already rejected for this same signal**. So the rider channel is structurally incapable of
carrying this information, not merely expensive.

The hook surface *can* observe a Read, and code-atlas already ships that shape twice — `poke.py`
(036) and `refresh.py` (053), both console scripts, both documented as **manual install, never
auto-installed**. This ticket adds a third of the same kind and wires nothing.

**The bound this records (the point of the ticket):** no description reaches an agent that never
opens the tool list. That is the ceiling on 069/081-style routing work, and it is why 097's
recognition probe and this ticket are the same finding measured from two sides.

**Rejected alternatives:**
1. **Payload rider on `next_tool_suggestions`** — rejected above: cannot see a `Read`, and 061.
   (Also already rejected by 097; this ticket does not re-open it.)
2. **A new MCP tool the agent calls at read time** — rejected: it is another tool call, and the
   evidence is that *none of the three moments wanted a tool call*. Adding one answers a question
   nobody asked.
3. **code-atlas installs the hook itself** — rejected on ticket Constraint 5. Wiring is the host's
   decision; 036/053 set the precedent (`contrib/git/`, manual copy) and the docs say so plainly.
4. **A stateful "fire once per path per session" latch** — rejected: needs persistence, is wrong on
   the second session, and the field's cost cases are excludable *structurally* (below) with no
   state at all.

### The silence rule (R3/AC4) — structural, not stateful

§3 names exactly where an interruption destroys value. Each maps to a structural exclusion:

| Field's costly occasion | Encoded as |
|---|---|
| browser-probe output; ~40 CI shell results | tool is not `Read`/`Write` ⇒ silent (those are `Bash`) |
| "every `Write` during authoring" | `Write` to a path that **already exists** ⇒ silent (create only) |
| — | path not in the index ⇒ silent (nothing to say) |
| "past ~300 tokens I would skim it" | fewer than `_MIN_SYMBOLS` (5) ⇒ silent (not worth 150 tokens) |
| — | no index, or path outside the project ⇒ silent |

No session state, nothing to garbage-collect, and every rule is a negative test.

### The two lines (R4), and one correction to the ticket

- **Read →** `code-atlas: <rel> defines N symbols — name:line, name:line, … (+K more)`
- **Write (create) →** `code-atlas: <rel> is untracked — symbol queries answer `not_indexed` until
  it is committed and reindexed (092).`

**Ticket-text correction:** the Evidence table quotes the second signal as warning about
`no_such_symbol`. That was true when 099 was written; **092 shipped and changed it** — an untracked
indexable path now answers `not_indexed` + `try_instead=build_or_update_index`. The signal states
the *current* behaviour; saying `no_such_symbol` would ship a line the product no longer produces.

### Cost gate (C3)

Never builds, never reparses, never takes the write lock — it opens the store read-only and reads
`nodes_by_file`. When the file's hash no longer matches the index it still answers, appending
`(index may be behind)`: the ticket requires answering from the index as-is rather than blocking on
freshness. A read-time signal that needed a rebuild would not be a read-time signal.

### Change list (traced to matrix rows)

| # | Change | File | Traces |
|---|--------|------|--------|
| CL1 | the entry point: both signals, silence rule, token cap, no-build | `code_atlas/hooks/signal.py` *(new)* | R2, R3, R4, C1–C4 |
| CL2 | `estimate_tokens` — one definition site for the budget proxy | `code_atlas/tokens.py` *(new)* | C4, R6.7 |
| CL3 | import the shared estimator instead of defining a second one | `scripts/tokens_to_answer.py` | R6.7 |
| CL4 | `code-atlas-signal` console script | `pyproject.toml` | R2 |
| CL5 | budget · latency · both signals · silence negatives · guard-fails | `tests/test_write_time_signal.py` *(new)* | AC2, AC3, AC4 |
| CL6 | pinned core-module counts 38 → 40 | `tests/test_core_is_language_agnostic.py`, `tests/test_sql_confinement.py` | blast radius (LESSONS 072) |
| CL7 | verdict + wiring docs + 092 xref + retro recall row + PLAN/BACKLOG/LESSONS | docs, README | R1, R5, AC1, AC3, AC5, C5 |

### Rule-compliance check

`RULE SECTIONS: 9 applicable | 9 answered | 0 unanswered`

- **R1.1** — the hook reads symbols the index already holds; it never branches on language. ✅
- **R1.2** — two signals, no third; the field refused one and so does the code. ✅
- **R1.3** — `hooks/` imports `config`/`store`; nothing imports the hook back. ✅
- **R4.1** — an index lookup plus a `Path.exists()`; no model, no network. ✅
- **R4.2** — same index + same path ⇒ same line, byte for byte. ✅
- **R6.4** — every silence rule has a negative test, and the guard is made to fire. ✅
- **R6.5** — the two pinned counts move deliberately, in the change list (LESSONS 072). ✅
- **R7.1** — a verdict plus one command; wiring stays the host's. ✅
- **R6.7** (via recalled handle) — the budget proxy gets **one** definition site (CL2/CL3) instead of
  a second copy; the silence rule keys off the tool name and the store, not a hand-kept path list. ✅

`HANDLES: 3 recalled | 3 answered | 0 unanswered`

| Handle | Answer |
|--------|--------|
| 097-C2 (descriptions cannot make the agent notice) | **traced** — this ticket builds the workflow trigger 097 named; the verdict records the bound. |
| `derived-not-listed-invariant` (→ R6.7) | **traced** — one `estimate_tokens`, and the silence rule derives from tool name + index state. |
| `prove-the-guard-fails` | **traced** — a test asserts the signal **does** fire on the positive case, so the silence tests cannot pass vacuously. |

### Proving test

`pytest tests/test_write_time_signal.py::test_read_signal_names_the_symbols_within_the_budget`
— pins **both** AC2 bounds (≤ 150 tokens, < 1 s against a large index) on one call.

### Verification plan

1. `scripts/docker-test.sh` — full gate green, no test removed.
2. Silence negatives green, and the positive-fire test proves they are not vacuous.
3. `code-atlas-signal` importable as a console script (`pyproject.toml` entry).

- **Gate 2 status:** awaiting confirm

---

## Phase 3 — Execute

- **Branch:** `feat/099-write-time-signal-seam`
- **Proving test added:** `tests/test_write_time_signal.py` (14 tests)
- **Verification sweep:** file axis ✅ — diff is exactly CL1–CL7.
  - R1.1: no `if language ==` under `code_atlas/` ✅
  - R4.1: no network/LLM import in `signal.py` ✅
  - R1.4: SQL still only in `store.py` ✅
  - **C3 proven mechanically:** `grep -E "full_build|incremental_update|reparse_file|build_or_update"`
    over `signal.py` returns **nothing** — the entry point cannot build, it does not merely decline to.
- **The two pinned counts moved 38 → 40** and were verified to *fail first* (both guards fired on the
  new modules before the pins were touched) — LESSONS 072's trap, met deliberately.
- **Empirical:** `scripts/docker-test.sh` — ruff + mypy green; **1222 passed** (baseline **1204**;
  +14 signal tests, +4 from the two new modules entering the parametrized core sweeps).

## Resolution

**Verdict: the signal lives in the host's hook surface. Not a payload rider, not both.** The full
reasoning and four rejected alternatives are in the Design section above; the short form is that a
payload rider reaches the agent *after it asks*, and the finding is that it never asks.

**Shipped:** `code-atlas-signal` (console script; `code_atlas/hooks/signal.py`), the third hook of
the same shape as 036/053 — offered, never wired.

- **Read →** `code-atlas: <rel> defines N symbols — name:line, …` (≤ 150 tokens, hard cap).
- **Write (create) →** the untracked warning, in 092's *current* vocabulary.
- **Silence rule (structural, no session state):** any tool that is not `Read`/`Write`; a `Write` to
  a path that already exists; a file below `MIN_SYMBOLS`; an unindexed path; no index; a path
  outside the project.

**Hook events are not interchangeable, and the docs say so.** `Read` wants `PostToolUse` (the field
asked for the line *inside* the read result); `Write` wants `PreToolUse`, because create-vs-edit is
decided by whether the path exists and after a write it always does. A test pins that semantics so a
future reader cannot mistake the silence for a bug.

**One deliberate deviation from the ticket text.** Its Evidence table specifies the untracked line
should warn about `no_such_symbol`. That was true when 099 was written; **092 shipped and changed
it** to `not_indexed` + `try_instead=build_or_update_index`. The signal states what the product
actually does today — a test asserts `no_such_symbol` is *absent* from the line.

**The bound this records.** No description reaches an agent that never opens the tool list. That is
the ceiling on 069/081-style routing work, and it is why 097 (recognition) and 099 (position) are one
finding seen from two sides.

### Follow-ups (named, not dropped)

- **The falsifier is the next field round** (retro §0.6, added here): if the evaluator reports the
  signal `tuned out` at the shipped cap, this finding was session-specific and the seam should be
  reconsidered. Recording that is the point.
- **No third signal** until the field names one (R1.2). The interview explicitly refused to.

- **Gate 3 status:** cleared (autonomous) → review

## Phase 4 — Review ✋

Challenger **waived** at solve invocation (`with skipped challenge`). Reviewer pass run in the main
loop (0 dispatch — this host does not surface subagent usage).

**Verdict: CHANGES REQUESTED → fixed → clean.** Three findings from reading the diff:

1. **`hooks/signal.py` — the hook event was an unstated part of the contract.** The create-vs-edit
   test reads the filesystem, so wired at `PostToolUse` the `Write` signal is silent *by
   construction* — the file always exists by then. That is correct for an edit and useless for a
   create, and nothing said so. Fixed: the module docstring and the README now name the required
   events (`Read` → PostToolUse, `Write` → PreToolUse), and
   `test_the_write_signal_is_a_pre_tool_use_signal` pins the semantics so the silence cannot be
   misread as a bug later.
2. **`hooks/signal.py::_fit` — a stray leading comma when nothing fits.** A file whose first symbol
   already blows the budget produced `… — , +60 more`. Fixed, with
   `test_a_wide_file_that_fits_nothing_still_reads_cleanly`.
3. **`tests/test_write_time_signal.py` — an unused `capsys` fixture.** Removed.

The budget loop was also checked by hand for the off-by-one it invites: the reserved tail is one
count wider than the final one, so the emitted line is always ≤ cap. Conservative, and the two
budget tests pin it.

- **Reviewed at:** working tree at Phase 3 + the three fixes (files: `code_atlas/hooks/signal.py`,
  `code_atlas/tokens.py`, `tests/test_write_time_signal.py`, `scripts/tokens_to_answer.py`,
  `pyproject.toml`, the two pin updates)
- **Ph3/4 proven by:** `tests/test_write_time_signal.py` (14) · Docker full gate **1222 passed**

## Phase 5 — Finalise ✋

- Planned outward actions (standing AGENTS.md approval + this solve): commit, push branch, open PR.
- Durable lesson: `docs/LESSONS.md` — 099 entry + claims 099-C1/C2/C3.
- Revert: revert the PR commit; nothing is wired, so reverting removes an unused command.

### Learning loop

`CLAIMS: 3 claim(s) from 1 lesson entry | T1=0 T2=3 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded | 0 promotion candidate(s)`
`FALSIFY: 3 candidate(s) checked | 3 still-true | 0 falsified | 0 not cheaply checkable`
`PROMOTION: 0 proposed (all three are seen: 099 only — one sighting each)`

## Cost ledger

| Phase | Subagent / dispatch | Round | Tokens | Optimizer applied · est./measured saving |
|-------|---------------------|-------|--------|------------------------------------------|
| — | none dispatched (challenge waived; main-loop only) | — | n/a — 0 dispatches | RTK present, not depended on |

`LEDGER TOTAL: 0 dispatches, so 0 rows — complete, not empty by omission.`
`Top cost driver: main-loop reading of the hook precedent and the store surface (not measured by mango).`

## Decision log

| When | Decision | Why |
|------|----------|-----|
| Gate 1 | proceed; both pinned core-module counts flagged up front | LESSONS 072 — a count guard is invalidated by a file existing |
| Gate 2 | verdict = host hook; rider rejected as **structurally** incapable | the agent never asks; the core cannot see a `Read` |
| Gate 2 | silence rule structural, not stateful | every costly occasion §3 named is excludable without state |
| Ph3 | ship `not_indexed`, not the ticket's `no_such_symbol` | 092 shipped and changed it; the ticket text predates that |
| Gate 4 | hook-event contract documented + pinned by a test | silence at PostToolUse is by construction, not a bug |
| final | commit + push + PR | AGENTS.md standing + this solve |

## Session status

- **Last updated:** 2026-08-15
- **Current phase:** finalise
- **work_doc_mode:** embed · `docs/tasks/099_write-time-signal-seam.md`
- **Next action:** open the PR
- **Blocked on:** none
