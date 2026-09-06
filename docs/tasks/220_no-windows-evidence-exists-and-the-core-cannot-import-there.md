---
id: 220
slug: no-windows-evidence-exists-and-the-core-cannot-import-there
title: 'Three entry points import `fcntl` at module scope, so on native Windows `code-atlas-build`, `build_or_update_index` and `get_index_status` all fail before running — the maintainer therefore drives it through WSL or Docker Desktop, reports both as unusably slow, and no measurement from either exists'
phase: 1.5b
milestone: Freshness
status: todo
depends_on: [203, 219, 053]
---

## Why this exists

The maintainer runs code-atlas on Windows. **It cannot run there natively**, and nothing in the repo
says so. `code_atlas/index_lock.py:16` is a bare top-level `import fcntl` with no fallback, and three
entry points import that module:

| Entry point | Imports | On native Windows |
|---|---|---|
| `code-atlas-build` | `cli.py:17` → `read_build_progress` | **ModuleNotFoundError at startup** |
| `build_or_update_index` | `build_or_update_index.py:21` → `try_index_write_lock` | **ModuleNotFoundError** |
| `get_index_status` | `get_index_status.py:20` → `build_in_progress` | **ModuleNotFoundError** |

Verified by blocking `import fcntl` and importing each module: all three raise. The lock is
deliberate — 053 and 072 chose `flock` precisely because *"`flock` is released by the OS on process
death, so a reader that finds the lock free reports no build however recently the line was written"*,
where a DB flag would survive `kill -9` and become a permanent lie. **That reasoning is sound and is
not what this ticket disputes.** What it disputes is that the platform consequence is undocumented
and unmeasured.

The maintainer therefore drives it through **WSL and Docker Desktop, and reports both as unusably
slow**. Neither has ever produced a number in this repo. Every figure code-atlas publishes —
including 203's rebuild pair and the ~65× tokens-to-answer ratio — was measured on Linux.

**The likely split, and why it must be measured rather than argued.** 219 shows a populated full
rebuild costs 76 min *on Linux*, so a slow Windows rebuild is partly the tax every host pays. On top
of that, a repo living on `/mnt/c` (WSL) or a Docker Desktop bind mount crosses a 9P/virtiofs
boundary on every file read, which is the workload shape the indexer has. **Both explanations predict
"slow" and they need different fixes**, so a verdict without the split is not actionable.

## Scope

1. **State the platform support position in `README.md`** — one line. Whatever the answer (native
   unsupported · WSL recommended · Docker), a user on Windows must learn it before installing, not
   from an `ImportError`.
2. **Run the measurement protocol below on the maintainer's Windows host** and record the rows.
3. **Decide native Windows support on that evidence.** The Protocol seam is `index_lock`; a Windows
   implementation is `msvcrt.locking` or a `CreateFile` share-mode lock, both of which the OS also
   releases on process death, so 072's property is preservable — but this ticket does not presume
   the outcome. Recording *"native stays unsupported, WSL on a native path is the answer"* is a
   legitimate close if the numbers say so.

**Not in scope:** the rebuild cost itself (219 owns it); changing the lock's semantics on POSIX.

## The protocol — for the agent running on Windows

Run each step and paste the raw output. Do **not** summarise; the numbers are the artifact.

**Step 0 — say what you are.** `python -c "import sys,platform;print(sys.version,platform.platform())"`,
whether this is native Windows / WSL / Docker Desktop, and **where the repo lives** — a Windows path
(`C:\...`, `/mnt/c/...`) or a Linux-native one (`~/...` inside the WSL filesystem). This one fact
splits the two hypotheses.

**Step 1 — does it even import?** `python -c "import code_atlas.cli"`. On native Windows this is
expected to raise `ModuleNotFoundError: No module named 'fcntl'`. Record the traceback verbatim.

**Step 2 — the filesystem tax, with no code-atlas involved.** Save as `fsprobe.py` and run it once
per location you have tried:

```python
import hashlib, subprocess, sys, time
from pathlib import Path
root = Path(sys.argv[1]).resolve()
files = subprocess.run(["git", "-C", str(root), "ls-files"],
                       capture_output=True, text=True, check=True).stdout.split()
paths = [root / f for f in files]
t0 = time.monotonic(); sum(1 for p in paths if p.exists()); t_stat = time.monotonic() - t0
t0 = time.monotonic(); n = 0
for p in paths:
    try: b = p.read_bytes()
    except OSError: continue
    n += len(b); hashlib.sha256(b).hexdigest()
t = time.monotonic() - t0
print(f"{root}\nfiles {len(files)} ({n/1e6:.1f} MB)")
print(f"stat  {t_stat:.2f}s  {len(paths)/max(t_stat,1e-9):,.0f} files/s")
print(f"read  {t:.2f}s  {len(files)/max(t,1e-9):,.0f} files/s  {n/1e6/max(t,1e-9):,.1f} MB/s")
```

**Linux control, measured 2026-09-06 on this repo:** stat **180,291 files/s**, read+sha256 **47,370
files/s / 522 MB/s**. A Windows or mounted result within one order of magnitude means the filesystem
is **not** the story and 219 is the whole answer; a result 10–50× below it means the mount is a
second, independent term.

**Step 3 — where the build's time actually goes.** `python scripts/profile_incremental.py --root
<abs path>` prints per-phase wall seconds for noop / one_edit / pull_shaped across the eight
`INCREMENTAL_PHASES`. Report the table. The discriminator: **`tree_walk` + `hashing` dominating**
points at the filesystem; **`parse` dominating** points at the adapter pipe or the write path.

**Step 4 — a full build pair, if the host can afford it.** 219's shape: the same tree built once into
an empty DB and once over a populated one, wall and files/s for each.

## Acceptance criteria

- **AC1** README states the Windows position in one line, and it matches what step 1 observed.
- **AC2** Steps 0–3 are recorded with raw output, including which of the three hosts and which
  filesystem each row came from. A row without its host and path is not a measurement.
- **AC3** The verdict names which term dominates — per-file write (219) or filesystem boundary — and
  cites the step that shows it. *"Both"* is allowed only with the split quantified.
- **AC4** If native Windows support is taken, `index_lock` keeps the property 053/072 bought: a lock
  the OS releases on process death, so a stale `building: true` cannot outlive its process. Pinned by
  a test, and the POSIX path unchanged.
- **AC5** If it is declined, README and `AGENTS.md` say so plainly and this ticket closes as
  *decided*, not deferred.

## Exclusions

- **E1** Nobody can run step 2–4 from this repo's CI or from a Linux session; they need the
  maintainer's host. An agent that cannot reach Windows must stop at scope 1 and say so rather than
  reasoning about what the numbers would be.

## Notes

`BACKLOG.md`'s follow-up list carries *"Adapter-subprocess test harness on Windows (bug) — `CA_*_CMD`
uses POSIX quoting but splits with `posix=False`"*. That reads **already fixed**: `config.py:354` is
`shlex.split(..., posix=os.name != "nt")`. Confirm and remove the row, or say what still bites — an
open bug that is not open costs every reader who checks it.
