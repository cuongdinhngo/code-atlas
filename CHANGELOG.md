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

### Security

- **Python dependencies are locked and audited** (425). `uv.lock` pins every package with hashes; CI
  and both Docker images install from it, and CI and `scripts/gate.sh` run `pip-audit`,
  `npm audit --omit=dev` and `composer audit`, failing on any known vulnerability. The install floor
  moved to `fastmcp>=3.4.10,<4` and `mcp>=1.30.0,<2`, above every published advisory (SEC-MCP-09). A
  user's `uv tool install git+…@vX.Y.Z` is unchanged; it resolves the new floors.
- **The tool surface is pinned** (428). Every tool declares MCP annotations (all closed-world; queries
  read-only; `build_or_update_index` and `generate_onboarding` non-read-only and idempotent, the
  latter destructive, as it deletes its earlier pages), and every input schema is closed. Visible to a client: an unexpected tool error is
  masked to `Error calling tool '<name>'` (a deliberate `ValueError` refusal keeps its message), an
  argument is validated against the schema before the tool runs (a string for an integer is refused,
  not coerced), a free string over 4096 characters is refused, an array over 1000 items is refused,
  and `find_callers` `arg_is` is an `enum`. `records_filter` keeps taking a string, number, boolean
  or a list of up to 100 of them per key, with at most 64 keys of up to 256 characters. No parameter
  was renamed. `tool_manifest.json` pins names, descriptions and schemas; a range that changes it
  needs a line here that says "tool surface" or names a changed tool.
- **Installs and upgrades name a release tag** (427). The README, the plugin and the state hook give
  `git+…@vX.Y.Z` and `marketplace add cuongdinhngo/code-atlas#vX.Y.Z`, and the README says
  code-atlas is not the PyPI packages `code-atlas-mcp` or `codeatlas`.
- **The server refuses a mismatched plugin** (427). The plugin launches `code-atlas --expect-version`;
  a server of another release exits 2 with the reinstall command instead of warning.
- **Hooks wake on the index database** (427), not the `.code-atlas/` directory, in the plugin, the
  Codex and OpenCode snippets; one git tracks stays silent. An index moved by `CA_DB_PATH` gets no hooks.
- **The release check's `git ls-remote` runs hardened** (427), from the cache directory.
- **A source file above `CA_MAX_FILE_BYTES` is skipped, never parsed** (430). The default is 4 MiB; the
  count shows as `skipped.oversize` in `get_index_status` and the build summary. An adapter reply
  line over 64 MiB fails that file and restarts the adapter, and the adapter handshake is bounded by
  `adapter_timeout`.
- **A regex in a rules file is refused when it can backtrack catastrophically** (430): past 512
  characters, with a backreference, or with a repeat inside a repeat. The error names the rule.
- **Caps in `.code-atlas.toml` are clamped to a ceiling** (430) in `code_atlas/limits.py`; the
  environment is not clamped.
- **Stub roots and read-through repair stay inside the repo** (430), and a read that crosses the
  trust line opens with `O_NOFOLLOW`, checks the descriptor it got (on Linux and macOS, its real
  path, so a swapped parent directory is refused), and refuses a file over 64 MiB.
- **`host_root` and `container_root` in `.code-atlas.toml` need `CA_TRUST_PROJECT_FILE=1`** (430),
  like `[adapter_cmd]`; the environment variables work as before.
- **Adapters start with an allow-listed environment and git without `GIT_*`** (430): no `*_TOKEN`,
  `*_KEY`, `ANTHROPIC_*` or `GH_*` reaches an adapter. This includes the release check's fetch.
- **The onboarding cache under `.code-atlas/onboarding/` is `0700`/`0600`** (430) and refuses a link.
- **CI is pinned and least-privilege** (424). Every `uses:` is a full commit SHA with its version,
  each workflow holds `contents: read` at the top, no checkout keeps its token, and no `run:` reads an
  event expression. The tokens-to-answer ratio is now in the job summary, not a PR comment, because
  the comment needed a write token beside PR code.
- **Dependabot, CodeQL and OpenSSF Scorecard** (424): weekly updates for pip, both npm adapters,
  composer, Actions and Docker; CodeQL on Python and JavaScript/TypeScript; Scorecard to code scanning.
- **A weekly settings-drift check** (424) reads the `main` and `v*` rulesets, private reporting, secret
  scanning, push protection, Dependabot security updates, `sha_pinning_required` and the repo's admins
  against the standard's new `set:` items, and opens an issue on a difference. It needs the repository
  secret `SETTINGS_READ_TOKEN` (fine-grained, Administration: read).
- **The identity sweep reads branch and pull-request head ref names** (424), not only commits and files.
- **New guards** (424): no `eval`, `exec`, `pickle`, unsafe YAML or dynamic import under `code_atlas/`
  and `adapters/`; no committed binary outside a named allow-list; `store.py` binds every value; the
  plugin passes `claude plugin validate --strict` in CI.

### Changed

- The state hook's upgrade lines are the tagged reinstalls; the "pinned install" line is gone, as it
  told you to unpin. The README no longer advises auto-update.

## 0.9.1 — 2026-10-29 · contract 20 · schema 9

### Security

Fixes [GHSA-66g7-7jr3-j5rc](https://github.com/cuongdinhngo/code-atlas/security/advisories/GHSA-66g7-7jr3-j5rc)
(419–421): an index the indexed repo committed could pass a git option, write through a link, or
put text in the agent's instructions. Upgrade every install. No rebuild, no adapter update.

- **A committed index is now refused.** If `.code-atlas/` is tracked, untrack it
  (`git rm -r --cached .code-atlas`) and add it to `.gitignore`. In the runtime image, run with
  `--user "$(id -u):$(id -g)"` so the index stays readable to you.

### Changes

- A build refused for an adapter on another contract carries a `hint` naming the older half and its
  step (`git checkout v<release>` or reinstall the core), on the payload, the CLI line and
  `refresh_refused`. When the adapter runs from the checkout the core was installed from, the hint
  and the SessionStart line say so instead of `git pull` (418).
- Every git call runs through `gitutil._run`, hardened: no system config, no prompt, and
  `core.fsmonitor`, `core.hooksPath`, `core.sshCommand` and `diff.external` overridden; `diff` adds
  `--no-ext-diff --no-textconv`. A revision read from the index must be a full object id and follows
  `--end-of-options`; anything else is refused on stderr and the build falls back to full. git 2.24
  or newer is required (419).
- The index directory is trusted only if code-atlas wrote it. When git tracks anything under it, or
  it, the database, a `-wal`/`-shm` or the shadow is a link or resolves outside the repo, the build,
  the server, `get_index_status` and every hook refuse with the fix (`git rm -r --cached <dir>`),
  and the hooks inject nothing. Every file there is written without following a link, `0600` in a
  `0700` directory, so an index a root container creates needs `--user` to stay readable to you;
  the database opens with `trusted_schema=OFF` and defensive mode (420).
- Text read back from the index can no longer add a line to `nudge.log` or speak to the agent.
  A refusal record's reason and route must be ones code-atlas writes (else `unknown`, with its own
  hint), the coverage-loss clause names only shipped or configured languages, and the
  `get_index_status` summary — the server instructions and the SessionStart line — is scrubbed of
  control, bidi and ANSI characters and capped at 1,024 characters (421).

## 0.9.0 — 2026-10-26 · contract 20 · schema 9

- **Full rebuild required.** Run `code-atlas-build --full`: a pre-0.9.0 index kept one handler per
  route key and none of the rule file's new blocks, so its answers would read as complete.
- **Adapter checkout must be updated.** Every adapter speaks contract 20.
- Route rows sharing a key are all stored, and a URL reaching that key answers every target, flagged
  `ambiguity: "route_collision"` with `route_candidates`. `get_index_status` balances the table
  under `routes`: `declared` = `stored` + `dropped` by reason (`unresolved`, `short_name_tie`,
  `duplicate`, `incomplete`), with examples, `collisions` and `conditional`. `significant_by_path`
  gives a path its own significant keys (411).
- `impact` lists the subject's own records first, each with `distance` and `direct`;
  `records: "direct"` returns those alone and `records_limit` pages them. A records block's
  `stop_at` names hub files whose records reach no other answer, counted in `records_stopped` (412).
- A records block's `attributes` ride on every record row, and `records_filter` on `read_symbol`,
  `find_references` and `impact` keeps the records whose attribute matches. A path no block
  declares, or a value no attribute holds, is refused (413).
- A rules file's `definitions.precedence` (path globs, most authoritative first) names which of a
  qname's definitions answers: `read_symbol` reads it, `search_symbol` leads with it under
  `ambiguity: "definition_precedence"`, and `impact` / `impact_modules` walk the qname with the rest
  under `other_definitions` (414).
- Rows of one route key that each carry a `when` label (and optional `source`) are a conditional
  route: one flow per handler, each with its `when`/`source`. A TSV label column the file lacks
  fails the build (415).
- `impact(paths=[…])` seeds only the symbols the file defines: a `Namespace` another file also
  declares is no path's seed, so that file's records never read `direct` (416).

## 0.8.0 — 2026-10-24 · contract 19 · schema 9

- **Full rebuild required.** Run `code-atlas-build --full`: a statement now names the columns it reads.
- **Adapter checkout must be updated.** Every adapter speaks contract 19.
- `find_references(<Table::Column>, kinds=["READS"])` lists who reads a column: a T-SQL routine or
  view naming it as `alias.col`, or bare beside its one source (`RESOLVED`), and a host string's
  `SELECT … FROM t` doing the same (`HEURISTIC`). A table's readers that named none of its columns —
  a `select *`, say — are counted in `column_reads_unknown`; a bare name beside several sources, or
  through a CTE, binds to none. A column read links case-insensitively, as T-SQL resolves it; an
  ORDER BY alias, a CONVERT type or a collation is never a column. A table's own `READS` row lists
  `columns` (410).
- `read_symbol`, `file_outline`, `search_symbol`, `find_callers` and `find_references` take
  `caller_root`: a subagent in a worktree, sharing its parent's roots, names that worktree for the
  call and is answered from it rather than the main checkout. A path outside this repository is
  refused; the skill and agent brief say when to pass it (408).
- An empty `find_callers` on a multi-language index answers `relation_unmodelled_for_language` only
  when another language names the subject — as a callee or as a literal argument, `querySP('name')`.
  Otherwise it is `no_matches`, with the unreached languages in `cross_language_unmeasured` (409).
- A `records` block in the rule file attaches a consumer's records — a QA ticket, an incident — to
  the symbols they name: `find_references`, `read_symbol` and `impact` list them, and the build and
  `get_index_status` report dangling targets and how many ids the block's exclusion list kept off.
  Sources are JSON or JSON Lines and may be gitignored exports; an edit reads `rules_stale` until
  the next refresh (407).
- A rule file's `template_refs` reads references from file text, not from a call: a regex's named
  groups, plus a `context_pattern` found once per file and `{path}`, fill a target. So
  `ng-click="ctrl.save()"` under `ng-controller="EditCtrl as ctrl"` makes the view a `HEURISTIC`
  caller of `EditCtrl::save`, and a reference naming nothing counts in `rule_keys_unresolved` (406).
- `keyed_calls` takes `key_from: "list"`: each one-string entry of `loadScripts(['js/x.js'])` names
  its target, such as the asset's File (406).

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
