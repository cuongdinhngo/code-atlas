# Design — building, freshness, search order and reachability

> Part of code-atlas's **design record**. The [README](../../README.md) states what the product does and
> how to install it; this file carries *why an answer is shaped the way it is*, one section per
> field incident that changed it. It is **not** a rule book (→ [`ENGINEERING_RULES.md`](../ENGINEERING_RULES.md)), not
> task status (→ [`BACKLOG.md`](../BACKLOG.md)), and never the authority for a benchmark number
> (→ [`runbooks/`](../runbooks/)).

When the index is built, whether it is current, what order results come back in, and when a walk
refuses to answer. Every section is a field incident that moved one of those.

### Build from a shell — `code-atlas-build` (task 176)

A CI job cannot call an MCP tool, and `code-atlas-refresh` is deliberately incremental-only and
never builds without an index (053). `code-atlas-build` is the shell route to a **first** build and
a **full** rebuild — it calls `build_or_update_index` itself, so the write lock (R4.3), the
schema-mismatch answer and the report shape are the MCP route's:

```bash
code-atlas-build          # incremental; falls back to full when there is no index or no git diff
code-atlas-build --full   # always a full rebuild — after wiring an adapter or changing config
```

One line on stderr per run, and four exit codes a CI job can branch on:

| Exit | Meaning |
|---|---|
| `0` | built — the run wrote files |
| `3` | nothing to do — the build ran and wrote nothing |
| `4` | another build is running (the shared `write.lock`) — a clean skip, not a failure |
| `1` | failed — no usable adapter, a refused schema, or a broken config |

### Is it building, or is it wedged? — `code-atlas-build --status` (task 177)

A full build of a large repo can run for many minutes, and until it returns the tool says nothing —
a valid long build looked exactly like a hang. A running build now publishes one line into the
`write.lock` it already holds, and any reader can ask for it:

```bash
code-atlas-build --status     # → phase=parse done=4210 total=19000 pid=8123 at=1787876431
```

Exit `0` while a build is running, `3` when none is. Two properties are deliberate:

- **The phase, not just a counter.** A file counter reaches 100 % and then sits in `enrichment`
  and `resolve` — the whole-graph link phase — for an unbounded share of the wall time. A build
  stuck at `100 %` reads as a wedge one screen later; `phase=resolve done=N` advances once per
  unresolved-edge batch (no wall-time throttle when `total` is unset — 290), so a `done` that
  climbs across batches is work. A line that never gains `done` across multiple batches is the
  hang signal; a single long batch can still look quiet until it finishes (cost: never per-edge).
- **The claim cannot outlive the build.** Liveness is the live `flock`, not a written flag: the OS
  drops the lock when the process dies, so a `kill -9`'d build reports *no build running* on the
  very next call, even though its last line is still on disk. A `building: true` row in the
  database would have survived and become permanent.

### A full rebuild keeps serving the last good index (task 356)

A full build used to stamp the live index incomplete and truncate it, so for the minutes the build
ran every read answered from a partial graph — a symbol not yet re-parsed came back as a confident
not-found. It now fills `graph.db.shadow` and, once that graph is stamped complete, copies it over
the live file with the SQLite backup API in one destination transaction. A reader is a WAL
snapshot, so it sees the old graph or the new one, never a mix; the live path and inode never
change, which is why there is no rename (it fails over an open file on native Windows). A killed
or failed build leaves the live index byte-identical, and the next build drops the leftover shadow.

- **Cost:** up to about three times the index on disk while it publishes (live, shadow, WAL), and
  the publish holds the write lock for about 0.5 s per 200 MB (measured on a 211 MB index), which a
  fit-counter write or a read-through repair waits out inside `busy_timeout`.
- **Kept:** fit counters written during the build are carried into the shadow. A read-through
  repair made mid-build is not; the next read sees the file's hash drift and repairs it again.
- **Every guarded answer says so:** `build_in_progress: true` and `build_phase` while a writer holds
  the lock, omitted otherwise. The incremental path still writes in place and keeps 202's stamp.

### Two things `staleness` deliberately does not tell you (task 178)

`staleness` answers **which revision** this index describes, and nothing else — 072's busy refusal
and 077 both read it that way. So `standard` status carries two further axes, each omitted when
there is nothing to say:

| Field | When it appears | What it means |
|---|---|---|
| `build_in_progress: true` | a writer holds `write.lock` right now | someone is building; an incremental's numbers are moving, a full rebuild's are the last good index's (356) |
| `index_complete: false` | the last build never finished linking | the graph holds parsed rows whose edges were never linked |

`build_in_progress` is the same live-`flock` probe `--status` uses, so it cannot outlive the
process that set it. `index_complete` is the opposite kind of claim and is safe to persist: a build
writes `0` before it touches the graph and `1` only after the link phase returns, so a build that
dies mid-link leaves `0` — a surviving *negative* claim is honest.

The build stamp moved with it. `built_at` and `last_commit` used to be written when **parsing**
ended, with the whole link phase still to run, so a build killed during linking left
`staleness: "current"` on an under-linked graph permanently. They are now written after the late
writes, so nothing claims a graph is built until it is.

### Wiring a new adapter escalates the next build (task 172)

An incremental build plans from the git delta plus the files that depend on it. A file that entered
scope because an **adapter** was added is neither, so the build used to report a clean no-op —
`wrote.files: 0` beside a collection census that counted the new files, and a graph that never grew.

The announced suffix set is now compared against the one the index was built with, in
`indexer.incremental_update` itself — so the MCP tool and `code-atlas-refresh` both inherit it. When
it has moved, the build escalates to a full one and **names why**:

```json
"mode": "full",
"scope_change": {"added": [".ts", ".tsx"], "removed": [], "escalated_to": "full"}
```

This is the same escalation `incremental_update` makes on a `contract_version` change (over MCP that
one is refused first and routed to a full rebuild — 201/347). A build whose scope did not change is byte-identical, and pays one meta read it already made.

### Exact matches band ahead of near-misses (task 180)

`search_symbol("showAttachment")` returned 46 hits whose first page held two substring near-misses
and six same-named definitions from a legacy tree, and **not one row** from the directory the caller
wanted — at `reason: "ok"`, which was *correct*, because exact matches were present further down.
The label was right and the order was wrong, which is worse than a wrong label: nothing in the
payload told the caller to page. Exactness now bands the result set, with BM25 as the tie-break
**inside** each band, over the whole set rather than the page. `reason: "substring_match"` keeps its
meaning — no direct match on page 1 — and can no longer stay silent while exact matches sit at
rank 40.

### A container outranks its CONTAINS members (tasks 292, 297)

An exact-name search for a Table or Procedure put the real definitions on the page and then
filled the rest with Columns whose qnames merely *prefixed* the same string — forty
`Table::col_*` rows, same exactness band, ranked on BM25 alone. The graph already stored
`CONTAINS`; the order ignored it. Within the exactness band, **any** hit that is the target of a
`CONTAINS` edge from a parent that itself direct-matches the query **and is also a hit under the
same filters** now ranks after every non-member hit. 292 keyed that rule to `Column` and a class
therefore still buried itself under its own methods; 297 dropped the kind, so the key is
`CONTAINS` alone (R1.1) and every language gets the same order. A hit set with no such pair stays
byte-identical (061). Mirror prefer (277) still runs after this key.

### `find_orphans` refuses rather than dumping what it has flagged (tasks 182, 279)

A field round returned **215,177 orphans of 216,664 nodes — 99.31 %** — with `walk_truncated: true`
and `authoritative: false` beside them. The tool flagged its own answer unreliable and handed over
the rows anyway. The cause was the roots, not the walk: the repo dispatches after a `chdir()` the
graph cannot see, so almost nothing is reachable from `CA_ENTRY_POINTS` and the complement is
essentially the whole codebase.

Two refusals now return **no rows at all** — `status: "roots_matched_nothing"` and
`status: "walk_budget_exhausted"` — each carrying `roots_reached` and `nodes_total`, the two numbers
that separate *this code is dead* from *these roots are wrong*. A caller's own `depth=` is
deliberately not one of them: *"what is unreachable within two hops?"* is a real question and still
answers. `status: "ok"` with zero rows still means nothing is orphaned, which is an answer, not a
refusal. The roots stay **configured** rather than derived — a `chdir()` is not a fact the graph
holds — so `entry_points_unmatched` is named even on a complete answer.

A third refusal, `status: "resolution_unmodelled"`, answers the same way for a resolution strategy
the graph does not model. Each adapter stamps `File.extra.unmodelled_resolution` where the language
loads code by a name the file does not spell — PHP autoload (279), a non-literal `import()` /
`require()` in TypeScript (294), `importlib` / `__import__` in Python (295), T-SQL dynamic `EXEC` /
`sp_executesql` (296) — and the build unions those into
`meta.unmodelled_resolution_by_language`. The adapter never invents the edge it cannot name; the
stamp is what lets the tool say *unmeasured* instead of *dead*.
