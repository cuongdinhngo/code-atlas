#!/usr/bin/env pwsh
# Native-first verification for the Windows dev loop — run BEFORE Docker, on every iteration.
#
#   scripts/verify.ps1                       # L0 only: ruff + mypy + the pure-Python guards (~10 s)
#   scripts/verify.ps1 tests/test_store.py   # L0 + L1: also run the given tests natively
#   scripts/verify.ps1 -k truncate           # L1 target by -k (any pytest args are forwarded)
#
# WHY: ~2,150 of the ~3,000 tests import and run natively on Windows (proven: `pytest --collect-only`
# collects them; a curated run is 585 pass / ~12 s). Only the index-lock tests (fcntl) and the
# php/node adapter integration tests need a POSIX host with adapters. Running the cheap native lane
# FIRST catches lint / type / doc-size / bookkeeping / core-logic breakage in seconds, so Docker runs
# ONCE at the end instead of three times.
#
#   L0 (always, native): ruff check . · mypy (pyproject `files`) · doc-size + backlog bookkeeping.
#   L1 (optional): native pytest of the paths / args you pass — your change area.
#   L2 (NOT here): scripts/docker-test.sh ONCE before the PR — adapters + index lock + CI parity.
#
# This script is a FAST PRE-CHECK, never a green-suite claim: the POSIX-only and adapter tests do not
# run here. `scripts/gate.sh --fast` is the POSIX-host equivalent.

param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Targets)

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$failed = @()

function Step($name, [scriptblock]$cmd) {
    Write-Host "== $name ==" -ForegroundColor Cyan
    & $cmd
    if ($LASTEXITCODE -ne 0) { $script:failed += $name }
}

Step 'L0 ruff'              { python -m ruff check . }
# --platform linux: CI type-checks on Linux, where fcntl exposes flock/LOCK_*; without it mypy
# defaults to win32 and false-errors on index_lock.py. This mirrors CI's view, not this host's.
Step 'L0 mypy'              { python -m mypy --platform linux }
Step 'L0 doc + bookkeeping' { python -m pytest -q tests/test_doc_size_budget.py tests/test_backlog_bookkeeping.py }

if ($Targets) {
    Step "L1 pytest ($($Targets -join ' '))" { python -m pytest -q @Targets }
}

Write-Host ''
if ($failed.Count -gt 0) {
    Write-Host "VERIFY FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host 'VERIFY OK (native fast-lane). Before the PR run scripts/docker-test.sh once (adapters + lock + CI parity).' -ForegroundColor Green
