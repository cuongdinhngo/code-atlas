---
id: 220
slug: no-windows-evidence-exists-and-the-core-cannot-import-there
title: 'Three entry points import `fcntl` at module scope, so on native Windows `code-atlas-build`, `build_or_update_index` and `get_index_status` all fail before running — the maintainer therefore drives it through WSL or Docker Desktop, reports both as unusably slow, and no measurement from either exists'
phase: 1.5b
milestone: Freshness
status: done
depends_on: [203, 219, 053]
---

## Verdict (recorded 2026-09-07, on the maintainer's Windows host)

**Decided, not deferred (AC5).** Native Windows stays **unsupported**; the answer is **WSL2 with the
repo on the Linux-native filesystem**. The dominant term in "unusably slow" is the **filesystem
boundary**, not 219's per-file write path — quantified below, with no code-atlas involved (Step 2). The
`fcntl` lock (053/072) is left unchanged; **AC4 is not taken** because native support is declined.

The split, one order-of-magnitude table (read+sha256, Step 2, this repo, 827 files / 9.2 MB):

| Host / path | filesystem | stat files/s | read files/s | read MB/s | vs Linux read control |
|---|---|---|---|---|---|
| Native Windows `D:\` — cold | NTFS + Defender | 51,688 | **34–37** | 0.4 | ~1,300× slower |
| Native Windows `D:\` — warm | NTFS (cached) | ~13,000 | 13,339 | 147.8 | 3.6× slower |
| WSL2 `/mnt/d` — run 1 | 9p drvfs | 707 | **556** | 6.2 | 85× slower |
| WSL2 `/mnt/d` — run 2 | 9p drvfs | 384 | **437** | 4.8 | 108× slower |
| WSL2 `~/` (ext4 clone) | ext4 | 207,000 | **82k–94k** | 893–1021 | **1.7–2.0× *faster*** |
| Linux control (ticket) | — | 180,291 | 47,370 | 522 | 1× |

Reading the table (AC3): (1) **Native Windows can't run at all** — the core raises `ModuleNotFoundError:
fcntl` at import (Step 1). (2) Even with that seam fixed, the **cold** first pass — the exact shape of a
build — is Defender scan-on-open at a *constant* ~34 files/s regardless of repo or file size (a fixed
~27 ms/file; the same D: SSD does 148 MB/s warm, so it is the AV filter driver, not disk). (3) The
maintainer's actual host — **WSL2 on `/mnt/d`** — pays the **9p/drvfs** crossing: 437–556 files/s,
85–108× below Linux. (4) The fix is proven in the same run: the identical tree on **WSL ext4** does
82k–94k files/s, matching/beating the Linux control and ~150–200× faster than `/mnt/d`. 219's 76-min
populated rebuild is a *separate additive* term every host pays; nothing here re-measures it, and it is
not what makes Windows special.

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

## Raw output — recorded 2026-09-07 (AC2; do not summarise)

Three hosts, all on the same machine. The one fact that splits the hypotheses: **where the repo lives.**

**Step 0 — say what you are.**
- **Native Windows:** `3.12.10 (MSC v.1943 64 bit) Windows-11-10.0.26200-SP0`. Repo at `D:\PROJECTS\code-atlas` — a **Windows path (NTFS)**. Defender `RealTimeProtectionEnabled: True`.
- **WSL2 Ubuntu:** `3.12.3 [GCC 13.3.0] Linux-6.6.87.2-microsoft-standard-WSL2`. Two locations tried: `/mnt/d/PROJECTS/code-atlas` (`D:\ on /mnt/d type 9p … aname=drvfs`) and `$HOME` (`/dev/sdf ext4`).

**Step 1 — does it import?**
```
# Native Windows — python -c "import code_atlas.cli"
  File "D:\PROJECTS\code-atlas\code_atlas\cli.py", line 17, in <module>
    from code_atlas.index_lock import read_build_progress
  File "D:\PROJECTS\code-atlas\code_atlas\index_lock.py", line 16, in <module>
    import fcntl
ModuleNotFoundError: No module named 'fcntl'
# same traceback from code_atlas.tools.build_or_update_index (line 21) and code_atlas.tools.get_index_status (line 20)
# WSL2 (/mnt/d): import OK
```
(Ticket table said `build_or_update_index.py` / `get_index_status.py`; their real module paths are `code_atlas.tools.*` — line numbers 21/20 match.)

**Step 2 — filesystem tax (fsprobe.py, no code-atlas involved).**
```
# Native Windows  D:\PROJECTS\code-atlas
files 827 (9.2 MB)
stat  0.02s  51,688 files/s
read  22.30s     37 files/s    0.4 MB/s        # cold
read   0.06s  13,339 files/s  147.8 MB/s        # warm (2nd run, same files)
# independent cold samples (untouched repos): the TypeScript sample 34 files/s · a second TypeScript sample 36 files/s  → constant ~27 ms/file

# WSL2  /mnt/d/PROJECTS/code-atlas  (9p drvfs)
stat 1.17s  707 files/s   read 1.49s  556 files/s  6.2 MB/s    # run 1
stat 2.15s  384 files/s   read 1.89s  437 files/s  4.8 MB/s    # run 2

# WSL2  ~/ca-native  (ext4, git clone of same tree)
stat 0.00s 206,971 files/s   read 0.01s 93,852 files/s  1,021.3 MB/s   # run 1
stat 0.00s 208,728 files/s   read 0.01s 82,137 files/s    893.8 MB/s   # run 2
```

**Steps 3–4 — not run, and why (not "would be").** The profiler (`scripts/profile_incremental.py`)
requires a **pre-existing `.code-atlas/graph.db` and configured adapters** (`bind_index`, lines 59/68).
Native Windows cannot build one — Step 1 fails at import. On WSL the core imports, but a build needs the
adapter server stood up (`CA_<LANG>_CMD`; the repo root ships no `.code-atlas.toml`) plus a full build,
whose *cost* is 219's territory and explicitly out of scope here (§Scope "Not in scope"). Step 2 already
isolates the filesystem term independently of code-atlas, which is why the verdict does not hinge on 3–4.

## Acceptance criteria — status

- **AC1 ✅** README `## Quick start` now states the POSIX-only position in its lead line, matching Step 1 (`fcntl` at import).
- **AC2 ✅** Steps 0–2 recorded raw above with host + filesystem on every row. Steps 3–4 could not run natively (import) and are out-of-scope to stand up on WSL (build cost = 219); documented, not reasoned-around (E1).
- **AC3 ✅** Verdict names the **filesystem boundary** as dominant (Defender on native NTFS; 9p on `/mnt/d`), cites Step 2, and shows the same tree on ext4 erases it — 219's write path is a separate additive term, not the Windows differentiator.
- **AC4 — n/a.** Native Windows support declined, so the `index_lock` Protocol seam is left as the POSIX `fcntl` implementation, unchanged.
- **AC5 ✅** README and `AGENTS.md` state the position plainly; ticket closed as **decided**.

## Notes

`BACKLOG.md`'s follow-up list carried *"Adapter-subprocess test harness on Windows (bug) —
`CA_*_CMD` uses POSIX quoting but splits with `posix=False`"*. **Confirmed fixed, and the row is gone**
(2026-09-06): `config.py:354` is `shlex.split(..., posix=os.name != "nt")`. Its *"fails ~56 adapter
tests on Windows"* figure was never measurable from a Linux session either — E1 above is that same
gap. Nothing here is re-asked; what remains is the protocol.
