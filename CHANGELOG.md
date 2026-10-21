# Changelog

One entry per release, newest first. Each heading names the release, its date, and the contract and
schema versions it ships. `tests/test_release_discipline.py` reads the top heading. A change to
`CONTRACT_VERSION` or `SCHEMA_VERSION` therefore needs a new release, and the first test run says so.

Each entry flags the two costs an upgrade can carry:

- **Full rebuild required.** The index's contract or schema moved. Run `code-atlas-build --full`.
  Until then `get_index_status` leads with `rebuild required`.
- **Adapter checkout must be updated.** The adapters speak the new contract. Pull the checkout that
  `CA_<LANG>_CMD` points into, and reinstall its dependencies. An older adapter fails the handshake.

How to upgrade each install route is in the README, under *Upgrading*.

## Unreleased

Commits after the newest tag; not a release until a version and a `vX.Y.Z` tag are cut (381).

- A `records` block in the rule file attaches a consumer's records — a QA ticket, an incident — to
  the symbols they name: `find_references`, `read_symbol` and `impact` list them, and the build and
  `get_index_status` report dangling targets and how many ids the block's exclusion list kept off.
  Sources are JSON or JSON Lines and may be gitignored exports; an edit reads `rules_stale` until the next refresh (407).

## 0.7.0 — 2026-10-19 · contract 18 · schema 9

- **Full rebuild required.** Run `code-atlas-build --full`: a PHP view's `<script>` becomes symbols.
- **Adapter checkout must be updated.** Every adapter speaks contract 18.
- A function or member in a `.php` / `.phtml` view's inline `<script>` is a symbol of the view at its
  own line: `file_outline`, `search_symbol` and `read_symbol` find it. The PHP adapter names each
  classic or module script's bytes (PHP inside it is skipped); the JS adapter reads them. A
  `text/ng-template` or other data block, and a `<script src>`'s content, are not code (399).
- A script's calls link in JavaScript and a PHP call never links to a script's function: a row from a
  region keeps its own language (schema 9). A view whose script no adapter read says so on its file,
  as `embedded_unread`.

## 0.6.0 — 2026-10-19 · contract 17 · schema 8

- **Full rebuild required.** Run `code-atlas-build --full`: a T-SQL view becomes a `View` node.
- **Adapter checkout must be updated.** Every adapter speaks contract 17.
- A T-SQL view (`CREATE`, `ALTER`, `CREATE OR ALTER VIEW`) is a `View` node: `search_symbol` finds
  it, `read_symbol` returns its definition, its `FROM` / `JOIN` sources are `READS` from the view
  rather than from its file, and a migration that redefines it is in its `altered_by` (402).
- `read_symbol` on a routine or view that several Flyway versioned migrations (`V7__x.sql`) redefine
  answers the highest version and lists the others, instead of refusing as `subject_ambiguous`; two
  unversioned definitions still refuse. The SQL adapter stamps `extra.migration_version` (403).
- `search_symbol` for a PHP property's bare name (`isInRespite`) ranks `C::$isInRespite` as an exact
  match, as `$isInRespite` already did, and a two-letter `id` finds `$id`. The stored name is unchanged (404).
- An answer read while an incremental build runs is the previous graph's, never a half-linked one:
  the build writes in one transaction, so a caller in a re-parsed file is no longer missing until the
  resolve, and a killed incremental leaves the index as it was. A call served meanwhile skips its fit
  and cost counts instead of waiting 5 s on each, and the poke hook skips its repair (400).
- A refresh hook that is refused (an adapter failing its handshake, for one) or errors no longer
  goes only to a log: `get_index_status` names it as `refresh_refused`, with the time and the fix,
  and the session-start line shows it on screen, until a build succeeds (401).
- The plugin says when a newer tagged release is out, even with marketplace auto-update off: a
  background hook caches the newest `vX.Y.Z` tag daily, and the next session start names it on
  screen. New console script `code-atlas-release-check`; `CA_RELEASE_CHECK=0` turns it off (405).
  Tags `v0.3.0`, `v0.4.0` and `v0.5.0` are now cut.

## 0.5.0 — 2026-10-17 · contract 16 · schema 8

- **Full rebuild required.** Run `code-atlas-build --full`: a call site gains `arg_strings` and
  `kwarg_strings`, the value of a plain string literal argument.
- **Adapter checkout must be updated.** Every adapter speaks contract 16.
- A `keyed_calls` string key is read from the edge, so `insertRow(\n 'Items', $row)` and two calls
  on one line link; `key_kw` names the key by keyword, and PHP 8 named arguments are read into
  `kwargs` (a named argument no longer voids `args`). Each rule counts `keys_unread` — a string
  literal where its key is, yet no key read — in the build report and `get_index_status` (398).
- A `routes` block reads a JSON census as is (`json`, `rows`, `columns`): a handler named by its
  short class (`OrderController::listAction()`) links when one class holds that name, `prefer`
  picks among same-named classes, and `get_index_status` lists the rows still ambiguous (397).
- A rule file or routes TSV edited after the build no longer answers as current: `get_index_status`
  reports `rules_stale` with both digests, rule-fed answers say `rules_stale` instead of `ok`, and
  the next incremental (the refresh hook's included) re-applies the rules without `--full` (396).
- `check_column_defaults(default_expr="user_name()")` lists every column whose `DEFAULT` is that
  expression, across tables, each with its omitters — no grep over the schema first (391).
- `$m = Factory::legacy(); $m->attach();` links when `legacy()` documents `@return Mailer` (PHP,
  `HEURISTIC`), and `find_callers` on a method counts `unresolved_receivers` (393). A file reads its
  docblocks when it next re-parses; `code-atlas-build --full` reads them all now.
- `function EditCtrl() { var self = this; self.save = function () {}; }` declares `EditCtrl::save` as
  a Method (TS/JS: members assigned on `this` or its alias inside the constructor;
  `Ctor.prototype.x =` is not read) — `search_symbol save` finds it (395).
- `find_references Items`, `impact` and `find_callers` (a procedure) answer a bare table or routine
  name a column shares, with `resolved_from: "bare"`; two schemas' tables refuse with both (392).

## 0.4.0 — 2026-10-17 · contract 15 · schema 7

- **Full rebuild required.** Run `code-atlas-build --full`: the edge vocabulary gains `READS`.
- **Adapter checkout must be updated.** Every adapter speaks contract 15.
- A table names its readers: `find_references(<table>, kinds=["READS"])` lists the routines whose
  `SELECT` reads it (`FROM` / `JOIN`, `RESOLVED`) and the PHP, TS or Python strings that begin a
  `SELECT … FROM` it (`HEURISTIC`). Without `kinds` a table still answers its writers (390).
- `read_symbol` names where else a hit's code lives: `implemented_by` (on an empty or abstract
  method, the overriding methods of linked subtypes) and `aliases` (from `ALIASES` edges, `test_double` when a test file declares
  one). A name with one production definition and test copies answers the production one, with
  `ambiguity: "test_copies"`; `search_symbol` lists it first and marks each of its rows (394).
- An agent in a worktree of the indexed repo reads that worktree: `read_symbol`, `file_outline` and
  `search_symbol` parse the files that differ from the built commit (plus untracked ones) without
  storing them, labelled `overlay: worktree`, and `find_callers` / `find_references` add the
  worktree's edges at `HEURISTIC` (`worktree_overlay`). The worktree comes from MCP `roots`, or
  `CA_CALLER_ROOT` when a client reports none; switching the main checkout changes nothing (389).
- A `behind` index with no build running answers instead of refusing: `find_callers` and
  `find_references` label an unchanged subject `index_behind` with the built revision, and a subject
  the working tree no longer declares `index_behind_subject_removed`; `search_symbol` never answers
  `index_stale` (drifted rows carry `source_stale`). Only a changed subject that cannot be re-read
  refuses, naming the exact `serve_behind=true` call. `get_index_status` lists the changed paths in
  `behind_because` and drops `behind_refuses` (388).
- An agent in a consuming repo can now find 382–385: `which_tool` and the skill route a reported
  URL to `trace_capability(route=…)`, and the agent brief and both skills name `code-atlas query`,
  `--verify-claims` and `--changed-since`. Re-run `gen_skill.py --write-agent-brief <repo>` to refresh
  a repo's `AGENTS.md` (387).
- A `routes` block in a `CA_INDIRECTION_RULES` file declares URL → handler (inline or a TSV census,
  `significant` query keys); `trace_capability(route=…)` traces from the handler, `impact` takes
  `routes` and lists the routes into its radius, `search_symbol` finds them by key, and the build
  counts `routes_unresolved`. A lookup, not graph rows: no contract change (385).
- `code-atlas query --snapshot-symbols <out>` writes every symbol's signature and body fingerprint;
  `--changed-since <snapshot> --qname Q --path P` answers per symbol `unchanged`, `body_changed`,
  `signature_changed`, `moved`, `removed`, `unknown_at_base` or `unknown`, exiting `3` unless all are
  unchanged. Every adapter stamps `extra.body_hash`; **update the adapter checkout and run
  `code-atlas-build --full`** to fingerprint every symbol — until then one answers `unknown` (384).
- A signed claim is format `code-atlas/2` and ends with `call=`, the tool's arguments;
  `code-atlas query --verify-claim '<line>'` / `--verify-claims <file>` re-run claims at the current
  index as `holds`, `changed` (naming the keys that moved) or `unverifiable`, exiting `3` when one did
  not hold. A `code-atlas/1` line is always `unverifiable` (383).
- `code-atlas query <tool> --args '<json>'` and `code-atlas query --batch <file.jsonl>` answer the
  read tools from a shell with the MCP payload, one JSON line each, from one process (382).
- A PHP, TS or Python string that runs `EXEC Proc @p` with no schema calls `dbo.Proc`, T-SQL's
  default schema; a procedure created with no schema answers to `dbo.Proc` too (386).
- The `SessionStart` hook puts a skew, a pinned tool install or a pending rebuild on the developer's
  screen (`systemMessage`) as well as the agent's context, names a uv install pinned to `?rev=`, and
  the hand hook snippet is gated like the plugin's, so committed settings leave a teammate without
  code-atlas untouched (381). **A project that merged the snippet before this must re-copy it**: the
  old one names each script bare, and a teammate without code-atlas gets exit 127 on every hook.

## 0.3.0 — 2026-10-08 · contract 14 · schema 7

- **Full rebuild required.** Run `code-atlas-build --full`: the edge table gains `kwargs`.
- **Adapter checkout must be updated.** Every adapter speaks contract 14.
- The `SessionStart` hook names every half of the install that lags the newest — tool, plugin, and
  the adapter checkout, whose contract it reads by launching each configured adapter — with each
  fix in upgrade order; `server_stale_process` now sees a package replaced after the first answer (374).
- `get_index_status(detail_level="verbose")` counts, per tool, each answer's est. tokens against an
  est. grep+Read baseline of the files it cites, in `est_tokens_vs_grep_read` — an estimate, not a
  benchmark tier (379).
- `search_symbol` answers a one-letter typo with `did_you_mean`: declared names within a small
  edit distance, nearest first, beside the token candidates and never in `results` (378).
- The grep nudge stays silent while the index is behind, building or pending a rebuild, and a
  subagent hears it once for itself instead of being silenced by its parent's session (377).
- A plugin installed before its console scripts no longer fails every hook with exit 127: the
  `SessionStart` hook names the install command once, and every hook exits 0 (376).
- `read_symbol` refuses a file that now resolves outside the repo — an indexed file swapped for a
  symlink since the build — with `path_outside_root`, no text and no graph fields; the onboarding
  docblock reads empty (375).
- A Python keyword argument is recorded in `kwargs` beside the positional `args`, and
  `find_callers` filters by one with `arg_name` + `arg_is` (372).
- A TypeScript or Python string that begins a T-SQL write or `EXEC` writes, deletes or calls
  its object, as a PHP one does; one shared table keeps the three readers in step (371).
- A Python module loaded by `run_path`, `spec_from_file_location` or `exec` of a `__file__`-relative
  path, or by a literal `import_module`, is imported; a computed load stamps its file (373).
- A TS/JS `require` built from `__dirname` plus literals imports its file; a root constant plus
  a `/…` literal links by its unique path suffix at `HEURISTIC` (370).
- A TypeScript static field and a Python class attribute read or written through their class or
  its lexical receiver are `REFERENCES` onto the member, so `find_references` lists them (369).
- A Python call on a module-level variable built by `Foo()` resolves to `Foo`'s method, as it
  already did in a function (368).
- The TypeScript and Python adapters flag their constructors too, so `find_callers` on a TS
  `constructor` or a Python `__init__`/`__new__` lists its class's construction sites; a TS
  `super(…)` now calls the base class's constructor (367). **Full rebuild required** once.
- A client whose first MCP root is another checkout of the repo at another commit than the built
  one gets `reason: ref_mismatch`, rows kept, with both commits named (366).
- While a build holds the live index, callers and references answer labelled and `read_symbol`
  parses the file unstored, instead of waiting and refusing (365).
- A `keyed_calls` rule may declare `kind: WRITES` or `DELETES` of the table its key names (364).
- `include_graph` attests a zero for a file nothing includes, and withholds it while an unlinked
  include could name the file (363).
- `find_callers` on a constructor lists its class's `new` sites (362). **Full rebuild required**
  once (`code-atlas-build --full`) for the PHP adapter's constructor flag to reach the index.
- `keyed_calls` gains `key_pattern` (a regex over a string key) and `key_from: "object"` (fields of
  an object literal) to fill the target template (361).
- A build stamps the HEAD it read before parsing, so a commit landing mid-build leaves the index
  `behind` instead of falsely `current` (360). An index built across such a move cannot be told
  apart: if `get_index_status` says `current` but a file committed then is missing, run
  `code-atlas-build --full` once.
- A refresh that finds the write lock held is no longer dropped: it leaves `write.pending`, and the
  running build serves it with one more incremental before it exits (357). A rebase's last refresh
  now lands at its HEAD.
- `check_architecture_rules` gains a `required` rule mode: every selected symbol must reach a gate
  qname within `depth` hops; a miss is confirmed only over an all-RESOLVED walk (359). The rule
  file format is documented in `docs/TOOLS.md`, *Architecture rule files*.
- CI builds the test image `docker/Dockerfile` (358).

## 0.2.0 — 2026-09-30 · contract 13 · schema 6

The first versioned release. `0.1.0` was never bumped while the contract moved from v10 to v13, so
no install could tell which code it ran.

- **Full rebuild required.** Every index built before contract v13 needs `code-atlas-build --full`.
- **Adapter checkout must be updated.** Every adapter speaks v13 (`symbol_shapes`).
- The Claude Code plugin (marketplace `cuongdinhngo/code-atlas`) ships the server, the hooks and the
  skill.
- The state hook names a plugin/package version skew and the command that closes it.
- An index from an older contract reports `rebuild required` on every channel.
- The read/write-time signal and the grep-time nudge reach the model as `additionalContext`.
