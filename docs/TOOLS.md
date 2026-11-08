# Tools — the full surface

> The agent-facing surface of code-atlas: all 26 tools, what each returns, which take a list of
> subjects and which do not, the operator prompts, and the opt-in hooks. The
> [README](../README.md) names the handful you call first; this is the reference. It is **not**
> the payload contract (→ [`CONVENTION.md`](CONVENTION.md) §6) and not design reasoning
> (→ [`design/`](design/)).

## Tools

| Tool | Returns |
|---|---|
| `get_index_status` | index stats, last indexed commit, staleness, next-step suggestions (call first). **Leads with a one-line `summary`** at every level — staleness, counts, built-on ref and the edge-health verdict lifted into one sentence from the fields below, so a caller reads the headline without reparsing the payload (316). With `entry_points` / `stub_roots` unset it also nominates candidate globs with `files_matched` and applies none — `entry_point_candidates` / `stub_root_candidates`, on an unbuilt index at any level and otherwise at `standard`, never on the cheap `minimal` path (268). `standard` also names the running build — `server_version` and `server_build`, with `+dirty` when the checkout has uncommitted changes — so a report can say [which code and which config answered it](design/payload.md#which-code-answered-and-which-config-tasks-170-175) (125/170/175); on a multi-language index `standard` also carries `edge_health_by_language` as the per-language verdict (`unlinked` / `by_tier` only — 261) beside the bounded `cross_language` crossing census (`linked` / `unlinked` / `by_tier`, no `pairs` — 243) and `capabilities_by_language` (231/244), and `verbose` replaces it with the full census including `pairs` (183); `verbose` also carries `fit_counts` — local per-tool ask tallies (task 260; definition in [design/fit.md](design/fit.md) — read that before quoting a number); `reset_fit_counts=true` clears them. `parse_failures` (standard+) is adapter parse inability — a floor, not a fatal surface (`parse_failures_note`; 280). On a `behind` index it names the routes rather than one verdict — `behind_serves` (every read tool, 388), the `serve_behind_opt_in` that serves a changed subject (omitted while a build writes the live index in place, which serves it unasked — 365), the `changed_indexed_between` pair it drifted across and, at `standard`, `changed_indexed_files` plus `behind_because` — the first 20 changed paths, each `deleted` / `uncommitted` / `committed`, with `behind_because_truncated` past that — so "is my subject affected?" needs no second call (274/388); while a build holds the lock it names `build_progress_route`, the one live phase no MCP tool can read (177/203); a client whose first MCP root in this repo (none is the index root) is another checkout gets that worktree overlaid — `read_symbol`, `file_outline` and `search_symbol` parse the files that differ from the built commit (plus untracked ones), unstored, and answer with its spans, bodies and new symbols labelled `overlay: worktree`; `find_callers` / `find_references` add its edges onto the subject at `HEURISTIC` as `worktree_overlay`, counting calls on untyped receivers in `overlay_unlinked_same_name` and flagging a deeper walk `overlay_first_hop_only` (389; `CA_CALLER_ROOT` names the worktree when the client reports no roots, and a call's own `caller_root` argument names it ahead of both — a path outside this repository is refused, 408). Every other tool, at another commit than the built one, gets `ref_mismatch` (rows kept, the old reason in `reason_at_index`) and here a summary naming both commits and the per-worktree-index route; when the check cannot run, `ref_check` here only says why — `client_declared_no_roots` (no `roots` capability, never asked), `client_reported_no_roots`, `client_roots_timed_out` or `client_roots_failed` (the last two stop asking that session) (366); an index from an older contract carries `full_rebuild_required` at every level (both versions and the full-build route), and the `summary` leads with `rebuild required` instead of a staleness an incremental would refuse (201/347); `verbose` carries `est_tokens_vs_grep_read` (read `est_tokens_note` with it) — per tool `calls`, `cited_calls`, est. `response_tokens` (chars/4 of each answer) and est. grep+Read `baseline_tokens` (bytes/4 of the first 20 files a found answer cites, read whole — so it sums `cited_calls` only), reset with `reset_fit_counts`: an estimate, never the fixture or sample tier of the tokens-to-answer benchmark (379) |
| `build_or_update_index` | `wrote` counts + timing; `standard` also `graph` totals; `full=false` incremental when possible, else full. An index one **vocabulary era** behind cannot be extended incrementally (030 AC1), and rebuilding it can outlast the call: `full=false` answers `mode: refused` · `reason: contract_rebuild_required` with the `code-atlas-build --full` route instead of starting it, and `allow_full_rebuild=true` runs it in-band anyway — and the same refusal shape now answers an explicit `full=true` on an index that already exists, because MCP cannot outlive its client and a timed-out "failed" does not stop the server-side build (291). The escalation is reported as `contract_change`, disjoint from 172's `scope_change`, so a caller can tell which one it hit (201). A build killed mid-write leaves a graph no incremental can repair — `last_commit` still names HEAD — so `staleness` reads `incomplete`, the next build escalates and reports `incomplete_index`, and `repair_incomplete=false` refuses instead for a caller that must not start a long build of its own (202). A **fourth** escalation is about cost rather than correctness: past `CA_FULL_BUILD_CROSSOVER` files to parse, the delta would be the slower route, so the build escalates and reports `delta_too_large` with the parse count, the git-named count and the threshold beside each other. **It is off by default (`0`), because measuring this repo found no such crossover:** a delta costs ~60.8 s plus 0.135 s per parsed file up to 1,000 files, then the slope collapses to 0.0088 s/file as the resolve phase saturates — 213.6 s for 3,000 changed files against a measured 550 s full build. R2.3 forbids importing another project's constant, so the mechanism ships for a repo that measures its own. The three correctness routes outrank it, and a contract-era lag never reaches it at all (212) |
| `search_symbol` | ranked symbols (`qname`, kind, `file:line`) — exact and prefix matches band ahead of substring near-misses across the whole result set, not just the page ([180](design/indexing.md#exact-matches-band-ahead-of-near-misses-task-180)). Within a band, any hit CONTAINED by a direct-match parent ranks after the container's own definitions so members cannot truncate them off the page ([292, 297](design/indexing.md#a-container-outranks-its-contains-members-tasks-292-297)); paths outside a stamped mirror pair rank above copies, and a mirrored hit names `mirror_counterpart` only when that sibling is itself indexed — a diverged file gets no field rather than a path that does not exist (282); `search_order` states the rule when mirrors exist (277 / 115). **The stack-trace spelling is a first-class query:** `Class::method` — and the container spelling `Class.method` — bands as a *direct* match when it is a separator-boundary suffix of the qname, so you can paste what the stack trace, the code review or the ticket said without first splitting it (287/293). A member stored with its sigil (`C::$prop`) is as exact under its bare name (`prop`), short queries included (404). A miss sharing no substring with any symbol is routed through its own name tokens rather than answered as a flat zero — `reason: token_candidates` (253). A zero **at a coverage edge** — a `dynamic_sql` / unmodelled-resolution stamp, or a suffix outside what the index holds — carries a `try_instead_hint` naming the Grep fallback (no `try_instead`, since Grep is not a registered tool), so the dead end routes the reader on instead of dying silent (314). A `Table`/`Function`/`View` row names the migrations that change it — `altered_by` for a literal `ALTER`, `altered_by_dynamic` for DDL read out of an executed string — so "already migrated?" is a lookup (321); a zero-overlap miss also carries `did_you_mean` — declared names a typo away (`edit_distance` ≤ 1/2/3 by length), nearest first, never in `results`, with its own `try_instead_hint` when no token candidate exists (378) |
| `file_outline` | symbols + line ranges, no bodies |
| `read_symbol` | source of just one class/method + docblock; bodies above `BODY_LINE_THRESHOLD` (600) elide by default with `body_elided` + route (`full_body` / `line_start`–`line_end` keep the whole or a range — 288; a caller `max_lines` elides earlier and the hint names that cap — 337); at `standard` `stored_fields` lists the node and `extra` keys actually populated, so an absent field reads as absent rather than unasked (250); on a repo with stamped mirror pairs a hit names its twin — `mirror_counterpart`, or `mirror_no_counterpart: true` when the sibling is not indexed — so a perfect body for the port no request reaches cannot read as *the* code that runs (286); the same cue for an override and an alias (394): `implemented_by` lists, for an `abstract` method or one whose body reaches nothing, the overriding methods of linked subtypes (capped, `implemented_by_truncated`), `aliases` the names an `ALIASES` edge ties to the hit — `relation` `alias_of` / `aliased_as`, with file and line, `test_double: true` when a test file declares it — and a name whose one production definition has only test copies answers that one with `ambiguity: "test_copies"`, and one whose every production definition is a versioned migration (`V7__x.sql`) in one directory answers the highest version with `ambiguity: "migration_redefinitions"`, the others under `ambiguous_definitions` (403); a declared `definitions.precedence` first answers with `ambiguity: "definition_precedence"` (414), `definition_state: "live"`, and each other definition its own `definition_state` and `superseded_by` (437); with a `records` block, the subject's declared records under `records` (407) (search lists it first and marks each of its rows, not the page); while a build writes the index in place a changed subject is parsed from the file unstored — `parsed_unstored: true`, `answered_about_ref: null`; body and span current, columns and supertypes still the built graph's (365); an indexed file swapped for a link out of the repo since the build answers `path_outside_root` with no text and no graph fields (375) |
| `find_callers` / `find_references` / `find_implementations` | resolved relationships + confidence tier; `find_references` on a `Foo::class` mention is `DYNAMIC` and sets `authoritative: false` when every hit is (094); a PHP static property read or write `Foo::$x` is a `REFERENCES` onto the property (`static::` `HEURISTIC`, 336), and so is a TS static field's (`Foo.x`, `this.x` in a static member) and a Python class attribute's (`Foo.x`, `self.x`, `cls.x`) when the class is declared in the same file (369); a `find_callers` row whose caller calls the subject from several lines names them in `call_lines` — one caller still (338); on a **Table** or **Column**, `find_references` returns linked `WRITES` and `DELETES` (tiers as stored; a `DELETES` targets the Table only — 328) — a Table unions writers of the table and of its CONTAINS columns, a Column is the narrower set — with `unlinked_writes_count` when the graph still holds unlinked writers; multi-language indexes carry `writes_emitters_only` when a covered language emits no `WRITES` — a PHP, TS or Python string that begins a T-SQL write or `EXEC` is read at `HEURISTIC` (371), and so is a call a `keyed_calls` rule of kind `WRITES`/`DELETES` declares (364), SQL assembled at runtime is not (278/281/335); `kinds=["READS"]` on a Table lists its readers instead — a routine's `SELECT` source at `RESOLVED`, a host string that begins `SELECT … FROM` at `HEURISTIC`, with `reads_emitters_only` when a covered language emits none and `unlinked_reads_count` for unlinked readers (390), and on a Column the statements naming it (`alias.col`, or bare beside one source), its table's readers that named no column (`select *`) counted in `column_reads_unknown`, while a Table's row lists them in `columns` (410); `kinds_ignored` lists the asked kinds a subject other than a Table/Column ignores; `find_callers` can also filter call sites by argument shape (`arg_position` or a keyword's `arg_name`, + `arg_is`; `absent` on a keyword means not passed by that keyword — 372; a position is never `absent` at a site that passed any keyword, which may fill it by name — 398), and by tier: `confidence_tier` at depth 1 is a **store predicate**, not a post-page filter, so the one RESOLVED caller of a common name is reachable — and the default inbound page order is now tier-first (`RESOLVED` before `HEURISTIC` before `DYNAMIC`, then today's stable keys — 265), so page 1 is no longer an accident of spelling; `tier_filter` names an opt-in filter and an unfiltered mixed page carries `tier_census` (251). On a constructor its adapter flags (`extra.constructor`: PHP; TS `constructor`, Python `__init__`/`__new__` — 367; a full rebuild adds the flag to an existing index) the callers are the class's construction sites as well (a Python `Foo(…)` is a `CALLS` onto the class), `arg_is` included, and `new self`/`static`/`parent` count (`static` `HEURISTIC`) — a subclass that inherits it, a constructor declared in a trait and an anonymous class's `new` are not followed (362). Three answers are deliberately **not** `ok`: a class-level `find_references` answered from its members' callers is `via_members` (252), an empty `find_callers` on a `Method` that expands to proximity-ranked unresolved same-named call sites is `proximity_candidates` with `candidate_of` on every row (258) — a site qualifies by directory, or by sitting one include away from a file whose top level does `new` of the subject's class (362), and an empty `find_references` with unlinked inbound edges of **any** kind says so in `unlinked_edge_kinds` rather than a bare `no_matches` — the honesty predicate is no longer keyed to the two kinds a PHP class subject happens to have (255). On an index behind HEAD `find_callers` and `find_references` answer from the built graph and label it with the built revision — an unchanged subject as `index_behind`, one its built file no longer declares (a deleted method, a deleted file — or a move into a file not yet re-read) as `index_behind_subject_removed`, so "who still uses what I deleted" is answerable (388). Only a subject whose changed file cannot be re-read refuses as `index_stale`, and its `try_instead_hint` names the exact call to copy: `serve_behind=true` answers it as `index_behind_subject_changed` (267). While a build holding `write.lock` writes the live index in place (not a 356 shadow rebuild; a lone short writer is still waited out), a changed subject is labelled `index_behind_subject_changed` without the opt-in, and `read_symbol` reads it through its adapter (`parsed_unstored`, see its row), rather than waiting out the busy timeout to refuse; every answer then carries `build_in_progress` (365). An incremental writes in one transaction, so what it serves meanwhile is the previous graph, never a half-linked one (400). Both inbound tools partition the answer by role: `production_count` + `test_count`, with `test_role_source` naming how the test rows were decided (`adapter` · `path_convention` · `mixed`) — *three callers* and *three callers, all in the unit test* are different answers (262). `exclude_tests=true` filters in SQL **before** paging, so page 1 is production callers, not the production callers that survived a page of tests; at depth > 1 test-role callers are pruned from the walk so they never expand (332), and the census is omitted above depth 1 because a depth-1 partition cannot add up to a BFS total. A zero at a coverage edge here likewise carries the Grep-routing `try_instead_hint` rather than a silent `no_matches` (314). A bare name another kind's qname only shadows — a table `RefType` beside a column `dbo.X::RefType` — answers about its one Table or Function (`find_callers`: Function) with `resolved_from: "bare"`, as `impact` does (plus `resolved_qnames`, bare → qname per seed); only a Table outranks a column, so a Function beside one stays `name_not_qualified` except on `find_callers`; two tables refuse as `subject_ambiguous` with each site and its `qname`, as `check_column_defaults` does — but `find_callers` on a bare table name answers `name_not_qualified`, since a table has no callers (392). A Method's depth-1 answer counts `unresolved_receivers` — calls in its language by its bare name on a receiver no type reached, such as an untyped parameter, left unlinked (`exclude_tests` applies) — so "is the list complete?" has an answer (393). With a `records` block, `find_references` lists the subject's declared records under `records` (407) |
| `find_view_data` | view-scope keys a handler publishes (`PROVIDES_VIEW_DATA` — needs `CA_INDIRECTION_RULES` `view_data` setters) |
| `include_graph` | `include`/`require` neighbors (`imports` / `imported_by` / `both`). `__DIR__ . '/x.php'` and `dirname(__DIR__) . '/x.php'` link `RESOLVED`; `ROOT . '/src/x.php'` links `HEURISTIC` when exactly one indexed file ends with that path, else it stays in `unresolved_includes` (353); a file whose language carries the relation as `IMPORTS` instead gets `relation_unmodelled_for_language` and a route, never a confident zero (186/188); an empty `imported_by` stays `relationship_not_modelled` only while an unlinked include's path tail could be this file (listed in `unlinked_includes`) — otherwise it is an attested `no_matches` naming any included same-named file in `same_basename_included`, `authoritative: true` unless `dynamic_includes_unchecked` counts includes that name no file (363). Tail matching ignores case; known limits: a bare-literal include resolves through `include_path` at runtime, so it may reach a file other than the one linked, and `dynamic_includes_unchecked` is index-wide, not scoped to the subject |
| `impact` | bounded blast radius of a change (paths/qnames, or `routes` URLs through a declared table — 385), depth-limited with decay; each row names its test role and mirror twin, and `exclude_tests` filters inside the walk (313); with a route table, `routes` lists the declared routes into the radius; with a `records` block, `records` lists the declared records on the seeds (an ambiguous one included) and rows, each with the `via` node that carries it, its `distance` and `direct`, the subject's own first, capped at `records_limit` (at most the page; `records_total`); `records="direct"` keeps the subject's alone (407, 412) |
| `impact_modules` | the same radius rolled up to the business modules it reaches — per-module symbol counts split by confidence tier, one exemplar `file:line` to read first, and an explicit `unassigned` bucket. `walk_truncated` marks a bounded walk, which makes every count an under-estimate (140) |
| `subtree_dependencies` | tree-to-tree crossing with duplicate-declaration attribution — attributable vs unattributable always paired; dynamic alias bridges surfaced |
| `reachable_from` | forward reachability from configured entry points. Default `detail_level` is **`minimal`** (268) — ask for `standard` when you want the full walk |
| `find_orphans` | unreachable / zero-inbound symbols (dead-code candidates). Default `detail_level` is **`minimal`** (268); pages with `limit`/`offset`, and its walk is bounded by its **own** `CA_ORPHANS_MAX_NODES` rather than the impact budget. Roots that match nothing, a walk that exhausts its budget (182), and an index stamped with `unmodelled_resolution_by_language` (279, and 294-296 for the other three adapters) [refuse instead of returning rows](design/indexing.md#find-orphans-refuses-rather-than-dumping-what-it-has-flagged-tasks-182-279) |
| `compute` | exact answers over the whole graph from a named template, never caller SQL (440): no `template` lists the catalogue (id, question, params). `tier_mix` splits edges per kind across confidence tiers; `no_referrer` lists the symbols of a `kind` no edge reaches, each labelled `no_edge_no_mention` (a strong candidate) or `no_edge_but_mentioned` (unknown, never dead) — or `mention_unchecked` when a name is under three characters or the literal pass hit its deadline. Every answer carries a data-driven `caveat` and `caveat_data`, a truthful `total_count`, `truncated`, and when empty a `reason` (`no_edge_matches`, `no_symbol_of_that_kind`, `every_one_is_referenced`). A template that does not take a param refuses it. Runs in a read-only sandbox — `mode=ro`, `query_only`, an authorizer allowing SELECT/READ and a short function list, 3 s per statement, at most 200 rows; a refusal or a deadline answers no rows with `reason` `refused_by_sandbox` / `deadline_exceeded`. Overlaps `find_orphans` without entry points: that one walks reachability, this one counts edges |
| `verify_refs` | which paths and symbols named in instruction files, memory and docs still resolve (439, core in 438): by default only the actionable counts and 20 rows (443, *Behaviour by tool*); each row `ok` · `moved` · `gone` · `never_existed` · `ambiguous` · `unknown` with its reason, instruction files first; `globs`, `doc_class`, `state` narrow it and summaries count every row. A `moved` row with one successor carries `replacement` — written the way the doc wrote it, root- or doc-relative — and `patch_ready`; a split, a gone or an ambiguous row carries a `hint` instead, and archive rows are never patched. `format: patch` answers `edits` (file, line, ref, replacement) and `apply_with`, the shell command whose diff `git apply` takes; the diff itself carries doc lines, so it never rides the MCP payload |
| `compute` | exact answers over the whole graph from a named template, never caller SQL (440): no `template` lists the catalogue (id, question, params). `tier_mix` splits edges per kind and source × target language across confidence tiers; `no_referrer` lists the symbols of a `kind` no edge reaches, each labelled `no_edge_no_mention` (a strong candidate) or `no_edge_but_mentioned` (unknown, never dead) — or `mention_unchecked` when a name is under three characters or the literal pass hit its deadline. Every answer carries a data-driven `caveat` and `caveat_data`, a truthful `total_count`, `truncated`, and when empty a `reason` (`no_edge_matches`, `no_symbol_of_that_kind`, `every_one_is_referenced`). A template that does not take a param refuses it. Runs in a read-only sandbox — `mode=ro`, `query_only`, an authorizer allowing SELECT/READ and a short function list, 3 s per statement, at most 200 rows; a refusal or a deadline answers no rows with `reason` `refused_by_sandbox` / `deadline_exceeded`. Overlaps `find_orphans` without entry points: that one walks reachability, this one counts edges. 441 adds seven: `unreferenced_objects` (no_referrer's evidence split, counting only referrers in `language`; a language no file is in answers `no_file_in_that_language`), `calls_by_module` (calls into a `target` qname GLOB or a `target_kind`, per module of the one business-module table, unassigned files in `unassigned`), `untested_classes` (types no edge from a test symbol reaches — directly or through a member — with `by_module`; `no_test_symbol_indexed` when nothing is a test), `resolved_share` (RESOLVED share of CALLS per module), `includes_by_dir` (INCLUDES per top directory by tier), `multi_defined` (one object per kind and qname defined more than once — 443 — `live` from the declared `definition_order` — `live_state: unknown` with `why_unknown`, never a guess) and `variant_pairs` (same-container names sharing a stem through `left`/`right` one-`*` patterns, or the toml's `variant_pairs`, where exactly one side has an inbound edge). A per-file or per-type aggregate larger than 200,000 rows is refused (`over_internal_cap`), never cut |
| `explain_path` | shortest control-flow path between two symbols |
| `architecture_overview` | this repo's layers, their degrees and the crossings between them — default `detail_level` is **`minimal`** (268) — plus the zero-inbound split, the capability table and the mirror panel ([detail](#architecture_overview--layers-crossings-and-the-populations-behind-a-zero)) (onboarding) |
| `guided_tour` | a dependency-ordered reading list of files, cycle-safe and budget-bounded ([detail](#guided_tour--a-reading-order-that-expands)) (onboarding) |
| `generate_onboarding` | writes the committable markdown and the self-contained `index.html` **system map** under `docs/onboarding/` — four or five files depending on `audience`, no per-module page tree ([detail](#generate_onboarding--the-committable-system-map)) (onboarding) |
| `check_architecture_rules` | confirmed vs candidate violations of declarative rules (`CA_ARCHITECTURE_RULES`): a path set that must not reach another, or symbols that must reach a gate ([rule files](#architecture-rule-files)) |
| `diff_architecture` | architectural drift between two onboarding dataset / manifest snapshots; a path resolving outside the indexed tree answers `path_outside_root`, unread (342) |
| `class_diagram` | mermaid class diagram for one type plus its ancestry, or every type in one file — inheritance from resolved edges; associations from declared types only |
| `check_column_defaults` | which writers of a table omit a column that declares a `DEFAULT`, against the total that write it — a writer naming no columns is *unmeasured*, never an omitter; a bare table name resolves to its one schema-qualified table or is refused with the candidates (SQL tier 2, 320); `default_expr` replaces `table` as the subject — every column whose `DEFAULT` is that expression (case, brackets and outer parentheses ignored; whitespace outside a quoted literal removed, so `a b` matches `ab`), each row naming its `table` and measured against that table's writers (391) |
| `trace_capability` | the capability flows ONE subject takes part in — an entry symbol (`qname`), a file (`path`), a business module (`module`) or a URL through a declared route table (`route`, 385: flows start at its target, that hop `HEURISTIC` + `rule: true`; a miss names `nearest_routes`); each result is a traced path with its hops (`qname` · `file` · `layer` · `kind` · `tier`), how it `ended` and its `sink`. Carries no layer table, matrix or hub list: for the whole picture call `architecture_overview`. A subject the index does not hold answers `no_such_symbol`; one that joins no flow answers `no_matches` (199); on an index where no flow could be seeded — no declared entry point, no entry-named path — every subject answers `capability_not_configured` and routes to `get_index_status`, which nominates entry-point globs (354) |

### `architecture_overview` — layers, crossings, and the populations behind a zero

- `summary.reachability` splits the zero-inbound modules into their real populations — web surface,
  vendored, tests, no-inbound-but-outbound (**not** dead code), no-edge-either-way (a list to check,
  not a conclusion) — with the raw total kept beside them.
- `summary.business_modules` is the capability table — which file to open for a named screen — with
  its own coverage beside it, the container level derived from the tree rather than named, and a
  role-organised container refused with its reason. It is **never empty**: it fills from three
  ordered sources — a human `docs/onboarding/capabilities.toml`, then entry rows from
  `CA_ENTRY_POINTS` / HTTP entries, then structural modules — and only a genuine miss falls through,
  naming its candidate globs and `files_matched` rather than an empty table (263).
- `summary.mirrors` names sibling subtrees that duplicate each other's paths — discovered, not
  configured — with a counterpart lookup whose negative answer marks divergence, and the standing
  caveat that it compares paths, not bytes.
- Each bucket also reports **which signal produced it** — `signals: {declared, vocabulary,
  structure}` — and every declared glob reports what it `files_matched` beside what it
  `zero_inbound_claimed`, so a stale declaration is legible instead of invisible (119).
- A bucket whose own declaration was never given **and** whose count is 0 says so where the count
  is, and names the setting that would populate it (`entry_points` / `stub_roots`, env
  `CA_ENTRY_POINTS` / `CA_STUB_ROOTS`) — that 0 answers a question nobody asked, and reading it as
  *"this repo vendors nothing"* is the misreading it now prevents (208). A declaration that matches
  no indexed file still reports so beside the count, so the two disclosures compose.
- Every list is capped at `CA_MAX_RESULTS`; `verbose` pages the per-module rows with `offset`.

### `guided_tour` — a reading order that expands

- Dependency-ordered list of files, cycle-safe via SCC condensation.
- Roots prefer files that lead somewhere, then reading-seed layer rank (HTTP before Config), and are
  capped at a quarter of the node budget, so the walk expands
  instead of spending the budget on isolated files.
- A component no entry point reaches is re-seeded, not dropped.
- The walk is bounded by `CA_IMPACT_MAX_NODES`; the page is capped at `CA_MAX_RESULTS` with `offset`.

### `generate_onboarding` — the committable system map

- Writes `overview.md` and `manifest.json` always, plus whatever the `audience` contract names —
  `tour.md`, `flows.md` and a self-contained `index.html`, so `full` and `newcomer` get **five files**
  and `maintainer` **four** (no tour). Offline, theme-aware, repo text escaped so a path cannot
  inject markup, with a `<noscript>` fallback. `overview.md` includes a mermaid layer flowchart
  (GitHub/VS Code render it; the HTML map stays fetch-free and does not bundle mermaid).
  Its body is organised under **question-shaped headings** — the seven a reader actually asks (what
  is this repo, where are the landmines, where to start reading, which file for a named change, the
  spine, what changed since the last generate, what not to trust) — with the graph-noun census
  sections demoted to an appendix (269).
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
- **There is no per-module page tree.** It emitted one page per node-budget slot — 500 on every
  repo, whatever its size — and the median page carried a path already in its own filename, a role,
  a layer and a truncated neighbour list; on a 24,535-file repo 412 of the 500 rendered a Summary
  line saying there was no summary (205). The facts those pages carried are in `tour.md`,
  `overview.md` and the map.
- It refuses a tree it did not write, and removes the module pages a **pre-205** manifest recorded —
  so the first regeneration after 205 cleans the old tree and leaves a hand-authored file alone.
- Regenerable, versioned `artifact.json` under `.code-atlas/onboarding/` (`ARTIFACT_VERSION`;
  gitignored). The tour walk is bounded by `CA_IMPACT_MAX_NODES`; nothing else borrows that budget.

## Behaviour by tool

The model-facing description of each tool is short: the question, when to use it, the parameters an agent sets and the key fields. Everything it dropped is kept here, unchanged, so nothing is lost — reach for this when a `reason`, `truncated` or tier needs its exact meaning.

### `get_index_status`

The full description before the tool surface was shortened, verbatim:

```text
Is the index built, fresh, and healthy — and what should I call next? Call this first.

Reports stats, health, last commit, staleness, and next-tool suggestions. ``parse_failures``
(``standard``/``verbose``) counts files the adapter could not parse — a floor on
brokenness, not a fatal surface; see ``parse_failures_note`` (language runtime
compiler/linter). ``verbose`` adds capped ``parse_failure_paths`` plus
``parse_failures_truncated``; pass ``offset`` to page further. ``minimal`` / ``standard``
omit the list (cheap path). ``standard``/``verbose`` also carry ``page_limit``
(query-time row ceiling) and ``max_candidates`` (build-time resolver fan-out), each with
its own ``governs`` list so the two caps are not conflated (066/259). ``verbose`` also
carries ``collection`` — the
denominator to reconcile ``files`` against your own ``git ls-files``:
``collected - skipped.suffix - skipped.ignore == kept``, ``kept + stubs == files`` (082).
``skipped.untracked`` sits beside that identity: files git does not list, with an indexed
suffix, that are not ignored (092). ``verbose`` also names ``skipped.ignore_sources`` —
per-source counts that sum to ``skipped.ignore`` (095); omitted when empty or pre-095.
``standard``/``verbose`` carry ``unconfigured_adapters`` — adapters that ship in-repo but
have no launch command, each with the ``CA_<LANG>_CMD`` that enables it; omitted when all
are wired (159). On a multi-language index they also carry ``cross_language`` — the
build-stamped crossing census without ``pairs`` (243); omitted under two language buckets
and on a pre-204 stamp (R5.6 / 061). ``standard``/``verbose`` also carry
``capabilities_by_language`` — the build-stamped R1.6 flags, for the languages this
index holds files of (231/244/173); omitted when the stamp is absent or empty
(R5.6 / 061). ``standard``/``verbose`` also carry ``edge_health_by_language`` on a
multi-language index (261): ``standard`` is the verdict only (``unlinked`` /
``by_tier`` per language); ``verbose`` nests the full census including ``pairs``.
``verbose`` also carries ``fit_counts`` — local per-tool ask tallies (task 260); pass
``reset_fit_counts=true`` to clear them first — skipped while a build holds the live
index, saying ``fit_reset_skipped: true`` (400) — (documented reset; local counts are not
telemetry). See ``docs/design/fit.md`` for the fit definition before reading the numbers.
``verbose`` also carries ``est_tokens_vs_grep_read`` — read ``est_tokens_note`` first (379).
Every level carries ``refresh_refused`` when the last hook refresh did not run: its
``reason``, ``at`` (UTC) and a ``hint`` or ``route``, until a build succeeds (401).

``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
``key=value`` line stating how many files this index covers and at which revision. An
unbuilt or unreadable index carries no line — it cannot name a revision (task 100).
```

### `build_or_update_index`

The full description before the tool surface was shortened, verbatim:

```text
Build or refresh this repo's index so the other tools have current data.

Returns ``wrote`` counts (and ``graph`` on standard) plus elapsed time. An index written
under an *older* ``schema_version`` is deleted and rebuilt in-band so an MCP client can
recover without a shell; a *newer* one is refused untouched — that index is current and this
server is the stale one (050). Concurrent writers share ``write.lock`` (053); a held lock
returns ``mode: busy`` carrying the staleness of the index the loser is about to query,
read-only (072); the request is queued, and the running build serves it with one more
incremental before it exits (357), so do not retry in a loop. To *see* a busy refusal on
purpose, follow the ``code-atlas-refresh`` race recipe in
``docs/runbooks/parallel-agents.md`` (082).

An index written under an older *vocabulary* era cannot be extended
incrementally either (030 AC1). Rather than silently starting an hour-long
rebuild inside a call that cannot outlive its client, ``full=false`` returns
``mode: refused`` with ``reason: contract_rebuild_required`` and the route that
can serve it. ``allow_full_rebuild=true`` runs that rebuild in-band anyway,
accepting the wait (201). The same refusal shape answers an explicit
``full=true`` on an index that already exists — MCP cannot outlive its client,
and a timed-out "failed" does not stop the server-side build (291).
```

### `search_symbol`

The full description before the tool surface was shortened, verbatim:

```text
Find a symbol from part of its name or text — ranked, with where each one lives.

Pass ``query`` for one subject, or ``queries`` for a sweep of them — *"are any of these ten
names already taken?"* is one call, not ten (101). Never both. A sweep returns ``subjects``:
one entry per subject, **in the order you asked**, each with its own ``results``, ``reason``
and ``total_count``, so one miss never colours the rest. At most ``max_subjects`` are
accepted; the rest are named in ``subjects_dropped`` beside ``subjects_capped_to``.
A sweep shares **one** read-through repair budget across every subject, so a subject whose
file drifted may answer ``source_stale`` rows where a single call would have repaired it;
it carries ``retry_as: query``. When a sweep mixes vouched ``ok`` answers with such
subjects, the envelope names them in ``index_stale_subjects`` and states that the shared
budget decided (275) — a fully-vouched sweep stays unchanged (061).

Returns ``{qname, kind, file, line}`` rows (FTS trigram, or a name/qname prefix scan for
queries under three characters), capped by ``limit`` or ``CA_MAX_RESULTS``; ``offset`` pages
in search order (057). **Exact and prefix matches come first**, near-misses after, relevance
as the tie-break inside each band — over the whole result set, not the page (180).
At ``standard``, a ``Column`` whose schema declares a foreign key also carries its target(s)
from existing ``REFERENCES`` edges (239): resolved column targets under ``references``, and
a column-list-omitted FK — which names only its table — under ``references_unresolved``, so
the two are never signed alike (R5.6). Both are omitted when empty, and never appear on
``minimal`` or non-``Column`` rows. A ``Table`` / ``Function`` row names the files whose DDL
changes it (321): a literal ``ALTER`` under ``altered_by``, a name read out of an executed
string under ``altered_by_dynamic`` — a claim, never signed as resolved. When the first
page holds only substring/trigram near-misses — no
result exactly matches or prefixes the query — ``reason=substring_match`` marks the answer a
near-miss, not a hit, and carries the language-coverage note (167 / 160). A
``substring_match`` answer, or a page short of ``total_count``, also carries
``try_instead=file_outline`` plus the narrow-by-qname hint, so the reader has a query to
make next instead of inventing one (245 / 093). It never refuses on
staleness (388): a hit whose file drifted beyond the per-call reparse cap carries
``source_stale: true``; a zero-hit first page may repair a named subject file or the sole
dirty indexed file; a miss nothing could vouch for (an unnameable subject amid several
dirty files) answers ``reason=index_behind``, empty, with ``other_indexed_files_drifted``
— never an empty proof of absence (073/246). Stub-
indexed nodes carry ``stub: true`` (039); a ``File`` hit that only restates a ``Class``
hit's declaring file in the same page is suppressed — request File rows via ``kind`` (061).
A zero-overlap miss answers ``reason=token_candidates`` with ``candidates`` (names sharing a
word, 253) and, when a declared name is a typo away, ``did_you_mean`` — ``{qname, name,
kind, edit_distance}``, nearest first, never in ``results`` (378).
``exclude_tests`` (default off) drops test-role nodes in SQL before paging (332);
``total_count`` then counts the filtered set. Off is byte-identical (061).
A qname held by one production row and test copies lists the production row first and
marks each of its rows ``ambiguity: "test_copies"``; a type row at ``standard`` names
its ``aliases`` (394).
Asked from another worktree of this repo, rows from files it changed are swapped for that
worktree's own symbols — new files included — and ``overlay: worktree`` is set (389).
``caller_root`` names that worktree for this call alone — an absolute path inside a
checkout of this repository, ahead of the roots and ``CA_CALLER_ROOT``; any other value
is refused as an error (408).
A single ``query`` held by a declared route key (385) adds ``routes`` — ``{route, target,
file, tier, rule}`` — beside ``results``; pass one to ``trace_capability(route=…)``.
```

### `file_outline`

The full description before the tool surface was shortened, verbatim:

```text
What does this file define, and on what lines — without printing the source?

Call this before you read or port a large file — it is the symbol map, not a body.
Returns each symbol with its ``line_start``/``line_end``, never bodies. ``path`` may be
absolute (under the repo root) or ``./``-prefixed; it is normalised to the repo-relative
form stored in the index. ``found`` is false when that path is not indexed.

``limit`` defaults to ``CA_MAX_RESULTS``; ``offset`` pages in store symbol order (057).
``total_count`` is the file's full symbol count, not the page length — when the map is
capped, ``truncated`` is true and ``result_kinds`` names how many symbols of each kind
the file holds — omitted for a single-kind file, where it would restate ``total_count``
— so a one-page reader can see what the page omitted (067/123). Asked from another
worktree of this repo, a file that worktree changed or added is outlined from its bytes,
and the answer carries ``overlay: worktree`` (389). ``caller_root`` names that worktree
for this call alone — an absolute path inside a checkout of this repository, ahead of the
roots and ``CA_CALLER_ROOT``; any other value is refused as an error (408).
```

### `read_symbol`

The full description before the tool surface was shortened, verbatim:

```text
Read just one symbol's source and its doc comment, without opening the whole file.

``standard`` returns ``line_start…line_end`` for ``qname`` plus the contiguous comment
block above it; ``minimal`` returns the declaration range alone (no docblock), so ``source``
matches the returned ``line_start``/``line_end`` (163). At ``standard`` a found
**callable** hit also carries ``params`` (name + declared type, adapter spelling) when the
language's adapter stamps that capability; otherwise ``params_not_captured_by_adapter`` —
never an empty list that reads as "takes no arguments" (242 / R5.6). ``minimal``, and every
non-callable kind, omit both (061). A found **Table** at ``standard`` carries a paged
``columns`` list (name + declared type + ``DEFAULT`` when present) from ``CONTAINS``, in
DDL order — never the CREATE header as the product; a table with no indexed columns says
so rather than returning an empty list (248 / 061). A found **Class** / **Interface** at
``standard`` carries ``supertypes`` (``EXTENDS`` / ``IMPLEMENTS`` in declaration order —
resolved qname when linked, raw name + ``unresolved`` when not); an adapter that does not
stamp ``inheritance`` discloses ``supertypes_not_captured_by_adapter`` (285 / R5.6); a type
that declares none omits the field (061). ``limit`` / ``offset`` page that list
only; other kinds ignore them. ``stored_fields=True`` adds which ``NODE_FIELDS`` are
populated and which ``extra`` keys the node carries — key names only, never extra
values (250). A ``Column`` also always lists ``references`` / ``references_unresolved``
(empty = no FK). Default off: existing payloads stay byte-identical (061). On
hash drift, reparses that one file inline (035); returns ``stale: true`` and
``reason=index_stale`` when the file is missing, no adapter owns it, or repair fails.
Stub-indexed nodes carry ``stub: true`` (039). A qname with more than one definition
returns ``reason=subject_ambiguous`` plus ``ambiguous_definitions`` and **no body** —
empty ``source``, no ``file``/``line_*`` — so one region's code cannot be read while
ignoring the list (070 warn; 078 refuse) — unless one is production and every other a
test copy: that one answers, with ``ambiguity: "test_copies"`` and the copies listed (394);
or every one a versioned migration's redefinition (``V7__x.sql``): the highest version
answers, ``ambiguity: "migration_redefinitions"``, the earlier ones listed (403); or a
rules file's ``definitions.precedence`` glob names one: ``"definition_precedence"`` (414).
A found hit names where else its code lives (394): ``implemented_by`` — for an abstract
method or one whose body reaches nothing, the overriding methods of linked subtypes,
capped — and ``aliases`` — the names an ``ALIASES`` edge ties
to it, with file, ``relation`` and ``test_double`` when a test file declares the alias.
``try_instead`` points at ``read_symbol`` with
``path_prefix`` (327); ``path_prefix`` filters definition rows first (315's validator),
and one that drops every definition answers ``path_excluded`` with their files (339).
An untracked indexable file matching the subject is ``reason=not_indexed`` (092).
Asked from another worktree of this repo (MCP roots, or ``CA_CALLER_ROOT``), a subject in
a file that worktree changed is read from its bytes — span and body — and every answer
so read carries ``overlay: worktree`` and ``overlay_root`` (389). ``caller_root`` names
that worktree for this call alone — an absolute path inside a checkout of this repository,
ahead of the roots and ``CA_CALLER_ROOT``; any other value is refused as an error (408).
An indexed file that now resolves outside the repo (swapped for a symlink since the build)
answers ``reason=path_outside_root`` with ``file`` and an empty ``source`` (375).

Bodies above BODY_LINE_THRESHOLD (600 lines — one site in ``source_slice``) elide by
default: ``source`` is the signature line only, with ``body_elided: true``, ``line_count``,
and a route to ``file_outline`` or a line range — never a silent mid-body cut (288). Pass
``full_body=true`` (or a ``max_lines`` at/above the span) for the whole declaration;
``line_start``/``line_end`` return exactly that clamped range inside the symbol.
With a ``records`` rule the subject's declared records ride in ``records``, each with
its declared ``attributes``; ``records_filter`` (``{"tier": ["A"]}``) keeps those whose
attribute equals a value, and a name no block declares raises ``ValueError`` (407, 413).
```

### `find_callers`

The full description before the tool surface was shortened, verbatim:

```text
Who calls this function or method? Every call site, with confidence and optional depth.

``depth`` defaults to 1 (direct). Deeper values BFS over CALLS/NEW, but only
``RESOLVED`` edges expand the frontier — HEURISTIC/DYNAMIC hits are returned and counted
in ``frontier_skipped_non_resolved`` when a deeper hop was requested.

``total_count`` is the size of the BFS hit set within ``depth`` (exact at depth 1;
a lower bound when a deeper walk hits the count budget — and at depth > 1 that floor
is valid for the requested page only, because the budget grows with ``offset``).

``include_source`` (default off, so the common case stays token-frugal) adds each call
site's own source line as ``source``, capped in length — answering "show me" without a
second call. A site whose file drifted since indexing is never quoted: those hits carry
``source_stale`` instead. At depth 1 a caller that calls the subject from two or more
lines carries them all as ``call_lines`` (``line`` stays the first), quoted as
``call_sources`` under ``include_source``; it is still one caller in ``total_count``.

``arg_position`` (1-based) with ``arg_is`` keeps only call sites whose argument there has
that shape: a literal category (``null``, ``true``, ``false``, ``number``, ``string``,
``array``), ``absent`` (the call passes fewer arguments), or ``dynamic`` (present, but not
a literal). ``total_count`` then counts matches, and ``args_unrecorded`` says how many
call sites the filter could not judge — sites whose arguments were never recorded, which
are never counted as matches. Depth 1 only. ``arg_name`` in place of ``arg_position``
judges a keyword argument the same way (``absent``: not passed *by that keyword*, so a
positional value counts as absent) — only an adapter that
records keywords can match, Python today (372); the rest count as ``args_unrecorded``.

``confidence_tier`` (default off) keeps only callers at that tier — the predicate runs in
the store query next to ``kinds`` / ``args_at``, so a RESOLVED-only page is not a
post-filter over an alphabetically truncated page (task 251). ``total_count`` then counts
matches of that request, and ``tier_filter`` names the filter (R5.6). Without the filter,
``tier_census`` reports the full hit set's tier breakdown when more than one tier is
present (omit-when-empty, 061). Depth 1 only.

A Method subject whose linked answer is empty may expand to the unresolved same-named
CALL sites near it, ranked by shared subtree (258). Those rows are candidates the
resolver declined to link, so the answer is ``proximity_candidates``, never ``ok``, and
each row names ``candidate_of``.

``limit`` / ``offset`` page results (057). At depth 1 the store owns OFFSET; deeper walks
apply offset to the BFS hit stream. Complete enumeration is guaranteed at depth 1.

When bare-name resolution capped Method candidates alphabetically (task 054), a subject
outside that cap can have zero inbound edges while CALLS sites named its bare method still
exist. Those sites are counted in ``unresolved_bare_calls``, and an empty answer then uses
``reason=bare_name_truncated`` instead of ``no_matches``.

When a Function subject still has unlinked CALLS targeting its short name
(schema-unqualified ``EXEC`` that could not resolve uniquely — task 214), an empty
answer uses ``reason=relation_unmodelled_for_language`` instead of ``no_matches``.
The same unmeasured route fires when ``production_count`` is 0 on a depth-1 indexed
subject with surviving test callers: ``reason`` is not ``ok``, and
``unlinked_same_name_sites`` counts the unlinked inbound that name it (272). A Function
answer with hits carries the same count, ``authoritative: false`` and the
``unlinked_same_name_sites`` caveat when such CALLS remain beside them (334). A Method
answer at depth 1 counts ``unresolved_receivers``: calls in its language by its bare name on
a receiver no type reached (an untyped parameter, say) and left unlinked; ``exclude_tests``
drops test callers from it too (393).

When another language is indexed but no linked ``*->L`` pair reaches the subject's
language (221/238), an empty answer upgrades to ``relation_unmodelled_for_language`` only
if another language names the subject — as an unlinked call's callee, or as a literal
argument of any call that is the name or ends in it (``querySP('dbo.name')``). Otherwise it
stays ``no_matches`` and lists those languages in ``cross_language_unmeasured`` (409).
Hits carry ``authoritative: false`` only when the stamped census has cross-language
edges (276); an empty census is status-only. ``caveat_limits`` states the cost (251).

``subject_refreshed_only`` is present (and ``true``) only when read-through freshness
reparsed the subject's file this call — neighbors were not re-verified (035 / 061).
An untracked indexable file matching the subject is ``reason=not_indexed`` plus
``try_instead=build_or_update_index`` — never ``no_such_symbol`` (092).

``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
``key=value`` line naming subject, question, answer and the revision the index describes.
The weakest tier present is named, so the line can never claim ``RESOLVED`` over a
``HEURISTIC`` hit. An answer with no index carries no line (task 100).

``exclude_tests`` (default off) drops test-role callers in SQL; at depth > 1
they are pruned from the walk so they never expand (313 shape; 332).
On a ``behind`` index the built graph answers, labelled with ``last_commit``: an unchanged
subject as ``index_behind``, one the working tree no longer declares as
``index_behind_subject_removed`` (388). A subject whose changed file cannot be re-read
refuses as ``index_stale``; its ``try_instead_hint`` names the exact call, where
``serve_behind=true`` answers it as ``index_behind_subject_changed`` (267). Asked from
another worktree of this repo, rows from files it changed give way to its own edges onto
the subject, at ``HEURISTIC``, as ``reason=worktree_overlay`` (389). ``caller_root`` names
that worktree for this call alone — an absolute path inside a checkout of this repository,
ahead of the roots and ``CA_CALLER_ROOT``; any other value is refused as an error (408).

A leading-anchor difference from the stored qname is re-pointed and answered;
``resolved_qname`` names the stored form (075/122). An exact stored qname is unchanged.
```

### `find_references`

The full description before the tool surface was shortened, verbatim:

```text
Where is this symbol used across the codebase?

Resolved edges whose ``target_qname`` is ``qname``, with confidence tiers.
A **Table** or **Column** subject returns linked ``WRITES`` and ``DELETES``
(278/328). A Table unions writers of the table and of its CONTAINS columns
(named-column sites never target the Table qname); each writing statement is
one row with the named columns folded in (329). A Column is the narrower
per-edge set. ``DELETES`` target the Table only. ``kinds`` (Table / Column subjects
only, default ``["WRITES", "DELETES"]``) picks the relations instead: ``["READS"]``
lists the routines a ``select`` reads the table from (RESOLVED) and host strings that
begin one (HEURISTIC) — 390 — and on a Column the statements naming that column, by
``alias.col`` or, beside one source, a bare name (410); a Table's row then lists them
in ``columns``. ``column_reads_unknown`` counts its table's readers that named no column
of it (a ``select *``); a bare name beside several sources is never bound.
``kinds_ignored`` lists asked kinds a non-Table/Column subject ignores.
Unlinked edges of an asked kind that still name the table are counted as
``unlinked_writes_count`` / ``unlinked_reads_count``. On a multi-language
index the answer carries ``writes_emitters_only`` when a covered language
emits no ``WRITES``. A host-language string that begins a write is read at
``HEURISTIC`` where its adapter reads one; SQL built at runtime is not
(§19 / 281 / 335). ``REFERENCES`` (a ``Foo::class`` mention) is FQN-linked at
``DYNAMIC`` — a candidate list, not a proven use. When every returned hit
is ``DYNAMIC``, the payload sets ``authoritative: false``. When another
language is indexed but no linked ``*->L`` pair reaches the subject's
language (238/276), a hits-bearing answer is
``authoritative: false`` only when the stamped census has cross-language edges;
an empty census is status-only. ``reason`` stays ``ok``.
An ``IMPORTS`` naming an indexed file is linked since 188, so a
**File** subject lists its importers; one naming a symbol or an unresolvable specifier stays
bare. When unlinked ``REFERENCES``/``IMPORTS`` exist for an indexed subject and linked
hits are zero, the
payload uses ``reason=relationship_not_modelled``, ``try_instead=search_symbol`` (it
enumerates the class's methods) and a ``try_instead_hint`` naming the two-step (065/093)
— unless the subject is a ``Class`` with ``CONTAINS`` children, in which case the same
call returns their inbound ``CALLS``/``NEW`` as ``reason=via_members`` (252; never ``ok``).
When ``production_count`` is 0 but test hits remain, the same unmeasured route runs
and ``unlinked_same_name_sites`` counts the unlinked inbound that name the subject (272).

``include_source`` (default off, so the common case stays token-frugal) adds each site's
own source line as ``source``, capped in length. A site whose file drifted since indexing
is never quoted: those hits carry ``source_stale`` instead.

``limit`` / ``offset`` page in store edge order (057); default limit is
``CA_MAX_RESULTS``. Optional ``path_prefix`` narrows to edges whose stored file
path is under that index-root-relative POSIX prefix (315).

``subject_refreshed_only`` is present (and ``true``) only when read-through freshness
reparsed the subject's file this call — neighbors were not re-verified (035 / 061).

``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
``key=value`` line naming subject, question, answer and the revision the index describes,
carrying ``authoritative`` when every hit is ``DYNAMIC``. An answer with no index carries
no line (task 100).

On a ``behind`` index the built graph answers, labelled with ``last_commit``: an unchanged
subject as ``index_behind``, one the working tree no longer declares as
``index_behind_subject_removed`` (388). A subject whose changed file cannot be re-read
refuses as ``index_stale``; its ``try_instead_hint`` names the exact call, where
``serve_behind=true`` answers it as ``index_behind_subject_changed`` (267). Asked from
another worktree of this repo, rows from files it changed give way to its own edges onto
the subject, at ``HEURISTIC``, as ``reason=worktree_overlay`` (389). ``caller_root`` names
that worktree for this call alone — an absolute path inside a checkout of this repository,
ahead of the roots and ``CA_CALLER_ROOT``; any other value is refused as an error (408).

A leading-anchor difference from the stored qname (``Ns\Sub\Enum`` vs
``\Ns\Sub\Enum``) is re-pointed and answered; ``resolved_qname`` names the
stored form (075/122). An exact stored qname is unchanged.
With a ``records`` rule the subject's declared records ride in ``records``, each with
its declared ``attributes``; ``records_filter`` (``{"tier": ["A"]}``) keeps those whose
attribute equals a value, and a name no block declares raises ``ValueError`` (407, 413).
```

### `find_implementations`

The full description before the tool surface was shortened, verbatim:

```text
Which types extend or implement this one? Direct subtypes only (not transitive).

``limit`` defaults to ``CA_MAX_RESULTS``; ``offset`` pages in store edge order (057).
``EXTENDS``/``IMPLEMENTS`` are resolver-linked when present; an empty linked page still
routes through the shared empty-inbound predicate (264) so unlinked evidence of any mapped
kind cannot read as bare ``no_matches``. ``subject_refreshed_only`` is ``true`` only when
read-through freshness reparsed the subject's file this call — neighbors were not
re-verified (035 / 061). For transitive subtypes, see ``impact``. A leading-anchor
difference from the stored qname is re-pointed; ``resolved_qname`` names the stored
form (075/122). An exact stored qname is unchanged.
```

### `find_view_data`

The full description before the tool surface was shortened, verbatim:

```text
What variables does this handler make available to its template?

Each hit carries the ``key`` a caller can read in the view, the call-site ``line``, and
``rule: true``. Needs ``CA_INDIRECTION_RULES`` with a ``view_data`` setter rule: with no
rules configured the answer is ``reason=capability_not_configured`` (the tool is inert on
this index), which is distinct from a configured repo where this handler simply publishes
nothing (``no_matches``). ``file`` is the subject's declaration path when known.
A leading-anchor difference from the stored qname is re-pointed; ``resolved_qname``
names the stored form (075/122). An exact stored qname is unchanged.
```

### `include_graph`

The full description before the tool surface was shortened, verbatim:

```text
What does this file pull in, and what pulls it in?

``direction`` is ``imports`` (what this file includes), ``imported_by`` (who includes it),
or ``both``. ``depth`` defaults to 1 (direct); deeper values BFS over linked ``INCLUDES``
only, capped by ``CA_MAX_RESULTS``. ``unresolved_includes`` counts bare/dynamic includes on
the seed's ``imports`` side and is omitted for ``imported_by`` (inbound unresolved is not a
confident zero — 065). An empty inbound answer with unlinked includes whose path tail
could be this file returns ``reason=relationship_not_modelled``, lists them in
``unlinked_includes``, and adds a ``try_instead_hint`` but deliberately NO ``try_instead`` —
no registered tool reads unlinked include text (093); more fitting includes than the page
limit says ``unlinked_includes_truncated``; path matching ignores case. When none could,
an indexed file's zero is attested:
``no_matches`` naming any included same-named file in ``same_basename_included``, and
``authoritative: true`` unless ``dynamic_includes_unchecked`` counts includes naming no
file at all (363).
An empty inbound answer on a file whose **language** emits no ``INCLUDES`` at all returns
``reason=relation_unmodelled_for_language`` instead of a confident zero: the relation is
carried under another edge kind here (186). Where that kind is ``IMPORTS``, which 188 links,
``try_instead`` names ``find_references``; where the language emits neither, it stays a hint
with no route.
```

### `impact`

The full description before the tool surface was shortened, verbatim:

```text
What could break if I change this file or symbol — the blast radius?

Bounded best-score over changed paths and/or qnames. Seeds are the union of every indexed
node on ``paths`` and the explicit ``qnames``.
``depth`` defaults to ``CA_IMPACT_DEPTH``; the node budget is ``CA_IMPACT_MAX_NODES``.
HEURISTIC/DYNAMIC neighbors are returned with their tier but do not expand the
frontier. Missing seeds and a missing database yield an empty successful result.

Walks resolver-linked IMPACT kinds only — an empty answer is a modelled zero for those
kinds, not ``relationship_not_modelled`` (task 065; see ``find_references``). When a
Method seed still has unlinked same-name CALLS, ``unlinked_same_name_sites`` names them
and the answer is not authoritative (330).

``seeds_dropped`` counts every requested subject that produced no seed — a qname that is
absent or resolves to many, a path with no indexed node — plus any seed the node budget
pruned. ``results: []`` with ``seeds_dropped: 0`` therefore means a modelled zero and
nothing else (task 102). When every named subject was lost the answer also carries
``reason`` (``no_such_symbol`` / ``name_not_qualified`` / ``not_indexed``, with
``candidate_count`` / ``try_instead`` where the classifier has them).

A seed whose qname has more than one definition is **not** walked (the graph links callers
by qname, so it cannot be attributed to one twin): its sites are listed under
``ambiguous_definitions``; when no seed was walkable, ``reason=subject_ambiguous`` (161).
A rules file's ``definitions.precedence`` naming one definition walks the qname with its
seed placed there — the walk still spans every definition's edges — the rest under
``other_definitions`` (414).
The default payload names the revision it describes — ``staleness`` plus ``last_commit`` —
so a blast radius acted on destructively is never silently undated (8-E).

At ``standard`` a row whose symbol is stored as test carries ``test_role_source``
(``adapter`` / ``path_convention``, how it was decided); a row without it is production.
A row on a stamped mirror pair carries ``mirror_counterpart`` (its indexed twin) or
``mirror_no_counterpart: true``. These are row properties — no count splits the radius.
``exclude_tests`` drops test sources inside the walk, before the node budget and the page,
so page one holds production rows rather than those a page of tests left over.

``routes`` names URLs a declared ``routes`` table maps to a handler (385): each seeds its
target, and one that matches no route counts in ``seeds_dropped``; one whose key several
declared rows give different targets seeds them all and, unless each row carries its own
``when`` (a conditional route, 415), the answer carries ``ambiguity: "route_collision"``
with ``route_candidates`` (411). Whenever a table is
declared, ``routes`` in the answer lists each route whose target is a seed or in the radius
(``HEURISTIC``, ``rule: true``) — omitted when none reaches it.

With a ``records`` rule, ``records`` lists the declared records on the subject and its
radius, each with ``via`` (its carrier), ``distance`` and ``direct`` (on a seed, a member a
seed contains, or a seed's file): direct rows first, then by distance, at most
``records_limit`` (at most the page, ``limit_capped_to`` when reduced); ``records_total``
counts them all.
``records="direct"`` keeps the direct rows alone; a ``stop_at`` hub file carries none into
the radius and ``records_stopped`` counts what it kept out (407, 412). ``records_filter``
(``{"tier": ["A", "B"]}``) keeps records whose declared attribute equals a value; a name
no block declares raises ``ValueError`` (413).

``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
``key=value`` line naming subject, question, answer and the revision the index describes,
with ``seeds`` beside ``answer`` (``answer == seeds`` is the modelled zero: nothing beyond
the seeds depends on them) and ``seeds_dropped`` / ``frontier_skipped_non_resolved``.
No line is emitted when there is no index, or when no seed resolved — a question nothing
answered would be signed ``answer=0``, and a claim that cannot be re-run is decoration.
```

### `impact_modules`

The full description before the tool surface was shortened, verbatim:

```text
Which modules does changing this reach, and how much of each?

The same bounded walk as ``impact``, summarised by the business-module table the system map
prints — so the two never disagree. Each row carries the symbol count split by confidence
tier, because a module reached only through HEURISTIC edges has not been *shown* to be
reached (136), and at ``standard`` one exemplar ``file:line`` to read first.

Files no module covers are counted under ``unassigned`` rather than given a home. A walk
that hits ``CA_IMPACT_MAX_NODES`` sets ``walk_truncated`` and labels every count an
under-estimate (124) — a bounded walk reporting a total without saying so is a false total.

``sign`` adds the quotable ``claim`` line, as on ``impact``.
```

### `subtree_dependencies`

The full description before the tool surface was shortened, verbatim:

```text
Can this subtree be deleted — what still crosses into or out of it?

Reports crossing edges at directory-prefix grain, split by ``confidence_tier`` and by
whether the target symbol is declared only under ``subtree`` (attributable) or also
elsewhere (unattributable). The unattributable total always sits beside the attributable
one — a blocker count without its unknown companion is structurally unavailable.

``counterpart`` optionally narrows the other side (e.g. ``src/`` when ``subtree`` is
``legacy/``). Ranked ``dependent_files`` (outside) and ``depended_on_paths`` (inside,
mirror-collapsed when siblings mirror) carry edge counts for prioritisation.
``dynamic_bridges`` surfaces alias files whose only link is ``DYNAMIC`` — no static edge
is never rendered as no dependency. Node-budgeted like ``impact``; truncation is disclosed.
``depended_on_path_total`` counts declaration paths before the mirror collapse, so it can
exceed the collapsed list even when nothing was truncated.
```

### `reachable_from`

The full description before the tool surface was shortened, verbatim:

```text
What is actually reachable from the app's entry points (and what is dead)?

Walks forward from ``CA_ENTRY_POINTS`` over RESOLVED impact relations.
Default ``depth`` is unset — walk until the frontier empties or
``CA_IMPACT_MAX_NODES`` binds (transitive closure). Pass ``depth`` to cap hops;
``depth_exhausted`` / ``truncated`` signal an incomplete answer. Unset entry
points yield ``status=no_roots_configured``.

Reachability uses the same linked IMPACT kinds as ``impact`` — empty/unproven is not
``relationship_not_modelled`` (task 065).
```

### `find_orphans`

The full description before the tool surface was shortened, verbatim:

```text
Which symbols and files look unused — nothing calls them and no entry point reaches them?

Each orphan carries ``why``: ``no_inbound`` or ``unreachable_from_roots``. Reachability
starts from ``CA_ENTRY_POINTS``; HEURISTIC-only neighbors are ``unproven``, never orphans.
Default walk is closure (see ``reachable_from``); unset entry points yield
``status=no_roots_configured``.

``limit`` defaults to ``CA_MAX_RESULTS``; ``offset`` pages orphans in store order (057).
``total_count`` is the full orphan population, not the page length, and ``truncated``
describes this page alone — page until it is false. ``unproven_total`` is the full unproven
count — at ``minimal`` the rows themselves are omitted so large repos stay transport-safe,
at ``standard`` they are capped to one page.

**Three refusals, and none return rows** (182 / 279). Roots that match no file give
``status=roots_matched_nothing``; a walk that hit ``CA_ORPHANS_MAX_NODES`` gives
``status=walk_budget_exhausted``; an index stamped with an unmodelled resolution strategy
(registered class autoload, …) gives ``status=resolution_unmodelled`` — include-based
orphan counts are unmeasured there, not dead code. ``status=ok`` with no rows still means
nothing is orphaned, which is a real answer (102).
```

### `explain_path`

The full description before the tool surface was shortened, verbatim:

```text
How does one symbol reach another — the shortest path between them?

Walks outgoing CALLS/NEW/INCLUDES/EXTENDS/IMPLEMENTS from ``from_qname`` to ``to_qname``
(same kinds as
``impact`` / ``reachable_from``). Default ``depth`` is unset — walk until
the frontier empties or ``CA_IMPACT_MAX_NODES`` binds. A RESOLVED-only path
is ``status=path``; a path that needs HEURISTIC/DYNAMIC hops is
``unproven``. Missing endpoints → ``unknown``; bound hit before ``to`` →
``incomplete``; both present with no route → ``no_path``.

Path search is over linked IMPACT kinds — ``no_path`` is modelled, not
``relationship_not_modelled`` (task 065).
```

### `architecture_overview`

See also the `architecture_overview` section above.

The full description before the tool surface was shortened, verbatim:

```text
What are this codebase's top-level layers, and how do they depend on each other?

Groups every indexed file into a layer, orders the layers by net dependency direction, and
names the entry points — the map an onboarding reader would otherwise build by hand.
``results`` is the layer list, capped at ``CA_MAX_RESULTS`` with ``truncated``, and
``total_count`` is the layer count before the cap. ``standard`` adds each layer's degrees, a
repo-level ``summary`` — whose ``reachability`` splits the zero-inbound modules into the
populations they are (web surface, vendored, tests, dynamic, no-edge-either-way), keeping
the raw total beside it — and ``cross_layer_edges`` (layer → layer crossings, heaviest
first, capped with its own flag). ``verbose`` adds one row per module in layer order with
its degrees and role — ``modules_truncated`` says the cap bit, and ``offset`` pages further,
so no layer's modules are unreachable. ``method`` names how the grouping was derived, so a
caller can tell a path-derived split from the dependency-direction fallback.
```

### `guided_tour`

See also the `guided_tour` section above.

The full description before the tool surface was shortened, verbatim:

```text
What should I read first in this codebase, in dependency order?

A topological walk of the include/call graph, seeded from entry-point files (zero
inbound) that **lead somewhere**, ranked by out-degree and reading-seed layer (HTTP /
Entry before Config — 131), at most a quarter of the budget so the walk always has room
to expand — a repo with more entry points than budget would otherwise spend it all on
roots and traverse no edge at all (106). A component no entry point reaches is
re-seeded rather than dropped. Cycles
become one strongly-connected component so the walk cannot loop. Each stop is a file
with a one-line rationale. The walk is bounded by ``CA_IMPACT_MAX_NODES``; ``results``
is one page of ``CA_MAX_RESULTS`` stops from ``offset``, and ``results_offset`` says
which page. ``truncated`` is true when the node budget left an indexed file out of the
tour or when stops remain after this page, so the rest of the order stays reachable.
``minimal`` returns files only; ``standard`` adds ``rationale`` and, for a cycle, the
``scc`` members.
```

### `trace_capability`

The full description before the tool surface was shortened, verbatim:

```text
How this codebase routes an incoming request — the capability flows one subject is in.

Prefer this over Grep/Glob when the question is *"how does a request reach the code that
produces the response?"* or *"what happens when a user does X?"*. Answers for **one**
subject: an entry symbol (``qname``), a file (``path``), a business module (``module``), or
a URL a front controller dispatches at run time (``route``, read through a declared
``routes`` table: its flows start at the route's target, whose hop is ``HEURISTIC`` with
``rule: true``; a URL whose key several declared rows give different targets traces every
one — under each row's own ``when`` label a conditional route, each flow's ``route``
carrying ``when``/``source`` (never evaluated), else ``ambiguity: "route_collision"`` with
``route_candidates``; an unmatched URL
answers ``no_such_symbol`` with ``nearest_routes``; no table answers
``capability_not_configured``). Supply exactly one; naming none or several
answers ``reason: name_not_qualified``. Each
result is one flow — its seed, its ordered ``steps`` (``qname`` · ``file`` · ``layer`` ·
``kind`` · ``tier``), how it ``ended`` and its ``sink``. A subject the index does not hold
answers ``no_such_symbol``; one it holds that joins no traced flow answers ``no_matches``
and routes to ``architecture_overview`` — never an empty ``results`` presented as an answer.
An index where no flow could be seeded (no declared entry point, no entry-named path)
answers ``capability_not_configured`` for every subject and routes to ``get_index_status``,
which nominates entry-point globs.
Carries no layer table, matrix, hub list or capability table: for the whole picture call
``architecture_overview`` instead.
```

### `generate_onboarding`

See also the `generate_onboarding` section above.

The full description before the tool surface was shortened, verbatim:

```text
Write committable onboarding docs for this repo — overview, guided tour and flows.

Reads the index and writes **up to five files** under ``docs/onboarding/``: ``overview.md``,
``tour.md``, ``flows.md``, ``manifest.json``, and ``index.html`` — one self-contained page
that embeds the same facts, so it opens offline with no server and no fetch. There is **no
per-module page tree**: 500 sub-kilobyte pages, one per node-budget slot, were emitted on
every repo and carried nothing a reader could not read off the path (205).
Regenerating rewrites this tool's own files, and removes the module pages a **pre-205**
``manifest.json`` recorded — a hand-authored file in that tree is left alone, and a tree
holding these names without that manifest is refused rather than overwritten. A versioned
dump of the same structure lands under ``.code-atlas/onboarding/artifact.json``
(gitignored, ``ARTIFACT_VERSION``). Deterministic given the summarizer: no timestamps.
The walk that sizes the tour is the same node-budgeted subgraph ``guided_tour`` uses
(``CA_IMPACT_MAX_NODES``) — roots ranked by out-degree, capped at a quarter of the budget
so the tour describes files the walk actually reached (106); ``truncated`` is true when
that budget left an indexed file out.

Three independent axes (210 / 216):

- ``detail_level`` — how much of the *response* to return (same meaning on every tool that takes it); the
  response is discarded, so it does not reshape the committed tree.
- ``audience`` — which *sections* the written tree holds (``full`` / ``newcomer`` /
  ``maintainer``); unset takes ``CA_AUDIENCE``.
- ``working_roots`` — which *population* those sections draw from: restricts the tour,
  flow seeds and busiest-file pick to those trees (206). Omitted inherits
  ``CA_WORKING_ROOTS`` / config; a list wins over the environment; ``[]`` forces the
  whole index even when the environment scopes it.

``results`` lists the committed relative paths, capped at ``CA_MAX_RESULTS``.
``minimal`` omits the path to the ``artifact.json`` dump.
```

### `check_architecture_rules`

The full description before the tool surface was shortened, verbatim:

```text
Do the architecture dependency rules still hold on this index?

Reads ``CA_ARCHITECTURE_RULES`` (JSON files of path-set constraints). Each confirmed
violation is a RESOLVED walk from a source path set into a forbidden path set;
HEURISTIC-only evidence is listed under ``candidates`` and never counts as confirmed.
A ``required`` rule flags each source symbol that reaches none of its target qnames;
it is confirmed only when every edge its walk met was RESOLVED.
``total_count`` is the confirmed population; page with ``limit``/``offset`` until
``truncated`` is false. Empty answers name the cause: not indexed, rules unset,
no source file matched a rule, or no violation.
```

### `check_column_defaults`

The full description before the tool surface was shortened, verbatim:

```text
Which writers of this table omit a column that has a DEFAULT, and what is that DEFAULT?

Answers the defect class *"a column whose value comes from a DEFAULT because every writer
omits it"*. With no ``column``, scans every column of ``table`` that declares a DEFAULT;
with one, reports just that column. Each row carries ``omitted_count`` against
``writers_total`` — a ratio, not a bare list — plus ``omitted_by`` and ``named_by`` at
``standard``. A writer that named no columns at all is ``unmeasured``, never counted as
omitting; a table with no recorded writers answers ``status: table_has_no_writers`` and
carries **no** ``omitted_by``, because an empty list there would claim a zero the graph
cannot see. When linked writers exist but unlinked ``WRITES`` still name the table, the
envelope carries ``writers_partial`` and a hint naming the remaining forms (215). Duplicate
``CONTAINS`` declarations collapse to one row with ``declarations`` when N>1. Needs a
SQL-layer index (task 022); ``column`` takes the full member qname
(``dbo.Trans::ChangeUser``) or the bare column name.

``table`` may be bare (``Trans``): one indexed Table of that name is measured and named in
``resolved_qname``; several (one per schema) answer ``reason: subject_ambiguous`` with no
rows and each qualified candidate in ``ambiguous_definitions``; none answers
``no_such_symbol`` with ``try_instead: search_symbol`` (320).

``default_expr`` replaces ``table`` as the subject (391): every column whose stored
``DEFAULT`` is that expression — compared without case, brackets, whitespace or outer
parentheses — each row naming its ``table`` and measured against that table's writers,
with ``writers_partial`` per row. Pass exactly one of ``table`` and ``default_expr``;
``column`` narrows a ``table`` only.
```

### `diff_architecture`

The full description before the tool surface was shortened, verbatim:

```text
Diff two 112 dataset (or onboarding manifest) JSON files for architectural drift.

Both sides must name the same ``index_root`` and the same dataset ``version``; a mismatch
is refused with a direction-aware reason rather than rendered. Identical architecture
yields an explicit *no architectural change* statement — never an empty artifact.
Paths are relative to the indexed tree; an absolute one must still resolve inside it.
```

### `verify_refs`

Its description is one line (443); the rest is here. Each row is one reference with one state and
a `reason` — `ok`, `moved` (one `successor`, or `successors` on a split), `gone` (`last_seen`, and
`nearest_existing` for a path), `never_existed`, `ambiguous`, `unknown` (never `ok`) — plus
`strength`: `strong` for a path git or the tree knows, a path with a folder and a suffix, or an
adapter-shaped symbol written as code; `weak` otherwise. **Actionable** = `moved`/`gone`, strong, not
archive. With no `globs`, `doc_class`, `state`, `strength` or `limit` the answer is `actionable`
(counts per class and state), `actionable_total`, and up to 20 compact rows, instruction files first;
any filter answers every state with `by_class`, `files` (per-file actionable counts) and full rows. A
reference doc's weak rows leave every summary unless `strength` names them (`weak_rows_not_counted`).
A member its class does not declare is `ok` (`inherited`) when an ancestor declares it, `gone` only
when git shows it left the class's file, else `unknown` (`not_declared_on_container`). A `moved` row
with one successor and an in-place form is `patch_ready`; `format: patch` answers `edits` and
`apply_with`. Memory rows (`<agent-memory>/…`) are edits only — they are outside git. The shell adds
`--format jsonl` (every row, uncapped, keyed `class`/`file`/`ref`) and `--refs-diff OLD NEW`.

### `compute`

Its description is one line (443); the catalogue (`compute` with no `template`) lists each id, its
question and typed params, and the table row above has the semantics. `multi_defined` counts one
object per kind and qualified name — a namespace each file re-declares is none — and takes
`language`; ask `kind: Function, language: sql` for redefined SQL routines (procedures, functions,
triggers). An absence's mention check is a case-insensitive whole-word `git grep`, kept to files in
`language` when one is given; past its deadline a row is `mention_unchecked`, never strong.

### `class_diagram`

The full description before the tool surface was shortened, verbatim:

```text
Mermaid class diagram for one class plus its ancestry, or every type in one file.

Inheritance arrows are ``EXTENDS`` / ``IMPLEMENTS`` / ``USES_TRAIT`` only. Associations
come from declared property and parameter types — never from CALLS/NEW. ``limit`` caps
members per type and is disclosed when it bites. Pass ``qname`` or ``path``, not both.
```

## The tool surface is pinned (428)

- **Annotations.** Every tool declares MCP annotations from one table in `code_atlas/main.py`: the
  queries `readOnlyHint: true`; `build_or_update_index` and `generate_onboarding`
  `readOnlyHint: false`, `idempotentHint: true`, and `generate_onboarding` alone `destructiveHint: true`
  (it deletes the pages a previous run wrote). Every tool is `openWorldHint: false`. A tool absent from
  the table fails server start.
- **Closed schemas.** Each input schema has `additionalProperties: false`, closed domains as `enum`,
  a `maxLength` of 4096 on any other string and a `maxItems` of 1000 on any array (a map such as
  `records_filter` is bounded in keys and values). An unknown or wrongly typed argument is refused as a
  tool error before the tool runs; `"10"` for an integer is not coerced.
- **Errors** reach the client as an `isError` result naming the tool, never the exception text; a
  refusal a tool raises on purpose (`ValueError`, such as a bad `path_prefix`) keeps its message.
- **The manifest** `tests/fixtures/tool_manifest.json` holds each tool's name, description, schema and
  annotations. After a change, run `python scripts/gen_tool_manifest.py` for the diff, then `--write`
  to accept it; `tests/test_tool_manifest.py` fails on drift, and CI and `scripts/gate.sh` fail a
  range that changes it without an added `CHANGELOG.md` line that says "tool surface" or names a
  changed tool.

## Repo text in an answer is marked (429)

A docblock, a source slice, a symbol name and a path are written by the indexed repo. Every answer
escapes each control, bidi and format character in them as a visible `\u{XXXX}` (source and markdown
keep their line breaks), and lists the fields that hold repo text in `untrusted_fields`, for example
`["source", "file"]` or `["results[].qname", "results[].file"]`; a batch prefixes `subjects[].`. The
server `instructions` say once that those fields are data, never instructions. A field that echoes an
argument you passed (`qname`, `subtree`) is listed too when present. A name holding a control comes
back escaped, so it no longer round-trips into the next call. The table is `code_atlas/untrusted.py` `FIELDS`; a tool absent from
it fails server start.

## What it cannot answer — reach for `grep` instead

The verdict of the field retros ([protocol](runbooks/field-retro.md); the round corpus is kept
outside this repo, findings land in [PLAN §19](PLAN.md#19-project-context--decision-log)):
code-atlas is excellent at **who / what / where** over resolved symbols, and structurally
unable to answer **"is something missing here?"**. The
index holds what the adapters parsed. A question whose answer is an *absence* cannot be settled by a
store of presences, and asking anyway buys a confident wrong answer.

| Question shape | Why the index cannot settle it | Ask instead |
|---|---|---|
| "Is there any call site that forgets to check X?" | an omission leaves no node and no edge | `grep` the positive form, then subtract |
| "Does any file still use the old constant?" | string-only usage is not a resolved relation | `grep` — it is literal text |
| "Which of these have no test?" | an untested symbol has no *absence* row; only `find_callers` + `test_count` can bound it | `find_callers` per subject, then read the zeros as *candidates* |
| "Is this config key read anywhere?" | keys live in strings, not the symbol table | `grep`, then `find_references` on whatever resolves |

The positive twin of each of these **is** a graph question — *who calls this*, *what writes that
table*, *which modules does this change reach* — and that is where the ~69× token saving lives.

## Coverage honesty — before you read a zero as "it is not there"

Three fields say the index never looked, rather than looked and found nothing:
`unconfigured_adapters` (the adapter is not launchable), `unindexed_languages` (it runs, the graph
holds none of that language) and `unindexed_same_basename` (same-stem files whose suffix the index
does not hold, beside a **non-empty** page). Field rules are the contract's, in
[`CONVENTION.md` §6](CONVENTION.md#6-mcp-tool-conventions); what matters at call time is this:

- **They are omitted when empty**, so seeing one at all is the signal (061).
- **`detail_level: "minimal"` omits all three** (223) — and `reachable_from`, `find_orphans` and
  `architecture_overview` *default* to `minimal` (268). On those three, a default-level zero is not
  an audited zero: ask for `standard` before concluding absence.
- **A partial answer needs them as much as an empty one** (192). One hit with `reason: ok` for a
  symbol with hundreds of sites in a language the index does not hold is a false negative wearing a
  modelled zero's clothes — `reason` stays `ok`, the field beside it is the caveat (299).

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
file drifted may therefore answer with `source_stale: true` rows, or an empty miss as `index_behind`,
where a single call would have repaired it — a name search never refuses (388), and the answer says
so rather than reporting a quieter `no_matches`. When a sweep mixes vouched `ok` answers with such
subjects, the envelope names them in `index_stale_subjects`, with `repair_budget_shared` and
`repair_budget_order: "queries"` (275); a fully-vouched sweep stays unchanged. Each such entry
carries `retry_as: "query"` so the single-subject call can spend the whole budget. A `kind=` filter that
drops an exact-name hit of another kind answers `kind_excluded` (with those kinds), not absence.
A `path_prefix=` filter that drops an exact-name hit outside the subtree answers `path_excluded`
(with those file paths), not absence (315); `read_symbol` answers the same miss the same way (339). `exclude_tests=true` drops test-role nodes in SQL
before paging, and `total_count` counts the filtered set (332).

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
| `compute` | its subject is a template over the whole graph; a list of templates is a batch the client can send itself |
| `verify_refs` | its subject is the doc corpus; `globs` already narrow it to a list of files |
| `explain_path` | its subject is already a pair; a list of pairs is a query language, which 101 deliberately is not |
| `architecture_overview` | its subject is the whole index — there is one repo to lay out, and a list of subjects has no meaning for a repo-wide shape |
| `guided_tour` | its subject is the whole index — there is one reading order, and a list of subjects has no meaning for a repo-wide walk |
| `generate_onboarding` | a write is one artifact against one tree — R4.3's single writer, not a fan-out |
| `check_architecture_rules` | its subject is the configured rule set — a list of rule ids is filtering, not a batch of independent questions |
| `diff_architecture` | its subject is already a pair of snapshots — a list of pairs is a query language, which 101 deliberately is not |
| `class_diagram` | its subject is one type (plus ancestry) or one file — a list of subjects is N diagrams, and the honest form is N calls |
| `check_column_defaults` | its subject is one table, or one `default_expr` (391) — a list of tables is N independent scans with no shared arithmetic |
| `trace_capability` | its subject IS the question — *what happens when a user does X* is asked of one entry, one file or one module. A list would return N unrelated traces and reintroduce exactly the over-answering 199 exists to remove (101) |

## Operator prompts (human-invoked — not part of the agent tool surface)

These MCP prompts are **operator recipes a human invokes**; an agent's client exposes only the tools
above to the model, so a model never sees a prompt (task 081). Agent routing lives in the tool
descriptions themselves (each names the question it answers — task 069), not here. `which_tool` is
the exception a model *can* read: task 200 generates its map into an Agent Skill at
[`contrib/skill/`](../contrib/skill/) — generated from the registered tools, never hand-edited, with
a drift guard.
The blind recognition probe that scores whether those descriptions route — and that separates
name-only answers from description-backed ones — is
[`docs/runbooks/tool-recognition-probe.md`](runbooks/tool-recognition-probe.md) (081, 097).

| Prompt | Recipe |
|---|---|
| `explore_area` | status → search/outline → read only what's needed |
| `find_usages` | status → find_references / find_callers / find_implementations → read to confirm |
| `impact_of_change` | status → impact on the changed paths/qnames → read only the blast-radius surface |
| `which_tool` | a recognition map: which tool answers a given question, across all 26 tools |

## Hooks (opt-in)

code-atlas answers when asked. Five hooks cover the moments an agent was never going to ask — an
edit or a pull that drifts the index, a `Read`/`Write` that could carry one line of context, a session
boundary, and a grep for a symbol. All are opt-in and code-atlas never edits your settings itself:
install the Claude Code plugin (344, `claude plugin install code-atlas@code-atlas`), which wires all
five, or merge the generated [`settings.snippet.json`](../contrib/claude-code/) by hand. Poke,
refresh, signal and state take `--verbose` (or `CA_<HOOK>_VERBOSE=1`) as an install check; an
install failure always prints one stderr line.

### Keep the index fresh while Claude edits (opt-in)

Task 035 already reparses drifted files at query time. For eager updates after Claude Code
`Edit`/`Write` on a file **any** installed adapter owns — the matcher is generated from each
adapter's own declared suffixes, so the next adapter is covered the day it lands (200) — install the
PostToolUse hook under
[`contrib/claude-code/`](../contrib/claude-code/) (`code-atlas-poke` console script + `"async": true`);
opt-in git refresh after pull, checkout, commit and rebase via [`contrib/git/`](../contrib/git/) (`code-atlas-refresh`,
background — never auto-installed into `.git/hooks`); the plugin also runs it async at `SessionStart`.
Safe no-op when `.code-atlas/graph.db` is missing; does not stall the tool round-trip. A refresh
that is refused or errors is recorded as `.code-atlas/refresh.refused`, which `get_index_status`
names as `refresh_refused` (with the time and the fix) until a build succeeds (401). A contract
refusal's `hint` names the older half and its step, and the checkout the core was installed from (418).

### The read-time signal — a line that rides along with a file you are already opening (opt-in)

Field evidence (task 099): the three most consequential
decisions an agent made *without* calling code-atlas all wanted **one line at the moment of a `Read`
or a `Write`** — and none of them wanted a tool call. An MCP tool answers when asked; this fires
when the agent was never going to ask, so it is a **hook**, not a tool.

`code-atlas-signal` emits at most one line (~150 tokens, hard cap) and exits 0. Called as a hook it
prints the line as `hookSpecificOutput.additionalContext` for the payload's event, because a hook's
plain stdout never reaches the model (346); called with arguments from a shell it prints the bare line:

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

### The session-boundary state line — the index state, restated when the first copy decayed (opt-in)

MCP `instructions` deliver the index state once, on `initialize`; a long session outlives it and a
compaction drops it, so agents that started a multi-minute build filed its progress signal as missing
(322). `code-atlas-state` restates
`get_index_status`'s own `summary` — lifted, never recomposed — at `SessionStart` (its `compact`
source is the post-compaction delivery), `PreCompact`, and `PostCompact` where a host names it. While a build holds the lock it appends the
live phase and names `code-atlas-build --status`. **Silent** when there is no index, or when the index
is current, no build runs and no full rebuild is pending; ≤ 90 tokens. The generated hook passes
`--expect-contract` and `--expect-version`, and the hook launches each configured adapter for its
handshake (3 s for all, else the contract a refused build recorded). Every half — tool, plugin,
adapter checkout — older than the newest prints first, with its fix in upgrade order, even on a current
index (348, 374), and so does a uv tool install pinned to `?rev=`, which `uv tool upgrade` never moves
(381). At `SessionStart` a skew, a pin or a pending rebuild goes out as JSON — `systemMessage` for the
developer, `additionalContext` for the agent — since that event's plain stdout reaches only the agent
(381); always exits 0; never builds, reparses or takes the build lock.
With `refs_session_line = true` it adds, at `SessionStart` only, one count-only line of actionable
doc references — instruction files first, strong `unknown` counted apart from `ok`, archive never —
inside the read signal's 150 tokens (439). It reads the counts a build or refresh stored, never the
docs; an index or docs that moved since say so in the line (443).

### The grep-time nudge — one line right after a grep for a symbol (opt-in, 345)

`code-atlas-nudge` runs at `PostToolUse` on `Grep` and on a `Bash` call that starts with `grep`, `rg`
or `git grep`. When the pattern matches a shape an adapter declared in its v13 handshake
(`symbol_shapes`, stamped into the index at build time), it injects one line through
`additionalContext` — *ask the index first, keep Grep as the cross-check*. A shape fires when the grep
is unscoped or scoped to that adapter's suffixes, and a `scoped` shape only in the latter. Once per
kind per session, and per subagent inside it (keyed `session/agent_id`, 377); firings append to
`.code-atlas/nudge.log`. Silent unless the index is settled — `current`, no build running, nothing
pending, the state hook's own judgement (377); never blocks; always exits 0.

## Configuration reference

Every knob resolves **environment → project file → default**. The project file is
`.code-atlas.toml` at the repo root (optional, meant to be committed); its keys are the environment
names lower-cased without the `CA_` prefix. A malformed value or an unknown key is a loud error, never
a silent fallback.

| Environment | `.code-atlas.toml` | Default | Meaning |
|---|---|---|---|
| `CA_DB_PATH` | `db_path` | `.code-atlas/graph.db` | index location (relative to the repo root). The file value must stay inside the repo; only the env var may point outside (341) |
| `CA_WORKERS` | `workers` | `max(1, min(cpu-2, 8))` | adapter processes during a build |
| `CA_ADAPTER_TIMEOUT` | `adapter_timeout` | `30` | seconds an adapter may stay silent before a build kills it |
| `CA_PAGE_LIMIT` | `page_limit` | `50` | query-time row ceiling for search/nav; a request above the cap is honoured to the cap and says so in `limit_capped_to`. Changing it does **not** require a rebuild (259) |
| `CA_MAX_CANDIDATES` | `max_candidates` | `50` | build-time resolver fan-out; changing it **requires a rebuild**. `CA_MAX_RESULTS` / project-file `max_results` alias here only — they no longer set the page cap (259). Since 258 fan-out no longer multiplies unresolved bare-name `Method` calls into the graph |
| `CA_MAX_SUBJECTS` | `max_subjects` | `25` | subjects one `search_symbol` sweep may take; a refused subject is named in `subjects_dropped`, never dropped silently |
| `CA_IMPACT_DEPTH` | `impact_depth` | `2` | hops the impact engine traverses (with default decay/floor, depths above ~8 are a no-op) |
| `CA_IMPACT_MAX_NODES` | `impact_max_nodes` | `500` | node budget for one impact query (seeds kept preferentially when over budget) |
| `CA_ORPHANS_MAX_NODES` | `orphans_max_nodes` | `500` | node budget for the reachability walk inside `find_orphans` only — deliberately **not** the impact knob, so tuning one cannot change which orphans exist |
| `CA_FULL_BUILD_CROSSOVER` | `full_build_crossover` | `0` (disabled) | files-to-parse above which an incremental escalates to a full build **for cost**, reported as `delta_too_large`. Off by default because measuring the anchor found no crossover below its own size — a delta there is cheaper at every size, since the resolve phase saturates around 1,000 files (212). Set it only from your own measurement (R2.3) |
| `CA_PATH_INDEX_MAX` | `path_index_max` | `20000` | path cap for the onboarding dataset's front-coded path index; when it trims, the dataset carries both the total and the shown count |
| `CA_MAX_FILE_BYTES` | `max_file_bytes` | `4194304` (4 MiB) | a source file above this is skipped and counted (`collection.skipped.oversize`), never truncated and never sent to an adapter. A project-file value is clamped to 64 MiB; so is every other project-file cap to its ceiling in `code_atlas/limits.py` — the environment is not clamped (430) |
| `CA_ENTRY_POINTS` | `entry_points` | unset | file globs that seed reachability. **`reachable_from` and `find_orphans` need this** — unset, they report *no roots configured* rather than guessing |
| `CA_STUB_ROOTS` | `stub_roots` | unset | dependency roots (e.g. `vendor`) to index declarations-only, so third-party signatures resolve; hits carry `stub: true`. Costs one extra pass |
| `CA_WORKING_ROOTS` | `working_roots` | unset | repo-relative directory prefixes the onboarding artifact treats as the reader's working tree. It narrows the onboarding tour, flow seeds and busiest-file pick; unset is the whole index |
| `CA_SOURCE_ROOTS` | `source_roots` | unset | extra repo-relative directories tried (in order) after the repo root and the importer's ancestors when resolving absolute imports. Needed for a `src/` layout or a mounted layer/package tree; unset keeps today's climb-only behaviour |
| `CA_PROJECT_FILES` | `project_files` | the ecosystem manifests, a root `README*` and an agent brief | repo-relative files the onboarding *Start here* section quotes and cites. Values are lifted from declared keys and reproduced verbatim, never summarised; a file that cannot be parsed becomes a stated gap and never fails the build |
| `CA_AUDIENCE` | `audience` | `full` | who the WRITTEN onboarding tree is for: `full` (every section), `newcomer` (orientation, a four-line summary, the layer vocabulary, the tour and the flows) or `maintainer` (every aggregate, no tour, no orientation). An unrecognised value falls back to `full` and the artifact states which audience it actually used |
| `CA_INDIRECTION_RULES` | `indirection_rules` | unset | JSON rule files mapping framework indirection to edges ([format](#indirection-rule-files)). **`find_view_data` needs this** — without `view_data` setters it answers `capability_not_configured`, not a zero |
| `CA_ARCHITECTURE_RULES` | `architecture_rules` | unset | JSON rule files of path-set dependency constraints. **`check_architecture_rules` needs this** — unset → `capability_not_configured` |
| `CA_DEFINITION_ORDER` | `definition_order` | unset | path globs, most authoritative first, naming the **live** definition of a qname defined more than once (437): one `<n>` in a glob reads a version from the path, highest wins (`["db/migrations/V<n>__*.sql", "db/snapshot/*.sql"]`). Read before a rules file's `definitions.precedence`, [same rules](#indirection-rule-files). In the toml anything but a list of globs fails loud |
| `CA_REFS_INSTRUCTION` · `CA_REFS_MEMORY` · `CA_REFS_REFERENCE` · `CA_REFS_ARCHIVE` | `refs_instruction` · `refs_memory` · `refs_reference` · `refs_archive` | `CLAUDE.md`, `AGENTS.md`, `.claude/rules|skills/**`, `.cursor/rules/**`, `.github/copilot-instructions.md` · the host's project memory folder · `docs/**`, wiki folders · none | the doc corpus `code-atlas query --verify-refs` reads, per priority class (438): repo-relative globs of markdown files, matched, never run (430). `archive` is reported and never counted; a file two classes name takes the more authoritative. Unset `refs_memory` reads Claude Code's memory folder for this repo (`$CLAUDE_CONFIG_DIR` or `~/.claude`, `projects/<repo path, non-alphanumerics as ->/memory`), a host choice the repo cannot move (443) |
| `CA_REFS_SESSION_LINE` | `refs_session_line` | `false` | `true` adds the stale-reference count line to `code-atlas-state` at `SessionStart` (439); off, nothing reads the corpus at session start |
| `CA_TOOLS` | `tools` | all tools | comma-separated tool allow-list. Opt-in field-18 six-tool preset (268): `get_index_status,search_symbol,read_symbol,find_callers,find_references,impact` (`code_atlas.main.FIELD18_TOOLS`). Default surface stays 26. |
| `CA_VARIANT_PAIRS` | `variant_pairs` | none | name-pattern pairs `compute`'s `variant_pairs` reads when no params name one (441): toml `[["*Async", "*"]]`, env `*Async|*,get*|set*`; each side a name with exactly one `*` and no other glob character, matched, never run. Region twins read the same way: `[["*<RegionA>", "*<RegionB>"]]` for `SaveOrder<RegionA>` / `SaveOrder<RegionB>` (443) |
| `CA_TOOLS` | `tools` | all tools | comma-separated tool allow-list. Opt-in field-18 six-tool preset (268): `get_index_status,search_symbol,read_symbol,find_callers,find_references,impact` (`code_atlas.main.FIELD18_TOOLS`). Default surface stays 25. |
| `CA_HOST_ROOT` | `host_root` | unset | absolute-path rewrite only (pair with `CA_CONTAINER_ROOT`; unused by the relative-path build) |
| `CA_CONTAINER_ROOT` | `container_root` | unset | absolute-path rewrite only (pair with `CA_HOST_ROOT`) |
| `CA_CALLER_ROOT` | `caller_root` | unset | the caller's worktree when the client reports no MCP `roots` — reads overlay it (389); ignored when roots arrive, and by a call that passes `caller_root` (408) |
| `CA_<LANG>_CMD` | `[adapter_cmd].<lang>` | — | the **complete argv** that launches one adapter in server mode . The file table is honoured only with `CA_TRUST_PROJECT_FILE=1` (341) |
| `CA_TRUST_PROJECT_FILE` | — (env only) | unset | `1` lets the repo's own `[adapter_cmd]` choose the argv. Unset, a table there is a loud error: a repo you index must not pick the command code-atlas runs (341) |

```toml
# .code-atlas.toml
workers = 4
page_limit = 50
max_candidates = 50
tools = ["get_index_status", "build_or_update_index"]   # only names the server serves; a typo is a loud error
# Optional: only needed if something passes absolute host paths to the adapter.
# host_root = "/home/you/project"
# container_root = "/app"

[adapter_cmd]
php = "docker compose exec -T php php /app/adapters/php/index.php --server"
typescript = "node /abs/path/to/code-atlas/adapters/typescript/index.js --server"
sql = "node /abs/path/to/code-atlas/adapters/sql/index.js --server"
python = "python /abs/path/to/code-atlas/adapters/python/index.py --server"
# or, where quoting bites (Windows paths), one word per entry:
# php = ["C:\\php\\php.exe", "adapters/php/index.php", "--server"]
```

### Indirection rule files

A call whose target is a **string argument** — `Widget::make('SaveButton')`, `$db->runProc('Insert_Order')`
— has no edge to that target, so `find_callers` on it answers `relation_unmodelled_for_language` when
another language names it as an unlinked callee or a literal argument, else zero (409).
A `keyed_calls` rule models it: every call to `setter` whose argument `key_arg` is a string literal
gets a HEURISTIC `CALLS` edge (or the rule's `kind`) to `target_template` with `{key}` replaced by
the literal. Hits carry `rule: true`. The key is read from the edge (`arg_strings`, contract 16), so
a wrapped call and two calls on a line each name theirs; where the field is absent (SQL, whose
scanner masks literals) the call's first line is read, as before (398).

```json
{"keyed_calls": [
  {"setter": "make",    "key_arg": 1, "target_template": "\\App\\Widgets\\{key}::render"},
  {"setter": "runProc", "key_arg": 1, "target_template": "dbo.{key}"}
]}
```

- **`setter`** is an exact callee qname, or a bare method name matching any `::<name>`.
- **A key passed by name (398).** `key_kw: "table"` reads the keyword argument `table` (PHP 8 named
  arguments, Python keywords) before `key_arg`, which it makes optional; a call that passes the
  keyword is never read positionally.
- **A key inside a literal (361).** `key_pattern` is a Python regex searched in the string key: its
  named groups fill same-named placeholders (`"module=(?P<module>\\w+)&action=(?P<action>\\w+)"` →
  `"\\App\\{module}Controller::{action}Action"`), else group 1 fills `{key}`. A literal it does not
  match is no route — no edge, not counted. A pattern without groups fills `{key}` with the whole match;
  `key_pattern` is refused with any `key_from` but `"string"`.
  `key_from: "object"` reads an object/array literal argument's top-level fields that are one
  string each (`{module: 'Items', action: 'x'}`); every placeholder, `{key}` included, names a field.
  A nested, concatenated, shorthand, template or double-quoted `$` value names nothing, as does a
  repeated field; a spread voids the whole literal. A placeholder no field fills yields nothing, and
  an object key is still read from the call's first line only.
- **A list of keys (406).** `key_from: "list"` reads a `[…]` / `array(…)` argument: each top-level
  entry that is one string literal is a key (`loadScripts(['js/x.js'])` → `"public/{key}"`, a File).
  A variable, a concatenation or a keyed entry names nothing; read from the call's first line, so a
  list split over lines names nothing and counts in `keys_unread`.
- **A reference in a file's text (406).** `template_refs` entries are not calls: `files` (globs over
  the repo-relative path, `*` crossing `/`) picks indexed files, and every match of `pattern` is a
  `HEURISTIC` edge (`kind` `CALLS` or `REFERENCES`) from the file's File node at its line. Its named
  groups fill `target_template`, with `{path}` and the groups of `context_pattern`, which must take
  one value in the file — none or two, and the file's matches link nothing:
  `{"files": ["views/*.php"], "context_pattern": "ng-controller=\"(?P<ctrl>\\w+) as ctrl\"",
  "pattern": "(?<![\\w$.])ctrl\\.(?P<member>\\w+)\\(", "target_template": "{path}::{ctrl}::{member}"}`.
  A match that links nothing counts in `rule_keys_unresolved`. The whole file is searched, script
  included, and only a file an adapter indexes is read.
- **A table named by a string (364).** `kind: "WRITES"` or `"DELETES"` emits that edge instead of a
  `CALLS`, onto the `Table` the template spells (`"dbo.{key}"` — a `::` member is refused): a writer
  with no column list, so `check_column_defaults` reads it as unmeasured. A `WRITES` key links
  case-insensitively like any writer (215); a `DELETES` key must spell the stored qname, and a miss of
  either kind is counted in `rule_keys_unresolved` (a key naming a member writes nothing, and is
  counted too). `path_prefix` places the rule row at its source's file. **Limit:** an exact key
  links whatever symbol holds that qname — a key spelling a proc lists the caller as its writer.
- **`target_template`** must spell the **stored** qname — a PHP class carries its leading `\`, a SQL
  proc its schema — and may name a File (256). Several rules may share a setter; a literal links
  under whichever one names a real symbol.
- **Nothing is invented:** only an argument that is one whole literal names a key — a variable or a
  concatenation emits nothing. A literal that names no indexed symbol stays unlinked. The build
  report counts three misses: `rule_keys_unresolved` (call sites and text matches linked under no rule),
  `rules_unresolved` (rules that linked nothing at all) and, per rule, `keys_unread` (a string
  literal where the key is, yet no key read — an interpolated `"x$v"`, or one over 256 characters);
  `get_index_status` (standard) repeats `keys_unread`.
- **A route a front controller dispatches at run time (385).** `routes` declares URL → handler as
  data — inline `table` rows `{key, target}`, or a `tsv` census used as is through `columns`
  (`{"key": "url", "target": "handler"}`). `significant` names the query keys that decide a route;
  the rest, and their order, are noise, and `*` is a glob over the sorted `path?k=v&…` key, so it
  can span a `&` when the significant keys are not the last. A target is a stored qname or a
  File. The build stores the table in the index (no node, no edge) and
  counts rows naming nothing indexed in `routes_unresolved`. `trace_capability(route=…)`,
  `impact(routes=[…])` and `search_symbol` read it; with no `routes` block — or an index built before
  the block — they answer `capability_not_configured`. A key is case-sensitive and percent-decoded,
  its fragment dropped; any string (a CLI command, a message type) works as a path-only key.
  `significant_by_path` (`{"/x.php": ["cmd"]}`) gives a path its own keys in place of the block's
  (411). Rows of one canonical key with different targets are all stored, and a URL reaching that
  key — or the first matching pattern's — answers every target, never one handler; the trace is
  one build seeded at every target, under its usual caps. When each row carries its own `when`
  label (`region=A`, `flag=ON`) and optional `source` (`file:line`) — inline fields, or `columns`
  entries for a TSV or JSON census — the key is a **conditional route**: each flow and route row
  carries its `when`/`source`, labels nothing evaluates (415). One row without a label (a blank
  cell is none), or two sharing one, makes the key a **collision**, flagged
  `ambiguity: "route_collision"` with `route_candidates` (up to 20; `route_candidates_total` when
  cut), each URL judged on its own key; a TSV label column the file lacks fails the build. A
  repeated key and target is a `duplicate` — an unlabelled row beside a labelled one of the same
  target too; a dead-target row is counted, not stored — even when an earlier row routed its key —
  so its URL answers `no_such_symbol`. `get_index_status` balances the table under `routes`:
  `declared` = `stored` + the `dropped` counts (`unresolved`, `short_name_tie`, `duplicate`,
  `incomplete` — a census row missing its key or target), with up to 20 `dropped_examples` per
  reason, `collisions`, `collision_examples` (20 routes each, with `routes_total`) and
  `conditional` (keys). Only those three tools read routes — the map,
  `find_callers`, `explain_path` and `reachable_from` do not — and only the hop into the target is
  `HEURISTIC` + `rule: true`; later hops carry their own tiers.
  **A JSON census (397).** `json` names a file, `rows` a dotted path to its list of objects (absent:
  the file is the list) and `columns` the key and target fields, dotted for a nested one; a row
  missing either is skipped, and the file is digested like a TSV (396). Its targets may name a
  short class — `Class::method()` or `Class::method` — which links when exactly one stored class of
  that last name declares the member. Several: `prefer` (qname segments, tried in order, each that
  matches any candidate narrowing the set) picks the one left, else the row counts in
  `routes_unresolved` and `get_index_status` lists it under `routes_ambiguous` with its candidates
  (first 20, `routes_ambiguous_count` beside). TSV and inline rows resolve exactly as before.

  ```json
  {"routes": {"significant": ["module", "action"], "tsv": "docs/routes.tsv",
              "columns": {"key": "url", "target": "handler"}}}
  {"routes": {"significant": ["module", "action"], "json": "docs/endpoints.json",
              "rows": "endpoints", "columns": {"key": "url", "target": "handler"},
              "prefer": ["Main"]}}
  ```
- **Records written about code (407).** `records` attaches a consumer's own records — a QA ticket,
  an incident, an ADR — to the symbols they name. `sources` are repo-relative globs of JSON files,
  each holding one record or a list, or JSON Lines (`.jsonl`/`.ndjson`, a record per line, a bad line
  skipped alone), read straight off disk (an untracked or gitignored export
  counts). `fields` maps `id`, `title`, `url` (a list serves its first link), `kind` to dotted paths and `targets` to a list of
  them (strings or lists of strings, concatenated); `kind` sets one for every record. A target is a
  stored qname, an indexed file, or the one `Table` whose qname matches ignoring case; every
  definition of a qname carries it. `find_references`, `read_symbol` and `impact` list the attached
  records (`HEURISTIC`, `rule: true`; `impact` names each one's first carrier, a file record
  under a path or row file) and nothing else reads them. In `impact` a record on a seed, a
  member a seed contains or a seed's file is `direct` (`distance` 0) and leads — a path seed's
  file is that path alone, and a `Namespace` another file also declares is no path's seed (416);
  the rest follow by `distance`, symbols before files. `stop_at` (globs, fnmatch, `*` crossing `/`) names hub files
  whose records reach no answer seeded elsewhere — counted in `records_stopped` — while their own
  `impact` lists them (412). Direct rows come seeds, paths, a seed's files, then members; every
  `read_symbol` and `find_references` row is the subject's own, so `direct` at `distance` 0. The build result and
  `get_index_status` carry `records`: `files` (the globs' matches), `declared`, `untargeted` (no
  target read — a field map naming the wrong key), `attached`, `attachments`, `dangling` (a target
  naming nothing indexed, never attached) with `dangling_first` (10 `{id, target}`), `excluded`,
  `skipped` (an unreadable file, a record with no id, a repeated id — the first by path wins).
  `attributes` names further dotted paths (`["tier", "region"]`) whose values — a string, number,
  boolean or a list of up to 20 of them, a string at most 200 characters; anything else is
  dropped, never cut — ride on a record row as `attributes`,
  keyed by the path as written, omitted when the record holds none of them (413). `records_filter` on `read_symbol`, `find_references` and
  `impact` (`{"tier": ["A", "B"]}`) keeps a record whose attribute equals a value (a list attribute:
  any element; a record without the attribute never matches), before `records_total` counts; a path
  no block declares, or a value no attribute holds, is refused (`ValueError`) before any answer.
  `exclude` names a file of ids, one per line (`#` starts a comment, inline too): they are dropped before anything else
  reads them, so only their count is served — and a missing file fails the build rather than serve
  them. The files join the rules digest, so an edit reads `rules_stale` until the next refresh.

  ```json
  {"records": {"sources": ["docs/qa/*.json"], "kind": "ticket", "exclude": "docs/qa/.exclude",
               "fields": {"id": "key", "title": "summary", "targets": ["code.symbols", "code.tables"]}}}
  ```
- **Which definition answers (414).** `definitions` declares `precedence`: path globs (fnmatch,
  `*` crossing `/`), most authoritative first. For a qname with several production definitions, the
  first glob any of them matches decides — one match answers `read_symbol` and leads `search_symbol`
  with `ambiguity: "definition_precedence"`, the rest under `ambiguous_definitions`; `impact` and
  `impact_modules` walk a named qname with its seed placed at it, the rest under
  `other_definitions` — the walk is the qname's, so it spans every definition's edges (a seed a path
  expanded into keeps its file); two matches stay `subject_ambiguous`. A glob may carry one `<n>`, a
  `1`, `1.5` or `2_0_1` version read from the path: among that glob's matches the highest version
  answers, and a tie (`V2` and `V2.0`) answers nothing (437). The toml's `definition_order` takes the
  same globs and is read first. Test copies (394) are settled
  first, migration versions (403) after; a cut search page applies neither. Several rules files
  join their globs in file-name order. References target the
  qname, so they already span every definition — and `impact` walks call and type edges, not
  `READS`/`WRITES`: a table's readers and writers are `find_references`' answer.

  ```json
  {"definitions": {"precedence": ["db/schema/**", "db/migrations/*"]}}
  ```
- **Rules age with the index (396).** A build stores the digest of its rule files and any routes
  TSV. When the files on disk differ — edited, removed, or the knob turned off — `get_index_status`
  reports `rules_stale: true` with `rules_digest` (`built` / `current`; `rules_error` when a file no
  longer loads) and its summary says so. `find_view_data`, the rule hits of `find_callers` /
  `find_references`, `trace_capability(route=…)` and `impact(routes=[…])` then answer `rules_stale`
  for `ok`, rows kept; a route side-field (`search_symbol`, `impact` on a path) only carries the flag.
  The next incremental re-applies the rules without a parse (`wrote.rules_reapplied: true`); an index
  built before 396 reads stale under rules until then.
- `aliases`, `calls` and `view_data` entries share the file; PLAN §11 holds their limits.

The adapter command is the **whole** command: the core appends nothing to it, not even `--server`, so
it never has to know where a language's adapter lives. An adapter announces its own name, the file
suffixes it owns, and its capabilities on the first line it writes — that handshake is what routes
files to it.

Files are skipped using built-in patterns (`vendor/ var/ uploads/ log/ node_modules/ .git/
*.blade.*`), then `.gitignore`, then an optional `.codeatlasignore` — later rules win, so
`.codeatlasignore` can re-include what an earlier source excluded. A path below an excluded
*directory* stays excluded, which is what lets the walk prune a subtree.

### Architecture rule files

`CA_ARCHITECTURE_RULES` names JSON files of `{"rules": [...]}`; each rule has an `id` and one of two
modes. A rule's `status` reads `rule_matched_no_files` when one side matched nothing — nothing was
checked, which is not a pass.

```json
{"rules": [
  {"id": "domain-stays-pure", "sources": ["domain/**"], "forbidden": ["http/**"]},
  {"id": "writes-check-access", "sources": ["handlers/**"], "kind": "Method", "name": "^save",
   "required": ["\\Guard\\Access::check"], "kinds": ["CALLS"], "depth": 2,
   "expect": {"violating": ["\\H::legacySave"], "passing": ["\\H::saveOrder"]}}
]}
```

- **`forbidden`** (138): a RESOLVED walk from a `sources` file into a `forbidden` file is a confirmed
  violation; `kinds`, `direction` and `transitive` shape the walk.
- **`required`** (359): every symbol in a `sources` file — narrowed by node `kind` and a `name` regex
  — must reach one of the `required` qnames within `depth` hops of `kinds` edges. Only RESOLVED
  edges count as reaching; a source that reaches none is **confirmed** only when every edge the walk
  met was RESOLVED, else a **candidate** with `unresolved_outgoing` (edges met that were unlinked,
  HEURISTIC or DYNAMIC). No `kind` means every node in the files; a source that is itself a target
  passes; a required qname the index lacks is named in `targets_missing`.
  Reaching a target is a pass even if the walk also met an unresolved edge on the way.
- **`expect`** calibrates a required rule with qnames known to violate or pass; one it misses names
  itself in `expected_missed` and the rule reads `calibration_failed`, rows still returned. Only a
  **confirmed** row meets a `violating` entry, and a candidate or an unmatched qname misses a
  `passing` one. A rule that matched no source or target reads `rule_matched_no_files` first.

### Optional LLM enrichment (opt-in, off by default)

The onboarding tools are fully deterministic by default — no LLM, no network. An opt-in package,
[`onboarding_llm/`](../onboarding_llm/README.md), plugs into three seams: it can replace the one-line
module summary (085), rename weak architectural layers — the generic `source`/`sink`/`mixed` bands
084 falls back to on flat namespaces (091) — and write the map's prose (117): each layer's
responsibility line, each tour step's narrative, and the wording of the headline facts.

**Structure is never the seam's to change.** Every count, ranking, grouping and the set of headline
facts is derived before a model is consulted, so enrichment rewords the map and nothing more; a
failure or a filler answer simply leaves the deterministic sentence in place.

**What each seam costs per build**, because the two are bounded differently and a single figure for
"enrichment" was wrong:

| seam | calls per build | bound by |
|---|---|---|
| prose (117) | at most **45** whatever the repo's size | a per-slot ceiling: 6 headline · 12 layer · 15 step · 12 module |
| layer names (091) | one, and only when the layer method is a weak fallback | the layer table, not the repo |
| module summaries (085) | **one call per tour module** — uncapped by the seam | `CA_IMPACT_MAX_NODES` (default 500), which sizes the tour |

So the summarizer is the expensive one: it scales with the tour budget while prose does not. Narrow
it with `CA_IMPACT_MAX_NODES` or `CA_WORKING_ROOTS` before turning it on over a large repo.

The **core never imports it**: you install the `llm` extra, set `CA_ONBOARDING_SUMMARIZER=llm`,
`CA_ONBOARDING_LAYER_REFINER=llm` and/or `CA_ONBOARDING_PROSE=llm`, and run `code-atlas-llm` instead
of `code-atlas`. All three are memoised in content-hash caches so runs replay and diffs stay stable.
These are `onboarding_llm` knobs, not core config — the full table is in that package's README.

**`audience` and `detail_level` are different knobs, and this is the decision (210).**
`detail_level` means the same thing on every tool that takes it — how much of the **response** to return — and the
response is read once and dropped. Growing it to reshape the committed tree would make files a repo
checks into git depend on a per-call argument, so it **stays a payload knob and is unchanged**.
`audience` is the artifact knob: it selects which sections `overview.md` holds and which documents
are written at all, and the tree states which audience produced it, in `overview.md`'s *Who this was
written for* section and in `manifest.json`. Each audience is a written content contract — the
sections it gets **and why that reader needs each one** — held in one place, `onboarding/audience.py`,
which the markdown, the dataset and the viewer all read rather than re-deriving.

**What a newcomer asks first** is answered above the aggregates, in `overview.md`'s *Start here*
section: what the repo says it is, how to run its tests, its declared commands, services, ports and
runtime — each one quoted from a declared project file and carrying the `path:line` it came from,
and each one the repo does **not** declare stated as an explicit gap rather than left silent. The
graph never sees these files; the section is I/O over the repo, not inference (207). The answers reach `dataset.json` under
`orientation`; the tool payload carries none of them — read the committed `overview.md` (207).

**Which one wrote the tree you are reading** is recorded in the artifact itself: `overview.md` ends
with a *How this was written* section and `manifest.json` carries the same three names under
`provenance`, so an empty summary is attributable to the run rather than read as a fact about the
repo (209).
