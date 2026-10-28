# Security policy

## Reporting a vulnerability

**Do not open a public issue.** Instead:

1. Open the repository's **Security** tab.
2. Click **Report a vulnerability**. This opens a private advisory that only the maintainer can see.

A useful report includes the affected version or commit, a minimal repo or file that triggers the
issue, and what an attacker gains.

code-atlas has a single maintainer, and reports are handled on a best-effort basis. You will get
an acknowledgement, and a fix or a decision, before anything is disclosed. Please give that time
before publishing.

## Supported versions

Releases are tagged `vX.Y.Z` and listed in [`CHANGELOG.md`](CHANGELOG.md). Only the latest release
is supported: fixes land on `main` and ship in the next release.

## Threat model

code-atlas indexes repositories you may not have written, so **the indexed repo is treated as
untrusted input**. It aims to hold these guarantees:

- **Indexed code is parsed, never executed.** Each adapter uses a parser only: `nikic/php-parser`,
  the TypeScript compiler API, Python's `ast`, and a purpose-built T-SQL scanner.
- **The indexed repo cannot choose what code-atlas runs.** A `.code-atlas.toml` with an
  `[adapter_cmd]` table is a loud error unless you set `CA_TRUST_PROJECT_FILE=1` yourself.
- **The indexed repo cannot aim the index outside itself.** A `db_path` set in `.code-atlas.toml`
  must resolve inside the repo; only the `CA_DB_PATH` environment variable may point elsewhere.
- **Reads and writes stay inside the repo.** A path code-atlas reads from, or writes into, the
  indexed repo is resolved with symlinks followed and refused if it lands outside
  (`code_atlas/containment.py`).
- **The index directory is code-atlas's own.** An index that git tracks, or whose directory,
  database or database sibling is a link or leads outside the repo, is refused by every entry point
  with the fix. Each index file is written by `code_atlas/containment.py`, never through a link,
  `0600` in a `0700` directory, and the database is opened with `trusted_schema=OFF` and SQLite's
  defensive mode.
- **git runs hardened.** Every git command is spawned by `code_atlas/gitutil.py` with the
  repo's `core.fsmonitor`, `core.hooksPath`, `core.sshCommand` and `diff.external` overridden, and a
  stored revision is accepted only as a full object id, after `--end-of-options`.
- **The core makes no network calls.** The optional LLM package, `onboarding_llm/`, is off by
  default. When you enable it, it sends derived facts to Anthropic's API: module paths,
  signatures, docblocks and graph facts, not function bodies.

### Known limitations

- **Two symlink paths are not yet contained:** files under a configured stub root (`CA_STUB_ROOTS`),
  and an indexed file swapped for a link out of the repo since the build — `read_symbol` refuses it,
  but another tool's read-through repair still re-parses it (375). Both are tracked in
  [`docs/BACKLOG.md`](docs/BACKLOG.md).
- **`trusted_schema` stays on where SQLite is too old for it.** A build older than the 3.45 tested
  here (3.40 in Debian bookworm, the runtime image's base) refuses the index's own full-text
  triggers with it off, so there only defensive mode applies.
- **A committed index is refused only where git can answer.** If git cannot run in the repo (not
  installed, or refusing a `.git` owned by another user, as in the runtime image), the index is not
  known to be tracked and is opened, still under the link, mode and SQLite defences above.
- **The rest of the indexed repo's git config applies.** The read-only `git` commands
  (`rev-parse`, `ls-files`, `diff --name-only`, `config --get`) still read its `.git/config` beyond
  the overridden keys. Do not index a working copy whose `.git` directory you did not create, such
  as one unpacked from an archive, outside a container.
- **The runtime image runs as root** unless you pass `--user`. The README shows how.

A report that breaks one of the guarantees above is in scope. A report that restates a known
limitation is not, unless it shows a worse consequence than the one listed here.
