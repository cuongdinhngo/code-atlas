---
id: 343
slug: server-instructions-truncated-at-2048-chars
title: 'Claude Code cuts the server instructions at ~2,048 characters — KEEP_GOING and LIMITS never arrive'
phase: 2
milestone: Adoption
status: done
depends_on: [300]
---

## Why this exists

[300](../PLAN.md#19-project-context--decision-log) made the server's `instructions` the one routing
channel that needs nothing installed in the consumer repo. On Claude Code that channel is capped, and
`instructions.render` overruns the cap by half, so the model receives only a prefix of it.

## Evidence (anchor repo, 2026-09-29, server at `4c913e5`)

- `instructions.render(config, main.TOOL_NAMES)` on the anchor index: **3,047 characters**. The
  parts measure WHY 300 · LOAD 320 · recognition map 1,780 · KEEP_GOING 175 · LIMITS 412, plus the state
  line.
- The copy that reached the session's system prompt ends mid-line at **character 2,045**:
  `- Write committable onboarding docs (overvi… [truncated]`.
- KEEP_GOING starts at character 2,458 and LIMITS at 2,635, so **neither has ever reached a Claude
  Code session**. LIMITS is the sentence that stops the confident wrong answer ("the graph cannot answer
  an ABSENCE"), and KEEP_GOING answers 300's held-out H4, where a session called the index once and
  then did 29 grep/read calls. Both are exactly the sentences 300 wrote the channel for.
- `tests/test_server_instructions.py` checks content, not length, so nothing catches the overrun.
- The state line is frozen at `initialize`: the session showed `incomplete @ e3f4427` for its whole
  length, long after the build finished. 322's `code-atlas-state` hook covers this, but only where
  someone installed it (see 344).
- 200 is `blocked` on its own measurement; this fix has its own evidence and does not wait on it.

The cap was observed, not read from Claude Code's docs. AC1 measures it rather than assuming 2,048.

## Scope

1. **Priority order, not document order.** Render in this order: state line → LOAD → one sentence
   that fuses WHY and LIMITS (index for resolved who/what/where, Grep for literal text **and for
   absence**) → KEEP_GOING → the recognition map. Whatever the cap cuts is then the least important
   part. The fusion drops LIMITS' first half (read a non-ok `reason` and the coverage fields); that
   half is claimed to ride every tool result already (`tools/coverage.py`, `tools/collection.py`);
   AC3c proves that before the sentence is dropped, and the module docstring says where it went.
2. **Shrink the map for this channel.** Keep the full map in the skill (`gen_skill.py`) and put a
   subset here: the rows flagged `core` on `RECOGNITION_MAP` itself (callers, references, read,
   impact, search, outline, include_graph, explain_path). R6.7 still holds: the subset is a filter
   over that tuple, never a second copy. Until 344 installs the skill, a session without it loses the
   unflagged rows — accepted, since the `core` rows are the questions the field asks.
3. **LOAD names the working set.** Today it tells the client to load two tools, so the first
   `find_callers` costs a second ToolSearch round. Name the core set (`get_index_status`,
   `search_symbol`, `read_symbol`, `find_callers`, `find_references`, `impact`) in the one `select:`
   string, filtered by the registered `names` exactly as the map is: a `CA_TOOLS` that drops a tool
   drops it from LOAD too, since a name the session cannot call is worse than none.

## Acceptance criteria

- **AC1:** The client cap is measured on a running Claude Code (long padded `instructions`, then
  read back where the cut lands) and recorded as a named constant along with the version it was
  measured on.
- **AC2:** The rendered `instructions` fit under that constant minus a 200-character margin (the
  state line varies with sha and counts) on every index state (unindexed, behind, current,
  incomplete) and with `CA_TOOLS` unset. A test pins it.
- **AC3:** A test asserts the order: the LIMITS/absence sentence and KEEP_GOING come before the first
  map line.
- **AC3b:** A test asserts every map line in `instructions` is a `core` row of `RECOGNITION_MAP`.
- **AC3c:** A test asserts every tool result carries `reason` and the coverage fields that LIMITS'
  dropped half names; if any tool lacks them, that half stays in `instructions`.
- **AC3d:** With `CA_TOOLS` cutting a core tool, a test asserts LOAD's `select:` string omits it.
- **AC4:** A fresh Claude Code session on the anchor repo shows the whole `instructions` block with
  no `[truncated]` marker, on the Claude Code version AC1 recorded.

## Out of scope

- Hosts other than Claude Code. Record their caps if known, but don't design for them here.
- Refreshing the state line mid-session. MCP has no push for `instructions`; that job belongs to the
  hook (322, 344).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 343 · **work_doc_mode:** embed · **Current phase:** 3 execute · **Next action:** review.
- `TRACK: backend` · `TIER: full` · `SCOPE: S` · `STRUCTURE: native` · Run mode: `autorun` (unattended, stops at the PR). Run arg *"with skipped
  reviewer"* = `--no-reviewer` only; the ticket-blind challenger keeps its seat.
- Contract `.mango/run-contract-343.txt`. RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN
  | 2 UNBOUND | 0 could-not-run — every bound condition failing before any work exists.

## Phase 0 — refine

`PREMISE: 12 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

The ticket was re-scoped in PR #5; every open point left is a HOW. `LESSONS.md` holds no live claim
since the phase-1 reset, so recall surfaces nothing.

## Phase 1 — analysis

`PREMISE: 12 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Evidence, Scope, Acceptance criteria, Out of scope) | 5 decomposed | ROWS: C=5 R=5 G=1 AC=7`
`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/6 touched files under UI paths`
`BASELINE: green`
`SCOPE: S`
`TIER: full`

Both counting lines above `SECTIONS:` are carried forward from Phase 0. `TIER: full` although
`SCOPE: S`: AC2 is universal over N = 5 index states, so the lite lane does not apply.

### BASELINE — `config.test_command` on the untouched checkout

`.venv/bin/python -m pytest -q -p no:cacheprovider`, in a clean worktree of the branch point.
Ran at e58d8c13

```
3984 passed, 4 skipped in 379.03s (0:06:19)
```

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Why | "the model receives only a prefix of it" | KEEP_GOING and LIMITS reach a Claude Code session whole | measured: 3,094 chars rendered, 2,048 delivered (below) | open |
| C1 | Evidence | "checks content, not length" | a length guard is missing | `tests/test_server_instructions.py` — no `len(` | open |
| C2 | Evidence | "The state line is frozen at `initialize`" | context only; the fix is 322/344 | `code_atlas/hooks/state.py` | n/a — out of scope |
| C3 | Evidence | "does not wait on it" | no dependency on 200 | frontmatter `depends_on: [300]` | met |
| C4 | Out of scope | "Hosts other than Claude Code" | design for one cap only | — | constraint |
| C5 | Out of scope | "Refreshing the state line mid-session" | no push mechanism added | — | constraint |
| R1 | Scope 1 | "state line → LOAD → … → KEEP_GOING → the recognition map" | render order changes | `instructions.py:58` renders WHY, LOAD, map, KEEP_GOING, LIMITS | open |
| R2 | Scope 1 | "one sentence that fuses WHY and LIMITS" | WHY and LIMITS' absence clause become one sentence | `instructions.py:13-18,37-43` | open |
| R3 | Scope 1 | "say so in the module docstring" | docstring names where LIMITS' first half went | `instructions.py:1-6` | open |
| R4 | Scope 2 | "rows flagged `core` on `RECOGNITION_MAP` itself" | a flag on the tuple, subset = a filter over it | `tools/prompts.py:23` 3-tuples; unpacked at `prompts.py:80`, `tests/test_server_instructions.py:23` | open |
| R5 | Scope 3 | "Name the core set … filtered by the registered `names`" | LOAD's `select:` string lists the six, minus any `CA_TOOLS` cut | `instructions.py:24-27` names two | open |
| AC1 | AC | "measured on a running Claude Code … recorded as a named constant along with the version" | a constant + version | measured below: 2,048 on Claude Code 2.1.284 | open |
| AC2 | AC | "fit under that constant minus a 200-character margin … on every index state" | `len(render) <= 1,848` for N = 5 states, `CA_TOOLS` unset | today 3,094 | open |
| AC3 | AC | "the LIMITS/absence sentence and KEEP_GOING come before the first map line" | index order test | — | open |
| AC3b | AC | "every map line in `instructions` is a `core` row" | derived from the flag (R6.7) | — | open |
| AC3c | AC | "if any tool lacks them, that half stays in `instructions`" | the premise does not hold → the half stays | 3 of 24 tool modules never name `reason` | open |
| AC3d | AC | "LOAD's `select:` string omits it" | test with `CA_TOOLS` cutting a core tool | — | open |
| AC4 | AC | "shows the whole `instructions` block with no `[truncated]` marker" | re-run the AC1 probe against the built server | — | open |

### AC validation — every value re-derived, and its falsifiability

| AC | Ticket value | Re-derived | Falsifiable? |
|---|---|---|---|
| AC1 | "~2,048"; anchor copy "ends … at character 2,045" | **2,048** exactly, twice. (1) this session's own copy of the code-atlas instructions stops at char 2,048 of the 3,094-char render; (2) a padded probe server (`%08d\|` cells, one per 9 chars) through `claude -p --strict-mcp-config` on **Claude Code 2.1.284** returned `…00002043\|00002… [truncated]` — cell 2,043 plus 5 chars = 2,048. The anchor's 2,045 was an eyeballed position; the ticket told AC1 to measure rather than assume, so this is the ticket's own procedure, not a silent correction | yes — the probe is re-runnable |
| AC2 | cap − 200 | 2,048 − 200 = **1,848**. Worst state line today: the schema-mismatch form, ~115 chars at 7-digit counts | yes — `len()` |
| AC3 / 3b / 3d | ordering, subset, omission | — | yes — string index / set membership |
| AC3c | "every tool result carries `reason` and the coverage fields" | **does not hold**: coverage fields are omit-when-empty (`tools/coverage.py:135-157`), and `find_orphans.py`, `reachable_from.py`, `subtree_dependencies.py` never name `reason` | yes — the fallback is asserted as present text |
| AC4 | no `[truncated]` | — | yes — the AC1 probe, pointed at this server |

### Clarifications — all five self-resolved, each cited

1. **Measured cap vs the ticket's 2,045.** 2,048, measured on 2.1.284 (table above); ticket AC1
   *"measures it rather than assuming 2,048"*.
2. **Where the constant lives.** `code_atlas/instructions.py` — the one module that renders the
   channel it bounds (R1.8, one decision, one implementation).
3. **Form of the `core` flag.** A 4th field on each `RECOGNITION_MAP` row — ticket Scope 2
   *"flagged `core` on `RECOGNITION_MAP` itself … never a second copy"*.
4. **AC3c's premise.** Not established (table above), so the ticket's own fallback applies: LIMITS'
   first half stays, compressed — ticket AC3c *"if any tool lacks them, that half stays"*.
5. **`get_index_status` is not a `core` map row.** Scope 2 lists eight tools verbatim; the state line
   and LOAD already name it — ticket Scope 2–3.

### Universal inventory — N = 5 index states (AC2)

1 unindexed · 2 schema mismatch · 3 behind · 4 current · 5 any other staleness (the anchor's
`incomplete`) — the five branches of `_compose_summary` (`tools/get_index_status.py:311-338`).
Per-item: review confirms each state, not a total.

### Gap analysis (enhancement)

Current: `render` emits WHY 300 · LOAD 320 · 25-line map · KEEP_GOING 175 · LIMITS 412 in document
order (`instructions.py:58`), 3,094 chars; Claude Code keeps 2,048, so KEEP_GOING (from char 2,458)
and LIMITS (from 2,635) never arrive. Target: ≤ 1,848 chars in priority order.

### Blast radius

`code_atlas/instructions.py` (render) · `code_atlas/tools/prompts.py` (`RECOGNITION_MAP` shape +
`recognition_lines`) · consumers of the tuple: `prompts.py:80`, `tests/test_server_instructions.py:23`;
`scripts/gen_skill.py` reads the rendered `which_tool` text, not the tuple — unaffected. Docs: README
§"Routing ships with the server", PLAN §"Operator prompts are not agent routing". `config.repos`: `app`.

### Rule sections

`RULE SECTIONS: 9 applicable — 9 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the core filter keys on a map flag and names no language, §R1.8 (change-type) ✅ the cap and the working set live once (instructions.py, main.FIELD18_TOOLS), §R4.2 (change-type) ✅ render stays a pure function of state and names, §R6.1 (change-type) ✅ tests extend test_server_instructions.py, §R6.5 (change-type) ✅ the cap guard is red on the 3094-char render of today, §R6.7 (change-type) ✅ the subset guard derives from the flag and lists nothing, §R6.9 (change-type) ✅ AC4 asserts at the consumer (a live Claude Code), §R7.2 (change-type) ✅ BACKLOG status and TOKEN_LEDGER row in the finishing commit, §R7.6 (change-type) ✅ README and PLAN sentences replaced and not appended`

N/A: §2 because no adapter is touched · §3 because no contract field or version moves · §5 because
no error path changes · §8 because no dependency is added. R7.5 (comments ≤ 3 lines) is checked at execute.

## Phase 2 — design

### Approach

1. **Flag the map.** Each `RECOGNITION_MAP` row gains a 4th field, `core: bool`, true on the eight
   Scope-2 rows; `recognition_lines(names, core_only=False)` filters on it. `which_tool` and
   `gen_skill.py` keep the full map unchanged.
2. **Name the cap.** `instructions.CLIENT_CAP = 2048` (Claude Code 2.1.284, measured 2026-09-29) and
   `CAP_MARGIN = 200`.
3. **Render in priority order:** state line → LOAD → SCOPE (WHY fused with LIMITS' absence clause)
   → COVERAGE (LIMITS' first half, compressed — it stays, AC3c) → KEEP_GOING → the `core` map lines.
4. **LOAD names the working set.** `render(config, names, working_set)`; `main.build_server` passes
   `main.FIELD18_TOOLS` (the ticket's six, already the 268 preset — R1.8, no second list). The
   `select:` string lists `working_set ∩ names`, falling back to `names` when that is empty.
5. **Docstring** says the full map lives in `which_tool` and the skill, and why COVERAGE stayed.
6. **Tests** in `tests/test_server_instructions.py`: cap on N = 5 states, order, `core` subset,
   `CA_TOOLS` omission from LOAD; the three existing tests the change invalidates are updated.
7. **Docs:** the README and PLAN sentences that say instructions carry "the map" are replaced.

### Rejected alternatives

- **Trim the prose, keep document order.** Fits today, but the next added row pushes the tail —
  KEEP_GOING and LIMITS again — out first. Priority order makes the cut land on the least important
  part.
- **A separate `CORE_TOOLS` frozenset.** A second list naming tools beside the map; ticket Scope 2
  asks for the flag on the tuple itself, so the subset stays a filter (R6.7).
- **Drop LIMITS' first half, as Scope 1 proposed.** Its premise failed in analysis (coverage fields
  are omit-when-empty; 3 tool modules never name `reason`); the ticket's AC3c fallback keeps it.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| A1 | Claude Code keeps a 2,048-character **prefix** and appends `… [truncated]` | verified — padded probe, Phase 1 |
| A2 | The cap counts characters (code points), not bytes | verified — this session's cut fell at char 2,048 of a text holding multi-byte `—`/`·` |
| A3 | A later Claude Code may change the cap | out of scope (C4); the constant carries its version |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `core` field on each row; `core_only` filter | `code_atlas/tools/prompts.py` | `recognition_lines` callers: `instructions.render`, `which_tool`; tuple unpacking at `prompts.py:80` | R4, AC3b | 1/1 |
| 2 | `CLIENT_CAP`, `CAP_MARGIN`, SCOPE/COVERAGE text, priority order, `working_set` LOAD, docstring | `code_atlas/instructions.py` | the one caller `main.build_server:107`; tests calling `render` | G1, R1, R2, R3, R5, AC1 | 1/1 |
| 3 | pass `FIELD18_TOOLS` to `render` | `code_atlas/main.py` | none identified beyond `build_server` | R5 | 1/1 |
| 4 | new guards + update the 3 tests the change invalidates (`ALL_TOOLS` unpack, `test_the_map_has_one_definition_site`, every `render(…)` call gains `working_set`) | `tests/test_server_instructions.py` | proof collateral | AC2, AC3, AC3b, AC3c, AC3d, C1 | 5/5 |
| 5 | replace the "carries the map" sentences | `README.md`, `docs/PLAN.md` | docs only (R7.6) | R3 | 2/2 |
| 6 | status + ledger rows | `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, this file | bookkeeping tests | R7.2 | — |

Test blast radius, traced. Ran at e58d8c13

```
$ grep -rn "RECOGNITION_MAP\|recognition_lines\|instructions.render" code_atlas scripts tests --include=*.py
code_atlas/tools/prompts.py:23  RECOGNITION_MAP: tuple[tuple[str, str, str], ...] = (
code_atlas/tools/prompts.py:80  for question, tool, note in RECOGNITION_MAP
code_atlas/instructions.py:57   lines = prompts.recognition_lines(frozenset(names))
code_atlas/main.py:107          instructions=instructions.render(config, names)
tests/test_server_instructions.py:23  ALL_TOOLS = tuple(tool for _q, tool, _n in prompts.RECOGNITION_MAP)
```

`scripts/gen_skill.py` parses the rendered `which_tool` text (`gen_skill.py:58-62`), not the tuple —
unaffected, and the `which_tool` body is unchanged.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

### Rule compliance

R1.1 no language named · R1.8 the working set is `FIELD18_TOOLS`, not a copy · R4.2 `render` stays
pure · R6.5 the cap guard is red on today's 3,094-char render · R6.7 the subset guard derives from
the flag · R6.9 AC4 asserts at the consumer (a live Claude Code) · R7.5 comments ≤ 3 lines · R7.6
README/PLAN sentences replaced. CONVENTION: naming follows `instructions.py`'s upper-case constants.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | runtime/3p | manual-recorded — padded probe via `claude -p` on 2.1.284 (Phase 1) | n/a | ✅ |
| AC2 | logic | unit — `len(render)` ≤ 1,848 on 5 states | n/a | ✅ |
| AC3 | logic | unit — index order | n/a | ✅ |
| AC3b | logic | unit — map lines ⊆ `core` rows (derived) | n/a | ✅ |
| AC3c | logic | unit — COVERAGE text present | n/a | ✅ |
| AC3d | logic | unit — `CA_TOOLS` cut drops the name from LOAD | n/a | ✅ |
| AC4 | runtime/3p | manual-recorded — the same probe against this repo's server after the change | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_server_instructions.py -k "fit_under_the_client_cap"` —
fails on today's render (3,094 > 1,848), passes after.

### Rollback + porting

`git revert` the branch's commits, or close the PR unmerged. One repo (`app`); nothing to port.

`SCOPE: S` — unchanged from analysis.

## Phase 3 — execute

Branch `fix/343-server-instructions-cap`. Commits: `b44fcb0d` (code + tests), `c6f80671` (README,
PLAN), `39eb5bd6` (review fix: the `which_tool` string restored, LOAD's fallback tested).

**Proving test — red before, green after.** Pre-change it failed on the missing constant
(`AttributeError: CLIENT_CAP`); the length red is the Phase-1 measurement, 3,094 > 1,848 on the
untouched render. After:

Ran at 39eb5bd6

```
$ .venv/bin/python -m pytest -q tests/test_server_instructions.py -k fit_under_the_client_cap
1 passed, 12 deselected in 0.43s
```

**AC4 — the consumer.** A fresh `claude -p --strict-mcp-config` session on Claude Code 2.1.284,
pointed at this branch's server, asked to quote the tail of the code-atlas instructions:

Ran at c6f80671

```
if I change this -> impact.
- How does one symbol reach another -> explain_path.
WHOLE. The block has no truncation marker and ends on the `explain_path` routing line.
```

`c6f80671` → `39eb5bd6` changed only a `which_tool` line layout and a test — the rendered
instructions are byte-identical, so the probe stands for the tree under review.

**Sweep — axis 1, file set.**

Ran at 39eb5bd6

```
$ git diff --stat main..HEAD
 README.md                         |  8 ++--
 code_atlas/instructions.py        | 65 +++++++++++++++----------
 code_atlas/main.py                |  4 +-
 code_atlas/tools/prompts.py       | 67 ++++++++++++++++----------
 docs/PLAN.md                      |  6 ++-
 tests/test_server_instructions.py | 99 ++++++++++++++++++++++++++++++++++-----
$ .venv/bin/ruff check .
All checks passed!
$ .venv/bin/mypy code_atlas
Success: no issues found in 95 source files
```

Every file is on the change list (items 1–5; item 6 is the bookkeeping commit). Every
`recognition_lines(` / `instructions.render(` call site passes the new arguments (grep, 25 hits, 0
stale). `ruff format` rewrote four untouched spots (two `main.py` calls, a `which_tool` string, a
test lambda); all four were reverted — the format-scope rule.

**Sweep — axis 2, design conformance.** Approach 1–7: implemented-as-approved. One note, not a
deviation: LOAD's empty-working-set fallback (Approach 4) had no test until the challenger named it;
added in `39eb5bd6`.
