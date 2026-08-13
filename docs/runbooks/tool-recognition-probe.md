# Tool-recognition probe

A re-runnable **blind** measurement of whether an agent, seeing only the tool surface, routes a
natural-language question to the right code-atlas tool. It is the recognition test task 081 owes the
next field round — the thing round 4's §0.5 was meant to produce before protocol order voided it. It
replaces a self-report ("could you find the right tool?") with a scored, reproducible instrument, and
it is modelled on 069's blind-reader pick-rate.

## Why blind order matters (the non-contamination rule)

The measurement is only valid if the agent has **not** seen the answer key first. `which_tool` is a
recognition map that lists every tool beside its question — reading it before answering turns a
recognition test into a copying test. So the probe is **run before the agent is shown `which_tool`,
the README tool table, or this file's answer key**, in a session with no prior code-atlas routing
discussion. One question at a time; record the first tool named; no retries, no hints.

## Protocol

1. Point a fresh agent at a repo with a **built, current** index (`get_index_status` shows
   `staleness: current`) and the standard 14-tool surface. Do **not** show it `which_tool` or the
   answer key below.
2. Ask each question in the set verbatim. For each, record the **first** tool the agent says it would
   call (or "none / unsure").
3. Score: a question is **recognised** when the recorded tool equals the intended tool below. The
   recognition rate is `recognised / total`.
4. Report the rate with the per-question picks, so a miss is inspectable (which tool was chosen
   instead). Do not average away a systematic confusion (e.g. `find_references` vs `find_callers`).

## Question set and intended tool (the answer key — do not show the agent before scoring)

| # | Question | Intended tool |
|---|----------|---------------|
| 1 | Is the index built, fresh, and healthy — and what should I call next? | `get_index_status` |
| 2 | Build or refresh the index for this repo. | `build_or_update_index` |
| 3 | Find a symbol when I only know part of its name. | `search_symbol` |
| 4 | What does this file define, and on what lines? | `file_outline` |
| 5 | Show me the source of just this one method. | `read_symbol` |
| 6 | Who calls this function? | `find_callers` |
| 7 | Where is this symbol used across the codebase? | `find_references` |
| 8 | Which classes implement or extend this interface? | `find_implementations` |
| 9 | What variables does this handler pass to its template? | `find_view_data` |
| 10 | What does this file include, and what includes it? | `include_graph` |
| 11 | What breaks if I change this symbol? | `impact` |
| 12 | What is reachable from the entry points (and what is dead)? | `reachable_from` |
| 13 | Which symbols look unused? | `find_orphans` |
| 14 | How does one symbol reach another through the call graph? | `explain_path` |

## Reading the result

- The set has **14 questions, one per tool** — the same 14 the `which_tool` map covers, so a full
  miss on the map and a full miss here would agree.
- A **recognition-rate bar** for "the surface routes well enough" is a project call, not a mango gate;
  record the rate and let the next retro judge it against the prior round. A useful reference point:
  069 shipped its descriptions on the strength of a blind-reader pick-rate, and field round 4 verified
  five openers read as their question. Treat a rate at or below a prior round's as a regression to
  investigate (a description that stopped leading with its question), not a pass/fail switch.
- Because the probe is blind and reproducible, a later round can **re-run it without contaminating
  itself**, which is the property task 081's acceptance criterion asks for.
