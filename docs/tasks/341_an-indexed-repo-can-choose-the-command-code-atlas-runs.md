---
id: 341
slug: an-indexed-repo-can-choose-the-command-code-atlas-runs
title: "An indexed repo's own .code-atlas.toml chooses the adapter argv code-atlas launches — opening an untrusted repo runs its command"
phase: 1
milestone: Agent-trust
status: done
depends_on: []
---

## Why this exists (public-launch security audit, 2026-09-27)

`_adapter_cmds` (`code_atlas/config.py:364-381`) builds each adapter's launch argv from the
`[adapter_cmd]` table of `<indexed repo>/.code-atlas.toml`, and `LanguageAdapter.start`
(`code_atlas/adapter.py:144`) hands it to `subprocess.Popen`. The indexed repo is **untrusted
content**: a repo that commits

```toml
[adapter_cmd]
php = ["sh", "-c", "<anything>"]
```

runs `<anything>` as the user on the first `build_or_update_index` — a call an agent makes on its
own, and one a prompt injection in the repo's text can ask for. The opt-in `contrib/git/`
post-checkout hook runs it on a plain `git checkout`.

The same file's `db_path` is joined onto the root with an absolute value winning
(`config.py:233`, `_as_path` at `:400`), so it can aim SQLite writes anywhere on disk.

This is the trust model VS Code (workspace trust), `direnv allow` and `mise trust` settle the same
way: a repo may *suggest* an executable setting; only the user may *enable* it.

## Goal

Nothing the indexed repo commits can choose a command code-atlas executes, or a path outside the
repo it writes to, unless the user has explicitly trusted it.

## Scope / Deliverables

1. `[adapter_cmd]` from the project file is honoured only when the environment sets
   `CA_TRUST_PROJECT_FILE=1` (the user's MCP client config or shell — a place the repo does not
   control). `CA_<LANG>_CMD` from the environment is unaffected.
2. Untrusted and present: a loud, actionable error (R5.3) naming the file, the languages it tried
   to set, and both ways out (set `CA_<LANG>_CMD`, or `CA_TRUST_PROJECT_FILE=1`) — never a silent
   ignore, which would read as "adapter missing".
3. `db_path` from the **project file** must resolve inside the root (no absolute path, no `..`
   escape); `CA_DB_PATH` from the environment keeps accepting any path.
4. README (config table, the Windows `[adapter_cmd]` example) and `docs/TOOLS.md` / PLAN §11 where
   they state the resolution order; a PLAN §19 decision row.

## Constraints

- **R1.1** — no language branch; the trust gate is generic over the table.
- **R5.3** — no silent fallback.
- `config_identity` (259) already hashes the project file as bytes; the trust variable is a
  build-affecting input only insofar as it changes which argv runs — decide and record whether it
  belongs in the `CA_*` identity slice.
- Existing tests that set `[adapter_cmd]` in a fixture project file set the trust variable, rather
  than being rewritten to env, so the file path stays covered.

## Acceptance criteria

- **AC1** A project file with `[adapter_cmd]` and no trust variable → `load_config` raises
  `ConfigError` naming the file and `CA_TRUST_PROJECT_FILE`; no process is launched. Red on today's
  code.
- **AC2** Same file with `CA_TRUST_PROJECT_FILE=1` → today's argv, unchanged.
- **AC3** `CA_<LANG>_CMD` set and no project table → works with no trust variable.
- **AC4** Project-file `db_path = "/tmp/x.db"` or `"../x.db"` → `ConfigError`; `CA_DB_PATH=/tmp/x.db`
  → accepted.
- **AC5** Env `CA_<LANG>_CMD` still overrides a trusted project table (resolution order unchanged).

## References
`code_atlas/config.py:25-26,224-233,343-400`; `code_atlas/adapter.py:135-150`; `README.md`
configuration table and the native-Windows section; `contrib/git/`; tickets 259 (config identity),
237 (Windows list-form argv).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 341 — an indexed repo cannot choose what code-atlas runs (working doc)

- **Ticket:** 341 · local · **SCOPE:** M · **TIER:** full · **TRACK:** backend
- **REVIEWER:** OFF (`--no-reviewer`) · **CHALLENGER:** ON
- **Current phase:** finalise
- **Session status:** done — autorun, PR open

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 1 claim(s) surfaced | 0 by symbol | 1 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`

The direction (opt-in trust, not removal, not a user-level file) was the maintainer's want-decision,
asked and answered in-session before the ticket was written (2026-09-27).

HOW1: the variable is `CA_TRUST_PROJECT_FILE`, not the ticket's first draft `CA_TRUST_PROJECT_CMD` —
any `CA_*_CMD` name matches `ADAPTER_CMD_ENV` and would be read as an adapter called
`trust_project`. Citation: `code_atlas/config.py:27`. The raw ticket was corrected before its first
commit, so no committed text names the old spelling.
HOW2: the trust flag stays out of `config_identity`'s `CA_*` slice — it decides whether a build may
start, never what it indexes, and the table's bytes are already hashed with the file. Citation:
Constraints ("decide and record"); `config.py` `_config_env_slice` (259).

Recalled (advisory): `prove-the-guard-fails` — AC1/AC4 are shown red against `main`'s `config.py`.

Exposure-checker: not dispatched — the one product decision was asked of the maintainer directly;
both remaining items are HOW with citations. Recorded in DISCLOSURE.

## Requirements matrix

`SECTIONS: 7 found (Why · Goal · Scope · Constraints · Acceptance · References · title) | 7 decomposed | ROWS: C=4 R=4 G=1 AC=5`

| ID | Source | Interpretation | Ph2 | Status |
|----|--------|----------------|-----|--------|
| G1 | Goal | nothing the repo commits chooses an executed argv or an outside write path, untrusted | D1 | ✅ |
| R1 | Scope 1 | file `[adapter_cmd]` honoured only with the env trust flag; env commands unaffected | D1 | ✅ |
| R2 | Scope 2 | untrusted + present → loud ConfigError naming file, languages, both ways out | D1 | ✅ |
| R3 | Scope 3 | file `db_path` repo-relative; `CA_DB_PATH` unrestricted | D1 | ✅ |
| R4 | Scope 4 | README, TOOLS, PLAN §11 + §19 row | D3 | ✅ |
| C1 | R1.1 | generic over the table — no language named | D1 | ✅ |
| C2 | R5.3 | no silent fallback | D1 | ✅ |
| C3 | 259 | trust flag's place in config identity decided + recorded | D1 | ✅ |
| C4 | Constraints | fixture tests that set the table set the trust flag, not rewritten to env | D2 | ✅ |
| AC1–AC5 | AC | proving | D2 | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause: `_adapter_cmds` merges the file table into the argv map with no provenance gate, and
  `_resolve("db_path", _as_path, …)` lets an absolute file value win `root / path`.
- Blast radius: `load_config` callers that write a `[adapter_cmd]` fixture (the full suite enumerates
  them — every one that goes red is a C4 site); `_as_repo_relative_list`, whose part check becomes
  the shared `_is_repo_relative` (R1.8), now also refusing a drive-letter prefix.

`TRACK: backend — 0/N UI`

`RULE SECTIONS: 4 applicable — 4 by change-type | 0 by recalled handle — R1.1 ✅ (no language branch) · R5.3 ✅ (loud error, no silent ignore) · R1.8 ✅ (one repo-relative rule for db_path and the list knobs) · R7.5 ✅ (comments ≤ 3 lines)`

`BASELINE: green`

Baseline: bare `pytest` on `2c184a4` (Linux, php · composer · node on PATH) → `4598 passed, 4 skipped`
(taken for 340 on the same base commit).

## Phase 2 — Design

`HANDLES: 1 recalled | 1 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- `prove-the-guard-fails` → traced: the proving file run against `main`'s `config.py` (Phase 3).

| # | Change | File | k/N |
|---|--------|------|-----|
| D1 | trust gate in `_adapter_cmds`; `_resolve_db_path`; shared `_is_repo_relative` | code_atlas/config.py | 1/1 |
| D2 | proving tests; trust flag added to the env of every fixture test that writes the table | tests/test_project_file_trust.py · fixture tests (C4) | 1/1 |
| D3 | docs + bookkeeping | README.md · docs/TOOLS.md · docs/PLAN.md · docs/TOKEN_LEDGER.md · docs/tasks/341_… | 1/1 |

| AC | risk | proof | provenance | match |
|----|------|-------|------------|-------|
| AC1 | untrusted table executes | pytest, `load_config` raises | authored | ✅ |
| AC2 | trusted table unchanged | pytest | authored | ✅ |
| AC3 | env needs no trust | pytest | authored | ✅ |
| AC4 | db_path escape | pytest, 5 shapes + env accepted | authored | ✅ |
| AC5 | env overrides trusted table | pytest | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_project_file_trust.py tests/test_config.py -q`

Rejected alternatives: removing the table (breaking for Windows users the README steers to it — the
maintainer chose trust); a user-level config file (a new config layer, larger scope); ignoring an
untrusted table with a warning (R5.3 — reads as "adapter missing").

`SCOPE: M`

## Phase 3 — Execute

**Branch:** fix/341-project-cmd-trust

Ran at 69b69b0

```
$ .venv/bin/python -m pytest tests/test_project_file_trust.py tests/test_config.py -q
79 passed
```

Red arm on `main`'s `config.py` (byte-identical to `main`): a project file with `[adapter_cmd]` and an
empty env returned `{'php': ('sh', '-c', 'echo pwned')}`, and `db_path = '/tmp/x.db'` resolved to
`/tmp/x.db` — AC1 and AC4 as the ticket describes them. C4: the first full run on the change found
37 failed + 114 errors, every one a fixture writing the table; 12 files now set the flag beside
their existing env, and none was rewritten to drop the table.

Design conformance: D1–D3 implemented-as-approved; `_is_repo_relative` also refuses a drive-letter
prefix, which tightens the existing list knobs the same way.

## Phase 4 — Review

REVIEWER: OFF (`--no-reviewer`) · CHALLENGER: ON — round 1 on `c82711e`: **CLEAN 13/0/0**.

| # | Note | Disposition |
|---|---|---|
| 1 | `host_root` / `container_root` from the project file accept any path, ungated | not exploitable today (`to_adapter_path` maps only repo-relative strings); BACKLOG follow-up in `69b69b0` |
| 2 | the identity-slice decision lived only in a test docstring | recorded in PLAN §19 in `69b69b0` |

## Phase 5 — Finalise (learning loop)

Lesson: `docs/LESSONS.md` § 341 — first sighting of `a-pattern-namespace-claims-every-name-of-its-shape`.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`LEDGER TOTAL: 88616 · top cost driver: review/challenger ×1 (1 dispatch; main-loop unmeasured)`
