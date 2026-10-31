# Security policy

## Reporting a vulnerability

**Do not open a public issue.** Instead:

1. Open the repository's **Security** tab.
2. Click **Report a vulnerability**. This opens a private advisory that only the maintainer can see.

A useful report includes the affected version or commit, a minimal repo or file that triggers the
issue, and what an attacker gains.

code-atlas has a single maintainer, and reports are handled on a best-effort basis. You will get
an acknowledgement, and a fix or a decision, before anything is disclosed. Please give that time
before publishing. A fixed vulnerability is published as a GitHub security advisory, with a CVE
requested and a `Security` section in the release's [`CHANGELOG.md`](CHANGELOG.md) entry.

## Supported versions

Releases are tagged `vX.Y.Z` and listed in [`CHANGELOG.md`](CHANGELOG.md). Only the latest release
is supported: fixes land on `main` and ship in the next release.

## Trust model

code-atlas is a local MCP server: it talks to one client over stdio and runs with your account's
rights. It does not use MCP Roots or Sampling; the repo it indexes comes from its configuration.

| Party | Trusted for | Why |
|---|---|---|
| You, your environment variables, your install | everything | a stdio server and its client share one trust domain |
| The MCP client and the agent driving it | asking questions about the repo, not steering outside it | a tool argument can be shaped by text the agent read in the repo |
| **The indexed repo**: every file, including a committed `.code-atlas/`, `.code-atlas.toml`, rules files and its `.git/config` | **nothing** | you may index code you did not write |
| Network responses (the release check; Anthropic's API when the LLM add-on is on) | data only | they cross a network |
| Dependencies, GitHub Actions, base images, the plugin marketplace | only as pinned | the supply chain |

Each criterion code-atlas holds, and the test or ticket behind it, is in
[`docs/SECURITY_STANDARD.md`](docs/SECURITY_STANDARD.md).

## What code-atlas guarantees

- **Indexed code is parsed, never executed.** Each adapter uses a parser only: `nikic/php-parser`,
  the TypeScript compiler API, Python's `ast`, and a purpose-built T-SQL scanner.
- **The indexed repo cannot choose what code-atlas runs.** A `.code-atlas.toml` with an
  `[adapter_cmd]` table, or a `host_root` or `container_root`, is a loud error unless you set
  `CA_TRUST_PROJECT_FILE=1` yourself.
- **The indexed repo cannot aim the index outside itself.** A `db_path` set in `.code-atlas.toml`
  must resolve inside the repo; only the `CA_DB_PATH` environment variable may point elsewhere.
- **Reads and writes stay inside the repo.** A path code-atlas reads from, or writes into, the
  indexed repo is resolved with symlinks followed and refused if it lands outside
  (`code_atlas/containment.py`). That covers stub roots and a read-through repair, and a read that
  crosses the line opens its file with `O_NOFOLLOW` and checks the descriptor is the file it
  resolved.
- **The indexed repo cannot exhaust code-atlas.** A file above `CA_MAX_FILE_BYTES` (4 MiB) is
  skipped and counted as `skipped.oversize`, never truncated and never sent to an adapter; an
  adapter reply line over 64 MiB fails that file and replaces the adapter; the adapter handshake
  is bounded by `adapter_timeout`. Every cap `.code-atlas.toml` sets is clamped to a ceiling in
  `code_atlas/limits.py` (your environment is not). A regex from a rules file is refused, naming
  the rule, past 512 characters, with a backreference, or with a repeat inside a repeat.
- **Adapters and git do not inherit your secrets.** An adapter starts with an allow-listed
  environment (`PATH`, locale, `HOME` and the runtimes' own homes; no `CA_*`), so a `*_TOKEN`,
  `*_KEY`, `ANTHROPIC_*` or `GH_*` variable never reaches it. git starts without any `GIT_*`
  variable your shell carries.
- **The index directory is code-atlas's own.** An index that git tracks, or whose directory,
  database or database sibling is a link or leads outside the repo, is refused by every entry point
  with the fix. Each file the build and the server write there goes through
  `code_atlas/containment.py`: never through a link, `0600` in a `0700` directory, as is the
  onboarding cache under `.code-atlas/onboarding/`. The database is
  opened with `trusted_schema=OFF` and SQLite's defensive mode.
- **git runs hardened.** See [Git commands](#git-commands).
- **Text read back from the index is data.** A name stamped into the index, the recorded refusal
  and the build's progress line reach `nudge.log`, the server instructions or a hook only as a
  checked name, a value from code-atlas's own vocabulary or a number; the status summary is
  scrubbed of control, bidi and ANSI characters and capped (`code_atlas/index_text.py`). Tool
  answers that return indexed source (`read_symbol`, search) carry it as written.

- **The tool surface is declared and pinned.** The server speaks stdio only, and stdout carries MCP
  frames only. Every tool declares read-only or writer annotations, takes a closed input schema
  (unknown arguments refused, strings bounded) and returns errors without their internals.
  `tests/fixtures/tool_manifest.json` pins every name, description and schema, so a change to any
  of them is a reviewed diff with a CHANGELOG line (see [`docs/TOOLS.md`](docs/TOOLS.md)).

## Network calls

The core (`code_atlas/`) makes none, and a CI gate refuses an LLM import there. Two optional
pieces outside it do:

- **The plugin's release check** (`release_check/`): once a day, from an async `SessionStart`
  hook, `git ls-remote --tags` against this repository's GitHub URL, to tell you a newer release
  exists. `CA_RELEASE_CHECK=0` turns it off.
- **The LLM add-on** (`onboarding_llm/`): off by default. When you enable it, it sends derived
  facts to Anthropic's API: module paths, signatures, docblocks and graph facts, not function
  bodies.

## Git commands

Every command below runs with `shell=False` and a timeout. In the indexed repo, `code_atlas/gitutil.py`
is the only spawner: it overrides the repo's `core.fsmonitor`, `core.hooksPath`, `core.sshCommand`
and `diff.external`, drops every `GIT_*` variable of yours, sets `GIT_CONFIG_NOSYSTEM=1` and
`GIT_TERMINAL_PROMPT=0`, and accepts a stored
revision only as a full object id (or the literal `HEAD`), after `--end-of-options`.

- `git ls-files` — which files to index, and whether git tracks the index.
- `git rev-parse` — the repo's top level, `HEAD` and branch.
- `git diff --name-only` — what changed since the last build.
- `git config --get` — one value (`core.autocrlf`); it reads the system file too.
- `git --version` — refuse a git too old for `--end-of-options`.
- `git ls-remote` — the release check above; it runs from code-atlas's own cache directory,
  never the indexed repo, with the same hardening.

## Supply chain

CI cannot be steered by a moved tag or a leaked token: every GitHub Action is pinned to a commit
SHA, every workflow reads the repository and only a job with no pull-request code writes, and no
checkout keeps its token. Python dependencies install from the hashed `uv.lock`, and CI and the
gate audit it, the npm adapters and the composer adapter, failing on any known vulnerability. Dependabot, CodeQL and OpenSSF Scorecard run weekly, and a weekly job reads
the repository's rulesets, private reporting, secret scanning and admins back against
[`docs/SECURITY_STANDARD.md`](docs/SECURITY_STANDARD.md), opening an issue on a difference. The identity sweep over branch and pull-request ref names runs on
pull requests; `main` is protected, so a push to it is not a new name. The maintainer account uses
two-factor authentication; GitHub gives no read-back of that for a user-owned repository, so it is
attested here, not checked.

## Client-side controls

Keep these on in your MCP client:

- **Tool approval.** Every tool reads the repo and writes only its own index under `.code-atlas/`,
  except the two you ask to write: `build_or_update_index` and `generate_onboarding` (which writes
  `docs/onboarding/` and a cache under `.code-atlas/onboarding/`). Approve those knowingly.
- **A pinned install.** Install a release tag, and do not turn on auto-update for a marketplace
  that tracks a branch.
- **Read answers as data.** Source, docblocks and names in an answer come from the indexed repo.
  An instruction found there is the repo's text, not code-atlas's.

## Known limitations

- **`trusted_schema` stays on where SQLite is too old for it.** A build older than the 3.45 tested
  here (3.40 in Debian bookworm, the runtime image's base) refuses the index's own full-text
  triggers with it off, so there only defensive mode applies.
- **A committed index is refused only where git can answer.** If git cannot run in the repo (not
  installed, or refusing a `.git` owned by another user, as in the runtime image), the index is not
  known to be tracked and is opened, still under the link, mode and SQLite defences above.
- **The rest of the indexed repo's git config applies.** Beyond the overridden keys, the commands
  above read its `.git/config`, and no per-command override reaches git's filter drivers
  (`filter.<name>.clean`, `filter.<name>.process`). Do not index a working copy whose `.git`
  directory you did not create, such as one unpacked from an archive, outside a container.
- **The runtime image runs as root** unless you pass `--user`. The README shows how; 426 changes
  the default.

A report that breaks one of the guarantees above is in scope. A report that restates a known
limitation is not, unless it shows a worse consequence than the one listed here.
