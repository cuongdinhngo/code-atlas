# Onboarding a real repo (install → measured build → daily use)

How to put code-atlas onto a working codebase for the first time. The [README](../../README.md) covers
the happy path in three commands; this runbook is for the case where the repo is **large, legacy, and
someone else's** — where a bad first build costs twenty minutes and a wrong knob costs a gigabyte.

Every number below is measured on one large private PHP monorepo (PSR-4 `src/`, ~18k non-namespaced
legacy files, a ZF1 area; ~28k git-tracked PHP files) on a 16-core Linux host. They are illustrative
magnitudes, not targets.

## 1. Check the runtime before anything else

```bash
php -v && composer --version && python3 -V     # need PHP ≥ 8.1, Python ≥ 3.12
php -r 'require "adapters/php/vendor/autoload.php";
        echo PhpParser\PhpVersion::getNewestSupported()->id, PHP_EOL;'
```

**The adapter's PHP runtime does not have to match the repo's PHP version.** nikic/php-parser is a
pure-PHP parser with its own grammar, so a PHP 8.3 CLI parses an 8.5 codebase fine (`Parser.php:24`
asks for `createForNewestSupportedVersion()`). Check the grammar id, not `php -v` — if it covers the
repo's target version you can skip Docker entirely, which removes the path-rebasing problem (§9) from
your setup.

Reach for the Docker adapter command only when there is **no** usable PHP CLI on the host.

## 2. Build once outside the MCP client, and measure it

Do not wire up the client first. A first build on a big repo is where you find out about invalid
files, bundled libraries, and disk cost — and inside an MCP tool call all you see is a timeout.

Drive `indexer.full_build` directly, write the DB somewhere disposable, and record: elapsed, files,
`parsed_ok`, node/edge counts, edge tiers, DB size, peak RSS.

```bash
cd /path/to/target-repo
CA_PHP_CMD="php /abs/path/to/code-atlas/adapters/php/index.php --server" \
CA_DB_PATH=/tmp/trial/graph.db CA_WORKERS=6 CA_ADAPTER_TIMEOUT=60 \
  /abs/path/to/code-atlas/.venv/bin/python your_build_script.py
```

What a healthy first run looked like: **18,867 files in 1,008 s** (6 workers), 185,821 nodes,
2,836,428 edges, **99.85 % `parsed_ok`**, peak RSS 65 MB in the core and 448 MB across all adapter
children. Memory is not the constraint; **wall-clock and disk** are.

Throughput is dominated by the write path, not the parser — the same adapter parses ~490 files/s
single-threaded in isolation. **`workers` is not a throughput knob and never was.** Two-point
measurement on the 24.6k-file anchor (task 203, both against the same populated index):

| workers | wall | files/s |
|---|---|---|
| 1 | 633 s | 38.8 |
| 6 | 592 s | 41.5 |

**1.07× for six times the processes.** The serial writer is the ceiling, so set `workers` to a
handful and spend your attention elsewhere. What *did* cost an hour was a missing index: the
per-file `DELETE FROM edges WHERE file_path = ?` scanned the whole edge table, 189 ms x 24,569
files, until `idx_edges_file` landed (`store.py`). The same rebuild went **75.8 min → 9.9 min**.

## 2b. Watch a long build — it is not a hang

The caller that started the build is blocked inside it, so progress is unreadable from there and
from every MCP tool. One shell command reads it:

```bash
code-atlas-build --status      # the live phase, or "no build is running"
```

`resolve` is the phase that outlasts `parse` on a large repo, and since 290 it **ticks per batch**
instead of publishing one line with `total=0` — a slow resolve now looks slow rather than stuck.
`total` stays `0` there on purpose: the batch count is not knowable up front, and a fabricated
denominator would be worse than none.

**The timings in §2 predate 283**, which removed one SQLite `COUNT` per bare-name `CALLS` edge from
`resolve` — on a million-edge tree that was the dominant term. Treat the numbers above as an upper
bound until you re-measure your own; the *method* is unchanged.

## 3. Read the parse failures — they are usually not your bug

After the first build, call `get_index_status(detail_level="verbose")` and read
`parse_failure_paths` (capped at 50 paths, independent of `CA_PAGE_LIMIT`; use `offset` to walk
further pages when `parse_failures_truncated` is true). The count alone (`parse_failures` on
`standard`) does not say whether the hole is vendored fixtures or controllers — listing them is how
you catch a systematic failure (one directory, one encoding, one PHP version) at onboarding rather
than two field retros later.

Sort the `parsed_ok = 0` list into two piles:

- **Bundled legacy libraries.** Vendored PDF/spreadsheet trees (TCPDF, dompdf, MPDF, FPDF, PHPExcel)
  account for most failures on old PHP codebases. Multi-MB generated font/CID tables can also exhaust
  the parser's memory and kill the adapter process; the indexer soft-fails that file and restarts the
  adapter (`indexer.py`), so the build survives — it just costs a restart cycle each time.
- **Genuinely invalid PHP.** Confirm with the language itself: `php -l <file>`. On the sample repo 5 of
  29 failures were files `php -l` also rejects — dead legacy fragments that cannot execute. That is a
  finding to hand back to the repo's owners, not a code-atlas defect.

A `parsed_ok` of 99.8 % on a repo this old is the expected shape. Investigate a number below ~99 %.

## 3b. Budget the incremental — the no-op is free, the first changed file is not

052 measured **~62 s** for `build_or_update_index(full=false)` on an ~19k-file / ~1.8M-edge index
whether **0** or **21** files changed, and called it a flat fee. **That shape no longer holds** —
096's delta-scoped resolve closed the
no-op. Measured on the 24.6k-file anchor, 2026-09-01: **0 files changed = 5.5 s**, 3 files =
**63.8 s**. So the fee is a step, not a flat rate: a no-op costs seconds and the first real change
costs about a minute. Budget for the change, not for the poll; do not put that call on a synchronous
git hook (053 is gated on the number).

Confirm where the minute goes with the local-tier profiler (reuses the on-disk index; report stays
outside this repo by default):

```bash
python scripts/profile_incremental.py --root /abs/path/to/checkout \
  --report /tmp/code-atlas-incremental-profile.json
```

It times announce · tree walk · reconcile · hashing · parse · meta · enrichment · **resolve** for
noop / one-edit / ~100-file pull-shaped scenarios. If `resolve` dominates the wall on a no-op, the
unscoped `resolve_edges` hypothesis is confirmed and a follow-up fix ticket is warranted; if the cost
is spread across walk/reconcile/resolve, treat it as the honest price of that graph and keep hooks
out of band.

## 4. Tune the knobs, then rebuild when the *build* ones move

Put them in a committed-or-not `.code-atlas.toml` at the repo root (see
[Configuration](../../README.md#configuration) for the full table).

| Knob | Rebuild? | Why it matters at scale |
|---|---|---|
| `workers` | yes | Leave CPUs for the writer. More than ~6 does not help (§2 above). |
| `adapter_timeout` | yes | Legacy page scripts run to thousands of lines; the 30 s default is tight when workers compete. 60 s is safer. |
| `max_candidates` (`CA_MAX_CANDIDATES`) | **yes** | Build-time resolver fan-out. Pre-259 name `max_results` / `CA_MAX_RESULTS` still means this (alias). |
| `page_limit` (`CA_PAGE_LIMIT`) | **no** | Query-time row ceiling for search/nav pages. Default 50. Changing it never forces a rebuild (259). |
| `entry_points` | yes | Without it `reachable_from` / `find_orphans` return `no_roots_configured` and do nothing. A **stale** root is worse than none: declare only what a request can actually reach (§9). |

**259 — two knobs, not one.** Until 259, `CA_MAX_RESULTS` capped both the page and the fan-out, so a
repo that pinned `10` for disk reasons also got ten-row pages. On upgrade: `CA_MAX_RESULTS=10` (or
`max_results = 10` in the project file) still sets **fan-out** to 10; **pages default to 50** with no
rebuild. Prefer the new names going forward. `parse_failure_paths` on `verbose` status stays its own
fixed page of 50 + `offset`.

### Fan-out history (258 ended cartesian edges; 259 split the knob)

**258 (2026-09-12):** a call the resolver cannot pin to one target stores **one** unresolved site;
`find_callers` expands candidates at query time as `reason=proximity_candidates`. Fan-out no longer
multiplies rows into the graph for bare-name `Method` calls.

**Pre-258 measurement** (why old indexes are the size they are): `full_build` passed the cap as
`resolve_edges(..., max_candidates=…)`. At every unsaturated multi-match site the resolver inserted
one edge per remaining candidate. On the sample repo (**491,741** heuristic call sites; **33,300**
saturated at 50):

| fan-out (then `max_results`) | Heuristic edges | Share |
|---|---|---|
| 1 | 491,741 | 10 % |
| 5 | 1,737,848 | 36 % |
| 10 | 2,601,514 | 54 % |
| 50 | 4,764,465 | 99 % |

Dropping 50 → 10 took the database from **2,115 MB to 1,133 MB** (also includes the `.codeatlasignore`
change from §5). Budget roughly **1 GB per 20k legacy PHP files** at fan-out 10 — a pre-258 upper
bound; 258's AC1 shipped E1 so no post-258 anchor measurement exists yet.

### If you set `entry_points`, also look at `impact_max_nodes` and `orphans_max_nodes`

`reachable_from` is bounded by `impact_max_nodes` (default 500), **not** by `page_limit`.
`find_orphans` pages orphan rows via `limit`/`offset` (same as other list tools) and uses its own
walk budget `orphans_max_nodes` (`CA_ORPHANS_MAX_NODES`, default 500) — changing `impact_max_nodes`
does not change which orphans are returned. At `detail_level = "standard"` a 500-row reachability
answer is ~160 KB of JSON — tens of thousands of tokens, which defeats the point. **That is why
`reachable_from`, `find_orphans` and `architecture_overview` default to `minimal` since 268**
(`minimal` omits the `unproven` rows and keeps `unproven_total`): ask for `standard` deliberately,
on a repo whose walk you have already bounded. At scale also pass a smaller `limit` or lower the
relevant walk budget for interactive use.

For a **blast radius** specifically, the shrink is no longer a workaround: `impact_modules` answers
the same walk rolled up to business modules, which is bounded by the module count rather than the
radius — 12 152 tokens down to 178 on `brick/math`'s busiest symbol
([benchmark](../benchmarks/140_module_rollup.md)). It states `walk_truncated` when the same bound
bites, so a shortened walk is never read as a smaller blast radius.

## 5. Ignore hygiene: check for `.gitignore` negations that re-include vendor trees

code-atlas layers built-ins → `.gitignore` → `.codeatlasignore`, and **the last matching rule wins**
(`ignore.py`). That makes `.codeatlasignore` the final word, and it makes one pattern in a host
repo's `.gitignore` a trap:

```gitignore
vendor/                 # normal
!some/lib/vendor/       # committed dependency, no composer step on deploy
```

That negation also cancels the **built-in** `vendor/` rule for the tree, so a committed dependency
lands in the index as full source. On the sample repo it pulled in 2,580 third-party files — 12 % of
the index, all of it noise. Diff what you expect against what you get:

```bash
python - <<'PY'
from pathlib import Path
from code_atlas import gitutil
from code_atlas.ignore import load_ignore
m, root = load_ignore(Path('.')), Path('.')
tracked = [p for p in gitutil.ls_files(root) if p.endswith(('.php', '.phtml'))]
kept = [p for p in tracked if not m.is_ignored(p)]
print(len(tracked), 'tracked ->', len(kept), 'indexed')
print('vendor-segment files still indexed:',
      sum(1 for p in kept if '/vendor/' in p or p.startswith('vendor/')))
PY
```

Then exclude them again in `.codeatlasignore`. Two more things worth a line in that file:

- **Nested worktree checkouts** (`.claude/worktrees/…`) when the repo's `.gitignore` does not exclude
  them — they roughly double the index.
- **Committed vendored libraries under non-`vendor/` paths** — these index by design; only you know
  they are dependencies.

Only git-**tracked** files are collected (`indexer.py` uses `git ls-files`). Untracked work in
progress is invisible to a build; stage it first.

### Round 2: index dependencies as declarations instead of dropping them

Once the first build is clean, `stub_roots` re-adds dependency trees **declarations-only** (task 039),
so calls into them resolve without paying for their bodies. A stub root must not overlap what the
normal walk already collects — `indexer._reject_stub_source_overlap` fails loud — so each
stub root has to be excluded in `.codeatlasignore` first. Expect the multi-MB generated files from §3
to cost adapter restarts here.

## 6. Register the MCP server without editing a shared `.mcp.json`

Many team repos commit `.mcp.json`. `scripts/setup.py` merges into it rather than replacing it, but it
still dirties a shared file. For a personal trial, register at local scope instead:

```bash
cd /path/to/target-repo
claude mcp add code-atlas --scope local \
  -e CA_PHP_CMD="php /abs/path/to/code-atlas/adapters/php/index.php --server" \
  -- sh -c 'cd /path/to/target-repo && exec /abs/path/to/code-atlas/.venv/bin/python -m code_atlas.main'
```

Two details that bite:

- **The `cd` wrapper is not decoration.** `main()` resolves the repo from `Path.cwd()`
  (`main.py`), and an MCP server inherits the client's working directory. Without the wrapper,
  launching the client from a subdirectory silently indexes that subdirectory. The wrapper pins the
  root wherever the client starts.
- **Use an absolute interpreter path.** In a `uv`-managed checkout the console scripts live in
  `.venv/bin` and are not on the global `PATH`.

Confirm with `claude mcp get code-atlas` — expect `Scope: Local config` and `Status: ✔ Connected`.

Keep the trial out of the host repo's history with `.git/info/exclude` (local, uncommitted):

```
.code-atlas/
.code-atlas.toml
.codeatlasignore
```

### After you upgrade code-atlas, restart the client

A running MCP server is a long-lived process holding the code it started with. Pull a `schema_version`
bump and the client keeps serving the old build, so the next call reports a mismatch — and the index
it is complaining about may be the *newer* one, freshly built by the upgraded code on the command
line. Read the direction before acting:

| What the tool reports | What it means | What to do |
|---|---|---|
| `direction: index_older_than_server` | The index predates the upgrade. | `build_or_update_index` — it deletes and rebuilds in-band. |
| `direction: index_newer_than_server` | The **server process** predates the upgrade. The index is current. | Restart the MCP client. Do not rebuild — you would spend a full build replacing a good index with an older one. |
| `direction: index_version_unrecognised` | The stamp is not a version this build can compare. | Inspect by hand; delete only if the index is disposable. |
| `rebuild required` / `contract_rebuild_required` | The index predates this server's **contract** (347). | `code-atlas-build --full`, or `build_or_update_index(allow_full_rebuild=true)` in band. |

`build_or_update_index` refuses the second and third cases and leaves the file untouched (task 050),
so following the message is safe — but a session that reads "mismatch" as "corrupt" and falls back to
`grep` pays the whole trial for a client restart.

### Optional: agent brief (266 / 270 / 300)

Offer the occasions brief into the indexed repo's `AGENTS.md` (when to ask the graph — not the
24-tool roster). 300 added a sixth occasion for request-routing questions (`trace_capability`);
without it, uncoached navigation stays on `Grep`/`Read` even when all tools are registered:

```bash
python /abs/path/to/code-atlas/scripts/setup.py /abs/path/to/target-repo --write-agent-brief
# or: python /abs/path/to/code-atlas/scripts/gen_skill.py --write-agent-brief /abs/path/to/target-repo
```

**Claude Code load:** that host's memory list is only `CLAUDE.md` / `CLAUDE.local.md`. If
`CLAUDE.md` lacks `@AGENTS.md`, the writer prints the one line to add and never writes
`CLAUDE.md`. Cursor reads `AGENTS.md` directly.

### Optional: eager freshness

Four mechanisms keep an index current — none of them alone covers a `git pull`:

| Layer | Covers | Automatic? |
|---|---|---|
| Read-through freshness (035) | **one** drifted file per tool call | yes, at query time |
| Poke hook (036) | files the agent edits via `Edit` / `Write` | yes, if installed |
| Incremental `build_or_update_index(full=false)` | everything git can name since `last_commit` | **no** — someone must call it |
| Full rebuild | contract bump, older schema, unusable git diff | no |

What each does **not** cover: read-through stops after one file and returns `index_stale`;
the poke never sees a pull/checkout/IDE edit; the MCP incremental only runs when an agent
(or operator) invokes it; a full rebuild is never a hook's job.

**Opt-in git hooks (053, 355)** close the pull, checkout, commit and rebase holes: copy
[`contrib/git/`](../../contrib/git/) into `.git/hooks/` (manual — never auto-installed). They
spawn `code-atlas-refresh` in the background so a large-index incremental cannot block `git`.

Read-through freshness (task 035) already reparses a drifted file at query time, so the poke hook is
an optimisation, not a requirement. To add it, merge
[`contrib/claude-code/settings.snippet.json`](../../contrib/claude-code/) into the client settings —
using the **absolute** path to `code-atlas-poke` for the same `PATH` reason as above. Hook blocks from
a project's settings and a user's local settings merge, so this coexists with a repo's existing
`PostToolUse` hooks.

## 7. Verify the tools, not just the build

Call every registered tool once against the real index and time it. Expected shape on the sample repo:

| Tool | Latency | Note |
|---|---|---|
| `get_index_status` | 321 ms | Reads `edge_health`; the one call that scans tiers. **`db_path` lives here** (and on build reports) — nav/search/read omit it (061). Every answer also carries **`index_root`** (071 — configured source tree). |
| `search_symbol` | 36 ms | FTS trigram; redundant File+Class pairs on the same page are suppressed (061) |
| `file_outline` / `read_symbol` | ~1 ms | Indexed by file / qname |
| `find_callers` / `find_references` / `find_implementations` | ~1 ms | `subject_refreshed_only` only when the subject's file was reparsed this call |
| `include_graph` / `impact` | < 5 ms | |
| `reachable_from` / `find_orphans` | ~0.6 s | Walks from every entry-point match |
| `explain_path` | 6.6 s | Worst case; a shortest-path search over the whole graph |

**Before you read or port a large file, call `file_outline`.** Round 5 named this the
highest-leverage uncalled tool: a 1,196-line source is 7 functions + 2 closures with line ranges
in ~1 KB. The tool description now says so. `next_tool_suggestions` cannot — the core does not
see that you are about to Read, and a suggestion on every payload would violate 061. Knowing the
name is not the same as noticing the occasion (097).

Two calling conventions to get right in a smoke test, or you will report a false negative:

- **`impact`'s first positional parameter is `paths`, not `qnames`.** Passing a qname positionally
  silently seeds nothing and returns an empty success. Use keywords.
- **An empty result is not a failure.** `find_implementations` on a class with no subclasses returns
  `reason: "no_matches"`, which is the correct answer (task 033).

## 8. Read the health numbers honestly

`get_index_status` returns `edge_health.by_tier`. On the sample repo: **484,983 RESOLVED, 2,348,512
HEURISTIC, 2,933 DYNAMIC**, with 490,922 edges `unlinked`.

- **Read `by_tier`, not `linked`.** The same payload carries `linked`/`unlinked`, which count only
  whether an edge found *a* target name — on that repo `linked` is roughly twice `by_tier.RESOLVED`,
  because a HEURISTIC edge with a matched name is still a guess. The number that says how much of the
  graph you can trust is `by_tier.RESOLVED` (048).
- **RESOLVED is the graph you can trust.** A `find_callers` hit at `confidence_tier: "RESOLVED"` with
  a call-site line is as good as reading the file.
- **`authoritative: false` on reachability means what it says.** With half a million unresolved edges,
  `find_orphans` output is a candidate list to verify, never a delete list.
- **`staleness: "behind"`** right after a build usually means commits landed during it. Expected on an
  active repo; `build_or_update_index(full=false)` catches up incrementally. Only files the index
  covers move this signal (task 047) — editing docs leaves it `current`, and `dirty_indexed_files` on
  `standard` says how many indexed files are actually dirty. An index built before 047 has no suffix
  stamp: it falls back to the whole tracked tree and reports `dirty_indexed_files: null`, so rebuild
  once to get the scoped signal. **Behind does not mean "rebuild before asking anything"** (274):
  `search_symbol` / `read_symbol` still serve (read-through repair); `find_callers` /
  `find_references` refuse unless you pass `serve_behind=true` (named on the status as
  `behind_refuses` + `serve_behind_opt_in`). Narrow a subject with the commits in
  `changed_indexed_between` (`last_commit`..`head_commit`) — `changed_indexed_files` is that set's
  size — before treating every answer as drifted.

`include_graph` is worth a specific check. On a Composer/PSR-4 codebase it is close to empty, because
autoloaded classes produce no `INCLUDES` edges (see the PSR-4 follow-up in
[`BACKLOG.md`](../BACKLOG.md)). A repo with a large `require`-based legacy area still gets real value —
4,640 resolved `INCLUDES` edges on the sample repo, all from the legacy side. When the indexer sees a
registered language-standard autoloader, a TypeScript file with a non-literal `import()` /
`require()`, a Python file that calls `importlib.import_module` / `__import__` /
`importlib.util.spec_from_file_location`, or T-SQL dynamic `EXEC` / `sp_executesql`, it stamps
`meta.unmodelled_resolution_by_language` and `find_orphans` refuses a bare orphan list
(`status=resolution_unmodelled`) rather than treating include-based silence as dead code
(279, 294, 295, 296).

## 9. Generate the onboarding map — and check what your own declarations did to it

Indexing gives an agent its tools; `generate_onboarding` gives a **human** the map. It writes
`docs/onboarding/`: `overview.md` and `manifest.json` always, plus whatever the `audience` contract
names — `tour.md`, `flows.md` and a self-contained `index.html` (offline, theme-aware). **There is
no per-module page tree**; 205 removed it, and the first regeneration after 205 deletes the pages a
pre-205 `manifest.json` recorded. Regenerating touches only what that manifest lists, so a
hand-authored file in the tree survives. Narrow the walk with `working_roots` / `CA_WORKING_ROOTS`
when the reader only works in part of the tree (206/216).

**Dated figure (2026-08, pre-205):** on the ~19k-file monorepo the run took **17 s** over the
existing index and the viewer was **950 KB**. The 500 module pages that measurement also counted no
longer exist, so treat the total as an upper bound until it is re-measured on an anchor.

Read the **Zero-inbound modules, by population** block first, and read it against your own config:

- `entry_points` is the highest-trust signal precisely because you wrote it — which means a stale glob
  quietly manufactures a whole population. On the anchor, `legacy/*/web/*.php` matched 1,087 files
  and parked **560** of them in *Web entry points*, while its nginx had rooted at `public/` only for
  two task cycles. Nothing in the output could reveal that (**119** exists to fix the disclosure), and
  the side effect is worse than a wrong label: **a declared root can never be an orphan**, so every
  unreferenced legacy page was self-justifying to `find_orphans`.
- Verify the declaration against the **deployment**, not the directory tree: the web server's document
  root and its `location` blocks decide what a request can address. Correcting that one glob moved the
  bucket **901 → 341**, with 494 files landing in *not statically reachable* and 66 in *no edge either
  way* — the second list being the only one worth reading as deletion candidates.
- Expect module summaries from the file's leading doc comment when present; otherwise an explicit
  no-docblock message — not `(none)` (118).

## Checklist

- [ ] Grammar version covers the repo's PHP target; Docker avoided if a host CLI exists
- [ ] One measured build outside the client; elapsed, `parsed_ok`, DB size recorded
- [ ] Parse failures triaged into "bundled library" vs "invalid PHP"
- [ ] `max_candidates` / `page_limit` chosen deliberately — fan-out needs a rebuild; page cap does not (259)
- [ ] `entry_points` set, or reachability tools knowingly left off
- [ ] Tracked-vs-indexed file counts diffed; `.gitignore` negations checked
- [ ] MCP server registered at local scope with a `cd` wrapper; shared `.mcp.json` untouched
- [ ] Every tool called once; latencies and empty-result reasons understood
- [ ] `generate_onboarding` run once; the map opened and read as a newcomer would
- [ ] Every `entry_points` glob checked against the deployment, not the tree

