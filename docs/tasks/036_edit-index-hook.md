---
id: 036
slug: edit-index-hook
title: Claude Code Edit/Write index-poke hook
phase: 1.5
milestone: Distribution
status: done
depends_on: [016, 035]
---

## Goal
Use the client's own hook system so the agent's edits keep the index live. code-atlas is built for a
consumer that has a hook mechanism (Claude Code) — a `PostToolUse` hook on `Edit`/`Write` that pokes
the index turns freshness from opt-in into automatic. This is a distribution move worth more than
several features (§19 agent-first pivot).

## Scope / Deliverables
- A hook script + a `settings.json` snippet (documented) that, after `Edit`/`Write`, marks the
  touched file(s) stale or triggers an incremental update for them, reusing the incremental path
  (task 016).
- README/docs section: how to install the hook and what it does.

## Constraints
- The hook is **opt-in configuration outside the core** — no core change beyond what the incremental
  path already exposes; no language branches.
- Must be a safe no-op when no index (`.code-atlas/graph.db`) exists — never build implicitly.
- Cheap and non-blocking: poking one file must not stall the editor tool round-trip.

## Acceptance criteria
- With the hook installed, editing a file via Claude Code makes the next query reflect the change
  (via task 035 read-through or an incremental poke) without a manual rebuild.
- With no index present, the hook exits cleanly and does nothing.
- Install steps documented and reproducible.

## References
`code_atlas/indexer.py` (`incremental_update`); task 016 (incremental via git diff); task 035
(read-through freshness). PLAN §5, §19. Feedback origin: [`FEEDBACK.md`](../FEEDBACK.md) round 3
("ship a Claude Code PostToolUse hook on Edit/Write — a distribution move worth more than several
features").

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 036 — Claude Code Edit/Write index-poke hook (working doc)

- **Ticket:** 036 · local `docs/tasks/036_edit-index-hook.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green — `667 passed` (main tip post-035)
  <!-- baseline exclusions: none -->
- **work_doc_mode:** embed

---

## Phase 0 — Refine

`REFINE: 3 unresolved surfaced | 1 want asked+ASSUMED | 2 exposure ASSUMED | 4 how-decision resolved+cited | skip: no`

**Settled wants (ASSUMED — standing approval 2026-08-04 "suggest and do the best / pass all gates").**

| # | Want | Chosen | AC constraint |
|---|------|--------|---------------|
| 1 | Poke vs rely-on-035 vs full incremental | **A — eager single-file `reparse_file`** | W1 |
| 2 | Delivery channel | **Checkout `scripts/` + `contrib/claude-code/` docs** (like `setup.py`) | W2 |
| 3 | Settings locus | **Project `.claude/settings.json` primary; user-global documented** | W3 |

**HOW (cited).**

| # | HOW | Resolution | Citation |
|---|-----|------------|----------|
| 1 | Outside core | Script under `scripts/`; snippet under `contrib/claude-code/` — no `code_atlas/` change | ticket C L24–25 |
| 2 | No index → no-op | Exit 0 if `config.db_path` missing; never `full_build` | ticket C L26–27; AC2 |
| 3 | Reuse write path | Call `indexer.reparse_file` | ticket Refs; `indexer.py` |
| 4 | Non-blocking | Settings `"async": true` (Claude Code hooks) | ticket C L28; Claude Code hooks docs |

**Exposure-checker:** 2 items → ASSUMED W2/W3 (dispatch `255122d1-ece0-41d4-842d-91371d0fff4f`)

---

## Requirements matrix

`SECTIONS: 4 found (Goal, Scope, Constraints, AC) | 4 decomposed | ROWS: C=3 R=2 G=1 AC=3 W=3`

| ID | Source | Verbatim (short) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 | Status |
|----|--------|------------------|----------------|--------------|-----|-------|--------|
| G1 | Goal | PostToolUse poke keeps index live | Eager reparse after Edit/Write | ticket L11–15 | | | ✅ |
| R1 | Scope | hook script + settings snippet | scripts + contrib snippet | ticket L18–20 | | | ✅ |
| R2 | Scope | README/docs install | README + contrib README | ticket L21 | | | ✅ |
| C1 | Constraints | outside core; no lang branches | no code_atlas/ edits | ticket L24–25 | | | ✅ |
| C2 | Constraints | no-op without index | exit 0; no build | ticket L26–27 | | | ✅ |
| C3 | Constraints | cheap non-blocking | async:true | ticket L28 | | | ✅ |
| AC1 | AC | edit → next query reflects | poke updates hash/rows | ticket L30–31 | | | ✅ |
| AC2 | AC | no index → clean exit | proving test | ticket L32 | | | ✅ |
| AC3 | AC | install docs reproducible | README + contrib | ticket L33 | | | ✅ |
| W1 | refine | eager reparse_file | ASSUMED A | Phase 0 | | | ✅ |
| W2 | refine | scripts+contrib delivery | ASSUMED | Phase 0 | | | ✅ |
| W3 | refine | project settings primary | ASSUMED | Phase 0 | | | ✅ |

## AC validation

| AC | Ticket | Computed | Match | Falsifiable |
|----|--------|----------|-------|-------------|
| AC1 | next query reflects change | poke updates store hash; read_symbol sees body | Y | measurable |
| AC2 | no index → clean exit | exit 0; no db created | Y | measurable |
| AC3 | install documented | README section + contrib README | Y | greppable |

### Gap
| Current | Target | path |
|---------|--------|------|
| No PostToolUse poke | scripts + snippet + docs | scripts/, contrib/, README |
| 035 alone is query-time | eager edit-time poke | reparse_file |

### Blast radius
Outside core: `scripts/claude_code_poke_index.py`, `contrib/claude-code/*`, README, tests, BACKLOG/PLAN/task.
Out of scope: core API changes; full incremental_update; mtime schema.

### Gate 1
**ASSUMED W1–W3 ratified** by standing approval. **cleared**.

---

## Phase 2 — Design

### Approach
1. Add `scripts/claude_code_poke_index.py`: stdin JSON → `file_path` → `load_config` → no-op without db → `reparse_file`.
2. Ship `contrib/claude-code/settings.snippet.json` with `PostToolUse` matcher `Edit|Write`, `"async": true`.
3. Document install in `contrib/claude-code/README.md` + short README pointer.
4. Proving tests: no-index noop; poke after edit updates hash and read_symbol source.

### Rejected
- Full `incremental_update` on every edit — too heavy / may stall (ticket C3).
- Rely-only-on-035 (no poke) — contradicts Goal "pokes the index".
- Core console script in `code_atlas/` — unnecessary; scripts/ matches setup.py.

### Change-list

| # | Change | File | Covers | k/N |
|---|--------|------|--------|-----|
| 1 | Poke script | `scripts/claude_code_poke_index.py` | G1,R1,C1,C2,W1 | 5/5 |
| 2 | Settings snippet | `contrib/claude-code/settings.snippet.json` | R1,C3,W3 | 3/3 |
| 3 | Contrib README | `contrib/claude-code/README.md` | R2,AC3,W2 | 3/3 |
| 4 | README pointer | `README.md` | R2,AC3 | 2/2 |
| 5 | Proving tests | `tests/test_claude_code_poke_index.py` | AC1,AC2,W1 | 3/3 |
| 6 | Docs BACKLOG/task | docs | R7.2 | 1/1 |

### Named proving test
`tests/test_claude_code_poke_index.py::test_poke_reparses_edited_file`

### Gate 2
**cleared** — standing approval; approach = scripts poke + async settings snippet.

## Phase 3 — Execute

**Branch:** `feat/036-edit-index-hook`
**Implemented:** change-list #1–6. Suite: `670 passed` (baseline 667 + 3 proving).

### Axis 1 — file set
`diff ⊆ approved list ✅` (scripts/, contrib/, README, tests, docs). **Zero** `code_atlas/` edits.

### Axis 2 — design-conformance
All Approach bullets implemented-as-approved.

### Ph3/4 proven by
| Row | Evidence |
|-----|----------|
| AC1–2, W1 | `tests/test_claude_code_poke_index.py` 3 passed |
| C1 | no files under `code_atlas/` in diff |
| Full suite | `670 passed in 27.13s` |

## Phase 4 — Review

**Reviewed at** `1525687` (files: scripts/claude_code_poke_index.py, contrib/claude-code/*, README, proving tests, docs). Bookkeeping after marker is exempt from stale-review.

### Reviewer (`mango:reviewer` · round 1 · [dc1ece47](dc1ece47-9ef7-4bb3-aec9-63a167576082))
- **Verdict:** **CHANGES REQUESTED** (conditional LGTM once findings 1–2 land)
- **Scope:** diff ⊆ Gate-2 list; **zero** `code_atlas/` edits; proving suite 3→5 after fixes; `"async": true` present
- **Findings:**
  | Sev | Finding | Path | Resolution |
  |-----|---------|------|------------|
  | Important | Relative `../` paths skipped containment; absolute-only check | `scripts/claude_code_poke_index.py:33-42` | Fixed in `1525687`: resolve under root + `relative_to`; proving `test_repo_relative_rejects_parent_escape` |
  | Important | `load_config`/imports outside soft-fail → exit 1 on ConfigError | `scripts/claude_code_poke_index.py:45-63` | Fixed in `1525687`: full `try` wrap; proving `test_poke_exits_zero_on_bad_config_env` |

### Reviewer (`mango:reviewer` · verify-only · [10a4989c](10a4989c-89e2-4df1-9297-040fe1eb0b06))
- **Verdict:** **LGTM** at tip `1525687`
- **Proof:** freshness poke suite **5 passed**; both Important findings closed; no new Critical/Important

### Challenger (ticket-blind · [bd56f6bd](bd56f6bd-307e-4de7-aff6-35754b6dbc09))

| # | Rebuilt requirement | Verdict | Adjudication |
|---|---------------------|---------|--------------|
| 1 | Hook script pokes via incremental/reparse path | **met** | `reparse_file` (035 write path); not full `incremental_update` — ticket AC allows poke |
| 2 | Documented settings.json PostToolUse Edit/Write | **met** | `contrib/claude-code/settings.snippet.json` |
| 3 | README/docs install + behaviour | **met** | contrib README + root README pointer |
| 4 | Outside core; no lang branches | **met** | no `code_atlas/` / `adapters/` in diff |
| 5 | No index → no-op; never build | **met** | exit 0 if db missing; proving test |
| 6 | Cheap / non-blocking | **met** | `"async": true`; script always exits 0 |
| 7 | AC edit → next query reflects (035 or poke) | **can't tell** (live Claude Code) | **manual exclusion** — simulated stdin/CLI proved; live PostToolUse left to install check |
| 8 | AC no index → clean exit | **met** | — |
| 9 | AC install docs reproducible | **met** | — |

### Scope reconciliation
- File axis: ✅ approved list only (+ review fix inside poke script/tests)
- Behaviour axis: ✅ Approach as approved; review findings fixed
- Challenger #7: accepted manual-check exclusion (not a Gate-4 miss)

### Gate 4 status
**clean** — reviewer LGTM at `1525687`; challenger gaps adjudicated.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| Phase 0 | exposure-checker | 1 | unmeasured (blocking retrieval) |
| Phase 4 | mango:reviewer | 1 | unmeasured (blocking retrieval) |
| Phase 4 | mango:challenger | 1 | unmeasured (blocking retrieval) |
| Phase 4 | mango:reviewer (verify) | 2 | unmeasured (blocking retrieval) |

`LEDGER: 4 dispatch rows | all cells valued or marked unmeasured | complete`

### Durable lesson
See `docs/LESSONS.md` §036.

## Phase 5 — Finalise
- Status → done; BACKLOG + token row; lesson in LESSONS.md
- Outward: push branch + open PR (user-approved 2026-08-04)

## Session status

- **Ticket:** 036
- **work_doc_mode:** embed
- **working-doc path:** `docs/tasks/036_edit-index-hook.md`
- **Current phase:** finalise — outward push + PR
- **Blocked on:** —
- **Next action:** push + `gh pr create`
