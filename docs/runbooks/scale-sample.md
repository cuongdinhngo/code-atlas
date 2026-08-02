# Scale sample full-build (task 015 / Plan §6.1)

The ~112k-file PHP monorepo is a **validation sample**, not a public checkout, and must **not**
run in per-PR CI. Use this opt-in local procedure.

## Prerequisites

- Out-of-tree checkout of the sample (operator-provisioned).
- `CA_PHP_CMD` set for host PHP or Docker (task 008 / Plan §9).
- `composer install` in `adapters/php` if using the repo adapter entrypoint.

## Run

```bash
export CODE_ATLAS_SCALE_SAMPLE=/path/to/large-php-monorepo
# optional:
# export CODE_ATLAS_SCALE_TIMING_OUT=artifacts/scale-full-build.json
# export CODE_ATLAS_SCALE_DB=/path/to/large-php-monorepo/.code-atlas/graph.db
# export CA_PHP_CMD='php adapters/php/index.php --server'

python scripts/scale_full_build.py
```

## Pass bar (ASSUMED A2 / A3)

- Build **completes without OOM** on the host you document in the JSON `host` block
  (`peak_rss_self_kb` / `peak_rss_children_kb` / `total_ram_kb`).
- Timing is a **baseline capture** (`elapsed_seconds`), not an SLA this ticket must clear.
- Keep the JSON under `artifacts/` (gitignored) or attach it where your team stores perf notes.

## What this does *not* do

- No scheduled GitHub Actions workflow in this ticket (defer if you want CI-hosted timing later).
- No adapter branches for the sample’s directory names (R2 / Standard over sample).
