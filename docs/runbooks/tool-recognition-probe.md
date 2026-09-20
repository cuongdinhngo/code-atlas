# Tool-recognition probe

A re-runnable **blind** measurement of whether an agent, seeing only the tool surface, routes a
natural-language question to the right code-atlas tool. It is the recognition test task 081 owes
the next field round. Task 097 added the markings that stop a name-only 14/14 from being read as
an 081 score.

The retro template that consumes this probe is [`field-retro.md`](field-retro.md) §0.5.

## Why blind order matters (the non-contamination rule)

The measurement is only valid if the agent has **not** seen the answer key first. `which_tool` is a
recognition map that lists every tool beside its question — reading it before answering turns a
recognition test into a copying test. So the probe is **run before the agent is shown `which_tool`,
the README tool table, or this file's answer key**, in a session with no prior code-atlas routing
discussion. One question at a time; record the first tool named; no retries, no hints.

## Protocol

1. Point a fresh agent at a repo with a **built, current** index (`get_index_status` shows
   `staleness: current`) and record the **channels that actually reached it** (200 AC5, 2026-09):

   | Record or the round is void | Values |
   |---|---|
   | Surface | default 24 (`CA_TOOLS` unset) or FIELD18 six-tool — say which. Default is 24. |
   | Consumer brief (266) | `AGENTS.md` code-atlas brief section present / absent |
   | Skill (`contrib/skill`) | installed in the agent / not |
   | Resident descriptions | `K / 24` schemas in context (a name list is not this) |

   Do **not** show it `which_tool` or the answer key below. The shipped brief, if present, **is**
   product — do not strip it unless you are running an explicit no-brief control arm.
2. **Before scoring**, record **resident descriptions:** `K / 24`. This harness often defers MCP
   schemas — a name list is not a description set. A round with deferred names and `K = 0` cannot
   score 081 (write `NOT OBSERVED`); it also cannot close 200.
3. Ask each question in the **surface set** (one per tool) verbatim. Then ask the **occasion-fit
   set**. For each, record:
   - the **first** tool the agent says it would call (or "none / unsure");
   - whether that answer was **name-only** or **description-backed** (the intended tool's schema
     was in context when the agent answered).
4. Score **two rates** on the surface set, never one undifferentiated 24/24:
   - **name-inclusive** = `recognised / 24`. Label it as such. Round 5 reported the 14-tool
     equivalent, before `architecture_overview` joined the surface (086).
   - **description-backed** = `recognised among description-backed answers / D`, where `D` is the
     number of answers marked description-backed in step 3. This is the 081 proxy. `D` equals `K`
     only if residency held for the whole probe; when a schema loads mid-probe the step-3 markings
     win — report `D` and re-record `K`. If `D = 0`, record 081 as `NOT OBSERVED`. If `K < 24`, do
     **not** treat a name-inclusive full score as evidence that descriptions route.
5. Score **occasion-fit** separately: `first-tool ∈ occasion's acceptable tools` / 6. A full
   surface score with a miss on O6 is the field-16–30 miss (contract change, not rename) and **is**
   a 200 result. `fit_counts` (260) may be copied from `get_index_status` verbose after the round;
   it does not replace steps 4–5.
6. Report both rates with the per-question picks and markings, so a miss is inspectable. Do not
   average away a systematic confusion (e.g. `find_references` vs `find_callers`).

## Question set and intended tool (the answer key — do not show the agent before scoring)

| # | Question | Intended tool |
|---|----------|---------------|
| 1 | Is the index built, fresh, and healthy — and what should I call next? | `get_index_status` |
| 2 | Build or refresh the index for this repo. | `build_or_update_index` |
| 3 | Find a symbol when I only know part of its name. | `search_symbol` |
| 4 | I am about to port a thousand-line source file. I need its symbols and line ranges without reading the body, so I do not count functions by hand. | `file_outline` |
| 5 | Show me the source of just this one method. | `read_symbol` |
| 6 | Who calls this function? | `find_callers` |
| 7 | Where is this symbol used across the codebase? | `find_references` |
| 8 | Which classes implement or extend this interface? | `find_implementations` |
| 9 | What variables does this handler pass to its template? | `find_view_data` |
| 10 | What does this file include, and what includes it? | `include_graph` |
| 11 | What breaks if I change this symbol? | `impact` |
| 12 | Can this directory subtree be deleted — what still crosses into or out of it? | `subtree_dependencies` |
| 13 | What is reachable from the entry points (and what is dead)? | `reachable_from` |
| 14 | Which symbols look unused? | `find_orphans` |
| 15 | How does one symbol reach another through the call graph? | `explain_path` |
| 16 | I have never opened this codebase. What are its top-level parts, and which depends on which? | `architecture_overview` |
| 17 | I have never opened this codebase. What should I read first, in dependency order? | `guided_tour` |
| 18 | Write the onboarding docs I can commit: an overview, a reading order, the request flows and a manifest. | `generate_onboarding` |
| 19 | Do the declared architecture dependency rules still hold? | `check_architecture_rules` |
| 20 | What did the agent change about the architecture between two revisions? | `diff_architecture` |
| 21 | Draw the class diagram for this type (or this file's types). | `class_diagram` |
| 22 | Which modules does this change reach, and which one do I look at first? | `impact_modules` |
| 23 | Which writers of this table leave a column to its DEFAULT? | `check_column_defaults` |
| 24 | What happens when a user does this — what does one request touch, entry to data? | `trace_capability` |

### Why Q4 discriminates (task 097)

Q4 is phrased in the user's occasion, not the tool's name or opener. A bare name list that
answers `read_symbol` or the host `Read` is a **miss** — those names look like "read the file."
The description is what says this tool returns the symbol map **without** the body. Round 5's
Q4 ("What does this file define, and on what lines?") was close enough to the opener that a
name-only pass still scored it. This shape is the one a name list can fail.

Scoring **only** over description-backed answers (step 4) is what makes 081 re-scorable. User-worded
Q4 is what makes the *set* able to fail a name-only pass. Near-miss pairs (`find_callers` vs
`find_references`) stay in the set as a confusion watch; they are not the 081 discriminator —
round 5 already separated those off names.

## Occasion-fit set (200 AC5 — do not show before scoring)

Not one-per-tool. Acceptable first tools are listed; a name from the 24-Q key that is outside the
list is a miss. Row ids are `O*`, so they do not join the surface-coverage table.

| Id | Question | Acceptable first tools |
|----|----------|------------------------|
| O1 | Before I rename this symbol, who still calls it? | find_callers, find_references, impact |
| O2 | I just edited indexed files. Is the graph still talking about this revision, and what did that change reach? | get_index_status, find_callers, impact |
| O3 | First hour in this repo — is the index usable, and what is the shape? | get_index_status, architecture_overview |
| O4 | This name exists in two languages. Can I treat a PHP hit as the whole answer? | search_symbol, get_index_status |
| O5 | I need a blast-radius sentence I can paste on the PR and re-run. | find_callers, impact, get_index_status |
| O6 | I am changing what this function **returns** for an input it used to reject. The name stays. Who still depends on the old contract? | find_callers |

O1–O5 match the shipped 266 brief. **O6 is the discriminator the brief does not name** (field: the
agent called `find_callers` on a sibling, then widened a return contract without asking). A miss on
O6 with a hit on O1 is a brief-gap result, not a surface-gap result.

## Reading the result

- The set has **one question per tool** — the same set the `which_tool` map covers, so a full
  miss on the map and a full miss here would agree. It grows with the surface; keep it one-per-tool.
- A **recognition-rate bar** for "the surface routes well enough" is a project call, not a mango
  gate; judge the **description-backed** rate against the prior round. A name-inclusive full score
  with `K` below the tool count is saturated names, not a pass.
- Because the probe is blind and reproducible, a later round can **re-run it without contaminating
  itself**.
- This file is a protocol, not a benchmark harness. 055 and 074 own measurement infrastructure.
