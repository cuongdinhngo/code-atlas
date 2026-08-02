# Cross-repo validation (task 018 / Plan §16 / R6.3)

Prove the PHP adapter follows the language standard across **several varied repos**, not one
sample. Per-PR CI stays fixture-only ([`ci.yml`](../../.github/workflows/ci.yml)); this path is
**opt-in / scheduled** only.

## Public samples (pinned)

Manifest: [`scripts/cross_repo_samples.json`](../../scripts/cross_repo_samples.json)

| Kind | Checkout | Role |
|------|----------|------|
| `laravel_app` | `laravel/laravel` @ pinned SHA | framework app |
| `symfony_app` | `symfony/demo` @ pinned SHA | framework app |
| `psr4_library` | `brick/math` @ pinned SHA | small PSR-4 library |

Pins live **outside** `adapters/` so R2.2 never sees framework/repo names in adapter source.

## Run locally

```bash
# optional cache / report paths (defaults under artifacts/, gitignored)
# export CODE_ATLAS_CROSS_REPO_CACHE=artifacts/cross-repo-cache
# export CODE_ATLAS_CROSS_REPO_REPORT=artifacts/cross-repo-report.json
# Prefer an absolute adapter path (sample builds use the sample as cwd).
export CA_PHP_CMD="php $(pwd)/adapters/php/index.php --server"

python3 scripts/cross_repo_validate.py
# GHA-equivalent (skip private scale fold-in):
python3 scripts/cross_repo_validate.py --public-only
```

The harness also rewrites a repo-relative `adapters/php/…` in `CA_PHP_CMD` to an absolute
path under the code-atlas checkout, so a relative env value still works when you launch from
this repo.

### Pass bar (ASSUMED A2 / A5)

- Build **completes without crash** for each public sample.
- `files > 0`, `nodes > 0`, `edges >= 0`.
- Parse failures (if any) are **per-file** — they must not abort the build. Third-party samples are
  **not** required to contain syntax errors; isolation is proven in per-PR fixtures and the
  harness unit test mini-repo.

## Large / private monorepo (optional)

Same operator path as task 015 — see [`scale-sample.md`](scale-sample.md).

```bash
export CODE_ATLAS_SCALE_SAMPLE=/path/to/large-php-monorepo
python3 scripts/cross_repo_validate.py   # runs public trio, then scale_full_build when env set
```

If `CODE_ATLAS_SCALE_SAMPLE` is unset, the scale step is **skipped** (not a failure) — correct for
public GHA and for laptops without the private checkout (A4).

## CI

[`.github/workflows/cross-repo.yml`](../../.github/workflows/cross-repo.yml):

- `workflow_dispatch` (manual)
- weekly `schedule` (Monday 06:00 UTC)
- public samples only (`--public-only`)

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
