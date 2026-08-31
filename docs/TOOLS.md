# Tools — the full surface

> The agent-facing surface of code-atlas: all 24 tools, what each returns, which take a list of
> subjects and which do not, the operator prompts, and the opt-in hooks. The
> [README](../README.md) names the handful you call first; this is the reference. It is **not**
> the payload contract (→ [`CONVENTION.md`](CONVENTION.md) §6) and not design reasoning
> (→ [`design/`](design/)).

## Tools

| Tool | Returns |
|---|---|
| `get_index_status` | index stats, last indexed commit, staleness, next-step suggestions (call first). `standard` also names the running build — `server_version` and `server_build`, with `+dirty` when the checkout has uncommitted changes — so a report can say [which code and which config answered it](design/payload.md#which-code-answered-and-which-config-tasks-170-175) (125/170/175); `verbose` adds `edge_health_by_language`, so a second adapter's tier mix is recoverable from a blended graph (183) |
| `build_or_update_index` | `wrote` counts + timing; `standard` also `graph` totals; `full=false` incremental when possible, else full |
| `search_symbol` | ranked symbols (`qname`, kind, `file:line`) — exact and prefix matches band ahead of substring near-misses across the whole result set, not just the page ([180](design/indexing.md#exact-matches-band-ahead-of-near-misses-task-180)) |
| `file_outline` | symbols + line ranges, no bodies |
| `read_symbol` | source of just one class/method + docblock |
| `find_callers` / `find_references` / `find_implementations` | resolved relationships + confidence tier; `find_references` on a `Foo::class` mention is `DYNAMIC` and sets `authoritative: false` when every hit is (094); `find_callers` can also filter call sites by argument shape (`arg_position` + `arg_is`) |
| `find_view_data` | view-scope keys a handler publishes (`PROVIDES_VIEW_DATA` — needs `CA_INDIRECTION_RULES` `view_data` setters) |
| `include_graph` | `include`/`require` neighbors (`imports` / `imported_by` / `both`); a file whose language carries the relation as `IMPORTS` instead gets `relation_unmodelled_for_language` and a route, never a confident zero (186/188) |
| `impact` | bounded blast radius of a change (paths/qnames), depth-limited with decay |
| `impact_modules` | the same radius rolled up to the business modules it reaches — per-module symbol counts split by confidence tier, one exemplar `file:line` to read first, and an explicit `unassigned` bucket. `walk_truncated` marks a bounded walk, which makes every count an under-estimate (140) |
| `subtree_dependencies` | tree-to-tree crossing with duplicate-declaration attribution — attributable vs unattributable always paired; dynamic alias bridges surfaced |
| `reachable_from` | forward reachability from configured entry points |
| `find_orphans` | unreachable / zero-inbound symbols (dead-code candidates); pages with `limit`/`offset`, and its walk is bounded by its **own** `CA_ORPHANS_MAX_NODES` rather than the impact budget. `walk_truncated` marks an answer where the walk stopped early (124); roots that match nothing, and a walk that exhausts its budget, [refuse instead of returning rows](design/indexing.md#find_orphans-refuses-rather-than-dumping-what-it-has-flagged-task-182) (182) |
| `explain_path` | shortest control-flow path between two symbols |
| `architecture_overview` | this repo's layers, their degrees and the crossings between them — plus the zero-inbound split, the capability table and the mirror panel ([detail](#architecture_overview--layers-crossings-and-the-populations-behind-a-zero)) (onboarding) |
| `guided_tour` | a dependency-ordered reading list of files, cycle-safe and budget-bounded ([detail](#guided_tour--a-reading-order-that-expands)) (onboarding) |
| `generate_onboarding` | writes the committable markdown and the self-contained `index.html` **system map** under `docs/onboarding/` ([detail](#generate_onboarding--the-committable-system-map)) (onboarding) |
| `check_architecture_rules` | confirmed vs candidate violations of declarative path-set dependency rules (`CA_ARCHITECTURE_RULES`) |
| `diff_architecture` | architectural drift between two onboarding dataset / manifest snapshots |
| `class_diagram` | mermaid class diagram for one type plus its ancestry, or every type in one file — inheritance from resolved edges; associations from declared types only |
| `check_column_defaults` | which writers of a table omit a column that declares a `DEFAULT`, against the total that write it — a writer naming no columns is *unmeasured*, never an omitter (SQL tier 2) |
| `trace_capability` | the capability flows ONE subject takes part in — an entry symbol (`qname`), a file (`path`) or a business module (`module`); each result is a traced path with its hops (`qname` · `file` · `layer` · `kind` · `tier`), how it `ended` and its `sink`. Carries no layer table, matrix or hub list: for the whole picture call `architecture_overview`. A subject the index does not hold answers `no_such_symbol`; one that joins no flow answers `no_matches` (199) |

### `architecture_overview` — layers, crossings, and the populations behind a zero

- `summary.reachability` splits the zero-inbound modules into their real populations — web surface,
  vendored, tests, no-inbound-but-outbound (**not** dead code), no-edge-either-way (a list to check,
  not a conclusion) — with the raw total kept beside them.
- `summary.business_modules` is the capability table — which file to open for a named screen — with
  its own coverage beside it, the container level derived from the tree rather than named, and a
  role-organised container refused with its reason.
- `summary.mirrors` names sibling subtrees that duplicate each other's paths — discovered, not
  configured — with a counterpart lookup whose negative answer marks divergence, and the standing
  caveat that it compares paths, not bytes.
- Each bucket also reports **which signal produced it** — `signals: {declared, vocabulary,
  structure}` — and every declared glob reports what it `files_matched` beside what it
  `zero_inbound_claimed`, so a stale declaration is legible instead of invisible (119).
- Every list is capped at `CA_MAX_RESULTS`; `verbose` pages the per-module rows with `offset`.

### `guided_tour` — a reading order that expands

- Dependency-ordered list of files, cycle-safe via SCC condensation.
- Roots prefer files that lead somewhere, then reading-seed layer rank (HTTP before Config), and are
  capped at a quarter of the node budget, so the walk expands
  instead of spending the budget on isolated files.
- A component no entry point reaches is re-seeded, not dropped.
- The walk is bounded by `CA_IMPACT_MAX_NODES`; the page is capped at `CA_MAX_RESULTS` with `offset`.

### `generate_onboarding` — the committable system map

- Writes markdown (overview · tour · flows · per-module) plus `manifest.json` and a self-contained
  `index.html` under `docs/onboarding/` — offline, theme-aware, repo text escaped so a path cannot
  inject markup, with a `<noscript>` fallback. `overview.md` includes a mermaid layer flowchart
  (GitHub/VS Code render it; the HTML map stays fetch-free and does not bundle mermaid).
- The map renders the onboarding dataset **alone**: sitemap treemap with drill-down, layer table with
  its node-kind composition, the full layer×layer dependency matrix with nothing cut, hubs, the
  capability table, the zero-inbound split, the mirror panel, a search palette with counterpart
  lookup, and a provenance section naming which parts are derived.
- Every figure is interpolated, so the same dataset always renders identical bytes, and a section
  that is empty or capped says so instead of looking exhaustive.
- The search palette ranks before it truncates, keeps one row for every top-level subtree the full
  match set spans, and names those subtrees when the page is cut — the artifact-layer form of
  `result_subtrees`. Every caveat the dataset carries is asserted to be *rendered*, by a guard that
  derives the caveat set from the dataset rather than listing it.
- It removes only the pages its own last manifest recorded, and refuses a tree it did not write.
- A module with no edge either way and no summary gets **no page** (one would only repeat its path) —
  the overview counts them, the manifest names them with `page: null`, `standard` reports
  `isolated_modules`, and a page whose neighbours the budget cut is kept and says so.
- Regenerable, versioned `artifact.json` under `.code-atlas/onboarding/` (`ARTIFACT_VERSION`;
  gitignored). Tour and pages bounded by `CA_IMPACT_MAX_NODES`.

## Sweeps — `search_symbol` takes a list of subjects (task 101)

*"Are any of these ten names already taken?"* is one question. Until 101 it was **ten calls**, so a
field session framed it as a sweep and reached for `grep -rn` instead — one call for all ten, over
two directories, where the index would have searched the whole tree. The tool was known and the cost
was not the problem: **ten calls is the wrong granularity for one question.**

```jsonc
search_symbol(queries: ["getState", "setState", "flushCache", …], kind: "Function")
→ { "indexed": true, "subject_count": 10, "index_root": "…",
    "subjects": [                                  // caller's order, never merged or deduped
      {"query": "getState",  "results": [{"qname": "\\Lib\\getState", …}], "reason": "ok",         "total_count": 1, "truncated": false},
      {"query": "setState",  "results": [],                                "reason": "no_matches", "total_count": 0, "truncated": false}
    ] }
```

Answer *i* answers subject *i*, so one miss never colours the other nine, and each entry carries its
own `reason` (and its own `try_instead`, when it has one). At most `CA_MAX_SUBJECTS` (default **25**)
subjects are accepted; the rest come back named in `subjects_dropped` beside `subjects_capped_to` —
a sweep exists to be complete, so a silent truncation is worse than ten honest calls (066). Passing
`query` and `queries` together raises. A `query=`-only call is byte-identical to before.

One caveat the shape imposes: a sweep shares **one** read-through repair budget across every subject,
because scaling it per subject is the unbounded fan-out the bound exists to prevent. A subject whose
file drifted may therefore answer `index_stale` where a single call would have repaired it — the
answer says so rather than reporting a quieter `no_matches`.

#### Tools that take one subject at a time

Batching is not free: it is only right where the question is genuinely list-shaped. One batched tool
first, proven in the field, before the pattern spreads (R1.2). Each of these keeps a single subject
for a reason:

| Tool | Why one subject |
|---|---|
| `get_index_status` | there is one index; a list of subjects has no meaning for a server-state answer |
| `build_or_update_index` | a build is one write against one tree — R4.3's single writer, not a fan-out |
| `file_outline` | already plural in its answer: one path returns every symbol in it |
| `read_symbol` | a batched body read is just a file read, and bodies are the one thing this server does not return in bulk |
| `find_callers` | the answer is a bounded traversal per subject; N subjects is N traversals, and the honest form of that is N calls the caller can page independently |
| `find_references` | same traversal cost as `find_callers`, plus `ambiguous_definitions` is a per-subject warning a merged page would bury (070) |
| `find_implementations` | subtypes of a list of interfaces is a different question — a union, which is exactly the merge 070 forbids |
| `find_view_data` | its zero is usually `capability_not_configured`, an inert-tool fact about the call, not about a subject (069) |
| `include_graph` | its subject is a path and its answer is already a graph; batching graphs means merging them |
| `impact` | it already takes `paths` and `qnames` — and merges them into one radius on purpose, because a blast radius is a union by definition (see ticket 102 for the cost of that merge) |
| `impact_modules` | the same subject as `impact`, and the same reason: one radius, rolled up once |
| `subtree_dependencies` | its subject is a directory prefix — the answer is a repo-wide report, not a per-name lookup |
| `reachable_from` | its subject is the configured entry-point set, not a caller-supplied name |
| `find_orphans` | the complement of the whole graph — there is no subject to list |
| `explain_path` | its subject is already a pair; a list of pairs is a query language, which 101 deliberately is not |
| `architecture_overview` | its subject is the whole index — there is one repo to lay out, and a list of subjects has no meaning for a repo-wide shape |
| `guided_tour` | its subject is the whole index — there is one reading order, and a list of subjects has no meaning for a repo-wide walk |
| `generate_onboarding` | a write is one artifact against one tree — R4.3's single writer, not a fan-out |
| `check_architecture_rules` | its subject is the configured rule set — a list of rule ids is filtering, not a batch of independent questions |
| `diff_architecture` | its subject is already a pair of snapshots — a list of pairs is a query language, which 101 deliberately is not |
| `class_diagram` | its subject is one type (plus ancestry) or one file — a list of subjects is N diagrams, and the honest form is N calls |
| `check_column_defaults` | its subject is one table, and the answer is already a scan of every defaulted column on it — a list of tables is N independent scans with no shared arithmetic |
| `trace_capability` | its subject IS the question — *what happens when a user does X* is asked of one entry, one file or one module. A list would return N unrelated traces and reintroduce exactly the over-answering 199 exists to remove (101) |

## Operator prompts (human-invoked — not part of the agent tool surface)

These MCP prompts are **operator recipes a human invokes**; an agent's client exposes only the tools
above to the model, so a model never sees a prompt (task 081). Agent routing lives in the tool
descriptions themselves (each names the question it answers — task 069), not here.
The blind recognition probe that scores whether those descriptions route — and that separates
name-only answers from description-backed ones — is
[`docs/runbooks/tool-recognition-probe.md`](runbooks/tool-recognition-probe.md) (081, 097).

| Prompt | Recipe |
|---|---|
| `explore_area` | status → search/outline → read only what's needed |
| `find_usages` | status → find_references / find_callers / find_implementations → read to confirm |
| `impact_of_change` | status → impact on the changed paths/qnames → read only the blast-radius surface |
| `which_tool` | a recognition map: which tool answers a given question, across all 24 tools |

## Hooks (opt-in)

code-atlas answers when asked. Two hooks cover the moments an agent was never going to ask — an edit
that drifts the index, and a `Read` that could have carried one line of context. Both are opt-in, and
both are offered rather than installed.

### Keep the index fresh while Claude edits (opt-in)

Task 035 already reparses drifted files at query time. For eager updates after Claude Code
`Edit`/`Write` on PHP files, install the PostToolUse hook under
[`contrib/claude-code/`](../contrib/claude-code/) (`code-atlas-poke` console script + `"async": true`);
opt-in git refresh after pull/checkout via [`contrib/git/`](../contrib/git/) (`code-atlas-refresh`,
background — never auto-installed into `.git/hooks`).
Safe no-op when `.code-atlas/graph.db` is missing; does not stall the tool round-trip.

### The read-time signal — a line that rides along with a file you are already opening (opt-in)

Field evidence (task [099](tasks/099_write-time-signal-seam.md)): the three most consequential
decisions an agent made *without* calling code-atlas all wanted **one line at the moment of a `Read`
or a `Write`** — and none of them wanted a tool call. An MCP tool answers when asked; this fires
when the agent was never going to ask, so it is a **hook**, not a tool.

`code-atlas-signal` prints at most one line (~150 tokens, hard cap) and exits 0:

- **`Read`** an indexed file with ≥ 5 symbols → `code-atlas: <path> defines N symbols — name:line, …`
- **`Write`** creating a new path under the indexed tree → `code-atlas: <path> is untracked — symbol
  queries answer `not_indexed` until it is committed and reindexed`

It never builds, never reparses and never takes the write lock; a file that has drifted since the
last index still answers, with `(index may be behind)` appended.

**Wire `Read` at `PostToolUse` and `Write` at `PreToolUse`.** The create-vs-edit test is whether the
path exists yet, so a `PostToolUse` `Write` is silent by construction — correct for an edit, useless
for a create.

**It stays silent** on any other tool (so browser-probe output and CI shell results are untouched),
on writes to files that already exist, on files below the symbol floor, and when there is no index.
That silence rule is the design, not a default: a line that fires on every read is chrome within
three invocations.

**code-atlas does not wire itself into anyone's editor.** As with the poke and refresh hooks, the
command is offered and the host decides — there is no installer and nothing is written to your
settings.

## Configuration reference

Every knob resolves **environment → project file → default**. The project file is
`.code-atlas.toml` at the repo root (optional, meant to be committed); its keys are the environment
names lower-cased without the `CA_` prefix. A malformed value or an unknown key is a loud error, never
a silent fallback.

| Environment | `.code-atlas.toml` | Default | Meaning |
|---|---|---|---|
| `CA_DB_PATH` | `db_path` | `.code-atlas/graph.db` | index location (relative to the repo root) |
| `CA_WORKERS` | `workers` | `max(1, min(cpu-2, 8))` | adapter processes during a build |
| `CA_ADAPTER_TIMEOUT` | `adapter_timeout` | `30` | seconds an adapter may stay silent before a build kills it |
| `CA_MAX_RESULTS` | `max_results` | `50` | result cap for search/nav tools — **and** the resolver's per-call-site candidate fan-out, which sets index size; a request above the cap is honoured to the cap and says so in `limit_capped_to` |
| `CA_MAX_SUBJECTS` | `max_subjects` | `25` | subjects one `search_symbol` sweep may take; a refused subject is named in `subjects_dropped`, never dropped silently |
| `CA_IMPACT_DEPTH` | `impact_depth` | `2` | hops the impact engine traverses (with default decay/floor, depths above ~8 are a no-op) |
| `CA_IMPACT_MAX_NODES` | `impact_max_nodes` | `500` | node budget for one impact query (seeds kept preferentially when over budget) |
| `CA_ORPHANS_MAX_NODES` | `orphans_max_nodes` | `500` | node budget for the reachability walk inside `find_orphans` only — deliberately **not** the impact knob, so tuning one cannot change which orphans exist |
| `CA_PATH_INDEX_MAX` | `path_index_max` | `20000` | path cap for the onboarding dataset's front-coded path index; when it trims, the dataset carries both the total and the shown count |
| `CA_ENTRY_POINTS` | `entry_points` | unset | file globs that seed reachability. **`reachable_from` and `find_orphans` need this** — unset, they report *no roots configured* rather than guessing |
| `CA_STUB_ROOTS` | `stub_roots` | unset | dependency roots (e.g. `vendor`) to index declarations-only, so third-party signatures resolve; hits carry `stub: true`. Costs one extra pass |
| `CA_INDIRECTION_RULES` | `indirection_rules` | unset | JSON rule files mapping framework indirection to edges. **`find_view_data` needs this** — without `view_data` setters it answers `capability_not_configured`, not a zero |
| `CA_ARCHITECTURE_RULES` | `architecture_rules` | unset | JSON rule files of path-set dependency constraints. **`check_architecture_rules` needs this** — unset → `capability_not_configured` |
| `CA_TOOLS` | `tools` | all tools | comma-separated tool allow-list |
| `CA_HOST_ROOT` | `host_root` | unset | absolute-path rewrite only (pair with `CA_CONTAINER_ROOT`; unused by the relative-path build) |
| `CA_CONTAINER_ROOT` | `container_root` | unset | absolute-path rewrite only (pair with `CA_HOST_ROOT`) |
| `CA_<LANG>_CMD` | `[adapter_cmd].<lang>` | — | the **complete argv** that launches one adapter in server mode |

```toml
# .code-atlas.toml
workers = 4
max_results = 50
tools = ["get_index_status", "build_or_update_index"]   # only names the server serves; a typo is a loud error
# Optional: only needed if something passes absolute host paths to the adapter.
# host_root = "/home/you/project"
# container_root = "/app"

[adapter_cmd]
php = "docker compose exec -T php php /app/adapters/php/index.php --server"
typescript = "node /abs/path/to/code-atlas/adapters/typescript/index.js --server"
# or, where quoting bites (Windows paths), one word per entry:
# php = ["C:\\php\\php.exe", "adapters/php/index.php", "--server"]
```

The adapter command is the **whole** command: the core appends nothing to it, not even `--server`, so
it never has to know where a language's adapter lives. An adapter announces its own name, the file
suffixes it owns, and its capabilities on the first line it writes — that handshake is what routes
files to it.

Files are skipped using built-in patterns (`vendor/ var/ uploads/ log/ node_modules/ .git/
*.blade.*`), then `.gitignore`, then an optional `.codeatlasignore` — later rules win, so
`.codeatlasignore` can re-include what an earlier source excluded. A path below an excluded
*directory* stays excluded, which is what lets the walk prune a subtree.

### Optional LLM enrichment (opt-in, off by default)

The onboarding tools are fully deterministic by default — no LLM, no network. An opt-in package,
[`onboarding_llm/`](../onboarding_llm/README.md), plugs into three seams: it can replace the one-line
module summary (085), rename weak architectural layers — the generic `source`/`sink`/`mixed` bands
084 falls back to on flat namespaces (091) — and write the map's prose (117): each layer's
responsibility line, each tour step's narrative, and the wording of the headline facts.

**Structure is never the seam's to change.** Every count, ranking, grouping and the set of headline
facts is derived before a model is consulted, so enrichment rewords the map and nothing more; a
failure or a filler answer simply leaves the deterministic sentence in place, and spend is capped at
33 calls per build whatever the repo's size.

The **core never imports it**: you install the `llm` extra, set `CA_ONBOARDING_SUMMARIZER=llm`,
`CA_ONBOARDING_LAYER_REFINER=llm` and/or `CA_ONBOARDING_PROSE=llm`, and run `code-atlas-llm` instead
of `code-atlas`. All three are memoised in content-hash caches so runs replay and diffs stay stable.
These are `onboarding_llm` knobs, not core config — the full table is in that package's README.
