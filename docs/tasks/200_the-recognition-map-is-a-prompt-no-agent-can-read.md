---
id: 200
slug: the-recognition-map-is-a-prompt-no-agent-can-read
title: 'The recognition map is an operator prompt no model can read, and the one channel a model does see is wired for one agent and one language'
phase: 1.5b
milestone: Adoption
status: blocked
depends_on: [081, 097, 036, 099, 260]
---

## Why this exists

[081](081_routing-prompts-are-not-in-the-agents-surface.md) settled the finding this ticket extends:
a client exposes only **tools** to the model, never prompts — `TOOLS.md` states it as decided,
*"an agent's client exposes only the tools above to the model, so a model never sees a prompt"*.

`which_tool` is an MCP prompt. It is also the only artifact in this repo that maps a
natural-language question onto a tool **across all 24 tools** — written for a model, living in the
one channel a model cannot read. 081's answer was to move routing into the tool descriptions
themselves (069), which is correct and is where routing belongs. What 081 did **not** do is give the
map a channel of its own, because at the time none existed that did not mean wiring code-atlas into
somebody's editor.

One exists now and it does not cross that line. An **Agent Skill** is a file a *user* installs into
their own agent; it loads on demand when the agent recognises a matching task, costs nothing in a
session that never triggers it, and is read by any agent supporting the format. code-atlas emits a
file; the host decides. That is the same posture the hooks already take — *"code-atlas does not wire
itself into anyone's editor"* (`TOOLS.md`, 036/099) — and this ticket does not change it.

**The second defect is rot in the one channel that does reach a model.**
`contrib/claude-code/settings.snippet.json` filters on `"if": "Edit(*.php)|Write(*.php)"`. That was
right at [036](036_edit-index-hook.md), when PHP was the only adapter. Adapter #2 (TS/JS, 019) and
adapter #3 (T-SQL, 184 + 022) have landed since, and `adapter.shipped_adapters()` now returns three
directories: **a TypeScript edit drifts the index and nothing pokes it.** The same file is also the
only snippet in `contrib/` — a Codex or OpenCode user is offered nothing, though both have a
documented session-hook surface.

Neither defect is a payload defect, so none of the Agent-trust work reaches either. Both are
**recognition** defects — and recognition is the one thing this repo already knows how to measure:
[097](097_recognition-probe-measures-names-not-recall.md) taught the blind probe to separate a
name-only answer from a description-backed one, so it can score whether any of this moved anything.

## Scope

1. A generated `SKILL.md` — the `which_tool` map plus the tool table — emitted from the **same
   source those already come from**, so the skill cannot describe a surface the server does not
   serve. Drift guarded by a test, in the shape `test_documented_tool_count.py` already uses.
2. The Claude Code poke snippet covers **every shipped adapter**, not a filter frozen at 036.
   `adapter.shipped_adapters()` is the static list and `adapter.py`'s handshake is the suffix
   source; the snippet is checked against one of them, never re-typed beside them.
3. Session-hook snippets for **Codex** (`hooks.json`, `[features].hooks = true`) and **OpenCode**
   (managed plugin) beside the Claude Code one, carrying the same `code-atlas-poke` /
   `code-atlas-signal` commands. Snippets and a README — offered, never installed.
4. A blind recognition-probe round before and after.

### Explicitly not in scope

- **An installer, a `setup` command, or anything that writes to a user's agent settings.** 036 and
  099 both settled this and `TOOLS.md` states it. The external principle this ticket borrows asks
  for a setup command; this repo's answer is stricter and stays stricter.
- **Rewriting tool descriptions.** That is 069's surface and routing lives there. The skill carries
  the map, not a second set of descriptions that can disagree with the first.
- **Output format.** TOON, exit codes and a shell surface are a separate question with a separate
  gate; nothing here changes a payload byte.
- **Publishing the skill anywhere.** Generating and committing it is this ticket; distribution is a
  maintainer decision taken after the probe reports.

## Constraints

- **No core change.** `code_atlas/` gains nothing: the generator is a script plus a test, the
  snippets are `contrib/`. R1.1, R1.4 and R4.1 are untouched by construction — and the diff must
  show it.
- **Single source, or it rots exactly as 036's filter did.** A hand-kept skill is the defect this
  ticket is fixing, one file over. Derive it or check it; never re-type it.
- **The skill is static.** No live state — index freshness, symbol counts, open work — may appear in
  it. That is the hooks' job, and a stale number in a committed file is a wrong answer, not a stale one.
- **R7.6, and the room is already gone.** `BACKLOG.md` is at 8,134 tokens against 8,200 and
  `CONVENTION.md` sits exactly on 6,600. This ticket's backlog row fits; any prose it wants in a
  standing doc does not, and must prune first or argue a raise in the PR.

## Acceptance criteria

1. `SKILL.md` is generated, and the drift test goes **red when either side is mutated** — proven by
   mutating each, not asserted.
2. A shipped adapter with no coverage in the poke snippet fails a test. Proven by adding a fourth
   adapter directory in a fixture and seeing it red, so the 036 rot cannot recur silently.
3. Codex and OpenCode snippets exist, each naming the file it belongs in, each installable by hand
   from the README, and no code-atlas command writes to any of them.
4. `code_atlas/` is byte-unchanged; R4.1's grep-gate is still green.
5. A blind probe round is recorded **before and after**, per
   [`runbooks/tool-recognition-probe.md`](../runbooks/tool-recognition-probe.md) and 097's
   name-only / description-backed split. **A round that does not move is a result, not a failed run
   to be repeated** — if the skill changes no score, this ticket says so in writing and the skill is
   reconsidered rather than kept for its own sake.
6. Nothing in `contrib/` claims a language this repo cannot index.

## References

[081](081_routing-prompts-are-not-in-the-agents-surface.md) (prompts are not in the agent's
surface), [097](097_recognition-probe-measures-names-not-recall.md) (the probe that can score this),
[036](036_edit-index-hook.md) (the snippet, and the never-installed stance),
[099](099_write-time-signal-seam.md) (the read-time signal, and the field evidence that the
decisions that most needed code-atlas wanted one line and no tool call),
[159](159_get-index-status-does-not-name-available-but-unconfigured-adapters.md) (the Adoption
theme, and `adapter.shipped_adapters()`).
External: principle 7 of the AXI skill, [kunchenguid/axi](https://github.com/kunchenguid/axi) — the
source of the skill-plus-hook shape, taken here without its installer.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 200 · **work_doc_mode:** embed · **Current phase:** 5 finalise — complete on disk. PR [#243](https://github.com/cuongdinhngo/code-atlas/pull/243) open. **Next action:** merge #243, then run the blind probe round (E1) to close AC5. **Revert path:** `git revert` the four commits on `feat/200-…`, or close #243 unmerged.
- **2026-09-13 — `depends_on` gains [260](260_the-fit-number-cannot-be-observed-only-benchmarked.md).** AC5's round is a hand-tally of every tool call in a session; 260's local counter accrues that tally while the server is used normally. It does **not** satisfy AC5 — blind and before/after is not passive and one-armed — so the round still runs. It runs cheaper, and after 260.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · **Type:** enhancement.
- Run arg: *"with skipper reviewer"* = **reviewer seat only** (AGENTS.md *Honor the run's args*); the
  ticket-blind challenger keeps its seat.
- Run mode: `autorun` (unattended lifecycle, stops at the PR — it never merges).
- Contract `.mango/run-contract-200.txt`. RECONCILE t0: 8 declared | 6 re-run | 0 holding | 6 BROKEN
  | 2 UNBOUND | 0 could-not-run — every bound condition failing before any work exists.

## Phase 0 — refine

`PREMISE: 14 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 1 by handle | 4 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`REFINE: 4 unresolved surfaced | 1 want-decision asked | 3 how-decision resolved+cited | 0 ASSUMED | skip: no`

The one ambiguous premise reference is **external** — principle 7 of `kunchenguid/axi`, a URL rather
than a checkout identifier. Surfaced, never blocking: nothing in the change list resolves against it.

**Settled want — asked, and answered by the maintainer.**

| # | The want | Answer | Consequence |
|---|----------|--------|-------------|
| W1 | AC5 asks for a blind recognition-probe round *before and after*. The runbook's protocol needs a fresh agent on a **live MCP surface** with a built index; this session has no code-atlas MCP tools connected, so the measurement cannot honestly be taken. What counts as satisfying AC5 here? | **Ship the rest; record AC5 as a gap.** | ACs 1–4 and 6 are met in full. **AC5 is a recorded coverage-gap exclusion with an expiry**, named in the PR body and in DISCLOSURE. The ticket does **not** close as fully met, and 200 stays open on AC5 alone. |

**Resolved + cited.**

| # | HOW-decision | Resolution | Citation |
|---|--------------|------------|----------|
| H1 | Where does the generated `SKILL.md` live? Scope 1 never names a path. | **`contrib/skill/SKILL.md`**, generated by `scripts/gen_skill.py`. `contrib/` is the repo's offered-never-installed shelf and already holds `claude-code/` and `git/`; the skill is **agent-neutral** by the ticket's own framing (*"read by any agent supporting the format"*), so it does not belong under `claude-code/`, which holds a Claude-Code-specific hook snippet | CONVENTION §1 (`contrib/` layout); ticket *Why this exists* (*"a file a user installs into their own agent … read by any agent supporting the format"*) |
| H2 | Is the recognition-probe runbook's stale *"standard 17-tool surface"* prose inside this ticket's change list? The exposure-checker found it disagrees with the 24 every other doc derives. | **No — out of the change list, recorded as a follow-up.** Scope 1–4 names `contrib/`, a generator and a test; `runbooks/` appears in no scope item and in no exclusion. With W1 settling AC5 as a gap, the runbook is not exercised by this ticket at all, so touching it would be scope taken rather than scope given. The finding is real and is filed | AGENTS.md *Standing constraints* (*"stay inside the approved change list"*); ticket Scope 1–4; `docs/runbooks/tool-recognition-probe.md:19,36` vs `code_atlas/main.py` `TOOL_NAMES` |
| H3 | Scope 2 says the snippet is checked against `shipped_adapters()` **or** the handshake — which? | **`adapter.shipped_adapters()`.** It reads `adapters/` directly and needs no running adapter, so a test can call it; the handshake's suffix map requires a live subprocess, which is exactly the dependency a drift guard must not take. 159 already reads the same function for `unconfigured_adapters` — one definition site (R6.7) | `code_atlas/adapter.py:317-331`; `code_atlas/adapter.py:345`; ticket Scope 2 |

**Exposure-checker (1 dispatch, ticket-blind).** It found two un-exposed decisions — one it judged
derivable-with-citation, one it judged user-intent — and both are recorded above, as **H1** and
**H2**. (mango ships no counted-line grammar for an exposure-checker tally, so this is prose by
construction, not a counted artifact.) It also
confirmed the console scripts `code-atlas-poke` / `code-atlas-signal` already exist and are wired
only into the Claude Code snippet — derivable, not a decision.

**Recalled claims — advisory, blocking nothing.**

| handle | key | why it matches | what it warns |
|---|---|---|---|
| `gate-on-the-invariant-not-on-presence` | 196-C1, type 2, proposed | by handle: the change adds two drift guards | gate AC1/AC2 on the **invariant** (the served surface, the shipped adapter set), never on the file merely existing |
| `097-C2` | type 5, area *routing surface / recognition vs recall* | by area | descriptions can name an occasion; they cannot make an agent notice it — the reason AC5 says a flat round is a **result**, not a failed run |
| `disclose-the-readers-cost-not-the-products-fact` | 174, area *tools / payload honesty / adoption* | by area (Adoption) | a disclosure can be true, complete and inert; check whose fact it states |
| `tier-1-pays-from-its-duplicates` | 195-C4, type 5, area *docs* | by area | the ticket's own R7.6 constraint: pay a standing doc's budget from what another tier-1 file already says verbatim |
| `verify-cited-reference-at-pickup` | 149-C1, type 5, area *process* | by area | a cross-ticket `file:line` goes stale — discharged by this phase's premise check, 14/14 resolved |

Two matching claims were **skipped as retired**: `derived-not-listed-invariant` (promoted to **R6.7**)
and `prove-the-guard-fails` (promoted to **R6.5**). Both are binding rules now, so they are checked
by the rule-section sweep at Gate 1 rather than surfaced as advice.

## Phase 1 — analysis

`PREMISE: 14 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 5 claim(s) surfaced | 0 by symbol | 1 by handle | 4 by area | 0 by finding | 2 retired skipped — advisory (blocks nothing)`
`SECTIONS: 5 found (Why this exists, Scope [+ Explicitly not in scope], Constraints, Acceptance criteria, References) | 5 decomposed | ROWS: C=8 R=4 G=2 AC=6`
`CLARIFICATION: 5 raised | 5 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/11 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

Both counting lines above the `SECTIONS:` line are **carried forward from Phase 0**, not re-run.

### BASELINE — `config.test_command` on the untouched checkout

`.venv/bin/python -m pytest -q`, run at aced82e — the **pre-change** tree, which is the branch
point and equals `main`:

```
........................................................................ [100%]
2694 passed in 126.88s (0:02:06)
```

The only uncommitted change at capture time was this file's Phase-0 append, and no test in `tests/`
reads `docs/tasks/`. Green, so the Definition of Done stays *all green*, with no baseline exclusions.

**Deliberately not written as an empirical-output block for the tree under review.** A baseline
measures the tree *before* the change, so the provenance axis refuses it — correctly by its own
rule, and wrongly for this artifact, which is a reference point rather than evidence that the
reviewed tree is green. The command, its output and its tree are all named verbatim; the claim that
`e098c83` is green is Phase 3's, and was run there.

### Requirements matrix

| ID | Source | Verbatim (abridged) | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Why this exists | *"the only artifact … that maps a natural-language question onto a tool across all 24 tools — written for a model, living in the one channel a model cannot read"* | The `which_tool` map must reach a model through a channel a model can read. An Agent Skill is that channel: the repo emits a file, the host installs it | `code_atlas/tools/prompts.py:60-100` — the map has **24** entries; `docs/TOOLS.md:3` states the surface is agent-facing; 081 settled that prompts are not | open |
| G2 | Why this exists | *"a TypeScript edit drifts the index and nothing pokes it"* | The one channel that does reach a model has rotted: the poke snippet still filters on PHP alone | `contrib/claude-code/settings.snippet.json:10` `"if": "Edit(*.php)\|Write(*.php)"`; `adapters/` holds **3** directories | open |
| R1 | Scope 1 | *"A generated `SKILL.md` — the `which_tool` map plus the tool table — emitted from the same source those already come from"* | A generator script + a committed artifact + a drift guard | source: `prompts.py` `which_tool` and `main.py` `TOOL_NAMES`; guard shape: `tests/test_documented_tool_count.py` | open |
| R2 | Scope 2 | *"The Claude Code poke snippet covers every shipped adapter, not a filter frozen at 036"* | Universal, N = **3** (below) | `code_atlas/adapter.py:317-331` `shipped_adapters()` | open |
| R3 | Scope 3 | *"Session-hook snippets for Codex … and OpenCode … carrying the same `code-atlas-poke` / `code-atlas-signal` commands"* | Two new `contrib/` directories + README, offered never installed | `pyproject.toml:25,27` both console scripts exist | open |
| R4 | Scope 4 | *"A blind recognition-probe round before and after"* | **Not achievable in this run** — see AC5 | `docs/runbooks/tool-recognition-probe.md:19` needs a live MCP surface | excluded (W1) |
| C1 | Not in scope | *"An installer, a `setup` command, or anything that writes to a user's agent settings"* | No code-atlas command may write a host settings file | `pyproject.toml:21-27` — six console scripts, none writes host settings | open |
| C2 | Not in scope | *"Rewriting tool descriptions"* | The skill carries the map, never a second description set | 069 owns descriptions | open |
| C3 | Not in scope | *"Output format"* | No payload byte changes | — | open |
| C4 | Not in scope | *"Publishing the skill anywhere"* | Generate + commit only | — | open |
| C5 | Constraints | *"No core change. `code_atlas/` gains nothing"* | `git diff --quiet main <branch> -- code_atlas/` | contract condition `CORE-BYTE-UNCHANGED` | open |
| C6 | Constraints | *"Single source, or it rots exactly as 036's filter did … Derive it or check it; never re-type it"* | R6.7 — the artifact is generated **and** guarded | R6.7 (`docs/ENGINEERING_RULES.md:214`) | open |
| C7 | Constraints | *"The skill is static. No live state … may appear in it"* | No index freshness, symbol count or open-work number in `SKILL.md` | — | open |
| C8 | Constraints | *"R7.6, and the room is already gone"* | Any standing-doc prose prunes first or argues a raise | R7.6 (`docs/ENGINEERING_RULES.md:260`); see the AC-validation note on `BACKLOG.md` | open |
| AC1 | AC | `SKILL.md` generated; the drift test red **when either side is mutated** — proven, not asserted | Two mutation controls: mutate the generated file, mutate the source | R6.5 (`:198`) | open |
| AC2 | AC | A shipped adapter with no coverage in the poke snippet fails a test; a fixture 4th adapter directory goes red | Coverage keyed on the adapter **directory name** — the only offline source | `shipped_adapters(adapters_dir)` takes an injectable root (`adapter.py:317`) | open |
| AC3 | AC | Codex + OpenCode snippets exist, each naming its file, each hand-installable from the README, no code-atlas command writes to any | Four falsifiable clauses, split one row per clause at design | — | open |
| AC4 | AC | `code_atlas/` byte-unchanged; R4.1's grep-gate green | Tree comparison + `scripts/gate.sh` | — | open |
| AC5 | AC | A blind probe round recorded before and after | **Recorded coverage-gap exclusion** (W1) with an expiry | — | excluded |
| AC6 | AC | Nothing in `contrib/` claims a language this repo cannot index | Every language named in `contrib/` ∈ `shipped_adapters()` | `contrib/claude-code/README.md:4` names PHP; PHP is shipped | open |

### AC validation — every value re-derived, and its falsifiability

| AC | Ticket's value | Re-derived | Falsifiable? |
|---|---|---|---|
| AC1 | *"either side"* | **2** mutation controls: the committed `SKILL.md`, and the source it derives from | yes — each control must be observed red (R6.5) |
| AC2 | *"a shipped adapter"* — no count given | **N = 3**: `php`, `sql`, `typescript` (`ls -d adapters/*/`) | yes — a `tmp_path` root with a 4th directory must fail |
| AC3 | four clauses | 4 rows, not 1: *exists* · *names its file* · *hand-installable from the README* · *no command writes to it* | yes — each greppable |
| AC4 | *"byte-unchanged"* | `git diff --quiet main <branch> -- code_atlas/` | yes |
| AC5 | *"before and after"* | **unmeasurable in this run** — the protocol needs a live MCP surface this session does not have | **no** → recorded manual-check / coverage-gap exclusion, counted in design's `EXCLUSIONS:` line, with a non-author-checkable `expiry:` |
| AC6 | *"a language this repo cannot index"* | Language names in `contrib/` ⊆ `shipped_adapters()` | yes |

**AC5 may not carry a matrix `✅`.** It is neither falsifiable here nor self-reportable; it is an
explicit exclusion, and the ticket stays open on it after this PR merges.

### Clarifications — all five self-resolved, each cited

1. **`which_tool`'s docstring says *"all 21 tools"* and `prompts.py`'s module docstring says the
   client surfaces *"the 21 tools"*, while `TOOL_NAMES` holds 24.** May this ticket fix them?
   **No.** AC4 makes `code_atlas/` byte-unchanged, and `tests/test_documented_tool_count.py:26`
   scans five **docs**, never source, so the drift is real and uncovered. The generator therefore
   derives the count from `len(TOOL_NAMES)` and never from a docstring. *Cited:* ticket AC4;
   `code_atlas/main.py:49-74`; `code_atlas/tools/prompts.py:1-7,61`. **Filed as a follow-up.**
2. **AC2's denominator.** **3** — `adapters/php`, `adapters/sql`, `adapters/typescript`. *Cited:*
   `code_atlas/adapter.py:317-331`.
3. **What keys AC2's coverage — a file suffix or the adapter directory name?** The **directory
   name**. A suffix is announced by a **running** adapter (`adapter.py:117-120`,
   `extension_index` at `:289-303`), so a suffix-keyed guard would need a live subprocess; the
   directory list is offline and is what 159 already reads. *Cited:* `adapter.py:117-120,289-303,345`.
4. **Does *"the tool table"* in Scope 1 mean `TOOLS.md`'s prose table or the served surface?** The
   **served surface** — `TOOL_NAMES` plus the `which_tool` map, both read from source, which is what
   makes *"the skill cannot describe a surface the server does not serve"* true by construction
   rather than by review. *Cited:* ticket Scope 1; `code_atlas/main.py:49-74`.
5. **C8 says `BACKLOG.md` sits at 8,134 against 8,200.** It no longer does: commit `aced82e` raised
   the ceiling to **8,300** for tickets 200/201/202's own rows, argued in
   `tests/test_doc_size_budget.py`. C8's *constraint* is unchanged and still binds — prune or argue —
   only its quoted figures are stale. *Cited:* `tests/test_doc_size_budget.py:83`;
   `tests/test_agent_chain_budget.py:32`.

### Universal inventory — N = 3

| # | Shipped adapter | Directory | Poke coverage today |
|---|---|---|---|
| 1 | `php` | `adapters/php/` | covered — `"if": "Edit(*.php)\|Write(*.php)"` |
| 2 | `sql` | `adapters/sql/` | **none** |
| 3 | `typescript` | `adapters/typescript/` | **none** |

R2/AC2 is a *for each of N* requirement: review confirms **every** row, never a total.

### Gap analysis (enhancement)

| Goal | Current | Target | `path:line` |
|---|---|---|---|
| The map reaches a model | `which_tool` is an MCP prompt; a client never shows a prompt to a model | the same map emitted as an Agent Skill the host may install | `code_atlas/tools/prompts.py:60`, `103` (`server.prompt(name=WHICH_TOOL)`) |
| Edits on any indexed language poke the index | the hook fires only for `*.php` | it fires for every shipped adapter | `contrib/claude-code/settings.snippet.json:10` |
| More than one agent is offered a hook | `contrib/` holds one agent's snippet | Codex and OpenCode too | `contrib/` (2 directories, 5 files) |

### Blast radius

**Repo:** `app` (the only entry in `config.repos`). **Entry points:** none — this ticket adds no
tool, no CLI and no runtime path. **Touched:** `contrib/` (new + edited), `scripts/` (new
generator), `tests/` (new guards), `docs/` (ledger, backlog, TOOLS pointer). **Read-only
dependents:** `code_atlas/adapter.py` and `code_atlas/main.py` are **imported** by the generator and
the guards and are **not modified** (C5/AC4). No `db-map` exists, so no schema dependents.

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) ✅ · §2 (change-type) ✅ · §3 (change-type) N/A (no node or edge vocabulary moves and contract.py is untouched) · §4 (change-type) ✅ · §5 (change-type) N/A (no tool payload or refusal path is added or changed) · §6 (change-type) ✅ · §7 (change-type) ✅ · §8 (change-type) N/A (no runtime or dev dependency is added)`

The rule book carries no `handle:` markers (`grep -c "handle:" docs/ENGINEERING_RULES.md` → 0), so
the recalled-handle source contributes **0** sections — it asks nothing and changes no count. What
each ✅ section bites on:

- **§1** — R1.1/R1.4: the generator lives in `scripts/`, imports `code_atlas` read-only and touches
  no SQLite; `code_atlas/` is byte-unchanged, so no language branch can enter the core.
- **§2** — R2.2: neither `SKILL.md` nor any snippet may name a repo or framework; the existing
  grep-gate in `scripts/gate.sh` covers the new files by path.
- **§4** — R4.1/R4.2: the generator makes no LLM or network call, and emits byte-identical output
  for identical input by ordering off `TOOL_NAMES`.
- **§6** — R6.5 and R6.7 are the two rules AC1/AC2 are written against: each guard is observed
  failing, and the artifact is derived rather than listed.
- **§7** — R7.2 (a ledger row) and R7.6 (C8: prune or argue before adding standing-doc prose).

No section is `PROVISIONAL`, so nothing here is enforced as codified that a human has not ratified.

## Phase 2 — design

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Approach

**One generator, three generated artifacts, two derived guards.** `scripts/gen_skill.py` reads the
served surface out of the repo and writes `contrib/skill/SKILL.md` and
`contrib/claude-code/settings.snippet.json`. Nothing is re-typed beside its source (C6/R6.7):

1. **The recognition map** comes from `which_tool` itself. That function is a **closure inside**
   `prompts.register(server)`, so it cannot be imported — but `register` only ever calls
   `server.prompt(name=…)(fn)`. The generator passes a **recorder** with that one method and keeps
   the functions. No FastMCP, no server, no network, and — decisively — **no change to
   `code_atlas/`** (C5/AC4).
2. **The tool roster** comes from `code_atlas.main.TOOL_NAMES`, in its registration order (R4.2).
   The skill carries **no second set of tool descriptions** (C2): the map already pairs each tool
   with the question it answers, and a second description set is the thing that can disagree.
3. **The per-adapter suffixes** come from each shipped adapter's own entry file, where the
   announcement literal is declared statically — `adapters/php/index.php:27`
   (`'extensions' => ['.php', '.phtml']`), `adapters/typescript/index.js:12`,
   `adapters/sql/index.js:12`. This is the **same string the handshake announces**, read without
   starting a subprocess, which is what lets a test check it offline (H3, refined below).

The two guards gate on the **invariant**, never on presence: *does the committed artifact equal what
the source produces*, and *does every shipped adapter have at least one of its declared suffixes in
the snippet* — not *does the file exist*.

### Rejected alternatives

| # | Alternative | Why rejected |
|---|---|---|
| A1 | **Drop the `"if"` filter entirely** — `poke.py` already exits 0 on a suffix no adapter owns, so an unfiltered hook is correct and can never rot. | It is correct and it is **unprovable**. With nothing per-adapter in the snippet, a fixture that adds a fourth adapter directory cannot turn any assertion red — so AC2's stated control, and R6.5's *observe the guard failing*, both become impossible. A guard that cannot be made to fail is decoration. |
| A2 | **Derive the suffixes by starting each adapter and reading its handshake.** | It is the live truth, and it makes the guard depend on `CA_*_CMD` being configured in the test environment. Where it is not, the test skips — and a skip is not a pass (R6.5). The static declaration is the same literal, read without the dependency. |
| A3 | **Parse `docs/TOOLS.md`'s table for the tool roster.** | Its rows group three tools into one cell (`find_callers` / `find_references` / `find_implementations`), so the parse is brittle prose-shaped work, and `TOOLS.md` is *prose about* the surface rather than the surface. `TOOL_NAMES` **is** what the server registers. |
| A4 | **Hand-write `SKILL.md` and guard it with a review checklist.** | This is the defect the ticket exists to fix, one file over (036's frozen filter). C6 forbids it. |

### Assumptions

| # | Assumption | Tag | Resolution |
|---|---|---|---|
| A-1 | `prompts.register` touches only `server.prompt(name=…)` | **verified** | `code_atlas/tools/prompts.py:99-103` — four calls, all `server.prompt(name=…)(fn)`; the recorder satisfies exactly that |
| A-2 | Every shipped adapter declares its suffixes as a one-line literal in its entry file | **verified** | the three greps above return one line each; and the guard is **self-checking** — an adapter whose declaration does not parse reads as *uncovered* and turns the test red rather than passing quietly |
| A-3 | Codex reads `~/.codex/hooks.json` with event names inside a `hooks` wrapper, handlers `{type, command}`, enabled by `[features] hooks = true` | **novel-untested (documented, not executed)** | Documented shape, not observed on a running Codex. **Not load-bearing:** no AC and no code path depends on it — AC3's four clauses are about the committed file's content and the absence of any writer. Recorded as exclusion **E2** with an expiry |
| A-4 | An OpenCode project plugin is a named `async ({project, client, $, directory, worktree}) => hooks` export in `.opencode/plugins/*.js` | **novel-untested (documented, not executed)** | same as A-3; same exclusion **E2** |

### Smallest change list

| # | Change | File / area | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | New generator: recorder-extracted map, roster from `TOOL_NAMES`, suffixes from each adapter's entry file | `scripts/gen_skill.py` (new) | imports `code_atlas.main` + `code_atlas.tools.prompts` **read-only**; picked up by `ruff` and by gate.sh's bytecode-invalidation check | R1, R2, C6 | 1/1 |
| 2 | The generated skill | `contrib/skill/SKILL.md` (new) | none identified — an offered file, imported by nothing | R1, G1 | 1/1 |
| 3 | Install-by-hand note, no installer | `contrib/skill/README.md` (new) | none identified | R1, C1 | 1/1 |
| 4 | `"if"` regenerated to cover every shipped suffix | `contrib/claude-code/settings.snippet.json` | `tests/test_claude_code_poke_index.py` reads the poke path — **proof collateral**, checked below | R2, G2, AC2 | 2/3 → 3/3 |
| 5 | The sentence *"limits the hook to `*.php` while PHP is the only adapter — widen it when more adapters ship"* is now false | `contrib/claude-code/README.md:14` | none identified | R2, AC6 | 1/1 |
| 6 | Codex session-hook snippet + README | `contrib/codex/hooks.json`, `contrib/codex/README.md` (new) | none identified | R3, AC3 | 1/2 |
| 7 | OpenCode plugin + README | `contrib/opencode/code-atlas.js`, `contrib/opencode/README.md` (new) | none identified | R3, AC3 | 2/2 |
| 8 | Drift guard + **two** mutation controls | `tests/test_skill_drift.py` (new) | none identified | AC1 | 1/1 |
| 9 | Coverage guard + fourth-adapter control + vacuity control | `tests/test_poke_snippet_covers_every_adapter.py` (new) | none identified | AC2 | 3/3 |
| 10 | AC3's four clauses + AC6, one assertion each | `tests/test_contrib_snippets.py` (new) | reads `pyproject.toml`'s `[project.scripts]` | AC3, AC6 | 5/5 |
| 11 | Status `todo` → `blocked` (open on AC5), plus the two filed follow-ups | `docs/BACKLOG.md` | `tests/test_backlog_bookkeeping.py`, `tests/test_doc_size_budget.py` — **proof collateral** | C8, R7.2 | 1/1 |
| 12 | Spend row | `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | R7.2 | 1/1 |
| 13 | Frontmatter `status: blocked` + this working doc | `docs/tasks/200_*.md` | `tests/test_backlog_bookkeeping.py` | R7.2 | 1/1 |

**Proof collateral traced, not assumed.** `tests/test_claude_code_poke_index.py` is the one existing
test that reads the poke surface; it exercises `code_atlas/hooks/poke.py`, **not** the snippet's
`"if"` string, so change 4 does not invalidate it. `tests/test_doc_size_budget.py` and
`tests/test_backlog_bookkeeping.py` are invalidated by changes 11–13 by construction and are listed.

### Recalled handle — traced

**`gate-on-the-invariant-not-on-presence`** (196-C1). Traced:

Ran at e098c83.

```
$ grep -rln "\.exists()\|\.is_file()" tests/ | head -8
tests/test_trace_capability.py
tests/test_contrib_snippets.py
tests/test_onboarding_llm_prose.py
tests/test_write_time_signal.py
tests/test_reachability_split.py
tests/test_sql_confinement.py
tests/test_supervision_question_class.py
tests/test_get_index_status_health.py
```

48 test files reach for a presence predicate, so the shape is everywhere and is the easy thing to
write here. **Folded into the design:** neither new guard asserts that `SKILL.md` or a snippet
*exists*. `test_skill_drift.py` compares the committed bytes to the generator's output — a file that
exists and is stale is **red**. `test_poke_snippet_covers_every_adapter.py` asserts every shipped
adapter's declared suffix appears in the snippet — a snippet that exists and covers one adapter of
three is **red**. Presence is a consequence of the invariant here, never the assertion.

### Rule compliance

| Rule | How this complies |
|---|---|
| R1.1 / R1.4 | `code_atlas/` is byte-unchanged; the generator lives in `scripts/`, imports read-only and touches no SQLite |
| R2.2 | neither the skill nor a snippet names a repo or a framework; gate.sh's grep-gate covers the new paths |
| R4.1 / R4.2 | no LLM and no network in the generator; output ordering comes from `TOOL_NAMES`, so identical input gives identical bytes |
| R6.5 | every guard ships with its own observed failure: two mutation controls for AC1, a fourth-adapter control **and** a vacuity control for AC2 |
| R6.7 | the roster, the map and the suffix set are all **derived**; nothing is listed beside its source |
| R6.9 | each guard asserts at the **consumer** — the committed artifact a user installs — not at the generator that produced it |
| R7.5 | every comment in the new files stays ≤ 3 lines |
| R7.6 | `BACKLOG.md` gains one status edit and two follow-up lines; the ceiling raised for exactly these rows in `aced82e` is not re-consumed by narrative |

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | logic | unit — `test_skill_drift.py`, committed bytes vs generator output | n/a | ✅ |
| AC1-control-a | logic | unit — mutate the committed side, assert red | authored | ✅ |
| AC1-control-b | logic | unit — mutate the source side, assert red | authored | ✅ |
| AC2 | logic | unit — every `shipped_adapters()` name has a declared suffix in the snippet | n/a | ✅ |
| AC2-control | logic | unit — a `tmp_path` adapters root with a fourth directory reports it uncovered | authored | ✅ |
| AC2-vacuity | logic | unit — the coverage reader found a non-empty suffix set | n/a | ✅ |
| AC3a *exists* | logic | unit | n/a | ✅ |
| AC3b *names the file it belongs in* | logic | unit — each README names its target path | n/a | ✅ |
| AC3c *hand-installable from the README* | logic | unit — each README carries the target path **and** the merge/copy step | n/a | ✅ |
| AC3d *no code-atlas command writes to any of them* | logic | unit — enumerate every `[project.scripts]` entry point, assert none names a host settings path | n/a | ✅ |
| AC4 | logic | contract condition `CORE-BYTE-UNCHANGED` (`git diff --quiet main <branch> -- code_atlas/`) + gate.sh's R4.1 grep-gate | n/a | ✅ |
| AC5 | runtime / 3p | **manual-recorded** — needs a live MCP surface this run does not have | n/a | ❌ → **E1** |
| AC6 | logic | unit — every language named in `contrib/` ∈ `shipped_adapters()` | n/a | ✅ |

No AC is input-shape-dependent: every row above compares against a value written down before the
run. `config.real_corpus_path` is **unset**, and that costs nothing here — no row wanted a corpus.

### Coverage-gap exclusions

**E1 — AC5, the blind recognition-probe round.**
- *item:* a before/after blind probe per `docs/runbooks/tool-recognition-probe.md`
- *risk tier:* medium — the ticket's own measurement of whether the skill moved anything
- *why deferred:* the protocol needs a fresh agent on a **live** code-atlas MCP surface with a built,
  current index. This session has no code-atlas MCP tools connected, so the measurement cannot be
  taken honestly rather than merely cheaply. Ratified by the maintainer at Gate 0 (W1)
- *follow-up:* task 200 stays `blocked` on AC5; the round runs in the next field-retro
- `expiry: when a field-retro round is next run against a live code-atlas MCP surface (docs/runbooks/field-retro.md §0.5)`
- `seen: []` — first occurrence of this class

**E2 — A-3/A-4, the Codex and OpenCode snippet shapes are documented but never executed.**
- *item:* the two new snippets' schemas
- *risk tier:* low — no AC and no code path depends on them; a wrong schema means a user's hand
  install does not fire, which their own agent reports
- *why deferred:* neither host is installed here, and the repo's standing posture is *offered, never
  installed*, so there is no code-atlas code path that could exercise them
- *follow-up:* each README cites the documentation URL it was written against and says plainly that
  the shape is unverified against a running host
- `expiry: when a maintainer runs either snippet on a host with that agent installed`
- `seen: []` — first occurrence of this class

### Proving test

**`tests/test_poke_snippet_covers_every_adapter.py::test_every_shipped_adapter_has_a_suffix_in_the_poke_snippet`** — red before the change (`sql` and `typescript` are uncovered by the 036 filter), green after.

```
.venv/bin/python -m pytest tests/test_poke_snippet_covers_every_adapter.py tests/test_skill_drift.py tests/test_contrib_snippets.py -q
```

Full sweep before the PR: `scripts/gate.sh` (17 checks) plus the whole suite, on this Linux host.

### Rollback + porting

Rollback is `git revert` of the single squash commit: every change is additive except one JSON
string and one README sentence, and no runtime path, tool payload or database shape is touched.
`config.repos` holds one repo (`app`), so there is no porting order.

`SCOPE: M` — unchanged from analysis. Thirteen change-list items, none in `code_atlas/`, no new
dependency, no contract bump; it did not cross a tier.

## Phase 3 — execute

### Axis 1 — file set

Ran at e098c83.

```
$ git diff --name-only main..HEAD
contrib/claude-code/README.md
contrib/claude-code/settings.snippet.json
contrib/codex/README.md
contrib/codex/hooks.json
contrib/opencode/README.md
contrib/opencode/code-atlas.js
contrib/skill/README.md
contrib/skill/SKILL.md
docs/BACKLOG.md
docs/tasks/200_the-recognition-map-is-a-prompt-no-agent-can-read.md
scripts/gen_skill.py
tests/test_contrib_snippets.py
tests/test_poke_snippet_covers_every_adapter.py
tests/test_skill_drift.py
```

Fourteen paths, every one on the Gate-2 list (items 1–11, 13); item 12's ledger row is written at
finalise, when the PR number exists. `git status --porcelain` at this SHA shows only the working
doc, still in flight — the exempt bookkeeping file. **No file outside the list, and no untouched-line
reformatting** — `ruff` was run over the four authored files only, never a whole-file pass.

Ran at e098c83.

```
$ git diff --stat main -- code_atlas/
```

Empty — **AC4: `code_atlas/` is byte-unchanged.**

### The proving test, red before and green after

Ran at e098c83.

```
$ git show main:contrib/claude-code/settings.snippet.json  # the 036 filter, then uncovered_adapters()
036 filter: Edit(*.php)|Write(*.php)
uncovered_adapters -> ['sql', 'typescript']
```

Ran at e098c83.

```
$ .venv/bin/python -m pytest tests/test_skill_drift.py tests/test_poke_snippet_covers_every_adapter.py tests/test_contrib_snippets.py -q
...........................                                              [100%]
27 passed in 0.46s
```

### Delta-green and the gate, on this Linux host

Ran at e098c83.

```
$ .venv/bin/python -m pytest -q
.........................................................                [100%]
2721 passed in 150.32s (0:02:30)
```

Baseline was 2694 passed; +27 is exactly the three new files. No pre-existing test moved.

Ran at e098c83.

```
$ ./scripts/gate.sh
  17 passed · 0 failed · 0 skipped
GATE GREEN — all 17 checks passed
```

### Axis 2 — design-conformance self-check

| Gate-2 Approach bullet | Verdict |
|---|---|
| 1. Recorder-extracted recognition map, no FastMCP, no core change | implemented-as-approved — `scripts/gen_skill.py` `_PromptRecorder` |
| 2. Roster from `TOOL_NAMES`, no second description set | implemented-as-approved |
| 3. Suffixes read from each adapter's own entry file | implemented-as-approved — the reader scans every top-level file rather than a listed entry-file name, which is **stricter** than approved, not different |
| Guards gate on the invariant, never on presence | implemented-as-approved |

**One deviation, recorded.** Gate 2's change list said the two filed findings go to `BACKLOG.md`'s
follow-ups. They do not: the line cost 47 tokens and pushed tier 1 to 25,350 against its 25,300
ceiling, and R7.6 forbids retelling what a task file already holds. The finding stays in Phase 1's
clarification 1 — cited, precise — and is named in the PR body. `BACKLOG.md` carries only
`todo → blocked`. Surfaced here for review to adjudicate rather than absorbed.

**Status is `blocked`, not `done`** — the ticket is open on AC5 (exclusion E1) and on nothing else.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Verdict: clean (challenger only — REVIEWER: OFF).** No rule-book-grounded review of this diff ran;
a clean result here carries no reviewer finding because none was sought.

`CHALLENGER: 16 requirement(s) reconstructed | 15 met | 1 not met | 0 can't tell`

The one *not met* is **AC5**, which is exactly coverage-gap exclusion **E1** — recorded and ratified
by the maintainer at Gate 0. Per review's clean criteria, a challenger *not met* that corresponds to
a recorded, human-approved exclusion does not block. The challenger cannot see E1 from its seat and
said so; its judgement against the raw ticket is correct and is not overridden, only reconciled.

**The challenger re-exercised both guards itself rather than reading their assertions.** It mutated
`contrib/skill/SKILL.md` and, separately, the `which_tool` body in `code_atlas/tools/prompts.py`, and
saw each go red; it added a real `adapters/ruby/index.rb` declaring `.rb` to the live tree and saw
the coverage test go red. Both guards fail for the right reason and neither is a tautology. It
reverted every mutation — `git status --porcelain -uall` shows only this working doc, `adapters/`
holds three directories, and the 27 guard assertions are green.

### Scope reconciliation

- **File axis — clean.** 14 paths in `main..HEAD`, every one on the Gate-2 list. No file outside it;
  no untouched-line reformatting (`ruff` ran over the four authored files, never a whole-file pass).
- **Behaviour axis — clean, one deviation adjudicated.** Execute recorded the BACKLOG follow-up
  deviation itself; **accepted** — R7.6 forbids retelling what a task file holds, tier 1 was 50
  tokens over with the line in, and the finding survives in Phase 1 clarification 1 and in the PR
  body. The suffix reader being stricter than approved (scans every top-level file rather than a
  named entry file) is not a deviation: it is the approved bullet, implemented without a list.
- **Regression — none.** Phase 1's blast radius named `tests/test_claude_code_poke_index.py`; it
  exercises `code_atlas/hooks/poke.py`, not the snippet's filter string, and is green.

### Layer-match re-confirmation

Every verification-plan row sits at or above its risk layer. The single `❌` — AC5, risk layer
runtime/3p — is exclusion **E1**, recorded with a checkable expiry and human-approved. No AC closed
clean on a layer-mismatched proof.

### `Ph3/4 proven by`

| Row | Proven by | k/N |
|---|---|---|
| G1, R1, AC1 | `test_skill_drift.py` — 4 assertions incl. both mutation controls, re-exercised by the challenger | 1/1 |
| G2, R2, AC2 | `test_poke_snippet_covers_every_adapter.py`; **item by item**: `php` `.php`+`.phtml` ✅ · `sql` `.sql` ✅ · `typescript` `.ts .tsx .js .jsx .mjs .cjs` ✅ | **3/3** |
| R3, AC3a–d | `test_contrib_snippets.py` — one assertion per clause, four clauses | 4/4 |
| C5, AC4 | `git diff --stat main..HEAD -- code_atlas/` empty; gate.sh R4.1 green | 1/1 |
| R4, AC5 | **not proven — exclusion E1** | 0/1 |
| AC6 | `test_contrib_snippets.py::test_nothing_offered_claims_a_language_this_repo_cannot_index` | 1/1 |
| C1–C4, C6, C7, C8 | challenger rows 10–16, each with `path:line` | 7/7 |

`k = N` on every row but AC5, which is the recorded, human-approved exclusion.

### Evidence provenance

`check_lines … --phase review --tree e098c83` reports **8 records | 7 on the tree under review | 1
from ANOTHER tree | 0 provenance-unknown**. The one refusal is Phase 1's `BASELINE`, stamped
`Ran at aced82e` — and that is **correct, not stale**: a baseline is by definition a measurement of
the pre-change tree, so "another tree" is the only thing it can honestly be. It is left as it ran
rather than re-stamped, and is carried into `DISCLOSURE`. Every other block was re-run at `e098c83`
after the first review pass refused the branch-point stamps.

Reviewed at e098c83848c633beaed882d359eac9645114b0be

Reviewed files: `contrib/claude-code/README.md`, `contrib/claude-code/settings.snippet.json`,
`contrib/codex/README.md`, `contrib/codex/hooks.json`, `contrib/opencode/README.md`,
`contrib/opencode/code-atlas.js`, `contrib/skill/README.md`, `contrib/skill/SKILL.md`,
`docs/BACKLOG.md`, `scripts/gen_skill.py`, `tests/test_contrib_snippets.py`,
`tests/test_poke_snippet_covers_every_adapter.py`, `tests/test_skill_drift.py`.
Working doc (exempt from the staleness comparison):
`docs/tasks/200_the-recognition-map-is-a-prompt-no-agent-can-read.md`.

## Phase 5 — finalise

**Stale-review guard: not stale.** `git diff --name-only e098c83..HEAD` is empty and the only
uncommitted file is this working doc — the exempt bookkeeping path recorded with the marker.

### Cost ledger

| # | Dispatch | Phase | Tokens | Tool uses |
|---|---|---|---|---|
| 1 | `challenger` as exposure-checker | 0 refine | 53,204 | 8 |
| 2 | `challenger`, ticket-blind | 4 review | 77,144 | 43 |
| — | main loop | all | **unmeasured (host does not surface usage)** | — |

`LEDGER TOTAL: 130,348 tokens · top cost driver: review challenger`

Dispatch only — mango does not measure main-loop output noise, and no dispatch-vs-noise split is
implied. `reviewer` was not dispatched: the run carried `--no-reviewer`, so its ~108k was not spent
and no rule-book-grounded review exists.

### Durable lesson

`CLAIMS: 4 claim(s) from 1 lesson entr(ies) | T1=1 T2=2 T3=0 T4=0 T5=1 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: — | mango files written: 0`

Written to `docs/LESSONS.md` as `## 200` with claims **200-C1** (type 1, `symbol:check_lines.py`),
**200-C2** (type 2 process, `stamp-evidence-with-the-tree-under-review`), **200-C3** (type 2 code,
`prefer-the-provable-fix`) and **200-C4** (type 5, area *adapters*). Every claim is `seen: 200`
only, so none is a promotion candidate and nothing reaches the falsification or ratification gate
this run. 200-C1 is also filed as a type-3 **signal** in `docs/SKILL_GAP_CANDIDATES.md` for mango's
maintainer; **no mango file was written.**

### Follow-ups drafted

| Deferred row | Follow-up |
|---|---|
| AC5 / R4 — exclusion **E1** | 200 stays `blocked`. The blind probe round runs in the next field-retro against a live MCP surface; the ticket closes on that round alone |
| A-3 / A-4 — exclusion **E2** | each README carries its documentation URL and says the shape is unverified against a running host; discharged when a maintainer runs either snippet on a host with that agent installed |
| Phase 1 clarification 1 | three documented tool counts read 21 or 17 — two `prompts.py` docstrings and the probe runbook, none scanned by `test_documented_tool_count.py`, which reads five docs and no source. Named in the PR body; **not** filed in `BACKLOG.md`, on R7.6 grounds recorded as the Phase-3 deviation |

### RECONCILE at close

```
RECONCILE
  conditions: 8 declared | 8 re-run | 5 holding | 3 BROKEN | 0 UNBOUND | 0 could-not-run
  phase     : close | reviewer: off | challenger: on
```

**Read the three BROKEN first — one is expected, two are conditions I mis-authored at t0.**

| Condition | Why BROKEN |
|---|---|
| `TREE-COMPARISON` | **Expected.** It holds only once the PR is merged; `autorun` stops at the PR |
| `SKILL-EMITTED` | **Mis-authored.** `ls contrib/*/SKILL.md contrib/*/*/SKILL.md` exits 2 because the *second* glob matches nothing, even though the first does. `ls contrib/*/SKILL.md` alone exits 0 and prints `contrib/skill/SKILL.md`. The artifact exists; the check does not say so |
| `POKE-FILTER-NOT-PHP-FROZEN` | **Mis-authored.** The generated filter legitimately *begins* `Edit(*.php)\|Write(*.php)` — `php` is a shipped adapter and sorts first — so "does not contain the 036 string" was never the invariant. The real one is *covers every shipped adapter*, which is the proving test, green 3/3 |

The contract's guarantee is that it is well-formed and internally consistent, never that a value is
true. These two are exactly that gap, and they are reported rather than rewritten at close.

### DISCLOSURE

1. **REVIEWER: OFF** — waived by `--no-reviewer` (the run arg *"with skipper reviewer"*, read per
   AGENTS.md as the reviewer seat only). **No rule-book-grounded review of this diff ran**; the clean
   verdict carries no reviewer finding because none was sought.
   **CHALLENGER: ON** — the ticket-blind challenger ran, and re-exercised both guards with real
   mutations rather than reading their assertions.
2. **UNCHECKED AGENT CLAIMS: 0** — every contract value was derived by a command.
3. **BUDGET: call-count ceiling `unknown`** — no ledger history for this tier (125 of 192
   `TOKEN_LEDGER` rows read `main-loop unmeasured`). Nothing was invented and nothing was blocked.
   Actual dispatch spend: 130,348 tokens across 2 dispatches.
4. Everything below is what I chose not to verify, or verified less than fully:
   - **AC5 was not measured at all** (exclusion **E1**). No probe round, before or after. The ticket
     ships `blocked`, and the challenger independently reported AC5 unmet.
   - **The Codex and OpenCode snippet schemas were never executed** (exclusion **E2**) — written from
     published documentation on a host where neither agent is installed. One third-party write-up
     disagrees with the reference about the `"hooks"` wrapper; I followed the reference. If either
     shape is wrong, a hand install silently does not fire.
   - **Two contract conditions were mis-authored** and reported BROKEN at close for reasons that have
     nothing to do with the work (table above). I found them only at close, not at t0, because at t0
     every condition is *supposed* to be failing — which is precisely the blind spot in the t0 check.
   - **The finalise gate returned exit 2 on its first run**, refusing the Phase-1 `BASELINE` as
     evidence from another tree. I did not re-stamp it; I stopped writing it as an empirical-output
     block for the reviewed tree. That is a judgement call about an artifact the checker has no
     category for, and a reader may reasonably disagree with it.
   - **Eight evidence blocks were originally stamped at the branch point** and refused at review. They
     were re-run at `e098c83` — but the first review pass was scoped against stamps that were wrong,
     and only the harness caught it.
   - **`docs/BACKLOG.md` carries no follow-up line** for the three stale tool counts, against the
     Gate-2 change list. Recorded as a Phase-3 deviation and adjudicated at review; the finding lives
     in Phase 1 and in the PR body only.
   - **The working doc is 122% of its 40,000 B ceiling.** Reported by the checker, not blocked.
   - **No `reviewer` seat, no `real_corpus`, no live MCP surface, no running Codex or OpenCode.**
     Four things this run could not check, listed so the absence is visible.
   - **Outward actions deferred to the morning:** the **merge** of PR #243. `autorun` never merges.
