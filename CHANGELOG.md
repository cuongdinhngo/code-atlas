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

## 0.3.0 — 2026-10-08 · contract 14 · schema 7

- **Full rebuild required.** Run `code-atlas-build --full`: the edge table gains `kwargs`.
- **Adapter checkout must be updated.** Every adapter speaks contract 14.
- The `SessionStart` hook names every half of the install that lags the newest — tool, plugin, and
  the adapter checkout, whose contract it reads by launching each configured adapter — with each
  fix in upgrade order; `server_stale_process` now sees a package replaced after the first answer (374).
- The grep nudge stays silent while the index is behind, building or pending a rebuild, and a
  subagent hears it once for itself instead of being silenced by its parent's session (377).
- A plugin installed before its console scripts no longer fails every hook with exit 127: the
  `SessionStart` hook names the install command once, and every hook exits 0 (376).
- `read_symbol` and the onboarding docblock read refuse a file that now resolves outside the repo — an
  indexed file swapped for a symlink since the build — with `path_outside_root` and no text (375).
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
