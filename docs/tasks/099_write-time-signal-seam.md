---
id: 099
slug: write-time-signal-seam
title: 'Every decision the agent made without the graph wanted one line inside a file read, not a tool call'
phase: 1.5b
milestone: Agent-fit
status: todo
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
