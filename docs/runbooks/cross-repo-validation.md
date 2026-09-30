# Cross-repo validation (task 018 / Plan §16 / R6.3)

Prove each adapter follows its language standard across **several varied repos**, not one
sample. Per-PR CI stays fixture-only ([`ci.yml`](../../.github/workflows/ci.yml)); this path is
**opt-in / scheduled** only.

## Public samples (pinned)

Manifest: [`scripts/cross_repo_samples.json`](../../scripts/cross_repo_samples.json)

| Kind | Checkout | Role |
|------|----------|------|
| `laravel_app` | `laravel/laravel` | php — framework app |
| `symfony_app` | `symfony/demo` | php — framework app |
| `psr4_library` | `brick/math` | php — small PSR-4 library |
| `ts_library` | `sindresorhus/ky` | typescript — small library |
| `ts_js_mixed` | `mqttjs/MQTT.js` | typescript — mixed TS/JS |
| `compiled_beside_source` | `socketio/socket.io` | typescript — build output beside source |
| `python_library` | `pallets/flask` | python — decorator-heavy framework |
| `python_src_layout` | `pydantic/pydantic` | python — `src/` layout |
| `python_flat_package` | `psf/requests` | python — flat package |
| `tsql_oltp_schema` | `microsoft/sql-server-samples` (sparse) | sql — one OLTP install script |
| `tsql_dw_tables` | `microsoft/sql-server-samples` (sparse) | sql — SSDT warehouse tables |

Every row is pinned to a SHA in the manifest; the manifest is the source of truth for the list.

Pins live **outside** `adapters/` so R2.2 never sees framework/repo names in adapter source. Each
row names its `language`; the harness resolves that adapter's command from `_ADAPTERS` — adding a
language is a manifest row plus an `_ADAPTERS` row, never a branch.

## Run locally

```bash
# optional cache / report paths (defaults under artifacts/, gitignored)
# export CODE_ATLAS_CROSS_REPO_CACHE=artifacts/cross-repo-cache
# export CODE_ATLAS_CROSS_REPO_REPORT=artifacts/cross-repo-report.json
# Every language in the manifest needs its adapter runnable. The TS adapter requires its own
# runtime deps, or it exits before announcing itself:
npm ci --prefix adapters/typescript
npm ci --prefix adapters/sql

# Prefer an absolute adapter path (sample builds use the sample as cwd).
export CA_PHP_CMD="php $(pwd)/adapters/php/index.php --server"
export CA_TYPESCRIPT_CMD="node $(pwd)/adapters/typescript/index.js --server"
export CA_PYTHON_CMD="python3 $(pwd)/adapters/python/index.py --server"
export CA_SQL_CMD="node $(pwd)/adapters/sql/index.js --server"

python3 scripts/cross_repo_validate.py
# Re-run against existing checkouts, no network:
python3 scripts/cross_repo_validate.py --public-only --skip-clone
# GHA-equivalent (skip private scale fold-in):
python3 scripts/cross_repo_validate.py --public-only
```

Both vars have a working absolute default, so unset is fine when you launch from this repo; the
harness also rewrites a repo-relative `adapters/<lang>/…` to an absolute path. Each sample's
`graph.db` is deleted before its build — a cached checkout whose db predates a schema bump would
otherwise be refused rather than rebuilt.

### Pass bar (A2 / A5)

- Build **completes without crash** for each public sample.
- Per-sample floors in the manifest (`min_files` / `min_nodes` / `min_edges`, ≈80% of a
  known-good smoke at that SHA). Bump floors when bumping a pin, and re-floor in the same PR
  when a change moves the counts by design ([AGENT_BRIEF P8](../AGENT_BRIEF.md)).
- Parse failure ratio `failed/files <= 0.02` on public samples (catches mass-parse regressions
  without requiring `failed == 0`). Isolation “one bad file does not abort the build” is proven in
  per-PR fixtures and the harness mini-repo test.
- The JSON report is written **even when a sample fails** (`ok: false` + `error`); exit code 1 if
  any public row failed.

## Large / private monorepo (optional)

Same operator path as task 015 — see [`scale-sample.md`](scale-sample.md).

```bash
export CODE_ATLAS_SCALE_SAMPLE=/path/to/large-php-monorepo
python3 scripts/cross_repo_validate.py   # runs public trio, then scale_full_build when env set
```

If `CODE_ATLAS_SCALE_SAMPLE` is unset, the scale step is **skipped** (not a failure) — correct for
public GHA and for laptops without the private checkout (A4, ratified for shipping public half).

## CI

[`.github/workflows/cross-repo.yml`](../../.github/workflows/cross-repo.yml):

- `workflow_dispatch` (manual)
- weekly `schedule` (Monday 06:00 UTC)
- public samples only (`--public-only`)
- on failure: opens/comments a `cross-repo-validation` GitHub issue (Actions tab is otherwise easy
  to miss for scheduled jobs)

**Outside the gate:** neither `ci.yml` nor `scripts/gate.sh` runs it, so a count a change moves
surfaces only here, up to a week later. The first GitHub run was 2026-09-28 (the repo went public
2026-09-27); it failed on floors that predated 258 — issue #4, re-floored by 349.

**Note:** GitHub disables `schedule` triggers after **60 days of repository inactivity**. A quiet
repo silently stops validating — re-run via `workflow_dispatch` or push to re-enable.
## Construct gaps → task 007

When a sample surfaces a language construct the adapter mishandles or skips, record it here and
mirror a bullet under **Follow-ups** in [`docs/BACKLOG.md`](../BACKLOG.md) so task 007 / 025 can
absorb it. Do **not** encode the sample’s names or layout into `adapters/php`.

### Gap log (fill during / after a run)

| Date | Sample id | Construct / symptom | Notes / follow-up |
|------|-----------|---------------------|-------------------|
| _(none yet)_ | | | |

## What this does *not* do

- No third-party clones in per-PR `ci.yml`.
- No adapter branches for sample directory or framework names (R2 / Standard over sample).
- No numeric SLA on elapsed time for public samples (report is diagnostic).
