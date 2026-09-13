---
id: 268
slug: twenty-four-descriptions-are-a-tax-paid-before-the-first-question
title: 'Ship the six-tool profile as an opt-in preset and pay down the operational debt that makes the server wrong by default in a worktree, silent on a first run, and expensive on a single walk — none of which needs a measurement first'
phase: 1.5b
milestone: Adoption
status: todo
depends_on: [260, 071, 119]
---

## Why this exists

Field round 18's keep-list is six tools: `get_index_status`, `search_symbol`, `read_symbol`, `find_callers`, `find_references`, `impact`. Twenty-four descriptions are a recognition tax the model pays before it asks anything. `CA_TOOLS` already exists (`main.py:160`), so **offering** the profile is nearly free — while **changing the default** without a number repeats the mistake this project has spent five rounds refusing. This ticket offers; [260](260_the-fit-number-cannot-be-observed-only-benchmarked.md) produces the number that may later change the default.

Four operational defects ride along, each cheap and each observed:

- **Worktree.** Parallel agents sit on worktrees; the server usually `cd`s to main. `index_root` tells the truth (071) and `CA_DB_PATH` is a runbook workaround — nobody reads a runbook at dispatch. Returning main's symbols with `reason: ok` to a worktree caller has been seen in a field probe.
- **First run is silent about roots.** `reachable_from` / `find_orphans` refuse without `CA_ENTRY_POINTS` — correct, and unhelpful. [119](119_reachability-signal-provenance.md) proved a stale glob put 560 files in the wrong bucket, so *nominating* candidates is not *guessing*.
- **One walk fills the context.** `reachable_from` at `standard` is ~160 KB (`impact_max_nodes` 500). Called once, never again.
- **Install friction.** Cloning the code-atlas monorepo and filling absolute paths is why a project does not switch the server on.

## Scope / Deliverables

- **Documented six-tool `CA_TOOLS` preset**, opt-in. **Default surface unchanged.**
- **Worktree-correct DB by default:** cwd inside a git worktree ⇒ the DB resolves under that worktree, or the call refuses with a reason naming `index_root` ≠ cwd. Never main's rows under `reason: ok`.
- **Nominate roots, never fill them:** first-run `get_index_status` proposes `CA_ENTRY_POINTS` / `CA_STUB_ROOTS` candidate globs with `files_matched`, for a human or agent to confirm. No auto-application.
- **`minimal` default on large walks** (`reachable_from`, `find_orphans`, verbose `architecture_overview`); `standard` on request.
- **One-line install** (`uvx` / `pipx`), enabling each adapter whose runtime is present.

## Constraints

- Do not change the default tool set in this ticket — that decision waits on 260's counter and [200](200_the-recognition-map-is-a-prompt-no-agent-can-read.md)'s probe.
- Nomination is not inference: candidates are listed, never applied, and a stale glob must stay visible as stale (119).
- No editor settings written (036/099).

## Acceptance criteria

- The preset is documented and tested; a test pins the default surface is still 24 (`tests/test_documented_tool_count.py` unchanged).
- A worktree fixture: the DB resolves under the worktree, or the payload refuses naming `index_root`; a test pins that main's rows can never return with `reason: ok` from a worktree cwd.
- First-run status lists candidate globs with `files_matched` and applies none.
- `reachable_from` default payload size drops measurably on a pinned sample, with `standard` still reachable by argument.
- The one-line install is exercised in CI or in the Docker test path.

## References
[260](260_the-fit-number-cannot-be-observed-only-benchmarked.md), [119](119_reachability-signal-provenance.md), `code_atlas/main.py:160`, `docs/runbooks/parallel-agents.md`, `docs/runbooks/onboarding-a-repo.md` §4, field retro round 18 keep-list.
