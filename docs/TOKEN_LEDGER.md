# Token ledger — code-atlas

One spend row per ticket, required before its PR opens
([`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) R7.2). It lives here rather than in
[`BACKLOG.md`](BACKLOG.md) because it is **tier 2**: a per-ticket retrospective is consulted when
somebody asks what a ticket cost, and is never read to learn a rule — yet in BACKLOG it was charged
to every session, 4,773 tokens of the chain's 49,572 (task 133). Append-only by rule, so it carries
no size ceiling; `tests/test_backlog_bookkeeping.py` reads the table below by heading.

**Reset for phase 2 (2026-09-27).** Phase 1's rows (335 tickets) were archived with its task files; they
linked PRs of the pre-public repository, whose numbers this one reuses. Rows below are phase 2's.

**Is NOT** the per-phase breakdown (→ each task's `tasks/NNN_slug.md` working-doc ledger); not task
status (→ [`BACKLOG.md`](BACKLOG.md)); not rationale (→ [PLAN §19](PLAN.md#19-project-context--decision-log)).

## Token usage

Token spend per task, recorded before its PR is opened
([`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) R7.2); the per-phase breakdown lives in each
task's `tasks/NNN_slug.work.md`
ledger. mango measures **subagent dispatch only**: `unmeasured` = the host surfaced no usage block, and
**main-loop spend is unmeasured unless a fresh/cache figure is given** (`rtk gain` is global and cannot
be attributed to one task, so nothing is invented). `no work doc` = the task skipped the mango
lifecycle. Fresh = input + output + cache-creation; cache reads are billed differently and listed apart.

| # | Tokens | PR |
|---|---|---|
| 343 | 1 dispatch: ticket-blind `challenger` round-1 **CLEAN** (55,473 fresh); `reviewer` waived by `--no-reviewer`; main-loop unmeasured. `/mango:autorun 343 --no-reviewer`. Claude Code keeps a 2,048-char prefix (probe, 2.1.284); instructions render in priority order at 1,686. Proving: `tests/test_server_instructions.py::test_instructions_fit_under_the_client_cap_on_every_state`. GATE GREEN (21/21 checks, Linux, bare pytest). | [#6](https://github.com/cuongdinhngo/code-atlas/pull/6) |
| 344 | 3 dispatches: refine exposure-checker (43,020 fresh), ticket-blind `challenger` round 1 (56,095 fresh — found the gitignored `.mcp.json`, fixed in `07fbfb86`), plugin-format docs research (80,923 fresh); `reviewer` waived by `--no-reviewer`; main-loop unmeasured. `/mango:autorun 344 --no-reviewer`. Plugin at `contrib/claude-code/plugin/`; live install from a clone: server connected, all four hooks fired. Found: a pipe-joined hook `if` never matches on 2.1.284. Proving: `tests/test_claude_code_plugin.py::test_the_plugin_hook_list_matches_the_snippet`. GATE GREEN (21/21 checks, Linux, bare pytest). | [#7](https://github.com/cuongdinhngo/code-atlas/pull/7) |
| 345 | 2 dispatches: refine exposure-checker (44,332 fresh), ticket-blind `challenger` round 1 (65,558 fresh — unscoped EXEC fixed); `reviewer` waived by `--no-reviewer`; main-loop unmeasured. `/mango:autorun 345 --no-reviewer`. Contract v13 `symbol_shapes`; `code-atlas-nudge` quoted live by the model after a Grep and a Bash grep. Proving: `tests/test_grep_nudge.py::test_anchor_shapes_fire_once_per_kind`. GATE GREEN (21/21 checks, Linux, bare pytest, after one red run: 4 findings fixed). | [#8](https://github.com/cuongdinhngo/code-atlas/pull/8) |
| 346 | 1 dispatch: ticket-blind `challenger` round 1 **CLEAN** (47,883 fresh); `reviewer` waived by `--no-reviewer`; refine self-skipped (no exposure-checker); main-loop unmeasured. `/mango:autorun 346 --no-reviewer`. The signal emits `additionalContext` for the payload's event; quoted live by the model after a `Read` (PostToolUse) and a new-file `Write` (PreToolUse), plain-stdout control `NONE`. Proving: `tests/test_write_time_signal.py::test_hook_stdin_payload_and_always_exit_zero`. GATE GREEN (21/21 checks, Linux, bare pytest). | [#10](https://github.com/cuongdinhngo/code-atlas/pull/10) |
| 347 | 1 dispatch: ticket-blind `challenger` round 1 **CLEAN** (48,510 fresh); `reviewer` waived by `--no-reviewer`; refine self-skipped (no exposure-checker); main-loop unmeasured. `/mango:autorun 347 --no-reviewer`. The summary leads with `rebuild required` (both contract versions, the full-build route) on an older-era index at any staleness and detail level; the state hook speaks for it at an unmoved HEAD; quoted live from this repo's v10 index as the instructions' first line. Proving: `tests/test_contract_rebuild_refusal.py::test_the_summary_names_the_pending_rebuild_at_an_unmoved_head`. GATE GREEN (21/21 checks, Linux, bare pytest). | [#11](https://github.com/cuongdinhngo/code-atlas/pull/11) |
| 348 | 2 dispatches: refine exposure-checker (40,984 fresh — surfaced three want-decisions, all answered by the maintainer), ticket-blind `challenger` round 1 **CLEAN** (54,257 fresh); `reviewer` waived by `--no-reviewer`; main-loop unmeasured. `/mango:autorun 348 --no-reviewer`. 0.2.0, the first versioned release: `CHANGELOG.md` heading test-gated against contract and schema; `code-atlas-state --expect-version` names plugin/package skew; README upgrade section from a spike (a plugin moves only on a version bump plus `claude plugin update`). Tag deferred to after merge. Proving: `tests/test_release_discipline.py::test_the_top_release_is_the_code_that_ships`. GATE GREEN (21/21 checks, Linux, bare pytest). | [#12](https://github.com/cuongdinhngo/code-atlas/pull/12) |
| 349 | 0 dispatches: no mango lifecycle (a data-only re-floor, resolving issue #4); main-loop unmeasured. Bisected flask's edge count over `main`'s first-parent history to 258 (`6e6f577`): a multi-match bare CALL is one unresolved edge, so socketio, flask, pydantic and requests lost edges at unchanged files and nodes. `min_edges` re-floored at ≈80% of the post-258 build. Proof: `scripts/cross_repo_validate.py --public-only --skip-clone` 11 ok / 0 failed (was 9 / 2). | [#13](https://github.com/cuongdinhngo/code-atlas/pull/13) |
