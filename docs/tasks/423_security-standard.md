---
id: 423
slug: security-standard
title: "The security standard lives in the repo — every SEC criterion names the test, CI step or setting that holds it, and a conformance test refuses a row with none"
phase: 2
milestone: Trust
status: todo
depends_on: [422]
---

## Why this exists

0.9.1 (419–421) fixed one advisory, but the repo states no standard it holds itself to: a
criterion that is not written down cannot be checked, and one that is checked by nothing regresses
silently. The standard was drawn up in a 2026-10-27 audit against the MCP specification
(2026-07-28 security best practices and local-server guidance), OWASP (LLM and Agentic Top 10 2026,
MCP Top 10, MCP Security Cheat Sheet), CoSAI's MCP guide, OpenSSF Scorecard and the OSPS Baseline,
SLSA v1.2, the Docker/OWASP container rules and Claude Code's hooks and plugins references.
It has seven groups (`SEC-IN` untrusted repo input, `SEC-MCP` protocol and tool surface, `SEC-PI`
prompt injection and LLM output, `SEC-PL` plugin and hooks, `SEC-SC` supply chain and release,
`SEC-CT` container, `SEC-GV` governance). Tickets 424–431 close the open rows; this ticket makes
the standard binding first, so each later ticket fills its rows rather than inventing them.

## Acceptance

1. **`docs/SECURITY_STANDARD.md`** (tier 2, reached by pointer): one row per criterion — ID, the
   criterion, level (MUST/SHOULD), source, and **Verified by**: a test (`tests/…::name`), a CI step
   (a job/step name in a workflow), a repo setting checked by name, or `DOC` (a section that
   states it). A row not yet held reads `open: NNN` naming the ticket that closes it. A SHOULD row
   may be deferred only with its reason written in the row.
2. **Rule book §9 Security** in `docs/ENGINEERING_RULES.md`, short binding rules citing the IDs:
   the indexed repo, its index directory and database are untrusted input; a subprocess argument
   from repo, index or tool input is validated and fenced, and git runs hardened; every index
   write goes through `containment`; a tool-surface change is a reviewed diff with a CHANGELOG
   line; a security fix is developed privately and disclosed by advisory; every MUST criterion has
   a guard seen failing (R6.5). The size budget is raised only as argued, after R7.6 prunes.
3. **Conformance test** `tests/test_security_standard.py`: parses the standard and fails when a
   row's Verified-by names a test that does not exist, a CI step no workflow has, or an `open:`
   ticket whose task file is `done` or missing; and when a MUST row is deferred. Seen failing on a
   planted row with no guard (R6.5).
4. **Rows already held are wired now:** the criteria 419–421 closed point at their existing tests
   (`test_git_revision_arguments`, `test_index_artifact_trust`, `test_index_text_injection`, …),
   and rows held by existing guards (SQL confinement, no HTTP transport, adapter command gate)
   point at theirs; where no guard exists the row is `open:` on the ticket that adds one.
5. **`SECURITY.md` rewritten** from the standard's trust model: who is trusted for what (the user
   and their environment; the client's tool arguments; the indexed repo including a committed index
   — untrusted; network responses; dependencies and Actions as pinned), every network call
   code-atlas makes, every git command it runs, the client-side controls a user should keep on
   (tool approval, no auto-update of a branch-tracking marketplace), and the known limitations
   carried from 0.9.1 — naming git filter drivers (`filter.<name>.clean`/`process`), which no
   per-command override covers, among the repo config that still applies. A test keeps the listed
   git commands equal to the ones `gitutil` runs.

Out of scope: closing any open row — each belongs to 424–431. The repo-settings drift check is 424.

## Call sites

New: `docs/SECURITY_STANDARD.md`, `tests/test_security_standard.py`. Changed: `SECURITY.md`,
`docs/ENGINEERING_RULES.md` (§9, pre-PR self-check), `tests/test_doc_size_budget.py` (argued),
`code_atlas/gitutil.py` (read only, by the doc test).

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 423 — security standard in the repo (working doc)

- **Ticket:** 423 · `docs/tasks/423_security-standard.md`
- **Type:** enhancement
- **Repo(s) / Porting:** app (`.`)
- **SCOPE:** M
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** red
  <!-- baseline exclusions: tests/test_install_skew.py::test_a_checkout_behind_the_core_is_named_with_its_fix and tests/test_release_discipline.py::test_the_plugin_hook_names_a_skew_against_the_installed_package — host only, the installed uv tool is 0.7.0 (older than the checkout); green in CI on main (PR #120). tests/test_no_client_identifiers.py::test_no_foreign_tracker_key_appears_in_any_tracked_file is NOT excluded: a845b772 (the 423–431 task files) introduced it; this ticket fixes it (AC1 makes the SEC IDs legal). -->
- **REVIEWER:** ON · **CHALLENGER:** ON

---

## Phase 0 — Refine

`PREMISE: 11 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`
`RECALL: 3 claim(s) surfaced | 0 by symbol | 3 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`

refine skipped: 0 unresolved product-decisions. The criteria, levels, rule numbering and the
`open: NNN` convention were decided with the owner on 2026-10-27 (decisions D1–D7, private plan);
the ticket text states each.

Referenced-as-existing (all resolve): `SECURITY.md`, `docs/ENGINEERING_RULES.md`,
`tests/test_doc_size_budget.py`, `code_atlas/gitutil.py`, `code_atlas/containment.py`,
`tests/test_git_revision_arguments.py`, `tests/test_index_artifact_trust.py`,
`tests/test_index_text_injection.py`, `tests/test_sql_confinement.py`, `REFRESH_HINTS`-era 421
tests, task files 424–431. To-be-created: `docs/SECURITY_STANDARD.md`,
`tests/test_security_standard.py`.

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | 408-C1 `a-docs-change-runs-every-doc-budget` | 2 | handle (docs change) | yes — rule book and tier 1 both near their ceilings |
| 2 | 414-C1 `run-the-ac-on-main-before-the-design` | 2 | handle (conformance premise) | yes — AC4 "rows already held" is a claim about today's tests |
| 3 | 411-C1 `a-baseline-needs-a-frozen-tree` | 2 | handle (baseline) | yes — baseline run on a committed tree, no edits during it |

**Constraints surfaced from the scan:**
- R7.6 / `test_doc_size_budget.py`: `ENGINEERING_RULES.md` is at 5,949 / 5,960; tier 1 at ~19,890 / 19,900.
- R2.4: the standard names no customer, employer or private project.
- R7.5: comments ≤ 3 lines.

**Exposure-checker:** not dispatched (refine skipped).

---

## Requirements matrix

`SECTIONS: 3 found (Why this exists, Acceptance, Call sites) | 3 decomposed | ROWS: C=3 R=0 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why | "this ticket makes the standard binding first" | every SEC row names its guard or its ticket | no standard in repo (`ls docs`) | | | ⚠ |
| AC1 | Acc 1 | "one row per criterion … Verified by … `open: NNN`" | `docs/SECURITY_STANDARD.md`, 7 groups, every row has ID/criterion/level/source/verified-by | absent | | | ⚠ |
| AC2 | Acc 2 | "Rule book §9 Security … raised only as argued" | R9.1–R9.6 in `ENGINEERING_RULES.md`, citing IDs; budget argued | §8 is last (`ENGINEERING_RULES.md:283`) | | | ⚠ |
| AC3 | Acc 3 | "Conformance test … fails when … Seen failing on a planted row" | `tests/test_security_standard.py` with 4 failure modes, each seen failing | absent | | | ⚠ |
| AC4 | Acc 4 | "Rows already held are wired now" | rows 419–421 closed and rows held by older guards name real tests | tests listed in Phase 1 | | | ⚠ |
| AC5 | Acc 5 | "`SECURITY.md` rewritten … A test keeps the listed git commands equal" | trust table, network calls, git commands, client controls, limitations incl. filter drivers; doc-vs-code test | `SECURITY.md` has guarantees, no trust table, no command list | | | ⚠ |
| C1 | Out of scope | "closing any open row — each belongs to 424–431" | no code change outside docs/tests | | | | ⚠ |
| C2 | Out of scope | "The repo-settings drift check is 424" | SET rows stay `open: 424` | | | | ⚠ |
| C3 | Call sites | "`code_atlas/gitutil.py` (read only, by the doc test)" | gitutil unchanged | | | | ⚠ |

Status legend: ✅ done/proven · ⚠ deferred (needs follow-up ticket) · ❌ not met.

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-----------------|
| AC1 | seven groups, one row per criterion | IN 14 · MCP 9 · PI 6 · PL 8 · SC 16 · CT 5 · GV 7 = 65 rows | Y | measurable: the test counts rows per prefix and IDs are unique | — |
| AC2 | rules citing the IDs | 6 rules (R9.1–R9.6); each names ≥ 1 `SEC-` ID present in the standard | Y | greppable: the conformance test checks every cited ID exists | — |
| AC3 | fails on 4 conditions, seen failing | 4 planted-row fixtures (missing test, missing CI step, `open:` on a done/missing ticket, deferred MUST) | Y | measurable: each red before the parser handles it | — |
| AC4 | held rows point at existing tests | every `T` row resolves to `tests/<file>.py::<name>` that exists (AST) | Y | measurable | — |
| AC5 | listed git commands equal to `gitutil`'s | `ls-files`, `rev-parse`, `diff`, `config` (`gitutil._run` callers) + `ls-remote` (`release_check/__init__.py:75`) | Y | measurable: set equality against an AST read of the call sites | — |
| AC5 | trust table, network calls, client controls | prose sections | — | headings greppable; adequacy is a manual-check exclusion (reviewer reads) | — |

## Inventory (universal "every" requirements)

- **Denominator N (criteria):** 65 — `SEC-IN-01..14`, `SEC-MCP-01..09`, `SEC-PI-01..06`,
  `SEC-PL-01..08`, `SEC-SC-01..16`, `SEC-CT-01..05`, `SEC-GV-01..07`. The conformance test is the
  per-item checklist: it resolves every row, so review reads its parametrised ids, not a total.
- **Denominator N (git commands):** 5 — `ls-files`, `rev-parse`, `diff`, `config`, `ls-remote`.

## Clarifications

`CLARIFICATION: 4 raised | 4 self-resolved (cited) | 0 for human decision`

- Self-resolved:
  1. Repo settings are on (B0) but nothing reads them back → SET rows read `open: 424`. Ticket
     AC1 ("a repo setting checked by name") + Out of scope ("drift check is 424").
  2. `SEC-SC-13` (PyPI trusted publishing) is a conditional MUST that does not apply → the row
     reads `n/a: no PyPI release (431)`, and the test allows `n/a` only with a reason.
     `docs/tasks/431_release-pipeline.md` Call sites ("13 recorded N/A: no PyPI").
  3. A partly held row (e.g. `SEC-IN-01`: wide containment tests, residuals in 430) reads
     `open: 430`, naming the existing tests as `partly:`. Ticket AC1 ("A row not yet held reads
     `open: NNN`").
  4. The wiki rows (`SEC-WK-*`) are not in this standard → ticket "It has seven groups".
- For human decision: none.

---

## Phase 1 — Analysis ✋ Gate 1

`BASELINE: red — test_install_skew::test_a_checkout_behind_the_core_is_named_with_its_fix (host), test_release_discipline::test_the_plugin_hook_names_a_skew_against_the_installed_package (host), test_no_client_identifiers::test_no_foreign_tracker_key_appears_in_any_tracked_file (introduced by a845b772 on this branch)`

Ran at `436df1b8`

```
$ .venv/bin/python -m pytest -q --no-header -p no:cacheprovider
FAILED tests/test_install_skew.py::test_a_checkout_behind_the_core_is_named_with_its_fix
FAILED tests/test_no_client_identifiers.py::test_no_foreign_tracker_key_appears_in_any_tracked_file
FAILED tests/test_release_discipline.py::test_the_plugin_hook_names_a_skew_against_the_installed_package
3 failed, 5108 passed, 4 skipped in 658.20s (0:10:58)
```

The tracker-key guard reads `SEC-MCP-09` as a foreign key `SEC-MCP-09` (`tests/test_no_client_identifiers.py:57`).
Every `SEC-` ID in the task files 424–431 trips it; the standard would trip it 65 times. The
fix belongs here: the guard learns the standard's own ID shape, nothing wider.

- **Gap analysis (enhancement):**
  - G1/AC1: no standard in the repo (`ls docs/` — no `SECURITY_STANDARD.md`).
  - AC2: rule book ends at §8 (`docs/ENGINEERING_RULES.md:283`), then the pre-PR self-check.
  - AC3: no conformance test; the pattern to follow is `tests/test_backlog_bookkeeping.py`
    (derived reader, guards the guard).
  - AC4: held today, by test — `test_git_revision_arguments.py` (5 tests: SEC-IN-02, SEC-IN-14 local),
    `test_index_artifact_trust.py` (9: SEC-IN-04, SEC-IN-05, SEC-IN-12 index part), `test_index_text_injection.py`
    (11: SEC-IN-08, SEC-MCP-06), `test_sql_confinement.py` (SEC-IN-06 part), `test_project_file_trust.py` (SEC-IN-03
    `adapter_cmd` part), `test_symlink_containment.py` (SEC-IN-01 part). Rows SEC-MCP-01, SEC-MCP-02, SEC-IN-07,
    SEC-PI-06, SEC-SC-03, SEC-SC-14 have no guard → `open:` on the ticket that adds one (428 for SEC-MCP-01/02;
    new guards for SEC-IN-07/SEC-SC-03/SEC-SC-14 belong to 424; SEC-PI-06 to 429).
  - AC5: `SECURITY.md` has guarantees and limitations (1,145 tokens) but no trust table, no network
    or git command list, no client-side controls; filter drivers unnamed.
- **Blast radius:** docs (`SECURITY.md`, `docs/ENGINEERING_RULES.md`, new
  `docs/SECURITY_STANDARD.md`), tests (`tests/test_security_standard.py`,
  `tests/test_doc_size_budget.py`, `tests/test_agent_chain_budget.py` if tier 1 moves). No code
  under `code_atlas/`, no contract, no tool surface. Tier 1 grows by §9 (rule book is tier 1).

`RULE SECTIONS: 8 applicable — 8 by change-type | 0 by recalled handle — §1 (change-type) N/A because no core module changes · §2 (change-type) ✅ R2.4: the standard and SECURITY.md cite public sources and CVE IDs only, no customer or employer name · §3 (change-type) N/A because no contract vocabulary changes · §4 (change-type) N/A because no core code · §5 (change-type) ✅ R5.3: the conformance test fails loud naming the row and the missing guard · §6 (change-type) ✅ R6.5: each AC3 failure mode seen failing on a planted row · §7 (change-type) ✅ R7.2 ledger row, R7.5 comments ≤ 3 lines, R7.6 prune what §9 supersedes in SECURITY.md and argue both budgets · §8 (change-type) N/A because no dependency is added`

- **TRACK:** `TRACK: backend — 0/5 touched files under UI paths`
- **SCOPE:** M · **TIER:** full (universal requirement, N = 65 > 1; security-tagged)
- **Gate 1 status:** approved 2026-10-30 (owner: "choose the best approach … complete the work
  autonomously")

---

## Phase 2 — Design ✋ Gate 2

`HANDLES: 3 recalled | 3 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- 408-C1: `scripts/agent_chain_cost.py` → tier 1 19,883 / 19,900; `ENGINEERING_RULES.md` 5,949 / 5,960,
  `CONVENTION.md` 7,149 / 7,150 — §9, the §8.1 row and the AGENTS.md pointer each need an argued raise.
- 414-C1: every test the standard names was listed from its file (`grep '^def test_'`) on `436df1b8`
  before a row was drafted; none is cited from memory.
- 411-C1: baseline ran on the committed `436df1b8`, nothing edited during it.

**Approach.** The standard is a Markdown file a test parses. Each row's *Verified by* is a
`;`-separated list of typed items — `test: tests/<file>.py::<name>`, `ci: <step or job name>`,
`doc: <path>#<heading>`, `open: NNN`, `n/a: <reason>`, `deferred: <reason>` — so the parser needs
no free-text judgement. A row is **held** when it has no `open:`; a held MUST names at least one
`test:` or `ci:` (R9.6), `deferred:` is SHOULD-only, `n/a:` needs a reason. A partly held row
carries both its tests and `open:`. A repo setting gets no item kind yet: nothing reads one back
until 424's drift check, so those rows read `open: 424` and 424 adds the kind with its reader.
One function, `problems(row)`, is used by the per-row test and by the planted-row test (guards the
guard, R6.5).

Every row with no guard today is owned by a ticket: where 424–431 did not list it, the ticket gains
the row and one AC line — 424: SEC-IN-07 grep gate, SEC-SC-14 binary sweep, SEC-PL-06 `plugin validate`,
SEC-GV-01/SEC-GV-04 and SEC-SC-09's setting in the drift check; 427: SEC-PL-07 skill-text lint; 429: SEC-PI-06 inert
agent-config fixture; 431: SEC-GV-02 changelog `Security` section test. SEC-IN-06 is held today by
`test_store` and the LIKE-wildcard test, so it gets no ticket.

The tracker-key guard accepts `SEC-<GROUP>-NN` with `GROUP` in the standard's closed set — the
guard reads the set from one constant, nothing wider.

**Rejected:** (a) a YAML/JSON standard rendered to Markdown — two files to keep in step (R6.7);
(b) free-text *Verified by* matched by regex — a typo would read as held; (c) a `set:` kind now with
no reader — a setting nobody checks is the drift the standard exists to stop.

**Change list** (traced to matrix rows):

| # | File | Change | Rows |
|---|------|--------|------|
| 1 | `docs/SECURITY_STANDARD.md` (new) | 65 rows, 7 groups, grammar preamble | G1, AC1, AC4, C2 |
| 2 | `tests/test_security_standard.py` (new) | parser, per-row resolution, ID shape, planted rows, §9 citations, SECURITY.md git list = code | AC2, AC3, AC4, AC5 |
| 3 | `docs/ENGINEERING_RULES.md` | §9 R9.1–R9.6; self-check names §9 | AC2 |
| 4 | `SECURITY.md` | rewrite: trust table, guarantees, network calls, git commands, client controls, limitations (filter drivers; residuals now on 427/430) | AC5 |
| 5 | `tests/test_no_client_identifiers.py` | accept `SEC-<group>-NN` from the standard's group set | baseline fix |
| 6 | `docs/tasks/424,427,429,431_*.md` | own the unticketed rows (AC line + call-site rows) | AC1 (`open:` names a real owner) |
| 7 | `docs/CONVENTION.md` §8.1, `AGENTS.md` tier-2 list | one row / one pointer for the new standing doc | AC1 (tier 2, reached by pointer) |
| 8 | `tests/test_doc_size_budget.py`, `tests/test_agent_chain_budget.py` | argued raises | AC2 |
| 9 | `docs/TOKEN_LEDGER.md`, `docs/BACKLOG.md`, frontmatter | spend row, row out, `done` | R7.2 |

No file under `code_atlas/` changes (C1, C3).

**Proving tests:** `test_security_standard.py::test_a_planted_row_is_refused` (one case per failure
mode: missing test, missing CI step, `open:` on a done ticket, `open:` on a missing ticket, deferred
MUST, held MUST with only `doc:`, unknown kind, empty) — each seen failing against a `problems()`
that returns `[]`; `::test_security_md_names_every_git_command_code_atlas_runs` seen failing on the
current `SECURITY.md` (it names no `ls-remote`, no `--version`).

`EXCLUSIONS: 1 recorded | 1 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

- AC5 prose adequacy (trust table, client controls) is not machine-checkable → the reviewer reads
  it at Gate 4 (expiry: Gate 4 verdict).

**Rule check:** R2.4 (public sources and CVE/GHSA ids only) · R5.3 (each failure names row + item)
· R6.5 (planted rows) · R6.7 (one parser, group set from one constant) · R7.5 · R7.6 (SECURITY.md's
BACKLOG pointers replaced, not added to).

- **Gate 2 status:** approved under the owner's standing autonomy grant (2026-10-30)

---

## Phase 3 — Execute

Change list held: 14 files, all in the approved list (rows 1–8; row 9 is finalise). Two additions
inside approved rows, recorded here: 428 also gained `SEC-MCP-01` (the standard names it `open: 428`
and 428 listed only 02..05, 07), and AGENTS.md paid for its pointer by dropping the 373-tree pytest
count the expected count supersedes (R7.6). The tracker-key guard also learned `OSPS-<family>-NN`
and `CWE`: the standard cites OSPS Baseline controls and CWE ids, both standards.

Seen failing (R6.5), before the docs they check existed:

```
$ pytest tests/test_security_standard.py            # standard written, SECURITY.md and §9 not yet
FAILED ...::test_every_row_names_what_holds_it[SEC-MCP-08]   # doc: SECURITY.md#Trust model — no heading
FAILED ...::test_every_row_names_what_holds_it[SEC-SC-13]    # a ';' inside the n/a reason split it
FAILED ...::test_every_row_names_what_holds_it[SEC-GV-02]    # doc: ENGINEERING_RULES.md#9. Security — none
FAILED ...::test_every_row_names_what_holds_it[SEC-GV-03]
FAILED ...::test_every_row_names_what_holds_it[SEC-GV-06]
FAILED ...::test_section_9_cites_only_criteria_the_standard_has
FAILED ...::test_security_md_names_every_git_command_code_atlas_runs   # no "Git commands" section
7 failed, 74 passed

$ python - # test_a_planted_row_is_refused against problems = lambda row: []
11 of 11 planted cases fail against problems() -> []
```

The git-command reader first counted `nudge.py`'s `tokens[:2] == ["git", "grep"]` — a comparison,
not a spawn; it now reads only `_run(...)` and `<spawn>([...])` call sites.

Targeted run after the docs landed: `test_security_standard` 81 passed; with
`test_no_client_identifiers`, both budget tests, `test_backlog_bookkeeping` and
`test_every_test_is_collected`: 298 passed. `ruff check tests/` clean. AGENTS.md's "through
0.9.0" also became "0.9.1" (true since 422; one word, recorded here).

---

## Phase 4 — Review ✋ Gate 4

**Challenger round 1** (ticket-blind): 10 met · 2 partly · 0 not met. Partly: (1a) no repo-setting
item kind — deliberate, `open: 424` (Clarification 1); (4) SEC-MCP-01 stays `open: 428`, since no
test asserts the absence of an HTTP transport and the ticket's own rule is "where no guard exists
the row is `open:`". Its two parser findings (a helper accepted as a test; a workflow `name:`
accepted as a CI step) were fixed — see reviewer 5.

**Reviewer round 1:** CHANGES REQUESTED, 4 Important + 3 Minor, all taken:

| # | Finding | Fix |
|---|---------|-----|
| 1 | SECURITY.md said every index file goes through `containment`; the onboarding cache does not | guarantee narrowed to the build and server; new limitation; SEC-IN-04 `open: 430`; 430 AC6 routes the cache through `containment` |
| 2 | SEC-IN-06 cited the confinement test, which does not guard binding | test dropped; `open: 424`; 424 AC7 adds an AST guard on `store.py` |
| 3 | SEC-GV-03 tested git commands only | `test_security_md_names_every_package_that_reaches_the_network`, seen failing on a copy missing `onboarding_llm/` |
| 4 | SEC-IN-05 overclaimed; SEC-IN-14 `open: 430` not owned by 430 | criterion says "where SQLite supports it", `open: 430`; 430 now lists SEC-IN-04, 05, 14 and asserts extension loading off |
| 5 | parser: helpers, workflow names, non-literal git subcommands | only `test*` defs without a skip mark; job/step names only; a built subcommand reads `NON_LITERAL`; two planted cases added |
| 6 | `HEAD` is also accepted | SECURITY.md says so |
| 7 | 4-line comment (R7.5); 0.9.1 bump unrecorded | trimmed to 3; recorded in Phase 3 |

---

## Decision log

| When | Decision | Why |
|------|----------|-----|
| 2026-10-30 | refine skipped; TIER full, SCOPE M | 0 open product decisions; N = 65; security-tagged |

## Session status

- **Last updated:** 2026-10-30
- **work_doc_mode:** embed · working doc: `docs/tasks/423_security-standard.md` (below the separator)
- **Current phase:** analysis
- **Next action:** owner approves Gate 1, then design writes the change list
- **Blocked on:** Gate 1
