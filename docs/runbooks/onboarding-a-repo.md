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

Throughput is dominated by the write path, not the parser. The same adapter parses ~490 files/s
single-threaded in isolation, while a full build with six workers sustains ~19 files/s end-to-end —
the difference is the single SQLite writer plus the `nodes_fts` trigram triggers (`store.py:75-84`).
Adding workers past a handful buys little.

## 3. Read the parse failures — they are usually not your bug

Sort the `parsed_ok = 0` list into two piles:

- **Bundled legacy libraries.** Vendored PDF/spreadsheet trees (TCPDF, dompdf, MPDF, FPDF, PHPExcel)
  account for most failures on old PHP codebases. Multi-MB generated font/CID tables can also exhaust
  the parser's memory and kill the adapter process; the indexer soft-fails that file and restarts the
  adapter (`indexer.py:565-573`), so the build survives — it just costs a restart cycle each time.
- **Genuinely invalid PHP.** Confirm with the language itself: `php -l <file>`. On the sample repo 5 of
  29 failures were files `php -l` also rejects — dead legacy fragments that cannot execute. That is a
  finding to hand back to the repo's owners, not a code-atlas defect.

A `parsed_ok` of 99.8 % on a repo this old is the expected shape. Investigate a number below ~99 %.

## 4. Tune four knobs, then rebuild once

Put them in a committed-or-not `.code-atlas.toml` at the repo root (see
[Configuration](../../README.md#configuration) for the full table).

| Knob | Why it matters at scale |
|---|---|
| `workers` | Leave CPUs for the writer. More than ~6 does not help (§2 above). |
| `adapter_timeout` | Legacy page scripts run to thousands of lines; the 30 s default is tight when workers compete. 60 s is safer. |
| `max_results` | **Also caps resolver fan-out.** See below — this is the disk knob. |
| `entry_points` | Without it `reachable_from` / `find_orphans` return `no_roots_configured` and do nothing. |

### `max_results` is doing two jobs

`full_build` passes it straight through as the resolver's candidate cap
(`indexer.py:118` → `resolve_edges(store, max_candidates=config.max_results)`). For every call the
resolver cannot pin to one target, `_queue_candidates` (`resolver.py:129`) inserts **one extra edge
per remaining candidate**. On a legacy codebase where most calls are `$obj->method()` with no type
information, that fallback (`nodes_by_names(kind="Method", limit=max_candidates)`) is where the graph
comes from.

Measured on the sample repo: **491,741 distinct heuristic call sites**, of which **33,300 saturated a
cap of 50**. Holding the file set constant, the heuristic edge count by cap:

| `max_results` | Heuristic edges | Share |
|---|---|---|
| 1 | 491,741 | 10 % |
| 5 | 1,737,848 | 36 % |
| 10 | 2,601,514 | 54 % |
| 50 | 4,764,465 | 99 % |

The rows a high cap adds are "some method with this name, somewhere" guesses. A saturated site returns
50 unrelated candidates, which is not an answer an agent can act on — and truncation is still reported
honestly through `total_count`, so the cap costs signal only where there was none. Dropping 50 → 10 on
the sample repo took the database from **2,115 MB to 1,133 MB**. (That figure also includes the
`.codeatlasignore` change from §5; the isolated fan-out effect is the −46 % in the table above.)

Budget roughly **1 GB of index per 20k legacy PHP files** at `max_results = 10`.

### If you set `entry_points`, also look at `impact_max_nodes`

`reachable_from` and `find_orphans` are bounded by `impact_max_nodes` (default 500), **not** by
`max_results`. At `detail_level = "standard"` a 500-row reachability answer is ~160 KB of JSON — tens
of thousands of tokens, which defeats the point. Use `detail_level = "minimal"`, pass a smaller
`limit`, or lower `impact_max_nodes` for interactive use.

## 5. Ignore hygiene: check for `.gitignore` negations that re-include vendor trees

code-atlas layers built-ins → `.gitignore` → `.codeatlasignore`, and **the last matching rule wins**
(`ignore.py:57-65`). That makes `.codeatlasignore` the final word, and it makes one pattern in a host
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

Only git-**tracked** files are collected (`indexer.py:264` uses `git ls-files`). Untracked work in
progress is invisible to a build; stage it first.

### Round 2: index dependencies as declarations instead of dropping them

Once the first build is clean, `stub_roots` re-adds dependency trees **declarations-only** (task 039),
so calls into them resolve without paying for their bodies. A stub root must not overlap what the
normal walk already collects — `_reject_stub_source_overlap` (`indexer.py:329`) fails loud — so each
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
  (`main.py:104`), and an MCP server inherits the client's working directory. Without the wrapper,
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

### Optional: eager freshness

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
| `get_index_status` | 321 ms | Reads `edge_health`; the one call that scans tiers |
| `search_symbol` | 36 ms | FTS trigram |
| `file_outline` / `read_symbol` | ~1 ms | Indexed by file / qname |
| `find_callers` / `find_references` / `find_implementations` | ~1 ms | |
| `include_graph` / `impact` | < 5 ms | |
| `reachable_from` / `find_orphans` | ~0.6 s | Walks from every entry-point match |
| `explain_path` | 6.6 s | Worst case; a shortest-path search over the whole graph |

Two calling conventions to get right in a smoke test, or you will report a false negative:

- **`impact`'s first positional parameter is `paths`, not `qnames`.** Passing a qname positionally
  silently seeds nothing and returns an empty success. Use keywords.
- **An empty result is not a failure.** `find_implementations` on a class with no subclasses returns
  `reason: "no_matches"`, which is the correct answer (task 033).

## 8. Read the health numbers honestly

`get_index_status` returns `edge_health.by_tier`. On the sample repo: **484,983 RESOLVED, 2,348,512
HEURISTIC, 2,933 DYNAMIC**, with 490,922 edges still unresolved.

- **RESOLVED is the graph you can trust.** A `find_callers` hit at `confidence_tier: "RESOLVED"` with
  a call-site line is as good as reading the file.
- **`authoritative: false` on reachability means what it says.** With half a million unresolved edges,
  `find_orphans` output is a candidate list to verify, never a delete list.
- **`staleness: "behind"`** right after a build usually means commits landed during it. Expected on an
  active repo; `build_or_update_index(full=false)` catches up incrementally.

`include_graph` is worth a specific check. On a Composer/PSR-4 codebase it is close to empty, because
autoloaded classes produce no `INCLUDES` edges (see the PSR-4 follow-up in
[`BACKLOG.md`](../BACKLOG.md)). A repo with a large `require`-based legacy area still gets real value —
4,640 resolved `INCLUDES` edges on the sample repo, all from the legacy side.

## Checklist

- [ ] Grammar version covers the repo's PHP target; Docker avoided if a host CLI exists
- [ ] One measured build outside the client; elapsed, `parsed_ok`, DB size recorded
- [ ] Parse failures triaged into "bundled library" vs "invalid PHP"
- [ ] `max_results` chosen deliberately, knowing it caps resolver fan-out
- [ ] `entry_points` set, or reachability tools knowingly left off
- [ ] Tracked-vs-indexed file counts diffed; `.gitignore` negations checked
- [ ] MCP server registered at local scope with a `cd` wrapper; shared `.mcp.json` untouched
- [ ] Every tool called once; latencies and empty-result reasons understood
