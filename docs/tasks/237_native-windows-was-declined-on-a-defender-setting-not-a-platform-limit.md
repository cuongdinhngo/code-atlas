---
id: 237
slug: native-windows-was-declined-on-a-defender-setting-not-a-platform-limit
title: 'The only POSIX-only import in the core has a documented Windows equivalent that keeps 072''s property, and the "unusably slow" row was measured with Defender scanning every open — so 220 declined native Windows on a configuration, not a platform limit'
phase: 1.5b
milestone: Adoption
status: todo
depends_on: [220, 072, 053, 219]
---

## Why this exists

[220](220_no-windows-evidence-exists-and-the-core-cannot-import-there.md) closed **decided**: native
Windows unsupported, WSL2-on-ext4 is the answer. Its measurements are sound and are not disputed
here. What this ticket disputes is that **two independent claims were fused into one verdict**, and
only one of them holds:

1. *"The core cannot import on Windows."* — **True, and one module wide.**
2. *"Windows is unusably slow, so native support is not worth taking."* — **Measured under
   `RealTimeProtectionEnabled: True`, and never re-measured with the exclusion that turns the
   dominant term off.**

README and `AGENTS.md` now tell a Windows user the platform cannot do this. The evidence says the
*default configuration* cannot do this. Those are different sentences, and the repo is publishing
the stronger one.

### Claim 1 — the import surface is one module, four call sites

Re-verified by blocking `import fcntl` and importing the core module by module:

```
FAIL  code_atlas.cli                          ModuleNotFoundError: fcntl
FAIL  code_atlas.tools.build_or_update_index  ModuleNotFoundError: fcntl
FAIL  code_atlas.tools.get_index_status       ModuleNotFoundError: fcntl
FAIL  code_atlas.main                         (transitively, via the two tools)
OK    code_atlas.store · indexer · adapter · config · onboarding.artifact
```

`code_atlas/index_lock.py:16` is the **only** POSIX-only import in the shipped tree
(`scripts/scale_full_build.py:17` and two tests use `resource`; nothing else). Everything downstream
of the lock already imports clean — and it does so **by design, not by luck**:

| Portability hazard | Already handled, at |
|---|---|
| Separators leaking into the graph | `indexer.py:834,999` `.as_posix()`; `PurePosixPath` across `tools/` |
| Adapters emitting `\` in a qname | `adapters/typescript/src/qname.js:9`, `adapters/python/src/parse.py:61` |
| `shlex` eating a Windows path | `config.py:357` — `posix=os.name != "nt"`, with the reason in its docstring |
| `fork`-based fan-out | Not used: `workers` is **threads driving adapter subprocesses** (`indexer.py:1088-1122`) |
| Deleting an open SQLite file | `store.py:475` closes the connection *before* raising `SchemaVersionError`, so `_unlink_index` (`tools/build_or_update_index.py:313`) runs with no handle open |
| Entry points | All six in `pyproject.toml:21-27` are console scripts; pip emits `.exe` shims |

Someone paid for Windows portability everywhere except the lock. That is the load-bearing fact.

### Claim 2 — the cell the table is missing

220's own reading of its cold row: *"a fixed ~27 ms/file; the same D: SSD does 148 MB/s warm, so **it
is the AV filter driver, not disk**."* The diagnosis is correct and stops one step short. Defender
has a first-class exclusion for exactly this workload, and Win11 ships **Dev Drive** (ReFS +
async performance mode) for it. Neither was in the run.

Two rows from 220 §Raw output, which is where they stay (R7.6):

| Native `D:\` | read | vs Linux control |
|---|---|---|
| cold, Defender **on** (measured) | 34-37 files/s | ~1,300× slower |
| warm (measured) | 13,339 files/s / 147.8 MB/s | **3.6×** slower |

The gap between those two rows is a filter driver, not a filesystem. **No row exists for native
`D:\` with an exclusion in place**, and that row is the whole decision — it either lands native
Windows within a small multiple of Linux, or it kills the idea on evidence rather than on a default.

### Three Windows footguns beyond the lock, found while auditing

- **`MAX_PATH` (260).** `stub_roots` walks `vendor/` directly, bypassing ignore
  (`indexer.py:816-840`) — precisely where Composer/npm trees exceed 260 chars. Python ≥ 3.6 opts
  into long paths by manifest, but only when the OS `LongPathsEnabled` key is set.
- **CRLF vs the stored digest.** There are two hashers: `_whitespace_fingerprint`
  (`indexer.py:700-715`) normalises line endings and is CRLF-immune, but `_digest`
  (`indexer.py:1277`) hashes **raw bytes** and is the one persisted for change detection. Consistent
  within a host, so not a correctness bug — but a `graph.db` built in Docker/WSL and then read by
  native Windows over an `autocrlf=true` checkout sees *every file changed* and reparses the world.
  `.gitattributes` pins only `*.sh` and `Dockerfile*` to LF.
- **A repo under `/mnt/*` on WSL.** Already the documented trap; nothing detects it and says so.

Each is detectable at startup. Today each surfaces as a mystery `OSError` or a silent full rebuild,
which is the failure shape R5.3 exists to forbid.

## Root cause — a mandatory-lock difference, not a missing API

`index_lock.py` needs four things (module docstring, 072): a non-blocking exclusive lock the **OS
releases on process death**; a **shared** probe that cannot starve a writer; a progress line written
by the holder on a *second* descriptor; and that line read by *another* process.

POSIX `flock` is advisory and per-open-file-description, so all four compose. Windows byte-range
locks are **mandatory and per-handle**, so a naive whole-file lock breaks the last two — the holder's
own second handle and every outside reader hit `ERROR_LOCK_VIOLATION`. That, not the absence of a
locking call, is why this looked harder than it is. It is fixed by locking a byte **disjoint from the
data**:

```
bytes [0, 200)   the progress line — never locked, so publish/read still work
byte  1 << 20    the lock itself — locking past EOF is legal on Windows, so nothing pads the file
```

`LOCKFILE_EXCLUSIVE_LOCK` ↔ `LOCK_EX`; no flag ↔ `LOCK_SH`; `LOCKFILE_FAIL_IMMEDIATELY` ↔ `LOCK_NB`;
`UnlockFileEx` ↔ `LOCK_UN`. Windows releases every byte-range lock when the handle closes and the
kernel closes all handles on process death, `TerminateProcess` included — so **072's property is
preserved, not traded away**.

**Why not `msvcrt.locking`**, which 220 §Scope named first: it has no shared mode, so
`build_in_progress` would have to take an *exclusive* lock and could deny the lock to a build that
was just starting — a false `busy` and a lost write window. `LockFileEx` through `ctypes` keeps the
shared probe and needs no `pywin32`.

## Scope

1. **`code_atlas/index_lock.py`** — two private implementations behind the existing five-function
   API, selected once at import by `sys.platform`. The POSIX path is unchanged. No new abstraction:
   R1.2 (`one seam, YAGNI`) stays intact, and a *platform* switch is not a *language* branch (R1.1).
2. **The AC4 test 220 declined** — kill the lock holder and assert `build_in_progress()` reads
   `False`. This is the deliverable that proves the property, on both platforms.
3. **A startup preflight** naming the three footguns above when it can detect them — loud and
   specific (R5.3), never a silent slow path.
4. **Re-measure native `D:\` with a Defender exclusion** (and on a Dev Drive if one exists), using
   220's own `fsprobe.py` so the row is comparable. Record it in 220's table shape.
5. **Restate the position** in `README.md:71-75` and `AGENTS.md` — from a prohibition to a tier:
   *runtime supported on Windows; WSL2-on-ext4 recommended (it beat the Linux control); the
   development and test loop stays POSIX.*
6. **Supersede the 220 decision in [PLAN §19](../PLAN.md#19-project-context--decision-log)** — 220
   closed as *decided*, so reopening it is a decision-log entry, not a quiet diff.

### Explicitly not in scope

- **Native-Windows parity for the dev loop.** `scripts/gate.sh` is bash, `scripts/docker-test.sh`
  needs Docker Desktop, and 7 of 202 test modules import `fcntl` / `signal` / `resource`. Declined
  deliberately, and §Scope 5 says so in the docs rather than leaving it implied.
- **The rebuild cost itself** — 219 owns it, on every host.
- **Changing the lock's semantics on POSIX** (220's exclusion, kept).
- **Normalising `_digest` over line endings.** Named as a finding and detected by the preflight;
  changing the persisted digest is a rebuild-forcing change that wants its own ticket.

## Constraints

- **C1** 072's property is not weakened on either platform: no carrier of a `building: true` claim
  may outlive the process that made it.
- **C2** The POSIX path stays byte-identical in behaviour — the 3,245-test green does not move
  because of this ticket.
- **C3** No third-party dependency for the lock (`ctypes` + `msvcrt`, both stdlib).
- **C4** No `if language ==` in the core (R1.1); no new seam (R1.2).
- **C5** Determinism (R4.2) is judged per host. Cross-host byte-identity was never promised and is
  not claimed here.

## Acceptance criteria

- **AC1** With `fcntl` unavailable, `code_atlas.cli`, `code_atlas.main`,
  `code_atlas.tools.build_or_update_index` and `code_atlas.tools.get_index_status` all import. Proven
  by the import probe above, run as a test.
- **AC2** On Windows, two concurrent writers serialise: the second gets `False` from
  `try_index_write_lock`, exactly as `flock` gives today.
- **AC3** On Windows, `publish_build_progress` writes and `read_build_progress` reads the line
  **while the exclusive lock is held** — the mandatory-lock trap, pinned by a test that fails if the
  lock ever covers byte 0.
- **AC4** (220's AC4, now taken) The holder is killed without cleanup and `build_in_progress()` reads
  `False`. Pinned on both platforms.
- **AC5** The preflight reports `LongPathsEnabled` off, `core.autocrlf=true`, and a repo under
  `/mnt/*`, each with the action to take. A clean host prints nothing.
- **AC6** README and `AGENTS.md` state the tiered position, and it matches what AC1 observed. PLAN
  §19 carries the supersession with both tickets cited.
- **AC7** The Defender-excluded `fsprobe.py` row is recorded with its host and path, or E1 below is
  invoked by name.

## Exclusions

- **E1** AC7 needs the maintainer's Windows host — no CI or Linux session can produce it, and
  **GitHub Actions on this repo are unbillable** (all four jobs on [#304](https://github.com/cuongdinhngo/code-atlas/pull/304) failed in ~3 s on billing, zero
  steps run). An agent that cannot reach Windows stops at scope 1-3 + 5-6 and says so rather than
  reasoning about what the number would be — 220's own E1, unchanged.
- **E2** AC2-AC4 on the Windows arm cannot be gated by CI for the same reason. They are written to
  run on both platforms so the POSIX arm is held by `pytest`, and the Windows arm is a recorded
  manual run naming its host. **Windows support ships verified-once, and this ticket says so** — that
  is the honest cost of taking it, and it is the argument 220 had available and did not make.

## References

- [220](220_no-windows-evidence-exists-and-the-core-cannot-import-there.md) — the decision this
  supersedes; its §Raw output holds every measurement and is not copied here (R7.6).
- [072](072_busy-build-hides-staleness.md), [053](053_refresh-on-checkout-hook.md) — why the lock is
  the carrier, and the property C1 protects.
- [219](219_a-full-rebuild-pays-the-populated-db-tax-nobody-chose.md) — the rebuild term every host
  pays; not what makes Windows special.
- `code_atlas/index_lock.py`, `code_atlas/config.py:357`, `code_atlas/indexer.py:816-840,1277`,
  `code_atlas/store.py:475`, `README.md:71-75`.
